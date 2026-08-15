# -*- coding: utf-8 -*-
"""N-24  ---  WHERE ARE THE LINES?  Breakevens for the two unmeasured quantities.   FREE.

WHY THIS TEST EXISTS
    Two entries in the open-risk register gate the entire agency claim, and both are quantities
    nobody has measured yet:

      RISK 1  Does the FortyGuard forecast get sharper as the target hour approaches?
              The stopping rule's whole reason to exist is that waiting buys information. N-9
              found that at the pessimistic extreme -- forecasts that never sharpen at all --
              the rule LOSES to a tuned fixed-hour rule by -0.204 cost units per day. So this
              is not a small risk. It is the risk.

      RISK 2  How uncertain is the hour the daily peak lands on?
              Measured at 1.49 h from five days of FortyGuard history, but drop one of those
              five days and it is 0.000 h. At 0.000 h the problem degenerates into a race to a
              known wall, which is exactly the flaw that made N-9 v1 fail: "wait until the last
              useful hour" becomes optimal by construction and the backward induction earns
              nothing.

    An open risk stated as "unmeasured, might be fatal" is nearly useless. The same risk stated
    as "unmeasured, and here is the exact value it has to clear" is a pre-registered experiment
    with a number attached. That is the entire purpose of this file: convert both risks from
    adjectives into thresholds BEFORE the live key is available on 18 Aug, so that day one either
    confirms or kills the claim and cannot be argued either way after the fact.

WHAT IS MEASURED
    The identical harness as N-9 -- imported, not reimplemented, so the adversary is the same
    code. At each sweep point:
      * the adversary is the BEST fixed-hour rule, with hour AND margin tuned exhaustively on
        20,000 TRAINING days
      * the stopping rule has zero tunable parameters; it sees only the cost constants
      * both are scored on 20,000 HELD-OUT days, and the gain is PAIRED per day
    The bias therefore runs against the stopping rule at every point, which is the direction a
    claim of agency needs it to run.

HOW THE SHARPENING RATE IS EXPRESSED SO IT CAN ACTUALLY BE MEASURED
    Internally the model is sigma(lead) = sigma_12h * (lead / 12) ** e. The exponent e is not
    something you can go and observe. The ratio

        rho = sigma(3 h lead) / sigma(12 h lead) = 0.25 ** e

    IS. It is one number: issue a forecast for a target hour 12 hours out, issue another for the
    same target hour 3 hours out, wait for the hour to happen, and compare the spread of the two
    error distributions. 3 h is chosen because it is the plant's lead time in this problem, so
    rho is literally "how much sharper is the forecast at the moment the decision stops mattering
    than it was at the start of the day". Every exponent below is reported as rho too, and rho is
    what goes on the day-one sheet.

        rho = 1.00  the forecast never improves       (e = 0.00)
        rho = 0.71  a quarter of the error removed     (e = 0.25)
        rho = 0.50  half the error removed             (e = 0.50, the random-walk value)
        rho = 0.25  three quarters removed             (e = 1.00)

PASS CONDITIONS, FIXED BEFORE THE SWEEPS WERE RUN
    P1  each gain curve is MONOTONE in the expected direction (Spearman rank correlation > 0.8):
        more sharpening should help the rule, and more peak-hour uncertainty should help it.
        A non-monotone or noisy curve means no threshold can be stated and the test has failed
        at its own purpose, whatever the individual numbers say.
    P2  a finite breakeven exists inside the swept range for each quantity, or the rule wins
        across the whole range (in which case that risk is retired outright).
    P3  the MEASURED peak-hour uncertainty, 1.49 h, sits on the winning side by more than two
        paired standard errors. If it does not, the agency claim is already dead and no day-one
        measurement is needed to kill it.

    Note P3 deliberately has no counterpart for the sharpening rate. Nothing has been measured
    there yet, so there is nothing to check it against -- which is the point.
"""
import sys, time
import numpy as np

