# -*- coding: utf-8 -*-
"""N-56 -- FREE-COOLING HOURS, with the incumbent RE-SPECIFIED. FREE, GPU. Zero API calls.

WHY N-51 IS BEING REDONE RATHER THAN QUOTED
-------------------------------------------
N-51 reported "~150 extra free-cooling hours/year, up to 40 exceedances/year prevented". **That number
is withdrawn.** Its incumbent was modelled as reading *a weather station some kilometres away*, carrying
a 0.40 C station-to-site divergence (N-49b). `claims-and-defences.md` section 1.15 then established, by
full-text search of the sources, that this framing is **verified false**: data centres use **ON-SITE
rooftop weather stations** (Vantage and GoDaddy named; Orion units wired to BMS/HVAC).

With an on-site sensor the 0.40 C divergence **largely vanishes**, and it was a big part of N-51's
margin. So the entire advantage has to be re-derived from what is actually verifiable.

WHAT IS VERIFIED ABOUT THE INCUMBENT, and it is the whole basis of this test
---------------------------------------------------------------------------
From the same sources, full-text searched:
  * They monitor **outside air temperature, dew point, humidity**.
  * **Wind speed and wind direction are entirely absent. So is solar radiation.**
  * In the 27-page authoritative LBNL thermal-guidelines document, the words **"outdoor", "outside air"
    and "forecast" do not appear at all.**

So the incumbent is a **reactive on-site rooftop sensor**: it knows ambient NOW, at its own location,
and nothing else. It has no forecast and no wind, therefore no way to estimate its own recirculation.
Three candidate advantages remain, and this test measures each rather than asserting it:

  (a) ANTICIPATION      -- if the plant needs N hours of notice, a reactive rule must extrapolate.
  (b) RECIRCULATION     -- invisible to an ambient sensor; we model it per hour from real geometry.
  (c) WIND              -- absent from what they monitor.

⚠ THE "3 HOURS NOTICE" FIGURE IS NOT SOURCED, SO IT IS SWEPT
    HANDOFF section 6.2 says "the plant needs ~3 h notice". We could not source that, so **N is swept
    over {0, 1, 2, 3, 4, 6} h** and the whole curve is reported. No single unsourced constant carries
    the result. **At N = 0 advantage (a) vanishes entirely**, so N = 0 is the honest FLOOR of the claim.

⚠ THE AGENT IS GIVEN FORECAST WIND, NOT OBSERVED WIND -- avoiding gotcha #17
    FortyGuard's API contains no wind field (confirmed from their OpenAPI spec), so at a lead of N > 0
    the agent must use a PUBLIC wind forecast, whose direction error was measured at **47-72 deg**
    (N-40). Handing the agent the realised bearing would be an oracle leak of exactly the kind that
    inverted N-50 by 35 sigma. So for N > 0 the agent's bearing is the truth plus N(0, sigma_dir) with
    sigma_dir swept over the measured 47-72 deg range. Only at N = 0 does it see observed wind.

⚠ THE AGENT'S FORECAST CARRIES FORTYGUARD'S MEASURED LEVEL BIAS
    Section 8e / HANDOFF section 2b measured FortyGuard's forecast to be off in LEVEL by a
    **spatially uniform, day-varying** offset: day-means **-0.84, -0.81, +0.15, -3.71 C** while the
    within-day spatial sd across 17,862 tiles is only 0.06-0.29 C. That is why live conformal coverage
    came in at **65.6 %** against a 90 % promise. This test therefore runs the agent BOTH ways:
        biased   -- a per-day level offset drawn to match the measured spread
        anchored -- the offset removed, i.e. the customer's sensor used to anchor the level
    and reports whether the conclusion depends on anchoring. If it does, the headline is CONDITIONAL.

GEOMETRY: the COMMITTED site, not the synthetic reference
    N-51 ran on `solver.demo_site()`. This runs on the real committed pair -- AWS IAD116 / IAD117,
    `AGENTIC-ARBITER/data/geometry/solver_site_longest.json`, 60.3 m facade gap, 2,600 m2 bank, where
    N-54 measured **0 % of downwind bearings refused**, so a rise is computable for every wind hour.

PRE-REGISTERED CONDITIONS -- written before the first run, methodology rule 2
----------------------------------------------------------------------------
Q1 EQUAL SAFETY OR THE COMPARISON IS VOID. Both policies calibrate a one-sided conformal buffer to the
   SAME 90 % level on the TRAIN half and are scored on the HELD-OUT half. On held-out hours each
   policy's exceedance rate among its own declared-safe hours must fall within **10 % +/- 2 pp**. If a
   policy misses that band its hours are NOT comparable and that configuration is reported VOID, not
   quoted. A policy may never win by being less safe.

Q2 THE N = 0 FLOOR. At zero notice the agent's only remaining edge is recirculation awareness. Report
   the gain at N = 0 with n, SE and a 95 % CI. **This is the floor of any claim made.** If the gain at
   N = 0 is not statistically distinguishable from zero, say so plainly.

Q3 THE NOTICE CURVE. Report gain for every N in {0,1,2,3,4,6} h. No single N may be quoted alone.

Q4 THE BIAS TEST -- the one that can kill the headline. With FortyGuard's measured day-varying level
   bias applied, does the agent still satisfy Q1? **Pre-registered: if it does NOT, then the gain must
   be stated as conditional on level anchoring, and the unanchored result must be reported as a
   FAILURE, not omitted.**

Q5 THE INCUMBENT IS A RANGE, NOT A STRAWMAN. Its rooftop sensor instrument error is swept over
   {0.1, 0.3, 0.5} C, and its buffer is TUNED by the same conformal procedure on the same train half
   (methodology rule 3). Its fitted buffer value is printed so it can be checked for being a strawman.

Q6 ANTI-DEGENERACY. Report the fitted buffers for both policies. If the agent's advantage equals the
   incumbent's buffer minus a constant, the "gain" is a threshold artefact (rule 4) and must be said so.

AMENDMENT 2026-08-18, AFTER THE FIRST RUN -- TWO ERRORS IN THIS FILE, BOTH MINE
------------------------------------------------------------------------------
The first run of this test was INVALID. Both faults are recorded rather than quietly patched.

**ERROR 1 -- AN ORACLE LEAK, the same family as gotcha #17.** The agent's forecast was built as
`amb_fut + N(0, FG_NOISE_SD)` with FG_NOISE_SD = 0.15 C **at every notice period**. But 0.15 C is
FortyGuard's residual sd on *observed* peak temperature, not the error of an N-hour-ahead forecast.
Measured persistence error sd at this station is **1.41 / 2.38 / 3.27 / 4.07 / 5.42 C at 1 / 2 / 3 / 4 /
6 h**. So the agent was handed a 6-hour forecast **36x better than persistence, for free**, which is why
its fitted buffer stayed flat at ~0.21 C while the incumbent's grew to 7.76 C, and why it "gained"
+2,439 h/yr at N = 6. **That number is withdrawn. It measured the leak, not the agent.**

FIX, and it is the only defensible framing given that HANDOFF section 6.2 states FortyGuard's H-hour
forecast skill at this site is UNMEASURED: the agent's forecast error sd at lead N is set to
    sd(N) = (1 - skill) * persistence_sd(N)
with `persistence_sd(N)` MEASURED from the same 43,763 hours, and **skill swept over
{0.00, 0.25, 0.50, 0.75, 0.90}**. skill = 0 means the agent forecasts no better than persistence, i.e.
it has NO anticipation advantage at all. **The headline becomes the BREAK-EVEN SKILL: how good the
forecast must be before the agent beats a reactive sensor.** That is a statement we can defend without
knowing FortyGuard's true skill, and it tells FortyGuard exactly which number would settle it.

**ERROR 2 -- Q1 WAS MIS-SPECIFIED AND CANNOT BE SATISFIED BY A CORRECT POLICY.** Q1 required the
exceedance rate *among declared-safe hours* to sit in 10 % +/- 2 pp. But a one-sided conformal bound
guarantees `P(intake <= pred + buffer) >= 90 %` **MARGINALLY over all hours**, not conditionally on the
declared subset. Among declared hours the true intake is typically far below the limit, so the observed
rate was **0.000-0.022 for BOTH policies** and all 132 configurations were reported VOID. That is a
defect in the condition, not a finding.

Q1 is therefore reported **FAILED AS WRITTEN**, and the correct equal-safety check is stated here:
    Q1b  MARGINAL HELD-OUT COVERAGE. For both policies, the fraction of held-out hours with
         `intake <= pred + buffer` must lie within **90 % +/- 2 pp** -- the same quantity and the same
         tolerance N-26 uses on the live forecast path. Both bounds are calibrated to the same alpha on
         the same train half, so if both cover at ~90 % the declared-hour comparison IS at equal safety.
**This correction affects BOTH policies identically and favours neither**, which is why it is a repair
rather than a moved goalpost. Q2-Q6 are unchanged and their verdicts stand as recorded.

WHAT IS NOT CLAIMED
    No dollars, no kWh -- the C-to-kWh conversion could not be sourced. Chiller-hours only.
    No humidity or enthalpy gate; real economizers also limit on wet-bulb, which would reduce hours for
    BOTH policies. KIAD ASOS stands in for the site's ambient time series for both policies equally,
    so no spatial term advantages either side -- that is the correction this test exists to make.
"""
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import banner, save_result, verdict, RESULTS      # noqa: E402
import solver                                                 # noqa: E402
from solver import CALIBRATED                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IA = os.path.join(ROOT, "AGENTIC-ARBITER")
SITE_JSON = os.path.join(IA, "data", "geometry", "solver_site_longest.json")
HOURLY = os.path.join(IA, "data", "weather", "kiad_hourly_2021_2025.json")

