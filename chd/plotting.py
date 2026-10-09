"""
The six figures used in the mid-evaluation slides. Each function saves a PNG
(300 dpi, or 200 for the response surface) to config.FIGURES and returns the
matplotlib Figure, so the notebook can also display it inline.

  study_area_landcover.png           Why India? (land cover map)
  freq_map_compound.png              Where compound months happen
  composite_gpp_z_overall.png        H1 (GPP)
  composite_ndvi_z_overall.png       H1 (NDVI)
  additivity_gpp_ndvi.png            H2 (observed vs additive)
  response_surface_gpp_explained.png H2 (response surface)
"""
from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from . import config as cfg
from .categories import CATEGORIES

CATEGORY_COLORS = {
    "normal": "#4C72B0", "hot_only": "#DD8452",
    "dry_only": "#C44E52", "compound": "#55A868",
}
# Colour encodes category identity, not severity: compound is compared
# directly against hot-only / dry-only, so it is not given an "alarm" red.


def _savefig(fig, name: str, dpi: int = 300):
    path = cfg.FIGURES / f"{name}.png"
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path


# ---------------------------------------------------------------- study area
def plot_study_area(ds, filename: str = "study_area_landcover"):
    """Dominant WorldCover class per India cell (purity >= threshold), with a
    reference line at 22N (Peninsular India lies south of it)."""
    frac_cols = [c for c in ds.data_vars if c.startswith("frac_")]
    fracs = np.nan_to_num(np.stack([ds[c].values for c in frac_cols], axis=0))
    names = [c.replace("frac_", "") for c in frac_cols]
    dom = np.argmax(fracs, axis=0).astype(float)
    dom[np.max(fracs, axis=0) < cfg.THRESH.landcover_purity] = np.nan
    india = ds["is_india"].values
    dom[~india] = np.nan
    # India cells with no class >= purity threshold are shown as "mixed" (white)
    mixed = len(names)
    dom[india & np.isnan(dom)] = mixed

    colours = {"tree_cover": "#1f77b4", "shrubland": "#ff7f0e", "grassland": "#2ca02c",
               "cropland": "#d62728", "built_up": "#9467bd", "bare_sparse": "#8c564b",
               "snow_ice": "#e377c2", "water": "#7f7f7f", "wetland": "#bcbd22",
               "mangrove": "#17becf", "moss_lichen": "#e7ba52"}
    cmap = mcolors.ListedColormap([colours.get(n, "#000000") for n in names] + ["#ffffff"])

    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=100)
    lat, lon = ds["lat"].values, ds["lon"].values
    half = 0.5 * abs(float(lat[1] - lat[0]))  # extent uses cell edges, not centres
    ax.imshow(dom, extent=[lon.min() - half, lon.max() + half, lat.min() - half, lat.max() + half],
              origin="upper", cmap=cmap, vmin=-0.5, vmax=mixed + 0.5, interpolation="nearest")
    ax.axhline(cfg.PENINSULAR_LAT_MAX, color="black", linestyle="--", linewidth=1.5)

    # legend: only classes that actually occur, with cell counts
    handles = []
    for k, n in enumerate(names + ["mixed (no class >=50%)"]):
        cnt = int(np.sum(dom == k))
        if cnt:
            handles.append(Patch(facecolor=cmap(k), edgecolor="0.6" if k == mixed else cmap(k),
                                 linewidth=0.5, label=f"{n.replace('_', ' ')} ({cnt})"))
    handles.append(plt.Line2D([], [], color="black", linestyle="--",
                              label=f"Peninsular cutoff ({cfg.PENINSULAR_LAT_MAX:.0f}N)"))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("Dominant land cover per 0.25° cell (ESA WorldCover 2021)", fontsize=9)
    ax.text(0.01, 0.01, "Boundary: USDOS LSIB 2017, not authoritative",
            transform=ax.transAxes, fontsize=6, color="0.3")
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


# ------------------------------------------------------ compound frequency
def plot_compound_frequency(freq, lat, lon, filename: str = "freq_map_compound"):
    """Share of each cell's active months that are compound."""
    fig, ax = plt.subplots(figsize=(5, 5.5), dpi=100)
    extent = [lon.min(), lon.max(), lat.min(), lat.max()]
    im = ax.imshow(freq, extent=extent, origin="upper", cmap="YlOrRd", aspect="equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(f"Share of active months that are 'compound'\n({cfg.STUDY_START}-{cfg.STUDY_END})",
                 fontsize=9)
    fig.colorbar(im, ax=ax, label="fraction of active-season months", shrink=0.8)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


# ---------------------------------------------------------------------- H1
def plot_category_composite(composite_df: pd.DataFrame, response_label: str,
                            title: str, filename: str):
    """Bar chart of mean response by category with bootstrap 95% CI whiskers."""
    df = composite_df.set_index("category").reindex(list(CATEGORIES))
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    x = np.arange(len(CATEGORIES))
    heights = df["mean"].values
    yerr = np.vstack([heights - df["ci_low"].values, df["ci_high"].values - heights])
    ax.bar(x, heights, yerr=yerr, capsize=4, color=[CATEGORY_COLORS[c] for c in CATEGORIES])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "-") for c in CATEGORIES])
    ax.set_ylabel(response_label)
    ax.set_title(title)
    for xi, n in zip(x, df["n"]):
        ax.annotate(f"n={int(n)}", (xi, 0), xytext=(0, -14),
                    textcoords="offset points", ha="center", fontsize=8)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


