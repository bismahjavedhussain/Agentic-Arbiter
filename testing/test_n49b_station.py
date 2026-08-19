# -*- coding: utf-8 -*-
"""N-49b  ---  isolate FortyGuard's SPECIFIC value: 60 m hyperlocal ambient vs a station miles away.

FREE. Existing GPU physics + saved FortyGuard fields + cached ASOS. Zero API calls, no key use.

WHY THIS EXISTS -- a fairness problem in N-49 that I flagged before quoting its headline
    N-49's detector A alarms on RAW measured intake, with no outdoor reference at all. Its calibrated
    threshold landed at 37.55 C against an ambient that peaks at 37.2 C, so it can only fire when the
    weather is also extreme. That is a real predicament, but it is the WEAKEST possible incumbent.

    A competent operator would subtract a nearby airport reading. That removes most of the weather too,
    leaving only the station-vs-site error. So N-49's 79.69 -> 0.03 day result is the value of having
    ANY ambient model -- NOT the value of FortyGuard's 60 m resolution specifically.

    This test adds detector D (station-corrected) and compares it against C (FortyGuard-corrected),
    holding the sequential CUSUM machinery identical. Whatever difference remains is attributable to
    ambient ACCURACY and nothing else.

THE STATION ERROR IS MEASURED, NOT ASSUMED
    Step 1 measures |dT| between the site tile and tiles at increasing separation, directly from a
    saved 17,862-tile FortyGuard field. That fixes which part of the swept range is realistic BEFORE
    the comparison is scored, so the choice cannot be made after seeing the answer.

    Modelling note: the station error is applied as DAY-VARYING noise, not a constant bias. A constant
    bias would be calibrated away by any operator setting a baseline, so including one would flatter us.
    Day-to-day divergence between site and station is the part that cannot be calibrated out.

PRE-REGISTERED, fixed before running
    P5  At the MEASURED station-error magnitude, detector C (FortyGuard) must beat detector D (station)
        by >= 2 paired SE in mean detection delay at F = 0.25 C, at matched false-alarm rate.
    P6  The FAR of C and D must both lie within +/-2 pp of the 5 % target on held-out fault-free runs,
        else the speed comparison is void -- same condition as N-49's P4.
    Also reported: the station-error magnitude at which C's advantage disappears (the crossover), which
    is a REQUIREMENT statement rather than a performance claim.

    If P5 FAILS, the honest conclusion is that a cheap airport feed is as good as FortyGuard for this
    application, and the FortyGuard-specific claim must be dropped even though the detector still works.
"""
import json
import math
import os
import statistics
import sys

import numpy as np

from common import banner, hav, load_field, save_result, verdict, FIXTURES
import test_n49_detection as n49

MIN_SIGMA = 2.0
P6_FAR_TOL = 0.02
TARGET_FAR = 0.05
P5_FAULT = 0.25
STATION_SDS = [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5]
SEED = 491


def measure_station_error():
    """Median |dT| between the AOI centre tile and tiles at increasing separation, from a saved field.

    This is the real spatial divergence of FortyGuard's own field, so it bounds how wrong a reading
    taken some kilometres away is. KIAD sits ~8 km from the site centre, which is OUTSIDE the 8x8 km
    AOI, so the largest separation measurable here (~4-5 km) is a LOWER BOUND on the station error.
    """
    print("\n   [1/3] MEASURING the station-vs-site divergence from a saved FortyGuard field")
    out = {}
    for key in ("DC_2026-07-28", "DC_2026-06-23"):
        tiles = load_field(key)
        if not tiles:
            print("      %s unavailable" % key)
            continue
        lats = [t[0] for t in tiles]
        lons = [t[1] for t in tiles]
        clat, clon = statistics.fmean(lats), statistics.fmean(lons)
        # centre tile temperature
        best = min(tiles, key=lambda t: hav((clat, clon), (t[0], t[1])))
        t0 = best[2].get("max_temperature")
        bins = {}
        for la, lo, pr in tiles:
            v = pr.get("max_temperature")
            if v is None or t0 is None:
                continue
            d = hav((clat, clon), (la, lo)) / 1000.0
            b = int(d)                      # 1 km bins
            bins.setdefault(b, []).append(abs(v - t0))
        rows = {}
        print("      %s -- median |dT| from the centre tile:" % key)
        for b in sorted(bins):
            if len(bins[b]) < 20 or b == 0:
                continue
            m = statistics.median(bins[b])
            rows[b] = {"n": len(bins[b]), "median_abs_dt_c": m}
            print("         %d-%d km : n=%5d   median |dT| %.3f C" % (b, b + 1, len(bins[b]), m))
        out[key] = rows
    return out


