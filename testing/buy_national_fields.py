# -*- coding: utf-8 -*-
"""S7 -- BUY A FORTYGUARD FIELD FOR EVERY REAL, RANKED NATIONAL AOI. PAID.

    python buy_national_fields.py dryrun [--max-calls N]        # free, zero network, exact plan
    python buy_national_fields.py run --allow-paid [--max-calls N] [--chunk-size N]

AUTHORISED BY THE USER 2026-08-23: "authorize the full 379 now" -- the real, measured credit
ceiling (1,600,160 remaining / 4,220 per call), not the disputed "30/day" figure this session
corrected (that number was never more than a second-hand belief in `fortyguard-api-findings.md`
section 8.7, phrased "we understand it to be", and is a REQUEST asking FortyGuard to document it,
not a confirmed limit). This script does not assume either belief about a daily cap is true; it
measures.

--------------------------------------------------------------------------------------------
WHAT THIS BUYS, AND WHAT IT DOES NOT DECIDE
--------------------------------------------------------------------------------------------
One PAST, elapsed heatmap window per AOI, ranked by `pack_national_aois.py`'s impact order (tagged
buildings served). This is the SAME shape as the existing single-site purchases
(`fetch_chicago_field.py`): 8x8 km, granularity 60, analytic `tcm`, a fully-elapsed 2-hour window
-- a past window was, AS OF 2026-08-19, the choice that had never failed on this key. It is NOT a
guarantee: this script's own first live run and DIAG-66's control call (a fresh past window at
Ashburn's long-proven geometry) both came back `completed_but_empty`, fully billed, on
2026-08-23 -- the vendor relapsed into a general outage the same day its forecast path had
recovered. A past window still guarantees the vendor is not refusing on entitlement or horizon
grounds; it does not guarantee data. See `fetch_chicago_field.py`'s retraction of the same claim.

It does NOT decide site geometry, pairing, or which sites eventually ship in the demo -- that is
S4 onward. This script's only job is: for every AOI in the plan, get ONE real, correctly-timed,
correctly-priced FortyGuard field, tagged so it can never be mistaken for another AOI's field, and
account for every credit spent.

--------------------------------------------------------------------------------------------
THE TIMEZONE, MEASURED PER AOI -- NOT A STATE-LEVEL GUESS
--------------------------------------------------------------------------------------------
Gotcha #1 cost this project four days: `/v1/heatmap` reads `start_time` in the AOI's OWN local
zone and echoes no timestamp back. A crude "one zone per state" table would get most AOIs right
and the border ones wrong -- eastern Tennessee, western Texas, northern Idaho, the Dakotas -- with
no visible symptom, which is exactly the failure shape gotcha #1 already proved is invisible until
someone notices a plausible-looking wrong answer. `timezonefinder` (installed this session) does a
real point-in-polygon lookup against the actual IANA timezone boundaries, verified here against
five AOIs spanning Eastern/Central/Mountain/Pacific/Arizona's no-DST zone before being trusted.

--------------------------------------------------------------------------------------------
WHY CHUNKED, NOT ONE BATCH OF 379
--------------------------------------------------------------------------------------------
`live.py:perceive_ambient()` proved that submitting many requests together and polling them in one
shared loop turns N sequential waits into one wait -- reused here. But this project has ALSO
measured a real, multi-day vendor outage (HANDOFF.md section 4.0: `completed` with zero cells,
billed in full, for days) that recovered only hours before this session started. Submitting all 379
at once would mean a single unbroken commitment of the whole remaining credit balance before any
evidence exists that the run is actually working. Chunks of CHUNK_SIZE give a genuine checkpoint:
after each chunk this script measures its own success rate and REFUSES TO CONTINUE if two
consecutive chunks look like the historical outage signature, rather than spending blind into a
repeat of it (gotcha #123: "a product that lets a user spend real money on a service with a
measured 0% success rate is not being neutral").
"""
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (banner, box_aoi, classify_vendor, credits_remaining,   # noqa: E402
                    HEATMAP_CREDITS, is_billed, load_key, RESULTS, utc_now)

