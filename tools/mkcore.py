# -*- coding: utf-8 -*-
"""Generate AGENTIC-ARBITER/core/ by MECHANICALLY lifting the agent out of demo/index.html.

WHY MECHANICALLY. This is decision-critical code: 500 DP cases, 789 conformal assertions, 1,336
explanations and 2,037 event sentences are checked against the Python agent, and all four corpora pass
today. Hand-transcribing 17 KB of it would introduce exactly the class of defect this repository spends
2,215 checks catching. So the bodies are lifted BYTE FOR BYTE by the same brace-matching extractor the
verifiers use, and the only edits are the ones this script makes explicitly and prints.

WHAT CHANGES, AND IT IS THE WHOLE POINT OF THE EXERCISE. Today the five node verifiers find these
functions by `html.indexOf('function decide(')` and then have to STUB `$()`, because the agent reaches
into the DOM for its configuration. That is a verification harness working around a design problem.
After this, the functions are importable and take their inputs as arguments:

    global T   ->  parameter `trace`
    global TK  ->  parameter `tk`
    global US  ->  parameter `us`
    $('#c_x')  ->  stays in the PAGE, in cfg(), which is a DOM adapter and belongs there

NOTHING IS DELETED FROM THE PAGE BY THIS SCRIPT. The inline copy stays exactly where it is, so that
verify_core_equivalence.mjs can run OLD against NEW on identical inputs and prove they agree before
anything is swapped. An extraction that cannot be proved equivalent is a rewrite.
"""
import hashlib
import io
import json
import os
import re

# ---- paths, derived from THIS FILE rather than hard-coded --------------------------------------
# These were absolute (r"D:\\FGHackathon\\...") while the generators lived in a scratch directory
# outside the repository. That made the committed generated files UNREPRODUCIBLE by anyone else: the
# manifests said "generated_by: scratchpad/mkresults.py" and no such file was tracked, so a drift
# report could be read but not acted on. Derived from __file__, the tools work from any checkout.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AA = os.path.join(ROOT, "AGENTIC-ARBITER")
DEMO = os.path.join(AA, "demo")
CORE = os.path.join(AA, "core")
os.makedirs(CORE, exist_ok=True)

s = io.open(os.path.join(DEMO, "index.html"), encoding="utf-8", newline="").read()
k = s.rfind("<script")
BODY = s[s.index(">", k) + 1: s.index("</script>", k)]


PAGE_SRC = {}      # function name -> the exact page source this run extracted


def extract(name):
    """The same brace-matcher the verifiers use, so what lands here is what they check today."""
    i = BODY.find("function " + name + "(")
    if i < 0:
        raise SystemExit("!! function %s not found" % name)
    d, started, j = 0, False, i
    while j < len(BODY):
        c = BODY[j]
        if c == "{":
            d += 1
            started = True
        elif c == "}":
            d -= 1
            if started and d == 0:
                j += 1
                break
        j += 1
    PAGE_SRC[name] = BODY[i:j]
    return BODY[i:j]


# ---- the one-liners that are consts in the page and belong in core as exports -------------------
FMT = re.search(r"^const fmt = .*?;$", BODY, re.M).group(0)

EDITS = []          # every substitution, printed so none of them is silent


