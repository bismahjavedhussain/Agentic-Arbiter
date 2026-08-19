# -*- coding: utf-8 -*-
"""N-47  ---  GATE: does FortyGuard's `persistence` analytic support a duration decision?

Pre-registered in n47-persistence-PREREG.md. Conditions P1-P4 were fixed before these calls.
[PAID: exactly 2 /v1/heatmap calls, user-authorised 2026-08-16.]

THE TWO UNKNOWNS THIS BUYS, and why everything else was established for free first
    Free from fixtures already on disk: `persistence` returns HOURS and is a different quantity from
    `exceedance` (n17_r2_persistence 7.031-10.374 h with 80 distinct values, vs n17_r2_exceedance
    143.249-169.991). Defect D3's "they are identical" was our own bug -- both returned the whole
    window because no threshold was applied.

    Still unknown, and what these calls resolve:
      1. Does `threshold` -- spelled as the spec defines it -- change the result AT ALL? Both prior
         tests sent `threshold_temperature`, which probe 2 proved the API silently ignores.
      2. What are the units? Total hours in the window, hours per day, or longest contiguous run?
         A 10-hour window bounds the answer: hours-within-window must be <= 10.0.

WINDOW CHOICE IS EVIDENCE-BASED, NOT ARBITRARY
    2026-06-23 was rejected after inspecting the saved field: max 20.52 C across the whole AOI, so any
    threshold near 30 C returns zeros and wastes both calls. 2026-07-28 spans 29.98-32.43 C
    (median 31.15), so thresholds of 31.0 and 32.0 straddle the distribution.

SAFETY / DISCIPLINE
    * Key via common.load_key(), never printed. Raw responses saved as fixtures.
    * Window built with common.site_window() from a timezone-aware site-local datetime -- never from
      a naive clock (HANDOFF GOTCHA #1, the 9-hour bug).
    * assert_non_empty on both responses: an out-of-range request returns status=completed with ZERO
      tiles, indistinguishable from an empty area (GOTCHA #2).
"""
import json
import os
import statistics
import sys
from datetime import datetime

from common import (banner, box_aoi, credits_remaining, load_key, save_result, site_tz,
                    site_window, submit_poll, verdict, FIXTURES)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
DAY = (2026, 7, 28)
START_HOUR_SITE = 10
WIN_H = 10                       # 10:00-20:00 site-local; bounds hours-within-window at 10.0
THRESHOLDS = [31.0, 32.0]        # straddle the measured 29.98-32.43 C field for this day
DIRECTION = "above"

# pre-registered conditions
P2_MAX_VALUE = float(WIN_H)
P3_MIN_SD_H = 0.25
P3_MIN_DISTINCT = 50


def tiles_of(result):
    out = {}
    for f in result.get("map_data", {}).get("features", []):
        c = f["geometry"]["coordinates"][0]
        key = (round(sum(x[1] for x in c[:4]) / 4, 6), round(sum(x[0] for x in c[:4]) / 4, 6))
        v = f["properties"].get("value")
        if isinstance(v, (int, float)):
            out[key] = float(v)
    return out


def summarise(name, vals):
    v = sorted(vals)
    n = len(v)
    return {"name": name, "n": n, "min": v[0], "p10": v[int(0.10 * (n - 1))],
            "median": statistics.median(v), "p90": v[int(0.90 * (n - 1))], "max": v[-1],
            "mean": statistics.fmean(v), "sd": statistics.stdev(v) if n > 1 else 0.0,
            "distinct": len(set(v)),
            "frac_at_ceiling": sum(1 for x in v if x >= P2_MAX_VALUE - 1e-9) / n,
            "frac_zero": sum(1 for x in v if x <= 1e-9) / n}


