# -*- coding: utf-8 -*-
"""N-48  ---  does the MARGIN SAVING scale with facility size?   FREE, GPU. Zero API calls.

THE QUESTION, and why it is the one that decides whether the product is marginal
    N-46/N-46b measured the margin saving at ONE geometry -- solver.demo_site(), a 60 x 120 m
    condenser bank -- and got 0.05-0.15 C at plausible forecast quality. That is ~1-4 % of the total
    margin an operator holds, which is too small to sell.

    But N-28 (already paid for, read at zero cost) shows the worst-direction rise varies 26x across
    six layouts: 0.179-0.707 C at L3 up to 1.201-4.753 C at L6. And L6's cause is specific and
    measurable: its condenser bank is 160 x 200 m against demo_site's 60 x 120 m -- 4.4x the source
    area, i.e. a bigger COOLING LOAD, not a tighter layout.

    So: is the benefit small because the physics is small, or small because demo_site is a small
    facility? If it scales with load, the product has a named segment -- large campuses -- instead of
    being marginal everywhere. That is the difference between a product and a curiosity.

WHAT IS HELD FIXED
    Everything except the site geometry. Same conformal construction, same tuned-constant adversary,
    same real KIAD wind (449 target-hour days, 6 summers), same leads, same paired scoring, same
    vectorised day generation imported from test_n46b_dirsweep. ONLY solver geometry changes, so any
    difference is attributable to facility size.

PRE-REGISTERED CONDITIONS -- fixed before this was run
    P1  SCALING. The absolute saving at 25 deg direction error must be at least 3x demo_site's
        0.0339 C, i.e. >= 0.1017 C. Below that the benefit does not meaningfully scale with load and
        the product is marginal at every facility size.
    P2  MATERIALITY. The absolute saving at 25 deg must be >= 0.50 C. Justification fixed in advance:
        half a degree is the smallest chiller-setpoint change an operator would plausibly act on, and
        anything less is inside the noise of their own instrumentation (ASHRAE monitoring guidance
        cites +/-0.5 C sensor accuracy). P1 can pass while P2 fails -- that would mean the effect
        scales but still does not reach a level worth acting on.
    P3  NO SAFETY SOLD. Agent held-out coverage >= fixed coverage, and both >= 88 %.
    P4  THE REQUIREMENT MUST NOT GET WORSE. The crossover direction-error sd at which the agent still
        wins by >= 2 SE must be >= 40 deg, matching N-46b. If a bigger facility needs a BETTER wind
        forecast, that is a finding against the product and must be reported as one.

    N-48 PASSES only if P1 AND P3 AND P4 hold. P2 is reported separately as the materiality verdict,
    because "it scales" and "it is worth money" are different claims and conflating them is how
    unsourced numbers get quoted.

WHAT THIS CANNOT ESTABLISH -- stated before running
    * The physics magnitude was validated against field data on a ~0.923 K signal (RMS 0.126 K, 14 %).
      L6 reaches ~4.75 C, which is roughly 5x OUTSIDE the validated magnitude range. The SCALING is a
      model extrapolation, not a measured fact, and must be labelled that way wherever it is quoted.
    * Still one wind station, persistence error, simulated days on real physics.
    * Nothing in energy or money: the C -> kWh conversion remains unsourced.
"""
import json
import os
import statistics
import sys
import time

import numpy as np

from common import banner, save_result, verdict
import solver
from solver import CALIBRATED
import warp_solver as ws
import test_n44_adaptive_commit as n44
from test_n46_margin import conformal_constant, ALPHA, WIND_FIXTURE
from test_n46b_dirsweep import make_days_vec, evaluate, TARGET_SDS
from test_n28_layouts import layout_wide_far, layout_east, BASE as N28_BASE

HEADLINE_LEAD = 9
N_TRAIN = 20000
N_TEST = 20000
SEED = 48
AMB = 30.0
WIND_SPEED_MS = 3.0
STEPS = 800

# pre-registered
P1_MIN_SAVING_C = 0.1017      # 3x demo_site's 0.0339 C at 25 deg
P2_MATERIAL_C = 0.50
P3_MIN_COVERAGE = 0.88
P4_MIN_CROSSOVER_DEG = 40.0
REF_25DEG_DEMO_SITE = 0.0339  # N-46b measured value at demo_site, for the comparison