try:
    from timezonefinder import TimezoneFinder
except ImportError:
    TimezoneFinder = None

from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLAN_FILE = os.path.join(ROOT, "AGENTIC-ARBITER", "data", "geometry", "national_aoi_plan.json")
FIELDS_DIR = os.path.join(ROOT, "AGENTIC-ARBITER", "data", "national_fields")
LEDGER_FILE = os.path.join(RESULTS, "national_field_ledger.json")

SIDE_KM = 8.0
GRAN = 60
ANALYTIC = "tcm"
WIN_H = 2
TARGET_HOUR_LOCAL = 14           # same convention as the existing single-site purchases
V1 = "https://api.fortyguard.com/v1"

CHUNK_SIZE = 20                  # a deliberate checkpoint interval, not the disputed "30/day" cap
# 0.4 -> 3.0 s, 2026-08-25, at the user's explicit instruction: "keep a few seconds of interval
# between calls so they don't crash again". 0.4 s is a burst, not an interval -- twenty submits went
# out inside eight seconds. The cost of spacing them is trivial next to the cost of provoking the
# vendor: 3 s x 40 calls is two minutes, against a run that already takes ~25 s per call to poll.
# Kept as one constant so the pacing is a stated policy rather than a scatter of sleeps.
SUBMIT_STAGGER_S = 3.0           # matches live.py -- a burst of identical-shape submits triggered
                                 # one submit_rejected in twelve (gotcha #124); this is the same
                                 # insurance, same value, reused rather than re-derived
SUBMIT_RETRY_WAIT_S = 3.0
POLL_MAX_S = 300
STOP_AFTER_BAD_CHUNKS = 2        # two consecutive chunks below the health floor halts the run
CHUNK_HEALTH_FLOOR = 0.34        # a chunk is "unhealthy" if less than a third returned real data


def _tz_for(lat, lon, _tf=[None]):
    """The AOI's REAL local zone, measured -- not a state-level approximation. Cached lazily."""
    if _tf[0] is None:
        if TimezoneFinder is None:
            raise RuntimeError("timezonefinder is not installed -- refusing to guess a zone. "
                                "pip install timezonefinder.")
        _tf[0] = TimezoneFinder()
    name = _tf[0].timezone_at(lat=lat, lng=lon)
    if not name:
        raise RuntimeError("no timezone resolved for %.4f,%.4f -- refusing to guess." % (lat, lon))
    return name


def elapsed_window(tz_name, now_utc):
    """A fully-elapsed TARGET_HOUR_LOCAL window, +30 min safety margin, in the AOI's OWN zone."""
    tz = ZoneInfo(tz_name)
    now_local = now_utc.astimezone(tz)
    day = now_local.date()
    start = datetime(day.year, day.month, day.day, TARGET_HOUR_LOCAL, 0, tzinfo=tz)
    while start + timedelta(hours=WIN_H, minutes=30) > now_local:
        day = day - timedelta(days=1)
        start = datetime(day.year, day.month, day.day, TARGET_HOUR_LOCAL, 0, tzinfo=tz)
    end = start + timedelta(hours=WIN_H)
    return {"start_date": start.strftime("%Y-%m-%d"), "start_time": start.strftime("%H:00"),
            "end_time": end.strftime("%H:00"), "filter_type": 2}, start, end


def load_plan(max_calls):
    d = json.load(open(PLAN_FILE, encoding="utf-8"))
    aois = d["aois"]
    return aois[:max_calls] if max_calls is not None else aois, d


def build_job(rank, aoi):
    lat, lon = aoi["centre"]
    tz_name = _tz_for(lat, lon)
    dt, start, end = elapsed_window(tz_name, utc_now())
    return {
        "rank": rank, "aoi_key": "%s_%d" % (aoi["state"] or "XX", rank),
        "state": aoi["state"], "category": aoi["category"], "n_tagged": aoi["n_tagged"],
        "kind": aoi["kind"], "entries": aoi["entries"], "operators": aoi.get("operators", []),
        "centre": [lat, lon], "tz": tz_name,
        "window": dt, "window_local_str": "%s %s-%s %s" % (dt["start_date"], dt["start_time"],
                                                            dt["end_time"], tz_name),
        "payload": {"polygon_aoi": box_aoi(lat, lon, SIDE_KM), "granularity": GRAN,
                    "analytic_type": ANALYTIC, "date_time": dt},
    }


