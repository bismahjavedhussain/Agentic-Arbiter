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
# `testing/` holds the paid collector and the two offline checks that exercise it. Reaching outside
# AGENTIC-ARBITER/ is deliberate: the collector is the thing that spends money, so its logic belongs
# in the same one-command proof as everything else.
TESTING = os.path.join(os.path.dirname(os.path.dirname(HERE)), "testing")
# The repository root, for the two surfaces that live above AGENTIC-ARBITER/: `testing/` above
# and, since 2026-08-28, `CONTEXT/` -- the durable-context pack whose freshness is the last step.
ROOT = os.path.dirname(os.path.dirname(HERE))

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
    # THE OTHER SITES. Ashburn is built by the steps above (its artefacts keep the unsuffixed
    # names the audited chain reads); this step builds every other offerable site on its own
    # weather, geometry and bound. Without it the site picker offers three sites and only one of
    # them has any data, which is how it shipped for two sessions.
    ("downloadable PDF report for ashburn", [sys.executable, "report.py", "ashburn"], HERE),
    # NO SITE LIST HERE. This read `["chicago", "dulles"]` as a literal, so a fourth offerable site
    # would have been silently skipped by the one step whose whole job is building the other sites --
    # the same "a name asserting a value" drift as `metros.weather_file` (which asserted kphx while
    # the station was IWA). `build_sites.py` with no arguments reads the manifest, which is the only
    # thing allowed to decide what is offerable.
    ("every other offerable site, on its own data",
     [sys.executable, "build_sites.py", "--others"], HERE),
    ("site manifest again: now with per-site artefact filenames",
     [sys.executable, "metros.py", "--manifest"], HERE),
    # THE NATIONAL FOOTPRINT, added 2026-08-23, MERGED into one map 2026-08-24 at the user's
    # instruction. `export_unified_map.py` cross-references sites.json's 5 hand-built metros
    # against the 422-entry national registry BY OSM ID (so the 3 running + 2 refused metros are
    # never counted or shown twice), and folds in the S4 geometry verdicts (isolated / refused on
    # geometry / not yet screened) for everything else -- one file, one map, no duplicate sites.
    # `export_national_sites.py` (the old, single-dimension exporter this replaced) is deleted, not
    # kept: its output had no remaining consumer once the two old map panels were merged.
    # Free: pure computation over files already on disk, no network, no credential.
    # THE FACILITY REGISTRY, before the map that will read it. Pure computation over files already
    # on disk -- no network, no credential. It turns the ~11 km DISCOVERY GRID (a batching
    # convenience that gotchas #150 and #152 both show is not a measurement of anything) into the
    # unit the solver actually works on: the connected component of buildings inside its validated
    # 600 m range. 639 facilities from 1,622 buildings.
    ("national registry: one row per real facility, classified and reasoned",
     [sys.executable, "build_national_registry.py"], HERE),
    ("national registry: the merge and classification rules, offline",
     [sys.executable, "build_national_registry.py", "selftest"], HERE),
    ("national footprint: one unified map, every real site, cross-referenced by OSM id",
     [sys.executable, "export_unified_map.py"], HERE),
    # THE LIVE PATH, VERIFIED OFFLINE. `live.py selftest` makes ZERO network calls -- it proves the
    # RLE expansion, the four-way vendor classifier, the gate logic and the margin provenance, all
    # of which are live-INDEPENDENT. What no offline check can prove is that FortyGuard answers, and
    # it does not pretend to: that is `live.py dryrun` (free) and `live.py run --paid`.
    ("live agent: offline self-test of the live chain", [sys.executable, "live.py", "selftest"],
     HERE),
    # THE COLLECTOR'S RETRY BUDGET, WHICH NOTHING ELSE CAN EXERCISE. It only ever runs unattended,
    # from a scheduled task, on a day the vendor is already failing -- and the only way to watch it
    # work for real is to spend 4,220 credits and wait ten minutes for a failure. Its previous
    # version counted FREE failures against a CREDIT budget for a day and a half and no check could
    # have seen it. Zero network, no key read.
    ("collector: the retry budget and the vendor classifier, offline",
     [sys.executable, "test_n26_coverage.py", "selftest"], TESTING),
    ("recovery watcher: the pacing arithmetic, offline",
     [sys.executable, "n26_recovery_watch.py", "selftest"], TESTING),
    # NATIONAL RECOVERY WATCHER, added 2026-08-23 after the national FortyGuard field purchase
    # was stopped mid-batch by a general vendor outage (DIAG-66). Same shape as the N26 watcher
    # immediately above -- day-keyed billed-probe budget, probe windows that shift automatically.
    # Zero network, no key read.
    ("national recovery watcher: the probe cadence and daily budget, offline",
     [sys.executable, "national_recovery_watch.py", "selftest"], TESTING),
    # THE CHICAGO OFFSET COLLECTOR guards a PAID path whose most dangerous property is invisible:
    # `common.SITE_TZ_NAME` is hard-coded to Eastern, so building a Chicago window through it would
    # be a silent ONE-HOUR error -- the nine-hour bug's little brother, and harder to see. The
    # self-test pins the zone, and pins that the lead band, target hour, AOI and granularity match
    # the Ashburn series exactly, because an offset measured under different conditions cannot
    # replace the offsets it is meant to replace. Zero network, no key read.
    ("chicago offset: the window, the zone and the lead band, offline",
     [sys.executable, "n26_chicago_offset.py", "selftest"], TESTING),
    ("AUDIT: everything, mechanically", [sys.executable, "audit.py"], HERE),
    # THE COLOUR TOKENS, MEASURED. Added 2026-08-27 with the second theme, and it is here rather
    # than in a comment because that is exactly the defect it fixes: the stylesheet used to carry
    # its own contrast arithmetic in prose ("--muted #7e8783 -> 3.10:1"), which is a number nothing
    # re-reads. It parses the tokens straight out of demo/index.html and asserts every pair the page
    # renders against its WCAG floor in BOTH themes. It found one real failure on its first run.
    # Offline and instant -- no browser, no network, no artefacts.
    ("colour tokens: every pair measured against its WCAG floor, both themes",
     [sys.executable, "verify_palette.py"], TESTING),
    # LAST, AND IT DRIVES A REAL BROWSER. Everything above reads artefacts; this renders the page
    # for every site and diffs the panels a judge would actually look at. It is last because it is
    # the slowest step and because it needs the artefacts every step above it writes.
    # It EXITS NON-ZERO IF NO BROWSER IS FOUND rather than skipping: a check that quietly skips is a
    # check that reports PASS for a path it never ran (gotcha #74). Chrome and Edge are both present
    # on this machine (HANDOFF section 14); if a future machine has neither, run
    # `python testing/verify_site_panels.py --browser PATH` and say so.
    ("render-level cross-site panel diff: every panel, in a real browser",
     [sys.executable, "verify_site_panels.py"], TESTING),
    # THE NATIONAL MAP'S HOVER READOUT, in the same real browser. It does NOT screenshot the map:
    # headless Chrome cannot reach a loaded MapLibre state in this environment, proved with a
    # code-independent minimal page (gotcha #155), so a check that needed the map to RENDER would be
    # permanently red for a reason unrelated to what it tests -- and a check that is always red gets
    # ignored, which is worse than no check. What it does verify is the part where a defect would
    # actually live: that the readout names the facility under the cursor, that a site with no agent
    # run says so instead of implying one, and that two facilities do not read identically -- the
    # national-scale form of check 6c, since at 421 points nobody will notice by eye.
    ("national map: the hover readout names the right facility, in a real browser",
     [sys.executable, "verify_map_hover.py"], TESTING),
    # 🔴 AND THE MAP ITSELF, RENDERED -- which the step above says is impossible, and was, until
    # 2026-08-28. Gotcha #155 recorded that headless Chrome could not reach a loaded MapLibre state
    # here; what fixes it is `--enable-unsafe-swiftshader --use-gl=angle`, which gives the headless
    # session a software WebGL rasteriser instead of none. So this step reads the live map: which
    # layer is visible, where the camera is, and how many distinct facilities are actually painted.
    # WHY IT NEEDED TO EXIST. Four changes landed on the filter bar at once -- full state names, a
    # California default, one dropdown restored, and individual circles per state -- and three of
    # them were claims about what maplibre DRAWS, which no read of the source can settle. It found a
    # real defect on its first pass: `addData` was gated on `map.isStyleLoaded()`, which stays false
    # while the OSM basemap has tiles in flight, so on a network that blocks or throttles those tiles
    # the 637 facilities were never added to the map at all.
    # It exits 3, not 1, if maplibre does not load from unpkg: the page degrades to a note by design
    # without it, and a missing CDN is not a failing page.
    # 🔴 THE ONLY STEP WITH A DECLARED "COULD NOT RUN" CODE. maplibre is fetched from unpkg at
    # RUNTIME, and the page is designed to degrade to a warning note without it, so an unreachable
    # CDN says nothing about this repository. The verifier reports that as exit 3, and the fourth
    # tuple element below is what stops the runner reading it as a failure. It is a DECLARATION, not
    # a blanket rule: exit 1 from this step still fails the rebuild, as it must.
    ("national map: the state filter and its dropdown, in the live map",
     [sys.executable, "verify_state_filter.py"], TESTING,
     {3: "maplibre could not be fetched from unpkg, so there was no live map to read. "
         "The page degrades to a note without it by design."}),
    # THE DURABLE-CONTEXT PACK, added 2026-08-28. CONTEXT/ is what a future session reads to recover
    # this project's state, and a context pack that has drifted from the artefacts is worse than none:
    # it does not merely fail to help, it misinforms with the authority of a document that says "read
    # this first". So every figure in it that CAN be re-derived is re-derived and compared here, the
    # auto-memory mirror is regenerated and diffed against its source, and two standing rules that
    # happen to be mechanically checkable are asserted: that the live-agent card and button still
    # exist in demo/index.html, and that the map still has the SECOND, flat GeoJSON source the
    # per-state view depends on.
    # It is deliberately honest about its limit: it does NOT check the prose, and says so in its own
    # verdict rather than implying it did.
    ("the CONTEXT pack still matches the artefacts it describes",
     [sys.executable, os.path.join(ROOT, "CONTEXT", "sync_context.py"), "--check"], ROOT),
    # THE SEAM BETWEEN core/ AND THE PAGE, added 2026-08-28. The agent lives twice while the React
    # migration is in progress: as importable modules under AGENTIC-ARBITER/core/, which the five
    # cross-implementation verifiers test against Python, and as the inline copy in demo/index.html,
    # which is what a reader runs. Those verifiers prove core/ matches Python; nothing else would
    # notice if the PAGE drifted away from core/, and then five passing checks would be testing code
    # nobody sees. This asserts the provenance hashes of both copies plus byte-identity for the
    # eleven functions lifted with no substitution at all.
    # It becomes unnecessary the moment the page imports core/ instead of carrying its own copy.
    ("core/ is still the page's own code, substitution for substitution",
     [sys.executable, "verify_core_matches_page.py"], TESTING),
]


