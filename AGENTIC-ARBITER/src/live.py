# -*- coding: utf-8 -*-
"""LIVE -- the agent perceives NOW and decides the next 12 hours, for the selected site.

    python live.py dryrun               # ZERO API calls: exactly what it would fetch, and the cost
    python live.py run --paid           # the real thing. Spends credits. Requires the flag.
    METRO=chicago python live.py run --paid --hours 6

WHY THIS EXISTS
---------------
Everything else in this project decides over a RECORDED past: `agent.py` over four saved FortyGuard
day-pairs, `backtest.py` over 43,763 archived hours, `rolling.py` over held-out days. That is what
makes those numbers auditable, and it is also a fair criticism of the demo -- the user put it
plainly: *"how is it an agent if it doesnt make any live API calls?"* A control loop that can only
run against a fixture is a simulation of an agent.

This module closes that gap. It asks FortyGuard what the next twelve hours look like AT THIS SITE,
right now, bounds that forecast with the margin measured from FortyGuard's OWN past errors, and
emits a switching schedule for hours that have not happened yet.

WHAT IT REUSES, AND WHY THAT IS THE WHOLE DESIGN
------------------------------------------------
It writes **no new decision logic**. The rise table, the nearest-tile lookup, the conformal
quantile, the dynamic-programming scheduler and the BMS command shape are imported from
`agent.py` unchanged:

    A.rise_table()     the 576 solves on THIS site's real geometry
    A.lookup_rise()    rise for a (bearing, speed) pair
    A.plan()           the schedule, under a switch budget and a dwell limit, by DP
    A.bms_commands()   the ACT stage's command rows

A parallel "live-only" decision core would drift from the verified one within a day, and then two
numbers on one page would disagree with no way to tell which was right. **The live path is the same
agent on different input.** That is also why `verify_live_offline()` can prove the whole chain
against saved fixtures with zero API calls -- the arithmetic is not live-specific.

THE THREE SOURCES, AND WHICH ONE IS FORTYGUARD'S
------------------------------------------------
| Quantity | Source | Why not FortyGuard |
|---|---|---|
| Dry-bulb ambient, per hour, at this site's own tile | **FortyGuard `/v1/heatmap`** | this IS the product, and the reason the project exists |
| Wind bearing and speed, per hour | **NWS `api.weather.gov`**, free, keyless | FortyGuard's API carries no wind field -- confirmed from their OpenAPI spec |
| Dew point, per hour | **NWS**, same call | `env_params` returns humidity and wet-bulb but **no dry-bulb**, and `heatmap` returns temperature but no environmentals, so one place and time already needs two endpoints (findings section 9.4). NWS gives dew point in the same free response as wind |

Using free public data for wind is not a shortcut taken here for convenience: the five-year record
does the same thing, and `PLAN.md` section 9 has said so since the beginning.

🔴 THE BOUND IS THE HONEST PART, AND IT IS WEAK
----------------------------------------------
A live FortyGuard forecast must be bounded by the margin measured on **FortyGuard's own**
forecast-versus-outcome residuals. It must NOT use the per-lead margins in `rolling.py`, which are
calibrated on de-biased *persistence* errors: those describe a different forecaster, and borrowing
them would be exactly the category error section 8e of `PLAN.md` exists to prevent.

So the live margin comes from `trace.json`'s `cycle.bound_day_level`, and everything known against
it travels with it in `margin_provenance`:

  * **n = 4 measured day-pairs.** A 90 % one-sided bound needs 9 calibration days; at n = 4 the
    attainable coverage CEILING is n/(n+1) = 80 %, so 90 % is arithmetically unreachable and the
    quantile is reported as clamped.
  * **Measured coverage 65.6 % on 3 test days, worst day 0.0 %. It FAILED its pre-registration.**
  * **Every pair was measured at a ~9.4 h lead against a 14:00 site-local window.** A live run
    bounds leads of 1..12 h at whatever hour it happens to be. **Applying a margin measured at one
    lead and one hour-of-day to all leads and all hours is an EXTRAPOLATION**, and the emitted JSON
    says so rather than leaving a reader to assume otherwise.
  * A site with no FortyGuard pairs of its own (Chicago, Dulles) borrows Ashburn's margin, flagged.

None of that is hidden behind a green tick. A bound whose limitations are published is worth more
than one whose are not.

🔴 IT NEVER INVENTS A FORECAST
------------------------------
FortyGuard was accepting heatmap jobs and never completing them on the day this was written
(DIAG-63: a forecast leg AND a past-window control both sat at `status: Processing` for 425 s).
`classify_vendor()` distinguishes four outcomes -- `ok`, `completed_but_empty`, `terminal_<status>`,
`stalled_in_processing` -- and when the vendor does not answer, this module returns
`status: "vendor_unavailable"` with the activity ids and elapsed times and **NO SCHEDULE AT ALL.**
There is no interpolation, no last-known-value substitution, and no silent fall back to a saved
field dressed as live. An agent that fabricates its perception is worse than one that stops.

COST, AND WHY IT IS SHAPED LIKE THIS
------------------------------------
A heatmap response carries `average/min/max_temperature` per tile **aggregated over the requested
window** -- not a time series. So an hourly trajectory costs one call per hour. Pricing is flat with
respect to hour count (findings section 5), so a 1 h window and a 6 h window cost the same 4,220:
the price is per CALL, and hourly resolution is therefore the expensive axis.

  * 12 h horizon = 12 calls = 50,640 credits.
  * The plan's binding limit is **30 heatmaps/day**, not credits (1,945,140 remain).
  * **Windows are cached** under `data/live_cache/<metro>/`. N-55 established that re-requesting an
    identical window returns 17,862 of 17,862 tiles byte-for-byte identical, max |delta| =
    0.00000000 C -- so a cache hit is the same data, not an approximation of it.
  * Because the horizon SLIDES, a re-run an hour later needs only the one new far-end window. A
    live agent polling hourly therefore costs ~1 call/hour after the first run, which fits inside
    the daily cap.
  * `dryrun` prints the windows, the cache hits and the exact cost, and **makes no calls** -- the
    same discipline as `test_n26_coverage.py dryrun`.
  * Spending requires `--paid` explicitly. Rule 8: ask before spending, every time.
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import agent as A                       # noqa: E402 -- the verified decision core, reused wholesale
import metros as M                      # noqa: E402

# Rule 8: the key is read ONLY through testing/common.py:load_key(). Nothing here reimplements it.
TESTING = os.path.join(os.path.dirname(M.ROOT), "testing")
sys.path.insert(0, TESTING)
from common import (load_key, credits_remaining, box_aoi, V1,          # noqa: E402
                    classify_vendor, vendor_sentence, VENDOR_HUMAN,     # noqa: E402
                    BILLED_CLASSES, is_billed, recent_vendor_record,    # noqa: E402
                    # `submit_poll` is used ONLY for env_params. The heatmap path deliberately keeps
                    # its own submit/poll, because it batches every window into one poll loop --
                    # that is what turned a 50-minute sequential run into 5 (gotcha #114). A single
                    # env_params call needs none of that machinery, and reusing the shared helper
                    # means it also gets the shared failure classification and fixture saving.
                    submit_poll, vendor_rec)                            # noqa: E402

HORIZON_H = 12
SIDE_KM = 8.0
GRAN = 60
ANALYTIC = "tcm"
HEATMAP_CREDITS = 4_220
# 🔴 RAISED 300 -> 600 s ON 2026-08-27, and the argument is about BILLING, not patience.
# ⚠ First, the arithmetic the UI was hiding: 300 s is FIVE minutes. The progress row prints
# "300 s budget", which reads as a small number and prompted "extend it to about 4 minutes" -- which
# would have SHORTENED it. It is now 600 s and the row says minutes as well as seconds.
# WHY LONGER IS STRICTLY BETTER HERE, rather than a trade:
#   * The vendor's own measured time-to-terminal-state is ~604-608 s (HANDOFF §4.0: "completed but
#     never populated after 59 polls over 604 s", and two more at 608 s). A 300 s budget therefore
#     abandoned jobs at HALF the time FortyGuard itself takes to finish with them.
#   * And abandoning does not save money. Gotcha #147: "billing happens server-side the instant
#     FortyGuard's own job completes, independent of whether the polling client is still alive."
#     So the credits are spent either way -- giving up early forfeits the DATA we already paid for
#     and buys nothing back. That is the whole case.
# WHAT IT DOES NOT FIX, stated so nobody expects it to: every window that has ever returned tiles
# did so on its FIRST status check (`polls: 1` on all 26 in live_spend.json), so a longer budget
# captures no success that a shorter one missed. What it captures is the STALL case -- a job still
# in `processing` at 300 s, which is unbilled today and may yet reach a terminal answer. A definite
# answer at 9 minutes is worth more than an abandoned one at 5.
# ⚠ COST IS WALL-CLOCK, and it is bounded: submits are batched and polled in ONE loop (#114), so
# this is 600 s for the whole horizon, not per hour.
POLL_MAX_S = 600
POLL_WAIT_S = 8
# Between submits in a batch, and before retrying one the vendor rejected.
SUBMIT_STAGGER_S = 0.4
SUBMIT_RETRY_WAIT_S = 3.0
DAILY_HEATMAP_CAP = 30
# A live AOI is built around the site's own centre, so its nearest tile is tens of metres away.
# Anything past this means the field belongs to a different place.
MAX_TILE_DIST_M = 2_000

# How far ahead `verify_live_offline` looks for an UNCACHED window to test the "never publish a
# schedule over an hour you did not perceive" guard against. It only has to exceed the number of
# windows a single live run can leave in the cache, which the daily cap bounds at 30.
SELFTEST_PROBE_H = 36

NWS_UA = {"User-Agent": "AGENTIC-ARBITER/1.0 (FortyGuard Hackathon 2026; free-cooling agent)",
          "Accept": "application/geo+json"}

CACHE = os.path.join(M.ROOT, "data", "live_cache")


def say(*a):
    print(*a, flush=True)


# ============================================================================
# 1. THE VENDOR, CLASSIFIED -- four outcomes, not "worked / didn't"
# ============================================================================
# MOVED TO testing/common.py 2026-08-21 (Session 4), NOT DELETED. The collector needs the same
# judgement about the same vendor, and a second copy of it is gotcha #12 -- the one that has bitten
# this project three times. The names are imported at the top of this file, so every call site
# below, `verify_live_offline()`'s five classifier assertions, and `serve_live.py` are unchanged;
# the classifier they exercise now also governs what the unattended collector does with its retry
# budget. `BILLED_CLASSES` / `is_billed()` came with it: the billing partition is a property of the
# vendor's behaviour, not of whichever of our programs happens to be asking.


# ============================================================================
# 2. FORTYGUARD, ONE HOUR AT A TIME, CACHED
# ============================================================================
def window_fields(start_local, hours=1):
    """The `date_time` block for a window starting at `start_local`, in the AOI's OWN local time.

    The endpoint reads `start_time` in the AOI's local zone -- gotcha #1 in the findings, and the
    cause of a 9-hour error early in this project. `start_local` must therefore already be a
    site-local datetime, and this function never converts.
    """
    end = start_local + timedelta(hours=hours)
    return {"start_date": start_local.date().isoformat(),
            "start_time": start_local.strftime("%H:00"),
            "end_time": end.strftime("%H:00"),
            "filter_type": 2}


def first_window_start(now_local):
    """The first hour of the horizon: the next whole hour boundary.

    🔴 THIS USED TO BE `(now + 1h)` FLOORED TO THE HOUR, WHICH IS NOT THE SAME THING and produced a
    misdescribed lead. At 09:55 it gave 10:00 -- a window starting in FIVE MINUTES while the record
    labelled it "lead +1 h". On a product whose entire thesis is *a thermometer cannot see three
    hours ahead*, mislabelling the lead by up to an hour is not a cosmetic slip: `lead_h` is what
    the margin's calibration domain is expressed in.

    Now it is simply the next whole hour, and the LEAD IS MEASURED rather than assumed -- see
    `lead_hours_for` below. A window can therefore be as little as a minute away, which is honest:
    that is genuinely how far ahead it is.
    """
    nxt = now_local.replace(minute=0, second=0, microsecond=0)
    return nxt + timedelta(hours=1) if nxt <= now_local else nxt


def lead_hours_for(now_local, window_start_local):
    """Real hours from the decision to the window's start. Never an index."""
    return (window_start_local - now_local).total_seconds() / 3600.0


def horizon_windows(metro, hours, now_local):
    """The windows this run needs, and which are ALREADY CACHED.

    Extracted so the caller can cost a run before committing to it. `serve_live.py` needs exactly
    this: its per-process call cap was checked against the HORIZON LENGTH, so a 12-hour request was
    counted as 12 calls even when 11 windows were already cached -- refusing runs that needed one
    call, and over-incrementing the counter when it did allow them.
    """
    start_local = first_window_start(now_local)
    out = []
    for i in range(hours):
        ws = start_local + timedelta(hours=i)
        w = window_fields(ws, 1)
        out.append({"window": w, "start_local": ws,
                    "lead_h": round(lead_hours_for(now_local, ws), 3),
                    "cached": os.path.exists(cache_path(metro, w))})
    return start_local, out


def cache_path(metro, dt_fields):
    d = os.path.join(CACHE, metro)
    os.makedirs(d, exist_ok=True)
    nm = "%s_%s-%s_g%d_%s.json" % (dt_fields["start_date"],
                                   dt_fields["start_time"].replace(":", ""),
                                   dt_fields["end_time"].replace(":", ""),
                                   GRAN, ANALYTIC)
    return os.path.join(d, nm)


