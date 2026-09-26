import argparse
import html
import json
from pathlib import Path
import sys

import numpy as np

from .core import CITIES, load_input, load_model, location_cell, make_report, nowcast, synthetic_input


def write_report(report, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    esc = html.escape
    rows = "".join(f'<tr><td>{esc(r["valid_at_ist"])}</td><td>{r["rate_mmh"]}</td></tr>' for r in report["forecast"])
    crossing = report["threshold_crossing_lead_minutes"]
    status = "No threshold crossing in this forecast window" if crossing is None else f"Threshold reached at +{crossing} minutes from last scan"
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>RainNet India research report</title><style>
body{{background:#111827;color:#e5e7eb;font:18px system-ui;max-width:850px;margin:40px auto;padding:20px}}
.badge{{background:#fbbf24;color:#111827;padding:12px;font-weight:bold}} h1{{font-size:42px}} td,th{{padding:12px;text-align:left;border-bottom:1px solid #374151}}
table{{width:100%}} small{{color:#cbd5e1}}</style>
<p class="badge">{esc(report['mode'])} · INDIA ACCURACY NOT VALIDATED</p>
<h1>RainNet India · {esc(report['location'])}</h1><p>{esc(status)}</p>
<p>Backend: {esc(report['model'])} · threshold {report['threshold_mmh']} mm/h</p>
<p>Observation: {esc(report['last_observation_ist'])} (IST)</p>
<p>{esc(report['interpretation'])}</p><table><tr><th>Forecast valid at (IST)</th><th>Rain rate (mm/h)</th></tr>{rows}</table>
<p>{esc(report['warning'])}</p><small>Source: {esc(report['source'])}</small></html>'''
    (directory / "report.html").write_text(page, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Indian city weather forecasts and experimental RainNet radar research.")
    sub = parser.add_subparsers(dest="command", required=True)
    weather = sub.add_parser("weather", help="Fetch current city forecast from Open-Meteo; no RainNet model needed")
    weather.add_argument("--city", choices=CITIES, default="mumbai")
    weather.add_argument("--output", type=Path, default=Path("output/weather"))
    demo = sub.add_parser("demo", help="Synthetic field + persistence baseline, no AI or network")
    demo.add_argument("--city", choices=CITIES, default="mumbai")
    demo.add_argument("--output", type=Path, default=Path("output/demo"))
    run = sub.add_parser("predict", help="Run published Germany-trained RainNet model on prepared Indian radar grids")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--model", type=Path, default=Path("models/rainnet2024.keras"))
    run.add_argument("--city", choices=CITIES, default="mumbai")
    run.add_argument("--steps", type=int, choices=range(1,13), default=12)
    run.add_argument("--threshold-mmh", type=float, default=1.0)
    run.add_argument("--archive", action="store_true", help="Allow old data; outputs marked archive replay")
    run.add_argument("--output", type=Path, default=Path("output/prediction"))
    args = parser.parse_args(argv)
    try:
        if args.command == "weather":
            from .weather import run_weather
            path = run_weather(args.city, args.output)
            print(f"Open-Meteo forecast for {args.city}; hourly weather, not radar AI.")
            print(f"Report: {path.resolve()}")
            return 0
        if args.command == "demo":
            path = args.output / "synthetic_input.npz"
            synthetic_input(path, args.city)
            rain, lat, lon, meta, last = load_input(path)
            pred = np.repeat(rain[-1:,:,:], 12, axis=0)
            backend = "persistence baseline (NOT AI)"
        else:
            rain, lat, lon, meta, last = load_input(args.input, archive=args.archive)
            # Fail on uncovered locations before loading the 310 MB model.
            location_cell(lat, lon, CITIES[args.city])
            pred = nowcast(rain, load_model(args.model), args.steps)
            backend = "RainNet2024 regression (Germany-trained)"
        report = make_report(pred, rain, location_cell(lat, lon, CITIES[args.city]), last, meta,
                             city=args.city, threshold=getattr(args, "threshold_mmh", 1.0),
                             archive=getattr(args, "archive", False), backend=backend)
        write_report(report, args.output)
        np.save(args.output / "forecast_mmh.npy", pred, allow_pickle=False)
        print(f"{report['mode']} | {report['location']} | {backend}")
        print("India accuracy NOT validated; see official IMD warnings.")
        if report["threshold_crossing_lead_minutes"] is not None:
            print("LOCAL RESEARCH ALERT: rain-rate threshold crossed; consider an umbrella.")
        else:
            print("No threshold crossing in this window; this is not an all-clear.")
        print(f"Report: {(args.output / 'report.html').resolve()}")
        return 0
    except (ValueError, KeyError, OSError, ImportError) as exc:
        print(f"Cannot produce forecast: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
