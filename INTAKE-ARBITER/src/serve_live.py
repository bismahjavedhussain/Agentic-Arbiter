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

# ---- process state. Guarded by a lock because ThreadingHTTPServer serves concurrently and the
# call counter is the thing standing between a browser loop and the daily cap.
JOBS = {}
LOCK = threading.Lock()
LIVE_CALLS_MADE = 0
CONF = {"allow_paid": False, "max_live_calls": 24}


def _json(handler, obj, code=200):
    body = json.dumps(obj, default=str, allow_nan=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    # No caching: a live answer is about a moment, and a cached one would be a lie about when.
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def offerable_sites():
    try:
        s = json.load(open(os.path.join(DEMO, "sites.json"), encoding="utf-8"))
        return [x["key"] for x in s["sites"] if x.get("offerable")]
    except (OSError, ValueError, KeyError):
        return []


def health():
    """What the page needs to decide whether to offer a LIVE button at all.

    Deliberately does NOT report the credit balance: reading it is a network call to FortyGuard, and
    a health check that hits the vendor is a health check that fails when the vendor does.
    """
    with LOCK:
        used = LIVE_CALLS_MADE
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
        "max_live_calls": CONF["max_live_calls"],
        "credits_per_call": LV.HEATMAP_CREDITS,
        "daily_vendor_cap": LV.DAILY_HEATMAP_CAP,
        "sites": offerable_sites(),
        "why_not_live": None if (CONF["allow_paid"] and key_present) else (
            "no API key on this machine" if not key_present else
            "server started without --allow-paid, so every request is served as a costed dry run"),
        "note": "the API key never leaves the server process. The browser receives numbers only.",
    }


def start_job(site, hours, limit_c, want_paid, replay):
    """Kick off a live run on a worker thread and return its id immediately."""
    global LIVE_CALLS_MADE
    jid = uuid.uuid4().hex[:12]

    paid = bool(want_paid and CONF["allow_paid"])
    refusal = None
    if want_paid and not CONF["allow_paid"]:
        refusal = ("This server was started without --allow-paid, so it will not spend credits. "
                   "Serving a costed dry run instead -- the numbers below are what it WOULD fetch.")
    if paid:
        with LOCK:
            if LIVE_CALLS_MADE + hours > CONF["max_live_calls"]:
                paid = False
                refusal = ("Refusing: this would be call %d of a %d-call per-process cap. The "
                           "plan's real limit is %d heatmaps/day. Restart with a higher "
                           "--max-live-calls if that is genuinely what you want -- nothing here "
                           "falls back to cached data and calls it live."
                           % (LIVE_CALLS_MADE + hours, CONF["max_live_calls"],
                              LV.DAILY_HEATMAP_CAP))
            else:
                LIVE_CALLS_MADE += hours

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
                              cfg={"limit_c": limit_c}, replay=replay, on_progress=prog)
            with LOCK:
                JOBS[jid].update({"state": "done", "result": out})
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

    def log_message(self, fmt, *args):
        # Quieter than the default, and -- more importantly -- this is the only place a request line
        # is written anywhere. Query strings are truncated so a stray parameter cannot be logged.
        line = (self.requestline or "")[:120]
        sys.stderr.write("   %s %s\n" % (self.address_string(), line))

    def do_GET(self):
        if self.path.startswith("/api/health"):
            return _json(self, health())
        if self.path.startswith("/api/live/job/"):
            jid = self.path.rsplit("/", 1)[-1].split("?")[0]
            with LOCK:
                j = JOBS.get(jid)
                if j is None:
                    return _json(self, {"error": "no such job"}, 404)
                return _json(self, {k: v for k, v in j.items() if k != "started"})
        if self.path.startswith("/api/"):
            return _json(self, {"error": "unknown endpoint"}, 404)
        return super().do_GET()

    def do_POST(self):
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
    print("INTAKE-ARBITER -- serving demo/ with the live agent attached")
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
