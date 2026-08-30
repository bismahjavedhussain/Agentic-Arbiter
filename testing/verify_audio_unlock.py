"""THE INTRO'S THREE SOUNDS ACTUALLY PLAY, under Chrome's real autoplay rule, on a real click.

🔴 WHY THIS FILE EXISTS SEPARATELY FROM verify_launch.py, WHICH IS 71 GREEN CHECKS ABOUT THE SAME
SEQUENCE. That file cannot see an autoplay refusal, and it is not a gap in its assertions but in its
harness. It launches Chrome with `--autoplay-policy=no-user-gesture-required` and presses the button
with `el.click()`, which carries NO user activation at all. Between them those two make every
permission question unanswerable: the flag says permission is never needed, and the synthetic click
would not have supplied it anyway. So the suite was green while the transition whoosh was refused
8 times out of 8 in every real browser.

THIS FILE INVERTS BOTH. Chrome runs with `--autoplay-policy=user-gesture-required`, appended after
cdp.py's own permissive flag so it wins, and the button is pressed with a real
`Input.dispatchMouseEvent`. Every probe passes `user_gesture=False`, because a CDP evaluate with the
default grants an activation of its own and would hand the page the permission this check exists to
measure.

WHAT IT GUARDS, and all three were live faults on 2026-08-30:
  1. THE MARKER PAIR. `hasSeenSplash` and `aa-intro-audio-played` both live in sessionStorage and
     describe one fact between them. When only the first was cleared on load, a refresh brought the
     gate back and `playVoice()` returned 0 on its first line: the reader clicked Initialize Arbiter
     and got 6.9 s of silence. So this drives a RELOAD and requires sound on the second load too.
  2. THE PER-ELEMENT UNLOCK. Chrome's transient activation lasts 5 s and the media unlock is per
     element. The whoosh fires at +5.9 s, derived from the crossfade landing on its low pad, so it
     can never earn its own permission. `audio.unlock()` plays and immediately stops all three inside
     the click. This requires the whoosh's LATE attempt to succeed, not merely its prime.
  3. THE ONE-WAY MUTE. The corner toggle wrote `aa-audio = 'off'` and was then not rendered, because
     it was gated on the value it had just written. This requires it to be present with the sound off,
     and it requires a reader still carrying the retired key to be heard anyway.
  4. THE PRIME THAT STOPPED THE SEQUENCE, which is fault 2's own fix biting back and is the reason
     this file no longer trusts a play() promise. `unlock()` pauses each element when its play promise
     resolves, and that callback landed 13 ms AFTER `playVoice()` had started the same element: the
     reader heard 8 ms of a 4,676 ms narration while all three promises resolved green. So the checks
     below sample `paused`, `muted` and `volume` on every animation frame and require a FLOOR OF
     AUDIBLE MILLISECONDS per file. A permission granted is not a sound heard, and only the second one
     is what the reader asked for.

Run from the repository root:  python testing/verify_audio_unlock.py
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cdp import Chrome, free_port                                    # noqa: E402

DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
STRICT = ["--autoplay-policy=user-gesture-required"]
PASS, FAIL = [], []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-56s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


# Every play() call is recorded with the activation state at the moment it was made, so a pass cannot
# be mistaken for "it was allowed anyway".
PROBE = r"""
window.__A = [];
window.__EL = {};
(function(){
  var P = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function(){
    var el = this, src = (el.currentSrc || el.src || '').split('/').pop();
    var active = navigator.userActivation ? navigator.userActivation.isActive : null;
    var t = Math.round(performance.now());
    var r = P.apply(this, arguments);
    if (r && r.then) r.then(
      function(){ window.__A.push({f:src, ok:true,  t:t, active:active,
                                   vol: Math.round(el.volume*100)/100}); },
      function(e){ window.__A.push({f:src, ok:false, t:t, active:active,
                                   err: e && e.name}); });
    else window.__A.push({f:src, ok:'no-promise', t:t, active:active});
    window.__EL[src] = el;
    return r;
  };
})();

/* WHO PAUSED IT, which is the question a play() log cannot answer. Recorded rather than asserted on:
   it is printed only when an element failed to reach its audible floor, and that one frame is what
   turned "the sound is gone" into a file and a line number in about a minute. */
window.__P = [];
(function(){
  var U = HTMLMediaElement.prototype.pause;
  HTMLMediaElement.prototype.pause = function(){
    var src = (this.currentSrc || this.src || '').split('/').pop();
    var f = (new Error()).stack || '';
    f = f.split(String.fromCharCode(10))[2] || '';   /* no escape: this string is a raw literal */
    window.__P.push({f:src, t:Math.round(performance.now()),
                     ct:Math.round((this.currentTime||0)*1000), at:f.trim().slice(0,90)});
    return U.apply(this, arguments);
  };
})();

