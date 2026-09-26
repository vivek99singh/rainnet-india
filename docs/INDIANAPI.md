# IndianAPI: optional data provider

Checked 26 September 2026: [documentation](https://indianapi.in/documentation/weather-api), [product/endpoints/pricing](https://indianapi.in/weather-api). The displayed free tier is 1,000 requests/month and 1 request/second. Login and an API subscription/key are required. No paid subscription is necessary for a small demo, and this repository does not purchase one.

- `/india/weather?city=Mumbai`: the provider attributes its India data to IMD. Documented response includes daily max/min, morning/evening humidity and dated daily forecast descriptions. These are not instantaneous temperature or hourly probability fields.
- `/india/cities`: resolves supported station IDs/names; city fuzzy matching must be checked, especially where Mumbai has multiple stations.
- `/india/weather_by_id`: targets a documented station ID.
- `/global/weather?location=Mumbai&days=3`: documented current and hourly forecast, including `chance_of_rain`, from aggregated global providers. Do not label this output IMD solely because the location is Indian.

The service explicitly says it is not affiliated with IMD. No numerical raw-radar endpoint is documented. Forecast JSON cannot train or replace the prepared radar inputs in `predict`.

## Fetch without publishing your key

Sign in at [IndianAPI](https://indianapi.in/sign-in), select an appropriate plan and obtain the API key. Run this in a local PowerShell terminal; the secret is entered in a masked prompt rather than saved in shell history:

```powershell
$weatherSecret = Read-Host 'IndianAPI key' -AsSecureString
$env:INDIANAPI_KEY = [System.Net.NetworkCredential]::new('', $weatherSecret).Password
try {
    .\.venv\Scripts\python.exe scripts/fetch_indianapi.py --city Mumbai
} finally {
    Remove-Item Env:\INDIANAPI_KEY
    $weatherSecret.Dispose()
}
```

For the documented hourly endpoint, add `--endpoint global` to the Python command. The script sends `x-api-key` only in an HTTPS request header to `weather.indianapi.in`; it never stores the key in JSON or HTML. Keep secrets out of screenshots and Git.

Output: `output/indianapi/response.json`. The fetch timestamp records when we received it; it is not a forecast issue time. Inspect returned city/station and forecast dates. Null rainfall means unavailable, not zero. Network failures do not silently switch to another provider.

Integration status: request client prepared against the published contract; no authenticated live response has been verified yet. The readable `weather` dashboard currently uses Open-Meteo. IndianAPI JSON is not yet mapped into that screen; its daily and hourly responses have different semantics and require a verified response before that mapping.
