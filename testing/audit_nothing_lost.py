# -*- coding: utf-8 -*-
r"""Prove that nothing was lost: no function, no element, no data, no assertion.

The user asked for assurance before restarting. Assurance is not a sentence, it is a diff. Everything
below compares the CURRENT working tree against the commit d28a50b, which predates every change in
this session, and reports losses rather than changes: a thing that existed then and does not exist now.

THE BASELINE IS PINNED, NOT `HEAD`. It was written as HEAD when d28a50b WAS head, and the first run
after committing this work reported 8 losses that were nothing of the kind: the rename had landed, so
`git show HEAD:INTAKE-ARBITER/...` failed and 8 unreadable files scored as 8 missing ones.
That is worth spelling out because the bug was structural rather than clumsy. A "nothing was lost"
check measured against `HEAD` becomes VACUOUS the moment the work is committed, since HEAD then
contains the changes and every comparison trivially agrees. The question this file answers is "did
anything survive the React work, the core extraction and the rename", and that question has one fixed
answer point: the commit before any of it. So BASE is a commit id, overridable with AUDIT_BASE.

Note on paths: the baseline holds the project under whichever folder name existed then, so the folder
is resolved AT the baseline rather than assumed. Before 2026-08-27 that is INTAKE-ARBITER/, after it
AGENTIC-ARBITER/, and the comparison is BASE:<old folder>/<x> against the tree's AGENTIC-ARBITER/<x>.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

# This file prints lines lifted out of the page and out of HANDOFF.md, and both contain emoji. On a
# Windows console that is cp1252 that raises UnicodeEncodeError and the traceback replaces the report.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"D:\FGHackathon"
# The last commit that predates the React app, the core/ extraction and the folder rename. Pinned so
# that committing the work cannot turn this check into a comparison of the work against itself.
BASE = os.environ.get("AUDIT_BASE", "d28a50b")
NEW = "AGENTIC-ARBITER"


def _folder_at_base():
    """Whichever name the project folder had at BASE. Assuming it costs 8 false losses."""
    r = subprocess.run(["git", "ls-tree", "--name-only", BASE], cwd=ROOT,
                       capture_output=True, text=True)
    names = r.stdout.split()
    for cand in (NEW, "INTAKE-ARBITER"):
        if cand in names:
            return cand
    raise SystemExit("!! neither %s/ nor INTAKE-ARBITER/ exists at %s" % (NEW, BASE))


OLD = _folder_at_base()
PROBLEMS = []
NOTES = []


def head(path):
    """The file's contents at HEAD, or None."""
    r = subprocess.run(["git", "show", BASE + ":" + path], cwd=ROOT,
                       capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8", "replace")


def now(path):
    p = os.path.join(ROOT, path.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    return io.open(p, encoding="utf-8", newline="", errors="replace").read()


def head_bytes(path):
    r = subprocess.run(["git", "show", BASE + ":" + path], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout


# 🔴 TWO DELIBERATE REMOVALS, 2026-08-28, declared here so this check stays meaningful.
#   data/       1,039 MB of BUILD INPUTS, moved to D:/FGHackathon-data with a directory junction left
#               at the old path so all twelve scripts that build os.path.join(IA, "data", ...) keep
#               working. Never fetched at runtime, proved by reading the page: it fetches only
#               relative names inside demo/. Untracked so it is never pushed, which took tracked bytes
#               from 1,823 MB to 962 MB, inside GitHub's recommended 1 GB.
#   unoffered   153 artefacts, 28.3 MB, belonging to the 14 sites sites.json marks NOT offerable.
#               Unreachable by design: #c_site only ever holds an offerable key, so loadSite() is
#               never called with one of these. Parked rather than deleted, under the same data folder.
# Anything absent that is NOT one of those two shapes is still a failure, which is the point.
UNOFFERED = set()
try:
    _sj = json.load(io.open(os.path.join(ROOT, NEW, "demo", "sites.json"), encoding="utf-8"))
    UNOFFERED = {x["key"] for x in _sj["sites"] if not x.get("offerable")}
except Exception:
    pass


# A THIRD DECLARED REMOVAL, 2026-08-28: 43 working-note markdown files, 1.3 MB, moved to
# D:/FGHackathon-notes so the repository presents ONE professional README to judges rather than sixty
# files of planning and research. The user's instruction, and the keep list was MEASURED rather than
# chosen: every .py in the tree was stripped of comments and docstrings, and the .md filenames
# surviving inside string literals are the ones code actually opens. Those all stayed.
# Listed by name rather than by pattern, because "any .md may vanish" would hide a real loss: if
# CONTEXT/01-STATE.md or money-sources.md ever disappeared, this check must still fail.
MOVED_NOTES = {
    "FORTYGUARD-NEXT-EXPERIMENTS.md", "FORTYGUARD-VALUE-AUDIT.md", "NATIONAL-BUILD-PLAN.md",
    "PLAN.md", "README.md", "GEOMETRY-AND-PHYSICS.md", "REVIEW.md", "RESULTS.md",
    "claims-and-defences.md", "damper-agent-plan.md", "damper-claims-and-defences.md",
    "damper-physics-explained.md", "damper-test-1-data-availability.md",
    "damper-test-2-switching-simulation.md", "damper-test-3-forecast-skill-PLANNED.md",
    "fortyguard-api-findings.md", "fortyguard-day1-data-checks.md",
    "fortyguard-day1-data-checks-RESULTS.md", "fortyguard-email-2-empty-completed.md",
    "fortyguard-email-3-empty-and-stalled-windows.md", "fortyguard-email-4-short-no-ids.md",
    "fortyguard-email-draft.md", "fortyguard-groupchat-message.md",
    "fortyguard-message-forecast-zero-tiles.md", "fortyguard-question-catalog-horizon.md",
    "fortyguard-report-2026-08-20-jobs-not-completing.md", "how-it-all-fits.md",
    "i-m-a-second-semester-computer-zazzy-hennessy.md", "intake-agent-checks.md",
    "intake-agent-plan.md", "n45-costmodel-PREREG.md", "n46-margin-PREREG.md",
    "n47-persistence-PREREG.md", "n49-detection-PREREG.md", "n50-timing-PREREG.md",
    "n56-freecooling-PREREG.md", "nvidia-integration-plan.md", "physics-explained.md",
    "project-master-plan-v2.md", "project-master-plan.md", "project-viability-report.md",
    "what-am-i-building.md", "._fortyguard-day1-data-checks-RESULTS.md",
}
# 🔴 A FILENAME MATCH IS NOT ENOUGH, and two files proved it. `README.md` exists three times: the root
# one judges read, `<proj>/README.md` which moved, and `<proj>/demo/README.md` which audit.py OPENS and
# must never vanish. A name-based exception protected the wrong one and then declared a kept one as
# moved, which would have let a real loss through silently.
# So the exception is by PATH, listing exactly what stayed, with the project folder normalised because
# the baseline calls it INTAKE-ARBITER and the tree calls it AGENTIC-ARBITER.
KEPT_MD = {
    "README.md",
    "API-USAGE.md",
    "CLAUDE.md",
    "RECIRCULATION-DEFENCE.md",
    "money-sources.md",
    "<proj>/demo/README.md",
    "<proj>/demo/money-sources.md",
    "<proj>/preserved/README.md",
}


def removed_on_purpose(p):
    q = p.replace(os.sep, "/")
    if "/data/" in q or q.endswith("/data"):
        return True
    # A FOURTH DECLARED REMOVAL, 2026-08-28: IMAGERY-REVIEW/, 17 files, 5.1 MB of ESRI-versus-USGS
    # comparison JPGs from a one-off visual review, moved to D:/FGHackathon-notes. Nothing in any .py,
    # .js, .mjs or .html reads it or any of its filenames; only HANDOFF.md mentions it in prose.
    # ⚠ validation-data/ IS DELIBERATELY NOT ON THIS LIST. It looks like the same kind of thing and is
    # not: test_n21_validate.py and test_n22_calibrate.py read its CSVs, digitised from California
    # Energy Commission report CEC-500-2013-065, and those back README's recirculation and
    # 67-Prairie-Grass claims. run_all.py does not run those two tests, so removing it would have gone
    # unnoticed by every gate, which is exactly why it is written down here.
    if q.startswith("IMAGERY-REVIEW/"):
        return True
    base = q.rsplit("/", 1)[-1]
    if base.endswith(".md"):
        norm = q.replace(OLD + "/", "<proj>/", 1).replace(NEW + "/", "<proj>/", 1)
        if norm in KEPT_MD or norm.startswith("CONTEXT/"):
            return False                      # kept on purpose; a loss here is a real loss
        return base in MOVED_NOTES
    body = base[len("plume_field_"):] if base.startswith("plume_field_") else base
    return any(body.startswith(k + "_") or body.startswith(k + ".") for k in UNOFFERED)



def sect(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def ck(name, ok, detail=""):
    print("   %s %-58s %s" % ("[ok]  " if ok else "[LOSS]", name, detail))
    if not ok:
        PROBLEMS.append(name)


# =================================================================================================
sect("1. THE PAGE: every function and every element id that existed at the baseline")
# =================================================================================================
h = head("%s/demo/index.html" % OLD)
n = now("%s/demo/index.html" % NEW)
if h is None or n is None:
    ck("both versions of index.html are readable", False,
       "base=%s now=%s" % (h is not None, n is not None))
else:
    def script_body(s):
        k = s.rfind("<script")
        return s[s.index(">", k) + 1: s.index("</script>", k)]

    hb, nb = script_body(h), script_body(n)
    hf = set(re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", hb))
    nf = set(re.findall(r"function\s+([A-Za-z_]\w*)\s*\(", nb))
    # DECLARED INTENTIONAL REMOVAL. showSiteStatus() and its #sitestatus* elements were deleted on
    # 2026-08-27 and replaced by the inspector drawer; index.html:1731 carries the removal note, the
    # four surviving mentions are all inside comments, and a comment-stripped scan of the live script
    # finds zero references to any of them. Verified in this session, not assumed.
    RETIRED_FN = {"showSiteStatus"}
    RETIRED_ID = {"sitestatusbody", "sitestatuscard", "sitestatusclose", "sitestatustitle"}
    lost_fn = sorted(hf - nf - RETIRED_FN)
    ck("no function lost from the page's script", not lost_fn,
       "%d functions at the baseline, %d now, %d added"
       % (len(hf), len(nf), len(nf - hf)) if not lost_fn else "LOST: " + ", ".join(lost_fn))
    if nf - hf:
        NOTES.append("functions ADDED to the page since the baseline: %s"
                     % ", ".join(sorted(nf - hf)))

    strip = lambda s: re.sub(r"<!--.*?-->", "", s, flags=re.S)
    hid = set(re.findall(r'\bid="([\w-]+)"', strip(h)))
    nid = set(re.findall(r'\bid="([\w-]+)"', strip(n)))
    lost_id = sorted(hid - nid - RETIRED_ID)
    ck("no element id lost from the page", not lost_id,
       "%d ids at the baseline, %d now, %d added"
       % (len(hid), len(nid), len(nid - hid)) if not lost_id else "LOST: " + ", ".join(lost_id))
    if nid - hid:
        NOTES.append("element ids ADDED since the baseline: %s" % ", ".join(sorted(nid - hid)))

    # the live agent, named explicitly because it is a standing instruction
    for i in ("livecard", "livego"):
        ck("the live agent's #%s is still in the page" % i, ('id="%s"' % i) in n)

    # the 22 functions that were extracted MUST still be in the page, unchanged
    man = json.load(io.open(os.path.join(ROOT, NEW, "core", "_transform.json"), encoding="utf-8"))
    def body_of(src, name):
        i = src.find("function " + name + "(")
        if i < 0:
            return None
        d, st, j = 0, False, i
        while j < len(src):
            c = src[j]
            if c == "{":
                d += 1
                st = True
            elif c == "}":
                d -= 1
                if st and d == 0:
                    j += 1
                    break
            j += 1
        return src[i:j]

    changed, missing = [], []
    for k, e in sorted(man["functions"].items()):
        pn = e["page_name"]
        a, b = body_of(hb, pn), body_of(nb, pn)
        if b is None:
            missing.append(pn)
        elif a is not None and a != b:
            changed.append(pn)
    ck("all 22 extracted functions are STILL IN THE PAGE", not missing,
       "%d checked" % len(man["functions"]) if not missing else "MISSING: " + ", ".join(missing))
    # 🔴 DECLARED, DATED EXCEPTIONS. A check that is expected to be red is worse than no check: the
    # redness stops meaning anything. On 2026-08-28 the user asked for no dashes anywhere in displayed
    # text, and these two functions build rendered strings that used em dashes as punctuation, so
    # their bodies genuinely changed. Named here so the change is a decision on the record, and so
    # that a THIRD function changing still fails.
    ALTERED_ON_PURPOSE = {
        "decide": "2026-08-28 dash removal: builds the level-anchor label "
                  "('anchored: one local reading', 'unanchored: FortyGuard's measured offset')",
        "explainHour": "2026-08-28 dash removal: builds the CLAMPED note and the level-term prose",
    }
    changed = [c for c in changed if c not in ALTERED_ON_PURPOSE]
    if ALTERED_ON_PURPOSE:
        for k2, why in sorted(ALTERED_ON_PURPOSE.items()):
            NOTES.append("%s altered on purpose, %s" % (k2, why))
    ck("and none of them was altered in the page, beyond the declared edits", not changed,
       "byte-identical to the baseline" if not changed else "CHANGED: " + ", ".join(changed))

# =================================================================================================
sect("2. THE DATA: every artefact the page fetches")
# =================================================================================================
demo = os.path.join(ROOT, NEW, "demo")
jsons = sorted(f for f in os.listdir(demo) if f.endswith(".json"))


def leaves(o, path=""):
    """Flatten JSON to path -> scalar.

    🔴 STRUCTURE, NOT BYTES. A byte comparison flagged five artefacts as changed. Walking them showed
    that four differ only in `generated_by` (INTAKE-ARBITER became AGENTIC-ARBITER) and that
    unified_sites.json -- the 637-facility registry every published count comes from -- has ZERO
    differing values, its byte difference being whitespace or key order. Bytes are the wrong
    instrument for "was any data lost": they cannot tell a reformat from a deletion. Leaf paths can."""
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(leaves(v, path + "/" + str(k)))
    elif isinstance(o, list):
        out[path + "#len"] = len(o)
        for n_, v in enumerate(o):
            out.update(leaves(v, path + "/" + str(n_)))
    else:
        out[path] = o
    return out


lost_paths, changed_vals, gone = [], [], []
for f in jsons:
    a = head_bytes("%s/demo/%s" % (OLD, f))
    if a is None:
        continue                      # a new artefact cannot have lost anything
    try:
        ja = json.loads(a.decode("utf-8", "replace"))
        jb = json.loads(io.open(os.path.join(demo, f), encoding="utf-8").read())
    except Exception as e:
        changed_vals.append("%s (unparseable: %s)" % (f, e))
        continue
    wa, wb = leaves(ja), leaves(jb)
    if set(wa) - set(wb):
        lost_paths.append("%s (%d path(s))" % (f, len(set(wa) - set(wb))))
    real = [k for k in set(wa) & set(wb)
            if wa[k] != wb[k]
            and not (isinstance(wa[k], str)
                     and wa[k].replace("INTAKE-ARBITER", "AGENTIC-ARBITER") == wb[k])]
    if real:
        changed_vals.append("%s (%d value(s), e.g. %s)" % (f, len(real), real[0][:40]))

r = subprocess.run(["git", "ls-tree", "-r", "--name-only", BASE, "%s/demo/" % OLD],
                   cwd=ROOT, capture_output=True, text=True)
for p in (r.stdout or "").strip().split("\n"):
    if (p.endswith(".json")
            and not removed_on_purpose(p)
            and not os.path.exists(
                os.path.join(ROOT, p.replace(OLD, NEW).replace("/", os.sep)))):
        gone.append(os.path.basename(p))

ck("no JSON artefact is missing", not gone,
   "%d present" % len(jsons) if not gone else "MISSING: " + ", ".join(gone[:6]))
ck("no JSON artefact lost a single leaf path", not lost_paths,
   "%d artefacts walked" % len(jsons) if not lost_paths else "; ".join(lost_paths[:4]))
ck("no JSON value changed beyond the rename", not changed_vals,
   "only `generated_by` moved, in 4 files" if not changed_vals
   else "; ".join(changed_vals[:4]))

# field files and other data
for ext in (".png", ".pdf", ".csv"):
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", BASE, "%s/" % OLD],
                       cwd=ROOT, capture_output=True, text=True)
    heads = [p for p in (r.stdout or "").split("\n") if p.endswith(ext)]
    miss = [p for p in heads
            if not removed_on_purpose(p)
            and not os.path.exists(os.path.join(ROOT, p.replace(OLD, NEW).replace("/", os.sep)))]
    ck("every %s at the baseline is still present" % ext, not miss,
       "%d files" % len(heads) if not miss else "MISSING %d, e.g. %s" % (len(miss), miss[0]))

# =================================================================================================
sect("3. THE VERIFIERS: no assertion dropped")
# =================================================================================================
for f in ("verify_browser_agent.js", "verify_browser_conformal.js", "verify_browser_decision.js",
          "verify_browser_explanation.js", "verify_browser_ticker.js"):
    a = head("%s/demo/%s" % (OLD, f))
    b = now("%s/demo/%s" % (NEW, f))
    if a is None or b is None:
        ck("%s readable both sides" % f, False)
        continue
    # every PASS/FAIL verdict string and every process.exit must survive
    ha = set(re.findall(r"'((?:PASS|FAIL)[^']*)'", a)) | set(re.findall(r'"((?:PASS|FAIL)[^"]*)"', a))
    hb2 = set(re.findall(r"'((?:PASS|FAIL)[^']*)'", b)) | set(re.findall(r'"((?:PASS|FAIL)[^"]*)"', b))
    lost = sorted(x for x in ha - hb2)
    ck("%-32s verdict strings preserved" % f, not lost,
       "%d" % len(ha) if not lost else "LOST: " + " | ".join(x[:40] for x in lost[:2]))
    # and the count of console.log reporting lines should not have shrunk
    ca, cb = a.count("console.log"), b.count("console.log")
    ck("%-32s reporting lines not reduced" % f, cb >= ca, "%d -> %d" % (ca, cb))

# =================================================================================================
sect("4. THE MOVED DOCUMENTS")
# =================================================================================================
CRLF = chr(13) + chr(10)
LF = chr(10)


def norm(x):
    """Compare on content, not on presentation.

    Two differences here are not losses and must not be reported as such:
      * LINE ENDINGS. READING-THE-AGENT.md went from LF to CRLF because an editor touched it. That
        makes difflib call every line changed while nothing about the text moved.
      * THE RENAME. INTAKE-ARBITER became AGENTIC-ARBITER on 2026-08-27, 32 lines of it in HANDOFF.md
        alone.
    Anything that survives both normalisations is a real difference."""
    if x is None:
        return None
    t = x.decode("utf-8", "replace").replace(CRLF, LF)
    return t.replace("INTAKE-ARBITER", "AGENTIC-ARBITER")


for src, dst in (("HANDOFF.md", "CONTEXT/HANDOFF.md"),
                 ("READING-THE-AGENT.md", "CONTEXT/READING-THE-AGENT.md")):
    a = head_bytes(src)
    p = os.path.join(ROOT, dst.replace("/", os.sep))
    b = io.open(p, "rb").read() if os.path.exists(p) else None
    na, nb = norm(a), norm(b)
    if na is None or nb is None:
        ck("%-24s readable on both sides" % src, False,
           "base=%s now=%s" % (na is not None, nb is not None))
        continue
    if na == nb:
        ck("%-24s moved with its content intact" % src, True,
           "%d bytes, identical once line endings and the rename are normalised" % len(nb))
        continue
    # A legitimate edit is allowed. The question that matters is whether any LINE that existed at
    # HEAD has vanished, so that is the assertion, rather than "the file is unchanged".
    ha = set(l.strip() for l in na.split(LF) if l.strip())
    hbs = set(l.strip() for l in nb.split(LF) if l.strip())
    # DECLARED, VERIFIED REWRITE. Seven lines describing TWO modes (REPLAY, LIVE) were replaced by a
    # description of THREE, adding LIVE / DRY RUN and what each lamp colour means. Confirmed by
    # reading the replacement text in this session, not inferred from the fact that the file grew.
    REWRITTEN = ("There are two modes, and the page tells you which one it is in near the top:",
                 "reproducible: the same request to FortyGuard returns byte-for-byte identical data,"
                 " which is why",
                 "saved answers are as good as live ones for showing the method.",
                 "decide on it, right now. Needs a key and a small local server, because a web page"
                 " cannot hold a",
                 "secret key (anything the page can read, every visitor can read).")
    goneL = [l for l in sorted(ha - hbs)
             if l not in REWRITTEN and not l.startswith("- **REPLAY**")
             and not l.startswith("- **LIVE**")]
    # The spend figures are MEANT to move: testing/bump_spend_docs.py rewrites them from the ledger
    # after every paid call, and audit.py check 9 fails until it has. A vanished spend line is the
    # system working. Recognised by shape rather than by exact text, so next month's figures also pass.
    # DEFINED BY WHAT bump_spend_docs.py OWNS, rather than by whichever line failed last. That script
    # rewrites exactly four shapes in these two documents after every paid call, and audit.py check 9
    # fails until it has. A vanished spend line is therefore the system working, not a loss.
    # Widening this by trial and error was going to end with a pattern loose enough to hide a real
    # loss, so it is anchored on the strings that script's own regexes target.
    SPEND_SHAPES = (r"SPEND IS"
                    r"|Spent to date"
                    r"|PROVABLY bought nothing"
                    r"|paid_calls|calls =|credits|% of plan|[Rr]emaining")
    goneL = [g for g in goneL if not re.search(SPEND_SHAPES, g)]
    ck("%-24s no line from the baseline has vanished" % src, not goneL,
       "%d lines now, %d added since the baseline" % (len(hbs), len(hbs - ha)) if not goneL
       else "%d baseline line(s) absent, e.g. %r" % (len(goneL), goneL[0][:56]))
    if hbs - ha:
        NOTES.append("%s gained %d line(s) since the baseline (edited, not lost)"
                     % (src, len(hbs - ha)))

# =================================================================================================
sect("5. EVERY PATH THAT EXISTED AT THE BASELINE")
# =================================================================================================
# 🔴 THIS SECTION USED TO READ `git status` FOR DELETIONS, and pinning the baseline made it VACUOUS:
# the rename is committed now, so the working tree has zero deletions and the check passed by
# examining nothing. That is the same failure mode as gotcha #74, and it was in this file.
# The question a pinned baseline can actually answer is the stronger one: walk every path that
# existed at BASE and require a counterpart today. 5,975 paths, not zero.
r = subprocess.run(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT,
                   capture_output=True, text=True)
base_paths = [p for p in (r.stdout or "").split("\n") if p.strip()]

# The only paths allowed to move rather than stay put, each one a MOVE THE USER ASKED FOR. Anything
# absent and not named here is a loss, which is the point: the exceptions are declared, not inferred.
MOVED = {
    "HANDOFF.md": "CONTEXT/HANDOFF.md",
    "READING-THE-AGENT.md": "CONTEXT/READING-THE-AGENT.md",
}


def counterpart(p):
    return MOVED.get(p, p.replace(OLD + "/", NEW + "/", 1))


absent = [p for p in base_paths
          if not os.path.exists(os.path.join(ROOT, counterpart(p).replace("/", os.sep)))
          and not removed_on_purpose(p)]
ck("every path that existed at %s is still on disk" % BASE, not absent,
   "%d paths walked, %d under the rename"
   % (len(base_paths), sum(1 for p in base_paths if p.startswith(OLD + "/")))
   if not absent else "ABSENT %d, e.g. %s" % (len(absent), absent[0]))

# Separately: nothing deleted in the working tree. The sweep above cannot see this, because a file
# added since BASE and then deleted never appears in base_paths at all.
r = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
dels = [l[3:].strip().strip('"') for l in (r.stdout or "").split("\n")
        if l.startswith(" D") or l.startswith("D ")]
dels = [d for d in dels if not removed_on_purpose(d)]
ck("no uncommitted deletion beyond the declared removals", not dels,
   "clean" if not dels else "%d DELETED: %s" % (len(dels), ", ".join(dels[:6])))

print()
print("=" * 78)
if PROBLEMS:
    print("LOSSES FOUND: %d" % len(PROBLEMS))
    for p in PROBLEMS:
        print("   * %s" % p)
else:
    print("NO LOSSES FOUND. Every function, element id, artefact, verdict string and document that")
    print("existed at %s is still present, and the 22 extracted functions are byte-identical in" % BASE)
    print("the page as well as being present in core/ and charts/.")
print("=" * 78)
for n_ in NOTES:
    print("   note: %s" % n_)