sys.path.insert(0, os.path.join(IA, "src"))
from build_site import rasterise                              # noqa: E402

# ---- swept, never single-valued
NOTICE_H = [0, 1, 2, 3, 4, 6]                 # Q3: "3 h" is unsourced, so sweep
SIGMA_DIR_DEG = [47.0, 72.0]                  # MEASURED, N-40 forecast direction error range
SENSOR_ERR_C = [0.1, 0.3, 0.5]                # Q5: incumbent instrument error range
LIMITS_C = [18.0, 21.0, 24.0, 27.0]           # ASHRAE-anchored changeover candidates

ALPHA = 0.10                                  # 90 % one-sided
CALM_KT = 3.0                                 # ASOS reports drct=0 when calm
FG_NOISE_SD = 0.15                            # FortyGuard residual sd on OBSERVED peak temp; used at N=0 only
FORECAST_SKILL = [0.00, 0.25, 0.50, 0.75, 0.90]   # 0 = no better than persistence; see AMENDMENT
COVERAGE_TOL = 0.02                           # Q1b: 90 % +/- 2 pp, same tolerance as N-26
FG_DAY_BIAS_SD = 1.80                         # matches measured day-means -0.84,-0.81,+0.15,-3.71 C
SPEED_GRID_MS = [0.5, 1.5, 2.5, 3.5, 5.0, 7.0, 9.0, 12.0]
STEP_DEG = 5
BEARINGS = np.arange(0.0, 360.0, STEP_DEG)
AMB_REF = 30.0
STEPS = 800
SEED = 56
YEARS = 5


