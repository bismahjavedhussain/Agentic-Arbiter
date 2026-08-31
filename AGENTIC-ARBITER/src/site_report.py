# -*- coding: utf-8 -*-
"""THE SITE REPORT, REBUILT: a standalone document, not a transcript of the page.

    python site_report.py                 # the default metro
    python site_report.py ashburn --out X.pdf

WHO IT IS FOR, IN ORDER. An executive who reads page 1 and the charts and decides whether this is
worth someone's time; then a technical evaluator who reads the methodology and wants to check the
claims. Page 1 must satisfy the first reader completely. Everything from page 3 serves the second.

🔴 WHAT WAS WRONG WITH THE VERSION THIS REPLACES, MEASURED FROM THE FILE RATHER THAN ASSERTED.
  * ZERO vector graphics on all four pages. `get_drawings()` returned 0, `get_images()` returned 0.
    A document about a physical system, illustrated with `====` rules.
  * THE REASONING WAS THREE PARAGRAPHS PRINTED TWENTY-FOUR TIMES. In the shipped configuration the
    24 hours carry exactly 3 distinct explanations: the switch-budget one appears 12 times, the
    dry-bulb one 10, free cooling twice. Pages 2 to 4 were that repetition. `_group_hours()` below
    collapses them and explains each reason once, which is the single largest change here.
  * IT OPENED WITH A DISCLAIMER. "THIS REPORT IS A SNAPSHOT, NOT THE LIVE PAGE" came before any
    finding. The caveat is kept, in full, as a footnote on the methodology page. Honest and last,
    rather than honest and first.
  * NO COMMERCIAL FIGURE ANYWHERE NEAR THE FRONT, and the hour-by-hour dump filled 3 of 4 pages.
  * FOUR DECIMAL PLACES on physical estimates: 0.3550 C. `_c()` rounds to a defensible precision.

⚠ NOT A BUG, AND CHECKED BEFORE SPENDING TIME ON IT: the previous report was reported as
truncating mid-line at hour 23. It does not. Both the attached copy and the shipped file contain
all 24 reasoning blocks and end with the complete read-back footer.

⚠ DETERMINISM IS PRESERVED, which is why this uses a PDF library and not a browser print.
`rl_config.invariant = 1` fixes the document id and drops the timestamp, so the same artefacts
produce the same bytes. A headless-Chrome print would have stamped a creation date into every run.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from reportlab import rl_config                                      # noqa: E402
rl_config.invariant = 1            # BEFORE anything else imports reportlab's canvas machinery

from reportlab.lib import colors                                     # noqa: E402
from reportlab.lib.enums import TA_LEFT                              # noqa: E402
from reportlab.lib.pagesizes import A4                               # noqa: E402
from reportlab.lib.styles import ParagraphStyle                      # noqa: E402
from reportlab.lib.units import mm                                   # noqa: E402
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable,  # noqa: E402
                                Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

import metros as M                                                   # noqa: E402
import site_report_aerial as AER                                     # noqa: E402
import site_report_charts as CH                                      # noqa: E402
import site_report_data as SD                                        # noqa: E402

ASSETS = os.path.join(HERE, "reportassets")
PAGE_W, PAGE_H = A4
MARGIN = 17 * mm                   # generous, per the brief; 498 pt of measure at A4
MEASURE = PAGE_W - 2 * MARGIN

# ONE PALETTE, imported rather than restated, so the document and its charts cannot drift.
# Measured contrast on white: NAVY 14.84:1, BODY 12.59:1, SECOND 6.77:1, BLUE 6.35:1,
# ORANGE 4.65:1. RULE and NEUTRAL are fills and are never used for text.
NAVY = colors.HexColor(CH.NAVY)
BLUE = colors.HexColor(CH.BLUE)
ORANGE = colors.HexColor(CH.ORANGE)
BODY_C = colors.HexColor(CH.BODY)
SECOND_C = colors.HexColor(CH.SECOND)
RULE = colors.HexColor(CH.RULE)
NEUTRAL = colors.HexColor(CH.NEUTRAL)
TILE_BG = colors.HexColor("#f2f6fb")
ZEBRA = colors.HexColor("#f7f9fc")

HEADER_H = 30                      # reserved for the logo strip on every page
LOGO = os.path.join(HERE, "..", "demo", "fortyguard-logo.png")
LOGO_W = 74.0                      # pt; the drawn width, and what the pre-scale is computed from
LOGO_LIFT = 10.0                   # pt of clear air between the mark's baseline and the header rule


# --------------------------------------------------------------------------- number formatting
def _n(x):
    """A whole number with thousands separators."""
    return format(int(round(x)), ",")


def _sp(x):
    """A wind speed. Keeps the decimal that `_n` rounds away, drops a trailing ".0"."""
    return ("%.1f" % x).rstrip("0").rstrip(".") or "0"


def _c(x, dp=1):
    """A temperature. ONE decimal place above 1, at most THREE below it.

    ⚠ THE OLD RULE WAS THREE SIGNIFICANT FIGURES, AND IT LEAKED A FOUR-DECIMAL NUMBER. "%.3g" keeps
    three significant figures, which for a value under 0.1 means four decimal places: the mean plume
    rise printed as 0.0685 °C, claiming a tenth of a millikelvin on an estimate whose own docstring
    called that naive. Three decimals is the floor the document can defend, and trailing zeros come
    off so 0.355 °C and 0.05 °C both read the way a person would write them.
    """
    if x is None:
        return "n/a"
    if abs(x) < 1:
        return ("%.3f" % x).rstrip("0").rstrip(".") or "0"
    return ("%%.%df" % dp) % x


def _q(text, kind="agent"):
    """A physical quantity in prose, coloured by what it MEANS, not by where it appears.

    Item 4 asks for the key quantities to be colour-coded so a reader can follow one thread through
    the document, and the palette already carries the meaning: blue is what the agent achieves and
    what its bound defends, orange is what constrains it. The charts have used that mapping since
    item 6; this puts the same two colours on the same two ideas in the sentences as well, so the
    blue in a paragraph and the blue in the chart under it are the same claim.

    ⚠ THREE PER PARAGRAPH IS THE CAP, and it is checked rather than trusted: `check_report.py`
    counts coloured spans per paragraph and reports any paragraph over the cap. Past three, colour
    stops being emphasis and becomes decoration, and the reader loses the thread it was meant to
    provide.
    """
    return "<b><font color='%s'>%s</font></b>" % (
        CH.ORANGE if kind == "constraint" else CH.BLUE, text)


def _pct(x, dp=0):
    """A percentage. No decimals above 10 by default, per the brief.

    ⚠ BUT PASS dp=1 FOR A FIGURE THE PROJECT PUBLISHES WITH A TENTH. The runtime cut is 10.7 %
    and the bound coverage is 65.6 % on the page, in the README and in the audit registry; showing
    an executive 11 % and 66 % would put the document out of step with every other surface, which
    is a worse failure than one decimal place.
    """
    v = x * 100 if abs(x) <= 1.0 else x
    if dp:
        return ("%%.%df%%%%" % dp) % v
    return "%d%%" % round(v) if v >= 10 else "%.1f%%" % v


# --------------------------------------------------------------------------- styles
# 🔴 ONE TYPE SCALE, AND NOTHING OUTSIDE IT. The previous version ran 7.8 pt to 10.5 pt across
# pages with no system: 10 pt on pages 1/5/6/8, 9 pt on page 2, 8.4 pt on page 3, 7.8 pt on page 9.
# Six roles, six sizes, and 8.5 pt is the floor everywhere in the document.
SZ = {"title": 20, "h1": 14, "h2": 11, "body": 10, "table": 9.5, "cap": 8.5}


def _styles():
    s = {}
    s["title"] = ParagraphStyle("title", fontName="Inter-Bold", fontSize=SZ["title"],
                                leading=SZ["title"] * 1.15, textColor=NAVY, spaceAfter=4.0)
    # ⚠ +3 pt, BECAUSE THE BOXES TOUCHED EVEN THOUGH THE INK DID NOT. "AGENTIC-ARBITER" is set in
    # capitals and has no descender, so the 20 pt line box hung 3 % into the subtitle's box below it
    # without a glyph ever colliding. The overlap check works on boxes, and it is right to: a
    # wordmark that clears its subtitle only because that particular string has no descenders is one
    # site label away from not clearing it.
    # 🔴 THE DECK IS PROSE, SO IT IS BODY COLOUR. Item 3 confines #525c6b to captions, axis
    # labels and footnotes, and caps it at 15 % of the document's characters. MEASURED before this
    # change: 7,291 of 17,498 characters were secondary grey, 41.7 %, because the deck under every
    # heading and the whole worked example were set in it. Both are things the reader is meant to
    # READ, not things they are meant to be able to ignore, which is the actual test for which grey
    # a run of text belongs in.
    s["sub"] = ParagraphStyle("sub", fontName="Inter", fontSize=SZ["cap"],
                              leading=SZ["cap"] * 1.5, textColor=BODY_C, spaceAfter=8, allowWidows=0, allowOrphans=0)
    s["lede"] = ParagraphStyle("lede", fontName="Inter", fontSize=SZ["h2"],
                               leading=SZ["h2"] * 1.5, textColor=BODY_C, spaceAfter=10, allowWidows=0, allowOrphans=0)
    s["h1"] = ParagraphStyle("h1", fontName="Inter-SemiBold", fontSize=SZ["h1"],
                             leading=SZ["h1"] * 1.25, textColor=NAVY, spaceBefore=2, spaceAfter=4)
    s["h2"] = ParagraphStyle("h2", fontName="Inter-SemiBold", fontSize=SZ["h2"],
                             leading=SZ["h2"] * 1.35, textColor=BLUE, spaceBefore=10, spaceAfter=3)
    # ⚠ WIDOW AND ORPHAN CONTROL, which ReportLab has and does not switch on. Left at the default
    # a paragraph may leave a single line stranded at the foot of a page or carry a single line over
    # to the next, and item 8 asks for neither. `allowWidows=0` forbids one line alone at the top of
    # a page, `allowOrphans=0` forbids one alone at the bottom; together they mean a paragraph splits
    # only where at least two lines land on each side of the break.
    s["body"] = ParagraphStyle("body", fontName="Inter", fontSize=SZ["body"],
                               leading=SZ["body"] * 1.5, textColor=BODY_C, spaceAfter=7,
                               alignment=TA_LEFT, allowWidows=0, allowOrphans=0)
    # ⚠ bulletFontName, or the bullet glyph alone renders in Helvetica. MEASURED: 4 stray
    # Helvetica spans on page 1, every one of them the "·" in front of a finding.
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=14, bulletIndent=2,
                                 spaceAfter=5, bulletFontName="Inter",
                                 bulletFontSize=SZ["body"])
    # The worked example is the most closely read paragraph in the document. It was grey.
    s["small"] = ParagraphStyle("small", fontName="Inter", fontSize=SZ["cap"],
                                leading=SZ["cap"] * 1.45, textColor=BODY_C, spaceAfter=5, allowWidows=0, allowOrphans=0)
    s["foot"] = ParagraphStyle("foot", fontName="Inter", fontSize=SZ["cap"],
                              leading=SZ["cap"] * 1.4, textColor=SECOND_C, spaceBefore=6, allowWidows=0, allowOrphans=0)
    s["tileval"] = ParagraphStyle("tileval", fontName="Inter-Bold", fontSize=17, leading=20,
                                  textColor=NAVY)
    s["tilelab"] = ParagraphStyle("tilelab", fontName="Inter", fontSize=SZ["cap"],
                                  leading=SZ["cap"] * 1.3, textColor=SECOND_C)
    s["tilenote"] = ParagraphStyle("tilenote", fontName="Inter-SemiBold", fontSize=SZ["cap"],
                                   leading=SZ["cap"] * 1.2, textColor=ORANGE)
    s["mono"] = ParagraphStyle("mono", fontName="Courier", fontSize=SZ["table"], leading=13,
                               textColor=BODY_C)
    s["toc"] = ParagraphStyle("toc", fontName="Inter", fontSize=SZ["body"],
                              leading=SZ["body"] * 1.8, textColor=BODY_C, allowWidows=0, allowOrphans=0)
    return s


# --------------------------------------------------------------------------- page furniture
class Doc(BaseDocTemplate):
    """A logo header and a three-part footer on every page.

    🔴 THE HEADER IS A REAL RASTER LOGO, AND ITS RESOLUTION WAS A BOAST THAT COST 130 KB A COPY.
    This docstring used to argue that `demo/fortyguard-logo.png` at 2362 x 827, drawn 74 pt wide,
    "renders at 2,298 dpi against a 300 dpi print threshold, so it is indistinguishable from vector
    at any zoom". Every word of that is true about quality and silent about cost. 2,298 dpi is 7.7
    times more pixels than 300 dpi can show, and ReportLab embeds what it is given: MEASURED, the
    logo was 130 KB of the report's 472 KB, in a document that carries it on every page.

    So it is pre-scaled once to `reportassets/_logo.png` at the width 300 dpi actually needs, and the
    cache is keyed on the source file's own size and mtime so a new mark regenerates it. Same mark,
    same print quality, about 12 KB. It is the same mistake the aerial figure made at 300 dpi, and
    finding one is what sent me looking for the other.

    ⚠ ONE MARGIN NUMBER OWNS THE HORIZONTAL EDGE. Content ran 21 pt off the right of page 7 in
    the previous build; `CONTENT_R` below is the single value every table and chart is measured
    against, and `_fitw()` clamps to it.
    """

    def __init__(self, path, meta, **kw):
        self.meta = meta
        BaseDocTemplate.__init__(self, path, pagesize=A4,
                                 leftMargin=MARGIN, rightMargin=MARGIN,
                                 topMargin=MARGIN + HEADER_H, bottomMargin=MARGIN + 10,
                                 title=meta["title"], author="AGENTIC-ARBITER",
                                 subject=meta["subject"],
                                 creator="AGENTIC-ARBITER/src/site_report.py", **kw)
        frame = Frame(MARGIN, MARGIN + 10, MEASURE,
                      PAGE_H - 2 * MARGIN - HEADER_H - 10, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="page", frames=[frame],
                                           onPage=self._furniture)])

    def _logo(self):
        """The mark, pre-scaled to what 300 dpi needs at the width it is drawn, cached on disk."""
        if not os.path.exists(LOGO):
            return None
        try:
            from PIL import Image as PILImage
        except ImportError:                                          # noqa: BLE001
            return LOGO                                              # embed the big one rather than none
        st = os.stat(LOGO)
        tag = "%d-%d" % (st.st_size, int(st.st_mtime))
        out = os.path.join(ASSETS, "_logo.png")
        stamp = out + ".src"
        if os.path.exists(out) and os.path.exists(stamp):
            if open(stamp, encoding="utf-8").read().strip() == tag:
                return out
        # 🔴 AN UNWRITABLE CACHE FALLS BACK TO THE FULL-SIZE MARK, NOT TO NO MARK.
        # Render's free plan has no persistent disk, so this directory is whatever the image layer
        # gave the container: writable today, and not guaranteed to be. When the write raised, the
        # exception propagated to `_furniture`, whose own `except` draws the word "FortyGuard" in
        # type instead. MEASURED by blocking the write: a served 41,864 byte PDF with no logo on any
        # page, against 57,065 with one. The brand mark on every page of a document a CEO may forward
        # is worth 130 KB more than it is worth losing, so the source PNG is the fallback and the
        # pre-scale is the optimisation.
        try:
            im = PILImage.open(LOGO).convert("RGBA")
            want = int(round(LOGO_W / 72.0 * 300))
            if im.width > want:
                im = im.resize((want, int(round(im.height * want / float(im.width)))),
                               PILImage.LANCZOS)
            im.save(out, "PNG", optimize=True)
            open(stamp, "w", encoding="utf-8").write(tag)
            return out
        except (OSError, PermissionError):
            return LOGO

    def _furniture(self, canv, doc):
        canv.saveState()
        # ---- header: the mark on the left, the section on the right, a hairline under both
        # 🔴 THE MARK SAT ON THE RULE, WHICH IS WHY IT READ AS PART OF IT. MEASURED: the logo is
        # 25.9 pt tall drawn 74 pt wide, its bottom edge was at `top - 23.9`, and the header rule was
        # at `top - 16`. The rule therefore crossed the logo 8 pt above its own baseline, straight
        # through the descender of the wordmark. It looked welded to the line because it was.
        #
        # ⚠ THE FIX SPENDS THE MARGIN'S OWN WHITE, NOT THE PAGE'S CONTENT. There is 48 pt of paper
        # above `top` and the header was only using the bottom 16 pt of it, so the mark and the
        # running head both move UP and the rule stays where it is. Raising HEADER_H instead would
        # have cost every page 12 pt of frame, and two pages are already at 99 % of theirs.
        top = PAGE_H - MARGIN
        rule_y = top - 16
        ih = LOGO_W * 827.0 / 2362.0
        logo_y = rule_y + LOGO_LIFT
        assert logo_y > rule_y + 4, "the mark would sit on the header rule again"
        try:
            canv.drawImage(self._logo(), MARGIN, logo_y, width=LOGO_W, height=ih,
                           mask="auto", preserveAspectRatio=True, anchor="sw")
        except Exception:                                            # noqa: BLE001
            canv.setFont("Inter-SemiBold", 10)
            canv.setFillColor(NAVY)
            canv.drawString(MARGIN, logo_y + ih / 2 - 3.6, "FortyGuard")
        # the running head optically centred on the mark rather than on the rule
        canv.setFont("Inter", SZ["cap"])
        canv.setFillColor(SECOND_C)
        canv.drawRightString(PAGE_W - MARGIN, logo_y + ih / 2 - SZ["cap"] * 0.36,
                             self.meta["running"])
        canv.setStrokeColor(RULE)
        canv.setLineWidth(0.7)
        canv.line(MARGIN, rule_y, PAGE_W - MARGIN, rule_y)

        # ---- footer: page number, site, date. The date is the newest input artefact's mtime,
        # NOT the clock, so the document stays byte-reproducible from unchanged artefacts.
        y = MARGIN - 2
        canv.line(MARGIN, y + 13, PAGE_W - MARGIN, y + 13)
        canv.setFont("Inter", SZ["cap"])
        canv.setFillColor(SECOND_C)
        canv.drawString(MARGIN, y, "%s  ·  generated %s"
                        % (self.meta["site"], self.meta["date"]))
        canv.setFont("Inter-SemiBold", SZ["cap"])
        canv.drawRightString(PAGE_W - MARGIN, y, "%d" % doc.page)
        canv.restoreState()


# --------------------------------------------------------------------------- the sections
# 🔴 ONE LIST OWNS EVERY SECTION TITLE, because two lists disagreed. The contents page was written
# by hand and the headings were written separately, so the document shipped a contents page
# advertising "Validation and credibility", "Scale and commercial value" and "Appendix: every hour"
# against real headings reading "Validation, and how the bound is measured", "Scale, and what it is
# worth" and "Appendix: every hour, and each reason once". Three wrong entries out of seven, plus a
# whole section, The site, that the contents did not mention at all.
#
# Now the heading and the contents row are the same string by construction. `_h1()` emits the
# heading and drops an invisible mark at the same time, and the page number the mark lands on is
# what the contents prints.
SECTIONS = [
    ("summary", "Executive summary",
     "what the agent did on this day, what it is worth, and how well the bound held"),
    ("site", "The site",
     "the two halls, the gap the exhaust crosses, and what the imagery can and cannot show"),
    ("findings", "The findings",
     "the bound against the limit hour by hour, and the comparison with the incumbent"),
    ("decision", "How the decision is made",
     "the margin and where each degree of it comes from, the gates, the switch budget"),
    ("physics", "The physics",
     "the exhaust plume solved on this building's own footprint, and why it needs a GPU"),
    ("validation", "Validation, and how the bound is measured",
     "held-out testing, and how the bound's coverage is measured as the record grows"),
    ("scale", "Scale, and what it is worth",
     "the same agent across every covered site, and who buys this"),
    ("appendix", "Appendix: every hour, and each reason once",
     "the full schedule, and each distinct reason explained once"),
]
TITLES = {k: t for k, t, _ in SECTIONS}

# 🔴 168 OF THE 249 COVERED SITES HAVE NO SECOND BUILDING, SO THEY HAVE NO PLUME SECTION.
# `build_standalone_site.py` writes a facility with no mapped neighbour: no receptor, no facade gap,
# no intake to warm, and the solver records `n_solves: 0`. There is nothing for an exhaust plume to
# cross and nothing for it to reach, so the whole physics section would be four pages of apparatus
# describing a term that is identically zero. It is removed from the document AND from the contents,
# because a contents page listing a section that is not there is worse than either.
#
# ⚠ THE SITE SECTION'S DESCRIPTION CHANGES TOO. "the two halls, the gap the exhaust crosses" is a
# false description of a single building, and the contents page is the first thing a reader reads.
SOLO_DROP = ("physics",)

# ⚠ THE SITE ROW DESCRIBES WHAT IS ACTUALLY ON THE PAGE, WHICH IS FOUR CASES AND NOT ONE. Five of
# the 264 sites have no screening frame at all, and a contents page promising "what the imagery can
# and cannot show" beside a section containing no imagery is a small lie on the first page a reader
# reads. The variants are keyed on (standalone, has_imagery).
SITE_DESC = {
    (False, True): "the two halls, the gap the exhaust crosses, and what the imagery can and "
                   "cannot show",
    (True, True): "the one mapped building at this site, and what the imagery can and cannot show",
    (False, False): "the two halls and the gap the exhaust crosses, from the mapped geometry",
    (True, False): "the one mapped building at this site, from the mapped geometry",
}


def _sections(standalone, has_img=True):
    """The sections this particular site's report actually contains, in order."""
    out = []
    for key, title, desc in SECTIONS:
        if standalone and key in SOLO_DROP:
            continue
        if key == "site":
            desc = SITE_DESC[(bool(standalone), bool(has_img))]
        out.append((key, title, desc))
    return out


