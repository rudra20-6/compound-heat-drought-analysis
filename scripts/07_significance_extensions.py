"""
Final-phase extensions (run per region; CHD_REGION=india | australia):

  A. Significance testing (feedback: "look at p-tests")
     A1. Year-block bootstrap p-values for every H1/H2 contrast (from 04_impacts, re-tabulated)
     A2. Year-level paired tests: per-year category means (one value per year, n ~ 22),
         paired t-test and Wilcoxon signed-rank for compound vs dry-only / hot-only / normal,
         and one-sample tests of the yearly amplification index against 0
     A3. Naive Welch t-test that treats every cell-month as independent -- shown only to
         illustrate pseudo-replication (p-values collapse to ~0 because n ~ 10^5)
     A4. Benjamini-Hochberg FDR correction across the whole family of tests
  B. H2 as a regression (no fixed cut-offs): z_resp = a*heat + b*dry + c*heat*dry,
     cell fixed effects, SEs clustered by year; c < 0 = synergy
  C. Risk-based amplification (probability of a severe loss, GPP/NDVI z <= -1):
     relative risks, RERI (relative excess risk due to interaction; > 0 = synergy on the
     additive risk scale) and the multiplicative interaction ratio, year-block bootstrap
  D. Sensitivity runs of H1/H2: thresholds 1.28 SD, SPEI-6, soil-moisture drought,
     1-month lagged response, pure land-cover cells, early vs late period
  E. Recovery (H3) with significance: Cox proportional-hazards model of time to recovery,
     adjusted for drought severity and duration, SEs clustered by event start year;
     stricter compound rule (>= 50% of drought months hot)

Usage:
    CHD_REGION=australia python scripts/07_significance_extensions.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats as sst

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd.stats import (bootstrap_category_contrasts, panel_fixed_effects_ols, benjamini_hochberg,
                       _year_weights, _per_year_sums, _ci, bootstrap_p_value)

CATS = ("normal", "hot_only", "dry_only", "compound")
RESP = (("gpp_z", "GPP"), ("ndvi_z", "NDVI"))
OUT = cfg.RESULTS


def classify(heat_z, dry_index, hot=1.0, dry=-1.0):
    """2x2 category from a heat z-score and a dryness index (lower = drier)."""
    heat_z = np.asarray(heat_z, float)
    dry_index = np.asarray(dry_index, float)
    out = np.full(len(heat_z), "nan", dtype=object)
    ok = ~np.isnan(heat_z) & ~np.isnan(dry_index)
    h, d = heat_z >= hot, dry_index <= dry
    out[ok & ~h & ~d] = "normal"
    out[ok & h & ~d] = "hot_only"
    out[ok & ~h & d] = "dry_only"
    out[ok & h & d] = "compound"
    return out


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_long_table_with_extras() -> pd.DataFrame:
    """Long table from 04_impacts plus lag-1 responses and SPEI-6 (from the cube / raw cache)."""
    df = pd.read_pickle(cfg.DATA_PROCESSED / "long_table.pkl")
    ds = xr.open_dataset(cfg.CUBE_PATH)
    times = pd.DatetimeIndex(ds["time"].values)
    lats, lons = ds["lat"].values, ds["lon"].values
    ti = times.get_indexer(pd.DatetimeIndex(df["time"]))
    li = pd.Index(np.round(lats, 4)).get_indexer(np.round(df["lat"].values, 4))
    lo = pd.Index(np.round(lons, 4)).get_indexer(np.round(df["lon"].values, 4))
    assert (ti >= 0).all() and (li >= 0).all() and (lo >= 0).all()

    for v in ("gpp_z", "ndvi_z"):
        arr = ds[v].transpose("time", "lat", "lon").values
        lag = np.full_like(arr, np.nan)
        lag[:-1] = arr[1:]                      # response in the FOLLOWING month
        df[f"{v}_lag1"] = lag[ti, li, lo]

    # SPEI-6 from the raw cache (already standardised by SPEIbase)
    years = range(cfg.STUDY_START, cfg.STUDY_END + 1)
    spei6 = np.concatenate([np.load(cfg.DATA_RAW / f"spei_{y}.npz")["spei_06"] for y in years], axis=0)
    df["spei06"] = spei6[ti, li, lo]

    # land-cover purity of the dominant class (for the "pure cells" sensitivity run)
    frac_cols = [c for c in ds.data_vars if c.startswith("frac_")]
    fr = np.nan_to_num(np.stack([ds[c].values for c in frac_cols]))
    df["lc_purity"] = fr.max(axis=0)[li, lo]
    ds.close()
    return df


# ---------------------------------------------------------------------------
# A2 / A3: year-level paired tests and the naive cell-month test
# ---------------------------------------------------------------------------
def yearly_category_means(df, resp, cat_col="category"):
    t = df.groupby(["year", cat_col], observed=True)[resp].mean().unstack(cat_col)
    return t.reindex(columns=list(CATS))


def year_level_tests(df, resp, cat_col="category", label=""):
    ym = yearly_category_means(df, resp, cat_col)
    rows = []
    pairs = [("compound", "dry_only"), ("compound", "hot_only"), ("compound", "normal"),
             ("dry_only", "normal"), ("hot_only", "normal")]
    for a, b in pairs:
        d = (ym[a] - ym[b]).dropna()
        t = sst.ttest_1samp(d, 0.0)
        w = sst.wilcoxon(d) if len(d) >= 6 else None
        rows.append({"spec": label, "response": resp, "test": f"{a} - {b}", "n_years": len(d),
                     "mean_diff": d.mean(), "t_stat": t.statistic, "p_paired_t": t.pvalue,
                     "p_wilcoxon": w.pvalue if w is not None else np.nan,
                     "years_negative": int((d < 0).sum())})
    ai = ((ym["compound"] - ym["normal"]) - (ym["hot_only"] - ym["normal"])
          - (ym["dry_only"] - ym["normal"])).dropna()
    t = sst.ttest_1samp(ai, 0.0)
    w = sst.wilcoxon(ai)
    rows.append({"spec": label, "response": resp, "test": "amplification index (yearly)",
                 "n_years": len(ai), "mean_diff": ai.mean(), "t_stat": t.statistic,
                 "p_paired_t": t.pvalue, "p_wilcoxon": w.pvalue, "years_negative": int((ai < 0).sum())})
    return pd.DataFrame(rows), ym


def naive_tests(df, resp):
    rows = []
    for a, b in [("compound", "dry_only"), ("compound", "hot_only")]:
        xa = df.loc[df["category"] == a, resp].dropna()
        xb = df.loc[df["category"] == b, resp].dropna()
        t = sst.ttest_ind(xa, xb, equal_var=False)
        rows.append({"response": resp, "test": f"{a} - {b}", "n_a": len(xa), "n_b": len(xb),
                     "mean_diff": xa.mean() - xb.mean(), "t_stat": t.statistic,
                     "p_naive_welch": t.pvalue,
                     "log10_p": (np.log10(t.pvalue) if t.pvalue > 0 else -np.inf)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# B: H2 regression with interaction
# ---------------------------------------------------------------------------
def h2_regressions(df):
    rows = []
    d = df.copy()
    d["heat"] = d["tmax_z"]
    d["dry"] = -d["spei03"]                       # positive = drier
    d["dry_spi"] = -d["spi03"] if "spi03" in d else np.nan
    d["sm_dry"] = -d["sm_z"]                      # positive = drier soil
    d["heat_x_dry"] = d["heat"] * d["dry"]
    d["heat_x_dry_spi"] = d["heat"] * d["dry_spi"]
    d["heat2"] = d["heat"] ** 2
    d["dry2"] = d["dry"] ** 2
    d["vpd_x_smdry"] = d["vpd_z"] * d["sm_dry"]
    specs = [
        ("SPEI-3", ["heat", "dry", "heat_x_dry"], "heat_x_dry"),
        ("SPEI-3 + quadratic terms", ["heat", "dry", "heat_x_dry", "heat2", "dry2"], "heat_x_dry"),
        ("SPI-3", ["heat", "dry_spi", "heat_x_dry_spi"], "heat_x_dry_spi"),
        ("Soil moisture x VPD", ["vpd_z", "sm_dry", "vpd_x_smdry"], "vpd_x_smdry"),
    ]
    for resp, rlabel in RESP:
        for name, xs, inter in specs:
            res = panel_fixed_effects_ols(d, resp, xs)
            ci = res.conf_int()
            for term in xs:
                rows.append({"response": rlabel, "spec": name, "term": term,
                             "coef": res.params[term], "se": res.bse[term],
                             "ci_low": ci.loc[term, 0], "ci_high": ci.loc[term, 1],
                             "p_value": res.pvalues[term], "is_interaction": term == inter,
                             "n_obs": int(res.nobs)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# C: risk-based amplification (RERI)
# ---------------------------------------------------------------------------
def risk_amplification(df, resp, cat_col="category", thresh=-1.0,
                       n_boot=cfg.BOOTSTRAP_N, seed=cfg.BOOTSTRAP_SEED):
    d = df[[resp, "year", cat_col]].dropna()
    years = np.unique(d["year"])
    w = _year_weights(len(years), n_boot, seed)
    p_pt, p_bt = {}, {}
    for c in CATS:
        g = d[d[cat_col] == c]
        s, n = _per_year_sums((g[resp] <= thresh).astype(float).values, g["year"].values, years)
        p_pt[c] = s.sum() / n.sum()
        with np.errstate(invalid="ignore", divide="ignore"):
            p_bt[c] = (w @ s) / (w @ n)

    def metrics(p):
        rr_h, rr_d, rr_c = p["hot_only"] / p["normal"], p["dry_only"] / p["normal"], p["compound"] / p["normal"]
        return {"p_normal": p["normal"], "p_hot_only": p["hot_only"], "p_dry_only": p["dry_only"],
                "p_compound": p["compound"], "rr_hot": rr_h, "rr_dry": rr_d, "rr_compound": rr_c,
                "risk_diff_ai": (p["compound"] - p["normal"]) - (p["hot_only"] - p["normal"])
                - (p["dry_only"] - p["normal"]),
                "reri": rr_c - rr_h - rr_d + 1.0,
                "log_mult_interaction": np.log(rr_c / (rr_h * rr_d))}

    pt, bt = metrics(p_pt), metrics(p_bt)
    rows = []
    for k in pt:
        lo, hi = _ci(np.asarray(bt[k]))
        p = bootstrap_p_value(np.asarray(bt[k])) if k in ("risk_diff_ai", "reri", "log_mult_interaction") else np.nan
        rows.append({"response": resp, "category_col": cat_col, "metric": k, "estimate": float(pt[k]),
                     "ci_low": lo, "ci_high": hi, "p_value": p})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# D: sensitivity runs
# ---------------------------------------------------------------------------
def sensitivity(df):
    mid_year = (cfg.STUDY_START + cfg.STUDY_END) // 2       # 2011
    runs = [
        ("Baseline (Tmax z>=1, SPEI-3<=-1)", df, classify(df["tmax_z"], df["spei03"]), "gpp_z", "ndvi_z"),
        ("Stricter thresholds (1.28 SD)", df, classify(df["tmax_z"], df["spei03"], 1.28, -1.28), "gpp_z", "ndvi_z"),
        ("Drought = SPI-3 (rain only)", df, classify(df["tmax_z"], df["spi03"]), "gpp_z", "ndvi_z"),
        ("Drought = SPEI-6", df, classify(df["tmax_z"], df["spei06"]), "gpp_z", "ndvi_z"),
        ("Drought = root-zone soil moisture z<=-1", df, classify(df["tmax_z"], df["sm_z"]), "gpp_z", "ndvi_z"),
        ("Response 1 month later", df, classify(df["tmax_z"], df["spei03"]), "gpp_z_lag1", "ndvi_z_lag1"),
    ]
    pure = df[(df["lc_purity"] >= 0.7)]
    runs.append(("Pure land-cover cells (>=70%)", pure, classify(pure["tmax_z"], pure["spei03"]),
                 "gpp_z", "ndvi_z"))
    early = df[df["year"] <= mid_year]
    late = df[df["year"] > mid_year]
    runs.append((f"Early period {cfg.STUDY_START}-{mid_year}", early,
                 classify(early["tmax_z"], early["spei03"]), "gpp_z", "ndvi_z"))
    runs.append((f"Late period {mid_year + 1}-{cfg.STUDY_END}", late,
                 classify(late["tmax_z"], late["spei03"]), "gpp_z", "ndvi_z"))
    rows = []
    for name, data, cats, g, n in runs:
        for col, rlabel in ((g, "GPP"), (n, "NDVI")):
            res = bootstrap_category_contrasts(data[col].values, data["year"].values, cats)
            row = {"spec": name, "response": rlabel, "n_compound": res["n_compound"],
                   "share_compound_pct": 100.0 * res["n_compound"] / sum(res[f"n_{c}"] for c in CATS)}
            for c in CATS:
                row[f"mean_{c}"] = res[f"mean_{c}"]["estimate"]
            for k in ("d_compound", "compound_minus_dry", "compound_minus_hot", "amplification_index"):
                row[k] = res[k]["estimate"]
                row[f"{k}_ci_low"] = res[k]["ci_low"]
                row[f"{k}_ci_high"] = res[k]["ci_high"]
                row[f"{k}_p"] = res[k]["p_value"]
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# E: recovery with Cox PH
# ---------------------------------------------------------------------------
def add_hot_fraction(events):
    """Fraction of a drought event's months that were hot (tmax_z >= hot_z), from the cube."""
    ds = xr.open_dataset(cfg.CUBE_PATH)
    tz = ds["tmax_z"].transpose("time", "lat", "lon").values
    times = pd.DatetimeIndex(ds["time"].values)
    li = pd.Index(np.round(ds["lat"].values, 4)).get_indexer(np.round(events["lat"].values, 4))
    lo = pd.Index(np.round(ds["lon"].values, 4)).get_indexer(np.round(events["lon"].values, 4))
    si = times.get_indexer(pd.DatetimeIndex(events["start_date"]))
    ei = times.get_indexer(pd.DatetimeIndex(events["end_date"]))
    frac = np.full(len(events), np.nan)
    for k in range(len(events)):
        seg = tz[si[k]:ei[k] + 1, li[k], lo[k]]
        frac[k] = np.mean(seg >= cfg.THRESH.hot_z) if seg.size else np.nan
    ds.close()
    events = events.copy()
    events["hot_frac"] = frac
    return events


