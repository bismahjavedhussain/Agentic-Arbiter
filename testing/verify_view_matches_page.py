# -*- coding: utf-8 -*-
r"""The React app's engine markup must still be the page's markup, and must satisfy the engine.

TWO DIFFERENT QUESTIONS, and the second is the one that would otherwise bite silently.

  1. IS IT STILL THE PAGE'S MARKUP? app/src/generated/engine-markup.ts holds 39 KB of the configure
     and results sections lifted verbatim, so that results/engine.mjs can find its 116 element ids
     without anyone retyping them. If the page's markup changes and this does not, the React app
     renders yesterday's panels. Recomputed from the page here, not trusted.

  2. DOES EVERY ELEMENT THE ENGINE REACHES FOR ACTUALLY EXIST? This is the failure this whole
     arrangement is exposed to. The engine does 215 `$('#id')` lookups. If one id is not in the
     markup, is not created at runtime, and is not one React renders itself, then some panel writes
     into null -- and the page's own history says exactly what that looks like: HANDOFF.md records a
     panel that "wrote into nothing", threw, and because drawAll() has no error boundary took every
     panel after it down with it. One missing container, twelve blank cards, no error on screen.

     So every referenced id is accounted for by name, in one of FOUR buckets:
       * in the lifted markup
       * created at runtime, by buildControls() or by document.createElement
       * owned by the React app, listed explicitly below
       * looked up behind a null guard, which is correct code and not a defect. #limits is that
         case: its card was deliberately deleted and drawLimits() kept as the executable record of
         what the limits are, so the lookup returns null by design.
     Anything in none of those four is a failure, and the message names it.
"""
import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "AGENTIC-ARBITER", "demo", "index.html")
ENG = os.path.join(ROOT, "AGENTIC-ARBITER", "results", "engine.mjs")
GEN = os.path.join(ROOT, "AGENTIC-ARBITER", "app", "src", "generated")
TS = os.path.join(GEN, "engine-markup.ts")
MAN = os.path.join(GEN, "engine-markup.json")

FAILS = []
CHECKS = [0]


def ck(ok, label, detail=""):
    CHECKS[0] += 1
    if ok:
        print("   [ok]   %-54s %s" % (label, detail))
    else:
        FAILS.append(label)
        print("   [FAIL] %-54s %s" % (label, detail))


print("=" * 78)
print("app/src/generated/engine-markup.ts vs demo/index.html")
print("=" * 78)

for p in (PAGE, ENG, TS, MAN):
    if not os.path.exists(p):
        print("   [FAIL] missing: %s" % p)
        print("   Generate with scratchpad/mkview.py and scratchpad/mkresults.py.")
        sys.exit(1)

ts = io.open(TS, encoding="utf-8", newline="").read()
man = json.loads(io.open(MAN, encoding="utf-8").read())
eng = io.open(ENG, encoding="utf-8", newline="").read()

# ---- 1: the markup is the page's ----------------------------------------------------------------
m = re.search(r'(?s)export const ENGINE_MARKUP_SECTIONS: string\[\] = (\[.*?\n\]);\n', ts)
ck(m is not None, "the markup sections parse")
if not m:
    sys.exit(1)
sections = json.loads(m.group(1))
markup = "\n".join(sections)

got = hashlib.sha256(markup.encode("utf-8")).hexdigest()
ck(got == man["sha256"], "the markup matches its manifest hash",
   "" if got == man["sha256"] else "engine-markup.ts has been edited since generation")

page = io.open(PAGE, encoding="utf-8", newline="").read()
body = page[page.index(">", page.index("<body")) + 1: page.rfind("<script")]
# EACH BLOCK IS A VERBATIM SUBSTRING OF THE PAGE. This is the honest form of the check. Comparing
# line by line failed on #modebanner, which is a <span> sitting mid-line in the page: a span starts at
# the '<' of its opening tag, so a lifted block can be a fragment of a line rather than a whole one,
# and no amount of stripping makes a fragment equal to the line that contains it.
stray = [lab for lab, sec in zip(man["sections"], sections) if sec not in body]
ck(not stray, "every lifted block is still verbatim page markup",
   "%d blocks, %.1f KB" % (len(sections), len(markup) / 1024.0) if not stray
   else "NOT FOUND IN THE PAGE: " + ", ".join(stray))

