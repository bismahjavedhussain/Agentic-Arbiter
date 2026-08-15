# -*- coding: utf-8 -*-
"""N-23  ---  does the bound WIDEN by itself when the forecast straddles a geometric edge? FREE, GPU.

THE QUESTION
    Wind direction behaves almost like a switch: if the exhaust plume points at the intake you get a
    jump, and if it does not you get nothing. That is why the field measurements show direction
    mattering enormously in some periods and not at all in others.

    So: does the agent notice by itself when direction matters, and does that reach the margin?

THREE CASES, and the third is the one worth having

    1. SAFE     forecast direction well away from the plume. Every ensemble member lands in the cold
                zone, the spread is tiny, the margin is tiny. -> relax with confidence.
    2. HOT      forecast direction squarely on the plume. Every member lands in the hot zone, the
                spread is again tight but the LEVEL is high. -> do not relax, and say why.
    3. KNIFE EDGE  forecast direction near the boundary of the plume sector. The +/-15 deg forecast
                uncertainty now straddles the edge: some members are cold, some are hot. The
                distribution should go WIDE and BIMODAL, and the 90th percentile should sit high.

    Case 3 is the day where a point forecast is most dangerous and where an honest bound earns its
    keep -- the answer is not "hot" or "cold", it is "we cannot tell which side of the edge we are
    on". If the ensemble does NOT widen there, the pipeline is not propagating direction uncertainty
    properly and that is a defect worth knowing about.

WHAT IS MEASURED
    Forecast direction swept in 5 deg steps. At each, a 60-member ensemble with the operational
    uncertainties (direction +/-15 deg, speed +/-1 m/s, load 65-100 %). Recorded: mean, sd, p90, and
    a bimodality score (the fraction of members in neither the cold nor the hot cluster is low when
    the distribution is genuinely split).

    Pass requires the spread at the edge to be materially larger than in either interior, i.e. the
    agent discovers the edge without being told where it is.
"""
import sys
import numpy as np

from common import banner, save_result, verdict
from solver import Site, downwash_fraction, CALIBRATED
import warp_solver as ws

DX, AMB, STEPS = 10.0, 30.0, 800
N_MEMBERS = 60
DIR_SD = 15.0            # forecast direction uncertainty [S]
SPD, SPD_SD = 6.0, 1.0
LOAD_LO, LOAD_HI = 0.65, 1.0
UC = CALIBRATED["downwash_uc"]
EXPO = CALIBRATED["downwash_exponent"]
EXCH = CALIBRATED["exchange_s"]


def site_with_intake():
    """Our hall, condensers on its east face, neighbour 300 m east, score the neighbour's intake."""
    s = Site(2000.0, DX)
    s.add_building(cx=700, cy=1000, w=200, h=120)
    s.add_condensers(cx=830, cy=1000, w=60, h=120, discharge_k=11.0, exchange_s=EXCH)
    s.add_building(cx=1200, cy=1000, w=200, h=120)
    return s, (1090.0, 1000.0)


def rise_at(T, site, ix, iy, r_m=30.0):
    r = max(1, int(r_m / site.dx))
    i, j = int(iy / site.dx), int(ix / site.dx)
    return float(np.mean(T[max(0, i - r):min(site.n, i + r + 1),
                           max(0, j - r):min(site.n, j + r + 1)])) - AMB


def ensemble_at(theta0, rng):
    site, intake = site_with_intake()
    wf = theta0 + rng.normal(0, DIR_SD, N_MEMBERS)
    spd = np.clip(SPD + rng.normal(0, SPD_SD, N_MEMBERS), 0.3, 14.0)
    scl = rng.uniform(LOAD_LO, LOAD_HI, N_MEMBERS)
    dw = np.array([downwash_fraction(v, UC, EXPO) for v in spd])
    T = ws.solve_batch(site, np.full(N_MEMBERS, AMB), spd, wf, scl, steps=STEPS, downwash=dw)
    return np.array([rise_at(T[k].astype(np.float64), site, *intake) for k in range(N_MEMBERS)])


