# -*- coding: utf-8 -*-
"""N-51 step 1  ---  FULL-YEAR hourly weather at KIAD, all hours. FREE, no API key.

WHY
    Every dataset so far is summer-only at 16:00 site-local (534 days) because the earlier tests were
    about the afternoon peak. Counting FREE-COOLING HOURS needs every hour of every year: free cooling
    is mostly available at night and in the shoulder seasons, which the 16:00 summer sample cannot see
    at all.

WHAT IT COLLECTS
    tmpc  dry-bulb air temperature      -> the free-cooling changeover variable
    dwpc  dew point                     -> lets wet-bulb / enthalpy limits be computed later
    drct  wind direction                -> which bearing the plume is on, hour by hour
    sknt  wind speed                    -> plume dilution
    Five complete calendar years, 2021-2025, so annual hour counts are over whole years and not
    biased by a partial one.

DISCIPLINE
    * tz requested from the server as America/New_York -- never computed from a local clock
      (HANDOFF GOTCHA #1, the 9-hour bug).
    * Monthly chunks with retries, saved incrementally per year, so a 503 loses one month rather than
      the run (GOTCHA #13: Iowa State rate-limits and 503s on large requests).
    * Every field parsed BEFORE touching the dict, because setdefault() creates the key first and 'M'
      for missing would leave an empty list that explodes fmean() later (GOTCHA #10).
"""
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request

from common import banner, FIXTURES

FIXTURE = os.path.join(FIXTURES, "n51_kiad_fullyear.json")
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "IAD"
YEARS = [2021, 2022, 2023, 2024, 2025]
RETRIES = 4
BACKOFF_S = 6


def fetch(y, m):
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    parts = [("station", STATION), ("data", "tmpc"), ("data", "dwpc"),
             ("data", "drct"), ("data", "sknt"),
             ("year1", y), ("month1", m), ("day1", 1),
             ("year2", y2), ("month2", m2), ("day2", 1),
             ("tz", "America/New_York"), ("format", "onlycomma"), ("latlon", "no"),
             ("missing", "M"), ("trace", "T"), ("direct", "no"), ("report_type", 3)]
    url = BASE + "?" + urllib.parse.urlencode(parts)
    for a in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace")
        except Exception as e:
            if a == RETRIES - 1:
                print("      FAILED %d-%02d after %d attempts: %s" % (y, m, RETRIES, str(e)[:90]))
                return None
            time.sleep(BACKOFF_S)
    return None


def parse_into(raw, obs):
    """{(date, hour): [(tmpc, dwpc, drct, sknt)]}. Temperature is required; the rest may be missing."""
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


def main():
    banner("N-51 step 1  full-year hourly KIAD weather, 2021-2025   [FREE, no key]")

    if os.path.exists(FIXTURE):
        d = json.load(open(FIXTURE, encoding="utf-8"))
        print("   cached: %s" % FIXTURE)
        print("   %d hourly records" % len(d["hours"]))
        return 0

    obs, failed = {}, []
    n = 0
    total = len(YEARS) * 12
    t0 = time.time()
    for y in YEARS:
        for m in range(1, 13):
            n += 1
            raw = fetch(y, m)
            if raw is None:
                failed.append("%d-%02d" % (y, m))
                continue
            k = parse_into(raw, obs)
            if m % 3 == 0 or m == 12:
                print("   [%2d/%2d] %d-%02d  %5d rows   running hours: %6d   %.0fs elapsed"
                      % (n, total, y, m, k, len(obs), time.time() - t0))

    if not obs:
        print("\n   NOTHING FETCHED -- not writing a fixture (an empty one would poison later steps)")
        return 2

    # average duplicate reports inside the hour; keep None-safe means per field
    hours = {}
    for (date, hh), rows in obs.items():
        def avg(j):
            v = [r[j] for r in rows if r[j] is not None]
            return round(statistics.fmean(v), 2) if v else None
        hours["%s %02d" % (date, hh)] = [avg(0), avg(1), avg(2), avg(3)]

    temps = sorted(v[0] for v in hours.values() if v[0] is not None)
    nT = len(temps)
    meta = {
        "station": "KIAD", "years": YEARS,
        "tz_requested_from_server": "America/New_York",
        "fields": ["tmpc", "dwpc", "drct", "sknt"],
        "n_hours": len(hours), "n_with_temp": nT,
        "expected_hours_5y": 5 * 8760,
        "coverage_frac": nT / (5 * 8760.0),
        "temp_min": temps[0], "temp_p10": temps[int(0.10 * (nT - 1))],
        "temp_median": statistics.median(temps),
        "temp_p90": temps[int(0.90 * (nT - 1))], "temp_max": temps[-1],
        "failed_chunks": failed,
        "source": "NOAA ASOS via Iowa State Environmental Mesonet (free, no key)",
    }
    json.dump({"hours": hours, "meta": meta}, open(FIXTURE, "w"))

    print("\n   hourly records: %d  (%.1f %% of the %d hours in five years)"
          % (len(hours), 100 * meta["coverage_frac"], 5 * 8760))
    print("   dry-bulb: min %.1f  p10 %.1f  median %.1f  p90 %.1f  max %.1f C"
          % (meta["temp_min"], meta["temp_p10"], meta["temp_median"], meta["temp_p90"],
             meta["temp_max"]))
    if failed:
        print("   WARNING: %d chunk(s) missing: %s" % (len(failed), ", ".join(failed)))
    print("\n   written: %s" % FIXTURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
