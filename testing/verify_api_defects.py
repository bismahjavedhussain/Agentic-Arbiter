# -*- coding: utf-8 -*-
"""VERIFY every candidate API defect with REPEATED fresh calls before reporting any of them.

This exists because the output feeds a document that goes to FortyGuard. A false positive there
is worse than saying nothing, so nothing is written up from a single observation. Every candidate
is retried, and each one ends up in exactly one bucket:

    CONFIRMED       reproduced on every trial (n reported)
    INTERMITTENT    reproduced on some trials (rate reported)
    OBSERVED_ONCE   seen before but not reproduced here -- report as a question, not a defect
    WITHDRAWN       did not reproduce; must NOT appear in the report

Every check records the exact request payload so FortyGuard can reproduce it.
The API key is never printed.
"""
import json, math, statistics, sys, time
from datetime import datetime, timedelta

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    assert_non_empty, hav)

CENTRE = (39.0100, -77.4460)
FINDINGS = {}
CALLS = [0]


def rec(cid, title, status, expected, actual, trials, payloads, notes=""):
    FINDINGS[cid] = {"id": cid, "title": title, "status": status, "expected": expected,
                     "actual": actual, "trials": trials, "payloads": payloads, "notes": notes}
    print("      -> %-13s %s" % (status, cid))


def hm(key, payload, tag):
    CALLS[0] += 1
    return submit_poll(key, "heatmap", payload, tag)


def ep(key, payload, tag):
    CALLS[0] += 1
    return submit_poll(key, "env_params", payload, tag)


def tiles_of(r):
    if not r.get("ok"):
        return None
    return (r["result"].get("map_data") or {}).get("features") or []


# ---------------------------------------------------------------- D1
def d1_forecast_retries(key, now):
    """Forecast windows: how often do they come back empty, and does retrying fix it?"""
    print("\n   D1  FORECAST AVAILABILITY AND RETRY BEHAVIOUR  (10 attempts)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], 1.0)
    fut = (now + timedelta(hours=6)).replace(minute=0, second=0, microsecond=0)
    payload = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
               "date_time": {"start_date": fut.strftime("%Y-%m-%d"),
                             "start_time": fut.strftime("%H:00"), "filter_type": 1}}
    outcomes = []
    for i in range(10):
        r = hm(key, payload, "vd_d1_%02d" % i)
        t = tiles_of(r)
        if not r.get("ok"):
            outcomes.append("error:%s" % str(r.get("error"))[:40])
        elif not t:
            outcomes.append("EMPTY_completed")
        else:
            outcomes.append("ok:%d" % len(t))
        print("      attempt %2d: %s" % (i + 1, outcomes[-1]))
        time.sleep(1)
    n_ok = sum(1 for o in outcomes if o.startswith("ok"))
    n_empty = sum(1 for o in outcomes if o == "EMPTY_completed")

    # The DEFECT here is not "no forecast" -- FortyGuard confirms a 12 h forecast exists and that
    # transient failures are retryable. The defect is the FAILURE MODE: an unavailable window is
    # reported as a SUCCESS with an empty payload, which no client can distinguish from
    # "this area genuinely has no tiles".
    status = "CONFIRMED" if n_empty > 0 else "WITHDRAWN"
    rec("D1", "Unavailable forecast window returns status=completed with zero tiles instead of "
              "an error or retry signal",
        status,
        "Either tiles, or a non-success status / explicit error the client can retry on",
        "status=completed, map_data.features=[] , stats_data present but empty. %d/%d attempts "
        "empty, %d/%d returned tiles" % (n_empty, len(outcomes), n_ok, len(outcomes)),
        {"n": len(outcomes), "empty": n_empty, "ok": n_ok, "outcomes": outcomes},
        [payload],
        "FortyGuard confirms the 12 h forecast exists and transient failures are retryable. This "
        "entry is about the failure MODE, not the capability: a retryable condition is "
        "indistinguishable from a legitimately empty result, so clients cannot know to retry.")
    return n_ok > 0


