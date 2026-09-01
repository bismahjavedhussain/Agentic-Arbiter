# -*- coding: utf-8 -*-
"""N-15  ---  is the forecast gone, or is this key degraded to history-only?   PAID.

THE QUESTION
    N-14 found that data stops at roughly the current wall-clock moment: every window from -30 h
    to +2 h returns tiles, and +4 h onward returns ZERO TILES with status completed. The diurnal
    curve keyed on requested start_time is textbook for Ashburn (21.1 C at 04:00-06:00 rising to
    33.8 C at 16:00-18:00), so start_time is being read as site-local and the request builder is
    not at fault.

    But a 12-hour forecast demonstrably WORKED on this same key earlier: fb_1_FCST_12H.json
    holds 6,875 tiles, and forecast-vs-outcome residuals were measured from it (bias +0.349 C,
    sd 0.150), which is only possible if it was a real forecast that later had an outcome.

    So something changed. Three candidates, very different consequences:

      A KEY DEGRADED. The key reports active: false with a closed billing cycle. An
        inactive key may be served history only. -> design intact; forecasts unverifiable until
        a live key on Aug 18.
      B TRANSIENT OUTAGE of the forecast service. -> design intact; retest later.
      C THE FORECAST PRODUCT CHANGED. -> the design's central assumption is gone and INTAKE
        cannot anticipate anything.

WHAT DISCRIMINATES THEM
    1. Dump the FULL usage/status response, not just cycle_remaining_credits. Any active flag,
       plan, tier or expiry field speaks directly to A. (Key value is never printed.)
    2. Try a future hour with filter_type 1 as well as 2 -- maybe forecasts only ever came
       through one filter shape and earlier work never isolated that.
    3. Try env_params for a FUTURE timestamp. It served future values earlier
       (fb_10_EP_FUTURE.json). If env_params still forecasts while heatmap does not, the
       forecast product exists and the limitation is specific to heatmap; if neither does, that
       points hard at A.
    4. Try a future hour on a DIFFERENT metro, to rule out an AOI-specific gap.

None of these can be inferred. They have to be asked.
"""
import json, sys, urllib.request
from datetime import datetime, timedelta

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    V1, _headers, assert_non_empty)

CENTRE = (39.0100, -77.4460)
ALT_CENTRE = (32.7790, -96.8080)      # Dallas: different metro, rules out an AOI-local gap


def full_usage(key):
    """Dump every field the usage endpoint returns. The key itself is never printed."""
    req = urllib.request.Request("%s/system/fetch-api-key-usage" % V1,
                                 data=json.dumps({"api_key": key}).encode(),
                                 headers=_headers(key))
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def redact(obj, key):
    s = json.dumps(obj, indent=1, default=str)
    return s.replace(key, "<REDACTED>")


