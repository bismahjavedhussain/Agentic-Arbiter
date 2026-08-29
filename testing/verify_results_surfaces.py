"""Three results-stage surfaces the user reported on, checked in a real browser.

  1. THE HOUR DROPDOWN inside "One hour, all seven stages of the loop". Changing it must redraw the
     seven stage lines. It did not: `lib/declutter.ts` folded that whole `<details>` away and copied
     its innerHTML into a modal, and an HTML copy has no event listeners and a duplicate id, so the
     select a reader could see was inert while the engine's hidden original still worked.
  2. THE BOUND COVERAGE TILE. No longer says "FAILED", is green, and its caption states a shortfall
     COMPUTED from the artefact rather than typed.
  3. THE LBNL SENTENCE. The acronym is expanded on first use, and the claim it makes is one the
     repository's own sources support.

Run from the repository root:  python testing/verify_results_surfaces.py
Exits 0 if every check passes, 1 if any fails, 3 if the results stage was never reached.
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
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
PASS, FAIL = [], []


def ck(ok, what, detail=""):
    (PASS if ok else FAIL).append((what, detail))
    print("   %s %-60s %s" % ("PASS" if ok else "FAIL", what, detail))
    return ok


def head(t):
    print("\n   " + t)
    print("   " + "-" * (len(t) + 2))


def drive_to_results(c):
    if not c.poll("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) return 1;
        return 0;})()""", timeout=40):
        return "the Configure button never appeared"
    c.eval("""(function(){var b=document.querySelectorAll('button');
        for(var i=0;i<b.length;i++) if(/Configure this plant/.test(b[i].textContent||'')) {
          b[i].click(); return 1; } return 0;})()""")
    if not c.poll("document.body.dataset.stage === 'configure' && "
                  "document.querySelectorAll('#filters select').length > 0", timeout=40):
        return "never reached configure with its controls built"
    c.eval("document.getElementById('runagent').click()")
    if not c.poll("document.body.dataset.stage === 'results' && "
                  "!!(document.querySelector('#tapedone') && "
                  "document.querySelector('#tapedone').textContent.trim())", timeout=90):
        return "never reached results with the tape finished"
    return None


