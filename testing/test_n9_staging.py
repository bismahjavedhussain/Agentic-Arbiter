# -*- coding: utf-8 -*-
"""N-9  ---  is the staging decision genuinely sequential, or secretly a threshold?  FREE.

run_e2e.py currently ends in three if-statements on headroom. That is a threshold, and a
threshold is not an agent. This test replaces it with an online stopping rule and then
tries hard to prove the replacement was pointless -- because if a simple rule can match it,
we should say so and stop claiming agency.

WHAT THE FIRST VERSION OF THIS TEST GOT WRONG, AND WHY IT MATTERS
    v1 posed the problem with a KNOWN peak hour. Deferring was then strictly better on both
    axes -- a tighter bound AND fewer paid hours -- with a hard wall where staging stopped
    working. "Wait until the wall" is near-optimal by construction there, and the DP duly
    discovered it: the simple rule WON. The tension was missing from the problem, not from
    the solver.

    The fix is physical, not cosmetic. You do not know which hour the peak will land on. If
    it arrives earlier than expected, the lead time you were saving no longer exists and the
    capacity shows up after the event. So waiting now carries a real, quantified risk that
    grows as you wait -- and how much risk you should accept depends on how hot the forecast
    says it will be. That trade-off has no fixed-hour solution.

THE ADVERSARY
    Not the rule we shipped. The best possible rule of the form "check the forecast at one
    fixed hour and stage if the bound breaches", with BOTH the hour and the margin tuned by
    exhaustive search. That family contains the day-0 threshold and defer-to-deadline as
    special cases.

    Critically, the adversary is tuned on TRAINING days and scored on HELD-OUT days. v1
    tuned and scored on the same days, which flattered it by roughly the size of the gap.
    The stopping rule has no tunable parameters at all -- it sees only the cost constants.

Calibration is real: forecast-vs-outcome residuals from fb_1_FCST_12H.json and
fb_2_HIST_SAMEWIN.json, 6,875 matched tiles.
"""
import json, sys
import numpy as np

from common import banner, save_result, verdict, field_path
from staging import (Spec, conformal_halfwidth, sigma_schedule, solve, make_forecast_paths,
                     draw_peak_hours, evaluate, fire_dp, fire_threshold_t0, fire_deadline,
                     fire_myopic, fire_fixed_hour, fire_always, fire_never, oracle_cost)

ALPHA = 0.10
N_TRAIN = 20000
N_TEST = 20000
SEED = 19

# [S] plant stubs. One cost unit = one hour of running the extra cooling train.
BASE = dict(thr_c=33.0, capacity_c=1.5, lead_h=3, horizon_h=12, end_h=12,
            c_stage_hr=1.0, c_stage_fixed=2.0, c_excursion=120.0,
            peak_centre_h=8.0, peak_sd_h=1.5)

ANCHOR_LEAD = 12
MARGINS = np.arange(-3.0, 3.001, 0.05)


# ------------------------------------------------------------------ calibration
def load_residuals():
    """Signed per-tile forecast errors on PEAK temperature, from the saved fixtures."""
    pf, ph = field_path("fb_1_FCST_12H.json"), field_path("fb_2_HIST_SAMEWIN.json")
    if not pf or not ph:
        return None, None

    def load(p):
        out = {}
        for t in json.load(open(p))["map_data"]["features"]:
            c = t["geometry"]["coordinates"][0]
            out[(round(sum(x[1] for x in c[:4]) / 4, 6),
                 round(sum(x[0] for x in c[:4]) / 4, 6))] = t["properties"]
        return out

    F, H = load(pf), load(ph)
    keys = [k for k in F if k in H]
    res = [F[k]["max_temperature"] - H[k]["max_temperature"] for k in keys
           if F[k].get("max_temperature") is not None and H[k].get("max_temperature") is not None]
    return res, len(keys)


def halfwidth_schedule(hw, exponent, max_lead=ANCHOR_LEAD, floor=0.05):
    """[S] shape, [M] anchor: conformal half-width by lead time."""
    return np.array([max(floor, hw * (l / float(max_lead)) ** exponent) if l > 0 else floor
                     for l in range(max_lead + 1)])


# ------------------------------------------------------------------ day generation
class Days:
    """One sampled population of days: true peak temperature, true peak hour, forecasts."""

    def __init__(self, spec, sigmas, n, seed):
        rng = np.random.default_rng(seed)
        self.truth = rng.normal(spec.thr_c - 0.6, 1.4, n)
        self.peak_h = draw_peak_hours(spec, n, rng)
        self.M = make_forecast_paths(spec, sigmas, self.truth, rng)

    def score(self, spec, F):
        return evaluate(spec, F, self.truth, self.peak_h)


