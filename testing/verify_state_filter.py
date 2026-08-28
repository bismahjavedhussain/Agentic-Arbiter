# -*- coding: utf-8 -*-
"""Check the map's state filter IN A REAL BROWSER: full state names, the default view, individual
small circles per state, and the name box's dropdown.

WHY THIS EXISTS RATHER THAN A READ OF THE SOURCE. All four of these changes are claims about what
maplibre actually draws, and three of them were wrong the first time in ways the source could not
show. maplibre fixes clustering at source creation and offers no setter, so "the state view shows
individual circles" is only true if the flat source is the visible one at that zoom; `fitBounds`
silently no-ops on an empty bounds; and a `visibility:'none'` layer receives no events, so a handler
bound to it looks correct and does nothing. Each is read back out of the live map here.

NOTHING IN THIS FILE HARD-CODES A COUNT. The option counts, the fitted extents and the per-state
totals are all recomputed from unified_sites.json and sites.json and compared to what the page
reports, so the check cannot pass by agreeing with a number that only exists in this file.

Exit 0 pass, 1 fail, 3 could not run.
"""
import collections
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
sys.path.insert(0, HERE)
from verify_site_panels import find_browser, free_port                # noqa: E402

DRIVER_NAME = "_verify_state.html"
MARKER = "STATEPROBE"

# HOW MUCH REAL TIME ONE WARM-UP REQUEST BUYS. The probe's retry loop awaits `/__warm_N.txt`, and
# Chrome's virtual clock is PAUSED for as long as that request is outstanding -- which is the only
# lever a page under --virtual-time-budget has for giving a worker wall-clock time. 120 ms per retry,
# so the loop's thirty attempts are worth 3.6 real seconds rather than 30 virtual milliseconds.
WARM_MS = 120.0


class _Handler(SimpleHTTPRequestHandler):
    """The demo directory, plus one reserved path that deliberately takes its time."""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DEMO, **kw)

    def do_GET(self):
        if self.path.startswith("/__warm"):
            time.sleep(WARM_MS / 1000.0)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, *a):
        pass

