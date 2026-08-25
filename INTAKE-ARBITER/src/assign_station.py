# -*- coding: utf-8 -*-
"""S5 STEP 2 -- ASSIGN A WEATHER STATION TO A FACILITY, ON COMPLETENESS NOT PROXIMITY.

    python assign_station.py dryrun <FACILITY_KEY>     # the candidate ranking. FREE, no fetch.
    python assign_station.py run <FACILITY_KEY>        # measures candidates until one qualifies
    python assign_station.py list                      # what is already assigned. FREE.

ZERO FORTYGUARD CALLS. Iowa State Mesonet only, free and keyless.

--------------------------------------------------------------------------------------------
THE RULE, AS THIS PROJECT ALREADY STATES IT -- and it is not "nearest"
--------------------------------------------------------------------------------------------
`metros.py` records the decision that gives this module its shape. For the Phoenix cluster:

    KIWA sits 2.7 km away and looked ideal. Its five-year record came back 81.70 % complete,
    and the gap was STRUCTURAL rather than scattered -- 4,454 hours in 2021 and 5,747 in 2022
    against ~8,520 in 2023-25. KFFZ at 16.7 km came back 99.1 % and was taken instead.
    "Proximity lost to completeness."

So the assignment is: rank by distance, then walk that ranking measuring each candidate, and take
the FIRST one whose own five-year record clears `metros.MIN_WEATHER_COVERAGE` (0.95). Every
candidate tried is recorded with its distance and its measured coverage, so the choice is auditable
and the rejected ones are visible rather than implied.

🔴 WHY THE ORDER MATTERS AND CANNOT BE SHORTCUT. The conformal bound is the quantile of THIS SITE'S
OWN forecast residuals; `fetch_weather.py`'s docstring puts it plainly -- "KIAD's residual
distribution says nothing about Mesa's". A gappy record does not merely add noise, it removes whole
hours-of-day from the Mondrian groups the bound is fitted per. That is why the floor is a gate and
not a warning, and why a station cannot be accepted on metadata alone.

--------------------------------------------------------------------------------------------
WHAT MAKES 639 FACILITIES AFFORDABLE
--------------------------------------------------------------------------------------------
A five-year record is 60 month-chunk requests, and stations are SHARED: Ashburn and Dulles already
use one KIAD record deliberately. So the cost is per DISTINCT STATION, not per facility, and
`fetch_weather.build_station` returns immediately when the file exists. The second facility assigned
to KDSM costs zero requests.

Metadata prunes before any of that: a station whose `archive_begin` is after the window's start
cannot have a five-year record, and a non-null `archive_end` means it stopped reporting. Both come
from one request per state, already cached by `fetch_asos_stations.py`.

⚠ AND THE LIMIT OF THAT PRUNING, stated rather than assumed away: `archive_begin` is the FIRST
observation, not a guarantee of continuity. KIWA's archive starts in the 1990s and its record is
still 81.70 % complete. Metadata can rule a station OUT. Only the record can rule one IN.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
WEATHER = os.path.join(IA, "data", "weather")
GEOM = os.path.join(IA, "data", "geometry")
STATIONS = os.path.join(WEATHER, "asos_stations.json")
REGISTRY = os.path.join(GEOM, "national_registry.json")
OUT = os.path.join(WEATHER, "station_assignments.json")

sys.path.insert(0, HERE)
import metros as M                                                   # noqa: E402
import fetch_weather as W                                            # noqa: E402

# How many ranked candidates to MEASURE before giving up. Not a quality threshold -- a spend cap on
# a free but shared service: each candidate costs up to 60 requests. A facility that exhausts it is
# recorded as unassigned WITH the candidates tried, never assigned to the least-bad one.
#
# 4 -> 6, 2026-08-25. THE CAP WAS BEING SPENT ON SMALL MUNICIPAL FIELDS AND NEVER REACHING THE
# MAJOR AIRPORT. Measured on the first national run: AZ_way_938592711 has 27 stations inside 200 km
# and 24 viable on metadata, but its four nearest are GYR (0.6351), LUF (0.9486), GEU (0.4307) and
# BXK (0.9276) -- all under the 0.95 floor -- so it exhausted the cap and recorded UNASSIGNED while
# PHOENIX/SKY HARBOR sat FIFTH at 33.9 km, never fetched. Every Phoenix-area facility failed the
# same way, in 0.7 s each, because all four were already on disk and already known to be short.
#
# This does NOT relax a quality rule. `MIN_WEATHER_COVERAGE` is untouched and candidates are still
# ranked nearest-first, so a facility still takes the CLOSEST station that clears the floor; the cap
# only decides how far down that ranked list the search is allowed to look. Raising it converts
# outright failures into assignments and cannot degrade an assignment that already succeeded --
# a facility that found a station within four candidates never reaches candidate five.
# The extra spend is bounded and falls only on facilities that would otherwise have failed: at most
# two additional candidates, and only after four have already been measured and rejected.
MAX_CANDIDATES = 6
# Beyond this there is no honest claim that a station represents the site's air at all. Chosen to be
# generous rather than tuned: the widest accepted separation in the hand-built registry is KFFZ at
# 16.7 km, and this is an order of magnitude past it, so it excludes only the absurd.
MAX_DISTANCE_M = 200000.0


def haversine_m(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def load_json(p, what):
    if not os.path.exists(p):
        raise SystemExit("%s missing -- %s" % (os.path.basename(p), what))
    return json.load(open(p, encoding="utf-8"))


def viable(s, window_start="2021-01-01"):
    """Could this station POSSIBLY have a record over the window? Metadata only, no fetch."""
    if not s.get("online"):
        return False, "offline"
    if s.get("archive_end"):
        return False, "archive ended %s" % s["archive_end"]
    ab = s.get("archive_begin")
    if not ab:
        return False, "no archive_begin recorded"
    if ab > window_start:
        return False, "archive begins %s, after the window opens %s" % (ab, window_start)
    return True, None


def candidates(centre):
    """Every cached station, ranked by real distance, with a viability note. No network."""
    nets = load_json(STATIONS, "run fetch_asos_stations.py first")["networks"]
    out = []
    for st, net in nets.items():
        for s in net["stations"]:
            if s.get("lat") is None or s.get("lon") is None:
                continue
            d = haversine_m(centre, (s["lat"], s["lon"]))
            if d > MAX_DISTANCE_M:
                continue
            ok, why = viable(s)
            out.append({"sid": s["sid"], "name": s["name"], "network_state": st,
                        "tz": s["tz"], "distance_m": round(d, 1),
                        "metadata_viable": ok, "metadata_reason": why,
                        "archive_begin": s.get("archive_begin"),
                        "archive_end": s.get("archive_end")})
    out.sort(key=lambda r: r["distance_m"])
    return out, sorted(nets)


def measured_coverage(sid):
    """This station's coverage if its record is already on disk, else None. Never fetches."""
    p = W.station_path(sid)
    if not os.path.exists(p):
        return None
    try:
        m = json.load(open(p, encoding="utf-8"))["meta"]
    except (ValueError, KeyError):
        return None
    return {"coverage_frac": m.get("coverage_frac"), "n_with_temp": m.get("n_with_temp"),
            "n_hours": m.get("n_hours"), "failed_chunks": m.get("failed_chunks") or [],
            "file": os.path.basename(p)}


