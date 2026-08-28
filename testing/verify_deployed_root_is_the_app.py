# -*- coding: utf-8 -*-
r"""The page a visitor gets at `/` must be the React app, not the page it replaced.

🔴 THE FAILURE THIS CATCHES ALREADY HAPPENED, ON THE LIVE HOST. The user opened
agentic-arbiter.onrender.com and saw the PREVIOUS single-file interface. serve_live.py serves
AGENTIC-ARBITER/demo/ as its static root, so `/` returned demo/index.html while the React bundle sat
at demo/app/index.html, reachable only by typing /app/. The build was fine, the bundle was current,
the key was present, the deploy was green. Wrong page.

WHY NO EXISTING CHECK SAW IT, and this is the useful part. verify_shipped_app_is_current.py proves the
bundle was BUILT FROM the committed source, and it was correct to pass: the bundle was current. It
just was not what anyone reached. verify_app_flow.py drives the app by opening the bundle directly, so
it never asks the server which page `/` is. "The bundle is current" and "the bundle is what `/`
returns" are different claims, and only the second is the one the user is looking at.

So this starts the real server and asks it, over HTTP, for the root.

WHAT IT ASSERTS
  1. `/` is a redirect to `/app/`, and exactly one Cache-Control header comes with it
  2. `/app/` is the React bundle: <div id="root"> plus its hashed js and css
  3. every asset the bundle references resolves at that depth, including ../fonts and ART = '../'
  4. the keep-alive surface: `/api/ping` is tiny, and HEAD works on it as well as GET
  5. `/index.html` STILL serves the single-file page with #livecard and #livego intact

Point 4 is here because a free Render instance sleeps after 15 minutes without traffic, so an external
pinger hits one URL every 10 minutes indefinitely. Monitors commonly send HEAD, and
SimpleHTTPRequestHandler implements do_HEAD for FILES only: every /api/* path used to answer 404 to a
HEAD request while answering 200 to GET. A pinger that gets a 404 is worse than none, because the
service still sleeps and the monitor also starts reporting an outage.

Point 5 is not decoration either. CLAUDE.md makes the live agent permanent and calls demo/index.html
canonical, so a future change that made `/app/` the root by MOVING or DELETING the old page would be a
different and worse defect than the one this file exists to catch.

WHY A REDIRECT AND NOT A FILE READ AT `/`. The bundle's references are relative and deliberately so:
`./assets/index-*.js` and `../fonts/inter-latin.woff2`. Served at `/` they resolve to /assets/ and to
a parent of the static root, neither of which exists. The /app/ depth is load-bearing, which is why
check 3 fetches the assets rather than trusting the markup.

NO API CALLS AND NO SPEND. The server is started WITHOUT --allow-paid, and nothing here touches
/api/live. /api/health is used only as a readiness signal and makes no vendor request. The set of
files under demo/ is compared before and after, because a measurement that writes is not a
measurement (trap 5b.5).

EXIT CODES
  0  `/` serves the React app and the old page is still reachable
  1  it does not
  3  cannot tell: no bundle at demo/app/. A skip, not a pass.
"""
import http.client
import io
import os
import socket
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "AGENTIC-ARBITER", "src")
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
SHIP = os.path.join(DEMO, "app")

FAILS = []


def bad(msg):
    FAILS.append(msg)
    print("   [FAIL] %s" % msg)


