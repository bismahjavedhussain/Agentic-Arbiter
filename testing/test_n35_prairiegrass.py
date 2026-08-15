# -*- coding: utf-8 -*-
"""N-35  ---  PRAIRIE GRASS: the first external validation of our dispersion.   FREE.

WHY THIS IS THE MOST IMPORTANT VALIDATION IN THE PROJECT
    Everything we have validated so far is either our own calibration, or power-station condenser
    data we also calibrated against. Nothing has ever been checked against an INDEPENDENT field
    experiment. This is that check.

    Project Prairie Grass (O'Neill, Nebraska, July-August 1956) released sulphur dioxide from a
    near-ground source and measured concentration on arcs at 50, 100, 200, 400 and 800 m downwind.
    Those distances span exactly our range of interest (150-600 m separations). It remains, in the
    literature's words, "the most complete available for the analysis of surface layer dispersion".

    Files pulled directly from harmo.org/jsirwin -- free, no registration:
        PGARCS.txt       340 arc records, 68 experiments, crosswind concentration profiles
        PGrassTTUU.txt   temperature and wind speed at 7 heights per experiment, 20-min averages

WHAT IS AND IS NOT BEING TESTED -- read this before the numbers
    ❌ NOT a test of whether our D matches the Pasquill-Gifford table. That would be CIRCULAR: our D
       is DERIVED from that table (N-30), so agreement at the matching distance is guaranteed by
       construction and proves nothing.

    ✅ A test of the FUNCTIONAL FORM, which is the one thing that cannot be circular. Our solver's
       verified plume law is sigma_y = sqrt(2 D x / u), i.e.

            OURS      sigma_y  proportional to  x^0.5
            PUBLISHED sigma_y  proportional to  x^0.88 to x^0.91   (Pasquill-Gifford)
            MEASURED  sigma_y  proportional to  x^?                <- this test

       If the measured exponent comes out near 0.9, then the published table is confirmed against
       real data AND our square-root shape is confirmed as the outlier -- which is exactly the gap
       flagged in physics-explained.md Part 5 Step 4, but measured instead of argued.

       This also means a single D can only match reality at ONE distance. This test measures how big
       the error is at the others, using field data rather than another formula.

METHOD
    sigma_y per arc   second moment of the concentration profile about its concentration-weighted
                      CIRCULAR mean. The circular part matters: sampler azimuths wrap through
                      360/0 deg, and a naive mean gives physically impossible widths -- 60 m at a
                      50 m arc, which is how this bug was caught.
    quality filter    an arc is rejected if concentration at either END of the sampled span exceeds
                      20 % of the peak, because then the plume is wider than the arc and the second
                      moment is truncated -- it would UNDERSTATE sigma_y and flatter our x^0.5.
    stability         from the measured vertical temperature gradient, 0.25 m to 8 m. Temperature
                      falling with height = lapse = unstable; rising = inversion = stable. Thresholds
                      are ✏️ OURS (+/-1.0 C over that span) and labelled as such; the sign is physics.
    exponent          least squares on log(sigma_y) against log(x), per experiment, needing >= 3
                      surviving arcs so there is a residual left to judge the fit by.

PRE-REGISTERED CONDITIONS, fixed before running
    P1  median measured exponent > 0.70, i.e. clearly above our model's 0.5. Confirms the gap is real
        and measured rather than inferred from another formula.
    P2  median measured exponent within [0.70, 1.10], i.e. consistent with the published 0.88-0.91.
        If it landed far outside, the published table itself would be in question.
    P3  at least 20 experiments survive the quality filter, so the median means something.
"""
import sys, os, math, re, statistics
from collections import defaultdict
import numpy as np

from common import banner, save_result, verdict, SCRATCH

ARCS = os.path.join(SCRATCH, "PGARCS.txt")
MET = os.path.join(SCRATCH, "PGrassTTUU.txt")
EDGE_FRAC = 0.20          # reject an arc if either end exceeds this fraction of the peak
MIN_ARCS = 3              # per experiment, to fit an exponent with a residual
OUR_EXPONENT = 0.5        # what our solver does, verified exactly in N-29
P1_MIN = 0.70
P2_RANGE = (0.70, 1.10)
P3_MIN_EXPERIMENTS = 20


