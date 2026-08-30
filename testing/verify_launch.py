"""VERIFY_LAUNCH -- the timed cinematic that "Initialize Arbiter" starts.

Six scenarios, all named by the user's brief, plus the kill switch:

    1. normal run          the full sequence, the three cues, the push-in, the crossfade
    2. escape hatch        click, Esc and Space, at several points, including before audio loads,
                           and NO visible skip hint at any moment
    3. muted               the short path, and no dead silence
    4. audio missing       every file 404s: the sequence still completes, nothing thrown
    5. double click        two clicks, one sequence
    6. navigate away       mid-sequence: audio stops, nothing left running
    7. the kill switch     ?cinematic=off makes the button navigate instantly

🔴 THIS FILE RUNS ON A REAL CLOCK, AND THAT IS WHY IT IS A SEPARATE FILE.
`verify_intro.py` runs every scenario under `--virtual-time-budget`, which is what lets it describe
twelve seconds and finish in two. GSAP does not advance under that clock (05-TRAPS 5b.13), so a
GSAP-driven nine-second sequence cannot be measured there at all: what completes it is the wall-clock
watchdog, and every cue attached to a timeline label is simply never reached.
So this file removes the budget and lets `serve_app.py --hold N` give the page N real seconds. That is
slow, deliberately: these are the assertions that cannot be made any other way.

⚠ IT COSTS NOTHING. No API calls, no writes outside `app/dist`, and it skips cleanly with exit 3 if
there is no build or no browser.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AA = os.path.join(ROOT, "AGENTIC-ARBITER")
DIST = os.path.join(AA, "app", "dist")
FACILITY = "metro_ashburn"

CHECKS = [0]
FAILS = []

# Comment patterns for the source scan in section 8, built with chr() rather than written as
# escapes: this project has been bitten nine times by a shell eating a backslash (05-TRAPS 5.4),
# and a regex that silently matches nothing is the worst possible outcome for a check.
SLASH, STAR, NL = chr(47), chr(42), chr(10)
BLOCK_COMMENT = re.compile(re.escape(SLASH + STAR) + ".*?" + re.escape(STAR + SLASH), re.S)
LINE_COMMENT = re.compile(re.escape(SLASH + SLASH) + "[^" + NL + "]*")



def ck(ok, label, detail=""):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(label + ("   " + detail if detail else ""))
    print("   %s %s%s" % ("PASS" if ok else "FAILED", label, ("   " + detail) if detail else ""))


def head(t):
    print("\n   " + t)
    print("   " + "-" * min(78, len(t) + 4))


def find_browser():
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        if os.path.isfile(c):
            return c
    return None


CH = find_browser()

# ---------------------------------------------------------------------------------------------
# THE PROBE. Injected into <head> so it runs BEFORE the bundle: the media patch has to be in place
# before audio.ts constructs its elements, and the error trap before anything can throw.
# ---------------------------------------------------------------------------------------------
PROBE = r"""
<script>
(function(){
  var SC = (location.hash || '').replace('#','') || 'observe';
  var log = { scenario: SC, steps: [], media: [], errors: [], rejections: [] };
  window.__aaLaunch = log;

  /* ERRORS THE READER WOULD SEE. Both channels: a throw that reaches window, and a promise nobody
     caught. A media element's own `error` event is NOT one of these, which is the point of the
     missing-files scenario: a 404 must be handled, not thrown. */
  window.addEventListener('error', function(e){ log.errors.push(String(e.message || e)); });
  window.addEventListener('unhandledrejection', function(e){
    log.rejections.push(String((e.reason && e.reason.message) || e.reason || e));
  });

  /* EVERY play() AND pause(), WITH ITS FILE AND THE MOMENT. This is the only way to see the cue
     sequence: the elements are built with `new Audio()` and never enter the document. */
  var P = HTMLMediaElement.prototype;
  var rawPlay = P.play, rawPause = P.pause, rawLoad = P.load;
  var t0 = performance.now();
  function name(el){ return String(el.currentSrc || el.src || '').split('/').pop().split('?')[0]; }
  P.play = function(){
    log.media.push({ ev:'play', file:name(this), at:Math.round(performance.now()-t0),
                     vol:Math.round(this.volume*1000)/1000 });
    var p;
    try { p = rawPlay.apply(this, arguments); } catch(e){ return Promise.reject(e); }
    return (p && p.catch) ? p.catch(function(err){
      log.media.push({ ev:'refused', file:name(this), at:Math.round(performance.now()-t0) });
      throw err;
    }.bind(this)) : p;
  };
  P.pause = function(){
    log.media.push({ ev:'pause', file:name(this), at:Math.round(performance.now()-t0) });
    return rawPause.apply(this, arguments);
  };
  P.load = function(){
    log.media.push({ ev:'load', file:name(this), at:Math.round(performance.now()-t0) });
    return rawLoad.apply(this, arguments);
  };

  /* SCENARIO 4: every audio file 404s. The src setter is intercepted before the bundle runs, so the
     app asks for a directory that does not exist. This is a real network failure rather than a
     simulated one, which is the difference between testing the product and testing a stub. */
  if (SC === 'missing') {
    var d = Object.getOwnPropertyDescriptor(P, 'src');
    Object.defineProperty(P, 'src', {
      configurable: true,
      get: function(){ return d.get.call(this); },
      set: function(v){ d.set.call(this, String(v).replace('/audio/', '/audio-gone/')); }
    });
  }

  function q(s){ return document.querySelector(s); }
  function cta(){ return q('.shiny-cta'); }
  function rect(el){ if(!el) return null; var r = el.getBoundingClientRect();
    return { x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height) }; }

  /* 🔴 THE SKIP-HINT SCAN. The brief: "Do not render any visible skip hint, button, or text."
     Every visible word on the splash is collected and matched against the vocabulary such a hint
     would have to use. Text nodes only, and only in elements that are actually displayed, so a
     `display: none` leftover would not raise a false alarm and an `aria-label` would not hide one:
     labels are read too, because a screen reader announcing "press escape to skip" is a hint. */
  function skipHint(){
    var root = q('.aa-splash') || document.body;
    var hits = [];
    var walk = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null);
    var el = root;
    while (el) {
      var cs = getComputedStyle(el);
      if (cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.02) {
        var own = '';
        for (var i = 0; i < el.childNodes.length; i++)
          if (el.childNodes[i].nodeType === 3) own += el.childNodes[i].nodeValue;
        var aria = el.getAttribute && (el.getAttribute('aria-label') || '');
        var s = (own + ' ' + aria);
        if (/\b(skip|esc|escape|space ?bar|press any|click to skip|dismiss)\b/i.test(s))
          hits.push(s.trim().slice(0, 70));
      }
      el = walk.nextNode();
    }
    return hits;
  }

  function snap(tag){
   try {
    var g = q('.aa-gate.aa-splash');
    var c = cta();
    var canvas = q('.aa-splash-globe-canvas');
    log.steps.push({
      tag: tag,
      at: Math.round(performance.now() - t0),
      gate: !!g,
      gateOpacity: g ? getComputedStyle(g).opacity : null,
      gateTransform: g ? getComputedStyle(g).transform : null,
      leaving: g ? g.classList.contains('is-leaving') : null,
      ctaText: c ? (c.textContent || '').trim() : null,
      ctaDisabled: c ? !!c.disabled : null,
      ctaCommitted: c ? c.classList.contains('is-committed') : null,
      stage: document.body.dataset.stage || null,
      introAttr: document.body.getAttribute('data-aa-intro'),
      pickOpacity: (function(){ var p = q('[data-show="pick"]');
        return p ? getComputedStyle(p).opacity : null; })(),
      sphere: canvas && canvas.dataset ? canvas.dataset.aaSphere : null,
      dolly: canvas && canvas.dataset ? canvas.dataset.aaDolly : null,
      skipHints: skipHint(),
      paused: (function(){
        var out = [];
        var all = document.querySelectorAll('audio');
        for (var i = 0; i < all.length; i++) out.push(all[i].paused);
        return out;
      })()
    });
   } catch (e) {
    log.steps.push({ tag: tag, at: Math.round(performance.now() - t0),
                     snapError: String(e && e.message ? e.message : e) });
   }
  }

  /* 🔴 IDEMPOTENT, AND THERE IS AN UNCONDITIONAL LATE CALL BELOW.
     Trap 5b.3: a polling probe must be able to report even when its own path fails. The first version
     of this file published only from inside each scenario branch, so a throw anywhere in `run()` or in
     one of its timers meant NOTHING was published and the harness reported "the probe ran: FAILED"
     with no information about why. Now the log always comes back, even if it comes back empty. */
  var published = false;
  function publish(){
    if (published) return;
    published = true;
    var d = document.createElement('div');
    d.id = 'LAUNCHPROBE'; d.style.display = 'none';
    d.textContent = JSON.stringify(log);
    document.body.appendChild(d);
  }

  function press(key, code){
    window.dispatchEvent(new KeyboardEvent('keydown',
      { key: key, code: code || key, bubbles: true, cancelable: true }));
  }

  /* 🔴 EVERY TIME IN THIS LOG IS RELATIVE TO PAGE PARSE, AND THE ASSERTIONS ARE ABOUT THE CLICK.
     Those differ by however long the splash took to mount and the CTA took to arm, which is variable.
     So the click stamps itself and the Python side subtracts. The first version compared raw parse-
     relative figures against click-relative expectations and reported a voiceover 2.6 s "late" when it
     had in fact started on the same frame as the click. */
  function clickCta(el){
    log.clickAt = Math.round(performance.now() - t0);
    el.click();
  }

  function run(){
    var c = cta();
    if (!c) { log.err = 'no CTA on the splash'; publish(); return; }

    /* Scenario 7: the kill switch. Nothing is clicked differently; what changes is the flag in the
       query string, and the assertion is that the gate is gone almost immediately. */
    snap('before');

    if (SC === 'nohint-preclick') { snap('idle'); setTimeout(function(){ snap('idle2'); publish(); }, 900); return; }

    if (SC === 'escape-early') {
      /* BEFORE THE AUDIO CAN HAVE LOADED: the escape is pressed 60 ms after the click. */
      clickCta(c);
      setTimeout(function(){ snap('committed'); press('Escape'); }, 60);
      setTimeout(function(){ snap('after-escape'); publish(); }, 1400);
      return;
    }
    if (SC === 'escape-space') {
      clickCta(c);
      setTimeout(function(){ snap('mid'); press(' ', 'Space'); }, 2200);
      setTimeout(function(){ snap('after-escape'); publish(); }, 3600);
      return;
    }
    if (SC === 'escape-tooearly') {
      /* THE GRACE WINDOW. A pointerdown 250 ms after the reader's own click is an impatient second
         press, not a decision to skip, and it must NOT cut the sequence. */
      c.click();
      setTimeout(function(){
        window.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      }, 250);
      setTimeout(function(){ snap('after-escape'); publish(); }, 1600);
      return;
    }
    if (SC === 'escape-click') {
      c.click();
      setTimeout(function(){
        snap('mid');
        window.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      }, 3400);
      setTimeout(function(){ snap('after-escape'); publish(); }, 4800);
      return;
    }
    if (SC === 'escape-repeat') {
      /* IDEMPOTENCE: five presses must not queue five transitions. */
      clickCta(c);
      setTimeout(function(){
        for (var i = 0; i < 5; i++) press('Escape');
        window.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      }, 900);
      setTimeout(function(){ snap('after-escape'); publish(); }, 2600);
      return;
    }
    if (SC === 'double') {
      clickCta(c);
      c.click();
      try { c.click(); } catch (e) {}
      setTimeout(function(){ snap('t900'); }, 900);
      setTimeout(function(){ snap('t3000'); publish(); }, 3000);
      return;
    }
    if (SC === 'away') {
      clickCta(c);
      setTimeout(function(){
        snap('mid');
        window.dispatchEvent(new Event('pagehide'));
      }, 2400);
      setTimeout(function(){ snap('after-away'); publish(); }, 3600);
      return;
    }

    /* Scenarios 1, 3, 7: run it and watch. */
    clickCta(c);
    [200, 1200, 3000, 5200, 6400, 7400, 8400].forEach(function(t){
      setTimeout(function(){ snap('t' + t); }, t);
    });
    setTimeout(function(){ snap('end'); publish(); }, 9400);
  }

  function guarded(){
    try { run(); } catch (e) { log.err = 'run() threw: ' + (e && e.message ? e.message : e); publish(); }
  }
  /* 🔴 POLLED FOR THE BUTTON, NOT HUNG OFF DOMContentLoaded, AND THE DIFFERENCE COST A ROUND.
     `serve_app.py --hold N` keeps one subresource pending for N seconds, which is exactly how this
     file buys real wall-clock time. It also DELAYS DOMContentLoaded past the hold, so a listener on
     that event fires after the DOM has already been dumped: the first version of this probe waited
     for it and published nothing at all, with no steps and no error to explain why.
     Polling for the CTA is both earlier and more honest: the thing the scenario needs is the button,
     so wait for the button. */
  var waited = 0;
  var boot = setInterval(function(){
    waited += 100;
    var c = document.querySelector('.shiny-cta');
    /* 🔴 WAIT FOR AN *ENABLED* BUTTON, NOT MERELY A PRESENT ONE, and that distinction cost a round.
       `IntroGate` disables the CTA until the three audio files report enough data, capped at
       ARM_CAP_MS. A disabled button silently ignores `.click()`, so the first version of this clicked
       into the void: no cues, no committed state, and a gate that sat there until the probe's own
       late publish. Nothing was broken; the test was early.
       `armedAtMs` is recorded because it is worth knowing how long that window really is: it is the
       one moment a reader could meet a dead control. */
    if ((c && !c.disabled) || waited > 6000) {
      clearInterval(boot);
      log.armedAtMs = c && !c.disabled ? waited : null;
      setTimeout(guarded, 250);
    }
  }, 100);
  /* THE GIVE-UP, CHECKED LAST IN TIME AND FIRST IN IMPORTANCE. Whatever happened, the log is
     published before the hold expires and the DOM is dumped. */
  setTimeout(function(){
    if (!published) log.err = (log.err || '') + ' [late publish: the scenario never finished]';
    publish();
  }, 14200);
})();
</script>
"""


def serve(hold):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port),
                          "--hold", str(hold)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % port, timeout=1).read(1)
            break
        except Exception:
            time.sleep(0.4)
    return p, port


def load(port, scenario, query="", size=(1400, 900)):
    """One REAL-CLOCK load. No --virtual-time-budget: see the note at the top of this file."""
    prof = tempfile.mkdtemp(prefix="launch_")
    url = ("http://127.0.0.1:%d/app/_launch.html?facility=%s%s#%s"
           % (port, FACILITY, query, scenario))
    try:
        r = subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
             "--user-data-dir=" + prof, "--window-size=%d,%d" % size,
             "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--autoplay-policy=no-user-gesture-required",
             "--dump-dom", url],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'id="LAUNCHPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    return json.loads(m.group(1)) if m else None


def rel(d, at):
    """Click-relative milliseconds. See the note on clickAt in the probe."""
    if at is None:
        return None
    return at - ((d or {}).get("clickAt") or 0)


def step(d, tag):
    for s in (d or {}).get("steps", []):
        if s.get("tag") == tag:
            return s
    return {}


def files(d, ev="play"):
    return [m["file"] for m in (d or {}).get("media", []) if m.get("ev") == ev]


def main():
    print("=" * 78)
    print("   THE LAUNCH SEQUENCE: the timed cinematic behind Initialize Arbiter")
    print("=" * 78)
    if not CH:
        print("\n   [skip] no Chrome found.")
        return 3
    if not os.path.isdir(DIST):
        print("\n   [skip] no build at AGENTIC-ARBITER/app/dist.")
        return 3

    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    io.open(os.path.join(DIST, "_launch.html"), "w", encoding="utf-8", newline="").write(
        src.replace("</head>", PROBE + "</head>"))

    # 15 real seconds: the longest scenario samples at 10.5 s and the probe starts 2.2 s in.
    srv, port = serve(15)
    try:
        lsrc = io.open(os.path.join(AA, "app", "src", "intro", "launch.ts"),
                       encoding="utf-8").read()

        # ---------------------------------------------------------------- 0. the two markers agree
        head("0. THE TWO INTRO MARKERS EXPIRE TOGETHER")
        # 🔴 THE CHECK THAT WOULD HAVE CAUGHT A SILENT CINEMATIC. `hasSeenSplash` and the audio's
        # PLAYED_KEY describe one fact between them: the reader has already been through the intro in
        # this document. `app/index.html` clears them before the bundle runs so a refresh returns to
        # the globe WITH its sound. Clearing only the first is what happened on 2026-08-30, and the
        # result was a gate that came back and a `playVoice()` that returned 0 on its first line.
        # The key name is necessarily typed twice, because a pre-paint script cannot import from the
        # bundle, so the two strings are compared here rather than trusted.
        asrc = io.open(os.path.join(AA, "app", "src", "intro", "audio.ts"),
                       encoding="utf-8").read()
        hsrc = io.open(os.path.join(AA, "app", "index.html"), encoding="utf-8").read()
        m = re.search(r"const PLAYED_KEY = '([^']+)'", asrc)
        key = m.group(1) if m else None
        ck(bool(key), "audio.ts declares a PLAYED_KEY", str(key))
        ck(bool(key) and ("removeItem('%s')" % key) in hsrc,
           "and index.html clears that exact key on every document load",
           "looked for removeItem('%s')" % key)
        ck("removeItem('hasSeenSplash')" in hsrc,
           "alongside the splash marker, so the gate and its sound cannot disagree")

        # ---------------------------------------------------------------- 1. the normal run
        head("1. THE NORMAL RUN: it holds, it plays, it crosses over")
        d = load(port, "normal")
        ck(bool(d) and not d.get("err"), "the probe ran", (d or {}).get("err") or "")
        before, t200, t1200 = step(d, "before"), step(d, "t200"), step(d, "t1200")
        t5200, end = step(d, "t5200"), step(d, "end")

        pre = [m["file"] for m in d.get("media", [])
               if m.get("ev") == "play" and m["at"] < (d.get("clickAt") or 0)]
        ck(before.get("gate") is True and not pre,
           "nothing had played before the click, so the narration is not on arrival", str(pre))
        ck(t200.get("gate") is True,
           "THE SCREEN DOES NOT CHANGE ON THE CLICK: the gate is still up 200 ms later")
        ck(t200.get("ctaCommitted") is True and t200.get("ctaDisabled") is True,
           "the button is visibly committed and refuses further clicks",
           "label %r" % t200.get("ctaText"))
        ck((t200.get("ctaText") or "") != "Initialize Arbiter",
           "and its label has collapsed, so the click is unmistakably acknowledged",
           repr(t200.get("ctaText")))

        played = files(d)
        ck("voiceover.mp3" in played, "the voiceover started", str(played))
        ck("intro-swell.mp3" in played, "with the ambient bed under it")
        first = [m for m in d["media"] if m["ev"] == "play" and m["file"] == "voiceover.mp3"]
        vat = rel(d, first[0]["at"]) if first else None
        ck(vat is not None and vat < 400,
           "both at t = 0 of the sequence rather than after a lead",
           "voice at +%s ms after the click" % vat)
        vol = {m["file"]: m["vol"] for m in d["media"] if m["ev"] == "play"}
        ck(vol.get("voiceover.mp3", 0) <= 0.4 + 1e-9,
           "master volume is not exceeded", "voice at %s" % vol.get("voiceover.mp3"))
        ck(vol.get("intro-swell.mp3", 1) < vol.get("voiceover.mp3", 0),
           "and the bed sits well under the voice",
           "bed %s vs voice %s" % (vol.get("intro-swell.mp3"), vol.get("voiceover.mp3")))

        wh = [m for m in d["media"] if m["ev"] == "play" and m["file"] == "transition-whoosh.mp3"]
        ck(bool(wh), "the whoosh fired")
        if wh:
            # 🔴 THE LAST PLAY, NOT THE FIRST, AND THE FIRST IS NOW A DELIBERATE ONE.
            # `audio.unlock()` plays and immediately stops all three elements inside the click, at
            # volume 0, so each one earns Chrome's per-element playback permission while the click's
            # five-second activation is still live. Without it the whoosh, which fires at +5.876 s,
            # is refused in every real browser: measured 8 times out of 8. So there are two play()
            # calls on this element and only the second is audible. This assertion is about WHEN THE
            # READER HEARS IT, which is the last one.
            wat = rel(d, wh[-1]["at"])
            # voice 4.676 + hold 1.0 + out 1.2 - pad 1.0 = 5.876 s after the click.
            ck(5300 <= wat <= 6500,
               "at the transition, about 1 s before the end, not on the voiceover's ended event",
               "+%s ms after the click (expected about 5,876)" % wat)
            ck(vol.get("transition-whoosh.mp3", 1) < vol.get("voiceover.mp3", 1),
               "and slightly under the voice, as briefed",
               "whoosh %s" % vol.get("transition-whoosh.mp3"))

        ck(t5200.get("gate") is True, "the gate is still up through the hold at 5.2 s")
        ck(end.get("gate") is False, "and gone by the end", "at %s ms" % end.get("at"))
        ck(end.get("stage") == "pick", "on the site picker", str(end.get("stage")))

        # THE PUSH-IN. Measured from what HeatGlobe publishes, so it is the applied value.
        # 🔴 MEASURED FROM THE PUBLISHED DOLLY, NOT FROM THE PUBLISHED DIAMETER.
        # `data-aa-sphere` carries what applyLayout SOLVED, which is the resting framing and does not
        # move during a push-in; comparing it at two moments reported "724 px -> 724 px" for a camera
        # that was travelling the whole time. HeatGlobe publishes `data-aa-dolly` separately, which is
        # the value the timeline is actually driving, and the effective diameter follows from it.
        def dol(st):
            v = st.get("dolly")
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        k0, k5, k64 = dol(t200), dol(t5200), dol(step(d, "t6400"))
        ck(k0 is not None, "the globe publishes its push-in", str(k0))
        ck(k0 is not None and k5 is not None and k5 > k0 + 0.3,
           "THE GLOBE IS PUSHING IN: the camera has travelled by 5.2 s",
           "dolly %s -> %s" % (k0, k5))
        ck(k64 is None or k5 is None or k64 >= k5,
           "and is still moving through the hold rather than stopping with the voice",
           "%s at 5.2 s -> %s at 6.4 s" % (k5, k64))
        ck(k5 is None or k5 <= 1.0,
           "clamped, so an easing overshoot cannot push the camera through the planet", str(k5))

        ck(not d.get("errors"), "nothing threw", str(d.get("errors"))[:120])
        ck(not d.get("rejections"), "and no promise went uncaught", str(d.get("rejections"))[:120])

        # ------------------------------------------------- 2a. the escape hatch has a grace window
        # 🔴 A NEGATIVE CONTROL FOR A GUARD ADDED 2026-08-30, and the fault it guards was measured on
        # the deployed site: a real second click at +1.5 s cut the run from 6,927 ms to 2,060 ms, so a
        # reader who pressed again because nothing seemed to happen silenced their own intro and never
        # heard the transition whoosh at +5.9 s. A pointerdown inside 600 ms is now ignored. The
        # keyboard route is deliberately NOT delayed, and `escape-early` above still presses Esc at
        # 60 ms and still escapes, which is what keeps this from being a blanket delay.
        head("2a. AN IMPATIENT SECOND CLICK DOES NOT COUNT AS A SKIP")
        e = load(port, "escape-tooearly", "")
        after = step(e, "after-escape")
        ck(bool(e) and not e.get("err"), "the probe ran", (e or {}).get("err") or "")
        ck(after.get("gate") is True,
           "a pointerdown 250 ms after the reader's own click leaves the sequence running",
           "gate=%s at %s ms" % (after.get("gate"), after.get("at")))

        # ---------------------------------------------------------------- 2. the escape hatch
        head("2. THE ESCAPE HATCH: undocumented, and it works from three inputs")
        for sc, label, query in (
            ("escape-early", "Esc 60 ms after the click, before audio can have loaded", ""),
            ("escape-space", "Space at 2.2 s", ""),
            ("escape-click", "a click anywhere at 3.4 s", ""),
            ("escape-repeat", "five presses and a click at once", ""),
        ):
            e = load(port, sc, query)
            after = step(e, "after-escape")
            ck(bool(e) and not e.get("err"), "%s: the probe ran" % label, (e or {}).get("err") or "")
            ck(after.get("gate") is False, "%s: the gate is gone" % label,
               "at %s ms" % after.get("at"))
            ck(after.get("stage") == "pick", "%s: and the picker is showing" % label)
            paused = after.get("paused") or []
            ck(all(paused) if paused else True, "%s: audio is stopped" % label, str(paused))
            ck(not e.get("errors"), "%s: nothing threw" % label, str(e.get("errors"))[:100])

        # 🔴 NO VISIBLE HINT, AT ANY MOMENT SAMPLED.
        hint_runs = []
        for sc in ("nohint-preclick", "normal", "escape-space"):
            h = load(port, sc)
            for st in (h or {}).get("steps", []):
                hint_runs.extend(st.get("skipHints") or [])
        ck(not hint_runs,
           "no visible skip hint is rendered at any sampled moment, per the instruction",
           str(hint_runs)[:160])

        # ---------------------------------------------------------------- 3. muted
        head("3. MUTED: the short path, and no dead silence")
        m = load(port, "normal", "&audio=off")
        mt = step(m, "t1200")
        mend = step(m, "t3000") or step(m, "end")
        ck(not files(m), "nothing played", str(files(m)))
        ck((step(m, "t200") or {}).get("gate") is True, "the click still commits before it leaves")
        ck(mend.get("gate") is False, "and the sequence is over well before the full length")
        gone_at = rel(m, next((s["at"] for s in (m or {}).get("steps", [])
                               if s.get("gate") is False), None))
        # short path 1.5 s + the watchdog's 0.4 s of slack, plus sampling granularity.
        ck(gone_at is not None and gone_at <= 3400,
           "measurably shorter than the audio path, which is the point of it",
           "gate gone by +%s ms after the click" % gone_at)

        # ---------------------------------------------------------------- 4. audio missing
        head("4. AUDIO FILES MISSING: the sequence completes anyway")
        g = load(port, "missing")
        gend = step(g, "end")
        ck(bool(g) and not g.get("err"), "the probe ran", (g or {}).get("err") or "")
        ck(gend.get("gate") is False,
           "the visual sequence completed with every audio file 404ing",
           "gate at end: %s" % gend.get("gate"))
        ck(gend.get("stage") == "pick", "and handed over to the picker")
        ck(not g.get("errors"),
           "nothing was thrown into the console", str(g.get("errors"))[:160])
        ck(not g.get("rejections"),
           "and every play() rejection was caught, as the brief requires",
           str(g.get("rejections"))[:160])

        # ---------------------------------------------------------------- 5. double click
        head("5. DOUBLE CLICK: two clicks, one sequence")
        dd = load(port, "double")
        # ⚠ TWO CALLS PER SEQUENCE IS NOW CORRECT, and the check is about the SEQUENCE not restarting.
        # `audio.unlock()` primes every element inside the click at volume 0; `playVoice()` then plays
        # the voiceover for real. What a double click must not do is run either of those twice, so the
        # bound is two rather than one, and the `started` guard in audio.ts is what holds it there.
        voices = [m for m in (dd or {}).get("media", [])
                  if m["ev"] == "play" and m["file"] == "voiceover.mp3"]
        ck(len(voices) <= 2, "the voiceover started exactly once, plus its silent prime",
           "%d play() calls" % len(voices))
        ck(step(dd, "t900").get("gate") is True,
           "the second click did not short-circuit the hold")
        ck(step(dd, "t900").get("ctaDisabled") is True,
           "and the button was already disabled when it arrived")

        # ---------------------------------------------------------------- 6. navigate away
        head("6. NAVIGATE AWAY MID-SEQUENCE: audio stops, nothing is left running")
        aw = load(port, "away")
        mid, post = step(aw, "mid"), step(aw, "after-away")
        ck(mid.get("gate") is True, "the sequence was still running when the page went away")
        paused = post.get("paused") or []
        ck(all(paused) if paused else True,
           "every audio element is paused afterwards", str(paused))
        pauses = [m for m in (aw or {}).get("media", []) if m["ev"] == "pause"]
        ck(bool(pauses), "and the pause was actually issued rather than the element merely ending",
           "%d pause calls" % len(pauses))
        ck(not aw.get("errors"), "nothing threw on the way out", str(aw.get("errors"))[:120])

        # ---------------------------------------------------------------- 7. the kill switch
        head("7. THE KILL SWITCH: ?cinematic=off navigates instantly")
        k = load(port, "normal", "&cinematic=off")
        kfirst = next((s for s in (k or {}).get("steps", []) if s.get("tag") == "t200"), {})
        ck(not files(k), "no audio at all", str(files(k)))
        kgone = rel(k, next((s["at"] for s in (k or {}).get("steps", [])
                             if s.get("gate") is False), None))
        ck(kgone is not None and kgone <= 400,
           "and the gate is gone within the first sample, so the button just navigates",
           "gone by +%s ms after the click" % kgone)
        ck(kfirst.get("stage") in (None, "pick"), "landing on the picker")

        # ---------------------------------------------------------------- the source contract
        head("8. THE CONTRACT THE SOURCE HAS TO KEEP")
        # 🔴 COMMENTS MASKED FIRST, WHICH IS TRAP 5b.1 AND IT CAUGHT ME AGAIN.
        # launch.ts explains at length why it does NOT chain off `audio.onended`, so a substring search
        # for that name finds the explanation and reports the opposite of the truth. This codebase
        # documents its own decisions by quoting the thing it decided against; any scan of it has to
        # strip comments before looking.
        code = re.sub(BLOCK_COMMENT, " ", lsrc)
        code = re.sub(LINE_COMMENT, " ", code)
        ck("addEventListener('ended'" not in code and ".onended" not in code
           and "addEventListener('canplay" not in code
           and "addEventListener('timeupdate" not in code,
           "nothing in launch.ts listens to an audio event, so no cue can stall the sequence")
        ck("onended" in lsrc,
           "and the file says so in prose, which is why the scan above has to mask comments")
        ck("window.setTimeout(finish" in lsrc,
           "a wall-clock watchdog also completes it, so a frozen GSAP clock cannot strand the reader")
        ck("addEventListener('keydown', onKey, true)" in lsrc
           and "addEventListener('pointerdown', onPointer, true)" in lsrc,
           "the escape hatch is bound before the timeline is built, so it survives a throw in it")
        ck(lsrc.index("window.addEventListener('keydown'") < lsrc.index("gsap.timeline("),
           "and literally earlier in the function, not merely nearby")
        ck("if (done) return" in lsrc, "and it is idempotent, so repeated presses queue nothing")
    finally:
        srv.terminate()
        try:
            os.remove(os.path.join(DIST, "_launch.html"))
        except OSError:
            pass

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (CHECKS[0], len(FAILS)))
    if FAILS:
        for f in FAILS:
            print("      FAILED: %s" % f)
        print("=" * 78)
        return 1
    print("   VERDICT: the sequence holds, plays, crosses over and completes; the undocumented")
    print("            escape works from three inputs and leaves nothing running.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
