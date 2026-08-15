# -*- coding: utf-8 -*-
"""N-45 step 1 of 3  ---  fetch REAL ambient temperature history for KIAD. FREE, no API key.

WHY THIS EXISTS
    test_n44_adaptive_commit.py held ambient FROZEN at AMB = 30.0 C on every simulated day, so the
    realised outcome was the recirculation rise alone (0 to ~0.4 C) and the breach threshold was a
    p75 quantile of the model's own output (0.00978 C). That removed the weather -- the dominant
    driver of whether an intake actually overheats -- from the decision problem. N-45 puts it back.

WHAT IT COLLECTS, and why each choice matches existing work rather than inventing a new convention
    * Station KIAD (Washington Dulles), the same station test_n40_windsharpen.py used, so ambient
      and wind-direction errors share one clock and one location.
    * Target hour = 16:00 SITE-LOCAL, again matching N-40, so lead L means the same thing in both
      error pools. tz=America/New_York is requested from the server so no local-clock arithmetic is
      ever done here -- GOTCHA #1 in HANDOFF.md (the 9-hour timezone bug) came from exactly that.
    * Six summers, 2021-2026, June 1 to Sept 1. Multiple summers because a single one gives too few
      genuinely hot days to characterise the upper tail, which is the only part that matters when
      the threshold is an ASHRAE allowable limit.
    * Persistence error of ambient per lead: err(L) = T(16:00) - T(16:00 - L). Persistence is the
      honest LOWER bound on forecast skill -- any real forecast beats it -- so every number derived
      from this understates how well the agent would really do. Same framing N-40 used.

CACHING
    Writes results/fixtures/n45_kiad_temps.json and reuses it if present, so the network is touched
    once. Chunks are saved incrementally: a 503 partway through loses one chunk, not the run
    (HANDOFF GOTCHA #13 -- Iowa State rate-limits and 503s on large requests).
"""
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request

from common import banner, FIXTURES      # importing common also forces UTF-8 stdout (GOTCHA #5)

FIXTURE = os.path.join(FIXTURES, "n45_kiad_temps.json")
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "IAD"
TARGET_HOUR = 16                 # site-local, matches test_n40_windsharpen.fetch_direction_errors
LEADS = list(range(1, 13))       # 1..12 h, matching the confirmed 12 h FortyGuard horizon
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
# ~3-week chunks inside each summer (GOTCHA #13: fetch small, save often)
SPANS = [(6, 1, 6, 21), (6, 21, 7, 11), (7, 11, 8, 1), (8, 1, 8, 21), (8, 21, 9, 1)]
RETRIES = 4
BACKOFF_S = 6