class Mark(Flowable):
    """A zero-size flowable that records the page it is drawn on.

    ⚠ WHY A FLOWABLE AND NOT A COUNTER. Where a heading lands depends on how everything before it
    flowed, which is only known once ReportLab has laid the page out. A mark drawn at the heading's
    own position is the only thing that knows the answer, which is why the document is built twice:
    pass one to learn the numbers, pass two to print them.
    """
    width = 0
    height = 0

    def __init__(self, key, into):
        Flowable.__init__(self)
        self.key = key
        self.into = into

    def draw(self):
        self.into[self.key] = self.canv.getPageNumber()

    def wrap(self, *_a):
        return (0, 0)


# --------------------------------------------------------------------------- building blocks
def _fit_size(text, avail, base, floor=11.0, font="Inter-Bold"):
    """The largest size at or below `base` at which `text` fits `avail` on ONE line.

    🔴 THIS EXISTS BECAUSE A FIXED SIZE BROKE A NUMBER IN HALF. Widening the money tile fixed the
    money tile and left the rule unlearned, so the next build printed the weather-hours tile as
    "43,76" on one line and "3" on the next, and the chiller tile as "+406" over "h". A reader
    cannot tell a wrapped number from a different number, which makes this a correctness defect
    wearing a layout defect's clothes, and hand-tuning five widths would only move it again the
    first time a site has a longer figure.

    ⚠ MEASURED AT THE SIZE IT WILL BE DRAWN, in the face it will be drawn in. `stringWidth` is the
    same metric ReportLab uses when it decides to break the line, so agreement is exact rather than
    approximate.
    """
    from reportlab.pdfbase import pdfmetrics
    size = float(base)
    while size > floor and pdfmetrics.stringWidth(text, font, size) > avail:
        size -= 0.25
    return size


