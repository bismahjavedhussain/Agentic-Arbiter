# -*- coding: utf-8 -*-
"""N-55 -- Does a FULL-SIZE 8x8 km @ granularity 60 request return a complete field?

WHY THIS EXISTS
---------------
On 2026-08-18 I twice wrote a wrong cause into the project's documents (gotchas #34, #35). The last
wrong one was "the plan caps request size", inferred from comparing a FAILING call against a
SUCCEEDING call that differed in FOUR ways at once.

This probe changes exactly ONE variable. It re-issues a request already known to succeed -- same AOI,
same granularity, same analytic type, same target window -- and asks only whether a full-size request
returns a full field.

  8x8 km @ gran 60, 2026-08-16 14:00-16:00 site-local  ->  expected 17,862 features, 7.4 MB

PRE-REGISTERED INTERPRETATION -- written before the call, so the answer cannot be rationalised after
------------------------------------------------------------------------------------------------------
  NON-EMPTY  =>  the plan does NOT cap request size. N-26 needs NO changes, its 8x8 km @ 60 AOI stands,
                 and comparability with all four existing pairs is intact. The 08-18 emptiness is then
                 a data-AVAILABILITY matter (the window was ~8.6 h in the future when asked), which
                 tomorrow's free 13:30 run settles by back-filling the 08-18 outcome.
  EMPTY      =>  the plan DOES cap request size after all. My retracted claim was right by luck, and it
                 must be RE-asserted with this controlled evidence, not with the old confounded pair.
                 N-26 then needs the section 6.1 decision (shrink / freeze / parallel).

BONUS, free: the target window is one we already hold as a fixture (n26_h_2026-08-16.json), so this
is also a REPRODUCIBILITY check. Does the API return the identical field when the same settled past
window is requested again? Nothing in the project had tested that, and gotcha #31 warns not to assume
a saved call reproduces. It matters directly: the demo replays fixtures offline, and that is only
honest if a replay is faithful.

COST: 1 heatmap call = 4,220 credits = 0.21 % of 2,000,000. Authorised by the user.
System/usage endpoints are free (gotcha #33), so the meter is read before and after (spending rule 1).
"""
import io
import json
import os
import sys
import urllib.request
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (load_key, submit_poll, box_aoi, site_window, site_tz, tile_key,   # noqa: E402
                   assert_non_empty, save_result, FIXTURES, V1, _headers)

# byte-identical to test_n26_coverage.py -- do not "tidy" these
CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14
TARGET_DATE = (2026, 8, 16)          # a window already known to return a full field
BASELINE_FIXTURE = "n26_h_2026-08-16.json"
TAG = "n55_newkey_8km_gran60_2026-08-16"


def usage(key):
    """Full usage payload. FREE -- gotcha #33."""
    req = urllib.request.Request("%s/system/fetch-api-key-usage" % V1,
                                 data=json.dumps({"api_key": key}).encode(),
                                 headers=_headers(key))
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def meters(u):
    c = u.get("credit_summary", {})
    return (c.get("total_credits_used"), c.get("total_available_credits"),
            c.get("total_remaining_credits"), c.get("cycle_remaining_credits"))


