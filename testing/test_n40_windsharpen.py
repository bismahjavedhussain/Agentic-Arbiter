# -*- coding: utf-8 -*-
"""N-40  ---  DOES *WIND* UNCERTAINTY SHARPEN ENOUGH TO MAKE THE STOPPING RULE AGENTIC?   FREE.

    Zero API calls. Local solver + the free NOAA ASOS archive (Iowa State Environmental Mesonet).

WHY THIS TEST EXISTS -- the short version of a bad night
    N-24 established that the DP stopping rule earns nothing unless SOME quantity's uncertainty
    shrinks as the decision hour approaches. Its headline "+0.356 cost units/day, 11.2 sigma" was
    computed with the sharpening exponent HELD FIXED AT 0.50 (test_n24_breakeven.py line 211) -- an
    assumed random-walk value, never measured.

    N-25 measured it, on FortyGuard's TEMPERATURE forecast, 17,862 tiles x 5 known leads:

        b = -0.0608,  SE 0.0803,  t = -0.76,  R^2 0.161,  95 % CI [-0.316, +0.195]

    Two things follow, and both matter:
      * FAIL against the pre-registered b >= 0.187. Recorded as a fail; threshold not moved.
      * The CI contains 0, 0.129 AND 0.187 -- so it does NOT establish that the forecast fails to
        sharpen. It is UNDERPOWERED. But it DOES exclude 0.500, which is the value N-24 assumed.
        The headline agentic margin rests on an assumption the data rules out.

    So the temperature channel cannot carry the claim. This test asks whether a different channel can.

WHY WIND DIRECTION IS THE RIGHT CANDIDATE, AND IT IS NOT A GUESS
    1. Direction is what decides the outcome. CEC-500-2013-065, six instrumented condensers:
       recirculation varies 1.60x across wind-direction sectors against 1.22x across the entire
       measured wind-speed range. Direction is a switch; speed is a dimmer.
    2. Direction uncertainty demonstrably shrinks with lead. Measured here from KIAD ASOS, 72 days,
       target hour 16 site-local, calm hours (< 3 kt) excluded because ASOS reports drct = 0 when
       calm. PERSISTENCE error, which is the honest LOWER BOUND on any forecast's skill:
           MAE  33.9 deg at 1 h lead  ->  62.1 deg at 12 h
           b = +0.278, SE 0.0335, t = +8.28, 95 % CI [+0.203, +0.353]   (12 leads, 10 dof)
       Compare N-25's t = -0.76. This trend is real; that one is not resolvable.
    3. FortyGuard exposes no wind at all (36 response fields checked), so this channel is
       independent of the endpoint whose forecast just failed.

AND IT FIXES A DEFECT OF OUR OWN, WHICH IS REQUIRED REGARDLESS OF THE VERDICT
    solver.ensemble() perturbs wind direction with wind_sd_deg = 15.0. The MEASURED error is
    52-71 deg. We have been understating the dominant uncertainty by a factor of 3.5-4.7, which
    means N-23's 27.04x knife edge and every p90 bound were computed with far too narrow a
    direction spread. This test uses the measured per-lead distribution instead, and it samples the
    EMPIRICAL errors rather than a Gaussian, because direction errors are heavy-tailed (reversals).

THE CONSTRUCTION -- what is combined with what
    The quantity the decision thresholds is intake temperature = ambient + recirculation rise.
    Its forecast uncertainty at lead l therefore has two independent parts:

        sigma_total(l) = sqrt( sigma_ambient(l)^2 + sigma_recirc(l)^2 )

        sigma_ambient(l)   MEASURED by N-25 tonight: 0.106 / 0.108 / 0.096 / 0.130 / 0.112 C at
                           leads 9.41 / 7.49 / 5.49 / 3.49 / 1.49. Essentially FLAT. Interpolated
                           across 1-12 h. It contributes no sharpening -- that is the N-25 result.
        sigma_recirc(l)    computed HERE: 100 solver members per lead with direction sampled from
                           the measured error distribution at that lead. All the sharpening, if
                           any, has to come from this term.

THE RISK THIS TEST IS MOST LIKELY TO DIE ON -- named before running, not after
    SATURATION. The bad plume sector is ~40 deg wide. The direction error is 34-62 deg. Both ends
    are comparable to or wider than the sector, so the ensemble may be geometrically unresolvable
    at EVERY lead and sigma_recirc may come out flat even though the direction error clearly
    shrinks. That would mean b ~ 0 through the solver despite b = +0.278 in degrees, and the DP
    earns nothing from wind either. If that happens it is a real null, and it gets reported as one.

PRE-REGISTERED -- fixed before a single number was looked at
    W1  PRIMARY. Using the measured sigma_total(l) SHAPE (normalised so sigma_total(12) equals
        N-24's calibrated sd of 0.15036 C, so the only thing that differs from N-24 is the shape),
        the DP must beat the exhaustively tuned fixed-hour adversary by >= 2 SE on 20,000 HELD-OUT
        days. Same adversary, same scoring code, imported from N-9 rather than reimplemented.
    W2  The fitted exponent on sigma_total(l) must be >= 0.129, N-24's break-even, and is reported
        with n, SE and a 95 % CI. No exponent from this project is quoted without its interval.
    W3  At least 8 usable leads, and sigma_recirc must be non-degenerate at every lead (> 0.001 C).
        If the plume never reaches the intake the test is VOID, not a pass and not a fail.

    Reported alongside, NOT as pass conditions: the absolute (un-normalised) sigma_total, and the
    same fit at four other nominal wind directions, because the agent does not get to choose the
    wind and a result that only holds at one bearing is worth knowing about.
"""
import json, math, os, statistics, sys, time, urllib.parse, urllib.request