def fetch_chunk(y, m1, d1, m2, d2):
    """One request. Returns raw CSV text, or None after RETRIES failures."""
    parts = [("station", STATION), ("data", "tmpc"),
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
                print("      FAILED %d-%02d-%02d..%02d-%02d after %d attempts: %s"
                      % (y, m1, d1, m2, d2, RETRIES, e))
                return None
            time.sleep(BACKOFF_S)
    return None


def parse_into(raw, obs):
    """Accumulate {(date, hour): [temps]}. Parses EVERY field before touching obs, because
    setdefault() creates the key first -- inlining float() leaves an empty list behind whenever
    ASOS reports 'M' for missing, which then explodes fmean(). HANDOFF GOTCHA #10."""
    kept = 0
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 3:
            continue
        try:
            date, tm = p[1].split(" ")
            hh = int(tm.split(":")[0])
            tmpc = float(p[2])
        except Exception:
            continue
        if tmpc < -60.0 or tmpc > 60.0:          # guard against a bad decode, not a real reading
            continue
        obs.setdefault((date, hh), []).append(tmpc)
        kept += 1
    return kept


def main():
    banner("N-45 step 1  ambient temperature history, KIAD, 2021-2026 summers   [FREE, no key]")

    if os.path.exists(FIXTURE):
        d = json.load(open(FIXTURE, encoding="utf-8"))
        print("   cached fixture already present: %s" % FIXTURE)
        print("   %d target days, %d lead pools" % (len(d["target_by_date"]), len(d["errors"])))
        print("   nothing fetched. Delete the fixture to force a refetch.")
        return 0

    obs, failed = {}, []
    total_chunks = len(YEARS) * len(SPANS)
    n = 0
    for y in YEARS:
        for (m1, d1, m2, d2) in SPANS:
            n += 1
            raw = fetch_chunk(y, m1, d1, m2, d2)
            if raw is None:
                failed.append("%d-%02d-%02d" % (y, m1, d1))
                continue
            kept = parse_into(raw, obs)
            print("   [%2d/%2d] %d-%02d-%02d..%02d-%02d  %6d rows kept  (running hours: %d)"
                  % (n, total_chunks, y, m1, d1, m2, d2, kept, len(obs)))

    if not obs:
        print("\n   NOTHING FETCHED. Not writing a fixture -- an empty one would silently poison")
        print("   every later step. Re-run when the network or the Iowa State service recovers.")
        return 2

    # average duplicate reports within an hour (ASOS specials), same as N-40 did
    agg = {k: statistics.fmean(v) for k, v in obs.items()}
    dates = sorted({k[0] for k in agg})

    target_by_date = {d: agg[(d, TARGET_HOUR)] for d in dates if (d, TARGET_HOUR) in agg}

    errors = {}
    for lead in LEADS:
        h0 = TARGET_HOUR - lead
        if h0 < 0:
            continue
        e = []
        for d, tgt in target_by_date.items():
            prev = agg.get((d, h0))
            if prev is None:
                continue
            e.append(tgt - prev)                 # signed, in C: target minus what persistence said
        if len(e) >= 15:
            errors[lead] = e

    if not target_by_date or not errors:
        print("\n   Fetched rows but could not build target/error pools. Not writing a fixture.")
        return 2

    tvals = sorted(target_by_date.values())
    meta = {
        "station": "KIAD",
        "target_hour_site": TARGET_HOUR,
        "tz_requested_from_server": "America/New_York",
        "years": YEARS,
        "span": "June 1 - Sept 1, each year listed",
        "n_hours": len(agg),
        "n_days_any_hour": len(dates),
        "n_target_days": len(target_by_date),
        "quantity": "site-local %02d:00 dry-bulb air temperature, and its PERSISTENCE error per lead"
                    % TARGET_HOUR,
        "why_lower_bound": "persistence is the honest lower bound on forecast skill; any real "
                           "forecast beats it, so results derived from this understate performance",
        "target_min_c": tvals[0],
        "target_median_c": statistics.median(tvals),
        "target_p90_c": tvals[int(0.90 * (len(tvals) - 1))],
        "target_max_c": tvals[-1],
        "failed_chunks": failed,
        "source": "NOAA ASOS via Iowa State Environmental Mesonet (free, no key)",
    }

    json.dump({"target_by_date": target_by_date,
               "errors": {str(k): v for k, v in errors.items()},
               "meta": meta}, open(FIXTURE, "w"), indent=1)

    print("\n   target days (site-local %02d:00): %d" % (TARGET_HOUR, len(target_by_date)))
    print("   ambient at target hour:  min %.1f   median %.1f   p90 %.1f   max %.1f C"
          % (meta["target_min_c"], meta["target_median_c"], meta["target_p90_c"],
             meta["target_max_c"]))
    print("   persistence error sd by lead (C):")
    for lead in sorted(errors):
        v = errors[lead]
        print("      lead %2d h   n=%4d   sd %.3f   mean %+.3f"
              % (lead, len(v), statistics.stdev(v), statistics.fmean(v)))
    if failed:
        print("\n   WARNING: %d chunk(s) failed and are MISSING from the pools: %s"
              % (len(failed), ", ".join(failed)))
    print("\n   written: %s" % FIXTURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