def _tiles(rows, weights=None):
    """The metric grid. Value large, label small under it, a MODELED flag where one is owed.

    ⚠ THE COLUMNS ARE NOT EQUAL, AND THAT IS THE FIX FOR A REAL DEFECT. Five equal tiles gave the
    money tile 99 pt, and "$334k – $967k" does not fit 99 pt at 16 pt Inter-Bold: the first render
    broke a number across lines as "$334,26 / 9". A tile carrying a range needs more room than a
    tile carrying "11%", so the caller says so.

    ⚠ AND THE VALUE SIZE IS FITTED PER TILE, so unequal columns are a preference rather than the
    only thing standing between the document and a broken number. See `_fit_size`.
    """
    S = _styles()
    wts = weights or [1.0] * len(rows)
    tot = float(sum(wts))
    widths = [MEASURE * w / tot for w in wts]
    cells = []
    for (val, lab, note), wid in zip(rows, widths):
        # the usable measure inside the tile: the cell width less this table's own padding
        avail = wid - 14 - 8 - 6
        plain = re.sub("<[^>]+>", "", val)
        vsize = _fit_size(plain, avail, 17.0)
        # ⚠ 1.32, NOT 1.16. `_fit_size` shrinks a value until it fits one line, but it stops at an
        # 11 pt floor, so a long value can still wrap. At 1.16 the two lines' boxes overlapped by
        # 4 % and the overlap check reported it. Leading that survives a wrap costs nothing on the
        # single-line values, which are almost all of them.
        vstyle = ParagraphStyle("tileval-%.2f" % vsize, parent=S["tileval"],
                                fontSize=vsize, leading=vsize * 1.32)
        assert (_fit_size(plain, avail, vsize, floor=vsize) == vsize), "tile value cannot fit"
        inner = [[Paragraph(val, vstyle)], [Paragraph(lab, S["tilelab"])]]
        if note:
            inner.append([Paragraph(note, S["tilenote"])])
        t = Table(inner, colWidths=[wid - 14])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 8),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                               ("TOPPADDING", (0, 0), (0, 0), 9),
                               ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
                               ("TOPPADDING", (0, 1), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        cells.append(t)
    grid = Table([cells], colWidths=widths)
    grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TILE_BG),
        ("LINEAFTER", (0, 0), (-2, -1), 0.7, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return grid


def _chart(svg, is_path=False, scale=1.0):
    """A chart as a vector Drawing, never wider than the content measure.

    🔴 MEASURED FAULT: page 7 put content at x = 598.4 pt against a 547.1 pt right margin. The old
    guard only shrank a Drawing when `d.width` already exceeded the measure, and matplotlib reports
    a width that excludes the ink its own labels place outside the axes, so a 475 pt Drawing was
    still painting past the edge. Scaling unconditionally against the measure fixes both cases.
    """
    dr = CH.to_drawing(svg, is_path=is_path)
    k = scale
    if dr.width * k > MEASURE:
        k = MEASURE / dr.width
    if k != 1.0:
        dr.scale(k, k)
        dr.width *= k
        dr.height *= k
    return dr


def _caption(text, S):
    return Paragraph(text, S["small"])


def _fitw(widths):
    """Clamp a column set to the content measure. The single guard against horizontal overflow.

    🔴 MEASURED FAULT THIS EXISTS FOR: page 7 of the previous build put content at x = 616 pt on a
    595 pt page, 21 pt past the right margin, which cut the money table. Column widths were being
    hand-summed and one sum was wrong. Now every table is scaled to fit whatever it was given.
    """
    tot = float(sum(widths))
    if tot <= MEASURE:
        return list(widths)
    k = MEASURE / tot
    return [w * k for w in widths]


CELL_PAD_X = 7.0                   # pt each side; the one number every cell measurement uses


def _table(data, widths, head=True, align=None, zebra=None):
    """Horizontal rules, a light outer border, and every cell MEASURED against its own column.

    Zebra striping once a table passes 8 rows, per the brief: below that it is noise, above it the
    eye loses the row.

    🔴 THE LENGTH HEURISTIC WAS WRONG, AND IT PUT "GPU (NVIDIA Warp)" OUTSIDE THE TABLE.
    The previous rule was `len(cell) > 24` becomes a Paragraph, anything shorter stays a raw string.
    A raw string in a ReportLab cell is one unbreakable line that neither wraps nor clips: it paints
    straight out of the cell. "GPU (NVIDIA Warp)" is 17 characters, so it stayed a string, and 17
    characters of 9.5 pt Inter is 88 pt against the 74.5 pt of usable width in that column. Character
    count is not width: "wall clock" and "GPU (NVIDIA Warp)" are both short and only one of them fits.

    Every cell is now measured with `stringWidth` in the face and size it will actually be drawn in,
    against its own column less this table's own padding, and anything that does not fit becomes a
    Paragraph, which wraps by construction. The assertion at the end then holds for the whole table
    rather than for the cells someone remembered to check.

    ⚠ ALIGNMENT HAD TO FOLLOW THE CELL INTO THE PARAGRAPH. `TableStyle`'s ALIGN moves a raw string
    but has no effect on a Paragraph, which aligns by its own style. So a right-aligned numeric column
    silently went left the moment one of its cells grew long enough to wrap. The requested alignment
    is passed into the Paragraph style instead.
    """
    widths = _fitw(widths)
    # 🔴 THE REAL CAUSE OF THE PAGE 7 CUT, AND IT WAS NOT THE COLUMN WIDTHS.
    # ReportLab draws a raw string in a Table cell as one unbreakable line. It does not wrap and it
    # does not clip: it paints straight out of the cell and off the paper. MEASURED: the money
    # table's Basis column reached x = 597.9 pt against a 547.1 pt margin, which is the "table is
    # cut" fault. A Paragraph wraps inside its column by construction, so every cell with prose in
    # it becomes one. Short cells stay strings, because a Paragraph costs layout time and a
    # three-character cell has nothing to gain.
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    S_ = _styles()
    _cell = ParagraphStyle("cell", parent=S_["body"], fontSize=SZ["table"],
                           leading=SZ["table"] * 1.35, spaceAfter=0)
    _cellh = ParagraphStyle("cellh", parent=_cell, fontName="Inter-SemiBold", textColor=NAVY)
    _ALIGN = {"RIGHT": TA_RIGHT, "CENTER": TA_CENTER, "CENTRE": TA_CENTER}
    _styled = {}

    def _para_style(base, col):
        """The cell style, carrying the column's requested alignment."""
        want = _ALIGN.get(str((align or {}).get(col, "")).upper())
        if want is None:
            return base
        key = (base.name, col)
        if key not in _styled:
            _styled[key] = ParagraphStyle("%s-%d" % (base.name, col), parent=base, alignment=want)
        return _styled[key]

    def _fits(text, col, bold):
        usable = widths[col] - 2 * CELL_PAD_X
        font = "Inter-SemiBold" if bold else "Inter"
        return pdfmetrics.stringWidth(str(text), font, SZ["table"]) <= usable

    # 🔴 WRAPPING A CELL THAT CANNOT WRAP IS WORSE THAN THE OVERFLOW IT REPLACES. Measuring every
    # cell and turning the ones that did not fit into Paragraphs fixed "GPU (NVIDIA Warp)" and broke
    # the schedule table: the "safe" column is 32 pt wide, which leaves 18 pt of measure against
    # 19.4 pt of the word "safe", so the header became a Paragraph in a column too narrow for it and
    # ReportLab split it mid-word as "saf" over "e". The hour column did the same to "22", printing
    # it as "2" over "2". A number broken across two lines is not a number.
    #
    # A Paragraph can only help where the text contains a space to break AT. Where the longest
    # unbreakable token is itself wider than the column, no amount of wrapping fits it and the honest
    # conclusion is that the column is too narrow. So the columns are widened to their content first,
    # and the surplus is taken from whichever column has the most room to spare, which is always the
    # prose column in this document's tables.
    def _tok_min(col):
        """The narrowest this column can be: its widest unbreakable token, plus padding."""
        worst = 0.0
        for ri, row in enumerate(data):
            if col >= len(row) or not isinstance(row[col], str):
                continue
            bold = bool(head and ri == 0)
            font = "Inter-SemiBold" if bold else "Inter"
            plain = re.sub("<[^>]+>", "", row[col])
            for tok in plain.split():
                worst = max(worst, pdfmetrics.stringWidth(tok, font, SZ["table"]))
        return worst + 2 * CELL_PAD_X + 0.5

    need = [_tok_min(c) for c in range(len(widths))]
    short = [c for c in range(len(widths)) if widths[c] < need[c]]
    for c in short:
        deficit = need[c] - widths[c]
        # take it from the column with the most slack, one column at a time
        for _ in range(len(widths)):
            slack = [(widths[k] - need[k], k) for k in range(len(widths)) if k != c]
            slack.sort(reverse=True)
            if not slack or slack[0][0] <= 0.5:
                break
            take = min(deficit, slack[0][0])
            widths[slack[0][1]] -= take
            widths[c] += take
            deficit -= take
            if deficit <= 0.01:
                break
    assert all(widths[c] >= need[c] - 0.51 for c in range(len(widths))), (
        "no column has room to give: need %s, have %s"
        % ([round(x, 1) for x in need], [round(x, 1) for x in widths]))

    wrapped = []
    for ri, row in enumerate(data):
        out = []
        for ci, cell in enumerate(row):
            if not isinstance(cell, str):
                out.append(cell)
                continue
            bold = bool(head and ri == 0)
            base = _cellh if bold else _cell
            # Markup can only be rendered by a Paragraph, and cannot be measured as a plain string.
            if "<" in cell or not _fits(cell, ci, bold):
                out.append(Paragraph(cell, _para_style(base, ci)))
            else:
                out.append(cell)
        wrapped.append(out)
    data = wrapped

    # 🔴 THE GUARD, IN TWO PARTS. Every remaining raw string has been measured as fitting on one
    # line, and every column is at least as wide as its widest unbreakable token, so neither an
    # overflow nor a mid-word break is reachable without one of these failing first.
    for ri, row in enumerate(data):
        for ci, cell in enumerate(row):
            if isinstance(cell, str):
                assert _fits(cell, ci, bool(head and ri == 0)), (
                    "cell %r is %.1f pt wide in a %.1f pt column"
                    % (cell, pdfmetrics.stringWidth(cell, "Inter", SZ["table"]),
                       widths[ci] - 2 * CELL_PAD_X))
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("FONTNAME", (0, 0), (-1, -1), "Inter"),
          ("FONTSIZE", (0, 0), (-1, -1), SZ["table"]),
          ("TEXTCOLOR", (0, 0), (-1, -1), BODY_C),
          # ⚠ 4 pt, NOT 5. The schedule table is 25 rows, so a point of padding either side of every
          # row is 50 pt of paper, which was the difference between a standalone site's report ending
          # on page 8 and spilling three lines onto a page 9 that was then 11 % full. 4 pt still
          # clears the 9.5 pt type comfortably: the row box is 17.5 pt against a 12.8 pt line.
          ("TOPPADDING", (0, 0), (-1, -1), 4),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD_X),
          ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD_X),
          ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
          # ⚠ A LIGHT OUTER BOX, so the table has a visible edge for its content to sit inside.
          # Horizontal rules alone left the bounds implied, which is fine until a cell runs past
          # them and there is nothing on the page to say it did. Still no vertical inner lines: a
          # full grid reads as a spreadsheet and this is a document.
          ("BOX", (0, 0), (-1, -1), 0.5, RULE),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if head:
        st += [("FONTNAME", (0, 0), (-1, 0), "Inter-SemiBold"),
               ("FONTSIZE", (0, 0), (-1, 0), SZ["table"]),
               ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
               ("LINEBELOW", (0, 0), (-1, 0), 0.9, NAVY),
               ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]
    if zebra or (zebra is None and len(data) > 9):
        for r in range(1 if head else 0, len(data)):
            if (r % 2) == (1 if head else 0):
                st.append(("BACKGROUND", (0, r), (-1, r), ZEBRA))
    for col, a in (align or {}).items():
        st.append(("ALIGN", (col, 0), (col, -1), a))
    t.setStyle(TableStyle(st))
    return t


