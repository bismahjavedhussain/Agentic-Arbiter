# -*- coding: utf-8 -*-
"""THE OVERNIGHT DRIVER -- weather, imagery, geometry and the full agent chain, per facility.

    python build_national_batch.py plan                     # FREE. What it would do, in order.
    python build_national_batch.py run                      # the whole standalone tier
    python build_national_batch.py run --limit 40           # bounded by COUNT
    python build_national_batch.py run --hours 9            # bounded by TIME, stops between sites
    python build_national_batch.py run --keys A B C         # named facilities
    python build_national_batch.py status                   # what is done. No network.

ZERO FORTYGUARD CALLS. Every network request here is free and keyless: Iowa State Mesonet for
weather, the ArcGIS export endpoint for one aerial frame. `FORTYGUARD_API_KEY` is never read --
`env_params` purchases are a separate, authorised, per-call decision and are deliberately not
automated here.

--------------------------------------------------------------------------------------------
WHY A DRIVER, AND WHAT IT IS HONEST ABOUT
--------------------------------------------------------------------------------------------
Per facility the chain is six steps and about six and a half minutes, almost all of it waiting on a
free service that rate-limits. 359 standalone facilities is therefore a ~40-hour job, which means it
runs unattended or not at all. That is fine for the mechanical steps. It is NOT fine for one of
them, and this module refuses to pretend otherwise:

🔴 THE IMAGERY VERDICT IS NOT AUTOMATED, AND WILL NOT BE.
   The screening gate asks whether the cooling plant sits at ground level, where FortyGuard's 2 m
   field applies. It is the only gate that has ever refused a whole metro -- Santa Clara for
   roof-mounted plant, Phoenix for never having been built -- and answering it means LOOKING at the
   frame. This driver fetches the frame and records `NOT YET ASSESSED`. A facility then ships at the
   `national_unscreened` tier with that stated on its page, and is upgraded only when a real
   assessment is recorded against it by name. A script asserting a verdict nobody made would be the
   worst defect this project could ship, because it would be invisible.

RESUMABLE BY CONSTRUCTION, not by a checkpoint file. Every step is idempotent and asks the disk
whether it already ran: `assign_station` skips a station whose record exists, `fetch_weather` returns
"cached", `fetch_facility_imagery` will not refetch a frame, and the chain is skipped for a facility
whose trace is newer than its geometry. So killing this at any point and re-running it loses at most
the facility in flight -- which matters, because a 40-hour run WILL be interrupted.

⚠ AND THE COURTESY POINT, because it is a real cost and not a rate-limit worry. Iowa State's Mesonet
and the ArcGIS basemap are free, shared, volunteer-and-taxpayer-funded services. This paces itself
(a pause between facilities, the fetchers' own backoff on top) and it processes facilities ONE AT A
TIME. Parallelising it would finish sooner and would be the wrong thing to do.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")
WEATHER = os.path.join(IA, "data", "weather")
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import metros as M                                                   # noqa: E402

# A pause between facilities, on top of each fetcher's own backoff. Not a performance knob.
PAUSE_S = 4.0
STEP_TIMEOUT_S = 3600


def registry():
    return json.load(open(os.path.join(GEOM, "national_registry.json"),
                         encoding="utf-8"))["facilities"]


def assignments():
    p = os.path.join(WEATHER, "station_assignments.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding="utf-8"))["assignments"]
    except (ValueError, KeyError):
        return {}


def _geometry_done(key, kind):
    """Is this facility's geometry COMPLETE for its kind, not merely started?

    standalone -- `selected_site.json` is the whole of it: there is no receptor, so the direction
                  table is legitimately a zero surface and `worst: None` is the correct value.
    paired     -- the chain rederives `modes.<mode>.worst.bearing`, so the direction table must
                  exist AND carry a real worst bearing for both placements. A table whose `worst`
                  is null is the standalone stub, and rebuilding is cheap next to failing 69 s into
                  the agent chain with a traceback that names neither this file nor the cause.
    """
    if not os.path.exists(M.geom_path("selected_site.json", key)):
        return False
    if kind == "standalone":
        return True
    # THE SAME TEST THE MANIFEST USES, imported rather than restated. Two copies of this disagreed
    # for an hour and published a site backed by a standalone stub -- see
    # `metros.paired_geometry_ready`'s docstring for what that cost.
    return M.paired_geometry_ready(key)


def state_of(key, reg, asn):
    """What is already true for this facility. All stat() and JSON reads -- nothing inferred."""
    f = reg[key]
    have_station = key in asn
    wx = None
    if have_station:
        try:
            wx = os.path.exists(M.weather_path(key))
        except SystemExit:
            wx = False
    return {
        "kind": f["kind"],
        "station": have_station,
        "weather": bool(wx),
        "frame": os.path.exists(os.path.join(M.imagery_dir(key), "screen_manifest.json")),
        # 🔴 NOT `selected_site.json` ALONE, FOR A PAIRED FACILITY. That file only proves the pair
        # was CHOSEN; the chain also needs the refusal surface, and for a while build_paired_site
        # wrote a standalone STUB there -- every row zero, `worst: None`. A presence test called
        # that geometry "done", so the batch skipped the geometry step and handed the stub to the
        # chain, which died 69 s later in ticker.py on "'NoneType' object is not subscriptable".
        # Same shape as `built` testing `trace.json` alone, noted directly below: the FIRST
        # artefact of several cannot answer "did this stage finish".
        "geometry": _geometry_done(key, f["kind"]),
        # NOT trace.json alone: that is the first of six artefacts, and testing it made an
        # interrupted chain permanently indistinguishable from a finished one.
        "built": all(os.path.exists(M.demo_path(n + ".json", key))
                     for n in M.REQUIRED_ARTEFACTS),
    }


# KINDS WIDENED 2026-08-25, once build_paired_site.py existed. This defaulted to ("standalone",)
# because that was the only path with a geometry builder -- so a run given 127 paired keys silently
# reduced to the 10 standalone ones and reported success over a tenth of the work. The paired kinds
# are admitted now; `do_facility` routes each to the builder that fits it.
def eligible(reg, kinds=("standalone", "paired_clear", "paired_advisory"), keys=None, limit=None):
    """Which facilities this driver will touch, in a DETERMINISTIC, impact-ordered sequence.

    Ordered by longest facade -- the measured proxy for plant size, and therefore for how much a
    result at that site is worth. Deterministic so an interrupted run resumes in the same order
    rather than re-deciding what matters each time.
    """
    ks = [k for k in reg if reg[k]["kind"] in kinds]
    if keys:
        want = set(keys)
        ks = [k for k in ks if k in want]
    ks.sort(key=lambda k: -(reg[k].get("longest_facade_m") or 0))
    return ks[:limit] if limit else ks


def reg_kind(key):
    """This facility's classification, read from the registry rather than inferred from its key."""
    try:
        return (registry().get(key) or {}).get("kind")
    except Exception:                                                # noqa: BLE001
        return None


