# -*- coding: utf-8 -*-
"""VERIFY_PALETTE -- reads the colour tokens out of demo/index.html and MEASURES every pair the
page actually renders, in BOTH themes, against the WCAG 2.1 floors.

    python testing/verify_palette.py

WHY THIS FILE EXISTS. The stylesheet already carries the arithmetic in prose -- "--muted #7e8783 ->
3.10:1 and it carries 10.5px uppercase labels" -- and a number written in a comment is a number no
check re-reads. That is the same defect class the rest of this project polices (a sentence stating a
figure nothing verifies), applied to colour. Worse, a second theme doubles every pair: the light
palette was measured by hand once, and the dark palette that used to sit beside it was never
finished, which is exactly why it was deleted in the first place.

So the floors are asserted here instead of asserted in English:

  * 4.5:1  body and label text                     (WCAG 1.4.3 AA, normal-size text)
  * 3.0:1  non-text graphics -- axes, borders,
           legend swatches, chart marks            (WCAG 1.4.11)
  * 3.0:1  large text (>=24px, or >=18.66px bold)  (WCAG 1.4.3 AA, large text)

It does NOT re-measure the CVD dE figures quoted at the top of the stylesheet. Those were measured
on the --series-1/--series-2 pair, that pair is unchanged in both themes, and this script asserts
only that it stays unchanged -- a claim it can actually check.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "AGENTIC-ARBITER", "demo", "index.html")

FAILS = []
CHECKS = [0]


def srgb_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(hexstr):
    h = hexstr.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb_lin(r) + 0.7152 * srgb_lin(g) + 0.0722 * srgb_lin(b)


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# 🔴 rgba() IS CAPTURED AS WELL AS HEX, ADDED 2026-08-28. This used to read `#hex` only, which meant
# `--glass` -- the frosted panel fill behind the bezel, the KPI cards, the drawer and the facility
# dropdown -- was simply invisible to this file, and so was every pair rendered on top of it. It is
# stored in the same map as the opaque tokens; only glass_surfaces() parses it, and no PAIR names it
# as a foreground, so nothing asks lum() to read an alpha.
TOKEN_RE = r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))"


def read_tokens():
    """Return {theme: {token: hex}} for the light block and the dark block."""
    src = open(PAGE, encoding="utf-8").read()
    # Comments first: a hex quoted inside an explanatory comment is not a declaration.
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    i = src.find("<style>")
    j = src.find("</style>")
    if i < 0 or j < 0:
        raise SystemExit("index.html has no <style> block")
    css = src[i:j]

    def block(sel):
        k = css.find(sel)
        if k < 0:
            return None
        o = css.find("{", k)
        c = css.find("}", o)
        return css[o + 1:c]

    # 🔴 `:root{}` IS THE DARK PALETTE, and it used to be the light one. The page became dark-first
    # on 2026-08-27, which inverted which block is the base and which one overrides it. Reading the
    # base as "light" after that change would have measured the DARK values against the LIGHT
    # surfaces and reported a clean pass for a palette nothing had actually checked -- a check that
    # is wrong in the flattering direction, which is the worst kind there is.
    # The override block is asserted to EXIST rather than assumed, so this can never silently
    # degrade into measuring one theme twice and calling it two.
    out = {}
    base = block(":root{")
    if base is None:
        raise SystemExit("no :root{ block found")
    out["dark"] = dict(re.findall(TOKEN_RE, base))
    light = block('[data-theme="light"]')
    if light is None:
        raise SystemExit('no :root[data-theme="light"] block found -- either the second theme is '
                         'missing, or this is a version where DARK was the override and this '
                         'reader is now inverted')
    d = dict(out["dark"])
    d.update(dict(re.findall(TOKEN_RE, light)))
    out["light"] = d
    return out


def ck(name, ok, detail=""):
    CHECKS[0] += 1
    print("   [%s] %-58s %s" % ("ok  " if ok else "FAIL", name, detail))
    if not ok:
        FAILS.append(name)


# EVERY PAIR IS DECLARED WITH THE ELEMENT THAT RENDERS IT, so a floor can be argued with rather
# than merely failed. (token, surface, floor, what renders it)
PAIRS = [
    ("--text-primary",   ("--page", "--surface-1", "--surface-2"), 4.5, "body copy, tile values"),
    ("--text-secondary", ("--page", "--surface-1", "--surface-2"), 4.5, ".note, .tile .d, h3"),
    ("--muted",          ("--page", "--surface-1", "--surface-2"), 4.5, ".tile .k, .plate-cell .pk, th"),
    ("--good",           ("--page", "--surface-1", "--surface-2"), 4.5, "positive figures in prose"),
    ("--warning",        ("--page", "--surface-1", "--surface-2"), 4.5, ".plate-refused .pv"),
    ("--critical",       ("--page", "--surface-1", "--surface-2"), 4.5, ".err, .plate-cell.miss .pv"),
    ("--action",         ("--page", "--surface-1", "--surface-2"), 4.5, "summary, .btn:hover label"),
    ("--axis",           ("--page", "--surface-1", "--surface-2"), 3.0, "chart axes, .btn border"),
    ("--grid",           ("--surface-1", "--surface-2"),           1.2, "table rules (decorative)"),
    ("--series-1",       ("--surface-1", "--surface-2"),           3.0, "legend swatch, chart line"),
    ("--series-2",       ("--surface-1", "--surface-2"),           3.0, "legend swatch, chart line"),
    # 🔴 THE FROSTED SURFACES, ADDED 2026-08-28, AND NOTHING MEASURED THEM BEFORE. `--glass` is
    # translucent, so a pair against it is a pair against a COMPOSITE -- see GLASS_OVER below for the
    # two backdrops it is composited over and why those two. #bezel, .plate-cell, .inspector and
    # .mapbar-drop all render text on it.
    ("--text-primary",   ("@glass-on-page", "@glass-on-map"),      4.5,
     "#bezel, .plate-cell .pv, .inspector h3, .mfrow .srchname"),
    ("--text-secondary", ("@glass-on-page", "@glass-on-map"),      4.5,
     ".rail-step, .insp-rows dd, .mfrow .srchmeta"),
    # The drawer is the one that MATTERS here and it is why --muted moved: .inspector is
    # background:var(--glass), fixed to the right edge, and opens from a map click, so these two sit
    # on glass composited over the basemap rather than over the page.
    ("--muted",          ("@glass-on-page", "@glass-on-map"),      4.5,
     ".inspector .eyebrow, .insp-rows dt, .plate-cell .pk, .plate-stamp"),
]

# THE BACKDROPS A FROSTED PANEL SITS ON, and there are exactly two worth checking.
#   the PAGE, which is what is behind the bezel and the KPI plate; and
#   the BASEMAP, which is what is behind the facility dropdown, and which is the lightest thing this
#   page puts behind text in dark mode and the darkest in light mode -- the worst case either way.
# The basemap is NOT a token: it is OpenStreetMap raster pushed through `raster-brightness-max`, so
# its rendered value has to be MEASURED rather than read. Both figures below are the mean RGB of the
# same 630x360 px region of the map canvas, in two real 1440 px screenshots of the California view,
# located by a marker the page itself painted at the canvas origin so the two samples cover identical
# pixels. The page background was read out of the same screenshots to confirm which theme each was:
#   dark  #323232   (raster-brightness-max 0.22;  page read back as #09090b)
#   light #cfcfcf   (raster-brightness-min 0.18, max 0.97;  page read back as #fafafa)
# `backdrop-filter: blur()` does not change a region's mean luminance -- it redistributes it -- so the
# mean is the right statistic for a contrast floor over a blurred backdrop.
BASEMAP_RENDERED = {"dark": "#323232", "light": "#cfcfcf"}


def composite(fg_rgba, bg_hex):
    """Source-over: what a translucent fill actually renders as on a given background."""
    r, g, b, a = fg_rgba
    br, bg_, bb = (int(bg_hex[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (round(r * a + br * (1 - a)), round(g * a + bg_ * (1 - a)),
                              round(b * a + bb * (1 - a)))


def parse_rgba(v):
    """rgba(24,24,27,.72) -> (24, 24, 27, 0.72). Returns None for anything else."""
    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)", v.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            float(m.group(4)) if m.group(4) else 1.0)


def glass_surfaces(tok, theme):
    """The two composited surfaces, as {name: hex}, or {} if --glass is not an rgba() this run."""
    g = parse_rgba(tok.get("--glass", ""))
    if not g:
        return {}
    return {"@glass-on-page": composite(g, tok["--page"]),
            "@glass-on-map": composite(g, BASEMAP_RENDERED[theme])}

# ---- THE ONE PAIR THAT CANNOT BE FIXED BY MOVING THE COLOUR, AND WHAT IS REQUIRED INSTEAD -------
#
# `--series-2` (#eb6834) measures 2.83:1 against --surface-2 in the LIGHT theme, which is under the
# 3:1 floor for a graphic a reader must perceive. It is not retuned, because the CVD dE figures
# quoted at the top of the stylesheet were measured on that exact fill by an instrument this tree
# does not contain -- moving it would invalidate a stated validation rather than repair anything.
#
# WCAG 2.1's own remedy for this case is a perceivable BOUNDARY around the object, so that is what
# the page does. This is NOT a waiver: three things have to be true, each asserted below, and if any
# of them stops being true the check fails exactly as it would have without the remedy.
#
#   1. the boundary token itself clears the 3:1 floor on every surface;
#   2. the stylesheet actually draws a boundary on `.legend i` -- the swatch is the smallest, most
#      isolated instance of the fill on the page, so if anything needs it, it does;
#   3. the script casings its canvas marks with that same token, because a 2 px polyline of the fill
#      on near-white paper has the identical problem and a CSS rule cannot reach a canvas.
#
# theme -> {failing token: (boundary token, css selector that must carry it, js identifier)}
BOUNDARY_REMEDY = {
    "light": {"--series-2": ("--series-2-edge", ".legend i", "EDGE")},
}

# Text on a filled button: the fill is the background, not the paper.
ON_FILL = [("--action-ink", "--action", 4.5, ".btn-go label on its own fill")]

# The validated categorical pair. Unchanged in both themes BY DESIGN -- the CVD dE figures at the
# top of the stylesheet were measured on it and cannot be re-measured here.
FROZEN = ["--series-1", "--series-2"]


def main():
    themes = read_tokens()
    print("VERIFY_PALETTE -- measured, not asserted in prose")
    print("   themes found: %s" % ", ".join(sorted(themes)))
    for theme in sorted(themes):
        tok = themes[theme]
        print("\n   ---- %s ----" % theme.upper())
        remedies = BOUNDARY_REMEDY.get(theme, {})
        # The composited frosted surfaces join the opaque tokens in one lookup, so a pair does not
        # have to know which kind it is asking about. Named with a leading @ so they cannot collide
        # with a real custom property.
        surf = dict(tok)
        surf.update(glass_surfaces(tok, theme))
        for name, surfaces, floor, what in PAIRS:
            if name not in tok:
                ck("%s declared" % name, False, "missing in %s" % theme)
                continue
            missing = [x for x in surfaces if x not in surf]
            if missing:
                # A surface this file names but the page does not define is a FAILURE, not a skip: the
                # loop used to `continue` past an unknown surface, which would have reported PASS for
                # a pair it never measured.
                ck("%s: every surface it is checked on exists" % name, False,
                   "unknown: %s" % ", ".join(missing))
                continue
            worst, worst_s = 99.0, None
            for s in surfaces:
                r = ratio(tok[name], surf[s])
                if r < worst:
                    worst, worst_s = r, s
            if worst >= floor or name not in remedies:
                ck("%s on %s >= %.1f" % (name, worst_s, floor), worst >= floor,
                   "%.2f:1  %s on %s  (%s)" % (worst, tok[name], surf[worst_s], what))
                continue
            # Under the floor AND carrying a declared boundary remedy: the fill is excused only if
            # all three conditions hold. Each is its own check, so a half-applied remedy fails.
            edge, selector, jsname = remedies[name]
            src = open(PAGE, encoding="utf-8").read()
            print("   [note] %-58s %.2f:1 -- boundary remedy, %s" % (
                "%s on %s is UNDER %.1f" % (name, worst_s, floor), worst, edge))
            ew = min(ratio(tok[edge], surf[s]) for s in surfaces) if edge in tok else 0.0
            ck("  %s clears %.1f on every surface" % (edge, floor), ew >= floor,
               "%.2f:1  %s" % (ew, tok.get(edge)))
            # The rule has to be in the STYLESHEET and has to name the token. Comments are already
            # stripped from `src` for the token scan, but this reads the raw file, so the selector
            # is searched for together with the token inside its own declaration block.
            m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", src)
            ck("  the stylesheet draws a boundary on `%s`" % selector,
               bool(m) and ("border" in m.group(1)) and ("--axis" in m.group(1)
                                                         or edge in m.group(1)),
               (" ".join(m.group(1).split())[:70] if m else "selector not found"))
            ck("  the script casings its canvas marks (`%s`)" % jsname,
               re.search(r"\b%s\b\s*=" % re.escape(jsname), src) is not None
               and src.count(jsname) >= 3,
               "%d references to %s" % (src.count(jsname), jsname))
        for ink, fill, floor, what in ON_FILL:
            if ink in tok and fill in tok:
                r = ratio(tok[ink], tok[fill])
                ck("%s on %s >= %.1f" % (ink, fill, floor), r >= floor,
                   "%.2f:1  (%s)" % (r, what))

    if "dark" in themes:
        print("\n   ---- the validated pair must be identical in both themes ----")
        for f in FROZEN:
            same = themes["light"].get(f, "").lower() == themes["dark"].get(f, "").lower()
            ck("%s unchanged across themes" % f, same,
               "%s / %s" % (themes["light"].get(f), themes["dark"].get(f)))

    print("\n   %d checks, %d failed" % (CHECKS[0], len(FAILS)))
    if FAILS:
        for f in FAILS:
            print("      FAILED: %s" % f)
        return 1
    print("   VERDICT: every measured pair clears its floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
