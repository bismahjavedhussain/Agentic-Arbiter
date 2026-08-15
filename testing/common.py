# -*- coding: utf-8 -*-
"""Shared helpers for the INTAKE test suite.

Nothing here spends credits. The API client is used only by the paid tests,
and every response it returns is written to results/fixtures/ so the rest of
the suite (and the demo) can run offline.
"""
import json, math, os, sys, time, urllib.request, statistics

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

# Fields already captured in earlier work — reused so we do not pay twice.
SCRATCH = os.path.join(
    os.environ.get("TEMP", r"C:\Users\bisma\AppData\Local\Temp"),
    "claude", "d--FGHackathon", "48b2e995-a9e0-4f0c-8ab4-8cbe4f628a17", "scratchpad")

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
# Established 2026-08-12 from data already on disk, at zero cost, by two independent arguments:
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
    for base in (SCRATCH, FIXTURES, HERE):
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
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8-sig"):
        if line.strip().startswith("FORTYGUARD_API_KEY"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("FORTYGUARD_API_KEY not found in .env")


V1 = "https://api.fortyguard.com/v1"


def _headers(key):
    return {"api-key": key, "Content-Type": "application/json"}


def credits_remaining(key):
    req = urllib.request.Request(f"{V1}/system/fetch-api-key-usage",
                                data=json.dumps({"api_key": key}).encode(),
                                headers=_headers(key))
    d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return d["credit_summary"]["cycle_remaining_credits"]


def submit_poll(key, endpoint, payload, tag, max_s=420, wait=8):
    """Submit, poll to completion, save the raw response as a fixture."""
    t0 = time.time()
    try:
        req = urllib.request.Request(f"{V1}/{endpoint}",
                                     data=json.dumps(payload).encode(), headers=_headers(key))
        resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
    except Exception as e:
        return {"error": "submit: %s" % str(e)[:200]}
    aid = resp.get("data", {}).get("activity_id")
    while time.time() - t0 < max_s:
        try:
            j = urllib.request.urlopen(
                urllib.request.Request(f"{V1}/status/{aid}", headers=_headers(key)), timeout=90)
        except Exception:
            time.sleep(wait); continue
        if j.status == 404:                       # documented grace window right after submit
            time.sleep(wait); continue
        jd = json.loads(j.read())
        st = str(jd.get("data", {}).get("status") or jd.get("message")).lower()
        if st == "completed":
            res = jd["data"]["result"]
            with open(os.path.join(FIXTURES, "%s.json" % tag), "w") as f:
                json.dump(res, f, default=str)
            return {"ok": True, "aid": aid, "secs": round(time.time() - t0, 1), "result": res}
        if st in ("processing", "pending", "queued", "in progress"):
            time.sleep(wait); continue
        return {"error": st, "aid": aid, "secs": round(time.time() - t0, 1)}
    return {"error": "timeout", "aid": aid}


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
