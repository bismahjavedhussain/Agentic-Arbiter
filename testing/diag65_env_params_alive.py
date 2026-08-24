# -*- coding: utf-8 -*-
"""DIAG-65 -- IS `env_params` ALIVE WHILE `heatmap` IS DOWN?   PAID, 1 call, 2,900 credits.

THE HYPOTHESIS, WRITTEN DOWN BEFORE THE CALL (methodology rule 2)
    H1  The fault that has returned `completed` with `n_cells: 0` for every `/v1/heatmap` window --
        past and future, both AOIs -- since 2026-08-18 is SPECIFIC TO THE HEATMAP ENDPOINT, and
        `/v1/env_params` is serving normally.

    Origin: the user's read of the situation on 2026-08-23. It has never been tested: every probe
    this project has made during the outage has been a heatmap call.

WHY THIS IS WORTH 2,900 CREDITS WHATEVER THE ANSWER
    It is the cheapest call available (2,900 against the heatmap's 4,220) and both outcomes are
    useful, which is the property a diagnostic needs:

      alive  -> the fault is heatmap-specific. E2 in FORTYGUARD-NEXT-EXPERIMENTS.md becomes
               buildable DURING the outage: the humidity and air-quality gates could run on
               FortyGuard's own forecast while the temperature path is still broken. It also gives
               the vendor report a clean contrast -- "your heatmap returns empty for an AOI and hour
               where your env_params serves fine" is far more actionable than "your API is broken".
      dead   -> the fault spans endpoints. That kills the "just heatmap" hypothesis, and it tells
               FortyGuard the blast radius is wider than a single service. Not a wasted call.

WHAT THIS DELIBERATELY DOES NOT TEST
    Whether the VALUES are right. This asks only whether the path serves data. Field correctness is
    a separate question and the answer here must not be stretched into one.

PRE-REGISTERED OUTCOMES -- fixed before the call
    P1  ALIVE   -- the response carries a `locations[0]` block whose parameter arrays are populated
                   with at least one non-null hourly value.
    P2  EMPTY   -- the response completes but the arrays are absent or all-null. Same signature as
                   the heatmap fault, one endpoint wider.
    P3  ERROR   -- submit rejected, terminal failure, or a stall. Classified, not guessed, by the
                   shared `common.classify_vendor`.

    A note on what "populated" means here: `env_params` is documented (findings 9.4) to return
    HOURLY ARRAYS -- 24 values per field for a filter_type 2 day -- so a response with the keys
    present but every array empty is P2, not P1. That distinction is checked rather than eyeballed.

COST
    One call, 2,900 credits. `env_params` is NOT free -- established from `activity_breakdown`,
    HANDOFF 12.2 -- and this file exists partly so nobody re-learns that by accident.

USAGE
    python diag65_env_params_alive.py dryrun            # the payload and the cost. ZERO calls.
    python diag65_env_params_alive.py run --allow-paid   # the real thing
"""
import json
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, site_now, utc_now, SITE_TZ_NAME, classify_vendor, vendor_rec,
                    vendor_sentence, is_billed)

IA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "INTAKE-ARBITER")
sys.path.insert(0, os.path.join(IA, "src"))
import metros as M                                                        # noqa: E402

METRO = "ashburn"
SIDE_KM = 8.0                     # the SAME box the heatmap calls use, so the two are comparable
ENV_PARAMS_CREDITS = 2_900        # measured from activity_breakdown, NOT free

# The fields we would actually consume, from findings 9.4. Listed here so the check is about the
# data we need rather than about whatever happens to come back.
WANTED = ["relative_humidity_percent", "wet_bulb_temperature_celsius",
          "air_quality_pm2p5:idx", "air_quality_pm10:idx", "air_quality_no2:idx",
          "air_quality_o3:idx", "air_quality_so2:idx",
          "cloud_cover_octas", "solar_irradiance", "precipitation_mm"]

# Refused on evidence, and re-checked here so a regression on their side is visible to us.
REFUSED = {"heat_index_celsius": "findings 1.1 -- computed from the caller's own temperature input",
           "temperature": "findings 1.7 -- echoes the caller's input; env_params has no dry-bulb"}


def window():
    """Today, 00:00-23:00 site-local: one call, 24 hourly values per field, forecast hours included.

    filter_type 2 across a whole day is the shape findings 9.4 measured, and it is why this probe is
    cheap per hour of coverage. The zone is the AOI's own -- `common.site_window` is not used because
    it enforces a window that does not cross midnight and this one deliberately spans the day.
    """
    d = site_now().date()
    return {"start_date": d.isoformat(), "start_time": "00:00", "end_time": "23:00",
            "filter_type": 2}


