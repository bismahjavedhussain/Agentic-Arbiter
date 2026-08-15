# -*- coding: utf-8 -*-
"""N-34  ---  HOW BIG is the missing vertical dimension?   FREE, analytic.

THE GAP, AND WHY IT IS THE LARGEST ONE
    Our solver is two-dimensional. It has no "up". Real plumes spread vertically as well as
    horizontally, and that vertical spread dilutes them. ASHRAE Chapter 46's dilution equation (22)
    makes the missing term explicit:

        ASHRAE, 3-D :   concentration  proportional to  Q / (U * sigma_y * sigma_z)
        ours, 2-D   :   temperature    proportional to  Q / (U * sigma_y)

    The difference is exactly one factor of sigma_z. N-29 already established the DIRECTION this
    biases us -- we over-predict, because we omit a dilution term. This test establishes the SIZE.

THE DERIVATION, so the number can be checked rather than believed
    Peak values of a Gaussian plume at downwind distance x:

        2-D:   theta_2 = (Q/H) / (u * sigma_y * sqrt(2 pi))      H = the layer depth our 2-D world
                                                                  implicitly assumes
        3-D:   theta_3 =  Q     / (u * sigma_y * sigma_z * 2 pi)

        ratio  theta_2 / theta_3 = sqrt(2 pi) * sigma_z / H

    Our exchange_s was FITTED so that the solver reproduces the measured recirculation at the
    calibration geometry. That fit is what implicitly set H: it chose H such that the ratio is 1 at
    the calibration distance, i.e. H = sqrt(2 pi) * sigma_z(x_cal). Substituting:

        OVER-PREDICTION FACTOR  =  sigma_z(x_app) / sigma_z(x_cal)

    So the error is not a fixed number -- it GROWS with how far the application distance exceeds the
    distance the model was calibrated at. That is the honest statement of the gap.

INPUTS, each labelled
    sigma_z / sigma_y = 0.667   📘 ASHRAE Ch. 46 Eq. (21): i_y = 0.75 i_x, i_z = 0.50 i_x, so the
                                ratio is 0.50/0.75. Valid in the near-field mechanical-mixing regime,
                                which is where we are (source 96 m wide, distances 150-600 m).
    sigma_y = a x^b             📘 published Pasquill-Gifford, cross-checked in two sources
    x_cal                       ✏️ OURS, and the weak link. The calibration was on air-cooled
                                condenser DECK recirculation, and the deck we modelled in N-21 was
                                8 x 4 cells of 30 m = 240 x 120 m. The distance hot air actually
                                travels from the upstream edge into the inlet is of that order but is
                                not a single number, so it is SWEPT rather than assumed.

WHAT THIS TEST CANNOT DO
    It cannot tell us the true intake temperature. It converts "we are missing a dimension, and we
    know the sign" into "we are missing a dimension, we know the sign, and here is the factor" -- with
    the factor's dependence on the one weak assumption shown explicitly instead of buried.
"""
import sys, math
import numpy as np

from common import banner, save_result, verdict

PG = {"A": (0.493, 0.88), "B": (0.337, 0.88), "C": (0.195, 0.90),
      "D": (0.128, 0.90), "E": (0.091, 0.91), "F": (0.067, 0.90)}
SZ_OVER_SY = 0.50 / 0.75           # ASHRAE Ch.46 Eq.(21)
X_CAL_SWEEP = (60.0, 120.0, 180.0, 240.0)      # plausible ACC-deck travel distances, swept
X_APP = (150.0, 230.0, 400.0, 600.0)           # separations the product is applied at
HEADLINE_AT_230 = 0.8389                       # N-19 post-fix headline, for the corrected estimate


def sigma_z(cls, x):
    a, b = PG[cls]
    return SZ_OVER_SY * a * x ** b


