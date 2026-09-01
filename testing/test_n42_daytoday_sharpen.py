# -*- coding: utf-8 -*-
"""N-42  ---  the CORRECTED sharpening test: day-to-day, site-level, not spatial.   PAID (extra
leads) / FREE (status, validate, report on whatever exists).

WHY THIS FILE EXISTS AND HOW IT DIFFERS FROM N-25
    staging.py's make_forecast_paths() draws an INDEPENDENT random error per (simulated day,
    lead):
        return truths[:, None] + rng.standard_normal((len(truths), K + 1)) * sig[None, :]
    So sigma(lead), as the DP actually consumes it, means: across many different DAYS, how much
    does the SITE-LEVEL forecast error vary at a fixed lead. It is a day-to-day statistic.

    N-24's sd_c = 0.15036 and N-25's fitted b both came from the SPATIAL spread of the residual
    across ~17,862 tiles on a SINGLE day. That is a different quantity -- how much the error
    varies across SPACE, not across TIME. N-25's b = -0.061 (CI [-0.316,+0.195], FAIL vs the
    0.129 break-even) is a correct answer to "does the field's spatial pattern get more accurate
    at short lead" (no) but does not settle whether the DP's actual sigma(lead) sharpens.
    N-25 remains correct for what it measures and is not modified.

    This file fits b on the DAY-TO-DAY sd of the SITE-LEVEL error -- the mean forecast-minus-
    outcome over the 49 nearest tiles to the AOI centre, matching solver.intake_temperature's
    default averaging footprint (radius_m=30 over 60 m tiles -> a 7x7 block).

THE HONEST PROBLEM WITH THIS TEST, FOUND BEFORE COLLECTING A SINGLE EXTRA DAY
    N-25's five leads, read at the site level rather than the spatial level, show:
        lead 9.41h +0.906C   7.49h +1.135C   5.49h +0.900C   3.49h +1.249C   1.49h +1.087C
    That is a large, PERSISTENT day-level offset (mean +1.06C) with a much smaller lead-specific
    wobble (+/-0.17C) riding on top of it. If a large share of the site-level error is common to
    every lead on a given day -- a systematic bias that does not resolve just because the decision
    hour gets closer -- then even a forecast that genuinely sharpens on its LEAD-SPECIFIC component
    will show an ATTENUATED, and possibly undetectable, b when measured this way. Modelled as
        error(day, lead) = D_day + e(day, lead),   e ~ N(0, sigma_e12 * (lead/12)**b_true)
    a Monte-Carlo check (3 leads: 1.5/5.5/9.5h) gives, for the MEASURED b as a function of the
    true b and the ratio D/e (sigma_D expressed as a multiple of sigma_e at the 12h anchor):

        b_true \\ D/e     0.0     0.5     1.0     2.0     3.0
             0.25        0.250   0.175   0.094   0.033   0.016
             0.50        0.500   0.289   0.138   0.046   0.022
             0.75        0.750   0.348   0.156   0.051   0.024
             1.00        1.000   0.372   0.163   0.053   0.025

    At D/e = 1.0 -- plausible given the +/-0.17C wobble against a much larger persistent offset
    seen in the one day measured -- a TRUE b of 0.50 measures as 0.138, barely above the 0.129
    break-even and clearly short of the 0.187 two-sigma bar. At D/e = 2.0 it measures 0.046 and
    the DP is RIGHT to earn nothing, because the unresolvable part of the error never resolves no
    matter how many days you collect.

    AND EVEN IF the true b is favourable, the STATISTICAL POWER to detect it is poor on the
    calendar available. A Monte-Carlo of the OLS estimator itself (3 leads, no day-level offset,
    the MOST favourable case) gives SE(b_hat):
        n_days   5     10     20     40     80    160
        SE     0.296  0.188  0.123  0.086  0.060  0.042
    Distinguishing b=0 from the 0.187 threshold needs roughly SE <= 0.047 -- i.e. ~80 days, in the
    BEST case with zero day-level offset. With a realistic D/e ~ 1.0, n_days=40 gives SE=0.057 on
    a b_hat already attenuated to ~0.12 -- underpowered on both the effect size and the estimate.

    CONCLUSION, STATED BEFORE COLLECTING ONE EXTRA DAY: this test, run for the few days the
    schedule allows, is very unlikely to produce a decisive PASS or FAIL. It should still be run,
    for two reasons that do not depend on reaching significance by any particular date: (1) it is
    the CORRECT statistic, and reporting the wrong one again would repeat N-25's original mistake
    in the other direction; (2) the fitting and refitting machinery below is exactly the online
    recalibration behaviour the agent needs regardless of the final verdict -- see refit_history().

PRE-REGISTERED, same thresholds as N-24/N-25 for direct comparability
    b >= 0.187      2-sigma win over the tuned fixed-hour adversary
    0.129-0.187     marginal; re-run N-9/N-24 at the measured b
    b <  0.129      waiting buys nothing at this sharpening rate
    ADDED HERE, because of the power analysis above: the verdict is reported as UNDERPOWERED
    whenever the 95% CI half-width exceeds 0.10 (i.e. cannot even reliably distinguish 0 from the
    0.187 threshold), regardless of where the point estimate falls. A verdict is claimed PASS or
    FAIL only when the CI is tight enough for that claim to mean something.

INSTRUMENT VALIDATION -- checked before trusting real data, same discipline as N-25
    validate() builds synthetic day-to-day data at KNOWN (b_true, D/e) and confirms the fit
    recovers it, including the attenuation table above (i.e. that the synthetic recovery MATCHES
    the analytic attenuation prediction, not just that some number comes out).

COST, AND WHY THIS FILE DOES NOT SPEND CREDITS ON ITS OWN
    Reuses N-26's existing ~9.5h leg entirely from its manifest/fixtures -- zero extra cost for
    that lead. Adding the two extra leads (~5.5h, ~1.5h) that this test needs to fit a slope at
    all costs 2 extra heatmap calls/day = ~8,440 credits/day at the documented 4,220/call rate.
    THIS FILE DOES NOT FIRE THOSE CALLS. 'status' and 'report' only read what already exists.
    A human must explicitly enable the extra-lead collection (see collect_extra_leads below) --
    per the standing rule, that requires stating the cost and getting confirmation first.

USAGE
    python test_n42_daytoday_sharpen.py validate   # synthetic recovery check, FREE
    python test_n42_daytoday_sharpen.py status      # what data exists, current power, FREE
    python test_n42_daytoday_sharpen.py report      # fit b on whatever real data exists, FREE
    python test_n42_daytoday_sharpen.py collect     # PAID -- only run after explicit approval
"""
import json, math, os, statistics, sys
from datetime import timedelta

