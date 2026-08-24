# -*- coding: utf-8 -*-
"""S6 -- ONE AERIAL FRAME PER FACILITY.  FREE, KEYLESS, ZERO FORTYGUARD CALLS.

    python fetch_facility_imagery.py <FACILITY_KEY> [<KEY> ...]
    python fetch_facility_imagery.py --subset          # the prioritised subset file
    python fetch_facility_imagery.py --dryrun <KEY>    # the bbox and URL, no request

WHY A NEW MODULE RATHER THAN A FLAG ON THE EXISTING ONES
    `fetch_imagery.py` fetches ONE hard-wired committed pair into fixed filenames.
    `screen_architecture.py` fetches the top 8 candidates of a metro's `refusal_rank.json` -- a file
    a national facility never produces, because it never runs the pairwise funnel.
    Neither can be pointed at a facility. This is their shape applied to the unit the registry
    actually holds: one facility, one frame, its own directory.

    The ArcGIS request is COPIED EXACTLY from `screen_architecture.py:49-61` -- same endpoint, same
    bboxSR/imageSR, same size, same format, same pads -- because the frames have to be comparable
    with the ones the three shipped sites were screened from. A different zoom would mean a reader
    was judging national sites at a different scale from Ashburn.

--------------------------------------------------------------------------------------------
🔴 WHAT THIS DOES **NOT** DO, AND THE DISTINCTION IS THE WHOLE POINT
--------------------------------------------------------------------------------------------
FETCHING A PHOTOGRAPH IS NOT SCREENING A SITE.

The imagery gate (G5) asks one question: **is the cooling plant at ground level, where FortyGuard's
2 m field applies?** It is the only gate that has ever refused a whole metro -- Santa Clara for
roof-mounted plant, Phoenix for never having been built -- and it decides whether this model
describes the building at all. A frame with nobody's judgement attached answers nothing.

So this module produces `architecture_verdict: "NOT YET ASSESSED"`, exactly as
`screen_architecture.py:97` does, and the facility keeps its `NOT SCREENED` state until a verdict is
recorded against it by name. `NATIONAL-BUILD-PLAN.md` section 7.4: *"If imagery is unavailable for a
site, that site is NOT SCREENED, not 'screened, assumed fine'."* The same applies to a site whose
imagery exists and has not been looked at.

What the frame DOES buy immediately, and it is not small: the reader can see the actual building
under its own footprint outline, on the same panel and at the same scale as Ashburn's.

--------------------------------------------------------------------------------------------
WHY THE MANIFEST SHAPE IS COPIED RATHER THAN INVENTED
--------------------------------------------------------------------------------------------
`metros.committed_imagery()` already does the hard part -- it matches a candidate to the committed
pair, copies the PNG into `demo/` under the per-site name the page loads, and sets
`two_source_cross_check` from how many sources it found. It finds the manifest through
`metros.imagery_dir(k)`, and it matches on the exact tuple
`(committed.source_osm_id, committed.receptor_osm_id)`.

For a standalone facility that tuple is `(<osm id>, None)` -- so the candidate written here carries
`receptor_osm_id: null` and the match succeeds with no change to `committed_imagery` at all. That is
why this writes a `screen_manifest.json` in that module's own schema instead of a new format.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")

sys.path.insert(0, HERE)
import metros as M                                                   # noqa: E402
from measure_national_gaps import is_building_footprint               # noqa: E402

# COPIED VERBATIM from screen_architecture.py so national frames are comparable with the screened
# ones. Changing any of these would mean judging national sites at a different scale from Ashburn.
ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
PAD_LAT, PAD_LON = 0.0009, 0.0012      # ~200 x 200 m -- tight enough to see individual units
SIZE = (1400, 1050)
UA = {"User-Agent": "INTAKE-ARBITER/1.0 (research)"}
PAUSE_S = 1.5
RETRIES = 3
# MODULE LEVEL, because `fetch()` uses it. It was defined inside `run()` and the encode raised
# `NameError` on all three attempts -- caught only because the fetcher reports a failure as a
# failure ("recorded as absent, not as unscreened-and-fine") instead of writing a partial frame.
JPEG_QUALITY = 88

CAVEAT = ("0.3-0.5 m resolution shows objects, not nameplates. Cannot certify unit type or measure "
          "heights.")


def facility(key):
    reg = json.load(open(os.path.join(GEOM, "national_registry.json"),
                         encoding="utf-8"))["facilities"]
    if key not in reg:
        raise SystemExit("%r is not in the national registry" % key)
    return reg[key]


def own_buildings(f):
    """This facility's own BUILDING footprints in lat/lon, largest first. Parcels excluded."""
    rings = json.load(open(os.path.join(GEOM, "national_geometry.json"),
                           encoding="utf-8"))["rings"]
    out = [(m, rings[m]["geometry"], (rings[m].get("tags") or {}).get("name"))
           for m in f["members"] if m in rings and is_building_footprint(rings[m])]
    out.sort(key=lambda t: -len(t[1]))
    return out


