"""
Build the analysis cube from the cached data/raw/*.npz files (no Earth Engine
calls) and save it to data/processed/cube.nc. Prints data-quality checks:

  - how many grid cells are inside India and how many have growing-season months
  - share of NDVI cell-months removed by the MODIS quality mask
  - whether known Indian droughts (2002, 2009, 2014, 2015) and pre-monsoon
    heatwaves (2010, 2022) show up in the inputs

Usage:
    python scripts/02_build_cube.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import cube

KNOWN_DROUGHT_YEARS = [2002, 2009, 2014, 2015]
KNOWN_HEAT_YEARS = [2010, 2022]


def main():
    print("Building the cube from cached data (SPI fitting takes a few minutes)...")
    ds, full = cube.build_full_cube(return_climate=True)
    print(f"Cube built: dims={dict(ds.sizes)}")
    ds.to_netcdf(cfg.CUBE_PATH, engine="netcdf4")
    print(f"Saved to {cfg.CUBE_PATH}")

    # ---- what goes into the statistics ----
    india = ds["is_india"].values
    active = ds["active_season"].values
    print(f"\nIndia cells (>=50% inside India): {int(india.sum())}")
    print(f"Cells with any growing-season month: {int(active.any(axis=0).sum())} "
          f"(outside India: {int((active.any(axis=0) & ~india).sum())}, must be 0)")
    print(f"Growing-season cell-months: {int(active.sum())}")
    nd_raw = ds["ndvi"].values[active]
    nd_clean = ds["ndvi_clean"].values[active]
    removed = (np.isnan(nd_clean) & ~np.isnan(nd_raw)).sum() / (~np.isnan(nd_raw)).sum()
    print(f"NDVI growing-season cell-months removed by the QA mask: {100 * removed:.1f}%")

    # ---- do the inputs reproduce known events? ----
    india_da = full["is_india"]
    month = full["era5_time"].dt.month

    def india_mean(da):
        return da.where(india_da).mean(dim=["lat", "lon"], skipna=True)

    sep_spei = india_mean(full["spei03"].where(month == 9)).groupby("era5_time.year").mean()
    mam_tmax = india_mean(full["tmax_z"].where(month.isin([3, 4, 5]))).groupby("era5_time.year").mean()
    n_years = len(sep_spei)

    print("\nIndia-mean SPEI-3 at the end of the monsoon (Sep) in known drought years:")
    for y in KNOWN_DROUGHT_YEARS:
        val = float(sep_spei.sel(year=y))
        rank = int((sep_spei.values < val).sum()) + 1
        print(f"  {y}: {val:+.2f}  (rank {rank} driest of {n_years})")
    print("India-mean pre-monsoon (Mar-May) Tmax z in known heat years:")
    for y in KNOWN_HEAT_YEARS:
        val = float(mam_tmax.sel(year=y))
        rank = int((mam_tmax.values > val).sum()) + 1
        print(f"  {y}: {val:+.2f}  (rank {rank} hottest of {n_years})")


if __name__ == "__main__":
    main()
