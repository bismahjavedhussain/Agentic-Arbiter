"""DIAG-63 -- WHY DOES THE FORECAST LEG FAIL, AND IS IT THE FORECAST OR THE ACCOUNT?

Authorised by the user 2026-08-20: "check if the forecast request is working now ... If not, report
me the error that occurs", with credits explicitly not a constraint.

WHAT CHANGED, AND WHY THIS SCRIPT EXISTS
----------------------------------------
Until today the forecast leg failed as `HTTP 200` + `status: completed` + zero `features`, and was
BILLED 4,220 each time (HANDOFF section 4, and the report we wrote for FortyGuard). At 10:48 UTC
today it failed differently: **`status: failed`, and the meter did not move.** That is a materially
different signal -- and it is two of the three things we asked FortyGuard for (a non-`completed`
status on failure, and no billing for a result that carries no data).

But `submit_poll` reduces a terminal status to a single word, so "failed" is all we have. This
script captures the WHOLE payload.

THE EXPERIMENT, AND WHY IT HAS A CONTROL LEG
--------------------------------------------
A failing forecast call on its own cannot distinguish:

    (a) the forecast/future-window path is broken
    (b) the key, plan or daily quota is exhausted or revoked
    (c) the heatmap endpoint is down for everything
    (d) this particular AOI or granularity is being rejected

So two legs, identical in every field except the date:

    LEG A  FORECAST   today 14:00-16:00 site-local   -- the N-26 collector's exact request
    LEG B  CONTROL    a PAST window, same AOI/gran   -- historically works, most recently 08-19

If A fails and B succeeds, it is (a) and nothing else. If both fail, it is (b) or (c), and the
status payload will say which. **A diagnosis without a control leg is a guess with a log file.**

Every field of every response is saved to `results/diag63_forecast_failed_status.json`.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (load_key, credits_remaining, box_aoi, save_result, site_now, site_tz,  # noqa
                   utc_now, RESULTS, V1, SITE_TZ_NAME)
from datetime import timedelta

CENTRE = (39.0100, -77.4460)      # the committed N-26 centre, unchanged since 2026-08-12
SIDE_KM = 8.0
GRAN = 60
TARGET_HOUR = 14
WIN_H = 2
MAX_POLL_S = 420
POLL_WAIT_S = 8


def headers(key):
    return {"api-key": key, "Content-Type": "application/json"}


def window_for(date_obj):
    """The collector's window: a 2-hour block at 14:00 site-local, expressed as the API wants it."""
    return {"start_date": date_obj.isoformat(),
            "start_time": "%02d:00" % TARGET_HOUR,
            "end_time": "%02d:00" % (TARGET_HOUR + WIN_H),
            "filter_type": 2}