def payload():
    """🔴 `env_params` TAKES A POINT, NOT A POLYGON. The first version of this file sent
    `polygon_aoi` -- copied from the heatmap payload without checking -- and FortyGuard rejected it
    with `422 Field 'latitude' is required`. Free, because rejections are unbilled, but it produced
    a WRONG CONCLUSION (see `interpret`), which was the expensive part.

    The shape below is the one our own working calls use (`test_n15_forecast_state.py`,
    `verify_api_defects.py`): latitude, longitude, and a `temperature` the endpoint echoes back.

    ⚠ `temperature` is REQUIRED but its value is NOT a measurement of anything -- findings §1.1 and
    §1.7: the endpoint computes `heat_index_celsius` from whatever you send and echoes
    `locations[].temperature` straight back. Both fields are on our refused list for exactly that
    reason, so the value here is a placeholder and nothing downstream may read it.
    """
    clat, clon = M.site_centre(METRO)
    return {"latitude": round(clat, 5), "longitude": round(clon, 5),
            "temperature": 25.0,          # required by the schema; echoed, never consumed
            "date_time": window()}


def classify_response(res):
    """P1 / P2, decided on the arrays rather than on the presence of keys."""
    locs = (res or {}).get("locations") or []
    if not locs:
        return "empty_no_locations", {}, 0
    params = locs[0].get("parameters") or {k: v for k, v in locs[0].items() if isinstance(v, list)}
    filled = {}
    for k, v in (params or {}).items():
        if isinstance(v, list):
            n = sum(1 for x in v if x is not None)
            if n:
                filled[k] = n
    return ("alive" if filled else "empty_all_null"), filled, len((params or {}))


def dryrun():
    banner("DIAG-65 dry run   is env_params alive?  ZERO API CALLS, no key read.")
    clat, clon = M.site_centre(METRO)
    w = window()
    print("   AOI            : %.6f, %.6f  %.0fx%.0f km   (the SAME box the heatmap calls use)"
          % (clat, clon, SIDE_KM, SIDE_KM))
    print("   window         : %s %s-%s %s-local (filter_type 2 -> 24 hourly values per field)"
          % (w["start_date"], w["start_time"], w["end_time"], SITE_TZ_NAME))
    print("   endpoint       : POST /v1/env_params")
    print("   cost           : %s credits  (NOT free -- measured from activity_breakdown)"
          % format(ENV_PARAMS_CREDITS, ","))
    print("\n   fields we would consume if it answers:")
    for f in WANTED:
        print("      %s" % f)
    print("\n   fields we refuse on evidence, re-checked for regression:")
    for f, why in REFUSED.items():
        print("      %-28s %s" % (f, why))
    print("\n   Nothing has been spent. `run --allow-paid` makes the call.")
    return 0


