# -*- coding: utf-8 -*-
"""S4 STEP 4 -- FULL FOOTPRINT RINGS for tagged data-centre buildings.

    python fetch_national_geometry.py           # pairing groups only (1,226 buildings)
    python fetch_national_geometry.py --all     # every tagged building (1,622), INCREMENTALLY

FREE, KEYLESS. Overpass, `way(id:...); out geom;` -- by ID, no bbox scan. Writes
data/geometry/national_geometry.json.

Smaller batches than the centroid fetch (150 vs 300) because `out geom` returns every node of
every way, not one centroid point -- a materially heavier payload per id.

--------------------------------------------------------------------------------------------
WHY `--all`, AND WHY IT IS INCREMENTAL RATHER THAN A RE-FETCH
--------------------------------------------------------------------------------------------
The original run deliberately skipped the 396 isolated buildings: they have no neighbour inside the
solver's validated range, so they need no FACADE GAP measured, and a gap is all this file was for.

That reasoning was right for the gate and wrong for the product. A standalone facility still has to
show the reader ITS OWN building -- the aerial panel draws real OSM footprints over a real
photograph, and with no ring there is nothing to draw. Shipping a standalone site with no footprint
would leave the aerial panel either empty or, far worse, showing the geometry of whatever site was
loaded before it: gotcha #98's exact shape.

⚠ IT ONLY FETCHES IDS NOT ALREADY IN THE OUTPUT FILE, and merges. Overpass is a free, shared,
volunteer-run service and HANDOFF's standing traps list says plainly not to re-run these scripts
casually -- repeated automated load on a free public resource is a real courtesy cost, not just a
rate-limit risk to yourself. Re-fetching 1,226 rings that are already on disk to obtain 396 new ones
would be four times the necessary load for no information. So the existing file is read first and
only the genuinely missing ids are requested: 396 ids, 3 batches, one run.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GROUPS_FILE = os.path.join(IA, "data", "geometry", "national_building_groups.json")
OUT = os.path.join(IA, "data", "geometry", "national_geometry.json")

ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
BATCH_SIZE = 150
PAUSE_BETWEEN_BATCHES_S = 8


def fetch_batch(way_ids, tries=4):
    """One Overpass batch, with a backoff that is actually long enough to matter.

    ⚠ MEASURED 2026-08-24: the original backoff was `5 * (i + 1)` seconds over 3 tries -- 5 s then
    10 s. A real run took `HTTP 429 Too Many Requests` on its third batch and then burned all
    remaining attempts inside 15 seconds, hitting 500/502/504 from both mirrors on the way, and gave
    up with 96 ids unfetched. A 429 is the server saying "you are asking too fast": answering it
    5 seconds later is not a retry, it is the same mistake again, and it adds load to a free
    volunteer-run service at the exact moment it has asked you to stop.

    So the backoff is exponential from a much longer base, and a 429 or a 504 -- the two that mean
    "slow down" rather than "this query is wrong" -- waits longer still. Worst case is a few minutes
    on one batch, against re-running the whole script and re-requesting everything.
    """
    q = "[out:json][timeout:150];way(id:%s);out geom;" % ",".join(way_ids)
    body = urllib.parse.urlencode({"data": q}).encode()
    for i in range(tries):
        throttled = False
        for ep in ENDPOINTS:
            try:
                req = urllib.request.Request(ep, data=body,
                                             headers={"User-Agent": "INTAKE-ARBITER/1.0"})
                return json.loads(urllib.request.urlopen(req, timeout=180).read())
            except Exception as e:                                    # noqa: BLE001
                msg = str(e)[:70]
                if "429" in msg or "504" in msg or "Too Many" in msg:
                    throttled = True
                print("      %s: %s" % (ep.split("//")[1].split("/")[0], msg))
        if i < tries - 1:
            wait = (60 if throttled else 20) * (2 ** i)
            print("      backing off %d s before retry %d/%d%s"
                  % (wait, i + 2, tries, " (throttled)" if throttled else ""))
            time.sleep(wait)
    return None


def main(argv=()):
    want_all = "--all" in argv
    groups_doc = json.load(open(GROUPS_FILE, encoding="utf-8"))
    groups = groups_doc["groups"]
    chosen = groups if want_all else {k: g for k, g in groups.items()
                                      if g["kind"] == "pairing_candidate"}
    all_ids = sorted({m.split("/")[1] for g in chosen.values() for m in g["members"]
                      if m.startswith("way/")})

    # READ WHAT IS ALREADY ON DISK AND FETCH ONLY THE DIFFERENCE. See the module docstring: this is
    # a courtesy decision about a free shared service, not an optimisation.
    rings = {}
    if os.path.exists(OUT):
        try:
            rings = json.load(open(OUT, encoding="utf-8")).get("rings") or {}
        except ValueError:
            rings = {}
    todo = [i for i in all_ids if ("way/%s" % i) not in rings]

    print("=" * 78)
    print("S4 STEP 4 -- FULL RING GEOMETRY, %d buildings across %d group(s)%s"
          % (len(all_ids), len(chosen), " [--all]" if want_all else " [pairing groups only]"))
    print("=" * 78)
    print("   %d ring(s) already on disk; %d to fetch" % (len(rings), len(todo)))
    if not todo:
        print("   nothing to fetch. Not contacting Overpass at all.")

    batches = [todo[i:i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]
    for bi, batch in enumerate(batches, 1):
        print("   batch %d/%d (%d ids)..." % (bi, len(batches), len(batch)), end=" ", flush=True)
        d = fetch_batch(batch)
        if not d:
            print("FAILED -- skipping this batch")
            continue
        got = 0
        for el in d.get("elements", []):
            geom = el.get("geometry")
            if not geom:
                continue
            wid = "way/%s" % el["id"]
            rings[wid] = {"geometry": [[p["lat"], p["lon"]] for p in geom if p],
                          "tags": el.get("tags") or {}}
            got += 1
        print("%d of %d rings returned" % (got, len(batch)))
        if bi < len(batches):
            time.sleep(PAUSE_BETWEEN_BATCHES_S)

    missing = [i for i in all_ids if ("way/%s" % i) not in rings]
    resolved = len(all_ids) - len(missing)
    print("\n   %d of %d requested ids resolved; %d missing. %d rings on disk in total"
          % (resolved, len(all_ids), len(missing), len(rings)))
    if missing:
        print("   missing sample: %s" % ", ".join(missing[:8]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_by": "src/fetch_national_geometry.py", "api_calls_made": 0,
              "source": "OpenStreetMap via Overpass (ODbL), queried by element id, full geometry",
              # `n_requested`/`n_resolved` are about THE SET THIS RUN ASKED FOR, so the pair still
              # reads as "did we get what we wanted". `n_rings_total` is the file's whole contents,
              # which can legitimately exceed the request after an incremental `--all` run -- two
              # different questions that one number used to answer badly.
              "n_requested": len(all_ids), "n_resolved": resolved,
              "n_rings_total": len(rings),
              "scope": "all_tagged_buildings" if want_all else "pairing_groups_only",
              "missing_ids": missing,
              "rings": rings},
             open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("   written: %s" % OUT)
    return 0 if not missing or len(missing) < len(all_ids) * 0.05 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
