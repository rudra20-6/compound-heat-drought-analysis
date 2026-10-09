"""
Index computation: standardized anomalies, SPI (gamma-fit), VPD.

All functions operate on 1-D numpy arrays (a single grid cell's time series)
or are vectorized over an ``xarray.DataArray`` with dims (time, lat, lon).
Keeping the per-cell math in plain numpy functions makes them trivial to
unit-test on synthetic series (see tests/test_indices.py) before wiring them
into the full cube.
"""
from __future__ import annotations

import numpy as np
import xarray as xr
from scipy import stats as sstats


# ---------------------------------------------------------------------------
# Generic monthly standardized anomaly (z-score), optionally detrended
# ---------------------------------------------------------------------------
def monthly_zscore_1d(values: np.ndarray, months: np.ndarray,
                       detrend: bool = False,
                       baseline_mask: np.ndarray | None = None) -> np.ndarray:
    """
    Standardize a single-cell time series into monthly z-scores.

    For each calendar month (1..12) independently:
      1. (optional) remove a linear trend fit over the baseline years
      2. subtract the baseline mean and divide by the baseline std

    Parameters
    ----------
    values : (n,) array, may contain NaN
    months : (n,) int array, calendar month 1..12 for each entry
    detrend : if True, remove a linear trend in time (per calendar month)
              before standardizing -- used for GPP/NDVI/soil-moisture to
              strip out greening/irrigation trends so that "anomaly" means
              deviation from the expected trajectory, not from a flat mean.
    baseline_mask : (n,) bool array selecting which indices define the
                    baseline mean/std/trend (e.g. 1991-2020). If None, all
                    indices are used.

    Returns
    -------
    z : (n,) array of z-scores, NaN where input was NaN.
    """
    values = np.asarray(values, dtype=float)
    months = np.asarray(months)
    n = len(values)
    z = np.full(n, np.nan)

    if baseline_mask is None:
        baseline_mask = np.ones(n, dtype=bool)

    for m in range(1, 13):
        sel = months == m
        if not np.any(sel):
            continue
        base_sel = sel & baseline_mask
        y = values[sel]
        valid_base = base_sel & ~np.isnan(values)
        n_base = np.sum(valid_base)
        if n_base < 3:
            continue

        if detrend:
            t_base = np.flatnonzero(valid_base).astype(float)
            y_base = values[valid_base]
            slope, intercept, *_ = sstats.linregress(t_base, y_base)
            t_all = np.flatnonzero(sel).astype(float)
            trend_pred = intercept + slope * t_all
            resid = y - trend_pred
            base_resid = resid[np.isin(np.flatnonzero(sel), np.flatnonzero(valid_base))]
        else:
            resid = y
            base_resid = values[valid_base]

        mu = np.nanmean(base_resid)
        sd = np.nanstd(base_resid, ddof=1)
        if sd == 0 or np.isnan(sd):
            continue
        z[sel] = (resid - mu) / sd

    return z