def resolve_without_network(dt_fields, metro, want_latlon, replay, allow_paid):
    """Replay, cache, or refuse -- everything that needs no network.

    Returns `(value, rec)` when the window is settled here, or `(None, None)` meaning **the caller
    must submit it**. Split out of `fetch_window` so the batch path can settle every free window
    first and then submit only what is genuinely outstanding.
    """
    # ---- REPLAY: a saved REAL FortyGuard response, used to verify the decide path offline.
    # 🔴 THIS IS NOT A FALLBACK AND MUST NEVER BECOME ONE. It is reachable only when a caller
    # passes `replay=` explicitly, it never fires because a live call failed, and every output it
    # produces is stamped `mode: replay-verification` plus a `NOT_LIVE` banner. The difference
    # between a test harness and a lie is whether the artefact can be mistaken for the real thing.
    if replay:
        res = json.load(open(replay, encoding="utf-8"))
        res = res.get("result", res)
        tile, dist = A.nearest_tile(res, want_latlon[0], want_latlon[1])
        # 🔴 A FIXTURE FROM ANOTHER METRO IS NOT A VALID REPLAY, and `nearest_tile` will not tell
        # you: it returns the closest tile it HAS, so replaying Ashburn's field for Chicago picks an
        # Ashburn edge tile ~900 km from the plant. Dulles is the dangerous case at 4 km.
        if dist > MAX_TILE_DIST_M:
            return None, {"source": "replay-fixture", "class": "fixture_wrong_metro",
                          "fixture": os.path.basename(replay),
                          "tile_dist_m": round(dist, 1),
                          "error": "the nearest tile in %s is %.0f km from this site's centre, so "
                                   "this fixture is another metro's field. Refusing to report a "
                                   "temperature for it."
                                   % (os.path.basename(replay), dist / 1000.0)}
        return tile[2], {"source": "replay-fixture", "class": "ok",
                         "fixture": os.path.basename(replay),
                         "tiles": len(res.get("map_data", {}).get("features") or []),
                         "tile_dist_m": round(dist, 1),
                         "NOT_LIVE": "a saved response, replayed to verify the decision chain"}

    cp = cache_path(metro, dt_fields)
    if os.path.exists(cp):
        try:
            saved = json.load(open(cp, encoding="utf-8"))
            res = saved["result"]
            tile, dist = A.nearest_tile(res, want_latlon[0], want_latlon[1])
            return tile[2], {"source": "cache", "class": "ok", "path": os.path.basename(cp),
                             "tiles": len(res.get("map_data", {}).get("features") or []),
                             "tile_dist_m": round(dist, 1),
                             "fetched_utc": saved.get("fetched_utc")}
        except (ValueError, OSError, KeyError, TypeError):
            pass          # a corrupt cache entry is not a reason to fail; re-fetch it

    if not allow_paid:
        # 🔴 "NOT ATTEMPTED" IS OUR DECISION, NOT THE VENDOR'S FAILURE. Conflating the two produced
        # the worst output this project has emitted -- nine never-requested hours published as a
        # live decision. `no_data_reason` travels with the record so no summary can lose it.
        return None, {"source": "would-call", "class": "not_attempted",
                      "no_data_reason": "this run was not permitted to spend",
                      "credits_if_called": HEATMAP_CREDITS}
    return None, None                      # caller must submit this one


def submit_window(key, aoi, dt_fields):
    """POST one heatmap request. Returns a record carrying `activity_id`, or a failure class.

    Submitting is fast (about a second); it is the POLLING that takes minutes. Separating the two is
    what lets a 12-hour horizon be one wait instead of twelve.
    """
    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": ANALYTIC,
               "date_time": dt_fields}
    rec = {"source": "live", "window": dt_fields, "submitted_at": time.time()}
    try:
        req = urllib.request.Request("%s/heatmap" % V1, data=json.dumps(payload).encode(),
                                     headers={"api-key": key, "Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
        rec["submit_http"] = 200
    except urllib.error.HTTPError as e:
        rec.update({"submit_http": e.code,
                    "submit_error_body": e.read().decode("utf-8", "replace")[:400]})
        rec["class"] = classify_vendor(rec)
        return rec
    except Exception as e:
        rec.update({"submit_http": None, "submit_exception": str(e)[:300]})
        rec["class"] = classify_vendor(rec)
        return rec
    rec["activity_id"] = (resp.get("data") or {}).get("activity_id")
    if not rec["activity_id"]:
        rec["class"] = classify_vendor(rec)
    return rec


def read_status(key, aid):
    """One free status poll. Returns (status_string, result_dict_or_None), or (None, None)."""
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "%s/status/%s" % (V1, aid), headers={"api-key": key}), timeout=90)
        jd = json.loads(r.read())
    except Exception:
        return None, None
    st = str((jd.get("data") or {}).get("status") or jd.get("message") or "?").lower()
    return st, ((jd.get("data") or {}).get("result") or None)


# `recent_vendor_record` MOVED TO testing/common.py 2026-08-21 (Session 4), and it gained a second
# source in the move. It read `live_spend.json` only -- the live agent's own runs -- so on any day
# the live agent had not been run it returned None and the UI showed NO vendor record beside the
# button that can spend 50,640 credits. Measured on 2026-08-21: the last live run was 18 h old, the
# function returned None, and the COLLECTOR had four same-day billed failures on record. A record
# with a blind spot is gotcha #103 exactly, and this one sat in front of the spend button. It now
# reads the collector's per-attempt log as well, so both spenders report into one record -- which is
# also why the watcher can use it without a second copy. Imported at the top of this file, so
# `serve_live.py`'s `/api/health` and every call site here are unchanged.


def replay_sequence(replay, hours):
    """Expand one replay fixture into the CHRONOLOGICAL RUN of saved windows beside it.

    WHY. A replay used to hand the same saved window to every hour of the horizon, so the ambient
    trajectory was flat: 30.7076 C, twelve times. That proves the decide chain executes and shows
    nothing about a day -- no mode change can be forced by a temperature that never moves, and the
    environmental array beside it WAS varying hourly, so the two halves of the same replay
    disagreed about how time works.

    The live cache already holds consecutive windows for the same date (Ashburn has 09:00, 10:00,
    11:00 and 12:00 on 2026-08-20), so a replay can walk them and get a REAL hourly trajectory for
    nothing. Returns (paths, local_hours, date) with the horizon truncated to what actually exists
    -- a replay that pretends to more hours than were saved would be inventing exactly the thing
    this mode exists to avoid.
    """
    if not replay:
        return None, None, None
    try:
        here = os.path.dirname(os.path.abspath(replay))
        base = json.load(open(replay, encoding="utf-8"))
        day = ((base.get("window") or {}).get("start_date"))
    except (OSError, ValueError, TypeError, AttributeError):
        return [replay], None, None
    if not day:
        return [replay], None, None
    found = []
    for nm in sorted(os.listdir(here)):
        if not nm.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(here, nm), encoding="utf-8"))
        except (OSError, ValueError):
            continue
        w = d.get("window") or {}
        if w.get("start_date") != day or not w.get("start_time"):
            continue
        found.append((w["start_time"], os.path.join(here, nm)))
    if len(found) < 2:
        return [replay], None, day
    found.sort()
    found = found[:hours]
    return [p for _t, p in found], [int(t[:2]) for t, _p in found], day


def perceive_ambient(key, aoi, metro, want_latlon, plan_w, allow_paid, replay, max_calls,
                     on_progress):
    """Every window's ambient value: free ones first, then submit the rest and POLL THEM TOGETHER.

    🔴 WHY THIS IS A BATCH AND NOT A LOOP. It used to fetch windows one at a time, each waiting up
    to POLL_MAX_S for the vendor. With 10 uncached windows that is a worst case of **50 minutes**,
    and the user watched it apparently hang after hour 2. FortyGuard's own API is submit-then-poll,
    which is inherently parallel: submitting all outstanding windows first and then polling them in
    one loop makes the whole run bounded by ONE poll window rather than twelve.

    🔴 AND IT REPORTS WHILE IT WAITS. The progress hook used to fire only when a window RESOLVED, so
    a 300 s wait produced total silence -- the exact "dead spinner indistinguishable from a broken
    page" this module's comments claimed the hook prevented. It now emits a heartbeat every poll
    cycle carrying elapsed seconds and how many windows are still outstanding.
    """
    n = len(plan_w)
    temps = [None] * n
    recs = [None] * n
    pending = {}
    budget = max_calls if max_calls is not None else 10 ** 6

    # ---- 1. everything that costs nothing, first. A cached window must never consume a budget.
    for i, pw in enumerate(plan_w):
        # A LIST means a sequence replay -- one saved window per horizon hour, in order.
        rp = replay[i] if isinstance(replay, list) else replay
        v, rec = resolve_without_network(pw["window"], metro, want_latlon, rp, allow_paid)
        if rec is not None:
            temps[i], recs[i] = v, rec
            if on_progress:
                on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                             "window": pw["window"], "value_c": v,
                             "class": rec.get("class"), "source": rec.get("source")})
            continue
        if budget <= 0:
            recs[i] = {"source": "would-call", "class": "not_attempted",
                       "no_data_reason": "this run's %d-call budget was spent" % max_calls}
            if on_progress:
                on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                             "window": pw["window"], "value_c": None,
                             "class": "not_attempted", "source": "would-call"})
            continue
        pending[i] = pw
        budget -= 1

    if not pending:
        return temps, recs

    # ---- 2. submit them all. Fast, and it is what makes the wait shared.
    if on_progress:
        on_progress({"stage": "perceive",
                     "note": "submitting %d window%s to FortyGuard" % (len(pending),
                                                                       "" if len(pending) == 1
                                                                       else "s")})
    outstanding = {}
    for k, (i, pw) in enumerate(pending.items()):
        # STAGGERED, AND A REJECTION IS RETRIED ONCE.
        # A 12-window batch submitted back-to-back had one window come back `submit_rejected`
        # while the other eleven were accepted -- the signature of a rate limit rather than a bad
        # request, since the twelve differ only in `start_time`. A fraction of a second between
        # submits costs ~5 s against a 300 s poll and is free insurance; losing an hour of the
        # horizon to a transient 429 is not.
        if k:
            time.sleep(SUBMIT_STAGGER_S)
        rec = submit_window(key, aoi, pw["window"])
        if not rec.get("activity_id") and rec.get("submit_http") not in (None, 200):
            time.sleep(SUBMIT_RETRY_WAIT_S)
            retry = submit_window(key, aoi, pw["window"])
            retry["submit_retried_after"] = rec.get("submit_http")
            retry["first_attempt_body"] = (rec.get("submit_error_body") or "")[:200]
            rec = retry
        recs[i] = rec
        if rec.get("activity_id"):
            rec.update({"polls": 0, "statuses_seen": []})
            outstanding[i] = rec
        elif on_progress:
            on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                         "value_c": None, "class": rec.get("class"), "source": "live",
                         "detail": "HTTP %s %s" % (rec.get("submit_http"),
                                                   (rec.get("submit_error_body") or "")[:120])})

    # ---- 3. one poll loop over everything outstanding.
    t0 = time.time()
    while outstanding and time.time() - t0 < POLL_MAX_S:
        for i in list(outstanding):
            rec = outstanding[i]
            st, res = read_status(key, rec["activity_id"])
            if st is None:
                continue                          # transport hiccup; try again next cycle
            rec["polls"] += 1
            if st not in rec["statuses_seen"]:
                rec["statuses_seen"].append(st)
            if st == "completed":
                feats = ((res or {}).get("map_data") or {}).get("features")
                if feats:
                    rec.update({"terminal_status": "completed", "tiles": len(feats),
                                "elapsed_s": round(time.time() - t0, 1)})
                    rec["class"] = classify_vendor(rec)
                    tile, dist = A.nearest_tile(res, want_latlon[0], want_latlon[1])
                    rec["tile_dist_m"] = round(dist, 1)
                    temps[i] = tile[2]
                    # allow_nan=False: NaN is legal Python JSON and ILLEGAL standard JSON, so a
                    # cached field carrying one would load here and kill the browser silently.
                    json.dump({"result": res, "window": rec["window"], "granularity": GRAN,
                               "analytic_type": ANALYTIC, "fetched_utc": _utcnow().isoformat()},
                              open(cache_path(metro, rec["window"]), "w", encoding="utf-8"),
                              default=str, allow_nan=False)
                    del outstanding[i]
                    if on_progress:
                        on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                                     "value_c": temps[i], "class": "ok", "source": "live"})
                    continue
                rec["terminal_status"] = "completed"   # complete-but-empty: keep polling
            elif st in ("failed", "error", "cancelled", "canceled", "expired"):
                rec.update({"terminal_status": st, "tiles": 0,
                            "elapsed_s": round(time.time() - t0, 1)})
                rec["class"] = classify_vendor(rec)
                del outstanding[i]
                if on_progress:
                    on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                                 "value_c": None, "class": rec["class"], "source": "live"})
        if outstanding:
            if on_progress:
                on_progress({"stage": "perceive", "waiting": True,
                             "outstanding": len(outstanding),
                             "elapsed_s": round(time.time() - t0, 1),
                             "budget_s": POLL_MAX_S,
                             "note": "waiting on FortyGuard: %d of %d window(s) still processing"
                                     % (len(outstanding), n)})
            time.sleep(POLL_WAIT_S)

    # ---- 4. whatever never finished. Classified, never guessed at.
    for i, rec in outstanding.items():
        rec.update({"tiles": 0, "elapsed_s": round(time.time() - t0, 1)})
        rec["class"] = classify_vendor(rec)
        if on_progress:
            on_progress({"stage": "perceive", "hour_index": i, "of_hours": n,
                         "value_c": None, "class": rec["class"], "source": "live"})
    return temps, recs


def fetch_window(key, aoi, dt_fields, metro, allow_paid, want_latlon, replay=None):
    """One window. A thin wrapper over the batch path, so there is only one implementation."""
    v, rec = resolve_without_network(dt_fields, metro, want_latlon, replay, allow_paid)
    if rec is not None:
        return v, rec
    temps, recs = perceive_ambient(key, aoi, metro, want_latlon,
                                   [{"window": dt_fields, "cached": False, "lead_h": None}],
                                   allow_paid, replay, None, None)
    return temps[0], recs[0]


