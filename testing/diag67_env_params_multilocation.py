# -*- coding: utf-8 -*-
"""DIAG-67 -- DOES `env_params` ACCEPT MANY LOCATIONS IN ONE CALL?

    python diag67_env_params_multilocation.py dryrun            # FREE. Prints the exact payloads.
    python diag67_env_params_multilocation.py run --allow-paid   # sends them

THE QUESTION, AND WHY IT DECIDES THE WHOLE NATIONAL BUILD
    This is FortyGuard's hackathon, and on the three shipped sites their data IS the load-bearer:
    the forecast is the thesis, the safety margin is calibrated on their own measured forecast
    errors, and the humidity and contamination gates run on their `env_params`. On the 639
    nationally discovered facilities, FortyGuard currently contributes NOTHING -- those sites are
    OSM geometry plus Iowa State weather. That is the wrong shape for this project and it has to
    change.

    `/v1/env_params` is the one path CONFIRMED ALIVE during the heatmap outage (DIAG-65: 15 fields x
    24 hourly values while every heatmap window returned `n_cells: 0`). It is also a POINT call,
    which is exactly the shape a per-facility build needs, and it returns the wet-bulb, relative
    humidity, six air-quality indices and cloud cover that drive the humidity gate, the
    contamination gate carrying the LBNL commercial argument, and the Pasquill stability class.

    At 2,900 per call, 582 runnable facilities is 1,687,800 credits against 1,435,580 remaining --
    NOT affordable one-per-site. But every response this project has ever received carries
    `result.locations` as an ARRAY (`live.py` reads `locs0[0]`), while every request we have ever
    sent carried a single scalar `latitude`/`longitude`. Nobody has tested whether the endpoint
    accepts more than one location per call. If it does, the cost per facility collapses and
    FortyGuard perception becomes affordable for every site.

WHY THIS IS CHEAP WHATEVER THE ANSWER
    A REJECTED request is unbilled -- established the expensive way at DIAG-65, whose first attempt
    sent `polygon_aoi` and came back `422 Field 'latitude' is required` for free. So:
      rejected  -> 0 credits, and we know the endpoint is single-point only.
      accepted  -> 2,900 credits, and we know per-site FortyGuard data is affordable nationally.
    Worst case is 2,900, i.e. 0.20 % of the remaining balance, to answer the question that decides
    whether the national build can be a FortyGuard product at all.

PRE-REGISTERED OUTCOMES -- fixed before any call (methodology rule 2)
    P1  MULTI_OK      -- a variant is accepted AND the response carries >= 2 `locations` entries
                         whose parameter arrays are populated with distinct values. Distinctness
                         matters: two locations echoing ONE location's data would be the
                         "one site's value stood in for another" defect (#98/#132/#133/#142) arriving
                         from the vendor instead of from our own code, and it must not be read as
                         success.
    P2  MULTI_ECHO    -- accepted, >= 2 locations returned, but their values are IDENTICAL. Recorded
                         as a FAILURE of the affordability hypothesis, not a success: we would be
                         paying once and getting one site's air labelled as several.
    P3  SINGLE_ONLY   -- every variant rejected (422 or similar). Free. The endpoint takes one
                         point, and per-site cost stays 2,900.
    P4  ACCEPTED_ONE  -- accepted but only ONE location comes back, i.e. the extra locations were
                         silently ignored. This is the dangerous outcome: a caller could believe it
                         had bought N sites' data and have bought one. Explicitly separated from P1.
    P5  ERROR         -- stall or terminal failure, classified by the shared `common.classify_vendor`.

WHAT THIS DELIBERATELY DOES NOT TEST
    Whether the values are CORRECT. This asks only whether the shape is accepted and whether the
    returned locations are distinct. Field correctness is a separate question and this answer must
    not be stretched into one.

ORDER NOTE: this tests `env_params`, NOT the heatmap. The heatmap path went 0-for-39 on 2026-08-23
    with a control at Ashburn's own proven geometry also failing, so buying dry-bulb fields right now
    would spend into a confirmed fault. That probe is a separate, later decision.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "AGENTIC-ARBITER", "src"))

import common as C                                                    # noqa: E402

RESULTS = os.path.join(HERE, "results")
OUT = os.path.join(RESULTS, "diag67_env_params_multilocation.json")

# The day to ask for. A PAST, fully-elapsed day in every US zone, so nothing here depends on a
# forecast horizon or a catalog forward limit (the confound §4.0-CATALOG raised).
DAY = "2026-08-22"
WINDOW = {"start_date": DAY, "start_time": "00:00", "end_time": "23:00", "filter_type": 2}

# Two real, widely separated facilities from the national registry, plus Ashburn's own proven
# centroid. Widely separated ON PURPOSE: if the endpoint echoes one location's data for all of them,
# identical wet-bulb values across ~1,500 km is unmistakable, where three neighbouring sites might
# genuinely agree and hide a P2.
POINTS = [
    ("ashburn_proven", 39.024017, -77.419691),
    ("IA_apple_waukee", 41.61685, -93.92440),
    ("AZ_phoenix_area", 33.34731, -111.6291745),
]


def variants():
    """The candidate payload shapes, most-likely first.

    A mirrors the RESPONSE shape -- `result.locations[]` is a list of objects each carrying its own
    parameters -- which is the most probable request shape for an API that answers that way.
    B is the array-valued-scalar convention some APIs use instead.
    Both are tried because a rejection costs nothing, and stopping at the first guess would leave
    the question half-answered.
    """
    return [
        ("A_locations_array", {
            "locations": [{"latitude": round(la, 5), "longitude": round(lo, 5),
                           "temperature": 25.0} for _, la, lo in POINTS],
            "date_time": WINDOW}),
        ("B_parallel_arrays", {
            "latitude": [round(la, 5) for _, la, _ in POINTS],
            "longitude": [round(lo, 5) for _, _, lo in POINTS],
            "temperature": 25.0,
            "date_time": WINDOW}),
    ]


def populated(loc):
    """{field: n_non_null} for one returned location block."""
    params = loc.get("parameters") or {k: v for k, v in loc.items() if isinstance(v, list)}
    out = {}
    for k, v in (params or {}).items():
        if isinstance(v, list):
            n = sum(1 for x in v if x is not None)
            if n:
                out[k] = n
    return out


def signature(loc):
    """A comparable fingerprint of one location's actual values, for the distinctness test."""
    params = loc.get("parameters") or {k: v for k, v in loc.items() if isinstance(v, list)}
    keys = sorted(k for k, v in (params or {}).items() if isinstance(v, list))
    return json.dumps({k: params[k] for k in keys}, sort_keys=True)


