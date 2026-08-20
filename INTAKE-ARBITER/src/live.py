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
from common import load_key, credits_remaining, box_aoi, V1   # noqa: E402

HORIZON_H = 12
SIDE_KM = 8.0
GRAN = 60
ANALYTIC = "tcm"
HEATMAP_CREDITS = 4_220
POLL_MAX_S = 300
POLL_WAIT_S = 8
DAILY_HEATMAP_CAP = 30
# A live AOI is built around the site's own centre, so its nearest tile is tens of metres away.
# Anything past this means the field belongs to a different place.
MAX_TILE_DIST_M = 2_000

NWS_UA = {"User-Agent": "INTAKE-ARBITER/1.0 (FortyGuard Hackathon 2026; free-cooling agent)",
          "Accept": "application/geo+json"}

CACHE = os.path.join(M.ROOT, "data", "live_cache")


def say(*a):
    print(*a, flush=True)


# ============================================================================
# 1. THE VENDOR, CLASSIFIED -- four outcomes, not "worked / didn't"
# ============================================================================
def classify_vendor(rec):
    """What actually happened to one heatmap request.

    A STALL IS NOT A FAILURE and neither is a rejection. DIAG-63's first version collapsed all of
    them to "fail", which reads as "the vendor said no" -- when in fact the vendor said HTTP 200,
    issued an activity id, answered 45 status polls, and simply never finished the job. Different
    fault, different owner, different message to the operator.
    """
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


def cache_path(metro, dt_fields):
    d = os.path.join(CACHE, metro)
    os.makedirs(d, exist_ok=True)
    nm = "%s_%s-%s_g%d_%s.json" % (dt_fields["start_date"],
                                   dt_fields["start_time"].replace(":", ""),
                                   dt_fields["end_time"].replace(":", ""),
                                   GRAN, ANALYTIC)
    return os.path.join(d, nm)


