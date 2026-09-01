# -*- coding: utf-8 -*-
"""PROBE  ---  what do /v1/satellite and /v1/streetview actually RETURN?   [PAID: 2 calls]

Authorised by the user for exactly two calls, one per endpoint, at the project site.

WHY
    The OpenAPI spec (hackathon/hackathon/openapi.json) documents six data endpoints. We have only
    ever used /v1/heatmap and /v1/env_params. Both response schemas in the spec are literally `{}`,
    so the only way to learn the shape is to call them once.

    The specific question: does either endpoint return BUILDING GEOMETRY? solver.demo_site() is
    currently a hand-written layout -- building positions, exhaust locations, intake location. If
    FortyGuard can supply that geometry, the agent could derive its own site layout from FortyGuard
    data instead of a human drawing it, which removes a hand-specified input and puts FortyGuard
    inside the agentic path rather than only at the boundary condition.

SAFETY
    * The key is read via common.load_key() and NEVER printed, logged, or written to a fixture.
    * Structure only is printed: keys, types, container sizes. Long strings (base64 imagery) are
      reported as byte lengths, never dumped.
    * Every raw response is saved under results/fixtures/ so this never has to be paid for twice.
    * Handles BOTH sync and async replies. common.submit_poll() assumes an activity_id and would
      poll /status/None for 420 s if these endpoints answer synchronously.
    * cycle_remaining recorded before and after. NOTE: that meter is frozen, so spend probably
      cannot be observed here at all. Recorded anyway.
"""
import json
import os
import sys
import time
import urllib.request

from common import banner, FIXTURES, V1, _headers, credits_remaining, load_key, save_result

SITE_LAT, SITE_LON = 39.0100, -77.4460       # common.TARGET_CENTRE, the project site all along
SAT_DATE = "2026-06-23"                      # a day already known to hold data for this AOI
POLL_MAX_S = 240
POLL_WAIT_S = 8
MAX_STR_PRINT = 120


def describe(obj, indent=6, depth=0, path="$"):
    """Print STRUCTURE only. Never dumps a long string -- base64 imagery is reported by length."""
    pad = " " * indent
    if depth > 4:
        print("%s... (depth limit)" % pad)
        return
    if isinstance(obj, dict):
        print("%sdict with %d keys: %s" % (pad, len(obj), list(obj.keys())[:14]))
        for k, v in list(obj.items())[:14]:
            print("%s  .%s ->" % (pad, k), end=" ")
            brief(v, indent + 4, depth + 1, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        print("%slist of %d" % (pad, len(obj)))
        if obj:
            print("%s  [0] ->" % pad, end=" ")
            brief(obj[0], indent + 4, depth + 1, path + "[0]")
    else:
        brief(obj, indent, depth, path)


def brief(v, indent, depth, path):
    if isinstance(v, dict):
        print("dict(%d keys) %s" % (len(v), list(v.keys())[:10]))
        if depth <= 2:
            describe(v, indent + 2, depth + 1, path)
    elif isinstance(v, list):
        print("list(%d)" % len(v))
        if v and depth <= 2:
            print("%s[0] ->" % (" " * (indent + 2)), end=" ")
            brief(v[0], indent + 4, depth + 1, path + "[0]")
    elif isinstance(v, str):
        if len(v) > MAX_STR_PRINT:
            print("str, %d chars  [NOT PRINTED -- likely encoded imagery]" % len(v))
        else:
            print("str %r" % v)
    else:
        print("%s %r" % (type(v).__name__, v))


def call(key, endpoint, payload, tag):
    """POST, then poll only if an activity_id came back. Saves the raw result either way."""
    print("\n   POST /v1/%s" % endpoint)
    print("      payload: %s" % json.dumps(payload))
    t0 = time.time()
    try:
        req = urllib.request.Request("%s/%s" % (V1, endpoint),
                                     data=json.dumps(payload).encode(), headers=_headers(key))
        raw = urllib.request.urlopen(req, timeout=90).read()
        resp = json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:600]
        print("      HTTP %s -- %s" % (e.code, body))
        return {"error": "http %s" % e.code, "body": body}
    except Exception as e:
        print("      submit failed: %s" % str(e)[:250])
        return {"error": str(e)[:250]}

    with open(os.path.join(FIXTURES, "%s_submit.json" % tag), "w") as f:
        json.dump(resp, f, indent=1, default=str)
    print("      submit reply in %.1f s" % (time.time() - t0))
    describe(resp)

    aid = None
    if isinstance(resp, dict):
        aid = (resp.get("data") or {}).get("activity_id") if isinstance(resp.get("data"), dict) \
            else resp.get("activity_id")
    if not aid:
        print("      no activity_id -- treating the submit reply as the whole result (synchronous)")
        return {"ok": True, "sync": True, "result": resp}

    print("      activity_id present -> polling /v1/status/%s" % str(aid)[:12] + "...")
    while time.time() - t0 < POLL_MAX_S:
        try:
            r = urllib.request.urlopen(
                urllib.request.Request("%s/status/%s" % (V1, aid), headers=_headers(key)), timeout=90)
            jd = json.loads(r.read())
        except Exception as e:
            print("         poll retry (%s)" % str(e)[:80])
            time.sleep(POLL_WAIT_S)
            continue
        data = jd.get("data") if isinstance(jd.get("data"), dict) else {}
        st = str(data.get("status") or jd.get("message") or "").lower()
        print("         status=%s  t=%.0fs" % (st or "?", time.time() - t0))
        if st == "completed":
            res = data.get("result", jd)
            with open(os.path.join(FIXTURES, "%s.json" % tag), "w") as f:
                json.dump(res, f, default=str)
            return {"ok": True, "sync": False, "secs": round(time.time() - t0, 1), "result": res}
        if st in ("processing", "pending", "queued", "in progress", "in_progress", ""):
            time.sleep(POLL_WAIT_S)
            continue
        with open(os.path.join(FIXTURES, "%s_terminal.json" % tag), "w") as f:
            json.dump(jd, f, indent=1, default=str)
        return {"error": st, "raw": jd}
    return {"error": "timeout after %ds" % POLL_MAX_S}


