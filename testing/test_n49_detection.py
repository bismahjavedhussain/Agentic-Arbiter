# -*- coding: utf-8 -*-
"""N-49  ---  GATE: can the agent DETECT a cooling-plant fault, and is the detection AGENTIC?

Pre-registered in n49-detection-PREREG.md. P1-P4 fixed before running. FREE: existing GPU physics +
cached free NOAA ASOS. Zero API calls, no key use.

WHY THIS ESCAPES WHAT KILLED SIX CORES
    All six died of wind-direction FORECAST error (47-72 deg) against a ~40 deg plume. A diagnostic is a
    HINDCAST -- it uses OBSERVED wind, accurate to ~5 deg -- and N-46b measured the physics winning
    decisively there (+0.1045 C at 10 deg, +70 sigma). The killing error simply is not present.

THE THREE DETECTORS, and what each isolates
    A  raw threshold on measured intake        -> no FortyGuard, no solver. THE INCUMBENT.
    B  tuned single-day residual threshold     -> FortyGuard + solver, no memory. Tests whether
                                                  removing the WEATHER confound helps.
    C  sequential CUSUM on the residual        -> + state. Tests whether being SEQUENTIAL helps.

    All three calibrated to the SAME false-alarm rate on fault-free days BEFORE any speed comparison,
    because a trigger-happy detector otherwise "wins" by alarming constantly. A and B get one tuned
    constant each; C gets two, all fitted on TRAIN runs and scored on HELD-OUT runs.
"""
import json
import os
import statistics
import sys
import time

import numpy as np

from common import banner, save_result, verdict, FIXTURES
import solver
from solver import CALIBRATED
import warp_solver as ws
import test_n44_adaptive_commit as n44
from test_n46b_dirsweep import dbin_vec

# ----------------------------------------------------------------- pre-registered
FAULTS_C = [0.0, 0.10, 0.25, 0.50, 1.00]
P1_FAULT = 0.50          # the size at which "does FortyGuard help" is judged
P2_FAULT = 0.25          # the size at which "does being sequential help" is judged
MIN_SIGMA = 2.0
P3_MIN_OFF_MODAL = 0.25
P4_FAR_TOL = 0.02        # +/- 2 percentage points
TARGET_FAR = 0.05        # 5 % of fault-free runs may raise an alarm in the window

WINDOW_DAYS = 120
N_TRAIN_RUNS = 4000     # run 1 used 400; the 95th-pct estimate was too noisy to land the
N_TEST_RUNS = 2000      # 5 % FAR target out of sample (P4 failed by 0.2 pp). Same P4 condition.
OBS_DIR_ERR_DEG = 5.0    # ASOS reports direction in 10 deg increments -> ~+/-5 deg quantisation
FAULT_START_LO, FAULT_START_HI = 30, 70      # fault begins somewhere in the middle of the window
AMB = 30.0
WIND_SPEED_MS = 3.0
STEPS = 800
SEED = 49

WIND_FIX = os.path.join(FIXTURES, "n46_kiad_wind.json")
TEMP_FIX = os.path.join(FIXTURES, "n45_kiad_temps.json")


def build_table(seed=7):
    """rise(direction) table for the calibrated demo site -- same construction as N-44/N-46."""
    rng = np.random.default_rng(seed)
    site, intake = solver.demo_site()
    solver.assert_intake_clear(site, *intake, label="N-49 demo_site")
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
    print("      %d GPU solves in %.1f s" % (len(wf), time.time() - t0))
    return rise.reshape(n44.N_DIR_BINS, n44.N_MEMBERS_PER_BIN), dirs


