"""
Figure-generation helpers for the mid-eval slides and demo notebook.

Each function saves a PNG (300 dpi, for slides) to config.FIGURES and
returns the matplotlib Figure (so the notebook can also just display it
inline). Kept deliberately simple (no seaborn dependency) since the
mid-eval deliverable is a fixed set of ~10 figures, not a general viz library.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as cfg

CATEGORY_ORDER = ["normal", "hot_only", "dry_only", "compound"]
CATEGORY_COLORS = {
    "normal": "#4C72B0", "hot_only": "#E89A2E",
    "dry_only": "#B23A48", "compound": "#3E9B5C",
}
# Validated (dataviz validate_palette.js, light, all pairs): CVD dE >= 8.2, normal-vision
# dE >= 20.3. The mid-sub orange/red pair (#DD8452/#C44E52) failed the normal-vision floor.
COUNTRY_COLORS = {"India": "#6250d6", "Australia": "#1baf7a"}
# Note: "compound" is intentionally NOT colored red/alarm here -- it is
# compared directly against hot_only/dry_only, so color encodes *category
# identity*, not severity. Severity is shown by bar height / CI, not hue.


def _savefig(fig, name: str):
    path = cfg.FIGURES / f"{name}.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    return path


def plot_category_composite(composite_df: pd.DataFrame, response_label: str,
                             title: str, filename: str):
    """Bar chart of mean response by category with bootstrap 95% CI whiskers."""
    df = composite_df.set_index("category").reindex(CATEGORY_ORDER)
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(CATEGORY_ORDER))
    heights = df["mean"].values
    yerr = np.vstack([heights - df["ci_low"].values, df["ci_high"].values - heights])
    colors = [CATEGORY_COLORS[c] for c in CATEGORY_ORDER]

    ax.bar(x, heights, yerr=yerr, capsize=4, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "-") for c in CATEGORY_ORDER])
    ax.set_ylabel(response_label)
    ax.set_title(title)
    for xi, n, flagged in zip(x, df["n"], df["flagged_low_n"]):
        marker = "*" if flagged else ""
        ax.annotate(f"n={int(n)}{marker}", (xi, 0), xytext=(0, -14),
                    textcoords="offset points", ha="center", fontsize=8)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_response_surface(surface_df: pd.DataFrame, response_label: str,
                           title: str, filename: str):
    """Heatmap of mean response_var over (tmax_z bin) x (spei03 bin)."""
    pivot = surface_df.pivot(index="spei_bin", columns="tz_bin", values="mean")
    # interval index -> midpoint for plotting/sorting
    tz_mid = [iv.mid for iv in pivot.columns]
    spei_mid = [iv.mid for iv in pivot.index]
    order_x = np.argsort(tz_mid)
    order_y = np.argsort(spei_mid)[::-1]  # dry (negative) at bottom
    data = pivot.values[order_y][:, order_x]

    fig, ax = plt.subplots(figsize=(6, 5))
    vmax = np.nanmax(np.abs(data)) if np.any(~np.isnan(data)) else 1
    im = ax.imshow(data, cmap="RdBu", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(tz_mid)))
    ax.set_xticklabels([f"{tz_mid[i]:.1f}" for i in order_x], rotation=45, fontsize=7)
    ax.set_yticks(range(len(spei_mid)))
    ax.set_yticklabels([f"{spei_mid[i]:.1f}" for i in order_y], fontsize=7)
    ax.set_xlabel("Tmax z-score")
    ax.set_ylabel("SPEI-3")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=response_label)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_amplification_by_stratum(ai_df: pd.DataFrame, group_col: str,
                                   title: str, filename: str):
    """Horizontal bars of the amplification index per stratum, with 95% CI
    whiskers when available. Hatched bars = CI includes zero (not significant)."""
    fig, ax = plt.subplots(figsize=(6, 4))
    df = ai_df.sort_values("amplification_index")
    vals = df["amplification_index"].values
    colors = ["#B23A48" if v < 0 else "#4C72B0" for v in vals]
    xerr = None
    if {"amplification_index_ci_low", "amplification_index_ci_high"} <= set(df.columns):
        xerr = np.vstack([vals - df["amplification_index_ci_low"].values,
                          df["amplification_index_ci_high"].values - vals])
    bars = ax.barh(df[group_col].astype(str), vals, color=colors, xerr=xerr, capsize=3)
    if "amplification_index_sig" in df.columns:
        for bar, sig in zip(bars, df["amplification_index_sig"].values):
            if not sig:
                bar.set_alpha(0.35)
                bar.set_hatch("//")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Amplification index (< 0 = synergistic; faded = CI includes 0)")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_area_trend(year_pct_df: pd.DataFrame, trend: dict, title: str, filename: str):
    """Line plot of %-area-under-compound-stress per year, with Sen's-slope trend line."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(year_pct_df["year"], year_pct_df["pct_area"], "o-", color=CATEGORY_COLORS["compound"])
    if not np.isnan(trend.get("slope", np.nan)):
        years = year_pct_df["year"].values
        fit = trend["intercept"] + trend["slope"] * years
        ax.plot(years, fit, "--", color="black",
                 label=f"Sen slope = {trend['slope']:.3f}/yr (p={trend['p_value']:.3f})")
        ax.legend()
    ax.set_xlabel("Year")
    ax.set_ylabel("% of active cell-months that are compound")
    ax.set_title(title)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_recovery_composite(composite_df: pd.DataFrame, response_label: str,
                             title: str, filename: str):
    """Superposed-epoch composite: one line + shaded CI per event_type."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = {"compound": "#3E9B5C", "drought_only": "#B23A48", "heat_only": "#E89A2E"}
    for event_type, g in composite_df.groupby("event_type"):
        g = g.sort_values("offset_months")
        c = colors.get(event_type, None)
        ax.plot(g["offset_months"], g["mean"], label=event_type.replace("_", "-"), color=c)
        ax.fill_between(g["offset_months"], g["ci_low"], g["ci_high"], alpha=0.2, color=c)
    ax.axvline(0, color="black", linestyle=":", linewidth=1, label="event start")
    ax.axhline(0, color="gray", linewidth=0.6)
    ax.set_xlabel("Months relative to event start")
    ax.set_ylabel(response_label)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def map_figsize(lat, lon, height=5.5):
    """Figure size that keeps the map's aspect ratio (India is tall, Australia wide)."""
    ratio = (float(np.max(lon)) - float(np.min(lon))) / max(float(np.max(lat)) - float(np.min(lat)), 1e-6)
    return (max(4.5, min(9.0, height * ratio * 0.95 + 1.2)), height)