from common import banner, save_result, verdict
from staging import Spec, conformal_halfwidth, sigma_schedule
import test_n9_staging as n9

N_TRAIN = 20000
N_TEST = 20000
MEASURED_PEAK_SD_H = 1.49        # [M] N-12c, from 5 days of FortyGuard history
LEAD_FOR_RHO = 3                 # the plant lead time in BASE; rho is defined at this lead

EXPONENTS = np.round(np.arange(0.0, 1.001, 0.05), 3)
PEAK_SDS = np.round(np.arange(0.0, 3.001, 0.10), 3)
GRID_E = (0.0, 0.15, 0.30, 0.50, 0.75)
GRID_S = (0.25, 0.75, 1.49, 2.50, 4.00)


_SD_FOR_RHO = [None]             # set once from the measured calibration in main()


def rho_of(e):
    """The measurable sharpening ratio sigma(3 h) / sigma(12 h) implied by exponent e.

    Computed from sigma_schedule itself rather than as the analytic (3/12)**e, because the
    schedule carries a 0.05 C floor on sigma. With the measured 12 h sd of 0.150 C that floor
    starts to bind at exponent 0.794, above which sigma(3 h) stops falling and the effective
    ratio saturates at 0.333 no matter how large the exponent gets. The analytic form would
    print rho = 0.250 at exponent 1.0, which is not a number anyone could ever measure. Both
    breakevens found below sit at exponents near 0.13-0.19, far under the binding point, so the
    reported thresholds are unaffected -- but the top of the table would have been wrong.
    """
    sd = _SD_FOR_RHO[0]
    if sd is None:
        return (LEAD_FOR_RHO / float(n9.ANCHOR_LEAD)) ** float(e)
    s = sigma_schedule(n9.ANCHOR_LEAD, sd, n9.ANCHOR_LEAD, exponent=float(e))
    return float(s[LEAD_FOR_RHO] / s[n9.ANCHOR_LEAD])


def spearman(x, y):
    """Rank correlation without a scipy dependency."""
    def rank(v):
        order = np.argsort(np.asarray(v, dtype=np.float64))
        r = np.empty(len(v), dtype=np.float64)
        r[order] = np.arange(len(v), dtype=np.float64)
        return r
    rx, ry = rank(x), rank(y)
    rx -= rx.mean(); ry -= ry.mean()
    d = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / d) if d > 0 else 0.0


def cross(xs, gains, ses, k=0.0):
    """First x where gain exceeds k * se, linearly interpolated. None if it never does."""
    xs, gains, ses = np.asarray(xs), np.asarray(gains), np.asarray(ses)
    tgt = k * ses
    above = gains > tgt
    if above.all():
        return float(xs[0]), True          # wins everywhere in range
    if not above.any():
        return None, False
    i = int(np.argmax(above))              # first True
    if i == 0:
        return float(xs[0]), True
    y0, y1 = gains[i - 1] - tgt[i - 1], gains[i] - tgt[i]
    if y1 == y0:
        return float(xs[i]), False
    return float(xs[i - 1] + (xs[i] - xs[i - 1]) * (-y0) / (y1 - y0)), False


def evaluate_point(bias, sd, hw, exponent, peak_sd_h):
    """One (sharpening, peak-hour-uncertainty) point. Returns (gain, se, dp_cost, adv_cost)."""
    sigmas = sigma_schedule(n9.ANCHOR_LEAD, sd, n9.ANCHOR_LEAD, exponent=exponent)
    hws = n9.halfwidth_schedule(hw, exponent)
    base = dict(n9.BASE)
    base["peak_sd_h"] = float(peak_sd_h)
    spec = Spec(bias_c=bias, **base)
    train = n9.Days(spec, sigmas, N_TRAIN, n9.SEED)
    test = n9.Days(spec, sigmas, N_TEST, n9.SEED + 1000)
    out = n9.score_all(spec, sigmas, hw, hws, test)
    adv = n9.best_fixed_hour(spec, hws, train, test)
    g, se = n9.paired(adv["per_day"], out["stopping_rule"]["per_day"])
    return g, se, out["stopping_rule"]["cost"], adv["test_cost"], adv["hour"]


