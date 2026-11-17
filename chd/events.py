"""
Stress-category classification (2x2: Normal/Hot-only/Dry-only/Compound)
and event segmentation (contiguous drought / heat runs) for recovery analysis.

Pure functions operating on 1-D numpy arrays (single grid cell) so they are
directly unit-testable on hand-built synthetic series (tests/test_events.py).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import THRESH

CATEGORY_NORMAL = "normal"
CATEGORY_HOT_ONLY = "hot_only"
CATEGORY_DRY_ONLY = "dry_only"
CATEGORY_COMPOUND = "compound"

CATEGORIES = (CATEGORY_NORMAL, CATEGORY_HOT_ONLY, CATEGORY_DRY_ONLY, CATEGORY_COMPOUND)


def classify_months(tmax_z: np.ndarray, spei: np.ndarray,
                     hot_z: float = THRESH.hot_z,
                     dry_spei: float = THRESH.dry_spei) -> np.ndarray:
    """
    Classify each cell-month into one of the 4 stress categories.

    Returns an object array of strings (NaN input -> None / "nan").
    hot  := tmax_z >= hot_z
    dry  := spei   <= dry_spei
    """
    tmax_z = np.asarray(tmax_z, dtype=float)
    spei = np.asarray(spei, dtype=float)
    n = len(tmax_z)
    out = np.full(n, "nan", dtype=object)

    valid = ~np.isnan(tmax_z) & ~np.isnan(spei)
    hot = tmax_z >= hot_z
    dry = spei <= dry_spei

    out[valid & ~hot & ~dry] = CATEGORY_NORMAL
    out[valid & hot & ~dry] = CATEGORY_HOT_ONLY
    out[valid & ~hot & dry] = CATEGORY_DRY_ONLY
    out[valid & hot & dry] = CATEGORY_COMPOUND
    return out


def _find_runs(mask: np.ndarray, min_len: int) -> list[tuple[int, int]]:
    """Return list of (start_idx, end_idx_inclusive) for True-runs of length >= min_len."""
    runs = []
    n = len(mask)
    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and mask[j + 1]:
            j += 1
        if (j - i + 1) >= min_len:
            runs.append((i, j))
        i = j + 1
    return runs


@dataclass
class EventRecord:
    event_type: str          # "drought" or "heat_only"
    is_compound: bool
    start_idx: int
    end_idx: int              # inclusive
    duration: int
    severity: float           # sum of SPEI deficits (drought) or sum of tmax_z (heat)
    peak_heat: float           # max tmax_z during event
    min_gpp_z: float           # min GPP z from event start to end+1 month (resistance)
    has_impact: bool           # min_gpp_z <= impact_z threshold
    recovery_time: float       # months after event end until recovered; NaN if never computed
    censored: bool             # True if recovery_time hit the censor horizon / next event / end


def segment_drought_events(spei: np.ndarray, tmax_z: np.ndarray,
                            min_len: int = THRESH.min_event_months,
                            dry_spei: float = THRESH.dry_spei,
                            hot_z: float = THRESH.hot_z,
                            compound_frac: float = THRESH.compound_event_frac
                            ) -> list[tuple[int, int, bool]]:
    """
    Segment contiguous SPEI <= dry_spei runs (length >= min_len) into drought
    events, flagging each as compound if the fraction of its months with
    tmax_z >= hot_z exceeds `compound_frac` (default: any month, frac=0 means
    "at least one hot month" since we use > comparison against 0 count... see
    note below).

    Returns list of (start_idx, end_idx_inclusive, is_compound).
    """
    spei = np.asarray(spei, dtype=float)
    tmax_z = np.asarray(tmax_z, dtype=float)
    dry_mask = np.nan_to_num(spei, nan=np.inf) <= dry_spei
    runs = _find_runs(dry_mask, min_len)

    out = []
    for (s, e) in runs:
        seg_heat = tmax_z[s:e + 1]
        valid_heat = seg_heat[~np.isnan(seg_heat)]
        if len(valid_heat) == 0:
            frac_hot = 0.0
        else:
            frac_hot = np.mean(valid_heat >= hot_z)
        is_compound = frac_hot > compound_frac if compound_frac > 0 else frac_hot > 0
        out.append((s, e, is_compound))
    return out


def segment_heat_only_events(tmax_z: np.ndarray, spei: np.ndarray,
                              min_len: int = THRESH.min_event_months,
                              hot_z: float = THRESH.hot_z,
                              dry_spei: float = THRESH.dry_spei
                              ) -> list[tuple[int, int]]:
    """
    Segment contiguous tmax_z >= hot_z runs where SPEI stays above dry_spei
    throughout (i.e. "pure" heat events, no drought overlap at all).
    """
    tmax_z = np.asarray(tmax_z, dtype=float)
    spei = np.asarray(spei, dtype=float)
    hot_mask = np.nan_to_num(tmax_z, nan=-np.inf) >= hot_z
    runs = _find_runs(hot_mask, min_len)

    out = []
    for (s, e) in runs:
        seg_spei = spei[s:e + 1]
        valid_spei = seg_spei[~np.isnan(seg_spei)]
        if len(valid_spei) > 0 and np.any(valid_spei <= dry_spei):
            continue  # overlaps drought -> not "pure" heat-only, handled by drought segmentation
        out.append((s, e))
    return out


def compute_recovery(gpp_z: np.ndarray, active_mask: np.ndarray,
                      event_end_idx: int, next_event_start_idx: int | None,
                      recovered_z: float = THRESH.recovered_z,
                      censor_months: int = THRESH.censor_months) -> tuple[float, bool]:
    """
    Compute recovery time (in months, counted on *active* months only, i.e.
    among months where active_mask is True) after an event ends.

    "Recovered" = first month m (after event_end_idx) such that gpp_z[m] >=
    recovered_z AND the next active month after m also has gpp_z >= recovered_z
    (2 consecutive active months above threshold).

    Recovery time is measured in calendar months from event_end_idx to the
    first month of that 2-month recovered window.

    Returns (recovery_time, censored). If recovery never occurs before the
    censor horizon, the next event, or the end of series, returns
    (censor_horizon_used, True) where censor_horizon_used is the number of
    months actually searched (for Kaplan-Meier censoring in the final phase).
    """
    gpp_z = np.asarray(gpp_z, dtype=float)
    active_mask = np.asarray(active_mask, dtype=bool)
    n = len(gpp_z)

    horizon = n - 1 if next_event_start_idx is None else min(n - 1, next_event_start_idx - 1)
    horizon = min(horizon, event_end_idx + censor_months)

    # indices of active months strictly after the event, up to horizon
    candidates = [i for i in range(event_end_idx + 1, horizon + 1) if active_mask[i]]

    for k in range(len(candidates) - 1):
        i, i_next = candidates[k], candidates[k + 1]
        if gpp_z[i] >= recovered_z and gpp_z[i_next] >= recovered_z:
            return float(i - event_end_idx), False

    # not recovered within horizon -> censored
    return float(horizon - event_end_idx), True


def build_event_table(dates: pd.DatetimeIndex, spei: np.ndarray, tmax_z: np.ndarray,
                       gpp_z: np.ndarray, active_mask: np.ndarray,
                       cell_id: str = "") -> pd.DataFrame:
    """
    Full per-cell pipeline: segment drought + heat-only events, compute
    severity/duration/resistance/recovery for each, return a tidy DataFrame.
    """
    drought_events = segment_drought_events(spei, tmax_z)
    heat_events = segment_heat_only_events(tmax_z, spei)

    all_events = []
    for (s, e, is_compound) in drought_events:
        all_events.append({
            "event_type": "compound" if is_compound else "drought_only",
            "start_idx": s, "end_idx": e,
        })
    for (s, e) in heat_events:
        all_events.append({"event_type": "heat_only", "start_idx": s, "end_idx": e})

    all_events.sort(key=lambda d: d["start_idx"])
    rows = []
    for idx, ev in enumerate(all_events):
        s, e = ev["start_idx"], ev["end_idx"]
        duration = e - s + 1
        seg_spei = spei[s:e + 1]
        seg_tmax = tmax_z[s:e + 1]
        severity = float(np.nansum(np.clip(-seg_spei, 0, None))) if ev["event_type"] != "heat_only" \
            else float(np.nansum(np.clip(seg_tmax, 0, None)))
        peak_heat = float(np.nanmax(seg_tmax)) if np.any(~np.isnan(seg_tmax)) else np.nan

        resist_end = min(e + 1, len(gpp_z) - 1)
        seg_gpp = gpp_z[s:resist_end + 1]
        min_gpp_z = float(np.nanmin(seg_gpp)) if np.any(~np.isnan(seg_gpp)) else np.nan
        has_impact = (not np.isnan(min_gpp_z)) and (min_gpp_z <= THRESH.impact_z)

        next_start = all_events[idx + 1]["start_idx"] if idx + 1 < len(all_events) else None
        rt, censored = compute_recovery(gpp_z, active_mask, e, next_start)

        rows.append({
            "cell_id": cell_id,
            "event_type": ev["event_type"],
            "start_date": dates[s], "end_date": dates[e],
            "duration_months": duration,
            "severity": severity,
            "peak_heat_z": peak_heat,
            "min_gpp_z": min_gpp_z,
            "has_impact": has_impact,
            "recovery_time_months": rt,
            "censored": censored,
        })

    return pd.DataFrame(rows)
