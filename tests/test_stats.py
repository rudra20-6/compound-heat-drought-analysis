import numpy as np
import pandas as pd

from chd.stats import (
    year_block_bootstrap_mean, bootstrap_difference, sen_slope_mk_trend,
    amplification_index, panel_fixed_effects_ols,
)


def test_bootstrap_mean_ci_contains_true_mean():
    rng = np.random.default_rng(0)
    years = np.repeat(np.arange(2000, 2020), 10)
    values = rng.normal(5.0, 1.0, len(years))
    result = year_block_bootstrap_mean(values, years, n_boot=500)
    assert result["ci_low"] < 5.0 < result["ci_high"]
    assert result["n_obs"] == len(values)


def test_bootstrap_mean_handles_nan():
    years = np.repeat(np.arange(2000, 2010), 5)
    values = np.full(len(years), 2.0)
    values[0] = np.nan
    result = year_block_bootstrap_mean(values, years, n_boot=200)
    assert result["n_obs"] == len(values) - 1
    assert abs(result["estimate"] - 2.0) < 1e-9


def test_bootstrap_difference_detects_real_difference():
    rng = np.random.default_rng(1)
    years_a = np.repeat(np.arange(2000, 2020), 10)
    years_b = np.repeat(np.arange(2000, 2020), 10)
    values_a = rng.normal(0.0, 1.0, len(years_a))
    values_b = rng.normal(-3.0, 1.0, len(years_b))  # clearly lower
    result = bootstrap_difference(values_a, years_a, values_b, years_b, n_boot=500)
    assert result["estimate"] > 0
    assert result["ci_low"] > 0  # CI should exclude zero given the large gap


def test_sen_slope_recovers_known_linear_trend():
    years = np.arange(1991, 2024)
    true_slope = 0.5
    rng = np.random.default_rng(2)
    values = 10 + true_slope * (years - 1991) + rng.normal(0, 0.2, len(years))
    result = sen_slope_mk_trend(years, values)
    assert abs(result["slope"] - true_slope) < 0.1
    assert result["p_value"] < 0.01  # strong trend should be significant
    assert result["tau"] > 0.8


def test_sen_slope_no_trend_gives_small_slope_high_pvalue():
    years = np.arange(1991, 2024)
    rng = np.random.default_rng(3)
    values = rng.normal(10, 1.0, len(years))  # pure noise, no trend
    result = sen_slope_mk_trend(years, values)
    assert abs(result["slope"]) < 0.3
    assert result["p_value"] > 0.05


def test_sen_slope_too_few_points_returns_nan():
    result = sen_slope_mk_trend(np.array([2000, 2001]), np.array([1.0, 2.0]))
    assert np.isnan(result["slope"])


def test_amplification_index_synergistic_case():
    # compound loss (-4) is worse than sum of single-stressor losses (-1 + -1 = -2)
    means = {"normal": 0.0, "hot_only": -1.0, "dry_only": -1.0, "compound": -4.0}
    ai = amplification_index(means)
    assert ai == -2.0  # -4 - (-1 + -1) = -4 + 2 = -2, i.e. more negative = synergistic
    assert ai < 0


def test_amplification_index_additive_case():
    means = {"normal": 0.0, "hot_only": -1.0, "dry_only": -1.5, "compound": -2.5}
    ai = amplification_index(means)
    assert abs(ai) < 1e-9  # exactly additive


def test_panel_fixed_effects_ols_recovers_known_coefficient():
    rng = np.random.default_rng(4)
    n_cells, n_years = 20, 15
    rows = []
    cell_effects = rng.normal(0, 2, n_cells)
    true_beta = -1.5
    for c in range(n_cells):
        for y in range(n_years):
            x = rng.normal(0, 1)
            noise = rng.normal(0, 0.3)
            y_val = cell_effects[c] + true_beta * x + noise
            rows.append({"cell_id": c, "year": 2000 + y, "x": x, "y": y_val})
    df = pd.DataFrame(rows)

    result = panel_fixed_effects_ols(df, y_col="y", x_cols=["x"], cell_col="cell_id", year_col="year")
    assert abs(result.params["x"] - true_beta) < 0.2
    assert result.pvalues["x"] < 0.01


def test_bootstrap_counts_repeated_years():
    """Regression test: the old implementation used np.isin on the drawn
    years, silently dropping repeat draws (each replicate saw only ~63% of
    years once). With one dominant outlier year, a true bootstrap must
    sometimes include it more than once, pulling replicate means beyond what
    a single inclusion allows."""
    years = np.repeat(np.arange(2000, 2010), 10)
    values = np.zeros(len(years))
    values[years == 2000] = 10.0  # outlier year
    res = year_block_bootstrap_mean(values, years, n_boot=2000)
    # one inclusion out of 10 years -> mean 1.0; >1.0 needs repeat draws
    assert res["ci_high"] > 1.5


def test_bootstrap_category_contrasts_shapes():
    from chd.stats import bootstrap_category_contrasts
    rng = np.random.default_rng(5)
    years = np.repeat(np.arange(2001, 2021), 40)
    cats = np.tile(["normal", "hot_only", "dry_only", "compound"], len(years) // 4)
    effect = {"normal": 0.0, "hot_only": -0.5, "dry_only": -1.0, "compound": -2.5}
    values = np.array([effect[c] for c in cats]) + rng.normal(0, 0.3, len(years))
    res = bootstrap_category_contrasts(values, years, cats, n_boot=500)
    assert abs(res["amplification_index"]["estimate"] - (-1.0)) < 0.15
    assert res["amplification_index"]["ci_high"] < 0  # clearly synergistic
    assert res["n_compound"] == len(years) // 4
