# -*- coding: utf-8 -*-
"""N-46b  ---  HOW GOOD must the direction forecast be for a modelled margin to beat a constant?

THE LAST TEST OF THE MARGIN THESIS. Agreed stopping rule: whatever this returns, no
further variant of the margin claim is proposed. FREE, GPU table reused, zero API calls, no key.

WHY THIS EXISTS
    N-46 FAILED at -2.19 sigma: the modelled margin came out LARGER than the smallest constant
    achieving the same 90 % coverage. The mechanism was measured, not guessed:
      * the rise field is severely zero-inflated -- median p90 across all 72 direction bins is
        0.0000 C, peak 0.7887 C at 270 deg -- so the unconditional 90th percentile of realised rise
        is only 0.2144 C, and that is all a constant has to cover;
      * direction forecast error of 47.7 deg (1 h) to 72.7 deg (12 h) SMEARS that narrow plume across
        most of the compass, so the ensemble p90 is inflated on most days.
    But that error is KIAD PERSISTENCE, the honest LOWER bound on forecast skill, and N-46's §4
    recorded this limitation before the run. A real forecast is better. So the decisive question is
    not "does it work" but "how good must the direction forecast be".

WHAT IS SWEPT, AND WHY IT IS SCALED RATHER THAN REPLACED
    The empirical error pool is SCALED by a factor k, which preserves the observed distribution SHAPE
    (heavy tails and all) and changes only its magnitude. Substituting a Gaussian would silently
    change the shape as well as the size, and the shape is exactly what determines how often a
    forecast lands on the wrong side of a narrow plume edge.

    The scaled pool is used in BOTH places it appears: the true forecast error AND the agent's own
    ensemble spread. They must match, because a bound calibrated on one and evaluated against the
    other measures miscalibration, not forecast quality -- a different experiment.

PRE-REGISTERED BANDS, fixed before any output was seen, so "achievable" cannot be decided afterwards
    Let X = the direction-error sd (deg) at which the agent's margin advantage first reaches +2 SE.
      X >= 25 deg  -> the thesis is VIABLE on a modest requirement. Still must source real forecast
                      skill before any claim is made, but 25 deg at 9 h lead is unremarkable.
      10 <= X < 25 -> VIABLE BUT DEMANDING. No claim may be made until FortyGuard's (or an NWP)
                      direction skill is sourced and shown to beat X.
      X < 10 deg   -> DEAD. A requirement that tight is not plausibly met at 9 h lead.
      no crossover -> DEAD, and more strongly: modelling cannot beat a constant even with a PERFECT
                      direction forecast, which would mean the irreducible load/speed spread alone
                      is enough to sink it.
"""
import json
import math
import os
import sys

import numpy as np

from common import banner, save_result, FIXTURES
import test_n44_adaptive_commit as n44
from test_n9_staging import paired
from test_n46_margin import conformal_constant, ALPHA, HEADLINE_LEAD, WIND_FIXTURE

N_TRAIN = 20000          # larger than N-46: zero-inflation puts the 90th percentile in a sparse
N_TEST = 20000           # tail, and N-46 saw the tuned constant swing 0.1642-0.2209 C on resampling
SEED = 461
N_MEMBERS = 60           # matches n44.N_ENSEMBLE

# target direction-error sd in degrees; None means "as measured" (k = 1)
TARGET_SDS = [0.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, None]
P1_MIN_SIGMA = 2.0


def load_wind():
    d = json.load(open(WIND_FIXTURE, encoding="utf-8"))
    errors = {int(k): np.asarray(v, float) for k, v in d["errors"].items()}
    real_dirs = np.asarray(list(d["dir_by_date"].values()), float)
    return errors, real_dirs, d["meta"]


def dbin_vec(deg):
    """Vectorised form of n44.dbin. Kept adjacent to it so the two cannot silently diverge --
    HANDOFF GOTCHA #12 (two code paths agreeing only because they share a default)."""
    return (np.round((deg % 360.0) / (360.0 / n44.N_DIR_BINS)).astype(int)) % n44.N_DIR_BINS


