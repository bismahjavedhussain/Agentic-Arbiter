# -*- coding: utf-8 -*-
"""N-46 step 1  ---  fetch REAL wind direction/speed history for KIAD. FREE, no API key.

WHY, and how this differs from what already exists
    test_n40_windsharpen.py cached a direction-ERROR pool only, from 72 days in summer 2026
    (results/fixtures/n40_kiad_dir_errors.json). N-46 additionally needs the DIRECTION DISTRIBUTION
    itself -- how often the wind actually blows from each bearing -- because a worst-case fixed
    margin must cover the plume peak on every hour of the year, and the agent's saving depends on
    how rare those bearings really are. Averaging over an assumed-uniform compass would silently
    invent the answer.

    It also re-derives the direction error pool over SIX summers (2021-2026) rather than 72 days,
    which is a large power gain for free.

CONVENTIONS, matched to existing work rather than reinvented
    * Station KIAD, target hour 16:00 SITE-LOCAL, tz requested from the server -- never computed from
      the local clock (HANDOFF GOTCHA #1, the 9-hour timezone bug).
    * Calm hours excluded at < 3 kt: ASOS reports drct = 0 when calm, which is not a direction.
      Same rule and same threshold as test_n40_windsharpen.py.
    * Persistence error per lead L: angdiff(drct(16:00), drct(16:00 - L)), signed, in degrees.
    * Chunked ~3 weeks with retries, saved once at the end but only if non-empty (GOTCHA #13).
"""
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request

from common import banner, FIXTURES

FIXTURE = os.path.join(FIXTURES, "n46_kiad_wind.json")
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "IAD"
TARGET_HOUR = 16
LEADS = list(range(1, 13))
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
SPANS = [(6, 1, 6, 21), (6, 21, 7, 11), (7, 11, 8, 1), (8, 1, 8, 21), (8, 21, 9, 1)]
MIN_KT = 3.0
RETRIES = 4
BACKOFF_S = 6


def angdiff(a, b):
    """Signed smallest angle a - b, in (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return d


def fetch_chunk(y, m1, d1, m2, d2):
    parts = [("station", STATION), ("data", "drct"), ("data", "sknt"),
             ("year1", y), ("month1", m1), ("day1", d1),
             ("year2", y), ("month2", m2), ("day2", d2),
             ("tz", "America/New_York"), ("format", "onlycomma"), ("latlon", "no"),
             ("missing", "M"), ("trace", "T"), ("direct", "no"), ("report_type", 3)]
    url = BASE + "?" + urllib.parse.urlencode(parts)
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == RETRIES - 1:
                print("      FAILED %d-%02d-%02d..%02d-%02d: %s" % (y, m1, d1, m2, d2, e))
                return None
            time.sleep(BACKOFF_S)
    return None


def parse_into(raw, obs):
    """Accumulate {(date, hour): [(drct, sknt)]}. Every field parsed BEFORE touching obs, because
    setdefault() creates the key first and 'M' for missing would otherwise leave an empty list that
    blows up fmean() later. HANDOFF GOTCHA #10."""
    kept = 0
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 4:
            continue
        try:
            date, tm = p[1].split(" ")
            hh = int(tm.split(":")[0])
            drct = float(p[2])
            sknt = float(p[3])
        except Exception:
            continue
        if not (0.0 <= drct <= 360.0) or sknt < 0.0 or sknt > 200.0:
            continue
        obs.setdefault((date, hh), []).append((drct, sknt))
        kept += 1
    return kept