# ---- 2: every id the engine reaches for is accounted for -----------------------------------------
# 🔴 MASK BLOCK COMMENTS FIRST. This engine documents its own bug history, and one of those notes
# QUOTES a lookup: the guard on #limits is preceded by a paragraph containing `$('#limits')` in prose.
# Counting that as a reference made `limits` look like an unguarded lookup, when the code beneath the
# comment reads `const el = $('#limits'); if(!el) return;`. Masking preserves offsets so line numbers
# stay usable, and CODE is what gets analysed.
CODE = re.sub(r"/\*.*?\*/", lambda mo: " " * len(mo.group(0)), eng, flags=re.S)
assert len(CODE) == len(eng)

refs = sorted(set(re.findall(r"""\$\('#([A-Za-z0-9_]+)'\)""", CODE)))
# 🔴 MASK HTML COMMENTS BEFORE COLLECTING IDS, and this one cost a debugging session. The page
# documents its own history in comments, and one of them reads:
#     THIS WAS A SECOND <select id="c_site"> -- A DUPLICATE ID, and therefore dead UI.
# Collecting ids from the raw text counted that MENTION, so `c_site` was reported present in the lifted
# markup while the real element sits in #pickcard, on React's side of the seam. This check passed, and
# the app then stalled at the configure stage with #c_site absent from the DOM.
# Fourth time this session that a name in prose was mistaken for a definition. Mask first, always.
MARKUP_CODE = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
in_markup = set(re.findall(r'\bid="([A-Za-z0-9_]+)"', MARKUP_CODE))

# built at runtime by buildControls() from the CONTROLS table, so they cannot be in static markup
controls = re.search(r"(?s)^const CONTROLS = \[(.*?)\];", CODE, re.M)
runtime = set(re.findall(r"'(c_[a-z0-9_]+)'", controls.group(1))) if controls else set()

# rendered by the React app itself. Named, so that "React will have that one" is a claim on a list
# rather than an assumption in my head.
REACT_RENDERS = {
    "app",          # the results column's own scroll container
    "themebtn",     # React's theme toggle, which calls the engine's applyTheme
    "masthead",     # React's masthead
    "bezel",        # the page frame
    # the pick screen, all reimplemented in React
    "natmap", "natmapcard", "natmapintro", "natmapnote", "natside", "natsidebody",
    "pickcard", "pickgo", "pickinfo", "sitesearch", "searchclear", "searchresults",
    "searchintro", "searchnote", "screenzeronote", "zeronote", "readytiles",
    "mf_state", "mf_op", "mf_q", "mf_drop", "mf_all", "mf_all_n", "mf_ready",
    "mf_ready_n", "mf_count",
    # ⚠ "filters" was on this list and should not have been: #filters IS in the lifted markup, and
    # buildControls() fills it. Listing it here meant the check would have stayed quiet if the lift
    # had ever dropped it. An entry on this list is a promise that React renders the thing.
    "c_site",       # React owns the picker now, so React renders the engine's hidden <select>
    "inspector", "inspclose", "inspclose2", "inspgo",
    "railind",
}

# created by the engine itself: document.createElement followed by `.id = 'x'`, or an id written into
# an innerHTML template, or buildControls()'s `f_<select id>` wrappers
made = set(re.findall(r"""\.id\s*=\s*['"]([A-Za-z0-9_]+)['"]""", CODE))
made |= set(re.findall(r"""\bid=\\?["']([A-Za-z0-9_]+)\\?["']""", CODE))
made |= {"f_" + c for c in runtime}

