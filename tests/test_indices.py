import numpy as np
import pandas as pd
import pytest

from chd.indices import (
    monthly_zscore_1d, spi_1d, saturation_vapor_pressure_kpa, vpd_kpa,
    root_zone_soil_moisture,
)


def _monthly_index(n_years, start_year=1991):
    dates = pd.date_range(f"{start_year}-01-01", periods=n_years * 12, freq="MS")
    return dates.month.values, dates.year.values, dates


def test_monthly_zscore_mean_zero_std_one_per_month():
    rng = np.random.default_rng(0)
    months, years, _ = _monthly_index(30)
    n = len(months)
    # synthetic: different mean/std per calendar month, no trend
    base_mean = {m: 10 + m for m in range(1, 13)}
    base_std = {m: 2 + 0.1 * m for m in range(1, 13)}
    values = np.array([rng.normal(base_mean[m], base_std[m]) for m in months])

    z = monthly_zscore_1d(values, months, detrend=False)
    assert not np.any(np.isnan(z))
    for m in range(1, 13):
        sel = months == m
        assert abs(np.mean(z[sel])) < 0.3          # near zero
        assert abs(np.std(z[sel], ddof=1) - 1) < 0.3  # near unit std


def test_monthly_zscore_detrend_removes_linear_trend():
    months, years, _ = _monthly_index(30)
    n = len(months)
    t = np.arange(n)
    # strong linear trend + small noise, same for all months
    rng = np.random.default_rng(1)
    values = 5.0 + 0.05 * t + rng.normal(0, 0.1, n)

    z_detrend = monthly_zscore_1d(values, months, detrend=True)
    z_plain = monthly_zscore_1d(values, months, detrend=False)

    # Detrended z should show much weaker correlation with time than plain z
    corr_detrend = np.corrcoef(t, z_detrend)[0, 1]
    corr_plain = np.corrcoef(t, z_plain)[0, 1]
    assert abs(corr_detrend) < abs(corr_plain)
    assert abs(corr_detrend) < 0.3


def test_monthly_zscore_respects_baseline_mask():
    months, years, _ = _monthly_index(35)  # 1991-2025, so some years fall after 2020
    rng = np.random.default_rng(2)
    values = rng.normal(10, 2, len(months))
    # shift post-2020 values up a lot -- baseline stats should ignore them
    values[years > 2020] += 50

    baseline_mask = years <= 2020
    z = monthly_zscore_1d(values, months, baseline_mask=baseline_mask)
    # post-2020 months should have large positive z (far outside baseline)
    assert np.mean(z[years > 2020]) > 5


def test_monthly_zscore_nan_propagates():
    months, years, _ = _monthly_index(5)
    values = np.full(len(months), 1.0)
    values[3] = np.nan
    z = monthly_zscore_1d(values, months)
    assert np.isnan(z[3])


def test_spi_on_synthetic_gamma_recovers_standard_normal():
    """
    Generate precipitation from a known gamma distribution (no seasonality,
    single calendar month repeated) and check the resulting SPI-1 values
    are approximately standard normal.
    """
    rng = np.random.default_rng(3)
    n_years = 60
    shape, scale = 2.0, 30.0
    precip = rng.gamma(shape, scale, size=n_years)
    months = np.full(n_years, 6)  # pretend every entry is June

    spi = spi_1d(precip, months, window=1)
    valid = ~np.isnan(spi)
    assert valid.sum() > n_years - 5
    assert abs(np.mean(spi[valid])) < 0.3
    assert abs(np.std(spi[valid]) - 1) < 0.3


def test_spi_handles_zero_precipitation():
    rng = np.random.default_rng(4)
    n_years = 60
    precip = rng.gamma(2.0, 20.0, size=n_years)
    precip[::5] = 0.0  # 20% zeros
    months = np.full(n_years, 1)

    spi = spi_1d(precip, months, window=1)
    assert not np.all(np.isnan(spi))
    # zero-precip months should get the most negative (driest) SPI values
    zero_idx = np.flatnonzero(precip == 0)
    nonzero_idx = np.flatnonzero(precip > 0)
    assert np.nanmean(spi[zero_idx]) < np.nanmean(spi[nonzero_idx])


