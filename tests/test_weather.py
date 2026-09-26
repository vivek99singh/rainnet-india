from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rainnet_india.core import IST
from rainnet_india.cli import main
from rainnet_india.weather import prepare_weather


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 26, 23, 20, tzinfo=IST)
        self.data = {
            "latitude": 19.076, "longitude": 72.8777, "utc_offset_seconds": 19800,
            "current": {"time": "2026-09-26T23:15", "temperature_2m": 27.4, "apparent_temperature": 31.9,
                        "relative_humidity_2m": 80, "wind_speed_10m": 9.4, "weather_code": 3},
            "current_units": {"temperature_2m": "°C", "apparent_temperature": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h"},
            "hourly_units": {"temperature_2m": "°C", "precipitation_probability": "%", "precipitation": "mm"},
            "hourly": {
                "time": [(datetime(2026, 9, 26, 22) + timedelta(hours=i)).isoformat() for i in range(12)],
                "temperature_2m": [27] * 12, "precipitation_probability": [10] * 12,
                "precipitation": [0] * 12, "weather_code": [3] * 12,
            },
        }

    def test_midnight_intervals_and_past_rain_not_used(self):
        self.data["hourly"]["precipitation_probability"][1] = 95  # 22-23h, already past
        report = prepare_weather(self.data, "mumbai", self.now)
        self.assertEqual(report["hourly"][0]["start"], "2026-09-26T23:00:00+05:30")
        self.assertEqual(report["hourly"][0]["end"], "2026-09-27T00:00:00+05:30")
        self.assertEqual(report["peak_hourly_probability"], 10)

    def test_missing_rain_data_does_not_mean_dry(self):
        for field in ("precipitation_probability", "precipitation"):
            with self.subTest(field=field):
                data = deepcopy(self.data)
                data["hourly"][field][2] = None
                report = prepare_weather(data, "mumbai", self.now)
                self.assertIn("अधूरा", report["headline"])

    def test_wet_signal_even_when_other_hour_missing(self):
        self.data["hourly"]["precipitation_probability"][2] = None
        self.data["hourly"]["precipitation"][3] = 0.3
        report = prepare_weather(self.data, "mumbai", self.now)
        self.assertIn("छाता", report["headline"])

    def test_bad_response_rejected(self):
        changes = [
            ("utc_offset_seconds", 0),
            ("latitude", 28.61),
            ("current_units", {"temperature_2m": "°F"}),
        ]
        for key, value in changes:
            with self.subTest(key=key):
                data = deepcopy(self.data)
                data[key] = value
                with self.assertRaises(ValueError):
                    prepare_weather(data, "mumbai", self.now)
        with self.assertRaisesRegex(ValueError, "stale"):
            prepare_weather(self.data, "mumbai", self.now + timedelta(hours=3))

    def test_invalid_or_gapped_hourly_data_rejected(self):
        for field, value in (("precipitation_probability", 101), ("precipitation", -2), ("temperature_2m", float('nan'))):
            data = deepcopy(self.data)
            data["hourly"][field][2] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                prepare_weather(data, "mumbai", self.now)
        self.data["hourly"]["time"][4] = self.data["hourly"]["time"][3]
        with self.assertRaisesRegex(ValueError, "gaps"):
            prepare_weather(self.data, "mumbai", self.now)

    def test_cli_renders_forecast_and_invalidates_it_when_refresh_fails(self):
        report = prepare_weather(self.data, "mumbai", self.now)
        report["source_url"] = "https://api.open-meteo.com/v1/forecast"
        with tempfile.TemporaryDirectory() as tmp:
            args = ["weather", "--output", tmp]
            with patch("rainnet_india.weather.fetch_weather", return_value=(report, self.data)):
                self.assertEqual(main(args), 0)
            page = (Path(tmp) / "report.html").read_text(encoding="utf-8")
            self.assertIn("27.4°", page)
            self.assertIn("Open-Meteo", page)
            with patch("rainnet_india.weather.fetch_weather", side_effect=OSError("Provider unavailable")):
                self.assertEqual(main(args), 2)
            self.assertNotIn("27.4°", (Path(tmp) / "report.html").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((Path(tmp) / "report.json").read_text())["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
