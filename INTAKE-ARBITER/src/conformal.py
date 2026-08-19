# -*- coding: utf-8 -*-
"""CONFORMAL PREDICTION, DONE THE WAY THE LITERATURE SAYS TO DO IT.

Run `python conformal.py` to execute the self-test suite at the bottom, which is the evidence
that these implementations are correct rather than merely present.

--------------------------------------------------------------------------------------------
WHY THIS FILE EXISTS -- the defect it repairs
--------------------------------------------------------------------------------------------
The first version of the agent calibrated its safety margin on FOUR residuals, all taken from
ONE hour-of-day (14:00) at ONE forecast lead (~9.4 h), and then applied that margin to every
hour of the day at leads of 0 to 6 h.

Conformal prediction's guarantee requires EXCHANGEABILITY: the calibration examples and the new
case must be interchangeable, like cards drawn from one shuffled deck. A 14:00 residual at 9.4 h
lead is not interchangeable with an 04:00 residual at 3 h lead -- the error of a temperature
forecast depends on both the time of day and how far ahead you asked. So the old bound was not
merely "marginal instead of conditional"; it was applied OUTSIDE THE DOMAIN IT WAS CALIBRATED ON.

--------------------------------------------------------------------------------------------
THE THREE LEVELS OF GUARANTEE, and which one is achievable
--------------------------------------------------------------------------------------------
  1. MARGINAL          right (1-alpha) of the time, averaged over all hours.
                       Cheap, and what a naive split-conformal gives you.

  2. GROUP-CONDITIONAL right (1-alpha) of the time WITHIN EVERY GROUP -- each hour-of-day, each
     (MONDRIAN)        lead, each wind regime. ACHIEVABLE. Vovk, "Conditional validity of
                       inductive conformal predictors", ACML 2012, PMLR 25:475-490.
                       *** THIS IS WHAT WE BUILD. ***

  3. FULL CONDITIONAL  right (1-alpha) for every individual case given its exact covariates.
                       *** PROVABLY IMPOSSIBLE *** distribution-free in finite samples --
                       Barber, Candes, Ramdas & Tibshirani, "The limits of distribution-free
                       conditional predictive inference", Information and Inference 10(2):
                       455-482, 2021.  https://arxiv.org/abs/1903.04684

So "make it right for every hour" in the strictest sense is forbidden by a theorem. We build the
strongest thing that is not forbidden, and we say which one we shipped.

--------------------------------------------------------------------------------------------
WHAT ELSE IS IN HERE, AND WHY EACH PIECE IS NEEDED
--------------------------------------------------------------------------------------------
* `convolved_upper` -- the agent's error has TWO components (a whole-day level offset from
  FortyGuard, and an hour-to-hour shape error). Adding two (1-alpha) bounds guarantees only
  1-2*alpha by Bonferroni: two 90 % bounds give 80 %. Convolving the two empirical error
  distributions and taking one quantile of the SUM recovers the real (1-alpha). Costs an
  independence assumption, which is stated at the call site rather than buried.

* `NormalizedConformal` -- a constant-width margin is wasteful where the physics is confident
  and dangerous where it is not. Dividing the residual by a per-case difficulty estimate makes
  the interval breathe. Romano, Patterson & Candes, "Conformalized Quantile Regression",
  NeurIPS 2019, arXiv:1905.03222. Our difficulty estimate is the dispersion ensemble's spread,
  which is measured 27x wider at the geometric edge than in a safe sector.

* `ACI` / `DtACI` -- weather drifts, so exchangeability fails no matter how we stratify.
  Adaptive Conformal Inference adjusts alpha online and guarantees LONG-RUN coverage WITHOUT
  exchangeability. Gibbs & Candes, NeurIPS 2021 (arXiv:2106.00170); DtACI in JMLR 25 (2024),
  paper 22-1218. Also Zaffran et al., ICML 2022, PMLR 162:25834-25866 (AgACI), whose
  application is electricity-price forecasting -- structurally close to ours.

* `joint_upper` -- the agent COMMITS TO A MODE FOR SEVERAL HOURS. Per-hour 90 % coverage does
  not give 90 % coverage across the whole committed run. A max-over-horizon nonconformity score
  gives simultaneous coverage. Stankeviciute, Alaa & van der Schaar, "Conformal Time-Series
  Forecasting", NeurIPS 2021.

* `coverage_by_group` -- reporting one average coverage number hides exactly the groups where a
  controller is dangerous. Every report here carries the WORST group, not just the mean.

Primary text throughout: Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction
and Distribution-Free Uncertainty Quantification", arXiv:2107.07511.
"""
import math

