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
     it was gated on the value it had just written. This requires it to be present with the sound off.

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
    return r;
  };
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
    return json.loads(c.eval("JSON.stringify(window.__A)", user_gesture=False))


def report(ev, label):
    by = {}
    for e in ev or []:
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
            ck(ev is not None, "the call to action armed and was clicked")
            report(ev, "fresh:")

        # ============================================= 2. after a reload
        head("2. AFTER A RELOAD, which is the path that went silent")
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.5)
            c.eval(PROBE, user_gesture=False)     # before the click, or __A does not exist yet
            first = drive(c)
            ck(bool(first), "the first load plays")
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
            ck(ev is not None, "the gate is back and was clicked again")
            report(ev, "reload:")

        # ============================================= 3. the mute toggle has a way back
        head("3. THE MUTE TOGGLE IS REACHABLE WITH THE SOUND OFF")
        with Chrome(url, width=1400, height=900, extra=STRICT) as c:
            c.goto(settle=1.0)
            c.eval(PROBE, user_gesture=False)
            c.eval("localStorage.setItem('aa-audio','off'); 1", user_gesture=False)
            c.goto(settle=1.8)
            got = c.eval("(function(){try{return localStorage.getItem('aa-audio');}"
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
