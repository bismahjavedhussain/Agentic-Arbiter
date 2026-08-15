# -*- coding: utf-8 -*-
"""N-45 step 2 of 3  ---  DIAGNOSTIC, run BEFORE any policy is written.

Answers two questions that decide whether N-45 is worth running at all:

  Q1  With a PHYSICAL threshold (ASHRAE class Allowable limit) instead of a p75 quantile of our own
      output, how many real days are actually decision-relevant? A day only matters if ambient is
      close enough to the limit that the 0-0.4 C recirculation rise decides whether you breach.
      If that band contains a handful of days, N-45 is unpowered and must be reported as such
      rather than dressed up with 65 configurations.

  Q2  Does ambient uncertainty actually SHRINK as the decision hour approaches, once the diurnal
      cycle is removed? Raw persistence error at lead 12 h has a mean of +8.8 C -- that is the sun,
      not forecast error, because lead 12 from 16:00 compares against 04:00. Subtracting the
      per-lead mean leaves the ANOMALY error, which is the fair persistence baseline.

Reports n, sd, SE and a 95 % CI on the fitted exponent, per methodology rule #1: no exponent is
ever quoted without them. FREE, no API key, no GPU.
"""
import json
import math
import os
import statistics
import sys

from common import banner, FIXTURES

FIXTURE = os.path.join(FIXTURES, "n45_kiad_temps.json")

# ASHRAE 2011 class Allowable upper limits, via Green Grid WP46 (on disk, read).
# [1 citation layer from ASHRAE -- flagged in n45-costmodel-PREREG.md section 2]
ASHRAE_LIMITS = {"A2": 35.0, "A3": 40.0}

# The largest intake rise the calibrated solver produces at this site, from N-23's direction sweep
# (p90 peaked at 0.3962 C at 265 deg). Used only to size the "last straw" band.
MAX_RISE_C = 0.40

TCRIT_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
            9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131}


def fit_loglog(xs, ys):
    """OLS slope of log(y) on log(x), with SE and 95 % CI. Returns (b, se, lo, hi, n)."""
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    n = len(lx)
    mx, my = statistics.fmean(lx), statistics.fmean(ly)
    sxx = sum((x - mx) ** 2 for x in lx)
    b = sum((x - mx) * (y - my) for x, y in zip(lx, ly)) / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(lx, ly)]
    dof = n - 2
    s2 = sum(r * r for r in resid) / dof
    se = math.sqrt(s2 / sxx)
    t = TCRIT_95.get(dof, 1.96)
    return b, se, b - t * se, b + t * se, n


