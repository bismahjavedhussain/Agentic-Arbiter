# -*- coding: utf-8 -*-
"""N-26 RECOVERY WATCHER  ---  spend the whole in-band window, not the first 45 minutes of it.

THE DEFECT THIS EXISTS FOR, AND IT COST A DAY-PAIR WE CANNOT GET BACK
    The collector fires from three Windows scheduled tasks at 13:30, 13:50 and 14:15 PKT. The
    window in which a call is COMPARABLE with the rest of the series -- the lead between 6.0 and
    11.5 hours before a 14:00 site-local target -- runs from 11:30 to 17:00 PKT. That is five and a
    half hours of opportunity, and the three triggers use the first forty-five minutes of it.

    On 2026-08-20 FortyGuard's forecast path was down all morning, took all three attempts, and
    then RECOVERED at about 12:5x UTC. Nobody was watching. By then the lead had fallen to 5.15 h,
    below the comparability floor, and the day's pair was lost -- to a service that was, by that
    point, working. The recovery is in the record (HANDOFF section 4.0a): a real forecast window,
    17,785 tiles, 39.8 s. We simply were not asking any more.

WHAT IT DOES
    It watches the clock and the manifest, and it re-runs the ONE code path that knows how to bank
    a pair -- `test_n26_coverage.collect()`. It writes no API call of its own. Every attempt it
    makes is a collector attempt, subject to the collector's own two budgets, so this program
    cannot spend anything the collector would have refused.

    Its only real decision is WHEN to try again, and that decision is taken from the billing
    partition rather than from a timer:

        after a BILLED failure (`completed` with no data, 4,220 charged)
            space the remaining billed attempts evenly across the remaining in-band window. A
            billed attempt is scarce -- three a day -- so the question is where to place probes to
            most likely overlap a recovery, and even spacing is the answer when you know nothing
            about when the recovery will come.

        after a FREE failure (`status: failed`, or an indefinite `Processing` stall)
            try again almost at once. It cost nothing, and a vendor mid-recovery is exactly the
            state in which a stall is followed by a success.

WHAT IT CANNOT DO, SAID PLAINLY
    There is NO free probe for "does the forecast work right now". A past-window request worked
    throughout the outage, so it cannot discriminate; the forecast request IS the test, and it
    costs 4,220 when it comes back `completed` with nothing in it. So this watcher does not detect
    recovery and then spend -- it spends in order to detect. On a day whose failures are all billed
    (2026-08-21: four of four) it buys nothing the three scheduled tasks did not already buy. On a
    day whose failures are free (2026-08-20: a stall and a `failed`) it can probe the whole window
    for zero credits. Both cases are real and neither is the general case.

    It also cannot make a late pair as good as an early one. A shorter lead is an easier forecast,
    so a pair banked at a 6.5 h lead will tend to flatter coverage against a series calibrated
    around 9.4 h. That is why `MIN_LEAD_H` exists and why the report already warns when the spread
    across days exceeds 3 h. The watcher prints the projected spread before each attempt and after
    a successful bank. A pair at the bottom of the band is worth having and it is not free of cost:
    both halves of that are true and the number that shows it is on screen.

USAGE
    python n26_recovery_watch.py plan                  # zero calls, no key read. What it would do.
    python n26_recovery_watch.py watch --allow-paid     # the real thing. Attended, deliberate.
    python n26_recovery_watch.py selftest              # the pacing arithmetic, zero network

EXIT CODES -- because a green scheduled task means only that python exited (gotcha #96)
    0  the forecast leg is banked (or already was)
    2  the in-band window closed with no pair
    3  a budget stopped it: the credit budget, or the runaway ceiling
    4  nothing to do inside the wall-clock limit given
    5  refused: `watch` without --allow-paid
"""
import json
import os
import sys
import time
from datetime import timedelta

import test_n26_coverage as N26
from common import (banner, recent_vendor_record, utc_now, lead_hours, site_now, HEATMAP_CREDITS,
                    SITE_TZ_NAME)

