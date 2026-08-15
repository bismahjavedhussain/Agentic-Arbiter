# -*- coding: utf-8 -*-
"""N-44  ---  ADAPTIVE COMMITMENT: does today's MEASURED ambiguity make WHEN-to-commit a real
sequential decision?   FREE, GPU precompute then pure array lookups. Zero API calls.

=============================================================================================
WHY THIS TEST EXISTS -- and what was wrong with the three that failed before it
=============================================================================================
Three decision cores have now failed or been rendered unmeasurable in this project:

  N-25  FortyGuard temperature sharpening.  b = -0.0608, CI [-0.316,+0.195], FAIL vs the 0.129
        pre-registered break-even. Later found to have fitted the WRONG STATISTIC (spatial sd
        across tiles, not day-to-day sd of the site-level error).
  N-42  The corrected day-to-day statistic. Estimator built and validated, but a power analysis
        showed ~80-160 DAYS are needed for a decisive verdict, and an irreducible day-level
        offset attenuates the measurable exponent further. Unresolvable on the hackathon calendar.
  N-40  Wind-direction sharpening through the solver.  sigma_recirc went the WRONG WAY:
        0.26 C at 1 h lead vs 0.16 C at 12 h lead, CI [-0.221,-0.046], excludes zero, well
        powered. Recorded as a real, decisive FAIL.
  N-43  Multi-site fleet triage.  -3.63 sigma against a tuned point-forecast baseline. Real,
        decisive FAIL (a sign-inversion bug was found and fixed first; the verdict survived it).

    THE COMMON STRUCTURE OF ALL FOUR: each assumed or tested that some SUMMARY STATISTIC in
    degrees Celsius shrinks as the decision hour approaches. Three measured it and found it does
    not. So "waiting buys a tighter number" is dead, and this test does NOT resurrect it.

=============================================================================================
THE OBSERVATION THAT MOTIVATES THIS TEST, AND WHY IT IS NOT THE SAME CLAIM
=============================================================================================
N-40's inversion has a specific, mechanical explanation that is visible in its own output, and
that explanation points at a DIFFERENT quantity:

  At LONG lead, direction error is huge (measured 71.9 deg sd at 12 h). The ensemble sprays
  members across most of the compass, so most of them miss the plume entirely. The distribution
  of intake rise collapses toward "probably nothing": N-40 measured mean rise 0.10 C, and only
  43 % of members in the hot zone. A distribution piled up near zero has LOW standard deviation.

  At SHORT lead, direction error is much smaller (measured 52.5 deg sd at 1 h). More members land
  squarely on the plume. N-40 measured mean rise 0.28 C with 71 % of members hot. A distribution
  genuinely split between "hot" and "not hot" has HIGH standard deviation.

    So sigma in degrees C was measuring DILUTION, not CONFIDENCE. A washed-out ensemble looks
    "certain" by that metric precisely because it has stopped resolving anything. N-40's number
    is correct and its FAIL stands -- for the quantity it measured. It does not settle whether the
    forecast becomes more DECISION-RELEVANT as lead shortens, because sigma-in-C is the wrong
    yardstick for that.

  And the INPUT does sharpen, strongly and with real statistical power: wind-direction persistence
  error, measured over 72 real days at KIAD, falls from 62.0 deg MAE at 12 h to 33.8 deg at 1 h
  (b = +0.278, SE 0.034, t = +8.28, CI [+0.203,+0.353]). That is not in dispute.

=============================================================================================
PHASE 1 -- THE HONEST PREREQUISITE, MEASURED BEFORE ANY DECISION POLICY IS BUILT
=============================================================================================
Before building any stopping rule, measure the only thing that could justify one:

    does the forecast's ability to DISCRIMINATE breach from no-breach improve as lead shortens?

Measured as AUC (area under the ROC curve) of the ensemble p90 as a score for the binary outcome
"did the realised intake rise exceed the threshold". AUC is scale-free and cannot be gamed by
dilution: an ensemble that washes out toward zero loses discriminating power and its AUC falls
toward 0.5, however small its standard deviation becomes. This is precisely the failure mode that
sigma-in-C was blind to.

  P1 (PRE-REGISTERED): AUC must INCREASE as lead shortens, by a margin that clears its own
      bootstrap confidence interval. If AUC is flat or falls, then waiting genuinely buys NO
      decision-relevant information, the stopping problem is dead for the fourth time, and this
      test reports that null and stops. No policy is built and nothing is salvaged.

=============================================================================================
PHASE 2 -- THE DECISION, AND WHY IT IS SEQUENTIAL RATHER THAN A THRESHOLD
=============================================================================================
Only if P1 passes. The problem, using this project's own already-measured constants:

  * The peak hour is UNCERTAIN. peak_sd_h = 1.4475 h, measured on 15 days in N-38, with a
    leave-one-out floor of 1.1579 h (2.9x the 0.395 h break-even). This is the most robustly
    measured decision-relevant quantity in the entire project and it is what makes waiting risky.
  * Reserve cooling needs LEAD_H hours to come online, and costs money for every hour it runs.
    Committing LATER is CHEAPER (fewer paid hours) but risks the capacity arriving after the peak.
  * Waiting also buys information -- but only as much as Phase 1 actually measured, no more.

  THE ADAPTIVE ELEMENT, which is the whole point: how much information waiting buys is NOT the
  same on every day. It depends on where today's forecast sits relative to the plume geometry --
  N-23 measured the ensemble spread varying 27.04x between the geometric edge (0.2556 C at 285
  deg) and the safe sectors (0.0095 C). On a day sitting solidly in a safe or solidly in a hot
  sector, the answer is already resolved and waiting buys nothing. On a knife-edge day it is
  genuinely unresolved and waiting buys a great deal. So the OPTIMAL COMMITMENT TIME IS
  STATE-DEPENDENT, and the state variable is measured, not assumed.

  THE ADVERSARY: the best FIXED-LEAD commitment rule -- commit at a fixed hour if p90 exceeds a
  margin -- with BOTH the hour and the margin tuned exhaustively on TRAINING days and scored on
  HELD-OUT days. Same adversary family and the same paired-standard-error scoring imported from
  test_n9_staging, not reimplemented. The adaptive policy has ZERO tuned parameters.

  P2 (PRE-REGISTERED): the adaptive policy must beat the best tuned fixed-lead rule by >= 2
      paired standard errors on held-out days.

  P3 (PRE-REGISTERED -- THE ANTI-THRESHOLD GUARD, and the most important condition here):
      the adaptive policy must actually VARY its commitment hour across days. Specifically it
      must fire off its own modal hour on >= 25 % of committing days. N-9 v1 failed in exactly
      this way -- it "won" by discovering a constant, which is a threshold wearing a costume. If
      the policy collapses to a single hour, this test FAILS EVEN IF P2 PASSES, and the honest
      conclusion is that a fixed rule is sufficient and no agent is warranted.

=============================================================================================
WHAT THIS TEST CANNOT ESTABLISH -- stated before running
=============================================================================================
  * It uses ONE site geometry (solver.demo_site). N-28 already showed conclusions can be layout
    specific; a pass here would need the layout sweep repeating before being generalised.
  * The wind-direction error distribution is PERSISTENCE, from one station, 72 days. Persistence
    is the honest LOWER bound on forecast skill, so a real forecast should do better -- but this
    also means the absolute AUC numbers are pessimistic, not calibrated to FortyGuard's product.
  * Simulated days, real physics. The rise distributions come from the calibrated solver on the
    GPU; the days themselves are sampled, not observed. This tests the DECISION STRUCTURE, not
    FortyGuard's forecast skill (that is damper-test-3 / a separate live test).
"""
import json, os, statistics, sys, time

