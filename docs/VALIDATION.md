# Validation evidence

Date: 26 September 2026. Platform: Windows x64, Python 3.12. Upstream base: `43aa7c0144202c6e85706a07690d00619b222492`.

## Completed

- Current offline suite: 26 tests passed on Windows/Python 3.12, including the original 17 radar tests, six weather tests and three IndianAPI request/security tests. Live IndianAPI authentication is not covered by mocks.

- Weather-view update: current Open-Meteo Mumbai request completed at 23:17 IST on 26 September 2026. API current-model timestamp 23:15 IST; 27.4°C, feels-like 31.9°C, 80% humidity and 9.3 km/h wind. The next three hourly probabilities were 21%, 26%, 29%. These are recorded fetch results, not enduring weather facts. Source JSON is local under `output/weather/` and is not committed.
- Browser check: readable Mumbai HTML displayed current values and all eight hourly intervals, crossing midnight correctly. This is a weather-model forecast view, separate from RainNet inference.
- Indian radar sample `IMD/JPR220822135253-IMD-B.nc` downloaded from open-radar-data (2,171,460 bytes). A historical sample download does not establish live Mumbai access or model skill.
- IndianAPI optional request client prepared from the published contract. Authenticated live response remains pending an account API key. Tests use explicit mock responses and do not establish provider availability.

- 17 offline unit/integration tests passed: units/grid spacing/orientation, missing data, timestamps, coverage, normalization/channel order, recursive feedback, model-output failures, IST/threshold reporting, archive labels, HTML escaping and CLI demo.
- Mumbai synthetic demo generated JSON/HTML/NumPy output. Persistence baseline, explicitly NOT AI.
- Isolated model dependencies installed; exact environment in `requirements-tested-windows-py312.txt`.
- Editable package installation and CLI help succeeded; `pip check` reported no broken requirements.
- Original regression weights downloaded from Zenodo; publisher MD5 `d65444a42821655e31217c808aa59a9d` matched.
- Real RainNet2024 inference succeeded on German event 20815: input indices 20-23, observed comparison indices 24-35, output `(12,256,256)`. All predictions finite/nonnegative. Inference took 35.55 seconds on the local CPU (one run, not a benchmark).
- Mean absolute rain-rate error on that single sample: RainNet **0.9311 mm/h**, persistence **0.9981 mm/h**. These are grid/time averages for one German event, not India accuracy or a general superiority claim.
- The `predict` CLI also completed three AI forecast steps on the synthetic Mumbai grid and generated the labeled synthetic JSON/HTML/NumPy outputs and console alert. Synthetic inputs establish integration behavior, not forecast skill.
- [GitHub Actions run 36259133932](https://github.com/vivek99singh/rainnet-india/actions/runs/36259133932) passed on Ubuntu/Python 3.12 for commit `dafd8f36e59fbe94289fe21f5c4dd5e6c36aed1c`: package installation, all 17 tests and the Mumbai offline demo. Completed 26 September 2026 at 17:28 UTC. Model inference is tested locally, not by this lightweight CI job.

## Pending

- Live Indian radar ingestion/calibration, Indian model training/evaluation and phone notifications: not performed.

Software tests do not establish meteorological accuracy.
