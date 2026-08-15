# -*- coding: utf-8 -*-
"""N-7  ---  is there actually a compute bottleneck?  FREE.

The NVIDIA claim must be a measured bottleneck, not a logo. This measures how long
a real ensemble takes on CPU and extrapolates to the daily agent cycle.

  "the GPU gives Nx, so a 100-run ensemble over 20 sites takes S seconds not M minutes"
     -> a stated bottleneck, defensible
  "we used NVIDIA Warp"
     -> a logo

If CPU is fast enough, say so and drop the GPU claim. That is the honest outcome.
"""
import sys, time
import numpy as np
from solver import Site, solve, intake_temperature, demo_site, ensemble, HAVE_WARP
from common import banner, save_result, verdict

CYCLE_BUDGET_S = 300.0     # a daily agent cycle should finish inside 5 minutes
N_SITES = 20
N_ENSEMBLE = 100


def time_one(dx):
    s, intake = demo_site(dx=dx)
    t0 = time.time()
    T = solve(s, 30.0, 3.0, 270.0)
    dt = time.time() - t0
    return dt, s.n, intake_temperature(T, s, *intake) - 30.0


def main():
    banner("N-7  Is there a real compute bottleneck?   [FREE]")
    print("   NVIDIA Warp installed: %s" % ("YES" if HAVE_WARP else "NO"))

    print("\n   single-solve cost on CPU (NumPy):")
    rows = []
    for dx in (20.0, 10.0, 5.0):
        dt, n, rise = time_one(dx)
        rows.append({"dx": dx, "grid": n, "secs": round(dt, 3), "rise": round(rise, 4)})
        print("      dx=%4.1f m   grid %dx%d   %7.3f s   rise %+.4f C" % (dx, n, n, dt, rise))

    print("\n   extrapolated to one daily agent cycle (%d sites x %d ensemble members):"
          % (N_SITES, N_ENSEMBLE))
    print("      dx      per solve      cycle total          verdict")
    verdicts = {}
    for r in rows:
        total = r["secs"] * N_SITES * N_ENSEMBLE
        if total < CYCLE_BUDGET_S:
            v = "CPU is fine"
        elif total < 3600:
            v = "CPU too slow for a 5-min cycle"
        else:
            v = "CPU IMPOSSIBLE (%.1f hours)" % (total / 3600)
        verdicts[r["dx"]] = {"total_s": total, "verdict": v}
        print("      %4.1f m   %7.3f s   %10s   %s"
              % (r["dx"], r["secs"],
                 ("%.0f s" % total) if total < 600 else ("%.1f h" % (total / 3600)), v))

    # measured ensemble at the working resolution
    print("\n   MEASURED ensemble (not extrapolated), dx=10 m, 1 site:")
    s, intake = demo_site(dx=10.0)
    for n_runs in (5, 20):
        t0 = time.time()
        d = ensemble(s, intake, 30.0, 0.6, 3.0, 270.0, n_runs=n_runs, seed=1)
        el = time.time() - t0
        print("      %3d runs  %7.2f s   (%.3f s/run)   intake rise mean %+.3f C  sd %.3f  p90 %+.3f"
              % (n_runs, el, el / n_runs, d.mean(), d.std(), np.percentile(d, 90)))
    per_run = el / n_runs
    full = per_run * N_SITES * N_ENSEMBLE

    print("\n   -> full cycle at dx=10: %.0f s  (%.1f min) on CPU" % (full, full / 60))
    print("   -> full cycle at dx=5 : %.1f h on CPU" % (rows[2]["secs"] * N_SITES * N_ENSEMBLE / 3600))

    bottleneck = full > CYCLE_BUDGET_S
    print()
    verdict(bottleneck,
            "PASS - there IS a real bottleneck. A %d-site x %d-member ensemble needs %.0f s on CPU, "
            "over the %.0f s cycle budget. GPU acceleration is justified by a measured number."
            % (N_SITES, N_ENSEMBLE, full, CYCLE_BUDGET_S),
            "FAIL - CPU finishes in %.0f s, inside the %.0f s budget. THE GPU CLAIM IS NOT JUSTIFIED "
            "at this resolution; either raise resolution/ensemble size or drop the Warp story and "
            "keep NVIDIA to local Nemotron only." % (full, CYCLE_BUDGET_S))

    if not HAVE_WARP:
        print("\n   NOTE: Warp is not installed, so no GPU comparison was measured.")
        print("         The port is the same kernel; the speedup number must be measured before")
        print("         it is claimed. Do not quote a speedup we have not observed.")

    save_result("n7_speedup.json", {"warp_installed": HAVE_WARP, "single_solve": rows,
                                    "extrapolated": verdicts, "per_run_s": per_run,
                                    "full_cycle_s": full, "bottleneck": bottleneck})
    return 0 if bottleneck else 1


if __name__ == "__main__":
    sys.exit(main())
