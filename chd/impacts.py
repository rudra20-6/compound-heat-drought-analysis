"""
Impact & synergy analysis (plan sections 3.B and 3.C): category composites
with bootstrap CIs, the amplification index, the bivariate (Tz x SPEI)
response surface, and land-cover / region stratification.

Operates on a "long" (flattened) table of active cell-months rather than
the raw cube, since every analysis here is a group-by over categories or
bins -- flattening once up front keeps every function a simple pandas
groupby, which is both easier to test and easier to re-run per stratum.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from . import config as cfg
from .stats import year_block_bootstrap_mean, amplification_index, bootstrap_category_contrasts


def cube_to_long_table(ds: xr.Dataset, response_vars=("gpp_z", "ndvi_z")) -> pd.DataFrame:
    """
    Flatten the cube's active-season cell-months into a long DataFrame with
    one row per (time, lat, lon), keeping only cells where active_season is
    True. Columns: time, year, lat, lon, cell_id, category, tmax_z, spei03,
    sm_z, vpd_z, dominant land-cover columns, region flags, + response_vars.
    """
    active = ds["active_season"]
    cols = ["category", "tmax_z", "spei03", "sm_z", "vpd_z", *response_vars]
    cols += [c for c in ("category_spi", "spi03") if c in ds and c not in cols]
    df = ds[cols].where(active).to_dataframe().reset_index()
    df = df.dropna(subset=["category"])
    df = df[df["category"] != "nan"]
    df["year"] = pd.DatetimeIndex(df["time"]).year
    df["cell_id"] = df["lat"].round(4).astype(str) + "_" + df["lon"].round(4).astype(str)

    frac_cols = [c for c in ds.data_vars if c.startswith("frac_")]
    if frac_cols:
        frac_df = ds[frac_cols].to_dataframe().reset_index()
        frac_df["cell_id"] = frac_df["lat"].round(4).astype(str) + "_" + frac_df["lon"].round(4).astype(str)
        fracs = frac_df.set_index("cell_id")[frac_cols].fillna(0.0)
        dominant = fracs.idxmax(axis=1).str.replace("frac_", "", regex=False)
        purity = fracs.max(axis=1)
        dominant[purity < cfg.THRESH.landcover_purity] = "mixed"
        df["dominant_landcover"] = df["cell_id"].map(dominant)

    # H4 sub-region from cell-centre lat/lon (India: peninsular / north, with the
    # Andaman & Nicobar islands labelled "islands"; Australia: tropical_north /
    # temperate_south). See config.subregion_of.
    df["region"] = cfg.subregion_of(df["lat"].values, df["lon"].values)
    month = pd.DatetimeIndex(df["time"]).month
    season_of = {m: s for s, ms in cfg.REGION_SEASONS.items() for m in ms}
    df["season"] = month.map(season_of).values

    return df


def category_composites(df: pd.DataFrame, response_var: str,
                          group_cols: list[str] | None = None,
                          category_col: str = "category") -> pd.DataFrame:
    """
    Mean response_var by category (optionally further grouped by group_cols,
    e.g. ["dominant_landcover"] or ["region"]), with year-block bootstrap CIs.
    `n` counts non-missing response values. Strata with n < MIN_STRATUM_N are
    flagged via the `flagged_low_n` column.
    """
    group_cols = group_cols or []
    rows = []
    for keys, g in df.groupby(group_cols + [category_col], dropna=True, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        *strata_keys, category = keys
        if category == "nan":
            continue
        boot = year_block_bootstrap_mean(g[response_var].values, g["year"].values)
        row = dict(zip(group_cols, strata_keys))
        row.update({
            "category": category, "n": boot["n_obs"],
            "mean": boot["estimate"], "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
            "flagged_low_n": boot["n_obs"] < cfg.MIN_STRATUM_N,
        })
        rows.append(row)
    return pd.DataFrame(rows)


CONTRASTS = ("d_hot", "d_dry", "d_compound", "compound_minus_dry",
             "compound_minus_hot", "amplification_index")


def category_contrasts(df: pd.DataFrame, response_var: str,
                       group_cols: list[str] | None = None,
                       category_col: str = "category") -> pd.DataFrame:
    """
    Per stratum: the four category means and the contrasts between them
    (each category minus normal; compound minus dry-only; compound minus
    hot-only; amplification index), all from one *joint* year-block
    bootstrap so every contrast gets a valid 95% CI. A contrast is called
    significant when its CI excludes zero (column `<name>_sig`).
    """
    group_cols = group_cols or []
    groups = df.groupby(group_cols, observed=True) if group_cols else [((), df)]
    rows = []
    for keys, g in groups:
        if not isinstance(keys, tuple):
            keys = (keys,)
        res = bootstrap_category_contrasts(g[response_var].values, g["year"].values,
                                           g[category_col].values)
        row = dict(zip(group_cols, keys))
        for cat in ("normal", "hot_only", "dry_only", "compound"):
            row[f"n_{cat}"] = res[f"n_{cat}"]
            row[f"mean_{cat}"] = res[f"mean_{cat}"]["estimate"]
        for name in CONTRASTS:
            row[name] = res[name]["estimate"]
            row[f"{name}_ci_low"] = res[name]["ci_low"]
            row[f"{name}_ci_high"] = res[name]["ci_high"]
            row[f"{name}_sig"] = bool(res[name]["ci_low"] > 0 or res[name]["ci_high"] < 0)
            row[f"{name}_p"] = res[name]["p_value"]
        row["min_category_n"] = min(res[f"n_{c}"] for c in ("normal", "hot_only", "dry_only", "compound"))
        rows.append(row)
    return pd.DataFrame(rows)


def compute_amplification(composites: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Given the output of category_composites (one row per category per stratum),
    compute the amplification index per stratum.
    """
    group_cols = group_cols or []
    rows = []
    if group_cols:
        groups = composites.groupby(group_cols)
    else:
        groups = [((), composites)]
    for keys, g in groups:
        means = dict(zip(g["category"], g["mean"]))
        if not {"normal", "hot_only", "dry_only", "compound"} <= set(means):
            continue
        ai = amplification_index(means)
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row["amplification_index"] = ai
        rows.append(row)
    return pd.DataFrame(rows)


