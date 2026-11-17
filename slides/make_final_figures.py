"""Slide/report figures for the final submission, for each country that has results:

  figures[/australia]/additivity_gpp_ndvi.png             H2 additivity bars (with bootstrap p-values)
  figures[/australia]/response_surface_gpp_explained.png  explained heat x dryness response surface
  figures[/australia]/pvalue_ladder.png                   naive vs honest p-values for one contrast

Run from midSub/:  python slides/make_final_figures.py
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chd.plotting import CATEGORY_COLORS  # noqa: E402

HOT, DRY, CMP, GREY = (CATEGORY_COLORS["hot_only"], CATEGORY_COLORS["dry_only"],
                       CATEGORY_COLORS["compound"], "#8a8a8a")
COUNTRIES = {"India": (ROOT / "results", ROOT / "figures"),
             "Australia": (ROOT / "results" / "australia", ROOT / "figures" / "australia")}


def fmt_p(p):
    if p < 0.001:
        return "p < 0.001"
    s = f"{p:.2f}" if p >= 0.095 else f"{p:.2g}"
    if "e" in s:
        s = f"{p:.4f}"
    if s in ("1", "1.0"):
        s = "1.00"
    return f"p = {s}"


def additivity(country, R, F):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    lows = []
    for ax, (v, title) in zip(axes, [("gpp_z", "GPP (productivity)"), ("ndvi_z", "NDVI (greenness)")]):
        d = pd.read_csv(R / f"contrasts_{v}_overall.csv").iloc[0]
        vals = [d.d_hot, d.d_dry, d.d_hot + d.d_dry, d.d_compound]
        lo = [d.d_hot_ci_low, d.d_dry_ci_low, np.nan, d.d_compound_ci_low]
        hi = [d.d_hot_ci_high, d.d_dry_ci_high, np.nan, d.d_compound_ci_high]
        lows.append(np.nanmin(lo + vals))
        x = np.arange(4)
        bars = ax.bar(x, vals, color=[HOT, DRY, "white", CMP], edgecolor=["none", "none", GREY, "none"],
                      linewidth=1.5, width=0.62)
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
        ai, ail, aih, aip = (d.amplification_index, d.amplification_index_ci_low,
                             d.amplification_index_ci_high, d.amplification_index_p)
        ax.text(0.5, 0.04, f"observed − additive = {ai:+.2f}  (95% CI {ail:+.2f} to {aih:+.2f}; {fmt_p(aip)})",
                transform=ax.transAxes, ha="center", fontsize=8.5, color="#222222")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("Change vs normal months (z-score)")
    axes[0].set_ylim(min(lows) - 0.3, 0.1)
    fig.suptitle(f"{country}: is heat + drought worse than the two effects added together?", fontsize=12)
    fig.tight_layout()
    fig.savefig(F / "additivity_gpp_ndvi.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def lower_edge(s):
    return float(s.strip("(]").split(",")[0])


def response_surface(country, R, F):
    d = pd.read_csv(R / "response_surface_gpp.csv").dropna(subset=["mean"])
    d = d[d["n"] >= 30].copy()
    d["x0"] = d["tz_bin"].map(lower_edge)
    d["y0"] = d["spei_bin"].map(lower_edge)
    xe = np.arange(-2.0, 3.0 + 1e-9, 0.5)
    ye = np.arange(-2.5, 2.5 + 1e-9, 0.5)
    grid = np.full((len(ye) - 1, len(xe) - 1), np.nan)
    for _, r in d.iterrows():
        grid[int(round((r.y0 - ye[0]) / 0.5)), int(round((r.x0 - xe[0]) / 0.5))] = r["mean"]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    vmax = np.nanmax(np.abs(grid))
    ax.set_facecolor("#f2f2f2")
    m = ax.pcolormesh(xe, ye, grid, cmap="RdBu", vmin=-vmax, vmax=vmax, edgecolors="white", linewidth=0.6)
    cb = fig.colorbar(m, ax=ax)
    cb.set_label("Average GPP z-score of those months\n(red = below normal, blue = above)")
    ax.axvline(1, color="black", ls="--", lw=1.2)
    ax.axhline(-1, color="black", ls="--", lw=1.2)
    box = dict(facecolor="white", alpha=0.85, edgecolor="none", pad=1.5)
    ax.text(2.0, -2.25, "COMPOUND\n(hot + dry)", ha="center", va="bottom", fontsize=8, fontweight="bold", bbox=box)
    ax.text(-0.5, -2.25, "dry-only", ha="center", va="bottom", fontsize=8, bbox=box)
    ax.text(2.0, 0.6, "hot-only", ha="center", va="center", fontsize=8, bbox=box)
    ax.text(-0.5, 0.6, "normal", ha="center", va="center", fontsize=8, bbox=box)
    ax.set_xticks(xe)
    ax.set_yticks(ye)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("Heat: temperature anomaly, Tmax z  (hotter →)")
    ax.set_ylabel("Water balance: SPEI-3  (← drier)")
    ax.set_title(f"{country}: average GPP for every heat × dryness combination", fontsize=10)
    fig.tight_layout()
    fig.savefig(F / "response_surface_gpp_explained.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def pvalue_ladder(country, R, F):
    """Same contrast (GPP: compound - dry-only), three ways of getting a p-value."""
    naive = pd.read_csv(R / "naive_cellmonth_tests.csv")
    naive = naive[(naive["response"] == "gpp_z") & (naive["test"] == "compound - dry_only")].iloc[0]
    boot = pd.read_csv(R / "contrasts_gpp_z_overall.csv").iloc[0]
    yl = pd.read_csv(R / "year_level_tests.csv")
    yl = yl[(yl["response"] == "gpp_z") & (yl["spec"] == "SPEI-3") & (yl["test"] == "compound - dry_only")].iloc[0]
    rows = [("Naive t-test\n(every grid-month independent)", max(naive["p_naive_welch"], 1e-300),
             f"n = {int(naive['n_a'] + naive['n_b']):,}"),
            ("Year-block bootstrap\n(our main method)", boot["compound_minus_dry_p"], "22 years resampled"),
            ("Paired t-test on yearly means\n(one value per year)", yl["p_paired_t"], f"n = {int(yl['n_years'])} years")]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    y = np.arange(len(rows))[::-1]
    vals = [-np.log10(r[1]) for r in rows]
    ax.barh(y, vals, color=["#9aa7b8", CMP, "#4C72B0"], height=0.55)
    ax.axvline(-np.log10(0.05), color="#B23A48", ls="--", lw=1.2)
    ax.text(-np.log10(0.05), -0.62, "p = 0.05 ", color="#B23A48", fontsize=8, va="center", ha="right")
    for yi, v, r in zip(y, vals, rows):
        lab = "p < 1e-300" if r[1] <= 1e-300 else (f"p = {r[1]:.1e}" if r[1] < 1e-3 else f"p = {r[1]:.3f}")
        xpos = v * 1.3 if v > 10 else max(v, -np.log10(0.05)) + 0.4
        ax.text(xpos, yi, f"{lab}   ({r[2]})", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xscale("symlog", linthresh=10)
    ax.set_xlim(0, max(vals) * 30 + 20)
    ax.set_ylim(-0.8, len(rows) - 0.5)
    ax.set_xlabel("−log10(p)   (longer bar = smaller p-value)")
    ax.set_title(f"{country}, GPP compound − dry-only = {boot['compound_minus_dry']:+.2f}: "
                 "same difference, three p-values", fontsize=9.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(F / "pvalue_ladder.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for country, (R, F) in COUNTRIES.items():
        if not (R / "contrasts_gpp_z_overall.csv").exists():
            print(f"skip {country}: no results yet")
            continue
        additivity(country, R, F)
        response_surface(country, R, F)
        if (R / "naive_cellmonth_tests.csv").exists():
            pvalue_ladder(country, R, F)
        print("figures done for", country)