# ------------------------------------------------------------------ adversary
def best_fixed_hour(spec, hws, train, test):
    """Tune (hour, margin) on TRAIN, report cost on TEST. Returns dict."""
    best = (None, None, float("inf"))
    for h in range(spec.horizon_h):
        for m in MARGINS:
            c = train.score(spec, fire_fixed_hour(spec, train.M, hws, h, float(m)))[0]
            if c < best[2]:
                best = (h, float(m), c)
    h, m, train_cost = best
    test_cost, _, exc, per_day = test.score(spec, fire_fixed_hour(spec, test.M, hws, h, m))
    return {"hour": h, "margin": m, "train_cost": train_cost,
            "test_cost": test_cost, "excursions": exc, "per_day": per_day}


def paired(adv_per_day, dp_per_day):
    """Mean and standard error of the PER-DAY cost difference (adversary minus stopping rule).

    Paired, because both policies are scored on identical days. A gain is only worth
    claiming if it clears about two of these standard errors.
    """
    d = np.asarray(adv_per_day) - np.asarray(dp_per_day)
    return float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d)))


def score_all(spec, sigmas, hw, hws, days):
    grid, policy, _ = solve(spec, sigmas)
    out = {}
    for name, F in (
        ("stopping_rule", fire_dp(spec, days.M, grid, policy)),
        ("deadline_thr", fire_deadline(spec, days.M, hws)),
        ("threshold_t0", fire_threshold_t0(spec, days.M, hw)),
        ("myopic_hourly", fire_myopic(spec, days.M, hws)),
        ("always_stage", fire_always(spec, days.M)),
        ("never_stage", fire_never(spec, days.M)),
    ):
        cost, epochs, exc, per_day = days.score(spec, F)
        out[name] = {"cost": cost, "epochs": epochs, "excursions": exc, "per_day": per_day}
    out["oracle"] = {"cost": oracle_cost(spec, days.truth, days.peak_h),
                     "epochs": None, "excursions": None}
    return out


