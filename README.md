# Compound Heat–Drought Stress over India

**Are ecosystems hit harder when heat and drought strike together?**
EVS course project, mid-evaluation. IIIT Hyderabad.
Arnav Deshmukh, Ayush Brajesh Roy, Saksham Chitkara, Gracy Garg, Rudra Choudhary.

We test whether months that are both hot and dry ("compound" months) reduce vegetation
productivity (MODIS GPP) and greenness (MODIS NDVI) more than hot-only or dry-only months, and whether
the compound effect is larger than the heat effect and the drought effect added together.
All of India, 0.25° grid, monthly, 2001–2022.

- **`analysis.ipynb`** contains every analysis and figure in our slides, with outputs.
- **`slides/midsub_slides.pdf`** is the mid-evaluation presentation.

## Main results

| | GPP | NDVI |
|---|---|---|
| Mean z in compound months [95% CI] | −0.43 [−0.54, −0.33] | −0.68 [−0.81, −0.55] |
| Compound minus dry-only | −0.16 [−0.26, −0.04] | −0.38 [−0.49, −0.28] |
| Compound minus hot-only | −0.30 [−0.40, −0.21] | −0.31 [−0.43, −0.21] |
| Amplification index, SPEI-3 (< 0 = synergy) | +0.09 [−0.03, +0.21] | +0.18 [+0.06, +0.30] |
| Amplification index, SPI-3 | −0.00 [−0.12, +0.13] | +0.06 [−0.05, +0.18] |

- **H1 supported:** compound months reduce GPP and NDVI significantly more than heat alone or drought
  alone, with both drought indices. They combine the driest soils (soil moisture z −1.04) with the
  thirstiest air (VPD z +1.43).
- **H2 not supported:** the compound effect is about the *sum* of the two single effects, not more.
  The details depend on the drought index (SPEI-3 vs SPI-3).

Hypotheses H3 (recovery after compound events) and H4 (differences by land cover and region) are planned
for the final evaluation and are not part of this repository.

## Repository structure

```
analysis.ipynb          all analyses and slide figures, with outputs
chd/                    Python package used by the notebook and scripts
  config.py               grid, periods, dataset IDs, thresholds, paths
  gee.py                  Google Earth Engine download and aggregation to the 0.25° grid
  indices.py              z-scores, SPI-3 (gamma fit), VPD, root-zone soil moisture, MODIS GPP monthly totals
  cube.py                 builds the analysis data cube (anomalies, stress categories, growing-season mask)
  categories.py           normal / hot-only / dry-only / compound classification
  stats.py                year-block bootstrap (all confidence intervals)
  impacts.py              H1/H2: composites, contrasts, amplification index, SPI-3 check,
                          response surface, soil-moisture/VPD check, compound frequency
  plotting.py             the six slide figures
scripts/
  00_check_gee.py         check Earth Engine access and every dataset
  01_fetch.py             download all data to data/raw/ (resumable, about 1 hour)
  02_build_cube.py        build data/processed/cube.nc and print data-quality checks
  03_analysis_h1_h2.py    the notebook's analyses as one script (writes results/ and figures/)
figures/                the six figures used in the slides
results/                result tables (CSV) behind every number in the slides
tests/                  unit tests on synthetic data (pytest)
slides/                 mid-evaluation slides (PDF and PPTX)
```

## How to reproduce

The data are not stored in the repository (about 300 MB raw, 1 GB processed). They are downloaded from
Google Earth Engine, which needs a free Earth Engine account and a Google Cloud project.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt      # Python 3.12 or newer

earthengine authenticate             # once, opens a browser
export EE_PROJECT=your-gcp-project   # Windows: $env:EE_PROJECT="your-gcp-project"

python scripts/00_check_gee.py       # checks access to every dataset
python scripts/01_fetch.py           # downloads everything to data/raw/
python scripts/02_build_cube.py      # builds data/processed/cube.nc (a few minutes)
python scripts/03_analysis_h1_h2.py  # or open analysis.ipynb and run all cells
python -m pytest tests -q            # unit tests (no data or Earth Engine needed)
```

Steps 02 and 03 need no Earth Engine access once `data/raw/` exists.

## Method in brief

1. **Data:** monthly fields on one 0.25° grid over India (4,481 grid cells), aggregated in Earth Engine.
2. **Anomalies:** every variable becomes a z-score for its own grid cell and calendar month.
   Temperature uses a 1991–2020 baseline and is not detrended, so warming counts as heat.
   GPP and NDVI are detrended, so long-term greening is not counted as an anomaly.
   Only growing-season months count: the cell is inside India, at least 50% vegetated, and its GPP that
   month is normally at least 30% of its peak (824,598 cell-months).
3. **Four boxes:** hot = Tmax z ≥ 1; dry = SPEI-3 ≤ −1. Repeated with SPI-3 (rainfall only), because
   SPEI's evaporative-demand term depends on temperature.
4. **Tests:** mean GPP z and NDVI z per box (H1), and the amplification index
   Δcompound − (Δhot + Δdry) (H2). All 95% confidence intervals come from a year-block bootstrap
   (1,000 resamples of whole years), because cell-months from the same year are not independent.
   A heat × dryness response surface checks the result without fixed cut-offs.

## Data sources

| Dataset | Earth Engine ID | Reference |
|---|---|---|
| ERA5-Land daily | `ECMWF/ERA5_LAND/DAILY_AGGR` | Muñoz-Sabater et al. (2021), doi:10.5194/essd-13-4349-2021 |
| SPEI v2.11 | `CSIC/SPEI/2_11` | Vicente-Serrano et al. (2010), doi:10.1175/2009JCLI2909.1 |
| CHIRPS v2 | `UCSB-CHG/CHIRPS/PENTAD` | Funk et al. (2015), doi:10.1038/sdata.2015.66 |
| MODIS GPP (MOD17A2H v006) | `MODIS/006/MOD17A2H` | Running et al. (2015); Running et al. (2004), doi:10.1641/0006-3568(2004)054[0547:ACSMOG]2.0.CO;2 |
| MODIS NDVI (MOD13A3 v061) | `MODIS/061/MOD13A3` | Didan (2021) |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | Zanaga et al. (2022), doi:10.5281/zenodo.7254221 |
| Country boundary | `USDOS/LSIB_SIMPLE/2017` | US Department of State LSIB |
| Processing | Google Earth Engine | Gorelick et al. (2017), doi:10.1016/j.rse.2017.06.031 |

The India mask uses the US State Department boundary (LSIB), which is not India's official boundary;
it is used only to select grid cells for the analysis.
