"""Build slides/midsub_v4_themed.pptx: the midsub_v4 deck in the
"Africa Viva" (SlidesMania) theme, with the title-slide Africa map replaced by
India.

Run with a Python that has python-pptx and lxml (here: C:/Python313/python.exe):
    python slides/pptx_build/build_pptx.py
Inputs : Africa Viva template (midSub/), figures/*.png,
         slides/pptx_build/india_outline_gaul.json (FAO GAUL 2015 level 0:
         India + Jammu and Kashmir + Aksai Chin + Arunachal Pradesh + China/India,
         i.e. India's official outline; fetched from Earth Engine).
Content: identical to slides/midsub_v4.tex (same text, numbers and citations).
"""
import json
import math
import re
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # midSub/
TEMPLATE = ROOT / "Africa Viva · SlidesMania.pptx"
FIG = ROOT / "figures"
OUT = ROOT / "slides" / "midsub_v4_themed.pptx"

# theme colours (theme2.xml of the template)
MAROON = RGBColor(0x37, 0x07, 0x17)
RED1 = RGBColor(0x6A, 0x04, 0x0F)
RED2 = RGBColor(0x9D, 0x02, 0x08)
ORANGE = RGBColor(0xDA, 0x62, 0x16)
ORANGE2 = RGBColor(0xF4, 0x8C, 0x05)
GOLD = RGBColor(0xFA, 0xA3, 0x06)
YELLOW = RGBColor(0xFF, 0xBA, 0x07)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM = RGBColor(0xFF, 0xF4, 0xE0)
CARD = RGBColor(0x52, 0x10, 0x22)         # slightly lighter maroon for cards
CARD2 = RGBColor(0x45, 0x0C, 0x1C)
GREEN = RGBColor(0x5E, 0xA1, 0x3A)
OLIVE = RGBColor(0x9C, 0x8A, 0x3A)

BODY_FONT = "Epilogue"
HEAD_FONT = "Impact"

L_TITLE, L_TOC, L_SECTION, L_TWO, L_BULLETS, L_TEAM, L_TIMELINE, L_YELLOW, L_PLAIN = 0, 3, 4, 5, 6, 8, 10, 11, 13

I = Inches


# ----------------------------------------------------------------- text tools
TOKEN = re.compile(r"(\*\*.+?\*\*|//.+?//|_\{.+?\}|\^\{.+?\})")


def add_runs(p, text, size, color, em_color=None, bold=False, italic=False, font=BODY_FONT):
    """Mini-markup: **bold (em colour)**, //italic//, _{sub}, ^{sup}."""
    em_color = em_color or color
    for tok in TOKEN.split(text):
        if not tok:
            continue
        r_bold, r_italic, r_color, base, t = bold, italic, color, 0, tok
        if tok.startswith("**"):
            t, r_bold, r_color = tok[2:-2], True, em_color
        elif tok.startswith("//"):
            t, r_italic = tok[2:-2], True
        elif tok.startswith("_{"):
            t, base = tok[2:-1], -25000
        elif tok.startswith("^{"):
            t, base = tok[2:-1], 30000
        # allow //italic// inside **bold** and vice versa (one level)
        inner = TOKEN.split(t) if (tok.startswith("**") or tok.startswith("//")) and TOKEN.search(t) else None
        if inner:
            add_runs(p, t, size, r_color, em_color, r_bold, r_italic, font)
            continue
        r = p.add_run()
        r.text = t
        f = r.font
        f.size = Pt(size)
        f.bold = r_bold
        f.italic = r_italic
        f.name = font
        f.color.rgb = r_color
        if base:
            r._r.get_or_add_rPr().set("baseline", str(base))


def set_bullet(p, level, kind, size, color, indent_in=0.28):
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:buClr", "a:buSzPct", "a:buFont", "a:buNone", "a:buChar", "a:buAutoNum"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    if kind is None:
        pPr.set("marL", str(int(I(indent_in * level))))
        pPr.set("indent", "0")
        etree.SubElement(pPr, qn("a:buNone"))
        return
    mar = I(indent_in * (level + 1))
    pPr.set("marL", str(int(mar)))
    pPr.set("indent", str(int(-I(indent_in * 0.85))))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", str(color))
    if kind == "num":
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", "+mj-lt")
        etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
    else:
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
        etree.SubElement(pPr, qn("a:buChar")).set("char", "•" if level == 0 else "–")


def text_box(slide, x, y, w, h, items, size=16, color=WHITE, em=YELLOW, bullets=True,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6, font=BODY_FONT,
             bold=False, line=1.0, num=False, bullet_color=None):
    """items: list of str (level 0) or (level, str) or ('plain', str)."""
    tb = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, I(0.03))
    first = True
    for it in items:
        level, txt, plain = 0, it, not bullets
        if isinstance(it, tuple):
            if it[0] == "plain":
                txt, plain = it[1], True
            else:
                level, txt = it
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space)
        if line != 1.0:
            p.line_spacing = line
        bsize = size if level == 0 else size - 1
        set_bullet(p, level, None if plain else ("num" if num and level == 0 else "dot"), bsize,
                   bullet_color or (YELLOW if color == WHITE else RED2))
        add_runs(p, txt, bsize, color, em, bold=bold, font=font)
    return tb


def heading(slide, x, y, w, h, txt, size=24, color=YELLOW, align=PP_ALIGN.LEFT):
    return text_box(slide, x, y, w, h, [txt], size=size, color=color, em=color, bullets=False,
                    align=align, font=HEAD_FONT, space=0)


def set_title(slide, txt, size=None, color=None, align=None, box=None):
    t = slide.shapes.title
    if box:
        t.left, t.top, t.width, t.height = (I(v) for v in box)
    t.text = txt
    p = t.text_frame.paragraphs[0]
    if align is not None:
        p.alignment = align
    for r in p.runs:
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color
    return t


