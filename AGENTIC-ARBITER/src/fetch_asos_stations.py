# -*- coding: utf-8 -*-
"""S5 STEP 1 -- THE ASOS STATION LIST, per state.  FREE, KEYLESS, ZERO FORTYGUARD CALLS.

    python fetch_asos_stations.py IA IL          # named states
    python fetch_asos_stations.py --registry     # every state present in the national registry
    python fetch_asos_stations.py --list         # what is already cached. No network.

WHY THIS EXISTS
    `fetch_weather.py` fetches a five-year hourly record for a STATION CODE, and until now every
    station code in this project was typed by hand into `metros.METROS` -- five of them. A national
    build cannot type 639. Nothing in the repo listed stations or mapped a coordinate to one:
    HANDOFF called the capability "confirmed working, NOT YET SCRIPTED" in three places, and the
    confirmation lived only in prose.

WHAT THE ENDPOINT GIVES, verified against a real response before this file was written
    GET https://mesonet.agron.iastate.edu/geojson/network/<STATE>_ASOS.geojson
    -> {"type": "FeatureCollection", "count": 62, "generated_at": "...", "features": [...]}
    Each feature: geometry.coordinates = [LON, LAT]  (GeoJSON order -- the reverse of every
    lat/lon pair elsewhere in this project, which is exactly the trap `metros.committed_imagery`
    documents for ArcGIS bboxes), and properties carrying:
        sid            'ADU'                 the station code, 3 letters
        sname          'AUDUBON'
        state          'IA'
        tzname         'America/Chicago'     a real IANA zone, per station
        online         True
        archive_begin  '1994-12-25'          <- the cheap viability signal, see below
        archive_end    None                  <- non-null means the station STOPPED reporting
        elevation      399.3

🔴 `archive_begin` / `archive_end` ARE WHY THIS IS AFFORDABLE.
    Measuring a station's five-year completeness costs 60 month-chunk requests. Assigning stations
    to 639 facilities by measuring every nearby candidate would be tens of thousands of requests
    against a free, volunteer-run service. But a station whose archive BEGINS after 2021-01-01
    cannot have a 2021-2025 record, and one with a non-null `archive_end` has stopped -- both
    knowable from ONE request per state. Measured on Iowa: 62 stations, 61 survive that filter, so
    the metadata alone does not prune much in a well-served state -- its real value is catching the
    handful that would otherwise waste 60 requests each proving they have no data.

    ⚠ AND WHAT IT DOES NOT TELL YOU, said plainly: `archive_begin` is the FIRST observation, not a
    promise of continuity. KIWA's archive begins long before 2021 and its five-year record is still
    only 81.70 % complete, with 2021 at 50.8 % -- which is why `metros.py` rejected it at 2.7 km in
    favour of KFFZ at 16.7 km. Metadata can rule a station OUT. Only the record itself can rule one
    IN, and `assign_station.py` is where that measurement happens.

STATE COVERAGE IS NOT A BORDER. A facility in eastern Iowa may be closest to an Illinois station.
    So the assigner reads EVERY cached network, and records which networks it considered, rather
    than silently limiting itself to the facility's own state.
"""
import json
import os
import sys
import time
import http.client
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
WEATHER = os.path.join(IA, "data", "weather")
GEOM = os.path.join(IA, "data", "geometry")
OUT = os.path.join(WEATHER, "asos_stations.json")

URL = "https://mesonet.agron.iastate.edu/geojson/network/%s_ASOS.geojson"
UA = {"User-Agent": "AGENTIC-ARBITER/1.0 (FortyGuard Hackathon 2026; free-cooling agent)"}
PAUSE_S = 2.0           # between states. One request each; there is no hurry.
RETRIES = 3


def load_cache():
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT, encoding="utf-8"))
        except ValueError:
            pass
    return {"generated_by": "src/fetch_asos_stations.py", "api_calls_made": 0,
            "source": "Iowa State Environmental Mesonet, <STATE>_ASOS network metadata "
                      "(free, keyless, no credential)",
            "coordinate_order_note": "geometry.coordinates is [lon, lat]; this file stores "
                                     "lat/lon as named fields so the order cannot be misread",
            "networks": {}}


