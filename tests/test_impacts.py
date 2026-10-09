import numpy as np
import pandas as pd
import pytest

from chd import cube
from chd.impacts import (
    cube_to_long_table, category_counts, category_composites, category_contrasts,
    robustness_spei_vs_spi, response_surface, surface_row_means, mechanism_check,
    compound_frequency,
)


def _synthetic_long_df(n_years=20, seed=0, compound_effect=-4.0):
    """Hand-built long table with known category effects (hot -1, dry -1)."""
    rng = np.random.default_rng(seed)
    rows = []
    true_effect = {"normal": 0.0, "hot_only": -1.0, "dry_only": -1.0, "compound": compound_effect}
    for year in range(2001, 2001 + n_years):
        year_shift = rng.normal(0, 0.3)  # shared year-level noise
        for cat, effect in true_effect.items():
            for _ in range(20):
                rows.append({
                    "year": year, "category": cat, "category_spi": cat,
                    "gpp_z": effect + year_shift + rng.normal(0, 0.5),
                    "ndvi_z": effect + rng.normal(0, 0.5),
                    "sm_z": effect * 0.5 + rng.normal(0, 0.3),
                    "vpd_z": -effect * 0.3 + rng.normal(0, 0.3),
                })
    return pd.DataFrame(rows)


def test_category_counts_shares_sum_to_100():
    counts = category_counts(_synthetic_long_df())
    assert list(counts["category"]) == ["normal", "hot_only", "dry_only", "compound"]
    assert counts["pct"].sum() == pytest.approx(100.0)


def test_category_composites_recovers_known_means():
    comp = category_composites(_synthetic_long_df(), "gpp_z")
    means = dict(zip(comp["category"], comp["mean"]))
    assert means["hot_only"] - means["normal"] == pytest.approx(-1.0, abs=0.2)
    assert means["compound"] - means["normal"] == pytest.approx(-4.0, abs=0.2)
    assert (comp["ci_low"] < comp["mean"]).all() and (comp["mean"] < comp["ci_high"]).all()


def test_category_contrasts_recovers_known_synergy():
    row = category_contrasts(_synthetic_long_df(), "gpp_z").iloc[0]
    # compound=-4, hot=-1, dry=-1, normal=0 -> AI=-2, compound-dry=-3
    assert row["amplification_index"] == pytest.approx(-2.0, abs=0.3)
    assert row["amplification_index_sig"]
    assert row["compound_minus_dry"] == pytest.approx(-3.0, abs=0.3)


def test_category_contrasts_additive_case_not_significant():
    df = _synthetic_long_df(seed=7, compound_effect=-2.0)  # exactly additive
    assert not category_contrasts(df, "gpp_z").iloc[0]["amplification_index_sig"]


def test_robustness_has_both_indices_for_both_responses():
    rob = robustness_spei_vs_spi(_synthetic_long_df())
    assert set(zip(rob["response"], rob["drought_index"])) == {
        ("gpp_z", "SPEI-3"), ("gpp_z", "SPI-3"), ("ndvi_z", "SPEI-3"), ("ndvi_z", "SPI-3")}


def test_response_surface_masks_sparse_bins():
    rng = np.random.default_rng(1)
    n = 5000
    df = pd.DataFrame({"tmax_z": rng.normal(0, 1.5, n), "spei03": rng.normal(0, 1.5, n),
                       "gpp_z": rng.normal(0, 1, n)})
    surf = response_surface(df, "gpp_z", min_n=30)
    assert surf.loc[surf["n"] < 30, "mean"].isna().all()
    assert surf.loc[surf["n"] >= 30, "mean"].notna().any()
    rows = surface_row_means(surf)
    assert rows["spei_low"].is_monotonic_decreasing


def test_mechanism_check_compound_is_driest():
    mech = mechanism_check(_synthetic_long_df()).set_index("category")
    assert mech.loc["compound", "sm_z"] < mech.loc["normal", "sm_z"]
    assert mech.loc["compound", "vpd_z"] > mech.loc["normal", "vpd_z"]


def test_long_table_and_frequency_from_small_grid(small_grid):
    ds = cube.build_full_cube(raw_dir=small_grid)
    df = cube_to_long_table(ds)
    assert set(df.columns) >= {"time", "year", "lat", "lon", "category", "category_spi",
                               "tmax_z", "spei03", "gpp_z", "ndvi_z"}
    assert (df["category"] != "nan").all()
    freq = compound_frequency(ds)
    assert freq.shape == ds["is_india"].shape
    assert np.nanmin(freq) >= 0 and np.nanmax(freq) <= 1
