"""Fetch provider JSON without exposing an API key in code, URLs or output."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch(city, endpoint, key):
    if not key:
        raise ValueError("Set INDIANAPI_KEY in your local environment; do not put the key in Git or chat.")
    if endpoint not in ("india", "global"):
        raise ValueError("Unsupported endpoint")
    params = {"city": city} if endpoint == "india" else {"location": city, "days": 3}
    url = "https://weather.indianapi.in/" + endpoint + "/weather?" + urlencode(params)
    request = Request(url, headers={"x-api-key": key, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=25) as response:
            data = json.load(response)
    except HTTPError as exc:
        # Never echo arbitrary provider error bodies, which may include request details.
        raise ValueError(f"IndianAPI HTTP {exc.code}; check subscription/key, city and quota.") from None
    except URLError:
        raise ValueError("Cannot reach IndianAPI; check network and TLS connection.") from None
    if not isinstance(data, dict) or "forecast" not in (data.get("weather", {}) if endpoint == "india" else data):
        raise ValueError("Unexpected IndianAPI response; no forecast object received.")
    return {"provider": "IndianAPI (third-party service)", "endpoint": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(), "requested_city": city,
            "data": data}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", default="Mumbai")
    parser.add_argument("--endpoint", choices=("india", "global"), default="india")
    parser.add_argument("--output", type=Path, default=Path("output/indianapi/response.json"))
    args = parser.parse_args(argv)
    try:
        result = fetch(args.city, args.endpoint, os.environ.get("INDIANAPI_KEY", ""))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Provider response saved: {args.output.resolve()}")
        print("Check matched station and forecast dates before displaying as current weather.")
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
