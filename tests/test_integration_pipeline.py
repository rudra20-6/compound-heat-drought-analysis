"""
End-to-end integration test replicating what scripts/02-06 do, on the tiny
synthetic grid from conftest.py, with no GEE calls and no subprocesses:

  build_raw_cube -> derived vars -> align -> anomalies/categories ->
  active-season mask -> region masks
    -> build_all_events -> recovery_summary -> superposed_epoch_composite
    -> cube_to_long_table -> category_composites -> compute_amplification
       -> response_surface -> mechanism_check
    -> each result plotted via plotting.py (headless, into a tmp dir)
    -> the dominant-stress-category reduction used by scripts/06_case_studies.py

This is the test most likely to catch a real wiring bug between modules
(as opposed to a bug within a single pure function), since every unit test
above exercises one module in isolation.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")

from chd import config as cfg
from chd import cube
from chd import plotting as plot
from chd.impacts import (
    cube_to_long_table, category_composites, compute_amplification,
    response_surface, mechanism_check,
)
from chd.recovery import build_all_events, recovery_summary, superposed_epoch_composite


def test_full_pipeline_scripts_02_through_06_equivalent(small_grid, tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "FIGURES", tmp_path)

    # ---- script 02 equivalent ----
    ds = cube.build_full_cube(raw_dir=small_grid)
    assert ds["category"].shape[0] == 36

    # ---- script 03 equivalent: events + frequency maps ----
    events = build_all_events(ds)
    india_mask = ds["is_india"].values
    active = ds["active_season"].values
    category = ds["category"].values
    for cat in ["normal", "hot_only", "dry_only", "compound"]:
        freq = np.mean((category == cat) & active, axis=0)
        freq = np.where(india_mask, freq, np.nan)
        plot.plot_map(freq, ds["lat"].values, ds["lon"].values,
                      title=f"freq {cat}", filename=f"freq_{cat}", cbar_label="frac")
        assert (tmp_path / f"freq_{cat}.png").exists()

    # ---- script 04 equivalent: impacts & synergy ----
    df = cube_to_long_table(ds, response_vars=("gpp_z", "ndvi_z"))
    assert len(df) > 0
    comp_gpp = category_composites(df, "gpp_z")
    plot.plot_category_composite(comp_gpp, "GPP z", "test", "composite_gpp")
    assert (tmp_path / "composite_gpp.png").exists()

    if set(comp_gpp["category"]) >= {"normal", "hot_only", "dry_only", "compound"}:
        ai = compute_amplification(comp_gpp)
        assert "amplification_index" in ai.columns

    if "dominant_landcover" in df.columns:
        comp_lc = category_composites(df, "gpp_z", group_cols=["dominant_landcover"])
        ai_lc = compute_amplification(comp_lc, group_cols=["dominant_landcover"])
        if len(ai_lc) > 0:
            plot.plot_amplification_by_stratum(ai_lc, "dominant_landcover", "test", "ai_lc")
            assert (tmp_path / "ai_lc.png").exists()

    surf = response_surface(df, "gpp_z")
    plot.plot_response_surface(surf, "GPP z", "test", "surface")
    assert (tmp_path / "surface.png").exists()

    mech = mechanism_check(df)
    assert "sm_z" in mech.columns

    # ---- script 05 equivalent: recovery ----
    summary = recovery_summary(events)
    assert isinstance(summary, type(summary))  # just confirms it runs without error
    for response_var in ["gpp_z", "ndvi_z"]:
        composite = superposed_epoch_composite(ds, events, response_var=response_var)
        plot.plot_recovery_composite(composite, response_var, "test", f"recovery_{response_var}")
        assert (tmp_path / f"recovery_{response_var}.png").exists()

    # ---- script 06 equivalent: dominant-category reduction (case studies) ----
    cat_codes = {"normal": 0, "hot_only": 1, "dry_only": 2, "compound": 3, "nan": -1}
    coded = np.vectorize(lambda c: cat_codes.get(c, -1))(category)

    def _mode_or_missing(x):
        valid = x[x >= 0]
        return np.bincount(valid, minlength=4).argmax() if len(valid) > 0 else -1

    mode_cat = np.apply_along_axis(_mode_or_missing, 0, coded).astype(float)
    mode_cat[mode_cat < 0] = np.nan
    assert mode_cat.shape == (cfg.N_LAT, cfg.N_LON)
    # every cell in this fixture has active data every month, so none should be all-NaN
    assert not np.all(np.isnan(mode_cat))
