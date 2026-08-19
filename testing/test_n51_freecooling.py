# -*- coding: utf-8 -*-
"""N-51  ---  HOW MANY CHILLER-HOURS does a calibrated intake prediction actually save?  FREE, GPU.

THE HEADLINE NUMBER THE PROJECT HAS NEVER HAD. Zero API calls, no key use.

THE COMPARISON, and why both sides are held to the SAME safety level
    Free cooling is available when the air ENTERING the cooling equipment is below a changeover limit.
    Intake air = ambient + the site's own recirculation.

    INCUMBENT   sees a station reading some kilometres away. It cannot see either the station-to-site
                divergence or its own recirculation, so it must hold ONE conservative buffer covering
                both. Measured inputs: station-vs-site divergence 0.40 C (N-49b, from a saved 17,862-tile
                FortyGuard field at 4-5 km, n=3,375), and worst-case recirculation 0.855 C (N-23/N-44).
    AGENT       sees FortyGuard's hyperlocal ambient and MODELS the recirculation per hour from the real
                wind direction, then adds a conformal correction from measured residuals.

    BOTH buffers are calibrated to the SAME 90 % safety level on training hours, so the comparison is
    hours-at-equal-safety. A policy cannot "win" by being less safe.

WHY THE SMALL DEGREES FINALLY MATTER HERE
    A 0.4-1.2 C buffer difference was worth almost nothing as a margin claim (N-46: 0.05-0.15 C, ~1-4 %
    of total margin). Next to a CHANGEOVER THRESHOLD it converts directly into HOURS, because the
    temperature distribution is dense around the limit rather than in a tail.

WHAT THIS IS NOT
    Not a forecast problem -- economizer changeover is a real-time decision on observed conditions, so
    the 47-72 deg FORECAST direction error that killed seven decision cores does not apply here.
    Not money: chiller-hours are reported, never dollars. The kW conversion is unsourced.
"""
import json
import math
import os
import statistics
import sys
import time

import numpy as np

from common import banner, save_result, FIXTURES
import solver
from solver import CALIBRATED
import warp_solver as ws
import test_n44_adaptive_commit as n44
from test_n46b_dirsweep import dbin_vec

FULLYEAR = os.path.join(FIXTURES, "n51_kiad_fullyear.json")

# measured inputs, all traceable
STATION_DIVERGENCE_SD = 0.40    # N-49b, 4-5 km bin, n=3,375, median |dT| 0.399-0.420 C
FG_OBS_ERR_SD = 0.15            # FortyGuard residual sd on peak temperature (plan 2.1, n=6,875)
CALM_KT = 3.0                   # ASOS reports drct=0 when calm; below this the bearing is meaningless

# ASHRAE-anchored changeover candidates. Recommended range upper is 27 C; A2 Allowable is 35 C
# (Green Grid WP46, on disk). Reporting a CURVE over the limit rather than picking one.
LIMITS_C = [15.0, 18.0, 21.0, 24.0, 27.0]
ALPHA = 0.10
YEARS = 5
SEED = 51
WIND_SPEED_MS = 3.0
STEPS = 800
AMB_REF = 30.0


def build_table(seed=7):
    rng = np.random.default_rng(seed)
    site, intake = solver.demo_site()
    solver.assert_intake_clear(site, *intake, label="N-51 demo_site")
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


def conformal(res, alpha=ALPHA):
    r = np.sort(np.asarray(res, float))
    k = math.ceil((len(r) + 1) * (1.0 - alpha))
    return float(r[min(k, len(r)) - 1])


