# -*- coding: utf-8 -*-
"""Does the app load at the top after a reload from a scrolled position?

FIRST LOAD:  scroll to 600, set a sessionStorage flag, reload.
SECOND LOAD: report history.scrollRestoration and scrollY at several moments, and whether any
             scroll-to-top was suppressed by the shim.

This exists because the shim in lib/noscrolljump.ts stopped a no-op setStage from scrolling to the
top, and the user then found the page loading already scrolled. The suspicion is that Chrome's own
scroll restoration was being corrected by exactly those no-op scrolls. Suspicion is not evidence.
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
  var KEY = 'aa_reload_probe';
  var phase = sessionStorage.getItem(KEY);

  if (!phase) {
    /* FIRST LOAD: get scrolled, remember, reload. */
    var t = setInterval(function(){
      if (document.documentElement.scrollHeight < 900) return;
      clearInterval(t);
      window.scrollTo(0, 600);
      setTimeout(function(){
        sessionStorage.setItem(KEY, 'scrolled:' + Math.round(window.scrollY));
        location.reload();
      }, 700);
    }, 200);
    return;
  }

  /* SECOND LOAD: watch where we end up. */
  var out = {was: phase, restoration: (history.scrollRestoration || 'unknown'), samples: [],
             suppressed: 0};
  function tr(){ try { return (new Error()).stack.split(String.fromCharCode(10)).slice(2,5).join(' | '); } catch(e){ return '?'; } }
  var _to = window.scrollTo;
  window.scrollTo = function(){
    out.samples.push({t: Math.round(performance.now()), ev: 'scrollTo(' + JSON.stringify(arguments[0]||null) + ')', y: Math.round(window.scrollY), st: tr()});
    return _to.apply(window, arguments);
  };
  var _siv = Element.prototype.scrollIntoView;
  Element.prototype.scrollIntoView = function(){
    out.samples.push({t: Math.round(performance.now()), ev: 'scrollIntoView on ' + (this.id||this.className||this.tagName), y: Math.round(window.scrollY), st: tr()});
    return _siv.apply(this, arguments);
  };
  var _fc = HTMLElement.prototype.focus;
  HTMLElement.prototype.focus = function(){
    out.samples.push({t: Math.round(performance.now()), ev: 'focus on ' + (this.id||this.className||this.tagName), y: Math.round(window.scrollY), st: tr()});
    return _fc.apply(this, arguments);
  };
  /* Fine-grained sampler: the jump happened between 187ms and 300ms last time, so watch that window
     closely and record the first sample where scrollY leaves zero. */
  var seen0 = true;
  var fine = setInterval(function(){
    var y = Math.round(window.scrollY);
    if (seen0 && y !== 0) { seen0 = false;
      out.samples.push({t: Math.round(performance.now()), ev: '*** LEFT THE TOP ***', y: y}); }
    if (performance.now() > 3000) clearInterval(fine);
  }, 20);
  function sample(label){
    out.samples.push({t: Math.round(performance.now()), ev: label, y: Math.round(window.scrollY)});
  }
  sample('script ran');
  document.addEventListener('DOMContentLoaded', function(){ sample('DOMContentLoaded'); });
  window.addEventListener('load', function(){ sample('load'); });
  [300, 900, 1800, 3000, 4500].forEach(function(ms){
    setTimeout(function(){ sample('at ' + ms + 'ms'); }, ms);
  });
  setTimeout(function(){
    out.finalY = Math.round(window.scrollY);
    out.stage = document.body.dataset.stage || null;
    sessionStorage.removeItem(KEY);
    var d = document.createElement('div');
    d.id = 'RELOADPROBE'; d.style.display = 'none';
    d.textContent = JSON.stringify(out);
    document.body.appendChild(d);
  }, 5200);
})();
</script>
"""


def main():
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    io.open(os.path.join(DIST, "_reload.html"), "w", encoding="utf-8", newline="").write(
        src.replace("</body>", PROBE + "</body>"))
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "testing", "serve_app.py"), str(port), "--hold", "2"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    prof = tempfile.mkdtemp(prefix="reload_")
    try:
        r = subprocess.run(
            [CH, "--headless=new", "--no-first-run", "--user-data-dir=" + prof,
             "--window-size=1400,900", "--enable-unsafe-swiftshader", "--use-gl=angle",
             "--virtual-time-budget=30000", "--dump-dom",
             "http://127.0.0.1:%d/app/_reload.html" % port],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    finally:
        srv.terminate()
        try:
            os.remove(os.path.join(DIST, "_reload.html"))
        except OSError:
            pass

    m = re.search(r'id="RELOADPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    if not m:
        print("   the probe never published (the reload may not have completed in budget)")
        return 1
    d = json.loads(m.group(1))
    print("   first load left:        %s" % d.get("was"))
    print("   history.scrollRestoration on the second load: %s" % d.get("restoration"))
    print("   stage on the second load: %s" % d.get("stage"))
    print()
    print("   WHEN                       scrollY")
    for s_ in d["samples"]:
        print("   %-52s %6s" % ("%s (+%dms)" % (s_["ev"][:44], s_["t"]), s_["y"]))
        if s_.get("st"): print("        %s" % str(s_["st"])[:132])
    print()
    print("   FINAL scrollY: %s   %s"
          % (d.get("finalY"),
             "AT THE TOP, correct" if d.get("finalY") == 0 else "NOT at the top, this is the bug"))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