import numpy as np

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, RESULTS, FIXTURES, tile_key, site_now, site_window, lead_hours,
                    utc_now, site_tz, SITE_TZ_NAME)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14                 # matches N-26, so its ~9.5h leg is reused for free
N_INTAKE_CELLS = 49                   # matches solver.intake_temperature's default 7x7 @ 30m/60m
ADDITIONAL_LEADS = [5.5, 1.5]         # what N-42 needs beyond N-26's existing ~9.5h leg
NOMINAL_LEADS = [1.5, 5.5, 9.5]       # the three legs this test pools across days
LEAD_TOLERANCE_H = 2.5                # actual leads drift day to day (task fires when it fires);
                                       # group by nearest nominal leg within this tolerance, never
                                       # by literal rounding -- 9.41h and 9.50h are the SAME leg
N26_MANIFEST = os.path.join(RESULTS, "n26_manifest.json")
MANIFEST = os.path.join(RESULTS, "n42_manifest.json")
CREDITS_PER_CALL = 4220               # documented rate; the key's meter is frozen, so this is the
                                       # only way to state a cost -- see fortyguard-api-findings.md

PASS_B = 0.187
MARGINAL_B = 0.129
UNDERPOWERED_CI_HALFWIDTH = 0.10      # if the CI is wider than this, no verdict is claimed

TCRIT_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
            8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 15: 2.131, 20: 2.086}