def submit_one(key, job):
    rec = {"aoi_key": job["aoi_key"], "rank": job["rank"], "submitted_at": time.time()}
    try:
        req = urllib.request.Request("%s/heatmap" % V1, data=json.dumps(job["payload"]).encode(),
                                     headers={"api-key": key, "Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
        rec["submit_http"] = 200
    except urllib.error.HTTPError as e:
        rec.update({"submit_http": e.code,
                    "submit_error_body": e.read().decode("utf-8", "replace")[:400]})
        return rec
    except Exception as e:                                            # noqa: BLE001
        rec.update({"submit_http": None, "submit_exception": str(e)[:300]})
        return rec
    rec["activity_id"] = (resp.get("data") or {}).get("activity_id")
    return rec


def read_status(key, aid):
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "%s/status/%s" % (V1, aid), headers={"api-key": key}), timeout=90)
        jd = json.loads(r.read())
    except Exception:                                                  # noqa: BLE001
        return None, None
    st = str((jd.get("data") or {}).get("status") or jd.get("message") or "?").lower()
    return st, ((jd.get("data") or {}).get("result") or None)


def append_ledger_one(entry):
    """Append ONE entry and flush to disk IMMEDIATELY. Called the instant a job resolves.

    🔴 THIS USED TO BATCH: `run_chunk()` returned ALL of a chunk's records, and the caller
    classified and wrote them to the ledger only after the WHOLE chunk (every job) had reached a
    terminal state. The first live national run was killed mid-chunk-2 after the credit meter
    (a free, independent check) showed 14 MORE calls had been billed than the ledger had any
    record of -- FortyGuard bills server-side the moment ITS job completes, entirely independent
    of whether this process is still alive to poll for the result. Gotcha #103's exact lesson
    ("a ledger with a blind spot is worse than no ledger, because it is trusted") recurring in a
    NEW shape: not a missing SOURCE this time, but a batching window wide enough for a kill to fall
    inside it. Fixed by writing the instant this process itself LEARNS a job is terminal, not after
    the slowest sibling in its chunk also finishes.
    """
    log = []
    if os.path.exists(LEDGER_FILE):
        try:
            log = json.load(open(LEDGER_FILE, encoding="utf-8"))
        except (OSError, ValueError):
            log = []
    log.append(entry)            # APPEND, NEVER OVERWRITE -- gotcha #100 was caused by exactly
                                 # the opposite of this.
    os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
    json.dump(log, open(LEDGER_FILE, "w", encoding="utf-8"), indent=1, allow_nan=False)


