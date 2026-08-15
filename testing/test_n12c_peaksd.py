# -*- coding: utf-8 -*-
"""N-12c  ---  measure peak_sd_h WITHOUT the broken time_of_measure analytic.   PAID.

WHY
    N-9's "this is genuinely an agent" claim depends on peak_sd_h, the between-day spread of
    the hour the daily maximum lands on. N-9's own sweep:

        peak_sd_h 0.5 h -> gain +0.005 (0.2 sigma)  TIE, agency claim dies
        peak_sd_h 1.0 h -> gain +0.147 (5.7 sigma)
        peak_sd_h 1.5 h -> gain +0.356 (11.2 sigma)

    N-12 tried to read this from analytic_type=time_of_measure and the endpoint FAILED
    validation: it returned modal peak hours of 0, 1, 2 and 22 for summer days in Virginia, and
    N-12b falsified it directly -- on 2026-07-28 the 12:00-16:00 window is 6.446 C hotter than
    20:00-23:00, so a claimed peak at hour 22 is wrong by about eight hours. The endpoint is
    unusable for this.

METHOD  (uses only tcm, which IS validated)
    For each day, request a series of 2-hour windows spanning the afternoon and read the
    per-tile maximum in each. The window holding the largest maximum contains the peak. Take
    that window's centre as the day's peak hour, then compute the between-day sd.

    Quantisation: a 2-hour bin adds about 0.58 h of uniform error in quadrature, so a true
    sd of 0.5 h reads as ~0.76 h and a true 1.5 h reads as ~1.60 h. That is coarse but it does
    separate the two cases that matter, and the correction is applied and reported.

    Known endpoint defect to avoid: start_time == end_time returns HTTP 500 (found in N-12b).
"""
import math, statistics, sys
from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 2.0
GRAN = 100
DAYS = ["2026-06-15", "2026-06-30", "2026-07-10", "2026-07-20", "2026-07-28"]
WINDOWS = [("10:00", "12:00"), ("12:00", "14:00"), ("14:00", "16:00"),
           ("16:00", "18:00"), ("18:00", "20:00")]
BIN_H = 2.0


def window_max(key, aoi, day, s, e):
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {"start_date": day, "start_time": s, "end_time": e, "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, "n12c_%s_%s" % (day, s.replace(":", "")))
    if not r.get("ok"):
        return None, r.get("error")
    f = (r["result"].get("map_data") or {}).get("features") or []
    if not f:
        return None, "ZERO TILES"
    v = [t["properties"].get("max_temperature") for t in f]
    v = [x for x in v if x is not None]
    return (statistics.fmean(v) if v else None), None


def main():
    banner("N-12c  peak_sd_h by window bisection on tcm (time_of_measure is unusable)  [PAID]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    print("   %d days x %d two-hour windows = %d calls" % (len(DAYS), len(WINDOWS),
                                                           len(DAYS) * len(WINDOWS)))

    per_day, errors, n = {}, {}, 0
    for day in DAYS:
        print("\n   %s" % day)
        vals = {}
        for s, e in WINDOWS:
            n += 1
            m, err = window_max(key, aoi, day, s, e)
            if err:
                errors["%s %s" % (day, s)] = err
                print("      %s-%s  FAILED: %s" % (s, e, err))
                continue
            vals[s] = m
            print("      %s-%s  mean per-tile max %.3f C" % (s, e, m))
        if len(vals) < 3:
            print("      too few windows returned; skipping this day")
            continue
        best = max(vals, key=lambda k: vals[k])
        centre = int(best.split(":")[0]) + BIN_H / 2.0
        spread = max(vals.values()) - min(vals.values())
        per_day[day] = {"by_window": vals, "peak_window_start": best,
                        "peak_hour_centre": centre, "within_day_spread_c": spread}
        print("      -> peak window %s, centre hour %.1f   (max-min across windows %.3f C)"
              % (best, centre, spread))

    after = credits_remaining(key)
    print("\n   %d calls issued.  cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (n, format(after, ","), format(before - after, ",")))

    if len(per_day) < 3:
        print("\n   fewer than 3 usable days -- cannot estimate between-day sd.")
        save_result("n12c_peaksd.json", {"per_day": per_day, "errors": errors, "pass": None})
        return 2

    centres = [v["peak_hour_centre"] for v in per_day.values()]
    raw_sd = statistics.pstdev(centres) if len(centres) > 1 else 0.0
    quant = BIN_H / math.sqrt(12.0)                     # uniform bin sd
    corrected = math.sqrt(max(raw_sd ** 2 - quant ** 2, 0.0))

    print("\n   RESULT")
    print("      %-12s %14s %8s" % ("day", "peak window", "centre"))
    for d, v in per_day.items():
        print("      %-12s %14s %8.1f" % (d, v["peak_window_start"], v["peak_hour_centre"]))
    print("      ------------------------------------------")
    print("      distinct peak windows           : %s" % sorted(set(centres)))
    print("      raw between-day sd              : %.3f h" % raw_sd)
    print("      quantisation sd of a %.0f h bin   : %.3f h" % (BIN_H, quant))
    print("      quantisation-corrected estimate  : %.3f h   <-- peak_sd_h, MEASURED" % corrected)

    ok = corrected >= 1.0
    marginal = 0.5 <= corrected < 1.0
    print("\n   WHAT THIS DOES TO N-9  (thresholds fixed in advance, from N-9's own sweep)")
    print("      >= 1.0 h  -> N-9 stands on measured ground")
    print("      0.5-1.0 h -> MARGINAL, the gain shrinks toward a tie")
    print("      <  0.5 h  -> N-9's agency claim collapses")
    print("      measured %.3f h -> %s"
          % (corrected, "STANDS" if ok else ("MARGINAL" if marginal else "COLLAPSES")))
    print("\n      CAVEAT the estimate is quantised to %.0f h bins over %d days. It separates the"
          % (BIN_H, len(per_day)))
    print("      cases that matter but it is not a precise number, and n=%d is small."
          % len(per_day))

    print()
    verdict(ok,
            "PASS - peak hour moves %.2f h between days (quantisation-corrected), measured from "
            "tcm rather than the broken time_of_measure analytic. N-9's stopping problem rests on "
            "a measurement." % corrected,
            "FAIL - peak hour is repeatable to %.2f h on this evidence. N-9's agency claim cannot "
            "be supported at this site; either re-run peak_sd_h at 1 h resolution over more days, "
            "or drop the peak-hour mechanism and rebuild the agency argument on fleet allocation."
            % corrected)

    save_result("n12c_peaksd.json", {
        "method": "window bisection on tcm; time_of_measure falsified in N-12b",
        "aoi": {"centre": CENTRE, "side_km": SIDE_KM, "granularity": GRAN},
        "days": DAYS, "windows": [list(w) for w in WINDOWS], "bin_h": BIN_H,
        "per_day": per_day, "errors": errors, "n_calls": n,
        "peak_hour_centres": centres, "raw_between_day_sd": raw_sd,
        "quantisation_sd": quant, "peak_sd_h_measured": corrected,
        "n9_verdict": "stands" if ok else ("marginal" if marginal else "collapses"),
        "before": before, "after": after, "meter_moved": before != after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