def tcrit(dof):
    if dof in TCRIT_95:
        return TCRIT_95[dof]
    return 1.96 if dof > 30 else TCRIT_95[min(TCRIT_95, key=lambda k: abs(k - dof))]


# ----------------------------------------------------------------- the estimator (one place)
def fit_stats(xs, ys):
    """OLS of ln(y) on ln(x), with SE, t, R^2 and a 95% CI. Same estimator as test_n25_sharpen.py
    _fit_stats -- copied rather than reinvented, per the standing rule."""
    n = len(xs)
    if n < 3:
        return None
    lx = [math.log(x) for x in xs]
    ly = [math.log(max(y, 1e-12)) for y in ys]
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    sxx = sum((x - mx) ** 2 for x in lx)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(lx, ly)]
    dof = n - 2
    se = math.sqrt(sum(r * r for r in resid) / dof / sxx)
    sst = sum((y - my) ** 2 for y in ly)
    tc = tcrit(dof)
    r2 = 1.0 - sum(r * r for r in resid) / sst if sst > 0 else None
    return {"n": n, "dof": dof, "b": b, "se": se, "t": b / se if se > 0 else float("inf"),
            "r2": r2, "ci_lo": b - tc * se, "ci_hi": b + tc * se, "tcrit": tc}


# ----------------------------------------------------------------- power / attenuation analysis
def attenuation_table():
    """Reproduces the analytic attenuation of measured b vs true b, at 3 leads (1.5/5.5/9.5h),
    as a function of the day-level-offset-to-lead-error ratio D/e."""
    leads = np.array([1.5, 5.5, 9.5])

    def measured(b_true, ratio):
        s12 = math.sqrt(ratio ** 2 + 1.0)
        lo = math.sqrt(ratio ** 2 + (leads[0] / 12.0) ** (2 * b_true))
        return math.log(s12 / lo) / math.log(12.0 / leads[0])

    ratios = (0.0, 0.5, 1.0, 2.0, 3.0)
    return {"leads": leads.tolist(), "ratios": ratios,
            "table": {str(bt): [measured(bt, r) for r in ratios]
                      for bt in (0.25, 0.50, 0.75, 1.00)}}


def power_table(n_trials=3000, seed=41):
    """Monte-Carlo SE(b_hat) vs n_days, at 3 leads, true b=0.50, zero day-offset (best case)."""
    rng = np.random.default_rng(seed)
    leads = np.array([1.5, 5.5, 9.5])
    lx = np.log(leads)
    mx = lx.mean()
    sxx = ((lx - mx) ** 2).sum()
    sig = 0.15 * (leads / 12.0) ** 0.50
    out = {}
    for nd in (5, 10, 20, 40, 80, 160):
        bs = []
        for _ in range(n_trials):
            err = rng.normal(0, 1, (nd, len(leads))) * sig[None, :]
            sd = err.std(axis=0, ddof=1)
            if np.any(sd <= 0):
                continue
            ly = np.log(sd)
            bs.append(float(((lx - mx) * (ly - ly.mean())).sum() / sxx))
        a = np.array(bs)
        out[nd] = {"mean_b": float(a.mean()), "se": float(a.std(ddof=1))}
    return out


# ----------------------------------------------------------------- validate the fitter
def validate():
    banner("N-42 validate  synthetic recovery check, incl. the attenuation model   [FREE]")
    rng = np.random.default_rng(42)
    leads = [1.5, 5.5, 9.5]
    print("   %-24s %10s %10s %10s" % ("case", "b_true", "b_recovered (synthetic, n=40 days)", ""))
    ok = True
    for b_true, D_over_e in ((0.500, 0.0), (0.187, 0.0), (0.000, 0.0), (0.500, 1.0)):
        sig_e12 = 0.15
        sig_e = sig_e12 * (np.array(leads) / 12.0) ** b_true
        sig_D = D_over_e * sig_e12
        n_days = 4000                              # large n isolates recovery from noise
        D = rng.normal(0, sig_D, n_days)[:, None] if sig_D > 0 else np.zeros((n_days, 1))
        e = rng.normal(0, 1, (n_days, len(leads))) * sig_e[None, :]
        err = D + e
        sd = err.std(axis=0, ddof=1)
        f = fit_stats(leads, sd.tolist())
        att = attenuation_table()
        expected = None
        if D_over_e in (0.0, 1.0) and str(b_true) in att["table"]:
            idx = att["ratios"].index(D_over_e)
            expected = att["table"][str(b_true)][idx]
        match = expected is None or abs(f["b"] - expected) < 0.02
        ok = ok and match
        print("   b_true=%.3f D/e=%.1f  -> recovered %.4f  (attenuation model predicts %s)  %s"
              % (b_true, D_over_e, f["b"],
                 "%.4f" % expected if expected is not None else "n/a",
                 "OK" if match else "MISMATCH"))
    print()
    print("   VERDICT: %s" % ("fitter and attenuation model agree -- both trusted below"
                              if ok else "MISMATCH -- do not trust report() until fixed"))
    return 0 if ok else 1


