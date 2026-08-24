# -*- coding: utf-8 -*-
"""N-26  ---  DOES THE BOUND ACTUALLY COVER WHAT IT PROMISES?   PAID, one pair per day.

WHY THIS RANKS SECOND ONLY TO THE SHARPENING TEST
    The product is not a temperature prediction. It is a BOUND: "90 % of the time the intake stays
    below X." Everything downstream -- the released cooling margin, the staging decision, the whole
    commercial pitch -- is built on that number meaning what it says.

    Right now it is verified on ONE forecast/outcome pair. One pair cannot measure a 90 % rate. If
    the truth breaches the bound 30 % of the time out of sample, the core deliverable is broken no
    matter how good the physics is, and no amount of GPU or solver work fixes it.

    Like the sharpening test, this needs elapsed calendar days, so waiting until 18 Aug is the one
    choice that guarantees it cannot be fixed in time. Started 2026-08-12, it yields six independent
    day-pairs before the hackathon.

WHAT A "BOUND" MEANS HERE, PRECISELY
    Split conformal prediction, one-sided upper. Let d = outcome - forecast, per tile.

        calibrate   pool d over the CALIBRATION days; take the k-th smallest, where
                    k = ceil((n + 1) * (1 - alpha)), the finite-sample-valid index
        predict     bound = forecast + q
        score       coverage = fraction of tiles on a LATER day with outcome <= bound

    Signed rather than absolute residuals, because the decision only ever needs an upper limit --
    being cooler than predicted is never the failure. A one-sided bound is also tighter, and it
    absorbs any systematic warm or cool bias automatically instead of needing a separate correction.

THE FAILURE MODE THIS IS LOOKING FOR
    Conformal prediction guarantees coverage >= 1 - alpha only if the calibration days and the test
    day are exchangeable -- loosely, "drawn from the same weather". They are not. Days differ
    systematically: a humid day, a windy day, a frontal passage. So the honest question is not
    whether the mathematics is right (it is), but whether the day-to-day drift is small enough that
    a bound calibrated on last week still holds today. That is an empirical question about
    FortyGuard's forecast, and it is exactly what this measures.

PASS CONDITIONS, FIXED NOW, BEFORE ANY OUTCOME EXISTS
    P1  pooled out-of-sample coverage >= 0.85            (nominal is 0.90; 5 points of slack)
    P2  no single test day below 0.60                    (the agent acts daily, so one catastrophic
                                                          day is disqualifying, not averaged away)
    P3  at least 3 test days available                   (fewer cannot show a trend)

WHAT THIS DOES AND DOES NOT MEASURE -- state this before anyone asks
    DOES      whether a bound calibrated on earlier days covers, across 17,862 locations, on a day
              it has never seen. That is the right question for a multi-site deployment.
    DOES NOT  the breach rate at ONE fixed site over many days. That needs far more days than exist
              before 18 Aug. Tiles are also spatially correlated, so the effective sample is much
              smaller than the tile count and the finite-sample index is optimistic. Coverage is
              therefore also reported per spatial quadrant.

COST
    One forecast (~9.5 h lead) plus one outcome per day = 2 calls/day. Day 1 reuses the N-25
    fixtures for 2026-08-12 at zero extra cost, since N-25 already forecasts and scores the same
    14:00-16:00 window.

USAGE
    python test_n26_coverage.py collect    # safe to run any time; does only what is due today
    python test_n26_coverage.py report     # coverage, per test day and pooled
"""
import json, math, os, statistics, sys
from datetime import datetime, timedelta, timezone

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, RESULTS, FIXTURES, tile_key, site_now, site_window, lead_hours,
                    utc_now, site_tz, SITE_TZ_NAME,
                    classify_vendor, vendor_sentence, vendor_rec, is_billed, BILLED_CLASSES,
                    HEATMAP_CREDITS)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14          # same window as N-25, so day 1 is free
HORIZON_H = 12.0
ALPHA = 0.10                   # nominal 90 % one-sided coverage

# Comparability guard. The target HOUR is fixed at 14:00 site-local so every day scores the same
# decision-relevant window (the diurnal peak) and diurnal predictability is held constant. That
# leaves the LEAD free to vary with whatever time of day this happens to be run, and lead matters:
# a 2 h forecast is far better than a 10 h one, so a day collected late would show artificially
# high coverage and quietly flatter the result. Only accept leads in a band around the 9.41 h that
# N-25 used, and record the actual lead so the report can warn if the spread grows.
MIN_LEAD_H = 6.0
MAX_LEAD_H = 11.5
LEAD_SPREAD_WARN_H = 3.0

