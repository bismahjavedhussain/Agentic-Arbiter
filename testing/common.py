# -*- coding: utf-8 -*-
"""Shared helpers for the INTAKE test suite.

Nothing here spends credits. The API client is used only by the paid tests,
and every response it returns is written to results/fixtures/ so the rest of
the suite (and the demo) can run offline.
"""
import json, math, os, sys, time, urllib.request, urllib.error, statistics

# ---------------------------------------------------------------- console encoding
# The Windows console defaults to cp1252, a 256-character legacy codepage. Any print() containing a
# character outside it -- a warning glyph, an arrow, a degree-adjacent symbol -- raises
# UnicodeEncodeError and kills the process.
#
# That is not cosmetic. In N-38 it fired at line 185, AFTER all 40 paid API calls had completed but
# BEFORE save_result() ran, so the result was destroyed. It survived only because submit_poll()
# happens to cache every response to disk, making the re-run free. Luck, not design.
#
# It had already happened twice before. Relying on remembering to use ASCII in print() has a
# demonstrated failure rate of 3, so force UTF-8 on the streams instead and stop depending on
# discipline. Every test imports this module, so every test is covered.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(HERE, "results")
FIXTURES = os.path.join(RESULTS, "fixtures")
os.makedirs(FIXTURES, exist_ok=True)

# Fields already captured in earlier work, reused so we do not pay twice.
#
# ⚠ SCRATCH NAMES A DEAD DIRECTORY, and that is a trap rather than a bug in itself. It points at one
# specific Claude session's temp folder, by id, and that session is long gone: the path does not exist.
# Anything that looked ONLY here silently found nothing. test_n21_validate.py and
# test_n22_calibrate.py did exactly that and have been exiting 2 with "no field data found in the
# scratchpad" ever since, which reads like an absent dataset rather than a stale path.
SCRATCH = os.path.join(
    os.environ.get("TEMP", r"C:\Users\bisma\AppData\Local\Temp"),
    "claude", "d--FGHackathon", "48b2e995-a9e0-4f0c-8ab4-8cbe4f628a17", "scratchpad")

# THE DURABLE HOME of the digitised field data, which is where those CSVs actually survived. All seven
# filenames the two recirculation tests ask for are here, and they are the evidence behind README's
# recirculation and 67-Prairie-Grass claims: CSVs digitised from California Energy Commission report
# CEC-500-2013-065, whose three source PDFs sit beside them.
VALIDATION = os.path.join(os.path.dirname(HERE), "validation-data")

SAVED_FIELDS = {
    "DC_2026-06-23": "dec_1_DC_dayA.json",     # 8x8 km @ 39.0100,-77.4460  17,862 tiles
    "DC_2026-07-28": "dec_2_DC_dayB.json",     # identical polygon, different day
    "CT_2026-06-23": "dec_3_CT_dayA.json",     # control polygon @ 39.1500,-77.2000
    "CT_2026-07-28": "dec_4_CT_dayB.json",
}

TARGET_CENTRE = (39.0100, -77.4460)            # 168 usable data centres inside 8x8 km
TARGET_SIDE_KM = 8.0

R_EARTH = 6371000.0


# ----------------------------------------------------------------- time  🐛 THE 9-HOUR BUG
# The heatmap endpoint interprets `start_time` / `end_time` in the AOI's OWN LOCAL TIME. It echoes
# no timestamp and carries no metadata block, so a wrong assumption is completely silent.
#
# Every earlier paid test built its windows from datetime.now() -- this machine, UTC+5 -- and sent
# bare "%H:00" strings. The AOI is Loudoun County, Virginia, UTC-4 in August. That is a silent
# NINE HOUR error on every forecast request we ever issued, and it invalidated their lead labels.
#
# Established from data already on disk, at zero cost, by two independent arguments:
#   1. Across five saved days the diurnal maximum falls in the 16:00-18:00 labelled window and is
#      already declining by 18:00-20:00. That is a normal local afternoon curve. Under a UTC
#      reading, 18:00 UTC = 14:00 EDT, essentially the peak, where temperature cannot be falling.
#   2. Site-local is the ONLY one of the three candidate conventions that explains which N-13
#      leg-1 windows returned data: true start-leads of 9.25 h and 11.25 h succeeded, 13.25 h and
#      17.25 h returned zero tiles. The cut sits exactly at the documented 12 h horizon. A UTC
#      reading predicts the 9.25 h case should have succeeded; it did not.
#
# Consequences already actioned: N-18's four "leads" of 4/6/8/10 h were really 13/15/17/19 h, all
# beyond the horizon, so its "48 retries recovered nothing" is OUR bug and the intermittency claim
# against FortyGuard is withdrawn. The silent-empty-success defect stands, and is now sharper.
#
# USE THESE HELPERS. Never format a window time from a naive datetime again.
SITE_TZ_NAME = "America/New_York"              # the AOI throughout is Loudoun County, Virginia


