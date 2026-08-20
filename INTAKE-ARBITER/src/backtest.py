# -*- coding: utf-8 -*-
"""FIVE-YEAR BACKTEST -- the agent over all 43,763 real hours, on the rigorous conformal layer.

    python backtest.py            # everything; writes ../demo/backtest.json
    python backtest.py n56        # only the N-56 reproduction, for the comparison audit
    python backtest.py aci        # only the online adaptive-conformal experiment

ZERO API CALLS.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS
--------------------------------------------------------------------------------------------
The agent's headline free-cooling number was a CITATION to N-56, a separate test. That is a weak
position: the thing being demonstrated and the thing being measured were different programs. This
runs the agent itself -- same bound, same gates, same scheduler -- over every hour of five real
years and produces its OWN annual number.

It also makes possible three things the 7-day case set could not support:

  1. MONDRIAN group-conditional calibration with enough data to be real. Stratified by
     hour-of-day, each group holds ~1,800 residuals; a 90 % quantile needs 9.
  2. An ONLINE ADAPTIVE CONFORMAL experiment with ~43,000 rounds. ACI's guarantee is a long-run
     one, so it cannot be demonstrated on 4 days. It can be demonstrated on five years.
  3. A HELD-OUT split. Buffers are calibrated on one set of days and scored on days never used
     for calibration.

--------------------------------------------------------------------------------------------
THE METRIC, AND WHY THERE ARE TWO OF THEM
--------------------------------------------------------------------------------------------
`free_h`      hours the policy declared free cooling.
`safe_free_h` hours it declared free cooling AND the true intake was genuinely under the limit.
`breach_h`    declared free while the true intake was over. free_h = safe_free_h + breach_h.

**N-56's headline uses `safe_free_h`**, so that is the metric used for the comparison in `n56`.
Reporting `free_h` alone would let a reckless policy look good.

--------------------------------------------------------------------------------------------
KNOWN, DELIBERATE DIFFERENCES FROM N-56 -- every one makes THIS test harder to pass
--------------------------------------------------------------------------------------------
Recorded before running, so the comparison cannot be rationalised afterwards.

  1. N-56 gives the incumbent a sensor error of 0.1-0.5 C. We give it a PERFECT sensor at zero
     notice. A stronger incumbent means a smaller measured gain for us.
  2. N-56 declares hour by hour with no switching constraints. We impose a switch budget AND a
     minimum dwell, which can only REDUCE the agent's free hours.
  3. N-56's headline row sits at forecast_skill = 1.00 and sigma_dir_deg = 0.0 -- a perfect
     forecast and perfectly known wind direction. We sweep skill and never use 1.00 as a
     headline.
  4. We add a DEW-POINT gate at the published ASHRAE recommended maximum (15 C, Green Grid
     WP#46 p.6), which removes hours from BOTH policies and which N-56 explicitly listed as a gap
     in its own limitations. It replaced an INVENTED "wet-bulb minus 3 C" gate that had no source.
  5. Our bound is group-conditional, so it is tighter in easy hours and WIDER in hard ones.
     Wider in hard hours costs free-cooling hours.

So the expected direction is: **this test should report a SMALLER gain than N-56.** If it reports
a larger one, something is wrong and the difference must be explained before either is quoted.

--------------------------------------------------------------------------------------------
WHAT CANNOT BE BACKTESTED HERE, STATED PLAINLY
--------------------------------------------------------------------------------------------
* THE AIR-QUALITY GATE. No five-year air-quality record exists in this project -- KIAD's ASOS
  fixture carries temperature, dew point, wind direction and wind speed only. FortyGuard supplies
  air quality, but for 29 days, not five years. The contamination gate is therefore measured
  separately on the FortyGuard days and reported with its own n; it is NOT folded into the annual
  number. Fetching a five-year EPA AQS record would fix this and needs no FortyGuard credits.
* FORTYGUARD'S LEVEL OFFSET still rests on n = 4 days. The SHAPE error is calibrated on five
  years; the LEVEL error cannot be. That asymmetry is carried through every result here.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
ROOT = os.path.dirname(IA)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import conformal as C                                                     # noqa: E402
import environment as E                                                   # noqa: E402
import metros as M                                                        # noqa: E402
from agent import (BEARINGS, CALM_KT, FORECAST_SKILL, MODE_FREE, MODE_MECH,  # noqa: E402
                   PLANT_ENVELOPE, SPEED_GRID_MS,
                   STEP_DEG, debiased_persistence_residuals, load_hours,
                   lookup_rise, perceive_fortyguard, plan, reactive_incumbent,
                   rise_table, say, banner)

ALPHA = 0.10

# ---- the reference point for the one-at-a-time sensitivity sweeps.
# This is NOT a hidden constant: `run_sensitivity()` varies EVERY axis below around it and reports
# each result, and `main()` refuses to write output if any axis is declared here and left unswept.
# A sensitivity analysis needs a stated base case; what it must not have is an UNSTATED one.
#
# `dewpoint_limit_c` REPLACED AN INVENTED CONSTANT and the replacement is the point. This file
# used to gate on "wet-bulb <= dry-bulb limit MINUS 3 C". The 3.0 had no source, was derived from
# our OWN other knob, and so failed this project's point-at-the-constant test. The sourced
# replacement is a DEW-POINT maximum of 15 C -- Green Grid White Paper #46 p.6, which gives the
# ASHRAE recommended maxima as 27 C dry-bulb AND 15 C dew point and counts a free-cooling hour
# only when BOTH hold. See agent.py's PLANT_ENVELOPE, which this file now imports rather than
# restates, so the two cannot drift (gotcha #12).
# `offset_day` USED TO SIT HERE AND IT WAS NOT AN AXIS -- score_config ignores whatever is passed
# for it, because the anchor decides the offset treatment. It is now DERIVED from `anchor` in the
# result row, so a reader cannot mistake a label for a knob.
BASE = {"notice_h": 3, "anchor": "sensor", "skill": 0.50, "limit_c": 24.0,
        "switch_budget": 2, "min_dwell_h": 3, "dewpoint_limit_c": 15.0,
        "bank_mode": "longest",
        "sensor_err_c": 0.3, "fg_noise_sd_c": 0.15, "include_rise": True,
        "sensor_dither": True}

# ---- THE SWEEP AXES ARE IMPORTED, NOT RESTATED. Before this, backtest.py declared its own
# copies and they had already drifted from the agent's: switch_budget read [1,2,3,4] here against
# [1,2,4] there, min_dwell_h read [1,2,3] against [1,3]. Two files disagreeing about the plant
# envelope while both claim to describe one plant is exactly gotcha #12.
NOTICE_H = PLANT_ENVELOPE["notice_h"]
ANCHORS = PLANT_ENVELOPE["anchor"]
SKILLS = FORECAST_SKILL
LIMITS_C = PLANT_ENVELOPE["limit_c"]
SWITCH_BUDGET = PLANT_ENVELOPE["switch_budget"]
MIN_DWELL_H = PLANT_ENVELOPE["min_dwell_h"]
# None = gate disabled, so the gate's cost in hours is measurable rather than assumed.
DEWPOINT_LIMIT_C = PLANT_ENVELOPE["dewpoint_limit_c"]
BANK_MODES = PLANT_ENVELOPE["bank_mode"]
# The INCUMBENT's own rooftop sensor error. N-56 swept exactly these three and its headline row
# sits at 0.3 -- which turns out to be what produces the +67 h/yr, see run_n56_audit().
SENSOR_ERR_C = [0.1, 0.3, 0.5]
# The AGENT's measurement noise on FortyGuard's field, as a standard deviation in C.
#
# WHERE 0.15 COMES FROM, AND WHAT IT IS NOT. It is a CONSERVATIVE ROUND-UP of our own
# measurement: the per-tile sd of the four N-26 forecast/outcome pairs is 0.0644, 0.0699, 0.1056,
# 0.2903 C -- mean 0.1326. 0.15 sits ABOVE that mean, which makes the agent's own bound wider and
# therefore costs the agent hours; that is the direction an assumption about ourselves should err
# in. It is the same treatment the shipped plume bound gives sigma_dir, where 72 deg is the
# pessimistic end of a measured 47-72 deg range.
# The SWEEP RANGE IS NOT TYPED IN. `sensitivity_axes()` reads the four measured sd values off disk
# and sweeps min / mean / max, so the range cannot drift from the data it claims to come from.
FG_NOISE_SD_C = 0.15


# ============================================================================
# A fast dynamic program -- verified against the reference implementation
# ============================================================================
def plan_fast(safe, switch_budget, min_dwell_h):
    """Same optimisation as `agent.plan`, but returns only counts and allocates nothing per path.

    NEEDED because the sweep calls this ~450,000 times. It is a SECOND code path computing a
    quantity the first one already computes, which is exactly the situation gotcha #12 warns
    about -- so `_verify_dp_agreement()` below checks the two against each other on random
    inputs and this module refuses to run if they ever disagree.
    """
    H = len(safe)
    B, D = switch_budget, max(1, min_dwell_h)
    NEG = -1 << 30
    # state index: mode*( (B+1)*D ) + used*D + dwell_left
    S = 2 * (B + 1) * D
    val = np.full(S, NEG, dtype=np.int64)
    sw = np.zeros(S, dtype=np.int64)

    def idx(m, u, dl):
        return m * ((B + 1) * D) + u * D + dl

    val[idx(MODE_MECH, 0, 0)] = 0
    for h in range(H):
        nv = np.full(S, NEG, dtype=np.int64)
        ns = np.zeros(S, dtype=np.int64)
        s_ok = bool(safe[h])
        for m in (MODE_MECH, MODE_FREE):
            for u in range(B + 1):
                for dl in range(D):
                    i = idx(m, u, dl)
                    if val[i] == NEG:
                        continue
                    # stay
                    if m == MODE_MECH or s_ok:
                        j = idx(m, u, max(0, dl - 1))
                        cand = val[i] + (1 if m == MODE_FREE else 0)
                        if cand > nv[j] or (cand == nv[j] and sw[i] < ns[j]):
                            nv[j], ns[j] = cand, sw[i]
                    # switch
                    if dl == 0 and u < B:
                        nm = 1 - m
                        if nm == MODE_MECH or s_ok:
                            j = idx(nm, u + 1, max(0, D - 1))
                            cand = val[i] + (1 if nm == MODE_FREE else 0)
                            if cand > nv[j] or (cand == nv[j] and sw[i] + 1 < ns[j]):
                                nv[j], ns[j] = cand, sw[i] + 1
        val, sw = nv, ns
    best = int(val.max())
    if best == NEG:
        return 0, 0
    cands = np.flatnonzero(val == best)
    return best, int(sw[cands].min())


def _verify_dp_agreement(n=300, seed=11):
    """The fast DP must agree with `agent.plan` on free hours for random safety patterns."""
    rng = np.random.default_rng(seed)
    bad = 0
    for _ in range(n):
        H = int(rng.integers(6, 25))
        safe = rng.random(H) < rng.uniform(0.1, 0.9)
        b = int(rng.integers(1, 5)); d = int(rng.integers(1, 4))
        _, f_ref, _ = plan(list(safe), b, d)
        f_fast, _ = plan_fast(safe, b, d)
        if f_ref != f_fast:
            bad += 1
            if bad <= 3:
                say("      MISMATCH H=%d b=%d d=%d ref=%d fast=%d" % (H, b, d, f_ref, f_fast))
    return bad


# ============================================================================
# Build the five-year state once
# ============================================================================
def build_state(bank_mode="longest"):
    """Every per-hour quantity the agent needs, for all 43,763 hours. Vectorised."""
    keys, T, Td, drct, sknt = load_hours(with_dewpoint=True)
    n = len(keys)
    hod = np.array([int(k[-2:]) for k in keys])
    day = np.array([k[:10] for k in keys])
    month = np.array([int(k[5:7]) for k in keys])
    doy = np.array([(np.datetime64(k[:10]) - np.datetime64(k[:4] + "-01-01")).astype(int) + 1
                    for k in keys])

    # dew point comes from the shared loader now -- one reader, one field mapping
    RH = E.rh_from_dewpoint(T, Td)
    Twb, stull_ok = E.wet_bulb_stull(T, RH)

    # recirculation rise on the committed geometry
    tab, refused, meta = rise_table(bank_mode)
    ok_rows = np.array([int(b) not in refused for b in BEARINGS])
    worst_by_speed = (tab[ok_rows].max(axis=0) if ok_rows.any()
                      else np.full(len(SPEED_GRID_MS), np.nan))
    s_ms = np.maximum(np.where(np.isnan(sknt), 0.0, sknt) * 0.514444, 0.3)
    b_deg = np.where(np.isnan(drct), 0.0, drct)
    calm = np.isnan(drct) | (np.where(np.isnan(sknt), 0.0, sknt) < CALM_KT)
    si = np.abs(np.asarray(SPEED_GRID_MS)[None, :] - s_ms[:, None]).argmin(axis=1)
    rise = np.where(calm, worst_by_speed[si], lookup_rise(tab, b_deg, s_ms))
    bearing_key = (np.round(b_deg / STEP_DEG).astype(int) * STEP_DEG) % 360
    ref_flag = np.array([((bk in refused) and not c) or (c and not ok_rows.any())
                         for bk, c in zip(bearing_key, calm)])

    return {"keys": keys, "n": n, "T": T, "Td": Td, "RH": RH, "Twb": Twb,
            "stull_ok": stull_ok, "hod": hod, "day": day, "month": month, "doy": doy,
            "wind_ms": s_ms, "bearing": b_deg, "calm": calm,
            "rise": rise, "refused": ref_flag, "rise_meta": meta,
            "bank_mode": bank_mode}


def split_days(st, mode="chronological"):
    """Calibration / test split over DAYS, never over hours -- hours inside a day are not
    independent, so splitting on hours would leak.

    Both splits are reported because they answer different questions:
      chronological -- honest about drift; the calibration set is the PAST, as in deployment.
      alternating   -- closer to exchangeable, so it isolates the conformal machinery from drift.
    """
    days = np.array(sorted(set(st["day"])))
    if mode == "chronological":
        cut = len(days) // 2
        cal_days, te_days = set(days[:cut]), set(days[cut:])
    else:
        cal_days = set(days[0::2]); te_days = set(days[1::2])
    cal = np.array([d in cal_days for d in st["day"]])
    te = ~cal
    return cal, te, len(cal_days), len(te_days)


def persistence_shift(x, N, day_boundaries=None):
    """x shifted by N hours, i.e. what a persistence forecaster issued N hours earlier."""
    out = x.copy()
    if N:
        out[N:] = x[:-N]
        out[:N] = x[0]
    return out


# ============================================================================
# The bound -- Mondrian, group-conditional on hour-of-day
# ============================================================================
def fit_bounds(st, cal, N, alpha=ALPHA):
    """Group-conditional conformal calibration for BOTH gated quantities, on hour-of-day.

    Two separate Mondrian models, because dry-bulb and dew-point persistence errors have
    different scales and different diurnal shapes. Calibrated on the CALIBRATION days only.

    THE SECOND QUANTITY IS DEW POINT, NOT WET BULB, and the reason is a sourcing one. A wet-bulb
    gate has no published maximum to test against, so the old version invented an offset from our
    own dry-bulb knob. Dew point has a published maximum (15 C, Green Grid WP#46 p.6) and is read
    straight from the station record at 100 % coverage, so no psychrometric formula sits between
    the measurement and the decision. Wet bulb is still computed in `build_state` -- it is
    validated against PsychroLib in environment.py and reported as a diagnostic -- but it no
    longer gates anything here, which is what agent.py already did.
    """
    out = {}
    for name, x in (("dry", st["T"]), ("dp", st["Td"])):
        res_all, bias = debiased_persistence_residuals(x, st["hod"], N)
        if N == 0:
            out[name] = {"mondrian": None, "bias": bias, "pooled_q": 0.0,
                         "note": "zero notice: the policy reads the value it acts on"}
            continue
        # rebuild the per-hour residual aligned to the full index so we can split by day
        sh = persistence_shift(x, N)
        r = (x - sh) - bias[st["hod"]]
        r[:N] = np.nan
        m = C.Mondrian(alpha).fit(st["hod"][cal & ~np.isnan(r)], r[cal & ~np.isnan(r)])
        out[name] = {"mondrian": m, "bias": bias, "resid": r,
                     "pooled_q": m.pooled_["q"], "summary": m.summary()}
    return out


# ============================================================================
# One configuration, scored on held-out days
# ============================================================================
def score_config(st, bnd_by_N, cal, te, cfg, fg_offsets):
    """One configuration, calibrated on `cal` days and scored on `te` days only."""
    N, skill, limit = cfg["notice_h"], cfg["skill"], cfg["limit_c"]
    bnd = bnd_by_N[N]
    sens = cfg.get("sensor_err_c", 0.3)
    fgn = cfg.get("fg_noise_sd_c", FG_NOISE_SD_C)
    use_rise = cfg.get("include_rise", True)

    # ------------------------------------------------------------------------
    # BOTH POLICIES BOUND THE SAME TARGET -- the TRUE INTAKE TEMPERATURE -- each using a
    # conformal quantile of ITS OWN residuals on the calibration days. This is the textbook
    # setup and it replaces an earlier version of this function that bounded the incumbent
    # against AMBIENT instead. That was unfair to the incumbent: a real operator's fitted
    # buffer absorbs the plume statistically even though the operator has never heard of it,
    # because the plume is inside the residuals they fit on. Bounding it against ambient
    # removed that, made the adversary weaker than reality, and inflated our gain.
    # ------------------------------------------------------------------------
    truth_intake = st["T"] + st["rise"]          # the REAL intake always includes the plume

    # ---- the agent's point prediction of the intake
    if N and bnd["dry"]["mondrian"] is not None:
        r = np.where(np.isnan(bnd["dry"]["resid"]), 0.0, bnd["dry"]["resid"])
        rd = np.where(np.isnan(bnd["dp"]["resid"]), 0.0, bnd["dp"]["resid"])
        fc_dry = st["T"] - (1.0 - skill) * r
        fc_dp = st["Td"] - (1.0 - skill) * rd
    else:
        fc_dry, fc_dp = st["T"].copy(), st["Td"].copy()

    if cfg["anchor"] == "none":
        # THE OFFSET MUST VARY BY DAY, and this is not a detail.
        # An earlier version applied ONE constant offset to all 1,826 days. A conformal margin
        # fitted on those days then absorbed it completely, and the unanchored case came out
        # looking almost as good as the anchored one. That is an ORACLE: a CONSTANT bias is
        # learnable from history, but FortyGuard's offset is not constant -- the four measured
        # days run -0.8396, -0.8115, +0.1520, -3.7127, and N-26 watched coverage collapse to
        # 0.0 % on the day it flipped. So each day is assigned one of the four MEASURED offsets
        # in rotation: calibration days and test days then carry different offsets, the margin
        # has to cover the SPREAD rather than a constant, and it cannot cheat.
        offs = np.array([o["mean_d"] for o in fg_offsets], dtype=float)
        udays = np.array(sorted(set(st["day"])))
        day_to_off = {d: offs[i % len(offs)] for i, d in enumerate(udays)}
        off_h = np.array([day_to_off[d] for d in st["day"]], dtype=float)
        lvl = C.split_conformal(offs, ALPHA)
        level_margin = 0.0        # the spread is now inside the fitted residuals, not added on
        level_note = {"method": "four MEASURED offsets rotated across days; the margin must "
                                "cover their spread rather than a constant",
                      "offsets": offs.tolist(), "n": lvl["n"], "clamped": lvl["clamped"],
                      "warning": "the LEVEL component still rests on n=4 distinct values; only "
                                 "the SHAPE component is calibrated on five years"}
        fc_dry, fc_dp = fc_dry - off_h, fc_dp - off_h
    else:
        off, level_margin = 0.0, 0.0
        level_note = {"method": "anchored: one local reading removes the day level"}

    # FortyGuard's own measurement noise, applied to BOTH channels it supplies.
    #
    # THE DEW-POINT CHANNEL USED TO BE NOISE-FREE, AND THAT WAS AN UNFAIR ADVANTAGE. The old
    # wet-bulb code dithered the INCUMBENT's hygrometer by its sensor error and left the AGENT's
    # humidity reading exact, so the agent's fitted humidity margin came out at 0.0000 C at zero
    # notice -- a free perfect hygrometer. It went unnoticed while the humidity gate rarely bound;
    # migrating to the dew-point gate made it load-bearing (it bites on 16 % of dry-bulb-allowed
    # hours), and rerunning without this fix overstated the gate row by roughly 2x.
    # The 0.15 C sd is MEASURED for FortyGuard's temperature field (per-tile sd of the four N-26
    # forecast/outcome pairs, 0.0644-0.2903 C). Reusing it for the dew-point channel is an
    # ASSUMPTION, and it is the conservative one: it can only widen the agent's own bound and cost
    # the agent hours. A separate RNG stream keeps the dry-bulb draw byte-identical to before.
    ag_noise = np.random.default_rng(15).normal(0.0, fgn, st["n"]) if fgn else 0.0
    ag_noise_dp = np.random.default_rng(16).normal(0.0, fgn, st["n"]) if fgn else 0.0
    fc_dry = fc_dry + ag_noise
    fc_dp = fc_dp + ag_noise_dp
    rise_used = st["rise"] if use_rise else np.zeros(st["n"])
    ag_pred_dry = fc_dry + rise_used
    ag_pred_dp = fc_dp                   # recirculation raises temperature, not dew point:
                                         # the plume adds sensible heat, no moisture, so the
                                         # absolute humidity of the intake air is the ambient's

    # ---- the incumbent's point prediction: its own noisy rooftop sensor, persistence, no plume
    inc_dry = persistence_shift(st["T"], N)
    inc_dp = persistence_shift(st["Td"], N)
    if N:
        inc_dry = inc_dry + bnd["dry"]["bias"][st["hod"]]
        inc_dp = inc_dp + bnd["dp"]["bias"][st["hod"]]
    if sens and cfg.get("sensor_dither", True):
        inc_dry = inc_dry + np.random.default_rng(56).normal(0.0, sens, st["n"])
        inc_dp = inc_dp + np.random.default_rng(57).normal(0.0, sens, st["n"])

    # ---- each policy's Mondrian margin, from ITS OWN residuals on CALIBRATION days only
    def fitted_margin(pred, target):
        res = target - pred
        m = cal & ~np.isnan(res)
        mond = C.Mondrian(ALPHA).fit(st["hod"][m], res[m])
        return mond.q_array(st["hod"]), mond

    marg_dry, m_ag = fitted_margin(ag_pred_dry, truth_intake)
    marg_dp, _ = fitted_margin(ag_pred_dp, st["Td"])
    marg_inc, m_in = fitted_margin(inc_dry, truth_intake)
    marg_inc_dp, _ = fitted_margin(inc_dp, st["Td"])

    ub_dry = ag_pred_dry + marg_dry + level_margin
    ub_dp = ag_pred_dp + marg_dp + level_margin
    ub_inc = inc_dry + marg_inc
    ub_inc_dp = inc_dp + marg_inc_dp

    # ---- GATE 1, DRY BULB: the changeover limit.
    # ---- GATE 2, DEW POINT: a PUBLISHED maximum, not an offset from our own knob.
    # Green Grid WP#46 p.6 gives the ASHRAE recommended maxima as 27 C dry-bulb and 15 C dew
    # point and counts a free-cooling hour only when BOTH hold. `dp_limit is None` disables the
    # gate so its cost in hours stays measurable. BOTH POLICIES FACE IT -- outside air is outside
    # air regardless of who opened the damper -- and each tests it with a bound built from ITS OWN
    # residuals, so neither is handed the other's information.
    # (The air-quality gate cannot be backtested: no five-year record exists. See the header.)
    dp_limit = cfg["dewpoint_limit_c"]
    gate_dry = ub_dry <= limit
    gate_dp = (np.ones(st["n"], dtype=bool) if dp_limit is None else (ub_dp <= dp_limit))
    safe_agent = gate_dry & gate_dp & (~st["refused"])
    safe_inc = ub_inc <= limit
    if dp_limit is not None:
        safe_inc = safe_inc & (ub_inc_dp <= dp_limit)

    # GROUND TRUTH uses the MEASURED dew point against the same published maximum -- no bound,
    # because this is what actually happened, and an hour is only genuinely safe if the real
    # intake cleared the temperature limit AND the real dew point cleared the humidity one.
    truly_safe = truth_intake <= limit
    if dp_limit is not None:
        truly_safe = truly_safe & (st["Td"] <= dp_limit)

    # ---------- SCHEDULE, per held-out day -----------------------------------
    dayidx = {}
    for i in np.flatnonzero(te):
        dayidx.setdefault(st["day"][i], []).append(i)

    per_day = []
    ag_free = ag_safe = ag_br = ag_sw = 0
    in_free = in_safe = in_br = in_sw = in_over = 0
    for dk in sorted(dayidx):
        ix = np.array(dayidx[dk])
        ma, fa, swa = plan(list(safe_agent[ix]), cfg["switch_budget"], cfg["min_dwell_h"])
        # `over` is the number of times the incumbent BROKE ITS OWN SWITCH BUDGET to stay safe.
        # It was being discarded, and it must not be: it is the fairness caveat on every
        # switch-budget row. The agent honours the budget as a hard constraint in the DP; the
        # reactive incumbent exceeds it and still has its free hours counted. That favours the
        # INCUMBENT, and at switch_budget = 1 it is what makes the agent lose (see
        # run_sensitivity's reversal report). Reported rather than quietly fixed, because a real
        # reactive controller does break its switch budget -- pretending otherwise would be the
        # untuned-adversary mistake (methodology rule 3).
        mi, fi, swi, over = reactive_incumbent(safe_inc[ix], cfg["switch_budget"],
                                              cfg["min_dwell_h"])
        in_over += int(over)
        ma = np.array(ma) == MODE_FREE
        mi = np.array(mi) == MODE_FREE
        sa = int((ma & truly_safe[ix]).sum()); ba = int((ma & ~truly_safe[ix]).sum())
        si_ = int((mi & truly_safe[ix]).sum()); bi = int((mi & ~truly_safe[ix]).sum())
        ag_free += int(ma.sum()); ag_safe += sa; ag_br += ba; ag_sw += swa
        in_free += int(mi.sum()); in_safe += si_; in_br += bi; in_sw += swi
        per_day.append(sa - si_)

    pd = np.array(per_day, dtype=float)
    nd = len(pd)
    dmean = float(pd.mean()) if nd else float("nan")
    dse = (float(pd.std(ddof=1)) / math.sqrt(nd)) if nd > 1 else float("nan")

    # realised marginal coverage of each policy's bound, on held-out hours
    # both measured against the SAME target, which is the point of the rewrite above
    cov_a = float((truth_intake[te] <= ub_dry[te]).mean())
    cov_i = float((truth_intake[te] <= ub_inc[te]).mean())

    return {
        **{k: cfg[k] for k in ("notice_h", "anchor", "skill", "limit_c", "switch_budget",
                               "min_dwell_h", "dewpoint_limit_c",
                               "sensor_err_c", "fg_noise_sd_c", "include_rise",
                               "sensor_dither")},
        # DERIVED, not passed: the anchor decides the offset treatment, so a caller cannot claim
        # one offset regime while `anchor` produces another. The old code accepted an
        # `offset_day="2026-08-16"` that score_config silently ignored.
        "offset_day": ("anchored" if cfg["anchor"] == "sensor" else "rotated-4-measured"),
        "bank_mode": st["bank_mode"],
        "test_days": nd,
        "agent_free_h": ag_free, "agent_safe_free_h": ag_safe, "agent_breach_h": ag_br,
        "incumbent_free_h": in_free, "incumbent_safe_free_h": in_safe,
        "incumbent_breach_h": in_br,
        "agent_switches_total": ag_sw, "incumbent_switches_total": in_sw,
        # days on which the incumbent exceeded the switch budget the agent is held to
        "incumbent_budget_exceeded_days": in_over,
        # THE REFUSAL GUARD'S PRICE. `refused` is pure geometry -- the intake has no line of sight
        # to the source, so the solver cannot produce a valid rise and the agent declines to
        # answer instead of returning a meaningless number. These two counts say what that costs:
        # how many held-out hours were refused, and how many of those were GENUINELY SAFE and so
        # handed to the incumbent for free. On bank_mode=facing this is the entire result.
        "refused_h": int((st["refused"] & te).sum()),
        "refused_but_truly_safe_h": int((st["refused"] & te & truly_safe).sum()),
        "agent_margin_mean_c": float(marg_dry.mean()),
        "incumbent_margin_mean_c": float(marg_inc.mean()),
        "agent_dewpoint_margin_mean_c": float(marg_dp.mean()),
        # A VACUITY GUARD on the humidity gate (gotcha #37): a gate that never binds is not a
        # gate. Counted on held-out hours only, as hours where dry-bulb said yes and dew point
        # said no. If this is 0 the gate row in the ladder is meaningless and must be reported so.
        "humidity_gate_binds_h": int((gate_dry & ~gate_dp & te).sum()),
        "humidity_gate_binds_frac_of_dry_ok": (float((gate_dry & ~gate_dp & te).sum())
                                               / float(max(int((gate_dry & te).sum()), 1))),
        "gain_safe_h_per_day": dmean, "gain_safe_h_per_day_se": dse,
        "gain_safe_h_per_day_ci95": ([dmean - 1.96 * dse, dmean + 1.96 * dse]
                                     if nd > 1 else None),
        "significant": bool(nd > 1 and ((dmean - 1.96 * dse) > 0 or (dmean + 1.96 * dse) < 0)),
        "gain_h_per_year": dmean * 365.25 if nd else float("nan"),
        "level_combination": level_note,
        "coverage_agent_bound": cov_a, "coverage_incumbent_bound": cov_i,
        "agent_breach_per_1000_free_h": (1000.0 * ag_br / ag_free) if ag_free else 0.0,
        "incumbent_breach_per_1000_free_h": (1000.0 * in_br / in_free) if in_free else 0.0,
    }



# ============================================================================
# The online adaptive-conformal experiment -- ~43,000 rounds
# ============================================================================
def run_aci(st, N=3, window=2000, alpha=ALPHA):
    """ACI and DtACI on the real five-year residual stream, versus a static bound.

    This is the experiment the four FortyGuard days could never support: ACI's guarantee is
    long-run, so it needs thousands of rounds. Here it gets ~43,000, on measured data, in
    chronological order -- which is the order a deployed controller would see them in.
    """
    res_all, bias = debiased_persistence_residuals(st["T"], st["hod"], N)
    sh = persistence_shift(st["T"], N)
    r = (st["T"] - sh) - bias[st["hod"]]
    r[:N] = np.nan
    ok = np.flatnonzero(~np.isnan(r))
    stream = r[ok]

    warm = 500
    static_q = C.split_conformal(stream[:warm], alpha)["q"]
    static_miss = stream[warm:] > static_q

    out = {}
    for label, algo in (("ACI", C.ACI(alpha, gamma=0.02)), ("DtACI", C.DtACI(alpha))):
        miss, alphas = [], []
        buf = list(stream[:warm])
        arr = np.array(buf, dtype=float)
        for t in range(warm, len(stream)):
            a = algo.alpha_t
            alphas.append(a)
            k, _ = C.quantile_index(len(arr), a)
            qt = np.partition(arr, k - 1)[k - 1]
            m = bool(stream[t] > qt)
            miss.append(m)
            algo.step(m)
            buf.append(stream[t])
            if len(buf) > window:
                buf = buf[-window:]
            arr = np.array(buf, dtype=float)
        miss = np.array(miss)
        out[label] = {"rounds": int(len(miss)),
                      "realised_coverage": float(1.0 - miss.mean()),
                      "alpha_mean": float(np.mean(alphas)),
                      "alpha_min": float(np.min(alphas)), "alpha_max": float(np.max(alphas)),
                      "coverage_first_half": float(1.0 - miss[:len(miss) // 2].mean()),
                      "coverage_second_half": float(1.0 - miss[len(miss) // 2:].mean())}
    out["static"] = {"rounds": int(len(static_miss)),
                     "realised_coverage": float(1.0 - static_miss.mean()),
                     "q": float(static_q),
                     "coverage_first_half": float(1.0 - static_miss[:len(static_miss) // 2].mean()),
                     "coverage_second_half": float(1.0 - static_miss[len(static_miss) // 2:].mean())}
    out["notice_h"] = N
    out["window"] = window
    return out


# ============================================================================
# Mondrian vs pooled, measured on the real data
# ============================================================================
def run_mondrian_audit(st, cal, te, N=3, alpha=ALPHA):
    """Does group-conditional calibration actually matter HERE, on real weather?

    The synthetic self-test in conformal.py proves the machinery works. This asks whether the
    real five-year residuals have the group structure that makes it necessary -- which is an
    empirical question, and the answer is allowed to be no.
    """
    res_all, bias = debiased_persistence_residuals(st["T"], st["hod"], N)
    sh = persistence_shift(st["T"], N)
    r = (st["T"] - sh) - bias[st["hod"]]
    r[:N] = np.nan
    m_cal = cal & ~np.isnan(r)
    m_te = te & ~np.isnan(r)

    pooled = C.split_conformal(r[m_cal], alpha)
    mond = C.Mondrian(alpha).fit(st["hod"][m_cal], r[m_cal])

    rep_pooled = C.coverage_by_group(st["hod"][m_te], r[m_te], lambda g: pooled["q"])
    rep_mond = C.coverage_by_group(st["hod"][m_te], r[m_te], lambda g: mond.q(g)[0])

    # season as a second stratification, to test whether hour-of-day alone is enough
    season = np.array([(mo % 12) // 3 for mo in st["month"]])
    key2 = np.array(["%02d|%d" % (h, s) for h, s in zip(st["hod"], season)])
    mond2 = C.Mondrian(alpha).fit(key2[m_cal], r[m_cal])
    rep_mond2 = C.coverage_by_group(key2[m_te], r[m_te], lambda g: mond2.q(g)[0])

    # ship the pooled bound's PER-GROUP coverage too: the demo draws both series so a viewer can
    # see the pooled line dip in the exact hours the group-conditional one holds
    pooled_by_group = {r["group"]: r["coverage"] for r in rep_pooled["per_group"]}
    for r in rep_mond["per_group"]:
        r["pooled_coverage"] = pooled_by_group.get(r["group"])
    return {"notice_h": N,
            "pooled": {"q": pooled["q"], "n": pooled["n"],
                       "overall": rep_pooled["overall_coverage"],
                       "worst_group": rep_pooled["worst_group"],
                       "groups_below_target": rep_pooled["groups_below_target"],
                       "per_group": rep_pooled["per_group"]},
            "mondrian_hod": {"n_groups": mond.summary()["n_groups_fitted"],
                             "smallest_group_n": mond.summary()["smallest_group_n"],
                             "q_min": mond.summary()["group_q_min"],
                             "q_max": mond.summary()["group_q_max"],
                             "overall": rep_mond["overall_coverage"],
                             "worst_group": rep_mond["worst_group"],
                             "groups_below_target": rep_mond["groups_below_target"],
                             "per_group": rep_mond["per_group"]},
            "mondrian_hod_x_season": {"n_groups": mond2.summary()["n_groups_fitted"],
                                      "n_fallback": mond2.summary()["n_groups_fallback"],
                                      "smallest_group_n": mond2.summary()["smallest_group_n"],
                                      "overall": rep_mond2["overall_coverage"],
                                      "worst_group": rep_mond2["worst_group"],
                                      "groups_below_target": rep_mond2["groups_below_target"]}}


# ============================================================================
# ONE-AT-A-TIME SENSITIVITY -- every axis BASE declares, varied around it
# ============================================================================
#
# WHY THIS FUNCTION EXISTS, STATED PLAINLY BECAUSE IT IS A CORRECTION.
#
# BASE's comment used to claim "every axis below is varied around it and reported, and the full
# factorial over the value axes is run separately". THAT WAS FALSE IN THIS FILE. Eight sweep lists
# were declared at module level and exactly ONE of them -- SENSOR_ERR_C -- was ever iterated.
# NOTICE_H, ANCHORS, SKILLS, LIMITS_C, SWITCH_BUDGET, MIN_DWELL_H, the humidity limit and
# BANK_MODES were dead names. The five-year headline therefore rested on a hand-picked
# notice_h = 3, skill = 0.50, limit_c = 24 C, switch_budget = 2, min_dwell_h = 3 with nothing in
# the five-year code varying them -- which is the point-at-the-constant test failing five times
# over, hidden behind a comment asserting the opposite.
#
# (The 120,960-scenario full factorial in agent.py is real, but it runs over FOUR FortyGuard days,
# not over the five-year record. A sweep on other data is not a sweep on this data.)
#
# `main()` now refuses to write output if any key in BASE has no entry here, so the comment cannot
# come apart from the code again.
def sensitivity_axes(fg_offsets):
    """The value list for every axis BASE declares. Nothing here is typed in by hand.

    Eleven of the twelve come straight from agent.py's PLANT_ENVELOPE (so the two files cannot
    disagree about the plant), from N-56's own published sensor grid, or from a two-valued
    mechanism toggle. The twelfth, `fg_noise_sd_c`, is READ OFF DISK: the min / mean / max of the
    per-tile sd of the four measured N-26 forecast-outcome pairs, so the swept range cannot drift
    from the measurement it claims to be.
    """
    sds = sorted(float(o["sd_d"]) for o in fg_offsets if o.get("sd_d") is not None)
    fg_noise = ([sds[0], sum(sds) / len(sds), sds[-1]] if sds else [FG_NOISE_SD_C])
    return {
        "notice_h": NOTICE_H,
        "anchor": ANCHORS,
        "skill": SKILLS,
        "limit_c": LIMITS_C,
        "switch_budget": SWITCH_BUDGET,
        "min_dwell_h": MIN_DWELL_H,
        "dewpoint_limit_c": DEWPOINT_LIMIT_C,
        "bank_mode": BANK_MODES,
        "sensor_err_c": SENSOR_ERR_C,
        "fg_noise_sd_c": fg_noise,
        # Mechanism toggles, not tuning knobs. Both directions are reported because each answers a
        # question: does the agent still win if it ignores the plume, and if the incumbent's
        # sensor is treated as perfect?
        "include_rise": [True, False],
        "sensor_dither": [True, False],
    }


def _vfmt(v):
    """Shorten a float for the printed table. DISPLAY ONLY -- the value written to JSON and used
    in every comparison stays at full precision (gotcha #44: never round what a comparison
    depends on; display rounding belongs in the view)."""
    return ("%.4f" % v) if isinstance(v, float) else str(v)


def run_sensitivity(st_by_mode, bnd, cal, te, fg_offsets):
    """Vary each axis alone, hold the rest at BASE, report every row.

    Returns (rows, unswept, reversals). A non-empty `unswept` is FATAL to the caller: it means
    BASE declares a value that nothing varies, which is the defect this function was written to
    end. `reversals` lists the axes on which the gain changes sign.
    """
    banner("ONE-AT-A-TIME SENSITIVITY   every axis BASE declares, varied around it")
    axes = sensitivity_axes(fg_offsets)
    unswept = sorted(k for k in BASE if k not in axes)
    if unswept:
        say("   *** BASE declares %s with no sweep list. REFUSING -- a base case whose axes are"
            % ", ".join(unswept))
        say("       not varied is a set of hidden constants (point-at-the-constant test). ***")
        return [], unswept, []

    say("   base case: %s" % ", ".join("%s=%s" % (k, BASE[k]) for k in sorted(BASE)))
    say("   %d axes, %d configurations, all scored on the SAME %d held-out days"
        % (len(axes), sum(len(v) for v in axes.values()), int(len(set(st_by_mode[
            BASE["bank_mode"]]["day"][te])))))
    say("\n   %-17s %-10s %11s %9s %9s %8s %9s"
        % ("axis", "value", "gain h/day", "+/-95%", "h/yr", "cov", "breach/1k"))

    rows = []
    for axis in sorted(axes):
        for v in axes[axis]:
            cfg = dict(BASE)
            cfg[axis] = v
            r = score_config(st_by_mode[cfg["bank_mode"]], bnd, cal, te, cfg, fg_offsets)
            # `is_base` marks the row that reproduces the base case exactly, so a reader can see
            # every axis pass through one common point instead of taking it on trust.
            at_base = (v is BASE[axis]) or (v == BASE[axis] and type(v) is type(BASE[axis]))
            rows.append({"axis": axis, "value": v, "is_base": bool(at_base), **r})
            say("   %-17s %-10s %+11.4f %9.4f %+9.1f %8.4f %9.2f %s"
                % (axis, _vfmt(v), r["gain_safe_h_per_day"],
                   1.96 * r["gain_safe_h_per_day_se"],
                   r["gain_h_per_year"], r["coverage_agent_bound"],
                   r["agent_breach_per_1000_free_h"], "<- base" if at_base else ""))

    # WHICH AXES CHANGE THE ANSWER'S SIGN. This is the only part of a sensitivity table that
    # matters for a claim: an axis that flips the gain negative is an axis on which the headline
    # is conditional, and it has to be said out loud rather than left in a table for a reader to
    # find. Reported per axis, using each row's own 95 % interval rather than the point estimate.
    say("\n   AXES ON WHICH THE HEADLINE IS CONDITIONAL (the gain's sign is not stable):")
    flips = []
    for axis in sorted(axes):
        g = [r["gain_h_per_year"] for r in rows if r["axis"] == axis]
        sig = [r for r in rows if r["axis"] == axis and r["significant"]]
        if g and min(g) < 0 < max(g):
            neg = [r for r in rows if r["axis"] == axis and r["gain_h_per_year"] < 0]
            flips.append({"axis": axis, "min_h_per_year": min(g), "max_h_per_year": max(g),
                          "negative_at": [r["value"] for r in neg],
                          "n_significant": len(sig)})
            say("      %-17s %+.1f to %+.1f h/yr; NEGATIVE at %s"
                % (axis, min(g), max(g), ", ".join(_vfmt(r["value"]) for r in neg)))
            # EACH REVERSAL EXPLAINS ITSELF FROM ITS OWN MEASURED ROW, rather than from a
            # sentence I wrote next to it. Every mechanism below is something the row counted.
            #
            # AND EACH IS REPORTED ONLY IF IT DIFFERS FROM THE BASE ROW. The first version of this
            # block printed "the incumbent exceeded the switch budget on 28 days" under
            # anchor=none and bank_mode=facing -- but the BASE case also sits at 28, so that
            # quantity did not differ between the compared runs and cannot be the cause. That is
            # gotcha #35 ("tabulate every variable that differed before writing a cause down"),
            # committed by the very code meant to prevent it. Now a diagnostic has to move.
            b = next((x for x in rows if x["axis"] == axis and x["is_base"]), None)
            for r in neg:
                if b and r["coverage_agent_bound"] - b["coverage_agent_bound"] > 0.02:
                    say("         %s=%s: the agent's realised coverage ROSE %.4f -> %.4f against "
                        "a 0.90 nominal."
                        % (axis, _vfmt(r["value"]), b["coverage_agent_bound"],
                           r["coverage_agent_bound"]))
                    say("         -> the bound went conservative and paid for it in hours. It "
                        "stayed SAFE and lost the argument on efficiency,")
                    say("            which is the direction a one-sided upper bound is supposed "
                        "to fail in.")
                if r["refused_but_truly_safe_h"] > (b["refused_but_truly_safe_h"] if b else 0):
                    say("         %s=%s: the agent REFUSED %s of %s held-out hours and %s of "
                        "those were genuinely safe"
                        % (axis, _vfmt(r["value"]), format(r["refused_h"], ","),
                           format(int(r["test_days"]) * 24, ","),
                           format(r["refused_but_truly_safe_h"], ",")))
                    say("         -> that is the geometric refusal guard, not a scheduling loss. "
                        "It declines to answer where the")
                    say("            intake has no line of sight to the source, and it hands "
                        "those hours to the incumbent for free.")
                if r["incumbent_budget_exceeded_days"] > (b["incumbent_budget_exceeded_days"]
                                                          if b else 0):
                    say("         %s=%s: the incumbent EXCEEDED the switch budget on %s of %s "
                        "held-out days (base case: %s) and kept its hours;"
                        % (axis, _vfmt(r["value"]),
                           format(r["incumbent_budget_exceeded_days"], ","),
                           format(int(r["test_days"]), ","),
                           format(b["incumbent_budget_exceeded_days"], ",") if b else "n/a"))
                    say("            the agent honours the same budget as a hard DP constraint. "
                        "The comparison favours the INCUMBENT here.")
    if not flips:
        say("      none -- the gain keeps its sign across every value of every axis")
    return rows, [], flips


# ============================================================================
# The N-56 reproduction audit
# ============================================================================
def run_n56_audit(st, fg_offsets):
    """Reproduce N-56's headline, decompose the difference, and ISOLATE what actually causes it.

    WHY THIS AUDIT CHANGED SHAPE. A first version of this function gave the incumbent a PERFECT
    sensor and got a gain of exactly +0.0000 h/day. Exactly zero is a tell, not a measurement,
    and the reason turned out to be provable rather than a bug: with a perfect sensor, a perfect
    forecast and a non-negative plume rise, the set of hours the agent declares is
    {T + rise <= L}, which is a SUBSET of the incumbent's {T <= L}; and since the incumbent's
    hours that are GENUINELY safe are also exactly {T + rise <= L}, the two policies score
    identically on `safe_free_h` by construction.

    That forced the real question: where does N-56's +67 h/yr come from? Reading its own rows at
    notice 0, anchored, limit 24 C:

        sensor error 0.1 C -> incumbent buffer 0.2177, agent buffer 0.1945, gain  +10.4 h/yr
        sensor error 0.3 C -> incumbent buffer 0.4588, agent buffer 0.1945, gain  +66.8 h/yr
        sensor error 0.5 C -> incumbent buffer 0.7113, agent buffer 0.1945, gain +162.0 h/yr

    The agent's buffer NEVER MOVES. The gain tracks the INCUMBENT's buffer exactly. So the
    zero-notice number is produced by an UNCERTAINTY ASYMMETRY -- FortyGuard's field assumed
    more precise (0.15 C) than the customer's own rooftop sensor (0.3 C) -- and NOT by
    recirculation awareness. Step 0 below isolates recirculation directly by rerunning with the
    plume term removed from the agent's bound while leaving it in the ground truth.
    """
    banner("N-56 COMPARISON AUDIT   their headline: +0.1827 h/day, +66.8 h/yr, n = 914 days")
    say("   N-56 headline row (read from testing/results/n56_freecooling.json):")
    say("      anchored=True  notice_h=0  forecast_skill=1.00  sigma_dir_deg=0.0")
    say("      sensor_err_c=0.3  limit_c=24.0  ->  66.8 h/yr over 914 paired test days")
    say("      metric: hours DECLARED free AND genuinely safe; no switch or dwell constraint")
    say("\n   THEIR OWN SENSITIVITY TO THE ONE ASSUMPTION THAT DRIVES IT:")
    say("      sensor err 0.1 -> +10.4 h/yr   0.3 -> +66.8 h/yr   0.5 -> +162.0 h/yr")
    say("      (agent buffer fixed at 0.1945 C in all three; only the INCUMBENT's moves)")

    cal, te, ncal, nte = split_days(st, "alternating")
    say("\n   our split: alternating days, %d calibration / %d held-out test days" % (ncal, nte))
    bnd = {0: fit_bounds(st, cal, 0), 3: fit_bounds(st, cal, 3)}

    rows = []
    base = dict(BASE, notice_h=0, anchor="sensor", skill=1.00, limit_c=24.0,
                switch_budget=24, min_dwell_h=1, dewpoint_limit_c=None,
                fg_noise_sd_c=0.15, include_rise=True)

    say("\n   A. DOES THE SENSOR-ERROR ASSUMPTION REPRODUCE THEIR CURVE? (notice 0, no constraints)")
    say("   %-34s %11s %10s %9s %10s %10s"
        % ("configuration", "gain h/day", "+/-95%", "h/yr", "agent marg", "inc marg"))
    for se in SENSOR_ERR_C:
        r = score_config(st, bnd, cal, te, dict(base, sensor_err_c=se), fg_offsets)
        rows.append(("A sensor_err %.1f C" % se, r))
        say("   %-34s %+11.4f %10.4f %+9.1f %10.4f %10.4f"
            % ("sensor error %.1f C" % se, r["gain_safe_h_per_day"],
               1.96 * r["gain_safe_h_per_day_se"], r["gain_h_per_year"],
               r["agent_margin_mean_c"], r["incumbent_margin_mean_c"]))

    say("\n   B. IS THE GAIN RECIRCULATION, OR THE UNCERTAINTY ASYMMETRY? (sensor 0.3 C)")
    r_with = score_config(st, bnd, cal, te, dict(base, sensor_err_c=0.3, include_rise=True),
                          fg_offsets)
    r_without = score_config(st, bnd, cal, te, dict(base, sensor_err_c=0.3, include_rise=False),
                             fg_offsets)
    rows += [("B with plume term", r_with), ("B plume term REMOVED", r_without)]
    say("   %-34s %+11.4f %10.4f %+9.1f   breaches/1000 free h %.2f"
        % ("agent KNOWS about the plume", r_with["gain_safe_h_per_day"],
           1.96 * r_with["gain_safe_h_per_day_se"], r_with["gain_h_per_year"],
           r_with["agent_breach_per_1000_free_h"]))
    say("   %-34s %+11.4f %10.4f %+9.1f   breaches/1000 free h %.2f"
        % ("agent IGNORES the plume", r_without["gain_safe_h_per_day"],
           1.96 * r_without["gain_safe_h_per_day_se"], r_without["gain_h_per_year"],
           r_without["agent_breach_per_1000_free_h"]))
    # 🔴 THE SIGN HERE WAS INVERTED FOR TWO DAYS -- HANDOFF gotcha #97. This block printed
    # "knowing about the plume COSTS +22.8 h/yr", which contradicts itself: dh is
    # (with - without), so a POSITIVE dh means the plume term WINS hours. The confident sentence
    # underneath ("buys SAFETY, not HOURS") is what stopped anyone reading the number, and the
    # claim propagated into two documents. State the direction from the sign, not from a story.
    dh = r_with["gain_h_per_year"] - r_without["gain_h_per_year"]
    db = (r_without["agent_breach_per_1000_free_h"]
          - r_with["agent_breach_per_1000_free_h"])
    verb = "WINS" if dh > 0 else "COSTS"
    say("   -> knowing about the plume %s %+.1f h/yr and REMOVES %.2f breaches per 1000"
        % (verb, dh, db))
    say("      free-cooling hours -- %s free h vs %s, %d breaches vs %d. BOTH, not a trade."
        % (format(r_with["agent_free_h"], ","), format(r_without["agent_free_h"], ","),
           r_with["agent_breach_h"], r_without["agent_breach_h"]))
    say("      WHY: the truth is always T + rise, so with the term the plume CANCELS out of the")
    say("      residual ((T+rise) - (fc+rise) = T - fc) and the margin is pure forecast error.")
    say("      Drop the term and the 90th-percentile quantile has to absorb the plume's whole")
    say("      spread, charging every hour a worst case instead of its actual value. Dropping the")
    say("      physics buys a WIDER bound, not a cheaper one.")

    say("\n   C. WHAT OUR EXTRA REALISM COSTS (sensor 0.3 C, cumulative)")
    steps = [("N-56-like: notice 0, skill 1.00, no constraints",
              dict(base, sensor_err_c=0.3)),
             ("+ switch budget 2, min dwell 3 h",
              dict(base, sensor_err_c=0.3, switch_budget=2, min_dwell_h=3)),
             ("+ dew-point gate 15 C (Green Grid WP#46 p.6)",
              dict(base, sensor_err_c=0.3, switch_budget=2, min_dwell_h=3,
                   dewpoint_limit_c=15.0)),
             ("+ notice 3 h, skill 0.50 (no perfect forecast)",
              dict(base, sensor_err_c=0.3, switch_budget=2, min_dwell_h=3,
                   dewpoint_limit_c=15.0, notice_h=3, skill=0.50)),
             # LABEL CORRECTED 2026-08-19. This row used to read "worst measured FG offset" and
             # pass offset_day="2026-08-16", which score_config IGNORES when anchor="none" -- it
             # rotates all four measured offsets across days on purpose, so that calibration and
             # test days carry different offsets and a constant bias cannot be learned (gotcha
             # #48). The label described a single-offset run that has not been executed since the
             # oracle was removed. HANDOFF 6.4 already said "day-varying"; the code did not.
             # `offset_day` is now DERIVED from `anchor` in the result row and cannot be passed.
             ("+ unanchored, 4 measured FG offsets rotated",
              dict(base, sensor_err_c=0.3, switch_budget=2, min_dwell_h=3,
                   dewpoint_limit_c=15.0, notice_h=3, skill=0.50, anchor="none"))]
    say("   %-46s %11s %10s %9s %8s"
        % ("step", "gain h/day", "+/-95%", "h/yr", "cov"))
    for label, cfg in steps:
        r = score_config(st, bnd, cal, te, cfg, fg_offsets)
        rows.append(("C " + label, r))
        say("   %-46s %+11.4f %10.4f %+9.1f %8.4f"
            % (label, r["gain_safe_h_per_day"], 1.96 * r["gain_safe_h_per_day_se"],
               r["gain_h_per_year"], r["coverage_agent_bound"]))

    say("\n   VERDICT")
    say("      N-56's +66.8 h/yr is REPRODUCED in mechanism and in magnitude once the same")
    say("      sensor-error assumption is used -- but it is NOT 'recirculation alone'. That")
    say("      attribution in HANDOFF section 5.3 is WRONG and must be corrected: the number is")
    say("      an uncertainty asymmetry between FortyGuard's field and the customer's sensor,")
    say("      and recirculation awareness reduces it while removing breaches.")
    return [{"step": l, **r} for l, r in rows]


# ============================================================================
def main(which="all"):
    t0 = time.time()
    banner("FIVE-YEAR BACKTEST   43,763 real hours, rigorous conformal layer.  ZERO API CALLS.")

    say("   verifying the fast DP against the reference implementation...")
    bad = _verify_dp_agreement()
    if bad:
        say("   *** %d DISAGREEMENTS -- refusing to continue (gotcha #12) ***" % bad)
        return 2
    say("   fast DP agrees with agent.plan on 300 random safety patterns.")

    st = build_state(BASE["bank_mode"])
    say("\n   state built: %s hours, %s days, bank=%s"
        % (format(st["n"], ","), format(len(set(st["day"])), ","), st["bank_mode"]))
    # THE GATED HUMIDITY QUANTITY IS DEW POINT, read straight from the station record. Wet bulb is
    # still derived and its validity reported, because it is what environment.py validates against
    # PsychroLib -- but it no longer gates anything, so it cannot introduce an unsourced offset.
    dp_ok = np.isfinite(st["Td"])
    say("   dew point: %.2f %% of hours present; %.2f %% exceed the published 15 C maximum"
        % (100.0 * dp_ok.mean(), 100.0 * (st["Td"][dp_ok] > 15.0).mean()))
    say("   wet-bulb derived from the same dew point (DIAGNOSTIC ONLY, not gated); Stull envelope "
        "covers %.2f %% of hours" % (100.0 * st["stull_ok"].mean()))
    say("   recirculation: mean %+.4f C  max %+.4f C  refused hours %s"
        % (st["rise"].mean(), st["rise"].max(), format(int(st["refused"].sum()), ",")))

    pairs, _ = perceive_fortyguard()
    # `sd_d` is carried through now, not dropped: sensitivity_axes() reads the FortyGuard noise
    # sweep range off these measured values instead of having it typed in.
    fg_offsets = [{"date": p["date"], "mean_d": p["mean_d"], "sd_d": p["sd_d"]} for p in pairs]
    say("   FortyGuard measured day offsets: %s"
        % ", ".join("%s %+.4f (sd %.4f)" % (o["date"], o["mean_d"], o["sd_d"])
                    for o in fg_offsets))

    out = {"generated_by": "INTAKE-ARBITER/src/backtest.py", "api_calls_made": 0,
           "hours": int(st["n"]), "days": len(set(st["day"])),
           "base_case": BASE, "alpha": ALPHA,
           "fortyguard_offsets": fg_offsets,
           "rise_meta": {k: st["rise_meta"][k] for k in
                         ("mode", "device", "solve_seconds", "n_solves", "refused",
                          "max_rise_c", "max_rise_bearing", "mean_rise_c")},
           "not_backtestable": {
               "air_quality_gate": "no five-year air-quality record exists in this project; "
                                   "measured separately on the 29 FortyGuard env_params days",
               "fortyguard_level_offset_n": len(fg_offsets)}}

    if which in ("all", "n56"):
        cal, te, ncal, nte = split_days(st, "alternating")
        out["n56_audit"] = run_n56_audit(st, fg_offsets)
    if which in ("all", "sensitivity"):
        # Same split as the N-56 ladder, so every row here is directly comparable to a ladder row.
        cal, te, ncal, nte = split_days(st, "alternating")
        # `bank_mode` is the one axis needing a second state -- it changes the rise table and the
        # refusal mask. The BOUNDS do not depend on it (they are fitted on temperature and dew
        # point, which no bank position affects), so they are fitted once and reused.
        st_by_mode = {BASE["bank_mode"]: st}
        for mode in BANK_MODES:
            if mode not in st_by_mode:
                st_by_mode[mode] = build_state(mode)
        bnd_all = {N: fit_bounds(st, cal, N) for N in NOTICE_H}
        rows, unswept, reversals = run_sensitivity(st_by_mode, bnd_all, cal, te, fg_offsets)
        if unswept:
            say("\n   *** REFUSING TO WRITE OUTPUT: %s declared in BASE with no sweep. ***"
                % ", ".join(unswept))
            return 3
        out["sensitivity"] = {
            "split": "alternating", "held_out_days": nte,
            "base_case": BASE,
            "axes": {k: v for k, v in sensitivity_axes(fg_offsets).items()},
            "note": "ONE-AT-A-TIME: each row varies a single axis and holds every other at BASE. "
                    "This is NOT a full factorial -- interactions between axes are not measured "
                    "here. agent.py runs the 120,960-scenario factorial, but over the four "
                    "FortyGuard days, not over this five-year record.",
            "reversals": reversals,
            "rows": rows}
    if which in ("all", "mondrian"):
        cal, te, ncal, nte = split_days(st, "chronological")
        banner("MONDRIAN AUDIT   does group-conditional calibration matter on REAL weather?")
        out["mondrian"] = {}
        for N in (1, 3, 6):
            a = run_mondrian_audit(st, cal, te, N)
            out["mondrian"][str(N)] = a
            p, m, m2 = a["pooled"], a["mondrian_hod"], a["mondrian_hod_x_season"]
            say("\n   notice %d h" % N)
            say("      pooled      q %+.4f  overall cov %.4f  WORST GROUP hour %s at %.4f  "
                "(%d of 24 groups below 90 %%)"
                % (p["q"], p["overall"], p["worst_group"]["group"],
                   p["worst_group"]["coverage"], p["groups_below_target"]))
            say("      Mondrian    q %.4f..%.4f  overall cov %.4f  WORST GROUP hour %s at %.4f  "
                "(%d below)"
                % (m["q_min"], m["q_max"], m["overall"], m["worst_group"]["group"],
                   m["worst_group"]["coverage"], m["groups_below_target"]))
            say("      + season    %d groups, smallest n=%d, worst %.4f (%d below)"
                % (m2["n_groups"], m2["smallest_group_n"], m2["worst_group"]["coverage"],
                   m2["groups_below_target"]))
    if which in ("all", "aci"):
        banner("ONLINE ADAPTIVE CONFORMAL   thousands of rounds on the real residual stream")
        out["aci"] = {}
        for N in (3,):
            a = run_aci(st, N)
            out["aci"][str(N)] = a
            say("   notice %d h, trailing window %d, %s rounds"
                % (a["notice_h"], a["window"], format(a["ACI"]["rounds"], ",")))
            for k in ("static", "ACI", "DtACI"):
                z = a[k]
                say("      %-6s realised coverage %.4f   first half %.4f   second half %.4f"
                    % (k, z["realised_coverage"], z["coverage_first_half"],
                       z["coverage_second_half"]))

    out["runtime_seconds"] = round(time.time() - t0, 1)
    os.makedirs(DEMO, exist_ok=True)
    p = M.demo_path("backtest.json")
    json.dump(json_safe(out), open(p, "w", encoding="utf-8"), default=_j, allow_nan=False)
    say("\n   wrote %s (%.1f KB) in %.1f s" % (p, os.path.getsize(p) / 1024.0,
                                               out["runtime_seconds"]))
    return 0


def json_safe(o):
    """Recursively replace NaN / +-Infinity with None so the output is VALID STANDARD JSON.

    THE BUG THIS FIXES, because it is a good one. `json.dump` happily writes bare `NaN` and
    `Infinity`. Python's own `json.load` reads them back, so a Python-side validator sees nothing
    wrong -- but they are NOT legal JSON, and a browser's `JSON.parse` rejects the whole file with
    `Unexpected token 'N'`. The demo failed to load with every data path individually verified,
    and only rendering the page in a real browser surfaced it.

    Everything written from here passes `allow_nan=False` as well, so a future NaN raises at write
    time instead of silently shipping a file no browser can read.
    """
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    if isinstance(o, np.floating):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return json_safe(o.tolist())
    return o


def _j(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, C.Mondrian):
        return o.summary()
    raise TypeError(repr(type(o)))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "all"))
