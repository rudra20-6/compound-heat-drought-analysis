import numpy as np
import pandas as pd
import xarray as xr
import pytest

from chd import config as cfg
from chd.recovery import build_all_events, recovery_summary, superposed_epoch_composite


def _toy_cube(n_months=48, n_lat=2, n_lon=2, seed=0):
    """
    Minimal synthetic cube with just the fields recovery.py needs
    (spei03, tmax_z, gpp_z, active_season, time/lat/lon coords), with a
    hand-injected compound event + recovery trajectory in cell (0,0).
    """
    rng = np.random.default_rng(seed)
    time = pd.date_range("2001-01-01", periods=n_months, freq="MS")
    lat = np.array([30.0, 25.0])
    lon = np.array([75.0, 80.0])

    spei = rng.normal(0, 0.5, (n_months, n_lat, n_lon))
    tmax_z = rng.normal(0, 0.5, (n_months, n_lat, n_lon))
    gpp_z = rng.normal(0, 0.3, (n_months, n_lat, n_lon))
    active = np.ones((n_months, n_lat, n_lon), dtype=bool)

    # inject one compound drought event at months 10-13 in cell (0,0), with a
    # GPP crash that recovers by month 20 (2 consecutive good months)
    spei[10:14, 0, 0] = -1.5
    tmax_z[10:14, 0, 0] = 1.3
    gpp_z[10:18, 0, 0] = -1.5
    gpp_z[18:, 0, 0] = 0.2  # recovered for the remainder

    ds = xr.Dataset(
        data_vars=dict(
            spei03=(("time", "lat", "lon"), spei),
            tmax_z=(("time", "lat", "lon"), tmax_z),
            gpp_z=(("time", "lat", "lon"), gpp_z),
            active_season=(("time", "lat", "lon"), active),
        ),
        coords=dict(time=time, lat=lat, lon=lon),
    )
    return ds


def test_build_all_events_finds_injected_event():
    ds = _toy_cube()
    events = build_all_events(ds)
    assert len(events) >= 1
    compound = events[events["event_type"] == "compound"]
    assert len(compound) == 1
    row = compound.iloc[0]
    assert row["lat"] == 30.0 and row["lon"] == 75.0
    assert row["duration_months"] == 4
    assert row["has_impact"] == True


def test_build_all_events_skips_inactive_cells():
    ds = _toy_cube()
    ds["active_season"].values[:] = False  # nothing active anywhere
    events = build_all_events(ds)
    assert len(events) == 0


def test_recovery_summary_basic_columns_and_values():
    ds = _toy_cube()
    events = build_all_events(ds)
    summary = recovery_summary(events, horizons=(3, 6, 12))
    assert "median_rt_months_uncensored" in summary.columns
    assert "pct_recovered_within_12m" in summary.columns
    compound_row = summary[summary["event_type"] == "compound"].iloc[0]
    assert compound_row["n_events"] == 1
    assert compound_row["n_censored"] == 0  # our injected event does recover


def test_superposed_epoch_composite_shapes_and_alignment():
    ds = _toy_cube()
    events = build_all_events(ds)
    composite = superposed_epoch_composite(ds, events, response_var="gpp_z",
                                            event_types=("compound",),
                                            pre_months=6, post_months=18)
    assert set(composite["offset_months"]) == set(range(-6, 19))
    # at offset 0 (event start month), n should be >=1 (our one compound event)
    row0 = composite[composite["offset_months"] == 0].iloc[0]
    assert row0["n"] >= 1
    # the composite mean around offset +3 (inside the crash window) should be
    # much lower than around offset -3 (before the event)
    pre = composite[composite["offset_months"] == -3]["mean"].iloc[0]
    during = composite[composite["offset_months"] == 3]["mean"].iloc[0]
    assert during < pre


def test_kaplan_meier_handles_censoring():
    from chd.recovery import kaplan_meier_recovery
    # 10 events recover at month 2; 10 are censored at month 1 (e.g. a new
    # event started). A naive "% recovered within 3 months" says 50%; KM
    # correctly treats the censored ones as unknown -> P(recovered by 3) = 1.
    df = pd.DataFrame({
        "event_type": ["compound"] * 20,
        "has_impact": True,
        "recovery_time_months": [2.0] * 10 + [1.0] * 10,
        "censored": [False] * 10 + [True] * 10,
    })
    km = kaplan_meier_recovery(df, horizons=(3,), event_types=("compound",))
    assert km.iloc[0]["p_recovered_by_3m"] == pytest.approx(1.0)
    assert km.iloc[0]["km_median_rt"] == pytest.approx(2.0)
