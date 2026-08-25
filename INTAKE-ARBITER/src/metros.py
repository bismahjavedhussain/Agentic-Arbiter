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
import shutil
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
        # The four measured forecast/outcome DAY-PAIRS live here and nowhere else. Every other site
        # reads 0, which is what makes "this site's coverage is borrowed" a fact in the registry
        # rather than a sentence in a document.
        "fortyguard_field_fixture": None,          # the pairs are exported instead, one per leg
        "fortyguard_day_pairs": 4,
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
        "fortyguard_field_fixture": None,
        "fortyguard_day_pairs": 0,
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
        # 🔴 THIS SAID `None` UNTIL 2026-08-21, AND CHICAGO'S FIELD WAS ON DISK THE WHOLE TIME.
        # One past-window heatmap was purchased for this site on 2026-08-19 -- 17,797 tiles, 4,220
        # credits, saved as `testing/results/fixtures/chicago_field_20260818_1400.json`. Because this
        # key was None, `export_manifest()` published `has_own_fortyguard_field: false`, the demo's
        # own note told the reader *"this site has no FortyGuard field of its own"*, and the panel
        # showed ASHBURN'S field instead of the one we had paid for. A field we bought, labelled as
        # not existing, standing next to a Virginia heatmap on a Chicago page.
        # ⚠ IT IS ONE PAST WINDOW, NOT A DAY-PAIR. It buys the spatial statistics and the screen-zero
        # visual; it does NOT buy a level offset or a coverage record, because those need a forecast
        # leg AND its elapsed outcome (2 calls) -- see `fortyguard_day_pairs` below, which is the key
        # the borrowed-calibration machinery actually reads.
        "fortyguard_field": "purchased -- 1 past-window heatmap call, 17,797 tiles (2026-08-18 "
                            "14:00 site-local), explicit timezone",
        "fortyguard_field_fixture": "chicago_field_20260818_1400",
        "fortyguard_day_pairs": 0,
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
        "fortyguard_field_fixture": None,
        "fortyguard_day_pairs": 0,
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
        "fortyguard_field_fixture": None,
        "fortyguard_day_pairs": 0,
        "climate_note": "mild marine: a narrow annual range, so the margin should be tight and the "
                        "hours plentiful. TO BE MEASURED",
    },
}

DEFAULT_METRO = "ashburn"

# Below this share of the 43,824 hours in five years (2024 is a leap year -- §10 #167), a
# station record is too gappy to fit 24
# hour-of-day conformal quantiles on. Measured consequence, not a preference: see readiness().
MIN_WEATHER_COVERAGE = 0.95

# WHAT "THE CHAIN HAS FINISHED" MEANS, in one place, because it was answered in two and they
# disagreed. `build_national_batch.state_of()` tested `trace.json` alone -- the FIRST artefact
# the chain writes -- so a facility interrupted after step 1 was recorded as built FOREVER,
# skipped on every resume, counted complete by `status`, and still offered by the manifest with
# four of its panels missing. Measured: 1 of the first 7 national facilities (WI_way_1510420026)
# was orphaned exactly that way. These six are the set `audit.py` requires of any offerable
# site; the audit states its own copy deliberately, so a check asserts the two agree rather
# than the audit importing the code it audits.
REQUIRED_ARTEFACTS = ("trace", "backtest", "rolling", "money", "ticker", "explanations")


# ---------------------------------------------------------------------------------------------
# THE NATIONAL FACILITY REGISTRY, read on demand
# ---------------------------------------------------------------------------------------------
# `METROS` above is five HAND-BUILT entries and stays exactly that: each one carries a researched
# bbox, a station chosen on measured record quality, and prose provenance no generator could write.
# Those five are authoritative and nothing below changes them.
#
# What the national build produces is different in kind: 639 facilities, each a connected component
# of tagged buildings inside the solver's validated range, with a measured centroid, a measured
# timezone and a reverse-geocoded state. Typing those into a literal dict would be absurd, and
# generating them into one would put a 639-entry machine-written blob in the middle of a file whose
# value is its hand-written reasoning. So they are LOADED, and `metro()` answers from whichever
# source holds the key.
#
# 🔴 THE SAFETY PROPERTY THAT MUST SURVIVE: `metro_key()` raising on an unknown key is not
# pedantry. `geom_path`/`demo_path` fall back to the UNSUFFIXED Ashburn filenames for the default
# metro, so a typo that resolved to "some metro" would silently load Ashburn's geometry, Ashburn's
# weather and Ashburn's bound under another site's name -- gotcha #98's family, from a spelling
# mistake. So the validation still happens; it now consults two registries instead of one.
_NATIONAL_CACHE = [None]
_ASSIGN_CACHE = [None]
_FIELD_CACHE = [None]


