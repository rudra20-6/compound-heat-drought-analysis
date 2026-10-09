"""Smoke tests: every slide figure renders and is written to FIGURES."""
import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

from chd import config as cfg
from chd import cube
from chd import plotting as plot
from chd.impacts import cube_to_long_table, category_composites, category_contrasts, response_surface


def test_all_slide_figures_render(small_grid, tmp_path, monkeypatch):
    out = tmp_path / "figs"
    out.mkdir()
    monkeypatch.setattr(cfg, "FIGURES", out)
    ds = cube.build_full_cube(raw_dir=small_grid)
    plot.plot_study_area(ds)

    rng = np.random.default_rng(0)
    plot.plot_compound_frequency(rng.uniform(0, 0.2, (4, 5)), ds["lat"].values, ds["lon"].values)

    rows = []
    for year in range(2001, 2011):
        for cat, e in {"normal": 0, "hot_only": -0.2, "dry_only": -0.3, "compound": -0.5}.items():
            for _ in range(10):
                rows.append({"year": year, "category": cat, "gpp_z": e + rng.normal(0, 0.3),
                             "ndvi_z": e + rng.normal(0, 0.3),
                             "tmax_z": rng.normal(0, 1.5), "spei03": rng.normal(0, 1.5)})
    df = pd.DataFrame(rows)
    plot.plot_category_composite(category_composites(df, "gpp_z"), "GPP z", "t", "composite_gpp_z_overall")
    plot.plot_additivity({v: category_contrasts(df, v) for v in ("gpp_z", "ndvi_z")})
    plot.plot_response_surface(response_surface(df, "gpp_z", min_n=5))

    for name in ("study_area_landcover", "freq_map_compound", "composite_gpp_z_overall",
                 "additivity_gpp_ndvi", "response_surface_gpp_explained"):
        assert (out / f"{name}.png").exists(), name