def submit_and_watch(key, dt_fields, label):
    """Submit one heatmap request and record EVERY distinct status payload until terminal.

    Returns a dict describing what happened. Never raises: a diagnostic that dies on the thing it
    is diagnosing tells you nothing.
    """
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
               "date_time": dt_fields}
    out = {"label": label, "request_date_time": dt_fields, "granularity": GRAN,
           "analytic_type": "tcm", "aoi_centre": list(CENTRE), "side_km": SIDE_KM}
    t0 = time.time()

    print("\n" + "=" * 78)
    print("%s -- submitting  %s %s-%s  (filter_type %s)"
          % (label, dt_fields["start_date"], dt_fields["start_time"], dt_fields["end_time"],
             dt_fields["filter_type"]))
    print("=" * 78)

    # ---- the submit itself. Capture the HTTP error BODY, not just the code: FortyGuard puts the
    # reason in the body and a bare "HTTP Error 400: Bad Request" would hide it.
    try:
        req = urllib.request.Request("%s/heatmap" % V1, data=json.dumps(payload).encode(),
                                     headers=headers(key))
        raw = urllib.request.urlopen(req, timeout=90).read()
        resp = json.loads(raw)
        out["submit_http"] = 200
        out["submit_response"] = resp
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        out["submit_http"] = e.code
        out["submit_error_body"] = body
        print("   SUBMIT FAILED  HTTP %s" % e.code)
        print("   body: %s" % body)
        return out
    except Exception as e:
        out["submit_http"] = None
        out["submit_exception"] = str(e)[:400]
        print("   SUBMIT RAISED  %s" % str(e)[:300])
        return out

    aid = (resp.get("data") or {}).get("activity_id")
    out["activity_id"] = aid
    print("   submit OK, activity_id %s" % aid)
    if not aid:
        print("   NO ACTIVITY ID IN THE RESPONSE -- full body follows")
        print("   %s" % json.dumps(resp)[:1200])
        return out

    # ---- poll. Record each DISTINCT status payload, so a transition sequence is visible rather
    # than only the final word.
    seen, transitions, n_polls = set(), [], 0
    terminal = None
    while time.time() - t0 < MAX_POLL_S:
        n_polls += 1
        try:
            r = urllib.request.urlopen(
                urllib.request.Request("%s/status/%s" % (V1, aid), headers=headers(key)),
                timeout=90)
            code, jd = r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            code, jd = e.code, {"_http_error_body": e.read().decode("utf-8", "replace")[:900]}
        except Exception as e:
            time.sleep(POLL_WAIT_S)
            continue

        status = str((jd.get("data") or {}).get("status") or jd.get("message") or "?").lower()
        # A payload is "new" if its status changed -- keeps the log short without losing the shape.
        if status not in seen:
            seen.add(status)
            snap = {"at_s": round(time.time() - t0, 1), "http": code, "status": status,
                    "payload": jd}
            transitions.append(snap)
            print("   [%6.1fs] poll %-3d http %s  status=%s"
                  % (time.time() - t0, n_polls, code, status))
            # The whole point of the run: print the terminal payload in full.
            if status not in ("processing", "pending", "queued", "in progress", "?"):
                print("   ---- FULL PAYLOAD ----")
                print(json.dumps(jd, indent=1, default=str)[:3000])
                print("   ----------------------")

        if status == "completed":
            res = (jd.get("data") or {}).get("result") or {}
            feats = ((res.get("map_data") or {}).get("features"))
            n = len(feats) if feats is not None else None
            if n:
                terminal = {"status": "completed", "tiles": n}
                print("   COMPLETED with %s tiles" % format(n, ","))
                break
            # completed-but-empty is the OLD failure mode; keep polling per FortyGuard's guidance
            terminal = {"status": "completed", "tiles": 0}
        elif status in ("failed", "error", "cancelled", "canceled", "expired"):
            terminal = {"status": status}
            print("   TERMINAL FAILURE STATUS: %s" % status)
            break
        time.sleep(POLL_WAIT_S)

    out.update({"polls": n_polls, "elapsed_s": round(time.time() - t0, 1),
                "distinct_statuses": sorted(seen), "transitions": transitions,
                "terminal": terminal})
    return out


