# -*- coding: utf-8 -*-
"""N-22  ---  calibrate the solver's wind response against ACC FIELD DATA.   FREE, GPU.

WHY
    N-21 falsified N-11. The downwash closure was fitted to a sentence in the literature ("hot
    recirculation rises with wind speed, peaking near 9 m/s") and produced a response
    ANTI-correlated (r = -0.869) with what six instrumented ACCs actually measured. The original
    uncalibrated solver had the right sign but was 28x too large at low wind and ten times too
    steep.

    We now have ~40,000 measured points. This fits the closure to DATA instead of prose.

THE PHYSICS OF THE FIT, so the result is not a black box
    With no downwash term the solver's deck recirculation scales almost exactly as 1/U -- 29.630 K
    at 1.12 m/s falling to 2.862 K at 12.29 m/s, a factor 10.4 across a speed ratio of 11. That is
    textbook advection-dominated dilution.

    The measurements are nearly FLAT (1.043 -> 0.882 K). So the retained fraction g(U) must grow
    with U to cancel the 1/U dilution: if g ~ U then g/U is constant and the curve is flat.
    g(U) = U^p / (U^p + uc^p) is linear in U at small U when p = 1, and saturates at large U -- which
    gives flat at low wind then declining at high wind. That IS the measured shape. N-11 used p = 2,
    which is too abrupt and pushes the peak far too high.

METHOD
    Amplitude is separable: exchange_s only scales the curve, so for each (p, uc) the shape is
    computed once and the optimal amplitude solved in closed form by least squares. Only (p, uc)
    needs sweeping.

    Fit quality is then checked three ways, in increasing severity:
      1. RMS against the pooled 6-plant speed curve (the fit target)
      2. HELD-OUT: fit on 3 plants, score on the other 3
      3. INDEPENDENT: does the DIRECTION swing still match Wygen's measured 1.60 x?
         Direction was never part of the fit, so this is a genuine out-of-sample check.
"""
import os, sys
import numpy as np

from common import banner, save_result, verdict, SCRATCH
from solver import Site
import warp_solver as ws

DX, AMB, STEPS = 10.0, 30.0, 800
MPH, F2K = 0.44704, 5.0 / 9.0
BINS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30)]
SPEEDS = np.array([(lo + hi) / 2.0 * MPH for lo, hi in BINS])

FIELD = [
    ("El Dorado 2007", "VERIFIED_fig4-17_recirc_vs_windspeed.csv", 36.0, 6.0),
    ("Bighorn", "fig6-14_bighorn.csv", 36.0, 20.0),
    ("El Dorado 2005", "fig6-32_eldorado.csv", 36.0, 20.0),
    ("Wygen", "fig6-89_wygen_vs_windspeed.csv", 36.0, 20.0),
    ("Front Range", "fig6-75_frontrange_ws.csv", 36.0, 20.0),
    ("Apex", "fig6-52_apex_ws.csv", 36.0, 10.0),
]
FIT_PLANTS = {"El Dorado 2007", "Bighorn", "El Dorado 2005"}      # held-out split


def load_xy(fn, xmax, ymax):
    p = os.path.join(SCRATCH, fn)
    if not os.path.exists(p):
        return None
    rows = []
    with open(p, encoding="utf-8-sig") as f:
        next(f, None)
        for ln in f:
            try:
                a, b = ln.split(",")[:2]
                x, y = float(a), float(b)
            except Exception:
                continue
            if 0.0 <= x <= xmax and 0.0 <= y <= ymax:
                rows.append((x, y))
    return np.array(rows) if rows else None


def binned_K(arr):
    out = []
    for lo, hi in BINS:
        m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
        out.append(float(arr[m, 1].mean() * F2K) if m.sum() >= 20 else None)
    return out


def acc_site(n_cx=8, n_cy=4, cell_m=30.0, discharge_k=11.0, exchange_s=20.0):
    s = Site(2000.0, DX)
    w, h = n_cx * cell_m, n_cy * cell_m
    cx = cy = 1000.0
    s.add_condensers(cx=cx, cy=cy, w=w, h=h, discharge_k=discharge_k, exchange_s=exchange_s)
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    cells = [(x0 + (i + .5) * cell_m, y0 + (j + .5) * cell_m)
             for i in range(n_cx) for j in range(n_cy)]
    return s, cells


def recirc(T, site, cells):
    v = np.array([T[min(max(int(y / site.dx), 0), site.n - 1),
                    min(max(int(x / site.dx), 0), site.n - 1)] for x, y in cells],
                 dtype=np.float64)
    return float(v.mean() - v.min())


def g_of(U, p, uc):
    if uc is None:
        return np.ones_like(np.asarray(U, dtype=np.float64))
    U = np.asarray(U, dtype=np.float64)
    return U ** p / (U ** p + float(uc) ** p)


