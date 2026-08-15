# -*- coding: utf-8 -*-
"""Online stopping rule for cooling-plant staging.  FREE, no API calls.

Replaces the three if-statements at the end of run_e2e.py with a genuine sequential
decision under uncertainty.

THE DECISION
    Extra cooling capacity -- another chiller, another tower cell, a CRAH bank, or a
    changeover from free cooling to mechanical -- needs LEAD_H hours of notice before it
    is actually doing work, and it burns energy for every hour it runs. Once each hour,
    the agent chooses:  STAGE (irreversible) or WAIT.

WHY WAITING HAS VALUE
    Two reasons, and both are quantitative:
      1. Forecast error shrinks as the target hour approaches, so deferring buys a
         TIGHTER bound on the peak.
      2. Staging later costs less, because the extra plant runs for fewer hours.

WHY WAITING HAS RISK
    Capacity needs LEAD_H hours of notice. After t > peak_hour - LEAD_H the peak can no
    longer be protected at all, and an unprotected thermal excursion costs far more than
    the wasted energy ever would.

WHY THIS IS NOT A THRESHOLD
    The right action at hour t depends on the value of information the NEXT forecast will
    bring, which depends on how much lead time is left to exploit it. A threshold on
    today's bound cannot express that -- it has no representation of "how much better will
    I know this in three hours, and will I still be able to act on it?"  So the rule is
    obtained by backward induction over the 12-hour horizon FortyGuard actually serves.

TAGS
    [M] measured from the saved FortyGuard fixtures.  [S] plant stub -- a documented
    placeholder with no measurement behind it, swept in test_n9_staging.py.
"""
import math
import numpy as np

# ----------------------------------------------------------------- normal helpers
SQRT2 = math.sqrt(2.0)


def phi(z):
    """Standard normal CDF, vectorised."""
    z = np.asarray(z, dtype=np.float64)
    return 0.5 * (1.0 + np.vectorize(math.erf)(z / SQRT2))


def p_exceed(mu, sigma, x):
    """P(theta > x) for theta ~ N(mu, sigma^2)."""
    sigma = max(float(sigma), 1e-9)
    return 1.0 - phi((x - np.asarray(mu, dtype=np.float64)) / sigma)


# ----------------------------------------------------------------- calibration
def conformal_halfwidth(residuals, alpha=0.10):
    """One-sided split-conformal half-width: ceil((n+1)(1-alpha))-th smallest |residual|.

    The small-sample penalty lives in the formula, not in a fudge factor. Returns
    (halfwidth, n) or (None, n) if n is too small for the requested alpha.
    """
    r = sorted(abs(float(x)) for x in residuals if x is not None)
    n = len(r)
    if n < int(1.0 / alpha) - 1:
        return None, n
    k = min(n - 1, math.ceil((n + 1) * (1.0 - alpha)) - 1)
    return r[k], n


def sigma_schedule(max_lead, sigma_anchor, anchor_lead, exponent=0.5, floor=0.05):
    """Forecast error sd as a function of lead time, in hours.

    [M] anchored: sigma(anchor_lead) == sigma_anchor, taken from the measured
        forecast-vs-outcome residuals in the saved fixtures.
    [S] shape:    sigma(l) = sigma_anchor * (l / anchor_lead) ** exponent

    The exponent is a MODEL, not a measurement -- the heatmap aggregates over the
    requested window, so per-lead-time residuals cannot be recovered from the fixtures
    we already hold. exponent=0.5 is the random-walk value. test_n9_staging.py sweeps it
    from 0.0 (no tightening at all -- the pessimistic case that removes the entire value
    of waiting) to 1.0, and the conclusion must survive the whole range.

    Returns array indexed by lead time 0..max_lead.
    """
    out = np.zeros(max_lead + 1)
    for l in range(max_lead + 1):
        if l <= 0:
            out[l] = floor
        else:
            out[l] = max(floor, sigma_anchor * (l / float(anchor_lead)) ** exponent)
    return out