def parse_arcs(path):
    """Records of (exp, date, time, distance, [(azimuth, concentration)])."""
    out, cur = [], None
    for line in open(path, encoding="latin-1").read().splitlines()[1:]:
        if "," in line and "'" in line:
            if cur and cur["rows"]:
                out.append(cur)
            p = [x.strip().strip("'").strip() for x in line.split(",")]
            try:
                cur = {"exp": int(p[0]), "date": p[2], "time": p[3], "dist": float(p[4]),
                       "rows": [], "meta": None}
            except Exception:
                cur = None
            continue
        if cur is not None and cur["meta"] is None and "," in line:
            cur["meta"] = [x.strip() for x in line.split(",")]
            continue
        if cur is not None and line.strip():
            f = line.split()
            if len(f) == 4:
                try:
                    az, _s, _d, c = (float(x) for x in f)
                    cur["rows"].append((az, c))
                except Exception:
                    pass
    if cur and cur["rows"]:
        out.append(cur)
    return out


def parse_met(path):
    """{exp: [(height, temp, wind)]} with missing values dropped."""
    out, cur = {}, None
    for line in open(path, encoding="latin-1").read().splitlines():
        m = re.match(r"\s*Exp\s+(\d+)\s*$", line)
        if m:
            cur = int(m.group(1)); out[cur] = []; continue
        if cur is None:
            continue
        f = line.split()
        if len(f) == 3:
            try:
                h, t, u = (float(x) for x in f)
            except Exception:
                continue
            if t > -900 and u > -900:
                out[cur].append((h, t, u))
    return out


def sigma_y_from_arc(rows, dist):
    """Circular-mean second moment -> sigma_y in metres. Returns (sigma, quality_ok, edge_frac)."""
    az = np.array([r[0] for r in rows], dtype=float)
    c = np.clip(np.array([r[1] for r in rows], dtype=float), 0.0, None)
    if c.sum() <= 0 or len(c) < 6:
        return None, False, None
    th = np.radians(az)
    mean_az = math.degrees(math.atan2((c * np.sin(th)).sum(), (c * np.cos(th)).sum())) % 360.0
    d = (az - mean_az + 180.0) % 360.0 - 180.0        # signed offset, degrees
    y = np.radians(d) * dist                          # crosswind distance, metres
    order = np.argsort(y)
    y, c = y[order], c[order]
    peak = c.max()
    edge = max(c[0], c[-1]) / peak if peak > 0 else 1.0
    m = (c * y).sum() / c.sum()
    var = (c * (y - m) ** 2).sum() / c.sum()
    if var <= 0:
        return None, False, edge
    return math.sqrt(var), (edge <= EDGE_FRAC), edge


def stability_from_met(prof):
    """Sign and size of the 0.25 m -> 8 m temperature change. Thresholds OURS; the sign is physics."""
    if not prof:
        return None, None, None
    hs = {h: (t, u) for h, t, u in prof}
    lo = min(hs); hi = max(hs)
    if hi <= lo:
        return None, None, None
    dT = hs[hi][0] - hs[lo][0]
    u_ref = None
    for h in (2.0, 1.0, 4.0, 0.5, 8.0, 0.25):
        if h in hs:
            u_ref = hs[h][1]; break
    if dT < -1.0:
        cls = "unstable (lapse)"
    elif dT > 1.0:
        cls = "stable (inversion)"
    else:
        cls = "near-neutral"
    return cls, dT, u_ref