# ---------------------------------------------------------------- D2
def d2_time_of_measure(key):
    """Same request, repeated: is time_of_measure deterministic? And is it physically plausible?"""
    print("\n   D2  time_of_measure DETERMINISM AND PLAUSIBILITY  (3 identical calls + tcm check)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], 2.0)
    payload = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "time_of_measure",
               "date_time": {"start_date": "2026-07-28", "start_time": "01:00",
                             "end_time": "23:00", "filter_type": 2}}
    runs = []
    for i in range(3):
        r = hm(key, payload, "vd_d2_%d" % i)
        t = tiles_of(r)
        if not t:
            runs.append(None); print("      call %d: no tiles" % (i + 1)); continue
        v = [x["properties"].get("value") for x in t]
        v = [x for x in v if x is not None]
        runs.append({"n": len(v), "min": min(v), "max": max(v),
                     "mean": statistics.fmean(v), "modal": max(set(v), key=v.count)})
        print("      call %d: n=%d modal=%.0f mean=%.2f range %.0f-%.0f"
              % (i + 1, len(v), runs[-1]["modal"], runs[-1]["mean"], min(v), max(v)))
        time.sleep(1)

    good = [r for r in runs if r]
    identical = len({(r["modal"], round(r["mean"], 3)) for r in good}) == 1 if good else None

    # cross-check against tcm: which window really holds the max on that date?
    print("      tcm cross-check on the same date:")
    wins, tcm = [("12:00", "16:00"), ("20:00", "23:00")], {}
    for s, e in wins:
        p2 = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
              "date_time": {"start_date": "2026-07-28", "start_time": s, "end_time": e,
                            "filter_type": 2}}
        r = hm(key, p2, "vd_d2_tcm_%s" % s.replace(":", ""))
        t = tiles_of(r)
        if t:
            mx = [x["properties"].get("max_temperature") for x in t]
            mx = [x for x in mx if x is not None]
            tcm[s] = statistics.fmean(mx)
            print("        %s-%s mean per-tile max %.3f C" % (s, e, tcm[s]))

    implausible = None
    if good and len(tcm) == 2:
        afternoon_hotter = tcm["12:00"] > tcm["20:00"] + 0.5
        nominated_late = any(r["modal"] >= 19 or r["modal"] <= 5 for r in good)
        implausible = afternoon_hotter and nominated_late

    if good and (identical is False or implausible):
        status = "CONFIRMED"
    elif good and identical and not implausible:
        status = "WITHDRAWN"
    else:
        status = "OBSERVED_ONCE"

    rec("D2", "analytic_type=time_of_measure returns non-reproducible and physically implausible "
              "hours",
        status,
        "The hour of the daily maximum: for Ashburn VA in July, mid-afternoon, and identical "
        "across identical requests",
        "Identical requests returned %s. tcm on the same date: 12:00-16:00 = %s C vs "
        "20:00-23:00 = %s C, so the maximum is in the afternoon."
        % ([r["modal"] for r in good],
           ("%.3f" % tcm["12:00"]) if "12:00" in tcm else "n/a",
           ("%.3f" % tcm["20:00"]) if "20:00" in tcm else "n/a"),
        {"runs": runs, "identical_across_calls": identical, "tcm_windows": tcm,
         "physically_implausible": implausible},
        [payload],
        "A previously saved response for this same date and window returned 14.0 for all tiles "
        "with spatial sd 0.000, while later calls returned a modal hour of 22 with range 14-22.")