# 🔴 AND THE FOURTH BUCKET, WHICH IS THE REAL RULE: a GUARDED lookup of a missing element is correct
# code, not a defect. #limits is the case that taught it. The "Honest limits" card was deleted on
# 2026-08-26 and drawLimits() was kept on purpose as the executable record of what the limits are, so
# `$('#limits')` returns null by design and the function reads `const el = $('#limits'); if(!el)
# return;`. The comment above that guard is a war story about this exact failure mode: an earlier
# version had no guard, assigning .innerHTML on null threw, drawLimits() is the LAST call in drawAll(),
# and the throw escaped so runAgent() never reached `await streamTape()`. Sixteen tape rows silently
# absent, every panel rendered, nothing on screen to say why.
# So what this check is really asserting is: no UNGUARDED lookup of an element nobody renders.
def guarded(eid):
    """True when every `$('#eid')` in the engine is protected against a null result."""
    pat = re.compile(r"""(?:(?:const|let|var)\s+(\w+)\s*=\s*)?\$\('#""" + re.escape(eid) + r"""'\)""")
    sites = 0
    safe = 0
    for mo in pat.finditer(CODE):
        sites += 1
        var = mo.group(1)
        # the reference plus the next two lines: enough for `if(!el) return;` on its own line
        tail = CODE[mo.end(): mo.end() + 200]
        head = CODE[max(0, mo.start() - 60): mo.start()]
        if var and re.search(r"if\s*\(\s*!?\s*" + re.escape(var) + r"\s*\)", tail):
            safe += 1
        elif re.search(r"if\s*\(\s*!?\s*$", head) or re.search(r"if\s*\(\s*$", head):
            safe += 1        # the lookup is itself the condition
        elif re.match(r"\s*\)\s*(?:\{|return|;)", tail) and "if" in head[-30:]:
            safe += 1
    return sites > 0 and safe == sites


unaccounted = [r for r in refs
               if r not in in_markup and r not in runtime and r not in REACT_RENDERS
               and r not in made and not guarded(r)]
ck(not unaccounted, "no unguarded lookup of an element nobody renders",
   "%d ids: %d in markup, %d runtime, %d React's, %d guarded"
   % (len(refs), len([r for r in refs if r in in_markup]),
      len([r for r in refs if r in runtime or r in made]),
      len([r for r in refs if r in REACT_RENDERS]),
      len([r for r in refs if r not in in_markup and r not in runtime
           and r not in REACT_RENDERS and r not in made]))
   if not unaccounted
   else "UNGUARDED (%d): %s" % (len(unaccounted), ", ".join(unaccounted[:10])))

# ---- 2b: THE SELECTORS THAT ARE NOT IDS ----------------------------------------------------------
# 🔴 THE CHECK ABOVE ONLY SEES `$('#id')`, AND THAT BLIND SPOT COST A DEBUGGING SESSION. The engine
# reads its design tokens through
#     const cssv = n => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n)
# which is a CLASS selector. With no `.viz-root` in the DOM that returns null, getComputedStyle throws
# "parameter 1 is not of type 'Element'" inside an async handler, the configure transition rejects, and
# the screen simply stops with nothing on it and nothing in the console that names the cause.
# So every selector the engine uses that is NOT a plain #id is enumerated and accounted for. Six of
# them today, and each one has to resolve somewhere nameable.
NONID = set()
for pat in (r"""querySelector\('([^']+)'\)""", r"""querySelectorAll\('([^']+)'\)""",
            r"""\$\('([^']+)'\)"""):
    for sel in re.findall(pat, CODE):
        if not re.fullmatch(r"#[A-Za-z0-9_]+", sel):
            NONID.add(sel)

# Provided by the React app rather than by the lifted markup. Named, so it is a promise on a list.
REACT_PROVIDES_SELECTORS = {
    ".viz-root",        # EngineStage's host div: the engine's token root
}


def _class_exists(cls):
    """In the static markup, or written by the engine into markup it generates itself.

    The second half matters and the first version omitted it: `.plate-cell` and `.pv` are built by
    drawPlate() writing innerHTML, so they never appear in the lifted markup and were reported
    unresolved. Likewise `aria-current`, which syncRail() SETS rather than finds.
    """
    # A REGEX, because a class name can be terminated by a JAVASCRIPT string boundary rather than by
    # the quote that closes the attribute. The engine builds its plate cells with
    #     '<div class="plate-cell' + (cls ? ' '+cls : '') + '">'
    # so the text on disk is `class="plate-cell'` -- an opening double quote and a closing SINGLE one.
    # Substring patterns for `"plate-cell"` and `"plate-cell ` both missed it, and the check reported a
    # class the engine demonstrably writes as unresolved.
    pat = re.compile(r"""(?:class=["']|["'\s])""" + re.escape(cls) + r"""(?=["'\s>]|$)""")
    return any(pat.search(hay) for hay in (MARKUP_CODE, CODE))


