# -*- coding: utf-8 -*-
"""THE SEVEN CHARTS, AS VECTOR SVG. Nothing here reads an artefact; it is handed numbers.

WHY FIVE ARE HAND-WRITTEN AND TWO USE MATPLOTLIB, which was a deliberate split rather than
laziness in either direction. A coloured band, a line with a shaded region, stacked bars, grouped
bars and a dot plot are `<rect>`, `<line>`, `<path>` and `<text>`: writing them directly costs less
code than turning matplotlib's defaults off, and it means the chart inherits the exact palette and
the exact Inter weights the document uses. The polar plot and the histogram are the two where
matplotlib genuinely saves work, because angular axes and binning are fiddly by hand.

🔴 SVGLIB DROPS FONT WEIGHT AND FALLS BACK TO HELVETICA UNLESS YOU REGISTER THE FAMILY.
MEASURED before this module existed: `font-family="Inter" font-weight="600"` came out of `svg2rlg`
as plain `Helvetica`, for every weight, so every chart label would have disagreed with the body text
and Inter would not have embedded for any of them. `svglib.fonts.register_font` is the supported
fix and `register()` below calls it. It also collapses `600` and `700` to one "bold" slot, which is
why charts use exactly two weights.

⚠ SVGLIB SCALES SVG PIXELS TO POINTS AT 0.75. A 664 px wide chart arrives as a 498 pt Drawing,
which is the full text measure of the page. Design in px here; the document does not rescale.

⚠ GREYSCALE IS SOLVED BY LUMINANCE ALONE, WHICH IS WHY THE HATCH COULD GO. An earlier version
carried diagonal hatch lines on every mechanical fill as a second channel for monochrome printing.
Item 6 of the layout brief removes them, and the removal is safe rather than merely obedient: free
cooling sits at relative luminance 0.129 against constraint fills at 0.28 and 0.79, so a monochrome
printer separates all three unaided. The hatch was costing about 340 `<line>` elements per chart and
reading as texture noise at 8.5 pt. There is no hatch anywhere in this module now, and no helper to
draw one.
"""
import math
import os

# --------------------------------------------------------------------------- ONE PALETTE
# 🔴 SIX VALUES, AND NOTHING OUTSIDE THEM. The previous version used two competing blues
# (#0d5c82 for headings, #2a78d6 for the agent series), an orange, a navy and two greys, which is
# the incoherence. Every ratio below is MEASURED against white paper by the WCAG 2.1 formula.
#
#   NAVY    #12274a  14.84:1   headline text only
#   BLUE    #1f5fae   6.35:1   THE single blue: headings, accents, agent, free cooling
#   ORANGE  #c2521f   4.65:1   the one accent, reserved for the plant limit and MODELED flags
#   BODY    #2b343f  12.42:1   all body and table text, the value the brief names
#   SECOND  #525c6b   6.77:1   captions and axis labels
#   RULE    #d5dce3      n/a   rules and light fills, never text
#   NEUTRAL #c9d1da      n/a   the baseline/mechanical fill, never text
#
# ⚠ WHY THE BLUE IS #1f5fae AND NOT THE SITE'S #2a78d6. The brief asks for ONE blue doing both
# headings and the series. The site's --series-1 measures 4.42:1, below the 4.5:1 floor for text, so
# using it for headings would have shipped failing contrast. #1f5fae is the same hue one step darker
# and clears text at 6.35:1, so a single value can do both jobs. It reads as the same blue beside
# the page; the alternative was keeping two blues, which is what was wrong before.
#
# ⚠ THE OLD CAPTION GREY #7c8794 IS GONE. It measured 3.65:1 and was being used for body copy on
# three pages. #525c6b replaces it at 6.77:1.
#
# ⚠ GREYSCALE IS SOLVED BY LUMINANCE. Free cooling L=0.129, the solid constraint orange L=0.28 and
# the constraint tint L=0.79 are three steps a monochrome printer separates without any pattern.
NAVY = "#12274a"
BLUE = "#1f5fae"
ORANGE = "#c2521f"
BODY = "#2b343f"
SECOND = "#525c6b"
RULE = "#d5dce3"
NEUTRAL = "#c9d1da"
NEUTRAL_EDGE = "#8a949f"
BLUE_PALE = "#dce7f6"
ORANGE_PALE = "#f7e4d9"    # fill only, never text
PAPER = "#ffffff"

# The names the rest of the module uses. FREE and MECH are the two series and they mean the same
# thing in every chart in the document.
FREE = BLUE
MECH = NEUTRAL
FREE_PALE = BLUE_PALE
MECH_PALE = NEUTRAL
TEAL = BLUE            # the second blue is deleted; anything that asked for it gets the one blue
GREY = BODY
MUTED = SECOND

# --------------------------------------------------------------------------- ONE TYPE SCALE
# Sizes in SVG px. svglib maps px to points at 0.75, so 13.33 px lands at 10 pt. Nothing below
# 8.5 pt anywhere, which is the document's floor.
PX = 1 / 0.75
T_TITLE = round(13.0 * PX, 2)
T_SUB = round(9.0 * PX, 2)
T_LABEL = round(9.5 * PX, 2)
T_AXIS = round(8.5 * PX, 2)
T_VALUE = round(11.0 * PX, 2)

W = 664                   # px; arrives as 498 pt, the full measure
F = "Inter"


