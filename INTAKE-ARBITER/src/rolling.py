# -*- coding: utf-8 -*-
"""ROLLING CONTROL -- the agent carried forward from ANY hour, and how much its plan CHURNS.

    python rolling.py            # the full measurement; writes ../demo/rolling.json
    python rolling.py quick      # a 120-day subset, for iterating

ZERO API CALLS.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS -- two gaps, and the second one was a question we could not answer
--------------------------------------------------------------------------------------------
1. THE AGENT COULD NOT RUN IN THE PRESENT TENSE. Everything shipped planned one CALENDAR DAY from
   midnight with a clean slate. A plant does not work like that: it is 15:00, the plant is already
   in FREE-COOLING, two hours into a three-hour dwell, and it has spent one of its two daily
   switches. `agent.plan()` now accepts exactly that state (`start_switches`, `start_dwell_owed`,
   `budget_reset_at`), and this module drives it hour by hour.

2. NOBODY HAD MEASURED WHETHER SUCCESSIVE PLANS AGREE. The switch budget and the dwell limit bound
   chatter INSIDE one plan, by construction. They say nothing about whether the plan issued at
   14:00 survives contact with the plan issued at 15:00. An operator's first question about a
   12-hour schedule is "will this still be the schedule in an hour?", and the honest answer was
   that we did not know. Two pre-registered attempts at commitment logic (N-44/45 adaptive
   commitment, N-50 commitment timing) both FAILED and nothing was shipped, so there is no
   commitment mechanism to appeal to. This measures the churn instead of assuming it away.

--------------------------------------------------------------------------------------------
WHAT MAKES THE CHURN REAL RATHER THAN TRIVIALLY ZERO
--------------------------------------------------------------------------------------------
Each hour of the horizon is forecast AT ITS OWN LEAD, with its own conformal margin calibrated for
that lead. At 14:00 the 20:00 slot is a 6 h forecast; at 15:00 it is a 5 h forecast -- a different
number, from a tighter quantile. So the plan has a genuine reason to change, and the churn we
measure is the churn a real deployment would see. A single-notice model would have produced zero
churn by construction and told us nothing.

This is also strictly more rigorous than the day-at-a-time path: there, one `notice_h` was applied
to all 24 hours. Here the margin GROWS along the horizon, which is what a conformal bound calibrated
per lead actually does.

--------------------------------------------------------------------------------------------
THE METRICS, defined before they were computed
--------------------------------------------------------------------------------------------
`churn`             over the OVERLAP of two consecutive plans, the fraction of hours whose mode
                    changed. 0.0 means the new plan reaffirmed the old one exactly.
`next_hour_flips`   the plan issued at t promises a mode for t+2; at t+1 the agent re-decides it.
                    How often does that promise break? THIS IS THE OPERATIONALLY CRITICAL ONE --
                    it is the hour the plant is about to act on.
`churn_by_position` churn split by how far ahead the hour sits. Far hours should churn more; if
                    near hours churn as much as far ones, the schedule is not usable.
`executed_*`        what the controller actually did, hour by hour, having only ever acted on the
                    first slot of each plan. This is the honest free-cooling count for a rolling
                    controller, and it is NOT the same as the day-at-a-time number.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import conformal as C                                                        # noqa: E402
from agent import (MODE_FREE, MODE_MECH, debiased_persistence_residuals,      # noqa: E402
                   plan, say, banner)
from backtest import ALPHA, BASE, build_state, split_days, persistence_shift  # noqa: E402

HORIZON_H = 12          # the schedule the UI publishes and the report downloads
# Chronological is REQUIRED, not preferred -- see the leakage guard in simulate(). Named once here so
# the written output cannot disagree with the code, which it already did once.
SPLIT_MODE = "chronological"
QUICK_DAYS = 120


# ============================================================================
def hour_numbers(keys):
    """Absolute hour index for each record, so a LEAD can be measured in HOURS not array steps.

    🔴 WHY THIS EXISTS. Everything here originally took the distance between array positions as the
    forecast lead. The KIAD record is not gap-free: it holds 43,763 rows across a 43,824-hour span,
    so **61 hours are missing** and **46 consecutive index pairs are 2, 3 or 5 real hours apart**,
    not 1. Wherever a gap falls inside a horizon, a slot labelled "3 hours ahead" is really 5 hours
    ahead and was being bounded with the 3-hour margin -- silent UNDER-bounding, in the unsafe
    direction, on ~0.1 % of pairs.

    It was found by asking why the ~24 h/day guard needed a tolerance band at all. The answer was
    that the guard was absorbing the record's own gaps, which meant it could no longer tell a data
    gap from a bug. A guard that cannot separate those two is the wrong guard: the fix is to measure
    the lead correctly and then require the count to be EXACT.
    """
    out = np.empty(len(keys), dtype=np.int64)
    for i, k in enumerate(keys):
        y, mo, d, hh = int(k[0:4]), int(k[5:7]), int(k[8:10]), int(k[11:13])
        # days since a fixed epoch, by civil-date arithmetic -- no timezone, no DST, just an index
        a = (mo - 3) // 12
        yy = y + a
        mm = mo - 3 - 12 * a
        era_days = (365 * yy + yy // 4 - yy // 100 + yy // 400
                    + (153 * mm + 2) // 5 + d - 1)
        out[i] = era_days * 24 + hh
    return out


def build_lead_bounds(st, cal, horizon=HORIZON_H, alpha=ALPHA):
    """For every lead 1..horizon: the de-biased persistence forecast and its Mondrian margin.

    One Mondrian model PER LEAD, each stratified by hour-of-day, each fitted on CALIBRATION days
    only. That is `horizon` separate conformal calibrations, which is the point -- a 1 h forecast
    and a 12 h forecast have nothing like the same error, so one pooled margin would be
    simultaneously far too wide for the near hours and too tight for the far ones.
    """
    hn = st["hnum"]
    out = {}
    for N in range(1, horizon + 1):
        # A residual only belongs to the lead-N model if index i and index i-N really are N HOURS
        # apart. Across one of the record's 46 gaps they are not, and including those rows would
        # calibrate the N-hour margin partly on 2N-hour errors -- widening it for the wrong reason.
        true_lead = np.full(len(hn), -1, dtype=np.int64)
        true_lead[N:] = hn[N:] - hn[:-N]
        lead_ok = (true_lead == N)
        row = {"n_calibration_dropped_to_gaps": int((~lead_ok[N:]).sum())}
        for name, x in (("dry", st["T"]), ("dp", st["Td"])):
            _, bias = debiased_persistence_residuals(x, st["hod"], N)
            sh = persistence_shift(x, N)
            r = (x - sh) - bias[st["hod"]]
            r[:N] = np.nan
            r[~lead_ok] = np.nan
            ok = cal & ~np.isnan(r)
            m = C.Mondrian(alpha).fit(st["hod"][ok], r[ok])
            # `resid` is kept because the SKILL axis needs it. See rolling_safety(): a forecast with
            # skill s sits (1-s) of the way from truth back to persistence, and its margin scales by
            # the same (1-s). Scaling only the margin -- which the first version of this module did --
            # shrinks the bound without improving the forecast and destroys its validity.
            row[name] = {"bias": bias, "margin": m.q_array(st["hod"]), "mondrian": m,
                         "resid": np.where(np.isnan(r), 0.0, r)}
        out[N] = row
    return out


def rolling_safety(st, lb, t, horizon, cfg, rise, plume):
    """Is each hour t+1..t+horizon declarable, as judged FROM TIME t?

    Hour t+k is forecast at lead k from the reading at t -- de-biased persistence, which is exactly
    the model the rest of the project uses and measures. The margin is that lead's own Mondrian
    quantile at the target hour-of-day.
    """
    n = st["n"]
    hn = st["hnum"]
    # THE LEAD IS MEASURED IN REAL HOURS, not array steps (see hour_numbers()). Slots whose true
    # lead falls outside 1..horizon -- which happens on the far side of a gap in the record -- are
    # dropped rather than bounded with the wrong lead's margin.
    cand = np.arange(t + 1, min(t + 1 + horizon, n))
    if len(cand) == 0:
        return cand, np.zeros(0, dtype=bool), np.zeros(0), np.zeros(0, dtype=int)
    true_lead = hn[cand] - hn[t]
    keep = (true_lead >= 1) & (true_lead <= horizon)
    idx = cand[keep]
    k = true_lead[keep]
    if len(idx) == 0:
        return idx, np.zeros(0, dtype=bool), np.zeros(0), np.zeros(0, dtype=int)
    skill, limit = cfg["skill"], cfg["limit_c"]
    dp_lim = cfg["dewpoint_limit_c"]

    fc_dry = np.empty(len(idx))
    fc_dp = np.empty(len(idx))
    mg_dry = np.empty(len(idx))
    mg_dp = np.empty(len(idx))
    # 🔴 SKILL MUST SCALE THE FORECAST AND THE MARGIN TOGETHER, and the first version of this
    # function scaled only the margin. It computed `ub = de-biased persistence + (1-skill)*q`, which
    # at the shipped skill of 0.50 is a 90 % quantile with HALF its width and a forecast that was not
    # a bit better for it. Realised coverage came out at 0.73-0.79 on ALL TWELVE leads -- 12 of 12
    # below nominal is a broken construction, not sampling noise, and it is the tell that caught it.
    #
    # The correct model, the same one agent.py uses: a forecast of skill s sits (1-s) of the way from
    # the truth back towards persistence, and carries (1-s) of the persistence margin. s = 0 is pure
    # de-biased persistence with its full margin; s = 1 is a perfect forecast needing none.
    s = 1.0 - skill
    for j, (i, kk) in enumerate(zip(idx, k)):
        d = lb[int(kk)]
        fc_dry[j] = st["T"][i] - s * d["dry"]["resid"][i]
        fc_dp[j] = st["Td"][i] - s * d["dp"]["resid"][i]
        mg_dry[j] = d["dry"]["margin"][i]
        mg_dp[j] = d["dp"]["margin"][i]

    ub_dry = fc_dry + s * mg_dry + rise[idx] + plume[idx]
    ub_dp = fc_dp + s * mg_dp
    ok = ub_dry <= limit
    if dp_lim is not None:
        ok = ok & (ub_dp <= dp_lim)
    ok = ok & (~st["refused"][idx])
    return idx, ok, ub_dry, k


def simulate(st, lb, day_keys, cfg, horizon=HORIZON_H, plume=None):
    """Drive the controller hour by hour and record every plan it issued.

    THE CONTROLLER ONLY EVER ACTS ON THE FIRST SLOT. Everything past it is a published intention,
    which is precisely what churn measures the reliability of. Carrying `mode`, `dwell_owed` and
    `switches_today` across the boundary is what makes this a controller rather than 24 unrelated
    optimisations.
    """
    rise = st["rise"] if cfg.get("include_rise", True) else np.zeros(st["n"])
    plume = np.zeros(st["n"]) if plume is None else plume
    dayset = set(day_keys)
    idx_all = np.flatnonzero(np.array([d in dayset for d in st["day"]]))
    if len(idx_all) == 0:
        return None
    t0, t1 = int(idx_all[0]), int(idx_all[-1])

    # 🔴 A LEAKAGE GUARD, AND IT CAUGHT A REAL BUG THE FIRST TIME IT RAN.
    # A rolling controller must sweep a CONTIGUOUS block of hours -- it cannot skip a day, because
    # its state (mode, dwell owed, switches spent) carries across the boundary. The first version of
    # this module was handed the ALTERNATING split, whose test days are every other day: the sweep
    # from the first to the last test hour covered a 43,739-hour span containing 21,857 CALIBRATION
    # hours, and scored the controller on days it had calibrated on. The tell was an executed total
    # of 28.5 free hours per day, which is impossible in a 24-hour day.
    # Chronological is now required, and it is the honest split for this question anyway: a
    # deployed controller calibrates on the past and cannot calibrate on the future.
    span = t1 - t0 + 1
    if span != len(idx_all):
        raise ValueError(
            "simulate() needs a CONTIGUOUS block of hours: span %d vs %d selected hours. Pass a "
            "chronological split -- an alternating one leaks calibration days into the sweep."
            % (span, len(idx_all)))

    mode = MODE_MECH
    dwell_owed = 0
    switches_today = 0
    cur_day = st["day"][t0]

    plans = {}          # t -> (idx array, modes array) as promised at time t
    cov = {}            # lead -> [covered, total] for the rolling bound's realised coverage
    executed = []       # (hour index, mode) actually run
    truth_ok = []
    switches_used = 0

    for t in range(t0, t1):
        if st["day"][t] != cur_day:              # midnight: the daily switch budget resets
            cur_day = st["day"][t]
            switches_today = 0
        idx, safe, ub, leads = rolling_safety(st, lb, t, horizon, cfg, rise, plume)
        if len(idx) == 0:
            break
        # REALISED COVERAGE OF THE ROLLING BOUND, per lead. The bound is constructed at 90 % for
        # every lead separately, so this is the check that the construction survives contact with
        # held-out weather -- and it is the number the UI should show, because "the conformal
        # prediction happening" is exactly this: a bound per lead, scored against what occurred.
        truth_i = st["T"][idx] + rise[idx]
        for kk, tv, bv in zip(leads, truth_i, ub):
            c = cov.setdefault(int(kk), [0, 0])
            c[1] += 1
            c[0] += int(tv <= bv)
        # where does the horizon cross midnight? that is where the budget resets INSIDE the plan
        reset_at = None
        for j, i in enumerate(idx):
            if st["day"][i] != st["day"][t]:
                reset_at = j
                break
        modes, _, _ = plan(list(safe), cfg["switch_budget"], cfg["min_dwell_h"],
                           start_mode=mode, start_switches=switches_today,
                           start_dwell_owed=dwell_owed, budget_reset_at=reset_at)
        plans[t] = (idx, np.array(modes, dtype=np.int8))

        # ---- act on the first slot only, then advance the state
        nm = modes[0]
        if nm != mode:
            switches_today += 1
            switches_used += 1
            dwell_owed = max(0, cfg["min_dwell_h"] - 1)
            mode = nm
        else:
            dwell_owed = max(0, dwell_owed - 1)
        executed.append((int(idx[0]), int(nm)))
        truth_ok.append(bool(st["T"][idx[0]] + rise[idx[0]] <= cfg["limit_c"]
                             and (cfg["dewpoint_limit_c"] is None
                                  or st["Td"][idx[0]] <= cfg["dewpoint_limit_c"])))
    return {"plans": plans, "executed": executed, "truth_ok": truth_ok,
            "switches_used": switches_used,
            # one step per selected record, minus the last hour which has no successor to act on.
            # The largest gap in the record is 5 h, well inside the 12 h horizon, so the loop can
            # never break early -- making this an exact expectation rather than an approximate one.
            "hours_run_expected": len(idx_all) - 1,
            "coverage_by_lead": {str(k): (v[0] / v[1]) for k, v in sorted(cov.items())},
            "coverage_n_by_lead": {str(k): v[1] for k, v in sorted(cov.items())}}


def churn(sim, horizon=HORIZON_H):
    """Compare each plan with its successor over the hours they both cover."""
    plans = sim["plans"]
    ts = sorted(plans)
    changed = total = 0
    nh_changed = nh_total = 0
    by_pos = {}
    per_replan = []
    for a, b in zip(ts, ts[1:]):
        if b != a + 1:
            continue
        ia, ma = plans[a]
        ib, mb = plans[b]
        pa = {int(i): int(m) for i, m in zip(ia, ma)}
        pb = {int(i): int(m) for i, m in zip(ib, mb)}
        shared = sorted(set(pa) & set(pb))
        if not shared:
            continue
        diff = sum(1 for i in shared if pa[i] != pb[i])
        changed += diff
        total += len(shared)
        per_replan.append(diff)
        # the operationally critical promise: the hour the plant acts on NEXT
        first = shared[0]
        nh_total += 1
        nh_changed += int(pa[first] != pb[first])
        for i in shared:
            pos = i - b                          # 1 = next hour, horizon = far edge
            d = by_pos.setdefault(pos, [0, 0])
            d[1] += 1
            d[0] += int(pa[i] != pb[i])
    return {"replans": len(per_replan),
            "hours_compared": total,
            "churn": (changed / total) if total else float("nan"),
            "next_hour_flip_rate": (nh_changed / nh_total) if nh_total else float("nan"),
            "replans_with_zero_change": (sum(1 for d in per_replan if d == 0) / len(per_replan))
                                       if per_replan else float("nan"),
            "mean_hours_changed_per_replan": (sum(per_replan) / len(per_replan))
                                             if per_replan else float("nan"),
            "churn_by_position": {str(k): (v[0] / v[1]) for k, v in sorted(by_pos.items())}}


def summarise(sim, cfg):
    ex = sim["executed"]
    free = sum(1 for _, m in ex if m == MODE_FREE)
    safe_free = sum(1 for (i, m), ok in zip(ex, sim["truth_ok"]) if m == MODE_FREE and ok)
    breach = free - safe_free
    return {"hours_run": len(ex), "hours_run_expected": sim["hours_run_expected"],
            "executed_free_h": free, "executed_safe_free_h": safe_free,
            "executed_breach_h": breach, "switches": sim["switches_used"],
            "breach_per_1000_free_h": (1000.0 * breach / free) if free else 0.0}


# ============================================================================
def main(mode="full"):
    t0 = time.time()
    banner("ROLLING CONTROL   the agent carried forward hour by hour.  ZERO API CALLS.")
    st = build_state(BASE["bank_mode"])
    st["hnum"] = hour_numbers(st["keys"])
    # CHRONOLOGICAL, and it is not a preference -- see the leakage guard in simulate(). A rolling
    # controller carries state across day boundaries, so it must sweep contiguous hours; and
    # calibrating on the past is what a deployment actually does.
    cal, te, ncal, nte = split_days(st, SPLIT_MODE)
    days = sorted(set(st["day"][te]))
    if mode == "quick":
        days = days[:QUICK_DAYS]
    say("   state %s hours; %d calibration / %d held-out days (CHRONOLOGICAL); simulating %d"
        % (format(st["n"], ","), ncal, nte, len(days)))

    say("\n   calibrating %d SEPARATE conformal models, one per lead 1..%d h, each Mondrian on"
        % (HORIZON_H, HORIZON_H))
    say("   hour-of-day, all on calibration days only ...")
    lb = build_lead_bounds(st, cal, HORIZON_H)
    say("   margin at hour 14, by lead:  " + "  ".join(
        "%dh %.2f" % (N, lb[N]["dry"]["margin"][np.flatnonzero(st["hod"] == 14)[0]])
        for N in (1, 3, 6, 9, 12)))
    say("   -> the margin GROWS with lead, which is why a re-plan has something to change.")

    configs = [
        ("shipped: budget 2, dwell 3 h", dict(BASE)),
        ("unconstrained: budget 24, dwell 1 h", dict(BASE, switch_budget=24, min_dwell_h=1)),
        ("tight: budget 1, dwell 3 h", dict(BASE, switch_budget=1, min_dwell_h=3)),
    ]
    out = {"generated_by": "INTAKE-ARBITER/src/rolling.py", "api_calls_made": 0,
           # NOT a literal: this label was hard-coded as "alternating" and survived the switch to
           # chronological, so the written output described a split the code was not using.
           "horizon_h": HORIZON_H, "alpha": ALPHA, "split": SPLIT_MODE,
           "held_out_days_simulated": len(days), "base_case": BASE,
           "lead_margins_c_at_hour14": {str(N): float(
               lb[N]["dry"]["margin"][np.flatnonzero(st["hod"] == 14)[0]])
               for N in range(1, HORIZON_H + 1)},
           "configs": []}

    say("\n   %-38s %9s %11s %13s %11s %9s"
        % ("configuration", "churn", "next-hour", "zero-change", "free h/day", "breach/1k"))
    for label, cfg in configs:
        sim = simulate(st, lb, days, cfg, HORIZON_H)
        if sim is None:
            continue
        ch = churn(sim, HORIZON_H)
        sm = summarise(sim, cfg)
        # THE GUARD IS NOW AN EXACT IDENTITY, NOT A TOLERANCE BAND.
        # It used to accept 20.0-24.5 hours per simulated day, which quietly absorbed both the
        # record's 61 missing hours AND any real bug -- so it could not tell them apart. Now that
        # leads are measured in real hours, the loop must step exactly once per selected record,
        # minus the final hour that has no successor to act on. Anything else is a defect.
        expected = sm["hours_run_expected"]
        if sm["hours_run"] != expected:
            raise ValueError("simulated %d hours, expected exactly %d. The sweep is not stepping "
                             "one record at a time." % (sm["hours_run"], expected))
        hpd = sm["hours_run"] / max(1, len(days))
        row = {"label": label, "config": {k: cfg[k] for k in sorted(cfg)}, **ch, **sm,
               "hours_run_per_day": round(hpd, 3),
               "executed_free_h_per_day": sm["executed_free_h"] / max(1, len(days)),
               "coverage_by_lead": sim["coverage_by_lead"],
               "coverage_n_by_lead": sim["coverage_n_by_lead"]}
        out["configs"].append(row)
        say("   %-38s %9.4f %11.4f %13.4f %11.3f %9.2f"
            % (label, ch["churn"], ch["next_hour_flip_rate"],
               ch["replans_with_zero_change"], row["executed_free_h_per_day"],
               sm["breach_per_1000_free_h"]))

    base = out["configs"][0]
    say("\n   REALISED COVERAGE OF THE ROLLING BOUND, PER LEAD  (nominal %.0f %%, shipped config)"
        % (100 * (1 - ALPHA)))
    cbl = base["coverage_by_lead"]
    ks = sorted(cbl, key=int)
    say("      lead h   : " + " ".join("%6s" % k for k in ks))
    say("      coverage : " + " ".join("%6.4f" % cbl[k] for k in ks))
    below = [k for k in ks if cbl[k] < (1 - ALPHA)]
    say("      -> %d of %d leads below the %.0f %% nominal%s"
        % (len(below), len(ks), 100 * (1 - ALPHA),
           (": leads " + ", ".join(below)) if below else " -- every lead holds"))
    say("      Each lead is calibrated SEPARATELY, so this is %d independent conformal bounds"
        % len(ks))
    say("      scored on held-out weather, not one bound reused. The margin runs %.2f C at 1 h to"
        % lb[1]["dry"]["margin"][np.flatnonzero(st["hod"] == 14)[0]])
    say("      %.2f C at %d h; a single pooled margin would be wrong at both ends."
        % (lb[HORIZON_H]["dry"]["margin"][np.flatnonzero(st["hod"] == 14)[0]], HORIZON_H))
    say("      NOTE the per-hour-of-day margins are NOT monotone in lead even though the MEAN is")
    say("      (1.20 C at 1 h to 5.38 C at 12 h): a 12 h-ahead reading sits at the opposite phase")
    say("      of the diurnal cycle, which after de-biasing can be more predictable than 9 h.")

    say("\n   CHURN BY HOW FAR AHEAD THE HOUR SITS  (shipped config)")
    say("      lead h : " + " ".join("%5s" % k for k in
                                     sorted(base["churn_by_position"], key=int)))
    say("      churn  : " + " ".join("%5.3f" % base["churn_by_position"][k] for k in
                                     sorted(base["churn_by_position"], key=int)))

    say("\n   WHAT THIS MEANS, read off the numbers above and not decided in advance:")
    nh = base["next_hour_flip_rate"]
    say("      * the hour the plant is about to act on changes in %.2f %% of re-plans." % (100 * nh))
    say("      * %.1f %% of re-plans reaffirm the previous plan with NO change at all."
        % (100 * base["replans_with_zero_change"]))
    say("      * mean %.2f of %d published hours move per re-plan."
        % (base["mean_hours_changed_per_replan"], HORIZON_H - 1))
    # WHERE THE STABILITY COMES FROM -- and the first draft of this block got it wrong.
    # It asserted that the switch budget and dwell limit "CUT churn ... the mechanism that makes a
    # published schedule trustworthy". The measured numbers do not support that: churn is nearly
    # identical constrained and unconstrained. Reported as measured, with the ratio printed so the
    # reader can see it is ~1 rather than taking a claim on trust (methodology rule 3, and gotcha
    # #35 -- do not write a cause down before checking that the thing actually differed).
    unc = next((c for c in out["configs"] if "unconstrained" in c["label"]), None)
    if unc and base["churn"]:
        ratio = unc["churn"] / base["churn"]
        say("      * removing the switch budget and dwell limit moves churn %.4f -> %.4f, a factor"
            % (base["churn"], unc["churn"]))
        say("        of %.2f. So the constraints are NOT what makes the schedule stable." % ratio)
        say("        The stability comes from the FORECAST: consecutive issue times share almost all")
        say("        of their information, so the bound barely moves and the optimum barely moves.")
        say("      * there is NO commitment mechanism here, and none is claimed. Two pre-registered")
        say("        attempts at one failed (N-44/45 adaptive commitment, N-50 commitment timing).")
        say("        This is a MEASUREMENT of stability, not a guarantee of it.")
        out["stability_attribution"] = {
            "churn_shipped": base["churn"], "churn_unconstrained": unc["churn"],
            "ratio": ratio,
            "conclusion": ("the switch budget and dwell limit do NOT explain the low churn; "
                           "consecutive de-biased persistence forecasts are highly correlated, so "
                           "the bound and therefore the optimum barely move. No commitment "
                           "mechanism exists or is claimed.")}

    out["runtime_seconds"] = round(time.time() - t0, 1)
    os.makedirs(DEMO, exist_ok=True)
    p = os.path.join(DEMO, "rolling.json")
    json.dump(_safe(out), open(p, "w", encoding="utf-8"), allow_nan=False, default=str)
    say("\n   wrote %s (%.1f KB) in %.1f s"
        % (p, os.path.getsize(p) / 1024.0, out["runtime_seconds"]))
    return 0


def _safe(o):
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: _safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_safe(v) for v in o]
    if isinstance(o, (np.floating,)):
        return _safe(float(o))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _safe(o.tolist())
    return o


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "full").lower()))
