# -*- coding: utf-8 -*-
"""SERVE_LIVE -- serves demo/ and exposes the live agent, with the API key never leaving this process.

    python serve_live.py                      # replay + dryrun only. Spends nothing. Safe default.
    python serve_live.py --allow-paid         # permits live FortyGuard calls from the browser
    python serve_live.py --allow-paid --port 8000 --max-live-calls 24

Then open http://127.0.0.1:8000.

WHY A SERVER AT ALL
-------------------
The demo is a single static HTML file and that is deliberate: no build step, no dependencies, and a
judge can host it anywhere. But a static page **cannot make a live FortyGuard call**, for one
unarguable reason: the request needs the API key, and anything the page can read, every visitor can
read. Putting the key in `index.html` publishes it. There is no clever way around this -- an API
that authenticates with a bearer secret cannot be called from an untrusted client, full stop.

So the live path runs here. The browser POSTs to `/api/live/<site>`, this process reads the key via
`testing/common.py:load_key()`, calls FortyGuard, and returns **only the resulting numbers**. The
key never appears in a response body, a URL, a log line or an error message.

That split keeps both properties:

  * **GitHub Pages still works** -- serving `demo/` as static files gives the REPLAY-only demo, with
    every panel and every proof intact. `/api/*` simply 404s and the page falls back.
  * **Running locally gives the genuine live agent**, because the key is on the machine that has it.

THREE SAFETY DECISIONS, EACH ONE DELIBERATE
-------------------------------------------
1. **Binds to 127.0.0.1, not 0.0.0.0.** This process holds a capability that spends money. A server
   that can be made to spend credits must not be reachable from the network by default; `--host` can
   override it, and the banner says so out loud when it is used.
2. **Refuses to spend unless BOTH the server was started with `--allow-paid` AND the request asks
   for it.** A page reload must never cost 50,640 credits. Without the flag every request is served
   as a `dryrun`, which returns the exact costing and calls nothing.
3. **A hard per-process cap on live calls** (`--max-live-calls`, default 24). The plan's real limit
   is 30 heatmaps/day; a runaway loop in a browser could burn that in a minute. When the cap is hit
   the answer is an explicit refusal, not a silent switch to cached data.

WHY THE JOB IS ASYNCHRONOUS
---------------------------
One hourly window can take 300 s, because that is how long FortyGuard is given to answer before this
gives up. A 12-hour horizon is therefore up to an hour of wall-clock, and no browser `fetch()`
survives that. So the API mirrors FortyGuard's own shape:

    POST /api/live/<site>        -> {"job_id": ...}    returns immediately
    GET  /api/live/job/<job_id>  -> {"state": "running"|"done"|"error", "progress": [...], ...}

The progress list is what the page streams, so "the agent is working" is a real status line fed by
real stage events -- not a spinner with a timer behind it.
"""
import argparse
import importlib
import json
import os
import sys
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live as LV                     # noqa: E402
import metros as M                    # noqa: E402

DEMO = os.path.join(M.ROOT, "demo")

# 🔴 THE MTIME OF live.py AS THIS PROCESS LOADED IT.
# Python caches imported modules, so a long-running server keeps executing the code it started
# with. That cost real diagnostic time: a screenshot showed the OLD partial-horizon wording hours
# after the fix had been written, and the natural conclusion was that the fix had not worked. It had;
# the server was stale. `/api/health` now reports both mtimes so the page can say so out loud
# instead of leaving a reader to compare timestamps by hand.
LIVE_PY = os.path.join(HERE, "live.py")
SELF_PY = os.path.abspath(__file__)
LOADED_MTIME = os.path.getmtime(LIVE_PY)
SELF_MTIME = os.path.getmtime(SELF_PY)
RELOADS = 0