def drop_placeholders(slide, keep_title=True):
    for ph in list(slide.placeholders):
        if keep_title and ph.placeholder_format.type in (1, 3):  # TITLE / CENTER_TITLE
            continue
        ph._element.getparent().remove(ph._element)


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08,
         line_w=1.5):
    s = slide.shapes.add_shape(shape, I(x), I(y), I(w), I(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def box_text(shape, items, size, color, em=None, align=PP_ALIGN.CENTER, font=BODY_FONT, bold=False):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for side in ("margin_left", "margin_right"):
        setattr(tf, side, I(0.08))
    first = True
    for txt in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        add_runs(p, txt, size, color, em or color, bold=bold, font=font)


def arrow(slide, x1, y1, x2, y2, color=YELLOW, width=2.5):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(x1), I(y1), I(x2), I(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return c


def picture_card(slide, path, x, y, w, h, pad=0.08, card=WHITE):
    """Picture fitted (aspect kept) inside x,y,w,h on a white rounded card."""
    from PIL import Image
    iw, ih = Image.open(path).size
    s = min((w - 2 * pad) / iw, (h - 2 * pad) / ih)
    pw, phh = iw * s, ih * s
    px, py = x + (w - pw) / 2, y + (h - phh) / 2
    rect(slide, px - pad, py - pad, pw + 2 * pad, phh + 2 * pad, card, radius=0.04)
    slide.shapes.add_picture(str(path), I(px), I(py), I(pw), I(phh))


def waves(slide, prs):
    """Paper-cut ground bands along the bottom (for the plain layout)."""
    W, H = prs.slide_width, prs.slide_height
    bands = [(RED2, 7.00, 0.09, 3.3, 0.0), (ORANGE, 7.13, 0.08, 2.4, 1.3),
             (GOLD, 7.24, 0.07, 1.9, 2.4), (YELLOW, 7.33, 0.05, 1.4, 0.7)]
    for col, base, amp, period, ph in bands:
        pts = []
        n = 120
        for k in range(n + 1):
            xin = 13.333 * k / n
            yin = base + amp * math.sin(2 * math.pi * xin / period + ph)
            pts.append((int(I(xin)), int(I(yin))))
        ff = slide.shapes.build_freeform(pts[0][0], pts[0][1], scale=1.0)
        ff.add_line_segments(pts[1:] + [(W, H), (0, H)], close=True)
        s = ff.convert_to_shape()
        s.fill.solid()
        s.fill.fore_color.rgb = col
        s.line.fill.background()
        s.shadow.inherit = False
    # SlidesMania asks that the slidesmania.com credit stays visible
    text_box(slide, 0.05, 7.3, 1.6, 0.2, [("plain", "slidesmania.com")], size=7, color=MAROON, bullets=False)


def page_no(slide, n, color=MAROON):
    text_box(slide, 12.2, 7.12, 1.0, 0.3, [("plain", f"**{n}**")], size=11, color=color, em=color,
             bullets=False, align=PP_ALIGN.RIGHT)


def cite(*nums):
    return "[" + ", ".join(str(n) for n in nums) + "]"


# ---------------------------------------------------------------- table tool
def set_cell_border(cell, color="FFBA07", width_pt=1.0, sides=("B",)):
    tcPr = cell._tc.get_or_add_tcPr()
    for side in ("L", "R", "T", "B"):
        tag = qn(f"a:ln{side}")
        for el in tcPr.findall(tag):
            tcPr.remove(el)
    for side in ("L", "R", "T", "B"):
        ln = etree.SubElement(tcPr, qn(f"a:ln{side}"))
        if side in sides:
            ln.set("w", str(int(Pt(width_pt))))
            sf = etree.SubElement(ln, qn("a:solidFill"))
            etree.SubElement(sf, qn("a:srgbClr")).set("val", color)
        else:
            ln.set("w", "0")
            etree.SubElement(ln, qn("a:noFill"))
    # lnX must come before fill elements in tcPr
    fills = [el for el in tcPr if el.tag in (qn("a:solidFill"), qn("a:noFill"))]
    for el in fills:
        tcPr.remove(el)
        tcPr.append(el)


def table(slide, rows, x, y, col_w, row_h=0.32, size=11, header=True, color=WHITE,
          head_fill=YELLOW, head_color=MAROON, body_fill=(CARD, CARD2), em=YELLOW,
          section_rows=(), align=None, valign=MSO_ANCHOR.MIDDLE, border="9D0208"):
    nr, nc = len(rows), len(col_w)
    gf = slide.shapes.add_table(nr, nc, I(x), I(y), I(sum(col_w)), I(row_h * nr))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"   # No Style, No Grid
    for j, w in enumerate(col_w):
        tbl.columns[j].width = I(w)
    for i in range(nr):
        tbl.rows[i].height = I(row_h)
        for j in range(nc):
            cell = tbl.cell(i, j)
            txt = rows[i][j] if j < len(rows[i]) else ""
            cell.margin_left = cell.margin_right = I(0.06)
            cell.margin_top = cell.margin_bottom = I(0.025)
            cell.vertical_anchor = valign
            is_head = header and i == 0
            is_sec = i in section_rows
            cell.fill.solid()
            if is_head:
                cell.fill.fore_color.rgb = head_fill
            elif is_sec:
                cell.fill.fore_color.rgb = RED1
            else:
                cell.fill.fore_color.rgb = body_fill[i % 2]
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            if align and align[j]:
                p.alignment = align[j]
            if is_head:
                add_runs(p, txt, size, head_color, head_color, bold=True)
            elif is_sec:
                add_runs(p, txt, size, YELLOW, YELLOW, italic=True)
            else:
                add_runs(p, txt, size, color, em)
            set_cell_border(cell, border, 0.75, ("B",))
    # merge section rows across all columns
    for i in section_rows:
        tbl.cell(i, 0).merge(tbl.cell(i, nc - 1))
    return gf


# ------------------------------------------------------------- India outline
def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0.0, 0
    for k in range(1, len(pts) - 1):
        x0, y0 = pts[k]
        d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, k
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def rdp_ring(ring, eps):
    """RDP for a closed ring: split at the point farthest from the start, simplify both halves."""
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    x0, y0 = pts[0]
    far = max(range(len(pts)), key=lambda k: (pts[k][0] - x0) ** 2 + (pts[k][1] - y0) ** 2)
    a = rdp(pts[: far + 1], eps)
    b = rdp(pts[far:] + [pts[0]], eps)
    return a[:-1] + b[:-1]


def india_rings():
    gj = json.loads((HERE / "india_outline_gaul.json").read_text())
    polys = []

    def collect(g):
        if g["type"] == "Polygon":
            polys.append(g["coordinates"])
        elif g["type"] == "MultiPolygon":
            polys.extend(g["coordinates"])
        elif g["type"] == "GeometryCollection":
            for h in g["geometries"]:
                collect(h)

    collect(gj)
    polys.sort(key=lambda p: -len(p[0]))
    main = polys[0][0]
    rings = [rdp_ring([tuple(p) for p in main], 0.04)]
    # Andaman & Nicobar islands: the larger polygons east of 92E, south of 14.5N
    for p in polys[1:]:
        ring = p[0]
        lon = sum(q[0] for q in ring) / len(ring)
        lat = sum(q[1] for q in ring) / len(ring)
        if lon > 92 and lat < 14.5 and len(ring) >= 20:
            rings.append(rdp_ring([tuple(q) for q in ring], 0.02))
    return rings


def signed_area(pts):
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))


def put_india_on_title_layout(prs):
    """The title layout shows a layered landscape through an Africa-shaped hole
    (+ Madagascar) cut into a white shape. Replace those two holes with India."""
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    layout = prs.slide_layouts[L_TITLE]
    target = None
    for sp in layout.shapes._spTree.iter(qn("p:sp")):
        nv = sp.find(".//" + qn("p:cNvPr"))
        if nv is not None and nv.get("id") == "26":
            target = sp
    path = target.find(".//" + qn("a:path"))
    groups, cur = [], None
    for el in list(path):
        if el.tag == A + "moveTo":
            cur = []
            groups.append(cur)
        cur.append(el)

    def pts_of(group):
        return [(int(pt.get("x")), int(pt.get("y"))) for el in group for pt in el.findall(A + "pt")]

    africa = pts_of(groups[1])
    xs, ys = [p[0] for p in africa], [p[1] for p in africa]
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    orient = math.copysign(1, signed_area(africa))

    rings = india_rings()
    allpts = [q for r in rings for q in r]
    lon0, lon1 = min(q[0] for q in allpts), max(q[0] for q in allpts)
    lat0, lat1 = min(q[1] for q in allpts), max(q[1] for q in allpts)
    kx = math.cos(math.radians(23))
    S = min((bx1 - bx0) / ((lon1 - lon0) * kx), (by1 - by0) / (lat1 - lat0))
    ox = bx0 + ((bx1 - bx0) - (lon1 - lon0) * kx * S) / 2
    oy = by0 + ((by1 - by0) - (lat1 - lat0) * S) / 2

    new_groups = []
    for r in rings:
        pts = [(int(ox + (lon - lon0) * kx * S), int(oy + (lat1 - lat) * S)) for lon, lat in r]
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        if math.copysign(1, signed_area(pts)) != orient:
            pts = pts[::-1]
        els = []
        for k, (x, y) in enumerate(pts):
            el = etree.Element(A + ("moveTo" if k == 0 else "lnTo"))
            pt = etree.SubElement(el, A + "pt")
            pt.set("x", str(x))
            pt.set("y", str(y))
            els.append(el)
        els.append(etree.Element(A + "close"))
        new_groups.append(els)

    # yellow backing behind the landscape layers (fills small gaps between them)
    spTree = layout.shapes._spTree
    back = etree.fromstring(
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:nvSpPr><p:cNvPr id="900" name="India backing"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="0" y="3300000"/><a:ext cx="4500000" cy="2700000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '<a:solidFill><a:srgbClr val="FAA306"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>')
    first_shape = [el for el in spTree if el.tag in (qn("p:sp"), qn("p:grpSp"))][0]
    first_shape.addprevious(back)

    # rebuild the path: outer boundary, India rings, then the remaining small subpaths
    for el in list(path):
        path.remove(el)
    for el in groups[0]:
        path.append(el)
    for g in new_groups:
        for el in g:
            path.append(el)
    for g in groups[3:]:
        for el in g:
            path.append(el)


# ------------------------------------------------------------------- slides
def main():
    prs = Presentation(str(TEMPLATE))
    # remove the template's example slides
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)
    put_india_on_title_layout(prs)

    lay = prs.slide_layouts
    page = [0]

    def new(layout_idx, title=None, number=True, num_color=MAROON, plain_waves=None, **tkw):
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
        if plain_waves or (plain_waves is None and layout_idx == L_PLAIN):
            waves(s, prs)
        if number:
            page_no(s, page[0], num_color)
        return s

    # ---------------------------------------------------------------- 1 title
    s = new(L_TITLE, number=False)
    set_title(s, "COMPOUND HEAT–DROUGHT STRESS OVER INDIA", size=56, align=PP_ALIGN.RIGHT,
              box=(6.9, 0.4, 6.0, 3.3))
    sub = s.placeholders[1]
    sub.left, sub.top, sub.width, sub.height = I(7.45), I(3.75), I(5.45), I(1.7)
    tf = sub.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    add_runs(p, "Are ecosystems hit harder when heat and drought strike together?", 17, YELLOW)
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.RIGHT
    p.space_before = Pt(4)
    add_runs(p, "Mid-Evaluation, EVS Project", 14, WHITE)
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.RIGHT
    p.space_before = Pt(8)
    add_runs(p, "Arnav Deshmukh · Ayush Brajesh Roy · Saksham Chitkara", 13, WHITE)
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.RIGHT
    add_runs(p, "Gracy Garg · Rudra Choudhary", 13, WHITE)
    p = tf.add_paragraph()
    p.alignment = PP_ALIGN.RIGHT
    add_runs(p, "IIIT Hyderabad · October 9, 2026", 13, WHITE)

    # -------------------------------------------------------------- 2 outline
    s = new(L_TOC, "OUTLINE", num_color=MAROON)
    drop_placeholders(s)
    secs = [("01", "Problem statement & motivation"), ("02", "Our hypotheses"),
            ("03", "Methodology"), ("04", "Preliminary analysis (H1, H2)"),
            ("05", "Things left to do")]
    for k, (n, t) in enumerate(secs):
        y = 0.75 + k * 1.2
        heading(s, 6.3, y, 1.2, 0.9, n, size=48, color=ORANGE)
        heading(s, 7.55, y + 0.2, 5.4, 0.6, t.upper(), size=26, color=RED1)

    # ----------------------------------------------------------- section 01
    def section(num, title):
        s = new(L_SECTION, title.upper(), number=False, size=50, align=PP_ALIGN.CENTER,
                box=(1.2, 2.05, 10.93, 1.9))
        drop_placeholders(s)
        s.shapes.title.text_frame.vertical_anchor = MSO_ANCHOR.TOP
        # big yellow number behind the title, as in the template
        nb = text_box(s, 3.2, 0.1, 6.93, 2.7, [("plain", num)], size=170, color=YELLOW,
                      bullets=False, align=PP_ALIGN.CENTER, font=HEAD_FONT)
        s.shapes._spTree.remove(nb._element)
        s.shapes._spTree.insert(2, nb._element)
        return s

    section("01", "Problem statement & motivation")

    # ---------------------------------------- 3 heat and drought rarely alone
    s = new(L_PLAIN, "HEAT AND DROUGHT RARELY COME ALONE")
    text_box(s, 0.6, 1.75, 4.2, 4.6, [
        "**Drought**: too little water (little rain, dry soil)",
        "**Heat**: high temperature, “thirsty” air",
        "They feed each other: dry soil heats up, heat dries soil",
        "Plants get hit from both sides"], size=20, space=16)
    bw, bh = 3.15, 1.35
    hx, hy, vx, sy = 5.75, 1.75, 9.75, 4.6
    heat = rect(s, hx, hy, bw, bh, RED2)
    box_text(heat, ["**Heat**", "(high temperature)"], 18, WHITE)
    vpd = rect(s, vx, hy, bw, bh, ORANGE)
    box_text(vpd, ["**Thirsty air**", "(high VPD)"], 18, WHITE)
    soil = rect(s, hx, sy, bw, bh, RED1, line=ORANGE2)
    box_text(soil, ["**Dry soil**", "(drought)"], 18, WHITE)
    gpp = rect(s, vx, sy, bw, bh, YELLOW)
    box_text(gpp, ["Plants close stomata", "⇒ **less photosynthesis**"], 17, MAROON)
    arrow(s, hx + bw, hy + bh / 2, vx, hy + bh / 2)                    # heat -> vpd
    arrow(s, vx + bw / 2, hy + bh, vx + bw / 2, sy)                   # vpd -> gpp
    arrow(s, hx + bw, sy + bh / 2, vx, sy + bh / 2)                    # soil -> gpp
    arrow(s, hx + 0.75, hy + bh, hx + 0.75, sy)                        # heat -> soil
    arrow(s, hx + bw - 0.75, sy, hx + bw - 0.75, hy + bh)              # soil -> heat
    text_box(s, 4.55, 3.3, 1.95, 0.8, [("plain", "more\nevaporation")], size=15, color=CREAM,
             bullets=False, align=PP_ALIGN.RIGHT)
    text_box(s, hx + bw - 0.62, 3.3, 1.4, 0.8, [("plain", "less\ncooling")], size=15, color=CREAM,
             bullets=False, align=PP_ALIGN.LEFT)

    # ---------------------------------------------------- 4 GPP & carbon sink
    s = new(L_PLAIN, "KEY IDEA: GPP AND THE LAND CARBON SINK")
    text_box(s, 0.6, 1.3, 12.1, 1.1, [("plain",
        "**Gross primary productivity (GPP)** is the total amount of carbon that plants take out of "
        "the air by photosynthesis, per area and time (we use grams of carbon per m² per month). "
        "It is the starting point of plant growth, crop yield and the land carbon sink.")],
        size=17, bullets=False)

    def panel(cx, title, gw, rw, crown, verdict):
        heading(s, cx - 2.5, 2.5, 5.0, 0.4, title, size=20, color=YELLOW, align=PP_ALIGN.CENTER)
        co2 = rect(s, cx - 2.2, 2.95, 4.4, 0.45, CARD, line=CREAM, line_w=1)
        box_text(co2, ["CO₂ in the air"], 14, CREAM)
        # ground
        g = rect(s, cx - 2.4, 5.2, 4.8, 0.06, ORANGE2, shape=MSO_SHAPE.RECTANGLE)
        # tree
        rect(s, cx - 0.08, 4.6, 0.16, 0.62, RGBColor(0x7A, 0x45, 0x1E), shape=MSO_SHAPE.RECTANGLE)
        rect(s, cx - 0.48, 3.8, 0.96, 0.96, crown, shape=MSO_SHAPE.OVAL)
        # photosynthesis (down) and respiration (up)
        a = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, I(cx - 1.05 - gw / 2), I(3.5), I(gw), I(1.6))
        a.fill.solid(); a.fill.fore_color.rgb = GREEN; a.line.fill.background(); a.shadow.inherit = False
        b = s.shapes.add_shape(MSO_SHAPE.UP_ARROW, I(cx + 1.05 - rw / 2), I(3.5), I(rw), I(1.6))
        b.fill.solid(); b.fill.fore_color.rgb = ORANGE2; b.line.fill.background(); b.shadow.inherit = False
        text_box(s, cx - 3.4, 3.85, 1.95, 0.8, [("plain", "photosynthesis\n(GPP)")], size=13,
                 color=RGBColor(0x9F, 0xD8, 0x7A), bullets=False, align=PP_ALIGN.RIGHT)
        text_box(s, cx + 1.45, 3.85, 1.95, 0.8, [("plain", "respiration\n(plants + soil)")], size=13,
                 color=ORANGE2, bullets=False, align=PP_ALIGN.LEFT)
        text_box(s, cx - 3.0, 5.3, 6.0, 0.8, [("plain", verdict[0]), ("plain", verdict[1])], size=14,
                 color=WHITE, bullets=False, align=PP_ALIGN.CENTER, space=0)

    panel(3.55, "NORMAL YEAR", 0.62, 0.22, GREEN,
          ("Uptake > release ⇒ carbon **SINK**", "(land removes CO₂ from the air)"))
    panel(9.75, "HEAT + DROUGHT", 0.2, 0.55, OLIVE,
          ("Uptake < release ⇒ carbon **SOURCE**", "(land adds CO₂ to the air)"))
    text_box(s, 0.6, 6.35, 12.1, 0.4, [("plain",
        f"Heat + drought can flip land from sink to source: Europe in 2003 {cite(1)}.")],
        size=14, color=CREAM, bullets=False, align=PP_ALIGN.CENTER)

    # ------------------------------------------------------- 5 why it matters
    s = new(L_BULLETS, "WHY IT MATTERS", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.5, 9.0, 4.0, [
        f"**Europe 2003**: a summer of heat + drought cut productivity by about 30% and turned "
        f"Europe’s land into a temporary carbon //source// {cite(1)}.",
        f"**Worldwide**: across flux-tower sites, combined heat + drought reduced the carbon sink "
        f"more than either extreme alone {cite(2)}.",
        f"**India**: droughts and heatwaves that happen at the same time have become more frequent "
        f"and widespread {cite(3)}.",
        "As the climate warms, more droughts will happen during hot spells, so we need to know how "
        "much worse the combination is."], size=20, space=14)

    # ------------------------------------------------------------ 6 why India
    s = new(L_PLAIN, "WHY INDIA?")
    text_box(s, 0.6, 1.45, 6.6, 5.0, [
        "**Monsoon-dependent**: most rain falls in Jun–Sep; a weak monsoon means drought (2002, 2009).",
        "**Hot pre-monsoon**: Mar–May is the hottest season; extreme heat in 2010 and 2022.",
        "**Mostly cropland** (~60% of cells): lost productivity means lost food and income.",
        f"**Under-studied**: most work covers Europe, China or the globe; India-wide studies are new "
        f"{cite(4, 5)}."], size=20, space=18)
    picture_card(s, FIG / "study_area_landcover.png", 7.35, 1.3, 5.75, 5.45)

    # ------------------------------------------------------ 7 problem statement
    s = new(L_YELLOW, "PROBLEM STATEMENT", num_color=WHITE,
            box=(0.7, 0.35, 11.9, 0.85), align=PP_ALIGN.CENTER)
    drop_placeholders(s)
    s.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = MAROON
    heading(s, 0.7, 1.25, 11.9, 0.7, "TOPIC: COMPOUND HEAT–DROUGHT STRESS", size=36, color=RED2,
            align=PP_ALIGN.CENTER)
    text_box(s, 0.7, 1.95, 11.9, 0.5, [("plain", "Are ecosystems experiencing stronger combined impacts?")],
             size=22, color=MAROON, bullets=False, align=PP_ALIGN.CENTER)
    text_box(s, 1.2, 2.6, 10.9, 0.9, [("plain",
        "Does simultaneous heat and drought produce **greater ecosystem stress** than either "
        "disturbance alone?")], size=19, color=MAROON, em=RED2, bullets=False, align=PP_ALIGN.CENTER)
    blk = rect(s, 1.6, 3.55, 10.1, 1.55, MAROON, radius=0.12)
    text_box(s, 1.85, 3.62, 9.6, 0.4, [("plain", "WHY THIS MATTERS")], size=18, color=YELLOW,
             bullets=False, font=HEAD_FONT)
    text_box(s, 1.85, 4.0, 9.6, 1.05, [("plain",
        "If heat and drought damage simply **add up**, we can predict compound impacts from "
        "single-stress studies. If they **amplify** each other, compound events are a separate, "
        "bigger risk.")], size=17, color=WHITE, bullets=False)

    # ---------------------------------------------------------- 8 our questions
    s = new(L_BULLETS, "OUR QUESTIONS (FOR INDIA)", box=(0.7, 0.45, 11.9, 0.9), align=PP_ALIGN.LEFT)
    drop_placeholders(s)
    text_box(s, 0.75, 1.5, 9.3, 4.0, [
        "Is vegetation hit harder in **compound** (hot //and// dry) months than in hot-only or "
        "dry-only months?",
        "Is the compound hit **bigger than the heat damage plus the drought damage added together**?",
        "Do ecosystems take **longer to recover** after compound events?",
        "Does the answer differ between **forests, croplands, grasslands**, and between "
        "**Peninsular and North India**?"], size=21, space=16, num=True)

    # ----------------------------------------------------- 9 known vs open
    s = new(L_PLAIN, "WHAT IS KNOWN, AND WHAT IS STILL OPEN")
    for x, head, items in [
        (0.55, "KNOWN", [
            f"Heat + drought together cut the carbon uptake of ecosystems more than either extreme "
            f"alone (flux towers worldwide {cite(2)}; Europe 2003 {cite(1)}).",
            f"In India, hot and dry conditions together raise the //chance// that vegetation goes "
            f"into drought {cite(4)}.",
            f"In Peninsular India’s forests, compound hot–dry extremes raise the risk of large GPP "
            f"losses {cite(5)}."]),
        (6.8, "OPEN", [
            "Is the damage to //average// productivity more than heat damage + drought damage "
            "(synergy), or just the sum? Few studies test this directly, with uncertainty.",
            f"The answer depends on how “drought” is defined: soil-based and air-based definitions "
            f"give different impacts {cite(6)}.",
            f"Do ecosystems recover more slowly after compound events? Global studies disagree "
            f"{cite(7, 8, 9)}, and we found no India-specific comparison."])]:
        rect(s, x, 1.3, 6.0, 5.4, CARD, radius=0.05)
        heading(s, x + 0.25, 1.42, 5.5, 0.5, head, size=24)
        text_box(s, x + 0.2, 2.0, 5.6, 4.6, items, size=18, space=16)

    # ------------------------------------------------------------ hypotheses
    section("02", "Our hypotheses")
    s = new(L_PLAIN, "OUR HYPOTHESES")
    text_box(s, 0.6, 1.25, 12.1, 1.0, [("plain",
        "**Our aim:** an India-wide, honest test of additivity on two satellite measures, with "
        "uncertainty and a drought-index check, then recovery and regional differences. This is a "
        "regional synthesis with extensions, not a first-of-its-kind study.")], size=17, bullets=False)
    table(s, [
        ["", "Hypothesis", "Current status"],
        ["**H1**", "Vegetation (GPP, NDVI) is lower in compound months than in hot-only or dry-only months.",
         "**Tested**"],
        ["**H2**", "The compound effect is //synergistic//: larger than the heat effect + the drought effect.",
         "**Tested**"],
        ["**H3**", "Ecosystems recover more slowly after compound events than after droughts.", "In progress"],
        ["**H4**", "The response differs by land cover and by region (Peninsular vs North India).",
         "In progress"]],
        0.6, 2.55, [0.8, 8.9, 2.4], row_h=0.72, size=17)
    text_box(s, 0.6, 6.25, 12.1, 0.5, [("plain",
        "Throughout, we check that conclusions do not depend on the choice of drought index "
        "(SPEI-3 vs SPI-3).")], size=14, color=CREAM, bullets=False)

    # ----------------------------------------------------------- methodology
    section("03", "Methodology")
    s = new(L_TIMELINE, "WORKFLOW", box=(0.7, 0.3, 11.9, 0.95), align=PP_ALIGN.CENTER)
    drop_placeholders(s)
    steps = [("STEP 1", "Download & aggregate data (Earth Engine)"),
             ("STEP 2", "Monthly anomalies (z-scores)"),
             ("STEP 3", "Sort each grid-month: normal / hot / dry / compound"),
             ("STEP 4", "Compare GPP & NDVI across boxes (H1, H2)")]
    bw, gap, x0, y0, bh = 2.7, 0.42, 0.6, 1.6, 1.65
    for k, (h, t) in enumerate(steps):
        x = x0 + k * (bw + gap)
        b = rect(s, x, y0, bw, bh, [RED2, ORANGE, ORANGE2, YELLOW][k])
        col = MAROON if k == 3 else WHITE
        box_text(b, [f"**{h}**", t], 17, col)
        if k < 3:
            arrow(s, x + bw + 0.04, y0 + bh / 2, x + bw + gap - 0.04, y0 + bh / 2, color=YELLOW, width=3)
    x4 = x0 + 3 * (bw + gap)
    e = rect(s, x4 - 0.15, y0 + bh + 0.38, bw + 0.3, 1.3, CARD, line=YELLOW, line_w=1.25)
    box_text(e, ["Events & recovery (H3),", "land cover & region (H4)", "//in progress//"], 15, WHITE)
    arrow(s, x4 + bw / 2, y0 + bh + 0.04, x4 + bw / 2, y0 + bh + 0.34, color=YELLOW, width=3)
    text_box(s, 0.6, 3.75, 8.6, 1.0, [("plain",
        "Everything is scripted in Python (xarray, scipy, statsmodels) and checked by 68 automated "
        "tests. The analysis reruns from cached data in minutes.")], size=16, color=CREAM, bullets=False)

    # ----------------------------------------------------------- step 1: data
    s = new(L_PLAIN, "STEP 1: DATA")
    table(s, [
        ["Dataset", "What we use", "Period", "Role"],
        [f"ERA5-Land {cite(10)}", "daily max temperature; soil moisture 0–100 cm; VPD", "1991–2024",
         "defines “hot”; mechanism"],
        [f"SPEI v2.11 {cite(11)}", "SPEI-3 (rain minus evaporative demand)", "1991–2024", "defines “dry”"],
        [f"CHIRPS v2 {cite(12)}", "rainfall → SPI-3", "1991–2024", "temperature-free drought check"],
        [f"MODIS MOD17A2H {cite(13, 14)}", "GPP (photosynthesis)", "2001–2022", "main response"],
        [f"MODIS MOD13A3 {cite(15)}", "NDVI (greenness), quality-masked", "2001–2022", "second response"],
        [f"ESA WorldCover {cite(16)}", "land-cover fractions", "2021", "vegetation mask; land-cover groups"]],
        0.6, 1.25, [3.1, 4.6, 1.4, 3.0], row_h=0.58, size=16)
    text_box(s, 0.6, 5.4, 12.1, 1.6, [
        f"All five suggested datasets, processed in Google Earth Engine {cite(17)} onto one common grid: "
        f"0.25° (≈27 km), monthly, all of India (4,481 grid cells).",
        "GPP and NDVI both come from the MODIS Terra satellite: two different products, but not "
        "independent sensors."], size=17, space=6)

    # ------------------------------------------------------------- metrics
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

    # ------------------------------------------------------ step 2: anomalies
    s = new(L_PLAIN, "STEP 2: MONTHLY ANOMALIES (COMPARING LIKE WITH LIKE)")
    text_box(s, 0.6, 1.25, 12.1, 1.3, [
        "Raw values are not comparable: May is always hotter than January, and a desert always has "
        "less GPP than a forest.",
        "So for every grid cell and every calendar month, we convert a value into a **z-score**:"],
        size=17, space=5)
    # z = numerator / denominator
    text_box(s, 2.55, 2.67, 0.9, 0.6, [("plain", "//z// =")], size=20, color=WHITE, bullets=False,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    text_box(s, 3.55, 2.5, 7.2, 0.45, [("plain", "this month’s value − normal for this cell in this month")],
             size=17, color=WHITE, bullets=False, align=PP_ALIGN.CENTER)
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(3.65), I(2.97), I(10.65), I(2.97))
    ln.line.color.rgb = YELLOW
    ln.line.width = Pt(1.5)
    text_box(s, 3.55, 3.01, 7.2, 0.45, [("plain", "typical year-to-year spread")], size=17, color=WHITE,
             bullets=False, align=PP_ALIGN.CENTER)
    text_box(s, 0.6, 3.55, 12.1, 3.3, [
        (1, "//z// = −1 means “one standard deviation below what is normal here at this time of year”."),
        "**Temperature**: normal = 1991–2020. Not detrended, so long-term warming counts as heat.",
        "**GPP, NDVI**: a linear trend is removed first, so the long-term greening of India (CO₂, "
        "irrigation) is not mistaken for an anomaly.",
        "**Only growing-season months count**: the cell is in India, at least 50% vegetated, and GPP in "
        "that month is normally at least 30% of its peak. This removes deserts and dormant seasons "
        "(824,598 grid-months remain)."], size=18, space=9)

    # ------------------------------------------------------- step 3: boxes
    s = new(L_PLAIN, "STEP 3: SORTING EVERY GRID-MONTH INTO FOUR BOXES")
    # 2x2 grid
    gx, gy, cw, chh = 1.95, 1.75, 1.75, 0.7
    heading(s, gx, 1.25, 2 * cw, 0.45, "SPEI-3 (dryness)", size=17, align=PP_ALIGN.CENTER)
    for j, lab in enumerate(["> −1", "≤ −1"]):
        text_box(s, gx + j * cw, gy - 0.05, cw, 0.4, [("plain", lab)], size=15, color=CREAM,
                 bullets=False, align=PP_ALIGN.CENTER)
    heading(s, 0.35, gy + 0.4 + 0.45, 0.9, 0.6, "Tmax z", size=17, align=PP_ALIGN.CENTER)
    for i, lab in enumerate(["< 1", "≥ 1"]):
        text_box(s, 1.2, gy + 0.4 + i * chh, 0.7, chh, [("plain", lab)], size=15, color=CREAM,
                 bullets=False, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    cells = [["Normal", "Dry-only"], ["Hot-only", "**Compound**"]]
    fills = [[CARD, ORANGE], [RED2, YELLOW]]
    for i in range(2):
        for j in range(2):
            b = rect(s, gx + j * cw + 0.03, gy + 0.4 + i * chh + 0.03, cw - 0.06, chh - 0.06, fills[i][j],
                     radius=0.1)
            box_text(b, [cells[i][j]], 16, MAROON if (i, j) == (1, 1) else WHITE, em=MAROON)
    table(s, [["Normal", "573,543"], ["Hot-only", "79,717"], ["Dry-only", "109,073"],
              ["**Compound**", "**62,265** (7.6%)"]],
          1.95, 3.55, [1.75, 1.75], row_h=0.42, size=14, header=False,
          align=[None, PP_ALIGN.RIGHT])
    text_box(s, 6.0, 1.3, 6.8, 5.3, [
        "**Hot**: the month’s average daily maximum temperature is at least 1 standard deviation "
        "above normal.",
        "**Dry**: **SPEI-3** ≤ −1, i.e. the last 3 months had clearly less water than usual (rain minus "
        "evaporative demand).",
        "**SPEI**’s demand term depends on temperature, so “dry” is partly driven by heat. We therefore "
        "repeat everything with **SPI-3**, which uses rainfall only.",
        "Left: number of growing-season grid-months in each box, India, 2001–2022."],
        size=19, space=16)

    # ------------------------------------------------------- step 4: tests
    s = new(L_PLAIN, "STEP 4: HOW WE TEST H1 AND H2")
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

    # ------------------------------------------------- preliminary analysis
    section("04", "Preliminary analysis (H1, H2)")
    s = new(L_PLAIN, "WHERE COMPOUND MONTHS HAPPEN")
    picture_card(s, FIG / "freq_map_compound.png", 0.55, 1.25, 6.2, 5.5)
    text_box(s, 7.0, 1.45, 5.9, 5.2, [
        "Share of each cell’s growing-season months that were compound, 2001–2022.",
        "Overall, 7.6% of growing-season grid-months are compound.",
        "Hotspots: the northern plains, east-central India, the North-East, and a belt in the western "
        "Deccan (around 15–18°N).",
        "Both North and Peninsular India have more than 20,000 compound grid-months, enough for a "
        "reliable comparison."], size=20, space=18)

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
        "Each square: average GPP //z// of all months in that range (red = below normal; grey = fewer "
        "than 30 months).",
        "Dashed lines = our cut-offs; bottom-right = the compound box."], size=16, space=6)
    heading(s, 7.15, 4.1, 5.8, 0.45, "WHAT WE SEE", size=20)
    text_box(s, 7.15, 4.45, 5.85, 2.4, [
        "GPP falls as it gets drier: about +0.5 in the wettest rows, −0.35 in the driest.",
        "Worst square: hottest + driest corner (−0.92). Hot but wet months are not below normal.",
        "⇒ Dryness is the main driver and heat adds to it, consistent with additive effects."],
        size=16, space=6)

    s = new(L_PLAIN, "OBSERVATIONS SO FAR")
    text_box(s, 0.6, 1.2, 12.1, 5.6, [
        "**H1 supported.** Compound heat–drought months reduce productivity (GPP) and greenness (NDVI) "
        "significantly more than heat alone or drought alone. This holds for both drought indices.",
        "**H2 not supported.** The compound effect is about the //sum// of the heat and drought effects, "
        "not more.",
        "**Mechanism.** Compound months have the driest soils and the thirstiest air at the same time.",
        "**Drought definition matters.** SPEI vs SPI changes the H2 details. Hot-only months also have "
        "dry soils (soil moisture z = −0.75), which rainfall-based indices miss.",
        f"**How this fits the literature.** Meena et al. {cite(4)} report “nonlinear amplification” for "
        f"India using //probabilities// of vegetation drought. Our test on //average// anomalies finds "
        f"additivity. The two ask different questions; comparing them directly is planned.",
        "**Caveats.** MOD17 GPP is partly modelled (it uses air dryness and temperature, and has no "
        "soil-moisture input). NDVI is from the same satellite. Monthly 0.25° data blur short heatwaves."],
        size=18.5, space=11)

    # ------------------------------------------------------------ left to do
    section("05", "Things left to do")
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

    # ------------------------------------------------------------ references
    refs = [
        "Philippe Ciais, Markus Reichstein, Nicolas Viovy, André Granier, Jérôme Ogée, Vincent Allard, Marc Aubinet, Nina Buchmann, Christian Bernhofer, Arnaud Carrara, Frédéric Chevallier, Nathalie De Noblet, A. D. Friend, Pierre Friedlingstein, Thomas Grünwald, Bernard Heinesch, P. Keronen, Alexander Knohl, Gerhard Krinner, and Riccardo Valentini. Europe-wide reduction in primary productivity caused by the heat and drought in 2003. //Nature//, 437(7058):529–533, 2005. doi: 10.1038/nature03972.",
        "Jannis von Buttlar, Jakob Zscheischler, Anja Rammig, Sebastian Sippel, Markus Reichstein, Alexander Knohl, Martin Jung, Olaf Menzer, M. Altaf Arain, Nina Buchmann, Alessandro Cescatti, David Ehrhart, Lutz Merbold, Leonardo Montagnani, Dario Papale, Georg Wohlfahrt, Sonia Wolf, and Miguel D. Mahecha. Impacts of droughts and extreme-temperature events on gross primary production and ecosystem respiration: a systematic assessment across ecosystems and climate zones. //Biogeosciences//, 15(5):1293–1318, 2018. doi: 10.5194/bg-15-1293-2018.",
        "S. Sharma and P. Mujumdar. Increasing frequency and spatial extent of concurrent meteorological droughts and heatwaves in India. //Scientific Reports//, 7:15582, 2017. doi: 10.1038/s41598-017-15896-3.",
        "A. Meena, S. Swarnkar, S. Dash, and V. Peepliwal. Nonlinear amplification of vegetation drought under compound dry–hot extremes across India. //Ecological Indicators//, 191:115617, 2026. doi: 10.1016/j.ecolind.2026.115617.",
        "D. Sen, D. Barua, and J. Monteiro. Quantile-based sensitivity and risk thresholds reveal asymmetric responses of tropical forest productivity to individual and compound hot–dry extremes. //Environmental Research Communications//, 2026. doi: 10.1088/2515-7620/aea1e9.",
        "Y. Liang, J. Wang, Z. Hao, H. Wang, H. Cui, and Q. Ge. Anthropogenically-driven escalating impact of soil-based compound dry-hot extremes on vegetation productivity. //Nature Communications//, 17:2303, 2026. doi: 10.1038/s41467-026-68878-3.",
        "Y. Yao et al. Compound hot-dry events greatly prolong the recovery time of dryland ecosystems. //National Science Review//, 11(10):nwae274, 2024. doi: 10.1093/nsr/nwae274.",
        "M. Huang and P. Zhai. Protracted vegetation recovery after compound drought and hot extreme compared to general drought. //Environmental Research Letters//, 20(2):024001, 2025. doi: 10.1088/1748-9326/ada4c3.",
        "X. Feng et al. Divergent vegetation recovery shaped by drought, heat and compound extremes. //Communications Earth & Environment//, 7:688, 2026. doi: 10.1038/s43247-026-03927-9.",
        "Joaquín Muñoz-Sabater, Emanuel Dutra, Anna Agustí-Panareda, Clément Albergel, Gabriele Arduini, Gianpaolo Balsamo, Souhail Boussetta, Margarita Choulga, Shaun Harrigan, Hans Hersbach, Mikel Martínez-Sánchez, Luca Minola, et al. ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. //Earth System Science Data//, 13(9):4349–4383, 2021. doi: 10.5194/essd-13-4349-2021.",
        "Sergio M. Vicente-Serrano, Santiago Beguería, and Juan I. López-Moreno. A multiscalar drought index sensitive to global warming: the standardized precipitation evapotranspiration index. //Journal of Climate//, 23(7):1696–1718, 2010. doi: 10.1175/2009JCLI2909.1.",
        "Chris Funk, Pete Peterson, Martin Landsfeld, Diego Pedreros, James Verdin, Shraddhanand Shukla, Gregory Husak, James Rowland, Laura Harrison, Andrew Hoell, and Joel Michaelsen. The climate hazards infrared precipitation with stations – a new environmental record for monitoring extremes. //Scientific Data//, 2:150066, 2015. doi: 10.1038/sdata.2015.66.",
        "S. Running, Q. Mu, and M. Zhao. MOD17A2H MODIS/Terra gross primary productivity 8-day L4 global 500m SIN grid V006. NASA EOSDIS Land Processes DAAC, 2015.",
        "Steven W. Running, Ramakrishna R. Nemani, Faith Ann Heinsch, Maosheng Zhao, Matthew Reeves, and Hirofumi Hashimoto. A continuous satellite-derived measure of global terrestrial primary production. //BioScience//, 54(6):547–560, 2004. doi: 10.1641/0006-3568(2004)054[0547:ACSMOG]2.0.CO;2.",
        "K. Didan. MODIS/Terra vegetation indices monthly L3 global 1km SIN grid V061 (MOD13A3). NASA EOSDIS Land Processes DAAC, 2021.",
        "Daniele Zanaga, Ruben Van De Kerchove, Dirk Daems, Wanda De Keersmaecker, Carsten Brockmann, Grit Kirches, Jan Wevers, Oliver Cartus, Maurizio Santoro, Steffen Fritz, et al. ESA WorldCover 10 m 2021 v200. //Zenodo//, 2022. doi: 10.5281/zenodo.7254221.",
        "Noel Gorelick, Matt Hancher, Mike Dixon, Simon Ilyushchenko, David Thau, and Rebecca Moore. Google Earth Engine: Planetary-scale geospatial analysis for everyone. //Remote Sensing of Environment//, 202:18–27, 2017. doi: 10.1016/j.rse.2017.06.031.",
    ]
    for part, (a, b) in enumerate([(0, 6), (6, 12), (12, 17)]):
        s = new(L_PLAIN, f"REFERENCES ({part + 1}/3)")
        text_box(s, 0.6, 1.2, 12.1, 5.6, [("plain", f"**[{k + 1}]**  {refs[k]}") for k in range(a, b)],
                 size=14, space=10, bullets=False)

    # --------------------------------------------------------------- thanks
    s = new(L_YELLOW, "THANK YOU!", number=False, box=(0.7, 1.4, 11.9, 1.4), align=PP_ALIGN.CENTER,
            size=66)
    drop_placeholders(s)
    s.shapes.title.text_frame.paragraphs[0].runs[0].font.color.rgb = MAROON
    text_box(s, 0.7, 2.85, 11.9, 0.6, [("plain", "**Questions?**")], size=24, color=MAROON, em=RED2,
             bullets=False, align=PP_ALIGN.CENTER)
    text_box(s, 0.7, 3.5, 11.9, 0.5, [("plain", "Presentation template: SlidesMania (Africa Viva)")],
             size=12, color=MAROON, bullets=False, align=PP_ALIGN.CENTER)

    prs.save(str(OUT))
    print("wrote", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    main()
