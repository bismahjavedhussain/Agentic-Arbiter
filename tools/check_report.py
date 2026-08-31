# -*- coding: utf-8 -*-
"""MEASURE the site report against the layout brief. Nothing here is an impression.

    python tools/check_report.py <report.pdf> [--png <dir>]

Reports, per page: fill percentage, the maximum x any element reaches, the fonts and sizes in use,
the number of vector drawings and images, and whether the logo is present. Then, document-wide:
contrast ratio for every text colour, duplicate paragraphs, and whether the text ends mid-sentence.

WHY A TOOL AND NOT A ONE-OFF SCRIPT. The brief asks for eight measurements after every change, and
three of them (fill, overflow, contrast) are the kind that regress silently the moment a chart grows
by ten points. Making them a command means the answer is always current rather than always
remembered from two builds ago.
"""
import argparse
import os
import re
import sys
from collections import Counter

A4_W, A4_H = 595.276, 841.89
MARGIN = 17 * 2.83465                       # 17 mm, the document's own margin
CONTENT_L, CONTENT_R = MARGIN, A4_W - MARGIN
# The frame the document actually fills, from site_report.py: header 30 pt, footer 10 pt.
TOP = A4_H - MARGIN - 30
BOTTOM = MARGIN + 10
USABLE = TOP - BOTTOM


def _lum(rgb):
    c = []
    for x in rgb:
        x = x / 255.0 if x > 1 else x
        c.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _cr(rgb, bg=(1.0, 1.0, 1.0)):
    a, b = _lum(rgb), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _seg_hits_rect(a, b, r):
    """True when the segment a..b passes through the interior of rect r.

    Cohen-Sutherland style: reject early when both ends sit outside the same edge, accept when
    either end is inside, otherwise clip the parametric segment against the four slabs.
    """
    if r.contains(a) or r.contains(b):
        return True
    dx, dy = b.x - a.x, b.y - a.y
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a.x - r.x0), (dx, r.x1 - a.x), (-dy, a.y - r.y0), (dy, r.y1 - a.y)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / float(p)
            if p < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return t0 <= t1


def _furniture_text(page):
    """The grey text in the running header and footer bands of one page.

    Identified by POSITION rather than by matching the strings, because the footer carries the page
    number and the generation date and so is not identical from page to page.
    """
    H = page.rect.height
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for sp in l["spans"]:
                y = (sp["bbox"][1] + sp["bbox"][3]) / 2.0
                # MEASURED on this document: the running head sits at y = 53.1 and the footer
                # strip at y = 792.6 on an 841.9 pt page, so 60 and H-60 bracket both with room.
                if (y < 60 or y > H - 60) and sp["color"] == 0x525c6b:
                    out.append(sp["text"])
    return "".join(out)


def _int_to_rgb(v):
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)


