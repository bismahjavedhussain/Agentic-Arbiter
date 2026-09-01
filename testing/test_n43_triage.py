# -*- coding: utf-8 -*-
"""N-43  ---  fleet triage: given ONE shared regional wind forecast, which of N sites gets a
SCARCE PHYSICAL resource today?   FREE, GPU (one-time precompute, then pure array lookups).

WHY THIS TEST EXISTS
    N-20 (test_n20_fleet.py) already tested "is fleet allocation a real decision" and FAILED
    (-2.67 sigma, equal split won). That result stands and is not repeated here. But N-20
    allocated a LIMITED GPU-COMPUTE budget -- which sites get more ensemble MEMBERS spent on
    them today, to reduce uncertainty about an UNKNOWN per-site quantity. GPU compute is cheap
    (the plan documents 13-17s for 20 sites x 100 members), so there was no real scarcity for a
    clever policy to exploit, and equal-split -- "just fully evaluate everyone" -- won.

    This test allocates a genuinely scarce PHYSICAL resource instead (a handful of portable
    chillers / technician-hours / operator attention-slots), and the quantity that varies across
    sites is not unknown-and-learnable but PHYSICALLY DETERMINED and cheap to compute exactly for
    every site, every day: each site's geometry sets where its "bad sector" (the compass heading
    that drives its exhaust back into its own intake, N-23) sits, and one shared regional wind
    forecast, with its OWN measured uncertainty, interacts with 20 different bad-sector headings
    in 20 different ways. A site whose bad sector currently straddles the forecast's uncertainty
    is genuinely ambiguous (wide, high risk); one whose bad sector sits outside it is not -- even
    if a bare POINT reading of the forecast happens to give both sites a similar number.

PREDICTION, RECORDED BEFORE RUNNING, same discipline as N-20
    I expect this to have a REAL chance of passing, for a reason N-20 did not have: N-23 already
    measured a 27.04x spread in ensemble uncertainty between the geometric edge and safe sectors,
    driven by a near-binary nonlinearity in how rise depends on direction. A point estimate reads
    one number off a curve; it cannot see whether that number sits on a steep part of the curve
    (ambiguous, forecast error matters enormously) or a flat part (robust, forecast error is
    nearly irrelevant). An ensemble that propagates the forecast's ACTUAL measured error through
    each site's OWN curve can see that difference. Whether it is large enough to change WHICH
    sites get picked, and by enough to beat the best simple ranking, is what this test answers.
    HONEST RISK: if most sites' curves are similarly shaped (all near-linear, or all near-binary
    at similar headings), the point estimate may already capture most of the differentiating
    signal and this could fail exactly as N-20 did. That is a real possible outcome.

WHY THERE IS NO TRAIN/TEST SPLIT HERE, UNLIKE N-9/N-20/N-24
    Every policy below is a FIXED rule with no tunable parameter (rank by X, pick top-k). There
    is nothing to fit on training days, so nothing can be flattered by reuse. thr (the excursion
    threshold) is derived directly from each site's own precomputed physics, not from simulated
    days, so it exists before a single "day" is drawn. All N_TEST_DAYS below are therefore true
    held-out evaluation, and this is a CLEANER evaluation than N-20's, not a shortcut.

THE MECHANISM, PRECISELY
    1. ONE-TIME PRECOMPUTE (real physics, real GPU): for each of 20 sites (geometries from
       test_n20_fleet.build(), same random (separation, bank_w) ranges as N-20 for direct
       comparability), sweep wind_from_deg over the full 0-360deg circle in 5deg bins, with
       N_MEMBERS_PER_BIN members per bin varying speed and load, using the calibrated solver on
       the GPU (warp_solver.solve_batch). This gives each site a real, physics-derived rise
       DISTRIBUTION as a function of absolute wind direction -- exactly the object N-23 already
       showed is near-binary and knife-edged.
    2. ORIENTATION DIVERSITY WITHOUT INVENTING NEW GEOMETRY: test_n20_fleet.build() always faces
       the condenser bank east with the neighbour due east, so every site's bad sector would sit
       at the SAME absolute compass heading and a shared regional wind would put every site in or
       out of danger together -- no triage signal would exist. Real facilities are not all built
       facing the same way. So each site gets a random ORIENTATION OFFSET in [0, 360), applied at
       QUERY time: site k's response to a wind direction theta is read from its own table at
       (theta - offset_k) mod 360. This is a valid rotational relabelling of the same physics (the
       advection-diffusion equation over flat open ground has no preferred absolute direction other
       than the wind vector itself -- rotating the wind-query index while holding geometry fixed
       is equivalent to rotating the geometry while holding the true wind fixed), NOT an invented
       shortcut, and it is the only way to get orientation diversity without solving 20 x 6 new
       geometries.
    3. PER SIMULATED DAY (pure array lookups, no new solves): draw ONE true regional direction,
       uniform over the full compass (no invented climatological skew). Draw a FORECAST direction
       by adding a REAL, MEASURED persistence error sampled from N-40's fixture
       (results/fixtures/n40_kiad_dir_errors.json, KIAD ASOS, 72 real days) at lead=3h, matching
       the ~3h reserve-cooling lead time used throughout this project. Truth for each site is drawn
       from its table at the TRUE direction; the point-estimate baselines read the table at the
       FORECAST direction only; the ensemble policy resamples 100 draws from the REAL error
       distribution around the forecast, propagates each through each site's table, and scores by
       the resulting p90 -- the same acting statistic ("p90 is what the agent acts on, because
       averages hide danger") used everywhere else in this project.

ADVERSARIES, PRE-REGISTERED BEFORE LOOKING
    A equal_rotation   ignore the forecast; rotate which k of N sites get the resource, day to day
    B top_k_by_mean     rank by the POINT forecast rise (no uncertainty), pick top k
    C top_k_marginal    rank by |point forecast - threshold| ascending, pick top k
    D random_k          random k each day
    PROPOSED ensemble_p90   rank by each site's ensemble-propagated p90 given today's forecast
                            AND its measured uncertainty, pick top k

PASS CONDITION, FIXED BEFORE RUNNING
    ensemble_p90 beats the best of {A,B,C,D} by >= 2 paired standard errors on N_TEST_DAYS,
    scored by total fleet excursion cost (unserved site whose TRUE rise breaches threshold_rise
    costs C_EXCURSION; served sites cost 0, i.e. the resource is assumed to fully mitigate that
    site's excursion that day -- all policies spend the same k units, so the deployment cost
    itself is common across policies and cancels out of the comparison; only WHERE differs).

USAGE
    python test_n43_triage.py     # builds the precompute (GPU, ~1-2 min), runs the full test
"""
import json, math, os, sys, time