# ----------------------------------------------------------------- problem spec
def peak_hour_pmf(horizon_h=12, centre_h=8.0, sd_h=1.5):
    """[S] Distribution over WHICH hour the daily peak lands on.

    This is the piece that makes the problem a real stopping problem rather than a race to
    a known wall. You do not know exactly when the hottest hour will arrive, so deferring
    is not free: if the peak comes earlier than expected, the lead time you were saving no
    longer exists and the capacity arrives after the event.

    sd_h is a stub, but a CHEAPLY SETTLED one: FortyGuard's `time_of_measure` analytic type
    returns the hour at which each tile's maximum occurred, so the forecast-vs-outcome error
    on peak hour is directly measurable. That is a one-call test on Aug 18.
    """
    h = np.arange(horizon_h, dtype=np.float64)
    w = np.exp(-0.5 * ((h - centre_h) / max(sd_h, 1e-6)) ** 2)
    return w / w.sum()


class Spec:
    """A staging problem for one facility on one day.

    thr_c        [S] intake temperature above which the plant is capacity-limited
    capacity_c   [S] how much headroom staging the extra train buys
    lead_h       [S] hours of notice the extra capacity needs before it is effective
    horizon_h    [M] decision epochs available -- 12, because that is FortyGuard's horizon
    end_h            hour the elevated period ends (staged plant runs until then)
    c_stage_hr   [S] energy cost of running the extra train, per hour, arbitrary units
    c_excursion  [S] cost of an unprotected excursion, same units
    bias_c       [M] signed mean forecast error, removed before deciding
    pmf          [S] distribution over the peak hour (see peak_hour_pmf)
    """

    def __init__(self, thr_c=33.0, capacity_c=1.5, lead_h=3, horizon_h=12, end_h=12,
                 c_stage_hr=1.0, c_stage_fixed=2.0, c_excursion=120.0, bias_c=0.0,
                 peak_sd_h=1.5, peak_centre_h=8.0):
        self.thr_c = float(thr_c)
        self.capacity_c = float(capacity_c)
        self.lead_h = int(lead_h)
        self.horizon_h = int(horizon_h)
        self.end_h = int(end_h)
        self.c_stage_hr = float(c_stage_hr)
        self.c_stage_fixed = float(c_stage_fixed)
        self.c_excursion = float(c_excursion)
        self.bias_c = float(bias_c)
        self.peak_centre_h = float(peak_centre_h)
        self.peak_sd_h = float(peak_sd_h)
        self.pmf = peak_hour_pmf(horizon_h, peak_centre_h, peak_sd_h)

    @property
    def last_epoch(self):
        """Staging remains *possible* right to the end of the horizon; whether it is ever
        worth it that late is for the solver to decide, not for us to hard-code."""
        return self.horizon_h - 1

    def protect_prob(self, t):
        """P(the peak arrives at or after t + lead_h) -- i.e. staging at t actually helps.

        Decreasing in t. This is the risk of waiting, and it is what the old formulation
        was missing: there it was a step function (1 up to the wall, 0 after), so waiting
        to the wall was free.
        """
        first = t + self.lead_h
        if first >= self.horizon_h:
            return 0.0
        return float(self.pmf[first:].sum())

    def stage_cost(self, t):
        """Fixed commitment cost plus hourly running from t+lead_h until end_h.

        c_stage_fixed matters more than it looks: without it, staging in the last few hours
        costs nothing, so the solver becomes indifferent and "stages" as a free no-op that
        cannot possibly help. Starting a chiller has a real fixed cost -- inrush, start
        wear, minimum run time -- so the fixed term is physical, not a numerical patch.
        """
        return self.c_stage_fixed + self.c_stage_hr * max(0, self.end_h - max(t + self.lead_h, 0))

    def epoch_sigma(self, t, sigmas):
        """Forecast error sd for the peak, seen from hour t.

        Lead is measured to the EXPECTED peak hour -- a documented simplification, since
        the belief over peak hour is carried separately in protect_prob.
        """
        lead = max(0, int(round(self.peak_centre_h)) - t)
        return sigmas[min(lead, len(sigmas) - 1)]