def field_assignments():
    """facility key -> the purchased FortyGuard AOI field that COVERS it, or {} if S7b has not run.

    A SIDE-CAR, FOR THE SAME REASON `station_assignments()` IS ONE, and the reason is money.
    `build_national_registry.py` is pure computation over geometry and is re-run whenever a
    classification rule changes -- it writes `fortyguard_field: null` for every facility by design.
    A field assignment represents a real 4,220-credit purchase, so it lives in its own file where a
    geometry rebuild cannot destroy it. `wire_national_fields.py` writes it.

    WHY AN ASSIGNMENT AND NOT A PURCHASE PER SITE: a heatmap AOI is 8x8 km and the tagged estate is
    clustered, so one field genuinely covers many facilities -- AOI rank #1 covers 111 of them. The
    assignment records WHICH field a facility is reading and how far its centre sits from that
    field's centre, so the page can state a shared field as shared rather than implying each site
    was bought its own.
    """
    if _FIELD_CACHE[0] is None:
        p = os.path.join(GEOM, "national_field_assignments.json")
        try:
            _FIELD_CACHE[0] = json.load(open(p, encoding="utf-8"))["assignments"]
        except (IOError, OSError, ValueError, KeyError):
            _FIELD_CACHE[0] = {}
    return _FIELD_CACHE[0]


def station_assignments():
    """facility key -> its MEASURED station assignment, or {} if S5 has not run.

    Deliberately a separate file from the registry (`data/weather/station_assignments.json`), not a
    field inside it: `build_national_registry.py` is pure computation over geometry and is re-run
    whenever a classification rule changes, and an assignment that cost 60 real requests to measure
    must not be destroyed by a geometry rebuild.
    """
    if _ASSIGN_CACHE[0] is None:
        p = os.path.join(WEATHER, "station_assignments.json")
        try:
            _ASSIGN_CACHE[0] = json.load(open(p, encoding="utf-8"))["assignments"]
        except (IOError, OSError, ValueError, KeyError):
            _ASSIGN_CACHE[0] = {}
    return _ASSIGN_CACHE[0]


def national_registry():
    """The facility registry, or {} if it has not been built. Cached: `metro()` is called per
    import of `agent.py` and this file is ~1 MB."""
    if _NATIONAL_CACHE[0] is None:
        p = os.path.join(GEOM, "national_registry.json")
        try:
            _NATIONAL_CACHE[0] = json.load(open(p, encoding="utf-8"))["facilities"]
        except (IOError, OSError, ValueError, KeyError):
            _NATIONAL_CACHE[0] = {}
    return _NATIONAL_CACHE[0]


def national_entry(k):
    """A METROS-shaped record for one national facility, built from its MEASURED fields.

    Every value here is either read from the registry or explicitly `None`. Nothing is invented to
    fill a gap: `station` is None until S5 assigns one on measured record completeness, and
    `weather_file()` refuses rather than composing a filename around it -- because a name that
    asserts a station the pipeline never fetched is exactly the drift `weather_file`'s own docstring
    was written about.
    """
    f = national_registry()[k]
    names = f.get("names") or []
    label = "%s, %s" % (names[0], f.get("state") or "US") if names else \
            "%s facility %s" % (f.get("state") or "US", k)
    # The bbox brackets this facility's OWN buildings, with a margin big enough for the solver's
    # validated range so a later geometry fetch cannot clip a neighbour it needs to see.
    lats = [c[0] for c in [f["centre"]]]
    lons = [c[1] for c in [f["centre"]]]
    pad = 0.012                      # ~1.3 km: covers the 600 m range plus the largest campus seen
    # THE STATION, IF S5 HAS MEASURED ONE. Absent otherwise -- never the nearest by default, because
    # nearest is not the rule: `assign_station.py` walks candidates by distance and takes the first
    # whose OWN five-year record clears the coverage floor, exactly as KFFZ at 16.7 km was taken over
    # KIWA at 2.7 km. A facility with no measured assignment has `station: None`, and
    # `weather_file()` refuses rather than composing a filename around it.
    asn = station_assignments().get(k) or {}
    fga = field_assignments().get(k) or {}
    return {
        "state": f.get("state"),
        "label": label,
        "bbox": (min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad),
        "station": asn.get("station"),         # S5. Measured, or absent -- never guessed.
        "station_assignment": asn or None,
        "tz": f.get("tz"),
        # A DERIVED NAME, not None. There is no pairwise candidate search for a national facility,
        # so this file will not exist -- but `candidates_path()` is a PATH CONSTRUCTOR, and several
        # modules build that path at IMPORT time (`fetch_geometry.py:45` is one). Returning None
        # made `os.path.join` raise `TypeError` before any of those modules could even be imported
        # for a facility, which is the same import-time landmine `site_centre()` was.
        # Whether the file EXISTS is a separate question, and `readiness()` already answers it with
        # `os.path.exists` -- so a path to an absent file is exactly what that check expects to find.
        "candidates_file": "%s_candidates.json" % k,
        "basis": "national OSM discovery: %d tagged building(s), %s. Classified %s."
                 % (f.get("n_buildings", 0), ", ".join(f.get("members", [])[:3]), f.get("kind")),
        # 🔴 THESE WERE HARD `None`, WHICH IS WHY 40 PAID FIELDS REACHED NOTHING.
        # `build_national_registry.py:53` says of its own null: "ABSENT, explicitly, so a later
        # stage fills them in" -- and that later stage did not exist, so every national facility
        # reported `has_own_fortyguard_field: false` no matter what had been bought for it. Exactly
        # the Chicago defect recorded further down, where a purchased field sat unused while the
        # page told the reader the site had none, now at national scale.
        # Read from the side-car, exactly as `station` is, and absent when nothing covers this site.
        "fortyguard_field": (fga.get("provenance") if fga else None),
        "fortyguard_field_fixture": (fga.get("aoi_key") if fga else None),
        "fortyguard_field_assignment": fga or None,
        # STILL ZERO, AND NOT THE SAME QUESTION. A field is one elapsed window: it buys the spatial
        # picture and the tile statistics. A day-PAIR is a forecast leg plus its own outcome, which
        # is what a conformal residual is measured from -- and no amount of field buying produces
        # one, because the outcome has to elapse. Keeping these separate is what stops a site with a
        # field from claiming a calibration it does not have.
        "fortyguard_day_pairs": 0,
        "climate_note": None,
        # National-only fields, so a caller can tell the two registries apart rather than guessing
        # from the shape of the key.
        "national": True,
        "kind": f.get("kind"),
        "facility": f,
    }