def selector_resolves(sel):
    """Is there a nameable place every part of this selector comes from?"""
    if sel in REACT_PROVIDES_SELECTORS:
        return True
    # a descendant selector resolves if each of its parts does
    parts = [p for p in sel.split() if p]
    if len(parts) > 1:
        return all(selector_resolves(p) for p in parts)
    # attribute-qualified: check the bare part and the attribute name separately
    m = re.match(r"^([^\[]*)\[([A-Za-z-]+)", sel)
    if m:
        base, attr = m.group(1), m.group(2)
        if attr not in MARKUP_CODE and attr not in CODE:
            return False
        return selector_resolves(base) if base else True
    if sel.startswith("."):
        return _class_exists(sel[1:])
    if sel.startswith("#"):
        return sel[1:] in in_markup or sel[1:] in REACT_RENDERS or sel[1:] in made
    if sel.startswith("["):
        a = re.sub(r"[\[\]]", "", sel).split("=")[0]
        return a in MARKUP_CODE or a in CODE
    # a bare tag name resolves if the markup contains such a tag, or the engine creates one
    return ("<" + sel) in MARKUP_CODE or ("'" + sel + "'") in CODE


unresolved = sorted(s for s in NONID if not selector_resolves(s))
ck(not unresolved, "every non-id selector the engine uses resolves",
   "%d selectors: %s" % (len(NONID), ", ".join(sorted(NONID)))
   if not unresolved else "UNRESOLVED: " + ", ".join(unresolved))

# ---- 3: the live card came across ---------------------------------------------------------------
# Standing rule C1, checked on the VIEW side as well as the engine side. The engine can keep all five
# live functions and the card can still be missing from the markup, which is the same outcome.
LIVE_IDS = ["livecard", "livego", "livetiles", "livetable", "livebound", "liveenv",
            "livemsg", "liverefusal", "livestream", "livecost"]
gone = [i for i in LIVE_IDS if i not in in_markup]
ck(not gone, "the live agent's card and its ten ids are in the markup",
   "" if not gone else "MISSING: " + ", ".join(gone))

# ---- 4: the stage attributes survived ------------------------------------------------------------
# setStage() is the single owner of visibility and it works by walking [data-show]. If the attributes
# were lost in the lift, every card would be permanently visible at every stage.
shows = re.findall(r'data-show="([a-z ]+)"', MARKUP_CODE)
ck(len(shows) >= 15, "the [data-show] attributes survived the lift",
   "%d elements carry a stage" % len(shows))
ck('data-needs="plume"' in MARKUP_CODE, "data-needs=\"plume\" survived",
   "the dial card is still removed where there is no tagged neighbour")

# ---- 5: the buttons the user asked about ---------------------------------------------------------
# The complaint that started this work was a missing button, so the buttons are asserted by name.
BUTTONS = {"runagent": "Run the agent", "runagent2": "Run the agent (second)",
           "autofill": "Auto-fill a realistic plant", "backtopick": "Choose a different site",
           "livego": "Run the agent on live data"}
missing_btn = [b for b in BUTTONS if ('id="%s"' % b) not in MARKUP_CODE]
ck(not missing_btn, "every action button is in the markup",
   ", ".join(sorted(BUTTONS)) if not missing_btn
   else "MISSING: " + ", ".join(missing_btn))

print()
print("=" * 78)
if FAILS:
    print("%d checks, %d FAILED" % (CHECKS[0], len(FAILS)))
    for f in FAILS:
        print("   * %s" % f)
    print()
    print("Regenerate with scratchpad/mkview.py if the page is what changed.")
else:
    print("%d checks, 0 failed. The React app renders the page's own configure and results"
          % CHECKS[0])
    print("markup: %d ids, every engine lookup accounted for, the live card present."
          % len(refs))
print("=" * 78)
sys.exit(1 if FAILS else 0)