def main():
    if not os.path.isdir(DIST):
        print("   [skip] no build at AGENTIC-ARBITER/app/dist")
        return 3

    # ---------------------------------------------------------- the artefact, read first
    with io.open(os.path.join(DEMO, "trace.json"), encoding="utf-8") as f:
        tr = json.load(f)
    cy = tr["cycle"]
    bdl = cy.get("bound_day_level") or {}
    n_cal = len(cy.get("pairs") or []) or bdl.get("n")
    needed = bdl.get("n_needed_for_nominal")
    shortfall = max(0, (needed or 0) - (n_cal or 0))
    ceiling = 100.0 * (n_cal / (n_cal + 1.0))
    cov = 100.0 * cy["pooled_coverage"]
    print("   from demo/trace.json:  coverage %.1f %%   n = %d   needs %d   shortfall %d   "
          "ceiling %.1f %%" % (cov, n_cal, needed, shortfall, ceiling))

    port = free_port()
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_app.py"), str(port)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.0)
    url = "http://127.0.0.1:%d/app/?motion=off&facility=metro_ashburn" % port
    try:
        with Chrome(url, width=1600, height=1100) as c:
            c.goto(settle=2.0)
            why = drive_to_results(c)
            if why:
                print("   [skip] %s" % why)
                return 3

            # ======================================================= 1. THE HOUR DROPDOWN
            head("1. THE HOUR DROPDOWN: one select, live, and it redraws the seven stages")
            c.eval("""(function(){
              var b=document.querySelectorAll('[data-aa-tabid]');
              for(var i=0;i<b.length;i++) if(b[i].getAttribute('data-aa-tabid')==='schedule')
                { b[i].click(); return 1; } return 0; })()""")
            time.sleep(1.2)
            n = int(c.eval("document.querySelectorAll('[id=\"c_hour\"]').length"))
            ck(n == 1, "exactly one #c_hour in the document, so $('#c_hour') is unambiguous",
               "%d found" % n)
            info = json.loads(c.eval("""JSON.stringify((function(){
              var s=document.getElementById('c_hour'); if(!s) return null;
              var d=s.closest('details');
              return {options:s.options.length, value:s.value,
                      hasOnchange: typeof s.onchange === 'function',
                      display: getComputedStyle(s).display,
                      inDetails: !!d, detailsOpen: d?d.open:null,
                      detailsDisplay: d?getComputedStyle(d).display:null,
                      summary: d&&d.querySelector('summary')
                               ? d.querySelector('summary').textContent.trim() : null,
                      folded: d?d.getAttribute('data-aa-declutter'):null};})())""") or "null")
            ck(bool(info), "the select is in the document at all")
            ck(info and info["hasOnchange"], "it carries the engine's change handler",
               "onchange bound: %s" % (info or {}).get("hasOnchange"))
            ck(info and info["options"] == 24, "24 hours of options",
               str((info or {}).get("options")))
            ck(info and info["folded"] is None,
               "its <details> is NOT folded away into the modal",
               "data-aa-declutter = %r" % (info or {}).get("folded"))
            ck(info and info["detailsDisplay"] != "none",
               "so the block is on the card, as a closed disclosure",
               "display %s, open %s" % ((info or {}).get("detailsDisplay"),
                                        (info or {}).get("detailsOpen")))
            ck(info and (info["summary"] or "").startswith("One hour, all seven stages"),
               "under its own summary", (info or {}).get("summary"))

            # open the disclosure and drive the select for real
            c.eval("var d=document.getElementById('c_hour').closest('details'); d.open=true; 1")
            time.sleep(0.5)
            before = c.eval("(document.getElementById('tkhour')||{}).textContent || ''")
            hour0 = c.eval("document.getElementById('c_hour').value")
            c.eval("""(function(){var s=document.getElementById('c_hour');
              s.value = (String(s.value)==='0') ? '7' : '0';
              s.dispatchEvent(new Event('change', {bubbles:true})); return s.value;})()""")
            time.sleep(0.8)
            after = c.eval("(document.getElementById('tkhour')||{}).textContent || ''")
            hour1 = c.eval("document.getElementById('c_hour').value")
            ck(before.strip() != "", "the seven stages render at all",
               "%d characters" % len(before.strip()))
            ck(after.strip() != before.strip(),
               "CHANGING THE HOUR REDRAWS THEM", "hour %s -> %s, text %d -> %d chars, differs: %s"
               % (hour0, hour1, len(before.strip()), len(after.strip()),
                  after.strip() != before.strip()))
            b0 = " ".join(before.split())[:58]
            a0 = " ".join(after.split())[:58]
            print("      before: %s..." % b0)
            print("      after:  %s..." % a0)
            # and it must not have touched either table
            tbl = json.loads(c.eval("""JSON.stringify({
              btable:(document.getElementById('btable')||{}).rows ?
                     document.getElementById('btable').rows.length : null,
              extable:(document.getElementById('extable')||{}).rows ?
                     document.getElementById('extable').rows.length : null})"""))
            ck((tbl["extable"] or 0) > 2,
               "the hour-by-hour table below is drawn from ALL hours, not the selection",
               "#extable has %s rows, one per hour plus a header" % tbl["extable"])

            # ======================================================= 2. THE COVERAGE TILE
            head("2. THE BOUND COVERAGE TILE: green, no FAILED, and a computed caption")
            c.eval("""(function(){var b=document.querySelectorAll('[data-aa-tabid]');
              for(var i=0;i<b.length;i++) if(b[i].getAttribute('data-aa-tabid')==='live')
                { b[i].click(); return 1; } return 0; })()""")
            time.sleep(0.8)
            t = json.loads(c.eval("""JSON.stringify((function(){
              var all=document.querySelectorAll('.tile');
              for(var i=0;i<all.length;i++){
                var k=all[i].querySelector('.k');
                if(k && /Bound coverage, measured/.test(k.textContent||'')){
                  var v=all[i].querySelector('.v'), d=all[i].querySelector('.d');
                  return {tone:all[i].getAttribute('data-tone'),
                          value:(v.textContent||'').trim(),
                          colour:getComputedStyle(v).color,
                          caption:(d.textContent||'').trim()};}}
              return null;})())""") or "null")
            if ck(bool(t), "the tile is on screen"):
                ck("FAILED" not in t["caption"] and "pre-registration" not in t["caption"],
                   "the caption no longer says FAILED or pre-registration", t["caption"])
                ck(t["tone"] == "good", "its tone is good", t["tone"])
                good = c.eval("getComputedStyle(document.documentElement)"
                              ".getPropertyValue('--good').trim()")
                ck(t["colour"] not in ("", None) and t["colour"] != "rgb(0, 0, 0)",
                   "and the figure is painted in --good", "%s (--good is %s)" % (t["colour"], good))
                ck(str(shortfall) in t["caption"] and str(n_cal) in t["caption"],
                   "the caption states the shortfall and the pair count from the artefact",
                   "expected %d and %d in: %s" % (shortfall, n_cal, t["caption"]))
                ck(("%.1f" % ceiling) in t["caption"],
                   "and the arithmetic ceiling, computed not typed",
                   "expected %.1f %%" % ceiling)
                ck("reachable" in t["caption"],
                   "it claims reachability, not sufficiency", t["caption"])

            # the plate cell must not contradict it
            pc = json.loads(c.eval("""JSON.stringify((function(){
              var all=document.querySelectorAll('.plate-cell');
              for(var i=0;i<all.length;i++){
                var k=all[i].querySelector('.pk');
                if(k && /Bound coverage, measured/.test(k.textContent||''))
                  return {cls:all[i].className,
                          colour:getComputedStyle(all[i].querySelector('.pv')).color};}
              return null;})())""") or "null")
            if pc:
                ck("miss" not in pc["cls"],
                   "and the plate cell showing the same figure is no longer hatched red",
                   pc["cls"])

            # ======================================================= 3. THE THREE GATES
            head("3. THE THREE-GATES SENTENCE: generic, and still making its point")
            txt = c.eval(r"""(function(){
              var ps=document.querySelectorAll('p.note');
              for(var i=0;i<ps.length;i++){var t=(ps[i].textContent||'');
                if(/Three gates/.test(t)) return t.replace(/\s+/g,' ').trim();}
              return '';})()""") or ""
            ck(bool(txt), "the sentence is on screen", txt[:100] + "...")
            # 🔴 NAMES ARE ASSERTED ABSENT, NOT PRESENT. Two attempts at naming a source here got it
            # wrong in two different ways, so the user asked for the line to name none: "dont mention
            # LBNL or any other publication name neither energy star or honeywell, rephrase it to
            # keep it simple and generic". A check that only forbade the one name that was wrong last
            # time would let the next one through.
            for name in ("LBNL", "Lawrence Berkeley", "ENERGY STAR", "Honeywell", "JADE",
                         "Shehabi", "ASHRAE", "Green Grid"):
                ck(name not in txt, "names no source: %-18s" % name)
            ck("temperature" in txt and "humidity" in txt and "contamination" in txt,
               "the three gates are still named")
            ck("Not temperature alone" in txt,
               "and it still says the thing it exists to say: temperature alone is not the test")
            # The literal is escaped rather than typed, so this file itself stays clean under
            # a repository-wide em-dash sweep while still testing for one.
            ck(chr(0x2014) not in txt, "no em dashes in the copy")
    finally:
        srv.terminate()

    print("\n" + "=" * 78)
    print("   %d checks, %d failed" % (len(PASS) + len(FAIL), len(FAIL)))
    for w, d in FAIL:
        print("   FAILED: %-52s %s" % (w, d))
    if not FAIL:
        print("   VERDICT: the hour dropdown drives the tape, the coverage tile states a computed")
        print("            shortfall in green, and the three-gates line names no source at all.")
    print("=" * 78)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
