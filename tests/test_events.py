import numpy as np
import pandas as pd
import pytest

from chd.events import (
    classify_months, segment_drought_events, segment_heat_only_events,
    compute_recovery, build_event_table, CATEGORY_NORMAL, CATEGORY_HOT_ONLY,
    CATEGORY_DRY_ONLY, CATEGORY_COMPOUND,
)


def test_classify_months_all_four_categories():
    tmax_z = np.array([0.0, 1.5, 0.0, 1.5, np.nan])
    spei = np.array([0.0, 0.0, -1.5, -1.5, -1.5])
    cats = classify_months(tmax_z, spei)
    assert list(cats) == [CATEGORY_NORMAL, CATEGORY_HOT_ONLY, CATEGORY_DRY_ONLY,
                           CATEGORY_COMPOUND, "nan"]


def test_classify_months_threshold_boundary():
    # exactly at threshold counts as triggered (>=, <=)
    tmax_z = np.array([1.0, 0.99])
    spei = np.array([0.0, 0.0])
    cats = classify_months(tmax_z, spei, hot_z=1.0)
    assert cats[0] == CATEGORY_HOT_ONLY
    assert cats[1] == CATEGORY_NORMAL


def test_segment_drought_events_basic_run():
    # drought from idx 2-5 (4 months), with a hot month at idx 3 -> compound
    spei = np.array([0.5, 0.2, -1.2, -1.5, -1.1, -1.3, 0.1, -0.5])
    tmax_z = np.array([0.0, 0.0, 0.2, 1.3, 0.3, 0.2, 0.0, 0.0])
    events = segment_drought_events(spei, tmax_z, min_len=2)
    assert len(events) == 1
    s, e, is_compound = events[0]
    assert (s, e) == (2, 5)
    assert bool(is_compound) is True


def test_segment_drought_events_too_short_excluded():
    spei = np.array([0.5, -1.5, 0.3, 0.2])  # only 1 month below threshold
    tmax_z = np.zeros(4)
    events = segment_drought_events(spei, tmax_z, min_len=2)
    assert events == []


def test_segment_drought_events_pure_drought_not_compound():
    spei = np.array([0.0, -1.2, -1.3, -1.1, 0.0])
    tmax_z = np.array([0.0, 0.0, 0.0, 0.0, 0.0])  # never hot
    events = segment_drought_events(spei, tmax_z, min_len=2)
    assert len(events) == 1
    _, _, is_compound = events[0]
    assert bool(is_compound) is False


def test_segment_heat_only_excludes_drought_overlap():
    # hot run at idx 1-3, but SPEI dips below threshold inside it -> excluded
    tmax_z = np.array([0.0, 1.5, 1.6, 1.4, 0.0])
    spei = np.array([0.0, 0.0, -1.3, 0.0, 0.0])
    events = segment_heat_only_events(tmax_z, spei, min_len=2)
    assert events == []


def test_segment_heat_only_pure_heat_run():
    tmax_z = np.array([0.0, 1.5, 1.6, 1.4, 0.0])
    spei = np.array([0.0, 0.1, 0.2, -0.3, 0.0])  # stays above dry threshold
    events = segment_heat_only_events(tmax_z, spei, min_len=2)
    assert events == [(1, 3)]


def test_compute_recovery_recovers_after_two_consecutive_good_months():
    # event ends at idx 4. months 5,6 active with gpp_z below threshold (still bad),
    # months 7,8 active with gpp_z >= recovered_z -> recovery_time = 7-4 = 3
    gpp_z = np.array([0, 0, 0, 0, 0, -2.0, -1.0, -0.3, -0.2, 0, 0])
    active = np.ones(len(gpp_z), dtype=bool)
    rt, censored = compute_recovery(gpp_z, active, event_end_idx=4,
                                     next_event_start_idx=None,
                                     recovered_z=-0.5, censor_months=24)
    assert rt == 3.0
    assert censored is False


def test_compute_recovery_skips_inactive_months():
    # month 6 (good) is inactive and should be skipped as a candidate;
    # recovery should instead require months 7 & 8 to both be active+good
    gpp_z =   np.array([0, 0, 0, 0, 0, -2.0, -0.1, -0.2, -0.3, 0, 0])
    active =  np.array([1, 1, 1, 1, 1,  1,     0,    1,    1,  1, 1], dtype=bool)
    rt, censored = compute_recovery(gpp_z, active, event_end_idx=4,
                                     next_event_start_idx=None,
                                     recovered_z=-0.5, censor_months=24)
    # candidates after idx4: 5(bad),7(good),8(good) -> pair (7,8) both good
    assert rt == 3.0  # 7 - 4
    assert censored is False


def test_compute_recovery_censored_at_horizon():
    gpp_z = np.full(30, -2.0)  # never recovers
    active = np.ones(30, dtype=bool)
    rt, censored = compute_recovery(gpp_z, active, event_end_idx=0,
                                     next_event_start_idx=None,
                                     recovered_z=-0.5, censor_months=10)
    assert censored is True
    assert rt == 10.0


def test_compute_recovery_censored_by_next_event():
    gpp_z = np.full(30, -2.0)
    active = np.ones(30, dtype=bool)
    rt, censored = compute_recovery(gpp_z, active, event_end_idx=0,
                                     next_event_start_idx=5,
                                     recovered_z=-0.5, censor_months=24)
    assert censored is True
    assert rt == 4.0  # horizon = min(29, 5-1=4, 0+24) = 4; 4-0


def test_build_event_table_end_to_end_synthetic():
    dates = pd.date_range("2001-01-01", periods=36, freq="MS")
    n = len(dates)
    spei = np.zeros(n)
    tmax_z = np.zeros(n)
    gpp_z = np.zeros(n)
    active = np.ones(n, dtype=bool)

    # Inject one compound event at months 10-13 with a GPP crash and later recovery
    spei[10:14] = -1.5
    tmax_z[10:14] = 1.2
    gpp_z[10:16] = -1.5
    gpp_z[16:] = 0.0  # recovers fully after

    df = build_event_table(dates, spei, tmax_z, gpp_z, active, cell_id="test_cell")
    assert len(df) == 1
    row = df.iloc[0]
    assert row["event_type"] == "compound"
    assert row["duration_months"] == 4
    assert row["has_impact"] == True
    assert row["censored"] == False
    assert row["recovery_time_months"] >= 0
