# Viva script: slides 1–13 (`ff_themed.pptx`)

Total speaking time for these 13 slides: about 7–8 minutes.
**Say** is what to speak, in plain words. **If they ask** gives likely viva questions with short answers.
Every number below matches the slides or our result files.

---

## Slide 1: Title (≈ 20 s)

**Say:**
"Good morning. We are presenting our EVS project on compound heat–drought stress over India.
The question is simple: when heat and drought hit at the same time, are ecosystems hurt more than
when only one of them hits? This is our mid-evaluation, so we'll show what we have tested so far and
what is left for the final evaluation."

**If they ask:**
- *What is the map on the title slide?* It's just a decorative India outline from the template, not a result.

---

## Slide 2: Outline (≈ 15 s)

**Say:**
"We'll go in five parts: the problem and why it matters, our four hypotheses, our method, the
preliminary results for the first two hypotheses, and what we will do next."

---

## Slide 3: Section 01, Problem statement & motivation (≈ 5 s)

**Say:** "First, the problem."

---

## Slide 4: Problem statement (≈ 40 s)

**Say:**
"Our assigned topic is compound heat–drought stress: are ecosystems experiencing stronger combined
impacts? Put simply: does heat and drought happening together cause more stress to vegetation than
either one alone?
The task asks us to compare two things between compound and single-stress events: productivity,
meaning how much plants grow, and recovery, meaning how fast they bounce back.
'Compound' just means two extremes at the same place and time. Here that is a month that is both
unusually hot and unusually dry."

**If they ask:**
- *Why does "combined" matter, if both are bad anyway?* If the damages simply add up, we can predict
  compound damage from studies of heat alone and drought alone. If they amplify each other, compound
  events are a separate and bigger risk, and single-stress studies would underestimate it.
- *Have you studied recovery?* Not yet. Recovery is hypothesis H3, planned for the final evaluation.
  The code to detect events is written, but we haven't presented results.
- *Is this new?* Honestly, it's a regional synthesis rather than a first-of-its-kind study. Recent
  India-wide work exists. For example, Meena et al. (2026) look at the *probability* of vegetation
  drought, and Sen et al. (2026) look at Peninsular forests. What we add is a direct test of whether
  the effect on *average* productivity is more than additive, with confidence intervals, on two satellite
  measures and two drought definitions.

---

## Slide 5: Heat and drought rarely come alone (≈ 60 s)

**Say:**
"Drought is a shortage of water: little rain, so the soil dries out and roots can't supply the plant.
A heatwave is unusually high temperature. Hot air is 'thirstier'. The scientific term is
vapour-pressure deficit, or VPD, and it pulls water out of leaves faster.
The key point is that the two feed each other. Normally, when the sun heats wet ground, much of that
energy goes into evaporating water, which cools the surface. When the soil is dry there is nothing to
evaporate, so the energy heats the air instead. And hotter air evaporates water faster, so the soil
dries even more. That's the loop on the right.
Both paths end in the same place: plants close their stomata, the small pores on their leaves, and
photosynthesis drops."

**If they ask:**
- *What exactly is VPD?* The difference between how much water vapour the air *could* hold at its
  temperature and how much it actually holds, measured in kPa. High VPD means dry, thirsty air. We
  compute it from ERA5-Land air temperature and dew point.
- *Is there evidence in your data that they occur together?* Yes. In our growing-season months, 17%
  are hot and 21% are dry. If the two were independent we'd expect about 3.6% of months to be both, but
  we see 7.6%, about twice as many.
- *What's the physics term for this loop?* Land–atmosphere (soil-moisture–temperature) feedback. Less
  evaporation means less latent heat and more sensible heat, so the surface warms.
- *Is heat always bad for plants?* No. When water is plentiful, warm months can even help growth. Our
  response surface (later) shows hot-but-wet months are not below normal. Heat hurts mainly when it
  comes with dryness.

---

## Slide 6: How heat and drought affect plants (≈ 70 s)

**Say:**
"Plants take carbon out of the air through photosynthesis. The total amount is called gross primary
productivity, or GPP. It's the base of all plant growth and of food production, so it's our main
measure of plant health.
Leaves take in CO₂ through tiny pores called stomata, but water escapes through the same pores. So a
plant always trades water for carbon.
Under heat and drought together the plant is squeezed from both sides. Drought means less water in
the soil, so roots can't supply the leaves. Heat means the air demands more water, so the plant closes
its stomata to avoid drying out. But closed stomata also mean less CO₂ comes in, so GPP falls. And with
no water to evaporate, leaves can't cool themselves and they overheat.
Two real examples: in Europe in summer 2003, heat with drought cut plant productivity by about 30%. In
India in 2009, the monsoon brought about 22% less rain than normal along with above-normal
temperatures. Vegetation browned across north and central India and the kharif harvest fell sharply."

**If they ask:**
- *What are the units of GPP?* Grams of carbon per square metre per month (gC/m²/month) in our data.
- *GPP vs NPP?* GPP is total carbon fixed. NPP (net primary productivity) is GPP minus what the plant
  itself respires. We use GPP because it reacts directly to stomatal closure.
