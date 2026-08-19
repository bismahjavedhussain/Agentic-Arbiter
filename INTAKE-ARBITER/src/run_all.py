# -*- coding: utf-8 -*-
"""RUN EVERYTHING, in dependency order, and audit the result.  ZERO API CALLS.

    python run_all.py

This is the single command that reproduces every published number from scratch and then checks
them. If it exits 0, every figure in PLAN.md and HANDOFF.md is backed by a file this run wrote.

ORDER MATTERS, and here is why each step depends on the one before it:
  1. plume_uncertainty  builds the spread tables and calibrates the plume term of the bound.
                        `agent.py` reads its calibration, so it must exist first. If it is missing
                        the agent DISABLES the plume term rather than guessing, and says so.
  2. agent             runs the loop, writes trace.json / scenarios.json / the field files.
  3. backtest          the five-year run: the N-56 audit ladder, the Mondrian coverage audit and
                       the online adaptive-conformal experiment.
  4. explain           stage 7, and verifies every explanation by re-running the agent.
  5. ticker            the stage-event tape. Depends on explain's state builder, and its own guard
                       is that no template may contain a literal digit -- so every number on the
                       tape has to have arrived from a file an earlier step wrote.
  6. gen_*_cases       scheduling cases and stage-event tapes scored by PYTHON, for the browser
                       tests. The tape fixtures are chosen to cover EVERY branch, and the generator
                       exits non-zero if any branch is unreachable.
  7. audit             dead code, NaN-unsafe writers, rounded decision arrays, constant drift,
                       stage 5's command bounds, every published number, every self-test, and the
                       four cross-language consistency tests.

Nothing here calls the FortyGuard API. Every input is a saved response, a committed geometry file,
or the 43,763-hour weather record.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(os.path.dirname(HERE), "demo")

STEPS = [
    ("plume uncertainty: spread tables + calibration", [sys.executable, "plume_uncertainty.py"], HERE),
    ("the agent loop: trace, scenarios, fields", [sys.executable, "agent.py", "run"], HERE),
    ("five-year backtest: N-56 ladder, 12-axis sensitivity, Mondrian, ACI",
     [sys.executable, "backtest.py", "all"], HERE),
    ("rolling control: present-tense agent, 12 per-lead bounds, plan churn",
     [sys.executable, "rolling.py"], HERE),
    # The site manifest is what the interface is ALLOWED to offer. Regenerated every run so the
    # picker cannot drift from the engine -- it already caught itself offering two sites the
    # imagery scope gate had refused.
    ("site manifest: what the interface may offer, and why",
     [sys.executable, "metros.py", "--manifest"], HERE),
    # After the backtest, whose ladder and sensitivity rows are the hours it prices. Reads no new
    # data and calls nothing -- every source is a document already downloaded and quoted.
    ("money: chiller-hours priced, both conversion factors swept",
     [sys.executable, "money.py"], HERE),
    ("stage 7 explain, with verification", [sys.executable, "explain.py"], HERE),
    # After explain, because the per-hour tape is built on `explain.state_from_trace`; before the
    # fixtures, which are generated from the tape it writes.
    ("stage events: the reasoning tape, and the no-literal-digit guard",
     [sys.executable, "ticker.py"], HERE),
    ("browser test fixtures", [sys.executable, "gen_dp_cases.py"], DEMO),
    ("browser test fixtures: stage-event tapes", [sys.executable, "gen_ticker_cases.py"], DEMO),
    ("browser test fixtures: the conformal arithmetic",
     [sys.executable, "gen_conformal_cases.py"], DEMO),
    ("AUDIT: everything, mechanically", [sys.executable, "audit.py"], HERE),
]


def main():
    t0 = time.time()
    print("=" * 78)
    print("INTAKE-ARBITER  --  full rebuild and audit.  ZERO API CALLS.")
    print("=" * 78)
    failed = []
    for i, (label, cmd, cwd) in enumerate(STEPS, 1):
        print("\n[%d/%d] %s" % (i, len(STEPS), label))
        t = time.time()
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=3600)
        lines = [l for l in (r.stdout or "").strip().split("\n") if l.strip()]
        for l in lines[-3:]:
            print("      %s" % l[:110])
        if r.returncode != 0:
            failed.append(label)
            err = (r.stderr or "").strip().split("\n")[-3:]
            for l in err:
                print("      ERR %s" % l[:110])
        print("      -> %s in %.1f s" % ("OK" if r.returncode == 0 else "FAILED", time.time() - t))
    print("\n" + "=" * 78)
    if failed:
        print("REBUILD FAILED at: %s" % "; ".join(failed))
        print("Do not quote any number until this exits 0.")
    else:
        print("REBUILD COMPLETE in %.1f s -- every published number is backed by a file this run "
              "wrote." % (time.time() - t0))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
