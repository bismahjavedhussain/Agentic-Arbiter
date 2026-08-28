# -*- coding: utf-8 -*-
"""N-21  ---  VALIDATION against real ACC field measurements.   FREE, GPU.

THE FIRST REAL-WORLD VALIDATION IN THIS PROJECT
    Source: Maulbetsch, J.S. & DiFilippo, M.N., "Effect of Wind on the Performance of Air-Cooled
    Condensers", California Energy Commission CEC-500-2013-065 (2010) and its Appendix B
    CEC-500-2013-065-APB (2008). Field campaigns at six operating power-plant ACCs, 1-minute
    resolution, measuring cell inlet air temperature alongside wind speed and direction.
    Public domain. ~40,000 (wind, recirculation) pairs digitised from the report's vector figures.

WHAT IS BEING TESTED, AND IT CUTS BOTH WAYS
    N-11 changed the solver's wind-speed response on the strength of ACC literature saying hot
    recirculation RISES with wind speed and peaks near 9 m/s. Before that change the solver had
    recirculation FALLING with wind speed. The field data decides which was right.

    If the measurements fall with wind speed, N-11 made the solver worse and must be reverted.
    That is a real possibility and the test is built to detect it, not to avoid it.

THE METRIC MUST MATCH OR THE COMPARISON IS MEANINGLESS
    The reports do not measure rise above far-field ambient. They substitute the MINIMUM cell inlet
    temperature for ambient, so their "recirculation" is:

        recirculation = mean(cell inlet T) - min(cell inlet T)

    So the solver must produce the same quantity: an ACC deck of cells, the air temperature arriving
    at each cell, mean minus min across the deck. A rise-above-ambient comparison would be invalid.
    Under wind, upwind cells ingest near-ambient air while downwind cells ingest air already warmed
    by the deck -- which is exactly the spatial gradient the field metric captures.

UNITS: report is mph and degF. Converted to m/s (x0.44704) and K (x5/9).
"""
import os, sys, glob
import numpy as np

from common import banner, save_result, verdict, field_path, SCRATCH
from solver import Site, downwash_fraction
import warp_solver as ws

DX = 10.0
AMB = 30.0
STEPS = 800
MPH = 0.44704
F2K = 5.0 / 9.0

# Digitised field figures. Axis boxes are used to clip legend / adjacent-chart leakage, which the
# extraction agents explicitly flagged for Front Range and Apex.
FIELD = [
    ("El Dorado 2007", "VERIFIED_fig4-17_recirc_vs_windspeed.csv", 36.0, 6.0),
    ("Bighorn", "fig6-14_bighorn.csv", 36.0, 20.0),
    ("El Dorado 2005", "fig6-32_eldorado.csv", 36.0, 20.0),
    ("Wygen", "fig6-89_wygen_vs_windspeed.csv", 36.0, 20.0),
    ("Front Range", "fig6-75_frontrange_ws.csv", 36.0, 20.0),
    ("Apex", "fig6-52_apex_ws.csv", 36.0, 10.0),
]
BINS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30)]


def load_field(fn, xmax, ymax):
    # field_path() rather than a bare SCRATCH join: SCRATCH names a dead session temp
    # directory, so this looked in one place that does not exist and reported the dataset
    # missing. The resolver also tries validation-data/, where the CSVs actually are.
    p = field_path(fn)
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
            if 0.0 <= x <= xmax and 0.0 <= y <= ymax:      # clip to the axis box
                rows.append((x, y))
    return np.array(rows) if rows else None


def bin_field(arr):
    out = []
    for lo, hi in BINS:
        m = (arr[:, 0] >= lo) & (arr[:, 0] < hi)
        out.append({"lo_mph": lo, "hi_mph": hi, "centre_ms": (lo + hi) / 2.0 * MPH,
                    "n": int(m.sum()),
                    "mean_F": float(arr[m, 1].mean()) if m.sum() >= 20 else None,
                    "mean_K": float(arr[m, 1].mean() * F2K) if m.sum() >= 20 else None})
    return out


# ------------------------------------------------------------------ ACC deck in the solver
def acc_site(n_cells_x=8, n_cells_y=4, cell_m=30.0, discharge_k=11.0, exchange_s=20.0):
    """A single ACC deck: a rectangular block of condenser cells, as the field sites are.

    Returns the site plus the (x, y) centre of every cell so inlet temperature can be read per
    cell, which is what the report tabulates.
    """
    s = Site(2000.0, DX)
    w = n_cells_x * cell_m
    h = n_cells_y * cell_m
    cx, cy = 1000.0, 1000.0
    x0, y0 = cx - w / 2.0, cy - h / 2.0
    s.add_condensers(cx=cx, cy=cy, w=w, h=h, discharge_k=discharge_k, exchange_s=exchange_s)
    cells = [(x0 + (i + 0.5) * cell_m, y0 + (j + 0.5) * cell_m)
             for i in range(n_cells_x) for j in range(n_cells_y)]
    return s, cells


