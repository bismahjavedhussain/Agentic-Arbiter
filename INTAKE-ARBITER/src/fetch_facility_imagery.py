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


def fetch(bbox, path, url=None):
    # `url` defaults to ESRI so every existing caller is unchanged; the USGS second source passes
    # its own endpoint. The PARAMS are deliberately identical for both providers -- same bboxSR,
    # imageSR, size and format -- because the two frames are compared against each other, and a
    # difference in request shape would show up as a difference in the ground.
    params = {"bbox": "%.6f,%.6f,%.6f,%.6f" % bbox, "bboxSR": "4326", "imageSR": "3857",
              "size": "%d,%d" % SIZE, "format": "png32", "transparent": "false", "f": "image"}
    url = (url or ESRI) + "?" + urllib.parse.urlencode(params)
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


def label_committed_pair(key, dryrun=False):
    """Name the COMMITTED PAIR against the frame already on disk. ZERO NETWORK CALLS.

    🔴 THE DEFECT THIS CLOSES: the aerial panel was blank on every PAIRED national facility -- 87 of
    the 90 offerable ones, and paired facilities are the only ones that HAVE a plume, so it was blank
    exactly where a reader most needs to see the geometry (a building standing between the condensers
    and the neighbour's intake is the whole reason 20 sites are refused).

    IT WAS NEVER A MISSING PHOTOGRAPH. `run()` above computes its bbox with
    `frame_bbox(all of the facility's own buildings)`, so the frame already covers the WHOLE campus.
    What it records is standalone-shaped: `candidates[0]` names `blds[0]` as the source with
    `receptor_osm_id: None`. `select_site.py` then commits whichever PAIR inside that campus wins the
    refusal ranking, which is usually not `blds[0]`, so `metros.committed_imagery()`'s exact-tuple
    match correctly finds nothing and the panel says so.
    MEASURED before writing this: for all 87 paired national facilities, BOTH committed building
    centres already fall inside the existing frame's bbox. Zero are outside. So there is nothing to
    fetch -- ArcGIS is not called, and the free service is not touched.

    WHY THE MATCHER IS NOT LOOSENED INSTEAD. Making `committed_imagery()` accept "any frame whose
    bbox contains both centres" would be a tempting one-liner, and it is the wrong move: that
    function's exact-tuple rule exists because gotcha #98 put Chicago's halls on Ashburn's
    photograph, and #131 records what happens when a matcher is given a clever exception -- it
    silently excuses the case it was meant to catch. So the strict rule stays and this writes the
    DATA it needs, with the containment PROVEN per facility and recorded in the artefact.

    ⚠ THIS IS NOT A SCREENING, AND MUST NEVER READ AS ONE. `architecture_verdict` is untouched, so
    the facility stays NOT SCREENED and its imagery tier stays `national_unscreened`. All this does
    is let a reader LOOK at the frame with the committed footprints drawn on it. Gotcha #184 is the
    rule: fetching -- or in this case labelling -- a photograph is not screening a site.
    """
    # `metros` is already imported as M at module scope -- no local import, which would also drag
    # this module into audit check 6f's scope by a different route (see #182).
    sites = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
    row = next((s for s in sites["sites"] if s["key"] == key), None)
    com = (row or {}).get("committed") or {}
    if not com.get("receptor_osm_id"):
        print("   %-22s skipped -- no committed pair (standalone frames already match)" % key)
        return 0
    mp = os.path.join(M.imagery_dir(key), "screen_manifest.json")
    if not os.path.exists(mp):
        print("   %-22s NO MANIFEST -- run the fetch first" % key)
        return 1
    man = json.load(open(mp, encoding="utf-8"))
    cands = man.get("candidates") or []
    if not cands or not cands[0].get("bbox"):
        print("   %-22s NO FRAME/BBOX on disk" % key)
        return 1
    base = cands[0]
    # NORMALISED, because sites.json carries these as STRINGS for a national facility and as INTS
    # for a hand-built metro. `committed_imagery()` compares the tuple with ==, so a correct pair
    # written with the wrong type would still not match -- a second, quieter half of the same bug.
    src_id, rec_id = str(com["source_osm_id"]), str(com["receptor_osm_id"])
    if any(str(c.get("source_osm_id")) == src_id
           and str(c.get("receptor_osm_id")) == rec_id for c in cands):
        print("   %-22s already labelled for its committed pair" % key)
        return 0
    lo_lon, lo_lat, hi_lon, hi_lat = base["bbox"]
    pts = [com.get("source_latlon"), com.get("receptor_latlon")]
    # ASSERTED, NOT ASSUMED. If a committed building is outside the frame, saying the frame depicts
    # it would be exactly the defect this whole function is written around. Refuse and say so.
    for lbl, p in zip(("source", "receptor"), pts):
        if not p or not (lo_lat <= p[0] <= hi_lat and lo_lon <= p[1] <= hi_lon):
            print("   %-22s REFUSED -- committed %s is outside the frame; it needs its own fetch"
                  % (key, lbl))
            return 1
    if dryrun:
        print("   %-22s would label %s -> %s onto %s" % (key, src_id, rec_id, base["file"]))
        return 0
    cands.append({
        "rank": len(cands),
        "file": base["file"],
        "source_osm_id": int(src_id),
        "receptor_osm_id": int(rec_id),
        "source_name": com.get("source_name"),
        "receptor_name": com.get("receptor_name"),
        "source_latlon": com.get("source_latlon"),
        "receptor_latlon": com.get("receptor_latlon"),
        "bbox": list(base["bbox"]),
        "bbox_order": base.get("bbox_order"),
        # THE PROVENANCE, in the artefact rather than in a comment: this entry reuses a frame that
        # was fetched centred on a different building of the same facility, and the reuse is only
        # legitimate because containment was checked. A reader can re-check it from these fields.
        "frame_reused_from_rank": base.get("rank", 0),
        "frame_centred_on_osm_id": base.get("source_osm_id"),
        "pair_verified_inside_frame": True,
        "labelled_by": "fetch_facility_imagery.py pair -- no network call, no screening verdict",
    })
    man["candidates"] = cands
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("   %-22s labelled %s -> %s onto %s" % (key, src_id, rec_id, base["file"]))
    return 0