def main():
    banner("N-34  How big is the missing vertical dimension?   [FREE, analytic]")
    print("   ASHRAE Ch.46 Eq.(22):  D = 4 U sigma_y sigma_z / (Ve de^2)   -- sigma_z is the term we lack")
    print("   over-prediction factor = sigma_z(x_app) / sigma_z(x_cal) = (x_app/x_cal)^b")
    print("   sigma_z/sigma_y = %.4f from ASHRAE Eq.(21); b = 0.88-0.91 from Pasquill-Gifford"
          % SZ_OVER_SY)
    print("\n   NOTE the factor does NOT depend on sigma_z/sigma_y at all -- that ratio cancels in")
    print("   sigma_z(x_app)/sigma_z(x_cal). It depends only on the EXPONENT b and the two distances.")
    print("   So the one ASHRAE-sourced ratio is not even load-bearing here. Good.")

    print("\n   OVER-PREDICTION FACTOR, by stability class and calibration distance")
    print("   (>1 means we over-predict, i.e. CONSERVATIVE)")
    rows = []
    for cls in ("B", "C", "D"):                      # the classes that dominate decision hours (N-33)
        a, b = PG[cls]
        print("\n      class %s  (b = %.2f)" % (cls, b))
        print("      %-14s %s" % ("x_cal", "  ".join("x_app=%.0f m" % x for x in X_APP)))
        for xc in X_CAL_SWEEP:
            fac = [(x / xc) ** b for x in X_APP]
            rows.append({"cls": cls, "b": b, "x_cal": xc,
                         "factors": {str(int(x)): f for x, f in zip(X_APP, fac)}})
            print("      %-14s %s" % ("%.0f m" % xc,
                                      "  ".join("%10.2f" % f for f in fac)))

    # headline sensitivity at the geometry we actually quote
    print("\n   WHAT THIS DOES TO THE HEADLINE AT 230 m")
    print("      N-19 post-fix headline: %+.4f C" % HEADLINE_AT_230)
    print("      %-14s %-14s %-16s" % ("x_cal", "factor", "corrected estimate"))
    corr = {}
    b_mid = PG["C"][1]
    for xc in X_CAL_SWEEP:
        f = (230.0 / xc) ** b_mid
        corr[xc] = HEADLINE_AT_230 / f
        print("      %-14s %-14.2f %+.4f C" % ("%.0f m" % xc, f, corr[xc]))
    lo, hi = min(corr.values()), max(corr.values())
    print("      -> corrected headline spans %+.4f to %+.4f C across the x_cal sweep" % (lo, hi))
    print("      N-19's measured band from the stub sweep is 0.415 to 1.713 C")
    inside = (lo >= 0.415) and (hi <= 1.713)
    print("      is the whole corrected range already INSIDE that band? %s" % inside)

    # the factor at the calibration scale itself -- a consistency check
    print("\n   CONSISTENCY CHECK")
    print("      At x_app = x_cal the factor must be exactly 1.00 by construction:")
    for xc in X_CAL_SWEEP:
        print("         x_cal = x_app = %.0f m  ->  factor %.4f" % (xc, (xc / xc) ** b_mid))

    f230 = [(230.0 / xc) ** b_mid for xc in X_CAL_SWEEP]
    f600 = [(600.0 / xc) ** b_mid for xc in X_CAL_SWEEP]
    print("\n   RESULT")
    print("      at 230 m (our quoted geometry): factor %.2f to %.2f" % (min(f230), max(f230)))
    print("      at 600 m (largest separation) : factor %.2f to %.2f" % (min(f600), max(f600)))
    print("      the factor is >= 1 in %d of %d (class, x_cal, x_app) combinations"
          % (sum(1 for r in rows for v in r["factors"].values() if v >= 1.0),
             sum(1 for r in rows for _ in r["factors"])))

    # PASS condition, fixed before running: the correction must be bounded and conservative
    all_f = [v for r in rows for v in r["factors"].values()]
    bounded = max(all_f) < 10.0
    mostly_conservative = float(np.mean([v >= 1.0 for v in all_f])) > 0.7
    ok = bounded and mostly_conservative and inside

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      correction bounded (max factor < 10)        : %s  (max %.2f)" % (bounded, max(all_f)))
    print("      mostly conservative (>70 %% of cases >= 1)   : %s  (%.0f %%)"
          % (mostly_conservative, 100 * float(np.mean([v >= 1.0 for v in all_f]))))
    print("      corrected headline stays inside N-19's band  : %s" % inside)
    print()
    verdict(ok,
            "PASS - the missing vertical dimension is quantified and bounded. At our quoted 230 m "
            "geometry it means we over-predict by a factor of %.2f to %.2f depending on the "
            "calibration distance; at the largest separation we consider, 600 m, by %.2f to %.2f. It "
            "is CONSERVATIVE in %.0f %% of cases, and the corrected headline stays inside the band we "
            "already publish. So the largest gap in the physics now has a size, a sign, and a stated "
            "dependence on its one weak assumption."
            % (min(f230), max(f230), min(f600), max(f600),
               100 * float(np.mean([v >= 1.0 for v in all_f]))),
            "FAIL - the correction is either unbounded (max %.2f) or not reliably conservative "
            "(%.0f %% >= 1) or pushes the headline outside the published band. Do not claim the gap "
            "is quantified." % (max(all_f), 100 * float(np.mean([v >= 1.0 for v in all_f]))))

    save_result("n34_vertical.json", {
        "gap": "solver is 2-D; ASHRAE Eq.(22) shows the missing term is sigma_z",
        "derivation": "theta_2/theta_3 = sqrt(2pi) sigma_z / H; the fit set H = sqrt(2pi) "
                      "sigma_z(x_cal); therefore factor = sigma_z(x_app)/sigma_z(x_cal) = "
                      "(x_app/x_cal)^b",
        "note": "the ASHRAE sigma_z/sigma_y ratio cancels; only the exponent b and the two "
                "distances matter",
        "sz_over_sy_ashrae": SZ_OVER_SY, "x_cal_sweep": list(X_CAL_SWEEP),
        "x_app": list(X_APP), "rows": rows,
        "headline_at_230": HEADLINE_AT_230,
        "corrected_headline": {str(int(k)): v for k, v in corr.items()},
        "corrected_range": [lo, hi], "n19_band": [0.415, 1.713],
        "corrected_inside_n19_band": inside,
        "factor_at_230": [min(f230), max(f230)], "factor_at_600": [min(f600), max(f600)],
        "frac_conservative": float(np.mean([v >= 1.0 for v in all_f])),
        "max_factor": max(all_f), "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
