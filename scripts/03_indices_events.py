"""
Load the cube (data/processed/cube.nc), segment per-cell drought/heat events
(saved to data/processed/events.csv), and run analysis A: event-category
frequency maps (study period) and the trend in the compound share of
active-season India cell-months over the FULL climate record 1991-2024
(Sen's slope + Mann-Kendall) -- plan section 3.6.A, hypothesis H5.

Usage:
    python scripts/03_indices_events.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import plotting as plot
from chd.recovery import build_all_events
from chd.stats import sen_slope_mk_trend


def main():
    print(f"Loading cube from {cfg.CUBE_PATH}")
    ds = xr.open_dataset(cfg.CUBE_PATH)

    # ---- Event segmentation (active-season India cells only) ----
    print("Segmenting drought/heat events per cell (this iterates every grid cell)...")
    events = build_all_events(ds)
    events.to_csv(cfg.EVENTS_PATH, index=False)
    print(f"Saved {len(events)} events to {cfg.EVENTS_PATH}")

    # Event-type confound check: are compound droughts longer / more severe?
    summary = events.groupby("event_type").agg(
        n=("event_type", "size"),
        median_duration=("duration_months", "median"),
        median_severity=("severity", "median"),
        median_min_gpp_z=("min_gpp_z", "median"),
        pct_with_impact=("has_impact", "mean"),
    )
    summary["pct_with_impact"] *= 100
    summary.to_csv(cfg.RESULTS / "event_type_summary.csv")
    print("\nEvent types (medians):")
    print(summary.round(2))

    # ---- Analysis A: category frequency maps (study period) ----
    india_mask = ds["is_india"].values
    active = ds["active_season"].values
    category = ds["category"].values  # (time, lat, lon), object dtype
    n_active = active.sum(axis=0).astype(float)

    for cat in ["normal", "hot_only", "dry_only", "compound"]:
        with np.errstate(invalid="ignore", divide="ignore"):
            freq = ((category == cat) & active).sum(axis=0) / n_active  # share of ACTIVE months
        freq = np.where(india_mask & (n_active > 0), freq, np.nan)
        plot.plot_map(
            freq, ds["lat"].values, ds["lon"].values,
            title=f"Share of active months that are '{cat}'\n({cfg.STUDY_START}-{cfg.STUDY_END})",
            filename=f"freq_map_{cat}", cmap="YlOrRd" if cat != "normal" else "Blues",
            cbar_label="fraction of active-season months",
        )

    shares = {cat: float(((category == cat) & active).sum() / active.sum()) for cat in
              ["normal", "hot_only", "dry_only", "compound"]}
    pd.DataFrame([shares]).to_csv(cfg.RESULTS / "category_shares_active.csv", index=False)
    print("Share of active cell-months per category:", {k: round(100 * v, 1) for k, v in shares.items()})

    # ---- Analysis A: trend over the FULL climate record (1991-2024) ----
    # Same seasonal/vegetation/India mask as the impact analysis (active_by_month),
    # applied to every year of the climate record.
    cat_full = ds["category_full"]  # (era5_time, lat, lon)
    full_months = cat_full["era5_time"].dt.month.values
    full_years = cat_full["era5_time"].dt.year.values
    act_bm = ds["active_by_month"].transpose("month", "lat", "lon").values  # month 1..12
    active_full = act_bm[full_months - 1]
    compound_full = (cat_full.transpose("era5_time", "lat", "lon").values == "compound") & active_full

    rows = []
    for year in np.unique(full_years):
        ymask = full_years == year
        n_act = active_full[ymask].sum()
        rows.append({"year": int(year),
                     "pct_area": 100.0 * compound_full[ymask].sum() / n_act if n_act else np.nan})
    year_pct_df = pd.DataFrame(rows)
    year_pct_df.to_csv(cfg.RESULTS / "compound_area_trend.csv", index=False)

    trend = sen_slope_mk_trend(year_pct_df["year"].values, year_pct_df["pct_area"].values)
    pd.DataFrame([trend]).to_csv(cfg.RESULTS / "compound_area_trend_stats.csv", index=False)
    print(f"\nTrend {full_years.min()}-{full_years.max()} in % of active {cfg.COUNTRY_NAME} cell-months that are "
          f"compound: slope={trend['slope']:.3f} pct-points/yr "
          f"[{trend['slope_ci_low']:.3f}, {trend['slope_ci_high']:.3f}], "
          f"tau={trend['tau']:.3f}, p={trend['p_value']:.4f}")
    top = year_pct_df.sort_values("pct_area", ascending=False).head(5)
    print("Top-5 compound years:")
    print(top.to_string(index=False))

    plot.plot_area_trend(
        year_pct_df, trend,
        title=f"Compound share of active-season {cfg.COUNTRY_NAME} cell-months, {full_years.min()}-{full_years.max()}",
        filename="compound_area_trend",
    )

    print(f"\nDone. Figures in {cfg.FIGURES}, tables in {cfg.RESULTS}.")


if __name__ == "__main__":
    main()
