# -*- coding: utf-8 -*-
"""DIAG-61  ---  why do FORECAST windows return zero tiles on the Hackathon key?

STAGE 1 IS FREE.  STAGE 2 IS ONE PAID CALL (4,220 credits), authorised by the user 2026-08-19.

THE PROBLEM
    The daily N-26 collector returned ZERO TILES on two consecutive days, 2026-08-18 and
    2026-08-19, on forecast windows at 8.6 h and 9.38 h lead -- both inside the 6.0-11.5 h
    comparability band, and both using the request shape that works for a past window.

THE VARIABLE TABLE, built before writing any cause (gotcha #35)

    variable            PAST window OK      FAIL            FAIL            FAIL
    lead                -- (elapsed)        ~8.6 h          9.38 h          8.86 h
    AOI                 8x8 km              8x8 km          8x8 km          8x8 km
    granularity         60                  60              60              60
    analytic_type       tcm                 tcm             tcm             tcm
    WINDOW DIRECTION    PAST                future          future          future
    result              17,862 tiles        0 tiles         0 tiles         0 tiles

    Exactly one thing differs between the success and every failure: WHETHER THE WINDOW IS IN THE
    PAST OR THE FUTURE. N-55 established that this key serves 8x8 km at granularity 60 and returns
    17,862 features -- for a PAST target. So the combination never demonstrated to
    work is:

        this key  x  FUTURE window   =  the only untested thing left.

COMPETING EXPLANATIONS, and what would separate them
    A1  The plan carries no FORECAST entitlement.             -> every future window fails, any lead
    A2  The forecast HORIZON is shorter than 12 h.            -> a SHORT lead succeeds, a long one fails
    A3  The forecast path is transiently degraded.            -> indistinguishable from A1 today;
                                                                 separated only by retrying later
    A4  Something specific to these target dates.             -> a different target date would work

    STAGE 2 tests A2 against A1/A3 by changing ONE variable: the lead, 9.4 h -> ~3 h. Same AOI, same
    granularity, same analytic_type. Tiles returned means the forecast path works and the horizon is
    the constraint, so the collector simply moves later in the day. Zero tiles leaves A1 or A3, and
    A3 is then tested for free by the next scheduled run.

PRE-REGISTERED, before the call is made
    P1  a ~3 h-lead forecast returns > 0 tiles   -> A2. FIX: shift the collection time.
    P2  it returns 0 tiles                       -> A1 or A3. No further paid call today; report to
                                                    FortyGuard and let tomorrow's free run separate
                                                    them.
    Either way the result is recorded, and 65.6 % remains the quoted coverage until a fifth pair
    exists.

SAFETY
    * The key is read via common.load_key() and never printed, logged or written to a fixture.
    * Stage 1 touches ONLY /system/fetch-api-key-usage, documented free (gotcha #33).
    * The meter is differenced before and after, so the true cost is measured, not assumed --
      including whether the two zero-tile failures were billed (gotcha #30: they are).
    * Exactly ONE paid call. `assert_non_empty` is not used to abort, because a zero-tile answer IS
      the measurement here.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (V1, _headers, banner, box_aoi, load_key, save_result,   # noqa: E402
                    site_now, site_tz, site_window, submit_poll, TARGET_CENTRE, TARGET_SIDE_KM)

GRAN = 60
WIN_H = 2
SHORT_LEAD_H = 3.0


def usage(key):
    """FREE -- gotcha #33. Never prints the key."""
    req = urllib.request.Request("%s/system/fetch-api-key-usage" % V1,
                                 data=json.dumps({"api_key": key}).encode(),
                                 headers=_headers(key))
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def meters(u):
    c = u.get("credit_summary", {}) or {}
    return (c.get("total_credits_used"), c.get("total_available_credits"),
            c.get("total_remaining_credits"), c.get("cycle_remaining_credits"))


