# -*- coding: utf-8 -*-
"""N-50  ---  WHEN should the agent commit its setpoint?  The seventh and final decision core.

Pre-registered in n50-timing-PREREG.md. P0-P5 fixed before running. FREE: existing GPU physics table +
cached free NOAA ASOS. Zero API calls, no key use.

WHY THIS IS NOT A REPEAT OF N-44
    N-44 held AMB = 30.0 FROZEN on all 4,000 days and scored only the recirculation rise, which deleted
    the one term that sharpens from the problem it was testing. Here ambient VARIES from 534 real KIAD
    days and its forecast error comes from the measured per-lead anomaly pool, whose exponent is
    b = +0.3414, CI [+0.2427, +0.4402] -- the project's only positive sharpening measurement.

TWO SPECIFICATION FIXES, both aimed at N-44's failure modes
    1. COST = margin x W, with W the FIXED risk-window duration. N-44's
       hours_run = max(0, HORIZON_H - online_t + 1) made late commitment cheap TWICE -- tighter bound
       AND fewer paid hours -- which is part of why its DP drifted late and useless. Here the only
       benefits of waiting are a tighter bound and the risk of missing the deadline.
    2. The breach penalty R is SWEPT over four decades, never chosen, and P2 demands a contiguous
       winning band >= 1 decade wide so no unsourced constant can carry the result.

    The DP is isotonic-regression Longstaff-Schwartz -- the third and cleanest of N-44's three
    implementations. The binned transition-matrix approach is excluded by design: two real defects
    lived in it.

SIGN CONVENTIONS (HANDOFF GOTCHA #11 / N-43's lesson)
    Direction follows N-44/N-46 exactly: fc_dir = true_dir + err, and the ensemble inverts with
    true = fc_dir - err. Ambient follows its pool's own definition: the n45 pool is
    err = T(target) - T(target - L), i.e. truth minus persistence forecast, so forecast = truth - err.
    Both pools are de-biased per lead before use (the raw ambient pool has a +8.784 C mean at 12 h,
    which is the diurnal cycle, not forecast error).
"""
import json
import math
import os
import statistics
import sys
import time

import numpy as np
from sklearn.isotonic import IsotonicRegression

from common import banner, save_result, verdict, FIXTURES
import solver
from solver import CALIBRATED
import warp_solver as ws
import test_n44_adaptive_commit as n44
from test_n46b_dirsweep import dbin_vec
from test_n9_staging import paired

# ----------------------------------------------------------------- pre-registered constants
PEAK_CENTRE_H = 12.0
PEAK_SD_H = 1.4475          # N-38, 15 days, LOO floor 1.1579
LEAD_H = 3                  # plant response time
T_LAST = 9                  # latest decision hour: t + LEAD_H <= 12
DECISION_HOURS = list(range(0, T_LAST + 1))
W_WINDOW = 1.0              # risk-window duration; cost is linear in W so it cancels from comparisons
ALPHA = 0.10
R_GRID = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0]

N_TRAIN = 4000
N_TEST = 4000
SEED = 50
WIND_SPEED_MS = 3.0
STEPS = 800
AMB_REF = 30.0              # only the reference the GPU table is built at; days use real ambient

P0_TOL = 0.05               # generator must reproduce its input sds to 5 %
P2_MIN_SIGMA = 2.0
P2_MIN_BAND = 3             # >= 3 adjacent R values = >= 1 decade
P3_MIN_OFF_MODAL = 0.25
P4_MIN_ABS_RHO = 0.15

# BUG FIX: the grid ran to 3.0 while the margin variable reaches 5.5 C at early hours,
# so 43 % of (day, hour) margins exceeded the grid maximum and NO threshold could suppress firing.
# Both adversaries degenerated to "always commit", and SCAN-10 could not express "never fire here".
# Now spans the full observed range plus a sentinel above it so "never fire" IS expressible.
MARGINS = np.append(np.arange(-1.0, 6.001, 0.10), 99.0)   # adversary threshold, in C

WIND_FIX = os.path.join(FIXTURES, "n46_kiad_wind.json")
TEMP_FIX = os.path.join(FIXTURES, "n45_kiad_temps.json")