def monthly_zscore_array(arr: np.ndarray, months: np.ndarray, detrend: bool = False,
                          baseline_mask: np.ndarray | None = None,
                          min_baseline: int = 3) -> np.ndarray:
    """
    Vectorised equivalent of monthly_zscore_1d over a (time, ...) array: same
    maths (per-calendar-month OLS detrend fitted on the baseline, then
    standardise by the baseline residual mean/std, ddof=1), computed for all
    grid cells at once instead of one Python call per cell.
    """
    arr = np.asarray(arr, dtype=float)
    months = np.asarray(months)
    n = arr.shape[0]
    if baseline_mask is None:
        baseline_mask = np.ones(n, dtype=bool)
    out = np.full(arr.shape, np.nan)
    t_all = np.arange(n, dtype=float)
    extra = (1,) * (arr.ndim - 1)

    for m in range(1, 13):
        sel = np.flatnonzero(months == m)
        if len(sel) == 0:
            continue
        y = arr[sel]
        t = t_all[sel].reshape((-1,) + extra)
        base = (baseline_mask[sel].reshape((-1,) + extra)) & ~np.isnan(y)
        nb = base.sum(axis=0)
        yb = np.where(base, y, 0.0)

        if detrend:
            tb = np.where(base, t, 0.0)
            st, sy = tb.sum(0), yb.sum(0)
            stt, sty = (tb * tb).sum(0), (tb * yb).sum(0)
            with np.errstate(invalid="ignore", divide="ignore"):
                slope = (nb * sty - st * sy) / (nb * stt - st ** 2)
                intercept = (sy - slope * st) / nb
            resid = y - (intercept + slope * t)
        else:
            resid = y

        rb = np.where(base, resid, 0.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mu = rb.sum(0) / nb
            var = (np.where(base, (resid - mu) ** 2, 0.0)).sum(0) / (nb - 1)
            sd = np.sqrt(var)
            z = (resid - mu) / sd
        bad = (nb < min_baseline) | ~(sd > 0)
        z = np.where(bad, np.nan, z)
        out[sel] = z
    return out


def monthly_zscore(da: xr.DataArray, time_dim: str = "time",
                    detrend: bool = False,
                    baseline_years: tuple[int, int] | None = None) -> xr.DataArray:
    """Vectorized wrapper of monthly_zscore_1d over an (time, lat, lon) DataArray."""
    months = da[time_dim].dt.month.values
    years = da[time_dim].dt.year.values
    baseline_mask = None
    if baseline_years is not None:
        baseline_mask = (years >= baseline_years[0]) & (years <= baseline_years[1])

    def _apply(values_1d):
        return monthly_zscore_1d(values_1d, months, detrend=detrend,
                                  baseline_mask=baseline_mask)

    return xr.apply_ufunc(
        _apply, da,
        input_core_dims=[[time_dim]],
        output_core_dims=[[time_dim]],
        vectorize=True,
        dask="parallelized" if da.chunks else False,
        output_dtypes=[float],
    ).transpose(*da.dims)


# ---------------------------------------------------------------------------
# SPI: Standardized Precipitation Index via gamma-distribution fit
# ---------------------------------------------------------------------------
def spi_1d(precip: np.ndarray, months: np.ndarray, window: int = 3,
           baseline_mask: np.ndarray | None = None) -> np.ndarray:
    """
    Compute SPI-<window> for a single cell's monthly precipitation series.

    Standard McKee et al. (1993) method with a zero-inflated gamma fit:
    accumulate `window`-month rolling precipitation totals, then for each
    calendar month fit a gamma distribution (on the baseline period) to the
    positive totals, mix in the fraction of zero totals, and transform the
    fitted CDF to a standard-normal z-score via the inverse normal CDF.

    Parameters
    ----------
    precip : (n,) monthly precipitation totals (mm), may contain NaN
    months : (n,) calendar month per entry
    window : accumulation window in months (3, 1, 6, ...)
    baseline_mask : which indices to use for fitting gamma params
                    (e.g. 1991-2020); defaults to all indices.

    Returns
    -------
    spi : (n,) array, NaN where insufficient data.
    """
    precip = np.asarray(precip, dtype=float)
    n = len(precip)
    months = np.asarray(months)

    # Rolling sum (trailing window, requires `window` consecutive valid months)
    accum = np.full(n, np.nan)
    for i in range(n):
        if i + 1 < window:
            continue
        chunk = precip[i - window + 1: i + 1]
        if np.any(np.isnan(chunk)):
            continue
        accum[i] = np.sum(chunk)

    if baseline_mask is None:
        baseline_mask = np.ones(n, dtype=bool)

    spi = np.full(n, np.nan)
    for m in range(1, 13):
        sel = months == m
        if not np.any(sel):
            continue
        base_sel = sel & baseline_mask & ~np.isnan(accum)
        base_vals = accum[base_sel]
        if len(base_vals) < 10:
            continue

        q = np.mean(base_vals == 0)  # probability of zero accumulation
        positives = base_vals[base_vals > 0]
        if len(positives) < 5 or np.std(positives) == 0:
            continue  # degenerate (e.g. near-constant precip in an arid cell): skip
        # Fit gamma via MLE (shape, loc fixed at 0, scale)
        try:
            shape, loc, scale = sstats.gamma.fit(positives, floc=0)
        except (ValueError, RuntimeError):
            continue  # fit failed to converge (degenerate/near-degenerate sample)

        y = accum[sel]
        valid = ~np.isnan(y)
        cdf = np.full(y.shape, np.nan)
        cdf[valid & (y == 0)] = q
        pos_mask = valid & (y > 0)
        cdf[pos_mask] = q + (1 - q) * sstats.gamma.cdf(y[pos_mask], shape, loc=loc, scale=scale)
        # guard against cdf exactly 0 or 1 -> ppf(+/-inf)
        cdf = np.clip(cdf, 1e-6, 1 - 1e-6)
        spi[sel] = sstats.norm.ppf(cdf)

    return spi


# ---------------------------------------------------------------------------
# Vapour Pressure Deficit (VPD) from air temperature and dewpoint (Tetens)
# ---------------------------------------------------------------------------
def modis_8day_coverage_days(year: int) -> np.ndarray:
    """
    Days covered, per calendar month, by the MODIS 8-day composites whose
    start date falls in that month. Composites start on day-of-year 1, 9, 17,
    ..., 361; each covers 8 days except the last of the year (DOY 361), which
    covers the 5 (6 in leap years) remaining days.

    In leap years the schedule shifts one calendar day: DOY 121 is 30 April
    (not 1 May) and DOY 305 is 31 October (not 1 November), so April and
    October get 4 composites instead of 3 and May and November get 3 instead
    of 4. Summing composites per month therefore inflates leap-year Apr/Oct
    GPP by ~1/3 and deflates May/Nov by ~1/4.
    """
    import calendar
    import datetime as dt
    n_days = 366 if calendar.isleap(year) else 365
    covered = np.zeros(12)
    for doy in range(1, n_days + 1, 8):
        month = (dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)).month
        covered[month - 1] += min(8, n_days - doy + 1)
    return covered


