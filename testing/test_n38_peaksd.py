# -*- coding: utf-8 -*-
"""N-38  ---  peak_sd_h on 15 days instead of 5.   PAID, 40 calls.

WHAT THIS NUMBER IS AND WHY IT MATTERS
    peak_sd_h is the spread, across days, of WHICH HOUR the daily maximum temperature lands on. It is
    one of exactly two quantities the agentic claim rests on:

        N-24 pre-registered:  peak_sd_h > 0.70 h  for a 2-sigma win over the best tuned fixed-hour
                              rule; break-even at 0.395 h.

    Why it matters at all: if the peak hour were perfectly predictable, waiting until the last useful
    moment would be optimal by construction and the backward induction would earn nothing. That is
    exactly how N-9 v1 failed. The uncertainty in WHEN is what makes the decision a real decision.

    The previous estimate was 1.49 h from FIVE days -- and dropping one of those five collapsed it to
    0.000 h. A number that fragile cannot carry the claim, which is why this test exists.

WHY IT IS MEASURED THIS AWKWARD WAY
    The endpoint has an analytic that should answer this directly -- analytic_type: time_of_measure --
    and it is broken (findings section 1.2: it nominated hour 22 on a day when tcm puts the maximum
    unambiguously in the afternoon, and returned 0/1/2 on three other days). So the peak hour has to
    be recovered indirectly, by requesting a series of narrow tcm windows and comparing their maxima.
    That is 4 calls per day instead of 1.

DESIGN, and the budget that shaped it
    4 windows per day: 12-14, 14-16, 16-18, 18-20 site-local. Across the five days already held, every
    observed peak fell at 12:00 or 16:00, so 12:00-20:00 brackets them with room either side.
    10 new days x 4 windows = 40 calls = 168,800 credits against 180,980 showing on the key.
    The five existing days are recomputed on the SAME four windows so all 15 use one estimator.

⚠ THE LIMITATION THIS METHOD CANNOT ESCAPE
    2-hour windows locate the peak to +/-1 h, so peak_sd_h comes out QUANTISED. The estimate is coarse
    by construction, and no number of days fixes that -- only a working time_of_measure would. Reported
    with that stated, not smoothed over.

PRE-REGISTERED -- inherited from N-24, not chosen now
    P1  peak_sd_h > 0.70 h on the 15-day sample (the 2-sigma threshold)
    P2  removing any single day must leave it above the 0.395 h break-even -- i.e. the estimate must
        no longer be hostage to one day, which was the whole complaint about the 5-day version
    P3  at least 13 days return usable data
"""
import sys, os, json, statistics
import numpy as np

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, FIXTURES)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 2.0
GRAN = 100
WINDOWS = [("12:00", "14:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")]
CENTRES = {"12:00": 13.0, "14:00": 15.0, "16:00": 17.0, "18:00": 19.0}

HELD_DAYS = ["2026-06-15", "2026-06-30", "2026-07-10", "2026-07-20", "2026-07-28"]
NEW_DAYS = ["2026-07-01", "2026-07-05", "2026-07-14", "2026-07-24", "2026-08-01",
            "2026-08-03", "2026-08-05", "2026-08-07", "2026-08-09", "2026-08-11"]

P1_MIN = 0.70
P2_MIN = 0.395
P3_MIN_DAYS = 13
CREDIT_ABORT = 20000          # abort if the meter drops by more than this