def main():
    banner("PROBE  /v1/satellite and /v1/streetview response shapes   [PAID: 2 calls, authorised]")
    print("   site %.4f, %.4f (the project AOI centre). Key is never printed." % (SITE_LAT, SITE_LON))

    key = load_key()
    try:
        before = credits_remaining(key)
        print("   cycle_remaining BEFORE: %s" % format(before, ","))
    except Exception as e:
        before = None
        print("   could not read credits before: %s" % str(e)[:120])

    out = {}

    # ---- 1. satellite segmentation, finest granularity so building-scale detail is possible ----
    sat_payload = {"sat": {"latitude": SITE_LAT, "longitude": SITE_LON},
                   "date_time": {"start_date": SAT_DATE, "filter_type": 3},
                   "granularity": 60}
    out["satellite"] = call(key, "satellite", sat_payload, "probe_satellite")
    if out["satellite"].get("ok"):
        print("\n   ---- SATELLITE RESULT STRUCTURE ----")
        describe(out["satellite"]["result"])

    # ---- 2. streetview segmentation, level view forward ----
    sv_payload = {"latitude": SITE_LAT, "longitude": SITE_LON,
                  "vertical_angle": 0, "horizontal_angle": 0, "back_view": False}
    out["streetview"] = call(key, "streetview", sv_payload, "probe_streetview")
    if out["streetview"].get("ok"):
        print("\n   ---- STREETVIEW RESULT STRUCTURE ----")
        describe(out["streetview"]["result"])

    after = None
    try:
        after = credits_remaining(key)
        print("\n   cycle_remaining AFTER: %s" % format(after, ","))
        if before is not None:
            print("   apparent spend: %s  (that meter is frozen, so 0 here"
                  % format(before - after, ","))
            print("   does NOT prove the calls were free)")
    except Exception as e:
        print("\n   could not read credits after: %s" % str(e)[:120])

    # what we actually wanted to know
    print("\n   THE QUESTION THIS PROBE EXISTS TO ANSWER")
    for name in ("satellite", "streetview"):
        r = out[name]
        if not r.get("ok"):
            print("      %-11s NO USABLE RESPONSE (%s)" % (name, r.get("error")))
            continue
        blob = json.dumps(r["result"], default=str).lower()
        hits = [w for w in ("building", "footprint", "polygon", "height", "roof", "geometry",
                            "class", "segment", "mask", "label", "surface", "vegetation",
                            "impervious", "coordinates", "area") if w in blob]
        print("      %-11s keys=%s" % (name, list(r["result"].keys())[:10]
                                       if isinstance(r["result"], dict) else type(r["result"]).__name__))
        print("      %-11s geometry-related terms present: %s" % ("", hits or "NONE"))

    save_result("probe_endpoints.json", {
        "authorised": "user, exactly two calls",
        "site": [SITE_LAT, SITE_LON],
        "sat_payload": sat_payload, "sv_payload": sv_payload,
        "credits_before": before, "credits_after": after,
        "credits_note": "that meter is frozen; a zero difference does not prove zero spend",
        "satellite": {k: v for k, v in out["satellite"].items() if k != "result"},
        "streetview": {k: v for k, v in out["streetview"].items() if k != "result"},
        "fixtures": "results/fixtures/probe_satellite*.json, probe_streetview*.json",
    })
    print("\n   raw responses saved under results/fixtures/ -- never pay for this twice")
    return 0


if __name__ == "__main__":
    sys.exit(main())