def days_in_months(year: int) -> np.ndarray:
    import calendar
    return np.array([calendar.monthrange(year, m)[1] for m in range(1, 13)], dtype=float)


def composite_sums_to_monthly(sums: np.ndarray, year: int) -> np.ndarray:
    """
    Convert per-month sums of MODIS 8-day composite totals (shape (12, ...))
    into calendar-month totals: mean daily rate over the days the composites
    cover, times the number of days in the month. Removes the leap-year
    composite-count artefact described in modis_8day_coverage_days.
    """
    sums = np.asarray(sums, dtype=float)
    scale = days_in_months(year) / modis_8day_coverage_days(year)
    return sums * scale.reshape((12,) + (1,) * (sums.ndim - 1))


def saturation_vapor_pressure_kpa(temp_c: np.ndarray) -> np.ndarray:
    """Tetens formula, kPa, for temperature in degrees C."""
    temp_c = np.asarray(temp_c, dtype=float)
    return 0.6108 * np.exp(17.27 * temp_c / (temp_c + 237.3))


def vpd_kpa(temp_c: np.ndarray, dewpoint_c: np.ndarray) -> np.ndarray:
    """VPD (kPa) = es(T) - es(Td). Negative values (shouldn't occur) are clipped to 0."""
    es = saturation_vapor_pressure_kpa(temp_c)
    ea = saturation_vapor_pressure_kpa(dewpoint_c)
    return np.clip(es - ea, 0, None)


# ---------------------------------------------------------------------------
# Root-zone soil moisture: depth-weighted combination of ERA5-Land layers
# ---------------------------------------------------------------------------
def root_zone_soil_moisture(swvl1: np.ndarray, swvl2: np.ndarray, swvl3: np.ndarray,
                             depths_cm: tuple[float, float, float] = (7, 21, 72)) -> np.ndarray:
    """
    Depth-weighted mean volumetric soil water content over layers 1-3
    (0-7, 7-28, 28-100 cm), approximating 0-100 cm root-zone moisture.
    """
    total_depth = sum(depths_cm)
    w = np.array(depths_cm) / total_depth
    return w[0] * swvl1 + w[1] * swvl2 + w[2] * swvl3
