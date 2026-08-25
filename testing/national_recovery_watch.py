# -*- coding: utf-8 -*-
"""NATIONAL RECOVERY WATCHER  ---  probe for the heatmap path coming back, then fire the full buy.

WHY THIS EXISTS
    2026-08-23: the national FortyGuard field purchase's first live chunk went 20-for-20
    `completed_but_empty`. DIAG-66 then proved even Ashburn's own long-proven, repeatedly-successful
    geometry ALSO failed on a fresh past window -- a GENERAL outage, not an AOI-specific gap, the
    same day the forecast path had recovered (HANDOFF section 4.0-RECOVERY). The national batch was
    stopped with ~360 of 399 real purchases still unbought.

WHAT IT DOES, AND THE ONE THING IT CANNOT DO
    There is NO free probe for "does the heatmap path work right now" -- `n26_recovery_watch.py`'s
    own docstring already says this about the forecast path, and DIAG-66 measured the same thing
    true of past/observed windows: the request IS the test, and it costs 4,220 when it comes back
    `completed_but_empty`. So this watcher does not detect recovery for free -- it spends, at a
    capped rate, in order to detect. Mirrors `n26_recovery_watch.py`'s architecture exactly (this
    project's own rule 12: never let two code paths compute one judgement two ways) --
    day-keyed billed-probe budget, a heartbeat during sleep, `plan` free / `watch --allow-paid` real.

    ATTENDED ONLY, per the user's explicit choice 2026-08-23: this is NOT registered as a scheduled
    task. It runs only for as long as someone has started `watch --allow-paid` and left it running.
    A process that can spend ~1.4M credits unattended is exactly the risk this project has already
    scarred itself on once this session (the stray `serve_live.py --allow-paid`, three days
    unattended). Registering this as a scheduled task is a separate, explicit decision -- not this
    script's default, and not made here.

EACH PROBE
    One fresh, never-before-requested past window at ASHBURN'S OWN committed geometry (the same
    control DIAG-66 used) -- `now - PROBE_LOOKBACK_H` rounded to an even 2 h boundary, which shifts
    by exactly one probe interval between consecutive probes, so consecutive probes are
    automatically different windows without needing a separate "already tried" ledger.

ON SUCCESS
    Calls `buy_national_fields.main()` directly (imported, not subprocessed -- the same pattern
    `n26_recovery_watch.py` uses for `test_n26_coverage.collect()`), sized to whatever the live
    credit balance affords at that moment, impact-ranked, per the user's standing allocation
    instruction ("start with real tagged data centres... then highest impact... till all are
    covered").

USAGE
    python national_recovery_watch.py plan                  # zero paid calls. what it would do.
    python national_recovery_watch.py watch --allow-paid    # the real thing. attended, deliberate.
    python national_recovery_watch.py selftest              # the pacing/budget arithmetic, offline

EXIT CODES
    0  recovery detected and the national buy was launched (or already complete)
    3  the daily billed-probe budget is spent
    4  nothing to do inside the wall-clock limit given
    5  refused: `watch` without --allow-paid
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (banner, box_aoi, classify_vendor, credits_remaining, HEATMAP_CREDITS,
                    is_billed, load_key, RESULTS, submit_poll, utc_now, vendor_rec, verdict)
import buy_national_fields as BNF

STATE_FILE = os.path.join(RESULTS, "national_recovery_state.json")
IA_GEOM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "INTAKE-ARBITER", "data", "geometry", "selected_site.json")
TZ_NAME = "America/New_York"          # Ashburn's real zone -- the same control DIAG-66 used

MAX_BILLED_PROBES_PER_DAY = 3         # matches N26's own convention -- a hand-chosen ceiling,
                                      # labelled as one, deliberately identical to the collector's
                                      # so probing this outage does not out-spend probing the other
PROBE_INTERVAL_S = 2 * 3600           # the answered question: every 2 hours
PROBE_LOOKBACK_H = 25                 # always comfortably >24 h elapsed, so a probe is NEVER
                                      # accidentally a future/near window regardless of DST or when
                                      # inside its 2 h interval the watcher happens to wake
HEARTBEAT_S = 60


def _load_state():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        return {"days": {}}


def _save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(st, open(STATE_FILE, "w", encoding="utf-8"), indent=1, allow_nan=False)


def _today_key(now=None):
    return (now or utc_now()).date().isoformat()


def billed_probes_today(state, now=None):
    day = (state.get("days") or {}).get(_today_key(now), {})
    return len(day.get("probes") or [])


def record_probe(state, cls, billed, n_tiles, now=None):
    key = _today_key(now)
    state.setdefault("days", {}).setdefault(key, {"probes": []})
    state["days"][key]["probes"].append({
        "at_utc": (now or utc_now()).isoformat(), "class": cls, "billed": billed,
        "n_tiles": n_tiles})
    _save_state(state)


def probe_window(now=None):
    """A fresh, never-repeated past window: now - PROBE_LOOKBACK_H, floored to an even 2 h mark."""
    now = now or utc_now()
    base = now - timedelta(hours=PROBE_LOOKBACK_H)
    floored_hour = (base.hour // 2) * 2
    start_utc = base.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
    return start_utc, start_utc + timedelta(hours=2)


def do_one_probe(key):
    """ONE call, identical shape to DIAG-66. Returns (ok, cls, billed, n_tiles, credits_spent)."""
    sel = json.load(open(IA_GEOM, encoding="utf-8"))
    a, b = sel["source_building"]["centre_latlon"], sel["receptor_building"]["centre_latlon"]
    clat, clon = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    start_utc, end_utc = probe_window()
    # Rendered in the AOI's own zone for the payload -- America/New_York, not UTC.
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(TZ_NAME)
    start_local, end_local = start_utc.astimezone(tz), end_utc.astimezone(tz)
    dt = {"start_date": start_local.strftime("%Y-%m-%d"), "start_time": start_local.strftime("%H:00"),
          "end_time": end_local.strftime("%H:00"), "filter_type": 2}
    payload = {"polygon_aoi": box_aoi(clat, clon, 8.0), "granularity": 60, "analytic_type": "tcm",
              "date_time": dt}
    before = credits_remaining(key)
    r = submit_poll(key, "heatmap", payload,
                    "national_recovery_probe_%s" % start_utc.strftime("%Y%m%d_%H%M"),
                    max_s=480, require_data=True)
    after = credits_remaining(key)
    feats = (((r.get("result") or {}).get("map_data") or {}).get("features") or [])
    # 🔴 `classify_vendor(r)` ON THE RAW RETURN MEANT THIS WATCHER COULD NEVER SEE RECOVERY.
    # The classifier reads `rec["tiles"]`; a common.submit_poll return has no such key and carries
    # the payload at `result.map_data.features`. So `cls` was permanently "completed_but_empty",
    # `ok = cls == "ok" and ...` was permanently False, and the watcher would have reported the
    # vendor down while holding real tiles in `feats` on the very same line. `vendor_rec()` is the
    # converter that exists for exactly this, and it reads submit_poll's own key names.
    cls = classify_vendor(vendor_rec(r))
    billed = is_billed(cls)
    ok = cls == "ok" and len(feats) > 0
    print("   probe window %s %s-%s %s  ->  class=%s  tiles=%d  credits %s -> %s"
          % (dt["start_date"], dt["start_time"], dt["end_time"], TZ_NAME, cls, len(feats),
             format(before, ","), format(after, ",")))
    return ok, cls, billed, len(feats)


def plan():
    banner("NATIONAL RECOVERY WATCH -- PLAN. Zero API calls, no key read, nothing spent.")
    state = _load_state()
    used = billed_probes_today(state)
    print("   billed probes used today : %d of %d" % (used, MAX_BILLED_PROBES_PER_DAY))
    print("   probe interval            : every %.0f h" % (PROBE_INTERVAL_S / 3600.0))
    print("   worst case today          : %d more billed probes = %s credits, if every one is"
          " empty" % (MAX_BILLED_PROBES_PER_DAY - used,
                      format((MAX_BILLED_PROBES_PER_DAY - used) * HEATMAP_CREDITS, ",")))
    print("\n   ON THE FIRST PROBE THAT RETURNS REAL TILES:")
    print("      buy_national_fields.main(['run', '--allow-paid']) fires immediately, sized to")
    print("      whatever the live credit balance affords -- impact-ranked, exactly the batch that")
    print("      was interrupted by the 2026-08-23 outage.")
    print("\n   ATTENDED ONLY. Not a scheduled task. Runs only while `watch --allow-paid` is")
    print("   actually running in a session someone started.")
    print("\n   Nothing above has been spent. Run `watch --allow-paid` to act on it.")
    return 0


def watch(allow_paid, max_wall_h=24.0):
    banner("NATIONAL RECOVERY WATCH -- WATCH.  THIS SPENDS CREDITS: up to %d probes/day."
          % MAX_BILLED_PROBES_PER_DAY)
    if not allow_paid:
        print("   REFUSED: `watch` needs --allow-paid. Each probe costs up to %s credits when the"
              % format(HEATMAP_CREDITS, ","))
        print("   vendor answers `completed` with no data. `plan` shows the worst case for free.")
        return 5

    key = load_key()
    deadline = time.time() + max_wall_h * 3600
    probes_here = 0
    while True:
        state = _load_state()
        used = billed_probes_today(state)
        print("\n-- %s UTC   (billed probes today: %d/%d, this session: %d)"
              % (utc_now().strftime("%H:%M:%S"), used, MAX_BILLED_PROBES_PER_DAY, probes_here))
        if used >= MAX_BILLED_PROBES_PER_DAY:
            print("   STOP: today's billed-probe budget is spent (%d of %d)."
                  % (used, MAX_BILLED_PROBES_PER_DAY))
            return 3
        if time.time() >= deadline:
            print("   STOP: the %.1f h wall clock given to this run has elapsed." % max_wall_h)
            return 4

        ok, cls, billed, n_tiles = do_one_probe(key)
        state = _load_state()
        record_probe(state, cls, billed, n_tiles)
        probes_here += 1

        if ok:
            print("\n   *** RECOVERY DETECTED: %d real tiles. Firing the national buy now. ***"
                  % n_tiles)
            rem = credits_remaining(key)
            print("   live credits remaining: %s (%d calls affordable)"
                  % (format(rem, ","), rem // HEATMAP_CREDITS))
            rc = BNF.main(["run", "--allow-paid"])
            print("\n   buy_national_fields exited %d." % rc)
            return 0

        print("   still down (%s). %d/%d billed probes used today."
              % (cls, billed_probes_today(_load_state()), MAX_BILLED_PROBES_PER_DAY))
        if billed_probes_today(_load_state()) >= MAX_BILLED_PROBES_PER_DAY:
            print("   STOP: that probe used the last billed slot for today.")
            return 3
        gap = PROBE_INTERVAL_S
        if time.time() + gap > deadline:
            print("   STOP: the next probe would fall past the %.1f h wall clock." % max_wall_h)
            return 4
        print("   next probe in %.0f min" % (gap / 60))
        _sleep(gap, deadline)


def _sleep(seconds, deadline):
    end = min(time.time() + seconds, deadline)
    while True:
        left = end - time.time()
        if left <= 0:
            return
        time.sleep(min(HEARTBEAT_S, left))
        left = end - time.time()
        if left > 0:
            print("      ... waiting, %.0f min to go" % (left / 60))


def selftest():
    """The probe-window arithmetic and the daily budget. ZERO network, no key read."""
    banner("National recovery watch selftest. ZERO API CALLS.")
    fails = []

    def ck(name, ok, detail=""):
        (fails.append(name) if not ok else None)
        print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))

    now = datetime(2026, 8, 24, 15, 37, tzinfo=timezone.utc)
    s1, e1 = probe_window(now)
    elapsed_h = (now - e1).total_seconds() / 3600.0
    ck("a probe window's END is comfortably >= 23 h in the past (flooring can only move it "
       "earlier than PROBE_LOOKBACK_H, never later)",
       elapsed_h >= PROBE_LOOKBACK_H - 2, "now - end = %.1f h" % elapsed_h)
    ck("a probe window is exactly 2 h wide", (e1 - s1).total_seconds() == 7200,
       "%.0f s" % (e1 - s1).total_seconds())
    ck("the window start is on an even 2 h boundary", s1.hour % 2 == 0, "hour=%d" % s1.hour)

    later = now + timedelta(hours=PROBE_INTERVAL_S / 3600.0)
    s2, _ = probe_window(later)
    ck("consecutive probe intervals land on DIFFERENT windows", s2 != s1,
       "%s vs %s" % (s1, s2))

    import tempfile
    global STATE_FILE
    orig = STATE_FILE
    with tempfile.TemporaryDirectory() as td:
        STATE_FILE = os.path.join(td, "state.json")
        st = _load_state()
        ck("a fresh state starts at zero probes today", billed_probes_today(st, now) == 0, "0")
        for i in range(MAX_BILLED_PROBES_PER_DAY):
            record_probe(st, "completed_but_empty", True, 0, now)
            st = _load_state()
        ck("the daily cap is reached after exactly %d billed probes" % MAX_BILLED_PROBES_PER_DAY,
           billed_probes_today(st, now) == MAX_BILLED_PROBES_PER_DAY,
           "%d recorded" % billed_probes_today(st, now))
        tomorrow = now + timedelta(days=1)
        ck("the budget resets on a new UTC day", billed_probes_today(st, tomorrow) == 0,
           "0 on %s" % _today_key(tomorrow))
        record_probe(st, "submit_rejected", False, 0, now)
        st = _load_state()
        ck("a FREE probe result is still recorded (for the log) even though it is not billed",
           len((st["days"][_today_key(now)]["probes"])) == MAX_BILLED_PROBES_PER_DAY + 1,
           "%d probes logged" % len(st["days"][_today_key(now)]["probes"]))
    STATE_FILE = orig

    print()
    verdict(not fails,
           "PASS - probe windows are always safely elapsed and change every interval without a "
           "separate 'already tried' ledger, and the daily billed-probe budget resets on a new day.",
           "FAIL - %s" % ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    mode = (argv[0].lower() if argv and not argv[0].startswith("-") else "plan")
    allow = "--allow-paid" in argv
    hours = 24.0
    for i, a in enumerate(argv):
        if a == "--hours" and i + 1 < len(argv):
            hours = float(argv[i + 1])
    if mode == "watch":
        sys.exit(watch(allow, hours))
    if mode == "selftest":
        sys.exit(selftest())
    sys.exit(plan())
