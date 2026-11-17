"""
Recovery analysis (plan section 3.D, hypothesis H3), India active-season cells:

  - Kaplan-Meier recovery curves per event type (censored events -- next
    event began, record ended, or 24-month horizon reached before recovery --
    are treated as censored, NOT as "never recovered")
  - log-rank tests between event types (descriptive: events are spatially
    and temporally correlated, so p-values are optimistic)
  - severity-matched comparison: compound vs drought-only within terciles of
    drought severity, since compound droughts are longer/more severe
  - superposed-epoch composites of GPP and NDVI z around event onset

Usage:
    python scripts/05_recovery.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chd import config as cfg
from chd import plotting as plot
from chd.recovery import (
    kaplan_meier_recovery, logrank_tests, severity_matched_recovery,
    superposed_epoch_composite,
)

COLORS = {"compound": "#3E9B5C", "drought_only": "#B23A48", "heat_only": "#E89A2E"}


def main():
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)
    print(f"Loading cube from {cfg.CUBE_PATH} and events from {cfg.EVENTS_PATH}")
    ds = xr.open_dataset(cfg.CUBE_PATH)
    events = pd.read_csv(cfg.EVENTS_PATH, parse_dates=["start_date", "end_date"])
    impactful = events[events["has_impact"]]
    print(f"Loaded {len(events)} events; {len(impactful)} with impact "
          f"(min GPP z <= {cfg.THRESH.impact_z} during event or the month after)")

    km = kaplan_meier_recovery(events)
    km.to_csv(cfg.RESULTS / "recovery_km.csv", index=False)
    print(f"\nKaplan-Meier recovery (impactful events):\n{km.round(3).to_string()}")

    lr = logrank_tests(events)
    lr.to_csv(cfg.RESULTS / "recovery_logrank.csv", index=False)
    print(f"\nLog-rank tests (descriptive -- events are not independent):\n{lr.round(4).to_string()}")

    sev = severity_matched_recovery(events)
    sev.to_csv(cfg.RESULTS / "recovery_severity_matched.csv", index=False)
    print(f"\nSeverity-matched (drought-severity terciles):\n{sev.round(3).to_string()}")

    # KM curves figure
    from lifelines import KaplanMeierFitter
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for et, color in COLORS.items():
        g = impactful[impactful["event_type"] == et]
        if len(g) == 0:
            continue
        kmf = KaplanMeierFitter().fit(g["recovery_time_months"], ~g["censored"].astype(bool),
                                      label=f"{et.replace('_', '-')} (n={len(g)})")
        cdf = 1 - kmf.survival_function_
        ci = 1 - kmf.confidence_interval_survival_function_
        ax.step(cdf.index, cdf.iloc[:, 0], where="post", color=color, label=kmf._label)
        ax.fill_between(ci.index, ci.iloc[:, 0], ci.iloc[:, 1], step="post", color=color, alpha=0.2)
    ax.set_xlim(0, cfg.THRESH.censor_months)
    ax.set_xlabel("Months after event end")
    ax.set_ylabel("Fraction recovered (Kaplan-Meier)")
    ax.set_title("Recovery after impactful events (GPP z >= -0.5 for 2 active months)", fontsize=10)
    ax.legend()
    fig.tight_layout()
    fig.savefig(cfg.FIGURES / "recovery_km.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    for response_var, label in [("gpp_z", "GPP z-score"), ("ndvi_z", "NDVI z-score")]:
        composite = superposed_epoch_composite(
            ds, impactful, response_var=response_var,
            event_types=("compound", "drought_only", "heat_only"),
            pre_months=6, post_months=18,
        )
        composite.to_csv(cfg.RESULTS / f"recovery_composite_{response_var}.csv", index=False)
        plot.plot_recovery_composite(
            composite, label,
            f"Superposed-epoch composite (impactful events): {label}",
            f"recovery_composite_{response_var}",
        )

    print(f"\nDone. Figures in {cfg.FIGURES}, tables in {cfg.RESULTS}.")


if __name__ == "__main__":
    main()