def main():
    banner("N-24  Where are the lines? Breakevens for the two unmeasured quantities   [FREE]")
    t0 = time.time()

    res, n_tiles = n9.load_residuals()
    if res is None:
        print("   saved forecast/history fixtures not found -- cannot calibrate. ABORT.")
        return 2
    bias, sd = float(np.mean(res)), float(np.std(res))
    _SD_FOR_RHO[0] = sd          # rho is now the ratio the schedule actually produces
    hw, n_res = conformal_halfwidth(res, n9.ALPHA)
    print("\n   CALIBRATION  [M] %s matched tiles: bias %+.4f C, sd %.4f C, conformal hw %.4f C"
          % (format(n_tiles, ","), bias, sd, hw))
    print("   Adversary and scoring imported from test_n9_staging -- same code, not a copy.")
    print("   %s training + %s held-out days at every sweep point."
          % (format(N_TRAIN, ","), format(N_TEST, ",")))

    # ================================================================ RISK 1
    print("\n" + "=" * 74)
    print("   RISK 1  HOW MUCH FORECAST SHARPENING DOES THE RULE NEED?")
    print("=" * 74)
    print("   peak-hour uncertainty held at the measured %.2f h throughout." % MEASURED_PEAK_SD_H)
    print("\n   %9s %8s %11s %11s %9s %8s %6s"
          % ("exponent", "rho", "best tuned", "stopping", "gain", "se", "sigma"))
    rows_e = []
    for e in EXPONENTS:
        g, se, dp, adv, h = evaluate_point(bias, sd, hw, float(e), MEASURED_PEAK_SD_H)
        rows_e.append({"exponent": float(e), "rho": rho_of(e), "gain": g, "se": se,
                       "dp_cost": dp, "adv_cost": adv, "adv_hour": h})
        print("   %9.2f %8.3f %11.3f %11.3f %+9.3f %8.3f %6.1f%s"
              % (e, rho_of(e), adv, dp, g, se, g / max(se, 1e-12),
                 "" if g > 2 * se else ("  ns" if g > -2 * se else "  LOSES")))

    ge = np.array([r["gain"] for r in rows_e])
    see = np.array([r["se"] for r in rows_e])
    be0, e_all = cross(EXPONENTS, ge, see, 0.0)
    be2, _ = cross(EXPONENTS, ge, see, 2.0)
    sp_e = spearman(EXPONENTS, ge)
    print("\n   BREAKEVEN IN SHARPENING")
    if e_all:
        print("      the rule wins across the ENTIRE swept range -- risk 1 retired outright")
    elif be0 is None:
        print("      the rule NEVER wins in the swept range -- risk 1 is fatal, not open")
    else:
        print("      breaks even   at exponent %.3f  ->  rho = %.3f" % (be0, rho_of(be0)))
        print("      clears 2 sigma at exponent %.3f  ->  rho = %.3f"
              % (be2, rho_of(be2)) if be2 is not None else "      never clears 2 sigma")
        print("      MEANING: the 3-hour-lead forecast error must be at most %.0f %% of the"
              % (100 * rho_of(be2 if be2 is not None else be0)))
        print("               12-hour-lead forecast error. Above that ratio the stopping rule")
        print("               earns nothing over a tuned fixed-hour rule and we say so.")
    print("      monotone in the expected direction (Spearman) : %+.3f" % sp_e)

    # ================================================================ RISK 2
    print("\n" + "=" * 74)
    print("   RISK 2  HOW UNCERTAIN MUST THE PEAK HOUR BE?")
    print("=" * 74)
    print("   sharpening held at the random-walk exponent 0.50 (rho = %.3f) throughout."
          % rho_of(0.5))
    print("\n   %9s %11s %11s %9s %8s %6s %s"
          % ("peak sd h", "best tuned", "stopping", "gain", "se", "sigma", ""))
    rows_s = []
    for s in PEAK_SDS:
        g, se, dp, adv, h = evaluate_point(bias, sd, hw, 0.5, float(s))
        rows_s.append({"peak_sd_h": float(s), "gain": g, "se": se, "dp_cost": dp,
                       "adv_cost": adv, "adv_hour": h})
        mark = "   <-- MEASURED (N-12c)" if abs(s - 1.5) < 1e-9 else ""
        print("   %9.2f %11.3f %11.3f %+9.3f %8.3f %6.1f%s%s"
              % (s, adv, dp, g, se, g / max(se, 1e-12),
                 "" if g > 2 * se else ("  ns" if g > -2 * se else "  LOSES"), mark))

    gs = np.array([r["gain"] for r in rows_s])
    ses = np.array([r["se"] for r in rows_s])
    bs0, s_all = cross(PEAK_SDS, gs, ses, 0.0)
    bs2, _ = cross(PEAK_SDS, gs, ses, 2.0)
    sp_s = spearman(PEAK_SDS, gs)
    print("\n   BREAKEVEN IN PEAK-HOUR UNCERTAINTY")
    if s_all:
        print("      the rule wins across the ENTIRE swept range, including sd = 0")
    elif bs0 is None:
        print("      the rule NEVER wins in the swept range")
    else:
        print("      breaks even   at peak sd %.3f h" % bs0)
        print("      clears 2 sigma at peak sd %.3f h" % bs2 if bs2 is not None
              else "      never clears 2 sigma")
        print("      measured value %.2f h sits %s the 2-sigma line"
              % (MEASURED_PEAK_SD_H, "ABOVE" if (bs2 is not None and MEASURED_PEAK_SD_H > bs2)
                 else "BELOW"))
    print("      monotone in the expected direction (Spearman) : %+.3f" % sp_s)

    # verdict on the measured point specifically
    at_meas = min(rows_s, key=lambda r: abs(r["peak_sd_h"] - 1.5))
    p3 = at_meas["gain"] > 2.0 * at_meas["se"]
    print("      at the measured value: gain %+.3f +/- %.3f = %.1f sigma  -> P3 %s"
          % (at_meas["gain"], at_meas["se"], at_meas["gain"] / max(at_meas["se"], 1e-12),
             "PASS" if p3 else "FAIL"))

    # ================================================================ JOINT
    print("\n" + "=" * 74)
    print("   WHICH RISK ACTUALLY CARRIES THE CLAIM?  joint grid")
    print("=" * 74)
    print("   If the rule survives sd = 4 h even with NO sharpening, then peak-hour uncertainty")
    print("   alone is enough and risk 1 is not existential. If it dies everywhere at exponent 0,")
    print("   the sharpening measurement on 18 Aug decides the project. The grid says which.")
    print("\n   rows = tightening exponent (rho), cols = peak-hour sd in hours. Cell = sigma.")
    print("\n   %14s" % "" + "".join("%9.2f" % s for s in GRID_S))
    grid = []
    for e in GRID_E:
        line, cells = "   e=%.2f rho=%.2f" % (e, rho_of(e)), []
        for s in GRID_S:
            g, se, dp, adv, h = evaluate_point(bias, sd, hw, float(e), float(s))
            sig = g / max(se, 1e-12)
            cells.append({"exponent": float(e), "peak_sd_h": float(s), "gain": g, "se": se,
                          "sigma": sig})
            line += "%9.1f" % sig
        grid.append(cells)
        print(line)
    print("\n   (positive = stopping rule wins; > 2 = wins significantly; < -2 = loses)")

    no_sharpen = grid[0]
    survives_no_sharpen = [c for c in no_sharpen if c["sigma"] > 2.0]
    print("\n   READING THE FIRST ROW (no sharpening at all, rho = 1.00):")
    if survives_no_sharpen:
        need = min(c["peak_sd_h"] for c in survives_no_sharpen)
        print("      the rule still wins with NO sharpening once peak-hour sd reaches %.2f h."
              % need)
        print("      So the two risks are SUBSTITUTES, not both required: peak-hour uncertainty")
        print("      alone can carry the claim. Measured sd is %.2f h." % MEASURED_PEAK_SD_H)
    else:
        print("      the rule loses at EVERY peak-hour uncertainty when forecasts never sharpen.")
        print("      So risk 1 is not merely open, it is LOAD-BEARING: the 18 Aug sharpening")
        print("      measurement decides whether this decision is agentic at all. Say that")
        print("      plainly rather than discovering it in front of a judge.")

    # ================================================================ verdict
    p1 = sp_e > 0.8 and sp_s > 0.8
    p2 = (e_all or be0 is not None) and (s_all or bs0 is not None)
    ok = p1 and p2 and p3
    print("\n   RESULT")
    print("      P1 both curves monotone (>0.8)      : %s   (sharpening %+.3f, peak sd %+.3f)"
          % (p1, sp_e, sp_s))
    print("      P2 a finite breakeven exists in each: %s" % p2)
    print("      P3 measured peak sd wins by >2 sigma: %s   (%.1f sigma)"
          % (p3, at_meas["gain"] / max(at_meas["se"], 1e-12)))
    print("      elapsed %.0f s for %d sweep points"
          % (time.time() - t0, len(EXPONENTS) + len(PEAK_SDS) + len(GRID_E) * len(GRID_S)))
    print()
    verdict(ok,
            "PASS - both open risks now have numbers instead of adjectives. Forecast sharpening "
            "must reach rho <= %.3f (3 h error at most that fraction of the 12 h error) for the "
            "stopping rule to beat a tuned fixed-hour rule; peak-hour uncertainty must exceed "
            "%.2f h, and the measured %.2f h clears it at %.1f sigma. Both are now pre-registered "
            "day-one measurements with a stated kill condition."
            % (rho_of(be2 if be2 is not None else (be0 or 0.0)), bs2 if bs2 is not None else 0.0,
               MEASURED_PEAK_SD_H, at_meas["gain"] / max(at_meas["se"], 1e-12)),
            "FAIL - the sweeps do not yield a usable threshold (P1 %s, P2 %s, P3 %s). Either the "
            "gain curves are not monotone, so no day-one measurement can decide the question, or "
            "the measured peak-hour uncertainty is already on the losing side. Do not present the "
            "risks as merely open." % (p1, p2, p3))

    save_result("n24_breakeven.json", {
        "calibration": {"n_tiles": n_tiles, "bias_c": bias, "sd_c": sd,
                        "conformal_halfwidth_c": hw, "n_residuals": n_res},
        "n_train": N_TRAIN, "n_test": N_TEST, "spec": n9.BASE,
        "rho_definition": "sigma(%d h lead) / sigma(%d h lead)" % (LEAD_FOR_RHO, n9.ANCHOR_LEAD),
        "sharpening_sweep": rows_e,
        "sharpening_breakeven_exponent": be0, "sharpening_breakeven_rho":
            rho_of(be0) if be0 is not None else None,
        "sharpening_2sigma_exponent": be2, "sharpening_2sigma_rho":
            rho_of(be2) if be2 is not None else None,
        "sharpening_wins_everywhere": bool(e_all), "sharpening_spearman": sp_e,
        "peak_sd_sweep": rows_s,
        "peak_sd_breakeven_h": bs0, "peak_sd_2sigma_h": bs2,
        "peak_sd_wins_everywhere": bool(s_all), "peak_sd_spearman": sp_s,
        "measured_peak_sd_h": MEASURED_PEAK_SD_H,
        "at_measured": at_meas,
        "joint_grid": grid,
        "survives_without_sharpening_at_sd_h":
            (min(c["peak_sd_h"] for c in survives_no_sharpen) if survives_no_sharpen else None),
        "p1_monotone": p1, "p2_breakeven_exists": p2, "p3_measured_wins": p3, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
