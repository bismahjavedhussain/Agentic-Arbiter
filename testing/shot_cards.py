"""MEASURE the headline row: the prose column, the two summary cards, and the filter panel below.

WHY THIS EXISTS SEPARATELY FROM shot_hero.py: that one measures the splash, and the splash covers the
page these cards live on. This drives the app with `?motion=off`, which flags.ts documents as leaving
a FINISHED page rather than a broken one, so what is measured is what a reader sees after the gate.

THE THREE THINGS THE BRIEF ASKED TO BE MEASURED, and they are printed with their targets:
  * the card width at a 1920 window          (expected about 540-580 px)
  * the gutter between prose and cards       (expected about 72 px)
  * card right edge == filter panel right edge, exactly, because both are now grid/flow children of
    one container rather than one of them being absolutely positioned

⚠ THE WINDOW IS NOT THE VIEWPORT. Measured in this headless build Chrome keeps 18 px of width, so a
1920 window reports 1902. Every figure below is therefore printed against the MEASURED container, and
the container is what the ratios are checked against.

Run from the repository root:  python testing/shot_cards.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "dist")
CH = None
for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
          os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")):
    if os.path.isfile(c):
        CH = c
        break

PROBE = r"""
setTimeout(function(){
  function rect(s){ var e=document.querySelector(s); if(!e) return null;
    var r=e.getBoundingClientRect();
    return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),
            right:Math.round(r.right),bottom:Math.round(r.bottom)}; }
  function all(s){ return Array.prototype.map.call(document.querySelectorAll(s), function(e){
    var r=e.getBoundingClientRect();
    return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height),
            right:Math.round(r.right),bottom:Math.round(r.bottom)}; }); }
  function css(s,p){ var e=document.querySelector(s); return e?getComputedStyle(e)[p]:null; }

  var out = {
    viewport:{w:window.innerWidth,h:window.innerHeight},
    stage: document.body.getAttribute('data-stage'),
    theme: document.documentElement.dataset.theme || null,
    app: rect('#app'),
    appPad: css('#app','paddingLeft'),
    grid: rect('.aa-mast-grid'),
    gridCols: css('.aa-mast-grid','gridTemplateColumns'),
    gridGap: css('.aa-mast-grid','columnGap'),
    col: rect('.aa-mast-col'),
    stack: rect('.aa-bubble-stack'),
    stackDir: css('.aa-bubble-stack','flexDirection'),
    stackGap: css('.aa-bubble-stack','gap'),
    cards: all('.aa-bubble'),
    cardPad: css('.aa-bubble','padding'),
    /* THE FILTER PANEL. SearchBar's outer div is a sticky spacer with negative margins; the visible
       panel is the .glass inside it, and it is the first .glass in the pick screen. */
    panel: rect('[data-show="pick"] .glass'),
    /* ONE SCALE FOR BOTH HEADLINE FIGURES: the check is that these two strings are equal. */
    numSizes: Array.prototype.map.call(document.querySelectorAll('.aa-bubble-num'), function(e){
      var c=getComputedStyle(e); return c.fontSize+'/'+c.fontWeight; }),
    numText: Array.prototype.map.call(document.querySelectorAll('.aa-bubble-num'), function(e){
      return (e.textContent||'').trim(); }),
    kpiCount: document.querySelectorAll('section[aria-label] .glass').length
  };
  var d=document.createElement('div'); d.id='CARDPROBE'; d.style.display='none';
  d.textContent=JSON.stringify(out); document.body.appendChild(d);
}, 2600);
"""


def page(drive):
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    p = src.replace("</body>", "<script>(function(){" + drive + "})();</script></body>")
    name = "_cards.html"
    io.open(os.path.join(DIST, name), "w", encoding="utf-8", newline="").write(p)
    return name


def run(port, name, w, h, shot):
    prof = tempfile.mkdtemp(prefix="cards_")
    url = "http://127.0.0.1:%d/app/%s?motion=off" % (port, name)
    args = [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
            "--user-data-dir=" + prof, "--window-size=%d,%d" % (w, h), "--hide-scrollbars",
            "--enable-unsafe-swiftshader", "--use-gl=angle",
            "--virtual-time-budget=16000"]
    png = None
    if shot:
        png = os.path.join(HERE, "shot_cards_%d.png" % w)
        args.append("--screenshot=" + png)
    else:
        args.append("--dump-dom")
    args.append(url)
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=200)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    if shot:
        ok = png and os.path.isfile(png) and os.path.getsize(png) > 4000
        print("   shot %-5d %s %s" % (w, "OK" if ok else "FAILED",
                                      ("%d B" % os.path.getsize(png)) if ok else ""))
        return png if ok else None
    m = re.search(r'id="CARDPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    if not m:
        print("   probe at %d NEVER PUBLISHED" % w)
        tail = (r.stderr or "")[-500:]
        if tail.strip():
            print("      stderr: %s" % tail.replace("\n", " ")[:500])
        return None
    return json.loads(m.group(1))


def report(d, w):
    print("\n   ================ window %d ================" % w)
    print("   viewport %sx%s   stage=%s   theme=%s"
          % (d["viewport"]["w"], d["viewport"]["h"], d["stage"], d["theme"]))
    app, grid, col, stack, panel = (d["app"], d["grid"], d["col"], d["stack"], d["panel"])
    if not grid:
        print("   NO .aa-mast-grid")
        return
    print("   #app            x=%s w=%s right=%s   padding-left %s"
          % (app["x"], app["w"], app["right"], d["appPad"]))
    print("   grid            %s   gap %s" % (d["gridCols"], d["gridGap"]))
    cards = d["cards"]
    print("   cards           %d, padding %s, stack %s gap %s"
          % (len(cards), d["cardPad"], d["stackDir"], d["stackGap"]))
    for i, c in enumerate(cards):
        print("      card %d       x=%-5s w=%-5s h=%-4s right=%s" % (i + 1, c["x"], c["w"],
                                                                     c["h"], c["right"]))
    if cards:
        widths = set(c["w"] for c in cards)
        print("   equal width     %s  %s" % ("YES" if len(widths) == 1 else "NO", sorted(widths)))
    # A gutter only exists while the grid HAS two columns. Below 1100px the cards sit under the prose
    # and `cards[0].x - col.right` is a large negative number that means nothing; printing it as a
    # gutter would be a measurement of the wrong distance, which is worse than no measurement.
    twoCol = len((d["gridCols"] or "").split()) > 1
    if col and cards and twoCol:
        gut = cards[0]["x"] - col["right"]
        print("   GUTTER          %d px   (prose column ends %d, first card starts %d)"
              % (gut, col["right"], cards[0]["x"]))
    elif col and cards:
        print("   GUTTER          n/a, single column: cards sit under the prose")
    if panel and cards:
        same = cards[0]["right"] == panel["right"]
        print("   RIGHT EDGES     cards %s | filter panel %s  ->  %s"
              % (cards[0]["right"], panel["right"], "SAME x" if same else "DIFFER"))
    else:
        print("   RIGHT EDGES     filter panel not found")
    print("   numeric scale   %s" % d["numSizes"])
    print("   one scale       %s" % ("YES" if len(set(d["numSizes"])) <= 1 else "NO"))
    print("   headline text   %s" % d["numText"])


def main():
    if not CH:
        print("no chrome found")
        return 1
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "serve_app.py"), str(port), "--hold", "30"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.2)
    try:
        name = page(PROBE)
        for w, h in ((1920, 1080), (1024, 900), (600, 900)):
            d = run(port, name, w, h, shot=False)
            if d:
                report(d, w)
            run(port, name, w, h, shot=True)
    finally:
        srv.terminate()
        try:
            os.remove(os.path.join(DIST, "_cards.html"))
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