# THE PROBE. It waits on maplibre's own `idle` event after every change rather than on a timer:
# --virtual-time-budget compresses setTimeout while leaving the network real, so a fixed sleep either
# elapses before a 620 ms camera animation starts or does not elapse at all (gotcha #112).
PROBE = r"""
<div id="%(marker)s" style="display:none"></div>
<script>
(async () => {
  const out = {ok:false, why:null};
  const $ = s => document.querySelector(s);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  try{
    // Bare identifiers, not window.*: top-level let/const in a classic script are in the global
    // lexical environment but are NOT properties of window (verify_map_hover.py records the same
    // trap, which cost a timeout against working code).
    for(let i=0; i<400 && !(typeof NATMAP !== 'undefined' && NATMAP && NATMAP.getLayer
          && NATMAP.getLayer('unisites-flat') && $('#mf_state').options.length); i++)
      await sleep(100);
    /* 🔴 DISTINGUISH "THE PAGE IS BROKEN" FROM "THE CDN DID NOT ANSWER". maplibre is fetched from
       unpkg at runtime, which is a real network request that --virtual-time-budget does not
       compress -- so on a slow or offline machine this probe can time out against a page that is
       working exactly as designed (the page degrades to a warning note, by design, because the map
       is the only panel that needs the network). Reporting WHICH of the two happened is the
       difference between a real failure and a check that cannot run. */
    out.cdn = (typeof maplibregl !== 'undefined');
    if(typeof NATMAP !== 'undefined' && NATMAP && NATMAP.on)
      NATMAP.on('error', e => { window.__MAPERR = String((e && e.error && e.error.message)
                                                          || (e && e.error) || e); });
    out.fallback = (($('#natmapnote') || {}).textContent || '').slice(0, 160);
    if(typeof NATMAP === 'undefined' || !NATMAP){
      out.why = out.cdn ? 'NATMAP never created' : 'CDNDOWN: maplibre never loaded from unpkg';
      throw 0; }
    const m = NATMAP;
    if(!m.getLayer('unisites-flat')){
      // Say WHAT is there instead of only what is missing, so the next run does not need a guess.
      out.layers = (m.getStyle() && m.getStyle().layers || []).map(l => l.id);
      out.sources = Object.keys((m.getStyle() && m.getStyle().sources) || {});
      out.styleLoaded = m.isStyleLoaded();
      out.err = window.__MAPERR || null;
      out.why = out.cdn ? 'the flat layer was never added'
                        : 'CDNDOWN: maplibre never loaded from unpkg';
      throw 0; }
    if(!$('#mf_state').options.length){ out.why='the state select was never populated'; throw 0; }

    /* SETTLE, IN TWO STAGES, BECAUSE ONE IS NOT ENOUGH UNDER VIRTUAL TIME.
       --virtual-time-budget compresses setTimeout to nothing, so a timeout fallback fires before the
       thing it was meant to wait for -- the first version of this probe read every snapshot mid-ease
       and reported that no state ever moved the camera, which was false.
         (a) the camera: maplibre fires `moveend` at the end of an ease, so wait for that whenever
             `isMoving()` says one is running.
         (b) the paint: `setLayoutProperty` is observable immediately but `queryRenderedFeatures`
             reads the LAST RENDERED FRAME, and maplibre's `idle` is exactly the event that says one
             has been drawn with nothing left pending. A generous timeout backs it up, since the page
             is required to work with a dead tile CDN and must not hang this check.
             (requestAnimationFrame does not tick in this headless mode -- an earlier version pumped
             frames here and simply never returned.) */
    const once = (ev, ms) => new Promise(res => {
      let done = false;
      const fin = () => { if(!done){ done = true; res(); } };
      m.once(ev, fin);
      setTimeout(fin, ms);
    });
    /* 🔴 THE FALLBACK TIMEOUTS ARE SPENT FROM ONE SHARED VIRTUAL-TIME BUDGET. A `once('idle')` that
       registers when the map is ALREADY idle never fires, so every settle() pays its full fallback,
       and seventeen settles at 12 s each overran the 120 s budget -- Chrome dumped the DOM mid-probe
       and the marker came back empty. Kept small and deliberately summed: 17 x (12 + 3.5) s sits
       inside the 300 s budget below with room to spare. */
    const settle = async () => {
      if(m.isMoving()) await once('moveend', 12000);
      await once('idle', 3500);
      /* 🔴 AND THEN FORCE A FRAME. `queryRenderedFeatures` reads the last PAINTED frame, and with
         reduced motion forced the camera jump is synchronous -- so `once('idle')` can register after
         the idle it was waiting for has already fired, take its timeout, and return before anything
         has been drawn at the new camera. Symptom: California reported its layer visible, its count
         correct and zero circles rendered, while Connecticut (a much larger camera change, so tiles
         really were pending) reported all four. `triggerRepaint` guarantees a frame is scheduled, so
         the `render` event that follows is a paint that actually happened. */
      m.triggerRepaint();
      await once('render', 3000);
      await sleep(60);
    };
    await settle();

    const vis = id => m.getLayer(id) ? (m.getLayoutProperty(id,'visibility') || 'visible') : 'ABSENT';
    /* 🔴 DISTINCT FACILITIES, NOT RENDERED INSTANCES. `queryRenderedFeatures` returns one entry per
       SOURCE TILE a feature appears in, and a point within a tile's buffer of a boundary appears in
       both -- so ten runnable California sites, fitted tightly enough that the tile grid cuts through
       them, came back as a stable 32. Counting `properties.key` into a Set asks the question this
       check actually means: how many facilities are on screen. */
    const distinct = (layer) => new Set(m.queryRenderedFeatures({layers:[layer]})
      .map(f => f.properties && f.properties.key).filter(Boolean)).size;
    /* 🔴 AND A SEPARATE ORACLE FOR THE EXACT COUNT, because the rendered one is not sound for it.
       `queryRenderedFeatures` reads the LAST PAINTED FRAME, and maplibre repaints the two layers of
       a source independently: narrowing California to its ten runnable sites produced a frame where
       the glow layer had the new filter (10) and the point layer still had the old one (32 in view),
       stable across successive reads, on roughly every other run. That is a real property of the
       renderer and no amount of waiting makes it a reliable oracle for "how many does this layer
       select".
       `querySourceFeatures` with the layer's OWN filter answers that question against the loaded
       source tiles instead of against a frame, so it is frame-independent. The rendered count keeps
       its own job below: proving the layer is actually painting rather than merely configured. */
    const selected = (src, layer) => { try{
      return new Set(m.querySourceFeatures(src, {filter: m.getFilter(layer)})
        .map(f => f.properties && f.properties.key).filter(Boolean)).size;
    }catch(e){ return -1; } };
    const snap = () => { const b = m.getBounds(); return {
      cl:vis('unisites-clusters'), pt:vis('unisites-circles'),
      fl:vis('unisites-flat'), fh:vis('unisites-flat-halo'),
      zoom:+m.getZoom().toFixed(2), count:($('#mf_count')||{}).textContent.trim(),
      s:+b.getSouth().toFixed(3), n:+b.getNorth().toFixed(3),
      w:+b.getWest().toFixed(3), e:+b.getEast().toFixed(3),
      drawnFlat:distinct('unisites-flat'), drawnNat:distinct('unisites-circles'),
      drawnClusters:m.queryRenderedFeatures({layers:['unisites-clusters']}).length,
      selFlat:selected('unisitesflat', 'unisites-flat'),
      selNat:selected('unisites', 'unisites-circles')}; };
    /* 🔴 THE RENDER READ HAS TO CONVERGE, NOT FIRE ONCE. A GeoJSON source builds its tiles in a
       WORKER, and worker messages are real time while --virtual-time-budget compresses the timers
       this probe waits on -- so `idle` can time out while the tiles for the new camera are still
       being built, and the snapshot then reports a correct filter, a correct count and zero circles
       drawn. That combination appeared for California, then for Texas, then for Connecticut on
       different runs: it is a race, and a longer sleep only moves it.
       So: take the snapshot, and if nothing at all was drawn, force another frame and take it again,
       up to a bounded number of tries. Every filter this check applies matches at least four
       facilities, so "nothing drawn" is never the right answer and is a safe signal to retry on. */
    const snapDrawn = async () => {
      /* WAIT FOR THE LAYER THE PAGE SAYS IT IS SHOWING, not for "anything at all". Waiting for
         anything let a STALE frame satisfy the loop: switching from the national view back to
         California exited on the previous frame's 29 cluster bubbles and reported zero circles.
         The condition is liveness only -- "the intended layer has painted something" -- so the
         assertions that follow, including the one that the OTHER layer drew nothing, are read from a
         frame that is known to be fresh rather than converged into being true. */
      /* AND THE FRAME HAS TO BE STABLE, not merely non-empty. Liveness alone still read half-updated
         frames: narrowing California from 46 facilities to its 10 runnable ones was satisfied
         instantly by the 46 that were already on screen, and the read that followed reported 32 --
         a real count of a frame caught mid-retile. So the loop needs two SUCCESSIVE reads that agree
         as well as a non-empty intended layer. Stability is not the thing being asserted, so this
         still cannot converge a false claim into a true one. */
      const live = v => (v.fl === 'visible') ? v.drawnFlat > 0 : v.drawnClusters > 0;
      const same = (a, b) => b && a.drawnFlat === b.drawnFlat
                          && a.drawnClusters === b.drawnClusters && a.drawnNat === b.drawnNat;
      let v = snap(), prev = null;
      for(let i=0; i<40 && !(live(v) && same(v, prev)); i++){
        prev = v;
        /* 🔴 A NETWORK FETCH IS HOW YOU BUY REAL TIME UNDER VIRTUAL TIME, and this loop needs real
           time specifically. A GeoJSON source builds its tiles in a WORKER, on the real clock, while
           --virtual-time-budget fast-forwards the timers this probe waits on -- so thirty retries
           spaced by setTimeout all execute before the worker has delivered a single tile, and every
           one of them reads zero circles. Chrome's virtual-time policy PAUSES the clock while a
           network fetch is outstanding, so awaiting one hands the worker actual wall-clock time.
           `/__warm_N.txt` is a path this check's own server answers with a 204 after a deliberate
           120 ms, which is what makes the pause worth having -- a plain 404 is a one millisecond
           round trip and bought so little that two consecutive runs disagreed about which snapshots
           had converged. Nothing the page reads, so it cannot perturb its state. */
        try{ await fetch('__warm_' + i + '.txt', {cache:'no-store'}); }catch(e){}
        m.triggerRepaint();
        await once('render', 400);
        v = snap();
      }
      return v;
    };
    const pick = async (v) => { const s=$('#mf_state'); s.value=v;
      s.dispatchEvent(new Event('change')); await settle(); return await snapDrawn(); };

    // ---- (2) the options, and (4) which one is selected on load ----
    out.stateOpts = [...$('#mf_state').options].map(o => [o.value, o.textContent.trim()]);
    out.selectedOnLoad = $('#mf_state').value;
    out.load = await snapDrawn();

    // ---- (3) each state moves the camera and shows individual circles ----
    out.tx = await pick('TX');
    out.ct = await pick('CT');
    out.all = await pick('');
    out.ca = await pick('CA');

    out.radiusFlat = m.getPaintProperty('unisites-flat','circle-radius');
    out.radiusNat  = m.getPaintProperty('unisites-circles','circle-radius');
    out.opFilterKeepsClusters = null;

    // ---- (1) the name box's dropdown ----
    const type = async (v) => { const i=$('#mf_q'); i.value=v;
      i.dispatchEvent(new Event('input',{bubbles:true})); await sleep(60); };
    const rows = () => [...document.querySelectorAll('#mf_drop .mfrow')].map(r => ({
      key:r.dataset.key || null, text:r.textContent.replace(/\s+/g,' ').trim(),
      w:Math.round(r.getBoundingClientRect().width),
      h:Math.round(r.getBoundingClientRect().height),
      nameW:(() => { const n = r.querySelector('.srchname');
                     return n ? Math.round(n.getBoundingClientRect().width) : 0; })(),
      nameText:(() => { const n = r.querySelector('.srchname');
                        return n ? n.textContent.trim().slice(0,60) : ''; })()}));

    await type('a');           out.q1 = rows().length;          // below the 2-character floor
    await type('equinix');     out.qEquinix = rows();
    /* MEASURED WITH HITS ON SCREEN, not on the miss box. The panel is `width:max-content`, so the
       one-line "No facility matches" state is 222 px and the eight-row state is 339 -- and it was
       the narrow one being measured, which reported the panel as too narrow for a name while the
       rows it was actually checking were fine. */
    const b1 = $('#mf_drop').getBoundingClientRect(), i1 = $('#mf_q').getBoundingClientRect();
    const cs = getComputedStyle($('#mf_drop'));
    out.dropGeom = {gap:+(b1.top - i1.bottom).toFixed(1), dl:Math.round(b1.left - i1.left),
                    dr:Math.round(b1.right - i1.right), z:+cs.zIndex,
                    bg:cs.backgroundColor, w:Math.round(b1.width)};
    await type('zzzznothing'); out.qMiss = rows();

    // choosing a row names that facility: the map goes to it and the inspector opens on it
    await type('equinix');
    const first = document.querySelector('#mf_drop .mfrow[data-key]');
    out.pickedKey = first ? first.dataset.key : null;
    if(first) first.click();
    await settle();
    // `data-open="1"` is what index.html:1322 keys the slide-over transform off, and the title is an
    // <h3> inside the generated head rather than a stable id.
    const insp = $('#inspector');
    out.pickOpenedInspector = !!(insp && insp.dataset.open === '1'
                                 && insp.getAttribute('aria-hidden') === 'false');
    out.pickDropClosed = $('#mf_drop').innerHTML === '';
    out.pickZoom = +m.getZoom().toFixed(2);
    out.pickTitle = (insp && insp.querySelector('h3') ? insp.querySelector('h3').textContent
                                                      : '').trim().slice(0,90);
    out.pickWhere = (() => { const dl = insp.querySelector('.insp-rows'); if(!dl) return '';
      const kids = [...dl.children];
      for(let i=0; i<kids.length; i++)
        if(kids[i].tagName === 'DT' && /where/i.test(kids[i].textContent) && kids[i+1])
          return kids[i+1].textContent.replace(/\s+/g,' ').trim();
      return ''; })();
    out.pickTitleFull = out.pickTitle;
    if($('#inspclose')) $('#inspclose').click();

    // A NAME SEARCH also narrows the map, and switches it to individual circles. State cleared, for
    // the same reason as the operator block above.
    await pick('');
    await type('equinix'); await settle();
    out.qFilter = await snapDrawn();
    await type(''); await settle();
    out.qCleared = await snapDrawn();

    // AN OPERATOR FILTER ALONE leaves a national spread, so it must KEEP clustering. The state has
    // to be cleared first: the filters compose, and "AWS" while California is selected is correctly
    // 2 sites, not 57.
    await pick('');
    const os_ = $('#mf_op');
    let target = null;
    for(const o of os_.options) if(o.value){ target = o.value; break; }
    out.opValue = target;
    const setOp = async (v) => { os_.value = v; os_.dispatchEvent(new Event('change'));
                                 await settle(); };
    await setOp(target);
    out.opSnap = await snapDrawn();
    // AND THE COMPOSITION ITSELF, asserted rather than tripped over: that same operator inside one
    // state must report the intersection.
    await pick('CA');
    out.opInCA = await snapDrawn();
    await setOp('');
    await pick('');

    // ---- the segmented toggle still composes with a state ----
    await pick('CA');
    $('#mf_ready').checked = true; $('#mf_ready').dispatchEvent(new Event('change'));
    await settle();
    out.caReady = await snapDrawn();
    out.caReadyDiag = {
      filter: JSON.stringify(m.getFilter('unisites-flat')),
      srcFeatures: m.querySourceFeatures('unisitesflat').length,
      srcLoaded: m.getSource('unisitesflat').loaded ? m.getSource('unisitesflat').loaded() : null,
      qAll: m.queryRenderedFeatures().length,
      qHalo: m.queryRenderedFeatures({layers:['unisites-flat-halo']}).length,
      readyChecked: $('#mf_ready').checked, allChecked: $('#mf_all').checked,
      state: $('#mf_state').value, q: $('#mf_q').value};

    out.ok = true;
  }catch(e){ if(!out.why) out.why = 'threw: ' + (e && e.message || e); }
  document.getElementById('%(marker)s').textContent = JSON.stringify(out);
})();
</script>
"""


