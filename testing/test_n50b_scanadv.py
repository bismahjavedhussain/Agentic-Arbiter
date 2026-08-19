# -*- coding: utf-8 -*-
"""N-50b  ---  is N-50's win a TIMING win, or just an INFORMATION win?   FREE, GPU. Zero API calls.

WHY THIS EXISTS -- a specification defect in N-50 that I found and reported myself
    N-50's adversary (inherited from N-9/N-44) commits at ONE tuned hour or never. The DP scans all ten
    decision hours. So the DP had TEN observations against ONE, and its +13.6 to +20.6 sigma advantage
    may be an INFORMATION advantage rather than a TIMING advantage.

    The mechanism is visible in N-50's own numbers: the fixed rule's cost explodes to 965 at R = 10,000
    because on any day whose margin at its single chosen hour falls below threshold it NEVER commits and
    eats the full breach penalty. The DP simply catches those days at another hour. That is better day
    SELECTION, not better TIMING.

THE FAIR ADVERSARIES ADDED HERE -- both see all ten hours, neither computes a state-dependent boundary
    SCAN-1   commit at the FIRST hour where margin > m*, with the single constant m* tuned on TRAIN.
             This is the natural no-model stopping rule an engineer would actually write, and by the
             project's own standard a single tuned constant IS a threshold in a costume.
    SCAN-10  commit at the FIRST hour where margin > m*_t, with a SEPARATE constant per hour, tuned by
             coordinate descent on TRAIN. The strongest reasonable non-model stopping rule: ten tuned
             constants, still with no model-derived boundary.

DIRECTION OF THIS CORRECTION, stated so it cannot be mistaken for p-hacking
    Adding a STRONGER adversary can only REDUCE our measured advantage. This makes the test harder, not
    easier. Nothing here can manufacture a win that was not there.

PRE-REGISTERED, fixed before running
    P2'  The DP must beat SCAN-1 by >= 2 paired SE over a contiguous band of >= 3 adjacent R values.
    P2'' The DP must beat SCAN-10 by >= 2 paired SE over a contiguous band of >= 3 adjacent R values.
    P3'  Within the P2' band, the DP's off-modal commitment fraction must be >= 25 %.
    If P2' fails, N-50's headline was an information artifact and the timing decision is CLOSED --
    seventh and final. If P2' passes but P2'' fails, the honest statement is that timing needs at most a
    per-hour threshold schedule, which is ten constants rather than a model, and must be labelled so.
"""
import json
import statistics
import sys

import numpy as np

from common import banner, save_result, verdict
from test_n9_staging import paired
import test_n50_timing as n50

MIN_SIGMA = 2.0
MIN_BAND = 3
P3_MIN_OFF_MODAL = 0.25
CD_PASSES = 3


def scan_cost(d, q, R, thrs):
    """First-crossing scan with a per-hour threshold vector. thrs may be a scalar."""
    c_commit, c_never, bound, margin, _ = n50.day_costs(d, q, R)
    n = len(d["true_intake"])
    thr = np.broadcast_to(np.asarray(thrs, float).ravel(), (len(n50.DECISION_HOURS),))
    fire = margin > thr[None, :]
    any_fire = fire.any(axis=1)
    first = np.where(any_fire, fire.argmax(axis=1), 0)
    cost = np.where(any_fire, c_commit[np.arange(n), first], c_never)
    commits = np.where(any_fire, np.asarray(n50.DECISION_HOURS)[first], -1)
    return cost, commits


def tune_scan1(d, q, R):
    best = (None, float("inf"))
    for m in n50.MARGINS:
        c, _ = scan_cost(d, q, R, float(m))
        if c.mean() < best[1]:
            best = (float(m), c.mean())
    return best[0]


def tune_scan10(d, q, R, start):
    """Coordinate descent from the SCAN-1 optimum. Ten constants, no model-derived boundary."""
    thrs = np.full(len(n50.DECISION_HOURS), start, float)
    best = scan_cost(d, q, R, thrs)[0].mean()
    for _ in range(CD_PASSES):
        improved = False
        for i in range(len(thrs)):
            cur = thrs[i]
            for m in n50.MARGINS:
                trial = thrs.copy()
                trial[i] = float(m)
                c = scan_cost(d, q, R, trial)[0].mean()
                if c < best - 1e-12:
                    best, cur, improved = c, float(m), True
            thrs[i] = cur
        if not improved:
            break
    return thrs, best


def band_of(rows, key):
    cur, best = [], []
    for R in n50.R_GRID:
        if rows[R][key] >= MIN_SIGMA:
            cur.append(R)
            if len(cur) > len(best):
                best = list(cur)
        else:
            cur = []
    return best