def step(label, cmd, env, quiet=True):
    t = time.time()
    r = subprocess.run([sys.executable] + cmd, cwd=HERE, env=env,
                       capture_output=True, text=True, timeout=STEP_TIMEOUT_S)
    ok = (r.returncode == 0)
    tail = [l for l in (r.stdout or "").strip().split("\n") if l.strip()][-1:]
    print("      %-34s %s %6.1fs  %s"
          % (label, "OK    " if ok else "FAILED", time.time() - t,
             (tail[0].strip()[:56] if tail and not quiet else "")), flush=True)
    if not ok:
        # 🔴 STDOUT TOO, AND THIS IS THE THIRD MODULE WITH THIS EXACT BUG. `build_sites.py` and
        # `build_paired_site.py` both printed only stderr on failure, and every child in this
        # project REFUSES CLEANLY -- it explains itself on stdout and exits non-zero with stderr
        # empty. So the log read "FAILED" followed by a bare "ERR " with nothing after it.
        # Measured cost: 23 chain failures in the overnight batch, every one of them logged with an
        # empty ERR, diagnosed only by re-running a child by hand the next morning. A diagnostic
        # that omits the stream the reason is written to is worse than no diagnostic, because it
        # looks like the reason was absent rather than unprinted.
        out = [l for l in (r.stdout or "").strip().split("\n") if l.strip()]
        for l in out[-18:]:
            print("         %s" % l[:150], flush=True)
        err = [l for l in (r.stderr or "").strip().split("\n") if l.strip()]
        for l in err[-4:]:
            print("         ERR %s" % l[:150], flush=True)
        if not err:
            print("         ERR (stderr empty -- the child refused cleanly with exit %d; the reason "
                  "is in the output above)" % r.returncode, flush=True)
    return ok