def main():
    banner("N-23  Does the bound widen by itself at a geometric knife edge?   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable."); return 2
    print("   calibrated solver: exponent %.2f, uc %.1f m/s, exchange_s %.1f s (N-22)"
          % (EXPO, UC, EXCH))
    print("   forecast uncertainty: direction +/-%.0f deg, speed +/-%.1f m/s, load %.0f-%.0f %%"
          % (DIR_SD, SPD_SD, 100 * LOAD_LO, 100 * LOAD_HI))
    print("   the agent is never told where the plume sector is -- it has to discover it")

    rng = np.random.default_rng(23)
    dirs = np.arange(180.0, 360.1, 5.0)
    rows = []
    print("\n   %8s %9s %9s %9s %9s %8s" % ("wind from", "mean", "sd", "p90", "max", "frac>0.2"))
    for th in dirs:
        r = ensemble_at(float(th), rng)
        rows.append({"dir": float(th), "mean": float(r.mean()), "sd": float(r.std(ddof=1)),
                     "p90": float(np.percentile(r, 90)), "max": float(r.max()),
                     "frac_hot": float(np.mean(r > 0.2))})
        print("   %8.0f %9.4f %9.4f %9.4f %9.4f %8.2f"
              % (th, rows[-1]["mean"], rows[-1]["sd"], rows[-1]["p90"], rows[-1]["max"],
                 rows[-1]["frac_hot"]))

    sd = np.array([r["sd"] for r in rows])
    mean = np.array([r["mean"] for r in rows])
    fh = np.array([r["frac_hot"] for r in rows])
    p90 = np.array([r["p90"] for r in rows])

    # the knife edge is where members are genuinely split: frac_hot nearest 0.5
    edge_i = int(np.argmin(np.abs(fh - 0.5)))
    sd_peak_i = int(np.argmax(sd))
    # interiors: clearly cold (frac_hot < 0.05) and clearly hot (frac_hot > 0.95)
    cold = [i for i in range(len(rows)) if fh[i] < 0.05]
    hot = [i for i in range(len(rows)) if fh[i] > 0.95]

    print("\n   RESULT")
    print("      widest spread at wind from %.0f deg, sd %.4f C" % (dirs[sd_peak_i], sd[sd_peak_i]))
    print("      most SPLIT ensemble at %.0f deg (%.0f %% of members hot)"
          % (dirs[edge_i], 100 * fh[edge_i]))
    if cold:
        print("      clearly-cold directions  : %s   mean sd %.4f C"
              % ("%.0f-%.0f deg" % (dirs[cold[0]], dirs[cold[-1]]), sd[cold].mean()))
    if hot:
        print("      clearly-hot directions   : %s   mean sd %.4f C"
              % ("%.0f-%.0f deg" % (dirs[hot[0]], dirs[hot[-1]]), sd[hot].mean()))

    ratios = []
    if cold:
        ratios.append(sd[sd_peak_i] / max(sd[cold].mean(), 1e-6))
        print("      spread at the edge is %.1f x the clearly-cold spread"
              % (sd[sd_peak_i] / max(sd[cold].mean(), 1e-6)))
    if hot:
        ratios.append(sd[sd_peak_i] / max(sd[hot].mean(), 1e-6))
        print("      spread at the edge is %.1f x the clearly-hot spread"
              % (sd[sd_peak_i] / max(sd[hot].mean(), 1e-6)))

    print("\n   WHAT REACHES THE DECISION")
    print("      The bound the agent acts on is the p90, not the mean. At the edge:")
    print("        mean %.4f C  but  p90 %.4f C   -> the bound is %.1f x the mean"
          % (mean[edge_i], p90[edge_i], p90[edge_i] / max(mean[edge_i], 1e-6)))
    if cold:
        print("      deep in the cold sector: mean %.4f, p90 %.4f -> almost nothing to carry"
              % (mean[cold].mean(), p90[cold].mean()))
    print("      So the SAME code relaxes on safe days and refuses to relax at the edge, purely")
    print("      because the ensemble straddles the geometry. Nobody wrote a rule for that.")

    ok = bool(ratios) and min(ratios) > 1.5
    print()
    verdict(ok,
            "PASS - the agent discovers the knife edge on its own. Spread at the boundary is %.1f x "
            "the interior spread, so the bound widens exactly on the days when a point forecast "
            "cannot tell which side of the geometry you are on. That behaviour is emergent from "
            "propagating direction uncertainty through the physics, not a coded rule."
            % (min(ratios) if ratios else 0.0),
            "FAIL - the spread does not widen at the boundary (ratio %.1f). Direction uncertainty is "
            "not reaching the bound, which means the ensemble is not doing the job it exists for. "
            "Investigate before claiming the margin is direction-aware."
            % (min(ratios) if ratios else 0.0))

    save_result("n23_knifeedge.json", {
        "calibrated": {"exponent": EXPO, "uc": UC, "exchange_s": EXCH},
        "dir_sd_deg": DIR_SD, "n_members": N_MEMBERS, "rows": rows,
        "edge_dir": float(dirs[edge_i]), "sd_peak_dir": float(dirs[sd_peak_i]),
        "sd_at_peak": float(sd[sd_peak_i]),
        "sd_cold_mean": float(sd[cold].mean()) if cold else None,
        "sd_hot_mean": float(sd[hot].mean()) if hot else None,
        "ratios": ratios, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