def make_runs(table, real_dirs, real_amb, n_runs, fault_c, rng):
    """One run = WINDOW_DAYS of observed conditions with a step fault injected partway.

    Returns dict of arrays shaped (n_runs, WINDOW_DAYS):
       measured : ambient + true rise + fault      (what the customer's sensor reads)
       modelled : ensemble MEAN rise at the OBSERVED direction, plus observed ambient
       start    : the day the fault begins (or WINDOW_DAYS if fault_c == 0)
    """
    shape = (n_runs, WINDOW_DAYS)
    true_dir = rng.choice(real_dirs, size=shape, replace=True)
    amb = rng.choice(real_amb, size=shape, replace=True)

    # truth: a realised member at the TRUE bearing
    midx = rng.integers(0, table.shape[1], size=shape)
    true_rise = table[dbin_vec(true_dir), midx]

    # what we model: ensemble mean at the OBSERVED bearing (observation error only, no forecast error)
    obs_dir = true_dir + rng.normal(0.0, OBS_DIR_ERR_DEG, size=shape)
    bin_mean = table.mean(axis=1)
    modelled_rise = bin_mean[dbin_vec(obs_dir)]

    if fault_c > 0:
        start = rng.integers(FAULT_START_LO, FAULT_START_HI, size=n_runs)
        day = np.arange(WINDOW_DAYS)[None, :]
        fault = np.where(day >= start[:, None], fault_c, 0.0)
    else:
        start = np.full(n_runs, WINDOW_DAYS)
        fault = np.zeros(shape)

    measured = amb + true_rise + fault
    modelled = amb + modelled_rise          # observed ambient is known to both
    return {"measured": measured, "modelled": modelled, "residual": measured - modelled,
            "start": start, "amb": amb}


def first_cross(sig, thr):
    """Per row, the first index where sig > thr, else -1."""
    hit = sig > thr
    any_hit = hit.any(axis=1)
    idx = np.where(any_hit, hit.argmax(axis=1), -1)
    return idx


def far_of(alarm_idx):
    return float((alarm_idx >= 0).mean())


def calibrate_threshold(sig_clean, target_far):
    """Smallest threshold whose alarm rate on FAULT-FREE runs is <= target_far.
    Uses the quantile of each run's MAXIMUM, which is the exact object that controls FAR."""
    run_max = sig_clean.max(axis=1)
    q = 1.0 - target_far
    return float(np.quantile(run_max, q))


def cusum_signal(resid, k):
    """S_t = max(0, S_{t-1} + (r_t - k)). Vectorised over runs, sequential over days."""
    n, T = resid.shape
    s = np.zeros(n)
    out = np.empty((n, T))
    for t in range(T):
        s = np.maximum(0.0, s + (resid[:, t] - k))
        out[:, t] = s
    return out


def delays(alarm_idx, start, window=WINDOW_DAYS):
    """Detection delay in days. A run that never alarms is censored at the window length -- recorded
    explicitly rather than dropped, because dropping misses would flatter a slow detector."""
    d = np.where(alarm_idx >= 0, alarm_idx - start, window)
    return np.maximum(d, 0).astype(float), float((alarm_idx < 0).mean())