def thread(src, name, subs):
    """Apply the named global->parameter substitutions, asserting each one actually fires.

    `old` is a REGEX, not a literal: the whole point is `T`, a word-boundary match, so that the
    global `T` is threaded without also rewriting the T inside `TK`, `TRUE` or a string. An earlier
    version of this helper re.escape()d the pattern and therefore searched for the six literal
    characters `T`, found none, and stopped. Word boundaries are the reason this is a regex."""
    for old, new in subs:
        hits = list(re.finditer(old, src))
        if not hits:
            raise SystemExit("!! %s: no occurrence of %r to thread" % (name, old))
        # 🔴 REFUSE TO EDIT INSIDE A STRING LITERAL. This is the guard for the defect that shipped
        # once: `\bUS\b` matched inside `'en-US'` and silently rewrote a locale tag, because a
        # hyphen and a quote are both non-word characters so a word boundary sits between them.
        spans = string_spans(src)
        inside = [h for h in hits if any(a <= h.start() < b for a, b in spans)]
        if inside:
            ctx = src[max(0, inside[0].start() - 40):inside[0].end() + 40]
            raise SystemExit("!! %s: %r matches inside a string literal, refusing to substitute.\n"
                             "   at ...%s...\n"
                             "   If the identifier really is used there, narrow the pattern."
                             % (name, old, " ".join(ctx.split())))
        src = re.sub(old, new, src)
        EDITS.append((name, old, new, len(hits)))
    return src


def string_spans(src):
    """(start, end) of every STRING literal in a JS fragment, with comments excluded.

    Classifies as it walks, because the three contexts nest in only one direction: a quote inside a
    comment is prose, and a comment marker inside a string is text. Getting that backwards is what
    made an earlier version refuse a legitimate substitution in decide() and point at a sentence.

    Only STRING spans are returned. Substituting an identifier inside a COMMENT is allowed on purpose:
    once decide()'s parameter is called `trace`, the comment that says `T.cases.fg_offsets` should say
    so too. Regex literals are not modelled; a `/` starting one is treated as code, which can only
    cause a refusal that names itself, never a silent edit."""
    spans, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        # comments first: they swallow quotes
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"`":
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c or (c != "`" and src[j] == "\n"):
                    break
                j += 1
            spans.append((i, min(j, n)))
            i = j + 1
            continue
        i += 1
    return spans


HEAD = """/* AGENTIC-ARBITER -- %s
   ============================================================================================
   GENERATED by tools/mkcore.py, lifted byte for byte out of demo/index.html's inline script
   by the same brace-matching extractor the node verifiers use. Do not hand-edit until the page has
   been switched over to import it; until then demo/index.html holds the live copy and
   verify_core_equivalence.mjs asserts the two agree on every case in all four corpora.

   THE ONLY DELIBERATE CHANGE from the inline original is that the three artefact globals the page
   kept in scope are now ARGUMENTS. That is what makes these functions importable at all, and it is
   why the verifiers no longer need to stub the DOM to test the agent.
   ============================================================================================ */

"""

# ================================================================================================
#  core/format.mjs -- the one formatter the decision and the explanation both print through
# ================================================================================================
fmt_mod = (HEAD % "core/format.mjs") + """/* `fmt` is shared by decide() and explainHour(), and it is the reason a bound of 6.4 C reads the
   same way in the schedule and in the sentence that explains the schedule. One copy, imported. */
export """ + FMT + "\n"
io.open(os.path.join(CORE, "format.mjs"), "w", encoding="utf-8", newline="\n").write(fmt_mod)

# ================================================================================================
#  core/config.mjs -- the shape of a configuration, and the coercions that produce it
# ================================================================================================
cfgsrc = extract("cfg")
# The DOM read becomes a callback. Everything else about the function is untouched, which is the
# point: the eleven coercions below decide whether `offday` is "0" or 0, and that must not be
# reproduced by hand in four different test files.
before = 'const v=id=>$(id).value;'
if cfgsrc.count(before) != 1:
    raise SystemExit("!! cfg() no longer reads the DOM the way this transform expects")
cfgsrc = cfgsrc.replace(before, 'const v=id=>get(id);')
cfgsrc = cfgsrc.replace("function cfg()", "function cfgFromStrings(get)", 1)
EDITS.append(("cfg", "$(id).value", "get(id)", 1))
cfg_mod = (HEAD % "core/config.mjs") + """/* 🔴 THE CONTRACT, NOT THE CONTROL. `get` is a callback that returns the STRING for a control id, so
   the page passes `id => $(id).value` and a test passes `id => String(row[...])`. Both then run the
   identical eleven coercions below.
   That matters more than it looks. A <select> always yields a string, so `offday` is "0" and not 0,
   and `dp`/`aq` are null exactly when the control reads "off". A test that assembled this object from
   scenarios.json's raw JSON types would hand the agent a number where the page hands it a string, and
   nothing would report the difference. */

export """ + cfgsrc + "\n"
io.open(os.path.join(CORE, "config.mjs"), "w", encoding="utf-8", newline="\n").write(cfg_mod)