# ----------------------------------------------------------------- the stopping rule
def solve(spec, sigmas, grid_lo=None, grid_hi=None, grid_step=0.01):
    """Backward induction. Returns (grid, policy, value).

    grid_step 0.01 is measured, not guessed: refining 0.05 -> 0.01 moved the margin over the
    tuned adversary from +0.291 to +0.356, and 0.01 -> 0.0025 only reached +0.365. So 0.01
    captures nearly all of it at a quarter of the cost.

    policy[t, i] is True where STAGE is optimal at epoch t given bias-corrected
    forecast grid[i]. value[t, i] is the expected cost-to-go.

    State is the bias-corrected forecast of the PEAK intake temperature. Belief about
    the truth given that forecast is N(m, sigma(lead)^2) under a flat prior.
    """
    if grid_lo is None:
        grid_lo = spec.thr_c - 5.0
    if grid_hi is None:
        grid_hi = spec.thr_c + 5.0
    grid = np.arange(grid_lo, grid_hi + grid_step, grid_step)
    G = len(grid)
    K = spec.last_epoch
    if K < 0:
        raise ValueError("peak_h (%d) is inside the lead time (%d): nothing to decide"
                         % (spec.peak_h, spec.lead_h))

    value = np.zeros((K + 1, G))
    policy = np.zeros((K + 1, G), dtype=bool)

    def cost_if_stage(t, sig):
        """Staging at t only helps if the peak arrives after the capacity does.

        With probability protect_prob(t) the extra train is running in time and the
        effective threshold rises by capacity_c; with the remaining probability the peak
        has already passed and we paid for nothing.
        """
        pp = spec.protect_prob(t)
        prot = p_exceed(grid, sig, spec.thr_c + spec.capacity_c)
        unprot = p_exceed(grid, sig, spec.thr_c)
        return spec.stage_cost(t) + (pp * prot + (1.0 - pp) * unprot) * spec.c_excursion

    def cost_if_never(sig):
        return p_exceed(grid, sig, spec.thr_c) * spec.c_excursion

    # ---- terminal epoch: last chance, so it really is a two-way comparison
    sigK = spec.epoch_sigma(K, sigmas)
    stage_K, never_K = cost_if_stage(K, sigK), cost_if_never(sigK)
    policy[K] = stage_K < never_K
    value[K] = np.minimum(stage_K, never_K)

    # ---- earlier epochs: STAGE now, or WAIT and re-decide with a tighter bound
    for t in range(K - 1, -1, -1):
        sig_t = spec.epoch_sigma(t, sigmas)
        sig_next = spec.epoch_sigma(t + 1, sigmas)
        # m' | m ~ N(m, sig_t^2 + sig_next^2): the forecast wanders while belief tightens
        step_sd = math.sqrt(sig_t ** 2 + sig_next ** 2)
        trans = _transition(grid, step_sd)
        wait = trans.dot(value[t + 1])
        stage = cost_if_stage(t, sig_t)
        policy[t] = stage < wait
        value[t] = np.minimum(stage, wait)

    return grid, policy, value


def _transition(grid, step_sd):
    """Row-stochastic Gaussian transition matrix on the grid (edges absorb mass)."""
    step_sd = max(float(step_sd), 1e-6)
    d = grid[:, None] - grid[None, :]            # d[i,j] = grid[i] - grid[j]
    w = np.exp(-0.5 * (d / step_sd) ** 2)
    w /= w.sum(axis=1, keepdims=True)
    return w


# ----------------------------------------------------------------- simulation
# Every policy is expressed as a boolean "fire" matrix of shape (n_days, n_epochs):
# fire[d, t] is True if, on day d, the policy would stage at hour t GIVEN it has not
# already staged. The stage epoch is then the first True in each row, which makes the
# whole evaluation a couple of numpy calls -- needed because the margin searches below
# evaluate thousands of candidate policies.

def make_forecast_paths(spec, sigmas, truths, rng):
    """(n_days, n_epochs) bias-corrected forecasts of the PEAK intake temperature.

    Error sd shrinks with lead time, so later columns are sharper views of the same truth.
    """
    K = spec.last_epoch
    sig = np.array([spec.epoch_sigma(t, sigmas) for t in range(K + 1)])
    truths = np.asarray(truths, dtype=np.float64)
    return truths[:, None] + rng.standard_normal((len(truths), K + 1)) * sig[None, :]


def _hw_by_epoch(spec, halfwidths, n_epochs):
    c = int(round(spec.peak_centre_h))
    return np.array([halfwidths[min(max(c - t, 0), len(halfwidths) - 1)]
                     for t in range(n_epochs)])


