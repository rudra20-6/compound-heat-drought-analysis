"""Narrative text of the final deck. Numbers are pulled from final_numbers (results CSVs)."""
import final_numbers as N
from final_numbers import m, ci, pv

DATE = "November 2026"


def _ct(c, resp, k):
    return N.contrast_str(c, resp, k)


def _yl(c, resp, test, spec="SPEI-3"):
    return N.yearly(c, resp, spec, test)


WHY_AUSTRALIA = [
    "The mid-term deck ended with an open question: **does India’s “additive, not synergistic” result hold "
    "elsewhere?**",
    "Australia is a strong test: mostly **semi-arid**, dominated by grassland, shrubland and savanna rather than "
    "cropland, and its rain is driven by **El Niño** rather than one monsoon.",
    "Its ecosystems drive much of the year-to-year swing in the global land carbon sink [22, 23], and it has famous "
    "compound years: the **Millennium Drought** (2001–2009) [21] and **2019**, the hottest and driest year on "
    "record [26].",
    "All our datasets are global, so the **same pipeline**, thresholds and statistics run unchanged.",
]

PTEST_BULLETS = [
    "All grid cells in one month share the same weather, so ~10⁵–10⁶ grid-months are **not independent**.",
    "A textbook t-test treats them as independent ⇒ p-values like 10⁻²¹⁹ for tiny differences (right).",
    "**① Year-block bootstrap** (main): resample whole years 10,000 times ⇒ 95% CI and p; p < 0.05 exactly "
    "when the CI excludes 0.",
    "**② Year-level paired tests**: one mean per year (n = 22), paired t-test and Wilcoxon – the most "
    "conservative check.",
    "**③ FDR correction** (Benjamini–Hochberg) for the ~140 tests per country [24].",
    "**④** Regression and Cox models: errors **clustered by year**.",
]

PTEST_SIDE = [
    "Same India difference, three p-values: the naive test says “certain”, the bootstrap says p = 0.011, the "
    "yearly test says p = 0.27.",
    "We report ①; where ② disagrees we say so. A result we call significant survives ① and ③.",
]


def _country_text(c):
    if c == "India":
        y = _yl(c, "gpp_z", "compound - dry_only")
        return dict(
            where=["Hotspots: the northern plains, east-central India, the North-East and a belt in the western "
                   "Deccan (15–18°N)."],
            h1=[
                "All three stress types lower GPP and NDVI significantly below normal (all p < 0.001).",
                "**Compound months are the worst**, significantly worse than either single stress:",
                (1, f"compound − dry-only: GPP {_ct(c, 'gpp_z', 'compound_minus_dry')}; "
                    f"NDVI {_ct(c, 'ndvi_z', 'compound_minus_dry')};"),
                (1, f"compound − hot-only: GPP {_ct(c, 'gpp_z', 'compound_minus_hot')}; "
                    f"NDVI {_ct(c, 'ndvi_z', 'compound_minus_hot')}."),
                f"Strictest test (one value per year): NDVI gaps stay at p < 0.001; GPP compound − dry-only is "
                f"negative in {int(y['years_negative'])}/22 years but {pv(y['p_paired_t'])} – carried by the big "
                f"compound years.",
                "**Why?** Compound months have the driest soils //and// the thirstiest air:",
            ],
            h1_verdict="H1 SUPPORTED.",
            h2=[
                "① Amplification is **never negative**: damages add up; NDVI with SPEI-3 is even slightly "
                "//less// than additive.",
                f"② The GPP interaction hints at synergy, but disappears once curvature terms are added "
                f"(c = {m(N.regression(c, 'GPP', 'SPEI-3 + quadratic terms')['coef'], 3)}, "
                f"{pv(N.regression(c, 'GPP', 'SPEI-3 + quadratic terms')['p_value'])}).",
                f"③ The **risk** of a severe GPP loss rises faster than additive with SPI-3 "
                f"(RERI {m(N.risk(c, 'gpp_z', 'category_spi', 'reri')['estimate'])}, "
                f"{pv(N.risk(c, 'gpp_z', 'category_spi', 'reri')['p_value'])}) – but exactly as additive mean shifts "
                f"crossing the threshold predict ({m(N.reri_bench(c, 'gpp_z', 'SPI-3')['reri_if_means_additive'])}).",
            ],
            h2_verdict="**H2 not supported**: damages add up, in the mean and in the tail.",
            surface=["GPP falls as it gets drier; hot but wet months are not below normal.",
                     "Worst square: the hottest + driest corner.",
                     "⇒ Dryness drives the loss and heat adds to it: additive."],
            h3=["Median recovery ~3 months; ≥ 97% of events recover within a year.",
                "**H3 not supported**: the mid-term “modest support” came from the log-rank test and does not "
                "survive clustering by year."],
            region_label="Peninsular − North (bootstrap)",
            h4=["**No land cover shows synergy.** Damage is largest in shrubland and cropland.",
                "**Forests**: GPP barely drops but NDVI does – MOD17 GPP has no soil-moisture input and is known to "
                "under-respond in forests [25]; Peninsular forests respond asymmetrically [5].",
                "Peninsular greenness is more sensitive to every stress; GPP shows no regional difference. "
                "Compound penalty is largest pre-monsoon (MAM), absent in the monsoon (JJAS).",
                "**H4 supported** (damage size varies; synergy nowhere)."],
            case="2009", case_title="2009 MONSOON DROUGHT",
            case_text=[f"Jun–Sep 2009: {N.case_shares(c, '2009')['compound']:.1f}% of active grid-months compound, "
                       f"{N.case_shares(c, '2009')['hot_only']:.1f}% hot-only.",
                       "The biggest GPP losses came in the hot, dry **pre-monsoon** months (Feb–Apr 2009 and March "
                       "2010), not in the monsoon itself."],
        )
    return AUSTRALIA_TEXT


