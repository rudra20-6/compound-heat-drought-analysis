"""
Resumable fetch loop: pulls every variable, year by year, from Earth Engine,
and caches results as .npz under data/raw/. Already-cached variable-years
are skipped, so this script can be killed and restarted freely.

Usage:
    export EE_PROJECT=your-gcp-project-id
    python scripts/01_fetch.py                  # fetch everything
    python scripts/01_fetch.py --only era5       # fetch one dataset only
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import gee
from chd.gee import init_ee, with_retry


def _cache_path(name: str, year: int) -> Path:
    return cfg.DATA_RAW / f"{name}_{year}.npz"


def _already_cached(name: str, year: int) -> bool:
    return _cache_path(name, year).exists()


def fetch_era5(ee, start_year, end_year):
    for year in range(start_year, end_year + 1):
        if _already_cached("era5", year):
            continue
        monthly = {k: np.full((12, cfg.N_LAT, cfg.N_LON), np.nan)
                   for k in ["tmax_k", "t2m_k", "dewpoint_k", "swvl1", "swvl2", "swvl3"]}
        for m in range(1, 13):
            result = with_retry(gee.fetch_era5_land_month, ee, year, m)
            for k, v in result.items():
                monthly[k][m - 1] = v
            print(f"  era5 {year}-{m:02d} done")
        np.savez_compressed(_cache_path("era5", year), **monthly)
        print(f"era5 {year} cached.")


def fetch_chirps(ee, start_year, end_year):
    for year in range(start_year, end_year + 1):
        if _already_cached("chirps", year):
            continue
        monthly = np.full((12, cfg.N_LAT, cfg.N_LON), np.nan)
        for m in range(1, 13):
            monthly[m - 1] = with_retry(gee.fetch_chirps_month, ee, year, m)
            print(f"  chirps {year}-{m:02d} done")
        np.savez_compressed(_cache_path("chirps", year), precip=monthly)
        print(f"chirps {year} cached.")


def fetch_spei(ee, start_year, end_year):
    for year in range(start_year, end_year + 1):
        if _already_cached("spei", year):
            continue
        monthly = {f"spei_{ts:02d}": np.full((12, cfg.N_LAT, cfg.N_LON), np.nan)
                   for ts in (1, 3, 6)}
        for m in range(1, 13):
            for ts in (1, 3, 6):
                monthly[f"spei_{ts:02d}"][m - 1] = with_retry(gee.fetch_spei_month, ee, year, m, ts)
            print(f"  spei {year}-{m:02d} done")
        np.savez_compressed(_cache_path("spei", year), **monthly)
        print(f"spei {year} cached.")


def fetch_gpp(ee, start_year, end_year, source):
    for year in range(start_year, end_year + 1):
        if _already_cached("gpp", year):
            continue
        monthly = with_retry(gee.fetch_modis_gpp_year, ee, year, source)
        np.savez_compressed(_cache_path("gpp", year), gpp=monthly,
                            monthly_method=np.array(cfg.GPP_MONTHLY_METHOD))
        print(f"gpp {year} cached.")


def fetch_ndvi(ee, start_year, end_year):
    for year in range(start_year, end_year + 1):
        if _already_cached("ndvi", year):
            continue
        result = with_retry(gee.fetch_modis_ndvi_year, ee, year)
        np.savez_compressed(_cache_path("ndvi", year), ndvi=result["ndvi"], qa=result["qa"])
        print(f"ndvi {year} cached.")


def fetch_static(ee):
    if not _already_cached("worldcover", 0):
        fractions = with_retry(gee.fetch_worldcover_fractions, ee)
        np.savez_compressed(_cache_path("worldcover", 0), **fractions)
        print("worldcover cached.")
    if not _already_cached("india_mask", 0):
        mask = with_retry(gee.fetch_india_mask, ee)
        np.savez_compressed(_cache_path("india_mask", 0), india=mask)
        print("india_mask cached.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["era5", "chirps", "spei", "gpp", "ndvi", "static"],
                         default=None)
    args = parser.parse_args()

    ee = init_ee()
    gpp_source_path = cfg.DATA_PROCESSED / "gpp_source.txt"
    gpp_source = gpp_source_path.read_text().strip() if gpp_source_path.exists() else "mod17"

    jobs = {
        "era5": lambda: fetch_era5(ee, cfg.FETCH_START, cfg.FETCH_END),
        "chirps": lambda: fetch_chirps(ee, cfg.FETCH_START, cfg.FETCH_END),
        "spei": lambda: fetch_spei(ee, cfg.FETCH_START, cfg.FETCH_END),
        "gpp": lambda: fetch_gpp(ee, cfg.GPP_START, cfg.GPP_END, gpp_source),
        "ndvi": lambda: fetch_ndvi(ee, cfg.NDVI_START, cfg.NDVI_END),
        "static": lambda: fetch_static(ee),
    }

    to_run = [args.only] if args.only else list(jobs.keys())
    for name in to_run:
        print(f"\n=== Fetching {name} ===")
        t0 = time.time()
        jobs[name]()
        print(f"=== {name} done in {time.time()-t0:.1f}s ===")


if __name__ == "__main__":
    main()