import numpy as np

import solver
import staging
import test_n9_staging as n9
from common import banner, save_result, verdict, FIXTURES, RESULTS

# ----------------------------------------------------------------- pre-registered
W1_MIN_SIGMA = 2.0          # DP must beat the tuned adversary by this many standard errors
W2_MIN_B = 0.129            # N-24 break-even on the sharpening exponent
W3_MIN_LEADS = 8
W3_MIN_SPREAD_C = 0.001

# N-24's calibration, so this test differs from N-24 in the SIGMA SHAPE and nothing else.
N24_BIAS_C = 0.34893848727272736
N24_SD_C = 0.15035545399123917
N24_HW_C = 0.49499999999999744
MEASURED_PEAK_SD_H = 1.4475          # N-38, 15 days, leave-one-out floor 1.1579 h

# N-25's measured ambient forecast error, 17,862 tiles per lead.
N25_SIGMA_AMBIENT = {9.41: 0.1056, 7.49: 0.1084, 5.49: 0.0959, 3.49: 0.1299, 1.49: 0.1123}

LEADS = list(range(1, 13))
N_MEMBERS = 100
PRIMARY_DIR = 265.0                  # N-23: highest p90, i.e. where the staging decision binds
SENSITIVITY_DIRS = [180.0, 250.0, 285.0, 315.0]
WIND_SPEED_MS = 3.0                  # N-23's design speed
AMBIENT_C = 30.0
STEPS = 800
SEED = 40

TCRIT_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
            8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 15: 2.131, 20: 2.086}


def fit_ci(xs, ys):
    """OLS of ln(y) on ln(x) with SE and a 95 % CI on the slope. Same estimator as N-25."""
    n = len(xs)
    if n < 3:
        return None
    lx = [math.log(x) for x in xs]
    ly = [math.log(max(y, 1e-12)) for y in ys]
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    sxx = sum((x - mx) ** 2 for x in lx)
    if sxx <= 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(lx, ly)]
    dof = n - 2
    se = math.sqrt(sum(r * r for r in resid) / dof / sxx)
    sst = sum((y - my) ** 2 for y in ly)
    tc = TCRIT_95.get(dof, 1.96 if dof > 30 else 4.303)
    return {"n": n, "dof": dof, "b": b, "se": se, "t": b / se if se else float("inf"),
            "r2": 1 - sum(r * r for r in resid) / sst if sst > 0 else None,
            "ci_lo": b - tc * se, "ci_hi": b + tc * se, "tcrit": tc}


