"""Every number shown in the final deck/report, read straight from results/*.csv.

Nothing is typed by hand: slides call these helpers, so a re-run of the
pipeline updates the deck. Formatting uses a true minus sign (−).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]          # midSub/
RES = {"India": ROOT / "results", "Australia": ROOT / "results" / "australia"}
FIGS = {"India": ROOT / "figures", "Australia": ROOT / "figures" / "australia"}
CMP_RES = ROOT / "results" / "comparison"
CMP_FIG = ROOT / "figures" / "comparison"
CATS = ("normal", "hot_only", "dry_only", "compound")


def csv(country, name):
    return pd.read_csv(RES[country] / name)


def m(x, d=2, sign=True):
    """Number with a real minus sign; '+' for positives when sign=True."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    if round(x, d) == 0:
        x = 0.0
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    if round(x, d) == 0 and sign:
        s = s.replace("+", "")
    return s.replace("-", "−")


def ci(lo, hi, d=2):
    return f"[{m(lo, d)}, {m(hi, d)}]"


def pv(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "–"
    if p < 0.001:
        return "p < 0.001"
    s = f"{p:.2f}" if p >= 0.095 else f"{p:.2g}"
    if "e" in s:
        s = f"{p:.4f}"
    if s in ("1", "1.0"):
        s = "1.00"
    return f"p = {s}"


def pshort(p):
    return pv(p).replace("p = ", "").replace("p < ", "< ")


def n0(x):
    return f"{int(round(x)):,}"


def overall(country, resp):
    return csv(country, f"contrasts_{resp}_overall.csv").iloc[0]


def composite(country, resp):
    return csv(country, f"composite_{resp}_overall.csv").set_index("category")


def contrast_str(country, resp, k, with_p=True):
    o = overall(country, resp)
    s = f"{m(o[k])} {ci(o[k + '_ci_low'], o[k + '_ci_high'])}"
    return s + (f", {pv(o[k + '_p'])}" if with_p else "")


def robustness(country, resp, idx):
    r = csv(country, "robustness_spei_vs_spi.csv")
    return r[(r["response"] == resp) & (r["drought_index"] == idx)].iloc[0]


def counts(country):
    c = csv(country, "category_counts_active.csv")
    c.columns = ["category", "n"]
    return c.set_index("category")["n"].reindex(list(CATS)).fillna(0)


def study(country):
    return csv(country, "study_area_counts.csv").iloc[0]


def mech(country):
    return csv(country, "mechanism_check.csv").set_index("category")


def trend(country):
    return csv(country, "compound_area_trend_stats.csv").iloc[0]


def top_years(country, k=3):
    t = csv(country, "compound_area_trend.csv").sort_values("pct_area", ascending=False).head(k)
    return [(int(r.year), r.pct_area) for r in t.itertuples()]


def km(country):
    return csv(country, "recovery_km.csv").set_index("event_type")


def logrank(country):
    return csv(country, "recovery_logrank.csv")


def cox(country, model_prefix, term="compound"):
    c = csv(country, "recovery_cox.csv")
    return c[c["model"].str.startswith(model_prefix) & (c["term"] == term)].iloc[0]


def regression(country, resp_label, spec, term=None):
    r = csv(country, "h2_regression.csv")
    r = r[(r["response"] == resp_label) & (r["spec"] == spec)]
    return r[r["is_interaction"]].iloc[0] if term is None else r[r["term"] == term].iloc[0]


def yearly(country, resp, spec, test):
    y = csv(country, "year_level_tests.csv")
    return y[(y["response"] == resp) & (y["spec"] == spec) & (y["test"] == test)].iloc[0]


def naive(country, resp, test):
    n = csv(country, "naive_cellmonth_tests.csv")
    return n[(n["response"] == resp) & (n["test"] == test)].iloc[0]


def risk(country, resp, col, metric):
    r = csv(country, "risk_amplification.csv")
    return r[(r["response"] == resp) & (r["category_col"] == col) & (r["metric"] == metric)].iloc[0]


def by(country, resp, kind):
    return csv(country, f"contrasts_{resp}_by_{kind}.csv")


def subregion_test(country):
    return csv(country, "subregion_difference_test.csv")


def pvalues(country):
    return csv(country, "pvalues_all_contrasts.csv")


def qc(country):
    return csv(country, "qc_known_events.csv")


def sens(country):
    return csv(country, "sensitivity_h1_h2.csv")


def case_shares(country, name):
    return csv(country, f"case_{name}_category_shares.csv").iloc[0]


def country_diff():
    return pd.read_csv(CMP_RES / "country_difference_tests.csv")


def cdiff(resp_label, idx, contrast):
    d = country_diff()
    return d[(d["response"] == resp_label) & (d["drought_index"] == idx) & (d["contrast"] == contrast)].iloc[0]


def reri_bench(country, resp, idx):
    """Observed RERI vs the RERI that exactly additive mean effects would give (threshold convexity)."""
    b = pd.read_csv(CMP_RES / "reri_vs_additive_expectation.csv")
    return b[(b["country"] == country) & (b["response"] == resp) & (b["drought_index"] == idx)].iloc[0]
