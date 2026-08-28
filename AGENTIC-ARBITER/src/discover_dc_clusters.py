# -*- coding: utf-8 -*-
"""FIND DATA-CENTRE CLUSTERS FROM OPENSTREETMAP, instead of guessing where they are.

    python discover_dc_clusters.py AZ IL CA        # states to search
    python discover_dc_clusters.py --all           # every state in STATE_BBOX

FREE, KEYLESS. Overpass + OSM (ODbL). NO FortyGuard credential is read or used.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS -- a guess of mine that the data refuted
--------------------------------------------------------------------------------------------
`metros.py` first carried a Phoenix bounding box I picked from memory. Running the geometry fetch
over it returned, as its ten largest buildings: **Chandler Fashion Center, a Dillards distribution
centre, a Walmart Supercenter and a beverage distributor.** Retail and warehousing. Not one data
centre. The area filter (8,000-400,000 m2) cannot tell a hyperscale hall from a shopping mall,
because on footprint alone they look alike -- and I was one step from pointing a 4,220-credit
FortyGuard call at a mall.

The Ashburn set shows the honest way to do this: **96 of its 128 buildings carry
`telecom=data_center` and 82 carry `building=data_center`.** OSM already knows where data centres
are. So this asks OSM, clusters what comes back, and emits bounding boxes DERIVED from the answer.

    A bbox chosen from memory is an assumption. A bbox derived from tagged footprints is a
    measurement, and it can be re-run and checked.

--------------------------------------------------------------------------------------------
WHAT IT DOES NOT CLAIM
--------------------------------------------------------------------------------------------
OSM tagging is crowd-sourced and incomplete: a hall tagged only `building=industrial` will be
missed, so these counts are a LOWER BOUND on how many data centres a place holds. That is fine for
the purpose -- we need somewhere with several tagged, large, close-together halls, and a cluster
that clears that bar is usable whether or not its neighbours are tagged. It is NOT evidence about
market size and is not used as any.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data", "geometry", "dc_clusters.json")

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Coarse state boxes, only to scope the Overpass query. Approximate on purpose: the CLUSTERS that
# come back are what matters, and they are computed from returned centroids, not from these edges.
STATE_BBOX = {
    "VA": (36.5, -83.7, 39.5, -75.2),
    "AZ": (31.3, -114.9, 37.0, -109.0),
    "IL": (36.9, -91.6, 42.6, -87.0),
    "CA": (32.5, -124.5, 42.1, -114.1),
    "TX": (25.8, -106.7, 36.6, -93.5),
    "OR": (41.9, -124.6, 46.3, -116.4),
    "OH": (38.4, -84.9, 42.0, -80.5),
    "UT": (36.9, -114.1, 42.0, -109.0),
    "NV": (35.0, -120.0, 42.0, -114.0),
    "GA": (30.3, -85.7, 35.0, -80.8),
    # ---- ADDED 2026-08-23 for the national build. The ten above were the markets screened by
    # hand; these are the rest of the country, so `--all` means the United States and not
    # "the ten states someone thought of". Still coarse and still overlapping ON PURPOSE (see the
    # note above) -- overlap is now harmless because the state is MEASURED per cluster below.
    "AL": (30.1, -88.5, 35.1, -84.8), "AR": (33.0, -94.7, 36.6, -89.6),
    "CO": (36.9, -109.1, 41.1, -102.0), "CT": (40.9, -73.8, 42.1, -71.7),
    "DC": (38.7, -77.2, 39.0, -76.8), "DE": (38.4, -75.8, 39.9, -74.9),
    "FL": (24.3, -87.7, 31.1, -79.9), "IA": (40.3, -96.7, 43.6, -90.1),
    "ID": (41.9, -117.3, 49.1, -110.9), "IN": (37.7, -88.2, 41.8, -84.7),
    "KS": (36.9, -102.2, 40.1, -94.5), "KY": (36.4, -89.6, 39.2, -81.9),
    "LA": (28.9, -94.1, 33.1, -88.7), "MA": (41.2, -73.6, 43.0, -69.8),
    "MD": (37.8, -79.6, 39.8, -74.9), "ME": (43.0, -71.2, 47.5, -66.8),
    "MI": (41.6, -90.5, 48.4, -82.3), "MN": (43.4, -97.3, 49.5, -89.4),
    "MO": (35.9, -95.9, 40.7, -89.0), "MS": (30.1, -91.7, 35.1, -88.0),
    "MT": (44.3, -116.2, 49.1, -103.9), "NC": (33.7, -84.4, 36.7, -75.3),
    "ND": (45.8, -104.1, 49.1, -96.5), "NE": (39.9, -104.1, 43.1, -95.2),
    "NH": (42.6, -72.6, 45.4, -70.5), "NJ": (38.8, -75.6, 41.4, -73.8),
    "NM": (31.3, -109.1, 37.1, -102.9), "NY": (40.4, -79.8, 45.1, -71.8),
    "OK": (33.6, -103.1, 37.1, -94.4), "PA": (39.6, -80.6, 42.4, -74.6),
    "RI": (41.1, -71.9, 42.1, -71.0), "SC": (32.0, -83.4, 35.3, -78.4),
    "SD": (42.4, -104.1, 46.0, -96.4), "TN": (34.9, -90.4, 36.8, -81.6),
    "VT": (42.6, -73.5, 45.1, -71.4), "WA": (45.5, -124.9, 49.1, -116.8),
    "WI": (42.4, -93.0, 47.2, -86.7), "WV": (37.1, -82.7, 40.7, -77.6),
    "WY": (40.9, -111.1, 45.1, -104.0),
}

# ---------------------------------------------------------------------------------------------
# 🔴 THE STATE MUST BE MEASURED, NOT INHERITED FROM THE QUERY BOX.
#
# This file used to record `"state": st` -- the state whose bbox happened to return the cluster.
# The boxes above overlap deliberately, so the FIRST state searched claims everything in the
# overlap, and the 2026-08-23 registry proved it: `CA_36.06_-115.22` is "Switch Las Vegas 10",
# in NEVADA, and `CA_39.57_-119.55` is Reno. Both were labelled CA because California's box was
# searched first and reaches to -114.1.
#
# That is not cosmetic. `money.prices_for_metro()` selects the electricity tariff on
# METROS[k]["state"], so a Nevada campus would have been priced on California power -- and the
# money panel is the commercial argument. Gotcha #64: having built the measurement, use its output.
#
# So the state is reverse-geocoded from the cluster's own centroid, cached on disk (the answer for
# a fixed coordinate never changes), and rate-limited to Nominatim's published 1 req/s. If the
# lookup fails the state is recorded as None and SAID to be unresolved -- never guessed, because a
# guessed state silently picks a tariff.
NOMINATIM = "https://nominatim.openstreetmap.org/reverse"
STATE_CACHE = os.path.join(ROOT, "data", "geometry", "state_by_coord.json")
UA = "AGENTIC-ARBITER/1.0 (FortyGuard Hackathon 2026; data-centre siting research)"
_LAST_NOMINATIM = [0.0]


def _load_state_cache():
    try:
        return json.load(open(STATE_CACHE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def resolve_geo(lat, lon, cache=None):
    """The USPS state code the coordinate is REALLY in, plus enough to tell WHY it has none.

    Returns a dict: {"state": "NV" or None, "country": "us"/"ca"/... or None,
    "reason": None (resolved) | "outside_united_states" | "geocode_failed"}.

    🔴 THIS USED TO RETURN JUST A STATE STRING OR None, AND THAT COLLAPSED TWO DIFFERENT THINGS
    INTO ONE VALUE: "Nominatim could not be reached" and "this coordinate genuinely is not in the
    United States" both showed up as state=null, indistinguishable. The first national run found
    two real clusters -- 13 tagged buildings, real names (Cologix TOR4, Equinix Markham TR5) --
    that were Toronto and Markham, ONTARIO, CANADA, because the NY state bbox (its northern edge is
    45.1 deg) reaches well north of the border. Both surfaced as "unresolved state" identically to a
    genuine network failure, which would have let a real CANADIAN data centre sit in a "US data
    centres" registry with no flag distinguishing it from a US site whose lookup simply needs a
    retry. The failure mode this project has hit before (gotcha #64) is trusting a filter that
    cannot tell a real negative from a null result -- this is that, one field over.
    Any state box near a border (WA/ND/MT/ME/NY here; also plausible near TX/AZ/CA and Mexico)
    has the same exposure, so the fix is general, not a two-entry patch.
    """
    cache = _load_state_cache() if cache is None else cache
    key = "%.4f,%.4f" % (lat, lon)
    if key in cache and isinstance(cache[key], dict) and "reason" in cache[key]:
        return cache[key]                     # legacy plain string/None cache entries are RE-looked
    wait = 1.05 - (time.time() - _LAST_NOMINATIM[0])
    if wait > 0:
        time.sleep(wait)                       # Nominatim's published limit is 1 req/s. Respect it.
    url = "%s?lat=%.6f&lon=%.6f&format=json&zoom=5&addressdetails=1" % (NOMINATIM, lat, lon)
    out = {"state": None, "country": None, "reason": "geocode_failed"}
    try:
        rq = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(rq, timeout=30) as r:
            addr = (json.load(r) or {}).get("address") or {}
        cc = (addr.get("country_code") or "").lower() or None
        out["country"] = cc
        if cc and cc != "us":
            out["reason"] = "outside_united_states"
        else:
            # ISO3166-2-lvl4 is "US-NV" and unambiguous; `state` is a display name that varies
            # ("Washington" vs "State of Washington"), so it is only the fallback.
            iso = addr.get("ISO3166-2-lvl4") or ""
            if iso.startswith("US-") and len(iso) == 5:
                out["state"] = iso[3:]
            elif addr.get("state"):
                out["state"] = US_STATE_BY_NAME.get(addr["state"].strip().lower())
            out["reason"] = None if out["state"] else "geocode_failed"
    except Exception as e:                                            # noqa: BLE001
        print("      state lookup failed for %s: %s" % (key, e))
    _LAST_NOMINATIM[0] = time.time()
    cache[key] = out
    try:
        os.makedirs(os.path.dirname(STATE_CACHE), exist_ok=True)
        # allow_nan=False even though this cache holds only strings/nulls/dicts: the rule is
        # source-level and blanket (gotcha #43) precisely so nobody has to be right about which
        # writers "cannot" emit NaN. audit.py caught this one within a minute of it being written.
        json.dump(cache, open(STATE_CACHE, "w", encoding="utf-8"), indent=1, sort_keys=True,
                  allow_nan=False)
    except OSError:
        pass
    return out


US_STATE_BY_NAME = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district of columbia": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

MIN_AREA_M2 = 8000.0        # the same floor the solver pipeline uses
CELL_DEG = 0.10             # ~11 km cells; a campus fits inside one
MIN_CLUSTER = 3             # fewer than three tagged halls is not a cluster worth a paid call


def q(bbox):
    s, w, n, e = bbox
    # `out center tags` returns a centroid per way instead of full geometry -- a fraction of the
    # payload, which is what makes a state-sized query practical.
    return f"""
[out:json][timeout:300];
(
  way["telecom"="data_center"]({s},{w},{n},{e});
  way["building"="data_center"]({s},{w},{n},{e});
);
out center tags;
""".strip()


def fetch(bbox, tries=3):
    body = urllib.parse.urlencode({"data": q(bbox)}).encode()
    for i in range(tries):
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=body,
                                             headers={"User-Agent": "AGENTIC-ARBITER/1.0"})
                return json.loads(urllib.request.urlopen(req, timeout=330).read())
            except Exception as e:
                print("      %s: %s" % (ep.split("//")[1].split("/")[0], str(e)[:70]))
        time.sleep(5 * (i + 1))
    return None


def main(argv):
    states = [a.upper() for a in argv if not a.startswith("-")]
    if "--all" in argv or not states:
        states = list(STATE_BBOX)
    bad = [s for s in states if s not in STATE_BBOX]
    if bad:
        raise SystemExit("unknown state(s): %s. Known: %s" % (bad, ", ".join(STATE_BBOX)))

    print("=" * 78)
    print("DATA-CENTRE CLUSTER DISCOVERY from OpenStreetMap. Free, keyless, no credential.")
    print("=" * 78)
    print("   Tag filter: telecom=data_center OR building=data_center")
    print("   These counts are a LOWER BOUND -- an untagged hall is invisible here.\n")

    # 🔴 ACCUMULATE ACROSS EVERY STATE FIRST, DEDUPED BY OSM ID, AND CLUSTER ONCE AT THE END.
    # The per-state loop used to cluster and emit inside the loop, keyed by the QUERY state. With
    # 49 overlapping boxes that double-counts every campus in an overlap: Las Vegas is inside both
    # CA's box and NV's, so it would emit as `CA_36.06_-115.22` AND `NV_36.06_-115.22` -- two
    # entries, same buildings, and the national count inflated by exactly the overlaps. Dedupe on
    # the OSM element id, which is the identity OSM itself guarantees.
    seen = {}                     # osm id -> element, so one building is one building
    found_in = defaultdict(set)   # osm id -> which state QUERIES returned it (evidence, not truth)
    failed = []
    for st in states:
        print("   %s ..." % st, end=" ", flush=True)
        d = fetch(STATE_BBOX[st])
        if not d:
            print("FAILED")
            failed.append(st)
            continue
        els = [e for e in d.get("elements", []) if e.get("center")]
        new = 0
        for e in els:
            oid = "%s/%s" % (e.get("type", "way"), e.get("id"))
            if oid not in seen:
                seen[oid] = e
                new += 1
            found_in[oid].add(st)
        print("%d tagged ways (%d new)" % (len(els), new))

    print("\n   %d distinct tagged data-centre ways nationally (deduped by OSM id)" % len(seen))
    cells = defaultdict(list)
    for oid, e in seen.items():
        c = e["center"]
        cells[(math.floor(c["lat"] / CELL_DEG), math.floor(c["lon"] / CELL_DEG))].append(e)

    # 🔴 MIN_CLUSTER=3 WAS THE ONLY THRESHOLD, AND IT SILENTLY DROPPED TWO REAL CATEGORIES.
    # A cell with exactly 2 tagged data centres is NOT "not a cluster worth a paid call" -- it is
    # exactly what select_site.py's pairwise funnel needs: one source, one receptor. Dropping it at
    # the old ">= 3" line meant every genuine two-building pair anywhere outside the four
    # hand-picked metros was invisible to this registry before it ever reached the funnel.
    # A cell with exactly 1 is the case the user actually asked about: a standalone data centre with
    # no neighbour to recirculate with. That is not "not a cluster" either -- it is a real site with
    # a real, honest, favourable finding (no recirculation risk to model), and the national build
    # cannot claim "majority of US data centres" while silently deleting every one of these.
    # So every cell is emitted now, tagged by what it actually is, and NOTHING with >= 1 tagged
    # building is thrown away before a human or a later stage decides what to do with it.
    print("   %d cells hold >= 1 tagged data centre; resolving each cell's REAL state ONCE from "
          "its centroid, not per building (Nominatim, 1 req/s, cached)\n" % len(cells))

    allc, unresolved, excluded_non_us = {}, [], []
    n_cluster = n_pair = n_single = 0
    scache = _load_state_cache()
    for key, members in cells.items():
        lats = [m["center"]["lat"] for m in members]
        lons = [m["center"]["lon"] for m in members]
        ctr = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
        geo = resolve_geo(ctr[0], ctr[1], scache)
        st_real = geo["state"]
        ops = sorted({(m.get("tags") or {}).get("operator") for m in members} - {None})
        names = sorted({(m.get("tags") or {}).get("name") for m in members} - {None})
        if geo["reason"] == "outside_united_states":
            # NOT "unresolved" -- CONFIRMED not in the United States. The state boxes are
            # deliberately coarse (a comment near STATE_BBOX says so) and several border states'
            # boxes reach past the border (NY's box goes to 45.1 deg N, well into Ontario). A real
            # Toronto/Markham cluster surfaced here on the first national run. This project's own
            # rule is "never claim a data centre that does not exist" -- the sharper form of that
            # for a US-scoped build is "never claim a REAL data centre is a US one when it is not."
            # Recorded with its evidence, not silently dropped, so the exclusion is auditable.
            excluded_non_us.append({"centre": ctr, "country": geo["country"], "n_tagged": len(members),
                                    "sample_names": names[:5], "operators": ops[:8]})
            continue
        queried = sorted(set().union(*(found_in["%s/%s" % (m.get("type", "way"), m.get("id"))]
                                       for m in members)))
        if st_real is None:
            unresolved.append("%.2f,%.2f" % (ctr[0], ctr[1]))
        n = len(members)
        category = "cluster" if n >= MIN_CLUSTER else ("pair" if n == 2 else "single")
        n_cluster += category == "cluster"; n_pair += category == "pair"; n_single += category == "single"
        # 🔴 THE OLD KEY WAS "%s_%.2f_%.2f" % (state, min(lats), min(lons)) -- 2-DECIMAL ROUNDING
        # OF THE MEMBERS' OWN COORDINATES, NOT A GUARANTEED-UNIQUE IDENTIFIER. For a single-member
        # cell that IS just the one building's coordinate rounded to ~1.1 km. Two DIFFERENT
        # standalone data centres in the same state, sitting on opposite sides of a CELL_DEG grid
        # line (so each is correctly its own separate "single" cell) but close enough that their
        # raw coordinates round to the same two decimals, collided on this key -- and one silently
        # overwrote the other. Measured: the loop counted 236 singles; only 235 survived in `allc`.
        # `key` here is the (row, col) grid-cell tuple from `cells` -- unique by construction,
        # because it IS the dict key `cells` was built from. Using it directly makes a collision
        # impossible rather than merely unlikely.
        allc["%s_%d_%d" % (st_real or "XX", key[0], key[1])] = {
            # MEASURED from the centroid, not inherited from whichever box returned it.
            "state": st_real,
            "state_source": "nominatim_reverse_geocode_of_cell_centroid",
            # Kept as evidence: where the boxes disagree with the measurement, that is visible
            # rather than silently resolved. This is the field the old code mistook for the state.
            "state_queries_that_returned_it": queried,
            # "cluster" (>= MIN_CLUSTER tagged halls, campus-style), "pair" (exactly 2 -- a real
            # source/receptor candidate the existing funnel can run on directly), or "single" (one
            # tagged data centre, no OSM-tagged neighbour in this ~11 km cell -- the standalone
            # case; S3/S4 must check NATIONALLY, not just this cell, before calling it isolated).
            "category": category,
            "n_tagged": n,
            "lat_range": [min(lats), max(lats)], "lon_range": [min(lons), max(lons)],
            "centre": ctr,
            # a bbox padded to ~8 km, matching the scale the solver pipeline wants
            "suggested_bbox": [round(min(lats) - 0.012, 4), round(min(lons) - 0.015, 4),
                               round(max(lats) + 0.012, 4), round(max(lons) + 0.015, 4)],
            "operators": ops[:8], "sample_names": names[:5],
            "osm_ids": ["%s/%s" % (m.get("type", "way"), m.get("id")) for m in members]}

    # A KEY COLLISION MUST NEVER SILENTLY SHRINK THIS REGISTRY AGAIN. It already did once: the old
    # key format rounded members' own coordinates to 2 decimals (~1.1 km), and two distinct
    # standalone data centres on opposite sides of a grid boundary collided, one overwriting the
    # other -- the loop counted 236 singles, only 235 survived. Every emitted key is now the
    # cell's own (row, col) grid index, unique by construction, so this exact assertion should
    # never fire again -- it stays as a tripwire for the NEXT key-format change, not this one.
    counted = n_cluster + n_pair + n_single
    if len(allc) != counted:
        raise SystemExit(
            "INTEGRITY FAILURE: %d cells were counted (cluster/pair/single) but only %d survived "
            "in the output dict -- a key collision silently dropped %d real data centre "
            "grouping(s). Do not trust this file; find the collision before re-running."
            % (counted, len(allc), counted - len(allc)))

    if failed:
        print("   !! STATE QUERIES THAT FAILED (re-run them; absence here is not evidence): %s"
              % ", ".join(failed))
    if excluded_non_us:
        print("   !! %d cell(s) EXCLUDED, confirmed OUTSIDE the United States (%s): %s tagged "
              "buildings total -- see excluded_non_us in the output, not silently dropped"
              % (len(excluded_non_us), ", ".join(sorted({e["country"] or "?" for e in excluded_non_us})),
                 sum(e["n_tagged"] for e in excluded_non_us)))
    if unresolved:
        print("   !! %d cell(s) with an UNRESOLVED state (network/geocode failure, NOT confirmed "
              "foreign), recorded as null and keyed XX: %s"
              % (len(unresolved), ", ".join(unresolved[:6])))
        print("     A null state must not be priced -- money.prices_for_metro() falls back and "
              "reports the fallback.")
    print("   %d clusters (>=%d) / %d pairs (==2) / %d singles (==1)"
          % (n_cluster, MIN_CLUSTER, n_pair, n_single))

    ranked = sorted(allc.items(), key=lambda kv: -kv[1]["n_tagged"])
    print("\n   TOP ENTRIES BY TAGGED COUNT (clusters and pairs; singles are the long, flat tail)")
    print("   %-4s %-8s %6s  %-19s %-34s %s"
          % ("st", "kind", "tagged", "centre lat,lon", "operators", "bbox"))
    for k, c in ranked[:26]:
        print("   %-4s %-8s %6d  %8.4f,%9.4f  %-34s %s"
              % (c["state"] or "??", c["category"], c["n_tagged"], c["centre"][0], c["centre"][1],
                 (", ".join(c["operators"]) or "-")[:34],
                 ",".join("%.3f" % v for v in c["suggested_bbox"])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/discover_dc_clusters.py", "api_calls_made": 0,
               "source": "OpenStreetMap via Overpass (ODbL). No FortyGuard credential used.",
               "tag_filter": "telecom=data_center OR building=data_center",
               "caveat": "crowd-sourced tagging; counts are a LOWER BOUND and are not evidence "
                         "about market size",
               "cell_deg": CELL_DEG, "min_cluster": MIN_CLUSTER,
               "category_rule": "cluster: >= %d tagged in one ~11 km cell (campus-style). "
                                 "pair: exactly 2 (a direct source/receptor candidate for "
                                 "select_site.py's existing funnel). single: exactly 1 (no "
                                 "OSM-tagged neighbour in this cell -- S3/S4 must confirm no "
                                 "neighbour NATIONALLY, not just in-cell, before calling it "
                                 "isolated, since the CELL_DEG grid can split two real "
                                 "neighbours across a boundary)." % MIN_CLUSTER,
               "n_clusters": n_cluster, "n_pairs": n_pair, "n_singles": n_single,
               "states_searched": states,
               "states_failed": failed,
               "excluded_non_us": excluded_non_us,
               "excluded_non_us_note": "confirmed by reverse-geocoding the centroid, country != "
                                       "'us' -- NOT the same as an unresolved lookup. State boxes "
                                       "are deliberately coarse and several reach past the border "
                                       "(NY's box extends to 45.1 deg N); the first national run "
                                       "found real Toronto/Markham, Ontario clusters this way. "
                                       "Recorded here, not dropped, so the exclusion is auditable.",
               "state_field": "MEASURED by reverse-geocoding each cell's own centroid, not "
                              "inherited from the query bbox. The boxes overlap, so the old "
                              "query-state label put Las Vegas and Reno in California -- and "
                              "money.prices_for_metro() picks the electricity tariff off it.",
               "deduped_by": "OSM element id, because 49 overlapping state boxes return the same "
                             "campus more than once",
               "n_distinct_tagged_ways": len(seen),
               "clusters": allc},
              open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s  (%d clusters)" % (OUT, len(allc)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