def frame_bbox(geoms):
    """ArcGIS export order: lon_min, lat_min, lon_max, lat_max.

    ⚠ THE ORDER IS THE TRAP. Everything else in this project carries (lat, lon); the ArcGIS export
    and the manifest `bbox` this writes are (lon, lat). `metros.committed_imagery` records the order
    in the artefact for exactly that reason, and `drawAerial` reads it back in that order.
    Padded around EVERY building this facility owns, so a merged two-hall structure is framed whole
    rather than centred on its larger half.
    """
    lats = [p[0] for g in geoms for p in g]
    lons = [p[1] for g in geoms for p in g]
    return (min(lons) - PAD_LON, min(lats) - PAD_LAT,
            max(lons) + PAD_LON, max(lats) + PAD_LAT)


def fetch(bbox, path):
    params = {"bbox": "%.6f,%.6f,%.6f,%.6f" % bbox, "bboxSR": "4326", "imageSR": "3857",
              "size": "%d,%d" % SIZE, "format": "png32", "transparent": "false", "f": "image"}
    url = ESRI + "?" + urllib.parse.urlencode(params)
    for i in range(RETRIES):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                         timeout=180).read()
            # An ArcGIS error comes back as a tiny image or a JSON blob, both far under 2 kB. Same
            # guard `fetch_imagery.py:90` uses; without it an error tile is saved as evidence.
            if len(raw) < 2000:
                print("      response only %d bytes -- probably an error tile, not saving"
                      % len(raw))
                return None
            if path.lower().endswith((".jpg", ".jpeg")):
                # The endpoint only serves png32, so the recompression happens here. Written via a
                # temporary buffer rather than a temp file so a failed encode cannot leave a
                # half-written frame that the "already on disk" check would then trust.
                import io
                from PIL import Image
                Image.open(io.BytesIO(raw)).convert("RGB").save(
                    path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            else:
                open(path, "wb").write(raw)
            return os.path.getsize(path)
        except Exception as e:                                        # noqa: BLE001
            print("      attempt %d/%d: %s" % (i + 1, RETRIES, str(e)[:70]))
            if i < RETRIES - 1:
                time.sleep(5 * (2 ** i))
    return None


def run(key, dryrun=False):
    f = facility(key)
    blds = own_buildings(f)
    if not blds:
        print("   %-22s SKIPPED -- no building footprint (boundary_only)" % key)
        return 0
    bbox = frame_bbox([g for _, g, _ in blds])
    osm, geom, name = blds[0]
    lat0 = sum(p[0] for p in geom) / len(geom)
    lon0 = sum(p[1] for p in geom) / len(geom)
    out_dir = M.imagery_dir(key)
    # 🔴 JPEG, NOT PNG, AND THE REASON IS A HARD LIMIT RATHER THAN A PREFERENCE.
    # A frame is 2.58 MB as png32. At 359 standalone facilities that is 928 MB of aerial imagery in
    # `demo/` alone -- and GitHub Pages caps a published site at 1 GB, so the PNGs by themselves
    # would make the demo unpublishable before a single other artefact was counted. Measured on a
    # real frame: JPEG q88 is 0.42 MB, 6.1x smaller, for 151 MB across the tier.
    # VERIFIED LEGIBLE BEFORE CONVERTING, which NATIONAL-BUILD-PLAN section 8 asks for explicitly:
    # the equipment yard was cropped from both formats and compared, and the individual condenser
    # units keep their fin and fan structure at q88. The screening judgement this frame exists to
    # support is unaffected.
    # The five HAND-BUILT metros keep their PNGs untouched -- their frames are the audited evidence
    # behind "five screened, two refused", and two browser harnesses name `site_aerial.png`.
    fname = "00_%s.jpg" % osm.replace("/", "_")

    print("   %-22s %-28s %d building(s)" % (key, (name or "(unnamed)")[:28], len(blds)))
    print("      bbox (lon,lat order) : %.6f,%.6f,%.6f,%.6f" % bbox)
    print("      frame                : %s/%s  %dx%d" % (os.path.basename(out_dir), fname,
                                                         SIZE[0], SIZE[1]))
    if dryrun:
        print("      DRY RUN -- nothing fetched")
        return 0

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, fname)
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        print("      already on disk (%.1f MB) -- not refetched"
              % (os.path.getsize(path) / 1048576.0))
        n = os.path.getsize(path)
    else:
        n = fetch(bbox, path)
        if not n:
            print("      FETCH FAILED -- recorded as absent, not as unscreened-and-fine")
            return 1
        print("      fetched %.1f MB" % (n / 1048576.0))

    # THE MANIFEST, in `screen_architecture.py`'s own schema so `metros.committed_imagery()` reads it
    # unchanged. `receptor_osm_id: null` is what makes the tuple match for a standalone facility.
    man = {
        "generated_by": "INTAKE-ARBITER/src/fetch_facility_imagery.py",
        "api_calls_made": 0,
        "source": "ESRI World Imagery via the keyless ArcGIS REST export endpoint",
        "facility": key,
        "caveat": CAVEAT,
        # 🔴 NOT A VERDICT. See this module's docstring: a frame is not a screening. The facility
        # stays NOT SCREENED until a human or model judgement is recorded against it BY NAME.
        "architecture_verdict": "NOT YET ASSESSED",
        "what_would_change_this": ("a recorded judgement on whether the cooling plant is at ground "
                                   "level (where FortyGuard's 2 m field applies) or roof-mounted "
                                   "(where this model does not describe the building at all)"),
        "candidates": [{
            "rank": 0,
            "file": fname,
            "source_osm_id": int(osm.split("/")[1]),
            # NULL, deliberately: there is no receptor. This is the field that makes
            # `committed_imagery`'s exact-tuple match succeed for a one-building facility.
            "receptor_osm_id": None,
            "source_name": name,
            "receptor_name": None,
            "source_latlon": [lat0, lon0],
            "receptor_latlon": None,
            "bbox": list(bbox),
            "bbox_order": "lon_min, lat_min, lon_max, lat_max (ArcGIS export order)",
            "n_buildings_framed": len(blds),
            "architecture_verdict": "NOT YET ASSESSED",
        }],
    }
    json.dump(man, open(os.path.join(out_dir, "screen_manifest.json"), "w", encoding="utf-8"),
              indent=1, allow_nan=False)
    return 0


