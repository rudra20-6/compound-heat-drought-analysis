"""Shared pytest fixtures: a small synthetic grid + period standing in for
the real India cube, so cube/impacts tests never need live Earth Engine data.
"""
import numpy as np
import pytest

from chd import config as cfg

N_LAT_TEST, N_LON_TEST = 4, 5
YEARS = (2001, 2003)  # 3 years = 36 months


@pytest.fixture
def small_grid(tmp_path, monkeypatch):
    """Monkeypatch config to a tiny grid + short period, write synthetic .npz caches."""
    monkeypatch.setattr(cfg, "N_LAT", N_LAT_TEST)
    monkeypatch.setattr(cfg, "N_LON", N_LON_TEST)
    monkeypatch.setattr(cfg, "AFFINE", (68.0, 0.25, 0.0, 37.5, 0.0, -0.25))
    monkeypatch.setattr(cfg, "FETCH_START", YEARS[0])
    monkeypatch.setattr(cfg, "FETCH_END", YEARS[1])
    monkeypatch.setattr(cfg, "GPP_START", YEARS[0])
    monkeypatch.setattr(cfg, "GPP_END", YEARS[1])
    monkeypatch.setattr(cfg, "NDVI_START", YEARS[0])
    monkeypatch.setattr(cfg, "NDVI_END", YEARS[1])
    monkeypatch.setattr(cfg, "STUDY_START", YEARS[0])
    monkeypatch.setattr(cfg, "STUDY_END", YEARS[1])
    monkeypatch.setattr(cfg, "CLIMATOLOGY_START", YEARS[0])
    monkeypatch.setattr(cfg, "CLIMATOLOGY_END", YEARS[1])
    monkeypatch.setattr(cfg, "DATA_RAW", tmp_path)

    rng = np.random.default_rng(0)
    shape = (12, N_LAT_TEST, N_LON_TEST)

    for year in range(YEARS[0], YEARS[1] + 1):
        era5 = dict(
            tmax_k=rng.normal(305, 3, shape),
            t2m_k=rng.normal(300, 3, shape),
            dewpoint_k=rng.normal(290, 3, shape),
            swvl1=rng.uniform(0.1, 0.3, shape),
            swvl2=rng.uniform(0.1, 0.3, shape),
            swvl3=rng.uniform(0.1, 0.3, shape),
        )
        np.savez_compressed(tmp_path / f"era5_{year}.npz", **era5)

        np.savez_compressed(tmp_path / f"chirps_{year}.npz",
                             precip=rng.gamma(2.0, 30.0, shape))

        spei = {f"spei_{ts:02d}": rng.normal(0, 1, shape) for ts in (1, 3, 6)}
        np.savez_compressed(tmp_path / f"spei_{year}.npz", **spei)

        np.savez_compressed(tmp_path / f"gpp_{year}.npz",
                             gpp=rng.uniform(50, 300, shape),
                             monthly_method=np.array("daily_rate_x_days_in_month"))

        np.savez_compressed(tmp_path / f"ndvi_{year}.npz",
                             ndvi=rng.uniform(0.2, 0.8, shape),
                             qa=np.zeros(shape))

    wc = {
        "tree_cover": np.full((N_LAT_TEST, N_LON_TEST), 0.4),
        "cropland": np.full((N_LAT_TEST, N_LON_TEST), 0.3),
        "water": np.full((N_LAT_TEST, N_LON_TEST), 0.1),
    }
    np.savez_compressed(tmp_path / "worldcover_0.npz", **wc)
    np.savez_compressed(tmp_path / "india_mask_0.npz",
                         india=np.full((N_LAT_TEST, N_LON_TEST), 1.0))

    return tmp_path
