# -*- coding: utf-8 -*-
"""DIAG-53  ---  is the 90 % bound RECOVERABLE by anchoring the LEVEL to one observation?

FREE. Reuses N-26's already-paid forecast/outcome pairs. Zero API calls, no key use.

THE CHAIN OF EVIDENCE THAT LEADS HERE
    1. N-26 live coverage FAILED: 65.6 % pooled vs a 90 % promise, worst day 0.0 %.
    2. Not our comparison -- both legs use the SAME call_window() payload.
    3. Not FortyGuard's history -- it tracks KIAD ASOS within +0.86..+1.92 C, consistent with an
       urban heat-island offset over a data-centre corridor, and smallest on the coolest day.
    4. It is the forecast LEVEL: a SPATIALLY UNIFORM, DAY-VARYING offset. Within-day sd across
       17,862 tiles is 0.06-0.29 C while the day-mean offset ran -0.84, -0.81, +0.15, -3.71 C.
    5. Shortening the lead does NOT fix it (DIAG-52): the offset is -1.02 C at 1.49 h lead versus
       -0.84 C at 9.41 h, with |offset|/sd between 7.9 and 10.0 at EVERY lead.

    So the error is one number per day, not a field. That suggests the fix: use FortyGuard's forecast
    for the SPATIAL PATTERN, which is excellent, and ANCHOR the absolute LEVEL to a single observation.
    Because the error is spatially uniform, subtracting one scalar should remove almost all of it.

WHAT IS TESTED HERE
    ANCHORED residual = (outcome - forecast) - (that day's mean offset)
    i.e. exactly what you get if ONE observation in the AOI tells you the level, and FortyGuard tells
    you the shape. Then run the identical sequential out-of-sample conformal protocol N-26 uses:
    calibrate the half-width on all EARLIER days, test coverage on the NEXT day.

    UNANCHORED is scored alongside as the control, and must reproduce N-26's failure. If it does not,
    this script is wrong and nothing here may be read.

WHAT THIS CANNOT ESTABLISH -- stated before running
    * FOUR pairs, THREE test days. Tiny. A pass is encouraging, not a guarantee.
    * Anchoring assumes ONE trustworthy in-AOI observation exists. A data centre has one (its own
      sensor); a greenfield site does not. This makes the customer's sensor a REQUIRED input, not an
      optional examiner -- that is a real change to the product's dependencies and must be stated.
    * The tiles are spatially correlated, so the effective sample is far below 17,862.
    * It does not repair the underlying forecast-vs-history level disagreement; it routes around it.
"""
import io
import json
import math
import os
import statistics
import sys

from common import banner, save_result, field_path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MANIFEST = os.path.join("results", "n26_manifest.json")
ALPHA = 0.10


def load_tiles(tag):
    p = field_path(tag + ".json")
    if not p:
        return None
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for t in d.get("map_data", {}).get("features", []):
        c = t["geometry"]["coordinates"][0]
        key = (round(sum(x[1] for x in c[:4]) / 4, 6), round(sum(x[0] for x in c[:4]) / 4, 6))
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[key] = float(v)
    return out


def halfwidth(res, alpha=ALPHA):
    """One-sided split-conformal upper half-width: k-th smallest where k = ceil((n+1)(1-alpha))."""
    r = sorted(res)
    k = math.ceil((len(r) + 1) * (1.0 - alpha))
    if k > len(r):
        return float("inf")
    return r[k - 1]