def facility(key):
    reg = load_json(REGISTRY, "run build_national_registry.py first")["facilities"]
    if key in reg:
        return reg[key], tuple(reg[key]["centre"])
    if key.lower() in M.METROS:
        return None, M.site_centre(key.lower())
    raise SystemExit("unknown facility %r" % key)


def load_assignments():
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT, encoding="utf-8"))
        except ValueError:
            pass
    return {"generated_by": "src/assign_station.py", "api_calls_made": 0,
            "rule": "ranked by real distance, then the FIRST candidate whose own five-year record "
                    "clears metros.MIN_WEATHER_COVERAGE. Proximity loses to completeness -- "
                    "measured, see this module's docstring for the KIWA/KFFZ precedent",
            "min_coverage": M.MIN_WEATHER_COVERAGE,
            "assignments": {}}


def report(key, cands, nets, limit=8):
    print("   facility %s" % key)
    print("   networks considered: %s" % ", ".join(nets))
    print("   %-5s %-26s %-9s %-9s %s" % ("sid", "name", "dist km", "meta", "coverage on disk"))
    for c in cands[:limit]:
        cov = measured_coverage(c["sid"])
        covs = ("%.4f" % cov["coverage_frac"]) if cov and cov["coverage_frac"] is not None \
            else "not fetched"
        print("   %-5s %-26s %8.1f  %-9s %s%s"
              % (c["sid"], (c["name"] or "")[:26], c["distance_m"] / 1000.0,
                 "ok" if c["metadata_viable"] else "REJECT", covs,
                 "" if c["metadata_viable"] else "   <- " + (c["metadata_reason"] or "")))


