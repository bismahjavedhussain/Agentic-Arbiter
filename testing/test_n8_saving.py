# -*- coding: utf-8 -*-
"""N-8  ---  what is the saving, honestly?   FREE, GPU.

HISTORY, because this check has been wrong three times and every error is instructive.

  v1  compared the ensemble's p90 against the same ensemble's MAX. Circular: it measured the
      width of my own Monte Carlo tail, not anything an operator does. Retracted.

  v2  compared a per-day conditional bound against the p99 of a distribution built by sampling
      wind direction UNIFORMLY over 360 degrees. Two faults:
        (a) the intake is only downwind in a ~40 degree window, so ~90 % of draws returned
            exactly 0.000 C. The p50 was zero and the "p99 design point" was an artifact of
            where the sampling window edge happened to fall.
        (b) it reported a windy-vs-calm comparison with direction UNCONTROLLED and n=4 in the
            top speed band. Confounded and underpowered. N-11 is the valid test for the
            speed dependence; it holds direction fixed and sweeps speed.
      Numbers from v2 (+0.502 C design point) are void.

  v3  fixed the baseline (worst direction, not uniform sampling) but ran on the PRE-CALIBRATION
      solver: exchange_s = 20 s and downwash exponent = 2.0, both of which N-11 asserted from a
      CFD figure I had mistaken for a measurement. N-21 falsified that configuration against
      real field data and N-22 refitted it. So v3's +0.874 C is void as well -- not because the
      method was wrong, but because the physics underneath it was.

      v3 also printed a claim it could not support: "a fixed margin is wrong in BOTH directions
      -- too generous on most, NOT ENOUGH on the aligned one." That second half is unreachable
      by construction. The baseline IS the p99 at the worst direction, so it covers the worst
      direction by definition; the saving there can approach zero but cannot go negative. The
      claim has been removed rather than rescued.

  v4  THIS FILE. Same method as v3, three changes:
        1. the N-22 CALIBRATED constants (exponent 1.25, uc 8.0 m/s, exchange_s 47.4 s), fitted
           to published field measurements from three power stations and validated held-out on
           three more
        2. moved to the Warp GPU batch solver, verified in N-16 to agree with the NumPy solver
           to 0.000247 C. This is what makes point 3 affordable
        3. MANY more members. v3 estimated a p99 from 120 samples, where the top 1 % is about
           one draw -- an estimate with no business being quoted to three decimals. v4 uses 600.

WHY WORST-DIRECTION IS THE CORRECT BASELINE, not a convenient one
    A fixed design margin has to hold on every day the plant will ever see, including the day
    the wind lines the exhaust up with the intake. That is how design conditions are actually
    set -- ASHRAE sizes to a 1 % exceedance, not to a direction-averaged mean. Averaging over
    directions would under-protect on precisely the aligned-wind days that matter, which is an
    engineering error, not a conservative choice.

    So:  NO-FORECAST BASELINE  = p99 over (speed, load) uncertainty at the WORST direction
         CONDITIONAL BOUND     = p90 given today's forecast direction, speed and load
         SAVING(direction)      = baseline - conditional(direction)

    THE CLAIM UNDER TEST, stated so it can fail: on the directions that carry the exhaust away
    from the intake, most of that fixed margin is dead weight. It is NOT that the fixed margin
    is unsafe. It is that it is paid for every hour of every day to cover a geometry that holds
    for a small fraction of them.
"""
import sys, time
import numpy as np
from solver import demo_site, intake_temperature, downwash_fraction, CALIBRATED
from common import banner, save_result, verdict
import warp_solver as ws

AMB = 30.0
DX = 10.0
STEPS = 800                # N-16: agrees with the iterated NumPy solver to 0.000247 C

CAL_UC = CALIBRATED["downwash_uc"]              # [F] fitted to field data in N-22
CAL_EXPO = CALIBRATED["downwash_exponent"]      # [F] fitted to field data in N-22
CAL_EXCHANGE_S = CALIBRATED["exchange_s"]       # [F] fitted to field data in N-22

DIRECTIONS = (0, 45, 90, 135, 180, 225, 270, 315)
N_SCAN = 40             # runs per direction when hunting for the worst one
N_BASE = 600            # runs for the baseline p99 at the worst direction
N_COND = 200            # runs per direction for the conditional bound
DESIGN_WIND = 6.0       # [S] design wind speed; swept below


