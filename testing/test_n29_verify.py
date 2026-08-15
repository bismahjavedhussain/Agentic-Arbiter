# -*- coding: utf-8 -*-
"""N-29  ---  VERIFICATION: does the code solve its own equations correctly?   FREE, CPU.

VERIFICATION IS NOT VALIDATION, AND WE HAD DONE NONE OF IT
    validation    are the equations right for reality?    needs measurements. Ours are power-station
                  field data (N-21/N-22), and that limit cannot be closed before a site sensor exists.
    verification  is the code solving the equations correctly?   needs NO measurements at all. It is
                  checkable against exact mathematics, and until this file there was none.

    That distinction matters because a solver can be perfectly calibrated and still be solving the
    wrong discrete problem. Calibration would then be absorbing a numerical error into a physical
    constant -- which is precisely how N-11 went wrong, one level up.

THE EQUATION ACTUALLY IMPLEMENTED, read off solver.solve()
        dT/dt = -(u dT/dx + v dT/dy) + D (d2T/dx2 + d2T/dy2) + S
    upwind advection (1st order), central diffusion (2nd order), explicit stepping to steady state,
    inflow held at ambient, outflow zero-gradient, obstacle cells FORCED to ambient. No sink term.

THREE CHECKS

  V1  ANALYTIC GAUSSIAN PLUME.  With no obstacles, uniform wind u along +x, and streamwise diffusion
      negligible (high Peclet number), the steady equation reduces to the heat equation with x/u
      playing the role of time:
                  u dTheta/dx = D d2Theta/dy2
      whose solution from a source at x0 is Gaussian in y with variance
                  sigma_y^2(x) = sigma_0^2 + 2 D (x - x0) / u
      So a straight line fitted to sigma_y^2 against x must have SLOPE EXACTLY 2D/u. That is a sharp,
      normalisation-free, quantitative test of the diffusion term -- it does not require knowing the
      source strength, and the intercept absorbs the finite source size.

  V2  CROSS-STREAM HEAT CONSERVATION.  With no sink, everything injected must be advected downstream:
                  u * integral(Theta dy)  =  integral integral (S dA)
      exactly, at every station downstream of the source. Units both K m^2 / s. This is an exact
      identity, not an approximation, so any shortfall is numerical loss and is measurable.

  V3  GRID CONVERGENCE.  Halve dx twice on the real geometry. If the answer keeps moving, the number
      is a discretisation artifact rather than physics. The observed order of convergence is estimated
      by Richardson extrapolation; upwind advection is formally 1st order, so p ~ 1 is the expectation
      and a p near 0 would mean the answer is not converging at all.

  V4  OBSTACLE TREATMENT vs ITS OWN DOCUMENTATION.  solver.py's docstring says "Buildings are no-flow
      obstacle cells". The code does `newT = np.where(free, newT, ambient)`, which is a fixed-
      temperature Dirichlet condition, not a no-flow wall. A no-flow wall reflects heat and conserves
      it; a cell pinned at ambient ABSORBS heat. If that is what is happening, the buildings are
      acting as heat sinks and the documentation is wrong about the physics being solved. Measured
      by repeating V2 with obstacles present.

INTERPRETING A FAILURE
    Unlike a validation test, a verification failure has two possible causes and they must be
    separated before anything is claimed: either the CODE is wrong, or the ANALYTIC EXPECTATION is
    mis-specified. This file states the expectation explicitly enough to tell the difference.

PRE-REGISTERED
    V1  fitted slope within 10 % of 2D/u at the finest grid
    V2  conservation shortfall < 5 % with no obstacles
    V3  |rise(dx=5) - rise(dx=10)| < 0.05 C, and observed order p in [0.5, 2.5]
    V4  reported, not pass/failed -- it is a documentation-vs-code question, not a correctness bound
"""
import sys, math, time
import numpy as np

from common import banner, save_result, verdict
from solver import Site, solve, demo_site, intake_temperature, CALIBRATED