def build_table(site, intake, label, seed=7):
    """rise(direction) table for an ARBITRARY site. Mirrors n44.build_direction_table exactly except
    that the site is a parameter -- so any difference in the result is geometry, not method."""
    rng = np.random.default_rng(seed)
    solver.assert_intake_clear(site, *intake, label=label)
    dirs = np.arange(0.0, 360.0, 360.0 / n44.N_DIR_BINS)
    wf = np.repeat(dirs, n44.N_MEMBERS_PER_BIN)
    spd = np.clip(rng.normal(WIND_SPEED_MS, 1.0, len(wf)), 0.3, 14.0)
    scl = np.maximum(0.1, rng.normal(1.0, 2.0 / 11.0, len(wf)))
    dw = np.array([solver.downwash_fraction(v, CALIBRATED["downwash_uc"],
                                            CALIBRATED["downwash_exponent"]) for v in spd])
    t0 = time.time()
    T = ws.solve_batch(site, np.full(len(wf), AMB), spd, wf, scl, steps=STEPS,
                       device="cuda", downwash=dw)
    rise = np.array([solver.intake_temperature(T[m].astype(np.float64), site, *intake) - AMB
                     for m in range(len(wf))])
    print("      %s: %d solves in %.1f s" % (label, len(wf), time.time() - t0))
    return rise.reshape(n44.N_DIR_BINS, n44.N_MEMBERS_PER_BIN), dirs


def sweep(table, base_pool, real_dirs, label):
    """Same sweep as N-46b: scale the empirical error pool, report saving vs error magnitude."""
    base_sd = float(base_pool.std(ddof=1))
    rows = []
    for tgt in TARGET_SDS:
        k = 1.0 if tgt is None else (tgt / base_sd if base_sd > 0 else 0.0)
        pool = base_pool * k
        rng = np.random.default_rng(SEED + 11)
        tr = make_days_vec(table, pool, real_dirs, N_TRAIN, rng)
        te = make_days_vec(table, pool, real_dirs, N_TEST, rng)
        r = evaluate(tr, te)
        r.update({"target_sd_deg": tgt, "effective_sd_deg": float(pool.std(ddof=1)), "k": k})
        rows.append(r)
    return rows


def crossover(rows, min_sigma=2.0):
    w = [r["effective_sd_deg"] for r in rows if r["sigma"] >= min_sigma]
    return max(w) if w else None


def at_target(rows, tgt):
    for r in rows:
        if r["target_sd_deg"] == tgt:
            return r
    return None