def restart_if_self_stale():
    """Re-exec this process when serve_live.py itself changes. Returns True if a job blocks it.

    🔴 THE AUTO-RELOAD FIXED HALF THE PROBLEM AND I REPORTED IT AS FIXED. `reload_if_stale` reloads
    `live.py`, but **a module cannot meaningfully reload its own `__main__`** -- so an edit to THIS
    file kept being ignored, and the symptom was indistinguishable from the bug it was supposed to
    have fixed: a truncation branch that lived here never ran, while `live.py`'s truncation code sat
    loaded and unreachable because the old code here still set `paid = False` first.

    So this file re-execs instead of reloading:
      * **only when no job is running**, because re-execing would abandon an in-flight run;
      * **carrying the call log forward in the environment**, so restarting does not silently reset
        the spend cap -- a safety counter that resets on every code edit is not a cap.
    """
    try:
        m = os.path.getmtime(SELF_PY)
    except OSError:
        return False
    if m <= SELF_MTIME + 1:
        return False
    with LOCK:
        busy = any(j.get("state") == "running" for j in JOBS.values())
        log = ",".join("%.0f" % t for t in CALL_LOG)
    if busy:
        return True                      # caller reports "restart pending"
    sys.stderr.write("   serve_live.py changed on disk -- re-executing (carrying %d calls "
                     "used today)\n" % calls_today())
    os.environ["SERVE_LIVE_CALL_LOG"] = log

    # DEFERRED BY HALF A SECOND, so the request that TRIGGERED the restart still gets an answer.
    # Calling execv inline replaced the process mid-response: the browser saw a dead socket, and a
    # self-healing restart that looks like a network failure is not an improvement on a stale banner.
    def _exec():
        time.sleep(0.5)
        sys.stdout.flush()
        sys.stderr.flush()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_exec, daemon=True).start()
    return False


def reload_if_stale():
    """Re-import live.py when it changes on disk. Returns True if a reload happened.

    A STALENESS WARNING IS A WORKAROUND; THIS IS THE FIX. Reporting `code_is_stale` was correct but
    it put the work on the operator: every edit meant noticing a red banner and restarting by hand,
    and the one time that was missed it cost a whole diagnostic cycle -- a screenshot showed pre-fix
    wording 48 minutes after the fix, which reads exactly like "the fix did not work".

    `importlib.reload` refreshes the module object IN PLACE, so:
      * every later `LV.<name>` lookup gets the new code, and
      * a job thread already holding a reference to the old `live_run` function keeps running it to
        completion rather than being torn out mid-flight.
    Both of those are what we want. `live.py` holds no mutable module state -- only constants and
    functions -- so there is nothing to migrate across a reload.
    """
    global LOADED_MTIME, RELOADS
    try:
        m = os.path.getmtime(LIVE_PY)
    except OSError:
        return False
    if m <= LOADED_MTIME + 1:
        return False
    with LOCK:
        if m <= LOADED_MTIME + 1:          # another thread got there first
            return False
        LOADED_MTIME, RELOADS = m, RELOADS + 1
    importlib.reload(LV)
    sys.stderr.write("   live.py changed on disk -- reloaded (reload #%d)\n" % RELOADS)
    return True

# ---- process state. Guarded by a lock because ThreadingHTTPServer serves concurrently and the
# call counter is the thing standing between a browser loop and the daily cap.
JOBS = {}
LOCK = threading.Lock()
# THE CAP IS A ROLLING DAILY WINDOW, NOT A PER-PROCESS TOTAL.
# A per-process counter that only ever increases made the agent permanently unrunnable once it was
# spent -- the user hit exactly that: "already made 3 of its 3 permitted live calls". But the
# constraint being modelled is the VENDOR'S, and that is 30 heatmaps PER DAY. So calls are logged
# with timestamps and only those since UTC midnight count, so the budget clears by itself the way
# the real quota does. Carried across a self-restart so a code edit cannot silently reset it.
CALL_LOG = [float(t) for t in (os.environ.get("SERVE_LIVE_CALL_LOG") or "").split(",") if t]
CONF = {"allow_paid": False, "max_live_calls": 24}


def _utc_midnight():
    n = time.gmtime()
    return time.time() - (n.tm_hour * 3600 + n.tm_min * 60 + n.tm_sec)


def calls_today():
    cut = _utc_midnight()
    return sum(1 for t in CALL_LOG if t >= cut)


def record_calls(n):
    now = time.time()
    with LOCK:
        CALL_LOG.extend([now] * n)
        CALL_LOG[:] = [t for t in CALL_LOG if t >= _utc_midnight()]