def cusum_delays(resid_clean_tr, resid_te, start_te, target_far):
    """Calibrate a CUSUM on fault-free TRAIN residuals, then measure delay on TEST residuals."""
    k = float(np.quantile(resid_clean_tr, 0.75))
    h = n49.calibrate_threshold(n49.cusum_signal(resid_clean_tr, k), target_far)
    idx = n49.first_cross(n49.cusum_signal(resid_te, k), h)
    d, miss = n49.delays(idx, start_te)
    return d, miss, k, h, idx


def main():
    banner("N-49b  is FortyGuard's 60 m ambient better than an airport reading?   [FREE]")
    print("   Isolates ambient ACCURACY: detector C (FortyGuard) vs D (station), identical CUSUM.")

    station_meas = measure_station_error()

    # pick the measured magnitude: the largest well-populated separation bin available
    cand = []
    for key, rows in station_meas.items():
        for b, r in rows.items():
            cand.append((b, r["median_abs_dt_c"]))
    if cand:
        far_bin = max(b for b, _ in cand)
        measured_sd = statistics.fmean([v for b, v in cand if b == far_bin])
        print("\n      -> MEASURED divergence at the largest resolvable separation (%d-%d km): "
              "%.3f C" % (far_bin, far_bin + 1, measured_sd))
        print("         KIAD is ~8 km away, outside this AOI, so this is a LOWER BOUND on the real")
        print("         station error. P5 is judged at this lower bound, which is the conservative")
        print("         choice: it makes FortyGuard's advantage HARDER to demonstrate, not easier.")
    else:
        measured_sd = 0.3
        print("\n      -> could not measure; falling back to 0.300 C and flagging it as unmeasured")

    w = json.load(open(n49.WIND_FIX, encoding="utf-8"))
    t = json.load(open(n49.TEMP_FIX, encoding="utf-8"))
    real_dirs = np.asarray(list(w["dir_by_date"].values()), float)
    real_amb = np.asarray(list(t["target_by_date"].values()), float)

    print("\n   [2/3] GPU precompute + calibration")
    table, dirs = n49.build_table()

    rng = np.random.default_rng(SEED)
    clean_tr = n49.make_runs(table, real_dirs, real_amb, n49.N_TRAIN_RUNS, 0.0, rng)
    clean_te = n49.make_runs(table, real_dirs, real_amb, n49.N_TEST_RUNS, 0.0, rng)
    fault_te = n49.make_runs(table, real_dirs, real_amb, n49.N_TEST_RUNS, P5_FAULT, rng)

    # detector C: FortyGuard-corrected residual, sequential
    dC, missC, kC, hC, iC = cusum_delays(clean_tr["residual"], fault_te["residual"],
                                         fault_te["start"], TARGET_FAR)
    farC = n49.far_of(cusum_delays(clean_tr["residual"], clean_te["residual"],
                                   clean_te["start"], TARGET_FAR)[4])

    print("\n   [3/3] detector D at each station-error magnitude, identical CUSUM machinery")
    print("      %-13s %11s %11s %10s %9s %9s"
          % ("station sd", "C delay", "D delay", "C vs D", "sigma", "D FAR"))
    rows = {}
    for s in STATION_SDS:
        r_tr = clean_tr["residual"] + rng.normal(0.0, s, clean_tr["residual"].shape)
        r_cl = clean_te["residual"] + rng.normal(0.0, s, clean_te["residual"].shape)
        r_ft = fault_te["residual"] + rng.normal(0.0, s, fault_te["residual"].shape)
        dD, missD, kD, hD, iD = cusum_delays(r_tr, r_ft, fault_te["start"], TARGET_FAR)
        farD = n49.far_of(cusum_delays(r_tr, r_cl, clean_te["start"], TARGET_FAR)[4])
        g, se = n49.paired(dD, dC)          # positive = C faster
        sig = g / se if se > 0 else float("inf")
        rows[s] = {"station_sd_c": s, "delay_C": float(dC.mean()), "delay_D": float(dD.mean()),
                   "miss_D": missD, "gain_days": g, "se": se, "sigma": sig, "far_D": farD,
                   "cusum_k": kD, "cusum_h": hD}
        print("      %-13.2f %11.2f %11.2f %+10.2f %+9.2f %8.1f %%"
              % (s, dC.mean(), dD.mean(), g, sig, 100 * farD))

    # P5 judged at the measured magnitude: nearest swept value at or below it (conservative)
    elig = [s for s in STATION_SDS if s <= measured_sd + 1e-9 and s > 0]
    judge_sd = max(elig) if elig else min(s for s in STATION_SDS if s > 0)
    r5 = rows[judge_sd]
    p5 = r5["sigma"] >= MIN_SIGMA
    p6 = (abs(farC - TARGET_FAR) <= P6_FAR_TOL and abs(r5["far_D"] - TARGET_FAR) <= P6_FAR_TOL)
    crossover = None
    for s in sorted(STATION_SDS):
        if s > 0 and rows[s]["sigma"] >= MIN_SIGMA:
            crossover = s
            break

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      measured station divergence (lower bound) : %.3f C -> P5 judged at swept %.2f C"
          % (measured_sd, judge_sd))
    print("      P5 C beats D at F=%.2f by >= %.1f SE      : %s (%+.2f SE, D %.2f -> C %.2f days)"
          % (P5_FAULT, MIN_SIGMA, p5, r5["sigma"], r5["delay_D"], r5["delay_C"]))
    print("      P6 FARs matched (C %.1f %%, D %.1f %%)       : %s"
          % (100 * farC, 100 * r5["far_D"], p6))
    print("      smallest station error at which FortyGuard already wins by >= 2 SE : %s C"
          % crossover)

    ok = p5 and p6
    print()
    verdict(ok,
            "PASS - FortyGuard's 60 m ambient is measurably better than a station reading for this "
            "diagnostic: at a station divergence of %.2f C (a LOWER bound on the ~8 km KIAD "
            "separation, measured from FortyGuard's own field) the sequential detector reaches a "
            "fault in %.2f days on FortyGuard ambient versus %.2f days on station ambient (%+.2f SE), "
            "at matched false-alarm rate and with identical CUSUM machinery. The FortyGuard-specific "
            "claim is therefore supported, not just the generic have-an-ambient-model claim."
            % (judge_sd, r5["delay_C"], r5["delay_D"], r5["sigma"]),
            "FAIL - P5 %s, P6 %s. If P5 failed, a cheap airport feed is as good as FortyGuard for "
            "this application at the measured separation: the detector still works and detector A is "
            "still hopeless, but the FORTYGUARD-SPECIFIC claim must be dropped and the pitch must say "
            "'any accurate ambient reference', not 'FortyGuard'. Report it that way."
            % (p5, p6))

    save_result("n49b_station.json", {
        "measures": "whether FortyGuard's 60 m ambient beats a station reading for fault detection, "
                    "holding the sequential CUSUM machinery identical -- isolating ambient ACCURACY",
        "does_not_measure": "field performance (faults are injected, no real sensor); gradual faults; "
                            "and it uses a LOWER BOUND on the station error, so the real advantage is "
                            "likely larger than measured here",
        "why": "N-49's detector A had no outdoor reference at all, the weakest incumbent. This adds the "
               "realistic incumbent: intake minus a nearby airport reading.",
        "station_error_measured_from_field": station_meas,
        "station_sd_used_for_p5": judge_sd,
        "station_sd_measured_lower_bound": measured_sd,
        "kiad_separation_note": "KIAD ~8 km from the AOI centre, outside the 8x8 km box, so the "
                                "largest measurable separation understates the true station error",
        "fault_c": P5_FAULT,
        "detector_C": {"cusum_k": kC, "cusum_h": hC, "far": farC, "delay": float(dC.mean()),
                       "miss": missC},
        "by_station_sd": {str(k): v for k, v in rows.items()},
        "crossover_station_sd_c": crossover,
        "conditions": {"min_sigma": MIN_SIGMA, "p6_far_tol": P6_FAR_TOL, "target_far": TARGET_FAR},
        "p5": bool(p5), "p6": bool(p6), "pass": bool(ok),
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
