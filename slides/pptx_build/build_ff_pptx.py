"""Build slides/ff_themed.pptx: slides/ff.tex in the "Africa Viva" theme
(same helpers and title-slide India map as build_pptx.py).

Run with a Python that has python-pptx:  python slides/pptx_build/build_ff_pptx.py
"""
from build_pptx import *  # noqa: F401,F403  (helpers, colours, layout indices)
from build_pptx import (ROOT, TEMPLATE, FIG, put_india_on_title_layout, set_title, waves, page_no,
                        text_box, heading, drop_placeholders, rect, box_text, arrow, picture_card,
                        table, add_runs)

OUT = ROOT / "slides" / "ff_themed.pptx"


def main():
    prs = Presentation(str(TEMPLATE))
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)
    put_india_on_title_layout(prs)
    lay = prs.slide_layouts
    page = [0]

    def new(layout_idx, title=None, number=True, num_color=MAROON, **tkw):
        s = prs.slides.add_slide(lay[layout_idx])
        page[0] += 1
        if layout_idx == L_PLAIN:
            tkw.setdefault("box", (0.45, 0.2, 12.43, 0.9))
            tkw.setdefault("size", 36)
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

    # ------------------------------------------------------------- title
    s = new(L_TITLE, number=False)
    set_title(s, "COMPOUND HEAT–DROUGHT STRESS OVER INDIA", size=56, align=PP_ALIGN.RIGHT,
              box=(6.9, 0.4, 6.0, 3.3))
    sub = s.placeholders[1]
    sub.left, sub.top, sub.width, sub.height = I(7.45), I(3.75), I(5.45), I(1.7)
    tf = sub.text_frame
    tf.word_wrap = True
    for k, (txt, size, col, before) in enumerate([
            ("Are ecosystems hit harder when heat and drought strike together?", 17, YELLOW, 0),
            ("Mid-Evaluation, EVS Project", 14, WHITE, 4),
            ("Arnav Deshmukh · Ayush Brajesh Roy · Saksham Chitkara", 13, WHITE, 8),
            ("Gracy Garg · Rudra Choudhary", 13, WHITE, 0),
            ("IIIT Hyderabad · October 9, 2026", 13, WHITE, 0)]):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.RIGHT
        p.space_before = Pt(before)
        add_runs(p, txt, size, col)

    # -------------------------------------------------------------- outline
    secs = [("01", "Problem statement & motivation"), ("02", "Our hypotheses"),
            ("03", "Methodology"), ("04", "Preliminary analysis (H1, H2)"),
            ("05", "Things left to do")]
    s = new(L_TOC, "OUTLINE")
    drop_placeholders(s)
    for k, (n, t) in enumerate(secs):
        y = 0.75 + k * 1.2
        heading(s, 6.3, y, 1.2, 0.9, n, size=48, color=ORANGE)
        heading(s, 7.55, y + 0.2, 5.4, 0.6, t.upper(), size=26, color=RED1)

    def section(k):
        num, title = secs[k]
        s = new(L_SECTION, title.upper(), number=False, size=50, align=PP_ALIGN.CENTER,
                box=(1.2, 2.05, 10.93, 1.9))
        drop_placeholders(s)
        s.shapes.title.text_frame.vertical_anchor = MSO_ANCHOR.TOP
        # big yellow number behind the title, as in the template
        nb = text_box(s, 3.2, 0.1, 6.93, 2.7, [("plain", num)], size=170, color=YELLOW,
                      bullets=False, align=PP_ALIGN.CENTER, font=HEAD_FONT)
        s.shapes._spTree.remove(nb._element)
        s.shapes._spTree.insert(2, nb._element)

    # ---------------------------------------------------- problem statement
    section(0)
    s = new(L_YELLOW, "PROBLEM STATEMENT", num_color=WHITE, box=(0.7, 0.35, 11.9, 0.85),
            align=PP_ALIGN.CENTER)
    drop_placeholders(s)
    s.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = MAROON
    heading(s, 0.7, 1.35, 11.9, 1.3,
            "COMPOUND HEAT–DROUGHT STRESS: ARE ECOSYSTEMS EXPERIENCING STRONGER COMBINED IMPACTS?",
            size=32, color=RED2, align=PP_ALIGN.CENTER)
    text_box(s, 1.2, 2.85, 10.9, 0.9, [("plain",
        "Does simultaneous heat and drought produce greater ecosystem stress than either disturbance "
        "alone?")], size=22, color=MAROON, bullets=False, align=PP_ALIGN.CENTER)
    blk = rect(s, 2.2, 3.95, 8.9, 0.75, MAROON, radius=0.2)
    box_text(blk, ["Compare productivity and recovery during compound and single-stressor events."],
             17, WHITE)

    # ------------------------------------------ heat and drought rarely alone
    s = new(L_PLAIN, "HEAT AND DROUGHT RARELY COME ALONE")
    text_box(s, 0.6, 1.4, 5.6, 5.3, [
        "**Drought**: a shortage of water – little rain, so the soil dries and roots cannot supply "
        "the plant.",
        "**Heatwave**: unusually high temperature. Hot air is “thirstier” (higher VPD) and pulls water "
        "out of leaves.",
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

    # ---------------------------------------- how heat and drought affect plants
    s = new(L_PLAIN, "HOW HEAT AND DROUGHT AFFECT PLANTS?")
    text_box(s, 0.6, 1.25, 12.1, 5.6, [
        "Plants take up carbon by photosynthesis. The total amount is **gross primary productivity "
        "(GPP)** – the base of food production.",
        "Leaves have tiny pores (**stomata**): CO₂ enters through them, and water escapes through the "
        "same pores.",
        "Under heat //and// drought, plants are squeezed from both sides:",
        (1, "**drought**: less water in the soil, so roots cannot supply the leaves;"),
        (1, "**heat**: the air demands more water, so stomata close ⇒ less CO₂ uptake ⇒ lower GPP;"),
        (1, "with no water to evaporate, leaves cannot cool themselves and overheat."),
        "Past events:",
        (1, "**Europe, summer 2003**: record heat with drought cut plant productivity by ~30%."),
        (1, "**India, 2009**: the monsoon brought ~22% less rain than normal alongside above-normal "
            "temperatures; crops and natural vegetation browned across north and central India and the "
            "summer (kharif) harvest fell sharply.")], size=19, space=9)

    # ------------------------------------------------------------ hypotheses
    section(1)
    s = new(L_PLAIN, "OUR HYPOTHESES")
    table(s, [
        ["", "Hypothesis", "Status"],
        ["**H1**", "GPP and NDVI are lower in compound months than in hot-only or dry-only months.", "**Tested**"],
        ["**H2**", "The compound effect is //synergistic//: larger than heat effect + drought effect.", "**Tested**"],
        ["**H3**", "Recovery is slower after compound events than after droughts.", "Final eval"],
        ["**H4**", "The response differs by land cover and region (Peninsular vs North).", "Final eval"]],
        0.6, 1.6, [0.9, 9.1, 2.1], row_h=0.85, size=18)

    # -------------------------------------------------------------- workflow
    section(2)
    s = new(L_TIMELINE, "WORKFLOW", box=(0.7, 0.3, 11.9, 0.95), align=PP_ALIGN.CENTER)
    drop_placeholders(s)
    steps = [("STEP 1", "Download & aggregate data (Earth Engine)"),
             ("STEP 2", "Monthly anomalies (z) and sort each month: normal / hot / dry / compound"),
             ("STEP 3", "Compare GPP & NDVI across the four boxes (H1, H2)")]
    bw, gap, x0, y0, bh = 3.4, 0.6, 0.95, 1.6, 1.75
    for k, (h, t) in enumerate(steps):
        x = x0 + k * (bw + gap)
        b = rect(s, x, y0, bw, bh, [RED2, ORANGE, YELLOW][k])
        box_text(b, [f"**{h}**", t], 17, MAROON if k == 2 else WHITE)
        if k < 2:
            arrow(s, x + bw + 0.05, y0 + bh / 2, x + bw + gap - 0.05, y0 + bh / 2, color=YELLOW, width=3)
    x3 = x0 + 2 * (bw + gap)
    e = rect(s, x3, y0 + bh + 0.38, bw, 1.25, CARD, line=YELLOW, line_w=1.25)
    box_text(e, ["Events & recovery (H3),", "land cover & region (H4)", "//final evaluation//"], 15, WHITE)
    arrow(s, x3 + bw / 2, y0 + bh + 0.04, x3 + bw / 2, y0 + bh + 0.34, color=YELLOW, width=3)
    text_box(s, 0.95, 3.8, 7.4, 1.0, [("plain",
        "Everything is scripted in Python (xarray, numpy, scipy) and checked by automated tests. "
        "The analysis reruns from cached data in minutes.")], size=16, color=CREAM, bullets=False)

    # ------------------------------------------------------------------ data
    s = new(L_BULLETS, "DATA", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.35, 9.3, 0.5, [("plain",
        "All data put on one grid: boxes ~27 km wide (0.25°), one value per month, 4,481 boxes inside "
        "India.")], size=16, bullets=False, color=CREAM)
    text_box(s, 0.75, 1.95, 9.3, 3.6, [
        "**ERA5-Land** (1991–2024): reconstructed daily weather; its maximum temperature tells us which "
        "months are //hot//.",
        "**SPEI** (1991–2024): a ready-made drought index; tells us which months are //dry//.",
        "**CHIRPS** (1991–2024): rainfall from satellites and rain gauges; gives a second, rain-only "
        "drought check.",
        "**MODIS GPP** (2001–2022): satellite estimate of plant photosynthesis; our main measure of "
        "plant health.",
        "**MODIS NDVI** (2001–2022): satellite greenness; our second measure of plant health.",
        "**ESA WorldCover** (2021): land-cover map; tells us forest, cropland, shrubland or grassland, "
        "and removes non-vegetated areas."], size=15.5, space=5)

    # --------------------------------------------------------------- metrics
    s = new(L_PLAIN, "METRICS AT A GLANCE")
    table(s, [
        ["Metric", "What it measures", "How to read it"],
        ["Ecosystem response", "", ""],
        ["GPP", "Carbon taken up by plants through photosynthesis (gC/m²/month)", "higher = more productive"],
        ["NDVI", "Canopy greenness from red and near-infrared reflectance (0–1)", "higher = greener"],
        ["Stress", "", ""],
        ["Tmax z", "Anomaly of the monthly mean daily maximum temperature", "≥ 1: “hot” month"],
        ["SPEI-3", "3-month water balance: rain minus evaporative demand", "≤ −1: “dry” month"],
        ["SPI-3", "3-month rainfall only (no temperature in it)", "≤ −1: dry (robustness)"],
        ["Soil moisture", "Water in the top 1 m of soil", "lower = drier soil"],
        ["VPD", "Vapour-pressure deficit: how “thirsty” the air is", "higher = more water stress"],
        ["Statistics", "", ""],
        ["z-score", "Distance from normal for that place and calendar month (in SDs)", "0 = normal; −1 = clearly low"],
        ["Amplification", "Compound effect − (heat effect + drought effect)", "< 0 synergy; ≈ 0 additive"],
        ["95% CI", "Year-block bootstrap: 1,000 resamples of whole years", "excludes 0 = significant"]],
        0.6, 1.2, [2.1, 6.7, 3.3], row_h=0.395, size=14.5, section_rows=(1, 4, 10))

    # ------------------------------------------------- method: four categories
    s = new(L_PLAIN, "METHOD: FOUR STRESS CATEGORIES")
    text_box(s, 0.6, 1.3, 6.6, 5.5, [
        "**Why z-scores?** Raw values cannot be compared: May is always hotter than January, and deserts "
        "always have less GPP than forests.",
        "**Hot**: the month’s average daily maximum temperature (Tmax z) ≥ 1.",
        "**Dry**: **SPEI-3** ≤ −1, meaning the last 3 months had clearly less water than usual (rain "
        "minus evaporative demand).",
        "Each of the 824,598 growing-season grid-months falls into one of four boxes: normal, hot-only, "
        "dry-only or compound.",
        "**SPEI**’s demand term depends on temperature, so “dry” is partly driven by heat; we therefore "
        "repeat everything with **SPI-3**, which uses rainfall only."], size=16, space=9)
    gx, gy, cw, chh = 9.0, 2.05, 1.9, 1.05
    for j, lab in enumerate(["SPEI-3 > −1", "SPEI-3 ≤ −1"]):
        text_box(s, gx + j * cw, gy - 0.45, cw, 0.4, [("plain", lab)], size=14, color=YELLOW,
                 bullets=False, align=PP_ALIGN.CENTER, font=HEAD_FONT)
    for i, lab in enumerate(["Tmax z < 1", "Tmax z ≥ 1"]):
        text_box(s, gx - 1.55, gy + i * chh, 1.5, chh, [("plain", lab)], size=14, color=YELLOW,
                 bullets=False, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, font=HEAD_FONT)
    cells = [[("Normal", "573,543"), ("Dry-only", "109,073")],
             [("Hot-only", "79,717"), ("**Compound**", "**62,265** (7.6%)")]]
    fills = [[CARD, ORANGE], [RED2, YELLOW]]
    for i in range(2):
        for j in range(2):
            b = rect(s, gx + j * cw + 0.04, gy + i * chh + 0.04, cw - 0.08, chh - 0.08, fills[i][j], radius=0.1)
            box_text(b, list(cells[i][j]), 15, MAROON if (i, j) == (1, 1) else WHITE, em=MAROON)
    text_box(s, gx - 1.55, gy + 2 * chh + 0.15, 1.55 + 2 * cw, 0.6, [("plain",
        "Number of growing-season grid-months in each box, India, 2001–2022.")], size=12, color=CREAM,
        bullets=False, align=PP_ALIGN.CENTER)

    # --------------------------------------------------- step 3: how we test
    s = new(L_PLAIN, "STEP 3: HOW WE TEST H1 AND H2")
    text_box(s, 0.6, 1.25, 12.1, 1.5, [
        "**H1**: average GPP //z// (and NDVI //z//) in each box, and the differences between boxes.",
        "**H2**: compare the compound effect with the sum of the single effects. Each effect is measured "
        "relative to normal months:"], size=20, space=8)
    eq = rect(s, 2.9, 2.75, 7.5, 0.8, CARD, line=YELLOW, line_w=1)
    box_text(eq, ["Amplification = Δ_{compound} − (Δ_{hot} + Δ_{dry})"], 24, WHITE)
    text_box(s, 0.6, 3.75, 12.1, 3.2, [
        (1, "< 0: compound is worse than the sum ⇒ **synergy**;"),
        (1, "≈ 0: **additive**;"),
        (1, "> 0: less than the sum (**sub-additive**)."),
        "**Uncertainty**: 95% confidence intervals from a //year-block bootstrap//. We resample whole "
        "years (1,000 times), because neighbouring cells in the same year are not independent. A result "
        "is called significant when its interval excludes zero."], size=20, space=10)

    # --------------------------------------------------- where compound months
    section(3)
    s = new(L_PLAIN, "WHERE COMPOUND MONTHS HAPPEN")
    picture_card(s, FIG / "freq_map_compound.png", 0.55, 1.25, 6.2, 5.5)
    text_box(s, 7.0, 1.45, 5.9, 5.2, [
        "Share of each cell’s growing-season months that were compound, 2001–2022.",
        "Overall, 7.6% of growing-season grid-months are compound.",
        "Hotspots: the northern plains, east-central India, the North-East, and a belt in the western "
        "Deccan (around 15–18°N).",
        "Both North and Peninsular India have more than 20,000 compound grid-months, enough for a "
        "reliable comparison."], size=20, space=18)

    # ------------------------------------------------------------------- H1
    s = new(L_PLAIN, "H1: IS VEGETATION HIT HARDER IN COMPOUND MONTHS?")
    picture_card(s, FIG / "composite_gpp_z_overall.png", 0.8, 1.2, 5.6, 3.6)
    picture_card(s, FIG / "composite_ndvi_z_overall.png", 6.9, 1.2, 5.6, 3.6)
    table(s, [
        ["Mean z [95% CI]", "Normal", "Hot-only", "Dry-only", "Compound"],
        ["GPP", "+0.12", "−0.13 [−0.24, −0.01]", "−0.27 [−0.40, −0.15]", "**−0.43** [−0.54, −0.33]"],
        ["NDVI", "+0.19", "−0.37 [−0.50, −0.26]", "−0.30 [−0.41, −0.21]", "**−0.68** [−0.81, −0.55]"]],
        0.75, 4.95, [2.2, 1.3, 2.7, 2.7, 2.95], row_h=0.48, size=15,
        align=[None, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER])

    s = new(L_PLAIN, "H1: RESULT")
    text_box(s, 0.6, 1.2, 12.1, 3.9, [
        "All three stress types lower productivity and greenness significantly compared with normal months.",
        "**Compound months are the worst**, and significantly worse than either single stress:",
        (1, "compound minus dry-only: GPP −0.16 [−0.26, −0.04], NDVI −0.38 [−0.49, −0.28];"),
        (1, "compound minus hot-only: GPP −0.30 [−0.40, −0.21], NDVI −0.31 [−0.43, −0.21]."),
        "Robust to the drought index. With rainfall-only SPI-3, compound minus dry-only is GPP −0.26 "
        "[−0.37, −0.13] and NDVI −0.48 [−0.61, −0.35].",
        "**Why?** Compound months combine the driest soils //and// the thirstiest air:"],
        size=18, space=8)
    table(s, [
        ["", "Normal", "Hot-only", "Dry-only", "Compound"],
        ["Root-zone soil moisture z", "+0.29", "−0.75", "−0.38", "**−1.04**"],
        ["Air dryness (VPD) z", "−0.38", "+1.11", "+0.18", "**+1.43**"]],
        1.0, 5.05, [3.9, 1.75, 1.75, 1.75, 1.75], row_h=0.46, size=16,
        align=[None] + [PP_ALIGN.CENTER] * 4)
    heading(s, 9.3, 6.35, 3.5, 0.55, "H1 SUPPORTED.", size=28, align=PP_ALIGN.RIGHT)

    # ------------------------------------------------------------------- H2
    s = new(L_PLAIN, "H2: IS THE COMBINATION WORSE THAN THE SUM?")
    picture_card(s, FIG / "additivity_gpp_ndvi.png", 0.9, 1.2, 11.5, 4.95)
    text_box(s, 0.9, 6.25, 11.5, 0.5, [("plain",
        "Hatched bar: what we would expect if the two damages simply added up. Green bar: what "
        "actually happened in compound months.")], size=14, color=CREAM, bullets=False,
        align=PP_ALIGN.CENTER)

    s = new(L_PLAIN, "H2: RESULT")
    text_box(s, 0.6, 1.3, 5.9, 0.9, [("plain",
        "Amplification = Δ_{compound} − (Δ_{hot} + Δ_{dry}); < 0 would mean synergy.")],
        size=20, bullets=False)
    table(s, [
        ["", "with SPEI-3", "with SPI-3"],
        ["GPP", "+0.09", "−0.00"],
        ["", "[−0.03, +0.21]", "[−0.12, +0.13]"],
        ["NDVI", "+0.18", "+0.06"],
        ["", "[+0.06, +0.30]", "[−0.05, +0.18]"]],
        0.8, 2.6, [1.4, 2.25, 2.25], row_h=0.62, size=19,
        align=[None, PP_ALIGN.CENTER, PP_ALIGN.CENTER], body_fill=(CARD, CARD))
    text_box(s, 6.9, 1.3, 6.0, 4.5, [
        "**No synergy**: the amplification is never significantly negative.",
        "Heat and drought damages roughly **add up**. Compound months are worse than either alone, but "
        "not worse than both together.",
        "With SPEI-3, NDVI is even slightly //less// than additive, but this disappears with SPI-3. "
        "**The drought definition matters.**"], size=20, space=18)
    text_box(s, 0.6, 6.1, 12.1, 0.6, [("plain",
        "**H2 not supported** (for average productivity, India-wide).")], size=24, bullets=False)

    s = new(L_PLAIN, "H2: RESPONSE SURFACE (A CHECK WITHOUT BOXES)")
    picture_card(s, FIG / "response_surface_gpp_explained.png", 0.45, 1.2, 6.5, 5.6)
    heading(s, 7.15, 1.2, 5.8, 0.45, "WHAT YOU ARE LOOKING AT", size=20)
    text_box(s, 7.15, 1.65, 5.85, 2.3, [
        "x = heat (Tmax //z//); y = water balance (SPEI-3, lower = drier).",
        "Each square: average GPP //z// of all grid-months in that range (red = below normal; grey = "
        "fewer than 30 grid-months).",
        "Dashed lines = our cut-offs; bottom-right = the compound box."], size=15, space=5)
    heading(s, 7.15, 4.1, 5.8, 0.45, "WHAT WE SEE", size=20)
    text_box(s, 7.15, 4.55, 5.85, 2.4, [
        "GPP falls as it gets drier: about +0.5 in the wettest rows, −0.35 in the driest.",
        "Worst square: hottest + driest corner (−0.92). Hot but wet months are not below normal.",
        "⇒ Dryness is the main driver and heat adds to it, consistent with additive effects."],
        size=15, space=5)

    # ----------------------------------------------------------- observations
    s = new(L_BULLETS, "OBSERVATIONS SO FAR", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.5, 9.2, 4.0, [
        "**H1 supported.** Compound heat–drought months reduce productivity (GPP) and greenness (NDVI) "
        "significantly more than heat alone or drought alone. This holds for both drought indices.",
        "**H2 not supported.** The compound effect is about the //sum// of the heat and drought effects, "
        "not more.",
        "**Mechanism.** Compound months have the driest soils and the thirstiest air at the same time.",
        "**Drought definition matters.** SPEI vs SPI changes the H2 details. Hot-only months also have "
        "dry soils (soil moisture z = −0.75), which rainfall-based indices miss."], size=17, space=10)

    # --------------------------------------------------------- improving H2
    section(4)
    s = new(L_TWO, "IMPROVING H2: REGRESSION INSTEAD OF FOUR BOXES", box=(0.7, 0.3, 11.9, 0.85),
            align=PP_ALIGN.LEFT, size=36)
    drop_placeholders(s)
    rect(s, 0.7, 1.3, 11.9, 1.35, CARD, line=YELLOW, line_w=1)
    text_box(s, 0.95, 1.36, 11.4, 0.4, [("plain", "WHY AND WHAT")], size=18, color=YELLOW, bullets=False,
             font=HEAD_FONT)
    text_box(s, 0.95, 1.73, 11.4, 0.9, [("plain",
        "The four boxes use fixed cut-offs (±1) and ignore how strong each anomaly is. So, by the final "
        "submission, we will move from four boxes to a **regression fitted to every month’s actual heat "
        "and dryness values**.")], size=16.5, bullets=False)
    text_box(s, 0.7, 2.8, 11.9, 0.55, [("plain",
        "GPP = //a// × heat + //b// × dryness + //c// × (heat × dryness)")], size=22, color=YELLOW,
        bullets=False, align=PP_ALIGN.CENTER)
    text_box(s, 0.9, 3.45, 9.5, 1.3, [
        "//a//, //b//: how much GPP drops per unit of heat or dryness on its own",
        "//c// < 0 ⇒ heat hurts more when it is also dry (synergy)",
        "One direct test with a confidence interval, and no arbitrary cut-offs"], size=17, space=4)

    # ----------------------------------------------------------- further work
    s = new(L_TEAM, "FURTHER WORK")
    drop_placeholders(s)
    cols = [("H3: RECOVERY", ["Time for vegetation to recover after each event",
                              "Compound vs drought-only at the same drought severity"]),
            ("H4: LAND COVER & REGION", ["Forests, croplands, grasslands", "Peninsular vs North India"]),
            ("BEYOND INDIA", ["Repeat the analysis for another country",
                              "Does India’s “additive” result hold elsewhere?"])]
    for k, (h, its) in enumerate(cols):
        x = 1.0 + k * 3.85
        heading(s, x, 1.35, 3.6, 0.5, h, size=22, align=PP_ALIGN.LEFT)
        text_box(s, x, 1.95, 3.6, 1.9, its, size=17, space=8)
    text_box(s, 1.0, 3.95, 11.3, 0.5, [("plain",
        "All our datasets cover the globe (CHIRPS: 50°S–50°N), so the same pipeline can be pointed at "
        "a new region.")], size=15, color=CREAM, bullets=False)

    prs.save(str(OUT))
    print("wrote", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
