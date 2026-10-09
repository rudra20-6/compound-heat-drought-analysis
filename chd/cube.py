"""
Assemble the cached per-variable .npz arrays (data/raw/) into one tidy
xarray.Dataset (the "cube"), then derive anomalies, indices, and stress
categories on top of it.

This module is the seam between the GEE fetch layer (gee.py, network-bound,
untestable offline) and the pure-numpy analysis layer (indices.py,
categories.py, unit-tested). `build_raw_cube` only does reshaping/stacking
(no GEE calls), so it can be exercised in tests with small hand-built .npz
fixtures.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from . import config as cfg
from .indices import monthly_zscore_array, spi_1d, vpd_kpa, root_zone_soil_moisture
from .categories import classify_months


def _lat_lon_coords():
    x0, dx, _, y0, _, dy = cfg.AFFINE
    lons = x0 + (np.arange(cfg.N_LON) + 0.5) * dx
    lats = y0 + (np.arange(cfg.N_LAT) + 0.5) * dy  # dy is negative -> descending lats
    return lats, lons


def _month_index(start_year: int, end_year: int) -> pd.DatetimeIndex:
    return pd.date_range(f"{start_year}-01-01", f"{end_year}-12-01", freq="MS")


def _stack_years(prefix: str, key: str, start_year: int, end_year: int,
                  raw_dir: Path = cfg.DATA_RAW) -> np.ndarray:
    """Load data_raw/{prefix}_{year}.npz[key] for each year and stack along time."""
    chunks = []
    for year in range(start_year, end_year + 1):
        path = raw_dir / f"{prefix}_{year}.npz"
        with np.load(path) as f:
            chunks.append(f[key])
    return np.concatenate(chunks, axis=0)  # (n_years*12, N_LAT, N_LON)


def _check_gpp_cache(start_year: int, end_year: int, raw_dir: Path) -> None:
    """Refuse GPP caches written before the leap-year fix (plain sums of
    8-day composites per month). See indices.modis_8day_coverage_days."""
    for year in range(start_year, end_year + 1):
        with np.load(raw_dir / f"gpp_{year}.npz") as f:
            method = str(f["monthly_method"]) if "monthly_method" in f else None
        if method != cfg.GPP_MONTHLY_METHOD:
            raise ValueError(
                f"data/raw/gpp_{year}.npz holds uncorrected 8-day composite sums "
                f"(monthly_method={method!r}). Re-fetch it with scripts/01_fetch.py "
                "--only gpp after deleting it.")


def build_raw_cube(raw_dir: Path = cfg.DATA_RAW) -> xr.Dataset:
    """
    Load all cached variables and assemble into a single xr.Dataset on the
    common analysis grid, each on its own native time axis (ERA5/CHIRPS/SPEI:
    FETCH_START-FETCH_END; GPP: GPP_START-GPP_END; NDVI: NDVI_START-NDVI_END).
    Static layers (worldcover fractions, india mask) are added without a time dim.
    """
    lats, lons = _lat_lon_coords()

    era5_time = _month_index(cfg.FETCH_START, cfg.FETCH_END)
    tmax_k = _stack_years("era5", "tmax_k", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    t2m_k = _stack_years("era5", "t2m_k", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    dewpoint_k = _stack_years("era5", "dewpoint_k", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    swvl1 = _stack_years("era5", "swvl1", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    swvl2 = _stack_years("era5", "swvl2", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    swvl3 = _stack_years("era5", "swvl3", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    precip = _stack_years("chirps", "precip", cfg.FETCH_START, cfg.FETCH_END, raw_dir)
    spei03 = _stack_years("spei", "spei_03", cfg.FETCH_START, cfg.FETCH_END, raw_dir)

    gpp_time = _month_index(cfg.GPP_START, cfg.GPP_END)
    _check_gpp_cache(cfg.GPP_START, cfg.GPP_END, raw_dir)
    gpp = _stack_years("gpp", "gpp", cfg.GPP_START, cfg.GPP_END, raw_dir)

    ndvi_time = _month_index(cfg.NDVI_START, cfg.NDVI_END)
    ndvi = _stack_years("ndvi", "ndvi", cfg.NDVI_START, cfg.NDVI_END, raw_dir)
    ndvi_qa = _stack_years("ndvi", "qa", cfg.NDVI_START, cfg.NDVI_END, raw_dir)

    ds = xr.Dataset(
        data_vars=dict(
            tmax_c=(("era5_time", "lat", "lon"), tmax_k - 273.15),
            t2m_c=(("era5_time", "lat", "lon"), t2m_k - 273.15),
            dewpoint_c=(("era5_time", "lat", "lon"), dewpoint_k - 273.15),
            swvl1=(("era5_time", "lat", "lon"), swvl1),
            swvl2=(("era5_time", "lat", "lon"), swvl2),
            swvl3=(("era5_time", "lat", "lon"), swvl3),
            precip_mm=(("era5_time", "lat", "lon"), precip),
            spei03=(("era5_time", "lat", "lon"), spei03),
            gpp_gC_m2=(("gpp_time", "lat", "lon"), gpp),
            ndvi=(("ndvi_time", "lat", "lon"), ndvi),
            ndvi_qa=(("ndvi_time", "lat", "lon"), ndvi_qa),
        ),
        coords=dict(
            era5_time=era5_time, gpp_time=gpp_time, ndvi_time=ndvi_time,
            lat=lats, lon=lons,
        ),
    )

    wc_path = raw_dir / "worldcover_0.npz"
    if wc_path.exists():
        with np.load(wc_path) as f:
            for name in cfg.WORLDCOVER_CLASS_NAMES.values():
                if name in f:
                    ds[f"frac_{name}"] = (("lat", "lon"), f[name])

    mask_path = raw_dir / "india_mask_0.npz"
    if mask_path.exists():
        with np.load(mask_path) as f:
            ds["india_frac"] = (("lat", "lon"), f["india"])

    return ds


def add_derived_variables(ds: xr.Dataset) -> xr.Dataset:
    """VPD, root-zone soil moisture -- pure arithmetic, no resampling needed."""
    ds["vpd_kpa"] = xr.apply_ufunc(vpd_kpa, ds["t2m_c"], ds["dewpoint_c"])
    ds["root_zone_sm"] = xr.apply_ufunc(
        root_zone_soil_moisture, ds["swvl1"], ds["swvl2"], ds["swvl3"]
    )
    return ds


def add_india_mask(ds: xr.Dataset) -> xr.Dataset:
    """Static mask: is_india (cell >= 50% inside India)."""
    if "india_frac" in ds:
        ds["is_india"] = ds["india_frac"] >= 0.5
    else:
        ds["is_india"] = xr.DataArray(np.ones((ds.sizes["lat"], ds.sizes["lon"]), dtype=bool),
                                      dims=("lat", "lon"), coords={"lat": ds.lat, "lon": ds.lon})
    return ds


def _zscore_da(da: xr.DataArray, tdim: str, detrend: bool, baseline) -> xr.DataArray:
    """Vectorised monthly z-score of a (tdim, lat, lon) DataArray."""
    months = da[tdim].dt.month.values
    years = da[tdim].dt.year.values
    base = None if baseline is None else (years >= baseline[0]) & (years <= baseline[1])
    z = monthly_zscore_array(da.transpose(tdim, "lat", "lon").values, months,
                             detrend=detrend, baseline_mask=base)
    return xr.DataArray(z, dims=(tdim, "lat", "lon"), coords={tdim: da[tdim], "lat": da.lat, "lon": da.lon})


def _classify_da(tmax_z: xr.DataArray, dry_index: xr.DataArray, tdim: str) -> xr.DataArray:
    t = tmax_z.transpose(tdim, "lat", "lon").values
    d = dry_index.transpose(tdim, "lat", "lon").values
    flat = classify_months(t.ravel(), d.ravel()).reshape(t.shape)  # classify_months is elementwise
    return xr.DataArray(flat, dims=(tdim, "lat", "lon"),
                        coords={tdim: tmax_z[tdim], "lat": tmax_z.lat, "lon": tmax_z.lon})


def compute_climate_anomalies(ds: xr.Dataset,
                              baseline=(cfg.CLIMATOLOGY_START, cfg.CLIMATOLOGY_END)) -> xr.Dataset:
    """
    Climate-side anomalies on the FULL ERA5/CHIRPS/SPEI record (era5_time,
    1991-2024), *before* cutting to the GPP study period -- so the stated
    1991-2020 baseline is actually the baseline used:

      tmax_z  : Tmax z vs 1991-2020 calendar-month climatology (not detrended:
                warming counts as heat)
      sm_z    : root-zone soil moisture z (detrended, 1991-2020 baseline)
      vpd_z   : VPD z (1991-2020 baseline)
      spi03   : SPI-3 from CHIRPS, gamma fitted on 1991-2020 (India cells only)
      category      : 2x2 stress category using SPEI-3 (primary)
      category_spi  : same, using SPI-3 (temperature-free robustness check)
    """
    ds = ds.copy()
    tdim = "era5_time"
    ds["tmax_z"] = _zscore_da(ds["tmax_c"], tdim, detrend=False, baseline=baseline)
    ds["sm_z"] = _zscore_da(ds["root_zone_sm"], tdim, detrend=True, baseline=baseline)
    ds["vpd_z"] = _zscore_da(ds["vpd_kpa"], tdim, detrend=False, baseline=baseline)

    months = ds[tdim].dt.month.values
    years = ds[tdim].dt.year.values
    base = (years >= baseline[0]) & (years <= baseline[1])
    precip = ds["precip_mm"].transpose(tdim, "lat", "lon").values
    india = ds["is_india"].values
    spi = np.full(precip.shape, np.nan)
    for i, j in zip(*np.nonzero(india)):  # gamma fits only where they are used
        if not np.all(np.isnan(precip[:, i, j])):
            spi[:, i, j] = spi_1d(precip[:, i, j], months, window=3, baseline_mask=base)
    ds["spi03"] = xr.DataArray(spi, dims=(tdim, "lat", "lon"),
                               coords={tdim: ds[tdim], "lat": ds.lat, "lon": ds.lon})

    ds["category"] = _classify_da(ds["tmax_z"], ds["spei03"], tdim)
    ds["category_spi"] = _classify_da(ds["tmax_z"], ds["spi03"], tdim)
    return ds


CLIMATE_VARS = ("tmax_c", "t2m_c", "dewpoint_c", "swvl1", "swvl2", "swvl3", "precip_mm",
                "spei03", "vpd_kpa", "root_zone_sm", "tmax_z", "sm_z", "vpd_z", "spi03",
                "category", "category_spi")


def align_to_common_time(ds: xr.Dataset, start_year: int, end_year: int) -> xr.Dataset:
    """
    Reindex the time-varying variables (on era5_time / gpp_time / ndvi_time)
    onto one shared monthly 'time' axis for the primary analysis period
    (bounded by GPP availability).
    """
    common_time = _month_index(start_year, end_year)
    out = xr.Dataset(coords=dict(time=common_time, lat=ds.lat, lon=ds.lon))

    pairs = [(v, "era5_time") for v in CLIMATE_VARS] + [
        ("gpp_gC_m2", "gpp_time"), ("ndvi", "ndvi_time"), ("ndvi_qa", "ndvi_time")]
    for var, tdim in pairs:
        if var not in ds:
            continue
        out[var] = ds[var].rename({tdim: "time"}).reindex(time=common_time)

    for var in ds.data_vars:
        if ds[var].dims == ("lat", "lon"):
            out[var] = ds[var]
    return out


def compute_vegetation_anomalies(ds: xr.Dataset) -> xr.Dataset:
    """
    GPP and NDVI z-scores over the study period (detrended, so CO2/irrigation
    greening is not counted as an anomaly). NDVI is first masked where the
    cell's mean MOD13A3 SummaryQA > 1, i.e. where most underlying 1 km pixels
    were snow/ice or cloudy (QA 2/3) rather than good/marginal (QA 0/1).
    """
    ds = ds.copy()
    ds["gpp_z"] = _zscore_da(ds["gpp_gC_m2"], "time", detrend=True, baseline=None)
    ndvi_clean = ds["ndvi"].where(ds["ndvi_qa"] <= 1.0)
    ds["ndvi_clean"] = ndvi_clean
    ds["ndvi_z"] = _zscore_da(ndvi_clean, "time", detrend=True, baseline=None)
    return ds


def add_active_season_mask(ds: xr.Dataset) -> xr.Dataset:
    """
    A cell-month is 'active' if (a) the cell is inside India, (b) its vegetated
    land-cover fraction >= active_season_veg_frac, and (c) climatological GPP
    for that calendar month is >= active_season_gpp_frac of the cell's peak
    month. Stored per study-period month as `active_season` (time x lat x lon).
    """
    clim = ds["gpp_gC_m2"].groupby("time.month").mean("time")  # (month, lat, lon)
    peak = clim.max("month")
    frac_of_peak = clim / peak.where(peak > 0)

    veg_classes = [f"frac_{cfg.WORLDCOVER_CLASS_NAMES[c]}" for c in cfg.VEGETATED_CLASSES
                   if f"frac_{cfg.WORLDCOVER_CLASS_NAMES[c]}" in ds]
    if veg_classes:
        veg_frac = sum(ds[v] for v in veg_classes)
    else:
        veg_frac = xr.ones_like(ds["is_india"], dtype=float)

    static_ok = (veg_frac >= cfg.THRESH.active_season_veg_frac) & ds["is_india"]
    active_by_month = (frac_of_peak >= cfg.THRESH.active_season_gpp_frac) & static_ok
    per_time = active_by_month.sel(month=ds["time"].dt.month).drop_vars("month", errors="ignore")
    ds["active_season"] = per_time.transpose("time", "lat", "lon")
    return ds


def build_full_cube(raw_dir: Path | None = None, return_climate: bool = False):
    """End-to-end: raw -> derived -> masks -> climate anomalies (full record)
    -> align to study period -> vegetation anomalies -> active-season mask.

    With return_climate=True also returns the full-record (1991-2024)
    climate dataset (era5_time axis), used for the data QC checks.
    """
    ds = build_raw_cube(raw_dir or cfg.DATA_RAW)
    ds = add_derived_variables(ds)
    ds = add_india_mask(ds)
    climate = compute_climate_anomalies(ds)
    out = align_to_common_time(climate, cfg.STUDY_START, cfg.STUDY_END)
    out = compute_vegetation_anomalies(out)
    out = add_active_season_mask(out)
    return (out, climate) if return_climate else out