def main():
    key = load_key()
    before = credits_remaining(key)
    today = site_now().date()
    yesterday = today - timedelta(days=1)

    print("=" * 78)
    print("DIAG-63  the forecast leg's failure, with a past-window control")
    print("=" * 78)
    print("   site local now      : %s (%s)" % (site_now().strftime("%Y-%m-%d %H:%M"), SITE_TZ_NAME))
    print("   utc now             : %s" % utc_now().strftime("%Y-%m-%d %H:%M"))
    print("   cycle_remaining     : %s" % format(before, ","))
    print("   LEG A  forecast     : %s 14:00-16:00 site-local" % today)
    print("   LEG B  past control : %s 14:00-16:00 site-local" % yesterday)

    legA = submit_and_watch(key, window_for(today), "LEG A  FORECAST (future window)")
    mid = credits_remaining(key)
    legB = submit_and_watch(key, window_for(yesterday), "LEG B  CONTROL (past window)")
    after = credits_remaining(key)

    def classify(leg):
        """What actually happened to one leg. A STALL IS NOT A FAILURE and must not be called one.

        The first version of this function had only ok/not-ok, and it labelled the real outcome
        "BOTH LEGS FAIL ... an account, quota or service-wide cause" -- which reads as a rejection.
        Nothing was rejected: both submits returned HTTP 200 with an activity_id, the status
        endpoint answered 200 for 45 consecutive polls, and the status never left `Processing`.
        Jobs are being ACCEPTED AND QUEUED AND NEVER PROCESSED, which is a different fault with a
        different owner and a different fix. Name it.
        """
        if leg.get("submit_http") != 200:
            return "submit_rejected"
        if not leg.get("activity_id"):
            return "no_activity_id"
        t = leg.get("terminal") or {}
        if t.get("tiles"):
            return "ok"
        if t.get("status") == "completed":
            return "completed_but_empty"      # the 08-18..08-20 mode: billed, zero tiles
        if t.get("status"):
            return "terminal_" + t["status"]  # e.g. terminal_failed -- vendor said no
        busy = {"processing", "pending", "queued", "in progress"}
        if set(leg.get("distinct_statuses") or []) <= busy:
            return "stalled_in_processing"    # accepted, queued, never processed
        return "unknown"

    ca, cb = classify(legA), classify(legB)
    a_ok, b_ok = ca == "ok", cb == "ok"

    # The diagnosis is written from the two classifications, not chosen by hand -- so the script
    # cannot narrate a conclusion its own data does not support.
    if a_ok and b_ok:
        verdict = "BOTH WORK -- the forecast path is healthy again. Bank the pair."
    elif b_ok and not a_ok:
        verdict = ("FORECAST PATH SPECIFICALLY BROKEN (leg A %s). The control leg proves the key, "
                   "the plan, the quota, the endpoint, the AOI and the granularity are all fine; "
                   "only the FUTURE window fails." % ca)
    elif a_ok and not b_ok:
        verdict = "FORECAST WORKS, PAST WINDOW FAILS -- unexpected; treat the control as suspect."
    elif ca == cb == "stalled_in_processing":
        verdict = ("VENDOR-SIDE PROCESSING STALL, NOT A REJECTION AND NOT FORECAST-SPECIFIC. Both "
                   "legs were ACCEPTED (HTTP 200 + activity_id), the status endpoint answered every "
                   "poll, and both sat at `Processing` for the whole budget without ever reaching a "
                   "terminal state. A PAST window -- which worked reliably through 08-19 -- stalls "
                   "identically, so this is not the forecast path, the key, the plan, the quota, the "
                   "AOI or the granularity. FortyGuard is accepting heatmap jobs and not completing "
                   "them. Neither call was billed.")
    else:
        verdict = ("BOTH LEGS UNUSABLE -- leg A %s, leg B %s. Not forecast-specific; read the "
                   "status payloads." % (ca, cb))

    print("\n" + "=" * 78)
    print("VERDICT: %s" % verdict)
    print("=" * 78)
    print("   LEG A forecast : %s" % (legA.get("terminal") or legA.get("submit_error_body")
                                      or legA.get("submit_exception") or "no terminal state"))
    print("   LEG B control  : %s" % (legB.get("terminal") or legB.get("submit_error_body")
                                      or legB.get("submit_exception") or "no terminal state"))
    print("   credits        : %s -> %s -> %s   (leg A cost %s, leg B cost %s)"
          % (format(before, ","), format(mid, ","), format(after, ","),
             format(before - mid, ","), format(mid - after, ",")))
    print("   ⚠ A FAILED CALL THAT COSTS 0 IS A VENDOR-SIDE IMPROVEMENT over the billed")
    print("     zero-tile responses of 08-18..08-20. Record it either way.")

    save_result("diag63_forecast_failed_status.json", {
        "test": "DIAG-63 forecast failure status, with past-window control",
        "authorised_by_user": "2026-08-20 (credits explicitly not a constraint)",
        "api_calls_made": 2,
        "site_tz": SITE_TZ_NAME,
        "site_now": site_now().isoformat(),
        "utc_now": utc_now().isoformat(),
        "leg_a_forecast": legA,
        "leg_b_past_control": legB,
        "credits_before": before,
        "credits_after_leg_a": mid,
        "credits_after": after,
        "leg_a_cost": before - mid,
        "leg_b_cost": mid - after,
        "forecast_ok": a_ok,
        "control_ok": b_ok,
        "leg_a_classification": ca,
        "leg_b_classification": cb,
        "verdict": verdict,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