import numpy as np

from common import banner, save_result, verdict, FIXTURES
from solver import CALIBRATED
import warp_solver as ws
from test_n20_fleet import build, rise_of
from test_n9_staging import paired

if not ws.HAVE_WARP:
    print("warp-lang unavailable; this test requires the GPU path.")
    sys.exit(2)

AMB = 30.0
N_SITES = 20
N_DIR_BINS = 72                       # 5 deg bins, matching N-23's resolution
N_MEMBERS_PER_BIN = 15
DECISION_LEAD_H = 3                   # matches the ~3h reserve-cooling lead used throughout
K_SERVED = 4                          # 20% of the fleet -- a genuinely scarce daily allocation
N_TEST_DAYS = 3000
N_ENSEMBLE_DRAWS = 100                # matches N-40/N-23's ensemble convention
C_EXCURSION = 1.0
CAL_UC = CALIBRATED["downwash_uc"]
CAL_EXPO = CALIBRATED["downwash_exponent"]
STEPS = 800
SEED = 43


def load_measured_direction_errors(lead=DECISION_LEAD_H):
    p = os.path.join(FIXTURES, "n40_kiad_dir_errors.json")
    if not os.path.exists(p):
        print("   N-40's wind-error fixture is missing (%s). Run test_n40_windsharpen.py first "
              "to generate it (free, no API key needed)." % p)
        sys.exit(2)
    d = json.load(open(p, encoding="utf-8"))
    errs = d["errors"].get(str(lead))
    if not errs:
        print("   no measured errors at lead=%dh in the fixture." % lead)
        sys.exit(2)
    return np.asarray(errs, dtype=float), d["meta"]


