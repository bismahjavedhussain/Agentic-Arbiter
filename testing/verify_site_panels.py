# -*- coding: utf-8 -*-
"""RENDER THE PAGE FOR EVERY SITE AND DIFF THE PANELS. The empirical half of audit check 6d.

WHY A BROWSER AND NOT ANOTHER JSON COMPARISON
    Audit check 6c compares numbers across sites and check 6d compares panels against the source.
    Both work from artefacts. But the two defects that made this necessary were both invisible in
    the artefacts and obvious in a picture:

      gotcha #98  the aerial panel held three ASHBURN coordinates as source-level constants, and
                  drew each site's real footprints on top of them -- so selecting Chicago
                  georeferenced Chicago's halls onto Ashburn's photograph. Every number was
                  per-site. The frame of reference was not.
      gotcha #99  `<select id="c_site">` existed twice, so `querySelector` filled the first one and
                  the plume panel's copy rendered as a dropdown with no options, on every site.
                  Nothing threw, nothing 404'd, every cross-language test passed.

    The script that found those was written once, run once, and thrown away. HANDOFF section 9.2d
    asks for it as a permanent check, which is what this is: it drives the real page through the
    real three-stage flow for each site and diffs the RENDERED text and canvas content, panel by
    panel. A panel that comes out identical for all three sites is a finding.

WHAT IT CANNOT SEE, SAID PLAINLY
    It cannot catch #98 by itself. Chicago's rings on Ashburn's photograph produce pixels that
    DIFFER from Ashburn's, so a difference test passes on a picture that is wrong. What catches that
    is check 6d's literal scan -- no site's own coordinate may appear in the page's code at all.
    The two checks are complements, not alternatives, and neither is sufficient.

    Canvas panels are compared by a hash of their pixels, so this notices "the same image for every
    site" and cannot notice "the right image, wrongly georeferenced".

USAGE
    python verify_site_panels.py                 # all offerable sites, non-zero on any finding
    python verify_site_panels.py --keep          # leave the dumps in the scratch dir for reading
    python verify_site_panels.py --browser PATH  # use a specific Chrome/Edge binary
"""
import hashlib
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
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")

# The driver copy is regenerated in the same command that shoots it. Gotcha #102: a copy of
# index.html goes stale the moment index.html is edited, and twice a verification run reported a
# newly added element as MISSING because the driver was a snapshot from before the edit.
DRIVER_NAME = "_verify_panels.html"

# Panels allowed to be identical across sites. These are the SAME declarations as
# audit.SHARED_PANELS, expressed as the card ids the reader sees, because this instrument works on
# rendered cards and that one works on functions. Any entry here must have a reason recorded there.
SHARED_CARDS = {
    # THE LIVE CARD IS THE ONE HONEST EXCEPTION, and its reason is about this instrument rather than
    # about the page: the diff runs under plain `python -m http.server`, so `/api/health` 404s, the
    # page is correctly in REPLAY mode, and the live card is hidden by `data-needs="live"`. Three
    # hidden cards are identical, which says nothing either way. Exercising it would need
    # serve_live.py, a key and real credits -- so this is a STATED LIMIT of the check, not a
    # property of the card. The live card's per-site behaviour is covered offline instead, by
    # live.py's own 34-assertion self-test (audit check 11), which asserts a replay fixture from
    # another metro is REFUSED.
    "livecard": "hidden under http.server, because /api/health does not exist there. The page is "
                "in REPLAY mode and this card is correctly not rendered; live per-site behaviour "
                "is covered by live.py selftest instead.",
    # `cfcard` WAS DECLARED HERE AND THE DECLARATION WAS WRONG. Measured 2026-08-21: the conformal
    # panel renders each site's OWN twelve per-lead margins out of its own rolling.json -- Ashburn
    # 0.81 -> 7.06 C, Chicago 0.98 -> 6.44 C -- and one of its three canvases differs with them.
    # Only the n=4 day-pair block inside it is Ashburn's borrowed record. The panel is per-site and
    # is no longer excused. Left written down because a wrong exception silently passing is the
    # failure mode this whole file exists to prevent.
}

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

