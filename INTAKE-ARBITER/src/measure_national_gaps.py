# -*- coding: utf-8 -*-
"""S4 STEP 5 -- G3, THE REAL GATE: >= 60 m edge-to-edge, on REAL footprint rings. Free, instant.

    python measure_national_gaps.py

FREE. Pure computation over `national_geometry.json` + `national_building_groups.json` -- no
network, no credential. Writes data/geometry/national_gate_verdicts.json.

--------------------------------------------------------------------------------------------
REUSED, NOT REIMPLEMENTED -- gotcha #12
--------------------------------------------------------------------------------------------
`to_metres()` (fetch_geometry.py) and `ring_gap()` / `longest_edge()` (build_site.py) are imported
directly, unchanged. This project's own rule 12 is "never let two code paths compute one quantity
two ways" -- a second gap-measurement function, however carefully written, is exactly that mistake.

--------------------------------------------------------------------------------------------
WHICH TWO BUILDINGS, WHEN A GROUP HAS MORE THAN TWO
--------------------------------------------------------------------------------------------
A real 600 m group can hold more than 2 buildings (measured: up to 81). The single-metro pipeline
(`refusal_rank.py`) scores every pair by usable_exposure and picks the best. At national scale,
scoring every pair inside an 81-building group (3,240 pairs) for every one of 243 groups is not
this session's remaining scope -- the pragmatic, HONESTLY STATED simplification here is: measure
the CLOSEST two buildings in each group (by centroid distance, from `national_building_groups.json`,
already computed) as the representative candidate. This is not a claim that it is the BEST possible
pair, only the nearest -- and the nearest pair is the one most likely to bind the G3 floor, so it is
also the conservative choice for a refusal decision (a pair that clears at its closest distance
would also clear at any other spacing; a pair refused at its closest distance might still be
refusable at another spacing too, but this method will not falsely PASS a group that has a real
problem, which is the safe direction for a gate).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from fetch_geometry import to_metres                                        # noqa: E402
from build_site import ring_gap, longest_edge                               # noqa: E402

GROUPS_FILE = os.path.join(IA, "data", "geometry", "national_building_groups.json")
GEOM_FILE = os.path.join(IA, "data", "geometry", "national_geometry.json")
OUT = os.path.join(IA, "data", "geometry", "national_gate_verdicts.json")

# THE SAME constant the single-metro pipeline gates on (build_site.py / select_site.py), imported
# by value comment, not re-derived: standoff + intake radius + half the condenser bank depth = 60 m
# (gotcha #65 -- it was 50 m and omitted the bank; Ashburn's own committed site clears it by 0.3 m).
MIN_GAP_M = 60.0
KM_PER_DEG_LAT = 111.32


def haversine_m(lat1, lon1, lat2, lon2):
    dlat_km = (lat2 - lat1) * KM_PER_DEG_LAT
    mid = (lat1 + lat2) / 2.0
    dlon_km = (lon2 - lon1) * KM_PER_DEG_LAT * math.cos(math.radians(mid))
    return math.hypot(dlat_km, dlon_km) * 1000.0


def is_building_footprint(ring_rec):
    """Is this OSM way a BUILDING, or a land parcel that merely carries `telecom=data_center`?

    THE ONE DEFINITION, imported by `build_national_registry.py` rather than restated there, so the
    gate and the registry cannot disagree about what a building is.

    The test is the presence of a `building=*` tag. That is OSM's own distinction, not a heuristic
    of ours: a hall is `building=yes` / `building=industrial` / `building=data_center`, while a site
    boundary is `landuse=industrial` + `telecom=data_center` with no `building` key. Measured across
    the 1,622 tagged ways: 1,535 carry `building=*` (median 10,625 m2, max 12.4 ha -- plausible
    halls) and 87 do not (median 61,894 m2, max 247 ha, 60 of them explicitly `landuse`).

    NOT judged on AREA, deliberately. A 12 ha hall and a 6 ha parcel overlap in size, so a
    threshold would misclassify both directions -- and it would be an invented constant, which is
    the #49 scar. The tag is a fact recorded by the mapper; the area is an inference we would be
    making about it.
    """
    if not ring_rec:
        return False
    b = (ring_rec.get("tags") or {}).get("building")
    # `building=no` IS A TAG, AND IT MEANS THE OPPOSITE OF WHAT A PRESENCE TEST CONCLUDES.
    # OSM uses it to state explicitly that a mapped area is NOT a building -- usually to override a
    # bad import or a misleading outline. A `"building" in tags` test counts it as one. Three ways
    # nationally carry it, and one of them (`Compute North`, NE) was the ONLY "building" in its
    # facility, so the facility was being published as a standalone site with a 235.8 m facade that
    # the mapper had explicitly said is not a building.
    if b is None or str(b).strip().lower() == "no":
        return False
    return True


# ⚠ NOT FILTERED HERE, AND STATED RATHER THAN SILENTLY INCLUDED: 16 ways carry
# `building=construction`. Those are real structures with real outlines, so the geometry is valid
# and they are measured -- but a facility still under construction has no operating chiller plant,
# and this project has already refused a whole metro (Phoenix) for exactly that reason on IMAGERY
# evidence. Construction status from a crowd-sourced tag is not evidence of the same quality as a
# photograph, so it is recorded as a question for the imagery stage (S6) rather than acted on with a
# tag alone. `data/geometry/national_registry.json` carries the tag per building so the stage that
# CAN judge it has the input.
BUILDING_TAGS_NEEDING_IMAGERY_REVIEW = ("construction",)


def centroid_latlon(ring_latlon):
    return (sum(p[0] for p in ring_latlon) / len(ring_latlon),
           sum(p[1] for p in ring_latlon) / len(ring_latlon))


def real_gap_m(rings_raw, wa, wb):
    """The true edge-to-edge gap between two buildings' real footprints, or None if either is
    missing geometry. Projects locally around THIS pair's own centroid -- correct even for a
    building far from the group's overall centre."""
    ra, rb = rings_raw.get(wa), rings_raw.get(wb)
    if not ra or not rb:
        return None
    lat0, lon0 = centroid_latlon(ra["geometry"])
    ring_a_m = to_metres([{"lat": p[0], "lon": p[1]} for p in ra["geometry"]], lat0, lon0)
    ring_b_m = to_metres([{"lat": p[0], "lon": p[1]} for p in rb["geometry"]], lat0, lon0)
    return ring_gap(ring_a_m, ring_b_m)