def window_mean(key, aoi, day, s, e, tag):
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {"start_date": day, "start_time": s, "end_time": e, "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, tag)
    if not r.get("ok"):
        return None, r.get("error")
    f = (r["result"].get("map_data") or {}).get("features") or []
    v = [t["properties"].get("max_temperature") for t in f]
    v = [x for x in v if x is not None]
    if not v:
        return None, "ZERO TILES"
    return statistics.fmean(v), None


def held_window_mean(day, s):
    """Reuse the N-12c fixture for a held day and window start."""
    p = os.path.join(FIXTURES, "n12c_%s_%s.json" % (day, s.replace(":", "")))
    if not os.path.exists(p):
        return None
    f = (json.load(open(p)).get("map_data") or {}).get("features") or []
    v = [t["properties"].get("max_temperature") for t in f]
    v = [x for x in v if x is not None]
    return statistics.fmean(v) if v else None


def main():
    banner("N-38  peak_sd_h on 15 days instead of 5   [PAID, up to 40 calls]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    print("   4 windows/day: %s" % ", ".join("%s-%s" % w for w in WINDOWS))
    print("   %d held days recomputed on the same windows + %d new days = %d total"
          % (len(HELD_DAYS), len(NEW_DAYS), len(HELD_DAYS) + len(NEW_DAYS)))
    print("   time_of_measure would answer this in 1 call/day; it is broken (findings 1.2)")

    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    days, errors, calls = {}, {}, 0

    print("\n   HELD DAYS (from saved fixtures, no calls)")
    for day in HELD_DAYS:
        means = {}
        for s, e in WINDOWS:
            m = held_window_mean(day, s)
            if m is not None:
                means[s] = m
        if len(means) < 3:
            errors[day] = "only %d held windows" % len(means); continue
        pk = max(means, key=lambda s: means[s])
        days[day] = {"means": means, "peak_window": pk, "peak_h": CENTRES[pk], "source": "held"}
        print("      %s  %s  -> peak %s (centre %.1f h)"
              % (day, " ".join("%.2f" % means[s] for s in sorted(means)), pk, CENTRES[pk]))

    print("\n   NEW DAYS (4 calls each)")
    for day in NEW_DAYS:
        means = {}
        for s, e in WINDOWS:
            tag = "n38_%s_%s" % (day, s.replace(":", ""))
            fx = os.path.join(FIXTURES, "%s.json" % tag)
            if os.path.exists(fx):
                f = (json.load(open(fx)).get("map_data") or {}).get("features") or []
                v = [t["properties"].get("max_temperature") for t in f if
                     t["properties"].get("max_temperature") is not None]
                if v:
                    means[s] = statistics.fmean(v)
                continue
            m, err = window_mean(key, aoi, day, s, e, tag)
            calls += 1
            if m is None:
                errors["%s %s" % (day, s)] = err
            else:
                means[s] = m
        now = credits_remaining(key)
        if before - now > CREDIT_ABORT:
            print("      *** meter dropped %s credits -- ABORTING to protect the key"
                  % format(before - now, ","))
            break
        if len(means) < 3:
            errors[day] = "only %d windows returned" % len(means); continue
        pk = max(means, key=lambda s: means[s])
        days[day] = {"means": means, "peak_window": pk, "peak_h": CENTRES[pk], "source": "new"}
        print("      %s  %s  -> peak %s (centre %.1f h)"
              % (day, " ".join("%.2f" % means[s] for s in sorted(means)), pk, CENTRES[pk]))

    after = credits_remaining(key)
    print("\n   %d calls made.  cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (calls, format(after, ","), format(before - after, ",")))

    if len(days) < 3:
        print("\n   too few days to compute a spread.")
        save_result("n38_peaksd.json", {"days": {k: v["peak_h"] for k, v in days.items()},
                                        "errors": errors, "pass": None})
        return 2

    peaks = np.array([v["peak_h"] for v in days.values()])
    sd = float(peaks.std(ddof=1))
    print("\n   RESULT over %d days" % len(days))
    from collections import Counter
    print("      peak-hour histogram: %s"
          % ", ".join("%.0f h x%d" % (h, n) for h, n in sorted(Counter(peaks).items())))
    print("      mean peak hour %.2f h   peak_sd_h = %.3f h" % (peaks.mean(), sd))
    print("      previous 5-day estimate: 1.49 h")

    # P2: leave-one-out robustness -- the exact complaint about the 5-day version
    loo = []
    for i in range(len(peaks)):
        rest = np.delete(peaks, i)
        loo.append(float(rest.std(ddof=1)))
    print("\n      LEAVE-ONE-OUT (the 5-day version collapsed to 0.000 when one day was dropped)")
    print("      min %.3f   max %.3f   -> %s"
          % (min(loo), max(loo),
             "robust: no single day can collapse it" if min(loo) > P2_MIN
             else "STILL FRAGILE: dropping one day takes it below %.3f" % P2_MIN))

    p1 = sd > P1_MIN
    p2 = min(loo) > P2_MIN
    p3 = len(days) >= P3_MIN_DAYS
    ok = p1 and p2 and p3
    print("\n   VERDICT AGAINST N-24'S PRE-REGISTERED THRESHOLDS")
    print("      P1 peak_sd_h > %.2f h              : %s  (%.3f)" % (P1_MIN, p1, sd))
    print("      P2 leave-one-out stays > %.3f h    : %s  (min %.3f)" % (P2_MIN, p2, min(loo)))
    print("      P3 >= %d usable days               : %s  (%d)" % (P3_MIN_DAYS, p3, len(days)))
    # NOTE: plain ASCII only in print(). The Windows console is cp1252 and a warning glyph here
    # crashed this test AFTER all 40 paid calls had completed but BEFORE save_result ran, so the
    # result was lost and had to be recovered from cached fixtures. Third time this has bitten.
    print("\n   NOTE: 2-hour windows locate the peak to +/-1 h, so this estimate is QUANTISED and")
    print("   coarse by construction. Only a working time_of_measure would fix that.")
    print()
    verdict(ok,
            "PASS - peak_sd_h = %.3f h on %d days, clearing the 0.70 h that N-24 pre-registered, and "
            "leave-one-out never drops below %.3f h. The complaint about the 5-day version -- that one "
            "day could collapse it to zero -- no longer applies. The agentic claim's second pillar is "
            "now on 15 days instead of 5." % (sd, len(days), min(loo)),
            "FAIL - peak_sd_h = %.3f h on %d days (P1 %s, P2 %s, P3 %s). If it is below 0.70 h the "
            "stopping rule's margin over a tuned fixed-hour rule shrinks; if leave-one-out drops below "
            "0.395 h it is still hostage to a single day. Re-run N-24 at the measured value and quote "
            "whatever that yields." % (sd, len(days), p1, p2, p3))

    save_result("n38_peaksd.json", {
        "why_awkward": "time_of_measure is broken (findings 1.2), so the peak hour is recovered from "
                       "4 narrow tcm windows per day",
        "windows": WINDOWS, "window_centres": CENTRES,
        "aoi": {"centre": list(CENTRE), "side_km": SIDE_KM, "granularity": GRAN},
        "days": {k: {"peak_h": v["peak_h"], "peak_window": v["peak_window"],
                     "source": v["source"], "means": v["means"]} for k, v in days.items()},
        "n_days": len(days), "peak_sd_h": sd, "mean_peak_h": float(peaks.mean()),
        "previous_5day_estimate": 1.49,
        "leave_one_out_sd": loo, "loo_min": min(loo), "loo_max": max(loo),
        "quantisation_note": "2-hour windows locate the peak to +/-1 h; the estimate is coarse by "
                             "construction and only a working time_of_measure would fix it",
        "thresholds": {"p1_min": P1_MIN, "p2_min": P2_MIN, "p3_min_days": P3_MIN_DAYS},
        "p1": p1, "p2": p2, "p3": p3, "errors": errors,
        "calls": calls, "credits_before": before, "credits_after": after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