def main():
    print("=" * 78)
    print("  N-55  Does a full-size 8x8 km @ granularity 60 request return a full field?")
    print("  ONE variable changed vs a request already known to succeed.")
    print("=" * 78)
    key = load_key()

    before = usage(key)
    tu0, tav0, trem0, cyc0 = meters(before)
    print("\n  METER BEFORE   total_used %s   available %s   remaining %s   cycle_remaining %s"
          % (tu0, tav0, trem0, cyc0))

    start = datetime(TARGET_DATE[0], TARGET_DATE[1], TARGET_DATE[2],
                     TARGET_HOUR_SITE, 0, tzinfo=site_tz())
    dt = site_window(start, WIN_H)
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
               "date_time": {k: v for k, v in dt.items() if not k.startswith("_")}}

    print("  REQUEST        centre %.4f, %.4f   %.0f x %.0f km   granularity %d   analytic tcm"
          % (CENTRE[0], CENTRE[1], SIDE_KM, SIDE_KM, GRAN))
    print("                 window %s %s-%s site-local (filter_type %d)"
          % (payload["date_time"]["start_date"], payload["date_time"]["start_time"],
             payload["date_time"]["end_time"], payload["date_time"]["filter_type"]))
    print("                 this window is ~2 days PAST, so availability is not a factor")

    print("\n  submitting (polling to completion, may take a few minutes) ...")
    r = submit_poll(key, "heatmap", payload, TAG)

    after = usage(key)
    tu1, tav1, trem1, cyc1 = meters(after)
    print("\n  METER AFTER    total_used %s   available %s   remaining %s   cycle_remaining %s"
          % (tu1, tav1, trem1, cyc1))
    spent = None
    if isinstance(tu0, (int, float)) and isinstance(tu1, (int, float)):
        spent = tu1 - tu0
        print("  SPENT          %s credits  (expected 4,220)   -> %s"
              % (spent, "MATCHES the documented cost" if spent == 4220 else "*** DIFFERENT ***"))

    if not r.get("ok"):
        print("\n  *** CALL DID NOT COMPLETE: %s" % r.get("error"))
        save_result("n55_keysize.json", {"outcome": "call_failed", "error": r.get("error"),
                                    "spent": spent, "payload_shape": "8x8km gran60 tcm"})
        return 2

    res = r["result"]
    ok, msg = assert_non_empty(res)
    feats = res.get("map_data", {}).get("features") or []
    ncell = res.get("stats_data", {}).get("n_cells")
    print("\n" + "=" * 78)
    print("  RESULT: %s   -- %s" % ("NON-EMPTY" if ok else "EMPTY", msg))
    print("=" * 78)
    print("  features %d   stats_data.n_cells %s   completed in %s s" % (len(feats), ncell, r["secs"]))

    out = {"outcome": "non_empty" if ok else "empty", "n_features": len(feats),
           "n_cells": ncell, "spent_credits": spent, "secs": r["secs"],
           "request": {"centre": list(CENTRE), "side_km": SIDE_KM, "granularity": GRAN,
                       "analytic_type": "tcm", "date_time": payload["date_time"]},
           "meter_before": {"total_used": tu0, "remaining": trem0, "cycle_remaining": cyc0},
           "meter_after": {"total_used": tu1, "remaining": trem1, "cycle_remaining": cyc1}}

    if not ok:
        print("\n  => THE PLAN DOES CAP REQUEST SIZE. My retracted claim was right after all, and this")
        print("     is the controlled evidence it always needed. N-26 needs the section 6.1 decision.")
        out["interpretation"] = ("plan caps request size -- CONFIRMED with one variable changed; "
                                "re-assert the retracted claim using THIS evidence")
        save_result("n55_keysize.json", out)
        return 1

    print("\n  => THE PLAN DOES NOT CAP REQUEST SIZE. N-26 needs NO changes; its 8x8 km @ 60 AOI stands")
    print("     and comparability with all four existing pairs is intact. The 08-18 emptiness is a")
    print("     data-AVAILABILITY matter, which tomorrow's free 13:30 run settles.")
    out["interpretation"] = ("plan does NOT cap request size; N-26 AOI stands, comparability intact; "
                             "08-18 emptiness is an availability matter")

    # ---------------------------------------------------------- reproducibility of a replay
    bp = os.path.join(FIXTURES, BASELINE_FIXTURE)
    if os.path.exists(bp) and os.path.getsize(bp) > 0:
        base = json.load(open(bp, encoding="utf-8"))
        bf = base.get("map_data", {}).get("features") or []
        print("\n  REPRODUCIBILITY  (same past window, requested again)")
        print("     saved fixture features %d   fresh request features %d   %s"
              % (len(bf), len(feats), "SAME COUNT" if len(bf) == len(feats) else "*** DIFFERENT ***"))

        def index(fs):
            """Index by tile_id on `average_temperature`.

            BUG FIXED 2026-08-18: the first version guessed the property name as
            temperature/value/tcm. The real name is `average_temperature` (alongside
            `min_temperature`, `max_temperature`, `tile_id`), so BOTH sides indexed 0 tiles and the
            comparison silently reported "0 matched" instead of failing. A parser that returns an
            empty index must never be read as "no agreement".
            """
            d = {}
            for f in fs:
                p = f.get("properties") or {}
                if "tile_id" in p and p.get("average_temperature") is not None:
                    d[p["tile_id"]] = float(p["average_temperature"])
            if fs and not d:
                raise SystemExit("index() parsed 0 of %d features -- property names changed; "
                                 "fix the parser rather than reporting no agreement" % len(fs))
            return d

        A, B = index(bf), index(feats)
        common = set(A) & set(B)
        print("     tiles matched by coordinate : %d  (old %d, new %d indexed)"
              % (len(common), len(A), len(B)))
        if common:
            diffs = [B[k] - A[k] for k in common]
            ad = sorted(abs(d) for d in diffs)
            ident = sum(1 for d in diffs if d == 0.0)
            print("     identical values            : %d of %d  (%.2f %%)"
                  % (ident, len(common), 100.0 * ident / len(common)))
            print("     mean delta  %+.6f C     max |delta|  %.6f C     median |delta|  %.6f C"
                  % (sum(diffs) / len(diffs), ad[-1], ad[len(ad) // 2]))
            out["cross_key"] = {"old_features": len(bf), "new_features": len(feats),
                                "matched": len(common), "identical": ident,
                                "mean_delta_c": sum(diffs) / len(diffs),
                                "max_abs_delta_c": ad[-1],
                                "median_abs_delta_c": ad[len(ad) // 2]}
            if ident == len(common):
                print("     => BYTE-FOR-BYTE REPRODUCIBLE across keys. Fixtures are trustworthy.")
            else:
                print("     => values DIFFER across keys for an identical PAST window. Worth reporting:")
                print("        a settled historical field should not change between requests.")
    else:
        print("\n  baseline fixture %s missing or empty -- skipping replay check" % BASELINE_FIXTURE)

    save_result("n55_keysize.json", out)
    print("\n  saved: testing/results/n55_keysize.json   fixture: %s.json" % TAG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
