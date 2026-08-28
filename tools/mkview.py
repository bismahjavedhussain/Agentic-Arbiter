# -*- coding: utf-8 -*-
"""Lift the CONFIGURE and RESULTS markup out of demo/index.html for the React app to render.

WHY THE MARKUP HAS TO BE LIFTED TOO, not rewritten as JSX. The 100 engine functions in
results/engine.mjs find their targets by element id -- 215 `$('#...')` lookups -- and write into them
with innerHTML and canvas contexts. Retyping 61 KB of markup as components would mean retyping 145
ids, and a single typo produces a panel that silently draws nothing. audit.py would not catch it,
because audit.py checks the numbers in the page, not the ids in a rebuild.

So the markup travels verbatim, hashed, with a verifier. React renders it once into a container and
never re-renders its children: the engine owns what is inside. That is the ordinary pattern for
driving a non-React widget, and here it is also the thing that keeps 2,215 checks meaningful.

WHAT IS TAKEN: every `[data-show]` element whose stage is not exactly "pick", plus the few
engine-owned elements that live outside those (the tooltip, the mode banner, the loading line, the
site plate, the section rail). WHAT IS LEFT: the two pick cards, the masthead and the theme button.
React ships its own, and its containers carry `data-show="pick"` so the engine's setStage() keeps
being the single owner of what is visible.

TAG MATCHING IS SAME-NAME COUNTING, not a tree walk. A depth counter over all tags drifts on HTML's
implicitly-closed elements and reported the whole body as four elements; counting only `<div`/`</div>`
for a div is exact for this job.
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
APPGEN = os.path.join(AA, "app", "src", "generated")
os.makedirs(APPGEN, exist_ok=True)

page = io.open(os.path.join(DEMO, "index.html"), encoding="utf-8", newline="").read()
b0 = page.index(">", page.index("<body")) + 1
k = page.rfind("<script")
M = page[b0:k]


# 🔴 MATCH OVER A COMMENT-MASKED COPY. This page documents itself heavily, and an HTML comment can
# contain anything -- including text that looks like a tag. The first attempt counted tags inside
# comments and could not close `<div data-show="configure results">` at all. So tag matching runs
# against MASK, where every comment is blanked to spaces of the same length, and the slice is taken
# from M. Offsets stay identical, and the comments survive in the output, where they are worth having.
MASK = re.sub(r"<!--.*?-->", lambda mo: " " * len(mo.group(0)), M, flags=re.S)
assert len(MASK) == len(M), "the mask must preserve offsets exactly"


def outer(start):
    """From the '<' of an opening tag to just past its matching close, counting same-name tags."""
    m = re.match(r"<([a-zA-Z][a-zA-Z0-9]*)\b", MASK[start:])
    if not m:
        return None
    tag = m.group(1)
    op = re.compile(r"<" + tag + r"\b", re.I)
    cl = re.compile(r"</" + tag + r"\s*>", re.I)
    depth = 0
    i = start
    while i < len(MASK):
        mo = op.search(MASK, i)
        mc = cl.search(MASK, i)
        if mc is None:
            return None
        if mo is not None and mo.start() < mc.start():
            depth += 1
            i = mo.end()
            continue
        depth -= 1
        if depth == 0:
            return (start, mc.end())
        i = mc.end()
    return None


# ---- what to take -------------------------------------------------------------------------------
spans = []      # (start, end, label)

for m in re.finditer(r'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*\bdata-show="([a-z ]+)"', M):
    stage = m.group(1).strip()
    if stage == "pick":
        continue                       # React's own pick screen carries this
    sp = outer(m.start())
    if sp is None:
        raise SystemExit("!! could not close the element at %d (stage %r)" % (m.start(), stage))
    idm = re.search(r'\bid="([A-Za-z0-9_]+)"', M[sp[0]:sp[0] + 240])
    spans.append((sp[0], sp[1], (idm.group(1) if idm else "stage:" + stage)))

# the engine-owned elements that are not inside a [data-show] card
# 🔴 #modebanner AND #loading ARE DELIBERATELY NOT LIFTED, because React already says both things and
# two copies on one screen is worse than either. Seen in a screenshot of the configure stage: a stale
# "Loading saved data..." card across the top, and "Running in REPLAY, 0 live API calls" printed twice.
#   #loading   nothing in the engine references it at all -- the page hides it in boot(), which is
#              fenced -- and React's own "Loading saved data" state covers it.
#   #modebanner drawModeBanner() opens with `const el = $('#modebanner'); if(!el) return;`, so its
#              absence is already handled, and React's masthead carries the mode line the brief asks
#              for ("ending on the live-agent line").
#   #plate    THE FIVE CARDS THE USER SAW TWICE. drawPlate() renders the same five metrics the React
#             KPI cards already show, so the pick screen carried them once from React and once from
#             the engine. Their words: "the same cards are repeated as if you have copied the html
#             from here onwards. This tab of 'Pick a site' is what already exists above, so this must
#             not be on the first page." Both drawPlate() and animatePlate() open with
#             `if(!el) return;`, so dropping it is already handled.
EXTRA = ["tt", "rail"]
for eid in EXTRA:
    m = re.search(r'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*\bid="' + eid + r'"', M)
    if not m:
        print("   note: #%s not found in the markup" % eid)
        continue
    sp = outer(m.start())
    if sp is None:
        raise SystemExit("!! could not close #%s" % eid)
    spans.append((sp[0], sp[1], eid))

# ---- drop anything already contained in another span --------------------------------------------
spans.sort()
kept = []
for a, b, lab in spans:
    if any(qa <= a and b <= qb for qa, qb, _ in kept):
        print("   note: #%s is nested inside an already-taken span, skipped" % lab)
        continue
    kept.append((a, b, lab))

# and assert nothing partially overlaps, which would mean a mis-closed tag
for i in range(1, len(kept)):
    if kept[i][0] < kept[i - 1][1]:
        raise SystemExit("!! spans partially overlap: %s and %s" % (kept[i - 1][2], kept[i][2]))

html = "\n".join(M[a:b] for a, b, _ in kept)
ids = re.findall(r'\bid="([A-Za-z0-9_]+)"', html)
sha = hashlib.sha256(html.encode("utf-8")).hexdigest()

TS = '''/* GENERATED by tools/mkview.py. Do not edit.
 *
 * The configure and results markup, lifted VERBATIM out of AGENTIC-ARBITER/demo/index.html.
 *
 * WHY IT IS A STRING AND NOT JSX. results/engine.mjs finds every target by element id -- %d ids
 * across these sections -- and writes into them with innerHTML and canvas contexts. Retyping this as
 * components would mean retyping those ids, and one typo yields a panel that silently draws nothing:
 * audit.py checks the numbers in the page, not the ids in a rebuild. So it travels as text, hashed,
 * with testing/verify_view_matches_page.py asserting it still matches the page.
 *
 * React renders this ONCE and never re-renders its children. The engine owns what is inside.
 * Visibility is still the engine's setStage(), which walks [data-show] -- so the React pick screen
 * carries data-show="pick" and there remains exactly one owner of what is on screen.
 */
export const ENGINE_MARKUP_SHA256 = %s;

/* The six lifted blocks, kept SEPARATE as well as joined. A span begins at the '<' of its opening
 * tag, so a block can be a FRAGMENT of a page line rather than a whole one -- #modebanner is a span
 * sitting mid-line. That makes a line-by-line comparison against the page the wrong instrument, and
 * it reported a false orphan. Keeping the blocks lets the verifier assert the honest thing: each one
 * is still a verbatim substring of the page. */
export const ENGINE_MARKUP_SECTIONS: string[] = %s;

export const ENGINE_MARKUP: string = ENGINE_MARKUP_SECTIONS.join(NL);
''' % (len(set(ids)), json.dumps(sha), json.dumps([M[a:b] for a, b, _ in kept], indent=2))

# NL rather than a "\n" written into the template: editing this file through a shell has mangled
# backslash escapes eight times in this project (CONTEXT/05-TRAPS.md 5.4), and the last time it turned
# `join("\n")` into a join across a real line break, which is not valid TypeScript. Emitting the
# constant means there is no escape in the template for a shell to eat.
TS = TS.replace("ENGINE_MARKUP_SECTIONS.join(NL)",
                'ENGINE_MARKUP_SECTIONS.join(' + json.dumps(chr(10)) + ')')

io.open(os.path.join(APPGEN, "engine-markup.ts"), "w", encoding="utf-8", newline="\n").write(TS)

# ---- the stylesheet, verbatim ---------------------------------------------------------------------
# 🔴 THE MARKUP WITHOUT THE CSS IS 39 KB OF UNSTYLED DIVS. The lifted sections use 37 of the page's
# classes statically, and the engine generates markup at runtime using more (.ev, .live, .tile, .warn,
# .err). Retyping any of that in Tailwind would be a redesign of the panels the brief says not to
# touch: "Do not modify the existing reports, graphs, or numerical data cards."
#
# IT LIFTS CLEANLY BECAUSE THE PAGE'S CSS IS SELF-CONTAINED: zero url() references, and its own
# comment records why -- "no @font-face, no @import anywhere in this file", because the page must work
# offline and verify_site_panels.py demands byte-identical canvases, which a font arriving over the
# network cannot promise. So there are no paths to rewrite for a file served from a different folder.
#
# It is emitted as real CSS rather than an injected string so that Vite bundles it, and imported
# BEFORE the app's own index.css so that on any collision the new design wins.
sm = re.search(r"<style[^>]*>", page)
css = page[sm.end(): page.index("</style>", sm.start())]
css_sha = hashlib.sha256(css.encode("utf-8")).hexdigest()
CSSHDR = """/* GENERATED by tools/mkview.py. Do not edit.
 *
 * The page's stylesheet, lifted verbatim from AGENTIC-ARBITER/demo/index.html, because the configure
 * and results markup in engine-markup.ts is written against these classes and these tokens. Rewriting
 * them in Tailwind would be a redesign of the very panels the brief protects.
 *
 * Imported BEFORE src/index.css on purpose: where the two define the same thing, the app's own design
 * is meant to win. The tokens are not in conflict by accident -- testing/verify_palette.py asserts 34
 * page/app colour pairs agree.
 */