def fire_fixed_hour(spec, M, halfwidths, hour, margin=0.0):
    """THE ADVERSARY: act at ONE fixed hour of the day, thresholding the bound then.

    Both the hour and the margin are tuned by exhaustive search, so this is the best
    possible rule of the form "check the forecast at HH:00 and stage if it looks bad".
    It subsumes the day-0 threshold (hour=0) and defer-to-deadline (hour=last) as special
    cases. If the stopping rule cannot beat the best member of this family OUT OF SAMPLE,
    the backward induction earns nothing and the test must fail.
    """
    F = np.zeros(M.shape, dtype=bool)
    h = int(np.clip(hour, 0, M.shape[1] - 1))
    hw = _hw_by_epoch(spec, halfwidths, M.shape[1])[h]
    F[:, h] = (M[:, h] + hw + margin) > spec.thr_c
    return F


def fire_threshold_t0(spec, M, halfwidth, margin=0.0):
    """What run_e2e.py does today: decide once at t=0 and never revisit."""
    F = np.zeros(M.shape, dtype=bool)
    F[:, 0] = (M[:, 0] + halfwidth + margin) > spec.thr_c
    return F


def fire_deadline(spec, M, halfwidths, margin=0.0):
    """Defer until capacity would only just arrive in time for the expected peak."""
    h = max(0, int(round(spec.peak_centre_h)) - spec.lead_h)
    return fire_fixed_hour(spec, M, halfwidths, h, margin)


def fire_myopic(spec, M, halfwidths, margin=0.0):
    """Re-check the bound every hour and stage the moment it breaches. Careful, but blind
    to what the next forecast will reveal."""
    hw = _hw_by_epoch(spec, halfwidths, M.shape[1])
    return (M + hw[None, :] + margin) > spec.thr_c


def fire_dp(spec, M, grid, policy):
    """The stopping rule."""
    idx = np.clip(np.searchsorted(grid, M), 0, len(grid) - 1)
    F = np.zeros(M.shape, dtype=bool)
    for t in range(M.shape[1]):
        F[:, t] = policy[min(t, policy.shape[0] - 1), idx[:, t]]
    return F


def fire_always(_spec, M):
    F = np.zeros(M.shape, dtype=bool)
    F[:, 0] = True
    return F


def fire_never(_spec, M):
    return np.zeros(M.shape, dtype=bool)


def draw_peak_hours(spec, n_days, rng):
    """Sample the hour the peak actually lands on, one per day."""
    return rng.choice(np.arange(spec.horizon_h), size=n_days, p=spec.pmf)


def evaluate(spec, F, truths, peak_hours):
    """Score a fire matrix. Returns (mean_cost, stage_epoch_array, n_excursions).

    stage_epoch is -1 on days the policy never staged. Staging is irreversible, so only
    the first True in each row matters. Capacity only protects the day if it arrived
    before the peak: staged_at + lead_h <= actual peak hour.
    """
    truths = np.asarray(truths, dtype=np.float64)
    fired = F.any(axis=1)
    epoch = np.where(fired, F.argmax(axis=1), -1)
    stage_costs = np.array([spec.stage_cost(t) for t in range(F.shape[1])])
    cost = np.where(fired, stage_costs[np.clip(epoch, 0, None)], 0.0)
    in_time = fired & ((epoch + spec.lead_h) <= peak_hours)
    thr_eff = np.where(in_time, spec.thr_c + spec.capacity_c, spec.thr_c)
    hit = truths > thr_eff
    cost = cost + hit * spec.c_excursion
    # per-day costs are returned so comparisons can be PAIRED: two policies scored on the
    # same days share almost all their variance, and the SE of the difference is far
    # tighter than the SE of either mean.
    return float(cost.mean()), epoch, int(hit.sum()), cost


def oracle_cost(spec, truths, peak_hours):
    """Clairvoyant floor: knows both the true peak temperature AND its hour, and stages at
    the latest hour that still arrives in time -- only when doing so beats taking the hit."""
    truths = np.asarray(truths, dtype=np.float64)
    latest = np.asarray(peak_hours) - spec.lead_h          # last useful staging hour
    can = latest >= 0
    sc = np.where(can, spec.c_stage_fixed + spec.c_stage_hr * np.maximum(
        0, spec.end_h - np.clip(latest, 0, None) - spec.lead_h), 0.0)
    hit_if_staged = truths > spec.thr_c + spec.capacity_c
    hit_if_not = truths > spec.thr_c
    cost_stage = np.where(can, sc + hit_if_staged * spec.c_excursion, np.inf)
    cost_not = hit_if_not * spec.c_excursion
    return float(np.minimum(cost_stage, cost_not).mean())
