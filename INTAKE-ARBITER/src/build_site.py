# -*- coding: utf-8 -*-
"""Build a solver Site from the REAL Ashburn footprints. FREE, no credential.

WHY A POLYGON RASTERISER IS NEEDED AT ALL
    solver.Site.add_building(cx, cy, w, h) places AXIS-ALIGNED rectangles. The real halls are rotated:
    measured minimum-area rectangles are 190 x 62 m at 52.9 deg and 158 x 62 m at 154.0 deg, and their
    axis-aligned bounding boxes fill only 0.38 and 0.46 of themselves. Placing bbox rectangles at the
    real 141 m centre separation makes the two buildings INTERPENETRATE by 28 m -- physically nonsense.
    So the real polygon rings are rasterised instead.

VERIFICATION, because this is new code touching the physics
    Three checks run before any site is written, and the script REFUSES to write if any fails:
      V1  a rasterised axis-aligned rectangle must agree with solver.add_building to within one
          perimeter cell layer (the two use different edge conventions, so exact equality is not
          expected and is not claimed)
      V2  each rasterised footprint's cell area must match the analytic polygon area to within one
          perimeter cell layer
      V3  the two rasterised buildings must not share a single cell
    A rasteriser that silently mis-places a building would corrupt every number downstream, so it is
    checked rather than trusted.

ASSUMPTIONS, all recorded in the output file and in PLAN.md
    * Condenser bank position and size: NOT mapped in OSM. Placed as a strip inside the source hall
      along the facade facing the receptor -- the physically conservative worst case.
    * Intake position: likewise assumed, on the receptor facade facing the source.
    * discharge_k and exchange_s keep their CALIBRATED values, so the source STRENGTH per unit area is
      unchanged from the validated reference. Total heat release therefore follows the real footprint,
      which is correct: a differently sized facility releases a different amount of heat.
    * Building height is absent from OSM and plays no part in this 2-D solver -- see the section-view
      caveat in docs/GEOMETRY-AND-PHYSICS.md about the 2 m measurement height.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from physics import solver                                        # noqa: E402
from physics.solver import CALIBRATED                             # noqa: E402

# METRO-AWARE; ashburn keeps both original filenames so the audited chain is untouched.
sys.path.insert(0, HERE)
import metros as _M                                                        # noqa: E402
SITE_JSON = _M.geom_path("selected_site.json")
OUT = _M.geom_path("solver_site_%s.json" % os.environ.get("BANK_MODE", "longest").lower())

SIZE_M = 2000.0            # same domain as every validated prior result
DX = 10.0                  # same grid spacing
BANK_FACADE_FRACTION = 0.80    # bank spans this much of the facing facade   [ASSUMED]
BANK_DEPTH_M = 20.0            # how far the bank extends into the hall      [ASSUMED]
INTAKE_STANDOFF_M = 20.0       # intake sits this far outside the receptor facade [ASSUMED]
INTAKE_RADIUS_M = 30.0         # averaging disc, same as all prior work


# ----------------------------------------------------------------- rasteriser
def point_in_ring(px, py, ring):
    """Even-odd ray casting. ring is a closed or open list of (x, y)."""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            xint = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
            if px < xint:
                inside = not inside
    return inside


def rasterise(ring, n, dx):
    """Boolean mask of cells whose CENTRE lies inside the ring."""
    mask = np.zeros((n, n), dtype=bool)
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    j0 = max(0, int(min(xs) / dx) - 1)
    j1 = min(n, int(max(xs) / dx) + 2)
    i0 = max(0, int(min(ys) / dx) - 1)
    i1 = min(n, int(max(ys) / dx) + 2)
    for i in range(i0, i1):
        py = (i + 0.5) * dx
        for j in range(j0, j1):
            px = (j + 0.5) * dx
            if point_in_ring(px, py, ring):
                mask[i, j] = True
    return mask


def poly_area(ring):
    a = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def perimeter(ring):
    p = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        p += math.hypot(x2 - x1, y2 - y1)
    return p


# ----------------------------------------------------------------- verification
def verify(rings, n, dx):
    ok = True
    print("\n   VERIFICATION -- refusing to write the site if any check fails")

    # V1: a rasterised axis-aligned rectangle vs solver.add_building
    cx, cy, w, h = 1000.0, 1000.0, 200.0, 120.0
    rect = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    mine = rasterise(rect, n, dx)
    s = solver.Site(SIZE_M, dx)
    s.add_building(cx, cy, w, h)
    theirs = s.obstacle
    diff = int(np.logical_xor(mine, theirs).sum())
    layer = int((perimeter(rect) / dx) + 4)
    v1 = diff <= layer
    ok &= v1
    print("      V1 rasteriser vs add_building : %s  (%d cells differ, one perimeter layer = %d)"
          % ("PASS" if v1 else "FAIL", diff, layer))

    # V2: rasterised area vs analytic area, per footprint
    for name, ring in rings.items():
        m = rasterise(ring, n, dx)
        cells = int(m.sum())
        a_ras = cells * dx * dx
        a_true = poly_area(ring)
        tol = perimeter(ring) * dx          # one cell layer around the boundary
        v2 = abs(a_ras - a_true) <= tol
        ok &= v2
        print("      V2 %-9s area           : %s  (raster %.0f m2 vs analytic %.0f m2, tol %.0f)"
              % (name, "PASS" if v2 else "FAIL", a_ras, a_true, tol))

    # V3: the two buildings must not share a cell
    ms = [rasterise(r, n, dx) for r in rings.values()]
    overlap = int(np.logical_and(ms[0], ms[1]).sum())
    v3 = overlap == 0
    ok &= v3
    print("      V3 no shared cells            : %s  (%d cells overlap)"
          % ("PASS" if v3 else "FAIL", overlap))
    return ok


# ----------------------------------------------------------------- placement
def facing_edge(ring, centroid, toward):
    """The EDGE whose midpoint lies furthest along `toward` -- i.e. the facade facing that way.

    BUG FIXED 2026-08-16: this previously returned the furthest VERTEX. A vertex of a rotated
    building is a CORNER, so a 152 m bank strip centred on it extended outside the hall and toward
    the receptor, and solver.assert_intake_clear correctly refused the site (4 % of the intake disc
    landed on source cells). Facades are edges, not corners.

    Returns (midpoint, unit_direction_along_edge, edge_length).
    """
    ux, uy = toward
    cx, cy = centroid
    best = None
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        score = (mx - cx) * ux + (my - cy) * uy
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6:
            continue
        if best is None or score > best[0]:
            best = (score, (mx, my), ((x2 - x1) / L, (y2 - y1) / L), L)
    return best[1], best[2], best[3]



def longest_edge(ring, centroid):
    """The LONGEST edge, and the outward direction from the centroid across it.

    Physically, a condenser row sits along a LONG facade (or on the roof) -- not on a narrow end
    wall. At the selected pair the source's receptor-facing facade is only 37 m long, because the
    receptor lies off the END of a 190 m hall, so the facing-facade rule produces a 600 m2 bank
    against the validated reference's 7,200 m2. Both placements are therefore built and swept, and
    the RANGE is reported rather than one of them being chosen.

    Returns (midpoint, unit_direction_along_edge, edge_length, outward_unit_normal).
    """
    cx, cy = centroid
    best = None
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6:
            continue
        if best is None or L > best[0]:
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            nx, ny = -uy, ux
            if (mx - cx) * nx + (my - cy) * ny < 0:      # make the normal point OUTWARD
                nx, ny = -nx, -ny
            best = (L, (mx, my), (ux, uy), (nx, ny))
    return best[1], best[2], best[0], best[3]


def seg_seg_distance(p, q, r, t):
    """True distance between segments pq and rt -- NOT vertex-to-vertex, which overstates the gap."""
    def pt_seg(a, b, c):
        ax, ay = a
        bx, by = b
        cx, cy = c
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0.0:
            return math.hypot(cx - ax, cy - ay)
        u = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / L2))
        return math.hypot(cx - (ax + u * dx), cy - (ay + u * dy))
    return min(pt_seg(p, q, r), pt_seg(p, q, t), pt_seg(r, t, p), pt_seg(r, t, q))


def ring_gap(ringA, ringB):
    """Minimum edge-to-edge distance between two closed rings."""
    best = float("inf")
    for i in range(len(ringA)):
        p, q = ringA[i], ringA[(i + 1) % len(ringA)]
        for j in range(len(ringB)):
            r, t = ringB[j], ringB[(j + 1) % len(ringB)]
            best = min(best, seg_seg_distance(p, q, r, t))
    return best


def strip_ring(centre, along, length, depth):
    """A rectangle centred at `centre`, `length` along the unit vector `along`, `depth` across it."""
    ax, ay = along
    px, py = -ay, ax
    cx, cy = centre
    hl, hd = length / 2.0, depth / 2.0
    return [(cx + ax * hl + px * hd, cy + ay * hl + py * hd),
            (cx + ax * hl - px * hd, cy + ay * hl - py * hd),
            (cx - ax * hl - px * hd, cy - ay * hl - py * hd),
            (cx - ax * hl + px * hd, cy - ay * hl + py * hd)]


def ascii_map(site, intake, step=4):
    """Coarse text picture so the geometry can be EYEBALLED, not just trusted."""
    n = site.n
    rows = []
    for i in range(n - 1, -1, -step):
        line = []
        for j in range(0, n, step):
            blk_o = site.obstacle[max(0, i - step + 1):i + 1, j:j + step]
            blk_s = site.source[max(0, i - step + 1):i + 1, j:j + step]
            if blk_s.any():
                line.append("C")
            elif blk_o.any():
                line.append("#")
            else:
                line.append(".")
        rows.append("".join(line))
    ix, iy = intake
    ii = int((n - 1 - int(iy / site.dx)) / step)
    jj = int(int(ix / site.dx) / step)
    if 0 <= ii < len(rows) and 0 <= jj < len(rows[0]):
        r = list(rows[ii])
        r[jj] = "I"
        rows[ii] = "".join(r)
    return rows


def main():
    print("=" * 78)
    print("INTAKE-ARBITER  building the solver site from REAL footprints   [FREE]")
    print("=" * 78)

    s = json.load(open(SITE_JSON, encoding="utf-8"))
    A, B = s["source_building"], s["receptor_building"]
    n = int(SIZE_M / DX)

    # centre the pair in the domain
    ax, ay = A["centre_m"]
    bx, by = B["centre_m"]
    mid = ((ax + bx) / 2.0, (ay + by) / 2.0)
    shift = (SIZE_M / 2.0 - mid[0], SIZE_M / 2.0 - mid[1])
    ringA = [(x + shift[0], y + shift[1]) for x, y in A["ring_m"]]
    ringB = [(x + shift[0], y + shift[1]) for x, y in B["ring_m"]]
    cA = (ax + shift[0], ay + shift[1])
    cB = (bx + shift[0], by + shift[1])

    print("\n   source   %s  %s" % (A["osm_id"], A["name"] or A["operator"]))
    print("            rotated rect %.0f x %.0f m at %.1f deg, area %.0f m2"
          % (A["rot_rect_long_m"], A["rot_rect_short_m"], A["rot_rect_angle_deg"], A["area_m2"]))
    print("   receptor %s  %s" % (B["osm_id"], B["name"] or B["operator"]))
    print("            rotated rect %.0f x %.0f m at %.1f deg, area %.0f m2"
          % (B["rot_rect_long_m"], B["rot_rect_short_m"], B["rot_rect_angle_deg"], B["area_m2"]))

    if not verify({"source": ringA, "receptor": ringB}, n, DX):
        print("\n   *** VERIFICATION FAILED. Site NOT written. Fix the rasteriser first.")
        return 2

    # unit vector source -> receptor
    d = math.hypot(cB[0] - cA[0], cB[1] - cA[1])
    u = ((cB[0] - cA[0]) / d, (cB[1] - cA[1]) / d)
    perp = (-u[1], u[0])

    # condenser bank -- TWO defensible placements, both built, neither chosen for us
    mode = os.environ.get("BANK_MODE", "longest").lower()
    if mode == "facing":
        mid_a, along_a, len_a = facing_edge(ringA, cA, u)
        inward = (-u[0], -u[1])
    else:
        mid_a, along_a, len_a, out_n = longest_edge(ringA, cA)
        inward = (-out_n[0], -out_n[1])
    bank_centre = (mid_a[0] + inward[0] * BANK_DEPTH_M / 2.0,
                   mid_a[1] + inward[1] * BANK_DEPTH_M / 2.0)
    bank_len = len_a * BANK_FACADE_FRACTION
    bank_ring = strip_ring(bank_centre, along_a, bank_len, BANK_DEPTH_M)
    print("      BANK_MODE=%s : facade %.0f m long, bank %.0f x %.0f m"
          % (mode, len_a, bank_len, BANK_DEPTH_M))

    # intake: outside the receptor facade facing the source, on that facade's midpoint
    mid_b, along_b, len_b = facing_edge(ringB, cB, (-u[0], -u[1]))
    intake = (mid_b[0] - u[0] * INTAKE_STANDOFF_M, mid_b[1] - u[1] * INTAKE_STANDOFF_M)
    print("      source facing facade  %.0f m long, midpoint (%.0f, %.0f)" % (len_a, mid_a[0], mid_a[1]))
    print("      receptor facing facade %.0f m long, midpoint (%.0f, %.0f)" % (len_b, mid_b[0], mid_b[1]))

    site = solver.Site(SIZE_M, DX)
    for ring in (ringA, ringB):
        site.obstacle |= rasterise(ring, n, DX)
    bank_mask = rasterise(bank_ring, n, DX)
    site.source[bank_mask] += 11.0 / CALIBRATED["exchange_s"]      # discharge_k 11 K, calibrated tau
    bank_cells = int(bank_mask.sum())

    print("\n   PLACEMENT")
    gap = ring_gap(ringA, ringB)
    print("      facade-to-facade gap the plume must cross : %.1f m  (true edge-to-edge)" % gap)
    print("      condenser bank  %.0f x %.0f m strip, %d cells, %.0f m2   [ASSUMED position]"
          % (bank_len, BANK_DEPTH_M, bank_cells, bank_cells * DX * DX))
    print("      intake at (%.0f, %.0f) m, %.0f m outside the receptor facade  [ASSUMED]"
          % (intake[0], intake[1], INTAKE_STANDOFF_M))

    try:
        solver.assert_intake_clear(site, intake[0], intake[1], INTAKE_RADIUS_M, label="real site")
        print("      intake clear of obstacles and sources     : PASS")
    except Exception as ex:
        print("      intake clear check FAILED: %s" % str(ex)[:160])
        print("      *** Site NOT written. The intake standoff needs increasing.")
        return 2

    print("\n   THE SITE, as the solver sees it   ( # building   C condensers   I intake )")
    for row in ascii_map(site, intake):
        print("      " + row)

    json.dump({
        "provenance": "OpenStreetMap ways %s (source) and %s (receptor), Ashburn VA. ODbL."
                      % (A["osm_id"], B["osm_id"]),
        "domain": {"size_m": SIZE_M, "dx_m": DX, "n": n},
        "shift_applied_m": list(shift),
        "source_ring_m": ringA, "receptor_ring_m": ringB,
        "source_centre_m": list(cA), "receptor_centre_m": list(cB),
        "bank_mode": os.environ.get("BANK_MODE", "longest").lower(),
        "bank_ring_m": bank_ring, "bank_cells": bank_cells,
        "facade_gap_m": round(gap, 1),
        "bank_area_m2": bank_cells * DX * DX,
        "intake_m": list(intake), "intake_radius_m": INTAKE_RADIUS_M,
        "unit_source_to_receptor": list(u),
        "discharge_k": 11.0, "exchange_s": CALIBRATED["exchange_s"],
        "assumptions": {
            "bank_position": "strip inside the source hall on the facade facing the receptor; "
                             "NOT mapped in OSM. Conservative worst case.",
            "bank_facade_fraction": BANK_FACADE_FRACTION,
            "bank_depth_m": BANK_DEPTH_M,
            "intake_position": "on the receptor facade facing the source, %.0f m standoff; NOT mapped"
                               % INTAKE_STANDOFF_M,
            "building_height": "absent from OSM; irrelevant to this 2-D solver but central to the 2 m "
                               "measurement-height gap -- see docs/GEOMETRY-AND-PHYSICS.md section 2",
            "source_strength": "discharge_k 11 K with the calibrated exchange_s; strength per unit "
                               "area is unchanged from the validated reference, so total heat "
                               "release follows the real footprint",
        },
        "verification": "V1 rasteriser vs add_building, V2 area vs analytic, V3 no shared cells -- "
                        "all passed; the script refuses to write otherwise",
    }, open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
