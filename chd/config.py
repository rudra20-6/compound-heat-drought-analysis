"""
Central configuration: grid, periods, dataset IDs, thresholds and paths.

Every threshold lives here so that a sensitivity run only changes values in
this file, never the analysis code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (data folders can be redirected with environment variables)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = Path(os.environ.get("CHD_RAW_DIR", ROOT / "data" / "raw"))
DATA_PROCESSED = Path(os.environ.get("CHD_PROCESSED_DIR", ROOT / "data" / "processed"))
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"

for _p in (DATA_RAW, DATA_PROCESSED, RESULTS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

CUBE_PATH = DATA_PROCESSED / "cube.nc"

# ---------------------------------------------------------------------------
# Earth Engine
# ---------------------------------------------------------------------------
# Set with:  export EE_PROJECT="your-gcp-project-id"
EE_PROJECT = os.environ.get("EE_PROJECT", "")

# ---------------------------------------------------------------------------
# Grid (EPSG:4326, India domain)
# ---------------------------------------------------------------------------
GRID_RES_DEG = 0.25
LON_MIN, LON_MAX = 68.0, 98.0       # degrees East
LAT_MIN, LAT_MAX = 6.0, 37.5        # degrees North
N_LON = round((LON_MAX - LON_MIN) / GRID_RES_DEG)   # 120
N_LAT = round((LAT_MAX - LAT_MIN) / GRID_RES_DEG)   # 126

# Affine transform (GDAL convention): [x0, dx, 0, y0, 0, -dy]
# Cell centres: lon = LON_MIN + (i+0.5)*dx ; lat = LAT_MAX - (j+0.5)*dy
AFFINE = (LON_MIN, GRID_RES_DEG, 0.0, LAT_MAX, 0.0, -GRID_RES_DEG)

# Reference latitude drawn on the study-area map (Peninsular India lies south of it)
PENINSULAR_LAT_MAX = 22.0

# ---------------------------------------------------------------------------
# Study periods
# ---------------------------------------------------------------------------
CLIMATOLOGY_START, CLIMATOLOGY_END = 1991, 2020   # baseline for z-scores / SPI fit
FETCH_START, FETCH_END = 1991, 2024               # ERA5-Land / CHIRPS / SPEI fetch window
GPP_START, GPP_END = 2001, 2022                   # MODIS GPP period (primary response)
NDVI_START, NDVI_END = 2001, 2024                 # MODIS NDVI period

# Analysis period, bounded by GPP availability (the limiting dataset)
STUDY_START, STUDY_END = GPP_START, GPP_END

# ---------------------------------------------------------------------------
# GEE asset IDs (verified against the GEE Data Catalog, Oct 2026)
# ---------------------------------------------------------------------------
ERA5_LAND_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
CHIRPS_PENTAD = "UCSB-CHG/CHIRPS/PENTAD"
SPEI_ASSET = "CSIC/SPEI/2_11"
MODIS_GPP_PRIMARY = "MODIS/006/MOD17A2H"            # deprecated but covers 2001-2022
MODIS_GPP_FALLBACK = "projects/pml_evapotranspiration/PML/OUTPUT/PML_V22a"
MODIS_NDVI = "MODIS/061/MOD13A3"
WORLDCOVER = "ESA/WorldCover/v200"
INDIA_BOUNDARY = "USDOS/LSIB_SIMPLE/2017"

# Marker stored in data/raw/gpp_*.npz: monthly GPP = mean daily rate of the
# 8-day composites starting in the month x days in month (not a plain sum,
# which is biased in leap years -- see indices.modis_8day_coverage_days).
GPP_MONTHLY_METHOD = "daily_rate_x_days_in_month"


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Thresholds:
    hot_z: float = 1.0                   # Tmax z-score >= this -> "hot"
    dry_spei: float = -1.0               # SPEI-3 (or SPI-3) <= this -> "dry"
    active_season_gpp_frac: float = 0.3  # cell-month active if clim. GPP >= this frac of peak
    active_season_veg_frac: float = 0.5  # and vegetated land-cover fraction >= this
    landcover_purity: float = 0.5        # dominant-class purity threshold (study-area map)


THRESH = Thresholds()

# Vegetated ESA WorldCover classes (10=tree, 20=shrub, 30=grass, 40=crop, 90=wetland, 95=mangrove)
VEGETATED_CLASSES = (10, 20, 30, 40, 90, 95)
WORLDCOVER_CLASS_NAMES = {
    10: "tree_cover",
    20: "shrubland",
    30: "grassland",
    40: "cropland",
    50: "built_up",
    60: "bare_sparse",
    70: "snow_ice",
    80: "water",
    90: "wetland",
    95: "mangrove",
    100: "moss_lichen",
}

# Bootstrap settings
BOOTSTRAP_N = 1000
BOOTSTRAP_SEED = 42

# Minimum number of cell-months for a response-surface bin to be shown
MIN_BIN_N = 30
