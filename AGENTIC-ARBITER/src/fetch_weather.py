# -*- coding: utf-8 -*-
"""FIVE YEARS OF HOURLY WEATHER for any metro in the registry. FREE, keyless.

    METRO=phoenix python fetch_weather.py
    python fetch_weather.py --all          # every registry metro that is missing its record

NO FortyGuard CREDENTIAL IS READ OR USED. Source: NOAA ASOS via Iowa State Environmental Mesonet.

--------------------------------------------------------------------------------------------
WHY THIS IS THE GATING STEP FOR A NEW SITE, NOT THE FORTYGUARD CALL
--------------------------------------------------------------------------------------------
The safety margin this agent ships is not chosen -- it is a conformal quantile of how wrong the
forecast has actually been AT THAT STATION, stratified by hour of day. So a new site cannot borrow
Ashburn's margin: KIAD's residual distribution says nothing about Mesa's. A metro without its own
five-year record has NO honest bound and must not be offered in the interface as though it did.

That makes this free download the real prerequisite. The 4,220-credit FortyGuard call adds the
spatial field and the level-offset measurement; it does not substitute for the station history.

--------------------------------------------------------------------------------------------
FAITHFUL TO THE PROVEN FETCHER
--------------------------------------------------------------------------------------------
The chunking, retry/backoff, row parsing, the -50..55 C sanity window, the duplicate-report
averaging within an hour and the meta block are all carried over from
`testing/fetch_n51_fullyear.py`, which produced the 43,763-record KIAD file every published number
rests on. Only the STATION, the TIMEZONE and the OUTPUT PATH are parameters. Keeping the parsing
identical is deliberate: a second parser would be a second way to compute one quantity, which is
the mistake this project has made most often (gotcha #12).

    ⚠ Iowa State rate-limits and returns 503s under load (gotcha #13). Hence month-sized chunks,
    four attempts each with growing backoff, and `failed_chunks` recorded in the output rather than
    a silent gap. A partial record is written ONLY with its failures listed.
"""
import datetime
import glob
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import metros as M                                                          # noqa: E402

BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
YEARS = [2021, 2022, 2023, 2024, 2025]
RETRIES = 4
BACKOFF_S = 6
MIN_COVERAGE = 0.95      # below this the record is too gappy to calibrate a per-hour quantile on


def fetch_chunk(station, tz, y, m):
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    parts = [("station", station), ("data", "tmpc"), ("data", "dwpc"),
             ("data", "drct"), ("data", "sknt"),
             ("year1", y), ("month1", m), ("day1", 1),
             ("year2", y2), ("month2", m2), ("day2", 1),
             ("tz", tz), ("format", "onlycomma"), ("latlon", "no"),
             ("missing", "M"), ("trace", "T"), ("direct", "no"), ("report_type", 3)]
    url = BASE + "?" + urllib.parse.urlencode(parts)
    for a in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace")
        except Exception as e:
            if a == RETRIES - 1:
                print("      FAILED %d-%02d after %d attempts: %s" % (y, m, RETRIES, str(e)[:80]))
                return None
            time.sleep(BACKOFF_S * (a + 1))
    return None


def parse_into(raw, obs):
    """{(date, hour): [(tmpc, dwpc, drct, sknt)]}. Temperature required; the rest may be missing."""
    kept = 0
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 6:
            continue
        try:
            date, tm = p[1].split(" ")
            hh = int(tm.split(":")[0])
            tmpc = float(p[2])
        except Exception:
            continue
        if tmpc < -50.0 or tmpc > 55.0:
            continue

        def opt(j):
            try:
                return float(p[j])
            except Exception:
                return None

        obs.setdefault((date, hh), []).append((tmpc, opt(3), opt(4), opt(5)))
        kept += 1
    return kept


def expected_hours():
    """The REAL number of hours in the requested span, counted from the calendar.

    🔴 THIS WAS `len(YEARS) * 8760`, AND 2024 IS A LEAP YEAR.
    2021-01-01 00:00 to 2026-01-01 00:00 is 1,826 days = **43,824 hours**, not 43,800. So every
    coverage figure this module has ever written is inflated by a factor of 1.000548, i.e. +0.055
    percentage points. Measured on the four records on disk: KIAD 0.999155 published against
    0.998608 true, KFFZ 0.957055 against 0.956531.

    Small, and it did not change any of the four existing verdicts -- but `MIN_COVERAGE` is a
    DECISION BOUNDARY at 0.95, so an inflated numerator-over-denominator can pass a station that
    should fail: a true 0.9497 record reports 0.9502. At three hand-checked sites that is noise. At
    639 facilities, each assigned a station by this gate with nobody inspecting individual results,
    it is a wrong answer waiting for the station that lands in the 0.055 pp band.

    Counted, not multiplied, so it stays right if YEARS ever changes.
    """
    a = datetime.date(YEARS[0], 1, 1)
    b = datetime.date(YEARS[-1] + 1, 1, 1)
    return (b - a).days * 24