# ----------------------------------------------------------------- inputs
def load_pools():
    w = json.load(open(WIND_FIX, encoding="utf-8"))
    t = json.load(open(TEMP_FIX, encoding="utf-8"))
    dirs = np.asarray(list(w["dir_by_date"].values()), float)
    amb = np.asarray(list(t["target_by_date"].values()), float)
    dir_err = {int(k): np.asarray(v, float) for k, v in w["errors"].items()}
    amb_raw = {int(k): np.asarray(v, float) for k, v in t["errors"].items()}
    # de-bias ambient per lead: the raw mean IS the diurnal cycle, not forecast error
    amb_err = {k: v - v.mean() for k, v in amb_raw.items()}
    return dirs, amb, dir_err, amb_err


def build_table(seed=7):
    rng = np.random.default_rng(seed)
    site, intake = solver.demo_site()
    solver.assert_intake_clear(site, *intake, label="N-50 demo_site")
    dd = np.arange(0.0, 360.0, 360.0 / n44.N_DIR_BINS)
    wf = np.repeat(dd, n44.N_MEMBERS_PER_BIN)
    spd = np.clip(rng.normal(WIND_SPEED_MS, 1.0, len(wf)), 0.3, 14.0)
    scl = np.maximum(0.1, rng.normal(1.0, 2.0 / 11.0, len(wf)))
    dw = np.array([solver.downwash_fraction(v, CALIBRATED["downwash_uc"],
                                            CALIBRATED["downwash_exponent"]) for v in spd])
    t0 = time.time()
    T = ws.solve_batch(site, np.full(len(wf), AMB_REF), spd, wf, scl, steps=STEPS,
                       device="cuda", downwash=dw)
    rise = np.array([solver.intake_temperature(T[m].astype(np.float64), site, *intake) - AMB_REF
                     for m in range(len(wf))])
    print("      %d GPU solves in %.1f s" % (len(wf), time.time() - t0))
    return rise.reshape(n44.N_DIR_BINS, n44.N_MEMBERS_PER_BIN), dd


# ----------------------------------------------------------------- day generation
def make_days(table, dirs, amb, dir_err, amb_err, n, seed):
    """Vectorised. Returns per-day truth plus, for every decision hour, the observable bound."""
    rng = np.random.default_rng(seed)
    true_dir = rng.choice(dirs, size=n, replace=True)
    true_amb = rng.choice(amb, size=n, replace=True)
    peak_h = np.clip(rng.normal(PEAK_CENTRE_H, PEAK_SD_H, n), 1.0, 16.0)

    midx = rng.integers(0, table.shape[1], size=n)
    true_rise = table[dbin_vec(true_dir), midx]
    true_intake = true_amb + true_rise

    nb = table.shape[1]
    obs_bound = np.empty((n, len(DECISION_HOURS)))
    obs_point = np.empty((n, len(DECISION_HOURS)))
    obs_spread = np.empty((n, len(DECISION_HOURS)))
    sd_check_amb, sd_check_dir = {}, {}

    for i, t in enumerate(DECISION_HOURS):
        lead = int(PEAK_CENTRE_H - t)
        lead = max(1, min(12, lead))
        de = rng.choice(dir_err[lead], size=n, replace=True)
        ae = rng.choice(amb_err[lead], size=n, replace=True)
        sd_check_dir[lead] = float(de.std(ddof=1))
        sd_check_amb[lead] = float(ae.std(ddof=1))

        fc_dir = (true_dir + de) % 360.0                    # N-44/N-46 convention
        fc_amb = true_amb - ae                              # n45 pool is truth - forecast

        # ensemble at the forecast bearing, spread by that lead's own direction error
        draws = rng.choice(dir_err[lead], size=(n, n44.N_ENSEMBLE), replace=True)
        implied = (fc_dir[:, None] - draws) % 360.0          # true = forecast - error
        mi = rng.integers(0, nb, size=(n, n44.N_ENSEMBLE))
        samp = table[dbin_vec(implied), mi]
        p90 = np.percentile(samp, 90, axis=1)
        mean = samp.mean(axis=1)

        obs_point[:, i] = fc_amb + mean                      # the un-margined expectation
        obs_bound[:, i] = fc_amb + p90                       # before the conformal correction
        obs_spread[:, i] = samp.std(axis=1, ddof=1)          # the knife-edge state, for P4

    return {"true_intake": true_intake, "true_rise": true_rise, "peak_h": peak_h,
            "obs_bound": obs_bound, "obs_point": obs_point, "obs_spread": obs_spread,
            "sd_amb": sd_check_amb, "sd_dir": sd_check_dir}