def _australia_text():
    c = "Australia"
    y = _yl(c, "ndvi_z", "compound - dry_only")
    rq = N.regression(c, "GPP", "SPEI-3 + quadratic terms")
    rs = N.regression(c, "NDVI", "Soil moisture x VPD")
    rk = N.risk(c, "gpp_z", "category_spi", "reri")
    cs = N.case_shares(c, "2019")
    return dict(
        where=["Hotspots: the south-west wheatbelt, the central west and the south-east (Victoria, Riverina); "
               "rarer in the monsoonal north."],
        h1=[
            "All three stress types lower GPP and NDVI far below normal (all p < 0.001); heat alone already "
            f"costs GPP {m(N.overall(c, 'gpp_z')['d_hot'])} z.",
            "**Compound months are the worst**, significantly worse than either single stress:",
            (1, f"compound − dry-only: GPP {_ct(c, 'gpp_z', 'compound_minus_dry')}; "
                f"NDVI {_ct(c, 'ndvi_z', 'compound_minus_dry')};"),
            (1, f"compound − hot-only: GPP {_ct(c, 'gpp_z', 'compound_minus_hot')}; "
                f"NDVI {_ct(c, 'ndvi_z', 'compound_minus_hot')}."),
            f"Strictest test (one value per year): GPP gaps hold in 22/22 and 19/22 years (p < 0.001); NDVI "
            f"compound − dry-only {pv(y['p_paired_t'])}.",
            "**Why?** Again the driest soils //and// the thirstiest air:",
        ],
        h1_verdict="H1 SUPPORTED.",
        h2=[
            "① Amplification is **significantly positive**: compound damage is clearly //less// than heat + "
            "drought added together – the opposite of synergy – with every drought index.",
            f"② The regression agrees (c > 0); with curvature terms GPP c = {m(rq['coef'], 3)}, {pv(rq['p_value'])}. "
            f"Exception: VPD × soil dryness is **synergistic for NDVI** (c = {m(rs['coef'], 3)}, {pv(rs['p_value'])}).",
            f"③ RERI is positive with SPI-3 ({m(rk['estimate'])}, {pv(rk['p_value'])}) but far //below// the "
            f"{m(N.reri_bench(c, 'gpp_z', 'SPI-3')['reri_if_means_additive'])} that additive means would give: "
            "the tail is sub-additive too.",
        ],
        h2_verdict="**H2 rejected**: compound damage is less than additive, in the mean and in the tail.",
        surface=["Both heat and dryness lower GPP; the hot side is already well below normal even when wet.",
                 "Worst square: the hottest + driest corner, but not by as much as the two edges add up.",
                 "⇒ Compound damage saturates: sub-additive."],
        h3=["Median recovery 3 months for all event types; ≥ 89% recover within a year.",
            "**H3 not supported**: no difference after compound events (Cox HR ≈ 1)."],
        region_label="Tropical north − temperate south (bootstrap)",
        h4=["Compound damage is large everywhere (−0.56 to −0.83 in GPP z); **sub-additive in every land cover** "
            "except forest (GPP), where it is additive.",
            "The tropical north and temperate south respond alike (no difference significant at p < 0.05).",
            "Compound penalty is largest in summer (DJF: compound − dry-only −0.61) and absent in winter.",
            "**H4 partly supported**: land cover and season matter; sub-regions do not."],
        case="2019", case_title="2019 HEAT–DROUGHT",
        case_text=[f"Sep–Dec 2019: **{cs['compound']:.0f}%** of active grid-months compound (normal: "
                   f"{cs['normal']:.0f}%).",
                   "Australia-wide GPP z reached −1.71 in December 2019, as the Black Summer fires took hold; "
                   "vegetation recovered within ~3 months once rain returned (Feb–Mar 2020)."],
    )


