"""Figures used only by slides/midsub_v4.tex.

Run from midSub/:  python slides/make_v4_figures.py
Writes figures/response_surface_gpp_explained.png from results/response_surface_gpp.csv
(same numbers as figures/response_surface_gpp.png, with clearer labels, bin-edge
ticks and the hot / dry thresholds drawn in).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
d = pd.read_csv(ROOT / "results" / "response_surface_gpp.csv").dropna(subset=["mean"])
d = d[d["n"] >= 30]


def lower_edge(s):
    return float(s.strip("(]").split(",")[0])


d["x0"] = d["tz_bin"].map(lower_edge)
d["y0"] = d["spei_bin"].map(lower_edge)
xe = np.arange(-2.0, 3.0 + 1e-9, 0.5)
ye = np.arange(-2.5, 2.5 + 1e-9, 0.5)
grid = np.full((len(ye) - 1, len(xe) - 1), np.nan)
for _, r in d.iterrows():
    i = int(round((r.y0 - ye[0]) / 0.5))
    j = int(round((r.x0 - xe[0]) / 0.5))
    grid[i, j] = r["mean"]

fig, ax = plt.subplots(figsize=(6.4, 4.8))
vmax = np.nanmax(np.abs(grid))
ax.set_facecolor("#f2f2f2")
m = ax.pcolormesh(xe, ye, grid, cmap="RdBu", vmin=-vmax, vmax=vmax,
                  edgecolors="white", linewidth=0.6)
cb = fig.colorbar(m, ax=ax)
cb.set_label("Average GPP z-score of those months\n(red = below normal, blue = above)")

# thresholds used for the four boxes
ax.axvline(1, color="black", ls="--", lw=1.2)
ax.axhline(-1, color="black", ls="--", lw=1.2)
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
out = ROOT / "figures" / "response_surface_gpp_explained.png"
fig.savefig(out, dpi=200)
print("wrote", out)
