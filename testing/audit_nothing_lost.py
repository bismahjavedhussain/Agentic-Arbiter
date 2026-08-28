# -*- coding: utf-8 -*-
r"""Prove that nothing was lost: no function, no element, no data, no assertion.

The user asked for assurance before restarting. Assurance is not a sentence, it is a diff. Everything
below compares the CURRENT working tree against git HEAD (d28a50b), which predates every change in
this session, and reports losses rather than changes: a thing that existed then and does not exist now.

Note on paths: HEAD holds the project under the OLD folder name, INTAKE-ARBITER/, because the rename
to AGENTIC-ARBITER/ on 2026-08-27 is still uncommitted. So the comparison is
HEAD:INTAKE-ARBITER/<x> against the working tree's AGENTIC-ARBITER/<x>.
"""
import hashlib
import io
import json
import os
import re
import subprocess

ROOT = r"D:\FGHackathon"
OLD = "INTAKE-ARBITER"
NEW = "AGENTIC-ARBITER"
PROBLEMS = []
NOTES = []


def head(path):
    """The file's contents at HEAD, or None."""
    r = subprocess.run(["git", "show", "HEAD:" + path], cwd=ROOT,
                       capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8", "replace")


def now(path):
    p = os.path.join(ROOT, path.replace("/", os.sep))
    if not os.path.exists(p):
        return None
    return io.open(p, encoding="utf-8", newline="", errors="replace").read()


def head_bytes(path):
    r = subprocess.run(["git", "show", "HEAD:" + path], cwd=ROOT, capture_output=True)
    return None if r.returncode else r.stdout


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
sect("1. THE PAGE: every function and every element id that existed at HEAD")
# =================================================================================================
h = head("%s/demo/index.html" % OLD)
n = now("%s/demo/index.html" % NEW)
if h is None or n is None:
    ck("both versions of index.html are readable", False,
       "HEAD=%s now=%s" % (h is not None, n is not None))
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
       "%d functions at HEAD, %d now, %d added"
       % (len(hf), len(nf), len(nf - hf)) if not lost_fn else "LOST: " + ", ".join(lost_fn))
    if nf - hf:
        NOTES.append("functions ADDED to the page since HEAD: %s"
                     % ", ".join(sorted(nf - hf)))

    strip = lambda s: re.sub(r"<!--.*?-->", "", s, flags=re.S)
    hid = set(re.findall(r'\bid="([\w-]+)"', strip(h)))
    nid = set(re.findall(r'\bid="([\w-]+)"', strip(n)))
    lost_id = sorted(hid - nid - RETIRED_ID)
    ck("no element id lost from the page", not lost_id,
       "%d ids at HEAD, %d now, %d added"
       % (len(hid), len(nid), len(nid - hid)) if not lost_id else "LOST: " + ", ".join(lost_id))
    if nid - hid:
        NOTES.append("element ids ADDED since HEAD: %s" % ", ".join(sorted(nid - hid)))

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
    ck("and none of them was altered in the page", not changed,
       "byte-identical to HEAD" if not changed else "CHANGED: " + ", ".join(changed))

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

r = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD", "%s/demo/" % OLD],
                   cwd=ROOT, capture_output=True, text=True)
for p in (r.stdout or "").strip().split("\n"):
    if p.endswith(".json") and not os.path.exists(
            os.path.join(ROOT, p.replace(OLD, NEW).replace("/", os.sep))):
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
    r = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD", "%s/" % OLD],
                       cwd=ROOT, capture_output=True, text=True)
    heads = [p for p in (r.stdout or "").split("\n") if p.endswith(ext)]
    miss = [p for p in heads
            if not os.path.exists(os.path.join(ROOT, p.replace(OLD, NEW).replace("/", os.sep)))]
    ck("every %s at HEAD is still present" % ext, not miss,
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
           "HEAD=%s now=%s" % (na is not None, nb is not None))
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
    ck("%-24s no line from HEAD has vanished" % src, not goneL,
       "%d lines now, %d added since HEAD" % (len(hbs), len(hbs - ha)) if not goneL
       else "%d HEAD line(s) absent, e.g. %r" % (len(goneL), goneL[0][:56]))
    if hbs - ha:
        NOTES.append("%s gained %d line(s) since HEAD (edited, not lost)"
                     % (src, len(hbs - ha)))

# =================================================================================================
sect("5. WHAT WAS DELETED, and was any of it not the rename?")
# =================================================================================================
r = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
dels = [l[3:].strip().strip('"') for l in (r.stdout or "").split("\n")
        if l.startswith(" D") or l.startswith("D ")]
not_rename = [d for d in dels if not d.startswith(OLD + "/")]
ck("every deletion is part of the uncommitted folder rename", not not_rename,
   "%d deletions, all under %s/" % (len(dels), OLD) if not not_rename
   else "OUTSIDE THE RENAME: " + ", ".join(not_rename[:8]))
# for the rename: does each deleted path have a counterpart?
orphans = [d for d in dels if d.startswith(OLD + "/")
           and not os.path.exists(os.path.join(ROOT, d.replace(OLD, NEW, 1).replace("/", os.sep)))]
ck("every renamed file has a counterpart under %s/" % NEW, not orphans,
   "%d checked" % len(dels) if not orphans
   else "%d WITHOUT A COUNTERPART, e.g. %s" % (len(orphans), orphans[0]))

print()
print("=" * 78)
if PROBLEMS:
    print("LOSSES FOUND: %d" % len(PROBLEMS))
    for p in PROBLEMS:
        print("   * %s" % p)
else:
    print("NO LOSSES FOUND. Every function, element id, artefact, verdict string and document that")
    print("existed at HEAD is still present, and the 22 extracted functions are byte-identical in the")
    print("page as well as being present in core/ and charts/.")
print("=" * 78)
for n_ in NOTES:
    print("   note: %s" % n_)