def response_surface(df: pd.DataFrame, response_var: str,
                      tz_bins=np.arange(-2.0, 3.01, 0.5),
                      spei_bins=np.arange(-2.5, 2.51, 0.5),
                      min_n: int = cfg.MIN_STRATUM_N) -> pd.DataFrame:
    """
    Bin tmax_z x spei03 and compute mean response_var in each 2D bin.
    Bins with n < min_n are masked (mean set to NaN) so sparse corners of
    the response surface don't get over-interpreted.
    """
    df = df.copy()
    df["tz_bin"] = pd.cut(df["tmax_z"], tz_bins)
    df["spei_bin"] = pd.cut(df["spei03"], spei_bins)

    grouped = df.groupby(["tz_bin", "spei_bin"], observed=True)[response_var]
    out = grouped.agg(mean="mean", n="count").reset_index()
    out.loc[out["n"] < min_n, "mean"] = np.nan
    return out


def mechanism_check(df: pd.DataFrame) -> pd.DataFrame:
    """Mean sm_z and vpd_z by category -- used to check which mechanism (soil-moisture
    depletion vs atmospheric aridity) dominates in each stress category."""
    return df.groupby("category", observed=True)[["sm_z", "vpd_z"]].mean().reset_index()


def region_difference_test(df: pd.DataFrame, response_var: str,
                           region_a: str | None = None, region_b: str | None = None,
                           n_boot: int = cfg.BOOTSTRAP_N, seed: int = cfg.BOOTSTRAP_SEED) -> pd.DataFrame:
    """
    Is a stress effect (category minus normal) larger in region_a than in
    region_b? Joint year-block bootstrap over both regions' cell-months
    (same year draws), 95% CI of the difference in effects.
    """
    from .stats import _year_weights, _per_year_sums, _ci, bootstrap_p_value
    region_a = region_a or cfg.SUBREGION["region_a"]
    region_b = region_b or cfg.SUBREGION["region_b"]
    years = np.unique(df["year"])
    w = _year_weights(len(years), n_boot, seed)
    effects = {}
    for reg in (region_a, region_b):
        g = df[df["region"] == reg]
        means = {}
        for cat in ("normal", "hot_only", "dry_only", "compound"):
            sel = g["category"] == cat
            s, c = _per_year_sums(g.loc[sel, response_var].values, g.loc[sel, "year"].values, years)
            with np.errstate(invalid="ignore", divide="ignore"):
                means[cat] = ((w @ s) / (w @ c), s.sum() / c.sum())
        effects[reg] = {k: (means[k][0] - means["normal"][0], means[k][1] - means["normal"][1])
                        for k in ("hot_only", "dry_only", "compound")}
    rows = []
    for k in ("hot_only", "dry_only", "compound"):
        boot = effects[region_a][k][0] - effects[region_b][k][0]
        est = effects[region_a][k][1] - effects[region_b][k][1]
        lo, hi = _ci(boot)
        rows.append({"response": response_var, "effect": f"d_{k}", "difference": f"{region_a} - {region_b}",
                     "estimate": est, "ci_low": lo, "ci_high": hi, "sig": bool(lo > 0 or hi < 0),
                     "p_value": bootstrap_p_value(boot)})
    return pd.DataFrame(rows)
