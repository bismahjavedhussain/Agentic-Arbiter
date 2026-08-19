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
                                             headers={"User-Agent": "INTAKE-ARBITER/1.0"})
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

    allc = {}
    for st in states:
        print("   %s ..." % st, end=" ", flush=True)
        d = fetch(STATE_BBOX[st])
        if not d:
            print("FAILED")
            continue
        els = [e for e in d.get("elements", []) if e.get("center")]
        print("%d tagged data-centre ways" % len(els))
        cells = defaultdict(list)
        for e in els:
            c = e["center"]
            key = (math.floor(c["lat"] / CELL_DEG), math.floor(c["lon"] / CELL_DEG))
            cells[key].append(e)
        for key, members in cells.items():
            if len(members) < MIN_CLUSTER:
                continue
            lats = [m["center"]["lat"] for m in members]
            lons = [m["center"]["lon"] for m in members]
            ops = sorted({(m.get("tags") or {}).get("operator") for m in members} - {None})
            names = sorted({(m.get("tags") or {}).get("name") for m in members} - {None})
            allc["%s_%.2f_%.2f" % (st, min(lats), min(lons))] = {
                "state": st, "n_tagged": len(members),
                "lat_range": [min(lats), max(lats)], "lon_range": [min(lons), max(lons)],
                "centre": [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2],
                # a bbox padded to ~8 km, matching the scale the solver pipeline wants
                "suggested_bbox": [round(min(lats) - 0.012, 4), round(min(lons) - 0.015, 4),
                                   round(max(lats) + 0.012, 4), round(max(lons) + 0.015, 4)],
                "operators": ops[:8], "sample_names": names[:5]}

    ranked = sorted(allc.items(), key=lambda kv: -kv[1]["n_tagged"])
    print("\n   CLUSTERS WITH >= %d TAGGED DATA CENTRES, ranked by count" % MIN_CLUSTER)
    print("   %-4s %6s  %-19s %-34s %s" % ("st", "tagged", "centre lat,lon", "operators", "bbox"))
    for k, c in ranked[:26]:
        print("   %-4s %6d  %8.4f,%9.4f  %-34s %s"
              % (c["state"], c["n_tagged"], c["centre"][0], c["centre"][1],
                 (", ".join(c["operators"]) or "-")[:34],
                 ",".join("%.3f" % v for v in c["suggested_bbox"])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/discover_dc_clusters.py", "api_calls_made": 0,
               "source": "OpenStreetMap via Overpass (ODbL). No FortyGuard credential used.",
               "tag_filter": "telecom=data_center OR building=data_center",
               "caveat": "crowd-sourced tagging; counts are a LOWER BOUND and are not evidence "
                         "about market size",
               "cell_deg": CELL_DEG, "min_cluster": MIN_CLUSTER,
               "states_searched": states, "clusters": allc},
              open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s  (%d clusters)" % (OUT, len(allc)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