def do_facility(key, st):
    """The six steps, each skipped if the disk says it already ran."""
    env = dict(os.environ, METRO=key)
    if not st["station"]:
        if not step("weather: assign a station", ["assign_station.py", "run", key], env):
            return "no_station"
    if not st["frame"]:
        step("imagery: one aerial frame", ["fetch_facility_imagery.py", key], env)
    if not st["geometry"]:
        # ROUTE BY KIND. A standalone facility has no receptor, so its rise table is identically zero
        # and `build_standalone_site.py` writes it directly. A paired facility has a real neighbour,
        # so it goes through the same funnel Ashburn did -- select the committed pair against the
        # three published gates, rasterise both rings, place the bank and the intake -- and its rise
        # table is SOLVED rather than written. Choosing the wrong builder here would either invent a
        # receptor or throw a real one away, so it is keyed off the registry's own classification.
        kind = (reg_kind(key) or "standalone")
        if kind in ("paired_clear", "paired_advisory"):
            if not step("paired geometry: commit a pair and solve", ["build_paired_site.py", key],
                        env):
                return "no_geometry"
        elif not step("standalone geometry", ["build_standalone_site.py", key], env):
            return "no_geometry"
    if not st["built"]:
        # `metros --manifest` FIRST: build_sites.py reads sites.json to decide what is offerable, and
        # a facility that has just become buildable is not in it yet.
        step("manifest refresh", ["metros.py", "--manifest"], env)
        ok = step("the 8-step agent chain", ["build_sites.py", key], env)
        # AND AGAIN AFTERWARDS, WHICH MATTERS MOST WHEN THE CHAIN FAILED.
        # The refresh above marks this facility offerable the moment it becomes buildable. If the
        # chain then dies partway -- and across 340 facilities on 335 new weather stations, some
        # will -- the manifest is left OFFERING a site whose later artefacts were never written, and
        # every audit run for the rest of the night fails on it. That is exactly how three
        # facilities (CO_way_1273968634, IA_way_191655977, OH_way_1281982556) came to be listed as
        # offerable with four artefacts missing each.
        # Re-reading the manifest after the attempt puts the facility back where it belongs, with
        # `not_offerable_because` naming what is absent. An unattended run must leave the build
        # GREEN when a facility fails, not red -- otherwise one bad station poisons the morning.
        step("manifest re-read", ["metros.py", "--manifest"], env)
        if not ok:
            return "chain_failed"
    return "built"