def _json(handler, obj, code=200):
    body = json.dumps(obj, default=str, allow_nan=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    # No caching: a live answer is about a moment, and a cached one would be a lie about when.
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


# (mtime, keys) as ONE tuple, deliberately. ThreadingHTTPServer answers requests on many threads, and
# two separate stores would let a reader see the NEW mtime beside the OLD keys. A single name rebound
# to a single tuple cannot be observed half-updated. No lock needed for that reason.
_SITES_CACHE = (None, ())


def offerable_sites():
    """Which sites the interface may offer, cached on `sites.json`'s mtime.

    🔴 WHY THIS IS CACHED. `health()` calls this, and it used to re-parse the whole file every time.

    MEASURED: parsing the 784,300-byte `sites.json` costs **8.40 ms median on a full core** (40 runs,
    2026-08-28), so roughly 84 ms on the free instance's 0.1 CPU. Cached it is 0.0356 ms, 220x faster.

    NOT MEASURED, and an earlier version of this comment wrongly stated it as if it were: the health
    check INTERVAL. render.com/docs/health-checks says only *"Every few seconds, Render sends health
    checks"* and publishes no number. So the cost is a range, not the single figure that was here:

        every 3 s   ->  28,800 polls/day,  2,419 CPU-seconds/day,  2.80 % of 0.1 CPU
        every 10 s  ->   8,640 polls/day,    726 CPU-seconds/day,  0.84 % of 0.1 CPU

    Whatever the true cadence, it is CONTINUOUS while the instance is up (the docs describe checks on
    "actively running services", not only on deploys), and it dwarfs a keep-alive ping: one every 10
    minutes is 144 calls and 12.1 CPU-seconds a day, 0.01 % of CPU.

    🔴 AND THE FAILURE MODE IS DOCUMENTED, WHICH IS WHY THIS IS MORE THAN TIDINESS.
    render.com/docs/health-checks: *"If a running service instance fails consecutive health checks for
    15 seconds, Render temporarily stops routing traffic to it"*, and at 60 seconds it *"automatically
    restarts the instance"*. Traffic stopped at the edge is exactly the intermittent
    `x-render-routing: no-server` 404 observed on 2026-08-28, interleaved with 200s. A health check
    that has to parse 784 KB on a tenth of a CPU, while a visitor is pulling a 2.9 MB page through the
    same tenth, is a plausible way to miss 15 seconds of checks. Hence both this cache and the
    12-byte `/api/ping` that the check should point at instead.

    MTIME AND NOT A TTL, because the answer is a pure function of the file: `build_sites.py` rewrites
    `sites.json` and the mtime moves, so a stale answer cannot outlive the file that produced it. A
    TTL would be both slower to notice a change and pointless work when nothing changed.

    Returns a fresh list each time, so a caller cannot mutate the cache from underneath the next one.
    """
    global _SITES_CACHE
    p = os.path.join(DEMO, "sites.json")
    try:
        m = os.path.getmtime(p)
    except OSError:
        return []
    mtime, keys = _SITES_CACHE
    if mtime == m:
        return list(keys)
    try:
        s = json.load(open(p, encoding="utf-8"))
        keys = tuple(x["key"] for x in s["sites"] if x.get("offerable"))
    except (OSError, ValueError, KeyError):
        return []
    _SITES_CACHE = (m, keys)
    return list(keys)


def health():
    """What the page needs to decide whether to offer a LIVE button at all.

    Deliberately does NOT report the credit balance: reading it is a network call to FortyGuard, and
    a health check that hits the vendor is a health check that fails when the vendor does.
    """
    reload_if_stale()       # the docstring must stay FIRST or it is not a docstring at all
    restart_pending = restart_if_self_stale()
    used = calls_today()
    key_present = False
    try:
        # Existence only. The value is never read into a variable that leaves this function, never
        # logged, and never returned.
        key_present = bool(LV.load_key())
    except Exception:
        key_present = False
    return {
        "live_available": bool(CONF["allow_paid"] and key_present),
        "paid_enabled": bool(CONF["allow_paid"]),
        "key_present": key_present,
        "live_calls_made": used,
        "live_calls_window": "since 00:00 UTC -- this budget clears daily, like the vendor's own",
        "max_live_calls": CONF["max_live_calls"],
        "credits_per_call": LV.HEATMAP_CREDITS,
        "daily_vendor_cap": LV.DAILY_HEATMAP_CAP,
        "sites": offerable_sites(),
        "why_not_live": None if (CONF["allow_paid"] and key_present) else (
            "no API key on this machine" if not key_present else
            "server started without --allow-paid, so every request is served as a costed dry run"),
        "note": "the API key never leaves the server process. The browser receives numbers only.",
        # What the vendor has actually done lately, so a click that could spend 50,640
        # credits is made with the recent success rate visible rather than blind.
        "vendor_recent": LV.recent_vendor_record(),
        "code_loaded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(LOADED_MTIME)),
        "code_on_disk_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime(os.path.getmtime(LIVE_PY))),
        "code_is_stale": os.path.getmtime(LIVE_PY) > LOADED_MTIME + 1,
        "code_reloads": RELOADS,
        "server_code_restart_pending": bool(restart_pending),
        "server_code_note": ("serve_live.py changed on disk and a job is in flight, so the restart "
                             "is deferred. It will re-exec once the job finishes."
                             if restart_pending else None),
        "stale_note": ("live.py has changed on disk since this server started -- RESTART IT. "
                       "Python caches imported modules, so this process is still running the old "
                       "code.") if os.path.getmtime(LIVE_PY) > LOADED_MTIME + 1 else None,
    }


def start_job(site, hours, limit_c, want_paid, replay):
    """Kick off a live run on a worker thread and return its id immediately."""
    # A run must never execute code older than the request that asked for it -- both files.
    reload_if_stale()
    restart_if_self_stale()
    jid = uuid.uuid4().hex[:12]

    paid = bool(want_paid and CONF["allow_paid"])
    refusal = None
    if want_paid and not CONF["allow_paid"]:
        refusal = ("This server was started without --allow-paid, so it will not spend credits. "
                   "Serving a costed dry run instead -- the numbers below are what it WOULD fetch.")
    # 🔴 THE CAP MUST COUNT CALLS, NOT HOURS. It checked `LIVE_CALLS_MADE + hours`, so a 12-hour
    # request was costed as 12 calls even when 11 windows were already cached -- which refused runs
    # that needed a single call, and over-incremented the counter on the runs it allowed. A cached
    # window costs nothing and must not consume a budget.
    #
    # The remaining allowance is passed INTO the run as `max_calls`, so the budget is enforced where
    # the calls happen rather than guessed at up front, and the counter is reconciled afterwards
    # against the number actually made.
    needed = 0
    if paid:
        try:
            _, plan_w = LV.horizon_windows(site, hours, LV.site_local_now(
                next((x["tz"] for x in json.load(open(os.path.join(DEMO, "sites.json"),
                                                          encoding="utf-8"))["sites"]
                      if x["key"] == site), "America/New_York")))
            needed = sum(1 for p in plan_w if not p["cached"])
        except Exception:
            needed = hours          # cannot cost it: assume the worst rather than under-refuse
        allowance = max(0, CONF["max_live_calls"] - calls_today())
        if allowance <= 0:
            # EXHAUSTED IS NOT A REASON TO REFUSE EITHER. This branch used to set paid=False,
            # which passed max_calls=None and so BYPASSED the truncation entirely -- producing the
            # exact "NO SCHEDULE, 11 of 12 hours NEVER REQUESTED" wall of text the truncation was
            # written to remove. A zero budget still permits every CACHED window, so the horizon
            # truncates to the cached prefix and a short honest schedule comes back instead.
            refusal = ("Budget note: %d of %d live calls already used today; this budget clears at "
                       "00:00 UTC, mirroring the vendor's %d heatmaps/day. No new calls are "
                       "available, so the horizon covers only what is already cached -- and every "
                       "hour reported was genuinely perceived."
                       % (calls_today(), CONF["max_live_calls"], LV.DAILY_HEATMAP_CAP))
        elif needed > allowance:
            # NOT A REFUSAL ANY MORE -- A SHORTER HORIZON. Refusing the whole run was safe but
            # unusable: with 9 calls left and 11 needed the agent simply could not be run. live_run
            # now truncates the horizon to the longest prefix the budget covers, so no hour inside
            # it is unlooked-at. This message explains the shortening rather than announcing a
            # failure, because a complete 10-hour decision is a better answer than none.
            refusal = ("Budget note: the full %d-hour horizon needs %d live call(s) (%d already "
                       "cached) and %d remain of this process's %d-call cap, so the horizon has "
                       "been SHORTENED to what the budget covers. Every hour reported was actually "
                       "perceived -- none are left unlooked-at."
                       % (hours, needed, hours - needed, allowance, CONF["max_live_calls"]))

    with LOCK:
        JOBS[jid] = {"state": "running", "site": site, "hours": hours, "paid": paid,
                     "started": time.time(), "progress": [], "result": None, "error": None,
                     "refusal": refusal}

    def work():
        def prog(ev):
            with LOCK:
                j = JOBS.get(jid)
                if j is not None:
                    j["progress"].append(dict(ev, at_s=round(time.time() - j["started"], 1)))
        try:
            out = LV.live_run(metro=site, hours=hours, allow_paid=paid, verbose=False,
                              cfg={"limit_c": limit_c}, replay=replay, on_progress=prog,
                              max_calls=(allowance if paid else None))
            # RECONCILE against what actually happened, rather than trusting the estimate. The
            # counter now moves by the calls the run really made.
            made = int((out.get("spend") or {}).get("calls_attempted") or 0)
            if made:
                record_calls(made)
            with LOCK:
                JOBS[jid].update({"state": "done", "result": out, "live_calls_made": made})
        except SystemExit as e:
            with LOCK:
                JOBS[jid].update({"state": "error", "error": str(e)})
        except Exception as e:
            with LOCK:
                JOBS[jid].update({"state": "error",
                                  "error": "%s: %s" % (type(e).__name__, str(e)[:400])})

    threading.Thread(target=work, daemon=True).start()
    return jid


class Handler(SimpleHTTPRequestHandler):
    """Static files from demo/, plus /api/*. Everything else behaves exactly as http.server does."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DEMO, **kw)

    def end_headers(self):
        """Make static artefacts REVALIDATE. `SimpleHTTPRequestHandler` sends no `Cache-Control` at
        all, so a browser falls back to heuristic freshness and may serve `demo/*.json` from memory
        long after the file changed on disk.

        Measured 2026-08-25, and it wasted a round trip diagnosing a bug that did not exist: an edit
        to `index.html` was picked up (browsers revalidate the top-level document on reload) while
        `trace.json` was not, so the page rendered the NEW prose around a field the OLD artefact did
        not have -- and because that clause and a whole paragraph are guarded on the field being
        present, both silently vanished. The page looked broken and was correct; the server was
        serving 0.962 the whole time.

        `no-cache` means "revalidate before reuse", NOT "do not store" -- the answer is usually a
        304 with no body, so this costs a request header and buys away a class of phantom bug.
        `/api/*` sets its own `no-store` in `_json` and is left alone, which keeps this stateless:
        no per-request flag to reset on a keep-alive connection.
        """
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        # Quieter than the default, and -- more importantly -- this is the only place a request line
        # is written anywhere. Query strings are truncated so a stray parameter cannot be logged.
        line = (self.requestline or "")[:120]
        sys.stderr.write("   %s %s\n" % (self.address_string(), line))

    def _unprefix_api(self):
        """`/app/api/...` is the same route as `/api/...`. Rewrite it. Returns True if it did.

        🔴 THIS IS WHY THE LIVE AGENT WAS DEAD ON THE DEPLOYED SITE, and the cause is one missing
        prefix in code that cannot be edited. `probeLive()` in results/engine.mjs:2077 does:

            const r = await fetch('api/health', {cache:'no-store'});

        A BARE RELATIVE PATH, with no `ART`. On demo/index.html, served from demo/, that resolves to
        `/api/health` and works. The React app is served from demo/app/, so the browser resolves the
        same string against `/app/` and asks for **`/app/api/health`**, which `do_GET` does not
        recognise as an API route at all: it does not start with `/api/`. So it fell through to the
        static handler, 404d, `HEALTH` became null, and `drawLiveUnavailable()` disabled `#livego` and
        labelled it "Live agent not attached". Measured against the live host: `/api/health` 200,
        `/app/api/health` 404.

        Three routes were affected, not one: `api/health`, `api/live/<site>` (the POST that starts a
        run, engine.mjs:2229) and `api/live/job/<id>` (the poll, engine.mjs:2239).

        WHY NOT FIX IT IN THE ENGINE. run_all.py step 30 asserts results/engine.mjs is character for
        character the code inside demo/index.html, and that identity is what makes the React rebuild
        trustworthy. Adding a prefix there would end it. So the server accepts both spellings, exactly
        as `_app_artefact_fallback` already does for the artefacts, which failed to catch this because
        it only rewrites paths that resolve to a real FILE and these are routes.

        NO NEW CAPABILITY. It strips a known prefix and hands the request to the same handlers, which
        keep their own checks: `do_POST` still refuses a site that is not offerable, `--allow-paid` is
        still required before anything is spent, and the per-process cap still applies.
        """
        p, _, q = self.path.partition("?")
        if not p.startswith("/app/api/"):
            return False
        self.path = p[len("/app"):] + (("?" + q) if q else "")
        return True

    def _app_artefact_fallback(self):
        """An `/app/<name>` the bundle does not have falls back to `demo/<name>`. Returns True if the
        path was rewritten.

        🔴 WITHOUT THIS THE DEPLOYED APP CANNOT LOAD A SINGLE SITE, and the failure names the wrong
        cause. `loadSite()` in results/engine.mjs fetches every artefact by the BARE filename that
        sites.json's `artefacts` map gives it -- `trace.json`, `backtest.json`, `money.json`, the
        plume field -- because the engine is lifted byte for byte out of demo/index.html, which is
        served FROM demo/ where a bare name resolves. The React app is served from demo/app/, one
        level down, so the browser resolves those same names against /app/ and every one of them
        404s. `loadSite` returns false on a missing trace, so the app reports "No built artefacts for
        <site>" for EVERY site, and the Configure button does nothing because the transition it
        starts rejects. Measured on the live host 2026-08-28, and reported by the user.

        WHY THE FIX IS HERE AND NOT IN THE ENGINE. The engine must stay byte-identical to the page:
        run_all.py step 30 asserts it character for character, and that identity is what makes the
        React rebuild safe to trust at all. Prefixing the fetches would break it. React's own code
        already carries `ART = '../'` for the artefacts IT reads (app/src/lib/artefacts.ts); the
        engine cannot, so the server closes the gap instead.

        THIS IS EXACTLY WHAT testing/serve_app.py ALREADY DID, and that is the whole reason the bug
        shipped. Its comment says an /app/ path "tries the bundle first and then demo/, because the
        app's own assets and the artefacts live in different places". The browser flow check drove the
        app through that server, the fallback made every fetch succeed, and the check passed while
        production had no such fallback. The harness did not reproduce production. Trap 5b.7.

        PATH TRAVERSAL IS NOT POSSIBLE HERE. Both candidates go through `translate_path`, which
        collapses `..`, drops leading slashes and anchors the result under `directory=DEMO`, so
        `/app/../../.env` cannot resolve outside demo/. The rewrite only ever REMOVES the `/app`
        prefix; it never joins attacker-controlled text to a filesystem path itself.
        """
        raw = self.path
        p, _, q = raw.partition("?")
        if not p.startswith("/app/") or p.endswith("/"):
            return False
        if os.path.isfile(self.translate_path(p)):
            return False                          # the bundle has it: its own js, css, index.html
        alt = "/" + p[len("/app/"):]
        if not os.path.isfile(self.translate_path(alt)):
            return False                          # neither has it, so let the honest 404 happen
        self.path = alt + (("?" + q) if q else "")
        return True

    def _root_redirect(self):
        """Shared by GET and HEAD so a monitor configured for HEAD sees the same routing. Returns True
        when it has answered the request."""
        if self.path.split("?")[0] not in ("", "/", "/index.htm"):
            return False
        self.send_response(302)
        self.send_header("Location", "/app/")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_HEAD(self):
        self._unprefix_api()      # /app/api/... is the same route as /api/...; see _unprefix_api
        """🔴 UPTIME MONITORS OFTEN SEND HEAD, NOT GET, and without this they would see a 404 and
        report the site as down. `SimpleHTTPRequestHandler` implements `do_HEAD` for files only, so
        every `/api/*` path answered 404 to a HEAD request while answering 200 to a GET. Measured
        2026-08-28: `HEAD /api/health` returned 404 on this server.

        A keep-alive pinger that gets a 404 is worse than no pinger: the free service still sleeps,
        and the monitoring service starts emailing that the site is down.
        """
        if self.path.split("?")[0] in ("/api/ping", "/api/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/api/"):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self._root_redirect():
            return
        self._app_artefact_fallback()
        return super().do_HEAD()

    def do_GET(self):
        self._unprefix_api()      # MUST be first: the /api/ branches below match on the prefix
        # 🔴 THE CHEAPEST POSSIBLE LIVENESS ANSWER, and it exists because /api/health is not cheap
        # enough to be polled. Measured 2026-08-28: /api/health returns 6,233 bytes, almost all of it
        # the 250-key `sites` list, resent to a robot that does not read it.
        #
        # render.com/docs/health-checks publishes no interval, only "Every few seconds", so the cost is
        # a range. Per month against the 5 GiB free bandwidth allowance:
        #
        #     polled every 3 s   ->  5.46 GB   101.8 % of the allowance
        #     polled every 10 s  ->  1.64 GB    30.5 % of the allowance
        #
        # This endpoint's body is 12 bytes, which turns both of those into 10.5 MB and 3.2 MB. A
        # 10-minute keep-alive ping on it costs 0.07 MB a month. (Whether Render bills its OWN health
        # checks as egress is not documented; the endpoint removes the question either way.)
        #
        # IT DELIBERATELY DOES NO WORK. No reload_if_stale, no offerable_sites, no key read. What it
        # proves is exactly what a restart decision should hinge on: the process is accepting
        # connections and its Python handler still runs. Anything heavier makes the health check
        # itself a way to fail the health check, which on 0.1 CPU is a real risk rather than a
        # theoretical one.
        #
        # Point Render's Health Check Path and any external pinger HERE, not at /api/health.
        if self.path.startswith("/api/ping"):
            return _json(self, {"ok": True})
        if self.path.startswith("/api/health"):
            return _json(self, health())
        # 🔴 THE LIVE RUN'S OWN REPORT, built at request time from the job that produced it.
        # NOT the per-site report: that one is generated at build time from saved responses for one
        # named configuration and cannot describe hours decided after the build. live_report.py writes
        # this one from the job's own `result` and `progress`, in Helvetica for prose and Courier for
        # the table, and reads it back before returning a byte of it.
        #
        # `latest` resolves to the most recently FINISHED job in this process, which is what the
        # browser can ask for without the engine exposing its job id. ⚠ On a shared host that is
        # whichever visitor ran last; the content is a weather schedule rather than anything private,
        # and the explicit /<job_id> form is there for a caller that has one.
        if self.path.startswith("/api/live/report/"):
            want = self.path.rsplit("/", 1)[-1].split("?")[0]
            with LOCK:
                if want == "latest":
                    done = [(j.get("started") or 0, k, j) for k, j in JOBS.items()
                            if j.get("state") == "done"]
                    job = dict(max(done)[2], id=max(done)[1]) if done else None
                else:
                    j = JOBS.get(want)
                    job = dict(j, id=want) if j else None
            if job is None:
                return _json(self, {"error": "no finished live run to report on"}, 404)
            try:
                import live_report as LR
                data, meta = LR.build_live(job)
                problems = LR.verify_live(data, meta)
            except Exception as e:                                    # noqa: BLE001
                return _json(self, {"error": "the report could not be built: %s" % e}, 500)
            if problems:
                # A report that fails its own read-back is not served. Saying why beats handing over
                # a file that looks fine until something opens it.
                return _json(self, {"error": "the report failed its own verification",
                                    "problems": problems}, 500)
            name = "agentic-arbiter-live-%s-%s.pdf" % (
                str(meta.get("site") or "site"), str(meta.get("generated") or "").replace(":", "").replace(" ", "-"))
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path.startswith("/api/live/job/"):
            jid = self.path.rsplit("/", 1)[-1].split("?")[0]
            with LOCK:
                j = JOBS.get(jid)
                if j is None:
                    return _json(self, {"error": "no such job"}, 404)
                return _json(self, {k: v for k, v in j.items() if k != "started"})
        if self.path.startswith("/api/"):
            return _json(self, {"error": "unknown endpoint"}, 404)

        # 🔴 THE FRONT DOOR IS THE REACT APP, NOT demo/index.html. The static root is DEMO, so
        # without this `/` serves the single-file page: a SUCCESSFUL deploy that shows the previous
        # interface, with every light green and nothing anywhere reporting a problem. Observed on the
        # live host 2026-08-28, and it is the same class of silent staleness that
        # testing/verify_shipped_app_is_current.py exists to catch, one layer further out: that check
        # proves the bundle is CURRENT, this makes it the thing a visitor actually reaches.
        #
        # A REDIRECT, rather than serving demo/app/index.html at `/`, because the bundle's asset
        # references are RELATIVE and that is not incidental: `./assets/index-*.js` and
        # `../fonts/inter-latin.woff2`. Served at `/` they resolve to /assets/ and to a parent of the
        # root, neither of which exists. Served at `/app/` they resolve to demo/app/assets/ and
        # demo/fonts/, and the app's own ART = '../' fetches land on demo/*.json. The bundle only
        # works at that depth, so the URL is load-bearing: do not "simplify" this to a file read.
        #
        # demo/index.html IS NOT HIDDEN. It stays reachable at /index.html, which is what the
        # verification layer measures and what CLAUDE.md calls canonical. This changes which page is
        # served at one path; it removes nothing.
        #
        # Shared with do_HEAD via _root_redirect, so a monitor sending HEAD is routed identically.
        # No Cache-Control set by hand in there: end_headers() above adds `no-cache` for every
        # non-/api/ path, and sending it twice would emit a duplicate header.
        if self._root_redirect():
            return
        self._app_artefact_fallback()
        return super().do_GET()

    def do_POST(self):
        self._unprefix_api()      # the live RUN arrives here as /app/api/live/<site>
        if not self.path.startswith("/api/live/"):
            return _json(self, {"error": "unknown endpoint"}, 404)
        site = self.path[len("/api/live/"):].split("?")[0].strip("/")
        if site not in offerable_sites():
            return _json(self, {"error": "site %r is not offerable" % site}, 400)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            body = {}
        hours = max(1, min(int(body.get("hours", 12)), 24))
        limit_c = float(body.get("limit_c", 24.0))
        replay = body.get("replay") or None
        if replay:
            # A browser must not be able to name an arbitrary path on this filesystem.
            replay = os.path.join(LV.TESTING, "results", "fixtures",
                                  os.path.basename(str(replay)))
            if not os.path.exists(replay):
                return _json(self, {"error": "no such fixture"}, 400)
        jid = start_job(site, hours, limit_c, bool(body.get("paid")), replay)
        return _json(self, {"job_id": jid, "poll": "/api/live/job/%s" % jid})


def main():
    ap = argparse.ArgumentParser(description="serve demo/ and the live agent")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="loopback by default. This process can spend money; do not expose it.")
    ap.add_argument("--allow-paid", action="store_true",
                    help="permit live FortyGuard calls. Without it every request is a dry run.")
    ap.add_argument("--max-live-calls", type=int, default=24)
    a = ap.parse_args()

    CONF["allow_paid"] = bool(a.allow_paid)
    CONF["max_live_calls"] = a.max_live_calls

    print("=" * 78)
    print("AGENTIC-ARBITER -- serving demo/ with the live agent attached")
    print("=" * 78)
    print("   url            : http://%s:%d" % (a.host, a.port))
    print("   static root    : %s" % DEMO)
    print("   live calls     : %s" % ("ENABLED, cap %d calls this process" % a.max_live_calls
                                      if a.allow_paid else
                                      "DISABLED -- every request is a costed dry run"))
    print("   credits/call   : %s   vendor daily cap: %d heatmaps"
          % (format(LV.HEATMAP_CREDITS, ","), LV.DAILY_HEATMAP_CAP))
    print("   the API key    : read in this process only, never sent to the browser")
    if a.host not in ("127.0.0.1", "localhost", "::1"):
        print("   \U0001f534 WARNING     : bound to %s, not loopback. This process can spend "
              "credits and is now reachable from the network." % a.host)
    print("   sites          : %s" % ", ".join(offerable_sites()))
    print("=" * 78)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
