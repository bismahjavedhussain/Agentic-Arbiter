# -*- coding: utf-8 -*-
"""Generate AGENTIC-ARBITER/results/engine.mjs by lifting the page's ENGINE out of demo/index.html.

WHAT THIS IS FOR. The React rebuild had only the pick screen, so the "Configure the plant" button led
out of the new UI and back into the old one, and the whole results stage -- 18 cards, the decision
tape, the plume field, the conformal panels, the money sweep and the LIVE agent -- existed nowhere in
it. This lifts the machinery that draws all of that, so the new UI can be the whole product.

WHY MECHANICALLY, AND WHY ONE FILE.
  * MECHANICALLY, for the same reason mkcore.py was: audit.py checks 2,215 things and 77 published
    figures come out of these renderers. Hand-transcribing 200 KB of them would introduce exactly the
    defect class this repository spends its verification budget catching. Bodies are lifted byte for
    byte by the brace-matcher the five node verifiers already use.
  * ONE FILE, because unlike core/'s 22 functions these are NOT pure. core/ could be split into six
    modules only because every global was threaded into a parameter -- `decide(k)` became
    `decide(k, trace)`. The renderers read a shared block of loaded artefacts (T, BT, FIELD, ENV, RL,
    PF, SITES, TK, MN, EX, SITE) and a set of module constants, and threading those through 95
    functions would be a rewrite, not a lift. Keeping them in ONE module lets every reference stay
    literally `T`, so the source is byte-identical and a verifier can prove it.

WHAT IS DELIBERATELY *NOT* LIFTED: the 21 pick-stage functions React replaces (drawUnifiedMap,
searchWire, buildSitePicker, chooseSite, applyMapFilter, setMapView, natReadout, openInspector and
friends), plus boot() and wireChrome() -- React does its own booting and ships its own theme toggle --
plus loadScript(), which fetches maplibre for a map React now owns.
With that fence, the engine calls NOTHING on React's side of the seam: measured, zero crossings.

THE PAGE IS NOT MODIFIED. The inline copy stays exactly where it is, because deleting it would force
index.html to use `<script type="module" src=...>`, and browsers block module loading over file:// --
so a judge could no longer open the page by double-clicking it. Two copies is the price of that, and
verify_results_matches_page.py is what stops them drifting.
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
OUT = os.path.join(AA, "results")
os.makedirs(OUT, exist_ok=True)

page = io.open(os.path.join(DEMO, "index.html"), encoding="utf-8", newline="").read()
k = page.rfind("<script")
BODY = page[page.index(">", k) + 1: page.index("</script>", k)]

NAME = r"[A-Za-z_$][A-Za-z0-9_$]*"
names = sorted(set(
    re.findall(r"^function (" + NAME + r")\s*\(", BODY, re.M)
    + re.findall(r"^async function (" + NAME + r")\s*\(", BODY, re.M)))


def span_of(name):
    m = re.search(r"^(?:async )?function " + re.escape(name) + r"\s*\(", BODY, re.M)
    if not m:
        return None
    i = m.start()
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
    return (i, j)


FSPAN = {}
for n in names:
    sp = span_of(n)
    if sp:
        FSPAN[n] = sp

# ---- the fence -----------------------------------------------------------------------------------
REACT_OWNS = {
    # the national map and the search, which the React pick screen already reimplements
    "drawUnifiedMap", "mapFallback", "setMapView", "applyMapFilter", "mapFilterExpr",
    "filteredSites", "mfDropRender", "buildFilterBar", "wireFilterBar",
    "natReadout", "natClusterReadout", "openInspector", "closeInspector", "inspectorEl",
    "searchWire", "searchRender", "searchMatch", "searchOpen", "searchIndexReady",
    "buildSitePicker", "chooseSite",
    # React boots itself and ships its own theme button; it loads maplibre itself
    "boot", "wireChrome", "loadScript",
}

# stopLive IS AN ENTRY POINT FOR THE SAME REASON runLive IS: the walk below follows CALLS,
# matching `name(`, and an event handler is never called -- it is ASSIGNED
# (`lsb.onclick = stopLive`). Leaving it out lifted the string "api/live/stop/" into the
# engine, inside runLive, while the function itself stayed behind: the bundle threw
# "stopLive is not defined" from buildControls and the whole flow stalled at step 1.
ENTRY = ["drawAll", "runLive", "stopLive", "probeLive", "drawReadyTiles", "setStage",
         "runAgent",
         "loadSite", "loadField", "streamTape", "autofill", "buildControls", "describeSite",
         "siteIsRunnable", "drawPlate", "drawSiteNotes", "wire", "applyTheme", "wireRail",
         "repaintForTheme", "railOnResize", "wireAerial", "styleMapForTheme"]

engine, stack, crossings = set(), list(ENTRY), {}
while stack:
    n = stack.pop()
    if n in engine or n not in FSPAN:
        continue
    engine.add(n)
    src = BODY[FSPAN[n][0]:FSPAN[n][1]]
    for o in names:
        if o == n:
            continue
        if re.search(r"\b" + re.escape(o) + r"\s*\(", src):
            if o in REACT_OWNS:
                crossings.setdefault(o, []).append(n)
            else:
                stack.append(o)

if crossings:
    print("!! SEAM CROSSINGS -- the engine calls into React's side:")
    for o in sorted(crossings):
        print("     %s <- %s" % (o, ", ".join(sorted(set(crossings[o])))))
    raise SystemExit("refusing to generate an engine that depends on code React replaces")

# ---- every top-level declaration, taken WHOLESALE and in page order ------------------------------
# Deliberately not dependency-analysed. A missing const is a ReferenceError at import time, and the
# earlier attempt to detect which ones were "used" got `$` wrong immediately, because \b$\b cannot
# match a name that is not a word character. Constants are cheap; a missing one is not. Take them all.
# 🔴 THE SCANNER HAS TO UNDERSTAND REGEX LITERALS. Without that, the first version read
#     const escHtml = s => String(s).replace(/[&<>"]/g, ...)
# saw the `"` inside the CHARACTER CLASS as the start of a string, never left string mode, and let one
# declaration span 110,308 bytes instead of 80 -- swallowing thirty function bodies, which is how
# `BASEMAP_TILES` came to be declared twice and the module failed to import.
# A `/` is a regex when the previous meaningful character cannot end an expression. That is the
# standard heuristic and it is sufficient here; the assertions below are what make it safe to rely on.
REGEX_OK_BEFORE = set("=(,:[!&|?{};+-*%~^<>") | {""}


def _prev_meaningful(t, i):
    # isspace() rather than a " \t\r\n" literal on purpose: this file is edited through a shell that
    # has mangled backslash escapes eight times in this project (CONTEXT/05-TRAPS.md section 5.4).
    j = i - 1
    while j >= 0 and t[j].isspace():
        j -= 1
    return t[j] if j >= 0 else ""


def _skip_regex(t, i):
    """From the opening slash to just past the flags, honouring [...] classes and escapes."""
    j = i + 1
    incls = False
    while j < len(t):
        c = t[j]
        if c == chr(92):
            j += 2
            continue
        if c == chr(10):
            return None            # a regex cannot span lines: this was division after all
        if incls:
            if c == "]":
                incls = False
        elif c == "[":
            incls = True
        elif c == "/":
            j += 1
            while j < len(t) and t[j].isalpha():
                j += 1
            return j
        j += 1
    return None


DSPAN = []
for m in re.finditer(r"(?m)^(?:const|let|var)\s", BODY):
    i = m.start()
    j, depth, instr = i, 0, None
    while j < len(BODY):
        c = BODY[j]
        if instr:
            if c == chr(92):
                j += 2
                continue
            if c == instr:
                instr = None
        elif c in "'\"" + chr(96):
            instr = c
        elif c == "/" and j + 1 < len(BODY) and BODY[j + 1] == "*":
            e = BODY.find("*" + "/", j + 2)
            j = (e + 2) if e > 0 else len(BODY)
            continue
        elif c == "/" and j + 1 < len(BODY) and BODY[j + 1] == "/":
            e = BODY.find(chr(10), j)
            j = (e if e > 0 else len(BODY))
            continue
        elif c == "/" and _prev_meaningful(BODY, j) in REGEX_OK_BEFORE:
            e = _skip_regex(BODY, j)
            if e:
                j = e
                continue
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth <= 0:
            j += 1
            break
        j += 1
    DSPAN.append((i, j))

# a declaration inside a function body is not top level; drop anything that overlaps a function span
fun_ranges = sorted(FSPAN.values())


def inside_a_function(a, b):
    return any(fa < a and b <= fb for fa, fb in fun_ranges)


DSPAN = [(a, b) for a, b in DSPAN if not inside_a_function(a, b)]

# ---- assertions, because a silent runaway is what produced a module that would not import --------
DSPAN.sort()
_ov = [(DSPAN[i - 1], DSPAN[i]) for i in range(1, len(DSPAN)) if DSPAN[i][0] < DSPAN[i - 1][1]]
if _ov:
    for a, b in _ov[:4]:
        print("!! overlapping declaration spans: [%d,%d) then [%d,%d)" % (a[0], a[1], b[0], b[1]))
        print("     %r" % BODY[a[0]:a[0] + 70])
    raise SystemExit("refusing to emit: a declaration span ran past its own semicolon")

_txt = chr(10).join(BODY[a:b] for a, b in DSPAN)
_names = re.findall(r"(?m)^\s*(?:const|let|var)\s+(" + NAME + r")", _txt)
_dup = sorted({d for d in _names if _names.count(d) > 1})
if _dup:
    raise SystemExit("refusing to emit: %s declared more than once at top level: %s"
                     % (len(_dup), ", ".join(_dup)))

# and no top-level declaration should be enormous; the runaway was 110 KB where the real max is under
# a kilobyte. A ceiling turns the next such bug into a message instead of a broken import.
_big = [(a, b) for a, b in DSPAN if b - a > 4096]
if _big:
    a, b = _big[0]
    raise SystemExit("refusing to emit: declaration of %d bytes at %d, %r"
                     % (b - a, a, BODY[a:a + 70]))

# ---- does any declaration touch the DOM at import time? ------------------------------------------
# It matters: the module is imported before React has rendered the results markup, so a const that
# resolves an element AT LOAD would capture null and every later use would throw. Printed, not
# assumed, and turned into a lazy getter only if one actually appears.
dom_at_load = []
for a, b in DSPAN:
    t = BODY[a:b]
    head = t.split("=", 1)[0]
    if re.search(r"\b(document|querySelector|getElementById)\b", t) and "=>" not in t.split("\n")[0]:
        dom_at_load.append(head.strip()[:60])

# ---- 🔴 THE FENCE HAD A HOLE, AND IT WAS IN THE DECLARATIONS -------------------------------------
# The crossing check above analyses FUNCTIONS. The declarations were taken wholesale, on the argument
# that a missing const is worse than an extra one -- which is true, and which quietly assumed
# declarations do not CALL anything. One of them does:
#
#     const BOOTED = boot();
#
# That is the page's entire bootstrap, executed at module load. Lifting it produced a module that threw
# `ReferenceError: boot is not defined` the moment React imported it, so the app rendered its shell and
# nothing else. The static verifiers all passed: the code was byte-identical, the ids were all present.
# Only driving it in a browser found it.
#
# So two things change. Declarations get the same crossing analysis as functions, and -- more
# importantly -- the ASSERTION MOVES TO THE OUTPUT. Checking the inputs is checking my own reasoning
# about what the inputs contain; checking the emitted text is checking the artefact.
def mask_js(t):
    """Blank comments and string bodies, preserving length, so a name in prose is not a call."""
    out = list(t)
    i, n = 0, len(t)
    BQ, SQ, DQ, BS, SL, ST = chr(96), "'", '"', chr(92), "/", "*"
    while i < n:
        c = t[i]
        if c == SL and i + 1 < n and t[i + 1] == ST:
            j = t.find(ST + SL, i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == SL and i + 1 < n and t[i + 1] == SL:
            j = t.find(chr(10), i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c in (SQ, DQ, BQ):
            j = i + 1
            while j < n:
                if t[j] == BS:
                    j += 2
                    continue
                if t[j] == c:
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                out[k] = " "
            i = min(j + 1, n)
            continue
        i += 1
    return "".join(out)


kept_d, dropped_d = [], []
for a, b in DSPAN:
    code = mask_js(BODY[a:b])
    hit = sorted({f for f in REACT_OWNS
                  if re.search(r"\b" + re.escape(f) + r"\s*\(", code)})
    if hit:
        head = re.match(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)", BODY[a:b])
        dropped_d.append((head.group(1) if head else "?", ", ".join(hit)))
        continue
    kept_d.append((a, b))
DSPAN = kept_d

# ---- emit ----------------------------------------------------------------------------------------
pieces = [(a, b, "decl") for a, b in DSPAN]
pieces += [(FSPAN[n][0], FSPAN[n][1], n) for n in engine]
pieces.sort()

HDR = '''/* AGENTIC-ARBITER -- THE ENGINE, lifted byte for byte out of demo/index.html.
 *
 * GENERATED. Do not edit by hand. Regenerate with tools/mkresults.py and prove it with
 * testing/verify_results_matches_page.py, which run_all.py runs as a step: every function below must
 * be character-for-character identical to the copy still inline in the page.
 *
 * WHY THIS FILE EXISTS. The React rebuild in app/ had only the pick screen, so "Configure the plant"
 * led out of the new UI into the old page, and the results stage -- 18 cards, the decision tape, the
 * plume field, the conformal panels, the money sweep, and the live agent -- was not in the new UI at
 * all. This is that machinery, importable.
 *
 * WHY ONE BIG MODULE RATHER THAN SIX SMALL ONES, which is what core/ got. core/'s 22 functions were
 * made PURE first: every global became a parameter, so `decide(k)` became `decide(k, trace)`. These
 * are renderers. They read a shared block of loaded artefacts and write the DOM by element id, and
 * threading that through %d functions would be a rewrite rather than a lift. Together in one module,
 * every reference stays literally `T`, `SITE`, `PF` -- so the text is byte-identical and provable.
 *
 * WHAT IS NOT HERE: the pick stage. The national map, the search, the site picker, boot() and the
 * theme button all stay behind, because the React app ships its own. Measured: with that fence, this
 * file calls nothing on React's side of the seam.
 *
 * HOW THE VIEW AND THE ENGINE MEET. The engine finds its elements by id and shows or hides cards via
 * `[data-show]`, exactly as it does in the page. React renders markup carrying those ids and those
 * attributes, and does not re-render their children -- the engine owns what is inside them. That is
 * the ordinary pattern for driving a third-party widget from React, and it is what keeps the drawing
 * code unmodified.
 *
 * THE MAP REFERENCES HERE ARE INERT BY DESIGN. repaintForTheme() is guarded with `if(NATMAP)` and
 * NATMAP stays null in this module, because React owns the map instance. So the guard does the work
 * and styleMapForTheme() simply never fires here. React restyles its own map.
 */

''' % len(engine)

parts = [HDR]
for a, b, _tag in pieces:
    parts.append(BODY[a:b])
    parts.append("\n\n")

# ---- THE ADAPTER: the only code in this file that is not the page's -------------------------------
# 🔴 EVERYTHING ABOVE IS LIFTED. THIS IS WRITTEN, and it is kept to three functions so that "what did
# you add?" has a short and checkable answer. verify_results_matches_page.py asserts this text
# CHARACTER FOR CHARACTER, so logic cannot accumulate here later.
#
# WHY IT IS NEEDED AT ALL. `SITES` is a module-level `let`. ES modules export bindings read-only, so
# an importer cannot assign it, and the function that used to fill it was boot() -- which is fenced
# off because React does its own booting. Without a setter the engine would load a site and find no
# registry to look it up in. This is the same shape as core/'s cfgFromStrings(get) adapter: a seam,
# deliberately narrow, named rather than smuggled.
ADAPTER = '''/* ---- THE ADAPTER ----------------------------------------------------------------------------
 * The only code in this file that was not lifted out of the page. Three functions, because the
 * import boundary makes them impossible to do from outside:
 *
 *   attachSites  `SITES` is a module-level `let` and ES module exports are read-only bindings, so
 *                the view cannot assign it. boot() used to fill it, and boot() stays in the page
 *                because it also starts the national map the React app replaces.
 *   currentSite  the view needs the loaded site to title its own chrome; SITE is likewise a `let`.
 *   currentStage the view mirrors the stage in its own layout, and STAGE is likewise a `let`.
 *
 * Nothing here computes anything. If a fourth function ever appears here, that is the moment to ask
 * whether it belongs in the page instead.
 */
export function attachSites(sites){ SITES = sites; return !!(sites && sites.sites); }
export function currentSite(){ return SITE; }
export function currentStage(){ return STAGE; }
'''
# ADAPTER already ends in a newline. Appending another put one byte between it and the export block
# that the manifest hash did not cover, and the verifier correctly reported an edit that had not
# happened. What is hashed and what is written have to be the same string.
parts.append(ADAPTER)

EXPORTS = sorted(n for n in engine)
parts.append("/* ---- the surface React drives ---------------------------------------------------\n"
             " * Everything the engine defines is exported, deliberately. A narrower list would be a\n"
             " * judgement about what the view will need, and getting that judgement wrong is a second\n"
             " * edit to this file later; the module is not a public API, it is one half of one page.\n"
             " */\n")
parts.append("export {\n")
for i in range(0, len(EXPORTS), 5):
    parts.append("  " + ", ".join(EXPORTS[i:i + 5]) + ",\n")
parts.append("};\n")

out = "".join(parts)

# ---- THE ASSERTION THAT MATTERS, ON THE EMITTED TEXT ----------------------------------------------
# Not on the inputs. `const BOOTED = boot();` slipped through every input-side check because those
# checks looked at functions, and this is what refuses to write the file at all. If a fenced name is
# called anywhere in the output and nothing in the output defines it, the module cannot even be
# imported, so this is the difference between a generator failure and a blank screen in a browser.
_code = mask_js(out)
_defined = set(re.findall(r"(?m)^(?:async )?function ([A-Za-z_$][\w$]*)", out))
_defined |= set(re.findall(r"(?m)^export function ([A-Za-z_$][\w$]*)", out))
_leaks = []
for f in sorted(REACT_OWNS):
    if f in _defined:
        continue
    for mo in re.finditer(r"\b" + re.escape(f) + r"\s*\(", _code):
        _leaks.append("%s called at output line %d" % (f, _code[:mo.start()].count(chr(10)) + 1))
        break
if _leaks:
    print("!! THE OUTPUT CALLS FENCED CODE THAT IS NOT IN IT:")
    for x in _leaks:
        print("     %s" % x)
    raise SystemExit("refusing to write a module that cannot import")

io.open(os.path.join(OUT, "engine.mjs"), "w", encoding="utf-8", newline="\n").write(out)

# ---- provenance ----------------------------------------------------------------------------------
man = {
    "generated_by": "tools/mkresults.py",
    "source": "AGENTIC-ARBITER/demo/index.html",
    "note": ("Every entry is a SHA-256 of the exact page text lifted. "
             "verify_results_matches_page.py recomputes these against the page and fails on drift."),
    "functions": {},
    "declarations": len(DSPAN),
    "excluded_react_owns": sorted(REACT_OWNS),
    # Declarations deliberately NOT lifted, because they call fenced code. Recorded so the verifier
    # checks a declared exception instead of me hard-coding a name into it.
    "dropped_declarations": {name: why for name, why in dropped_d},
    # the written seam, hashed so the verifier can pin it and refuse silent growth
    "adapter": {
        "functions": ["attachSites", "currentSite", "currentStage"],
        "sha256": hashlib.sha256(ADAPTER.encode("utf-8")).hexdigest(),
        "bytes": len(ADAPTER.encode("utf-8")),
    },
}
for n in sorted(engine):
    a, b = FSPAN[n]
    t = BODY[a:b]
    man["functions"][n] = {
        "bytes": len(t.encode("utf-8")),
        "sha256": hashlib.sha256(t.encode("utf-8")).hexdigest(),
    }
io.open(os.path.join(OUT, "_transform.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(man, indent=2, sort_keys=True) + "\n")

if dropped_d:
    print("declarations DROPPED because they call fenced code:")
    for name, why in dropped_d:
        print("   %-14s calls %s" % (name, why))
print("results/engine.mjs   %d functions, %d declarations, %.1f KB"
      % (len(engine), len(DSPAN), len(out) / 1024.0))
print("results/_transform.json  %d hashes" % len(man["functions"]))
print("seam crossings: 0")
if dom_at_load:
    print()
    print("!! declarations that touch the DOM at import time (%d):" % len(dom_at_load))
    for d in dom_at_load:
        print("     %s" % d)
    print("   These capture an element BEFORE React renders it. Handle before wiring the view.")
else:
    print("no declaration resolves an element at import time")