STATE_FULL = {}


def fitted(view, ex, slack=0.9, spread=3.2):
    """Is this camera FITTED to that extent, rather than merely near it?

    Two conditions, because either alone passes for the wrong reason. CONTAINMENT: every facility in
    the set is inside the frame, or the fit dropped some of them. TIGHTNESS: the frame is not more
    than `spread` times the larger of the set's own two spans, or a continental view would "contain"
    every state and pass for all of them.

    A degree of slack rather than an exact box because fitBounds pads, and because a set whose extent
    is tall and narrow (California: 5.9 degrees of latitude, 5.3 of longitude) must be given a wider
    frame than its own width to fit its height into a landscape viewport at all."""
    lat0, lat1, lon0, lon1 = ex
    contains = (view["s"] <= lat0 + slack and view["n"] >= lat1 - slack
                and view["w"] <= lon0 + slack and view["e"] >= lon1 - slack)
    own = max(lat1 - lat0, lon1 - lon0, 0.4)
    tight = max(view["n"] - view["s"], view["e"] - view["w"]) <= own * spread + 1.2
    return contains and tight


def describe_fit(view, ex, name):
    lat0, lat1, lon0, lon1 = ex
    return ("view %.1fx%.1f deg at (%.1f, %.1f) vs %s %.1fx%.1f"
            % (view["n"] - view["s"], view["e"] - view["w"],
               (view["s"] + view["n"]) / 2, (view["w"] + view["e"]) / 2,
               name, lat1 - lat0, lon1 - lon0))


