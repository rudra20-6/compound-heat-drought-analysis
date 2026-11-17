"""
Recovery analysis (plan section 3.D): aggregate per-cell event tables across
the whole grid, superposed-epoch composites around event onset, and a
preliminary recovery-time summary.

Mid-eval scope only covers the simple median-RT / %-recovered-by-N-months
summary below. Kaplan-Meier survival curves, log-rank tests, severity-tercile
stratification, and the recovery-drivers regression (testing Yao vs Huang vs
Feng) are final-phase work -- see plan section 5.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xarray as xr

from . import config as cfg
from .events import build_event_table
from .stats import year_block_bootstrap_mean


def build_all_events(ds: xr.Dataset) -> pd.DataFrame:
    """
    Run build_event_table (events.py) independently for every grid cell that
    has any active-season data, concatenating into one DataFrame with lat/lon
    columns added. Cells that are entirely inactive or entirely NaN are skipped.
    """
    dates = pd.DatetimeIndex(ds["time"].values)
    lats = ds["lat"].values
    lons = ds["lon"].values

    spei = ds["spei03"].values        # (time, lat, lon)
    tmax_z = ds["tmax_z"].values
    gpp_z = ds["gpp_z"].values
    active = ds["active_season"].values

    tables = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            active_ij = active[:, i, j]
            if not np.any(active_ij):
                continue
            spei_ij = spei[:, i, j]
            tmax_ij = tmax_z[:, i, j]
            gpp_ij = gpp_z[:, i, j]
            if np.all(np.isnan(spei_ij)) or np.all(np.isnan(gpp_ij)):
                continue

            cell_id = f"{lat:.4f}_{lon:.4f}"
            table = build_event_table(dates, spei_ij, tmax_ij, gpp_ij, active_ij, cell_id=cell_id)
            if len(table) == 0:
                continue
            table["lat"] = lat
            table["lon"] = lon
            tables.append(table)

    if not tables:
        return pd.DataFrame(columns=[
            "cell_id", "event_type", "start_date", "end_date", "duration_months",
            "severity", "peak_heat_z", "min_gpp_z", "has_impact",
            "recovery_time_months", "censored", "lat", "lon",
        ])
    return pd.concat(tables, ignore_index=True)


def recovery_summary(events_df: pd.DataFrame, horizons=(3, 6, 12)) -> pd.DataFrame:
    """
    Preliminary recovery summary by event_type, restricted to events with
    impact (min_gpp_z <= impact_z threshold, already filtered into has_impact
    by build_event_table... actually has_impact is a column, filter here):

      - n: number of impactful events
      - n_censored: how many never recovered within their individual horizon
      - median_rt_months: median recovery time among *uncensored* events only
                          (censored events have a lower-bound RT, not a point
                          estimate -- mixing them into a plain median would
                          bias it downward; full phase uses Kaplan-Meier)
      - pct_recovered_within_N: fraction of all impactful events (including
        censored) that recovered within N months
    """
    df = events_df[events_df["has_impact"]].copy()
    rows = []
    for event_type, g in df.groupby("event_type"):
        row = {
            "event_type": event_type,
            "n_events": len(g),
            "n_censored": int(g["censored"].sum()),
            "median_rt_months_uncensored": float(g.loc[~g["censored"], "recovery_time_months"].median())
                if (~g["censored"]).any() else np.nan,
        }
        for h in horizons:
            recovered_by_h = (~g["censored"]) & (g["recovery_time_months"] <= h)
            row[f"pct_recovered_within_{h}m"] = float(recovered_by_h.mean()) if len(g) > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def superposed_epoch_composite(ds: xr.Dataset, events_df: pd.DataFrame,
                                response_var: str = "gpp_z",
                                event_types=("compound", "drought_only", "heat_only"),
                                pre_months: int = 6, post_months: int = 18) -> pd.DataFrame:
    """
    For each event, extract response_var from (start - pre_months) to
    (start + post_months) relative to event start, aligned on relative month
    offset (0 = event start month). Returns a tidy DataFrame with columns
    event_type, offset_months, mean, ci_low, ci_high, n -- ready to plot as
    one line per event_type with a shaded CI band.
    """
    dates = pd.DatetimeIndex(ds["time"].values)
    date_to_idx = {d: i for i, d in enumerate(dates)}
    response = ds[response_var].values  # (time, lat, lon)
    lat_to_i = {round(float(l), 4): i for i, l in enumerate(ds["lat"].values)}
    lon_to_j = {round(float(l), 4): j for j, l in enumerate(ds["lon"].values)}

    offsets = np.arange(-pre_months, post_months + 1)
    rows = []

    for event_type in event_types:
        sub = events_df[events_df["event_type"] == event_type]
        # collect (offset -> list of (value, event_start_year)) for bootstrap
        per_offset_values = {o: [] for o in offsets}
        per_offset_years = {o: [] for o in offsets}

        for _, ev in sub.iterrows():
            i = lat_to_i.get(round(ev["lat"], 4))
            j = lon_to_j.get(round(ev["lon"], 4))
            if i is None or j is None:
                continue
            start_idx = date_to_idx.get(pd.Timestamp(ev["start_date"]))
            if start_idx is None:
                continue
            start_year = pd.Timestamp(ev["start_date"]).year

            for o in offsets:
                idx = start_idx + o
                if 0 <= idx < len(dates):
                    val = response[idx, i, j]
                    if not np.isnan(val):
                        per_offset_values[o].append(val)
                        per_offset_years[o].append(start_year)

        for o in offsets:
            vals = np.array(per_offset_values[o])
            yrs = np.array(per_offset_years[o])
            if len(vals) == 0:
                rows.append({"event_type": event_type, "offset_months": o,
                             "mean": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": 0})
                continue
            boot = year_block_bootstrap_mean(vals, yrs, n_boot=min(cfg.BOOTSTRAP_N, 500))
            rows.append({
                "event_type": event_type, "offset_months": o,
                "mean": boot["estimate"], "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
                "n": len(vals),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Kaplan-Meier recovery analysis (handles censored events properly)
# ---------------------------------------------------------------------------
def kaplan_meier_recovery(events_df: pd.DataFrame, horizons=(3, 6, 12),
                          event_types=("compound", "drought_only", "heat_only")) -> pd.DataFrame:
    """
    For impactful events of each type, fit a Kaplan-Meier curve to recovery
    time with censored events (next event started / end of record / 24-month
    horizon reached before recovery) treated as censored rather than as
    "not recovered". Reports the KM median recovery time (with 95% CI) and
    the KM probability of having recovered by each horizon.
    """
    from lifelines import KaplanMeierFitter
    from lifelines.utils import median_survival_times

    df = events_df[events_df["has_impact"]]
    rows = []
    for et in event_types:
        g = df[df["event_type"] == et]
        if len(g) == 0:
            continue
        km = KaplanMeierFitter().fit(g["recovery_time_months"], event_observed=~g["censored"].astype(bool))
        med_ci = median_survival_times(km.confidence_interval_)
        row = {
            "event_type": et, "n_events": len(g),
            "pct_censored": 100.0 * g["censored"].mean(),
            "km_median_rt": float(km.median_survival_time_),
            "km_median_ci_low": float(med_ci.iloc[0, 0]),
            "km_median_ci_high": float(med_ci.iloc[0, 1]),
        }
        for h in horizons:
            row[f"p_recovered_by_{h}m"] = float(1.0 - km.survival_function_at_times(h).iloc[0])
        rows.append(row)
    return pd.DataFrame(rows)


def logrank_tests(events_df: pd.DataFrame, pairs=(("compound", "drought_only"),
                                                   ("compound", "heat_only"),
                                                   ("drought_only", "heat_only"))) -> pd.DataFrame:
    """
    Log-rank tests between event types' recovery-time distributions.
    NOTE: events from the same cell/year are not independent, so these
    p-values are optimistic (too small); treat them as descriptive.
    """
    from lifelines.statistics import logrank_test
    df = events_df[events_df["has_impact"]]
    rows = []
    for a, b in pairs:
        ga, gb = df[df["event_type"] == a], df[df["event_type"] == b]
        r = logrank_test(ga["recovery_time_months"], gb["recovery_time_months"],
                         event_observed_A=~ga["censored"].astype(bool),
                         event_observed_B=~gb["censored"].astype(bool))
        rows.append({"a": a, "b": b, "test_statistic": float(r.test_statistic), "p_value": float(r.p_value)})
    return pd.DataFrame(rows)


def severity_matched_recovery(events_df: pd.DataFrame, n_bins: int = 3,
                              horizon: int = 12) -> pd.DataFrame:
    """
    Compound drought events are on average longer and more severe droughts
    than drought-only events, so a raw compound-vs-drought comparison mixes
    up "added heat" with "worse drought". Here impactful drought events
    (compound + drought_only) are split into terciles of drought severity
    (sum of SPEI deficit) and the two types are compared *within* each
    tercile: Kaplan-Meier median and P(recovered by horizon) per type, plus a
    log-rank p-value per tercile (optimistic: events are not independent).
    """
    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test
    df = events_df[events_df["has_impact"] & events_df["event_type"].isin(["compound", "drought_only"])].copy()
    df["severity_bin"] = pd.qcut(df["severity"], n_bins, labels=[f"T{i+1}" for i in range(n_bins)])
    rows = []
    for sev_bin, gb in df.groupby("severity_bin", observed=True):
        a = gb[gb["event_type"] == "compound"]
        d = gb[gb["event_type"] == "drought_only"]
        lr = logrank_test(a["recovery_time_months"], d["recovery_time_months"],
                          event_observed_A=~a["censored"].astype(bool),
                          event_observed_B=~d["censored"].astype(bool))
        for et, g in (("compound", a), ("drought_only", d)):
            km = KaplanMeierFitter().fit(g["recovery_time_months"], event_observed=~g["censored"].astype(bool))
            rows.append({
                "severity_bin": str(sev_bin), "event_type": et, "n_events": len(g),
                "median_severity": float(g["severity"].median()),
                "km_median_rt": float(km.median_survival_time_),
                f"p_recovered_by_{horizon}m": float(1.0 - km.survival_function_at_times(horizon).iloc[0]),
                "logrank_p_within_bin": float(lr.p_value),
            })
    return pd.DataFrame(rows)