def fetch_committed_pair(key, dryrun=False):
    """Fetch a frame CENTRED ON THE COMMITTED PAIR. One real ArcGIS request per facility.

    `run()` frames the whole facility -- `frame_bbox(every building it owns)` -- which is the right
    view for judging a campus and the reason `pair` above could reuse it: all 87 committed pairs
    already fall inside. What it is NOT is centred: the pair that `select_site.py` commits can sit
    off to one side of a multi-building campus, so the two halls and the gap between them are
    smaller in frame than they would be if the frame had been asked for around THEM.
    This asks for that frame. Same endpoint, same `bboxSR`/`imageSR`/`size`/pads as `run()` and
    therefore as `screen_architecture.py` -- §3.5.7's rule, so a national frame stays comparable
    with the ones the three shipped metros were screened from. A different zoom would mean judging
    national sites at a different scale, which is not a fair comparison to offer.

    ⚠ STILL NOT A SCREENING. `architecture_verdict` is untouched; the facility stays NOT SCREENED.
    A sharper photograph nobody has read refuses nothing (#184).

    The facility-wide `00_*.jpg` is KEPT. It is the campus view and it is real evidence; this adds
    `01_<src>_<rec>.jpg` beside it rather than overwriting it. `demo/` does not grow either way,
    because `metros.committed_imagery()` copies exactly one frame per site.
    """
    sites = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
    row = next((s for s in sites["sites"] if s["key"] == key), None)
    com = (row or {}).get("committed") or {}
    if not com.get("receptor_osm_id"):
        print("   %-22s skipped -- no committed pair" % key)
        return 0
    src_id, rec_id = str(com["source_osm_id"]), str(com["receptor_osm_id"])
    rings = json.load(open(os.path.join(GEOM, "national_geometry.json"),
                           encoding="utf-8"))["rings"]
    geoms, missing = [], []
    for oid in (src_id, rec_id):
        mk = "way/" + oid
        if mk in rings and rings[mk].get("geometry"):
            geoms.append(rings[mk]["geometry"])
        else:
            missing.append(mk)
    # RECORDED AS A FAILURE, NOT SKIPPED. #178: `fetch_facility_imagery.py` only found its own
    # NameError because it reports failures as failures instead of quietly showing nothing.
    if missing:
        print("   %-22s NO RING GEOMETRY for %s -- cannot frame the pair" % (key, ", ".join(missing)))
        return 1
    bbox = frame_bbox(geoms)
    out_dir = M.imagery_dir(key)
    fname = "01_%s_%s.jpg" % (src_id, rec_id)
    path = os.path.join(out_dir, fname)
    print("   %-22s %s -> %s" % (key, src_id, rec_id))
    print("      bbox (lon,lat order) : %.6f,%.6f,%.6f,%.6f" % bbox)
    if dryrun:
        print("      DRY RUN -- would fetch %s  %dx%d" % (fname, SIZE[0], SIZE[1]))
        return 0
    os.makedirs(out_dir, exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        print("      already on disk (%.2f MB) -- not refetched"
              % (os.path.getsize(path) / 1048576.0))
    else:
        n = fetch(bbox, path)
        if not n:
            print("      FETCH FAILED -- recorded as absent, not as centred-and-fine")
            return 1
        print("      fetched %.2f MB" % (n / 1048576.0))

    mp = os.path.join(out_dir, "screen_manifest.json")
    man = json.load(open(mp, encoding="utf-8"))
    cands = man.get("candidates") or []
    ent = {
        "rank": 1,
        "file": fname,
        "source_osm_id": int(src_id),
        "receptor_osm_id": int(rec_id),
        "source_name": com.get("source_name"),
        "receptor_name": com.get("receptor_name"),
        "source_latlon": com.get("source_latlon"),
        "receptor_latlon": com.get("receptor_latlon"),
        "bbox": list(bbox),
        "bbox_order": "lon_min, lat_min, lon_max, lat_max (ArcGIS export order)",
        "framed_on": "the committed pair, not the facility",
        "request_matches": "screen_architecture.py -- same endpoint, size and pads (§3.5.7)",
        "labelled_by": "fetch_facility_imagery.py pairfetch -- one ArcGIS request, no verdict",
    }
    # REPLACED IN PLACE, NOT APPENDED. `committed_imagery()` takes the FIRST candidate whose id
    # tuple matches, so leaving the earlier reused-frame entry ahead of this one would keep the
    # off-centre file on screen and make this fetch invisible -- a silent no-op that looks like a
    # success. Match on the id pair, normalised, for the same string/int reason recorded in metros.
    hit = next((i for i, c in enumerate(cands)
                if str(c.get("source_osm_id")) == src_id
                and str(c.get("receptor_osm_id")) == rec_id), None)
    if hit is None:
        cands.append(ent)
    else:
        cands[hit] = ent
    man["candidates"] = cands
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("      manifest points at %s" % fname)
    return 0


USGS = ("https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/export")


def fetch_usgs_pair(key, dryrun=False):
    """A SECOND SOURCE for the committed pair, from USGS. Free, keyless, public domain.

    🔴 WHY THIS EXISTS, AND IT IS THE PROJECT'S OWN RULE RATHER THAN A NEW IDEA.
    `data/geometry/architecture_verdicts.json` states it outright:
        "No verdict is recorded from a single source. ESRI and USGS have DIFFERENT CAPTURE SEASONS,
         so agreement between them is meaningful."
    That rule is what the five hand-built metros were screened under. The national tier has been
    running on ESRI alone, in the `national_single_source` tier, and that is exactly why the
    built-or-not question could not be settled: the keyless ArcGIS export exposes NO acquisition
    date, so one undated frame showing bare ground is evidence about an unknown moment.
    TWO undated frames from two providers with different capture seasons are far stronger. If ESRI
    shows graded pads and USGS shows a finished hall, the ground was cleared BEFORE it was built and
    the site is real. If both show bare ground, that is two independent looks agreeing.

    THE BBOX IS REUSED VERBATIM from the ESRI pair frame, so the two images are the same footprint
    at the same scale and can be compared pixel for pixel. A different bbox would make the
    comparison a judgement about framing rather than about the ground.

    NAMED `usgs_<esri file>` ON PURPOSE: `metros.committed_imagery()` already looks for exactly
    that prefix and will offer it in the picker's source dropdown with no further change --
    the same mechanism Ashburn's second source uses.
    """
    mp = os.path.join(M.imagery_dir(key), "screen_manifest.json")
    if not os.path.exists(mp):
        print("   %-22s NO MANIFEST -- fetch the ESRI frame first" % key)
        return 1
    man = json.load(open(mp, encoding="utf-8"))
    cand = next((c for c in (man.get("candidates") or []) if c.get("framed_on")), None)
    if not cand:
        print("   %-22s no committed-pair frame yet -- run `pairfetch` first" % key)
        return 1
    bbox = tuple(cand["bbox"])
    out_dir = M.imagery_dir(key)
    fname = "usgs_" + cand["file"]
    path = os.path.join(out_dir, fname)
    print("   %-22s %s" % (key, fname))
    print("      bbox (lon,lat order) : %.6f,%.6f,%.6f,%.6f  [same as the ESRI frame]" % bbox)
    if dryrun:
        print("      DRY RUN -- nothing fetched")
        return 0
    n = fetch(bbox, path, url=USGS)
    if not n:
        # RECORDED AS ABSENT, NOT AS AGREEMENT. A missing second source must never read as a
        # confirmed one -- that is the whole point of the two-source rule (#178's lesson: report
        # failures as failures).
        print("      NO USGS COVERAGE HERE -- recorded absent, NOT as a cross-check")
        return 1
    print("      fetched %.2f MB -- a genuine second source, different capture season" % (n / 1048576.0))
    cand["usgs_file"] = fname
    cand["second_source"] = "USGS The National Map, USGSImageryOnly (public domain)"
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1, allow_nan=False)
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
    # `pair` LABELS AN EXISTING FRAME WITH THE COMMITTED PAIR AND MAKES NO NETWORK CALL. Separate
    # subcommand rather than folded into the fetch, because the two do different things and only one
    # of them touches a third party's free service -- and `--all` here must never be mistaken for
    # `--all` there. See label_committed_pair()'s docstring.
    # `pairfetch` MAKES ONE REAL ArcGIS REQUEST PER FACILITY. Kept a separate word from `pair`,
    # which makes none, because the difference is whether a third party's free service is touched
    # and that must never turn on a flag someone could miss.
    # `usgs` FETCHES THE SECOND SOURCE. Separate word again: it makes real requests, to a different
    # provider, and its whole purpose is to be an INDEPENDENT look -- so it must never be something
    # that happens implicitly as part of the ESRI fetch.
    if argv and argv[0] == "usgs":
        rest = [a for a in argv[1:] if a != "--dryrun"]
        dryp = "--dryrun" in argv
        if not rest:
            raise SystemExit("usgs <KEY> [KEY ...] [--dryrun]")
        print("=" * 78)
        print("SECOND SOURCE from USGS The National Map -- %d facility(ies)%s"
              % (len(rest), "  [DRY RUN]" if dryp else "  REAL REQUESTS"))
        print("   Public domain, keyless. Different capture season from ESRI, which is the whole")
        print("   point: architecture_verdicts.json requires two sources for a verdict.")
        print("=" * 78)
        rc, ok = 0, 0
        for i, k in enumerate(rest, 1):
            r = fetch_usgs_pair(k, dryrun=dryp)
            rc |= r
            ok += (r == 0)
            if i < len(rest) and not dryp:
                time.sleep(PAUSE_S)
        print("\n   %d of %d fetched. A second frame is EVIDENCE, not a verdict -- it still has to"
              % (ok, len(rest)))
        print("   be read, and the reading recorded with `verdict`.")
        print("=" * 78)
        return rc
    if argv and argv[0] == "pairfetch":
        rest = [a for a in argv[1:] if a != "--dryrun"]
        dryp = "--dryrun" in argv
        if rest == ["--all"] or not rest:
            sj = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
            rest = [s["key"] for s in sj["sites"]
                    if s.get("offerable") and (s.get("committed") or {}).get("receptor_osm_id")
                    and s["key"] not in M.METROS]
        print("=" * 78)
        print("FETCH FRAMES CENTRED ON THE COMMITTED PAIR -- %d facility(ies)%s"
              % (len(rest), "  [DRY RUN]" if dryp else "  REAL ArcGIS REQUESTS"))
        print("   free and keyless, paced %.1f s apart. A FRAME IS NOT A SCREENING." % PAUSE_S)
        print("=" * 78)
        rc, ok = 0, 0
        for i, k in enumerate(rest, 1):
            r = fetch_committed_pair(k, dryrun=dryp)
            rc |= r
            ok += (r == 0)
            if i < len(rest) and not dryp:
                time.sleep(PAUSE_S)
        print("\n   %d of %d succeeded. architecture_verdict untouched: every facility here stays"
              % (ok, len(rest)))
        print("   NOT SCREENED. The five hand-built metros were not touched at all.")
        print("=" * 78)
        return rc
    if argv and argv[0] == "pair":
        rest = [a for a in argv[1:] if a != "--dryrun"]
        dryp = "--dryrun" in argv
        if rest == ["--all"] or not rest:
            sj = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
            rest = [s["key"] for s in sj["sites"]
                    if s.get("offerable") and (s.get("committed") or {}).get("receptor_osm_id")
                    and s["key"] not in M.METROS]
        print("=" * 78)
        print("LABEL COMMITTED PAIRS onto frames already on disk -- %d facility(ies), NO fetch."
              % len(rest))
        print("=" * 78)
        rc = 0
        for k in rest:
            rc |= label_committed_pair(k, dryrun=dryp)
        print("\n   No ArcGIS request was made. architecture_verdict is untouched: every facility")
        print("   here stays NOT SCREENED. This only lets a reader LOOK at the frame.")
        print("=" * 78)
        return rc
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
