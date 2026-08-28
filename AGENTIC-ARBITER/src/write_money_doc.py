# -*- coding: utf-8 -*-
"""Write the LIMITS and SOURCES sections of money-sources.md from money.json. ZERO API CALLS.

    python write_money_doc.py            # rewrite the generated blocks
    python write_money_doc.py --check    # exit 1 if they are stale, write nothing

WHY THIS EXISTS
---------------
The money panel used to print three blocks on screen: the 608-cell sweep with its worst cell, the
seven-item "What this is NOT", and the four parsed sources. They were removed from the card on
2026-08-25 at the user's direction -- the panel is for the figure, and 400 words of provenance under
it is a document, not a panel.

Moving a disclosure is only legitimate if it ARRIVES. `money-sources.md` already existed and was
already linked from README, but it was hand-written on 2026-08-20 and had drifted: it carried two of
the four sources and NONE of the seven caveats verbatim. Had the card simply been emptied, five
sourced limitations and two citations would have left the repository's reader-facing surface
altogether and nobody would have noticed.

So the two sections are GENERATED from `money.json` between markers, and `audit.py` asserts that
every `not_claimed` item and every source title is present in the file. The prose around them stays
hand-written -- it explains the derivation, which is not something a generator should be guessing at.

WHY NOT money.py
----------------
`money.py` writes `money.json`, and running it would rewrite that artefact for whichever metro is
selected. A national batch is usually in flight, and a regenerated artefact mid-batch is how sites
built before and after a change stop agreeing. This reads the artefact and touches one markdown
file, so it is safe to run at any time.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
ROOT = os.path.dirname(IA)
DOC = os.path.join(ROOT, "money-sources.md")
DEMO_DOC = os.path.join(IA, "demo", "money-sources.md")   # served copy, see main()
MONEY = os.path.join(IA, "demo", "money.json")

# The markers are HTML comments so they render as nothing on GitHub, and they are matched exactly.
# A missing marker is an error rather than an append: silently adding a second copy of a section is
# how a document ends up contradicting itself further down.
LIM_A, LIM_B = "<!-- GENERATED:LIMITS start -->", "<!-- GENERATED:LIMITS end -->"
SRC_A, SRC_B = "<!-- GENERATED:SOURCES start -->", "<!-- GENERATED:SOURCES end -->"


def limits_block(m):
    out = ["", "### What this is NOT",
           "",
           "*Every item below is read from `money.json`'s `not_claimed` array by "
           "`src/write_money_doc.py`. None of it is written here by hand, so the list cannot drift "
           "from the artefact the figure comes from.*", ""]
    for x in m["not_claimed"]:
        out.append("- %s" % x)
    worst = min((c for c in m["cells"] if c["family"] == "12-axis sensitivity"),
                key=lambda c: c["usd_per_mw_it_per_year"])
    out += ["",
            "### The sweep, and its worst cell",
            "",
            "**%s cells** — every ladder and sensitivity row × %d published chiller efficiencies × "
            "%d published prices, **and no row is collapsed**. The demo's table shows the anchored "
            "ladder steps at the selected cell; the sweep behind it is wider and includes rows that "
            "come out negative."
            % (format(len(m["cells"]), ","), len(m["chiller_efficiencies_swept"]),
               len(m["electricity_prices_swept"])),
            "",
            "The worst cell anywhere in it is **−$%s per MW of IT load per year**, at *%s* — the "
            "refusal guard firing, on the %s chiller at the %s tariff. A money figure that could "
            "not show that number would not be worth reading."
            % (format(int(round(abs(worst["usd_per_mw_it_per_year"]))), ","),
               worst["hours_label"], worst["chiller"], worst["price_label"]),
            ""]
    return "\n".join(out)


def sources_block(m):
    out = ["", "### Sources, each downloaded and parsed in this repository",
           "",
           "*Generated from `money.json`'s `sources` block. `how_read` is the actual extraction "
           "method, recorded so anyone can repeat it and get the same characters.*", ""]
    groups = (("Electricity price", "electricity_price"),
              ("Chiller efficiency", "chiller_efficiency"),
              ("Context only — NOT used in any figure", "context_only"))
    for label, key in groups:
        rows = m["sources"].get(key) or []
        if not rows:
            continue
        out += ["#### %s" % label, ""]
        for s in rows:
            out.append("- **[%s](%s)** — %s" % (s["title"], s["url"], s["publisher"]))
            out.append("  - *How it was read:* %s." % s["how_read"])
            for extra in ("note", "rating_conditions", "what_it_gives", "what_it_does_NOT_give"):
                if s.get(extra):
                    out.append("  - *%s:* %s" % (extra.replace("_", " "), s[extra]))
        out.append("")
    return "\n".join(out)


def splice(txt, a, b, body, label):
    if a not in txt or b not in txt:
        raise SystemExit("marker %s missing from money-sources.md -- add it, do not let this "
                         "append a second %s section" % (a, label))
    i, j = txt.index(a) + len(a), txt.index(b)
    return txt[:i] + body + txt[j:]


def main(argv):
    m = json.load(open(MONEY, encoding="utf-8"))
    txt = io.open(DOC, encoding="utf-8").read()
    new = splice(txt, LIM_A, LIM_B, limits_block(m), "limits")
    new = splice(new, SRC_A, SRC_B, sources_block(m), "sources")
    if "--check" in argv:
        served = io.open(DEMO_DOC, encoding="utf-8").read() if os.path.exists(DEMO_DOC) else None
        same = (new == txt) and (served == new)
        print("money-sources.md is %s%s"
              % ("current" if new == txt else "STALE",
                 "" if served == new else "; the served copy in demo/ does NOT match"))
        return 0 if same else 1
    if new != txt:
        io.open(DOC, "w", encoding="utf-8", newline="").write(new)
        print("money-sources.md: %d not_claimed items and %d sources written from money.json"
              % (len(m["not_claimed"]), sum(len(v) for v in m["sources"].values())))
    else:
        print("money-sources.md already current")
    # A SERVED COPY, because the demo's document root is `demo/` and the money panel links to this
    # file. `href="../../money-sources.md"` escapes the root and 404s under both `http.server` and
    # `serve_live.py` -- measured, not assumed. The alternatives were a broken link on a
    # judge-facing panel or a hand-maintained duplicate, and a duplicate written by the same
    # generator that writes the original is neither: `audit.py` asserts the two are byte-identical,
    # so they cannot drift the way the hand-written original drifted from money.json.
    io.open(DEMO_DOC, "w", encoding="utf-8", newline="").write(new)
    print("   served copy -> %s" % os.path.relpath(DEMO_DOC, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