def deck_recirculation(T, site, cells):
    """mean(cell inlet T) - min(cell inlet T), the report's definition."""
    vals = []
    for (x, y) in cells:
        i, j = int(y / site.dx), int(x / site.dx)
        i = min(max(i, 0), site.n - 1); j = min(max(j, 0), site.n - 1)
        vals.append(T[i, j])
    v = np.array(vals, dtype=np.float64)
    return float(v.mean() - v.min())


def solver_curve(speeds_ms, uc, seed=3, n_dir=12):
    """Solver recirculation vs wind speed, averaged over wind direction as the field data is."""
    site, cells = acc_site()
    rng = np.random.default_rng(seed)
    dirs = np.linspace(0.0, 360.0, n_dir, endpoint=False)
    out = []
    for U in speeds_ms:
        spd = np.full(len(dirs), U)
        dw = np.array([downwash_fraction(U, uc)] * len(dirs))
        T = ws.solve_batch(site, np.full(len(dirs), AMB), spd, dirs,
                           np.ones(len(dirs)), steps=STEPS, downwash=dw)
        rec = [deck_recirculation(T[k].astype(np.float64), site, cells) for k in range(len(dirs))]
        out.append(float(np.mean(rec)))
    return np.array(out)


def shape_score(meas, pred):
    """Pearson correlation of the two curves, plus where each peaks."""
    m = np.array([x for x in meas if x is not None], dtype=np.float64)
    if len(m) < 3:
        return None, None, None
    p = np.array(pred[:len(m)], dtype=np.float64)
    r = float(np.corrcoef(m, p)[0, 1]) if m.std() > 0 and p.std() > 0 else 0.0
    return r, int(np.argmax(m)), int(np.argmax(p))


