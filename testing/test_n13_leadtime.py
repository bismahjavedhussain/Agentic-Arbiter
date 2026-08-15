# -*- coding: utf-8 -*-
"""N-13  ---  does the forecast SHARPEN as the target hour approaches?   PAID, two legs.

*** SUPERSEDED 2026-08-12 BY test_n25_sharpen.py. DO NOT RUN. DO NOT QUOTE ITS LEADS. ***

    Two independent faults, either of which alone invalidates the result:

    1. THE 9-HOUR TIMEZONE BUG. This file builds windows from datetime.now() -- machine local,
       UTC+5 -- and sends bare "%H:00" strings. The endpoint reads them in the AOI's local zone,
       UTC-4. Its recorded lead_centre_h of 2.0 and 4.0 were really 9.25 h and 11.25 h. The two
       windows that "failed beyond the horizon" were at 13.25 h and 17.25 h, i.e. genuinely outside
       the 12 h horizon -- which is how the bug was finally found. See common.py, the time section.

    2. THE TIME-OF-DAY CONFOUND, flagged in the note below and never fixed: every lead had a
       different target window, so lead time was confounded with diurnal predictability.

    N-25 fixes both: one target window forecast repeatedly as it approaches, all times built through
    common.site_window(), which raises on a naive datetime rather than guessing.

    Kept on disk unmodified as the audit trail of how the timezone bug was discovered.

WHY THIS IS ONE OF THE TWO TESTS THE AGENCY CLAIM RESTS ON

N-9's stopping rule earns its keep because waiting buys INFORMATION: the forecast for a given
hour is supposed to get sharper as that hour approaches, so deferring a commitment lets you act
on a tighter bound. That sharpening rate is sigma(lead), and N-9's sweep shows how load-bearing
it is:

    tightening exponent 1.00  ->  gain +0.373  (10.6 sigma)
    tightening exponent 0.50  ->  gain +0.356  (11.2 sigma)   <-- assumed value
    tightening exponent 0.00  ->  gain -0.204  (-5.1 sigma)   <-- LOSES

Exponent 0 means "the forecast never sharpens". If that is what the data does, there is no
information value in waiting and N-9's agency claim fails. Only ONE point of this curve has ever
been measured: the 12-hour anchor, |residual| q90 = 0.4950 C on peak temperature over 6,875
tiles. The SHAPE is currently an assumption.

WHY IT TAKES TWO LEGS AND CANNOT BE DONE IN ONE SITTING
    A forecast error needs a forecast and then the outcome. The API cannot issue a forecast
    dated in the past, so leg 1 records predictions now and leg 2 collects what actually
    happened once those hours have elapsed. That is a property of the calendar, not the code.

        leg1   issue forecasts for narrow windows across the next ~11 h, save a manifest
        leg2   run tomorrow: request the SAME windows (now historical) and diff them

USAGE
    python test_n13_leadtime.py leg1      # today
    python test_n13_leadtime.py leg2      # tomorrow, or any time after the windows elapse

KNOWN CONFOUND, STATED UP FRONT
    Each window has a different lead time AND a different time of day, so lead time is
    confounded with diurnal predictability -- a 03:00 forecast may simply be easier than a
    15:00 one. The clean fix is to re-issue the SAME target windows at a shorter lead, which
    leg1b does if run a few hours after leg1. Without leg1b, treat the slope as indicative.

DEFECTS CODED AROUND
    - beyond-horizon requests return status completed with ZERO tiles -> assert non-empty
    - start_time == end_time returns HTTP 500 (found in N-12b) -> windows are always >= 2 h
    - windows are never allowed to cross midnight: the endpoint takes a single start_date
"""
import json, os, statistics, sys, math
from datetime import datetime, timedelta

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, RESULTS, tile_key)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 2.0
GRAN = 100
WIN_H = 2                      # 2-hour windows: >= 2 h avoids the equal-time 500
OFFSETS = [1, 3, 5, 7, 9]      # window starts, hours from now -> lead centres 2,4,6,8,10
MANIFEST = os.path.join(RESULTS, "n13_manifest.json")