def classify(res):
    """P1..P4 from the response, decided on values rather than on the presence of keys."""
    locs = (res or {}).get("locations") or []
    fills = [populated(l) for l in locs]
    n_filled = sum(1 for f in fills if f)
    if not locs:
        return "P5_no_locations", {"n_locations": 0}
    if n_filled < 2:
        return ("P4_accepted_one" if n_filled == 1 else "P2_empty"), {
            "n_locations": len(locs), "n_populated": n_filled,
            "fields_per_location": fills}
    sigs = {signature(l) for l in locs if populated(l)}
    if len(sigs) < n_filled:
        return "P2_multi_echo", {"n_locations": len(locs), "n_populated": n_filled,
                                 "n_distinct_value_sets": len(sigs),
                                 "fields_per_location": fills}
    return "P1_multi_ok", {"n_locations": len(locs), "n_populated": n_filled,
                           "n_distinct_value_sets": len(sigs),
                           "fields_per_location": fills}


def dryrun():
    print("=" * 78)
    print("DIAG-67 DRY RUN -- no key is read, no request is made")
    print("=" * 78)
    print("   day requested: %s (fully elapsed in every US zone)" % DAY)
    print("   %d points, deliberately far apart so an echoed value is unmistakable:" % len(POINTS))
    for n, la, lo in POINTS:
        print("      %-18s %9.5f, %10.5f" % (n, la, lo))
    for name, p in variants():
        print("\n   variant %s:" % name)
        print("      " + json.dumps(p)[:300])
    print("\n   cost: 0 if rejected (rejections are unbilled, proven at DIAG-65);")
    print("         2,900 per ACCEPTED variant. Worst case both accepted = 5,800.")
    print("   Nothing is sent without `run --allow-paid`.")
    print("=" * 78)
    return 0


