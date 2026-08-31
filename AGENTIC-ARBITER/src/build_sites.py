# -*- coding: utf-8 -*-
"""BUILD EVERY OFFERABLE SITE, each on its own weather, its own geometry, its own bound.

    python build_sites.py                # every offerable site in sites.json
    python build_sites.py chicago dulles # only these

ZERO API CALLS.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS
--------------------------------------------------------------------------------------------
The interface offered a site picker with three entries, and picking one changed exactly ONE panel:
the solved plume field. The headline, the schedule, the decision, the explanation, the wind dial,
the coverage record, the ladder and the money were all Ashburn's, wearing whichever label the picker
was set to. `backtest.py` and `rolling.py` had no idea a second metro existed.

That is a promise the engine could not keep, and it is the sort of thing a judge checks by switching
sites and watching whether anything moves.

`agent.py` is now metro-aware, and because `backtest.py` and `rolling.py` take ALL their data
through `agent.load_hours()`, `agent.rise_table()` and `agent.perceive_fortyguard()`, making the one
module metro-aware made all three. This driver just runs the chain per site with METRO set.

--------------------------------------------------------------------------------------------
WHAT IS GENUINELY PER-SITE, AND WHAT IS BORROWED -- read this before quoting a non-Ashburn number
--------------------------------------------------------------------------------------------
OWN, for every site:
    building footprints          its own OSM ways, its own committed pair, its own facade gap
    5-year weather record        its own ASOS station -- KIAD 43,763 h, KORD 43,775 h
    576 GPU plume solves         its own geometry, its own refusal set, its own worst bearing
    conformal margins            quantiles of ITS OWN station's forecast residuals
    plume spread + calibration   its own -- ⚠ TRUE ONLY SINCE 2026-08-24. Before that the spread
                                 table and the plume calibration were cached to unsuffixed
                                 filenames, so Chicago's and Dulles's plume margin was measurably
                                 Ashburn's. Fixed by making both paths go through M.demo_path and
                                 by running plume_uncertainty.py per site as step 1 of this chain
    the whole scheduling sweep   120,960 scenarios on its own days
    the money table              its own STATE's EIA tariff -- Illinois is 11.81 c/kWh against
                                 Virginia's 8.72, a 35 % difference, so this is not cosmetic

BORROWED FROM ASHBURN, and stated in every trace:
    the four MEASURED FortyGuard level offsets, and the N-26 coverage record
Only Ashburn has forecast/outcome day pairs. Chicago holds one past-window field and Dulles none, so
there is nothing to measure a level offset against at those sites. Quote a site's HOURS as its own;
quote the COVERAGE as Ashburn's. `trace.fortyguard_provenance` says so in the artefact itself.

DULLES IS THE INTERESTING CONTROL. It shares KIAD with Ashburn, so its weather is identical and only
its GEOMETRY differs -- which isolates the geometry-and-operator effect from climate. Expect its
five-year numbers to sit close to Ashburn's, and that closeness is a measurement, not a bug.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import metros as M                                                  # noqa: E402

# Order matters exactly as in run_all.py: the backtest needs the agent's rise tables, rolling needs
# the backtest's state builder, money prices the backtest's ladder, ticker reads all three.
CHAIN = [
    # FIRST, and it was missing until 2026-08-24. The spread tables and the plume calibration are
    # resampled from THIS site's rise table and fitted on THIS site's weather record, so they are
    # per-site measurements -- but `run_all.py` ran this module once, globally, and every other site
    # then read the reference site's file. `agent.py` needs the calibration, so it has to come
    # before the agent, exactly as it does in run_all's own ordering.
    ("plume uncertainty: this site's spread tables + calibration", ["plume_uncertainty.py"]),
    ("the agent loop", ["agent.py", "run"]),
    ("five-year backtest", ["backtest.py", "all"]),
    ("rolling control", ["rolling.py"]),
    ("money, priced in this state's tariff", ["money.py"]),
    ("stage 7 explain, verified", ["explain.py"]),
    ("stage events", ["ticker.py"]),
    # 🔴 LAST, AND IT IS `site_report.py` SINCE 2026-08-31, NOT `report.py`. The PDF quotes the
    # explanation, the ladder, the rolling summary and the money table, so all of them have to
    # exist first. The GENERATOR was replaced: `report.py` writes the monospaced text-style PDF
    # and is still imported by `live_report.py`, which is why it stays in the tree.
    # `site_report.py` is the typeset one, with this site's own satellite frame and seven charts.
    #
    # ⚠ IT NEEDS `requirements-build.txt` (reportlab, svglib, matplotlib, pillow, brotli), which
    # the deploy image deliberately does not carry. A host without them cannot run this step, and
    # that is correct rather than unfortunate: these PDFs are built here and committed, because
    # `serve_live.py` promises that serving demo/ as static files gives the whole replay demo.
    #
    # ⚠ AND IT IS NOT IN SKIP_FOR_STANDALONE. A facility with no neighbour still gets a full
    # report; what it does not get is the plume section, which `site_report.py` drops from the
    # document and from its contents page on its own.
    ("downloadable PDF report", ["site_report.py"]),
]


def offerable_sites():
    """Read from the manifest, not listed here. `metros.export_manifest()` is the only thing allowed
    to decide what may be offered -- it gates on data readiness AND an in-scope architecture verdict
    for the committed pair, and it already caught itself offering two sites the imagery gate had
    refused (gotcha #69)."""
    p = os.path.join(DEMO, "sites.json")
    if not os.path.exists(p):
        raise SystemExit("demo/sites.json missing -- run `python metros.py --manifest` first")
    # 🔴 `data_ready` OR `offerable`, NOT `offerable` ALONE.
    # `offerable` means "the interface may show this site", which requires its artefacts to already
    # exist. Gating a BUILD on it is circular -- a facility could never be built because it had not
    # been built. `data_ready` is the question that actually applies here: does this facility have
    # its own geometry and its own >= 95 % weather record, so that building it would produce an
    # honest result? `offerable` is kept in the test so the five hand-built metros, which predate
    # the distinction, behave exactly as before.
    # 🔴 A SCREENED REFUSAL IS NOT A BUILD TARGET, AND THIS GATE LET TWO OF THEM THROUGH.
    # `data_ready` asks only whether the DATA exists -- geometry, its own weather, a runnable kind.
    # It says nothing about the imagery scope gate, and `phoenix` (NOT BUILT) and `santaclara`
    # (ROOFTOP) both satisfy it: they have candidate geometry and a full weather record, and they
    # were refused for a reason no amount of data changes. So `--others` handed them to the chain,
    # which died on the first step with FileNotFoundError on `phoenix_solver_site_longest.json` --
    # a file that does not exist precisely BECAUSE the site was refused before geometry was solved.
    # run_all step 13 has been failing on this, which is why the rebuild could not go green.
    #
    # THE DISTINCTION IS THE ONE metros.py ALREADY DRAWS, and it is load-bearing: "A screened
    # refusal and an unscreened unknown are different facts and the manifest keeps them different."
    #   GRADE         assessed, plant at ground level      -> build it
    #   NOT SCREENED  no verdict recorded yet              -> build it, and it ships saying so
    #   ROOFTOP       assessed and REFUSED                 -> never build it
    #   NOT BUILT     assessed and REFUSED                 -> never build it
    # So this filters on the RECORDED REFUSAL, not on `scope_ok` -- every one of the national
    # facilities is `scope_ok: false` because it is unscreened, and gating on that flag would refuse
    # the entire national tier.
    REFUSED_VERDICTS = ("ROOFTOP", "NOT BUILT")
    out = []
    for s in json.load(open(p, encoding="utf-8"))["sites"]:
        if not (s.get("offerable") or s.get("data_ready")):
            continue
        if s.get("scope_verdict") in REFUSED_VERDICTS:
            continue
        # AND A MECHANICAL PRECONDITION, independent of any verdict: the chain's first step solves
        # the rise table, which loads `<key>_solver_site_longest.json`. Without it the build cannot
        # start, so skipping here turns a traceback 60 s in into a stated skip now.
        if not os.path.exists(M.geom_path("solver_site_longest.json", s["key"])):
            continue
        out.append(s["key"])
    return out


def main():
    # NOT BLINDLY LOWERCASED. The five hand-built keys are lower case and every existing caller and
    # scheduled task types them that way, but a national facility key is `IA_way_1318322780` -- an
    # upper-case state prefix and a real OSM id. Lowercasing it produced
    # "not offerable: ia_way_1318322780" while the very same list printed `IA_way_1318322780` as
    # offerable, which is a confusing way to say "wrong case". Same trap `metro_key()` handles.
    known = offerable_sites()
    _by_lower = {x.lower(): x for x in known}
    argv = [_by_lower.get(a.lower(), a) for a in sys.argv[1:]]
    # `--others` = every offerable site EXCEPT the reference one, derived from the manifest rather
    # than typed. run_all.py builds the reference site through its own steps (its artefacts keep the
    # unsuffixed names the audited chain reads), so it wants exactly this set -- and it used to get
    # it as the literal ["chicago", "dulles"], which would silently skip a fourth site.
    if "--others" in argv:
        argv = [a for a in argv if a != "--others"]
        argv = argv or [k for k in known if k != M.DEFAULT_METRO]
    want = argv or known
    bad = [w for w in want if w not in known]
    if bad:
        raise SystemExit("not offerable: %s. Offerable: %s" % (", ".join(bad), ", ".join(known)))

    print("=" * 78)
    print("BUILD SITES -- %s.  ZERO API CALLS." % ", ".join(want))
    print("=" * 78)
    # WHICH STEPS A STANDALONE FACILITY SKIPS, AND WHY IT IS A SKIP AND NOT A FAILURE.
    # `plume_uncertainty.py` fits the WIDTH of the plume half of the bound to the spread of the
    # rise across bearings. A standalone facility's rise table is identically zero, so there is no
    # spread: measured, its four self-test assertions all fail (the difficulty signal is flat, the
    # normalized coverage is 1.0, the fixed and normalized margins are both 0.0) and `main()`
    # returns 1. Those assertions are RIGHT -- a flat difficulty signal means a normalized bound
    # buys nothing -- so the honest response is not to run the stage, and not to weaken its checks.
    # `agent.plume_uncertainty_terms()` then finds no calibration and DISABLES the plume term with
    # a reason, which is the path it has always had for a missing calibration.
    SKIP_FOR_STANDALONE = {"plume_uncertainty.py"}
    t0, failed = time.time(), []
    for k in want:
        m = M.metro(k)                            # was M.METROS[k]: KeyError on a national key
        kind = (m.get("facility") or {}).get("kind")
        print("\n" + "-" * 78)
        print("%s  (%s, station K%s, %s)%s"
              % (k.upper(), m["label"], m["station"], m["state"],
                 ("   [%s]" % kind) if kind else ""))
        print("-" * 78)
        env = dict(os.environ, METRO=k)
        for label, cmd in CHAIN:
            if kind == "standalone" and cmd[0] in SKIP_FOR_STANDALONE:
                print("   %-38s SKIPPED  -- no plume to calibrate at a facility with no "
                      "neighbour; the agent disables the term and says so" % label)
                continue
            t = time.time()
            r = subprocess.run([sys.executable] + cmd, cwd=HERE, env=env,
                               capture_output=True, text=True, timeout=3600)
            tail = [l for l in (r.stdout or "").strip().split("\n") if l.strip()][-1:]
            print("   %-38s %s in %5.1f s   %s"
                  % (label, "OK    " if r.returncode == 0 else "FAILED",
                     time.time() - t, (tail[0].strip()[:60] if tail else "")))
            if r.returncode != 0:
                failed.append("%s/%s" % (k, label))
                # 🔴 STDOUT TOO, AND ENOUGH OF IT. This printed the last 4 lines of STDERR only, so
                # a child that refuses CLEANLY -- writing its reason to stdout and nothing to
                # stderr -- produced a bare "ERR" with no text after it. Three failures in one day
                # were diagnosed only by re-running the child by hand: plume_uncertainty's
                # hard-quartile assertion, ticker's "'NoneType' object is not subscriptable", and
                # the direction-table stub behind it. The reason was on screen every time, in the
                # stream this did not print.
                out = [l for l in (r.stdout or "").strip().split("\n") if l.strip()]
                for l in out[-20:]:
                    print("      %s" % l[:150])
                err = [l for l in (r.stderr or "").strip().split("\n") if l.strip()]
                for l in err[-6:]:
                    print("      ERR %s" % l[:150])
                if not err:
                    print("      ERR (stderr empty -- refused cleanly with exit %d; the reason is "
                          "in the output above)" % r.returncode)
                break

    print("\n" + "=" * 78)
    if failed:
        print("BUILD FAILED at: %s" % "; ".join(failed))
    else:
        print("BUILT %d SITES in %.1f s. Each on its own weather, geometry and bound."
              % (len(want), time.time() - t0))
        for k in want:
            files = [f for f in sorted(os.listdir(DEMO))
                     if (f.startswith(k + "_") or (k == M.DEFAULT_METRO and "_" not in f))
                     and f.endswith(".json")]
            print("   %-10s %d artefacts" % (k, len(files)))
    print("=" * 78)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
