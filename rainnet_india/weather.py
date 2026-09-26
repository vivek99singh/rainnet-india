"""Current weather-model forecast, separate from the radar research model."""
from datetime import datetime, timedelta
import html
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from .core import CITIES, IST


def condition(code):
    if code == 0:
        return "Clear sky", "☀"
    if code in (1, 2):
        return "Partly cloudy", "⛅"
    if code == 3:
        return "Overcast", "☁"
    if code in (45, 48):
        return "Fog", "≋"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle", "🌦"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain / showers", "🌧"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow", "❄"
    if code in (95, 96, 99):
        return "Thunderstorms", "⛈"
    return "Condition unavailable", "—"


def number(value, lower=-100, upper=100):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError("Weather provider returned an invalid numeric value")
    return value


def local_time(value):
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=IST) if dt.tzinfo is None else dt.astimezone(IST)


def prepare_weather(data, city, fetched_at):
    """Reject stale or mismatched responses; missing weather stays unknown."""
    if fetched_at.tzinfo is None:
        raise ValueError("Fetch time needs a timezone")
    fetched_at = fetched_at.astimezone(IST)
    if data.get("utc_offset_seconds") != 19800:
        raise ValueError("Expected an India-time weather response")
    lat, lon = CITIES[city]
    if abs(float(data["latitude"]) - lat) > 0.25 or abs(float(data["longitude"]) - lon) > 0.25:
        raise ValueError("Weather response does not cover the requested city")
    for section, fields in {
        "current_units": {"temperature_2m": "°C", "apparent_temperature": "°C", "wind_speed_10m": "km/h", "relative_humidity_2m": "%"},
        "hourly_units": {"temperature_2m": "°C", "precipitation": "mm", "precipitation_probability": "%"},
    }.items():
        if any(data.get(section, {}).get(k) != v for k, v in fields.items()):
            raise ValueError("Unexpected weather units")
    current = data["current"]
    valid_at = local_time(current["time"])
    if not -900 <= (fetched_at - valid_at).total_seconds() <= 7200:
        raise ValueError("Current weather response is stale or future-dated")
    hourly = data["hourly"]
    fields = ("temperature_2m", "precipitation_probability", "precipitation", "weather_code")
    if any(len(hourly[k]) != len(hourly["time"]) for k in fields):
        raise ValueError("Incomplete hourly weather series")
    times = [local_time(t) for t in hourly["time"]]
    if any(b - a != timedelta(hours=1) for a, b in zip(times, times[1:])):
        raise ValueError("Hourly weather series has gaps or duplicate times")
    rows = []
    for i, end in enumerate(times):
        if end <= fetched_at:
            continue
        rows.append({
            "end": end.isoformat(),
            "start": (end - timedelta(hours=1)).isoformat(),
            "temperature": number(hourly["temperature_2m"][i]),
            "probability": number(hourly["precipitation_probability"][i], 0, 100),
            "precipitation": number(hourly["precipitation"][i], 0, 2000),
            "condition": condition(hourly["weather_code"][i])[0],
            "icon": condition(hourly["weather_code"][i])[1],
        })
        if len(rows) == 8:
            break
    if len(rows) < 8:
        raise ValueError("Not enough upcoming hourly forecasts")
    near = rows[:3]
    probabilities = [r["probability"] for r in near if r["probability"] is not None]
    peak = max(probabilities) if probabilities else None
    missing = any(r[k] is None for r in near for k in ("probability", "precipitation"))
    wet = any((r["probability"] or 0) >= 40 or (r["precipitation"] or 0) >= 0.1 for r in near)
    headline = "छाता साथ रख लीजिए" if wet else ("बारिश का अनुमान अधूरा है" if missing else "फिलहाल बारिश की संभावना कम है")
    detail = "आने वाले घंटों में बारिश का संकेत है। निकलने से पहले दोबारा जाँच लें।" if wet else ("कुछ आँकड़े उपलब्ध नहीं हैं। इसे dry-weather signal न मानें।" if missing else "स्थानीय मौसम बदल सकता है। बाहर जाने से पहले forecast फिर देख लें।")
    return {
        "city": city, "source": "Open-Meteo weather-model forecast", "fetched_at": fetched_at.isoformat(),
        "valid_at": valid_at.isoformat(), "temperature": number(current.get("temperature_2m")),
        "feels_like": number(current.get("apparent_temperature")),
        "humidity": number(current.get("relative_humidity_2m"), 0, 100),
        "wind": number(current.get("wind_speed_10m"), 0, 500),
        "condition": condition(current.get("weather_code"))[0], "icon": condition(current.get("weather_code"))[1],
        "hourly": rows, "peak_hourly_probability": peak, "headline": headline, "detail": detail,
    }