# ================================================================================================
#  core/conformal.mjs -- already pure, lifted with no edits at all
# ================================================================================================
CONF = ["cfMinN", "cfAttainable", "cfQuantileIndex", "cfSplit"]
conf_mod = (HEAD % "core/conformal.mjs") + """/* ALL FOUR WERE ALREADY PURE. Not one substitution was needed in this file, which is the strongest
   thing that can be said about the conformal implementation: the split, the quantile index, the
   attainable-coverage ceiling and the minimum-n floor never touched a global or the document. */

"""
for n in CONF:
    conf_mod += "export " + extract(n) + "\n\n"
io.open(os.path.join(CORE, "conformal.mjs"), "w", encoding="utf-8", newline="\n").write(conf_mod)

# ================================================================================================
#  core/agent.mjs -- H0, plan, reactive, decide
# ================================================================================================
agent_mod = (HEAD % "core/agent.mjs")
for n in ("H0", "plan", "reactive"):
    agent_mod += "export " + extract(n) + "\n\n"

dec = extract("decide")
# `decide` reached for TWO things outside itself: the per-site trace global `T`, and cfg(), which is
# the DOM adapter. Both become parameters, and the second one is the substantive change in this whole
# exercise: it is why verify_browser_decision.js currently has to define a fake `$()` before it can
# test the agent at all. The config arrives as an argument now, so the agent has no opinion about
# where it came from -- a <select>, a React state hook, or a literal in a test.
sig = re.match(r"function decide\(([^)]*)\)", dec)
args = sig.group(1).strip()
if args:
    raise SystemExit("!! decide() gained parameters upstream; revisit this signature rewrite")
dec = dec.replace(sig.group(0), "function decide(k, trace)", 1)
dec = thread(dec, "decide", [
    (r"\bT\b", "trace"),
    # `const k=cfg(), ds=...` -- k is the parameter now, so only ds is declared here.
    (r"const k=cfg\(\), ds=", "const ds="),
])
agent_mod += ("/* 🔴 `decide` GAINED ONE PARAMETER, `trace`, and lost its reach into the module-scope\n"
              "   global `T`. That global is the per-site artefact the page happens to have loaded, which\n"
              "   meant the agent's behaviour depended on page state rather than on its arguments -- the\n"
              "   reason verify_browser_decision.js has to stub the browser before it can test anything. */\n")
agent_mod += "export " + dec + "\n"
io.open(os.path.join(CORE, "agent.mjs"), "w", encoding="utf-8", newline="\n").write(agent_mod)

# ================================================================================================
#  core/explain.mjs
# ================================================================================================
ex_mod = (HEAD % "core/explain.mjs")
ex_mod += "export " + extract("explainHour") + "\n"
io.open(os.path.join(CORE, "explain.mjs"), "w", encoding="utf-8", newline="\n").write(ex_mod)

# ================================================================================================
#  core/ticker.mjs -- tkFixed, tkRender, tkFormat, tkEvent, tickerFor
# ================================================================================================
tk_mod = (HEAD % "core/ticker.mjs")
for n in ("tkFixed", "tkRender"):
    tk_mod += "export " + extract(n) + "\n\n"

# 🔴 tkFormat IS PURE, and an earlier version of this generator wrongly decided it was not.
# `\bUS\b` matched the `US` inside `toLocaleString('en-US')`, so the "dependency on the national
# registry" was a locale tag, and threading it rewrote the tag to 'en-us'. Emitted unchanged.
tkf = extract("tkFormat")
tk_mod += ("/* PURE, and verified so: the only `US` in this function is the locale tag in\n"
           "   toLocaleString('en-US'). It reads no global. */\n")