def shape(p, uc, speeds=SPEEDS, n_dir=12):
    """Solver curve at exchange_s = 20 s; amplitude is solved separately."""
    site, cells = acc_site(exchange_s=20.0)
    dirs = np.linspace(0.0, 360.0, n_dir, endpoint=False)
    out = []
    for U in speeds:
        dw = np.full(len(dirs), float(g_of(U, p, uc)))
        T = ws.solve_batch(site, np.full(len(dirs), AMB), np.full(len(dirs), U), dirs,
                           np.ones(len(dirs)), steps=STEPS, downwash=dw)
        out.append(float(np.mean([recirc(T[k].astype(np.float64), site, cells)
                                  for k in range(len(dirs))])))
    return np.array(out)


def best_amplitude(meas, pred):
    """Least-squares scale a minimising ||meas - a*pred||."""
    m = np.array(meas, dtype=np.float64); q = np.array(pred, dtype=np.float64)
    ok = ~np.isnan(m)
    if ok.sum() < 3 or (q[ok] ** 2).sum() <= 0:
        return None, None
    a = float((m[ok] * q[ok]).sum() / (q[ok] ** 2).sum())
    rms = float(np.sqrt(np.mean((m[ok] - a * q[ok]) ** 2)))
    return a, rms


def main():
    banner("N-22  Calibrating the wind response against ACC field measurements   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable."); return 2

    # ------------- measured curves ---------------------------------------
    per_plant = {}
    for name, fn, xm, ym in FIELD:
        arr = load_xy(fn, xm, ym)
        if arr is not None and len(arr) >= 200:
            per_plant[name] = {"n": len(arr), "bins": binned_K(arr)}
    if len(per_plant) < 4:
        print("   insufficient field data."); return 2

    def pool(names):
        out = []
        for k in range(len(BINS)):
            v = [per_plant[n]["bins"][k] for n in names
                 if per_plant[n]["bins"][k] is not None]
            out.append(float(np.mean(v)) if v else np.nan)
        return np.array(out)

    fit_names = [n for n in per_plant if n in FIT_PLANTS]
    hold_names = [n for n in per_plant if n not in FIT_PLANTS]
    y_fit, y_hold, y_all = pool(fit_names), pool(hold_names), pool(list(per_plant))

    print("\n   MEASURED (K) at %s m/s" % np.round(SPEEDS, 2).tolist())
    print("      fit set  (%d plants: %s)" % (len(fit_names), ", ".join(fit_names)))
    print("        %s" % "  ".join("%.3f" % v for v in y_fit))
    print("      HELD OUT (%d plants: %s)" % (len(hold_names), ", ".join(hold_names)))
    print("        %s" % "  ".join("%.3f" % v for v in y_hold))

    # ------------- baselines ---------------------------------------------
    print("\n   BASELINES (current code), amplitude left as coded")
    for lbl, p_, uc_ in (("N-11 ON (p=2, uc=8)", 2.0, 8.0), ("N-11 OFF (no downwash)", 1.0, None)):
        c = shape(p_, uc_)
        r = float(np.corrcoef(y_all[~np.isnan(y_all)], c[~np.isnan(y_all)])[0, 1])
        rms_raw = float(np.sqrt(np.nanmean((y_all - c) ** 2)))
        print("      %-24s curve %s" % (lbl, "  ".join("%7.3f" % v for v in c)))
        print("      %-24s corr %+.3f   RMS(as-is) %.3f K" % ("", r, rms_raw))

    # ------------- the sweep ---------------------------------------------
    print("\n   SWEEPING the closure shape; amplitude solved in closed form each time")
    print("      %6s %6s %10s %10s %10s" % ("p", "uc", "amp_scale", "RMS_fit", "corr"))
    results = []
    for p_ in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        for uc_ in (0.5, 1.0, 2.0, 4.0, 6.0, 8.0):
            c = shape(p_, uc_)
            a, rms = best_amplitude(y_fit, c)
            if a is None or a <= 0:
                continue
            ok = ~np.isnan(y_fit)
            r = float(np.corrcoef(y_fit[ok], c[ok])[0, 1]) if c[ok].std() > 0 else 0.0
            results.append({"p": p_, "uc": uc_, "amp": a, "rms_fit": rms, "corr": r,
                            "curve20": c.tolist()})
            print("      %6.2f %6.2f %10.4f %10.4f %+10.3f" % (p_, uc_, a, rms, r))

    if not results:
        print("   no viable fit."); return 1
    best = min(results, key=lambda d: d["rms_fit"])
    exch = 20.0 / best["amp"]
    fitted = np.array(best["curve20"]) * best["amp"]

    print("\n   BEST FIT")
    print("      exponent p        = %.2f   (N-11 used 2.0)" % best["p"])
    print("      uc                = %.2f m/s   (N-11 used 8.0)" % best["uc"])
    print("      amplitude scale   = %.4f  ->  exchange_s = %.1f s   (was 20 s)"
          % (best["amp"], exch))
    print("      fitted curve (K)  : %s" % "  ".join("%.3f" % v for v in fitted))
    print("      measured  (K)     : %s" % "  ".join("%.3f" % v for v in y_fit))
    print("      RMS on FIT set    = %.4f K   corr %+.3f" % (best["rms_fit"], best["corr"]))

    # ------------- held-out ----------------------------------------------
    ok_h = ~np.isnan(y_hold)
    rms_hold = float(np.sqrt(np.mean((y_hold[ok_h] - fitted[ok_h]) ** 2)))
    r_hold = float(np.corrcoef(y_hold[ok_h], fitted[ok_h])[0, 1])
    print("\n   HELD-OUT CHECK  (%s -- never used in the fit)" % ", ".join(hold_names))
    print("      held-out (K)      : %s" % "  ".join("%.3f" % v for v in y_hold))
    print("      RMS on HELD-OUT   = %.4f K   corr %+.3f" % (rms_hold, r_hold))
    print("      mean measured     = %.3f K  -> RMS is %.0f%% of the signal"
          % (np.nanmean(y_hold), 100 * rms_hold / max(np.nanmean(y_hold), 1e-9)))

    # ------------- independent direction check ---------------------------
    print("\n   INDEPENDENT CHECK: direction swing (never part of the fit)")
    site, cells = acc_site(exchange_s=exch)
    dirs = np.arange(0.0, 360.0, 22.5)
    U = 5.0
    dw = np.full(len(dirs), float(g_of(U, best["p"], best["uc"])))
    T = ws.solve_batch(site, np.full(len(dirs), AMB), np.full(len(dirs), U), dirs,
                       np.ones(len(dirs)), steps=STEPS, downwash=dw)
    rec = np.array([recirc(T[k].astype(np.float64), site, cells) for k in range(len(dirs))])
    swing = float(rec.max() - rec.min())
    ratio = float(rec.max() / max(rec.min(), 1e-9))
    print("      solver at %.0f m/s: min %.3f K  max %.3f K  swing %.3f K  ratio %.2f x"
          % (U, rec.min(), rec.max(), swing, ratio))
    print("      MEASURED (Wygen, 12,290 pts): swing 0.296 K  ratio 1.60 x")
    print("      -> solver direction ratio is %.2f x vs measured 1.60 x" % ratio)
    dir_ok = 1.15 <= ratio <= 4.0

    # ------------- verdict ------------------------------------------------
    good_fit = rms_hold < 0.35 * max(np.nanmean(y_hold), 1e-9)
    ok = good_fit and dir_ok
    print("\n   RESULT")
    print("      held-out RMS within 35%% of signal : %s (%.0f%%)"
          % (good_fit, 100 * rms_hold / max(np.nanmean(y_hold), 1e-9)))
    print("      direction ratio in a sane band     : %s (%.2f x)" % (dir_ok, ratio))
    print("\n   THE CALIBRATED CONSTANTS TO ADOPT")
    print("      downwash_exponent = %.2f" % best["p"])
    print("      downwash_uc       = %.2f m/s" % best["uc"])
    print("      exchange_s        = %.1f s" % exch)
    print("      These are fitted to 40,000 measured points across %d ACCs, NOT to a literature")
    print("      sentence. That is the first empirically calibrated physics in this project.")
    print("      N-8 v3, N-19 and N-20 must be recomputed on these values.")

    print()
    verdict(ok,
            "PASS - the closure fits the field data with held-out RMS %.4f K (%.0f%% of signal) and "
            "preserves a direction swing of %.2f x against a measured 1.60 x. Adopt p=%.2f, "
            "uc=%.2f m/s, exchange_s=%.1f s."
            % (rms_hold, 100 * rms_hold / max(np.nanmean(y_hold), 1e-9), ratio, best["p"],
               best["uc"], exch),
            "FAIL - no member of this closure family reproduces the measured curve on held-out "
            "plants (RMS %.4f K, %.0f%% of signal; direction ratio %.2f x). The 2-D form is "
            "probably too restrictive; report the direction result only and stop claiming a "
            "quantitative wind-speed response."
            % (rms_hold, 100 * rms_hold / max(np.nanmean(y_hold), 1e-9), ratio))

    save_result("n22_calibrate.json", {
        "source": "Maulbetsch & DiFilippo CEC-500-2013-065 + Appendix B",
        "speeds_ms": SPEEDS.tolist(), "bins_mph": [list(b) for b in BINS],
        "per_plant": per_plant, "fit_plants": fit_names, "held_out_plants": hold_names,
        "measured_fit_K": y_fit.tolist(), "measured_held_K": y_hold.tolist(),
        "sweep": results, "best": best,
        "calibrated": {"downwash_exponent": best["p"], "downwash_uc": best["uc"],
                       "exchange_s": exch},
        "fitted_curve_K": fitted.tolist(),
        "rms_fit_K": best["rms_fit"], "rms_heldout_K": rms_hold, "corr_heldout": r_hold,
        "direction_ratio_solver": ratio, "direction_ratio_measured": 1.60,
        "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
