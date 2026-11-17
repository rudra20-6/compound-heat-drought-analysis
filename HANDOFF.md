# HANDOFF — Compound Heat–Drought Stress over India (EVS project #19)

Notes for the next Claude session working on this project. Written Oct 2026; section 0 added Nov 17, 2026.
Teammate-facing docs are in `README.md`. This file covers state, environment, gotchas and open work.

## 0. FINAL PHASE (Nov 2026): read this first; it supersedes older sections where they conflict
- **New PC** (user `rudra`). Project root `C:\Users\rudra\OneDrive\Desktop\EST\EST\midSub`.
  venv `C:\Users\rudra\venvs\est-midsub` (Python 3.13, `requirements-lock.txt` + python-pptx, pymupdf, python-docx).
  EE project `est-proj-510822` (authenticated on this PC). **No TinyTeX here** (install was blocked); the
  report is a Claude Doc instead of LaTeX. PowerPoint/Word are installed; `slides/pptx_build/render_pptx.ps1`
  renders a .pptx to PDF/PNGs for checking.
- **Australia added.** `CHD_REGION=australia` (env var, default `india`) switches grid (112–154°E, 44–9°S),
  country mask (LSIB "Australia", 11,150 cells), sub-regions (tropical north vs temperate south at 23.44°S),
  seasons, QC years and case study (Sep–Dec 2019). Australia data/results live in `data/australia/`,
  `results/australia/`, `figures/australia/`; India keeps the original folders. India's
  Andaman & Nicobar cells are now labelled `islands` and excluded from the Peninsular-vs-North test.
- **Run order (per region):** scripts 02–07 (`07_significance_extensions.py` = year-level tests, naive-test demo,
  H2 regression, RERI, sensitivity runs, Cox recovery, BH-FDR table), then `08_compare_countries.py`
  (country-difference tests, mechanism checks, RERI-vs-additive benchmark, comparison figures), then
  `slides/make_final_figures.py`, then `slides/pptx_build/build_final_pptx.py`.
- **Bootstrap** now 10,000 replicates with two-sided percentile p-values (`stats.bootstrap_p_value`); every
  contrast CSV has `<name>_p`. Mid-sub CSVs/figures are frozen in `_midsub_snapshot/`.
- **Category colours changed** (old orange/red pair failed a colour-vision check): see `plotting.CATEGORY_COLORS`.
- **Deliverables:** deck `slides/final_themed.pptx` (+ `.pdf`; 58 slides, same Africa Viva theme; every number
  is read from CSVs via `final_numbers.py`, narrative in `final_text.py`). Report = Claude Doc
  https://claude.ai/artifact/KZgXWpbHrnCvZFo4kJdHmi (figures in `figures/report/`).
- **Headline results (final):** H1 supported in both countries. H2: no synergy — additive in India, significantly
  *less* than additive in Australia (AI +0.36, p < 0.001), robust to 9 sensitivity runs. RERI > 0 with SPI-3
  is **not** tail synergy: additive mean shifts across a threshold already give that RERI (benchmark in
  `results/comparison/reri_vs_additive_expectation.csv`). Only synergy: VPD × soil dryness for Australian NDVI.
  H3 **not** supported in either country once events are clustered by year (Cox; the mid-sub log-rank p = 0.002
  was pseudo-replication). H4: land cover/season matter. H5: no significant trend (India p = 0.56, Australia p = 0.10).
  India GPP compound − dry-only is p = 0.011 (pooled bootstrap) but p = 0.27 on yearly means — report as weaker.

## 1. Who / what
- **User:** Rudra Choudhary (IIIT Hyderabad), in a team of 5: Arnav Deshmukh, Ayush Brajesh Roy, Saksham Chitkara, Gracy Garg, Rudra Choudhary.
- **Course:** Environmental Science & Technology (EVS/EST). Assigned topic #19:
  "Compound Heat–Drought Stress: are ecosystems experiencing stronger combined impacts?"
  Suggested datasets: ERA5-Land, CHIRPS, SPEI, MODIS GPP/NDVI, ESA WorldCover.
