# -*- coding: utf-8 -*-
"""ONE ROW PER REAL FACILITY -- the unit the agent actually runs on.  ZERO API CALLS.

    python build_national_registry.py            # writes data/geometry/national_registry.json
    python build_national_registry.py selftest   # the merge and classification rules, offline

WHY THIS FILE EXISTS: THE MAP AND THE PHYSICS WERE COUNTING DIFFERENT THINGS
    `dc_clusters.json` is keyed by a ~11 km DISCOVERY GRID CELL. That grid was a convenience for
    batching Overpass queries and it is not a measurement of anything: gotcha #150 recorded two real
    Georgia data centres 280 m apart landing in adjacent cells and being labelled "isolated", and
    gotcha #152 recorded Chicago's committed pair straddling a cell boundary and producing two map
    dots for one site. One cell can hold 81 buildings or one.

    The unit the SOLVER cares about is the connected component of buildings within its validated
    600 m range -- a campus is one facility, a lone hall is one facility. `build_national_pairs.py`
    already computes those components (639 of them). This file makes that the published unit, so
    "hover a dot and see the exact data centre" names a facility rather than a grid square.

THE THREE KINDS, and why none of them is a refusal
    standalone       no other tagged data centre inside the solver's 600 m validated range. The
                     plume term is ZERO BY GEOMETRY -- there is no neighbour exhaust to model. Real,
                     favourable, and the honest majority of the country.
    paired_clear     a real internal pair clears the 60 m facade floor. The existing, unmodified
                     pairwise physics runs on it.
    paired_advisory  every internal pair sits INSIDE the 60 m floor. The plume is not modelled and
                     -- unlike a standalone site -- that is NOT neutral: RECIRCULATION-PHYSICS.md
                     sections 5 and 171-188 state that below ~60 m the 30 m intake disc physically
                     overlaps the condenser bank, so any number would be an artefact, and that the
                     TIGHTER the pair the LARGER the real recirculation. So the decision still runs
                     on FortyGuard's own temperature/humidity/air-quality perception, and the site
                     carries an on-screen advisory that its bound may be optimistic. Published with
                     the measured gap, never silently.

THE MERGE, AND ITS LIMIT
    Two halls whose real footprints are 0.00 m apart are one building that OSM happens to record as
    two ways -- measured examples: `Iron Mountain AZP-1 + AZP-2`, `Verizon + Verizon`,
    `T5@Cleveland + T5@Cleveland`, all at 0.00 m with the same operator on both halls. Treating them
    as a source/receptor pair would measure a plume crossing a gap that does not exist.
    So a two-building group whose real edge-to-edge gap is under MERGE_GAP_M is recorded as ONE
    structure and becomes standalone.
    ⚠ THE LIMIT, STATED: this does not make recirculation go away, it makes it SELF-recirculation --
    one building's own exhaust re-entering its own intake. That is not modelled anywhere in this
    project, at any site, including the three shipped ones: `build_site.py` puts the bank on the
    SOURCE ring and the intake outside the RECEPTOR's facade, so the only quantity ever computed is
    the neighbour's exhaust arriving at my intake. It is the primary case ASHRAE Handbook Ch. 46 --
    this project's own cited source -- is about. Merging is therefore CONSISTENT with how every
    existing site is treated, not a special allowance, and the limitation is published per facility
    rather than implied.

WHAT THIS FILE DOES NOT DO
    It does not assign a weather station (S5), it does not screen imagery (S6), and it does not buy
    a FortyGuard field (S7). Every facility here carries `weather: null`, `imagery: null` and
    `fortyguard_field: null` -- ABSENT, explicitly, so a later stage fills them in and nothing
    downstream can mistake "not yet done" for "done and fine" (gotcha #74).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")
sys.path.insert(0, HERE)
# REUSED UNCHANGED, never reimplemented (gotcha #12): `longest_edge` and `to_metres` are the same
# functions `build_site.py` and `measure_national_gaps.py` measure real geometry with, and
# `BANK_DEPTH_M` is the same constant the solver places the condenser bank with. A second
# implementation of "how long is this wall" would be a second answer waiting to disagree.
from build_site import BANK_DEPTH_M, longest_edge                    # noqa: E402
from fetch_geometry import to_metres                                 # noqa: E402
# ONE definition of "is this a building", shared with the gate that produced the verdicts.
from measure_national_gaps import is_building_footprint              # noqa: E402

# The solver's validated range. Project Prairie Grass (1956) validated surface-layer dispersion at
# 150-600 m; this solver has never been checked against reality past 600 m and a near-field
# building-wake model has no business being extrapolated to kilometre scale. Imported in spirit from
# build_national_pairs.py, which computed the components -- re-read from that file's own header
# below rather than restated here, so the two cannot drift.
MIN_GAP_M = 60.0          # = INTAKE_STANDOFF_M + INTAKE_RADIUS_M + BANK_DEPTH_M/2, see build_site.py
MERGE_GAP_M = 5.0         # below this, two footprints are one structure. See "THE MERGE" above.


def facade_len(ring_rec):
    """The longest wall of one OSM footprint, in metres, via the project's own operators.

    The stored ring is [[lat, lon], ...]; `to_metres` expects [{"lat":…, "lon":…}] plus an origin,
    so the conversion happens here rather than by giving `to_metres` a second input shape to
    support -- one function, one contract.
    """
    g = ring_rec["geometry"]
    if not g or len(g) < 3:
        return 0.0
    lat0 = sum(p[0] for p in g) / len(g)
    lon0 = sum(p[1] for p in g) / len(g)
    ring = to_metres([{"lat": p[0], "lon": p[1]} for p in g], lat0, lon0)
    c = (sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring))
    return float(longest_edge(ring, c)[2])


def haversine_m(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _standalone_reason(nearest_m, merged_gap_m=None):
    """The wording for a facility with no neighbour inside the validated range.

    🔴 THIS SAYS "NOT MODELLED", NEVER "ZERO", AND THE DIFFERENCE IS THE WHOLE POINT.
    The first version of this function wrote "the plume term is zero by geometry" -- which is
    exactly the framing NATIONAL-BUILD-PLAN.md section 0.2 had already researched and REJECTED:
    a workflow's own adversarial verify step returned NOT_DEFENSIBLE, because this solver
    under-predicts rise by 5-25 % at these distances (N-35, 67 Prairie Grass experiments) and
    assuming zero past a cutoff is "biased in the unsafe direction, which is worse than the last
    invented-constant scar (#49), not milder".

    WHY IT MATTERS QUANTITATIVELY, measured over this registry: 23 of 405 standalone facilities
    (5.7 %) have a neighbour between 600 and 700 m -- as little as 2 % outside the boundary, with
    the closest at 612 m. For those, "zero" would be an assertion about physics the tool has never
    been checked against. For a facility 373 km from anything it is self-evident. Publishing the
    MEASURED DISTANCE in the reason lets a reader tell those two cases apart without this code
    inventing a second threshold to separate them.
    """
    head = ("The two tagged footprints are %.2f m apart -- one structure recorded as two OSM ways, "
            "not a source/receptor pair, so there is no facade between them for a plume to cross. "
            % merged_gap_m) if merged_gap_m is not None else ""
    d = ("%.0f m" % nearest_m) if nearest_m is not None else "an unmeasured distance"
    return (head +
            "Recirculation from a neighbour is NOT MODELLED here: the nearest other tagged data "
            "centre is %s away, outside the 150-600 m range this solver has been validated "
            "against (Project Prairie Grass, 67 field experiments). That is a statement about this "
            "tool's validated domain, NOT a claim that the effect is zero -- assuming zero past a "
            "cutoff was researched and rejected as biased in the unsafe direction. The "
            "free-cooling decision runs on FortyGuard's own temperature, humidity and air-quality "
            "perception, the same gates every paired site also uses." % d)


def classify(n_members, verdict, gap_m, nearest_m=None, longest_facade_m=None,
             n_buildings=None):
    """(kind, plume_modelled, reason) for one group. Pure, so the self-test can exercise it.

    ORDER MATTERS THREE TIMES OVER, and each step answers a question the next one presumes:
      1. Is there a BUILDING here at all, or only a land parcel? Everything below assumes a facade.
      2. Is that building big enough to host the modelled plant? The plume geometry is meaningless
         on a 4.7 m cabinet.
      3. Only then: is there a neighbour, and how far away is its facade?
    The merge is tested before the advisory for the same reason: a two-hall building recorded as two
    OSM ways must not be reported as a facility with a dangerous facade gap, because there is no
    facade between them.
    """
    # ---- IS THERE A BUILDING? A property line is not a facade. ------------------------------
    # OSM applies `telecom=data_center` to land parcels as well as halls -- 87 of 1,622 tagged ways
    # carry no `building=*` tag, 60 explicitly `landuse`, up to 247 hectares. The parcel is real
    # EVIDENCE that a data centre is there, and the site is shown because of it; what it is not is
    # a building this model can place a condenser bank on. Before this branch existed, the largest
    # such polygon was published as a facility with a 1,489.8 m "wall".
    if n_buildings is not None and n_buildings < 1:
        return ("boundary_only", False,
                "OpenStreetMap records this site as a land parcel (a `landuse`/`telecom` polygon), "
                "not as a building. The parcel is real evidence that a data centre is here -- and "
                "is why the site is shown -- but there is no building footprint to place a "
                "condenser bank on, so no plume is modelled and no hours or dollar figure are "
                "published. What is missing is a mapped building outline, not the data centre.")
    # ---- SCALE. Derived from an EXISTING constant, not a new one. --------------------------
    # OSM's `telecom=data_center` tag covers a hyperscale hall and a street-side equipment cabinet
    # equally: measured on this registry, the smallest tagged "data centre" has a 4.7 m longest wall
    # and a 19 m2 footprint, and the set includes "Modesto Junior College West Data Center",
    # "Family History Center", "CTI Biopharma" and "Norma Beach Cable Landing Station" -- server
    # rooms and cable huts, not plants with mechanical chillers.
    #
    # The floor is NOT a judgement about those buildings and NOT a chosen number. `BANK_DEPTH_M` is
    # the depth of the condenser bank this project's solver places on a facade (build_site.py). A
    # building whose LONGEST wall is shorter than the bank is deep cannot host the modelled bank at
    # all -- the geometry is impossible, not merely unlikely. So this is the instrument declaring
    # where it does not apply, which is the same kind of statement as the 600 m validated range, and
    # it introduces no constant that "point at the constant" could catch.
    #
    # Reporting "chiller-hours avoided per MW of IT load" for a 19 m2 hut would be a number about a
    # chiller plant that is not there -- requirement 4, never claim a data centre that does not
    # exist. These are PUBLISHED AND COUNTED, never deleted: the tag is real, the building is real,
    # and what is refused is only the claim that our model describes it.
    if longest_facade_m is not None and longest_facade_m < BANK_DEPTH_M:
        return ("below_model_scale", False,
                "This building's longest wall is %.1f m, shorter than the %.0f m depth of the "
                "condenser bank this project's solver places on a facade -- so the modelled plant "
                "cannot be placed on it at all. OSM's `telecom=data_center` tag covers everything "
                "from a hyperscale hall to a street-side equipment cabinet, and at this scale it is "
                "a server room or a cable hut rather than a facility with mechanical chillers. The "
                "building is real and is shown; what is refused is the claim that this model "
                "describes it. No hours and no dollar figure are published for it."
                % (longest_facade_m, BANK_DEPTH_M))
    # 🔴 EVERY BRANCH BELOW COUNTS BUILDINGS, NOT TAGGED WAYS, AND IT USED TO COUNT WAYS.
    # Caught by this module's own self-test: a facility with ONE building and TWO land parcels has
    # `n_members == 3`, so it fell past the lone-building branch, past the merge branch, and landed
    # on `paired_advisory` -- publishing an advisory about a dangerous FACADE GAP for a site that
    # has no second facade to be close to. The number that decides whether a pairing exists is the
    # count of real footprints; the count of tagged ways includes fence lines.
    n_b = n_members if n_buildings is None else n_buildings
    if n_b == 1:
        return ("standalone", False, _standalone_reason(nearest_m))
    if verdict == "clear":
        return ("paired_clear", True,
                "A real internal pair clears the %.0f m facade floor, so the plume is solved on "
                "this facility's own footprints." % MIN_GAP_M)
    if n_b == 2 and gap_m is not None and gap_m < MERGE_GAP_M:
        return ("standalone", False, _standalone_reason(nearest_m, merged_gap_m=gap_m))
    return ("paired_advisory", False,
            "Every internal pair is closer than the %.0f m measurement floor (best %.2f m). The "
            "30 m intake disc would overlap the condenser bank, so any rise this solver produced "
            "would be an artefact. ADVISORY: recirculation here is likely LARGER than at any "
            "shipped site and is not measurable with this instrument, so the safety bound below "
            "may be optimistic. The decision runs on FortyGuard's own temperature, humidity and "
            "air-quality perception alone." % (MIN_GAP_M, gap_m if gap_m is not None else -1.0))


def selftest():
    """The classification rule, against cases whose right answer is already known."""
    ok = True

    def t(name, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("   [%s] %-58s %s" % ("PASS" if good else "FAIL", name, got))

    def tb(name, cond, detail=""):
        """For BOOLEAN assertions. `t()` compares got == want, so passing a bool against a
        description string is always False -- which is how the three wording assertions below first
        reported FAIL while two of them were actually true. A test harness that can report a
        passing condition as a failure is as bad as one that reports the reverse."""
        nonlocal ok
        ok = ok and bool(cond)
        print("   [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    t("a lone building is standalone", classify(1, None, None, 7000.0)[0], "standalone")
    t("a clear pair is paired_clear", classify(2, "clear", 118.4, 900.0)[0], "paired_clear")
    # Ashburn's own committed pair clears by 0.3 m. It must NOT be merged and must NOT be advisory.
    t("Ashburn's 60.3 m pair stays paired_clear", classify(2, "clear", 60.3, 900.0)[0],
      "paired_clear")
    t("two halls 0.00 m apart merge to standalone",
      classify(2, "too_close", 0.0, 5000.0)[0], "standalone")
    t("a 4.79 m pair merges to standalone", classify(2, "too_close", 4.79, 5000.0)[0], "standalone")
    # 20 m is a real gap that is simply below the instrument's floor: advisory, never merged.
    t("a 20.07 m pair is advisory, not merged", classify(2, "too_close", 20.07, 5000.0)[0],
      "paired_advisory")
    t("a 3-building tight group is advisory",
      classify(3, "too_close", 12.0, 5000.0)[0], "paired_advisory")
    # A big group is never merged, even if its closest pair touches: merging one pair still leaves
    # the others, and the recorded gap is already the BEST in the group.
    t("a 4-building group with a touching pair stays advisory",
      classify(4, "too_close", 0.0, 5000.0)[0], "paired_advisory")
    t("a standalone facility never claims a modelled plume",
      classify(1, None, None, 7000.0)[1], False)
    t("only paired_clear models the plume", classify(2, "clear", 99.0, 900.0)[1], True)

    # 🔴 THE WORDING IS PART OF THE CORRECTNESS, not presentation. "zero" past a distance was
    # researched and REJECTED as unsafe-biased (NATIONAL-BUILD-PLAN section 0.2), and the first
    # version of this file shipped that exact phrasing. These two assertions are why it cannot
    # come back.
    r = classify(1, None, None, 612.0)[2]
    tb("a standalone reason says NOT MODELLED and disclaims 'zero'",
       ("NOT MODELLED" in r) and ("NOT a claim that the effect is zero" in r),
       "asserts not-modelled AND explicitly refuses the zero claim")
    tb("a standalone reason publishes the measured distance", "612 m" in r, "quotes 612 m")
    tb("a standalone reason cites the validation domain", "150-600 m" in r and "Prairie Grass" in r,
       "names Prairie Grass and the 150-600 m range")
    tb("the advisory says the bound may be OPTIMISTIC, in those words",
       "optimistic" in classify(2, "too_close", 20.07, 5000.0)[2],
       "states the direction of the risk, not just its existence")

    # ---- IS IT A BUILDING AT ALL? This outranks everything, including scale: a 116 ha land
    # parcel is not "too big", it is not a building.
    t("a parcel with no building is boundary_only",
      classify(1, None, None, 5000.0, 1489.8, n_buildings=0)[0], "boundary_only")
    t("boundary_only outranks a clear pairing",
      classify(2, "clear", 400.0, 900.0, 800.0, n_buildings=0)[0], "boundary_only")
    t("one real building among parcels is still classified normally",
      classify(3, None, None, 5000.0, 190.0, n_buildings=1)[0], "standalone")
    tb("a boundary_only reason blames the MAP, not the site",
       "What is missing is a mapped building outline, not the data centre"
       in classify(1, None, None, 5000.0, 800.0, n_buildings=0)[2],
       "the parcel is evidence the site is real")
    tb("a boundary_only facility publishes no hours or dollars",
       "no hours or dollar figure are published"
       in classify(1, None, None, 5000.0, 800.0, n_buildings=0)[2], "stated in the reason")

    # ---- SCALE. The floor is BANK_DEPTH_M, an existing constant, so these cases pin the
    # BOUNDARY behaviour rather than a number this file chose.
    t("a 4.7 m cabinet is below model scale",
      classify(1, None, None, 7000.0, 4.7)[0], "below_model_scale")
    t("a wall exactly at the bank depth is NOT below scale",
      classify(1, None, None, 7000.0, BANK_DEPTH_M)[0], "standalone")
    t("a 19.9 m wall IS below scale", classify(1, None, None, 7000.0, 19.9)[0],
      "below_model_scale")
    # Scale is tested FIRST: a tiny building must not be reported as a facility with a dangerous
    # facade gap, because the interesting fact about it is that our model does not describe it.
    t("scale outranks the tight-facade advisory",
      classify(2, "too_close", 1.0, 5000.0, 6.0)[0], "below_model_scale")
    t("scale outranks a clear pairing", classify(2, "clear", 400.0, 900.0, 8.0)[0],
      "below_model_scale")
    # AND THE CONTROL THAT MATTERS MOST: a real shipped site must be untouched by all of this.
    # Ashburn's committed source hall is a 190 m building on a 60.3 m gap.
    t("Ashburn's own 190 m hall is unaffected",
      classify(2, "clear", 60.3, 900.0, 190.0)[0], "paired_clear")
    tb("an unmeasurable facade SKIPS the scale test rather than passing it",
       classify(1, None, None, 7000.0, None)[0] == "standalone",
       "no ring -> not silently marked below scale, and not silently cleared either")
    r2 = classify(1, None, None, 7000.0, 4.7)[2]
    tb("a below-scale reason publishes the measured wall and the floor",
       "4.7 m" in r2 and "20 m" in r2, "quotes both numbers")
    tb("a below-scale reason refuses the CLAIM, not the building",
       "building is real and is shown" in r2, "the building is shown; the model's claim is not")
    print("\n   SELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def load(name):
    p = os.path.join(GEOM, name)
    if not os.path.exists(p):
        raise SystemExit("%s missing -- run the national discovery chain first" % name)
    return json.load(open(p, encoding="utf-8"))


def main(argv):
    if argv and argv[0] == "selftest":
        return selftest()

    print("=" * 78)
    print("NATIONAL REGISTRY -- one row per real facility.  ZERO API CALLS.")
    print("=" * 78)

    grp = load("national_building_groups.json")
    ver = load("national_gate_verdicts.json")
    cen = load("national_building_centres.json")["centres"]
    reg = load("dc_clusters.json")["clusters"]
    sbc = load("state_by_coord.json")
    rings = load("national_geometry.json")["rings"]

    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        raise SystemExit("timezonefinder is required: a state-level timezone guess is not "
                         "acceptable (Arizona does not observe DST, and env_params already cost "
                         "this project a nine-hour bug). pip install timezonefinder")
    tf = TimezoneFinder()

    groups, verdicts = grp["groups"], ver["verdicts"]
    # Entry -> state, so a facility inherits the state its own cell was REVERSE-GEOCODED to. Never
    # the query bbox's state: gotcha, Switch Las Vegas was priced on California power because
    # California's search box reaches -114.1.
    entry_state = {k: e.get("state") for k, e in reg.items()}

    # NEAREST OTHER TAGGED DATA CENTRE, per facility. For a standalone site this is the number that
    # makes "nothing within 600 m" a measurement rather than an assertion, so it is published.
    # O(n^2) over 1,622 points is ~1.3 M haversines: about a second, and worth it for an exact
    # answer over a spatial index that would need its own correctness argument.
    pts = [(bid, (c["lat"], c["lon"])) for bid, c in cen.items()]
    own_group = {}
    for gk, gv in groups.items():
        for m in gv["members"]:
            own_group[m] = gk

    facilities, counts = {}, {}
    for gk, gv in sorted(groups.items()):
        members = gv["members"]
        v = verdicts.get(gk) or {}
        gap = v.get("real_edge_to_edge_gap_m")

        cs = [(cen[m]["lat"], cen[m]["lon"]) for m in members if m in cen]
        centre = [sum(x[0] for x in cs) / len(cs), sum(x[1] for x in cs) / len(cs)]

        # MEASURED FIRST, because the standalone wording quotes it. A reason that says "not
        # modelled" without saying how far away the nearest neighbour is leaves the reader unable
        # to tell 612 m from 373 km, and those two deserve very different amounts of trust.
        nearest_m, nearest_id = None, None
        for bid, p in pts:
            if own_group.get(bid) == gk:
                continue
            d = min(haversine_m(c, p) for c in cs)
            if nearest_m is None or d < nearest_m:
                nearest_m, nearest_id = d, bid

        # ROUND ONCE, HERE, AND USE THE SAME VALUE FOR THE FIELD AND THE PROSE.
        # This was rounded twice from two different starting points -- the published field from
        # `round(nearest_m, 1)` and the sentence from the raw float -- and on 23 facilities the two
        # disagreed by 1 m, because "%.0f" rounds half to EVEN while the raw value was just above
        # the half. So `nearest_other_tagged_dc_m: 1980.5` sat beside prose reading "1981 m away".
        # Cosmetic in size, but it is the "a number in prose that no check re-reads" family, and
        # methodology rule 11 is exactly this: generate the prose from the data, once.
        nearest_r = round(nearest_m, 1) if nearest_m is not None else None

        # THE LONGEST WALL, measured on this facility's own real BUILDING footprints -- parcels
        # excluded, because the longest edge of a 116 ha landuse polygon is a fence line and was
        # being published as a 1,489.8 m facade. `None` when no ring is present, in which case the
        # scale test is SKIPPED rather than assumed to pass (gotcha #74).
        blds = [m for m in members if is_building_footprint(rings.get(m))]
        edges = [facade_len(rings[m]) for m in blds]
        longest = round(max(edges), 1) if edges else None

        kind, modelled, reason = classify(len(members), v.get("verdict"), gap, nearest_r, longest,
                                         n_buildings=len(blds))
        counts[kind] = counts.get(kind, 0) + 1

        states = sorted({entry_state.get(e) for e in gv.get("source_entries", [])} - {None})
        tz = tf.timezone_at(lat=centre[0], lng=centre[1])
        names = [n for n in (gv.get("names") or []) if n]
        # MERGED means "two BUILDINGS close enough to be one structure" -- so it has to test the
        # building count and the measured gap, not the tagged-way count. This read
        # `len(members) == 2`, which flagged a single hall standing next to a land parcel as a
        # merged two-hall structure, with `facade_gap_m: None`. Third instance of the same
        # ways-vs-buildings confusion in one file; the first two were caught by the self-test and
        # this one by the audit crashing on the None it produced.
        merged = (kind == "standalone" and len(blds) == 2
                  and gap is not None and gap < MERGE_GAP_M)

        facilities[gk] = {
            "members": members, "n_buildings": len(members),
            "centre": centre, "state": states[0] if len(states) == 1 else (states or [None])[0],
            "states_spanned": states, "tz": tz,
            "names": names, "operators": [o for o in (gv.get("operators") or []) if o],
            "source_entries": gv.get("source_entries", []),
            "kind": kind,
            # MEASURED, and published even when it changes nothing, because it is the number the
            # scale classification turns on and a reader must be able to see it rather than take
            # the verdict on trust.
            "longest_facade_m": longest,
            "model_scale_floor_m": BANK_DEPTH_M,
            "n_rings_present": len(edges),
            # PUBLISHED SEPARATELY, because "how many tagged ways" and "how many of them are
            # buildings" are different questions and one number answered both badly.
            "n_building_footprints": len(blds),
            "n_parcel_ways": len(members) - len(blds),
            # The raw `building=*` value per member, carried through so the imagery stage can see
            # `construction` -- a real structure with a real outline but no operating plant -- and
            # judge it on a photograph rather than on a crowd-sourced tag. See
            # measure_national_gaps.BUILDING_TAGS_NEEDING_IMAGERY_REVIEW.
            "building_tags": {m: ((rings.get(m) or {}).get("tags") or {}).get("building")
                              for m in members},
            "plume": {
                "modelled": modelled, "reason": reason,
                "facade_gap_m": gap,
                "best_pair": v.get("best_pair"),
                "merged_into_one_structure": merged,
                "nearest_other_tagged_dc_m": nearest_r,
                "nearest_other_tagged_dc_id": nearest_id,
                # HOW FAR OUTSIDE THE VALIDATED DOMAIN, as a ratio rather than a label. 1.02 means
                # "2 % past the edge of what Prairie Grass validated" and 622 means "self-evidently
                # nothing nearby". Published as a number so a reader can rank the honesty of the
                # not-modelled claim per facility, WITHOUT this code inventing a second threshold
                # to bucket them (the #49 scar: a constant that decides something is a constant
                # even when it only decides a label).
                "nearest_over_validated_range": (
                    round(nearest_r / grp["solver_validated_range_m"], 3)
                    if nearest_r is not None else None),
                "self_recirculation_modelled": False,
                "self_recirculation_note":
                    "A building's own exhaust re-entering its own intake is not modelled at ANY "
                    "site in this project. build_site.py places the condenser bank on the SOURCE "
                    "ring and the intake outside the RECEPTOR's facing facade, so the only "
                    "quantity computed is the neighbour's exhaust arriving at my intake. Stated "
                    "because it is the primary case ASHRAE Handbook Ch. 46 addresses.",
            },
            # ABSENT, EXPLICITLY. A later stage fills these; until then nothing may read them as
            # "checked and fine" (gotcha #74: a skipped gate reported as a pass).
            "weather": None, "imagery": None, "fortyguard_field": None,
        }

    out = {
        "generated_by": "src/build_national_registry.py",
        "api_calls_made": 0,
        "unit": "one connected component of tagged data-centre buildings within the solver's "
                "600 m validated range -- a campus is one facility, a lone hall is one facility",
        "solver_validated_range_m": grp["solver_validated_range_m"],
        "min_gap_m": MIN_GAP_M, "merge_gap_m": MERGE_GAP_M,
        "n_facilities": len(facilities), "n_buildings": grp["n_buildings"],
        "counts": counts,
        "kinds_are_not_refusals":
            "standalone / paired_clear / paired_advisory are all RUN. Refusal in this project is "
            "reserved for facts about the physical world -- rooftop-mounted plant outside a "
            "ground-plane model's view, and a tagged cluster that was never built -- both decided "
            "on imagery (G5), which no facility here has been through yet.",
        "facilities": facilities,
    }

    # MECHANICAL TRIPWIRE, not a printed reassurance. discover_dc_clusters.py lost one real site to
    # a key collision and the arithmetic is what caught it; this refuses to write rather than
    # publish a file whose own counts do not close.
    if sum(counts.values()) != len(facilities):
        raise SystemExit("counts %r do not sum to %d facilities" % (counts, len(facilities)))
    if sum(f["n_buildings"] for f in facilities.values()) != grp["n_buildings"]:
        raise SystemExit("facility members do not partition the %d buildings" % grp["n_buildings"])

    p = os.path.join(GEOM, "national_registry.json")
    json.dump(out, open(p, "w", encoding="utf-8"), allow_nan=False)
    print("   %d facilities from %d buildings" % (len(facilities), grp["n_buildings"]))
    for k in sorted(counts):
        print("      %-16s %4d" % (k, counts[k]))
    n_tz = len({f["tz"] for f in facilities.values()})
    n_st = len({f["state"] for f in facilities.values() if f["state"]})
    print("   %d timezones, %d states" % (n_tz, n_st))
    miss_tz = [k for k, f in facilities.items() if not f["tz"]]
    miss_st = [k for k, f in facilities.items() if not f["state"]]
    if miss_tz:
        print("   %d facility(ies) with NO timezone -- listed, not guessed: %s"
              % (len(miss_tz), ", ".join(miss_tz[:5])))
    if miss_st:
        print("   %d facility(ies) with NO state -- they cannot be priced until resolved: %s"
              % (len(miss_st), ", ".join(miss_st[:5])))
    print("   wrote %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
