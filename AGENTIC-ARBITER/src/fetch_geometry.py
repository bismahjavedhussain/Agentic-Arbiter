# -*- coding: utf-8 -*-
"""Fetch REAL data-centre campus geometry from OpenStreetMap. FREE, keyless, no FortyGuard credential.

WHY THIS REPLACES A HAND-WRITTEN LAYOUT
    Every physics result so far used solver.demo_site() -- a layout invented in code: one hall, a
    condenser bank on its east face, a neighbour 300 m east. That is a fair reference case but it is
    made up, and "you invented the geometry" is a legitimate objection.

    FortyGuard cannot supply geometry either: /v1/satellite was probed on 2026-08-16 and returns a
    225 x 225 raster with a two-class vocabulary ("earth, ground" 99.78 %, "others" 0.22 %),
    alpha-blended over the photo, with NO georeferencing. No building footprints. So OpenStreetMap.

WHAT IT DOES
    Queries the Overpass API for building footprints in Loudoun County's data-centre corridor
    (Ashburn, Virginia -- the densest concentration of data centres on earth), converts lat/lon rings
    to a local metric frame, and ranks candidate PAIRS of large buildings by how well they match what
    the solver needs: a source building and a downwind neighbour a few hundred metres away.

    Output: data/geometry/ashburn_candidates.json -- footprints in metres, ready for the solver.

NO CREDENTIAL IS USED OR REQUIRED. Overpass and OSM are open data (ODbL).
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "data", "geometry")
# ---- THE METRO IS NOW A PARAMETER, and the default is byte-identical to what shipped.
# This file hard-coded a Loudoun County bbox and an `ashburn_candidates.json` output, so the agent
# could not be pointed anywhere else -- which made "choose your data centre" a promise the engine
# could not keep. `METRO=phoenix python fetch_geometry.py` now fetches Mesa/Chandler instead.
# With METRO unset it resolves to ashburn: the same bbox, the same filename, so every downstream
# artefact and every audited number is untouched.
sys.path.insert(0, HERE)
import metros as M                                                          # noqa: E402

MKEY = M.metro_key()
MET = M.metro(MKEY)
OUT = M.candidates_path(MKEY)
BBOX = MET["bbox"]                             # south, west, north, east
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",     # mirror, in case the primary is busy
]
MIN_AREA_M2 = 8000.0        # a hyperscale hall is tens of thousands of m2; this filters out sheds
MAX_AREA_M2 = 400000.0
PAIR_MIN_M = 120.0          # closer than this and the two are effectively one structure
PAIR_MAX_M = 700.0          # beyond this the plume is too dilute to matter at intake scale
RETRIES = 3
BACKOFF_S = 10

R_EARTH = 6371000.0


def overpass_query():
    s, w, n, e = BBOX
    # Ask for anything building-like plus explicit data-centre tagging, with full geometry.
    return f"""
[out:json][timeout:180];
(
  way["building"]({s},{w},{n},{e});
  way["telecom"="data_center"]({s},{w},{n},{e});
  way["building"="data_center"]({s},{w},{n},{e});
);
out geom tags;
""".strip()


def fetch():
    q = overpass_query()
    for ep in ENDPOINTS:
        for attempt in range(RETRIES):
            try:
                print("   querying %s (attempt %d)..." % (ep.split("/")[2], attempt + 1))
                data = urllib.parse.urlencode({"data": q}).encode()
                req = urllib.request.Request(ep, data=data,
                                             headers={"User-Agent": "AGENTIC-ARBITER/1.0 (hackathon)"})
                raw = urllib.request.urlopen(req, timeout=240).read()
                return json.loads(raw)
            except Exception as ex:
                print("      failed: %s" % str(ex)[:140])
                if attempt < RETRIES - 1:
                    time.sleep(BACKOFF_S)
    return None


def to_metres(ring, lat0, lon0):
    """Local equirectangular projection. Accurate to well under a metre over a few km."""
    out = []
    for p in ring:
        la, lo = p["lat"], p["lon"]
        x = math.radians(lo - lon0) * R_EARTH * math.cos(math.radians(lat0))
        y = math.radians(la - lat0) * R_EARTH
        out.append((x, y))
    return out



def min_area_rect(pts):
    """Smallest-area enclosing rectangle, tried at every edge orientation.

    An axis-aligned bounding box badly overstates a rotated building -- at the selected Ashburn pair
    the real polygons fill only 0.38 and 0.46 of their bboxes. Buildings align to roads, not to north.
    Returns (long_side_m, short_side_m, angle_deg_of_long_side_from_east).
    """
    best = None
    n = len(pts)
    for k in range(n):
        x1, y1 = pts[k]
        x2, y2 = pts[(k + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        L = math.hypot(ex, ey)
        if L < 1e-9:
            continue
        ux, uy = ex / L, ey / L          # along the edge
        vx, vy = -uy, ux                 # perpendicular
        us = [p[0] * ux + p[1] * uy for p in pts]
        vs = [p[0] * vx + p[1] * vy for p in pts]
        a = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or a < best[0]:
            best = (a, max(us) - min(us), max(vs) - min(vs), math.degrees(math.atan2(uy, ux)))
    if best is None:
        return 0.0, 0.0, 0.0
    _, s1, s2, ang = best
    return (max(s1, s2), min(s1, s2), ang % 180.0)


def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def oriented_extent(pts):
    """Axis-aligned width (E-W) and height (N-S) in metres -- what the solver's add_building takes."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return max(xs) - min(xs), max(ys) - min(ys)


