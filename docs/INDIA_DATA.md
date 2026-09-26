# Indian radar input contract

Accepts already calibrated/gridded QPE. Raw IMD polar radar volumes, images and weather-API forecasts are not supported. No automatic live Indian feed is configured.

## Data access and preparation

Start with [IMD APIs](https://mausam.imd.gov.in/responsive/apis.php) and the [Radar Data Supply Portal](https://radarapi.imd.gov.in/dsp/frontend/contact). Check access/redistribution terms for the actual product. Keep credentials and acquired data out of Git.

The [IMD API reference](https://api.imd.gov.in/public/api_reference.html) lists radar images; images cannot replace numeric rainfall tensors. The [xradar IMD NetCDF reader](https://docs.openradarscience.org/projects/xradar/en/main/notebooks/IMD.html) can help read authorized raw data, but does not itself establish rainfall calibration.

Provider-specific reflectivity-to-rain-rate conversion, clutter/attenuation/beam-blockage handling, missing-data masks, projection and scan timing require radar expertise. There is no universal Z-R relationship for every monsoon event; this project does not invent one.

## NPZ fields

| Field | Contract |
|---|---|
| `rain_mmh` | float32 `(4,256,256)`, oldest to newest, calibrated mm/h, finite/nonnegative |
| `latitude` | numeric `(256,256)` WGS84 cell-center latitudes |
| `longitude` | numeric `(256,256)` WGS84 cell-center longitudes |
| `metadata` | scalar JSON string, never a pickled Python object |

Use a Cartesian grid with approximately 1 km cells, columns west-to-east and rows south-to-north, matching the upstream operational orientation. The validator checks adjacent spacing, not scientific correctness of calibration/projection. Do not resize a radar screenshot to 256x256.

Metadata example with illustrative historical timestamps, not supplied observations:

```json
{
  "country": "India",
  "source": "Provider/product identifier and authorized processing provenance",
  "synthetic": false,
  "quality_controlled": true,
  "units": "mm/h",
  "grid_resolution_m": 1000,
  "timestamps": [
    "2026-09-01T06:00:00Z", "2026-09-01T06:05:00Z",
    "2026-09-01T06:10:00Z", "2026-09-01T06:15:00Z"
  ]
}
```

Exactly five-minute spacing and explicit timezone offsets are required. Do not silently interpolate a ten-minute feed and label it observed five-minute data. Fresh runs require scan age 0-10 minutes; historical data requires `--archive`.

Save your prepared arrays:

```python
import json
import numpy as np

def save_prepared_radar(path, rain, lat, lon, metadata):
    np.savez_compressed(
        path, rain_mmh=np.asarray(rain, dtype=np.float32),
        latitude=np.asarray(lat), longitude=np.asarray(lon),
        metadata=json.dumps(metadata),
    )
```

## Model adaptation

The wrapper preserves upstream four-channel ordering, `mm/h / 400.0` inputs, `(1,256,256,4)` batches and inverse scaling by 400. It clips negative predictions before feedback and rejects nonfinite output. Recursive +10 through +60 minute predictions accumulate model error.

Germany-trained weights may fail on Indian monsoon/coastal convection, calibration and terrain. Geographic preprocessing is not retraining.

Before Indian accuracy claims, obtain representative events across seasons/sites; split by event/time/site to avoid leakage; compare persistence and optical-flow baselines; report CSI, false alarm ratio, probability of detection, FSS and intensity errors by lead time. Hold out locations and extreme events, and record radar outages separately. Fine-tune after establishing a baseline; retain independent evaluation.

The v0.1 loader accepts only the checksum-pinned upstream regression artifact. Future India-trained weights require an explicit manifest, checksum, training provenance and updated tests.