def main():
    banner("N-21  VALIDATION against Maulbetsch & DiFilippo ACC field measurements   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable."); return 2

    # ---------------- 1. the measurements ---------------------------------
    print("\n   1. MEASURED recirculation = mean(cell inlet) - min(cell inlet), by wind-speed bin")
    print("      source: CEC-500-2013-065 and Appendix B, 1-minute field data, six ACCs")
    print("      %-16s %7s   %s" % ("plant", "n", "  ".join("%2d-%2d" % b for b in BINS)))
    plants, all_binned = [], []
    for name, fn, xmax, ymax in FIELD:
        arr = load_field(fn, xmax, ymax)
        if arr is None or len(arr) < 200:
            print("      %-16s  (not available / too few rows)" % name); continue
        b = bin_field(arr)
        plants.append({"plant": name, "n": len(arr), "bins": b})
        all_binned.append([x["mean_F"] for x in b])
        cells = "  ".join(("%5.2f" % x["mean_F"]) if x["mean_F"] is not None else "    -"
                          for x in b)
        print("      %-16s %7d   %s" % (name, len(arr), cells))
    if not plants:
        print("      no field data found in the scratchpad -- cannot validate."); return 2

    # pooled measured curve, in K
    pooled = []
    for k in range(len(BINS)):
        vals = [row[k] for row in all_binned if row[k] is not None]
        pooled.append(float(np.mean(vals) * F2K) if vals else None)
    print("\n      POOLED across %d plants (K): %s"
          % (len(plants), "  ".join(("%.3f" % v) if v is not None else "  -" for v in pooled)))

    idx_ok = [k for k, v in enumerate(pooled) if v is not None]
    peak_meas = max(idx_ok, key=lambda k: pooled[k])
    print("      measured peak is in the %d-%d mph bin (%.1f-%.1f m/s)"
          % (BINS[peak_meas][0], BINS[peak_meas][1],
             BINS[peak_meas][0] * MPH, BINS[peak_meas][1] * MPH))
    trend = pooled[idx_ok[-1]] - pooled[idx_ok[0]]
    print("      measured trend from lowest to highest bin: %+.3f K -> recirculation %s with wind"
          % (trend, "RISES" if trend > 0.05 else ("FALLS" if trend < -0.05 else "is flat")))

    # ---------------- 2. the solver, both ways ----------------------------
    speeds = np.array([(lo + hi) / 2.0 * MPH for lo, hi in BINS])
    print("\n   2. SOLVER, same metric, same wind-speed bins")
    print("      evaluating at %s m/s" % np.round(speeds, 2).tolist())
    with_fix = solver_curve(speeds, uc=8.0)
    without = solver_curve(speeds, uc=None)
    print("      %-26s %s" % ("N-11 fix ON  (uc=8)",
                              "  ".join("%5.3f" % v for v in with_fix)))
    print("      %-26s %s" % ("N-11 fix OFF (original)",
                              "  ".join("%5.3f" % v for v in without)))

    r_on, pk_m, pk_on = shape_score(pooled, with_fix)
    r_off, _, pk_off = shape_score(pooled, without)

    print("\n   3. WHICH MATCHES THE MEASUREMENTS?")
    print("      %-26s %10s %16s" % ("configuration", "corr r", "peak bin"))
    print("      %-26s %10s %16s" % ("MEASURED", "-", "%d-%d mph" % BINS[pk_m]))
    print("      %-26s %10.3f %16s" % ("N-11 fix ON", r_on, "%d-%d mph" % BINS[pk_on]))
    print("      %-26s %10.3f %16s" % ("N-11 fix OFF", r_off, "%d-%d mph" % BINS[pk_off]))

    better = "ON" if r_on > r_off else "OFF"
    print("\n      -> the configuration matching the field data is: N-11 fix %s" % better)

    # ---------------- 4. verdict ------------------------------------------
    print("\n   4. WHAT THIS MEANS")
    if better == "OFF":
        print("      *** N-11 MADE THE SOLVER WORSE. The published statement that hot")
        print("      recirculation rises with wind speed to a ~9 m/s peak is NOT what these six")
        print("      instrumented ACCs measured. The original falling response was closer to")
        print("      reality on this metric. N-11 must be reverted or re-scoped, and every number")
        print("      computed on the calibrated solver (N-8 v3, N-19, N-20) needs recomputing.")
    else:
        print("      N-11's direction is supported by the field data on this metric.")
    print("\n      HONEST LIMITS OF THIS COMPARISON, whichever way it went:")
    print("      - these are POWER-PLANT ACCs, not data centres; deck sizes and cell counts differ")
    print("      - the field metric uses min-cell as an ambient surrogate, so it measures the")
    print("        SPATIAL GRADIENT across a deck, not rise above true far-field ambient. A model")
    print("        can be right about one and wrong about the other")
    print("      - the y values come from digitised vector figures, not tabulated data")
    print("      - the solver deck geometry is generic, not any of the six real sites")

    # ---------------- 5. DIRECTION: the claim that actually matters --------
    print("\n   5. DOES WIND DIRECTION MATTER IN THE FIELD DATA?")
    print("      (this is the project's core claim, and it is separate from the speed response)")
    dirp = field_path("fig6-90_wygen_vs_winddir.csv")
    dir_res = None
    if os.path.exists(dirp):
        rows = []
        with open(dirp, encoding="utf-8-sig") as f:
            next(f, None)
            for ln in f:
                try:
                    a, b = ln.split(",")[:2]
                    x, y = float(a), float(b)
                except Exception:
                    continue
                if 0.0 <= x <= 360.0 and 0.0 <= y <= 20.0:
                    rows.append((x, y))
        d = np.array(rows)
        print("      Wygen, %d clipped points, mean recirculation by 45 deg sector:" % len(d))
        secs = []
        for lo in range(0, 360, 45):
            m = (d[:, 0] >= lo) & (d[:, 0] < lo + 45)
            if m.sum() >= 20:
                secs.append({"lo": lo, "n": int(m.sum()), "mean_F": float(d[m, 1].mean()),
                             "mean_K": float(d[m, 1].mean() * F2K)})
                print("        %3d-%3d deg  n=%5d  %.3f F  (%.3f K)"
                      % (lo, lo + 45, m.sum(), secs[-1]["mean_F"], secs[-1]["mean_K"]))
        if secs:
            mk = [x["mean_K"] for x in secs]
            dir_swing = max(mk) - min(mk)
            dir_ratio = max(mk) / max(min(mk), 1e-9)
            spd_swing = max(v for v in pooled if v is not None) - min(v for v in pooled if v is not None)
            dir_res = {"sectors": secs, "swing_K": dir_swing, "ratio": dir_ratio,
                       "speed_swing_K": spd_swing}
            print("\n      DIRECTION swing %.3f K (ratio %.2f x)" % (dir_swing, dir_ratio))
            print("      SPEED     swing %.3f K" % spd_swing)
            print("      -> in the real measurements, direction matters %.1f x %s than speed"
                  % (dir_swing / max(spd_swing, 1e-9),
                     "MORE" if dir_swing > spd_swing else "LESS"))
    else:
        print("      direction file not found")

    ok = max(r_on, r_off) > 0.5
    print()
    verdict(ok,
            "PASS - the solver reproduces the measured shape with r=%.3f in its better "
            "configuration (N-11 %s). This is the project's first comparison against real-world "
            "measurements." % (max(r_on, r_off), better),
            "FAIL - neither configuration reproduces the measured wind-speed shape (best r=%.3f). "
            "The solver's wind response is not validated and must not be presented as physical."
            % max(r_on, r_off))

    save_result("n21_validate.json", {
        "source": "Maulbetsch & DiFilippo, CEC-500-2013-065 and Appendix B",
        "metric": "mean(cell inlet) - min(cell inlet), matching the report definition",
        "plants": plants, "bins_mph": [list(b) for b in BINS],
        "pooled_measured_K": pooled, "measured_peak_bin": list(BINS[peak_meas]),
        "measured_trend_K": trend,
        "solver_speeds_ms": speeds.tolist(),
        "solver_with_n11": with_fix.tolist(), "solver_without_n11": without.tolist(),
        "corr_with_n11": r_on, "corr_without_n11": r_off,
        "better_configuration": better, "direction": dir_res, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