def main():
    t0 = time.time()
    print("=" * 78)
    print("AGENTIC-ARBITER  --  full rebuild and audit.  ZERO API CALLS.")
    print("=" * 78)
    failed, notrun = [], []
    for i, step in enumerate(STEPS, 1):
        # A step is (label, cmd, cwd) or (label, cmd, cwd, soft) where `soft` maps an exit code to
        # the reason it means "could not run" rather than "failed". See the verify_state_filter entry.
        label, cmd, cwd = step[0], step[1], step[2]
        soft = step[3] if len(step) > 3 else {}
        print("\n[%d/%d] %s" % (i, len(STEPS), label))
        t = time.time()
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=3600)
        lines = [l for l in (r.stdout or "").strip().split("\n") if l.strip()]
        for l in lines[-3:]:
            print("      %s" % l[:110])
        if r.returncode == 0:
            outcome = "OK"
        elif r.returncode in soft:
            # NOT A PASS, AND NOT SILENT. The reason is printed here and repeated in the final
            # banner, because the one thing worse than a red check is a green run that quietly
            # skipped something (gotcha #74).
            outcome = "COULD NOT RUN"
            notrun.append((label, soft[r.returncode]))
            print("      !! could not run: %s" % soft[r.returncode])
        else:
            outcome = "FAILED"
            failed.append(label)
            err = (r.stderr or "").strip().split("\n")[-3:]
            for l in err:
                print("      ERR %s" % l[:110])
        print("      -> %s in %.1f s" % (outcome, time.time() - t))
    print("\n" + "=" * 78)
    if failed:
        print("REBUILD FAILED at: %s" % "; ".join(failed))
        print("Do not quote any number until this exits 0.")
    elif notrun:
        # Exit 0, because nothing FAILED -- but the completion claim is narrowed to what actually
        # ran, in the banner, rather than printed in full and quietly untrue.
        print("REBUILD COMPLETE in %.1f s, with %d step(s) that COULD NOT RUN:"
              % (time.time() - t0, len(notrun)))
        for label, why in notrun:
            print("   * %s" % label)
            print("     %s" % why)
        print("Every number the steps that DID run publish is backed by a file this run wrote. The "
              "step(s) above proved nothing either way.")
    else:
        print("REBUILD COMPLETE in %.1f s -- every published number is backed by a file this run "
              "wrote." % (time.time() - t0))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