import numpy as np

ALPHA = 0.10


# ============================================================================
# The one-sided upper quantile, and the small-sample truth about it
# ============================================================================
def quantile_index(n, alpha=ALPHA):
    """k = ceil((n+1)(1-alpha)), and whether it had to be clamped to n.

    If k > n there IS no k-th smallest residual. Implementations silently clamp to the maximum,
    which quietly degrades the guarantee -- so this returns the clamp flag and callers must
    report it. At alpha=0.10 you need n >= 9 before a 90 % bound is even arithmetically
    possible; below that the best attainable coverage is n/(n+1).
    """
    k = math.ceil((n + 1) * (1.0 - alpha))
    return min(k, n), bool(k > n)


def attainable_coverage(n):
    """The arithmetic ceiling on coverage from n exchangeable calibration points: n/(n+1)."""
    return n / (n + 1.0) if n > 0 else 0.0


def min_n_for(alpha=ALPHA):
    """Smallest calibration set for which (1-alpha) is attainable at all."""
    return int(math.ceil(1.0 / alpha) - 1)


def split_conformal(res, alpha=ALPHA):
    """One-sided upper conformal quantile of `res`, with its own honesty attached."""
    r = np.sort(np.asarray(res, dtype=float))
    r = r[~np.isnan(r)]
    n = len(r)
    if n == 0:
        return {"q": float("nan"), "n": 0, "k": 0, "clamped": True, "ceiling": 0.0,
                "nominal": 1.0 - alpha}
    k, clamped = quantile_index(n, alpha)
    return {"q": float(r[k - 1]), "n": int(n), "k": int(k), "clamped": clamped,
            "ceiling": attainable_coverage(n), "nominal": 1.0 - alpha}


# ============================================================================
# MONDRIAN / group-conditional conformal  -- Vovk 2012
# ============================================================================
class Mondrian:
    """A separate conformal quantile per group, so the guarantee holds within each group.

    A group with too few points cannot support the quantile. Rather than silently returning a
    clamped value -- which is the exact failure mode this class was written to remove -- such a
    group FALLS BACK to the pooled quantile and the fallback is recorded and reported. Every
    caller can see how much of its coverage is genuinely group-conditional and how much is not.
    """

    def __init__(self, alpha=ALPHA, min_n=None):
        self.alpha = alpha
        self.min_n = min_n if min_n is not None else min_n_for(alpha)
        self.groups_ = {}
        self.pooled_ = None
        self.fallbacks_ = []

    def fit(self, groups, res):
        groups = np.asarray(groups)
        res = np.asarray(res, dtype=float)
        ok = ~np.isnan(res)
        groups, res = groups[ok], res[ok]
        self.pooled_ = split_conformal(res, self.alpha)
        self.groups_, self.fallbacks_ = {}, []
        for g in np.unique(groups):
            sub = res[groups == g]
            key = g.item() if hasattr(g, "item") else g
            if len(sub) < self.min_n:
                self.fallbacks_.append((key, int(len(sub))))
                continue
            self.groups_[key] = split_conformal(sub, self.alpha)
        return self

    def q(self, group):
        """(quantile, n, source) where source is 'group' or 'pooled-fallback'."""
        if group in self.groups_:
            c = self.groups_[group]
            return c["q"], c["n"], "group"
        return self.pooled_["q"], self.pooled_["n"], "pooled-fallback"

    def q_array(self, groups):
        return np.array([self.q(g)[0] for g in groups], dtype=float)

    def summary(self):
        return {
            "alpha": self.alpha, "min_n_per_group": self.min_n,
            "n_groups_fitted": len(self.groups_),
            "n_groups_fallback": len(self.fallbacks_),
            "fallback_groups": self.fallbacks_[:50],
            "pooled": self.pooled_,
            "any_group_clamped": any(c["clamped"] for c in self.groups_.values()),
            "smallest_group_n": (min(c["n"] for c in self.groups_.values())
                                 if self.groups_ else 0),
            "group_q_min": (min(c["q"] for c in self.groups_.values())
                            if self.groups_ else float("nan")),
            "group_q_max": (max(c["q"] for c in self.groups_.values())
                            if self.groups_ else float("nan")),
        }


