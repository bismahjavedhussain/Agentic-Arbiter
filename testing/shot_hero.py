"""Capture and MEASURE the hero splash. Two runs of the same page: one --dump-dom for the numbers,
one --screenshot for the look.

WHY NOT testing/render_shots.py: it passes `--force-prefers-reduced-motion=reduce`, and
`flags.gateEnabled()` returns false under that query, so the splash is never rendered at all. Every
shot it takes is of the page BEHIND the splash. That flag is right for the shots it was written for
and fatal for this one.

WHY THE VIRTUAL-TIME BUDGET IS STILL HERE: --screenshot fires at the load event, serve_app.py --hold
keeps one subresource pending so the load event never arrives, and the budget's expiry is what
triggers the capture. Chrome pauses the virtual clock while a fetch is outstanding, so the four
textures still decode on the real clock. Same mechanism render_shots.py uses.
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
# Beside render_shots.py's output, same convention, so both live where the project looks.
OUT = HERE
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
  function css(s,p){ var e=document.querySelector(s); return e?getComputedStyle(e)[p]:null; }

  function rl(c){ var s=c.map(function(v){v/=255;
      return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4);});
    return 0.2126*s[0]+0.7152*s[1]+0.0722*s[2]; }
  function parse(c){ var m=/rgba?\(([^)]+)\)/.exec(c||''); if(!m) return null;
    var p=m[1].split(',').map(parseFloat);
    return {rgb:[p[0],p[1],p[2]], a:p.length>3?p[3]:1}; }
  function bgOf(el){ var e=el; while(e){ var v=parse(getComputedStyle(e).backgroundColor);
      if(v&&v.a>0.98) return v.rgb; e=e.parentElement; } return [9,9,11]; }
  function ratio(sel){ var el=document.querySelector(sel); if(!el) return null;
    var cs=getComputedStyle(el); var f=parse(cs.color); if(!f) return {sel:sel,unparsed:cs.color};
    var e=el; while(e){ var o=parseFloat(getComputedStyle(e).opacity);
      if(!isNaN(o)&&o<1) f.a*=o; e=e.parentElement; }
    var bg=bgOf(el);
    var comp=[0,1,2].map(function(i){ return f.rgb[i]*f.a+bg[i]*(1-f.a); });
    var l1=rl(comp), l2=rl(bg), hi=Math.max(l1,l2), lo=Math.min(l1,l2);
    return {sel:sel, ratio:Math.round((hi+0.05)/(lo+0.05)*100)/100,
            size:cs.fontSize, color:cs.color, bg:'rgb('+bg.join(',')+')'}; }

  var cv = document.querySelector('.aa-splash-globe-canvas');
  var gl = null;
  if (cv) { try { gl = !!(cv.getContext('webgl2')||cv.getContext('webgl')); } catch(e){ gl='ERR'; } }

  var res = [];
  try {
    performance.getEntriesByType('resource').forEach(function(r){
      if (/textures\//.test(r.name))
        res.push({name:r.name.split('/').pop(), bytes:r.encodedBodySize||r.transferSize||0,
                  ms:Math.round(r.duration)});
    });
  } catch(e){}

  var out = {
    viewport: {w: window.innerWidth, h: window.innerHeight},
    theme: document.documentElement.dataset.theme || null,
    introAttr: document.body.getAttribute('data-aa-intro'),
    splashPresent: !!document.querySelector('.aa-splash'),
    splashBg: css('.aa-splash','backgroundColor'),
    canvas: rect('.aa-splash-globe-canvas'),
    canvasSquare: (function(){ var r=rect('.aa-splash-globe-canvas');
      return r ? Math.abs(r.w-r.h) < 2 : null; })(),
    /* 🔴 THE SPHERE, AS THE COMPONENT ACTUALLY SOLVED IT. Not re-derived here: HeatGlobe.tsx
       publishes leftLimb,topLimb,diameter,vw,vh on the canvas after its layout pass. This probe
       used to report the CANVAS box as though it were the sphere, and once the canvas started
       covering the whole viewport that meant it printed "0 % cropped" for a globe that is visibly
       cropped. A measurement of the wrong box is worse than none. */
    sphere: (function(){ var c=document.querySelector('.aa-splash-globe-canvas');
      var v = c && c.dataset ? c.dataset.aaSphere : null;
      if (!v) return null;
      var p = v.split(',').map(Number);
      return {leftLimb:p[0], topLimb:p[1], diameter:p[2], vw:p[3], vh:p[4],
              cameraZ:p[5], funnelApex:p[6]}; })(),
    canvasBuffer: cv ? {w: cv.width, h: cv.height} : null,
    hasGL: gl,
    column: rect('.aa-splash-inner'),
    title: rect('.aa-gate-title'),
    cta: rect('.shiny-cta'),
    ctaLabel: (function(){ var b=document.querySelector('.shiny-cta');
      return b ? (b.textContent||'').trim() : null; })(),
    widgets: document.querySelectorAll('.aa-splash-widget').length,
    brand: rect('.aa-gate-brand'),
    textures: res,
    contrast: ['.aa-gate-eyebrow','.aa-gate-title','.aa-gate-sub','.aa-gate-by',
               '.aa-splash-widget-label','.aa-splash-widget-note','.aa-splash-widget-time']
              .map(ratio).filter(Boolean)
  };
  var d = document.createElement('div');
  d.id = 'HEROPROBE';
  d.textContent = JSON.stringify(out);
  d.style.display = 'none';
  document.body.appendChild(d);
}, 4200);
"""


