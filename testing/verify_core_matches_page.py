# -*- coding: utf-8 -*-
r"""Assert that AGENTIC-ARBITER/core/ is still the same code as demo/index.html's inline copy.

WHY THIS EXISTS, AND WHY IT IS TEMPORARY. The agent lives twice right now: as importable ES modules
under `core/`, which the five cross-implementation verifiers test against Python, and as the inline
copy inside `demo/index.html`, which is what a reader actually runs. Two copies of decision-critical
code with nothing comparing them is the defect this repository has caught over and over. The five
verifiers prove `core/` matches PYTHON; without this, nothing would notice if the PAGE drifted away
from `core/`, and the passing verifiers would be testing code the reader never sees.

It stops being needed the moment the page imports `core/` rather than carrying its own copy. Until
then this is the seam, and a seam without a check is a fiction.

HOW IT WORKS: PROVENANCE, PLUS BYTE-IDENTITY WHERE IT IS OWED.
`core/_transform.json` is written by the generator and records, per function, the SHA-256 of the page
source it extracted, the SHA-256 of the module source it produced, and the substitutions it applied in
words. This check re-extracts from the page, re-reads the module, and asserts both hashes. So:

    edit the page          -> page_sha256 mismatch -> FAIL, re-run the generator
    hand-edit core/        -> core_sha256 mismatch -> FAIL, re-run the generator
    change the generator   -> both move together, deliberately, in one commit

Independently of the manifest, the eleven functions that were lifted with NO substitution are compared
byte for byte. That second half matters: it means a substitution quietly introduced into one of those
cannot pass merely by being recorded in the manifest alongside it.

🔴 THE INSTRUMENT BEHIND THIS HAS ALREADY EARNED ITS KEEP, TWICE.
  * It found that the generator's `\bUS\b -> us` substitution had matched the `US` inside
    `toLocaleString('en-US')` -- a hyphen and a quote are both non-word characters, so a word boundary
    sits between them. A locale tag had been silently rewritten to 'en-us'. Locale matching is
    case-insensitive, so no behavioural test would ever have failed on it.
  * An earlier version of THIS FILE declared the permitted differences as exact diff RUNS and compared
    them to difflib's output, which asserts against the diff algorithm's chunking rather than against
    the code: `cfg` -> `cfgFromStrings` arrives as an insertion of "FromStrings", and `tkEvent(` ->
    `_ev(` fragments because the two strings share a `v` and a `(`. Hashes do not have opinions.

Exit 0 clean, 1 drifted, 3 could not run.
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
CORE = os.path.join(ROOT, "AGENTIC-ARBITER", "core")
CHARTS = os.path.join(ROOT, "AGENTIC-ARBITER", "charts")
DIRS = {"core": CORE, "charts": CHARTS}

CHECKS = [0]
FAILS = []

# Lifted with NO substitution, and required to stay that way. Named here as well as in the manifest
# so that adding a substitution to one of them cannot pass by being recorded.
IDENTICAL = ["cfMinN", "cfAttainable", "cfQuantileIndex", "cfSplit", "H0", "plan", "reactive",
             "explainHour", "tkFixed", "tkRender", "tkFormat",
             # charts/primitives.mjs -- all seven lifted with no substitution at all.
             "motionOK", "getCssVar", "fitCanvas", "casePath", "chipText", "sparkSVG",
             "countUpText"]


def ck(name, ok, detail=""):
    CHECKS[0] += 1
    if ok:
        print("   [ok]   %-54s %s" % (name, detail))
    else:
        FAILS.append(name)
        print("   [FAIL] %-54s %s" % (name, detail))


def brace_body(src, header):
    """The function starting at `header`, brace-matched. The extractor the verifiers use."""
    i = src.find(header)
    if i < 0:
        return None
    d, started, j = 0, False, i
    while j < len(src):
        c = src[j]
        if c == "{":
            d += 1
            started = True
        elif c == "}":
            d -= 1
            if started and d == 0:
                j += 1
                break
        j += 1
    return src[i:j]


def sha(x):
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def main():
    page = os.path.join(DEMO, "index.html")
    man_p = os.path.join(CORE, "_transform.json")
    for p in (page, man_p):
        if not os.path.exists(p):
            print("   cannot run: missing %s" % p)
            return 3
    s = io.open(page, encoding="utf-8", newline="").read()
    k = s.rfind("<script")
    BODY = s[s.index(">", k) + 1: s.index("</script>", k)]
    man = json.load(io.open(man_p, encoding="utf-8"))["functions"]

    print("=" * 78)
    print("VERIFY_CORE_MATCHES_PAGE -- core/ against demo/index.html's inline copy")
    print("=" * 78)
    print("   manifest: %d functions" % len(man))
    print()

    modcache = {}
    for name in sorted(man):
        e = man[name]
        modfile = e["module"]
        base = DIRS.get(e.get("dir", "core"), CORE)
        if modfile not in modcache:
            p = os.path.join(base, modfile)
            if not os.path.exists(p):
                ck("%s exists" % modfile, False, "missing")
                continue
            modcache[modfile] = io.open(p, encoding="utf-8", newline="").read()

        old = brace_body(BODY, "function %s(" % e["page_name"])
        new = brace_body(modcache[modfile], "export function %s(" % name)
        if new is not None:
            new = new[len("export "):]
        if old is None or new is None:
            ck("%s: extractable from both" % name, False,
               "page=%s core=%s" % (old is not None, new is not None))
            continue

        pg_ok = sha(old) == e["page_sha256"]
        cr_ok = sha(new) == e["core_sha256"]
        if e["page_name"] in IDENTICAL:
            ck("%-16s byte-identical to the page" % name, new == old,
               "%d chars" % len(old) if new == old else
               "THEY DIFFER (%d vs %d chars) -- this function is declared substitution-free"
               % (len(old), len(new)))
        ck("%-16s page copy unchanged since generation" % name, pg_ok,
           "%d chars" % len(old) if pg_ok else
           "the PAGE was edited; re-run the generator")
        ck("%-16s module unchanged since generation" % name, cr_ok,
           "%d chars, %d substitution(s)" % (len(new), len(e["substitutions"])) if cr_ok else
           "core/%s was hand-edited; re-run the generator" % modfile)

    # Every core export must appear in the manifest. A check that quietly stops covering a function
    # is worse than no check at all (gotcha #74).
    exports = set()
    for base in (CORE, CHARTS):
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if fn.endswith(".mjs"):
                t = io.open(os.path.join(base, fn), encoding="utf-8").read()
                for line in t.split("\n"):
                    if line.startswith("export function "):
                        exports.add(line[len("export function "):].split("(")[0])
    missing = sorted(exports - set(man))
    ck("every generated export is in the manifest", not missing,
       "%d exports across core/ and charts/" % len(exports) if not missing
       else "NOT COVERED: %s" % ", ".join(missing))
    # CF is the one deliberate rewrite: string literals duplicating the CSS tokens became getters
    # that resolve from them. Declared here so its absence from the identity checks is a decision.
    prim = os.path.join(CHARTS, "primitives.mjs")
    if os.path.exists(prim):
        t = io.open(prim, encoding="utf-8").read()
        ck("charts/ CF resolves the font tokens instead of duplicating them",
           "export const CF = {" in t and "get label()" in t and "getCssVar('--font-display')" in t,
           "getters, not literals -- fixes the drift the page's own comment concedes")

    print()
    print("   declared substitutions, in full:")
    for name in sorted(man):
        for op in man[name]["substitutions"]:
            print("      %-16s %s" % (name, op))

    print()
    print("%d checks, %d failed" % (CHECKS[0], len(FAILS)))
    if FAILS:
        for f in FAILS:
            print("   FAILED: %s" % f)
        print("VERDICT: core/ and demo/index.html have drifted apart. Re-run the generator so both "
              "move\n         together, and say in the same commit why the transform changed.")
        return 1
    n_ident = sum(1 for k in man if man[k]["page_name"] in IDENTICAL)
    n_subst = len(man) - n_ident
    print("VERDICT: core/ and charts/ are the page's own code.")
    print("         %d functions byte-identical to the page; %d differing only by the"
          % (n_ident, n_subst))
    print("         substitutions recorded in _transform.json, and every copy on both sides")
    print("         hashes to what the generator produced.")
    print("         The five cross-implementation verifiers test core/ against Python; this is")
    print("         what keeps that meaningful for the page a reader actually opens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
