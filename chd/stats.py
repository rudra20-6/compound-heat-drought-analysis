"""
Generic statistical helpers shared by impacts.py / recovery.py:
  - year-block bootstrap (resamples whole years, not individual cell-months,
    to respect spatial/temporal autocorrelation within a year)
  - Sen's slope + Mann-Kendall trend test
  - panel OLS with cell fixed effects and year-clustered SEs
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sstats

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


def bootstrap_p_value(boot: np.ndarray) -> float:
    """
    Two-sided bootstrap p-value for H0: statistic = 0, by inverting the
    percentile interval: p = 2 * min(P*(stat <= 0), P*(stat >= 0)) over the
    bootstrap replicates. It is consistent with _ci (p < 0.05 exactly when
    the 95% percentile CI excludes 0). When no replicate crosses 0 the
    p-value is reported as 1/B (i.e. "p < 1/B"; B = number of replicates).
    """
    boot = np.asarray(boot, dtype=float)
    boot = boot[~np.isnan(boot)]
    if len(boot) == 0:
        return np.nan
    p = 2.0 * min(np.mean(boot <= 0), np.mean(boot >= 0))
    return float(min(1.0, max(p, 1.0 / len(boot))))


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


def bootstrap_difference(values_a, years_a, values_b, years_b,
                          n_boot: int = cfg.BOOTSTRAP_N, seed: int = cfg.BOOTSTRAP_SEED) -> dict:
    """
    Bootstrap CI for mean(a) - mean(b). Both groups are resampled with the
    *same* year draws, since they come from the same years (e.g. two stress
    categories within one study period) and are correlated through them.
    """
    year_index = np.unique(np.concatenate([np.asarray(years_a), np.asarray(years_b)]))
    sa, ca = _per_year_sums(values_a, years_a, year_index)
    sb, cb = _per_year_sums(values_b, years_b, year_index)
    w = _year_weights(len(year_index), n_boot, seed)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = (w @ sa) / (w @ ca) - (w @ sb) / (w @ cb)
    ci_low, ci_high = _ci(boot)
    return {"estimate": float(sa.sum() / ca.sum() - sb.sum() / cb.sum()),
            "ci_low": ci_low, "ci_high": ci_high, "p_value": bootstrap_p_value(boot),
            "se": float(np.nanstd(boot)), "n_boot": int(np.sum(~np.isnan(boot)))}


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
        b = np.asarray(boot_c[name])
        lo, hi = _ci(b)
        out[name] = {"estimate": float(est), "ci_low": lo, "ci_high": hi,
                     "p_value": bootstrap_p_value(b), "se": float(np.nanstd(b))}
    return out


# ---------------------------------------------------------------------------
# Trend tests
# ---------------------------------------------------------------------------
def sen_slope_mk_trend(years: np.ndarray, values: np.ndarray) -> dict:
    """Theil-Sen slope (per year) + Mann-Kendall tau and p-value for a time series."""
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    valid = ~np.isnan(values)
    years, values = years[valid], values[valid]
    if len(values) < 4:
        return {"slope": np.nan, "intercept": np.nan, "tau": np.nan, "p_value": np.nan, "n": len(values)}

    slope, intercept, low_slope, high_slope = sstats.theilslopes(values, years)
    tau, p_value = sstats.kendalltau(years, values)
    return {
        "slope": float(slope), "intercept": float(intercept),
        "slope_ci_low": float(low_slope), "slope_ci_high": float(high_slope),
        "tau": float(tau), "p_value": float(p_value), "n": int(len(values)),
    }


# ---------------------------------------------------------------------------
# Panel OLS with cell fixed effects + year-clustered SEs
# ---------------------------------------------------------------------------
def panel_fixed_effects_ols(df: pd.DataFrame, y_col: str, x_cols: list[str],
                             cell_col: str = "cell_id", year_col: str = "year"):
    """
    Within-transform (demean by cell_id) panel OLS of y on x_cols, with
    standard errors clustered by year_col. Returns a statsmodels
    RegressionResultsWrapper (use .params, .bse, .tvalues, .pvalues).

    Requires statsmodels; import kept local so the rest of the package has
    no hard dependency on it.
    """
    import statsmodels.api as sm

    df = df.dropna(subset=[y_col] + x_cols + [cell_col, year_col]).copy()

    y_demeaned = df[y_col] - df.groupby(cell_col)[y_col].transform("mean")
    x_demeaned = df[x_cols].apply(lambda col: col - df.groupby(cell_col)[col.name].transform("mean"))

    X = sm.add_constant(x_demeaned)
    model = sm.OLS(y_demeaned, X)
    result = model.fit(cov_type="cluster", cov_kwds={"groups": df[year_col]})
    return result


def benjamini_hochberg(p_values) -> np.ndarray:
    """Benjamini-Hochberg FDR-adjusted p-values (q-values); NaNs are passed through."""
    p = np.asarray(p_values, dtype=float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return q
    order = np.argsort(pv)
    ranked = pv[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adj = np.empty(m)
    adj[order] = np.minimum(ranked, 1.0)
    q[ok] = adj
    return q


def amplification_index(mean_by_category: dict[str, float]) -> float:
    """
    AI = delta_compound - (delta_hot_only + delta_dry_only), each delta
    relative to the 'normal' category. AI < 0 means the compound loss is
    larger (more negative) than the simple sum of single-stressor losses
    (synergistic / non-additive interaction, per plan H2).
    """
    base = mean_by_category["normal"]
    d_compound = mean_by_category["compound"] - base
    d_hot = mean_by_category["hot_only"] - base
    d_dry = mean_by_category["dry_only"] - base
    return d_compound - (d_hot + d_dry)
