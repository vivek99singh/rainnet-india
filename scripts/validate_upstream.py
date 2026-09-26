"""One-event inference smoke test, not an India/general skill evaluation."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from rainnet_india.core import load_model, nowcast

root = Path(__file__).resolve().parents[1]
data = np.load(root / "data/20815.npy", allow_pickle=False).astype("float32")
if not np.isfinite(data).all() or (data < 0).any():
    raise ValueError("Upstream sample contains invalid values; review before inference.")
model = load_model(root / "models/rainnet2024.keras")
start = time.perf_counter()
forecast = nowcast(data[20:24], model, steps=12)
elapsed = time.perf_counter()-start
truth = data[24:36]
baseline = np.repeat(data[23:24], 12, axis=0)
report = {
    "dataset": "Upstream German CatRaRE event 20815; held-out event supplied by upstream",
    "input_indices": [20,21,22,23], "truth_indices": list(range(24,36)),
    "forecast_shape": list(forecast.shape), "inference_seconds": round(elapsed,2),
    "model_mae_mmh": round(float(np.abs(forecast-truth).mean()),4),
    "persistence_mae_mmh": round(float(np.abs(baseline-truth).mean()),4),
    "finite": bool(np.isfinite(forecast).all()), "minimum_mmh": float(forecast.min()),
    "maximum_mmh": round(float(forecast.max()),4),
    "limitation": "Single German sample smoke test. Does not establish India skill or general superiority."
}
out = root / "output/upstream-validation"
out.mkdir(parents=True, exist_ok=True)
(out/"metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
np.save(out/"forecast_mmh.npy", forecast, allow_pickle=False)
print(json.dumps(report, indent=2))