- *Where is the 30% from?* Ciais et al. (2005, Nature), on the 2003 European heatwave. That event also
  briefly turned Europe's land into a carbon source.
- *Where is the 22% from?* The India Meteorological Department's 2009 monsoon (June–September)
  rainfall was about 78% of the long-period average. In our own data, 2009 is the 5th driest monsoon of
  1991–2024 by SPEI-3, and 2002 is the driest.
- *Why does closing stomata reduce photosynthesis?* CO₂ enters only through open stomata. Closing them
  saves water but starves the leaf of CO₂.

---

## Slide 7: Section 02, Our hypotheses (≈ 5 s)

**Say:** "From this we built four hypotheses."

---

## Slide 8: Our hypotheses (≈ 50 s)

**Say:**
"H1: vegetation, measured by GPP and NDVI, is lower in compound months than in hot-only or dry-only
months. So compound is the worst of the three.
H2 is the stronger claim: the compound effect is *synergistic*, meaning bigger than the heat effect plus
the drought effect added together. This is the key question for prediction.
H3: ecosystems recover more slowly after compound events than after droughts alone.
H4: the response differs by land cover, like forest versus cropland, and by region, Peninsular versus
North India.
H1 and H2 are tested and we'll show results today. H3 and H4 are for the final evaluation."

**If they ask:**
- *What's the difference between H1 and H2?* H1 asks whether compound is worse than *each* single
  stress. H2 asks whether it is worse than *both together*. You can pass H1 and still fail H2.
- *Why did you expect synergy?* Because of the feedback loop: the two stresses strengthen each other
  physically, and some global studies report amplified impacts.
- *Why not H3 and H4 now?* We prioritised getting H1/H2 right with proper uncertainty. Recovery needs
  event tracking over months, and the land-cover split needs more checks, so both are scheduled for the
  final evaluation.
- *What is NDVI?* Normalised Difference Vegetation Index: (NIR − Red) / (NIR + Red) from satellite
  reflectance. It measures greenness on a 0–1 scale.

---

## Slide 9: Section 03, Methodology (≈ 5 s)

**Say:** "Now, how we tested this."

---

## Slide 10: Workflow (≈ 45 s)

**Say:**
"The pipeline has three steps. Step 1: we download all the datasets through Google Earth Engine and
average them onto one common grid, about 27 km boxes, one value per month. Step 2: we turn every value
into an anomaly, meaning how unusual it is for that place and that time of year, and we sort every month
into one of four boxes: normal, hot-only, dry-only or compound. Step 3: we compare GPP and NDVI across
the four boxes, which tests H1 and H2. The grey box is the recovery and region analysis for the final
evaluation.
Everything is scripted in Python and checked with automated tests, so the whole analysis can be rerun
from the saved data in minutes."

**If they ask:**
- *What is Google Earth Engine?* Google's free cloud platform that stores satellite and climate datasets
  and processes them on its servers. We only download the small aggregated grids, not terabytes of raw
  data. The standard citation is Gorelick et al. (2017).
- *How did you combine datasets with different resolutions?* Fine data (MODIS 500 m–1 km, ERA5-Land
  ~9 km, CHIRPS ~5 km) are averaged up to 0.25°. SPEI is coarser (0.5°), so each 0.25° box takes its
  value from the 0.5° cell it lies in.
- *What do the tests check?* For example: z-scores have mean 0 and SD 1, the drought index comes out
  right on synthetic data, months land in the correct box, and the statistics never include cells
  outside India.

---

## Slide 11: Data (≈ 70 s)

**Say:**
"Everything is on one grid: boxes about 27 km wide, one value per month, 4,481 boxes inside India.
- ERA5-Land, 1991–2024, is reconstructed weather, combining a weather model with observations. Its
  daily maximum temperature tells us which months are *hot*.
- SPEI, 1991–2024, is a ready-made drought index. It tells us which months are *dry*.
- CHIRPS, 1991–2024, is rainfall from satellites plus rain gauges. We use it as a second, rain-only
  drought check.
- MODIS GPP, 2001–2022, is the satellite estimate of photosynthesis and our main measure of plant
  health.
- MODIS NDVI, 2001–2022, is satellite greenness, our second measure.
- ESA WorldCover, 2021, is a land-cover map. It tells us forest, cropland, shrubland or grassland, and
  lets us remove non-vegetated areas like deserts and cities.
These are the five datasets suggested for the topic. The analysis period is 2001–2022 because that's
where satellite GPP is available. The climate data go back to 1991 so we have a 30-year baseline."

**If they ask:**
- *Why 2001–2022?* The MODIS GPP product we use (MOD17A2H v006) covers 2001 to early 2023 on Earth
  Engine, so 2022 is the last full year.
- *Is MODIS GPP measured or modelled?* Partly modelled. It's a light-use-efficiency model: absorbed
  sunlight (from MODIS) × an efficiency that is reduced by low temperature and high VPD. It has no
  soil-moisture input. That's a known limitation, which is why we also use NDVI, which is directly
  observed.