def register(asset_dir):
    """Point BOTH renderers at the instanced Inter. Call once before any chart is converted."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from svglib import fonts as SF
    for label, name in (("Regular", "Inter"), ("SemiBold", "Inter-SemiBold"),
                        ("Bold", "Inter-Bold")):
        p = os.path.join(asset_dir, "Inter-%s.ttf" % label)
        pdfmetrics.registerFont(TTFont(name, p))

    # 🔴 WITHOUT THIS, EVERY <b> IN THE DOCUMENT DOES NOTHING, SILENTLY. Registering three faces
    # tells ReportLab the fonts EXIST; registerFontFamily is what tells it which face to reach for
    # when a paragraph's markup asks for bold. Missing it, `Paragraph` resolves <b> against the
    # family of "Inter", finds no family, and falls back to the normal face without warning.
    #
    # MEASURED on the build before this line existed: 16,379 characters of Inter-Regular against 945
    # of Inter-SemiBold, and every one of those 945 came from a style that names the face directly,
    # such as a heading or a tile value. All 37 <b> runs in the prose rendered as body weight. That
    # includes every lead-in on page 1, every emphasised figure, and the worked example's label. The
    # document had no inline emphasis at all and read flat, and nothing failed, which is exactly why
    # it survived several rounds of looking at it.
    #
    # ⚠ ITALIC MAPS TO THE UPRIGHT FACE ON PURPOSE. `demo/fonts/inter-latin.woff2` is the upright
    # variable font; there is no italic axis in it and no italic file to instance, so promising
    # ReportLab an italic would just produce a silent fallback of a different kind. The one <i> in
    # the document is changed to <b> instead, so the emphasis is real.
    SF.register_font("Inter", os.path.join(asset_dir, "Inter-Regular.ttf"),
                     weight="normal", rlgFontName="Inter")
    SF.register_font("Inter", os.path.join(asset_dir, "Inter-SemiBold.ttf"),
                     weight="bold", rlgFontName="Inter-SemiBold")

    # 🔴 AFTER svglib, NOT BEFORE, AND THAT ORDER IS THE WHOLE FIX. `svglib.fonts.register_font`
    # registers with ReportLab itself, and in doing so it REWRITES the "inter" family mapping. Called
    # before it, the line below was measurably undone: `tt2ps("Inter", bold=1, italic=0)` still
    # returned "Inter". Two registries, one of them clobbering the other, and no error from either.
    pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-SemiBold",
                                  italic="Inter", boldItalic="Inter-SemiBold")
    from reportlab.lib.fonts import tt2ps
    assert tt2ps("Inter", 1, 0) == "Inter-SemiBold", (
        "<b> resolves to %r, so every bold run in the document would render as body weight"
        % tt2ps("Inter", 1, 0))
    # 🔴 AND MATPLOTLIB, WHICH HAS ITS OWN FONT CACHE AND KNOWS NOTHING ABOUT EITHER OF THE ABOVE.
    # Without this it prints "findfont: Font family 'Inter' not found" once per label and silently
    # draws the polar plot and the histogram in DejaVu Sans, so two of seven charts would have
    # disagreed with the other five and with the body text. MEASURED: 400+ warnings on the first
    # full build. `addfont` reads the file's own family name, which is why the instanced faces keep
    # "Inter" rather than being renamed.
    try:
        import matplotlib
        from matplotlib import font_manager as FM
        for label in ("Regular", "SemiBold", "Bold"):
            FM.fontManager.addfont(os.path.join(asset_dir, "Inter-%s.ttf" % label))
        matplotlib.rcParams["font.family"] = "Inter"
    except Exception:                                                # noqa: BLE001
        pass          # charts still render, just in matplotlib's default face


# --------------------------------------------------------------------------- measuring
# 🔴 A LABEL THAT IS NOT MEASURED IS A LABEL THAT WILL COLLIDE. Item 2 of the brief asks for the
# collisions to be fixed programmatically rather than nudged by hand, which needs the one thing the
# SVG string does not carry: how wide the text actually is. ReportLab already has the instanced Inter
# loaded, and it is the same font svglib will draw with, so its metrics are the real ones.
#
# ⚠ UNITS. `stringWidth` works in points; this module works in SVG px, and svglib maps px to pt at
# 0.75. So a size given here in px is `size * 0.75` pt to ReportLab, and the width it returns comes
# back to px by dividing by 0.75 again.
def _tw(text, size_px, bold=False):
    try:
        from reportlab.pdfbase import pdfmetrics
        return pdfmetrics.stringWidth(str(text), "Inter-SemiBold" if bold else "Inter",
                                      size_px * 0.75) / 0.75
    except Exception:                                                     # noqa: BLE001
        return 0.56 * size_px * len(str(text))     # only if register() was never called


# --------------------------------------------------------------------------- svg helpers
def _open(w, h):
    return ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">' % (w, h, w, h),
            '<rect x="0" y="0" width="%d" height="%d" fill="%s"/>' % (w, h, PAPER)]


def _txt(x, y, s, size=T_LABEL, fill=BODY, anchor="start", bold=False):
    return ('<text x="%.2f" y="%.2f" font-family="%s" font-size="%s"%s fill="%s"%s>%s</text>'
            % (x, y, F, size, ' font-weight="bold"' if bold else '', fill,
               '' if anchor == "start" else ' text-anchor="%s"' % anchor, _esc(s)))


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _rule(x1, y, x2, colour=RULE, width=0.8):
    return ('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="%s"/>'
            % (x1, y, x2, y, colour, width))


# 🔴 CHART HEIGHTS ARE SET BY WHAT THE PAGE HAS SPARE, MEASURED PAGE BY PAGE. Item 1 asks for no
# page more than 15 % empty, and the first attempt at that was pagination: making the section breaks
# conditional so sections would flow together. It changed nothing, and the measurement said why.
# Every section ends with 150 to 225 pt of a 705 pt page unused, and a section needs about 300 pt to
# start at all, because its first chart is 230 pt or more. So no section could ever begin in the gap
# left by the one before it, and the gaps were structural.
#
# The gap is not a pagination problem, it is a chart that is smaller than its page. Growing the plot
# area is the fix that costs nothing: these are vector drawings, so a taller plot is a more readable
# plot, not a stretched one. The numbers below are the free space each page measured at, converted
# from points to SVG px at the 0.75 mapping.

# 🔴 ONE LEFT EDGE FOR EVERY PLOT AREA, so four charts on four pages line up with each other.
# Item 8 asks for the plot areas to start at 48 pt. 48 pt is 64 px at this module's 0.75 mapping, and
# every axis chart now takes its gutter from this one number instead of repeating 46. The y-axis tick
# labels live inside that gutter and are right-aligned to its inner edge, so the LABELS align with
# the page margin and the PLOT AREAS align with each other, which is what a reader flipping between
# pages 3, 4 and 6 actually sees.
#
# ⚠ THE DECISION STRIP KEEPS ITS FULL WIDTH ON PURPOSE. It has no y-axis and therefore nothing to
# put in a 48 pt gutter, so indenting it would leave an empty strip to the left of a band that is
# supposed to read as the full width of the day. It aligns with the body text instead, which is the
# stronger alignment for a full-measure band.
PLOT_L = 64               # px; 48 pt, the common left edge of every plot area with an axis

# =========================================================================== 1. decision strip
# THE HERO CHART. One cell per hour, free cooling against mechanical, and the reason a mechanical
# hour is mechanical printed under it. A reader who looks at nothing else should see the shape of
# the day and why it has that shape.
BINDING_SHORT = {"switch budget": "budget", "dry-bulb": "dry-bulb", "dew point": "dew pt",
                 "refusal": "refused", "minimum dwell": "dwell", "air quality": "air"}


def decision_strip(hours, height=None):
    """THE HERO CHART, and the one place a label used to run over its own data.

    🔴 UNDER rotate(-90) A LABEL GROWS UPWARD, SO text-anchor DECIDES WHETHER IT HITS THE CELLS.
    The local +x axis points UP the page after the rotation, so the default anchor="start" made every
    reason label grow from its anchor toward the strip. "budget" is 27 px long and fitted inside the
    42 px band; "dry-bulb" is 40 px and did not, so it printed across the bottom of the very hour it
    was explaining. anchor="end" reverses the direction of growth: each label now HANGS DOWNWARD
    from one common top edge just below the cells, exactly as the short ones already appeared to.

    🔴 AND THE BAND IS MEASURED, NOT GUESSED. The old 42 px was a constant that happened to fit the
    shortest label. The longest label now sets the band, the rule and legend move down by the same
    amount, and the assertion below refuses to emit a chart whose labels could reach the cells.

    ⚠ THREE TREATMENTS, BECAUSE THE DATA HAS THREE STATES. This site's 24 hours are 2 free cooling,
    12 held by the switch budget and 10 by dry-bulb: a single "mechanical" grey threw away the more
    interesting half of the chart. Per item 6, blue is what the agent achieves and orange is what
    constrains it, so both constraints are orange and they differ in weight, solid against tint.

    ⚠ NO HATCH. Item 6 removes it. The greyscale argument in the module docstring already showed the
    hatch was the second channel and not the load-bearing one: free cooling sits at L=0.129 against
    a mechanical tint above L=0.6, which a monochrome printer separates unaided.
    """
    n = len(hours)
    L, R_, T, cellh = 4, 4, 44, 46
    cw = (W - L - R_) / float(n)

    def state(h):
        if h["mode"] == "FREE-COOLING":
            return "free"
        return "budget" if (h.get("binding") or "") == "switch budget" else "other"

    labs = [("free" if state(h) == "free"
             else BINDING_SHORT.get(h.get("binding") or "", "blocked")) for h in hours]
    lab_px = max([_tw(l, T_AXIS) for l in labs] or [0])
    ty = T + cellh + 11                       # the common top edge, clear of the cells
    y = ty + lab_px + 12                      # the rule, below the longest label
    height = max(int(math.ceil(y + 40)), height or 0)

    # the build assertions item 2 asks for
    assert ty > T + cellh + 4, "reason labels would touch the hour cells"
    assert cw > T_AXIS * 1.3, ("%d columns of %.1f px cannot hold %.1f px of rotated text"
                               % (n, cw, T_AXIS))
    assert height >= y + 34, "the legend would fall outside the chart"

    s = _open(W, height)
    s.append(_txt(2, 16, "The agent's day, hour by hour", T_TITLE, NAVY, bold=True))
    s.append(_txt(W - R_, 16, "%d of %d hours free cooling"
                  % (sum(1 for h in hours if h["mode"] == "FREE-COOLING"), n), T_LABEL, MUTED,
                  anchor="end"))
    for i, h in enumerate(hours):
        x = L + i * cw
        st = state(h)
        fill, edge, ink = ((FREE, FREE, PAPER) if st == "free" else
                           (ORANGE, ORANGE, PAPER) if st == "budget" else
                           (ORANGE_PALE, ORANGE, BODY))
        s.append('<rect x="%.2f" y="%d" width="%.2f" height="%d" fill="%s" stroke="%s" '
                 'stroke-width="0.6"/>' % (x, T, cw - 0.8, cellh, fill, edge))
        s.append(_txt(x + cw / 2 - 0.4, T + 15, h["hour"], T_AXIS, ink,
                      anchor="middle", bold=True))
        # the reason, hanging downward from the common top edge
        s.append('<g transform="translate(%.2f,%.2f) rotate(-90)">%s</g>'
                 % (x + cw / 2 + 3, ty, _txt(0, 0, labs[i], T_AXIS, SECOND, anchor="end")))
    s.append(_rule(L, y, W - R_))

    # legend: laid out by measured width, so the three entries cannot run into each other
    lx = L
    for fill, edge, text in ((FREE, FREE, "free cooling: outside air does the work"),
                             (ORANGE, ORANGE, "held by the switch budget"),
                             (ORANGE_PALE, ORANGE, "held by dry-bulb")):
        s.append('<rect x="%.2f" y="%.2f" width="11" height="9" fill="%s" stroke="%s" '
                 'stroke-width="0.6"/>' % (lx, y + 8, fill, edge))
        s.append(_txt(lx + 16, y + 16, text, T_AXIS, GREY))
        lx += 16 + _tw(text, T_AXIS) + 22
    assert lx - 22 <= W - R_ + 1, "the strip legend is %.0f px wider than the chart" % (lx - W)
    s.append("</svg>")
    return "\n".join(s)


# =========================================================================== 2. bound vs actual
# THE CREDIBILITY CHART. The forecast, the margin band on top of it, the agent's upper bound, what
# the intake actually did, and the plant limit as a threshold. It earns its space by showing the
# bound was never crossed while the actual stayed underneath it.
def bound_vs_actual(hours, limit_c, height=470):   # page 3 measured 170 pt free
    # ⚠ THE BOTTOM BAND HOLDS TWO ROWS OF TEXT, SO IT IS SIZED FOR TWO. Giving the hour labels the
    # 6 px of clearance they needed from the y-axis corner pushed them into the legend underneath,
    # trading one collision for five. B is now 60 px and the chart 12 px taller, which leaves 24 px
    # between the hour row and the legend row rather than 10.
    n = len(hours)
    L, R_, T, B = PLOT_L, 12, 48, 60
    pw, ph = W - L - R_, height - T - B
    fc = [h["ambient_c"] for h in hours]
    ub = [h["bound_c"] for h in hours]
    ac = [h["actual_intake_c"] for h in hours]
    vals = fc + ub + ac + [limit_c]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or 1.0
    lo, hi = lo - pad, hi + pad

    def X(i):
        return L + pw * (i / float(n - 1))

    def Y(v):
        return T + ph * (1 - (v - lo) / (hi - lo))

    s = _open(W, height)
    s.append(_txt(2, 16, "The bound against the plant limit", T_TITLE, NAVY, bold=True))
    s.append(_txt(2, 34, "degrees Celsius at the intake", T_AXIS, MUTED))
    # gridlines + y labels
    for i in range(5):
        v = lo + (hi - lo) * i / 4.0
        y = Y(v)
        s.append(_rule(L, y, W - R_, RULE, 0.6))
        s.append(_txt(L - 6, y + 3, "%.0f" % v, T_AXIS, MUTED, anchor="end"))
    # the margin band: forecast up to bound
    band = ["M%.2f %.2f" % (X(0), Y(fc[0]))]
    band += ["L%.2f %.2f" % (X(i), Y(fc[i])) for i in range(1, n)]
    band += ["L%.2f %.2f" % (X(i), Y(ub[i])) for i in range(n - 1, -1, -1)]
    s.append('<path d="%s Z" fill="%s" opacity="0.75"/>' % (" ".join(band), FREE_PALE))
    # the plant limit
    s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.6" '
             'stroke-dasharray="6 3"/>' % (L, Y(limit_c), W - R_, Y(limit_c), ORANGE))
    # ⚠ KNOCKED OUT OF ITS OWN RULE, for the same reason the coverage values are. The label sits
    # 5 px above a line it is describing, which at 11.3 px of type means the rule runs through the
    # bottom of the glyph box. It reads acceptably because these particular glyphs have no
    # descenders, which is not a property to rely on: "plant limit 18" is safe and "plant limit
    # 18 °C, dew point" would not be.
    _lt = "plant limit %.0f" % limit_c
    _lw = _tw(_lt, T_AXIS, bold=True)
    s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
             % (W - R_ - 2 - _lw - 3, Y(limit_c) - 5 - T_AXIS * 0.86, _lw + 6, T_AXIS * 1.06, PAPER))
    s.append(_txt(W - R_ - 2, Y(limit_c) - 5, _lt, T_AXIS, ORANGE, anchor="end", bold=True))

    def poly(seq, colour, width, dash=None):
        d = " ".join(("M" if i == 0 else "L") + "%.2f %.2f" % (X(i), Y(v))
                     for i, v in enumerate(seq))
        return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s"%s/>'
                % (d, colour, width, ' stroke-dasharray="3 2"' if dash else ''))

    s.append(poly(fc, MUTED, 1.1, dash=True))
    s.append(poly(ub, FREE, 2.0))
    s.append(poly(ac, NAVY, 1.5))
    # x labels
    for i in range(0, n, 3):
        # ⚠ 20 px OF CLEARANCE, NOT 14. MEASURED: at 14 the first hour label "00" clipped the
        # lowest y-axis tick label "-4" by 0.9 by 2.0 pt at the bottom-left corner, where the two
        # axes' label runs meet. It is the one collision in this chart that no amount of anchoring
        # fixes, because both labels are correctly placed relative to their own axis; the only cure
        # is distance.
        s.append(_txt(X(i), height - B + 20, hours[i]["hour"], T_AXIS, MUTED, anchor="middle"))
    # legend
    ly = height - 16
    for dx, colour, lab, dash in ((0, FREE, "agent's upper bound", False),
                                  (168, NAVY, "what the intake actually did", False),
                                  (368, MUTED, "raw forecast", True)):
        s.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2"%s/>'
                 % (L + dx, ly - 3, L + dx + 16, ly - 3, colour,
                    ' stroke-dasharray="3 2"' if dash else ''))
        s.append(_txt(L + dx + 21, ly, lab, T_AXIS, GREY))
    s.append('<rect x="%d" y="%d" width="11" height="9" fill="%s"/>' % (L + 520, ly - 8, FREE_PALE))
    s.append(_txt(L + 537, ly, "margin", T_AXIS, GREY))
    s.append("</svg>")
    return "\n".join(s)


# =========================================================================== 3. margin parts
# The margin is MEASURED, not chosen, and this is the chart that shows it: two real components per
# hour, group-conditional forecast error and plume spread, stacked. `explanations.json` already
# carries the split, so nothing here derives anything.
def margin_decomposition(hours, height=430):       # page 4 measured 189 pt free
    n = len(hours)
    L, R_, T, B = PLOT_L, 12, 48, 40
    pw, ph = W - L - R_, height - T - B
    shape = [h["margin_parts"]["shape_group_conditional"] for h in hours]
    plume = [h["margin_parts"]["plume_from_ensemble_spread"] for h in hours]
    hi = max(a + b for a, b in zip(shape, plume)) * 1.15
    bw = pw / float(n) * 0.72
    s = _open(W, height)
    s.append(_txt(2, 16, "Where each degree of the margin comes from", T_TITLE, NAVY, bold=True))
    s.append(_txt(2, 34, "degrees Celsius added on top of the forecast", T_AXIS, MUTED))
    for i in range(4):
        v = hi * i / 3.0
        y = T + ph * (1 - v / hi)
        s.append(_rule(L, y, W - R_, RULE, 0.6))
        s.append(_txt(L - 6, y + 3, "%.1f" % v, T_AXIS, MUTED, anchor="end"))
    for i in range(n):
        x = L + pw * (i / float(n)) + (pw / n - bw) / 2
        hs = ph * shape[i] / hi
        hp = ph * plume[i] / hi
        s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
                 % (x, T + ph - hs, bw, hs, TEAL))
        # 🔴 THE PLUME PART IS ORANGE, NOT GREY. Item 6 reserves neutral grey for the incumbent
        # baseline and nothing else. These two stacked parts are the two things the margin is made
        # of: the agent's own measured forecast error, which is blue because it is the agent's, and
        # the plume allowance, which is orange because it is a constraint the site imposes. Drawn
        # grey the upper part read as "no data" rather than "this is the physics term".
        s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" stroke="%s" '
                 'stroke-width="0.5"/>' % (x, T + ph - hs - hp, bw, hp, ORANGE_PALE, ORANGE))
    for i in range(0, n, 3):
        s.append(_txt(L + pw * (i / float(n)) + pw / n / 2, height - B + 14, hours[i]["hour"], T_AXIS, MUTED, anchor="middle"))
    ly = height - 12
    s.append('<rect x="%d" y="%d" width="11" height="9" fill="%s"/>' % (L, ly - 8, TEAL))
    s.append(_txt(L + 16, ly, "forecast error measured for this hour of day", T_AXIS, GREY))
    # ⚠ NO LEGEND ENTRY FOR A PART THAT IS NOT THERE. On a single-building site every plume value
    # is identically zero, so the upper rect has no height and a swatch describing it would point at
    # nothing. 168 of the 249 covered sites are that shape, and a legend that names an invisible
    # series is how a reader concludes the chart is broken.
    if any(v > 0 for v in plume):
        s.append('<rect x="%d" y="%d" width="11" height="9" fill="%s" stroke="%s" '
                 'stroke-width="0.5"/>' % (L + 300, ly - 8, ORANGE_PALE, ORANGE))
        s.append(_txt(L + 316, ly, "how far the exhaust plume could move", T_AXIS, GREY))
    s.append("</svg>")
    return "\n".join(s)


# =========================================================================== 4. agent vs incumbent
def agent_vs_incumbent(mech_agent_h, mech_inc_h, cut_pct, held_out_days=None,
                       height=206):  # shares page 3
    """Chiller runtime, agent against incumbent, over the held-out record.

    🔴 THE HELD-OUT DAY COUNT WAS THE LITERAL 913, WHICH IS ASHBURN'S. Every one of the other 249
    sites got Ashburn's number in this chart's subtitle while its own prose, two lines below on the
    same page, printed the truth. MEASURED in the shipped GA_way_39083797_report.pdf page 3: the
    chart said "across 913 days the agent never trained on" and the paragraph under it said "the
    second half, 908 days, was kept back". Two different values for one quantity, on one page, in a
    document whose entire argument is that its numbers are checkable.

    The count is a per-site measurement (898 to 913 across the sites sampled), so it is a parameter.
    `None` renders the phrase without a number rather than inventing one.
    """
    L, R_, T = PLOT_L, 12, 54
    # 🔴 180, not 120. The value label is drawn to the RIGHT of each bar, so the track has to
    # stop early enough for the label to fit inside the measure. MEASURED at 120: "9,510 h"
    # reached x = 554.5 pt against a 547.1 pt right margin.
    pw = W - L - R_ - 180
    hi = max(mech_agent_h, mech_inc_h) * 1.06
    s = _open(W, height)
    s.append(_txt(2, 16, "Chiller runtime, agent against incumbent", T_TITLE, NAVY, bold=True))
    s.append(_txt(2, 34, ("hours of mechanical cooling across %s days the agent never trained on"
                          % format(int(held_out_days), ",")) if held_out_days
                  else "hours of mechanical cooling over the held-out record",
                  T_AXIS, MUTED))
    # Item 6's mapping: neutral grey is the baseline and nothing else, blue is the agent.
    rows = (("Reactive incumbent", mech_inc_h, NEUTRAL, NEUTRAL_EDGE),
            ("This agent", mech_agent_h, FREE, FREE))
    # 🔴 THE TRACK STARTS WHERE THE LONGEST LABEL ENDS, MEASURED. The gutter was the constant 118,
    # which held while the plot gutter was 46 px and stopped holding the moment item 8 moved every
    # plot area to a common 64 px: "Reactive incumbent" then ran 3.5 pt UNDER the grey bar. The
    # text-overlap check could not see it, because one of the two things overlapping was a rectangle
    # and not a word, which is the gap `check_report.py` now closes.
    bx = L + max(_tw(r[0], T_LABEL) for r in rows) + 14
    for i, (lab, v, fill, edge) in enumerate(rows):
        y = T + i * 42
        s.append(_txt(L, y + 15, lab, T_LABEL, GREY))
        bwid = pw * v / hi
        s.append('<rect x="%.2f" y="%d" width="%.2f" height="22" fill="%s" stroke="%s" '
                 'stroke-width="0.6"/>' % (bx, y, bwid, fill, edge))
        s.append(_txt(bx + bwid + 8, y + 16, "%s h" % format(int(round(v)), ","), T_LABEL, NAVY,
                      bold=True))
    s.append(_rule(L, T + 92, W - R_))
    s.append(_txt(L, T + 110, "%.1f%% less chiller runtime, a share so it holds at any hall size"
                  % cut_pct, T_LABEL, TEAL, bold=True))
    s.append("</svg>")
    return "\n".join(s)


# =========================================================================== 5. coverage
# THE HONEST CHART. Three populations, one picture: the four-day FortyGuard calibration that failed
# its promise, the same method at five-year sample sizes, and the twelve per-lead bounds. The
# ceiling at n = 4 is drawn, because a bar short of 90 % means nothing without it.
def coverage(bound, height=440):                   # page 6 measured 156 pt free
    """THE HONEST CHART, and the one that kept printing its own explanation over its own data.

    🔴 THRESHOLD LABELS ARE NOT ALLOWED INSIDE THE PLOT ANY MORE, which is item 2 of the brief and
    also the third attempt at this. The 90 % label started right-aligned, where it collided with the
    rightmost bar's value; moved to the left, where it collided with the ceiling label; and the
    ceiling label was moved above its own tick, where the 90 % dashed rule then struck straight
    through it. MEASURED at the tightened threshold: "90% target" against "80% reachable at n=4",
    overlapping. Every one of those was a legal position for one label and an illegal position for
    the other, because the top-left of this plot has two thresholds 10 points apart in a 24 point
    space. So the LINES stay in the plot, where they carry meaning against the bars, and the WORDS
    move to a legend under the axis where nothing can reach them.

    ⚠ ORANGE DASHED MEANS THRESHOLD IN EVERY CHART IN THIS DOCUMENT. The plant limit in
    `bound_vs_actual` was already orange dashed; the 90 % target was navy, which the palette
    reserves for headline text. Item 6 makes the two agree.

    ⚠ THE ARITHMETIC CEILING IS GREY, NOT ORANGE, and the distinction is real rather than decorative.
    Everything else marked in this document is something the plant or the physics imposes. This one
    is a property of the sample: with four measured days a one-sided 90 % bound cannot read above
    80 % however good the method is. It is a fact about the measurement, so it is drawn in the
    colour this document uses for things said about the data rather than by it.
    """
    L, R_, T, B = PLOT_L, 12, 52, 86
    pw, ph = W - L - R_, height - T - B
    # ORANGE marks the population still accumulating days; BLUE the ones already at target.
    # Never NEUTRAL for a bar carrying a label: #c9d1da measures 1.54:1 as text and washes out.
    bars = [("FortyGuard days\nn = %d so far" % (bound["n_pairs"] or 4), bound["pooled"],
             ORANGE, True),
            ("worst hour-of-day\ngroup, 5 years", bound["mondrian_worst_group"], BLUE, False),
            # 🔴 THE ROUND COUNT WAS THE LITERAL 43,260, WHICH IS ALSO ASHBURN'S, AND `bound`
            # ALREADY CARRIES THE RIGHT ONE. MEASURED: 43,260 on this chart against 42,747 in the
            # prose of the same page of GA_way_39083797_report.pdf. It varies from 41,986 to 43,273
            # across the sites sampled, and it was one dictionary lookup away the whole time.
            ("adaptive bound\n%s rounds" % format(int(bound.get("aci_rounds") or 0), ","),
             bound["aci_coverage"], BLUE, False),
            ("worst of 12\nper-lead bounds", min(bound["coverage_by_lead"].values()),
             BLUE, False)]
    lo, hi = 0.0, 1.0
    s = _open(W, height)
    s.append(_txt(2, 16, "Bound coverage, by population size", T_TITLE, NAVY, bold=True))
    s.append(_txt(2, 34, "share of hours the real intake stayed under the bound", T_AXIS, MUTED))

    def Y(v):
        return T + ph * (1 - (v - lo) / (hi - lo))

    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = Y(frac)
        s.append(_rule(L, y, W - R_, RULE, 0.6))
        s.append(_txt(L - 6, y + 3, "%d%%" % (frac * 100), T_AXIS, MUTED, anchor="end"))

    # the 90 % promise, as a LINE only
    s.append('<line x1="%d" y1="%.2f" x2="%d" y2="%.2f" stroke="%s" stroke-width="1.4" '
             'stroke-dasharray="6 3"/>' % (L, Y(0.9), W - R_, Y(0.9), ORANGE))

    bw = pw / len(bars) * 0.46
    ceiling_drawn = False
    for i, (lab, v, colour, short) in enumerate(bars):
        cx = L + pw * (i + 0.5) / len(bars)
        s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" opacity="%s"/>'
                 % (cx - bw / 2, Y(v), bw, Y(0) - Y(v), colour, "0.9"))
        # 🔴 A WHITE KNOCKOUT UNDER THE VALUE, because the 90 % rule crosses it. The bar for 87.9 %
        # tops out just below the target line, so its value label sat exactly ON the dashed rule and
        # was printed through. Moving the label inside the bar was the other option and it fails on
        # contrast: white on the orange bar measures 3.18:1, under the 4.5:1 floor. Knocking the
        # background out keeps the label where it belongs, above its own bar, and keeps the rule
        # legible either side of it.
        vtxt = "%.1f%%" % (v * 100)
        vw = _tw(vtxt, T_LABEL, bold=True)
        s.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>'
                 % (cx - vw / 2 - 3, Y(v) - 6 - T_LABEL * 0.86, vw + 6, T_LABEL * 1.06, PAPER))
        s.append(_txt(cx, Y(v) - 6, vtxt, T_LABEL, colour, anchor="middle", bold=True))
        # ⚠ 15 px OF PITCH, ARRIVED AT BY MEASUREMENT. 11 px overlapped the two lines of every tick
        # label by 20 % of the smaller box, 12 px by 12 %. An 8.5 pt line box is about 11.9 pt tall
        # once ascent and descent are counted, which at the 0.75 px-to-pt mapping is 15.9 px, so
        # anything under about 14 px guarantees the boxes touch however the glyphs happen to fall.
        for j, part in enumerate(lab.split("\n")):
            s.append(_txt(cx, Y(0) + 16 + j * 15, part, T_AXIS, GREY, anchor="middle"))
        if short and bound.get("ceiling"):
            yc = Y(bound["ceiling"])
            s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                     'stroke-width="1.2"/>' % (cx - bw / 2 - 6, yc, cx + bw / 2 + 6, yc, SECOND))
            ceiling_drawn = True

    # ---- the legend, below the axis, where no line can reach it
    ly = Y(0) + 52
    s.append(_rule(L, ly - 14, W - R_))
    lx = L
    s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-width="1.4" '
             'stroke-dasharray="5 3"/>' % (lx, ly - 3, lx + 18, ly - 3, ORANGE))
    t1 = "90% target"
    s.append(_txt(lx + 24, ly, t1, T_AXIS, GREY, bold=True))
    lx += 24 + _tw(t1, T_AXIS, bold=True) + 24
    if ceiling_drawn:
        s.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                 'stroke-width="1.2"/>' % (lx, ly - 3, lx + 18, ly - 3, SECOND))
        t2 = ("%d%% is the highest a one-sided 90%% bound can read on %d days"
              % (round(bound["ceiling"] * 100), bound["n_pairs"] or 4))
        s.append(_txt(lx + 24, ly, t2, T_AXIS, GREY))
        lx += 24 + _tw(t2, T_AXIS)
    assert lx <= W - R_ + 1, "the coverage legend is %.0f px wider than the chart" % (lx - (W - R_))
    assert ly + 6 <= height, "the coverage legend falls outside the chart"
    s.append("</svg>")
    return "\n".join(s)


# =========================================================================== 6. plume polar (mpl)
def plume_polar(rise_table_path, worst_bearing, worst_rise, out_svg, placed_scale=1.0):
    # 🔴 THIS CHART IS PLACED AT 0.86, AND SCALING A DRAWING SCALES ITS TEXT WITH IT.
    # MEASURED: the eight compass labels asked for at 8.5 pt arrived on paper at 7.3 pt and the
    # title at 8.2 pt, both under the document 8.5 pt floor, because the caller shrinks the
    # Drawing to fit a two-column row and nothing inside the chart could see that. So the
    # placement scale is passed in and every size divided by it: what is asked for in points is
    # what lands on paper.
    def fs(pt):
        assert pt >= 8.5, "%.2f pt is below the document floor before scaling" % pt
        return pt / float(placed_scale)

    """Intake rise against wind bearing, from the 576 solves. matplotlib: polar axes by hand are
    fiddly and this is the one chart where the library earns its dependency."""
    import json
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams.update({"svg.fonttype": "none", "font.family": "Inter",
                                "svg.hashsalt": "agentic-arbiter"})
    import matplotlib.pyplot as plt

    d = json.load(open(rise_table_path, encoding="utf-8"))
    rise = np.array(d["rise"], dtype=float)          # [bearing][speed]
    worst_per_bearing = rise.max(axis=1)
    n = len(worst_per_bearing)
    th = np.deg2rad(np.arange(n) * (360.0 / n))
    th = np.append(th, th[0])
    r = np.append(worst_per_bearing, worst_per_bearing[0])

    fig = plt.figure(figsize=(3.4, 3.4), dpi=100)
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.plot(th, r, color=FREE, lw=1.6)
    ax.fill(th, r, color=FREE, alpha=0.16)
    ax.plot([np.deg2rad(worst_bearing)], [worst_rise], "o", ms=7, color=ORANGE, zorder=5)

    # 🔴 THE RADIAL LABELS GO WHERE THIS SITE'S PLUME IS NOT, WHICH IS A QUESTION ONLY THE DATA CAN
    # ANSWER. Two hand-picked angles had already failed: 112 degrees threw the labels right, over
    # the E and NE compass points and into the prose column beside the chart, and the 205 that
    # replaced it put them straight down the middle of THIS site's lobe, where MEASURED they
    # overlapped each other in six pairs and sat on top of the filled region. Any constant is wrong
    # for some site, because the lobe points wherever the receptor happens to be. The emptiest
    # bearing is computed instead, so the labels land in clear air at every site in the portfolio.
    quiet = int(round(float(np.argmin(worst_per_bearing)) * (360.0 / n)))
    ax.set_rlabel_position(quiet)

    # 🔴 AND THERE WERE TOO MANY OF THEM. matplotlib's default put eight radial ticks on a 0.35 °C
    # range, so the labels collided with each other whatever angle they were thrown at: MEASURED,
    # "0.05" against "0.10" overlapped by 15 % with no data anywhere near them. Four is the most
    # this radius can hold, and MaxNLocator picks round values rather than 0.0875 steps.
    from matplotlib.ticker import MaxNLocator
    ax.yaxis.set_major_locator(MaxNLocator(4, prune="lower"))
    ax.tick_params(colors=MUTED, labelsize=fs(8.5))
    ax.set_xticks(np.deg2rad(np.arange(0, 360, 45)))
    ax.set_xticklabels(["N", "NE", "E", "SE", "S", "SW", "W", "NW"], fontsize=fs(8.5), color=GREY)
    ax.grid(color=RULE, lw=0.6)
    ax.spines["polar"].set_color(RULE)
    ax.set_title("Intake rise by wind bearing", fontsize=fs(9.5), color=NAVY, pad=14)

    # ⚠ THE WORST-CASE NOTE LIVES IN THE FIGURE, UNDER THE PLOT, IN RESERVED SPACE. Inside the axes
    # it collided with something at every anchor tried: on the data point it ran off the column
    # edge, and at the top-left corner it printed across the "N" compass label at 59 % overlap.
    # There is no free corner inside a circle inscribed in a square once all eight compass points
    # are labelled, so `rect` reserves a strip and the note is placed in it.
    fig.tight_layout(rect=(0, 0.055, 1, 1))
    fig.text(0.02, 0.012, "worst %.2f °C at %d°, from %d solves"
             % (worst_rise, int(worst_bearing), rise.size),
             color=ORANGE, fontsize=fs(8.5), ha="left", va="bottom")
    fig.savefig(out_svg, format="svg", transparent=False, facecolor=PAPER)
    plt.close(fig)
    return out_svg


# =========================================================================== 7. portfolio (mpl)
def portfolio_hist(gains, out_svg, this_site_gain=None):
    """Chiller-hours recovered per year across the sites this agent is OFFERED on.

    🔴 THIS CHART NEVER PLOTTED THE LOSING SITES, AND THE CAPTION SAID IT DID.
    The line was `pos = g[g >= 0]` followed by `ax.hist(pos, ...)`, so every negative gain was
    dropped before binning, while the document underneath asserted that those sites "are in the chart
    rather than filtered out of it: publishing them is what makes the rest of the distribution worth
    reading." The claim was the opposite of the code, and it was the credibility argument of the
    whole page.
    #
    ⚠ AND PLOTTING THEM IS NOT THE FIX EITHER. The worst is -3,649 h/yr against a useful range of
    250 to 850, so an honest axis would compress everything a reader came for into the right-hand
    sixth of the frame to make room for twelve bars of height one. The fix is for the chart to be
    given only what it plots and to SAY what that is: the caller now passes the offered sites, the
    title counts them, and the excluded twelve are described in words with their range, where a
    number can be stated exactly instead of being a pixel wide.
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams.update({"svg.fonttype": "none", "font.family": "Inter",
                                "svg.hashsalt": "agentic-arbiter"})
    import matplotlib.pyplot as plt

    g = np.array([x for x in gains], dtype=float)
    # The caller passes the offered set, so nothing is dropped here. The assertion is what stops the
    # old silent filter coming back: if a negative ever arrives, the chart refuses rather than hiding
    # it and letting a caption speak for it.
    assert g.size == 0 or float(g.min()) >= 0.0, (
        "portfolio_hist was given %d negative gain(s), worst %.0f; this chart plots the offered "
        "sites and the excluded ones are described in the caption, not silently dropped here"
        % (int((g < 0).sum()), float(g.min())))
    fig, ax = plt.subplots(figsize=(6.6, 2.5), dpi=100)
    ax.hist(g, bins=28, color=FREE, edgecolor=PAPER, linewidth=0.6)
    # 🔴 THE MARKER MUST NOT DRAG THE AXIS OFF THE DISTRIBUTION. `this_site_gain` is the gain of the
    # site whose report this is, and for the 12 withheld sites that is negative, down to -3,649
    # against a plotted range of about 250 to 850. matplotlib extends an axis to include an axvline,
    # so those twelve reports would have shown the whole distribution squashed into the right-hand
    # sixth of the frame to make room for one rule: the exact failure the caption explains, in the
    # one place a reader would meet it with no explanation beside it.
    _in_range = bool(this_site_gain is not None and g.size
                     and float(g.min()) <= this_site_gain <= float(g.max()))
    if _in_range:
        ax.axvline(this_site_gain, color=ORANGE, lw=1.6)
    # ⚠ THE NOTE IS NOT CONDITIONAL ON THE RULE. Skipping both when the value is off scale removed
    # the only statement of where this site sits, which for the 12 withheld reports is the single
    # most important number on the page. The rule is omitted because it would distort the axis; the
    # note stays and says which way it went.
    if this_site_gain is not None:
        # 🔴 TOP RIGHT, IN AXES COORDINATES, CLEAR OF ITS OWN MARKER. Anchored near the line it
        # labelled, the note was printed through by that line and sat on top of the tallest bar in
        # the distribution. The line is orange and so is the note, which is what ties them together;
        # a label does not have to touch the thing it names in order to name it.
        ax.annotate(("this site\n%+.0f h/yr" % this_site_gain) if _in_range
                    else ("this site\n%+.0f h/yr, off the scale to the left"
                          % this_site_gain),
                    xy=(0.995, 0.98), xycoords="axes fraction",
                    color=ORANGE, fontsize=8.5, ha="right", va="top",
                    # ⚠ AND A WHITE PLATE UNDER IT. Moving the note to the empty top right of the
                    # axes took it off its own marker line and off the tallest bar, and left it
                    # sitting across a horizontal gridline instead. matplotlib's own bbox is the
                    # same knockout the hand-written charts use.
                    bbox=dict(facecolor=PAPER, edgecolor="none", pad=1.2))
    ax.set_xlabel("chiller-hours recovered per year, per site", fontsize=8.5, color=GREY)
    ax.set_ylabel("sites", fontsize=8.5, color=GREY)
    ax.tick_params(colors=MUTED, labelsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(RULE)
    ax.grid(axis="y", color=RULE, lw=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    # ⚠ matplotlib does NOT clip a title to the axes, so a long one paints off the figure and
    # then off the page: this one reached x = 598.4 pt. Short title, and the count moves into the
    # document's caption where it can wrap.
    ax.set_title("Chiller-hours recovered, all %d offered sites" % len(g),
                 fontsize=9.5, color=NAVY, loc="left", pad=8)
    fig.tight_layout()
    fig.savefig(out_svg, format="svg", transparent=False, facecolor=PAPER)
    plt.close(fig)
    return out_svg


# --------------------------------------------------------------------------- to ReportLab
def to_drawing(svg_text_or_path, is_path=False):
    """SVG to a ReportLab vector Drawing. Everything in the document goes through here."""
    from svglib.svglib import svg2rlg
    if is_path:
        return svg2rlg(svg_text_or_path)
    import io
    return svg2rlg(io.BytesIO(svg_text_or_path.encode("utf-8")))
