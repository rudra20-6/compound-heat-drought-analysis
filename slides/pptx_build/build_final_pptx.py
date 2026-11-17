"""Build slides/final_themed.pptx: the final-evaluation deck (India + Australia) in the
same "Africa Viva" theme, layouts and helpers as the mid-sub deck (build_ff_pptx.py).

Every number comes from results/*.csv through final_numbers.py; the narrative text
lives in final_text.py. Run from anywhere with the project venv:
    python slides/pptx_build/build_final_pptx.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_pptx import *  # noqa: F401,F403
from build_pptx import (ROOT, TEMPLATE, set_title, waves, page_no, text_box, heading, drop_placeholders,
                        rect, box_text, arrow, picture_card, table, add_runs)
from title_map import put_countries_on_title_layout
import final_numbers as N
from final_numbers import m, ci, pv, n0, FIGS, CMP_FIG
import final_text as T

OUT = ROOT / "slides" / "final_themed.pptx"
C = PP_ALIGN.CENTER


def main():
    T._init()
    prs = Presentation(str(TEMPLATE))
    lst = prs.slides._sldIdLst
    for sid in list(lst):
        prs.part.drop_rel(sid.rId)
        lst.remove(sid)
    put_countries_on_title_layout(prs)
    lay = prs.slide_layouts
    page = [0]

    def new(layout_idx, title=None, number=True, num_color=MAROON, **tkw):
        s = prs.slides.add_slide(lay[layout_idx])
        page[0] += 1
        if layout_idx == L_PLAIN:
            tkw.setdefault("box", (0.45, 0.2, 12.43, 0.9))
            tkw.setdefault("size", 34)
            tkw.setdefault("color", YELLOW)
        if title is not None:
            t = set_title(s, title, **tkw)
            t.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            t.text_frame.word_wrap = True
        if layout_idx == L_PLAIN:
            waves(s, prs)
        if number:
            page_no(s, page[0], num_color)
        return s

    secs = [("01", "Problem & motivation"), ("02", "Hypotheses"), ("03", "Data & methods"),
            ("04", "Results: India"), ("05", "Results: Australia"), ("06", "India vs Australia"),
            ("07", "Conclusions")]

    def section(k):
        num, title = secs[k]
        s = new(L_SECTION, title.upper(), number=False, size=50, align=C, box=(1.2, 2.05, 10.93, 1.9))
        drop_placeholders(s)
        s.shapes.title.text_frame.vertical_anchor = MSO_ANCHOR.TOP
        nb = text_box(s, 3.2, 0.1, 6.93, 2.7, [("plain", num)], size=170, color=YELLOW,
                      bullets=False, align=C, font=HEAD_FONT)
        s.shapes._spTree.remove(nb._element)
        s.shapes._spTree.insert(2, nb._element)

    def footnote(s, txt, y=6.62):
        text_box(s, 0.6, y, 12.1, 0.4, [("plain", txt)], size=11, color=CREAM, bullets=False)

    # ================================================================ title
    s = new(L_TITLE, number=False)
    set_title(s, "COMPOUND HEAT–DROUGHT STRESS: INDIA & AUSTRALIA", size=50, align=PP_ALIGN.RIGHT,
              box=(6.6, 0.4, 6.3, 3.3))
    sub = s.placeholders[1]
    sub.left, sub.top, sub.width, sub.height = I(7.2), I(3.75), I(5.7), I(1.7)
    tf = sub.text_frame
    tf.word_wrap = True
    for k, (txt, size, col, before) in enumerate([
            ("Are ecosystems hit harder when heat and drought strike together?", 17, YELLOW, 0),
            ("Final Evaluation, EVS Project #19", 14, WHITE, 4),
            ("Arnav Deshmukh · Ayush Brajesh Roy · Saksham Chitkara", 13, WHITE, 8),
            ("Gracy Garg · Rudra Choudhary", 13, WHITE, 0),
            (f"IIIT Hyderabad · {T.DATE}", 13, WHITE, 0)]):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.RIGHT
        p.space_before = Pt(before)
        add_runs(p, txt, size, col)

    # ================================================================ outline
    s = new(L_TOC, "OUTLINE")
    drop_placeholders(s)
    for k, (n, t) in enumerate(secs):
        y = 0.45 + k * 0.92
        heading(s, 6.3, y, 1.2, 0.8, n, size=40, color=ORANGE)
        heading(s, 7.45, y + 0.16, 5.5, 0.55, t.upper(), size=24, color=RED1)

    # ================================================================ 01 problem
    section(0)
    s = new(L_YELLOW, "PROBLEM STATEMENT", num_color=WHITE, box=(0.7, 0.35, 11.9, 0.85), align=C)
    drop_placeholders(s)
    s.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = MAROON
    heading(s, 0.7, 1.35, 11.9, 1.3,
            "COMPOUND HEAT–DROUGHT STRESS: ARE ECOSYSTEMS EXPERIENCING STRONGER COMBINED IMPACTS?",
            size=32, color=RED2, align=C)
    text_box(s, 1.2, 2.85, 10.9, 0.9, [("plain",
        "Does simultaneous heat and drought produce greater ecosystem stress than either disturbance "
        "alone?")], size=22, color=MAROON, bullets=False, align=C)
    blk = rect(s, 2.2, 3.95, 8.9, 0.75, MAROON, radius=0.2)
    box_text(blk, ["Compare productivity and recovery during compound and single-stressor events."], 17, WHITE)
    text_box(s, 3.2, 4.85, 9.4, 0.9, [("plain",
        "Final phase: all four hypotheses tested, with proper significance tests, in **India** and again in "
        "**Australia**.")], size=18, color=MAROON, em=RED2, bullets=False, align=C)

    s = new(L_PLAIN, "HEAT AND DROUGHT RARELY COME ALONE")
    text_box(s, 0.6, 1.4, 5.6, 5.3, [
        "**Drought**: a shortage of water – little rain, so the soil dries and roots cannot supply the plant.",
        "**Heatwave**: unusually high temperature. Hot air is “thirstier” (higher VPD) and pulls water out of "
        "leaves.",
        "**They feed each other:**",
        (1, "dry soil has no water to evaporate, so the sun heats the air instead of cooling the land;"),
        (1, "heat speeds up evaporation, so the soil dries even faster.")], size=17, space=10)
    bw, bh = 2.85, 1.35
    hx, hy, vx, sy = 6.75, 1.75, 10.15, 4.6
    b1 = rect(s, hx, hy, bw, bh, RED2)
    box_text(b1, ["**Heat**", "(high temperature)"], 17, WHITE)
    b2 = rect(s, vx, hy, bw, bh, ORANGE)
    box_text(b2, ["**Dry air**", "(high VPD)"], 17, WHITE)
    b3 = rect(s, hx, sy, bw, bh, RED1, line=ORANGE2)
    box_text(b3, ["**Dry soil**", "(drought)"], 17, WHITE)
    b4 = rect(s, vx, sy, bw, bh, YELLOW)
    box_text(b4, ["Plants close stomata", "⇒ **less photosynthesis**"], 15, MAROON)
    arrow(s, hx + bw, hy + bh / 2, vx, hy + bh / 2)
    arrow(s, vx + bw / 2, hy + bh, vx + bw / 2, sy)
    arrow(s, hx + bw, sy + bh / 2, vx, sy + bh / 2)
    arrow(s, hx + 0.7, hy + bh, hx + 0.7, sy)
    arrow(s, hx + bw - 0.7, sy, hx + bw - 0.7, hy + bh)
    text_box(s, hx - 1.35, 3.3, 1.95, 0.8, [("plain", "more\nevaporation")], size=14, color=CREAM,
             bullets=False, align=PP_ALIGN.RIGHT)
    text_box(s, hx + bw - 0.58, 3.3, 1.4, 0.8, [("plain", "less\ncooling")], size=14, color=CREAM,
             bullets=False, align=PP_ALIGN.LEFT)

    s = new(L_PLAIN, "HOW HEAT AND DROUGHT AFFECT PLANTS")
    text_box(s, 0.6, 1.25, 12.1, 5.6, [
        "Plants take up carbon by photosynthesis. The total amount is **gross primary productivity (GPP)** "
        "– the base of food production and of the land carbon sink.",
        "Leaves have tiny pores (**stomata**): CO₂ enters through them, and water escapes through the same pores.",
        "Under heat //and// drought, plants are squeezed from both sides:",
        (1, "**drought**: less water in the soil, so roots cannot supply the leaves;"),
        (1, "**heat**: the air demands more water, so stomata close ⇒ less CO₂ uptake ⇒ lower GPP."),
        "Past events:",
        (1, "**Europe, 2003**: record heat with drought cut plant productivity by ~30% [1]."),
        (1, "**India, 2009**: ~22% monsoon rainfall deficit with above-normal temperatures; crops browned "
            "across north and central India."),
        (1, "**Australia, 2019**: the warmest and driest year on record, followed by the “Black Summer” "
            "fires that burnt ~21% of its temperate forests [20]."),
        ], size=18, space=8)

    s = new(L_PLAIN, "WHY ADD AUSTRALIA?")
    text_box(s, 0.6, 1.25, 6.3, 5.4, T.WHY_AUSTRALIA, size=17, space=10)
    rows = [["", "India", "Australia"],
            ["Climate", "Monsoon: one wet season", "Mostly semi-arid; rain driven by ENSO"],
            ["Main land cover", "Cropland (irrigated + rainfed)", "Grassland, shrubland, savanna"],
            ["Top compound years (our data)", ", ".join(str(y) for y, _ in N.top_years("India")),
             ", ".join(str(y) for y, _ in N.top_years("Australia"))],
            ["Grid cells in country", n0(N.study("India")["country_cells"]),
             n0(N.study("Australia")["country_cells"])],
            ["Growing-season grid-months", n0(N.counts("India").sum()), n0(N.counts("Australia").sum())]]
    table(s, rows, 7.15, 1.35, [1.95, 2.0, 2.1], row_h=0.62, size=13.5,
          align=[None, C, C])

    # ================================================================ 02 hypotheses
    section(1)
    s = new(L_PLAIN, "OUR HYPOTHESES")
    table(s, [
        ["", "Hypothesis", "Test"],
        ["**H1**", "GPP and NDVI are lower in compound months than in hot-only or dry-only months.",
         "Category means, contrasts, p-values"],
        ["**H2**", "The compound effect is //synergistic//: larger than heat effect + drought effect.",
         "Amplification index, regression, risk"],
        ["**H3**", "Recovery is slower after compound events than after droughts.", "Kaplan–Meier, Cox model"],
        ["**H4**", "The response differs by land cover and region.", "Stratified contrasts"],
        ["**H5**", "Compound months are becoming more frequent (1991–2024).", "Sen slope, Mann–Kendall"],
        ["**+**", "Do the answers hold in a second, very different country (Australia)?",
         "Same pipeline; country difference tests"]],
        0.6, 1.35, [0.9, 7.6, 3.6], row_h=0.74, size=16)

    # ================================================================ 03 methods
    section(2)
    s = new(L_TIMELINE, "WORKFLOW", box=(0.7, 0.3, 11.9, 0.95), align=C)
    drop_placeholders(s)
    steps = [("STEP 1", "Download & aggregate data (Earth Engine), India and Australia"),
             ("STEP 2", "Monthly anomalies (z); sort each month: normal / hot / dry / compound"),
             ("STEP 3", "H1–H5: impacts, synergy, recovery, strata, trends"),
             ("STEP 4", "Significance tests, sensitivity runs, India vs Australia")]
    bw, gap, x0, y0, bh = 2.65, 0.45, 0.75, 1.6, 1.95
    for k, (h, t) in enumerate(steps):
        x = x0 + k * (bw + gap)
        b = rect(s, x, y0, bw, bh, [RED2, ORANGE, YELLOW, GOLD][k])
        box_text(b, [f"**{h}**", t], 15, MAROON if k >= 2 else WHITE)
        if k < 3:
            arrow(s, x + bw + 0.04, y0 + bh / 2, x + bw + gap - 0.04, y0 + bh / 2, color=YELLOW, width=3)
    text_box(s, 0.95, 3.85, 11.4, 1.0, [("plain",
        "One Python pipeline (xarray, numpy, scipy, statsmodels, lifelines) with automated tests. "
        "Switching country is one setting (CHD_REGION); everything else – data, thresholds, statistics – "
        "is identical, so the two countries are directly comparable.")], size=16, color=CREAM, bullets=False)

    s = new(L_BULLETS, "DATA", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.35, 9.3, 0.5, [("plain",
        f"Same grid for both countries: ~27 km boxes (0.25°), one value per month. "
        f"{n0(N.study('India')['country_cells'])} boxes in India, "
        f"{n0(N.study('Australia')['country_cells'])} in Australia.")], size=15, bullets=False, color=CREAM)
    text_box(s, 0.75, 1.95, 9.3, 3.6, [
        "**ERA5-Land** (1991–2024): daily weather reanalysis; maximum temperature ⇒ //hot// months [10].",
        "**SPEI** (1991–2024): drought index (rain minus evaporative demand) ⇒ //dry// months [11].",
        "**CHIRPS** (1991–2024): satellite + gauge rainfall ⇒ rain-only drought index SPI-3 [12].",
        "**MODIS GPP** (2001–2022): satellite photosynthesis; main measure of plant health [13, 14].",
        "**MODIS NDVI** (2001–2022): satellite greenness; second measure [15].",
        "**ESA WorldCover** (2021): land cover; removes non-vegetated areas [16].",
        "All processed in **Google Earth Engine** [17]; ~300 MB per country after aggregation."],
        size=15, space=5)

    s = new(L_PLAIN, "STUDY AREAS AND LAND COVER")
    picture_card(s, FIGS["India"] / "study_area_landcover.png", 0.45, 1.2, 5.3, 4.95)
    picture_card(s, FIGS["Australia"] / "study_area_landcover.png", 5.95, 1.2, 6.95, 4.95)
    footnote(s, "Dominant ESA WorldCover class per 0.25° cell (white = no class ≥ 50%). Dashed line = sub-region "
                "split used for H4: Peninsular India (≤ 22°N) vs North; Australia’s tropical north vs temperate "
                "south (Tropic of Capricorn).", y=6.25)

    s = new(L_PLAIN, "METRICS AT A GLANCE")
    table(s, [
        ["Metric", "What it measures", "How to read it"],
        ["Ecosystem response", "", ""],
        ["GPP", "Carbon taken up by plants through photosynthesis (gC/m²/month)", "higher = more productive"],
        ["NDVI", "Canopy greenness from red and near-infrared reflectance (0–1)", "higher = greener"],
        ["Stress", "", ""],
        ["Tmax z", "Anomaly of the monthly mean daily maximum temperature", "≥ 1: “hot” month"],
        ["SPEI-3 / SPI-3", "3-month water balance / 3-month rainfall only", "≤ −1: “dry” month"],
        ["Soil moisture, VPD", "Water in the top 1 m of soil; “thirstiness” of the air", "mechanism check"],
        ["Statistics", "", ""],
        ["Amplification", "Compound effect − (heat effect + drought effect)", "< 0 synergy; ≈ 0 additive"],
        ["95% CI and p", "Year-block bootstrap: 10,000 resamples of whole years", "p < 0.05 ⇔ CI excludes 0"],
        ["q-value", "p-value corrected for testing many things at once (FDR)", "q < 0.05 survives"]],
        0.6, 1.2, [2.3, 6.5, 3.3], row_h=0.43, size=14.5, section_rows=(1, 4, 8))

    s = new(L_PLAIN, "METHOD: FOUR STRESS CATEGORIES")
    text_box(s, 0.6, 1.3, 5.6, 5.4, [
        "**z-scores** remove the seasonal cycle and the difference between places: each value is compared "
        "with what is normal for //that cell in that month//.",
        "**Hot**: Tmax z ≥ 1. **Dry**: SPEI-3 ≤ −1.",
        "Only **growing-season** months count: cell ≥ 50% vegetated and the month’s normal GPP ≥ 30% of the "
        "cell’s peak.",
        "SPEI’s demand term depends on temperature, so we repeat everything with rainfall-only **SPI-3**."],
        size=16, space=9)
    gx, gy, cw, chh = 8.15, 1.95, 2.2, 1.15
    for j, lab in enumerate(["SPEI-3 > −1", "SPEI-3 ≤ −1"]):
        text_box(s, gx + j * cw, gy - 0.45, cw, 0.4, [("plain", lab)], size=14, color=YELLOW,
                 bullets=False, align=C, font=HEAD_FONT)
    for i, lab in enumerate(["Tmax z < 1", "Tmax z ≥ 1"]):
        text_box(s, gx - 1.55, gy + i * chh, 1.5, chh, [("plain", lab)], size=14, color=YELLOW,
                 bullets=False, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, font=HEAD_FONT)
    ci_, ca_ = N.counts("India"), N.counts("Australia")
    tot_i, tot_a = ci_.sum(), ca_.sum()

    def cell(cat, label):
        return [label, f"IN {100 * ci_[cat] / tot_i:.1f}%", f"AU {100 * ca_[cat] / tot_a:.1f}%"]
    cells = [[cell("normal", "Normal"), cell("dry_only", "Dry-only")],
             [cell("hot_only", "Hot-only"), cell("compound", "**Compound**")]]
    fills = [[CARD, ORANGE], [RED2, YELLOW]]
    for i in range(2):
        for j in range(2):
            b = rect(s, gx + j * cw + 0.04, gy + i * chh + 0.04, cw - 0.08, chh - 0.08, fills[i][j], radius=0.1)
            box_text(b, cells[i][j], 13.5, MAROON if (i, j) == (1, 1) else WHITE, em=MAROON)
    text_box(s, gx - 1.55, gy + 2 * chh + 0.15, 1.55 + 2 * cw, 0.8, [("plain",
        f"Share of growing-season grid-months in each box, 2001–2022 "
        f"(India {n0(tot_i)}; Australia {n0(tot_a)}).")], size=12, color=CREAM, bullets=False, align=C)

    s = new(L_PLAIN, "HOW WE TEST H1 AND H2")
    text_box(s, 0.6, 1.2, 12.1, 1.0, [
        "**H1**: mean GPP //z// and NDVI //z// in each box, and the differences between boxes.",
        "**H2**, three complementary ways:"], size=19, space=6)
    eq = rect(s, 1.0, 2.25, 11.3, 0.7, CARD, line=YELLOW, line_w=1)
    box_text(eq, ["① Amplification = Δ_{compound} − (Δ_{hot} + Δ_{dry})     < 0 ⇒ synergy"], 20, WHITE)
    eq = rect(s, 1.0, 3.1, 11.3, 0.7, CARD, line=YELLOW, line_w=1)
    box_text(eq, ["② Regression: z = //a//·heat + //b//·dryness + //c//·(heat × dryness)     //c// < 0 ⇒ synergy"],
             20, WHITE)
    eq = rect(s, 1.0, 3.95, 11.3, 0.7, CARD, line=YELLOW, line_w=1)
    box_text(eq, ["③ Risk of a severe loss (z ≤ −1): RERI = RR_{compound} − RR_{hot} − RR_{dry} + 1     > 0 ⇒ synergy"],
             20, WHITE)
    text_box(s, 0.6, 4.85, 12.1, 1.7, [
        "① uses the four boxes; ② every month’s actual heat and dryness, no cut-offs (cell fixed effects, errors "
        "clustered by year); ③ the //chance// of a bad month [18], compared with what additive means alone would give.",
        "Recovery (H3): events = runs of ≥ 2 dry (or hot) months; recovered = GPP z ≥ −0.5 for 2 active months; "
        "Kaplan–Meier curves and a Cox model [19]."], size=15, space=8)

    s = new(L_PLAIN, "SIGNIFICANCE TESTING: P-VALUES DONE RIGHT")
    text_box(s, 0.6, 1.2, 6.2, 5.4, T.PTEST_BULLETS, size=15, space=8)
    picture_card(s, FIGS["India"] / "pvalue_ladder.png", 7.0, 1.35, 5.9, 2.5)
    text_box(s, 7.0, 4.05, 5.9, 2.6, T.PTEST_SIDE, size=14, space=6)

    s = new(L_PLAIN, "DATA CHECK: DO THE INPUTS SEE KNOWN EVENTS?")
    picture_card(s, FIGS["India"] / "qc_known_events.png", 0.45, 1.2, 6.15, 3.9)
    picture_card(s, FIGS["Australia"] / "qc_known_events.png", 6.75, 1.2, 6.15, 3.9)
    q_i, q_a = N.qc("India"), N.qc("Australia")

    def qc_line(q, kind):
        r = q[q["check"] == kind]
        return ", ".join(f"{int(x.year)} ({'driest' if kind == 'drought' else 'hottest'} #{int(x.rank)}/{int(x.of)})"
                         for x in r.itertuples())
    text_box(s, 0.6, 5.25, 12.1, 1.4, [
        f"**India**: droughts {qc_line(q_i, 'drought')}; heat {qc_line(q_i, 'heat')}.",
        f"**Australia**: droughts {qc_line(q_a, 'drought')}; heat {qc_line(q_a, 'heat')}.",
        "Both pipelines reproduce well-documented events, so the inputs can be trusted."], size=14, space=4)

    # ================================================================ 04/05 country results
    for k, country in ((3, "India"), (4, "Australia")):
        section(k)
        country_slides(new, country, footnote)

    # ================================================================ 06 comparison
    section(5)
    comparison_slides(new, footnote)

    # ================================================================ 07 conclusions
    section(6)
    s = new(L_PLAIN, "HYPOTHESES SCORECARD")
    table(s, T.SCORECARD, 0.6, 1.2, [1.1, 4.8, 3.2, 3.0], row_h=0.66, size=14.5,
          align=[None, None, C, C])
    footnote(s, T.SCORECARD_NOTE, y=6.15)

    s = new(L_BULLETS, "CONCLUSIONS", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.4, 9.4, 5.0, T.CONCLUSIONS, size=16, space=9)

    s = new(L_PLAIN, "LIMITATIONS")
    text_box(s, 0.6, 1.25, 12.1, 5.4, T.LIMITATIONS, size=16, space=8)

    s = new(L_PLAIN, "HOW THIS COMPARES WITH THE LITERATURE")
    text_box(s, 0.6, 1.25, 12.1, 5.4, T.LITERATURE, size=16, space=9)

    refs = T.REFERENCES
    per = 9
    chunks = [refs[i:i + per] for i in range(0, len(refs), per)]
    for part, chunk in enumerate(chunks):
        s = new(L_PLAIN, f"REFERENCES ({part + 1}/{len(chunks)})")
        start = part * per
        text_box(s, 0.6, 1.2, 12.1, 5.6, [("plain", f"**[{start + k + 1}]**  {r}") for k, r in enumerate(chunk)],
                 size=13, space=8, bullets=False)

    s = new(L_YELLOW, "THANK YOU!", number=False, box=(0.7, 1.4, 11.9, 1.4), align=C, size=66)
    drop_placeholders(s)
    s.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = MAROON
    text_box(s, 1.2, 3.1, 10.9, 1.2, [("plain", "Questions?")], size=30, color=RED2, bullets=False, align=C)

    # ---------------------------------------------------------- backup slides
    for country in ("India", "Australia"):
        response_surface_slide(new, country)

    prs.save(str(OUT))
    print("wrote", OUT, "slides:", len(prs.slides))


# ---------------------------------------------------------------------------
def country_slides(new, country, footnote):
    F = FIGS[country]
    tx = T.COUNTRY[country]
    up = country.upper()

    # where compound months happen + trend
    s = new(L_PLAIN, f"{up}: WHERE AND HOW OFTEN?")
    picture_card(s, F / "freq_map_compound.png", 0.45, 1.2, 6.1 if country == "India" else 6.6, 5.0)
    tr = N.trend(country)
    tops = ", ".join(f"{y} ({v:.1f}%)" for y, v in N.top_years(country))
    cnt = N.counts(country)
    text_box(s, 7.0 if country == "Australia" else 6.8, 1.35, 5.9, 5.2, [
        "Map: share of each cell’s growing-season months that were compound, 2001–2022.",
        f"Overall **{100 * cnt['compound'] / cnt.sum():.1f}%** of growing-season grid-months are compound.",
        *tx["where"],
        f"**H5 (trend 1991–2024)**: {m(tr['slope'])} percentage points per year "
        f"{ci(tr['slope_ci_low'], tr['slope_ci_high'])}, Mann–Kendall {pv(tr['p_value'])}. "
        f"Peak years: {tops}."], size=15, space=10)

    # H1
    s = new(L_PLAIN, f"{up} – H1: HIT HARDER IN COMPOUND MONTHS?")
    picture_card(s, F / "composite_gpp_z_overall.png", 0.8, 1.15, 5.6, 3.5)
    picture_card(s, F / "composite_ndvi_z_overall.png", 6.9, 1.15, 5.6, 3.5)
    rows = [["Mean z [95% CI]", "Normal", "Hot-only", "Dry-only", "Compound"]]
    for resp, lab in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
        c = N.composite(country, resp)
        rows.append([lab] + [m(c.loc["normal", "mean"])] +
                    [f"{m(c.loc[k, 'mean'])} {ci(c.loc[k, 'ci_low'], c.loc[k, 'ci_high'])}" for k in
                     ("hot_only", "dry_only")] +
                    [f"**{m(c.loc['compound', 'mean'])}** {ci(c.loc['compound', 'ci_low'], c.loc['compound', 'ci_high'])}"])
    table(s, rows, 0.75, 4.8, [1.6, 1.3, 2.95, 2.95, 3.0], row_h=0.44, size=14,
          align=[None, C, C, C, C])
    rows2 = []
    for resp, lab in (("gpp_z", "GPP"), ("ndvi_z", "NDVI")):
        rows2.append(f"**{lab}**: compound − dry-only {N.contrast_str(country, resp, 'compound_minus_dry')}; "
                     f"compound − hot-only {N.contrast_str(country, resp, 'compound_minus_hot')}")
    text_box(s, 0.75, 6.2, 12.0, 0.6, [("plain", " · ".join(rows2))], size=11.5, color=CREAM, bullets=False)

    s = new(L_PLAIN, f"{up} – H1: RESULT")
    text_box(s, 0.6, 1.2, 12.1, 3.7, tx["h1"], size=17, space=8)
    mc = N.mech(country)
    table(s, [["", "Normal", "Hot-only", "Dry-only", "Compound"],
              ["Root-zone soil moisture z"] + [m(mc.loc[k, "sm_z"]) for k in N.CATS[:3]] + [f"**{m(mc.loc['compound', 'sm_z'])}**"],
              ["Air dryness (VPD) z"] + [m(mc.loc[k, "vpd_z"]) for k in N.CATS[:3]] + [f"**{m(mc.loc['compound', 'vpd_z'])}**"]],
          1.0, 5.0, [3.9, 1.75, 1.75, 1.75, 1.75], row_h=0.44, size=15, align=[None] + [C] * 4)
    heading(s, 8.8, 6.38, 4.0, 0.5, tx["h1_verdict"], size=26, align=PP_ALIGN.RIGHT)

    # H2 additivity
    s = new(L_PLAIN, f"{up} – H2: WORSE THAN THE SUM?")
    picture_card(s, F / "additivity_gpp_ndvi.png", 0.9, 1.15, 11.5, 4.95)
    footnote(s, "Hatched bar: expected if heat and drought damage simply added up. Green bar: what happened in "
                "compound months. Text: amplification index with 95% CI and bootstrap p-value.", y=6.2)

    # H2 result: AI table + regression
    s = new(L_PLAIN, f"{up} – H2: RESULT (THREE TESTS)")
    rows = [["", "① Amplification index", "② Regression c (heat × dry)", "③ RERI (risk)"]]
    for resp, lab, rl in (("gpp_z", "GPP", "GPP"), ("ndvi_z", "NDVI", "NDVI")):
        for idx, col, spec in (("SPEI-3", "category", "SPEI-3"), ("SPI-3", "category_spi", "SPI-3")):
            r = N.robustness(country, resp, idx)
            g = N.regression(country, rl, spec)
            k = N.risk(country, resp, col, "reri")
            rows.append([f"{lab}, {idx}",
                         f"{m(r['amplification_index'])} {ci(r['amplification_index_ci_low'], r['amplification_index_ci_high'])}  {N.pshort(r['amplification_index_p'])}",
                         f"{m(g['coef'], 3)} {ci(g['ci_low'], g['ci_high'], 3)}  {N.pshort(g['p_value'])}",
                         f"{m(k['estimate'])} {ci(k['ci_low'], k['ci_high'])}  {N.pshort(k['p_value'])}"])
    table(s, rows, 0.55, 1.2, [1.9, 3.55, 3.75, 3.1], row_h=0.5, size=13, align=[None, C, C, C])
    text_box(s, 0.6, 3.85, 12.1, 2.4, tx["h2"], size=15.5, space=7)
    text_box(s, 0.6, 6.25, 12.1, 0.5, [("plain", tx["h2_verdict"])], size=20, bullets=False)

    # H3 recovery
    s = new(L_PLAIN, f"{up} – H3: RECOVERY AFTER EVENTS")
    picture_card(s, F / "recovery_km.png", 0.45, 1.2, 6.2, 4.1)
    k_ = N.km(country)
    rows = [["", "Compound", "Drought-only", "Heat-only"],
            ["Impactful events"] + [n0(k_.loc[e, "n_events"]) for e in ("compound", "drought_only", "heat_only")],
            ["Median recovery (months)"] + [f"{k_.loc[e, 'km_median_rt']:.0f}" for e in ("compound", "drought_only", "heat_only")],
            ["Recovered by 3 months"] + [f"{100 * k_.loc[e, 'p_recovered_by_3m']:.0f}%" for e in ("compound", "drought_only", "heat_only")],
            ["Recovered by 12 months"] + [f"{100 * k_.loc[e, 'p_recovered_by_12m']:.0f}%" for e in ("compound", "drought_only", "heat_only")]]
    table(s, rows, 6.85, 1.25, [2.5, 1.2, 1.3, 1.1], row_h=0.48, size=13, align=[None, C, C, C])
    lr = N.logrank(country)
    lr_cd = lr[(lr["a"] == "compound") & (lr["b"] == "drought_only")].iloc[0]
    cu = N.cox(country, "drought events: compound vs drought-only (adj")
    cs = N.cox(country, "strict compound")
    text_box(s, 6.85, 3.85, 6.1, 2.8, [
        f"Log-rank (events treated as independent): {pv(lr_cd['p_value'])}.",
        f"**Cox model**, adjusted for drought severity and length, errors clustered by year: hazard ratio of "
        f"recovering, compound vs drought-only = **{cu['hazard_ratio']:.2f}** "
        f"[{cu['hr_ci_low']:.2f}, {cu['hr_ci_high']:.2f}], {pv(cu['p_value'])}.",
        f"Stricter rule (≥ 50% of months hot): HR {cs['hazard_ratio']:.2f} "
        f"[{cs['hr_ci_low']:.2f}, {cs['hr_ci_high']:.2f}], {pv(cs['p_value'])}."], size=13.5, space=6)
    text_box(s, 0.6, 5.45, 6.1, 1.2, tx["h3"], size=13.5, space=4)

    # H4
    s = new(L_PLAIN, f"{up} – H4: LAND COVER, REGION, SEASON")
    lc = N.by(country, "gpp_z", "landcover")
    lc = lc[lc["min_category_n"] >= 300].sort_values("mean_compound")
    rows = [["GPP, by land cover", "Compound", "Comp. − dry", "Amplification [95% CI], p"]]
    for r in lc.itertuples():
        rows.append([r.dominant_landcover.replace("_", " "), m(r.mean_compound),
                     f"{m(r.compound_minus_dry)} ({N.pshort(r.compound_minus_dry_p)})",
                     f"{m(r.amplification_index)} {ci(r.amplification_index_ci_low, r.amplification_index_ci_high)}, "
                     f"{N.pshort(r.amplification_index_p)}"])
    table(s, rows, 0.45, 1.2, [1.9, 1.2, 1.75, 3.0], row_h=0.42, size=12.5, align=[None, C, C, C])
    n_lc_rows = len(rows)
    st = N.subregion_test(country)
    import final_numbers as _n
    rows = [["Effect vs normal", "GPP difference", "NDVI difference"]]
    for eff, lab in (("d_hot_only", "hot-only"), ("d_dry_only", "dry-only"), ("d_compound", "compound")):
        g = st[(st["response"] == "gpp_z") & (st["effect"] == eff)].iloc[0]
        n = st[(st["response"] == "ndvi_z") & (st["effect"] == eff)].iloc[0]
        rows.append([lab, f"{m(g['estimate'])}, {N.pshort(g['p_value'])}", f"{m(n['estimate'])}, {N.pshort(n['p_value'])}"])
    text_box(s, 8.65, 1.2, 4.3, 0.4, [("plain", tx["region_label"])], size=12.5, color=YELLOW, bullets=False)
    table(s, rows, 8.65, 1.62, [1.35, 1.45, 1.45], row_h=0.42, size=12, align=[None, C, C])
    text_box(s, 0.6, 1.35 + 0.42 * n_lc_rows + 0.25, 12.1, 2.6, tx["h4"], size=14.5, space=6)

    # case study
    s = new(L_PLAIN, f"{up} – CASE STUDY: {tx['case_title']}")
    picture_card(s, F / f"case_{tx['case']}_category.png", 0.45, 1.2, 5.2 if country == "India" else 6.3, 5.3)
    picture_card(s, F / f"case_{tx['case']}_trajectory.png", 6.0 if country == "India" else 7.0, 1.2,
                 6.9 if country == "India" else 5.9, 2.9)
    text_box(s, 6.0 if country == "India" else 7.0, 4.25, 6.9 if country == "India" else 5.9, 2.4,
             tx["case_text"], size=14, space=5)


def response_surface_slide(new, country):
    F = FIGS[country]
    tx = T.COUNTRY[country]
    up = country.upper()
    s = new(L_PLAIN, f"BACKUP – {up}: H2 RESPONSE SURFACE")
    picture_card(s, F / "response_surface_gpp_explained.png", 0.45, 1.2, 6.5, 5.4)
    heading(s, 7.15, 1.2, 5.8, 0.45, "WHAT YOU ARE LOOKING AT", size=20)
    text_box(s, 7.15, 1.65, 5.85, 2.0, [
        "x = heat (Tmax //z//); y = water balance (SPEI-3, lower = drier).",
        "Each square: average GPP //z// of all grid-months in that range (grey = fewer than 30).",
        "Dashed lines = our cut-offs; bottom-right = compound box."], size=14, space=4)
    heading(s, 7.15, 3.75, 5.8, 0.45, "WHAT WE SEE", size=20)
    text_box(s, 7.15, 4.2, 5.85, 2.4, tx["surface"], size=14, space=5)



# ---------------------------------------------------------------------------
def comparison_slides(new, footnote):
    s = new(L_PLAIN, "H1 SIDE BY SIDE")
    picture_card(s, CMP_FIG / "compare_h1_composites.png", 0.6, 1.15, 12.1, 4.65)
    text_box(s, 0.6, 5.95, 12.1, 0.8, T.CMP_H1, size=14, space=4)

    s = new(L_PLAIN, "H2 SIDE BY SIDE: AMPLIFICATION INDEX")
    picture_card(s, CMP_FIG / "compare_ai_forest.png", 1.2, 1.15, 10.9, 4.65)
    text_box(s, 0.6, 5.95, 12.1, 0.8, T.CMP_H2[:1], size=14.5, space=4)

    s = new(L_PLAIN, "H2 SIDE BY SIDE: REGRESSION")
    picture_card(s, CMP_FIG / "compare_regression_interaction.png", 0.45, 1.15, 8.3, 5.4)
    text_box(s, 8.95, 1.3, 4.0, 5.2, T.CMP_H2_REG, size=14, space=8)

    s = new(L_PLAIN, "WHY IS AUSTRALIA LESS THAN ADDITIVE?")
    picture_card(s, CMP_FIG / "compare_ai_by_productivity.png", 0.45, 1.15, 7.4, 3.9)
    text_box(s, 8.05, 1.3, 4.9, 5.3, T.CMP_MECH, size=14, space=8)

    s = new(L_PLAIN, "IS THE DIFFERENCE BETWEEN COUNTRIES REAL?")
    rows = [["Australia − India", "GPP [95% CI], p", "NDVI [95% CI], p"]]
    for k, lab in (("d_hot", "Heat effect (hot − normal)"), ("d_dry", "Drought effect (dry − normal)"),
                   ("d_compound", "Compound effect"), ("compound_minus_dry", "Compound − dry-only"),
                   ("amplification_index", "Amplification index")):
        cells = [lab]
        for rl in ("GPP", "NDVI"):
            d = N.cdiff(rl, "SPEI-3", k)
            cells.append(f"{m(d['australia_minus_india'])} {ci(d['ci_low'], d['ci_high'])}, {N.pshort(d['p_value'])}")
        rows.append(cells)
    table(s, rows, 0.6, 1.25, [3.9, 4.1, 4.1], row_h=0.5, size=14, align=[None, C, C])
    text_box(s, 0.6, 4.4, 12.1, 2.2, T.CMP_DIFF, size=15, space=7)

    s = new(L_PLAIN, "RISK VIEW: THE CHANCE OF A SEVERE LOSS")
    picture_card(s, CMP_FIG / "compare_risk_reri.png", 1.2, 1.15, 10.9, 4.65)
    text_box(s, 0.6, 5.95, 12.1, 0.8, T.CMP_RISK_RECOVERY[:1], size=14.5, space=4)

    s = new(L_PLAIN, "H3 SIDE BY SIDE: RECOVERY")
    picture_card(s, CMP_FIG / "compare_recovery_km.png", 0.6, 1.15, 12.1, 4.5)
    text_box(s, 0.6, 5.8, 12.1, 0.9, T.CMP_RISK_RECOVERY[1:], size=14.5, space=4)

    s = new(L_PLAIN, "ROBUSTNESS: DOES ANY CHOICE CHANGE THE ANSWER?")
    picture_card(s, CMP_FIG / "compare_sensitivity_ai.png", 0.45, 1.1, 9.05, 3.85 + 1.05)
    text_box(s, 9.7, 1.25, 3.3, 5.3, T.CMP_SENS, size=13.5, space=6)

    s = new(L_PLAIN, "H5: ARE COMPOUND MONTHS BECOMING MORE COMMON?")
    picture_card(s, CMP_FIG / "compare_compound_trend.png", 0.6, 1.15, 12.1, 4.7)
    text_box(s, 0.6, 6.0, 12.1, 0.7, T.CMP_TREND, size=14, space=4)

    s = new(L_PLAIN, "WHICH RESULTS SURVIVE MULTIPLE TESTING?")
    text_box(s, 0.6, 1.25, 12.1, 5.4, T.CMP_FDR, size=15.5, space=8)


if __name__ == "__main__":
    main()