# ----------------------------------------------------------------- precompute (real GPU physics)
def build_site_tables(seed=7):
    """For each of N_SITES real geometries, a (N_DIR_BINS, N_MEMBERS_PER_BIN) array of rise
    samples as a function of absolute wind direction. One real GPU ensemble sweep per site."""
    rng = np.random.default_rng(seed)
    seps = rng.uniform(150, 700, N_SITES)
    banks = rng.uniform(30, 120, N_SITES)
    offsets = rng.uniform(0, 360, N_SITES)      # orientation diversity, applied at QUERY time
    dirs = np.arange(0.0, 360.0, 360.0 / N_DIR_BINS)
    tables = []
    t0 = time.time()
    for k in range(N_SITES):
        site, intake = build(float(seps[k]), float(banks[k]))
        wf = np.repeat(dirs, N_MEMBERS_PER_BIN)
        spd = np.clip(rng.normal(6.0, 2.0, len(wf)), 0.3, 14.0)
        scl = rng.uniform(0.5, 1.0, len(wf))
        dw = np.array([1.0 for _ in spd])   # solve_batch's own downwash=None default is 1.0;
                                            # kept explicit for clarity, matches N-20's convention
        T = ws.solve_batch(site, np.full(len(wf), AMB), spd, wf, scl, steps=STEPS, downwash=None)
        r = np.array([rise_of(T[m].astype(np.float64), site, intake[0], intake[1], AMB)
                     for m in range(len(wf))])
        tables.append(r.reshape(N_DIR_BINS, N_MEMBERS_PER_BIN))
    elapsed = time.time() - t0
    print("   %d sites x %d bins x %d members = %d GPU solves in %.1f s"
          % (N_SITES, N_DIR_BINS, N_MEMBERS_PER_BIN,
             N_SITES * N_DIR_BINS * N_MEMBERS_PER_BIN, elapsed))
    return {"tables": tables, "seps": seps, "banks": banks, "offsets": offsets, "dirs": dirs}


def query_bin(direction_deg, offset_deg):
    local = (direction_deg - offset_deg) % 360.0
    return int(round(local / (360.0 / N_DIR_BINS))) % N_DIR_BINS


# ----------------------------------------------------------------- day simulation (pure numpy)
def simulate_days(state, n_days, err_pool, seed):
    """For each simulated day: shared true direction, forecast = true + real measured error, so
    true = forecast - error. Returns per-site TRUE rise, per-site POINT (forecast-only) rise, and
    per-site ENSEMBLE p90 (forecast, minus fresh error draws, propagated through the real error
    distribution -- the sign must match how forecast was generated from true above)."""
    rng = np.random.default_rng(seed)
    tables, offsets = state["tables"], state["offsets"]
    true_dir = rng.uniform(0, 360, n_days)
    fc_err = rng.choice(err_pool, size=n_days, replace=True)
    fc_dir = (true_dir + fc_err) % 360.0

    truth = np.zeros((n_days, N_SITES))
    point = np.zeros((n_days, N_SITES))
    ens_p90 = np.zeros((n_days, N_SITES))
    for k in range(N_SITES):
        tb, off = tables[k], offsets[k]
        for d in range(n_days):
            tbin = query_bin(true_dir[d], off)
            truth[d, k] = rng.choice(tb[tbin])
            fbin = query_bin(fc_dir[d], off)
            point[d, k] = tb[fbin].mean()
            draws = rng.choice(err_pool, size=N_ENSEMBLE_DRAWS, replace=True)
            # Generation uses fc_dir = true_dir + fc_err, i.e. true_dir = fc_dir - fc_err. The
            # inversion must use the SAME sign or it queries a distribution inconsistent with how
            # the day was generated -- found and fixed, it was using +draws.
            implied_true = (fc_dir[d] - draws) % 360.0
            bins = np.array([query_bin(t, off) for t in implied_true])
            samples = np.array([rng.choice(tb[b]) for b in bins])
            ens_p90[d, k] = np.percentile(samples, 90)
    return true_dir, fc_dir, truth, point, ens_p90


# ----------------------------------------------------------------- allocators (fixed rules, no tuning)
def alloc_equal_rotation(day_idx, _point, _ens_p90):
    start = (day_idx * K_SERVED) % N_SITES
    return set((start + i) % N_SITES for i in range(K_SERVED))


def alloc_top_k_mean(_day_idx, point, _ens_p90):
    return set(np.argsort(-point)[:K_SERVED])


def alloc_top_k_marginal(_day_idx, point, _ens_p90, thr):
    return set(np.argsort(np.abs(point - thr))[:K_SERVED])


def alloc_random(_day_idx, _point, _ens_p90, rng):
    return set(rng.choice(N_SITES, size=K_SERVED, replace=False))


def alloc_ensemble_p90(_day_idx, _point, ens_p90):
    return set(np.argsort(-ens_p90)[:K_SERVED])


def fleet_cost(served, truths_row, thr):
    return sum(C_EXCURSION for k in range(N_SITES) if k not in served and truths_row[k] > thr)