import numpy as np
from sklearn.isotonic import IsotonicRegression

from common import banner, save_result, verdict, FIXTURES
import solver
from solver import CALIBRATED
import warp_solver as ws
from test_n9_staging import paired

if not ws.HAVE_WARP:
    print("warp-lang unavailable; this test needs the GPU path.")
    sys.exit(2)

# ----------------------------------------------------------------- measured inputs
PEAK_SD_H = 1.4475          # N-38, 15 days, leave-one-out floor 1.1579 h
PEAK_CENTRE_H = 8.0         # matches test_n9_staging.BASE
HORIZON_H = 12
LEAD_H = 3                  # reserve cooling needs 3 h to come online (n9.BASE)
C_STAGE_HR = 1.0
C_STAGE_FIXED = 2.0
C_EXCURSION = 120.0
CAPACITY_RISE = 0.25        # C of intake rise the reserve absorbs [S] swept in the sensitivity block

AMB = 30.0
WIND_SPEED_MS = 3.0
N_DIR_BINS = 72             # 5 deg bins, matching N-23's sweep resolution
N_MEMBERS_PER_BIN = 60
N_ENSEMBLE = 60
STEPS = 800
N_TRAIN = 4000
N_TEST = 4000
N_AUC_TRIALS = 3000
SEED = 44

