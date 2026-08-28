# -*- coding: utf-8 -*-
"""Render the app in Chrome and SAVE PNGs, so a fix can be checked by looking at it.

WHY THIS EXISTS. Two rounds of "fixed" were reported after grepping the built CSS for a selector,
which proves a rule shipped and says nothing about what a reader sees. Both were wrong: one rule
targeted the engine's .info-bub while the masthead uses React's own Info component, and one set a
colour that a Tailwind utility on the inner span overrode. A screenshot would have caught either in
one look.

    python shots.py               # all shots
    python shots.py dropdown      # just one
"""
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

ROOT = r"D:\FGHackathon"
DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
OUT = os.path.dirname(os.path.abspath(__file__))
CH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Each shot: a name, the JS that drives the page into the state worth photographing, and a wait.
SHOTS = {
    # The state combobox, open, on the pick screen. Picture 1's defect.
    "dropdown": """
      var t = setInterval(function(){
        var b = document.querySelectorAll('[role="combobox"], input[placeholder*="choose"]');
        if (!b.length) return;
        clearInterval(t);
        b[0].focus(); b[0].click();
        var btn = b[0].parentElement && b[0].parentElement.querySelector('button');
        if (btn) btn.click();
      }, 150);
    """,
    # A masthead popover, open. Picture 2's defect.
    "popover": """
      var t = setInterval(function(){
        var i = document.querySelectorAll('[aria-label*="more"], [aria-expanded]');
        var cand = null, all = document.querySelectorAll('button');
        for (var k = 0; k < all.length; k++)
          if ((all[k].textContent || '').trim() === 'i' || all[k].className.indexOf('rounded-full') >= 0) { cand = all[k]; break; }
        if (!cand) return;
        clearInterval(t);
        cand.focus(); cand.click();
        cand.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
      }, 150);
    """,
    # The configure stage, top. Pictures 3, 4, 6, 7.
    "configure": """
      var t = setInterval(function(){
        var b = document.querySelectorAll('button');
        for (var i = 0; i < b.length; i++)
          if (/Configure this plant/.test(b[i].textContent || '')) { clearInterval(t); b[i].click(); }
      }, 150);
    """,
    # Results, then the Plume tab: is the NVIDIA Warp strip there and does it carry real numbers?
    "plume": """
      var st = 0;
      var t = setInterval(function(){
        var b = document.querySelectorAll('button');
        if (st === 0) {
          for (var i = 0; i < b.length; i++)
            if (/Configure this plant/.test(b[i].textContent || '')) { b[i].click(); st = 1; return; }
        } else if (st === 1) {
          var r = document.getElementById('runagent');
          if (r) { r.click(); st = 2; }
        } else if (st === 2) {
          if (document.body.dataset.stage !== 'results') return;
          /* WAIT before clicking. EngineStage moves to the 'live' tab when the stage becomes
             'results', so a click landing in the same tick is immediately overridden and the shot
             photographs the wrong tab. Learned by looking at the PNG. */
          st = 3;
          setTimeout(function(){
            var tab = document.querySelector('[data-aa-tabid="plume"]');
            if (tab && !tab.disabled) tab.click();
            clearInterval(t);
          }, 2600);
        }
      }, 200);
    """,

    # The configure stage, scrolled. Picture 5: does the tab heading survive?
    "configure_scrolled": """
      var t = setInterval(function(){
        var b = document.querySelectorAll('button');
        for (var i = 0; i < b.length; i++)
          if (/Configure this plant/.test(b[i].textContent || '')) {
            clearInterval(t); b[i].click();
            setTimeout(function(){
              var m = document.querySelector('.aa-workspace-main');
              if (m) m.scrollTop = 420;
            }, 2500);
          }
      }, 150);
    """,
}


def shot(name, drive, port, theme):
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    boot = ("<script>try{localStorage.setItem('aa-theme',%s);"
            "document.documentElement.dataset.theme=%s;}catch(e){}</script>"
            % (json.dumps(theme), json.dumps(theme)))
    page = src.replace("<head>", "<head>" + boot, 1).replace(
        "</body>", "<script>(function(){" + drive + "})();</script></body>")
    tmp = "_shot_%s.html" % name
    io.open(os.path.join(DIST, tmp), "w", encoding="utf-8", newline="").write(page)
    png = os.path.join(OUT, "shot_%s_%s.png" % (name, theme))
    prof = tempfile.mkdtemp(prefix="shot_")
    try:
        subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
             "--user-data-dir=" + prof, "--window-size=1500,1000", "--hide-scrollbars",
             "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--force-prefers-reduced-motion=reduce",
             "--virtual-time-budget=26000",
             "--screenshot=" + png,
             "http://127.0.0.1:%d/app/%s?facility=metro_ashburn" % (port, tmp)],
            capture_output=True, timeout=200)
    finally:
        try:
            os.remove(os.path.join(DIST, tmp))
        except OSError:
            pass
    ok = os.path.isfile(png) and os.path.getsize(png) > 4000
    print("   %-20s %-6s %s  %s" % (name, theme, "OK " if ok else "FAILED",
                                    "%d B" % os.path.getsize(png) if ok else ""))
    return png if ok else None


def main():
    want = sys.argv[1:] or list(SHOTS)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "testing", "serve_app.py"), str(port), "--hold", "26"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    try:
        for name in want:
            if name in SHOTS:
                for theme in ("dark", "light"):
                    shot(name, SHOTS[name], port, theme)
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
