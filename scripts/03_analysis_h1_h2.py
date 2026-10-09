"""
All analyses and figures shown in the mid-evaluation slides (H1 and H2).
Same steps as analysis.ipynb, without the explanations.

Reads data/processed/cube.nc (from scripts/02_build_cube.py) and writes
tables to results/ and the six slide figures to figures/.

Usage:
    python scripts/03_analysis_h1_h2.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import impacts
from chd import plotting as plot


def main():
    pd.set_option("display.width", 200)
    ds = xr.open_dataset(cfg.CUBE_PATH)
    df = impacts.cube_to_long_table(ds)

    # ---- study area ----
    india = ds["is_india"].values
    crop = ds["frac_cropland"].values
    fracs = np.nan_to_num(np.stack([ds[c].values for c in ds.data_vars if c.startswith("frac_")]))
    crop_dominant = india & (np.nan_to_num(crop) >= cfg.THRESH.landcover_purity) & (np.nan_to_num(crop) == fracs.max(0))
    print(f"India cells: {int(india.sum())}; cropland-dominant: {100 * crop_dominant.sum() / india.sum():.1f}%")
    plot.plot_study_area(ds)

    # ---- the four boxes ----
    counts = impacts.category_counts(df)
    counts.to_csv(cfg.RESULTS / "category_counts.csv", index=False)
    print(f"\nGrowing-season cell-months: {len(df)}\n{counts.round(1).to_string(index=False)}")

    # ---- where compound months happen ----
    freq = impacts.compound_frequency(ds)
    plot.plot_compound_frequency(freq, ds["lat"].values, ds["lon"].values)
    comp = df[df["category"] == "compound"]
    print(f"Compound cell-months north / south of {cfg.PENINSULAR_LAT_MAX:.0f}N (sample size only): "
          f"{int((comp['lat'] > cfg.PENINSULAR_LAT_MAX).sum())} / {int((comp['lat'] <= cfg.PENINSULAR_LAT_MAX).sum())}")

    # ---- H1: composites and contrasts ----
    contrasts = {}
    for v, label in [("gpp_z", "GPP z-score"), ("ndvi_z", "NDVI z-score")]:
        compo = impacts.category_composites(df, v)
        compo.to_csv(cfg.RESULTS / f"composite_{v}_overall.csv", index=False)
        plot.plot_category_composite(compo, label, f"Mean {label} by stress category (India)",
                                     f"composite_{v}_overall")
        print(f"\n{v} composites:\n{compo.round(3).to_string(index=False)}")
        contrasts[v] = impacts.category_contrasts(df, v)
        contrasts[v].to_csv(cfg.RESULTS / f"contrasts_{v}_overall.csv", index=False)
        print(contrasts[v].round(3).T.to_string())

    # ---- H1 and H2 with SPI-3 instead of SPEI-3 ----
    rob = impacts.robustness_spei_vs_spi(df)
    rob.to_csv(cfg.RESULTS / "robustness_spei_vs_spi.csv", index=False)
    print("\nSPEI-3 vs SPI-3:")
    print(rob[["response", "drought_index", "compound_minus_dry", "compound_minus_dry_ci_low",
               "compound_minus_dry_ci_high", "amplification_index", "amplification_index_ci_low",
               "amplification_index_ci_high"]].round(2).to_string(index=False))

    # ---- why? soil moisture and VPD ----
    mech = impacts.mechanism_check(df)
    mech.to_csv(cfg.RESULTS / "mechanism_check.csv", index=False)
    print(f"\nMechanism check:\n{mech.round(2).to_string(index=False)}")

    # ---- H2: additivity figure and response surface ----
    plot.plot_additivity(contrasts)
    surf = impacts.response_surface(df, "gpp_z")
    surf.to_csv(cfg.RESULTS / "response_surface_gpp.csv", index=False)
    plot.plot_response_surface(surf)
    rows = impacts.surface_row_means(surf)
    print(f"\nResponse surface, mean GPP z per SPEI-3 row (wettest first):\n{rows.round(2).to_string(index=False)}")
    worst = surf.dropna(subset=["mean"]).sort_values("mean").iloc[0]
    print(f"Lowest bin: Tmax z {worst['tz_bin']}, SPEI-3 {worst['spei_bin']}: "
          f"{worst['mean']:.2f} (n={int(worst['n'])})")

    print(f"\nDone. Tables in {cfg.RESULTS}, figures in {cfg.FIGURES}.")


if __name__ == "__main__":
    main()