P1_MIN_AUC_GAIN = 0.0       # must be positive AND clear its bootstrap CI
P2_MIN_SIGMA = 2.0
P3_MIN_OFF_MODAL = 0.25     # >= 25 % of committing days must fire off the modal hour

MARGINS = np.arange(-0.30, 0.301, 0.02)


def load_dir_errors():
    p = os.path.join(FIXTURES, "n40_kiad_dir_errors.json")
    if not os.path.exists(p):
        print("   missing %s -- run test_n40_windsharpen.py first (free)" % p)
        sys.exit(2)
    d = json.load(open(p, encoding="utf-8"))
    return {int(k): np.asarray(v, dtype=float) for k, v in d["errors"].items()}, d["meta"]


# ----------------------------------------------------------------- GPU precompute
def build_direction_table(seed=7):
    """rise(wind_direction) distribution for the calibrated demo site, real physics on the GPU.
    Returns (N_DIR_BINS, N_MEMBERS_PER_BIN) of intake rise above ambient."""
    rng = np.random.default_rng(seed)
    site, intake = solver.demo_site()
    solver.assert_intake_clear(site, *intake, label="N-44 demo_site")
    dirs = np.arange(0.0, 360.0, 360.0 / N_DIR_BINS)
    wf = np.repeat(dirs, N_MEMBERS_PER_BIN)
    spd = np.clip(rng.normal(WIND_SPEED_MS, 1.0, len(wf)), 0.3, 14.0)
    scl = np.maximum(0.1, rng.normal(1.0, 2.0 / 11.0, len(wf)))
    dw = np.array([solver.downwash_fraction(v, CALIBRATED["downwash_uc"],
                                            CALIBRATED["downwash_exponent"]) for v in spd])
    t0 = time.time()
    T = ws.solve_batch(site, np.full(len(wf), AMB), spd, wf, scl,
                       steps=STEPS, device="cuda", downwash=dw)
    rise = np.array([solver.intake_temperature(T[m].astype(np.float64), site, *intake) - AMB
                     for m in range(len(wf))])
    print("      %d bins x %d members = %d GPU solves in %.1f s"
          % (N_DIR_BINS, N_MEMBERS_PER_BIN, len(wf), time.time() - t0))
    return rise.reshape(N_DIR_BINS, N_MEMBERS_PER_BIN), dirs


def dbin(direction_deg):
    return int(round((direction_deg % 360.0) / (360.0 / N_DIR_BINS))) % N_DIR_BINS