# ---- PACING. One hand-chosen constant in this file, and it is labelled because the project's own
# test is "point at the constant".
#
# MIN_ATTEMPT_SPACING_S is a courtesy floor between the STARTS of two attempts. It is not derived
# from anything measured, and the evidence that pacing matters at all is n=1: on 2026-08-20 one of
# twelve otherwise-identical submits was rejected, which points at a rate limit but does not
# establish one (gotcha #124). Two things make it safe to have anyway:
#   1. It cannot bind in practice. The runaway ceiling is 8 attempts; 8 x 300 s is 40 minutes
#      against a 5.5 hour window, so the CEILING stops the loop long before the floor paces it.
#   2. A failing attempt already occupies up to 600 s inside `submit_poll`'s own poll ceiling, so
#      for every slow failure the real spacing is set by the attempt, not by this number.
# If it were load-bearing it would need measuring. It is not, and that is why it is allowed to be
# a constant.
MIN_ATTEMPT_SPACING_S = 300

HEARTBEAT_S = 60          # how often a sleeping watcher says it is still alive, presentation only


# ---------------------------------------------------------------- the window
def window_state(now=None):
    """Everything time-dependent, computed through the collector's OWN helpers.

    Nothing here re-derives a window or a lead. `window_for` and `lead_hours` are the functions the
    paid path uses, and gotcha #64 in this project is "I substituted my own arithmetic for a
    measurement twice, on the same number". So this reads them.
    """
    now = now or utc_now()
    today = now.astimezone(N26.site_tz()).date()
    w = N26.window_for(today)
    lead = lead_hours(w["_start_utc"], now)
    # The interval of wall-clock times whose lead lands inside the comparability band.
    opens = w["_start_utc"] - timedelta(hours=N26.MAX_LEAD_H)
    closes = w["_start_utc"] - timedelta(hours=N26.MIN_LEAD_H)
    return {"now": now, "date": today.isoformat(), "window": w, "lead_h": lead,
            "opens": opens, "closes": closes,
            "in_band": opens <= now <= closes,
            "seconds_until_open": max(0.0, (opens - now).total_seconds()),
            "seconds_until_close": (closes - now).total_seconds()}


def day_record(manifest, date_iso):
    return (manifest.get("days") or {}).get(date_iso) or {}


def budgets(day):
    """What is left of each budget. Read through the collector's helpers, never recounted here."""
    billed = N26.billed_attempts(day)
    total = N26.total_attempts(day)
    return {"billed_used": billed, "billed_left": max(0, N26.MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY
                                                      - billed),
            "total_used": total, "total_left": max(0, N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY
                                                   - total),
            "credits_committed": billed * HEATMAP_CREDITS}


def next_gap_s(last_was_billed, billed_left, seconds_until_close):
    """How long to wait before trying again. The one piece of judgement in this program.

    A FREE failure is retried at the floor: it cost nothing, and a stall is the state a recovering
    vendor passes through.

    A BILLED failure spaces what remains evenly across what remains of the window, dividing by
    `billed_left + 1` rather than `billed_left` -- so the last attempt does not land against the
    closing edge, where the lead is at its worst and a missed sleep loses the pair outright.

    Returns None when there is no point waiting at all.
    """
    if seconds_until_close <= 0:
        return None
    if not last_was_billed:
        gap = MIN_ATTEMPT_SPACING_S
    elif billed_left <= 0:
        return None
    else:
        gap = seconds_until_close / float(billed_left + 1)
    gap = max(MIN_ATTEMPT_SPACING_S, gap)
    if gap >= seconds_until_close:
        # Waiting that long would close the window. Better to try immediately at the floor than to
        # wake up after the deadline holding an unspent budget.
        return MIN_ATTEMPT_SPACING_S if MIN_ATTEMPT_SPACING_S < seconds_until_close else None
    return gap


def projected_lead_spread(manifest, new_lead_h):
    """What banking a pair at `new_lead_h` would do to the series' lead spread.

    The comparability guard is a WARNING, not a gate: 6.0-11.5 h is the gate, and this is the cost
    of using the low end of it. Printed rather than enforced, because a pair at 6.5 h is worth
    having and the honest thing is to show what it does to the series.
    """
    leads = [d.get("forecast_lead_h") for d in (manifest.get("days") or {}).values()
             if d.get("forecast_done") and d.get("forecast_lead_h") is not None]
    if not leads:
        return None
    now_spread = max(leads) - min(leads)
    with_new = leads + [new_lead_h]
    return {"days": len(leads), "spread_now_h": round(now_spread, 2),
            "spread_after_h": round(max(with_new) - min(with_new), 2),
            "warn_at_h": N26.LEAD_SPREAD_WARN_H,
            "would_warn": (max(with_new) - min(with_new)) > N26.LEAD_SPREAD_WARN_H}


