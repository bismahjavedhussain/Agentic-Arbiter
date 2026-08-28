# -*- coding: utf-8 -*-
"""S4 STEP 2 -- EVERY TAGGED BUILDING'S OWN COORDINATE, fetched by OSM ID, not a bbox rescan.

    python fetch_national_building_centres.py

FREE, KEYLESS. Overpass, `way(id:...); out center;` -- the same lightweight query shape
`discover_dc_clusters.py` already used, just targeted at the 1,622 specific ids already in the
registry instead of scanning 49 state bounding boxes again. Writes
data/geometry/national_building_centres.json.

--------------------------------------------------------------------------------------------
WHY THIS QUERY SHAPE, AND WHY IT IS RESPECTFUL OF A SHARED FREE SERVICE
--------------------------------------------------------------------------------------------
`classify_isolation.py` (S4 step 1) approximated "does this real location have a neighbour" using
each REGISTRY ENTRY's aggregate bounding box -- but a "cluster" entry (>=3 tagged buildings inside
one ~11 km discovery grid cell) can itself contain buildings that are NOT within the solver's
600 m validated range of each other; the discovery grid's cell size has nothing to do with the
physics gate. Answering G2 correctly needs each building's OWN coordinate, not an aggregate box.

Querying by `id:` list needs no bbox scan at all -- Overpass answers directly from its own
element-id index, which is why this can safely run today even though three full 49-state sweeps
already happened this session and showed real rate-limiting. Batched at 300 ids/request (comfortably
under any practical URL/body limit) with a real pause between batches, exactly the courtesy this
project already applied to the national discovery sweeps.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
CLUSTERS_FILE = os.path.join(IA, "data", "geometry", "dc_clusters.json")
OUT = os.path.join(IA, "data", "geometry", "national_building_centres.json")

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
BATCH_SIZE = 300
PAUSE_BETWEEN_BATCHES_S = 8


def fetch_batch(way_ids, tries=3):
    ids_csv = ",".join(way_ids)
    q = "[out:json][timeout:120];way(id:%s);out center tags;" % ids_csv
    body = urllib.parse.urlencode({"data": q}).encode()
    for i in range(tries):
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=body,
                                             headers={"User-Agent": "AGENTIC-ARBITER/1.0"})
                return json.loads(urllib.request.urlopen(req, timeout=150).read())
            except Exception as e:                                    # noqa: BLE001
                print("      %s: %s" % (ep.split("//")[1].split("/")[0], str(e)[:70]))
        time.sleep(5 * (i + 1))
    return None


def main():
    clusters = json.load(open(CLUSTERS_FILE, encoding="utf-8"))["clusters"]
    all_ids = sorted({i.split("/")[1] for e in clusters.values() for i in e["osm_ids"]
                      if i.startswith("way/")})
    print("=" * 78)
    print("S4 STEP 2 -- PER-BUILDING CENTROIDS, %d tagged ways, by ID (no bbox rescan)"
          % len(all_ids))
    print("=" * 78)

    centres = {}
    batches = [all_ids[i:i + BATCH_SIZE] for i in range(0, len(all_ids), BATCH_SIZE)]
    for bi, batch in enumerate(batches, 1):
        print("   batch %d/%d (%d ids)..." % (bi, len(batches), len(batch)), end=" ", flush=True)
        d = fetch_batch(batch)
        if not d:
            print("FAILED -- skipping this batch, it will be missing from the output")
            continue
        got = 0
        for el in d.get("elements", []):
            c = el.get("center")
            if not c:
                continue
            wid = "way/%s" % el["id"]
            tags = el.get("tags") or {}
            centres[wid] = {"lat": c["lat"], "lon": c["lon"], "name": tags.get("name"),
                            "operator": tags.get("operator")}
            got += 1
        print("%d of %d centres returned" % (got, len(batch)))
        if bi < len(batches):
            time.sleep(PAUSE_BETWEEN_BATCHES_S)

    missing = [i for i in all_ids if ("way/%s" % i) not in centres]
    print("\n   %d of %d ids resolved; %d missing (deleted/merged since discovery, or a batch "
          "failed outright)" % (len(centres), len(all_ids), len(missing)))
    if missing:
        print("   missing sample: %s" % ", ".join(missing[:8]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/fetch_national_building_centres.py", "api_calls_made": 0,
              "source": "OpenStreetMap via Overpass (ODbL), queried by element id",
              "n_requested": len(all_ids), "n_resolved": len(centres), "missing_ids": missing,
              "centres": centres},
             open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("   written: %s" % OUT)
    return 0 if not missing or len(missing) < len(all_ids) * 0.05 else 1


if __name__ == "__main__":
    sys.exit(main())
