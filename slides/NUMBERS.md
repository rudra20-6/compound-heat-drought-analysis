# Where every number on the slides comes from

All paths are relative to `midSub/`. Rerun `scripts/02`–`06` to regenerate them.
`python slides/extract_numbers.py` prints all of these in one go.
CIs are 95% year-block bootstrap intervals (1,000 replicates, 2001–2022) unless stated otherwise.
Numbers are as of the GPP leap-year fix (see `HANDOFF.md`, section 4, item 10).

| Slide | Claim | Source |
|---|---|---|
| Study area | 4,481 India cells; 4,160 with an active month | printed by `scripts/02_build_cube.py` |
| Data | NDVI QA mask removes 14.6% of active cell-months | printed by `scripts/02_build_cube.py` |
| QC | 2002 driest of 34 yrs (SPEI-3, Sep), 2009 5th, 2015 10th, 2014 11th; MAM 2010 hottest, 2022 3rd | printed by `scripts/02_build_cube.py`; `figures/qc_jjas_anomalies.png` |
| H5 | slope +0.033 pp/yr [−0.090, 0.165], p = 0.563; 2009 20.9%, 2006 18.4%, 2002 13.4% | `results/compound_area_trend_stats.csv`, `results/compound_area_trend.csv` |
| H1 | category means and CIs | `results/composite_gpp_z_overall.csv`, `results/composite_ndvi_z_overall.csv` |
| H1 | compound − dry, compound − hot, category − normal | `results/contrasts_{gpp,ndvi}_z_overall.csv` |
| H2 | amplification index, SPEI-3 and SPI-3 | `results/robustness_spei_vs_spi.csv` |
| H4 | AI by land cover / region; compound GPP means: shrubland −0.75, cropland −0.61 | `results/contrasts_{gpp,ndvi}_z_by_{landcover,region}.csv` |
| H4 | Peninsular − North differences | `results/peninsular_vs_north_test.csv` |
| Obs I | soil moisture / VPD z by category | `results/mechanism_check.csv` |
| Obs I | tree-cover GPP d_hot +0.146 [+0.064, +0.227]; compound − dry +0.184 [+0.025, +0.332]; NDVI compound − dry −0.249 | `results/contrasts_{gpp,ndvi}_z_by_landcover.csv` |
| H3 | KM medians, % recovered by 3 / 12 months, event counts | `results/recovery_km.csv` |
| H3 | log-rank p = 0.0018 (compound vs drought-only) | `results/recovery_logrank.csv` |
| H3 | severity-matched medians: compound vs drought 4/3 (T1), 4/3 (T2), 3/2 (T3); log-rank p per tercile | `results/recovery_severity_matched.csv` |
| Obs II | event duration 3 vs 2 months; SPEI deficit 4.87 vs 3.18 | `results/event_type_summary.csv` |
| Obs II | NDVI epoch trough −0.86 vs −0.61; back above −0.1 at +9 vs +7 months | `results/recovery_composite_ndvi_z.csv` (impactful events) |
| 2009 | 19.8% compound / 27.5% hot-only / 17.9% dry-only (Jun–Sep 2009, active cell-months) | `results/case_2009_jjas_category_shares.csv` |
| 2009 | India-mean SPEI-3 −1.59 (Feb 2009); active GPP z −0.44…+0.26 (JJAS), −0.63…−0.71 (Feb–Apr 2009), −1.18 (Mar 2010) | `results/case_2009_india_monthly.csv` |

`slides/midsub_v2.pdf` (alternative structure: no H5; H3/H4 as further work) uses the same sources.
Its extra numbers: 60% of India cells are cropland-dominant (WorldCover, cube.nc); North 39,784 and Peninsular 22,481
compound grid-months (`results/contrasts_gpp_z_by_region.csv`); additivity bars from `results/contrasts_{gpp,ndvi}_z_overall.csv`
(figure made by `python slides/make_v2_figures.py`).

`slides/midsub_v3.pdf` (concise) and `slides/midsub_v4.pdf` (concise + team feedback, numeric citations) use the
same sources. v4's response-surface slide reads `results/response_surface_gpp.csv`: row averages about +0.48
(wettest) and −0.35 (driest); hottest + driest bin −0.92, n = 670 (figure made by `python slides/make_v4_figures.py`).

Citations: every reference DOI was checked against Crossref / DataCite in October 2026.