AUSTRALIA_TEXT = None
COUNTRY = {}


def _init():
    global AUSTRALIA_TEXT
    AUSTRALIA_TEXT = _australia_text()
    COUNTRY["India"] = _country_text("India")
    COUNTRY["Australia"] = AUSTRALIA_TEXT
    _init_comparison()


def _init_comparison():
    g = globals()
    d_hot = N.cdiff("GPP", "SPEI-3", "d_hot")
    d_ai = N.cdiff("GPP", "SPEI-3", "amplification_index")
    d_ai_spi = N.cdiff("GPP", "SPI-3", "amplification_index")
    d_cmd_n = N.cdiff("NDVI", "SPEI-3", "compound_minus_dry")
    g["CMP_H1"] = [
        "**H1 holds in both countries**: compound months are the worst for GPP and NDVI. Australian GPP is hit "
        f"harder by every stress, above all by heat alone ({m(d_hot['australia'])} vs {m(d_hot['india'])}; "
        f"difference {pv(d_hot['p_value'])})."]
    g["CMP_H2"] = [
        "**No synergy in the average damage anywhere**: India is additive, Australia clearly //less// than "
        "additive (both indices, both measures).",
        "The regression tells the same story; the one synergy (NDVI, VPD × soil dryness, Australia) appears only "
        "when stress is measured physically rather than with drought indices – in line with Liang et al. [6]."]
    import pandas as _pd
    ov = _pd.read_csv(N.CMP_RES / "mechanism_overlap.csv").set_index("country")
    te = _pd.read_csv(N.CMP_RES / "ai_by_productivity_tercile.csv")

    def _t(c, t, col="ai"):
        return te[(te["country"] == c) & (te["response"] == "GPP") & (te["gpp_tercile"] == t)].iloc[0][col]
    rg = {c: {k: N.regression(c, "GPP", k) for k in ("SPEI-3", "SPEI-3 + quadratic terms", "Soil moisture x VPD")}
          for c in ("India", "Australia")}
    rn = N.regression("Australia", "NDVI", "Soil moisture x VPD")
    g["CMP_H2_REG"] = [
        "Every month’s actual heat and dryness, no cut-offs; c < 0 = synergy.",
        f"**India**: GPP c = {m(rg['India']['SPEI-3']['coef'], 3)} ({pv(rg['India']['SPEI-3']['p_value'])}), "
        f"→ {m(rg['India']['SPEI-3 + quadratic terms']['coef'], 3)} with curvature terms: additive.",
        f"**Australia**: c > 0 (antagonism) for SPEI-3 (GPP {pv(rg['Australia']['SPEI-3']['p_value'])}).",
        f"Only physical stress shows synergy: Australian NDVI, VPD × soil dryness c = {m(rn['coef'], 3)} "
        f"({pv(rn['p_value'])}) [6]."]
    g["CMP_MECH"] = [
        f"**Overlap**: heat and dryness travel together (correlation of Tmax z and SPEI-3: India "
        f"{m(ov.loc['India', 'corr_tmax_z_spei03'])}, Australia {m(ov.loc['Australia', 'corr_tmax_z_spei03'])}). "
        f"Australia’s “dry-only” months are warm (Tmax z {m(ov.loc['Australia', 'tmax_z_in_dry_only'])} vs "
        f"{m(ov.loc['Australia', 'tmax_z_in_normal'])} normal), so Δhot + Δdry counts part of the damage twice.",
        f"**Floor effect**: in Australia’s least productive third of cells AI = {m(_t('Australia', 'low (driest)'))}; "
        f"in its most productive third {m(_t('Australia', 'high (wettest)'))} – vegetation near its minimum "
        "has little left to lose.",
        f"In India the pattern is weak (AI {m(_t('India', 'low (driest)'))} → {m(_t('India', 'high (wettest)'))}), "
        "consistent with its near-additive result."]
    g["CMP_DIFF"] = [
        f"Australia’s heat penalty is ~3× India’s ({pv(d_hot['p_value'])}); its compound effect is larger too.",
        f"Its amplification index is higher by {m(d_ai['australia_minus_india'])} for GPP with SPEI-3 "
        f"({pv(d_ai['p_value'])}; q = {d_ai['q_bh']:.2f} after FDR) and {m(d_ai_spi['australia_minus_india'])} "
        f"with SPI-3 ({pv(d_ai_spi['p_value'])}; q = {d_ai_spi['q_bh']:.2f}).",
        f"NDVI: compound adds less on top of drought in Australia ({m(d_cmd_n['australia_minus_india'])}, "
        f"{pv(d_cmd_n['p_value'])}).",
        "Same years resampled for both countries (shared ENSO years)."]
    ri, ra = N.risk("India", "gpp_z", "category_spi", "reri"), N.risk("Australia", "gpp_z", "category_spi", "reri")
    ci_ = N.cox("India", "drought events: compound vs drought-only (adj")
    ca_ = N.cox("Australia", "drought events: compound vs drought-only (adj")
    bi, ba = N.reri_bench("India", "gpp_z", "SPI-3"), N.reri_bench("Australia", "gpp_z", "SPI-3")
    g["CMP_RISK_RECOVERY"] = [
        f"RERI > 0 looks like synergy (India {m(ri['estimate'])}, {pv(ri['p_value'])}; Australia "
        f"{m(ra['estimate'])}, {pv(ra['p_value'])}), but chance-of-threshold metrics rise faster than additive even "
        f"when mean effects simply add (◇). Observed − expected: India {m(bi['excess'])} ({pv(bi['excess_p'])}), "
        f"Australia {m(ba['excess'])} ({pv(ba['excess_p'])}) ⇒ **no extra synergy in the tail**.",
        f"**Recovery**: no difference between compound and drought-only events in either country (Cox HR India "
        f"{ci_['hazard_ratio']:.2f}, {pv(ci_['p_value'])}; Australia {ca_['hazard_ratio']:.2f}, "
        f"{pv(ca_['p_value'])}); median ~3 months, almost all recover within a year."]
    g["CMP_SENS"] = [
        "9 choices × 2 measures × 2 countries = 36 amplification indices.",
        "**Not one is significantly negative** (no synergy anywhere).",
        "Australia: positive (sub-additive) in all 18.",
        "India: between additive and mildly sub-additive; sub-additive with stricter thresholds, SPEI-6, a "
        "1-month lag and in 2012–2022.",
        "The H2 answer does not hinge on any single choice."]
    ti, ta = N.trend("India"), N.trend("Australia")
    g["CMP_TREND"] = [
        f"**H5 not supported in either country** at p < 0.05: India {m(ti['slope'])} pp/yr ({pv(ti['p_value'])}), "
        f"Australia {m(ta['slope'])} pp/yr ({pv(ta['p_value'])}). Both records are dominated by single extreme years "
        "(India 2009, Australia 2019). Studies reporting increases for India start in 1951 and use daily heatwaves [3]."]
    pi, pa = N.pvalues("India"), N.pvalues("Australia")
    g["CMP_FDR"] = [
        f"India: {int(pi['sig_p05'].sum())} of {len(pi)} bootstrap tests have p < 0.05; "
        f"**{int(pi['sig_q05'].sum())}** survive FDR correction. Australia: {int(pa['sig_p05'].sum())} of "
        f"{len(pa)}; **{int(pa['sig_q05'].sum())}** survive.",
        "So the headline H1 contrasts and Australia’s sub-additivity are not false alarms from testing many things.",
        "What does **not** survive the stricter checks:",
        (1, "India H3 “slower recovery” (log-rank p = 0.002 → Cox p = 0.30 once events are clustered by year);"),
        (1, "India GPP compound − dry-only on yearly means (p = 0.27; pooled bootstrap p = 0.011);"),
        (1, f"the Australia − India difference in GPP amplification with SPEI-3 (q = {d_ai['q_bh']:.2f})."),
        "Naive tests that treat every grid-month as independent give p ≈ 0 for everything – meaningless."]
    g["SCORECARD"] = [
        ["", "Hypothesis", "India", "Australia"],
        ["**H1**", "Compound worse than either single stress", "**Yes** (GPP vs dry-only weaker)", "**Yes**"],
        ["**H2**", "Synergy: worse than heat + drought added", "No – additive", "No – //less// than additive"],
        ["H2 risk", "…for the chance of a severe loss", "No – as additive means predict", "No – //less// than additive"],
        ["**H3**", "Slower recovery after compound events", "No (p = 0.30)", "No (p = 0.39)"],
        ["**H4**", "Response differs by land cover / region", "Yes (land cover, Peninsula)", "Partly (land cover, season)"],
        ["**H5**", "Compound months becoming more frequent", "No (p = 0.56)", "Not significant (p = 0.10)"]]
    g["SCORECARD_NOTE"] = ("“Yes” = p < 0.05 with the year-block bootstrap or a year-clustered model; the H1/H2 "
                           "contrasts behind it also survive FDR correction (q < 0.05).")
    g["CONCLUSIONS"] = [
        "**Compound heat–drought months are the most damaging months for vegetation in both India and Australia** "
        "(H1), in productivity and in greenness.",
        "But they are **not more than the sum of their parts** on average: additive in India, //less// than additive "
        "in semi-arid Australia, where dryness and heat overlap and stressed vegetation has little left to lose (H2).",
        "The chance of a severe loss rises faster than additive, but only as much as additive mean shifts "
        "crossing a threshold predict – **no hidden synergy in the tail**.",
        "Recovery is quick (median ~3 months) and **no slower after compound events** once correlated events are "
        "handled properly (H3).",
        "Damage size depends on land cover and season (H4); no significant rise in compound frequency since 1991 (H5).",
        "**Method lesson**: with ~10⁶ correlated grid-months, naive p-values are meaningless. Tests that respect "
        "the correlation overturned one mid-term conclusion (H3) and weakened another (India GPP, compound vs dry-only)."]
    g["LIMITATIONS"] = [
        "**MOD17 GPP is partly modelled** (temperature and VPD scalars, no soil moisture), so part of its heat "
        "response is built in; NDVI comes from the same satellite. An independent GPP product (e.g. GOSIF) would help.",
        "**Monthly, 0.25° data** blur short heatwaves and differences within a cell; daily heatwave definitions "
        "could change H5.",
        "**Static land cover** (2021) and no irrigation map: irrigated cropland in India may buffer drought.",
        "**z-scores in drylands**: Australia’s arid interior has small, noisy GPP; sub-additivity weakens but stays "
        "significant in its most productive third of cells.",
        "**Overlap of stresses**: hot-only months are partly dry and dry-only months partly hot (correlation of "
        "Tmax z and SPEI-3 ≈ −0.5), which pushes the amplification index up; the regression and risk views guard "
        "against this.",
        "**Lenient event rule** (any hot month makes a drought compound); the stricter ≥ 50% rule gives the same H3 "
        "answer."]
    g["LITERATURE"] = [
        "**Compound worse than single extremes** (H1): agrees with global syntheses [2] and with India-wide "
        "greenness studies [4].",
        "**Synergy**: Meena et al. [4] report “nonlinear amplification” for India using //probabilities//; we "
        "reproduce a positive RERI, but show it is what additive mean effects already produce once a threshold is "
        "applied – probability metrics can look synergistic when the underlying effects add up.",
        "**Recovery**: global studies report slower recovery after compound events [7, 8], others do not [9]; with "
        "clustered errors we find no difference in either country.",
        "**Soil vs atmospheric drought**: synergy appears only for VPD × soil moisture in Australia, consistent with "
        "the importance of soil-based compound extremes [6].",
        "**What we add**: the same pipeline and statistics on two contrasting countries, formal country-difference "
        "tests, and a demonstration of how much the choice of significance test matters."]