def main(argv):
    cmd = argv[0] if argv else "plan"
    lim = None
    if "--limit" in argv:
        lim = int(argv[argv.index("--limit") + 1])
    # A TIME BUDGET, CHECKED BETWEEN FACILITIES AND NEVER INSIDE ONE.
    # `--limit` bounds the run by COUNT, which is the wrong unit for "run this overnight and stop
    # before I need the machine": a facility takes 1.5 min if its station is already cached and
    # about 7 if it is not, so any count is a guess at the wall clock. The check happens before a
    # facility STARTS, so the run always stops on a clean boundary -- killing it on a timer instead
    # would land mid-fetch and lose the facility in flight, which is the one thing this driver's
    # resumability is built to avoid.
    hours = None
    if "--hours" in argv:
        hours = float(argv[argv.index("--hours") + 1])
    keys = None
    if "--keys" in argv:
        keys = [a for a in argv[argv.index("--keys") + 1:] if not a.startswith("--")]

    reg = registry()
    asn = assignments()
    todo = eligible(reg, keys=keys, limit=lim)
    states = {k: state_of(k, reg, asn) for k in todo}

    if cmd == "status":
        done = [k for k in todo if states[k]["built"]]
        print("=" * 78)
        print("NATIONAL BATCH STATUS -- no network calls")
        print("=" * 78)
        for nm, fn in (("station assigned", "station"), ("weather record", "weather"),
                       ("aerial frame", "frame"), ("geometry written", "geometry"),
                       ("full chain built", "built")):
            print("   %-20s %4d / %d" % (nm, sum(1 for k in todo if states[k][fn]), len(todo)))
        print("\n   %d facility(ies) complete." % len(done))
        if done:
            print("   most recent: %s" % ", ".join(done[:4]))
        return 0

    if cmd == "plan":
        rem = [k for k in todo if not states[k]["built"]]
        need_wx = [k for k in rem if not states[k]["weather"]]
        print("=" * 78)
        print("NATIONAL BATCH PLAN -- %d facility(ies) in scope, %d already built"
              % (len(todo), len(todo) - len(rem)))
        print("=" * 78)
        print("   remaining                  : %d" % len(rem))
        print("   of those, needing weather  : %d  <- this is the whole cost" % len(need_wx))
        # MEASURED, not assumed: 5.05 min/station over the 8 stations fetched between 20:36 and
        # 21:17 on 2026-08-24, times the 1.3 stations a facility actually consumes (a candidate
        # below the 95 % coverage floor is rejected and the next one is fetched).
        mins = len(need_wx) * 5.05 * 1.3 + len(rem) * (80.0 / 60.0)
        print("   estimated wall clock       : %.1f h  (%.0f min)" % (mins / 60.0, mins))
        print("      weather is ~5.05 min/station measured, x ~1.3 stations per facility")
        print("      the chain is ~80 s/facility and is not the bottleneck")
        print("\n   first 10 in order (largest facade first):")
        for k in rem[:10]:
            f = reg[k]
            print("      %-22s %-3s %7.1f m  %s"
                  % (k, f["state"], f.get("longest_facade_m") or -1,
                     ", ".join(f.get("names") or ["(unnamed)"])[:34]))
        print("\n   The imagery VERDICT is not part of this. Frames are fetched and recorded")
        print("   NOT YET ASSESSED; a facility ships unscreened, with that stated, until a real")
        print("   assessment is recorded against it. See this module's docstring.")
        print("=" * 78)
        return 0

    if cmd != "run":
        raise SystemExit("commands: plan | run | status")

    rem = [k for k in todo if not states[k]["built"]]
    print("=" * 78)
    print("NATIONAL BATCH RUN -- %d facility(ies). One at a time, on purpose." % len(rem))
    print("=" * 78)
    # Gotcha #149: a long unattended run whose output is redirected to a file must not be
    # block-buffered, or there is no way to see what it is doing without checking side effects.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:                                                # noqa: BLE001
        pass

    tally, t0, stopped_early = {}, time.time(), None
    for i, k in enumerate(rem, 1):
        if hours is not None and (time.time() - t0) >= hours * 3600.0:
            stopped_early = i - 1
            print("\n   TIME BUDGET REACHED -- %.2f h of %.2f h used, stopping BEFORE facility "
                  "%d of %d rather than interrupting it."
                  % ((time.time() - t0) / 3600.0, hours, i, len(rem)), flush=True)
            break
        f = reg[k]
        print("\n[%d/%d] %-22s %-3s %s  (%.1f h elapsed)"
              % (i, len(rem), k, f["state"],
                 ", ".join(f.get("names") or ["(unnamed)"])[:36], (time.time() - t0) / 3600.0),
              flush=True)
        try:
            out = do_facility(k, states[k])
        except subprocess.TimeoutExpired:
            out = "timeout"
        except Exception as e:                                       # noqa: BLE001
            out = "error:%s" % type(e).__name__
            print("      unexpected: %s" % str(e)[:96], flush=True)
        tally[out] = tally.get(out, 0) + 1
        print("      -> %s" % out, flush=True)
        if i < len(rem):
            time.sleep(PAUSE_S)

    print("\n" + "=" * 78)
    print("BATCH DONE in %.2f h" % ((time.time() - t0) / 3600.0))
    if stopped_early is not None:
        print("   STOPPED ON THE TIME BUDGET, not because the work ran out:")
        print("      %d facility(ies) attempted, %d of %d still to do."
              % (stopped_early, len(rem) - stopped_early, len(rem)))
    for kk in sorted(tally):
        print("   %-16s %d" % (kk, tally[kk]))
    print("   Re-run to continue: every step asks the disk whether it already ran, so nothing")
    print("   below is repeated and at most the facility in flight is lost.")
    print("   NEXT, and it needs a person: read each frame and record a screening verdict.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