tk_mod += "export " + tkf + "\n\n"

for n in ("tkEvent", "tickerFor"):
    src = extract(n)
    m = re.match(r"function %s\(([^)]*)\)" % n, src)
    a = m.group(1).strip()
    src = src.replace(m.group(0), "function %s(%s, tk)" % (n, a) if a else "function %s(tk)" % n, 1)
    src = thread(src, n, [(r"\bTK\b", "tk")])
    if n == "tickerFor":
        # 🔴 THE TWELVE CALL SITES. tkEvent's arity changed, and tickerFor calls it twelve times with
        # two arguments. Without this, `tk` is undefined inside tkEvent, `tk && tk.templates`
        # short-circuits, and all 2,037 event sentences throw "no template". Bind the parameter once
        # and rename the calls: a plain identifier substitution, rather than appending a third
        # argument across twelve multi-line calls full of nested braces and strings.
        head = src.index("{") + 1
        src = (src[:head]
               + "\n  /* GENERATED: binds the ticker artefact for the twelve tkEvent calls below, so"
                 " the\n     substitution that carries it is an identifier rename rather than twelve"
                 " bracket-matched\n     argument insertions. */\n"
                 "  const _ev = (c, v) => tkEvent(c, v, tk);\n"
               + src[head:])
        src = thread(src, n, [(r"\btkEvent\(", "_ev(")])
        # the binding itself must survive the rename
        src = src.replace("const _ev = (c, v) => _ev(c, v, tk);",
                          "const _ev = (c, v) => tkEvent(c, v, tk);", 1)
    tk_mod += "export " + src + "\n\n"
io.open(os.path.join(CORE, "ticker.mjs"), "w", encoding="utf-8", newline="\n").write(tk_mod)

# ================================================================================================
print("core/ generated in %s" % CORE)
for f in sorted(os.listdir(CORE)):
    print("   %-16s %6d bytes" % (f, os.path.getsize(os.path.join(CORE, f))))
print()
print("EVERY SUBSTITUTION MADE (none is silent):")
for name, old, new, n in EDITS:
    print("   %-12s %-8s -> %-8s  x%d" % (name, old, new, n))

# ================================================================================================
#  charts/primitives.mjs -- the shared layer under all 31 panels
# ================================================================================================
CHARTS = os.path.join(os.path.dirname(CORE), "charts")
os.makedirs(CHARTS, exist_ok=True)

PRIMS = ["motionOK", "getCssVar", "fitCanvas", "casePath", "chipText", "sparkSVG", "countUpText"]
ch = (HEAD % "charts/primitives.mjs") + """/* THE LAYER UNDER EVERY PANEL, and the only part of the 3,621 lines of drawing code that is worth
   lifting verbatim. The 31 draw* functions are panel renderers: each one writes innerHTML as well as
   painting canvas, so each has to be REBUILT as a component rather than moved. These seven do not:
   they are primitives, they are shared, and a React chart component needs all of them on day one. */

"""

# The two small constants the primitives close over, lifted from the page.
for pat, why in ((r"^const DPR_CAP = 2;.*$",
                  "fitCanvas caps the device-pixel-ratio here"),
                 (r"^const EDGE = \{[^}]*\};.*$",
                  "casePath reads this to case a mark in its colourblind-safe edge tone")):
    m = re.search(pat, BODY, re.M)
    if not m:
        raise SystemExit("!! could not find %s" % pat)
    ch += "/* %s */\nexport %s\n\n" % (why, m.group(0).strip())

for n in PRIMS:
    ch += "export " + extract(n) + "\n\n"