def run(allow_paid):
    banner("DIAG-65   is env_params alive while heatmap is down?   [%s]"
           % ("PAID -- 1 call" if allow_paid else "REFUSING to spend"))
    if not allow_paid:
        print("   --allow-paid was not given. `dryrun` shows the plan for free.")
        return 5
    key = load_key()
    before = credits_remaining(key)
    w = window()
    clat, clon = M.site_centre(METRO)
    print("   meter before   : %s" % format(before, ","))
    print("   window         : %s %s-%s %s-local" % (w["start_date"], w["start_time"],
                                                     w["end_time"], SITE_TZ_NAME))
    print("   PRE-REGISTERED : alive = at least one hourly array carries a non-null value.")

    r = submit_poll(key, "env_params", payload(), "diag65_env_params", require_data=False)
    rec = vendor_rec(r, tiles=0)
    rec["class"] = cls = classify_vendor(rec)
    rec["billed"] = is_billed(cls)
    after = credits_remaining(key)
    print("\n   -> %s" % vendor_sentence(cls, rec))
    print("      meter %s -> %s   spent %s" % (format(before, ","), format(after, ","),
                                               format(before - after, ",")))

    # 🔴 THE VENDOR CLASSIFICATION OUTRANKS THE BODY INSPECTION, and the first version had this
    # backwards. A submit rejected at validation has no result body, so `classify_response` returned
    # `empty_no_locations` and the conclusion read "env_params carried no populated hourly arrays --
    # the fault SPANS ENDPOINTS". That was about to go into a vendor report. The request had never
    # reached their data path at all: it was OUR malformed payload, refused in 1 second with a 422
    # naming the missing field.
    # The rule: a request that was never accepted says NOTHING about the endpoint's health, and a
    # diagnostic that cannot tell "they refused me" from "they served me nothing" is worse than no
    # diagnostic. P3 is checked FIRST now.
    if cls != "ok" and not (r.get("result") or {}).get("locations"):
        conclusion = ("INCONCLUSIVE -- the request never reached the data path (%s). %s "
                      "This says NOTHING about whether env_params is serving; fix the request and "
                      "re-run before concluding anything about the endpoint."
                      % (cls, (rec.get("submit_error_body") or "")[:160]))
        print()
        print("   " + "\n   ".join(conclusion[i:i + 92] for i in range(0, len(conclusion), 92)))
        save_result("diag65_env_params_alive.json", {
            "test": "DIAG-65 is env_params alive while heatmap is down",
            "authorised_by_user": utc_now().date().isoformat(),
            "endpoint": "env_params", "api_calls_made": 1,
            "credits_before": before, "credits_after": after, "credits_spent": before - after,
            "vendor_class": cls, "state": "request_never_accepted",
            "submit_http": rec.get("submit_http"),
            "submit_error_body": rec.get("submit_error_body"),
            "h1_supported": None, "conclusion": conclusion,
            "does_not_establish": "anything at all about endpoint health -- the request was "
                                  "refused before reaching it"})
        verdict(False, "", conclusion[:220])
        return 2

    state, filled, n_params = classify_response(r.get("result"))
    print("\n   parameters returned : %d" % n_params)
    if filled:
        for k in sorted(filled):
            mark = "   <- WE CONSUME THIS" if k in WANTED else (
                "   <- REFUSED (%s)" % REFUSED[k].split("--")[0].strip() if k in REFUSED else "")
            print("      %-34s %3d non-null hourly value(s)%s" % (k, filled[k], mark))
    missing = [f for f in WANTED if f not in filled]

    if state == "alive":
        conclusion = ("H1 SUPPORTED. env_params served %d populated field(s) for the same AOI and "
                      "day that /v1/heatmap has been returning `completed` with n_cells: 0 for. The "
                      "fault is HEATMAP-SPECIFIC. E2 is buildable now -- the humidity and "
                      "air-quality gates can run on FortyGuard's own forecast while the temperature "
                      "path is still broken -- and the vendor report gains a clean contrast case."
                      % len(filled))
        if missing:
            conclusion += (" NOTE: %d field(s) we consume were absent or all-null: %s."
                           % (len(missing), ", ".join(missing)))
    elif state.startswith("empty"):
        conclusion = ("H1 NOT SUPPORTED. env_params completed but carried no populated hourly "
                      "arrays (%s) -- the same shape of failure as the heatmap path. The fault "
                      "SPANS ENDPOINTS, which is worth telling FortyGuard because it widens the "
                      "blast radius beyond a single service." % state)
    else:
        conclusion = ("INCONCLUSIVE on availability: the call did not complete normally (%s). "
                      "This is a third outcome, not a quiet failure -- repeat before drawing "
                      "anything from it." % cls)

    print()
    print("   " + "\n   ".join(conclusion[i:i + 92] for i in range(0, len(conclusion), 92)))
    save_result("diag65_env_params_alive.json", {
        "test": "DIAG-65 is env_params alive while heatmap is down",
        "hypothesis": "the empty-response fault is specific to /v1/heatmap",
        "authorised_by_user": utc_now().date().isoformat(),
        "endpoint": "env_params", "metro": METRO,
        "aoi_centre": list(M.site_centre(METRO)), "side_km": SIDE_KM,
        "date_time": w, "api_calls_made": 1,
        "credits_before": before, "credits_after": after, "credits_spent": before - after,
        "vendor_class": cls, "state": state,
        "n_parameters_returned": n_params,
        "populated_fields": filled,
        "wanted_fields_missing": missing,
        "h1_supported": state == "alive",
        "conclusion": conclusion,
        "does_not_establish": "whether the VALUES are correct -- only that the path serves data"})
    verdict(state == "alive", conclusion[:220], conclusion[:220])
    return 0 if state == "alive" else 1


if __name__ == "__main__":
    mode = (sys.argv[1].lower() if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
            else "dryrun")
    sys.exit(run("--allow-paid" in sys.argv) if mode == "run" else dryrun())
