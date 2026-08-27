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
    python testing/rebuild_calibration.py preflight    # free, read-only, exits non-zero if not safe
    python testing/rebuild_calibration.py run          # the real thing, hours
    python testing/rebuild_calibration.py run --dry    # preflight + print the plan, no rebuild
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


def preflight():
    say("=" * 78)
    say("PREFLIGHT -- read-only. Nothing is written and nothing is spent.")
    say("=" * 78)
    ok = True

    # 1. THE TREE MUST ALREADY BE COMMITTED, because that commit IS the rollback. Refusing here is
    #    the difference between a bounded failure and an afternoon of forensics.
    st = git("status", "--porcelain")
    dirty = [l for l in st.stdout.splitlines() if l.strip()]
    if dirty:
        say("   [FAIL] working tree has %d uncommitted change(s). Commit or stash first --"
            % len(dirty))
        say("          the last commit is what a rollback restores to.")
        ok = False
    else:
        head = git("rev-parse", "--short", "HEAD").stdout.strip()
        say("   [ok  ] tree is clean; rollback target is %s" % head)

    # 2. IT MUST ALREADY BE GREEN. Rebuilding on top of a red tree cannot tell you whether the
    #    rebuild broke something or it was already broken -- and that is the question that matters.
    say("   ...... running audit.py to confirm the CURRENT state is green (this takes a minute)")
    a = subprocess.run([sys.executable, "audit.py"], cwd=SRC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    last = audit_verdict_line(a.stdout)
    if a.returncode != 0:
        say("   [FAIL] audit.py is NOT green right now: %s" % last[0].strip())
        say("          fix that first; do not rebuild on a red tree.")
        ok = False
    else:
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

    a = subprocess.run([sys.executable, "audit.py"], cwd=SRC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    aout = (a.stdout or "").splitlines()
    alast = [l for l in aout if l.strip()][-1:] or [""]
    say("   audit.py              : %s" % alast[0].strip())
    fails = [l for l in aout if "FAIL" in l]

    # 🔴 A FAILING check 9 or check 10 IS EXPECTED HERE AND IS *NOT* A BROKEN REBUILD.
    # Section 3.6.7's two-step: the rebuild moves the figures, so the documents quoting them go
    # stale in the same instant and the audit says so. Only failures OUTSIDE those two checks mean
    # the rebuild actually broke something.
    doc_only = fails and all(("README figure" in l) or ("quotes the current spend" in l)
                             or ("OTHER call count" in l) or ("superseded figure" in l)
                             for l in fails)
    if fails and not doc_only:
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


def main(argv):
    mode = (argv[0] if argv else "preflight").lower()
    say("")
    say("### rebuild_calibration.py %s  at %s UTC"
        % (mode, time.strftime("%Y-%m-%d %H:%M", time.gmtime())))
    if mode == "preflight":
        return preflight()
    if mode == "run":
        return run(dry="--dry" in argv)
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