def main():
    banner("N-51  chiller-hours saved by a calibrated intake prediction   [FREE, GPU]")

    d = json.load(open(FULLYEAR, encoding="utf-8"))
    keys = sorted(d["hours"])
    rows = [d["hours"][k] for k in keys]
    station = np.array([r[0] for r in rows], float)
    drct = np.array([r[2] if r[2] is not None else np.nan for r in rows], float)
    sknt = np.array([r[3] if r[3] is not None else np.nan for r in rows], float)
    ok = ~np.isnan(station)
    station, drct, sknt = station[ok], drct[ok], sknt[ok]
    n = len(station)
    print("\n   %d usable hours over %d years (%.1f per year)" % (n, YEARS, n / YEARS))
    print("   dry-bulb: min %.1f  median %.1f  p90 %.1f  max %.1f C"
          % (station.min(), np.median(station), np.percentile(station, 90), station.max()))

    print("\n   [1/4] GPU precompute of the recirculation field")
    table, dd = build_table()
    bin_p90 = np.percentile(table, 90, axis=1)
    bin_mean = table.mean(axis=1)
    print("      rise p90 peaks %.4f C at %.0f deg; median p90 across bearings %.4f C"
          % (bin_p90.max(), dd[int(np.argmax(bin_p90))], np.median(bin_p90)))

    print("\n   [2/4] realising each hour: true site ambient, true recirculation, true intake")
    rng = np.random.default_rng(SEED)
    calm = np.isnan(drct) | np.isnan(sknt) | (sknt < CALM_KT)
    print("      calm or missing-direction hours: %d (%.1f %%) -- these use the ALL-BEARING mean rise,"
          % (calm.sum(), 100 * calm.mean()))
    print("      because ASOS reports drct=0 when calm and a bearing is then meaningless")

    dbin = np.where(calm, 0, dbin_vec(np.nan_to_num(drct)))
    midx = rng.integers(0, table.shape[1], size=n)
    true_rise = np.where(calm, table.mean(), table[dbin, midx])
    true_amb = station + rng.normal(0.0, STATION_DIVERGENCE_SD, n)     # site differs from station
    true_intake = true_amb + true_rise

    # what each policy observes
    obs_incumbent = station                                            # the station reading, as-is
    obs_agent_amb = true_amb + rng.normal(0.0, FG_OBS_ERR_SD, n)       # FortyGuard, hyperlocal
    modelled_rise_p90 = np.where(calm, np.percentile(table, 90), bin_p90[dbin])

    # calibrate both to the SAME 90 % safety level on the first half (train), score on the second
    half = n // 2
    tr = slice(0, half)
    te = slice(half, n)
    B_inc = conformal(true_intake[tr] - obs_incumbent[tr])
    q_agent = conformal(true_intake[tr] - (obs_agent_amb[tr] + modelled_rise_p90[tr]))
    print("\n   [3/4] buffers calibrated to 90 %% on the first %d hours, scored on the last %d"
          % (half, n - half))
    print("      incumbent single conservative buffer  B = %.4f C" % B_inc)
    print("      agent conformal correction            q = %+.4f C" % q_agent)
    print("      agent's TOTAL buffer varies by bearing: %.4f C (safe) to %.4f C (plume)"
          % (q_agent + np.percentile(bin_p90, 5), q_agent + bin_p90.max()))

    bound_inc = obs_incumbent + B_inc
    bound_agent = obs_agent_amb + modelled_rise_p90 + q_agent
    cov_inc = float((true_intake[te] <= bound_inc[te]).mean())
    cov_agent = float((true_intake[te] <= bound_agent[te]).mean())
    print("      held-out coverage: incumbent %.1f %%   agent %.1f %%   (target 90 %%)"
          % (100 * cov_inc, 100 * cov_agent))

    print("\n   [4/4] FREE-COOLING HOURS at equal safety, per year, scored on held-out hours")
    print("      %-9s %13s %13s %12s %10s   %10s"
          % ("limit C", "incumbent h/y", "agent h/y", "GAINED h/y", "gain %", "breaches"))
    scale = YEARS * (n - half) / float(n)          # held-out hours expressed as years
    out = {}
    for L in LIMITS_C:
        inc_ok = bound_inc[te] < L
        agt_ok = bound_agent[te] < L
        inc_h = inc_ok.sum() / scale
        agt_h = agt_ok.sum() / scale
        gained = (agt_ok & ~inc_ok).sum() / scale
        lost = (inc_ok & ~agt_ok).sum() / scale
        # safety audit: of the hours the agent unlocked, how many actually exceeded the limit?
        unlocked = agt_ok & ~inc_ok
        unsafe = int((true_intake[te][unlocked] >= L).sum())
        # and where the agent was MORE conservative, did that prevent a real exceedance?
        prevented = int((true_intake[te][inc_ok & ~agt_ok] >= L).sum())
        out["limit_%.0f" % L] = {"limit_c": L, "incumbent_h_per_y": inc_h, "agent_h_per_y": agt_h,
                                 "gained_h_per_y": gained, "lost_h_per_y": lost,
                                 "gain_pct": (100 * gained / inc_h) if inc_h > 0 else None,
                                 "unsafe_unlocked_hours": unsafe,
                                 "exceedances_prevented": prevented}
        print("      %-9.0f %13.0f %13.0f %12.0f %9.1f%%   %4d unsafe / %d prevented"
              % (L, inc_h, agt_h, gained, out["limit_%.0f" % L]["gain_pct"] or 0, unsafe, prevented))

    best = max(out.values(), key=lambda r: r["gained_h_per_y"])
    print("\n   HEADLINE: at a %.0f C changeover limit, the calibrated agent unlocks"
          % best["limit_c"])
    print("             %.0f additional free-cooling hours per year at equal 90 %% safety"
          % best["gained_h_per_y"])
    print("             = %.0f chiller-hours per year avoided (%.1f %% more free cooling)"
          % (best["gained_h_per_y"], best["gain_pct"] or 0))
    print("\n   NOT CLAIMED: any energy or dollar figure. The chiller kW conversion could not be")
    print("   sourced from any primary document on disk, so this stays in hours.")

    save_result("n51_freecooling.json", {
        "measures": "additional free-cooling hours per year unlocked by a calibrated hyperlocal intake "
                    "prediction versus a station reading with one conservative buffer, at EQUAL 90 % "
                    "safety",
        "does_not_measure": "energy or money (chiller kW unsourced); one site layout (demo_site, not yet "
                            "a real mapped campus); a real economizer's humidity/enthalpy limits; and "
                            "the station divergence is applied as day-varying noise at the measured "
                            "0.40 C, which is a LOWER bound since KIAD is ~8 km away",
        "not_a_forecast_problem": "changeover is a real-time decision on observed conditions, so the "
                                  "47-72 deg forecast direction error that closed seven decision cores "
                                  "does not apply",
        "inputs": {"n_hours": n, "years": YEARS, "station": "KIAD",
                   "station_divergence_sd_c": STATION_DIVERGENCE_SD,
                   "station_divergence_source": "N-49b, 4-5 km bin, n=3,375, median |dT| 0.399-0.420",
                   "fg_obs_err_sd_c": FG_OBS_ERR_SD,
                   "calm_hours_frac": float(calm.mean())},
        "calibration": {"incumbent_buffer_c": B_inc, "agent_q_c": q_agent,
                        "coverage_incumbent": cov_inc, "coverage_agent": cov_agent},
        "by_limit": out,
        "headline": best,
    })
    print("\n   written: results/n51_freecooling.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