# ============================================================================
# The SUM of two error components, without the Bonferroni penalty
# ============================================================================
def convolved_upper(a, b, alpha=ALPHA, max_pairs=4_000_000, seed=0):
    """(1-alpha) upper quantile of A+B from the empirical convolution of the two samples.

    WHY NOT JUST ADD THE TWO QUANTILES. q(A) + q(B) is a valid bound only in the Bonferroni
    sense: each component fails at most alpha of the time, so the sum fails at most 2*alpha.
    Two 90 % bounds therefore deliver 80 %. Convolving recovers the true (1-alpha).

    THE ASSUMPTION, STATED: this treats A and B as INDEPENDENT. In our use A is FortyGuard's
    whole-day level offset and B is the hour-to-hour shape error, which are plausibly but not
    provably independent. If they are positively dependent this UNDER-estimates the quantile,
    so `bonferroni` is returned alongside for comparison and the caller can choose the
    conservative one.
    """
    a = np.asarray(a, dtype=float); a = a[~np.isnan(a)]
    b = np.asarray(b, dtype=float); b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return {"q": float("nan"), "n_pairs": 0, "exact": False,
                "bonferroni": float("nan"), "saving_c": float("nan")}
    if len(a) * len(b) <= max_pairs:
        s = (a[:, None] + b[None, :]).ravel()
        exact = True
    else:
        rng = np.random.default_rng(seed)
        m = max_pairs
        s = a[rng.integers(0, len(a), m)] + b[rng.integers(0, len(b), m)]
        exact = False
    c = split_conformal(s, alpha)
    bon = split_conformal(a, alpha)["q"] + split_conformal(b, alpha)["q"]
    return {"q": c["q"], "n_pairs": int(len(s)), "exact": exact, "k": c["k"],
            "bonferroni": float(bon), "saving_c": float(bon - c["q"]),
            "guarantee": "1-alpha under independence of the two components",
            "bonferroni_guarantee": 1.0 - 2.0 * alpha}


# ============================================================================
# NORMALIZED (adaptive-width) conformal  -- Romano et al. 2019
# ============================================================================
class NormalizedConformal:
    """Interval width proportional to a per-case difficulty estimate.

    score = residual / difficulty; the conformal quantile of the score is a MULTIPLIER, so the
    margin for a new case is multiplier * difficulty(new case). Narrow where the model is
    confident, wide where it is not -- with the same marginal guarantee as a fixed width.

    Our difficulty signal is the dispersion ensemble's standard deviation, which is a physical
    quantity, not a fitted one: it is measured 27x wider at the geometric edge of the plume than
    in a safe sector, and no plume rule exists anywhere in the solver source that would produce
    that. `floor` prevents a near-zero difficulty from exploding the score.
    """

    def __init__(self, alpha=ALPHA, floor=1e-3):
        self.alpha = alpha
        self.floor = floor
        self.mult_ = None
        self.cal_ = None

    def fit(self, res, difficulty):
        res = np.asarray(res, dtype=float)
        d = np.maximum(np.asarray(difficulty, dtype=float), self.floor)
        ok = ~np.isnan(res) & ~np.isnan(d)
        self.cal_ = split_conformal(res[ok] / d[ok], self.alpha)
        self.mult_ = self.cal_["q"]
        return self

    def margin(self, difficulty):
        d = np.maximum(np.asarray(difficulty, dtype=float), self.floor)
        return self.mult_ * d

    def summary(self):
        return {"multiplier": self.mult_, "calibration": self.cal_, "floor": self.floor}