"""
io.open(os.path.join(APPGEN, "engine.css"), "w", encoding="utf-8", newline="\n").write(
    CSSHDR + css)

man = {
    "generated_by": "tools/mkview.py",
    "source": "AGENTIC-ARBITER/demo/index.html",
    "sha256": sha,
    "css_sha256": css_sha,
    "css_bytes": len(css.encode("utf-8")),
    "bytes": len(html.encode("utf-8")),
    "sections": [lab for _a, _b, lab in kept],
    "unique_ids": sorted(set(ids)),
}
io.open(os.path.join(APPGEN, "engine-markup.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(man, indent=2, sort_keys=True) + "\n")

print()
print("app/src/generated/engine-markup.ts   %.1f KB, %d sections, %d unique ids"
      % (len(html) / 1024.0, len(kept), len(set(ids))))
CLS = re.compile("[.]([a-z][a-z0-9-]{1,24})" + chr(92) + "b")
# chr(92)+"b" rather than a written escape: the previous version of this very line was
# edited through a shell and  arrived as a literal BACKSPACE character, so the regex
# matched nothing and reported 0 classes in a 96 KB stylesheet. Trap 5.4, ninth time.
print("app/src/generated/engine.css         %.1f KB, %d classes, %d url() references"
      % (len(css) / 1024.0, len(set(CLS.findall(css))), len(re.findall("url" + chr(92) + "(", css))))
print("sections in page order:")
for i in range(0, len(kept), 4):
    print("   " + ", ".join(lab for _a, _b, lab in kept[i:i + 4]))