# ----------------------------------------------------------------- data access
def field_max(result):
    feats = (result.get("map_data") or {}).get("features") or []
    out = {}
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[tile_key(la, lo)] = (v, la, lo)
    return out


def load_fixture(tag):
    p = os.path.join(FIXTURES, "%s.json" % tag)
    if not os.path.exists(p):
        return None
    return field_max(json.load(open(p, encoding="utf-8")))


def nominal_lead(lead_h):
    """Nearest of NOMINAL_LEADS within LEAD_TOLERANCE_H, or None if it matches none -- e.g. a
    9.41h and a 9.50h actual lead both belong to the SAME ~9.5h leg; literal rounding would
    split them into two single-day buckets and silently make every leg look unpoolable."""
    best = min(NOMINAL_LEADS, key=lambda n: abs(n - lead_h))
    return best if abs(best - lead_h) <= LEAD_TOLERANCE_H else None


def site_level_error(F, H, centre=CENTRE, n_cells=N_INTAKE_CELLS):
    """Mean(forecast - outcome) over the n_cells tiles nearest the AOI centre -- matches
    solver.intake_temperature's default averaging footprint, NOT the spatial sd across all tiles."""
    keys = [k for k in F if k in H]
    if len(keys) < n_cells:
        return None, 0
    near = sorted(keys, key=lambda k: (k[0] - centre[0]) ** 2 + (k[1] - centre[1]) ** 2)[:n_cells]
    d = [F[k][0] - H[k][0] for k in near]
    return statistics.fmean(d), len(near)


# ----------------------------------------------------------------- gather what exists (FREE)
def gather_days():
    """One row per (day, lead) where both a forecast and an outcome fixture exist. Reuses N-26's
    ~9.5h leg via its manifest; N-42's own manifest (if collect() has ever run) supplies the
    additional leads."""
    rows = []
    if os.path.exists(N26_MANIFEST):
        m26 = json.load(open(N26_MANIFEST, encoding="utf-8"))
        for dk, d in m26["days"].items():
            ft, ot = d.get("forecast_tag"), d.get("outcome_tag")
            if not (ft and ot):
                continue
            F, H = load_fixture(ft), load_fixture(ot)
            if F is None or H is None:
                continue
            err, n = site_level_error(F, H)
            if err is not None:
                rows.append({"day": dk, "lead_h": d.get("forecast_lead_h"),
                            "site_error_c": err, "n_cells": n, "source": "N-26"})
    if os.path.exists(MANIFEST):
        m42 = json.load(open(MANIFEST, encoding="utf-8"))
        for dk, day in m42.get("days", {}).items():
            for leadkey, leg in day.get("legs", {}).items():
                ft, ot = leg.get("forecast_tag"), leg.get("outcome_tag")
                if not (ft and ot):
                    continue
                F, H = load_fixture(ft), load_fixture(ot)
                if F is None or H is None:
                    continue
                err, n = site_level_error(F, H)
                if err is not None:
                    rows.append({"day": dk, "lead_h": leg.get("lead_h"),
                                "site_error_c": err, "n_cells": n, "source": "N-42"})
    return rows


