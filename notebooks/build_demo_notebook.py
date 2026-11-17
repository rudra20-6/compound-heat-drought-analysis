"""
Generates notebooks/demo.ipynb programmatically (via nbformat) so the JSON
is always well-formed. Run this script to (re)build the notebook; don't
hand-edit the .ipynb directly -- edit this script instead.

Usage:
    python notebooks/build_demo_notebook.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

cells.append(nbf.v4.new_markdown_cell(
"""# Compound Heat-Drought Stress over India -- Mid-Eval Demo

Loads only cached outputs from `data/processed/` and `results/` -- no
network calls, so this runs in well under a minute and can't fail on a
flaky connection during the live demo.

Run `scripts/00`-`06` first to populate those caches from real data."""
))

cells.append(nbf.v4.new_code_cell(
"""import sys
from pathlib import Path

# Find the midSub folder (the one containing chd/) no matter where Jupyter was started
_here = Path.cwd().resolve()
_candidates = [_here, *_here.parents] + [p / "midSub" for p in [_here, *_here.parents]]
PROJECT_ROOT = next((p for p in _candidates if (p / "chd" / "config.py").exists()), None)
if PROJECT_ROOT is None:
    raise RuntimeError(f"Can't find the midSub folder (with chd/) from {_here}. "
                       "Open the notebook from inside the midSub folder.")
sys.path.insert(0, str(PROJECT_ROOT))
print("Project folder:", PROJECT_ROOT)
print("Python running this notebook:", sys.executable)

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, Image
from matplotlib.colors import ListedColormap

from chd import config as cfg
from chd.plotting import CATEGORY_COLORS, CATEGORY_ORDER

CUBE_AVAILABLE = cfg.CUBE_PATH.exists()
EVENTS_AVAILABLE = cfg.EVENTS_PATH.exists()
print(f"cube.nc available: {CUBE_AVAILABLE}")
print(f"events.csv available: {EVENTS_AVAILABLE}")

if CUBE_AVAILABLE:
    ds = xr.open_dataset(cfg.CUBE_PATH)
    print(ds)
else:
    ds = None
    print("Run scripts/00-02 first to generate the cube. "
          "The rest of this notebook will show placeholders until then.")"""
))

cells.append(nbf.v4.new_markdown_cell("## 1. Month picker: map of Tz / SPEI / category / GPP z"))

cells.append(nbf.v4.new_code_cell(
"""def plot_month(year, month):
    if ds is None:
        print("No cube loaded.")
        return
    sel = ds.sel(time=f"{year}-{month:02d}-01", method="nearest")
    india_mask = ds["is_india"].values if "is_india" in ds else None

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    extent = [float(ds.lon.min()), float(ds.lon.max()), float(ds.lat.min()), float(ds.lat.max())]
    fields = [
        ("tmax_z", "Reds", -2, 3, "Tmax z"),
        ("spei03", "BrBG", -2.5, 2.5, "SPEI-3"),
        ("gpp_z", "RdYlGn", -3, 3, "GPP z"),
    ]
    for ax, (var, cmap, vmin, vmax, label) in zip(axes[:3], fields):
        field = sel[var].values
        if india_mask is not None:
            field = np.where(india_mask, field, np.nan)
        im = ax.imshow(field, cmap=cmap, vmin=vmin, vmax=vmax, origin="upper", extent=extent)
        ax.set_title(label)
        fig.colorbar(im, ax=ax, shrink=0.7)

    cat_codes = {"normal": 0, "hot_only": 1, "dry_only": 2, "compound": 3, "nan": -1}
    coded = np.vectorize(lambda c: cat_codes.get(c, -1))(sel["category"].values).astype(float)
    coded[coded < 0] = np.nan
    if india_mask is not None:
        coded = np.where(india_mask, coded, np.nan)
    # exactly four colours, same as the slides (blue/orange/red/green)
    cmap4 = ListedColormap([CATEGORY_COLORS[c] for c in CATEGORY_ORDER])
    im = axes[3].imshow(coded, cmap=cmap4, vmin=-0.5, vmax=3.5, origin="upper", extent=extent)
    axes[3].set_title("Category")
    cbar = fig.colorbar(im, ax=axes[3], ticks=[0, 1, 2, 3], shrink=0.7)
    cbar.ax.set_yticklabels(["normal", "hot", "dry", "compound"])

    fig.suptitle(f"{year}-{month:02d}")
    fig.tight_layout()
    plt.show()


