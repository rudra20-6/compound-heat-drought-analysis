"""
Verify Earth Engine authentication + that every required asset loads, and
decide which MODIS GPP source to use (MOD17 v006 vs PML_V22a fallback).

Usage:
    export EE_PROJECT=your-gcp-project-id
    python scripts/00_check_gee.py

Writes the chosen GPP source to data/processed/gpp_source.txt, which
scripts/01_fetch.py reads.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd.gee import init_ee


def check_asset(ee, asset_id, is_image=False, filter_band=None):
    try:
        if is_image:
            obj = ee.Image(asset_id)
            info = obj.getInfo()
            print(f"  OK  {asset_id}  (Image, bands={[b['id'] for b in info['bands']]})")
        else:
            ic = ee.ImageCollection(asset_id)
            if filter_band:
                ic = ic.select(filter_band)
            size = ic.size().getInfo()
            first_date = ee.Date(ic.sort("system:time_start").first().get("system:time_start")) \
                .format("YYYY-MM-dd").getInfo()
            last_date = ee.Date(ic.sort("system:time_start", False).first().get("system:time_start")) \
                .format("YYYY-MM-dd").getInfo()
            print(f"  OK  {asset_id}  (n={size}, {first_date} .. {last_date})")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {asset_id}: {exc}")
        return False


def check_feature_collection(ee, asset_id, filter_prop=None, filter_value=None):
    """LSIB_SIMPLE/2017 (and similar boundary datasets) are FeatureCollections,
    not ImageCollections -- checked separately from check_asset()."""
    try:
        fc = ee.FeatureCollection(asset_id)
        if filter_prop is not None:
            fc = fc.filter(ee.Filter.eq(filter_prop, filter_value))
        n = fc.size().getInfo()
        print(f"  OK  {asset_id}  (FeatureCollection, {n} matching feature(s))")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {asset_id}: {exc}")
        return False


def main():
    print(f"EE_PROJECT = {cfg.EE_PROJECT!r}")
    ee = init_ee()
    print("Earth Engine initialized OK.\n")

    print("Checking core assets:")
    check_asset(ee, cfg.ERA5_LAND_DAILY)
    check_asset(ee, cfg.CHIRPS_PENTAD)
    check_asset(ee, cfg.SPEI_ASSET)
    check_asset(ee, cfg.MODIS_NDVI)
    check_asset(ee, cfg.WORLDCOVER)
    check_feature_collection(ee, cfg.INDIA_BOUNDARY, filter_prop="country_na", filter_value="India")

    print("\nDeciding MODIS GPP source (MOD17 v006 primary, PML_V22a fallback):")
    gpp_source = "pml"
    try:
        ic = ee.ImageCollection(cfg.MODIS_GPP_PRIMARY).filterDate("2015-01-01", "2015-02-01")
        n = ic.size().getInfo()
        if n > 0:
            print(f"  MOD17 v006 ({cfg.MODIS_GPP_PRIMARY}) loads fine ({n} images in Jan 2015).")
            gpp_source = "mod17"
        else:
            print("  MOD17 v006 returned 0 images -- falling back to PML_V22a.")
    except Exception as exc:  # noqa: BLE001
        print(f"  MOD17 v006 failed to load ({exc}) -- falling back to PML_V22a.")

    if gpp_source == "pml":
        check_asset(ee, cfg.MODIS_GPP_FALLBACK)

    out_path = cfg.DATA_PROCESSED / "gpp_source.txt"
    out_path.write_text(gpp_source)
    print(f"\nGPP source decision: '{gpp_source}' (written to {out_path})")
    print("\nAll checks complete.")


if __name__ == "__main__":
    main()
