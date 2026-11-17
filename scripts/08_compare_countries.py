"""
India vs Australia: formal difference tests and side-by-side figures.

Needs scripts 02-07 to have been run for BOTH regions:
    CHD_REGION=india     python scripts/0X_*.py
    CHD_REGION=australia python scripts/0X_*.py

Country-difference test: for every H1/H2 contrast, (Australia - India) with a
joint year-block bootstrap -- the SAME resampled years are applied to both
countries in each replicate, because both share the 2001-2022 calendar years
(and so large-scale drivers such as ENSO). Two-sided bootstrap p-values.

Writes results/comparison/*.csv and figures/comparison/*.png.

Usage:
    python scripts/08_compare_countries.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd.stats import _year_weights, _per_year_sums, _ci, bootstrap_p_value, benjamini_hochberg
from chd.plotting import CATEGORY_COLORS, COUNTRY_COLORS

ROOT = cfg.ROOT
REG = {
    "India": dict(proc=ROOT / "data" / "processed", res=ROOT / "results"),
    "Australia": dict(proc=ROOT / "data" / "australia" / "processed", res=ROOT / "results" / "australia"),
}
OUT_R = ROOT / "results" / "comparison"
OUT_F = ROOT / "figures" / "comparison"
OUT_R.mkdir(parents=True, exist_ok=True)
OUT_F.mkdir(parents=True, exist_ok=True)
CATS = ("normal", "hot_only", "dry_only", "compound")
CAT_LABEL = {"normal": "Normal", "hot_only": "Hot-only", "dry_only": "Dry-only", "compound": "Compound"}
COUNTRIES = ("India", "Australia")
INK, MUTED = "#222222", "#6b6b6b"

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.labelcolor": INK, "xtick.color": "#444444",
                     "ytick.color": "#444444", "axes.titlesize": 11})


def res_csv(country, name):
    return pd.read_csv(REG[country]["res"] / name)


def fmt_p(p):
    if pd.isna(p):
        return ""
    if p < 0.001:
        return "p < 0.001"
    s = f"{p:.2f}" if p >= 0.095 else f"{p:.2g}"
    if "e" in s:
        s = f"{p:.4f}"
    if s in ("1", "1.0"):
        s = "1.00"
    return f"p = {s}"


# ---------------------------------------------------------------------------
# Joint-year bootstrap of country differences
# ---------------------------------------------------------------------------
def contrasts_from_means(m):
    d_hot, d_dry, d_cmp = m["hot_only"] - m["normal"], m["dry_only"] - m["normal"], m["compound"] - m["normal"]
    return {"mean_compound": m["compound"], "d_hot": d_hot, "d_dry": d_dry, "d_compound": d_cmp,
            "compound_minus_dry": m["compound"] - m["dry_only"],
            "compound_minus_hot": m["compound"] - m["hot_only"],
            "amplification_index": d_cmp - (d_hot + d_dry)}


def country_difference_tests(tables):
    years = np.unique(np.concatenate([t["year"].unique() for t in tables.values()]))
    w = _year_weights(len(years), cfg.BOOTSTRAP_N, cfg.BOOTSTRAP_SEED)
    rows = []
    for resp, rlabel in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
        for cat_col, idx in (("category", "SPEI-3"), ("category_spi", "SPI-3")):
            pt, bt = {}, {}
            for c, df in tables.items():
                mp, mb = {}, {}
                for cat in CATS:
                    g = df[df[cat_col] == cat]
                    s, n = _per_year_sums(g[resp].values, g["year"].values, years)
                    mp[cat] = s.sum() / n.sum()
                    with np.errstate(invalid="ignore", divide="ignore"):
                        mb[cat] = (w @ s) / (w @ n)
                pt[c], bt[c] = contrasts_from_means(mp), contrasts_from_means(mb)
            for k in pt["India"]:
                diff_b = np.asarray(bt["Australia"][k]) - np.asarray(bt["India"][k])
                lo, hi = _ci(diff_b)
                rows.append({"response": rlabel, "drought_index": idx, "contrast": k,
                             "india": pt["India"][k], "australia": pt["Australia"][k],
                             "australia_minus_india": pt["Australia"][k] - pt["India"][k],
                             "ci_low": lo, "ci_high": hi, "p_value": bootstrap_p_value(diff_b)})
    out = pd.DataFrame(rows)
    out["q_bh"] = benjamini_hochberg(out["p_value"].values)
    return out


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_h1_composites():
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), sharey=True)
    width = 0.38
    for ax, (resp, title) in zip(axes, (("gpp_z", "GPP (productivity)"), ("ndvi_z", "NDVI (greenness)"))):
        x = np.arange(len(CATS))
        for k, c in enumerate(COUNTRIES):
            d = res_csv(c, f"composite_{resp}_overall.csv").set_index("category").reindex(CATS)
            xs = x + (k - 0.5) * width
            ax.bar(xs, d["mean"], width=width - 0.04, color=COUNTRY_COLORS[c], label=c)
            ax.errorbar(xs, d["mean"], yerr=[d["mean"] - d["ci_low"], d["ci_high"] - d["mean"]],
                        fmt="none", ecolor=INK, capsize=3, linewidth=1)
            for xi, v, lo, hi in zip(xs, d["mean"], d["ci_low"], d["ci_high"]):
                yl = hi + 0.03 if v >= 0 else lo - 0.03          # just past the whisker end
                ax.text(xi, yl, f"{v:+.2f}".replace("-", "−"), ha="center",
                        va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
        ax.axhline(0, color="#444444", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels([CAT_LABEL[c] for c in CATS])
        ax.set_title(title)
        ax.grid(axis="y", color="#e6e6e6", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_ylim(-1.08, 0.52)
    axes[0].set_ylabel("Mean z-score (95% CI)")
    axes[0].legend(frameon=False, loc="lower left")
    fig.suptitle("H1: vegetation anomaly in each stress category, India vs Australia (2001-2022)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_h1_composites.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def forest(ax, rows, xlabel, zero_label_left="", zero_label_right=""):
    """rows: list of (label, {country: (est, lo, hi, p)})"""
    y = np.arange(len(rows))[::-1].astype(float)
    off = {"India": 0.17, "Australia": -0.17}
    for yi, (lab, vals) in zip(y, rows):
        for c in COUNTRIES:
            if c not in vals or vals[c] is None:
                continue
            est, lo, hi, p = vals[c]
            ax.errorbar(est, yi + off[c], xerr=[[est - lo], [hi - est]], fmt="o", ms=6,
                        color=COUNTRY_COLORS[c], ecolor=COUNTRY_COLORS[c], capsize=3, linewidth=1.6,
                        label=c if yi == y[0] else None, markeredgecolor="white", markeredgewidth=0.8)
            if p is not None and not pd.isna(p):
                ax.text(1.01, yi + off[c], fmt_p(p), transform=ax.get_yaxis_transform(),
                        va="center", fontsize=7.5, color=MUTED)
    ax.axvline(0, color="#444444", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", color="#e6e6e6", linewidth=0.6)
    ax.set_axisbelow(True)
    if zero_label_left:
        ax.text(0.0, 1.01, zero_label_left, transform=ax.transAxes, fontsize=8, color=MUTED, ha="left")
    if zero_label_right:
        ax.text(1.0, 1.01, zero_label_right, transform=ax.transAxes, fontsize=8, color=MUTED, ha="right")


def fig_ai_forest():
    rows = []
    for resp, rl in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
        for idx in ("SPEI-3", "SPI-3"):
            vals = {}
            for c in COUNTRIES:
                r = res_csv(c, "robustness_spei_vs_spi.csv")
                r = r[(r["response"] == resp) & (r["drought_index"] == idx)].iloc[0]
                vals[c] = (r["amplification_index"], r["amplification_index_ci_low"],
                           r["amplification_index_ci_high"], r.get("amplification_index_p", np.nan))
            rows.append((f"{rl}, drought = {idx}", vals))
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    forest(ax, rows, "Amplification index  = Δcompound − (Δhot + Δdry)   (95% CI)",
           "← synergy (worse than the sum)", "less than the sum →")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("H2: is compound damage larger than heat + drought added together?", pad=16)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_ai_forest.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_regression():
    rows = []
    for rl in ("GPP", "NDVI"):
        for spec in ("SPEI-3", "SPEI-3 + quadratic terms", "SPI-3", "Soil moisture x VPD"):
            vals = {}
            for c in COUNTRIES:
                r = res_csv(c, "h2_regression.csv")
                r = r[(r["response"] == rl) & (r["spec"] == spec) & r["is_interaction"]].iloc[0]
                vals[c] = (r["coef"], r["ci_low"], r["ci_high"], r["p_value"])
            lab = {"SPEI-3": "heat × dryness (SPEI-3)", "SPEI-3 + quadratic terms": "  … + curvature terms",
                   "SPI-3": "heat × dryness (SPI-3)", "Soil moisture x VPD": "VPD × soil dryness"}[spec]
            rows.append((f"{rl}: {lab}", vals))
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    forest(ax, rows, "Interaction coefficient c  (z per unit² ; 95% CI, year-clustered)",
           "← synergy", "antagonism →")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("H2 as a regression: interaction term c (cell fixed effects)", pad=16)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_regression_interaction.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_sensitivity():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.0), sharey=True)
    for ax, rl in zip(axes, ("GPP", "NDVI")):
        specs = res_csv("India", "sensitivity_h1_h2.csv")["spec"].unique()
        rows = []
        for spec in specs:
            vals = {}
            for c in COUNTRIES:
                s = res_csv(c, "sensitivity_h1_h2.csv")
                s = s[(s["response"] == rl)]
                # period labels are identical across countries
                r = s[s["spec"] == spec]
                if len(r) == 0:
                    vals[c] = None
                    continue
                r = r.iloc[0]
                vals[c] = (r["amplification_index"], r["amplification_index_ci_low"],
                           r["amplification_index_ci_high"], None)
            rows.append((spec, vals))
        forest(ax, rows, "Amplification index (95% CI)", "← synergy", "")
        ax.set_title(rl)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2, fontsize=9.5)
    fig.suptitle("Sensitivity of the H2 result to every analysis choice", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT_F / "compare_sensitivity_ai.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_risk():
    rows = []
    for resp, rl in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
        for col, idx in (("category", "SPEI-3"), ("category_spi", "SPI-3")):
            vals = {}
            for c in COUNTRIES:
                r = res_csv(c, "risk_amplification.csv")
                r = r[(r["response"] == resp) & (r["category_col"] == col) & (r["metric"] == "reri")].iloc[0]
                vals[c] = (r["estimate"], r["ci_low"], r["ci_high"], r["p_value"])
            rows.append((f"{rl}, drought = {idx}", vals))
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    forest(ax, rows, "RERI = RR_compound − RR_hot − RR_dry + 1   (95% CI)",
           "← less than additive", "more than additive →")
    # benchmark: RERI that exactly additive MEAN effects would already produce (threshold convexity)
    bench = pd.read_csv(OUT_R / "reri_vs_additive_expectation.csv")
    y = np.arange(len(rows))[::-1].astype(float)
    off = {"India": 0.17, "Australia": -0.17}
    k = 0
    for resp in ("gpp_z", "ndvi_z"):
        for idx in ("SPEI-3", "SPI-3"):
            for c in COUNTRIES:
                b = bench[(bench["country"] == c) & (bench["response"] == resp) & (bench["drought_index"] == idx)]
                ax.plot(b["reri_if_means_additive"].iloc[0], y[k] + off[c], marker="D", ms=7, mfc="none",
                        mec=COUNTRY_COLORS[c], mew=1.6, ls="none")
            k += 1
    h, l = ax.get_legend_handles_labels()
    h.append(plt.Line2D([], [], marker="D", ms=7, mfc="none", mec="#666666", mew=1.6, ls="none"))
    l.append("expected if mean effects add up")
    ax.legend(h, l, frameon=False, loc="lower right", fontsize=8.5)
    ax.set_title("Risk view: chance of a severe loss (z ≤ −1); ◇ = what additive mean effects alone would give",
                 pad=16, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_risk_reri.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_km():
    from lifelines import KaplanMeierFitter
    colors = {"compound": CATEGORY_COLORS["compound"], "drought_only": CATEGORY_COLORS["dry_only"],
              "heat_only": CATEGORY_COLORS["hot_only"]}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.0), sharey=True)
    for ax, c in zip(axes, COUNTRIES):
        ev = pd.read_csv(REG[c]["proc"] / "events.csv")
        ev = ev[ev["has_impact"]]
        for et, col in colors.items():
            g = ev[ev["event_type"] == et]
            kmf = KaplanMeierFitter().fit(g["recovery_time_months"], ~g["censored"].astype(bool))
            cdf = 1 - kmf.survival_function_
            ax.step(cdf.index, cdf.iloc[:, 0], where="post", color=col, linewidth=2,
                    label=f"{et.replace('_', '-')} (n={len(g):,})")
        ax.set_xlim(0, 24)
        ax.set_title(c)
        ax.set_xlabel("Months after event end")
        ax.grid(color="#e6e6e6", linewidth=0.6)
        ax.legend(frameon=False, loc="lower right", fontsize=8.5)
    axes[0].set_ylabel("Fraction recovered (Kaplan-Meier)")
    fig.suptitle("H3: recovery after impactful events (GPP z back to ≥ −0.5 for 2 active months)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_recovery_km.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig_trend():
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for c in COUNTRIES:
        t = res_csv(c, "compound_area_trend.csv")
        st = res_csv(c, "compound_area_trend_stats.csv").iloc[0]
        ax.plot(t["year"], t["pct_area"], color=COUNTRY_COLORS[c], linewidth=2, marker="o", ms=3.5,
                label=f"{c}: Sen slope {st['slope']:+.2f} pp/yr, Mann-Kendall {fmt_p(st['p_value'])}")
        ax.plot(t["year"], st["intercept"] + st["slope"] * t["year"], color=COUNTRY_COLORS[c],
                linewidth=1, linestyle="--")
    ax.set_ylabel("% of active cell-months\nthat are compound")
    ax.set_ylim(bottom=0)
    ax.grid(color="#e6e6e6", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("Are compound months becoming more common? (1991-2024)")
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_compound_trend.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def mechanism_tests(tables):
    """Why is compound damage additive in India but sub-additive in Australia?

    (a) Overlap: are 'hot-only' months already partly dry and 'dry-only' months partly hot?
        If so, Δhot + Δdry double-counts part of the damage and AI > 0 by construction.
    (b) Floor effect: in low-productivity (arid) cells there is little GPP left to lose, so
        stresses cannot add up. Test: AI by tercile of each cell's mean annual GPP.
    """
    from chd.stats import bootstrap_category_contrasts
    import xarray as xr
    over, terc = [], []
    for c, df in tables.items():
        act = df
        over.append({"country": c,
                     "spei03_in_hot_only": act.loc[act["category"] == "hot_only", "spei03"].mean(),
                     "spei03_in_normal": act.loc[act["category"] == "normal", "spei03"].mean(),
                     "tmax_z_in_dry_only": act.loc[act["category"] == "dry_only", "tmax_z"].mean(),
                     "tmax_z_in_normal": act.loc[act["category"] == "normal", "tmax_z"].mean(),
                     "corr_tmax_z_spei03": act[["tmax_z", "spei03"]].corr().iloc[0, 1]})
        ds = xr.open_dataset(REG[c]["proc"] / "cube.nc")
        ann = (ds["gpp_gC_m2"].mean("time") * 12).to_dataframe(name="gpp_annual").reset_index()
        ds.close()
        ann["cell_id"] = ann["lat"].round(4).astype(str) + "_" + ann["lon"].round(4).astype(str)
        gmap = ann.set_index("cell_id")["gpp_annual"]
        cell_gpp = gmap.reindex(df["cell_id"].unique())
        edges = np.nanquantile(cell_gpp.values, [0, 1 / 3, 2 / 3, 1])
        lab = pd.cut(cell_gpp, edges, labels=["low (driest)", "middle", "high (wettest)"], include_lowest=True)
        tlab = df["cell_id"].map(lab)
        for t in ["low (driest)", "middle", "high (wettest)"]:
            g = df[tlab == t]
            for resp, rl in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
                r = bootstrap_category_contrasts(g[resp].values, g["year"].values, g["category"].values)
                terc.append({"country": c, "gpp_tercile": t, "response": rl,
                             "gpp_range": f"{edges[['low (driest)', 'middle', 'high (wettest)'].index(t)]:.0f}-"
                                          f"{edges[['low (driest)', 'middle', 'high (wettest)'].index(t) + 1]:.0f}",
                             "d_hot": r["d_hot"]["estimate"], "d_dry": r["d_dry"]["estimate"],
                             "d_compound": r["d_compound"]["estimate"],
                             "ai": r["amplification_index"]["estimate"],
                             "ai_ci_low": r["amplification_index"]["ci_low"],
                             "ai_ci_high": r["amplification_index"]["ci_high"],
                             "ai_p": r["amplification_index"]["p_value"], "n_compound": r["n_compound"]})
    return pd.DataFrame(over), pd.DataFrame(terc)


def reri_additive_expectation(tables, thresh=-1.0, n_boot=cfg.BOOTSTRAP_N, seed=cfg.BOOTSTRAP_SEED):
    """Is a positive RERI evidence of synergy, or just a threshold effect?

    P(z <= -1) is convex in the mean, so purely ADDITIVE mean shifts already push more
    compound months past the threshold than the additive-risk expectation, giving RERI > 0.
    Benchmark: shift the observed compound distribution so that its mean equals the
    additive prediction (normal + Δhot + Δdry), recompute P(z <= -1) and the RERI.
    'excess' = observed RERI - RERI expected under additive means; > 0 would be synergy in
    the tail beyond what additive means imply. Year-block bootstrap CI and p for the excess.
    """
    rows = []
    for c, df in tables.items():
        years = np.unique(df["year"])
        w = _year_weights(len(years), n_boot, seed)
        for resp in ("gpp_z", "ndvi_z"):
            for col in ("category", "category_spi"):
                d = df[df[col].isin(CATS)][[resp, col, "year"]].dropna()
                # per-year sums for means and exceedances of each category
                S, Nn, E = {}, {}, {}
                for cat in CATS:
                    g = d[d[col] == cat]
                    S[cat], Nn[cat] = _per_year_sums(g[resp].values, g["year"].values, years)
                    E[cat], _ = _per_year_sums((g[resp] <= thresh).astype(float).values, g["year"].values, years)
                comp = d[d[col] == "compound"]

                def stats(weights):
                    mu = {k: (weights @ S[k]) / (weights @ Nn[k]) for k in CATS}
                    p = {k: (weights @ E[k]) / (weights @ Nn[k]) for k in CATS}
                    return mu, p

                def reri(p, pc):
                    return (pc - p["hot_only"] - p["dry_only"] + p["normal"]) / p["normal"]

                mu, p = stats(np.ones(len(years)))
                mu_add = mu["hot_only"] + mu["dry_only"] - mu["normal"]
                shift = mu_add - mu["compound"]
                p_add = float(((comp[resp].values + shift) <= thresh).mean())
                obs, exp_ = reri(p, p["compound"]), reri(p, p_add)
                # bootstrap the excess (the shifted-distribution exceedance is recomputed per year)
                cy = comp["year"].values
                cv = comp[resp].values
                boot = []
                for b in range(min(n_boot, 2000)):
                    wb = w[b]
                    mub, pb = stats(wb)
                    sh = (mub["hot_only"] + mub["dry_only"] - mub["normal"]) - mub["compound"]
                    ex, _ = _per_year_sums(((cv + sh) <= thresh).astype(float), cy, years)
                    pab = (wb @ ex) / (wb @ Nn["compound"])
                    boot.append(reri(pb, pb["compound"]) - reri(pb, pab))
                boot = np.asarray(boot)
                lo, hi = _ci(boot)
                rows.append({"country": c, "response": resp, "drought_index": "SPEI-3" if col == "category" else "SPI-3",
                             "reri_observed": obs, "reri_if_means_additive": exp_, "excess": obs - exp_,
                             "excess_ci_low": lo, "excess_ci_high": hi, "excess_p": bootstrap_p_value(boot)})
    return pd.DataFrame(rows)


def fig_aridity(terc):
    rows = []
    for rl in ("GPP", "NDVI"):
        for t in ["low (driest)", "middle", "high (wettest)"]:
            vals = {}
            for c in COUNTRIES:
                r = terc[(terc["country"] == c) & (terc["response"] == rl) & (terc["gpp_tercile"] == t)].iloc[0]
                vals[c] = (r["ai"], r["ai_ci_low"], r["ai_ci_high"], r["ai_p"])
            rows.append((f"{rl}: {t} third of cells", vals))
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    forest(ax, rows, "Amplification index (95% CI), by each cell's mean annual GPP",
           "← synergy", "less than the sum →")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("Is sub-additivity a 'floor effect' of dry, low-productivity land?", pad=16)
    fig.tight_layout()
    fig.savefig(OUT_F / "compare_ai_by_productivity.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def summary_table():
    """One row per key number, both countries -- the source for comparison slides."""
    rows = []
    for c in COUNTRIES:
        ct = res_csv(c, "category_shares_active.csv").iloc[0]
        sa = res_csv(c, "study_area_counts.csv").iloc[0]
        mech = res_csv(c, "mechanism_check.csv").set_index("category")
        tr = res_csv(c, "compound_area_trend_stats.csv").iloc[0]
        row = {"country": c, "country_cells": sa["country_cells"], "active_cell_months": sa["active_cell_months"],
               **{f"share_{k}": 100 * ct[k] for k in CATS},
               **{f"sm_z_{k}": mech.loc[k, "sm_z"] for k in CATS},
               **{f"vpd_z_{k}": mech.loc[k, "vpd_z"] for k in CATS},
               "trend_slope": tr["slope"], "trend_p": tr["p_value"]}
        for resp in ("gpp_z", "ndvi_z"):
            o = res_csv(c, f"contrasts_{resp}_overall.csv").iloc[0]
            for k in ("mean_normal", "mean_hot_only", "mean_dry_only", "mean_compound"):
                row[f"{resp}_{k}"] = o[k]
            for k in ("compound_minus_dry", "compound_minus_hot", "amplification_index"):
                row[f"{resp}_{k}"] = o[k]
                row[f"{resp}_{k}_ci_low"] = o[f"{k}_ci_low"]
                row[f"{resp}_{k}_ci_high"] = o[f"{k}_ci_high"]
                row[f"{resp}_{k}_p"] = o[f"{k}_p"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("country").T


def main():
    tables = {c: pd.read_pickle(REG[c]["proc"] / "long_table.pkl") for c in COUNTRIES}
    for c, t in tables.items():
        print(f"{c}: {len(t):,} active cell-months, {t['cell_id'].nunique():,} cells")

    diff = country_difference_tests(tables)
    diff.to_csv(OUT_R / "country_difference_tests.csv", index=False)
    print("\nAustralia - India (joint year-block bootstrap):")
    print(diff.round(4).to_string())

    over, terc = mechanism_tests(tables)
    over.to_csv(OUT_R / "mechanism_overlap.csv", index=False)
    terc.to_csv(OUT_R / "ai_by_productivity_tercile.csv", index=False)
    print("\nOverlap check:\n", over.round(3).to_string())
    print("\nAI by productivity tercile:\n", terc.round(3).to_string())
    fig_aridity(terc)

    rexp = reri_additive_expectation(tables)
    rexp.to_csv(OUT_R / "reri_vs_additive_expectation.csv", index=False)
    print("\nRERI observed vs expected if mean effects were exactly additive:\n", rexp.round(3).to_string())

    summ = summary_table()
    summ.to_csv(OUT_R / "comparison_summary.csv")
    print("\nSummary:\n", summ.to_string())

    fig_h1_composites()
    fig_ai_forest()
    fig_regression()
    fig_sensitivity()
    fig_risk()
    fig_km()
    fig_trend()
    print(f"\nFigures in {OUT_F}")


if __name__ == "__main__":
    main()