def site_tz():
    from zoneinfo import ZoneInfo
    return ZoneInfo(SITE_TZ_NAME)


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def site_now():
    """Current time in the AOI's local zone -- the zone the endpoint speaks."""
    return utc_now().astimezone(site_tz())


def site_window(start_site, win_h):
    """Payload fields for a window given its SITE-LOCAL start. Returns a dict plus the UTC bounds.

    start_site must be timezone-aware in the site zone (build it with site_now().replace(...)).
    Raises on a naive datetime rather than guessing, because guessing is what caused the bug.
    """
    from datetime import timedelta
    if start_site.tzinfo is None:
        raise ValueError("start_site must be timezone-aware in the site zone -- naive datetimes "
                         "are exactly how the 9-hour bug happened")
    end_site = start_site + timedelta(hours=win_h)
    if end_site.date() != start_site.date():
        raise ValueError("window crosses midnight; the endpoint takes a single start_date")
    return {
        "start_date": start_site.strftime("%Y-%m-%d"),
        "start_time": start_site.strftime("%H:00"),
        "end_time": end_site.strftime("%H:00"),
        "filter_type": 2,
        "_start_utc": start_site.astimezone(utc_now().tzinfo),
        "_end_utc": end_site.astimezone(utc_now().tzinfo),
    }


def lead_hours(start_utc, now=None):
    """TRUE lead in hours from now to a window start. Negative once the start has passed."""
    return ((start_utc - (now or utc_now())).total_seconds()) / 3600.0