def test_spi_rolling_window_requires_consecutive_valid_months():
    rng = np.random.default_rng(5)
    months = np.tile(np.arange(1, 13), 10)
    precip = rng.gamma(3.0, 20.0, size=len(months))  # needs variance for gamma.fit
    precip[5] = np.nan
    spi = spi_1d(precip, months, window=3)
    # the 3-month windows ending at indices 5,6,7 should be NaN (contain the gap)
    assert np.isnan(spi[5]) and np.isnan(spi[6]) and np.isnan(spi[7])


def test_vpd_zero_when_saturated():
    # dewpoint == temperature -> VPD should be ~0
    t = np.array([25.0, 30.0, 15.0])
    vpd = vpd_kpa(t, t)
    assert np.allclose(vpd, 0, atol=1e-8)


def test_vpd_increases_with_temperature_dewpoint_gap():
    t = np.array([30.0, 30.0])
    td = np.array([28.0, 10.0])
    vpd = vpd_kpa(t, td)
    assert vpd[1] > vpd[0]  # bigger T-Td gap -> bigger VPD
    assert np.all(vpd >= 0)


def test_saturation_vapor_pressure_monotonic_in_temperature():
    temps = np.array([0, 10, 20, 30, 40])
    es = saturation_vapor_pressure_kpa(temps)
    assert np.all(np.diff(es) > 0)


def test_root_zone_soil_moisture_weighted_average():
    # if all layers equal, weighted mean should equal that value regardless of weights
    swvl1 = np.array([0.3, 0.2])
    swvl2 = np.array([0.3, 0.2])
    swvl3 = np.array([0.3, 0.2])
    rz = root_zone_soil_moisture(swvl1, swvl2, swvl3)
    assert np.allclose(rz, [0.3, 0.2])

    # weighting sanity: deepest layer (layer3, largest weight) should dominate
    swvl1b = np.array([1.0])
    swvl2b = np.array([0.0])
    swvl3b = np.array([0.0])
    rz_b = root_zone_soil_moisture(swvl1b, swvl2b, swvl3b)
    assert 0 < rz_b[0] < 0.2  # layer1 has smallest weight (7/100)


@pytest.mark.parametrize("detrend", [False, True])
def test_vectorised_zscore_matches_per_cell_version(detrend):
    """monthly_zscore_array (used in production) must reproduce
    monthly_zscore_1d (the reference implementation) cell by cell."""
    from chd.indices import monthly_zscore_array
    rng = np.random.default_rng(11)
    months, years, _ = _monthly_index(25)
    n = len(months)
    arr = rng.normal(10, 2, (n, 3, 4)) + 0.03 * np.arange(n)[:, None, None]
    arr[rng.random(arr.shape) < 0.05] = np.nan  # scattered gaps
    base = years <= 2010
    vec = monthly_zscore_array(arr, months, detrend=detrend, baseline_mask=base)
    for i in range(3):
        for j in range(4):
            ref = monthly_zscore_1d(arr[:, i, j], months, detrend=detrend, baseline_mask=base)
            np.testing.assert_allclose(vec[:, i, j], ref, rtol=1e-9, atol=1e-9, equal_nan=True)


def test_modis_8day_coverage_covers_whole_year():
    from chd.indices import modis_8day_coverage_days
    assert modis_8day_coverage_days(2003).sum() == 365
    assert modis_8day_coverage_days(2004).sum() == 366


def test_modis_8day_leap_year_shift():
    """Regression test for the leap-year bug: in leap years DOY 121 is 30 April
    and DOY 305 is 31 October, so April/October gain a composite and May/November
    lose one."""
    from chd.indices import modis_8day_coverage_days
    non, leap = modis_8day_coverage_days(2003), modis_8day_coverage_days(2004)
    assert (non[3], non[4], non[9], non[10]) == (24, 32, 24, 32)
    assert (leap[3], leap[4], leap[9], leap[10]) == (32, 24, 32, 24)


def test_composite_sums_to_monthly_constant_rate():
    """A constant daily GPP rate must give rate x days-in-month in every month
    of both leap and non-leap years, whatever the composite count."""
    from chd.indices import composite_sums_to_monthly, modis_8day_coverage_days, days_in_months
    rate = 3.0
    for year in (2003, 2004):
        sums = rate * modis_8day_coverage_days(year)            # what summing composites gives
        monthly = composite_sums_to_monthly(sums[:, None, None] * np.ones((12, 2, 2)), year)
        np.testing.assert_allclose(monthly[:, 0, 0], rate * days_in_months(year))