# ============================================================================
# ADAPTIVE CONFORMAL INFERENCE  -- Gibbs & Candes 2021 / JMLR 2024
# ============================================================================
class ACI:
    """Online alpha adaptation. Guarantees LONG-RUN coverage WITHOUT exchangeability.

        alpha_{t+1} = alpha_t + gamma * (alpha_target - 1{the interval missed at t})

    Miss -> alpha shrinks -> the interval widens. Cover -> alpha grows -> it tightens. The
    running average of realised coverage converges to 1 - alpha_target at rate O(1/T)
    regardless of how the distribution drifts, which is exactly the failure mode that broke
    the static bound: weather is not exchangeable across days.

    Gibbs & Candes, "Adaptive Conformal Inference Under Distribution Shift", NeurIPS 2021.
    """

    def __init__(self, alpha=ALPHA, gamma=0.02, clip=(1e-4, 0.5)):
        self.alpha_target = alpha
        self.gamma = gamma
        self.clip = clip
        self.alpha_t = alpha
        self.history = []

    def step(self, missed):
        """Record the outcome of the interval just used, then return the NEXT alpha."""
        self.history.append({"alpha_used": self.alpha_t, "missed": bool(missed)})
        self.alpha_t = float(np.clip(
            self.alpha_t + self.gamma * (self.alpha_target - (1.0 if missed else 0.0)),
            self.clip[0], self.clip[1]))
        return self.alpha_t

    def realised_coverage(self):
        if not self.history:
            return float("nan")
        return 1.0 - sum(h["missed"] for h in self.history) / len(self.history)


class DtACI:
    """ACI with several learning rates run as competing experts, aggregated by exponential
    weighting -- removes the need to pick gamma by hand.

    Gibbs & Candes, "Conformal Inference for Online Prediction with Arbitrary Distribution
    Shifts", JMLR 25 (2024), paper 22-1218. Cite the JMLR version, not the arXiv preprint.
    """

    def __init__(self, alpha=ALPHA, gammas=(0.001, 0.005, 0.02, 0.08, 0.32), eta=2.0):
        self.alpha_target = alpha
        self.experts = [ACI(alpha, g) for g in gammas]
        self.gammas = list(gammas)
        self.w = np.ones(len(gammas)) / len(gammas)
        self.eta = eta
        self.history = []

    @property
    def alpha_t(self):
        return float(np.dot(self.w, [e.alpha_t for e in self.experts]))

    def step(self, missed):
        a_used = self.alpha_t
        # pinball-style loss per expert: penalise being on the wrong side of the outcome
        loss = np.array([abs((1.0 if missed else 0.0) - self.alpha_target)
                         if (e.alpha_t < self.alpha_target) == bool(missed)
                         else abs(e.alpha_t - self.alpha_target)
                         for e in self.experts])
        self.w = self.w * np.exp(-self.eta * loss)
        s = self.w.sum()
        self.w = (self.w / s) if s > 0 else np.ones(len(self.experts)) / len(self.experts)
        for e in self.experts:
            e.step(missed)
        self.history.append({"alpha_used": a_used, "missed": bool(missed)})
        return self.alpha_t

    def realised_coverage(self):
        if not self.history:
            return float("nan")
        return 1.0 - sum(h["missed"] for h in self.history) / len(self.history)


# ============================================================================
# JOINT coverage across a committed multi-hour run
# ============================================================================
def joint_upper(res_runs, alpha=ALPHA):
    """Simultaneous coverage over every hour of a committed run.

    Per-hour 90 % coverage does NOT give 90 % that all hours of a multi-hour commitment hold.
    The nonconformity score here is the MAXIMUM residual within a run, so one quantile of that
    score bounds the whole run at once -- much tighter than Bonferroni-in-time (alpha/H), which
    ignores the strong positive correlation between consecutive hours.

    `res_runs` is (n_runs, run_length). Stankeviciute, Alaa & van der Schaar, NeurIPS 2021.
    """
    R = np.asarray(res_runs, dtype=float)
    if R.ndim == 1:
        R = R[None, :]
    with np.errstate(invalid="ignore"):
        worst = np.nanmax(R, axis=1)
    c = split_conformal(worst, alpha)
    H = R.shape[1]
    per_hour = split_conformal(R[~np.isnan(R)].ravel(), alpha)["q"]
    bonf_in_time = split_conformal(R[~np.isnan(R)].ravel(), alpha / max(H, 1))["q"]
    return {"q_joint": c["q"], "n_runs": c["n"], "run_length": int(H),
            "q_per_hour": per_hour, "q_bonferroni_in_time": bonf_in_time,
            "clamped": c["clamped"]}


