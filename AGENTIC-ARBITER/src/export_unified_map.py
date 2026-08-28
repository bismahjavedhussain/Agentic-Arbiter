# -*- coding: utf-8 -*-
"""ONE MAP, EVERY REAL SITE -- the union of sites.json (5 hand-built metros) and the 422-entry
national registry, cross-referenced by OSM id so nothing is ever counted or shown twice.

    python export_unified_map.py

FREE. Pure computation over files already on disk -- no network call, no credential. Writes
demo/unified_sites.json.

--------------------------------------------------------------------------------------------
WHY A CROSS-REFERENCE, NOT A CONCATENATION
--------------------------------------------------------------------------------------------
Ashburn, Chicago, Dulles, Phoenix and Santa Clara are ALL real, OSM-tagged buildings, so all five
already exist somewhere inside `dc_clusters.json`'s 422 entries -- they were never a separate
population. Concatenating the two lists would show each of the five TWICE. This module finds each
metro's committed OSM ids inside the national registry and ANNOTATES that entry with the metro's
already-known, already-verified status, instead of adding a duplicate point.

--------------------------------------------------------------------------------------------
THE FIVE STATUSES, AND WHAT EACH ONE HONESTLY CLAIMS
--------------------------------------------------------------------------------------------
  fully_built        one of the 3 metros with a complete agent run and a purchased FortyGuard
                     field (ashburn/chicago/dulles). Clicking it opens the SAME existing flow,
                     unchanged -- nothing about that path is new.
  refused_known      one of the 2 metros already refused by a REAL, already-run imagery check
                     (phoenix: not built; santaclara: rooftop-cooled). The reason is carried
                     verbatim from sites.json, never re-derived or guessed.
  refused_geometry   a national entry whose OWN real footprint geometry means every possible
                     internal pairing is too close to measure safely (G3, measure_national_gaps.py).
  isolated           a national entry with no other tagged building within the solver's validated
                     range (600 m) -- not refused, just no plume term; still a real candidate for a
                     standalone run once weather/imagery/a field exist for it.
  not_yet_screened   passed geometry (or has a real neighbour not yet geometry-checked) but has not
                     been through weather (S5), imagery (S6) or a FortyGuard field (S7) -- the
                     honest, current state of the great majority of the country today.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")
CLUSTERS_FILE = os.path.join(IA, "data", "geometry", "dc_clusters.json")
SITES_FILE = os.path.join(DEMO, "sites.json")
ISOLATION_FILE = os.path.join(IA, "data", "geometry", "national_building_groups.json")
VERDICTS_FILE = os.path.join(IA, "data", "geometry", "national_gate_verdicts.json")
# THE FACILITY REGISTRY -- the unit this map now plots. One connected component of tagged buildings
# inside the solver's validated range = one dot, replacing the ~11 km discovery-grid cell that could
# hold anywhere from 1 to 81 buildings behind a single marker.
REGISTRY_FILE = os.path.join(IA, "data", "geometry", "national_registry.json")
OUT = os.path.join(DEMO, "unified_sites.json")

sys.path.insert(0, HERE)
import metros as M                                                          # noqa: E402


# VERDICTS THAT MEAN "THIS IS NOT AN OPERATING DATA CENTRE", as opposed to "this is one and our
# model does not describe it". Only these remove a facility from the map.
#   NOT_BUILT          the footprints are mapped but nothing is built there yet
#   NOT_A_DATA_CENTRE  the buildings are real and are something else (a warehouse, a colo suite
#                      inside a leased industrial unit) -- OSM's name is on the wrong structure
# ROOFTOP is deliberately NOT here: that facility exists and operates, and it stays on the map
# carrying its refusal. See the block in main() for why the two cases must not be merged.
ABSENT_VERDICTS = {"NOT_BUILT", "NOT_A_DATA_CENTRE"}

# 🔴 `PAIR_NOT_BUILT` IS DELIBERATELY *NOT* IN ABSENT_VERDICTS, and the distinction was forced by a
# real case rather than invented. At VA_way_460175664 the FACILITY is a live Digital Realty campus
# (IAD42, Building R, 22124 Broderick Drive, operating) while the two footprints `select_site.py`
# committed to are a demolished office park being redeveloped -- USGS shows the offices, ESRI shows
# the cleared pads, OSM tags both ways `building=construction`, and a dated trade source confirms
# the area is "knock-down redevelopment converting office parks into data centers".
# Excluding that facility from the map would HIDE A REAL, OPERATING DATA CENTRE, which is the
# opposite of the rule that excludes the absent ones. So the map keeps the dot and states the
# refusal; the agent still cannot run on it, because `offerable` is gated separately on in_scope.
#
# ONE REASON SENTENCE PER VERDICT. The first version of the refused-site detail asserted "the plant
# is not at the 2 m plane" for every out-of-scope verdict, which is true of ROOFTOP and false of the
# others -- gotcha #67 is that a sentence stating a reason must state THIS site's reason.
REFUSAL_REASON = {
    "ROOFTOP": ("the cooling plant is roof-mounted, so FortyGuard's 2 m field does not describe "
                "the air it breathes — the same refusal Santa Clara carries"),
    "NO_GROUND_PLANT_VISIBLE": ("no ground-level cooling plant is visible on either committed "
                                "building, so the condenser bank this model needs is not evidenced"),
    "PAIR_NOT_BUILT": ("the facility is real and operating, but the two footprints the solver "
                       "committed to are not built yet — so a schedule for them would describe "
                       "buildings that do not exist"),
    "MIXED_ROOF_AND_GRADE": ("some cooling plant is at ground level and some is on the roof, so a "
                             "2 m field describes only part of what this facility breathes — the "
                             "model cannot say which part without knowing the split, and it will "
                             "not guess"),
}


def facility_verdict(key):
    """(verdict, assessed) from this facility's OWN frame manifest. Never inferred.

    `assessed` matches `metros.export_manifest()`'s rule exactly -- a verdict counts only when an
    assessor is named and it is not the placeholder. A frame with nobody's judgement on it is not a
    screening (gotcha #184), so it can neither refuse a facility nor remove it from the map.
    """
    p = os.path.join(M.imagery_dir(key), "screen_manifest.json")
    if not os.path.exists(p):
        return None, False
    try:
        sm = json.load(open(p, encoding="utf-8"))
    except (ValueError, OSError):
        return None, False
    v = sm.get("architecture_verdict") or "NOT SCREENED"
    return v, bool(sm.get("assessed_by")) and v != "NOT YET ASSESSED"


def load_metro_selected(key):
    fp = M.geom_path("selected_site.json", key)
    if not os.path.exists(fp):
        return None
    return json.load(open(fp, encoding="utf-8"))


def main():
    clusters = json.load(open(CLUSTERS_FILE, encoding="utf-8"))["clusters"]
    sites_doc = json.load(open(SITES_FILE, encoding="utf-8"))
    groups_doc = json.load(open(ISOLATION_FILE, encoding="utf-8"))["groups"]
    verdicts = json.load(open(VERDICTS_FILE, encoding="utf-8"))["verdicts"]

    # OSM id -> which registry entry holds it (an entry's own osm_ids list)
    osm_to_entry = {}
    for ekey, e in clusters.items():
        for wid in e["osm_ids"]:
            osm_to_entry[wid] = ekey

    # OSM id -> which real building-group it landed in (for the isolated/clear/refused verdict)
    osm_to_group = {}
    for gkey, g in groups_doc.items():
        for wid in g["members"]:
            osm_to_group[wid] = gkey

    # 🔴 A METRO'S COMMITTED PAIR CAN SPAN TWO DIFFERENT DISCOVERY-GRID ENTRIES, AND DID: Chicago's
    # real 118.4 m facade gap straddles a ~11 km grid-cell boundary, so its source and receptor
    # were recorded as two SEPARATE registry entries -- and the first version of this script
    # emitted TWO "fully_built" dots for one real site. A metro's map position must come from its
    # own authoritative committed geometry (`metros.site_centre()`, the same value `agent.py`
    # itself uses), never from re-deriving it out of the discovery grid. Every registry entry that
    # is PART OF a known metro is absorbed and skipped -- one metro, one dot, always.
    absorbed_entry_keys = set()
    metro_dots = []
    for site in sites_doc["sites"]:
        # ONLY THE HAND-BUILT METROS ARE "ABSORBED" HERE. This loop exists to fold the 5 metros into
        # the national registry by OSM id so they are never counted or drawn twice (gotcha #154).
        # A NATIONAL facility is already IN that registry -- it IS a registry entry -- so absorbing
        # it would be absorbing it into itself, and `M.METROS[site["key"]]` below raised a KeyError
        # the moment one became offerable and appeared in `sites.json`.
        if site.get("national") or site["key"] not in M.METROS:
            continue
        sel = load_metro_selected(site["key"])
        if not sel:
            continue
        ids = ["way/%s" % sel["selected"]["source_osm_id"], "way/%s" % sel["selected"]["receptor_osm_id"]]
        entry_keys = {osm_to_entry[i] for i in ids if i in osm_to_entry}
        absorbed_entry_keys.update(entry_keys)
        centre = list(M.site_centre(site["key"]))
        n_tagged = sum(clusters[ek]["n_tagged"] for ek in entry_keys if ek in clusters)
        ops = sorted({op for ek in entry_keys if ek in clusters
                      for op in clusters[ek].get("operators", [])})
        names = sorted({nm for ek in entry_keys if ek in clusters
                        for nm in clusters[ek].get("sample_names", [])})
        if site["offerable"]:
            status, detail = "fully_built", "Full agent run, FortyGuard field purchased."
        else:
            status = "refused_known"
            detail = "REFUSED (%s): %s" % (site.get("scope_verdict"),
                                           site.get("not_offerable_because") or "")
        metro_dots.append({
            "key": "metro_%s" % site["key"], "state": M.METROS[site["key"]]["state"],
            "category": "cluster", "n_tagged": n_tagged or 2, "centre": centre,
            "operators": ops[:8], "sample_names": names[:5],
            "status": status, "detail": detail, "metro_key": site["key"], "label": site["label"],
        })

    # ---- ONE DOT PER FACILITY, NOT PER DISCOVERY CELL ------------------------------------------
    # 🔴 THE MAP AND THE PHYSICS WERE COUNTING DIFFERENT THINGS. This loop used to walk
    # `dc_clusters.json`, whose key is a ~11 km DISCOVERY GRID CELL -- a convenience for batching
    # Overpass queries that gotchas #150 and #152 both show is not a measurement of anything. One
    # cell can hold 81 buildings or one, so "hover a dot and see the exact data centre" could only
    # ever show a SAMPLE of what was under the cursor.
    # `national_registry.json` is keyed by the unit the solver actually works on: the connected
    # component of buildings inside its validated 600 m range. A campus is one facility, a lone hall
    # is one facility. 639 of them, each with its own measured centroid, timezone and state.
    #
    # `metro_key` IS SET FOR A BUILT FACILITY, and that is what makes the map click and the search
    # box work: both resolve a site through `sites.json` by that key, so a facility becomes
    # clickable the moment it has artefacts, with no further change here.
    registry = json.load(open(REGISTRY_FILE, encoding="utf-8"))["facilities"]
    offerable = {}
    for s in sites_doc["sites"]:
        offerable[s["key"]] = s
    absorbed_groups = set()
    for site in sites_doc["sites"]:
        if site.get("national") or site["key"] not in M.METROS:
            continue
        sel = load_metro_selected(site["key"])
        if not sel:
            continue
        for oid in ("source_osm_id", "receptor_osm_id"):
            v = sel["selected"].get(oid)
            if v and ("way/%s" % v) in osm_to_group:
                absorbed_groups.add(osm_to_group["way/%s" % v])

    out_sites = list(metro_dots)
    dropped_absent = []
    for gkey, f in registry.items():
        if gkey in absorbed_groups:
            continue                      # already drawn as one of the 5 hand-built metro dots
        kind = f["kind"]
        row = offerable.get(gkey)
        built = bool(row and row.get("offerable"))

        # 🔴 A FACILITY THAT IS NOT AN OPERATING DATA CENTRE IS REMOVED FROM THE MAP ENTIRELY.
        # Not greyed, not labelled -- absent. The user's standing rule, recorded in HANDOFF 3.4:
        # "never claim a data centre that does not exist." A dot on a national map IS that claim,
        # and a reader who hovers it is being told a data centre is there.
        #
        # THE DISTINCTION THAT MATTERS, and it is not the same as `offerable`:
        #   NOT_BUILT / NOT_A_DATA_CENTRE -> the facility does not exist as an operating data
        #        centre. Excluded here, so it is absent from the map, the search box and the picker
        #        (all three read this file or the manifest).
        #   ROOFTOP / anything else out of scope -> the data centre IS REAL and IS OPERATING; what
        #        fails is our model's domain, because a 2 m field does not describe air that a
        #        roof-mounted plant breathes. Those STAY VISIBLE and carry their refusal, exactly
        #        as Santa Clara does -- refusing on evidence is the project's most credible claim
        #        and hiding it would throw that away.
        # Read from the facility's OWN frame manifest, the same file `metros.export_manifest()`
        # reads for the offerable gate, so the two cannot disagree about a verdict.
        av, a_assessed = facility_verdict(gkey)
        if a_assessed and av in ABSENT_VERDICTS:
            dropped_absent.append((gkey, av))
            continue
        if built:
            status = "built_national"
            detail = ("Full agent run on this facility's own geometry, its own %s weather record "
                      "and its own state's tariff. %s"
                      % (row.get("station") or "assigned", row.get("scope_verdict") == "NOT SCREENED"
                         and "Aerial imagery NOT YET SCREENED -- see the caveat on its page."
                         or "Imagery screened."))
        elif a_assessed:
            # REAL, OPERATING, AND REFUSED ON EVIDENCE -- shown, never hidden. This is the Santa
            # Clara case at national scale: the plant is roof-mounted, so FortyGuard's 2 m field
            # does not describe the air it breathes, and this model has nothing true to say about
            # it. Stating that is worth more than a silently shorter list.
            status = "refused_scope"
            # THIS SITE'S OWN REASON, from REFUSAL_REASON above -- never a generic one. If a verdict
            # arrives that has no reason registered, the sentence says so instead of inventing one:
            # an unexplained refusal is better than a confidently wrong explanation (#67).
            why = REFUSAL_REASON.get(av)
            detail = ("A real data centre, REFUSED by the imagery screening gate: %s — %s. Shown "
                      "rather than hidden, because refusing on evidence is a result, not a gap."
                      % (av, why or ("no reason is registered for this verdict in "
                                     "export_unified_map.REFUSAL_REASON, so none is asserted here")))
        elif kind == "standalone":
            status = "standalone"
            detail = f["plume"]["reason"]
        elif kind == "paired_clear":
            status = "paired_clear"
            detail = ("A real internal pair clears the %.0f m facade floor (%.1f m measured), so "
                      "the plume can be solved on its own footprints. Not yet built."
                      % (60.0, f["plume"]["facade_gap_m"] or -1))
        elif kind == "paired_advisory":
            status = "paired_advisory"
            detail = f["plume"]["reason"]
        else:
            status = kind                 # boundary_only / below_model_scale
            detail = f["plume"]["reason"]
        out_sites.append({
            "key": gkey, "state": f["state"],
            # CATEGORY still drives marker radius, so it is derived from the real building count
            # rather than inherited from the discovery grid's own guess.
            "category": ("cluster" if f["n_buildings"] >= 3
                         else "pair" if f["n_buildings"] == 2 else "single"),
            "n_tagged": f["n_buildings"],
            "centre": f["centre"], "operators": f.get("operators", []),
            "sample_names": f.get("names", []),
            "kind": kind,
            "longest_facade_m": f.get("longest_facade_m"),
            "nearest_other_tagged_dc_m": f["plume"].get("nearest_other_tagged_dc_m"),
            "status": status, "detail": detail,
            "metro_key": gkey if built else None,
            "label": row.get("label") if row else None,
        })

    counts = {}
    for s in out_sites:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    print("=" * 78)
    print("UNIFIED NATIONAL MAP -- %d sites total" % len(out_sites))
    print("=" * 78)
    # NO SILENT EXCLUSION. A map that quietly got shorter is indistinguishable from a map that
    # never had those facilities, and gotcha #176's rule is that a check with no visible failure is
    # decoration. Every dropped facility is named, with the verdict that dropped it.
    if dropped_absent:
        print("   EXCLUDED as not an operating data centre (%d):" % len(dropped_absent))
        for k, v in sorted(dropped_absent):
            print("      %-22s %s" % (k, v))
        print()
    for k, v in sorted(counts.items()):
        print("   %-20s %d" % (k, v))

    os.makedirs(DEMO, exist_ok=True)
    json.dump({"generated_by": "src/export_unified_map.py", "n_sites": len(out_sites),
              "counts": counts, "sites": out_sites},
             open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
