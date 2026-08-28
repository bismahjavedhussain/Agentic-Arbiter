# -*- coding: utf-8 -*-
r"""AGENTIC-ARBITER/results/engine.mjs must still be the page's own code, character for character.

WHY THIS FILE IS THE WHOLE JUSTIFICATION FOR results/. The engine now exists twice: inline in
demo/index.html, and as an importable module the React app drives. Two copies of 218 KB of
decision-critical drawing code is a liability unless something refuses to let them drift, and this is
that something. run_all.py runs it as a step, so drift fails the build rather than surviving to a demo.

WHY NOT JUST DELETE THE INLINE COPY. Because then index.html would need
`<script type="module" src="../results/engine.mjs">`, and browsers block module loading over file://.
A judge who double-clicks index.html would get a blank page. The single-file page opening from disk
with nothing installed is the product's most-tested property; keeping it costs one duplicated file and
this verifier.

WHAT IS CHECKED
  1. Every function in the manifest is byte-identical between the page and the module.
  2. The manifest's own SHA-256 matches what is on disk on BOTH sides, so a stale manifest cannot
     certify a drifted module.
  3. Every top-level declaration the page has, the module has verbatim. A missing `const` is a
     ReferenceError at import time, which is a broken results stage, not a cosmetic difference.
  4. THE FENCE HOLDS: the module defines none of the pick-stage functions React replaces. If one
     reappears, the two implementations of the national map have started competing.
  5. THE LIVE AGENT IS PRESENT. Standing rule C1 says #livecard and #livego are permanent, so the
     five functions that serve them must be in the module. A results stage that quietly lost the
     live path would still look complete.
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
MAN = os.path.join(ROOT, "AGENTIC-ARBITER", "results", "_transform.json")

NAME = r"[A-Za-z_$][A-Za-z0-9_$]*"
CHECKS = [0]
FAILS = []


def ck(ok, label, detail=""):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(label)
        print("   [FAIL] %-52s %s" % (label, detail))


def note(label, detail=""):
    print("   [ok]   %-52s %s" % (label, detail))


def script_body(html):
    k = html.rfind("<script")
    return html[html.index(">", k) + 1: html.index("</script>", k)]


def fn_span(text, name):
    """The brace-matcher the five node verifiers use, so this compares what they check."""
    m = re.search(r"^(?:async )?function " + re.escape(name) + r"\s*\(", text, re.M)
    if not m:
        return None
    i = m.start()
    d, started, j = 0, False, i
    while j < len(text):
        c = text[j]
        if c == "{":
            d += 1
            started = True
        elif c == "}":
            d -= 1
            if started and d == 0:
                j += 1
                break
        j += 1
    return text[i:j]


print("=" * 78)
print("results/engine.mjs vs demo/index.html: substitution for substitution")
print("=" * 78)

for p in (PAGE, ENG, MAN):
    if not os.path.exists(p):
        print("   [FAIL] missing: %s" % p)
        print()
        print("   Generate it with scratchpad/mkresults.py before running this.")
        sys.exit(1)

html = io.open(PAGE, encoding="utf-8", newline="").read()
BODY = script_body(html)
eng = io.open(ENG, encoding="utf-8", newline="").read()
man = json.loads(io.open(MAN, encoding="utf-8").read())

# ---- 1 and 2: every function, both sides, against the manifest ----------------------------------
fns = man["functions"]
same, drift, missing = 0, [], []
for name in sorted(fns):
    a = fn_span(BODY, name)
    b = fn_span(eng, name)
    if a is None:
        missing.append(name + " (absent from the PAGE)")
        continue
    if b is None:
        missing.append(name + " (absent from the MODULE)")
        continue
    if a != b:
        drift.append(name)
        continue
    h = hashlib.sha256(a.encode("utf-8")).hexdigest()
    if h != fns[name]["sha256"]:
        drift.append(name + " (manifest hash stale)")
        continue
    same += 1

ck(not missing, "every manifested function exists on both sides",
   "MISSING: " + ", ".join(missing[:4]) if missing else "")
ck(not drift, "every function is byte-identical, page and module",
   "DRIFTED: " + ", ".join(drift[:4]) if drift else "")
if not missing and not drift:
    note("%d functions byte-identical and hash-confirmed" % same,
         "%.1f KB" % (sum(f["bytes"] for f in fns.values()) / 1024.0))

# ---- 3: the declarations ------------------------------------------------------------------------
# Taken by name from the page's own top-level declarations and required verbatim in the module. Only
# the declaration HEAD is compared, because the whole point of check 1 is that bodies are compared
# exactly and a declaration is not a function; what matters here is that none has gone missing.
decl_names = re.findall(r"(?m)^(?:const|let|var)\s+(" + NAME + r")", BODY)
decl_names = sorted(set(decl_names))


def _declared(name, text):
    # 🔴 NO TRAILING \b WHEN THE NAME DOES NOT END IN A WORD CHARACTER. `re.escape('$')` is `\$`, and
    # `\$\b` demands a word boundary after a non-word character, which never matches -- so the page's
    # `const $ = s => document.querySelector(s)` was reported ABSENT while sitting on line 33 of the
    # module. Third time this session that a \b assumption produced a confident wrong answer.
    tail = r"\b" if name[-1:].isalnum() or name[-1:] == "_" else r"(?![\w$])"
    return re.search(r"(?m)^(?:const|let|var)\s+" + re.escape(name) + tail, text) is not None


# 🔴 ONE DECLARATION IS DELIBERATELY ABSENT, and the exception is DECLARED rather than assumed.
# `const BOOTED = boot();` is the page's entire bootstrap, executed at module load. Lifting it made the
# module throw `ReferenceError: boot is not defined` the instant React imported it -- boot() stays in
# the page because it also starts the national map React replaces. Every static check passed on that
# module: the code was byte-identical and every id was present. Only driving the app in a browser found
# it, which is why testing/verify_app_flow.py now exists.
# The generator records what it dropped and why; this reads that record, so a SECOND silent drop would
# still fail here.
dropped = man.get("dropped_declarations") or {}
absent = [d for d in decl_names if not _declared(d, eng) and d not in dropped]
ck(all(_declared(d, eng) is False for d in dropped),
   "each declared exception really is absent",
   ", ".join("%s (calls %s)" % (k, v) for k, v in sorted(dropped.items())) or "none declared")
ck(not absent, "every top-level declaration is present in the module",
   "ABSENT: " + ", ".join(absent[:6]) if absent else "")
if not absent:
    note("%d of the page's %d top-level declarations lifted"
         % (len(decl_names) - len(dropped), len(decl_names)),
         "%d declared exception: %s" % (len(dropped), ", ".join(sorted(dropped)))
         if dropped else "all of them")

# ---- 4: the fence -------------------------------------------------------------------------------
fence = man.get("excluded_react_owns") or []
leaked = [f for f in fence
          if re.search(r"(?m)^(?:async )?function " + re.escape(f) + r"\s*\(", eng)]
ck(not leaked, "the fence holds: no pick-stage function in the module",
   "LEAKED: " + ", ".join(leaked) if leaked else "")
if not leaked:
    note("%d pick-stage functions correctly absent" % len(fence),
         "React owns the map and the search")

# ---- 5: the live agent --------------------------------------------------------------------------
# Standing rule C1. The live path is the one thing a "results stage" can lose while still looking
# finished, so it is named explicitly rather than left to the closure.
LIVE = ["runLive", "drawLive", "drawLiveCost", "drawLiveUnavailable", "probeLive"]
gone = [f for f in LIVE
        if not re.search(r"(?m)^(?:async )?function " + re.escape(f) + r"\s*\(", eng)]
ck(not gone, "the live agent's five functions are in the module",
   "MISSING: " + ", ".join(gone) if gone else "")
if not gone:
    note("live path intact", ", ".join(LIVE))

# and the nine elements it writes, so a renamed id is caught here and not on stage
LIVE_IDS = ["livetiles", "livetable", "livebound", "liveenv", "livemsg",
            "liverefusal", "livestream", "livecost", "livego"]
noid = [i for i in LIVE_IDS if ("'#" + i + "'") not in eng]
ck(not noid, "the live card's nine element ids are still referenced",
   "MISSING: " + ", ".join(noid) if noid else "")
if not noid:
    note("%d live element ids referenced" % len(LIVE_IDS))

# ---- 6: the module is self-contained ------------------------------------------------------------
# It must not import from core/. core/'s copies were deliberately CHANGED when they were extracted
# (decide(k) became decide(k, trace) so the node verifiers stop stubbing $()), so importing them
# would silently break every call site here. The duplication is intentional and this asserts it.
imports = re.findall(r"(?m)^import\s.*$", eng)
ck(not imports, "the module imports nothing",
   "IMPORTS: " + "; ".join(imports[:3]) if imports else "")
if not imports:
    note("self-contained", "core/ deliberately not imported: its signatures differ")

# ---- 7: the adapter is pinned -------------------------------------------------------------------
# The three-function seam is the ONLY written code in a generated file. Pinning its hash is what stops
# it becoming the place where logic quietly accumulates, which is exactly what would happen otherwise:
# it is the one section a future edit can touch without any other check noticing.
ad = man.get("adapter") or {}
i = eng.find("/* ---- THE ADAPTER")
ck(i > 0, "the adapter section is present")
if i > 0:
    # bounded at the export block, because the manifest hashed the adapter ALONE. Slicing to end of
    # file swept the `export { ... }` list in and reported an edit that had not happened.
    j = eng.find("/* ---- the surface React drives", i)
    text = eng[i:j] if j > i else eng[i:]
    got = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ck(got == ad.get("sha256"), "the adapter is byte-identical to its manifest hash",
       "" if got == ad.get("sha256") else "the adapter has been edited since generation")
    defined = re.findall(r"(?m)^export function (" + NAME + r")", eng)
    want = ad.get("functions") or []
    ck(sorted(defined) == sorted(want),
       "the adapter defines exactly its three declared functions",
       "found %s, expected %s" % (sorted(defined), sorted(want))
       if sorted(defined) != sorted(want) else "")
    if got == ad.get("sha256") and sorted(defined) == sorted(want):
        note("adapter pinned", "%d bytes: %s" % (ad.get("bytes"), ", ".join(want)))

exported = re.search(r"(?ms)^export \{(.*?)\};", eng)
n_exp = len(re.findall(NAME, exported.group(1))) if exported else 0
ck(n_exp >= len(fns), "every engine function is exported",
   "%d exported, %d defined" % (n_exp, len(fns)))
if n_exp >= len(fns):
    note("%d exports" % n_exp)

print()
print("=" * 78)
if FAILS:
    print("%d checks, %d FAILED" % (CHECKS[0], len(FAILS)))
    for f in FAILS:
        print("   * %s" % f)
    print()
    print("Regenerate with scratchpad/mkresults.py if the PAGE is the one that changed.")
    print("If the MODULE was hand-edited, that edit is the bug: this file is generated.")
else:
    print("%d checks, 0 failed. results/engine.mjs is the page's own engine, unmodified: %d"
          % (CHECKS[0], same))
    print("functions byte-identical, the pick-stage fence intact, and the live agent present.")
print("=" * 78)
sys.exit(1 if FAILS else 0)
