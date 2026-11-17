"""
End-to-end cube-assembly test on a small synthetic grid + short period,
exercising build_raw_cube -> derived vars -> region masks -> full-record
climate anomalies -> time alignment -> vegetation anomalies -> active-season
mask, without any GEE calls.

Uses the shared `small_grid` fixture from conftest.py.
"""
import numpy as np
import pytest
import xarray as xr

from chd import config as cfg
from chd import cube
from .conftest import N_LAT_TEST, N_LON_TEST


def test_build_raw_cube_shapes(small_grid):
    ds = cube.build_raw_cube(raw_dir=small_grid)
    assert ds["tmax_c"].shape == (36, N_LAT_TEST, N_LON_TEST)
    assert ds["gpp_gC_m2"].shape == (36, N_LAT_TEST, N_LON_TEST)
    assert ds["ndvi"].shape == (36, N_LAT_TEST, N_LON_TEST)
    assert "frac_tree_cover" in ds
    assert "india_frac" in ds
    assert ds["tmax_c"].values.mean() == pytest.approx(305 - 273.15, abs=1.0)


def test_full_pipeline_end_to_end(small_grid):
    ds = cube.build_full_cube(raw_dir=small_grid)
    assert len(ds["time"]) == 36
    for var in ["tmax_c", "gpp_gC_m2", "ndvi", "spei03", "vpd_kpa", "tmax_z", "gpp_z",
                "ndvi_z", "sm_z", "category", "category_spi", "active_season"]:
        assert ds[var].dims == ("time", "lat", "lon"), var
    assert np.all(ds["vpd_kpa"].values[~np.isnan(ds["vpd_kpa"].values)] >= 0)
    assert set(np.unique(ds["category"].values)) & {"normal", "hot_only", "dry_only", "compound"}
    assert ds["active_season"].dtype == bool
    assert ds["active_by_month"].dims == ("month", "lat", "lon")
    assert "category_full" in ds and "era5_time" in ds["category_full"].dims
    # lat grid: 37.5 - (i+0.5)*0.25 for i=0..3 -> all > 22N -> none peninsular
    assert not ds["peninsular"].values.any()
    assert ds["is_india"].values.all()


def test_climate_anomalies_use_full_record_baseline(small_grid):
    """Regression test for a real bug: anomalies used to be computed AFTER
    cutting to the study period, so the climatology baseline silently became
    the study period instead of CLIMATOLOGY_START-END. Here the study period
    is a single year (2003) but the baseline is 2001-2003: the old code path
    would have had only one value per calendar month (-> all NaN)."""
    raw = cube.build_raw_cube(raw_dir=small_grid)
    year = raw["era5_time"].dt.year
    raw["tmax_c"] = xr.full_like(raw["tmax_c"], 20.0) + 10.0 * (year == 2003)
    raw = cube.add_derived_variables(raw)
    raw = cube.add_region_masks(raw)
    clim = cube.compute_climate_anomalies(raw, baseline=(2001, 2003))
    aligned = cube.align_to_common_time(clim, 2003, 2003)
    # values 20, 20, 30 -> z(30) = (30 - 23.33) / 5.774 = 1.155 everywhere
    np.testing.assert_allclose(aligned["tmax_z"].values, 1.1547, atol=1e-3)


def test_active_season_excludes_non_india_cells(small_grid):
    """Regression test: statistics used to include neighbouring countries
    because the India mask was applied only when plotting maps."""
    india = np.ones((N_LAT_TEST, N_LON_TEST))
    india[:, :2] = 0.0  # first two columns outside India
    np.savez_compressed(small_grid / "india_mask_0.npz", india=india)
    ds = cube.build_full_cube(raw_dir=small_grid)
    assert not ds["active_season"].values[:, :, :2].any()


def test_ndvi_qa_mask_applied(small_grid):
    ds = cube.build_raw_cube(raw_dir=small_grid)
    ds = cube.add_derived_variables(ds)
    ds = cube.add_region_masks(ds)
    ds = cube.compute_climate_anomalies(ds)
    ds = cube.align_to_common_time(ds, cfg.STUDY_START, cfg.STUDY_END)
    ds["ndvi_qa"][:] = 0.0
    ds["ndvi_qa"][5] = 3.0  # month 6: all cloudy
    ds = cube.compute_vegetation_anomalies(ds)
    assert np.all(np.isnan(ds["ndvi_clean"].values[5]))
    assert not np.all(np.isnan(ds["ndvi_clean"].values[4]))


def test_build_raw_cube_missing_npz_raises(small_grid):
    (small_grid / "gpp_2002.npz").unlink()
    with pytest.raises(FileNotFoundError):
        cube.build_raw_cube(raw_dir=small_grid)


def test_uncorrected_gpp_cache_is_refused(small_grid):
    """Old caches (plain 8-day sums, no monthly_method marker) must not be used."""
    with np.load(small_grid / "gpp_2002.npz") as f:
        g = f["gpp"]
    np.savez_compressed(small_grid / "gpp_2002.npz", gpp=g)
    with pytest.raises(ValueError, match="uncorrected"):
        cube.build_raw_cube(raw_dir=small_grid)