def fit_conformal(train):
    """One correction per decision hour so the committed bound covers 90 % of realised intake."""
    q = np.empty(len(DECISION_HOURS))
    for i in range(len(DECISION_HOURS)):
        r = train["true_intake"] - train["obs_bound"][:, i]
        k = math.ceil((len(r) + 1) * (1.0 - ALPHA))
        q[i] = np.sort(r)[min(k, len(r)) - 1]
    return q


# ----------------------------------------------------------------- cost model
def day_costs(d, q, R):
    """Per-day cost of committing at each hour, plus the cost of never committing.

    margin(t) = committed bound - un-margined expectation. Cost = margin * W, plus R on a breach.
    Committing is only PROTECTIVE if t + LEAD_H <= peak_h; a late commitment is paid for and useless.
    """
    bound = d["obs_bound"] + q[None, :]
    margin = np.maximum(0.0, bound - d["obs_point"])
    in_time = (np.asarray(DECISION_HOURS)[None, :] + LEAD_H) <= d["peak_h"][:, None]
    baseline = d["obs_point"][:, -1]                       # no margin: the deadline point forecast
    breach_unprot = (d["true_intake"] > baseline).astype(float)
    breach_prot = (d["true_intake"][:, None] > bound).astype(float)
    breach = np.where(in_time, breach_prot, breach_unprot[:, None])
    c_commit = margin * W_WINDOW + R * breach
    c_never = R * breach_unprot
    return c_commit, c_never, bound, margin, in_time


# ----------------------------------------------------------------- policies
def run_fixed(d, q, R, hour, thr):
    c_commit, c_never, bound, margin, _ = day_costs(d, q, R)
    i = DECISION_HOURS.index(hour)
    fire = margin[:, i] > thr
    cost = np.where(fire, c_commit[:, i], c_never)
    commits = np.where(fire, hour, -1)
    return cost, commits


def tune_fixed(d, q, R):
    best = (None, None, float("inf"))
    for h in DECISION_HOURS:
        for m in MARGINS:
            c, _ = run_fixed(d, q, R, h, float(m))
            if c.mean() < best[2]:
                best = (h, float(m), c.mean())
    return best[0], best[1]


def fit_dp(train, q, R):
    """Isotonic Longstaff-Schwartz backward induction on the continuous observable."""
    c_commit, c_never, bound, margin, _ = day_costs(train, q, R)
    nT = len(DECISION_HOURS)
    V = c_never.copy()                       # value of never having committed
    cont_fit = {}
    for i in range(nT - 1, -1, -1):
        x = margin[:, i]
        # continuation cost cannot legitimately fall as today's own margin requirement rises
        f = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(x, V)
        cont_fit[i] = f
        V = np.minimum(c_commit[:, i], f.predict(x))
    return cont_fit


def run_dp(d, q, R, cont_fit):
    c_commit, c_never, bound, margin, _ = day_costs(d, q, R)
    n = len(d["true_intake"])
    cost = c_never.copy()
    commits = np.full(n, -1)
    open_mask = np.ones(n, bool)
    for i, t in enumerate(DECISION_HOURS):
        if not open_mask.any():
            break
        x = margin[:, i]
        wait = cont_fit[i].predict(x)
        act = (c_commit[:, i] <= wait) & open_mask
        cost[act] = c_commit[act, i]
        commits[act] = t
        open_mask &= ~act
    return cost, commits


def clairvoyant(d, q, R):
    c_commit, c_never, _, _, _ = day_costs(d, q, R)
    return np.minimum(c_commit.min(axis=1), c_never)


def off_modal(commits):
    fired = commits[commits >= 0]
    if len(fired) == 0:
        return 0.0, None, 0
    v, c = np.unique(fired, return_counts=True)
    return float(1.0 - c.max() / c.sum()), int(v[c.argmax()]), int(len(fired))


