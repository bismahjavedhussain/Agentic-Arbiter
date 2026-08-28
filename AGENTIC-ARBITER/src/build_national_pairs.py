# -*- coding: utf-8 -*-
"""S4 STEP 3 -- REAL BUILDING-LEVEL GROUPS, by the solver's 600 m validated range. Free, instant.

    python build_national_pairs.py

FREE. Pure computation over `national_building_centres.json` -- no network, no credential. Writes
data/geometry/national_building_groups.json.

--------------------------------------------------------------------------------------------
WHY UNION-FIND ON REAL DISTANCE, NOT THE DISCOVERY GRID OR THE ENTRY BBOX
--------------------------------------------------------------------------------------------
Neither of the two earlier passes answers G2 correctly at the building level:
  - `discover_dc_clusters.py`'s grid groups by an arbitrary ~11 km cell -- a cell can hold three
    buildings that are 10 km apart from each other inside it, or split two 300 m-apart buildings
    across a boundary into two different "single" entries.
  - `classify_isolation.py`'s bbox check treats a whole multi-building entry as one aggregate
    point/box, so it cannot see that a "cluster" entry's own buildings might not actually be
    mutually within the solver's 600 m validated range.

This step has each building's OWN coordinate (from `fetch_national_building_centres.py`) and does
the only thing that is actually correct: connect any two buildings within 600 m with a union-find
edge, and let CONNECTED COMPONENTS be the real groups -- transitively, so three buildings each
300 m from the next but 600 m apart end-to-end are correctly one group, matching what "within
range of a real neighbour" has to mean.

A component of size 1 is genuinely isolated (G2 fails, the standalone path -- section 0.2). A
component of size >= 2 is a real pairing/cluster candidate and is handed to
`fetch_national_geometry.py` for the exact G3 (facade gap) measurement. Centroid distance is USUALLY
larger than the true edge-to-edge gap for compact, convex buildings, but that is a tendency, not a
guarantee: measured counter-example, `TX_way_1533350872` (Microsoft Texas Research Park), whose real
ring-to-ring gap (130.7 m) came back LARGER than the crude vertex-average centroid distance
(50.7 m) between an irregularly-shaped pair. Nothing here is treated as a final verdict either
way -- `measure_national_gaps.py` decides G3 from real footprint rings, never from this distance.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
CENTRES_FILE = os.path.join(IA, "data", "geometry", "national_building_centres.json")
CLUSTERS_FILE = os.path.join(IA, "data", "geometry", "dc_clusters.json")
OUT = os.path.join(IA, "data", "geometry", "national_building_groups.json")

KM_PER_DEG_LAT = 111.32
SOLVER_VALIDATED_RANGE_M = 600.0     # same constant as classify_isolation.py -- one definition


def haversine_m(lat1, lon1, lat2, lon2):
    dlat_km = (lat2 - lat1) * KM_PER_DEG_LAT
    mid = (lat1 + lat2) / 2.0
    dlon_km = (lon2 - lon1) * KM_PER_DEG_LAT * math.cos(math.radians(mid))
    return math.hypot(dlat_km, dlon_km) * 1000.0


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def main():
    centres_doc = json.load(open(CENTRES_FILE, encoding="utf-8"))
    centres = centres_doc["centres"]
    clusters = json.load(open(CLUSTERS_FILE, encoding="utf-8"))["clusters"]

    # which registry entry (and its state) each building belongs to, and its category before this
    building_to_entry = {}
    for ekey, e in clusters.items():
        for wid in e["osm_ids"]:
            building_to_entry[wid] = {"entry": ekey, "state": e["state"], "category": e["category"]}

    ids = [wid for wid in centres if wid in building_to_entry]
    print("=" * 78)
    print("S4 STEP 3 -- REAL BUILDING GROUPS at the %.0f m validated range"
          % SOLVER_VALIDATED_RANGE_M)
    print("=" * 78)
    print("   %d buildings with both a coordinate and a registry entry -- O(n^2) = %d comparisons"
          % (len(ids), len(ids) * (len(ids) - 1) // 2))

    uf = UnionFind(ids)
    n_edges = 0
    for i in range(len(ids)):
        lat_i, lon_i = centres[ids[i]]["lat"], centres[ids[i]]["lon"]
        for j in range(i + 1, len(ids)):
            # cheap pre-filter: a >0.02 deg lat difference is already > 2 km, no need to haversine
            if abs(centres[ids[j]]["lat"] - lat_i) > 0.02:
                continue
            d = haversine_m(lat_i, lon_i, centres[ids[j]]["lat"], centres[ids[j]]["lon"])
            if d <= SOLVER_VALIDATED_RANGE_M:
                uf.union(ids[i], ids[j])
                n_edges += 1

    groups = {}
    for wid in ids:
        groups.setdefault(uf.find(wid), []).append(wid)

    isolated = [g for g in groups.values() if len(g) == 1]
    paired = [g for g in groups.values() if len(g) >= 2]
    print("   %d real edges (<=%.0f m) found among %d buildings"
          % (n_edges, SOLVER_VALIDATED_RANGE_M, len(ids)))
    print("   %d buildings are GENUINELY isolated (no real neighbour within range)" % len(isolated))
    print("   %d real groups of >=2 buildings -- pairing/cluster candidates for geometry" % len(paired))
    print("   sizes of the paired groups: %s" % sorted((len(g) for g in paired), reverse=True)[:15])

    # cross-check against the discovery grid's own category, honestly -- where they disagree, say so
    disagreements = 0
    for g in groups.values():
        cats = {building_to_entry[w]["category"] for w in g}
        was_single_now_grouped = len(g) >= 2 and cats == {"single"}
        was_grouped_now_isolated = len(g) == 1 and building_to_entry[g[0]]["category"] != "single"
        if was_single_now_grouped or was_grouped_now_isolated:
            disagreements += 1
    print("   %d groups disagree with the discovery grid's original category -- expected, since "
          "the grid used an ~11 km cell and this uses the real %.0f m range"
          % (disagreements, SOLVER_VALIDATED_RANGE_M))

    out_groups = {}
    for root, members in groups.items():
        states = sorted({building_to_entry[w]["state"] or "XX" for w in members})
        gkey = "%s_%s" % (states[0] if len(states) == 1 else "MIX", root.replace("/", "_"))
        out_groups[gkey] = {
            "members": members, "n_members": len(members),
            "states": states, "source_entries": sorted({building_to_entry[w]["entry"] for w in members}),
            "centres": [[centres[w]["lat"], centres[w]["lon"]] for w in members],
            "names": [centres[w].get("name") for w in members if centres[w].get("name")],
            "operators": sorted({centres[w].get("operator") for w in members
                                 if centres[w].get("operator")}),
            "kind": "isolated" if len(members) == 1 else "pairing_candidate",
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/build_national_pairs.py", "api_calls_made": 0,
              "solver_validated_range_m": SOLVER_VALIDATED_RANGE_M,
              "n_buildings": len(ids), "n_isolated": len(isolated), "n_pairing_candidates": len(paired),
              "n_disagreements_with_discovery_grid": disagreements,
              "groups": out_groups},
             open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