# ---------------------------------------------------------------- reporting
def print_state(st, day, bud, manifest):
    print("   site local (%s) : %s" % (SITE_TZ_NAME, site_now().strftime("%Y-%m-%d %H:%M:%S")))
    print("   target window        : %s %s-%s site-local"
          % (st["window"]["start_date"], st["window"]["start_time"], st["window"]["end_time"]))
    print("   lead right now       : %.2f h        band %.1f-%.1f h"
          % (st["lead_h"], N26.MIN_LEAD_H, N26.MAX_LEAD_H))
    print("   in-band window       : %s to %s UTC   %s"
          % (st["opens"].strftime("%H:%M"), st["closes"].strftime("%H:%M"),
             "OPEN, %.1f h left" % (st["seconds_until_close"] / 3600.0) if st["in_band"]
             else ("opens in %.1f h" % (st["seconds_until_open"] / 3600.0)
                   if st["seconds_until_open"] > 0 else "CLOSED")))
    print("   forecast leg today   : %s"
          % ("BANKED (%s)" % day.get("forecast_tag") if day.get("forecast_done")
             else "not yet"))
    print("   credit budget        : %d of %d billed attempts used, %s credits committed"
          % (bud["billed_used"], N26.MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY,
             format(bud["credits_committed"], ",")))
    print("   runaway ceiling      : %d of %d attempts used"
          % (bud["total_used"], N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY))
    print("   %s" % N26.attempt_summary(day))

    spread = projected_lead_spread(manifest, st["lead_h"])
    if spread:
        print("   lead spread          : %.2f h across %d banked day(s); banking at this lead "
              "would make it %.2f h%s"
              % (spread["spread_now_h"], spread["days"], spread["spread_after_h"],
                 "  <-- past the %.1f h comparability warning" % spread["warn_at_h"]
                 if spread["would_warn"] else ""))

    rec = recent_vendor_record(6.0)
    if rec:
        print("   VENDOR, LAST 6 h     : %d of %d windows returned a field (%.0f %%), %s credits "
              "billed for nothing"
              % (rec["returned_a_field"], rec["windows_seen"], 100 * rec["success_rate"],
                 format(rec["credits_spent_for_nothing"], ",")))
        print("                          sources: %s" % ", ".join(rec["sources"]))
    else:
        print("   VENDOR, LAST 6 h     : no measurement in the last 6 h from either the live agent "
              "or the collector")


# ---------------------------------------------------------------- plan (free)
def plan(max_wall_h=6.0):
    banner("N-26 recovery watch -- PLAN. Zero API calls, no key read, nothing spent.")
    st = window_state()
    manifest = N26.load_manifest()
    day = day_record(manifest, st["date"])
    bud = budgets(day)
    print_state(st, day, bud, manifest)

    print("\n   WHAT `watch --allow-paid` WOULD DO FROM HERE")
    if day.get("forecast_done"):
        print("      NOTHING. Today's forecast leg is already banked; the watcher exits 0 at once.")
        return 0
    if bud["billed_left"] <= 0:
        print("      NOTHING. The credit budget is spent (%d of %d billed). Raise it deliberately "
              "with" % (bud["billed_used"], N26.MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY))
        print("      N26_MAX_ATTEMPTS if today's pair is still recoverable and you want to pay for "
              "it.")
        return 3
    if bud["total_left"] <= 0:
        print("      NOTHING. The runaway ceiling is reached (%d of %d attempts)."
              % (bud["total_used"], N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY))
        return 3
    if st["seconds_until_close"] <= 0:
        print("      NOTHING. The in-band window closed %.1f h ago. Today's pair cannot be "
              "recovered -- run before %s UTC tomorrow."
              % (-st["seconds_until_close"] / 3600.0, st["closes"].strftime("%H:%M")))
        return 2

    # The schedule it would follow, assuming the worst case: every attempt billed and empty.
    print("      Worst case -- every attempt BILLED and empty, which is the 2026-08-21 shape:")
    t, left, when = st["seconds_until_close"], bud["billed_left"], 0.0
    if not st["in_band"]:
        print("         +%5.0f min  wait for the window to open" % (st["seconds_until_open"] / 60))
        when = st["seconds_until_open"]
    n = 0
    while left > 0 and t > 0 and n < bud["total_left"]:
        n += 1
        lead_then = st["lead_h"] - (when / 3600.0)
        print("         +%5.0f min  attempt %d   lead would be %.2f h   %s credits"
              % (when / 60, n, lead_then, format(HEATMAP_CREDITS, ",")))
        gap = next_gap_s(True, left - 1, t)
        left -= 1
        if gap is None or left <= 0:
            break
        when += gap
        t -= gap
    print("      Total worst-case cost today: %s credits for %d attempt(s)."
          % (format(n * HEATMAP_CREDITS, ","), n))
    print("      Free failures do NOT consume that budget, so a stalling vendor would be probed")
    print("      every %d min up to the %d-attempt ceiling at ZERO credits."
          % (MIN_ATTEMPT_SPACING_S / 60, N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY))
    print("\n      Nothing above has been spent. Run `watch --allow-paid` to act on it.")
    return 0