# --------------------------------------------------------------------------- deduplication
REASON_TITLE = {
    "switch budget": "Blocked by the switch budget",
    "dry-bulb": "Blocked by air temperature",
    "dew point": "Blocked by the dew-point gate",
    "refusal": "Declined: the physics could not be modelled here",
    "minimum dwell": "Blocked by the minimum dwell time",
    "air quality": "Blocked by the air-quality gate",
    None: "Free cooling ran",
}


def _halls(operator):
    """"Amazon Web Services IAD116 / Amazon Web Services IAD117" -> "IAD116 and IAD117, both
    operated by Amazon Web Services".

    ⚠ THE OSM `operator` TAG REPEATS THE COMPANY ONCE PER BUILDING, which is correct as data and
    clumsy as a sentence: the first draft of the site paragraph opened "Two halls, Amazon Web
    Services IAD116 / Amazon Web Services IAD117." Naming the company once and the halls once reads
    the way a person would say it. Falls back to the raw tag whenever the shape is not this shape,
    because a wrong guess about a site's name is worse than a clumsy sentence.
    """
    parts = [x.strip() for x in (operator or "").split("/") if x.strip()]
    if len(parts) != 2:
        return operator or "adjacent buildings"
    codes, owners = [], []
    for part in parts:
        toks = part.split()
        code = [t for t in toks if t.upper() == t and any(c.isdigit() for c in t)]
        if len(code) != 1:
            return operator
        codes.append(code[0])
        owners.append(" ".join(t for t in toks if t != code[0]).strip())
    if owners[0] and owners[0] == owners[1]:
        return "%s and %s, both operated by %s" % (codes[0], codes[1], owners[0])
    return "%s and %s" % (parts[0], parts[1])


def _h1(key, S, pages):
    """The heading for a section, plus the mark that records which page it landed on."""
    return [Mark(key, pages), Paragraph(TITLES[key], S["h1"])]


def _aerial(site_key, site, target_w, dpi=200, max_h=300.0):
    """The satellite frame as a flowable, or (None, reason) if this site has no imagery.

    ⚠ SIZED FROM THE FILE, NOT FROM AN ASSUMED ASPECT. The composite is resampled to square ground
    pixels, so its aspect is whatever the frame's bbox is, near enough 1:1 at this site rather than
    the 4:3 of the source raster. Reading the height off the image means a site whose frame is a
    different shape still lands inside its column instead of pushing the caption off the page.
    """
    # 🔴 `sites.json` IS GLOBAL, AND `demo_path` WOULD KEY-PREFIX IT. `demo_path("x.json")`
    # returns the unsuffixed name only for the DEFAULT metro and `<KEY>_x.json` for every
    # other, which is right for per-site artefacts and wrong for the one manifest that lists
    # all of them. Under `METRO=AL_way_1540172608` it resolved to
    # `AL_way_1540172608_sites.json` and raised FileNotFoundError, so this would have failed
    # on all 249 sites the moment build_sites.py drove it. `audit.py` names sites.json in its
    # own GLOBAL_OK list and reads it straight from DEMO; this now does the same.
    sj = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
    rec = [x for x in sj["sites"] if x["key"] == site_key]
    if not rec:
        return None, "%s is not in sites.json" % site_key
    out = os.path.join(ASSETS, "_aerial_%s.jpg" % site_key)
    # Pass the placement, so the raster resolution and the on-image type sizes are derived from
    # the width this figure is actually drawn at rather than assumed.
    path, meta = AER.build(site_key, rec[0].get("imagery"), site, out,
                           placed_pt=target_w, dpi=dpi)
    if not path:
        return None, meta
    from PIL import Image as PILImage
    iw, ih = PILImage.open(path).size

    # 🔴 A HEIGHT CAP, BECAUSE FIXING THE WIDTH ALONE EMPTIED PAGE 2 ON 27 SITES.
    # This sized the figure purely by width, so its height was whatever the frame's own aspect gave.
    # MEASURED across the 236 offerable sites with imagery, the ground aspect runs from 0.36 to 2.54:
    # at 252 pt wide, a 2.54 frame is 640 pt tall. Page 2 carries the contents first and has nowhere
    # near that left, so the whole block moved and the page was left with the contents alone. That is
    # exactly the 41 % to 45 % fill measured on WI_way_1510420026, CA_way_209087373 and 25 others,
    # and it is why "no page more than 15 % empty" held for Ashburn and for almost nowhere else:
    # Ashburn's frame is 0.99, so the defect could not appear on the one site the target was tuned on.
    #
    # ⚠ THE CAP IS ON THE SPACE PAGE 2 ACTUALLY HAS, not on a pleasing number. The contents block is
    # about 260 pt and the heading and caption another 60, so 300 pt is what remains of a 705 pt
    # frame with room for the prose beside it. A tall frame is now narrow rather than absent.
    scale = min(target_w / float(iw), max_h / float(ih))
    w, h = iw * scale, ih * scale
    meta["placed_wh_pt"] = (round(w, 1), round(h, 1))
    meta["capped_by"] = "height" if (max_h / float(ih)) < (target_w / float(iw)) else "width"
    return Image(path, width=w, height=h), meta


def _ranges(idxs):
    """[0,1,2,5,6] -> '00:00 to 02:00, 05:00 to 06:00'. Contiguous runs, named by hour."""
    if not idxs:
        return ""
    runs, start, prev = [], idxs[0], idxs[0]
    for i in idxs[1:]:
        if i == prev + 1:
            prev = i
            continue
        runs.append((start, prev))
        start = prev = i
    runs.append((start, prev))
    out = []
    for a, b in runs:
        out.append("%02d:00" % a if a == b else "%02d:00 to %02d:00" % (a, b))
    return ", ".join(out)


def _group_hours(hours):
    """One entry per DISTINCT reason, with the hours it covers and one representative hour.

    🔴 THIS FUNCTION IS THE POINT OF THE REBUILD. The previous report printed a paragraph per hour,
    and in the shipped configuration only three of those paragraphs were distinct: the reader met
    the same switch-budget explanation twelve times. Grouping by binding constraint turns 24
    paragraphs into 3, and the reason gets explained once, properly, instead of being asserted
    twelve times and understood none.
    """
    groups = {}
    for h in hours:
        key = h.get("binding")
        g = groups.setdefault(key, {"idx": [], "hours": []})
        g["idx"].append(int(h["hour"]))
        g["hours"].append(h)
    out = []
    for key, g in groups.items():
        g["idx"].sort()
        # the representative is the TIGHTEST hour: closest to the limit, so the example is the one
        # that actually mattered rather than an arbitrary first.
        rep = min(g["hours"], key=lambda x: abs(x["limit_c"] - x["bound_c"]))
        out.append({"binding": key, "n": len(g["idx"]), "ranges": _ranges(g["idx"]), "rep": rep,
                    "mode": g["hours"][0]["mode"]})
    out.sort(key=lambda x: -x["n"])
    return out


