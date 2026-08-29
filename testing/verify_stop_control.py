# -*- coding: utf-8 -*-
"""Does "Stop agent now" actually stop the spending?

    python testing/verify_stop_control.py

ZERO API CALLS. Every test here stubs the two functions that touch FortyGuard, and one of the
assertions is that the stub was never reached.

WHY THIS FILE EXISTS, AND WHY THE ASSERTION IS A COUNT RATHER THAN A FLAG
-------------------------------------------------------------------------
A stop button that sets a flag and changes a label is easy to write and impossible to trust. The
only claim worth making about this one is arithmetic: *how many paid calls did pressing it
prevent?* So test B stops the run midway through the submit loop and asserts the number of submits
is EXACTLY the number made before the press, not one more.

That number is where the money is, because of how the vendor bills. From API-USAGE.md's measured
table:

    POST /v1/heatmap        4,220 credits   (per call)
    GET  /v1/status/{id}    free            (unchanged meter across 59 polls)

The charge attaches when a window is SUBMITTED. So:

  * stopping BEFORE a submit saves 4,220 credits, every time;
  * stopping DURING the poll saves nothing at all, and dropping the poll would forfeit data that
    has already been paid for.

Test C is the second half of that: after a stop, the poll loop must take one more FREE reading
rather than abandoning windows already billed. A stop that burns 4,220 credits and returns nothing
for them is worse than no stop button.
"""
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "AGENTIC-ARBITER", "src")
PAGE = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "index.html")
sys.path.insert(0, SRC)
sys.path.insert(0, HERE)

CHECKS = []