# ----------------------------------------------------------------- status (FREE)
def status():
    banner("N-42 status  what data exists, current power, cost of what is missing   [FREE]")
    rows = gather_days()
    by_lead = {}
    for r in rows:
        nl = nominal_lead(r["lead_h"])
        if nl is not None:
            by_lead.setdefault(nl, []).append(r)
    print("   %d (day, lead) rows available, from %d distinct days"
          % (len(rows), len({r["day"] for r in rows})))
    for lead in sorted(by_lead):
        rs = by_lead[lead]
        vals = [r["site_error_c"] for r in rs]
        print("      lead ~%.1fh: n_days=%d  errors %s  %s"
              % (lead, len(rs), ", ".join("%+.3f" % v for v in vals),
                 "sd=%.4f" % statistics.stdev(vals) if len(rs) > 1 else "(need >=2 to get an sd)"))
    n_distinct_leads = len(by_lead)
    print("\n   distinct leads with data: %d  (need >= 3 to fit a slope at all)" % n_distinct_leads)

    print("\n   POWER, given current design (3 leads: 1.5/5.5/9.5h)")
    pt = power_table()
    print("   %8s %12s %12s   %s" % ("n_days", "mean b_hat", "SE(b_hat)", "note"))
    for nd, v in pt.items():
        note = "sufficient to separate 0 from 0.187" if v["se"] <= 0.047 else "underpowered"
        print("   %8d %12.4f %12.4f   %s" % (nd, v["mean_b"], v["se"], note))
    print("   (best case: zero day-level offset. With the D/e~1.0 measured, the TRUE b")
    print("    itself is already attenuated to roughly 25% of its unresolvable-free value -- see")
    print("    the attenuation table in this file's docstring.)")

    print("\n   WHAT COLLECTING THE EXTRA LEADS WOULD COST")
    print("      2 extra calls/day (leads ~%s) x %s credits = %s credits/day"
          % (ADDITIONAL_LEADS, format(CREDITS_PER_CALL, ","),
             format(2 * CREDITS_PER_CALL, ",")))
    print("      This file's 'collect' mode does NOT fire these on its own -- ask first.")
    save_result("n42_status.json", {"rows": rows, "n_distinct_leads": n_distinct_leads,
                                    "power_table": pt, "attenuation_table": attenuation_table()})
    return 0


