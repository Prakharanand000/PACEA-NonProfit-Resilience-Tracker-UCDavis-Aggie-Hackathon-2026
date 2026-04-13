# irs_990_downloader.py
# Downloads IRS Form 990 bulk XML ZIPs. Resumable, skips existing, per-year folders.

import os
import sys
import time
import requests
from pathlib import Path

# ---- CONFIG ----
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]  # edit as needed; skip 2026 (partial)
OUT_DIR = Path("./irs_990_raw")
INDEX_ONLY = False  # set True to grab ONLY the small index CSVs first (smart first step)
CHUNK = 1024 * 1024  # 1 MB
HEADERS = {"User-Agent": "Mozilla/5.0 (hackathon research script)"}

# File lists per year, scraped from irs.gov/charities-non-profits/form-990-series-downloads
FILES = {
    2026: ["2026_TEOS_XML_01A.zip"],
    2025: [f"2025_TEOS_XML_{m}.zip" for m in
           ["01A","02A","03A","04A","05A","06A","07A","08A","09A","10A",
            "11A","11B","11C","11D","12A"]],
    2024: [f"2024_TEOS_XML_{m:02d}A.zip" for m in range(1, 13)],
    2023: [f"2023_TEOS_XML_{m:02d}A.zip" for m in range(1, 13)],
    2022: ["2022_TEOS_XML_01A.zip"],
    2021: ["2021_TEOS_XML_01A.zip"],
    2020: ["2020_TEOS_XML_CT1.zip"] + [f"download990xml_2020_{i}.zip" for i in range(1, 9)],
    2019: ["2019_TEOS_XML_CT1.zip"] + [f"download990xml_2019_{i}.zip" for i in range(1, 9)],
}

BASE = "https://apps.irs.gov/pub/epostcard/990/xml/{year}/{fname}"
INDEX_URL = "https://apps.irs.gov/pub/epostcard/990/xml/{year}/index_{year}.csv"


def download(url: str, dest: Path) -> None:
    """Resumable download. Skips if file already fully present."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    # HEAD for total size
    try:
        h = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=30)
        total = int(h.headers.get("Content-Length", 0))
    except Exception as e:
        print(f"  HEAD failed ({e}); will try GET anyway")
        total = 0

    if dest.exists() and total and dest.stat().st_size == total:
        print(f"  ✓ already complete: {dest.name}")
        return

    resume_at = dest.stat().st_size if dest.exists() else 0
    headers = dict(HEADERS)
    mode = "wb"
    if resume_at and total and resume_at < total:
        headers["Range"] = f"bytes={resume_at}-"
        mode = "ab"
        print(f"  → resuming {dest.name} at {resume_at/1e6:.1f} MB")
    else:
        print(f"  → downloading {dest.name} ({total/1e9:.2f} GB)" if total else f"  → downloading {dest.name}")

    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, mode) as f:
            for chunk in r.iter_content(CHUNK):
                if chunk:
                    f.write(chunk)
    print(f"  ✓ done: {dest.name} ({dest.stat().st_size/1e9:.2f} GB)")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for year in YEARS:
        print(f"\n=== {year} ===")
        year_dir = OUT_DIR / str(year)

        # Always grab the index CSV (tiny, tells you which EIN is in which ZIP)
        idx_url = INDEX_URL.format(year=year)
        idx_dest = year_dir / f"index_{year}.csv"
        try:
            download(idx_url, idx_dest)
        except Exception as e:
            print(f"  ! index failed: {e}")

        if INDEX_ONLY:
            continue

        for fname in FILES.get(year, []):
            url = BASE.format(year=year, fname=fname)
            dest = year_dir / fname
            for attempt in range(3):
                try:
                    download(url, dest)
                    break
                except Exception as e:
                    print(f"  ! attempt {attempt+1} failed for {fname}: {e}")
                    time.sleep(5 * (attempt + 1))
            else:
                print(f"  ✗ GAVE UP on {fname}")

    print("\nAll done.")


if __name__ == "__main__":
    main()