# ----------------------------------------------------------------- geometry
def hav(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    dla, dlo = (la2 - la1) * p, (lo2 - lo1) * p
    h = math.sin(dla / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin(dlo / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(h))


def box_aoi(clat, clon, side_km):
    a = (side_km / 2) / 110.574
    o = (side_km / 2) / (111.320 * math.cos(math.radians(clat)))
    ring = [[clon - o, clat - a], [clon + o, clat - a], [clon + o, clat + a],
            [clon - o, clat + a], [clon - o, clat - a]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


# ----------------------------------------------------------------- fields
def field_path(fn):
    # VALIDATION added 2026-08-28. SCRATCH names a dead session temp directory, so anything that
    # lived only there was unreachable; validation-data/ is where the digitised CSVs actually survived.
    for base in (SCRATCH, VALIDATION, FIXTURES, HERE):
        p = os.path.join(base, fn)
        if os.path.exists(p):
            return p
    return None


def load_field(key):
    """Return list of (lat, lon, props) for a saved heatmap response, or None."""
    fn = SAVED_FIELDS.get(key)
    if not fn:
        return None
    p = field_path(fn)
    if not p:
        return None
    feats = json.load(open(p))["map_data"]["features"]
    out = []
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        out.append((la, lo, t["properties"]))
    return out


def tile_key(la, lo):
    """Stable key for matching the same tile across calls (lattice verified identical)."""
    return (round(la, 6), round(lo, 6))


# ----------------------------------------------------------------- reporting
def banner(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def verdict(ok, msg_pass, msg_fail):
    print("   VERDICT: %s" % (msg_pass if ok else msg_fail))
    return ok


def save_result(name, obj):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "w") as f:
        json.dump(obj, f, indent=1, default=str)


def stats(vals):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    return {"n": len(vals), "min": round(min(vals), 4), "max": round(max(vals), 4),
            "mean": round(statistics.fmean(vals), 4), "sd": round(statistics.pstdev(vals), 4)}


# ----------------------------------------------------------------- API (paid tests only)
def load_key():
    """The FortyGuard key, from the environment first and the repository .env second.

    🔴 THE ENVIRONMENT BRANCH IS WHAT MAKES DEPLOYMENT POSSIBLE, and its absence was a hard blocker.
    This function used to read `<root>/.env` and nothing else. That file is gitignored and must stay
    that way, so it does not exist on a deployed host: the live agent could not start anywhere except
    this machine, and it would have failed with "FORTYGUARD_API_KEY not found in .env" on a box where
    no such file could ever legitimately exist. Every host injects secrets as environment variables,
    so that is now the first place looked.

    ORDER MATTERS AND IT IS DELIBERATE. The environment wins, because on a host that is the only
    source, and locally a developer who exports the variable is deciding to override the file on
    purpose. The .env fallback keeps every existing local workflow working unchanged.

    THE VALUE IS STILL NEVER PRINTED, LOGGED OR RETURNED ANYWHERE BUT HERE. Only the length and a
    hash prefix are ever reported, by testing/scan_secrets.py. Nothing about that changes.
    """
    env = os.environ.get("FORTYGUARD_API_KEY")
    if env and env.strip():
        return env.strip().strip('"').strip("'")

    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            if line.strip().startswith("FORTYGUARD_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise RuntimeError(
        "FORTYGUARD_API_KEY not found. Set it as an environment variable (this is how a deployed "
        "host supplies it) or put it in the repository-root .env for local work.")


V1 = "https://api.fortyguard.com/v1"


def _headers(key):
    return {"api-key": key, "Content-Type": "application/json"}


def credits_remaining(key):
    req = urllib.request.Request(f"{V1}/system/fetch-api-key-usage",
                                data=json.dumps({"api_key": key}).encode(),
                                headers=_headers(key))
    d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d["credit_summary"]["cycle_remaining_credits"]


def submit_poll(key, endpoint, payload, tag, max_s=600, wait=8, require_data=True):
    """Submit, poll to completion AND to POPULATED DATA, save the raw response as a fixture.

    🔴 BUG FIXED 2026-08-19, AND IT WAS THE CAUSE OF OUR "BLOCKER".

    This function used to return the moment `status == "completed"`, without checking whether
    `map_data.features` had actually been populated. FortyGuard's own team then documented the
    behaviour that breaks:

        "map_data / stats_data can return empty on the first Completed poll -- you need to keep
         polling even after status hits Completed until the data fields are actually populated."
        -- Qusay Alhasanat, FortyGuard

    So a `completed` response with zero tiles is NOT necessarily an out-of-range request, an empty
    area, or a missing plan entitlement. It can simply be **too early**. We recorded four such
    responses as hard failures and spent two days concluding that forecast windows were unavailable
    on this plan. `assert_non_empty()` existed and was being used -- but DOWNSTREAM, to classify an
    already-returned empty result as terminal, which is exactly the wrong reading.

    The loop now treats "completed but empty" as a REASON TO KEEP POLLING, and reports how many
    extra polls were needed so the behaviour is measurable rather than folklore. Set
    `require_data=False` only when an empty result is genuinely the measurement being taken.

    EVERY RETURN PATH ALSO CARRIES THE EVIDENCE NEEDED TO CLASSIFY THE FAILURE -- added
    2026-08-21, Session 4. `error` is a sentence; a sentence cannot be counted. The vendor now
    fails in three distinguishable ways whose BILLING DIFFERS (`completed`-with-no-data is charged
    4,220; `failed` and an indefinite `Processing` stall are free), so a caller that has to decide
    whether to retry needs the shape, not the prose. It also keeps the HTTP status and body of a
    rejected submit, which gotcha #124 lost: "a record of a failure that omits the reason is
    barely a record." Additive only -- `ok` / `error` / `aid` / `result` are unchanged.
    """
    t0 = time.time()
    statuses_seen, polls = [], 0

    def _out(d):
        """Every exit carries the same evidence block, so no path can forget one."""
        d.setdefault("secs", round(time.time() - t0, 1))
        d["polls"] = polls
        d["statuses_seen"] = statuses_seen
        d["empty_completed_polls"] = d.get("empty_completed_polls", 0)
        return d

    try:
        req = urllib.request.Request(f"{V1}/{endpoint}",
                                     data=json.dumps(payload).encode(), headers=_headers(key))
        http = urllib.request.urlopen(req, timeout=90)
        submit_http, resp = http.status, json.loads(http.read())
    except urllib.error.HTTPError as e:
        # The vendor answered and said no. The BODY is the only field that explains why -- a 429
        # and a malformed-payload 422 are the same status class to a caller and need opposite
        # responses, so it is kept rather than collapsed into str(e).
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            body = None
        return _out({"error": "submit: HTTP %d %s" % (e.code, (body or "")[:160]),
                     "submit_http": e.code, "submit_error_body": body})
    except Exception as e:
        # No HTTP status at all: DNS, TLS, timeout. Not the vendor refusing -- the vendor unreached.
        return _out({"error": "submit: %s" % str(e)[:200], "submit_http": None,
                     "submit_error_body": None, "submit_exception": type(e).__name__})
    aid = resp.get("data", {}).get("activity_id")
    empty_completed_polls = 0
    last_empty = None
    while time.time() - t0 < max_s:
        try:
            j = urllib.request.urlopen(
                urllib.request.Request(f"{V1}/status/{aid}", headers=_headers(key)), timeout=90)
        except Exception:
            time.sleep(wait); continue
        polls += 1
        if j.status == 404:                       # documented grace window right after submit
            time.sleep(wait); continue
        jd = json.loads(j.read())
        st = str(jd.get("data", {}).get("status") or jd.get("message")).lower()
        if st not in statuses_seen:
            statuses_seen.append(st)
        if st == "completed":
            res = jd["data"]["result"]
            ok, why = assert_non_empty(res)
            if ok or not require_data:
                with open(os.path.join(FIXTURES, "%s.json" % tag), "w") as f:
                    json.dump(res, f, default=str)
                return _out({"ok": True, "aid": aid, "submit_http": submit_http,
                             "terminal_status": st, "result": res,
                             "empty_completed_polls": empty_completed_polls, "data_note": why})
            # COMPLETED BUT NOT YET POPULATED -- keep polling, per FortyGuard's guidance
            empty_completed_polls += 1
            last_empty = res
            time.sleep(wait); continue
        if st in ("processing", "pending", "queued", "in progress"):
            time.sleep(wait); continue
        return _out({"error": st, "aid": aid, "submit_http": submit_http, "terminal_status": st})
    # timed out. If it was completed-but-empty throughout, say so precisely -- that is a different
    # finding from "still processing", and only now may it be called empty.
    if empty_completed_polls:
        with open(os.path.join(FIXTURES, "%s.json" % tag), "w") as f:
            json.dump(last_empty, f, default=str)
        return _out({"error": "completed but never populated after %d polls over %.0f s"
                             % (empty_completed_polls, time.time() - t0),
                     "aid": aid, "submit_http": submit_http, "terminal_status": "completed",
                     "empty_completed_polls": empty_completed_polls, "result": last_empty})
    return _out({"error": "timeout", "aid": aid, "submit_http": submit_http,
                 "terminal_status": None})


# ============================================================================
# WHAT ACTUALLY HAPPENED TO ONE REQUEST -- the single classifier
# ============================================================================
# MOVED HERE FROM src/live.py 2026-08-21 (Session 4). It was written for the live agent, and the
# collector needed the same judgement -- so the choice was a second copy or a shared one. Rule 12
# of the gotcha log ("never let two code paths compute one quantity two ways") has been violated
# three times in this project and cost real time each time, so it is shared. `common.py` is the
# natural home because both callers ALREADY import it: `live.py` for load_key(), the collector for
# everything. Importing `live.py` from the collector was the alternative and it is worse -- it
# would drag numpy and the whole agent into an unattended scheduled task.

# THE BILLING PARTITION, AND IT IS THE WHOLE REASON THIS FUNCTION IS SHARED.
# Measured against the live vendor on 2026-08-20/21, not inferred from documentation:
#   completed + zero features   BILLED 4,220   (11 of them in one live run = 46,420 credits)
#   status: failed              FREE
#   indefinite Processing stall FREE
#   submit rejected (4xx/5xx)   FREE
# Until 2026-08-20 every failure was billed, so "attempts" and "billed calls" were the same number
# and the collector's retry budget could count either. They are no longer the same number (gotcha
# #101), and a budget that exists to ration CREDITS must therefore count what is CHARGED.
BILLED_CLASSES = frozenset(("ok", "completed_but_empty"))

# The price of one heatmap call, MEASURED by differencing the credit meter across single calls,
# repeatedly. Defined here 2026-08-21 because a second consumer appeared: the collector now costs
# its own retries, and `api_usage_ledger.py` had held the only copy. Two copies of a measured price
# is gotcha #12, and `audit.py` check 4 exists because that has happened before -- so the ledger
# imports this one rather than keeping its own.
HEATMAP_CREDITS = 4_220


def classify_vendor(rec):
    """What actually happened to one heatmap request.

    A STALL IS NOT A FAILURE and neither is a rejection. DIAG-63's first version collapsed all of
    them to "fail", which reads as "the vendor said no" -- when in fact the vendor said HTTP 200,
    issued an activity id, answered 45 status polls, and simply never finished the job. Different
    fault, different owner, different message to the operator.
    """
    # 🔴 AN UNCONVERTED RECORD IS NOT CLASSIFIABLE, AND ACCEPTING ONE SILENTLY COST REAL MONEY AND
    # FIVE DAYS OF A WRONG DIAGNOSIS.
    # This function reads `rec["tiles"]`. A raw submit-and-poll return does not have that key -- it
    # carries the payload at `result.map_data.features` -- and `vendor_rec()` below exists precisely
    # to convert one into the other. Three callers skipped it: buy_national_fields.py,
    # national_recovery_watch.py and diag67. For those, `rec.get("tiles")` was ALWAYS None, so this
    # function could never return "ok", so every completed job was labelled `completed_but_empty`
    # no matter what the vendor sent. Measured 2026-08-25: one authorised AOI purchase returned
    # 17,383 real features at `result.map_data.features`, was labelled empty, had its field
    # discarded by `ok = cls == "ok" and ...`, and was billed 4,220 credits. The same shape explains
    # the "20-for-20 completed_but_empty across nine states" run that was read as a vendor outage --
    # a simultaneous 100 % failure across VA, CA, TX, OH, WA, OR, PA, IA and WY is far more
    # consistent with one client-side bug than with nine regions failing at once.
    # Worse, `national_recovery_watch.py` had the same defect, so THE THING WATCHING FOR RECOVERY
    # COULD NEVER SEE IT: it probed, received real tiles, classified them empty, and reported the
    # vendor still down.
    # So an unrecognised shape now RAISES instead of resolving to the most pessimistic class. A
    # loud failure costs one traceback; a silent one cost a plan-sized misreading.
    if "tiles" not in rec and "result" in rec:
        raise TypeError(
            "classify_vendor() was handed a RAW submit/poll return (it has 'result' and no "
            "'tiles'). Convert it first -- vendor_rec(r) for a common.submit_poll return, or "
            "dict(rec, tiles=len(features)) if the caller polled the vendor itself. Classifying "
            "the raw shape silently reports every completed job as empty.")
    if rec.get("submit_http") != 200:
        return "submit_rejected"
    if not rec.get("activity_id"):
        return "no_activity_id"
    if rec.get("tiles"):
        return "ok"
    st = rec.get("terminal_status")
    if st == "completed":
        return "completed_but_empty"
    if st:
        return "terminal_" + st
    if set(rec.get("statuses_seen") or []) <= {"processing", "pending", "queued", "in progress"}:
        return "stalled_in_processing"
    return "unknown"


def is_billed(cls):
    """Did this outcome move the credit meter?

    Anything not measured as free is assumed BILLED. That asymmetry is deliberate: guessing "free"
    on an unrecognised class under-reports spend, and this project has already had a ledger with a
    blind spot it trusted (gotcha #103). Over-reporting is visible in the reconciliation; the meter
    is the final witness either way.
    """
    return cls in BILLED_CLASSES or cls.startswith("unknown")


VENDOR_HUMAN = {
    "ok": "answered",
    "submit_rejected": "rejected the request outright",
    "no_activity_id": "accepted the request but issued no activity id",
    "completed_but_empty": "reported the job COMPLETE and returned zero tiles",
    "stalled_in_processing": "accepted the job and never finished it",
}


def vendor_sentence(cls, rec):
    """One line an operator could act on. No jargon, no blame, the numbers that were observed."""
    base = VENDOR_HUMAN.get(cls) or ("ended the job with status %r" % cls.replace("terminal_", ""))
    bits = ["FortyGuard " + base]
    if rec.get("activity_id"):
        bits.append("activity %s" % rec["activity_id"][:8])
    if rec.get("elapsed_s") is not None:
        bits.append("after %.0f s and %d status polls" % (rec["elapsed_s"], rec.get("polls", 0)))
    if rec.get("submit_error_body"):
        bits.append("body: %s" % rec["submit_error_body"][:160])
    return ", ".join(bits) + "."


def vendor_rec(r, tiles=None):
    """Normalise a `submit_poll` return into the record `classify_vendor` reads.

    Two callers build these records from different shapes -- the live agent from its own submit and
    poll calls, the collector from `submit_poll` -- and the classifier must not learn about either.
    So the shape conversion lives here, once, next to the thing it feeds.

    `tiles` is passed in rather than counted from `result`, because the caller already counted it
    and recounting it a second way is how two paths drift.
    """
    if tiles is None:
        res = r.get("result") or {}
        feats = (res.get("map_data") or {}).get("features") or []
        tiles = len(feats)
    return {"submit_http": r.get("submit_http"),
            "activity_id": r.get("aid"),
            "tiles": tiles,
            "terminal_status": r.get("terminal_status"),
            "statuses_seen": r.get("statuses_seen") or [],
            "elapsed_s": r.get("secs"),
            "polls": r.get("polls", 0),
            "empty_completed_polls": r.get("empty_completed_polls", 0),
            "submit_error_body": r.get("submit_error_body"),
            "error": r.get("error")}


def recent_vendor_record(hours_back=6.0, results_dir=None):
    """How the vendor has actually behaved lately. Zero network calls, no key read.

    WHY THE PRODUCT NEEDS THIS. A 12-hour horizon costs up to 50,640 credits, and on a day when
    FortyGuard returns `completed` with an empty field for every window that is 50,640 credits for
    nothing -- which is exactly what happened: 11 of 12 windows empty in one batch, then 4 of 4 in
    the next. Inviting a click that spends real money on a service with a measured 0 % success rate
    over the last hour is not a neutral default.

    So the recent record is surfaced and the user decides with it in front of them. It is NOT a
    block: the vendor recovered once today after three days of failure, so refusing outright would
    be as wrong as spending blindly.

    TWO SOURCES, AND THE SECOND ONE WAS A BLIND SPOT UNTIL 2026-08-21. This read `live_spend.json`
    alone -- the live agent's own runs. But the COLLECTOR spends against the same vendor on a
    schedule, and on any day the live agent had not been run this function returned None: no record,
    from a function whose entire job is to put the record in front of a paying click. Measured that
    morning: last live run 18 h old, four collector failures the same day, function returns None.
    Gotcha #103's lesson is that a record with a blind spot is worse than none because it is
    trusted, so both spenders now report into it and the caller is told which sources it saw.
    """
    from datetime import datetime, timezone
    # `results_dir` is injectable ONLY so this function can be tested. It sits in front of a button
    # that spends 50,640 credits and its blind spot went unnoticed for a day, so "it is hard to test
    # without touching the real manifest" is not an acceptable reason to leave it untested.
    results_dir = results_dir or RESULTS
    cut = time.time() - hours_back * 3600
    ok = empty = other = 0
    billed_no_data = 0          # counted through is_billed(), never by assuming a class is free
    latest = None
    sources = []

    def _stamp(v):
        try:
            return datetime.fromisoformat(str(v)).timestamp()
        except (ValueError, TypeError):
            return None

    def _tally(c, ok, empty, other, billed_no_data):
        """One place decides what a class means, and BILLING is decided by is_billed().

        The first version of this counted `other * 4,220` as credits spent for nothing -- but
        `other` is mostly the FREE classes (a stall, a rejection), so it overstated our own spend.
        Asking is_billed() is the only way that cannot drift from the billing partition itself.
        """
        c = c or "unknown"
        if c == "ok":
            return ok + 1, empty, other, billed_no_data
        if is_billed(c):
            billed_no_data += 1
        if c == "completed_but_empty":
            return ok, empty + 1, other, billed_no_data
        return ok, empty, other + 1, billed_no_data

    # ---- source 1: the live agent's per-run spend ledger -------------------------------
    try:
        doc = json.load(open(os.path.join(results_dir, "live_spend.json"), encoding="utf-8"))
    except (ValueError, OSError):
        doc = None
    if doc:
        seen = 0
        for run in doc.get("runs", []):
            t = _stamp(run.get("utc"))
            if t is None or t < cut:
                continue
            latest = max(latest or t, t)
            for w in run.get("windows", []):
                seen += 1
                ok, empty, other, billed_no_data = _tally(
                    w.get("class"), ok, empty, other, billed_no_data)
        if seen:
            sources.append("live runs (%d windows)" % seen)

    # ---- source 2: the N-26 collector's per-attempt log --------------------------------
    # Only the per-attempt log is read, never the legacy integer counter: the counter carries no
    # timestamp, so folding it in would report a four-day-old failure as recent.
    try:
        man = json.load(open(os.path.join(results_dir, "n26_manifest.json"), encoding="utf-8"))
    except (ValueError, OSError):
        man = None
    if man:
        seen = 0
        for day in (man.get("days") or {}).values():
            for r in (day.get("forecast_attempt_log") or []):
                t = _stamp(r.get("at_utc"))
                if t is None or t < cut:
                    continue
                latest = max(latest or t, t)
                seen += 1
                ok, empty, other, billed_no_data = _tally(
                    r.get("class"), ok, empty, other, billed_no_data)
        if seen:
            sources.append("collector attempts (%d)" % seen)

    n = ok + empty + other
    if not n:
        return None
    return {"window_hours": hours_back, "windows_seen": n, "returned_a_field": ok,
            "completed_but_empty": empty, "other_failures": other,
            "success_rate": round(ok / float(n), 4),
            "sources": sources,
            "last_run_utc": (datetime.fromtimestamp(latest, timezone.utc).isoformat()
                             if latest else None),
            "billed_but_no_data": billed_no_data,
            "credits_spent_for_nothing": billed_no_data * HEATMAP_CREDITS,
            "advice": ("The vendor has returned a field for %d of the last %d windows. A full "
                       "12-hour horizon would cost up to %s credits and, at that rate, would very "
                       "likely buy nothing. `completed`-with-no-data IS billed."
                       % (ok, n, format(12 * HEATMAP_CREDITS, ",")))
                      if ok * 4 < n else
                      ("The vendor has answered %d of the last %d windows." % (ok, n))}


def assert_non_empty(result):
    """FortyGuard returns status=completed with zero tiles for out-of-range requests.
    Never treat that as data. (Measured defect.)"""
    if not result:
        return False, "no result"
    feats = result.get("map_data", {}).get("features")
    if feats is not None:
        if not feats:
            return False, "ZERO TILES with completed status"
        return True, "%d tiles" % len(feats)
    if result.get("locations"):
        return True, "%d locations" % len(result["locations"])
    return False, "unrecognised shape"
