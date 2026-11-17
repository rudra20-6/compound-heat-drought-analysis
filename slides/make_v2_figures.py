"""Figure for slides/midsub_v2.tex: additivity check (H2).
Run from midSub/:  python slides/make_v2_figures.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
HOT, DRY, CMP, GREY = "#DD8452", "#C44E52", "#55A868", "#8a8a8a"  # same colours as the other figures

fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, (v, title) in zip(axes, [("gpp_z", "GPP (productivity)"), ("ndvi_z", "NDVI (greenness)")]):
    d = pd.read_csv(R / f"contrasts_{v}_overall.csv").iloc[0]
    vals = [d.d_hot, d.d_dry, d.d_hot + d.d_dry, d.d_compound]
    lo = [d.d_hot_ci_low, d.d_dry_ci_low, np.nan, d.d_compound_ci_low]
    hi = [d.d_hot_ci_high, d.d_dry_ci_high, np.nan, d.d_compound_ci_high]
    x = np.arange(4)
    colors = [HOT, DRY, "white", CMP]
    bars = ax.bar(x, vals, color=colors, edgecolor=["none", "none", GREY, "none"],
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
    ai, ail, aih = d.amplification_index, d.amplification_index_ci_low, d.amplification_index_ci_high
    ax.text(0.5, 0.04, f"observed - additive = {ai:+.2f}  (95% CI {ail:+.2f} to {aih:+.2f})",
            transform=ax.transAxes, ha="center", fontsize=9, color="#222222")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].set_ylabel("Change vs normal months (z-score)")
axes[0].set_ylim(-1.35, 0.1)
fig.suptitle("Is heat + drought worse than the two effects added together?", fontsize=12)
fig.tight_layout()
fig.savefig(F / "additivity_gpp_ndvi.png", dpi=300, bbox_inches="tight")
print("saved", F / "additivity_gpp_ndvi.png")