AMB = 30.0
U = 6.0                 # wind speed, m/s
WIND_FROM = 270.0       # from the west -> u = +6 m/s, v = 0
D_DIFF = 8.0            # the diffusivity whose implementation V1 tests
SIZE = 2000.0
SRC_X, SRC_Y = 400.0, 1000.0
SRC_SIDE = 20.0
SRC_STRENGTH = 11.0 / CALIBRATED["exchange_s"]      # K/s, the operational value
STATIONS = (600.0, 800.0, 1000.0, 1200.0, 1400.0, 1600.0)

V1_TOL = 0.10
V2_TOL = 0.05
V3_TOL_C = 0.05
V3_ORDER_RANGE = (0.5, 2.5)


def plume_site(dx):
    """Empty domain, one small square source. No buildings at all."""
    s = Site(SIZE, dx)
    i0, i1 = int((SRC_Y - SRC_SIDE / 2) / dx), int((SRC_Y + SRC_SIDE / 2) / dx)
    j0, j1 = int((SRC_X - SRC_SIDE / 2) / dx), int((SRC_X + SRC_SIDE / 2) / dx)
    s.source[i0:i1, j0:j1] = SRC_STRENGTH
    return s


def gaussian_moments(theta_col, dx):
    """Variance of a 1-D cross-stream profile, by second moment. Returns (mass, mean, var)."""
    y = np.arange(len(theta_col)) * dx
    w = np.clip(theta_col, 0.0, None)
    m = w.sum()
    if m <= 0:
        return 0.0, float("nan"), float("nan")
    mu = float((w * y).sum() / m)
    var = float((w * (y - mu) ** 2).sum() / m)
    return float(m), mu, var


def run_plume(dx, max_steps=200000, tol=1e-9):
    site = plume_site(dx)
    t0 = time.time()
    T, steps = solve(site, AMB, U, WIND_FROM, diffusivity=D_DIFF,
                     max_steps=max_steps, tol=tol, return_steps=True)
    return site, T - AMB, steps, time.time() - t0


