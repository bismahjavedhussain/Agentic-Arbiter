# -*- coding: utf-8 -*-
"""S3 -- PACK THE NATIONAL REGISTRY INTO REAL 8x8 km FortyGuard PURCHASES.

    python pack_national_aois.py

FREE. Pure computation over data/geometry/dc_clusters.json -- no network call, no FortyGuard
credential, no Overpass query. Writes data/geometry/national_aoi_plan.json.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS, AND WHY IT DOES NOT USE THE DISCOVERY GRID
--------------------------------------------------------------------------------------------
`discover_dc_clusters.py` groups tagged buildings by a ~11 km (CELL_DEG=0.10) grid, purely so
Overpass results are countable. That grid is an ARTEFACT OF THE QUERY, not a real answer to "how
many 8x8 km FortyGuard purchases does this cover" -- two real, close-together sites can sit in
ADJACENT cells (and so look like two purchases) when a single real 8x8 km box would cover both, and
one real, sprawling campus can occupy ONE grid cell while genuinely needing more than one purchase
because it is wider than 8 km. This script re-derives the real answer from each entry's own measured
extent (`lat_range` / `lon_range`, already in the registry -- no need to re-fetch anything), which is
why NO new Overpass query is needed here.

--------------------------------------------------------------------------------------------
THE ALGORITHM, STATED SO IT CAN BE CHECKED
--------------------------------------------------------------------------------------------
1. OVERSIZED entries (own measured extent > 8 km in width or height) get their OWN dedicated
   ceil(w/8) x ceil(h/8) purchases. They are never asked to share -- a campus that is itself bigger
   than one AOI cannot be shrunk by sharing with a neighbour.
2. Everything else is PACKABLE. Greedy packing: repeatedly find the unassigned entry whose OWN
   8x8 km box (centred on that entry) would fully contain the most OTHER unassigned entries' own
   extents, commit that box, mark everything it covers as assigned, and repeat.
3. This is a GREEDY HEURISTIC, not a proof of the fewest possible purchases -- exact geometric bin
   packing is NP-hard and this project does not need the exact optimum, it needs a real, checkable,
   honest count. Stated as a heuristic here and on screen, not as an optimal solution.

--------------------------------------------------------------------------------------------
WHAT THIS DOES NOT DECIDE
--------------------------------------------------------------------------------------------
This does not buy anything and does not decide WHICH AOIs to buy first if the count exceeds the
150-call ceiling -- it computes the real national count and ranks AOIs by how many tagged buildings
each would put a real FortyGuard field behind, so that decision can be made with real numbers in
front of it, by the user, per rule 8 (ask before every paid call).
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IN = os.path.join(ROOT, "data", "geometry", "dc_clusters.json")
OUT = os.path.join(ROOT, "data", "geometry", "national_aoi_plan.json")

AOI_SIDE_KM = 8.0            # matches the FortyGuard heatmap call this project already buys
KM_PER_DEG_LAT = 111.32


def km_extent(lat_range, lon_range, lat_for_cos):
    dlat = (lat_range[1] - lat_range[0]) * KM_PER_DEG_LAT
    dlon = (lon_range[1] - lon_range[0]) * KM_PER_DEG_LAT * math.cos(math.radians(lat_for_cos))
    return dlat, dlon


def half_deg(km_half, lat_for_cos):
    """km -> degrees, at this latitude. Returns (half_deg_lat, half_deg_lon)."""
    return km_half / KM_PER_DEG_LAT, km_half / (KM_PER_DEG_LAT * math.cos(math.radians(lat_for_cos)))


def fits_within(entry_lat_range, entry_lon_range, box_lat_range, box_lon_range):
    return (box_lat_range[0] <= entry_lat_range[0] and entry_lat_range[1] <= box_lat_range[1]
            and box_lon_range[0] <= entry_lon_range[0] and entry_lon_range[1] <= box_lon_range[1])


def main():
    t0 = time.time()
    d = json.load(open(IN, encoding="utf-8"))
    clusters = d["clusters"]

    print("=" * 78)
    print("S3 -- NATIONAL AOI PACKING (real distance, not the discovery grid)")
    print("=" * 78)
    print("   %d registry entries (%d cluster / %d pair / %d single), %d tagged buildings"
          % (len(clusters), d["n_clusters"], d["n_pairs"], d["n_singles"], d["n_distinct_tagged_ways"]))

    oversized, packable = [], []
    for key, e in clusters.items():
        lat_c = e["centre"][0]
        h_km, w_km = km_extent(e["lat_range"], e["lon_range"], lat_c)
        e2 = dict(e, _key=key, _w_km=w_km, _h_km=h_km)
        if w_km > AOI_SIDE_KM or h_km > AOI_SIDE_KM:
            oversized.append(e2)
        else:
            packable.append(e2)

    # ---- Step 1: oversized entries get their own dedicated grid of AOIs, never shared. ----
    # 🔴 THIS USED TO EMIT ONE LIST ITEM CARRYING `"n_calls": nx*ny` AND A SINGLE CENTROID --
    # a purchase count that was never turned into that many actual, distinctly-centred boxes. A
    # downstream buyer iterating "one call per list item" would have bought exactly ONE box on the
    # cluster's centroid and silently missed every building outside it: an 83-building campus
    # wider than 8 km does not become covered by a single box just because the number 2 is written
    # beside it. Now each oversized entry emits `nx*ny` REAL entries, one per tile, each centred on
    # its own slice of the entry's measured extent -- so "how many purchases" and "how many boxes
    # actually exist in the list" can never diverge again.
    aois = []
    for e in oversized:
        lat0, lat1 = e["lat_range"]
        lon0, lon1 = e["lon_range"]
        nx = max(1, math.ceil(e["_w_km"] / AOI_SIDE_KM))
        ny = max(1, math.ceil(e["_h_km"] / AOI_SIDE_KM))
        for iy in range(ny):
            for ix in range(nx):
                tlat = lat0 + (lat1 - lat0) * (iy + 0.5) / ny
                tlon = lon0 + (lon1 - lon0) * (ix + 0.5) / nx
                aois.append({
                    "kind": "oversized_split", "entries": [e["_key"]], "n_calls": 1,
                    "tile": [iy * nx + ix, nx * ny],
                    "n_tagged": max(1, round(e["n_tagged"] / (nx * ny))),
                    "state": e["state"], "category": e["category"],
                    "centre": [tlat, tlon], "operators": e.get("operators", []),
                    "why_split": "%.1f x %.1f km, bigger than one %g km AOI -- tile %d of %d"
                                 % (e["_w_km"], e["_h_km"], AOI_SIDE_KM, iy * nx + ix + 1, nx * ny),
                })
    n_oversized_calls = len(aois)
    print("   %d entries exceed one %g km AOI on their own -- %d dedicated purchases, never shared"
          % (len(oversized), AOI_SIDE_KM, n_oversized_calls))

    # ---- Step 2: greedy pack everything else. ----
    remaining = {e["_key"]: e for e in packable}
    greedy_aois = []
    half_km = AOI_SIDE_KM / 2.0
    while remaining:
        best_key, best_covers, best_box = None, [], None
        for cand_key, cand in remaining.items():
            hlat, hlon = half_deg(half_km, cand["centre"][0])
            box_lat = (cand["centre"][0] - hlat, cand["centre"][0] + hlat)
            box_lon = (cand["centre"][1] - hlon, cand["centre"][1] + hlon)
            covers = [k for k, e in remaining.items()
                      if fits_within(e["lat_range"], e["lon_range"], box_lat, box_lon)]
            if len(covers) > len(best_covers):
                best_key, best_covers, best_box = cand_key, covers, (box_lat, box_lon)
        anchor = remaining[best_key]
        greedy_aois.append({
            "kind": "packed", "entries": best_covers, "n_calls": 1,
            "n_tagged": sum(remaining[k]["n_tagged"] for k in best_covers),
            "state": anchor["state"], "category": "mixed" if len(best_covers) > 1 else anchor["category"],
            "centre": anchor["centre"],
            "operators": sorted({op for k in best_covers for op in remaining[k].get("operators", [])})[:8],
            "n_entries_shared": len(best_covers),
        })
        for k in best_covers:
            del remaining[k]

    aois.extend(greedy_aois)
    n_packed_calls = len(greedy_aois)
    total_calls = n_oversized_calls + n_packed_calls
    total_tagged_covered = sum(a["n_tagged"] for a in aois)

    shared = [a for a in greedy_aois if a["n_entries_shared"] > 1]
    print("   %d packable entries -> %d real purchases (%d of them share >=2 registry entries)"
          % (len(packable), n_packed_calls, len(shared)))
    print("   TOTAL: %d real FortyGuard purchases would cover all %d registry entries / %d tagged "
          "buildings" % (total_calls, len(clusters), total_tagged_covered))

    # ---- Rank by impact: most tagged buildings served per purchase, for a ceiling decision. ----
    ranked = sorted(aois, key=lambda a: -a["n_tagged"])
    CEILING = 150
    cum = 0
    for i, a in enumerate(ranked):
        cum += a["n_tagged"]
        a["_rank"] = i + 1
        a["_cumulative_tagged_at_this_rank"] = cum
    covered_at_ceiling = ranked[:CEILING]
    tagged_at_ceiling = sum(a["n_tagged"] for a in covered_at_ceiling)
    print("\n   RANKED BY IMPACT (tagged buildings served per purchase), against the %d-call ceiling:"
          % CEILING)
    if total_calls <= CEILING:
        print("   ALL %d purchases fit inside the %d-call ceiling with %d calls to spare."
              % (total_calls, CEILING, CEILING - total_calls))
    else:
        print("   %d purchases needed, %d over the ceiling. The top %d by impact cover %d of %d "
              "tagged buildings (%.1f%%); the %d cut for the ceiling would drop %d buildings (%.1f%%)."
              % (total_calls, total_calls - CEILING, CEILING, tagged_at_ceiling,
                 total_tagged_covered, 100.0 * tagged_at_ceiling / total_tagged_covered,
                 total_calls - CEILING, total_tagged_covered - tagged_at_ceiling,
                 100.0 * (total_tagged_covered - tagged_at_ceiling) / total_tagged_covered))

    print("\n   TOP 20 PURCHASES BY IMPACT")
    print("   %-4s %-4s %-8s %6s %6s  %-19s %s"
          % ("rk", "st", "kind", "tagged", "calls", "centre", "operators"))
    for a in ranked[:20]:
        print("   %-4d %-4s %-8s %6d %6d  %8.4f,%9.4f  %s"
              % (a["_rank"], a["state"] or "??", a["kind"], a["n_tagged"], a["n_calls"],
                 a["centre"][0], a["centre"][1], (", ".join(a["operators"]) or "-")[:40]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({
        "generated_by": "src/pack_national_aois.py", "api_calls_made": 0,
        "method": "GREEDY heuristic, not proven optimal. Oversized entries (own extent > %g km) "
                  "get dedicated splits and never share; everything else is packed by repeatedly "
                  "taking the unassigned entry whose own %g km box covers the most other "
                  "unassigned entries." % (AOI_SIDE_KM, AOI_SIDE_KM),
        "aoi_side_km": AOI_SIDE_KM,
        "ceiling_evaluated": CEILING,
        "n_registry_entries": len(clusters), "n_tagged_buildings": d["n_distinct_tagged_ways"],
        "n_oversized_entries": len(oversized), "n_oversized_calls": n_oversized_calls,
        "n_packable_entries": len(packable), "n_packed_calls": n_packed_calls,
        "n_shared_purchases": len(shared),
        "total_calls_for_full_national_coverage": total_calls,
        "total_tagged_covered": total_tagged_covered,
        "tagged_covered_at_ceiling": tagged_at_ceiling,
        "runtime_seconds": round(time.time() - t0, 1),
        "aois": ranked,
    }, open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
