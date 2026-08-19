# -*- coding: utf-8 -*-
"""THE METRO REGISTRY -- which places the agent can be pointed at, and what each one needs.

    python metros.py            # list the registry and what exists on disk for each

ZERO API CALLS. ZERO CREDENTIALS.

--------------------------------------------------------------------------------------------
WHY A REGISTRY, AND WHAT IT DELIBERATELY DOES NOT CLAIM
--------------------------------------------------------------------------------------------
Everything shipped so far was pinned to ONE site in Ashburn: `fetch_geometry.py` hard-coded a
Loudoun County bbox and wrote `ashburn_candidates.json`, and six other modules hard-coded that
filename. So the agent could not be pointed anywhere else, which made "pick your data centre" an
interface promise the engine could not keep.

**THIS FILE MAKES NO CLAIM ABOUT DATA-CENTRE MARKET RANKINGS.** It would be easy to write "Phoenix
is a top-five market" and it would be unsourced. What each entry carries instead is a bounding box,
a weather station, a timezone, and a stated BASIS for the box -- and whether a metro actually holds
usable geometry is then MEASURED by the Overpass fetch (how many buildings over 8,000 m2, how many
candidate pairs, what the true facade gaps are). A measurement beats an assertion, and the pipeline
needs the measurement anyway.

--------------------------------------------------------------------------------------------
WHAT EVERY SITE NEEDS, AND WHAT IT COSTS
--------------------------------------------------------------------------------------------
    building footprints   OpenStreetMap via Overpass          FREE, keyless, one request
    aerial imagery        ESRI World Imagery / USGS REST      FREE
    5-year weather        Iowa State ASOS archive             FREE, 60 month-chunks per station
    plume rise table      576 GPU solves on the real geometry FREE, 5-9 s
    FortyGuard field      /v1/heatmap                         4,220 CREDITS

Only the last line costs money. A site without it is still fully real -- real footprints, real
weather, its own conformal calibration, its own physics -- and the interface must say plainly that
no FortyGuard field was purchased for it rather than borrowing another site's.

🔴 THE CALIBRATION IS PER SITE AND CANNOT BE BORROWED. The Mondrian margins are quantiles of THAT
station's own forecast residuals. Showing KIAD's margins for a Phoenix site would be exactly the
kind of borrowed calibration this project refuses, so a metro without its own ASOS record has no
bound and must not be offered as if it did.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GEOM = os.path.join(ROOT, "data", "geometry")
WEATHER = os.path.join(ROOT, "data", "weather")
DEMO = os.path.join(ROOT, "demo")

# ---------------------------------------------------------------------------------------------
# Each bbox is ~7-12 km on a side, the scale at which two hyperscale halls a few hundred metres
# apart can be found. `basis` records HOW the box was chosen so a reader can check it, not trust it.
#
# 🔴 EVERY NON-ASHBURN BBOX IS THE `suggested_bbox` FROM data/geometry/dc_clusters.json, COPIED
# VERBATIM -- and that wording is load-bearing, because getting it wrong cost two wasted fetches:
#   attempt 1: a Phoenix box from memory        -> ten largest buildings were a shopping mall, a
#                                                  Dillards depot and a Walmart. 0 data centres.
#   attempt 2: the DISCOVERED cluster centroid, -> 12 buildings, "Dose Moving & Storage".
#              but re-derived as centre +-0.012    0 data centres. The real cluster spans 8 x 9.6 km;
#                                                  my box was 2.7 x 2.8 km around its midpoint.
#   attempt 3: the suggested_bbox verbatim      -> see the counts printed by `python metros.py`.
# The measurement was right both times and I substituted my own arithmetic for it twice. The check
# that matters is not "does the fetch return buildings" but "does it return buildings TAGGED as
# data centres", which is why `readiness()` reports that count and not just the total.
# ---------------------------------------------------------------------------------------------
METROS = {
    "ashburn": {
        # US state, for the EIA electricity tariff money.py sweeps. Explicit rather
        # than parsed out of `label`, because a prose field is not a data field.
        "state": "VA",
        "label": "Ashburn, Virginia",
        "bbox": (39.000, -77.500, 39.060, -77.410),
        "station": "IAD",
        "tz": "America/New_York",
        "candidates_file": "ashburn_candidates.json",   # PRE-EXISTING NAME -- do not rename
        "basis": "Loudoun County data-centre corridor; brackets the coordinate the earlier "
                 "FortyGuard work used as its site centre (39.0100, -77.4460)",
        "fortyguard_field": "purchased -- 9 heatmap calls, 8 saved fields plus a verified forecast",
        "climate_note": "mixed-humid: the dew-point gate and the dry-bulb limit both bind",
    },
    "phoenix": {
        # US state, for the EIA electricity tariff money.py sweeps. Explicit rather
        # than parsed out of `label`, because a prose field is not a data field.
        "state": "AZ",
        "label": "Mesa, Arizona",
        # DISCOVERED, not guessed. src/discover_dc_clusters.py found 10 OSM-tagged data centres
        # here (Apple Inc., EdgeConneX). The bbox this replaced was picked from memory and its ten
        # largest buildings were Chandler Fashion Center, a Dillards distribution centre and a
        # Walmart Supercenter -- it fell BETWEEN two real clusters. See that module's docstring.
        "bbox": (33.2933, -111.6931, 33.3652, -111.5891),   # suggested_bbox, verbatim
        # STATION CHANGED IWA -> FFZ, 2026-08-19, on MEASURED record quality.
        # KIWA sits 2.7 km from the cluster and looked ideal, but its five-year record came back
        # 81.70 %% complete with the gap structural rather than scattered: 4,454 hours in 2021 and
        # 5,747 in 2022 against ~8,520 in 2023-25, i.e. only 50.8 %% of 2021. It also returned a
        # lone 54.0 C reading with the next value at 46.0 -- a sensor fault. A 2021 probe across
        # every nearby station: KIWA 50.8 %%, KCHD 61.5 %%, KFFZ 99.1 %%, KPHX 99.8 %%, KSDL 99.7 %%.
        # The small municipal fields are the problem, not Arizona.
        # So: KFFZ (Falcon Field, Mesa), 99.1 %% coverage, MEASURED 16.7 km from the cluster.
        # 16.7 km is ~2x the 8.9 km between our own Ashburn site and KIAD. That is a REAL
        # degradation and it is not hidden: a more distant station has wider forecast residuals,
        # so the conformal margin widens automatically and the site earns FEWER hours. The bound
        # stays honest; the economics get worse. That is the system behaving correctly.
        "station": "FFZ",
        "tz": "America/Phoenix",
        "candidates_file": "phoenix_candidates.json",
        "basis": "OSM cluster of 10 tagged data centres (Apple Data Center, EdgeConneX PHX02) "
                 "at 33.3293, -111.6411, found by discover_dc_clusters.py. Station KFFZ chosen "
                 "on measured record completeness, not proximity -- see the comment above",
        "fortyguard_field": None,
        # NOTE America/Phoenix does NOT observe daylight saving. That is a real trap for the
        # site_window() helpers and exactly the class of bug gotcha #1 and #27 record.
        "climate_note": "hot-dry: dry-bulb should dominate and the 15 C dew-point gate should "
                        "rarely bind -- the opposite balance to Ashburn. TO BE MEASURED, not assumed",
    },
    "chicago": {
        # US state, for the EIA electricity tariff money.py sweeps. Explicit rather
        # than parsed out of `label`, because a prose field is not a data field.
        "state": "IL",
        "label": "Elk Grove Village, Illinois",
        # DISCOVERED: 11 tagged data centres (Aligned, Centersquare, Digital Realty).
        "bbox": (41.9010, -87.9885, 42.0111, -87.9025),      # suggested_bbox, verbatim
        "station": "ORD",          # MEASURED 4.4 km from the cluster centre
        "tz": "America/Chicago",
        "candidates_file": "chicago_candidates.json",
        "basis": "OSM cluster of 11 tagged data centres (Aligned, Centersquare, Digital Realty) "
                 "at 41.9560, -87.9455, found by discover_dc_clusters.py; KORD is 4.4 km away",
        "fortyguard_field": None,
        "climate_note": "cold: free cooling should be abundant and the binding constraint should "
                        "shift toward the switch budget. TO BE MEASURED",
    },
    "dulles": {
        # US state, for the EIA electricity tariff money.py sweeps. Explicit rather
        # than parsed out of `label`, because a prose field is not a data field.
        "state": "VA",
        "label": "Dulles corridor, Virginia",
        # DISCOVERED cluster VA_38.94_-77.56: 19 OSM-tagged data centres operated by AMAZON WEB
        # SERVICES, GOOGLE, MICROSOFT and CyrusOne in one box -- sample names Amazon IAD124, IAD125,
        # IAD62, IAD68, IAD81. suggested_bbox copied VERBATIM (see the warning at the top of METROS).
        "bbox": (38.9298, -77.5755, 38.9703, -77.4907),
        # THE POINT OF THIS SITE: station IAD is MEASURED 6.7 km from the cluster centre -- closer
        # than the 8.9 km between our own committed Ashburn site and the same station -- and the
        # 43,763-hour KIAD record ALREADY EXISTS. So this metro needs no 60-chunk ASOS fetch, no new
        # conformal calibration and carries no coverage-floor risk. That was the expensive and risky
        # part of adding Chicago; here it is already paid for.
        "station": "IAD",
        "tz": "America/New_York",
        "candidates_file": "dulles_candidates.json",
        "basis": "OSM cluster of 19 tagged data centres (Amazon Web Services, Google, Microsoft, "
                 "CyrusOne) at 38.9501, -77.5331, found by discover_dc_clusters.py; 6.7 km from "
                 "KIAD, whose five-year record is already on disk",
        "fortyguard_field": None,
        "climate_note": "same station and climate as the committed Ashburn site, so this isolates "
                        "GEOMETRY and OPERATOR from weather -- a genuinely different site, not a "
                        "different climate",
    },
    "santaclara": {
        # US state, for the EIA electricity tariff money.py sweeps. Explicit rather
        # than parsed out of `label`, because a prose field is not a data field.
        "state": "CA",
        "label": "Santa Clara, California",
        # DISCOVERED: 53 tagged data centres -- the second-densest cluster in the whole search,
        # after Ashburn's 106. Operators include AWS, Cologix and CoreSite.
        "bbox": (37.3492, -122.0037, 37.4106, -121.9273),    # suggested_bbox, verbatim
        "station": "SJC",          # MEASURED 4.3 km from the cluster centre
        "tz": "America/Los_Angeles",
        "candidates_file": "santaclara_candidates.json",
        "basis": "OSM cluster of 53 tagged data centres at 37.3799, -121.9655 -- the densest "
                 "found outside Ashburn -- via discover_dc_clusters.py; KSJC is 4.3 km away. Also "
                 "the location of the NetApp case ENERGY STAR documents and PLAN.md section 12 "
                 "already cites, so one claim in the deck ties to this site",
        "fortyguard_field": None,
        "climate_note": "mild marine: a narrow annual range, so the margin should be tight and the "
                        "hours plentiful. TO BE MEASURED",
    },
}

DEFAULT_METRO = "ashburn"

# Below this share of the 43,800 hours in five years, a station record is too gappy to fit 24
# hour-of-day conformal quantiles on. Measured consequence, not a preference: see readiness().
MIN_WEATHER_COVERAGE = 0.95


def metro_key():
    """Which metro the pipeline is operating on. Defaults to ashburn so every existing path,
    filename and audited number is unchanged unless a caller explicitly asks otherwise."""
    k = (os.environ.get("METRO") or DEFAULT_METRO).strip().lower()
    if k not in METROS:
        raise SystemExit("unknown METRO=%r. Known: %s" % (k, ", ".join(sorted(METROS))))
    return k


def metro(k=None):
    return METROS[k or metro_key()]


def candidates_path(k=None):
    return os.path.join(GEOM, metro(k)["candidates_file"])


def weather_file(k=None):
    """DERIVED from the station id, never written by hand.

    The phoenix entry carried `weather_file: "kphx_hourly_2021_2025.json"` while its station
    had already been corrected to IWA -- a filename asserting a station the pipeline was not
    going to fetch. Same class of drift as the hard-coded "alternating" split label and the
    "595 h/year" literal in the view: if a name describes a value, compute it from that value.
    Ashburn keeps its historical filename because that file exists and is audited."""
    m = metro(k)
    if m["station"] == "IAD":
        return "kiad_hourly_2021_2025.json"   # PRE-EXISTING, 43,763 records, do not rename
    return "k%s_hourly_2021_2025.json" % m["station"].lower()


def weather_path(k=None):
    return os.path.join(WEATHER, weather_file(k))


def geom_path(name, k=None):
    """Path for a per-site geometry artefact, e.g. geom_path("selected_site.json").

    ASHBURN KEEPS THE UNSUFFIXED NAME, and that is not cosmetic: `selected_site.json`,
    `refusal_rank.json`, `direction_table.json` and `solver_site_*.json` are read by modules whose
    outputs `audit.py` re-checks against 61 published numbers. Renaming them would invalidate the
    audited chain for no benefit. Every other metro gets a prefix, so the four sites coexist without
    a single conditional in the downstream scripts.
    """
    kk = k or metro_key()
    return os.path.join(GEOM, name if kk == DEFAULT_METRO else "%s_%s" % (kk, name))


# NOTE an `imagery_dir()` helper was written here for the screening step and removed again the same
# hour: audit.py's dead-code check failed the build because nothing referenced it yet. That is the
# check doing its job -- speculative helpers are how a tree accumulates functions no caller wants.
# It goes back in when screen_architecture.py is actually made metro-aware.


def demo_path(name, k=None):
    """Path for a per-site artefact in demo/, e.g. demo_path("trace.json").

    SAME CONVENTION AS `geom_path`, for the same reason: ashburn keeps the unsuffixed name because
    `audit.py` re-reads 68 published numbers out of `trace.json`, `backtest.json`, `rolling.json`
    and `money.json`, and renaming them would invalidate the audited chain for no benefit. Every
    other metro gets a prefix, so three sites coexist with no conditional downstream.
    """
    kk = k or metro_key()
    return os.path.join(DEMO, name if kk == DEFAULT_METRO else "%s_%s" % (kk, name))


def site_centre(k=None):
    """(lat, lon) midpoint of the committed pair, READ from the committed geometry.

    `agent.py` used to carry `SITE_CENTRE = (39.024017, -77.419691)` as a literal, which is fine
    while there is one site and wrong the moment there are three. Derived from the same
    `centre_latlon` fields `export_manifest` publishes, so the map marker and the agent cannot
    disagree about where a site is.
    """
    p = geom_path("selected_site.json", k)
    sel = json.load(open(p, encoding="utf-8"))
    a = sel.get("source_building", {}).get("centre_latlon")
    b = sel.get("receptor_building", {}).get("centre_latlon")
    if not a or not b:
        raise KeyError("%s has no centre_latlon for its committed pair" % p)
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def readiness(k):
    """What exists on disk for this metro. Nothing here is inferred -- it is all stat() calls."""
    m = METROS[k]
    cand = candidates_path(k)
    wx = weather_path(k)
    out = {"key": k, "label": m["label"], "station": "K" + m["station"], "tz": m["tz"],
           "geometry": os.path.exists(cand), "weather": os.path.exists(wx),
           "fortyguard_field": m["fortyguard_field"]}
    if out["geometry"]:
        try:
            d = json.load(open(cand, encoding="utf-8"))
            bl = d.get("buildings") or []
            pr = d.get("pairs") or []
            out["n_buildings"] = len(bl)
            out["n_pairs"] = len(pr)
            # THE REAL ADMISSION TEST, and it is not "did the fetch return buildings".
            # Two bboxes of mine returned plenty of buildings and NOT ONE data centre -- a shopping
            # mall, a Dillards depot, a Walmart, a moving-and-storage yard. The footprint filter
            # (8,000-400,000 m2) cannot tell a hyperscale hall from a mall, so the TAG has to.
            # A metro is only usable if it holds a pair where BOTH ends are tagged data centres,
            # because that is what the plume solver is being asked to model.
            isdc = {x["osm_id"]: (x.get("building_tag") == "data_center"
                                  or x.get("telecom_tag") == "data_center") for x in bl}
            out["n_tagged_dc"] = sum(1 for v in isdc.values() if v)
            dcp = [q for q in pr
                   if isdc.get(q["source_osm_id"]) and isdc.get(q["receptor_osm_id"])]
            out["n_dc_to_dc_pairs"] = len(dcp)
            if dcp:
                best = max(dcp, key=lambda q: q["combined_area_m2"])
                out["best_dc_pair"] = "%s -> %s (%.0f m)" % (
                    best.get("source_name") or best["source_osm_id"],
                    best.get("receptor_name") or best["receptor_osm_id"],
                    best["separation_m"])
        except Exception as e:
            out["geometry_error"] = str(e)[:60]
    if out["weather"]:
        try:
            d = json.load(open(wx, encoding="utf-8"))
            out["n_hours"] = len(d.get("hours") or {})
            wm = d.get("meta") or {}
            out["coverage_frac"] = wm.get("coverage_frac")
            out["suspect_high_reading_c"] = wm.get("suspect_high_reading_c")
            # A COVERAGE FLOOR, because a gappy record cannot carry a per-hour-of-day quantile.
            # KIWA sat 2.7 km from the Mesa cluster -- the closest station of any candidate -- and
            # came back 81.70 % complete with only 50.8 % of 2021. Twenty-four hourly groups fitted
            # on a record that thin gives some groups a handful of residuals, and a conformal
            # quantile needs 9 just to express 90 %. Proximity lost to completeness, and KFFZ at
            # 16.7 km was taken instead.
            out["weather_ok"] = bool(out["coverage_frac"] is not None
                                     and out["coverage_frac"] >= MIN_WEATHER_COVERAGE)
        except Exception as e:
            out["weather_error"] = str(e)[:60]
    # A metro is OFFERABLE only with geometry AND its own weather: without the station record it has
    # no conformal calibration of its own, and borrowing one would be a lie about the bound.
    # Geometry alone is not enough, and neither is geometry + weather: the geometry must contain a
    # real data-centre pair, or the solver is faithfully modelling a warehouse.
    out["offerable"] = bool(out["geometry"] and out["weather"] and out.get("weather_ok")
                            and out.get("n_dc_to_dc_pairs", 0) > 0)
    return out


def export_manifest():
    """Write demo/sites.json -- what the interface is allowed to offer, and why.

    The demo must not decide for itself which sites are real: `offerable` already encodes the three
    gates (own geometry, a data-centre-to-data-centre pair, and a >= 95 % own weather record), and a
    site that fails any of them has no honest conformal bound. Exporting the same computation keeps
    the picker and the engine from disagreeing.

    Sites REJECTED by the imagery scope gate are exported too, with their reason. Hiding them would
    throw away the most credible thing this project can show -- that five sites were screened and
    two were refused on evidence.
    """
    demo = os.path.join(ROOT, "demo")
    arch = {}
    ap = os.path.join(GEOM, "architecture_verdicts.json")
    if os.path.exists(ap):
        a = json.load(open(ap, encoding="utf-8"))
        for k in a:
            if k.startswith("assessed_"):
                for v in a[k]:
                    arch.setdefault(v.get("metro", DEFAULT_METRO), []).append(v)
    sites = []
    for k in sorted(METROS):
        r = readiness(k)
        m = METROS[k]
        verdicts = arch.get(k, [])
        committed = None
        cp = geom_path("selected_site.json", k)
        if os.path.exists(cp):
            try:
                sel = json.load(open(cp, encoding="utf-8"))
                sb, rb = sel.get("source_building", {}), sel.get("receptor_building", {})
                committed = {
                    "source_osm_id": sel["selected"]["source_osm_id"],
                    "receptor_osm_id": sel["selected"]["receptor_osm_id"],
                    "source_name": sb.get("name") or sb.get("operator"),
                    "receptor_name": rb.get("name") or rb.get("operator"),
                    "source_latlon": sb.get("centre_latlon"),
                    "receptor_latlon": rb.get("centre_latlon"),
                    # A FIELD NAME MUST NOT ASSERT A QUANTITY IT DOES NOT HOLD (gotcha #62/#67).
                    # This read `refusal_measurement.true_gap_m or selected.separation_m` -- and
                    # `refusal_measurement` has no `true_gap_m`, so the fallback always fired and
                    # `facade_gap_m` shipped the CENTROID SEPARATION: 165.5 m for Ashburn, whose
                    # real facade-to-facade gap is 60.3 m and clears the 60 m floor by 0.3 m. The
                    # two are now separate fields, and the gap is read from where it is measured.
                    "facade_gap_m": sel["selected"].get("true_gap_m"),
                    "centroid_separation_m": sel["selected"].get("separation_m")}
            except Exception:
                committed = None
        pf = "plume_field_%s_longest.json" % k
        # EVERY per-site artefact, named here so the browser never has to guess a filename.
        # `demo_path` keeps ashburn unsuffixed (the audited chain reads those names), so the
        # convention is invisible to the page: it just loads whatever this manifest tells it to.
        # Only files that EXIST are listed -- a name for a file that is not there is how the page
        # would report "not loaded" for a site the picker had already offered.
        artefacts = {}
        for nm in ("trace.json", "backtest.json", "rolling.json", "money.json",
                   "explanations.json", "ticker.json", "scenarios.json", "report.pdf"):
            fp = demo_path(nm, k)
            if os.path.exists(fp):
                # strip ANY extension, not just .json -- "report.pdf" was becoming the key
                # "report.pdf", so the page looked up `artefacts["report"]` and got nothing
                artefacts[os.path.splitext(nm)[0]] = os.path.basename(fp)
        # 🔴 SCOPE IS A SEPARATE GATE FROM DATA, AND THE MANIFEST CAUGHT ME CONFLATING THEM.
        # `readiness().offerable` asks only whether the DATA exists: own geometry, a
        # data-centre-to-data-centre pair, a >= 95 % station record. Phoenix and Santa Clara pass all
        # three -- and both were REFUSED by the aerial-imagery scope gate, one rooftop-cooled and one
        # not yet built. The first version of this manifest marked them offerable, so the picker would
        # have offered exactly the two sites this project had just finished explaining are unfit.
        # A site is offerable only if the pair it COMMITTED carries an in_scope verdict.
        cpair = ([committed["source_osm_id"], committed["receptor_osm_id"]]
                 if committed else None)
        cver = next((v for v in verdicts if v["pair"] == cpair), None) if cpair else None
        scope_ok = bool(cver and cver["in_scope"])
        sites.append({
            "key": k, "label": m["label"], "station": "K" + m["station"], "tz": m["tz"],
            "bbox": list(m["bbox"]),
            "data_ready": r["offerable"],
            "scope_verdict": (cver or {}).get("verdict") or "NOT ASSESSED",
            "scope_ok": scope_ok,
            "offerable": bool(r["offerable"] and scope_ok
                              and os.path.exists(os.path.join(demo, pf))),
            "not_offerable_because": (
                None if (r["offerable"] and scope_ok and os.path.exists(os.path.join(demo, pf)))
                else ("committed pair is %s -- refused by the imagery scope gate"
                      % (cver or {}).get("verdict") if cver and not cver["in_scope"]
                      else "no in-scope architecture verdict for the committed pair"
                      if not scope_ok else "no solved plume field exported")),
            "n_buildings": r.get("n_buildings"), "n_tagged_dc": r.get("n_tagged_dc"),
            "n_dc_to_dc_pairs": r.get("n_dc_to_dc_pairs"),
            "weather_hours": r.get("n_hours"), "weather_coverage": r.get("coverage_frac"),
            "fortyguard_field": m["fortyguard_field"],
            "climate_note": m["climate_note"], "basis": m["basis"],
            "committed": committed,
            "plume_field_file": pf if os.path.exists(os.path.join(demo, pf)) else None,
            # The per-site artefact filenames. Without these the page could only ever load
            # `trace.json`, which is why picking a site changed one panel out of thirteen.
            "artefacts": artefacts,
            "has_own_fortyguard_field": bool(m.get("fortyguard_field")),
            "verdicts": [{"pair": v["pair"], "name": v["name"], "verdict": v["verdict"],
                          "in_scope": v["in_scope"],
                          "consequence": v.get("consequence", "")[:240]} for v in verdicts],
        })
    obj = {"generated_by": "INTAKE-ARBITER/src/metros.py --manifest", "api_calls_made": 0,
           "offerable_rule": ("own geometry AND a data-centre-to-data-centre pair AND a >= %.0f %% "
                              "own five-year station record. Without its own record a site has no "
                              "conformal bound of its own, and borrowing another site's would be a "
                              "lie about the only number this project promises."
                              % (100 * MIN_WEATHER_COVERAGE)),
           "screening_note": ("Five sites were screened from aerial imagery. Two were REFUSED -- one "
                              "rooftop-cooled, one not yet built -- and a third was refused by the "
                              "solver itself because the intake disc would have averaged the exhaust "
                              "it is meant to measure. The refusals are exported deliberately."),
           "sites": sites}
    p = os.path.join(demo, "sites.json")
    json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("   wrote %s -- %d sites, %d offerable"
          % (p, len(sites), sum(1 for s in sites if s["offerable"])))
    return 0


def main():
    if "--manifest" in sys.argv:
        return export_manifest()
    print("=" * 78)
    print("METRO REGISTRY -- %d entries. Zero API calls, zero credentials." % len(METROS))
    print("=" * 78)
    print("\n   %-12s %-26s %-7s %-20s %-9s %-8s %s"
          % ("key", "label", "station", "timezone", "geometry", "weather", "offerable"))
    for k in sorted(METROS):
        r = readiness(k)
        g = ("%s bldg / %s pairs" % (r.get("n_buildings", "?"), r.get("n_pairs", "?"))
             if r["geometry"] else "MISSING")
        w = ("%s h" % format(r.get("n_hours", 0), ",")) if r["weather"] else "MISSING"
        print("   %-12s %-26s %-7s %-20s %-9s %-8s %s"
              % (k, r["label"][:26], r["station"], r["tz"], g, w,
                 "YES" if r["offerable"] else "no"))
    print("\n   A metro is OFFERABLE only with BOTH its own geometry and its own 5-year station")
    print("   record. The conformal margins are quantiles of that station's residuals, so a site")
    print("   without one has no bound of its own -- and borrowing another site's would be a lie")
    print("   about the only number this project promises.")
    print("\n   FortyGuard field, per metro:")
    for k in sorted(METROS):
        print("      %-12s %s" % (k, METROS[k]["fortyguard_field"] or "NOT PURCHASED (4,220 each)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