def main():
    banner("N-50b  timing win or information win?  fair scan adversaries   [FREE, GPU]")
    print("   A STRONGER adversary can only reduce our advantage, so this correction cannot")
    print("   manufacture a win. N-50's adversary saw 1 hour; these see all 10.")

    dirs, amb, dir_err, amb_err = n50.load_pools()
    print("\n   [1/3] GPU precompute")
    table, dd = n50.build_table()

    print("\n   [2/3] generating days (same seeds as N-50, so this is the same population)")
    tr = n50.make_days(table, dirs, amb, dir_err, amb_err, n50.N_TRAIN, n50.SEED + 1)
    te = n50.make_days(table, dirs, amb, dir_err, amb_err, n50.N_TEST, n50.SEED + 2)
    q = n50.fit_conformal(tr)

    print("\n   [3/3] DP vs the fair adversaries, per breach penalty")
    print("      %-8s %10s %10s %10s %10s   %9s %9s %9s"
          % ("R", "fixed-1h", "SCAN-1", "SCAN-10", "DP", "vs SCAN1", "vs SCAN10", "off-mod"))
    rows = {}
    for R in n50.R_GRID:
        h, m = n50.tune_fixed(tr, q, R)
        c_fixed, _ = n50.run_fixed(te, q, R, h, m)

        m1 = tune_scan1(tr, q, R)
        c_s1, cm_s1 = scan_cost(te, q, R, m1)

        thrs10, _ = tune_scan10(tr, q, R, m1)
        c_s10, cm_s10 = scan_cost(te, q, R, thrs10)

        dp = n50.fit_dp(tr, q, R)
        c_dp, cm_dp = n50.run_dp(te, q, R, dp)

        g1, se1 = paired(c_s1, c_dp)
        g10, se10 = paired(c_s10, c_dp)
        s1 = g1 / se1 if se1 > 0 else float("inf")
        s10 = g10 / se10 if se10 > 0 else float("inf")
        om, modal, nf = n50.off_modal(cm_dp)
        om1, modal1, _ = n50.off_modal(cm_s1)

        rows[R] = {"R": R, "cost_fixed1h": float(c_fixed.mean()), "cost_scan1": float(c_s1.mean()),
                   "cost_scan10": float(c_s10.mean()), "cost_dp": float(c_dp.mean()),
                   "scan1_threshold": m1, "scan10_thresholds": thrs10.tolist(),
                   "sigma_vs_scan1": s1, "sigma_vs_scan10": s10,
                   "gain_vs_scan1": g1, "gain_vs_scan10": g10,
                   "dp_off_modal": om, "dp_modal_hour": modal, "dp_n_fired": nf,
                   "scan1_off_modal": om1, "scan1_modal_hour": modal1}
        print("      %-8.0f %10.4f %10.4f %10.4f %10.4f   %+9.2f %+9.2f %8.0f%%"
              % (R, c_fixed.mean(), c_s1.mean(), c_s10.mean(), c_dp.mean(), s1, s10, 100 * om))

    b1 = band_of(rows, "sigma_vs_scan1")
    b10 = band_of(rows, "sigma_vs_scan10")
    p2a = len(b1) >= MIN_BAND
    p2b = len(b10) >= MIN_BAND
    p3 = p2a and all(rows[R]["dp_off_modal"] >= P3_MIN_OFF_MODAL for R in b1)

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      P2'  DP beats SCAN-1  over >= %d adjacent R : %s (%s)" % (MIN_BAND, p2a, b1 or "none"))
    print("      P2'' DP beats SCAN-10 over >= %d adjacent R : %s (%s)" % (MIN_BAND, p2b, b10 or "none"))
    print("      P3'  off-modal >= %.0f%% throughout the P2' band : %s"
          % (100 * P3_MIN_OFF_MODAL, p3))
    print("\n      For reference, N-50's original one-look adversary and what it cost:")
    for R in (10.0, 1000.0, 10000.0):
        print("         R=%-6.0f fixed-1h %9.4f   SCAN-1 %9.4f   DP %9.4f"
              % (R, rows[R]["cost_fixed1h"], rows[R]["cost_scan1"], rows[R]["cost_dp"]))

    ok = p2a and p2b and p3
    print()
    verdict(ok,
            "PASS - the advantage survives a FAIR adversary. The DP beats a first-crossing scan with a "
            "tuned constant over R in %s, and beats a per-hour tuned schedule over R in %s, while "
            "genuinely varying its commitment hour. So N-50's win was a TIMING win, not merely an "
            "information win, and the timing decision is a real sequential decision."
            % (b1, b10),
            "FAIL - P2' %s, P2'' %s, P3' %s. If P2' failed, N-50's +13.6 to +20.6 sigma headline was an "
            "INFORMATION artifact: a first-crossing scan with one tuned constant matches the DP once it "
            "is allowed the same ten looks, so the timing decision is CLOSED -- seventh and final. If "
            "P2' passed but P2'' failed, timing needs at most a per-hour threshold SCHEDULE (ten "
            "constants, no model), which by this project's own standard is a threshold in a costume and "
            "must be labelled that way." % (p2a, p2b, p3))

    save_result("n50b_scanadv.json", {
        "measures": "whether N-50's DP advantage survives adversaries that see all ten decision hours",
        "does_not_measure": "FortyGuard forecast skill; field performance; anything in energy or money",
        "why": "N-50's adversary committed at ONE tuned hour or never, so the DP had 10 observations "
               "against 1. Adding stronger adversaries can only reduce our advantage.",
        "adversaries": {"SCAN-1": "first hour margin > one tuned constant",
                        "SCAN-10": "first hour margin > a per-hour tuned constant (coordinate descent)"},
        "rows": {str(k): v for k, v in rows.items()},
        "band_vs_scan1": b1, "band_vs_scan10": b10,
        "conditions": {"min_sigma": MIN_SIGMA, "min_band": MIN_BAND,
                       "p3_min_off_modal": P3_MIN_OFF_MODAL, "cd_passes": CD_PASSES},
        "p2_prime": bool(p2a), "p2_double_prime": bool(p2b), "p3_prime": bool(p3),
        "pass": bool(ok),
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
