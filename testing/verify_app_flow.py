# -*- coding: utf-8 -*-
r"""Drive the React app through pick -> configure -> results in a real browser, and check what lands.

WHY THIS IS THE TEST THAT MATTERS. Everything else about the engine lift is STATIC: the byte-identity
verifier proves results/engine.mjs is still the page's code, and the markup verifier proves the ids are
still the page's ids. Neither proves the two were wired together correctly. An engine that imports, a
markup blob that renders, and a button that calls the wrong function in the wrong order would pass both
and produce a blank results stage.

So this presses the buttons.

  1. The pick screen loads with a facility preselected via ?facility=, and the ONLY action offered is
     "Configure this plant". That is the brief: "The front page only has the configure button and then
     the run agent button and run agent live button all appears afterwards."
  2. Clicking it must reach the configure stage: the plant controls built, #runagent present.
  3. Clicking "Run the agent" must reach the results stage: the thirteen cards visible, the reasoning
     tape populated, real figures on screen, and #livecard with #livego present.

🔴 CHECK 3 IS AIMED AT A SPECIFIC HISTORICAL FAILURE. drawLimits() is the LAST call in drawAll(), and
when it once threw on a missing element the throw escaped -- drawAll() has no try/catch -- so
runAgent() never reached `await streamTape()`. Every panel rendered, the tape was empty, and nothing on
screen said why. So the tape's row count is asserted explicitly rather than inferred from the page
looking populated.

IT DRIVES THE UI, NOT THE FUNCTIONS. The probe clicks the actual buttons, because calling
configureSite() directly would prove the engine works and say nothing about whether anything is wired
to it. That was the whole defect being fixed.
"""
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

# The probe reports button labels verbatim, and this app's theme toggle is a sun glyph. On a Windows
# console that is cp1252, printing it raises UnicodeEncodeError and the traceback replaces the
# diagnostic the run existed to produce. Reconfigure once, here.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
SERVE = os.path.join(HERE, "serve_app.py")

FACILITY = "metro_ashburn"      # its metro is offerable, so the CTA is the button and not the refusal
HOLD = 34                       # seconds the load event is held open, giving the probe room to drive
# 🔴 THE GIVE-UP MUST FIRE BEFORE THE DUMP, or a stall reports nothing at all. The first version
# gave up after 130 polls at 150 ms -- 19.5 s per step -- against a 22 s hold, so when the configure
# transition really did fail the probe was still counting when --dump-dom fired and the run printed
# "the probe never published", which is the least useful thing it could have said. Six seconds a
# step, three steps, comfortably inside the hold.

CH = None
for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
    if os.path.exists(c):
        CH = c
        break