/* AUDIBLE MILLISECONDS, WHICH IS THE ONLY THING THAT ANSWERS "DID THE READER HEAR IT".
   A resolved play() promise says the browser ALLOWED playback to begin. It says nothing about whether
   playback then continued, and on 2026-08-30 that gap was the whole bug: three promises resolved
   green while the elements they belonged to had already been paused and rewound 13 ms later. This
   samples the only two properties that decide whether sound is leaving the machine. */
window.__MS = {};
(function(){
  var last = performance.now();
  function tick(){
    var now = performance.now(), dt = now - last; last = now;
    for (var k in window.__EL) {
      var el = window.__EL[k];
      if (!el.paused && !el.muted && el.volume > 0) window.__MS[k] = (window.__MS[k] || 0) + dt;
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})(); 1
"""

WANT = ('voiceover.mp3', 'intro-swell.mp3', 'transition-whoosh.mp3')


def drive(c):
    """Press Initialize Arbiter with a REAL pointer and let the whole sequence run."""
    if not c.poll("(function(){var b=document.querySelector('.shiny-cta');"
                  "return b && !b.disabled ? 1 : 0;})()", timeout=30, ):
        return None
    r = c.eval("""JSON.stringify((function(){
        var b = document.querySelector('.shiny-cta'); var q = b.getBoundingClientRect();
        return {cx: Math.round(q.x + q.width/2), cy: Math.round(q.y + q.height/2)};})())""",
               user_gesture=False)
    r = json.loads(r)
    c.click(r["cx"], r["cy"], settle=0.3)
    time.sleep(9.5)
    return json.loads(c.eval("JSON.stringify({a:window.__A, ms:window.__MS, p:window.__P})",
                             user_gesture=False))


# HOW MANY MILLISECONDS OF EACH FILE THE READER HAS TO ACTUALLY HEAR.
#
# 🔴 EVERY ONE OF THESE FLOORS IS WELL UNDER WHAT A HEALTHY BUILD MEASURES, AND THAT IS DELIBERATE.
# The point is not to pin the mix down to the millisecond, it is to be unable to pass while an
# element is paused. Healthy, measured on this machine: voiceover 6,862 ms, swell 6,862 ms,
# whoosh 996 ms. Broken by the unlock race: voiceover 5 ms, swell 11 ms, whoosh 996 ms - so the
# whoosh's floor is the loose one because the whoosh was never the casualty.
#
# ⚠ DO NOT REPLACE THIS WITH A `currentTime` ASSERTION. It is the obvious thing to reach for and it
# fails on a healthy build here: this box's Chrome has no audio output device, so the media clock
# never advances and a fully-buffered voiceover playing correctly sits at currentTime = 47 ms for as
# long as you watch it. `paused`, `muted` and `volume` are properties of the element and are all
# truthful without a sound card; the clock is not.
FLOOR_MS = {'voiceover.mp3': 3000, 'intro-swell.mp3': 3000, 'transition-whoosh.mp3': 500}


def report(res, label):
    ev = (res or {}).get("a") or []
    ms = (res or {}).get("ms") or {}
    pauses = (res or {}).get("p") or []
    by = {}
    for e in ev:
        by.setdefault(e["f"], []).append(e)
    ok = True
    for f in WANT:
        es = by.get(f, [])
        played = [e for e in es if e["ok"] is True]
        late = [e for e in played if e["t"] > 0 and e is es[-1] and len(es) > 1]
        ok = ck(bool(played), "%s  %s plays" % (label, f[:22]),
                "%d attempt(s), %d played%s" % (
                    len(es), len(played),
                    "" if played else "  " + ", ".join(str(e.get("err")) for e in es))) and ok
        if f == 'transition-whoosh.mp3' and es:
            last = es[-1]
            ck(last["ok"] is True and last["t"] > 4000,
               "%s  and its LATE attempt survives the 5 s window" % label,
               "last attempt at t=%d, active=%s, %s"
               % (last["t"], last["active"], "played" if last["ok"] is True else last.get("err")))

    # ---- and now the only question that matters: was any of it AUDIBLE?
    for f in WANT:
        got = int(ms.get(f, 0))
        floor = FLOOR_MS[f]
        good = ck(got >= floor, "%s  %s is AUDIBLE, not merely allowed" % (label, f[:22]),
                  "%d ms un-paused at volume > 0, floor %d" % (got, floor))
        ok = good and ok
        if not good:
            # The play() log will be green here, so it cannot explain this. The pause frame can.
            for q in [x for x in pauses if x["f"] == f][:3]:
                print("        ^ paused at t=%d, %d ms in, by %s" % (q["t"], q["ct"], q["at"]))
    return ok


def main():
    if not os.path.isdir(DIST):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist")
        return 3
    port = free_port()
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    url = "http://127.0.0.1:%d/app/?facility=metro_ashburn" % port
    try:
        # ============================================= 1. a fresh tab
        head("1. A FRESH TAB, strict autoplay, a real pointer click")
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.5)
            c.eval(PROBE, user_gesture=False)
            act = c.eval("navigator.userActivation ? navigator.userActivation.isActive : 'unsupported'",
                         user_gesture=False)
            ck(act is False or act == 'unsupported',
               "the page has no user activation before the click, so this test is real",
               "isActive = %s" % act)
            ev = drive(c)
            ck(bool(ev and ev.get("a")), "the call to action armed and was clicked")
            report(ev, "fresh:")

        # ============================================= 2. after a reload
        head("2. AFTER A RELOAD, which is the path that went silent")
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.5)
            c.eval(PROBE, user_gesture=False)     # before the click, or __A does not exist yet
            first = drive(c)
            ck(bool(first and first.get("a")), "the first load plays")
            marker = c.eval("(function(){try{return sessionStorage.getItem("
                            "'aa-intro-audio-played');}catch(e){return 'x';}})()",
                            user_gesture=False)
            ck(marker == '1', "and it records that it played, for this document only", str(marker))
            c.goto(settle=1.8)                       # a real reload
            after = c.eval("(function(){try{return sessionStorage.getItem("
                           "'aa-intro-audio-played');}catch(e){return 'x';}})()",
                           user_gesture=False)
            ck(after is None,
               "THE RELOAD CLEARS THAT MARKER, alongside hasSeenSplash", str(after))
            c.eval(PROBE, user_gesture=False)
            ev = drive(c)
            ck(bool(ev and ev.get("a")), "the gate is back and was clicked again")
            report(ev, "reload:")

        # ============================================= 3. a reader already carrying the OLD key
        head("3. A STALE `aa-audio` FROM THE BROKEN WINDOW DOES NOT SILENCE A NEW LOAD")
        # 🔴 THE KEY WAS RENAMED, AND THIS IS WHAT THE RENAME BUYS. Until 2026-08-30 the mute toggle
        # was rendered only when audio was already on, which is the value it writes, so one press left
        # a reader with 'off' stored and no control to undo it. Making the control visible again does
        # nothing for someone already carrying that value: they reported silence a second time with
        # the fix verifiably deployed. `aa-audio` is dead and `aa-audio-choice` replaces it, so the
        # trapped value expires once.
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.0)
            c.eval("localStorage.setItem('aa-audio','off'); 1", user_gesture=False)
            c.goto(settle=1.8)
            c.eval(PROBE, user_gesture=False)
            ev = drive(c)
            ck(bool(ev and ev.get("a")), "the gate opened for a reader carrying the old key")
            report(ev, "stale:")

        # ============================================= 4. and the CURRENT key still works
        head("4. THE MUTE TOGGLE IS REACHABLE WITH THE SOUND OFF")
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.0)
            c.eval(PROBE, user_gesture=False)
            c.eval("localStorage.setItem('aa-audio-choice','off'); 1", user_gesture=False)
            c.goto(settle=1.8)
            got = c.eval("(function(){try{return localStorage.getItem('aa-audio-choice');}"
                         "catch(e){return 'x';}})()", user_gesture=False)
            ck(got == 'off', "the reader's stored choice is 'off'", str(got))
            c.eval(PROBE, user_gesture=False)
            drive(c)
            time.sleep(0.8)
            btn = json.loads(c.eval("""JSON.stringify((function(){
                var b = document.querySelector('.aa-mutebtn');
                if (!b) {
                  var all = document.querySelectorAll('button, [role=button]');
                  for (var i=0;i<all.length;i++){
                    var l=(all[i].getAttribute('aria-label')||'')+' '+(all[i].title||'');
                    if (/sound|audio|mute|volume/i.test(l)) { b = all[i]; break; }
                  }
                }
                return b ? {found:true, label:b.getAttribute('aria-label'),
                            pressed:b.getAttribute('aria-pressed')} : {found:false};})())""",
                                    user_gesture=False))
            ck(btn["found"],
               "A CONTROL TO TURN THE SOUND BACK ON IS ON SCREEN, which was the trap",
               str(btn))
            ck(btn.get("pressed") == 'true',
               "and it shows the sound as off rather than lying about it",
               "aria-pressed=%s, label=%r" % (btn.get("pressed"), btn.get("label")))
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-48s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: all three cues play under Chrome's real autoplay rule, on a fresh tab and")
        print("            after a reload, and a muted reader can always find the way back.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