def main():
    banner("N-47  GATE: does `persistence` support a duration decision?   [PAID: 2 calls]")
    print("   Pre-registered in n47-persistence-PREREG.md. P1 threshold works / P2 units / P3 spatial")
    print("   variation. If P1 fails the sixth core dies for 2 calls instead of a day.")

    key = load_key()
    try:
        before = credits_remaining(key)
        print("\n   cycle_remaining BEFORE: %s  (frozen since 2026-07-19; spend unobservable)"
              % format(before, ","))
    except Exception as e:
        before = None
        print("\n   credits before unavailable: %s" % str(e)[:100])

    start_site = datetime(DAY[0], DAY[1], DAY[2], START_HOUR_SITE, 0, tzinfo=site_tz())
    w = site_window(start_site, WIN_H)
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    print("   window %s %s-%s SITE-LOCAL (%d h), AOI %.0f x %.0f km at granularity %d m"
          % (w["start_date"], w["start_time"], w["end_time"], WIN_H, SIDE_KM, SIDE_KM, GRAN))

    fields, meta = {}, {}
    for thr in THRESHOLDS:
        tag = "n47_persist_thr%.0f" % thr
        payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "persistence",
                   "threshold": thr, "direction": DIRECTION,
                   "date_time": {"start_date": w["start_date"], "start_time": w["start_time"],
                                 "end_time": w["end_time"], "filter_type": 2}}
        print("\n   CALL  persistence, threshold=%.1f C, direction=%s" % (thr, DIRECTION))
        r = submit_poll(key, "heatmap", payload, tag)
        if not r.get("ok"):
            print("      FAILED: %s" % r.get("error"))
            meta[thr] = {"error": r.get("error")}
            continue
        t = tiles_of(r["result"])
        if not t:
            print("      ZERO usable tiles -- out-of-range requests return completed+empty (GOTCHA #2)")
            meta[thr] = {"error": "zero tiles"}
            continue
        fields[thr] = t
        s = summarise("thr%.1f" % thr, list(t.values()))
        meta[thr] = s
        print("      %d tiles in %.0f s" % (len(t), r.get("secs", 0)))
        print("      value: min %.3f  p10 %.3f  median %.3f  p90 %.3f  max %.3f   sd %.3f"
              % (s["min"], s["p10"], s["median"], s["p90"], s["max"], s["sd"]))
        print("      distinct values %d   at ceiling(%.0f) %.1f %%   exactly zero %.1f %%"
              % (s["distinct"], P2_MAX_VALUE, 100 * s["frac_at_ceiling"], 100 * s["frac_zero"]))

    # ---------------------------------------------------------------- verdicts
    lo, hi = THRESHOLDS[0], THRESHOLDS[1]
    have_both = lo in fields and hi in fields
    p1 = p2 = p3 = False
    identical = None
    med_lo = med_hi = None

    if have_both:
        common_keys = [k for k in fields[lo] if k in fields[hi]]
        identical = all(abs(fields[lo][k] - fields[hi][k]) < 1e-9 for k in common_keys)
        med_lo, med_hi = meta[lo]["median"], meta[hi]["median"]
        p1 = (med_lo > med_hi) and not identical
        allv = list(fields[lo].values()) + list(fields[hi].values())
        p2 = all(0.0 - 1e-9 <= v <= P2_MAX_VALUE + 1e-9 for v in allv)
        p3 = meta[lo]["sd"] > P3_MIN_SD_H and meta[lo]["distinct"] >= P3_MIN_DISTINCT

        print("\n   P1  threshold changes the result")
        print("       median @ %.1f = %.3f h   vs   median @ %.1f = %.3f h   (difference %+.3f h)"
              % (lo, med_lo, hi, med_hi, med_lo - med_hi))
        print("       tile-for-tile identical across the two thresholds: %s" % identical)
        print("       -> P1 %s" % p1)

        print("\n   P2  values lie in [0, %.1f], i.e. hours WITHIN the requested window" % P2_MAX_VALUE)
        print("       observed overall range: %.3f to %.3f  -> P2 %s"
              % (min(allv), max(allv), p2))
        if not p2:
            print("       units are NOT hours-within-window. Candidates: hours per DAY, or longest")
            print("       contiguous run. DO NOT build a decision on a misread unit.")

        print("\n   P3  decision-relevant spatial variation at the lower threshold")
        print("       sd %.3f h (need > %.2f)   distinct %d (need >= %d)  -> P3 %s"
              % (meta[lo]["sd"], P3_MIN_SD_H, meta[lo]["distinct"], P3_MIN_DISTINCT, p3))

    ok = have_both and p1 and p2 and p3
    print()
    verdict(ok,
            "GATE PASSED - `threshold` is honoured when spelled correctly (median %.3f h at %.1f C vs "
            "%.3f h at %.1f C), values are hours within the window, and the duration field varies "
            "across the cluster (sd %.3f h, %d distinct). This earns ONE pre-registered day to build "
            "the duration decision core. It does NOT by itself establish day-to-day behaviour, "
            "forecast skill on duration, or that an operator would act on it (P4)."
            % (med_lo or 0, lo, med_hi or 0, hi, meta.get(lo, {}).get("sd", 0),
               meta.get(lo, {}).get("distinct", 0)) if have_both else "GATE PASSED",
            "GATE FAILED - see the P1/P2/P3 lines above. If P1 failed, `threshold` is ignored even "
            "when spelled as the spec defines it, which is a MORE serious API defect than any of the "
            "fifteen already documented, and the sixth decision core is dead for the price of two "
            "calls. Per the agreed stopping rule, no seventh core is proposed: the project ships as "
            "an instrument with six documented negative results.")

    after = None
    try:
        after = credits_remaining(key)
        print("\n   cycle_remaining AFTER: %s" % format(after, ","))
    except Exception:
        pass

    save_result("n47_persistence.json", {
        "measures": "whether /v1/heatmap analytic_type=persistence honours a correctly-spelled "
                    "`threshold`, what its units are, and whether the duration field varies across "
                    "the cluster enough to support a decision",
        "does_not_measure": "day-to-day behaviour, forecast skill on duration, or operator "
                            "willingness to act (P4 in n47-persistence-PREREG.md)",
        "authorised": "user, 2026-08-16, exactly 2 paid calls",
        "window": {"date": w["start_date"], "start_time_site": w["start_time"],
                   "end_time_site": w["end_time"], "hours": WIN_H, "filter_type": 2,
                   "tz": "America/New_York"},
        "aoi": {"centre": CENTRE, "side_km": SIDE_KM, "granularity": GRAN},
        "thresholds": THRESHOLDS, "direction": DIRECTION,
        "field_reconnaissance": "2026-06-23 rejected: max 20.52 C. 2026-07-28 spans 29.98-32.43 C, "
                                "median 31.15, from saved fixtures at zero cost",
        "prior_art_note": "verify_api_defects.py:172 and test_n17_recheck.py:49 both sent the ignored "
                          "field name `threshold_temperature`; this is the first test to send "
                          "`threshold` as the spec defines it",
        "summaries": {str(k): v for k, v in meta.items()},
        "identical_across_thresholds": identical,
        "conditions": {"p2_max_value": P2_MAX_VALUE, "p3_min_sd_h": P3_MIN_SD_H,
                       "p3_min_distinct": P3_MIN_DISTINCT},
        "p1": bool(p1), "p2": bool(p2), "p3": bool(p3), "gate_passed": bool(ok),
        "credits_before": before, "credits_after": after,
        "credits_note": "meter frozen since 2026-07-19; a zero difference does not prove zero spend",
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
