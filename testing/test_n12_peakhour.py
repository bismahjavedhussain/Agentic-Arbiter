# -*- coding: utf-8 -*-
"""N-12  ---  is the daily PEAK HOUR uncertain, or effectively deterministic?   PAID.

WHY THIS IS THE MOST IMPORTANT TEST IN THE PROJECT RIGHT NOW

N-9 is the entire "this is genuinely an agent, not a threshold" argument. It works because
waiting is RISKY: you do not know which hour the peak will land on, so deferring may leave the
extra cooling arriving after the event. That risk is parameterised by peak_sd_h.

peak_sd_h was a pure [S] stub set to 1.5 h. And N-9's own sweep shows how load-bearing it is:

        peak-hour sd 0.5 h   ->  gain +0.005  (0.2 sigma)  -- a TIE
        peak-hour sd 1.0 h   ->  gain +0.147  (5.7 sigma)
        peak-hour sd 1.5 h   ->  gain +0.356  (11.2 sigma)
        peak-hour sd 2.5 h   ->  gain +0.499  (10.9 sigma)

So if the real peak hour is repeatable to within about half an hour, the stopping rule buys
nothing and we must stop calling this agentic. If it moves by an hour or more between days, N-9
stands on measured ground instead of a guess.

A saved fixture already hints at trouble: analytic_type=time_of_measure over 01:00-23:00 on
2026-07-28 returned 14.0 for ALL 43 tiles, sd = 0.000. That is zero SPATIAL variation. But the
quantity N-9 needs is DAY-TO-DAY variation, which that single call cannot show. Hence this test.

WHAT IS MEASURED
    time_of_measure over the same AOI on N separate historical summer days.
      - between-day sd of the area-modal peak hour   -> peak_sd_h, measured
      - within-day spatial sd                        -> is the field degenerate?
      - a degeneracy check: if every day returns the identical hour, treat the endpoint as
        suspect (persistence was already found to be byte-identical to exceedance) rather than
        concluding the atmosphere is deterministic.

Credits are read before and after. The audited key's cycle closed 19 July and reads
active: false, so the meter may not move; that is reported, not assumed.
"""
import json, statistics, sys
from collections import Counter

from common import (load_key, credits_remaining, submit_poll, banner, save_result, verdict,
                    box_aoi)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 2.0
GRAN = 100
DAYS = ["2026-06-15", "2026-06-30", "2026-07-10", "2026-07-20", "2026-07-28"]
WIN = ("01:00", "23:00")


def peak_hours(key, day, aoi):
    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "time_of_measure",
               "date_time": {"start_date": day, "start_time": WIN[0], "end_time": WIN[1],
                             "filter_type": 2}}
    r = submit_poll(key, "heatmap", payload, "n12_tom_%s" % day)
    if not r.get("ok"):
        return None, r.get("error")
    feats = (r["result"].get("map_data") or {}).get("features") or []
    if not feats:
        return None, "ZERO TILES with completed status"
    vals = [f["properties"].get("value") for f in feats]
    vals = [v for v in vals if v is not None]
    return vals, None


