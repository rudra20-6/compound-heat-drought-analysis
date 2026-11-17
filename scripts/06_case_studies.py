"""
Case study: the 2009 Indian monsoon (JJAS) drought -- maps of Tmax z-score,
SPEI-3, stress category, and GPP z-score, plus India-wide monthly trajectories
through the event and its aftermath (plan section 3.F, mid-eval scope).

Final phase adds the March-April 2022 NW-India heat/cropland case and 2015.

Usage:
    python scripts/06_case_studies.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import plotting as plot

CASE = cfg.REGION_CASE                 # India: Jun-Sep 2009; Australia: Sep-Dec 2019
CASE_YEAR = CASE["name"]
CASE_START = pd.Timestamp(CASE["start"] + "-01")
CASE_END = pd.Timestamp(CASE["end"] + "-01")
COUNTRY = cfg.COUNTRY_NAME


def main():
    print(f"Loading cube from {cfg.CUBE_PATH}")
    ds = xr.open_dataset(cfg.CUBE_PATH)
    india_mask = ds["is_india"].values if "is_india" in ds else None

    sel = ds.sel(time=slice(CASE_START, CASE_END))
    if sel.sizes.get("time", 0) == 0:
        print(f"No data for {CASE['label']} in the study period "
              f"({cfg.STUDY_START}-{cfg.STUDY_END}) -- skipping case study.")
        return

    for var, cmap, vmin, vmax, label in [
        ("tmax_z", "Reds", -2, 3, "Tmax z-score"),
        ("spei03", "BrBG", -2.5, 2.5, "SPEI-3"),
        ("gpp_z", "RdYlGn", -3, 3, "GPP z-score"),
    ]:
        field = sel[var].mean(dim="time", skipna=True).values
        if india_mask is not None:
            field = np.where(india_mask, field, np.nan)
        plot.plot_map(
            field, ds["lat"].values, ds["lon"].values,
            title=f"{CASE['label']}: mean {label}",
            filename=f"case_{CASE_YEAR}_{var}", cmap=cmap, vmin=vmin, vmax=vmax,
            cbar_label=label,
        )

    # Category map: most common category per cell during the case window
    cats = sel["category"].values  # (time, lat, lon), object
    cat_codes = {"normal": 0, "hot_only": 1, "dry_only": 2, "compound": 3, "nan": -1}
    coded = np.vectorize(lambda c: cat_codes.get(c, -1))(cats)
    mode_cat = np.apply_along_axis(lambda x: np.bincount(x[x >= 0], minlength=4).argmax()
                                    if np.any(x >= 0) else -1, 0, coded)
    mode_cat = mode_cat.astype(float)
    mode_cat[mode_cat < 0] = np.nan
    if india_mask is not None:
        mode_cat = np.where(india_mask, mode_cat, np.nan)
    fig, ax = plt.subplots(figsize=plot.map_figsize(ds["lat"].values, ds["lon"].values))
    extent = [ds["lon"].values.min() - 0.125, ds["lon"].values.max() + 0.125,
              ds["lat"].values.min() - 0.125, ds["lat"].values.max() + 0.125]
    from matplotlib.colors import ListedColormap
    cmap4 = ListedColormap([plot.CATEGORY_COLORS[c] for c in plot.CATEGORY_ORDER])  # exactly 4 colours
    im = ax.imshow(mode_cat, extent=extent, origin="upper", cmap=cmap4, vmin=-0.5, vmax=3.5,
                   interpolation="nearest")
    cbar = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3], shrink=0.8)
    cbar.ax.set_yticklabels(["normal", "hot-only", "dry-only", "compound"])
    ax.set_title(f"Most frequent category per cell, {CASE['label']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(cfg.FIGURES / f"case_{CASE_YEAR}_category.png", dpi=300, bbox_inches="tight")

    # Numbers quoted on the case-study slide
    act = sel["active_season"].values
    shares = {c: 100.0 * ((cats == c) & act).sum() / act.sum()
              for c in ("normal", "hot_only", "dry_only", "compound")}
    print(f"{CASE['label']}, share of active {COUNTRY} cell-months (%):",
          {k: round(v, 1) for k, v in shares.items()})
    win = ds.sel(time=slice(CASE_START - pd.DateOffset(months=12), CASE_END + pd.DateOffset(months=9)))
    india_da = ds["is_india"]
    monthly = pd.DataFrame({
        "month": pd.DatetimeIndex(win["time"].values).strftime("%Y-%m"),
        "tmax_z": win["tmax_z"].where(india_da).mean(["lat", "lon"]).values,
        "spei03": win["spei03"].where(india_da).mean(["lat", "lon"]).values,
        "gpp_z_active": win["gpp_z"].where(india_da & win["active_season"]).mean(["lat", "lon"]).values,
        "ndvi_z_active": win["ndvi_z"].where(india_da & win["active_season"]).mean(["lat", "lon"]).values,
    })
    monthly.to_csv(cfg.RESULTS / f"case_{CASE_YEAR}_{cfg.REGION}_monthly.csv", index=False)
    pd.DataFrame([shares]).to_csv(cfg.RESULTS / f"case_{CASE_YEAR}_category_shares.csv", index=False)
    print(monthly.round(2).to_string(index=False))

    # India-wide monthly trajectory, 2008-01 through 2011-12, for context
    traj_window = ds.sel(time=slice(f"{CASE_START.year-1}-01-01", f"{min(CASE_START.year+2, cfg.STUDY_END)}-12-01"))

    def _india_mean(da):
        if india_mask is not None:
            da = da.where(india_mask)
        return da.mean(dim=["lat", "lon"], skipna=True)

    tmax_traj = _india_mean(traj_window["tmax_z"]).values
    spei_traj = _india_mean(traj_window["spei03"]).values
    gpp_traj = _india_mean(traj_window["gpp_z"]).values
    dates = pd.DatetimeIndex(traj_window["time"].values)

    plot.plot_qc_timeseries(
        dates, {"Tmax z": tmax_traj, "SPEI-3": spei_traj, "GPP z": gpp_traj},
        title=f"{COUNTRY}-wide trajectory around the {CASE['label']}",
        filename=f"case_{CASE_YEAR}_trajectory",
        shade_spans=[(CASE_START, CASE_END + pd.offsets.MonthEnd(0))],
    )

    print(f"\nDone. Figures in {cfg.FIGURES}.")


if __name__ == "__main__":
    main()