def main():
    banner("N-35  Prairie Grass 1956: does our plume-width SHAPE match real measurements?  [FREE]")
    for p in (ARCS, MET):
        if not os.path.exists(p):
            print("   missing %s" % p); return 2

    recs = parse_arcs(ARCS)
    met = parse_met(MET)
    byexp = defaultdict(list)
    for r in recs:
        byexp[r["exp"]].append(r)
    print("   %d arc records, %d experiments, distances %s"
          % (len(recs), len(byexp), sorted(set(r["dist"] for r in recs))))
    print("   met profiles for %d experiments, heights %s"
          % (len(met), sorted(set(h for v in met.values() for h, _, _ in v))))
    print("   OUR model: sigma_y proportional to x^%.1f   PUBLISHED: x^0.88 to x^0.91" % OUR_EXPONENT)
    print("   quality filter: reject an arc whose END concentration exceeds %.0f %% of its peak"
          % (100 * EDGE_FRAC))

    fits, rejected, per_arc = [], 0, []
    for exp in sorted(byexp):
        pts = []
        for r in sorted(byexp[exp], key=lambda r: r["dist"]):
            sy, ok, edge = sigma_y_from_arc(r["rows"], r["dist"])
            per_arc.append({"exp": exp, "dist": r["dist"], "sigma_y": sy,
                            "ok": bool(ok), "edge_frac": edge})
            if sy is None or not ok:
                rejected += 1
                continue
            pts.append((r["dist"], sy))
        if len(pts) < MIN_ARCS:
            continue
        xs = np.log([p[0] for p in pts]); ys = np.log([p[1] for p in pts])
        A = np.vstack([xs, np.ones_like(xs)]).T
        b, loga = np.linalg.lstsq(A, ys, rcond=None)[0]
        pred = A.dot([b, loga])
        r2 = 1.0 - ((ys - pred) ** 2).sum() / max(((ys - ys.mean()) ** 2).sum(), 1e-12)
        cls, dT, u_ref = stability_from_met(met.get(exp, []))
        fits.append({"exp": exp, "n_arcs": len(pts), "exponent": float(b),
                     "coef": float(math.exp(loga)), "r2": float(r2),
                     "stability": cls, "dT_0p25_to_8m": dT, "u_ref_ms": u_ref,
                     "date": byexp[exp][0]["date"], "time": byexp[exp][0]["time"],
                     "arcs": [(p[0], p[1]) for p in pts]})

    print("\n   %d arcs rejected by the quality filter (plume wider than the sampled span)" % rejected)
    print("   %d experiments have >= %d usable arcs and were fitted" % (len(fits), MIN_ARCS))

    if not fits:
        print("\n   nothing fitted -- cannot conclude.")
        save_result("n35_prairiegrass.json", {"n_fits": 0, "pass": None})
        return 2

    exps = np.array([f["exponent"] for f in fits])
    print("\n   MEASURED EXPONENT, per experiment (a sample)")
    print("      %5s %6s %10s %22s %9s %8s %7s"
          % ("exp", "arcs", "exponent", "stability", "dT C", "u m/s", "R2"))
    for f in fits[:14]:
        print("      %5d %6d %10.3f %22s %9s %8s %7.3f"
              % (f["exp"], f["n_arcs"], f["exponent"], f["stability"] or "-",
                 "%+.2f" % f["dT_0p25_to_8m"] if f["dT_0p25_to_8m"] is not None else "-",
                 "%.2f" % f["u_ref_ms"] if f["u_ref_ms"] else "-", f["r2"]))
    if len(fits) > 14:
        print("      ... %d more" % (len(fits) - 14))

    med = float(np.median(exps))
    print("\n   DISTRIBUTION OF THE MEASURED EXPONENT over %d experiments" % len(fits))
    print("      min %.3f   p25 %.3f   MEDIAN %.3f   p75 %.3f   max %.3f"
          % (exps.min(), np.percentile(exps, 25), med, np.percentile(exps, 75), exps.max()))
    print("      mean %.3f, sd %.3f, median R^2 %.3f"
          % (exps.mean(), exps.std(ddof=1), float(np.median([f["r2"] for f in fits]))))
    print("      our model               : %.3f" % OUR_EXPONENT)
    print("      published Pasquill-Gifford: 0.88 to 0.91")

    by_cls = defaultdict(list)
    for f in fits:
        if f["stability"]:
            by_cls[f["stability"]].append(f["exponent"])
    print("\n   BY MEASURED STABILITY (from the vertical temperature gradient)")
    for cls in sorted(by_cls, key=lambda k: -len(by_cls[k])):
        v = np.array(by_cls[cls])
        print("      %-22s n=%3d   median exponent %.3f   (range %.3f to %.3f)"
              % (cls, len(v), float(np.median(v)), v.min(), v.max()))

    # ---- P3: how wrong is our x^0.5 when matched at one distance?
    MATCH = 200.0
    print("\n   WHAT OUR SQUARE-ROOT SHAPE COSTS, matched to the measurement at %.0f m" % MATCH)
    print("      %10s %14s %14s %10s" % ("distance", "measured x^%.2f" % med, "ours x^0.5", "error"))
    err = {}
    for x in (50.0, 100.0, 200.0, 400.0, 800.0):
        meas = (x / MATCH) ** med
        ours = (x / MATCH) ** OUR_EXPONENT
        err[x] = 100.0 * (ours - meas) / meas
        print("      %10.0f %14.3f %14.3f %9.0f %%" % (x, meas, ours, err[x]))
    print("      (ratios relative to the match point, so both are 1.000 at %.0f m)" % MATCH)

    p1 = med > P1_MIN
    p2 = P2_RANGE[0] <= med <= P2_RANGE[1]
    p3 = len(fits) >= P3_MIN_EXPERIMENTS
    ok = p1 and p2 and p3
    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      P1 median exponent > %.2f (above our 0.5) : %s  (%.3f)" % (P1_MIN, p1, med))
    print("      P2 median within [%.2f, %.2f]             : %s  (%.3f)"
          % (P2_RANGE[0], P2_RANGE[1], p2, med))
    print("      P3 >= %d experiments fitted               : %s  (%d)"
          % (P3_MIN_EXPERIMENTS, p3, len(fits)))
    print()
    verdict(ok,
            "PASS - measured on %d independent field experiments from 1956, the plume-width exponent "
            "is %.3f. That CONFIRMS the published Pasquill-Gifford value of 0.88-0.91 against real "
            "data, and it CONFIRMS that our square-root shape is the outlier. Matched at %.0f m, our "
            "model is %+.0f %% at 50 m and %+.0f %% at 800 m. This is the project's first validation "
            "against an experiment that is neither our own calibration nor a power station -- and the "
            "thing it validates is a limitation we had already declared."
            % (len(fits), med, MATCH, err[50.0], err[800.0]),
            "FAIL - P1 %s, P2 %s, P3 %s (median exponent %.3f from %d experiments). Either the "
            "measurement disagrees with the published table, or the extraction is wrong. Diagnose "
            "which before claiming anything." % (p1, p2, p3, med, len(fits)))

    save_result("n35_prairiegrass.json", {
        "source": "Project Prairie Grass 1956, O'Neill Nebraska; PGARCS.txt and PGrassTTUU.txt from "
                  "harmo.org/jsirwin, free, no registration",
        "what_is_tested": "the FUNCTIONAL FORM of plume growth, which cannot be circular; NOT the "
                          "value of D, which is derived from the same published table",
        "our_exponent": OUR_EXPONENT, "published_exponent": [0.88, 0.91],
        "edge_frac_filter": EDGE_FRAC, "n_arc_records": len(recs),
        "n_arcs_rejected": rejected, "n_experiments_fitted": len(fits),
        "exponent_median": med, "exponent_mean": float(exps.mean()),
        "exponent_sd": float(exps.std(ddof=1)),
        "exponent_quartiles": [float(np.percentile(exps, 25)), float(np.percentile(exps, 75))],
        "exponent_range": [float(exps.min()), float(exps.max())],
        "median_r2": float(np.median([f["r2"] for f in fits])),
        "by_stability": {k: {"n": len(v), "median": float(np.median(v))} for k, v in by_cls.items()},
        "match_distance_m": MATCH, "our_error_pct": {str(int(k)): v for k, v in err.items()},
        "fits": fits, "per_arc": per_arc,
        "p1_above_ours": p1, "p2_matches_published": p2, "p3_enough": p3, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
