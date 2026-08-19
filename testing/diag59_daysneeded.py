# -*- coding: utf-8 -*-
"""DIAG-59 -- Is the 90 % promise RECOVERABLE, and does recovering it need a customer thermometer? FREE.

THE QUESTION
    Live coverage came in at 65.6 % against a 90 % promise. Two candidate causes, and they need
    separating because they have completely different remedies:

      CAUSE 1  OUR SAMPLE SIZE.  A one-sided split-conformal bound takes the k-th smallest calibration
               residual with k = ceil((n+1)(1-alpha)). For alpha = 0.10 that needs k <= n, i.e. n >= 9.
               With n = 3 the code clamps k to the maximum residual and the BEST ACHIEVABLE coverage is
               n/(n+1) = 3/4 = 75 %. **A 90 % bound was never obtainable from 3 days.** This is our
               problem, not FortyGuard's, and the remedy is free: collect more days.

      CAUSE 2  FORTYGUARD'S DAY-VARYING LEVEL OFFSET (validated in DIAG-58 against independent ASOS).
               Measured offsets over 4 days: +1.09, +0.80, -0.19, +3.64 C. A bound calibrated on days
               that never showed the +3.64 tail cannot cover it. The remedy is either MORE DAYS (so the
               tail enters calibration) or ANCHORING (remove the offset with a local reading).

    This file simulates coverage against the number of calibration days, so the two can be told apart
    and so we know whether the 90 % pitch is recoverable **without** customer hardware.

WHY THE METRIC IS EFFECTIVELY PER-DAY
    The offset is spatially UNIFORM -- DIAG-58 measured the shift as 3x to 12x the between-tile spread.
    So within a day nearly all 17,862 tiles pass or fail together, which is exactly why section 8e saw a
    "worst day 0.0 %". Pooled tile coverage is therefore approximately the fraction of DAYS covered, and
    that is what is simulated here.

⚠ THE HONEST LIMIT ON THIS FILE
    The offset distribution is estimated from **4 days**. Four. Every number below inherits that. The
    simulation is run three ways -- bootstrap from the 4 observed values, a normal fit, and a
    heavy-tailed fit -- and the SPREAD BETWEEN THOSE THREE is reported as the real uncertainty. No single
    "days needed" figure is quoted without that spread.
"""
import io
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import banner, save_result, RESULTS      # noqa: E402

MEASURED_OFFSETS = [1.0907, 0.8009, -0.1948, 3.6391]   # DIAG-58, validated against ASOS
WITHIN_DAY_SD = [0.1166, 0.0801, 0.0589, 0.3052]       # between-tile sd of the difference
ALPHA = 0.10
N_TRIALS = 20000
SEED = 59


def conformal_clamped(res, alpha=ALPHA):
    """Exactly what the project's conformal() does, INCLUDING the silent clamp."""
    r = np.sort(np.asarray(res, dtype=float))
    k = math.ceil((len(r) + 1) * (1.0 - alpha))
    return float(r[min(k, len(r)) - 1])


def theoretical_ceiling(n, alpha=ALPHA):
    k = min(math.ceil((n + 1) * (1.0 - alpha)), n)
    return k / (n + 1)


def draw(kind, rng, size):
    o = np.array(MEASURED_OFFSETS)
    if kind == "bootstrap":
        return rng.choice(o, size=size, replace=True)
    if kind == "normal":
        return rng.normal(o.mean(), o.std(ddof=1), size=size)
    if kind == "heavy":                       # t with 3 df, scaled to the measured sd
        t = rng.standard_t(3, size=size)
        return o.mean() + t * (o.std(ddof=1) / math.sqrt(3.0))
    raise ValueError(kind)


