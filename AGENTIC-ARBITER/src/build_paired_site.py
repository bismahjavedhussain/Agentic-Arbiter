# -*- coding: utf-8 -*-
"""THE PAIRED PATH -- geometry artefacts for a national facility that HAS a neighbour. ZERO API CALLS.

    python build_paired_site.py <FACILITY_KEY>
    python build_paired_site.py selftest        # the invariants, offline

WHY THIS EXISTS
    `build_standalone_site.py` handles the 360 facilities with no other tagged data centre inside the
    solver's 600 m validated range. It writes a zero rise table, correctly, because with no receptor
    there is no intake and the quantity is undefined rather than unknown.

    The other case had no driver at all. `metros.national_entry()` reported every paired facility as
    *"the pairwise plume funnel has not been run at national scale yet"*, and that was literally
    true: `build_national_pairs.py` had grouped the buildings by real 600 m distance and labelled
    114 facilities `paired_clear` or `paired_advisory`, and nothing downstream could build one.
    Measured 2026-08-25: 157 facilities were covered by a purchased FortyGuard field and 127 of them
    could not be opened, 117 for exactly this reason. Paid data with no path to a reader.

--------------------------------------------------------------------------------------------
WHAT THIS DOES NOT DO, AND THAT IS THE POINT
--------------------------------------------------------------------------------------------
It does not choose the pair, rasterise a footprint, place a condenser bank, position an intake or
solve a plume. Every one of those already exists, is verified, and is already key-generic:

    select_site.py   applies the THREE GEOMETRIC GATES and then ranks by wind exposure x separation
                     dilution over this site's OWN wind record. It reads `_M.candidates_path()` and
                     writes `_M.geom_path("selected_site.json")`, and it imports the gate constants
                     from build_site so the two cannot drift.
    build_site.py    rasterises both real rings, places the bank on the facade facing the receptor,
                     puts the intake outside the receptor's facing facade, and REFUSES to write
                     unless its three rasteriser checks pass.
    agent.rise_table solves 576 real dispersion runs per placement and caches the result.

So the only thing actually missing was the INPUT those tools expect: a candidates file. Ashburn's
comes from `fetch_geometry.py`, which queries Overpass over a metro bbox. A national facility already
has its rings on disk from the national build, so this composes the same structure from them and then
drives the existing tools. A national paired site therefore goes through the IDENTICAL selection rule
and the IDENTICAL gates as Ashburn -- which is the only way the two are comparable at all.

THE CANDIDATE FIELDS ARE COMPUTED BY THE SAME FUNCTIONS, NOT RE-DERIVED HERE.
`to_metres`, `poly_area`, `centroid`, `oriented_extent` and `min_area_rect` are imported from
`fetch_geometry`. A second implementation of the minimum-area rectangle would be a second thing to
keep correct, and the fill-ratio argument in that function's docstring (real polygons fill 0.38 and
0.46 of their bounding boxes) is exactly as load-bearing here as it is at Ashburn.

ONE SHARED PROJECTION ORIGIN, WHICH MATTERS FOR A PAIR.
`build_standalone_site.local_ring` re-centres each ring on the domain midpoint, which is right for a
single building and wrong for two: it would place both buildings on top of each other and destroy
the separation the whole model is about. Every ring here is projected through ONE origin -- the
facility centroid -- so relative positions survive. `build_site.py` then shifts the pair as a unit.

WHAT IS REAL AND WHAT IS NULL
    REAL: both OSM rings, projected; both areas, centroids and minimum-area rectangles; the
          committed pair chosen by the published rule; this facility's own wind statistics from its
          own assigned station.
    NULL: nothing. If a facility cannot produce a committed pair that clears the gates, this REFUSES
          and writes nothing -- it does not fall back to the standalone path and it does not relax a
          gate. A facility that fails the gates is a facility this model does not describe, which is
          the same answer Santa Clara and Phoenix got.
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")

sys.path.insert(0, HERE)
import metros as M                                                        # noqa: E402
from fetch_geometry import (PAIR_MAX_M, PAIR_MIN_M, centroid,             # noqa: E402
                            min_area_rect, oriented_extent, poly_area, to_metres)
# `facility()` is deliberately NOT imported from build_standalone_site: that one REFUSES any kind
# but `standalone`, which is correct for the no-neighbour path and is exactly the opposite of the
# gate this driver needs. `rings_for` and `wind_block` ARE kind-agnostic and are
# reused as-is -- the rings loader already excludes parcels and sorts by real footprint area.
# NOT `direction_table`: it returns a hardcoded standalone table (worst=None, every row zero,
# verdicts `not_applicable_no_intake`). A paired facility runs `direction_sweep.py` instead, which
# actually measures the refusal surface. Importing it here is how it got called by mistake.
from build_standalone_site import rings_for, wind_block                 # noqa: E402

PAIRED_KINDS = ("paired_clear", "paired_advisory")


def facility(key):
    """The registry record, gated on a PAIRED kind rather than a standalone one."""
    p = os.path.join(GEOM, "national_registry.json")
    reg = json.load(open(p, encoding="utf-8"))["facilities"]
    if key not in reg:
        raise SystemExit("%r is not in the national registry" % key)
    return reg[key]


def facility_tags(members):
    """The real OSM tag dict for each member way, keyed by the bare osm id.

    🔴 THE SECOND HALF OF THE 106-FACILITY FAILURE, AND AGAIN THE BUG WAS A COMMENT. This block
    used to write `operator/building_tag/telecom_tag = None` under the note *"OSM tags are not
    carried in the national rings file ... select_site does not gate on them"*. Both halves were
    false:

      * `national_geometry.json` DOES carry them -- `rings["way/<id>"]["tags"]` is exactly what
        `measure_national_gaps.is_building_footprint` reads to exclude land parcels.
      * `select_site.is_datacentre` gates on them HARD. It matches a name-keyword list
        ("data", "digital", "cloud", "cyrus", "equinix", "aws", "amazon", ...) and otherwise falls
        back to `building_tag`/`telecom_tag`. A hall named plainly "Microsoft TRP1", "Google" or
        "Meta" matches NO keyword, so with the tags nulled every pair at those facilities was
        rejected as "not a data-centre pair" -- 11 of 11 at the first facility in the batch.

    So the honest fix is to carry the fact rather than assert it. The national discovery query is
    `way[telecom=data_center]` OR `way[building=data_center]` (discover_dc_clusters.py:209-210), so
    the tag is present on every member by construction; this reads it instead of guessing, and a
    member whose tags are genuinely absent still gets None rather than an invented value.
    """
    rings = json.load(open(os.path.join(GEOM, "national_geometry.json"), encoding="utf-8"))["rings"]
    out = {}
    for m in members:
        r = rings.get(m)
        if r:
            out[str(m).split("/")[-1]] = r.get("tags") or {}
    return out


def candidate_buildings(blds, lat0, lon0, tags_by_id=None):
    """The facility's buildings in the shape select_site.py reads, through ONE projection origin.

    Mirrors `fetch_geometry.py`'s own building block field for field, using the same helpers, so a
    national candidate and an Ashburn candidate are the same kind of object.
    """
    tags_by_id = tags_by_id or {}
    out = []
    for osm, geom, name in blds:
        if not geom or len(geom) < 4:
            continue
        pts = to_metres([{"lat": p[0], "lon": p[1]} for p in geom], lat0, lon0)
        area = poly_area(pts)
        cx, cy = centroid(pts)
        w, h = oriented_extent(pts)
        L, W, ang = min_area_rect(pts)
        out.append({
            # STRING, because that is what fetch_geometry emits and what select_site compares.
            "osm_id": str(osm).split("/")[-1],
            "area_m2": round(area, 1),
            "centre_m": [round(cx, 1), round(cy, 1)],
            "width_m": round(w, 1), "height_m": round(h, 1),
            "rot_rect_long_m": round(L, 1), "rot_rect_short_m": round(W, 1),
            "rot_rect_angle_deg": round(ang, 1),
            "ring_m": [[round(x, 1), round(y, 1)] for x, y in pts],
            "name": name,
            # THE REAL TAGS, read from the rings file -- see facility_tags. `select_site.is_datacentre`
            # gates on these, and nulling them rejected every Microsoft/Google/Meta facility.
            "operator": (tags_by_id.get(str(osm).split("/")[-1]) or {}).get("operator"),
            "building_tag": (tags_by_id.get(str(osm).split("/")[-1]) or {}).get("building"),
            "telecom_tag": (tags_by_id.get(str(osm).split("/")[-1]) or {}).get("telecom"),
            "n_vertices": len(geom),
            "centre_latlon": [round(lat0 + math.degrees(cy / 6371000.0), 6),
                              round(lon0 + math.degrees(cx / (6371000.0
                                                              * math.cos(math.radians(lat0)))), 6)],
        })
    return out


def candidate_pairs(bs):
    """Enumerate the source/receptor pairs, in the shape `select_site.py` reads.

    🔴 THIS FUNCTION IS THE FIX FOR A 106-FACILITY FAILURE, AND THE BUG WAS A COMMENT.
    `write_candidates` used to emit `"pairs": []` under the note *"select_site.py forms its own
    pair list from `buildings`; an empty list here is not a gap."* That was simply false:
    `select_site.py:169` iterates `g["pairs"]` and never looks at `buildings` for pairing. So every
    paired facility reported `candidate pairs 0`, every gate counted zero rejections, and the
    driver exited 5 -- which the batch filed as `no_geometry`. It looked exactly like a data
    shortage (106 of 124 facilities "have no usable geometry") when the geometry was fine and the
    input was empty. A wrong assumption stated confidently in a comment survived a self-test,
    a code review and a full overnight batch.

    The enumeration mirrors `fetch_geometry.py` exactly -- same separation band, same bearing
    convention, same field names, same combined-area ranking -- because `select_site.py` must not
    be able to tell which producer wrote its input. Constants are IMPORTED, not restated, so the
    two cannot drift apart.
    """
    out = []
    for i, a in enumerate(bs):
        for b in bs[i + 1:]:
            dx = b["centre_m"][0] - a["centre_m"][0]
            dy = b["centre_m"][1] - a["centre_m"][1]
            sep = math.hypot(dx, dy)
            if not (PAIR_MIN_M <= sep <= PAIR_MAX_M):
                continue
            bearing = math.degrees(math.atan2(dx, dy)) % 360.0        # a -> b, 0 = north
            out.append({
                "source_osm_id": a["osm_id"], "receptor_osm_id": b["osm_id"],
                "separation_m": round(sep, 1),
                "bearing_a_to_b_deg": round(bearing, 1),
                "source_area_m2": a["area_m2"], "receptor_area_m2": b["area_m2"],
                "combined_area_m2": round(a["area_m2"] + b["area_m2"], 1),
                "source_name": a["name"] or a["operator"],
                "receptor_name": b["name"] or b["operator"],
            })
    out.sort(key=lambda p: -p["combined_area_m2"])
    return out


def write_candidates(key, f, blds):
    """`<key>_candidates.json`, the one input the existing tools were missing."""
    lats = [p[0] for _, g, _ in blds for p in g]
    lons = [p[1] for _, g, _ in blds for p in g]
    lat0, lon0 = f["centre"][0], f["centre"][1]
    bs = candidate_buildings(blds, lat0, lon0, facility_tags(f["members"]))
    obj = {
        "source": "national OSM discovery -- rings from data/geometry/national_geometry.json, "
                  "composed into candidate shape by build_paired_site.py. No network call.",
        "fetched_bbox_south_west_north_east": [round(min(lats), 6), round(min(lons), 6),
                                               round(max(lats), 6), round(max(lons), 6)],
        "projection": "local equirectangular, metres, via fetch_geometry.to_metres",
        "projection_origin_latlon": [lat0, lon0],
        "filters": "the facility's own building group, as connected by build_national_pairs.py "
                   "union-find at the solver's 600 m validated range",
        "n_ways_returned": len(bs),
        "buildings": bs,
        # `select_site.py:169` iterates THIS list. It does not pair `buildings` itself -- see
        # candidate_pairs' docstring for what assuming otherwise cost.
        "pairs": candidate_pairs(bs),
        "caveat": "OSM tags (operator, building, telecom) are the mapper's own, read from "
                  "national_geometry.json rather than guessed; a member with no such tag keeps "
                  "None. The national discovery query already selected on telecom=data_center OR "
                  "building=data_center, so select_site's data-centre gate sees the tag it needs "
                  "even for an operator its name-keyword list does not know.",
        "facility_key": key,
        "facility_kind": f.get("kind"),
        "api_calls_made": 0,
    }
    p = M.geom_path("candidates.json", key)
    json.dump(obj, open(p, "w", encoding="utf-8"), allow_nan=False)
    return p, len(bs)


def run_step(label, args, key, extra_env=None, ok_codes=(0,)):
    """One existing tool, driven for this facility. Its stdout is shown only when it fails.

    `ok_codes` exists because a non-zero exit is not always a failure in this repository.
    `direction_sweep.py` returns 1 whenever any pre-registered verdict fails, and at a
    DELIBERATELY CLEAR site P1 ("non-degenerate refusal") failing is the CORRECT answer -- Ashburn's
    own sweep exits 1 for exactly that reason and its table is the one `audit.py` reads. Treating
    the code as the gate would refuse every clear site; the artefact is checked instead.
    """
    env = dict(os.environ, METRO=key)
    if extra_env:
        env.update(extra_env)
    r = subprocess.run([sys.executable] + args, cwd=HERE, env=env,
                       capture_output=True, text=True, timeout=3600)
    ok = r.returncode in ok_codes
    print("   %-42s %s" % (label, "OK" if ok else "FAILED"))
    if not ok:
        # 24 LINES, NOT 6, AND THE COUNT IS THE WHOLE LESSON. `select_site.py`'s SELECTION FUNNEL
        # is 8 lines and is the only thing that says WHY a facility was refused. A 6-line tail cut
        # off the top of it, so the batch logged `= SURVIVED all gates 0` with no funnel above it
        # and an empty `ERR` line -- which reads as "this facility has no usable geometry". It was
        # a bug in this driver, and the log could not tell the difference for 124 facilities in a
        # row. A diagnostic that truncates the causal part of the message is worse than silence,
        # because silence does not look like an answer.
        for ln in (r.stdout or "").strip().splitlines()[-24:]:
            print("      %s" % ln[:150])
        err = (r.stderr or "").strip().splitlines()
        for ln in err[-8:]:
            print("      ERR %s" % ln[:150])
        if not err:
            print("      ERR (stderr empty -- the child refused cleanly, exit %d; the reason is in "
                  "the stdout above)" % r.returncode)
    return ok


def main(argv):
    if argv and argv[0] == "selftest":
        return selftest()
    if not argv:
        raise SystemExit("name a paired facility key, or 'selftest'")
    key = argv[0]
    f = facility(key)

    print("=" * 78)
    print("PAIRED SITE -- %s.  ZERO API CALLS." % key)
    print("=" * 78)
    print("   %s | %s | %s" % (", ".join(f.get("names") or ["(unnamed)"]), f.get("state"),
                               f.get("kind")))
    if f.get("kind") not in PAIRED_KINDS:
        print("   REFUSED: kind is %r, not one of %s. A standalone facility goes through "
              "build_standalone_site.py; this driver would have to invent a receptor."
              % (f.get("kind"), ", ".join(PAIRED_KINDS)))
        return 2
    if not M.metro(key).get("station"):
        print("   REFUSED: no weather station assigned yet, so select_site.py has no wind record to "
              "rank pairs against. Run the national batch's station step first.")
        return 3

    blds = rings_for(f)
    print("   buildings in group : %d" % len(blds))
    if len(blds) < 2:
        print("   REFUSED: a paired facility needs at least two rings on disk and this has %d. "
              "The registry says paired, the geometry does not -- that disagreement is reported "
              "rather than papered over." % len(blds))
        return 4

    p, n = write_candidates(key, f, blds)
    print("   wrote candidates   : %s  (%d building(s))" % (os.path.basename(p), n))

    wb, u_med = wind_block(key)
    print("   its own wind       : %s usable hours at %s, median %.4f m/s"
          % (format(wb["usable_hours"], ","), wb["station"], u_med))

    # ---- the existing, verified tools, driven in the order Ashburn's own build uses -------------
    if not run_step("select the committed pair (3 gates + exposure)", ["select_site.py"], key):
        print("   STOPPED. No pair cleared the published gates, so nothing was committed. That is "
              "a real answer about this facility, not a failure of this driver.")
        return 5
    for mode in ("longest", "facing"):
        if not run_step("rasterise the site, bank on %-8s" % mode, ["build_site.py"], key,
                        {"BANK_MODE": mode}):
            print("   STOPPED. build_site.py refuses to write when its rasteriser checks fail.")
            return 6

    # 🔴 THE REAL N-54 SWEEP, NOT build_standalone_site.direction_table().
    # This called that helper, under a comment at the top of this file claiming it was
    # "kind-agnostic". It is the opposite: it returns a hardcoded STANDALONE table --
    # `"test": "N-54 refusal surface -- NOT RUN, no receptor intake exists"`, every row zero,
    # `n_downwind: 0`, `worst: None`, and all three pre-registered verdicts recorded as
    # `not_applicable_no_intake`. Correct for a facility with no receptor, and a fabrication for a
    # paired one, which HAS an intake and whose refusal surface is the whole point of the gate.
    #
    # It failed loudly two steps later rather than shipping quietly, which is the one mercy here:
    # `ticker.py` rederives `solve.worst/worst_bearing` from
    # trace.direction_table.modes.longest.worst.bearing and raised
    # "'NoneType' object is not subscriptable". A zero table would otherwise have published a
    # paired site claiming it had measured a refusal surface it never swept.
    #
    # `direction_sweep.py` is already per-metro -- it reads `solver_site_<mode>.json`, which the
    # two build_site.py runs above have just written for THIS key, and writes
    # `<key>_direction_table.json`. So the fix is to run the tool that does the measurement.
    # EXIT 1 IS ACCEPTED, AND THE ARTEFACT IS GATED INSTEAD -- see run_step's docstring. Ashburn's
    # own sweep exits 1 with "P1 non-degenerate refusal: FAIL, refused 0.0 % of bearings", because
    # the committed pair was RE-SELECTED for a clear plume path and 0 % is the right answer at such
    # a site. Gating on the code would refuse exactly the sites the selection rule is trying to find.
    if not run_step("this facility's own 72-bearing refusal sweep", ["direction_sweep.py"], key,
                    ok_codes=(0, 1)):
        print("   STOPPED. The N-54 refusal sweep crashed rather than reporting a verdict.")
        return 7

    # WHAT THE CHAIN ACTUALLY NEEDS FROM THAT TABLE, checked here rather than five steps later.
    # `ticker.py` rederives `solve.worst/worst_bearing` from
    # modes.<mode>.worst.bearing and raises "'NoneType' object is not subscriptable" on a null --
    # which is how the standalone stub's `worst: None` was caught. Failing at the step that WRITES
    # the value is worth a few lines of duplication.
    dt = json.load(open(M.geom_path("direction_table.json", key), encoding="utf-8"))
    nullw = [m for m in ("longest", "facing")
             if not ((dt.get("modes") or {}).get(m) or {}).get("worst")]
    if nullw:
        print("   STOPPED. The direction table has a NULL `worst` for %s, so no worst bearing was "
              "found. ticker.py rederives that field and would fail on it five steps from here."
              % ", ".join(nullw))
        return 8
    print("   worst bearing      : %s"
          % ",  ".join("%s %s deg at %+.4f C" % (m, dt["modes"][m]["worst"]["bearing"],
                                                 dt["modes"][m]["worst"]["rise_c"])
                       for m in ("longest", "facing")))

    print()
    print("   The rise tables are NOT written here. `agent.rise_table()` solves 576 real dispersion")
    print("   runs per placement and caches them on the first chain run -- a zero table would be")
    print("   correct for a standalone facility and a lie for this one.")
    print("   next: python build_sites.py %s" % key)
    print("=" * 78)
    return 0


def selftest():
    """The invariants that would let this driver corrupt a site, checked offline."""
    ok = True

    def t(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("   [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("=" * 78)
    print("BUILD PAIRED SITE -- SELF TEST.  No network, no writes.")
    print("=" * 78)

    # 1. ONE ORIGIN KEEPS TWO BUILDINGS APART. The bug this guards is the whole reason the driver
    #    does not reuse `local_ring`: per-ring recentring places both buildings at the same point.
    a = [(39.0000, -77.0000), (39.0000, -76.9990), (39.0009, -76.9990), (39.0009, -77.0000)]
    b = [(39.0030, -77.0000), (39.0030, -76.9990), (39.0039, -76.9990), (39.0039, -77.0000)]
    blds = [("way/1", a, "A"), ("way/2", b, "B")]
    cb = candidate_buildings(blds, 39.0020, -77.0000)
    sep = math.hypot(cb[0]["centre_m"][0] - cb[1]["centre_m"][0],
                     cb[0]["centre_m"][1] - cb[1]["centre_m"][1])
    t("two buildings keep their real separation", 300.0 < sep < 400.0, "%.1f m apart" % sep)

    # 2. THE MINIMUM-AREA RECTANGLE IS THE IMPORTED ONE. A local reimplementation is the failure
    #    mode; this asserts the field is populated and sane rather than that a copy agrees.
    t("rotated rectangle is computed for every candidate",
      all(c["rot_rect_long_m"] >= c["rot_rect_short_m"] > 0 for c in cb),
      "long >= short > 0 at both")

    # 3. THE SHAPE select_site READS. Missing a key here fails 60 s into a subprocess instead of now.
    need = ("osm_id", "area_m2", "centre_m", "width_m", "height_m", "ring_m", "name", "operator")
    t("every field select_site.py reads is present",
      all(k in cb[0] for k in need), ", ".join(need))

    # 4. osm_id IS A STRING, as fetch_geometry emits and select_site compares.
    t("osm_id is a string, not an int", isinstance(cb[0]["osm_id"], str), repr(cb[0]["osm_id"]))

    # 5. A STANDALONE KIND MUST BE REFUSED, not quietly built with an invented receptor.
    t("PAIRED_KINDS excludes standalone", "standalone" not in PAIRED_KINDS,
      "kinds accepted: %s" % ", ".join(PAIRED_KINDS))

    # 6. THE PAIR LIST IS NOT EMPTY, WHICH IS THE ONE THING NOTHING CHECKED. Invariant 3 asserted
    #    the BUILDING fields and passed while `pairs` was hardcoded `[]` -- so the self-test went
    #    green through an overnight batch in which all 124 paired facilities failed. Two buildings
    #    ~350 m apart are inside the imported band, so a zero here is a defect, not geography.
    pr = candidate_pairs(cb)
    t("two buildings inside the band produce a pair", len(pr) == 1,
      "%d pair(s) from %d buildings at %.0f m (band %.0f-%.0f m)"
      % (len(pr), len(cb), sep, PAIR_MIN_M, PAIR_MAX_M))

    # 7. EVERY PAIR FIELD select_site READS, by name. Same reasoning as invariant 3, applied to the
    #    half of the file that had no coverage.
    pneed = ("source_osm_id", "receptor_osm_id", "separation_m", "bearing_a_to_b_deg",
             "combined_area_m2")
    t("every pair field select_site.py reads is present",
      bool(pr) and all(k in pr[0] for k in pneed), ", ".join(pneed))

    # 8. THE BAND IS ENFORCED AT BOTH ENDS. A pair closer than PAIR_MIN_M is one structure and a
    #    pair beyond PAIR_MAX_M is too dilute; neither may appear.
    t("separation band is enforced",
      all(PAIR_MIN_M <= p["separation_m"] <= PAIR_MAX_M for p in pr),
      "all %d pair(s) within %.0f-%.0f m" % (len(pr), PAIR_MIN_M, PAIR_MAX_M))

    # 9. THE TAGS REACH select_site's DATA-CENTRE GATE, tested against the real predicate rather
    #    than against our belief about it. A hall named for an operator the keyword list does not
    #    know ("Microsoft TRP1") must still pass on its OSM tag alone -- that is the exact case
    #    that rejected 11 of 11 pairs at the first facility of the batch.
    from select_site import is_datacentre                      # the real gate, not a copy
    tg = {"1": {"building": "data_center", "telecom": "data_center"}, "2": {"building": "yes"}}
    named = [("way/1", a, "Microsoft TRP1"), ("way/2", b, "Microsoft")]
    tagged = candidate_buildings(named, 39.0020, -77.0000, tg)
    t("a tagged hall passes select_site's own data-centre gate",
      is_datacentre(tagged[0]), "name %r + building=data_center" % tagged[0]["name"])
    t("tags are carried, not nulled",
      tagged[0]["building_tag"] == "data_center" and tagged[0]["telecom_tag"] == "data_center",
      "building_tag=%r telecom_tag=%r" % (tagged[0]["building_tag"], tagged[0]["telecom_tag"]))
    # And the honest negative: no tag and no keyword means the gate says no, which it should.
    t("an untagged non-keyword hall is still refused", not is_datacentre(tagged[1]),
      "name %r, building=yes -> refused" % tagged[1]["name"])

    print()
    print("SELF TEST: %s" % ("PASS" if ok else "FAIL"))
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
