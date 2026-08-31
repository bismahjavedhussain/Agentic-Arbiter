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
    # 🔴 `site_report.py`, NOT `report.py`, AND THE ORDER MATTERS MORE THAN THE NAME. This step
    # writes `demo/report.pdf`. Left pointing at the old generator it would have overwritten the
    # typeset report with the monospaced one on every single run_all, silently reverting the
    # rebuild for anyone who ran the pipeline after building the site. `report.py` stays in the
    # tree because `live_report.py` imports its primitives; it is simply no longer the document a
    # reader downloads.
    #
    # ⚠ THIS STEP NOW NEEDS `requirements-build.txt` (reportlab, svglib, matplotlib, pillow).
    # run_all still makes ZERO API calls, which is the property it exists to prove; it is not and
    # never was runnable with no third-party libraries at all.
    ("downloadable PDF report for ashburn",
     [sys.executable, "site_report.py", "ashburn"], HERE),
    # NO SITE LIST HERE. This read `["chicago", "dulles"]` as a literal, so a fourth offerable site
    # would have been silently skipped by the one step whose whole job is building the other sites --
    # the same "a name asserting a value" drift as `metros.weather_file` (which asserted kphx while
    # the station was IWA). `build_sites.py` with no arguments reads the manifest, which is the only
    # thing allowed to decide what is offerable.
    ("every other offerable site, on its own data",
     [sys.executable, "build_sites.py", "--others"], HERE),
    ("site manifest again: now with per-site artefact filenames",
     [sys.executable, "metros.py", "--manifest"], HERE),
    # THE PORTFOLIO TOTALS, added 2026-08-29, and they go HERE because they read the manifest line
    # above: it is the step that writes each site's artefact filenames, and portfolio_totals.py
    # opens all 750 of them. Placing it earlier would sum whatever the previous run left behind.
    # It writes demo/portfolio.json, which the landing page's two summary cards read. A derived
    # file that no step regenerates is a figure that can outlive the artefacts it was summed from,
    # which is the one failure mode the whole audit exists to prevent.
    # Free: pure computation over files already on disk, no network, no credential.
    ("portfolio totals: 250 sites' own artefacts, summed for the landing cards",
     [sys.executable, os.path.join(ROOT, "tools", "portfolio_totals.py")], ROOT),
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
    # THE REACT APP'S DETERMINISM, added 2026-08-28. The pick screen's KPI cards adapt a treatment
    # from a 21st.dev component whose motion was framer-motion SPRING physics and whose counter did
    # `toFixed(0)` -- the first is time-dependent, and the second would have rendered 10.7 % as
    # "11 %". Both were reimplemented, and this is the measurement that says the reimplementation
    # worked rather than my believing it did.
    # It compares the DOM, not pixels: two reduced-motion captures of the identical screen differ by
    # a few hundred pixels of glyph antialiasing and WebGL compositing, which measures Chrome and not
    # the product. Every figure, label, caption, bar height and map count must match across two
    # renders from fresh profiles.
    # It builds nothing and starts its own server, so it needs no setup; it exits 3 only when there is
    # no build to check or no browser to check it with.
    # THE ENGINE EXISTS TWICE NOW, and this is the only reason that is acceptable. results/engine.mjs
    # is the 100 functions that draw the configure and results stages, lifted byte for byte out of the
    # page so the React app can drive them instead of reimplementing them. The inline copy stays,
    # because deleting it would force index.html to load a module and browsers block that over
    # file:// -- a judge who double-clicks the page would get a blank screen.
    # So: two copies, and a step that refuses to let them drift. It also asserts the pick-stage fence
    # (React owns the map and the search; the engine must not define them) and that the live agent's
    # five functions and nine element ids are present, since a results stage can lose the live path
    # and still look finished.
    ("results/engine.mjs is still the page's own engine, byte for byte",
     [sys.executable, "verify_results_matches_page.py"], TESTING),
    # THE MARKUP TRAVELLED TOO, and it needs its own gate. The engine finds its targets by element id,
    # so the React app renders the page's own configure and results markup verbatim rather than a
    # retyped copy. This asserts it is still the page's markup, AND -- the part that actually catches
    # things -- that every one of the engine's 105 element lookups is accounted for: in the markup,
    # created at runtime, rendered by React, or behind a null guard. An unaccounted id is a panel that
    # writes into nothing, and the page's history says that takes every panel after it down with it.
    ("the app's engine markup is still the page's markup",
     [sys.executable, "verify_view_matches_page.py"], TESTING),
    # AND THE ONE THAT PRESSES THE BUTTONS. Everything above is static: it proves the code and the
    # markup are the page's. It cannot prove they were wired together. Three separate defects got
    # through the static checks and were caught only here -- a declaration that called fenced code, a
    # class selector no id-based check could see, and React re-applying its own innerHTML over the
    # engine's output. So this drives pick -> configure -> results in a real browser and checks what
    # lands on each screen.
    # 🔴 THE ONE FAILURE THAT WOULD BE COMPLETELY SILENT. The deployment serves demo/app/, the BUILT
    # bundle, which is committed. The Dockerfile installs Python dependencies and nothing else, so
    # there is no Node in the image and it cannot build the app. Edit app/src, commit, push: Render
    # rebuilds faithfully, deploys the bundle it already had, reports SUCCESS, and nothing a visitor
    # sees has changed. Every light green, the change invisible.
    # No other step here would notice. audit.py reads the single-file page, the byte-identity
    # verifiers compare the engine against the page, and the flow check drives whatever bundle is on
    # disk. So this compares a hash of the app source against the one recorded when the bundle was
    # built. Exit 3 when there is no bundle or no stamp, because a skip is not a pass.
    ("the shipped React bundle was built from the committed source",
     [sys.executable, "verify_shipped_app_is_current.py"], TESTING,
     {3: "no bundle in AGENTIC-ARBITER/demo/app or no build stamp. Build it with "
         "`python tools/build_app.py`. The single-file page is unaffected."}),
    # 🔴 AND THE BUNDLE HAS TO BE THE PAGE A VISITOR REACHES, which the step above does not check.
    # It passed, correctly, while the deployed site served the OLD single-file interface: the static
    # root is demo/, so `/` returned demo/index.html and the bundle sat at /app/, reachable only if
    # you knew to type it. "The bundle is current" and "the bundle is what / returns" are different
    # claims. This one starts the real server and asks it for the root over HTTP.
    ("the root URL serves the React app, not the page it replaced",
     [sys.executable, "verify_deployed_root_is_the_app.py"], TESTING,
     {3: "no bundle in AGENTIC-ARBITER/demo/app. Build it with `python tools/build_app.py`."}),
    ("the new UI carries the whole product, pick to results, in a browser",
     [sys.executable, "verify_app_flow.py"], TESTING,
     {3: "no build in AGENTIC-ARBITER/app/dist, or no browser. The single-file page remains "
         "canonical, so this is not a failure of the pipeline."}),
    # THE STOP CONTROL IS A SPEND CONTROL, so what it is checked against is a CALL COUNT. The
    # vendor bills at submit and polls free, so pressing stop can only prevent a window that has
    # not been submitted yet -- and this asserts it prevents exactly those and no more, with the
    # FortyGuard functions stubbed so the assertion itself costs nothing.
    ("Stop agent now prevents the un-submitted calls, and only those",
     [sys.executable, "verify_stop_control.py"], TESTING),
    # THE DOWNLOAD HAS TO EXIST AND THE ROUTE BEHIND IT HAS TO WORK, and those are separate
    # claims: a button pointing at a broken route and a working route with no button both look
    # fine from one side. Driven with a replay fixture, so it costs nothing.
    ("a live run offers its own report, and the route returns a real PDF",
     [sys.executable, "verify_live_report_button.py"], TESTING),
    # THE INTRO IS THE ONLY THING IN THE PRODUCT THAT CAN COVER THE PRODUCT. verify_app_flow runs
    # with ?motion=off precisely so it never meets the enter gate, which means nothing else in this
    # list would notice if the gate started swallowing the Configure click forever. This is where
    # that is checked WITH motion on, along with the two kill switches, the audio rules and the
    # contrast of every line on the gate in both palettes.
    ("the cinematic intro opens, unmounts, and never blocks the product",
     [sys.executable, "verify_intro.py"], TESTING,
     {3: "no build in AGENTIC-ARBITER/app/dist, or no browser. The single-file page is unaffected."}),
    # 🔴 A SEPARATE STEP FROM verify_intro, AND ON A REAL CLOCK. The launch sequence is GSAP-driven and
    # runs for about seven seconds; GSAP does not advance under the virtual-time budget every other
    # browser check uses (05-TRAPS 5b.13), so the cues attached to its labels are never reached there.
    # This one removes the budget and lets serve_app.py --hold give the page real wall-clock seconds,
    # which is the only way to measure the whoosh, the push-in and the escape hatch's real timing.
    # It is therefore SLOW, about three minutes, and it costs nothing: no API calls, no writes outside
    # app/dist.
    ("the Initialize Arbiter cinematic holds, plays, crosses over, and can always be escaped",
     [sys.executable, "verify_launch.py"], TESTING,
     {3: "no build in AGENTIC-ARBITER/app/dist, or no browser. The single-file page is unaffected."}),
    # THE THREE POINTER-AND-KEYBOARD CHECKS, added 2026-08-30. They are here rather than in a
    # scratch folder because each one guards a fault that shipped: a tooltip that painted under its
    # neighbour, a dropdown that was a dead clone of a wired control, and a revolving dot that never
    # came back after a navigation. All three drive Chrome over the DevTools Protocol
    # (testing/cdp.py), because `:hover` and `:focus-visible` cannot be produced from inside the page.
    # Free: a loopback server and a headless browser, no network and no credential.
    ("the (i) panel is opaque, alone, on top and reachable from the keyboard",
     [sys.executable, os.path.join(TESTING, "verify_tooltip.py")], ROOT),
    ("the hour dropdown drives the tape, and the coverage tile states a computed shortfall",
     [sys.executable, os.path.join(TESTING, "verify_results_surfaces.py")], ROOT),
    ("the landing copy, the value card, the loop's labels, the pulse and the reload",
     [sys.executable, os.path.join(TESTING, "verify_landing_surfaces.py")], ROOT),
    # ⚠ THIS ONE RUNS SHORT VIEWPORTS ON PURPOSE, 1366x768 and 1400x820. The scroll fault it guards
    # was invisible to every other browser check in this repository because they all use a tall
    # window (1500x1400, 1500x1000, 1600x1000, 1440x1000), and the page only clipped when the
    # viewport was short enough for the rail to run past the bottom of it.
    ("the page scrolls at a short viewport, and a theme choice stays on its own screen",
     [sys.executable, os.path.join(TESTING, "verify_scroll_and_theme.py")], ROOT),
    # ⚠ THIS ONE RUNS CHROME'S REAL AUTOPLAY RULE AND A REAL POINTER CLICK, and both halves matter.
    # verify_launch.py above is 71 green checks about the same sequence and is STRUCTURALLY unable to
    # see an autoplay refusal: it passes --autoplay-policy=no-user-gesture-required and presses the
    # button with el.click(), which carries no user activation. The transition whoosh was refused
    # 8 times out of 8 in every real browser while that suite was green.
    ("the intro's three sounds actually play, under the real autoplay rule",
     [sys.executable, os.path.join(TESTING, "verify_audio_unlock.py")], ROOT),
    ("the React app renders the same numbers twice, from fresh profiles",
     [sys.executable, "verify_app_deterministic.py"], TESTING,
     {3: "no build in AGENTIC-ARBITER/app/dist, or no browser. The app is a prototype and the "
         "single-file page remains canonical, so this is not a failure of the pipeline."}),
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