def ok(msg):
    print("   [ok]   %s" % msg)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def req(port, method, path):
    """One request, redirects NOT followed, which is the whole point of the first check."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        c.request(method, path)
        r = c.getresponse()
        body = r.read()
        return r.status, r.getheaders(), body
    finally:
        c.close()


def get(port, path):
    return req(port, "GET", path)


def HEAD(port, path):
    return req(port, "HEAD", path)


def snapshot():
    out = set()
    for r, _d, fs in os.walk(DEMO):
        for f in fs:
            out.add(os.path.relpath(os.path.join(r, f), DEMO).replace(os.sep, "/"))
    return out


print("=" * 78)
print("the deployed HTTP surface: the root page, the assets, and the keep-alive endpoint")
print("=" * 78)

if not os.path.isfile(os.path.join(SHIP, "index.html")):
    print("   [skip] no bundle at AGENTIC-ARBITER/demo/app/.")
    print("          Build it with: python tools/build_app.py")
    print("          Skipping is not passing: this is the page the deployment serves.")
    sys.exit(3)

before = snapshot()
port = free_port()

# WITHOUT --allow-paid. This check must not be able to spend a credit even if it were wrong.
proc = subprocess.Popen(
    [sys.executable, os.path.join(SRC, "serve_live.py"),
     "--host", "127.0.0.1", "--port", str(port)],
    cwd=SRC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

try:
    up = False
    deadline = time.time() + 40
    while time.time() < deadline:
        if proc.poll() is not None:
            print("   [FAIL] the server exited before answering, status %s" % proc.returncode)
            print((proc.stdout.read() or b"").decode("utf-8", "replace")[-1200:])
            sys.exit(1)
        try:
            st, _h, _b = get(port, "/api/health")
            if st == 200:
                up = True
                break
        except Exception:
            time.sleep(0.4)
    if not up:
        bad("the server never became ready on port %d within 40s" % port)
        raise SystemExit
    ok("server ready on port %d, started without --allow-paid" % port)
    print()

    # 1. THE ROOT IS A REDIRECT TO /app/
    st, hdrs, _b = get(port, "/")
    loc = [v for k, v in hdrs if k.lower() == "location"]
    cc = [v for k, v in hdrs if k.lower() == "cache-control"]
    if st not in (301, 302, 307, 308):
        bad("GET / returned %d, not a redirect. A visitor is being served demo/index.html, the "
            "single-file page the React app replaced." % st)
    else:
        ok("GET / -> %d" % st)
        if loc[:1] != ["/app/"]:
            bad("GET / redirects to %r, not '/app/'. The bundle's relative asset references only "
                "resolve at that depth." % (loc[:1] or None))
        else:
            ok("Location: /app/")
    if len(cc) > 1:
        bad("%d Cache-Control headers on the redirect. end_headers() adds one for every non-/api/ "
            "path, so do not send it by hand as well." % len(cc))

    # 2. /app/ IS THE REACT BUNDLE
    st, _h, body = get(port, "/app/")
    html = body.decode("utf-8", "replace")
    if st != 200:
        bad("GET /app/ returned %d" % st)
    elif 'id="root"' not in html:
        bad("GET /app/ has no <div id=\"root\">, so it is not the React bundle")
    else:
        ok("GET /app/ -> 200, %d bytes, carries <div id=\"root\">" % len(body))

    # 3. EVERY REFERENCE THE BUNDLE MAKES RESOLVES AT THAT DEPTH
    import re
    refs = re.findall(r'(?:src|href)="(\.\.?/[^"]+)"', html)
    if not refs:
        bad("GET /app/ references no relative assets at all, which cannot be a working bundle")
    for ref in sorted(set(refs)):
        # './x' under /app/ is /app/x; '../x' is /x. Resolve exactly as a browser would.
        url = "/app/" + ref[2:] if ref.startswith("./") else "/" + ref[3:]
        st, _h, b = get(port, url)
        if st != 200 or not b:
            bad("%s -> %s (%d bytes) from /app/, so the bundle references something the server "
                "does not have there" % (ref, st, len(b)))
        else:
            ok("%-34s -> %s  200, %d bytes" % (ref, url, len(b)))

    # The app's own artefact fetches use ART = '../', which is the same arithmetic.
    st, _h, b = get(port, "/sites.json")
    if st != 200 or not b:
        bad("/sites.json -> %d, and the app fetches its artefacts with ART = '../' from /app/" % st)
    else:
        ok("%-34s -> /sites.json  200, %d bytes" % ("ART = '../' + sites.json", len(b)))

    # 4. THE KEEP-ALIVE SURFACE. A free Render instance sleeps after 15 minutes without traffic, so
    # an external pinger hits this every 10 minutes forever. Two things have to hold.
    #
    # IT MUST BE TINY. /api/health returns 6,233 bytes, almost all of it the 250-key sites list. At
    # Render's health-check cadence of one poll every 5 seconds that is 3.28 GB a month against a
    # 5 GiB free allowance. /api/ping exists to be the polled endpoint instead.
    #
    # IT MUST ANSWER HEAD. Uptime monitors commonly send HEAD rather than GET, and
    # SimpleHTTPRequestHandler implements do_HEAD for files only: before this was fixed, every
    # /api/* path answered 404 to HEAD while answering 200 to GET. A pinger seeing 404 is worse than
    # no pinger, because the service still sleeps AND the monitor starts reporting an outage.
    st, _h, b = get(port, "/api/ping")
    if st != 200:
        bad("/api/ping -> %d. This is the keep-alive and health-check target." % st)
    elif len(b) > 64:
        bad("/api/ping returned %d bytes. It exists to be cheap enough to poll; keep it tiny."
            % len(b))
    else:
        ok("/api/ping -> 200, %d bytes, %s" % (len(b), b[:32].decode("utf-8", "replace")))

    for path in ("/api/ping", "/api/health"):
        st, _h, b = HEAD(port, path)
        if st != 200:
            bad("HEAD %s -> %d. Uptime monitors often send HEAD, and a 404 makes a working service "
                "look down while it still goes to sleep." % (path, st))
        else:
            ok("HEAD %-14s -> 200" % path)

    st, hdrs, _b = HEAD(port, "/")
    loc = [v for k, v in hdrs if k.lower() == "location"]
    if st not in (301, 302, 307, 308) or loc[:1] != ["/app/"]:
        bad("HEAD / -> %d %r, but GET / redirects to /app/. Both verbs must route the same way."
            % (st, loc[:1] or None))
    else:
        ok("HEAD /              -> %d to /app/, same as GET" % st)

    # An unknown API path must still be a clean 404 on HEAD, not a 200 that hides a typo.
    st, _h, _b = HEAD(port, "/api/nonsense")
    if st != 404:
        bad("HEAD /api/nonsense -> %d, so a mistyped ping URL would look healthy" % st)
    else:
        ok("HEAD /api/nonsense  -> 404, so a mistyped ping URL cannot look healthy")

    # 5. THE OLD PAGE IS STILL THERE, WITH THE PERMANENT LIVE SURFACE
    st, _h, b = get(port, "/index.html")
    old = b.decode("utf-8", "replace")
    if st != 200:
        bad("/index.html returned %d. The single-file page is canonical and must stay reachable." % st)
    else:
        missing = [i for i in ('id="livecard"', 'id="livego"') if i not in old]
        if missing:
            bad("/index.html is served but is missing %s. Those are permanent by standing "
                "instruction." % ", ".join(missing))
        else:
            ok("/index.html -> 200, %d bytes, #livecard and #livego both present" % len(b))

except SystemExit:
    pass
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except Exception:
        proc.kill()

after = snapshot()
gained, lost = after - before, before - after
if gained or lost:
    bad("this check changed demo/: %d added, %d removed (%s). A check must not write."
        % (len(gained), len(lost), ", ".join(sorted(gained | lost))[:120]))
else:
    ok("demo/ unchanged: %d files before and after" % len(before))

print()
if FAILS:
    print("=" * 78)
    print("VERDICT: FAIL, %d problem(s)." % len(FAILS))
    for f in FAILS:
        print("   - %s" % f)
    print()
    print("   The most likely cause is serve_live.py's do_GET no longer redirecting / to /app/.")
    print("   Its static root is demo/, so without that redirect / serves the single-file page:")
    print("   a green deploy showing the previous interface, which is what happened on 2026-08-28.")
    print("=" * 78)
    sys.exit(1)

print("=" * 78)
print("VERDICT: PASS. / serves the React app, its assets resolve at /app/, /api/ping answers")
print("both GET and HEAD cheaply, and the single-file page is still at /index.html with the")
print("live surface intact.")
print("=" * 78)
sys.exit(0)