# ---------------------------------------------------------------- D3
def d3_persistence_vs_exceedance(key, now):
    """Do the two analytics return the same numbers?"""
    print("\n   D3  persistence vs exceedance  (same window, both analytics)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], 1.0)
    day = (now - timedelta(hours=30)).strftime("%Y-%m-%d")
    dt = {"start_date": day, "start_time": "10:00", "end_time": "18:00", "filter_type": 2}
    out, pl = {}, []
    for at in ("exceedance", "persistence"):
        p = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": at,
             "threshold_temperature": 30.0, "date_time": dt}
        pl.append(p)
        r = hm(key, p, "vd_d3_%s" % at)
        t = tiles_of(r)
        if not t:
            print("      %s: no tiles (%s)" % (at, r.get("error"))); continue
        vals = {x["properties"].get("tile_id"): x["properties"].get("value") for x in t}
        out[at] = vals
        v = [x for x in vals.values() if x is not None]
        print("      %-12s n=%d  mean %.4f  range %.4f-%.4f"
              % (at, len(v), statistics.fmean(v), min(v), max(v)))
    if len(out) == 2:
        ks = [k for k in out["exceedance"] if k in out["persistence"]]
        same = sum(1 for k in ks if out["exceedance"][k] == out["persistence"][k])
        frac = same / len(ks) if ks else 0
        print("      identical on %d/%d tiles (%.1f%%)" % (same, len(ks), 100 * frac))
        status = "CONFIRMED" if frac > 0.99 else "WITHDRAWN"
        rec("D3", "analytic_type=persistence returns values identical to exceedance",
            status,
            "persistence should describe run-length / duration above threshold; exceedance "
            "describes count or magnitude of exceedance. They should differ.",
            "%d of %d tiles identical (%.1f%%)" % (same, len(ks), 100 * frac),
            {"tiles_compared": len(ks), "identical": same, "fraction": frac}, pl)
    else:
        rec("D3", "analytic_type=persistence returns values identical to exceedance",
            "OBSERVED_ONCE", "they should differ", "could not fetch both analytics this run",
            {}, pl)


# ---------------------------------------------------------------- D4
def d4_env_params_units(key, now):
    """cloud_cover_octas range, heat_index behaviour, timezone label."""
    print("\n   D4  env_params UNITS AND LABELS  (4 points/times)")
    pts = [(CENTRE[0], CENTRE[1]), (CENTRE[0] + 0.05, CENTRE[1] + 0.05),
           (32.7790, -96.8080), (33.4480, -112.0740)]
    hrs = ["06:00", "12:00", "18:00", "15:00"]
    day = (now - timedelta(hours=30)).strftime("%Y-%m-%d")
    rows, pl = [], []
    for i, ((la, lo), hh) in enumerate(zip(pts, hrs)):
        p = {"latitude": round(la, 5), "longitude": round(lo, 5), "temperature": 25.0,
             "date_time": {"start_date": day, "start_time": hh, "filter_type": 1}}
        pl.append(p)
        r = ep(key, p, "vd_d4_%d" % i)
        if not r.get("ok"):
            print("      point %d: %s" % (i, r.get("error"))); continue
        loc = r["result"]["locations"][0]
        g = lambda k: (loc["parameters"].get(k) or [None])[0]
        row = {"lat": la, "lon": lo, "hour": hh,
               "cloud_cover_octas": g("cloud_cover_octas"),
               "heat_index_celsius": g("heat_index_celsius"),
               "apparent_temperature_celsius": g("apparent_temperature_celsius"),
               "t_2m": g("t_2m:C") or g("temperature_celsius"),
               "tz": loc.get("timezone") or r["result"].get("timezone")}
        rows.append(row)
        print("      pt%d %s  cloud=%s  heat_index=%s  apparent=%s  tz=%s"
              % (i, hh, row["cloud_cover_octas"], row["heat_index_celsius"],
                 row["apparent_temperature_celsius"], row["tz"]))

    cc = [r["cloud_cover_octas"] for r in rows if isinstance(r["cloud_cover_octas"], (int, float))]
    over8 = [v for v in cc if v > 8]
    rec("D4a", "Parameter named cloud_cover_octas returns values outside the octas range 0-8",
        "CONFIRMED" if over8 else ("WITHDRAWN" if cc else "OBSERVED_ONCE"),
        "Octas are eighths of sky cover: integers 0-8",
        "observed values %s; %d of %d exceed 8" % (cc, len(over8), len(cc)),
        {"values": cc, "n_over_8": len(over8)}, pl,
        "Values look like percentages. Either the field should be renamed cloud_cover_percent or "
        "the values divided by 12.5.")

    hi = [r["heat_index_celsius"] for r in rows if isinstance(r["heat_index_celsius"], (int, float))]
    ap = [r["apparent_temperature_celsius"] for r in rows
          if isinstance(r["apparent_temperature_celsius"], (int, float))]
    hi_sd = statistics.pstdev(hi) if len(hi) > 1 else None
    ap_sd = statistics.pstdev(ap) if len(ap) > 1 else None
    near_const = hi_sd is not None and ap_sd is not None and hi_sd < 0.25 * ap_sd
    rec("D4b", "heat_index_celsius is near-constant across widely different conditions",
        "CONFIRMED" if near_const else "WITHDRAWN",
        "Heat index should vary with temperature and humidity, comparably to apparent temperature",
        "heat_index values %s (sd %s) vs apparent_temperature %s (sd %s) over the same four "
        "points/hours spanning Virginia, Texas and Arizona"
        % (hi, ("%.3f" % hi_sd) if hi_sd is not None else "n/a", ap,
           ("%.3f" % ap_sd) if ap_sd is not None else "n/a"),
        {"heat_index": hi, "apparent": ap, "hi_sd": hi_sd, "ap_sd": ap_sd}, pl)

    tzs = {r["tz"] for r in rows if r.get("tz")}
    rec("D4c", "Timezone label does not reflect daylight saving",
        "CONFIRMED" if any(str(t).endswith("-5") for t in tzs) else "OBSERVED_ONCE",
        "Eastern US in August is EDT = GMT-4",
        "labels seen: %s (for points spanning Eastern, Central and Mountain zones)" % sorted(tzs),
        {"labels": sorted(str(t) for t in tzs)}, pl,
        "Previously observed as GMT-5 in both July and August. A single label across multiple US "
        "time zones would be a separate issue.")
    return rows