# ---- the probe -----------------------------------------------------------------------------------
# Injected into a copy of the built index.html. It polls rather than listening for `load`, because
# --dump-dom fires ON load: a probe that waits for it is racing its own reader. serve_app.py's --hold
# keeps one subresource pending, and that window is where this works.
PROBE = r"""
<script>
(function(){
  var log = [];
  function q(s){ return document.querySelector(s); }
  function vis(el){ return !!(el && !el.hidden && el.offsetParent !== null); }
  function n(s){ return document.querySelectorAll(s).length; }
  function txt(s){ var e = q(s); return e ? (e.textContent || '').trim().slice(0, 90) : null; }

  var step = 0, tries = 0, out = {steps: [], done: false, thrown: []};

  /* 🔴 CAPTURE WHAT THE PAGE THROWS, rather than inferring it from what failed to appear. Three runs
     of this file reported only "the flow stalled at step 1", and the actual cause was a TypeError in
     an async handler -- invisible to the probe, because a rejected promise breaks nothing the probe
     can see. It just means some element never gets written. The page's own gotcha #86 is this exact
     shape: a handler bound to an id that no longer exists, inside an async function, is silent. */
  window.addEventListener('error', function(e){
    out.thrown.push('error: ' + String((e && e.message) || e).slice(0, 220));
  });
  window.addEventListener('unhandledrejection', function(e){
    var r = e && e.reason;
    out.thrown.push('rejection: ' + String((r && (r.stack || r.message)) || r).slice(0, 300));
  });

  function record(name, o){ o.step = name; out.steps.push(o); log.push(name); }

  var iv = setInterval(function(){
    tries++;
    /* THE GIVE-UP IS CHECKED FIRST, and that is the whole point. It used to sit at the BOTTOM of this
       callback, after the three step blocks -- every one of which does `if (not ready yet) return`.
       So the only path that ever reached the give-up was the one where a step had already succeeded,
       and a probe that never found its target could never report. Three runs printed "the probe never
       published", which says nothing about why. Checked at the top, a stall always reports. */
    if (tries > 40) {
      out.stalledAt = step;
      out.stage = document.body.dataset.stage || null;
      /* Enough state to diagnose a stall in ONE run rather than three. */
      out.diag = {
        filters:      n('#filters'),
        filterSelects: n('#filters select'),
        anySelect:    n('select'),
        filtersHtml:  (q('#filters') ? (q('#filters').innerHTML || '').length : -1),
        aerial:       n('#aerial'),
        sitename:     txt('#sitename'),
        runagent:     n('#runagent'),
        tape:         n('#tape'),
        vizRoot:      n('.viz-root'),
        cSiteValue:   (q('#c_site') ? q('#c_site').value : null)
      };
      out.buttonsSeen = (function(){
        var t = [], b = document.querySelectorAll('button');
        for (var i = 0; i < b.length && t.length < 12; i++) {
          var x = (b[i].textContent || '').trim();
          if (x) t.push(x.slice(0, 34));
        }
        return t;
      })();
      clearInterval(iv);
      publish();
      return;
    }
    try {
      if (step === 0) {
        /* PICK: the search bar and the map are up, and the only action is Configure. */
        var cta = null;
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++)
          if (/Configure this plant/.test(btns[i].textContent || '')) cta = btns[i];
        if (!cta) return;
        record('pick', {
          configureButton: (cta.textContent || '').trim(),
          runAgentVisible: vis(q('#runagent')),
          liveVisible:     vis(q('#livecard')),
          bodyStage:       document.body.dataset.stage || null,
          mapDots:         n('#natmap canvas') ? 'canvas' : 'none'
        });
        cta.click();
        step = 1; tries = 0; return;
      }

      if (step === 1) {
        /* CONFIGURE: the controls are built and the run button is on screen. */
        if (document.body.dataset.stage !== 'configure') return;
        if (!n('#filters select')) return;
        record('configure', {
          bodyStage:      document.body.dataset.stage,
          controlsBuilt:  n('#filters select'),
          runAgent:       txt('#runagent'),
          autofill:       txt('#autofill'),
          backToPick:     txt('#backtopick'),
          siteName:       txt('#sitename'),
          resultsVisible: vis(q('#headcard'))
        });
        q('#runagent').click();
        step = 2; tries = 0; return;
      }

      if (step === 2) {
        /* RESULTS: every card, the tape, the figures, and the live agent. */
        if (document.body.dataset.stage !== 'results') return;
        /* WAIT FOR #tapedone, NOT FOR THE FIRST ROW. streamTape() reveals the tape one line at a
           time, so "at least 2 rows" was satisfied about 200 ms in and the probe recorded a
           2-row tape and called it a failure. The engine fills #tapedone when streaming ends;
           that is the completion signal, so this waits for the thing that means finished. */
        var doneEl = q('#tapedone');
        if (!doneEl || !(doneEl.textContent || '').trim()) return;
        var tapeRows = n('#tape tr') + n('#tape .ev') + n('#tape > *');
        var cards = ['headcard','tapecard','decisioncard','laddercard','moneycard','fieldcard',
                     'sitecard','plumecard','whycard','scorecard','cfcard','livecard'];
        var shown = [], hidden = [];
        for (var j = 0; j < cards.length; j++)
          (vis(q('#' + cards[j])) ? shown : hidden).push(cards[j]);
        record('results', {
          bodyStage:   document.body.dataset.stage,
          tapeRows:    tapeRows,
          cardsShown:  shown,
          cardsHidden: hidden,
          headline:    txt('#headline'),
          tapeDone:    txt('#tapedone'),
          livegoDisabled: (function(){ var b = q('#livego'); return b ? !!b.disabled : null; })(),
          livego:      txt('#livego'),
          liveVisible: vis(q('#livecard')),
          canvases:    n('canvas'),
          figures:     (function(){
            var f = [], e = document.querySelectorAll('.tile .v, .tile b, #headline b');
            for (var k = 0; k < e.length && f.length < 14; k++) {
              var t = (e[k].textContent || '').trim();
              if (t) f.push(t.slice(0, 26));
            }
            return f;
          })()
        });
        out.done = true;
        clearInterval(iv);
        publish();
        return;
      }
    } catch (e) {
      out.error = String(e && (e.stack || e.message) || e).slice(0, 300);
      out.errorAtStep = step;
      clearInterval(iv);
      publish();
      return;
    }
  }, 150);

  function publish(){
    var d = document.createElement('div');
    d.id = 'FLOWPROBE';
    d.style.display = 'none';
    d.textContent = JSON.stringify(out);
    document.body.appendChild(d);
  }
})();
</script>
"""


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server(port, hold):
    """Start serve_app.py and WAIT UNTIL IT ANSWERS, rather than sleeping and hoping.

    A fixed sleep(1.5) was the first version and Chrome met ERR_CONNECTION_REFUSED: the server was
    listening about half a second later. verify_app_deterministic.py already polls for readiness for
    exactly this reason, so this matches it instead of inventing a second convention.
    """
    srv = subprocess.Popen(
        [sys.executable, SERVE, str(port), "--hold", str(hold)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % port, timeout=1).read(1)
            return srv
        except Exception:
            time.sleep(0.2)
    srv.terminate()
    return None


def main():
    print("=" * 78)
    print("THE REACT APP, DRIVEN: pick -> configure -> results")
    print("=" * 78)

    if not os.path.isdir(DIST) or not os.path.exists(os.path.join(DIST, "index.html")):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist. Run `npx vite build` in app/.")
        return 3
    if not CH:
        print("   [skip] no Chrome found, so the flow cannot be driven.")
        return 3

    # the probe copy, so the shipped index.html is never modified
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    probe_name = "_flow.html"
    probed = src.replace("</body>", PROBE + "</body>")
    if probed == src:
        probed = src + PROBE
    io.open(os.path.join(DIST, probe_name), "w", encoding="utf-8", newline="").write(probed)

    port = free_port()
    srv = start_server(port, HOLD)
    if srv is None:
        print("   [skip] testing/serve_app.py would not start on port %d" % port)
        try:
            os.remove(os.path.join(DIST, probe_name))
        except OSError:
            pass
        return 3
    print("   serving app/dist on port %d, load held %d s" % (port, HOLD))

    url = ("http://127.0.0.1:%d/app/%s?facility=%s"
           % (port, probe_name, FACILITY))
    prof = tempfile.mkdtemp(prefix="flow_")
    try:
        r = subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
             "--user-data-dir=" + prof, "--window-size=1500,1400", "--hide-scrollbars",
             "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--force-prefers-reduced-motion=reduce", "--force-prefers-color-scheme=dark",
             # NO --virtual-time-budget. It compresses setTimeout but not fetches or workers, so the
             # budget can expire while the app is still waiting on real artefact loads. serve_app.py's
             # --hold is the right instrument: it holds one subresource for real wall-clock seconds.
             "--dump-dom", url],
            capture_output=True, text=True, timeout=240, encoding="utf-8", errors="replace")
        dom = r.stdout or ""
    finally:
        srv.terminate()
        try:
            os.remove(os.path.join(DIST, probe_name))
        except OSError:
            pass
        shutil.rmtree(prof, ignore_errors=True)

    m = re.search(r'<div id="FLOWPROBE"[^>]*>(.*?)</div>', dom, re.S)
    if not m:
        print("   [FAIL] the probe never published. The app did not reach the pick screen.")
        print("          DOM was %d chars. Is there a build, and does it load its artefacts?" % len(dom))
        for pat in ("Could not load the artefacts", "no #root", "Loading saved data"):
            if pat in dom:
                print("          the DOM contains: %r" % pat)
        return 1

    raw = m.group(1)
    raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    try:
        o = json.loads(raw)
    except ValueError as e:
        print("   [FAIL] the probe published unreadable JSON: %s" % e)
        print("          %r" % raw[:300])
        return 1

    fails = []

    def ck(ok, label, detail=""):
        print("   %s %-46s %s" % ("[ok]  " if ok else "[FAIL]", label, detail))
        if not ok:
            fails.append(label)

    if o.get("thrown"):
        print("   the page threw %d time(s) during the run:" % len(o["thrown"]))
        for t in o["thrown"][:5]:
            print("      %s" % t.replace(chr(10), " | ")[:200])
    if o.get("error"):
        print("   [FAIL] the app threw at step %s" % o.get("errorAtStep"))
        print("          %s" % o["error"])
        return 1
    if "stalledAt" in o:
        print("   [FAIL] the flow stalled at step %s, body stage %r"
              % (o["stalledAt"], o.get("stage")))
        print("          steps that did complete: %s"
              % (", ".join(x["step"] for x in o.get("steps", [])) or "none"))
        if o.get("diag"):
            print("          state at the stall: %s"
                  % ", ".join("%s=%s" % (k, v) for k, v in sorted(o["diag"].items())))
        if o.get("buttonsSeen"):
            print("          buttons on screen: %s" % " | ".join(o["buttonsSeen"]))
        return 1

    by = {s["step"]: s for s in o.get("steps", [])}

    # ---- 1. the pick screen -----------------------------------------------------------------------
    p = by.get("pick") or {}
    ck(bool(p), "the pick screen rendered")
    ck("Configure this plant" in (p.get("configureButton") or ""),
       "its only action is Configure this plant", p.get("configureButton") or "ABSENT")
    ck(p.get("runAgentVisible") is False,
       "Run the agent is NOT on the first screen", "as the brief requires")
    ck(p.get("liveVisible") is False,
       "the live card is NOT on the first screen", "it belongs to the results stage")
    ck(p.get("bodyStage") == "pick", "body carries data-stage=pick", str(p.get("bodyStage")))

    # ---- 2. the configure stage -------------------------------------------------------------------
    c = by.get("configure") or {}
    ck(bool(c), "clicking Configure reached the configure stage")
    ck((c.get("controlsBuilt") or 0) >= 6,
       "buildControls() built the plant controls", "%s selects" % c.get("controlsBuilt"))
    ck("Run the agent" in (c.get("runAgent") or ""),
       "Run the agent appears here", c.get("runAgent") or "ABSENT")
    ck(bool(c.get("autofill")), "Auto-fill a realistic plant appears here",
       c.get("autofill") or "ABSENT")
    ck(bool(c.get("backToPick")), "the way back to the pick screen appears here",
       c.get("backToPick") or "ABSENT")
    ck(bool(c.get("siteName")), "the chosen site is named", c.get("siteName") or "ABSENT")
    ck(c.get("resultsVisible") is False,
       "the results cards are still hidden", "setStage is the single owner")

    # ---- 3. the results stage ---------------------------------------------------------------------
    rr = by.get("results") or {}
    ck(bool(rr), "clicking Run the agent reached the results stage")
    ck(not rr.get("cardsHidden"), "every results card is visible",
       "%d shown" % len(rr.get("cardsShown") or [])
       if not rr.get("cardsHidden") else "HIDDEN: " + ", ".join(rr["cardsHidden"]))
    ck((rr.get("tapeRows") or 0) >= 8, "the reasoning tape streamed to completion",
       "%s rows, and #tapedone is filled" % rr.get("tapeRows"))
    ck((rr.get("canvases") or 0) >= 6, "the charts drew", "%s canvases" % rr.get("canvases"))
    ck(bool(rr.get("headline")), "the headline rendered", (rr.get("headline") or "")[:60])
    ck(rr.get("liveVisible") is True, "the live agent card is present",
       "standing rule C1")
    # 🔴 MODE-AWARE, because "Live agent not attached" is the CORRECT label here and my first version
    # called it a failure. serve_app.py serves static files and answers no /api/health, so probeLive()
    # finds nothing and drawLiveUnavailable() disables the button and says so. That is the honest
    # behaviour standing rule C1 exists to preserve: the card stays and explains why a live run cannot
    # be requested, rather than vanishing. Asserting the live-run wording unconditionally would have
    # been asserting that a static host pretends to have a server.
    lg = rr.get("livego") or ""
    ck("live data" in lg or "not attached" in lg,
       "the live button states the mode it is in", lg or "ABSENT")
    ck(rr.get("livegoDisabled") is True if "not attached" in lg else True,
       "and it is disabled when no agent is attached",
       "replay mode, correctly refused" if "not attached" in lg else "a live agent is attached")
    figs = rr.get("figures") or []
    ck(len(figs) >= 4, "figures are on screen", ", ".join(figs[:6]))

    print()
    print("=" * 78)
    if fails:
        print("VERDICT: %d step(s) FAILED." % len(fails))
        for f in fails:
            print("   * %s" % f)
    else:
        print("VERDICT: PASS. The new UI carries the whole product. One button on the first screen,")
        print("         the plant controls behind it, and Run the agent plus Run the agent on live")
        print("         data on the stage after that, drawing %s canvases and a %s-row tape."
              % (rr.get("canvases"), rr.get("tapeRows")))
    print("=" * 78)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