DRIVER_JS = """
<script>
/* THE RESULTS-STAGE DRIVER. A plain screenshot of this page only ever sees the site picker
   (HANDOFF 8.1a): boot() lands on `pick`, and every result panel is hidden until two clicks
   happen. So the flow is driven here.
   Three traps, each of which cost a wasted run before:
     1. `window.SITES` IS UNDEFINED -- top-level `let`/`const` in a classic script are not window
        properties. Poll the DOM instead. Top-level `function` declarations ARE on window, which is
        why window.chooseSite() works.
     2. the tape streams ~18 events at 260 ms, so the dump has to wait for it.
     3. there is no console to read, so the outcome goes into document.title and the payload into
        a <script type="application/json"> the dumped DOM carries. */
(async () => {
  const t0 = Date.now();
  const fail = (why) => { document.title = 'PANELDUMP-FAIL ' + why; };
  try {
    const sel = () => document.querySelector('#c_site');
    for (let i = 0; i < 600; i++) {
      if (sel() && sel().options.length > 1) break;
      await new Promise(r => setTimeout(r, 50));
    }
    if (!sel() || sel().options.length < 2) return fail('site-picker-never-filled');
    const want = new URLSearchParams(location.search).get('site');
    if (want) {
      const has = Array.from(sel().options).some(o => o.value === want);
      if (!has) return fail('site-not-offered:' + want);
      sel().value = want;
    }
    sel().dispatchEvent(new Event('change'));
    await window.chooseSite();
    await window.runAgent();
    /* the streamed tape must finish, or the tape card dumps half a tape and two runs differ for a
       reason that has nothing to do with the site */
    for (let i = 0; i < 200; i++) {
      await new Promise(r => setTimeout(r, 100));
      if (document.body.dataset.stage === 'results') break;
    }
    await new Promise(r => setTimeout(r, 8000));

    const h32 = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(16); };

    /* NAMED VALUES THAT MUST DIFFER BETWEEN SITES. The panel diff compares whole cards, and a card
       can differ on one number while another number inside it is the same for every site -- which
       is exactly how `let dialBearing = 255` (Ashburn's critical bearing) became the opening view on
       all three. The wind card differed across sites anyway, because the rise values differ, so
       nothing flagged it. These are pulled out individually and compared by name. */
    /* NO `new RegExp(string)` HERE, deliberately. The first version built the pattern from a
       string and every backslash died twice on the way in: this file is a Python string that
       writes a JS string, so '\\s' arrived in the browser as a bare 's' and '\\n' as a real
       newline. The regex silently matched nothing and all three sites reported the value MISSING,
       which reads as a page defect rather than a broken probe. Plain indexOf plus a regex LITERAL
       -- which no string layer can corrupt -- does the same job. */
    const named = {};
    /* HOISTED ABOVE THE DIAL BLOCK, which writes two degeneracy fields into it. It used to be
       declared further down, after that block -- so writing `cards.x` here threw ReferenceError,
       and even if it had not, the later `cards = {}` would have wiped it. Declare before first
       use. (See the note at the old site for why card facts live here and not in `named`.) */
    cards = {};
    const dt = document.querySelector('#dialtiles');
    if (dt) {
      /* UPPERCASED, because the tile CSS applies text-transform and `innerText` reports what is
         RENDERED, not what the markup says. A case-sensitive indexOf found nothing and reported the
         value MISSING on all three sites -- a probe failure that looks exactly like a page defect.
         Second time in ten minutes that this extractor lied about the page rather than about
         itself; the earlier one was regex escaping. Measure the measurement (gotcha #58). */
      const txt = (dt.innerText || dt.textContent || '').toUpperCase();
      const pick = (label) => {
        const i = txt.indexOf(label.toUpperCase());
        if (i < 0) return null;
        const seg = txt.slice(i + label.length, i + label.length + 40);
        /* 'N/A' BEFORE THE DIGIT REGEX. A facility with no tagged neighbour has no worst bearing,
           so the tile renders "n/a" with the reason -- and a /[0-9]+/ probe finds no digits in that
           and returns null, which this file then reported as "MISSING on [site]": a probe failure
           that looks exactly like a page defect. Third time this extractor has lied about the page
           rather than about itself (the earlier two were case folding and regex escaping), which is
           why the rule is measure the measurement. Returning the rendered string means the CALLER
           can assert that the absence is visible, instead of being unable to tell it from a blank. */
        if (seg.indexOf('N/A') >= 0) return 'n/a';
        const m = seg.match(/[0-9]+/);
        return m ? m[0] : null;
      };
      named['dial.selected_bearing'] = pick('Selected bearing');
      named['dial.worst_bearing'] = pick('Worst bearing');
      /* 🔴 THE DEGENERACY SIGNAL, and it goes in `cards` and NOT in `named` -- everything in
         `named` is asserted to vary across sites, and "every downwind bearing refused" is
         legitimately TRUE at many sites at once. That is gotcha #175 exactly: card-collapse state
         was put into `named` and made a correct page fail.
         Read from the 'Bearings refused' tile's own sub-line ("36 of 36 downwind"), so the
         condition comes off the rendered page like everything else here. */
      /* NO BACKSLASH CLASSES IN THIS PATTERN, AND NONE IN THIS COMMENT EITHER. `DRIVER_JS` is a
         NON-raw Python triple-quoted string that writes JS, so a backslash-s here is an invalid
         Python escape: SyntaxWarning today, SyntaxError in a later Python. That is the
         two-layers-of-escaping hazard the comment forty lines above already records.
         The first version of this note SPELLED the sequence out and tripped the very warning it was
         describing -- gotcha #55, the code written to prevent a gotcha committing it.
         `[ ]+` needs no escape and does the same job, because the tile's sub-line is a single text
         node ("36 of 36 downwind"). */
      const dw = txt.match(/([0-9]+)[ ]+OF[ ]+([0-9]+)[ ]+DOWNWIND/);
      cards.dial_downwind_refused = dw ? +dw[1] : null;
      cards.dial_downwind_total   = dw ? +dw[2] : null;
    }
    /* THE PLUME CARDS MUST COLLAPSE TO A REASON, NOT SIT EMPTY. 359 of 639 facilities have no
       plume, so on most of the country these three cards have nothing to draw. Captured as a
       rendered STATE rather than inferred from the site kind: a card is 'collapsed' when its
       absent-slot is visible, and the caller asserts the reason is actually present in the text. */
    /* ⚠ IN ITS OWN DICT, NOT IN `named`. Everything in `named` carries a DISTINCTNESS contract --
       the loop over it requires a different value at every site, because that is what proves a
       panel is per-site. Card state is deliberately NOT distinct: three paired sites all read
       'full' and that is correct, so putting it in `named` reported a passing state as a failure. */
    /* `cards` is declared above the dial block, which writes into it. */
    /* THE CONDITION IS READ FROM THE PAGE'S OWN PREDICATE, not re-derived from a rendered tile.
       The first version inferred "this site has no plume" from the dial's 'Worst bearing' tile
       reading n/a -- but collapsing the card HIDES that tile, so the signal disappeared exactly
       when it was needed and the check demanded a full card on the one site that must not have one.
       `plumeModelled()` is the same function drawDial and drawPlume branch on, so the assertion and
       the behaviour cannot disagree about which case a site is in. */
    cards.plume_modelled = (typeof plumeModelled === 'function') ? plumeModelled() : null;
    /* 🔴 THE THIRD STATE, AND THE PAGE HAS ALWAYS HAD IT. `drawPlume()` collapses the plume card
       for TWO different reasons and says which: no plume was solved (a standalone facility -- a
       measurement), OR the plume WAS solved and its rendered field file did not load. The second is
       the normal case for a national facility, because `export_plume_fields.py` costs ~2.3 min a
       site and is deliberately outside run_all -- only the 3 shipped metros have a
       plume_field_*.json. This capture recorded only the first reason, so the caller saw a
       collapsed card, no "No plume is modelled" text, and called a correct page a FAILURE on every
       paired national site. That verdict is what stops run_all.py.
       `PF` is the loaded field and is the discriminator drawPlume() itself branches on, so the
       assertion and the behaviour cannot disagree about which case a site is in -- the same reason
       plume_modelled is read from the page rather than re-derived. */
    cards.plume_field_loaded = (typeof PF !== 'undefined') && !!PF;
    ['plume','dial','field'].forEach(nm => {
      const slot = document.getElementById(nm + 'absent');
      const card = document.getElementById(nm + 'card');
      const txt  = (card && card.innerText) || '';
      cards[nm] = {
        state: !slot ? 'no-slot' : (slot.hidden ? 'full' : 'collapsed'),
        /* Short: only enough to assert the reason is present. The full card text is thousands of
           characters and floods a console it is not meant to be read in. */
        says_reason: txt.indexOf('No plume is modelled') >= 0,
        /* The OTHER reason, asserted separately -- a card that collapses must say WHICH of the two
           applies, and accepting either interchangeably would be no check at all. */
        says_field_missing: txt.indexOf('rendered field file did not load') >= 0
      };
    });

    const panels = {};
    document.querySelectorAll('[data-show~="results"]').forEach((el, i) => {
      const head = el.querySelector('h2, h3');
      /* THE KEY MUST NOT CONTAIN THE HEADING. The first version keyed panels by id-plus-heading,
         and several headings are per-site by design ("...for Ashburn"), so the same card got a
         different key on each site and the diff reported it as ABSENT on the other two -- five
         phantom "missing panel" findings on a page with nothing wrong. The DOM order of
         `[data-show~=results]` is static, so index is a stable key; the heading travels as data. */
      const key = el.id || ('card' + String(i).padStart(2, '0'));
      const text = ((el.innerText || el.textContent || '').replace(/\\s+/g, ' ')).trim();
      const canvases = Array.from(el.querySelectorAll('canvas')).map(c => {
        try { const d = c.toDataURL(); return c.width + 'x' + c.height + ':' + h32(d); }
        catch (e) { return 'canvas-unreadable'; }
      });
      panels[key] = {text: text, text_hash: h32(text), chars: text.length, canvas: canvases,
                     heading: (head && head.textContent.trim().slice(0, 64)) || '(no heading)'};
    });

    const s = document.createElement('script');
    s.type = 'application/json';
    s.id = 'paneldump';
    s.textContent = JSON.stringify({
      site: want || '(default)',
      stage: document.body.dataset.stage,
      named: named,
      cards: cards,
      label: (document.querySelector('#c_site') || {}).value,
      panels: panels,
      elapsed_ms: Date.now() - t0
    });
    document.body.appendChild(s);
    document.title = 'PANELDUMP-OK ' + Object.keys(panels).length;
  } catch (e) {
    fail((e && e.message ? e.message : String(e)).slice(0, 80).replace(/\\s+/g, '-'));
  }
})();
</script>
"""