# ---------------------------------------------------------------- watch (paid)
def watch(allow_paid, max_wall_h=6.0):
    banner("N-26 recovery watch -- WATCH.  THIS SPENDS CREDITS through the collector.")
    if not allow_paid:
        print("   REFUSED: `watch` needs --allow-paid. Every attempt costs up to %s credits when"
              % format(HEATMAP_CREDITS, ","))
        print("   the vendor answers `completed` with no data, and this loop makes several.")
        print("   `plan` shows exactly what it would do and spends nothing.")
        return 5

    deadline = time.time() + max_wall_h * 3600
    attempts_here = 0
    while True:
        st = window_state()
        manifest = N26.load_manifest()
        day = day_record(manifest, st["date"])
        bud = budgets(day)

        print()
        print("-- %s UTC" % st["now"].strftime("%H:%M:%S"))
        print_state(st, day, bud, manifest)

        # ---- the four reasons to stop, each with its own exit code -------------------
        if day.get("forecast_done"):
            print("\n   BANKED. Today's forecast leg is recorded (%s) at a %.2f h lead."
                  % (day.get("forecast_tag"), day.get("forecast_lead_h") or float("nan")))
            spread = projected_lead_spread(manifest, day.get("forecast_lead_h") or 0.0)
            if spread and spread["would_warn"]:
                print("   NOTE: the series' lead spread is now %.2f h, past the %.1f h "
                      "comparability warning. The report will say so."
                      % (spread["spread_after_h"], spread["warn_at_h"]))
            print("   %d attempt(s) made by this watcher." % attempts_here)
            return 0
        if st["seconds_until_close"] <= 0:
            print("\n   STOP: the in-band window has closed. Today's pair is lost; a call now "
                  "would be below the %.1f h comparability floor and would flatter coverage."
                  % N26.MIN_LEAD_H)
            return 2
        if bud["billed_left"] <= 0:
            print("\n   STOP: the credit budget is spent -- %d billed attempt(s), %s credits."
                  % (bud["billed_used"], format(bud["credits_committed"], ",")))
            return 3
        if bud["total_left"] <= 0:
            print("\n   STOP: the runaway ceiling is reached -- %d attempt(s), %s credits."
                  % (bud["total_used"], format(bud["credits_committed"], ",")))
            return 3
        if not st["in_band"]:
            wait = min(st["seconds_until_open"], max(0.0, deadline - time.time()))
            if time.time() + st["seconds_until_open"] > deadline:
                print("\n   STOP: the window opens in %.1f h, beyond the %.1f h wall clock given."
                      % (st["seconds_until_open"] / 3600.0, max_wall_h))
                return 4
            print("\n   waiting %.0f min for the window to open" % (wait / 60))
            _sleep(wait)
            continue

        # ---- one attempt, through the collector ------------------------------------
        print("\n   ATTEMPT %d -- running the collector. Up to %s credits if the vendor bills it."
              % (attempts_here + 1, format(HEATMAP_CREDITS, ",")))
        attempts_here += 1
        try:
            N26.collect()
        except Exception as e:                                  # noqa: BLE001
            # A crash here must not look like a clean "no pair today". The collector writes the
            # manifest before its call, so the attempt is already recorded either way.
            print("   the collector RAISED: %s: %s" % (type(e).__name__, str(e)[:200]))

        # DO NOT TRUST THE RETURN VALUE. `collect()` returns 0 whether or not it got data -- that
        # is gotcha #96 (a green task means python exited) and it is why this re-reads the record.
        manifest = N26.load_manifest()
        day = day_record(manifest, st["date"])
        log = [r for r in (day.get("forecast_attempt_log") or []) if r.get("leg") == "forecast"]
        last = log[-1] if log else None
        if day.get("forecast_done"):
            continue                       # the top of the loop reports and exits 0
        if last:
            print("   -> %s" % last.get("sentence", last.get("class")))
            billed = bool(last.get("billed"))
        else:
            # No record written: the collector skipped for a reason of its own (lead band, budget)
            # and printed why. Treat it as free -- nothing was charged -- and let the loop's own
            # stop conditions handle it on the next pass.
            print("   -> the collector made no attempt; its own reason is printed above")
            billed = False

        bud = budgets(day)
        gap = next_gap_s(billed, bud["billed_left"], window_state()["seconds_until_close"])
        if gap is None:
            print("   nothing left to wait for -- looping to report and exit")
            continue
        if time.time() + gap > deadline:
            print("\n   STOP: the next attempt would fall %.0f min past the %.1f h wall clock."
                  % ((time.time() + gap - deadline) / 60, max_wall_h))
            return 4
        print("   next attempt in %.0f min  (%s failure, %d billed attempt(s) left)"
              % (gap / 60, "BILLED" if billed else "free", bud["billed_left"]))
        _sleep(gap)