def metro_key():
    """Which metro the pipeline is operating on. Defaults to ashburn so every existing path,
    filename and audited number is unchanged unless a caller explicitly asks otherwise."""
    # 🔴 UNSET AND EMPTY ARE DIFFERENT THINGS, AND CONFLATING THEM OVERWRITES THE REFERENCE SITE.
    # This was `(os.environ.get("METRO") or DEFAULT_METRO)`, so METRO="" fell through to ashburn --
    # while METRO=" " raised, because a space is truthy and strips to empty. Harmless at three
    # sites, dangerous at 639: a driver looping `METRO=$KEY python agent.py` with one unset variable
    # would silently rebuild ASHBURN, and because `demo_path` gives the default metro the UNSUFFIXED
    # filenames, it would overwrite exactly the artefacts the 77 published numbers are read from.
    # So: absent means "nobody asked", and defaults. Present-but-empty means somebody tried to pass
    # a value and it was empty, which is a bug in the caller and is reported as one.
    raw = os.environ.get("METRO")
    if raw is None:
        return DEFAULT_METRO
    k = raw.strip()
    if not k:
        raise SystemExit("METRO is set but empty. That is a caller bug, not a request for the "
                         "default: an empty value here would silently rebuild %r and overwrite the "
                         "unsuffixed reference artefacts. Unset METRO entirely to mean %r."
                         % (DEFAULT_METRO, DEFAULT_METRO))
    # NOT lowercased for national keys: facility keys are `TX_way_102129663`, whose state prefix is
    # upper case and whose OSM id is a real identifier. The five hand-built keys stay
    # case-insensitive, because every existing caller and scheduled task types them in lower case.
    if k.lower() in METROS:
        return k.lower()
    if k in national_registry():
        return k
    raise SystemExit("unknown METRO=%r. %d hand-built: %s. %d national facilities in "
                     "data/geometry/national_registry.json%s"
                     % (k, len(METROS), ", ".join(sorted(METROS)), len(national_registry()),
                        " -- run build_national_registry.py" if not national_registry() else ""))


def metro(k=None):
    kk = k or metro_key()
    if kk in METROS:
        return METROS[kk]
    if kk in national_registry():
        return national_entry(kk)
    raise SystemExit("unknown metro %r" % kk)


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
    # NO STATION, NO FILENAME. A national facility has `station: None` until S5 assigns one on
    # measured five-year completeness, and composing "knone_hourly_2021_2025.json" around that
    # would produce a path that looks like a record and is not one -- the same class of drift this
    # docstring already describes, one step earlier. Refuse loudly instead.
    if not m.get("station"):
        raise SystemExit("%r has no weather station assigned yet, so it has no record filename. "
                         "A station is chosen on measured 5-year completeness (>= %.0f %%), not on "
                         "proximity -- see readiness(). Nothing here will guess one."
                         % (k or metro_key(), 100 * MIN_WEATHER_COVERAGE))
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


def imagery_dir(k=None):
    """The screening-imagery directory for a metro.

    Ashburn's frames sit at the ROOT of `data/imagery/screen` because it was screened before the
    tree was metro-aware; every metro screened afterwards has a subdirectory. Same asymmetry as
    `geom_path` and `demo_path`, and for the same reason -- the audited chain reads the unsuffixed
    Ashburn names.

    (A helper of this name was written and deleted on 2026-08-19 because nothing referenced it and
    `audit.check_dead_code` correctly failed the build. It has a caller now: `committed_imagery`.)
    """
    kk = k or metro_key()
    base = os.path.join(ROOT, "data", "imagery", "screen")
    return base if kk == DEFAULT_METRO else os.path.join(base, kk)


