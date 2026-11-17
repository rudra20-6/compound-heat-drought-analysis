"""
Impact & synergy analysis (plan sections 3.B/3.C, hypotheses H1/H2/H4):

  - category composites (GPP, NDVI) with year-block bootstrap CIs
  - joint-bootstrap contrasts with 95% CIs: each category vs normal,
    compound vs dry-only, compound vs hot-only, amplification index (AI)
  - the same contrasts by dominant land cover and by region
  - robustness: drought defined by SPI-3 (CHIRPS, temperature-free) instead
    of SPEI-3 (whose PET term depends on temperature)
  - Tmax-z x SPEI-3 response surface, and a soil-moisture / VPD mechanism check

All statistics use active-season cell-months inside India only.

Usage:
    python scripts/04_impacts.py
"""
import sys
from pathlib import Path

import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import plotting as plot
from chd.impacts import (
    cube_to_long_table, category_composites, category_contrasts,
    response_surface, mechanism_check, region_difference_test,
)

SHOW = ["n_normal", "n_hot_only", "n_dry_only", "n_compound",
        "mean_normal", "mean_hot_only", "mean_dry_only", "mean_compound",
        "compound_minus_dry", "compound_minus_dry_ci_low", "compound_minus_dry_ci_high",
        "amplification_index", "amplification_index_ci_low", "amplification_index_ci_high",
        "amplification_index_sig"]


def main():
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    print(f"Loading cube from {cfg.CUBE_PATH}")
    ds = xr.open_dataset(cfg.CUBE_PATH)

    df = cube_to_long_table(ds, response_vars=("gpp_z", "ndvi_z"))
    print(f"Long table: {len(df)} active {cfg.COUNTRY_NAME} cell-months, {df['cell_id'].nunique()} cells, "
          f"years {df['year'].min()}-{df['year'].max()}")
    print(df["category"].value_counts())

    # ---- H1: composites ----
    for response_var, label in [("gpp_z", "GPP z-score"), ("ndvi_z", "NDVI z-score")]:
        comp = category_composites(df, response_var)
        comp.to_csv(cfg.RESULTS / f"composite_{response_var}_overall.csv", index=False)
        plot.plot_category_composite(comp, label, f"Mean {label} by stress category ({cfg.COUNTRY_NAME})",
                                     f"composite_{response_var}_overall")
        print(f"\n{response_var} composites:\n{comp.round(3)}")

    # ---- H1/H2: contrasts with joint-bootstrap CIs ----
    for response_var in ("gpp_z", "ndvi_z"):
        overall = category_contrasts(df, response_var)
        overall.to_csv(cfg.RESULTS / f"contrasts_{response_var}_overall.csv", index=False)
        print(f"\n{response_var} contrasts (overall):\n{overall[SHOW].round(3).T}")

        sub_regions = df[df["region"].isin([cfg.SUBREGION["region_a"], cfg.SUBREGION["region_b"]])]
        for group, fname, data in [("dominant_landcover", "landcover", df), ("region", "region", sub_regions),
                                   ("season", "season", df)]:
            res = category_contrasts(data, response_var, group_cols=[group])
            res.to_csv(cfg.RESULTS / f"contrasts_{response_var}_by_{fname}.csv", index=False)
            print(f"\n{response_var} contrasts by {group}:\n{res[[group] + SHOW].round(3).to_string()}")
            if response_var == "gpp_z":
                plot.plot_amplification_by_stratum(
                    res, group, f"Amplification index by {fname} (GPP, 95% CI)",
                    f"amplification_by_{fname}")

    # ---- H4: is one sub-region more sensitive than the other? ----
    reg = pd.concat([region_difference_test(df, v) for v in ("gpp_z", "ndvi_z")], ignore_index=True)
    reg.to_csv(cfg.RESULTS / "subregion_difference_test.csv", index=False)
    if cfg.REGION == "india":
        reg.to_csv(cfg.RESULTS / "peninsular_vs_north_test.csv", index=False)
    print(f"\n{cfg.SUBREGION['region_a']} minus {cfg.SUBREGION['region_b']}, effect vs normal:")
    print(reg.round(3).to_string())

    # ---- Robustness: temperature-free drought index (SPI-3 instead of SPEI-3) ----
    if "category_spi" in df.columns:
        df_spi = df[df["category_spi"] != "nan"].dropna(subset=["category_spi"])
        rows = []
        for response_var in ("gpp_z", "ndvi_z"):
            for idx, sub, col in [("SPEI-3", df, "category"), ("SPI-3", df_spi, "category_spi")]:
                r = category_contrasts(sub, response_var, category_col=col).iloc[0].to_dict()
                r.update({"response": response_var, "drought_index": idx})
                rows.append(r)
        rob = pd.DataFrame(rows)
        rob.to_csv(cfg.RESULTS / "robustness_spei_vs_spi.csv", index=False)
        print("\nRobustness (SPEI-3 vs SPI-3):")
        print(rob[["response", "drought_index"] + SHOW].round(3).to_string())

    # ---- Response surface + mechanism ----
    surf = response_surface(df, "gpp_z")
    surf.to_csv(cfg.RESULTS / "response_surface_gpp.csv", index=False)
    plot.plot_response_surface(surf, "GPP z-score", "GPP response surface: Tmax-z x SPEI-3",
                               "response_surface_gpp")
    surf_n = response_surface(df, "ndvi_z")
    surf_n.to_csv(cfg.RESULTS / "response_surface_ndvi.csv", index=False)
    plot.plot_response_surface(surf_n, "NDVI z-score", "NDVI response surface: Tmax-z x SPEI-3",
                               "response_surface_ndvi")

    # Long table for the cross-country comparison (08_compare_countries.py)
    keep = ["year", "time", "cell_id", "lat", "lon", "category", "category_spi", "tmax_z", "spei03", "spi03",
            "sm_z", "vpd_z", "gpp_z", "ndvi_z", "dominant_landcover", "region", "season"]
    df[[c for c in keep if c in df.columns]].to_pickle(cfg.DATA_PROCESSED / "long_table.pkl")

    mech = mechanism_check(df)
    mech.to_csv(cfg.RESULTS / "mechanism_check.csv", index=False)
    print(f"\nMechanism check (soil moisture / VPD by category):\n{mech.round(3)}")

    print(f"\nDone. Figures in {cfg.FIGURES}, tables in {cfg.RESULTS}.")


if __name__ == "__main__":
    main()