def record_verdict(key, verdict, in_scope, assessed_by, evidence, note):
    """Attach a SCREENING VERDICT to a facility's frame, with who made it and on what.

    🔴 A VERDICT MUST NAME ITS ASSESSOR AND ITS EVIDENCE, and this project's existing ones do not --
    `architecture_verdicts.json` records the judgement and the reasoning but not who looked or at how
    many sources. That was survivable at five hand-screened metros. It is not survivable at scale,
    because a reader has no way to tell a two-source human screening (Ashburn) from a single-frame
    model reading, and those deserve different amounts of trust.

    So every verdict written here carries:
      assessed_by  -- the assessor, named, including when it is a model rather than a person
      evidence     -- how many sources and which, so `two_source_cross_check` can be judged
      limits       -- the resolution limit that applies to THIS verdict, quoted not implied

    The project's own precedent for the weaker grade is Dulles: one ESRI frame, no USGS cross-check,
    and its record says so rather than claiming parity with Ashburn.
    """
    d = M.imagery_dir(key)
    p = os.path.join(d, "screen_manifest.json")
    if not os.path.exists(p):
        raise SystemExit("no frame for %r -- fetch it first" % key)
    man = json.load(open(p, encoding="utf-8"))
    man["architecture_verdict"] = verdict
    man["in_scope"] = bool(in_scope)
    man["assessed_by"] = assessed_by
    man["assessed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    man["evidence"] = evidence
    man["verdict_note"] = note
    man["limits"] = ("Single-source reading at %s. Chillers and generators are not distinguishable "
                     "at this resolution, so 'ground-level plant' is a statement about WHERE the "
                     "equipment is, not about what it is. The two-source cross-check is NOT met -- "
                     "the same weaker standing this project records for Dulles." % CAVEAT.split(".")[0])
    for c in man.get("candidates", []):
        c["architecture_verdict"] = verdict
        c["in_scope"] = bool(in_scope)
    json.dump(man, open(p, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("   %-22s verdict %-8s in_scope=%s  by %s" % (key, verdict, in_scope, assessed_by))
    return 0


def main(argv):
    if argv and argv[0] == "verdict":
        # python fetch_facility_imagery.py verdict <KEY> <GRADE|ROOFTOP|NOT_BUILT> <in_scope 0|1>
        #        "<assessed_by>" "<evidence>" "<note>"
        if len(argv) < 7:
            raise SystemExit('verdict <KEY> <VERDICT> <0|1> "<by>" "<evidence>" "<note>"')
        return record_verdict(argv[1], argv[2], argv[3] == "1", argv[4], argv[5], argv[6])
    dry = "--dryrun" in argv
    argv = [a for a in argv if a != "--dryrun"]
    if "--subset" in argv:
        p = os.path.join(GEOM, "_subset20.json")
        keys = json.load(open(p, encoding="utf-8"))
    else:
        keys = argv
    if not keys:
        raise SystemExit("name facility keys, or --subset")

    print("=" * 78)
    print("FACILITY IMAGERY -- %d facility(ies), free and keyless.  A FRAME IS NOT A SCREENING."
          % len(keys))
    print("=" * 78)
    rc = 0
    for i, k in enumerate(keys, 1):
        rc |= run(k, dryrun=dry)
        if i < len(keys) and not dry:
            time.sleep(PAUSE_S)
    print("\n   Every frame carries architecture_verdict = NOT YET ASSESSED. The facility stays")
    print("   NOT SCREENED until a judgement is recorded against it, because the gate this")
    print("   feeds has refused two whole metros and a photograph nobody has read refuses nothing.")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