def main(argv):
    if not argv or argv[0] == "dryrun":
        return dryrun()
    if argv[0] != "run":
        raise SystemExit("commands: dryrun | run --allow-paid")
    if "--allow-paid" not in argv:
        raise SystemExit("refusing to spend without --allow-paid")

    key = C.load_key()                      # never printed, never logged
    before = C.credits_remaining(key)
    print("=" * 78)
    print("DIAG-67 -- env_params multi-location.  credits before: %s" % format(before, ","))
    print("=" * 78)

    attempts = []
    for name, payload in variants():
        print("\n   variant %s ..." % name)
        b = C.credits_remaining(key)
        rec = {"variant": name, "payload_keys": sorted(payload), "credits_before": b}
        # 🔴 `submit_poll` DOES NOT RAISE ON A REJECTION -- it catches the HTTPError and returns
        # `{"error": ..., "submit_http": 422, "submit_error_body": ...}`. The first version of this
        # file wrapped the call in try/except and read only `r["result"]`, so a 422 arrived as
        # "accepted, zero locations", the rejection BODY -- the only field that says why -- was
        # thrown away, and the run very nearly concluded "single point only" from a misread. The
        # body is exactly what gotcha #124 was about: a record of a failure that omits the reason is
        # barely a record.
        try:
            r = C.submit_poll(key, "env_params", payload, "diag67_%s" % name,
                              require_data=False)
        except Exception as e:                                        # noqa: BLE001
            r = {"error": "raised: %s" % str(e)[:180], "submit_http": None}
        rec["submit_http"] = r.get("submit_http")
        rec["submit_error_body"] = r.get("submit_error_body")
        rec["vendor_error"] = r.get("error")
        rec["activity_id"] = r.get("aid")
        rec["statuses_seen"] = r.get("statuses_seen")
        if r.get("submit_http") and r["submit_http"] >= 400:
            rec.update({"http": "rejected", "verdict": "P3_single_only"})
            print("      REJECTED HTTP %s" % r["submit_http"])
            print("      body: %s" % (r.get("submit_error_body") or "(none)")[:220])
        elif r.get("error") and not r.get("result"):
            rec.update({"http": "error", "verdict": "P5_error"})
            print("      ERROR: %s" % str(r.get("error"))[:200])
        else:
            verdict, detail = classify(r.get("result") or {})
            rec.update({"http": "accepted", "verdict": verdict, "detail": detail})
        a = C.credits_remaining(key)
        rec["credits_after"] = a
        rec["credits_spent"] = max(0, b - a)
        print("      verdict %s   spent %s credits"
              % (rec["verdict"], format(rec["credits_spent"], ",")))
        if rec.get("detail"):
            print("      %s" % json.dumps({k: v for k, v in rec["detail"].items()
                                           if k != "fields_per_location"}))
        attempts.append(rec)

    after = C.credits_remaining(key)
    wins = [a for a in attempts if a["verdict"] == "P1_multi_ok"]
    os.makedirs(RESULTS, exist_ok=True)
    json.dump({"generated_by": "testing/diag67_env_params_multilocation.py",
               "question": "does /v1/env_params accept multiple locations in one call",
               "day_requested": DAY, "points": POINTS,
               "credits_before": before, "credits_after": after,
               "credits_spent": max(0, before - after),
               "attempts": attempts,
               "conclusion": ("MULTI_LOCATION_SUPPORTED" if wins else
                              "SINGLE_POINT_ONLY_or_echoed"),
               "what_this_does_not_test": "whether the returned values are correct; only whether "
                                          "the shape is accepted and the locations are distinct"},
              open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)

    print("\n" + "=" * 78)
    print("   spent %s credits total. %s -> %s"
          % (format(max(0, before - after), ","), format(before, ","), format(after, ",")))
    if wins:
        n = len(POINTS)
        print("   🟢 MULTI-LOCATION WORKS: %d distinct locations in one 2,900-credit call"
              % n)
        print("      => %.0f credits per facility, against 2,900 one-per-site" % (2900.0 / n))
        print("      This is NOT a licence to assume N scales without limit -- the next step is to")
        print("      find the real per-call ceiling, which is another cheap rejection test.")
    else:
        print("   env_params takes ONE point per call. Per-facility cost stays 2,900.")
    print("   wrote %s" % OUT)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
