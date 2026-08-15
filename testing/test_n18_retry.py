# -*- coding: utf-8 -*-
"""N-18  persistent-retry probe: can forecast windows be obtained by retrying?   PAID.

*** RESULT INVALIDATED 2026-08-12 -- THE FAILURE WAS OURS, NOT FORTYGUARD'S. DO NOT QUOTE. ***

    This file built its windows from datetime.now() -- machine local, UTC+5 -- and sent bare
    "%H:00" strings. The endpoint reads them in the AOI's local zone, UTC-4. So the four leads it
    believed it was probing were really:

        believed +4 h   ->  true 13 h    outside the 12 h horizon
        believed +6 h   ->  true 15 h    outside
        believed +8 h   ->  true 17 h    outside
        believed +10 h  ->  true 19 h    outside

    Every one of the 48 attempts requested a window outside the horizon. No amount of retrying could
    ever have succeeded, so "0 of 4 leads recovered in 48 attempts" measures our own bug.

    Consequences already actioned:
      - the claim of forecast intermittency against FortyGuard is WITHDRAWN
        (fortyguard-api-findings.md section 1.4b)
      - the 12 h horizon is instead CONFIRMED: 9.25 h and 11.25 h return data, 13.25 h and 17.25 h
        return zero tiles, and a 9.41 h lead returned a full 17,862-tile field on 2026-08-12
      - what survives is the silent-empty-success defect, now stated with the exact boundary

    Kept on disk unmodified as the audit trail. Use common.site_window() for any new paid test.

FortyGuard confirms the 12 h forecast is a supported product and that transient failures are
retryable. N-14 saw every window beyond +2 h come back as an empty success on a single attempt.
This probe retries each lead time hard, and records:

   1. whether a forecast at each lead can be obtained AT ALL by retrying
   2. the measured success rate and attempts-to-first-success per lead  (-> findings doc)
   3. the forecast field itself, saved, so sigma(lead) leg 2 can diff it against the outcome

Windows are 2 h (equal start/end returns HTTP 500) and never cross midnight (single start_date).
"""
import json, os, statistics, sys, time
from datetime import datetime, timedelta
from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    RESULTS, tile_key)

CENTRE = (39.0100, -77.4460)
MAX_TRIES = 12
LEADS = [4, 6, 8, 10]
BACKOFF = 4

key = load_key()
banner("N-18  Do forecast windows appear on retry?   [PAID]")
before = credits_remaining(key)
now = datetime.now().replace(minute=0, second=0, microsecond=0)
print("   cycle_remaining BEFORE: %s   local now %s" % (format(before, ","), now.strftime("%H:%M")))
aoi = box_aoi(CENTRE[0], CENTRE[1], 2.0)

rows, calls = [], 0
for lead in LEADS:
    st = now + timedelta(hours=lead)
    en = st + timedelta(hours=2)
    if st.date() != en.date():
        print("\n   lead +%dh skipped: crosses midnight" % lead); continue
    payload = {"polygon_aoi": aoi, "granularity": 100, "analytic_type": "tcm",
               "date_time": {"start_date": st.strftime("%Y-%m-%d"),
                             "start_time": st.strftime("%H:00"),
                             "end_time": en.strftime("%H:00"), "filter_type": 2}}
    print("\n   LEAD +%2dh  target %s %s-%s   up to %d attempts"
          % (lead, st.strftime("%m-%d"), st.strftime("%H:00"), en.strftime("%H:00"), MAX_TRIES))
    outcomes, first_ok, tiles = [], None, None
    for a in range(1, MAX_TRIES + 1):
        calls += 1
        r = submit_poll(key, "heatmap", payload, "n18_L%02d" % lead)
        f = (r["result"].get("map_data") or {}).get("features") or [] if r.get("ok") else []
        if not r.get("ok"):
            outcomes.append("err")
        elif not f:
            outcomes.append("empty")
        else:
            outcomes.append("ok:%d" % len(f))
            if first_ok is None:
                first_ok, tiles = a, len(f)
        print("      attempt %2d: %s" % (a, outcomes[-1]))
        if first_ok:
            break
        time.sleep(BACKOFF)
    n_ok = sum(1 for o in outcomes if o.startswith("ok"))
    rows.append({"lead_h": lead, "date": st.strftime("%Y-%m-%d"), "start": st.strftime("%H:00"),
                 "end": en.strftime("%H:00"), "attempts": len(outcomes), "n_ok": n_ok,
                 "first_success_attempt": first_ok, "tiles": tiles, "outcomes": outcomes})
    print("      -> %s after %s attempts"
          % ("SUCCEEDED" if first_ok else "never succeeded", first_ok or len(outcomes)))

after = credits_remaining(key)
print("\n   %d calls.  cycle_remaining %s -> %s   SPEND %s"
      % (calls, format(before, ","), format(after, ","), format(before - after, ",")))

got = [r for r in rows if r["first_success_attempt"]]
print("\n   RESULT")
print("      %8s %10s %14s %8s" % ("lead", "attempts", "first success", "tiles"))
for r in rows:
    print("      %+7dh %10d %14s %8s"
          % (r["lead_h"], r["attempts"], r["first_success_attempt"] or "never", r["tiles"] or "-"))
print("      leads obtained by retrying: %d of %d" % (len(got), len(rows)))
if got:
    att = [r["first_success_attempt"] for r in got]
    print("      attempts to first success: min %d max %d mean %.1f"
          % (min(att), max(att), statistics.fmean(att)))
    print("      -> retry IS effective; sigma(lead) leg 1 captured at leads %s"
          % [r["lead_h"] for r in got])
else:
    print("      -> retrying up to %d times did NOT recover any forecast window today."
          % MAX_TRIES)
    print("         This is a measurement, not a conclusion about the product: FortyGuard")
    print("         confirms the forecast exists. Report the retry statistics and retest.")

json.dump({"issued_at": now.isoformat(), "centre": CENTRE, "rows": rows},
          open(os.path.join(RESULTS, "n18_manifest.json"), "w"), indent=1)
save_result("n18_retry.json", {"issued_at": now.isoformat(), "max_tries": MAX_TRIES,
                               "rows": rows, "n_leads_obtained": len(got), "n_calls": calls,
                               "before": before, "after": after})