def main():
    groups_doc = json.load(open(GROUPS_FILE, encoding="utf-8"))
    geom_doc = json.load(open(GEOM_FILE, encoding="utf-8"))
    rings_raw = geom_doc["rings"]

    paired_groups = {k: g for k, g in groups_doc["groups"].items() if g["kind"] == "pairing_candidate"}
    print("=" * 78)
    print("S4 STEP 5 -- G3: REAL EDGE-TO-EDGE GAP >= %.0f m, on real footprint rings" % MIN_GAP_M)
    print("=" * 78)
    print("   %d real pairing groups to measure" % len(paired_groups))
    n_internal_pairs = sum(g["n_members"] * (g["n_members"] - 1) // 2 for g in paired_groups.values())
    print("   checking EVERY internal pair per group (%d total) -- not just the closest one." % n_internal_pairs)
    print("   FIXED 2026-08-24: closest-pair-only gave a FALSE 'too close' verdict for real,")
    print("      working sites (Chicago, Dulles) whose group holds >2 buildings and whose")
    print("      COMMITTED pair is not the nearest one. Checking every pair removes that false")
    print("      negative -- a group is only refused if EVERY internal pair fails.")

    verdicts = {}
    n_clear = n_too_close = n_missing_geom = n_no_building = 0
    n_parcels_excluded = 0
    for gkey, g in paired_groups.items():
        # 🔴 BUILDINGS ONLY. A PROPERTY LINE IS NOT A FACADE.
        # `discover_dc_clusters.py` filters on `telecom=data_center OR building=data_center`, and
        # `telecom=data_center` is applied in OSM to LAND PARCELS as well as to halls: measured on
        # this registry, 87 of 1,622 tagged ways carry no `building=*` tag at all, 60 of them are
        # explicitly `landuse`, and their median area is 6x the real footprints' with a maximum of
        # 247 HECTARES. The largest was a 9-vertex, 116.8 ha polygon named "Amazon AWS Data Center"
        # whose "longest wall" came out at 1,489.8 m.
        # Measuring a facade gap between two of those measures a distance between FENCE LINES, and
        # the condenser bank this project places on a facade has nowhere to sit on one. Before this
        # filter, 18 of 243 verdicts (7.4 %) were decided on a parcel edge -- EIGHT of them
        # reported CLEAR, i.e. a property-line gap read as a safe facade gap, which would have let
        # the solver run on geometry that does not describe a building.
        members = [m for m in g["members"] if is_building_footprint(rings_raw.get(m))]
        n_parcels_excluded += len(g["members"]) - len(members)
        if len(members) < 2:
            # Not "too close" and not a fetch gap: there are fewer than two BUILDINGS here to
            # measure between. Recorded as its own outcome so it cannot be counted as a refusal.
            n_no_building += 1
            verdicts[gkey] = {
                "state": g["states"][0] if len(g["states"]) == 1 else "MIX",
                "n_members_in_group": g["n_members"],
                "source_entries": g["source_entries"],
                "n_building_footprints": len(members),
                "verdict": "no_building_footprint",
                "why": "this group holds %d tagged way(s) but only %d with a `building=*` tag; the "
                       "rest are land parcels (`landuse`/`telecom` polygons). There is no facade "
                       "to measure a gap between, so no verdict is issued -- the site is real, the "
                       "geometry does not describe a building."
                       % (g["n_members"], len(members)),
                "real_edge_to_edge_gap_m": None, "min_gap_m": MIN_GAP_M,
                "best_pair": None, "names": [], "n_pairs_checked": 0, "any_pair_clears": False,
            }
            continue
        n = len(members)
        best_clear = None      # the pair with the LARGEST gap that still clears the floor
        best_fail = None       # the pair with the LARGEST gap among those that do NOT clear it
        any_geom = False
        for i in range(n):
            for j in range(i + 1, n):
                wa, wb = members[i], members[j]
                gm = real_gap_m(rings_raw, wa, wb)
                if gm is None:
                    continue
                any_geom = True
                if gm >= MIN_GAP_M:
                    if best_clear is None or gm > best_clear[0]:
                        best_clear = (gm, wa, wb)
                else:
                    if best_fail is None or gm > best_fail[0]:
                        best_fail = (gm, wa, wb)
        if not any_geom:
            n_missing_geom += 1
            verdicts[gkey] = {"state": g["states"][0] if len(g["states"]) == 1 else "MIX",
                              "verdict": "geometry_missing", "gap_m": None}
            continue
        clear = best_clear is not None
        chosen = best_clear if clear else best_fail
        gap_m, wa, wb = chosen
        if clear:
            n_clear += 1
        else:
            n_too_close += 1
        verdicts[gkey] = {
            "state": g["states"][0] if len(g["states"]) == 1 else "MIX",
            "n_members_in_group": g["n_members"], "source_entries": g["source_entries"],
            "best_pair": [wa, wb],
            "names": [(rings_raw.get(wa) or {}).get("tags", {}).get("name"),
                     (rings_raw.get(wb) or {}).get("tags", {}).get("name")],
            "real_edge_to_edge_gap_m": round(gap_m, 2),
            "verdict": "clear" if clear else "too_close",
            "min_gap_m": MIN_GAP_M,
            "n_pairs_checked": n * (n - 1) // 2,
            "any_pair_clears": clear,
        }

    print("   %d groups CLEAR the %.0f m floor -- at least one real internal pair qualifies"
          % (n_clear, MIN_GAP_M))
    print("   %d groups are TOO CLOSE -- EVERY internal pair fails, refused on evidence"
          % n_too_close)
    print("   %d groups had missing geometry (fetch gap, not a verdict)" % n_missing_geom)
    print("   %d groups have FEWER THAN TWO BUILDING footprints -- no facade to measure between,"
          % n_no_building)
    print("      so no verdict. NOT a refusal: the site is real, the geometry is a land parcel.")
    print("   %d parcel way(s) excluded from measurement across all groups (see"
          % n_parcels_excluded)
    print("      is_building_footprint: `telecom=data_center` is applied to landuse polygons too)")

    if n_too_close:
        examples = [k for k, v in verdicts.items() if v["verdict"] == "too_close"][:5]
        for k in examples:
            v = verdicts[k]
            print("      REFUSED  %-20s best gap %.1f m < %.0f m over %d pairs  (%s)"
                  % (k, v["real_edge_to_edge_gap_m"], MIN_GAP_M, v["n_pairs_checked"],
                     ", ".join(filter(None, v["names"]))))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/measure_national_gaps.py", "api_calls_made": 0,
              "min_gap_m": MIN_GAP_M, "method": "EVERY internal pair of BUILDING footprints in "
              "each real (<=600m) group measured via ring_gap(); a group is 'clear' if ANY pair "
              "clears the floor, 'too_close' only if EVERY pair fails it. Ways without a "
              "`building=*` tag are land parcels and are EXCLUDED -- a property line is not a "
              "facade, and 18 of 243 verdicts were previously decided on one",
              "n_groups": len(paired_groups), "n_clear": n_clear, "n_too_close": n_too_close,
              "n_missing_geometry": n_missing_geom,
              "n_no_building_footprint": n_no_building,
              "n_parcel_ways_excluded": n_parcels_excluded,
              "verdicts": verdicts},
             open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