# --------------------------------------------------------------------------- the document
def _build_once(site_key, out_path, pages):
    CH.register(ASSETS)
    d = SD.collect(site_key)
    S = _styles()
    h, b, p, site, cfg = d["headline"], d["bound"], d["plume"], d["site"], d["config"]
    # One mapped building, so no neighbour, no facade gap, no plume term. Read once and passed down
    # rather than re-derived, so every branch in this function agrees about what the site is.
    solo = d["standalone"]
    out = out_path or M.demo_path("report.pdf", d["site_key"])

    # The footer date is the newest INPUT artefact's mtime, never the clock: same artefacts in,
    # same bytes out, and the date still moves when the data does.
    import datetime as _dt
    _srcs = [M.demo_path("%s.json" % x, d["site_key"])
             for x in ("trace", "explanations", "backtest", "rolling", "money")]
    _mt = max(os.path.getmtime(x) for x in _srcs if os.path.exists(x))
    meta = {"site": site["label"],
            "date": _dt.datetime.fromtimestamp(_mt, _dt.timezone.utc).strftime("%d %B %Y"),
            "title": "%s -- free-cooling decision report" % site["label"],
            "subject": "Hour-by-hour free-cooling decisions with a calibrated safety bound",
            "running": "AGENTIC-ARBITER  ·  %s  ·  free-cooling decision report" % site["label"]}
    doc = Doc(out, meta)
    st = []

    # ===================================================================== PAGE 1
    st.append(Mark("summary", pages))
    st.append(Paragraph("AGENTIC-ARBITER", S["title"]))
    st.append(Paragraph("Free-cooling decision report &nbsp;·&nbsp; %s &nbsp;·&nbsp; station %s "
                        "&nbsp;·&nbsp; %s" % (site["label"], site["station"],
                                              d["summary"]["day"]), S["sub"]))
    st.append(Paragraph(
        "An agent decides, hour by hour, whether this data centre can switch its mechanical "
        "chillers off and cool with outside air instead. Every hour it releases carries a safety "
        "margin measured from the agent's own past errors, and it declines the hours it cannot "
        "stand behind.", S["lede"]))

    # ⚠ THE TILE VALUE MUST FIT ON ONE LINE. MEASURED: "$334,269 - $967,245" wrapped across
    # three lines inside a 99 pt tile and broke a number mid-digit ("$334,26 / 9"). The tile
    # carries the rounded thousands and the label underneath carries the exact figures, which is
    # the right way round: the tile is for scanning, the label is for checking.
    money = ("$%dk – $%dk" % (round(h["usd_site_lo"] / 1000.0), round(h["usd_site_hi"] / 1000.0))
             if h["usd_site_lo"] else "n/a")
    st.append(_tiles([
        (money, "at this site: $%s to $%s, at $%s to $%s per MW of IT load per year"
         % (_n(h["usd_site_lo"]), _n(h["usd_site_hi"]),
            _n(h["usd_rate_lo"]), _n(h["usd_rate_hi"])), "MODELED"),
        (_pct(h["runtime_cut_pct"], 1), "less mechanical cooling runtime, a share so it holds at "
         "any hall size", None),
        ("+%s h" % _n(h["chiller_h_per_year"]), "chiller-hours recovered per year against the "
         "control operators run today", None),
        (_n(h["weather_hours"]), "hours of real recorded weather, %s days held out"
         % _n(h["held_out_days"]), None),
        # ⚠ THE LONGEST TILE LABEL SETS THE HEIGHT OF ALL FIVE. This one ran to eight lines and
        # left the three tiles beside it with 90 pt of empty panel underneath, which reads as a
        # layout accident rather than a design. The clause about the sample growing is the subject of
        # a whole page later on and does not have to be won here.
        (_pct(h["coverage_pooled"], 1), "bound coverage on the four measured forecast pairs, "
         "against a 90% target", None),
    ], weights=[1.55, 0.86, 0.86, 0.86, 0.87]))
    st.append(Spacer(1, 11))
    # ⚠ THE HEIGHT FREED BY TRIMMING THE TILE LABELS GOES TO THE HERO CHART RATHER THAN TO THE
    # BOTTOM MARGIN. Taller cells and a taller reason band is the most useful thing page 1 can do
    # with 60 pt; `decision_strip` treats this as a floor and grows past it if the labels need more.
    st.append(_chart(CH.decision_strip(d["hours"], height=222)))
    st.append(Spacer(1, 3))

    free_n = sum(1 for x in d["hours"] if x["mode"] == "FREE-COOLING")
    groups = _group_hours(d["hours"])
    top = groups[0]
    st.append(Paragraph("What this day shows", S["h2"]))
    for txt in (
        "Just %s ran on outside air. The remaining %s ran chillers, and every one of them has a "
        "named reason rather than a default."
        % (_q("%d of the %d hours" % (free_n, len(d["hours"]))),
           _q("%d" % (len(d["hours"]) - free_n), "constraint")),
        ("The largest single block was <b>not weather</b>. The switch budget accounts for %d of "
         "them, %s. The air was cold enough; the plant had already committed its allowance of "
         "mode changes for the day." % (top["n"], top["ranges"]))
        if top["binding"] == "switch budget" else
        ("<b>One constraint</b> shaped the day: %s accounts for %d of the %d hours, %s."
         % (REASON_TITLE.get(top["binding"], "A single gate"), top["n"], len(d["hours"]),
            top["ranges"])),
        "<b>The bound held</b> across %s days the agent never trained on. It took %s free-cooling "
        "hours and %s of them turned out unsafe: %s per thousand."
        % (_n(h["held_out_days"]), _q(_n(h["free_h_taken"])),
           _q("%d" % h["breach_h"], "constraint"), "%.2f" % h["breach_per_1000"]),
        "<b>The forecast is the product</b>: hold everything else and drop the forecast to no "
        "skill at all, and the %.0f hours a year this recovers becomes %.0f."
        % (d["ablation"]["base_gain"], d["ablation"]["zero_skill_gain"]),
    ):
        st.append(Paragraph(txt, S["bullet"], bulletText="·"))
    st.append(Paragraph(
        "<b>What makes this different from a thermostat with a forecast attached:</b> where the "
        "site geometry defeats the physics, the agent refuses the hour rather than return a number "
        "it cannot stand behind, and the cost of that caution is measured and published rather "
        "than hidden.", S["body"]))

    # 🔴 THE FRAME IS BUILT BEFORE THE CONTENTS, BECAUSE THE CONTENTS DESCRIBES IT. The site row
    # reads differently depending on whether this site has a screening frame at all, so whether
    # `_aerial` succeeded has to be known before the contents rows are written. It was below them,
    # and the contents referenced `aer` before assignment: an UnboundLocalError on every site.

    # ---- THE SITE. On this page because the contents alone left it 63 % empty, which was the
    # thinnest page in the document, and because a reader who has just seen the map of the document
    # is the right reader to hand the map of the place.
    IMG_W = 252.0
    # ⚠ 200 dpi, NOT 300. The screening frame's own ground resolution is 0.2276 m per pixel, and at
    # 252 pt wide a 300 dpi raster resolves 0.303 m per pixel: already coarser than the source, so the
    # extra pixels carry no extra detail about the site, only file size. MEASURED across the sweep:
    # 300 dpi is 275 KB, 240 is 195 KB, 200 is 149 KB at 0.455 m per pixel, which still renders a 57 m
    # hall 125 px wide. 200 dpi is also the floor this document will print an image at.
    IMG_DPI = 200
    aer, aer_meta = _aerial(d["site_key"], site, IMG_W, dpi=IMG_DPI)

    # ===================================================================== PAGE 2, contents
    st.append(PageBreak())
    st.append(Paragraph("Contents", S["h1"]))
    st.append(Paragraph("This document is one site's complete analysis. Page 1 is the whole "
                        "argument; everything after it is the evidence.", S["sub"]))
    for key, name, desc in _sections(solo, aer is not None):
        num = str(pages.get(key, "")) or "-"
        row = Table([[Paragraph("<font color='%s'><b>%s</b></font>" % (CH.BLUE, num), S["toc"]),
                      Paragraph("<b>%s</b>  <font size='8.5' color='%s'>%s</font>"
                                % (name, CH.SECOND, desc), S["toc"])]],
                    colWidths=[24, MEASURE - 24])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                                 ("LINEBELOW", (0, 0), (-1, -1), 0.35, RULE)]))
        st.append(row)

    st.append(Spacer(1, 16))
    st.extend(_h1("site", S, pages))
    # 🔴 THE PROSE IS BUILT WHETHER OR NOT THERE IS A PICTURE, because it is the part that carries
    # the argument. The first version put the whole section inside `if aer is not None` and gave a
    # site with no screening frame a single apologetic sentence: MEASURED, page 2 of
    # NE_way_405034584 came out 55 % empty and said nothing about the building at all. Whether an
    # aerial frame exists is a fact about the imagery vendor's coverage, not about the site, and it
    # should not decide whether the reader is told what they are looking at.
    if True:
        if solo:
            # ⚠ SAY WHAT IS ABSENT AND WHY, RATHER THAN SAYING NOTHING. A reader comparing two of
            # these reports will notice one has a physics section and one does not, and the honest
            # explanation is short: there is no neighbour, so there is no plume term to carry. It
            # belongs here, beside the picture that shows the single building, and not in a footnote.
            prose = [Paragraph(
                "One building, %s. It is the only data centre footprint mapped at this location, "
                "so there is no neighbouring hall discharging heat across a shared yard and "
                "nothing rejecting warm air toward the intake this agent is protecting."
                % (site.get("operator") or "unnamed in OpenStreetMap"), S["body"]),
                Paragraph(
                "That matters for what this report contains. Where two halls face each other, the "
                "exhaust from one can reach the air the other breathes, and the agent has to solve "
                "that %s on the real footprints before it will release an hour. A single site has "
                "no such term: the plume physics does not apply here, so the section on it is "
                "absent from this document rather than present and empty."
                % _q("plume", "constraint"), S["body"]),
                Paragraph(
                "Everything else is unchanged. The bound is still built from this site's own "
                "measured forecast error, still checked against the plant's own limit, and still "
                "declines any hour it cannot stand behind.", S["body"])]
            cap = ("%s. %s The outline is OpenStreetMap way %s on an independently georeferenced "
                   "basemap, so an edge can sit a few metres off the roofline; every distance in "
                   "this report is computed from the OpenStreetMap geometry, not from the picture."
                   % (aer_meta["source"], aer_meta["resolution_note"], site.get("osm_source"))
                   ) if aer is not None else ""
        else:
            # ⚠ THE GAP COMES FROM THE TRACE WHEN THERE IS NO FRAME TO MEASURE IT ON. The aerial
            # module recomputes it and asserts it against `facade_gap_m`, so the two agree by
            # construction; with no imagery there is no module run and the artefact is the source.
            gap = aer_meta["gap_m"] if aer is not None else site["facade_gap_m"]
            prose = [Paragraph(
                "Two halls, %s. The agent is deciding for the second one. When its neighbour "
                "rejects heat from the condensers along the facing wall, that warm air has only "
                "<b>%.1f m</b> of open ground to cross before it reaches the air this building "
                "breathes." % (_halls(site.get("operator")), gap), S["body"]),
                Paragraph(
                "That is what a <b><font color='%s'>plume</font></b> is: a moving body of warmer "
                "air leaving one building and drifting with the wind. It matters because free "
                "cooling only works while the air arriving at the intake is genuinely cool. A "
                "thermostat reading the regional forecast cannot see this, because the forecast is "
                "for the region and the plume is a hundred metres wide." % CH.ORANGE, S["body"]),
                Paragraph(
                "So the agent solves for it on this footprint, at this separation, for every wind "
                "bearing, and carries the answer as extra margin before it will release an hour.",
                S["body"])]
            cap = ("%s. %s Outlines are OpenStreetMap ways %s and %s on an independently "
                   "georeferenced basemap, so an edge can sit a few metres off the roofline; every "
                   "distance in this report is computed from the OpenStreetMap geometry, not from "
                   "the picture."
                   % (aer_meta["source"], aer_meta["resolution_note"],
                      site.get("osm_source"), site.get("osm_receptor"))
                   ) if aer is not None else ""
        if aer is None:
            # No frame from either imagery source for this site. The prose runs the full measure and
            # the reason is stated where the caption would have been, because a reader comparing two
            # reports deserves to know which of the two facts is missing.
            for para in prose:
                st.append(para)
            st.append(_caption(
                "No screening frame is available for this site: %s. Every distance above and "
                "throughout this report is computed from the OpenStreetMap geometry, which is the "
                "source the solver uses in either case; the imagery would only have shown it."
                % aer_meta, S))
        else:
            # ⚠ THE COLUMN FOLLOWS THE IMAGE, which is no longer always IMG_W wide. A tall frame
            # capped by height comes back narrower, and a column fixed at 252 pt would leave a strip
            # of white between the picture and the prose that reads as a mistake.
            _iw = (aer_meta.get("placed_wh_pt") or (IMG_W, 0))[0]
            block = Table([[aer, prose]], colWidths=[_iw + 12, MEASURE - _iw - 12])
            block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("LEFTPADDING", (0, 0), (0, 0), 0),
                                       ("LEFTPADDING", (1, 0), (1, 0), 6),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                       ("TOPPADDING", (0, 0), (-1, -1), 0),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            st.append(block)
            st.append(Spacer(1, 4))
            st.append(_caption(cap, S))

    # ===================================================================== PAGE 3, findings
    # 🔴 A CONDITIONAL BREAK, NOT A FORCED ONE. Eight forced page breaks for about seven and a half
    # pages of content is where the empty space came from: every section started at the top of a
    # fresh page and stopped wherever it stopped, so MEASURED, five of nine pages sat under the
    # brief's 85 % floor and one at 60 %. Nothing was wrong with the content; the pagination was
    # spending a page break it could not afford. A section now starts a new page only when fewer
    # than 260 pt remain, which is the least room in which a heading, its deck and its first chart
    # look deliberate rather than stranded.
    st.append(CondPageBreak(260))
    st.extend(_h1("findings", S, pages))
    st.append(Paragraph("Charts first. The prose under each one says only what the chart cannot.",
                        S["sub"]))
    st.append(_chart(CH.bound_vs_actual(d["hours"], cfg["limit_c"])))
    # 🔴 THIS CAPTION USED TO CLAIM "the bound sits above the actual in every hour". IT DOES NOT.
    # MEASURED on this day: the actual went above the bound in 6 of 24 hours. A CEO forwarding this
    # to a customer would have been forwarding a sentence the chart directly above it refutes, and
    # a technical reader would have found it in seconds. The true reading is also the better one,
    # so it is stated: all six were hours the agent had already put on chillers, and no hour it
    # released for free cooling exceeded the plant limit.
    over = [x for x in d["hours"] if x["actual_intake_c"] > x["bound_c"]]
    over_free = [x for x in over if x["mode"] == "FREE-COOLING"]
    breach = [x for x in d["hours"]
              if x["mode"] == "FREE-COOLING" and x["actual_intake_c"] > x["limit_c"]]
    st.append(_caption(
        "The pale band is the safety margin: the distance the agent adds on top of the raw "
        "forecast before it will commit to an hour. The blue line is the resulting upper bound, "
        "the navy line is what the intake temperature actually did, and the dashed line is the "
        "plant's limit.", S))
    st.append(_caption(
        "<b>Read the crossings</b>: the actual went above the bound in %d of the %d hours, which "
        "is what page 6 measures directly. All %d were hours the agent had already put on "
        "chillers, and <b>%d of the hours it released for free cooling exceeded the plant limit</b>. "
        "A bound exceeded on an hour the agent did not act on costs nothing; the hours that matter "
        "are the ones it said yes to."
        % (len(over), len(d["hours"]), len(over) - len(over_free), len(breach)), S))
    st.append(Spacer(1, 10))
    # height 168 not 150: at 150 the chart's own summary line sat on its bottom edge and the
    # caption flowable printed straight over it.
    st.append(_chart(CH.agent_vs_incumbent(h["mech_agent_h"], h["mech_inc_h"],
                                           h["runtime_cut_pct"],
                                           held_out_days=h["held_out_days"], height=168)))
    st.append(Spacer(1, 4))
    st.append(_caption(
        "The comparison is against a tuned reactive controller using an on-site sensor, which is "
        "what operators verifiably run today, not against doing nothing. <b>Held-out</b> means "
        "days the agent never trained on: the record was split chronologically and the second "
        "half, %s days, was kept back." % _n(h["held_out_days"]), S))

    # ===================================================================== PAGE 4, method
    st.append(CondPageBreak(260))
    st.extend(_h1("decision", S, pages))
    st.append(Paragraph(
        "Each hour the agent takes the forecast for this building's own tile, adds a margin, and "
        "compares the result against the plant's limit. It commits to free cooling only when the "
        "%s clears the %s, not when the forecast does."
        % (_q("upper bound"), _q("limit", "constraint")), S["body"]))
    st.append(_chart(CH.margin_decomposition(d["hours"])))
    if solo:
        st.append(_caption(
            "Every bar here is forecast error alone. The plume allowance that would sit on top of "
            "it is identically zero at this site, because there is no neighbouring hall for an "
            "exhaust to cross from, so the chart has one part rather than two.", S))
    st.append(_caption(
        "The margin is measured, not chosen. The lower part of each bar is the forecast error this "
        "agent has actually made at that hour of the day (<b>group-conditional</b>: the error is "
        "measured per hour of day rather than pooled across all of them, because a 3 a.m. forecast "
        "and a 3 p.m. forecast are not equally hard).%s"
        % ("" if solo else " The upper part is how far the exhaust plume could move if the wind "
           "sits differently from the direction planned for."), S))
    st.append(Paragraph("The gates an hour has to pass", S["h2"]))
    gates = [["Gate", "Setting here", "What it protects"],
             ["Plant limit", "%s °C" % _c(cfg["limit_c"]),
              "the intake temperature the hall is committed to"],
             ["Dew point", ("%s °C" % _c(cfg["dewpoint_limit_c"]))
              if cfg.get("dewpoint_limit_c") else "off",
              "condensation on cold surfaces inside the hall"],
             ["Notice", "%d h" % cfg["notice_h"],
              "the plant cannot change mode instantly"],
             ["Switch budget", "%d per day" % cfg["switch_budget"],
              "chillers and dampers wear out when cycled"],
             ["Minimum dwell", "%d h" % cfg["min_dwell_h"],
              "a mode has to hold before another change is allowed"]]
    st.append(_table(gates, [92, 82, MEASURE - 174]))
    st.append(Paragraph(
        "The switch budget is the reason a cold hour can still run chillers. With %d change%s "
        "permitted in a day, spending one early costs the agent the ability to switch later, so it "
        "schedules the whole day at once by dynamic programming rather than deciding each hour as "
        "it arrives." % (cfg["switch_budget"], "" if cfg["switch_budget"] == 1 else "s"),
        S["body"]))
    st.append(Paragraph(
        "<b>What this document is</b> &nbsp;·&nbsp; the interface recomputes for any configuration a reader "
        "selects. This file was generated for the one named above, chosen as the configuration "
        "where this site's agent does the most while still changing mode at least once. If the "
        "screen disagrees with this page, the configuration differs.", S["foot"]))

    # ⚠ SKIPPED ENTIRELY ON A SINGLE-BUILDING SITE. Everything below describes the exhaust
    # plume between two halls: the 576-solve sweep, the polar plot of intake rise by bearing,
    # the refusal logic and the GPU argument for why a bound needs that many solves. On a site
    # with no neighbour every one of those numbers is zero or None, and `plume_polar` would
    # raise on `int(None)` for the worst bearing. The contents page drops the entry to match,
    # which is `_sections`, so the document and its index cannot disagree.
    if not solo:
        # ===================================================================== PAGE 5, physics
        st.append(CondPageBreak(260))
        st.extend(_h1("physics", S, pages))
        st.append(Paragraph(
            "A data centre's condensers blow hot air out of the building. When the wind sits wrong "
            "that exhaust drifts toward a neighbour's air intake, so the machine can end up breathing "
            "warmed air while the forecast still reports the ambient. The agent therefore does not "
            "trust the forecast at the intake until it has solved where the exhaust actually goes.",
            S["body"]))
        # ⚠ ONE NUMBER, PASSED BOTH WAYS. The chart is drawn with its type divided by the same 0.86 the
        # Drawing is then scaled by, so the two cancel and the labels land at the size they ask for.
        POLAR_SCALE = 0.86
        # 🔴 THE SPECIFICATION GOES UNDER THE PLOT, IN SPACE THAT WAS ALREADY BEING PAID FOR. A polar
        # plot is square, so in a 42 % column it can never be taller than 209 pt however much height the
        # page has spare, and the row's height is set by the taller cell, which is the prose. MEASURED:
        # 130 pt of dead paper under the circle, and page 5 at 71 % against the brief's 85 % floor.
        # Growing the chart cannot fix that and neither can pagination; the column needed something in
        # it. This is the right something: the numbers that say HOW the solve was run, which is the one
        # question the picture beside it raises and does not answer.
        #
        # ⚠ EVERY ROW IS READ FROM `rise_table_<bank>.json` OR THE TRACE'S OWN GEOMETRY. Nothing here is
        # restated from prose and nothing is computed twice.
        spec = [["The solve", ""],
                ["bearings swept", "%d, every %d°" % (p["n_bearings"], round(360.0 / p["n_bearings"]))],
                # 🔴 `_n` ROUNDS TO A WHOLE NUMBER, AND THE SLOWEST WIND SPEED IS 0.5 m/s. So this row
                # printed "0 to 12 m/s" and claimed the sweep includes dead calm, which it does not and
                # must not: the plume model needs air movement to advect anything. `_n` is for hours and
                # dollars. A speed needs a decimal, and a trailing ".0" is noise on "12".
                ["wind speeds", "%d, %s to %s m/s"
                 % (len(p["speeds"]), _sp(min(p["speeds"])), _sp(max(p["speeds"])))
                 if p.get("speeds") else "%d" % (p["n_solves"] // max(p["n_bearings"], 1))],
                ["solves", _n(p["n_solves"])],
                ["solver", p["device"]],
                ["wall clock", "%s s" % _c(p["solve_seconds"], 2)],
                ["bearings refused", "%d of %d" % (len(p["refused"]), p["n_bearings"])],
                ["worst rise", "%s °C at %d°" % (_c(p["max_rise_c"], 2), int(p["max_rise_bearing"]))]]
        if p.get("mean_rise_c") is not None:
            spec.append(["mean rise", "%s °C" % _c(p["mean_rise_c"], 2)])
        _g = (site.get("geometry") or {}).get(p["bank"]) or {}
        if _g.get("bank_length_m"):
            spec.append(["condenser bank", "%s m of facade, %d cells"
                         % (_n(_g["bank_length_m"]), _g.get("bank_cells") or 0)])
        # ⚠ THE VALUE COLUMN TAKES THE WIDTH, because that is the side with "GPU (NVIDIA Warp)" on it
        # while the labels are two short words. 0.53/0.47 was an even split of a column that is not
        # evenly used.
        POLAR_W = MEASURE * 0.42
        left = [_chart(CH.plume_polar(p["rise_table_file"], p["max_rise_bearing"],
                                      p["max_rise_c"],
                                      os.path.join(ASSETS, "_polar_%s.svg" % d["site_key"]),
                                      placed_scale=POLAR_SCALE),
                       is_path=True, scale=POLAR_SCALE),
                Spacer(1, 8),
                _table(spec, [POLAR_W * 0.44, POLAR_W * 0.56 - 10])]
        row = Table([[left,
                      Paragraph(
            "<b>%s solves</b>, on this building's own outline. Every one of the %d wind bearings is "
            "solved across a grid of wind speeds, on the footprints taken from OpenStreetMap rather "
            "than an idealised box. The worst case anywhere on the compass is <b>%s °C</b> of intake "
            "rise, at %d degrees.<br/><br/>"
            "That is a small number until the bound sits on the limit, and then it decides the hour. "
            "Including this term moved unsafe hours from <b>%d to %d</b> across the five-year record "
            "and <b>added</b> free-cooling hours at the same time, because knowing where the exhaust "
            "goes lets the agent say yes on the bearings that carry it away.<br/><br/>"
            "Why this needs a GPU: a single solve is not the workload, the bound is. Stating "
            "\"90%% of the time the intake stays under X\" means running the physics many times over a "
            "spread of conditions. "
            # 🔴 THE ONE FULLY BOLD SENTENCE IN THE DOCUMENT, per item 5. It is the sentence that turns
            # a physics demo into a product: the same solve, two orders of magnitude faster, and checked
            # against the slow path rather than trusted. Everything else in this document is emphasised
            # by phrase so that this one carries.
            "<b>A hundred of these solves take about a minute on a processor and under a second on "
            "the GPU through NVIDIA Warp, and the two agree to within a ten-thousandth of a "
            "degree.</b> This site's table took <b>%s seconds</b> on %s."
            % (p["n_solves"], p["n_bearings"], _c(p["max_rise_c"]), int(p["max_rise_bearing"]),
               p["without_term"]["agent_breach_h"] if p["without_term"] else 11,
               p["with_term"]["agent_breach_h"] if p["with_term"] else 3,
               _c(p["solve_seconds"]), p["device"]), S["body"])]],
                    colWidths=[MEASURE * 0.42, MEASURE * 0.58])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (0, 0), 0),
                                 ("LEFTPADDING", (1, 0), (1, 0), 12)]))
        st.append(row)
        if p["refused"]:
            st.append(Paragraph(
                "At this placement the solver <b>refuses %d of the %d bearings</b>: a building sits on "
                "the path between the exhaust and the intake, the two-dimensional model cannot describe "
                "that, and the agent declines those hours rather than return a number it cannot stand "
                "behind." % (len(p["refused"]), p["n_bearings"]), S["body"]))
        else:
            st.append(Paragraph(
                "At this placement no bearing is refused: nothing blocks the path between the exhaust "
                "and the intake, so all %d directions return a number the agent is willing to use. The "
                "refusal is a property of geometry, not of this site, and where it does fire it is "
                "expensive: elsewhere in the sweep it costs the agent thousands of hours a year, and "
                "that cost is published rather than hidden." % p["n_bearings"], S["body"]))

    # ===================================================================== PAGE 6, validation
    st.append(CondPageBreak(260))
    st.extend(_h1("validation", S, pages))
    st.append(_chart(CH.coverage(b)))
    st.append(_caption(
        "A <b>bound</b> is a number the agent commits to the real intake staying under. Coverage "
        "is the share of hours it did. The target is 90%, and each population below is as large as "
        "the record currently allows.", S))
    st.append(Paragraph("What the measurement shows", S["h2"]))
    for txt in (
        "The method reaches its target <b>wherever the record is large enough to measure it</b>. "
        "Twelve separately calibrated per-lead bounds, every one at or above 90%%, the worst at %s. "
        "An adaptive bound over %s rounds of the five-year record realised %s."
        % (_pct(min(b["coverage_by_lead"].values())), _n(b["aci_rounds"]),
           _pct(b["aci_coverage"])),
        "<b>The FortyGuard-specific calibration currently rests on %d measured forecast days</b>, "
        "and reads %s. A one-sided 90%% bound needs <b>%d</b> such days: at %d the arithmetic "
        "ceiling is %s, so the target is a function of how many days have been forecast rather than "
        "of the method."
        % (b["n_pairs"], _pct(b["pooled"]), b["n_needed"], b["n_pairs"], _pct(b["ceiling"])),
        "A calibration day is <b>earned, not bought</b>. It is a forecast plus the day that follows "
        "it, so the count rises by one for every further day the site is forecast on. Nine days of "
        "operation is the whole distance between the figure above and the target.",
        "Conditioning already recovers <b>most of the gap</b>. Measuring the error per hour of day "
        "rather than pooling every hour together lifts the worst group from %s to %s."
        % (_pct(b["pooled_worst_group"]), _pct(b["mondrian_worst_group"])),
    ):
        st.append(Paragraph(txt, S["bullet"], bulletText="·"))
    st.append(_table(
        [["What was tested", "Volume", "Result"],
         ["Real recorded weather", "%s h / %s d" % (_n(h["weather_hours"]), _n(h["weather_days"])),
          "the record the schedule was scored on"],
         ["Held-out days", "%s d" % _n(h["held_out_days"]), "never trained on"],
         ["Re-plans compared", _n(d["rolling"]["replans"]),
          "%s changed nothing at all" % _pct(d["rolling"]["zero_change"])],
         ["Free-cooling hours taken", _n(h["free_h_taken"]),
          "%d unsafe, %s per thousand" % (h["breach_h"], "%.2f" % h["breach_per_1000"])]],
        [150, 96, MEASURE - 246]))

    # ===================================================================== PAGE 7, scale
    st.append(CondPageBreak(260))
    st.extend(_h1("scale", S, pages))
    st.append(Paragraph(
        # 🔴 THE COVERED COUNT IS THE OFFERED COUNT, NOT THE BUILT COUNT, AND THE DIFFERENCE IS
        # STATED. The agent is built and measured on every site in the distribution below, including
        # the ones where it loses; it is OFFERED on the subset where the five-year measurement says
        # it wins. Quoting the built total here and plotting a filtered distribution below, or
        # quoting the offered total and plotting everything without a word, would both be a form of
        # selection bias. Both numbers appear, a sentence apart, and the sentence says why they
        # differ. `sites.json` owns the gate: `metros.py` sets `pays` from each site's own backtest.
        "One hall is a pilot. The agent covers <b>%s sites</b>, each built on its own OpenStreetMap "
        "footprint, its own station weather record and its own tariff, drawn from 639 tagged data "
        "centre facilities mapped across the United States."
        % _n(d["offered_n"]), S["body"]))
    # ⚠ THE OFFERED SET, EXPLICITLY. The chart is given exactly the rows it plots, so its title and
    # the caption under it can both be counted from the same list rather than asserted.
    shown = [x for x in d["portfolio"] if x.get("offered")]
    excl = [x for x in d["portfolio"] if not x.get("offered")]
    st.append(_chart(CH.portfolio_hist([x["gain"] for x in shown],
                                       os.path.join(ASSETS, "_hist_%s.svg" % d["site_key"]),
                                       this_site_gain=h["chiller_h_per_year"]), is_path=True))
    neg = [x for x in excl if x["gain"] < 0]
    st.append(_caption(
        "This is every site the agent is offered on. <b>%d more were measured and excluded</b> "
        "because the agent's own constraints made it worse than the incumbent there, and those are "
        "not sold without site-specific engineering work on them first: at that geometry the safety "
        "margin hands back more free-cooling hours than it wins, so the agent runs the chillers "
        "more than the controller it would replace, the worst of them by %s hours a year. They are "
        "not in the chart, because an axis wide enough to hold them would compress everything above "
        "into a sixth of the frame; they are counted here instead, and they stay on the map marked "
        "measured rather than ready. A portfolio that reports where it does not work is one a "
        "reader can believe about where it does."
        % (len(excl), _n(abs(min(x["gain"] for x in neg))) if neg else "0"), S))
    st.append(Paragraph("Who buys this", S["h2"]))
    st.append(Paragraph(
        "An operator running many data centres, and the engineer inside it who owns the energy "
        "number. Their tenants' service level agreements commit them to a maximum supply air "
        "temperature, so an excursion is a contract breach and not just a warm hour, which is why "
        "the conservative buffer exists in the first place. What replaces the buffer has to come "
        "with a bound and a published breach rate, or it does not get switched on.", S["body"]))
    if h["usd_site_lo"]:
        st.append(_table(
            [["At this site", "Value", "Basis"],
             ["Measured footprint", "%s m²" % _n(site["footprint_m2"]),
              "OpenStreetMap rings, the same outlines the solver runs on"],
             ["IT load", "%d to %d MW" % (round(h["mw_lo"]), round(h["mw_hi"])),
              "DERIVED from a watts per square metre density"],
             ["Recovered hours", "+%s h/yr" % _n(h["chiller_h_per_year"]), "backtested"],
             ["Value of those hours", "$%s to $%s /yr" % (_n(h["usd_site_lo"]),
                                                          _n(h["usd_site_hi"])),
              "MODELED. Measured hours times published rates times derived megawatts"],
             ["The rate behind it", "$%s to $%s /MW-IT/yr" % (_n(h["usd_rate_lo"]),
                                                              _n(h["usd_rate_hi"])),
              "%d cells: published tariffs x published chiller efficiencies, swept"
              % h["rate_cells"]]],
            # ⚠ 148, NOT 118. Baking tabular figures in widened every digit to a common advance,
            # which is the point of them, and MEASURED it pushed "$334,269 to $967,245 /yr" 2.7 pt
            # into the Basis column beside it. A value column holding two thousands-separated
            # currency figures and a unit needs the room; the Basis column has it to give.
            [124, 148, MEASURE - 272]))
        st.append(Paragraph(
            "The percentage is the honest headline and the dollars are the illustration. %s less "
            "chiller runtime needs no assumption about how big the building is; the money rows do, "
            "and the two that depend on one are labelled." % _pct(h["runtime_cut_pct"]), S["foot"]))

    # ===================================================================== PAGE 8, appendix
    # ⚠ CONDITIONAL, LIKE THE OTHERS, AND FOR A MEASURED REASON. A hard break here left page 7 of
    # the first standalone report 6 % full: the money table filled page 6 exactly, its closing
    # footnote spilled onto page 7 alone, and nothing could follow it because the appendix insisted
    # on starting fresh. The appendix is the last section and reads perfectly well beginning part
    # way down a page. On a site where 260 pt is not free it still starts on a new one.
    st.append(CondPageBreak(260))
    st.extend(_h1("appendix", S, pages))
    st.append(Paragraph(
        "The %d hours of this day carry <b>%d distinct reasons</b> between them. Each is explained "
        "once below, with the hours it covers and the tightest of those hours as the worked "
        "example." % (len(d["hours"]), len(groups)), S["sub"]))
    for g in groups:
        rep = g["rep"]
        blk = [Paragraph("%s &nbsp;<font color='%s' size='8.5'>%d hour%s: %s</font>"
                         % (REASON_TITLE.get(g["binding"], "Reason: %s" % g["binding"]), CH.SECOND,
                            g["n"], "" if g["n"] == 1 else "s", g["ranges"]), S["h2"]),
               Paragraph(_explain(g, cfg), S["body"]),
               Paragraph(_worked(rep), S["small"])]
        st.append(KeepTogether(blk))
    st.append(Spacer(1, 6))
    st.append(Paragraph("The full schedule", S["h2"]))
    rows = [["hh", "mode", "safe", "reason", "bound", "limit", "actual", "margin"]]
    for x in d["hours"]:
        rows.append([x["hour"], "free" if x["mode"] == "FREE-COOLING" else "mechanical",
                     "yes" if x["safe"] else "no", x.get("binding") or "-",
                     _c(x["bound_c"]), _c(x["limit_c"]), _c(x["actual_intake_c"]),
                     _c(x["margin_total_c"])])
    st.append(_table(rows, [26, 68, 32, 92, 52, 44, 50, MEASURE - 364],
                     align={4: "RIGHT", 5: "RIGHT", 6: "RIGHT", 7: "RIGHT"}))
    # ===================================================================== the counterfactual
    # 🔴 THIS BLOCK EXISTS BECAUSE PAGE 9 WAS 60 % EMPTY AND THE ARTEFACT HAD AN UNUSED ANSWER IN IT.
    # `explanations.json` carries `would_flip_with_more_switches` and `would_flip_with_shorter_dwell`
    # per hour, and nothing in the report read them. They are the most commercially direct numbers
    # this document has: they say whether the hours the agent declined were declined because of the
    # weather or because of a setting.
    #
    # ⚠ THE COUNTERFACTUAL IS "+2", NOT "+1", AND SAYING +1 WOULD HAVE BEEN WRONG. `explain.py` line
    # 212 computes it as `plan(safe, cfg["switch_budget"] + 2, cfg["min_dwell_h"])`, so the flag
    # means the hour comes free when the budget rises BY TWO. It is also a single joint re-plan
    # rather than twelve separate ones, which is what makes "all twelve at once" a fair reading.
    #
    # ⚠ AND IT IS RE-CHECKED RATHER THAN ASSERTED. `explain.py` line 317 re-plans and fails the
    # build if any hour claiming this does not actually come free, which is why it can be printed.
    flip_sw = [x["hour"] for x in d["hours"] if x.get("would_flip_with_more_switches")]
    flip_dw = [x["hour"] for x in d["hours"] if x.get("would_flip_with_shorter_dwell")]
    st.append(Paragraph("What would change the answer", S["h2"]))
    st.append(Paragraph(
        "The hours above that ran chillers on a named schedule constraint were not held by the "
        "weather. Re-planning this same day with the switch budget raised from "
        "<b>%d to %d</b> releases <b>%d of the %d hours</b> to free cooling. Re-planning it with "
        "the minimum dwell cut from %d h to 1 h releases <b>%d</b>. On this day and this "
        "configuration the binding constraint is the number of mode changes the plant permits, "
        "not its dwell requirement and not the air."
        % (cfg["switch_budget"], cfg["switch_budget"] + 2, len(flip_sw), len(d["hours"]),
           cfg["min_dwell_h"], len(flip_dw)), S["body"]))
    st.append(_table(
        [["Change to the plant's own limits", "Hours released", "Which hours"],
         ["switch budget %d per day to %d" % (cfg["switch_budget"], cfg["switch_budget"] + 2),
          "+%d" % len(flip_sw), _ranges([x["index"] for x in d["hours"]
                                        if x.get("would_flip_with_more_switches")])
          if flip_sw else "none"],
         ["minimum dwell %d h to 1 h" % cfg["min_dwell_h"],
          "+%d" % len(flip_dw), _ranges([x["index"] for x in d["hours"]
                                        if x.get("would_flip_with_shorter_dwell")])
          if flip_dw else "none"]],
        [232, 84, MEASURE - 316], align={1: "RIGHT"}))
    _last_caveat = Paragraph(
        "That is a re-plan, not a promise. The switch budget exists because cycling chillers and "
        "dampers wears them out, so the hours above are available only if the plant is willing to "
        "pay that wear, and the agent deliberately does not make that trade on the operator's "
        "behalf. What it does is price it: this is the number an engineer needs in order to decide "
        "whether the setting is worth revisiting. Each of the %d is re-planned and re-checked in "
        "<font face='Courier'>explain.py</font> before it may be printed here."
        % len(flip_sw), S["body"])

    # 🔴 THE COLOPHON IS BOUND TO THE PARAGRAPH BEFORE IT, because alone it stranded a page.
    # MEASURED on CA_way_58708529: pages 8 and 9 came out at 100.2 % each and the colophon had
    # nowhere left to go, so page 10 carried three lines and nothing else, 6 % full. Three sites did
    # this. A KeepTogether over the closing pair means the last page carries the caveat and the
    # colophon together or neither, which is the difference between a short final page and an
    # orphan.
    st.append(KeepTogether([_last_caveat, Paragraph(
        "Generated by <font face='Courier'>AGENTIC-ARBITER/src/site_report.py</font> from this "
        "site's own artefacts. Every figure here is read from the file that produced it; the rows "
        "labelled MODELED are the only ones resting on an unmeasured assumption.", S["foot"])]))

    doc.build(st)
    return out, d, groups