# ============================================================================
# 3. WIND AND DEW POINT -- NWS, free, keyless
# ============================================================================
_DUR = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$")


def _parse_duration_h(s):
    """ISO8601 duration -> whole hours. NWS emits PT1H, PT2H, PT6H, P1DT6H."""
    m = _DUR.match(s)
    if not m:
        return 1
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    return max(1, d * 24 + h + (1 if mi else 0))


# ============================================================================
# E2 -- THE ENVIRONMENTAL GATES, ON FORTYGUARD'S OWN FORECAST
# ============================================================================
# WHY THIS EXISTS. Until 2026-08-23 this agent perceived exactly ONE FortyGuard variable: dry-bulb
# temperature, from `/v1/heatmap`. Its humidity gate ran on NWS and its air-quality gate did not run
# at all -- which made LBNL's finding, that CONTAMINATION AND HUMIDITY are the documented reasons
# operators refuse free cooling, an argument the live agent cited and never acted on.
#
# DIAG-65 established two things that make this cheap:
#   1. `env_params` serves the forecast horizon (`n15_ep_future.json`, now + 6 h, full parameter set).
#   2. It is ALIVE while `heatmap` is down -- 15 fields x 24 hourly values on 2026-08-23, at the same
#      AOI and day every heatmap window was returning `n_cells: 0` for.
#
# ONE CALL COVERS THE WHOLE DAY. `filter_type: 2` over 00:00-23:00 returns 24 hourly values per
# field, so the entire 12-hour horizon costs 2,900 ONCE -- against 4,220 PER HOUR for the heatmap.
# The environmental gates are therefore the cheapest part of the perception, not the most expensive.
ENV_PARAMS_CREDITS = 2_900


def fortyguard_env(key, lat, lon, day_site_local, allow_paid, verbose=True):
    """One `env_params` call: 24 hourly values per field for `day_site_local`, keyed by local hour.

    🔴 THE ALIGNMENT TRAP, AND WHY THIS RETURNS A DICT KEYED BY HOUR RATHER THAN A LIST.
    `env_params` reports a FIXED `GMT-5` offset and does not apply daylight saving (findings 1.8,
    severity HIGH). In August our Virginia AOI is UTC-4, so the response stamps `-05:00` on hours we
    requested as EDT. Indexing that array by position is exactly how the nine-hour bug happened,
    one order of magnitude smaller and therefore harder to see.
    So the alignment is taken from the HOUR LABEL the response echoes back -- we asked for 00:00..23:00
    and it returns 00:00..23:00 -- and the offset it stamps is deliberately NOT trusted. Whether that
    reading is right is then MEASURED, free, by `env_alignment_lag()` below.

    Returns (by_hour, meta) or (None, meta) -- never raises, because a failed environmental fetch
    must degrade the agent to the NWS path rather than kill the run.
    """
    meta = {"endpoint": "env_params", "requested_day_site_local": day_site_local,
            "credits": 0, "class": None, "n_fields": 0,
            "dst_caveat": "env_params reports a fixed GMT-5 offset and does not apply daylight "
                          "saving (findings 1.8). Hours are aligned by the LOCAL HOUR LABEL the "
                          "response echoes, not by its stated offset; the residual risk is "
                          "measured against NWS rather than assumed away."}
    if not allow_paid:
        meta["class"] = "not_attempted"
        meta["why"] = "paid environmental fetch not authorised for this run"
        return None, meta

    payload = {"latitude": round(lat, 5), "longitude": round(lon, 5),
               # REQUIRED by the schema and NEVER consumed: the endpoint computes
               # `heat_index_celsius` from whatever is sent here and echoes it back as
               # `locations[].temperature` (findings 1.1 and 1.7). Both are on our refused list.
               "temperature": 25.0,
               "date_time": {"start_date": day_site_local, "start_time": "00:00",
                             "end_time": "23:00", "filter_type": 2}}
    before = credits_remaining(key)
    r = submit_poll(key, "env_params", payload, "live_env_%s" % day_site_local,
                    require_data=False)
    after = credits_remaining(key)

    # 🔴 PARSE BEFORE CLASSIFYING, and pass the REAL payload count. The first version classified with
    # `tiles=0` -- because env_params returns no tiles -- so `classify_vendor` saw a completed job
    # carrying nothing and labelled a fully successful call `completed_but_empty`. On the very first
    # run that mislabelled 15 populated fields over 24 hours as a vendor failure.
    # It would not have stayed cosmetic: `recent_vendor_record` counts `completed_but_empty` as a
    # billed failure, so every successful environmental fetch would have degraded the success rate
    # shown next to the button that spends money.
    # The lesson is the same one DIAG-65 taught an hour earlier: the shared classifier encodes what
    # success looks like for a TILE endpoint, and a different endpoint has to hand it its own notion
    # of "did data come back" rather than inherit one that cannot apply.
    locs0 = ((r.get("result") or {}).get("locations") or [])
    params0 = (locs0[0].get("parameters") if locs0 else None) or (
        {k: v for k, v in locs0[0].items() if isinstance(v, list)} if locs0 else {})
    n_values = sum(1 for v in (params0 or {}).values() if isinstance(v, list)
                   for x in v if x is not None)
    rec = vendor_rec(r, tiles=n_values)      # "tiles" here means "values returned"
    cls = classify_vendor(rec)
    meta.update({"class": cls, "credits": max(0, before - after),
                 "activity_id": rec.get("activity_id"),
                 "credits_before": before, "credits_after": after})
    if verbose:
        say("      env_params: %s (%s credits)" % (cls, format(meta["credits"], ",")))

    # 🔴 RECORD THE SPEND WHERE THE LEDGER LOOKS. `api_usage_ledger.py` walks `testing/results/`;
    # this module writes to `demo/`. That exact mismatch is gotcha #103 -- the first 12-hour live run
    # spent 46,420 credits that no audited figure knew about while check 9 reported green -- and it
    # would have repeated here for every environmental call. APPEND, never overwrite (gotcha #100).
    if meta["credits"]:
        _append_env_spend(meta)

    locs = ((r.get("result") or {}).get("locations") or [])
    if not locs:
        meta["why"] = "no locations block returned"
        return None, meta
    params = locs[0].get("parameters") or {k: v for k, v in locs[0].items()
                                           if isinstance(v, list)}
    stamps = ((r.get("result") or {}).get("metadata") or {}).get("timestamps") or []
    by_hour = {}
    for i, ts in enumerate(stamps):
        try:
            hh = int(str(ts)[11:13])
        except (ValueError, IndexError):
            continue
        row = {}
        for k, v in (params or {}).items():
            if isinstance(v, list) and i < len(v) and v[i] is not None:
                row[k] = v[i]
        if row:
            by_hour[hh] = row
    meta["n_fields"] = len({k for row in by_hour.values() for k in row})
    meta["n_hours"] = len(by_hour)
    if not by_hour:
        meta["why"] = "parameters present but every hourly array was empty"
        return None, meta
    return by_hour, meta


def saved_fortyguard_env(day_site_local, want_latlon=None, verbose=True):
    """A SAVED FortyGuard `env_params` response, replayed exactly as a saved heatmap is.

    WHY A REPLAY USES THIS RATHER THAN SKIPPING. The first version of E2 skipped the environmental
    fetch during a replay so the run stayed free -- which quietly dropped the humidity gate back
    onto NWS and printed "skipped because this is a replay". Both halves were wrong: a replay of
    THIS agent should show FortyGuard supplying every gate it supplies live, and the only reason the
    heatmap can be replayed is that we saved its response. We saved the environmental ones too.

    So a replay is free, reproducible, AND still FortyGuard's data end to end -- the same
    relationship the heatmap already had. The only input that is not theirs, in replay or live, is
    wind, because they do not publish a wind field (findings section 6).

    Prefers a response for the requested day; falls back to the most complete one on disk and says
    which it used, because silently substituting a different day's air would be the borrowed-data
    mistake this project has already made twice.
    """
    meta = {"endpoint": "env_params", "requested_day_site_local": day_site_local,
            "credits": 0, "class": "saved", "source": "saved FortyGuard response", "n_fields": 0}
    fixdir = os.path.join(TESTING, "results", "fixtures")
    best, best_score, best_name = None, -1, None
    try:
        names = sorted(os.listdir(fixdir))
    except OSError:
        names = []
    for nm in names:
        if not nm.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(fixdir, nm), encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(d, dict) or "locations" not in d or "map_data" in d:
            continue
        locs = d.get("locations") or []
        if not locs:
            continue
        params = locs[0].get("parameters") or {k: v for k, v in locs[0].items()
                                               if isinstance(v, list)}
        stamps = (d.get("metadata") or {}).get("timestamps") or []
        n_vals = sum(1 for v in (params or {}).values() if isinstance(v, list)
                     for x in v if x is not None)
        # 🔴 LOCATION FIRST, THEN DATE, THEN COMPLETENESS -- and location outranks date because
        # getting it wrong is the worse error. The first version scored on date alone, so the moment
        # both Ashburn and Chicago had a 2026-08-20 response, CHICAGO'S REPLAY PICKED ASHBURN'S
        # HUMIDITY and reported `same_day: True` -- correct about the date, silently wrong about the
        # continent's worth of air between them. That is the same borrowed-data defect as the aerial
        # panel (gotcha #98) and the wind record (#132), for the third time.
        # `env_params` is a POINT call and its response echoes the point back as `lat`/`lon`, so the
        # match is measured rather than inferred from a filename.
        near = True
        if want_latlon and locs:
            la, lo = locs[0].get("lat"), locs[0].get("lon")
            if isinstance(la, (int, float)) and isinstance(lo, (int, float)):
                near = (abs(float(la) - want_latlon[0]) < 0.05
                        and abs(float(lo) - want_latlon[1]) < 0.05)
            else:
                near = False          # a response that cannot prove where it is does not qualify
        if not near:
            continue
        score = n_vals + (1_000_000 if any(str(t).startswith(day_site_local) for t in stamps) else 0)
        if score > best_score and n_vals:
            best, best_score, best_name = (d, params, stamps), score, nm
    if not best:
        meta["why"] = ("no saved env_params response for this SITE%s. Falling back to NWS rather "
                       "than replaying another site's air -- borrowing it is the defect this match "
                       "exists to prevent." % ("" if not want_latlon
                                               else " (%.4f, %.4f)" % want_latlon))
        return None, meta
    _d, params, stamps = best
    by_hour = {}
    for i, ts in enumerate(stamps):
        try:
            hh = int(str(ts)[11:13])
        except (ValueError, IndexError):
            continue
        row = {k: v[i] for k, v in (params or {}).items()
               if isinstance(v, list) and i < len(v) and v[i] is not None}
        if row:
            by_hour[hh] = row
    meta.update({"fixture": best_name, "n_hours": len(by_hour),
                 "n_fields": len({k for r in by_hour.values() for k in r}),
                 "same_day": bool(any(str(t).startswith(day_site_local) for t in stamps))})
    if not meta["same_day"]:
        meta["note"] = ("no saved response for %s, so %s is replayed instead. The gates are real "
                        "FortyGuard values but they are NOT this date's air." % (day_site_local,
                                                                                 best_name))
    if verbose:
        say("      env_params: replayed from %s (%d fields x %d hours, 0 credits)"
            % (best_name, meta["n_fields"], meta["n_hours"]))
    return (by_hour or None), meta


def _append_env_spend(meta):
    """One entry per paid `env_params` call, where `api_usage_ledger.py` will find it."""
    path = os.path.join(TESTING, "results", "live_env_spend.json")
    try:
        doc = json.load(open(path, encoding="utf-8"))
        if not isinstance(doc, dict) or "runs" not in doc:
            raise ValueError("unexpected shape")
    except (OSError, ValueError):
        doc = {"purpose": "every paid env_params call made by live.py, so the spend ledger sees it",
               "endpoint": "env_params", "runs": []}
    doc["runs"].append({k: meta.get(k) for k in
                        ("requested_day_site_local", "class", "credits", "activity_id",
                         "credits_before", "credits_after", "n_fields", "n_hours")})
    try:
        json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, allow_nan=False)
    except OSError:
        pass          # a ledger write must never take down a run that already spent the money


def dewpoint_from_env(row):
    """Dew point from FortyGuard's own humidity fields, or None.

    `env_params` returns NO DRY-BULB (findings 1.7 -- `locations[].temperature` is our own input
    echoed back), so the usual RH+temperature route is unavailable from this endpoint alone. What it
    does return is `wet_bulb_temperature_celsius`, and for the gate's purpose the wet-bulb IS the
    more defensible quantity: real economizers limit on wet-bulb rather than dry-bulb alone, which
    is why `environment.py` was built around it.
    So the gate compares FortyGuard's wet-bulb against the same limit, and the value is labelled as
    a wet-bulb rather than silently called a dew point. Conflating the two would be a units error
    dressed as a measurement.
    """
    wb = row.get("wet_bulb_temperature_celsius")
    return float(wb) if isinstance(wb, (int, float)) else None


