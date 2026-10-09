"""
Google Earth Engine (GEE) data-access layer.

All server-side aggregation (monthly compositing, reprojection to the
0.25-degree analysis grid) happens here, keeping the rest of the pipeline
(indices.py, categories.py, cube.py) completely GEE-free and testable offline.

Nothing in this module is imported by the unit tests -- it requires a live,
authenticated Earth Engine session (``earthengine authenticate`` +
``EE_PROJECT`` env var). See scripts/00_check_gee.py to verify access, and
scripts/01_fetch.py for the resumable per-year fetch loop.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import config as cfg
from .indices import composite_sums_to_monthly

# ee is imported lazily (inside functions) so that importing chd.gee does not
# require earthengine-api / credentials unless you actually call something.


def init_ee():
    import ee
    if not cfg.EE_PROJECT:
        raise RuntimeError(
            "EE_PROJECT environment variable is not set. "
            "Run: export EE_PROJECT=your-gcp-project-id"
        )
    ee.Initialize(project=cfg.EE_PROJECT)
    return ee


# ---------------------------------------------------------------------------
# Grid geometry helpers
# ---------------------------------------------------------------------------
def analysis_grid_crs_transform():
    """CRS transform list for ee.Image.getPixels / computePixels, matching config.AFFINE."""
    x0, dx, _, y0, _, dy = cfg.AFFINE
    return [dx, 0, x0, 0, dy, y0]


def grid_pixel_grid(ee):
    """ee.PixelGrid-style spec dict for computePixels requests."""
    return {
        "dimensions": {"width": cfg.N_LON, "height": cfg.N_LAT},
        "affineTransform": {
            "scaleX": cfg.GRID_RES_DEG, "shearX": 0, "translateX": cfg.LON_MIN,
            "shearY": 0, "scaleY": -cfg.GRID_RES_DEG, "translateY": cfg.LAT_MAX,
        },
        "crsCode": "EPSG:4326",
    }


def india_geometry(ee):
    """Union geometry of India from LSIB_SIMPLE (boundaries are illustrative, not authoritative)."""
    fc = ee.FeatureCollection(cfg.INDIA_BOUNDARY).filter(ee.Filter.eq("country_na", "India"))
    return fc.geometry()


# ---------------------------------------------------------------------------
# Server-side aggregation to the analysis grid
# ---------------------------------------------------------------------------
def reduce_to_grid(ee, image, reducer=None):
    """
    Reproject + reduceResolution an Image's native-resolution pixels onto
    the 0.25-deg analysis grid. Caller must have already set the desired
    band(s) on `image`. Must call .reproject(...) with the *source*
    projection before reduceResolution (GEE requirement), so this function
    expects `image` to already carry a meaningful default projection
    (true for raw EE collection images; composites need setDefaultProjection
    explicitly -- see fetch_* functions below).

    Uses bestEffort=True (GEE resamples via its own internal pyramids rather
    than enumerating every native pixel) instead of a hard maxPixels cap.
    This matters a lot at fine native resolutions: a fixed maxPixels (e.g.
    4096) fails outright for 10 m WorldCover ("Too many input pixels per
    output pixel. Need 9000000, but only 4096 allowed" -- a 0.25-deg output
    cell needs ~9M 10m input pixels) and made MODIS GPP (500 m) need an
    elaborate geographic-tiling workaround that turned out to be unnecessary.
    bestEffort=True fetches whole-India GPP/WorldCover in ~2s with no
    tiling at all (confirmed empirically, Oct 2026) -- at a small, acceptable
    cost in exactness (GEE's pyramid levels approximate the true
    full-resolution mean rather than computing it exactly).
    """
    reducer = reducer or ee.Reducer.mean()
    return (
        image
        .reduceResolution(reducer=reducer, bestEffort=True)
        .reproject(crs="EPSG:4326", crsTransform=analysis_grid_crs_transform())
    )


def compute_pixels_numpy(ee, image, band_names):
    """
    Fetch an Image's bands as a numpy array via ee.data.computePixels.

    IMPORTANT: computePixels does not preserve Earth Engine's pixel mask --
    a pixel with zero valid contributing source pixels (e.g. ocean cells in
    a land-only dataset like ERA5-Land, or cells outside a collection's
    coverage) comes back as the band's raw unmasked value (observed to be 0)
    rather than NaN. Confirmed by direct comparison against an explicit mask
    band on ERA5-Land ERA5_LAND/DAILY_AGGR (Oct 2026): cells where
    image.mask() == 0 matched cells where the fetched value == 0 exactly.
    Since real data can legitimately be 0 (zero precipitation, SPEI of 0,
    etc.), we fetch an explicit validity band alongside the data and use it
    to set masked pixels to NaN, rather than checking value == 0.
    """
    selected = image.select(band_names)
    valid_mask = selected.mask().reduce(ee.Reducer.min()).rename("valid_mask_band")
    request_image = selected.addBands(valid_mask)
    request = {
        "expression": request_image,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": grid_pixel_grid(ee),
    }
    arr = ee.data.computePixels(request)
    valid = arr["valid_mask_band"] > 0.5  # mask after reduceResolution can be fractional at edges
    # structured array -> plain (band, lat, lon) float array
    out = np.stack([arr[b].astype(float) for b in band_names], axis=0)
    out[:, ~valid] = np.nan
    return out  # shape (n_bands, N_LAT, N_LON)


# ---------------------------------------------------------------------------
# Per-dataset fetch functions
# ---------------------------------------------------------------------------
def fetch_era5_land_month(ee, year: int, month: int) -> dict[str, np.ndarray]:
    """
    Monthly mean-of-daily-max Tmax, monthly precip sum (sanity cross-check),
    monthly mean soil-moisture layers 1-3, monthly mean T2m & dewpoint (VPD).
    Returns dict of variable_name -> (N_LAT, N_LON) array.
    """
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    ic = ee.ImageCollection(cfg.ERA5_LAND_DAILY).filterDate(start, end)

    tmax_monthly_mean = ic.select("temperature_2m_max").mean()
    t2m_mean = ic.select("temperature_2m").mean()
    dewpoint_mean = ic.select("dewpoint_temperature_2m").mean()
    swvl1 = ic.select("volumetric_soil_water_layer_1").mean()
    swvl2 = ic.select("volumetric_soil_water_layer_2").mean()
    swvl3 = ic.select("volumetric_soil_water_layer_3").mean()

    composite = (
        ee.Image.cat([tmax_monthly_mean, t2m_mean, dewpoint_mean, swvl1, swvl2, swvl3])
        .rename(["tmax", "t2m", "dewpoint", "swvl1", "swvl2", "swvl3"])
        .setDefaultProjection(crs="EPSG:4326", scale=11132)
    )
    gridded = reduce_to_grid(ee, composite)
    arr = compute_pixels_numpy(ee, gridded, ["tmax", "t2m", "dewpoint", "swvl1", "swvl2", "swvl3"])
    return {
        "tmax_k": arr[0], "t2m_k": arr[1], "dewpoint_k": arr[2],
        "swvl1": arr[3], "swvl2": arr[4], "swvl3": arr[5],
    }


def fetch_chirps_month(ee, year: int, month: int) -> np.ndarray:
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    ic = ee.ImageCollection(cfg.CHIRPS_PENTAD).filterDate(start, end)
    composite = ic.select("precipitation").sum().rename("precip") \
        .setDefaultProjection(crs="EPSG:4326", scale=5566)
    gridded = reduce_to_grid(ee, composite)
    arr = compute_pixels_numpy(ee, gridded, ["precip"])
    return arr[0]


def fetch_spei_month(ee, year: int, month: int, timescale: int = 3) -> np.ndarray:
    band = f"SPEI_{timescale:02d}_month"
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")
    ic = ee.ImageCollection(cfg.SPEI_ASSET).filterDate(start, end).select(band)
    image = ic.first().setDefaultProjection(crs="EPSG:4326", scale=55660)
    gridded = reduce_to_grid(ee, image)
    arr = compute_pixels_numpy(ee, gridded, [band])
    return arr[0]


def fetch_modis_gpp_year(ee, year: int, source: str = "auto") -> np.ndarray:
    """
    Returns monthly total GPP in gC/m^2 for all 12 months of `year`, shape
    (12, N_LAT, N_LON). `source` is "mod17" or "pml" (see
    scripts/00_check_gee.py, which decides this once up front and writes the
    choice to data/processed/gpp_source.txt).

    All 12 months are requested as bands in a single reduce_to_grid /
    computePixels call (bestEffort=True handles the whole-India 500 m native
    resolution directly, confirmed at ~2s/month-equivalent, Oct 2026).
    """
    band_names = [f"m{m:02d}" for m in range(1, 13)]

    if source in ("mod17", "auto"):
        ic_all = ee.ImageCollection(cfg.MODIS_GPP_PRIMARY).select("Gpp")
        native_proj = ic_all.first().projection()
        bands = []
        for m in range(1, 13):
            start = ee.Date.fromYMD(year, m, 1)
            end = start.advance(1, "month")
            monthly = ic_all.filterDate(start, end).sum().multiply(0.0001).multiply(1000) \
                .rename(f"m{m:02d}")  # kgC/m2/8day-sum -> gC/m2/month
            bands.append(monthly)
        stacked = ee.Image.cat(bands).setDefaultProjection(native_proj)
    else:
        # PML fallback: GPP band is gC/m2/day at 0.01 scale, 8-day composite mean
        ic_all = ee.ImageCollection(cfg.MODIS_GPP_FALLBACK).select("GPP")
        native_proj = ic_all.first().projection()
        bands = []
        for m in range(1, 13):
            start = ee.Date.fromYMD(year, m, 1)
            end = start.advance(1, "month")
            days_in_month = end.difference(start, "day")
            monthly = ic_all.filterDate(start, end).mean().multiply(0.01) \
                .multiply(ee.Image.constant(days_in_month)).rename(f"m{m:02d}")
            bands.append(monthly)
        stacked = ee.Image.cat(bands).setDefaultProjection(native_proj)

    gridded = reduce_to_grid(ee, stacked)
    arr = compute_pixels_numpy(ee, gridded, band_names)
    if source in ("mod17", "auto"):
        # sums of 8-day composites -> calendar-month totals (fixes the
        # leap-year composite-count artefact; see indices.modis_8day_coverage_days)
        arr = composite_sums_to_monthly(arr, year)
    return arr


def fetch_modis_ndvi_year(ee, year: int) -> dict[str, np.ndarray]:
    """Returns {'ndvi': (12,N_LAT,N_LON), 'qa': (12,N_LAT,N_LON)} for all 12 months of `year`."""
    ic_all = ee.ImageCollection(cfg.MODIS_NDVI)

    ndvi_bands, qa_bands = [], []
    for m in range(1, 13):
        start = ee.Date.fromYMD(year, m, 1)
        end = start.advance(1, "month")
        img = ic_all.filterDate(start, end).first()
        ndvi_bands.append(img.select("NDVI").multiply(0.0001).rename(f"m{m:02d}"))
        qa_bands.append(img.select("SummaryQA").rename(f"q{m:02d}"))

    composite = ee.Image.cat(ndvi_bands + qa_bands).setDefaultProjection(crs="SR-ORG:6974", scale=1000)
    gridded = reduce_to_grid(ee, composite)

    ndvi_names = [f"m{m:02d}" for m in range(1, 13)]
    qa_names = [f"q{m:02d}" for m in range(1, 13)]
    arr = compute_pixels_numpy(ee, gridded, ndvi_names + qa_names)
    return {"ndvi": arr[:12], "qa": arr[12:]}


def fetch_worldcover_fractions(ee) -> dict[str, np.ndarray]:
    """Static (2021) land-cover class fractions per 0.25-deg cell. One-time fetch."""
    img = ee.ImageCollection(cfg.WORLDCOVER).first().select("Map")
    native_proj = img.projection()

    class_names = list(cfg.WORLDCOVER_CLASS_NAMES.values())
    masks = [img.eq(code).rename(name).toFloat() for code, name in cfg.WORLDCOVER_CLASS_NAMES.items()]
    stacked = ee.Image.cat(masks).setDefaultProjection(native_proj)

    gridded = reduce_to_grid(ee, stacked)
    arr = compute_pixels_numpy(ee, gridded, class_names)
    return {name: arr[i] for i, name in enumerate(class_names)}


def fetch_india_mask(ee) -> np.ndarray:
    """Fraction of each 0.25-deg cell covered by India (LSIB_SIMPLE union geometry)."""
    geom = india_geometry(ee)
    # unmask(0, sameFootprint=False) is required: the default sameFootprint=True
    # only fills masked *holes inside* the clipped extent and leaves pixels
    # outside the clip geometry still masked -- confirmed by direct testing
    # (Oct 2026), which made fetch_india_mask return 1.0 (and no NaN) over the
    # *entire* bounding box, Pakistan/ocean included, rather than 0 outside India.
    mask_img = ee.Image.constant(1).clip(geom).unmask(0, False).rename("india") \
        .setDefaultProjection(crs="EPSG:4326", scale=1000)
    gridded = reduce_to_grid(ee, mask_img)
    arr = compute_pixels_numpy(ee, gridded, ["india"])
    return arr[0]


def with_retry(fn, *args, retries=3, backoff=5, **kwargs):
    """Simple retry wrapper for transient EE server errors (rate limits, timeouts)."""
    last_exc = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - EE raises many exception types
            last_exc = exc
            time.sleep(backoff * (attempt + 1))
    raise last_exc