def cox_recovery(events):
    from lifelines import CoxPHFitter
    from lifelines import KaplanMeierFitter
    ev = events[events["has_impact"]].copy()
    ev["start_year"] = pd.DatetimeIndex(ev["start_date"]).year
    ev["recovered"] = (~ev["censored"].astype(bool)).astype(int)
    rows, km_rows = [], []

    def fit(data, label, covars):
        d = data[["recovery_time_months", "recovered", "start_year"] + covars].dropna()
        d = d[d["recovery_time_months"] > 0]
        cph = CoxPHFitter()
        cph.fit(d, duration_col="recovery_time_months", event_col="recovered",
                cluster_col="start_year", robust=True)
        s = cph.summary
        for term in covars:
            rows.append({"model": label, "term": term, "hazard_ratio": float(s.loc[term, "exp(coef)"]),
                         "hr_ci_low": float(s.loc[term, "exp(coef) lower 95%"]),
                         "hr_ci_high": float(s.loc[term, "exp(coef) upper 95%"]),
                         "p_value": float(s.loc[term, "p"]), "n_events": len(d)})

    # (1) drought events: compound vs drought-only, adjusted for severity and duration
    dr = ev[ev["event_type"].isin(["compound", "drought_only"])].copy()
    dr["compound"] = (dr["event_type"] == "compound").astype(int)
    fit(dr, "drought events: compound vs drought-only (unadjusted)", ["compound"])
    fit(dr, "drought events: compound vs drought-only (adj. severity, duration)",
        ["compound", "severity", "duration_months"])
    # (2) stricter compound rule: >= 50% of the drought months hot (vs drought-only)
    strict = dr[(dr["event_type"] == "drought_only") | (dr["hot_frac"] >= 0.5)].copy()
    fit(strict, "strict compound (>=50% hot months) vs drought-only (adj.)",
        ["compound", "severity", "duration_months"])
    # (3) all three types: heat-only vs drought-only reference
    al = ev.copy()
    al["compound"] = (al["event_type"] == "compound").astype(int)
    al["heat_only"] = (al["event_type"] == "heat_only").astype(int)
    fit(al, "all impactful events (reference: drought-only)", ["compound", "heat_only"])

    for et, g in [("compound (strict)", strict[strict["compound"] == 1])] + \
                 [(t, ev[ev["event_type"] == t]) for t in ("compound", "drought_only", "heat_only")]:
        km = KaplanMeierFitter().fit(g["recovery_time_months"], g["recovered"])
        km_rows.append({"event_type": et, "n": len(g), "km_median_rt": float(km.median_survival_time_),
                        "p_recovered_by_3m": float(1 - km.survival_function_at_times(3).iloc[0]),
                        "p_recovered_by_12m": float(1 - km.survival_function_at_times(12).iloc[0])})
    return pd.DataFrame(rows), pd.DataFrame(km_rows)