if ds is not None:
    years = sorted(set(pd.DatetimeIndex(ds["time"].values).year))
    widgets.interact(plot_month,
                      year=widgets.IntSlider(min=min(years), max=max(years), value=2009),
                      month=widgets.IntSlider(min=1, max=12, value=7))
else:
    print("(interactive map picker disabled -- no cube loaded)")"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 2. Cell picker: time series at three preset locations

- Western Ghats (evergreen forest): ~10.5N, 76.5E
- Central India (deciduous forest): ~21.5N, 80.5E
- Punjab (irrigated cropland): ~30.5N, 75.5E"""
))

cells.append(nbf.v4.new_code_cell(
"""PRESETS = {
    "Western Ghats (evergreen)": (10.5, 76.5),
    "Central India (deciduous)": (21.5, 80.5),
    "Punjab (irrigated cropland)": (30.5, 75.5),
}

def plot_cell_series(site_name):
    if ds is None:
        print("No cube loaded.")
        return
    lat, lon = PRESETS[site_name]
    cell = ds.sel(lat=lat, lon=lon, method="nearest")
    dates = pd.DatetimeIndex(cell["time"].values)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(dates, cell["gpp_z"].values, label="GPP z", color="#2a7")
    ax.axhline(0, color="gray", linewidth=0.6)

    cats = cell["category"].values
    for cat, color in [("hot_only", "#DD8452"), ("dry_only", "#C44E52"), ("compound", "#55A868")]:
        mask = cats == cat
        ax.fill_between(dates, -3, 3, where=mask, color=color, alpha=0.15, step="mid", label=cat)

    ax.set_ylim(-3, 3)
    ax.set_title(f"{site_name} (lat={float(cell.lat):.2f}, lon={float(cell.lon):.2f})")
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    fig.tight_layout()
    plt.show()


if ds is not None:
    widgets.interact(plot_cell_series, site_name=list(PRESETS.keys()))
else:
    print("(interactive cell picker disabled -- no cube loaded)")"""
))

cells.append(nbf.v4.new_markdown_cell("## 3. Headline results table"))

cells.append(nbf.v4.new_code_cell(
"""for name in ["composite_gpp_z_overall.csv", "composite_ndvi_z_overall.csv",
             "contrasts_gpp_z_overall.csv", "contrasts_ndvi_z_overall.csv",
             "robustness_spei_vs_spi.csv", "peninsular_vs_north_test.csv",
             "recovery_km.csv", "recovery_severity_matched.csv",
             "compound_area_trend_stats.csv"]:
    path = cfg.RESULTS / name
    print(f"--- {name} ---")
    if path.exists():
        display(pd.read_csv(path))
    else:
        print("  (not yet generated -- run the corresponding script)")
    print()"""
))

cells.append(nbf.v4.new_markdown_cell("## 4. Response surface (Tmax-z x SPEI-3)"))

cells.append(nbf.v4.new_code_cell(
"""for stem in ["response_surface_gpp", "response_surface_ndvi"]:
    fig_path = cfg.FIGURES / f"{stem}.png"
    if fig_path.exists():
        display(Image(filename=str(fig_path), width=520))
    else:
        print(f"({stem}.png not yet generated -- run scripts/04_impacts.py)")"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 5. Optional: one live Earth Engine call

Disabled by default (`RUN_LIVE_EE_CHECK = False`). Flip it on only if you
want to demo a live GEE round-trip during the presentation -- it needs
`EE_PROJECT` set and network access."""
))

cells.append(nbf.v4.new_code_cell(
"""RUN_LIVE_EE_CHECK = False

if RUN_LIVE_EE_CHECK:
    from chd.gee import init_ee
    ee = init_ee()
    img = ee.ImageCollection(cfg.MODIS_NDVI).filterDate("2020-07-01", "2020-08-01").first()
    print(img.getInfo()["bands"])
else:
    print("Live EE check skipped (RUN_LIVE_EE_CHECK = False).")"""
))

nb["cells"] = cells
# Run with the project venv (registered via:
#   python -m ipykernel install --user --name est-midsub --display-name "Python (est-midsub)")
nb.metadata["kernelspec"] = {"name": "est-midsub", "display_name": "Python (est-midsub)", "language": "python"}
nb.metadata["language_info"] = {"name": "python"}

with open("demo.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Wrote demo.ipynb")
