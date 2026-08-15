# -*- coding: utf-8 -*-
"""N-45 diagnostic 2  ---  is the empty 'last straw' band real, or a quantisation artifact?

ASOS reports temperature in whole degrees FAHRENHEIT, so tmpc lands on a grid ~0.56 C apart
(94 F = 34.44 C, 95 F = 35.00 C, 96 F = 35.56 C). A band 0.40 C wide is NARROWER than that grid
spacing, so it can contain zero achievable values even when the underlying distribution is dense
there. Reporting '0 days' without checking this would be a false precision claim.

This also sizes the alternative framing N-9 originally used (threshold 33.0 C, capacity 1.5 C),
because if the ASHRAE-allowable framing is dead, that is the next candidate and it should be
measured, not assumed. FREE, no key, no GPU.
"""
import json
import os
import statistics
import sys
from collections import Counter

from common import banner, FIXTURES

FIXTURE = os.path.join(FIXTURES, "n45_kiad_temps.json")


def main():
    banner("N-45 diag 2  quantisation check + sizing the alternative framing   [FREE]")

    d = json.load(open(FIXTURE, encoding="utf-8"))
    temps = sorted(d["target_by_date"].values())
    n = len(temps)

    print("\n   [1] Is tmpc on a whole-Fahrenheit grid?")
    fvals = [t * 9.0 / 5.0 + 32.0 for t in temps]
    frac_int = sum(1 for f in fvals if abs(f - round(f)) < 0.01) / n
    print("       %.1f %% of the %d readings are a whole number of degrees F"
          % (100.0 * frac_int, n))
    print("       -> grid spacing is 1 F = %.3f C, so any band narrower than that can be"
          % (5.0 / 9.0))
    print("          spuriously empty. A '0 days' claim on a 0.40 C band is NOT resolvable.")

    print("\n   [2] Distribution near the ASHRAE A2 Allowable limit of 35.0 C")
    print("       %-12s %8s %8s" % ("deg F", "deg C", "days"))
    cnt = Counter(round(f) for f in fvals)
    for f in range(92, 100):
        c = (f - 32.0) * 5.0 / 9.0
        print("       %-12d %8.2f %8d" % (f, c, cnt.get(f, 0)))

    print("\n   [3] Days within a given distance BELOW each candidate limit")
    print("       (a day is decision-relevant only if a remedy of that size flips the outcome)")
    print("\n       %-9s %10s %10s %10s %10s %10s"
          % ("limit C", "remedy0.25", "remedy0.40", "remedy1.00", "remedy1.50", "remedy2.00"))
    out_bands = {}
    for lim in (33.0, 35.0, 40.0):
        row, rec = [], {}
        for rem in (0.25, 0.40, 1.00, 1.50, 2.00):
            k = sum(1 for t in temps if lim - rem <= t < lim)
            row.append(k)
            rec["remedy_%.2f" % rem] = {"n_days": k, "frac": k / n}
        out_bands["limit_%.1f" % lim] = rec
        print("       %-9.1f %10s %10s %10s %10s %10s"
              % (lim, *["%d (%.1f%%)" % (k, 100.0 * k / n) for k in row]))

    print("\n   [4] Days where ambient ALONE already exceeds the limit (no remedy of any size helps,")
    print("       because these remedies are sized in single degrees, not in tens)")
    out_over = {}
    for lim in (33.0, 35.0, 40.0):
        k = sum(1 for t in temps if t >= lim)
        out_over["limit_%.1f" % lim] = {"n_days": k, "frac": k / n}
        print("       limit %.1f C : %3d days (%.1f %%)" % (lim, k, 100.0 * k / n))

    print("\n   [5] Headroom available on the hottest days -- how big must a remedy BE to matter?")
    for q, label in ((0.90, "p90"), (0.95, "p95"), (0.99, "p99"), (1.0, "max")):
        t = temps[min(int(q * (n - 1)), n - 1)]
        print("       %-4s ambient %.2f C  ->  headroom to 35.0 C = %+.2f C" % (label, t, 35.0 - t))

    res = {
        "measures": "whether the empty last-straw band is a real physical result or an artifact of "
                    "whole-Fahrenheit ASOS quantisation, and how many days each candidate remedy "
                    "size could actually flip",
        "n_days": n,
        "fahrenheit_grid_fraction": frac_int,
        "grid_spacing_c": 5.0 / 9.0,
        "band_0.40C_is_below_resolution": bool(0.40 < 5.0 / 9.0),
        "days_within_remedy_of_limit": out_bands,
        "days_ambient_alone_over_limit": out_over,
        "ambient_c": {"p90": temps[int(0.90 * (n - 1))], "p95": temps[int(0.95 * (n - 1))],
                      "p99": temps[int(0.99 * (n - 1))], "max": temps[-1],
                      "median": statistics.median(temps)},
    }
    path = os.path.join(os.path.dirname(FIXTURES), "n45_diag_quantisation.json")
    json.dump(res, open(path, "w"), indent=1)
    print("\n   written: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
