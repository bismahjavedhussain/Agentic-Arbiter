# -*- coding: utf-8 -*-
"""N-46  ---  does a MODELLED recirculation margin beat a WORST-CASE FIXED margin, at equal safety?

Pre-registered in n46-margin-PREREG.md. Conditions P1/P2/P3 below were fixed before any number was
computed. FREE: existing GPU physics + cached free NOAA ASOS. Zero API calls, no key use.

THE CLAIM UNDER TEST
    An operator who cannot see the recirculation at their own intake must hold a margin sized for the
    worst case over all wind directions, permanently. An agent that models it per hour should hold a
    SMALLER margin on most hours AT THE SAME SAFETY LEVEL.

WHY THIS COMPARISON ISOLATES OUR CONTRIBUTION
    Both policies handle ambient identically, so ambient CANCELS. The only difference is whether the
    recirculation increment is modelled or assumed worst-case. N-45 showed the earlier framings could
    not do this: the commitment decision was dominated by ambient (+-1.5-4 C) against a recirculation
    term of 0.25-0.40 C, so the physics was a 10-25 % correction. Here the physics is the whole signal.

THE ADVERSARY IS NOT A STRAWMAN
    It is the SMALLEST CONSTANT margin achieving >= 90 % coverage on training days -- exactly what a
    competent engineer does with the same data and no model. Both policies get ONE calibration
    constant, fitted by the identical one-sided split-conformal construction, so neither is
    advantaged. The agent has no other tuned parameter.

SIGN CONVENTION (N-43's lesson, HANDOFF GOTCHA #11)
    Days are generated as forecast = true + error, so the ensemble must invert with
    true = forecast - error. ensemble_p90() does exactly that; do not "fix" one without the other.
"""
import json
import math
import os
import statistics
import sys

import numpy as np

from common import banner, save_result, verdict, FIXTURES
import test_n44_adaptive_commit as n44
from test_n9_staging import paired

# ----------------------------------------------------------------- pre-registered conditions
ALPHA = 0.10                 # one-sided 90 % bound
P1_MIN_SIGMA = 2.0           # agent margin must be lower by >= 2 paired SE
P2_MIN_COVERAGE = 0.88       # sampling slack around the 90 % target; below this, calibration failed
P3_MIN_SD_C = 0.01           # agent margin must genuinely vary
P3_MIN_FRAC_BELOW = 0.50     # and be strictly below the fixed margin on >= 50 % of days

N_TRAIN = 4000
N_TEST = 4000
SEED = 46
HEADLINE_LEAD = 9            # matches the ~9.5 h lead N-25/N-26 actually operate at
LEADS_REPORTED = list(range(1, 13))

WIND_FIXTURE = os.path.join(FIXTURES, "n46_kiad_wind.json")


def load_wind():
    if not os.path.exists(WIND_FIXTURE):
        print("   wind fixture missing. Run: python fetch_n46_wind.py")
        sys.exit(2)
    d = json.load(open(WIND_FIXTURE, encoding="utf-8"))
    errors = {int(k): np.asarray(v, float) for k, v in d["errors"].items()}
    real_dirs = np.asarray(list(d["dir_by_date"].values()), float)
    return errors, real_dirs, d["meta"]


def conformal_constant(residuals, alpha=ALPHA):
    """Smallest q with P(residual <= q) >= 1 - alpha, finite-sample valid.

    One-sided split conformal: take the k-th smallest residual where k = ceil((n+1)(1-alpha)).
    That is the standard construction and it guarantees coverage >= 1 - alpha on exchangeable data.
    If k > n the bound is not attainable from this calibration set and we return +inf rather than
    silently clipping to the maximum, which would overstate coverage.
    """
    r = np.sort(np.asarray(residuals, float))
    n = len(r)
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        return float("inf")
    return float(r[k - 1])


def make_days(table, err_pool, real_dirs, n_days, lead, seed):
    """Sample days from the REAL direction distribution, not a uniform compass.

    Using a uniform compass would invent the answer: the plume peak at 265 deg sits in a sector
    holding only 7.8 % of observed target-hour days, while 210-240 deg holds 16.9 %.
    """
    rng = np.random.default_rng(seed)
    true_dir = rng.choice(real_dirs, size=n_days, replace=True)
    fc_dir = (true_dir + rng.choice(err_pool[lead], size=n_days, replace=True)) % 360.0
    truth = np.array([rng.choice(table[n44.dbin(t)]) for t in true_dir])
    p90 = np.array([n44.ensemble_p90(table, f, lead, err_pool, rng) for f in fc_dir])
    return {"true_dir": true_dir, "fc_dir": fc_dir, "truth": truth, "p90": p90}