def committed_imagery(k, committed):
    """The aerial frame for THIS site's committed pair, copied into demo/ and georeferenced.

    WHY THIS EXISTS
    ---------------
    The demo's aerial panel carried three hardcoded Ashburn constants -- the image bbox and the two
    OSM building centres -- so selecting Chicago or Dulles redrew ASHBURN'S imagery with ASHBURN'S
    georeferencing, and the overlay for the other two sites was meaningless. The values were
    verified to have been copied by hand out of Ashburn's own `screen_manifest.json`, so reading
    them per-site from that manifest is provably identical for Ashburn and correct for the others.

    WHAT IT RETURNS, AND THE BBOX ORDER TRAP
    ----------------------------------------
    `imagery.bbox` is **[lon_min, lat_min, lon_max, lat_max]** -- the ArcGIS export order, kept
    verbatim from the screening manifest so it is never re-ordered in flight. NOTE that a site's
    OTHER bbox field, `sites[].bbox`, is the metro CLUSTER extent in **[lat_min, lon_min, lat_max,
    lon_max]**. Two bboxes, two orders, one letter of difference in the name; the field is called
    `imagery.bbox` and documented here precisely because that is a trap.

    `sources` lists only frames that EXIST. Dulles has no USGS frame, and that absence is
    load-bearing: PLAN section 8o records that its imagery verdict fails the two-source rule, so the
    picker must not offer a USGS option that would 404 and imply a cross-check nobody made.
    """
    if not committed:
        return None
    d = imagery_dir(k)
    mp = os.path.join(d, "screen_manifest.json")
    if not os.path.exists(mp):
        return None
    try:
        man = json.load(open(mp, encoding="utf-8"))
    except (ValueError, OSError):
        return None

    want = (committed.get("source_osm_id"), committed.get("receptor_osm_id"))
    cand = next((c for c in man.get("candidates", [])
                 if (c.get("source_osm_id"), c.get("receptor_osm_id")) == want), None)
    if not cand or not cand.get("file"):
        # The pair was committed but never screened as a FRAME -- possible, because the refusal
        # ranking and the imagery screen are separate steps. Report the absence rather than
        # falling back to another site's frame, which is the bug this function exists to kill.
        return {"bbox": None, "sources": {}, "note":
                "no screening frame matches the committed pair %s -> %s" % want}

    out = {"candidate_file": cand["file"],
           "bbox": cand.get("bbox"),
           "bbox_order": "lon_min, lat_min, lon_max, lat_max (ArcGIS export order)",
           "source_latlon": cand.get("source_latlon"),
           "receptor_latlon": cand.get("receptor_latlon"),
           "resolution_note": man.get("caveat"),
           "sources": {}}

    # ESRI is the frame itself; USGS is the same pair re-exported from The National Map and is
    # prefixed `usgs_`. Copy each into demo/ under a stable per-site name so the page loads a
    # filename the manifest gave it rather than one it constructed.
    for label, src_name in (("esri", cand["file"]), ("usgs", "usgs_" + cand["file"])):
        src = os.path.join(d, src_name)
        if not os.path.exists(src):
            continue
        # THE DESTINATION KEEPS THE SOURCE'S EXTENSION. This was a hardcoded `.png`, so a national
        # facility's JPEG frame would have been copied to a file NAMED `.png` while containing JPEG
        # bytes. Browsers sniff content and would have rendered it, which is exactly what makes it
        # dangerous: a filename asserting a format the file is not, discovered by nobody, until
        # something downstream trusted the name. The five hand-built metros are PNG and stay PNG --
        # this only follows what is actually on disk.
        ext = os.path.splitext(src_name)[1].lower() or ".png"
        dst_name = (("site_aerial" if label == "esri" else "site_aerial_usgs") + ext)
        dst = demo_path(dst_name, k)
        # Copy only when the bytes differ, so a rebuild does not rewrite 2.5 MB per site per run
        # and git does not see a spurious change. `.gitattributes` marks *.png binary, so a
        # rewritten-but-identical PNG would still be a no-op diff -- this is about build time.
        need = True
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            need = open(dst, "rb").read() != open(src, "rb").read()
        if need:
            shutil.copyfile(src, dst)
        out["sources"][label] = os.path.basename(dst)

    out["two_source_cross_check"] = len(out["sources"]) >= 2
    return out


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
    kk = k or metro_key()

    # 🔴 A FACILITY WITH NO PAIR HAS A CENTRE TOO, AND THIS USED TO CRASH ON IT.
    # `agent.py` calls this at MODULE level (`SITE_CENTRE = M.site_centre()`), and
    # `backtest`/`rolling`/`money`/`explain`/`ticker`/`plume_uncertainty` all import `agent` -- so a
    # KeyError here meant no module in the chain could even be IMPORTED for a site without a
    # committed source+receptor pair. That single line is why the standalone path was decided in
    # prose and implemented nowhere: 383 of 639 national facilities have no pair by construction,
    # and the pipeline could not load for any of them.
    # A standalone facility's centre is the mean of its OWN buildings' measured coordinates, which
    # the registry already carries. This is not a fallback to something approximate -- it is the
    # same quantity, computed the same way, from the same OSM positions.
    nat = national_registry().get(kk)
    if nat:
        return (nat["centre"][0], nat["centre"][1])

    p = geom_path("selected_site.json", kk)
    sel = json.load(open(p, encoding="utf-8"))
    a = sel.get("source_building", {}).get("centre_latlon")
    b = sel.get("receptor_building", {}).get("centre_latlon")
    if not a or not b:
        raise KeyError("%s has no centre_latlon for its committed pair" % p)
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def national_readiness(k, m):
    """Readiness for a NATIONAL facility, and the amendment to the offerable rule.

    🔴 THE RULE THIS AMENDS, AND WHY THE AMENDMENT IS NOT A LOOSENING.
    `sites.json` has carried this sentence since the multi-site engine was built:

        "own geometry AND a data-centre-to-data-centre PAIR AND a >= 95 % own five-year station
         record. Without its own record a site has no conformal bound of its own, and borrowing
         another site's would be a lie about the only number this project promises."

    Two of those three clauses are load-bearing for every site and are enforced here unchanged. The
    PAIR clause is not: it exists so the plume solver is modelling two data centres rather than a
    warehouse, and it is the admission test for the PHYSICS. A standalone facility has no plume to
    model -- the rise is not computed, it is not applicable -- so requiring a pair of it would
    refuse 359 real facilities for failing a test of a stage they never run.

    What replaces it is stricter, not looser: the facility must be classified `standalone` by
    `build_national_registry.py` on MEASURED geometry, and its standalone artefacts must exist on
    disk. It cannot be offered by asserting it has no neighbour; it is offered because the union-find
    over every tagged building's own coordinate found none inside the solver's validated range, and
    because `build_standalone_site.py` then wrote its zero rise table and its own wind statistics.

    ⚠ ONLY `standalone` IS OFFERABLE TODAY, and the reason is capability, not policy: a
    `paired_clear` facility needs the existing pairwise funnel (select_site -> refusal_rank ->
    build_site x2 -> direction_sweep -> export_plume_fields) run on it, which has not been built at
    national scale. Recorded as `not_offerable_because` rather than left to look like a refusal.
    """
    reg = national_registry().get(k) or {}
    kind = reg.get("kind")
    wx = weather_path(k) if m.get("station") else None
    out = {"key": k, "label": m["label"],
           "station": ("K" + m["station"]) if m.get("station") else None,
           "tz": m["tz"], "national": True, "kind": kind,
           "geometry": os.path.exists(geom_path("selected_site.json", k)),
           "weather": bool(wx and os.path.exists(wx)),
           "fortyguard_field": m.get("fortyguard_field"),
           "n_buildings": reg.get("n_building_footprints"),
           "n_tagged_dc": reg.get("n_building_footprints"),
           # ZERO, AND THAT IS THE POINT rather than a missing measurement. Published so the
           # manifest cannot silently look like a site whose pair search simply failed.
           "n_dc_to_dc_pairs": 0 if kind == "standalone" else None,
           "longest_facade_m": reg.get("longest_facade_m"),
           "nearest_other_tagged_dc_m": (reg.get("plume") or {}).get("nearest_other_tagged_dc_m")}
    if out["weather"]:
        d = json.load(open(wx, encoding="utf-8"))
        wm = d.get("meta") or {}
        out["n_hours"] = len(d.get("hours") or {})
        out["coverage_frac"] = wm.get("coverage_frac")
        out["weather_ok"] = bool(out["coverage_frac"] is not None
                                 and out["coverage_frac"] >= MIN_WEATHER_COVERAGE)
    # 🔴 `built` USED TO TEST `trace.json` ALONE, AND THE CHAIN HAS EIGHT STEPS.
    # `trace.json` is the FIRST artefact the chain writes, so a facility whose chain died at step 6
    # of 8 still satisfied it -- and `offerable` is `data_ready and built`, so the manifest went on
    # OFFERING a site whose backtest, money, ticker or explanations had never been written. That is
    # not hypothetical: CO_way_1273968634, IA_way_191655977 and OH_way_1281982556 were each listed
    # as offerable with four artefacts missing, and audit.py failed on all three until they were
    # rebuilt by hand. The same comment at the top of this file records the identical trap in
    # `build_national_batch.state_of()` -- "tested `trace.json` alone, the FIRST artefact".
    #
    # THE NAMES HERE MATCH audit.py's OWN REQUIRED LIST exactly, which is what makes the manifest
    # and the checker agree by construction rather than by coincidence. `scenarios.json` and
    # `report.pdf` are deliberately NOT required: the manifest names them when they exist, but
    # neither is read by the six-artefact contract the audit asserts.
    #
    # WHY THIS IS ENOUGH, AND NEEDS NO CRASH CLEANUP: the chain is ORDERED, so a failure always
    # leaves at least one LATER artefact absent -- even when the artefact it died inside was left
    # half-written on disk. Existence of all six is therefore a sufficient test for "this chain ran
    # to completion", and a facility that fails overnight simply stops being offerable, with
    # `not_offerable_because` saying so, instead of turning the whole build red until morning.
    REQUIRED_ARTEFACTS = ("trace.json", "backtest.json", "rolling.json", "money.json",
                          "explanations.json", "ticker.json")
    missing_art = [nm for nm in REQUIRED_ARTEFACTS if not os.path.exists(demo_path(nm, k))]
    built = not missing_art
    out["artefacts_built"] = built
    # 🔴 TWO DIFFERENT QUESTIONS, AND CONFLATING THEM WAS A CIRCULAR DEPENDENCY.
    #   data_ready -- may this facility BE built? geometry + its own weather + a runnable kind.
    #   offerable  -- may the interface OFFER it? data_ready AND its artefacts actually exist.
    # One flag answered both, so `offerable` required `trace.json` to exist while `build_sites.py`
    # gated on `offerable` to decide what it was allowed to build. Nothing could ever be built:
    # measured on the first live batch, three facilities in a row reported
    # "not offerable: <key>. Offerable: ashburn, chicago, dulles, IA_way_..." AFTER their weather,
    # imagery and geometry had all completed successfully. The single facility that did work had
    # been built by hand before the manifest ever saw it -- which is exactly how a circular gate
    # hides: the one case that appears to prove it works is the case that bypassed it.
    # 🔴 THIS READ `kind == "standalone"`, AND IT WAS TRUE WHEN WRITTEN AND SILENTLY STOPPED BEING.
    # It encoded "the pairwise plume funnel has not been run at national scale yet" -- correct until
    # `build_paired_site.py` existed. After that it became a gate refusing the exact facilities the
    # new driver had just made buildable: a full batch reported `chain_failed / not offerable` in
    # 0.2 s per facility AFTER their geometry had solved successfully, and the reason string still
    # said the funnel had not been run. A capability check spelled as an equality against one
    # literal cannot notice that a second case now works.
    #
    # So it asks the mechanical question instead: does the pairwise geometry this kind needs EXIST?
    # A paired facility is ready only once its two bank placements and its 72-bearing table are on
    # disk, which is precisely what `build_paired_site.py` writes and what the chain's first step
    # loads. `standalone` keeps its old meaning exactly -- a zero rise table is correct for it and
    # `build_standalone_site.py` never writes a `facing` placement -- so the three shipped metros
    # and every already-built national site are unaffected.
    PAIRED_READY_ARTEFACTS = ("solver_site_longest.json", "solver_site_facing.json",
                              "direction_table.json")
    if kind == "standalone":
        kind_ready = True
    elif kind in ("paired_clear", "paired_advisory"):
        kind_ready = all(os.path.exists(geom_path(nm, k)) for nm in PAIRED_READY_ARTEFACTS)
    else:
        kind_ready = False                      # boundary_only and anything unrecognised
    out["kind_ready"] = kind_ready
    out["data_ready"] = bool(out["geometry"] and out["weather"] and out.get("weather_ok")
                             and kind_ready)
    out["offerable"] = bool(out["data_ready"] and built)
    if not out["offerable"]:
        out["not_offerable_because"] = (
            "no weather station assigned yet (S5)" if not out["weather"] else
            "its five-year record is %.4f, below the %.2f floor"
            % (out.get("coverage_frac") or 0.0, MIN_WEATHER_COVERAGE) if not out.get("weather_ok")
            else "standalone geometry artefacts not written -- run build_standalone_site.py"
            if not out["geometry"] else
            # NAME WHAT IS ABSENT. "artefacts not built" sent a reader to re-run the whole chain to
            # find out which step had not finished; the list says it outright, which matters most
            # after an unattended overnight run nobody watched.
            "%d of %d chain artefacts missing (%s) -- re-run the build_sites chain"
            % (len(missing_art), len(REQUIRED_ARTEFACTS),
               ", ".join(os.path.splitext(m)[0] for m in missing_art)) if not built else
            # NAME THE MISSING GEOMETRY, not the kind. The old text said the pairwise funnel "has
            # not been run at national scale yet" -- a statement about the PROJECT that stayed on
            # disk after `build_paired_site.py` made it false, and so described working facilities
            # as unsupported ones.
            "kind is %r and its pairwise geometry is incomplete (%s missing) -- run "
            "build_paired_site.py %s. NOT a refusal: nothing about it has been rejected"
            % (kind, ", ".join(os.path.splitext(nm)[0] for nm in PAIRED_READY_ARTEFACTS
                               if not os.path.exists(geom_path(nm, k))) or "none", k)
            if kind in ("paired_clear", "paired_advisory") else
            "kind is %r: only standalone and paired facilities can be built. A boundary-only "
            "facility has no building footprint to place a plant on" % kind)
    return out


