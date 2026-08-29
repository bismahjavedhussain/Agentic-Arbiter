# -*- coding: utf-8 -*-
"""PLUME UNCERTAINTY -- turning the dispersion ensemble into the width of the safety bound.

    python plume_uncertainty.py        # builds the spread tables, calibrates, and self-tests

ZERO API CALLS. No new PDE solves: the spread is resampled from the rise table already computed.

--------------------------------------------------------------------------------------------
WHY THIS EXISTS -- and the claim it replaces
--------------------------------------------------------------------------------------------
The agent's bound had a hole. It added a POINT ESTIMATE of the plume rise and attached no
uncertainty to it at all, while carrying a carefully calibrated margin for the temperature
forecast. That is inconsistent: the agent does not know tomorrow's wind DIRECTION either, and the
plume term depends on direction far more sharply than on anything else.

A previous session claimed the ensemble spread was already "the conformal normalizer... now
implemented and tested". It was not. `conformal.NormalizedConformal` existed and passed its
self-test, but nothing in the agent called it, and `agent.ensemble_spread()` was dead code. This
module is that claim actually built.

--------------------------------------------------------------------------------------------
WHERE THE UNCERTAINTY COMES FROM -- measured, not assumed
--------------------------------------------------------------------------------------------
N-40 MEASURED THE SPREAD OF WIND DIRECTION OVER THE LEAD TIME at 47-72 deg, from KIAD ASOS
observations. IT IS NOBODY'S FORECAST ERROR. It is how far the direction itself moves between the
hour a plan is made and the hour that plan applies to (47.3 deg at a 2 h lead, 71.6 deg at 10 h),
and using it as the allowance is deliberately conservative, because a real forecast tracks
direction better than assuming it holds. So the agent's plume estimate is the rise at the FORECAST
bearing, the truth is the rise at the ACTUAL bearing, and the error between them is a real,
measured consequence of having to commit to a plan before the hour arrives.

The spread of the rise over that direction distribution is the per-hour DIFFICULTY signal, and it
varies enormously with bearing -- measured on the committed geometry at sigma_dir = 47 deg:

    0.00594 C at 85 deg  (plume blows away from the intake)
    0.13949 C at 220 deg (plume swings across the intake)
    a ratio of 23.5x

A single fixed plume margin is therefore wrong in both directions at once: far too wide in the
calm sector, and too narrow exactly where the geometry is decisive. That is the textbook case for
a normalized nonconformity score -- Romano, Patterson & Candes, "Conformalized Quantile
Regression", NeurIPS 2019, arXiv:1905.03222.

--------------------------------------------------------------------------------------------
WHICH sigma_dir THE SHIPPED BOUND USES, and why that is not a hidden choice
--------------------------------------------------------------------------------------------
N-40 measured a RANGE, 47-72 deg. Both ends are calibrated and reported. The shipped bound uses
the value that produces the WIDER margin, because a safety bound should sit at the pessimistic end
of a measured range rather than the flattering one. The other end is reported alongside so the
cost of that choice is visible instead of buried.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
import conformal as C                                                        # noqa: E402
import metros as M                                                           # noqa: E402
from agent import (BEARINGS, CALM_KT, SIGMA_DIR_DEG, SPEED_GRID_MS, STEP_DEG,  # noqa: E402
                   banner, load_hours, lookup_rise, rise_table, say)

ALPHA = 0.10
N_MEMBERS = 400          # resampling draws per grid cell; a lookup, not a solve
SEED = 40                # named for N-40, the measurement this perturbation comes from
SPEED_SD_MS = 1.0        # speed perturbation, same value solver.ensemble() has always used


def spread_table(mode, sigma_dir, cache=True):
    """sd of the intake rise per (bearing, speed) cell, under the MEASURED direction spread.

    Costs no PDE solves. The rise table is already a function of (bearing, speed), so the
    ensemble is evaluated by resampling that table at perturbed bearings and speeds -- which is
    exactly what an ensemble over those two inputs means. Deterministic: one fixed seed, stated.

    🔴 THE CACHE PATH IS PER-SITE, AND IT WAS NOT, AND THAT SHIPPED.
    This table is resampled from `rise_table(mode)`, which is computed on THIS SITE'S OWN committed
    geometry -- so it is a per-site physical quantity, not a shared methodology constant. Until
    2026-08-24 the cache key was `os.path.join(DEMO, ...)` with NO metro prefix, so the first site
    built wrote the file and every site built afterwards silently READ IT BACK. Measured on disk
    when this was found: four `spread_table_*` files, all stamped 2026-08-19 00:30, against
    Ashburn's own rise table at 00:47 the same day and Chicago's and Dulles's at 2026-08-20 02:16
    and 02:24 -- i.e. the plume half of the safety bound was Ashburn's at all three sites.
    That is gotcha #132's family ("one site's value used for another"), which this project has now
    committed five times, and it is why `M.demo_path` exists. Nothing caught it because
    `check_wind_is_this_sites_own` was written for the wind record specifically rather than for the
    general rule; audit check `check_no_unsuffixed_per_site_artefact` is the general form.
    """
    cp = M.demo_path("spread_table_%s_sd%02d.json" % (mode, int(round(sigma_dir))))
    if cache and os.path.exists(cp):
        d = json.load(open(cp, encoding="utf-8"))
        return np.array(d["spread"]), d

    tab, refused, _ = rise_table(mode)
    rng = np.random.default_rng(SEED)
    out = np.zeros((len(BEARINGS), len(SPEED_GRID_MS)))
    for bi, b in enumerate(BEARINGS):
        for si, sp in enumerate(SPEED_GRID_MS):
            pb = (b + rng.normal(0.0, sigma_dir, N_MEMBERS)) % 360.0
            ps = np.clip(sp + rng.normal(0.0, SPEED_SD_MS, N_MEMBERS), 0.3, None)
            r = lookup_rise(tab, pb, ps)
            out[bi, si] = float(r.std(ddof=1))
    meta = {"mode": mode, "sigma_dir_deg": sigma_dir, "n_members": N_MEMBERS, "seed": SEED,
            "speed_sd_ms": SPEED_SD_MS,
            "bearings": [float(b) for b in BEARINGS], "speeds": SPEED_GRID_MS,
            "spread_min_c": float(out.min()), "spread_max_c": float(out.max()),
            "spread_median_c": float(np.median(out)),
            # A ratio is meaningless when the minimum is exactly zero, which happens in `facing`
            # mode: every refused bearing looks up the same table row, so the resampled spread is
            # identically 0 and the ratio blows up to ~6e10. Report the degeneracy instead of a
            # spectacular non-number -- an absurd figure in an output is a bug, not a result.
            "spread_min_nonzero_c": (float(out[out > 0].min()) if (out > 0).any() else None),
            "ratio_max_over_min": (float(out.max() / out.min()) if out.min() > 1e-9 else None),
            "ratio_degenerate_min_is_zero": bool(out.min() <= 1e-9),
            "spread": [[round(float(v), 6) for v in row] for row in out]}
    meta["metro"] = M.metro_key()          # so a table can never be mistaken for another site's
    if cache:
        os.makedirs(DEMO, exist_ok=True)
        json.dump(meta, open(cp, "w", encoding="utf-8"), allow_nan=False)
    return out, meta


def lookup_spread(sp_tab, bearing, speed):
    """Nearest neighbour on the same grid the rise table uses."""
    bi = (np.round(np.asarray(bearing, dtype=float) / STEP_DEG).astype(int)) % len(BEARINGS)
    sg = np.asarray(SPEED_GRID_MS)
    si = np.abs(np.asarray(speed, dtype=float)[:, None] - sg[None, :]).argmin(axis=1)
    return sp_tab[bi, si]


def build_calibration(mode, sigma_dir):
    """The (plume error, difficulty) pairs, on all 43,763 real hours.

    truth  = rise at the ACTUAL bearing the station recorded
    agent  = rise at the FORECAST bearing = actual + a draw from the MEASURED N-40 error
    error  = truth - agent          <- what a one-sided upper bound must cover
    diff   = ensemble spread at the FORECAST bearing/speed, i.e. what the agent can know
             at decision time WITHOUT knowing the outcome
    """
    keys, T, Td, drct, sknt = load_hours(with_dewpoint=True)
    tab, refused, _ = rise_table(mode)
    sp_tab, _ = spread_table(mode, sigma_dir)

    b_true = np.where(np.isnan(drct), 0.0, drct)
    s_ms = np.maximum(np.where(np.isnan(sknt), 0.0, sknt) * 0.514444, 0.3)
    calm = np.isnan(drct) | (np.where(np.isnan(sknt), 0.0, sknt) < CALM_KT)

    rng = np.random.default_rng(SEED)
    b_fcst = (b_true + rng.normal(0.0, sigma_dir, len(b_true))) % 360.0

    rise_true = lookup_rise(tab, b_true, s_ms)
    rise_fcst = lookup_rise(tab, b_fcst, s_ms)
    diff = lookup_spread(sp_tab, b_fcst, s_ms)

    ok = ~calm                        # calm hours have no defined bearing; excluded and counted
    return {"keys": keys, "err": (rise_true - rise_fcst)[ok], "diff": diff[ok],
            "n_calm_excluded": int(calm.sum()), "n": int(ok.sum()),
            "day": np.array([k[:10] for k in keys])[ok],
            "hod": np.array([int(k[-2:]) for k in keys])[ok]}


def calibrate(mode="longest", alpha=ALPHA):
    """Fit both a FIXED plume margin and a NORMALIZED one, on held-out days, and compare."""
    out = {}
    for sd in SIGMA_DIR_DEG:
        cal = build_calibration(mode, sd)
        days = np.array(sorted(set(cal["day"])))
        cut = set(days[0::2])                      # alternating days, as backtest.py uses
        m_cal = np.array([d in cut for d in cal["day"]])
        m_te = ~m_cal

        fixed = C.split_conformal(cal["err"][m_cal], alpha)
        nc = C.NormalizedConformal(alpha, floor=1e-3).fit(cal["err"][m_cal], cal["diff"][m_cal])

        cov_fixed = float((cal["err"][m_te] <= fixed["q"]).mean())
        marg_norm = nc.margin(cal["diff"][m_te])
        cov_norm = float((cal["err"][m_te] <= marg_norm).mean())

        # the point of an adaptive width: coverage held where it is HARD, width saved where easy
        d_te = cal["diff"][m_te]
        easy = d_te <= np.percentile(d_te, 25)
        hard = d_te >= np.percentile(d_te, 75)
        out[str(sd)] = {
            "sigma_dir_deg": sd, "n_cal": int(m_cal.sum()), "n_test": int(m_te.sum()),
            "n_calm_excluded": cal["n_calm_excluded"],
            "fixed_margin_c": fixed["q"], "fixed_coverage": cov_fixed,
            "fixed_coverage_easy": float((cal["err"][m_te][easy] <= fixed["q"]).mean()),
            "fixed_coverage_hard": float((cal["err"][m_te][hard] <= fixed["q"]).mean()),
            "normalized_multiplier": nc.mult_,
            "normalized_coverage": cov_norm,
            "normalized_coverage_easy": float((cal["err"][m_te][easy]
                                               <= marg_norm[easy]).mean()),
            "normalized_coverage_hard": float((cal["err"][m_te][hard]
                                               <= marg_norm[hard]).mean()),
            "mean_margin_fixed_c": float(fixed["q"]),
            "mean_margin_norm_c": float(marg_norm.mean()),
            "margin_norm_min_c": float(marg_norm.min()),
            "margin_norm_max_c": float(marg_norm.max()),
            "mean_margin_norm_easy_c": float(marg_norm[easy].mean()),
            "mean_margin_norm_hard_c": float(marg_norm[hard].mean()),
        }
    # the shipped bound takes the PESSIMISTIC end of the measured range
    ship = max(out.values(), key=lambda r: r["mean_margin_norm_c"])
    out["shipped"] = {"sigma_dir_deg": ship["sigma_dir_deg"],
                      "multiplier": ship["normalized_multiplier"],
                      "why": "the wider of the two ends of N-40's measured 47-72 deg range; "
                             "a safety bound belongs at the pessimistic end of a measurement"}
    return out


def main():
    banner("PLUME UNCERTAINTY   the dispersion ensemble as the width of the bound.  [no API calls]")
    say("   metro: %s   (spread tables and calibration are THIS site's own)" % M.metro_key())
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        say("   [%s] %-54s %s" % ("PASS" if cond else "FAIL", name, detail))

    say("\n1. SPREAD TABLES -- resampled from the existing rise table, no new PDE solves")
    metas = {}
    for mode in ("longest", "facing"):
        for sd in SIGMA_DIR_DEG:
            _, m = spread_table(mode, sd)
            metas["%s_%.0f" % (mode, sd)] = m
            say("      %-8s sigma_dir %2.0f deg : spread %.5f..%.5f C  median %.5f  %s"
                % (mode, sd, m["spread_min_c"], m["spread_max_c"], m["spread_median_c"],
                   ("ratio %.1fx" % m["ratio_max_over_min"]) if m["ratio_max_over_min"]
                   else "ratio undefined (min is 0: refused bearings give identical lookups)"))
    # judged on `longest`, the REALISTIC placement -- not on the best number across all modes
    prime_ratios = [m["ratio_max_over_min"] for k, m in metas.items()
                    if k.startswith("longest") and m["ratio_max_over_min"]]
    check("the difficulty signal is not flat on the REALISTIC placement",
          prime_ratios and max(prime_ratios) > 2.0,
          "longest: %s" % ", ".join("%.1fx" % r for r in prime_ratios))

    say("\n2. CALIBRATION on 43,763 real hours, held-out alternating days")
    cal = calibrate("longest")
    for sd in SIGMA_DIR_DEG:
        r = cal[str(sd)]
        say("\n      sigma_dir = %.0f deg   (n_cal %s, n_test %s, calm excluded %s)"
            % (sd, format(r["n_cal"], ","), format(r["n_test"], ","),
               format(r["n_calm_excluded"], ",")))
        say("        FIXED width      margin %.5f C   coverage %.4f   easy %.4f   hard %.4f"
            % (r["fixed_margin_c"], r["fixed_coverage"],
               r["fixed_coverage_easy"], r["fixed_coverage_hard"]))
        say("        NORMALIZED width mult  %.4f     coverage %.4f   easy %.4f   hard %.4f"
            % (r["normalized_multiplier"], r["normalized_coverage"],
               r["normalized_coverage_easy"], r["normalized_coverage_hard"]))
        say("        width: fixed %.5f C everywhere;  normalized %.5f..%.5f C "
            "(easy mean %.5f, hard mean %.5f)"
            % (r["fixed_margin_c"], r["margin_norm_min_c"], r["margin_norm_max_c"],
               r["mean_margin_norm_easy_c"], r["mean_margin_norm_hard_c"]))

    prime = cal[str(SIGMA_DIR_DEG[0])]
    check("normalized coverage lands at nominal",
          abs(prime["normalized_coverage"] - (1 - ALPHA)) < 0.02,
          "%.4f" % prime["normalized_coverage"])
    # 🔴 TWO CLAIMS, BECAUSE ONLY ONE OF THEM IS ALWAYS MEASURABLE.
    # This was a single strict check, `fixed_hard < normalized_hard`, and it is the right claim at
    # Ashburn: 0.9212 vs 0.9412, a real two-point gain on the quartile that matters. It FAILED at
    # the first national paired facility with `fixed 0.8493 vs normalized 0.8493` -- bit-identical,
    # because that pair sits 350 m apart against Ashburn's 165 m and its plume rise is three orders
    # of magnitude smaller (fixed margin 0.00009 C vs 0.08658 C). With a degenerate width there is
    # nothing to normalize, so both estimators classify every test point the same way. That is
    # physics, not a regression.
    #
    # Relaxing the check to `<=` would have made it pass everywhere and assert almost nothing --
    # including at a site where normalization genuinely stopped working. So the always-true property
    # is asserted unconditionally, and the strict improvement is asserted wherever it is measurable
    # at all. DEGENERACY IS DETECTED BY THE COVERAGES BEING EQUAL, not by comparing the margin
    # against an invented "too small to matter" constant -- if normalization cannot move a single
    # test point, that is the fact, and it needs no threshold to state.
    degenerate = (prime["fixed_coverage_hard"] == prime["normalized_coverage_hard"])
    check("normalization never UNDER-covers the HARD quartile",
          prime["fixed_coverage_hard"] <= prime["normalized_coverage_hard"],
          "fixed %.4f vs normalized %.4f"
          % (prime["fixed_coverage_hard"], prime["normalized_coverage_hard"]))
    if degenerate:
        say("      NOTE: the plume half of the bound is DEGENERATE at this site -- fixed margin "
            "%.5f C, normalized %.5f..%.5f C, and the two estimators classify every test point "
            "identically. Strict improvement is not measurable here and is not claimed; the site "
            "is bounded by its TEMPERATURE half, as a standalone facility is."
            % (prime["fixed_margin_c"], prime["margin_norm_min_c"], prime["margin_norm_max_c"]))
    else:
        check("a FIXED width under-covers the HARD quartile",
              prime["fixed_coverage_hard"] < prime["normalized_coverage_hard"],
              "fixed %.4f vs normalized %.4f"
              % (prime["fixed_coverage_hard"], prime["normalized_coverage_hard"]))
    check("normalized is TIGHTER on the easy quartile than fixed",
          prime["mean_margin_norm_easy_c"] < prime["fixed_margin_c"],
          "%.5f vs %.5f C" % (prime["mean_margin_norm_easy_c"], prime["fixed_margin_c"]))
    say("\n      SHIPPED: sigma_dir %.0f deg, multiplier %.4f -- %s"
        % (cal["shipped"]["sigma_dir_deg"], cal["shipped"]["multiplier"], cal["shipped"]["why"]))

    # PER-SITE, for the same reason `spread_table`'s cache is: `calibrate()` -> `build_calibration()`
    # reads THIS SITE'S weather record via `load_hours()` and THIS SITE'S geometry via
    # `rise_table()`, so the shipped multiplier and sigma_dir are this site's measurements. A single
    # shared file meant every site after the first was bounded by the first one's plume statistics.
    p = M.demo_path("plume_uncertainty.json")
    json.dump({"generated_by": "AGENTIC-ARBITER/src/plume_uncertainty.py", "api_calls_made": 0,
               "metro": M.metro_key(),
               "alpha": ALPHA, "sigma_dir_measured_deg": SIGMA_DIR_DEG,
               "source_of_sigma_dir": ("N-40: the measured spread of wind direction over "
                                       "the lead time, from KIAD ASOS observations (47.3 "
                                       "deg at a 2 h lead, 71.6 deg at 10 h). Belongs to "
                                       "no forecaster: it is used as a deliberately "
                                       "conservative allowance, because any real forecast "
                                       "tracks direction better than assuming it holds."),
               "spread_tables": {k: {kk: vv for kk, vv in v.items() if kk != "spread"}
                                 for k, v in metas.items()},
               # PUBLISHED, so a reader is never shown a plume bound that cannot move a decision.
               # True means the fixed and normalized estimators classified every test hour
               # identically -- the pair is far enough apart that its rise is numerically nil, and
               # the site is effectively bounded by its temperature half alone. Stated rather than
               # smoothed over, because "this site has a plume bound" and "this site's plume bound
               # is 0.0001 C" are different facts.
               "plume_term_degenerate": bool(degenerate),
               "calibration": cal},
              open(p, "w", encoding="utf-8"), allow_nan=False)
    say("\n   wrote %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    say("\n" + "=" * 78)
    say("SELF-TEST %s" % ("PASSED" if ok_all else "FAILED -- do not wire this in"))
    say("=" * 78)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