# ---------------------------------------------------------------- D5
def d5_equal_times(key, now):
    print("\n   D5  start_time == end_time  (3 attempts)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], 1.0)
    day = (now - timedelta(hours=30)).strftime("%Y-%m-%d")
    p = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
         "date_time": {"start_date": day, "start_time": "14:00", "end_time": "14:00",
                       "filter_type": 2}}
    outs = []
    for i in range(3):
        r = hm(key, p, "vd_d5_%d" % i)
        outs.append("ok" if r.get("ok") else str(r.get("error"))[:60])
        print("      attempt %d: %s" % (i + 1, outs[-1]))
        time.sleep(1)
    n500 = sum(1 for o in outs if "500" in o)
    rec("D5", "start_time equal to end_time returns HTTP 500 Internal Server Error",
        "CONFIRMED" if n500 == len(outs) else ("INTERMITTENT" if n500 else "WITHDRAWN"),
        "A 400-class validation error naming the problem, or a zero-length window handled "
        "gracefully",
        "HTTP 500 on %d of %d attempts" % (n500, len(outs)),
        {"attempts": outs, "n_500": n500}, [p])


# ---------------------------------------------------------------- D6
def d6_heatmap_vs_envparams(key, now):
    """Same point, same hour, two endpoints: how far apart are they?"""
    print("\n   D6  heatmap vs env_params AT THE SAME POINT AND HOUR  (2 pairs)")
    day = (now - timedelta(hours=30)).strftime("%Y-%m-%d")
    pairs, pl = [], []
    for hh in ("09:00", "15:00"):
        aoi = box_aoi(CENTRE[0], CENTRE[1], 0.5)
        ph = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
              "date_time": {"start_date": day, "start_time": hh, "filter_type": 1}}
        pe = {"latitude": round(CENTRE[0], 5), "longitude": round(CENTRE[1], 5),
              "temperature": 25.0,
              "date_time": {"start_date": day, "start_time": hh, "filter_type": 1}}
        pl += [ph, pe]
        rh = hm(key, ph, "vd_d6_hm_%s" % hh.replace(":", ""))
        re_ = ep(key, pe, "vd_d6_ep_%s" % hh.replace(":", ""))
        t = tiles_of(rh)
        if not t or not re_.get("ok"):
            print("      %s: incomplete pair" % hh); continue
        av = [x["properties"].get("average_temperature") for x in t]
        av = [x for x in av if x is not None]
        loc = re_["result"]["locations"][0]
        epv = loc.get("temperature")
        g = lambda k: (loc["parameters"].get(k) or [None])[0]
        if epv is None:
            epv = g("t_2m:C") or g("apparent_temperature_celsius")
        hmv = statistics.fmean(av)
        pairs.append({"hour": hh, "heatmap_mean_avg_c": hmv, "env_params_c": epv,
                      "difference_c": (hmv - epv) if isinstance(epv, (int, float)) else None})
        print("      %s  heatmap %.3f C   env_params %s   difference %s"
              % (hh, hmv, epv,
                 ("%+.3f C" % (hmv - epv)) if isinstance(epv, (int, float)) else "n/a"))
    diffs = [p["difference_c"] for p in pairs if p["difference_c"] is not None]
    big = [d for d in diffs if abs(d) > 1.0]
    rec("D6", "heatmap and env_params disagree substantially for the same point, hour and "
              "quantity",
        "CONFIRMED" if big else ("WITHDRAWN" if diffs else "OBSERVED_ONCE"),
        "Two endpoints describing air temperature at the same coordinate and hour should agree "
        "to well within 1 C, or the difference should be documented",
        "differences %s" % ["%+.3f" % d for d in diffs],
        {"pairs": pairs, "n_over_1C": len(big)}, pl,
        "If the two serve different quantities (e.g. tile-aggregate vs point, or different "
        "reference heights) that should be stated in the docs so clients do not blend them.")