# ---- RETRY BUDGET, added 2026-08-19 after a vendor outage cost two whole day-pairs.
# The collector fires from a scheduled task and had exactly ONE attempt per day. A single transient
# failure therefore lost a pair permanently, because by the time anyone noticed, the lead had fallen
# below the comparability floor. Extra triggers now fire a few minutes apart (see HANDOFF section 4.2).
#
# They cost NOTHING when the first attempt succeeds -- `forecast_done` and `outcome_done` both
# short-circuit before any call. They only spend after a failure, which is exactly when we want them.
# This cap bounds the downside: during a multi-day outage the retries would otherwise burn
# 3 x 4,220 per day forever. Three attempts is enough to clear a glitch and cheap enough to ignore.
#
# OVERRIDABLE FROM THE ENVIRONMENT, added 2026-08-20. The cap exists to bound a runaway loop, not
# to ration credits -- and the two get confused. On a day when the vendor is faulty for hours, three
# attempts inside a 5.5 h in-band window can all land inside the fault while the window is still
# open, and the cap then throws away a recoverable pair to save 4,220 credits. A lost day-pair is
# UNRECOVERABLE; 4,220 credits is 0.2 % of the plan. Set N26_MAX_ATTEMPTS to raise it deliberately;
# the default stays conservative for the unattended scheduled runs.
#
# ---- SPLIT IN TWO 2026-08-21 (Session 4), AND THE SPLIT IS THE POINT.
# The single counter above conflated two different things because, until 2026-08-20, they were the
# same thing: every failed request cost 4,220. Then the vendor started failing for FREE -- `status:
# failed` and an indefinite `Processing` stall are both unbilled, while `completed` with no data is
# still charged. From that day a budget written to ration CREDITS was being spent by failures that
# cost NO credits. That is gotcha #101 (attempts vs billed calls) recurring one layer down: the
# ledger was taught the difference and the collector was not.
#
# So there are now two limits, because there are two risks and they are not the same risk:
#
#   MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY  the CREDIT budget. Counts only attempts the vendor
#                                         actually charged for. Three billed misses in a day is
#                                         12,660 credits and enough evidence of a vendor-side
#                                         condition (gotcha #59).
#   MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY   the RUNAWAY guard. Counts everything, billed or not, so a
#                                         vendor stalling for free cannot be probed without bound.
#                                         Higher, because a free attempt costs only wall-clock --
#                                         and wall-clock inside the in-band window is exactly what
#                                         the recovery watcher exists to spend.
#
# The honest limit of this change: on a day like 2026-08-21, whose four failures were ALL
# `completed`-with-no-data, every attempt was billed and the new split buys nothing. On a day like
# 2026-08-20, which stalled twice for free, it buys the whole window.
MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY = int(os.environ.get("N26_MAX_ATTEMPTS", "3"))
MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY = int(os.environ.get("N26_MAX_TOTAL_ATTEMPTS", "8"))
MANIFEST = os.path.join(RESULTS, "n26_manifest.json")

MIN_COVERAGE = 0.85            # P1
MIN_DAY_COVERAGE = 0.60        # P2
MIN_TEST_DAYS = 3              # P3


def field_max(result):
    feats = (result.get("map_data") or {}).get("features") or []
    out = {}
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[tile_key(la, lo)] = (v, la, lo)
    return out


def window_for(date_site):
    """The site-local target window on a given date. date_site is a date object."""
    start = datetime(date_site.year, date_site.month, date_site.day,
                     TARGET_HOUR_SITE, 0, tzinfo=site_tz())
    return site_window(start, WIN_H)


def call_window(key, aoi, dt_fields, tag):
    """One paid window. Returns (tiles_by_key or None, count or error string, RECORD).

    THE THIRD RETURN VALUE IS THE SESSION-4 ADDITION, and it is what lets the caller decide
    whether to try again. Before it, a failure was a sentence -- "completed but never populated
    after 59 polls over 604 s" -- and a sentence cannot be counted, compared or billed. The record
    carries the vendor's classification (`ok` / `completed_but_empty` / `terminal_<status>` /
    `stalled_in_processing` / `submit_rejected`), whether that class MOVES THE CREDIT METER, the
    activity id, the poll count and the elapsed time. Classification is `common.classify_vendor`,
    the same function the live agent uses -- not a second copy of the same judgement.
    """
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {k: v for k, v in dt_fields.items() if not k.startswith("_")}}
    r = submit_poll(key, "heatmap", p, tag)
    d = field_max(r["result"]) if r.get("result") else {}
    rec = vendor_rec(r, tiles=len(d))
    rec["class"] = cls = classify_vendor(rec)
    rec["billed"] = is_billed(cls)
    rec["credits_if_billed"] = HEATMAP_CREDITS if rec["billed"] else 0
    rec["sentence"] = vendor_sentence(cls, rec)
    rec["tag"] = tag
    rec["at_utc"] = utc_now().isoformat()
    if not r.get("ok"):
        return None, r.get("error"), rec
    if not d:
        # `submit_poll` reported ok, so `assert_non_empty` saw features -- yet field_max found no
        # usable tile. Different fault from an empty response and it must not wear its label.
        return None, "tiles present but none parsed into the lattice", rec
    return d, len(d), rec


# ---------------------------------------------------- the per-day attempt log
# WHY A LOG AND NOT A COUNTER. The manifest used to carry `forecast_attempts` (an integer) and
# `forecast_error` (the last sentence). Both are lossy in ways that already cost this project real
# money and real diagnosis time:
#   * gotcha #100 -- the spend ledger lost three calls because it read a MUTABLE SINGLE-SLOT field
#     that a later, unbilled call overwrote. A list cannot be overwritten by its successor.
#   * gotcha #124 -- the only fields that explain a rejection (HTTP status and body) were gone by
#     the time anyone asked, because the record kept the class and threw the reason away.
#   * The billing split needs per-attempt truth. "3 attempts" cannot be priced; "2 billed, 1 free"
#     can, and it is the difference between 8,440 credits and 12,660.
# So each attempt appends one complete record and nothing is ever rewritten. The old integer is
# still maintained alongside it, because `api_usage_ledger.py` and this file's own report read it,
# and a rename that breaks the ledger to tidy a field name is a bad trade.

def attempt_log(day):
    return day.setdefault("forecast_attempt_log", [])


def record_attempt(day, rec):
    """Append one attempt. The ONLY writer of the log, so the append cannot be forgotten."""
    log = attempt_log(day)
    log.append(rec)
    # Derived, never independently incremented: two counters for one quantity is gotcha #12.
    day["forecast_billed_attempts"] = sum(1 for r in log
                                          if r.get("leg") == "forecast" and r.get("billed"))
    day["forecast_credits_spent"] = day["forecast_billed_attempts"] * HEATMAP_CREDITS
    return rec