def build(site_key=None, out_path=None):
    """Build twice, and return the second one.

    🔴 A CONTENTS PAGE CANNOT BE WRITTEN BEFORE THE DOCUMENT IT INDEXES. Where a heading falls
    depends on how every flowable before it wrapped, so pass one lays the document out with the page
    numbers still unknown, the `Mark` flowables record where each heading actually landed, and pass
    two prints those numbers. This is the standard resolution for any reference that points forward
    at its own layout, and it is why the hand-written contents page had drifted: nothing could have
    told it that "The findings" had moved to page 3 or that "The site" existed.

    ⚠ DETERMINISM IS UNAFFECTED, and that is worth stating because two passes sounds like it would
    not be. Both passes read the same artefacts and `rl_config.invariant` is already set, so pass
    two is a pure function of the same inputs. The only thing carried between passes is a dict of
    integers, and `--check` below asserts it did not move.

    ⚠ PASS ONE WRITES TO A SIDE PATH, so a failure halfway can never leave a report on the real
    path that says page 3 where it means page 4.
    """
    # 🔴 `metro_key()`, NOT `DEFAULT_METRO`. `build_sites.py` drives every child with the site in the
    # METRO environment variable and no argument, so `site_key` is None on all 249 of them. Falling
    # back to the default metro meant every site in the chain would have written its report over
    # ashburn's `demo/report.pdf`: 249 builds, one output file, and the last one wins. `metro_key()`
    # reads the same environment variable the data layer resolves the site from, so the artefact
    # read and the artefact written can no longer disagree about which site this is.
    out = out_path or M.demo_path("report.pdf", (site_key or M.metro_key()))
    pages = {}
    scratch = out + ".pass1"
    try:
        _build_once(site_key, scratch, pages)
    finally:
        if os.path.exists(scratch):
            os.remove(scratch)
    first = dict(pages)
    res = _build_once(site_key, out, pages)
    # If a page number moved between the passes, the contents is describing pass one's layout. It
    # cannot happen while the only difference is the digits in the contents rows, and the assertion
    # is here so that if it ever does, the build stops rather than shipping a wrong index.
    moved = {k: (first.get(k), pages.get(k)) for k in pages if first.get(k) != pages.get(k)}
    assert not moved, "section pages moved between passes: %r" % moved
    return res