REFERENCES = [
    "P. Ciais et al. Europe-wide reduction in primary productivity caused by the heat and drought in 2003. "
    "Nature 437:529–533, 2005. doi:10.1038/nature03972",
    "J. von Buttlar et al. Impacts of droughts and extreme-temperature events on gross primary production and "
    "ecosystem respiration. Biogeosciences 15:1293–1318, 2018. doi:10.5194/bg-15-1293-2018",
    "S. Sharma, P. Mujumdar. Increasing frequency and spatial extent of concurrent meteorological droughts and "
    "heatwaves in India. Scientific Reports 7:15582, 2017. doi:10.1038/s41598-017-15896-3",
    "A. Meena et al. Nonlinear amplification of vegetation drought under compound dry–hot extremes across India. "
    "Ecological Indicators 191:115617, 2026. doi:10.1016/j.ecolind.2026.115617",
    "D. Sen, D. Barua, J. Monteiro. Quantile-based sensitivity and risk thresholds reveal asymmetric responses of "
    "tropical forest productivity to individual and compound hot–dry extremes. Environ. Res. Commun., 2026. "
    "doi:10.1088/2515-7620/aea1e9",
    "Y. Liang et al. Anthropogenically-driven escalating impact of soil-based compound dry-hot extremes on "
    "vegetation productivity. Nature Communications 17:2303, 2026. doi:10.1038/s41467-026-68878-3",
    "Y. Yao et al. Compound hot–dry events greatly prolong the recovery time of dryland ecosystems. National "
    "Science Review 11:nwae274, 2024. doi:10.1093/nsr/nwae274",
    "M. Huang, P. Zhai. Protracted vegetation recovery after compound drought and hot extreme compared to general "
    "drought. Environ. Res. Lett. 20:024001, 2025. doi:10.1088/1748-9326/ada4c3",
    "X. Feng et al. Divergent vegetation recovery shaped by drought, heat and compound extremes. Communications "
    "Earth & Environment 7:688, 2026. doi:10.1038/s43247-026-03927-9",
    "J. Muñoz-Sabater et al. ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. Earth "
    "Syst. Sci. Data 13:4349–4383, 2021. doi:10.5194/essd-13-4349-2021",
    "S. M. Vicente-Serrano, S. Beguería, J. I. López-Moreno. A multiscalar drought index sensitive to global "
    "warming: the SPEI. Journal of Climate 23:1696–1718, 2010. doi:10.1175/2009JCLI2909.1",
    "C. Funk et al. The climate hazards infrared precipitation with stations – a new environmental record for "
    "monitoring extremes. Scientific Data 2:150066, 2015. doi:10.1038/sdata.2015.66",
    "S. Running, Q. Mu, M. Zhao. MOD17A2H MODIS/Terra Gross Primary Productivity 8-Day L4 Global 500m SIN Grid "
    "V006. NASA EOSDIS LP DAAC, 2015.",
    "S. W. Running et al. A continuous satellite-derived measure of global terrestrial primary production. "
    "BioScience 54:547–560, 2004. doi:10.1641/0006-3568(2004)054[0547:ACSMOG]2.0.CO;2",
    "K. Didan. MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid V061 (MOD13A3). NASA EOSDIS LP DAAC, "
    "2021.",
    "D. Zanaga et al. ESA WorldCover 10 m 2021 v200. Zenodo, 2022. doi:10.5281/zenodo.7254221",
    "N. Gorelick et al. Google Earth Engine: planetary-scale geospatial analysis for everyone. Remote Sensing of "
    "Environment 202:18–27, 2017. doi:10.1016/j.rse.2017.06.031",
    "T. J. VanderWeele, M. J. Knol. A tutorial on interaction. Epidemiologic Methods 3:33–72, 2014. "
    "doi:10.1515/em-2013-0005",
    "D. R. Cox. Regression models and life-tables. J. Royal Statistical Society B 34:187–202, 1972. "
    "doi:10.1111/j.2517-6161.1972.tb00899.x",
    "M. M. Boer, V. Resco de Dios, R. A. Bradstock. Unprecedented burn area of Australian mega forest fires. "
    "Nature Climate Change 10:171–172, 2020. doi:10.1038/s41558-020-0716-1",
    "A. I. J. M. van Dijk et al. The Millennium Drought in southeast Australia (2001–2009). Water Resources "
    "Research 49:1040–1057, 2013. doi:10.1002/wrcr.20123",
    "B. Poulter et al. Contribution of semi-arid ecosystems to interannual variability of the global carbon cycle. "
    "Nature 509:600–603, 2014. doi:10.1038/nature13376",
    "X. Ma et al. Drought rapidly diminishes the large net CO2 uptake in 2011 over semi-arid Australia. Scientific "
    "Reports 6:37747, 2016. doi:10.1038/srep37747",
    "Y. Benjamini, Y. Hochberg. Controlling the false discovery rate. J. Royal Statistical Society B 57:289–300, "
    "1995. doi:10.1111/j.2517-6161.1995.tb02031.x",
    "M. Flach et al. Vegetation modulates the impact of climate extremes on gross primary production. "
    "Biogeosciences 18:39–53, 2021. doi:10.5194/bg-18-39-2021",
    "Bureau of Meteorology. Annual Climate Statement 2019. Australian Government, Melbourne, 2020.",
]