def fetch_window(key, aoi, dt_fields, metro, allow_paid, want_latlon, replay=None):
    """One heatmap window -> the value at the site's own tile, or a vendor-state record.

    Returns (value_c, record). `value_c is None` means no data, and `record["class"]` says why.
    A cache hit costs nothing and is byte-identical to a fresh call (N-55).
    """
    # ---- REPLAY: a saved REAL FortyGuard response, used to verify the decide path offline.
    # 🔴 THIS IS NOT A FALLBACK AND MUST NEVER BECOME ONE. It is reachable only when a caller
    # passes `replay=` explicitly, it never fires because a live call failed, and every output it
    # produces is stamped `mode: replay-verification` plus a `NOT_LIVE` banner. The reason to be
    # this careful: the difference between a test harness and a lie is whether the artefact can be
    # mistaken for the real thing, and a silent cache-seed would have been exactly that.
    if replay:
        res = json.load(open(replay, encoding="utf-8"))
        res = res.get("result", res)
        tile, dist = A.nearest_tile(res, want_latlon[0], want_latlon[1])
        # 🔴 A FIXTURE FROM ANOTHER METRO IS NOT A VALID REPLAY, and `nearest_tile` will not
        # tell you: it returns the closest tile it has, so replaying Ashburn's field for Chicago
        # silently picks an Ashburn EDGE tile ~900 km from the plant and reports a temperature for
        # it. That is precisely the "one site's data wearing another site's label" fault this whole
        # rework exists to remove, so the distance is checked rather than assumed. A real live call
        # builds the AOI around the site's own centre, so its distance is always tens of metres.
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
        return None, {"source": "would-call", "class": "not_attempted",
                      "credits_if_called": HEATMAP_CREDITS}

    payload = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": ANALYTIC,
               "date_time": dt_fields}
    rec = {"source": "live", "window": dt_fields}
    t0 = time.time()
    try:
        req = urllib.request.Request("%s/heatmap" % V1, data=json.dumps(payload).encode(),
                                     headers={"api-key": key, "Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
        rec["submit_http"] = 200
    except urllib.error.HTTPError as e:
        rec.update({"submit_http": e.code,
                    "submit_error_body": e.read().decode("utf-8", "replace")[:400]})
        rec["class"] = classify_vendor(rec)
        return None, rec
    except Exception as e:
        rec.update({"submit_http": None, "submit_exception": str(e)[:300]})
        rec["class"] = classify_vendor(rec)
        return None, rec

    aid = (resp.get("data") or {}).get("activity_id")
    rec["activity_id"] = aid
    if not aid:
        rec["class"] = classify_vendor(rec)
        return None, rec

    seen, polls, terminal, result = set(), 0, None, None
    while time.time() - t0 < POLL_MAX_S:
        polls += 1
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                "%s/status/%s" % (V1, aid), headers={"api-key": key}), timeout=90)
            jd = json.loads(r.read())
        except Exception:
            time.sleep(POLL_WAIT_S)
            continue
        st = str((jd.get("data") or {}).get("status") or jd.get("message") or "?").lower()
        seen.add(st)
        if st == "completed":
            res = (jd.get("data") or {}).get("result") or {}
            feats = (res.get("map_data") or {}).get("features")
            if feats:
                terminal, result = "completed", res
                break
            terminal = "completed"          # complete-but-empty: keep polling, per FortyGuard
            time.sleep(POLL_WAIT_S)
            continue
        if st in ("failed", "error", "cancelled", "canceled", "expired"):
            terminal = st
            break
        time.sleep(POLL_WAIT_S)

    rec.update({"polls": polls, "elapsed_s": round(time.time() - t0, 1),
                "statuses_seen": sorted(seen), "terminal_status": terminal,
                "tiles": len((result or {}).get("map_data", {}).get("features") or [])
                if result else 0})
    rec["class"] = classify_vendor(rec)
    if rec["class"] != "ok":
        return None, rec

    # allow_nan=False, and not as a formality: `NaN` is legal Python JSON and ILLEGAL standard
    # JSON, so a cached field carrying one would load fine here and kill the browser silently
    # (audit check 2). If FortyGuard ever returns a non-finite value, this raises at write time --
    # which is where a bad value should stop, not three stages downstream.
    json.dump({"result": result, "window": dt_fields, "granularity": GRAN,
               "analytic_type": ANALYTIC, "fetched_utc": _utcnow().isoformat()},
              open(cp, "w", encoding="utf-8"), default=str, allow_nan=False)
    tile, dist = A.nearest_tile(result, want_latlon[0], want_latlon[1])
    rec["tile_dist_m"] = round(dist, 1)
    return tile[2], rec


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
             replay=None, on_progress=None):
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
    start_local = (now_local + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    start_utc = start_local.astimezone(timezone.utc)

    centre = trace["site"]["centre"]
    aoi = box_aoi(centre[0], centre[1], SIDE_KM)
    # The site's own tile, not the AOI mean: 8x8 km of Ashburn spans 1.45 C, so a mean would
    # describe the corridor and not the plant.
    want_latlon = (centre[0], centre[1])

    out = {
        "generated_by": "INTAKE-ARBITER/src/live.py",
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
    windows, temps, recs = [], [], []
    for i in range(hours):
        w = window_fields(start_local + timedelta(hours=i), 1)
        windows.append(w)
        v, rec = fetch_window(key, aoi, w, metro, allow_paid, want_latlon, replay=replay)
        temps.append(v)
        recs.append(rec)
        if verbose:
            say("      h+%-2d  %s %s  ->  %s  [%s]"
                % (i + 1, w["start_date"], w["start_time"],
                   ("%.4f C" % v) if v is not None else "no data", rec.get("class")))
        # A live run can sit for 300 s on ONE window while the vendor decides whether to answer.
        # Without a progress hook the caller has no way to distinguish "working" from "hung", and a
        # browser showing a dead spinner for ten minutes is indistinguishable from a broken page.
        if on_progress:
            on_progress({"stage": "perceive", "hour_index": i, "of_hours": hours,
                         "window": w, "value_c": v, "class": rec.get("class"),
                         "source": rec.get("source")})
    after = credits_remaining(key) if allow_paid else None
    out["spend"] = {"credits_before": before, "credits_after": after,
                    "credits_spent": (before - after) if (before and after) else 0,
                    "calls_attempted": sum(1 for r in recs if r.get("source") == "live"),
                    "cache_hits": sum(1 for r in recs if r.get("source") == "cache"),
                    "note": "cache hits are byte-identical to fresh calls -- N-55"}
    out["windows"] = [{"window": w, **{k: v for k, v in r.items() if k != "window"}}
                      for w, r in zip(windows, recs)]

    got = [i for i, t in enumerate(temps) if t is not None]
    if not got:
        # WHY there is no data decides what to TELL the operator, and the three reasons are not
        # interchangeable. An earlier version reported every one of them as "dryrun" whenever
        # --paid was absent, so a fixture-mismatch refusal was announced as a costing estimate.
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

    amb = np.array([t if t is not None else np.nan for t in temps], dtype=float)
    bound = amb + rise + float(margin)
    dewp = np.array([h["dewpoint_c"] if h["dewpoint_c"] is not None else np.nan
                     for h in nws["hours"]], dtype=float)

    # Both gates, and a refused bearing is NOT a free-cooling hour: the solver declining to answer
    # is not permission. NaN (a missing hour) is likewise never safe.
    # BOTH GATES, and three separate reasons an hour is NOT free-cooling. Kept as named arrays
    # rather than one expression, because each one is reported to the operator separately and a
    # reader has to be able to see which gate bit.
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
    safe = gate_dry & gate_dp & dp_known & bound_known & ~refused_arr

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
            "lead_h": i + 1,
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
        out["NOT_LIVE"] = (
            "REPLAY VERIFICATION. The ambient trajectory came from a SAVED FortyGuard response "
            "(%s), reused for every hour of the horizon, so the schedule below proves the "
            "solve/bound/decide/act chain and is NOT a forecast of the hours it names. Wind and "
            "dew point ARE live. Nothing in the demo may present this as a live run."
            % os.path.basename(replay))
    return out


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
                   cfg={"limit_c": a.limit_c}, replay=a.replay)
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