def billed_attempts(day):
    """Attempts on the FORECAST leg that moved the credit meter.

    Falls back to the plain attempt count for days recorded BEFORE the log existed (2026-08-18..21).
    That fallback is the conservative direction -- it treats every historical attempt as billed,
    which is what the ledger already assumes and what was true on 08-21.
    """
    log = [r for r in attempt_log(day) if r.get("leg") == "forecast"]
    if not log:
        return day.get("forecast_attempts", 0)
    return sum(1 for r in log if r.get("billed"))


def total_attempts(day):
    """Every attempt on the forecast leg, billed or not.

    Same pre-log fallback as `billed_attempts`, and it must have one: without it a day recorded
    before 2026-08-21 reports "4 billed of 3" beside "0 total of 8", which reads as a bug in the
    budget rather than a gap in the record. Two counters over one quantity have to agree about what
    they are counting.
    """
    log = [r for r in attempt_log(day) if r.get("leg") == "forecast"]
    return len(log) if log else day.get("forecast_attempts", 0)


def attempt_summary(day):
    """One line: what was tried today, how it failed, and what it cost."""
    log = attempt_log(day)
    if not log:
        n = day.get("forecast_attempts", 0)
        return ("%d attempt(s) recorded before per-attempt logging existed, so each is counted as "
                "billed" % n) if n else "no attempts recorded today"
    by = {}
    for r in log:
        by[r.get("class", "unknown")] = by.get(r.get("class", "unknown"), 0) + 1
    return ("today: %s  ->  %d billed (%s credits), %d free"
            % (", ".join("%d x %s" % (v, k) for k, v in sorted(by.items())),
               sum(1 for r in log if r.get("billed")),
               format(sum(1 for r in log if r.get("billed")) * HEATMAP_CREDITS, ","),
               sum(1 for r in log if not r.get("billed"))))


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    # first run: seed with day 1 pointing at the N-25 fixtures, which cost nothing extra
    m = {"created_utc": utc_now().isoformat(), "site_tz": SITE_TZ_NAME,
         "centre": list(CENTRE), "side_km": SIDE_KM, "granularity": GRAN, "win_h": WIN_H,
         "target_hour_site": TARGET_HOUR_SITE, "alpha": ALPHA,
         "min_coverage": MIN_COVERAGE, "min_day_coverage": MIN_DAY_COVERAGE,
         "days": {}, "errors": {}}
    d1 = site_now().date().isoformat()
    m["days"][d1] = {"date": d1, "forecast_tag": "n25_f_lead09.41", "forecast_lead_h": 9.41,
                     "forecast_done": True, "outcome_tag": "n25_outcome",
                     "outcome_done": False, "reused_from": "N-25"}
    return m


def write_manifest(m):
    json.dump(m, open(MANIFEST, "w"), indent=1, default=str)


def fixture_exists(tag):
    return bool(tag) and os.path.exists(os.path.join(FIXTURES, "%s.json" % tag))


