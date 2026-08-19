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
  7. SELF-TESTS         every module's own suite still passes.
  8. CROSS-LANGUAGE     the browser agrees with Python on decisions AND on reasons.
"""
import ast
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
    for p in ("index.html", "verify_browser_agent.js", "verify_browser_decision.js",
              "verify_browser_explanation.js", "gen_dp_cases.py"):
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
    dead = [(n, w) for n, w in sorted(defs.items()) if refs.get(n, 0) == 0 and n not in extra]
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
    rebuilds every decision from these arrays and matches the Python agent across 2,016
    configurations. That is an end-to-end equality test, which no precision heuristic can beat.
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
        ck("%-38s field %.5f vs audited %.5f C" % (d["metro"] + " " + b + " deg", got, want),
           rel < 0.02, "%.2f %% apart, %d disc cells" % (100 * rel, int(msk.sum())))


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

    reg = [
        ("N-26 pooled coverage 65.6 %", t["cycle"]["pooled_coverage"], 0.6559, 1e-3),
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
        ("plume awareness costs 22.8 h/yr",
         bw["gain_h_per_year"] - bo["gain_h_per_year"], 22.8, 0.5),
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


def check_self_tests():
    print("\n7. MODULE SELF-TESTS")
    for f in ("conformal.py", "environment.py", "plume_uncertainty.py", "explain.py"):
        run([sys.executable, f], HERE, "%-22s self-test" % f)
    run([sys.executable, "ticker.py", "selftest"], HERE, "%-22s self-test" % "ticker.py")


def check_cross_language():
    print("\n8. CROSS-LANGUAGE CONSISTENCY (browser vs Python)")
    run([sys.executable, "gen_dp_cases.py"], DEMO, "regenerate DP cases")
    run([sys.executable, "gen_ticker_cases.py"], DEMO, "regenerate stage-event tapes")
    for js, label in (("verify_browser_agent.js", "scheduler agrees"),
                      ("verify_browser_decision.js", "decisions agree, bound included"),
                      ("verify_browser_explanation.js", "reasons agree"),
                      ("verify_browser_ticker.js", "stage-event sentences agree, character for "
                                                   "character")):
        run(["node", js], DEMO, "%-38s" % label)


def main():
    print("=" * 78)
    print("AUDIT -- INTAKE-ARBITER, whole tree")
    print("=" * 78)
    check_dead_code()
    check_nan_writers()
    check_css_comments()
    check_plume_fields()
    check_decision_precision()
    check_duplicate_constants()
    check_retired_constants()
    check_act_stage()
    check_stage_events()
    check_published_numbers()
    check_self_tests()
    check_cross_language()
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
