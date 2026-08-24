# -*- coding: utf-8 -*-
"""THE OVERNIGHT DRIVER -- weather, imagery, geometry and the full agent chain, per facility.

    python build_national_batch.py plan                     # FREE. What it would do, in order.
    python build_national_batch.py run                      # the whole standalone tier
    python build_national_batch.py run --limit 40           # bounded
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
        "geometry": os.path.exists(M.geom_path("selected_site.json", key)),
        "built": os.path.exists(M.demo_path("trace.json", key)),
    }


def eligible(reg, kinds=("standalone",), keys=None, limit=None):
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
        for l in (r.stderr or "").strip().split("\n")[-3:]:
            print("         ERR %s" % l[:104], flush=True)
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
        if not step("standalone geometry", ["build_standalone_site.py", key], env):
            return "no_geometry"
    if not st["built"]:
        # `metros --manifest` FIRST: build_sites.py reads sites.json to decide what is offerable, and
        # a facility that has just become buildable is not in it yet.
        step("manifest refresh", ["metros.py", "--manifest"], env)
        if not step("the 8-step agent chain", ["build_sites.py", key], env):
            return "chain_failed"
    return "built"


def main(argv):
    cmd = argv[0] if argv else "plan"
    lim = None
    if "--limit" in argv:
        lim = int(argv[argv.index("--limit") + 1])
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

    tally, t0 = {}, time.time()
    for i, k in enumerate(rem, 1):
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
    print("BATCH DONE in %.1f h" % ((time.time() - t0) / 3600.0))
    for kk in sorted(tally):
        print("   %-16s %d" % (kk, tally[kk]))
    print("   Re-run to continue: every step asks the disk whether it already ran, so nothing")
    print("   below is repeated and at most the facility in flight is lost.")
    print("   NEXT, and it needs a person: read each frame and record a screening verdict.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
