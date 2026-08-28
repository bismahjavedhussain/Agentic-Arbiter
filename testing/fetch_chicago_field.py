# -*- coding: utf-8 -*-
"""ONE PAID /v1/heatmap CALL for the committed CHICAGO site. 4,220 credits.

AUTHORISED BY THE USER 2026-08-19 ("do the chicago one"), for exactly one call.

--------------------------------------------------------------------------------------------
WHY CHICAGO EARNED THIS AND THE OTHER TWO DID NOT
--------------------------------------------------------------------------------------------
Three metros were built out on free data. The aerial-imagery scope gate then rejected two:
  santaclara  ROOFTOP cooling on both screened pairs -> FortyGuard's 2 m plane is not the plane
              that equipment breathes, so PLAN section 8d's premise is false there.
  phoenix     the selected pair is BARE GRADED DESERT under construction -- no buildings to model.
Chicago passed: grade-level equipment yards, clean roofs, 0 % of bearings refused, and the full
geometry verification (V1 0 cells differ, V2 areas in tolerance, V3 no overlap, intake clear).

--------------------------------------------------------------------------------------------
🔴 THE TIMEZONE, WHICH IS WHY THIS FILE EXISTS INSTEAD OF REUSING common.site_window()
--------------------------------------------------------------------------------------------
`/v1/heatmap` reads `start_time` in the AOI'S OWN LOCAL ZONE and echoes no timestamp back
(gotcha #1 -- it cost this project four days). `common.py` hard-codes

    SITE_TZ_NAME = "America/New_York"      # the AOI throughout is Loudoun County, Virginia

so calling `site_window()` for an Illinois AOI would build the window in EASTERN time while the
server interpreted it as CENTRAL: a silent one-hour shift, with no error and a plausible-looking
field to show for it. The zone is therefore passed EXPLICITLY here and printed before the call.

--------------------------------------------------------------------------------------------
A PAST WINDOW, DELIBERATELY
--------------------------------------------------------------------------------------------
The forecast path recovered on 2026-08-19 and was verified (DIAG-62, 17,862 tiles at 9.41 h lead).
But it had also failed for ~30 hours immediately before that, and this is a single authorised call
on a new site. A past window had NEVER failed on this key across nine calls AS OF 2026-08-19, so
the conservative choice was a fully-elapsed window: it guaranteed the site got its field.

🔴 RETRACTED 2026-08-23 -- DIAG-66. A past window is no longer a guarantee of anything. The
national build's first live batch (20 calls, all AOIs) and a dedicated control call at Ashburn's
own long-proven geometry BOTH came back `completed_but_empty`, fully billed, on a past/elapsed
window -- the exact class this sentence claimed had never happened. It was true when written and
is false now: the vendor relapsed into a general outage the same day its forecast path had
recovered (HANDOFF.md section 4.0-RECOVERY). "Past window" is a risk-reducer, not a guarantee, and
must never be quoted as one again.

    What one field buys: the real FortyGuard spatial statistics for Chicago and the screen-zero
    visual. It does NOT buy a level-offset measurement -- that needs a forecast leg AND its elapsed
    outcome, i.e. two calls. Stated so the demo does not imply otherwise.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (banner, box_aoi, credits_remaining, load_key, RESULTS,   # noqa: E402
                    save_result, submit_poll, utc_now)

# The committed pair's two centroids, read from the file the pipeline wrote -- not typed in.
SITE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "AGENTIC-ARBITER", "data", "geometry", "chicago_selected_site.json")
TZ_NAME = "America/Chicago"          # the AOI's OWN zone. NOT common.SITE_TZ_NAME.
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
ANALYTIC = "tcm"
TARGET_HOUR_SITE = 14                # same hour Ashburn's fields use, for comparability


def main():
    banner("CHICAGO FIELD   one paid /v1/heatmap call, authorised. Past window, explicit tz.")

    sel = json.load(open(SITE_FILE, encoding="utf-8"))
    a = sel["source_building"]["centre_latlon"]
    b = sel["receptor_building"]["centre_latlon"]
    clat, clon = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    print("   committed pair : %s -> %s" % (sel["selected"]["source_osm_id"],
                                            sel["selected"]["receptor_osm_id"]))
    print("   %s -> %s" % (sel["source_building"].get("name"),
                           sel["receptor_building"].get("name")))
    print("   AOI centre     : %.6f, %.6f   (midpoint of the two centroids)" % (clat, clon))

    tz = ZoneInfo(TZ_NAME)
    now_site = utc_now().astimezone(tz)
    # the most recent day whose target window has FULLY elapsed, plus a 30-minute safety margin
    day = now_site.date()
    start = datetime(day.year, day.month, day.day, TARGET_HOUR_SITE, 0, tzinfo=tz)
    while start + timedelta(hours=WIN_H, minutes=30) > now_site:
        day = day - timedelta(days=1)
        start = datetime(day.year, day.month, day.day, TARGET_HOUR_SITE, 0, tzinfo=tz)
    end = start + timedelta(hours=WIN_H)
    elapsed_h = (now_site - end).total_seconds() / 3600.0

    print("   site zone      : %s   (common.py's hard-coded zone is America/New_York -- NOT used)"
          % TZ_NAME)
    print("   site-local now : %s" % now_site.strftime("%Y-%m-%d %H:%M %Z"))
    print("   window         : %s %s-%s site-local, ELAPSED %.1f h ago"
          % (start.strftime("%Y-%m-%d"), start.strftime("%H:%M"), end.strftime("%H:%M"), elapsed_h))
    print("   granularity/analytic : %d / %s   AOI %.0f x %.0f km"
          % (GRAN, ANALYTIC, SIDE_KM, SIDE_KM))
    if elapsed_h <= 0:
        print("   REFUSING: the window has not elapsed. A past window is the whole point.")
        return 2

    dt = {"start_date": start.strftime("%Y-%m-%d"),
          "start_time": start.strftime("%H:00"),
          "end_time": end.strftime("%H:00"),
          "filter_type": 2}
    print("   payload date_time : %s" % json.dumps(dt))

    key = load_key()                                   # never printed, never logged
    before = credits_remaining(key)
    print("\n   credits remaining BEFORE : %s" % format(before, ","))
    print("   making ONE paid call ...\n")

    payload = {"polygon_aoi": box_aoi(clat, clon, SIDE_KM), "granularity": GRAN,
               "analytic_type": ANALYTIC, "date_time": dt}
    r = submit_poll(key, "heatmap", payload, "chicago_field_%s" % start.strftime("%Y%m%d_%H%M"),
                    max_s=480, require_data=True)
    after = credits_remaining(key)

    feats = (((r.get("result") or {}).get("map_data") or {}).get("features") or [])
    stats = ((r.get("result") or {}).get("stats_data") or {}).get("temperature_stats") or {}
    ok = bool(r.get("ok")) and len(feats) > 0

    print("   activity_id            : %s" % r.get("aid"))
    print("   elapsed                : %s s   empty completed polls: %s"
          % (r.get("secs"), r.get("empty_completed_polls")))
    print("   TILES RETURNED         : %s" % format(len(feats), ","))
    if stats:
        print("   FortyGuard stats (tile AVERAGES): min %.4f  max %.4f  mean %.4f  sd %.4f"
              % (stats.get("minimum", float("nan")), stats.get("maximum", float("nan")),
                 stats.get("mean", float("nan")), stats.get("standard_deviation", float("nan"))))
    if feats:
        mx = [f["properties"].get("max_temperature") for f in feats
              if f["properties"].get("max_temperature") is not None]
        if mx:
            print("   our channel (per-tile MAX): min %.4f  max %.4f  mean %.4f  over %s tiles"
                  % (min(mx), max(mx), sum(mx) / len(mx), format(len(mx), ",")))
    if r.get("error"):
        print("   error                  : %s" % r["error"])
    print("\n   credits remaining AFTER  : %s   COST %s"
          % (format(after, ","), format(before - after, ",")))

    out = {"test": "chicago field, one paid call",
           "authorised_by_user": "2026-08-19",
           "api_calls_made": 1,
           "metro": "chicago",
           "pair": [sel["selected"]["source_osm_id"], sel["selected"]["receptor_osm_id"]],
           "names": [sel["source_building"].get("name"), sel["receptor_building"].get("name")],
           "aoi_centre": [clat, clon], "side_km": SIDE_KM,
           "tz_used": TZ_NAME,
           "tz_note": ("explicit, because common.SITE_TZ_NAME is hard-coded to America/New_York "
                       "and the endpoint reads start_time in the AOI's own zone (gotcha #1)"),
           "window_site": [start.isoformat(), end.isoformat()],
           "window_elapsed_h_before_call": round(elapsed_h, 2),
           "granularity": GRAN, "analytic_type": ANALYTIC, "date_time": dt,
           "activity_id": r.get("aid"), "elapsed_s": r.get("secs"),
           "empty_completed_polls": r.get("empty_completed_polls"),
           "tiles_returned": len(feats),
           "fortyguard_stats_tile_averages": stats,
           "error": r.get("error"),
           "credits_before": before, "credits_after": after, "credits_spent": before - after,
           "buys": "spatial field + screen-zero visual for chicago",
           "does_not_buy": ("a level-offset measurement -- that needs a forecast leg AND its "
                            "elapsed outcome, i.e. two calls"),
           "verdict": "OK" if ok else "FAILED"}
    save_result("chicago_field.json", out)
    print("   wrote %s" % os.path.join(RESULTS, "chicago_field.json"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