def evaluate(train, test):
    """Calibrate both policies on train, score both on the same test days."""
    # adversary: smallest constant margin covering 90 % of training truths
    c_fixed = conformal_constant(train["truth"])
    # agent: p90 plus the smallest conformal correction covering 90 % of training residuals
    q_agent = conformal_constant(train["truth"] - train["p90"])

    m_fixed = np.full(len(test["truth"]), c_fixed)
    m_agent = test["p90"] + q_agent

    cov_fixed = float((test["truth"] <= m_fixed).mean())
    cov_agent = float((test["truth"] <= m_agent).mean())

    gain, se = paired(m_fixed, m_agent)          # positive gain = agent holds a SMALLER margin
    sigma = gain / se if se > 0 else float("inf")

    return {
        "c_fixed": c_fixed, "q_agent": q_agent,
        "mean_margin_fixed_c": float(m_fixed.mean()), "mean_margin_agent_c": float(m_agent.mean()),
        "coverage_fixed": cov_fixed, "coverage_agent": cov_agent,
        "margin_saved_c": float(gain), "se_c": float(se), "sigma": float(sigma),
        "agent_margin_sd_c": float(m_agent.std(ddof=1)),
        "frac_agent_below_fixed": float((m_agent < m_fixed).mean()),
        "relative_saving": float(gain / m_fixed.mean()) if m_fixed.mean() > 0 else None,
    }