def conformal(res, alpha=ALPHA):
    """One-sided split-conformal quantile: k-th smallest residual, k = ceil((n+1)(1-alpha))."""
    r = np.sort(np.asarray(res, dtype=float))
    if len(r) == 0:
        return float("nan")
    k = math.ceil((len(r) + 1) * (1.0 - alpha))
    return float(r[min(k, len(r)) - 1])


def load_site():
    d = json.load(open(SITE_JSON, encoding="utf-8"))
    n, dx = d["domain"]["n"], d["domain"]["dx_m"]
    s = solver.Site(d["domain"]["size_m"], dx)
    for ring in (d["source_ring_m"], d["receptor_ring_m"]):
        s.obstacle |= rasterise(ring, n, dx)
    bank = rasterise(d["bank_ring_m"], n, dx)
    if int(bank.sum()) != int(d["bank_cells"]):
        raise SystemExit("site rebuild mismatch: %d vs %d bank cells" % (bank.sum(), d["bank_cells"]))
    s.source[bank] += d["discharge_k"] / d["exchange_s"]
    return s, d, bank


def emission_point(site, d, bank):
    """Facade midpoint marched outward until clear -- identical rule to direction_sweep.py 8f.1."""
    ys, xs = np.nonzero(bank)
    bc = ((xs.mean() + 0.5) * site.dx, (ys.mean() + 0.5) * site.dx)
    cA = d["source_centre_m"]
    ox, oy = bc[0] - cA[0], bc[1] - cA[1]
    L = math.hypot(ox, oy)
    ox, oy = ox / L, oy / L
    for k in range(200):
        px, py = bc[0] + ox * (site.dx * 0.5) * k, bc[1] + oy * (site.dx * 0.5) * k
        j, i = int(px / site.dx), int(py / site.dx)
        if not site.obstacle[i, j]:
            return (px, py)
    raise SystemExit("emission point never cleared the facade")


