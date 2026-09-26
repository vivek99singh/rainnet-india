"""Validated gridded radar inputs and RainNet2024 regression inference.

Normalization and channel ordering follow Georgy Ayzel's MIT-licensed
example_operational.ipynb at upstream commit 43aa7c0144202c6e85706a07690d00619b222492.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30), "IST")
CITIES = {
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
}
MODEL_MD5 = "d65444a42821655e31217c808aa59a9d"  # Zenodo publisher checksum


def parse_time(value):
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamps must include UTC offset; use +00:00 or Z.")
    return dt.astimezone(timezone.utc)


def distance_km(lat1, lon1, lat2, lon2):
    a, b = np.radians(lat1), np.radians(lat2)
    dlat, dlon = b - a, np.radians(lon2) - np.radians(lon1)
    h = np.sin(dlat / 2) ** 2 + np.cos(a) * np.cos(b) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def validate_rain(rain):
    rain = np.asarray(rain, dtype=np.float32)
    if rain.shape != (4, 256, 256):
        raise ValueError("Expected exactly four 256x256 radar grids, oldest first.")
    if not np.isfinite(rain).all() or (rain < 0).any():
        raise ValueError("Missing/negative rain data is not dry weather; fix upstream QC.")
    return rain


def load_input(path, *, archive=False, now=None):
    with np.load(path, allow_pickle=False) as z:
        rain = validate_rain(z["rain_mmh"])
        lat, lon = z["latitude"].copy(), z["longitude"].copy()
        meta = json.loads(str(z["metadata"].item()))
    if lat.shape != (256, 256) or lon.shape != (256, 256):
        raise ValueError("Latitude and longitude must each be 256x256 cell-center arrays.")
    if not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError("Coordinates must be finite.")
    if (np.abs(lat) > 90).any() or (np.abs(lon) > 180).any():
        raise ValueError("Coordinates outside WGS84 bounds.")
    if not (np.diff(lat, axis=0) > 0).all() or not (np.diff(lon, axis=1) > 0).all():
        raise ValueError("Grid rows must run south-to-north and columns west-to-east.")
    if meta.get("units") != "mm/h" or meta.get("grid_resolution_m") != 1000:
        raise ValueError("Require calibrated mm/h on a 1 km Cartesian grid; not dBZ/images.")
    # Reject false '1 km' metadata and duplicated geographic coordinates.
    for axis in (0, 1):
        l1, l2 = np.take(lat, range(255), axis), np.take(lat, range(1, 256), axis)
        o1, o2 = np.take(lon, range(255), axis), np.take(lon, range(1, 256), axis)
        spacing = distance_km(l1, o1, l2, o2)
        if not ((spacing > 0.85) & (spacing < 1.15)).all():
            raise ValueError("Cell centers are not approximately 1 km apart.")
    if meta.get("country") != "India" or meta.get("quality_controlled") is not True:
        raise ValueError("Declare country=India and quality_controlled=true after actual QC.")
    if not isinstance(meta.get("synthetic"), bool) or not meta.get("source"):
        raise ValueError("Declare a nonempty source and synthetic true/false.")
    times = [parse_time(t) for t in meta.get("timestamps", [])]
    if len(times) != 4 or any((b-a).total_seconds() != 300 for a,b in zip(times, times[1:])):
        raise ValueError("Require four chronological observations spaced exactly 5 minutes.")
    now = now or datetime.now(timezone.utc)
    age = (now - times[-1]).total_seconds()
    if not archive and not 0 <= age <= 600:
        raise ValueError("Newest scan is future-dated or older than 10 minutes; use --archive for replay.")
    return rain, lat, lon, meta, times[-1]


def location_cell(lat, lon, point):
    d = distance_km(lat, lon, *point)
    cell = np.unravel_index(np.argmin(d), d.shape)
    if d[cell] > 1.5:
        raise ValueError("Requested location is outside radar coverage (nearest cell >1.5 km).")
    return cell


def nowcast(rain, model, steps=12):
    if not 1 <= steps <= 12:
        raise ValueError("Choose 1-12 five-minute steps.")
    x = np.moveaxis(validate_rain(rain) / 400.0, 0, -1)[None, ...]
    results = []
    for _ in range(steps):
        pred = np.asarray(model.predict(x, verbose=0), dtype=np.float32)
        if pred.shape != (1, 256, 256, 1) or not np.isfinite(pred).all():
            raise ValueError("Invalid model output; refusing to emit a weather result.")
        pred = np.maximum(pred, 0)
        results.append(pred[0, :, :, 0] * 400.0)
        x = np.concatenate((x[..., 1:], pred), axis=-1)
    return np.stack(results)


def load_model(path):
    # Only load the specific published artifact, not arbitrary serialized models.
    h = hashlib.md5(usedforsecurity=False)
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != MODEL_MD5:
        raise ValueError("Model differs from the published RainNet2024 regression artifact.")
    import os
    os.environ["TF_USE_LEGACY_KERAS"] = "1"
    os.environ["SM_FRAMEWORK"] = "tf.keras"
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    import efficientnet.tfkeras  # noqa: F401 -- registers model custom objects
    import segmentation_models  # noqa: F401
    from tensorflow.keras.models import load_model as keras_load
    return keras_load(path, compile=False)


def make_report(pred, rain, cell, last_scan, meta, *, city, threshold=1.0, archive=False, backend="rainnet2024"):
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError("Threshold must be positive finite mm/h.")
    values = pred[:, cell[0], cell[1]]
    hits = np.flatnonzero(values >= threshold)
    mode = "SYNTHETIC DEMO" if meta["synthetic"] else ("ARCHIVE REPLAY" if archive else "EXPERIMENTAL")
    return {
        "mode": mode, "model": backend, "india_accuracy_validated": False,
        "location": city, "source": meta["source"], "timezone": "Asia/Kolkata",
        "last_observation_ist": last_scan.astimezone(IST).isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "observed_rate_mmh": float(rain[-1, cell[0], cell[1]]),
        "threshold_mmh": threshold,
        "threshold_crossing_lead_minutes": int((hits[0]+1)*5) if len(hits) else None,
        "forecast": [{"valid_at_ist": (last_scan+timedelta(minutes=(i+1)*5)).astimezone(IST).isoformat(),
                      "rate_mmh": round(float(v), 3)} for i,v in enumerate(values)],
        "interpretation": "Model threshold crossing; not a precise rain-start time or probability.",
        "warning": "Research only. Germany-trained model; India skill unmeasured. Follow official IMD warnings.",
    }


def synthetic_input(path, city):
    """An invented rain field at an Indian city; never an observed weather record."""
    lat0, lon0 = CITIES[city]
    y, x = np.mgrid[-128:128, -128:128]
    lat = lat0 + y / 111.195
    lon = lon0 + x / (111.195 * np.cos(np.radians(lat0)))
    rain = np.stack([10*np.exp(-((x-(-12+i*4))**2+y**2)/100) for i in range(4)]).astype("float32")
    latest = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    latest -= timedelta(minutes=latest.minute % 5)
    meta = {"country": "India", "source": "Invented Gaussian rain field; NO observed weather",
            "synthetic": True, "quality_controlled": True, "units": "mm/h", "grid_resolution_m": 1000,
            "timestamps": [(latest-timedelta(minutes=t)).isoformat() for t in (15,10,5,0)]}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, rain_mmh=rain, latitude=lat, longitude=lon, metadata=json.dumps(meta))