# ============================================================================
# Coverage diagnostics -- the worst group, never only the mean
# ============================================================================
def coverage_by_group(groups, res, q_of_group, target=1.0 - ALPHA):
    """Realised coverage overall AND within each group, plus the worst group.

    A single average coverage number hides the groups in which a controller is unsafe. This is
    the diagnostic the literature calls for (Angelopoulos & Bates, coverage-by-slice) and the
    one the old implementation lacked.
    """
    groups = np.asarray(groups)
    res = np.asarray(res, dtype=float)
    ok = ~np.isnan(res)
    groups, res = groups[ok], res[ok]
    q = np.array([q_of_group(g) for g in groups], dtype=float)
    covered = res <= q
    rows = []
    for g in np.unique(groups):
        m = groups == g
        rows.append({"group": g.item() if hasattr(g, "item") else g,
                     "n": int(m.sum()), "coverage": float(covered[m].mean()),
                     "q": float(q[m][0])})
    rows.sort(key=lambda r: r["coverage"])
    worst = rows[0] if rows else None
    return {"overall_coverage": float(covered.mean()), "n": int(len(res)),
            "target": target, "n_groups": len(rows),
            "worst_group": worst,
            "groups_below_target": sum(1 for r in rows if r["coverage"] < target),
            "groups_below_target_minus_2pp": sum(1 for r in rows
                                                 if r["coverage"] < target - 0.02),
            "per_group": rows}