# ----------------------------------------------------------------- collect
def collect():
    banner("N-26 collect  one forecast + one outcome, for the daily coverage record   [PAID]")
    m = load_manifest()
    key = load_key()
    before = credits_remaining(key)
    aoi = box_aoi(m["centre"][0], m["centre"][1], m["side_km"])
    today = site_now().date()
    print("   site local now %s   (site zone %s)"
          % (site_now().strftime("%Y-%m-%d %H:%M %Z"), SITE_TZ_NAME))
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    did = 0

    # ---- 1. today's forecast, if the window is still far enough ahead ----
    key_today = today.isoformat()
    day = m["days"].setdefault(key_today, {"date": key_today, "forecast_done": False,
                                           "outcome_done": False})
    if day.get("forecast_done"):
        print("\n   today's forecast: already recorded (%s)%s"
              % (day.get("forecast_tag"), " [reused from N-25]" if day.get("reused_from") else ""))
    else:
        w = window_for(today)
        lead = lead_hours(w["_start_utc"])
        print("\n   TODAY'S FORECAST  target %s %s-%s site-local, lead %.2f h"
              % (w["start_date"], w["start_time"], w["end_time"], lead))
        if lead <= 0:
            print("      SKIP: the window has already started at the site. Nothing to forecast.")
            day["forecast_error"] = "run too late; window already started"
        elif lead > MAX_LEAD_H:
            print("      SKIP: lead %.2f h is above the %.1f h comparability ceiling%s."
                  % (lead, MAX_LEAD_H, " (and the %.0f h horizon)" % HORIZON_H
                     if lead > HORIZON_H else ""))
            print("      Re-run in %.1f h. Nothing is lost by waiting." % (lead - MAX_LEAD_H))
        elif lead < MIN_LEAD_H:
            print("      SKIP: lead %.2f h is below the %.1f h comparability floor. A short-lead"
                  % (lead, MIN_LEAD_H))
            print("      forecast is much more accurate, so recording it would inflate coverage and")
            print("      flatter the result. Today is skipped deliberately -- run earlier tomorrow.")
            day["forecast_error"] = "lead %.2f h below comparability floor %.1f h" % (lead,
                                                                                      MIN_LEAD_H)
        elif billed_attempts(day) >= MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY:
            print("      SKIP: %d BILLED attempt(s) already made today and all failed (%s)."
                  % (billed_attempts(day), day.get("forecast_error")))
            print("      The CREDIT budget is spent -- %s credits on this day already. Not burning"
                  % format(billed_attempts(day) * HEATMAP_CREDITS, ","))
            print("      another %s on the same day: a repeated zero-tile answer is a vendor-side"
                  % format(HEATMAP_CREDITS, ","))
            print("      condition, not something a fourth identical request will fix (gotcha #59).")
            print("      %s" % attempt_summary(day))
        elif total_attempts(day) >= MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY:
            # The runaway guard, not the credit guard. Reaching this means the vendor has been
            # failing for FREE all day -- which costs nothing and must still terminate.
            print("      SKIP: %d attempts today (the runaway ceiling), though only %d were billed."
                  % (total_attempts(day), billed_attempts(day)))
            print("      Free failures cost credits nothing and wall-clock something. Stopping.")
            print("      %s" % attempt_summary(day))
        else:
            tag = "n26_f_%s" % key_today
            day["forecast_attempts"] = day.get("forecast_attempts", 0) + 1
            write_manifest(m)          # record the attempt BEFORE the call, so a crash still counts
            d, n, rec = call_window(key, aoi, w, tag)
            rec["lead_h"] = round(lead, 3)
            rec["leg"] = "forecast"
            record_attempt(day, rec)   # APPENDS -- gotcha #100, never a single overwritten slot
            if d is None:
                day["forecast_error"] = n
                m["errors"][tag] = n
                print("      FAILED: %s" % rec["sentence"])
                print("      class=%s  billed=%s  -> billed %d of %d, total %d of %d"
                      % (rec["class"], "YES %s credits" % format(HEATMAP_CREDITS, ",")
                         if rec["billed"] else "no, FREE",
                         billed_attempts(day), MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
                         total_attempts(day), MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY))
            else:
                day.update({"forecast_tag": tag, "forecast_lead_h": round(lead, 3),
                            "forecast_done": True, "forecast_n": n,
                            "forecast_mean": round(statistics.fmean(v[0] for v in d.values()), 4),
                            "forecast_issued_utc": utc_now().isoformat()})
                print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","),
                                                                     day["forecast_mean"]))
            did += 1
            write_manifest(m)

    # ---- 2. outcomes for any earlier day whose window has elapsed ----------
    for dk in sorted(m["days"]):
        day = m["days"][dk]
        if day.get("outcome_done") or not day.get("forecast_done"):
            continue
        dt = datetime.fromisoformat(dk).date()
        w = window_for(dt)
        if utc_now() < w["_end_utc"] + timedelta(minutes=15):
            print("\n   outcome for %s: window has not finished yet (ends %s UTC)"
                  % (dk, w["_end_utc"].strftime("%m-%d %H:%M")))
            continue
        tag = day.get("outcome_tag") or ("n26_h_%s" % dk)
        if fixture_exists(tag):
            day["outcome_done"] = True
            print("\n   outcome for %s: fixture already present (%s)" % (dk, tag))
            write_manifest(m)
            continue
        print("\n   OUTCOME for %s  target %s-%s site-local" % (dk, w["start_time"], w["end_time"]))
        d, n, rec = call_window(key, aoi, w, tag)
        rec["leg"] = "outcome"
        record_attempt(day, rec)
        if d is None:
            day["outcome_error"] = n
            m["errors"][tag] = n
            print("      FAILED: %s" % rec["sentence"])
            print("      class=%s  billed=%s" % (rec["class"], "yes" if rec["billed"] else "no, FREE"))
        else:
            day.update({"outcome_tag": tag, "outcome_done": True, "outcome_n": n,
                        "outcome_mean": round(statistics.fmean(v[0] for v in d.values()), 4),
                        "outcome_fetched_utc": utc_now().isoformat()})
            print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","),
                                                                 day["outcome_mean"]))
        did += 1
        write_manifest(m)

    after = credits_remaining(key)
    m["credits_last_before"], m["credits_last_after"] = before, after
    write_manifest(m)
    pairs = sum(1 for d in m["days"].values()
                if d.get("forecast_done") and d.get("outcome_done"))
    print("\n   %d call(s) this run.  complete day-pairs: %d  (need %d test days, so %d pairs)"
          % (did, pairs, MIN_TEST_DAYS, MIN_TEST_DAYS + 1))
    print("   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))
    print("   run this again tomorrow at about the same time (site window must be < %.0f h ahead)"
          % HORIZON_H)
    return 0


# ----------------------------------------------------------------- dry run
def dryrun():
    """Say exactly what `collect` would do RIGHT NOW, and make ZERO API calls.

    WHY THIS EXISTS. The collector is on a scheduled task and its correctness depends entirely on
    the lead that the firing time produces -- a quantity nobody could inspect without spending
    4,220 credits to watch it happen. Two whole day-pairs were already lost to a vendor outage, and
    a third would have been lost silently if the schedule had ever drifted out of the 6.0-11.5 h
    comparability band, because an out-of-band run SKIPS by design and looks like a clean exit.

    This reads the manifest, computes the window and the true lead through the same
    site_window()/lead_hours() helpers the real path uses, and prints the decision. It touches no
    endpoint and needs no key, so it can be run as often as you like.
    """
    banner("N-26 dry run   what collect() would do right now.  ZERO API CALLS, no key read.")
    m = load_manifest()
    today = site_now().date()
    sn = site_now()
    print("   machine local        : %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("   UTC                  : %s" % utc_now().strftime("%Y-%m-%d %H:%M:%S"))
    print("   site local (%s) : %s" % (SITE_TZ_NAME, sn.strftime("%Y-%m-%d %H:%M:%S %z")))

    w = window_for(today)
    lead = lead_hours(w["_start_utc"])
    day = m["days"].get(today.isoformat(), {})
    print("\n   TODAY'S FORECAST TARGET  %s %s-%s site-local  (fixed hour %d for comparability)"
          % (w["start_date"], w["start_time"], w["end_time"], TARGET_HOUR_SITE))
    print("   window start (UTC)   : %s" % w["_start_utc"].strftime("%Y-%m-%d %H:%M"))
    print("   LEAD RIGHT NOW       : %.2f h        band %.1f-%.1f h" % (lead, MIN_LEAD_H, MAX_LEAD_H))

    if day.get("forecast_done"):
        act = "NO CALL -- today's forecast is already recorded (%s)" % day.get("forecast_tag")
    elif lead <= 0:
        act = "SKIP -- the window has already started; nothing left to forecast"
    elif lead > MAX_LEAD_H:
        act = ("SKIP -- lead is %.2f h above the ceiling; re-run in %.1f h"
               % (lead - MAX_LEAD_H, lead - MAX_LEAD_H))
    elif lead < MIN_LEAD_H:
        act = ("SKIP -- lead is %.2f h below the %.1f h floor. A short-lead forecast is far more "
               "accurate, so recording it would FLATTER coverage" % (MIN_LEAD_H - lead, MIN_LEAD_H))
    elif billed_attempts(day) >= MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY:
        act = ("SKIP -- the CREDIT budget is spent: %d billed attempt(s) of %d"
               % (billed_attempts(day), MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY))
    elif total_attempts(day) >= MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY:
        act = ("SKIP -- the runaway ceiling is reached: %d attempts of %d, only %d billed"
               % (total_attempts(day), MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY,
                  billed_attempts(day)))
    else:
        act = ("WOULD CALL -- one paid forecast, %s credits, tag n26_f_%s"
               % (format(HEATMAP_CREDITS, ","), today.isoformat()))
    print("   ACTION               : %s" % act)

    # ---- the two budgets, reported apart, because they are two different risks --------
    print("\n   TODAY'S RETRY BUDGETS (split 2026-08-21: a free failure must not spend a credit"
          " budget)")
    print("      billed attempts    : %d of %d      %s credits committed today"
          % (billed_attempts(day), MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
             format(billed_attempts(day) * HEATMAP_CREDITS, ",")))
    print("      total attempts     : %d of %d      (the runaway guard; free failures land here"
          " only)" % (total_attempts(day), MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY))
    print("      %s" % attempt_summary(day))
    if attempt_log(day):
        print("      per attempt:")
        for r in attempt_log(day):
            print("         %s  %-22s %-6s lead %s  %s"
                  % (str(r.get("at_utc"))[11:19], r.get("class"),
                     "BILLED" if r.get("billed") else "free",
                     ("%.2f h" % r["lead_h"]) if r.get("lead_h") is not None else "   n/a",
                     (r.get("activity_id") or "-")[:8]))

    # ---- the window of firing times that WOULD be in band today ------------
    lo = w["_start_utc"] - timedelta(hours=MAX_LEAD_H)
    hi = w["_start_utc"] - timedelta(hours=MIN_LEAD_H)
    off_h = round((datetime.now().replace(tzinfo=timezone.utc) - utc_now()).total_seconds() / 3600)
    print("\n   ANY RUN INSIDE THIS WINDOW LANDS IN BAND TODAY:")
    print("      %s to %s UTC" % (lo.strftime("%H:%M"), hi.strftime("%H:%M")))
    print("      %s to %s machine-local (UTC%+d)"
          % ((lo + timedelta(hours=off_h)).strftime("%H:%M"),
             (hi + timedelta(hours=off_h)).strftime("%H:%M"), off_h))
    print("      -> that is a %.1f h window, so more than one scheduled trigger fits. A second and"
          % ((hi - lo).total_seconds() / 3600))
    print("         third trigger cost NOTHING when the first succeeds, because `forecast_done`")
    print("         and `outcome_done` both short-circuit. They only spend after a failure.")

    # ---- pending outcome legs ---------------------------------------------
    pend = []
    for dk in sorted(m["days"]):
        d = m["days"][dk]
        if d.get("outcome_done") or not d.get("forecast_done"):
            continue
        wd = window_for(datetime.fromisoformat(dk).date())
        pend.append((dk, utc_now() >= wd["_end_utc"] + timedelta(minutes=15)))
    print("\n   PENDING OUTCOME LEGS : %s"
          % (", ".join("%s%s" % (k, " (ready)" if r else " (window not finished)")
                       for k, r in pend) if pend else "none -- no outcome debt"))

    done = sum(1 for d in m["days"].values()
               if d.get("forecast_done") and d.get("outcome_done"))
    # THE CEILING IS SET BY THE CALIBRATION SET, AND THE OFF-BY-ONE MATTERS.
    # With n calibration residuals the largest attainable one-sided quantile is the maximum, which
    # covers at most n/(n+1). So a 90 % bound needs n = 9 CALIBRATION days -- and scoring it needs a
    # test day that is not one of them, hence 10 PAIRS, not 9. The first version of this line said 9
    # and would have had us stop one pair short of the claim, at 8/9 = 88.9 %.
    ncal_needed = 1
    while ncal_needed / (ncal_needed + 1.0) < (1.0 - ALPHA):
        ncal_needed += 1
    pairs_needed = ncal_needed + 1
    print("\n   COMPLETE DAY-PAIRS   : %d   (n calibration days cap attainable coverage at"
          " n/(n+1) = %.1f %%)" % (done, 100.0 * done / (done + 1)))
    print("   FOR A %.0f %% BOUND      : %d calibration days -> %d PAIRS total  (%d more needed)"
          % (100 * (1 - ALPHA), ncal_needed, pairs_needed, max(0, pairs_needed - done)))
    if m.get("errors"):
        print("\n   RECORDED FAILURES (kept so a recurrence is visible, not silently retried):")
        for k, v in m["errors"].items():
            print("      %-24s %s" % (k, v[:64]))
    return 0


# ----------------------------------------------------------------- report
def _q_index(n, alpha):
    """Finite-sample-valid split-conformal index: ceil((n+1)(1-alpha)), clipped."""
    return min(n - 1, math.ceil((n + 1) * (1.0 - alpha)) - 1)


def report():
    banner("N-26 report  out-of-sample coverage of the one-sided conformal bound")
    if not os.path.exists(MANIFEST):
        print("   no manifest -- run 'collect' first.")
        return 2
    m = json.load(open(MANIFEST))

    pairs = []
    for dk in sorted(m["days"]):
        day = m["days"][dk]
        ft, ot = day.get("forecast_tag"), day.get("outcome_tag")
        if not (fixture_exists(ft) and fixture_exists(ot)):
            continue
        F = field_max(json.load(open(os.path.join(FIXTURES, "%s.json" % ft))))
        H = field_max(json.load(open(os.path.join(FIXTURES, "%s.json" % ot))))
        keys = [k for k in F if k in H]
        if len(keys) < 100:
            continue
        d = {k: H[k][0] - F[k][0] for k in keys}          # outcome - forecast
        pairs.append({"date": dk, "lead_h": day.get("forecast_lead_h"), "n": len(keys),
                      "d": d, "F": F, "H": H,
                      "mean_d": statistics.fmean(d.values()),
                      "sd_d": statistics.pstdev(d.values())})

    print("   complete day-pairs found: %d" % len(pairs))
    if not pairs:
        print("   nothing to score yet. Each pair needs a forecast and its elapsed outcome.")
        return 2

    print("\n   %-12s %8s %10s %10s %10s" % ("date", "lead h", "n tiles", "mean d", "sd d"))
    for p in pairs:
        print("   %-12s %8s %10s %+10.4f %10.4f"
              % (p["date"], "%.2f" % p["lead_h"] if p["lead_h"] else "-",
                 format(p["n"], ","), p["mean_d"], p["sd_d"]))
    print("   (d = outcome - forecast, per tile. A positive mean means the forecast runs COOL.)")

    leads = [p["lead_h"] for p in pairs if p["lead_h"]]
    lead_spread = (max(leads) - min(leads)) if leads else 0.0
    if lead_spread > LEAD_SPREAD_WARN_H:
        print("\n   *** LEAD SPREAD WARNING: %.1f h across days (%.2f to %.2f) ***"
              % (lead_spread, min(leads), max(leads)))
        print("      Coverage is only comparable across days at a similar lead -- a short-lead")
        print("      forecast is more accurate and inflates coverage. Treat the pooled number as")
        print("      indicative and quote the per-day column instead.")
    elif leads:
        print("   lead spread across days: %.1f h (%.2f to %.2f) -- comparable"
              % (lead_spread, min(leads), max(leads)))

    if len(pairs) < 2:
        print("\n   only one pair: a bound can be calibrated OR tested, not both. Need >= 2.")
        save_result("n26_coverage.json", {"n_pairs": len(pairs), "pass": None,
                                          "days": [{k: p[k] for k in
                                                    ("date", "lead_h", "n", "mean_d", "sd_d")}
                                                   for p in pairs]})
        return 2

    # ---- sequential out-of-sample coverage: calibrate on days < k, test on day k ----
    print("\n   SEQUENTIAL OUT-OF-SAMPLE COVERAGE  (calibrate on all earlier days, test on the next)")
    print("   %-12s %9s %10s %10s %11s %s"
          % ("test day", "cal days", "cal n", "halfwidth", "coverage", "quadrants NE NW SE SW"))
    tests = []
    for i in range(1, len(pairs)):
        cal = [x for p in pairs[:i] for x in p["d"].values()]
        cal.sort()
        q = cal[_q_index(len(cal), ALPHA)]
        tp = pairs[i]
        breaches = [k for k, v in tp["d"].items() if v > q]
        cov = 1.0 - len(breaches) / tp["n"]
        lats = [tp["F"][k][1] for k in tp["d"]]
        lons = [tp["F"][k][2] for k in tp["d"]]
        mla, mlo = statistics.median(lats), statistics.median(lons)
        quad = {"NE": [0, 0], "NW": [0, 0], "SE": [0, 0], "SW": [0, 0]}
        for k, v in tp["d"].items():
            qq = ("N" if tp["F"][k][1] >= mla else "S") + ("E" if tp["F"][k][2] >= mlo else "W")
            quad[qq][1] += 1
            if v <= q:
                quad[qq][0] += 1
        qcov = {kk: (vv[0] / vv[1] if vv[1] else None) for kk, vv in quad.items()}
        tests.append({"test_date": tp["date"], "n_cal_days": i, "n_cal": len(cal),
                      "halfwidth": q, "coverage": cov, "n_breach": len(breaches),
                      "quad_coverage": qcov})
        print("   %-12s %9d %10s %10.4f %10.1f%%  %s"
              % (tp["date"], i, format(len(cal), ","), q, 100 * cov,
                 " ".join("%.0f%%" % (100 * qcov[x]) if qcov[x] is not None else " - "
                          for x in ("NE", "NW", "SE", "SW"))))

    covs = [t["coverage"] for t in tests]
    pooled = statistics.fmean(covs)
    worst = min(covs)
    print("\n   RESULT")
    print("      nominal coverage (1 - alpha)      : %.0f %%" % (100 * (1 - ALPHA)))
    print("      pooled out-of-sample coverage     : %.1f %%  over %d test day(s)"
          % (100 * pooled, len(tests)))
    print("      worst single test day             : %.1f %%" % (100 * worst))
    print("      shortfall vs nominal              : %+.1f points" % (100 * (pooled - (1 - ALPHA))))

    print("\n   HOW TO READ A SHORTFALL")
    print("      Conformal coverage is guaranteed only if the calibration days and the test day are")
    print("      exchangeable. They are not -- weather drifts. So a shortfall is not a bug in the")
    print("      mathematics, it measures how far FortyGuard's forecast error drifts day to day.")
    print("      The operational fix is a shorter calibration window or a per-day inflation factor,")
    print("      and this number is what tells you whether either is needed.")

    p1 = pooled >= MIN_COVERAGE
    p2 = worst >= MIN_DAY_COVERAGE
    p3 = len(tests) >= MIN_TEST_DAYS
    ok = p1 and p2 and p3
    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE ANY OUTCOME EXISTED")
    print("      P1 pooled coverage >= %.0f %%   : %s  (%.1f %%)"
          % (100 * MIN_COVERAGE, p1, 100 * pooled))
    print("      P2 no test day < %.0f %%        : %s  (%.1f %%)"
          % (100 * MIN_DAY_COVERAGE, p2, 100 * worst))
    print("      P3 at least %d test days       : %s  (%d)" % (MIN_TEST_DAYS, p3, len(tests)))
    print()
    verdict(ok,
            "PASS - a bound calibrated on earlier days covers %.1f %% of 17k locations on days it "
            "has never seen, against a %.0f %% promise, worst day %.1f %%. The central product claim "
            "is measured out of sample rather than asserted."
            % (100 * pooled, 100 * (1 - ALPHA), 100 * worst),
            ("NOT YET DECIDABLE - only %d test day(s) available, %d required. Keep collecting; this "
             "is a calendar limit, not a result." % (len(tests), MIN_TEST_DAYS)) if not p3 else
            ("FAIL - out-of-sample coverage is %.1f %% against a %.0f %% promise (worst day %.1f %%). "
             "The bound does not mean what it says across days. Do NOT quote a 90 %% bound. Either "
             "shorten the calibration window, inflate per day, or state the measured rate instead of "
             "the nominal one -- and say which you did."
             % (100 * pooled, 100 * (1 - ALPHA), 100 * worst)))

    save_result("n26_coverage.json", {
        "alpha": ALPHA, "nominal_coverage": 1 - ALPHA,
        "days": [{k: p[k] for k in ("date", "lead_h", "n", "mean_d", "sd_d")} for p in pairs],
        "tests": tests, "pooled_coverage": pooled, "worst_day_coverage": worst,
        "n_test_days": len(tests),
        "lead_spread_h": lead_spread, "lead_range_h": [min(leads), max(leads)] if leads else None,
        "leads_comparable": lead_spread <= LEAD_SPREAD_WARN_H,
        "measures": "coverage across ~17.9k locations on an unseen day, bound calibrated on "
                    "earlier days",
        "does_not_measure": "breach rate at one fixed site over many days; tiles are spatially "
                            "correlated so the effective sample is far below the tile count",
        "p1_pooled": p1, "p2_worst_day": p2, "p3_enough_days": p3, "pass": ok})
    return 0 if ok else 1


# ----------------------------------------------------------------- selftest
def selftest():
    """THE COLLECTOR'S OWN LOGIC, WITH ZERO NETWORK AND NO KEY READ.

    WHY THIS EXISTS. The retry budget is the one piece of this program nobody can watch work: it
    only ever fires unattended, from a scheduled task, on a day the vendor is already failing. Its
    previous version was wrong for a day and a half -- counting free failures against a credit
    budget -- and nothing could have caught that, because the only way to exercise it was to spend
    4,220 credits and wait ten minutes for a failure.

    So the failure shapes are fed in as RECORDS. Each of the three measured vendor faults is
    replayed against the real `classify_vendor` and the real budget helpers, and the assertions are
    about credits: how many the day has committed, and whether another attempt is permitted.
    """
    banner("N-26 selftest   the retry budget and the vendor classifier.  ZERO API CALLS.")
    fails = []

    def ck(name, ok, detail=""):
        (fails.append(name) if not ok else None)
        print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))

    # ---- 1. the three measured failure shapes, and what each one costs -----------------
    # Every one of these is a real observation, not an invented case:
    #   completed_but_empty   2026-08-21, "completed but never populated after 59 polls", BILLED
    #   terminal_failed       2026-08-20 diag63, `status: failed`,                        FREE
    #   stalled_in_processing 2026-08-20 activity a89fef3f, 33 polls over 307 s,          FREE
    #   submit_rejected       2026-08-20, 1 of 12 identical submits rejected (gotcha #124) FREE
    shapes = [
        ("ok", {"submit_http": 200, "activity_id": "9995dfd7", "tiles": 17785,
                "terminal_status": "completed"}, True),
        ("completed_but_empty", {"submit_http": 200, "activity_id": "aaaaaaaa", "tiles": 0,
                                 "terminal_status": "completed"}, True),
        ("terminal_failed", {"submit_http": 200, "activity_id": "bbbbbbbb", "tiles": 0,
                             "terminal_status": "failed"}, False),
        ("stalled_in_processing", {"submit_http": 200, "activity_id": "a89fef3f", "tiles": 0,
                                   "terminal_status": None,
                                   "statuses_seen": ["processing"]}, False),
        ("submit_rejected", {"submit_http": 429, "activity_id": None, "tiles": 0}, False),
    ]
    for want_cls, rec, want_billed in shapes:
        got = classify_vendor(rec)
        ck("classifies %s" % want_cls, got == want_cls, "got %s" % got)
        ck("  ...and prices it %s" % ("BILLED" if want_billed else "FREE"),
           is_billed(got) == want_billed,
           "%s credits" % format(HEATMAP_CREDITS if want_billed else 0, ","))

    # An unrecognised class must be assumed BILLED. Guessing "free" under-reports spend, and a
    # ledger with a blind spot is worse than no ledger (gotcha #103).
    ck("an UNKNOWN outcome is assumed billed, never free",
       is_billed(classify_vendor({"submit_http": 200, "activity_id": "c", "tiles": 0,
                                  "terminal_status": None, "statuses_seen": ["something new"]})),
       "unknown -> billed, the conservative direction")

    # ---- 2. THE BUDGET. This is the bug the split exists to prevent. -------------------
    def day_with(classes):
        d = {}
        for i, c in enumerate(classes):
            record_attempt(d, {"leg": "forecast", "class": c, "billed": is_billed(c),
                               "at_utc": "2026-08-21T0%d:00:00" % i})
        return d

    free_day = day_with(["stalled_in_processing"] * 3)
    ck("three FREE failures leave the credit budget untouched",
       billed_attempts(free_day) == 0
       and billed_attempts(free_day) < MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
       "0 of %d billed -- the collector may try again" % MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY)
    ck("...and cost 0 credits", free_day["forecast_credits_spent"] == 0, "0")
    ck("...but still count against the runaway ceiling",
       len(attempt_log(free_day)) == 3, "3 of %d" % MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY)

    billed_day = day_with(["completed_but_empty"] * 3)
    ck("three BILLED failures exhaust the credit budget",
       billed_attempts(billed_day) >= MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
       "%d of %d" % (billed_attempts(billed_day), MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY))
    ck("...and are priced exactly",
       billed_day["forecast_credits_spent"] == 3 * HEATMAP_CREDITS,
       "%s credits" % format(billed_day["forecast_credits_spent"], ","))

    mixed = day_with(["stalled_in_processing", "completed_but_empty", "terminal_failed",
                      "completed_but_empty"])
    ck("a MIXED day counts only what was charged",
       billed_attempts(mixed) == 2 and len(attempt_log(mixed)) == 4,
       "4 attempts, 2 billed, %s credits" % format(mixed["forecast_credits_spent"], ","))

    # THE RUNAWAY GUARD MUST BIND EVEN WHEN NOTHING IS BILLED, or a vendor stalling for free is an
    # unbounded loop. This is the failure mode the split introduces, so it is the one to pin.
    runaway = day_with(["stalled_in_processing"] * MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY)
    ck("a vendor failing FOREVER for free still terminates",
       len(attempt_log(runaway)) >= MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY
       and billed_attempts(runaway) == 0,
       "%d free attempts hits the ceiling with 0 credits spent" % len(attempt_log(runaway)))
    ck("the runaway ceiling sits ABOVE the credit budget, or it would mask it",
       MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY > MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
       "%d > %d" % (MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY,
                    MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY))

    # ---- 3. THE LOG APPENDS. Gotcha #100 was a single overwritten slot losing three calls. ----
    seq = day_with(["completed_but_empty", "stalled_in_processing"])
    record_attempt(seq, {"leg": "forecast", "class": "ok", "billed": True, "at_utc": "z"})
    ck("the attempt log APPENDS and never overwrites",
       [r["class"] for r in attempt_log(seq)]
       == ["completed_but_empty", "stalled_in_processing", "ok"],
       "3 records in submission order")
    ck("the OUTCOME leg is logged but never charged to the FORECAST budget",
       billed_attempts(day_with([]) | {"forecast_attempt_log":
                                       [{"leg": "outcome", "class": "completed_but_empty",
                                         "billed": True}]}) == 0,
       "an outcome-leg failure leaves the forecast budget alone")

    # ---- 4. BACK-COMPATIBILITY with the four days recorded before the log existed -------
    legacy = {"forecast_attempts": 4, "forecast_error": "completed but never populated"}
    ck("a pre-log day counts every attempt as billed, the safe direction",
       billed_attempts(legacy) == 4, "4 attempts -> 4 billed (08-18..08-21 are all pre-log)")

    # ---- 5. the evidence a failure must carry -----------------------------------------
    rec = vendor_rec({"error": "completed but never populated after 59 polls over 604 s",
                      "submit_http": 200, "aid": "9995dfd7-1111", "terminal_status": "completed",
                      "statuses_seen": ["processing", "completed"], "secs": 604.0, "polls": 59,
                      "empty_completed_polls": 59}, tiles=0)
    cls = classify_vendor(rec)
    ck("a failure record keeps the activity id, poll count and elapsed time",
       rec["activity_id"] == "9995dfd7-1111" and rec["polls"] == 59 and rec["elapsed_s"] == 604.0,
       vendor_sentence(cls, rec)[:78])
    rej = vendor_rec({"error": "submit: HTTP 429 slow down", "submit_http": 429,
                      "submit_error_body": "{\"detail\":\"rate limited\"}"}, tiles=0)
    ck("a REJECTION keeps the body that explains it (gotcha #124)",
       "rate limited" in vendor_sentence(classify_vendor(rej), rej),
       "the reason survives into the sentence")

    print()
    verdict(not fails,
            "PASS - the retry budget counts CREDITS, the runaway guard counts ATTEMPTS, and all "
            "three measured vendor failure shapes are classified and priced correctly with no "
            "network call and no key read.",
            "FAIL - %s" % ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "collect").lower()
    sys.exit({"collect": collect, "report": report, "dryrun": dryrun,
              "dry": dryrun, "selftest": selftest}.get(mode, collect)())