def env_alignment_lag(fg_by_hour, nws_hours, start_utc, tz_offset_h):
    """MEASURE the hour alignment between FortyGuard's array and NWS, instead of assuming it.

    This is the free half of the DST problem. `live.py` already fetches NWS dew point for the same
    hours at no cost, so the two humidity series can be cross-correlated: if FortyGuard's array is
    aligned, the best fit is at lag 0; if their fixed GMT-5 offset has shifted it, the best fit is
    at lag +/-1 and we have MEASURED a documented vendor defect rather than guessed about it.

    Returns a dict, always -- an unmeasurable lag is reported as unmeasurable, never as zero.
    """
    from datetime import timedelta as _td
    out = {"method": "cross-correlate FortyGuard wet-bulb against NWS dew point over the horizon",
           "lag_hours": None, "n_pairs": 0, "note": None}
    best, best_err, scores = None, None, {}
    for lag in (-1, 0, 1):
        errs = []
        for j, h in enumerate(nws_hours):
            if h.get("dewpoint_c") is None:
                continue
            hh = (start_utc + _td(hours=j + tz_offset_h + lag)).hour
            row = fg_by_hour.get(hh)
            if not row:
                continue
            wb = dewpoint_from_env(row)
            if wb is None:
                continue
            errs.append(abs(wb - float(h["dewpoint_c"])))
        if len(errs) >= 3:
            m = sum(errs) / len(errs)
            scores[lag] = m
            if best_err is None or m < best_err:
                best, best_err = lag, m
                out["n_pairs"] = len(errs)
    if best is None:
        out["note"] = ("too few overlapping hours to measure the lag; FortyGuard's array is used "
                       "as labelled and the DST caveat stands unresolved")
        out["applied_lag_hours"] = 0
        return out
    out["lag_hours"] = best
    out["mean_abs_difference_c"] = round(best_err, 3)
    out["candidates_c"] = {str(k): round(v, 3) for k, v in sorted(scores.items())}

    # 🔴 MEASURING A LAG AND ACTING ON ONE ARE DIFFERENT DECISIONS, and the first version conflated
    # them. On its first real run this picked lag = -1 from FOUR overlapping hours and the agent
    # indexed FortyGuard's array by it -- shifting the humidity gate by an hour on the strength of a
    # four-point comparison whose margin nobody had looked at.
    # A non-zero shift is now APPLIED only when the evidence is strong enough to carry it:
    #   * at least MIN_PAIRS overlapping hours, and
    #   * the winner beats the as-labelled alignment by a clear margin, not by a hair.
    # Otherwise the array is used AS LABELLED and the disagreement is reported unresolved. Erring
    # toward the label is the conservative direction: it is what the vendor says the data is, and a
    # wrong shift is silent while an unresolved flag is visible.
    MIN_PAIRS, MIN_MARGIN_C = 6, 0.25
    at_zero = scores.get(0)
    margin = (at_zero - best_err) if at_zero is not None else None
    strong = (best == 0) or (out["n_pairs"] >= MIN_PAIRS and margin is not None
                             and margin >= MIN_MARGIN_C)
    out["applied_lag_hours"] = best if strong else 0
    out["evidence"] = {"min_pairs_required": MIN_PAIRS, "min_margin_c": MIN_MARGIN_C,
                       "margin_vs_as_labelled_c": None if margin is None else round(margin, 3),
                       "strong_enough_to_apply": bool(strong)}
    if not strong:
        out["unresolved"] = (
            "measured lag %+d h is NOT applied: %d overlapping hour(s) against %d required, margin "
            "%s C against %.2f required. The array is used AS LABELLED and the daylight-saving "
            "question (findings 1.8) stands open. Re-run over a longer horizon to settle it."
            % (best, out["n_pairs"], MIN_PAIRS,
               "n/a" if margin is None else "%.3f" % margin, MIN_MARGIN_C))
    out["note"] = ("wet-bulb is BELOW dew point whenever the air is unsaturated, so this difference "
                   "is expected to be positive and is NOT an error measurement -- it is used only "
                   "to choose between three candidate alignments, where the correct one should be "
                   "the smallest and the neighbours should be clearly worse")
    return out