# 🔴 THE CANVAS FONT TABLE, RESOLVED FROM THE TOKENS INSTEAD OF DUPLICATING THEM.
ch += """/* ---- THE CANVAS FONT TABLE ------------------------------------------------------------------
   🔴 RESOLVED FROM THE CSS TOKENS, NOT DUPLICATED FROM THEM. index.html declares CFACE/CMONO/CBODY
   as string literals repeating the font stacks in --font-display/--font-mono/--font-body, and its own
   comment concedes the problem: "Keep the two in step by hand; there is no mechanical guard available
   and pretending otherwise is the drift this codebase keeps documenting."
   A guard does exist; it just was not reachable there. `getCssVar` sits 3,700 lines below CF in the
   page, so CF could not call it at declaration time. In a module the order is ours, and making CF an
   object of GETTERS defers the lookup to first use -- after the stylesheet is parsed, and with no
   change at any of the 40 fillText call sites, which still write `g.font = CF.label`.
   Cached because getComputedStyle is not free and a chart sets its font per label. Fonts do not
   change with the theme, so the cache never needs invalidating. */
let _F = null;
const faces = () => (_F || (_F = {
  face: getCssVar('--font-display'),
  mono: getCssVar('--font-mono'),
  body: getCssVar('--font-body')
}));

export const CF = {
  get tick()       { return '9px '      + faces().mono; },  /* densest axis figures */
  get axis()       { return '10px '     + faces().mono; },  /* tick and gridline figures */
  get axisStrong() { return '600 10px ' + faces().face; },  /* the one emphasised axis LABEL */
  get label()      { return '11px '     + faces().face; },  /* series names, compass letters */
  get message()    { return '13px '     + faces().body; }   /* empty and loading states */
};
"""
io.open(os.path.join(CHARTS, "primitives.mjs"), "w", encoding="utf-8", newline="\n").write(ch)
print()
print("charts/primitives.mjs: %d bytes, %d primitives + DPR_CAP + EDGE + a token-resolved CF"
      % (len(ch), len(PRIMS)))

# ================================================================================================
#  DERIVED CROSS-MODULE IMPORTS
# ================================================================================================
# 🔴 NOT HAND-MAINTAINED, and the reason is a defect this pass exists to prevent. explainHour() calls
# plan(), which lives in agent.mjs; the hand-written import list in explain.mjs had only `fmt`, and
# the 1,336-explanation corpus died with `ReferenceError: plan is not defined`. The dependency scan
# that designed these modules deliberately ignored references BETWEEN core functions, because it was
# answering "where does the core end", not "what does each file need".
#
# So: every core export is a known name. Scan each module for the ones it uses and does not itself
# declare, and generate the import lines. Deliberately liberal about strings -- a name inside a
# string literal yields a dead import, which is harmless, whereas a missing one is a ReferenceError
# in the middle of the agent.
EXPORTS = {}
for fn in os.listdir(CORE):
    if not fn.endswith(".mjs"):
        continue
    txt = io.open(os.path.join(CORE, fn), encoding="utf-8", newline="").read()
    for m in re.finditer(r"^export (?:function\s+(\w+)|const\s+(\w+))", txt, re.M):
        EXPORTS[m.group(1) or m.group(2)] = fn

added = []
for fn in sorted(os.listdir(CORE)):
    if not fn.endswith(".mjs"):
        continue
    p = os.path.join(CORE, fn)
    txt = io.open(p, encoding="utf-8", newline="").read()
    own = {n for n, f in EXPORTS.items() if f == fn}
    # 🔴 COMMENTS STRIPPED FIRST. format.mjs's header says "`fmt` is shared by decide() and
    # explainHour()", and scanning that as a use made format.mjs import both -- a circular import
    # generated out of prose. A name in a comment is never a use. Strings are left in: a name inside
    # one yields a dead import, which is harmless, whereas being clever risks missing a real use.
    code = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
    code = re.sub(r"//[^\n]*", " ", code)
    used = set(re.findall(r"\b([A-Za-z_]\w*)\b", code))
    need = {}
    for name in sorted(used & set(EXPORTS)):
        if name in own:
            continue
        need.setdefault(EXPORTS[name], []).append(name)
    if not need:
        continue
    lines = ["/* Imports DERIVED by mkcore.py from the names this file actually uses. See the note in",
             "   the generator: a hand-written list here already cost the explanation corpus once. */"]
    for src_fn in sorted(need):
        lines.append('import { %s } from "./%s";' % (", ".join(need[src_fn]), src_fn))
    block = "\n".join(lines) + "\n\n"
    # insert after the header comment block
    k = txt.index("*/\n") + 3
    txt = txt[:k] + "\n" + block + txt[k:].lstrip("\n")
    io.open(p, "w", encoding="utf-8", newline="\n").write(txt)
    added.append((fn, {k2: v for k2, v in need.items()}))