def field_max(result):
    f = (result.get("map_data") or {}).get("features") or []
    if not f:
        return None, None
    out = {}
    for t in f:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[tile_key(la, lo)] = v
    return out, len(f)


def call_window(key, aoi, date, s, e, tag):
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {"start_date": date, "start_time": s, "end_time": e, "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, tag)
    if not r.get("ok"):
        return None, r.get("error")
    d, n = field_max(r["result"])
    if not d:
        return None, "ZERO TILES with completed status (beyond horizon?)"
    return d, n


def leg1():
    banner("N-13 leg1  issue forecasts at several lead times, save a manifest   [PAID]")
    key = load_key()
    before = credits_remaining(key)
    now = datetime.now()
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    print("   issue time (local): %s" % now.strftime("%Y-%m-%d %H:%M"))

    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    windows = []
    for off in OFFSETS:
        st = (now + timedelta(hours=off)).replace(minute=0, second=0, microsecond=0)
        en = st + timedelta(hours=WIN_H)
        if en.date() != st.date():
            print("   skip offset +%dh: window would cross midnight (endpoint takes one date)"
                  % off)
            continue
        windows.append({"offset_h": off, "date": st.strftime("%Y-%m-%d"),
                        "start": st.strftime("%H:00"), "end": en.strftime("%H:00"),
                        "lead_centre_h": off + WIN_H / 2.0})

    if not windows:
        print("   no usable windows before midnight. Re-run leg1 earlier in the day.")
        return 2
    print("   %d windows:" % len(windows))
    for w in windows:
        print("      +%2dh  %s %s-%s   lead centre %.1f h"
              % (w["offset_h"], w["date"], w["start"], w["end"], w["lead_centre_h"]))

    saved, errors = [], {}
    for i, w in enumerate(windows, 1):
        tag = "n13_f_%s_%s" % (w["date"], w["start"].replace(":", ""))
        print("\n   CALL %d/%d  forecast %s %s-%s ..." % (i, len(windows), w["date"],
                                                          w["start"], w["end"]))
        d, n = call_window(key, aoi, w["date"], w["start"], w["end"], tag)
        if d is None:
            errors[tag] = n
            print("      FAILED: %s" % n)
            continue
        print("      %d tiles   mean per-tile max %.3f C" % (n, statistics.fmean(d.values())))
        w["tag"] = tag
        w["n_tiles"] = n
        w["mean_max"] = statistics.fmean(d.values())
        saved.append(w)

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))

    os.makedirs(RESULTS, exist_ok=True)
    json.dump({"issued_at": now.isoformat(), "centre": CENTRE, "side_km": SIDE_KM,
               "granularity": GRAN, "win_h": WIN_H, "windows": saved, "errors": errors,
               "before": before, "after": after},
              open(MANIFEST, "w"), indent=1)
    print("\n   manifest written: %s" % MANIFEST)
    print("   %d forecast windows recorded. RUN leg2 AFTER the latest window has elapsed:"
          % len(saved))
    if saved:
        last = saved[-1]
        print("      earliest safe leg2 time: after %s %s local" % (last["date"], last["end"]))
    print("   OPTIONAL leg1b: re-run leg1 in ~6 h. The later windows then get a SHORT lead as")
    print("   well as the long one already recorded, which removes the time-of-day confound.")
    return 0


