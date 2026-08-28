# -*- coding: utf-8 -*-
"""🔴 SUPERSEDED 2026-08-24 by `build_national_pairs.py` -- kept as the record of a real first pass,
not a live source of truth. DO NOT USE THIS SCRIPT'S OUTPUT.

This script treats each discovery-grid ENTRY as one aggregate point/box. That is too coarse: an
entry the grid calls a "cluster" (>=3 tagged buildings in one ~11 km cell) is not guaranteed to
have any two of ITS OWN buildings within the solver's 600 m validated range, and this script cannot
see that -- it only compares entries to OTHER entries, never a cluster's buildings to each other.
`build_national_pairs.py` fetches every building's own coordinate and unions them directly at
600 m, which is the correct question. Measured difference: this script found 28 real pairing
candidates nationally; the correct building-level version found 243. The gap is the coarseness
this file's own docstring already warned about, not a contradiction -- the entry-level Georgia
finding below is still real, it is just a small fraction of what building-level union-find found.

S4 STEP 1 (historical) -- WHICH REGISTRY ENTRIES ARE REALLY ISOLATED? Free, instant, corrects a
known flaw.

    python classify_isolation.py

FREE. Pure computation over dc_clusters.json -- no network call, no credential. Writes
data/geometry/national_isolation.json.

--------------------------------------------------------------------------------------------
THE FLAW THIS FIXES, ALREADY FLAGGED IN THE REGISTRY'S OWN category_rule FIELD
--------------------------------------------------------------------------------------------
`discover_dc_clusters.py` classifies "single" (no tagged neighbour) by grid-cell membership: a
~0.10 deg (~11 km) cell holding exactly one tagged building. Two real, close neighbours can sit on
OPPOSITE sides of a cell boundary and each be recorded as a lone "single" -- correct about their
cell, wrong about the world. The registry's own `category_rule` says so: "S3/S4 must confirm no
neighbour NATIONALLY, not just in-cell, before calling it isolated."

Section 0.2 of NATIONAL-BUILD-PLAN.md fixed the DECISION (a validated-domain boundary, not an
invented distance), but not this measurement. G2 -- "does another tagged data centre exist within
the solver's validated range (<=600 m)?" -- needs the REAL nearest OTHER entry, computed nationally,
not "is there a neighbour in the same 11 km bucket".

--------------------------------------------------------------------------------------------
WHAT IS MEASURED, AND ITS ONE STATED IMPRECISION
--------------------------------------------------------------------------------------------
Nearest-neighbour distance is measured BOUNDING-BOX to BOUNDING-BOX (nearest corner/edge of each
entry's `lat_range`/`lon_range` extent), not centroid-to-centroid -- centroid distance would
OVERSTATE the gap for any multi-building cluster, which is the unsafe direction for a gate whose
job is deciding whether two real buildings could recirculate. Bbox-to-bbox still slightly
OVERSTATES the true nearest-BUILDING distance within a "cluster"/"pair" entry (since it uses the
aggregate rectangle, not each individual building's own footprint) -- stated here, and closed at
the geometry stage (classify_isolation feeds candidates into fetch_national_geometry.py, which
measures real building rings for anything this step calls "has a neighbour").
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
CLUSTERS_FILE = os.path.join(IA, "data", "geometry", "dc_clusters.json")
OUT = os.path.join(IA, "data", "geometry", "national_isolation.json")

KM_PER_DEG_LAT = 111.32
# The solver's own validated domain boundary (Project Prairie Grass, 150-600 m -- already cited,
# NATIONAL-BUILD-PLAN.md section 0.2). NOT a negligible-rise claim -- a statement of where this
# project's physics has ever been checked against reality.
SOLVER_VALIDATED_RANGE_M = 600.0


def bbox_gap_km(a, b):
    """Nearest-edge distance between two lat/lon bounding boxes, in km. 0 if they overlap."""
    alat, alon, blat, blon = a["lat_range"], a["lon_range"], b["lat_range"], b["lon_range"]
    lat_gap_deg = max(0.0, max(alat[0] - blat[1], blat[0] - alat[1]))
    lon_gap_deg = max(0.0, max(alon[0] - blon[1], blon[0] - alon[1]))
    mid_lat = (a["centre"][0] + b["centre"][0]) / 2.0
    dlat_km = lat_gap_deg * KM_PER_DEG_LAT
    dlon_km = lon_gap_deg * KM_PER_DEG_LAT * math.cos(math.radians(mid_lat))
    return math.hypot(dlat_km, dlon_km)


def main():
    clusters = json.load(open(CLUSTERS_FILE, encoding="utf-8"))["clusters"]
    keys = list(clusters.keys())
    n = len(keys)
    print("=" * 78)
    print("S4 STEP 1 -- REAL NATIONAL ISOLATION CHECK (not the discovery grid's cell boundaries)")
    print("=" * 78)
    print("   %d registry entries -- O(n^2) = %d comparisons, pure geometry, no network"
          % (n, n * (n - 1) // 2))

    nearest = {k: (None, float("inf")) for k in keys}
    for i in range(n):
        ki, ei = keys[i], clusters[keys[i]]
        for j in range(i + 1, n):
            kj, ej = keys[j], clusters[keys[j]]
            gap_km = bbox_gap_km(ei, ej)
            if gap_km < nearest[ki][1]:
                nearest[ki] = (kj, gap_km)
            if gap_km < nearest[kj][1]:
                nearest[kj] = (ki, gap_km)

    reclassified = 0
    out_entries = {}
    for k in keys:
        e = clusters[k]
        nb_key, nb_gap_km = nearest[k]
        nb_gap_m = nb_gap_km * 1000.0
        within_range = nb_gap_m <= SOLVER_VALIDATED_RANGE_M
        was_single = e["category"] == "single"
        if was_single and within_range:
            reclassified += 1
        out_entries[k] = {
            "state": e["state"], "category": e["category"], "n_tagged": e["n_tagged"],
            "centre": e["centre"],
            "nearest_other_entry": nb_key, "nearest_other_entry_gap_m": round(nb_gap_m, 1),
            # G2: is there a real reason to run the paired funnel at all?
            "has_neighbour_within_validated_range": within_range,
            "reclassified_from_single": was_single and within_range,
        }

    n_isolated = sum(1 for v in out_entries.values() if not v["has_neighbour_within_validated_range"])
    n_paired_candidate = n - n_isolated
    print("   %d entries have NO other tagged entry within the solver's %.0f m validated range"
          % (n_isolated, SOLVER_VALIDATED_RANGE_M))
    print("   %d entries have a real neighbour within range -- pairing candidates for the next step"
          % n_paired_candidate)
    print("   %d 'single' entries were actually mislabelled by the discovery grid -- a real "
          "neighbour sits just across a cell boundary" % reclassified)

    if reclassified:
        examples = [k for k, v in out_entries.items() if v["reclassified_from_single"]][:5]
        for k in examples:
            v = out_entries[k]
            print("      %-20s -> nearest is %-20s at %.0f m" % (k, v["nearest_other_entry"],
                                                                  v["nearest_other_entry_gap_m"]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({
        "generated_by": "src/classify_isolation.py", "api_calls_made": 0,
        "method": "bbox-to-bbox nearest edge distance, national, O(n^2) -- overstates the true "
                  "nearest-BUILDING distance for wide multi-building entries; understating a gap "
                  "is the unsafe direction and this method never does that",
        "solver_validated_range_m": SOLVER_VALIDATED_RANGE_M,
        "n_entries": n, "n_isolated": n_isolated, "n_paired_candidate": n_paired_candidate,
        "n_reclassified_from_single": reclassified,
        "entries": out_entries,
    }, open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