def recompute_meta(path):
    """Recompute the derived meta of an EXISTING record from its own stored hours. No network.

    `build()` returns early when the file exists -- correctly, since refetching costs 60 requests
    per station against a free shared service for data that has not changed. But that also means a
    fix to a DERIVED figure (like the leap-year denominator above) would never reach the four
    records already on disk without deleting and refetching them: 240 requests to recompute a
    division. This recomputes from the hours already stored, which is the same arithmetic on the
    same inputs.
    """
    d = json.load(open(path, encoding="utf-8"))
    hours, meta = d["hours"], d["meta"]
    temps = sorted(v[0] for v in hours.values() if v[0] is not None)
    if not temps:
        return None
    nT = len(temps)
    before = meta.get("coverage_frac")
    meta["n_hours"] = len(hours)
    meta["n_with_temp"] = nT
    meta["expected_hours_5y"] = expected_hours()
    meta["coverage_frac"] = nT / float(expected_hours())
    meta["temp_min"], meta["temp_max"] = temps[0], temps[-1]
    meta["temp_p10"] = temps[int(0.10 * (nT - 1))]
    meta["temp_p90"] = temps[int(0.90 * (nT - 1))]
    meta["temp_median"] = statistics.median(temps)
    json.dump(d, open(path, "w", encoding="utf-8"), allow_nan=False)
    return before, meta["coverage_frac"], nT


def station_path(station):
    """Where a station's record lives. Keyed by STATION, not by site, which is the whole point:
    Ashburn and Dulles already share `kiad_hourly_2021_2025.json` deliberately, and at national
    scale hundreds of facilities will legitimately share a few hundred stations. Sharing a station
    is physically correct; sharing geometry, imagery, a tile or a plume is not."""
    if station.upper() == "IAD":
        return os.path.join(os.path.dirname(M.weather_path("ashburn")),
                            "kiad_hourly_2021_2025.json")     # PRE-EXISTING, audited, do not rename
    return os.path.join(os.path.dirname(M.weather_path("ashburn")),
                        "k%s_hourly_2021_2025.json" % station.lower())


def build(key):
    """Fetch the record for a REGISTRY key, resolving its station and zone from the registry."""
    met = M.metro(key)
    return build_station(met["station"], met["tz"], M.weather_path(key),
                         label=met.get("label"), metro=key)


