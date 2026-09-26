# Indian radar input contract

Accepts already calibrated/gridded QPE. Raw IMD polar radar volumes, images and weather-API forecasts are not supported. No automatic live Indian feed is configured.

## Data access and preparation

### Verified Indian sources (26 September 2026)

Indian radar data exists. Public samples, operational images and continuous numerical feeds have different access paths:

| Source | Verified availability | Use in this project |
|---|---|---|
| [open-radar-data IMD samples](https://github.com/openradar/open-radar-data/tree/main/data/IMD) | Public historical NetCDF files. Downloaded `JPR220822135253-IMD-B.nc` successfully (2,171,460 bytes). | Reader/preprocessing experiments; not current Mumbai weather or a training time series. |
| [xradar IMD reader](https://docs.openradarscience.org/projects/xradar/en/main/notebooks/IMD.html) | Documented `engine="imd"` reader; sample timestamp 22 August 2022. | Open-source parsing and volume assembly. The `.nc`, `.nc.1` through `.nc.9` files are elevation sweeps of one volume, not ten successive times. |
| [IMD Radar Data Supply guide](https://radarapi.imd.gov.in/Received_data/dsp_userguide.pdf) | Official guide describes account creation and data requests. Direct retrieval hit a certificate-chain error here. | Check account access, station/date availability and applicable terms. An anonymous continuous Mumbai numerical feed has not been verified. |
| [IMD Mumbai SWIRLS](https://nwp.imd.gov.in/swirls_mum.php) | Mumbai is listed in the [official nowcast menu](https://nwp.imd.gov.in/fdp_now/menu_1.php); opening the product redirected to login. | Potential existing nowcast source, subject to access; no current forecast retrieved from it. |
| [IMD public weather/radar map](https://dss.imd.gov.in/dwr_img/GIS/currentwx/currentwx.html) | Public visualization entry point. | Link for viewers; do not treat rendered colors as calibrated numeric rainfall. |

For a small reader experiment, the upstream example is:

```python
from open_radar_data import DATASETS
import xarray as xr
import xradar  # registers the IMD backend in versions with IMD support

path = DATASETS.fetch("IMD/JPR220822135253-IMD-B.nc")
sweep = xr.open_dataset(path, engine="imd")
print(sweep)
```

These are optional radar-research dependencies, not dependencies of `weather`. The download above was verified locally; this reader example is from the xradar development documentation and was not executed here. Use a release/build that includes its IMD backend. Reflectivity in dBZ still needs appropriate processing before the mm/h contract below.

An [IIT Bombay/IMD Mumbai preprint](https://arxiv.org/abs/2607.16080) describes training with Mumbai radar observations from May–August 2023. This supports the feasibility of India-trained nowcasting, but we have not obtained its training archive or model weights. It is not the model used by this repository.

For an immediate, readable forecast, use `weather --city mumbai`: this fetches Open-Meteo weather-model output. It does not use these radar samples, and does not claim to be India-trained RainNet.

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