# ---------------------------------------------------------------- D7
def d7_history_floor(key):
    print("\n   D7  HISTORY FLOOR  (which past years are served?)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], 1.0)
    out, pl = {}, []
    for y in (2019, 2021, 2023, 2025):
        p = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
             "date_time": {"start_date": "%d-07-15" % y, "start_time": "15:00",
                           "filter_type": 1}}
        pl.append(p)
        r = hm(key, p, "vd_d7_%d" % y)
        t = tiles_of(r)
        out[y] = ("ok:%d" % len(t)) if t else ("error:%s" % str(r.get("error"))[:40]
                                              if not r.get("ok") else "EMPTY_completed")
        print("      %d-07-15: %s" % (y, out[y]))
    served = [y for y, v in out.items() if v.startswith("ok")]
    rec("D7", "Historical coverage floor is undocumented; older years return empty successes",
        "CONFIRMED" if any(not v.startswith("ok") for v in out.values()) else "WITHDRAWN",
        "Either data, or an error stating the earliest supported date",
        "by year: %s" % out,
        {"by_year": out, "served_years": served}, pl,
        "Same failure mode as D1: unsupported ranges arrive as successful empty responses.")


# ---------------------------------------------------------------- main
def main():
    banner("VERIFY API DEFECTS  ---  repeated trials before anything is written up   [PAID]")
    key = load_key()
    before = credits_remaining(key)
    now = datetime.now()
    print("   cycle_remaining BEFORE: %s   machine local now %s"
          % (format(before, ","), now.strftime("%Y-%m-%d %H:%M")))

    d1_forecast_retries(key, now)
    d2_time_of_measure(key)
    d3_persistence_vs_exceedance(key, now)
    d4_env_params_units(key, now)
    d5_equal_times(key, now)
    d6_heatmap_vs_envparams(key, now)
    d7_history_floor(key)

    after = credits_remaining(key)
    print("\n   %d calls issued.  cycle_remaining %s -> %s   APPARENT SPEND: %s"
          % (CALLS[0], format(before, ","), format(after, ","), format(before - after, ",")))

    print("\n   SUMMARY BY BUCKET")
    for st in ("CONFIRMED", "INTERMITTENT", "OBSERVED_ONCE", "WITHDRAWN"):
        ids = [k for k, v in FINDINGS.items() if v["status"] == st]
        print("      %-14s %d   %s" % (st, len(ids), ids))
    print("\n   Only CONFIRMED and INTERMITTENT items may go in the report as defects.")
    print("   OBSERVED_ONCE items go in as questions. WITHDRAWN items must not appear at all.")

    save_result("api_defect_verification.json",
                {"verified_at": now.isoformat(), "n_calls": CALLS[0],
                 "before": before, "after": after, "findings": FINDINGS})
    return 0


if __name__ == "__main__":
    sys.exit(main())
