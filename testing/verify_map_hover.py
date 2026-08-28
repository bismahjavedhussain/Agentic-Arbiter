# -*- coding: utf-8 -*-
"""DRIVE THE NATIONAL MAP'S HOVER READOUT IN A REAL BROWSER, WITHOUT NEEDING WebGL.

WHY THIS EXISTS, AND WHY IT DOES NOT SCREENSHOT THE MAP
    Gotcha #155: headless Chrome in this environment cannot reach a loaded MapLibre state at all.
    It was proved with a MINIMAL, code-independent MapLibre page that also failed -- so a blank map
    in a headless shot is evidence about the shell, not about this project's code. Any check that
    depended on the map RENDERING would therefore be permanently red for a reason unrelated to what
    it is testing, and a check that is always red gets ignored, which is worse than no check.

    So this drives the part that can actually be verified. The hover readout's CONTENT -- which
    facility the cursor is over, its operators, its buildings, its coordinates, its real status --
    is plain DOM built by `natReadout()` from `NATBYKEY`, and `NATBYKEY` is populated from
    `unified_sites.json` BEFORE the map library is even fetched. That whole path is testable
    headlessly and is where a defect would actually live. What is left unverified is the wiring of
    `map.on('mousemove')` to `natReadout()`, which is three lines and must be confirmed by a human
    in a real browser. Said plainly rather than implied.

WHAT IT ASSERTS
    1. `US` and `NATBYKEY` load, and hold the same site count the file claims.
    2. The resting message shows when nothing is hovered -- never a blank panel, because a blank
       panel reads as a broken one (the `#fieldhover` lesson).
    3. A RUNNABLE site's readout names that site and offers to run the agent.
    4. A NON-runnable site's readout names it, states its real status, and says no agent run is
       published -- the honest half, and the one a reader is most likely to be misled by.
    5. Two different facilities produce DIFFERENT readouts. This is the national-scale form of
       `check_sites_actually_differ`: a hover menu that says the same thing everywhere is the same
       defect family as a panel that renders the same numbers everywhere (#98, #132, #133, #142).
    6. `siteIsRunnable()` is driven by the MANIFEST, not by the map's status string, so building
       more facilities routes their clicks without this code being edited again.

USAGE
    python verify_map_hover.py                 # non-zero on any finding
    python verify_map_hover.py --keep          # leave the driver page and DOM dump for reading
    python verify_map_hover.py --browser PATH  # use a specific Chrome/Edge binary
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")

sys.path.insert(0, HERE)
# REUSED, not reimplemented: browser discovery and free-port selection are already solved in
# verify_site_panels.py, and a second copy of either would drift from it (gotcha #12). The server
# and the DOM dump are inlined below because that file's versions are shaped around its own
# per-site driver and its `?site=` URL, which this check does not use.
from verify_site_panels import find_browser, free_port                # noqa: E402

DRIVER_NAME = "_verify_hover.html"
MARKER = "HOVERPROBE"

# The probe runs INSIDE the page, after boot, and writes one JSON blob into a marker element that
# `--dump-dom` will hand back. Nothing here fabricates a site key: the two probed sites are chosen
# from the loaded registry at runtime -- the first runnable one and the first non-runnable one --
# so this cannot pass by naming a site that happens to be hard-coded here and nowhere else.
PROBE = """
<div id="%(marker)s" style="display:none"></div>
<script>
(async () => {
  const out = {ok:false, why:null};
  try{
    // BARE, not `window.NATBYKEY`. Top-level `let`/`const` in a classic script live in the global
    // LEXICAL environment, which separate <script> blocks share, but they are NOT properties of
    // `window` -- only top-level `function` declarations are. verify_site_panels.py:91-93 records
    // the same trap. The first version of this probe polled `window.NATBYKEY` and timed out
    // against perfectly working code.
    for(let i=0; i<300 && !NATBYKEY; i++){ await new Promise(r=>setTimeout(r,100)); }
    if(!NATBYKEY){ out.why='NATBYKEY never populated'; throw 0; }
    const rows = Object.values(NATBYKEY);
    out.n_sites_file = US.n_sites;
    out.n_sites_index = rows.length;

    const runnable = rows.find(s => siteIsRunnable(s.metro_key));
    const other    = rows.find(s => !siteIsRunnable(s.metro_key));
    out.runnable_key = runnable ? runnable.key : null;
    out.other_key    = other ? other.key : null;

    const read = (k) => { natReadout(k); return $('#natsidebody').innerText.replace(/\\s+/g,' ').trim(); };
    out.rest = read(null);
    out.run_text = runnable ? read(runnable.key) : null;
    out.other_text = other ? read(other.key) : null;
    // A THIRD site, to prove the readout varies rather than merely differing from the resting text.
    const other2 = rows.find(s => other && s.key !== other.key && !siteIsRunnable(s.metro_key)
                                  && (s.state || '') !== (other.state || ''));
    out.other2_key = other2 ? other2.key : null;
    out.other2_text = other2 ? read(other2.key) : null;

    out.runnable_flag_manifest = siteIsRunnable('ashburn');
    out.runnable_flag_bogus    = siteIsRunnable('not_a_site_key');

    // ---- THE SEARCH BOX. Same probe, because it needs no WebGL either: it reads the registry
    // the map fetched and writes plain DOM. What is NOT covered here is typing with a real
    // keyboard, which is what oninput fires on -- so the input's value is set and searchRender()
    // called directly, and the gap is stated in the verdict rather than implied away.
    const inp = document.getElementById('sitesearch');
    out.search_input_exists = !!inp;
    out.search_index_ready  = searchIndexReady();
    const runQuery = (q) => {
      inp.value = q; searchRender();
      const box = document.getElementById('searchresults');
      const rows = [...box.querySelectorAll('.srchrow')];
      /* 🔴 FIND THE ROW, DO NOT ASSUME IT IS FIRST. This used to read row 0 and call it the
         no-run case, and the first hit for "equinix" is Digital Realty Silicon Valley SJC37, whose
         metro IS offerable -- searchMatch() floats runnable sites to the top of a score band on
         purpose, so row 0 is the LEAST likely row to be a no-run one. The check was asserting
         something the page had never promised.
         `data-ready="0"` rather than `aria-disabled`: such a row opens the facility's specs now, so
         it is not disabled and no longer says it is. */
      const nr = rows.find(r => r.dataset.ready === '0') || null;
      return {n: rows.length,
              first: rows.length ? rows[0].innerText.replace(/\\s+/g,' ').trim() : null,
              first_disabled: rows.length ? rows[0].getAttribute('aria-disabled')==='true' : null,
              n_norun: rows.filter(r => r.dataset.ready === '0').length,
              norun: nr ? nr.innerText.replace(/\\s+/g,' ').trim() : null,
              norun_aria: nr ? nr.getAttribute('aria-disabled') : null,
              norun_marked: nr ? nr.dataset.ready === '0' : null,
              note: (document.getElementById('searchnote')||{}).innerText || ''};
    };
    // A runnable facility by name. 'apple' must surface the Apple facility that HAS a run.
    out.q_apple   = runQuery('apple');
    // A name that exists in the registry but has no run behind it.
    out.q_equinix = runQuery('equinix');
    // Guards: too short, and no match at all.
    out.q_short   = runQuery('a');
    out.q_none    = runQuery('zzzznotathing');
    // A state code.
    out.q_state   = runQuery('IA');
    inp.value = '';
    out.ok = true;
  }catch(e){ if(!out.why) out.why = String(e && (e.stack||e.message) || e); }
  document.getElementById('%(marker)s').textContent = JSON.stringify(out);
})();
</script>
""" % {"marker": MARKER}


def build_driver():
    """Regenerate the driver from index.html EVERY run. Gotcha #102: a snapshot copy goes stale the
    moment index.html is edited, and twice a verification run reported a freshly-added element as
    missing because the driver predated the edit."""
    src = open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    if "</body>" not in src:
        raise SystemExit("index.html has no </body> to inject before")
    out = src.replace("</body>", PROBE + "</body>")
    p = os.path.join(DEMO, DRIVER_NAME)
    open(p, "w", encoding="utf-8").write(out)
    return p


def main(argv):
    keep = "--keep" in argv
    bexp = argv[argv.index("--browser") + 1] if "--browser" in argv else None
    print("=" * 78)
    print("MAP HOVER READOUT -- real browser, no WebGL required")
    print("=" * 78)

    browser = find_browser(bexp)
    if not browser:
        # NON-ZERO, not a skip. A check that skips reports PASS for a path it never ran (the
        # run_all step-20 lesson).
        print("   no Chrome/Edge found. This check FAILS rather than skipping.")
        return 4
    print("   browser: %s" % browser)

    driver = build_driver()
    fails = []

    def ck(name, ok, detail=""):
        if not ok:
            fails.append(name)
        print("   [%s] %-52s %s" % ("PASS" if ok else "FAIL", name, detail))

    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                           cwd=DEMO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    prof = tempfile.mkdtemp(prefix="hoververify_")
    try:
        bound = False
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/sites.json" % port, timeout=1).read(1)
                bound = True
                break
            except Exception:
                time.sleep(0.1)
        if not bound:
            print("   the local server never bound on 127.0.0.1:%d" % port)
            return 3
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run",
               "--no-default-browser-check", "--user-data-dir=" + prof,
               # Gotcha #112: --virtual-time-budget compresses setTimeout while the network stays
               # real, so the probe's own 30 s poll for NATBYKEY can elapse before the fetch lands.
               # 90 s is the same budget verify_site_panels.py settled on.
               "--virtual-time-budget=90000", "--dump-dom",
               "http://127.0.0.1:%d/%s" % (port, DRIVER_NAME)]
        dom = subprocess.run(cmd, capture_output=True, text=True, timeout=240,
                             encoding="utf-8", errors="replace").stdout or ""
    finally:
        srv.terminate()
        if not keep:
            try:
                os.remove(driver)
            except OSError:
                pass

    m = re.search(r'id="%s"[^>]*>(.*?)</div>' % MARKER, dom, re.S)
    if not m or not m.group(1).strip():
        print("   the probe never reported. The page did not reach a usable state.")
        if keep:
            open(os.path.join(DEMO, "_verify_hover_dom.html"), "w", encoding="utf-8").write(dom)
        return 3
    d = json.loads(m.group(1))
    if not d.get("ok"):
        print("   probe error: %s" % d.get("why"))
        return 3

    ck("the registry loads and the index covers every site",
       d["n_sites_index"] == d["n_sites_file"],
       "%s indexed of %s in the file" % (d["n_sites_index"], d["n_sites_file"]))
    ck("nothing hovered shows a resting message, not a blank panel",
       bool(d["rest"]) and "Hover" in d["rest"], repr(d["rest"])[:60])

    ck("a runnable site names itself and offers the agent",
       bool(d["run_text"]) and "Click to run the agent" in d["run_text"],
       "%s -> %s" % (d["runnable_key"], repr(d["run_text"])[:52]))
    ck("a non-runnable site says NO agent run is published",
       bool(d["other_text"]) and "No agent run is published" in d["other_text"],
       "%s -> %s" % (d["other_key"], repr(d["other_text"])[:44]))
    ck("a non-runnable site still states its own real status",
       bool(d["other_text"]) and len(d["other_text"]) > 80,
       "%d chars" % len(d["other_text"] or ""))

    ck("two different facilities read differently",
       d["other2_text"] and d["other2_text"] != d["other_text"],
       "%s vs %s" % (d["other_key"], d["other2_key"]))
    ck("every readout differs from the resting message",
       d["run_text"] != d["rest"] and d["other_text"] != d["rest"], "all three distinct")

    ck("runnable is decided by the manifest, not the map's status string",
       d["runnable_flag_manifest"] is True and d["runnable_flag_bogus"] is False,
       "ashburn=True, bogus key=False")

    # ---- THE SEARCH BOX ---------------------------------------------------------------------
    ck("the search input exists and its index is loaded",
       d.get("search_input_exists") and d.get("search_index_ready"),
       "input present, registry ready")
    qa = d.get("q_apple") or {}
    ck("searching a name returns matches, best first",
       qa.get("n", 0) >= 1 and "APPLE" in (qa.get("first") or "").upper(),
       "%d match(es), first = %r" % (qa.get("n"), (qa.get("first") or "")[:54]))
    ck("a runnable match offers to RUN THE AGENT and is not disabled",
       "RUN THE AGENT" in (qa.get("first") or "").upper() and qa.get("first_disabled") is False,
       "the top hit is openable")
    qe = d.get("q_equinix") or {}
    ck("a query returns both kinds of match, run and no-run",
       qe.get("n", 0) >= 1 and (qe.get("n_norun") or 0) >= 1,
       "%d match(es), %d of them with no published run" % (qe.get("n"), qe.get("n_norun") or 0))
    ck("a match with no agent run is shown and marked as such, not offered as a run",
       qe.get("norun_marked") is True
       and "RUN THE AGENT" not in (qe.get("norun") or "").upper(),
       "%r" % (qe.get("norun") or "")[:62])
    ck("and it does NOT claim to be disabled, because it opens that facility's specs",
       qe.get("norun_aria") is None,
       "aria-disabled=%r" % qe.get("norun_aria"))
    qs = d.get("q_short") or {}
    ck("a one-character query refuses rather than listing everything",
       qs.get("n") == 0 and "two characters" in (qs.get("note") or ""),
       repr((qs.get("note") or "")[:52]))
    qn = d.get("q_none") or {}
    ck("no match says so plainly instead of showing an empty box",
       qn.get("n") == 0 and "No facility matches" in (qn.get("note") or ""),
       repr((qn.get("note") or "")[:52]))
    qt = d.get("q_state") or {}
    ck("a state code matches facilities in that state",
       qt.get("n", 0) >= 1, "%d match(es) for a state code" % qt.get("n", 0))

    print("\n" + "=" * 78)
    if fails:
        print("VERDICT: FAIL -- %d finding(s): %s" % (len(fails), "; ".join(fails)))
    else:
        print("VERDICT: PASS -- the hover readout names the facility under the cursor, the search")
        print("         box finds facilities by name and offers only the ones that really run, and")
        print("         both say honestly when no agent run exists for a site.")
        print("   NOT VERIFIED HERE, stated rather than implied:")
        print("     * that map.on('mousemove') is wired to natReadout(). Headless Chrome cannot")
        print("       load MapLibre in this environment (gotcha #155), so that needs a real browser.")
        print("     * that typing fires the search. `oninput` is set and searchRender() is called")
        print("       directly here; a real keystroke is not simulated.")
    print("=" * 78)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