# ----------------------------------------------------------------- Phase 1: AUC vs lead
def auc(scores, labels):
    """Mann-Whitney AUC. No sklearn dependency."""
    s = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float)
    ranks[order] = np.arange(1, len(s) + 1)
    # average ranks within ties
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt))
    np.add.at(sums, inv, ranks)
    ranks = (sums / cnt)[inv]
    return (ranks[y].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def ensemble_p90(table, fc_dir, lead, err_pool, rng):
    draws = rng.choice(err_pool[lead], size=N_ENSEMBLE, replace=True)
    implied = (fc_dir - draws) % 360.0          # true = forecast - error (N-43's sign lesson)
    samples = np.array([rng.choice(table[dbin(t)]) for t in implied])
    return float(np.percentile(samples, 90))


def phase1_auc_vs_lead(table, err_pool, thr, rng):
    out = {}
    for lead in sorted(err_pool):
        scores, labels = [], []
        for _ in range(N_AUC_TRIALS):
            true_dir = rng.uniform(0, 360)
            fc_dir = (true_dir + rng.choice(err_pool[lead])) % 360.0
            p90 = ensemble_p90(table, fc_dir, lead, err_pool, rng)
            truth = float(rng.choice(table[dbin(true_dir)]))
            scores.append(p90)
            labels.append(truth > thr)
        a = auc(scores, labels)
        # bootstrap CI on the AUC
        boots = []
        s_arr, l_arr = np.asarray(scores), np.asarray(labels)
        for _ in range(200):
            idx = rng.integers(0, len(s_arr), len(s_arr))
            b = auc(s_arr[idx], l_arr[idx])
            if b is not None:
                boots.append(b)
        out[lead] = {"auc": a, "ci_lo": float(np.percentile(boots, 2.5)),
                     "ci_hi": float(np.percentile(boots, 97.5)),
                     "base_rate": float(l_arr.mean())}
    return out


# ----------------------------------------------------------------- day generation
def make_days(table, err_pool, n_days, seed):
    """Each day: a true wind direction, a true peak hour, a realised rise, and the p90 the agent
    would observe at every decision hour (with lead-appropriate MEASURED forecast error)."""
    rng = np.random.default_rng(seed)
    days = []
    for _ in range(n_days):
        true_dir = rng.uniform(0, 360)
        peak_h = int(np.clip(round(rng.normal(PEAK_CENTRE_H, PEAK_SD_H)), 1, HORIZON_H))
        truth = float(rng.choice(table[dbin(true_dir)]))
        obs = {}
        for t in range(0, HORIZON_H + 1):
            lead = max(1, min(12, int(round(PEAK_CENTRE_H - t))))
            fc_dir = (true_dir + rng.choice(err_pool[lead])) % 360.0
            draws = rng.choice(err_pool[lead], size=N_ENSEMBLE, replace=True)
            implied = (fc_dir - draws) % 360.0
            samples = np.array([rng.choice(table[dbin(x)]) for x in implied])
            obs[t] = {"p90": float(np.percentile(samples, 90)),
                      "sd": float(samples.std(ddof=1)),
                      "lead": lead}
        days.append({"true_dir": true_dir, "peak_h": peak_h, "truth": truth, "obs": obs})
    return days


def day_cost(commit_t, day, thr, capacity=CAPACITY_RISE):
    """commit_t = None means never commit."""
    if commit_t is None:
        breach = day["truth"] > thr
        return C_EXCURSION if breach else 0.0
    online_t = commit_t + LEAD_H
    hours_run = max(0, HORIZON_H - online_t + 1)
    c = C_STAGE_FIXED + hours_run * C_STAGE_HR
    helped = online_t <= day["peak_h"]
    effective_thr = thr + (capacity if helped else 0.0)
    if day["truth"] > effective_thr:
        c += C_EXCURSION
    return c


# ----------------------------------------------------------------- policies
def policy_fixed_lead(day, hour, margin, thr):
    o = day["obs"][hour]
    return o["p90"] > thr + margin


def run_fixed(days, hour, margin, thr):
    costs, commits = [], []
    for d in days:
        if hour <= HORIZON_H and policy_fixed_lead(d, hour, margin, thr):
            costs.append(day_cost(hour, d, thr))
            commits.append(hour)
        else:
            costs.append(day_cost(None, d, thr))
            commits.append(None)
    return np.array(costs), commits


def tune_fixed(days, thr):
    best = (None, None, float("inf"))
    for h in range(0, HORIZON_H - LEAD_H + 1):
        for m in MARGINS:
            c, _ = run_fixed(days, h, float(m), thr)
            if c.mean() < best[2]:
                best = (h, float(m), c.mean())
    return best[0], best[1]


def fit_dp(train, thr, capacity, last_commit_h):
    """Regression-based (Longstaff-Schwartz-style) backward induction. Estimated on TRAIN only.

    REPLACES two earlier attempts, kept here as the record of why:
      attempt 1  a hand-written heuristic that was not a DP at all -- lost by 6.17 SE, degenerated
                 to 'commit at hour 0 whenever p90 > thr', the most expensive action available.
      attempt 2  a proper backward-induction DP over (hour, p90-quantile-bin) with a fitted
                 transition matrix. Found and fixed one real bug (the final hour's transition row
                 was never populated and silently defaulted to uniform, corrupting the whole
                 chain) -- but STILL lost, and lost worse (21.59 SE), with the loss unchanged by
                 20x more training data and fewer bins, which rules out sampling noise. The
                 adaptive policy was staging on MORE days (88.6% vs 65.5%) yet breaching MORE
                 often (21.2% vs 12.7%) than the simple fixed-hour rule -- a policy in the DP's
                 own search space cannot legitimately be beaten this badly by a correctly
                 specified DP, so a second defect was hiding in the binning/transition machinery
                 itself, not just the one already found.

    THE FIX: stop discretising the observable (p90) into bins and fitting a transition matrix
    between them at all -- that machinery is exactly where both defects lived. Instead, at each
    hour, fit two MONOTONIC regressions directly against the continuous p90 value, using
    scikit-learn's IsotonicRegression (a standard, tested implementation, not hand-rolled):

      1. breach probability given p90(t), with and without capacity -- monotonic by physical
         necessity (a higher ensemble p90 cannot correspond to LOWER breach risk), so a fitted
         curve that isn't monotonic would be an immediate, visible sign of a defect, unlike a
         count table where the same problem hides in the noise.
      2. the CONTINUATION value itself, via the Longstaff-Schwartz technique used for pricing
         American options under continuous state spaces: each training day already knows its own
         realised value if it followed the optimal policy from hour t+1 onward (computed in the
         previous backward step, per day, exactly -- no approximation). Regressing that per-day
         realised value against the OBSERVABLE p90(t) gives the expected continuation value as a
         function usable for decision-making, with no intermediate discretisation to get wrong.

    The terminal value (waiting past the last commit hour) needs no regression at all: it is
    exactly C_EXCURSION if truth > thr else 0, known per day with certainty, since "never commit"
    depends only on the realised truth, not on any observation.
    """
    peaks = np.array([d["peak_h"] for d in train])
    p_helped = {t: float((peaks >= t + LEAD_H).mean()) for t in range(last_commit_h + 1)}

    breach_no_fit, breach_yes_fit = {}, {}
    for t in range(last_commit_h + 1):
        x = np.array([d["obs"][t]["p90"] for d in train])
        y_no = np.array([float(d["truth"] > thr) for d in train])
        y_yes = np.array([float(d["truth"] > thr + capacity) for d in train])
        breach_no_fit[t] = IsotonicRegression(increasing=True, out_of_bounds="clip",
                                              y_min=0.0, y_max=1.0).fit(x, y_no)
        breach_yes_fit[t] = IsotonicRegression(increasing=True, out_of_bounds="clip",
                                               y_min=0.0, y_max=1.0).fit(x, y_yes)

    def commit_cost_fn(t, p90_arr):
        hours_run = max(0, HORIZON_H - (t + LEAD_H) + 1)
        ph = p_helped[t]
        exp_breach = (ph * breach_yes_fit[t].predict(p90_arr)
                     + (1 - ph) * breach_no_fit[t].predict(p90_arr))
        return C_STAGE_FIXED + hours_run * C_STAGE_HR + exp_breach * C_EXCURSION

    # terminal realised value: exact per day, no fitting needed
    truths = np.array([d["truth"] for d in train])
    Y_next = np.where(truths > thr, C_EXCURSION, 0.0)     # V at hour last_commit_h + 1, per day

    continuation_fit = {}
    for t in range(last_commit_h, -1, -1):
        p90_t = np.array([d["obs"][t]["p90"] for d in train])
        # fit E[Y_next | p90(t)] -- the Bellman continuation value, as a monotonic function of
        # the observable. Continuation cost cannot legitimately DECREASE as today's own risk
        # signal rises, so increasing=True is the correct constraint, not just a convenience.
        cont_fit = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(p90_t, Y_next)
        continuation_fit[t] = cont_fit
        c_act = commit_cost_fn(t, p90_t)
        c_wait = cont_fit.predict(p90_t)
        Y_next = np.minimum(c_act, c_wait)                # this day's realised value at hour t

    return {"commit_cost_fn": commit_cost_fn, "continuation_fit": continuation_fit,
            "last_commit_h": last_commit_h}


def run_adaptive(days, thr, dp, capacity=CAPACITY_RISE):
    """Apply the fitted policy. Pure function evaluation; no parameters touched at test time."""
    commit_cost_fn = dp["commit_cost_fn"]
    continuation_fit = dp["continuation_fit"]
    last_commit_h = dp["last_commit_h"]
    costs, commits = [], []
    for d in days:
        commit_t = None
        for t in range(last_commit_h + 1):
            p90 = np.array([d["obs"][t]["p90"]])
            c_act = float(commit_cost_fn(t, p90)[0])
            c_wait = float(continuation_fit[t].predict(p90)[0])
            if c_act <= c_wait:
                commit_t = t
                break
        costs.append(day_cost(commit_t, d, thr, capacity))
        commits.append(commit_t)
    return np.array(costs), commits


def off_modal_fraction(commits):
    fired = [c for c in commits if c is not None]
    if not fired:
        return 0.0, None, 0
    from collections import Counter
    cnt = Counter(fired)
    modal, modal_n = cnt.most_common(1)[0]
    return 1.0 - modal_n / len(fired), modal, len(fired)


# ----------------------------------------------------------------- main
def main():
    banner("N-44  adaptive commitment: is WHEN-to-commit a real sequential decision?  [FREE, GPU]")
    print("   Three decision cores already failed (N-25/N-40 measured, N-43 measured, N-42")
    print("   unresolvable on the calendar). This does NOT re-test 'waiting buys a tighter number'")
    print("   -- that is dead. It tests whether waiting buys DISCRIMINATING POWER (AUC), which")
    print("   sigma-in-Celsius was structurally blind to. P1 below can kill this outright.")

    err_pool, meta = load_dir_errors()
    print("\n   [1/4] measured wind-direction error: %s, %d days, leads %d-%d h"
          % (meta["station"], meta["n_days"], min(err_pool), max(err_pool)))
    print("      sd falls %.1f deg (12 h) -> %.1f deg (1 h). The INPUT sharpens; that is not in dispute."
          % (err_pool[12].std(ddof=1), err_pool[1].std(ddof=1)))

    print("\n   [2/4] GPU precompute: real physics, calibrated demo site, full 0-360 deg sweep")
    table, dirs = build_direction_table()
    allr = table.ravel()
    thr = float(np.percentile(allr, 75))
    print("      rise across all directions: min %.4f  median %.4f  p75 %.4f  max %.4f C"
          % (allr.min(), np.median(allr), thr, allr.max()))
    print("      threshold set at p75 = %.4f C, so the decision is non-trivial by construction" % thr)

    rng = np.random.default_rng(SEED)
    print("\n   [3/4] PHASE 1 (pre-registered gate): does DISCRIMINATING POWER improve with lead?")
    a_by_lead = phase1_auc_vs_lead(table, err_pool, thr, rng)
    print("      %6s %8s %22s %10s" % ("lead h", "AUC", "95 % bootstrap CI", "base rate"))
    for lead in sorted(a_by_lead, reverse=True):
        v = a_by_lead[lead]
        print("      %6d %8.4f   [%.4f, %.4f] %10.3f"
              % (lead, v["auc"], v["ci_lo"], v["ci_hi"], v["base_rate"]))
    a12, a1 = a_by_lead[12], a_by_lead[1]
    gain = a1["auc"] - a12["auc"]
    disjoint = a1["ci_lo"] > a12["ci_hi"]
    print("\n      AUC at 1 h minus AUC at 12 h = %+.4f" % gain)
    print("      CIs disjoint (1 h strictly above 12 h): %s" % disjoint)
    p1 = gain > P1_MIN_AUC_GAIN and disjoint
    print("      P1 (AUC must rise as lead shortens, CI-clear): %s" % p1)

    if not p1:
        print("\n   *** P1 FAILED. Waiting does not buy decision-relevant information either.")
        print("       That is the FOURTH independent decision core to fail on this data, and it is")
        print("       now measured three different ways (sigma in C, fleet ranking, and AUC).")
        print("       Do NOT build a stopping rule. Report the null.")
        save_result("n44_adaptive_commit.json", {
            "phase1_auc_by_lead": a_by_lead, "auc_gain_1h_vs_12h": gain,
            "cis_disjoint": bool(disjoint), "p1": False, "pass": False,
            "conclusion": "waiting buys no discriminating power; stopping rule not warranted"})
        return 1

    print("\n   [4/4] PHASE 2: adaptive commitment vs the best TUNED fixed-lead rule")
    train = make_days(table, err_pool, N_TRAIN, SEED + 1)
    test = make_days(table, err_pool, N_TEST, SEED + 2)
    h_star, m_star = tune_fixed(train, thr)
    adv_cost, adv_commits = run_fixed(test, h_star, m_star, thr)
    dp = fit_dp(train, thr, CAPACITY_RISE, HORIZON_H - LEAD_H)
    dp_cost, dp_commits = run_adaptive(test, thr, dp)
    g, se = paired(adv_cost, dp_cost)
    sigma = g / se if se > 0 else float("inf")
    off_modal, modal, n_fired = off_modal_fraction(dp_commits)
    adv_off_modal, adv_modal, adv_fired = off_modal_fraction(adv_commits)

    print("      adversary tuned on TRAIN: commit at hour %d if p90 > thr %+0.3f" % (h_star, m_star))
    print("      %-26s %10s %10s" % ("policy (HELD-OUT)", "mean cost", "commits"))
    print("      %-26s %10.4f %10d" % ("tuned fixed-lead", adv_cost.mean(), adv_fired))
    print("      %-26s %10.4f %10d" % ("adaptive (0 tuned params)", dp_cost.mean(), n_fired))
    print("      gain (paired) %+.4f +/- %.4f = %+.2f sigma" % (g, se, sigma))

    print("\n      P3 ANTI-THRESHOLD GUARD -- does the adaptive policy actually vary its timing?")
    print("         adaptive : modal commit hour %s, fires OFF it on %.1f %% of committing days"
          % (modal, 100 * off_modal))
    print("         adversary: modal commit hour %s by construction (%.1f %% off-modal)"
          % (adv_modal, 100 * adv_off_modal))

    p2 = sigma >= P2_MIN_SIGMA
    p3 = off_modal >= P3_MIN_OFF_MODAL
    ok = p1 and p2 and p3

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE ANY NUMBER WAS SEEN")
    print("      P1 AUC rises with shorter lead, CI-clear : %s (%+.4f)" % (p1, gain))
    print("      P2 beats tuned fixed-lead by >= %.1f SE  : %s (%+.2f)" % (P2_MIN_SIGMA, p2, sigma))
    print("      P3 fires off modal hour on >= %.0f %%     : %s (%.1f %%)"
          % (100 * P3_MIN_OFF_MODAL, p3, 100 * off_modal))
    print()
    verdict(ok,
            "PASS - waiting buys measured DISCRIMINATING POWER (AUC %+.4f higher at 1 h than 12 h, "
            "CIs disjoint), the adaptive policy beats an exhaustively tuned fixed-lead rule by "
            "%+.2f SE on %d held-out days with ZERO tuned parameters of its own, AND it genuinely "
            "varies its commitment hour (off-modal on %.1f %% of days) rather than collapsing to a "
            "constant. The decision is sequential and state-dependent, and every input driving it "
            "(peak_sd_h from N-38, wind error from N-40, ensemble spread from N-23) is measured."
            % (gain, sigma, N_TEST, 100 * off_modal),
            "FAIL - P1 %s, P2 %s (%+.2f SE), P3 %s (%.1f %% off-modal). If P3 is what failed, the "
            "policy found a CONSTANT and is a threshold in disguise -- exactly how N-9 v1 failed -- "
            "and a fixed rule is sufficient, so no agent is warranted on this decision. Report it "
            "that way." % (p1, p2, sigma, p3, 100 * off_modal))

    save_result("n44_adaptive_commit.json", {
        "why": "N-40 measured sigma-in-C inverting; AUC is the decision-relevant quantity that "
               "sigma-in-C is structurally blind to (dilution vs confidence)",
        "measured_inputs": {"peak_sd_h": PEAK_SD_H, "peak_sd_h_source": "N-38, 15 days",
                            "wind_error_source": meta,
                            "dir_sd_12h": float(err_pool[12].std(ddof=1)),
                            "dir_sd_1h": float(err_pool[1].std(ddof=1))},
        "threshold_rise_c": thr, "capacity_rise_c": CAPACITY_RISE,
        "phase1_auc_by_lead": a_by_lead, "auc_gain_1h_vs_12h": gain,
        "cis_disjoint": bool(disjoint),
        "adversary": {"hour": h_star, "margin": m_star, "test_cost": float(adv_cost.mean()),
                      "n_commits": adv_fired},
        "adaptive": {"test_cost": float(dp_cost.mean()), "n_commits": n_fired,
                     "modal_hour": modal, "off_modal_fraction": off_modal},
        "gain": g, "se": se, "sigma": sigma,
        "thresholds": {"p1_min_auc_gain": P1_MIN_AUC_GAIN, "p2_min_sigma": P2_MIN_SIGMA,
                       "p3_min_off_modal": P3_MIN_OFF_MODAL},
        "p1": bool(p1), "p2": bool(p2), "p3": bool(p3), "pass": bool(ok),
        "limits": "one site layout (N-28 showed layout sensitivity); persistence wind error is a "
                  "LOWER bound on forecast skill; simulated days with real solver physics"})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