def spearman(a, b):
    """Spearman rho with a bootstrap CI. No scipy dependency."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 20 or np.unique(a).size < 3:
        return 0.0, (0.0, 0.0)

    def rho(x, y):
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        rx -= rx.mean(); ry -= ry.mean()
        den = math.sqrt((rx * rx).sum() * (ry * ry).sum())
        return float((rx * ry).sum() / den) if den > 0 else 0.0

    r = rho(a, b)
    rng = np.random.default_rng(7)
    bs = []
    for _ in range(400):
        idx = rng.integers(0, len(a), len(a))
        bs.append(rho(a[idx], b[idx]))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return r, (float(lo), float(hi))


# ----------------------------------------------------------------- main
def main():
    banner("N-50  when to commit the setpoint?  SEVENTH and final decision core   [FREE, GPU]")
    print("   Pre-registered in n50-timing-PREREG.md. Ambient VARIES here -- N-44 froze it at 30.0 C,")
    print("   which deleted the only term that sharpens (b = +0.3414, CI excludes zero).")

    dirs, amb, dir_err, amb_err = load_pools()
    print("\n   inputs: %d real wind directions, %d real ambient values (KIAD, 6 summers)"
          % (len(dirs), len(amb)))

    print("\n   [1/4] GPU precompute")
    table, dd = build_table()

    print("\n   [2/4] P0 instrument check -- does the generator reproduce its own input sds?")
    tr = make_days(table, dirs, amb, dir_err, amb_err, N_TRAIN, SEED + 1)
    te = make_days(table, dirs, amb, dir_err, amb_err, N_TEST, SEED + 2)
    print("      %-6s %14s %14s %10s   %14s %14s %10s"
          % ("lead", "amb sd input", "amb sd gen", "err", "dir sd input", "dir sd gen", "err"))
    p0_ok = True
    for lead in sorted(tr["sd_amb"]):
        ai = float((amb_err[lead]).std(ddof=1)); ag = tr["sd_amb"][lead]
        di = float((dir_err[lead]).std(ddof=1)); dg = tr["sd_dir"][lead]
        ea = abs(ag - ai) / ai if ai else 0.0
        ed = abs(dg - di) / di if di else 0.0
        if ea > P0_TOL or ed > P0_TOL:
            p0_ok = False
        print("      %-6d %14.3f %14.3f %9.1f%%   %14.2f %14.2f %9.1f%%"
              % (lead, ai, ag, 100 * ea, di, dg, 100 * ed))
    print("      -> P0 %s" % p0_ok)
    if not p0_ok:
        print("\n   *** P0 FAILED. The generator does not reproduce its own inputs; nothing")
        print("       downstream may be read. Fix the generator before interpreting anything.")
        save_result("n50_timing.json", {"p0": False,
                                        "conclusion": "generator failed its own instrument check"})
        return 2

    q = fit_conformal(tr)
    print("\n   conformal correction by decision hour (lead 12->3):")
    print("      " + "  ".join("t%d:%+.2f" % (t, q[i]) for i, t in enumerate(DECISION_HOURS)))

    print("\n   [3/4] sweeping the breach penalty over four decades")
    print("      %-9s %11s %11s %11s %9s %9s %9s"
          % ("R", "clairv.", "fixed", "DP", "sigma", "off-modal", "P1 ok"))
    rows = {}
    for R in R_GRID:
        h, m = tune_fixed(tr, q, R)
        cf, _ = run_fixed(te, q, R, h, m)
        dp = fit_dp(tr, q, R)
        cd, commits = run_dp(te, q, R, dp)
        cl = clairvoyant(te, q, R)
        g, se = paired(cf, cd)
        sig = g / se if se > 0 else float("inf")
        om, modal, nfired = off_modal(commits)
        p1 = bool(cl.mean() <= min(cf.mean(), cd.mean()) + 1e-9)
        fired = commits >= 0
        rho, ci = spearman(commits[fired], te["obs_spread"][fired, 0]) if fired.sum() > 20 else (0.0, (0, 0))
        rows[R] = {"R": R, "fixed_hour": h, "fixed_margin": m,
                   "cost_fixed": float(cf.mean()), "cost_dp": float(cd.mean()),
                   "cost_clairvoyant": float(cl.mean()),
                   "gain": g, "se": se, "sigma": sig,
                   "off_modal": om, "modal_hour": modal, "n_fired": nfired,
                   "commit_rate": float(fired.mean()),
                   "p1_clairvoyant_ok": p1,
                   "spearman_hour_vs_spread": rho, "spearman_ci": list(ci)}
        print("      %-9.0f %11.4f %11.4f %11.4f %+9.2f %8.0f%% %9s"
              % (R, cl.mean(), cf.mean(), cd.mean(), sig, 100 * om, p1))

    # ---- P2: contiguous band of >= 3 adjacent R values with sigma >= 2 ----
    wins = [R_GRID[i] for i in range(len(R_GRID)) if rows[R_GRID[i]]["sigma"] >= P2_MIN_SIGMA]
    band, best_band = [], []
    for i, R in enumerate(R_GRID):
        if rows[R]["sigma"] >= P2_MIN_SIGMA:
            band.append(R)
            if len(band) > len(best_band):
                best_band = list(band)
        else:
            band = []
    p1_all = all(rows[R]["p1_clairvoyant_ok"] for R in R_GRID)
    p2 = len(best_band) >= P2_MIN_BAND
    p3 = p2 and all(rows[R]["off_modal"] >= P3_MIN_OFF_MODAL for R in best_band)
    if best_band:
        rho_band = statistics.fmean([rows[R]["spearman_hour_vs_spread"] for R in best_band])
        ci_ok = all(rows[R]["spearman_ci"][0] * rows[R]["spearman_ci"][1] > 0 for R in best_band)
    else:
        rho_band, ci_ok = 0.0, False
    p4 = abs(rho_band) >= P4_MIN_ABS_RHO and ci_ok

    print("\n   [4/4] VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      P0 generator reproduces its inputs            : %s" % p0_ok)
    print("      P1 clairvoyant <= all policies at every R     : %s" % p1_all)
    print("      P2 contiguous winning band >= %d values        : %s (%s)"
          % (P2_MIN_BAND, p2, best_band or "none"))
    print("      P3 off-modal >= %.0f%% throughout that band     : %s" % (100 * P3_MIN_OFF_MODAL, p3))
    print("      -- reported separately --")
    print("      P4 timing tracks the knife-edge spread        : %s (rho %+.3f, CI excl 0: %s)"
          % (p4, rho_band, ci_ok))

    ok = p0_ok and p1_all and p2 and p3
    print()
    verdict(ok,
            "PASS - the commitment TIMING is a real sequential decision. The DP beats an exhaustively "
            "tuned fixed-hour rule by >= %.1f SE across a contiguous band of breach penalties %s "
            "(>= 1 decade), it genuinely varies its commitment hour rather than collapsing to a "
            "constant, and the clairvoyant bound confirms the cost model is consistent at every R. "
            "Ambient sharpening (b=+0.3414) is what makes waiting informative, and N-44 could not see "
            "this because it froze ambient. Physics-drives-timing (P4) is %s."
            % (P2_MIN_SIGMA, best_band, "SUPPORTED" if p4 else "NOT supported"),
            "FAIL - P0 %s, P1 %s, P2 %s, P3 %s. If P2 failed, the timing decision is dead for EVERY "
            "breach penalty across four decades -- a permanent closure, and the seventh and final "
            "attempt. If P2 passed but P3 failed, the optimal policy is 'wait until the deadline', "
            "which a fixed rule expresses perfectly, so no agent is warranted on this decision. "
            "Report it exactly that way." % (p0_ok, p1_all, p2, p3))

    save_result("n50_timing.json", {
        "measures": "whether the TIMING of a setpoint commitment is a genuine sequential decision once "
                    "ambient varies and its measured sharpening is present",
        "does_not_measure": "FortyGuard forecast skill (persistence is a LOWER bound); field "
                            "performance; anything in energy or money (P5 -- C->kWh unsourced); "
                            "absolute margin-hours are not physically calibrated because W is a "
                            "modelling choice that cancels from comparisons",
        "why_not_a_repeat_of_n44": "N-44 froze AMB at 30.0 and scored recirculation rise only, deleting "
                                   "the sharpening term; and its hours_run made late commitment cheap "
                                   "twice over. Both fixed here.",
        "inputs": {"n_dirs": len(dirs), "n_ambient": len(amb),
                   "peak_centre_h": PEAK_CENTRE_H, "peak_sd_h": PEAK_SD_H, "lead_h": LEAD_H,
                   "decision_hours": DECISION_HOURS, "w_window": W_WINDOW},
        "p0_sd_check": {"amb_generated": tr["sd_amb"], "dir_generated": tr["sd_dir"]},
        "conformal_q_by_hour": q.tolist(),
        "r_grid": R_GRID, "rows": {str(k): v for k, v in rows.items()},
        "winning_band": best_band, "all_winning_r": wins,
        "spearman_band_mean": rho_band,
        "conditions": {"p0_tol": P0_TOL, "p2_min_sigma": P2_MIN_SIGMA, "p2_min_band": P2_MIN_BAND,
                       "p3_min_off_modal": P3_MIN_OFF_MODAL, "p4_min_abs_rho": P4_MIN_ABS_RHO},
        "p0": bool(p0_ok), "p1": bool(p1_all), "p2": bool(p2), "p3": bool(p3), "p4": bool(p4),
        "pass": bool(ok),
    })
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
