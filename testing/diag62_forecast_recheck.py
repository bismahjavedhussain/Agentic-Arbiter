# -*- coding: utf-8 -*-
"""DIAG-62  ---  is the FORECAST path still returning zero tiles, at the lead we actually need?

ONE PAID CALL (4,220 credits). EXPLICITLY AUTHORISED BY THE USER, 2026-08-19, who asked to
"check the forecast again on the same conditions as we need using a paid call".

--------------------------------------------------------------------------------------------
WHAT IS ALREADY KNOWN, so this call is not buying an answer we own
--------------------------------------------------------------------------------------------
    request                         lead        result                         when
    PAST window 2026-08-16          elapsed     17,862 tiles                   works
    future                          ~8.6 h      0 tiles                        2026-08-18
    future                          9.38 h      0 tiles                        2026-08-19
    future                          2.29 h      0 tiles      <- kills the "12 h horizon" theory
    future                          8.86 h      0 tiles
    future                          8.22 h      0 after 58 polls over 607 s     through the FIXED loop
    automated n26_f_2026-08-18      --          "ZERO TILES with completed status"
    automated n26_f_2026-08-19      --          "completed but never populated after 58 polls"

EXCLUDED already: the 12 h horizon (2.29 h also failed), request size and granularity (8x8 km at
granularity 60 is exactly what returns 17,862 tiles for a PAST window), time of day (three attempts
inside 35 minutes), and the first-poll-empty behaviour FortyGuard's own team documented (the loop
was fixed, and a future window still never populated after 607 s).

    A1  the Hackathon plan carries no FORECAST entitlement   -> fails again today, and every day
    A3  FortyGuard's forecast path is transiently degraded    -> may have RECOVERED since 2026-08-19

--------------------------------------------------------------------------------------------
THE ONE VARIABLE, and why this call is worth making anyway
--------------------------------------------------------------------------------------------
Every field is held at the N-26 collector's own values -- 8x8 km AOI on the committed centre,
granularity 60, analytic_type tcm, a 2 h window -- and the LEAD is chosen to land at ~9.4 h, which
reproduces the N-25 reference lead of 9.41 h to within 0.05 h. So the only thing separating this
request from the one that returns 17,862 tiles is that the window is in the FUTURE.

The variable actually being tested is therefore TIME, not shape: this is the fourth consecutive day
on which a future window is attempted. That is the only thing that separates A1 from A3, and it is
what the user asked for.

--------------------------------------------------------------------------------------------
PRE-REGISTERED BEFORE THE CALL IS MADE  (methodology rule 2)
--------------------------------------------------------------------------------------------
    P1  > 0 tiles returned
        -> A3 CONFIRMED and RECOVERED. The forecast path works at the lead we need. N-26 collection
           resumes immediately, the 4-pair ceiling lifts, and coverage can move off 65.6 %.
           ACTION: re-enable collection, and treat 65.6 % as provisional again.
    P2  0 tiles after the full polling window
        -> the condition persists on a FOURTH consecutive day. A1 becomes the leading explanation.
           ACTION: 65.6 % stays PERMANENT, the FortyGuard message gets sent, and NO further paid
           forecast call is made -- the daily task already tests it for free-of-extra-effort.
    Either way: no further paid forecast probe today.

--------------------------------------------------------------------------------------------
SAFETY
--------------------------------------------------------------------------------------------
    * The key is read only via common.load_key(). It is NEVER printed, logged, or written to any
      fixture or result file.
    * The credit meter is read before and after through the FREE usage endpoint (gotcha #33) and
      DIFFERENCED, so the true cost is measured rather than assumed -- including confirming again
      that a zero-tile `completed` response IS billed (gotcha #30).
    * Exactly ONE paid call. There is no retry loop around the paid call.
    * `require_data=True`, so the FIXED polling loop keeps polling through completed-but-empty and
      reports `empty_completed_polls`. A zero-tile answer is only recorded after the timeout, which
      is the correct reading of FortyGuard's own guidance (gotcha #51).
    * max_s is 480 s. A past window populates in ~45 s; the known failure signature ran 607 s. 480 s
      of polling with no data is therefore decisive, and it keeps the run inside one foreground
      timeout instead of relying on unreliable background capture (gotcha #6).
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (banner, box_aoi, credits_remaining, lead_hours, load_key,  # noqa: E402
                    RESULTS, save_result, site_now, site_tz, site_window,
                    submit_poll, utc_now, SITE_TZ_NAME)

# ---- held IDENTICAL to test_n26_coverage.py, so nothing but the window direction differs
CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
ANALYTIC = "tcm"

TARGET_LEAD_H = 9.41           # the N-25 reference lead this reproduces
MIN_LEAD_H = 6.0               # the collector's comparability band
MAX_LEAD_H = 11.5
MAX_POLL_S = 480

OUT = os.path.join(RESULTS, "diag62_forecast_recheck.json")


def pick_window():
    """Choose the site-local target hour whose lead is closest to the N-25 reference.

    Uses common.site_window()/lead_hours() throughout -- never a naive datetime, never a window
    formatted from datetime.now(). That is gotcha #1, the 9-hour timezone bug, and it is the single
    easiest way to invalidate this entire measurement.
    """
    sn = site_now()
    best = None
    for day_off in (0, 1):
        for hh in range(24):
            d = sn.date() + timedelta(days=day_off)
            start = datetime(d.year, d.month, d.day, hh, 0, tzinfo=site_tz())
            try:
                w = site_window(start, WIN_H)
            except ValueError:
                continue                      # crosses midnight -- the endpoint cannot express it
            L = lead_hours(w["_start_utc"])
            if not (MIN_LEAD_H <= L <= MAX_LEAD_H):
                continue
            if best is None or abs(L - TARGET_LEAD_H) < abs(best[1] - TARGET_LEAD_H):
                best = (w, L, start)
    return best


def main():
    banner("DIAG-62   FORECAST RECHECK   one paid call, authorised. Pre-registered P1/P2 above.")

    picked = pick_window()
    if not picked:
        print("   No target hour lands inside the %.1f-%.1f h lead band from site-local %s."
              % (MIN_LEAD_H, MAX_LEAD_H, site_now().strftime("%Y-%m-%d %H:%M")))
        print("   REFUSING to call: a lead outside the band is not the condition we need, and a")
        print("   lead beyond ~12 h could return zero tiles for a legitimate horizon reason.")
        return 2

    win, lead, start_site = picked
    print("   site timezone            : %s" % SITE_TZ_NAME)
    print("   site-local now           : %s" % site_now().strftime("%Y-%m-%d %H:%M:%S %z"))
    print("   target window (site)     : %s  +%d h" % (start_site.strftime("%Y-%m-%d %H:%M"), WIN_H))
    print("   window start (UTC)       : %s" % win["_start_utc"].strftime("%Y-%m-%d %H:%M:%S %z"))
    print("   LEAD                     : %.2f h   (N-25 reference %.2f h, band %.1f-%.1f)"
          % (lead, TARGET_LEAD_H, MIN_LEAD_H, MAX_LEAD_H))
    print("   AOI                      : %.1f x %.1f km centred %.4f, %.4f"
          % (SIDE_KM, SIDE_KM, CENTRE[0], CENTRE[1]))
    print("   granularity / analytic   : %d / %s" % (GRAN, ANALYTIC))
    print("   payload date_time        : %s"
          % json.dumps({k: v for k, v in win.items() if not k.startswith("_")}))

    key = load_key()                                  # never printed, never logged
    before = credits_remaining(key)
    print("\n   credits remaining BEFORE : %s" % format(before, ","))
    print("   making ONE paid /v1/heatmap call, polling up to %d s ...\n" % MAX_POLL_S)

    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": ANALYTIC,
               "date_time": {k: v for k, v in win.items() if not k.startswith("_")}}
    tag = "diag62_forecast_lead%.2f" % lead
    r = submit_poll(key, "heatmap", payload, tag, max_s=MAX_POLL_S, require_data=True)

    after = credits_remaining(key)
    spent = before - after

    feats = (((r.get("result") or {}).get("map_data") or {}).get("features") or [])
    n_tiles = len(feats)
    ok = bool(r.get("ok")) and n_tiles > 0

    print("   activity_id              : %s" % r.get("aid"))
    print("   elapsed                  : %s s" % r.get("secs"))
    print("   empty completed polls    : %s" % r.get("empty_completed_polls"))
    print("   TILES RETURNED           : %s" % format(n_tiles, ","))
    if r.get("error"):
        print("   error                    : %s" % r["error"])
    print("\n   credits remaining AFTER  : %s" % format(after, ","))
    print("   COST OF THIS CALL        : %s  (a zero-tile completed response IS billed)"
          % format(spent, ","))

    print("\n   VERDICT AGAINST THE PRE-REGISTERED CONDITIONS")
    if ok:
        print("      P1 MET  -- %s tiles at a %.2f h lead. The forecast path WORKS." % (
            format(n_tiles, ","), lead))
        print("      -> A3 (transient degradation) is CONFIRMED and has RECOVERED.")
        print("      -> N-26 collection can resume; the 4-pair ceiling lifts; 65.6 %% becomes")
        print("         PROVISIONAL again rather than permanent.")
    else:
        print("      P2 MET  -- zero tiles again, on a FOURTH consecutive day, at a %.2f h lead"
              % lead)
        print("         with the AOI, granularity, analytic_type and window length that return")
        print("         17,862 tiles for a PAST window.")
        print("      -> A1 (no forecast entitlement on the Hackathon plan) is now the leading")
        print("         explanation. 65.6 %% stays PERMANENT. Send the FortyGuard message.")
        print("      -> NO further paid forecast probe. The daily task keeps testing it.")

    out = {"test": "DIAG-62 forecast recheck",
           "authorised_by_user": "2026-08-19",
           "api_calls_made": 1,
           "site_tz": SITE_TZ_NAME,
           "site_now": site_now().isoformat(),
           "utc_now": utc_now().isoformat(),
           "target_window_site": start_site.isoformat(),
           "window_start_utc": win["_start_utc"].isoformat(),
           "lead_h": round(lead, 4),
           "lead_band": [MIN_LEAD_H, MAX_LEAD_H],
           "n25_reference_lead_h": TARGET_LEAD_H,
           "aoi_centre": list(CENTRE), "side_km": SIDE_KM,
           "granularity": GRAN, "analytic_type": ANALYTIC, "win_h": WIN_H,
           "date_time": {k: v for k, v in win.items() if not k.startswith("_")},
           "activity_id": r.get("aid"),
           "elapsed_s": r.get("secs"),
           "empty_completed_polls": r.get("empty_completed_polls"),
           "tiles_returned": n_tiles,
           "error": r.get("error"),
           "credits_before": before, "credits_after": after, "credits_spent": spent,
           "prereg": {"P1": "> 0 tiles -> A3 recovered", "P2": "0 tiles -> A1 leading"},
           "verdict": "P1 MET -- forecast works" if ok else "P2 MET -- still zero tiles"}
    save_result("diag62_forecast_recheck.json", out)
    print("\n   wrote %s" % OUT)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
