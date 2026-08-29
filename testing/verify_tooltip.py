"""THE (i) PANEL: opaque, alone, on top, inside the viewport, and reachable from the keyboard.

WHY IT NEEDS A REAL POINTER. The fault this file was written for could not be seen from inside the
page: the panel's own computed style was already correct (opaque background, no backdrop-filter), and
what was wrong was WHICH ELEMENT PAINTS ON TOP while the card underneath is hovered. `:hover` comes
from pointer position and nothing in the DOM sets it, so the check drives Chrome over the DevTools
Protocol and moves a real pointer. See testing/cdp.py.

WHAT WAS ACTUALLY WRONG, recorded because the obvious reading was the wrong one. The report was
"semi-transparent, with the card's numbers showing through". MEASURED before any change: the panel's
background was rgb(12,26,42) at alpha 1.0 and its backdrop-filter was `none`, so it was never
translucent. The KPI card carries `hover:-translate-y-0.5`; Tailwind v4 ships that as the `translate`
property; a non-none `translate` MAKES A STACKING CONTEXT; so while the pointer was on the card, the
panel's z-index was scoped inside it and every later sibling card painted over it. The wash was the
NEIGHBOUR's own rgba(24,24,27,0.72) glass fill on top of an opaque panel. Sampled at 80 points:
topmost at 28/80 hovered, 79/80 with the pointer away. The fix portals the panel to <body>, where it
has no card ancestor to be trapped in.

Run from the repository root:  python testing/verify_tooltip.py
Exits 0 if every check passes, 1 if any fails, 3 if the cards never appeared.
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
PASS, FAIL = [], []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-62s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


def expected_fill(png):
    """Read a clipped screenshot of the panel's interior and count pixels that belong to NEITHER the
    panel's fill NOR its text.

    🔴 THIS IS THE ASSERTION THAT WOULD HAVE CAUGHT THE ORIGINAL BUG, and the only one that looks at
    what a reader sees rather than at what the DOM says. The fault was a NEIGHBOURING card's
    rgba(24,24,27,0.72) fill composited over an opaque panel: every computed style was correct and
    the pixels were (20,24,31) where they should have been (12,26,42).
    The panel's fill is taken as the MODAL colour of the crop, which is the background by definition
    on a panel that is mostly background. Anything within a small distance of it is fill; anything on
    the line between fill and the ink colour is text or its antialiasing. What is left over is a
    foreign surface, and there must be none."""
    from PIL import Image
    import numpy as np
    a = np.asarray(Image.open(png).convert("RGB")).reshape(-1, 3).astype(np.int16)
    packed = (a[:, 0].astype(np.int32) << 16) | (a[:, 1].astype(np.int32) << 8) | a[:, 2]
    vals, counts = np.unique(packed, return_counts=True)
    top = int(vals[int(np.argmax(counts))])
    fill = np.array([(top >> 16) & 255, (top >> 8) & 255, top & 255], dtype=np.int16)
    # The ink is the darkest-or-lightest extreme away from the fill; text sits on the segment between
    # them, so a pixel is "explained" if it is close to that line.
    d = a - fill
    dist_fill = np.abs(d).max(axis=1)
    ink = a[int(np.argmax(np.abs(d).sum(axis=1)))]
    seg = (ink - fill).astype(np.float64)
    L = float(np.dot(seg, seg)) or 1.0
    t = np.clip((d.astype(np.float64) @ seg) / L, 0.0, 1.0)
    proj = fill.astype(np.float64) + t[:, None] * seg
    off_line = np.abs(a.astype(np.float64) - proj).max(axis=1)
    foreign = int(np.count_nonzero((dist_fill > 6) & (off_line > 10)))
    return "rgb(%d,%d,%d)" % tuple(int(x) for x in fill), foreign, int(a.shape[0])


HELPERS = r"""
window.__tip = (function(){
  function R(el){ if(!el) return null; var r=el.getBoundingClientRect();
    return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom,
            cx:Math.round(r.x+r.width/2), cy:Math.round(r.y+r.height/2)}; }
  return {
    infos: function(){ return Array.prototype.map.call(
      document.querySelectorAll('section[aria-label="What the agent delivers, measured"] button[aria-label]'),
      function(b){ return {label:(b.getAttribute('aria-label')||'').slice(0,44), rect:R(b)}; }); },
    notes: function(){ return document.querySelectorAll('[role="note"]').length; },
    panel: function(){
      var p=document.querySelector('.aa-tip'); if(!p) return null;
      var cs=getComputedStyle(p);
      /* THE ANCESTOR WALK IS THE DECISIVE MEASUREMENT. Anything on the way to <html> that makes a
         stacking context can trap the panel's z-index, whatever that z-index says. */
      var ctx=[], e=p.parentElement, d=0;
      while(e){ d++; var c=getComputedStyle(e), why=[];
        if(c.transform!=='none') why.push('transform');
        if(c.translate && c.translate!=='none') why.push('translate');
        if(c.scale && c.scale!=='none') why.push('scale');
        if(c.rotate && c.rotate!=='none') why.push('rotate');
        if(c.filter!=='none') why.push('filter');
        if(c.backdropFilter && c.backdropFilter!=='none') why.push('backdrop-filter');
        if(parseFloat(c.opacity)<1) why.push('opacity');
        if(c.isolation==='isolate') why.push('isolation');
        if(c.willChange && c.willChange!=='auto') why.push('will-change:'+c.willChange);
        if(c.contain && c.contain!=='none') why.push('contain');
        if(c.position!=='static' && c.zIndex!=='auto') why.push('position+z-index');
        if(why.length) ctx.push({depth:d, tag:e.tagName, cls:(e.className||'').toString().slice(0,40),
                                 why:why.join('+')});
        e=e.parentElement; }
      /* And any ancestor that could CLIP it. */
      var clip=null; e=p.parentElement;
      while(e){ var c2=getComputedStyle(e);
        if(c2.overflow!=='visible'||c2.overflowX!=='visible'||c2.overflowY!=='visible'){
          clip={tag:e.tagName, cls:(e.className||'').toString().slice(0,40), overflow:c2.overflow}; break; }
        e=e.parentElement; }
      return {rect:R(p), parentTag:(p.parentElement||{}).tagName,
              background:cs.backgroundColor, backdropFilter:cs.backdropFilter,
              opacity:cs.opacity, visibility:cs.visibility, zIndex:cs.zIndex,
              position:cs.position, pointerEvents:cs.pointerEvents,
              textTransform:cs.textTransform, letterSpacing:cs.letterSpacing,
              lineHeight:cs.lineHeight, maxWidth:cs.maxWidth, textAlign:cs.textAlign,
              padding:cs.padding, text:(p.textContent||'').trim(),
              stackingContexts:ctx, clippedBy:clip}; },
    /* WHO IS ACTUALLY PAINTED ON TOP, over a grid of points inside the panel. This is the number
       that moved from 24/80 to 80/80, and no computed style would have shown it.

       🔴 `pointer-events` IS LENT BACK FOR THE DURATION OF THE SAMPLE, and without that this
       measurement reads 0 of 80 on a perfectly healthy panel. `elementFromPoint` performs HIT
       TESTING, and hit testing skips any element with `pointer-events: none` -- which this panel
       carries deliberately, so that it cannot steal hover from its own trigger. The first run of this
       check reported "topmost at 0 of 80" against a panel that a screenshot showed painting cleanly
       on top, which is a harness measuring the wrong property.
       Restoring it is sound because PAINT ORDER AND HIT TESTING ARE DECIDED SEPARATELY:
       `pointer-events` is not one of the properties that create a stacking context and it has no
       effect on z-order. The element is put back exactly as it was in a `finally`, and the pixel
       assertion further down does not depend on this at all -- it reads the rendered PNG. */
    paint: function(){
      var p=document.querySelector('.aa-tip'); if(!p) return null;
      var pe=p.style.pointerEvents; p.style.pointerEvents='auto';
      try{
      var r=p.getBoundingClientRect(), hit=0, tot=0, others={};
      for(var i=1;i<=10;i++) for(var j=1;j<=8;j++){
        var x=r.x+r.width*i/11, y=r.y+r.height*j/9;
        if(x<0||y<0||x>innerWidth-1||y>innerHeight-1) continue;
        tot++;
        var el=document.elementFromPoint(x,y);
        if(el && (el===p || p.contains(el))) hit++;
        else { var k=el?(el.tagName+'.'+String(el.className||'').split(' ')[0]):'null';
               others[k]=(others[k]||0)+1; }
      }
      return {hit:hit, total:tot, others:others};
      } finally { p.style.pointerEvents = pe; } },
    viewport: function(){ return {w:document.documentElement.clientWidth,
                                  h:document.documentElement.clientHeight}; },
    mapRect: function(){ var m=document.querySelector('.maplibregl-map, #natmap');
      return m?R(m):null; },
    active: function(){ var a=document.activeElement;
      return a?{tag:a.tagName, label:(a.getAttribute('aria-label')||'').slice(0,44),
                expanded:a.getAttribute('aria-expanded')}:null; }
  };
})(); 1
"""


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
        with Chrome(url, width=1600, height=1000) as c:
            c.goto(settle=2.5)
            if not c.poll("document.querySelectorAll("
                          "'section[aria-label=\"What the agent delivers, measured\"] button')"
                          ".length >= 5", timeout=40):
                print("   [skip] the five KPI cards never rendered")
                return 3
            c.eval(HELPERS)
            infos = json.loads(c.eval("JSON.stringify(window.__tip.infos())"))
            vp = json.loads(c.eval("JSON.stringify(window.__tip.viewport())"))
            ck(len(infos) == 5, "five (i) triggers, one per metric card", str(len(infos)))

            # ---------------------------------------------------- 1. every card, real pointer
            head("1. HOVER EACH (i) WITH A REAL POINTER: opaque, on top, from the first frame")
            for i, b in enumerate(infos):
                c.hover(1, 1)
                time.sleep(0.2)
                c.hover(b["rect"]["cx"], b["rect"]["cy"], settle=0.45)   # > the 120ms open delay
                p = c.eval("JSON.stringify(window.__tip.panel())")
                p = json.loads(p) if p else None
                if not ck(bool(p), "card %d opens on hover alone" % (i + 1), b["label"]):
                    continue
                paint = json.loads(c.eval("JSON.stringify(window.__tip.paint())"))
                a = p["background"]
                ck(a.startswith("rgb(") and "rgba" not in a,
                   "card %d panel is fully opaque" % (i + 1), a)
                ck(p["backdropFilter"] == "none",
                   "card %d no backdrop-filter to fail to composite" % (i + 1), p["backdropFilter"])
                ck(p["opacity"] == "1" and p["visibility"] == "visible",
                   "card %d painted at opacity 1" % (i + 1),
                   "opacity %s, visibility %s" % (p["opacity"], p["visibility"]))
                ck(paint["hit"] == paint["total"],
                   "card %d nothing paints over it" % (i + 1),
                   "topmost at %d of %d sampled points%s"
                   % (paint["hit"], paint["total"],
                      "" if paint["hit"] == paint["total"] else "  intruders: %s" % paint["others"]))
                ck(not p["stackingContexts"],
                   "card %d no ancestor traps its z-index" % (i + 1),
                   "ancestors that make one: %s" % (p["stackingContexts"] or "none"))
                ck(p["clippedBy"] is None, "card %d no ancestor can clip it" % (i + 1),
                   str(p["clippedBy"]))
                ck(p["parentTag"] == "BODY", "card %d is portalled to <body>" % (i + 1),
                   p["parentTag"])
                ck(int(c.eval("window.__tip.notes()")) == 1,
                   "card %d exactly one panel in the document" % (i + 1))

            # ---------------------------------------------------- 1b. THE PIXELS THEMSELVES
            head("1b. THE RENDERED PIXELS, read back out of a screenshot")
            for i in (0, 1, 2):
                c.hover(1, 1); time.sleep(0.2)
                c.hover(infos[i]["rect"]["cx"], infos[i]["rect"]["cy"], settle=0.5)
                p = json.loads(c.eval("JSON.stringify(window.__tip.panel())"))
                r = p["rect"]
                png = os.path.join(HERE, "_tipcheck.png")
                # An inset band, so the border, the shadow and the antialiased corners are excluded
                # and only the panel's own fill is sampled.
                c.shot(png, clip={"x": r["x"] + 6, "y": r["y"] + 6,
                                  "width": max(8, r["w"] - 12), "height": max(8, r["h"] - 12)})
                want, off, n = expected_fill(png)
                ck(off == 0,
                   "card %d every sampled pixel is the panel's own fill or its ink" % (i + 1),
                   "%d of %d pixels foreign to the panel; fill %s" % (off, n, want))
            try:
                os.remove(os.path.join(HERE, "_tipcheck.png"))
            except OSError:
                pass

            # ---------------------------------------------------- 2. sliding between two
            head("2. MOVE QUICKLY BETWEEN TWO ADJACENT (i): only one is ever open")
            worst = 0
            for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 3)):
                c.hover(infos[a]["rect"]["cx"], infos[a]["rect"]["cy"], settle=0.25)
                c.hover(infos[b]["rect"]["cx"], infos[b]["rect"]["cy"], settle=0.05)
                worst = max(worst, int(c.eval("window.__tip.notes()")))
                c.hover(infos[b]["rect"]["cx"], infos[b]["rect"]["cy"], settle=0.4)
                worst = max(worst, int(c.eval("window.__tip.notes()")))
            ck(worst <= 1, "never more than one panel, mid-slide or settled",
               "worst observed: %d" % worst)

            # ---------------------------------------------------- 3. the two edge cards
            head("3. THE LEFTMOST AND RIGHTMOST CARDS: the panel stays inside the viewport")
            for i in (0, 4):
                c.hover(1, 1); time.sleep(0.2)
                c.hover(infos[i]["rect"]["cx"], infos[i]["rect"]["cy"], settle=0.45)
                p = json.loads(c.eval("JSON.stringify(window.__tip.panel())"))
                r = p["rect"]
                ck(r["x"] >= 0 and r["right"] <= vp["w"] + 0.5,
                   "card %d stays inside horizontally" % (i + 1),
                   "x %.0f to %.0f in a %d px viewport" % (r["x"], r["right"], vp["w"]))
                ck(r["y"] >= 0 and r["bottom"] <= vp["h"] + 0.5,
                   "card %d stays inside vertically" % (i + 1),
                   "y %.0f to %.0f in a %d px viewport" % (r["y"], r["bottom"], vp["h"]))

            # ---------------------------------------------------- 4. over the map
            head("4. IT PAINTS ABOVE THE MAP AND THE MAP'S OWN CONTROLS")
            m = json.loads(c.eval("JSON.stringify(window.__tip.mapRect())") or "null")
            if m:
                c.hover(1, 1); time.sleep(0.2)
                c.hover(infos[2]["rect"]["cx"], infos[2]["rect"]["cy"], settle=0.45)
                p = json.loads(c.eval("JSON.stringify(window.__tip.panel())"))
                over = p["rect"]["bottom"] > m["y"] and p["rect"]["y"] < m["bottom"]
                paint = json.loads(c.eval("JSON.stringify(window.__tip.paint())"))
                ck(over, "the panel does overlap the map, so this is a real test",
                   "panel y %.0f-%.0f, map y %.0f-%.0f"
                   % (p["rect"]["y"], p["rect"]["bottom"], m["y"], m["bottom"]))
                ck(paint["hit"] == paint["total"],
                   "and nothing from the map paints through it",
                   "topmost at %d of %d" % (paint["hit"], paint["total"]))
            else:
                ck(False, "the map is on screen to test against", "not found")

            # ---------------------------------------------------- 5. formatting
            head("5. THE COPY: sentence case, 340px, 1.5 line-height, left aligned")
            ck(p["textTransform"] == "none", "no uppercase transform", p["textTransform"])
            ck(p["letterSpacing"] in ("normal", "0px"), "no inherited eyebrow tracking",
               p["letterSpacing"])
            ck(p["maxWidth"] == "340px", "max-width 340px", p["maxWidth"])
            lh = float(p["lineHeight"].replace("px", "")) / float(
                (p.get("fontSize") or "12.5px").replace("px", "")) if p["lineHeight"].endswith(
                "px") else 0
            ck(abs(lh - 1.5) < 0.02 or p["lineHeight"] == "1.5",
               "line-height 1.5", "%s (= %.2f x font size)" % (p["lineHeight"], lh))
            ck(p["textAlign"] == "left", "left aligned", p["textAlign"])
            ck(p["pointerEvents"] == "none", "cannot steal hover from its trigger",
               p["pointerEvents"])
            ck(not p["text"].isupper(), "the body is not all capitals",
               p["text"][:70] + "...")

            # ---------------------------------------------------- 6. keyboard
            head("6. KEYBOARD: opens on focus, closes on Escape")
            c.hover(1, 1); time.sleep(0.3)
            ck(int(c.eval("window.__tip.notes()")) == 0, "nothing open to start with")
            c.eval("document.body.focus(); "
                   "document.querySelector('section[aria-label=\"What the agent delivers, measured\"]"
                   " button').focus(); 1")
            # a real Tab so Chrome grants :focus-visible, landing on the second (i)
            reached, guard = False, 0
            while guard < 12 and not reached:
                guard += 1
                c.key("Tab")
                a = json.loads(c.eval("JSON.stringify(window.__tip.active())") or "null")
                if a and a.get("expanded") is not None:
                    reached = True
            ck(reached, "tabbing lands on an (i) trigger",
               (json.loads(c.eval("JSON.stringify(window.__tip.active())")) or {}).get("label"))
            time.sleep(0.3)
            ck(int(c.eval("window.__tip.notes()")) == 1, "it opened on focus alone, with no pointer")
            c.key("Escape")
            time.sleep(0.25)
            ck(int(c.eval("window.__tip.notes()")) == 0, "and Escape closes it")

            # ---------------------------------------------------- 7. click / tap
            head("7. CLICK: opens, and clicking again closes")
            c.hover(1, 1); time.sleep(0.3)
            c.eval("document.activeElement && document.activeElement.blur(); 1")
            # ⚠ THE RECTS ARE RE-READ HERE. Section 6 calls .focus() and presses Tab, and focusing an
            # element that is off screen scrolls it into view, so coordinates captured at the top of
            # this run no longer point at the button they were measured from. The first version of
            # this section reused them and reported a working toggle as broken.
            here = json.loads(c.eval("JSON.stringify(window.__tip.infos())"))[1]["rect"]
            c.click(here["cx"], here["cy"], settle=0.4)
            n1 = int(c.eval("window.__tip.notes()"))
            ck(n1 == 1, "a click opens it", "%d panel(s) open" % n1)
            c.click(here["cx"], here["cy"], settle=0.4)
            n2 = int(c.eval("window.__tip.notes()"))
            ck(n2 == 0, "and a second click closes it", "%d panel(s) open" % n2)

            # ---------------------------------------------------- 8. the photograph
            head("8. ONE PANEL OPEN, PHOTOGRAPHED")
            c.hover(1, 1); time.sleep(0.3)
            c.eval("document.activeElement && document.activeElement.blur(); 1")
            c.hover(infos[1]["rect"]["cx"], infos[1]["rect"]["cy"], settle=0.5)
            p = json.loads(c.eval("JSON.stringify(window.__tip.panel())"))
            shot = os.path.join(HERE, "shot_tooltip.png")
            r = p["rect"]
            c.shot(shot, clip={"x": r["x"] - 40, "y": r["y"] - 90,
                               "width": r["w"] + 420, "height": r["h"] + 130})
            ck(os.path.isfile(shot) and os.path.getsize(shot) > 3000,
               "screenshot written", "%s (%d B)" % (os.path.basename(shot),
                                                    os.path.getsize(shot)))
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-54s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: one opaque panel, portalled clear of every stacking context, on top of")
        print("            the map, inside the viewport, and reachable by pointer, key and click.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
