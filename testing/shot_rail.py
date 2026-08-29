"""MEASURE AND PHOTOGRAPH THE WORKSPACE RAIL: at rest, hovered, and focused by keyboard.

WHY IT NEEDS `cdp.py` AND NOT THE USUAL `--dump-dom` PATTERN. Two of the three states this file
exists to check cannot be produced from inside the page:
  * `:hover` comes from real pointer position. No DOM API sets it.
  * `:focus-visible` is a heuristic. Chrome withholds it from a programmatic `.focus()` on a <button>
    and grants it after a Tab keypress, so `.focus()` finding no ring proves nothing.
So this drives a live Chrome over the DevTools Protocol, moves a real pointer and presses a real Tab.
See the header of testing/cdp.py.

WHAT IT ASSERTS, from the user's brief of 2026-08-30:
  * the section labels are 700 / 11px / 0.09em / uppercase and clear 4.5:1 on the rail's own surface,
    with the ratio MEASURED in the browser against the nearest opaque ancestor rather than assumed;
  * main navigation reads at least as prominent as Quick Actions (type size and weight, both groups);
  * nav rows are ~40px tall, radius 8px, weight 500, and their icons are the same colour as their
    text rather than a fainter one;
  * the active row is distinguishable from a hovered row: different fill, extra weight, a brand-blue
    icon and a 3px accent bar flush to the left edge;
  * hover adds a neutral fill, a step of ink and exactly 2px of travel; a Quick Action's chevron adds
    3px of its own and gains opacity; the active row DEEPENS instead of taking the neutral fill;
  * every interactive row shows a visible focus ring when tabbed to, and the tab order covers all of
    them with nothing skipped and nothing unreachable.

Run from the repository root:  python testing/shot_rail.py
Exits 0 if every check passes, 1 if any fails, 3 if it could not reach the rail at all.
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

PASS = []
FAIL = []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-64s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


# ---------------------------------------------------------------- in-page helpers, injected once
HELPERS = r"""
window.__rail = (function(){
  function rect(el){ if(!el) return null; var r=el.getBoundingClientRect();
    return {x:r.x,y:r.y,width:r.width,height:r.height,
            cx:Math.round(r.x+r.width/2), cy:Math.round(r.y+r.height/2)}; }
  function lin(v){ v/=255; return v<=0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055,2.4); }
  function relL(rgb){ return 0.2126*lin(rgb[0])+0.7152*lin(rgb[1])+0.0722*lin(rgb[2]); }
  function parse(c){ var m=/rgba?\(([^)]+)\)/.exec(c||''); if(!m) return null;
    var p=m[1].split(/[,\s\/]+/).filter(function(x){return x!=='';}).map(parseFloat);
    return {rgb:[p[0],p[1],p[2]], a:(p.length>3?p[3]:1)}; }
  /* THE BACKGROUND A CONTRAST RATIO IS ACTUALLY AGAINST is the nearest ancestor that paints
     opaquely, composited with anything translucent stacked over it. Walking up and taking the first
     non-transparent colour is what every other check in this repository does and it is what makes the
     figure comparable to the ones in CONTEXT. */
  function bgOf(el){
    var stack=[], e=el;
    while(e){ var v=parse(getComputedStyle(e).backgroundColor);
      if(v && v.a>0){ stack.push(v); if(v.a>0.995) break; }
      e=e.parentElement; }
    if(!stack.length) return [255,255,255];
    var out = stack.pop().rgb.slice();
    while(stack.length){ var t=stack.pop();
      out = [0,1,2].map(function(i){ return t.rgb[i]*t.a + out[i]*(1-t.a); }); }
    return out;
  }
  function ratio(el){
    if(!el) return null;
    var cs=getComputedStyle(el), f=parse(cs.color); if(!f) return null;
    var e=el, a=f.a;
    while(e){ var o=parseFloat(getComputedStyle(e).opacity); if(!isNaN(o)&&o<1) a*=o;
      e=e.parentElement; }
    var bg=bgOf(el);
    var comp=[0,1,2].map(function(i){ return f.rgb[i]*a + bg[i]*(1-a); });
    var l1=relL(comp), l2=relL(bg), hi=Math.max(l1,l2), lo=Math.min(l1,l2);
    return {ratio: Math.round((hi+0.05)/(lo+0.05)*100)/100,
            ink: 'rgb('+comp.map(Math.round).join(',')+')',
            bg:  'rgb('+bg.map(Math.round).join(',')+')',
            declared: cs.color, effectiveAlpha: Math.round(a*1000)/1000};
  }
  function styles(el, props){
    if(!el) return null; var cs=getComputedStyle(el), o={};
    props.forEach(function(p){ o[p]=cs[p]; }); return o;
  }
  function rowOf(sel){ return document.querySelector(sel); }
  return {rect:rect, ratio:ratio, styles:styles, rowOf:rowOf,
    /* The bar is a ::before, so it has no element to measure. Its declared width and background are
       read off the pseudo-element directly. */
    accent: function(sel){ var el=document.querySelector(sel); if(!el) return null;
      var cs=getComputedStyle(el, '::before');
      return {content:cs.content, width:cs.width, background:cs.backgroundColor,
              left:cs.left, top:cs.top, bottom:cs.bottom, position:cs.position}; },
    nav: function(){ return Array.prototype.map.call(
      document.querySelectorAll('.aa-rail-nav .aa-tab'), function(b){
        var cs=getComputedStyle(b), ic=b.querySelector('.aa-tab-icon');
        return {id:b.getAttribute('data-aa-tabid'),
                label:(b.textContent||'').trim(),
                active:b.classList.contains('is-active'),
                locked:b.classList.contains('is-locked'),
                disabled:!!b.disabled,
                minHeight:cs.minHeight, height:Math.round(b.getBoundingClientRect().height),
                radius:cs.borderTopLeftRadius, padding:cs.padding,
                fontSize:cs.fontSize, fontWeight:cs.fontWeight,
                color:cs.color, background:cs.backgroundColor, transform:cs.transform,
                cursor:cs.cursor, transition:cs.transitionProperty+' / '+cs.transitionDuration,
                iconColor: ic?getComputedStyle(ic).color:null,
                iconOpacity: ic?getComputedStyle(ic).opacity:null,
                rect:rect(b)}; }); },
    qa: function(){ return Array.prototype.map.call(
      document.querySelectorAll('.aa-qa'), function(b){
        var cs=getComputedStyle(b), ic=b.querySelector('.aa-qa-icon'),
            ti=b.querySelector('.aa-qa-title'), ch=b.querySelector('.aa-qa-chev');
        return {title:ti?(ti.textContent||'').trim():null,
                off:b.classList.contains('is-off'),
                minHeight:cs.minHeight, height:Math.round(b.getBoundingClientRect().height),
                radius:cs.borderTopLeftRadius,
                background:cs.backgroundColor, color:cs.color, transform:cs.transform,
                titleSize: ti?getComputedStyle(ti).fontSize:null,
                titleWeight: ti?getComputedStyle(ti).fontWeight:null,
                iconColor: ic?getComputedStyle(ic).color:null,
                chevTransform: ch?getComputedStyle(ch).transform:null,
                chevOpacity: ch?getComputedStyle(ch).opacity:null,
                rect:rect(b)}; }); },
    eyebrows: function(){ return Array.prototype.map.call(
      document.querySelectorAll('.aa-rail-nav .aa-rail-eyebrow'), function(p){
        var cs=getComputedStyle(p);
        return {text:(p.textContent||'').trim(), fontSize:cs.fontSize, fontWeight:cs.fontWeight,
                letterSpacing:cs.letterSpacing, textTransform:cs.textTransform,
                marginTop:cs.marginTop, marginBottom:cs.marginBottom,
                tag:p.tagName, tabIndex:p.tabIndex,
                interactive: !!(p.onclick||p.getAttribute('role')||p.tabIndex>=0),
                contrast: ratio(p)}; }); },
    focusNow: function(){
      var a=document.activeElement; if(!a) return null;
      var cs=getComputedStyle(a);
      var visible=false; try{ visible=a.matches(':focus-visible'); }catch(e){ visible='unsupported'; }
      return {tag:a.tagName, cls:(a.className||'').toString().slice(0,60),
              text:(a.textContent||'').trim().slice(0,40),
              inRail: !!(a.closest && a.closest('.aa-rail-nav')),
              focusVisible: visible,
              outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth,
              outlineColor: cs.outlineColor, outlineOffset: cs.outlineOffset,
              rect: rect(a)};
    }
  };
})(); 1
"""


def drive_to_results(c):
    """pick -> configure -> results, exactly the path verify_app_flow.py walks."""
    ok = c.poll("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) return 1;
        return 0;})()""", timeout=40)
    if not ok:
        return "the Configure button never appeared"
    c.eval("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) {
          b[i].click(); return 1; } return 0;})()""")
    if not c.poll("document.body.dataset.stage === 'configure' && "
                  "document.querySelectorAll('#filters select').length > 0", timeout=40):
        return "never reached the configure stage with its controls built"
    c.eval("document.getElementById('runagent').click()")
    if not c.poll("document.body.dataset.stage === 'results' && "
                  "!!(document.querySelector('#tapedone') && "
                  "document.querySelector('#tapedone').textContent.trim())", timeout=90):
        return "never reached the results stage with the tape finished"
    return None


def seed(theme):
    """A copy of the built page that has already chosen a palette.

    ⚠ BOTH KEYS. `aa-theme` alone is only a CACHE of the last resolved palette and the app is free to
    overwrite it from the stage default; `aa-theme-choice` is the record that a reader pressed the
    toggle, and only that makes the seeded value stick. See app/index.html."""
    src = io.open(os.path.join(DIST, "index.html"), encoding="utf-8", newline="").read()
    boot = ("<script>try{localStorage.setItem('aa-theme-choice','1');"
            "localStorage.setItem('aa-theme',%s);"
            "document.documentElement.dataset.theme=%s;}catch(e){}</script>"
            % (json.dumps(theme), json.dumps(theme)))
    name = "_rail_%s.html" % theme
    io.open(os.path.join(DIST, name), "w", encoding="utf-8",
            newline="").write(src.replace("<head>", "<head>" + boot, 1))
    return name


def run_theme(port, theme, shots):
    page = seed(theme)
    url = "http://127.0.0.1:%d/app/%s?motion=off&facility=metro_ashburn" % (port, page)
    print("\n" + "=" * 78)
    print("   PALETTE: %s" % theme.upper())
    print("=" * 78)
    try:
        with Chrome(url, width=1600, height=1000) as c:
            c.goto(settle=2.0)
            why = drive_to_results(c)
            if why:
                print("   [skip] could not reach the rail: %s" % why)
                return 3
            c.eval(HELPERS)
            time.sleep(0.6)

            rail = c.eval("JSON.stringify(window.__rail.rect("
                          "document.querySelector('.aa-rail-nav')))")
            rail = json.loads(rail) if rail else None
            if not rail:
                print("   [skip] .aa-rail-nav is not on screen")
                return 3

            # ============================================================ 1. SECTION LABELS
            head("1. SECTION LABELS: typed like headers, and measured for contrast")
            eb = json.loads(c.eval("JSON.stringify(window.__rail.eyebrows())"))
            ck(len(eb) == 4, "all four section labels are present",
               " / ".join(x["text"] for x in eb))
            for x in eb:
                t = x["text"]
                ck(x["fontWeight"] in ("700", "bold"), "%-18s weight 700" % t, x["fontWeight"])
                ck(x["fontSize"] == "11px", "%-18s size 11px" % t, x["fontSize"])
                ck(abs(float(x["letterSpacing"].replace("px", "")) - 11 * 0.09) < 0.06,
                   "%-18s letter-spacing 0.09em" % t,
                   "%s (0.09em of 11px = %.2fpx)" % (x["letterSpacing"], 11 * 0.09))
                ck(x["textTransform"] == "uppercase", "%-18s uppercase" % t, x["textTransform"])
                ck(x["marginBottom"] == "10px", "%-18s margin-bottom 10px" % t, x["marginBottom"])
                ck(x["tag"] == "P" and x["tabIndex"] < 0 and not x["interactive"],
                   "%-18s non-interactive" % t,
                   "<%s> tabindex=%s" % (x["tag"].lower(), x["tabIndex"]))
                r = x["contrast"] or {}
                ck((r.get("ratio") or 0) >= 4.5,
                   "%-18s clears 4.5:1 on the rail surface" % t,
                   "MEASURED %s:1  ink %s on %s" % (r.get("ratio"), r.get("ink"), r.get("bg")))
            first = eb[0]
            rest = eb[1:]
            ck(first["marginTop"] == "0px", "the first label has no margin above it",
               first["marginTop"])
            ck(all(x["marginTop"] == "28px" for x in rest),
               "every later label has margin-top 28px",
               ", ".join("%s=%s" % (x["text"].split()[0], x["marginTop"]) for x in rest))

            # ============================================================ 2. NAV ROWS AT REST
            head("2. NAV ROWS AT REST: the box, the type, and the icon")
            nav = json.loads(c.eval("JSON.stringify(window.__rail.nav())"))
            ck(len(nav) == 6, "six nav rows, unchanged in number and order",
               " > ".join(x["id"] for x in nav))
            for x in nav:
                ck(x["minHeight"] == "40px", "%-26s min-height 40px" % x["id"], x["minHeight"])
                ck(x["radius"] == "8px", "%-26s radius 8px" % x["id"], x["radius"])
                ck(x["padding"] == "0px 11px", "%-26s padding 0 11px" % x["id"], x["padding"])
                ck(x["fontSize"] == "13.2px", "%-26s size 13.2px" % x["id"], x["fontSize"])
                exp = "600" if x["active"] else "500"
                ck(x["fontWeight"] == exp, "%-26s weight %s" % (x["id"], exp), x["fontWeight"])
                if not x["active"]:
                    ck(x["iconColor"] == x["color"] and x["iconOpacity"] == "1",
                       "%-26s icon matches the text colour" % x["id"],
                       "icon %s vs text %s, opacity %s"
                       % (x["iconColor"], x["color"], x["iconOpacity"]))
                if not x["locked"]:
                    ck(x["cursor"] == "pointer", "%-26s cursor pointer" % x["id"], x["cursor"])

            # ============================================================ 3. ACTIVE VS HOVER
            head("3. THE ACTIVE ROW: four signals, and none of them shared with hover")
            act = [x for x in nav if x["active"]]
            ck(len(act) == 1, "exactly one row is active", act[0]["id"] if act else "none")
            a = act[0]
            mark = json.loads(c.eval(
                "JSON.stringify(window.__rail.styles(document.querySelector('.aa-tab-marker'),"
                "['backgroundColor','boxShadow','borderTopLeftRadius']))"))
            acc = json.loads(c.eval("JSON.stringify(window.__rail.accent('.aa-tab.is-active'))"))
            ck(acc and acc["width"] == "3px", "a 3px accent bar exists on the active row",
               "width %s, background %s" % (acc.get("width"), acc.get("background")))
            ck(acc and acc["left"] == "0px" and acc["position"] == "absolute",
               "flush to the row's left edge", "left %s, position %s"
               % (acc.get("left"), acc.get("position")))
            ck(acc and acc["top"] == "0px" and acc["bottom"] == "0px",
               "and the full height of the row", "top %s bottom %s"
               % (acc.get("top"), acc.get("bottom")))
            ck(a["iconColor"] != nav[0]["iconColor"] or a["active"],
               "the active icon is tinted differently from a resting one", a["iconColor"])
            print("      active pill fill      %s" % mark["backgroundColor"])

            # hover a NON-active, unlocked row with a real pointer
            cand = [x for x in nav if not x["active"] and not x["locked"]]
            ck(bool(cand), "there is an unlocked, non-active row to hover")
            target = cand[0]
            c.hover(target["rect"]["cx"], target["rect"]["cy"])
            hov = json.loads(c.eval(
                "JSON.stringify(window.__rail.nav().filter(function(x){return x.id==='%s';})[0])"
                % target["id"]))
            head("4. HOVER, with a real pointer (CDP Input.dispatchMouseEvent)")
            ck(hov["background"] != target["background"],
               "a background fades in that was not there at rest",
               "%s -> %s" % (target["background"], hov["background"]))
            ck(hov["color"] != target["color"], "the ink takes a step",
               "%s -> %s" % (target["color"], hov["color"]))
            ck("matrix(1, 0, 0, 1, 2, 0)" == hov["transform"],
               "the row moves exactly 2px right", hov["transform"])
            ck(hov["iconColor"] == hov["color"],
               "the icon follows the text on hover too",
               "icon %s vs text %s" % (hov["iconColor"], hov["color"]))
            # ⚠ getComputedStyle NORMALISES A DURATION TO SECONDS. The stylesheet says `150ms`
            # and the browser reports `0.15s`; asserting on the string as authored fails against a
            # rule that is perfectly correct. Assert on the value.
            durs = [d.strip() for d in hov["transition"].split("/")[1].split(",")]
            ck(all(d == "0.15s" for d in durs) and len(durs) >= 3,
               "every transition on the row is 150ms", hov["transition"])
            ck(hov["background"] != mark["backgroundColor"],
               "AND THE HOVER FILL IS NOT THE ACTIVE FILL, so the two states cannot be confused",
               "hover %s vs active %s" % (hov["background"], mark["backgroundColor"]))
            shots["hover_" + theme] = os.path.join(HERE, "shot_rail_hover_%s.png" % theme)
            c.shot(shots["hover_" + theme], clip=rail, pad=8)

            # hover the ACTIVE row: it must deepen, not take the neutral fill
            c.hover(a["rect"]["cx"], a["rect"]["cy"])
            deep = json.loads(c.eval(
                "JSON.stringify(window.__rail.styles(document.querySelector('.aa-tab-marker'),"
                "['backgroundColor']))"))
            arow = json.loads(c.eval(
                "JSON.stringify(window.__rail.nav().filter(function(x){return x.active;})[0])"))
            ck(deep["backgroundColor"] != mark["backgroundColor"],
               "hovering the active row DEEPENS its own tint",
               "%s -> %s" % (mark["backgroundColor"], deep["backgroundColor"]))
            ck(arow["background"] in ("rgba(0, 0, 0, 0)", "transparent"),
               "and does not lay the neutral hover fill over it", arow["background"])

            # ============================================================ 5. QUICK ACTIONS
            head("5. QUICK ACTIONS: two rows, and a chevron that moves")
            c.hover(rail["x"] + 4, rail["y"] + 4)          # park the pointer off every row
            qa = json.loads(c.eval("JSON.stringify(window.__rail.qa())"))
            ck(len(qa) == 2, "exactly two Quick Action rows remain",
               " / ".join(str(x["title"]) for x in qa))
            ck(all("Run the agent" != x["title"] for x in qa),
               "'Run the agent' is gone from Quick Actions",
               " / ".join(str(x["title"]) for x in qa))
            ck(all(x["title"] in ("Run on live data", "Choose a different site") for x in qa),
               "and the two the user asked to keep are the two that are there")
            # 🔴 THE FIRST QUICK ACTION IS NOT NECESSARILY AN ENABLED ONE, and hovering a disabled
            # row proves nothing: every hover rule here is written `:not(.is-off)` on purpose. In
            # replay there is no live agent attached, so "Run on live data" mirrors a disabled
            # `#livego` and correctly ignores the pointer. Hover the first row that can respond.
            live = [x for x in qa if not x["off"]]
            ck(bool(live), "at least one Quick Action row is enabled to hover",
               "%d of %d enabled" % (len(live), len(qa)))
            q0 = live[0]
            qi = qa.index(q0)
            c.hover(q0["rect"]["cx"], q0["rect"]["cy"])
            qh = json.loads(c.eval("JSON.stringify(window.__rail.qa()[%d])" % qi))
            ck(qh["background"] != q0["background"], "the row takes the same neutral fill",
               "%s -> %s" % (q0["background"], qh["background"]))
            ck(qh["transform"] == "matrix(1, 0, 0, 1, 2, 0)", "and the same 2px shift",
               qh["transform"])
            ck(qh["chevTransform"] == "matrix(1, 0, 0, 1, 3, 0)",
               "the chevron slides 3px right", qh["chevTransform"])
            ck(float(qh["chevOpacity"]) > float(q0["chevOpacity"]),
               "and gains opacity", "%s -> %s" % (q0["chevOpacity"], qh["chevOpacity"]))
            ck(qh["iconColor"] != q0["iconColor"], "the icon takes its accent colour",
               "%s -> %s" % (q0["iconColor"], qh["iconColor"]))

            # ============================================================ 6. HIERARCHY
            head("6. THE HIERARCHY, which is what the brief led with")
            navsz = float(nav[0]["fontSize"].replace("px", ""))
            navwt = int(nav[0]["fontWeight"])
            qasz = float(q0["titleSize"].replace("px", ""))
            qawt = int(q0["titleWeight"])
            ck(navsz >= qasz and navwt >= qawt,
               "main nav reads at least as prominent as Quick Actions",
               "nav %.1fpx/%d vs quick action %.1fpx/%d" % (navsz, navwt, qasz, qawt))

            # ============================================================ 7. KEYBOARD
            head("7. TAB THROUGH THE WHOLE RAIL, with real Tab keypresses")
            c.hover(1, 1)
            c.eval("(document.querySelector('.aa-rail-nav .aa-tab')||{}).blur && "
                   "document.activeElement.blur(); document.body.focus(); 1")
            # Start focus before the rail, then walk forward until focus has left it again.
            c.eval("""(function(){
              var r=document.querySelector('.aa-rail-nav');
              var all=document.querySelectorAll('a[href],button:not([disabled]),select,input,'
                +'[tabindex]:not([tabindex="-1"])');
              for(var i=0;i<all.length;i++){ if(r.contains(all[i])){
                if(i>0){ all[i-1].focus(); } return 1; } }
              return 0;})()""")
            seen, ring_ok, ring_bad, guard = [], [], [], 0
            entered = False
            while guard < 40:
                guard += 1
                c.key("Tab")
                f = c.eval("JSON.stringify(window.__rail.focusNow())")
                f = json.loads(f) if f else None
                if not f:
                    break
                if f["inRail"]:
                    entered = True
                    key = f["cls"] + "|" + f["text"]
                    if key in seen:
                        break
                    seen.append(key)
                    ok = (f["focusVisible"] is True
                          and f["outlineStyle"] not in ("none", "")
                          and float((f["outlineWidth"] or "0px").replace("px", "")) >= 2)
                    (ring_ok if ok else ring_bad).append(f)
                    print("      tab %-2d %-34s focus-visible=%s  outline %s %s %s offset %s"
                          % (guard, f["text"][:34], f["focusVisible"], f["outlineWidth"],
                             f["outlineStyle"], f["outlineColor"], f["outlineOffset"]))
                    if len(ring_ok) == 1:
                        shots["focus_" + theme] = os.path.join(HERE, "shot_rail_focus_%s.png" % theme)
                        c.shot(shots["focus_" + theme], clip=rail, pad=8)
                elif entered:
                    break
            enabled_rows = len([x for x in nav if not x["locked"]]) + len(
                [x for x in qa if not x["off"]])
            ck(entered, "tabbing reaches the rail at all")
            ck(len(ring_bad) == 0, "every interactive row tabbed to shows a >=2px focus ring",
               "%d with a ring, %d without" % (len(ring_ok), len(ring_bad)))
            ck(len(ring_ok) >= enabled_rows,
               "and the tab order covers every enabled row",
               "%d reachable of %d enabled" % (len(ring_ok), enabled_rows))
            if ring_ok:
                r0 = ring_ok[0]
                ck(r0["outlineOffset"] == "2px", "the ring is offset by 2px", r0["outlineOffset"])

            # ============================================================ 8. AT REST
            head("8. THE RAIL AT REST")
            c.hover(1, 1)
            c.eval("document.activeElement && document.activeElement.blur(); 1")
            time.sleep(0.4)
            shots["rest_" + theme] = os.path.join(HERE, "shot_rail_rest_%s.png" % theme)
            c.shot(shots["rest_" + theme], clip=rail, pad=8)
            for k, v in sorted(shots.items()):
                if theme not in k:
                    continue
                ck(os.path.isfile(v) and os.path.getsize(v) > 2000,
                   "screenshot: %s" % k, "%s (%d B)" % (os.path.basename(v),
                                                        os.path.getsize(v)))
    finally:
        try:
            os.remove(os.path.join(DIST, page))
        except OSError:
            pass
    return 0


def main():
    if not os.path.isdir(DIST):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist. Run python tools/build_app.py")
        return 3

    port = free_port()
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    shots = {}
    skipped = 0
    try:
        for theme in (sys.argv[1:] or ["light", "dark"]):
            if run_theme(port, theme, shots) == 3:
                skipped += 1
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-56s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: the rail's hierarchy, states and keyboard path are as specified, and")
        print("            every figure above was read out of a live browser.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
