# -*- coding: utf-8 -*-
"""Instance the three static Inter weights the site report embeds, from the repo's own variable font.

    python tools/make_report_fonts.py

WHY THIS EXISTS AT ALL. `demo/fonts/inter-latin.woff2` is what the web page loads, and it is a
VARIABLE font: one file with a `wght` axis running 100 to 900. ReportLab cannot read woff2 and
cannot vary an axis, so the report needs static TTFs. Rather than adding a font download to the
build, this instances the file already in the repository, which means the PDF and the web page are
rendering the same outlines by construction.

🔴 THE NAME TABLE IS THE WHOLE REASON THIS IS A SCRIPT AND NOT A ONE-LINER.
FIRST ATTEMPT, MEASURED: instanced with `updateFontNames=False`, so all three files still declared
themselves "Inter Regular" internally. ReportLab registered three names, deduplicated the faces
behind them, and embedded a SINGLE `Inter-Regular` subset. A nine-page document that asked for
Inter-Bold on every heading rendered the entire hierarchy at one weight, and `get_fonts()` showed
one Inter where there should have been three.

⚠ AND THE FIX HAS TO SATISFY TWO LIBRARIES WITH DIFFERENT IDEAS OF A FONT NAME.
  * ReportLab keys the embedded subset off the PostScript name (nameID 6), so those must differ.
  * matplotlib looks up `font.family` against the FAMILY name (nameID 1), so those must MATCH,
    or `font.family = "Inter"` stops resolving and the two matplotlib charts silently fall back to
    DejaVu Sans while the other five use Inter.
So: family stays "Inter" for all three, and the subfamily, full name and PostScript name carry the
weight. That is also simply the correct convention, which is usually the way out of this kind of
bind.

⚠ WHAT THE SUBSET DOES NOT CONTAIN. `inter-latin.woff2` is the latin subset, 230 glyphs. It has
ASCII, the degree sign, the en and em dash and the multiplication sign. It does NOT have U+2264,
U+2265 or U+2192, so the report writes "at or under" rather than a glyph it cannot draw.
`inter-latin-ext.woff2` is deliberately NOT used: it is the accent range and carries no ASCII at
all, so instancing it produces a face that cannot set a single English word.
"""
import os
import sys

SRC = os.path.join("AGENTIC-ARBITER", "demo", "fonts", "inter-latin.woff2")
OUT = os.path.join("AGENTIC-ARBITER", "src", "reportassets")
WEIGHTS = ((400, "Regular"), (600, "SemiBold"), (700, "Bold"))
# The characters the report actually sets. Checked rather than hoped for.
NEEDED = (list("0123456789abcdefghijklmnopqrstuvwxyz"
               "ABCDEFGHIJKLMNOPQRSTUVWXYZ.,:;%$()[]/-+=<>?!'\"&#*")
          + ["°", "–", "·", "×"])


