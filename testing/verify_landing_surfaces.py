"""THE LANDING PAGE, after the 2026-08-30 brief: the copy, the value card, the loop and the reload.

Driven over the DevTools Protocol (see testing/cdp.py) because three of the five things checked here
cannot be produced from inside the page: a real navigation and back, a real reload, and the state of
a GSAP tween that only exists while the diagram is mounted.

WHAT IT ASSERTS:
  1. the two rewritten hero bullets, verbatim;
  2. the value card reads PRICE, then the free-cooling figure, then SITES, in that order; its money
     pair is POSITIVE and equals demo/portfolio.json's `usd_mid_*`; the phrase "chiller" is gone from
     it; and only numerals are bold;
  3. the two outer ring labels sit strictly INSIDE the loop path, measured against the path itself
     rather than against the control points it curves toward;
  4. the revolving dot exists and is moving on first load, and STILL DOES after a trip to the
     configure stage and back;
  5. a reload returns the reader to the landing gate, globe and all, while pick -> configure -> pick
     inside one document does not.

Run from the repository root:  python testing/verify_landing_surfaces.py
"""
import io
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
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
PASS, FAIL = [], []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-58s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


HELPERS = r"""
window.__lp = (function(){
  /* `textContent` drops <br> entirely, which glued "a year" to "gained" in the first run's
     output. Reading innerText where it exists keeps the line break as whitespace. */
  function norm(s){ return (s||'').replace(/\s+/g,' ').trim(); }
  function txt(el){ return norm(el ? (el.innerText !== undefined ? el.innerText
                                                                 : el.textContent) : ''); }
  return {
    bullets: function(){ return Array.prototype.map.call(
      document.querySelectorAll('[data-aa-hero="prose"] > ul > li'),
      function(li){ return norm(li.textContent); }); },
    /* The value card, block by block, in DOM order. Bold runs are reported separately so a check can
       insist that only figures are emphasised. */
    valueCard: function(){
      var card = document.querySelector('.aa-bubble-value'); if(!card) return null;
      var blocks = Array.prototype.map.call(card.children, function(el){
        return {cls: el.className, text: txt(el),
                bold: Array.prototype.map.call(el.querySelectorAll('b'),
                        function(b){ return norm(b.textContent); }),
                num: el.querySelector('.aa-bubble-num')
                     ? norm(el.querySelector('.aa-bubble-num').textContent) : null,
                unit: txt(el.querySelector('.aa-bubble-unit'))};
      });
      return {blocks: blocks, text: norm(card.textContent)};
    },
    /* 🔴 THE LOOP MEASURED AS A CURVE, NOT AS ITS CONTROL POINTS. `getPointAtLength` walks the real
       path, so the extent reported here is the one the browser draws. The previous fix anchored the
       labels to `XS[0] - 78`, the x of both control points on the left turn, which a cubic never
       reaches: the curve only gets to 3/4 of that offset. */
    ringFit: function(){
      var path = document.getElementById('aa-ring-track'); if(!path) return null;
      var L = path.getTotalLength(), pts = [];
      for (var i=0;i<=2000;i++){ var p = path.getPointAtLength(L*i/2000); pts.push([p.x,p.y]); }
      function extentAtY(y0,y1){
        var lo=Infinity, hi=-Infinity;
        for (var i=0;i<pts.length;i++){
          var x=pts[i][0], y=pts[i][1];
          if (y>=y0-0.5 && y<=y1+0.5){ if(x<lo) lo=x; if(x>hi) hi=x; }
        }
        return {lo:lo, hi:hi};
      }
      var notes = Array.prototype.slice.call(document.querySelectorAll('.aa-ring-note'));
      return notes.map(function(t, i){
        var b = t.getBBox();
        var e = extentAtY(b.y, b.y + b.height);
        return {i:i, text:norm(t.textContent),
                x:Math.round(b.x*10)/10, right:Math.round((b.x+b.width)*10)/10,
                y:Math.round(b.y*10)/10, bottom:Math.round((b.y+b.height)*10)/10,
                loopLo: isFinite(e.lo)?Math.round(e.lo*10)/10:null,
                loopHi: isFinite(e.hi)?Math.round(e.hi*10)/10:null};
      });
    },
    /* The dot: present, un-hidden, and actually moving. Its transform is what MotionPathPlugin
       writes, so two samples that differ prove the tween is live rather than merely constructed. */
    pulse: function(){
      var el = document.querySelector('[data-aa-pulse]'); if(!el) return null;
      var cs = getComputedStyle(el);
      return {present:true, visibility:cs.visibility, opacity:cs.opacity,
              transform:cs.transform, ringAttr:document.body.dataset.aaRing || null,
              introAttr:document.body.getAttribute('data-aa-intro')};
    },
    gate: function(){ return {present: !!document.querySelector('.aa-gate'),
                              globe: !!document.querySelector('.aa-splash-globe-canvas'),
                              seen: (function(){ try{
                                return window.sessionStorage.getItem('hasSeenSplash'); }
                                catch(e){ return 'unreadable'; } })(),
                              stage: document.body.dataset.stage || null}; }
  };
})(); 1
"""