def build_rise_table(site, d, bank):
    """rise[bearing, speed] on the REAL committed geometry. GPU if available, else CPU."""
    ix, iy = d["intake_m"]
    rad = d["intake_radius_m"]
    emit = emission_point(site, d, bank)

    # N-54 measured 0 % refused here; assert it rather than trusting it
    refused = [b for b in BEARINGS if solver.path_blocked(site, emit, ix, iy, float(b))]
    print("      path_blocked refusals at this site: %d of %d bearings" % (len(refused), len(BEARINGS)))
    if refused:
        print("      *** %d bearings are REFUSED. Those hours will be excluded and counted."
              % len(refused))

    bb, ss = np.meshgrid(BEARINGS, np.array(SPEED_GRID_MS), indexing="ij")
    bf, sf = bb.ravel(), ss.ravel()
    dw = np.array([solver.downwash_fraction(v, CALIBRATED["downwash_uc"],
                                            CALIBRATED["downwash_exponent"]) for v in sf])
    t0 = time.time()
    used = "GPU"
    try:
        import warp_solver as ws
        T = ws.solve_batch(site, np.full(len(bf), AMB_REF), sf, bf, np.ones(len(bf)),
                           steps=STEPS, device="cuda", downwash=dw)
        rise = np.array([solver.intake_temperature(T[m].astype(np.float64), site, ix, iy, rad,
                                                   disc=True) - AMB_REF for m in range(len(bf))])
    except Exception as ex:
        used = "CPU (%s)" % str(ex)[:60]
        rise = np.empty(len(bf))
        for m in range(len(bf)):
            Tm = solver.solve(site, AMB_REF, float(sf[m]), float(bf[m]), diffusivity=7.40,
                              downwash_uc=CALIBRATED["downwash_uc"],
                              downwash_exponent=CALIBRATED["downwash_exponent"])
            rise[m] = solver.intake_temperature(Tm, site, ix, iy, rad, disc=True) - AMB_REF
    print("      %d solves in %.1f s on %s" % (len(bf), time.time() - t0, used))
    tab = rise.reshape(len(BEARINGS), len(SPEED_GRID_MS))
    bi, si = np.unravel_index(int(np.argmax(tab)), tab.shape)
    print("      max rise %.4f C at bearing %.0f deg, %.1f m/s;  mean over table %.4f C"
          % (tab.max(), BEARINGS[bi], SPEED_GRID_MS[si], tab.mean()))
    return tab, set(int(b) for b in refused)


def lookup(tab, bearing, speed):
    """Nearest-neighbour in bearing (5 deg grid) and speed. Vectorised."""
    bi = (np.round(np.asarray(bearing) / STEP_DEG).astype(int)) % len(BEARINGS)
    sg = np.asarray(SPEED_GRID_MS)
    si = np.abs(np.asarray(speed)[:, None] - sg[None, :]).argmin(axis=1)
    return tab[bi, si]


def load_hours():
    d = json.load(open(HOURLY, encoding="utf-8"))
    f = d["meta"]["fields"]
    it, idr, isk = f.index("tmpc"), f.index("drct"), f.index("sknt")
    keys = sorted(d["hours"])
    t = np.array([d["hours"][k][it] if d["hours"][k][it] is not None else np.nan for k in keys])
    dr = np.array([d["hours"][k][idr] if d["hours"][k][idr] is not None else np.nan for k in keys])
    sk = np.array([d["hours"][k][isk] if d["hours"][k][isk] is not None else np.nan for k in keys])
    day = np.array([k[:10] for k in keys])
    return keys, t, dr, sk, day