def main():
    banner("N-15  Forecast gone, or key degraded to history-only?   [PAID]")
    key = load_key()
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    print("   machine local now: %s" % now.strftime("%Y-%m-%d %H:%M"))

    # ---- 1. what does the account actually say? --------------------------
    print("\n   1. FULL USAGE / STATUS RESPONSE  (key redacted)")
    try:
        u = full_usage(key)
        print(redact(u, key)[:2600])
    except Exception as e:
        u = {"error": str(e)[:200]}
        print("      failed: %s" % u["error"])

    before = credits_remaining(key)
    results = {}

    # ---- 2. heatmap, future hour, both filter shapes ---------------------
    fut = now + timedelta(hours=6)
    aoi = box_aoi(CENTRE[0], CENTRE[1], 1.0)
    print("\n   2. HEATMAP for a FUTURE hour (%s %s), both filter shapes"
          % (fut.strftime("%Y-%m-%d"), fut.strftime("%H:00")))

    for ft, extra in ((1, {}), (2, {"end_time": (fut + timedelta(hours=2)).strftime("%H:00")})):
        dt = {"start_date": fut.strftime("%Y-%m-%d"), "start_time": fut.strftime("%H:00"),
              "filter_type": ft}
        dt.update(extra)
        r = submit_poll(key, "heatmap", {"polygon_aoi": aoi, "granularity": 100,
                                         "analytic_type": "tcm", "date_time": dt},
                        "n15_hm_ft%d" % ft)
        if not r.get("ok"):
            results["heatmap_ft%d" % ft] = "error: %s" % str(r.get("error"))[:70]
        else:
            ok, why = assert_non_empty(r["result"])
            results["heatmap_ft%d" % ft] = ("ok: %s" % why) if ok else "EMPTY: %s" % why
        print("      filter_type=%d -> %s" % (ft, results["heatmap_ft%d" % ft]))

    # ---- 3. env_params for a future timestamp ---------------------------
    print("\n   3. ENV_PARAMS for the same FUTURE hour (it served future values earlier)")
    p = {"latitude": round(CENTRE[0], 5), "longitude": round(CENTRE[1], 5), "temperature": 25.0,
         "date_time": {"start_date": fut.strftime("%Y-%m-%d"), "start_time": fut.strftime("%H:00"),
                       "filter_type": 1}}
    r = submit_poll(key, "env_params", p, "n15_ep_future")
    if not r.get("ok"):
        results["env_params_future"] = "error: %s" % str(r.get("error"))[:70]
        print("      %s" % results["env_params_future"])
    else:
        ok, why = assert_non_empty(r["result"])
        results["env_params_future"] = ("ok: %s" % why) if ok else "EMPTY: %s" % why
        print("      %s" % results["env_params_future"])
        if ok:
            loc = r["result"]["locations"][0]
            g = lambda k: (loc["parameters"].get(k) or [None])[0]
            print("      wet_bulb %s  RH %s  apparent %s  elevation %s"
                  % (g("wet_bulb_temperature_celsius"), g("relative_humidity_percent"),
                     g("apparent_temperature_celsius"), loc.get("elevation")))

    # ---- 4. a different metro, same future hour -------------------------
    print("\n   4. HEATMAP future hour over a DIFFERENT metro (Dallas) to rule out an AOI gap")
    aoi2 = box_aoi(ALT_CENTRE[0], ALT_CENTRE[1], 1.0)
    r = submit_poll(key, "heatmap",
                    {"polygon_aoi": aoi2, "granularity": 100, "analytic_type": "tcm",
                     "date_time": {"start_date": fut.strftime("%Y-%m-%d"),
                                   "start_time": fut.strftime("%H:00"), "filter_type": 1}},
                    "n15_hm_dallas_future")
    if not r.get("ok"):
        results["heatmap_dallas_future"] = "error: %s" % str(r.get("error"))[:70]
    else:
        ok, why = assert_non_empty(r["result"])
        results["heatmap_dallas_future"] = ("ok: %s" % why) if ok else "EMPTY: %s" % why
    print("      %s" % results["heatmap_dallas_future"])

    # ---- 5. control: a PAST hour must still work ------------------------
    past = now - timedelta(hours=6)
    print("\n   5. CONTROL - a PAST hour (%s) must still return data" % past.strftime("%H:00"))
    r = submit_poll(key, "heatmap",
                    {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
                     "date_time": {"start_date": past.strftime("%Y-%m-%d"),
                                   "start_time": past.strftime("%H:00"), "filter_type": 1}},
                    "n15_hm_past_control")
    if not r.get("ok"):
        results["heatmap_past_control"] = "error: %s" % str(r.get("error"))[:70]
    else:
        ok, why = assert_non_empty(r["result"])
        results["heatmap_past_control"] = ("ok: %s" % why) if ok else "EMPTY: %s" % why
    print("      %s" % results["heatmap_past_control"])

    after = credits_remaining(key)
    print("\n   cycle_remaining %s -> %s   APPARENT SPEND: %s"
          % (format(before, ","), format(after, ","), format(before - after, ",")))

    # ---- diagnosis -------------------------------------------------------
    any_future = any(str(v).startswith("ok") for k, v in results.items() if "future" in k)
    past_ok = str(results.get("heatmap_past_control", "")).startswith("ok")
    print("\n   DIAGNOSIS")
    print("      any FUTURE request returned data : %s" % any_future)
    print("      PAST control returned data       : %s" % past_ok)
    if any_future:
        print("      -> Forecasts DO still exist on this key. The N-14 empties are specific to the")
        print("         request shape or window that failed, not a loss of the forecast product.")
        print("         Identify the working shape and rebuild the request builder around it.")
    elif past_ok:
        print("      -> History works, every forecast path is empty. Consistent with hypothesis A")
        print("         (key degraded to history-only) or B (forecast outage). NOT evidence that")
        print("         the forecast product is gone: a 12 h forecast provably worked on this key")
        print("         earlier, and its residuals were measured. The design assumption")
        print("         cannot be VALIDATED again until a live key on Aug 18 -- record it as")
        print("         unverified-but-previously-demonstrated, and make it day-one call #1.")
    else:
        print("      -> Even the past control failed. The API or the key is broken right now;")
        print("         draw no conclusions about the forecast from this run at all.")

    save_result("n15_forecast_state.json", {
        "machine_now": now.isoformat(), "future_hour": fut.isoformat(),
        "usage_response": u, "probes": results,
        "any_future_ok": any_future, "past_control_ok": past_ok,
        "prior_evidence": "fb_1_FCST_12H.json: 6875-tile 12 h forecast, "
                          "residuals measured (bias +0.349 C, sd 0.150)",
        "before": before, "after": after})
    return 0


if __name__ == "__main__":
    sys.exit(main())
