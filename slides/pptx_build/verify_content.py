"""Check that every piece of text in slides/midsub_v4.pdf also appears in
slides/midsub_v4_themed.pptx.

v4 text is split into fragments (PDF lines, further split at sentence
punctuation). Each fragment is normalised (NFKC, lower case, dashes/quotes
unified, all whitespace removed) and searched for in the normalised text of
the whole PPTX. Text inside raster figures is the same PNG in both decks, so it
is not compared. Prints every fragment that is not found.
"""
import re
import sys
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "midsub_v4.pdf")
PPTX = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "midsub_v4_themed.pptx")

FOOTER = re.compile(r"EVS Project #19 \(IIIT Hyderabad\)|Compound Heat-Drought Stress|October 9, 2026|\d+ / \d+")


def norm(t):
    t = unicodedata.normalize("NFKC", t).lower()
    for a in "–—−‐‑":
        t = t.replace(a, "-")
    for q in "“”‘’\"'`":
        t = t.replace(q, "")
    t = t.replace("∼", "~").replace("≈", "~").replace(" ", " ")
    return re.sub(r"\s+", "", t)


def pptx_text():
    prs = Presentation(str(PPTX))
    chunks = []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == 6:  # group
                walk(sh.shapes)
            if sh.has_text_frame:
                chunks.append(sh.text_frame.text)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    chunks.append(" ".join(c.text for c in row.cells))
    for s in prs.slides:
        walk(s.shapes)
    return "\n".join(chunks), len(prs.slides)


def main():
    ptxt, nslides = pptx_text()
    P = norm(ptxt)
    doc = fitz.open(str(PDF))
    total = missing = 0
    report = []
    # LaTeX T1 font encoding as extracted by PyMuPDF: ligatures, dashes and
    # quotes come out as control bytes (and \x1c-\x1e would count as line breaks)
    T1 = {"\x1b": "ff", "\x1c": "fi", "\x1d": "fl", "\x1e": "ffi", "\x1f": "ffl",
          "\x15": "–", "\x16": "—", "\x10": "“", "\x11": "”", "∆": "Δ"}
    for i, page in enumerate(doc):
        text = page.get_text()
        for a, b in T1.items():
            text = text.replace(a, b)
        frags = []
        for line in text.splitlines():
            line = FOOTER.sub("", line).strip()
            if not line:
                continue
            for f in re.split(r"(?<=[.;:?!])\s+", line):
                f = f.strip()
                if len(norm(f)) >= 2:
                    frags.append(f)
        for f in frags:
            total += 1
            # Beamer prints enumerate numbers as text; PowerPoint auto-numbers
            g = re.sub(r"^\d+\s+", "", f)
            if norm(f) not in P and norm(g) not in P:
                missing += 1
                report.append((i + 1, f))
    print(f"v4 pages: {len(doc)}, themed slides: {nslides}")
    print(f"fragments checked: {total}, not found verbatim: {missing}")
    for pg, f in report:
        print(f"  v4 p{pg}: {f!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
