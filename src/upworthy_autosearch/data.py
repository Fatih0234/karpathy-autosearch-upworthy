"""Download and cache raw Upworthy Research Archive CSVs."""
from __future__ import annotations

import os
from pathlib import Path

import requests
from tqdm import tqdm

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"

DATASETS = {
    "exploratory": "https://osf.io/download/3vqmp/",
    "confirmatory": "https://osf.io/download/vy8mj/",
}


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """Stream-download *url* to *dest* with a tqdm progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)) or None
        with open(dest, "wb") as f, tqdm(
            desc=dest.name,
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                bar.update(len(chunk))


def ensure_raw_data() -> dict[str, Path]:
    """Return paths to raw CSVs, downloading if missing."""
    paths: dict[str, Path] = {}
    for name, url in DATASETS.items():
        dest = RAW_DIR / f"{name}.csv"
        if not dest.exists():
            print(f"Downloading {name} dataset …")
            download_file(url, dest)
        else:
            print(f"Found cached {name} dataset at {dest}")
        paths[name] = dest
    return paths


if __name__ == "__main__":
    ensure_raw_data()
