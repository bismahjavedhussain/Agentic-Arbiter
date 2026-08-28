# -*- coding: utf-8 -*-
"""Write conformal_cases.json: the conformal arithmetic, answered by src/conformal.py, so that
`node verify_browser_conformal.js` can check the browser's copy against it.

WHY THIS TEST CAN DEMAND EXACT EQUALITY, WHERE THE OTHERS ASK FOR AGREEMENT.
`quantile_index` is `ceil((n+1)*(1-alpha))` and `split_conformal` is a sort plus an index. Both
languages run identical IEEE-754 operations in identical order, so the answers are not merely close,
they are the same bits -- and where that is true, a tolerance would only hide a real divergence.
The one thing that could differ is `ceil` at a boundary: `(n+1)*(1-alpha)` can land a hair above or
below a whole number depending on alpha, and whichever side it lands on decides k. So the grid below
deliberately sweeps every n around each 1/alpha boundary rather than sampling.

Three families:
  1. GRID       every (n, alpha) over a wide range -- k, the clamp flag, the ceiling, min_n.
  2. RESIDUALS  random residual arrays, including duplicates, negatives and NaN, through
                split_conformal -- the sort, the index, and the honesty fields.
  3. REAL       every bound the artefacts actually ship: the four-day level bound and all twelve
                per-lead bounds. If the browser recomputes those correctly, the panel is not
                decorating numbers, it is deriving them.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import conformal as cf                                       # noqa: E402

trace = json.load(open(os.path.join(HERE, "trace.json"), encoding="utf-8"))
rolling = json.load(open(os.path.join(HERE, "rolling.json"), encoding="utf-8"))

# ---- 1. the grid --------------------------------------------------------------------------
ALPHAS = [0.20, 0.10, 0.05, 0.02, 0.01, 0.005, 0.1234]
grid = []
for a in ALPHAS:
    boundary = int(math.ceil(1.0 / a))
    ns = sorted(set(list(range(1, 60))
                    + [boundary - 2, boundary - 1, boundary, boundary + 1, boundary + 2]
                    + [99, 100, 101, 999, 1000, 21838, 21856, 43763]))
    for n in ns:
        if n < 1:
            continue
        k, clamped = cf.quantile_index(n, a)
        grid.append({"n": n, "alpha": a, "k": int(k), "clamped": bool(clamped),
                     "ceiling": cf.attainable_coverage(n), "min_n": cf.min_n_for(a)})

# ---- 2. residual arrays -------------------------------------------------------------------
rng = np.random.default_rng(2026)
residuals = []
for i in range(300):
    n = int(rng.integers(1, 60))
    kind = i % 5
    if kind == 0:
        v = rng.normal(0, 1, n)
    elif kind == 1:
        v = rng.normal(-3.7, 0.2, n)                     # the FortyGuard offset regime
    elif kind == 2:
        v = np.round(rng.normal(0, 1, n), 1)             # heavy ties
    elif kind == 3:
        v = np.full(n, 0.5)                              # all identical
    else:
        v = rng.normal(0, 1, n)
        if n > 3:
            v[rng.integers(0, n, size=max(1, n // 4))] = np.nan   # NaN must be dropped, not sorted
    a = float(ALPHAS[i % len(ALPHAS)])
    c = cf.split_conformal(v, a)
    residuals.append({"res": [None if np.isnan(x) else float(x) for x in v], "alpha": a,
                      "q": None if math.isnan(c["q"]) else c["q"], "n": c["n"], "k": c["k"],
                      "clamped": c["clamped"], "ceiling": c["ceiling"]})

# ---- 3. the real shipped bounds ------------------------------------------------------------
real = [{"label": "day-level bound over the four measured FortyGuard offsets",
         "res": [p["mean_d"] for p in trace["cycle"]["pairs"]],
         "alpha": trace["alpha"],
         "q": trace["cycle"]["bound_day_level"]["margin"],
         "n": trace["cycle"]["bound_day_level"]["n"],
         "k": trace["cycle"]["bound_day_level"]["k"],
         "clamped": trace["cycle"]["bound_day_level"]["clamped"],
         "ceiling": trace["cycle"]["bound_day_level"]["attainable"]}]

# Every per-lead bound: the browser must reproduce k and the ceiling from the n that was SCORED,
# which is the number the panel puts in its table beside each realised coverage.
nb = rolling["configs"][0]["coverage_n_by_lead"]
for lead, n in sorted(nb.items(), key=lambda kv: int(kv[0])):
    k, clamped = cf.quantile_index(int(n), rolling["alpha"])
    real.append({"label": "per-lead bound at %s h" % lead, "res": None,
                 "alpha": rolling["alpha"], "q": None, "n": int(n), "k": int(k),
                 "clamped": bool(clamped), "ceiling": cf.attainable_coverage(int(n))})

out = os.path.join(HERE, "conformal_cases.json")
json.dump({"generated_by": "AGENTIC-ARBITER/demo/gen_conformal_cases.py",
           "grid": grid, "residuals": residuals, "real": real},
          open(out, "w", encoding="utf-8"), allow_nan=False)
print("wrote %s: %d (n, alpha) grid points, %d residual arrays, %d real shipped bounds"
      % (out, len(grid), len(residuals), len(real)))
