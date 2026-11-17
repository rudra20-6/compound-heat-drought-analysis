import numpy as np
import pandas as pd
import pytest

from chd import cube
from chd.impacts import (
    cube_to_long_table, category_composites, compute_amplification,
    response_surface, mechanism_check, category_contrasts,
)
from chd import config as cfg


def _synthetic_long_df(n_years=20, seed=0):
    """Hand-built long table with a known, deliberately synergistic signal:
    compound months have a much larger GPP drop than hot_only + dry_only combined."""
    rng = np.random.default_rng(seed)
    rows = []
    true_effect = {"normal": 0.0, "hot_only": -1.0, "dry_only": -1.0, "compound": -4.0}
    for year in range(2001, 2001 + n_years):
        for cat, effect in true_effect.items():
            for _ in range(20):  # 20 cell-months per category per year
                rows.append({
                    "year": year,
                    "category": cat,
                    "gpp_z": effect + rng.normal(0, 0.5),
                    "sm_z": effect * 0.5 + rng.normal(0, 0.3),
                    "vpd_z": -effect * 0.3 + rng.normal(0, 0.3),
                })
    return pd.DataFrame(rows)


def test_category_composites_recovers_known_means():
    df = _synthetic_long_df()
    comp = category_composites(df, "gpp_z")
    means = dict(zip(comp["category"], comp["mean"]))
    assert means["normal"] == pytest.approx(0.0, abs=0.2)
    assert means["hot_only"] == pytest.approx(-1.0, abs=0.2)
    assert means["dry_only"] == pytest.approx(-1.0, abs=0.2)
    assert means["compound"] == pytest.approx(-4.0, abs=0.2)
    assert not comp["flagged_low_n"].any()  # 20*20=400 obs per category, well above MIN_STRATUM_N


def test_category_composites_flags_small_strata():
    df = _synthetic_long_df(n_years=1)  # only 20 obs/category -> below MIN_STRATUM_N likely
    comp = category_composites(df, "gpp_z")
    assert (comp["n"] < cfg.MIN_STRATUM_N).any()
    assert comp.loc[comp["n"] < cfg.MIN_STRATUM_N, "flagged_low_n"].all()


def test_compute_amplification_detects_synergy():
    df = _synthetic_long_df()
    comp = category_composites(df, "gpp_z")
    ai = compute_amplification(comp)
    assert len(ai) == 1
    # true: compound=-4, hot=-1, dry=-1 -> AI = -4 - (-1-1) = -2
    assert ai["amplification_index"].iloc[0] == pytest.approx(-2.0, abs=0.3)


def test_compute_amplification_per_stratum():
    df = _synthetic_long_df()
    df["dominant_landcover"] = np.where(df.index % 2 == 0, "tree_cover", "cropland")
    comp = category_composites(df, "gpp_z", group_cols=["dominant_landcover"])
    ai = compute_amplification(comp, group_cols=["dominant_landcover"])
    assert set(ai["dominant_landcover"]) == {"tree_cover", "cropland"}
    assert (ai["amplification_index"] < 0).all()


def test_response_surface_bins_and_masks_sparse_bins():
    rng = np.random.default_rng(1)
    n = 5000
    df = pd.DataFrame({
        "tmax_z": rng.normal(0, 1.5, n),
        "spei03": rng.normal(0, 1.5, n),
        "gpp_z": rng.normal(0, 1, n),
    })
    surf = response_surface(df, "gpp_z", min_n=30)
    assert "mean" in surf.columns and "n" in surf.columns
    # bins with fewer than min_n obs should be NaN
    assert surf.loc[surf["n"] < 30, "mean"].isna().all()
    # at least some well-populated bins near the center should have real means
    assert surf.loc[surf["n"] >= 30, "mean"].notna().any()


def test_mechanism_check_groups_by_category():
    df = _synthetic_long_df()
    mech = mechanism_check(df)
    assert set(mech["category"]) == {"normal", "hot_only", "dry_only", "compound"}
    assert "sm_z" in mech.columns and "vpd_z" in mech.columns
    # compound should show the most negative soil moisture (driest)
    row = mech.set_index("category")
    assert row.loc["compound", "sm_z"] < row.loc["normal", "sm_z"]


def test_cube_to_long_table_from_small_grid(small_grid):
    full = cube.build_full_cube(raw_dir=small_grid)
    df = cube_to_long_table(full)
    assert set(df.columns) >= {"time", "lat", "lon", "cell_id", "category", "category_spi",
                               "tmax_z", "spei03", "gpp_z", "ndvi_z"}
    assert (df["category"] != "nan").all()
    assert "dominant_landcover" in df.columns
    assert "region" in df.columns


def test_category_contrasts_recovers_known_synergy():
    df = _synthetic_long_df()
    res = category_contrasts(df, "gpp_z")
    row = res.iloc[0]
    # true: compound=-4, hot=-1, dry=-1, normal=0 -> AI=-2, compound-dry=-3
    assert row["amplification_index"] == pytest.approx(-2.0, abs=0.3)
    assert row["amplification_index_sig"]
    assert row["compound_minus_dry"] == pytest.approx(-3.0, abs=0.3)
    assert row["amplification_index_ci_low"] < row["amplification_index"] < row["amplification_index_ci_high"]


def test_category_contrasts_additive_case_not_significant():
    rng = np.random.default_rng(7)
    rows = []
    effect = {"normal": 0.0, "hot_only": -1.0, "dry_only": -1.0, "compound": -2.0}  # exactly additive
    for year in range(2001, 2021):
        year_shift = rng.normal(0, 0.3)  # shared year-level noise
        for cat, e in effect.items():
            for _ in range(20):
                rows.append({"year": year, "category": cat, "gpp_z": e + year_shift + rng.normal(0, 0.5)})
    res = category_contrasts(pd.DataFrame(rows), "gpp_z")
    assert not res.iloc[0]["amplification_index_sig"]
