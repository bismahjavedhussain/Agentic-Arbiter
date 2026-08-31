# -*- coding: utf-8 -*-
"""THE SITE, ON ITS OWN SATELLITE IMAGERY, WITH THE SOLVER'S ACTUAL GEOMETRY DRAWN ON TOP.

The report's strongest single addition: it makes the analysis a real place rather than a table. The
frame is the site's own screening image, the outlines are the two OpenStreetMap ways the plume solver
runs on, and the short segment between them is the 60.3 m facade gap the hot air crosses.

🔴 ONE TRANSFORM FOR BOTH BUILDINGS, ANCHORED AT THE DOMAIN CENTRE. The first version of this module
registered each footprint separately, by its own `centre_latlon`, on the theory that this cancels
projection error per building. MEASURED, that was wrong twice over:

  - The error it was correcting is 0.35 m, not the 3 to 4 m assumed. The solver's domain centre
    (1000, 1000) maps to `site.centre` exactly, and from that single anchor both building centres
    land within 0.35 m of their own recorded `centre_latlon`. That is one and a half pixels.
  - Registering the two rings independently CORRUPTS THE ONE DISTANCE THE FIGURE IS ABOUT. Nudging
    each ring onto its own anchor changes the separation between them, so the segment drawn as the
    facade gap would no longer be 60.3 m. A per-building fit buys a fraction of a pixel of absolute
    accuracy by falsifying the relative geometry. One transform keeps the gap exact.

🔴 THE GAP SEGMENT IS RECOMPUTED HERE AND ASSERTED AGAINST THE TRACE. `facade_gap_m` is
facade-to-facade (`audit.py` line 2289: "facade-to-facade gap 60.3 m"), NOT centre-to-centre, which
is 165.5 m. An earlier draft drew the centre-to-centre line and would have labelled it 60.3 m: a
figure contradicting its own picture. `_gap()` finds the closest approach between the two rings by
segment-to-segment search and refuses to draw unless it reproduces the artefact's number.

⚠ THE OUTLINES ARE OSM WAYS ON AN INDEPENDENTLY GEOREFERENCED BASEMAP, AND THE CAPTION SAYS SO.
MEASURED by edge-gradient search, one edge of each ring sits 10 to 20 m off the roofline in this
frame, the two disagreeing in OPPOSITE directions, so it is neither this projection nor camera
parallax: OSM's geometry and ESRI's imagery are surveyed independently. Every distance in the
analysis comes from the OSM rings, self-consistently, so this changes no number in the report. It
does mean the picture is evidence about WHERE, and the caption must not imply survey registration.

⚠ RESAMPLED TO SQUARE GROUND PIXELS. The frame covers 318.7 m by 321.1 m of ground in a 1400x1050
raster, so a source pixel is 0.2276 m across and 0.3058 m down: a 34% vertical squash that makes a
158 m hall look 118 m long and a scale bar valid on only one axis. The composite is built on an
isotropic canvas, so shapes are true and the bar measures in both directions.

⚠ THE FRAME IS EVIDENCE ABOUT WHERE, NEVER ABOUT WHAT. `sites.json` records the resolution note
verbatim and the caption carries it: 0.3 to 0.5 m shows objects, not nameplates. It cannot certify a
unit type or measure a height, and the report says so next to the picture rather than in a footnote.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

M_PER_DEG_LAT = 110540.0
DOMAIN_CENTRE = 1000.0          # the solver's 2000 m domain is centred on site.centre

# Item 6's semantic mapping, applied to a photograph. Orange is the constraint, so it marks the heat
# and where it comes from; blue is what the bound defends, so it marks the hall being protected and
# the intake itself. That also happens to read the intuitive way round: hot is orange, cool is blue.
ORANGE = (194, 82, 31)
BLUE = (31, 95, 174)
WHITE = (255, 255, 255)


def _mpdl(lat):
    return math.cos(math.radians(lat)) * 111320.0


def _gap(ring_a, ring_b):
    """Closest approach between two rings, as (metres, point_on_a, point_on_b).

    Facade to facade means ring to ring, which means every edge of one against every edge of the
    other. Vertex-to-vertex would overstate the gap wherever the closest approach falls part way
    along a wall, which is exactly what happens here.
    """
    def pt_seg(p, a, b):
        ax, ay = a
        dx, dy = b[0] - ax, b[1] - ay
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        q = (ax + u * dx, ay + u * dy)
        return math.hypot(p[0] - q[0], p[1] - q[1]), p, q

    best = (float("inf"), None, None)
    for i in range(len(ring_a) - 1):
        for j in range(len(ring_b) - 1):
            cands = [pt_seg(ring_a[i], ring_b[j], ring_b[j + 1]),
                     pt_seg(ring_a[i + 1], ring_b[j], ring_b[j + 1])]
            for d, p, q in (pt_seg(ring_b[j], ring_a[i], ring_a[i + 1]),
                            pt_seg(ring_b[j + 1], ring_a[i], ring_a[i + 1])):
                cands.append((d, q, p))          # keep the ordering (on A, on B)
            for c in cands:
                if c[0] < best[0]:
                    best = c
    return best


def _font(px):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(os.path.join(HERE, "reportassets", "Inter-SemiBold.ttf"), px)
    except Exception:                                                     # noqa: BLE001
        return None


def _plate(dr, xy, text, font, fg=WHITE, pad=8):
    """Text on a dark plate. Satellite imagery has no reliable background, so every label carries
    its own; white-with-a-thin-outline is unreadable over both a pale roof and bright concrete."""
    x, y = xy
    if font is not None:
        l, t, r, b = dr.textbbox((x, y), text, font=font)
    else:
        l, t, r, b = x, y, x + 7 * len(text), y + 12
    dr.rectangle([l - pad, t - pad + 1, r + pad, b + pad - 1], fill=(17, 24, 34, 205))
    dr.text((x, y), text, fill=fg, font=font)
    return (r - l) + 2 * pad


def _dashed_circle(dr, cx, cy, rr, colour, width, dash_deg=9):
    for a in range(0, 360, dash_deg * 2):
        dr.arc([cx - rr, cy - rr, cx + rr, cy + rr], a, a + dash_deg, fill=colour, width=width)


def build(site_key, imagery, site, out_path, placed_pt=252.0, dpi=300):
    """Composite the frame plus the solver's geometry. Returns (path, meta) or (None, reason).

    🔴 EVERY SIZE IN HERE IS DERIVED FROM `placed_pt`, BECAUSE THE FIRST VERSION WAS NOT.
    It rendered a fixed 1400 px frame and sized its type as a fraction of that raster: the legend at
    H/60 came out around 23 px. Placed 252 pt wide in the document that is a scale of 0.18 pt per
    pixel, so the legend printed at FOUR POINTS and the scale bar with it. Every label was correct,
    present, and too small to read, which is the same as absent.

    So the raster is now built at exactly the resolution the placement needs, and label sizes are
    stated in POINTS and converted once. A label asked for at 7.5 pt is 7.5 pt on paper whatever the
    frame or the placement, and the file shrinks as a side effect: 1050 px at 300 dpi rather than
    1400 px of detail no printer will resolve at this size.
    """
    from PIL import Image, ImageDraw

    srcs = (imagery or {}).get("sources") or {}
    fname = srcs.get("esri") or srcs.get("usgs")
    if not fname:
        return None, "this site has no screening frame in sites.json"
    img_path = os.path.join(HERE, "..", "demo", fname)
    if not os.path.exists(img_path):
        return None, "%s is listed in sites.json but not present" % fname
    bbox = imagery.get("bbox")
    if not bbox or len(bbox) != 4:
        return None, "the frame has no lat/lon bbox, so nothing can be registered onto it"
    geom = ((site.get("geometry") or {}).get("longest")) or {}
    if not geom.get("source_ring_m"):
        return None, "the trace carries no solver geometry for this site"

    lon_min, lat_min, lon_max, lat_max = bbox
    im = Image.open(img_path).convert("RGB")
    W0, H0 = im.size

    # ---- isotropic canvas: one metre is one number of pixels in both directions
    span_x = (lon_max - lon_min) * _mpdl((lat_min + lat_max) / 2.0)
    span_y = (lat_max - lat_min) * M_PER_DEG_LAT
    W = int(round(placed_pt / 72.0 * dpi))
    PT = placed_pt / float(W)              # points on paper per pixel of this raster
    m_per_px = span_x / float(W)
    H = int(round(span_y / m_per_px))
    im = im.resize((W, H), Image.LANCZOS)

    cll = site["centre"]
    kx, ky = _mpdl(cll[0]), M_PER_DEG_LAT

    def px(x, y):
        """solver-domain metres -> pixels, through the one anchored transform"""
        lat = cll[0] + (y - DOMAIN_CENTRE) / ky
        lon = cll[1] + (x - DOMAIN_CENTRE) / kx
        return ((lon - lon_min) / (lon_max - lon_min) * W,
                (lat_max - lat) / (lat_max - lat_min) * H)

    # 🔴 MOST SITES HAVE ONE BUILDING, NOT TWO. `build_standalone_site.py` writes
    # `receptor_ring_m: null` and `intake_m: null` for a facility with no mapped neighbour, and 168
    # of the 249 covered sites are that shape. Reading the key directly raised a TypeError on every
    # one of them, so this module had only ever run on the 81 paired sites.
    src_ring = geom["source_ring_m"]
    rec_ring = geom.get("receptor_ring_m")
    solo = not rec_ring
    dr = ImageDraw.Draw(im, "RGBA")
    lw = max(2, int(round(0.9 / PT)))      # ~0.9 pt of ink on paper, whatever the raster

    def ring(pts_m, colour, fill_alpha=0, dashed=False):
        """🔴 SOLID MEANS MAPPED, DASHED MEANS MODELLED, and nothing here breaks that rule.

        The first version of this figure filled the condenser bank solid orange, giving it more
        visual weight than anything else in the frame. But `build_site.py` records its position as
        "strip inside the source hall on the facade facing the receptor; NOT mapped in OSM.
        Conservative worst case", and prints it as [ASSUMED]. The same is true of the intake. Drawing
        an assumption as the boldest object in a photograph is the picture-shaped version of an
        unverified claim, so the two modelled shapes are dashed and the legend says which is which.
        """
        p = [px(a, b) for a, b in pts_m]
        if fill_alpha:
            dr.polygon(p, fill=colour + (fill_alpha,))
        segs = list(zip(p, p[1:] + [p[0]]))
        if not dashed:
            dr.line(p + [p[0]], fill=(0, 0, 0, 120), width=lw + 4, joint="curve")
            dr.line(p + [p[0]], fill=colour + (255,), width=lw, joint="curve")
            return
        for (x1, y1), (x2, y2) in segs:
            L = math.hypot(x2 - x1, y2 - y1)
            n = max(int(L / (lw * 6)), 1)
            for k in range(0, n, 2):
                f0, f1 = k / float(n), min((k + 1) / float(n), 1.0)
                a_ = (x1 + (x2 - x1) * f0, y1 + (y2 - y1) * f0)
                b_ = (x1 + (x2 - x1) * f1, y1 + (y2 - y1) * f1)
                dr.line([a_, b_], fill=(0, 0, 0, 120), width=lw + 4)
                dr.line([a_, b_], fill=colour + (255,), width=lw)

    # ⚠ A LONE BUILDING IS BLUE, NOT ORANGE, AND THE DISTINCTION IS THE POINT. On a paired site
    # orange marks the hall the heat LEAVES and blue the hall the bound protects. Where there is only
    # one building there is no neighbour to receive anything, so it is purely the thing being
    # protected; painting it orange would imply heat aimed at something that is not there.
    ring(src_ring, BLUE if solo else ORANGE)
    if not solo:
        ring(rec_ring, BLUE)                                 # the hall the bound protects: mapped
    n_modelled = 0
    if geom.get("bank_ring_m"):
        # The condenser bank: 26 cells over 130 m of facade. Modelled, so dashed and lightly filled.
        ring(geom["bank_ring_m"], ORANGE, fill_alpha=90, dashed=True)
        n_modelled += 1

    # ---- the air intake being protected. Also modelled: a standoff off the facing facade.
    if geom.get("intake_m") and geom.get("intake_radius_m"):
        ix, iy = px(*geom["intake_m"])
        rr = geom["intake_radius_m"] / m_per_px
        _dashed_circle(dr, ix, iy, rr, (0, 0, 0, 130), lw + 3)
        _dashed_circle(dr, ix, iy, rr, BLUE + (255,), lw)
        n_modelled += 1

    # ---- the facade gap: recomputed, checked against the artefact, then drawn
    meta = {"source": "ESRI World Imagery" if srcs.get("esri") else "USGS The National Map",
            "resolution_note": imagery.get("resolution_note"),
            "operator": site.get("operator")}
    meta["standalone"] = solo
    # Stated in points, converted once. Nothing here scales with the raster.
    f_lab = _font(int(round(8.5 / PT)))
    f_leg = _font(int(round(7.2 / PT)))
    if solo:
        # ⚠ NO SECOND FACADE MEANS NOTHING TO MEASURE BETWEEN. `_gap` needs two rings, the trace
        # records `facade_gap_m: null`, and there is no honest number to print here, so the segment
        # and its label are both absent rather than zero. A "0.0 m" gap would read as two buildings
        # touching.
        meta["gap_m"] = None
        meta["gap_matches_trace"] = False
    else:
        gap_m, pa, pb = _gap(src_ring, rec_ring)
        stated = site.get("facade_gap_m")
        if stated is not None:
            assert abs(gap_m - float(stated)) < 0.05, (
                "the drawn facade gap is %.2f m but the trace states %s m; the picture and the "
                "number would contradict each other" % (gap_m, stated))
        a, b = px(*pa), px(*pb)
        dr.line([a, b], fill=(0, 0, 0, 150), width=lw + 4)
        dr.line([a, b], fill=WHITE + (255,), width=lw)
        for q in (a, b):                                      # end caps, so it reads as a measure
            dr.ellipse([q[0] - lw * 1.6, q[1] - lw * 1.6, q[0] + lw * 1.6, q[1] + lw * 1.6],
                       fill=WHITE + (255,))
        meta["gap_m"] = round(gap_m, 1)
        meta["gap_matches_trace"] = stated is not None
        # ⚠ THE LABEL SITS ABOVE THE SEGMENT, NOT ON IT. Centred on the midpoint, the plate covered
        # the right-hand half of the very measure it was labelling, so the 60.3 m line looked about
        # 30 m long. Just the figure: the prose and the caption beside the picture already say what
        # the measure is, and end caps on a line are unambiguous.
        _plate(dr, ((a[0] + b[0]) / 2 - 16.0 / PT, (a[1] + b[1]) / 2 - 15.0 / PT),
               "%.1f m" % gap_m, f_lab)

    # ---- legend. A standalone figure has to be readable without the caption.
    ops = [o.strip() for o in (site.get("operator") or "").split("/")] or ["", ""]

    def short(s):
        w = [t for t in s.split() if t.upper() == t and any(c.isdigit() for c in t)]
        return w[-1] if w else s
    if solo:
        rows = [(BLUE, False, "%s  the only mapped building at this site"
                 % short(ops[0] if ops else "this facility"))]
        if n_modelled:
            rows.append((None, True, "dashed: condenser bank, modelled placement"))
    else:
        rows = [(ORANGE, False, "%s  the hall the heat leaves"
                 % short(ops[0] if ops else "source")),
                (BLUE, False, "%s  the hall the bound protects"
                 % short(ops[1] if len(ops) > 1 else "receptor"))]
        if n_modelled:
            rows.append((None, True, "dashed: condenser bank and air intake, modelled placement"))
    h = int(round(6.6 / PT))               # the swatch, matched to the legend cap height
    x, y = int(W * 0.028), int(H * 0.030)
    # one plate behind the whole legend, sized to the widest row, so the rows cannot look ragged
    wid = max((dr.textlength(t, font=f_leg) if f_leg else 7 * len(t)) for _, _, t in rows)
    pitch = h + int(round(4.4 / PT))
    dr.rectangle([x - 10, y - 9, x + h + 12 + wid + 10, y + pitch * len(rows) - 7],
                 fill=(17, 24, 34, 205))
    for colour, dashed, text in rows:
        if dashed:
            for k in range(0, h + 2, 6):                       # a dashed swatch for the dashed rule
                dr.line([(x + k, y + h / 2), (x + min(k + 3, h), y + h / 2)],
                        fill=WHITE, width=max(2, lw - 1))
        else:
            dr.rectangle([x, y + 2, x + h, y + h - 2], fill=colour + (255,))
        dr.text((x + h + 12, y - 1), text, fill=WHITE, font=f_leg)
        y += h + int(round(4.4 / PT))
    meta["n_modelled_shapes"] = n_modelled
    meta["label_pt"] = round(7.2, 1)

    # ---- scale bar. Valid in both directions now that the canvas is isotropic.
    for cand in (200, 150, 100, 50, 25):
        if cand / m_per_px < W * 0.30:
            bar_m = cand
            break
    else:
        bar_m = 50
    bar_px = bar_m / m_per_px
    x0, y0 = int(W * 0.035), int(H * 0.952)
    cap = int(round(9.0 / PT))
    dr.rectangle([x0 - 12, y0 - cap, x0 + bar_px + 16, y0 + int(round(4.0 / PT))],
                 fill=(17, 24, 34, 200))
    dr.line([(x0, y0), (x0 + bar_px, y0)], fill=WHITE, width=max(3, lw))
    for xx in (x0, x0 + bar_px):
        tick = int(round(2.4 / PT))
        dr.line([(xx, y0 - tick), (xx, y0 + tick)], fill=WHITE, width=max(3, lw))
    dr.text((x0, y0 - cap + 2), "%d m" % bar_m, fill=WHITE, font=f_leg)
    meta["scale_bar_m"] = bar_m
    meta["m_per_px"] = round(m_per_px, 4)

    # JPEG: this is a photograph and the whole document has to stay small. q88 on a 1400 px frame
    # lands near 300 KB against the 2.4 MB source PNG.
    im.save(out_path, "JPEG", quality=86, optimize=True, progressive=True)
    meta["bytes"] = os.path.getsize(out_path)
    meta["px"] = im.size
    meta["placed_pt"] = placed_pt
    meta["effective_dpi"] = round(W / (placed_pt / 72.0))
    return out_path, meta


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import metros as M
    key = sys.argv[1] if len(sys.argv) > 1 else M.DEFAULT_METRO
    sj = json.load(open(M.demo_path("sites.json"), encoding="utf-8"))
    s = [x for x in sj["sites"] if x["key"] == key][0]
    t = json.load(open(M.demo_path("trace.json", key), encoding="utf-8"))
    out = os.path.join(HERE, "reportassets", "_aerial_%s.jpg" % key)
    p, meta = build(key, s.get("imagery"), t["site"], out,
                    placed_pt=float(sys.argv[2]) if len(sys.argv) > 2 else 252.0)
    if not p:
        print("   [no frame] %s" % meta)
    else:
        for k, v in meta.items():
            print("   %-18s %s" % (k, v))