def build_station(station, tz, out_path, label=None, metro=None):
    """Fetch a five-year record for an ARBITRARY station code and zone.

    THE GENERALISATION S5 NEEDED. `build()` used to resolve `station`, `tz` and the output path from
    `metros.METROS` -- five hand-written entries -- so there was no way to fetch a station chosen by
    measurement rather than typed by a person. Everything below is the original body unchanged; only
    the three inputs moved from a registry lookup to arguments. `build()` is now a thin caller, so
    there is exactly one implementation of the fetch (gotcha #12).
    """
    if not station:
        raise SystemExit("build_station needs a station code; refusing to guess one")
    if os.path.exists(out_path):
        d = json.load(open(out_path, encoding="utf-8"))
        print("   %-11s cached: %s  (%s records)"
              % (metro or station, os.path.basename(out_path), format(len(d["hours"]), ",")))
        return 0

    key = metro or station
    print("\n   %-11s K%s  tz %s  ->  %s"
          % (key, station, tz, os.path.basename(out_path)))
    print("      %d monthly chunks. Iowa State rate-limits, so this is slow on purpose."
          % (len(YEARS) * 12))
    obs, failed = {}, []
    n, total, t0 = 0, len(YEARS) * 12, time.time()
    for y in YEARS:
        for m in range(1, 13):
            n += 1
            raw = fetch_chunk(station, tz, y, m)
            if raw is None:
                failed.append("%d-%02d" % (y, m))
                continue
            k = parse_into(raw, obs)
            if m % 6 == 0:
                print("      [%2d/%2d] %d-%02d  %5d rows   running hours %6d   %.0fs"
                      % (n, total, y, m, k, len(obs), time.time() - t0))

    if not obs:
        print("      NOTHING FETCHED -- refusing to write. An empty record would poison every")
        print("      downstream calibration, and a missing file is honest where an empty one is not.")
        return 2

    hours = {}
    for (date, hh), rows in obs.items():
        def avg(j):
            v = [r[j] for r in rows if r[j] is not None]
            return round(statistics.fmean(v), 2) if v else None
        hours["%s %02d" % (date, hh)] = [avg(0), avg(1), avg(2), avg(3)]

    temps = sorted(v[0] for v in hours.values() if v[0] is not None)
    nT = len(temps)
    cov = nT / float(expected_hours())
    meta = {
        "station": "K" + station, "years": YEARS,
        "tz_requested_from_server": tz,
        "fields": ["tmpc", "dwpc", "drct", "sknt"],
        "n_hours": len(hours), "n_with_temp": nT,
        "expected_hours_5y": expected_hours(),
        "coverage_frac": cov,
        "temp_min": temps[0], "temp_p10": temps[int(0.10 * (nT - 1))],
        "temp_median": statistics.median(temps),
        "temp_p90": temps[int(0.90 * (nT - 1))], "temp_max": temps[-1],
        "failed_chunks": failed,
        # `metro` is None when the station was chosen by MEASUREMENT rather than named in the
        # hand-written registry -- a station serves facilities, it does not belong to one.
        "metro": metro, "metro_label": label,
        "source": "NOAA ASOS via Iowa State Environmental Mesonet (free, no key)",
        "generated_by": "AGENTIC-ARBITER/src/fetch_weather.py",
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"hours": hours, "meta": meta}, open(out_path, "w"), allow_nan=False)
    # `expected_hours()`, not `len(YEARS) * 8760` -- the printed denominator was still the stale
    # 43,800 while `cov` above had already been corrected to the real 43,824, so the line reported a
    # correct percentage against a wrong total. A number and its own denominator disagreeing in one
    # sentence is the "prose that no check re-reads" family (rule 11) in miniature.
    print("      %s records, %.2f %% of the %d hours in five years%s"
          % (format(len(hours), ","), 100 * cov, expected_hours(),
             ("  FAILED CHUNKS: " + ",".join(failed)) if failed else ""))
    print("      dry-bulb  min %.1f  p10 %.1f  median %.1f  p90 %.1f  max %.1f C"
          % (meta["temp_min"], meta["temp_p10"], meta["temp_median"], meta["temp_p90"],
             meta["temp_max"]))
    # PER-YEAR COUNTS, because an overall coverage figure hides a structural gap. KIWA came back at
    # 81.70 % overall, which sounds survivable -- until you split it: 4,454 records in 2021 and
    # 5,747 in 2022 against ~8,520 in 2023-25. The station was not reporting hourly in the early
    # years, so half the calibration window is thin rather than uniformly sparse.
    per_year = {}
    for k in hours:
        per_year[k[:4]] = per_year.get(k[:4], 0) + 1
    print("      per year: " + "  ".join("%s %s" % (y, format(per_year.get(str(y), 0), ","))
                                         for y in YEARS))
    # A LONE HIGH OUTLIER. The -50..55 C window is a sanity filter, not an outlier filter: KIWA's
    # max came back at 54.0 C with the next value at 46.0 and nothing in between, which is a sensor
    # fault, not weather. Reported rather than silently dropped -- a spurious HIGH reading only
    # widens a safety margin, so it is not dangerous, but it is still wrong and the reader is
    # entitled to know it is there.
    if nT > 100:
        hi = temps[-1]
        nxt = temps[int(0.9999 * (nT - 1))]
        if hi - nxt > 3.0:
            print("      SUSPECT HIGH READING: max %.1f C with the 99.99th percentile at %.1f C"
                  % (hi, nxt))
            print("        A %.1f C jump with nothing between is a sensor fault. Not removed here;"
                  % (hi - nxt))
            print("        recorded so a quantile fitted near the top is known to be affected.")
            meta["suspect_high_reading_c"] = hi
            meta["suspect_high_gap_c"] = round(hi - nxt, 2)
            json.dump({"hours": hours, "meta": meta}, open(out_path, "w"), allow_nan=False)
    if cov < MIN_COVERAGE:
        print("      *** COVERAGE %.2f %% IS BELOW THE %.0f %% FLOOR ***"
              % (100 * cov, 100 * MIN_COVERAGE))
        print("        Written, but this station is too gappy to calibrate a per-hour-of-day")
        print("        quantile on, so metros.readiness() will not mark this metro offerable.")
    return 0


def main(argv):
    print("=" * 78)
    print("FIVE-YEAR HOURLY WEATHER  --  free, keyless, NOAA ASOS via Iowa State")
    print("=" * 78)
    if "--recompute-meta" in argv:
        # ZERO NETWORK. Re-derives coverage and the percentiles from hours already on disk, so a
        # correction to a DERIVED figure does not cost 60 requests per station against a free
        # shared service for data that has not changed.
        print("   recomputing derived meta from stored hours. No requests will be made.")
        print("   expected hours in %d-%d = %d (counted from the calendar, leap years included)"
              % (YEARS[0], YEARS[-1], expected_hours()))
        n = 0
        for p in sorted(glob.glob(os.path.join(os.path.dirname(M.weather_path("ashburn")),
                                               "k*_hourly_*.json"))):
            r = recompute_meta(p)
            if r:
                before, after, nT = r
                print("      %-34s %s -> %.6f  (%s hours with temperature)"
                      % (os.path.basename(p),
                         ("%.6f" % before) if before is not None else "none", after,
                         format(nT, ",")))
                n += 1
        print("   %d record(s) updated." % n)
        return 0
    if "--all" in argv:
        keys = [k for k in sorted(M.METROS) if not os.path.exists(M.weather_path(k))]
        if not keys:
            print("   every registry metro already has its record.")
            return 0
    else:
        keys = [M.metro_key()]
    print("   fetching: %s" % ", ".join(keys))
    rc = 0
    for k in keys:
        rc |= build(k)
    print("\n   done. `python metros.py` now shows what is offerable.")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
