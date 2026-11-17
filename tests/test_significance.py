"""Tests for the final-phase significance helpers and region settings."""
import numpy as np

from chd import config as cfg
from chd.stats import (bootstrap_p_value, benjamini_hochberg, bootstrap_category_contrasts,
                       bootstrap_difference, _ci)


def test_bootstrap_p_value_consistent_with_ci():
    rng = np.random.default_rng(0)
    for centre in (0.0, 0.05, 0.1, 0.2, 0.5):
        boot = rng.normal(centre, 0.1, 5000)
        lo, hi = _ci(boot)
        p = bootstrap_p_value(boot)
        assert (p < 0.05) == (lo > 0 or hi < 0)


def test_bootstrap_p_value_floor_and_ceiling():
    assert bootstrap_p_value(np.full(1000, 3.0)) == 1.0 / 1000   # nothing crosses 0 -> p = 1/B
    sym = np.concatenate([-np.ones(500), np.ones(500)])
    assert bootstrap_p_value(sym) == 1.0
    assert np.isnan(bootstrap_p_value(np.array([np.nan, np.nan])))


def test_benjamini_hochberg_matches_hand_computation():
    p = np.array([0.01, 0.04, 0.03, 0.20, np.nan])
    q = benjamini_hochberg(p)
    # sorted p: 0.01, 0.03, 0.04, 0.20 (m = 4) -> raw 0.04, 0.06, 0.0533, 0.20 -> monotone 0.04, 0.0533, 0.0533, 0.20
    assert np.allclose(q[:4], [0.04, 0.05333333, 0.05333333, 0.20])
    assert np.isnan(q[4])
    assert np.all(q[:4] >= p[:4])


def test_category_contrasts_report_p_values():
    rng = np.random.default_rng(3)
    years = np.repeat(np.arange(2001, 2023), 200)
    cats = rng.choice(["normal", "hot_only", "dry_only", "compound"], len(years))
    effect = {"normal": 0.0, "hot_only": -0.3, "dry_only": -0.3, "compound": -0.6}
    values = np.array([effect[c] for c in cats]) + rng.normal(0, 0.5, len(years))
    res = bootstrap_category_contrasts(values, years, cats, n_boot=2000)
    assert res["d_compound"]["p_value"] < 0.01          # strong real effect
    assert res["amplification_index"]["p_value"] > 0.05  # built additive -> AI ~ 0
    assert "se" in res["amplification_index"]


def test_bootstrap_difference_has_p_value():
    rng = np.random.default_rng(4)
    years = np.repeat(np.arange(2000, 2020), 20)
    a = rng.normal(1.0, 1.0, len(years))
    b = rng.normal(0.0, 1.0, len(years))
    res = bootstrap_difference(a, years, b, years, n_boot=2000)
    assert res["p_value"] < 0.01


def test_subregion_of_india_default():
    # tests run with the default region (india)
    assert cfg.REGION == "india"
    lab = cfg.subregion_of(np.array([12.0, 30.0, 11.0]), np.array([77.0, 77.0, 93.0]))
    assert list(lab) == ["peninsular", "north", "islands"]
