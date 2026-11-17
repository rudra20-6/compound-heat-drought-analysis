"""
Central configuration for the Compound Heat-Drought (CHD) pipeline.

Every tunable threshold, period, and path lives here so that sensitivity
runs (see plan section 3.G) only ever require changing values in this
file, never the analysis code itself.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Study region (select with the CHD_REGION env var; default "india")
# ---------------------------------------------------------------------------
# Every region uses the same datasets, periods, thresholds and 0.25-deg grid
# spacing; only the bounding box, the LSIB country name and the output folders
# differ. India keeps its original folders (data/raw, results, ...) so the
# mid-sub cache and results are untouched; other regions get their own
# subfolders (data/<region>/raw, results/<region>, figures/<region>).
REGIONS = {
    "india": dict(
        lon_min=68.0, lon_max=98.0, lat_min=6.0, lat_max=37.5,
        country_na="India", subdir=None,
    ),
    # Mainland + Tasmania + Torres Strait islands (Cape York -10.7, Torres
    # Strait to ~-9.2, SE Cape Tasmania -43.6; Steep Point 113.2E, Cape Byron
    # 153.6E). External territories (Christmas I., Heard I., Macquarie I. ...)
    # fall outside the box and are excluded on purpose.
    "australia": dict(
        lon_min=112.0, lon_max=154.0, lat_min=-44.0, lat_max=-9.0,
        country_na="Australia", subdir="australia",
    ),
}
REGION = os.environ.get("CHD_REGION", "india").strip().lower()
if REGION not in REGIONS:
    raise ValueError(f"CHD_REGION={REGION!r} is not one of {sorted(REGIONS)}")
_R = REGIONS[REGION]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent  # midSub/
if _R["subdir"] is None:
    DATA_RAW = ROOT / "data" / "raw"
    DATA_PROCESSED = ROOT / "data" / "processed"
    RESULTS = ROOT / "results"
    FIGURES = ROOT / "figures"
else:
    DATA_RAW = ROOT / "data" / _R["subdir"] / "raw"
    DATA_PROCESSED = ROOT / "data" / _R["subdir"] / "processed"
    RESULTS = ROOT / "results" / _R["subdir"]
    FIGURES = ROOT / "figures" / _R["subdir"]

# Country-fraction mask cache: data/raw/<region>_mask_0.npz, array key <region>
# (for India this is the original india_mask_0.npz / key "india").
COUNTRY_NAME = _R["country_na"]
COUNTRY_MASK_NAME = f"{REGION}_mask"
COUNTRY_MASK_KEY = REGION

for _p in (DATA_RAW, DATA_PROCESSED, RESULTS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

CUBE_PATH = DATA_PROCESSED / "cube.nc"
ANOMALIES_PATH = DATA_PROCESSED / "anomalies.nc"
EVENTS_PATH = DATA_PROCESSED / "events.csv"

# ---------------------------------------------------------------------------
# Earth Engine
# ---------------------------------------------------------------------------
# Set with:  export EE_PROJECT="your-gcp-project-id"
EE_PROJECT = os.environ.get("EE_PROJECT", "")

# ---------------------------------------------------------------------------
# Grid (EPSG:4326, domain of the selected REGION)
# ---------------------------------------------------------------------------
GRID_RES_DEG = 0.25
LON_MIN, LON_MAX = _R["lon_min"], _R["lon_max"]   # degrees East
LAT_MIN, LAT_MAX = _R["lat_min"], _R["lat_max"]   # degrees North (negative = South)
N_LON = round((LON_MAX - LON_MIN) / GRID_RES_DEG)   # India 120, Australia 168
N_LAT = round((LAT_MAX - LAT_MIN) / GRID_RES_DEG)   # India 126, Australia 140

# Affine transform (GDAL convention): [x0, dx, 0, y0, 0, -dy]
# Cell centers: lon = LON_MIN + (i+0.5)*dx ; lat = LAT_MAX - (j+0.5)*dy
AFFINE = (LON_MIN, GRID_RES_DEG, 0.0, LAT_MAX, 0.0, -GRID_RES_DEG)

# Peninsular India cutoff (cells at/ south of this latitude are "Peninsular")
PENINSULAR_LAT_MAX = 22.0

# ---------------------------------------------------------------------------
# Region-specific analysis settings (H4 sub-regions, seasons, QC, case study)
# ---------------------------------------------------------------------------
# H4 sub-region split by latitude. Cells with lat <= lat_cut get `south`, the
# rest `north`; `exclude` (lon_min, lat_max) drops a corner box from the split
# (India: the Andaman & Nicobar islands, which are not "Peninsular India").
# region_difference_test reports region_a minus region_b.
_SUBREGIONS = {
    "india": dict(lat_cut=22.0, south="peninsular", north="north",
                  exclude=(92.0, 14.5), excluded_name="islands",
                  region_a="peninsular", region_b="north",
                  label="Peninsular (≤22°N) vs North"),
    # Tropic of Capricorn: monsoonal/savanna north vs temperate/arid south.
    "australia": dict(lat_cut=-23.44, south="temperate_south", north="tropical_north",
                      exclude=None, excluded_name=None,
                      region_a="tropical_north", region_b="temperate_south",
                      label="Tropical north vs temperate south (Tropic of Capricorn)"),
}
SUBREGION = _SUBREGIONS[REGION]
SUBREGION_LAT_CUT = SUBREGION["lat_cut"]


def subregion_of(lat, lon):
    """Vectorised H4 sub-region label for cell centres (numpy arrays or scalars)."""
    import numpy as _np
    lat = _np.asarray(lat, dtype=float)
    lon = _np.asarray(lon, dtype=float)
    out = _np.where(lat <= SUBREGION["lat_cut"], SUBREGION["south"], SUBREGION["north"]).astype(object)
    if SUBREGION["exclude"] is not None:
        lon_min, lat_max = SUBREGION["exclude"]
        out[(lon >= lon_min) & (lat <= lat_max)] = SUBREGION["excluded_name"]
    return out


# Meteorological seasons used to stratify results (southern-hemisphere seasons for Australia).
_SEASONS = {
    "india": {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJAS": (6, 7, 8, 9), "ON": (10, 11)},
    "australia": {"DJF (summer)": (12, 1, 2), "MAM (autumn)": (3, 4, 5),
                  "JJA (winter)": (6, 7, 8), "SON (spring)": (9, 10, 11)},
}
REGION_SEASONS = _SEASONS[REGION]

# QC: do the inputs reproduce well-known events? (02_build_cube.py)
#   drought: country-mean SPEI-3 at `drought_month` (India: Sep = end of monsoon), or the
#            calendar-year mean when drought_month is None (Australia, no single wet season)
#   heat:    country-mean Tmax z over `heat_months`
_QC = {
    "india": dict(drought_years=[2002, 2009, 2014, 2015], heat_years=[2010, 2022],
                  drought_month=9, drought_label="monsoon SPEI-3 (Sep)",
                  heat_months=(3, 4, 5), heat_label="pre-monsoon Tmax z (Mar-May)"),
    # BoM annual climate statements: 2019 warmest and driest year on record;
    # 2002 and 2006 Millennium-Drought El Nino years; 2013 the previous warmest year.
    "australia": dict(drought_years=[2002, 2006, 2019], heat_years=[2013, 2019],
                      drought_month=None, drought_label="annual-mean SPEI-3",
                      heat_months=tuple(range(1, 13)), heat_label="annual-mean Tmax z"),
}
REGION_QC = _QC[REGION]

# Case study (06_case_studies.py): a famous compound event in each country.
_CASES = {
    "india": dict(name="2009", start="2009-06", end="2009-09", label="Jun-Sep 2009 monsoon drought"),
    "australia": dict(name="2019", start="2019-09", end="2019-12",
                      label="Sep-Dec 2019 (pre-Black Summer) heat-drought"),
}
REGION_CASE = _CASES[REGION]

# ---------------------------------------------------------------------------
# Study periods
# ---------------------------------------------------------------------------
CLIMATOLOGY_START, CLIMATOLOGY_END = 1991, 2020   # baseline for z-scores / SPI fit
FETCH_START, FETCH_END = 1991, 2024               # ERA5-Land / CHIRPS / SPEI fetch window
GPP_START, GPP_END = 2001, 2022                   # MODIS GPP study period (primary response)
NDVI_START, NDVI_END = 2001, 2024                 # MODIS NDVI study period
EVENT_TREND_START, EVENT_TREND_END = 1991, 2024   # H5 frequency-trend window

# The "primary analysis" period used for impact/synergy/recovery stats
# (bounded by GPP availability, the limiting dataset).
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
INDIA_BOUNDARY = "USDOS/LSIB_SIMPLE/2017"   # country boundaries for every region
COUNTRY_BOUNDARY = INDIA_BOUNDARY

# Marker stored in data/raw/gpp_*.npz: monthly GPP = mean daily rate of the
# 8-day composites starting in the month x days in month (not a plain sum,
# which is biased in leap years -- see indices.modis_8day_coverage_days).
GPP_MONTHLY_METHOD = "daily_rate_x_days_in_month"

# ---------------------------------------------------------------------------
# Thresholds (stress-category and event definitions)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Thresholds:
    hot_z: float = 1.0           # Tmax z-score >= this -> "hot"
    dry_spei: float = -1.0       # SPEI-3 <= this -> "dry"
    recovered_z: float = -0.5    # GPP z >= this (2 consecutive months) -> "recovered"
    min_event_months: int = 2    # minimum run length to count as a drought event
    impact_z: float = -1.0       # event must reach this GPP z to count as "with impact"
    censor_months: int = 24      # recovery-time censoring horizon
    compound_event_frac: float = 0.0  # min fraction of drought-event months that must be hot
                                       # (0.0 = "any month hot"; sensitivity run uses 0.5)
    active_season_gpp_frac: float = 0.3  # cell-month active if clim. GPP >= this frac of peak
    active_season_veg_frac: float = 0.5  # and vegetated land-cover fraction >= this
    landcover_purity: float = 0.5        # dominant-class purity threshold


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

# Bootstrap settings. 10,000 replicates (final phase; mid-sub used 1,000) so that
# bootstrap p-values resolve down to ~0.0002; CIs change only in the 3rd decimal.
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 42

# Minimum sample size per stratum before it's flagged / merged
MIN_STRATUM_N = 30

SEASONS = {
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJAS": (6, 7, 8, 9),
    "ON": (10, 11),
}