def main():
    banner("N-56  free-cooling hours vs a REACTIVE ON-SITE ROOFTOP SENSOR   [FREE, zero API calls]")
    print("   N-51's ~150 h/yr is WITHDRAWN -- its incumbent read a station km away. See the docstring.")

    site, sd, bank = load_site()
    print("\n   [1/3] committed site: %s" % os.path.basename(SITE_JSON))
    print("      gap %.1f m, bank %d cells (%.0f m2), intake radius %.0f m"
          % (sd["facade_gap_m"], sd["bank_cells"], sd["bank_area_m2"], sd["intake_radius_m"]))
    tab, refused = build_rise_table(site, sd, bank)

    keys, tmpc, drct, sknt, day = load_hours()
    ok = ~np.isnan(tmpc)
    tmpc, drct, sknt, day = tmpc[ok], drct[ok], sknt[ok], day[ok]
    n = len(tmpc)
    print("\n   [2/3] %d usable hours over %d years (%.0f/yr)" % (n, YEARS, n / YEARS))

    rng = np.random.default_rng(SEED)
    calm = np.isnan(drct) | np.isnan(sknt) | (sknt < CALM_KT)
    spd = np.where(np.isnan(sknt), 0.0, sknt) * 0.514444
    brg = np.where(np.isnan(drct), 0.0, drct)
    print("      calm/missing-bearing hours: %d (%.1f %%) -- these use the ALL-BEARING mean rise"
          % (calm.sum(), 100 * calm.mean()))

    true_rise = np.where(calm, tab.mean(), lookup(tab, brg, spd))
    true_amb = tmpc                                  # KIAD stands in for site ambient, BOTH policies
    true_intake = true_amb + true_rise
    print("      true intake rise: mean %.4f  p90 %.4f  max %.4f C"
          % (true_rise.mean(), np.percentile(true_rise, 90), true_rise.max()))

    # per-day level bias for the agent's forecast, matching the measured spread (section 8e)
    udays = np.unique(day)
    dbias = dict(zip(udays, rng.normal(0.0, FG_DAY_BIAS_SD, len(udays))))
    day_bias = np.array([dbias[x] for x in day])

    # MEASURED persistence error per lead -- this is what a reactive rule must overcome, and it is
    # what the agent's forecast error is scaled against (see AMENDMENT, ERROR 1)
    pers_sd = {0: 0.0}
    for N in NOTICE_H:
        if N:
            pers_sd[N] = float(np.std(true_amb[N:] - true_amb[:-N], ddof=1))
    print("      MEASURED persistence error sd by lead: " +
          ", ".join("%dh %.2f" % (k, v) for k, v in sorted(pers_sd.items())))

    half = n // 2
    tr = slice(0, half)
    te = slice(half, n)
    print("      train %d hours, held-out %d hours (chronological split)" % (half, n - half))

    rows = []
    print("\n   [3/3] sweeping notice x sensor error x limit x anchoring")
    for anchored in (True, False):
        for N in NOTICE_H:
            # shift: decision at t, outcome at t+N
            if N == 0:
                idx_now, idx_fut = np.arange(n), np.arange(n)
            else:
                idx_now, idx_fut = np.arange(0, n - N), np.arange(N, n)
            amb_now = true_amb[idx_now]
            amb_fut = true_amb[idx_fut]
            rise_fut = true_rise[idx_fut]
            intake_fut = true_intake[idx_fut]
            calm_fut = calm[idx_fut]
            brg_fut, spd_fut = brg[idx_fut], spd[idx_fut]
            bias_fut = day_bias[idx_fut]
            day_fut = day[idx_fut]
            m = len(idx_now)
            h = m // 2
            TR, TE = slice(0, h), slice(h, m)

            sig_dirs = [0.0] if N == 0 else SIGMA_DIR_DEG
            skills = [1.0] if N == 0 else FORECAST_SKILL   # at N=0 there is nothing to forecast
            for sig_dir in sig_dirs:
              for skill in skills:
                # agent's forecast error is scaled to MEASURED persistence error at this lead.
                # skill = 0 -> no better than persistence; skill = 1 -> perfect (never used for N>0).
                fc_sd = math.hypot(FG_NOISE_SD, (1.0 - skill) * pers_sd[N])
                fc = amb_fut + rng.normal(0.0, fc_sd, m) + (0.0 if anchored else bias_fut)
                # agent's forecast bearing: truth + measured direction error (0 only at N = 0)
                bhat = (brg_fut + rng.normal(0.0, sig_dir, m)) % 360.0 if sig_dir > 0 else brg_fut
                rise_hat = np.where(calm_fut, tab.mean(), lookup(tab, bhat, spd_fut))
                pred_agent = fc + rise_hat

                for serr in SENSOR_ERR_C:
                    obs = amb_now + rng.normal(0.0, serr, m)   # reactive on-site sensor, NOW
                    pred_inc = obs                             # persistence, no wind, no recirc model

                    b_inc = conformal(intake_fut[TR] - pred_inc[TR])
                    b_ag = conformal(intake_fut[TR] - pred_agent[TR])
                    # Q1b: MARGINAL held-out coverage of each bound -- the quantity a conformal
                    # bound actually guarantees, and the same one N-26 measures
                    cov_i = float(np.mean(intake_fut[TE] <= pred_inc[TE] + b_inc))
                    cov_a = float(np.mean(intake_fut[TE] <= pred_agent[TE] + b_ag))
                    ok_cov = (abs(cov_i - 0.90) <= COVERAGE_TOL and abs(cov_a - 0.90) <= COVERAGE_TOL)

                    for lim in LIMITS_C:
                        dec_i = (pred_inc[TE] + b_inc) <= lim
                        dec_a = (pred_agent[TE] + b_ag) <= lim
                        safe = intake_fut[TE] <= lim
                        si_, sa_ = int((dec_i & safe).sum()), int((dec_a & safe).sum())
                        # PAIRED PER-DAY difference on held-out hours: the same day contributes to
                        # both policies, so the pairing removes day-to-day weather variance
                        # (methodology rule 3). n = days, not hours.
                        dts = day_fut[TE]
                        gi = (dec_i & safe).astype(np.int32)
                        ga = (dec_a & safe).astype(np.int32)
                        uq, inv = np.unique(dts, return_inverse=True)
                        per_day = (np.bincount(inv, weights=ga, minlength=len(uq))
                                   - np.bincount(inv, weights=gi, minlength=len(uq)))
                        nd = len(per_day)
                        dmean = float(per_day.mean())
                        dsd = float(per_day.std(ddof=1)) if nd > 1 else float("nan")
                        dse = dsd / math.sqrt(nd) if nd > 1 else float("nan")
                        lo95, hi95 = dmean - 1.96 * dse, dmean + 1.96 * dse
                        sig = (lo95 > 0.0) or (hi95 < 0.0)
                        xi = int((dec_i & ~safe).sum())
                        xa = int((dec_a & ~safe).sum())
                        ri = xi / max(1, int(dec_i.sum()))
                        ra = xa / max(1, int(dec_a.sum()))
                        # Q1: both exceedance rates must sit in 10 % +/- 2 pp
                        void = not (0.08 <= ri <= 0.12 and 0.08 <= ra <= 0.12)
                        scale = YEARS * (m / n) * 0.5     # held-out is half of the shifted series
                        rows.append({
                            "anchored": anchored, "notice_h": N, "sigma_dir_deg": sig_dir,
                            "forecast_skill": skill, "forecast_err_sd_c": fc_sd,
                            "persistence_sd_c": pers_sd[N],
                            "coverage_incumbent": cov_i, "coverage_agent": cov_a,
                            "equal_safety_q1b": bool(ok_cov),
                            "sensor_err_c": serr, "limit_c": lim,
                            "buffer_incumbent_c": b_inc, "buffer_agent_c": b_ag,
                            "declared_inc": int(dec_i.sum()), "declared_agent": int(dec_a.sum()),
                            "safe_inc": si_, "safe_agent": sa_,
                            "exc_inc": xi, "exc_agent": xa,
                            "exc_rate_inc": ri, "exc_rate_agent": ra,
                            "gain_hours_per_year": (sa_ - si_) / max(scale, 1e-9),
                            "paired_days_n": nd, "gain_per_day_mean_h": dmean,
                            "gain_per_day_se_h": dse,
                            "gain_per_day_ci95": [lo95, hi95],
                            "gain_per_day_significant": bool(sig),
                            "gain_per_year_from_paired_h": dmean * 365.25,
                            "void_unequal_safety": void})

    # ------------------------------------------------------------------ report
    def pick(**kw):
        out = rows
        for k, v in kw.items():
            out = [r for r in out if r[k] == v]
        return out

    print("\n" + "=" * 102)
    print("  Q6 / ANTI-DEGENERACY -- fitted buffers, both TUNED by the same conformal procedure")
    print("=" * 102)
    print("  %-9s %5s %8s %7s %12s %12s" % ("anchored", "N h", "sig_dir", "skill",
                                            "buf_incumb", "buf_agent"))
    for r in rows:
        if (r["limit_c"] == 24.0 and r["sensor_err_c"] == 0.3
                and r["sigma_dir_deg"] in (0.0, 72.0)
                and r["forecast_skill"] in (1.0, 0.0, 0.90)):
            print("  %-9s %5d %8.0f %7.2f %12.4f %12.4f"
                  % (r["anchored"], r["notice_h"], r["sigma_dir_deg"], r["forecast_skill"],
                     r["buffer_incumbent_c"], r["buffer_agent_c"]))

    print("\n" + "=" * 102)
    print("  Q1 -- FAILED AS WRITTEN. The condition was MIS-SPECIFIED (AMENDMENT, ERROR 2)")
    print("=" * 102)
    er = [r["exc_rate_agent"] for r in rows] + [r["exc_rate_inc"] for r in rows]
    print("  exceedance rate among DECLARED hours, both policies: %.4f .. %.4f -- nowhere near 10 %%."
          % (min(er), max(er)))
    print("  A conformal bound guarantees 90 %% coverage MARGINALLY, not conditionally on the declared")
    print("  subset, so no correct policy can satisfy this. It fails for BOTH policies identically and")
    print("  favours neither. Replaced by Q1b. Q1 stands as FAILED AS WRITTEN and is not a finding.")

    print("\n" + "=" * 102)
    print("  Q1b -- MARGINAL HELD-OUT COVERAGE, 90 %% +/- 2 pp  (the real equal-safety check)")
    print("=" * 102)
    for anch in (True, False):
        sub = pick(anchored=anch)
        good = [r for r in sub if r["equal_safety_q1b"]]
        ci = [r["coverage_incumbent"] for r in sub]
        ca = [r["coverage_agent"] for r in sub]
        print("  anchored=%-5s : %3d of %3d PASS   coverage incumbent %.3f..%.3f   agent %.3f..%.3f"
              % (anch, len(good), len(sub), min(ci), max(ci), min(ca), max(ca)))

    print("\n" + "=" * 102)
    print("  Q4 -- DOES FORTYGUARD'S MEASURED LEVEL BIAS BREAK THE AGENT'S BOUND?")
    print("=" * 102)
    for anch in (True, False):
        sub = pick(anchored=anch)
        bad = [r for r in sub if abs(r["coverage_agent"] - 0.90) > COVERAGE_TOL]
        ca = [r["coverage_agent"] for r in sub]
        print("  anchored=%-5s : agent coverage %.3f..%.3f ; OUTSIDE 90+/-2 pp in %d of %d"
              % (anch, min(ca), max(ca), len(bad), len(sub)))

    print("\n" + "=" * 102)
    print("  Q2 / Q3 / BREAK-EVEN SKILL   limit 24 C, sensor err 0.3 C, ANCHORED, sigma_dir 72 deg")
    print("=" * 102)
    print("  safe free-cooling hours per year, AGENT minus REACTIVE INCUMBENT")
    print("  %5s %8s" % ("N h", "pers_sd")
          + "".join("%10s" % ("sk%.2f" % s) for s in FORECAST_SKILL) + "   break-even")
    curve = []
    for N in NOTICE_H:
        cells, be = [], None
        for s in FORECAST_SKILL:
            sel = [r for r in rows
                   if r["anchored"] and r["notice_h"] == N and r["limit_c"] == 24.0
                   and r["sensor_err_c"] == 0.3
                   and r["forecast_skill"] == (1.0 if N == 0 else s)
                   and r["sigma_dir_deg"] == (0.0 if N == 0 else 72.0)]
            g = sel[0]["gain_hours_per_year"] if sel else float("nan")
            q = sel[0]["equal_safety_q1b"] if sel else False
            cells.append((g, q))
            if be is None and g == g and g > 0:
                be = s
        ps = [r["persistence_sd_c"] for r in rows if r["notice_h"] == N][0]
        print("  %5d %8.2f" % (N, ps)
              + "".join("%+9.0f%s" % (g, " " if q else "*") for g, q in cells)
              + "   " + ("skill>=%.2f" % be if be is not None else "NEVER wins"))
        # rule 1: nothing is quoted without n, SE and a 95 % CI
        for s_ in FORECAST_SKILL:
            sel = [r for r in rows
                   if r["anchored"] and r["notice_h"] == N and r["limit_c"] == 24.0
                   and r["sensor_err_c"] == 0.3
                   and r["forecast_skill"] == (1.0 if N == 0 else s_)
                   and r["sigma_dir_deg"] == (0.0 if N == 0 else 72.0)]
            if not sel:
                continue
            r = sel[0]
            print("           skill %.2f : %+.0f h/yr  |  paired per-day %+.4f h, SE %.4f, "
                  "95%% CI [%+.4f, %+.4f], n=%d days -> %s"
                  % (s_, r["gain_hours_per_year"], r["gain_per_day_mean_h"], r["gain_per_day_se_h"],
                     r["gain_per_day_ci95"][0], r["gain_per_day_ci95"][1], r["paired_days_n"],
                     "SIGNIFICANT" if r["gain_per_day_significant"] else "not distinguishable from 0"))
            if N == 0:
                break
        curve.append({"notice_h": N, "persistence_sd_c": ps,
                      "gain_by_skill": {("%.2f" % s): cells[i][0]
                                        for i, s in enumerate(FORECAST_SKILL)},
                      "break_even_skill": be})
    print("  * = fails Q1b, so that cell is NOT comparable at equal safety")
    print("")
    print("  N = 0 is the FLOOR (Q2): no forecast is involved, so the whole gain there is")
    print("  RECIRCULATION AWARENESS -- the one advantage needing no forecast skill at all.")

    save_result("n56_freecooling.json", {
        "test": "N-56 free cooling vs reactive on-site rooftop sensor",
        "supersedes": "N-51, whose incumbent read a station km away -- withdrawn",
        "site": {"file": os.path.basename(SITE_JSON), "gap_m": sd["facade_gap_m"],
                 "bank_area_m2": sd["bank_area_m2"], "refused_bearings": sorted(refused)},
        "swept": {"notice_h": NOTICE_H, "sigma_dir_deg": SIGMA_DIR_DEG,
                  "sensor_err_c": SENSOR_ERR_C, "limit_c": LIMITS_C,
                  "anchored": [True, False]},
        "constants": {"alpha": ALPHA, "fg_noise_sd": FG_NOISE_SD,
                      "fg_day_bias_sd": FG_DAY_BIAS_SD, "calm_kt": CALM_KT,
                      "speed_grid_ms": SPEED_GRID_MS},
        "hours": int(n), "years": YEARS,
        "true_rise": {"mean": float(true_rise.mean()), "p90": float(np.percentile(true_rise, 90)),
                      "max": float(true_rise.max())},
        "q1_status": "FAILED AS WRITTEN -- mis-specified, replaced by Q1b marginal coverage",
        "persistence_sd_c": {str(k): v for k, v in sorted(pers_sd.items())},
        "break_even_curve": curve,
        "rows": rows})
    print("\n  written: testing/results/n56_freecooling.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