- *How did you get monthly GPP from 8-day data?* We take the average daily rate of the 8-day composites
  in each month and multiply by the number of days in the month. A plain sum of composites gives wrong
  totals in some months, especially in leap years, so we corrected for that.
- *Clouds during the monsoon?* NDVI uses a quality flag. We drop cloudy or poor-quality values, which
  removes 14.6% of growing-season NDVI values.
- *WorldCover is from 2021 but your data start in 2001?* Yes, we assume land cover is roughly stable.
  We use it only to mask out non-vegetated cells, and the map shows the dominant class.
- *Which boundary did you use?* The US State Department LSIB boundary from Earth Engine, which is not
  India's official boundary. It's used only to pick grid cells, and a box counts if at least half of it
  is inside India.

---

## Slide 12: Metrics at a glance (≈ 60 s)

**Say:**
"Quickly, the measures. For the ecosystem response: GPP is carbon taken up by photosynthesis, higher
means more productive. NDVI is greenness, higher means greener.
For stress: Tmax z is the temperature anomaly, and 1 or more counts as a hot month. SPEI-3 is the
3-month water balance, rain minus evaporative demand, and −1 or less is a dry month. SPI-3 is the same
idea using rainfall only, our robustness check. Soil moisture is water in the top metre of soil. VPD is
how thirsty the air is. We use these two to explain *why* plants are stressed.
For statistics: a z-score is how far a value is from normal for that place and calendar month, in
standard deviations. The amplification index is the compound effect minus heat effect plus drought
effect: below zero means synergy, near zero means additive. And all our 95% confidence intervals come
from a year-block bootstrap: we resample whole years 1,000 times. A result is significant if its
interval doesn't include zero."

**If they ask:**
- *Why the thresholds +1 and −1?* They are standard: SPEI ≤ −1 is "moderate drought" in the usual
  classification, and ±1 SD picks out roughly the most extreme sixth of months. Testing other
  thresholds, like 1.28 SD, is planned. Our planned regression (in "Things left to do") avoids
  thresholds entirely.
- *What does "3" in SPEI-3 mean?* The water balance is added up over the last 3 months, so it captures
  drought that has built up over a season, not just one dry month.
- *Why resample years instead of individual months?* Neighbouring cells in the same year are strongly
  correlated, because one weak monsoon affects half the country. Treating 824,598 cell-months as
  independent would make the intervals far too narrow. Resampling whole years (22 of them) keeps that
  correlation.
- *Why both SPEI and SPI?* SPEI includes evaporative demand, which depends on temperature, so a hot month
  looks drier partly *because* it is hot. That would mix up heat and drought. SPI uses rainfall only,
  so it is a clean check.
- *Units of VPD and soil moisture?* VPD is in kPa. Soil moisture is volumetric (m³ of water per m³ of
  soil), averaged over 0–100 cm, weighted by layer depth. Both are converted to z-scores.

---

## Slide 13: Method: four stress categories (≈ 60 s)

**Say:**
"Why z-scores? Raw values can't be compared: May is always hotter than January, and a desert always has
less GPP than a forest. So for each grid box and each calendar month we compare a value with what is
normal *there* and *then*.
A month is hot if its average daily maximum temperature is at least one standard deviation above normal.
It is dry if SPEI-3 is −1 or less, meaning the last three months had clearly less water than usual.
Every one of our 824,598 growing-season grid-months then falls into one of four boxes. On the right:
573,543 normal, 79,717 hot-only, 109,073 dry-only and 62,265 compound, which is 7.6%.
Because SPEI depends partly on temperature, we repeat everything with SPI-3, which is rainfall only."

**If they ask:**
- *What is a "growing-season grid-month"?* A box-month that counts in our statistics. The box must be
  inside India and at least 50% vegetated, and the month must be one where GPP is normally at least 30%
  of that box's peak. This removes deserts, snow and dormant seasons.
- *Did you remove trends?* For GPP and NDVI, yes. India has been greening due to CO₂, irrigation and
  farming, and we don't want that counted as an anomaly. For temperature, no. We use a fixed 1991–2020
  baseline so that long-term warming counts as heat, because that is the real stress plants face.
- *Is 7.6% a lot?* It's about twice what you'd expect if heat and drought were independent: 17% hot ×
  21% dry ≈ 3.6%. So compound months are more common than chance, as slide 5 said.
- *Why is "dry-only" bigger than "hot-only"?* Monsoon failures make dry months fairly common, while a
  hot month in a wet spell is less common, because rain cools the land.
- *Couldn't one hot day be missed in monthly data?* Yes. Short heatwaves are smoothed out in monthly
  averages. It's a limitation we state, and daily heatwave definitions are a planned check.

---

### Quick numbers to remember

- 4,481 grid boxes (0.25°, ≈27 km); 824,598 growing-season grid-months; analysis period 2001–2022
- Boxes: normal 573,543 · hot-only 79,717 · dry-only 109,073 · compound 62,265 (7.6%)
- Hot ≥ +1 SD (Tmax z) · dry ≤ −1 (SPEI-3) · bootstrap: 1,000 resamples of 22 years
- Europe 2003: about −30% productivity · India 2009: about −22% monsoon rain