# ----------------------------------------------------------------- report (FREE, fits whatever exists)
def report():
    banner("N-42 report  fit b on the DAY-TO-DAY SITE-LEVEL statistic, whatever exists   [FREE]")
    rows = gather_days()
    by_lead = {}
    for r in rows:
        nl = nominal_lead(r["lead_h"])
        if nl is not None:
            by_lead.setdefault(nl, []).append(r["site_error_c"])
    usable = {l: v for l, v in by_lead.items() if len(v) >= 2}
    print("   leads with >=2 days (need this just to get a day-to-day sd at all): %d"
          % len(usable))
    for l in sorted(usable):
        print("      lead %.2fh: n=%d  sd=%.4f  values %s"
              % (l, len(usable[l]), statistics.stdev(usable[l]),
                 ", ".join("%+.3f" % v for v in usable[l])))

    if len(usable) < 3:
        print("\n   Fewer than 3 leads have >=2 days each. A slope literally cannot be fitted.")
        print("   This is not a null result -- it is 'not enough calendar days yet'. The extra")
        print("   leads must be collected (see 'status' for the cost) before this test can speak.")
        save_result("n42_daytoday_sharpen.json", {"rows": rows, "pass": None,
                                                   "reason": "fewer than 3 usable leads"})
        return 2

    leads = sorted(usable)
    sds = [statistics.stdev(usable[l]) for l in leads]
    f = fit_stats(leads, sds)
    print("\n   FIT  day-to-day sd(lead) = A * lead ** b")
    print("      n=%d  dof=%d  b=%+.4f  SE=%.4f  t=%+.2f  R^2=%s  95%% CI [%+.3f, %+.3f]"
          % (f["n"], f["dof"], f["b"], f["se"], f["t"],
             "%.3f" % f["r2"] if f["r2"] is not None else "n/a", f["ci_lo"], f["ci_hi"]))

    ci_width = f["ci_hi"] - f["ci_lo"]
    underpowered = ci_width > 2 * UNDERPOWERED_CI_HALFWIDTH
    print("\n   POWER CHECK: CI half-width = %.4f (threshold for a claimable verdict: %.2f)"
          % (ci_width / 2, UNDERPOWERED_CI_HALFWIDTH))
    if underpowered:
        band = "UNDERPOWERED"
    elif f["ci_lo"] >= PASS_B:
        band = "PASS"
    elif f["ci_hi"] < MARGINAL_B:
        band = "FAIL"
    else:
        band = "MARGINAL"
    print("   -> %s" % band)

    print("\n   WHAT THE INTERVAL EXCLUDES")
    for nm, v in (("0.000 no sharpening", 0.0), ("0.129 break-even", MARGINAL_B),
                 ("0.187 two-sigma", PASS_B), ("0.500 assumed by N-24", 0.500)):
        ex = v < f["ci_lo"] or v > f["ci_hi"]
        print("      %-24s %s" % (nm, "EXCLUDED" if ex else "inside the interval"))

    ok = band == "PASS"
    print()
    verdict(ok if band != "UNDERPOWERED" else None,
            "PASS - day-to-day sharpening is established at b=%+.4f, CI [%+.3f,%+.3f], clearing "
            "the 0.187 two-sigma bar on the SITE-LEVEL statistic the DP actually needs."
            % (f["b"], f["ci_lo"], f["ci_hi"]),
            "FAIL/MARGINAL/UNDERPOWERED (%s) - b=%+.4f, CI [%+.3f,%+.3f], on only %d days. This "
            "is the CORRECT statistic but the calendar has not yet supplied enough days to speak "
            "with confidence; do not report this as 'sharpening is dead' unless the CI genuinely "
            "excludes 0.129 on its high side." % (band, f["b"], f["ci_lo"], f["ci_hi"], f["n"]))

    save_result("n42_daytoday_sharpen.json", {
        "rows": rows, "leads_h": leads, "sds": sds, "fit": f,
        "ci_width": ci_width, "underpowered": underpowered, "band": band,
        "pass_b": PASS_B, "marginal_b": MARGINAL_B,
        "note": "fit on DAY-TO-DAY sd of the SITE-LEVEL (49-cell) error, not spatial sd across "
                "tiles -- see docstring for why these are different quantities",
        "pass": ok if band != "UNDERPOWERED" else None})
    return 0 if band == "PASS" else (2 if band == "UNDERPOWERED" else 1)


# ----------------------------------------------------------------- online recalibration (the
# behaviour that survives regardless of the verdict above)
def refit_history():
    """Refit b from whatever day-to-day data currently exists, and state the CURRENT best policy
    stance. Meant to be called once per day as new outcomes land -- an agent that updates its own
    belief about sharpening from its own accumulating experience, rather than trusting a single
    frozen pre-launch measurement. Returns a dict; does not print (callers decide how to surface
    it -- e.g. in the live reasoning ticker)."""
    rows = gather_days()
    by_lead = {}
    for r in rows:
        nl = nominal_lead(r["lead_h"])
        if nl is not None:
            by_lead.setdefault(nl, []).append(r["site_error_c"])
    usable = {l: v for l, v in by_lead.items() if len(v) >= 2}
    if len(usable) < 3:
        return {"n_usable_leads": len(usable), "b": None,
                "stance": "insufficient data -- treating sharpening as unproven, DP defaults to "
                          "the tuned fixed-hour policy until >=3 leads have >=2 days each"}
    leads = sorted(usable)
    sds = [statistics.stdev(usable[l]) for l in leads]
    f = fit_stats(leads, sds)
    if f["ci_hi"] - f["ci_lo"] > 2 * UNDERPOWERED_CI_HALFWIDTH:
        stance = ("underpowered at n=%d days -- current point estimate b=%+.3f is not yet "
                  "reliable; DP continues to use the tuned fixed-hour policy" % (f["n"], f["b"]))
    elif f["ci_lo"] >= PASS_B:
        stance = "sharpening confirmed (b>=%.3f at 95%% conf.) -- DP stopping rule active" % PASS_B
    elif f["ci_hi"] < MARGINAL_B:
        stance = "sharpening excluded (b<%.3f at 95%% conf.) -- DP defers to fixed-hour policy" % MARGINAL_B
    else:
        stance = "marginal -- DP active with a conservative (higher) margin"
    return {"n_usable_leads": len(usable), "n_days_total": len({r["day"] for r in rows}),
            "fit": f, "stance": stance}