def main():
    banner("DIAG-59  is the 90 % bound recoverable, and does it need a thermometer?   [FREE]")

    o = np.array(MEASURED_OFFSETS)
    print("\n   measured offsets (DIAG-58, ASOS-validated): %s"
          % ", ".join("%+.2f" % x for x in o))
    print("   mean %+.3f C, sd %.3f C, n = 4 days   <-- everything below inherits this n = 4"
          % (o.mean(), o.std(ddof=1)))

    print("\n   [1] THE ARITHMETIC CEILING -- nothing to do with FortyGuard")
    print("      %5s %6s %16s" % ("days", "k", "max coverage"))
    for n in (3, 4, 6, 9, 12, 19):
        print("      %5d %6d %15.1f%%" % (n, min(math.ceil((n + 1) * 0.9), n),
                                          100 * theoretical_ceiling(n)))
    print("      => with 3 days the ceiling is 75 %. **The 90 % promise was never obtainable.**")
    print("      => 90 % first becomes possible at n = 9 days.")

    print("\n   [2] SIMULATED COVERAGE vs CALIBRATION DAYS, unanchored (pure FortyGuard)")
    rng = np.random.default_rng(SEED)
    kinds = ("bootstrap", "normal", "heavy")
    ns = [3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 19, 25, 30, 40]
    table = {}
    print("      %5s %10s %10s %10s %10s %s"
          % ("days", "ceiling", "bootstrap", "normal", "heavy", "verdict (worst of the three)"))
    for n in ns:
        cov = {}
        for kind in kinds:
            hits = 0
            for _ in range(N_TRIALS):
                cal = draw(kind, rng, n)
                q = conformal_clamped(cal)
                if draw(kind, rng, 1)[0] <= q:
                    hits += 1
            cov[kind] = hits / N_TRIALS
        worst = min(cov.values())
        table[n] = {"ceiling": theoretical_ceiling(n), **cov, "worst": worst}
        print("      %5d %9.1f%% %9.1f%% %9.1f%% %9.1f%%  %s"
              % (n, 100 * theoretical_ceiling(n), 100 * cov["bootstrap"], 100 * cov["normal"],
                 100 * cov["heavy"],
                 "reaches 90 %" if worst >= 0.90 else ("close" if worst >= 0.85 else "short")))

    ok = [n for n in ns if table[n]["worst"] >= 0.90]
    ok85 = [n for n in ns if table[n]["worst"] >= 0.85]
    print("\n      days needed for >= 90 %% on ALL THREE distributions : %s"
          % (min(ok) if ok else "not reached by %d" % max(ns)))
    print("      days needed for >= 85 %% on ALL THREE                : %s"
          % (min(ok85) if ok85 else "not reached"))

    print("\n   [3] WHAT IF WE ANCHOR? offset removed, only the between-tile spread remains")
    print("      within-day between-tile sd measured at %.4f-%.4f C -- two orders of magnitude"
          % (min(WITHIN_DAY_SD), max(WITHIN_DAY_SD)))
    print("      smaller than the offsets. Simulating with the offset removed:")
    print("      %5s %10s %12s" % ("days", "ceiling", "coverage"))
    anch = {}
    sd = float(np.mean(WITHIN_DAY_SD))
    for n in (3, 4, 6, 9, 12):
        hits = 0
        for _ in range(N_TRIALS):
            cal = rng.normal(0.0, sd, n)
            q = conformal_clamped(cal)
            if rng.normal(0.0, sd) <= q:
                hits += 1
        anch[n] = hits / N_TRIALS
        print("      %5d %9.1f%% %11.1f%%" % (n, 100 * theoretical_ceiling(n), 100 * hits / N_TRIALS))
    print("      => anchoring makes coverage hit the ARITHMETIC CEILING at every n, because the")
    print("         residual is small and well behaved. But the ceiling itself still caps you at")
    print("         75 %% with 3 days. **Anchoring does not rescue a too-small calibration set.**")

    print("\n" + "=" * 82)
    print("  CONCLUSION")
    print("=" * 82)
    print("  The 65.6 %% shortfall has TWO causes and they need different fixes:")
    print("    * 90 %% -> 75 %%  is OUR SAMPLE SIZE (n = 3). Unavoidable arithmetic. Fix: collect days.")
    print("    * 75 %% -> 65.6 %% is FORTYGUARD'S day-varying offset. Fix: more days OR anchoring.")
    print("  Both fixes point the same way first: **COLLECT MORE DAYS**, which is free and needs no")
    print("  customer hardware. %s more days of the existing daily task gets n to %d."
          % (max(0, (min(ok) if ok else 19) - 4), (min(ok) if ok else 19)))
    print("  Anchoring is a SECOND, independent improvement -- it does not substitute for days.")

    save_result("diag59_daysneeded.json", {
        "test": "DIAG-59 coverage vs calibration days",
        "measured_offsets_c": MEASURED_OFFSETS,
        "n_days_behind_offset_estimate": 4,
        "caveat": "the offset distribution is estimated from FOUR days; the spread across three "
                  "distributional assumptions is reported as the real uncertainty",
        "arithmetic_ceiling": {str(n): theoretical_ceiling(n) for n in ns},
        "unanchored_coverage": {str(k): v for k, v in table.items()},
        "anchored_coverage": {str(k): v for k, v in anch.items()},
        "days_for_90pct_all_three": (min(ok) if ok else None),
        "days_for_85pct_all_three": (min(ok85) if ok85 else None),
        "decomposition": {"90_to_75": "our sample size, n=3, arithmetic",
                          "75_to_65.6": "FortyGuard day-varying level offset"}})
    print("\n  written: testing/results/diag59_daysneeded.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
