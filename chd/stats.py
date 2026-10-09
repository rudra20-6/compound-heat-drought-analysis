"""
Year-block bootstrap used for every confidence interval in the analysis.

Whole years are resampled (not individual cell-months), because cell-months
from the same year are spatially and temporally correlated.
"""
from __future__ import annotations

import numpy as np

from . import config as cfg


# ---------------------------------------------------------------------------
# Year-block bootstrap
# ---------------------------------------------------------------------------
def _year_weights(n_years: int, n_boot: int, seed: int) -> np.ndarray:
    """
    (n_boot, n_years) matrix of multinomial resampling counts: row b says how
    many times each year was drawn in bootstrap replicate b. Using counts
    (rather than np.isin on the drawn years, which silently drops repeat
    draws) gives a true with-replacement year-block bootstrap.
    """
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_years, size=(n_boot, n_years))
    return np.stack([np.bincount(row, minlength=n_years) for row in draws]).astype(float)


def _per_year_sums(values, years, year_index):
    """Per-year sum and count of the non-NaN values, aligned to `year_index`."""
    values = np.asarray(values, dtype=float)
    years = np.asarray(years)
    valid = ~np.isnan(values)
    pos = np.searchsorted(year_index, years[valid])
    sums = np.bincount(pos, weights=values[valid], minlength=len(year_index))
    counts = np.bincount(pos, minlength=len(year_index)).astype(float)
    return sums, counts


def _ci(boot: np.ndarray):
    boot = boot[~np.isnan(boot)]
    if len(boot) == 0:
        return np.nan, np.nan
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return float(lo), float(hi)


def year_block_bootstrap_mean(values: np.ndarray, years: np.ndarray,
                               n_boot: int = cfg.BOOTSTRAP_N,
                               seed: int = cfg.BOOTSTRAP_SEED) -> dict:
    """
    Bootstrap a CI for the mean of `values` by resampling *years* with
    replacement (all cell-months of a drawn year enter together, as many
    times as that year was drawn) rather than individual cell-months -- so
    spatially/temporally autocorrelated observations within a year are not
    treated as independent.

    Returns dict with keys: estimate, ci_low, ci_high, se, n_boot, n_obs.
    """
    values = np.asarray(values, dtype=float)
    years = np.asarray(years)
    year_index = np.unique(years)
    sums, counts = _per_year_sums(values, years, year_index)

    w = _year_weights(len(year_index), n_boot, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = (w @ sums) / (w @ counts)
    ci_low, ci_high = _ci(boot)
    n_obs = int(counts.sum())
    return {
        "estimate": float(sums.sum() / counts.sum()) if n_obs else np.nan,
        "ci_low": ci_low, "ci_high": ci_high,
        "se": float(np.nanstd(boot)),
        "n_boot": int(np.sum(~np.isnan(boot))),
        "n_obs": n_obs,
    }


CATEGORY_ORDER = ("normal", "hot_only", "dry_only", "compound")


def bootstrap_category_contrasts(values: np.ndarray, years: np.ndarray, categories: np.ndarray,
                                  n_boot: int = cfg.BOOTSTRAP_N,
                                  seed: int = cfg.BOOTSTRAP_SEED) -> dict:
    """
    Joint year-block bootstrap of the four category means and the contrasts
    built from them, all from the *same* resampled years in each replicate:

      d_hot, d_dry, d_compound  -- each category minus 'normal'
      compound_minus_dry        -- is compound worse than drought alone?
      compound_minus_hot        -- is compound worse than heat alone?
      amplification_index       -- d_compound - (d_hot + d_dry); < 0 = synergistic

    Returns {name: {"estimate", "ci_low", "ci_high"}} plus "n_<category>".
    A contrast is "significant" here when its 95% CI excludes zero.
    """
    values = np.asarray(values, dtype=float)
    years = np.asarray(years)
    categories = np.asarray(categories)
    year_index = np.unique(years)
    w = _year_weights(len(year_index), n_boot, seed)

    point, boot, out = {}, {}, {}
    for cat in CATEGORY_ORDER:
        sel = categories == cat
        s, c = _per_year_sums(values[sel], years[sel], year_index)
        out[f"n_{cat}"] = int(c.sum())
        point[cat] = s.sum() / c.sum() if c.sum() else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            boot[cat] = (w @ s) / (w @ c)

    def _contrasts(m):
        d_hot = m["hot_only"] - m["normal"]
        d_dry = m["dry_only"] - m["normal"]
        d_cmp = m["compound"] - m["normal"]
        return {
            "d_hot": d_hot, "d_dry": d_dry, "d_compound": d_cmp,
            "compound_minus_dry": m["compound"] - m["dry_only"],
            "compound_minus_hot": m["compound"] - m["hot_only"],
            "amplification_index": d_cmp - (d_hot + d_dry),
        }

    point_c = _contrasts(point)
    boot_c = _contrasts(boot)
    for cat in CATEGORY_ORDER:
        lo, hi = _ci(boot[cat])
        out[f"mean_{cat}"] = {"estimate": float(point[cat]), "ci_low": lo, "ci_high": hi}
    for name, est in point_c.items():
        lo, hi = _ci(np.asarray(boot_c[name]))
        out[name] = {"estimate": float(est), "ci_low": lo, "ci_high": hi}
    return out