def ck(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("   %s %s%s" % ("PASS" if ok else "FAIL", label, ("   " + detail) if detail else ""))


def banner(t):
    print()
    print("-" * 78)
    print(t)
    print("-" * 78)


def plan(n):
    """n uncached horizon windows, shaped the way horizon_windows() shapes them."""
    return [{"window": {"start_date": "2026-08-29", "start_time": "%02d:00" % (10 + i),
                        "end_date": "2026-08-29", "end_time": "%02d:00" % (12 + i)},
             "cached": False, "lead_h": i + 1} for i in range(n)]


def main():
    import live as LV

    print("=" * 78)
    print('"STOP AGENT NOW" -- does it stop the spending?')
    print("=" * 78)
    print("   zero API calls: the two functions that reach FortyGuard are stubbed, and one")
    print("   assertion is that the stub was never called.")

    N = 12
    AOI = {"stub": True}
    LATLON = (39.0, -77.5)

    # Nothing here may reach the network. Replaced for the whole module, restored at the end.
    orig = {"resolve": LV.resolve_without_network, "submit": LV.submit_window,
            "status": LV.read_status}
    calls = {"submit": 0, "status": 0}

    def no_free_windows(*a, **k):
        """Force every window into the submit path. Otherwise there is nothing to stop."""
        return None, None

    def submit_rejected(key, aoi, window):
        """A submit that is counted and then goes nowhere: no activity id, so no poll, no cache.

        `submit_http` is 200 so the caller's retry branch does not fire -- one call per window,
        which is what makes the count below a clean measurement.
        """
        calls["submit"] += 1
        return {"source": "live", "submit_http": 200, "class": "vendor_empty"}

    LV.resolve_without_network = no_free_windows
    LV.submit_window = submit_rejected

    try:
        # ------------------------------------------------------------------ A
        banner("A. STOPPED BEFORE IT STARTED: not one call may be made")
        calls["submit"] = 0
        temps, recs = LV.perceive_ambient("KEY-NOT-USED", AOI, "ashburn", LATLON, plan(N),
                                          True, None, None, None, should_stop=lambda: True)
        ck(calls["submit"] == 0, "no window was submitted",
           "submit_window called %d time(s), 0 required" % calls["submit"])
        marked = sum(1 for r in recs if r and r.get("stopped_by_operator"))
        ck(marked == N, "every window is marked stopped, not silently dropped",
           "%d of %d" % (marked, N))
        ck(all(r.get("class") == "not_attempted" for r in recs if r),
           "every window is classed not_attempted")
        ck(all(t is None for t in temps), "no value was invented for a window never requested")
        reasons = {r.get("no_data_reason") for r in recs if r}
        ck(len(reasons) == 1 and "operator stopped" in list(reasons)[0],
           "the reason names the operator, not a budget",
           list(reasons)[0][:58] if reasons else "none")

        # ------------------------------------------------------------------ B
        banner("B. STOPPED MIDWAY: exactly the calls already made, and not one more")
        calls["submit"] = 0
        # Stop the moment two submits have happened. Deterministic: it is a function of the
        # stub's own counter, not of timing.
        temps, recs = LV.perceive_ambient("KEY-NOT-USED", AOI, "ashburn", LATLON, plan(N),
                                          True, None, None, None,
                                          should_stop=lambda: calls["submit"] >= 2)
        ck(calls["submit"] == 2, "the submit loop stopped at the press, mid-batch",
           "submit_window called %d time(s), 2 expected" % calls["submit"])
        stopped = sum(1 for r in recs if r and r.get("stopped_by_operator"))
        ck(stopped == N - 2, "every un-submitted window is accounted for",
           "%d of %d" % (stopped, N - 2))
        saved = stopped * LV.HEATMAP_CREDITS
        ck(saved == (N - 2) * 4220, "the credits not spent are real and countable",
           "%s credits" % format(saved, ","))

        # ------------------------------------------------------------------ C
        banner("C. STOPPED DURING THE POLL: billed windows are read once more, not discarded")
        # These windows DO get activity ids, so they are billed and outstanding. Status never
        # completes, so nothing is written to the cache by this test.
        def submit_accepted(key, aoi, window):
            calls["submit"] += 1
            return {"source": "live", "submit_http": 200,
                    "activity_id": "stub-%d" % calls["submit"]}

        def status_processing(key, aid):
            calls["status"] += 1
            return "processing", None

        LV.submit_window = submit_accepted
        LV.read_status = status_processing
        calls["submit"] = calls["status"] = 0
        M = 4
        t0 = time.time()
        # THE STOP MUST ARRIVE AFTER THE SUBMITS, or there is nothing billed to protect. Asking
        # for it from the start is test A's case: the submit loop never runs and the poll loop is
        # never reached, which is right and is asserted there. Here every window is already paid
        # for before the press.
        temps, recs = LV.perceive_ambient("KEY-NOT-USED", AOI, "ashburn", LATLON, plan(M),
                                          True, None, None, None,
                                          should_stop=lambda: calls["submit"] >= M)
        el = time.time() - t0
        ck(el < 60, "the run ends promptly instead of waiting out the poll budget",
           "%.1f s, budget is %d s" % (el, LV.POLL_MAX_S))
        ck(calls["status"] >= 2 * M,
           "each billed window was read again after the stop, so its credits still buy data",
           "%d status reads over %d window(s), %d required" % (calls["status"], M, 2 * M))
        ck(calls["status"] < 12 * M, "and it did not keep polling forever",
           "%d reads" % calls["status"])
    finally:
        LV.resolve_without_network = orig["resolve"]
        LV.submit_window = orig["submit"]
        LV.read_status = orig["status"]

    # ------------------------------------------------------------------ D
    banner("D. THE HTTP CONTRACT, on a server started WITHOUT --allow-paid")
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    srv = subprocess.Popen([sys.executable, os.path.join(SRC, "serve_live.py"),
                            "--port", str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:%d" % port
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(base + "/api/ping", timeout=3).read()
                break
            except Exception:
                time.sleep(0.5)

        def post(path, body=None):
            d = json.dumps(body or {}).encode()
            req = urllib.request.Request(base + path, data=d,
                                         headers={"Content-Type": "application/json"})
            try:
                r = urllib.request.urlopen(req, timeout=30)
                return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b"{}")

        code, j = post("/api/live/stop/deadbeefdead")
        ck(code == 404, "an unknown job id is refused", "HTTP %s" % code)

        code, j = post("/api/live/ashburn", {"hours": 2, "limit_c": 24.0, "paid": False})
        jid = (j or {}).get("job_id")
        ck(code == 200 and jid, "a dry run starts and returns a job id", "HTTP %s" % code)

        if jid:
            code, j = post("/api/live/stop/" + jid)
            ck(code == 200 and j.get("stopping") is True, "the stop is accepted",
               "HTTP %s %s" % (code, j))
            code, j = post("/api/live/stop/" + jid)
            ck(code == 200 and j.get("stopping") is True,
               "and it is idempotent, so a double click is harmless", "HTTP %s" % code)
            r = urllib.request.urlopen(base + "/api/live/job/" + jid, timeout=30)
            jj = json.loads(r.read())
            ck(jj.get("cancel") is True,
               "the flag is visible to the poller, so the page can show the press landed")
            ck("started" not in jj, "and the job poll still hides its internal clock")

        # THE SAME ROUTE MUST WORK AT THE DEPTH THE REACT APP IS SERVED FROM. This is the exact
        # fault that made the live agent inert once already: the bundle lives at /app/, its fetches
        # are relative, so the request arrives as /app/api/... (trap 5b.7).
        code, j = post("/app/api/live/stop/deadbeefdead")
        ck(code == 404 and "no such job" in str(j),
           "the route also resolves under /app/, where the React bundle fetches from",
           "HTTP %s %s" % (code, j))
    finally:
        srv.terminate()

    # ------------------------------------------------------------------ E
    banner("E. THE CONTROL ON THE PAGE")
    page = io.open(PAGE, encoding="utf-8", newline="").read()
    ck('id="livestop"' in page, "#livestop exists")
    m = re.search(r'<button id="livestop"[^>]*>', page)
    ck(bool(m) and "hidden" in m.group(0),
       "it is hidden until a run is in flight", m.group(0)[:60] if m else "absent")
    ck(bool(m) and "btn-stop" in m.group(0), "it carries the red class")
    # STANDING RULE C1: the live card and its run button are permanent.
    ck('id="livego"' in page and 'id="livecard"' in page,
       "#livego and #livecard are still present and untouched")
    ck("stopLive" in page and "api/live/stop/" in page, "the click is wired to the stop route")
    ck("STOPWANTED" in page,
       "a stop pressed before the job id arrives is still honoured")
    # The specificity trap the page's own comment records having shipped once.
    ck(page.index(".btn-stop{") > page.index(".btn{"),
       ".btn-stop is declared after .btn, so it wins the single-class tie")
    ck(page.count("--critical") >= 2, "--critical is declared in both themes")

    # Lifted copies must carry it too, or the React app has no stop button.
    eng = io.open(os.path.join(ROOT, "AGENTIC-ARBITER", "results", "engine.mjs"),
                  encoding="utf-8", newline="").read()
    ck("api/live/stop/" in eng, "the lifted engine carries the stop route")
    # THE ROUTE STRING IS NOT THE FUNCTION, and checking only the string is what let this ship
    # broken once. mkresults.py walks reachability by CALLS (`name(`), and an event handler is
    # assigned rather than called -- so "api/live/stop/" arrived inside runLive while stopLive
    # itself stayed on the page, and the bundle threw "stopLive is not defined" from
    # buildControls. stopLive is now an explicit ENTRY, exactly as runLive already was.
    ck("function stopLive" in eng, "and the handler itself is DEFINED there, not just referenced")
    ck(re.search(r"export\s*\{[^}]*\bstopLive\b", eng, re.S) is not None,
       "and it is exported, so the React bundle can reach it")
    mk = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "src", "generated", "engine-markup.ts")
    if os.path.exists(mk):
        mkt = io.open(mk, encoding="utf-8", newline="").read()
        ck("livestop" in mkt, "the lifted markup carries the button")
    css = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "src", "generated", "engine.css")
    if os.path.exists(css):
        ck(".btn-stop" in io.open(css, encoding="utf-8", newline="").read(),
           "the lifted CSS carries the red class")

    bad = [c for c in CHECKS if not c[0]]
    print()
    print("=" * 78)
    print("   %d checks, %d failed" % (len(CHECKS), len(bad)))
    if bad:
        for _, label, detail in bad:
            print("   FAILED: %s   %s" % (label, detail))
    else:
        print("   VERDICT: pressing stop prevents the un-submitted calls and only those, reads the")
        print("            already-billed windows once more so their credits still buy data, and")
        print("            the route answers at both / and /app/.")
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