def main():
    banner("DIAG-53  is 90 % recoverable by ANCHORING the level to one observation?   [FREE]")

    m = json.load(open(MANIFEST, encoding="utf-8"))
    days = []
    for k in sorted(m["days"]):
        d = m["days"][k]
        if not (d.get("forecast_done") and d.get("outcome_done")):
            continue
        f = load_tiles(d["forecast_tag"])
        o = load_tiles(d["outcome_tag"])
        if not f or not o:
            print("   %s: fixture missing, skipped" % k)
            continue
        keys = [t for t in f if t in o]
        raw = [o[t] - f[t] for t in keys]
        mu = statistics.fmean(raw)
        days.append({"date": k, "n": len(keys), "mean": mu, "sd": statistics.stdev(raw),
                     "raw": raw, "anchored": [x - mu for x in raw]})
        print("   %s  n=%d  day-mean offset %+.4f C  within-day sd %.4f C"
              % (k, len(keys), mu, days[-1]["sd"]))

    if len(days) < 3:
        print("\n   need at least 3 complete pairs")
        return 2

    print("\n   SEQUENTIAL OUT-OF-SAMPLE COVERAGE -- identical protocol to N-26")
    print("   (calibrate the half-width on ALL earlier days, then test the NEXT day)")
    print("\n   %-12s %9s %12s %10s   %12s %10s"
          % ("test day", "cal days", "UNANCH hw", "cov", "ANCHORED hw", "cov"))
    rows = []
    for i in range(1, len(days)):
        cal = days[:i]
        te = days[i]
        hw_u = halfwidth([x for c in cal for x in c["raw"]])
        hw_a = halfwidth([x for c in cal for x in c["anchored"]])
        cov_u = sum(1 for x in te["raw"] if x <= hw_u) / len(te["raw"])
        cov_a = sum(1 for x in te["anchored"] if x <= hw_a) / len(te["anchored"])
        rows.append({"test_day": te["date"], "n_cal_days": i,
                     "halfwidth_unanchored": hw_u, "coverage_unanchored": cov_u,
                     "halfwidth_anchored": hw_a, "coverage_anchored": cov_a})
        print("   %-12s %9d %12.4f %9.1f%%   %12.4f %9.1f%%"
              % (te["date"], i, hw_u, 100 * cov_u, hw_a, 100 * cov_a))

    pooled_u = statistics.fmean(r["coverage_unanchored"] for r in rows)
    pooled_a = statistics.fmean(r["coverage_anchored"] for r in rows)
    worst_u = min(r["coverage_unanchored"] for r in rows)
    worst_a = min(r["coverage_anchored"] for r in rows)

    print("\n   RESULT")
    print("      %-28s pooled %6.1f %%   worst day %6.1f %%" % ("UNANCHORED (N-26 as shipped)",
                                                                100 * pooled_u, 100 * worst_u))
    print("      %-28s pooled %6.1f %%   worst day %6.1f %%" % ("ANCHORED to one observation",
                                                                100 * pooled_a, 100 * worst_a))
    print("      nominal target: 90.0 %")

    control_ok = pooled_u < 0.85
    print("\n      CONTROL CHECK: unanchored must reproduce N-26's failure (<85 %%) : %s"
          % ("PASS" if control_ok else "FAIL -- this script is wrong, read nothing from it"))

    if not control_ok:
        save_result("diag53_anchored.json", {"control_failed": True, "rows": rows})
        return 2

    if pooled_a >= 0.90 and worst_a >= 0.85:
        verdict = ("ANCHORING RECOVERS THE BOUND: pooled %.1f %% with worst day %.1f %% against a "
                   "90 %% target, versus %.1f %% / %.1f %% unanchored. The 90 %% claim IS defensible "
                   "-- but ONLY for the anchored architecture, which REQUIRES one trustworthy in-AOI "
                   "observation. On 3 test days, so this justifies the design, it does not prove the "
                   "rate." % (100 * pooled_a, 100 * worst_a, 100 * pooled_u, 100 * worst_u))
    elif pooled_a > pooled_u:
        verdict = ("ANCHORING HELPS BUT DOES NOT REACH 90 %%: pooled %.1f %% (worst %.1f %%) vs "
                   "%.1f %% (worst %.1f %%) unanchored. The level offset is the dominant term but not "
                   "the only one -- a residual spatial-pattern drift remains. Quote the MEASURED rate."
                   % (100 * pooled_a, 100 * worst_a, 100 * pooled_u, 100 * worst_u))
    else:
        verdict = ("ANCHORING DOES NOT HELP: pooled %.1f %% vs %.1f %% unanchored. The failure is not "
                   "explained by the level offset alone, and the diagnosis needs revisiting."
                   % (100 * pooled_a, 100 * pooled_u))
    print("\n   VERDICT: %s" % verdict)

    save_result("diag53_anchored.json", {
        "measures": "whether removing each day's spatially-uniform level offset -- i.e. anchoring the "
                    "level to one in-AOI observation -- restores out-of-sample conformal coverage",
        "does_not_measure": "the rate itself (3 test days only); and it does not repair FortyGuard's "
                            "forecast-vs-history level disagreement, it routes around it",
        "requires": "ONE trustworthy in-AOI observation. This turns the customer's own sensor from an "
                    "optional examiner into a REQUIRED input -- a real change to the dependency list",
        "alpha": ALPHA, "nominal_coverage": 1 - ALPHA,
        "day_offsets": [{"date": d["date"], "n": d["n"], "mean_offset_c": d["mean"],
                         "within_day_sd_c": d["sd"]} for d in days],
        "rows": rows,
        "pooled_unanchored": pooled_u, "worst_unanchored": worst_u,
        "pooled_anchored": pooled_a, "worst_anchored": worst_a,
        "control_reproduces_n26_failure": control_ok,
        "verdict": verdict,
    })
    print("\n   written: results/diag53_anchored.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