def main():
    banner("DIAG-61  forecast entitlement vs horizon vs outage   [stage 1 FREE, stage 2 = 1 call]")
    key = load_key()

    # ---------------- STAGE 1: FREE ----------------------------------------------------------
    print("\n   STAGE 1  free endpoints only")
    u0 = usage(key)
    tu0, tav0, trem0, cyc0 = meters(u0)
    print("      total_credits_used      : %s" % f"{tu0:,}" if isinstance(tu0, int) else tu0)
    print("      total_available_credits : %s" % f"{tav0:,}" if isinstance(tav0, int) else tav0)
    print("      total_remaining_credits : %s" % f"{trem0:,}" if isinstance(trem0, int) else trem0)
    print("      cycle_remaining_credits : %s" % f"{cyc0:,}" if isinstance(cyc0, int) else cyc0)

    print("\n      top-level keys in the usage payload:")
    for k in sorted(u0.keys()):
        v = u0[k]
        kind = type(v).__name__
        size = (" (%d)" % len(v)) if hasattr(v, "__len__") and not isinstance(v, str) else ""
        print("         %-28s %s%s" % (k, kind, size))

    # anything that looks like an entitlement / plan / feature list
    print("\n      searching the payload for plan or entitlement information:")
    found = False
    for k, v in u0.items():
        if any(t in k.lower() for t in ("plan", "tier", "feature", "entitle", "scope",
                                        "permission", "product", "limit")):
            found = True
            print("         %-28s %s" % (k, json.dumps(v)[:300]))
    if isinstance(u0.get("activity_breakdown"), list):
        print("\n      activity_breakdown (what has actually been billed):")
        for row in u0["activity_breakdown"][:12]:
            print("         %s" % json.dumps(row)[:180])
    if not found:
        print("         nothing named plan/tier/feature/entitlement in the payload")

    # what did the two zero-tile failures cost?
    print("\n      COST OF THE TWO ZERO-TILE FAILURES")
    print("      Manifest recorded 1,995,780 remaining after the 08-16 collection.")
    if isinstance(trem0, int):
        spent_since = 1995780 - trem0
        print("      remaining now %s  ->  %s credits spent since"
              % (f"{trem0:,}", f"{spent_since:,}"))
        print("      at 4,220 per call that is %.2f calls" % (spent_since / 4220.0))
        print("      (gotcha #30: a zero-tile `completed` response IS billed at full price)")

    # ---------------- STAGE 2: ONE PAID CALL -------------------------------------------------
    now = site_now()
    start = (now + timedelta(hours=SHORT_LEAD_H)).replace(minute=0, second=0, microsecond=0)
    dt = site_window(start, WIN_H)
    aoi = box_aoi(TARGET_CENTRE[0], TARGET_CENTRE[1], TARGET_SIDE_KM)
    lead = (start - now).total_seconds() / 3600.0
    print("\n   STAGE 2  ONE PAID CALL -- the ONLY variable changed vs the failing call is the LEAD")
    print("      site-local now      : %s" % now.strftime("%Y-%m-%d %H:%M %Z"))
    print("      target window       : %s  ->  lead %.2f h  (the failing calls were 8.6-9.4 h)"
          % (start.strftime("%Y-%m-%d %H:%M %Z"), lead))
    print("      AOI / granularity   : %.0fx%.0f km / %d   (identical to the failing call)"
          % (TARGET_SIDE_KM, TARGET_SIDE_KM, GRAN))
    print("      analytic_type       : tcm                   (identical)")

    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
               "date_time": {k: v for k, v in dt.items() if not k.startswith("_")}}
    r = submit_poll(key, "heatmap", payload, "diag61_shortlead")
    n_feat = 0
    if r.get("ok"):
        n_feat = len(((r.get("result") or {}).get("map_data") or {}).get("features") or [])
    print("\n      ok=%s   features=%s   %s"
          % (r.get("ok"), f"{n_feat:,}", ("error: %s" % r.get("error")) if not r.get("ok") else ""))

    u1 = usage(key)
    tu1, _, trem1, cyc1 = meters(u1)
    cost = (tu1 - tu0) if (isinstance(tu1, int) and isinstance(tu0, int)) else None
    print("      meter differenced   : %s credits for this call"
          % (f"{cost:,}" if cost is not None else "unavailable"))
    print("      remaining now       : %s" % (f"{trem1:,}" if isinstance(trem1, int) else trem1))

    # ---------------- VERDICT ----------------------------------------------------------------
    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE THE CALL")
    if n_feat > 0:
        print("      P1 MET: a %.1f h-lead forecast returned %s tiles." % (lead, f"{n_feat:,}"))
        print("      -> The forecast path WORKS on this key. The 9.4 h lead is the problem, so the")
        print("         effective horizon is SHORTER than the 12 h the API is documented to offer.")
        print("         FIX: move the collector later in the day so the lead falls inside whatever")
        print("         the new horizon is, and re-measure the horizon explicitly before trusting it.")
        print("      *** COMPARABILITY WARNING: the four existing pairs are at ~9.4 h lead. A")
        print("          shorter-lead pair is NOT exchangeable with them -- a shorter lead is an")
        print("          easier forecast and would inflate coverage. Either re-baseline all days at")
        print("          the new lead, or report the two groups separately. Do not mix them.")
    else:
        print("      P2 MET: a %.1f h-lead forecast ALSO returned 0 tiles." % lead)
        print("      -> The horizon is NOT the explanation. Remaining: the Hackathon plan has no")
        print("         forecast entitlement (A1), or FortyGuard's forecast path is degraded (A3).")
        print("         These are separated FOR FREE by tomorrow's scheduled run; no further paid")
        print("         call today. Report to FortyGuard with the two activity_ids.")
    print("\n      Either way: 65.6 %% remains the quoted coverage. There is still no fifth pair.")

    save_result("diag61_forecast_entitlement.json", {
        "test": "DIAG-61 forecast entitlement vs horizon vs outage",
        "authorised": "user, 2026-08-19, one paid call",
        "short_lead_h": lead,
        "target_window_site_local": start.isoformat(),
        "aoi_side_km": TARGET_SIDE_KM, "granularity": GRAN, "analytic_type": "tcm",
        "features_returned": n_feat,
        "call_ok": bool(r.get("ok")), "call_error": r.get("error"),
        "meter_before": {"total_used": tu0, "remaining": trem0, "cycle_remaining": cyc0},
        "meter_after": {"total_used": tu1, "remaining": trem1, "cycle_remaining": cyc1},
        "measured_cost_credits": cost,
        "verdict": ("P1 forecast path works, horizon shorter than 12 h"
                    if n_feat > 0 else
                    "P2 short lead also empty -- entitlement or outage, not horizon"),
        "comparability_note": ("existing 4 pairs are at ~9.4 h lead; a shorter-lead pair is not "
                               "exchangeable with them and must not be pooled"),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