def load_state_names():
    """Read the page's OWN code->name table instead of retyping it here.

    A second copy in this file would let the check agree with itself while the page said something
    else, which is the whole failure mode these verifiers exist to catch."""
    src = io.open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    # find, NOT index: str.index RAISES, and this runs before the browser work, so a renamed table
    # produced a stack trace where the documented exit 3 ("could not run") belongs. The check has an
    # honest way to say "I could not read the page"; it should use it.
    i = src.find("const US_STATE_NAMES = {")
    if i < 0:
        return None
    body = src[src.index("{", i) + 1: src.index("};", i)]
    for m in re.finditer(r"(\w{2}):\s*'([^']+)'", body):
        STATE_FULL[m.group(1)] = m.group(2)
    return STATE_FULL


def main():
    keep = "--keep" in sys.argv
    if load_state_names() is None:
        print("   cannot run: index.html has no `const US_STATE_NAMES = {` table to read the "
              "code-to-name expansion out of. If it was renamed, update load_state_names().")
        return 3
    browser = find_browser()
    if not browser:
        print("   no Chrome/Edge found, so this check cannot run")
        return 3

    page = io.open(os.path.join(DEMO, "index.html"), encoding="utf-8", newline="").read()
    if "</body>" not in page:
        print("   index.html has no </body> to inject the probe before")
        return 3
    driver = os.path.join(DEMO, DRIVER_NAME)
    io.open(driver, "w", encoding="utf-8", newline="").write(
        page.replace("</body>", PROBE % {"marker": MARKER} + "</body>"))

    u = json.load(io.open(os.path.join(DEMO, "unified_sites.json"), encoding="utf-8"))
    sites = json.load(io.open(os.path.join(DEMO, "sites.json"), encoding="utf-8"))
    # THE SAME RULE THE PAGE USES, read from the same file: index.html:5301 defines runnable as
    # `SITES.sites.some(x => x.key === metroKey && x.offerable)`. Mirrored rather than
    # reimplemented, so this check cannot pass against a different definition of "ready".
    runnable = {x["key"] for x in sites["sites"] if x.get("offerable")}
    rows = u["sites"]
    st = collections.Counter(x.get("state") or "??" for x in rows)

    def extent(pred):
        sel = [x for x in rows if pred(x)]
        if not sel:
            return None
        return (min(x["centre"][0] for x in sel), max(x["centre"][0] for x in sel),
                min(x["centre"][1] for x in sel), max(x["centre"][1] for x in sel))

    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    prof = tempfile.mkdtemp(prefix="stateverify_")
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % port, timeout=1).read(1)
                break
            except Exception:
                time.sleep(0.1)
        else:
            print("   the local server never bound on 127.0.0.1:%d" % port)
            return 3
        print("   serving %s on 127.0.0.1:%d, %.0f ms of real time per warm-up request"
              % (os.path.basename(DEMO), port, WARM_MS))
        cmd = [browser, "--headless=new", "--no-first-run", "--no-default-browser-check",
               "--user-data-dir=" + prof, "--window-size=1440,1000",
               # WebGL must actually work: the whole point is what maplibre DRAWS. SwiftShader is the
               # software rasteriser Chrome falls back to when there is no GPU in a headless session.
               "--enable-unsafe-swiftshader", "--use-gl=angle",
               # 🔴 REDUCED MOTION IS FORCED, and it is the only way to read the camera at all:
               # requestAnimationFrame does not tick in this headless mode, so an animated ease
               # never progresses and every state reported the view it started from. The page
               # honours prefers-reduced-motion by jumping instead, which is both the correct
               # behaviour for a reader who asked for it and a state this check can measure.
               "--force-prefers-reduced-motion=reduce",
               "--virtual-time-budget=300000", "--dump-dom",
               "http://127.0.0.1:%d/%s" % (port, DRIVER_NAME)]
        dom = subprocess.run(cmd, capture_output=True, text=True, timeout=420,
                             encoding="utf-8", errors="replace").stdout or ""
    finally:
        srv.shutdown()
        srv.server_close()
        if not keep:
            try:
                os.remove(driver)
            except OSError:
                pass

    m = re.search(r'id="%s"[^>]*>(.*?)</div>' % MARKER, dom, re.S)
    if not m or not m.group(1).strip():
        print("   the probe never reported. The page did not reach a usable state.")
        if keep:
            io.open(os.path.join(DEMO, "_verify_state_dom.html"), "w",
                    encoding="utf-8").write(dom)
        return 3
    d = json.loads(m.group(1))
    if not d.get("ok"):
        why = d.get("why") or ""
        if "CDNDOWN" in why or d.get("cdn") is False:
            # NOT a failure of the page: maplibre is a runtime CDN fetch and the page degrades to a
            # warning note without it, which is its documented behaviour offline.
            print("   cannot run: maplibre did not load from unpkg, so there is no map to read.")
            print("   the page's own note said: %r" % (d.get("fallback") or "")[:120])
            return 3
        print("   probe error: %s" % why)
        for k in ("layers", "sources", "styleLoaded", "err", "cdn", "fallback"):
            if k in d:
                print("     %-12s %s" % (k, d[k]))
        return 1

    fails, passes = [], [0]

    def ck(what, cond, detail=""):
        if cond:
            passes[0] += 1
            print("   [ok]   %-62s %s" % (what, detail))
        else:
            fails.append(what)
            print("   [FAIL] %-62s %s" % (what, detail))

    print("\n-- (2) STATES ARE NAMED, NOT CODED --------------------------------------------------")
    opts = d["stateOpts"]
    coded = [t for v, t in opts if v and re.match(r"^[A-Z]{2} ", t)]
    ck("no option still leads with a two-letter code", not coded,
       "%d of %d" % (len(coded), len(opts) - 1))
    named = {v: t for v, t in opts if v}
    ck("one option per state in the registry, plus an All row",
       len(opts) == len(st) + 1 and set(named) == set(st),
       "%d options for %d states" % (len(opts), len(st)))
    # Spot-check the expansion against the codes, not against a list in this file.
    KNOWN = {"CA": "California", "TX": "Texas", "VA": "Virginia", "CT": "Connecticut",
             "IA": "Iowa", "WY": "Wyoming", "MS": "Mississippi", "NC": "North Carolina"}
    bad = ["%s->%r" % (k, named.get(k)) for k, v in KNOWN.items()
           if k in named and not named[k].startswith(v + " ")]
    ck("each name is the right expansion of its code", not bad, "; ".join(bad) or "8 spot-checked")
    wrongn = ["%s %r != %d" % (v, t, st[v]) for v, t in opts
              if v and t.split("·")[-1].strip().replace(",", "") != str(st[v])]
    ck("each option's count is the registry's own count", not wrongn,
       "; ".join(wrongn[:3]) or "%d states counted" % len(st))
    names = [t.split("·")[0].strip() for v, t in opts if v]
    ck("sorted by name, so the list reads as sorted", names == sorted(names),
       "%s ... %s" % (names[0], names[-1]))

    print("\n-- (4) THE PAGE OPENS ON CALIFORNIA -------------------------------------------------")
    ck("the state control is on California before any interaction",
       d["selectedOnLoad"] == "CA", repr(d["selectedOnLoad"]))
    ld = d["load"]
    ck("the count reads California's own total",
       re.sub(r"\s+", " ", ld["count"]) == "%d of %d shown" % (st["CA"], len(rows)),
       repr(ld["count"]))
    caex = extent(lambda x: x.get("state") == "CA")
    ck("the opening camera is over California, not the continent", fitted(ld, caex),
       describe_fit(ld, caex, "CA"))
    ck("it opens zoomed into a state rather than a nation", ld["zoom"] > 4.4,
       "zoom %.2f" % ld["zoom"])
    ck("and it opens with California's facilities selected and painted",
       ld["selFlat"] == st["CA"] and ld["drawnFlat"] > 0,
       "%d selected, %d painted, of %d" % (ld["selFlat"], ld["drawnFlat"], st["CA"]))

    print("\n-- (3) A STATE SHOWS INDIVIDUAL SMALL CIRCLES ---------------------------------------")
    for code, key in (("CA", "ca"), ("TX", "tx"), ("CT", "ct")):
        v = d[key]
        ck("%s: the flat layer is the visible one" % code,
           v["fl"] == "visible" and v["cl"] == "none" and v["pt"] == "none",
           "flat=%s clusters=%s points=%s" % (v["fl"], v["cl"], v["pt"]))
        ck("%s: no cluster bubble is drawn at that zoom" % code,
           v["drawnClusters"] == 0, "%d drawn, zoom %.2f" % (v["drawnClusters"], v["zoom"]))
        ck("%s: the layer selects exactly its facilities, no more" % code,
           v["selFlat"] == st[code], "%d selected of %d in %s" % (v["selFlat"], st[code], code))
        ck("%s: and it is really painting them, not merely configured" % code,
           v["drawnFlat"] > 0, "%d distinct facilities in the painted frame" % v["drawnFlat"])
        ex = extent(lambda x, c=code: x.get("state") == c)
        ck("%s: the camera moved to its facilities" % code, fitted(v, ex),
           describe_fit(v, ex, code))
        ck("%s: the count is its own" % code,
           re.sub(r"\s+", " ", v["count"]) == "%d of %d shown" % (st[code], len(rows)),
           repr(v["count"]))
    ck("the three state views sit at three different zooms, i.e. each is fitted to its own state",
       len({d["ca"]["zoom"], d["tx"]["zoom"], d["ct"]["zoom"]}) == 3,
       "CA %.2f  TX %.2f  CT %.2f" % (d["ca"]["zoom"], d["tx"]["zoom"], d["ct"]["zoom"]))

    print("\n-- the circles really are smaller than the national ones ----------------------------")
    def radii(expr):
        # ['match', ['get','category'], 'cluster', R, 'pair', R, R]
        return [x for x in expr if isinstance(x, (int, float))]
    rf, rn = radii(d["radiusFlat"]), radii(d["radiusNat"])
    ck("the state view's radii are strictly smaller in every category",
       len(rf) == len(rn) == 3 and all(a < b for a, b in zip(rf, rn)),
       "state %s vs national %s" % (rf, rn))

    print("\n-- 'All states' goes back to the clustered continental view -------------------------")
    a = d["all"]
    ck("clustering is back on", a["cl"] == "visible" and a["fl"] == "none",
       "clusters=%s flat=%s" % (a["cl"], a["fl"]))
    ck("bubbles are actually drawn", a["drawnClusters"] > 0, "%d bubbles" % a["drawnClusters"])
    ck("the count is the whole registry",
       re.sub(r"\s+", " ", a["count"]) == "%d of %d shown" % (len(rows), len(rows)),
       repr(a["count"]))
    allex = extent(lambda x: True)
    ck("the camera pulled back to the continent", fitted(a, allex),
       describe_fit(a, allex, "the 637"))

    print("\n-- an OPERATOR filter alone keeps the national view --------------------------------")
    o = d["opSnap"]
    ck("clusters stay, because one operator is still spread across the country",
       o["cl"] == "visible" and o["fl"] == "none",
       "%s: clusters=%s flat=%s" % (d["opValue"], o["cl"], o["fl"]))
    nop = sum(1 for x in rows if d["opValue"] in (x.get("operators") or []))
    ck("its count is the registry's count for that operator",
       re.sub(r"\s+", " ", o["count"]) == "%d of %d shown" % (nop, len(rows)),
       "%s %r" % (d["opValue"], o["count"]))

    print("\n-- (1) THE NAME BOX HAS ITS DROPDOWN BACK ------------------------------------------")
    ck("nothing opens on one character, matching the search's own two-character floor",
       d["q1"] == 0, "%d rows" % d["q1"])
    eq = d["qEquinix"]
    ck("a real operator name opens a list of facilities", len(eq) > 0, "%d rows" % len(eq))
    ck("it is capped at eight rows rather than dumping every match", len(eq) <= 8,
       "%d rows" % len(eq))
    ck("every row carries a site key the registry knows",
       all(r["key"] and r["key"] in {x["key"] for x in rows} for r in eq),
       "%d keys checked" % len(eq))
    ck("every row is a real hit for what was typed",
       all("equinix" in ((x.get("label") or "") + " " + " ".join(x.get("sample_names") or [])
                         + " " + " ".join(x.get("operators") or [])).lower()
           for r in eq for x in rows if x["key"] == r["key"]),
       "%d rows checked against the registry" % len(eq))
    ck("each row names a state in full, not as a code",
       all(not re.search(r"[A-Z]{2}\s*$", r["text"].replace("READY", "").replace(
           "CANDIDATE", "").strip()) for r in eq),
       "%r + %r" % (eq[0]["nameText"][:40], eq[0]["text"][-30:]) if eq else "")
    ck("each row says whether the agent can run there",
       all(("READY" in r["text"]) == (
               next(x for x in rows if x["key"] == r["key"])["metro_key"] in runnable)
           for r in eq),
       "%d labels checked against the manifest" % len(eq))
    ck("rows are a clickable size", all(r["h"] >= 28 and r["w"] > 120 for r in eq),
       "%dx%d" % (eq[0]["w"], eq[0]["h"]) if eq else "")
    # 🔴 THE NAME IS ACTUALLY RENDERED, not collapsed to zero width. It was: the row's name span had
    # no flex basis and no min-width, so a nowrap state and category squeezed it out entirely and
    # every row read "California · multi-building campus" with no facility in it. Measured, because
    # the text was present in the DOM the whole time -- only its box was 0 px wide.
    ck("the facility NAME is rendered, not squeezed to nothing",
       all(r.get("nameW", 0) >= 60 for r in eq),
       "narrowest name box %d px" % min([r.get("nameW", 0) for r in eq] or [0]))
    miss = d["qMiss"]
    ck("a miss says so instead of showing an empty box",
       len(miss) == 1 and "No facility matches" in miss[0]["text"] and miss[0]["key"] is None,
       miss[0]["text"][:60] if miss else "nothing rendered")

    g = d["dropGeom"]
    ck("the list sits directly under the input", 0 < g["gap"] < 14, "%.1f px below" % g["gap"])
    # The panel is intentionally WIDER than the 220 px input (see .mapbar-drop): pinned to both edges
    # the facility name had no width and every row read only its state and category. So the contract
    # is left-aligned to the input, at least as wide as it, and never narrower.
    ck("it is left-aligned to the input and at least as wide",
       abs(g["dl"]) <= 2 and g["dr"] >= -2, "left %+d, right %+d wider" % (g["dl"], g["dr"]))
    ck("and wide enough for a facility name", g["w"] >= 300, "%d px" % g["w"])
    ck("it is above the map canvas", g["z"] >= 10, "z-index %d" % g["z"])
    ck("it is opaque enough to read over the map",
       g["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), g["bg"])

    print("\n-- choosing a row names that facility ----------------------------------------------")
    ck("a row was clickable", bool(d["pickedKey"]), repr(d["pickedKey"]))
    ck("the inspector opened on it", d["pickOpenedInspector"], repr(d["pickTitle"]))
    kk = next((x for x in rows if x["key"] == d["pickedKey"]), None)
    ck("the drawer names the state in full, like the filter and the list do",
       bool(kk) and STATE_FULL.get(kk.get("state") or "", "?nostate?") in d["pickWhere"],
       "%r" % d["pickWhere"][:70])

    print("\n-- and the filters COMPOSE ---------------------------------------------------------")
    oc = d["opInCA"]
    nopca = sum(1 for x in rows
                if x.get("state") == "CA" and d["opValue"] in (x.get("operators") or []))
    ck("that operator inside California is the intersection, not either one alone",
       re.sub(r"\s+", " ", oc["count"]) == "%d of %d shown" % (nopca, len(rows)),
       "%r vs %d %s sites in CA" % (oc["count"], nopca, d["opValue"]))
    ck("and adding a state switches it to individual circles",
       oc["fl"] == "visible" and oc["cl"] == "none",
       "flat=%s clusters=%s" % (oc["fl"], oc["cl"]))

    print("\n-- a name search narrows the map too ----------------------------------------------")
    qf = d["qFilter"]
    nq = sum(1 for x in rows
             if "equinix" in ((x.get("label") or "") + " " + " ".join(x.get("sample_names") or [])
                              + " " + " ".join(x.get("operators") or [])
                              + " " + (x.get("state") or "")).lower())
    ck("it shows individual circles, because a named search wants facilities",
       qf["fl"] == "visible" and qf["cl"] == "none",
       "flat=%s clusters=%s" % (qf["fl"], qf["cl"]))
    ck("its count matches the registry",
       re.sub(r"\s+", " ", qf["count"]) == "%d of %d shown" % (nq, len(rows)),
       "%r vs %d matching rows" % (qf["count"], nq))
    qc = d["qCleared"]
    ck("clearing the box restores the clustered view",
       qc["cl"] == "visible" and qc["fl"] == "none"
       and re.sub(r"\s+", " ", qc["count"]) == "%d of %d shown" % (len(rows), len(rows)),
       "%r" % qc["count"])

    print("\n-- the segmented toggle still composes with a state --------------------------------")
    cr = d["caReady"]
    ncr = sum(1 for x in rows if x.get("state") == "CA" and x["metro_key"] in runnable)
    ck("Ready-to-run inside California is the manifest's own count",
       re.sub(r"\s+", " ", cr["count"]) == "%d of %d shown" % (ncr, len(rows)),
       "%r vs %d runnable CA sites" % (cr["count"], ncr))
    ck("and the layer selects exactly those, no more", cr["selFlat"] == ncr,
       "%d selected of %d runnable" % (cr["selFlat"], ncr))
    ck("and it is really painting them", cr["drawnFlat"] > 0,
       "%d distinct facilities in the painted frame" % cr["drawnFlat"])

    print("\n%s: %d checks passed, %d FAILED" % ("VERDICT" if not fails else "VERDICT",
                                                 passes[0], len(fails)))
    if fails:
        for f in fails:
            print("   FAILED: %s" % f)
        return 1
    print("VERDICT: PASS -- states are named, the page opens on California, each state draws its own\n"
          "         facilities as individual small circles, and the name box lists its matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