def _sleep(seconds):
    """Sleep, saying so periodically.

    A silent process is indistinguishable from a hung one -- gotcha #115, where a 300 s wait with
    no heartbeat read as a frozen page. This one can wait an hour.
    """
    end = time.time() + seconds
    while True:
        left = end - time.time()
        if left <= 0:
            return
        time.sleep(min(HEARTBEAT_S, left))
        left = end - time.time()
        if left > 0:
            print("      ... waiting, %.0f min to go" % (left / 60))


# ---------------------------------------------------------------- selftest
def selftest():
    """The pacing arithmetic and the stop conditions. ZERO network, no key, no manifest writes."""
    banner("N-26 recovery watch selftest.  ZERO API CALLS.")
    fails = []

    def ck(name, ok, detail=""):
        (fails.append(name) if not ok else None)
        print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))

    HOUR = 3600.0

    # ---- 1. THE CORE OF IT: a free failure is retried at once, a billed one is spaced ------
    free = next_gap_s(False, 3, 5.5 * HOUR)
    ck("a FREE failure retries at the floor", free == MIN_ATTEMPT_SPACING_S,
       "%.0f min" % (free / 60))
    billed = next_gap_s(True, 2, 5.5 * HOUR)
    ck("a BILLED failure spaces the rest across the window", billed > free,
       "%.0f min, dividing 5.5 h by the 2 attempts left plus one" % (billed / 60))
    ck("...and that spacing is exactly window/(left+1)",
       abs(billed - (5.5 * HOUR / 3.0)) < 1e-6, "%.1f min == 5.5 h / 3" % (billed / 60))

    # THE WHOLE POINT, AS ONE ASSERTION. Three free failures must leave the loop able to continue;
    # three billed ones must stop it. Same three failures, opposite consequence, because one set
    # cost 12,660 credits and the other cost nothing.
    ck("three FREE failures still permit another attempt",
       next_gap_s(False, 3, 4 * HOUR) is not None
       and N26.billed_attempts({"forecast_attempt_log": [
           {"leg": "forecast", "class": "stalled_in_processing", "billed": False}] * 3}) == 0,
       "0 of %d billed" % N26.MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY)
    ck("a billed failure with nothing left to spend returns no gap",
       next_gap_s(True, 0, 4 * HOUR) is None, "None -- the loop stops rather than sleeping")

    # ---- 2. the window edges ---------------------------------------------------------
    ck("a closed window returns no gap", next_gap_s(True, 3, -60) is None, "None")
    ck("a gap that would outlast the window falls back to the floor, not past it",
       next_gap_s(True, 1, MIN_ATTEMPT_SPACING_S * 1.5) == MIN_ATTEMPT_SPACING_S,
       "%.0f min inside a %.0f min remainder"
       % (MIN_ATTEMPT_SPACING_S / 60, MIN_ATTEMPT_SPACING_S * 1.5 / 60))
    ck("a window shorter than the floor returns no gap",
       next_gap_s(True, 1, MIN_ATTEMPT_SPACING_S * 0.5) is None,
       "None -- waiting would close the window")
    ck("the floor cannot bind before the runaway ceiling does",
       MIN_ATTEMPT_SPACING_S * N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY
       < (N26.MAX_LEAD_H - N26.MIN_LEAD_H) * HOUR,
       "%.0f min of pacing inside a %.1f h window"
       % (MIN_ATTEMPT_SPACING_S * N26.MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY / 60,
          N26.MAX_LEAD_H - N26.MIN_LEAD_H))

    # ---- 3. the window state is READ from the collector, not recomputed ---------------
    st = window_state()
    band_h = (st["closes"] - st["opens"]).total_seconds() / 3600.0
    ck("the in-band window is exactly the comparability band wide",
       abs(band_h - (N26.MAX_LEAD_H - N26.MIN_LEAD_H)) < 1e-9,
       "%.2f h == %.1f - %.1f" % (band_h, N26.MAX_LEAD_H, N26.MIN_LEAD_H))
    ck("the lead at the window's opening edge is the band ceiling",
       abs(lead_hours(st["window"]["_start_utc"], st["opens"]) - N26.MAX_LEAD_H) < 1e-9,
       "%.2f h" % lead_hours(st["window"]["_start_utc"], st["opens"]))
    ck("the lead at the closing edge is the band floor",
       abs(lead_hours(st["window"]["_start_utc"], st["closes"]) - N26.MIN_LEAD_H) < 1e-9,
       "%.2f h" % lead_hours(st["window"]["_start_utc"], st["closes"]))
    ck("in_band agrees with the lead it was derived from",
       st["in_band"] == (N26.MIN_LEAD_H <= st["lead_h"] <= N26.MAX_LEAD_H),
       "lead %.2f h, in_band=%s" % (st["lead_h"], st["in_band"]))

    # ---- 4. the lead-spread projection is honest about the cost of a late pair --------
    fake = {"days": {"a": {"forecast_done": True, "forecast_lead_h": 9.41},
                     "b": {"forecast_done": True, "forecast_lead_h": 9.50}}}
    early = projected_lead_spread(fake, 9.45)
    late = projected_lead_spread(fake, 6.10)
    ck("banking near the reference lead does not trip the warning",
       early is not None and not early["would_warn"],
       "spread %.2f h" % early["spread_after_h"])
    ck("banking at the bottom of the band DOES trip it, and says so",
       late is not None and late["would_warn"],
       "spread %.2f h > %.1f h" % (late["spread_after_h"], late["warn_at_h"]))

    # ---- 5. the vendor record now reads BOTH spenders (the 2026-08-21 blind spot) -----
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        stamp = utc_now().isoformat()
        json.dump({"days": {"2026-08-21": {"forecast_attempt_log": [
            {"leg": "forecast", "class": "completed_but_empty", "billed": True, "at_utc": stamp},
            {"leg": "forecast", "class": "stalled_in_processing", "billed": False,
             "at_utc": stamp}]}}}, open(os.path.join(td, "n26_manifest.json"), "w"))
        rec = recent_vendor_record(6.0, results_dir=td)
        ck("the vendor record sees COLLECTOR attempts with no live run at all",
           rec is not None and rec["windows_seen"] == 2 and rec["returned_a_field"] == 0,
           "2 windows, 0 answered, sources: %s" % ", ".join(rec["sources"]) if rec else "None")
        ck("...and prices only the BILLED one as credits spent for nothing",
           rec is not None and rec["credits_spent_for_nothing"] == HEATMAP_CREDITS,
           "%s credits, not %s -- the stall was free"
           % (format(rec["credits_spent_for_nothing"], ","),
              format(2 * HEATMAP_CREDITS, ",")) if rec else "None")
        ck("an empty results directory yields no record rather than a fake zero",
           recent_vendor_record(6.0, results_dir=os.path.join(td, "nope")) is None, "None")

    print()
    N26.verdict(not fails,
                "PASS - the watcher paces on the BILLING of the last failure, reads its window and "
                "its budgets from the collector rather than recomputing them, and reports what a "
                "late pair would do to the series' lead spread.",
                "FAIL - %s" % ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:]]
    mode = (argv[0].lower() if argv and not argv[0].startswith("-") else "plan")
    allow = "--allow-paid" in argv
    hours = 6.0
    for i, a in enumerate(argv):
        if a == "--hours" and i + 1 < len(argv):
            hours = float(argv[i + 1])
    if mode == "watch":
        sys.exit(watch(allow, hours))
    if mode == "selftest":
        sys.exit(selftest())
    sys.exit(plan(hours))