def main():
    banner("N-29  VERIFICATION: is the code solving its own equations correctly?   [FREE]")
    print("   equation:  dT/dt = -(u dT/dx + v dT/dy) + D lap(T) + S")
    print("   upwind advection (1st order), central diffusion (2nd order), no sink term")
    print("   u = %.1f m/s along +x, D = %.1f m2/s  ->  expected sigma_y^2 slope = 2D/u = %.4f m"
          % (U, D_DIFF, 2 * D_DIFF / U))
    peclet = U * SIZE / D_DIFF
    print("   Peclet number u.L/D = %.0f, so neglecting streamwise diffusion is justified" % peclet)

    # ---------------------------------------------------------------- V1 + V2
    print("\n   V1/V2  ANALYTIC GAUSSIAN PLUME on an empty domain")
    print("      %6s %8s %10s %12s %12s %10s %10s"
          % ("dx m", "steps", "solve s", "slope 2D/u", "fitted slope", "err %", "cons err %"))
    v1_rows = []
    for dx in (20.0, 10.0, 5.0):
        site, th, steps, secs = run_plume(dx)
        total_src = float(site.source.sum()) * dx * dx          # K m^2 / s
        xs, vars_, masses = [], [], []
        for xs_m in STATIONS:
            j = int(xs_m / dx)
            col = th[:, j]
            m, mu, var = gaussian_moments(col, dx)
            if not math.isfinite(var):
                continue
            xs.append(xs_m - SRC_X)
            vars_.append(var)
            masses.append(m * dx * U)                            # u * integral(theta dy)
        xs, vars_, masses = np.array(xs), np.array(vars_), np.array(masses)
        A = np.vstack([xs, np.ones_like(xs)]).T
        slope, intercept = np.linalg.lstsq(A, vars_, rcond=None)[0]
        expected = 2 * D_DIFF / U
        err = abs(slope - expected) / expected
        cons_err = float(np.mean(np.abs(masses - total_src) / total_src))
        v1_rows.append({"dx": dx, "steps": steps, "secs": secs, "slope": float(slope),
                        "intercept": float(intercept), "expected_slope": expected,
                        "slope_err_frac": float(err), "cons_err_frac": cons_err,
                        "total_source": total_src, "fluxes": masses.tolist(),
                        "variances": vars_.tolist(), "x_rel": xs.tolist()})
        print("      %6.1f %8d %10.1f %12.4f %12.4f %10.2f %10.2f"
              % (dx, steps, secs, expected, slope, 100 * err, 100 * cons_err))

    fine = v1_rows[-1]
    print("\n      finest grid, station-by-station:")
    print("         %10s %12s %12s %14s %12s"
          % ("x - x0 m", "sigma_y m", "sigma^2 pred", "u.int(theta dy)", "source"))
    for k, xr in enumerate(fine["x_rel"]):
        pred = fine["intercept"] + fine["expected_slope"] * xr
        print("         %10.0f %12.2f %12.1f %14.4f %12.4f"
              % (xr, math.sqrt(fine["variances"][k]), pred, fine["fluxes"][k],
                 fine["total_source"]))

    v1 = fine["slope_err_frac"] < V1_TOL
    v2 = fine["cons_err_frac"] < V2_TOL
    print("\n      V1 sigma_y^2 slope within %.0f %% of 2D/u : %s  (%.2f %% at dx=%.0f)"
          % (100 * V1_TOL, v1, 100 * fine["slope_err_frac"], fine["dx"]))
    print("      V2 conservation shortfall < %.0f %%       : %s  (%.2f %%)"
          % (100 * V2_TOL, v2, 100 * fine["cons_err_frac"]))

    # ---------------------------------------------------------------- V3
    print("\n   V3  GRID CONVERGENCE on the real demo geometry")
    print("      %6s %8s %10s %14s" % ("dx m", "steps", "solve s", "intake rise C"))
    conv = []
    for dx in (20.0, 10.0, 5.0):
        site, intake = demo_site(dx=dx, exchange_s=CALIBRATED["exchange_s"])
        t0 = time.time()
        T, steps = solve(site, AMB, U, WIND_FROM, diffusivity=D_DIFF, max_steps=200000,
                         tol=1e-9, return_steps=True,
                         downwash_uc=CALIBRATED["downwash_uc"],
                         downwash_exponent=CALIBRATED["downwash_exponent"])
        rise = intake_temperature(T, site, *intake) - AMB
        conv.append({"dx": dx, "steps": steps, "secs": time.time() - t0, "rise": float(rise)})
        print("      %6.1f %8d %10.1f %14.5f" % (dx, steps, conv[-1]["secs"], rise))

    f20, f10, f5 = (c["rise"] for c in conv)
    d1, d2 = f20 - f10, f10 - f5
    if abs(d2) > 1e-12 and d1 / d2 > 0:
        order = math.log(abs(d1 / d2)) / math.log(2.0)
        rich = f5 + (f5 - f10) / (2 ** order - 1)
    else:
        order, rich = float("nan"), float("nan")
    print("      successive differences: dx20-dx10 = %+.5f, dx10-dx5 = %+.5f" % (d1, d2))
    print("      observed order of convergence p    : %.2f  (upwind advection is formally 1)" % order)
    print("      Richardson-extrapolated dx->0 rise : %.5f C" % rich)
    v3 = abs(d2) < V3_TOL_C and (V3_ORDER_RANGE[0] <= order <= V3_ORDER_RANGE[1])
    print("      V3 |dx10 - dx5| < %.2f C and p in [%.1f, %.1f] : %s"
          % (V3_TOL_C, V3_ORDER_RANGE[0], V3_ORDER_RANGE[1], v3))

    # ---------------------------------------------------------------- V4
    print("\n   V4  OBSTACLE TREATMENT vs THE DOCSTRING'S CLAIM")
    print("      solver.py says \"Buildings are no-flow obstacle cells\". The code pins them to")
    print("      ambient. A no-flow wall conserves heat; a cell pinned to ambient absorbs it.")
    dx = 10.0
    site_open = plume_site(dx)
    T_open = solve(site_open, AMB, U, WIND_FROM, diffusivity=D_DIFF, max_steps=200000, tol=1e-9)
    site_blk = plume_site(dx)
    site_blk.add_building(cx=900, cy=1000, w=120, h=200)      # a wall straddling the plume
    T_blk = solve(site_blk, AMB, U, WIND_FROM, diffusivity=D_DIFF, max_steps=200000, tol=1e-9)
    total_src = float(site_open.source.sum()) * dx * dx
    j = int(1600.0 / dx)
    flux_open = float(np.clip(T_open[:, j] - AMB, 0, None).sum()) * dx * U
    flux_blk = float(np.clip(T_blk[:, j] - AMB, 0, None).sum()) * dx * U
    absorbed = 1.0 - flux_blk / max(flux_open, 1e-12)
    print("      downstream flux, open domain     : %.4f  (source %.4f, %.1f %% conserved)"
          % (flux_open, total_src, 100 * flux_open / total_src))
    print("      downstream flux, wall in the plume: %.4f  -> %.1f %% of the heat DISAPPEARED"
          % (flux_blk, 100 * absorbed))
    if absorbed > 0.02:
        print("      *** CONFIRMED: obstacles are heat SINKS, not no-flow walls. The docstring is")
        print("          wrong about the physics being solved. This is a MODELLING choice with a")
        print("          real consequence -- a building between source and intake removes heat that")
        print("          a reflecting wall would deflect around it, so intake rise is BIASED LOW")
        print("          whenever a structure sits in the path. Fix the docstring, and decide")
        print("          deliberately whether the sink is wanted.")
    else:
        print("      obstacles do not measurably absorb heat; the docstring's wording is defensible.")

    ok = v1 and v2 and v3
    print("\n   RESULT")
    print("      V1 diffusion term correct  : %s" % v1)
    print("      V2 heat conserved          : %s" % v2)
    print("      V3 grid converged          : %s" % v3)
    print("      V4 obstacle sink found     : %s  (%.1f %% absorbed)" % (absorbed > 0.02,
                                                                        100 * absorbed))
    print()
    verdict(ok,
            "PASS - the solver reproduces the exact analytic plume solution: the sigma_y^2 slope is "
            "within %.2f %% of 2D/u, heat is conserved to %.2f %%, and the intake rise is grid "
            "converged (order %.2f, dx10-to-dx5 change %.5f C). This is VERIFICATION, independent of "
            "any measurement -- the code solves the equations it claims to. Validation against a data "
            "centre remains open and is stated separately."
            % (100 * fine["slope_err_frac"], 100 * fine["cons_err_frac"], order, abs(d2)),
            "FAIL - V1 %s (slope err %.2f %%), V2 %s (cons err %.2f %%), V3 %s (order %.2f, change "
            "%.5f C). Diagnose which of the two causes applies -- wrong code, or wrong analytic "
            "expectation -- before touching anything, and do not claim the solver is verified."
            % (v1, 100 * fine["slope_err_frac"], v2, 100 * fine["cons_err_frac"], v3, order,
               abs(d2)))

    save_result("n29_verify.json", {
        "equation": "dT/dt = -(u dT/dx + v dT/dy) + D lap(T) + S; upwind adv, central diff, no sink",
        "u_ms": U, "diffusivity": D_DIFF, "peclet": peclet,
        "expected_sigma2_slope": 2 * D_DIFF / U,
        "v1_v2_grids": v1_rows, "v1_pass": v1, "v2_pass": v2,
        "v1_tol": V1_TOL, "v2_tol": V2_TOL,
        "convergence": conv, "diff_20_10": d1, "diff_10_5": d2,
        "observed_order": order, "richardson_limit": rich, "v3_pass": v3,
        "obstacle_flux_open": flux_open, "obstacle_flux_blocked": flux_blk,
        "obstacle_absorbed_frac": absorbed,
        "obstacle_finding": "obstacles are pinned to ambient, i.e. Dirichlet heat sinks, not the "
                            "no-flow walls the docstring claims",
        "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