# ----------------------------------------------------------------- the wind data (free)
def angdiff(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def fetch_direction_errors(decision_hour=16, min_kt=3.0):
    """Empirical persistence errors of wind direction, per lead, from KIAD ASOS.

    Returns {lead_h: [signed errors in degrees]}. Cached to a fixture so the test is reproducible
    and so re-running costs nothing. This is the honest LOWER BOUND on forecast skill: any real
    forecast beats persistence, especially at long leads.
    """
    fx = os.path.join(FIXTURES, "n40_kiad_dir_errors.json")
    if os.path.exists(fx):
        d = json.load(open(fx, encoding="utf-8"))
        print("   using cached ASOS fixture (%d leads)" % len(d["errors"]))
        return {int(k): v for k, v in d["errors"].items()}, d["meta"]

    base = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    chunks = [(2026, 6, 1, 2026, 6, 21), (2026, 6, 21, 2026, 7, 11),
              (2026, 7, 11, 2026, 8, 1), (2026, 8, 1, 2026, 8, 12)]
    obs = {}
    for (y1, m1, d1, y2, m2, d2) in chunks:
        parts = [("station", "IAD"), ("data", "drct"), ("data", "sknt"),
                 ("year1", y1), ("month1", m1), ("day1", d1),
                 ("year2", y2), ("month2", m2), ("day2", d2),
                 ("tz", "America/New_York"), ("format", "onlycomma"), ("latlon", "no"),
                 ("missing", "M"), ("trace", "T"), ("direct", "no"), ("report_type", 3)]
        url = base + "?" + urllib.parse.urlencode(parts)
        raw = None
        for _ in range(4):
            try:
                raw = urllib.request.urlopen(
                    urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                    timeout=120).read().decode("utf-8", "replace")
                break
            except Exception:
                time.sleep(6)
        if raw is None:
            print("      chunk %02d-%02d FAILED after 4 attempts" % (m1, d1))
            continue
        for line in raw.splitlines()[1:]:
            p = [x.strip() for x in line.split(",")]
            if len(p) < 4:
                continue
            # Parse EVERY field before touching obs. setdefault() creates the key first, so
            # inlining float() into the append leaves an empty list behind whenever ASOS reports
            # "M" for a missing value -- which then blows up fmean() on an empty sequence.
            try:
                date, tm = p[1].split(" ")
                hh = int(tm.split(":")[0])
                drct = float(p[2])
                sknt = float(p[3])
            except Exception:
                continue
            obs.setdefault((date, hh), []).append((drct, sknt))
    agg = {k: (statistics.fmean(x[0] for x in v), statistics.fmean(x[1] for x in v))
           for k, v in obs.items()}
    errors = {}
    for lead in LEADS:
        h0 = decision_hour - lead
        if h0 < 0:
            continue
        e = []
        for (date, hh), (d, s) in agg.items():
            if hh != h0:
                continue
            tgt = agg.get((date, decision_hour))
            if tgt is None or s < min_kt or tgt[1] < min_kt:
                continue
            e.append(angdiff(tgt[0], d))
        if len(e) >= 15:
            errors[lead] = e
    meta = {"station": "KIAD", "decision_hour_site": decision_hour, "min_kt": min_kt,
            "n_hours": len(agg), "n_days": len({k[0] for k in agg}),
            "span": "2026-06-01 to 2026-08-11", "quantity": "persistence error of wind direction",
            "why_lower_bound": "any real forecast beats persistence; this understates skill",
            "calm_excluded_because": "ASOS reports drct=0 when calm, which is not a direction"}
    json.dump({"errors": {str(k): v for k, v in errors.items()}, "meta": meta},
              open(fx, "w"), indent=1)
    return errors, meta


# ----------------------------------------------------------------- the solver leg
def sigma_recirc_by_lead(site, intake, errors, nominal_dir, device):
    """sd of the intake RISE at each lead, direction sampled from the MEASURED error distribution.

    Empirical resampling, not Gaussian: wind-direction errors are heavy-tailed (a frontal passage
    or an outflow gives a near-reversal), and a Gaussian with the same sd would understate exactly
    the cases where the plume swings onto or off the intake.
    """
    rng = np.random.default_rng(SEED)
    out = {}
    for lead in sorted(errors):
        e = np.asarray(errors[lead], dtype=float)
        draws = rng.choice(e, size=N_MEMBERS, replace=True)
        dirs = nominal_dir + draws
        speeds = np.maximum(0.3, WIND_SPEED_MS + rng.normal(0, 1.0, N_MEMBERS))
        scales = np.maximum(0.1, 1.0 + rng.normal(0, 2.0 / 11.0, N_MEMBERS))
        ambs = np.full(N_MEMBERS, AMBIENT_C)
        dws = [solver.downwash_fraction(s, solver.CALIBRATED["downwash_uc"],
                                        solver.CALIBRATED["downwash_exponent"]) for s in speeds]
        if device:
            import warp_solver as ws
            Ts = ws.solve_batch(site, ambs, speeds, dirs, scales,
                                steps=STEPS, device=device, downwash=dws)
            rises = [solver.intake_temperature(Ts[i], site, *intake) - AMBIENT_C
                     for i in range(N_MEMBERS)]
        else:
            rises = []
            base = site.source.copy()
            for i in range(N_MEMBERS):
                site.source = base * scales[i]
                T = solver.solve(site, ambs[i], speeds[i], dirs[i],
                                 downwash_uc=solver.CALIBRATED["downwash_uc"])
                rises.append(solver.intake_temperature(T, site, *intake) - ambs[i])
            site.source = base
        r = np.asarray(rises, dtype=float)
        out[lead] = {"sd": float(r.std(ddof=1)), "mean": float(r.mean()),
                     "p90": float(np.quantile(r, 0.90)),
                     "frac_hot": float((r > 0.01).mean()),
                     "dir_sd_used_deg": float(draws.std(ddof=1))}
    return out


def sigma_ambient_at(lead):
    """N-25's measured ambient error, interpolated over 1-12 h. Flat by measurement, not by choice."""
    ks = sorted(N25_SIGMA_AMBIENT)
    if lead <= ks[0]:
        return N25_SIGMA_AMBIENT[ks[0]]
    if lead >= ks[-1]:
        return N25_SIGMA_AMBIENT[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= lead <= b:
            f = (lead - a) / (b - a)
            return N25_SIGMA_AMBIENT[a] * (1 - f) + N25_SIGMA_AMBIENT[b] * f
    return statistics.fmean(N25_SIGMA_AMBIENT.values())


# ----------------------------------------------------------------- the DP leg
def run_dp(sigma_by_lead, label):
    """Feed a MEASURED sigma(lead) array straight into N-9's machinery -- no power law anywhere.

    sigma_schedule() is bypassed deliberately: it generates sigma from an assumed exponent, and an
    assumed exponent is the thing that broke. The conformal half-width is scaled in proportion to
    the measured sigma rather than by a second assumed exponent.
    """
    max_lead = n9.ANCHOR_LEAD
    sig = np.zeros(max_lead + 1)
    sig[0] = 0.05
    for l in range(1, max_lead + 1):
        sig[l] = max(0.05, sigma_by_lead.get(l, sigma_by_lead[max(sigma_by_lead)]))
    ratio = sig / sig[max_lead]
    hws = np.maximum(0.05, N24_HW_C * ratio)
    hws[0] = 0.05

    base = dict(n9.BASE)
    base["peak_sd_h"] = MEASURED_PEAK_SD_H
    spec = staging.Spec(bias_c=N24_BIAS_C, **base)
    train = n9.Days(spec, sig, n9.N_TRAIN, n9.SEED)
    test = n9.Days(spec, sig, n9.N_TEST, n9.SEED + 1000)
    out = n9.score_all(spec, sig, N24_HW_C, hws, test)
    adv = n9.best_fixed_hour(spec, hws, train, test)
    g, se = n9.paired(adv["per_day"], out["stopping_rule"]["per_day"])
    return {"label": label, "gain": float(g), "se": float(se),
            "sigma_of_gain": float(g / se) if se > 0 else float("inf"),
            "dp_cost": float(out["stopping_rule"]["cost"]),
            "adv_cost": float(adv["test_cost"]), "adv_hour": int(adv["hour"]),
            "sigma_array": [float(x) for x in sig]}


# ----------------------------------------------------------------- main
def main():
    banner("N-40  does WIND uncertainty sharpen enough to make the stopping rule agentic?  [FREE]")
    print("   N-25 measured the TEMPERATURE channel: b = -0.0608, CI [-0.316, +0.195] -> FAIL,")
    print("   and underpowered, but it EXCLUDES the 0.500 N-24 assumed. This tests wind instead.")
    print("   Pre-registered: W1 DP beats tuned adversary by >= %.1f SE | W2 b >= %.3f (with CI) |"
          % (W1_MIN_SIGMA, W2_MIN_B))
    print("   W3 >= %d leads and non-degenerate spread." % W3_MIN_LEADS)

    print("\n   [1/4] wind-direction persistence errors from KIAD ASOS (free, no key)")
    errors, meta = fetch_direction_errors()
    if len(errors) < W3_MIN_LEADS:
        print("      only %d leads recovered -- W3 fails, test VOID." % len(errors))
        return 2
    print("      %d leads, %d-%d samples each, from %d days"
          % (len(errors), min(len(v) for v in errors.values()),
             max(len(v) for v in errors.values()), meta["n_days"]))
    dfit = fit_ci(sorted(errors), [statistics.fmean(abs(x) for x in errors[k])
                                   for k in sorted(errors)])
    print("      direction MAE exponent b = %+.4f  SE %.4f  t %+.2f  CI [%+.3f, %+.3f]"
          % (dfit["b"], dfit["se"], dfit["t"], dfit["ci_lo"], dfit["ci_hi"]))
    print("      *** and note: solver.ensemble() has been using wind_sd_deg = 15.0 while the")
    print("          measured sd is %.0f-%.0f deg. We understated the dominant uncertainty by %.1fx."
          % (min(statistics.pstdev(v) for v in errors.values()),
             max(statistics.pstdev(v) for v in errors.values()),
             statistics.fmean(statistics.pstdev(v) for v in errors.values()) / 15.0))

    print("\n   [2/4] propagating it through the solver, %d members per lead" % N_MEMBERS)
    site, intake = solver.demo_site()
    solver.assert_intake_clear(site, *intake, label="N-40 demo_site")
    device = None
    try:
        import warp_solver as ws
        if ws.HAVE_WARP:
            device = "cuda"
            print("      GPU batched path (warp). 6,000 solves would be ~60 min on CPU.")
    except Exception as e:
        print("      warp unavailable (%s) -- CPU path, this will take a while" % str(e)[:60])
    t0 = time.time()
    rec = sigma_recirc_by_lead(site, intake, errors, PRIMARY_DIR, device)
    print("      primary direction %.0f deg, %.1f s" % (PRIMARY_DIR, time.time() - t0))

    print("\n   %6s %10s %10s %10s %10s %10s %10s"
          % ("lead h", "dir sd", "rec mean", "rec sd", "rec p90", "frac hot", "sig_total"))
    sig_total, sig_total_norm = {}, {}
    rows = []
    for l in sorted(rec):
        sa = sigma_ambient_at(l)
        st = math.sqrt(sa ** 2 + rec[l]["sd"] ** 2)
        sig_total[l] = st
        rows.append({"lead_h": l, "dir_sd_deg": rec[l]["dir_sd_used_deg"],
                     "recirc_mean": rec[l]["mean"], "recirc_sd": rec[l]["sd"],
                     "recirc_p90": rec[l]["p90"], "frac_hot": rec[l]["frac_hot"],
                     "sigma_ambient": sa, "sigma_total": st})
        print("   %6d %10.1f %10.4f %10.4f %10.4f %9.1f%% %10.4f"
              % (l, rec[l]["dir_sd_used_deg"], rec[l]["mean"], rec[l]["sd"],
                 rec[l]["p90"], 100 * rec[l]["frac_hot"], st))

    degenerate = [l for l in rec if rec[l]["sd"] <= W3_MIN_SPREAD_C]
    if degenerate:
        print("\n   *** VOID: leads %s have spread <= %.4f C -- the plume never reaches the intake"
              % (degenerate, W3_MIN_SPREAD_C))
        print("       at %.0f deg. This is neither a pass nor a fail." % PRIMARY_DIR)
        save_result("n40_windsharpen.json", {"void": True, "degenerate_leads": degenerate,
                                             "rows": rows, "pass": None})
        return 2

    print("\n   [3/4] fitting the exponent, with an interval")
    f_abs = fit_ci(sorted(sig_total), [sig_total[l] for l in sorted(sig_total)])
    f_rec = fit_ci(sorted(rec), [rec[l]["sd"] for l in sorted(rec)])
    anchor = sig_total[max(sig_total)]
    for l in sig_total:
        sig_total_norm[l] = sig_total[l] * (N24_SD_C / anchor)
    print("      %-22s %+9s %8s %8s %8s   %s"
          % ("quantity", "b", "SE", "t", "R^2", "95 % CI"))
    for nm, f in (("sigma_recirc alone", f_rec), ("sigma_total (headline)", f_abs)):
        print("      %-22s %+9.4f %8.4f %8.2f %8.3f   [%+.3f, %+.3f]"
              % (nm, f["b"], f["se"], f["t"], f["r2"], f["ci_lo"], f["ci_hi"]))
    print("      sigma_total spans %.4f -> %.4f C over 1-12 h (ratio %.3f)"
          % (sig_total[min(sig_total)], sig_total[max(sig_total)],
             sig_total[max(sig_total)] / sig_total[min(sig_total)]))
    print("      N-24's assumed b was 0.500; N-25 measured -0.061 on temperature.")

    print("\n   [4/4] re-running N-24's comparison on the MEASURED sigma shape")
    print("      adversary and scoring imported from test_n9_staging -- same code, not a copy")
    dp_norm = run_dp(sig_total_norm, "measured shape, normalised to N-24's sd")
    dp_abs = run_dp(sig_total, "measured shape AND level")
    print("      %-42s %9s %8s %9s %9s %6s"
          % ("variant", "gain", "SE", "sigma", "dp cost", "adv h"))
    for d in (dp_norm, dp_abs):
        print("      %-42s %+9.4f %8.4f %+9.2f %9.4f %6d"
              % (d["label"], d["gain"], d["se"], d["sigma_of_gain"], d["dp_cost"], d["adv_hour"]))

    print("\n   SENSITIVITY -- the agent does not get to choose the wind")
    sens = {}
    for nd in SENSITIVITY_DIRS:
        r2 = sigma_recirc_by_lead(site, intake, errors, nd, device)
        st2 = {l: math.sqrt(sigma_ambient_at(l) ** 2 + r2[l]["sd"] ** 2) for l in r2}
        ff = fit_ci(sorted(st2), [st2[l] for l in sorted(st2)])
        sens[nd] = {"b": ff["b"], "se": ff["se"], "ci_lo": ff["ci_lo"], "ci_hi": ff["ci_hi"],
                    "sd_range": [min(r2[l]["sd"] for l in r2), max(r2[l]["sd"] for l in r2)],
                    "mean_rise": statistics.fmean(r2[l]["mean"] for l in r2)}
        print("      %3.0f deg  b %+.4f  SE %.4f  CI [%+.3f, %+.3f]  recirc sd %.4f-%.4f  mean rise %.4f"
              % (nd, ff["b"], ff["se"], ff["ci_lo"], ff["ci_hi"],
                 sens[nd]["sd_range"][0], sens[nd]["sd_range"][1], sens[nd]["mean_rise"]))

    w1 = dp_norm["sigma_of_gain"] >= W1_MIN_SIGMA
    w2 = f_abs["b"] >= W2_MIN_B
    w3 = len(rec) >= W3_MIN_LEADS and not degenerate
    ok = w1 and w2 and w3

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE ANY NUMBER WAS SEEN")
    print("      W1 DP beats tuned adversary by >= %.1f SE : %s  (%+.2f SE)"
          % (W1_MIN_SIGMA, w1, dp_norm["sigma_of_gain"]))
    print("      W2 fitted b >= %.3f                      : %s  (%+.4f, CI [%+.3f, %+.3f])"
          % (W2_MIN_B, w2, f_abs["b"], f_abs["ci_lo"], f_abs["ci_hi"]))
    print("      W3 >= %d leads, non-degenerate           : %s  (%d leads)"
          % (W3_MIN_LEADS, w3, len(rec)))
    if f_abs["ci_lo"] <= 0.0 <= f_abs["ci_hi"]:
        print("      NOTE the CI contains zero, so like N-25 this is underpowered on the exponent;")
        print("      W1 is the primary condition precisely because it tests the DECISION, not a slope.")
    print()

    verdict(ok,
            "PASS - wind-direction uncertainty, propagated through the calibrated solver with the "
            "MEASURED per-lead error distribution, sharpens at b = %+.4f (CI [%+.3f, %+.3f]) and the "
            "stopping rule beats the exhaustively tuned fixed-hour adversary by %+.2f SE on 20,000 "
            "held-out days. The agency claim now rests on a MEASURED channel instead of the assumed "
            "exponent 0.50 that N-25 excluded. FortyGuard supplies where the heat is; wind supplies "
            "when we will know."
            % (f_abs["b"], f_abs["ci_lo"], f_abs["ci_hi"], dp_norm["sigma_of_gain"]),
            "FAIL - b = %+.4f (CI [%+.3f, %+.3f]) and the DP gains %+.2f SE over the tuned adversary. "
            "If sigma_recirc is flat across leads this is SATURATION: the ~40 deg plume sector is "
            "narrower than the 34-62 deg direction error at every lead, so resolving the wind does not "
            "resolve the geometry. Neither channel sharpens. Report the null, drop the stopping-rule "
            "framing, and ship the measured behaviour that does not depend on sharpening -- N-23's "
            "27.04x self-widening margin, the line-of-sight refusal, and daily self-scoring."
            % (f_abs["b"], f_abs["ci_lo"], f_abs["ci_hi"], dp_norm["sigma_of_gain"]))

    save_result("n40_windsharpen.json", {
        "question": "does wind-direction uncertainty, through the solver, sharpen enough for the DP?",
        "why": "N-25 measured b = -0.0608 (CI [-0.316, +0.195]) on temperature: FAIL, underpowered, "
               "but it EXCLUDES the 0.500 N-24's headline assumed",
        "wind_data": meta, "direction_fit": dfit,
        "our_defect_fixed": {"was": "solver.ensemble wind_sd_deg = 15.0",
                             "measured_deg": [min(statistics.pstdev(v) for v in errors.values()),
                                              max(statistics.pstdev(v) for v in errors.values())],
                             "understated_by": statistics.fmean(
                                 statistics.pstdev(v) for v in errors.values()) / 15.0},
        "construction": "sigma_total = sqrt(sigma_ambient(N-25, measured, flat)^2 + sigma_recirc^2)",
        "n_members": N_MEMBERS, "primary_dir_deg": PRIMARY_DIR, "wind_speed_ms": WIND_SPEED_MS,
        "rows": rows,
        "fit_sigma_recirc": f_rec, "fit_sigma_total": f_abs,
        "dp_normalised": dp_norm, "dp_absolute": dp_abs,
        "sensitivity_by_direction": {str(k): v for k, v in sens.items()},
        "thresholds": {"w1_min_sigma": W1_MIN_SIGMA, "w2_min_b": W2_MIN_B,
                       "w3_min_leads": W3_MIN_LEADS},
        "w1": w1, "w2": w2, "w3": w3, "pass": ok,
        "n24_reference": {"bias_c": N24_BIAS_C, "sd_c": N24_SD_C, "hw_c": N24_HW_C,
                          "assumed_exponent": 0.50, "peak_sd_h": MEASURED_PEAK_SD_H},
        "limits": "persistence is a LOWER bound on forecast skill; one site geometry; sigma_ambient "
                  "comes from one day (N-25)"})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