def make_days_vec(table, pool, real_dirs, n_days, rng):
    """Vectorised day generation. Same model as test_n46_margin.make_days:
         forecast = true + error   (so the ensemble must invert with true = forecast - error,
                                    HANDOFF GOTCHA #11 / N-43's sign lesson)
    """
    true_dir = rng.choice(real_dirs, size=n_days, replace=True)
    fc_dir = (true_dir + rng.choice(pool, size=n_days, replace=True)) % 360.0

    midx = rng.integers(0, table.shape[1], size=n_days)
    truth = table[dbin_vec(true_dir), midx]

    errs = rng.choice(pool, size=(n_days, N_MEMBERS), replace=True)
    implied = (fc_dir[:, None] - errs) % 360.0            # true = forecast - error
    mi = rng.integers(0, table.shape[1], size=(n_days, N_MEMBERS))
    samples = table[dbin_vec(implied), mi]
    p90 = np.percentile(samples, 90, axis=1)
    return {"truth": truth, "p90": p90}


def evaluate(train, test):
    c_fixed = conformal_constant(train["truth"], ALPHA)
    q_agent = conformal_constant(train["truth"] - train["p90"], ALPHA)
    m_fixed = np.full(len(test["truth"]), c_fixed)
    m_agent = test["p90"] + q_agent
    gain, se = paired(m_fixed, m_agent)
    return {
        "c_fixed": float(c_fixed), "q_agent": float(q_agent),
        "mean_margin_fixed_c": float(m_fixed.mean()),
        "mean_margin_agent_c": float(m_agent.mean()),
        "coverage_fixed": float((test["truth"] <= m_fixed).mean()),
        "coverage_agent": float((test["truth"] <= m_agent).mean()),
        "margin_saved_c": float(gain), "se_c": float(se),
        "sigma": float(gain / se) if se > 0 else float("inf"),
        "agent_margin_sd_c": float(m_agent.std(ddof=1)),
        "frac_agent_below_fixed": float((m_agent < m_fixed).mean()),
        "relative_saving": float(gain / m_fixed.mean()) if m_fixed.mean() > 0 else None,
    }


