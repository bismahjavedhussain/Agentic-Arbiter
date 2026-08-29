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
  3. Clicking "Run the agent" must reach the results stage: all thirteen cards reachable across the
     six workspace tabs (the probe opens each in turn), the reasoning
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
    /* 🔴 12 SECONDS, NOT 6, AND THE REASON IS MEASURED. At 150ms a tick, `tries > 40` gave the whole
       flow six seconds. That is ample on an idle machine -- the artefacts land at ~1s -- and not
       ample with several Chrome instances competing for one CPU, where a run stalled at step 1 with
       the controls still empty. Doubling the patience costs nothing on a healthy run (the steps
       advance as soon as they are ready) and removes a false failure that would otherwise train
       whoever reads this output to re-run rather than believe it. A genuinely stalled flow still
       reports, six seconds later. */
    if (tries > 80) {
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
          /* 🔴 THE PAGE MUST LOAD AT THE TOP. It did not: MapLibre opens a popup for the
             preselected facility and calls _focusFirstElement(), the browser scrolls that close
             button into view, and the first screen arrived already scrolled past the headline.
             Measured at y=501 by scratchpad/reloadprobe.py, fixed with focusAfterOpen: false.
             Asserted here because it is a first-impression defect a judge meets before anything
             else, and nothing else in the suite looks at the window's scroll position. */
          loadScrollY:     Math.round(window.scrollY),
          mapDots:         n('#natmap canvas') ? 'canvas' : 'none'
        });
        cta.click();
        step = 1; tries = 0; return;
      }

      if (step === 1) {
        /* CONFIGURE: the controls are built and the run button is on screen. */
        /* 🔴 THE CLICK IS RETRIED, AND THIS IS ABOUT THE HARNESS, NOT THE PRODUCT.
           Step 0 clicks "Configure this plant" as soon as the button EXISTS, which React renders
           before the site's artefacts have finished loading. On an idle machine that is fine; with
           five Chrome instances competing for the CPU it produced one stall at step 1 with
           `filtersHtml=0`, and a re-run passed.
           MEASURED THAT THE PRODUCT IS NOT AT FAULT: clicking at the earliest possible moment
           (~570ms, the instant the button appears) reached the configure stage and built all 3,192
           characters of controls, three runs out of three. So the stall was a starved renderer, not
           a race in the app.
           A false failure is worse than no check, because it teaches you to re-run instead of read.
           The assertion is unchanged -- the stage must still become 'configure' and the controls must
           still be built -- this only stops one dropped click from being reported as a defect. */
        if (document.body.dataset.stage !== 'configure') {
          /* Every 12 ticks (1.8s), so the retries land at 1.8s, 3.6s and so on, all comfortably
             inside the 12s budget above rather than one tick before it. */
          if (tries > 0 && tries % 12 === 0) {
            var again = null, ab = document.querySelectorAll('button');
            for (var j = 0; j < ab.length; j++)
              if (/Configure this plant/.test(ab[j].textContent || '')) again = ab[j];
            if (again) again.click();
          }
          return;
        }
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
        /* 🔴 #tapecard IS DELIBERATELY NOT ON SCREEN, so it is not in this list.
           The one-row AgentConsole replaced it at the user's instruction: "The agent, working", its
           prose, its own PDF button and its disclosure are all gone from the display. The card stays
           in the DOM because #tape is what proves the reasoning streamed and #tapedone is the signal
           the console reads, and both are asserted separately below. Leaving it in this list would
           report a deliberate design decision as a broken panel. */
        var cards = ['headcard','decisioncard','laddercard','moneycard','fieldcard',
                     'sitecard','plumecard','whycard','scorecard','cfcard','livecard'];

        /* 🔴 THE THIRTEEN CARDS ARE NO LONGER ALL ON ONE SCREEN, so "every card visible" is now
           "every card visible IN ITS TAB". The results stage is a six-tab workspace, so a single
           snapshot would find ten of twelve hidden and be right to, which says nothing about whether
           the panels render.
           So this WALKS the tabs, one per poll of this interval. One per poll and not a tight loop
           because a click only sets React state: the panel is not laid out until React re-renders
           and, more importantly, EngineStage redraws the canvases on the next frame, because a canvas
           whose parent had no width painted nothing. A poll interval is a generous frame boundary.
           The union across tabs is what gets asserted, so a card that is unreachable in every tab
           still fails. */
        if (out._tabs === undefined) {
          out._tabs = Array.prototype.map.call(
            document.querySelectorAll('[data-aa-tabid]'),
            function (b) { return b.getAttribute('data-aa-tabid'); });
          out._tabIdx = -1;
          out._seen = {};
          out._canvasMax = 0;
          out._perTab = {};
        }
        /* Record what the CURRENT tab shows, before moving on. */
        if (out._tabIdx >= 0) {
          var cur = out._tabs[out._tabIdx];
          var here = [];
          for (var j = 0; j < cards.length; j++) {
            var el = q('#' + cards[j]);
            /* Only credit a card to the tab it claims, so a card left visible by a stale rule in
               some other tab cannot stand in for the tab that is meant to own it. */
            var owns = el && (el.getAttribute('data-aa-tab') || '').split(' ').indexOf(cur) >= 0;
            if (owns && vis(el)) { out._seen[cards[j]] = cur; here.push(cards[j]); }
          }
          out._perTab[cur] = here;
          out._canvasMax = Math.max(out._canvasMax, n('canvas'));
          /* STANDING RULE C1 IS ABOUT PRESENCE IN THE DOM, NOT ABOUT BEING ON SCREEN RIGHT NOW.
             #livecard must never be removed and never relocated. Sampled on EVERY tab, so a tab that
             tore it out of the document would be caught even though only one tab displays it. */
          out._liveInDomEveryTab = (out._liveInDomEveryTab !== false) && !!q('#livecard');
          /* Present but not displayed: that is the contract for the replaced tape card. */
          out._tapeCardInDom = (out._tapeCardInDom !== false) && !!q('#tapecard');
          out._tapeCardShown = out._tapeCardShown || vis(q('#tapecard'));
          /* 🔴 EVERY TAB MUST OPEN AT ITS OWN TOP. The tabs share one scroller, so its scroll
             position survived a tab change and a reader who had scrolled to the bottom of one tab
             landed halfway down the next. Reported as "it will show me somewhere middle of the page".
             The walk below scrolls DOWN before moving on, so each tab is entered from a scrolled
             predecessor, which is the only condition under which the bug appeared.
             ⚠ THE SCROLLER IS THE WINDOW SINCE 2026-08-30. It was `.aa-workspace-main`, until the
             fixed-viewport shell was removed so the page could scroll as one; that element's
             scrollTop is permanently 0 now, so a check still reading it would pass by measuring
             nothing. Same assertion, the scroller it names is the only thing that changed. */
          (function(){
            /* ⚠ ONLY FOR A TAB THAT EXISTS. `out._tabIdx` runs one past the end on the final pass, so
               `cur` is undefined there and this used to record a reading under the key "undefined"
               and assert on it. It read 0 while the scroller was `.aa-workspace-main`, whose scrollTop
               was always 0 after a reset, and started reading a real window position the moment the
               page got its own scroll. An assertion about a tab that does not exist can only ever be
               noise. */
            if (!cur) return;
            out._tabScroll = out._tabScroll || {};
            out._tabScroll[cur] = Math.round(window.scrollY);
            window.scrollTo(0, 400);           // leave it scrolled for the next tab to inherit
          })();
          /* 🔴 THE REPEATED SECTION HEADINGS. The page carries the eyebrow "The decision, and what it
             is worth" TWICE plus two more, and hiding them took three attempts because engine.css's
             rule is `body[data-stage="results"] .secgroup` (0,2,1), not the bare `.secgroup` the
             minified bundle appeared to show. Counted on EVERY tab, because a rule that wins on one
             tab and loses on another is exactly the shape of the bug that kept coming back. */
          (function(){
            var g = document.querySelectorAll('.secgroup'), shown = 0;
            for (var k = 0; k < g.length; k++) if (vis(g[k])) shown++;
            out._secgroupTotal = g.length;
            out._secgroupShown = Math.max(out._secgroupShown || 0, shown);
          })();
          out._livegoInDomEveryTab = (out._livegoInDomEveryTab !== false) && !!q('#livego');
        }
        /* Advance. While tabs remain, click the next one and come back next poll. */
        out._tabIdx += 1;
        if (out._tabIdx < out._tabs.length) {
          var btn = q('[data-aa-tabid="' + out._tabs[out._tabIdx] + '"]');
          if (btn && !btn.disabled) btn.click();
          return;
        }

        /* 🔴 POPUP TEXT MUST BE READABLE, MEASURED RATHER THAN EYEBALLED.
           The popups are dark in BOTH themes, and an earlier rule named only the tags I thought of
           (p, li, strong, b, h3, h4), so a <summary> inherited the PAGE's colour: near-black on
           near-black in the light theme, fine in dark. The heading "One hour, all seven stages of the
           loop" was invisible and the user photographed it.
           So this opens a dialog and computes the WCAG contrast ratio of every text node against the
           dialog's own background. A tag nobody remembered still fails.
           ⚠ THE EXAMPLE ABOVE IS HISTORY, THE CHECK IS NOT. Since 2026-08-30 lib/declutter.ts never
           folds a block containing a form control, so the "One hour, all seven stages" <details> is
           a live disclosure on the card rather than markup inside this dialog: it held a wired
           <select> whose handler did not survive being serialised. This loop takes the FIRST matching
           opener in document order, which is "What a live run costs" in #livecard, and measures every
           text node it finds there. The mechanism it guards is unchanged. */
        if (!out._contrast) {
          out._contrast = {opened: false, worst: null, worstEl: null, n: 0};
          var opener = null, ab = document.querySelectorAll('button');
          for (var z = 0; z < ab.length; z++)
            if (/Read the reasoning|How the schedule|How it scores|What a live run/.test(ab[z].textContent || ''))
              { opener = ab[z]; break; }
          if (opener) {
            opener.click();
            out._contrast.opened = true;
            /* Measured on the NEXT poll, so React has mounted the dialog. */
            return;
          }
        } else if (out._contrast.opened && out._contrast.worst === null) {
          var dlg = q('[role="dialog"]');
          if (dlg) {
            var lum = function (c) {
              var m = c.match(/rgba?\(([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/);
              if (!m) return null;
              var f = [1, 2, 3].map(function (i) {
                var v = parseFloat(m[i]) / 255;
                return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
              });
              return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2];
            };
            /* The dialog's own painted background: walk up until something is not transparent. */
            var bgEl = dlg, bg = null;
            while (bgEl && bg === null) {
              var cb = getComputedStyle(bgEl).backgroundColor;
              if (cb && cb.indexOf('rgba(0, 0, 0, 0)') < 0) bg = lum(cb);
              bgEl = bgEl.parentElement;
            }
            if (bg !== null) {
              var worst = 99, worstEl = '';
              var els = dlg.querySelectorAll('p, li, summary, h1, h2, h3, h4, strong, b, span, div, code, label');
              for (var y = 0; y < els.length; y++) {
                var el = els[y];
                /* NOT `txt`: this probe already has a global txt(selector) helper, and `var`
                   hoists to the whole enclosing function, so declaring `var txt` here shadowed it and
                   step 1's txt('#runagent') died with "txt is not a function". */
                var elTxt = (el.textContent || '').trim();
                if (!elTxt || el.children.length) continue;    // leaf nodes with real text only
                if (el.offsetParent === null) continue;         // not displayed
                var fl = lum(getComputedStyle(el).color);
                if (fl === null) continue;
                var hi = Math.max(fl, bg), lo2 = Math.min(fl, bg);
                var ratio = (hi + 0.05) / (lo2 + 0.05);
                out._contrast.n++;
                if (ratio < worst) { worst = ratio; worstEl = (el.tagName + '.' + (el.className || '')).slice(0, 40) + ' :: ' + elTxt.slice(0, 40); }
              }
              out._contrast.worst = Math.round(worst * 100) / 100;
              out._contrast.worstEl = worstEl;
            }
            var cl = dlg.parentElement && dlg.parentElement.querySelector('button');
            if (cl) cl.click();
          } else {
            out._contrast.worst = -1;                            // never mounted
          }
        }

        var shown = [], hidden = [];
        for (var m2 = 0; m2 < cards.length; m2++)
          (out._seen[cards[m2]] ? shown : hidden).push(cards[m2]);
        record('results', {
          tabs:        out._tabs,
          perTab:      out._perTab,
          liveInDom:   out._liveInDomEveryTab,
          tapeCardInDom: out._tapeCardInDom,
          contrast:      out._contrast,
          tabScroll:     out._tabScroll,
          secgroupTotal: out._secgroupTotal,
          secgroupShown: out._secgroupShown,
          tapeCardShown: out._tapeCardShown,
          livegoInDom: out._livegoInDomEveryTab,
          liveTab:     out._seen['livecard'] || null,
          cardsByTab:  out._seen,
          canvasMax:   out._canvasMax,
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

    # 🔴 ?motion=off DISABLES THE CINEMATIC INTRO, and this check needs it off for a concrete
    # reason rather than a general one: step 1 finds "Configure this plant" and CLICKS it, and the
    # enter gate is a fixed full-viewport overlay at z-index 200. An overlay swallows that click and
    # the whole flow stalls at step 1 -- the same failure shape as the stopLive ReferenceError.
    #
    # The flag is not a test-only escape hatch. It is one of the two kill switches the product ships
    # (app/src/intro/flags.ts), so what runs here is a configuration a judge can also select, not a
    # special build. With it off, IntroLayer returns null and the page is byte-for-byte the product
    # this file was written against.
    #
    # testing/verify_intro.py is what exercises the intro WITH motion on.
    url = ("http://127.0.0.1:%d/app/%s?facility=%s&motion=off"
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
    ck((p.get("loadScrollY") or 0) == 0, "the first screen loads at the top",
       "window.scrollY is %s on the pick stage" % p.get("loadScrollY"))
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
    # 🔴 "EVERY CARD VISIBLE" IS NOW "EVERY CARD VISIBLE IN ITS OWN TAB". The results stage is a
    # six-tab workspace, so the probe opens each tab in turn and credits a card only to the tab whose
    # id is in that card's own `data-aa-tab`. The union has to cover all thirteen: a card reachable
    # from no tab is a card no reader can ever see, which is the failure this still has to catch.
    tabs = rr.get("tabs") or []
    per = rr.get("perTab") or {}
    ck(len(tabs) >= 6, "the workspace offers its six tabs", "%d: %s" % (len(tabs), ", ".join(tabs)))
    ck(not rr.get("cardsHidden"), "every results card is reachable in its tab",
       "%d card(s) across %d tab(s)" % (len(rr.get("cardsShown") or []), len(tabs))
       if not rr.get("cardsHidden")
       else "UNREACHABLE IN EVERY TAB: " + ", ".join(rr["cardsHidden"]))
    # And no tab may be empty: an entry in the rail that shows nothing is worse than no entry.
    empty = [t for t in tabs if t != "config" and not per.get(t)]
    ck(not empty, "no results tab is empty",
       "each of %d tab(s) showed at least one panel" % (len(tabs) - 1) if not empty
       else "EMPTY: " + ", ".join(empty))
    ck((rr.get("tapeRows") or 0) >= 8, "the reasoning tape streamed to completion",
       "%s rows, and #tapedone is filled" % rr.get("tapeRows"))
    # canvasMax, not the final snapshot: only the active tab has canvases with a width to draw into,
    # so the count on the last tab visited says nothing about the others. The peak across the walk
    # is the honest figure, and it is what proves the redraw-on-tab-open actually fires.
    ck((rr.get("canvasMax") or 0) >= 6, "the charts drew",
       "%s canvases at the peak across %d tab(s)" % (rr.get("canvasMax"), len(tabs)))
    ck(bool(rr.get("headline")), "the headline rendered", (rr.get("headline") or "")[:60])
    # 🔴 C1 IS "NEVER REMOVED, NEVER RELOCATED", WHICH IS A CLAIM ABOUT THE DOM. Asserting
    # vis(#livecard) at the end of the run was asserting something else: the probe walks every tab and
    # finishes on the last one, so the card it owns is legitimately off screen by then. That is the tab
    # system working, not the rule breaking. So two separate assertions, each saying what it means.
    ck(rr.get("liveInDom") is True and rr.get("livegoInDom") is True,
       "#livecard and #livego are in the DOM on every tab", "standing rule C1: never removed")
    # The replaced tape card: still in the document on every tab, and shown on none of them. Both
    # halves matter. Gone from the DOM would break the console and the row count; visible would mean
    # the panel the console replaced is still competing with it.
    # WCAG contrast inside a popup, measured rather than eyeballed. 4.5:1 is the AA floor for body
    # text; 3.0 is the large-text floor. Anything under 3 is unreadable, which is what a <summary>
    # inheriting the page's near-black on a dark panel actually was.
    con = rr.get("contrast") or {}
    if con.get("worst") is None or con.get("worst") == -1:
        ck(False, "popup text contrast was measured", "no dialog could be opened to measure")
    else:
        ck(con["worst"] >= 3.0, "every popup text passes a 3:1 contrast floor",
           "worst is %.2f:1 over %d text node(s)%s"
           % (con["worst"], con.get("n") or 0,
              "" if con["worst"] >= 3.0 else "  <-- %s" % con.get("worstEl")))

    # Each tab is entered from a predecessor the probe deliberately left scrolled to 400, so a
    # non-zero reading here is the bug: the shared scroll container carried its position across.
    ts = rr.get("tabScroll") or {}
    stuck = {k: v for k, v in ts.items() if v}
    ck(not stuck, "every tab opens at its own top",
       "%d tab(s) entered at scrollTop 0" % len(ts) if not stuck
       else "ENTERED PART-SCROLLED: " + ", ".join("%s at %s" % kv for kv in stuck.items()))

    # The page's four .secgroup eyebrows, two of which carry the SAME text, must not reach the screen
    # on any tab. Asserted rather than reasoned about: two previous fixes were argued from specificity
    # and both were wrong, so this counts what a browser actually renders.
    ck((rr.get("secgroupShown") or 0) == 0,
       "no repeated section heading is on screen",
       "%s .secgroup element(s) in the page, %s displayed on any tab"
       % (rr.get("secgroupTotal"), rr.get("secgroupShown")))
    ck(rr.get("tapeCardInDom") is True and rr.get("tapeCardShown") is not True,
       "#tapecard is in the DOM and deliberately not displayed",
       "replaced by the one-row console; #tape still streams %s rows" % rr.get("tapeRows"))
    ck(bool(rr.get("liveTab")), "the live agent card is reachable in its tab",
       "shown under the %r tab" % rr.get("liveTab") if rr.get("liveTab")
       else "REACHABLE FROM NO TAB")
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