def main():
    banner("N-48  does the margin saving scale with FACILITY SIZE?   [FREE, GPU]")
    print("   Only the site geometry changes. Same conformal construction, same tuned adversary,")
    print("   same real KIAD wind, same leads. Any difference is attributable to facility size.")

    d = json.load(open(WIND_FIXTURE, encoding="utf-8"))
    err_pool = {int(k): np.asarray(v, float) for k, v in d["errors"].items()}
    real_dirs = np.asarray(list(d["dir_by_date"].values()), float)
    base_pool = err_pool[HEADLINE_LEAD]
    print("\n   wind: %d target-hour days, direction error sd %.2f deg at lead %d h"
          % (len(real_dirs), base_pool.std(ddof=1), HEADLINE_LEAD))

    cfg = dict(N28_BASE)
    sites = {
        "demo_site (60x120 m bank)": solver.demo_site(),
        "L6 wide_far (160x200 m bank)": layout_wide_far(cfg),
    }

    print("\n   [1/3] GPU precompute of the rise field at each geometry")
    tables, stats = {}, {}
    for label, (site, intake) in sites.items():
        tbl, dirs = build_table(site, intake, label)
        p90 = np.percentile(tbl, 90, axis=1)
        allr = tbl.ravel()
        stats[label] = {
            "max_rise_c": float(allr.max()), "median_rise_c": float(np.median(allr)),
            "p90_peak_c": float(p90.max()), "p90_peak_dir_deg": float(dirs[int(np.argmax(p90))]),
            "median_p90_across_bins_c": float(np.median(p90)),
            "frac_bins_zero_p90": float((p90 <= 1e-9).mean()),
        }
        tables[label] = tbl
        s = stats[label]
        print("      max rise %.4f C   p90 peak %.4f C at %.0f deg   median p90 across bins %.4f C"
              % (s["max_rise_c"], s["p90_peak_c"], s["p90_peak_dir_deg"],
                 s["median_p90_across_bins_c"]))

    print("\n   [2/3] margin comparison across direction-error magnitude, per geometry")
    results = {}
    for label in sites:
        print("\n      --- %s ---" % label)
        print("      %-12s %10s %10s %11s %9s %9s"
              % ("error sd", "fixed C", "agent C", "saved C", "sigma", "cov agent"))
        rows = sweep(tables[label], base_pool, real_dirs, label)
        results[label] = rows
        for r in rows:
            print("      %-12s %10.4f %10.4f %+11.4f %+9.2f %8.1f %%"
                  % ("as measured" if r["target_sd_deg"] is None else "%.0f deg" % r["target_sd_deg"],
                     r["mean_margin_fixed_c"], r["mean_margin_agent_c"], r["margin_saved_c"],
                     r["sigma"], 100 * r["coverage_agent"]))

    print("\n   [3/3] VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    L6 = "L6 wide_far (160x200 m bank)"
    DS = "demo_site (60x120 m bank)"
    r25_l6 = at_target(results[L6], 25.0)
    r25_ds = at_target(results[DS], 25.0)
    x_l6 = crossover(results[L6])
    x_ds = crossover(results[DS])

    scale_ratio = (r25_l6["margin_saved_c"] / r25_ds["margin_saved_c"]
                   if r25_ds and r25_ds["margin_saved_c"] > 0 else None)

    p1 = r25_l6["margin_saved_c"] >= P1_MIN_SAVING_C
    p2 = r25_l6["margin_saved_c"] >= P2_MATERIAL_C
    p3 = (r25_l6["coverage_agent"] >= r25_l6["coverage_fixed"]
          and min(r25_l6["coverage_agent"], r25_l6["coverage_fixed"]) >= P3_MIN_COVERAGE)
    p4 = (x_l6 is not None) and x_l6 >= P4_MIN_CROSSOVER_DEG

    print("      rise magnitude    demo_site max %.4f C  ->  L6 max %.4f C   (%.2fx)"
          % (stats[DS]["max_rise_c"], stats[L6]["max_rise_c"],
             stats[L6]["max_rise_c"] / max(stats[DS]["max_rise_c"], 1e-9)))
    print("      saving at 25 deg  demo_site %+.4f C  ->  L6 %+.4f C   (%s)"
          % (r25_ds["margin_saved_c"], r25_l6["margin_saved_c"],
             ("%.2fx" % scale_ratio) if scale_ratio else "n/a"))
    print("      P1 scaling   saving at 25 deg >= %.4f C : %s (%+.4f)"
          % (P1_MIN_SAVING_C, p1, r25_l6["margin_saved_c"]))
    print("      P3 no safety sold                       : %s (agent %.1f %% vs fixed %.1f %%)"
          % (p3, 100 * r25_l6["coverage_agent"], 100 * r25_l6["coverage_fixed"]))
    print("      P4 crossover >= %.0f deg                  : %s (L6 %s deg, demo_site %s deg)"
          % (P4_MIN_CROSSOVER_DEG, p4, x_l6, x_ds))
    print("      -- materiality, reported separately --")
    print("      P2 saving at 25 deg >= %.2f C           : %s (%+.4f)"
          % (P2_MATERIAL_C, p2, r25_l6["margin_saved_c"]))

    ok = p1 and p3 and p4
    print()
    verdict(ok,
            "PASS - the margin saving SCALES with facility size: %.4f C at demo_site's 60x120 m bank "
            "-> %.4f C at L6's 160x200 m bank (%s), at 25 deg direction error, with coverage preserved "
            "and the wind-forecast requirement no worse (%s deg). The benefit was small because the "
            "test facility was small. MATERIALITY (P2, >= 0.50 C) is %s. NOTE: L6's magnitude is ~5x "
            "outside the range the physics was validated against, so the SCALING is a model "
            "extrapolation and must be labelled as one."
            % (r25_ds["margin_saved_c"], r25_l6["margin_saved_c"],
               ("%.2fx" % scale_ratio) if scale_ratio else "n/a", x_l6,
               "REACHED" if p2 else "NOT reached"),
            "FAIL - the saving does not scale usefully with facility size (P1 %s, P3 %s, P4 %s). If P1 "
            "failed, the benefit is small at every facility size and the margin product is marginal "
            "everywhere -- report that plainly. If P4 failed, a larger facility needs a BETTER wind "
            "forecast, which is a finding against the product." % (p1, p3, p4))

    save_result("n48_geometry_scale.json", {
        "measures": "whether the margin saving scales with facility size (condenser bank area), "
                    "holding the conformal construction, adversary, wind data and leads fixed",
        "does_not_measure": "anything in energy or money (C->kWh unsourced); day-to-day behaviour; "
                            "and NOTE the physics was validated on a ~0.923 K signal so L6's ~4.75 C "
                            "is a model EXTRAPOLATION about 5x outside the validated range",
        "geometry_source": "test_n28_layouts.layout_wide_far vs solver.demo_site",
        "bank_area_note": "demo_site 60x120 m = 7,200 m2; L6 160x200 m = 32,000 m2 (4.4x)",
        "headline_lead_h": HEADLINE_LEAD, "n_train": N_TRAIN, "n_test": N_TEST,
        "rise_stats": stats,
        "saving_at_25deg": {"demo_site": r25_ds, "L6": r25_l6, "scale_ratio": scale_ratio},
        "crossover_deg": {"demo_site": x_ds, "L6": x_l6},
        "rows": {k: v for k, v in results.items()},
        "conditions": {"p1_min_saving_c": P1_MIN_SAVING_C, "p2_material_c": P2_MATERIAL_C,
                       "p3_min_coverage": P3_MIN_COVERAGE,
                       "p4_min_crossover_deg": P4_MIN_CROSSOVER_DEG,
                       "ref_25deg_demo_site": REF_25DEG_DEMO_SITE},
        "p1_scaling": bool(p1), "p2_materiality": bool(p2), "p3_coverage": bool(p3),
        "p4_requirement": bool(p4), "pass": bool(ok),
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
