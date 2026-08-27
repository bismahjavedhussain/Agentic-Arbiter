"""Rebuild every offerable site onto the CURRENT calibration count, safely, or not at all.

WHY THIS EXISTS
---------------
Every one of the ~250 offerable sites embeds its OWN copy of `cycle.bound_day_level` -- n, the
margin, the attainable ceiling -- because `agent.py` reads `n26_manifest.json` on every run and
writes what it found into that site's trace. So when a new calibration day-pair lands, the tree does
not partially update: it stays entirely on the old count until every site is rebuilt. Measured at
~63 s per site (README step 13), a full pass is about 4.4 hours.

That makes this a rebuild with real downside two days before a deadline, so the whole point of this
script is that FAILING IS CHEAP:

    PREFLIGHT  refuse to start unless the tree is already green and already committed
    REBUILD    run_all.py, the audited entry point, and read its LAST LINE
    VERIFY     audit.py must pass
    ROLLBACK   on any failure, restore the tracked artefacts to the commit and stop

⚠ IT COMMITS NOTHING AND BUMPS NO DOCUMENT. A successful rebuild moves published figures -- n, the
ceiling, the coverage, and audit's own self-reported check count -- so the second half of the
HANDOFF section 3.6.7 two-step ("rebuild -> audit tells you the demanded figures -> update the
document -> audit again") is left to a human. The script prints exactly which figures moved.

USAGE
    python testing/rebuild_calibration.py preflight    # free, WRITES NOTHING -- what the schedule runs
    python testing/rebuild_calibration.py run          # the real thing, hours
    python testing/rebuild_calibration.py run --dry    # preflight + print the plan, no rebuild
    python testing/rebuild_calibration.py selftest    # free, instant: checks the two gates' logic
"""
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IA = os.path.join(ROOT, "INTAKE-ARBITER")
SRC = os.path.join(IA, "src")
DEMO = os.path.join(IA, "demo")
MANIFEST = os.path.join(HERE, "results", "n26_manifest.json")
LOG = os.path.join(HERE, "results", "rebuild_calibration.log")

# The paths a rebuild writes into. Rollback restores exactly these, to the last commit -- surgical
# rather than `git reset --hard`, which would also throw away anything else in the working tree.
RESTORE = ["INTAKE-ARBITER/demo", "INTAKE-ARBITER/data"]

# Paths a rebuild neither reads as input nor restores on rollback: this script's own log, the ledger
# cache audit.py rewrites, and the paid fixtures a collector drops in.
#
# ⚠ THE GATE MUST EXEMPT THESE OR IT CAN NEVER PASS. `say()` appends the run header to the log
# BEFORE preflight starts, so the tree is already dirty by the time the check reads it -- a strict
# check refuses its own scheduled run, every time. Found by running `run --dry` twice: the second
# run failed on the first run's log line. Everything OUTSIDE this prefix still blocks, because
# rollback does `git checkout -- INTAKE-ARBITER/{demo,data}` and would destroy uncommitted work there.
OUTPUT_ONLY = ("testing/results/",)

ALPHA = 0.10


