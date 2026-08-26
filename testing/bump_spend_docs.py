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
    # THE PLAN IS MIXED-PRICE SINCE DIAG-65, AND THIS SCRIPT USED TO DENY IT. Three of its
    # templates hardcoded the pure-heatmap era: the "division proof" paragraph asserted that
    # 4,220 divided the total exactly, and two table rows computed credits as `calls * 4220`.
    # Once five `env_params` calls at 2,900 were billed, all three wrote FALSE STATEMENTS into a
    # judge-facing document -- and did so confidently, because a template that is wrong about
    # the world still substitutes cleanly. So the endpoint split is read from the ledger now
    # rather than assumed, and the arithmetic below is the ledger's, not this file's.
    hm = u["heatmap_calls"]
    oth = u["other_endpoint_calls"]
    othc = u["other_endpoint_credits"]
    price = u["heatmap_credits"]
    # Call counts for the attribution split are DERIVED AT THE HEATMAP PRICE and so are ±1 when
    # the plan is mixed. The credit totals are exact; these are not, and the document says so.
    attr_calls = u["attributed_credits"] // price
    unattr_calls = u["unattributed_credits"] // price
    misses = []

    # 🔴 REFUSE TO WRITE AN EQUATION WHOSE SIDES DISAGREE. The reconciliation sentence takes its
    # left side from the endpoint split and its right side from `spent`, and the first version of
    # it checked nothing -- so when the ledger snapshot was one call stale it wrote
    # "173 x 4,220 + 6 x 2,900 = 748,780" into a judge-facing document. The left side was 747,460.
    # A tool that writes arithmetic MUST do the arithmetic. This is also the live-drift alarm: the
    # snapshot goes stale the moment `live.py` bills anything, so re-derive and re-run.
    lhs = hm * price + othc
    # The classification table makes the same promise a second way, so it gets the same guard:
    # its three rows are asserted in the document to sum to the headline.
    row_calls = data + oth + empty + unattr
    row_credits = data * price + othc + empty * price + unattr * price
    if row_calls != calls or row_credits != spent:
        print("\n*** CLASSIFICATION ROWS DO NOT SUM TO THE HEADLINE -- NOTHING WAS WRITTEN.")
        print("    rows: %d calls / %s credits    headline: %d calls / %s credits"
              % (row_calls, money(row_credits), calls, money(spent)))
        print("    The document claims these sum. Fix the ledger's classification, not this text.")
        return 1
    if lhs != spent:
        print("\n*** LEDGER SNAPSHOT DOES NOT RECONCILE -- NOTHING WAS WRITTEN.")
        print("    %d heatmap x %s + %s other = %s, but spent = %s (differs by %s)."
              % (hm, money(price), money(othc), money(lhs), money(spent),
                 money(abs(spent - lhs))))
        print("    Almost always means a paid call landed between the ledger run and this one.")
        print("    Re-run: python testing/api_usage_ledger.py --json && "
              "python testing/bump_spend_docs.py")
        return 1

    print("ledger: %d calls, %s credits, %.2f %% of plan, %s remaining"
          % (calls, money(spent), pct, money(rem)))

    # ---- API-USAGE.md
    p = os.path.join(ROOT, "API-USAGE.md")
    t = io.open(p, encoding="utf-8").read()
    for pat, rep, label in (
        (r"\| \*\*Paid calls made\*\* \|[^\n]*",
         "| **Paid calls made** | **%d** — %d `heatmap` + %d `env_params` |"
         % (calls, hm, oth) if oth else
         "| **Paid calls made** | **%d** — all `heatmap` |" % calls, "paid calls"),
        (r"(\| \*\*Credits spent\*\* \| \*\*)[\d,]+(\*\* \|)",
         r"\g<1>%s\g<2>" % money(spent), "credits spent"),
        (r"(\| \*\*Share of the plan used\*\* \| \*\*)[\d.]+( %\*\* \|)",
         r"\g<1>%.2f\g<2>" % pct, "share of plan"),
        (r"(\| Credits remaining \| \*\*)[\d,]+(\*\* \|)",
         r"\g<1>%s\g<2>" % money(rem), "credits remaining"),
        # The reconciliation, not the old divisibility claim. Matches only the bolded arithmetic,
        # so the surrounding prose is the document's business and this is the ledger's.
        (r"\*\*\d[\d,]* × [\d,]+ \+ \d+ × [\d,]+ = [\d,]+\*\*",
         "**%d × %s + %d × %s = %s**"
         % (hm, money(price), oth, money(othc // oth if oth else 0), money(spent)),
         "reconciliation arithmetic"),
        (r"## 3\. The \d+ calls, itemised",
         "## 3. The %d calls, itemised" % calls, "section 3 heading"),
        (r"\| Returned a populated field, tile count saved \|[^\n]*",
         "| Returned a populated field, tile count saved | **%d** — %d heatmap + %d `env_params` "
         "| %s |" % (data + oth, data, oth, money(data * price + othc)) if oth else
         "| Returned a populated field, tile count saved | **%d** | %s |"
         % (data, money(data * price)), "populated field row"),
        (r"(\| Returned `completed` with \*\*zero\*\* features, individually attributed \| \*\*)\d+"
         r"(\*\* \| )[\d,]+( \|)",
         r"\g<1>%d\g<2>%s\g<3>" % (empty, money(empty * price)), "zero features row"),
        (r"(\| Not individually attributable — a gap between two readings \| \*\*)\d+"
         r"(\*\* \| )[\d,]+( \|)",
         r"\g<1>%d\g<2>%s\g<3>" % (unattr, money(unattr * price)), "unattributable row"),
        # The three rows must sum to the headline, and the document states the sum so a reader can
        # check it without trusting us. Maintained here so it cannot drift away from the rows above.
        # `[\d,]*\d` NOT `[\d,]+` -- the greedy version swallowed the comma that ends the clause
        # ("...to 748,780, which is the check") and deleted it from the sentence.
        (r"Those three rows sum to \d+ and to [\d,]*\d",
         "Those three rows sum to %d and to %s" % (row_calls, money(row_credits)),
         "row-sum sentence"),
        (r"\*\*\d+ calls\*\* saved a before/after meter pair and so are individually attributable; "
         r"the remaining\n\*\*\d+\*\*",
         "**%d calls** saved a before/after meter pair and so are individually attributable; "
         "the remaining\n**%d**" % (attr_calls, unattr_calls), "attribution split"),
        (r"The \d+-call gap figure", "The %d-call gap figure" % unattr_calls, "gap caveat"),
        # §3a's one-run share. It read "44 % of everything this plan has ever spent" for days after
        # that stopped being true -- a share of a moving total is a figure that MUST be derived, and
        # it slipped through because the audit only polices percentages given to two decimals.
        (r"(\| Spent \| \*\*46,420 credits\*\* — \*\*)[\d.]+( %\*\*)",
         r"\g<1>%.1f\g<2>" % (100.0 * 46420 / spent), "one-run share"),
        (r"records \*\*\d+\*\* failed attempts across \*\*\d+\*\* days",
         "records **%d** failed attempts across **%d** days"
         % (u["collector_recorded_failed_attempts"],
            u["collector_failed_attempt_days"]), "collector attempts"),
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
    # HANDOFF's ORIENTATION BLOCK, item 8. Added 2026-08-26 in the same edit that wrote the figure
    # there -- and it failed the audit within the hour, because two more live calls landed while the
    # section was being written. A spend figure in a NEW place is a new place for spend to go stale,
    # so it is registered in the same commit that introduces it rather than the commit after.
    t = sub_or_report(
        t, r"\*\*SPEND IS [\d,]+ CALLS / [\d,]+ / [\d.]+ %\*\*, [\d,]+ remaining — "
           r"\d+ heatmaps \+ \d+",
        "**SPEND IS %d CALLS / %s / %.2f %%**, %s remaining — %d heatmaps + %d"
        % (calls, money(spent), pct, money(rem), hm, oth),
        "HANDOFF: orientation item 8", misses)
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
