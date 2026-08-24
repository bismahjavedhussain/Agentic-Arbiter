# -*- coding: utf-8 -*-
"""DIAG-66 -- ONE control call, authorised, to settle general-outage vs AOI-specific.

`buy_national_fields.py`'s first live chunk went 20-for-20 `completed_but_empty` -- 100 % billed
failure across VA, CA, TX, OH, WA, OR, PA, IA, WY. Rank #1 of that batch (centre 39.0244,-77.4496)
sits ~2.5 km from Ashburn's own COMMITTED, repeatedly-successful centroid (39.0240165,-77.4196915)
-- the SAME AOI class this project has bought fields for many times, including a 12/12 recovery
run earlier TODAY. This asks: does the proven geometry ALSO fail right now?

  ok / ok_with_tiles  -> the fault is AOI-specific (new/unfamiliar locations), not a general outage
  completed_but_empty -> a general, renewed outage -- unrelated to which AOI is requested

SAME date/hour as the failed batch's rank #1 (2026-08-22 14:00-16:00), so only the geometry
differs -- and a window NEVER requested before for Ashburn (checked: only 08-20 and 08-23 exist
in data/live_cache/ashburn/), so this is a live call, not a cache hit.

ONE paid call, 4,220 credits. Authorised by the user 2026-08-23: "run the diagnostic."
"""
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (banner, box_aoi, credits_remaining, load_key, save_result,   # noqa: E402
                    submit_poll)

IA_GEOM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "INTAKE-ARBITER", "data", "geometry", "selected_site.json")
TZ_NAME = "America/New_York"        # Ashburn's real zone -- gotcha #1's fix, not a guess here
SIDE_KM = 8.0
GRAN = 60
ANALYTIC = "tcm"
WIN_START_LOCAL = "2026-08-22 14:00"     # same date/hour as the failed batch's rank #1
WIN_END_LOCAL = "2026-08-22 16:00"


def main():
    banner("DIAG-66  control: does ASHBURN's OWN proven geometry ALSO fail right now?")
    sel = json.load(open(IA_GEOM, encoding="utf-8"))
    a = sel["source_building"]["centre_latlon"]
    b = sel["receptor_building"]["centre_latlon"]
    clat, clon = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    print("   Ashburn committed centroid : %.6f, %.6f  (source %s / receptor %s)"
          % (clat, clon, sel["selected"]["source_osm_id"], sel["selected"]["receptor_osm_id"]))

    tz = ZoneInfo(TZ_NAME)
    start = datetime.strptime(WIN_START_LOCAL, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    end = datetime.strptime(WIN_END_LOCAL, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    dt = {"start_date": start.strftime("%Y-%m-%d"), "start_time": start.strftime("%H:00"),
          "end_time": end.strftime("%H:00"), "filter_type": 2}
    print("   window (same date/hour as the failed batch's rank #1) : %s %s-%s %s"
          % (dt["start_date"], dt["start_time"], dt["end_time"], TZ_NAME))
    print("   this window has never been requested for Ashburn before (checked live_cache)")

    key = load_key()
    before = credits_remaining(key)
    print("\n   credits remaining BEFORE : %s" % format(before, ","))
    print("   making ONE paid call ...\n")

    payload = {"polygon_aoi": box_aoi(clat, clon, SIDE_KM), "granularity": GRAN,
               "analytic_type": ANALYTIC, "date_time": dt}
    r = submit_poll(key, "heatmap", payload, "diag66_ashburn_control_20260822_1400",
                    max_s=480, require_data=True)
    after = credits_remaining(key)

    feats = (((r.get("result") or {}).get("map_data") or {}).get("features") or [])
    ok = bool(r.get("ok")) and len(feats) > 0

    print("   activity_id            : %s" % r.get("aid"))
    print("   elapsed                : %s s   empty completed polls: %s"
          % (r.get("secs"), r.get("empty_completed_polls")))
    print("   TILES RETURNED         : %s" % format(len(feats), ","))
    print("   credits: %s -> %s (spent %s)"
          % (format(before, ","), format(after, ","), format(before - after, ",")))

    print("\n" + "=" * 78)
    if ok:
        print("   RESULT: OK -- %s real tiles. Ashburn's PROVEN geometry works RIGHT NOW."
              % format(len(feats), ","))
        print("   -> The national batch's failure is likely AOI-SPECIFIC (unfamiliar/new")
        print("      locations), NOT a general vendor outage. Do not resume the national buy")
        print("      until that is understood further -- but the vendor itself is not down.")
    else:
        print("   RESULT: EMPTY/FAILED (class-equivalent to the national batch's failures).")
        print("   -> This is a GENERAL, RENEWED OUTAGE, unrelated to which AOI is requested.")
        print("      Even the proven Ashburn geometry failed. Resuming the national buy right")
        print("      now would spend into the same fault regardless of allocation strategy.")
    print("=" * 78)

    save_result("diag66_national_control.json", {
        "window": dt, "centre": [clat, clon], "ok": ok, "n_tiles": len(feats),
        "activity_id": r.get("aid"), "credits_before": before, "credits_after": after,
        "credits_spent": before - after, "raw": r,
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
