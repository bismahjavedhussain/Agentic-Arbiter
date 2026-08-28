# -*- coding: utf-8 -*-
"""S7b -- WIRE THE PURCHASED AOI FIELDS TO THE FACILITIES THEY ACTUALLY COVER.

    python wire_national_fields.py plan     # FREE, no writes. What it would wire, and what it drops.
    python wire_national_fields.py run      # write the assignment side-car

ZERO API CALLS. This reads what has already been bought and decides which facility may read which
field. It never fetches anything.

--------------------------------------------------------------------------------------------
WHY THIS STAGE EXISTS
--------------------------------------------------------------------------------------------
`testing/buy_national_fields.py` writes each purchased AOI to `data/national_fields/<AOI>.json`.
Nothing read that directory. `build_national_registry.py:53` had already anticipated the gap --
*"`fortyguard_field: null` -- ABSENT, explicitly, so a later stage fills them in"* -- and the later
stage was never written, so `metros.national_entry()` returned a hard `None` and every national
facility published `has_own_fortyguard_field: false` no matter what had been bought for it.

That is the Chicago defect at national scale. One past-window heatmap was purchased for Chicago on
2026-08-19, 17,797 tiles, 4,220 credits, and it sat unused in `testing/results/fixtures/` while the
demo told the reader *"this site has no FortyGuard field of its own"* and showed Ashburn's field
instead. Measured 2026-08-25: 40 AOI fields on disk, 168,800 credits, reaching zero sites.

--------------------------------------------------------------------------------------------
WHAT "COVERS" MEANS, AND WHY IT IS MEASURED RATHER THAN ASSUMED
--------------------------------------------------------------------------------------------
The obvious test is "is the facility inside the 8x8 km box we asked for", using
`buy_national_fields.SIDE_KM`. This does NOT do that, for a reason this codebase keeps relearning:
a constant that describes a delivered artefact drifts away from it. The box was what we REQUESTED;
what arrived is a set of tile centroids, and those are the only thing the panel can draw.

So coverage is computed from the DELIVERED tiles: a facility is covered when its centre lies inside
the bounding box of the tile centroids the vendor actually returned, and the distance from the
field's own centre is recorded alongside so a reader can see how central the reading is. If the
vendor ever returns a clipped or shifted field, this notices; a side-length constant could not.

--------------------------------------------------------------------------------------------
ONE FIELD, MANY FACILITIES -- STATED, NOT HIDDEN
--------------------------------------------------------------------------------------------
An 8x8 km AOI over a data-centre cluster covers many facilities: rank #1 covers 111 tagged
buildings. This does not pretend each of them was bought its own field. The assignment records the
AOI key, how many facilities share it, and the facility's distance from the field centre, and the
provenance sentence says "shared" in as many words -- so `has_own_fortyguard_field: true` means
"there is a real, paid field covering this site", never "this site was bought a private one".

A facility that no purchased field covers gets NO assignment and keeps saying it has none. That is
the whole point of the exercise and the one outcome this file must never fudge.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")
FIELDS_DIR = os.path.join(IA, "data", "national_fields")
OUT = os.path.join(GEOM, "national_field_assignments.json")

sys.path.insert(0, HERE)
import metros as M                                                    # noqa: E402


def tile_bbox_and_count(raw):
    """(min_lat, min_lon, max_lat, max_lon, n) over the DELIVERED tile centroids, or None.

    The centroid of each tile's first ring, which is what `agent.export_field` also draws from, so
    the area this reports is the area the panel can actually render -- not the area we asked for.
    """
    feats = ((raw or {}).get("map_data") or {}).get("features") or []
    if not feats:
        return None
    mnla = mnlo = 1e18
    mxla = mxlo = -1e18
    n = 0
    for f in feats:
        try:
            ring = f["geometry"]["coordinates"][0][:4]
        except (KeyError, IndexError, TypeError):
            continue
        la = sum(p[1] for p in ring) / 4.0
        lo = sum(p[0] for p in ring) / 4.0
        mnla, mxla = min(mnla, la), max(mxla, la)
        mnlo, mxlo = min(mnlo, lo), max(mxlo, lo)
        n += 1
    return None if not n else (mnla, mnlo, mxla, mxlo, n)


def window_sentence(w, tz):
    """The purchased window as prose, because this string is PRINTED ON THE PAGE.

    `buy_national_fields.py` stores the window as the payload dict it sent
    (`{start_date, start_time, end_time, filter_type}`). Interpolating that into a provenance
    sentence renders a Python dict repr -- "{'start_date': '2026-08-24', ..." -- straight into the
    reader's face, which is the same class of defect as a bare `null` leaking into the site picker.
    Formatted here, once, next to the thing that builds the sentence.
    """
    if not isinstance(w, dict):
        return str(w) if w else "window not recorded"
    d = w.get("start_date") or "?"
    a = w.get("start_time") or "?"
    b = w.get("end_time") or "?"
    return "%s %s-%s%s" % (d, a, b, " %s" % tz if tz else "")


def metres_between(a_lat, a_lon, b_lat, b_lon):
    """Local flat-earth separation. Correct to well under a metre at these distances, and the AOI is
    8 km wide -- a great-circle formula here would be precision theatre."""
    dla = (a_lat - b_lat) * 110574.0
    dlo = (a_lon - b_lon) * 111320.0 * math.cos(math.radians((a_lat + b_lat) / 2.0))
    return math.hypot(dla, dlo)


def load_purchased():
    """Every AOI field on disk that actually carries tiles, with its measured extent."""
    out = []
    if not os.path.isdir(FIELDS_DIR):
        return out
    for fn in sorted(os.listdir(FIELDS_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(FIELDS_DIR, fn), encoding="utf-8"))
        except (IOError, OSError, ValueError):
            continue
        bb = tile_bbox_and_count(d.get("raw_result"))
        if not bb:
            # A field file with no drawable tiles is not a field. Reported, never assigned.
            out.append({"aoi_key": d.get("aoi_key") or os.path.splitext(fn)[0], "bbox": None,
                        "n_tiles": 0, "centre": d.get("centre"), "window": d.get("window"),
                        "state": d.get("state"), "rank": d.get("rank")})
            continue
        out.append({"aoi_key": d.get("aoi_key") or os.path.splitext(fn)[0],
                    "bbox": bb[:4], "n_tiles": bb[4], "centre": d.get("centre"),
                    "window": window_sentence(d.get("window"), d.get("tz")),
                    "state": d.get("state"), "rank": d.get("rank")})
    return out


def assign():
    """facility key -> its covering field, plus the reasons anything was skipped."""
    fields = [f for f in load_purchased() if f["bbox"]]
    empty = [f["aoi_key"] for f in load_purchased() if not f["bbox"]]
    facilities = M.national_registry()

    chosen, uncovered = {}, []
    for key in sorted(facilities):
        c = (facilities[key] or {}).get("centre")
        if not c:
            continue
        la, lo = c[0], c[1]
        hits = []
        for f in fields:
            mnla, mnlo, mxla, mxlo = f["bbox"]
            if mnla <= la <= mxla and mnlo <= lo <= mxlo:
                fc = f["centre"] or [(mnla + mxla) / 2.0, (mnlo + mxlo) / 2.0]
                hits.append((metres_between(la, lo, fc[0], fc[1]), f))
        if not hits:
            uncovered.append(key)
            continue
        # NEAREST FIELD CENTRE WINS when several AOIs overlap this facility. The tile a reader
        # hovers is interpolated from the delivered lattice, and a facility near a field's edge sits
        # in a corner of it -- so of two real answers, the more central one is the better reading.
        hits.sort(key=lambda t: t[0])
        d_m, f = hits[0]
        chosen[key] = {"aoi_key": f["aoi_key"], "n_tiles": f["n_tiles"],
                       "field_centre": f["centre"], "window": f["window"],
                       "aoi_rank": f["rank"], "aoi_state": f["state"],
                       "metres_from_field_centre": round(d_m, 1),
                       "n_overlapping_fields": len(hits)}
    # How many facilities share each field -- needed for the provenance sentence to be honest.
    share = {}
    for v in chosen.values():
        share[v["aoi_key"]] = share.get(v["aoi_key"], 0) + 1
    for key, v in chosen.items():
        v["facilities_sharing_this_field"] = share[v["aoi_key"]]
        v["provenance"] = (
            "purchased -- 1 past-window FortyGuard heatmap over AOI %s (rank %s, %s), %s tiles, "
            "%s. This field covers %d facility(ies) and is SHARED between them; this site's centre "
            "is %s m from the field centre. It buys the spatial picture and the tile statistics, "
            "not a forecast leg -- so it carries no level offset and no coverage record."
            % (v["aoi_key"], v["aoi_rank"], v["aoi_state"], format(v["n_tiles"], ","),
               v["window"], v["facilities_sharing_this_field"],
               format(v["metres_from_field_centre"], ",")))
    return chosen, uncovered, fields, empty


def main(argv):
    cmd = argv[0].lower() if argv else "plan"
    if cmd not in ("plan", "run"):
        raise SystemExit("commands: plan | run")

    chosen, uncovered, fields, empty = assign()
    print("=" * 78)
    print("S7b -- WIRE PURCHASED AOI FIELDS TO FACILITIES.  ZERO API CALLS.")
    print("=" * 78)
    print("   purchased fields on disk   : %d  (%d with drawable tiles, %d empty)"
          % (len(fields) + len(empty), len(fields), len(empty)))
    if empty:
        print("      empty, NOT assigned     : %s" % ", ".join(empty[:8]))
    print("   facilities in the registry : %d" % len(M.national_registry()))
    print("   facilities now covered     : %d" % len(chosen))
    print("   facilities still uncovered : %d  (they keep saying they have no field)"
          % len(uncovered))

    if chosen:
        share = {}
        for v in chosen.values():
            share.setdefault(v["aoi_key"], []).append(v)
        print("\n   fields carrying the most facilities:")
        for aoi in sorted(share, key=lambda a: -len(share[a]))[:10]:
            vs = share[aoi]
            far = max(v["metres_from_field_centre"] for v in vs)
            print("      %-10s %3d facility(ies)   %s tiles   furthest %s m from centre"
                  % (aoi, len(vs), format(vs[0]["n_tiles"], ","), format(far, ",")))

    if cmd == "plan":
        print("\n   PLAN ONLY. Nothing written. Run `run` to write the side-car.")
        print("=" * 78)
        return 0

    obj = {"generated_by": "AGENTIC-ARBITER/src/wire_national_fields.py",
           "api_calls_made": 0,
           "coverage_rule": ("a facility is covered when its centre lies inside the bounding box "
                             "of the tile centroids the vendor actually DELIVERED, not inside the "
                             "box that was requested; of several overlapping fields the one whose "
                             "centre is nearest wins"),
           "n_fields": len(fields), "n_covered": len(chosen), "n_uncovered": len(uncovered),
           "assignments": chosen}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(obj, open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   wrote %s" % OUT)
    print("   next: `python metros.py --manifest` to republish, then rebuild the covered sites")
    print("         so their traces export the field they can now see.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
