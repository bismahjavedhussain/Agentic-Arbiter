# -*- coding: utf-8 -*-
"""WHO OWNS THE SCROLL around the plant-configuration column?

The user: "even if I scroll up all the way in the bar itself, it doesn't show till the top of the
bar unless I scroll the page itself up too."

Two plausible stories and no point choosing between them by reading CSS:
  (a) the WINDOW scrolls, so the bar's top is above the viewport and its own scrollbar cannot help;
  (b) the bar has no scroller of its own and is riding an ancestor that is clipped.

So: walk up from #filters, report every ancestor that can scroll, and then set the inner scroller
to 0 and ask whether the FIRST control is actually on screen. That last question is the user's
complaint stated as a measurement.
"""
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time

ROOT = r"D:\FGHackathon"
DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

PROBE = r"""
<script>
(function(){
  var out = {steps: [], chain: [], err: null};
  function q(s){ return document.querySelector(s); }
  function sty(el){ var c = getComputedStyle(el); return {
      position: c.position, overflowY: c.overflowY, maxHeight: c.maxHeight,
      height: c.height, flex: c.flex, minHeight: c.minHeight}; }
  function desc(el){
    if(el === document.documentElement) return 'html';
    if(el === document.body) return 'body';
    return (el.tagName||'?').toLowerCase()
      + (el.id ? '#' + el.id : '')
      + (el.className && typeof el.className === 'string'
          ? '.' + el.className.trim().split(/\s+/).slice(0,3).join('.') : '');
  }
  function snap(el){
    var r = el.getBoundingClientRect();
    return {el: desc(el), scrollTop: Math.round(el.scrollTop),
            scrollHeight: Math.round(el.scrollHeight),
            clientHeight: Math.round(el.clientHeight),
            canScroll: el.scrollHeight - el.clientHeight > 2,
            rectTop: Math.round(r.top), rectBottom: Math.round(r.bottom),
            style: sty(el)};
  }

  function step(){
    try{
      // 1. leave the pick stage
      var btns = document.querySelectorAll('button, a');
      for(var i=0;i<btns.length;i++){
        if(/Configure this plant/.test(btns[i].textContent||'')){ btns[i].click(); break; }
      }
      out.steps.push('clicked Configure');
      setTimeout(function(){
        // 2. the configuration tab
        var t = q('[data-aa-tabid="config"]');
        if(t) { t.click(); out.steps.push('clicked the config tab'); }
        else out.steps.push('NO config tab button found');
        setTimeout(measure, 900);
      }, 1400);
    }catch(e){ out.err = String(e); publish(); }
  }

  function measure(){
    try{
      out.stage = document.body.dataset.stage || null;
      out.active = (q('.aa-workspace')||{}).getAttribute
                     ? q('.aa-workspace').getAttribute('data-aa-active') : null;
      out.viewport = {w: innerWidth, h: innerHeight};

      // Does the WINDOW scroll at all?
      var de = document.documentElement;
      out.window = {scrollY: Math.round(scrollY),
                    docScrollHeight: Math.round(de.scrollHeight),
                    docClientHeight: Math.round(de.clientHeight),
                    windowCanScroll: de.scrollHeight - de.clientHeight > 2,
                    bodyOverflowY: getComputedStyle(document.body).overflowY,
                    htmlOverflowY: getComputedStyle(de).overflowY};

      var f = q('#filters');
      out.filtersFound = !!f;
      if(!f){ publish(); return; }
      out.filters = snap(f);
      out.filtersChildren = f.children.length;

      // 3. the whole chain up to html, flagging every real scroller
      var el = f, guard = 0;
      while(el && guard++ < 30){
        out.chain.push(snap(el));
        el = el.parentElement;
      }

      // 4. THE USER'S COMPLAINT, AS A MEASUREMENT. Find the nearest scrollable ancestor, put it at
      //    the top, and ask whether the first control is visible in the viewport.
      var sc = null, e2 = f.parentElement, g2 = 0;
      while(e2 && g2++ < 30){
        if(e2.scrollHeight - e2.clientHeight > 2 &&
           /auto|scroll/.test(getComputedStyle(e2).overflowY)){ sc = e2; break; }
        e2 = e2.parentElement;
      }
      out.scroller = sc ? desc(sc) : null;
      var first = f.querySelector('.f, label, select');
      out.firstControlText = first ? (first.textContent||'').trim().slice(0,40) : null;

      if(sc && first){
        sc.scrollTop = 999999;                       // bottom first, like a reader who scrolled down
        out.atBottom = {scrollerTop: Math.round(sc.scrollTop),
                        firstRectTop: Math.round(first.getBoundingClientRect().top)};
        sc.scrollTop = 0;                            // now all the way up with its OWN scrollbar
        var r = first.getBoundingClientRect();
        out.atTop = {scrollerTop: Math.round(sc.scrollTop),
                     firstRectTop: Math.round(r.top),
                     firstRectBottom: Math.round(r.bottom),
                     visible: r.top >= 0 && r.bottom <= innerHeight,
                     aboveViewport: r.top < 0};
        // and does the FILTERS element itself start on screen?
        var fr = f.getBoundingClientRect();
        out.filtersRectAtTop = {top: Math.round(fr.top), bottom: Math.round(fr.bottom),
                                startsOnScreen: fr.top >= 0};
      }
      publish();
    }catch(e){ out.err = String(e) + ' | ' + (e.stack||'').slice(0,200); publish(); }
  }

  function publish(){
    var d = document.createElement('div');
    d.id = 'RAILPROBE'; d.style.display = 'none';
    d.textContent = JSON.stringify(out);
    document.body.appendChild(d);
  }

  var t = setInterval(function(){
    if(!document.querySelector('button, a')) return;
    clearInterval(t); setTimeout(step, 2200);
  }, 200);
})();
</script>
"""