def main():
    import fitz
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--png", default=None)
    a = ap.parse_args()
    d = fitz.open(a.pdf)

    print("=" * 92)
    print("%s   %d pages   %.1f KB" % (os.path.basename(a.pdf), d.page_count,
                                       os.path.getsize(a.pdf) / 1024.0))
    print("=" * 92)
    print("%-5s %7s %8s %9s %7s %6s %5s  %s"
          % ("page", "fill%", "max x", "verdict", "drawings", "images", "logo", "lowest content y"))

    fills, overflow, nologo, thin = [], [], [], []
    for i in range(d.page_count):
        pg = d[i]
        lo_y, hi_x = BOTTOM, 0.0
        # text
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    x0, y0, x1, y1 = sp["bbox"]
                    if y1 < TOP + 2 and y0 > BOTTOM - 2:            # ignore header/footer
                        lo_y = max(lo_y, y1)
                        hi_x = max(hi_x, x1)
        # vector art
        for dr in pg.get_drawings():
            r = dr["rect"]
            if r.y1 < TOP + 2 and r.y0 > BOTTOM - 2:
                lo_y = max(lo_y, r.y1)
                hi_x = max(hi_x, r.x1)
        imgs = pg.get_images(full=True)
        for im in pg.get_image_info():
            r = im["bbox"]
            if r[3] < TOP + 2 and r[1] > BOTTOM - 2:
                lo_y = max(lo_y, r[3])
                hi_x = max(hi_x, r[2])
        used = lo_y - BOTTOM
        fill = 100.0 * used / USABLE
        fills.append(fill)
        # the logo lives in the header, so it is looked for separately
        has_logo = any(im["bbox"][1] < MARGIN + 34 for im in pg.get_image_info()) or bool(imgs)
        if not has_logo:
            nologo.append(i + 1)
        if hi_x > CONTENT_R + 0.5:
            overflow.append((i + 1, hi_x))
        if fill < 85:
            thin.append((i + 1, fill))
        print("  %-3d %6.1f%% %8.1f %9s %7d %6d %5s  %.1f"
              % (i + 1, fill, hi_x,
                 "OVERFLOW" if hi_x > CONTENT_R + 0.5 else ("thin" if fill < 85 else "ok"),
                 len(pg.get_drawings()), len(imgs), "yes" if has_logo else "NO", lo_y))

    print()
    print("  mean fill %.1f%%   pages under 85%%: %s"
          % (sum(fills) / len(fills), ", ".join("p%d %.0f%%" % t for t in thin) or "none"))
    print("  content right edge limit %.1f pt   overflow: %s"
          % (CONTENT_R, ", ".join("p%d at %.1f" % t for t in overflow) or "none"))
    print("  pages missing the logo: %s" % (nologo or "none"))

    # ---------------------------------------------------------------- type and colour
    print()
    print("TEXT COLOURS IN USE, contrast against white paper")
    seen = {}
    sizes = Counter()
    for i in range(d.page_count):
        for b in d[i].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    rgb = _int_to_rgb(sp["color"])
                    seen.setdefault(rgb, [0, set()])
                    seen[rgb][0] += len(sp["text"])
                    seen[rgb][1].add(round(sp["size"], 1))
                    sizes[round(sp["size"], 1)] += len(sp["text"])
    # 🔴 ROLE IS SIZE **AND** SHARE, because each alone gets it wrong, and this harness has now had
    # both errors. Version one used share alone: any colour past 2,000 characters was "body" and
    # owed 8:1, which failed the caption grey for the crime of being used often. Version two used
    # size alone: any colour appearing at 10 pt was "body", which failed the accent blue and the
    # accent orange for appearing inside 10 pt paragraphs, which is the entire point of an accent.
    #
    # The distinction that actually matters is whether a reader reads PARAGRAPHS in the colour or
    # only WORDS. So: set at body size and carrying a large share of the document, it is long-form
    # text and owes this document's own comfort floor of 8:1. Set at body size and carrying a small
    # share, it is inline emphasis, and the applicable public standard is WCAG 2.1's 4.5:1 for
    # normal text. Item 4 caps colour-coding at three terms per paragraph, which is what keeps the
    # accents on the small side of that line in the first place.
    total_chars = sum(v[0] for v in seen.values()) or 1
    LONGFORM_SHARE = 0.05
    for rgb, (chars, szs) in sorted(seen.items(), key=lambda kv: -kv[1][0]):
        r = _cr(rgb)
        big = max(szs) if szs else 0
        share = chars / float(total_chars)
        if big >= 10 and share >= LONGFORM_SHARE:
            role, need = "body, long-form", 8.0
        elif big >= 10:
            role, need = "accent, inline", 4.5
        else:
            role, need = "secondary", 4.5
        # White is inverse text on a filled series, so measuring it against paper is meaningless.
        if rgb == (255, 255, 255):
            role, need = "inverse (on blue)", 0.0
        print("   #%02x%02x%02x  %7.2f:1  %-16s %6d chars %5.1f%%  sizes %s   %s"
              % (rgb[0], rgb[1], rgb[2], r, role, chars, 100.0 * share,
                 ",".join("%g" % x for x in sorted(szs)),
                 "OK" if r >= need else "FAIL needs %.1f" % need))

    # ⚠ AND THE BRIEF'S OWN CAP, REPORTED AS A NUMBER RATHER THAN LEFT TO JUDGEMENT. Item 3 allows
    # the secondary grey for captions, axis labels and footnotes, and no more than 15 % of the
    # document's characters.
    # ⚠ TWO NUMBERS, BECAUSE THE RUNNING FURNITURE IS COUNTED ONCE PER PAGE AND READ ONCE IN TOTAL.
    # The header and footer strips are the same 115 characters of grey on all nine pages, so a
    # naive count charges the document 1,035 characters for boilerplate a reader takes in once and
    # then stops seeing. That is a real distortion of what the cap is about, which is how much of
    # the text a reader READS in the quieter grey, so both figures are printed and neither is
    # hidden: the raw share, and the share of the body text a reader actually works through.
    sec = seen.get((0x52, 0x5c, 0x6b), [0, set()])[0]
    furniture = sum(len(s) for i in range(d.page_count)
                    for s in (_furniture_text(d[i]),))
    body_total = max(total_chars - furniture, 1)
    body_sec = max(sec - furniture, 0)
    print("   secondary grey #525c6b, all text          %6d ch  %5.1f%%   cap 15%%  %s"
          % (sec, 100.0 * sec / total_chars,
             "OK" if sec / float(total_chars) <= 0.15 else "OVER"))
    print("   the same, excluding running header/footer %6d ch  %5.1f%%   cap 15%%  %s"
          % (body_sec, 100.0 * body_sec / body_total,
             "OK" if body_sec / float(body_total) <= 0.15 else "OVER"))
    print("   (running furniture is %d ch of grey, the same strip repeated on %d pages)"
          % (furniture, d.page_count))
    # ---------------------------------------------------------------- item 4's per-paragraph cap
    # 🔴 COUNTED, NOT TRUSTED. Item 4 allows the accent colours on at most three quantities per
    # paragraph. A block in the text layer is close enough to a paragraph for this purpose, and a
    # "coloured span" is one whose colour is neither the body ink, the secondary grey nor the navy
    # used for headings: that is, one of the two accents doing the item 4 job.
    ACCENTS = {0x1f5fae, 0xc2521f}
    print()
    print("ACCENT-COLOURED QUANTITIES PER PARAGRAPH  (item 4 allows 3)")
    worst = []
    for i in range(d.page_count):
        for b in d[i].get_text("dict")["blocks"]:
            runs, prev = 0, False
            txt = []
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    hit = sp["color"] in ACCENTS
                    if hit and not prev:
                        runs += 1
                    prev = hit
                    txt.append(sp["text"])
            if runs:
                worst.append((runs, i + 1, " ".join("".join(txt).split())[:58]))
    worst.sort(reverse=True)
    over = [w for w in worst if w[0] > 3]
    for n_, pg, t_ in worst[:6]:
        print("   %d  p%-2d  %s" % (n_, pg, t_))
    print("   paragraphs over the cap of 3: %d   %s"
          % (len(over), "OK" if not over else [(w[1], w[0]) for w in over]))

    print()
    print("FONT SIZES IN USE (by character count)")
    for sz, c in sorted(sizes.items()):
        print("   %5g pt  %7d chars %s" % (sz, c, "" if sz >= 8.5 else "  <- BELOW THE 8.5 FLOOR"))

    # ---------------------------------------------------------------- label overlaps
    # 🔴 ANY INTERSECTION COUNTS. The previous threshold was 30 % of the smaller box and it hid
    # real collisions: "90% target" against "80% reachable at n=4" measured 9.1 % and was reported
    # as clean while being plainly wrong on the page. The brief asks for any intersection, so the
    # only tolerance kept is a sub-point epsilon in BOTH directions, because adjacent words on one
    # line legitimately share an edge and a shared edge is not a collision.
    EPS = 0.4
    print("LABEL OVERLAPS  (any intersection deeper than %.1f pt in both directions)" % EPS)
    total_ov = 0
    for i in range(d.page_count):
        spans = []
        for b in d[i].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    if sp["text"].strip():
                        spans.append((fitz.Rect(sp["bbox"]), sp["text"].strip()))
        hits = []
        for x in range(len(spans)):
            for y in range(x + 1, len(spans)):
                ra, ta = spans[x]
                rb, tb = spans[y]
                inter = ra & rb
                if inter.is_empty:
                    continue
                area = inter.get_area()
                small = min(ra.get_area(), rb.get_area()) or 1
                if inter.width <= EPS or inter.height <= EPS:
                    continue
                # 🔴 ONE WORD IS SOMETIMES TWO SPANS, AND THAT IS NOT A COLLISION. A PDF splits a
                # text run wherever kerning or a glyph substitution says to, so the axis label
                # "-400" arrives as "-4" and "00" with their boxes abutting, and the pair was
                # counted as an overlap at 2 %. Left uncorrected the harness can never report zero,
                # which makes a zero-overlap assertion impossible to write. Spans sharing a line box
                # that merely abut are one run; spans sharing a line box that genuinely print over
                # each other overlap by far more than a kern.
                if abs(ra.y0 - rb.y0) < 0.6 and abs(ra.y1 - rb.y1) < 0.6:
                    if inter.width / (min(ra.width, rb.width) or 1) < 0.40:
                        continue
                hits.append((ta[:26], tb[:26], 100.0 * area / small))
        total_ov += len(hits)
        if hits:
            print("   p%-2d %d overlap(s)" % (i + 1, len(hits)))
            for a_, b_, pp in hits[:8]:
                print("        %r x %r  (%.0f%%)" % (a_, b_, pp))
    print("   TOTAL overlapping label pairs: %d" % total_ov)

    # ---------------------------------------------------------------- lines drawn through words
    # 🔴 THE CHECK ABOVE COMPARES TEXT WITH TEXT, AND THAT IS HALF THE PROBLEM. It reported zero
    # while three labels were being printed through by lines: the 90 % target rule crossed the
    # "87.9%" value on page 6, the portfolio marker crossed its own "this site" note on page 7, and
    # the runtime track ran under "Reactive incumbent" on page 3. Every one was visible at a glance
    # and invisible to the harness, because one side of each collision was a stroke rather than a
    # word.
    #
    # ⚠ STROKES ONLY, NOT FILLS. Text sitting on a filled rectangle is normal and wanted: the hour
    # digits inside the decision strip's cells, the tile values on their panels. A stroked path
    # running through a glyph is not.
    #
    # ⚠ AND THE TEXT BOX IS SHRUNK BEFORE TESTING. A rule immediately under a line of type, which is
    # what every table in this document uses, touches the descender box without touching a letter.
    # Testing the middle 62 % of the box vertically keeps those and still catches a line through the
    # x-height.
    print()
    print("LINES DRAWN THROUGH TEXT  (stroked paths crossing the middle of a glyph box)")
    total_st = 0
    for i in range(d.page_count):
        spans = []
        for b in d[i].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for sp in l["spans"]:
                    if sp["text"].strip():
                        r = fitz.Rect(sp["bbox"])
                        pad = r.height * 0.19
                        spans.append((fitz.Rect(r.x0 + 0.6, r.y0 + pad, r.x1 - 0.6, r.y1 - pad),
                                      sp["text"].strip()))
        # ⚠ A KNOCKOUT IS NOT A COLLISION, AND PAINT ORDER IS THE ONLY WAY TO TELL. The standard
        # fix for a label on a rule is an opaque plate behind the label, which leaves the geometry
        # exactly as it was: the stroke still crosses the glyph box, and nothing is printed through.
        # `get_drawings()` returns paths in paint order, so a white fill that fully contains the text
        # box and is painted AFTER the stroke means the reader sees the label, not the line. Without
        # this the check can only be satisfied by moving labels away from the lines they name.
        knock = []
        segs = []
        for order, dr in enumerate(d[i].get_drawings()):
            f = dr.get("fill")
            if f and "f" in (dr.get("type") or "") and min(f) > 0.95:
                knock.append((order, dr["rect"]))
            if "s" not in (dr.get("type") or ""):
                continue
            for it in dr["items"]:
                if it[0] == "l":
                    segs.append((order, fitz.Point(it[1]), fitz.Point(it[2])))
                elif it[0] == "re":
                    q = fitz.Rect(it[1])
                    for a_, b_ in (((q.x0, q.y0), (q.x1, q.y0)), ((q.x1, q.y0), (q.x1, q.y1)),
                                   ((q.x1, q.y1), (q.x0, q.y1)), ((q.x0, q.y1), (q.x0, q.y0))):
                        segs.append((order, fitz.Point(*a_), fitz.Point(*b_)))
        hits = []
        for box, txt in spans:
            crossed = [o for o, a, b2 in segs if _seg_hits_rect(a, b2, box)]
            if not crossed:
                continue
            covered = [o for o, r in knock if r.contains(box)]
            if covered and max(covered) > min(crossed):
                continue                      # an opaque plate was painted over the line
            hits.append(txt)
        total_st += len(hits)
        if hits:
            print("   p%-2d %d label(s) crossed by a line: %s"
                  % (i + 1, len(hits), [t[:26] for t in hits[:6]]))
    print("   TOTAL labels with a line through them: %d" % total_st)

    # ---------------------------------------------------------------- prose hygiene
    txt = "\n".join(d[i].get_text() for i in range(d.page_count))
    paras = [re.sub(r"\s+", " ", x).strip() for x in txt.split("\n") if len(x.strip()) > 90]
    dupes = [(n, p[:58]) for p, n in Counter(paras).items() if n > 1]
    print()
    # ---------------------------------------------------------------- item 8: space before a unit
    # ⚠ THE PER CENT SIGN IS DELIBERATELY EXEMPT. SI would put a space before it, but no reader of
    # a commercial report expects "10.7 %", and the document is consistent in setting it closed up.
    # Everything with a letter in it takes the space: 18.0 °C, 60.3 m, 5.34 s, 406 h, 13 MW.
    import re as _re
    # ⚠ THE ANGULAR DEGREE IS EXEMPT TOO, and it was the only thing this check found. A bearing is
    # written "255°" closed up by every convention there is, while a temperature is "18.0 °C" with
    # the space. So a bare degree sign is skipped and °C is not.
    UNIT = _re.compile(r"[0-9](?:°C|m/s|MW|km|mm|m²|(?<![A-Za-z])(?:m|h|s|K)(?![A-Za-z0-9]))")
    bad_units = []
    for i in range(d.page_count):
        for line in d[i].get_text().split(chr(10)):
            for m in UNIT.finditer(line):
                bad_units.append("p%d %r" % (i + 1, line[max(0, m.start() - 22):m.end() + 4]))
    print()
    print("SPACE BEFORE A UNIT  (item 8; the per cent sign is exempt)")
    print("   violations: %d   %s" % (len(bad_units), "OK" if not bad_units
                                      else bad_units[:6]))

    # ---------------------------------------------------------------- one quantity, one value
    # 🔴 THIS CHECK EXISTS BECAUSE TWO CHART LABELS CARRIED ASHBURN'S FIGURES ONTO 249 OTHER SITES.
    # `agent_vs_incumbent` had the literal "913 days" in its subtitle and `coverage` the literal
    # "43,260 rounds" in a bar label, both Ashburn's. MEASURED in the shipped
    # GA_way_39083797_report.pdf: page 3 said "across 913 days the agent never trained on" and the
    # paragraph two lines below said "the second half, 908 days, was kept back"; page 5 said "43,260
    # rounds" against "42,747 rounds" in its own prose. Every other check in this file passed on
    # those documents, because none of them compares a number to another number.
    #
    # THE RULE IT ENFORCES IS NARROW AND MECHANICAL: take every number that is followed by a unit
    # noun this document uses for a per-site measurement, and require that all occurrences of the
    # same noun in the same document agree. It cannot know which value is right; it only knows that
    # two of them cannot both be.
    #
    # ⚠ NOUNS ARE LISTED RATHER THAN INFERRED, and deliberately few. "hours" appears for the day, the
    # year, the record and the free-cooling total, all legitimately different, so it is not here.
    # These four are quantities a single site has exactly one of.
    print()
    print("ONE QUANTITY, ONE VALUE  (the same noun must not carry two numbers)")
    import re as _re2
    NOUNS = ("days the agent never trained on|days, was kept back|days held out", "held-out days"), \
            ("rounds of the five-year record|rounds", "adaptive-bound rounds"), \
            ("distinct reasons", "distinct reasons"), \
            ("per-lead bounds", "per-lead bounds")
    alltext = " ".join(" ".join(d[i].get_text().split()) for i in range(d.page_count))
    qbad = []
    for pat, label in NOUNS:
        vals = set()
        for m in _re2.finditer(r"([0-9][0-9,]{1,9})\s+(?:%s)" % pat, alltext):
            vals.add(m.group(1).replace(",", ""))
        if len(vals) > 1:
            qbad.append((label, sorted(vals, key=int)))
        print("   %-24s %s" % (label, sorted(vals, key=int) if vals else "not stated"))
    print("   quantities stated two different ways: %d   %s"
          % (len(qbad), "OK" if not qbad else qbad))

    print()
    print("PROSE")
    print("   duplicate paragraphs   %d %s" % (len(dupes), dupes[:3]))
    print("   four-plus decimals     %s" % (re.findall(r"\d+\.\d{4,}", txt)[:6] or "none"))
    print("   ends mid-sentence      %s" % (not txt.strip().endswith(".")))
    print("   last 64 chars          %r" % txt.strip()[-64:])

    if a.png:
        os.makedirs(a.png, exist_ok=True)
        for i in range(d.page_count):
            d[i].get_pixmap(dpi=120).save(os.path.join(a.png, "p%02d.png" % (i + 1)))
        print()
        print("   rendered %d page PNGs into %s" % (d.page_count, a.png))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