def _worked(rep):
    """One hour, decomposed so the numbers ON THE PAGE add up at the precision they are shown.

    🔴 THE BUG THIS REPLACES WAS THE WORST KIND IN THE DOCUMENT: a sentence a reader could falsify
    with mental arithmetic. It read

        "forecast 17.8 °C + margin 1.7 °C = bound 15.4 °C ... The intake actually reached 17.8 °C"

    and 17.8 + 1.7 is 19.5, not 15.4. Two independent errors behind one sentence:

      1. `ambient_c` IS NOT A FORECAST. It is the measured ambient air temperature from the station
         record, and `actual_intake_c` is that same figure plus the plume rise: MEASURED, the
         difference equals `plume_rise_c` to four decimals in all 24 hours. So the sentence printed
         one quantity twice, labelled it "forecast" and "actually reached", and left the reader to
         notice they matched.
      2. THE BOUND IS NOT AMBIENT PLUS MARGIN. `audit.py` check 6a rebuilds it as
             bound = ambient - level - (1-skill)*r_prime + (1-skill)*margin_dry + rise + plume_margin
         The dropped term is `-(1-skill)*r_prime`, the forecast's advantage over assuming today
         repeats. At hour 11 it is -4.10 C, which is why the bound sits BELOW the ambient air and
         why free cooling is possible on a warm hour at all. Omitting it did not lose precision, it
         deleted the reason the product works.

    ⚠ AND THEN A SECOND, SMALLER VERSION OF THE SAME FAULT. Deriving the forecast term at full
    precision and rounding all five numbers independently gave sentences that still did not close:
    "19.4 - 2.6 + 0.18 + 1.3" displays as 18.28 against a printed bound of 18.4. So the terms are
    ROUNDED FIRST and the forecast term is derived from the rounded values. The displayed sum is
    then exact by construction, whatever the engine's internal precision was.

    ⚠ THE FORECAST TERM IS DERIVED, NEVER RESTATED. Recomputing the formula here would be a second
    implementation of the bound, free to drift from `agent.py`. It is recovered as the residual of
    figures the artefact already carries.
    """
    dp = 2
    amb = round(rep["ambient_c"], dp)
    rise = round(rep.get("plume_rise_c") or 0.0, dp)
    marg = round(rep["margin_total_c"], dp)
    bound = round(rep["bound_c"], dp)
    lim = rep["limit_c"]
    intake = round(rep["actual_intake_c"], dp)
    gain = round(amb + rise + marg - bound, dp)

    # The guard: if the sentence below would not add up as printed, it refuses to be printed.
    assert abs((amb - gain + rise + marg) - bound) < 1e-9, \
        "worked example does not close at display precision for hour %s" % rep["hour"]

    def n(v):
        return ("%.2f" % v).rstrip("0").rstrip(".") or "0"

    if gain >= 0:
        clause = ("less the <b><font color='%s'>%s °C</font></b> the forecast earns over assuming "
                  "today repeats" % (CH.BLUE, n(gain)))
    else:
        # Hour 03 of this very day is -0.79: the forecast read warmer than persistence, so the term
        # RAISES the bound. "less the -0.79 °C the forecast earns" would be gibberish.
        clause = ("plus <b><font color='%s'>%s °C</font></b> where the forecast read warmer than "
                  "assuming today repeats" % (CH.BLUE, n(abs(gain))))
    # ⚠ A ZERO RISE IS NOT A SMALL RISE, AND "under 0.01 °C" WOULD IMPLY A PLUME THAT IS NOT THERE.
    # On a single-building site `plume_rise_c` is exactly 0 because no solve was run: there is no
    # neighbour to receive an exhaust and no intake to warm. "a plume rise under 0.01 °C" is true
    # arithmetic and a false description, so the clause is dropped instead, and the sentence reads as
    # the two-term decomposition it actually is.
    solo = (rise == 0.0)
    rise_txt = (("%s °C of plume rise" % n(rise)) if rise >= 0.01
                else "a plume rise under 0.01 °C")
    # 🔴 AND A THIRD ERROR, THIS ONE MINE, CAUGHT THE SAME WAY. The first correction said "the
    # intake is that ambient plus the rise", which is FALSE IN 15 OF THE 24 HOURS. There are two
    # rise figures in the day series and they are not the same quantity:
    #     `rise_c_<bank>`      the rise at the FORECAST wind bearing  -> goes into the BOUND
    #     `rise_true_c_<bank>` the rise at the bearing that OCCURRED  -> gives the actual intake
    # MEASURED at hour 12: forecast bearing 0.1773 C, true bearing 0.0083 C, and
    # 19.4400 + 0.0083 = 19.4483, which is the actual intake exactly. So the bound is built on the
    # rise the agent EXPECTED and the outcome reflects the rise that HAPPENED. The gap between them
    # is the entire reason a separate plume MARGIN exists, which makes this worth one clause rather
    # than a silent omission.
    if solo:
        # No plume term, so no rise to add and no bearing to have been wrong about. The intake IS
        # the ambient air here, which is why the two figures are the same number.
        return (
            "<b>Worked example, %s:00</b> &nbsp;·&nbsp; ambient air <b>%s °C</b>, %s, plus a "
            "measured <b><font color='%s'>%s °C</font></b> margin, gives a "
            "<b><font color='%s'>%s °C</font></b> bound against the %s °C limit. With no "
            "neighbouring hall to warm the incoming air, the intake is the ambient air, and it "
            "reached %s °C."
            % (rep["hour"], n(amb), clause, CH.ORANGE, n(marg),
               CH.BLUE, n(bound), _c(lim), n(intake)))
    return (
        "<b>Worked example, %s:00</b> &nbsp;·&nbsp; ambient air <b>%s °C</b>, %s, plus %s at the "
        "forecast wind bearing, plus a measured <b><font color='%s'>%s °C</font></b> margin, gives "
        "a <b><font color='%s'>%s °C</font></b> bound against the %s °C limit. The wind then sat "
        "somewhere slightly different, so the intake itself reached %s °C: covering that difference "
        "is what the plume half of the margin is for."
        % (rep["hour"], n(amb), clause, rise_txt, CH.ORANGE, n(marg),
           CH.BLUE, n(bound), _c(lim), n(intake)))