def main():
    banner("N-46 step 1  wind direction + speed, KIAD, 2021-2026 summers   [FREE, no key]")

    if os.path.exists(FIXTURE):
        d = json.load(open(FIXTURE, encoding="utf-8"))
        print("   cached fixture present: %s" % FIXTURE)
        print("   %d target-hour days, %d lead pools" % (len(d["dir_by_date"]), len(d["errors"])))
        return 0

    obs, failed = {}, []
    n = 0
    for y in YEARS:
        for (m1, d1, m2, d2) in SPANS:
            n += 1
            raw = fetch_chunk(y, m1, d1, m2, d2)
            if raw is None:
                failed.append("%d-%02d-%02d" % (y, m1, d1))
                continue
            kept = parse_into(raw, obs)
            print("   [%2d/%2d] %d-%02d-%02d..%02d-%02d  %6d rows  (running hours: %d)"
                  % (n, len(YEARS) * len(SPANS), y, m1, d1, m2, d2, kept, len(obs)))

    if not obs:
        print("\n   NOTHING FETCHED. Not writing a fixture; an empty one would poison later steps.")
        return 2

    # average duplicate reports inside an hour; keep direction and speed together
    agg = {}
    for k, v in obs.items():
        agg[k] = (statistics.fmean(x[0] for x in v), statistics.fmean(x[1] for x in v))

    # target-hour direction, calm excluded
    dir_by_date, spd_by_date = {}, {}
    for (date, hh), (dd, ss) in agg.items():
        if hh != TARGET_HOUR or ss < MIN_KT:
            continue
        dir_by_date[date] = dd
        spd_by_date[date] = ss

    errors = {}
    for lead in LEADS:
        h0 = TARGET_HOUR - lead
        if h0 < 0:
            continue
        e = []
        for date, tgt in dir_by_date.items():
            prev = agg.get((date, h0))
            if prev is None or prev[1] < MIN_KT:
                continue
            e.append(angdiff(tgt, prev[0]))
        if len(e) >= 15:
            errors[lead] = e

    if not dir_by_date or not errors:
        print("\n   Rows fetched but pools empty. Not writing a fixture.")
        return 2

    # 5-degree histogram of the target-hour direction, matching N-23's sweep resolution
    hist = [0] * 72
    for dd in dir_by_date.values():
        hist[int(dd // 5) % 72] += 1

    meta = {
        "station": "KIAD",
        "target_hour_site": TARGET_HOUR,
        "tz_requested_from_server": "America/New_York",
        "years": YEARS,
        "min_kt": MIN_KT,
        "calm_excluded_because": "ASOS reports drct=0 when calm, which is not a direction",
        "n_hours": len(agg),
        "n_target_days": len(dir_by_date),
        "quantity": "site-local %02d:00 wind direction and speed, plus PERSISTENCE direction error "
                    "per lead" % TARGET_HOUR,
        "why_lower_bound": "persistence is the honest lower bound on forecast skill",
        "hist_bin_deg": 5,
        "failed_chunks": failed,
        "source": "NOAA ASOS via Iowa State Environmental Mesonet (free, no key)",
    }

    json.dump({"dir_by_date": dir_by_date, "spd_by_date": spd_by_date,
               "dir_hist_5deg": hist,
               "errors": {str(k): v for k, v in errors.items()},
               "meta": meta}, open(FIXTURE, "w"), indent=1)

    print("\n   target-hour days with wind >= %.1f kt: %d" % (MIN_KT, len(dir_by_date)))
    print("   wind speed at target hour: median %.1f kt   max %.1f kt"
          % (statistics.median(spd_by_date.values()), max(spd_by_date.values())))
    print("\n   direction persistence error sd by lead (deg):")
    for lead in sorted(errors):
        v = errors[lead]
        print("      lead %2d h   n=%4d   sd %6.2f   MAE %6.2f"
              % (lead, len(v), statistics.stdev(v), statistics.fmean(abs(x) for x in v)))

    print("\n   direction frequency, 30-deg sectors (share of target-hour days):")
    for s in range(12):
        c = sum(hist[s * 6:(s + 1) * 6])
        bar = "#" * int(round(60.0 * c / max(1, len(dir_by_date))))
        print("      %3d-%3d deg  %5.1f %%  %s" % (s * 30, s * 30 + 30,
                                                   100.0 * c / len(dir_by_date), bar))
    if failed:
        print("\n   WARNING: %d chunk(s) missing from the pools: %s" % (len(failed), ", ".join(failed)))
    print("\n   written: %s" % FIXTURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