def main():
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    io.open(os.path.join(DIST, "_rail.html"), "w", encoding="utf-8", newline="").write(
        src.replace("</body>", PROBE + "</body>"))
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "testing", "serve_app.py"), str(port), "--hold", "2"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    prof = tempfile.mkdtemp(prefix="rail_")
    try:
        r = subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--user-data-dir=" + prof,
             "--window-size=1520,1000", "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--virtual-time-budget=40000", "--dump-dom",
             "http://127.0.0.1:%d/app/_rail.html" % port],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    finally:
        srv.terminate()
        try:
            os.remove(os.path.join(DIST, "_rail.html"))
        except OSError:
            pass

    m = re.search(r'id="RAILPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    if not m:
        print("   the probe never published")
        print((r.stdout or "")[:600])
        return 1
    d = json.loads(m.group(1))
    print("   steps: %s" % " -> ".join(d.get("steps") or []))
    print("   stage=%s  active tab=%s  viewport=%s" % (d.get("stage"), d.get("active"),
                                                       d.get("viewport")))
    if d.get("err"):
        print("   ERROR: %s" % d["err"])
    print()
    print("   DOES THE WINDOW SCROLL?")
    for k, v in (d.get("window") or {}).items():
        print("      %-20s %s" % (k, v))
    print()
    print("   #filters found: %s   children=%s" % (d.get("filtersFound"), d.get("filtersChildren")))
    print("   nearest scrollable ancestor: %s" % d.get("scroller"))
    print("   first control: %r" % d.get("firstControlText"))
    print()
    print("   THE CHAIN (scrollers marked ***)")
    for c in d.get("chain") or []:
        print("      %s %-42s scrollTop=%-6s %s/%s  rect %s..%s"
              % ("***" if c["canScroll"] else "   ", c["el"][:42], c["scrollTop"],
                 c["scrollHeight"], c["clientHeight"], c["rectTop"], c["rectBottom"]))
        print("            position=%-8s overflowY=%-7s maxHeight=%-16s height=%s"
              % (c["style"]["position"], c["style"]["overflowY"], c["style"]["maxHeight"],
                 c["style"]["height"]))
    print()
    print("   THE COMPLAINT, MEASURED")
    print("      after scrolling its own scroller to the BOTTOM: %s" % d.get("atBottom"))
    print("      after scrolling its own scroller to the TOP:    %s" % d.get("atTop"))
    print("      #filters rect at top: %s" % d.get("filtersRectAtTop"))
    at = d.get("atTop") or {}
    if at:
        print()
        if at.get("visible"):
            print("      VERDICT: the bar's own scrollbar DOES reach its top. Not reproduced here.")
        else:
            print("      VERDICT: the bar's own scrollbar does NOT reach its top -- first control "
                  "at y=%s, aboveViewport=%s. This is the bug." % (at.get("firstRectTop"),
                                                                   at.get("aboveViewport")))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