def page(theme, drive):
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    boot = ("<script>try{localStorage.setItem('aa-theme',%s);"
            "document.documentElement.dataset.theme=%s;}catch(e){}</script>"
            % (json.dumps(theme), json.dumps(theme)))
    p = src.replace("<head>", "<head>" + boot, 1)
    p = p.replace("</body>", "<script>(function(){" + drive + "})();</script></body>")
    name = "_hero_%s.html" % theme
    io.open(os.path.join(DIST, name), "w", encoding="utf-8", newline="").write(p)
    return name


def run(port, name, theme, shot, size=(1920, 1020)):
    prof = tempfile.mkdtemp(prefix="hero_")
    url = "http://127.0.0.1:%d/app/%s?facility=metro_ashburn" % (port, name)
    # ⚠ THE WINDOW IS NOT THE CONTAINER, and this is now the point rather than a nuisance. Measured in
    # this headless build the browser keeps 18 px of width and 96 px of height, so a 1920x1020 window
    # gives a container of about 1902x924. The brief asks for the figures AT a 1920x1020 window and for
    # every target to be a ratio of the container's measured height, precisely because the absolute
    # pixel figure it gave last round assumed a 1080 px viewport that does not exist.
    args = [CH, "--headless=new", "--no-first-run", "--no-default-browser-check",
            "--user-data-dir=" + prof, "--window-size=%d,%d" % size, "--hide-scrollbars",
            "--enable-unsafe-swiftshader", "--use-gl=angle",
            "--autoplay-policy=no-user-gesture-required",
            "--virtual-time-budget=20000"]
    png = None
    if shot:
        png = os.path.join(OUT, "shot_hero_%s.png" % theme)
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
        print("   shot %-6s %s  %s" % (theme, "OK" if ok else "FAILED",
                                       "%d B" % os.path.getsize(png) if ok else ""))
        return png if ok else None
    m = re.search(r'id="HEROPROBE"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    if not m:
        print("   probe %-6s NEVER PUBLISHED" % theme)
        tail = (r.stderr or "")[-600:]
        if tail.strip():
            print("      stderr tail: %s" % tail.replace("\n", " ")[:600])
        return None
    return json.loads(m.group(1))


def main():
    if not CH:
        print("no chrome found")
        return 1
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "serve_app.py"), str(port), "--hold", "30"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.2)
    try:
        for theme in (sys.argv[1:] or ["dark", "light"]):
            name = page(theme, PROBE)
            d = run(port, name, theme, shot=False)
            if d:
                print("\n   ---- %s ----" % theme.upper())
                print("   viewport        %sx%s   intro=%s  splash=%s"
                      % (d["viewport"]["w"], d["viewport"]["h"], d["introAttr"],
                         d["splashPresent"]))
                print("   splash bg       %s" % d["splashBg"])
                c = d["canvas"] or {}
                v = d["viewport"]
                print("   canvas rect     x=%s y=%s %sx%s  right=%s bottom=%s  square=%s  gl=%s"
                      % (c.get("x"), c.get("y"), c.get("w"), c.get("h"), c.get("right"),
                         c.get("bottom"), d["canvasSquare"], d["hasGL"]))
                sph = d.get("sphere")
                if sph:
                    # 🔴 THE FOUR FIGURES THE BRIEF MADE MEASURABLE, each printed with its own target
                    # beside it, so a pass or a fail is readable without going back to the message.
                    D = float(sph["diameter"])
                    left, top = sph["leftLimb"], sph["topLimb"]
                    right, bottom = left + D, top + D
                    vw, vh = sph["vw"], sph["vh"]
                    cxf = (left + D / 2) / float(vw)
                    cyf = (top + D / 2) / float(vh)
                    off_r = max(0, right - vw)
                    off_b = max(0, bottom - vh)
                    def verdict(ok):
                        return "OK " if ok else "OUT"
                    print("   container H     %d px   (W %d px)   camera z %s (derived)"
                          % (vh, vw, sph.get("cameraZ")))
                    print("   %s diameter      %.0f px   = %.3f x H   (target 0.90)"
                          % (verdict(0.87 <= D / vh <= 0.93), D, D / float(vh)))
                    print("   %s centre Y      %.0f px   = %.3f x H   (target 0.66, below the midpoint)"
                          % (verdict(0.63 <= cyf <= 0.69), top + D / 2, cyf))
                    print("   %s centre X      %.0f px   = %.3f x W   (target 0.72)"
                          % (verdict(0.70 <= cxf <= 0.74), left + D / 2, cxf))
                    print("   %s top clearance %.0f px   = %.3f x H   (target about 0.20)"
                          % (verdict(0.17 <= top / float(vh) <= 0.24), top, top / float(vh)))
                    print("   %s bottom limb   %s   (cropped by %.0f px = %.2f x H)"
                          % (verdict(off_b > 0),
                             "CROPPED" if off_b > 0 else "visible inside the frame",
                             off_b, off_b / float(vh)))
                    print("   %s left limb     x=%.0f  (%.1f%% across), fully visible"
                          % (verdict(left > 0), left, 100.0 * left / vw))
                    print("   %s right edge    x=%.0f  %s"
                          % (verdict(off_r > 0), right,
                             "cropped by %.0f px" % off_r if off_r > 0
                             else "NOT cropped, stops %.0f px short of W" % (vw - right)))
                    print("      lattice apex x=%.0f, %.0f px left of the sphere's own left limb"
                          % (sph.get("funnelApex", 0), left - sph.get("funnelApex", 0)))
                print("   buffer          %s" % d["canvasBuffer"])
                col = d["column"] or {}
                print("   text column     x=%s %sx%s   title y=%s   cta y=%s  %r"
                      % (col.get("x"), col.get("w"), col.get("h"),
                         (d["title"] or {}).get("y"), (d["cta"] or {}).get("y"), d["ctaLabel"]))
                print("   widgets         %s rows" % d["widgets"])
                print("   textures        %d fetched" % len(d["textures"]))
                for t in d["textures"]:
                    print("                     %-22s %8s B  %s ms"
                          % (t["name"], t["bytes"], t["ms"]))
                worst = None
                for r in sorted(d["contrast"], key=lambda x: x.get("ratio", 0)):
                    if r.get("unparsed"):
                        print("   CONTRAST        %-28s UNPARSEABLE %s"
                              % (r["sel"], r["unparsed"]))
                        continue
                    flag = "  <-- UNDER 4.5" if r["ratio"] < 4.5 else ""
                    print("   contrast        %-28s %6.2f:1 at %-7s on %s%s"
                          % (r["sel"], r["ratio"], r["size"], r["bg"], flag))
                    if worst is None:
                        worst = r
            run(port, name, theme, shot=True)
            try:
                os.remove(os.path.join(DIST, name))
            except OSError:
                pass
            measure_guard(os.path.join(OUT, "shot_hero_%s.png" % theme))
    finally:
        srv.terminate()
    return 0