def main():
    banner("N-12  Is the daily peak hour uncertain?  Decides whether N-9 survives.   [PAID]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    print("   AOI %.1f x %.1f km at %.4f, %.4f   granularity %d m   window %s-%s"
          % (SIDE_KM, SIDE_KM, CENTRE[0], CENTRE[1], GRAN, WIN[0], WIN[1]))
    print("   %d historical days: %s" % (len(DAYS), ", ".join(DAYS)))

    per_day, errors = {}, {}
    for i, d in enumerate(DAYS, 1):
        print("\n   CALL %d/%d  %s ..." % (i, len(DAYS), d))
        vals, err = peak_hours(key, d, aoi)
        if err:
            errors[d] = err
            print("      FAILED: %s" % err)
            continue
        c = Counter(vals)
        modal = c.most_common(1)[0][0]
        sd_sp = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        per_day[d] = {"n": len(vals), "modal": modal, "mean": statistics.fmean(vals),
                      "min": min(vals), "max": max(vals), "spatial_sd": sd_sp,
                      "hist": dict(sorted(c.items()))}
        print("      %d tiles   modal hour %.0f   mean %.2f   range %.0f-%.0f   spatial sd %.3f"
              % (len(vals), modal, per_day[d]["mean"], min(vals), max(vals), sd_sp))

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER : %s    APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))
    if before == after:
        print("   NOTE meter did not move. Consistent with the closed billing cycle already")
        print("        documented (active: false). Price per call remains UNMEASURED.")

    if len(per_day) < 2:
        print("\n   fewer than 2 days returned data -- cannot measure between-day variation.")
        save_result("n12_peakhour.json", {"per_day": per_day, "errors": errors,
                                          "before": before, "after": after, "pass": None})
        return 2

    # ---------------- the number that matters ------------------------------
    modals = [v["modal"] for v in per_day.values()]
    means = [v["mean"] for v in per_day.values()]
    between_sd = statistics.pstdev(modals) if len(modals) > 1 else 0.0
    between_sd_mean = statistics.pstdev(means) if len(means) > 1 else 0.0
    spatial_sds = [v["spatial_sd"] for v in per_day.values()]

    print("\n   RESULT")
    print("      %-12s %8s %8s %10s" % ("day", "modal", "mean", "spatial sd"))
    for d, v in per_day.items():
        print("      %-12s %8.0f %8.2f %10.3f" % (d, v["modal"], v["mean"], v["spatial_sd"]))
    print("      ------------------------------------------------")
    print("      BETWEEN-DAY sd of modal peak hour : %.3f h   <-- this is peak_sd_h" % between_sd)
    print("      BETWEEN-DAY sd of area-mean hour  : %.3f h" % between_sd_mean)
    print("      within-day spatial sd, max across days: %.3f h" % max(spatial_sds))
    print("      distinct modal hours observed     : %s" % sorted(set(modals)))

    # ---------------- degeneracy check ------------------------------------
    all_identical = len(set(modals)) == 1 and max(spatial_sds) == 0.0
    print("\n   DEGENERACY CHECK")
    if all_identical:
        print("      Every tile on every day returned the SAME hour, sd 0.000 everywhere.")
        print("      Do NOT read that as 'the atmosphere is deterministic'. The persistence")
        print("      analytic was already found byte-identical to exceedance, so a constant")
        print("      field is at least as likely to be an endpoint defect. Treat as SUSPECT")
        print("      and source peak-hour spread elsewhere (METAR hourly, or the heatmap's")
        print("      own hourly tcm series).")
    else:
        print("      Values vary across days and/or tiles -- the analytic is responsive.")

    # ---------------- verdict, thresholds fixed in advance -----------------
    usable = max(between_sd, between_sd_mean)
    ok = usable >= 1.0
    marginal = 0.5 <= usable < 1.0
    print("\n   WHAT THIS DOES TO N-9  (thresholds set before the call, from N-9's own sweep)")
    print("      sd >= 1.0 h  -> N-9 stands on measured ground (gain was +0.147 at 1.0 h)")
    print("      0.5-1.0 h    -> MARGINAL, gain shrinks toward a tie")
    print("      < 0.5 h      -> N-9's agency claim COLLAPSES; stop calling it agentic")
    print("      measured: %.3f h  -> %s"
          % (usable, "STANDS" if ok else ("MARGINAL" if marginal else "COLLAPSES")))

    print()
    verdict(ok,
            "PASS - peak hour moves %.2f h between days, so waiting carries genuine risk and "
            "N-9's stopping problem is real rather than an artifact of a stub." % usable,
            "FAIL - peak hour is repeatable to %.2f h. Either the endpoint is degenerate or the "
            "peak really is that predictable; either way N-9 cannot be claimed on this evidence "
            "and peak-hour spread must be measured from an independent source." % usable)

    save_result("n12_peakhour.json", {
        "aoi": {"centre": CENTRE, "side_km": SIDE_KM, "granularity": GRAN, "window": WIN},
        "days": DAYS, "per_day": per_day, "errors": errors,
        "between_day_sd_modal": between_sd, "between_day_sd_mean": between_sd_mean,
        "max_within_day_spatial_sd": max(spatial_sds),
        "distinct_modal_hours": sorted(set(modals)),
        "all_identical_suspect": all_identical,
        "peak_sd_h_measured": usable,
        "n9_verdict": "stands" if ok else ("marginal" if marginal else "collapses"),
        "before": before, "after": after, "apparent_spend": before - after,
        "meter_moved": before != after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