# ============================================================================
# SELF-TEST -- the evidence that the above is correct, not merely present
# ============================================================================
def _selftest():
    rng = np.random.default_rng(7)
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        print("   [%s] %-58s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("=" * 78)
    print("CONFORMAL SELF-TEST")
    print("=" * 78)

    # ---- 1. marginal validity of plain split conformal
    print("\n1. Split conformal reaches nominal coverage when exchangeability HOLDS")
    cal, test = rng.normal(0, 1, 5000), rng.normal(0, 1, 20000)
    q = split_conformal(cal, 0.10)["q"]
    cov = float((test <= q).mean())
    check("marginal coverage within 1 pp of 90 %", abs(cov - 0.90) < 0.01, "%.4f" % cov)

    # ---- 2. the small-sample ceiling is real
    print("\n2. The n/(n+1) ceiling is real, not a formality")
    c3 = split_conformal(rng.normal(0, 1, 3), 0.10)
    check("n=3 clamps and admits it", c3["clamped"] and abs(c3["ceiling"] - 0.75) < 1e-12,
          "ceiling %.3f" % c3["ceiling"])
    check("n=9 is the first n that needs no clamp",
          not split_conformal(rng.normal(0, 1, 9), 0.10)["clamped"]
          and split_conformal(rng.normal(0, 1, 8), 0.10)["clamped"], "min_n=%d" % min_n_for(0.10))

    # ---- 3. THE CORE CLAIM: pooling across groups breaks group coverage; Mondrian fixes it
    print("\n3. Groups with different error scales: pooled FAILS, Mondrian HOLDS")
    scales = {0: 0.3, 1: 1.0, 2: 3.0}          # e.g. three hour-of-day regimes
    g_cal = rng.integers(0, 3, 9000)
    r_cal = rng.normal(0, 1, 9000) * np.array([scales[g] for g in g_cal])
    g_te = rng.integers(0, 3, 30000)
    r_te = rng.normal(0, 1, 30000) * np.array([scales[g] for g in g_te])

    q_pool = split_conformal(r_cal, 0.10)["q"]
    pooled_cov = {g: float((r_te[g_te == g] <= q_pool).mean()) for g in (0, 1, 2)}
    m = Mondrian(0.10).fit(g_cal, r_cal)
    mond_cov = {g: float((r_te[g_te == g] <= m.q(g)[0]).mean()) for g in (0, 1, 2)}
    print("      pooled  per-group coverage: " + "  ".join("g%d %.3f" % (g, pooled_cov[g])
                                                          for g in (0, 1, 2)))
    print("      Mondrian per-group coverage: " + "  ".join("g%d %.3f" % (g, mond_cov[g])
                                                           for g in (0, 1, 2)))
    check("pooled leaves at least one group badly under-covered",
          min(pooled_cov.values()) < 0.85, "worst %.3f" % min(pooled_cov.values()))
    check("Mondrian holds >= 88 % in EVERY group",
          min(mond_cov.values()) >= 0.88, "worst %.3f" % min(mond_cov.values()))
    check("Mondrian is not just wider everywhere -- it is TIGHTER in the easy group",
          m.q(0)[0] < q_pool, "g0 %.3f vs pooled %.3f" % (m.q(0)[0], q_pool))

    # ---- 4. small groups fall back, and say so
    print("\n4. A group too small to support the quantile falls back and IS FLAGGED")
    g_small = np.concatenate([np.zeros(200, int), np.full(4, 1)])
    r_small = np.concatenate([rng.normal(0, 1, 200), rng.normal(0, 1, 4)])
    ms = Mondrian(0.10).fit(g_small, r_small)
    check("undersized group is reported as a fallback, not silently clamped",
          ms.summary()["n_groups_fallback"] == 1 and ms.q(1)[2] == "pooled-fallback",
          "fallbacks %s" % (ms.summary()["fallback_groups"],))

    # ---- 5. convolution beats Bonferroni and still covers
    print("\n5. Convolved quantile of a SUM: valid, and tighter than Bonferroni")
    A, B = rng.normal(0, 1, 4000), rng.normal(0, 1, 4000)
    conv = convolved_upper(A, B, 0.10, max_pairs=2_000_000)
    te = rng.normal(0, 1, 40000) + rng.normal(0, 1, 40000)
    cov_conv = float((te <= conv["q"]).mean())
    cov_bonf = float((te <= conv["bonferroni"]).mean())
    print("      convolved q %.4f -> coverage %.4f    Bonferroni q %.4f -> coverage %.4f"
          % (conv["q"], cov_conv, conv["bonferroni"], cov_bonf))
    check("convolved coverage is at nominal (within 1 pp)", abs(cov_conv - 0.90) < 0.01,
          "%.4f" % cov_conv)
    check("Bonferroni is conservative, i.e. over-covers", cov_bonf > 0.93, "%.4f" % cov_bonf)
    check("convolution is strictly tighter", conv["saving_c"] > 0,
          "saves %.4f C of margin" % conv["saving_c"])

    # ---- 6. normalized conformal adapts width to difficulty
    print("\n6. Normalized score gives width proportional to difficulty")
    diff_cal = rng.uniform(0.2, 4.0, 8000)
    r_ncal = rng.normal(0, 1, 8000) * diff_cal
    nc = NormalizedConformal(0.10).fit(r_ncal, diff_cal)
    diff_te = rng.uniform(0.2, 4.0, 30000)
    r_nte = rng.normal(0, 1, 30000) * diff_te
    cov_n = float((r_nte <= nc.margin(diff_te)).mean())
    fixed_q = split_conformal(r_ncal, 0.10)["q"]
    easy = diff_te < 1.0
    check("normalized coverage at nominal", abs(cov_n - 0.90) < 0.015, "%.4f" % cov_n)
    check("fixed-width under-covers the HARD cases",
          float((r_nte[~easy] <= fixed_q).mean()) < 0.90,
          "hard-case coverage %.4f" % float((r_nte[~easy] <= fixed_q).mean()))
    check("normalized margin is smaller on easy cases",
          nc.margin(diff_te[easy]).mean() < fixed_q,
          "%.3f vs %.3f" % (nc.margin(diff_te[easy]).mean(), fixed_q))

    # ---- 7. ACI recovers coverage under drift, where a static bound cannot
    print("\n7. Under DRIFT, a static bound fails and ACI recovers")
    T = 4000
    drift = np.concatenate([rng.normal(0, 1, T // 2), rng.normal(2.5, 1, T - T // 2)])
    static_q = split_conformal(rng.normal(0, 1, 2000), 0.10)["q"]
    static_cov = float((drift <= static_q).mean())

    aci, hist = ACI(0.10, gamma=0.05), []
    pool = list(rng.normal(0, 1, 200))
    for t in range(T):
        a = aci.alpha_t
        qt = split_conformal(np.array(pool[-500:]), a)["q"]
        missed = drift[t] > qt
        hist.append(not missed)
        aci.step(missed)
        pool.append(drift[t])
    aci_cov = float(np.mean(hist))
    aci_cov_2nd = float(np.mean(hist[T // 2:]))
    print("      static bound coverage over the drift: %.4f" % static_cov)
    print("      ACI coverage overall %.4f   after the shift %.4f" % (aci_cov, aci_cov_2nd))
    check("static bound is badly broken by the shift", static_cov < 0.80, "%.4f" % static_cov)
    check("ACI long-run coverage lands near 90 %", abs(aci_cov - 0.90) < 0.03, "%.4f" % aci_cov)
    # exercise the class's own accessor too -- an untested public method is a liability, and this
    # is cheaper than deleting a sensible one
    check("ACI.realised_coverage() agrees with the externally counted rate",
          abs(aci.realised_coverage() - aci_cov) < 1e-12,
          "%.6f vs %.6f" % (aci.realised_coverage(), aci_cov))
    check("ACI still near target AFTER the shift", aci_cov_2nd > 0.84, "%.4f" % aci_cov_2nd)

    dt = DtACI(0.10)
    pool2 = list(rng.normal(0, 1, 200)); h2 = []
    for t in range(T):
        qt = split_conformal(np.array(pool2[-500:]), dt.alpha_t)["q"]
        missed = drift[t] > qt
        h2.append(not missed); dt.step(missed); pool2.append(drift[t])
    check("DtACI also lands near target with no hand-tuned gamma",
          abs(float(np.mean(h2)) - 0.90) < 0.04, "%.4f" % float(np.mean(h2)))
    check("DtACI.realised_coverage() agrees with the externally counted rate",
          abs(dt.realised_coverage() - float(np.mean(h2))) < 1e-12,
          "%.6f" % dt.realised_coverage())

    # ---- 8. joint coverage over a committed run
    print("\n8. Joint coverage over a multi-hour commitment")
    H = 6
    base = rng.normal(0, 1, (3000, 1))
    runs = base + rng.normal(0, 0.3, (3000, H))          # correlated within a run
    j = joint_upper(runs, 0.10)
    tbase = rng.normal(0, 1, (8000, 1))
    truns = tbase + rng.normal(0, 0.3, (8000, H))
    joint_cov = float((truns.max(axis=1) <= j["q_joint"]).mean())
    perhour_joint = float((truns.max(axis=1) <= j["q_per_hour"]).mean())
    print("      per-hour q %.4f gives JOINT coverage %.4f" % (j["q_per_hour"], perhour_joint))
    print("      joint    q %.4f gives JOINT coverage %.4f" % (j["q_joint"], joint_cov))
    check("a per-hour quantile does NOT deliver joint coverage", perhour_joint < 0.90,
          "%.4f" % perhour_joint)
    check("the max-over-horizon score DOES", abs(joint_cov - 0.90) < 0.02, "%.4f" % joint_cov)
    check("and it beats Bonferroni-in-time on width",
          j["q_joint"] < j["q_bonferroni_in_time"],
          "%.3f vs %.3f" % (j["q_joint"], j["q_bonferroni_in_time"]))

    # ---- 9. the diagnostic reports the worst group
    print("\n9. Coverage diagnostics surface the WORST group, not the mean")
    rep = coverage_by_group(g_te, r_te, lambda g: q_pool)
    check("pooled bound looks acceptable on average but has a failing group",
          rep["overall_coverage"] > 0.85 and rep["worst_group"]["coverage"] < 0.85,
          "overall %.3f worst g%s %.3f" % (rep["overall_coverage"],
                                          rep["worst_group"]["group"],
                                          rep["worst_group"]["coverage"]))

    print("\n" + "=" * 78)
    print("SELF-TEST %s" % ("PASSED -- every claim above is reproducible by rerunning this file"
                            if ok_all else "FAILED -- do not use these results"))
    print("=" * 78)
    return 0 if ok_all else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