def finalize_job(job, rec):
    """Classify ONE resolved job, save its field if real, and ledger it -- all before returning."""
    # 🔴 COUNT THE FEATURES BEFORE CLASSIFYING, AND HAND THE COUNT TO THE CLASSIFIER.
    # `classify_vendor` reads `rec["tiles"]`. This module polls the vendor itself rather than through
    # common.submit_poll, so its record carries `result` and `activity_id` and has NO `tiles` key --
    # which made `rec.get("tiles")` always None, so `cls` was ALWAYS "completed_but_empty" and
    # `ok` was ALWAYS False. Every AOI this script ever bought was discarded on arrival and billed.
    # Measured 2026-08-25 on rank #1 (VA_1, 111 tagged buildings): 17,383 real features returned,
    # labelled empty, field not written, 4,220 credits charged.
    # `vendor_rec()` is NOT the right converter here -- it reads the activity id from `aid`, which is
    # common.submit_poll's key, not this module's. Passing the count explicitly is.
    feats = ((rec.get("result") or {}).get("map_data") or {}).get("features") or []
    cls = classify_vendor(dict(rec, tiles=len(feats)))
    billed = is_billed(cls)
    ok = cls == "ok" and len(feats) > 0
    if ok:
        out_path = os.path.join(FIELDS_DIR, "%s.json" % job["aoi_key"])
        json.dump({"aoi_key": job["aoi_key"], "rank": job["rank"], "state": job["state"],
                  "category": job["category"], "entries": job["entries"],
                  "centre": job["centre"], "tz": job["tz"], "window": job["window"],
                  "n_tiles": len(feats), "activity_id": rec.get("activity_id"),
                  "raw_result": rec.get("result")},
                 open(out_path, "w", encoding="utf-8"), default=str, allow_nan=False)
    append_ledger_one({
        "aoi_key": job["aoi_key"], "rank": job["rank"], "state": job["state"],
        "category": job["category"], "n_tagged": job["n_tagged"], "entries": job["entries"],
        "window_local": job["window_local_str"], "class": cls, "billed": billed,
        "n_tiles": len(feats), "activity_id": rec.get("activity_id"),
        "terminal_status": rec.get("terminal_status"), "submit_http": rec.get("submit_http"),
        "error": rec.get("error"), "credits_charged": HEATMAP_CREDITS if billed else 0,
        "bought_at_utc": utc_now().isoformat(),
    })
    print("      #%-4d %-4s %-16s class=%-20s tiles=%-6d %s"
          % (job["rank"], job["state"] or "??", job["aoi_key"], cls, len(feats),
             "BILLED" if billed else "free"))
    return ok, billed


def run_chunk(key, jobs):
    """Submit every job, staggered, poll together, and FINALIZE EACH THE INSTANT IT RESOLVES.

    Returns (n_ok, n_billed_empty, n_free_fail) for jobs finalized before this call returns. A job
    still genuinely `outstanding` when this returns has NOT been billed yet either -- billing and
    terminal status are the same event server-side -- so nothing counted here can be a blind spot.
    """
    recs, finalized = {}, set()
    n_ok = n_billed_empty = n_free_fail = 0

    def _finish(k):
        nonlocal n_ok, n_billed_empty, n_free_fail
        if k in finalized:
            return
        finalized.add(k)
        ok, billed = finalize_job(recs[k]["job"], recs[k])
        if ok:
            n_ok += 1
        elif billed:
            n_billed_empty += 1
        else:
            n_free_fail += 1

    for k, job in enumerate(jobs):
        if k:
            time.sleep(SUBMIT_STAGGER_S)
        rec = submit_one(key, job)
        if not rec.get("activity_id") and rec.get("submit_http") not in (None, 200):
            time.sleep(SUBMIT_RETRY_WAIT_S)
            retry = submit_one(key, job)
            retry["submit_retried_after"] = rec.get("submit_http")
            rec = retry
        rec["job"] = job
        recs[job["aoi_key"]] = rec
        if not rec.get("activity_id"):
            _finish(job["aoi_key"])     # a rejected/failed SUBMIT is already terminal -- free

    outstanding = {k: r for k, r in recs.items() if r.get("activity_id")}
    t0 = time.time()
    statuses_seen = {k: [] for k in outstanding}
    empty_polls = {k: 0 for k in outstanding}
    while outstanding and time.time() - t0 < POLL_MAX_S:
        for k in list(outstanding):
            st, result = read_status(key, outstanding[k]["activity_id"])
            if st is None:
                continue
            if st not in statuses_seen[k]:
                statuses_seen[k].append(st)
            if st == "completed":
                feats = ((result or {}).get("map_data") or {}).get("features") or []
                if feats:
                    recs[k].update({"terminal_status": "completed", "result": result,
                                    "statuses_seen": statuses_seen[k],
                                    "empty_completed_polls": empty_polls[k]})
                    del outstanding[k]
                    _finish(k)                       # ledgered THE INSTANT this process learns it
                else:
                    empty_polls[k] += 1     # completed but not yet populated -- keep polling
            elif st in ("processing", "pending", "queued", "in progress"):
                continue
            else:
                recs[k].update({"terminal_status": st, "statuses_seen": statuses_seen[k],
                                "empty_completed_polls": empty_polls[k]})
                del outstanding[k]
                _finish(k)
        if outstanding:
            print("      ... %d still outstanding, %.0f s elapsed"
                  % (len(outstanding), time.time() - t0))
            time.sleep(8)
    for k in list(outstanding):      # timed out -- still finalize what evidence exists
        recs[k].update({"terminal_status": "completed" if empty_polls[k] else "timeout",
                        "empty_completed_polls": empty_polls[k], "statuses_seen": statuses_seen[k],
                        "error": "timed out after %d polls" % empty_polls[k] if empty_polls[k]
                                 else "timeout, never completed"})
        _finish(k)
    return n_ok, n_billed_empty, n_free_fail