# ---------------------------------------------------------------------- H2
def plot_additivity(contrasts: dict, filename: str = "additivity_gpp_ndvi"):
    """Heat-only effect, drought-only effect, their sum (expected if additive)
    and the observed compound effect, for GPP and NDVI (z units, 95% CI).
    `contrasts` maps "gpp_z"/"ndvi_z" to the one-row output of category_contrasts."""
    hot, dry, cmp_, grey = (CATEGORY_COLORS["hot_only"], CATEGORY_COLORS["dry_only"],
                            CATEGORY_COLORS["compound"], "#8a8a8a")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True, dpi=100)
    for ax, (v, title) in zip(axes, [("gpp_z", "GPP (productivity)"), ("ndvi_z", "NDVI (greenness)")]):
        d = contrasts[v].iloc[0]
        vals = [d.d_hot, d.d_dry, d.d_hot + d.d_dry, d.d_compound]
        lo = [d.d_hot_ci_low, d.d_dry_ci_low, np.nan, d.d_compound_ci_low]
        hi = [d.d_hot_ci_high, d.d_dry_ci_high, np.nan, d.d_compound_ci_high]
        x = np.arange(4)
        bars = ax.bar(x, vals, color=[hot, dry, "white", cmp_],
                      edgecolor=["none", "none", grey, "none"], linewidth=1.5, width=0.62)
        bars[2].set_hatch("///")
        for i in (0, 1, 3):
            ax.errorbar(x[i], vals[i], yerr=[[vals[i] - lo[i]], [hi[i] - vals[i]]],
                        color="#333333", capsize=4, linewidth=1.2)
        for i, val in enumerate(vals):
            ax.text(x[i] - 0.18, val / 2, f"{val:+.2f}", ha="center", va="center", fontsize=9,
                    color="#222222", bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
        ax.axhline(0, color="#333333", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(["Heat only", "Drought only", "Heat + drought\n(if additive)",
                            "Observed\ncompound"], fontsize=9)
        ax.set_title(title, fontsize=11)
        ai, ail, aih = d.amplification_index, d.amplification_index_ci_low, d.amplification_index_ci_high
        ax.text(0.5, 0.04, f"observed - additive = {ai:+.2f}  (95% CI {ail:+.2f} to {aih:+.2f})",
                transform=ax.transAxes, ha="center", fontsize=9, color="#222222")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Change vs normal months (z-score)")
    axes[0].set_ylim(-1.35, 0.1)
    fig.suptitle("Is heat + drought worse than the two effects added together?", fontsize=12)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_response_surface(surface: pd.DataFrame, filename: str = "response_surface_gpp_explained"):
    """Average GPP z for every (Tmax z, SPEI-3) bin, with the hot / dry
    cut-offs drawn in and the four boxes labelled. Bins that response_surface
    masked (fewer than MIN_BIN_N months) are grey."""
    s = surface.dropna(subset=["mean"])
    xe = np.arange(-2.0, 3.0 + 1e-9, 0.5)
    ye = np.arange(-2.5, 2.5 + 1e-9, 0.5)
    grid = np.full((len(ye) - 1, len(xe) - 1), np.nan)
    for _, r in s.iterrows():
        i = int(round((r["spei_bin"].left - ye[0]) / 0.5))
        j = int(round((r["tz_bin"].left - xe[0]) / 0.5))
        grid[i, j] = r["mean"]

    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=100)
    vmax = np.nanmax(np.abs(grid))
    ax.set_facecolor("#f2f2f2")
    m = ax.pcolormesh(xe, ye, grid, cmap="RdBu", vmin=-vmax, vmax=vmax,
                      edgecolors="white", linewidth=0.6)
    cb = fig.colorbar(m, ax=ax)
    cb.set_label("Average GPP z-score of those months\n(red = below normal, blue = above)")

    ax.axvline(cfg.THRESH.hot_z, color="black", ls="--", lw=1.2)
    ax.axhline(cfg.THRESH.dry_spei, color="black", ls="--", lw=1.2)
    box = dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.5)
    ax.text(2.0, -2.25, "COMPOUND\n(hot + dry)", ha="center", va="bottom", fontsize=8,
            fontweight="bold", bbox=box)
    ax.text(-0.5, -2.25, "dry-only", ha="center", va="bottom", fontsize=8, bbox=box)
    ax.text(2.0, 0.6, "hot-only", ha="center", va="center", fontsize=8, bbox=box)
    ax.text(-0.5, 0.6, "normal", ha="center", va="center", fontsize=8, bbox=box)

    ax.set_xticks(xe)
    ax.set_yticks(ye)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("Heat: temperature anomaly, Tmax z  (hotter →)")
    ax.set_ylabel("Water balance: SPEI-3  (← drier)")
    ax.set_title("Average GPP for every heat × dryness combination", fontsize=10)
    fig.tight_layout()
    path = cfg.FIGURES / f"{filename}.png"
    fig.savefig(path, dpi=200)  # same as the slide version (no bbox cropping)
    return fig