print()
print("DERIVED IMPORTS:")
for fn, need in added:
    for src_fn, names in sorted(need.items()):
        print("   %-14s <- %-14s %s" % (fn, src_fn, ", ".join(names)))
if not added:
    print("   (none needed)")

# ================================================================================================
#  THE PROVENANCE MANIFEST
# ================================================================================================
# 🔴 WHAT THE DRIFT GATE READS. testing/verify_core_matches_page.py asserts both hashes below, so a
# hand edit to either copy fails until this generator is re-run. It replaced a first design that
# declared the permitted differences as exact diff RUNS -- which asserted against difflib's chunking
# rather than against the code, and broke on `cfg` -> `cfgFromStrings` for that reason alone.
def _fn_from_module(name):
    # Both generated directories, so charts/primitives.mjs comes under the same gate as core/.
    cands = [(os.path.join(CORE, f), "core", f) for f in sorted(os.listdir(CORE))
             if f.endswith(".mjs")]
    cands += [(os.path.join(CHARTS, f), "charts", f) for f in sorted(os.listdir(CHARTS))
              if f.endswith(".mjs")]
    for full, dname, fn in cands:
        t = io.open(full, encoding="utf-8", newline="").read()
        if ("export function %s(" % name) in t:
            i = t.index("export function %s(" % name) + len("export ")
            d, started, j = 0, False, i
            while j < len(t):
                c = t[j]
                if c == "{":
                    d += 1
                    started = True
                elif c == "}":
                    d -= 1
                    if started and d == 0:
                        j += 1
                        break
                j += 1
            return fn, t[i:j], dname
    return None, None, None


sha = lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest()
ops_by_fn = {}
for name, old, new, n in EDITS:
    ops_by_fn.setdefault(name, []).append("%s -> %s  (x%d)" % (old, new, n))

manifest = {
    "_what": "Provenance for AGENTIC-ARBITER/core/. Written by tools/mkcore.py; read by "
             "testing/verify_core_matches_page.py. page_sha256 is the function as extracted from "
             "demo/index.html, core_sha256 is the function as emitted here. If either side is edited "
             "by hand the gate fails until the generator is re-run.",
    "functions": {},
}
for name in sorted(set(PAGE_SRC) | set()):
    modfile, coresrc, dname = _fn_from_module("cfgFromStrings" if name == "cfg" else name)
    if coresrc is None:
        continue
    manifest["functions"][name if name != "cfg" else "cfgFromStrings"] = {
        "page_name": name,
        "dir": dname,
        "module": modfile,
        "page_sha256": sha(PAGE_SRC[name]),
        "core_sha256": sha(coresrc),
        "page_chars": len(PAGE_SRC[name]),
        "core_chars": len(coresrc),
        "substitutions": ops_by_fn.get(name, []),
    }
io.open(os.path.join(CORE, "_transform.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print()
print("PROVENANCE MANIFEST: core/_transform.json, %d functions"
      % len(manifest["functions"]))
for k in sorted(manifest["functions"]):
    v = manifest["functions"][k]
    print("   %-16s %-14s %5d -> %5d chars, %d substitution(s)"
          % (k, v["module"], v["page_chars"], v["core_chars"], len(v["substitutions"])))
