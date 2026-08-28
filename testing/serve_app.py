# -*- coding: utf-8 -*-
"""Serve the BUILT React app together with the demo artefacts, and optionally hold the load event.

WHY THIS EXISTS RATHER THAN `vite preview`.

  1. THE ARTEFACTS LIVE ELSEWHERE. The app fetches `sites.json`, `unified_sites.json` and the rest by
     relative path, and those are 695 MB across 3,304 files in AGENTIC-ARBITER/demo/. They are not
     copied into the bundle (see app/vite.config.ts for why), so something has to serve both trees at
     one origin. This does: app/dist first, then demo/.

  2. 🔴 A HEADLESS SCREENSHOT FIRES AT THE LOAD EVENT, WHICH IS ALWAYS TOO EARLY FOR THIS MAP.
     `--virtual-time-budget` does not fix it and makes it worse: a GeoJSON source builds its tiles in
     a WORKER on the real clock, while virtual time races the page's timers ahead. Measured through
     the app's own ?probe=1 surface: the source and all three layers existed, and
     `querySourceFeatures` returned 0 with `isStyleLoaded()` false. Nothing was broken; nothing had
     been given real time to happen.
     So `--hold` keeps ONE subresource open for N seconds. The load event stays pending, the screenshot
     waits for it, and the render loop gets real wall-clock time. Same trick, same reason, as the
     slowserve harness the single-file page uses.

Run:  python testing/serve_app.py [port] [--hold SECONDS]
"""
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".md": "text/markdown; charset=utf-8",
}
HOLD_S = 0.0
# The script tag injected into index.html when --hold is on. `defer` is what makes it delay the load
# event rather than merely delay parsing.
HOLD_TAG = b'<script src="/__hold.js" defer></script>'


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path.startswith("/__hold.js"):
            # The whole point: block here, with the response still owed, so `load` cannot fire.
            time.sleep(HOLD_S)
            return self._send(b"/* held */\n", "text/javascript")

        rel = path.lstrip("/") or "index.html"

        # 🔴 THE APP IS MOUNTED AT /app/, MIRRORING THE PRODUCTION LAYOUT, and that is what makes one
        # relative link correct in three places. The built bundle is meant to be dropped into
        # `demo/app/`, so the existing single-file page sits one level up at `../index.html`. Serving
        # the app at the ROOT here instead would make that link resolve to the app itself, and the
        # "Configure this plant" button would loop back to the screen it was pressed on.
        #   this harness : /  = demo/index.html      /app/ = the built app
        #   production   : demo/index.html           demo/app/index.html
        #   vite dev     : /  = the app, and /index.html falls through to demo/index.html
        # In all three, `../index.html` from the app reaches the page that owns configure and results.
        # An /app/ path tries the bundle first and then demo/, because the app's own assets and the
        # artefacts it fetches both arrive under that prefix once `../` is clamped at the root.
        #
        # 🔴 THIS FALLBACK MUST ALSO EXIST IN PRODUCTION, and for a while it did not. serve_live.py
        # served demo/ as a plain static root, so /app/trace.json was simply a missing file there
        # while it resolved here. The engine fetches every artefact by bare filename, so on the
        # deployed host loadSite() returned false for EVERY site: "No built artefacts for <site>" and
        # a Configure button that did nothing. The flow check driven through THIS server passed the
        # whole time, because this fallback hid the difference. Trap 5b.7.
        #
        # serve_live.py now has `_app_artefact_fallback()`, and step 33 asserts it by fetching every
        # artefact name from sites.json through the REAL server. If you change the routing here, change
        # it there too, or this harness goes back to certifying a server nobody runs.
        if rel == "app" or rel.startswith("app/"):
            sub = rel[4:] or "index.html"
            bases = [(DIST, sub), (DEMO, sub)]
        else:
            bases = [(DEMO, rel)]

        for base, sub in bases:
            target = os.path.realpath(os.path.join(base, sub))
            if not target.startswith(os.path.realpath(base)):
                continue
            if not os.path.isfile(target):
                continue
            body = open(target, "rb").read()
            # ANY .html, not only index.html. The determinism check serves its probe copy as
            # `_det.html`, which got no hold and was therefore dumped before React mounted --
            # and the check then compared two empty pages and called them equal.
            if target.endswith(".html") and HOLD_S > 0 and HOLD_TAG not in body:
                body = body.replace(b"</head>", HOLD_TAG + b"</head>", 1)
            ext = os.path.splitext(target)[1].lower()
            return self._send(body, TYPES.get(ext, "application/octet-stream"))

        # The app has one entry. Only paths under /app/ fall back to it, so an unknown artefact name
        # still 404s honestly instead of silently returning HTML.
        idx = os.path.join(DIST, "index.html")
        if (rel == "app" or rel.startswith("app/")) and os.path.isfile(idx)                 and "." not in os.path.basename(rel):
            body = open(idx, "rb").read()
            if HOLD_S > 0 and HOLD_TAG not in body:
                body = body.replace(b"</head>", HOLD_TAG + b"</head>", 1)
            return self._send(body, TYPES[".html"])
        return self._send(b"not found: " + rel.encode(), "text/plain", 404)

    def log_message(self, *a):
        pass


def main():
    global HOLD_S
    args = sys.argv[1:]
    port = 8123
    if args and args[0].isdigit():
        port = int(args[0])
    if "--hold" in args:
        i = args.index("--hold")
        HOLD_S = float(args[i + 1]) if len(args) > i + 1 else 14.0
    if not os.path.isdir(DIST):
        print("   no build to serve. Run `npm run build` in AGENTIC-ARBITER/app first.")
        return 3
    print("http://127.0.0.1:%d/      the single-file page (demo/)" % port)
    print("http://127.0.0.1:%d/app/  the React app (app/dist)   hold %.0f s"
          % (port, HOLD_S))
    sys.stdout.flush()
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