def readiness(k):
    """What exists on disk for this metro. Nothing here is inferred -- it is all stat() calls."""
    m = metro(k)                     # was METROS[k]: a KeyError for every national facility
    if m.get("national"):
        return national_readiness(k, m)
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
    # THE FIVE HAND-BUILT METROS, THEN EVERY NATIONAL FACILITY THAT HAS ACTUALLY BEEN BUILT.
    # `sorted(METROS)` alone meant a national facility could never reach `sites.json` no matter how
    # complete it was -- and `sites.json` is what the picker, `build_sites.py` and the map's click
    # handler all read, so that one loop was the last gate between a fully-built facility and the
    # interface. Gated on `trace.json` EXISTING rather than on the registry, so this lists the
    # facilities that have artefacts and not the 639 that could have them: a picker offering a site
    # with nothing behind it is the defect §6.13 exists for.
    # INCLUDED ONCE ITS GEOMETRY IS WRITTEN, not once it is built. Gating this on `trace.json` was
    # the other half of the circular dependency: a facility with weather, imagery and geometry still
    # had NO ROW in sites.json, so `build_sites.py` -- which reads this file -- could not see it and
    # therefore could not build it, so it never got a trace, so it never got a row.
    # `selected_site.json` is the right marker and it is one stat() per facility: it exists exactly
    # when `build_standalone_site.py` has run, which is the point at which a facility becomes
    # buildable. Facilities without it are simply not yet candidates and are correctly absent.
    built_national = [k for k in sorted(national_registry())
                      if os.path.exists(geom_path("selected_site.json", k))
                      or os.path.exists(demo_path("trace.json", k))]
    for k in sorted(METROS) + built_national:
        r = readiness(k)
        m = metro(k)                 # was METROS[k]
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

        # ---- THE NATIONAL TIER, AND THE TWO GATES IT CANNOT MEET -----------------------------
        # 🔴 THE IMAGERY GATE IS NOT WEAKENED HERE. It has actually refused two whole metros
        # (Santa Clara rooftop-cooled, Phoenix not built) and it answers the question that decides
        # whether this MODEL APPLIES AT ALL: is the cooling plant at ground level, where
        # FortyGuard's 2 m field is? If it is on the roof, none of this describes the building.
        # So an unscreened facility is given a THIRD state -- `not_screened` -- and never
        # `in_scope`. NATIONAL-BUILD-PLAN section 7.4: "If imagery is unavailable for a site, that
        # site is NOT SCREENED, not 'screened, assumed fine'." A screened refusal and an
        # unscreened unknown are different facts and the manifest keeps them different.
        #
        # THE PLUME FIELD is required of a paired site because the panel that renders it is real.
        # A standalone facility has no plume to render, so requiring the file would refuse it for
        # not having an artefact of a stage it never runs -- the same category error as requiring
        # it to have a pair.
        national = bool(m.get("national"))
        has_plume_field = os.path.exists(os.path.join(demo, pf))
        if national:
            # THE VERDICT IS READ FROM THIS FACILITY'S OWN FRAME, not assumed. `NOT SCREENED` was
            # correct while no facility had imagery; now a facility may have a frame AND a recorded
            # judgement, and the manifest must distinguish three states rather than two:
            #   fully_screened          two sources + a human verdict on the exact pair (Ashburn)
            #   national_single_source  one frame + one recorded verdict, naming its assessor --
            #                           the DULLES standard, whose own record says the two-source
            #                           rule is not met
            #   national_unscreened     a frame with nobody's judgement, or no frame at all
            # A frame is not a screening, so the middle state is only reached once a verdict exists.
            sm = {}
            smp = os.path.join(imagery_dir(k), "screen_manifest.json")
            if os.path.exists(smp):
                try:
                    sm = json.load(open(smp, encoding="utf-8"))
                except ValueError:
                    sm = {}
            v = sm.get("architecture_verdict") or "NOT SCREENED"
            assessed = bool(sm.get("assessed_by")) and v not in ("NOT YET ASSESSED",)
            imagery_state = v if assessed else "NOT SCREENED"
            in_scope_nat = bool(sm.get("in_scope")) if assessed else False
            tier = "national_single_source" if assessed else "national_unscreened"
            # A RECORDED REFUSAL STILL REFUSES. If the frame was read and the plant is roof-mounted
            # or the site is not built, this facility is NOT offerable -- the same consequence
            # Santa Clara and Phoenix carry, reached by the same gate.
            offer = bool(r["offerable"] and (in_scope_nat or not assessed))
            if assessed and not in_scope_nat:
                offer = False
            why_not = (("committed building is %s -- refused by the imagery scope gate" % v)
                       if (assessed and not in_scope_nat)
                       else r.get("not_offerable_because"))
        else:
            imagery_state = (cver or {}).get("verdict") or "NOT ASSESSED"
            offer = bool(r["offerable"] and scope_ok and has_plume_field)
            tier = "fully_screened"
            why_not = (None if offer else
                       ("committed pair is %s -- refused by the imagery scope gate"
                        % (cver or {}).get("verdict") if cver and not cver["in_scope"]
                        else "no in-scope architecture verdict for the committed pair"
                        if not scope_ok else "no solved plume field exported"))
        sites.append({
            "key": k, "label": m["label"],
            "station": ("K" + m["station"]) if m.get("station") else None,
            "tz": m["tz"],
            "bbox": list(m["bbox"]),
            # `data_ready` MEANS "COULD BE BUILT", not "is offered". It read `r["offerable"]`, which
            # made the two synonyms and is half of the circular gate described in
            # `national_readiness`. `build_sites.py` reads THIS field to decide what it may build.
            "data_ready": r.get("data_ready", r["offerable"]),
            "scope_verdict": imagery_state,
            # `scope_ok` MUST AGREE WITH `scope_verdict`. For a national facility the verdict comes
            # from its own frame, not from `architecture_verdicts.json` (which is keyed by
            # hand-built metro and has no row for it) -- so reading the old gate here published
            # `scope_verdict: GRADE` beside `scope_ok: false`, two fields contradicting each other
            # about the same screening in the same record.
            "scope_ok": (in_scope_nat if national else scope_ok),
            # WHICH TIER, published per site, so a reader and a judge can tell a fully-screened
            # site from an unscreened one without reading the code. The three hand-built sites have
            # a human imagery verdict on their exact committed pair; a national facility does not,
            # and saying so is the whole point.
            "offer_tier": tier,
            "national": national,
            "site_kind": r.get("kind"),
            "plume_modelled": (not national) or False,
            # THE CAVEAT TRACKS THE ACTUAL STATE. Three sentences for three situations, so a reader
            # is never told a question is open when it has been answered, nor that it is settled
            # when one frame was read at 0.3-0.5 m by a model.
            "unscreened_caveat": (
                None if not national else
                ("This facility HAS been screened, from a single aerial frame: %s. Verdict %s, "
                 "assessed by %s. Evidence: %s. The two-source cross-check is NOT met -- the same "
                 "weaker standing this project records for Dulles -- and at this resolution "
                 "'ground-level plant' says where the equipment is, not what it is."
                 % ((sm.get("verdict_note") or "").split(".")[0] + ".",
                    imagery_state, sm.get("assessed_by"), sm.get("evidence"))) if assessed else
                ("This facility has NOT been screened from aerial imagery. The screening gate asks "
                 "whether the cooling plant sits at ground level, where FortyGuard's 2 m field "
                 "applies -- and it has refused two of the five hand-built metros, one for "
                 "roof-mounted plant and one for never having been built. Until this facility is "
                 "screened, that question is OPEN for it: if its plant is roof-mounted, this model "
                 "does not describe it. Every other number here is its own.")),
            "offerable": offer,
            "not_offerable_because": why_not,
            "n_buildings": r.get("n_buildings"), "n_tagged_dc": r.get("n_tagged_dc"),
            "n_dc_to_dc_pairs": r.get("n_dc_to_dc_pairs"),
            "weather_hours": r.get("n_hours"), "weather_coverage": r.get("coverage_frac"),
            "fortyguard_field": m["fortyguard_field"],
            "climate_note": m["climate_note"], "basis": m["basis"],
            "committed": committed,
            # THE AERIAL FRAME FOR *THIS* SITE. The demo carried Ashburn's image bbox and both of
            # Ashburn's OSM building centres as source-level constants, so every site drew
            # Ashburn's imagery under its own name. Exported per site now; the page reads it and
            # holds no coordinate of its own.
            "imagery": committed_imagery(k, committed),
            "plume_field_file": pf if os.path.exists(os.path.join(demo, pf)) else None,
            # The per-site artefact filenames. Without these the page could only ever load
            # `trace.json`, which is why picking a site changed one panel out of thirteen.
            "artefacts": artefacts,
            "has_own_fortyguard_field": bool(m.get("fortyguard_field")),
            # OWNING A FIELD AND OWNING A CALIBRATION ARE DIFFERENT THINGS, and collapsing them
            # into one boolean made the picker say "FortyGuard field purchased for this site" for
            # Chicago while its measured LEVEL OFFSET is still Ashburn's. Chicago has one past
            # window; a level offset needs a forecast leg AND its elapsed outcome. So the day-pair
            # count travels too, and the interface has three states instead of two.
            "fortyguard_day_pairs": m.get("fortyguard_day_pairs", 0),
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