def plot_map(ds_var, lat, lon, title: str, filename: str, cmap="viridis",
             vmin=None, vmax=None, cbar_label=""):
    """Generic lat/lon map (no cartopy dependency -- plain imshow with extent)."""
    fig, ax = plt.subplots(figsize=map_figsize(lat, lon))
    half = 0.5 * abs(float(lat[1] - lat[0])) if len(lat) > 1 else 0.0
    extent = [lon.min() - half, lon.max() + half, lat.min() - half, lat.max() + half]
    im = ax.imshow(ds_var, extent=extent, origin="upper", cmap=cmap, vmin=vmin, vmax=vmax,
                    aspect="equal", interpolation="nearest")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title, fontsize=9)
    fig.colorbar(im, ax=ax, label=cbar_label, shrink=0.8)
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_qc_timeseries(dates, series_dict: dict, title: str, filename: str,
                        known_event_years=None, shade_spans=None):
    fig, ax = plt.subplots(figsize=(9, 4))
    for label, values in series_dict.items():
        ax.plot(dates, values, label=label)
    if shade_spans:
        for a, b in shade_spans:
            ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="red", alpha=0.08)
    elif known_event_years:
        for y in known_event_years:
            ax.axvspan(pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-30"),
                       color="red", alpha=0.08)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    _savefig(fig, filename)
    return fig


def plot_study_area(ds, filename: str = "study_area_landcover"):
    """Dominant WorldCover class per country cell (purity >= threshold) with the
    H4 sub-region cutoff line."""
    frac_cols = [c for c in ds.data_vars if c.startswith("frac_")]
    fracs = np.nan_to_num(np.stack([ds[c].values for c in frac_cols], axis=0))
    names = [c.replace("frac_", "") for c in frac_cols]
    dom = np.argmax(fracs, axis=0).astype(float)
    dom[np.max(fracs, axis=0) < cfg.THRESH.landcover_purity] = np.nan
    india = ds["is_india"].values
    dom[~india] = np.nan
    # India cells with no class >= purity threshold are shown as "mixed"
    MIXED = len(names)
    dom[india & np.isnan(dom)] = MIXED

    # tab10 colours in class order (cropland = red, as in the original figure);
    # tab10 has only 10 colours, so the 11th class gets its own gold instead of
    # repeating cyan. Mixed cells stay white, as before.
    colours = {"tree_cover": "#1f77b4", "shrubland": "#ff7f0e", "grassland": "#2ca02c",
               "cropland": "#d62728", "built_up": "#9467bd", "bare_sparse": "#8c564b",
               "snow_ice": "#e377c2", "water": "#7f7f7f", "wetland": "#bcbd22",
               "mangrove": "#17becf", "moss_lichen": "#e7ba52"}
    cmap = mcolors.ListedColormap([colours.get(n, "#000000") for n in names] + ["#ffffff"])

    lat, lon = ds["lat"].values, ds["lon"].values
    w, h = map_figsize(lat, lon, height=5.2)
    fig, ax = plt.subplots(figsize=(w + 2.2, h))
    half = 0.5 * abs(float(lat[1] - lat[0]))  # extent must use cell edges, not centres
    ax.imshow(dom, extent=[lon.min() - half, lon.max() + half, lat.min() - half, lat.max() + half],
              origin="upper", cmap=cmap, vmin=-0.5, vmax=MIXED + 0.5, interpolation="nearest")
    ax.axhline(cfg.SUBREGION_LAT_CUT, color="black", linestyle="--", linewidth=1.5)

    # legend: only classes that actually occur, with cell counts
    from matplotlib.patches import Patch  # noqa: local import, only used here
    handles = []
    for k, n in enumerate(names + ["mixed (no class >=50%)"]):
        cnt = int(np.sum(dom == k))
        if cnt:
            handles.append(Patch(facecolor=cmap(k), edgecolor="0.6" if k == MIXED else cmap(k),
                                 linewidth=0.5, label=f"{n.replace('_', ' ')} ({cnt})"))
    handles.append(plt.Line2D([], [], color="black", linestyle="--",
                              label=f"Sub-region split ({abs(cfg.SUBREGION_LAT_CUT):g}°"
                                    f"{'N' if cfg.SUBREGION_LAT_CUT >= 0 else 'S'})"))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N; negative = °S)" if lat.min() < 0 else "Latitude (°N)")
    ax.set_title("Dominant land cover per 0.25° cell (ESA WorldCover 2021)", fontsize=9)
    ax.text(0.01, 0.01, "Boundary: USDOS LSIB 2017, not authoritative",
            transform=ax.transAxes, fontsize=6, color="0.3")
    fig.tight_layout()
    _savefig(fig, filename)
    return fig