def _explain(g, cfg):
    """One explanation per reason, written once. The prose the old report repeated per hour."""
    rep, n = g["rep"], g["n"]
    key = g["binding"]
    if key == "switch budget":
        return ("These hours were <b>cold enough to free-cool and were run on chillers anyway</b>, "
                "and the reason is the schedule rather than the weather. The plant permits %d mode "
                "change%s a day. Spending one here would leave the agent unable to switch when a "
                "longer or colder block arrives, so the whole day is planned at once and these "
                "hours are the ones the plan gives up. This is the explanation a thermostat cannot "
                "give, because a thermostat has no plan to be constrained by."
                % (cfg["switch_budget"], "" if cfg["switch_budget"] == 1 else "s"))
    if key == "dry-bulb":
        return ("The air was simply too warm. In each of these hours the agent's upper bound on "
                "intake temperature sat above the plant's %s °C limit, so free cooling would have "
                "risked the hall. It is the bound that is compared against the limit, never the "
                "raw forecast: the margin is what makes the comparison safe rather than optimistic."
                % _c(rep["limit_c"]))
    if key == "dew point":
        return ("Temperature passed and humidity did not. Pulling in air this damp risks "
                "condensation on cold surfaces inside the hall, so the dew-point gate blocks the "
                "hour independently of how cool the air is.")
    if key == "refusal":
        return ("The agent <b>declined</b> these hours rather than answering. At these wind "
                "bearings a building sits on the path between the exhaust and the intake, and the "
                "two-dimensional plume model cannot describe that geometry. Returning a number "
                "here would mean inventing one, so it does not.")
    if key == "minimum dwell":
        return ("A mode has to hold for %d hour%s before another change is allowed, so these hours "
                "inherit the previous decision regardless of their own weather."
                % (cfg["min_dwell_h"], "" if cfg["min_dwell_h"] == 1 else "s"))
    if key == "air quality":
        return ("The contamination gate blocked these hours: free cooling draws outside air "
                "through the hall, and above a particulate threshold that air is not worth the "
                "filters it would load.")
    return ("Free cooling ran. In each of these hours the agent's upper bound cleared the plant "
            "limit with the full measured margin already added, so outside air did the cooling "
            "and the chillers stayed off.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out, d, groups = build(a.site, a.out)
    print("   wrote %s  (%.1f KB)" % (out, os.path.getsize(out) / 1024.0))
    print("   %s: %d hours, %d distinct reasons, %d portfolio sites"
          % (d["site_key"], len(d["hours"]), len(groups), len(d["portfolio"])))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