def paired(a, b):
    """mean(a - b) and its paired standard error. Positive = b is FASTER (lower delay)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    return float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d)))


def main():
    banner("N-49  GATE: fault detection -- is FortyGuard load-bearing, and is it agentic?  [FREE]")
    print("   Pre-registered in n49-detection-PREREG.md. A hindcast, so no forecast error: observed")
    print("   direction only (%.0f deg sd). This is what six failed cores did not have." % OBS_DIR_ERR_DEG)

    w = json.load(open(WIND_FIX, encoding="utf-8"))
    t = json.load(open(TEMP_FIX, encoding="utf-8"))
    real_dirs = np.asarray(list(w["dir_by_date"].values()), float)
    real_amb = np.asarray(list(t["target_by_date"].values()), float)
    print("\n   real inputs: %d wind directions, %d ambient temperatures (both 6 summers, KIAD)"
          % (len(real_dirs), len(real_amb)))
    print("   ambient spans %.1f-%.1f C -- that spread is what detector A must see through"
          % (real_amb.min(), real_amb.max()))

    print("\n   [1/4] GPU precompute of the rise field")
    table, dirs = build_table()
    bm = table.mean(axis=1)
    print("      rise: max %.4f C, median across bins %.4f C" % (table.ravel().max(), np.median(bm)))

    # ---- calibrate all three detectors on FAULT-FREE TRAIN runs, to the same FAR ----
    print("\n   [2/4] calibrating all three detectors to FAR = %.0f %% on fault-free TRAIN runs"
          % (100 * TARGET_FAR))
    rng = np.random.default_rng(SEED)
    clean_tr = make_runs(table, real_dirs, real_amb, N_TRAIN_RUNS, 0.0, rng)
    thr_A = calibrate_threshold(clean_tr["measured"], TARGET_FAR)
    thr_B = calibrate_threshold(clean_tr["residual"], TARGET_FAR)
    k_cusum = float(np.quantile(clean_tr["residual"], 0.75))     # slack: 75th pct of clean residual
    cus_tr = cusum_signal(clean_tr["residual"], k_cusum)
    thr_C = calibrate_threshold(cus_tr, TARGET_FAR)
    print("      A raw-intake threshold      %.4f C" % thr_A)
    print("      B residual threshold        %.4f C" % thr_B)
    print("      C CUSUM slack k=%.4f, bound h=%.4f" % (k_cusum, thr_C))

    # ---- P4: verify FAR out of sample on held-out fault-free runs ----
    clean_te = make_runs(table, real_dirs, real_amb, N_TEST_RUNS, 0.0, rng)
    far = {
        "A": far_of(first_cross(clean_te["measured"], thr_A)),
        "B": far_of(first_cross(clean_te["residual"], thr_B)),
        "C": far_of(first_cross(cusum_signal(clean_te["residual"], k_cusum), thr_C)),
    }
    print("\n   [3/4] P4  held-out false-alarm rates (target %.0f %% +/- %.0f pp)"
          % (100 * TARGET_FAR, 100 * P4_FAR_TOL))
    for kk in ("A", "B", "C"):
        print("      %s : %.1f %%" % (kk, 100 * far[kk]))
    p4 = all(abs(far[kk] - TARGET_FAR) <= P4_FAR_TOL for kk in far)
    print("      -> P4 %s" % p4)

    # ---- run each fault size ----
    print("\n   [4/4] detection delay by fault size, all detectors at matched FAR")
    print("      %-9s %11s %11s %11s   %11s %11s"
          % ("fault C", "A delay", "B delay", "C delay", "B vs A", "C vs B"))
    rows = {}
    for F in FAULTS_C:
        if F == 0.0:
            continue
        te = make_runs(table, real_dirs, real_amb, N_TEST_RUNS, F, rng)
        iA = first_cross(te["measured"], thr_A)
        iB = first_cross(te["residual"], thr_B)
        cus = cusum_signal(te["residual"], k_cusum)
        iC = first_cross(cus, thr_C)
        dA, mA = delays(iA, te["start"])
        dB, mB = delays(iB, te["start"])
        dC, mC = delays(iC, te["start"])
        gBA, seBA = paired(dA, dB)
        gCB, seCB = paired(dB, dC)
        sBA = gBA / seBA if seBA > 0 else float("inf")
        sCB = gCB / seCB if seCB > 0 else float("inf")

        fired = dC[iC >= 0]
        if len(fired):
            vals, cnts = np.unique(np.round(fired).astype(int), return_counts=True)
            off_modal = 1.0 - cnts.max() / cnts.sum()
            modal = int(vals[cnts.argmax()])
        else:
            off_modal, modal = 0.0, None

        rows[F] = {"fault_c": F,
                   "delay_A": float(dA.mean()), "delay_B": float(dB.mean()),
                   "delay_C": float(dC.mean()),
                   "miss_A": mA, "miss_B": mB, "miss_C": mC,
                   "B_vs_A_gain_days": gBA, "B_vs_A_se": seBA, "B_vs_A_sigma": sBA,
                   "C_vs_B_gain_days": gCB, "C_vs_B_se": seCB, "C_vs_B_sigma": sCB,
                   "C_off_modal_fraction": float(off_modal), "C_modal_delay": modal}
        print("      %-9.2f %11.2f %11.2f %11.2f   %+6.2f/%+5.1fs %+6.2f/%+5.1fs"
              % (F, dA.mean(), dB.mean(), dC.mean(), gBA, sBA, gCB, sCB))
        print("                (missed: A %.0f %%  B %.0f %%  C %.0f %%   C off-modal %.0f %%)"
              % (100 * mA, 100 * mB, 100 * mC, 100 * off_modal))

    r1, r2 = rows[P1_FAULT], rows[P2_FAULT]
    p1 = r1["B_vs_A_sigma"] >= MIN_SIGMA
    p2 = r2["C_vs_B_sigma"] >= MIN_SIGMA
    p3 = r2["C_off_modal_fraction"] >= P3_MIN_OFF_MODAL

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      P1 FortyGuard load-bearing: B beats A at F=%.2f by >= %.1f SE : %s (%+.2f SE, "
          "%.2f -> %.2f days)" % (P1_FAULT, MIN_SIGMA, p1, r1["B_vs_A_sigma"],
                                  r1["delay_A"], r1["delay_B"]))
    print("      P2 sequential is worth it : C beats B at F=%.2f by >= %.1f SE : %s (%+.2f SE, "
          "%.2f -> %.2f days)" % (P2_FAULT, MIN_SIGMA, p2, r2["C_vs_B_sigma"],
                                  r2["delay_B"], r2["delay_C"]))
    print("      P3 anti-threshold: C fires off its modal delay on >= %.0f %%  : %s (%.0f %%, modal "
          "day %s)" % (100 * P3_MIN_OFF_MODAL, p3, 100 * r2["C_off_modal_fraction"],
                       r2["C_modal_delay"]))
    print("      P4 false-alarm rates matched out of sample                : %s" % p4)

    ok = p1 and p2 and p3 and p4
    print()
    verdict(ok,
            "GATE PASSED - removing the weather with FortyGuard's observed ambient cuts detection "
            "delay from %.2f to %.2f days at a %.2f C fault (%+.2f SE), and accumulating evidence "
            "sequentially cuts it further from %.2f to %.2f days at %.2f C (%+.2f SE) with the "
            "declaration day genuinely varying (%.0f %% off modal) at a matched false-alarm rate. "
            "This is a diagnostic decision on OBSERVED data, so the 47-72 deg forecast error that "
            "killed six previous cores does not apply. It does NOT establish field performance: the "
            "faults are injected and there is no real sensor."
            % (r1["delay_A"], r1["delay_B"], P1_FAULT, r1["B_vs_A_sigma"],
               r2["delay_B"], r2["delay_C"], P2_FAULT, r2["C_vs_B_sigma"],
               100 * r2["C_off_modal_fraction"]),
            "GATE FAILED - P1 %s, P2 %s, P3 %s, P4 %s. If P1 failed, removing the weather confound "
            "does not speed detection and FortyGuard is not load-bearing for diagnosis either -- the "
            "pivot is dead, report it and stop. If P1 passed but P2 failed, FortyGuard IS load-bearing "
            "but a threshold on the residual suffices: a useful detector, NOT an agent, and it must be "
            "labelled that way." % (p1, p2, p3, p4))

    save_result("n49_detection.json", {
        "measures": "detection delay for an injected step fault, at matched false-alarm rate, for "
                    "three detectors isolating (A) the incumbent, (B) the value of removing weather "
                    "with FortyGuard, (C) the value of a sequential decision",
        "does_not_measure": "field performance -- faults are INJECTED and there is no real intake "
                            "sensor; a step fault is easier than real gradual fouling, so this is an "
                            "UPPER bound; one site layout; nothing in energy or money",
        "why_this_escapes_the_root_cause": "a diagnostic is a hindcast on OBSERVED wind (%.0f deg sd), "
                                          "not a forecast (47-72 deg), which is what killed N-25/40/"
                                          "43/44/45/46/48" % OBS_DIR_ERR_DEG,
        "inputs": {"n_real_dirs": len(real_dirs), "n_real_ambient": len(real_amb),
                   "ambient_span_c": [float(real_amb.min()), float(real_amb.max())],
                   "obs_dir_err_deg": OBS_DIR_ERR_DEG},
        "calibration": {"target_far": TARGET_FAR, "thr_A": thr_A, "thr_B": thr_B,
                        "cusum_k": k_cusum, "cusum_h": thr_C},
        "held_out_far": far,
        "window_days": WINDOW_DAYS, "n_train_runs": N_TRAIN_RUNS, "n_test_runs": N_TEST_RUNS,
        "by_fault": {str(k): v for k, v in rows.items()},
        "conditions": {"p1_fault_c": P1_FAULT, "p2_fault_c": P2_FAULT, "min_sigma": MIN_SIGMA,
                       "p3_min_off_modal": P3_MIN_OFF_MODAL, "p4_far_tol": P4_FAR_TOL},
        "p1": bool(p1), "p2": bool(p2), "p3": bool(p3), "p4": bool(p4), "gate_passed": bool(ok),
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