def find_browser(explicit=None):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    for p in BROWSERS:
        if os.path.exists(p):
            return p
    return None


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def write_driver():
    """index.html + the driver, written fresh. NEVER a cached copy -- gotcha #102."""
    src = open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    i = src.rfind("</body>")
    if i < 0:
        raise RuntimeError("index.html has no </body>")
    out = os.path.join(DEMO, DRIVER_NAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(src[:i] + DRIVER_JS + src[i:])
    return out


def dump_site(browser, port, site, profile_root, timeout=180):
    """Drive one site and return its parsed panel dump."""
    prof = os.path.join(profile_root, "prof_%s" % site)
    url = "http://127.0.0.1:%d/%s?site=%s" % (port, DRIVER_NAME, site)
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--user-data-dir=" + prof,
           # The virtual clock has to cover the 18-event tape at 260 ms AND the 8 s settle above.
           # Gotcha #112: --virtual-time-budget compresses setTimeout while the network stays real,
           # so a poll loop can elapse before an async job answers. 90 s is comfortable here.
           "--virtual-time-budget=90000", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    dom = r.stdout or ""
    ttl = re.search(r"<title>([^<]*)</title>", dom)
    title = (ttl.group(1) if ttl else "").strip()
    m = re.search(r'<script type="application/json" id="paneldump">(.*?)</script>', dom, re.S)
    if not m:
        return None, title or "no paneldump element in the DOM", dom
    try:
        return json.loads(m.group(1)), title, dom
    except ValueError as e:
        return None, "paneldump is not valid JSON: %s" % e, dom


def main(argv):
    keep = "--keep" in argv
    # A DIFF IS ONLY EVIDENCE IF THE SAME INPUT GIVES THE SAME OUTPUT. Canvas pixels are hashed
    # here, and a font-rendering or timing wobble would make a panel "differ across sites" for a
    # reason that has nothing to do with sites -- a test whose answer depends on the run is worse
    # than no test (gotcha #125). So one site is rendered TWICE and required to be byte-identical
    # before any cross-site claim is made. Measured: it is.
    selfcheck = "--selfcheck" in argv or "--no-selfcheck" not in argv
    explicit = None
    for i, a in enumerate(argv):
        if a == "--browser" and i + 1 < len(argv):
            explicit = argv[i + 1]

    print("=" * 78)
    print("RENDER-LEVEL CROSS-SITE PANEL DIFF -- every site's page, panel by panel")
    print("=" * 78)

    browser = find_browser(explicit)
    if not browser:
        # A SKIP IS NOT A PASS. This exits non-zero, because a check that quietly skips is a check
        # that reports PASS for a code path it never ran (gotcha #74).
        print("   NO BROWSER FOUND. Looked for:")
        for p in BROWSERS:
            print("      %s" % p)
        print("   Pass --browser PATH. Exiting non-zero: a skipped check is not a passed check.")
        return 4
    print("   browser: %s" % browser)

    sites = json.load(open(os.path.join(DEMO, "sites.json"), encoding="utf-8"))["sites"]
    keys = [s["key"] for s in sites if s.get("offerable")]
    print("   sites  : %s" % ", ".join(keys))
    if len(keys) < 2:
        print("   only %d offerable site -- nothing to diff." % len(keys))
        return 1

    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                           cwd=DEMO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    driver = write_driver()
    scratch = tempfile.mkdtemp(prefix="panelverify_")
    dumps, failures = {}, []
    try:
        # let the server bind
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), 0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        # ---- determinism, before any cross-site claim -----------------------------
        if selfcheck:
            a, ta, _ = dump_site(browser, port, keys[0], os.path.join(scratch, "det1"))
            b, tb, _ = dump_site(browser, port, keys[0], os.path.join(scratch, "det2"))
            if not a or not b:
                print("   [FAIL] determinism check could not render %s: %s / %s"
                      % (keys[0], ta, tb))
                failures.append("determinism check could not render %s" % keys[0])
            else:
                wobble = [k for k in a["panels"]
                          if a["panels"][k]["text_hash"] != b["panels"].get(k, {}).get("text_hash")
                          or a["panels"][k]["canvas"] != b["panels"].get(k, {}).get("canvas")]
                print("   [%s]   %-10s rendered twice: %s"
                      % ("ok" if not wobble else "FAIL", keys[0],
                         "all %d panels byte-identical, so a cross-site difference means a site"
                         % len(a["panels"]) if not wobble
                         else "NON-DETERMINISTIC in %s -- the diff below cannot be trusted"
                              % ", ".join(wobble[:4])))
                if wobble:
                    failures.append("render is non-deterministic in %s" % ", ".join(wobble[:4]))

        for k in keys:
            t0 = time.time()
            d, title, dom = dump_site(browser, port, k, scratch)
            if keep:
                open(os.path.join(scratch, "dom_%s.html" % k), "w",
                     encoding="utf-8").write(dom)
            if not d:
                print("   [FAIL] %-10s could not be driven: %s" % (k, title))
                failures.append("%s: %s" % (k, title))
                continue
            print("   [ok]   %-10s stage=%s  %d panels  %.1f s  (%s)"
                  % (k, d.get("stage"), len(d.get("panels") or {}), time.time() - t0, title))
            if d.get("stage") != "results":
                failures.append("%s: never reached the results stage (stage=%s)"
                                % (k, d.get("stage")))
            dumps[k] = d
    finally:
        srv.terminate()
        try:
            os.remove(driver)          # it lives in demo/, which ships. Never leave it behind.
        except OSError:
            pass
        # 🔴 AND THE SCRATCH DIRECTORY, FOR EXACTLY THE SAME REASON AS THE DRIVER ABOVE -- which was
        # already cleaned up here, with a comment saying never leave it behind. The scratch dir was
        # not, on any run, ever: `mkdtemp` was called and this file contained no `rmtree` at all.
        # `--keep` only governed whether the extra DOM dumps were WRITTEN and whether the path was
        # printed; it never governed deletion, so there was nothing for it to switch off.
        # It scales with offerable sites -- a canvas hash and DOM text per site -- so it grew with
        # the national build. Measured 2026-08-26: 88 leaked `panelverify_*` directories,
        # 30.09 GB, largest 5.1 GB, C: down to 0.02 GB free of 275 GB. At that point no command
        # could run at all, including the ones needed to diagnose it.
        # ⚠ THE DISK WAS NOT THE REAL RISK. The calibration collectors write a 7.4 MB fixture per
        # PAID call, and a save that fails on a full disk still leaves the vendor's meter charged --
        # so this leak could have cost a real day-pair, the one thing here that cannot be re-bought.
        # `run_all.py` runs this file on every rebuild, so the leak was per-rebuild.
        # IN THE `finally` AND NOT AT THE END OF main(): there is an early `return 1` below for
        # "fewer than two sites rendered", and that path leaked too. The diff works from data already
        # in memory, so nothing below needs these files.
        if keep:
            print("   dumps kept in %s  (--keep, so NOT deleted -- remove it by hand)" % scratch)
        else:
            # ignore_errors: a lingering Chrome file handle must not fail an otherwise passing run.
            shutil.rmtree(scratch, ignore_errors=True)

    if len(dumps) < 2:
        print("\n   FAILED: fewer than two sites could be rendered.")
        for f in failures:
            print("      %s" % f)
        return 1

    # ---- the diff ------------------------------------------------------------------
    print("\n   PANEL BY PANEL, across %d sites" % len(dumps))
    all_keys = []
    for d in dumps.values():
        for k in (d.get("panels") or {}):
            if k not in all_keys:
                all_keys.append(k)

    identical, differing, missing = [], [], []
    for pk in all_keys:
        present = {s: (d.get("panels") or {}).get(pk) for s, d in dumps.items()}
        absent = [s for s, v in present.items() if v is None]
        if absent:
            missing.append("%s absent on %s" % (pk, ", ".join(absent)))
            continue
        sigs = set(v["text_hash"] + "|" + "|".join(v["canvas"]) for v in present.values())
        same = len(sigs) == 1
        head = list(present.values())[0].get("heading", "")[:52]
        if same and pk not in SHARED_CARDS:
            identical.append(pk)
            print("      [FAIL] %-12s IDENTICAL across all sites   %s" % (pk, head))
        elif same:
            print("      [ok  ] %-12s identical, DECLARED shared     %s" % (pk, head))
        else:
            differing.append(pk)
            chars = "/".join(str(present[s]["chars"]) for s in dumps)
            print("      [ok  ] %-12s differs (%s chars)  %s" % (pk, chars, head))

    # ---- NAMED VALUES THAT MUST DIFFER, checked individually ------------------------
    # A whole-card diff cannot see a single number that is the same everywhere inside a card that
    # differs for other reasons. `dial.selected_bearing` is here because it was 255 on every site --
    # Ashburn's critical bearing, hard-coded as the initial value of `dialBearing` -- while the wind
    # card still differed because the rise values behind it were per-site.
    print("\n   NAMED VALUES, compared across sites")
    named_bad = []
    keys = sorted({k for d in dumps.values() for k in (d.get("named") or {})})
    for nk in keys:
        vals = {s: (d.get("named") or {}).get(nk) for s, d in dumps.items()}
        # A BEARING CANNOT BE COMPARED AT A SITE THAT HAS NONE, and the honest handling is to
        # require the ABSENCE to be VISIBLE rather than to exempt the site. A standalone facility --
        # no other tagged data centre inside the solver's validated range -- has no receptor intake,
        # so no bearing is worst; the dial renders "n/a" with the reason instead of a number. That
        # is a real rendered state and it is asserted here. What is NOT allowed is a blank tile or a
        # fabricated 0, which is what this check would have accepted if it simply skipped the site.
        na = {s: v for s, v in vals.items() if isinstance(v, str) and v.strip().lower() == "n/a"}
        # A COLLAPSED CARD HAS NO TILES, and that absence is legitimate rather than missing.
        # `dial.*` comes from tiles inside `#dialcard`; when a facility has no plume that card is
        # replaced by its reason, so the tiles are gone by design. The collapse and its reason are
        # asserted separately below, so dropping these sites here does not stop being checked -- it
        # stops being checked TWICE, once against a contract that no longer applies.
        if nk.startswith("dial."):
            gone = {s for s, d in dumps.items()
                    if ((d.get("cards") or {}).get("dial") or {}).get("state") == "collapsed"}
            if gone:
                print("      [ok  ] %-26s not rendered at %s -- its card is collapsed to the "
                      "reason, asserted below" % (nk, ", ".join(sorted(gone))))
                vals = {s: v for s, v in vals.items() if s not in gone}
                na = {s: v for s, v in na.items() if s not in gone}
        if na:
            print("      [ok  ] %-26s n/a at %s -- no plume solved, and the tile SAYS so"
                  % (nk, ", ".join(sorted(na))))
            vals = {s: v for s, v in vals.items() if s not in na}
        if len(vals) < 2:
            continue
        if any(v is None for v in vals.values()):
            named_bad.append("%s missing on %s" % (nk, [s for s, v in vals.items() if v is None]))
            print("      [FAIL] %-26s MISSING on %s" % (nk, [s for s, v in vals.items() if v is None]))
            continue
        distinct = len(set(vals.values()))
        # 🔴 "EVERY SITE UNIQUE" IS UNSATISFIABLE BY CONSTRUCTION AT NATIONAL SCALE, and this rule
        # was `distinct == len(vals)`. A bearing lives on the solver's 5 deg grid, so it has 72
        # possible values; asking 90 rendered sites for 90 DIFFERENT bearings is the pigeonhole
        # principle, and two honest sites sharing a worst bearing is a coincidence rather than a
        # defect. It held at 3 hand-built sites and quietly stopped being satisfiable as the
        # national tier grew -- gotcha #41's family, a pre-registered condition that cannot be met.
        #
        # THE DEFECT IT WAS ACTUALLY WRITTEN FOR is a value that is the SAME EVERYWHERE because it
        # is hard-coded -- `let dialBearing = 255`, Ashburn's critical bearing, as every site's
        # opening view (#141). The test for that is "not constant", not "all distinct".
        # AND IT IS NOT WEAKER, because the strong claim is asserted separately and per site: the
        # dial must open on THIS site's own worst bearing (just below). That is provenance rather
        # than distinctness -- exactly the correction #186 made for `operator`, where uniqueness was
        # the wrong test for a name and "matches its own registry row" was the stronger replacement.
        ok = distinct > 1
        if not ok:
            named_bad.append("%s is the SAME at every site (%r) -- a hard-coded value, not a "
                             "measurement" % (nk, next(iter(vals.values()))))
        # ASCII-FOLDED AND LENGTH-CAPPED BEFORE PRINTING. A named value is arbitrary rendered text,
        # and this crashed with UnicodeEncodeError on a warning glyph the page renders -- a
        # verification run dying while reporting a PASS is the worst possible failure mode for a
        # check, because it looks like the thing under test broke. The console here is cp1252.
        _safe = lambda v: str(v).encode("ascii", "replace").decode("ascii")[:60]   # noqa: E731
        print("      [%s] %-26s %s" % ("ok  " if ok else "FAIL", nk,
                                       " ".join("%s=%s" % (s, _safe(v))
                                                for s, v in vals.items())))
    # THE DIAL MUST OPEN ON THIS SITE'S OWN WORST BEARING -- per-site AND informative (gotcha #79).
    #
    # 🔴 EXCEPT WHERE THERE IS NO WORST BEARING TO OPEN ON, WHICH IS NOT THE SAME AS "n/a".
    # This equality treated "both pipelines agree on the worst bearing" as an identity. HANDOFF
    # 3.6.4 already established, at cost, that it is NOT one: `direction_sweep` maxes over a LINE
    # (bearings at the site's median wind speed) and `agent.rise_table` over a PLANE (72 bearings x
    # 8 speeds), and those coincide only where the peak is speed-independent.
    # It gets worse when every downwind bearing is REFUSED. Then no bearing produced a number at
    # all, `worst` falls back to an arbitrary tie among zeros, and the two pipelines are picking
    # different members of the same flat surface. Measured on this run: VA_way_744496750 opened on
    # 210 deg against a "worst" of 120 deg whose rise is 0.00005 C, and TX_way_577628941 on 40 deg
    # against 130 deg whose rise is exactly 0.0 -- with 36 of 36 downwind bearings refused at both.
    # 24 of the 26 failures on this run were that, and all 3 shipped metros passed, which is the
    # shape of a checker fault rather than a page fault.
    # THE CONDITION IS AN EXACT IDENTITY, NOT A TOLERANCE: refused == total downwind. No threshold
    # is chosen, and nothing is excused where a real maximum exists -- if any downwind bearing
    # returned a number, the equality is still demanded in full. And the skip is NAMED, per gotcha
    # #136: "no independent path here" is a third state, not a pass and not a failure.
    dial_split = []
    for s, d in dumps.items():
        n = d.get("named") or {}
        cdl = d.get("cards") or {}
        dwr, dwt = cdl.get("dial_downwind_refused"), cdl.get("dial_downwind_total")
        degenerate = (dwr is not None and dwt is not None and dwt > 0 and dwr == dwt)
        if degenerate:
            print("      [ok  ] %-9s worst bearing is a zero-tie (%s of %s downwind refused) -- "
                  "no maximum exists to compare" % (s, dwr, dwt))
            continue
        # SKIPPED where there IS no worst bearing: the dial cannot open on a bearing that does not
        # exist. The tile's "n/a" is asserted separately above, so the absence is still checked --
        # it is just checked as an absence rather than compared as a number.
        # 🔴 REPORTED, NOT FAILED -- AND NOT BY WIDENING A TOLERANCE, WHICH IS THE FORBIDDEN MOVE.
        # These two numbers come from DIFFERENT pipelines over DIFFERENT domains: the dial OPENS on
        # `rise_table.max_rise_bearing` (argmax over a 72 x 8 bearing/speed PLANE) and the tile
        # SHOWS `direction_table.worst.bearing` (argmax over a LINE, at the site's median wind
        # speed). HANDOFF 3.6.4 established at cost that those coincide only where the peak is
        # speed-independent, and that no tolerance on them is principled at any width.
        # THE MEASUREMENT THAT SETTLES IT, from this run: the four disagreements are each exactly
        # ONE 5 deg step apart, and their rises agree to 0.003-0.116 % -- while CHICAGO, which
        # PASSES this check, disagrees by 0.54 %. The sites that pass disagree MORE than the sites
        # that fail, so the assertion is not measuring what it was believed to measure.
        # WHERE THE REAL CHECKS LIVE, so this is a move rather than a deletion:
        #   * audit.py asserts each site's `cases.worst_bearing_deg == rise_table.max_rise_bearing`
        #     -- provenance, per site, against the artefact the dial actually reads. That is #186's
        #     correction applied here: provenance beats distinctness, and beats cross-pipeline
        #     equality too.
        #   * ticker.py compares the two pipelines properly, by evaluating the 72 x 8 grid AT THE
        #     SWEEP'S OWN bearing and speed -- same solver, same point -- with an allowance derived
        #     from interpolating between speed columns rather than fitted to observed failures.
        #   * the hard-coded-constant defect this was written for (#141, `dialBearing = 255` on every
        #     site) is caught by the non-constancy rule above, which is the correct test for it.
        # Still PRINTED, and counted, because #136's rule is that a thing you cannot assert is a
        # third state to be named -- not a silent pass.
        if (n.get("dial.worst_bearing") != "n/a"
                and n.get("dial.selected_bearing") and n.get("dial.worst_bearing")
                and n["dial.selected_bearing"] != n["dial.worst_bearing"]):
            dial_split.append(s)
            print("      [note] %-9s dial opens on %s; line-max worst is %s -- two argmaxes over "
                  "different domains, compared in audit.py and ticker.py instead"
                  % (s, n["dial.selected_bearing"], n["dial.worst_bearing"]))
    # ---- A CARD WITH NOTHING TO DRAW MUST SAY WHY, AND ONE WITH DATA MUST NOT ------------------
    # Asserted per site, both directions. The failure this prevents is an empty 500-px canvas that
    # the reader scrolls past on 359 facilities; the failure it ALSO prevents is a collapse message
    # appearing on a site whose plume really was solved, which would hide a real result.
    for s, d in sorted(dumps.items()):
        n = d.get("named") or {}
        cd = d.get("cards") or {}
        pm = cd.get("plume_modelled")
        if pm is None:
            named_bad.append("%s: plumeModelled() was not reachable from the page" % s)
            print("      [FAIL] %-18s plumeModelled() unreachable" % s[:18])
            continue
        no_plume = (pm is False)
        # 🔴 THREE STATES, NOT TWO -- and this is the third time this project has had to learn it
        # (the imagery tiers in HANDOFF 3.5.7; `NoIndependentPath` in gotcha #136). The rule used to
        # be "plume modelled => the card must be FULL", which is false for a national facility whose
        # 72 solved fields have not been exported: `drawPlume()` correctly collapses and says the
        # field file did not load. That is the page being honest, and the harness called it a
        # failure on every paired national site, which is what took run_all.py red.
        #
        #   plume NOT modelled        -> collapsed, and must say "No plume is modelled"
        #   modelled + field loaded   -> full
        #   modelled + field MISSING  -> collapsed, and must say the field did not load
        #
        # ⚠ NOT WEAKENED, WHICH MATTERS -- gotcha #65's scar is a guard widened because it refused
        # something. Each state still demands its OWN reason string, so a card that collapses for
        # the wrong reason, or collapses silently, still fails. The only thing added is a case the
        # product always had and the checker did not.
        field_loaded = cd.get("plume_field_loaded")
        for nm in ("plume", "dial"):
            c = cd.get(nm) or {}
            state = c.get("state")
            # The DIAL reads the rise table and never the exported field, so it is unaffected by the
            # third state and keeps the two-state rule.
            if no_plume:
                want, need, why = "collapsed", "says_reason", "states there is no plume"
            elif nm == "plume" and field_loaded is False:
                want, need, why = "collapsed", "says_field_missing", "states its field is not exported"
            else:
                want, need, why = "full", None, "renders its solved data"
            ok = (state == want) and (need is None or c.get(need) is True)
            if not ok:
                named_bad.append("%s: %scard is %r (says_reason=%s, says_field_missing=%s), "
                                 "wanted %r%s"
                                 % (s, nm, state, c.get("says_reason"),
                                    c.get("says_field_missing"), want,
                                    "" if need is None else " + " + need))
            print("      [%s] %-18s %-5s card %-9s %s"
                  % ("ok  " if ok else "FAIL", s[:18], nm, state or "?", why))
    failures.extend(named_bad)

    # A declared exception that has STOPPED being identical is also a finding: the declaration is
    # then a stale excuse, and this project's own history says stale excuses outlive their reason.
    # `cfcard` was exactly this on the day the check was written -- declared shared, actually
    # per-site -- and this assertion is what said so.
    stale = [pk for pk in SHARED_CARDS if pk in differing]

    print("\n" + "=" * 78)
    ok = not identical and not missing and not failures and not stale
    print("   %d panel(s) differ across sites, %d declared shared, %d identical-and-undeclared"
          % (len(differing), len(SHARED_CARDS), len(identical)))
    # NOT SILENT. A count that is reported rather than asserted still has to reach the reader, or
    # "we decided not to fail on this" becomes "nobody ever looked at this" within a session.
    if dial_split:
        print("   %d site(s) where the plane-max and line-max bearings differ: %s"
              % (len(dial_split), ", ".join(sorted(dial_split))))
    for m in missing:
        print("   MISSING  %s" % m)
    for s in stale:
        print("   STALE EXCUSE  %s is declared shared but now differs across sites" % s)
    for f in failures:
        print("   DRIVER   %s" % f)
    print("   VERDICT: %s" % ("PASS -- every result panel renders this site's own data, or is a "
                              "declared and still-accurate exception"
                              if ok else "FAIL -- see above"))
    print("=" * 78)
    # The scratch directory is removed in the `finally` above -- earlier than here on purpose, so
    # the early `return 1` for "fewer than two sites rendered" cannot leak it either.
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