def main(argv):
    if not argv:
        raise SystemExit(__doc__.strip().splitlines()[2])
    cmd = argv[0]
    store = load_assignments()

    if cmd == "list":
        a = store["assignments"]
        print("%d facility assignment(s) on disk (no network):" % len(a))
        for k in sorted(a):
            r = a[k]
            print("   %-24s -> K%-4s %7.1f km  coverage %.4f  (%d candidate(s) tried)"
                  % (k, r["station"], r["distance_m"] / 1000.0, r["coverage_frac"],
                     len(r["candidates_tried"])))
        return 0

    if len(argv) < 2:
        raise SystemExit("name a facility key")
    key = argv[1]
    fac, centre = facility(key)
    cands, nets = candidates(centre)
    print("=" * 78)
    print("STATION ASSIGNMENT -- %s  (%.5f, %.5f)" % (key, centre[0], centre[1]))
    print("=" * 78)
    if fac:
        print("   %s | %s | %s" % (", ".join(fac.get("names") or ["(unnamed)"]),
                                   fac.get("state"), fac.get("kind")))
    report(key, cands, nets)

    viables = [c for c in cands if c["metadata_viable"]]
    print("\n   %d station(s) within %.0f km, %d viable on metadata"
          % (len(cands), MAX_DISTANCE_M / 1000.0, len(viables)))

    if cmd == "dryrun":
        print("\n   DRY RUN. Nothing fetched. It would measure, in order:")
        for c in viables[:MAX_CANDIDATES]:
            cov = measured_coverage(c["sid"])
            print("      K%-4s %7.1f km   %s"
                  % (c["sid"], c["distance_m"] / 1000.0,
                     "already on disk (0 requests)" if cov else "60 month-chunk requests"))
        print("   cap: %d candidate(s). A facility that exhausts it is recorded UNASSIGNED with"
              % MAX_CANDIDATES)
        print("   its candidates, never assigned to the least-bad station.")
        return 0

    if cmd != "run":
        raise SystemExit("commands: dryrun | run | list")

    tried = []
    chosen = None
    for c in viables[:MAX_CANDIDATES]:
        cov = measured_coverage(c["sid"])
        if cov is None:
            print("\n   measuring K%s at %.1f km -- fetching its five-year record"
                  % (c["sid"], c["distance_m"] / 1000.0))
            rc = W.build_station(c["sid"], c["tz"], W.station_path(c["sid"]),
                                 label="%s (%s)" % (c["name"], c["network_state"]))
            if rc != 0:
                tried.append(dict(c, coverage_frac=None, verdict="fetch_failed"))
                print("      fetch failed -- recorded, moving to the next candidate")
                continue
            cov = measured_coverage(c["sid"])
        if cov is None or cov["coverage_frac"] is None:
            tried.append(dict(c, coverage_frac=None, verdict="no_record"))
            continue
        ok = cov["coverage_frac"] >= M.MIN_WEATHER_COVERAGE
        tried.append(dict(c, coverage_frac=cov["coverage_frac"], n_with_temp=cov["n_with_temp"],
                          verdict="accepted" if ok else "below_coverage_floor"))
        print("      K%s: %.4f coverage over %s hours  -> %s"
              % (c["sid"], cov["coverage_frac"], format(cov["n_with_temp"], ","),
                 "ACCEPTED" if ok else "BELOW THE %.2f FLOOR, trying the next" % M.MIN_WEATHER_COVERAGE))
        if ok:
            chosen = (c, cov)
            break

    if not chosen:
        store["assignments"].pop(key, None)
        # 🔴 TWO DIFFERENT FAILURES WERE REPORTED AS ONE, AND THE WRONG ONE. This always said
        # "no candidate ... cleared the coverage floor", which blames the 0.95 floor -- so eleven
        # facilities were recorded as having poor station records when NOT ONE STATION HAD BEEN
        # MEASURED. `candidates_tried` was `[]`, because the cached ASOS inventory holds 17 state
        # networks and California and New York are not among them: `fetch_asos_stations.py` was run
        # for the states that had facilities at the time. Ten of the eleven were Californian.
        # A message that names the wrong cause sends the next reader to measure coverage on stations
        # that were never in the list.
        store.setdefault("unassigned", {})[key] = {
            "why": ("no station is CACHED for this facility's search area -- 0 candidates, so the "
                    "%.2f coverage floor was never reached. Run fetch_asos_stations.py for this "
                    "state." % M.MIN_WEATHER_COVERAGE) if not tried else
                   ("none of the %d nearest stations cleared the %.2f coverage floor"
                    % (len(tried), M.MIN_WEATHER_COVERAGE)),
            "n_candidates_tried": len(tried),
            "candidates_tried": tried}
        json.dump(store, open(OUT, "w", encoding="utf-8"), allow_nan=False)
        print("\n   UNASSIGNED. %d candidate(s) measured, none cleared the floor. Recorded with"
              % len(tried))
        print("   its candidates rather than assigned to the least-bad one -- a site with no")
        print("   honest bound must not be offered.")
        return 3

    c, cov = chosen
    store.setdefault("unassigned", {}).pop(key, None)
    store["assignments"][key] = {
        "station": c["sid"], "station_name": c["name"], "tz": c["tz"],
        "network_state": c["network_state"],
        "distance_m": c["distance_m"], "coverage_frac": cov["coverage_frac"],
        "n_with_temp": cov["n_with_temp"], "n_hours": cov["n_hours"],
        "record_file": cov["file"], "failed_chunks": cov["failed_chunks"],
        "candidates_tried": tried,
        "rule": "first candidate by distance whose OWN record clears %.2f" % M.MIN_WEATHER_COVERAGE,
    }
    json.dump(store, open(OUT, "w", encoding="utf-8"), allow_nan=False)
    print("\n   ASSIGNED %s -> K%s (%s), %.1f km, coverage %.4f"
          % (key, c["sid"], c["name"], c["distance_m"] / 1000.0, cov["coverage_frac"]))
    rejected = [t for t in tried if t["verdict"] != "accepted"]
    if rejected:
        print("   %d nearer candidate(s) rejected on measurement: %s"
              % (len(rejected), ", ".join("K%s (%.1f km, %s)"
                                          % (t["sid"], t["distance_m"] / 1000.0, t["verdict"])
                                          for t in rejected)))
    print("   wrote %s" % OUT)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