def main():
    banner("N-46b  how good must the direction forecast be?  LAST test of the margin thesis  [FREE]")

    err_pool, real_dirs, meta = load_wind()
    base = err_pool[HEADLINE_LEAD]
    base_sd = float(base.std(ddof=1))
    print("   lead %d h, %s: measured direction-error sd = %.2f deg over n=%d"
          % (HEADLINE_LEAD, meta["station"], base_sd, len(base)))
    print("   sweeping the SCALED empirical pool (shape preserved), used for BOTH the true error and")
    print("   the agent's own ensemble spread, so the bound stays calibrated at every point.")

    table, dirs = n44.build_direction_table()
    p90_by_dir = np.percentile(table, 90, axis=1)
    print("      p90 rise peaks %.4f C at %.0f deg; median p90 across bins %.4f C"
          % (p90_by_dir.max(), dirs[int(np.argmax(p90_by_dir))], np.median(p90_by_dir)))

    # equivalence check: the vectorised path must reproduce N-46's headline within sampling error
    rng = np.random.default_rng(SEED)
    tr = make_days_vec(table, base, real_dirs, N_TRAIN, rng)
    te = make_days_vec(table, base, real_dirs, N_TEST, rng)
    chk = evaluate(tr, te)
    print("\n   EQUIVALENCE CHECK vs N-46 (loop implementation, 4k days, same inputs)")
    print("      N-46   : fixed 0.2144  agent 0.2220  saved -0.0076  sigma  -2.19")
    print("      N-46b  : fixed %.4f  agent %.4f  saved %+.4f  sigma %+6.2f"
          % (chk["mean_margin_fixed_c"], chk["mean_margin_agent_c"], chk["margin_saved_c"],
             chk["sigma"]))
    print("      (sigma differs with n by design: N-46b uses %d/%d days, not 4k/4k. The MARGINS are"
          % (N_TRAIN, N_TEST))
    print("       what must agree; a large discrepancy there would indicate a port defect.)")

    print("\n   %-12s %6s %10s %10s %10s %9s %9s"
          % ("target sd", "k", "fixed C", "agent C", "saved C", "sigma", "cov agent"))
    rows = []
    for tgt in TARGET_SDS:
        k = 1.0 if tgt is None else (tgt / base_sd if base_sd > 0 else 0.0)
        pool = base * k
        sd_eff = float(pool.std(ddof=1))
        rng = np.random.default_rng(SEED + 7)
        tr = make_days_vec(table, pool, real_dirs, N_TRAIN, rng)
        te = make_days_vec(table, pool, real_dirs, N_TEST, rng)
        r = evaluate(tr, te)
        r.update({"target_sd_deg": tgt, "k": k, "effective_sd_deg": sd_eff})
        rows.append(r)
        print("   %-12s %6.3f %10.4f %10.4f %+10.4f %+9.2f %8.1f %%"
              % ("as measured" if tgt is None else "%.0f deg" % tgt, k,
                 r["mean_margin_fixed_c"], r["mean_margin_agent_c"], r["margin_saved_c"],
                 r["sigma"], 100 * r["coverage_agent"]))

    # crossover: the LARGEST effective sd at which the agent still clears +2 SE. Reported as the
    # requirement, i.e. "the forecast must be at least this good".
    winners = [r for r in rows if r["sigma"] >= P1_MIN_SIGMA]
    crossover = max((r["effective_sd_deg"] for r in winners), default=None)

    print("\n   RESULT AGAINST BANDS FIXED BEFORE THE RUN")
    if crossover is None:
        band = "DEAD - no crossover at any error level, including a perfect direction forecast"
    elif crossover >= 25.0:
        band = "VIABLE on a modest requirement (crossover %.1f deg >= 25 deg)" % crossover
    elif crossover >= 10.0:
        band = ("VIABLE BUT DEMANDING (crossover %.1f deg, in [10, 25)) -- no claim until real "
                "direction skill is sourced and shown to beat it" % crossover)
    else:
        band = "DEAD - requirement %.1f deg is below the 10 deg plausibility floor" % crossover
    print("      largest direction-error sd at which modelling still wins by >= %.1f SE : %s"
          % (P1_MIN_SIGMA, "none" if crossover is None else "%.1f deg" % crossover))
    print("      verdict: %s" % band)
    print("\n      NOTE: this is a REQUIREMENT, not a performance claim. Nothing here shows that any")
    print("      real forecast -- FortyGuard's included -- actually meets it. That must be measured")
    print("      separately before a single word of it is pitched.")

    save_result("n46b_dirsweep.json", {
        "measures": "the direction-forecast accuracy REQUIRED for a modelled recirculation margin to "
                    "beat the smallest constant margin at equal 90 % coverage",
        "does_not_measure": "whether any real forecast meets that requirement; FortyGuard direction "
                            "skill is NOT measured here. Nothing in energy or money.",
        "stopping_rule": "agreed: this is the LAST test of the margin thesis, pass or fail",
        "lead_h": HEADLINE_LEAD,
        "measured_base_sd_deg": base_sd,
        "n_train": N_TRAIN, "n_test": N_TEST,
        "wind_source": meta,
        "equivalence_check_vs_n46": {
            "n46_fixed_c": 0.2144, "n46_agent_c": 0.2220, "n46_sigma": -2.19,
            "n46b_fixed_c": chk["mean_margin_fixed_c"], "n46b_agent_c": chk["mean_margin_agent_c"],
            "n46b_sigma": chk["sigma"]},
        "p90_peak_c": float(p90_by_dir.max()),
        "p90_median_across_bins_c": float(np.median(p90_by_dir)),
        "bands_fixed_before_run": {"viable_modest": ">= 25 deg", "viable_demanding": "[10, 25) deg",
                                   "dead": "< 10 deg or no crossover"},
        "crossover_sd_deg": crossover,
        "band": band,
        "rows": rows,
        "limits": "one site layout; scaled empirical error preserves shape but assumes the shape "
                  "itself does not change with forecast quality; simulated days, real physics",
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
