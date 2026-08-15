# -*- coding: utf-8 -*-
"""PROBE 2  ---  /v1/heat_intelligence, plus a FREE resolution of the `threshold` field-name question.

Authorised by the user 2026-08-16.

TWO INDEPENDENT JOBS
  A. /v1/heat_intelligence -- the last of FortyGuard's six data endpoints we have never called.
     [PAID: 1 call] All five `analysis` types are requested in the single call (the schema allows
     maxItems 5) so one payment returns the maximum information. The enum is
     geographic | environmental | urban | events | anthropogenic, and `anthropogenic` -- human-caused
     heat -- is the one that could matter to a recirculation problem, because a neighbouring waste-heat
     source is exactly what our solver models.

  B. Does /v1/heatmap recognise `threshold` or `threshold_temperature`?  [FREE]
     verify_api_defects.py:172 sends `threshold_temperature`, but the OpenAPI spec names the field
     `threshold` (number|null) with a companion `direction` (above/below) we never send. FastAPI
     ignores unknown body fields by default, so the exceedance/persistence comparison behind defect D3
     may have run against a DEFAULT threshold rather than the 30.0 C it intended.

     The trick that makes this free: send `granularity: 7`, which is outside the documented enum
     [60, 80, 100], so the request can NEVER validate and therefore can never create a billable task.
     FastAPI reports ALL validation errors at once, so whichever of the two field names is recognised
     will appear in the error list -- and an unrecognised one will either be absent (extras ignored)
     or flagged as extra_forbidden. Either outcome is decisive.

SAFETY
  * Key read via common.load_key(), NEVER printed.
  * Responses saved to results/fixtures/ so nothing is paid for twice.
  * Structure printed, not raw payloads; long strings reported by length.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

from common import banner, box_aoi, credits_remaining, load_key, save_result, FIXTURES, V1, _headers

SITE_LAT, SITE_LON = 39.0100, -77.4460
PAST_DATE = "2026-06-23"          # `date` is documented "past or present only"
INPUT_TEMP_C = 30.0              # this endpoint takes a temperature as an INPUT, like env_params
# The OpenAPI spec advertises maxItems: 5. The SERVER enforces 2 for this plan:
#   HTTP 400 "Heat Intelligence analysis types exceed current model limit of 2 types for premium plan"
# (measured 2026-08-16; the 400 fires before a task is created, so it is not billable.)
# Of the five available -- geographic | environmental | urban | events | anthropogenic -- these two are
# the ones that could inform a plume/recirculation model: `anthropogenic` is human-caused heat, i.e.
# exactly the neighbouring waste-heat source our solver models, and `urban` is the built environment
# that sets surface roughness and the heat-island background.
ANALYSES = ["anthropogenic", "urban"]
SKIP_JOB_B = "--skip-b" in sys.argv        # job B is free and already conclusive; allow skipping it
POLL_MAX_S = 240
POLL_WAIT_S = 8


def show(obj, indent=6, depth=0):
    pad = " " * indent
    if depth > 5:
        print("%s... (depth limit)" % pad)
        return
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:24]:
            if isinstance(v, dict):
                print("%s%s: dict(%d) %s" % (pad, k, len(v), list(v.keys())[:8]))
                show(v, indent + 3, depth + 1)
            elif isinstance(v, list):
                print("%s%s: list(%d)" % (pad, k, len(v)))
                if v:
                    if isinstance(v[0], (dict, list)):
                        show(v[0], indent + 3, depth + 1)
                    else:
                        print("%s   e.g. %r" % (pad, v[0]))
            elif isinstance(v, str) and len(v) > 200:
                print("%s%s: str, %d chars -- first 200: %s" % (pad, k, len(v), v[:200]))
            else:
                print("%s%s: %r" % (pad, k, v))
    elif isinstance(obj, list):
        print("%slist(%d)" % (pad, len(obj)))
        if obj:
            show(obj[0], indent + 3, depth + 1)
    else:
        print("%s%r" % (pad, obj))


def post(key, endpoint, payload):
    """Returns (http_status, parsed_body). Never raises on a 4xx -- a 422 is the point of job B."""
    try:
        req = urllib.request.Request("%s/%s" % (V1, endpoint),
                                     data=json.dumps(payload).encode(), headers=_headers(key))
        r = urllib.request.urlopen(req, timeout=90)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"_raw": body[:1200]}
    except Exception as e:
        return None, {"_error": str(e)[:250]}


def poll(key, aid, tag):
    t0 = time.time()
    while time.time() - t0 < POLL_MAX_S:
        try:
            jd = json.loads(urllib.request.urlopen(
                urllib.request.Request("%s/status/%s" % (V1, aid), headers=_headers(key)),
                timeout=90).read())
        except Exception as e:
            print("         poll retry (%s)" % str(e)[:70])
            time.sleep(POLL_WAIT_S)
            continue
        data = jd.get("data") if isinstance(jd.get("data"), dict) else {}
        st = str(data.get("status") or jd.get("message") or "").lower()
        print("         status=%s  t=%.0fs" % (st or "?", time.time() - t0))
        if st == "completed":
            res = data.get("result", jd)
            json.dump(res, open(os.path.join(FIXTURES, "%s.json" % tag), "w"), default=str)
            return res
        if st in ("processing", "pending", "queued", "in progress", "in_progress", ""):
            time.sleep(POLL_WAIT_S)
            continue
        return {"_terminal_status": st, "_raw": jd}
    return {"_error": "timeout after %ds" % POLL_MAX_S}


def job_b_threshold_fieldname(key):
    """FREE. granularity 7 is outside the enum, so this can never become a billable task."""
    print("\n" + "-" * 74)
    print("   JOB B  [FREE]  which field name does /v1/heatmap actually recognise?")
    print("-" * 74)
    aoi = box_aoi(SITE_LAT, SITE_LON, 2.0)
    payload = {
        "polygon_aoi": aoi,
        "date_time": {"start_date": PAST_DATE, "start_time": "15:00", "end_time": "17:00",
                      "filter_type": 2},
        "granularity": 7,                     # INVALID on purpose -> guarantees a 422, so no charge
        "analytic_type": "exceedance",
        "threshold": "not-a-number",          # spec name, wrong type on purpose
        "threshold_temperature": "not-a-number",   # the name our code has been sending
        "direction": "above",
    }
    status, body = post(key, "heatmap", payload)
    print("      HTTP %s   (a 422 means no task was created, so no credits)" % status)
    json.dump({"payload_sent": payload, "status": status, "body": body},
              open(os.path.join(FIXTURES, "probe_threshold_fieldname.json"), "w"),
              indent=1, default=str)

    detail = body.get("detail") if isinstance(body, dict) else None
    fields = []
    if isinstance(detail, list):
        print("      validation errors returned: %d" % len(detail))
        for d in detail:
            loc = ".".join(str(x) for x in (d.get("loc") or []))
            print("         loc=%-42s type=%-22s msg=%s"
                  % (loc, d.get("type"), str(d.get("msg"))[:60]))
            fields.append(loc)
    else:
        print("      unexpected body shape:")
        show(body)

    joined = " ".join(fields)
    verdict = {
        "threshold_recognised": "threshold" in joined and "threshold_temperature" not in joined.replace(
            "threshold_temperature", ""),
        "raw_fields": fields,
    }
    saw_threshold = any(f.endswith("threshold") for f in fields)
    saw_thr_temp = any("threshold_temperature" in f for f in fields)
    print("\n      `threshold` appears in the error list          : %s" % saw_threshold)
    print("      `threshold_temperature` appears in the list    : %s" % saw_thr_temp)
    if saw_threshold and not saw_thr_temp:
        concl = ("CONFIRMED DEFECT IN OUR CODE: the API validates `threshold` and silently IGNORES "
                 "`threshold_temperature`. verify_api_defects.py:172 therefore never applied the "
                 "30.0 C threshold it intended, and defect D3's exceedance/persistence comparison "
                 "must be re-run with the correct field name before being quoted.")
    elif saw_thr_temp:
        concl = ("`threshold_temperature` IS recognised (an alias, or the spec is out of date). Our "
                 "existing D3 test stands as run.")
    else:
        concl = ("Neither name appeared -- the 422 fired only on granularity and extras are ignored "
                 "silently. That still means an unknown field is dropped without warning, so the "
                 "field name our code sends cannot be assumed to have taken effect. Inconclusive on "
                 "aliasing; conclusive that silent-drop is the behaviour.")
    print("\n      CONCLUSION: %s" % concl)
    verdict["conclusion"] = concl
    verdict["saw_threshold"] = saw_threshold
    verdict["saw_threshold_temperature"] = saw_thr_temp
    verdict["http_status"] = status
    return verdict


def job_a_heat_intelligence(key):
    print("\n" + "-" * 74)
    print("   JOB A  [PAID: 1 call]  /v1/heat_intelligence, all five analyses in one request")
    print("-" * 74)
    payload = {"latitude": SITE_LAT, "longitude": SITE_LON, "temperature": INPUT_TEMP_C,
               "date": PAST_DATE, "analysis": ANALYSES}
    print("      payload: %s" % json.dumps(payload)[:200])
    status, body = post(key, "heat_intelligence", payload)
    print("      HTTP %s" % status)
    json.dump({"payload_sent": payload, "status": status, "body": body},
              open(os.path.join(FIXTURES, "probe_heatintel_submit.json"), "w"),
              indent=1, default=str)
    if status != 200:
        print("      submit did not succeed -- structure of the error:")
        show(body)
        return {"status": status, "body": body}

    show(body)
    aid = (body.get("data") or {}).get("activity_id") if isinstance(body.get("data"), dict) else None
    if not aid:
        print("      no activity_id -- treating the reply as the whole result (synchronous)")
        result = body
    else:
        print("      polling /v1/status/%s..." % str(aid)[:12])
        result = poll(key, aid, "probe_heatintel")

    print("\n      ---- RESULT STRUCTURE ----")
    show(result)

    blob = json.dumps(result, default=str).lower()
    terms = [w for w in ("building", "waste heat", "anthropogenic", "industrial", "data cent",
                         "source", "land use", "impervious", "albedo", "roughness", "population",
                         "traffic", "vegetation", "urban heat", "event", "elevation", "slope")
             if w in blob]
    print("\n      terms present that would matter to a plume/recirculation model: %s"
          % (terms or "NONE"))
    return {"status": status, "activity_id": aid, "result_keys":
            list(result.keys()) if isinstance(result, dict) else type(result).__name__,
            "relevant_terms": terms}


def main():
    banner("PROBE 2  /v1/heat_intelligence [1 PAID] + `threshold` field name [FREE]")
    key = load_key()
    try:
        before = credits_remaining(key)
        print("   cycle_remaining BEFORE: %s   (frozen since 2026-07-19, so spend is unobservable)"
              % format(before, ","))
    except Exception as e:
        before = None
        print("   credits before unavailable: %s" % str(e)[:100])

    if SKIP_JOB_B:
        print("\n   JOB B skipped (--skip-b): already conclusive, see "
              "results/fixtures/probe_threshold_fieldname.json")
        b = {"skipped": True}
    else:
        b = job_b_threshold_fieldname(key)   # free first, so a failure here costs nothing
    a = job_a_heat_intelligence(key)

    after = None
    try:
        after = credits_remaining(key)
        print("\n   cycle_remaining AFTER: %s" % format(after, ","))
    except Exception:
        pass

    save_result("probe_heat_intelligence.json", {
        "authorised": "user, 2026-08-16 -- heat_intelligence probe plus the threshold field-name check",
        "site": [SITE_LAT, SITE_LON], "date": PAST_DATE,
        "credits_before": before, "credits_after": after,
        "credits_note": "meter frozen since 2026-07-19; a zero difference does not prove zero spend",
        "job_a_heat_intelligence": a,
        "job_b_threshold_fieldname": b,
    })
    print("\n   raw responses in results/fixtures/probe_heatintel*.json and "
          "probe_threshold_fieldname.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