def main():
    banner("N-46  modelled recirculation margin vs worst-case fixed margin   [FREE, GPU]")
    print("   Pre-registered in n46-margin-PREREG.md. Both policies handle ambient identically, so")
    print("   ambient cancels and what is measured is attributable to the solver + wind inputs only.")

    err_pool, real_dirs, meta = load_wind()
    print("\n   [1/4] real wind, %s: %d target-hour days, %d summers, calm (< %.0f kt) excluded"
          % (meta["station"], len(real_dirs), len(meta["years"]), meta["min_kt"]))
    print("      direction persistence error sd: %.1f deg at 1 h -> %.1f deg at 12 h"
          % (err_pool[1].std(ddof=1), err_pool[12].std(ddof=1)))

    print("\n   [2/4] GPU precompute: calibrated demo site, full 0-360 deg sweep, real physics")
    table, dirs = n44.build_direction_table()
    allr = table.ravel()
    p90_by_dir = np.percentile(table, 90, axis=1)
    print("      rise over all directions: min %.4f  median %.4f  max %.4f C"
          % (allr.min(), np.median(allr), allr.max()))
    print("      p90 rise peaks at %.0f deg = %.4f C; median p90 across bins = %.4f C"
          % (dirs[int(np.argmax(p90_by_dir))], p90_by_dir.max(), np.median(p90_by_dir)))

    # what the real direction distribution implies, versus assuming a uniform compass
    w = np.zeros(n44.N_DIR_BINS)
    for d in real_dirs:
        w[n44.dbin(d)] += 1
    w /= w.sum()
    print("      mean p90 weighted by REAL direction frequency: %.4f C   (uniform compass: %.4f C)"
          % (float((w * p90_by_dir).sum()), float(p90_by_dir.mean())))

    print("\n   [3/4] headline at lead %d h (the lead N-25/N-26 actually operate at)" % HEADLINE_LEAD)
    train = make_days(table, err_pool, real_dirs, N_TRAIN, HEADLINE_LEAD, SEED + 1)
    test = make_days(table, err_pool, real_dirs, N_TEST, HEADLINE_LEAD, SEED + 2)
    r = evaluate(train, test)

    print("      tuned fixed margin (smallest constant with >= 90 %% train coverage) = %.4f C"
          % r["c_fixed"])
    print("      agent conformal correction q = %+.4f C" % r["q_agent"])
    print("      %-28s %12s %12s" % ("policy (HELD-OUT)", "mean margin", "coverage"))
    print("      %-28s %12.4f %11.1f %%" % ("tuned fixed", r["mean_margin_fixed_c"],
                                            100 * r["coverage_fixed"]))
    print("      %-28s %12.4f %11.1f %%" % ("agent (modelled)", r["mean_margin_agent_c"],
                                            100 * r["coverage_agent"]))
    print("      margin saved %+.4f +/- %.4f C = %+.2f sigma   (%.1f %% of the fixed margin)"
          % (r["margin_saved_c"], r["se_c"], r["sigma"], 100 * (r["relative_saving"] or 0.0)))

    p1 = r["sigma"] >= P1_MIN_SIGMA
    p2 = (r["coverage_agent"] >= r["coverage_fixed"]
          and min(r["coverage_agent"], r["coverage_fixed"]) >= P2_MIN_COVERAGE)
    p3 = (r["agent_margin_sd_c"] > P3_MIN_SD_C
          and r["frac_agent_below_fixed"] >= P3_MIN_FRAC_BELOW)

    print("\n   [4/4] the same comparison across every lead, to show how the saving depends on notice")
    print("      %-7s %11s %11s %10s %10s %9s" % ("lead h", "fixed C", "agent C", "saved C",
                                                  "sigma", "cov agent"))
    by_lead = {}
    for lead in LEADS_REPORTED:
        tr = make_days(table, err_pool, real_dirs, N_TRAIN, lead, SEED + 100 + lead)
        te = make_days(table, err_pool, real_dirs, N_TEST, lead, SEED + 200 + lead)
        rr = evaluate(tr, te)
        by_lead[lead] = rr
        print("      %-7d %11.4f %11.4f %10.4f %10.2f %8.1f %%"
              % (lead, rr["mean_margin_fixed_c"], rr["mean_margin_agent_c"], rr["margin_saved_c"],
                 rr["sigma"], 100 * rr["coverage_agent"]))

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE ANY NUMBER WAS SEEN")
    print("      P1 agent margin lower by >= %.1f paired SE : %s (%+.2f sigma)"
          % (P1_MIN_SIGMA, p1, r["sigma"]))
    print("      P2 no safety sold to buy it               : %s (agent %.1f %% vs fixed %.1f %%)"
          % (p2, 100 * r["coverage_agent"], 100 * r["coverage_fixed"]))
    print("      P3 margin genuinely varies, not a constant: %s (sd %.4f C, below fixed on %.1f %%)"
          % (p3, r["agent_margin_sd_c"], 100 * r["frac_agent_below_fixed"]))
    ok = p1 and p2 and p3
    print()
    verdict(ok,
            "PASS - modelling the recirculation holds a margin %.4f +/- %.4f C smaller than the best "
            "tuned constant (%+.2f SE, %.1f %% of it) with coverage %.1f %% vs %.1f %%, i.e. no safety "
            "was sold to buy it, and the margin genuinely varies (sd %.4f C) rather than collapsing to "
            "a constant. Ambient cancels from this comparison by construction, so the saving is "
            "attributable to the solver and the wind inputs."
            % (r["margin_saved_c"], r["se_c"], r["sigma"], 100 * (r["relative_saving"] or 0),
               100 * r["coverage_agent"], 100 * r["coverage_fixed"], r["agent_margin_sd_c"]),
            "FAIL - P1 %s (%+.2f SE), P2 %s (agent %.1f %% vs fixed %.1f %%), P3 %s (sd %.4f C, below "
            "on %.1f %%). If P3 is what failed, the conformal correction dominates the modelled term "
            "and the agent IS the fixed rule in costume. If P1 failed, modelling the recirculation "
            "buys no margin and INTAKE's value proposition is not margin reduction. Report it that way."
            % (p1, r["sigma"], p2, 100 * r["coverage_agent"], 100 * r["coverage_fixed"], p3,
               r["agent_margin_sd_c"], 100 * r["frac_agent_below_fixed"]))

    save_result("n46_margin.json", {
        "measures": "margin in C saved by modelling the recirculation increment per hour, versus the "
                    "smallest constant margin achieving the same 90 % coverage target",
        "does_not_measure": "the operator's TOTAL margin (ambient component is larger and not ours); "
                            "FortyGuard forecast skill (KIAD persistence is a LOWER bound); and "
                            "nothing in energy or money -- see P4 in n46-margin-PREREG.md",
        "wind_source": meta,
        "n_real_direction_days": len(real_dirs),
        "wind_speed_ms_primary": n44.WIND_SPEED_MS,
        "wind_speed_note": "primary run uses WIND_SPEED_MS = 3.0 for comparability with N-23/N-44; "
                           "the measured KIAD median at the target hour is 8.0 kt = 4.12 m/s, which "
                           "would give LOWER rise (concentration falls with wind speed), so 3.0 is "
                           "the conservative choice. Sensitivity at 4.12 m/s not yet run.",
        "headline_lead_h": HEADLINE_LEAD,
        "p90_peak_dir_deg": float(dirs[int(np.argmax(p90_by_dir))]),
        "p90_peak_c": float(p90_by_dir.max()),
        "mean_p90_real_weighted_c": float((w * p90_by_dir).sum()),
        "mean_p90_uniform_c": float(p90_by_dir.mean()),
        "headline": r,
        "by_lead": by_lead,
        "conditions": {"p1_min_sigma": P1_MIN_SIGMA, "p2_min_coverage": P2_MIN_COVERAGE,
                       "p3_min_sd_c": P3_MIN_SD_C, "p3_min_frac_below": P3_MIN_FRAC_BELOW},
        "p1": bool(p1), "p2": bool(p2), "p3": bool(p3), "pass": bool(ok),
        "limits": "one site layout (N-28 showed layout sensitivity); persistence wind error is a "
                  "LOWER bound on forecast skill; simulated days sampled from real wind and real "
                  "ambient with real solver physics; recirculation margin only",
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