def _get(url):
    """GET a URL, trying urllib and then http.client. Returns bytes, or raises the last error.

    🔴 urllib FAILS ON SOME STATES AND http.client DOES NOT, WITH THE SAME HEADER. Measured
    2026-08-26, back to back, same process, same User-Agent:

        CA   urllib=ConnectionResetError   http.client=OK 161 features
        NY   urllib=OK 53 features         http.client=OK 53 features

    CA, FL and MN each failed all three urllib retries with WinError 10054 -- "an existing
    connection was forcibly closed by the remote host" -- and were correctly recorded as absent
    rather than empty. They are among the largest state networks, and the endpoint serves them
    fine: `http.client` retrieved California's 161 stations first time. So this was never an
    upstream outage and never a rate limit; three states were simply unreachable through one
    HTTP client and reachable through another.

    I have NOT established why, and this comment does not pretend to. urllib adds headers of its
    own (Accept-Encoding, Connection) that http.client does not, and the failure tracks payload
    size, which points at the interaction between those and a large chunked response -- a
    hypothesis, not a finding. What is established is the behaviour above, which is enough to fix
    it: try both, prefer the one that answers.
    """
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
    except Exception:
        parts = urllib.parse.urlsplit(url)
        c = http.client.HTTPSConnection(parts.netloc, timeout=120)
        try:
            c.request("GET", parts.path or "/", headers=UA)
            r = c.getresponse()
            body = r.read()
            if r.status != 200:
                raise OSError("HTTP %s %s" % (r.status, r.reason))
            return body
        finally:
            c.close()


def fetch_state(st):
    """One state's ASOS network, or None. Never raises -- a missing state is recorded, not fatal."""
    for i in range(RETRIES):
        try:
            d = json.loads(_get(URL % st))
            out = []
            for f in d.get("features", []):
                p = f.get("properties") or {}
                c = (f.get("geometry") or {}).get("coordinates") or [None, None]
                out.append({
                    "sid": p.get("sid") or f.get("id"),
                    "name": p.get("sname"),
                    "state": p.get("state"),
                    "tz": p.get("tzname"),
                    "online": bool(p.get("online")),
                    "archive_begin": p.get("archive_begin"),
                    "archive_end": p.get("archive_end"),
                    "elevation_m": p.get("elevation"),
                    # NAMED, not positional. The source is [lon, lat] and everything else in this
                    # project is (lat, lon); storing them by name removes the whole class of bug.
                    "lat": c[1], "lon": c[0],
                })
            return {"count": d.get("count"), "generated_at": d.get("generated_at"),
                    "n_stations": len(out), "stations": out}
        except Exception as e:                                        # noqa: BLE001
            print("      %s attempt %d/%d: %s" % (st, i + 1, RETRIES, str(e)[:66]))
            if i < RETRIES - 1:
                time.sleep(5 * (2 ** i))
    return None


def registry_states():
    p = os.path.join(GEOM, "national_registry.json")
    if not os.path.exists(p):
        raise SystemExit("national_registry.json missing -- run build_national_registry.py first")
    f = json.load(open(p, encoding="utf-8"))["facilities"]
    return sorted({v["state"] for v in f.values() if v.get("state")})


def main(argv):
    cache = load_cache()

    if "--list" in argv:
        print("cached ASOS networks (no network calls made):")
        tot = 0
        for st in sorted(cache["networks"]):
            n = cache["networks"][st]["n_stations"]
            tot += n
            print("   %-4s %4d stations   fetched %s" % (st, n, cache["networks"][st]["generated_at"]))
        print("   %d state(s), %d stations" % (len(cache["networks"]), tot))
        return 0

    want = registry_states() if "--registry" in argv else [a.upper() for a in argv if a.isalpha()]
    if not want:
        raise SystemExit("name states (e.g. IA IL) or pass --registry")

    # INCREMENTAL. One request per state is cheap, but re-requesting 43 states that are already on
    # disk is 43 needless hits on a free service every time this runs in a pipeline.
    todo = [s for s in want if s not in cache["networks"]]
    print("=" * 78)
    print("ASOS STATION LIST -- free, keyless.  %d state(s) wanted, %d already cached, %d to fetch"
          % (len(want), len(want) - len(todo), len(todo)))
    print("=" * 78)

    failed = []
    for i, st in enumerate(todo, 1):
        print("   [%d/%d] %s ..." % (i, len(todo), st), end=" ", flush=True)
        got = fetch_state(st)
        if not got:
            failed.append(st)
            print("FAILED -- recorded, not skipped silently")
            continue
        cache["networks"][st] = got
        print("%d stations" % got["n_stations"])
        if i < len(todo):
            time.sleep(PAUSE_S)

    cache["states_failed"] = failed
    os.makedirs(WEATHER, exist_ok=True)
    json.dump(cache, open(OUT, "w", encoding="utf-8"), allow_nan=False)

    stations = sum(v["n_stations"] for v in cache["networks"].values())
    print("\n   %d network(s) cached, %d stations total" % (len(cache["networks"]), stations))
    if failed:
        print("   %d state(s) FAILED and are absent, not assumed empty: %s"
              % (len(failed), ", ".join(failed)))
    print("   wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
