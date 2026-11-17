"""Print every number used on the slides, straight from results/*.csv.
Run from midSub/:  python slides/extract_numbers.py"""
from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parent.parent / "results"


def ci(row, k, nd=2):
    return f"{row[k]:+.{nd}f} [{row[k + '_ci_low']:+.{nd}f}, {row[k + '_ci_high']:+.{nd}f}]{' *' if row[k + '_sig'] else ''}"


print("== Category means (95% CI) ==")
for v in ("gpp_z", "ndvi_z"):
    c = pd.read_csv(R / f"composite_{v}_overall.csv").set_index("category")
    print(v, {k: f"{c.loc[k, 'mean']:+.2f} [{c.loc[k, 'ci_low']:+.2f},{c.loc[k, 'ci_high']:+.2f}] n={c.loc[k, 'n']}"
              for k in ("compound", "dry_only", "hot_only", "normal")})

print("\n== Contrasts overall (* = CI excludes 0) ==")
for v in ("gpp_z", "ndvi_z"):
    d = pd.read_csv(R / f"contrasts_{v}_overall.csv").iloc[0]
    print(v, " | ".join(f"{k}: {ci(d, k)}" for k in
                        ("d_hot", "d_dry", "d_compound", "compound_minus_dry", "compound_minus_hot", "amplification_index")))

print("\n== By land cover / region ==")
for v in ("gpp_z", "ndvi_z"):
    for g, col in (("landcover", "dominant_landcover"), ("region", "region")):
        t = pd.read_csv(R / f"contrasts_{v}_by_{g}.csv")
        for _, r in t.iterrows():
            print(f"{v} {r[col]:11s} cmp={r.mean_compound:+.2f} dry={r.mean_dry_only:+.2f} hot={r.mean_hot_only:+.2f} "
                  f"norm={r.mean_normal:+.2f} d_hot={ci(r, 'd_hot')} c-d={ci(r, 'compound_minus_dry')} AI={ci(r, 'amplification_index')}")

print("\n== SPEI vs SPI ==")
rob = pd.read_csv(R / "robustness_spei_vs_spi.csv")
for _, r in rob.iterrows():
    print(f"{r.response} {r.drought_index}: c-d={ci(r, 'compound_minus_dry')} AI={ci(r, 'amplification_index')}")

print("\n== Peninsular - North ==")
print(pd.read_csv(R / "peninsular_vs_north_test.csv").round(3).to_string(index=False))
print("\n== Mechanism ==")
print(pd.read_csv(R / "mechanism_check.csv").round(2).to_string(index=False))
print("\n== Events ==")
print(pd.read_csv(R / "event_type_summary.csv").round(2).to_string(index=False))
print("\n== KM ==")
print(pd.read_csv(R / "recovery_km.csv").round(3).to_string(index=False))
print(pd.read_csv(R / "recovery_logrank.csv").round(4).to_string(index=False))
print(pd.read_csv(R / "recovery_severity_matched.csv").round(3).to_string(index=False))

print("\n== Epoch composites (impactful events) ==")
for v in ("gpp_z", "ndvi_z"):
    d = pd.read_csv(R / f"recovery_composite_{v}.csv")
    for et, g in d.groupby("event_type"):
        g = g.set_index("offset_months")
        tr = g["mean"].idxmin()
        back = g.loc[tr:][g.loc[tr:, "mean"] > -0.1].index.min()
        print(f"{v} {et:13s} trough {g['mean'].min():+.2f} at +{tr}m, back above -0.1 at +{back}m")

print("\n== Trend ==")
print(pd.read_csv(R / "compound_area_trend_stats.csv").round(4).to_string(index=False))
print(pd.read_csv(R / "compound_area_trend.csv").sort_values("pct_area", ascending=False).head(3).round(1).to_string(index=False))

print("\n== 2009 ==")
print(pd.read_csv(R / "case_2009_jjas_category_shares.csv").round(1).to_string(index=False))
m = pd.read_csv(R / "case_2009_india_monthly.csv")
print(m.round(2).to_string(index=False))