def leg2():
    banner("N-13 leg2  collect the outcomes and measure sigma(lead)   [PAID]")
    if not os.path.exists(MANIFEST):
        print("   no manifest at %s -- run leg1 first." % MANIFEST)
        return 2
    man = json.load(open(MANIFEST))
    key = load_key()
    before = credits_remaining(key)
    print("   forecasts were issued at %s" % man["issued_at"])
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    aoi = box_aoi(man["centre"][0], man["centre"][1], man["side_km"])

    rows, errors = [], {}
    for i, w in enumerate(man["windows"], 1):
        fx = os.path.join(RESULTS, "fixtures", "%s.json" % w["tag"])
        if not os.path.exists(fx):
            errors[w["tag"]] = "forecast fixture missing"
            continue
        F, _ = field_max(json.load(open(fx)))
        print("\n   CALL %d/%d  outcome for %s %s-%s (lead %.1f h) ..."
              % (i, len(man["windows"]), w["date"], w["start"], w["end"], w["lead_centre_h"]))
        H, n = call_window(key, aoi, w["date"], w["start"], w["end"],
                           "n13_h_%s_%s" % (w["date"], w["start"].replace(":", "")))
        if H is None:
            errors[w["tag"]] = n
            print("      FAILED: %s" % n)
            continue
        keys = [k for k in F if k in H]
        if not keys:
            errors[w["tag"]] = "no matching tiles"
            continue
        res = [F[k] - H[k] for k in keys]
        a = sorted(abs(x) for x in res)
        q90 = a[min(len(a) - 1, math.ceil((len(a) + 1) * 0.9) - 1)]
        rows.append({"lead_h": w["lead_centre_h"], "n_tiles": len(keys),
                     "bias": statistics.fmean(res), "sd": statistics.pstdev(res),
                     "q90_abs": q90})
        print("      %d matched tiles   bias %+.4f C   sd %.4f C   |res| q90 %.4f C"
              % (len(keys), statistics.fmean(res), statistics.pstdev(res), q90))

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))

    if len(rows) < 3:
        print("\n   fewer than 3 lead times recovered -- cannot fit a slope.")
        save_result("n13_leadtime.json", {"rows": rows, "errors": errors, "pass": None})
        return 2

    rows.sort(key=lambda r: r["lead_h"])
    print("\n   RESULT")
    print("      %8s %9s %10s %10s" % ("lead h", "n", "sd C", "q90 C"))
    for r in rows:
        print("      %8.1f %9d %10.4f %10.4f" % (r["lead_h"], r["n_tiles"], r["sd"], r["q90_abs"]))

    # fit sd = a * lead^b  in logs; b IS the tightening exponent N-9 sweeps
    xs = [math.log(r["lead_h"]) for r in rows]
    ys = [math.log(max(r["sd"], 1e-6)) for r in rows]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0
    print("      ------------------------------------------------")
    print("      fitted tightening exponent b in sd ~ lead^b : %.3f" % b)
    print("      (N-9 assumed 0.50; N-9 LOSES at b <= 0.0)")

    ok = b > 0.15
    print("\n   WHAT THIS DOES TO N-9  (thresholds fixed in advance)")
    print("      b >= 0.5   -> N-9's assumption is met or beaten")
    print("      0.15-0.5   -> weaker than assumed; re-run N-9 at the measured b")
    print("      <= 0.15    -> effectively no sharpening; N-9's agency claim fails")
    print("      measured b = %.3f" % b)
    print()
    verdict(ok,
            "PASS - forecast error shrinks with lead time at exponent %.3f, so waiting genuinely "
            "buys information and N-9's stopping rule rests on measured behaviour. Re-run N-9 "
            "with exponent=%.3f and quote that number." % (b, b),
            "FAIL - error does not shrink materially with lead time (b=%.3f). Waiting buys no "
            "information; N-9's gain must be recomputed at this exponent and the agency claim "
            "rebuilt on the peak-hour risk alone, or on fleet allocation." % b)

    save_result("n13_leadtime.json", {
        "issued_at": man["issued_at"], "rows": rows, "errors": errors,
        "fitted_exponent": b, "n9_assumed": 0.5,
        "confound_note": "lead time is confounded with time of day unless leg1b was run",
        "before": before, "after": after, "meter_moved": before != after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "leg1").lower()
    sys.exit(leg1() if mode == "leg1" else leg2())