- **Milestones:**
  - Lit review: done and submitted (`../LitReview-FinalSubmission.tex`).
  - Mid-eval: deliverable is **`slides/midsub_v4.pdf`** (latest, 28 slides) plus `notebooks/demo.ipynb`. Expects 50–60% of the work; see `instructions.md`.
  - Deck versions (all share the same numbers, see `slides/NUMBERS.md`). **Never edit an old version when asked for a new one; copy it to a new file.**
    - `midsub` (original, H1–H5 as results).
    - `_v2`: structure problem → hypotheses → methodology → preliminary H1/H2 → things left to do; no H5.
    - `_v3`: same as v2 with minimal text.
    - `_v4`: v3 plus team feedback.
      - Numbered citations.
      - GPP / carbon sink–source TikZ slide.
      - Problem statement split into topic and questions.
      - Workflow, then Step 1–4, with the v2 methods and results text.
      - Explained response surface (`figures/response_surface_gpp_explained.png` from `slides/make_v4_figures.py`).
      - "Further work" includes repeating the analysis for another (unchosen) country.
      - Footer short-author is "EVS Project #19" (the user didn't want "Deshmukh et al.").
  - Final presentation/report: next.
- **What the user wants:** correctness over speed, honest claims, and every number verified. They explicitly asked for double-checking and an honest novelty assessment. Do not overclaim.

## 2. Environment (this machine, Windows 11)
- **Project root:** `C:\Users\choud\OneDrive\Desktop\NewCollegeDocs\4-1\EST\midSub`.
- **venv:** `C:\Users\choud\venvs\est-midsub` (Python 3.13.1), kept outside OneDrive on purpose. Always run with `/c/Users/choud/venvs/est-midsub/Scripts/python.exe`.
  - Do **not** use the system `Python311`: its numpy/pandas are incompatible.
  - The pinned numpy 2.5.3 and scipy 1.18.1 need Python ≥ 3.12.
- **Jupyter kernel:** registered as `est-midsub` ("Python (est-midsub)"), and the notebook metadata points to it.
  - `EST\.vscode\settings.json` sets the default interpreter.
- **Earth Engine:**
  - Project ID: `est-proj-510822`. Set it with `export EE_PROJECT=est-proj-510822`.
  - Credentials live in `~/.config/earthengine/credentials` (already authenticated).
- **LaTeX:**
  - TinyTeX. Bare `tlmgr` is not on PATH; use `/c/Users/choud/AppData/Roaming/TinyTeX/bin/windows/tlmgr.bat`.
  - beamer, pgf/tikz, multirow and natbib are installed.
  - Compile from `slides/`: `pdflatex midsub_v4 && bibtex midsub_v4 && pdflatex midsub_v4 && pdflatex midsub_v4` (same pattern for the other versions).
  - Gotcha: `\usepackage[numbers]{natbib}` fails here with "grfext.sty not found". v4 loads natbib with no options and then calls `\setcitestyle{numbers,square,comma,sort&compress}`.
- **Study-area map** (`plotting.plot_study_area`):
  - Uses tab10 colours (cropland red; the user wants these).
  - Cell-edge extent, a legend of only the classes present (with counts), and white = mixed.
  - Boundary note "USDOS LSIB, not authoritative": LSIB excludes PoK/Aksai Chin.
  - The Peninsular mask (lat ≤ 22°N) also includes 9 Andaman & Nicobar cells; exclude them in the final phase.
- **Rendering slides to PNG for checking:** PyMuPDF is only in the system Python (`/c/Python313/python.exe -c "import fitz"`). Write output to a Windows path, not `/tmp`.
- **Shell gotcha:**
  - Python heredocs / `sed` in Git Bash have corrupted backslashes before (`\n` became a newline, `\citep` became garbage).
  - For LaTeX or anything containing `\`, use the Edit/Write tools.

## 3. Pipeline (all code in `chd/`, scripts in `scripts/`)
| Step | Script | Notes |
|---|---|---|
| 00 | `00_check_gee.py` | checks assets, picks GPP source (MOD17 v006) → `data/processed/gpp_source.txt` |
| 01 | `01_fetch.py` | GEE → `data/raw/*.npz` (resumable). ~1 h for everything. Already done; 150 files cached |
| 02 | `02_build_cube.py` | → `data/processed/cube.nc` (1.4 GB) + QC prints/figures |
| 03 | `03_indices_events.py` | events → `data/processed/events.csv`; frequency maps; 1991–2024 trend |
| 04 | `04_impacts.py` | composites, joint-bootstrap contrasts, AI, land cover/region, SPI robustness, Peninsular−North test, response surfaces, mechanism |
| 05 | `05_recovery.py` | Kaplan–Meier, log-rank, severity-matched, epoch composites |
| 06 | `06_case_studies.py` | 2009 maps/trajectory → `results/case_2009_*.csv` |

- **Tests:** `python -m pytest tests -q` (68 tests, all passing).
- **Number extraction:**
  - `python slides/extract_numbers.py` prints every slide number from `results/`.
  - `slides/NUMBERS.md` maps each slide claim to its source file.
- **Demo notebook:** generated by `notebooks/build_demo_notebook.py`. Edit the generator, not the `.ipynb`.

### Key design decisions (all in `chd/config.py`)
- **Grid:** 0.25° (68–98°E, 6–37.5°N), 120×126 cells.
- **India cells:** ≥50% inside USDOS LSIB_SIMPLE India, which gives 4,481 cells. All statistics use these only.
- **Active season:** inside India, ≥50% vegetated (WorldCover), and climatological GPP that month ≥30% of the cell's peak month.
- **Hot:** monthly-mean daily Tmax z ≥ 1, against a 1991–2020 calendar-month baseline. Not detrended.
- **Dry:** SPEI-3 ≤ −1 (CSIC SPEIbase v2.11). SPI-3 from CHIRPS is the robustness alternative.
- **Responses:** GPP z and NDVI z, detrended per calendar month over 2001–2022.
  - NDVI cell-months with mean SummaryQA > 1 are dropped (14.7%).
- **Events:** runs ≥2 months. A drought event is "compound" if any month is hot.
  - Impact = min GPP z ≤ −1.
  - Recovered = GPP z ≥ −0.5 for 2 consecutive active months.
  - Censored at the next event, at 24 months, or at the end of the record.
- **Statistics:** year-block bootstrap (1,000 replicates, multinomial year counts). Contrasts and the amplification index (AI) are bootstrapped jointly.

## 4. Bugs found and fixed (don't reintroduce)
1. **computePixels and masked pixels.** `computePixels` returns 0 (not NaN) for masked pixels. We now fetch a validity band → NaN (`gee.compute_pixels_numpy`).
2. **Resolution reduction.** Whole-India MODIS/WorldCover with a hard `maxPixels` fails ("Reprojection output too large" / "Too many input pixels"). `reduce_to_grid` uses `bestEffort=True`. No tiling is needed.
3. **India mask.** `unmask(0)` needs `sameFootprint=False`, otherwise the India mask was 1 everywhere.
4. **Band names.** EE band names can't start with `__`.
5. **India mask applied to stats.** It used to be applied only to maps, and 37% of the "India" statistics came from neighbouring countries. Fixed in `cube.add_active_season_mask`.
6. **Climatology baseline.** Anomalies used to be computed after cutting to 2001–2022, so the "1991–2020 baseline" was really 2001–2020. Now climate anomalies are computed on the full 1991–2024 record (`cube.compute_climate_anomalies`).
7. **NDVI QA** was never applied; now it is.
8. **Bootstrap.** It used `np.isin` on drawn years, which drops repeat draws. Now uses multinomial weights (`stats._year_weights`).
9. **Recovery censoring.** Censored events were counted as "not recovered". Now Kaplan–Meier, plus a severity-matched comparison, because compound droughts are longer and more severe.
10. **GPP leap-year artefact (found last).** We summed MOD17 8-day composites per month. In leap years DOY 121 = 30 Apr and DOY 305 = 31 Oct, so April and October gained a composite (+38–40%) and May and November lost one (−26%).
    - Fixed with `indices.composite_sums_to_monthly` (mean daily rate × days in month).
    - The cached `data/raw/gpp_*.npz` were corrected in place and carry a `monthly_method` marker; `cube._check_gpp_cache` refuses unmarked files.
    - Backup of the old files: `EST/_backup_gpp_uncorrected/`.
11. **Smaller fixes:**
    - Frequency-map denominator was wrong.
    - QC was checking heatwaves in JJAS; it now uses MAM.
    - Case-study colormap used Set2 with 8 colours; it now uses 4 explicit colours.

## 5. Current results
See section 9 of `README.md` and `slides/NUMBERS.md`. All numbers come from `results/` after the GPP fix.

## 6. Literature / novelty (verified via Crossref, Oct 2026)
**Already done by others:**
- **Meena et al. 2026**, *Ecol. Indicators* 191:115617, doi:10.1016/j.ecolind.2026.115617.
  - India-wide NDVI response to compound dry–hot conditions.
  - Copula probabilities with "nonlinear amplification" metrics.
- **Sen, Barua & Monteiro 2026**, *Environ. Res. Commun.*, doi:10.1088/2515-7620/aea1e9.
  - Peninsular forest MOD17 GPP under compound hot–dry conditions.
- **Global recovery studies** disagree with each other: Yao 2024 (NSR), Huang & Zhai 2025 (ERL), Feng 2026 (CEE).
- **Trend studies:** Sharma & Mujumdar 2017 and Bhattacharjee & Dhanya 2026 (NHESS) report increasing compound drought–heatwave events in India, using records from 1951 and daily definitions.
  - Our monthly 1991–2024 trend is not significant. The deck explains the difference.

**What we add, honestly:**
- India-wide recovery comparison of compound vs drought-only vs heat-only events, severity-matched.
- Mean-anomaly additivity test with CIs on both GPP and NDVI, by land cover and region.
- Evidence that the drought-index choice changes conclusions.
- GPP/NDVI disagreement for forests.

**Framing:** regional synthesis/replication with extensions.

**Errors in the submitted lit review** (not editable now; fix in the final report):
- Sen 2026 and Liang 2026 titles were paraphrased or fabricated.
  - Real Liang: *Nat. Commun.* 17:2303, "Anthropogenically-driven escalating impact of soil-based compound dry-hot extremes on vegetation productivity".
- "Xu 2024 forest structural complexity" is misattributed. The real Xu 2024 is AFM 344:109799 (2022 China event).
- "Li 2024" was not found.
- Tschumi is 2022, *Biogeosciences* 19:1979.
- von Buttlar 2018 **does** compare single vs compound extremes. Don't cite it as lacking a baseline.
- `slides/references.bib` already has the corrected entries.

## 7. Open work for the final phase
- **Recovery drivers:** regression of recovery time on post-event SPI/rainfall vs VPD, severity, land cover (Yao vs Huang vs Feng). `stats.panel_fixed_effects_ols` exists but is unused so far.
- **Stricter compound rule:** ≥50% hot months (`THRESH.compound_event_frac`). Also daily-heatwave definitions, to compare with the trend literature.
- **Independent GPP:** GOSIF / PML_V22a (`config.MODIS_GPP_FALLBACK`), to check the forest GPP vs NDVI disagreement and MOD17's built-in VPD/Tmin scalars.
- **Probability-based amplification metric**, for direct comparison with Meena 2026.
- **Deciduous vs evergreen split** in Peninsular forests (MODIS MCD12Q1).
- **Per-cell synergy map**; 2015 and 2022 case studies.
- **Sensitivity runs:**
  - Thresholds at 1.28 SD.
  - SPEI-1/6 (already cached in `spei_*.npz`).
  - Detrended Tmax.
  - 1-month lag.
  - Soil-moisture drought definition.
  - Land-cover purity 70%.
  - Early vs late period.
- **H2 regression** (teammates' idea, on the v4 slides): GPP z = a·Tmax z + b·(−SPEI-3) + c·interaction, with cell fixed effects and year-clustered SEs. `stats.panel_fixed_effects_ols` can do this.
- **Another country:** repeat the pipeline outside India; the country is not chosen yet. Needs a new grid and mask in `config.py` plus a new fetch.
- **Final report**, with the corrected citations.

## 8. Practical notes
- `cube.nc` is 1.4 GB and `data/raw` is 292 MB. Script 02 rebuilds the cube from `data/raw` with no GEE calls.
- Script 02 with full SPI fitting takes several minutes. Scripts 03–05 take a few minutes each.
- Plan file from the first session: `C:\Users\choud\.claude\plans\ok-so-do-the-tidy-lark.md`. It is outdated in places (tiling, MOD17 details, and its "Day" schedule). Trust the code and this file over it.
