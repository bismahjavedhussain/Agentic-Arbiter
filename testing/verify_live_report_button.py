# -*- coding: utf-8 -*-
"""After a live run, is the report actually downloadable?

    python testing/verify_live_report_button.py

ZERO API CALLS. The run is driven through the server with a REPLAY fixture, which is the same code
path a paid run takes minus the vendor call, so the report is built from a real emitted result.

WHY THIS FILE EXISTS
--------------------
The download row was gated on `#tapedone`, and that element is written by `streamTape()` -- the
REPLAY path. A live run never touches it, so after "Run the agent on live data" the React console
sat in its reasoning state indefinitely and neither Download PDF nor the live report ever appeared.
The user ran the agent live twice and had nothing to download.

So the offer now lives where the live output ends, written by `drawLive()`, which is the function
that actually knows a live run finished. Two things are checked here and they are different claims:

  1. the ELEMENT is present and `drawLive` fills it (static),
  2. the ENDPOINT returns a real PDF for a real job (over HTTP).

Either one passing alone would be a false pass: a button pointing at a broken route, or a working
route with no button.
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
AA = os.path.join(ROOT, "AGENTIC-ARBITER")
FIX = os.path.join(HERE, "results", "fixtures")

CHECKS = []


def ck(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("   %s %s%s" % ("PASS" if ok else "FAIL", label, ("   " + detail) if detail else ""))


def pick_replay():
    """A saved REAL FortyGuard heatmap response whose field actually covers THIS site.

    SELECTED BY TILE DISTANCE, NOT BY FILENAME, because that is the criterion the product itself
    applies. `resolve_without_network` rejects any fixture whose nearest tile is further than
    MAX_TILE_DIST_M (2,000 m) from the plant centre: replaying another metro's field would pick a
    tile hundreds of kilometres away and quietly decide the wrong site's schedule.

    Two earlier versions of this picker got it wrong in instructive ways. The first took any
    populated fixture, drew one from another metro, and the run came back `fixture_mismatch` with no
    hours -- so the report route refused to build one, which is the PRODUCT WORKING and my input
    being bad. The second filtered on "ashburn" appearing in the filename and matched nothing, since
    the usable fixtures are named for the experiment that bought them (n25_f_lead01.49) rather than
    for the site. Asking the same question the code asks avoids both.
    """
    import agent as A
    centre = json.load(io.open(os.path.join(AA, "demo", "trace.json"),
                               encoding="utf-8"))["site"]["centre"]
    lat, lon = centre[0], centre[1]          # [lat, lon]; live.py:1101 reads it in this order
    best, bestd = None, 1e18
    for n in sorted(os.listdir(FIX)):
        if not n.endswith(".json"):
            continue
        try:
            d = json.load(io.open(os.path.join(FIX, n), encoding="utf-8"))
        except Exception:
            continue
        r = d.get("result", d)
        if not ((r.get("map_data") or {}).get("features")):
            continue
        try:
            _, dist = A.nearest_tile(r, lat, lon)
        except Exception:
            continue
        if dist < bestd:
            best, bestd = n, dist
    return (best, bestd) if best and bestd <= 2000 else (None, bestd)


def main():
    print("=" * 78)
    print("THE LIVE RUN'S REPORT -- is it offered, and does the offer work?")
    print("=" * 78)

    # ---------------------------------------------------------------- static
    print()
    print("   1. THE OFFER IS ON THE PAGE, AND drawLive FILLS IT")
    page = io.open(os.path.join(AA, "demo", "index.html"), encoding="utf-8", newline="").read()
    ck('id="livereport"' in page, "#livereport exists in the live card")
    ck(page.index('id="livereport"') > page.index('id="livebound"'),
       "and it comes after the bound panel, at the end of the run's output")
    ck("api/live/report/' + LIVEJOB" in page,
       "drawLive names the job that produced the numbers on screen")
    ck(re.search(r"rep\.innerHTML\s*=\s*\(ok && LIVEJOB\)", page) is not None,
       "it is offered only for a run that produced a schedule")
    ck("rep.innerHTML = (ok && LIVEJOB)" in page and "': ''" in page.replace('"', "'")
       or ": ''" in page,
       "and cleared otherwise, so a stale link cannot sit under new numbers")

    eng = io.open(os.path.join(AA, "results", "engine.mjs"), encoding="utf-8",
                  newline="").read()
    ck("api/live/report/" in eng, "the lifted engine carries the report route")
    mk = os.path.join(AA, "app", "src", "generated", "engine-markup.ts")
    ck("livereport" in io.open(mk, encoding="utf-8", newline="").read(),
       "the lifted markup carries the element, so the React app has it too")

    console = io.open(os.path.join(AA, "app", "src", "components", "AgentConsole.tsx"),
                      encoding="utf-8", newline="").read()
    ck("function liveDone()" in console,
       "the console has a live-specific completion signal")
    ck("wasLive ? liveDone() : tapeDone()" in console,
       "and a live run no longer waits on #tapedone, which only the replay path writes")

    # ---------------------------------------------------------------- over HTTP
    print()
    print("   2. THE ROUTE RETURNS A REAL PDF, for a real job, at zero credits")
    sys.path.insert(0, SRC)
    fx, dist = pick_replay()
    ck(bool(fx), "a saved FortyGuard field covering this site is available to replay",
       "%s, nearest tile %.1f m" % (fx, dist) if fx else "none within 2,000 m (%.0f m)" % dist)
    if not fx:
        return 1

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

        body = json.dumps({"hours": 3, "limit_c": 24.0, "paid": False,
                           "replay": fx}).encode()
        req = urllib.request.Request(base + "/api/live/ashburn", data=body,
                                     headers={"Content-Type": "application/json"})
        j = json.loads(urllib.request.urlopen(req, timeout=60).read())
        jid = j.get("job_id")
        ck(bool(jid), "a replay run starts", str(j)[:60])

        state, result = None, None
        for _ in range(120):
            time.sleep(1.0)
            jj = json.loads(urllib.request.urlopen(
                base + "/api/live/job/" + jid, timeout=30).read())
            state = jj.get("state")
            if state in ("done", "error"):
                result = jj.get("result")
                break
        ck(state == "done", "and it completes", "state=%s" % state)
        status = (result or {}).get("status")
        ck(status in ("ok", "ok_partial", "ok_replay"),
           "with a status that earns a report", "status=%s" % status)
        # THE SPEND IS THE POINT OF THE FIXTURE: this must have cost nothing.
        spend = (result or {}).get("spend") or {}
        ck((spend.get("credits_spent") or 0) == 0 and (spend.get("calls_attempted") or 0) == 0,
           "having spent nothing", "credits=%s calls=%s" % (spend.get("credits_spent"),
                                                            spend.get("calls_attempted")))

        for path, label in ((("/api/live/report/" + jid), "by job id"),
                            ("/api/live/report/latest", "and as 'latest'")):
            try:
                r = urllib.request.urlopen(base + path, timeout=180)
                data = r.read()
                ctype = r.headers.get("Content-Type")
                ck(r.status == 200 and ctype == "application/pdf",
                   "the report is served %s" % label, "HTTP %s %s" % (r.status, ctype))
                ck(data[:5] == b"%PDF-", "and it is a PDF", data[:5].decode("latin-1"))
                ck(data.rstrip().endswith(b"%%EOF"),
                   "with a complete trailer, so it is not truncated")
                ck(len(data) > 3000, "and it has real content", "%s bytes" % format(len(data), ","))
                ck(b"/Type /Page" in data or b"/Type/Page" in data, "with page objects")
            except urllib.error.HTTPError as e:
                ck(False, "the report is served %s" % label,
                   "HTTP %s %s" % (e.code, (e.read() or b"")[:120]))

        # The same route at the depth the React bundle fetches from.
        try:
            r = urllib.request.urlopen(base + "/app/api/live/report/" + jid, timeout=180)
            ck(r.status == 200 and r.read()[:5] == b"%PDF-",
               "and it resolves under /app/, where the bundle asks from")
        except urllib.error.HTTPError as e:
            ck(False, "and it resolves under /app/", "HTTP %s" % e.code)
    finally:
        srv.terminate()

    bad = [c for c in CHECKS if not c[0]]
    print()
    print("=" * 78)
    print("   %d checks, %d failed" % (len(CHECKS), len(bad)))
    if bad:
        for _, label, detail in bad:
            print("   FAILED: %s   %s" % (label, detail))
    else:
        print("   VERDICT: the run's own report is offered where the run's output ends, and the")
        print("            route behind the offer returns a complete PDF at both depths.")
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
