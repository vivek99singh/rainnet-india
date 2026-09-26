# Readable weather forecast

Run from the repository, using its Python environment:

```powershell
.\.venv\Scripts\python.exe -m rainnet_india.cli weather --city mumbai
Start-Process output/weather/report.html
```

Supported city names: mumbai, delhi, bengaluru, chennai, kolkata, hyderabad, pune. Use `--output output/delhi-weather` to keep a separate report. Linux/macOS: use `.venv/bin/python` and open the report in your browser.

Data flow: city preset coordinates → Open-Meteo HTTPS forecast API → unit/time/location checks → upcoming hourly intervals → local HTML and JSON. No account, secrets or model weights are needed. Only city coordinates and standard forecast options are sent. No personal location is collected. There is no background polling or phone notification.

The dashboard presents model-estimated current temperature, feels-like temperature, humidity and wind, plus eight upcoming precipitation intervals. All times use IST. Probability and precipitation refer to the preceding hour ending at the API timestamp; cards explicitly show that interval. The first interval can be partially elapsed.

The umbrella suggestion is a rule: any of the first three intervals with probability ≥40% or precipitation ≥0.1 mm triggers a suggestion. These are product settings, not IMD warnings or calibrated safety thresholds. Missing values never become zero. Network errors, incorrect units, stale current data and malformed series stop generation. A failed/interrupted refresh marks previous reports unavailable. Saved pages show a stale notice when opened more than two hours after fetch; refresh manually.

Source: [Open-Meteo documentation](https://open-meteo.com/en/docs), [attribution licence](https://creativecommons.org/licenses/by/4.0/) and [API terms](https://open-meteo.com/en/terms). The free API endpoint permits non-commercial use including educational content under its terms; commercial products/promotions require appropriate service terms. No commercial subscription is purchased by this project.

## Video demo wording

“Mumbai select कीजिए। यहाँ तापमान और अगले घंटों में बारिश की संभावना दिखती है। यह project forecast के आधार पर छाता रखने का सुझाव देता है। बाहर निकलने से पहले दोबारा check कर लीजिए।”

Describe this as a weather-data project. Do not say this screen runs our India-trained AI or predicts the exact minute someone will get wet. The separate RainNet research path has different inputs and limitations. [Indian radar sources](INDIA_DATA.md) explain the next research step.
