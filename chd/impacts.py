"""
H1 / H2 analysis on growing-season ("active") cell-months inside India:

  - category composites: mean GPP / NDVI z per stress category, 95% CI
  - joint-bootstrap contrasts: each category vs normal, compound vs dry-only,
    compound vs hot-only, and the amplification index (H2)
  - robustness: the same contrasts with SPI-3 (rainfall only) instead of SPEI-3
  - heat x dryness response surface
  - mechanism check: soil moisture and VPD anomalies by category
  - compound-month frequency map

The cube is flattened once into a long table (one row per active cell-month),
so each analysis is a simple group-by over categories or bins.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from . import config as cfg
from .categories import CATEGORIES
from .stats import year_block_bootstrap_mean, bootstrap_category_contrasts


def cube_to_long_table(ds: xr.Dataset, response_vars=("gpp_z", "ndvi_z")) -> pd.DataFrame:
    """
    Flatten the cube's active-season cell-months into a long DataFrame with
    one row per (time, lat, lon). Columns: time, year, lat, lon, category,
    category_spi, tmax_z, spei03, spi03, sm_z, vpd_z, + response_vars.
    """
    cols = ["category", "category_spi", "tmax_z", "spei03", "spi03", "sm_z", "vpd_z", *response_vars]
    cols = [c for c in cols if c in ds]
    df = ds[cols].where(ds["active_season"]).to_dataframe().reset_index()
    df = df.dropna(subset=["category"])
    df = df[df["category"] != "nan"]
    df["year"] = pd.DatetimeIndex(df["time"]).year
    return df


def category_counts(df: pd.DataFrame, category_col: str = "category") -> pd.DataFrame:
    """Number and share of active cell-months in each stress category."""
    n = df[category_col].value_counts().reindex(list(CATEGORIES)).fillna(0).astype(int)
    return pd.DataFrame({"category": n.index, "n": n.values, "pct": 100 * n.values / n.sum()})


def category_composites(df: pd.DataFrame, response_var: str,
                        category_col: str = "category") -> pd.DataFrame:
    """Mean response_var per stress category with a year-block bootstrap 95% CI."""
    rows = []
    for cat in CATEGORIES:
        g = df[df[category_col] == cat]
        boot = year_block_bootstrap_mean(g[response_var].values, g["year"].values)
        rows.append({"category": cat, "n": boot["n_obs"], "mean": boot["estimate"],
                     "ci_low": boot["ci_low"], "ci_high": boot["ci_high"]})
    return pd.DataFrame(rows)


CONTRASTS = ("d_hot", "d_dry", "d_compound", "compound_minus_dry",
             "compound_minus_hot", "amplification_index")


def category_contrasts(df: pd.DataFrame, response_var: str,
                       category_col: str = "category") -> pd.DataFrame:
    """
    The four category means and the contrasts between them (each category
    minus normal; compound minus dry-only; compound minus hot-only;
    amplification index), all from one *joint* year-block bootstrap so every
    contrast gets a valid 95% CI. A contrast is significant when its CI
    excludes zero (column `<name>_sig`). Returns a one-row DataFrame.
    """
    res = bootstrap_category_contrasts(df[response_var].values, df["year"].values,
                                       df[category_col].values)
    row = {}
    for cat in CATEGORIES:
        row[f"n_{cat}"] = res[f"n_{cat}"]
        row[f"mean_{cat}"] = res[f"mean_{cat}"]["estimate"]
    for name in CONTRASTS:
        row[name] = res[name]["estimate"]
        row[f"{name}_ci_low"] = res[name]["ci_low"]
        row[f"{name}_ci_high"] = res[name]["ci_high"]
        row[f"{name}_sig"] = bool(res[name]["ci_low"] > 0 or res[name]["ci_high"] < 0)
    return pd.DataFrame([row])


def robustness_spei_vs_spi(df: pd.DataFrame, response_vars=("gpp_z", "ndvi_z")) -> pd.DataFrame:
    """
    Repeat the contrasts with drought defined by SPI-3 (CHIRPS rainfall only,
    no temperature in it) instead of SPEI-3 (whose evaporative-demand term
    depends on temperature).
    """
    df_spi = df[df["category_spi"] != "nan"].dropna(subset=["category_spi"])
    rows = []
    for response_var in response_vars:
        for index_name, sub, col in [("SPEI-3", df, "category"), ("SPI-3", df_spi, "category_spi")]:
            r = category_contrasts(sub, response_var, category_col=col).iloc[0].to_dict()
            r.update({"response": response_var, "drought_index": index_name})
            rows.append(r)
    out = pd.DataFrame(rows)
    return out[["response", "drought_index"] + [c for c in out.columns if c not in ("response", "drought_index")]]


def response_surface(df: pd.DataFrame, response_var: str,
                     tz_bins=np.arange(-2.0, 3.01, 0.5),
                     spei_bins=np.arange(-2.5, 2.51, 0.5),
                     min_n: int = cfg.MIN_BIN_N) -> pd.DataFrame:
    """
    Mean response_var in each (Tmax z, SPEI-3) bin of width 0.5. Bins with
    fewer than min_n cell-months get mean = NaN so sparse corners are not
    over-interpreted.
    """
    df = df.copy()
    df["tz_bin"] = pd.cut(df["tmax_z"], tz_bins)
    df["spei_bin"] = pd.cut(df["spei03"], spei_bins)
    out = (df.groupby(["tz_bin", "spei_bin"], observed=True)[response_var]
             .agg(mean="mean", n="count").reset_index())
    out.loc[out["n"] < min_n, "mean"] = np.nan
    return out


def surface_row_means(surface: pd.DataFrame) -> pd.DataFrame:
    """Simple mean of the shown bins in each SPEI-3 row (wettest to driest)."""
    s = surface.dropna(subset=["mean"]).copy()
    s["spei_low"] = s["spei_bin"].map(lambda iv: iv.left).astype(float)
    return (s.groupby("spei_low")["mean"].mean().sort_index(ascending=False)
              .rename("mean_gpp_z").reset_index())


def mechanism_check(df: pd.DataFrame) -> pd.DataFrame:
    """Mean root-zone soil-moisture z and VPD z by category: are compound months
    both the driest in the soil and the 'thirstiest' in the air?"""
    m = df.groupby("category", observed=True)[["sm_z", "vpd_z"]].mean()
    return m.reindex(list(CATEGORIES)).reset_index()


def compound_frequency(ds: xr.Dataset) -> np.ndarray:
    """Share of each India cell's active months that are compound (2D array,
    NaN outside India / where a cell has no active month)."""
    active = ds["active_season"].values
    compound = (ds["category"].values == "compound") & active
    n_active = active.sum(axis=0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        freq = compound.sum(axis=0) / n_active
    return np.where(ds["is_india"].values & (n_active > 0), freq, np.nan)