def main():
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    if not os.path.exists(SRC):
        raise SystemExit("%s missing -- run from the repository root" % SRC)
    os.makedirs(OUT, exist_ok=True)

    probe = TTFont(SRC)
    if "fvar" not in probe:
        raise SystemExit("%s is not a variable font, so it cannot be instanced" % SRC)
    axes = {a.axisTag: (a.minValue, a.maxValue) for a in probe["fvar"].axes}
    print("   source     %s" % SRC)
    print("   axes       %s" % ", ".join("%s %g..%g" % (k, v[0], v[1]) for k, v in axes.items()))

    made = []
    for weight, sub in WEIGHTS:
        ft = TTFont(SRC)
        instancer.instantiateVariableFont(ft, {"wght": weight}, inplace=True,
                                          updateFontNames=False)
        nm = ft["name"]
        for rec in list(nm.names):
            pid, enc, lang = rec.platformID, rec.platEncID, rec.langID
            if rec.nameID == 1:
                nm.setName("Inter", 1, pid, enc, lang)                 # matplotlib reads this
            elif rec.nameID == 2:
                nm.setName(sub, 2, pid, enc, lang)
            elif rec.nameID == 4:
                nm.setName("Inter %s" % sub, 4, pid, enc, lang)
            elif rec.nameID == 6:
                nm.setName("Inter-%s" % sub, 6, pid, enc, lang)        # ReportLab keys on this
        # 🔴 TABULAR FIGURES, BAKED IN, BECAUSE NOTHING DOWNSTREAM CAN TURN THEM ON.
        # Inter ships them: the source carries `zero.tf` through `nine.tf` and a `tnum` feature in
        # GSUB that selects them. But ReportLab does not apply OpenType features when it draws a
        # TTF, and neither does svglib, so `tnum` is unreachable at render time however the document
        # asks for it. MEASURED on the font before this change, the ten digit advance widths were
        # 1292, 833, 1249, 1265, 1323, 1215, 1270, 1159, 1267, 1270: a "1" is two thirds the width
        # of a "4", so a column of numbers cannot line up and a figure that changes between two
        # builds visibly shifts its neighbours.
        #
        # Remapping the cmap for U+0030..U+0039 onto the `.tf` glyphs makes the tabular set the
        # DEFAULT, which is the correct choice for a document that is almost entirely numbers, and it
        # reaches all three renderers at once because it is no longer a feature, it is the font.
        tab = 0
        want = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
        order = set(ft.getGlyphOrder())
        pairs = [(0x30 + i, want[i] + ".tf") for i in range(10) if want[i] + ".tf" in order]
        if len(pairs) == 10:
            for table in ft["cmap"].tables:
                for cp, glyph in pairs:
                    if cp in table.cmap:
                        table.cmap[cp] = glyph
            tab = 10
        widths = [ft["hmtx"][want[i] + (".tf" if tab else "")][0] for i in range(10)]
        assert not tab or len(set(widths)) == 1, (
            "the .tf glyphs are not actually tabular: widths %r" % widths)
        print("   %-10s tabular figures %s   digit width %s"
              % (sub, "remapped" if tab else "NOT AVAILABLE", widths[0] if tab else "varies"))

        ft["OS/2"].usWeightClass = weight
        ft.flavor = None
        p = os.path.join(OUT, "Inter-%s.ttf" % sub)
        ft.save(p)
        made.append((sub, p))

    print()
    ok = True
    for sub, p in made:
        f = TTFont(p)
        cmap = f.getBestCmap()
        missing = [c for c in NEEDED if ord(c) not in cmap]
        print("   Inter-%-9s family=%-6s subfamily=%-9s ps=%-15s weight=%d  %d glyphs  %s"
              % (sub, f["name"].getDebugName(1), f["name"].getDebugName(2),
                 f["name"].getDebugName(6), f["OS/2"].usWeightClass, len(cmap),
                 "ok" if not missing else "MISSING %d" % len(missing)))
        if missing:
            ok = False
            print("      missing: %s" % ", ".join("U+%04X %r" % (ord(c), c) for c in missing))

    # The faces must be genuinely different, or the instancing silently did nothing.
    from fontTools.pens.boundsPen import BoundsPen
    stems = []
    for sub, p in made:
        f = TTFont(p)
        gs = f.getGlyphSet()
        bp = BoundsPen(gs)
        gs["H"].draw(bp)
        stems.append((sub, bp.bounds[0]))
    print()
    print("   left sidebearing of 'H', which must SHRINK as the stem thickens:")
    for sub, x in stems:
        print("      %-9s %d" % (sub, x))
    if len({x for _, x in stems}) != len(stems):
        print("   [FAIL] two weights produced identical outlines")
        ok = False

    ps = {TTFont(p)["name"].getDebugName(6) for _, p in made}
    if len(ps) != len(made):
        print("   [FAIL] PostScript names collide, so ReportLab will embed one face for all")
        ok = False
    fam = {TTFont(p)["name"].getDebugName(1) for _, p in made}
    if len(fam) != 1:
        print("   [FAIL] family names differ, so matplotlib's font.family = Inter will not resolve")
        ok = False

    print()
    print("   [%s] %d faces in %s" % ("ok" if ok else "FAIL", len(made), OUT))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