def main():
    banner("N-45 step 2  is the decision LIVE? physical threshold + fair ambient error   [FREE]")

    if not os.path.exists(FIXTURE):
        print("   fixture missing. Run: python fetch_n45_ambient.py")
        return 2
    d = json.load(open(FIXTURE, encoding="utf-8"))
    temps = sorted(d["target_by_date"].values())
    n = len(temps)
    errors = {int(k): v for k, v in d["errors"].items()}

    print("\n   ambient at 16:00 site-local, KIAD, %d summer days 2021-2026" % n)
    print("      min %.1f   median %.1f   p90 %.1f   p99 %.1f   max %.1f C"
          % (temps[0], statistics.median(temps), temps[int(0.90 * (n - 1))],
             temps[int(0.99 * (n - 1))], temps[-1]))

    print("\n   Q1  HOW MANY DAYS ARE DECISION-RELEVANT?")
    print("       'ambient alone breaches' = no decision to make, you breach whatever you do.")
    print("       'LAST STRAW band' = ambient within %.2f C below the limit, so the recirculation" % MAX_RISE_C)
    print("       rise is what decides it. THAT is the only place a cooling decision changes anything.")
    print("\n      %-6s %8s %14s %14s %14s" % ("class", "limit C", "amb breaches", "LAST STRAW", "no risk"))
    q1 = {}
    for name in sorted(ASHRAE_LIMITS):
        lim = ASHRAE_LIMITS[name]
        n_over = sum(1 for t in temps if t >= lim)
        n_band = sum(1 for t in temps if lim - MAX_RISE_C <= t < lim)
        q1[name] = {"limit_c": lim, "n_ambient_breach": n_over, "n_last_straw": n_band,
                    "frac_last_straw": n_band / n}
        print("      %-6s %8.1f %8d (%4.1f%%) %8d (%4.1f%%) %8d (%4.1f%%)"
              % (name, lim, n_over, 100.0 * n_over / n, n_band, 100.0 * n_band / n,
                 n - n_over - n_band, 100.0 * (n - n_over - n_band) / n))

    print("\n   Q2  DOES AMBIENT UNCERTAINTY SHRINK AS THE DECISION HOUR APPROACHES?")
    print("       raw persistence error contains the diurnal cycle (lead 12 h from 16:00 compares")
    print("       against 04:00). The MEAN is that cycle; the SD around it is the real uncertainty.")
    print("\n      %-7s %5s %10s %10s %10s" % ("lead h", "n", "raw mean", "raw sd", "anomaly sd"))
    leads, sds = [], []
    q2 = {}
    for lead in sorted(errors):
        v = errors[lead]
        mu = statistics.fmean(v)
        sd_raw = statistics.stdev(v)                 # sample sd, not pstdev (GOTCHA #8)
        anom = [x - mu for x in v]                   # remove the diurnal offset for this lead
        sd_anom = statistics.stdev(anom)
        q2[lead] = {"n": len(v), "raw_mean_c": mu, "raw_sd_c": sd_raw, "anomaly_sd_c": sd_anom}
        leads.append(lead)
        sds.append(sd_anom)
        print("      %-7d %5d %+10.3f %10.3f %10.3f" % (lead, len(v), mu, sd_raw, sd_anom))

    b, se, lo, hi, npts = fit_loglog(leads, sds)
    ratio = sds[-1] / sds[0]
    print("\n      sd(anomaly) grows from %.3f C at %d h to %.3f C at %d h  ->  ratio %.2fx"
          % (sds[0], leads[0], sds[-1], leads[-1], ratio))
    print("      fitted sd(lead) proportional to lead^b :  b = %+.4f, SE %.4f, 95%% CI [%+.4f, %+.4f], n=%d"
          % (b, se, lo, hi, npts))
    print("      CI excludes zero: %s   (b > 0 means waiting genuinely buys a better ambient forecast)"
          % (lo > 0))

    out = {
        "measures": "whether a physically-specified commitment decision has any live days, and "
                    "whether ambient uncertainty shrinks with lead once the diurnal cycle is removed",
        "does_not_measure": "FortyGuard forecast skill (this is KIAD persistence, a LOWER bound), "
                            "and not the policy comparison itself",
        "n_days": n,
        "ambient_c": {"min": temps[0], "median": statistics.median(temps),
                      "p90": temps[int(0.90 * (n - 1))], "p99": temps[int(0.99 * (n - 1))],
                      "max": temps[-1]},
        "max_rise_c_assumed": MAX_RISE_C,
        "max_rise_source": "N-23 direction sweep, p90 peaked 0.3962 C at 265 deg",
        "ashrae_limits_source": "Green Grid WP46 on disk, quoting ASHRAE 2011 Allowable; ONE "
                                "CITATION LAYER REMOVED, confirm against ASHRAE primary before quoting",
        "q1_decision_relevant_days": q1,
        "q2_ambient_error_by_lead": q2,
        "q2_fit": {"b": b, "se": se, "ci_lo": lo, "ci_hi": hi, "n_points": npts,
                   "sd_ratio_12h_over_1h": ratio, "ci_excludes_zero": bool(lo > 0)},
    }
    path = os.path.join(os.path.dirname(FIXTURES), "n45_diag_live.json")
    json.dump(out, open(path, "w"), indent=1)
    print("\n   written: %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