# ---------------------------------------------------------------------------
def main():
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 40)
    print(f"Region: {cfg.REGION}. Loading long table + extras...")
    df = load_long_table_with_extras()
    print(f"{len(df)} active cell-months, years {df['year'].min()}-{df['year'].max()}")

    # ---- A2/A3 ----
    yl, naive = [], []
    for resp, _ in RESP:
        t, ym = year_level_tests(df, resp, "category", "SPEI-3")
        yl.append(t)
        ym.to_csv(OUT / f"yearly_category_means_{resp}.csv")
        if "category_spi" in df:
            t2, _ = year_level_tests(df[df["category_spi"] != "nan"], resp, "category_spi", "SPI-3")
            yl.append(t2)
        naive.append(naive_tests(df, resp))
    yl = pd.concat(yl, ignore_index=True)
    yl.to_csv(OUT / "year_level_tests.csv", index=False)
    naive = pd.concat(naive, ignore_index=True)
    naive.to_csv(OUT / "naive_cellmonth_tests.csv", index=False)
    print("\nYear-level paired tests:\n", yl.round(4).to_string())
    print("\nNaive Welch tests (pseudo-replication demo):\n", naive.to_string())

    # ---- B ----
    print("\nFitting H2 panel regressions (cell FE, year-clustered SEs)...")
    reg = h2_regressions(df)
    reg.to_csv(OUT / "h2_regression.csv", index=False)
    print(reg.round(4).to_string())

    # ---- C ----
    risk = pd.concat([risk_amplification(df, r, c) for r, _ in RESP
                      for c in ("category", "category_spi") if c in df], ignore_index=True)
    risk.to_csv(OUT / "risk_amplification.csv", index=False)
    print("\nRisk-based amplification:\n", risk.round(4).to_string())

    # ---- D ----
    print("\nSensitivity runs...")
    sens = sensitivity(df)
    sens.to_csv(OUT / "sensitivity_h1_h2.csv", index=False)
    print(sens[["spec", "response", "n_compound", "compound_minus_dry", "compound_minus_dry_p",
                "amplification_index", "amplification_index_ci_low", "amplification_index_ci_high",
                "amplification_index_p"]].round(4).to_string())

    # ---- E ----
    print("\nRecovery: Cox PH models...")
    events = pd.read_csv(cfg.EVENTS_PATH, parse_dates=["start_date", "end_date"])
    events = add_hot_fraction(events)
    events.to_csv(cfg.DATA_PROCESSED / "events_with_hotfrac.csv", index=False)
    cox, km = cox_recovery(events)
    cox.to_csv(OUT / "recovery_cox.csv", index=False)
    km.to_csv(OUT / "recovery_km_strict.csv", index=False)
    print(cox.round(4).to_string())
    print(km.round(3).to_string())

    # ---- A1 + A4: one table of the key p-values, with BH-FDR q-values ----
    rows = []
    for resp, rlabel in RESP:
        for f, scope in [(f"contrasts_{resp}_overall.csv", "overall"),
                         (f"contrasts_{resp}_by_landcover.csv", "landcover"),
                         (f"contrasts_{resp}_by_region.csv", "region"),
                         (f"contrasts_{resp}_by_season.csv", "season")]:
            c = pd.read_csv(OUT / f)
            strat_col = {"landcover": "dominant_landcover", "region": "region", "season": "season"}.get(scope)
            for _, r in c.iterrows():
                for k in ("d_hot", "d_dry", "d_compound", "compound_minus_dry", "compound_minus_hot",
                          "amplification_index"):
                    rows.append({"response": rlabel, "scope": scope,
                                 "stratum": r[strat_col] if strat_col else "all",
                                 "contrast": k, "estimate": r[k], "ci_low": r[f"{k}_ci_low"],
                                 "ci_high": r[f"{k}_ci_high"], "p_boot": r[f"{k}_p"],
                                 "min_category_n": r["min_category_n"]})
    pv = pd.DataFrame(rows)
    pv["q_bh"] = benjamini_hochberg(pv["p_boot"].values)
    pv["sig_p05"] = pv["p_boot"] < 0.05
    pv["sig_q05"] = pv["q_bh"] < 0.05
    pv.to_csv(OUT / "pvalues_all_contrasts.csv", index=False)
    n_tests = len(pv)
    print(f"\n{n_tests} bootstrap tests; significant at p<0.05: {int(pv['sig_p05'].sum())}, "
          f"after BH-FDR (q<0.05): {int(pv['sig_q05'].sum())}")
    print(pv[pv["scope"] == "overall"].round(4).to_string())
    print(f"\nDone. Tables in {OUT}.")


if __name__ == "__main__":
    main()
