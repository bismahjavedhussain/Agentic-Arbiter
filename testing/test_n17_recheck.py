# -*- coding: utf-8 -*-
"""N-17  recheck the two candidates I did not trust, plus a new hypothesis.  PAID.

R1  Is heat_index_celsius computed from the CALLER'S temperature input rather than from actual
    conditions? Same point, same hour, three different input temperatures. If heat_index tracks
    the input, that explains the "near-constant" observation far more precisely.

R2  Do persistence and exceedance differ over a window where they MUST? A single afternoon gives
    one contiguous run above threshold, so "hours above" and "longest run" are legitimately
    equal. A month cannot: many separate afternoons above 30 C means count >> longest run.
"""
import statistics
from common import load_key, credits_remaining, submit_poll, banner, box_aoi, save_result

key = load_key(); before = credits_remaining(key)
banner("N-17  Rechecking the two untrusted candidates   [PAID]")
print("   cycle_remaining BEFORE: %s" % format(before, ","))
out = {}

print("\n   R1  does heat_index track the CALLER'S temperature input?")
print("      %10s %14s %14s %14s" % ("input T", "heat_index", "apparent", "wet_bulb"))
r1 = []
for t_in in (10.0, 25.0, 40.0):
    p = {"latitude": 39.01, "longitude": -77.446, "temperature": t_in,
         "date_time": {"start_date": "2026-08-10", "start_time": "15:00", "filter_type": 1}}
    r = submit_poll(key, "env_params", p, "n17_r1_%d" % int(t_in))
    if not r.get("ok"):
        print("      input %.0f -> FAILED %s" % (t_in, r.get("error"))); continue
    loc = r["result"]["locations"][0]
    g = lambda k: (loc["parameters"].get(k) or [None])[0]
    row = {"input": t_in, "echo": loc.get("temperature"), "hi": g("heat_index_celsius"),
           "ap": g("apparent_temperature_celsius"), "wb": g("wet_bulb_temperature_celsius")}
    r1.append(row)
    print("      %10.1f %14s %14s %14s" % (t_in, row["hi"], row["ap"], row["wb"]))
his = [x["hi"] for x in r1 if isinstance(x["hi"], (int, float))]
ins = [x["input"] for x in r1 if isinstance(x["hi"], (int, float))]
tracks = len(his) >= 2 and (max(his) - min(his)) > 3.0
echoes = all(x["echo"] == x["input"] for x in r1)
print("      heat_index range across inputs: %s  -> tracks the input: %s"
      % (("%.1f" % (max(his) - min(his))) if his else "n/a", tracks))
print("      locations[].temperature always equals the input: %s" % echoes)
out["R1"] = {"rows": r1, "heat_index_tracks_input": tracks, "temperature_is_echo": echoes}

print("\n   R2  persistence vs exceedance over a MONTH (must differ if computed differently)")
aoi = box_aoi(39.01, -77.446, 1.0)
res2 = {}
for at in ("exceedance", "persistence"):
    p = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": at,
         "threshold_temperature": 30.0,
         "date_time": {"start_date": "2026-07-01", "end_date": "2026-07-31", "filter_type": 4}}
    r = submit_poll(key, "heatmap", p, "n17_r2_%s" % at)
    if not r.get("ok"):
        print("      %-12s FAILED %s" % (at, str(r.get("error"))[:60])); continue
    f = (r["result"].get("map_data") or {}).get("features") or []
    if not f:
        print("      %-12s EMPTY" % at); continue
    v = {x["properties"].get("tile_id"): x["properties"].get("value") for x in f}
    res2[at] = v
    vv = [x for x in v.values() if x is not None]
    print("      %-12s n=%d mean %.4f range %.4f-%.4f" % (at, len(vv), statistics.fmean(vv),
                                                          min(vv), max(vv)))
if len(res2) == 2:
    ks = [k for k in res2["exceedance"] if k in res2["persistence"]]
    same = sum(1 for k in ks if res2["exceedance"][k] == res2["persistence"][k])
    frac = same / len(ks) if ks else 0
    print("      identical on %d/%d tiles (%.1f%%)" % (same, len(ks), 100 * frac))
    print("      -> %s" % ("CONFIRMED defect: identical even over a month where they must differ"
                           if frac > 0.99 else
                           "WITHDRAWN: they DO differ over a discriminating window"))
    out["R2"] = {"n": len(ks), "identical": same, "fraction": frac,
                 "verdict": "CONFIRMED" if frac > 0.99 else "WITHDRAWN"}
else:
    out["R2"] = {"verdict": "INCONCLUSIVE", "note": "could not fetch both over a month"}
    print("      -> INCONCLUSIVE")

after = credits_remaining(key)
print("\n   cycle_remaining %s -> %s   SPEND %s" % (format(before, ","), format(after, ","),
                                                     format(before - after, ",")))
save_result("n17_recheck.json", out)