def main():
    print("=" * 78)
    print("AGENTIC-ARBITER  real campus geometry from OpenStreetMap   [FREE, no credential]")
    print("=" * 78)
    os.makedirs(OUT_DIR, exist_ok=True)

    if os.path.exists(OUT):
        d = json.load(open(OUT, encoding="utf-8"))
        print("   cached: %s" % OUT)
        print("   %d buildings, %d candidate pairs" % (len(d["buildings"]), len(d["pairs"])))
        return 0

    js = fetch()
    if js is None:
        print("\n   Overpass unreachable. Nothing written -- an empty geometry file would silently")
        print("   poison the solver. Re-run when the service recovers.")
        return 2

    els = [e for e in js.get("elements", []) if e.get("type") == "way" and e.get("geometry")]
    print("\n   %d ways returned" % len(els))

    lat0 = (BBOX[0] + BBOX[2]) / 2.0
    lon0 = (BBOX[1] + BBOX[3]) / 2.0

    buildings = []
    for e in els:
        ring = e["geometry"]
        if len(ring) < 4:
            continue
        pts = to_metres(ring, lat0, lon0)
        area = poly_area(pts)
        if not (MIN_AREA_M2 <= area <= MAX_AREA_M2):
            continue
        cx, cy = centroid(pts)
        w, h = oriented_extent(pts)
        L, W, ang = min_area_rect(pts)
        tags = e.get("tags", {})
        buildings.append({
            "osm_id": e["id"],
            "area_m2": round(area, 1),
            "centre_m": [round(cx, 1), round(cy, 1)],
            "width_m": round(w, 1), "height_m": round(h, 1),
            # the axis-aligned bbox above OVERSTATES a rotated building: measured fill ratios of
            # 0.38 and 0.46 at the selected pair. The rotated minimum-area rectangle and the raw
            # ring are the honest descriptors, so both are kept.
            "rot_rect_long_m": round(L, 1), "rot_rect_short_m": round(W, 1),
            "rot_rect_angle_deg": round(ang, 1),
            "ring_m": [[round(x, 1), round(y, 1)] for x, y in pts],
            "name": tags.get("name"),
            "operator": tags.get("operator"),
            "building_tag": tags.get("building"),
            "telecom_tag": tags.get("telecom"),
            "n_vertices": len(ring),
            "centre_latlon": [round(lat0 + math.degrees(cy / R_EARTH), 6),
                              round(lon0 + math.degrees(cx / (R_EARTH * math.cos(math.radians(lat0)))), 6)],
        })

    buildings.sort(key=lambda b: -b["area_m2"])
    print("   %d buildings between %.0f and %.0f m2" % (len(buildings), MIN_AREA_M2, MAX_AREA_M2))
    named = [b for b in buildings if b["name"] or b["operator"] or b["telecom_tag"]]
    print("   %d of them carry a name, operator or telecom tag" % len(named))
    print("\n   ten largest:")
    print("      %-12s %10s %9s %9s  %s" % ("osm_id", "area m2", "width m", "depth m", "name / operator"))
    for b in buildings[:10]:
        label = b["name"] or b["operator"] or (b["telecom_tag"] and "telecom=" + b["telecom_tag"]) or "-"
        print("      %-12s %10.0f %9.0f %9.0f  %s" % (b["osm_id"], b["area_m2"], b["width_m"],
                                                      b["height_m"], str(label)[:34]))

    # candidate pairs: a source hall and a neighbour at a plume-relevant separation
    pairs = []
    for i, a in enumerate(buildings):
        for b in buildings[i + 1:]:
            dx = b["centre_m"][0] - a["centre_m"][0]
            dy = b["centre_m"][1] - a["centre_m"][1]
            sep = math.hypot(dx, dy)
            if not (PAIR_MIN_M <= sep <= PAIR_MAX_M):
                continue
            bearing = (math.degrees(math.atan2(dx, dy))) % 360.0     # from a to b, 0 = north
            pairs.append({
                "source_osm_id": a["osm_id"], "receptor_osm_id": b["osm_id"],
                "separation_m": round(sep, 1),
                "bearing_a_to_b_deg": round(bearing, 1),
                "source_area_m2": a["area_m2"], "receptor_area_m2": b["area_m2"],
                "combined_area_m2": round(a["area_m2"] + b["area_m2"], 1),
                "source_name": a["name"] or a["operator"],
                "receptor_name": b["name"] or b["operator"],
            })
    # rank by combined size: the biggest adjacent pair is the most representative hyperscale case
    pairs.sort(key=lambda p: -p["combined_area_m2"])
    print("\n   %d candidate pairs at %.0f-%.0f m separation" % (len(pairs), PAIR_MIN_M, PAIR_MAX_M))
    print("      %-12s %-12s %9s %9s %12s" % ("source", "receptor", "sep m", "bearing", "combined m2"))
    for p in pairs[:8]:
        print("      %-12s %-12s %9.0f %9.1f %12.0f"
              % (p["source_osm_id"], p["receptor_osm_id"], p["separation_m"],
                 p["bearing_a_to_b_deg"], p["combined_area_m2"]))

    json.dump({
        "source": "OpenStreetMap via Overpass API (ODbL). Free, keyless. No FortyGuard credential used.",
        "fetched_bbox_south_west_north_east": list(BBOX),
        "projection": "local equirectangular about the bbox centre; metres",
        "projection_origin_latlon": [lat0, lon0],
        "filters": {"min_area_m2": MIN_AREA_M2, "max_area_m2": MAX_AREA_M2,
                    "pair_min_m": PAIR_MIN_M, "pair_max_m": PAIR_MAX_M},
        "n_ways_returned": len(els),
        "buildings": buildings, "pairs": pairs,
        "caveat": "OSM footprints are crowd-sourced; heights are usually absent, so the solver's "
                  "building height stays a stated assumption rather than a measurement. Condenser "
                  "bank positions are NOT in OSM and remain an assumption placed on the downwind face.",
    }, open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