def moving(c, label):
    """Two samples of the dot's transform, a beat apart. Different means the tween is running."""
    a = json.loads(c.eval("JSON.stringify(window.__lp.pulse())") or "null")
    time.sleep(0.7)
    b = json.loads(c.eval("JSON.stringify(window.__lp.pulse())") or "null")
    if not a or not b:
        return None, None, False
    return a, b, (a["transform"] != b["transform"])


def main():
    if not os.path.isdir(DIST):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist")
        return 3
    with io.open(os.path.join(DEMO, "portfolio.json"), encoding="utf-8") as f:
        pf = json.load(f)
    print("   from demo/portfolio.json:  usd_mid %s to %s   gain %s h   sites %d/%d"
          % (round(pf["usd_mid_lo"]), round(pf["usd_mid_hi"]), round(pf["gain_h_per_year"]),
             pf["sites_gaining"], pf["sites_summed"]))

    port = free_port()
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    base = "http://127.0.0.1:%d/app/?facility=metro_ashburn" % port
    try:
        # ============================================ A. copy and card, with the gate out of the way
        with Chrome(base + "&motion=off", width=1600, height=1100) as c:
            c.goto(settle=3.0)
            c.poll("!!document.querySelector('.aa-bubble-value')", timeout=40)
            c.eval(HELPERS)

            head("1. THE TWO REWRITTEN HERO BULLETS")
            bl = json.loads(c.eval("JSON.stringify(window.__lp.bullets())"))
            ck(len(bl) == 4, "four bullets, unchanged in number", str(len(bl)))
            want1 = ("Data centres run mechanical chillers even when outside air could provide "
                     "the necessary cooling.")
            want2 = ('FortyGuard forecasts heat at 2 m, the height a ground-mounted condenser '
                     'breathes, which turns "right now" into hours of prior notice.')
            ck(bl and bl[0] == want1, "bullet 1 reads as specified", bl[0] if bl else "")
            ck(len(bl) > 1 and bl[1] == want2, "bullet 2 reads as specified",
               bl[1] if len(bl) > 1 else "")

            head("2. THE VALUE CARD: price, then the figure, then sites")
            vc = json.loads(c.eval("JSON.stringify(window.__lp.valueCard())") or "null")
            if ck(bool(vc), "the value card is on screen"):
                b = vc["blocks"]
                ck(len(b) == 3, "three blocks and no more", str(len(b)))
                ck(b[0]["text"].startswith("worth "), "PRICE is first", b[0]["text"][:74])
                ck("aa-bubble-hero" in b[1]["cls"], "the free-cooling figure is second",
                   "%s %s" % (b[1]["num"], b[1]["unit"]))
                ck(b[2]["text"].startswith("238 of 250"), "SITES is third", b[2]["text"][:74])

                # the money, against the artefact
                def m(v):
                    return "$%.1fM" % (v / 1e6)
                ck(m(pf["usd_mid_lo"]) in b[0]["text"] and m(pf["usd_mid_hi"]) in b[0]["text"],
                   "the money pair is portfolio.json's usd_mid_*",
                   "expected %s and %s" % (m(pf["usd_mid_lo"]), m(pf["usd_mid_hi"])))
                ck("-$" not in vc["text"], "no negative figure anywhere on the card")
                ck(pf["usd_mid_lo"] > 0 and pf["usd_mid_hi"] > 0,
                   "and the artefact behind it is genuinely positive at both ends",
                   "%.0f / %.0f" % (pf["usd_mid_lo"], pf["usd_mid_hi"]))

                ck("free-cooling hours" in vc["text"], "it says free-cooling hours")
                ck("chiller" not in vc["text"].lower(), "and no longer says chiller anywhere",
                   vc["text"][:60])

                # only figures are bold
                import re
                bolds = [x for blk in b for x in blk["bold"]]
                bad = [x for x in bolds if not re.fullmatch(r"[+\-]?[$]?[\d,.]+[kM%]?", x)]
                ck(not bad, "every bold run is a figure and nothing else",
                   "%d bold runs: %s" % (len(bolds), ", ".join(bolds)))

        # ============================================ B. the dot, across a real navigation
        with Chrome(base, width=1600, height=1100) as c:
            c.goto(settle=2.0)
            c.eval(HELPERS)
            head("4. THE REVOLVING DOT, on arrival and on return")
            g = json.loads(c.eval("JSON.stringify(window.__lp.gate())"))
            ck(g["present"], "the gate is up on a fresh load", "globe canvas: %s" % g["globe"])
            # 🔴 WAIT FOR AN *ENABLED* BUTTON. IntroGate disables the CTA until the three audio files
            # report enough data, and a disabled button silently ignores `.click()`. The first version
            # of this clicked into the void and then reported that the loops never started, which was
            # true and had nothing to do with the loops. Same trap verify_launch.py records.
            armed = c.poll("(function(){var b=document.querySelector('.shiny-cta');"
                           "return b && !b.disabled ? 1 : 0;})()", timeout=30)
            ck(bool(armed), "the gate's call to action arms")
            c.eval("document.querySelector('.shiny-cta').click(); 1")
            # The cinematic holds on the globe through the voiceover before it hands over, so this is
            # a wall-clock wait on a real sequence rather than a render.
            passed = c.poll("!document.querySelector('.aa-gate')", timeout=45)
            ck(bool(passed), "and the gate hands over")
            ok = c.poll("!!document.querySelector('[data-aa-pulse]') && "
                        "document.body.dataset.aaRing === 'running'", timeout=45)
            ck(bool(ok), "the loops start after the gate is passed")
            head("3. THE RING LABELS STAY INSIDE THE LOOP")
            fit = json.loads(c.eval("JSON.stringify(window.__lp.ringFit())") or "null")
            if not fit:
                ck(False, "the ring is on screen", "no #aa-ring-track")
            else:
                ck(len(fit) == 5, "five notes", str(len(fit)))
                for t in fit:
                    inside = (t["loopLo"] is None
                              or (t["x"] >= t["loopLo"] and t["right"] <= t["loopHi"]))
                    ck(inside, "inside the loop: %-31s" % t["text"][:31],
                       "text x %.1f-%.1f, loop x %.1f-%.1f at that height"
                       % (t["x"], t["right"], t["loopLo"] or -1, t["loopHi"] or -1))

            head("4b. THE DOT ON FIRST ARRIVAL")
            a1, b1, mv1 = moving(c, "first")
            ck(bool(a1) and a1["visibility"] == "visible", "the dot is visible",
               (a1 or {}).get("visibility"))
            ck(mv1, "and it is moving", "%s -> %s" % ((a1 or {}).get("transform", "")[:34],
                                                      (b1 or {}).get("transform", "")[:34]))

            # leave for the configure stage, the way the user described
            c.eval("""(function(){var b=document.querySelectorAll('button');
              for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||''))
                { b[i].click(); return 1; } return 0;})()""")
            left = c.poll("document.body.dataset.stage === 'configure'", timeout=40)
            ck(bool(left), "reached the configure stage")
            time.sleep(0.8)
            gone = json.loads(c.eval("JSON.stringify(window.__lp.pulse())") or "null")
            ck(gone is None, "the diagram is unmounted while away, as designed",
               "pulse present: %s" % bool(gone))

            # and back
            c.eval("""(function(){var b=document.getElementById('backtopick');
              if(b){b.click(); return 1;} return 0;})()""")
            back = c.poll("document.body.dataset.stage === 'pick' && "
                          "!!document.querySelector('[data-aa-pulse]')", timeout=40)
            ck(bool(back), "returned to the landing stage with the diagram remounted")
            time.sleep(0.6)
            a2, b2, mv2 = moving(c, "return")
            ck(bool(a2), "the dot exists again", "ring attr: %s" % (a2 or {}).get("ringAttr"))
            ck(bool(a2) and a2["visibility"] == "visible",
               "IT IS VISIBLE ON THE RETURN, which was the bug", (a2 or {}).get("visibility"))
            ck(mv2, "and it is moving again", "%s -> %s" % ((a2 or {}).get("transform", "")[:34],
                                                            (b2 or {}).get("transform", "")[:34]))
            n = int(c.eval("document.querySelectorAll('[data-aa-pulse]').length"))
            ck(n == 1, "exactly one dot, so nothing doubled up", "%d found" % n)

            head("5. A RELOAD RETURNS TO THE LANDING GATE")
            seen = c.eval("(function(){try{return sessionStorage.getItem('hasSeenSplash');}"
                          "catch(e){return 'x';}})()")
            ck(seen == "true", "passing the gate set hasSeenSplash for this document", str(seen))
            g2 = json.loads(c.eval("JSON.stringify(window.__lp.gate())"))
            ck(not g2["present"], "and the gate did not come back on the in-document round trip",
               "stage %s" % g2["stage"])
            c.goto(settle=3.0)          # a real document load, which is what a refresh is
            c.eval(HELPERS)
            g3 = json.loads(c.eval("JSON.stringify(window.__lp.gate())"))
            ck(g3["present"], "AFTER A RELOAD THE GATE IS BACK", "globe canvas: %s" % g3["globe"])
            ck(g3["globe"], "with its globe canvas")
            ck(g3["stage"] in ("pick", None), "on the landing stage", str(g3["stage"]))
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-50s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: the copy reads as written, the card is positive and in order, the labels")
        print("            clear the curve, the dot survives a round trip, and a refresh comes home.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