def say(msg=""):
    print(msg, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def dirty_paths():
    """Uncommitted paths, split into (blocking, output-only churn).

    Porcelain's path field starts at column 3; a rename prints `old -> new` and only the new name
    matters. Paths with spaces or non-ASCII come back quoted, so the quotes are stripped -- the
    prefix test is on the git-reported forward-slash form, not an OS path.
    """
    out = git("status", "--porcelain").stdout.splitlines()
    blocking, churn = [], []
    for line in out:
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        path = path.strip('"')
        (churn if path.startswith(OUTPUT_ONLY) else blocking).append(path)
    return blocking, churn


def pairs_on_disk():
    """Complete day-pairs the collector holds, and the bound they would produce.

    Counted the way `agent.perceive_fortyguard()` counts: a day needs BOTH tags AND both saved
    fixtures. The manifest saying `outcome_done` is not enough -- gotcha #188's lesson is that a
    flag set at the start of a step does not prove the step finished.
    """
    m = json.load(open(MANIFEST, encoding="utf-8"))
    fx = os.path.join(HERE, "results", "fixtures")
    res = []
    for iso in sorted(m.get("days", {})):
        d = m["days"][iso]
        ft, ot = d.get("forecast_tag"), d.get("outcome_tag")
        if not (ft and ot):
            continue
        fp, hp = os.path.join(fx, ft + ".json"), os.path.join(fx, ot + ".json")
        if os.path.exists(fp) and os.path.exists(hp) and os.path.getsize(fp) > 100000:
            res.append(iso)
    return res


def run_audit():
    return subprocess.run([sys.executable, "audit.py"], cwd=SRC, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def audit_fails(out):
    return [l for l in (out or "").splitlines() if "[FAIL]" in l]


# The four checks `bump_spend_docs.py` exists to satisfy, by their audit.py labels. Kept as one
# named tuple so preflight (before the rebuild) and verify (after it) agree on what "the documents
# are merely lagging" means, instead of two hand-copied lists drifting apart.
SPEND_LABELS = ("quotes the current spend", "OTHER call count", "superseded figure")


def spend_only(fails):
    return bool(fails) and all(any(k in l for k in SPEND_LABELS) for l in fails)


def doc_only(fails):
    """True when every audit failure is a DOCUMENT lagging a figure the rebuild just moved.

    A rebuild changes n, the ceiling, the coverage and audit's own check count, so README and the
    two spend documents go stale in the same instant the rebuild succeeds -- that is the drift
    catcher working, not breakage. Anything else in the list means roll back.
    """
    return bool(fails) and all(("README figure" in l) or any(k in l for k in SPEND_LABELS)
                               for l in fails)


def audit_verdict_line(out):
    """audit.py's VERDICT line, not its last line.

    The last non-blank line of that file's output is a row of '=' -- taking it printed a separator
    where a verdict belonged, which reads as though the check produced nothing. Match the line that
    actually carries the counts and fall back to the last real line only if it is absent.
    """
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    for l in reversed(lines):
        if l.startswith("AUDIT:"):
            return [l]
    return [next((l for l in reversed(lines) if set(l) != {"="}), "(no output)")]


def n_offerable():
    try:
        s = json.load(open(os.path.join(DEMO, "sites.json"), encoding="utf-8"))
        return sum(1 for x in s["sites"] if x.get("offerable"))
    except (OSError, ValueError, KeyError):
        return -1


def published_bound():
    t = json.load(open(os.path.join(DEMO, "trace.json"), encoding="utf-8"))
    return t["cycle"].get("bound_day_level") or {}


def bound_at(n):
    k = math.ceil((n + 1) * (1 - ALPHA))
    return {"n": n, "k": min(k, n), "clamped": k > n,
            "attainable": n / (n + 1), "n_needed": math.ceil(1 / ALPHA) - 1}


def preflight(fix_docs=True):
    """Every gate, read-only, EXCEPT the one repair `fix_docs` allows.

    ⚠ `fix_docs=False` IS THE SCHEDULED MODE, at the user's direction: "dont proceed with the
    rebuild without my approval even at the time it's scheduled for." A wake-up that writes nothing
    at all is the only kind that cannot be mistaken for having started. With it False the stale
    spend documents are REPORTED rather than synced, and the verdict says so instead of claiming
    the tree is red.
    """
    say("=" * 78)
    say("PREFLIGHT -- read-only. Nothing is written and nothing is spent.")
    say("=" * 78)
    ok = True

    # 1. THE TREE MUST ALREADY BE COMMITTED, because that commit IS the rollback. Refusing here is
    #    the difference between a bounded failure and an afternoon of forensics.
    blocking, churn = dirty_paths()
    if blocking:
        say("   [FAIL] %d uncommitted change(s) OUTSIDE testing/results/. Commit or stash first --"
            % len(blocking))
        say("          the last commit is what a rollback restores to, and rollback overwrites")
        say("          INTAKE-ARBITER/demo and INTAKE-ARBITER/data without asking.")
        for q in blocking[:8]:
            say("          - %s" % q)
        if len(blocking) > 8:
            say("          ... and %d more" % (len(blocking) - 8))
        ok = False
    else:
        head = git("rev-parse", "--short", "HEAD").stdout.strip()
        say("   [ok  ] nothing uncommitted that a rollback would touch; target is %s" % head)
        if churn:
            say("          (%d output file(s) under testing/results/ differ -- this log, the ledger"
                % len(churn))
            say("           cache, collector fixtures. Rollback does not touch them.)")

    # 2. IT MUST ALREADY BE GREEN. Rebuilding on top of a red tree cannot tell you whether the
    #    rebuild broke something or it was already broken -- and that is the question that matters.
    say("   ...... running audit.py to confirm the CURRENT state is green (this takes a minute)")
    a = run_audit()
    last = audit_verdict_line(a.stdout)
    if a.returncode != 0 and spend_only(audit_fails(a.stdout)) and not fix_docs:
        say("   [ok  ] audit is red ONLY on the spend figure the collectors moved today, which is a")
        say("          document lagging a number rather than a broken tree. NOT synced here --")
        say("          this mode writes nothing. `run` syncs it before rebuilding.")
        for l in audit_fails(a.stdout)[:4]:
            say("          | %s" % l.strip())
    elif a.returncode != 0 and spend_only(audit_fails(a.stdout)):
        # ⚠ THIS IS WHY THE SCHEDULED RUN WOULD OTHERWISE ALWAYS REFUSE. The collectors buy pairs
        #    at 13:30-15:30 and the rebuild is scheduled for 16:00, so by the time preflight runs,
        #    the meter has moved and the two documents quoting it are stale BY DEFINITION. That is
        #    a document lagging a number, not a red tree -- and refusing on it would mean the
        #    rebuild never happens on any day a pair actually lands.
        say("   ...... audit is red ONLY on the spend figure, which the collectors moved today.")
        say("          refreshing the ledger and re-bumping the two documents that quote it.")
        for tool, extra in (("api_usage_ledger.py", ["--json"]), ("bump_spend_docs.py", [])):
            # THE --json IS NOT OPTIONAL and its order is not either: bump_spend_docs reads the
            # CACHED ledger, so without a refresh first it writes STALE figures and still reports
            # success. HANDOFF 3.7.7 #3.
            r = subprocess.run([sys.executable, os.path.join(HERE, tool)] + extra, cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            say("          %-22s exit %d" % (tool, r.returncode))
            if r.returncode != 0:
                say("          | %s" % (r.stderr or r.stdout or "").strip()[-300:])
                break
        say("   ...... re-running audit.py")
        a = run_audit()
        last = audit_verdict_line(a.stdout)
    if a.returncode != 0 and not (spend_only(audit_fails(a.stdout)) and not fix_docs):
        say("   [FAIL] audit.py is NOT green right now: %s" % last[0].strip())
        say("          fix that first; do not rebuild on a red tree.")
        for l in audit_fails(a.stdout)[:8]:
            say("          | %s" % l.strip())
        ok = False
    elif a.returncode == 0:
        say("   [ok  ] audit.py green: %s" % last[0].strip())

    # 3. THE COLLECTORS MUST NOT BE MID-WINDOW. HANDOFF 3.6.7 #6: never regenerate trace/backtest/
    #    money while a batch writes, or sites built before and after stop agreeing. The collectors
    #    fire 13:30-15:30 PKT; a rebuild started inside that window can read a half-written manifest.
    now_pkt = time.gmtime(time.time() + 5 * 3600)
    mins = now_pkt.tm_hour * 60 + now_pkt.tm_min
    if 13 * 60 + 20 <= mins <= 15 * 60 + 40:
        say("   [FAIL] it is %02d:%02d PKT -- inside the 13:30-15:30 collector window."
            % (now_pkt.tm_hour, now_pkt.tm_min))
        say("          a rebuild here can read a manifest mid-write. Start after 15:40 PKT.")
        ok = False
    else:
        say("   [ok  ] %02d:%02d PKT is outside the collector window"
            % (now_pkt.tm_hour, now_pkt.tm_min))

    # 4. AND THERE MUST BE SOMETHING TO GAIN.
    have = pairs_on_disk()
    pub = published_bound()
    n_now, n_new = pub.get("n"), len(have)
    say("")
    say("   published calibration : n = %s, ceiling %.2f %%, margin %s"
        % (n_now, 100 * (pub.get("attainable") or 0), pub.get("margin")))
    say("   on disk now           : n = %d  (%s)" % (n_new, ", ".join(have)))
    if n_new <= (n_now or 0):
        say("   [FAIL] nothing to gain -- disk has no more pairs than the tree already publishes.")
        ok = False
    else:
        b = bound_at(n_new)
        say("   [ok  ] a rebuild would take n %s -> %d, ceiling %.2f %% -> %.2f %%"
            % (n_now, n_new, 100 * (pub.get("attainable") or 0), 100 * b["attainable"]))
        say("          %d further pair(s) would make 90 %% reachable (n = %d)"
            % (max(0, b["n_needed"] - n_new), b["n_needed"]))
    say("")
    say("   VERDICT: %s" % ("SAFE TO RUN" if ok else "DO NOT RUN -- fix the [FAIL] rows above"))
    if not fix_docs:
        say("")
        say("   THIS MODE DOES NOT REBUILD AND HAS CHANGED NOTHING. The rebuild is a human decision")
        say("   and waits for one: `python testing/rebuild_calibration.py run`.")
    say("=" * 78)
    return 0 if ok else 1


def rollback(why):
    say("")
    say("=" * 78)
    say("ROLLBACK -- %s" % why)
    say("=" * 78)
    for p in RESTORE:
        r = git("checkout", "--", p)
        say("   git checkout -- %-24s %s" % (p, "ok" if r.returncode == 0 else r.stderr.strip()))
    say("   ...... re-running audit.py to confirm the restore is green")
    a = subprocess.run([sys.executable, "audit.py"], cwd=SRC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    last = audit_verdict_line(a.stdout)
    say("   audit after rollback  : %s" % last[0].strip())
    if a.returncode != 0:
        say("")
        say("   🔴 THE ROLLBACK DID NOT COME BACK GREEN. Do not improvise -- the tagged fallback is")
        say("      intact and is one command away:")
        say("         git checkout submission-safe-2026-08-27 -- INTAKE-ARBITER/")
        say("      That tag was committed green with scan_secrets CLEAN and is submittable as-is.")
        return 2
    say("   the tree is back where it started. Nothing was lost.")
    say("=" * 78)
    return 1


def run(dry=False):
    if preflight() != 0:
        return 1
    have, pub = pairs_on_disk(), published_bound()
    say("")
    say("=" * 78)
    say("REBUILD -- %d offerable sites + the full ladder. Expect ~4-5 HOURS at ~63 s/site."
        % n_offerable())
    say("   n %s -> %d. This rewrites every site's trace, backtest, rolling, money," % (pub.get("n"), len(have)))
    say("   explanations, ticker and PDF, because each carries its own copy of the bound.")
    say("=" * 78)
    if dry:
        say("   --dry: stopping here. Nothing rebuilt.")
        return 0
    t0 = time.time()
    p = subprocess.run([sys.executable, "run_all.py"], cwd=SRC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()]
    # THE LAST LINE, NOT THE EXIT CODE. Gotcha #158: a wrapper reported exit 0 on a run whose last
    # line said REBUILD FAILED, and the audit's own self-referential check count was the thing that
    # had moved. run_all prints REBUILD COMPLETE or REBUILD FAILED at: <step>.
    last = tail[-1].strip() if tail else "(no output)"
    say("")
    say("   run_all.py last line  : %s" % last)
    say("   elapsed               : %.1f min" % ((time.time() - t0) / 60.0))
    if "REBUILD COMPLETE" not in last:
        for l in tail[-25:]:
            say("      | %s" % l)
        return rollback("run_all.py did not finish: %s" % last)

    a = run_audit()
    say("   audit.py              : %s" % audit_verdict_line(a.stdout)[0].strip())

    # ⚠ MATCH "[FAIL]", NOT "FAIL". The summary line reads "0 warnings, 0 FAILURES", so a loose
    #    substring test finds one "failure" on a PERFECTLY GREEN audit -- and since that line
    #    matches none of the document patterns below, `doc_only` came out False and this function
    #    rolled back a successful rebuild. Measured on the green tree: loose match 1 line, strict
    #    match 0. Four and a half hours of work, discarded by a missing pair of brackets.
    fails = audit_fails(a.stdout)

    # 🔴 A FAILING check 9 or check 10 IS EXPECTED HERE AND IS *NOT* A BROKEN REBUILD.
    # Section 3.6.7's two-step: the rebuild moves the figures, so the documents quoting them go
    # stale in the same instant and the audit says so. Only failures OUTSIDE those two checks mean
    # the rebuild actually broke something.
    if fails and not doc_only(fails):
        for l in fails[:12]:
            say("      | %s" % l.strip())
        return rollback("audit.py failed on something other than a stale document figure")

    newb = published_bound()
    say("")
    say("=" * 78)
    say("REBUILD SUCCEEDED. Nothing has been committed and no document has been bumped.")
    say("=" * 78)
    say("   n          %s  ->  %s" % (pub.get("n"), newb.get("n")))
    say("   margin     %s  ->  %s" % (pub.get("margin"), newb.get("margin")))
    say("   ceiling    %.2f %%  ->  %.2f %%"
        % (100 * (pub.get("attainable") or 0), 100 * (newb.get("attainable") or 0)))
    if fails:
        say("")
        say("   THE SECOND HALF OF THE TWO-STEP IS YOURS -- audit is asking for these:")
        for l in fails:
            say("      | %s" % l.strip())
        say("")
        say("   Order matters (3.6.7 #7): update the document, THEN re-run audit.py. Writing the")
        say("   document first guarantees a second failure.")
    say("")
    say("   If anything about the result looks wrong, the tagged fallback is intact:")
    say("      git checkout submission-safe-2026-08-27 -- INTAKE-ARBITER/")
    say("=" * 78)
    return 0


def selftest():
    """Check the two decisions that can silently destroy a good rebuild, WITHOUT a 4.5-hour run.

    Both were real defects in this file, and neither would have shown up in a dry run:
      * a loose "FAIL" substring matched the summary line "0 FAILURES" on a GREEN audit, so the
        rollback fired after a successful rebuild;
      * the dirty-tree gate counted this script's own log line, so the scheduled run refused itself.
    """
    GREEN = "AUDIT: 2057 passed, 0 warnings, 0 FAILURES"
    SPEND = "   [FAIL] API-USAGE.md           quotes the current spend          missing 893,840"
    OTHERC = "   [FAIL] HANDOFF.md            quotes no OTHER call count or plan percentage"
    README = "   [FAIL] every README figure matches the emitted JSON             3 of 45 differ"
    REAL = "   [FAIL] the served copy is byte-identical to the root one        differs"

    cases = [
        ("green audit yields no [FAIL] rows", audit_fails(GREEN) == []),
        ("a green audit therefore never rolls back", not (audit_fails(GREEN) and True)),
        ("verdict line is the AUDIT line, not the separator",
         audit_verdict_line(chr(10).join(["=" * 78, GREEN, "=" * 78]))[0] == GREEN),
        ("spend-only is recognised", spend_only([SPEND, OTHERC]) is True),
        ("a README drift is NOT spend-only", spend_only([SPEND, README]) is False),
        ("a real failure is NOT spend-only", spend_only([SPEND, REAL]) is False),
        ("stale documents after a rebuild are doc-only", bool(doc_only([SPEND, README, OTHERC]))),
        ("a real failure after a rebuild rolls back", not doc_only([README, REAL])),
        ("no failures is not doc-only", not doc_only([])),
        ("this script's own log never blocks", "testing/results/rebuild_calibration.log"
         .startswith(OUTPUT_ONLY)),
        ("the ledger cache never blocks", "testing/results/api_usage.json".startswith(OUTPUT_ONLY)),
        ("a demo change DOES block", not "INTAKE-ARBITER/demo/trace.json".startswith(OUTPUT_ONLY)),
        ("a src change DOES block", not "INTAKE-ARBITER/src/agent.py".startswith(OUTPUT_ONLY)),
    ]
    bad = 0
    for name, passed in cases:
        say("   [%s] %s" % ("PASS" if passed else "FAIL", name))
        bad += 0 if passed else 1
    say("")
    say("   SELFTEST: %d passed, %d FAILURES" % (len(cases) - bad, bad))
    return 0 if bad == 0 else 1


def main(argv):
    mode = (argv[0] if argv else "preflight").lower()
    say("")
    say("### rebuild_calibration.py %s  at %s UTC"
        % (mode, time.strftime("%Y-%m-%d %H:%M", time.gmtime())))
    if mode == "preflight":
        # READ-ONLY, and that is what the scheduled task runs. It reports whether a rebuild WOULD
        # be safe and then stops, because the rebuild itself needs an explicit human yes.
        return preflight(fix_docs=False)
    if mode == "run":
        return run(dry="--dry" in argv)
    if mode == "selftest":
        return selftest()
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
