"""Download the upstream regression model with publisher checksum verification."""
import hashlib
from pathlib import Path
import urllib.request

URL = "https://zenodo.org/records/12547127/files/rainnet2024.keras?download=1"
CHECKSUM = "d65444a42821655e31217c808aa59a9d"


def main():
    target = Path(__file__).resolve().parents[1] / "models" / "rainnet2024.keras"
    if target.exists():
        print("Model already exists; inference will verify its checksum.")
        return
    partial = target.with_suffix(".part")
    h = hashlib.md5(usedforsecurity=False)
    request = urllib.request.Request(URL, headers={"User-Agent": "rainnet-india-research/0.1"})
    with urllib.request.urlopen(request, timeout=120) as src, partial.open("wb") as dst:
        while chunk := src.read(1024 * 1024):
            h.update(chunk)
            dst.write(chunk)
    if h.hexdigest() != CHECKSUM:
        raise RuntimeError("Downloaded artifact failed the publisher checksum; .part retained, not loaded.")
    partial.replace(target)
    print("Downloaded and verified", target.name)


if __name__ == "__main__":
    main()
