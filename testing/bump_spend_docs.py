"""Rewrite the API-spend figures in API-USAGE.md and HANDOFF.md from the ledger. Zero API calls.

    python testing/api_usage_ledger.py --json     # first: re-derive the ledger from the meter
    python testing/bump_spend_docs.py             # then: put its numbers in the documents

WHY THIS EXISTS
---------------
Every paid `live.py` run moves the spend total. `audit.py` check 9 then fails until four figures are
corrected in two documents -- and the fix is correct, because §8.2's rule is that a number no test
re-reads will drift. But hand-editing four numbers after every run is the wrong shape of work: I did
it twice, made an arithmetic slip neither time only because the audit was watching, and it will
recur every time the agent runs live.

So the CHECK stays -- it is what catches a forgotten update -- and the UPDATE becomes one command.
The two are deliberately separate: a script that both wrote the numbers and verified them would be
checking its own homework.

HOW IT MATCHES
--------------
By regex on the ROW LABEL, never on the current value. An earlier version searched for the literal
figures it was replacing, which made it a one-shot: it worked once and then silently matched
nothing. A tool that becomes a no-op without saying so is worse than one that fails.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def money(n):
    return format(int(n), ",")


def sub_or_report(text, pattern, repl, label, misses):
    r"""Substitute once, or record that nothing matched. Never silently no-op.

    🔴 THE REPLACEMENT IS A CALLABLE, NOT A STRING, AND THAT IS THE WHOLE POINT.
    This function used to do `repl.replace("\\", "\\\\")`, intending to protect against a stray
    backslash in the data. What it actually did was escape the `\g<1>` group references in the
    replacement templates, so `re.subn` inserted the LITERAL TEXT `\g<1>26\g<2>` into API-USAGE.md
    -- seven table rows of visible garbage in a submission document, written by the tool whose job
    was to keep that document correct.

    A callable replacement is not interpreted for escapes at all, which removes the whole class of
    error. It also means group references have to be resolved by hand via `m.expand()`, which is
    the price of never having to reason about backslash depth again.
    """
    def _repl(m):
        return m.expand(repl)

    out, n = re.subn(pattern, _repl, text, count=1)
    if n != 1:
        misses.append(label)
    return out


def main():
    up = os.path.join(HERE, "results", "api_usage.json")
    if not os.path.exists(up):
        print("no ledger output at %s -- run api_usage_ledger.py --json first" % up)
        return 1
    u = json.load(open(up, encoding="utf-8"))
    calls, spent, rem, pct = (u["paid_calls"], u["spent"], u["remaining"], u["pct_of_plan"])
    data = u["calls_returning_data"]
    empty = u["calls_returning_zero_tiles_meter_stamped"]
    unattr = u["calls_not_individually_identified"]
    floor = u["credits_that_bought_no_data_floor"]
    ceil = u["credits_that_bought_no_data_ceiling"]
    misses = []

    print("ledger: %d calls, %s credits, %.2f %% of plan, %s remaining"
          % (calls, money(spent), pct, money(rem)))

    # ---- API-USAGE.md
    p = os.path.join(ROOT, "API-USAGE.md")
    t = io.open(p, encoding="utf-8").read()
    for pat, rep, label in (
        (r"(\| \*\*Paid calls made\*\* \| \*\*)\d[\d,]*(\*\* \|)",
         r"\g<1>%d\g<2>" % calls, "paid calls"),
        (r"(\| \*\*Credits spent\*\* \| \*\*)[\d,]+(\*\* \|)",
         r"\g<1>%s\g<2>" % money(spent), "credits spent"),
        (r"(\| \*\*Share of the plan used\*\* \| \*\*)[\d.]+( %\*\* \|)",
         r"\g<1>%.2f\g<2>" % pct, "share of plan"),
        (r"(\| Credits remaining \| \*\*)[\d,]+(\*\* \|)",
         r"\g<1>%s\g<2>" % money(rem), "credits remaining"),
        (r"\*\*All \d+ paid calls on this plan were `/v1/heatmap`\.\*\* That is not an assumption: "
         r"[\d,]+ ÷ 4,220 =\n\*\*\d+ exactly\*\*",
         "**All %d paid calls on this plan were `/v1/heatmap`.** That is not an assumption: "
         "%s ÷ 4,220 =\n**%d exactly**" % (calls, money(spent), calls), "division proof"),
        (r"## 3\. The \d+ calls, itemised",
         "## 3. The %d calls, itemised" % calls, "section 3 heading"),
        (r"(\| Returned a populated field, tile count saved \| \*\*)\d+(\*\* \| )[\d,]+( \|)",
         r"\g<1>%d\g<2>%s\g<3>" % (data, money(data * 4220)), "populated field row"),
        (r"(\| Returned `completed` with \*\*zero\*\* features, individually attributed \| \*\*)\d+"
         r"(\*\* \| )[\d,]+( \|)",
         r"\g<1>%d\g<2>%s\g<3>" % (empty, money(empty * 4220)), "zero features row"),
        (r"(\| Not individually attributable — a gap between two readings \| \*\*)\d+"
         r"(\*\* \| )[\d,]+( \|)",
         r"\g<1>%d\g<2>%s\g<3>" % (unattr, money(unattr * 4220)), "unattributable row"),
        (r"So \*\*[\d.]+ %\*\* of spend is \*proven\* to have bought nothing, and the ceiling — if "
         r"every unattributable\ncall also failed — is \*\*[\d.]+ %\*\*\.",
         "So **%.1f %%** of spend is *proven* to have bought nothing, and the ceiling — if "
         "every unattributable\ncall also failed — is **%.1f %%**."
         % (100.0 * floor / spent, 100.0 * ceil / spent), "floor/ceiling sentence"),
    ):
        t = sub_or_report(t, pat, rep, "API-USAGE: " + label, misses)
    io.open(p, "w", encoding="utf-8", newline="").write(t)

    # ---- HANDOFF.md
    p = os.path.join(ROOT, "HANDOFF.md")
    t = io.open(p, encoding="utf-8").read()
    t = sub_or_report(
        t, r"\| \*\*Spent to date\*\* \| 🔴 \*\*[\d,]+ = \d+ calls = [\d.]+ %\.\*\* Remaining "
           r"\*\*[\d,]+\*\*\.",
        "| **Spent to date** | \U0001f534 **%s = %d calls = %.2f %%.** Remaining **%s**."
        % (money(spent), calls, pct, money(rem)), "HANDOFF: spent to date", misses)
    t = sub_or_report(
        t, r"\| \*\*⚠ Of that, [\d,]+ PROVABLY bought nothing\*\* \| \*\*[\d.]+ %\*\* of spend\. "
           r"Ceiling \*\*[\d,]+ = [\d.]+ %\*\*\.",
        "| **⚠ Of that, %s PROVABLY bought nothing** | **%.1f %%** of spend. Ceiling "
        "**%s = %.1f %%**." % (money(floor), 100.0 * floor / spent,
                               money(ceil), 100.0 * ceil / spent),
        "HANDOFF: floor/ceiling row", misses)
    io.open(p, "w", encoding="utf-8", newline="").write(t)

    if misses:
        # PLAIN ASCII, deliberately. The first version printed a red-circle emoji here and
        # UnicodeEncodeError'd on the cp1252 Windows console -- so the diagnostic crashed while
        # reporting the problem it existed to report, and hid which patterns had failed. A failure
        # path is the LAST place to spend a character the terminal may not have.
        print("\n*** %d PATTERN(S) DID NOT MATCH -- those figures were NOT updated:"
              % len(misses))
        for m in misses:
            print("   %s" % m)
        print("   Fix the pattern or the document; do not assume the number is current.")
        return 1
    print("both documents updated. Now re-run audit.py check 9 to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
