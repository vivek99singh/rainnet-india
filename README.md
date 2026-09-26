# RainNet India — city weather and radar experiments

Get a readable Indian city forecast with `weather`: temperature, feels-like temperature, upcoming hourly rain chances and a simple umbrella suggestion. This uses current [Open-Meteo](https://open-meteo.com/) weather-model output, not invented demo values.

The separate radar research workflow extends [RainNet2024](https://github.com/hydrogo/the-rainnet2024-family), with Indian city presets, radar-input checks, IST reports and a local rain-threshold alert.

**Radar research prototype: no live India radar connection, India-trained RainNet weights or verified Indian RainNet accuracy.** Changing coordinates does not adapt a weather model to a new climate. This project adds the engineering workflow for experiments with suitable Indian observations; scientific validation remains necessary.

[Hindi usage guide](docs/HINDI_GUIDE.md) · [India data contract](docs/INDIA_DATA.md) · [Validation](docs/VALIDATION.md) · [Original README](UPSTREAM_README.md)

## Capabilities

- Current city forecast dashboard, fetched on demand; hourly rain probability, precipitation, temperature, humidity and wind. A simple umbrella rule checks the next three hourly periods. It is not an AI inference or exact rain-start prediction.
- Offline synthetic demo for Mumbai, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad and Pune. Clearly marked **SYNTHETIC DEMO / NOT AI**: persistence repeats the latest invented rain field.
- RainNet2024 regression inference on four prepared radar grids, at 5-minute steps up to a 60-minute experimental rollout.
- Checks for mm/h units, dimensions, timestamps, missing data, approximate 1 km spacing and location coverage. Invalid inputs stop the run.
- IST JSON/HTML reports, gridded NumPy output and a **local console alert** at a user-selected rain-rate threshold.
- Offline tests and a real-model smoke-test script using the original German sample.

Phone push, WhatsApp/Telegram delivery, live IMD ingestion, raw radar calibration/gridding, automatic scheduling and fine-tuning are **not implemented**. No external messages are sent. The offline workflow needs no API key or cloud subscription.

## Quick start

Use Python 3.12. Download the repository ZIP, or clone it:

```bash
git clone https://github.com/vivek99singh/rainnet-india.git
cd rainnet-india
```

From this repository directory, Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m rainnet_india.cli weather --city mumbai
Start-Process output/weather/report.html
```

Linux/macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m rainnet_india.cli weather --city mumbai
```

Open `output/weather/report.html`. Rerun the command for a fresh snapshot. Internet is required; no API key or TensorFlow is needed for the free non-commercial endpoint. [Open-Meteo terms](https://open-meteo.com/en/terms) govern API use, including educational and commercial use; forecast attribution is included in the page. City presets represent a city-center point, not every neighborhood.

The page uses actual API output, but current conditions are weather-model estimates, not a local sensor measurement. It does not run RainNet. Rain chance and precipitation refer to the hour displayed on each card; the summary reports the highest individual hourly probability, not a combined three-hour probability. Missing data stays unknown; failed refreshes replace the previous report with an unavailable notice. See the [weather guide](docs/WEATHER.md).

Optional [IndianAPI request client](docs/INDIANAPI.md): fetch India-specific daily forecasts or documented global hourly forecasts using your own API key. Authentication/live response is not verified yet, and this client is not wired into the dashboard.

For the offline research demo, run `python -m rainnet_india.cli demo --city mumbai` and open `output/demo/report.html`. That command generates an invented rain field and is **not today's Mumbai weather**.

## Actual AI inference

Install the model dependencies into the same environment and download the regression weights (~310 MB):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
.\.venv\Scripts\python.exe scripts/download_model.py
.\.venv\Scripts\python.exe scripts/validate_upstream.py
```

The downloader verifies the publisher checksum on [Zenodo](https://zenodo.org/records/12547127). Weights are not committed here. The loader accepts this specific regression artifact. TensorFlow runs on CPU with legacy Keras compatibility. On Linux/macOS substitute `.venv/bin/python`.

`validate_upstream.py` uses **German** CatRaRE event 20815 and writes `output/upstream-validation/metrics.json`. The sample retains its original provenance; it has not been relabeled as Indian data.

Local verification: 26 tests passed across radar, weather and the optional IndianAPI client. Actual pretrained inference completed on the German sample, and the prediction CLI completed on a synthetic Mumbai grid. See [the evidence and limits](docs/VALIDATION.md).

For prepared Indian radar data, follow [INDIA_DATA.md](docs/INDIA_DATA.md):

```powershell
.\.venv\Scripts\python.exe -m rainnet_india.cli predict --input india-data/mumbai.npz --city mumbai --steps 12 --threshold-mmh 1
```

Add `--archive` for historical replay; outputs are visibly labeled. A fresh run requires the newest observation to be no more than 10 minutes old. `--output output/my-run` changes the destination.

Thresholds are research settings, **not IMD warning classifications**. A crossing is neither an exact rain-start time nor a calibrated probability. Rain may already be occurring; the report includes the latest observed rate. No crossing is not an all-clear.

## Data flow

Authorized Indian radar/QPE → provider-specific calibration, QC and 1 km gridding → four timestamped arrays → input validation → Germany-trained RainNet2024 → city threshold check → local report/console alert.

The original notebooks remain intact and use Germany's DWD feed. Do not reuse their DWD projection/downloader with Indian coordinates. Consult the [IMD API directory](https://mausam.imd.gov.in/responsive/apis.php), [radar data supply portal](https://radarapi.imd.gov.in/dsp/frontend/contact) and [xradar IMD reader](https://docs.openradarscience.org/projects/xradar/en/main/notebooks/IMD.html). Radar images and forecast bulletins are not calibrated rainfall tensors.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

CI runs lightweight tests/demo, not the model download. `requirements-model.txt` pins direct dependencies; `requirements-tested-windows-py312.txt` records the tested Windows environment. Do not use that Windows freeze unchanged on Linux.

## Credit

Based on Georgy Ayzel and Maik Heistermann's RainNet2024 work, upstream commit `43aa7c0144202c6e85706a07690d00619b222492`. Original MIT license, attribution, notebooks and sample provenance are retained. India workflow additions: Vivek Singh. Weights and datasets have their own source terms; code licensing does not override data access/redistribution rights. No IMD or original-author endorsement is implied.

Use [official IMD forecasts and warnings](https://mausam.imd.gov.in/) for weather decisions. This is not an emergency warning service.