def measure_guard(png, guard=0.38):
    """🔴 THE ONE REQUIREMENT THAT CANNOT BE MEASURED FROM THE DOM: no particles in the left 38 %.

    The lattice is drawn by a shader into a canvas, so nothing in the document says where its dots
    landed. The only honest measurement is the rendered image. This counts pixels whose blue channel
    clearly exceeds their red channel, which is what a cyan dot on a near-black navy field looks like
    and what neither the type (near-white, so red is high) nor the planet (green and tan) produces in
    quantity.
    Reported as a count on each side of the boundary. A handful on the left is antialiasing on the
    wordmark; hundreds would be the mesh."""
    try:
        from PIL import Image
    except ImportError:
        print("      (guard check needs pillow)")
        return
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    cut = int(w * guard)
    left = right = typed = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
            if b < 70:
                continue
            # 🔴 THE FIRST VERSION OF THIS COUNTED THE CYAN TYPE AS PARTICLES, and reported 1,335 px
            # in a zone the lattice was nowhere near. The eyebrow and the FortyGuard mark are painted
            # --fg-bright, #14a1e0 = (20,161,224): a very BLUE cyan with almost no red.
            # A lattice dot is #8fdcff at 0.55 alpha added over the #071018 floor, which lands near
            # (86,137,164): a PALE cyan with substantial red. So the red channel separates them, and
            # the two populations are counted apart rather than one being subtracted from the other.
            if b - r > 150 and r < 45:
                typed += 1
                continue
            # AND g MUST EXCEED r, which is what makes a colour CYAN rather than merely blue-ish.
            # Without it the test also caught the antialiasing of "POWERED BY", measured at colours
            # like (130,130,159): r == g exactly, a neutral grey over a navy floor. 66 of those in a
            # zone the lattice was nowhere near is how a clean run reads as a failure.
            if 15 < b - r < 130 and r > 40 and g - r > 25:
                if x < cut:
                    left += 1
                else:
                    right += 1
    print("   %s type guard    %d lattice px left of %d%% (x<%d), %d right of it"
          % ("OK " if left < 60 else "OUT", left, int(guard * 100), cut, right))
    print("      (%d px of cyan TYPE excluded by the red-channel test)" % typed)


if __name__ == "__main__":
    sys.exit(main())