# ----------------------------------------------------------------- collect (PAID -- not auto-run)
def collect_extra_leads():
    """Adds the ~5.5h and ~1.5h legs to today's collection, on the SAME target window N-26 uses.
    PAID: 2 calls today (~8,440 credits at the documented rate), repeating daily until enough
    days accumulate. NOT invoked by __main__ automatically -- a human runs this mode explicitly."""
    banner("N-42 collect  add %s leads to today's target window   [PAID, ~%s credits/day]"
          % (ADDITIONAL_LEADS, format(len(ADDITIONAL_LEADS) * CREDITS_PER_CALL, ",")))
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    today = site_now().date()
    m = json.load(open(MANIFEST, encoding="utf-8")) if os.path.exists(MANIFEST) else {"days": {}}
    day = m["days"].setdefault(today.isoformat(), {"legs": {}})
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)
    target = site_now().replace(hour=TARGET_HOUR_SITE, minute=0, second=0, microsecond=0)
    w = site_window(target, WIN_H)
    calls = 0
    for L in ADDITIONAL_LEADS:
        key_l = "%.1f" % L
        if key_l in day["legs"] and day["legs"][key_l].get("forecast_done"):
            continue
        due = w["_start_utc"] - timedelta(hours=L)
        now = utc_now()
        actual_lead = lead_hours(w["_start_utc"], now)
        if abs(actual_lead - L) > 1.0 and now < due:
            print("   lead %.1fh not due yet (due %s UTC) -- skip for now" % (L, due.strftime("%H:%M")))
            continue
        tag = "n42_f_%s_lead%05.2f" % (today.isoformat(), max(actual_lead, 0))
        p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
             "date_time": {k: v for k, v in w.items() if not k.startswith("_")}}
        r = submit_poll(key, "heatmap", p, tag)
        calls += 1
        if r.get("ok"):
            day["legs"][key_l] = {"lead_h": round(actual_lead, 3), "forecast_tag": tag,
                                  "forecast_done": True, "outcome_done": False}
            print("   lead %.2fh: %s tiles" % (actual_lead, format(len(field_max(r["result"])), ",")))
        else:
            print("   lead %.1fh FAILED: %s" % (L, r.get("error")))
        json.dump(m, open(MANIFEST, "w"), indent=1, default=str)
    # outcomes for any earlier day's legs whose window has elapsed
    for dk, dd in m["days"].items():
        for lk, leg in dd.get("legs", {}).items():
            if leg.get("outcome_done"):
                continue
            wl = site_window(datetime_from_day(dk), WIN_H)
            if utc_now() < wl["_end_utc"] + timedelta(minutes=15):
                continue
            tag = "n42_h_%s_%s" % (dk, lk)
            p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
                 "date_time": {k: v for k, v in wl.items() if not k.startswith("_")}}
            r = submit_poll(key, "heatmap", p, tag)
            calls += 1
            if r.get("ok"):
                leg["outcome_tag"] = tag
                leg["outcome_done"] = True
                print("   outcome %s/%s: %s tiles" % (dk, lk, format(len(field_max(r["result"])), ",")))
            json.dump(m, open(MANIFEST, "w"), indent=1, default=str)
    after = credits_remaining(key)
    print("\n   %d call(s). cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (calls, format(after, ","), format(before - after, ",")))
    return 0


def datetime_from_day(dk):
    from datetime import datetime
    y, mo, d = (int(x) for x in dk.split("-"))
    return datetime(y, mo, d, TARGET_HOUR_SITE, 0, tzinfo=site_tz())


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    sys.exit({"validate": validate, "status": status, "report": report,
             "collect": collect_extra_leads}.get(mode, status)())
