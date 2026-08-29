# -*- coding: utf-8 -*-
r"""Two renders of the React app must produce the same TEXT and the same NUMBERS.

WHY NOT A PNG HASH, WHICH IS WHAT I TRIED FIRST. Two reduced-motion captures of the identical screen
differed by 719 pixels in the KPI band. Magnified, both said "637 of 637 shown", letter for letter:
the difference was sub-pixel antialiasing of the same glyphs, plus a few pixels in the WebGL map.
Neither is the application being non-deterministic. Text rasterisation and SwiftShader compositing are
not bit-exact between Chrome processes, so a PNG hash of a page containing a WebGL canvas measures the
harness, not the product. This is the same lesson `queryRenderedFeatures` taught earlier in this
project: pixels are the wrong instrument for some questions.

The single-file page's own gate agrees, and it is worth noting why it does not have this problem:
testing/verify_site_panels.py captures `[data-show~="results"]` panels, whose canvases are 2D, and the
map lives on the PICK stage and is therefore never in the comparison.

SO THIS CHECKS THE THING THAT MATTERS: every figure, label and caption the reader sees, and the map's
own reported state, twice, from fresh browser profiles. If those agree, the screen is a pure function
of the artefacts, whatever the last bit of a glyph's edge did.

🔴 IT IS NOT A DECORATIVE CHECK. The KPI cards' bar treatment is adapted from a 21st.dev component
whose motion was framer-motion SPRING physics and whose counter did `toFixed(0)`. Springs are
time-dependent, and that rounding would have turned 10.7 % into "11 %". Both were reimplemented; this
is the measurement that says the reimplementation actually worked.

Needs: `npm run build` in AGENTIC-ARBITER/app. It starts and stops its own server.
Exit 0 identical, 1 differs, 3 could not run.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from verify_site_panels import find_browser, free_port                    # noqa: E402

# 🔴 THIS CHECK STARTS ITS OWN SERVER, rather than requiring one to be running.
# A check that returns "could not run" unless a human remembered to start something is a check that
# reports nothing most of the time, and run_all would either fail on it or be taught to ignore it.
# Neither is acceptable: gotcha #74, a skip is not a pass. An already-running server on APP_PORT is
# still honoured, so the harness stays usable by hand.
PORT = int(os.environ.get("APP_PORT", "0")) or 0
URL = "http://127.0.0.1:%d/app/?probe=1" % PORT

# Everything a reader can read on the pick screen, plus the map's own account of itself. Collected
# from the DOM rather than from the source, so a change in either would show up here.
PROBE = """
<script>
(function(){
  function harvest(){
    var out = {};
    var pick = function(sel){
      return [].map.call(document.querySelectorAll(sel), function(e){
        return (e.innerText || '').replace(/[ \\t\\r\\n]+/g, ' ').trim();
      }).filter(Boolean);
    };
    out.headings   = pick('h1, .label');
    out.figures    = pick('.num');
    out.paragraphs = pick('p');
    out.buttons    = [].map.call(document.querySelectorAll('button, a'), function(e){
      return ((e.innerText || e.getAttribute('aria-label') || '')
              .replace(/[ \\t\\r\\n]+/g, ' ')).trim();
    }).filter(Boolean);
    out.comboValues = [].map.call(document.querySelectorAll('input[role=combobox]'), function(e){
      return e.value;
    });
    // The chart bars, as the DATA the reader is being shown: each bar's height in percent, rounded
    // to two places. This is the sparkline's content, and it must not move between renders.
    out.bars = [].map.call(document.querySelectorAll('.aa-bar'), function(e){
      return (e.style.height || '') + '|' + (e.style.background || '');
    });
    out.barCharts = document.querySelectorAll('[role=img]').length;
    out.barLabels = [].map.call(document.querySelectorAll('[role=img]'), function(e){
      return e.getAttribute('aria-label');
    });
    var p = document.getElementById('AAPROBE');
    if (p && p.textContent) { try { out.map = JSON.parse(p.textContent); } catch(e){} }
    return out;
  }
  /* 🔴 POLL, DO NOT WAIT FOR `load`. --dump-dom fires on `load`, so a probe listening for it is
     racing its own reader, and the first version harvested a half-mounted tree: 1 bar chart where the
     DOM has 3. serve_app.py's --hold keeps a subresource open so `load` cannot fire for N seconds;
     that window is exactly when the page finishes, and this publishes as soon as it has. */
  var tries = 0;
  var done = false;
  function complete(o){
    /* 🔴 THE BARS WERE THE COMPLETENESS SIGNAL AND THEY ARE GONE. The KPI cards lost their sparkline
       charts on 2026-08-28, at the user's instruction that the cards carry text only and the graphs
       belong in the results stage. This condition still demanded 3 charts and 20 bars, so it never
       became true, the probe polled until its give-up, and the give-up was slower than the hold, so
       the run printed "a render did not report" and nothing else. Second time in this session that a
       liveness condition outlived the thing it was watching. */
    return (o.figures || []).length >= 5
        && (o.comboValues || []).length >= 3
        && o.map && o.map.paintedDots === 637;
  }
  function publish(o, why){
    if (done) return;
    done = true;
    o.__why = why;
    o.__tries = tries;
    var d = document.createElement('div');
    d.id = 'DETPROBE'; d.style.display = 'none';
    d.textContent = JSON.stringify(o);
    document.body.appendChild(d);
  }
  var iv = setInterval(function(){
    tries++;
    var o;
    try { o = harvest(); } catch (e) { o = {}; }
    if (complete(o)) { clearInterval(iv); publish(o, 'complete'); return; }
    /* A bounded give-up, so a genuinely broken page still reports and the floors below fail it
       loudly rather than the check timing out with nothing to say. */
    /* 40 polls at 150 ms is 6 s, comfortably inside the 16 s hold. At 120 the give-up fired
       AFTER --dump-dom had already read the page, so a stall reported nothing at all. */
    if (tries > 40) { clearInterval(iv); publish(o, 'gave up after ' + tries + ' polls'); }
  }, 150);
})();
</script>
"""


def capture(browser, tag):
    """One render, in a fresh profile, returning the harvested DOM facts."""
    prof = tempfile.mkdtemp(prefix="det_%s_" % tag)
    cmd = [browser, "--headless=new", "--no-first-run", "--no-default-browser-check",
           "--user-data-dir=" + prof, "--window-size=1440,1300", "--hide-scrollbars",
           "--enable-unsafe-swiftshader", "--use-gl=angle",
           "--force-prefers-color-scheme=dark",
           # Reduced motion, so the bar entrance is at its end state rather than mid-flight. The
           # animation is a fixed-duration CSS keyframe, but a capture should not have to race it.
           "--force-prefers-reduced-motion=reduce",
           "--dump-dom", URL]
    dom = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                         encoding="utf-8", errors="replace").stdout or ""
    m = re.search(r'id="DETPROBE"[^>]*>(.*?)</div>', dom, re.S)
    if not m or not m.group(1).strip():
        return None, dom
    return json.loads(m.group(1)), dom


def main():
    browser = find_browser()
    if not browser:
        print("   no Chrome/Edge found, so this check cannot run")
        return 3
    dist = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist", "index.html")
    if not os.path.exists(dist):
        print("   no build to check. Run `npm run build` in AGENTIC-ARBITER/app first.")
        return 3
    global PORT
    srv = None
    if PORT:
        # An explicitly named port means a server is already running; use it and do not manage it.
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % PORT, timeout=5).read(1)
        except Exception as e:
            print("   nothing is answering on APP_PORT=%d (%s)" % (PORT, type(e).__name__))
            return 3
    else:
        PORT = free_port()
        srv = subprocess.Popen(
            [sys.executable, os.path.join(HERE, "serve_app.py"), str(PORT), "--hold", "16"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % PORT, timeout=1).read(1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            srv.terminate()
            print("   could not start testing/serve_app.py on port %d" % PORT)
            return 3
        print("   started serve_app.py on port %d (hold 16 s)" % PORT)

    # The probe is injected by serving a copy of the built index.html with it appended. Same trick,
    # same reason, as verify_map_hover.py: the page has to publish its own facts.
    src = io.open(dist, encoding="utf-8", newline="").read()
    if "</body>" not in src:
        print("   the built index.html has no </body> to inject into")
        return 3
    probe_file = os.path.join(os.path.dirname(dist), "_det.html")
    io.open(probe_file, "w", encoding="utf-8", newline="").write(
        src.replace("</body>", PROBE + "</body>"))
    try:
        global URL
        # ?motion=off for a reason specific to THIS check: it renders twice from a FRESH PROFILE
        # each time, so localStorage and sessionStorage are empty on both runs and the enter gate
        # would show on both. Worse, an animated page is not a pure function of the artefacts at any
        # given instant -- two captures could differ purely by where a tween had reached, which
        # would make this check report a determinism failure that is really a timing artefact.
        # Motion off is the state this check is about: the final rendered page.
        URL = "http://127.0.0.1:%d/app/_det.html?probe=1&motion=off" % PORT
        a, doma = capture(browser, "a")
        b, _ = capture(browser, "b")
    finally:
        try:
            os.remove(probe_file)
        except OSError:
            pass
        if srv is not None:
            srv.terminate()

    print("=" * 78)
    print("VERIFY_APP_DETERMINISTIC -- two renders, fresh profile each, DOM compared")
    print("=" * 78)
    if a is None or b is None:
        print("   a render did not report. DOM bytes: %d" % len(doma or ""))
        return 3

    fails = []

    # 🔴 A FLOOR ON EVERY COLLECTION, BEFORE ANY COMPARISON. The first version of this check reported
    # PASS with every field empty, because two empty harvests are equal. A comparison is evidence only
    # if there was something to compare. The numbers below are what this screen actually contains, so
    # a render that half-works cannot agree with itself and slip through.
    FLOOR = {
        "headings": 6,      # the h1 plus the five card labels, at least
        "figures": 5,       # one dominant figure per card
        "paragraphs": 6,    # three masthead lines plus the card sub-lines
        "buttons": 4,       # five info triggers, the theme toggle, the combo chevrons
        "comboValues": 3,   # state, operator, facility
        # bars, barCharts and barLabels are deliberately NOT floored any more: the cards are text
        # only now. They are still HARVESTED and still COMPARED below, so if a chart ever reappears
        # in a card its heights have to be identical across the two renders like everything else.
        # A floor on a thing that should be absent is how a check starts failing the product for
        # doing what it was asked to do.
    }
    for tag, side in (("a", a), ("b", b)):
        print("   render %s: %s after %s poll(s)"
              % (tag, side.get("__why", "?"), side.get("__tries", "?")))
    thin = []
    for k, floor in FLOOR.items():
        for tag, side in (("a", a), ("b", b)):
            got = side.get(k)
            # A SCALAR IS ITS OWN COUNT. This scored any non-list as 1, so `barCharts: 3` was read as
            # 1 and the check failed against a page that was correct: the probe reported "complete"
            # in the same breath as the floor said "partial", which is the contradiction that gave it
            # away. bool is checked first because in Python it is an int.
            if isinstance(got, list):
                n = len(got)
            elif isinstance(got, bool) or got is None:
                n = 0
            elif isinstance(got, (int, float)):
                n = int(got)
            else:
                n = 1
            if n < floor:
                thin.append("%s.%s = %d, expected at least %d" % (tag, k, n, floor))
    ck_ok = not thin
    print("   %s %-14s %s" % ("[ok]  " if ck_ok else "[FAIL]", "rendered",
                              "both renders are complete" if ck_ok
                              else "A RENDER IS EMPTY OR PARTIAL"))
    if thin:
        for t in thin[:6]:
            print("        %s" % t)
        print()
        print("   The page did not render, so there is nothing to compare. This is not a PASS.")
        print("   Is testing/serve_app.py running with --hold? --dump-dom fires at the load event,")
        print("   which is always too early for this app.")
        return 1

    # 🔴 THE PROBE'S OWN DIAGNOSTICS ARE NOT THE APP'S OUTPUT. `__tries` is how many polls each
    # render needed, which legitimately differs (7 and 6), and comparing it would fail this check on
    # its own instrumentation. A measuring device must not be part of what it measures.
    SKIP = {"map", "__why", "__tries"}
    keys = sorted(set(a) | set(b))
    for k in keys:
        if k in SKIP:
            continue
        same = a.get(k) == b.get(k)
        n = len(a.get(k) or []) if isinstance(a.get(k), list) else 1
        print("   %s %-14s %s" % ("[ok]  " if same else "[DIFF]", k,
                                  "%d item(s) identical" % n if same else "THEY DIFFER"))
        if not same:
            fails.append(k)
            av, bv = a.get(k), b.get(k)
            if isinstance(av, list) and isinstance(bv, list):
                if len(av) != len(bv):
                    print("        a has %d item(s), b has %d" % (len(av), len(bv)))
                for x, y in zip(av, bv):
                    if x != y:
                        print("        a: %r" % str(x)[:80])
                        print("        b: %r" % str(y)[:80])
                        break
            else:
                print("        a: %r" % str(av)[:80])
                print("        b: %r" % str(bv)[:80])

    # The map reports its own state; compare only the fields that are data rather than timing.
    ma, mb = a.get("map") or {}, b.get("map") or {}
    # The map has to have DRAWN something for its counts to mean anything. 637 facilities, 246 of them
    # ready: named explicitly, so a map that renders nothing cannot pass by matching another empty one.
    for side, mm in (("a", ma), ("b", mb)):
        if mm.get("paintedDots") != 637 or mm.get("paintedHalo") != 246:
            print("   [FAIL] map drew %s dots / %s halos in render %s, expected 637 / 246"
                  % (mm.get("paintedDots"), mm.get("paintedHalo"), side))
            fails.append("map.rendered")
    for k in ("paintedDots", "paintedHalo", "srcGiven", "dotFilter", "dotColor", "popupText"):
        same = ma.get(k) == mb.get(k)
        print("   %s map.%-10s %s" % ("[ok]  " if same else "[DIFF]", k,
                                      json.dumps(ma.get(k))[:60] if same else
                                      "a=%s b=%s" % (json.dumps(ma.get(k))[:30],
                                                     json.dumps(mb.get(k))[:30])))
        if not same:
            fails.append("map." + k)

    print()
    print("   figures on screen, both renders:")
    for f in (a.get("figures") or [])[:12]:
        print("      %s" % f[:70])

    print()
    if fails:
        print("%d field(s) DIFFER: %s" % (len(fails), ", ".join(fails)))
        print("VERDICT: FAIL. Something the reader sees depends on the clock, the scroll position or")
        print("         a random number. Find it before shipping.")
        return 1
    print("VERDICT: PASS. Every figure, label, caption, bar height and map count is identical across")
    print("         two independent renders, so the screen is a pure function of the artefacts.")
    print("   NOT CHECKED HERE, stated rather than implied: pixel-exact rasterisation. Glyph")
    print("   antialiasing and SwiftShader compositing are not bit-exact between Chrome processes, so")
    print("   a PNG hash of a page containing a WebGL canvas measures the harness and not the product.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