# ------------------------------------------------------------------ main
def main():
    banner("N-9  Staging as an online stopping problem -- or is it secretly a threshold?  [FREE]")

    res, n_tiles = load_residuals()
    if res is None:
        print("   saved forecast/history fixtures not found -- cannot calibrate. ABORT.")
        return 2

    bias, sd = float(np.mean(res)), float(np.std(res))
    hw, n = conformal_halfwidth(res, ALPHA)
    print("\n   1. CALIBRATION  [M] from %s matched tiles" % format(n_tiles, ","))
    print("      forecast error on PEAK temperature: mean %+.4f C, sd %.4f C" % (bias, sd))
    print("      one-sided %d%% conformal half-width: %.4f C  (n=%s)"
          % (100 * (1 - ALPHA), hw, format(n, ",")))

    sigmas = sigma_schedule(ANCHOR_LEAD, sd, ANCHOR_LEAD, exponent=0.5)
    hws = halfwidth_schedule(hw, 0.5)
    spec = Spec(bias_c=bias, **BASE)

    print("\n   2. THE PROBLEM  [S] all costs are stubs")
    print("      threshold %.1f C, capacity gain %.1f C, lead time %d h, horizon %d h"
          % (spec.thr_c, spec.capacity_c, spec.lead_h, spec.horizon_h))
    print("      peak hour is UNCERTAIN: centred %.0f, sd %.1f h  -> waiting is risky"
          % (spec.peak_centre_h, spec.peak_sd_h))
    print("      P(staging at t still arrives before the peak):")
    print("         " + "  ".join("t=%d:%.2f" % (t, spec.protect_prob(t)) for t in range(0, 10)))
    print("      cost of staging at t (falls with t):")
    print("         " + "  ".join("t=%d:%.0f" % (t, spec.stage_cost(t)) for t in range(0, 10)))
    print("      -> waiting is CHEAPER and better-informed, but progressively less likely to")
    print("         work at all. There is no fixed hour that resolves that for every day.")

    train = Days(spec, sigmas, N_TRAIN, SEED)
    test = Days(spec, sigmas, N_TEST, SEED + 1000)
    print("\n   3. DAYS  %s train + %s held-out test days; %.1f%% of test days genuinely breach"
          % (format(N_TRAIN, ","), format(N_TEST, ","), 100 * np.mean(test.truth > spec.thr_c)))

    out = score_all(spec, sigmas, hw, hws, test)
    orc = out["oracle"]["cost"]
    print("\n   4. EXPECTED COST PER DAY on HELD-OUT days  (oracle knows temperature AND hour)")
    print("      %-16s %10s %12s %16s" % ("policy", "cost", "excursions", "regret vs oracle"))
    for k in ("oracle", "stopping_rule", "deadline_thr", "myopic_hourly", "threshold_t0",
              "always_stage", "never_stage"):
        c = out[k]["cost"]
        print("      %-16s %10.3f %12s %16s"
              % (k, c, "-" if k == "oracle" else format(out[k]["excursions"], ","),
                 "-" if k == "oracle" else "%+.3f" % (c - orc)))

    # ---- Q1 : beat the best tuned fixed-hour rule, out of sample
    adv = best_fixed_hour(spec, hws, train, test)
    dp_cost = out["stopping_rule"]["cost"]
    gain = adv["test_cost"] - dp_cost
    print("\n   5. Q1  BEST TUNED FIXED-HOUR RULE  (%d hours x %d margins searched on TRAIN)"
          % (spec.horizon_h, len(MARGINS)))
    print("      best: act at hour %d with margin %+.2f C" % (adv["hour"], adv["margin"]))
    print("        cost on TRAIN (where it was tuned) : %8.3f" % adv["train_cost"])
    print("        cost on HELD-OUT days              : %8.3f   <-- the honest number"
          % adv["test_cost"])
    print("        in-sample optimism it enjoyed      : %+8.3f" % (adv["test_cost"] - adv["train_cost"]))
    print("      stopping rule (zero tuned parameters): %8.3f" % dp_cost)
    gmean, gse = paired(adv["per_day"], out["stopping_rule"]["per_day"])
    print("      gain out of sample: %+.3f +/- %.3f (paired SE)   = %.1f sigma"
          % (gmean, gse, gmean / max(gse, 1e-12)))
    print("      that is %.1f%% of the regret the tuned rule leaves above the oracle"
          % (100 * gain / max(adv["test_cost"] - orc, 1e-9)))

    # ---- Q2 : state dependence
    eps = out["stopping_rule"]["epochs"]
    staged = eps[eps >= 0]
    hist = {t: int(np.sum(staged == t)) for t in range(spec.horizon_h)}
    n_staged = len(staged)
    modal = max(hist, key=lambda t: hist[t])
    off = n_staged - hist[modal]
    print("\n   6. Q2  WHEN does it stage?  (a fixed-hour rule fires at exactly ONE hour)")
    print("      staged on %s of %s test days (%.1f%%)"
          % (format(n_staged, ","), format(N_TEST, ","), 100 * n_staged / N_TEST))
    for t in range(spec.horizon_h):
        if hist[t]:
            print("        t=%-2d %6d  %s" % (t, hist[t], "#" * int(56 * hist[t] / max(n_staged, 1))))
    print("      modal hour t=%d holds %.1f%%; %s days (%.1f%%) fire at a different hour"
          % (modal, 100 * hist[modal] / max(n_staged, 1), format(off, ","),
             100 * off / max(n_staged, 1)))

    # ---- Q3 : stubs
    print("\n   7. Q3  DOES IT SURVIVE THE STUBS?  (all costs on held-out days)")
    print("      %-34s %11s %10s %8s %6s" % ("variation", "best tuned", "stopping", "gain", "sigma"))
    print("      (sigma = paired standard errors; |sigma|<2 means indistinguishable, not a loss)")
    sweeps, all_pos, worst = [], True, (None, float("inf"))

    def sweep(label, spec2, sigmas2, hws2):
        nonlocal all_pos, worst
        tr = Days(spec2, sigmas2, N_TRAIN, SEED)
        te = Days(spec2, sigmas2, N_TEST, SEED + 1000)
        o2 = score_all(spec2, sigmas2, hw, hws2, te)
        a2 = best_fixed_hour(spec2, hws2, tr, te)
        g, se = paired(a2["per_day"], o2["stopping_rule"]["per_day"])
        sig = g / max(se, 1e-12)
        sweeps.append({"variation": label, "best_tuned_hour": a2["hour"],
                       "best_tuned_test": a2["test_cost"],
                       "stopping": o2["stopping_rule"]["cost"], "gain": g,
                       "se": se, "sigma": sig})
        if g < -1e-9:
            all_pos = False
        if g < worst[1]:
            worst = (label, g)
        tag = "" if sig > 2 else ("  ns" if sig > -2 else "  LOSES")
        print("      %-34s %11.3f %10.3f %8s %6.1f%s"
              % (label, a2["test_cost"], o2["stopping_rule"]["cost"], "%+.3f" % g, sig, tag))

    for ex in (0.0, 0.5, 1.0):
        sweep("tightening exponent %.2f%s" % (ex, " (none)" if ex == 0 else ""),
              Spec(bias_c=bias, **BASE),
              sigma_schedule(ANCHOR_LEAD, sd, ANCHOR_LEAD, exponent=ex),
              halfwidth_schedule(hw, ex))
    for ps in (0.5, 1.0, 2.5, 4.0):
        b = dict(BASE); b["peak_sd_h"] = ps
        sweep("peak-hour sd %.1f h" % ps, Spec(bias_c=bias, **b), sigmas, hws)
    for ce in (20.0, 60.0, 240.0, 600.0):
        b = dict(BASE); b["c_excursion"] = ce
        sweep("excursion cost %.0f" % ce, Spec(bias_c=bias, **b), sigmas, hws)
    for lh in (1, 2, 4, 6):
        b = dict(BASE); b["lead_h"] = lh
        sweep("lead time %d h" % lh, Spec(bias_c=bias, **b), sigmas, hws)
    for cap in (0.5, 1.0, 3.0):
        b = dict(BASE); b["capacity_c"] = cap
        sweep("capacity gain %.1f C" % cap, Spec(bias_c=bias, **b), sigmas, hws)
    for cf in (0.0, 6.0, 15.0):
        b = dict(BASE); b["c_stage_fixed"] = cf
        sweep("fixed staging cost %.0f" % cf, Spec(bias_c=bias, **b), sigmas, hws)

    # ---- verdict
    q1 = gmean > 2.0 * gse
    q2 = (off / max(n_staged, 1)) > 0.05
    n_win = sum(1 for s in sweeps if s["sigma"] > 2)
    n_loss = sum(1 for s in sweeps if s["sigma"] < -2)
    print("\n   8. RESULT")
    print("      Q1 beats best tuned rule out of sample, >2 sigma  : %s  (%+.3f +/- %.3f)"
          % (q1, gmean, gse))
    print("      Q2 decision is state-dependent                    : %s  (%.1f%% off modal hour)"
          % (q2, 100 * off / max(n_staged, 1)))
    print("      Q3 of %d stub variations: %d significant wins, %d significant losses"
          % (len(sweeps), n_win, n_loss))
    print("         weakest variation: %s at %+.3f" % (worst[0], worst[1]))
    ok = q1 and q2
    print()
    verdict(ok,
            "PASS - the staging decision is genuinely sequential. Against the BEST tuned "
            "fixed-hour rule it wins %.3f cost units/day on held-out days with zero tuned "
            "parameters, and it fires off its modal hour on %.1f%% of staging days."
            % (gain, 100 * off / max(n_staged, 1)),
            "FAIL - a tuned fixed-hour rule matches or beats it. Do not claim agency from "
            "this decision; report the null and look to the fleet-allocation problem instead.")

    save_result("n9_staging.json", {
        "calibration": {"n_tiles": n_tiles, "bias_c": bias, "sd_c": sd,
                        "conformal_halfwidth_c": hw, "n_residuals": n, "alpha": ALPHA},
        "spec": BASE, "n_train": N_TRAIN, "n_test": N_TEST,
        "protect_prob": {t: spec.protect_prob(t) for t in range(spec.horizon_h)},
        "costs_heldout": {k: out[k]["cost"] for k in out},
        "excursions_heldout": {k: out[k]["excursions"] for k in out},
        "oracle": orc,
        "adversary": {k: adv[k] for k in ("hour", "margin", "train_cost", "test_cost", "excursions")},
        "gain_vs_best_tuned": gain, "gain_paired_se": gse, "gain_sigma": gmean / max(gse, 1e-12),
        "stage_epoch_histogram": hist, "modal_epoch": modal,
        "off_modal_frac": off / max(n_staged, 1),
        "sweeps": sweeps, "n_sweeps_won": n_win, "n_sweeps_lost": n_loss, "all_sweeps_positive": all_pos,
        "weakest_sweep": list(worst),
        "q1_beats_best_tuned": q1, "q2_state_dependent": q2, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