def fetch_weather(city):
    lat, lon = CITIES[city]
    query = urlencode({
        "latitude": lat, "longitude": lon, "timezone": "Asia/Kolkata", "forecast_days": 2,
        "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
    })
    url = "https://api.open-meteo.com/v1/forecast?" + query
    with urlopen(url, timeout=25) as response:
        data = json.load(response)
    report = prepare_weather(data, city, datetime.now(IST))
    report["source_url"] = url
    return report, data


def display(value, suffix="", decimals=0):
    return "—" if value is None else f"{value:.{decimals}f}{suffix}"


def write_weather(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    e = html.escape
    cards = []
    for row in report["hourly"]:
        start, end = local_time(row["start"]), local_time(row["end"])
        width = row["probability"] or 0
        cards.append(f'''<article class="hour"><small>{start:%d %b}</small><b>{start:%H:%M}–{end:%H:%M}</b>
        <span class="symbol">{row['icon']}</span><strong>{display(row['probability'], '%')}</strong>
        <span class="muted">rain chance</span><div class="track"><div style="width:{width}%"></div></div>
        <span>{display(row['precipitation'], ' mm', 1)}</span><small>{display(row['temperature'], '°')} at {end:%H:%M}</small></article>''')
    fetched, valid = local_time(report["fetched_at"]), local_time(report["valid_at"])
    page = f'''<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{e(report['city'].title())} weather · RainNet India</title><style>
    *{{box-sizing:border-box}} body{{margin:0;background:#081524;color:#edf6ff;font:16px 'Segoe UI',system-ui,sans-serif}}
    main{{max-width:1160px;margin:auto;padding:32px 28px}} header{{display:flex;justify-content:space-between;gap:16px;align-items:center}}
    .brand{{font-weight:700;letter-spacing:.08em;font-size:13px;color:#91b6ce}} .pill{{padding:8px 12px;border:1px solid #335367;border-radius:30px;color:#8ee1d0;font-size:12px}}
    h1{{font-size:42px;margin:28px 0 2px}} .muted,small{{color:#9eb3c5}} .grid{{display:grid;grid-template-columns:1fr 1.2fr;gap:24px;margin:22px 0 30px}}
    .current,.advice{{border:1px solid #294455;border-radius:24px;padding:26px;background:#112639}}
    .temp{{font-size:88px;font-weight:650;letter-spacing:-5px;line-height:1.2}} .sky{{font-size:56px;float:right}}
    .metrics{{display:flex;gap:25px;margin-top:22px}} .metrics b,.metrics span{{display:block}} .metrics span{{color:#a6bccc;font-size:12px;margin-top:6px}}
    .advice{{background:linear-gradient(135deg,#123b43,#122c3d)}} .advice h2{{font-size:31px;line-height:1.4;margin:12px 0}}
    .advice p{{color:#c3dae3;line-height:1.7}} .peak{{font-size:33px;color:#9af0cf}} h2{{font-size:21px}} .hours{{display:grid;grid-template-columns:repeat(8,1fr);gap:10px}}
    .hour{{background:#102436;border:1px solid #223c4f;border-radius:15px;padding:15px 10px;text-align:center;display:flex;flex-direction:column;gap:7px;font-size:12px}}
    .hour strong{{font-size:25px}} .hour .symbol{{font-size:29px;margin:4px}} .track{{height:5px;background:#294254;border-radius:5px;margin:4px 0}} .track div{{height:5px;background:#72dfc0;border-radius:5px}}
    .note{{font-size:12px;line-height:1.65;color:#9eb3c5;margin-top:18px}} a{{color:#96d8fa}} footer{{border-top:1px solid #284050;margin-top:28px;padding-top:18px;display:flex;justify-content:space-between;gap:20px;font-size:12px;line-height:1.8}}
    details{{font-size:12px;color:#9eb3c5;margin-top:20px}} code{{color:#c0e7ff}} #age{{display:none;background:#654218;padding:14px;border-radius:12px;margin-top:16px}}
    @media(max-width:900px){{.hours{{grid-template-columns:repeat(4,1fr)}}}} @media(max-width:620px){{main{{padding:22px 16px}}.grid{{grid-template-columns:1fr}}h1{{font-size:34px}}.hours{{grid-template-columns:repeat(2,1fr)}}footer{{flex-direction:column}}}}
    </style></head><body><main>
    <header><span class="brand">RAINNET INDIA / WEATHER</span><span class="pill">Forecast snapshot · IST</span></header>
    <div id="age">यह snapshot पुराना है। नया forecast लेने के लिए weather command फिर चलाएँ।</div>
    <h1>{e(report['city'].title())}</h1><div class="muted">{valid:%d %b %Y · %H:%M} IST · current model estimate</div>
    <div class="grid"><section class="current"><span class="sky">{report['icon']}</span><div class="temp">{display(report['temperature'], '°', 1)}</div>
    <p>{e(report['condition'])} · Feels like {display(report['feels_like'], '°', 1)}</p><div class="metrics">
    <div><b>{display(report['humidity'], '%')}</b><span>HUMIDITY</span></div><div><b>{display(report['wind'], ' km/h', 1)}</b><span>WIND</span></div></div></section>
    <section class="advice"><span class="brand">बाहर निकलने से पहले</span><h2>{e(report['headline'])}</h2><p>{e(report['detail'])}</p>
    <span class="peak">{display(report['peak_hourly_probability'], '%')}</span><div class="note">अगले 3 hourly periods में सबसे अधिक rain chance<br>यह पूरे 3 घंटे की combined probability नहीं है।</div></section></div>
    <h2>आने वाले घंटों में बारिश?</h2><div class="hours">{''.join(cards)}</div>
    <p class="note">हर card में बताए गए एक घंटे की बारिश की संभावना और कुल precipitation है। Temperature उस घंटे के अंत का है। पहला period अभी चल रहा हो सकता है। समय IST में है।</p>
    <footer><div>Weather: <a href="https://open-meteo.com/">Open-Meteo</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a><br>Fetched {fetched:%d %b %Y, %H:%M} IST · city-centre forecast</div>
    <div><a href="https://mausam.imd.gov.in/">IMD forecasts &amp; warnings</a><br><a href="https://dss.imd.gov.in/dwr_img/GIS/currentwx/currentwx.html">IMD radar &amp; weather map</a></div></footer>
    <details><summary>Source &amp; refresh</summary><p>यह weather-model forecast है; RainNet radar inference या India-trained AI output नहीं है। Hourly data से बारिश शुरू होने का exact minute नहीं मिलता। छाते का सुझाव एक सरल threshold rule है।</p>
    <p>Refresh: <code>python -m rainnet_india.cli weather --city {e(report['city'])}</code> · फिर बनी हुई report खोलें। यह page अपने-आप update नहीं होता।</p>
    <a href="{e(report['source_url'], quote=True)}">Source API response</a></details>
    </main><script>if(Date.now()-Date.parse('{report['fetched_at']}')>7200000)document.getElementById('age').style.display='block';</script></body></html>'''
    (directory / "report.html").write_text(page, encoding="utf-8")
    (directory / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def run_weather(city, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Mark any older output unavailable before fetching, including interrupted runs.
    (directory / "report.html").write_text('<!doctype html><meta charset="utf-8"><h1>Forecast unavailable</h1><p>A new forecast has not completed. Run the weather command again.</p>', encoding="utf-8")
    (directory / "report.json").write_text('{"status":"unavailable"}', encoding="utf-8")
    (directory / "source.json").write_text('{"status":"unavailable"}', encoding="utf-8")
    report, data = fetch_weather(city)
    (directory / "source.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_weather(report, directory)
    return directory / "report.html"