def nws_hourly(lat, lon, start_utc, hours):
    """Per-hour wind bearing (deg), wind speed (m/s) and dew point (C) from api.weather.gov.

    NWS returns each field RUN-LENGTH ENCODED over ISO intervals (`...T04:00:00+00:00/PT6H`), so a
    12-hour horizon can arrive as three entries. They are expanded to one value per hour here.

    The hourly `forecast/hourly` endpoint is NOT used for wind: it gives `windDirection` as a
    16-point compass string ("NE"), i.e. 22.5 deg resolution, against a rise table computed on a
    5 deg grid. The gridpoint endpoint gives numeric degrees, so it is the one used.
    """
    out = {"source": "api.weather.gov gridpoint forecast", "ok": False}
    try:
        p = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://api.weather.gov/points/%.4f,%.4f" % (lat, lon), headers=NWS_UA),
            timeout=45).read())["properties"]
        grid_url = p["forecastGridData"]
        out["grid"] = "%s %s,%s" % (p.get("gridId"), p.get("gridX"), p.get("gridY"))
        gp = json.loads(urllib.request.urlopen(urllib.request.Request(
            grid_url, headers=NWS_UA), timeout=60).read())["properties"]
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        return out

    def series(field, conv=lambda v: v):
        """Expand one RLE field into {utc_hour_iso: value}."""
        got = {}
        for v in (gp.get(field) or {}).get("values") or []:
            if v.get("value") is None:
                continue
            try:
                t_str, dur = v["validTime"].split("/")
                t = datetime.fromisoformat(t_str).astimezone(timezone.utc)
            except (ValueError, KeyError):
                continue
            for k in range(_parse_duration_h(dur)):
                got[(t + timedelta(hours=k)).replace(minute=0, second=0,
                                                     microsecond=0).isoformat()] = conv(v["value"])
        return got

    drct = series("windDirection")
    sknt = series("windSpeed", lambda kmh: kmh / 3.6)        # NWS gives km/h; the solver wants m/s
    dewp = series("dewpoint")
    rows, missing = [], []
    for i in range(hours):
        t = (start_utc + timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        k = t.isoformat()
        row = {"utc": k, "bearing_deg": drct.get(k), "speed_ms": sknt.get(k),
               "dewpoint_c": dewp.get(k)}
        if row["bearing_deg"] is None or row["speed_ms"] is None:
            missing.append(k)
        rows.append(row)
    out.update({"ok": not missing, "hours": rows, "missing": missing,
                "uom_note": "windSpeed converted km/h -> m/s; dewpoint already C"})
    return out


# ============================================================================
# 4. THE MARGIN -- measured on FortyGuard's own errors, with every caveat attached
# ============================================================================
def measured_margin(trace, site, horizon_h=HORIZON_H):
    """The conformal margin to apply to a LIVE FortyGuard forecast, plus its provenance.

    Read from `cycle.bound_day_level`, which is the quantile of FortyGuard's own measured
    forecast-vs-outcome day-level residuals. NOT from rolling.py's per-lead margins: those are
    calibrated on de-biased PERSISTENCE error and describe a different forecaster entirely.
    """
    cyc = (trace or {}).get("cycle") or {}
    dl = cyc.get("bound_day_level") or {}
    pairs = cyc.get("pairs") or []
    prov = (trace or {}).get("fortyguard_provenance") or {}
    own = bool(prov.get("own_measured_day_pairs"))
    leads = [p.get("lead_h") for p in pairs if p.get("lead_h") is not None]
    return dl.get("margin"), {
        "margin_c": dl.get("margin"),
        "source": "cycle.bound_day_level -- the quantile of FortyGuard's OWN measured "
                  "forecast-vs-outcome day-level residuals",
        "not_used": "rolling.py's per-lead margins are calibrated on de-biased PERSISTENCE error, "
                    "which describes a different forecaster. Using them here would be the category "
                    "error PLAN section 8e exists to prevent.",
        "n_calibration_pairs": dl.get("n"),
        "clamped_to_attainable": dl.get("clamped"),
        "attainable_coverage_ceiling": dl.get("attainable"),
        "nominal_coverage": dl.get("nominal"),
        "pairs_needed_for_nominal": dl.get("n_needed_for_nominal"),
        "measured_pooled_coverage": cyc.get("pooled_coverage"),
        "prereg_verdict": "FAIL -- 65.6 % measured against a 90 % promise, worst day 0.0 %",
        "calibration_leads_h": leads,
        "calibration_target_hour_site": 14,
        # The horizon is passed in so the sentence names the ACTUAL leads. It read "1..N h" with a
        # literal N, which shipped to the screen -- a placeholder in published prose reads as
        # carelessness and invites the reader to distrust the numbers beside it.
        "EXTRAPOLATION_WARNING": (
            "Every calibration pair was measured at a ~%s h lead against a 14:00 site-local "
            "window. This run bounds leads of 1..%d h at whatever hour it is now, so the margin is "
            "being applied OUTSIDE its calibration domain. Marginal coverage measured in one "
            "(lead, hour-of-day) cell is not a guarantee in another."
            % ((("%.1f" % leads[0]) if leads else "9.4"), horizon_h)),
        "site_owns_this_calibration": own,
        "borrowed_from": None if own else "ashburn",
        # NOTE the trailing comma here once made this a 1-TUPLE, which serialises as a
        # single-element list and reads as a data-shape bug to anything consuming it.
        "borrowed_note": None if own else (
            "%s has no FortyGuard day-pairs of its own, so the margin above was measured at "
            "Ashburn and applied here. Its hours and geometry are its own; its BOUND is not."
            % (site or {}).get("key")),
    }


# ============================================================================
# 5. THE RUN
# ============================================================================
def _utcnow():
    return datetime.now(timezone.utc)


def site_local_now(tz_name):
    try:
        from zoneinfo import ZoneInfo
        return _utcnow().astimezone(ZoneInfo(tz_name))
    except Exception:
        return _utcnow()


def live_run(metro=None, hours=HORIZON_H, allow_paid=False, cfg=None, verbose=True,
             replay=None, on_progress=None, max_calls=None):
    """Perceive now, decide the next `hours`, for one site. Returns the emitted dict."""
    metro = metro or M.metro_key()
    # 🔴 SET THE METRO IN THE ENVIRONMENT BEFORE ANY A.* CALL THAT RESOLVES A PATH.
    # `A.rise_table()` takes no metro argument -- it resolves through `M.demo_path`, which reads
    # `metro_key()`, which reads os.environ["METRO"]. So calling live_run(metro="chicago") without
    # this line loads ASHBURN'S rise table and silently decides Chicago's schedule on Virginia's
    # geometry. That is the exact class of fault this rework exists to remove, and a fallback that
    # always fires is not a fallback, it is the implementation (gotcha #80).
    os.environ["METRO"] = metro
    if M.metro_key() != metro:
        raise SystemExit("metro did not take: asked for %r, resolver says %r" % (metro,
                                                                                M.metro_key()))
    site = next((s for s in json.load(open(M.demo_path("sites.json", M.DEFAULT_METRO),
                                           encoding="utf-8"))["sites"] if s["key"] == metro), None)
    if site is None:
        raise SystemExit("unknown site %r -- not in sites.json" % metro)
    if not site.get("offerable"):
        raise SystemExit("%r is not offerable (%s). Refusing to publish a live schedule for a site "
                         "this project has refused." % (metro, site.get("not_offerable_because")))
    trace = json.load(open(M.demo_path("trace.json", metro), encoding="utf-8"))
    cfg = dict({"limit_c": 24.0, "switch_budget": 2, "min_dwell_h": 3,
                "dewpoint_limit_c": 15.0, "bank_mode": "longest"}, **(cfg or {}))

    tz = (site or {}).get("tz") or "America/New_York"
    now_local = site_local_now(tz)
    start_local = first_window_start(now_local)
    start_utc = start_local.astimezone(timezone.utc)

    centre = trace["site"]["centre"]
    aoi = box_aoi(centre[0], centre[1], SIDE_KM)
    # The site's own tile, not the AOI mean: 8x8 km of Ashburn spans 1.45 C, so a mean would
    # describe the corridor and not the plant.
    want_latlon = (centre[0], centre[1])

    out = {
        "generated_by": "AGENTIC-ARBITER/src/live.py",
        "mode": "replay-verification" if replay else "live",
        "metro": metro,
        "site_label": (site or {}).get("label"),
        "committed_pair": (site or {}).get("committed"),
        "utc_now": _utcnow().isoformat(),
        "site_local_now": now_local.isoformat(),
        "site_tz": tz,
        "horizon_h": hours,
        "first_hour_site_local": start_local.isoformat(),
        "config": cfg,
        "aoi": {"centre": centre, "side_km": SIDE_KM, "granularity": GRAN,
                "analytic_type": ANALYTIC},
        "sources": {
            "ambient_dry_bulb": "FortyGuard /v1/heatmap, one call per hour, this site's own tile",
            "wind_and_dewpoint": "NWS api.weather.gov gridpoint forecast (free, keyless). "
                                 "FortyGuard's API carries no wind field, and env_params returns "
                                 "no dry-bulb -- findings section 9.4",
            "rise": "this site's own 576-solve rise table on its real OSM geometry",
        },
    }

    # 🔴 THE HORIZON MUST BE SETTLED BEFORE ANY PER-HOUR ARRAY IS BUILT.
    # This block used to sit below the NWS fetch, so truncating the horizon left the wind and
    # dew-point arrays at the ORIGINAL length. `bound = amb + rise + margin` then BROADCAST a
    # length-1 ambient across a length-6 rise, silently producing six bounds from one measurement --
    # and `hours_with_NO_forecast` came out as **-5**, a negative count, which is what gave it away.
    # Truncate first, fetch second, and assert the lengths agree afterwards.
    _, plan_w = horizon_windows(metro, hours, now_local)

    # 🔴 A SHORTER COMPLETE HORIZON BEATS NO HORIZON. When the call budget cannot cover every
    # window, the first version refused the whole run -- correct in that it never scheduled an hour
    # it had not looked at, but far too blunt: with 9 calls left and 11 needed the user simply could
    # not run the agent, and the screen said so at length. TRUNCATE instead. The horizon shrinks to
    # the longest PREFIX the budget can cover, so there are no unlooked-at hours inside it and the
    # result is a genuine complete decision over fewer hours.
    #
    # A prefix specifically, not a subset: the DP schedules contiguous hours, and the near hours are
    # the ones an operator can still act on. Holes in the middle would be useless even if cheaper.
    if max_calls is not None and max_calls >= 0:
        spend_needed, keep = 0, 0
        for pw in plan_w:
            nxt = spend_needed + (0 if pw["cached"] else 1)
            if nxt > max_calls:
                break
            spend_needed, keep = nxt, keep + 1
        if keep < len(plan_w):
            out["horizon_truncated"] = {
                "requested_hours": hours, "covered_hours": keep,
                "call_budget": max_calls, "calls_needed_for_full_horizon":
                    sum(1 for pw in plan_w if not pw["cached"]),
                "why": "the call budget covers %d of the %d requested hours. The horizon was "
                       "SHORTENED rather than leaving hours inside it unlooked-at -- every hour "
                       "reported below was actually perceived." % (keep, hours)}
            plan_w = plan_w[:keep]
            hours = keep
            if not hours:
                out["status"] = "no_call_budget"
                out["operator_message"] = (
                    "NO SCHEDULE. The first hour of the horizon is not cached and there is no call "
                    "budget left to fetch it, so there is nothing the agent has perceived. Restart "
                    "the server with a higher --max-live-calls, or wait for the cache to catch up.")
                return out

    # ---- A REPLAY WALKS THE SAVED SEQUENCE, one window per hour, instead of repeating one -------
    # 🔴 THIS SITS BEFORE THE NWS FETCH, and that placement is the whole of gotcha #117.
    # It was below it, so truncating the horizon from 12 to 4 left a 12-row wind array against
    # 4 temperatures -- and the length guard caught it, which is the only reason it is not a
    # silent broadcast producing four plausible bounds from the wrong wind. SETTLE THE HORIZON
    # BEFORE BUILDING ANY PER-HOUR ARRAY: the comment three screens down says exactly this and
    # I still put it in the wrong place.
    # Truncating the horizon to what was actually saved is the point: a replay that ran for twelve
    # hours off four saved windows would be inventing eight of them.
    replay_seq, replay_hours, replay_day = replay_sequence(replay, hours)
    if replay_seq and len(replay_seq) > 1:
        if len(replay_seq) < hours:
            plan_w = plan_w[:len(replay_seq)]
            hours = len(replay_seq)
        out["replay_sequence"] = {
            "date": replay_day, "windows": len(replay_seq),
            "hours_site_local": replay_hours,
            "note": "the ambient trajectory is %d CONSECUTIVE saved windows from %s, not one window "
                    "repeated -- so the temperature varies hour to hour exactly as it did on the "
                    "day. Wind is still live, because no saved wind exists for a past date."
                    % (len(replay_seq), replay_day)}
        replay = replay_seq


    out["horizon_plan"] = [{"window": p["window"], "lead_h": p["lead_h"],
                            "already_cached": p["cached"]} for p in plan_w]

    # ---- WIND + DEW POINT (free) -------------------------------------------------
    if on_progress:
        on_progress({"stage": "perceive", "note": "reading live wind and dew point from NWS"})
    nws = nws_hourly(centre[0], centre[1], start_utc, hours)
    out["nws"] = {k: v for k, v in nws.items() if k != "hours"}
    if not nws.get("ok"):
        out["status"] = "wind_unavailable"
        out["operator_message"] = (
            "No schedule: the free wind/dew-point forecast could not be read (%s). The plume rise "
            "depends on bearing and speed, so without wind there is no bound to publish -- and an "
            "assumed calm would be the unsafe direction, because recirculation is worst in calm air."
            % (nws.get("error") or "missing hours: %s" % (nws.get("missing") or [])[:3]))
        return out

    # ---- AMBIENT, ONE CALL PER HOUR ---------------------------------------------
    key = load_key() if allow_paid else None
    before = credits_remaining(key) if allow_paid else None

    # ---- E2: THE ENVIRONMENTAL GATES, ON FORTYGUARD'S OWN FORECAST ----------------
    # ONE call for the whole day, before the per-hour heatmap loop, because it is cheap and because
    # it is the only part of the perception that still works while the heatmap path is down. If it
    # fails the run continues on NWS: an environmental fetch that dies must degrade the agent, not
    # kill it.
    if on_progress:
        on_progress({"stage": "perceive",
                     "note": "reading humidity and air quality from FortyGuard env_params"})
    # 🔴 A REPLAY REPLAYS EVERYTHING FORTYGUARD SUPPLIES -- it does not skip half of it.
    # Two earlier versions of this were wrong. The first let a replay make a LIVE PAID env call, so
    # something stamped "REPLAY VERIFICATION" charged 2,900 and stopped being reproducible. The
    # second skipped the fetch to keep it free, which silently dropped the humidity gate back onto
    # NWS and printed "skipped because this is a replay" -- turning a replay of THIS agent into a
    # replay of a lesser one.
    # The right answer was already sitting on disk: we save environmental responses exactly as we
    # save heatmap responses, so a replay uses a saved one. Free, reproducible, and still
    # FortyGuard's data on every gate they supply. Wind is NWS in both modes because they publish
    # no wind field -- that is the only exception, in replay and live alike.
    env_live = allow_paid and (replay is None or bool(cfg.get("env_live_during_replay")))
    if env_live:
        fg_env, fg_env_meta = fortyguard_env(key, centre[0], centre[1],
                                             start_local.strftime("%Y-%m-%d"), True, verbose)
        fg_env_meta["mode"] = "live"
    else:
        # 🔴 MATCH THE REPLAYED HEATMAP'S DATE, NOT TODAY'S.
        # The first version asked for today's date even in a replay, so it paired a 2026-08-20
        # temperature field with 2026-08-22 humidity -- two days apart -- and then reported
        # `same_day: True`, because it had compared the humidity against TODAY rather than against
        # the field it was standing beside. The flag was answering a question nobody asked.
        # A replay is supposed to be one site, one date, one set of saved responses. Where the
        # date is knowable it is used; the live-cache wrapper records the window it fetched.
        # ⚠ This branch also runs on a DRY RUN, where `replay` is None -- so the file read is
        # guarded on the path existing rather than on the exception type. The first version caught
        # OSError/ValueError and let a `TypeError: expected str, not NoneType` through, which took
        # the self-test down. Catching the exceptions you thought of is not the same as handling
        # the inputs you actually get.
        want_day = start_local.strftime("%Y-%m-%d")
        if replay:
            try:
                _rj = json.load(open(replay, encoding="utf-8"))
                want_day = ((_rj.get("window") or {}).get("start_date")) or want_day
            except (OSError, ValueError, TypeError, AttributeError):
                pass
        fg_env, fg_env_meta = saved_fortyguard_env(want_day, (centre[0], centre[1]), verbose)
        fg_env_meta["mode"] = "saved"
        fg_env_meta["matched_against"] = want_day
        fg_env_meta["matched_against_note"] = (
            "the replayed heatmap's own window date, so the temperature and the humidity describe "
            "the same day when a response for it exists")
    out["fortyguard_env"] = fg_env_meta
    if fg_env:
        # MEASURE the alignment against the NWS series we already hold, free. See the DST note on
        # `fortyguard_env`: their fixed GMT-5 offset means "hour 14" may or may not be 14:00 local,
        # and this is the only way to find out without a second paid call.
        tz_off = int(round((start_local.utcoffset().total_seconds() if start_local.utcoffset()
                            else 0) / 3600.0))
        fg_env_meta["alignment"] = env_alignment_lag(fg_env, nws["hours"], start_utc, tz_off)
    # A PER-RUN CALL BUDGET, enforced where the calls actually happen. Cached windows never consume
    # it, because they cost nothing. Once it is spent the remaining windows are marked
    # `not_attempted` with the reason -- never silently dropped.
    # ONE BATCH, ONE WAIT. `perceive_ambient` settles every free window first, submits the rest
    # together, and polls them in a single loop -- so the run is bounded by one poll window rather
    # than one per hour, and it heartbeats while it waits.
    windows = [pw["window"] for pw in plan_w]
    temps, recs = perceive_ambient(key, aoi, metro, want_latlon, plan_w, allow_paid, replay,
                                   max_calls, on_progress)
    for i, pw in enumerate(plan_w):
        recs[i]["lead_h"] = pw["lead_h"]
        if verbose:
            v = temps[i]
            say("      h+%-2d  %s %s  ->  %s  [%s]"
                % (i + 1, pw["window"]["start_date"], pw["window"]["start_time"],
                   ("%.4f C" % v) if v is not None else "no data", recs[i].get("class")))
    after = credits_remaining(key) if allow_paid else None
    out["spend"] = {"credits_before": before, "credits_after": after,
                    "credits_spent": (before - after) if (before and after) else 0,
                    "calls_attempted": sum(1 for r in recs if r.get("source") == "live"),
                    "cache_hits": sum(1 for r in recs if r.get("source") == "cache"),
                    "note": "cache hits are byte-identical to fresh calls -- N-55"}
    _append_spend_ledger(out, recs)
    out["windows"] = [{"window": w, **{k: v for k, v in r.items() if k != "window"}}
                      for w, r in zip(windows, recs)]

    got = [i for i, t in enumerate(temps) if t is not None]
    n_not_attempted = sum(1 for r in recs if r.get("class") == "not_attempted")
    if not got or n_not_attempted:
        # WHY there is no data decides what to TELL the operator, and the reasons are not
        # interchangeable. An earlier version reported every one of them as "dryrun" whenever
        # --paid was absent, so a fixture-mismatch refusal was announced as a costing estimate.
        #
        # 🔴 AND `n_not_attempted` NOW SHORT-CIRCUITS EVEN WHEN SOME HOURS DID RETURN DATA. That is
        # the fix for the worst output this project has produced: 3 cached hours plus 9 windows
        # that were never requested were published as "Decided at 09:55 ... 0 live calls" with all
        # nine unrequested hours scheduled MECHANICAL. The agent had not looked at those hours. A
        # schedule may only be published over hours the agent actually perceived, so a run that
        # skipped any window is reported as INCOMPLETE and emits no schedule at all.
        cls = sorted({r.get("class") for r in recs})
        out["vendor_classes"] = cls
        if cls == ["not_attempted"]:
            out["status"] = "dryrun"
            out["operator_message"] = (
                "DRY RUN -- no call was made. %d hourly windows would be fetched, %d already "
                "cached, so %d paid calls at %s credits = %s credits. The plan's binding limit is "
                "%d heatmaps/day, not credits."
                % (hours, out["spend"]["cache_hits"],
                   hours - out["spend"]["cache_hits"], format(HEATMAP_CREDITS, ","),
                   format((hours - out["spend"]["cache_hits"]) * HEATMAP_CREDITS, ","),
                   DAILY_HEATMAP_CAP))
        elif n_not_attempted:
            n_have = len(got)
            reasons = sorted({r.get("no_data_reason") for r in recs
                              if r.get("class") == "not_attempted" and r.get("no_data_reason")})
            out["status"] = "incomplete_not_attempted"
            out["operator_message"] = (
                "NO SCHEDULE. %d of %d hours were NEVER REQUESTED -- %s. %s A schedule is only "
                "published over hours the agent actually perceived: presenting one here would mean "
                "scheduling hours it never looked at, and the mechanical fallback would read as a "
                "decision rather than an absence. Re-run with the budget those %d calls need."
                % (n_not_attempted, hours,
                   "; ".join(reasons) or "this run was not permitted to spend",
                   ("%d hour(s) were available from cache and are listed below, unscheduled."
                    % n_have) if n_have else "",
                   n_not_attempted))
            out["hours_available_from_cache"] = n_have
            return out
        elif cls == ["fixture_wrong_metro"]:
            out["status"] = "fixture_mismatch"
            out["operator_message"] = recs[0].get("error", "the replay fixture is another "
                                                          "metro's field")
        else:
            worst = next((r for r in recs if r.get("class") not in ("not_attempted",)), recs[0])
            out["status"] = "vendor_unavailable"
            out["operator_message"] = (
                vendor_sentence(worst.get("class", "unknown"), worst)
                + " No hour of the horizon returned a field, so THERE IS NO SCHEDULE. Nothing here "
                  "is interpolated, carried forward from a previous run, or substituted from a "
                  "saved field: an agent that invents its perception is worse than one that stops.")
        return out

    # ---- SOLVE + BOUND + DECIDE -------------------------------------------------
    if on_progress:
        on_progress({"stage": "solve", "note": "loading this site's 576-solve rise table"})
    tab, refused, tmeta = A.rise_table(cfg["bank_mode"])
    brg = np.array([h["bearing_deg"] for h in nws["hours"]], dtype=float)
    spd = np.array([h["speed_ms"] for h in nws["hours"]], dtype=float)
    rise = A.lookup_rise(tab, brg, spd)
    refused_flags = [int(round(b / A.STEP_DEG)) % len(A.BEARINGS) in refused for b in brg]

    margin, mprov = measured_margin(trace, site, horizon_h=hours)
    out["margin_provenance"] = mprov
    if margin is None:
        out["status"] = "no_calibration"
        out["operator_message"] = ("No measured FortyGuard margin exists for this site, so no "
                                   "bound can be published and no schedule is emitted.")
        return out

    # EVERY PER-HOUR ARRAY MUST BE THE SAME LENGTH AS THE HORIZON. numpy broadcasting will happily
    # turn a length mismatch into plausible-looking numbers rather than an error, so it is checked
    # rather than assumed -- see the note above the horizon block.
    if not (len(temps) == len(recs) == len(nws["hours"]) == hours):
        raise SystemExit("horizon length mismatch: %d hours, %d temps, %d recs, %d nws rows"
                         % (hours, len(temps), len(recs), len(nws["hours"])))
    amb = np.array([t if t is not None else np.nan for t in temps], dtype=float)
    bound = amb + rise + float(margin)
    dewp = np.array([h["dewpoint_c"] if h["dewpoint_c"] is not None else np.nan
                     for h in nws["hours"]], dtype=float)

    # Both gates, and a refused bearing is NOT a free-cooling hour: the solver declining to answer
    # is not permission. NaN (a missing hour) is likewise never safe.
    # BOTH GATES, and three separate reasons an hour is NOT free-cooling. Kept as named arrays
    # rather than one expression, because each one is reported to the operator separately and a
    # reader has to be able to see which gate bit.
    # ---- E2: PREFER FORTYGUARD'S OWN HUMIDITY, AND SAY WHOSE NUMBER DECIDED EACH HOUR ----------
    # The humidity gate ran on NWS because `env_params` returns no dry-bulb and `heatmap` returns no
    # environmentals, so one place and time needed two endpoints. That is a cost argument, not a
    # capability one -- and it left the vendor whose data this product is built on supplying exactly
    # one variable. FortyGuard's wet-bulb is used where it exists, NWS remains the fallback, and the
    # SOURCE IS RECORDED PER HOUR so a reader can never be misled about whose measurement gated an
    # hour. Falling back silently would be worse than not falling back at all.
    #
    # ⚠ WET-BULB IS COMPARED AGAINST THE SAME LIMIT AS DEW POINT, and that is deliberate but not
    # free of consequence: for unsaturated air wet-bulb sits ABOVE dew point, so this gate is
    # STRICTER than the NWS one, never looser. Erring strict is the safe direction for a gate whose
    # job is to keep moist air out, and it is stated rather than buried.
    tz_off = int(round((start_local.utcoffset().total_seconds() if start_local.utcoffset()
                        else 0) / 3600.0))
    env_src = ["nws"] * hours
    if fg_env:
        # the APPLIED lag, not the measured one -- see `env_alignment_lag`: a shift is only
        # acted on when the evidence carries it, and is otherwise reported unresolved.
        lag = ((fg_env_meta.get("alignment") or {}).get("applied_lag_hours")) or 0
        for i in range(hours):
            # 🔴 IN A SEQUENCE REPLAY, INDEX BY THE HOUR THAT WAS REPLAYED, not by today's clock.
            # The temperature for hour i came from a saved 09:00 / 10:00 / 11:00 window, so its
            # humidity must come from the same hour of the same day. Using today's hour here is
            # what made the two halves of a replay disagree about what time it was.
            hh = (replay_hours[i] if replay_hours and i < len(replay_hours)
                  else (start_utc + timedelta(hours=i + tz_off + lag)).hour)
            wb = dewpoint_from_env(fg_env.get(hh) or {})
            if wb is not None:
                dewp[i] = wb
                # "fortyguard-saved" vs "fortyguard-live" -- both are their measurement, and a
                # reader is entitled to know which one gated the hour in front of them.
                env_src[i] = "fortyguard-" + (fg_env_meta.get("mode") or "live")
    out["humidity_source_per_hour"] = env_src
    out["humidity_source_summary"] = {
        "fortyguard_hours": sum(1 for x in env_src if x.startswith("fortyguard")),
        "fortyguard_mode": fg_env_meta.get("mode"),
        "nws_hours": sum(1 for x in env_src if x == "nws"),
        "gate_quantity": "wet-bulb where FortyGuard supplied it, dew point where NWS did",
        "note": "wet-bulb >= dew point in unsaturated air, so a FortyGuard-gated hour is held to a "
                "STRICTER test than an NWS-gated one, never a looser one"}

    # ---- E2: THE CONTAMINATION GATE, on FortyGuard's own air-quality indices -------------------
    # LBNL put particle counters in eight real data centres and found contamination is a documented
    # reason operators refuse free cooling -- it is this project's commercial thesis. FortyGuard
    # sells six air-quality indices and the live agent ignored every one of them, so the argument
    # was cited and never acted on. It is acted on now.
    # ⚠ The index carries NO DOCUMENTED UNITS (findings 9.3), which is why the limit is swept in the
    # five-year model rather than claimed. Here it is applied only if the caller sets one.
    aq_lim = cfg.get("aq_limit_idx")
    aq_vals = np.full(hours, np.nan)
    if fg_env:
        # the APPLIED lag, not the measured one -- see `env_alignment_lag`: a shift is only
        # acted on when the evidence carries it, and is otherwise reported unresolved.
        lag = ((fg_env_meta.get("alignment") or {}).get("applied_lag_hours")) or 0
        for i in range(hours):
            hh = (replay_hours[i] if replay_hours and i < len(replay_hours)
                  else (start_utc + timedelta(hours=i + tz_off + lag)).hour)
            v = (fg_env.get(hh) or {}).get("air_quality_pm2p5:idx")
            if isinstance(v, (int, float)):
                aq_vals[i] = float(v)
    gate_aq = (np.ones(hours, dtype=bool) if aq_lim is None
               else (aq_vals <= float(aq_lim)) & ~np.isnan(aq_vals))
    out["air_quality"] = {
        "limit_idx": aq_lim,
        "source": "FortyGuard env_params air_quality_pm2p5:idx" if fg_env else "not available",
        "hours_with_a_value": int(np.sum(~np.isnan(aq_vals))),
        "hours_blocked": int(np.sum(~gate_aq)) if aq_lim is not None else 0,
        "units_note": "the :idx fields carry no documented units or scale (findings 9.3), so a "
                      "limit is only applied when the caller sets one and is never assumed"}

    dp_lim = cfg.get("dewpoint_limit_c")
    gate_dry = bound <= cfg["limit_c"]
    # NaN <= 15.0 is already False, so a missing dew point closes the gate on its own. The explicit
    # `known` term is kept anyway: relying on a NaN comparison for a SAFETY decision is the kind of
    # thing that silently inverts when someone swaps a comparison operator.
    dp_known = np.ones(hours, dtype=bool) if dp_lim is None else ~np.isnan(dewp)
    gate_dp = np.ones(hours, dtype=bool) if dp_lim is None else (dewp <= dp_lim)
    refused_arr = np.array(refused_flags, dtype=bool)
    bound_known = ~np.isnan(bound)
    # A REFUSED BEARING IS NOT PERMISSION. The solver declining to answer is not a yes, and a
    # missing hour is not a yes either.
    # `gate_aq` joins the conjunction: any gate saying no means no, which is how a real
    # economizer works and why they are kept as named arrays rather than one expression.
    safe = gate_dry & gate_dp & dp_known & gate_aq & bound_known & ~refused_arr

    # A.plan returns (modes, free_hours, switches). Unpacking all three and CHECKING the two
    # counts against a recount is free, and it is the kind of check that catches a DP change
    # silently altering what it reports: the first version of this line bound the whole tuple to
    # `modes`, which surfaced as `TypeError: cannot use 'list' as a dict key` two stages later.
    if on_progress:
        on_progress({"stage": "decide", "note": "scheduling under the switch budget and dwell limit"})
    modes, plan_free_h, plan_switches = A.plan(
        [bool(x) for x in safe], cfg["switch_budget"], cfg["min_dwell_h"], start_mode=A.MODE_MECH)
    recount_free = int(sum(1 for m in modes if m == A.MODE_FREE))
    recount_switch = int(sum(1 for i in range(1, len(modes)) if modes[i] != modes[i - 1]))
    if recount_free != plan_free_h:
        raise SystemExit("plan() disagrees with its own schedule: reports %d free hours, the "
                         "schedule contains %d" % (plan_free_h, recount_free))
    hour_labels = [(start_local + timedelta(hours=i)).strftime("%Y-%m-%d %H:00") for i in range(hours)]
    cmds = A.bms_commands(modes, hour_labels, list(bound), cfg["limit_c"], list(rise),
                          refused_flags, mprov)

    n_missing = int(hours - np.count_nonzero(bound_known))
    out.update({
        # PARTIAL IS ITS OWN STATUS. "ok" over 12 hours when 8 of them have no forecast would be a
        # claim the run cannot support, and the reader has to be told without reading the table.
        "status": ("ok_replay" if replay else
                   ("ok_partial" if n_missing else "ok")),
        "device": tmeta.get("device"),
        "hours": [{
            "hour_site_local": hour_labels[i],
            # MEASURED, not the loop index. `i + 1` claimed a 1-hour lead for a window that could
            # be five minutes away, on a product whose thesis is about lead time and whose margin's
            # calibration domain is expressed in it.
            "lead_h": recs[i].get("lead_h"),
            "hour_index": i + 1,
            "no_data_reason": recs[i].get("no_data_reason") or (
                None if temps[i] is not None else
                "vendor returned no field (%s)" % recs[i].get("class")),
            "ambient_c": None if np.isnan(amb[i]) else round(float(amb[i]), 4),
            "bearing_deg": None if np.isnan(brg[i]) else float(brg[i]),
            "speed_ms": None if np.isnan(spd[i]) else round(float(spd[i]), 3),
            "rise_c": round(float(rise[i]), 4),
            "margin_c": round(float(margin), 4),
            "bound_c": None if np.isnan(bound[i]) else round(float(bound[i]), 4),
            "dewpoint_c": None if np.isnan(dewp[i]) else round(float(dewp[i]), 2),
            "bearing_refused": bool(refused_flags[i]),
            "gate_dry_ok": bool(gate_dry[i]),
            "gate_dewpoint_ok": bool(gate_dp[i]),
            "free_cooling": bool(modes[i] == A.MODE_FREE),
        } for i in range(hours)],
        # 🔴 AN HOUR WITH NO FORECAST WAS NOT "BLOCKED BY TEMPERATURE", AND SAYING SO IS A
        # LIE ABOUT WHY THE AGENT REFUSED. `bound` is NaN for a missing hour, and `NaN <= limit` is
        # False, so it fell into the temperature bucket and inflated it. The vendor is intermittent
        # -- a 12-hour run today returned four hours and then went empty -- so partial data is the
        # NORMAL case, not an edge one. Missing hours are counted separately, and excluded from
        # both gate counts, which are now reported only over hours that HAVE a forecast.
        "summary": {
            "free_cooling_hours": recount_free,
            "of_hours": hours,
            "hours_with_a_forecast": int(np.count_nonzero(bound_known)),
            "hours_with_NO_forecast": int(hours - np.count_nonzero(bound_known)),
            "mode_changes": recount_switch,
            "plan_reported_switches": plan_switches,
            "hours_refused_by_solver": int(sum(refused_flags)),
            "hours_blocked_by_dewpoint": int(sum(1 for i in range(hours)
                                                 if bound_known[i] and not gate_dp[i])),
            "hours_blocked_by_temperature": int(sum(1 for i in range(hours)
                                                    if bound_known[i] and not gate_dry[i])),
            "peak_bound_c": None if np.all(np.isnan(bound)) else round(float(np.nanmax(bound)), 4),
        },
        "commands": cmds,
    })
    if n_missing and not replay:
        out["operator_message"] = (
            "PARTIAL HORIZON: %d of %d hours returned a field, %d did not (%s). The hours with no "
            "forecast are scheduled MECHANICAL -- chillers on is the safe default -- and are NOT "
            "counted as blocked by temperature or humidity, because nothing was measured about "
            "them. Only the %d answered hours carry a bound."
            % (hours - n_missing, hours, n_missing,
               ", ".join(sorted({r.get("class") for r in recs if r.get("class") != "ok"})),
               hours - n_missing))
    if replay:
        # The banner has to describe which of the two replay shapes actually ran, and it used to
        # assert the flat one unconditionally -- "reused for every hour of the horizon" -- which
        # became false the moment a sequence replay existed. It also crashed on the list.
        seq = out.get("replay_sequence") or {}
        if seq.get("windows", 0) > 1:
            out["NOT_LIVE"] = (
                "REPLAY VERIFICATION. The ambient trajectory is %d CONSECUTIVE saved FortyGuard "
                "windows from %s (%s site-local), so the temperature varies hour to hour exactly as "
                "it did that day -- but these are NOT the hours the schedule names, and it is not a "
                "forecast. Humidity and air quality are FortyGuard's, from the same date and the "
                "same hours. WIND IS LIVE, because no saved wind exists for a past date. Nothing in "
                "the demo may present this as a live run."
                % (seq["windows"], seq.get("date"),
                   ", ".join("%02d:00" % h for h in (seq.get("hours_site_local") or []))))
        else:
            out["NOT_LIVE"] = (
                "REPLAY VERIFICATION. The ambient trajectory came from a SAVED FortyGuard response "
                "(%s), reused for every hour of the horizon, so the schedule below proves the "
                "solve/bound/decide/act chain and is NOT a forecast of the hours it names. Wind is "
                "live. Nothing in the demo may present this as a live run."
                % os.path.basename(replay[0] if isinstance(replay, list) else replay))
    return out


def _append_spend_ledger(out, recs):
    """Record this run's meter readings where `testing/api_usage_ledger.py` will find them.

    🔴 WITHOUT THIS, LIVE SPEND IS INVISIBLE TO THE PROJECT'S OWN SPEND LEDGER. The ledger
    walks `testing/results/` for saved `credits_before`/`credits_after` pairs, and `live.py` writes
    to `demo/`, so the first 12-hour run spent **46,420 credits that no audited figure knew about**.
    API-USAGE.md would have understated usage by 85 % while `audit.py` check 9 reported it green,
    because the check verifies that the documents match the ledger -- not that the ledger sees
    everything. A ledger with a blind spot is worse than no ledger, because it is trusted.

    APPEND, never overwrite: gotcha #100 was caused by a single-slot meter field being overwritten
    by a later unbilled call, which silently dropped three calls from the total. Each run is its own
    entry here.
    """
    if not out.get("spend") or not out["spend"].get("credits_before"):
        return                                    # a dry run or a replay: nothing was billed
    path = os.path.join(TESTING, "results", "live_spend.json")
    try:
        doc = json.load(open(path, encoding="utf-8"))
        if not isinstance(doc, dict) or "runs" not in doc:
            raise ValueError("unexpected shape")
    except (OSError, ValueError):
        doc = {"purpose": "every paid live.py run, so testing/api_usage_ledger.py sees live spend",
               "runs": []}
    sp = out["spend"]
    doc["runs"].append({
        "test": "live.py %s %s" % (out.get("metro"), out.get("first_hour_site_local")),
        "utc": out.get("utc_now"),
        "metro": out.get("metro"),
        "horizon_h": out.get("horizon_h"),
        # NO `status` FIELD. This append happens as soon as the SPEND is known -- deliberately, so
        # it runs whatever early return follows -- and at that moment the status does not exist yet.
        # The first version recorded it anyway and wrote `null` on every run: a field that is always
        # null is worse than an absent one, because a reader assumes it means something.
        #
        # ⚠ KILLING THE SERVER MID-RUN LOSES THAT RUN'S PER-CALL RECORD. The process dies before
        # this append. The TOTAL is still exact, because the meter is the authority and the ledger
        # derives spend from `issued - lowest reading ever seen` rather than from summing these
        # entries -- which is the whole reason it was built that way. Only the per-call attribution
        # is lost, and it degrades into the "unattributable" bucket where it belongs.
        "credits_before": sp["credits_before"],
        "credits_after": sp["credits_after"],
        "api_calls_made": sp["calls_attempted"],
        "cache_hits": sp["cache_hits"],
        # What each call BOUGHT, so the ledger can classify without guessing.
        # KEEP THE FAILURE DETAIL. The first version stored only class/tiles/activity_id, so when
        # a window came back `submit_rejected` the HTTP status and body -- the only fields that
        # explain WHY -- were already gone by the time anyone asked. A record of a failure that
        # omits the reason is barely a record.
        # 🔴 AND KEEP THE WINDOW THAT WAS ASKED FOR. Added 2026-08-21, and it is the third time this
        # record has been widened after the missing field was the one that mattered.
        # FortyGuard told another entrant that a window past "the last hour currently in the
        # catalog" comes back `completed` with an empty grid -- the exact signature this project has
        # spent four days calling a vendor outage. Testing that against our own history needs one
        # thing per call: WHICH HOUR WAS REQUESTED. It was not recorded. Only the successful windows
        # were recoverable at all, from `data/live_cache/` filenames, and the failures -- the ones
        # the question is about -- left no trace of their requested hour anywhere.
        # `cache_hits` also means the `windows` array is NOT a consecutive run of hours from the
        # first, so it cannot be reconstructed by counting. Record it instead of inferring it.
        "windows": [{k: v for k, v in
                     # SITE-LOCAL plus the LEAD, because together they pin the request exactly and
                     # both are plain strings/floats. The `_start_utc` datetime that also sits in
                     # the payload block is deliberately not written: `json.dump` here has no
                     # `default=`, so a datetime would raise inside the one function whose job is to
                     # make sure spend never goes unrecorded.
                     {"window_start_site_local":
                          ((r.get("window") or {}).get("start_date", "") + " "
                           + (r.get("window") or {}).get("start_time", "")).strip() or None,
                      "lead_h_at_request": r.get("lead_h"),
                      "class": r.get("class"), "tiles": r.get("tiles"),
                      "activity_id": r.get("activity_id"),
                      "submit_http": r.get("submit_http"),
                      "submit_error_body": (r.get("submit_error_body") or None),
                      "submit_exception": r.get("submit_exception"),
                      "submit_retried_after": r.get("submit_retried_after"),
                      "statuses_seen": r.get("statuses_seen"),
                      "polls": r.get("polls"),
                      "elapsed_s": r.get("elapsed_s")}.items() if v is not None}
                    for r in recs if r.get("source") == "live"],
    })
    json.dump(doc, open(path, "w", encoding="utf-8"), indent=1, default=str, allow_nan=False)


# ============================================================================
# 6. OFFLINE VERIFICATION -- the whole chain, zero API calls
# ============================================================================
def verify_live_offline():
    """Prove the live chain's arithmetic against SAVED data, with no network at all.

    This is what lets `run_all.py` stay offline and deterministic while still covering the live
    path. It checks the parts that are live-INDEPENDENT: the RLE expansion, the vendor classifier,
    the gate logic and the margin provenance. It cannot check that FortyGuard answers -- nothing
    offline can -- and it does not pretend to.
    """
    fails = []

    def ck(name, ok, detail=""):
        print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            fails.append(name)

    print("\nLIVE CHAIN, OFFLINE SELF-TEST")
    ck("ISO duration PT1H -> 1 h", _parse_duration_h("PT1H") == 1)
    ck("ISO duration PT6H -> 6 h", _parse_duration_h("PT6H") == 6)
    ck("ISO duration P1DT6H -> 30 h", _parse_duration_h("P1DT6H") == 30)
    ck("ISO duration garbage -> 1 h, never 0", _parse_duration_h("nonsense") == 1)

    ck("classifier: ok", classify_vendor(
        {"submit_http": 200, "activity_id": "a", "tiles": 17862}) == "ok")
    ck("classifier: stall is not a failure", classify_vendor(
        {"submit_http": 200, "activity_id": "a", "tiles": 0,
         "statuses_seen": ["processing"]}) == "stalled_in_processing")
    ck("classifier: completed-but-empty is its own case", classify_vendor(
        {"submit_http": 200, "activity_id": "a", "tiles": 0,
         "terminal_status": "completed"}) == "completed_but_empty")
    ck("classifier: terminal failed", classify_vendor(
        {"submit_http": 200, "activity_id": "a", "tiles": 0,
         "terminal_status": "failed"}) == "terminal_failed")
    ck("classifier: submit rejection", classify_vendor(
        {"submit_http": 429}) == "submit_rejected")

    # The window must be expressed in the AOI's own local time and never converted (gotcha #1).
    w = window_fields(datetime(2026, 8, 20, 14, 0), 1)
    ck("window is local-time, 1 h, filter_type 2",
       w == {"start_date": "2026-08-20", "start_time": "14:00", "end_time": "15:00",
             "filter_type": 2}, str(w))

    tr = json.load(open(M.demo_path("trace.json", M.DEFAULT_METRO), encoding="utf-8"))
    margin, prov = measured_margin(tr, {"key": "ashburn"})
    ck("margin comes from the MEASURED FortyGuard residuals", margin is not None,
       "%.6f C from n=%s pairs" % (margin, prov["n_calibration_pairs"]))
    ck("margin is flagged as clamped below its nominal coverage",
       prov["clamped_to_attainable"] is True and prov["attainable_coverage_ceiling"] < prov[
           "nominal_coverage"],
       "attainable %.2f < nominal %.2f" % (prov["attainable_coverage_ceiling"],
                                           prov["nominal_coverage"]))
    ck("margin carries the extrapolation warning",
       "OUTSIDE its calibration domain" in prov["EXTRAPOLATION_WARNING"])
    ck("the pre-registration verdict travels with the margin",
       prov["prereg_verdict"].startswith("FAIL"))

    # A borrowed calibration must say so, and must name the site it came from.
    sites = json.load(open(M.demo_path("sites.json", M.DEFAULT_METRO), encoding="utf-8"))["sites"]
    chi = next((s for s in sites if s["key"] == "chicago"), None)
    if chi:
        tr_c = json.load(open(M.demo_path("trace.json", "chicago"), encoding="utf-8"))
        _, pc = measured_margin(tr_c, chi)
        ck("a site with no pairs of its own reports a BORROWED bound",
           pc["site_owns_this_calibration"] is False and pc["borrowed_from"] == "ashburn")

    # THE WRONG-METRO FIXTURE GUARD. Dulles is the case that matters: it is only ~4 km from
    # Ashburn's AOI, close enough that `nearest_tile` returns a plausible-looking neighbour instead
    # of an obvious absurdity. A 926 km miss announces itself; a 4 km one does not.
    fx = os.path.join(TESTING, "results", "fixtures", "n26_f_2026-08-16.json")
    if os.path.exists(fx):
        tr_a = json.load(open(M.demo_path("trace.json", M.DEFAULT_METRO), encoding="utf-8"))
        ca = tr_a["site"]["centre"]
        v, rec = fetch_window(None, None, {"start_date": "x", "start_time": "00:00",
                                           "end_time": "01:00", "filter_type": 2},
                              M.DEFAULT_METRO, False, (ca[0], ca[1]), replay=fx)
        ck("replay accepts its OWN metro's fixture", v is not None and rec["class"] == "ok",
           "tile %.1f m from the site centre" % rec.get("tile_dist_m", -1))
        for other in ("chicago", "dulles"):
            try:
                tr_o = json.load(open(M.demo_path("trace.json", other), encoding="utf-8"))
            except OSError:
                continue
            co = tr_o["site"]["centre"]
            v2, rec2 = fetch_window(None, None, {"start_date": "x", "start_time": "00:00",
                                                 "end_time": "01:00", "filter_type": 2},
                                    other, False, (co[0], co[1]), replay=fx)
            ck("replay REFUSES another metro's fixture (%s)" % other,
               v2 is None and rec2["class"] == "fixture_wrong_metro",
               "%.0f km away" % (rec2.get("tile_dist_m", 0) / 1000.0))

    # ---- THE LEAD MUST BE MEASURED, NOT INDEXED. This is the check for the bug that labelled a
    # window five minutes away as "lead +1 h".
    from datetime import datetime as _dt
    n0 = _dt(2026, 8, 20, 9, 55)
    ck("first window is the next whole hour", first_window_start(n0) == _dt(2026, 8, 20, 10, 0),
       str(first_window_start(n0)))
    ck("a window 5 minutes away reports a 0.08 h lead, not 1 h",
       abs(lead_hours_for(n0, first_window_start(n0)) - 5 / 60.0) < 1e-9,
       "%.4f h" % lead_hours_for(n0, first_window_start(n0)))
    n1 = _dt(2026, 8, 20, 10, 0)
    ck("on the hour, the first window is the NEXT hour (never zero lead)",
       first_window_start(n1) == _dt(2026, 8, 20, 11, 0)
       and abs(lead_hours_for(n1, first_window_start(n1)) - 1.0) < 1e-9)
    _, pw = horizon_windows(M.DEFAULT_METRO, 4, n0)
    ck("horizon leads are strictly increasing and start below 1 h",
       [p["lead_h"] for p in pw] == sorted(p["lead_h"] for p in pw) and pw[0]["lead_h"] < 1.0,
       str([p["lead_h"] for p in pw]))
    ck("horizon_windows reports cache state per window",
       all("cached" in p for p in pw))

    # ---- A NEVER-REQUESTED WINDOW MUST NOT BECOME A SCHEDULED HOUR. The regression test for the
    # worst output this project has produced: 3 cached hours + 9 unrequested ones published as a
    # live decision, with the 9 scheduled MECHANICAL as though the agent had looked.
    rec_na = {"source": "would-call", "class": "not_attempted"}
    ck("an unrequested window classifies as not_attempted, never as vendor failure",
       classify_vendor(rec_na) != "ok" and rec_na["class"] == "not_attempted")

    # 🔴 THE HORIZON IS SIZED FROM THE MEASURED CACHE STATE, so an unlooked-at window is inside it
    # BY CONSTRUCTION. A fixed `hours=6` exercised this guard only while fewer than six windows
    # happened to be cached. On 2026-08-23 the vendor recovered and twelve consecutive windows
    # landed in the cache, so the six-hour horizon became fully cached, `ok` was the CORRECT answer,
    # and the regression test for the worst output this project has produced FAILED AGAINST WORKING
    # CODE. That is gotcha #125 -- a test whose result depends on the clock -- recurring in the two
    # branches the zero-budget test below had already been hardened against, three screens away.
    # Deriving the horizon from `horizon_windows()` makes the guard fire on every run instead of
    # only when the cache is thin, which is strictly stronger than what it replaces.
    _site = next((s for s in json.load(open(M.demo_path("sites.json", M.DEFAULT_METRO),
                                            encoding="utf-8"))["sites"]
                  if s["key"] == M.DEFAULT_METRO), None) or {}
    _now_p = site_local_now(_site.get("tz") or "America/New_York")
    _, _probe = horizon_windows(M.DEFAULT_METRO, SELFTEST_PROBE_H, _now_p)
    _n_cached = sum(1 for p in _probe if p["cached"])
    _first_uncached = next((i for i, p in enumerate(_probe) if not p["cached"]), None)
    # If this ever fails, the cache covers a whole day ahead and the guard cannot be exercised
    # offline. Report that rather than skipping: a check that skips reports PASS for a path it
    # never ran.
    ck("the self-test found an uncached window to exercise the #107 guard with",
       _first_uncached is not None,
       "%d of %d probe windows cached" % (_n_cached, len(_probe)))
    _h = (_first_uncached + 1) if _first_uncached is not None else SELFTEST_PROBE_H
    if _first_uncached is not None:
        out = live_run(metro=M.DEFAULT_METRO, hours=_h, allow_paid=False, verbose=False,
                       cfg={"limit_c": 27.0})
        ck("a run with unrequested windows emits NO schedule",
           out.get("status") in ("dryrun", "incomplete_not_attempted")
           and "hours" not in out and "commands" not in out,
           "status=%s over a %d h horizon, %d cached" % (out.get("status"), _h, _first_uncached))
        ck("...and says how many hours it never looked at",
           "NEVER REQUESTED" in (out.get("operator_message") or "")
           or "DRY RUN" in (out.get("operator_message") or ""),
           (out.get("operator_message") or "")[:60])

    # ---- A BUDGET SHORTENS THE HORIZON RATHER THAN LEAVING HOLES IN IT. Regression test for the
    # blunt refusal: with a budget smaller than the horizon needs, the run must still produce a
    # COMPLETE decision over fewer hours, with no `not_attempted` window inside it.
    # A ZERO BUDGET EITHER TRUNCATES TO THE CACHED PREFIX OR REPORTS THAT IT CANNOT COVER AN HOUR.
    # 🔴 BOTH BRANCHES ARE ASSERTED, because which one fires depends on whether the FIRST window of
    # the horizon happens to be in the cache -- and the horizon SLIDES with the clock. The first
    # version of this test assumed a cached first hour and started failing an hour later. A test
    # whose result depends on the time of day is worse than no test: it trains you to ignore it.
    # `_h` is sized so its LAST window is uncached, so with a zero budget the branch that fires is
    # decided by whether the FIRST window is cached -- which is exactly the fork below, and now a
    # measured fact rather than a coin toss.
    out2 = live_run(metro=M.DEFAULT_METRO, hours=_h, allow_paid=False, verbose=False,
                    cfg={"limit_c": 27.0}, max_calls=0)
    st2 = out2.get("status")
    if st2 == "no_call_budget":
        ck("a zero budget with nothing cached emits NO schedule and says why",
           "hours" not in out2 and "commands" not in out2
           and "NO SCHEDULE" in (out2.get("operator_message") or ""),
           "status=%s" % st2)
    else:
        tr = out2.get("horizon_truncated")
        ck("a zero budget truncates the horizon to the cached prefix",
           tr is not None and tr["requested_hours"] == _h and 0 < tr["covered_hours"] <= _h,
           "covered %s of %s" % ((tr or {}).get("covered_hours"),
                                 (tr or {}).get("requested_hours")))
        # THE SUMMARY MUST PARTITION THE HORIZON. A negative count is what exposed the broadcasting
        # bug -- a length-1 ambient against a length-6 rise gave `hours_with_NO_forecast: -5` while
        # every individual figure still looked plausible. Checked for sign AND for closure.
        s2 = out2.get("summary") or {}
        ck("summary counts are non-negative and partition the horizon",
           all(v >= 0 for k, v in s2.items() if isinstance(v, int))
           and s2.get("hours_with_a_forecast", 0) + s2.get("hours_with_NO_forecast", 0)
               == s2.get("of_hours"),
           "%s with + %s without = %s" % (s2.get("hours_with_a_forecast"),
                                          s2.get("hours_with_NO_forecast"), s2.get("of_hours")))
        ck("every per-hour array matched the horizon length (no broadcasting)",
           len(out2.get("hours") or []) == s2.get("of_hours"),
           "%d rows for %s hours" % (len(out2.get("hours") or []), s2.get("of_hours")))
        ck("...and no window inside the shortened horizon is unlooked-at",
           not any((h.get("no_data_reason") or "").startswith("this run was not permitted")
                   for h in (out2.get("hours") or [])),
           "status=%s" % st2)

    # ---- E2: THE ENVIRONMENTAL GATES, offline ------------------------------------------------
    # The alignment logic is the dangerous part and it is the part no live run would expose: a
    # one-hour shift produces a schedule that is entirely plausible and quietly wrong, which is the
    # nine-hour bug's whole family. So it is fed a synthetic day where the true lag is KNOWN.
    from datetime import timezone as _tzc
    base = _dt(2026, 8, 22, 12, 0, tzinfo=_tzc.utc)          # 08:00 EDT, so tz_off = -4
    # A dew-point series NWS would report, and a FortyGuard array holding the same shape shifted by
    # a known number of hours. If the detector cannot recover that shift, it cannot be trusted with
    # the real thing.
    shape = {h: 10.0 + 4.0 * math.sin((h - 4) * math.pi / 12.0) for h in range(24)}
    nws_rows = [{"dewpoint_c": shape[(base + timedelta(hours=j - 4)).hour]} for j in range(12)]
    for true_lag in (0, 1, -1):
        fg = {h: {"wet_bulb_temperature_celsius": shape[(h - true_lag) % 24]} for h in range(24)}
        got = env_alignment_lag(fg, nws_rows, base, -4)
        ck("alignment detector recovers a known %+d h shift" % true_lag,
           got.get("lag_hours") == true_lag,
           "measured %s over %s pairs" % (got.get("lag_hours"), got.get("n_pairs")))
    ck("alignment reports UNMEASURABLE rather than 0 when there is no overlap",
       env_alignment_lag({}, nws_rows, base, -4).get("lag_hours") is None,
       "returns None and says why, instead of a confident zero")

    # MEASURING A LAG IS NOT THE SAME DECISION AS ACTING ON ONE. The real first run picked -1 from
    # four overlapping hours and applied it; these pin that a thin result is reported and NOT used.
    thin_nws = nws_rows[:4]
    thin_fg = {h: {"wet_bulb_temperature_celsius": shape[(h + 1) % 24]} for h in range(24)}
    thin = env_alignment_lag(thin_fg, thin_nws, base, -4)
    ck("a lag measured from too few hours is reported but NOT applied",
       thin.get("lag_hours") is not None and thin.get("applied_lag_hours") == 0
       and "unresolved" in thin,
       "measured %+d over %d pairs, applied 0" % (thin.get("lag_hours") or 0, thin.get("n_pairs")))
    # ⚠ `shape[(h - L) % 24]` constructs a lag of +L -- the same convention as the loop above. The
    # first version of this line built +1 and asserted -1, so it failed against correct code. Reuse
    # the construction rather than restating it.
    for true_lag in (1, -1):
        strong = env_alignment_lag({h: {"wet_bulb_temperature_celsius": shape[(h - true_lag) % 24]}
                                    for h in range(24)}, nws_rows, base, -4)
        ck("...and a well-evidenced %+d h lag IS applied" % true_lag,
           strong.get("applied_lag_hours") == true_lag,
           "12 pairs, margin %.3f C over as-labelled"
           % ((strong.get("evidence") or {}).get("margin_vs_as_labelled_c") or 0.0))
    ck("every candidate lag's score is published, not just the winner",
       set((env_alignment_lag(thin_fg, nws_rows, base, -4).get("candidates_c") or {}))
       == {"-1", "0", "1"},
       "a reader can see the separation rather than trust the argmax")

    # The gate must never silently borrow: an hour gated on NWS and an hour gated on FortyGuard are
    # different claims and the output has to say which.
    ck("a run with no env_params still gates, on NWS, and says so",
       dewpoint_from_env({}) is None and dewpoint_from_env(
           {"wet_bulb_temperature_celsius": 18.5}) == 18.5,
       "missing -> None (falls back), present -> the value")
    ck("the refused fields are never read as a measurement",
       dewpoint_from_env({"heat_index_celsius": 31.0, "temperature": 25.0}) is None,
       "heat_index and the echoed temperature yield nothing (findings 1.1, 1.7)")
    # A SITE MUST NOT REPLAY ANOTHER SITE'S AIR. Chicago's first replay picked Ashburn's response
    # because the scan matched on date alone -- and reported `same_day: True` while doing it.
    ash_ll, chi_ll = M.site_centre("ashburn"), M.site_centre("chicago")
    _a, a_meta = saved_fortyguard_env("2026-08-20", ash_ll, verbose=False)
    _c, c_meta = saved_fortyguard_env("2026-08-20", chi_ll, verbose=False)
    ck("each site's replay picks its OWN saved environmental response",
       a_meta.get("fixture") and c_meta.get("fixture")
       and a_meta["fixture"] != c_meta["fixture"],
       "ashburn=%s chicago=%s" % (a_meta.get("fixture"), c_meta.get("fixture")))
    _n, n_meta = saved_fortyguard_env("2026-08-20", (10.0, 10.0), verbose=False)
    ck("a site with no environmental response of its own falls back, never borrows",
       _n is None and "another site" in (n_meta.get("why") or ""),
       "returns nothing and says why")

    # THE SEQUENCE REPLAY. A flat trajectory proves the chain executes and nothing about a day, and
    # the two halves of the same replay disagreed about time: temperature frozen, humidity hourly.
    _cache = os.path.join(M.ROOT, "data", "live_cache", "ashburn")
    _first = os.path.join(_cache, "2026-08-20_0900-1000_g60_tcm.json")
    if os.path.exists(_first):
        paths, hrs, day = replay_sequence(_first, 12)
        ck("a replay walks the CONSECUTIVE saved windows, not one repeated",
           paths and len(paths) > 1 and hrs == sorted(hrs) and day == "2026-08-20",
           "%d windows on %s at %s" % (len(paths or []), day,
                                       ", ".join("%02d:00" % h for h in (hrs or []))))
        ck("...and it truncates to what was SAVED rather than inventing hours",
           len(replay_sequence(_first, 2)[0]) == 2,
           "asked for 2 of 4 available -> 2")
        ck("a lone fixture with no siblings still replays, flat, without pretending otherwise",
           len(replay_sequence(os.path.join(M.ROOT, "data", "live_cache", "chicago",
                                            "2026-08-20_1100-1200_g60_tcm.json"), 12)[0]) == 1,
           "chicago has one saved window, so the sequence is one")

    sv, sv_meta = saved_fortyguard_env("2026-08-22", verbose=False)
    ck("a REPLAY gets FortyGuard humidity from a SAVED response, not from NWS and not by spending",
       sv is not None and sv_meta["credits"] == 0 and sv_meta["n_fields"] >= 10
       and dewpoint_from_env(sv.get(sorted(sv)[0])) is not None,
       "%s: %d fields x %d hours, 0 credits" % (sv_meta.get("fixture"), sv_meta.get("n_fields", 0),
                                                sv_meta.get("n_hours", 0)))
    ck("...and it says so when the saved day is not the requested one",
       ("note" in sv_meta) == (sv_meta.get("same_day") is False),
       "same_day=%s" % sv_meta.get("same_day"))
    m_na = fortyguard_env(None, 39.0, -77.4, "2026-08-22", allow_paid=False, verbose=False)[1]
    ck("an unauthorised env fetch is not_attempted and spends nothing",
       m_na["class"] == "not_attempted" and m_na["credits"] == 0,
       "class=%s credits=%d" % (m_na["class"], m_na["credits"]))

    print("   %s" % ("ALL PASS" if not fails else "%d FAILURE(S): %s" % (len(fails), fails)))
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="the live agent: perceive now, decide the next hours")
    ap.add_argument("mode", nargs="?", default="dryrun",
                    choices=["dryrun", "run", "selftest"])
    ap.add_argument("--hours", type=int, default=HORIZON_H)
    ap.add_argument("--paid", action="store_true",
                    help="permit spending credits. Without it, nothing is ever called.")
    ap.add_argument("--metro", default=None)
    ap.add_argument("--limit-c", type=float, default=24.0)
    ap.add_argument("--out", default=None, help="write the emitted JSON here")
    # THE ENVIRONMENTAL GATES ARE SETTABLE, and default to OFF rather than to a value. The
    # air-quality index carries no documented units (findings 9.3), so a limit is a CHOICE the
    # caller makes and must never be one this file makes on their behalf.
    ap.add_argument("--dewpoint-limit", type=float, default=15.0,
                    help="humidity gate, C. 15.0 is the Green Grid WP#46 p.6 maximum. "
                         "Pass a negative value to disable.")
    ap.add_argument("--aq-limit", type=float, default=None,
                    help="contamination gate on FortyGuard's PM2.5 index. Unset = gate off, "
                         "because the index has no documented units.")
    ap.add_argument("--env-live-during-replay", action="store_true",
                    help="fetch live env_params even in a replay. A replay is free and reproducible "
                         "by default; this makes it neither, and costs 2,900.")
    ap.add_argument("--replay", default=None,
                    help="verify the decide path from a SAVED FortyGuard response. Output is "
                         "stamped replay-verification and is not a live forecast.")
    a = ap.parse_args()

    if a.mode == "selftest":
        return verify_live_offline()

    if a.mode == "run" and a.replay:
        say("REPLAY VERIFICATION -- ambient comes from %s, NOT from a live call."
            % os.path.basename(a.replay))
        say("   This proves the solve/bound/decide/act chain. It is NOT a live forecast and the")
        say("   emitted JSON is stamped `mode: replay-verification`.")
    elif a.mode == "run" and not a.paid:
        say("REFUSING TO RUN: `run` spends credits and --paid was not given.")
        say("   %d hourly windows x %s credits = %s (minus cache hits)."
            % (a.hours, format(HEATMAP_CREDITS, ","),
               format(a.hours * HEATMAP_CREDITS, ",")))
        say("   Use `dryrun` to see exactly what it would fetch, for free.")
        return 2

    metro = a.metro or M.metro_key()
    say("=" * 78)
    say("LIVE AGENT -- %s, %d h horizon, %s"
        % (metro, a.hours, "PAID" if a.paid else "DRY RUN (no calls)"))
    say("=" * 78)
    out = live_run(metro=metro, hours=a.hours, allow_paid=bool(a.paid),
                   cfg={"limit_c": a.limit_c,
                        "dewpoint_limit_c": (None if a.dewpoint_limit is not None
                                             and a.dewpoint_limit < 0 else a.dewpoint_limit),
                        "aq_limit_idx": a.aq_limit,
                        "env_live_during_replay": bool(a.env_live_during_replay)},
                   replay=a.replay)
    say("")
    say("   status           : %s" % out.get("status"))
    if out.get("operator_message"):
        say("   operator message : %s" % out["operator_message"])
    if out.get("NOT_LIVE"):
        say("   🔴 NOT LIVE      : %s" % out["NOT_LIVE"])
    if out.get("status") in ("ok", "ok_replay"):
        s = out["summary"]
        say("   free cooling     : %d of %d hours, %d mode change(s)"
            % (s["free_cooling_hours"], s["of_hours"], s["mode_changes"]))
        say("   blocked by       : temperature %d h, dew point %d h, solver refusal %d h"
            % (s["hours_blocked_by_temperature"], s["hours_blocked_by_dewpoint"],
               s["hours_refused_by_solver"]))
        say("   peak bound       : %s C against a %.1f C limit"
            % (s["peak_bound_c"], out["config"]["limit_c"]))
        say("   \U0001f534 the bound     : %s" % out["margin_provenance"]["prereg_verdict"])
    if out.get("spend"):
        say("   spend            : %s credits, %d live call(s), %d cache hit(s)"
            % (format(out["spend"]["credits_spent"] or 0, ","),
               out["spend"]["calls_attempted"], out["spend"]["cache_hits"]))
    dst = a.out or M.demo_path("live.json", metro)
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=1, default=str, allow_nan=False)
    say("   wrote            : %s" % os.path.basename(dst))
    return 0


if __name__ == "__main__":
    sys.exit(main())
