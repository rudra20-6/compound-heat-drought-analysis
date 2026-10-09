import numpy as np

from chd.stats import year_block_bootstrap_mean, bootstrap_category_contrasts


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


def test_bootstrap_counts_repeated_years():
    """A true with-replacement year bootstrap must sometimes draw the same
    year more than once. With one outlier year out of ten, a single inclusion
    gives a replicate mean of 1.0, so values above 1.0 need repeat draws."""
    years = np.repeat(np.arange(2000, 2010), 10)
    values = np.zeros(len(years))
    values[years == 2000] = 10.0
    res = year_block_bootstrap_mean(values, years, n_boot=2000)
    assert res["ci_high"] > 1.5


def test_bootstrap_category_contrasts_recovers_synergy():
    rng = np.random.default_rng(5)
    years = np.repeat(np.arange(2001, 2021), 40)
    cats = np.tile(["normal", "hot_only", "dry_only", "compound"], len(years) // 4)
    effect = {"normal": 0.0, "hot_only": -0.5, "dry_only": -1.0, "compound": -2.5}
    values = np.array([effect[c] for c in cats]) + rng.normal(0, 0.3, len(years))
    res = bootstrap_category_contrasts(values, years, cats, n_boot=500)
    # AI = -2.5 - (-0.5 - 1.0) = -1.0
    assert abs(res["amplification_index"]["estimate"] - (-1.0)) < 0.15
    assert res["amplification_index"]["ci_high"] < 0
    assert res["n_compound"] == len(years) // 4
