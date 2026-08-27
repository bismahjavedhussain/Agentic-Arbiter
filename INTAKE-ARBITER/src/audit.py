# -*- coding: utf-8 -*-
"""AUDIT -- the whole tree, mechanically, in one command.

    python audit.py

Checks the classes of defect that have actually bitten this project, rather than reading the code
and hoping. Every check is repeatable, so it can be re-run after any change and before any claim.

WHAT IT CHECKS, AND WHICH REAL BUG EACH ONE EXISTS FOR
  1. DEAD CODE          functions defined and referenced nowhere. Three superseded helpers were
                        still sitting in the tree after score_config was rewritten.
  2. NaN-UNSAFE WRITERS every json.dump must pass allow_nan=False. `NaN` is legal Python JSON and
                        ILLEGAL standard JSON: the demo died on it with every Python-side check
                        passing, because json.load accepts what JSON.parse rejects.
  3. ROUNDED DECISIONS  arrays a decision is recomputed from must ship at full precision. Rounding
                        to 4 dp flipped decisions at exact gate boundaries -- twice in one day.
  4. DUPLICATE CONSTANTS the same physical constant defined in two modules will drift.
  5. RETIRED CONSTANTS  a constant removed FOR CAUSE must not reappear. agent.py replaced an
                        invented wet-bulb margin with a sourced dew-point maximum, and backtest.py
                        kept the invented one for another day -- so the five-year headline was
                        being produced by a number every document had already condemned.
  6. STALE PUBLISHED NUMBERS every headline figure quoted in PLAN.md / HANDOFF.md is re-read from
                        the JSON the code actually wrote. A figure that has drifted is a
                        hallucination with a paper trail, and this is the check that catches it.
  6a. STAGE 5 NUMBERS   the ACT stage's command rows must carry a real bound. All 37 of them shipped
                        `null` plus the literal word "nan" in their reason, because a `.get(key) or
                        default` covered for a key nothing ever wrote.
  6b. STAGE EVENTS      the reasoning tape's templates must contain no literal digit, and every digit
                        in the shipped text must trace to a payload value -- so "none of this is
                        hand-written" is a command rather than a claim.
  7. SELF-TESTS         every module's own suite still passes.
  8. CROSS-LANGUAGE     the browser agrees with Python on decisions, reasons, stage-event sentences
                        and the conformal quantile.
  9. API SPEND          the credit ledger is re-derived from saved meter readings, and the
                        submission documents are checked against it -- current figure present,
                        superseded figure absent.
 10. FRONT DOOR        every figure in the root README.md is re-derived from the emitted JSON and
                        matched as the FORMATTED STRING a reader sees. The failure figures are
                        registered next to the flattering ones so they cannot quietly rot away.
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
ROOT = os.path.dirname(IA)
DEMO = os.path.join(IA, "demo")

FAILS, WARNS, PASSES = [], [], []
PUBLISHED_COUNT = [0]      # set by check_published_numbers, read by check_front_door_figures


def ck(name, ok, detail="", warn=False):
    (PASSES if ok else (WARNS if warn else FAILS)).append((name, detail))
    print("   [%s] %-56s %s" % ("PASS" if ok else ("WARN" if warn else "FAIL"), name, detail))
    return ok


def jload(p):
    return json.load(open(p, encoding="utf-8"))


# ============================================================================
def check_dead_code():
    print("\n1. DEAD CODE")
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    defs, refs = {}, {}
    for f in files:
        tree = ast.parse(open(os.path.join(HERE, f), encoding="utf-8").read())
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.setdefault(n.name, []).append("%s:%d" % (f, n.lineno))
            elif isinstance(n, ast.Name):
                refs[n.id] = refs.get(n.id, 0) + 1
            elif isinstance(n, ast.Attribute):
                refs[n.attr] = refs.get(n.attr, 0) + 1
    extra = ""
    # EVERY file that can reference a src/ function has to be listed here, or a function used only
    # by a fixture generator gets reported as dead. Session D and F each added two.
    for p in ("index.html", "verify_browser_agent.js", "verify_browser_decision.js",
              "verify_browser_explanation.js", "verify_browser_ticker.js",
              "verify_browser_conformal.js", "gen_dp_cases.py", "gen_ticker_cases.py",
              "gen_conformal_cases.py"):
        fp = os.path.join(DEMO, p)
        if os.path.exists(fp):
            extra += open(fp, encoding="utf-8").read()
    for root, _, fs in os.walk(os.path.join(ROOT, "testing")):
        for f in fs:
            if f.endswith(".py"):
                try:
                    extra += open(os.path.join(root, f), encoding="utf-8").read()
                except Exception:
                    pass
    # FRAMEWORK-DISPATCHED METHODS ARE NOT DEAD CODE. `http.server` calls `do_GET` / `do_POST` /
    # `log_message` by name through its own dispatch table, so nothing in this tree references them
    # and a name-reference check cannot see the caller. Listed explicitly, one entry per contract,
    # rather than excluding the file: excluding a file hides everything else in it, and this check
    # has already earned its keep by finding four genuinely orphaned functions. The rule this
    # follows is check_nan_writers': a verification tool that cries wolf is worse than none.
    FRAMEWORK_DISPATCHED = {
        "do_GET", "do_POST", "do_HEAD", "log_message",   # http.server.BaseHTTPRequestHandler
    }
    dead = [(n, w) for n, w in sorted(defs.items())
            if refs.get(n, 0) == 0 and n not in extra and n not in FRAMEWORK_DISPATCHED]
    ck("no function is defined and referenced nowhere", not dead,
       "%d defs" % len(defs) if not dead else "; ".join("%s (%s)" % (n, w[0]) for n, w in dead))


def check_nan_writers():
    print("\n2. NaN-UNSAFE JSON WRITERS")
    bad = []
    for root in (HERE, DEMO):
        for f in sorted(os.listdir(root)):
            if not f.endswith(".py"):
                continue
            src = open(os.path.join(root, f), encoding="utf-8").read()
            for m in re.finditer(r"json\.dump\(", src):
                # Match parentheses across the WHOLE file, not a fixed window. A 500-char window
                # produced ten false failures here: `select_site.py`'s dump spans 2,415 characters,
                # so `allow_nan=False` sat outside the window and the check reported a guarded
                # call as unguarded. A verification tool that cries wolf is worse than none.
                depth, end = 0, None
                for i in range(m.start(), len(src)):
                    if src[i] == "(":
                        depth += 1
                    elif src[i] == ")":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                call = src[m.start():end + 1] if end is not None else src[m.start():]
                if "allow_nan=False" not in call:
                    line = src[:m.start()].count("\n") + 1
                    bad.append("%s:%d" % (f, line))
    ck("every json.dump passes allow_nan=False", not bad, "; ".join(bad) or "all guarded")

    print("\n2b. EMITTED JSON IS STRICT-VALID (what a browser demands)")
    bad2 = []
    for f in sorted(os.listdir(DEMO)):
        if f.endswith(".json"):
            try:
                json.loads(open(os.path.join(DEMO, f), encoding="utf-8").read(),
                           parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
            except ValueError as e:
                bad2.append("%s (%s)" % (f, e))
    ck("no NaN/Infinity in any emitted JSON", not bad2,
       "; ".join(bad2) or "%d files" % len([f for f in os.listdir(DEMO) if f.endswith(".json")]))


def check_decision_precision():
    """Decision-critical arrays must not be DISPLAY-ROUNDED on the way out.

    An earlier version of this check counted decimal places in the shipped values. That gave false
    failures: `temp_c` and `dewpoint_c` come from an ASOS record stored as 2-dp Celsius, so their
    full precision IS two decimals. Counting decimals cannot tell "rounded on write" from "the
    source only had two". So the check is now made at the SOURCE: no `round(` may be applied to a
    decision-critical array as it is written.

    The stronger guarantee lives elsewhere and is already proven: verify_browser_decision.js
    rebuilds every decision from these arrays and matches the Python agent across 20,160
    configurations -- both anchor settings and both bank placements, since restricting it to
    anchor == 'sensor' is what hid a 32 % disagreement. That is an end-to-end equality test, which no
    precision heuristic can beat.
    """
    print("\n3. DECISION-CRITICAL ARRAYS ARE NOT DISPLAY-ROUNDED ON WRITE")
    src = open(os.path.join(HERE, "agent.py"), encoding="utf-8").read()
    keys = ["temp_c", "dewpoint_c", "twb_c", "rise_c_", "rise_true_c_", "plume_margin_c_",
            "r_prime|", "rw_prime|", "rdp_prime|", "margin_dry|", "margin_wet|", "margin_dp|",
            "incumbent_src|", "incumbent_wet_src|", "incumbent_dp_src|"]
    bad = []
    for line in src.split("\n"):
        if "row[" not in line and '"temp_c"' not in line:
            continue
        if any(k in line for k in keys) and "round(" in line:
            bad.append(line.strip()[:70])
    # the cached rise table feeds the bound too
    if re.search(r'"rise": \[\[round\(', src):
        bad.append('rise_table cache writes rounded values')
    ck("no decision-critical array is rounded as it is written", not bad,
       "; ".join(bad) or "%d array families checked" % len(keys))
    t = jload(os.path.join(DEMO, "trace.json"))
    ds = t["cases"]["day_series"]["crossing"]
    missing = [k for k in ("temp_c", "dewpoint_c", "rise_c_longest", "plume_margin_c_longest",
                           "r_prime|3", "margin_dry|3", "margin_dp|3") if not ds.get(k)]
    ck("every array the browser rebuilds decisions from is present", not missing,
       "; ".join(missing) or "all present")


def check_duplicate_constants():
    """A constant defined in two modules is a drift risk. The defect is DISAGREEMENT, not
    duplication -- and centralising them would mean editing the committed site pipeline, whose
    output is the geometry every published number rests on. So the value is asserted equal instead,
    which catches drift the moment it appears without touching that pipeline.
    """
    print("\n4. CONSTANTS DEFINED IN MORE THAN ONE MODULE MUST AGREE")
    want = ["CALM_KT", "STEP_DEG", "AMB_REF", "SIGMA_DIR_DEG", "ALPHA", "SPEED_GRID_MS"]
    vals = {w: {} for w in want}
    for f in sorted(x for x in os.listdir(HERE) if x.endswith(".py")):
        src = open(os.path.join(HERE, f), encoding="utf-8").read()
        for w in want:
            m = re.search(r"^%s\s*=\s*(.+?)(?:\s+#.*)?$" % w, src, re.M)
            if m:
                vals[w][f] = m.group(1).strip()
    any_dup = False
    for w in want:
        d = vals[w]
        if len(d) < 2:
            continue
        any_dup = True
        uniq = set(d.values())
        ck("%-14s agrees across %d modules" % (w, len(d)), len(uniq) == 1,
           "%s  (%s)" % (" | ".join(sorted(uniq)), ", ".join(sorted(d))))
    if not any_dup:
        ck("no constant is duplicated at all", True, "checked %d" % len(want))


# ---- constants removed FOR CAUSE, which must not come back ---------------------------------
#
# THE BUG THIS CHECK EXISTS FOR, and it is a good one. `agent.py` replaced an invented wet-bulb
# margin with a sourced dew-point maximum. PLAN.md was updated. HANDOFF.md was updated. The demo
# was updated. And `backtest.py` KEPT THE INVENTED CONSTANT for another full day -- so the
# five-year headline ladder was still being produced by a number with no source while every
# document in the tree described the sourced one. No check in this file could see that, because
# "has this specific constant actually gone" was not a question anything asked. Now it is.
#
# The scope is the SHIPPED tree: INTAKE-ARBITER/src/*.py and INTAKE-ARBITER/demo/*.{js,html,json}.
RETIRED_CONSTANTS = [
    ("wetbulb_margin_c",
     "INVENTED 3.0 C offset from our own dry-bulb knob, no published source -> replaced by "
     "dewpoint_limit_c = 15 C, Green Grid WP#46 p.6"),
    ("THRESHOLD_C",
     "testing/run_e2e.py's hard-coded 33.0 C changeover -> superseded by the swept "
     "PLANT_ENVELOPE['limit_c']; run_e2e.py is not shipped"),
]


_COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/|<!--.*?-->", re.S)


def _uses_identifier_py(src, name):
    """Is `name` used as a CODE identifier in this Python source?

    AST-BASED ON PURPOSE, and the reason is a false positive this check produced on its first run.
    A substring scan flagged `agent.py`, whose module docstring says run_e2e.py "hard-codes
    THRESHOLD_C = 33.0, which is exactly the threshold in a costume the project forbids". That is
    PROSE DOCUMENTING THE RETIREMENT -- which methodology rule 6 requires to stay visible -- not a
    reintroduction. A checker that cannot tell code from a comment about code trains you to ignore
    it (gotcha #47).

    Comments never enter the AST at all, and a docstring is a single Constant whose value is the
    whole paragraph, so exact string equality never matches prose that merely contains the name.
    """
    hits = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Name) and n.id == name:
            hits.append(n.lineno)
        elif isinstance(n, ast.Attribute) and n.attr == name:
            hits.append(n.lineno)
        elif isinstance(n, ast.keyword) and n.arg == name:
            hits.append(getattr(n, "lineno", 0))
        elif isinstance(n, ast.arg) and n.arg == name:
            hits.append(n.lineno)
        # `cfg["retired_key"]` and `{"retired_key": ...}` -- EXACT equality, so a sentence
        # containing the name is not a match
        elif isinstance(n, ast.Constant) and n.value == name:
            hits.append(n.lineno)
    return sorted(set(hits))


def _uses_identifier_json(obj, name):
    """Exact key or exact string value, walked structurally rather than by regex."""
    if isinstance(obj, dict):
        return (name in obj) or any(_uses_identifier_json(v, name) for v in obj.values())
    if isinstance(obj, list):
        return any(_uses_identifier_json(v, name) for v in obj)
    return obj == name


def _selftest_retired_detector():
    """THE CHECKER GETS ITS OWN TEST, because on this project the checks have been wrong more
    often than the code. Both directions are asserted: prose must NOT trip it, code MUST."""
    prose = '"""run_e2e.py hard-codes THRESHOLD_C = 33.0, which is forbidden."""\nx = 1\n'
    comment = "# THRESHOLD_C was retired\nx = 1\n"
    real_assign = "THRESHOLD_C = 33.0\n"
    real_key = 'cfg = {"THRESHOLD_C": 33.0}\n'
    real_read = 'y = cfg["THRESHOLD_C"]\n'
    real_kw = "f(THRESHOLD_C=1)\n"
    cases = [(prose, False), (comment, False), (real_assign, True), (real_key, True),
             (real_read, True), (real_kw, True)]
    bad = [i for i, (src, want) in enumerate(cases)
           if bool(_uses_identifier_py(src, "THRESHOLD_C")) != want]
    return ck("the retired-constant detector passes its own 6-case test", not bad,
              "prose/comments ignored, assignments, dict keys, reads and kwargs caught"
              if not bad else "cases %s wrong" % bad)


def check_duplicate_element_ids():
    """NO id MAY APPEAR TWICE IN index.html, and this check exists because one did.

    The plume panel carried a second `<select id="c_site">`, left over from the layout that
    preceded the three-stage rebuild. Duplicate ids are not a validation nicety: `querySelector`
    returns the FIRST match, so `buildSitePicker()` filled the stage-1 picker and this one sat
    permanently EMPTY -- a "Data centre" dropdown with no options, under a heading, on every site.
    Nothing threw, nothing 404'd, every cross-language test passed, and it was visible only by
    looking at the page.

    Ids inside HTML comments are excluded, because the fix for the real one left an explanatory
    comment quoting the markup it removed.
    """
    print("\n2f. DUPLICATE ELEMENT IDS")
    src = open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    # Strip comments first, or the commented-out markup that documents a removal re-triggers it.
    stripped = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    ids = re.findall(r"""\sid=["']([^"']+)["']""", stripped)
    seen, dupes = set(), []
    for i in ids:
        if i in seen and i not in dupes:
            dupes.append(i)
        seen.add(i)
    ck("no element id is used twice", not dupes,
       "%d ids, all unique" % len(ids) if not dupes else "DUPLICATED: " + ", ".join(dupes))


def check_page_javascript_parses():
    """index.html's ONE inline script must actually parse.

    THE BUG THIS EXISTS FOR. A broken apostrophe escape -- `'...Ashburn's.'` -- was a SyntaxError,
    and a SyntaxError in the only script block means NOTHING runs: the page sat on "Loading saved
    data..." forever with no error in the console, no unhandled rejection, and every JSON file
    serving HTTP 200. Three probes found nothing because there was nothing running to probe.

    Exactly the same shape as `check_css_comments`, which exists because unbalanced CSS comment
    delimiters fed two paragraphs of English to the stylesheet and every screenshot still passed.
    The browser tests extract individual FUNCTIONS, so they cannot see a break between them.
    """
    # 2e, NOT 2d: `check_plume_fields` already prints 2d. Two sections sharing a label in one audit
    # report is precisely the small wrongness this file exists to refuse.
    print("\n2e. THE PAGE'S JAVASCRIPT PARSES")
    p = os.path.join(DEMO, "index.html")
    src = open(p, encoding="utf-8").read()
    i, j = src.rfind("<script>"), src.rfind("</script>")
    if i < 0 or j < i:
        ck("index.html has an inline script block", False, "none found")
        return
    tmp = os.path.join(DEMO, "_audit_syntax_check.js")
    open(tmp, "w", encoding="utf-8").write(src[i + 8:j])
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=120)
        detail = ""
        if r.returncode != 0:
            detail = " ".join((r.stderr or "").split())[:110]
        ck("index.html's inline script parses (%s chars)" % format(j - i - 8, ","),
           r.returncode == 0, detail)
    finally:
        os.remove(tmp)


def check_css_comments():
    """Balanced /* */ inside every <style> block, and no stray text between rules.

    THE BUG THIS EXISTS FOR. Successive edits to one explanatory CSS comment in index.html each
    appended a paragraph ending in `*/`, leaving THREE closers against one opener -- so two
    paragraphs of English sat in the stylesheet as if they were rules. Nothing visibly broke,
    because a CSS parser error-recovers by skipping to the next resync point, so every screenshot
    and every cross-language test still passed. An unbalanced comment is silent by construction,
    which is exactly why it needs a mechanical check.
    """
    print("\n2c. CSS COMMENTS ARE BALANCED")
    bad = []
    for f in sorted(os.listdir(DEMO)):
        if not f.endswith(".html"):
            continue
        src = open(os.path.join(DEMO, f), encoding="utf-8").read()
        for sm in re.finditer(r"<style[^>]*>(.*?)</style>", src, re.S):
            css = sm.group(1)
            base = src[:sm.start(1)].count("\n") + 1
            depth = 0
            i = 0
            while i < len(css) - 1:
                if css[i:i + 2] == "/*":
                    depth += 1
                    i += 2
                    continue
                if css[i:i + 2] == "*/":
                    depth -= 1
                    if depth < 0:
                        bad.append("%s:%d unmatched */" % (f, base + css[:i].count("\n")))
                        depth = 0
                    i += 2
                    continue
                i += 1
            if depth:
                bad.append("%s: %d unclosed /*" % (f, depth))
    ck("every <style> block has balanced /* */", not bad, "; ".join(bad[:4]) or "balanced")


def check_plume_fields():
    """Every shipped plume field must reproduce its own audited rise at the intake disc.

    WHY THIS IS THE RIGHT CHECK. `export_plume_fields.py` writes the real solver output so the
    360-degree view renders physics rather than a drawn cone -- but the file is CROPPED and
    QUANTISED to one byte per cell to be shippable, and it is written by a separate slow step that
    is not part of run_all. So the risk is a field that looks plausible and no longer matches the
    number `check_published_numbers` re-reads from the direction table.

    This averages the field over the intake disc using the SOLVER'S OWN rule -- excluding obstacle
    cells, as `intake_temperature(exclude_obstacles=True)` does -- and requires agreement with the
    published critical rise. Including obstacle cells instead loosens agreement from ~0.5 % to
    ~3 %, which is how the rule was identified rather than assumed.
    """
    print("\n2d. SHIPPED PLUME FIELDS REPRODUCE THEIR AUDITED RISE")
    import numpy as np
    files = sorted(f for f in os.listdir(DEMO) if f.startswith("plume_field_"))
    if not files:
        ck("plume fields present", False, "none found -- run export_plume_fields.py --all", warn=True)
        return
    for f in files:
        d = jload(os.path.join(DEMO, f))
        q = d["quantisation"]["scale_c_per_byte"]
        dx, R, C = d["dx_m"], d["rows"], d["cols"]
        ox, oy = d["origin_m"]
        ix, iy = d["intake_m"]
        rad = d["intake_radius_m"]
        b = str(d["critical_bearing_deg"])
        if b not in d["fields"]:
            ck("%s carries a field at its critical bearing %s" % (f, b), False,
               "bearing missing -- STEP_DEG must match direction_table's 5 deg")
            continue
        fld = np.array(d["fields"][b], dtype=float).reshape(R, C) * q
        obs = np.array(d["obstacle_mask"], dtype=bool).reshape(R, C)
        jj, ii = np.meshgrid(np.arange(C), np.arange(R))
        x = ox + (jj + 0.5) * dx
        y = oy + (ii + 0.5) * dx
        msk = (((x - ix) ** 2 + (y - iy) ** 2) <= rad * rad) & ~obs
        got = float(fld[msk].mean())
        want = d["critical_rise_c"]
        rel = abs(got - want) / max(abs(want), 1e-9)
        # ⚠ A RELATIVE TEST ALONE IS UNDEFINED WHEN THE WHOLE RISE IS BELOW ONE BYTE, and one real
        #    site is: IL_way_1219083554's audited critical rise is 0.00005 C -- 50 microkelvin --
        #    against a display resolution of ~0.0035 C per byte. It quantises to zero, so `rel` is
        #    100 % forever and no amount of correct physics can move it.
        #    So the field must agree to 2 % OR to within half a quantisation step, which is the
        #    finest difference the file can express at all. THIS IS NOT #65's WIDENED TOLERANCE:
        #    half a byte is 0.55 % of CA_way_209087373's rise and 0.25 % of Ashburn's, so it rescues
        #    nothing that has a rise to get wrong -- only fields whose entire signal is smaller than
        #    the pixel it is drawn with. Both figures are printed either way.
        near = abs(got - want) <= 0.5 * q
        ck("%-38s field %.5f vs audited %.5f C" % (d["metro"] + " " + b + " deg", got, want),
           rel < 0.02 or near,
           "%.2f %% apart, %.2f byte(s), %d disc cells"
           % (100 * rel, abs(got - want) / max(q, 1e-12), int(msk.sum())))


def check_retired_constants():
    print("\n5. RETIRED CONSTANTS -- removed for cause, must not reappear in the shipped tree")
    _selftest_retired_detector()
    me = os.path.basename(__file__)
    py = [os.path.join(HERE, f) for f in sorted(os.listdir(HERE))
          if f.endswith(".py") and f != me]
    other = [os.path.join(DEMO, f) for f in sorted(os.listdir(DEMO))
             if f.endswith((".js", ".html", ".json"))]
    for name, why in RETIRED_CONSTANTS:
        hits = []
        for p in py:
            for ln in _uses_identifier_py(open(p, encoding="utf-8").read(), name):
                hits.append("%s:%d" % (os.path.relpath(p, IA), ln))
        for p in other:
            if p.endswith(".json"):
                if _uses_identifier_json(jload(p), name):
                    hits.append(os.path.relpath(p, IA))
            else:
                # No JS parser here, so comments are STRIPPED and then the bare identifier is
                # matched on a word boundary. Stated limitation: a retired name inside a JS string
                # literal would be reported.
                stripped = _COMMENT_RE.sub("", open(p, encoding="utf-8").read())
                if re.search(r"\b%s\b" % re.escape(name), stripped):
                    hits.append(os.path.relpath(p, IA))
        ck("retired `%s` absent from src/ and demo/" % name, not hits,
           ("STILL PRESENT in %s" % ", ".join(hits[:4])) if hits else why[:60])
    ck("%d files scanned for retired constants" % (len(py) + len(other)),
       len(py) + len(other) > 20, "%d py, %d js/html/json" % (len(py), len(other)))


# ---- the registry: every headline number, and where the code actually keeps it -------------
def check_act_stage():
    """STAGE 5 MUST ACTUALLY CARRY ITS NUMBERS.

    THE BUG THIS EXISTS FOR. `run_cases` read the per-hour bound out of the day-series with
    `row.get("bound_c|longest|sensor|anchored|0.50|3") or [None] * H`. Nothing in the tree ever
    wrote that key -- `_day_series` is not built until after the sweep that computes the bound has
    finished -- so the `or` default fired every time, `bms_commands` formatted `"%.3f" % nan` into
    the reason text, and `json_safe()` turned the field beside it into a valid `null`.

    Result: 37 of 37 shipped command rows said "upper bound on intake nan C" and carried
    `bound_c: null` -- 100 % of the ACT stage's output, while the project's own pitch said each row
    "carries its own numbers". Nothing caught it. `check_nan_writers` looks for `allow_nan`, and the
    file was valid JSON. `check_published_numbers` re-reads 61 figures, none of them from act_log.

    So this check does three things a reader would do:
      a. every row's bound is a finite number, and no reason string contains "nan"/"None"/"null";
      b. the bound RECONSTRUCTS from the day-series inputs the browser is given, to full
         precision -- an independent path, since the sweep and `_day_series` are separate code
         (gotcha #46: two implementations' OUTPUTS compared is the only test that sees this class);
      c. the reason text quotes the same bound the row carries, so prose and field cannot drift.
    """
    print("\n6a. STAGE 5 (ACT) -- command rows carry real numbers")
    t = jload(os.path.join(DEMO, "trace.json"))
    al = t["cases"]["act_log"]
    ds_all = t["cases"]["day_series"]

    rows = [(k, c) for k, blk in al.items() for c in blk["commands"]]
    bad_val = [(k, c["hour"]) for k, c in rows
               if c["bound_c"] is None or not isinstance(c["bound_c"], (int, float))]
    ck("act_log: %d rows, every bound_c a real number" % len(rows), not bad_val,
       "" if not bad_val else "%d row(s) with no bound, first %s" % (len(bad_val), bad_val[0]))

    words = ("nan", "None", "null", "inf")
    bad_txt = [(k, c["hour"], w) for k, c in rows for w in words if w in c["reason"]]
    ck("act_log: no reason text states a non-number", not bad_txt,
       "" if not bad_txt else "%d occurrence(s), first %s" % (len(bad_txt), bad_txt[0]))

    # (b) rebuild the bound the way the BROWSER does, from the shipped inputs only.
    worst = (None, 0.0)
    n_checked = 0
    for k, blk in al.items():
        cf = blk["configuration"]
        case = k.split("@")[0]
        ds = ds_all.get(case)
        if ds is None:
            continue
        s = 1.0 - cf["forecast_skill"]
        N, bank = cf["notice_h"], cf["bank_mode"]
        rp = ds["r_prime|%d" % N]
        md = ds["margin_dry|%d" % N]
        rise = ds["rise_c_" + bank]
        pm = ds.get("plume_margin_c_" + bank) or [0.0] * len(rise)
        # anchor "sensor" removes the FortyGuard day level with one local reading, so off = 0
        off = 0.0 if cf["anchor"] == "sensor" else None
        if off is None:
            continue
        for c in blk["commands"]:
            i = c["index"]
            rebuilt = ds["temp_c"][i] - off - s * rp[i] + s * md[i] + rise[i] + pm[i]
            d = abs(rebuilt - c["bound_c"])
            n_checked += 1
            if d > worst[1]:
                worst = ("%s h%s: act_log %.6f vs rebuilt %.6f" % (k, c["hour"], c["bound_c"],
                                                                   rebuilt), d)
    # This is an IDENTITY, not an approximation: both sides sum the same five shipped float64
    # arrays. They differ only in the order the additions are associated, so the bound is 1e-9 --
    # about six orders of magnitude above float64 noise and six below anything a decision notices.
    # It used to be 5e-5, because act_log rounded `bound_c` to 4 dp; the rounding was removed
    # instead of the tolerance being justified (gotcha #63).
    ck("act_log: bound rebuilds from the shipped inputs (%d rows, max |d| %.2e C)"
       % (n_checked, worst[1]), n_checked > 0 and worst[1] <= 1e-9, worst[0] or "")

    # (c) the number in the prose must be the number in the field, at the precision it is printed.
    # An EXACT string identity -- no tolerance, because there is nothing here to tolerate.
    drift = []
    for k, c in rows:
        m = re.search(r"upper bound on intake (-?\d+\.\d+) C", c["reason"])
        if m is None:
            if not c["refused"]:
                drift.append((k, c["hour"], "no bound quoted in reason"))
            continue
        if m.group(1) != "%.3f" % c["bound_c"]:
            drift.append((k, c["hour"], "prose %s vs field %.3f" % (m.group(1), c["bound_c"])))
    ck("act_log: reason prose quotes the row's own bound", not drift,
       "" if not drift else "%d drift(s), first %s" % (len(drift), drift[0]))


def check_national_registry():
    """THE NATIONAL BUILD'S OWN FILES, WHICH NOTHING CHECKED AT ALL UNTIL NOW.

    Six files and ~1,600 real buildings were produced across two sessions, they feed the map on the
    front page, and `audit.py` had ZERO checks touching any of them. Every guard that exists lives
    inside the generator that wrote the file -- so a generator bug and its own verification failed
    together, which is the arrangement this whole module exists to replace.

    WHAT IS WORTH ASSERTING, and why each one is an EXACT identity rather than a tolerance:

      1. THE COUNTS PARTITION. Every one of these files publishes a headline count and a body, and
         each pair must close exactly. This is not decoration: `discover_dc_clusters.py` silently
         lost one real standalone data centre to a key collision (127+58+236 = 421 counted, 420
         written) and the arithmetic is what found it. It gained a tripwire in the generator; this
         is the same arithmetic re-run by something that did not write the file.
      2. REFERENTIAL INTEGRITY. A group cites registry entries, a verdict cites a group, a group
         cites buildings. A dangling id means two files disagree about what exists.
      3. NO FABRICATED SITE. Every point on the map must resolve to a real OSM element id in the
         registry -- "never claim a data centre that does not exist" expressed mechanically.
      4. NO NON-US SITE LEAKED THROUGH. 12 cells and 25 tagged ways were confirmed foreign
         (Toronto, Markham, and one Mexican cell) and excluded WITH their evidence. A national build
         scoped to the US may not show them, and the sharper form of the same rule is that it may
         not claim a real foreign data centre is an American one.
      5. ONE METRO, ONE DOT. Chicago's committed pair straddles two ~11 km discovery cells, so the
         first version of the exporter emitted "fully_built" twice for one site.
    """
    print("\n6g. THE NATIONAL REGISTRY -- counts close, ids resolve, nothing invented")
    GEOM = os.path.join(IA, "data", "geometry")
    # Read from the gate file rather than restated, so this cannot drift from the value that
    # actually produced the verdicts.
    MIN_GAP_AUDIT = jload(os.path.join(GEOM, "national_gate_verdicts.json"))["min_gap_m"]

    def g(name):
        p = os.path.join(GEOM, name)
        return jload(p) if os.path.exists(p) else None

    # LOADED UP HERE, not in section 6 where it used to be: the map-point checks in sections 3-4 now
    # resolve against FACILITIES rather than discovery-grid entries, so they need it before those
    # sections run. Python's closure scoping made that an obvious failure -- `NameError: cannot
    # access free variable 'F'` -- rather than a silent wrong answer, which is the good outcome.
    nr = g("national_registry.json")
    F = (nr or {}).get("facilities") or {}
    reg, grp = g("dc_clusters.json"), g("national_building_groups.json")
    ver, cen = g("national_gate_verdicts.json"), g("national_building_centres.json")
    geo = g("national_geometry.json")
    uni = jload(os.path.join(DEMO, "unified_sites.json")) \
        if os.path.exists(os.path.join(DEMO, "unified_sites.json")) else None
    if not all((reg, grp, ver, cen, uni)):
        missing = [n for n, v in (("dc_clusters", reg), ("building_groups", grp),
                                  ("gate_verdicts", ver), ("building_centres", cen),
                                  ("unified_sites", uni)) if not v]
        ck("the national registry files exist", False, "missing: %s" % ", ".join(missing))
        return

    # ---- 1. THE COUNTS PARTITION ----------------------------------------------------------
    cl = reg["clusters"]
    ck("dc_clusters: cluster + pair + single == the entries actually written",
       reg["n_clusters"] + reg["n_pairs"] + reg["n_singles"] == len(cl),
       "%d + %d + %d == %d" % (reg["n_clusters"], reg["n_pairs"], reg["n_singles"], len(cl)))
    ck("dc_clusters: every entry's n_tagged equals its own osm_ids length",
       all(e["n_tagged"] == len(e["osm_ids"]) for e in cl.values()),
       "%d entries, %d tagged buildings"
       % (len(cl), sum(e["n_tagged"] for e in cl.values())))

    groups = grp["groups"]
    ck("building_groups: isolated + pairing candidates == the groups written",
       grp["n_isolated"] + grp["n_pairing_candidates"] == len(groups),
       "%d + %d == %d" % (grp["n_isolated"], grp["n_pairing_candidates"], len(groups)))
    ck("building_groups: the members partition the building count exactly",
       sum(len(v["members"]) for v in groups.values()) == grp["n_buildings"],
       "%d members == %d buildings"
       % (sum(len(v["members"]) for v in groups.values()), grp["n_buildings"]))

    vd = ver["verdicts"]
    nb = ver.get("n_no_building_footprint", 0)
    ck("gate_verdicts: every outcome accounted for, none double-counted",
       ver["n_clear"] + ver["n_too_close"] + ver["n_missing_geometry"] + nb
       == ver["n_groups"] == len(vd),
       "%d clear + %d too_close + %d missing + %d no-building == %d == %d"
       % (ver["n_clear"], ver["n_too_close"], ver["n_missing_geometry"], nb,
          ver["n_groups"], len(vd)))
    ck("gate_verdicts: every verdict is a declared outcome",
       set(v["verdict"] for v in vd.values())
       <= {"clear", "too_close", "geometry_missing", "no_building_footprint"},
       "verdicts seen: %s" % ", ".join(sorted(set(v["verdict"] for v in vd.values()))))
    # 🔴 THE GATE MUST NEVER DECIDE A FACADE GAP ON A PROPERTY LINE. `telecom=data_center` is
    # applied to landuse polygons as well as halls, and before `is_building_footprint` filtered
    # them out, 18 of 243 verdicts were measured between parcel edges -- EIGHT of them reported
    # CLEAR, i.e. a fence-line gap read as a safe facade gap. Re-derived here from the geometry's
    # own tags rather than trusted from the gate's own report.
    if geo:
        gr = geo["rings"]
        parcel_decided = [k for k, v in vd.items() if (v.get("best_pair") or [])
                          and any("building" not in ((gr.get(m) or {}).get("tags") or {})
                                  for m in v["best_pair"])]
        ck("gate_verdicts: no verdict is decided on a land parcel's edge",
           not parcel_decided,
           "%d verdict(s) on real building facades, %d parcel way(s) excluded"
           % (len([v for v in vd.values() if v.get("best_pair")]),
              ver.get("n_parcel_ways_excluded", 0))
           if not parcel_decided else "decided on a parcel: %s" % parcel_decided[:3])

    ck("unified_sites: the status counts partition the sites shown",
       sum(uni["counts"].values()) == uni["n_sites"] == len(uni["sites"]),
       "%d == %d == %d" % (sum(uni["counts"].values()), uni["n_sites"], len(uni["sites"])))

    ck("building_centres and geometry resolved everything they asked for",
       cen["n_requested"] == cen["n_resolved"] and not cen["missing_ids"]
       and (geo is None or (geo["n_requested"] == geo["n_resolved"] and not geo["missing_ids"])),
       "centres %d/%d, rings %s" % (cen["n_resolved"], cen["n_requested"],
                                    "%d/%d" % (geo["n_resolved"], geo["n_requested"]) if geo
                                    else "not fetched"))

    # ---- 2. REFERENTIAL INTEGRITY ---------------------------------------------------------
    all_osm = set()
    for e in cl.values():
        all_osm |= set(e["osm_ids"])
    ck("every grouped building is a real registry building",
       all(m in all_osm for v in groups.values() for m in v["members"]),
       "%d grouped ids all present in the %d-id registry"
       % (sum(len(v["members"]) for v in groups.values()), len(all_osm)))
    ck("every grouped building has its own fetched coordinate",
       all(m in cen["centres"] for v in groups.values() for m in v["members"]),
       "no building is in a group without a measured position")
    ck("every gate verdict names a group that exists",
       all(k in groups for k in vd),
       "%d verdicts, all resolving" % len(vd))
    ck("every gated group really is a pairing candidate, not an isolated one",
       all(groups[k]["kind"] != "isolated" for k in vd if k in groups),
       "the 60 m facade gate is only ever applied where a real neighbour exists")

    # ---- 3 & 4. NOTHING INVENTED, NOTHING FOREIGN ----------------------------------------
    entry_keys = set(cl)
    nonmetro = [s for s in uni["sites"] if not s.get("metro_key")]
    # 🔴 THE MAP'S UNIT CHANGED, AND THESE TWO CHECKS CAUGHT IT BY FAILING.
    # `unified_sites.json` used to be keyed by DISCOVERY-GRID ENTRY (`VA_390_-775`); it is now keyed
    # by FACILITY (`IA_way_1318322780`), so that a dot is one real data centre rather than an ~11 km
    # cell that could hold 81 buildings. Both assertions below were written against the old unit and
    # were measuring the wrong thing the moment the exporter changed -- which is the correct
    # behaviour for a check whose subject moves, and better than silently continuing to pass.
    ck("every national map point is a real FACILITY in the registry",
       all(s["key"] in F for s in nonmetro),
       "%d national points, all resolving to national_registry facility keys" % len(nonmetro))
    # ⚠ THE FIRST VERSION OF THIS CHECK PASSED VACUOUSLY, and was caught before it shipped.
    # It intersected `excluded_non_us[*].key` against the map's keys -- but those records carry only
    # `centre`, `country`, `n_tagged`, `sample_names`, `operators`. There is no `key` field, so the
    # set was always empty, an empty intersection is always empty, and the check could never fail.
    # Exactly the "a check that cannot fail is not a check" trap, one section after two negative
    # controls were added to 6f for the same reason. Rewritten to match on the thing these records
    # actually carry: the COORDINATE, looked up in the Nominatim country cache that made the
    # exclusion decision in the first place.
    sbc = g("state_by_coord.json") or {}
    ckey = lambda c: "%.4f,%.4f" % (c[0], c[1])                          # noqa: E731
    # RESOLVED THROUGH THE FACILITY'S OWN SOURCE ENTRIES, not through its centroid.
    # A facility's centre is the MEAN of its buildings' coordinates; the Nominatim country cache is
    # keyed by the DISCOVERY CELL centroid that was actually geocoded. Those are different points,
    # so looking a facility centre up in that cache found only 272 of 633 -- not because 361
    # facilities are foreign, but because their centroid was never the thing geocoded. Every
    # facility records the cell(s) it came from, and those ARE in the cache, so the country question
    # is answered on the coordinate that was really asked about.
    def _country_of(fac):
        for ek in fac.get("source_entries") or []:
            e = cl.get(ek)
            if e and ckey(e["centre"]) in sbc:
                return sbc[ckey(e["centre"])].get("country")
        return None
    countries = {s["key"]: _country_of(F[s["key"]]) for s in nonmetro if s["key"] in F}
    resolved = [k for k, c in countries.items() if c]
    foreign_shown = [k for k, c in countries.items() if c and c != "us"]
    ck("every national map point geocoded to the UNITED STATES",
       not foreign_shown and len(resolved) == len(nonmetro),
       "%d of %d facilities resolved via their own source cell, %d foreign"
       % (len(resolved), len(nonmetro), len(foreign_shown)))
    # THE NEGATIVE CONTROL for the line above: the cache must actually hold foreign entries, or
    # "none of them are on the map" is a statement about an empty set again.
    n_foreign_cached = sum(1 for v in sbc.values() if v.get("country") != "us")
    ck("the country cache really does hold foreign locations to exclude",
       n_foreign_cached > 0 and len(reg.get("excluded_non_us") or []) > 0,
       "%d foreign coordinates cached, %d cells excluded with their evidence"
       % (n_foreign_cached, len(reg.get("excluded_non_us") or [])))
    ck("every map point carries a real coordinate",
       all(isinstance(s.get("centre"), list) and len(s["centre"]) == 2
           and -180 <= s["centre"][1] <= -60 and 18 <= s["centre"][0] <= 72
           for s in uni["sites"]),
       "all %d centres inside the North American window" % len(uni["sites"]))

    # ---- 5. ONE METRO, ONE DOT -----------------------------------------------------------
    mk = [s["metro_key"] for s in uni["sites"] if s.get("metro_key")]
    ck("each hand-built metro appears exactly once on the map",
       len(mk) == len(set(mk)),
       "%d metro dots: %s" % (len(mk), ", ".join(sorted(mk))))

    # ---- 6. THE FACILITY REGISTRY -- the unit the agent will actually run on -------------
    if not nr:
        ck("national_registry.json exists", False, "run build_national_registry.py")
        return
    ck("registry: the kind counts partition the facilities",
       sum(nr["counts"].values()) == nr["n_facilities"] == len(F),
       "%s == %d" % (" + ".join("%d" % v for v in nr["counts"].values()), len(F)))
    ck("registry: the facilities partition every tagged building exactly",
       sum(f["n_buildings"] for f in F.values()) == nr["n_buildings"] == grp["n_buildings"],
       "%d buildings across %d facilities"
       % (sum(f["n_buildings"] for f in F.values()), len(F)))

    # 🔴 THE STRONGEST CHECK IN THIS SECTION. A "standalone" facility is one with no tagged data
    # centre inside the solver's validated range -- if the union-find that produced the components
    # were wrong in EITHER direction, this is where it shows, because the distance is re-measured
    # here from the building coordinates rather than trusted from the grouping step. Gotcha #150
    # is exactly this failure: two Georgia data centres 280 m apart labelled isolated.
    rng = nr["solver_validated_range_m"]
    viol = [(k, f["plume"]["nearest_other_tagged_dc_m"]) for k, f in F.items()
            if f["kind"] == "standalone"
            and (f["plume"]["nearest_other_tagged_dc_m"] or 1e9) < rng]
    ck("registry: no standalone facility has a neighbour inside the validated range",
       not viol, "%d standalone, closest neighbour %.0f m against a %.0f m range"
       % (nr["counts"].get("standalone", 0),
          min((f["plume"]["nearest_other_tagged_dc_m"] for f in F.values()
               if f["kind"] == "standalone" and f["plume"]["nearest_other_tagged_dc_m"]),
              default=-1), rng)
       if not viol else "INSIDE the range: %s" % viol[:3])

    ck("registry: only paired_clear facilities model a plume",
       all((f["plume"]["modelled"] is True) == (f["kind"] == "paired_clear")
           for f in F.values()),
       "%d paired_clear model it, nothing else claims to" % nr["counts"].get("paired_clear", 0))
    ck("registry: every paired_clear facility really clears the %.0f m floor" % MIN_GAP_AUDIT,
       all(f["plume"]["facade_gap_m"] is not None
           and f["plume"]["facade_gap_m"] >= MIN_GAP_AUDIT
           for f in F.values() if f["kind"] == "paired_clear"),
       "tightest clear gap %.1f m" % min((f["plume"]["facade_gap_m"] for f in F.values()
                                          if f["kind"] == "paired_clear"), default=-1))
    ck("registry: every advisory facility is genuinely inside the floor",
       all(f["plume"]["facade_gap_m"] is not None
           and f["plume"]["facade_gap_m"] < MIN_GAP_AUDIT
           for f in F.values() if f["kind"] == "paired_advisory"),
       "%d advisory, widest gap %.1f m" % (nr["counts"].get("paired_advisory", 0),
                                           max((f["plume"]["facade_gap_m"] for f in F.values()
                                                if f["kind"] == "paired_advisory"), default=-1)))

    # THE WORDING IS PART OF THE CORRECTNESS. NATIONAL-BUILD-PLAN section 0.2 researched and
    # REJECTED "assume zero past a cutoff" as biased in the unsafe direction -- worse than the #49
    # invented-constant scar, not milder. The first version of build_national_registry.py shipped
    # that exact phrasing ("the plume term is zero by geometry"). This is the mechanical guard that
    # it cannot return, on every facility rather than on a sample.
    zero_claims = [k for k, f in F.items() if f["kind"] == "standalone"
                   and "NOT a claim that the effect is zero" not in f["plume"]["reason"]]
    ck("registry: no standalone facility CLAIMS zero recirculation",
       not zero_claims,
       "all %d standalone reasons say NOT MODELLED and disclaim zero"
       % nr["counts"].get("standalone", 0)
       if not zero_claims else "%d claim zero: %s" % (len(zero_claims), zero_claims[:3]))
    ck("registry: every advisory states the bound may be OPTIMISTIC",
       all("optimistic" in f["plume"]["reason"] for f in F.values()
           if f["kind"] == "paired_advisory"),
       "the direction of the risk is named, not just its existence")
    ck("registry: every standalone reason publishes its measured distance",
       all(("%.0f m" % f["plume"]["nearest_other_tagged_dc_m"]) in f["plume"]["reason"]
           for f in F.values()
           if f["kind"] == "standalone" and f["plume"]["nearest_other_tagged_dc_m"]),
       "a reader can tell 612 m from 373 km without leaving the sentence")

    ck("registry: every facility has its own measured timezone and state",
       all(f["tz"] and f["state"] for f in F.values()),
       "%d timezones, %d states, none guessed from a bbox"
       % (len({f["tz"] for f in F.values()}), len({f["state"] for f in F.values()})))
    # BELOW MODEL SCALE. OSM's `telecom=data_center` tag covers a hyperscale hall and a street
    # cabinet equally; the smallest tagged "data centre" nationally has a 4.7 m longest wall. The
    # floor is not a chosen number -- it is `build_site.BANK_DEPTH_M`, the depth of the condenser
    # bank the solver places on a facade, so a shorter wall cannot host the modelled plant at all.
    # Asserted against build_site's own constant rather than a literal, so the two cannot drift.
    from build_site import BANK_DEPTH_M                                  # noqa: PLC0415
    bms = {k: f for k, f in F.items() if f["kind"] == "below_model_scale"}
    ck("registry: the scale floor IS build_site's own bank depth, not a new constant",
       all(f["model_scale_floor_m"] == BANK_DEPTH_M for f in F.values()),
       "floor %.1f m == BANK_DEPTH_M" % BANK_DEPTH_M)
    ck("registry: every below-scale facility really is under the floor",
       all(f["longest_facade_m"] is not None and f["longest_facade_m"] < BANK_DEPTH_M
           for f in bms.values()),
       "%d below scale, longest wall among them %.1f m"
       % (len(bms), max((f["longest_facade_m"] for f in bms.values()), default=-1)))
    ck("registry: every facility ABOVE the floor is classified as something runnable",
       all(f["kind"] != "below_model_scale" for f in F.values()
           if f["longest_facade_m"] is not None and f["longest_facade_m"] >= BANK_DEPTH_M),
       "the floor is applied in one direction only, never as a general exclusion")
    ck("registry: no below-scale facility claims a modelled plume or hides its measurement",
       all(f["plume"]["modelled"] is False
           and ("%.1f m" % f["longest_facade_m"]) in f["plume"]["reason"]
           and "building is real and is shown" in f["plume"]["reason"]
           for f in bms.values()),
       "each publishes its own measured wall and refuses the CLAIM, not the building")

    # ---- 7. THE REGISTRY LOADER, and the one hole in it that would overwrite the reference site --
    # `metro_key()` resolving a bad value to the DEFAULT metro is not a cosmetic problem: the
    # default metro owns the UNSUFFIXED artefact filenames, which are exactly the ones the 77
    # published numbers are read from. A driver looping over 639 facilities with one unset shell
    # variable would rebuild Ashburn and overwrite them. Unset must default; set-but-empty must not.
    import metros as _M                                                  # noqa: PLC0415
    _saved = os.environ.get("METRO")
    try:
        cases, bad = [], []
        for val, want in ((None, _M.DEFAULT_METRO), ("", "RAISE"), ("   ", "RAISE"),
                          ("ashburn", "ashburn"), ("ASHBURN", "ashburn"), ("ashbrun", "RAISE"),
                          ("no_such_facility", "RAISE")):
            if val is None:
                os.environ.pop("METRO", None)
            else:
                os.environ["METRO"] = val
            try:
                got = _M.metro_key()
            except SystemExit:
                got = "RAISE"
            cases.append((val, got, want))
            if got != want:
                bad.append("%r -> %r, wanted %r" % (val, got, want))
        ck("metro_key: unset defaults, but a bad or EMPTY value refuses",
           not bad, "%d cases, incl. METRO='' refusing rather than rebuilding %r"
           % (len(cases), _M.DEFAULT_METRO) if not bad else "; ".join(bad))
        # And a real facility key must resolve, or the national path is unreachable.
        any_key = sorted(F)[0]
        os.environ["METRO"] = any_key
        ck("metro_key: a national facility key resolves to itself",
           _M.metro_key() == any_key, "%s" % any_key)
        ck("metro: a national facility carries its own measured tz and state, station absent",
           (lambda m: m.get("national") is True and m["tz"] and m["state"]
            and m["station"] is None)(_M.metro(any_key)),
           "station is None until S5 assigns one on measured completeness")
    finally:
        if _saved is None:
            os.environ.pop("METRO", None)
        else:
            os.environ["METRO"] = _saved

    # BOUNDARY-ONLY: a real site whose OSM record is a land parcel, with no building outline.
    bo = {k: f for k, f in F.items() if f["kind"] == "boundary_only"}
    ck("registry: every boundary-only facility genuinely has no building footprint",
       all(f["n_building_footprints"] == 0 and f["n_parcel_ways"] >= 1 for f in bo.values()),
       "%d boundary-only, %d parcel way(s) between them"
       % (len(bo), sum(f["n_parcel_ways"] for f in bo.values())))
    ck("registry: no boundary-only facility publishes a facade, a plume or a figure",
       all(f["plume"]["modelled"] is False
           and "no hours or dollar figure are published" in f["plume"]["reason"]
           and "not the data centre" in f["plume"]["reason"] for f in bo.values()),
       "each says the MAP is missing a building outline, not that the site is absent")
    ck("registry: a facility with any real building is never boundary-only",
       all(f["kind"] != "boundary_only" for f in F.values()
           if f["n_building_footprints"] >= 1),
       "the parcel test is applied only where there is nothing else to measure")
    # AND THE ONE THAT CAUGHT THREE BUGS: pairing decisions must count BUILDINGS, not tagged ways.
    # A facility with one hall and two land parcels has three members and one facade -- it was
    # classified `paired_advisory` (an advisory about a gap it cannot have) and separately flagged
    # `merged_into_one_structure` with a null gap.
    ck("registry: no single-building facility is treated as a pair",
       all(f["kind"] in ("standalone", "below_model_scale", "boundary_only")
           for f in F.values() if f["n_building_footprints"] <= 1),
       "%d facility(ies) with <=1 building, none of them classified as paired"
       % len([f for f in F.values() if f["n_building_footprints"] <= 1]))

    merged = [f for f in F.values() if f["plume"]["merged_into_one_structure"]]
    ck("registry: a merged facility is exactly two BUILDINGS inside the merge distance",
       all(f["n_building_footprints"] == 2 and f["plume"]["facade_gap_m"] is not None
           and f["plume"]["facade_gap_m"] < nr["merge_gap_m"]
           for f in merged),
       "%d merged, widest merged gap %.2f m against a %.1f m rule"
       % (len(merged), max((f["plume"]["facade_gap_m"] for f in merged), default=-1),
          nr["merge_gap_m"]))


def _unexplained_agreements(rows):
    """(n_distinct_decisions, [[site keys], ...]) for every group of sites that agree on the
    numbers WITHOUT agreeing on the station that produced them.

    `rows` is {key: {"gain":…, "all_mech":…, "station":…}}. Two sites sharing a station may share
    an answer -- that is Dulles/Ashburn by design, and any two standalone facilities on one ASOS
    record. Two sites on DIFFERENT stations may not: that is one site wearing the other's numbers.
    """
    by_decision = {}
    for k, v in rows.items():
        key = (round(float(v["gain"]), 6), round(float(v["all_mech"]), 6))
        by_decision.setdefault(key, []).append(k)
    bad = [sorted(ks) for ks in by_decision.values()
           if len(ks) > 1 and len(set(rows[k]["station"] for k in ks)) > 1]
    return len(by_decision), bad


def _selftest_agreement_rule():
    """The rule must FIRE on the defect it exists for and STAY QUIET on the coincidence that is
    real. Both cases, every run, because this is the one assertion in 6c permissive enough to pass
    by accident."""
    caught, _ = None, None
    # (1) THE DEFECT: gotcha #132's shape -- two sites, different stations, identical output.
    n, bad = _unexplained_agreements({
        "ashburn": {"gain": 65.6, "all_mech": 0.437, "station": "KIAD"},
        "chicago": {"gain": 65.6, "all_mech": 0.437, "station": "KORD"}})
    caught = bool(bad)
    # (2) THE REAL COINCIDENCE: two standalone facilities on ONE station, legitimately identical.
    n2, bad2 = _unexplained_agreements({
        "site_a": {"gain": 41.0, "all_mech": 0.500, "station": "KDEN"},
        "site_b": {"gain": 41.0, "all_mech": 0.500, "station": "KDEN"}})
    ck("the agreement rule fires on #132's shape and not on a shared station",
       caught and not bad2,
       "different stations -> caught; same station -> allowed")


def _cross_station_collisions(rows):
    """THE SAME RULE AS `_unexplained_agreements`, APPLIED TO WHOLE FILES INSTEAD OF TWO FIGURES.

    `rows` is a list of (site key, station, digest). Returns the groups that share one digest across
    MORE THAN ONE station -- the only shape that is a defect. Two facilities on one station can
    legitimately produce the same artefact once the plume term is zero, because then the stage's
    inputs are the same array; two facilities on different stations cannot, because no shared input
    exists that could make them agree. Argued in full at the call site in 6d.
    """
    by_digest = {}
    for key, station, digest in rows:
        by_digest.setdefault(digest, []).append((key, station))
    return [ks for ks in by_digest.values()
            if len(ks) > 1 and len(set(st for _, st in ks)) > 1]


def _selftest_collision_rule():
    """A PERMISSIVE RULE NEEDS ITS OWN CONTROL, for the reason `_selftest_agreement_rule` states:
    this is an assertion that can pass by accident, so it has to be shown failing on the defect it
    exists for and staying quiet on the coincidence that is real. Both cases, every run."""
    defect = _cross_station_collisions([                     # gotcha #132's shape, whole-file
        ("ashburn", "KIAD", "d1"),
        ("chicago", "KORD", "d1")])
    real = _cross_station_collisions([                       # two standalone sites on one station
        ("AZ_a", "KFFZ", "d2"),
        ("AZ_b", "KFFZ", "d2")])
    mixed = _cross_station_collisions([                      # a real pair AND a defect together
        ("AZ_a", "KFFZ", "d3"),
        ("AZ_b", "KFFZ", "d3"),
        ("ashburn", "KIAD", "d4"),
        ("chicago", "KORD", "d4")])
    ck("the artefact-collision rule fires across stations and not within one",
       bool(defect) and not real and len(mixed) == 1,
       "different stations -> caught; same station -> allowed; mixed -> only the cross-station pair")


def check_sites_actually_differ():
    """EVERY OFFERABLE SITE MUST HAVE ITS OWN NUMBERS, and this check exists because they did not.

    The interface offered a three-entry site picker and `loadSite()` swapped exactly one file: the
    solved plume field. `backtest.py` and `rolling.py` had no idea a second metro existed, so the
    headline, the schedule, the decision, the explanation, the wind dial, the coverage record, the
    ladder and the money were all Ashburn's, wearing whichever label the picker was set to. Nothing
    caught it: every number was internally consistent and every test passed.

    So the check is comparison, not existence. A site whose artefacts merely EXIST proves nothing --
    they have to be TRACEABLY ITS OWN. Dulles is the exception that proves the rule: it shares KIAD
    with Ashburn, so its WEATHER figures are identical by construction and only its GEOMETRY may
    differ. That is asserted here too.

    ⚠ REWRITTEN 2026-08-24. The rule used to be "these four fields all differ across all sites",
    which was right at three sites and breaks at three hundred -- it crashes on a standalone site's
    `facade_gap_m: null`, and its premise stops holding once the plume term is zero, because then
    two facilities on the same station in the same state produce identical numbers legitimately.
    The three exact statements that replaced it are argued in full at the comment block below.
    """
    print("\n6c. EVERY OFFERABLE SITE HAS ITS OWN NUMBERS")
    sites = jload(os.path.join(DEMO, "sites.json"))["sites"]
    keys = [s["key"] for s in sites if s.get("offerable")]
    ck("sites.json offers more than one site", len(keys) > 1, "offerable: %s" % ", ".join(keys))

    got = {}
    for s in sites:
        if not s.get("offerable"):
            continue
        art = s.get("artefacts") or {}
        missing = [n for n in ("trace", "backtest", "rolling", "money", "ticker", "explanations")
                   if n not in art]
        if missing:
            ck("%s: manifest names every artefact" % s["key"], False, "missing %s" % missing)
            continue
        t = jload(os.path.join(DEMO, art["trace"]))
        b = jload(os.path.join(DEMO, art["backtest"]))
        rt = t["cycle"]["rise_tables"]["longest"]
        base = [r for r in b["sensitivity"]["rows"] if r["is_base"]][0]
        got[s["key"]] = {
            "station": t["weather"]["station"], "hours": t["weather"]["n_hours"],
            "facade_gap_m": t["site"]["facade_gap_m"],
            "worst_bearing": rt["max_rise_bearing"], "worst_rise": rt["max_rise_c"],
            "all_mech": t["cases"]["all_mechanical"]["fraction"],
            "gain": base["gain_h_per_year"],
            "state": jload(os.path.join(DEMO, art["money"]))["metro"]["state"],
            # PROVENANCE -- who this plant physically is. Unique by construction: OSM element ids
            # are globally unique, so this is the one tuple that must never repeat at ANY scale.
            "who": (t["site"].get("osm_source"), t["site"].get("osm_receptor"),
                    tuple(t["site"]["centre"]) if t["site"].get("centre") else None),
        }
    ck("every offerable site's artefacts load", len(got) == len(keys),
       "%d of %d" % (len(got), len(keys)))
    if len(got) < 2:
        return

    # ---- 🔴 WHY THIS SECTION WAS REWRITTEN 2026-08-24, BEFORE THE SITE COUNT GREW -------------
    # The original rule was "every one of these four fields differs across every site", rounded to
    # 6 dp. It was correct at three sites and is wrong at three hundred, in two separate ways:
    #
    #  (a) IT CRASHES. `float(None)` raises, and a STANDALONE facility -- no other tagged data
    #      centre inside the solver's validated 600 m range -- has `facade_gap_m: null` and no worst
    #      bearing, because there is no receptor to have an intake. 396 of the nationally
    #      discovered facilities are standalone.
    #  (b) ITS PREMISE STOPS HOLDING. The docstring's reasoning is "different geometry on different
    #      weather cannot produce the same worst bearing and the same annual gain". For a standalone
    #      site the plume term is exactly zero, so the bound reduces to forecast + level + shape
    #      margin -- all three derived from the WEATHER RECORD alone. Two standalone facilities
    #      assigned the same ASOS station, in the same state, therefore produce genuinely IDENTICAL
    #      hours and gain. That is a true consequence of the model, not a defect, and a check that
    #      called it one would be teaching the next reader to route around a correct guard (#65).
    #      `all_mech` and `gain` are also a fraction and an hour count: at hundreds of sites they
    #      will coincide by arithmetic coincidence between unrelated facilities.
    #
    # So the rule becomes three EXACT statements with no tolerance and no threshold, each of which
    # stays true at any N:
    #   1. PROVENANCE is unique          -- no two sites are the same buildings.
    #   2. GEOMETRY is unique, among sites that HAVE geometry.
    #   3. A SHARED DECISION HAS A SHARED CAUSE -- if two sites agree on the numbers, they must
    #      agree on the station that produced them. This is the scalable form of the original
    #      intent: it still fails on Chicago-wearing-Ashburn's-numbers (different stations, same
    #      output) while permitting the one coincidence that is physically real.
    # `NATIONAL-BUILD-PLAN.md:551` is the principle: sharing a station is physically correct;
    # sharing geometry, imagery, a tile or a plume is not.

    ck("no two sites are the same buildings (provenance is unique)",
       len(set(v["who"] for v in got.values())) == len(got),
       "%d distinct (source, receptor, centre) of %d sites" % (
           len(set(v["who"] for v in got.values())), len(got)))

    paired = {k: v for k, v in got.items() if v["facade_gap_m"] is not None}
    standalone = {k: v for k, v in got.items() if v["facade_gap_m"] is None}
    geo = {k: (round(float(v["facade_gap_m"]), 6), v["worst_bearing"],
               round(float(v["worst_rise"]), 6)) for k, v in paired.items()}
    ck("no two PAIRED sites share a geometry measurement",
       len(set(geo.values())) == len(geo),
       "%d paired site(s), %d distinct (gap, worst bearing, worst rise)"
       % (len(geo), len(set(geo.values()))))

    # STANDALONE sites: the plume term must be exactly zero and SAID to be, not merely absent.
    # Reported even when there are none, so this cannot pass vacuously and unnoticed.
    ck("standalone sites carry a zero plume term, not a missing one",
       all(float(v["worst_rise"]) == 0.0 for v in standalone.values()),
       "%d standalone site(s) in this manifest%s" % (
           len(standalone), "" if standalone else " -- nothing to check yet, stated not hidden"))

    # A SHARED DECISION MUST HAVE A SHARED CAUSE. Extracted to `_unexplained_agreements` so it can
    # be exercised against the defect it exists for -- see `_selftest_agreement_rule` below, which
    # runs first. A rule this permissive (it deliberately allows two sites to agree) has to be shown
    # to still catch the original #98/#132 shape, or it is just a pass waiting to happen.
    _selftest_agreement_rule()
    n_dec, unexplained = _unexplained_agreements(got)
    ck("any two sites with the same numbers also share the station that produced them",
       not unexplained,
       "%d distinct decision(s) across %d sites" % (n_dec, len(got))
       if not unexplained
       else "SAME numbers, DIFFERENT stations: %s" % "; ".join(
           ", ".join(ks) for ks in unexplained[:3]))

    # DULLES SHARES KIAD WITH ASHBURN, so its weather figures MUST match and its geometry must not.
    if {"ashburn", "dulles"} <= set(got):
        a, d = got["ashburn"], got["dulles"]
        ck("dulles shares Ashburn's station and hour count, by design",
           a["station"] == d["station"] and a["hours"] == d["hours"],
           "%s/%s vs %s/%s" % (a["station"], a["hours"], d["station"], d["hours"]))
        ck("dulles differs from Ashburn on GEOMETRY, which is what it isolates",
           a["facade_gap_m"] != d["facade_gap_m"] and a["worst_bearing"] != d["worst_bearing"],
           "gap %.1f vs %.1f m, worst bearing %.0f vs %.0f deg"
           % (a["facade_gap_m"], d["facade_gap_m"], a["worst_bearing"], d["worst_bearing"]))
    # ---- THE PROSE MUST QUOTE THIS SITE'S OWN MEASUREMENT ------------------------------------
    # `CASE_SPECS`'s knife_edge criterion carried the literal "255 deg" -- Ashburn's worst bearing --
    # and shipped it on every site: Chicago published it while its own worst bearing was 240, Dulles
    # while its own was 265. The DAY selected was correct (the code minimises distance to the real
    # variable), so only the sentence was false, which is the hardest version to catch: nothing
    # crashed, nothing disagreed with itself numerically, and no existing check compared a criterion
    # against the number it names. Fifth instance of gotcha #67. Registered per site, so a sixth
    # hard-coded narrative in this list fails the build.
    for k, v in sorted(got.items()):
        art = [s for s in sites if s["key"] == k][0]["artefacts"]["trace"]
        t = jload(os.path.join(DEMO, art))
        crit = {c["name"]: c["criterion"] for c in t["cases"]["cases"]}
        ke = crit.get("knife_edge", "")
        wb = t["cycle"]["rise_tables"]["longest"]["max_rise_bearing"]
        # NO BEARING, NO NUMBER -- and the criterion must say so rather than quote one. This check
        # CRASHED here on the first standalone facility, and the crash is what exposed a real
        # defect: `select_cases` computed its own worst bearing by argmax, argmax of an all-zero
        # table returns index 0, and index 0 is due north -- so the trace published "the worst
        # bearing, 0 deg" for a facility with no plume at all. Both halves are asserted now, because
        # the absent case is the one that was wrong.
        if wb is None:
            ck("%-9s knife_edge states NOT APPLICABLE, and quotes no bearing" % k,
               "NOT APPLICABLE" in ke and " deg" not in ke.replace("bearing -- NOT", ""),
               "%r" % ke[-58:])
        else:
            want = "%.0f deg" % wb
            ck("%-9s knife_edge criterion quotes ITS OWN worst bearing" % k,
               want in ke, "%s -- %r" % (want, ke[-46:]))
        # AND THE TWO COMPUTATIONS OF THE SAME QUANTITY MUST AGREE. `cases.worst_bearing_deg` and
        # `rise_tables.longest.max_rise_bearing` are the same measurement derived twice, in
        # different functions. They disagreed (None vs 0.0) and nothing compared them.
        ck("%-9s the two worst-bearing derivations agree" % k,
           t["cases"]["worst_bearing_deg"] == wb,
           "cases=%r rise_table=%r" % (t["cases"]["worst_bearing_deg"], wb))
        # And no criterion may still carry an unfilled placeholder: a `{...}` that reached the
        # artefact means the .format() was skipped and a reader sees template syntax.
        ck("%-9s no case criterion carries an unfilled placeholder" % k,
           not any("{" in c or "}" in c for c in crit.values()),
           "%d criteria, all rendered" % len(crit))

    if "chicago" in got:
        ck("chicago is priced on ILLINOIS electricity, not Virginia's",
           got["chicago"]["state"] == "IL", "state=%s" % got["chicago"]["state"])
        ck("chicago runs on its OWN station record",
           got["chicago"]["station"] != got.get("ashburn", {}).get("station"),
           "%s vs ashburn %s" % (got["chicago"]["station"],
                                 got.get("ashburn", {}).get("station")))


# ---- 6d: the panels themselves, not just the numbers behind them ---------------------------
# WHICH GLOBAL CARRIES WHICH SITE'S DATA. `index.html` keeps every artefact in a short global, so
# "does this panel render anything belonging to the selected site" reduces to "which of these does
# its function body read". The mapping is the only hand-written part, it is nine lines long, and
# every entry is checkable by opening `loadSite()`.
PER_SITE_GLOBALS = {
    "T":     "trace",            # agent.py    -- geometry, rise table, cases, provenance
    "BT":    "backtest",         # backtest.py -- the five-year ladder and the sensitivity sweep
    "RL":    "rolling",          # rolling.py  -- the present-tense controller
    "MN":    "money",            # money.py    -- priced in this site's own state
    "TK":    "ticker",           # ticker.py   -- the stage-event tape
    "EX":    "explanations",     # explain.py  -- stage 7
    "PF":    "plume_field",      # export_plume_fields.py (not in `artefacts`; named per site)
    "SITE":  "sites.json entry", # the manifest row: label, station, imagery, committed pair
    "SITES": "sites.json",       # the whole manifest; drawReportLink selects this site's row from it
    "FIELD": "FortyGuard field", # only Ashburn and Chicago have one; Dulles has none
}

# A panel is allowed to render the SAME thing for every site only if the reason is recorded here.
# This is the one surviving limit from the per-site rework (HANDOFF section 6.13): only Ashburn has
# forecast/outcome day-pairs, so every site's COVERAGE is Ashburn's, borrowed and labelled. Writing
# it down as an exception is the point -- a borrowed number that nobody declared is indistinguishable
# from the bug this check exists to catch.
SHARED_PANELS = {
    "drawCoverageTiles": "the N-26 coverage tiles ARE Ashburn's measured day-pairs. No other site "
                         "has any, so borrowing is the honest presentation and the tile is "
                         "labelled 'borrowed' by drawHeadline.",
    # `drawConformal` WAS DECLARED HERE AND IT WAS WRONG. The render-level diff measured it on
    # 2026-08-21: the panel draws each site's OWN twelve per-lead margins from its own rolling.json
    # (Ashburn 0.81 -> 7.06 C, Chicago 0.98 -> 6.44 C) and one of its three canvases differs with
    # them. Only the n=4 day-pair block inside it is borrowed. A wrong exception is worse than no
    # exception, because it silently excuses the panel from the check -- which is why the two
    # instruments exist: this one reads the source, testing/verify_site_panels.py renders the page,
    # and the render caught what the source reading excused.
}

# Panels that are not per-site by construction, and would be a lie if they were.
GLOBAL_PANELS = {
    # RENAMED 2026-08-24: the small 5-metro map and the ~422-site national map were merged into
    # one, per the user's instruction. `drawUnifiedMap` shows every real site this project has
    # found, across all sites the picker offers -- more global than `drawMap` ever was, not less;
    # it is deliberately never filtered to the current selection.
    "drawUnifiedMap": "the unified map shows every real site this project has identified -- the "
                      "running ones, the known refusals, and every national candidate -- and is "
                      "deliberately not filtered to whichever site is currently selected.",
    "drawModeBanner": "LIVE vs REPLAY is a property of the SERVER, not of the site.",
}


def _js_code_only(src):
    """Blank out comments and string/template/regex literals, KEEPING LENGTH AND OFFSETS.

    WHY NOT `_COMMENT_RE`. The blunt regex is fine for hunting an identifier -- a truncated line can
    only lose a hit, which `check_retired_constants` records as a stated limitation. It is NOT fine
    for counting braces, and this cost a wrong answer on the first run of check 6d: `//` inside a
    string is not a comment, so `'https://server.arcgisonline.com/...'` had its line eaten from the
    `//` onward, taking the closing brace with it. `drawMap` -- the one panel full of tile URLs --
    then had unbalanced braces and reported as "no function body found", which reads as a missing
    function rather than a broken scanner. Gotcha #47's family: my verification code was buggier
    than the product.

    Blanking rather than deleting keeps every offset, so a match found here points at the same
    character in the original text.

    STATED LIMITS. The regex-vs-division `/` ambiguity is resolved by the standard heuristic (a
    regex may start only where a value may not continue). This file is friendly to it: gotcha #77
    already forced `tkRender` to write `\\x7B` / `\\x7D` instead of literal braces inside a regex,
    with a comment telling the next reader not to tidy it up. `_selftest_js_scanner` pins the cases.
    """
    n = len(src)
    out = list(src)

    def blank(k):
        if 0 <= k < n and out[k] != "\n":     # newlines survive, so line numbers still work
            out[k] = " "

    i, mode, prev = 0, "code", ""
    tpl = []                        # brace depth inside each `${ ... }` we are currently within
    in_class = False                # inside a regex character class, where `/` is literal
    while i < n:
        c, two = src[i], src[i:i + 2]
        if mode == "code":
            if two == "//":
                mode = "line"; blank(i); blank(i + 1); i += 2; continue
            if two == "/*":
                mode = "block"; blank(i); blank(i + 1); i += 2; continue
            if src[i:i + 4] == "<!--":
                mode = "html"
                for k in range(4):
                    blank(i + k)
                i += 4; continue
            if c in "'\"":
                mode = "sq" if c == "'" else "dq"; blank(i); i += 1; continue
            if c == "`":
                mode = "tpl"; blank(i); i += 1; continue
            # A `/` starts a regex only where a VALUE cannot continue. After an identifier, a
            # digit, or a closing bracket, it is division.
            if c == "/" and not (prev.isalnum() or prev in "_)]}"):
                mode = "regex"; in_class = False; blank(i); i += 1; continue
            if tpl:
                if c == "{":
                    tpl[-1] += 1
                elif c == "}":
                    if tpl[-1] == 0:
                        blank(i); tpl.pop(); mode = "tpl"; i += 1; continue
                    tpl[-1] -= 1
            if not c.isspace():
                prev = c
            i += 1; continue
        if mode == "line":
            if c == "\n":
                mode = "code"; i += 1; continue
            blank(i); i += 1; continue
        if mode == "block":
            if two == "*/":
                blank(i); blank(i + 1); mode = "code"; i += 2; continue
            blank(i); i += 1; continue
        if mode == "html":
            if src[i:i + 3] == "-->":
                for k in range(3):
                    blank(i + k)
                mode = "code"; i += 3; continue
            blank(i); i += 1; continue
        if mode in ("sq", "dq"):
            if c == "\\":
                blank(i); blank(i + 1); i += 2; continue
            if c == ("'" if mode == "sq" else '"'):
                blank(i); mode = "code"; prev = "1"; i += 1; continue
            if c == "\n":
                mode = "code"; i += 1; continue        # unterminated: bail rather than eat the file
            blank(i); i += 1; continue
        if mode == "tpl":
            if c == "\\":
                blank(i); blank(i + 1); i += 2; continue
            if two == "${":
                blank(i); blank(i + 1); tpl.append(0); mode = "code"; i += 2; continue
            if c == "`":
                blank(i); mode = "code"; prev = "1"; i += 1; continue
            blank(i); i += 1; continue
        if mode == "regex":
            if c == "\\":
                blank(i); blank(i + 1); i += 2; continue
            if c == "\n":
                mode = "code"; i += 1; continue        # not a regex after all
            if c == "[":
                in_class = True
            elif c == "]":
                in_class = False
            elif c == "/" and not in_class:
                blank(i); mode = "code"; prev = "1"; i += 1; continue
            blank(i); i += 1; continue
    return "".join(out)


def _selftest_js_scanner():
    """The scanner gets its own test, because it is the thing that decides what check 6d can see.

    Every case here is a shape that actually appears in `index.html`, and the first one is the bug
    that made the check report a missing function on its first run.
    """
    cases = [
        ("a URL in a string is not a comment",
         "function f(){ const u='https://x/y'; }", "function f(){ const u=", True),
        ("a real line comment goes",
         "function f(){ // }} nonsense\n }", "nonsense", False),
        ("a block comment goes, braces and all",
         "function f(){ /* }} SPOILER */ }", "SPOILER", False),
        ("a brace inside a string does not count",
         "function f(){ const s='{{{'; }", "{{{", False),
        ("a template literal's ${} stays code",
         "function f(){ `a${T.x}b`; }", "T.x", True),
        ("a regex literal is blanked",
         "function f(){ s.replace(/[}]/g,''); }", "[}]", False),
    ]
    bad = []
    for name, src, needle, want in cases:
        got = needle in _js_code_only(src)
        if got != want:
            bad.append(name)
    # And the property that matters: braces must balance on every case.
    for name, src, _, _ in cases:
        code = _js_code_only(src)
        if code.count("{") != code.count("}"):
            bad.append("%s (braces unbalanced: %d/%d)"
                       % (name, code.count("{"), code.count("}")))
    ck("the JS scanner passes its own %d-case test" % len(cases), not bad,
       "comments and literals blanked, offsets preserved" if not bad else "; ".join(bad))


def _js_function_body(src, name):
    """Extract one `function name(...) { ... }` body by brace counting over code-only text.

    Comments are removed for a second reason beyond brace safety: a retraction note in `index.html`
    quotes the three Ashburn coordinates that gotcha #98 removed, so a scanner that reads comments
    would report the documented retraction as the defect it documents -- gotcha #55b, verbatim, for
    the third time in this project.
    """
    code = _js_code_only(src)
    m = re.search(r"function\s+%s\s*\([^)]*\)\s*\{" % re.escape(name), code)
    if not m:
        return None
    i = m.end() - 1
    depth = 0
    for j in range(i, len(code)):
        if code[j] == "{":
            depth += 1
        elif code[j] == "}":
            depth -= 1
            if depth == 0:
                return code[i:j + 1]
    return None


def check_panels_are_per_site():
    """EVERY RESULT PANEL MUST RENDER THE SELECTED SITE'S OWN DATA -- checked at the panel level.

    Check 6c compares NUMBERS across sites and is the reason the picker cannot go back to swapping
    one file. But 6c works from a list of values chosen by hand, so it can only ever prove things
    about the values someone thought to register. The defect it was written for had a second half
    that a value list cannot see: `drawAerial` read THREE ASHBURN COORDINATES as source-level
    constants while drawing per-site footprints on top of them, so selecting Chicago georeferenced
    Chicago's halls onto Ashburn's photograph (gotcha #98). Every number was per-site. The frame of
    reference was not, and the picture looked entirely plausible.

    So this check works from the PANELS instead, and it derives the panel list from `drawAll()`
    rather than holding one -- a panel added to the page and not registered here fails the build,
    which is the only way a registry stays honest (gotcha #74: a test that excludes a code path
    reports PASS for it).

    Three things are asserted:
      1. every panel `drawAll()` calls either reads a per-site global, or is declared shared/global
         WITH A REASON;
      2. every per-site global's underlying artefact really does differ between the three sites --
         because a panel reading `BT` proves nothing if all three backtests are the same file;
      3. no site-identifying literal (a committed OSM id, a hall coordinate, an imagery bbox, a
         station id) appears anywhere in the page's code. That is #98's signature, and it is the one
         thing neither 6c nor a screenshot can see.
    """
    print("\n6d. EVERY PANEL RENDERS THE SELECTED SITE, NOT ASHBURN WEARING ITS LABEL")
    # The scanner decides what this whole check is able to see, so it is tested first and its
    # result is a REGISTERED ASSERTION -- not a comment claiming it was tested once.
    _selftest_js_scanner()
    # Same standard for the artefact-collision rule below: it is permissive by design, so its
    # control is registered rather than asserted in prose.
    _selftest_collision_rule()
    page = open(os.path.join(DEMO, "index.html"), encoding="utf-8").read()
    sites = jload(os.path.join(DEMO, "sites.json"))["sites"]
    offer = [s for s in sites if s.get("offerable")]

    # ---- 1. the panel list, DERIVED from drawAll() -------------------------------------
    body = _js_function_body(page, "drawAll")
    if body is None:
        ck("drawAll() is where the panel list comes from", False, "not found in index.html")
        return
    panels = [n for n in re.findall(r"\b(draw[A-Za-z]\w*)\s*\(", body)]
    panels = sorted(set(panels))
    ck("the panel list is read from drawAll(), not held here", len(panels) >= 12,
       "%d panels: %s" % (len(panels), ", ".join(p[4:].lower() for p in panels)))

    # ---- 2. each panel reads something that belongs to the selected site --------------
    # ONE LEVEL OF INDIRECTION IS FOLLOWED, and it has to be: `drawSched` reads nothing itself, it
    # calls `decide()` -- the agent, re-run in the browser -- and `drawLimits` gets its two priced
    # entries from `refusalLimits()`. A check that only saw direct reads reported both as rendering
    # nothing site-specific, which is a false alarm, and a check that cries wolf gets ignored
    # (gotcha #47). Depth is ONE and stated: deeper would need a call graph, and at that point the
    # render-level driver in testing/verify_site_panels.py is the better instrument.
    def reads_of(fn_src):
        return sorted(g for g in PER_SITE_GLOBALS if re.search(r"\b%s\b" % g, fn_src))

    unregistered, no_input, per_site_ok = [], [], {}
    for p in panels + sorted(GLOBAL_PANELS):
        fn = _js_function_body(page, p)
        if fn is None:
            unregistered.append("%s (no function body found)" % p)
            continue
        direct = reads_of(fn)
        if direct:
            per_site_ok[p] = ", ".join(direct)
            continue
        via = None
        for callee in sorted(set(re.findall(r"\b([a-z][A-Za-z0-9_]*)\s*\(", fn))):
            if callee == p:
                continue
            sub = _js_function_body(page, callee)
            if sub and reads_of(sub):
                via = "%s() -> %s" % (callee, ", ".join(reads_of(sub)))
                break
        if via:
            per_site_ok[p] = via
        elif p in SHARED_PANELS or p in GLOBAL_PANELS:
            pass                                     # declared, with its reason, above
        else:
            no_input.append(p)
    ck("every panel drawAll() calls renders the selected site's own data, or says why not",
       not no_input and not unregistered,
       "%d per-site, %d declared shared/global"
       % (len(per_site_ok), len(SHARED_PANELS) + len(GLOBAL_PANELS))
       if not (no_input or unregistered)
       else "UNDECLARED: %s" % ", ".join(no_input + unregistered))

    # ---- 2b. THE DECLARED EXCEPTIONS MUST BE TRUE, NOT JUST DECLARED -----------------
    # The first version of this asserted that a "shared" panel reads no per-site global, and that
    # was the wrong test: `drawConformal` reads `T` for `cycle.bound_day_level`, which is BYTE
    # IDENTICAL across all three sites by design. Reading a per-site file does not make a panel
    # per-site; rendering a value that differs does. So the exception is checked against the data:
    # what it claims is borrowed must actually be identical, and the artefact must SAY it is
    # borrowed. An excuse nobody re-reads is how a retracted claim survives (gotcha #56).
    if len(offer) > 1:
        traces = {}
        for s in offer:
            nm = (s.get("artefacts") or {}).get("trace")
            if nm and os.path.exists(os.path.join(DEMO, nm)):
                traces[s["key"]] = jload(os.path.join(DEMO, nm))
        covs = set(json.dumps(t["cycle"]["bound_day_level"], sort_keys=True)
                   for t in traces.values())
        pooled = set(round(t["cycle"]["pooled_coverage"], 12) for t in traces.values())
        ck("the borrowed coverage really is identical across sites, as declared",
           len(covs) == 1 and len(pooled) == 1,
           "one bound_day_level and one pooled coverage %.4f across %d sites"
           % (list(pooled)[0], len(traces)) if len(covs) == 1 and len(pooled) == 1
           else "%d distinct bound_day_level / %d distinct coverage -- the SHARED_PANELS "
                "declaration is now false and those panels are per-site" % (len(covs), len(pooled)))
        # And every site that borrows must SAY so in the artefact the page reads, or the borrowing
        # is invisible to a reader. This is the one limit HANDOFF 6.13 says survives.
        unlabelled = [k for k, t in traces.items()
                      if k != "ashburn"
                      and (t.get("fortyguard_provenance") or {}).get("own_measured_day_pairs")
                      is not False]
        ck("every site without its own day-pairs records that its coverage is borrowed",
           not unlabelled, "%d borrowing site(s) labelled" % (len(traces) - 1) if not unlabelled
           else "UNLABELLED: %s" % ", ".join(unlabelled))

    # ---- 3. the artefacts behind those globals actually differ -------------------------
    # Reading `BT` proves a panel asked for the backtest. It does not prove the three backtests are
    # three different files -- which is exactly what was wrong before the per-site rework.
    # ⚠ AMENDED 2026-08-25, and it is the SAME amendment 6c already carries.
    #
    # The rule was `len(digests) == len(paths)` -- every offerable site's artefact must be a
    # distinct file, full stop. That was correct at three hand-built metros and it is wrong at
    # three hundred national facilities, for exactly the reason `check_sites_actually_differ`
    # records one section above: "its premise stops holding once the plume term is zero, because
    # then two facilities on the same station in the same state produce identical numbers
    # legitimately." 6c was rewritten for that on 2026-08-24. This check was not, so the premise
    # survived here alone and fired on the first pair of facilities that met it.
    #
    # THE PAIR THAT FOUND IT: AZ_way_1015704066 and AZ_way_567575425. Both standalone, both with
    # `plume_modelled: false`, both on KFFZ, both with 41919 hours -- and their traces carry
    # byte-identical `temp_c`, `dewpoint_c` and `twb_c`. The explanation stage reads temperature,
    # dew point, wet-bulb and plume rise. With no plume term, its inputs at those two sites are the
    # same array, so identical explanations are the CORRECT output. Demanding that they differ
    # would be demanding a difference the physics does not contain -- which is the one thing this
    # file exists to prevent, pointed the wrong way.
    #
    # So the test becomes the one 6c uses via `_unexplained_agreements`: a digest collision is a
    # defect only when it CROSSES A WEATHER STATION. Two sites on one station may agree; two sites
    # on different stations may not, because there is no shared input that could make them.
    # Gotcha #132's shape -- Chicago wearing Ashburn's numbers -- still fails, which is the whole
    # point of keeping the check at all.
    if len(offer) > 1:
        differing, identical, detail = [], [], []
        for g, art in sorted(PER_SITE_GLOBALS.items()):
            pairs = []                               # (site key, station, path)
            for s in offer:
                nm = (s.get("artefacts") or {}).get(art)
                if nm:
                    pairs.append((s["key"], s.get("station"), os.path.join(DEMO, nm)))
            if len(pairs) < 2:
                continue                             # PF/SITE/FIELD are not `artefacts` entries
            rows = []
            for key, station, path in pairs:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        rows.append((key, station, hashlib.md5(f.read()).hexdigest()))
            crossed = _cross_station_collisions(rows)
            if crossed:
                identical.append(g)
                for ks in crossed:
                    detail.append("%s: %s" % (g, " = ".join("%s(%s)" % (k, st) for k, st in ks)))
            else:
                differing.append(g)
        ck("no per-site artefact is shared by two sites on DIFFERENT stations", not identical,
           "%s: no cross-station collision across %d sites" % (", ".join(differing), len(offer))
           if not identical else "CROSS-STATION COLLISION -- %s" % "; ".join(detail))

    # ---- 4. no site-identifying literal in the page's code ---------------------------
    # THE ONE THAT WOULD HAVE CAUGHT #98. Comments are stripped first, deliberately: the retraction
    # note in index.html quotes the three coordinates it removed, and flagging that note would be
    # gotcha #55b for the third time -- a scanner failing on prose that documents a retirement.
    code = _COMMENT_RE.sub("", page)
    i, j = code.rfind("<script>"), code.rfind("</script>")
    code = code[i:j] if i >= 0 and j > i else code
    leaked = []
    for s in sites:                                  # ALL sites, including the two refused
        c = s.get("committed") or {}
        im = s.get("imagery") or {}
        cands = []
        for key in ("source_osm_id", "receptor_osm_id"):
            if c.get(key):
                cands.append((key, str(c[key])))
        for key in ("source_latlon", "receptor_latlon"):
            for v in (c.get(key) or []):
                cands.append((key, "%.6f" % float(v)))
        for v in (im.get("bbox") or []):
            cands.append(("imagery bbox", "%.6f" % float(v)))
        if s.get("station"):
            cands.append(("station", str(s["station"])))
        for what, lit in cands:
            # Trailing-zero forms are what a hand-copied coordinate looks like, so both are checked.
            forms = {lit, lit.rstrip("0").rstrip(".")} if "." in lit else {lit}
            for f in forms:
                if len(f) >= 6 and re.search(r"(?<![\d.])%s(?![\d])" % re.escape(f), code):
                    leaked.append("%s %s=%s" % (s["key"], what, f))
    ck("no site's own coordinate, OSM id or station is a literal in the page",
       not leaked, "checked %d sites' committed pairs and imagery frames" % len(sites)
       if not leaked else "LEAKED: %s" % "; ".join(sorted(set(leaked))[:4]))


def check_wind_is_this_sites_own():
    """EVERY SITE'S WIND RECORD MUST BE ITS OWN STATION'S, AND THE ARITHMETIC PROVES IT.

    THE DEFECT. `direction_sweep.py:load_wind()` read `kiad_hourly_2021_2025.json` as a LITERAL, on
    every site, for two days after the engine was made per-site. So Chicago's per-bearing rise curve
    and its 72 rendered plume fields were solved at **Virginia's** median wind speed (3.60 m/s
    instead of its own 4.12), its wind statistics were KIAD's, and the block even hard-coded
    `"station": "KIAD"` beside them.

    WHY NOTHING CAUGHT IT. Check 6c compares values across sites and fails on agreement -- but it
    compares a registered list, and the wind block was not on it. Check 6d compares panels. Both
    would have passed forever: every number was internally consistent, and "Chicago is windier than
    Virginia" is not something a reader can check by looking.

    WHAT CATCHES IT IS AN IDENTITY, and it was sitting in the artefact all along. The three wind
    counts PARTITION the station's record, so

        usable_hours + calm_excluded + missing == that site's own n_hours

    must hold exactly. Chicago's came to 43,763 -- KIAD's hour count -- against its own 43,775. Two
    numbers twelve apart in a file nobody was joining. This is the same shape as gotcha #63: an
    exact identity is worth more than a tolerance, because you can say why it must be zero.
    """
    print("\n6e. EVERY SITE'S WIND IS ITS OWN STATION'S RECORD")
    sites = jload(os.path.join(DEMO, "sites.json"))["sites"]
    seen = {}
    for s in sites:
        if not s.get("offerable"):
            continue
        art = (s.get("artefacts") or {}).get("trace")
        if not art:
            continue
        t = jload(os.path.join(DEMO, art))
        w = t.get("direction_table", {}).get("wind") or {}
        n_hours = t["weather"]["n_hours"]
        station = t["weather"]["station"]
        parts = [w.get("usable_hours"), w.get("calm_excluded"), w.get("missing")]
        ck("%-9s wind counts partition its OWN record exactly" % s["key"],
           all(isinstance(x, int) for x in parts) and sum(parts) == n_hours,
           "%s + %s + %s = %s == %s h at %s"
           % tuple(list(parts) + [sum(x for x in parts if isinstance(x, int)), n_hours, station])
           if all(isinstance(x, int) for x in parts)
           else "wind block is missing a count: %s" % parts)
        ck("%-9s wind names the station the weather record came from" % s["key"],
           w.get("station") == station,
           "%s == %s" % (w.get("station"), station))
        seen[s["key"]] = (w.get("station"), tuple(parts), t["direction_table"]["modes"]["longest"]
                          .get("u_median_ms"))

    # AND THE CROSS-SITE HALF: two sites may share a wind record ONLY if they share a station.
    # Dulles shares KIAD with Ashburn by design and must match; Chicago must not match either.
    if {"ashburn", "chicago"} <= set(seen):
        a, c = seen["ashburn"], seen["chicago"]
        ck("chicago's wind DIFFERS from ashburn's, because KORD is not KIAD",
           a[1] != c[1] and a[2] != c[2],
           "calm %d vs %d h, median wind %.4f vs %.4f m/s"
           % (a[1][1], c[1][1], a[2], c[2]))
    if {"ashburn", "dulles"} <= set(seen):
        a, d = seen["ashburn"], seen["dulles"]
        ck("dulles's wind MATCHES ashburn's, because it is the same station -- the control",
           a[1] == d[1] and a[2] == d[2],
           "both %d usable at %.4f m/s, so only geometry differs" % (a[1][0], a[2]))

    # ---- WHO THIS PLANT IS. Three literals, in every site's trace, for two days. ------------
    # `osm_source`, `osm_receptor` and `operator` were typed into `agent.py`, so Chicago's trace
    # identified its plant as two AWS halls in Virginia and `report.py` printed that OSM pair onto
    # page 1 of Chicago's PDF. Found by walking every leaf of the three traces and listing the ones
    # that AGREED -- which is the general method this check now encodes for the identity fields:
    # two different buildings cannot share an OSM id, so equality here is proof of a fallback.
    ident = {}
    for s in sites:
        if not s.get("offerable"):
            continue
        art = (s.get("artefacts") or {}).get("trace")
        if not art:
            continue
        st = jload(os.path.join(DEMO, art))["site"]
        ident[s["key"]] = (st.get("osm_source"), st.get("osm_receptor"), st.get("operator"))
    # 🔴 AN ABSENT RECEPTOR IS NOT A COLLIDING ONE, and this is the THIRD check in this file to meet
    # that distinction. `osm_receptor` is null at every standalone facility -- there is no second
    # building -- so two of them both read `None` and a pairwise-distinctness test calls that a
    # fallback. It is the opposite: it is the honest record of an absence, and the value that must
    # be unique is the one that identifies the plant, `osm_source`.
    # So nulls are EXCLUDED from the comparison and asserted separately as nulls. Skipping them
    # silently would be the danger; counting them as duplicates is merely wrong.
    # THE TWO ID FIELDS KEEP THE UNIQUENESS RULE, because the premise holds for them exactly: an
    # OSM way id names one building, so two sites reporting the same id is proof of a fallback and
    # cannot be anything else.
    for i, field in enumerate(("osm_source", "osm_receptor")):
        vals = {k: v[i] for k, v in ident.items()}
        absent = {k for k, v in vals.items() if v is None}
        if absent:
            ck("%s is NULL at %d facility(ies) with no receptor, not duplicated" % (field,
                                                                                   len(absent)),
               all(vals[k] is None for k in absent),
               "null at %s -- one building, so there is no second id to name"
               % ", ".join(sorted(absent)))
            vals = {k: v for k, v in vals.items() if k not in absent}
        if len(vals) < 2:
            continue
        ck("every site names its OWN %s" % field,
           len(set(vals.values())) == len(vals),
           " | ".join("%s=%s" % (k, str(v)[:26]) for k, v in vals.items()))

    # 🔴 `operator` WAS IN THE LOOP ABOVE, AND UNIQUENESS IS THE WRONG TEST FOR A NAME.
    # It failed the moment the national tier reached a second Google facility: NE_way_1422101116
    # (way 1422101116, Nebraska) and OH_way_1281982556 (way 1252196814, Ohio) are two different
    # buildings about 1,100 km apart, and OpenStreetMap tags both `name=Google`. That is OSM telling
    # the truth -- one operator runs many halls -- not a fallback. Demanding distinct operator
    # strings would force a FABRICATED difference into the trace and onto page 1 of two PDFs, which
    # is this section's own failure mode pointed the wrong way.
    # The defect it was written for is narrower and is still asserted below: a non-default site
    # carrying the DEFAULT site's operator string, which is how Chicago's trace came to identify its
    # plant as two AWS halls in Virginia. The strong general guarantee is the OSM-id uniqueness
    # above -- an id cannot be legitimately shared, a name can.
    import metros as _MO                                                  # noqa: PLC0415
    ops = {k: v[2] for k, v in ident.items() if v[2] is not None}
    default_op = ops.get(_MO.DEFAULT_METRO)
    if default_op and len(ops) > 1:
        borrowed = sorted(k for k, v in ops.items()
                          if k != _MO.DEFAULT_METRO and v == default_op)
        ck("no site wears the reference site's operator", not borrowed,
           "%d site(s) checked against %r" % (len(ops) - 1, default_op) if not borrowed
           else "BORROWED by %s" % ", ".join(borrowed))
    # AND A FALLBACK LABEL MUST STILL BE UNIQUE. "OSM way N" is derived from the id, so two sites
    # showing the same one would mean the id itself was shared -- forbidden above. This reads that
    # same guarantee back through the operator string, which is the field a reader actually sees,
    # and it is the assertion that would have caught the bare word "unnamed" shared by four sites.
    fb = {k: v for k, v in ops.items() if v.startswith("OSM way ")}
    if fb:
        ck("every derived operator label is unique, not a shared placeholder",
           len(set(fb.values())) == len(fb),
           "%d unnamed building(s), each identified by its own way id" % len(fb))
    # AND IT MUST MATCH THE MANIFEST, which reads the same committed file by a different path. Equal
    # values from two readers is the check; the trace agreeing with itself would prove nothing.
    for s in sites:
        if not s.get("offerable") or s["key"] not in ident:
            continue
        c = s.get("committed") or {}
        got = ident[s["key"]]
        ck("%-9s trace and manifest agree on the committed pair" % s["key"],
           got[0] == c.get("source_osm_id") and got[1] == c.get("receptor_osm_id"),
           "OSM %s -> %s" % (got[0], got[1]))

    # The rendered plume fields are solved AT that median speed, so they must agree with it. This is
    # the path the defect actually travelled: export_plume_fields.py reads the direction table's u.
    for s in sites:
        if not s.get("offerable"):
            continue
        pf = os.path.join(DEMO, "plume_field_%s_longest.json" % s["key"])
        if not os.path.exists(pf):
            continue
        u_field = jload(pf).get("wind_speed_ms")
        u_table = seen.get(s["key"], (None, None, None))[2]
        ck("%-9s rendered plume was solved at ITS OWN median wind" % s["key"],
           u_field is not None and u_table is not None
           and abs(float(u_field) - float(u_table)) < 1e-6,
           "%.6f m/s in both the field and the direction table" % float(u_field)
           if u_field is not None else "field carries no wind_speed_ms")


def _binding_counts(ex):
    """Count every hour explanation by which gate decided it, walking the shipped file.

    Walked rather than read from a summary block, because there is no summary block -- and that is
    precisely why these figures drifted. Counting them here means the documents are checked against
    the explanations themselves, not against another number someone maintained by hand.
    """
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if "binding" in o:
                k = o["binding"] or "none"
                out[k] = out.get(k, 0) + 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(ex)
    return out


def _binding_count(ex, gate):
    return _binding_counts(ex).get(gate, 0)


def _binding_pct(ex, gate):
    c = _binding_counts(ex)
    total = sum(c.values())
    return round(100.0 * c.get(gate, 0) / total, 1) if total else 0.0


# ---- 5b: retracted CLAIMS, not retracted constants -----------------------------------------
# `check_retired_constants` catches a retracted NUMBER coming back. Nothing caught a retracted
# SENTENCE, and this project has now shipped one three times:
#   #56  "the solver absorbs heat into buildings" -- live in the demo's own Honest Limits panel a
#        week after retraction.
#   #129 "No dollars, no kWh, anywhere" -- live beside a priced money panel, and Ashburn's worst
#        rise quoted on all three sites.
#   #97/#137 "Recirculation awareness buys safety, not hours" -- live on the five-year ladder panel
#        for three days after backtest.py and HANDOFF had both been corrected, printing the word
#        "costs" in front of a positive gain.
# Every one was invisible to `check_published_numbers`, because that re-reads FIGURES and all three
# defects were in the WORDS around correct figures. Hence a phrase registry.
#
# WHERE IT SCANS, and why the list is short: the surfaces a reader actually meets. HANDOFF.md and
# PLAN.md are excluded as WHOLE files because both are required to quote retracted claims in order
# to record the retraction (methodology rule 6) -- registering a phrase and then banning the
# document that explains it would be gotcha #55b for the fourth time.
#
# ⚠ A RETRACTION IS A CLAIM, NOT A STRING, AND THIS REGISTRY MATCHES STRINGS. Two live defects
# evaded it BY ONE WORD each, found 2026-08-23:
#   INTAKE-ARBITER/demo/README.md carried "costs hours and buys safety" against a registry holding
#   "buys safety, not hours"; and agent.py's say() block carried "+67 h/yr, recirculation alone"
#   against a registry holding "+67 h/yr FROM recirculation alone" -- a comma for a preposition.
# So every phrasing of a retracted claim that has ACTUALLY BEEN WRITTEN gets its own entry, and the
# entries below record which file each one was found in. This cannot be made exhaustive against
# paraphrase; it can only be kept honest about what has been seen.
RETRACTED_CLAIMS = [
    ("buys safety, not hours",
     "gotcha #97: the plume buys BOTH -- +22.8 h/yr AND 3.7x fewer breaches"),
    ("costs hours and buys safety",
     "gotcha #97/#137: it buys BOTH; not a safety-for-hours trade (was in demo/README.md)"),
    ("buys safety rather than hours",
     "gotcha #97/#137: it buys BOTH"),
    ("recirculation awareness costs hours",
     "gotcha #97/#137: plume awareness GAINS +22.8 h/yr; it does not cost hours"),
    ("h/yr, recirculation alone",
     "gotcha #67 / PLAN 12.9: the misattribution again, comma for `from` (was in agent.py's say())"),
    ("h/year, recirculation alone",
     "gotcha #67 / PLAN 12.9: same misattribution, spelled-out form"),
    ("costs 22.8 h/year",
     "gotcha #97: it is a difference of two GAINS, so it is a benefit"),
    ("solver absorbs heat into buildings",
     "gotcha #26/#56: obstacles are TRANSPARENT, 0.0 % absorbed"),
    ("absorbs heat into buildings",
     "gotcha #26/#56: obstacles are TRANSPARENT, 0.0 % absorbed"),
    ("no dollars, no kwh, anywhere",
     "gotcha #129: the compressor term IS priced and a money panel ships"),
    ("operators read a weather station kilometres away",
     "PLAN 12.9: FALSE -- on-site rooftop stations"),
    ("nobody sells forecast-aware switching",
     "PLAN 12.9: overstated"),
    ("+67 h/yr from recirculation alone",
     "PLAN 12.9: misattributed -- it is an uncertainty asymmetry"),
    ("forecast windows are unavailable on this plan",
     "gotcha #59: wrong -- it was an outage, entitlement is proved"),
]


def _retracted_hits(text, is_html):
    """Which registered retracted phrases survive in `text` once excusable context is removed."""
    if is_html:
        text = _js_code_only(text)            # blanks comments AND is string-safe, unlike a regex
    else:
        keep = []
        for ln in text.splitlines():
            if re.search(r"retract|corrected|superseded|was wrong|no longer|gotcha #|"
                         r"never reuse|stood here|used to (say|read)", ln, re.I):
                continue
            keep.append(ln)
        text = "\n".join(keep)
    low = re.sub(r"\s+", " ", text).lower()
    return [(p, why) for p, why in RETRACTED_CLAIMS if p in low]


# A PRINTED STRING IS A READER-FACING SURFACE; A COMMENT IS NOT. `agent.py`'s say() block prints
# to the console on every `agent.py run` and carried a registered retraction for weeks -- the
# markdown/HTML scan above never looked at .py files. But `backtest.py` deliberately QUOTES
# "buys SAFETY, not HOURS" in a comment explaining gotcha #97's correction, and flagging that would
# be gotcha #55b for the fifth time (the scanner that fires on prose documenting a retirement).
#
# The discriminator is therefore SYNTACTIC, not textual: an AST walk over string constants sees the
# say() and cannot see the comment. That is the same reasoning that forced `check_retired_constants`
# to be AST-based. Docstrings are excluded on the same ground as comments -- they explain to a
# maintainer, they do not assert to a user.
_PY_SCAN_SKIP = {"audit.py"}      # this file HOLDS the registry; scanning it would hit every phrase


def _docstring_ids(tree):
    """id() of every string node that is a docstring, so the scan can skip them."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def _retracted_hits_in_python(src, filename="<scan>"):
    """Registered retractions living in a string this module can PRINT or EMIT.

    Returns [(phrase, why, lineno)]. A SyntaxError is reported rather than swallowed: a source file
    this audit cannot parse is a file it cannot vouch for, and returning [] would read as clean.
    """
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError as e:
        return [("<unparseable>", "could not parse: %s" % e, getattr(e, "lineno", 0) or 0)]
    skip = _docstring_ids(tree)
    hits = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip):
            low = re.sub(r"\s+", " ", node.value).lower()
            for phrase, why in RETRACTED_CLAIMS:
                if phrase in low:
                    hits.append((phrase, why, getattr(node, "lineno", 0)))
    return hits


def _selftest_python_retraction_scanner():
    """A NEGATIVE CONTROL whose first case is the exact string that shipped in agent.py.

    Case 3 is the one that matters most: it is `backtest.py`'s real comment, and it MUST NOT hit.
    A scanner that cannot tell a printed assertion from a comment explaining a correction would be
    turned off within a day, and then it protects nothing (gotcha #47).
    """
    SHIPPED = ('say("        claims to: N-56 puts the zero-notice gain at '
               '+67 h/yr, recirculation alone.")')
    cases = [
        ("the say() that actually shipped in agent.py is caught", SHIPPED, True),
        ("a retraction in any other printed string is caught",
         'print("the solver absorbs heat into buildings")', True),
        ("backtest.py's real COMMENT quoting the retraction is NOT flagged",
         '# underneath ("buys SAFETY, not HOURS") is what stopped anyone reading the number\n'
         'dh = a - b', False),
        ("a DOCSTRING explaining the retraction is NOT flagged",
         'def f():\n    """This used to say buys safety, not hours, which was wrong."""\n    return 1',
         False),
        ("a module docstring explaining it is NOT flagged",
         '"""Retired: costs hours and buys safety."""\nx = 1', False),
        ("corrected wording in a printed string is clean",
         'say("the plume buys BOTH: +22.8 h/yr and 3.7x fewer breaches")', False),
        ("an f-string carrying the claim is still caught",
         'say(f"gain {x}: buys safety, not hours")', True),
        ("a file that does not parse is reported, never treated as clean",
         'def broken(:\n', True),
    ]
    bad = []
    for name, src, want_hit in cases:
        if bool(_retracted_hits_in_python(src)) != want_hit:
            bad.append(name)
    ck("the python-string retraction scanner passes its own %d-case control" % len(cases), not bad,
       "including agent.py's shipped say() AND backtest.py's legitimate comment" if not bad
       else "; ".join(bad))


def _selftest_retracted_scanner():
    """A NEGATIVE CONTROL. The first case is the exact sentence that shipped on the demo page.

    Without this the check is a green light that has never been shown to be capable of turning red,
    and this file already contains two scars from exactly that (gotcha #78: my verification check was
    vacuous twice in one session).
    """
    LIVE = ("knowing about it <strong>costs 22.8 h/year</strong> ... "
            "<strong>Recirculation awareness buys safety, not hours.</strong>")
    cases = [
        ("the sentence that actually shipped is caught", LIVE, False, True),
        ("...and is caught in HTML too", "<p>" + LIVE + "</p>", True, True),
        ("the corrected wording is clean",
         "knowing about it buys 22.8 h/year and cuts breaches 3.7x", False, False),
        ("a markdown line documenting the retraction is allowed",
         "CORRECTED 2026-08-23: this used to say buys safety, not hours, and it was wrong.",
         False, False),
        ("an HTML COMMENT documenting the retraction is allowed",
         "/* it read: Recirculation awareness buys safety, not hours */ const x = 1;", True, False),
        ("an unrelated retraction is still caught",
         "the solver absorbs heat into buildings, a known defect", False, True),
    ]
    bad = []
    for name, txt, is_html, want_hit in cases:
        if bool(_retracted_hits(txt, is_html)) != want_hit:
            bad.append(name)
    ck("the retracted-claim scanner passes its own %d-case control" % len(cases), not bad,
       "including the exact sentence that shipped on the ladder panel" if not bad
       else "; ".join(bad))


def check_retracted_claims():
    """A RETRACTED SENTENCE MUST NOT SURVIVE ON A SURFACE A READER MEETS.

    The three instances above were all found by a human reading the page, never by a check, and the
    reason is structural: everything mechanical in this tree re-reads NUMBERS. `audit.py` verifies 77
    figures against the files that produced them and would have passed all three defects, because in
    every case the figure was right and the words around it were wrong.

    Comments are stripped from the page before scanning, deliberately: `index.html` now carries the
    retracted wording inside comments that explain the correction, and flagging those would be the
    same false positive that forced `check_retired_constants` to become AST-based (gotcha #55b).
    """
    print("\n5b. RETRACTED CLAIMS -- must not survive on any surface a reader meets")
    _selftest_retracted_scanner()
    _selftest_python_retraction_scanner()
    targets = [("demo/index.html", os.path.join(DEMO, "index.html")),
               # ADDED 2026-08-23. This was the gap: demo/README.md carried "costs hours and buys
               # safety" and a retired "about 595 h/year" while sitting UNSCANNED, and HANDOFF 9.1b
               # says in as many words that a judge opens the demo before reading anything. The
               # front door of the thing being judged was the one document nothing read.
               ("demo/README.md", os.path.join(DEMO, "README.md")),
               ("README.md", os.path.join(ROOT, "README.md")),
               ("RECIRCULATION-DEFENCE.md", os.path.join(ROOT, "RECIRCULATION-DEFENCE.md")),
               ("READING-THE-AGENT.md", os.path.join(ROOT, "READING-THE-AGENT.md"))]
    scanned, hits, missing = 0, [], []
    for label, path in targets:
        if not os.path.exists(path):
            # A SKIP IS NOT A PASS (gotcha #74). Every target here is a committed file, so an
            # absent one means it was deleted or this path is wrong -- either way the surface is
            # unscanned, and silently continuing would report PASS for a file nothing read.
            missing.append(label)
            continue
        scanned += 1
        # Through the SHARED helper, so the negative control above and the real scan below can
        # never diverge -- a control that tests different code from the check proves nothing.
        for phrase, why in _retracted_hits(open(path, encoding="utf-8").read(),
                                           path.endswith(".html")):
            hits.append("%s: \"%s\" (%s)" % (label, phrase, why))
    ck("every registered reader-facing surface exists to be scanned", not missing,
       "%d surfaces" % scanned if not missing else "MISSING: " + ", ".join(missing))
    ck("no retracted claim appears on a reader-facing surface", not hits,
       "%d phrases x %d surfaces checked" % (len(RETRACTED_CLAIMS), scanned) if not hits
       else "; ".join(hits[:3]))

    # PRINTED PYTHON STRINGS, the surface the four documents above do not cover. agent.py's say()
    # block asserted a registered retraction to the console on every run for weeks.
    py_hits, py_files = [], 0
    for base in (HERE, os.path.join(ROOT, "testing")):
        if not os.path.isdir(base):
            continue
        for nm in sorted(os.listdir(base)):
            if not nm.endswith(".py") or nm in _PY_SCAN_SKIP:
                continue
            py_files += 1
            path = os.path.join(base, nm)
            for phrase, why, ln in _retracted_hits_in_python(
                    open(path, encoding="utf-8").read(), nm):
                py_hits.append("%s:%d \"%s\" (%s)" % (nm, ln, phrase, why))
    ck("no retracted claim is PRINTED or EMITTED by any python string", not py_hits,
       "%d phrases x %d modules, comments and docstrings excluded"
       % (len(RETRACTED_CLAIMS), py_files) if not py_hits else "; ".join(py_hits[:3]))


def check_no_unsuffixed_per_site_artefact():
    """NO PER-SITE ARTEFACT MAY BE REACHED THROUGH THE RAW `demo/` PATH. THE GENERAL RULE.

    THE DEFECT THIS EXISTS FOR, measured 2026-08-24. `plume_uncertainty.spread_table()` cached to
    `os.path.join(DEMO, "spread_table_%s_sd%02d.json")` -- no metro prefix -- and `main()` wrote
    `os.path.join(DEMO, "plume_uncertainty.json")` the same way. Both are derived from
    `rise_table(mode)` (this site's committed geometry) and `load_hours()` (this site's station
    record), so both are per-site MEASUREMENTS. The first site built wrote them; every site built
    afterwards read them back. Measured consequence, from each site's own rebuilt calibration:

        ashburn  own margin 0.10616 C   (it wrote the file, so it was correct by luck)
        chicago  own margin 0.17034 C   was shipping 0.10616  ->  37.7 % TOO NARROW
        dulles   own margin 0.14614 C   was shipping 0.10616  ->  27.4 % TOO NARROW

    Both errors are in the UNSAFE direction: the plume half of the safety bound was tighter than
    those sites' own geometry justifies. Nothing caught it. Check 6c compares a registered list of
    values; check 6d compares panels; check 6e (`check_wind_is_this_sites_own`) was written for the
    WIND record specifically, after the same failure shape hit `direction_sweep.load_wind()`.

    SO THIS IS 6e's GENERAL FORM, and it is a SOURCE check rather than a data check on purpose: a
    data check can only compare the sites that happen to be built, while the rule being enforced is
    "a per-site artefact is addressed per-site", which is true or false in the source regardless of
    how many sites exist. That matters at national scale, where nobody will be reading artefacts.
    """
    print("\n6f. NO PER-SITE ARTEFACT IS ADDRESSED THROUGH THE RAW demo/ PATH")

    # Basenames (or `%`-template stems) that are DERIVED PER SITE. Kept as an explicit list, not a
    # pattern, so adding a per-site artefact is a deliberate act that shows up in review.
    PER_SITE = ("trace.json", "backtest.json", "rolling.json", "money.json", "explanations.json",
                "ticker.json", "scenarios.json", "report.pdf", "plume_uncertainty.json",
                "rise_table_", "spread_table_", "selected_site.json", "direction_table.json",
                "solver_site_", "refusal_rank.json", "candidates.json")
    # Genuinely GLOBAL files that legitimately live at the raw path: one copy for the whole tree.
    GLOBAL_OK = ("sites.json", "unified_sites.json", "dp_cases.json", "ticker_cases.json",
                 "conformal_cases.json", "national_")

    # `os.path.join(DEMO, "<name>"` / `os.path.join(GEOM, "<name>"` with a literal first segment.
    pat = re.compile(r'os\.path\.join\(\s*(DEMO|GEOM)\s*,\s*(["\'])(.+?)\2')

    # WHICH MODULES THE RULE APPLIES TO, and why this is not a file exclusion.
    # A module that imports `metros` has declared that it operates on "the current site" -- so for
    # it, an unsuffixed per-site path is a bug by definition. A module that does not import `metros`
    # is not claiming to be per-site at all: `audit.py` itself deliberately reads the REFERENCE
    # site's unsuffixed artefacts, because re-checking Ashburn's published numbers is its whole job.
    # Excluding audit.py by NAME would hide any future defect in it (the §9.2c lesson -- excluding a
    # file hides everything else in it); keying on the import means that the moment audit.py becomes
    # metro-aware, it comes into scope automatically.
    # TOP-LEVEL ONLY -- column 0, no leading whitespace. This regex was `^\s*import\s+metros\b`,
    # and the moment THIS FILE gained a function-local `import metros as _M` for a self-test, audit
    # .py counted itself as metro-aware and its own legitimate reference-site reads failed the
    # check. That is the right instinct applied at the wrong granularity: a module that is genuinely
    # metro-aware imports `metros` at MODULE scope, because every function in it needs the current
    # site. A lazy import inside one function is a test fixture, not a declaration that the whole
    # file operates per-site.
    metro_aware = re.compile(r'^import\s+metros\b', re.M)
    offenders, scanned, skipped = [], [], []
    for fn in sorted(os.listdir(HERE)):
        if not fn.endswith(".py"):
            continue
        src = open(os.path.join(HERE, fn), encoding="utf-8").read()
        if not metro_aware.search(src):
            skipped.append(fn)
            continue
        scanned.append(fn)
        for m in pat.finditer(src):
            name = m.group(3)
            if any(g in name for g in GLOBAL_OK):
                continue
            if any(name.startswith(p) or name == p for p in PER_SITE):
                line = src[:m.start()].count("\n") + 1
                offenders.append("%s:%d %s" % (fn, line, name))

    ck("no metro-aware module joins a per-site artefact onto the raw demo/ path",
       not offenders,
       "%d metro-aware modules scanned, all clean (%d non-metro modules out of scope)"
       % (len(scanned), len(skipped)) if not offenders
       else "use M.demo_path/M.geom_path instead: " + "; ".join(offenders[:6]))

    # TWO NEGATIVE CONTROLS, because a check that cannot fail is not a check.
    # (a) the detector must fire on the exact string that shipped -- otherwise an over-eager
    #     GLOBAL_OK entry silently turns the whole thing into a pass.
    probe = 'cp = os.path.join(DEMO, "spread_table_%s_sd%02d.json" % (mode, sd))'
    hit = [m.group(3) for m in pat.finditer(probe)]
    ck("the detector fires on the real defect string (negative control)",
       hit and any(h.startswith("spread_table_") for h in hit),
       "matched %r" % (hit[0] if hit else None))
    # (b) the scan must actually be looking at the pipeline. A filter bug that skipped everything
    #     would leave (a) passing and the real check vacuously green.
    ck("the scan covers the metro-aware pipeline, not an empty set",
       len(scanned) >= 8 and "agent.py" in scanned and "plume_uncertainty.py" in scanned,
       "%d modules incl. %s" % (len(scanned), ", ".join(scanned[:4])))

    # AND THE DATA HALF, for the sites that do exist: each must carry its own calibration, and two
    # sites may not share a plume multiplier -- Dulles shares Ashburn's STATION but not its
    # geometry, so even the deliberate weather control must differ here.
    try:
        sites = [s for s in jload(os.path.join(DEMO, "sites.json"))["sites"] if s.get("offerable")]
    except Exception as ex:
        ck("sites.json readable for the per-site plume check", False, str(ex)[:70])
        return
    mults = {}
    for s in sites:
        k = s["key"]
        p = os.path.join(DEMO, "plume_uncertainty.json" if k == "ashburn"
                         else "%s_plume_uncertainty.json" % k)
        # A STANDALONE FACILITY MUST HAVE **NO** PLUME CALIBRATION, and that is the assertion --
        # not an exemption from one. The calibration fits a margin to the spread of a plume rise;
        # with no neighbour intake there is no rise to have a spread, so a file here would mean a
        # width had been fitted to something that was never computed. `agent`'s own disable path
        # then reports the plume term as off, which is what the trace has to show.
        standalone = (s.get("site_kind") == "standalone")
        if standalone:
            ck("%-9s standalone: NO plume calibration exists, as it must not" % k[:9],
               not os.path.exists(p), "%s absent" % os.path.basename(p))
            t = jload(os.path.join(DEMO, (s.get("artefacts") or {}).get("trace", "")))
            rt = t["cycle"]["rise_tables"]["longest"]
            ck("%-9s standalone: its rise table is zero and names no worst bearing" % k[:9],
               rt["max_rise_c"] == 0.0 and rt["max_rise_bearing"] is None,
               "max %.4f C, bearing %r" % (rt["max_rise_c"], rt["max_rise_bearing"]))
            continue
        if not os.path.exists(p):
            ck("%-9s has its OWN plume calibration on disk" % k, False, "missing %s"
               % os.path.basename(p))
            continue
        d = jload(p)
        ck("%-9s plume calibration names itself, not another site" % k, d.get("metro") == k,
           "metro=%r" % d.get("metro"))
        mults[k] = round(float(d["calibration"]["shipped"]["multiplier"]), 6)
    ck("no two PLUME-MODELLING sites share a multiplier (each is its own geometry's)",
       len(set(mults.values())) == len(mults),
       ", ".join("%s %.4f" % (k, v) for k, v in sorted(mults.items())))


def check_published_numbers():
    print("\n6. PUBLISHED NUMBERS vs WHAT THE CODE NOW WRITES")
    t = jload(os.path.join(DEMO, "trace.json"))
    bt = jload(os.path.join(DEMO, "backtest.json"))
    pu = jload(os.path.join(DEMO, "plume_uncertainty.json"))
    ex = jload(os.path.join(DEMO, "explanations.json"))
    m3 = bt["mondrian"]["3"]
    a03 = [r for r in bt["n56_audit"] if r["step"] == "A sensor_err 0.3 C"][0]
    bw = [r for r in bt["n56_audit"] if r["step"] == "B with plume term"][0]
    bo = [r for r in bt["n56_audit"] if r["step"] == "B plume term REMOVED"][0]
    p47 = pu["calibration"]["47.0"]
    # THE FIVE-YEAR LADDER WAS NEVER IN THIS REGISTRY, AND THAT IS EXACTLY HOW THE INVENTED
    # WET-BULB MARGIN SURVIVED. PLAN.md and HANDOFF.md both quoted "+112.4 h/yr" for the humidity
    # row for a full day after the constant behind it had been condemned, because no test re-read
    # the number (methodology rule 10). Every ladder row is registered now.
    rl = jload(os.path.join(DEMO, "rolling.json"))
    rb = rl["configs"][0]
    ru = [c for c in rl["configs"] if "unconstrained" in c["label"]][0]
    lad = {r["step"][2:]: r for r in bt["n56_audit"] if r["step"].startswith("C ")}
    sen = bt["sensitivity"]
    srow = {(r["axis"], str(r["value"])): r for r in sen["rows"]}
    sbase = [r for r in sen["rows"] if r["is_base"]]

    # SESSION G. The money figure is a PRODUCT of a measured hours row and two SOURCED conversion
    # factors, so the registry pins the factors -- which come from documents -- and one worked cell.
    # A drifted kW/ton would otherwise change every dollar on the page silently.
    mn = jload(os.path.join(DEMO, "money.json"))
    mcell = [c for c in mn["cells"]
             if c["family"] == "five-year ladder"
             and c["hours_label"].startswith("+ notice 3 h")
             and c["kw_per_ton"] == 0.576 and c["cents_per_kwh"] == 8.72]

    reg = [
        ("N-26 pooled coverage 65.6 %", t["cycle"]["pooled_coverage"], 0.6559, 1e-3),
        # PNNL-29674 Table 82, water cooled > 300 tons -- read off PDF page 236
        ("ASHRAE 90.1-2019 centrifugal > 300 tons, full load 0.576 kW/ton",
         [c["kw_per_ton"] for c in mn["chiller_efficiencies_swept"]
          if c["label"] == "centrifugal, full load"][0], 0.576, 0),
        ("ASHRAE 90.1-2019 centrifugal > 300 tons, IPLV 0.549 kW/ton",
         [c["kw_per_ton"] for c in mn["chiller_efficiencies_swept"]
          if c["label"] == "centrifugal, IPLV.IP"][0], 0.549, 0),
        # EIA table_4.pdf, 2024 Total Electric Industry
        ("EIA 2024 Virginia commercial 8.72 cents/kWh",
         [p_["cents"] for p_ in mn["electricity_prices_swept"]
          if p_["label"] == "Virginia commercial, 2024 annual"][0], 8.72, 0),
        ("1 ton of refrigeration = 3.5168528 kW", mn["kw_per_ton_of_refrigeration"],
         3.5168528420666, 1e-9),
        ("chiller draws 163.78 kW per MW of IT at 0.576 kW/ton",
         mn["chiller_kw_per_mw_it"]["centrifugal, full load"], 163.782798, 1e-5),
        ("the priced headline is about $5,794 per MW of IT per year",
         mcell[0]["usd_per_mw_it_per_year"] if mcell else -1, 5794.0, 2.0),
        ("FortyGuard tiles per call 17,862", t["fields"]["2026-08-16_forecast"]["n_tiles"],
         17862, 0),
        ("facade-to-facade gap 60.3 m", t["site"]["facade_gap_m"], 60.3, 1e-9),
        # TWO PIPELINES, TWO NUMBERS, REGISTERED SEPARATELY. `direction_sweep.py` solves every
        # bearing at ONE median wind speed; `agent.rise_table()` solves a 72 x 8 bearing-by-speed
        # grid and maxes over both. So the worst-case rise is 0.35477 C on the first and 0.35497 C
        # on the second, and the published "0.3550 C" is the second. This entry used to check only
        # the direction table, against 0.3550, with a 5e-4 tolerance wide enough to swallow the
        # difference -- a tolerance doing work that a second registry line should do.
        ("worst plume rise, direction sweep at the median speed",
         t["direction_table"]["modes"]["longest"]["worst"]["rise_c"], 0.35477, 1e-5),
        ("worst plume rise, rise table over the speed grid (the published 0.3550)",
         t["cycle"]["rise_tables"]["longest"]["max_rise_c"], 0.35497, 1e-5),
        ("worst bearing 255 deg, and BOTH pipelines must find it there",
         t["direction_table"]["modes"]["longest"]["worst"]["bearing"],
         t["cycle"]["rise_tables"]["longest"]["max_rise_bearing"], 0),
        ("pooled worst-group coverage 0.7314 at 3 h",
         m3["pooled"]["worst_group"]["coverage"], 0.7314, 1e-3),
        ("pooled groups below target 6 of 24", m3["pooled"]["groups_below_target"], 6, 0),
        ("Mondrian worst-group coverage 0.8794", m3["mondrian_hod"]["worst_group"]["coverage"],
         0.8794, 1e-3),
        ("ACI realised coverage 0.8998", bt["aci"]["3"]["ACI"]["realised_coverage"], 0.8998, 1e-3),
        ("static bound coverage 0.8943", bt["aci"]["3"]["static"]["realised_coverage"],
         0.8943, 1e-3),
        ("ACI rounds 43,260", bt["aci"]["3"]["ACI"]["rounds"], 43260, 0),
        ("N-56 reproduction +65.6 h/yr at sensor 0.3", a03["gain_h_per_year"], 65.6, 0.5),
        # 🔴 THIS ENTRY USED TO READ "plume awareness costs 22.8 h/yr" AND IT PASSED FOR TWO
        # DAYS WHILE THE CLAIM WAS BACKWARDS (gotcha #97). The magnitude was registered; the
        # DIRECTION was not, and the direction was the claim. A registry entry's label is part of
        # what it asserts -- so the three checks below pin the sign, the raw hours and the breach
        # counts, and no relabelling can pass them.
        ("plume awareness WINS 22.8 safe h/yr (sign included)",
         bw["gain_h_per_year"] - bo["gain_h_per_year"], 22.8, 0.5),
        ("...and MORE raw free hours: 17,511 with the term vs 17,462 without",
         bw["agent_free_h"] - bo["agent_free_h"], 49, 0),
        ("...and FEWER breaches: 3 with the term vs 11 without",
         bo["agent_breach_h"] - bw["agent_breach_h"], 8, 0),
        ("plume awareness cuts breaches 0.63 -> 0.17 per 1000",
         bo["agent_breach_per_1000_free_h"], 0.63, 0.02),
        ("fixed plume margin 0.08658 C", p47["fixed_margin_c"], 0.08658, 1e-4),
        ("fixed width hard-quartile coverage 0.9212", p47["fixed_coverage_hard"], 0.9212, 1e-3),
        ("normalized hard-quartile coverage 0.9412", p47["normalized_coverage_hard"],
         0.9412, 1e-3),
        ("normalized easy-quartile margin 0.02980 C", p47["mean_margin_norm_easy_c"],
         0.02980, 1e-4),
        ("spread ratio 34.6x at sigma_dir 47", pu["spread_tables"]["longest_47"]
         ["ratio_max_over_min"], 34.6, 0.1),
        ("Warp peak VRAM 371 MiB", ex["warp_peak_vram_mib"], 371, 0),
        ("explanations verified 1,336", ex["verification"]["hour_explanations"], 1336, 0),
        ("explanation verification failures 0", ex["verification"]["failures"], 0, 0),
        # THE BINDING-CONSTRAINT DISTRIBUTION, registered 2026-08-21 because it had DRIFTED.
        # HANDOFF §7.5 quoted dry-bulb 46.7 / none 32.6 / dew point 11.1 / switch budget 2.8 while
        # the shipped file said 46.8 / 32.7 / 10.7 / 3.0. Small, and §8.2 is the standing rule it
        # breaks: a number in a document that no test re-reads is a number that will drift -- this
        # is the fifth instance. `READING-THE-AGENT.md` teaches these seven to a beginner, which
        # makes them exactly the wrong numbers to leave unregistered.
        ("binding: dry-bulb 46.9 %", _binding_pct(ex, "dry-bulb"), 46.9, 0.05),
        ("binding: nothing binds 32.7 %", _binding_pct(ex, "none"), 32.7, 0.05),
        ("binding: dew point 10.8 %", _binding_pct(ex, "dew point"), 10.8, 0.05),
        ("binding: refusal 6.6 %", _binding_pct(ex, "refusal"), 6.6, 0.05),
        ("binding: switch budget 3.0 %", _binding_pct(ex, "switch budget"), 3.0, 0.05),
        # 🔴 THE AIR-QUALITY GATE NOW BINDS ZERO HOURS, and it is registered as a COUNT for the same
        # reason `minimum dwell` is: "0.1 %" hid that it was two hours, and "0.0 %" would hide that
        # it is now none at all. It moved 2 -> 0 on 2026-08-23 when DIAG-65's response became the
        # 30th env_params day in the corpus and shifted the measured PM2.5 diurnal profile. That is
        # the system behaving correctly -- new measured evidence changing a measured number -- and
        # this registry is what caught it. Report the gate as VACUOUS in this configuration
        # (gotcha #37: a condition can be MET AND MEANINGLESS, and must be reported as both).
        ("binding: air quality, 0 hours of 1,336 -- vacuous here",
         _binding_count(ex, "air quality"), 0, 0),
        # THE VACUOUS ONE, PINNED AS A COUNT rather than a percentage. "0.1 %" hides that it is a
        # single hour, and the honest reading of this row is "one hour in 1,336" (gotcha #37: a
        # condition can be MET AND MEANINGLESS, and must be reported as both).
        ("binding: minimum dwell, 1 hour in 1,336", _binding_count(ex, "minimum dwell"), 1, 0),
        ("API calls at view time 0", t["api_calls_made"], 0, 0),

        # ---- THE FIVE-YEAR LADDER, all five rows, in the order PLAN.md prints them ----------
        ("ladder 1 N-56-like +65.6 h/yr",
         lad["N-56-like: notice 0, skill 1.00, no constraints"]["gain_h_per_year"], 65.6, 0.5),
        ("ladder 2 + switch budget 2, dwell 3 h +85.6",
         lad["+ switch budget 2, min dwell 3 h"]["gain_h_per_year"], 85.6, 0.5),
        ("ladder 3 + SOURCED dew-point gate 15 C +118.8",
         lad["+ dew-point gate 15 C (Green Grid WP#46 p.6)"]["gain_h_per_year"], 118.8, 0.5),
        ("ladder 4 + notice 3 h, skill 0.50 +405.7",
         lad["+ notice 3 h, skill 0.50 (no perfect forecast)"]["gain_h_per_year"], 405.7, 0.5),
        ("ladder 5 + unanchored, 4 offsets rotated -156.0",
         lad["+ unanchored, 4 measured FG offsets rotated"]["gain_h_per_year"], -156.0, 0.5),
        ("ladder 5 unanchored coverage 0.9865",
         lad["+ unanchored, 4 measured FG offsets rotated"]["coverage_agent_bound"], 0.9865, 1e-3),
        ("unanchored costs 561.7 h/yr",
         (lad["+ notice 3 h, skill 0.50 (no perfect forecast)"]["gain_h_per_year"]
          - lad["+ unanchored, 4 measured FG offsets rotated"]["gain_h_per_year"]), 561.7, 1.0),
        # the SOURCED gate is registered as costing about what the invented one did, which is the
        # reason the headline story did not depend on the invented number
        ("dew-point gate row is within 10 h/yr of the retired invented gate's +112.4",
         abs(lad["+ dew-point gate 15 C (Green Grid WP#46 p.6)"]["gain_h_per_year"] - 112.4)
         < 10.0, True, 0),
        ("dew-point gate is NOT vacuous, binds >0 held-out hours",
         lad["+ dew-point gate 15 C (Green Grid WP#46 p.6)"]["humidity_gate_binds_h"] > 0,
         True, 0),

        # ---- THE ONE-AT-A-TIME SENSITIVITY -------------------------------------------------
        ("every BASE axis is swept: 12 axes", len(sen["axes"]), 12, 0),
        ("sensitivity configurations 33", len(sen["rows"]), 33, 0),
        ("sensitivity held-out days 913", sen["held_out_days"], 913, 0),
        ("reversal axes 3 (anchor, bank_mode, switch_budget)", len(sen["reversals"]), 3, 0),
        ("refusal guard costs -3124.4 h/yr at bank_mode=facing",
         srow[("bank_mode", "facing")]["gain_h_per_year"], -3124.4, 1.0),
        ("refusal guard forgoes 7,142 genuinely-safe held-out hours",
         srow[("bank_mode", "facing")]["refused_but_truly_safe_h"], 7142, 0),
        ("switch_budget=1 reverses to -78.0 h/yr",
         srow[("switch_budget", "1")]["gain_h_per_year"], -78.0, 0.5),
        ("incumbent exceeds a budget of 1 on 212 of 913 days",
         srow[("switch_budget", "1")]["incumbent_budget_exceeded_days"], 212, 0),
        # TWO INDEPENDENT ROUTES TO ONE CONFIGURATION. The ladder builds its row 4 by overriding a
        # notice-0 N-56 template; the sensitivity builds the same configuration by overriding
        # BASE. They must land on the identical number to full precision, and every one of the 11
        # `is_base` sensitivity rows must agree too -- that is what makes "held at BASE" checkable
        # rather than asserted.
        ("ladder row 4 == the sensitivity base case, to full precision",
         lad["+ notice 3 h, skill 0.50 (no perfect forecast)"]["gain_safe_h_per_day"],
         sbase[0]["gain_safe_h_per_day"], 0),
        ("ladder row 5 == the sensitivity anchor=none row, to full precision",
         lad["+ unanchored, 4 measured FG offsets rotated"]["gain_safe_h_per_day"],
         srow[("anchor", "none")]["gain_safe_h_per_day"], 0),
        ("all 11 is_base sensitivity rows carry one identical gain",
         len({r["gain_safe_h_per_day"] for r in sbase}), 1, 0),
        # the gate the five-year numbers actually used, read back out of the written file
        ("backtest base case gates on the SOURCED dew-point limit 15.0 C",
         bt["base_case"]["dewpoint_limit_c"], 15.0, 0),

        # ---- ROLLING CONTROL: the present-tense agent and its plan stability ---------------
        ("rolling: split is chronological, not alternating", rl["split"], "chronological", 0),
        ("rolling: 12 h horizon", rl["horizon_h"], 12, 0),
        ("rolling: 913 held-out days simulated", rl["held_out_days_simulated"], 913, 0),
        ("rolling: 21,879 re-plans compared", rb["replans"], 21879, 0),
        ("rolling: 240,252 horizon-hours compared", rb["hours_compared"], 240252, 0),
        ("rolling churn 1.128 %", rb["churn"], 0.011280, 1e-5),
        ("rolling next-hour flip rate 0.873 %", rb["next_hour_flip_rate"], 0.008730, 1e-5),
        ("rolling: 94.08 % of re-plans change nothing",
         rb["replans_with_zero_change"], 0.940811, 1e-5),
        ("rolling: 0.124 of 11 published hours move per re-plan",
         rb["mean_hours_changed_per_replan"], 0.123863, 1e-5),
        ("rolling executed free cooling 14.72 h/day", rb["executed_free_h_per_day"], 14.7152, 5e-3),
        ("rolling breach 0.52 per 1,000 free h", rb["breach_per_1000_free_h"], 0.5210, 1e-3),
        # THE VALIDITY CHECK ON THE NEW PATH. Twelve independently calibrated bounds, and every one
        # must hold on held-out weather. The first implementation scaled the margin by (1-skill)
        # without improving the forecast and put ALL TWELVE at 0.73-0.79 -- this is the check that
        # would have caught it, so it is registered rather than left to a one-off inspection.
        ("rolling: every one of 12 leads covers >= 90 %",
         sum(1 for v in rb["coverage_by_lead"].values() if v < 0.90), 0, 0),
        ("rolling: worst lead coverage 0.9141", min(rb["coverage_by_lead"].values()), 0.914140, 1e-5),
        # the honest negative: the constraints do NOT explain the stability
        ("rolling: constraints barely change churn (ratio 1.00)",
         ru["churn"] / rb["churn"], 1.001107, 1e-4),
        # THE LEAKAGE GUARD, AS AN EXACT IDENTITY. It was a 20.0-24.5 h/day tolerance band, which
        # silently absorbed both the record's 61 missing hours and any real bug. Leads are measured in
        # real hours now (rolling.hour_numbers), so the step count must match exactly.
        ("rolling: hours run == hours expected, exactly",
         rb["hours_run"] - rb["hours_run_expected"], 0, 0),
        ("rolling: 21,880 hours stepped", rb["hours_run"], 21880, 0),
        ("rolling: 23.965 hours per day, i.e. 24 minus the record's own gaps",
         rb["hours_run_per_day"], 23.965, 1e-3),
    ]
    bad = []
    for label, got, want, tol in reg:
        ok = (got == want) if tol == 0 else (abs(float(got) - float(want)) <= tol)
        if not ok:
            bad.append("%s: doc says %s, code says %s" % (label, want, got))
        print("      [%s] %-52s %s" % ("ok" if ok else "STALE", label, got))
    # The SIZE of this registry is itself a published figure -- README.md and HANDOFF.md both
    # promise a reader how many numbers get re-read -- so check 10 reads it from here rather than
    # from a human's memory of it. It has already drifted once, 68 -> 70.
    PUBLISHED_COUNT[0] = len(reg)
    ck("every published headline number still matches the code", not bad,
       "%d checked" % len(reg) if not bad else "; ".join(bad))


def run(cmd, cwd, label, timeout=2400):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        tail = (r.stdout or "").strip().split("\n")[-1][:70]
        return ck(label, r.returncode == 0, tail)
    except Exception as e:
        return ck(label, False, str(e)[:70])


def check_stage_events():
    """THE REASONING TAPE MUST BE CHECKABLE, not merely plausible.

    A ticker is the easiest thing in this project to fake, so the guard is mechanical: no template in
    ticker.py may contain a literal digit, and every digit in the rendered text must trace to a
    payload value. This check re-runs that verification against the SHIPPED file rather than trusting
    the run that wrote it, because a hand-edited artefact is precisely what the digit scan is for.
    """
    print("\n6b. STAGE EVENTS -- no phrase on the reasoning tape was typed")
    sys.path.insert(0, HERE)
    try:
        import ticker as tk
    except Exception as exc:                                              # noqa: BLE001
        ck("ticker.py imports (the digit guard runs at import time)", False, str(exc)[:90])
        return
    p = os.path.join(DEMO, "ticker.json")
    if not os.path.exists(p):
        ck("ticker.json present", False, "run `python ticker.py`")
        return
    tj = jload(p)
    art = {n: jload(os.path.join(DEMO, "%s.json" % n)) for n in ("trace", "backtest", "rolling")}

    bad = {c: "".join(tk.literal_digits(d["template"])) for c, d in tj["templates"].items()
           if tk.literal_digits(d["template"])}
    ck("%d shipped templates, none holding a literal digit" % len(tj["templates"]), not bad,
       "" if not bad else "%d do: %s" % (len(bad), sorted(bad)[:3]))

    fails, counts = tk.verify(tj["system"], art)
    ck("system tape verifies (V1-V5) -- %d numbers re-derived from an independent field"
       % counts["rederived"], not fails, "" if not fails else "%d: %s" % (len(fails), fails[0]))

    ex_fails, _ = tk.verify(tj["hour_tape_example"]["events"])
    ck("shipped hour-tape example verifies", not ex_fails,
       "" if not ex_fails else ex_fails[0])

    v = tj["verification"]
    ck("%s hour-tapes verified in the run that wrote this" % format(v["hour_tapes_checked"], ","),
       v["hour_failures"] == 0 and v["system_failures"] == 0 and v["hour_tapes_checked"] > 0,
       "%d hour failures, %d system failures" % (v["hour_failures"], v["system_failures"]))
    # The tape's own claim about itself has to be true, or the panel is lying about its guarantee.
    ck("ticker.json's stated digit count matches the templates it ships",
       tj["templates_with_literal_digits"] == len(bad) == 0,
       "file says %d, scan finds %d" % (tj["templates_with_literal_digits"], len(bad)))


def check_money_doc():
    """The limits that LEFT the money panel must be IN money-sources.md, and in both copies.

    🔴 A DISCLOSURE THAT MOVES IS ONLY MOVED IF IT ARRIVES. Three blocks came off the money card on
    2026-08-25 -- the 608-cell sweep with its worst cell, the seven-item "What this is NOT", and the
    four parsed sources. `money-sources.md` already existed and was already linked from README, and
    it had drifted: hand-written on 2026-08-20, it carried TWO of the four sources and NONE of the
    seven caveats verbatim. Emptying those elements without this check would have removed five
    sourced limitations and two citations from every reader-facing surface in the project, silently.

    So each item is matched as a string, whitespace-insensitively because markdown wraps. And BOTH
    copies are checked: `demo/money-sources.md` is what the panel's link actually serves (the demo's
    document root is `demo/`, so a link to the repository root 404s), and a served copy that has
    fallen behind the root one is exactly the drift this check exists to catch.
    """
    print("\n12. THE MONEY DISCLOSURES, moved off the panel and therefore checked in the document")
    mn = jload(os.path.join(DEMO, "money.json"))
    squeeze = lambda s: re.sub(r"\s+", " ", s).strip()
    for label, path in (("root", os.path.join(ROOT, "money-sources.md")),
                        ("served", os.path.join(DEMO, "money-sources.md"))):
        if not os.path.exists(path):
            ck("money-sources.md exists (%s copy)" % label, False, path)
            continue
        txt = squeeze(open(path, encoding="utf-8").read())
        miss = [x for x in mn["not_claimed"] if squeeze(x) not in txt]
        ck("%-6s copy carries all %d stated limits" % (label, len(mn["not_claimed"])),
           not miss, "all present" if not miss
           else "MISSING %d: %s" % (len(miss), miss[0][:70]))
        srcs = (mn["sources"]["electricity_price"] + mn["sources"]["chiller_efficiency"]
                + mn["sources"]["context_only"])
        smiss = [s["title"] for s in srcs if squeeze(s["title"]) not in txt]
        ck("%-6s copy carries all %d sources" % (label, len(srcs)),
           not smiss, "all present" if not smiss
           else "MISSING %d: %s" % (len(smiss), smiss[0][:70]))
    a = os.path.join(ROOT, "money-sources.md")
    b = os.path.join(DEMO, "money-sources.md")
    if os.path.exists(a) and os.path.exists(b):
        same = open(a, encoding="utf-8").read() == open(b, encoding="utf-8").read()
        ck("the served copy is byte-identical to the root one", same,
           "identical" if same else "THEY DIFFER -- run src/write_money_doc.py")


def check_live_chain():
    """THE LIVE PATH MUST BE VERIFIABLE WITHOUT THE NETWORK, or it cannot be in the audit at all.

    `live.py selftest` covers the parts that are live-INDEPENDENT: ISO8601 run-length expansion of
    the NWS grid series, the four-way vendor classifier (`ok` / `completed_but_empty` /
    `terminal_<status>` / `stalled_in_processing`), the local-time window construction, and the
    margin provenance -- including that the margin is read from FortyGuard's OWN measured residuals
    and NOT from rolling.py's persistence-calibrated per-lead margins, and that a site with no
    day-pairs of its own reports a borrowed bound.

    It cannot prove that FortyGuard answers. Nothing offline can, and on the day this was written
    the vendor was accepting jobs and never completing them.
    """
    print("\n11. THE LIVE PATH, verified offline")
    run([sys.executable, os.path.join(HERE, "live.py"), "selftest"], HERE,
        "live chain self-test (zero network calls)")


def check_self_tests():
    print("\n7. MODULE SELF-TESTS")
    for f in ("conformal.py", "environment.py", "plume_uncertainty.py", "explain.py"):
        run([sys.executable, f], HERE, "%-22s self-test" % f)
    run([sys.executable, "ticker.py", "selftest"], HERE, "%-22s self-test" % "ticker.py")
    run([sys.executable, "money.py", "selftest"], HERE, "%-22s self-test" % "money.py")
    run([sys.executable, "report.py", "selftest"], HERE, "%-22s self-test" % "report.py")


def check_cross_language():
    print("\n8. CROSS-LANGUAGE CONSISTENCY (browser vs Python)")
    run([sys.executable, "gen_dp_cases.py"], DEMO, "regenerate DP cases")
    run([sys.executable, "gen_ticker_cases.py"], DEMO, "regenerate stage-event tapes")
    run([sys.executable, "gen_conformal_cases.py"], DEMO, "regenerate conformal cases")
    for js, label in (("verify_browser_agent.js", "scheduler agrees"),
                      ("verify_browser_decision.js", "decisions agree, bound included"),
                      ("verify_browser_explanation.js", "reasons agree"),
                      ("verify_browser_ticker.js", "stage-event sentences agree, character for "
                                                   "character"),
                      ("verify_browser_conformal.js", "conformal quantile agrees EXACTLY")):
        run(["node", js], DEMO, "%-38s" % label)


# ---- the spend-claim scanner, shared by check 9 and its own negative control ---------------
_SPEND_MARKER = re.compile(r"stale|supersed|previous|was\b|used to|predat|historical|earlier|"
                           r"drift|by three calls|no test re-read|said", re.I)
_SPEND_PCT = re.compile(r"(\d{1,2}\.\d{2})\s*%")


def _unmarked_spend_claims(txt, paid_calls, pct_of_plan):
    """Every total-spend claim in `txt` that is neither current nor marked as history.

    SCANNED BY PARAGRAPH, NOT BY LINE, and that is not a detail. Markdown wraps, so gotcha #93's
    own entry puts "WAS WRONG BY THREE CALLS" on one line and the figures it is quoting on the next
    -- and a line scanner therefore reported the gotcha documenting the drift as the drift itself.
    `check_front_door_figures` had already learned this and collapses whitespace for the same
    reason. A paragraph is also how a reader meets the number.

    WHAT COUNTS AS A TOTAL-SPEND CLAIM. The first version was greedy and flagged "11 calls, 46,420
    credits" -- a true statement about ONE live run -- and "13 calls", the meter reconciliation that
    recovered a historical count. Neither claims a total. A tool that cries wolf trains you to
    ignore it (gotcha #47), so the rule is the SHAPE OF A TOTAL: a call count is a total-spend claim
    only when the same paragraph also states a plan percentage to two decimals. That is exactly the
    form that drifted -- "61 CALLS / 257,420 / 12.87 %" -- and nothing else in these documents uses
    it.
    """
    units = []
    for para in re.split(r"\n\s*\n", txt):
        # A markdown table is many independent claims in one paragraph, so its rows are split back
        # out -- otherwise one marked row would excuse every row beside it.
        units.extend(para.splitlines() if para.lstrip().startswith("|") else [para])
    bad = []
    for ln in units:
        if _SPEND_MARKER.search(ln):
            continue
        pcts = _SPEND_PCT.findall(ln)
        plan_ctx = re.search(r"of\s+(?:the\s+)?plan|spen[dt]|remaining", ln, re.I)
        for pc in pcts:
            if plan_ctx and abs(float(pc) - pct_of_plan) > 0.005:
                bad.append('"%s %%" (current: %.2f %%)' % (pc, pct_of_plan))
        if not pcts:
            continue                       # no percentage in this unit: not a total claim
        for m in re.finditer(r"(\d{1,4})\s*(?:paid\s+)?calls?\b", ln, re.I):
            if int(m.group(1)) != paid_calls and int(m.group(1)) > 9:
                bad.append('"%s" (current: %d calls)' % (m.group(0), paid_calls))
    return sorted(set(bad))


def _selftest_spend_scanner():
    """A NEGATIVE CONTROL, because a document check that cannot fail is not checking the document.

    The real stale header is the first case: it sat in HANDOFF.md and check 9 passed over it for a
    day, because the check required a NAMED superseded string and nobody had named this one. If this
    scanner cannot see it, it has the same hole.
    """
    NOW_CALLS, NOW_PCT = 65, 13.71
    cases = [
        ("the real stale header is caught",
         "**SPEND IS 61 CALLS / 257,420 / 12.87 %.** Never quote from memory.", True),
        ("the current figure is not flagged",
         "**Spent to date** 274,300 = 65 calls = 13.71 % of the plan.", False),
        ("a per-run count with no plan percentage is not a total claim",
         "One 12-hour run = 11 calls, 46,420 credits, and 8 returned nothing.", False),
        ("a stale figure the text marks as superseded is allowed",
         "The previous line said 42,200 = 10 calls = 2.11 %, and it was stale by three calls.",
         False),
        ("a wrapped paragraph keeps its marker",
         "A SPEND FIGURE WAS WRONG BY THREE CALLS.\n    Section 12.2 quoted 10 calls = 2.11 %.",
         False),
        ("one marked table row does not excuse the row beside it",
         "| a | superseded: 2.11 % of the plan |\n| b | 12.87 % of the plan, 61 calls |", True),
    ]
    bad = []
    for name, txt, want_hit in cases:
        got = bool(_unmarked_spend_claims(txt, NOW_CALLS, NOW_PCT))
        if got != want_hit:
            bad.append(name)
    ck("the spend-claim scanner passes its own %d-case control" % len(cases), not bad,
       "including the exact header it failed to catch on 2026-08-21" if not bad
       else "; ".join(bad))


def check_api_spend():
    """THE SUBMISSION'S API-USAGE FIGURES, RE-DERIVED FROM THE METER.

    This check exists because the number DID drift. HANDOFF 12.2 said "42,200 = 10 calls = 2.11 %"
    while `testing/results/n26_manifest.json` recorded a meter of 1,945,140 -- the collector had
    fired three more attempts and no test re-read the figure. That is methodology rule 10 exactly:
    a number in a document that nothing re-reads is a number that will drift.

    So the ledger is regenerated from saved usage-endpoint readings (zero API calls, no key read)
    and the documents are checked against it BOTH WAYS: the current figure must appear, and the
    superseded one must NOT. Requiring the new string alone would pass a document that quoted both.
    """
    print("\n9. API SPEND -- the ledger, and the documents that quote it")
    # The negative control runs FIRST. A document check that cannot fail is not checking the
    # document, and this one demonstrably could not: it passed over a stale header for a day.
    _selftest_spend_scanner()
    led = os.path.join(ROOT, "testing", "api_usage_ledger.py")
    if not os.path.exists(led):
        ck("api spend ledger present", False, "testing/api_usage_ledger.py is missing")
        return
    run([sys.executable, led, "--json"], ROOT, "regenerate the spend ledger from meter readings")
    u = jload(os.path.join(ROOT, "testing", "results", "api_usage.json"))

    # The reconciliation itself. `issued - remaining` must be a whole number of heatmap calls at
    # the measured price; a remainder means a differently-priced endpoint was billed or a reading
    # is wrong, and either way no call count may be published.
    # THE PLAN IS MIXED-PRICE SINCE 2026-08-23. Every billed call used to be a 4,220 heatmap and the
    # exact division WAS the proof; DIAG-65 then spent 2,900 on `env_params` and this check fired,
    # correctly. The proof is preserved rather than weakened: non-heatmap spend is subtracted at its
    # own measured price and the heatmap remainder must still be exactly zero.
    # ⚠ THE DETAIL LINE REPORTS THE REMAINDER, it does not assert it. The first version ended with
    # the literal ", remainder 0" -- so on the run where the remainder was NOT zero, the failure
    # message said it was. A check whose own explanation contradicts its verdict is worse than a
    # check with no explanation.
    ck("spend reconciles exactly at the measured prices",
       u["whole_call_remainder"] == 0,
       "%d heatmap x %s + %d other (%s) = %s spent, remainder %s"
       % (u["heatmap_calls"], format(u["heatmap_credits"], ","),
          u["other_endpoint_calls"], format(u["other_endpoint_credits"], ","),
          format(u["spent"], ","), format(u["whole_call_remainder"], ",")))
    ck("the ledger's own arithmetic closes",
       u["issued"] - u["remaining"] == u["spent"]
       and u["attributed_credits"] + u["unattributed_credits"] == u["spent"],
       "%s issued - %s remaining = %s spent" % (format(u["issued"], ","),
                                               format(u["remaining"], ","),
                                               format(u["spent"], ",")))
    # Classification must stay a partition: evidenced-with-data + evidenced-zero + unidentified
    # has to equal the call count, or the floor/ceiling either side of it means nothing.
    # The partition must be over METER-STAMPED calls only. It used to include the collector's
    # recorded ATTEMPT count, which held while every failure was billed 4,220 -- and broke on
    # 2026-08-20 when the vendor started failing for free, because an unbilled attempt was being
    # counted against a billed-call total. It passed anyway: the unattributable bucket absorbed the
    # error. A partition check that a miscount can satisfy is not checking the partition.
    # THE PARTITION IS OVER HEATMAP CALLS, not over every billed call, and that is not a loophole.
    # Its three buckets are "returned tiles" / "returned zero tiles" / "unattributable" -- categories
    # that only mean something for an endpoint that returns tiles. `env_params` returns hourly
    # arrays, so folding it in would make the partition close by accident rather than by evidence.
    # It is checked separately, on its own count, so nothing is left out of the accounting.
    ck("the call classification partitions the BILLED HEATMAP calls",
       u["calls_returning_data"] + u["calls_returning_zero_tiles_meter_stamped"]
       + u["calls_not_individually_identified"] == u["heatmap_calls"],
       "%d with data + %d meter-stamped zero + %d unattributable = %d heatmap calls"
       % (u["calls_returning_data"], u["calls_returning_zero_tiles_meter_stamped"],
          u["calls_not_individually_identified"], u["heatmap_calls"]))
    ck("every billed call is accounted for across all endpoints",
       u["heatmap_calls"] + u["other_endpoint_calls"] == u["paid_calls"],
       "%d heatmap + %d other = %d total"
       % (u["heatmap_calls"], u["other_endpoint_calls"], u["paid_calls"]))
    ck("collector attempts are reported apart from billed calls",
       u.get("collector_attempts_are_not_all_billed") is True
       and isinstance(u.get("collector_recorded_failed_attempts"), int),
       "%d recorded attempts, not summed into the %d billed calls"
       % (u.get("collector_recorded_failed_attempts", -1), u["paid_calls"]))

    # Now the documents. Every figure a reader can quote from API-USAGE.md is registered here.
    current = [format(u["spent"], ","), format(u["remaining"], ","),
               "%.2f %%" % u["pct_of_plan"], str(u["paid_calls"])]
    # Superseded TOTALS, listed explicitly. Add to this list whenever spend changes -- that is the
    # point: the stale figure has to be named to be caught.
    #
    # Two numbers are deliberately NOT banned bare, because each has a legitimate current use and
    # `check_nan_writers`' own lesson applies -- a check that cries wolf is worse than no check:
    #   * `1,957,800` was the stale "remaining" total, but it is ALSO the true meter reading after
    #     the Chicago call, and it appears as such in the itemised ledger.
    #   * `42,200` was the stale "spent" total, but it is ALSO the ledger's honest upper bound on
    #     credits that bought no data.
    # So the ban is on the stale CLAIM, not on the digits: the phrasing that asserts them as
    # totals. `2.11 %` has no legitimate current use at all and is banned outright.
    superseded = ["2.11 %", "42,200 = 10", "10 calls = 2.11", "42,200 credits", "Remaining **1,957,800**"]
    for doc in ("API-USAGE.md", "HANDOFF.md"):
        path = os.path.join(ROOT, doc)
        if not os.path.exists(path):
            ck("%s exists" % doc, False, "missing")
            continue
        txt = open(path, encoding="utf-8").read()
        missing = [s for s in current if s not in txt]
        ck("%-22s quotes the current spend" % doc, not missing,
           "all of %s present" % ", ".join(current) if not missing
           else "MISSING %s" % ", ".join(missing))
        # HANDOFF.md is allowed to name a superseded figure, because it documents the drift as a
        # gotcha and naming it is the whole lesson. API-USAGE.md is judge-facing and may not.
        if doc == "API-USAGE.md":
            stale = [s for s in superseded if s in txt]
            ck("%-22s carries no superseded figure" % doc, not stale,
               "none of %s present" % ", ".join(superseded) if not stale
               else "STALE %s still quoted" % ", ".join(stale))

        # ---- AND THE SAME CHECK WITHOUT A HAND-MAINTAINED LIST -------------------------
        # THE HAND-MAINTAINED LIST ABOVE HAS THE DEFECT IT WAS BUILT TO CATCH. Found 2026-08-21:
        # HANDOFF.md's own summary block read "SPEND IS 61 CALLS / 257,420 / 12.87 %" while section
        # 12.2 read 65 / 274,300 / 13.71 %. Check 9 passed, because it requires the CURRENT strings
        # to be present (they were, in 12.2) and a NAMED list of superseded ones to be absent -- and
        # 257,420 had never been added to that list. A stale figure has to be named to be caught, so
        # the first stale figure of a new generation is never caught. That is gotcha #93's lesson
        # recurring inside the check written for gotcha #93.
        #
        # So the shape of the claim is matched instead of its value: any "<n> calls" or "<x> %" that
        # reads as a spend claim must be the current one, unless its own line marks it as history.
        # HANDOFF documents its own drift on purpose, which is why the marker escape exists rather
        # than a blanket ban.
        MARK = _SPEND_MARKER
        # WHAT COUNTS AS A TOTAL-SPEND CLAIM, and the first version of this got it wrong by being
        # greedy. It flagged "11 calls, 46,420 credits" -- a true statement about ONE live run --
        # and "13 calls", the meter reconciliation that recovered a historical call count. Neither
        # claims a total. A tool that cries wolf trains you to ignore it (gotcha #47), so the rule
        # is the SHAPE OF A TOTAL: a call count is only a total-spend claim when the same line also
        # states a percentage of the plan to two decimals. That is exactly the form that drifted --
        # "61 CALLS / 257,420 / 12.87 %" -- and it is the form nothing else in these documents uses.
        bad = _unmarked_spend_claims(txt, u["paid_calls"], u["pct_of_plan"])
        ck("%-22s quotes no OTHER call count or plan percentage" % doc, not bad,
           "shape-matched, not listed: nothing but %d calls / %.2f %% claimed"
           % (u["paid_calls"], u["pct_of_plan"]) if not bad
           else "UNMARKED STALE FIGURE: %s" % "; ".join(sorted(set(bad))[:3]))


def _run_all_steps():
    """`run_all.STEPS`, imported lazily so a syntax error there fails the step count rather than the
    whole audit at import time. Returns an empty list if it cannot be read, which fails the figure
    check loudly instead of quietly reporting whatever the README happens to say."""
    try:
        sys.path.insert(0, HERE)
        import run_all                                              # noqa: PLC0415
        return run_all.STEPS
    except Exception:
        return []


def check_front_door_figures():
    """THE ROOT README IS THE FIRST THING A JUDGE READS, so its numbers get the same treatment.

    Every figure quoted there is re-derived from the emitted JSON and matched as the FORMATTED
    STRING the reader sees -- not the float behind it. That is deliberate: `+406 h/yr` and
    `405.6555` are the same measurement but only one of them is on the page, and it is the one on
    the page that can be wrong.

    The failure figures are registered alongside the flattering ones ON PURPOSE. If the coverage
    number ever drifts upward, or the "-156 h/yr, the agent LOSES" row quietly disappears, this
    check fails -- so the honest rows cannot rot away while the headline rows stay fresh.
    """
    print("\n10. THE FRONT DOOR -- README.md figures vs the emitted JSON")
    path = os.path.join(ROOT, "README.md")
    if not os.path.exists(path):
        ck("README.md exists", False, "the repository has no root README")
        return
    # WHITESPACE-INSENSITIVE, because markdown wraps. "70 published figures" is written in the
    # README as "70 published" + a line break + "figures", and an exact-substring check reported
    # a correct document
    # as stale -- the same cry-wolf failure `check_nan_writers` was rewritten to avoid.
    txt = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())
    t = jload(os.path.join(DEMO, "trace.json"))
    bt = jload(os.path.join(DEMO, "backtest.json"))
    rl = jload(os.path.join(DEMO, "rolling.json"))
    ex = jload(os.path.join(DEMO, "explanations.json"))
    tk = jload(os.path.join(DEMO, "ticker.json"))
    rb = rl["configs"][0]
    # The 3 h-notice Mondrian block, which the demo's removed "what is not claimed" panel read.
    MOND3 = bt["mondrian"]["3"]
    C = [r for r in bt["n56_audit"] if r["step"].startswith("C ")]
    # ANCHOR-BASED, NOT INDEX-BASED. The shipped row used to be addressed as `C[-2]` and the
    # unanchored stress test as `C[-1]`, which silently encoded "the unanchored row is last". It is
    # a field on the row, so ask for it: adding a rung to the ladder would otherwise re-point both
    # registrations at the wrong configurations without any check noticing.
    C_SHIP = [r for r in C if r["anchor"] != "none"][-1]
    C_UNANCH = [r for r in C if r["anchor"] == "none"]
    # THE FORECAST'S OWN SHARE, derived exactly as drawLadder() derives it for the page, so the
    # README, the panel and this check cannot disagree. Measured by REMOVING the forecast: at skill
    # 0 the agent has nothing beyond debiased persistence, so the difference is what FortyGuard
    # contributes. Registered because it is now the README's headline claim about the vendor.
    SK = [r for r in bt["sensitivity"]["rows"] if r["axis"] == "skill"]
    SK0 = [r for r in SK if float(r["value"]) == 0.0][0]
    SKB = [r for r in SK if r.get("is_base")][0]
    FG_SHARE = (SKB["gain_h_per_year"] - SK0["gain_h_per_year"]) / SKB["gain_h_per_year"]
    NT = sorted((r for r in bt["sensitivity"]["rows"] if r["axis"] == "notice_h"),
                key=lambda r: float(r["value"]))
    # THE SCALE BLOCK AND THIS SITE'S FOOTPRINT, read from the manifest that computed them rather
    # than recomputed here -- the point of registering a derived figure is to catch the PRODUCER
    # drifting, and a checker that redoes the arithmetic itself cannot see that.
    import metros as _MS                                                 # noqa: PLC0415
    SITES_J = jload(os.path.join(DEMO, "sites.json"))
    SCALE = SITES_J.get("scale") or {}
    SITE_FOOT = next((s.get("footprint_m2") for s in SITES_J["sites"]
                      if s["key"] == _MS.DEFAULT_METRO), None)
    # MECHANICAL RUNTIME, both controllers, on the shipped row. Same derivation as the page's tile.
    _sr = [r for r in C if r["anchor"] != "none"][-1]
    _hpd = bt["hours"] / bt["days"]
    _H = _hpd * _sr["test_days"]
    RUNTIME = {"mech_agent": _H - _sr["agent_safe_free_h"],
               "mech_inc": _H - _sr["incumbent_safe_free_h"]}
    mn = jload(os.path.join(DEMO, "money.json"))
    MONEY_ROW = [c["usd_per_mw_it_per_year"] for c in mn["cells"]
                 if c["hours_label"].startswith("+ notice 3 h")]
    RT = jload(os.path.join(DEMO, "rise_table_longest.json"))

    want = [
        ("free cooling delivered",  "%s h/yr" % format(round(rb["executed_free_h_per_day"]
                                                             * 365.25), ",")),
        ("held-out days",           "%s held-out days" % format(rl["held_out_days_simulated"], ",")),
        ("chiller-hours avoided",   "+%d h/yr" % round(C_SHIP["gain_h_per_year"])),
        # THE UNANCHORED LOSS IS NO LONGER A README HEADLINE, and that is a deliberate editorial
        # change rather than a figure going unchecked. The measurement is untouched in
        # backtest.json and four other registrations below still re-derive it (-156.0 h/yr, its
        # 0.9865 coverage, its per-day gain, and the 561.7 h/yr difference). What was dropped is the
        # REQUIREMENT that the README quote it as a top-line result: it rotates four measured
        # forecast-vs-history LEVEL differences across five years of KIAD ASOS, and this project's
        # own finding is that the difference reads as an offset between two endpoints rather than as
        # forecast error. Headlining it therefore attributed an integration detail to forecast
        # quality. It now lives in the panel's disclosure with that attribution stated.
        ("the forecast's share",    "%.1f %%" % (100 * FG_SHARE)),
        ("gain with NO forecast",   "+%.1f h/yr" % SK0["gain_h_per_year"]),
        # ONE ENTRY PER RUNG, IN PLAIN ASCII. The first version registered the whole rendered
        # string, arrows and middots included -- and a FAILING check would then have tried to print
        # U+2192 to this repo's cp1252 console and died inside its own error path, which is the
        # bug `bump_spend_docs` already carries a scar for. Per-rung is also more precise: it names
        # which lead time drifted instead of failing on the whole sentence.
        ("notice 0 h",              "+%.1f" % NT[0]["gain_h_per_year"]),
        ("notice 1 h",              "+%.1f" % NT[1]["gain_h_per_year"]),
        ("notice 3 h",              "+%.1f" % NT[2]["gain_h_per_year"]),
        ("notice 6 h",              "+%.1f" % NT[3]["gain_h_per_year"]),
        ("plan stability",          "%.1f %%" % (100 * rb["replans_with_zero_change"])),
        ("re-plan count",           "%s re-plans" % format(rb["replans"], ",")),
        ("coverage, and its FAILURE", "%.1f %%" % (100 * t["cycle"]["pooled_coverage"])),
        ("hours of real weather",   "%s hours" % format(bt["hours"], ",")),
        ("swept scenarios",         "%s swept scenarios" % format(t["cases"]["all_mechanical"]
                                                                 ["n_total"], ",")),
        ("explanations verified",   "%s explanations with 0 verification failures"
                                    % format(ex["verification"]["hour_explanations"], ",")),
        ("tape templates",          "%d templates contain not one literal digit" % tk["n_templates"]),
        # SELF-REFERENTIAL BY DESIGN, and it has to run LAST for that to work: this function adds
        # exactly one check of its own, so the total a reader is promised is what has been counted
        # so far plus one. Anything cleverer (writing the count to a file and reading it back next
        # run) reports yesterday's number as today's.
        ("audit check count",       "%d audit checks" % (len(PASSES) + len(WARNS) + len(FAILS) + 1)),
        ("published-number count",  "%d published figures" % PUBLISHED_COUNT[0]),
        # THE REBUILD'S OWN STEP COUNT, registered because it had drifted into TEN places at once:
        # README said 20, HANDOFF's header said 22, HANDOFF section 3.1 said 20, and the real
        # number was 22. Nothing re-read any of them, so each new step made the drift worse. Read
        # from `run_all.STEPS` itself -- importing it is safe, the module does nothing at import
        # time and guards main() behind __name__. "Register it or do not write it."
        ("run_all step count",      "%d steps" % len(_run_all_steps())),
        # THE COMMERCIAL AND "USEFUL AI" FIGURES ADDED FOR THE JUDGING CRITERIA. They are the
        # numbers a reader is most likely to quote back at us, so they get the same treatment as
        # the hours: re-derived from the emitted JSON, matched as the formatted string on the page.
        ("$/MW-IT/yr floor", "$%s" % format(round(min(MONEY_ROW)), ",")),
        ("$/MW-IT/yr ceiling", "$%s" % format(round(max(MONEY_ROW)), ",")),
        ("money cells swept", "%d cells" % len(MONEY_ROW)),
        # THE 30 MW ILLUSTRATION IS GONE, replaced by the site's own MEASURED footprint. It was the
        # only unsourced number in that table -- a round figure I picked -- and it is now a
        # derivation with a measured half. Registered more thoroughly than it was, not less: both
        # ends of the density, the national footprint it divides, the per-site footprint, and both
        # ends of the resulting dollar range. A derived figure drifts exactly as easily as a read
        # one, and this one has more moving parts than the thing it replaced.
        ("national footprint measured", "%s m²" % format(int(SCALE["national_footprint_m2"]), ",")),
        ("national average IT load", "%s MW" % format(int(SCALE["national_it_mw_average"]), ",")),
        ("density, average load", "%d W/m²" % round(SCALE["w_per_m2_average_load"])),
        ("density, installed", "%s W/m²" % format(int(round(SCALE["w_per_m2_installed"])), ",")),
        ("the shipped site's footprint", "%s m²" % format(int(SITE_FOOT), ",")),
        # round(), NOT "%d" -- %d TRUNCATES, so 60.55 MW registered as "60" while the README quite
        # correctly said 61. A display figure is rounded; a check that truncates fails a document
        # that is right.
        ("the shipped site in MW",
         "**%d–%d MW**" % (round(SITE_FOOT * SCALE["w_per_m2_average_load"] / 1e6),
                           round(SITE_FOOT * SCALE["w_per_m2_installed"] / 1e6))),
        ("the shipped site in dollars",
         "$%s – $%s per year" % (format(int(round(SITE_FOOT * SCALE["w_per_m2_average_load"] / 1e6
                                                 * min(MONEY_ROW), -3)), ","),
                                 format(int(round(SITE_FOOT * SCALE["w_per_m2_installed"] / 1e6
                                                  * max(MONEY_ROW), -3)), ","))),
        # THE SCALE-FREE HEADLINE, which is now the first row of that table and the one the pitch
        # leads with. Mechanical hours are (hours in the scored days) minus (safe free-cooling
        # hours), and the day total uses the record's own MEASURED hours-per-day rather than 24 --
        # the station does not report every hour, and assuming it does understates the share.
        ("chiller runtime cut", "%.1f %%" % (100 * (RUNTIME["mech_inc"] - RUNTIME["mech_agent"])
                                            / RUNTIME["mech_inc"])),
        ("incumbent chiller hours", "%s h" % format(int(round(RUNTIME["mech_inc"])), ",")),
        ("agent chiller hours", "%s" % format(int(round(RUNTIME["mech_agent"])), ",")),
        ("the LLM was declined with room to spare",
         "**%d MiB peak of %s available**" % (ex["warp_peak_vram_mib"],
                                              format(ex["gpu_total_mib"], ","))),
        ("no local model was used", "local_model_used: false"),
        ("GPU solve count and time",
         "**%d coupled advection–diffusion solves**" % RT["n_solves"]),
        ("GPU solve seconds", "**NVIDIA Warp in %.2f s**" % RT["solve_seconds"]),
        ("pairs needed vs held", "**9 calibration day-pairs; 4 exist.**"),
        ("attainable ceiling at n=4", "n/(n+1) = **80 %**"),
        # THE "WHAT IS NOT CLAIMED" DISCLOSURE MOVED OFF THE DEMO PAGE 2026-08-26, and these five
        # figures moved with it. On the page they were rendered live from backtest.json, so nothing
        # could go stale; in a markdown file they are prose, and section 8.2 of HANDOFF says what
        # happens to a number no test re-reads -- it has happened five times in this project. So
        # they are registered here, re-derived from the same block the panel used to read.
        # These are ROWS IN ONE CHECK, not checks of their own: the whole `want` list feeds a single
        # ck() below, so adding them does not move the audit's self-reported check count.
        ("pooled coverage looks fine on average",
         "**%.2f %%** overall" % (100 * MOND3["pooled"]["overall"])),
        ("the worst hour it hides",
         "**%.2f %%**" % (100 * MOND3["pooled"]["worst_group"]["coverage"])),
        ("pooled hours under nominal",
         "**%d of %d**" % (MOND3["pooled"]["groups_below_target"],
                           MOND3["mondrian_hod"]["n_groups"])),
        ("Mondrian-by-hour lifts the worst hour",
         "**%.2f %%**" % (100 * MOND3["mondrian_hod"]["worst_group"]["coverage"])),
        ("Mondrian hours under nominal",
         "**%d of %d**" % (MOND3["mondrian_hod"]["groups_below_target"],
                           MOND3["mondrian_hod"]["n_groups"])),
        # THE REJECTED VARIANT IS REGISTERED TOO, for the same reason the failure rows above are:
        # "we tried the more elaborate stratification and it was worse" is only credible while the
        # numbers that say so are still checkable.
        ("season over-stratifies, worst group",
         "**%.2f %%**" % (100 * MOND3["mondrian_hod_x_season"]["worst_group"]["coverage"])),
        ("season groups under nominal",
         "**%d of %d**" % (MOND3["mondrian_hod_x_season"]["groups_below_target"],
                           MOND3["mondrian_hod_x_season"]["n_groups"])),
    ]
    missing = [(lbl, s) for lbl, s in want if re.sub(r"\s+", " ", s) not in txt]
    ck("every README figure matches the emitted JSON", not missing,
       "%d figures checked" % len(want) if not missing
       else "; ".join("%s: expected \"%s\"" % (l, s) for l, s in missing))


def main():
    print("=" * 78)
    print("AUDIT -- INTAKE-ARBITER, whole tree")
    print("=" * 78)
    check_dead_code()
    check_nan_writers()
    check_css_comments()
    check_duplicate_element_ids()
    check_plume_fields()
    check_page_javascript_parses()
    check_decision_precision()
    check_duplicate_constants()
    check_retired_constants()
    check_retracted_claims()
    check_act_stage()
    check_stage_events()
    check_sites_actually_differ()
    check_panels_are_per_site()
    check_wind_is_this_sites_own()
    check_no_unsuffixed_per_site_artefact()
    check_national_registry()
    check_published_numbers()
    check_self_tests()
    check_cross_language()
    check_api_spend()
    check_live_chain()
    check_money_doc()
    check_front_door_figures()          # LAST: it counts every check above it, including its own
    print("\n" + "=" * 78)
    print("AUDIT: %d passed, %d warnings, %d FAILURES" % (len(PASSES), len(WARNS), len(FAILS)))
    for n, d in FAILS:
        print("   FAIL  %s  %s" % (n, d))
    for n, d in WARNS:
        print("   WARN  %s  %s" % (n, d))
    print("=" * 78)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
