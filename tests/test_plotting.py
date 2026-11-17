"""Smoke tests for plotting.py: confirm each figure function runs end-to-end
and writes a PNG, using tiny synthetic inputs. Not testing visual content."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless, no display needed

from chd import config as cfg
from chd import plotting as plot


def test_plot_category_composite_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    df = pd.DataFrame({
        "category": ["normal", "hot_only", "dry_only", "compound"],
        "mean": [0.0, -1.0, -1.2, -3.0],
        "ci_low": [-0.2, -1.3, -1.5, -3.5],
        "ci_high": [0.2, -0.7, -0.9, -2.5],
        "n": [100, 80, 70, 40],
        "flagged_low_n": [False, False, False, False],
    })
    fig = plot.plot_category_composite(df, "GPP z-score", "Test", "cat_composite")
    assert (tmp_path / "cat_composite.png").exists()


def test_plot_response_surface_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    tz_bins = pd.IntervalIndex.from_breaks([-2, -1, 0, 1, 2])
    spei_bins = pd.IntervalIndex.from_breaks([-2, -1, 0, 1, 2])
    rows = []
    for tz in tz_bins:
        for sp in spei_bins:
            rows.append({"tz_bin": tz, "spei_bin": sp, "mean": np.random.randn(), "n": 50})
    df = pd.DataFrame(rows)
    plot.plot_response_surface(df, "GPP z", "Test surface", "surface")
    assert (tmp_path / "surface.png").exists()


def test_plot_amplification_by_stratum_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    df = pd.DataFrame({"landcover": ["tree", "crop", "grass"],
                        "amplification_index": [-2.0, -0.5, 0.3]})
    plot.plot_amplification_by_stratum(df, "landcover", "Test AI", "ai_strata")
    assert (tmp_path / "ai_strata.png").exists()


def test_plot_area_trend_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    df = pd.DataFrame({"year": range(1991, 2024), "pct_area": np.random.uniform(0, 20, 33)})
    trend = {"slope": 0.2, "intercept": 5.0, "p_value": 0.01}
    plot.plot_area_trend(df, trend, "Test trend", "trend")
    assert (tmp_path / "trend.png").exists()


def test_plot_recovery_composite_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    offsets = range(-6, 19)
    rows = []
    for et in ["compound", "drought_only", "heat_only"]:
        for o in offsets:
            rows.append({"event_type": et, "offset_months": o,
                         "mean": np.random.randn(), "ci_low": -1, "ci_high": 1, "n": 10})
    df = pd.DataFrame(rows)
    plot.plot_recovery_composite(df, "GPP z", "Test recovery", "recovery")
    assert (tmp_path / "recovery.png").exists()


def test_plot_map_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    data = np.random.randn(10, 12)
    lat = np.linspace(6, 37.5, 10)
    lon = np.linspace(68, 98, 12)
    plot.plot_map(data, lat, lon, "Test map", "map", cbar_label="z-score")
    assert (tmp_path / "map.png").exists()


def test_plot_qc_timeseries_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)
    dates = pd.date_range("1991-01-01", periods=120, freq="MS")
    series = {"Tmax anomaly": np.random.randn(120), "Rainfall anomaly": np.random.randn(120)}
    plot.plot_qc_timeseries(dates, series, "Test QC", "qc", known_event_years=[2002, 2009])
    assert (tmp_path / "qc.png").exists()
