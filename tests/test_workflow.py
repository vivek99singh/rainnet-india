from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from rainnet_india.cli import main, write_report
from rainnet_india.core import (CITIES, load_input, location_cell, make_report,
                               nowcast, parse_time, synthetic_input)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "input.npz"
        synthetic_input(self.path, "mumbai")

    def change(self, **updates):
        with np.load(self.path, allow_pickle=False) as z:
            d = {k: z[k].copy() for k in z.files}
        meta = json.loads(str(d["metadata"].item()))
        for k, v in updates.items():
            if k in d and k != "metadata":
                d[k] = v
            else:
                meta[k] = v
        d["metadata"] = json.dumps(meta)
        np.savez_compressed(self.path, **d)

    def test_valid_india_grid_and_city_cell(self):
        rain, lat, lon, meta, last = load_input(self.path)
        self.assertEqual(location_cell(lat, lon, CITIES["mumbai"]), (128, 128))
        self.assertEqual(rain.shape, (4, 256, 256))
        self.assertTrue(meta["synthetic"])

    def test_wrong_city_is_rejected(self):
        _, lat, lon, _, _ = load_input(self.path)
        with self.assertRaisesRegex(ValueError, "coverage"):
            location_cell(lat, lon, CITIES["delhi"])

    def test_dbz_is_not_rain_rate(self):
        self.change(units="dBZ")
        with self.assertRaisesRegex(ValueError, "mm/h"):
            load_input(self.path)

    def test_bad_grid_metadata(self):
        self.change(grid_resolution_m=5000)
        with self.assertRaises(ValueError):
            load_input(self.path)

    def test_fake_grid_spacing(self):
        self.change(latitude=np.full((256,256),19.0), longitude=np.full((256,256),73.0))
        with self.assertRaises(ValueError):
            load_input(self.path)

    def test_flipped_grid_is_rejected(self):
        with np.load(self.path) as z:
            self.change(latitude=z["latitude"][::-1])
        with self.assertRaisesRegex(ValueError, "south-to-north"):
            load_input(self.path)

    def test_nodata_not_treated_as_dry(self):
        rain = np.ones((4,256,256), dtype="float32")
        rain[0,0,0] = np.nan
        self.change(rain_mmh=rain)
        with self.assertRaisesRegex(ValueError, "Missing"):
            load_input(self.path)

    def test_stale_requires_archive(self):
        load_input(self.path, archive=True)
        with self.assertRaisesRegex(ValueError, "older"):
            load_input(self.path, now=datetime.now(timezone.utc)+timedelta(hours=1))

    def test_future_rejected(self):
        with self.assertRaises(ValueError):
            load_input(self.path, now=datetime.now(timezone.utc)-timedelta(hours=1))

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            parse_time("2026-01-01T10:00:00")

    def test_cadence_required(self):
        self.change(timestamps=["2026-01-01T00:00:00Z"]*4)
        with self.assertRaisesRegex(ValueError, "5 minutes"):
            load_input(self.path, archive=True)

    def test_normalization_channel_order_and_feedback(self):
        class Model:
            def predict(self, x, verbose=0):
                np.testing.assert_allclose(x[0,0,0], self.expect)
                self.expect = np.array([.2,.3,.4,.5])
                return x[..., -1:] + .1
        model = Model()
        model.expect = np.array([.1,.2,.3,.4])
        rain = np.stack([np.full((256,256), x, dtype="float32") for x in (40,80,120,160)])
        pred = nowcast(rain, model, 2)
        self.assertEqual(pred.shape, (2,256,256))
        np.testing.assert_allclose(pred[:,0,0], [200,240], rtol=1e-6)

    def test_invalid_model_output_rejected(self):
        class Model:
            def predict(self, x, verbose=0):
                return np.full((1,256,256,1), np.nan)
        with self.assertRaisesRegex(ValueError, "model output"):
            nowcast(np.zeros((4,256,256)), Model(), 1)

    def test_report_ist_threshold_and_no_guarantee(self):
        rain, lat, lon, meta, last = load_input(self.path)
        pred = np.stack([np.zeros((256,256)), np.ones((256,256))*2])
        report = make_report(pred, rain, (128,128), last, meta, city="mumbai")
        self.assertEqual(report["threshold_crossing_lead_minutes"], 10)
        self.assertTrue(report["last_observation_ist"].endswith("+05:30"))
        self.assertEqual(report["mode"], "SYNTHETIC DEMO")
        self.assertFalse(report["india_accuracy_validated"])
        pred[:] = 0
        self.assertIsNone(make_report(pred, rain, (128,128), last, meta, city="mumbai")["threshold_crossing_lead_minutes"])

    def test_archive_labeled(self):
        rain, _, _, meta, last = load_input(self.path)
        meta["synthetic"] = False
        report = make_report(rain[:1], rain, (128,128), last, meta, city="mumbai", archive=True)
        self.assertEqual(report["mode"], "ARCHIVE REPLAY")

    def test_html_source_is_escaped(self):
        rain, _, _, meta, last = load_input(self.path)
        meta["source"] = '<script>alert(1)</script>'
        report = make_report(rain[:1], rain, (128,128), last, meta, city="mumbai")
        write_report(report, self.tmp.name)
        html = (Path(self.tmp.name)/"report.html").read_text()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_cli_demo_end_to_end_without_model(self):
        self.assertEqual(main(["demo", "--city", "mumbai", "--output", self.tmp.name]), 0)
        report = json.loads((Path(self.tmp.name)/"report.json").read_text())
        self.assertIn("NOT AI", report["model"])
        self.assertEqual(len(report["forecast"]), 12)


if __name__ == "__main__":
    unittest.main()