def main(argv):
    # 🔴 STDOUT WAS FULLY BUFFERED WHEN REDIRECTED TO A LOG FILE, AND IT COST REAL VISIBILITY
    # DURING A LIVE PAID RUN. Redirecting to a file (rather than a terminal) makes Python's
    # default buffering mode BLOCK-buffered, not line-buffered -- nothing appeared in the log for
    # the first several minutes of the first live run despite real, billed activity already
    # happening, and the only way to tell the process was actually working was to check the credit
    # meter directly. A run that can spend real money must never depend on someone knowing to
    # route around output buffering to see what it is doing.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    mode = argv[0] if argv else "dryrun"
    allow_paid = "--allow-paid" in argv
    max_calls = None
    chunk_size = CHUNK_SIZE
    for i, a in enumerate(argv):
        if a == "--max-calls" and i + 1 < len(argv):
            max_calls = int(argv[i + 1])
        if a == "--chunk-size" and i + 1 < len(argv):
            chunk_size = int(argv[i + 1])

    if not os.path.exists(PLAN_FILE):
        print("no national_aoi_plan.json -- run pack_national_aois.py first")
        return 2

    banner("S7 -- NATIONAL FORTYGUARD FIELD PURCHASE")
    if TimezoneFinder is None:
        print("   timezonefinder is not installed. pip install timezonefinder. Refusing to guess.")
        return 2

    if mode == "dryrun":
        aois, plan = load_plan(max_calls or 10 ** 6)
        key_needed_for_tz = False
        print("   plan: %d AOIs available, showing the first %d (or fewer if fewer exist)"
              % (len(plan["aois"]), max_calls or len(aois)))
        cost = 0
        for rank, aoi in enumerate(aois, 1):
            job = build_job(rank, aoi)
            cost += HEATMAP_CREDITS
            if rank <= 15 or rank > len(aois) - 3:
                print("   #%-4d %-4s %-8s tagged=%-4d  %-19s  %s"
                      % (rank, aoi["state"] or "??", aoi["kind"], aoi["n_tagged"],
                         job["window_local_str"], (", ".join(aoi.get("operators", [])) or "-")[:40]))
            elif rank == 16:
                print("   ... (%d more) ..." % (len(aois) - 18))
        print("\n   TOTAL: %d calls x %d credits = %d credits" % (len(aois), HEATMAP_CREDITS, cost))
        print("   NOTHING WAS SPENT. NO NETWORK CALL WAS MADE. Run with `run --allow-paid` to spend.")
        return 0

    if mode != "run" or not allow_paid:
        print("usage: buy_national_fields.py dryrun | run --allow-paid [--max-calls N] "
              "[--chunk-size N]")
        return 2

    key = load_key()
    before_all = credits_remaining(key)
    affordable = before_all // HEATMAP_CREDITS
    n_calls = min(max_calls or affordable, affordable)
    aois, plan = load_plan(None)
    aois = aois[:n_calls]
    print("   credits remaining right now (measured): %s" % format(before_all, ","))
    print("   affordable at %s/call: %d calls" % (format(HEATMAP_CREDITS, ","), affordable))
    print("   this run will attempt up to %d calls, in chunks of %d\n" % (len(aois), chunk_size))

    os.makedirs(FIELDS_DIR, exist_ok=True)
    bad_chunk_streak = 0
    total_ok = total_billed_empty = total_free_fail = 0
    chunk_start = 0
    rank_offset = 1
    while chunk_start < len(aois):
        remaining_credits = credits_remaining(key)
        can_afford = remaining_credits // HEATMAP_CREDITS
        if can_afford <= 0:
            print("   STOPPING: %d credits remaining, cannot afford another call."
                  % remaining_credits)
            break
        chunk_aois = aois[chunk_start: chunk_start + min(chunk_size, can_afford)]
        if not chunk_aois:
            break
        jobs = [build_job(rank_offset + i, a) for i, a in enumerate(chunk_aois)]
        print("   --- chunk %d: ranks %d-%d, %d credits remaining before this chunk ---"
              % (chunk_start // chunk_size + 1, jobs[0]["rank"], jobs[-1]["rank"],
                 remaining_credits))
        # Every job in this chunk is now classified, saved (if real) and ledgered THE INSTANT it
        # resolves, inside run_chunk() itself -- not batched until the whole chunk returns. A kill
        # partway through this call can therefore never again leave a billed job unrecorded: by
        # the time this process has learned a job is terminal, it has already been written to
        # disk. See finalize_job()'s docstring for the run this was found on.
        chunk_ok, chunk_billed_empty, chunk_free_fail = run_chunk(key, jobs)
        total_ok += chunk_ok; total_billed_empty += chunk_billed_empty
        total_free_fail += chunk_free_fail

        n_this_chunk = len(jobs)
        health = chunk_ok / n_this_chunk if n_this_chunk else 0.0
        print("   chunk result: %d ok / %d billed-empty / %d free-fail  (health %.0f%%)"
              % (chunk_ok, chunk_billed_empty, chunk_free_fail, 100 * health))
        # 🔴 A CATASTROPHIC FIRST CHUNK MUST NOT WAIT FOR A SECOND ONE TO CONFIRM IT.
        # The first live run needed a MANUAL kill after chunk 1 came back 20-for-20 empty (0 %
        # health), because STOP_AFTER_BAD_CHUNKS=2 required a second bad chunk before the script
        # would have stopped itself -- and by the time a human intervened, chunk 2 had already
        # billed 14 more calls into the same fault. Zero real results out of a full chunk is
        # already overwhelming evidence; waiting for a second chunk to "confirm" it only spends
        # more money to learn what is already known.
        if chunk_ok == 0 and n_this_chunk >= 10:
            print("\n   STOPPING IMMEDIATELY: the FIRST chunk returned ZERO real results out of "
                  "%d. Matches the signature of the multi-day vendor outage HANDOFF.md section "
                  "4.0 measured. Refusing to spend into a second chunk to 'confirm' a result this "
                  "clear. Report back before resuming." % n_this_chunk)
            break
        if health < CHUNK_HEALTH_FLOOR:
            bad_chunk_streak += 1
            print("   !! chunk health below the %.0f%% floor (streak %d/%d)"
                  % (100 * CHUNK_HEALTH_FLOOR, bad_chunk_streak, STOP_AFTER_BAD_CHUNKS))
            if bad_chunk_streak >= STOP_AFTER_BAD_CHUNKS:
                print("\n   STOPPING: %d consecutive unhealthy chunks -- this matches the "
                      "signature of the multi-day vendor outage HANDOFF.md section 4.0 measured. "
                      "Refusing to keep spending into it blind. Report this back before resuming."
                      % bad_chunk_streak)
                break
        else:
            bad_chunk_streak = 0

        chunk_start += len(chunk_aois)
        rank_offset += len(chunk_aois)

    after_all = credits_remaining(key)
    print("\n" + "=" * 78)
    print("   TOTAL this run: %d ok / %d billed-empty / %d free-fail, attempted %d of %d planned"
          % (total_ok, total_billed_empty, total_free_fail, chunk_start, len(aois)))
    print("   credits: %s -> %s  (spent %s)"
          % (format(before_all, ","), format(after_all, ","), format(before_all - after_all, ",")))
    print("   real fields written to: %s" % FIELDS_DIR)
    print("   ledger appended: %s" % LEDGER_FILE)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