def main():
    banner("N-43  fleet triage: scarce PHYSICAL resource, shared regional forecast   [FREE, GPU]")
    print("   PREDICTION RECORDED BEFORE RUNNING: real chance of passing, because N-23 already")
    print("   measured a 27.04x uncertainty swing a point estimate cannot see. Real risk of")
    print("   failing exactly as N-20 did if site curves are too similarly shaped. Reporting")
    print("   whatever happens.")

    print("\n   [1/3] loading N-40's REAL measured wind-direction errors at lead=%dh" % DECISION_LEAD_H)
    err_pool, meta = load_measured_direction_errors()
    print("      %d real samples, %s" % (len(err_pool), meta["span"]))

    print("\n   [2/3] one-time GPU precompute: %d real site geometries x full 0-360deg sweep"
          % N_SITES)
    state = build_site_tables()

    all_rise = np.concatenate([t.ravel() for t in state["tables"]])
    per_site_p90 = np.array([np.percentile(t.ravel(), 90) for t in state["tables"]])
    thr = float(np.median(per_site_p90))
    print("      per-site marginal p90 range %.4f-%.4f C, threshold set at median %.4f C"
          % (per_site_p90.min(), per_site_p90.max(), thr))

    print("\n   [3/3] simulating %d held-out days (no training needed -- see docstring)"
          % N_TEST_DAYS)
    true_dir, fc_dir, truth, point, ens_p90 = simulate_days(state, N_TEST_DAYS, err_pool, SEED + 1)

    rng_r = np.random.default_rng(SEED + 2)
    costs = {}
    for name, fn in (
        ("equal_rotation", lambda d: alloc_equal_rotation(d, point[d], ens_p90[d])),
        ("top_k_mean", lambda d: alloc_top_k_mean(d, point[d], ens_p90[d])),
        ("top_k_marginal", lambda d: alloc_top_k_marginal(d, point[d], ens_p90[d], thr)),
        ("random_k", lambda d: alloc_random(d, point[d], ens_p90[d], rng_r)),
        ("ensemble_p90", lambda d: alloc_ensemble_p90(d, point[d], ens_p90[d])),
    ):
        per_day = np.array([fleet_cost(fn(d), truth[d], thr) for d in range(N_TEST_DAYS)])
        costs[name] = per_day

    print("\n   %-16s %10s %10s" % ("policy", "mean cost", "sd"))
    for name, per_day in costs.items():
        print("   %-16s %10.4f %10.4f" % (name, per_day.mean(), per_day.std(ddof=1)))

    baselines = {k: v for k, v in costs.items() if k != "ensemble_p90"}
    best_name = min(baselines, key=lambda k: baselines[k].mean())
    best = baselines[best_name]
    gain, se = paired(best, costs["ensemble_p90"])
    sigma = gain / se if se > 0 else float("inf")

    print("\n   RESULT")
    print("      best baseline        : %s at %.4f" % (best_name, best.mean()))
    print("      ensemble_p90         : %.4f" % costs["ensemble_p90"].mean())
    print("      gain (paired)        : %+.4f +/- %.4f  =  %.2f sigma" % (gain, se, sigma))

    ok = sigma > 2.0
    print("\n   VERDICT AGAINST THE PRE-COMMITTED CONDITION (>2 sigma over the best baseline)")
    print()
    verdict(ok,
            "PASS - triaging a scarce physical resource by ensemble-propagated p90, using the "
            "REAL measured wind-direction error distribution, beats the best simple ranking (%s) "
            "by %+.4f +/- %.4f (%.2f sigma) on %d held-out days. This is a genuine WHAT/WHERE "
            "agentic decision that does not depend on any temporal-sharpening result."
            % (best_name, gain, se, sigma, N_TEST_DAYS),
            "FAIL - as it could have been. The best simple ranking (%s) matches or beats the "
            "ensemble policy (%+.4f +/- %.4f, %.2f sigma). Do not claim fleet triage as the "
            "agentic core; site risk curves are apparently similar enough in shape that a point "
            "forecast already captures most of the differentiating signal, same failure mode as "
            "N-20." % (best_name, gain, se, sigma))

    save_result("n43_triage.json", {
        "prediction": "real chance of passing, due to N-23's 27.04x measured uncertainty swing; "
                      "real risk of failing like N-20 if site curves are similarly shaped",
        "n_sites": N_SITES, "n_dir_bins": N_DIR_BINS, "n_members_per_bin": N_MEMBERS_PER_BIN,
        "k_served": K_SERVED, "n_test_days": N_TEST_DAYS, "decision_lead_h": DECISION_LEAD_H,
        "wind_error_source": meta, "threshold_rise": thr,
        "per_site_marginal_p90": per_site_p90.tolist(),
        "costs": {k: {"mean": float(v.mean()), "sd": float(v.std(ddof=1))}
                 for k, v in costs.items()},
        "best_baseline": best_name, "gain": gain, "se": se, "sigma": sigma, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