def sample(site, intake, rng, n, wf_mean, wf_sd, ws_mean, ws_sd, load_lo, load_hi):
    """One batched ensemble on the GPU. Returns intake rise above ambient, per member."""
    wf = wf_mean + (rng.normal(0, wf_sd, n) if wf_sd else np.zeros(n))
    spd = np.clip(ws_mean + (rng.normal(0, ws_sd, n) if ws_sd else np.zeros(n)), 0.3, 14.0)
    scl = rng.uniform(load_lo, load_hi, n)
    dw = np.array([downwash_fraction(v, CAL_UC, CAL_EXPO) for v in spd])
    T = ws.solve_batch(site, np.full(n, AMB), spd, wf, scl, steps=STEPS, downwash=dw)
    return np.array([intake_temperature(T[k].astype(np.float64), site, *intake) - AMB
                     for k in range(n)])


def main():
    banner("N-8 v4  The honest saving on the CALIBRATED solver   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable -- v4 needs the GPU to afford 600-member baselines.")
        return 2

    t0 = time.time()
    site, intake = demo_site(dx=DX, exchange_s=CAL_EXCHANGE_S)
    rng = np.random.default_rng(11)

    print("   CALIBRATED solver [F, N-22]: downwash exponent %.2f, uc %.1f m/s, exchange_s %.1f s"
          % (CAL_EXPO, CAL_UC, CAL_EXCHANGE_S))
    print("   v3 ran at exponent 2.00 / exchange_s 20.0 s -- FALSIFIED by field data in N-21.")
    print("   site: one hall, condensers on its east face discharging 11 C above ambient;")
    print("         neighbour hall 300 m east; we score the NEIGHBOUR's west-facing intake.")

    # ---- 1. find the worst direction -------------------------------------
    print("\n   1. WHICH DIRECTION IS WORST?  %d runs each at %.0f m/s" % (N_SCAN, DESIGN_WIND))
    scan = {}
    for wf in DIRECTIONS:
        v = sample(site, intake, rng, N_SCAN, wf, 10.0, DESIGN_WIND, 0.8, 0.7, 1.0)
        scan[wf] = float(np.mean(v))
        print("      %3d deg   mean %+.4f C" % (wf, scan[wf]))
    worst = max(scan, key=lambda d: scan[d])
    n_zero = sum(1 for d in DIRECTIONS if scan[d] < 0.005)
    print("      -> worst direction: %d deg" % worst)
    print("      -> %d of %d directions return essentially nothing (< 0.005 C): direction"
          % (n_zero, len(DIRECTIONS)))
    print("         behaves as a SWITCH, not a dial. That is the whole product in one line.")

    # ---- 2. the no-forecast baseline --------------------------------------
    print("\n   2. NO-FORECAST BASELINE  (must cover the worst direction; %d runs)" % N_BASE)
    B = sample(site, intake, rng, N_BASE, worst, 20.0, DESIGN_WIND, 2.0, 0.5, 1.0)
    for q in (50, 90, 95, 99):
        print("        p%-3d %+.4f C" % (q, np.percentile(B, q)))
    print("        max  %+.4f C" % B.max())
    baseline = float(np.percentile(B, 99))
    print("      -> a fixed margin must be at least %+.4f C (p99 at the worst direction)" % baseline)

    # ---- 3. conditional bounds, per direction ----------------------------
    print("\n   3. CONDITIONAL BOUND given today's forecast  (%d runs per direction)" % N_COND)
    print("      wind FROM   cond p90   saving vs baseline   verdict")
    rows = []
    for wf in DIRECTIONS:
        C = sample(site, intake, rng, N_COND, wf, 15.0, DESIGN_WIND, 1.0, 0.65, 1.0)
        p90 = float(np.percentile(C, 90))
        sav = baseline - p90
        v = ("DO NOT RELAX - exhaust on the intake" if sav <= 0.05
             else "relax" if sav > 0.5 * baseline else "partial")
        rows.append({"wind_from": wf, "cond_p90": p90, "saving": sav, "verdict": v})
        print("        %3d deg   %+.4f C    %+.4f C          %s" % (wf, p90, sav, v))

    sav = np.array([r["saving"] for r in rows])
    n_relax = int(np.sum(sav > 0.5 * baseline))
    n_hold = int(np.sum(sav <= 0.05))
    print("\n   4. RESULT")
    print("      baseline a fixed margin must carry : %+.4f C" % baseline)
    print("      median conditional saving          : %+.4f C" % float(np.median(sav)))
    print("      best  (exhaust blown away)         : %+.4f C  = %.0f %% of the baseline"
          % (sav.max(), 100 * sav.max() / max(baseline, 1e-9)))
    print("      worst (exhaust onto the intake)    : %+.4f C" % sav.min())
    print("      directions where most of the margin can be released : %d / %d"
          % (n_relax, len(rows)))
    print("      directions where it must NOT be released            : %d / %d"
          % (n_hold, len(rows)))

    # ---- 5. what the two-sidedness actually is ---------------------------
    two_sided = sav.max() > 0.5 * baseline and sav.min() <= 0.05
    print("\n   5. THE CLAIM UNDER TEST  (v3's wording is retracted; see the docstring)")
    print("      SUPPORTED  : the fixed margin is dead weight on the directions that carry the")
    print("                   exhaust away -- up to %.0f %% of it released, on %d of %d directions."
          % (100 * sav.max() / max(baseline, 1e-9), n_relax, len(rows)))
    print("      NOT CLAIMED: that the fixed margin is unsafe on the aligned day. It cannot be.")
    print("                   The baseline is defined AS the p99 at that direction, so the")
    print("                   saving there approaches zero and cannot go negative. v3 printed")
    print("                   otherwise; that was a logical error, not a finding.")
    print("      both halves present as now defined: %s" % two_sided)

    # ---- 6. sweep the design wind speed ---------------------------------
    print("\n   6. SWEEPING THE DESIGN WIND SPEED  [S]")
    print("      %8s %12s %12s %12s" % ("m/s", "baseline", "best save", "worst save"))
    sweeps = []
    for dw in (3.0, 6.0, 9.0, 12.0):
        Bs = sample(site, intake, rng, 200, worst, 20.0, dw, 2.0, 0.5, 1.0)
        bl = float(np.percentile(Bs, 99))
        best = bl - float(np.percentile(
            sample(site, intake, rng, 100, (worst + 180) % 360, 15.0, dw, 1.0, 0.65, 1.0), 90))
        wor = bl - float(np.percentile(
            sample(site, intake, rng, 100, worst, 15.0, dw, 1.0, 0.65, 1.0), 90))
        sweeps.append({"design_wind": dw, "baseline": bl, "best_saving": best, "worst_saving": wor})
        print("      %8.1f %12.4f %12.4f %12.4f" % (dw, bl, best, wor))

    ok = two_sided and baseline > 0.2
    print("\n   elapsed %.1f s on the GPU" % (time.time() - t0))
    print()
    verdict(ok,
            "PASS - on the calibrated solver a fixed margin must carry %+.4f C to cover the worst "
            "direction, and on the directions that blow exhaust away %+.4f C of that (%.0f %%) is "
            "dead weight. Quote it as a band from N-19, never as this point value."
            % (baseline, sav.max(), 100 * sav.max() / max(baseline, 1e-9)),
            "FAIL - either the worst-direction baseline is too small to matter (%.4f C), or the "
            "margin cannot be released on any direction. Drop the dead-weight argument."
            % baseline)

    save_result("n8_saving.json", {
        "version": 4,
        "supersedes": ["v1 circular p90-vs-max",
                       "v2 uniform-direction p99 (+0.502 C), void",
                       "v3 pre-calibration solver (+0.874 C), void: exponent 2.0 / exchange_s 20 s "
                       "falsified in N-21, refitted in N-22. v3 also claimed under-protection on "
                       "the aligned direction, which is unreachable by construction. Archived at "
                       "results/n8_saving_v3_ARCHIVED.json"],
        "calibrated": {"exponent": CAL_EXPO, "uc": CAL_UC, "exchange_s": CAL_EXCHANGE_S},
        "backend": "warp GPU", "steps": STEPS,
        "n_scan": N_SCAN, "n_base": N_BASE, "n_cond": N_COND,
        "design_wind_ms": DESIGN_WIND,
        "direction_scan": scan, "worst_direction": worst,
        "n_directions_near_zero": n_zero,
        "baseline_p99": baseline,
        "baseline_quantiles": {q: float(np.percentile(B, q)) for q in (50, 90, 95, 99)},
        "by_direction": rows,
        "median_saving": float(np.median(sav)), "best_saving": float(sav.max()),
        "worst_saving": float(sav.min()),
        "best_saving_frac_of_baseline": float(sav.max() / max(baseline, 1e-9)),
        "n_relax": n_relax, "n_hold": n_hold, "two_sided": two_sided,
        "sweeps": sweeps, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
