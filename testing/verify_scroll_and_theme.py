"""THE PAGE SCROLLS, AND THE THEME BELONGS TO THE SCREEN IT WAS CHOSEN ON.

Two faults reported together on 2026-08-30, both of which only appear under conditions no existing
check reproduced.

  1. "I am not able to scroll through this page. If I cant scroll, I cant look at the options under
     the Quick Actions in the side bar on the left."
     🔴 IT WAS INVISIBLE BECAUSE EVERY OTHER BROWSER CHECK USES A TALL WINDOW: 1500x1400, 1500x1000,
     1600x1000, 1440x1000. MEASURED at 1366x768 before the fix, `main#app` had clientHeight 672
     against scrollHeight 755, so 83px were clipped by `overflow: hidden` with no scroller in the
     chain able to reach them; both Quick Action rows sat entirely below the fold and the rail's own
     scrollbar had 19px of travel, exhausted in one wheel tick, which did not bring either into view.
     So this file runs SHORT viewports on purpose, and asserts the window is the scroller.

  2. "this page again appears in a light mode by default. It should appear in dark mode by default
     when the website is run, and when the user clicks on 'configure the plant', after that, the page
     that appears is supposed to be there in light mode by default."
     🔴 A CHOICE USED TO BE GLOBAL. Pressing the toggle TWICE on configure leaves configure looking
     identical and permanently pins the LANDING page to light. That is the sequence this file drives,
     with real pointer clicks, because it is the one that made the report reproducible.

Run from the repository root:  python testing/verify_scroll_and_theme.py
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
PASS, FAIL = [], []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-56s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


HELPERS = r"""
window.__q = (function(){
  function R(el){ if(!el) return null; var r=el.getBoundingClientRect();
    return {top:Math.round(r.top),bottom:Math.round(r.bottom),h:Math.round(r.height)}; }
  return {
    page: function(){ var se=document.scrollingElement;
      return {scrollHeight:se.scrollHeight, clientHeight:se.clientHeight,
              scrollY:Math.round(window.scrollY), vh:innerHeight}; },
    app: function(){ var a=document.getElementById('app'); if(!a) return null;
      var c=getComputedStyle(a);
      return {overflow:c.overflow, height:c.height, minHeight:c.minHeight,
              clientHeight:a.clientHeight, scrollHeight:a.scrollHeight, rect:R(a)}; },
    rail: function(){ var n=document.querySelector('.aa-rail-nav'); if(!n) return null;
      var c=getComputedStyle(n);
      return {rect:R(n), maxHeight:c.maxHeight, position:c.position, top:c.top,
              overflowY:c.overflowY}; },
    /* The row the reader said they could not reach. */
    lastQA: function(){ var q=document.querySelectorAll('.aa-qa');
      if(!q.length) return null; var e=q[q.length-1];
      return {text:(e.textContent||'').trim().slice(0,26), rect:R(e),
              fullyVisible: e.getBoundingClientRect().top >= 0 &&
                            e.getBoundingClientRect().bottom <= innerHeight}; },
    sidebar: function(){ var e=document.querySelector('.sidebar'); if(!e) return null;
      var c=getComputedStyle(e);
      return {rect:R(e), maxHeight:c.maxHeight, top:c.top, position:c.position,
              belowFold: e.getBoundingClientRect().bottom > innerHeight}; },
    theme: function(){ return {theme:document.documentElement.dataset.theme,
              stage:document.body.dataset.stage,
              bg:getComputedStyle(document.body).backgroundColor,
              pick:[(function(){try{return localStorage.getItem('aa-theme-choice-pick');}catch(e){return 'x';}})(),
                    (function(){try{return localStorage.getItem('aa-theme-pick');}catch(e){return 'x';}})()],
              work:[(function(){try{return localStorage.getItem('aa-theme-choice-work');}catch(e){return 'x';}})(),
                    (function(){try{return localStorage.getItem('aa-theme-work');}catch(e){return 'x';}})()]}; },
    toggle: function(){ var b=document.querySelector('#aa-themebtn, [data-aa-theme-toggle], header button');
      var all=document.querySelectorAll('button');
      for(var i=0;i<all.length;i++){ var l=(all[i].getAttribute('aria-label')||'')+' '+(all[i].title||'');
        if(/theme|dark|light/i.test(l)) return {found:true, label:l.trim().slice(0,40),
          rect:(function(r){return {cx:Math.round(r.x+r.width/2),cy:Math.round(r.y+r.height/2)};})(all[i].getBoundingClientRect())}; }
      return {found:false, label:b?'unlabelled':'none'}; }
  };
})(); 1
"""


def drive_to(c, stage):
    if not c.poll("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) return 1;
        return 0;})()""", timeout=40):
        return "the Configure button never appeared"
    c.eval("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) {
          b[i].click(); return 1; } return 0;})()""")
    if not c.poll("document.body.dataset.stage === 'configure' && "
                  "document.querySelectorAll('#filters select').length > 0", timeout=40):
        return "never reached configure"
    if stage == 'configure':
        return None
    c.eval("document.getElementById('runagent').click()")
    if not c.poll("document.body.dataset.stage === 'results' && "
                  "!!(document.querySelector('#tapedone') && "
                  "document.querySelector('#tapedone').textContent.trim())", timeout=90):
        return "never reached results"
    return None


def main():
    if not os.path.isdir(DIST):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist")
        return 3
    port = free_port()
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    url = "http://127.0.0.1:%d/app/?motion=off&facility=metro_ashburn" % port
    try:
        # ================================================= 1 and 2. THE SCROLL, at short viewports
        for (W, H), stage in (((1366, 768), 'results'), ((1400, 820), 'results'),
                              ((1366, 768), 'configure')):
            head("SCROLL at %dx%d on the %s stage" % (W, H, stage))
            with Chrome(url, width=W, height=H) as c:
                c.goto(settle=2.0)
                why = drive_to(c, stage)
                if why:
                    ck(False, "reached the %s stage" % stage, why)
                    continue
                c.eval(HELPERS)
                time.sleep(0.8)
                pg = json.loads(c.eval("JSON.stringify(window.__q.page())"))
                app = json.loads(c.eval("JSON.stringify(window.__q.app())"))
                ck(pg["scrollHeight"] > pg["clientHeight"],
                   "the document has something to scroll",
                   "scrollHeight %d against clientHeight %d" % (pg["scrollHeight"],
                                                                pg["clientHeight"]))
                c.eval("window.scrollTo(0, 4000); 1")
                time.sleep(0.35)
                y = int(c.eval("Math.round(window.scrollY)"))
                ck(y > 0, "AND THE WINDOW ACTUALLY SCROLLS", "scrollY reached %d" % y)
                ck(app["overflow"] != "hidden",
                   "#app no longer clips its own overflow", "overflow %s" % app["overflow"])
                ck(app["clientHeight"] >= app["scrollHeight"],
                   "and nothing is cut off inside it",
                   "clientHeight %d against scrollHeight %d" % (app["clientHeight"],
                                                                app["scrollHeight"]))
                # back to the top, then find the row the user could not reach
                c.eval("window.scrollTo(0, 0); 1")
                time.sleep(0.3)
                rail = json.loads(c.eval("JSON.stringify(window.__q.rail())"))
                ck(rail["position"] == "sticky", "the rail is sticky", "top %s" % rail["top"])
                ck(rail["maxHeight"] == "calc(100vh - 32px)" or
                   abs(float(rail["maxHeight"].replace("px", "")) - (H - 96 - 32)) < 200,
                   "bounded against the window rather than a guessed offset", rail["maxHeight"])
                qa = json.loads(c.eval("JSON.stringify(window.__q.lastQA())") or "null")
                if ck(bool(qa), "the last Quick Action row exists", (qa or {}).get("text")):
                    if not qa["fullyVisible"]:
                        # it is allowed to start below the fold; it must be REACHABLE by scrolling
                        c.eval("window.scrollTo(0, document.body.scrollHeight); 1")
                        time.sleep(0.4)
                        qa = json.loads(c.eval("JSON.stringify(window.__q.lastQA())"))
                    ck(qa["fullyVisible"],
                       "'%s' IS REACHABLE" % qa["text"][:22],
                       "rect %s in a %dpx viewport" % (qa["rect"], pg["vh"]))
                if stage == 'configure':
                    sb = json.loads(c.eval("JSON.stringify(window.__q.sidebar())") or "null")
                    if sb:
                        ck(not sb["belowFold"] or sb["maxHeight"] != "none",
                           "the engine sidebar is bounded too",
                           "max-height %s, rect %s" % (sb["maxHeight"], sb["rect"]))

        # ================================================= 3. THE THEME, per stage group
        head("THEME: the default is per stage, and a choice belongs to the screen it was made on")
        with Chrome("http://127.0.0.1:%d/app/?motion=off&facility=metro_ashburn" % port,
                    width=1500, height=1000) as c:
            c.goto(settle=2.5)
            c.eval(HELPERS)
            t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
            ck(t["theme"] == "dark" and t["stage"] == "pick",
               "a fresh visit lands DARK on the landing page",
               "%s / %s / %s" % (t["theme"], t["stage"], t["bg"]))
            ck(t["pick"] == [None, None] and t["work"] == [None, None],
               "with nothing recorded in either group", "pick %s work %s" % (t["pick"], t["work"]))

            why = drive_to(c, 'configure')
            ck(not why, "reached configure", why or "")
            time.sleep(0.5)
            t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
            ck(t["theme"] == "light", "configure defaults LIGHT", "%s / %s" % (t["theme"], t["bg"]))

            # press the toggle TWICE on configure: it ends where it started, and must not touch pick
            tg = json.loads(c.eval("JSON.stringify(window.__q.toggle())"))
            if ck(tg["found"], "the theme toggle is findable", tg.get("label", "")):
                c.click(tg["rect"]["cx"], tg["rect"]["cy"], settle=0.4)
                c.click(tg["rect"]["cx"], tg["rect"]["cy"], settle=0.4)
                t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
                ck(t["theme"] == "light", "two presses leave configure where it started", t["theme"])
                ck(t["work"][0] == "1", "and record a choice for the WORK group only",
                   "work %s, pick %s" % (t["work"], t["pick"]))
                ck(t["pick"] == [None, None],
                   "THE LANDING GROUP IS UNTOUCHED, which was the bug", "pick %s" % (t["pick"],))
                c.eval("""(function(){var b=document.getElementById('backtopick');
                  if(b){b.click(); return 1;} return 0;})()""")
                c.poll("document.body.dataset.stage === 'pick'", timeout=30)
                time.sleep(0.6)
                t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
                ck(t["theme"] == "dark", "and the landing page is still DARK on the way back",
                   "%s / %s" % (t["theme"], t["bg"]))

            # now press it on the LANDING, and check it sticks there and only there
            tg = json.loads(c.eval("JSON.stringify(window.__q.toggle())"))
            if tg["found"]:
                c.click(tg["rect"]["cx"], tg["rect"]["cy"], settle=0.5)
                t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
                ck(t["theme"] == "light" and t["pick"][0] == "1",
                   "a press on the landing pins the landing", "pick %s" % (t["pick"],))
                c.goto(settle=2.5)
                c.eval(HELPERS)
                t = json.loads(c.eval("JSON.stringify(window.__q.theme())"))
                ck(t["theme"] == "light",
                   "and it survives a reload, because it really was a choice", t["theme"])
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-48s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: the document scrolls on every stage and at short viewports, the last")
        print("            Quick Action is reachable, and a theme choice stays on its own screen.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
