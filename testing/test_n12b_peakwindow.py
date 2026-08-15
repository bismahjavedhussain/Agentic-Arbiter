# -*- coding: utf-8 -*-
"""N-12b  falsify time_of_measure: is the max actually in the afternoon or at 22:00?  PAID."""
import statistics
from common import load_key, credits_remaining, submit_poll, banner, box_aoi, save_result

key = load_key()
aoi = box_aoi(39.0100, -77.4460, 2.0)
banner("N-12b  Where is the daily max REALLY?  tcm max in afternoon vs night windows  [PAID]")
before = credits_remaining(key)
print("   cycle_remaining BEFORE: %s" % format(before, ","))

TESTS = [("2026-07-28", "12:00", "16:00", "afternoon"),
         ("2026-07-28", "20:00", "23:00", "night"),
         ("2026-06-15", "12:00", "16:00", "afternoon"),
         ("2026-06-15", "23:00", "23:00", "midnight-ish")]

res = {}
for i, (day, s, e, label) in enumerate(TESTS, 1):
    print("\n   CALL %d/%d  %s  %s-%s (%s)" % (i, len(TESTS), day, s, e, label))
    p = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
         "date_time": {"start_date": day, "start_time": s, "end_time": e, "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, "n12b_%s_%s" % (day, s.replace(":", "")))
    if not r.get("ok"):
        print("      FAILED: %s" % r.get("error")); continue
    f = (r["result"].get("map_data") or {}).get("features") or []
    if not f:
        print("      ZERO TILES"); continue
    mx = [t["properties"].get("max_temperature") for t in f]
    av = [t["properties"].get("average_temperature") for t in f]
    mx = [v for v in mx if v is not None]; av = [v for v in av if v is not None]
    res[(day, label)] = {"n": len(f), "area_max": max(mx), "mean_of_max": statistics.fmean(mx),
                         "mean_avg": statistics.fmean(av)}
    print("      %d tiles   area max %.3f C   mean of per-tile max %.3f   mean avg %.3f"
          % (len(f), max(mx), statistics.fmean(mx), statistics.fmean(av)))

after = credits_remaining(key)
print("\n   cycle_remaining AFTER : %s   APPARENT SPEND: %s"
      % (format(after, ","), format(before - after, ",")))

print("\n   VERDICT")
for day in ("2026-07-28", "2026-06-15"):
    a = res.get((day, "afternoon"))
    n = res.get((day, "night")) or res.get((day, "midnight-ish"))
    if a and n:
        d = a["mean_of_max"] - n["mean_of_max"]
        print("      %s  afternoon %.3f C  vs  late %.3f C   difference %+.3f C  -> %s"
              % (day, a["mean_of_max"], n["mean_of_max"], d,
                 "AFTERNOON is hotter (time_of_measure's 0/1/2/22 are WRONG)" if d > 0.2
                 else "late window hotter -- unexpected, investigate"))
save_result("n12b_peakwindow.json", {"tests": [list(t) for t in TESTS],
                                     "results": {"%s|%s" % k: v for k, v in res.items()},
                                     "before": before, "after": after})
