"""Title-slide map for the final deck: India AND Australia cut into the
"Africa Viva" title layout (generalises build_pptx.put_india_on_title_layout).

Outlines: FAO GAUL 2015 level 0 (India's official outline; Australia mainland +
Tasmania), fetched from Earth Engine into *_outline_gaul.json.
"""
import json
import math

from lxml import etree
from pptx.oxml.ns import qn

from build_pptx import HERE, L_TITLE, rdp_ring, signed_area, india_rings


def australia_rings():
    gj = json.loads((HERE / "australia_outline_gaul.json").read_text())
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
    rings = [rdp_ring([tuple(p) for p in polys[0][0]], 0.12)]           # mainland
    for p in polys[1:]:
        ring = p[0]
        lat = sum(q[1] for q in ring) / len(ring)
        if lat < -40 and len(ring) >= 200:                               # Tasmania
            rings.append(rdp_ring([tuple(q) for q in ring], 0.06))
    return rings


def put_countries_on_title_layout(prs):
    """Replace the Africa (+ Madagascar) holes with India (upper left) and
    Australia (lower right), each scaled into its own part of Africa's box."""
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
    W, H = bx1 - bx0, by1 - by0
    orient = math.copysign(1, signed_area(africa))

    # (rings, box as fractions of Africa's bounding box, mid-latitude for the lon scaling)
    placements = [
        (india_rings(), (0.00, 0.00, 0.64, 0.60), 23.0),
        (australia_rings(), (0.08, 0.52, 1.04, 1.10), -27.0),
    ]
    new_groups = []
    for rings, (fx0, fy0, fx1, fy1), mid_lat in placements:
        allpts = [q for r in rings for q in r]
        lon0, lon1 = min(q[0] for q in allpts), max(q[0] for q in allpts)
        lat0, lat1 = min(q[1] for q in allpts), max(q[1] for q in allpts)
        kx = math.cos(math.radians(mid_lat))
        X0, Y0 = bx0 + fx0 * W, by0 + fy0 * H
        BW, BH = (fx1 - fx0) * W, (fy1 - fy0) * H
        S = min(BW / ((lon1 - lon0) * kx), BH / (lat1 - lat0))
        ox = X0 + (BW - (lon1 - lon0) * kx * S) / 2
        oy = Y0 + (BH - (lat1 - lat0) * S) / 2
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

    spTree = layout.shapes._spTree
    back = etree.fromstring(
        '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<p:nvSpPr><p:cNvPr id="900" name="Map backing"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="0" y="3300000"/><a:ext cx="5200000" cy="3558000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '<a:solidFill><a:srgbClr val="FAA306"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>')
    first_shape = [el for el in spTree if el.tag in (qn("p:sp"), qn("p:grpSp"))][0]
    first_shape.addprevious(back)

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
