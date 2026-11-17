"""
Build the full analysis cube from cached data/raw/*.npz files (no GEE calls),
save it to data/processed/cube.nc, and generate the data-QC figures:
  - all-India JJAS rainfall anomaly and Tmax anomaly time series, checked
    against known Indian drought/heat years (2002, 2009, 2014, 2015 droughts;
    2010, 2022 heat)
  - GPP climatology map (sanity: high in Western Ghats/NE, low in Thar desert)

Usage:
    python scripts/02_build_cube.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import cube
from chd import plotting as plot

KNOWN_DROUGHT_YEARS = [2002, 2009, 2014, 2015]
KNOWN_HEAT_YEARS = [2010, 2022]


def main():
    print("Building full cube from cached data...")
    ds, full = cube.build_full_cube(return_climate=True)
    print(f"Cube built: dims={dict(ds.sizes)}")

    print(f"Saving to {cfg.CUBE_PATH}")
    ds.to_netcdf(cfg.CUBE_PATH, engine="netcdf4")

    # ---- QC 0: what actually goes into the statistics ----
    india = ds["is_india"].values
    active = ds["active_season"].values
    print(f"{cfg.COUNTRY_NAME} cells (>=50% inside): {int(india.sum())}")
    print(f"Cells with any active month: {int(active.any(axis=0).sum())} "
          f"(outside {cfg.COUNTRY_NAME}: {int((active.any(axis=0) & ~india).sum())} -- must be 0)")
    nd_raw = ds["ndvi"].values[active]
    nd_clean = ds["ndvi_clean"].values[active]
    print(f"NDVI active cell-months removed by QA mask: "
          f"{100 * (np.isnan(nd_clean) & ~np.isnan(nd_raw)).sum() / (~np.isnan(nd_raw)).sum():.1f}%")

    # ---- QC 1: country-wide anomalies vs. known drought and heat years ----
    import matplotlib.pyplot as plt
    clim_time = "era5_time"
    country_da = full["is_india"]   # holds the selected region's country mask
    qc = cfg.REGION_QC
    country = cfg.COUNTRY_NAME

    def _country_mean(da):
        return da.where(country_da).mean(dim=["lat", "lon"], skipna=True)

    month = full[clim_time].dt.month
    if qc["drought_month"] is not None:
        spei_sel = full["spei03"].where(month == qc["drought_month"])
    else:
        spei_sel = full["spei03"]
    yr_spei = _country_mean(spei_sel).groupby(f"{clim_time}.year").mean()
    yr_tmax = _country_mean(full["tmax_z"].where(month.isin(list(qc["heat_months"]))))         .groupby(f"{clim_time}.year").mean()
    years_full = yr_spei["year"].values

    qc_rows = []
    print(f"QC check -- {country}-mean {qc['drought_label']} in known drought years:")
    for y in qc["drought_years"]:
        val = float(yr_spei.sel(year=y))
        rank = int((yr_spei.values < val).sum()) + 1
        ok = val < 0
        qc_rows.append({"check": "drought", "year": y, "value": val, "rank": rank,
                        "of": len(years_full), "ok": ok})
        print(f"  {y}: {val:+.2f}  (rank {rank} driest of {len(years_full)})  "
              f"[{'OK' if ok else 'UNEXPECTED'}]")
    print(f"QC check -- {country}-mean {qc['heat_label']} in known heat years:")
    for y in qc["heat_years"]:
        val = float(yr_tmax.sel(year=y))
        rank = int((yr_tmax.values > val).sum()) + 1
        ok = val > 0
        qc_rows.append({"check": "heat", "year": y, "value": val, "rank": rank,
                        "of": len(years_full), "ok": ok})
        print(f"  {y}: {val:+.2f}  (rank {rank} hottest of {len(years_full)})  "
              f"[{'OK' if ok else 'UNEXPECTED'}]")
    pd.DataFrame(qc_rows).to_csv(cfg.RESULTS / "qc_known_events.csv", index=False)
    pd.DataFrame({"year": years_full, "spei03": yr_spei.values, "tmax_z": yr_tmax.values})         .to_csv(cfg.RESULTS / "qc_yearly_series.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(9, 5.5), sharex=True)
    axes[0].bar(years_full, yr_spei.values,
                color=["#B23A48" if y in qc["drought_years"] else "#9aa7b8" for y in years_full])
    axes[0].set_ylabel("SPEI-3")
    axes[0].set_title(f"{country}-mean {qc['drought_label']} (red = known drought years)", fontsize=10)
    axes[1].bar(years_full, yr_tmax.values,
                color=["#E89A2E" if y in qc["heat_years"] else "#9aa7b8" for y in years_full])
    axes[1].set_ylabel("Tmax z")
    axes[1].set_title(f"{country}-mean {qc['heat_label']} (orange = known heat years)", fontsize=10)
    for ax in axes:
        ax.axhline(0, color="black", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(cfg.FIGURES / "qc_known_events.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # ---- QC 2: GPP climatology map ----
    gpp_clim = ds["gpp_gC_m2"].mean(dim="time", skipna=True)
    plot.plot_map(
        gpp_clim.values, ds["lat"].values, ds["lon"].values,
        title="Mean GPP 2001-2022 (gC/m^2/month)",
        filename="qc_gpp_climatology", cmap="YlGn", cbar_label="gC/m^2/month",
    )

    plot.plot_study_area(ds)

    # ---- QC 3: sample size per category (flag strata with n<30) ----
    cat_counts = pd.Series(ds["category"].values.ravel()).value_counts()
    print("\nCell-month counts per category (all months, before active-season filter):")
    print(cat_counts)
    act_counts = pd.Series(ds["category"].values[ds["active_season"].values]).value_counts()
    act_counts.rename("n").to_csv(cfg.RESULTS / "category_counts_active.csv")
    pd.DataFrame([{"country_cells": int(india.sum()), "cells_with_active_month": int(active.any(axis=0).sum()),
                   "active_cell_months": int(active.sum())}]).to_csv(cfg.RESULTS / "study_area_counts.csv", index=False)

    print(f"\nDone. Cube saved to {cfg.CUBE_PATH}. QC figures in {cfg.FIGURES}.")


if __name__ == "__main__":
    main()
