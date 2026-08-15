# -*- coding: utf-8 -*-
"""N-6  ---  solver validation.  FREE.

Six physics checks. If the solver fails these it is decoration, not evidence,
and the NVIDIA argument collapses with it.
"""
import math, sys, time
import numpy as np
from solver import Site, solve, intake_temperature, demo_site
from common import banner, save_result, verdict

AMB = 30.0
results = {}


def t1_far_field():
    print("\n   1. FAR-FIELD RELAXATION  (no heat sources -> interior returns to ambient)")
    s = Site(1000.0, 10.0)
    s.add_building(500, 500, 100, 100)
    T = solve(s, AMB, 3.0, 270.0)
    dev = float(np.max(np.abs(T - AMB)))
    ok = dev < 0.01
    print("      max deviation from ambient: %.6f C" % dev)
    results["far_field"] = {"max_dev": dev, "pass": ok}
    return ok


def t2_no_wind_symmetry():
    print("\n   2. NO-WIND SYMMETRY  (calm + central source -> radially symmetric)")
    s = Site(1000.0, 10.0)
    s.add_condensers(500, 500, 40, 40, discharge_k=11.0)
    T = solve(s, AMB, 0.0, 0.0)
    n = s.n
    lr = float(np.max(np.abs(T - np.fliplr(T))))
    ud = float(np.max(np.abs(T - np.flipud(T))))
    ok = lr < 0.05 and ud < 0.05
    print("      left-right asymmetry: %.6f C   up-down: %.6f C" % (lr, ud))
    results["symmetry"] = {"lr": lr, "ud": ud, "pass": ok}
    return ok


def t3_wind_response():
    print("\n   3. WIND RESPONSE  (rotate inflow 180 deg -> the plume flips sides)")
    s = Site(1400.0, 10.0)
    s.add_condensers(700, 700, 60, 60, discharge_k=11.0)
    east = intake_temperature(solve(s, AMB, 3.0, 270.0), s, 1000, 700) - AMB   # wind FROM west
    west = intake_temperature(solve(s, AMB, 3.0, 90.0), s, 1000, 700) - AMB    # wind FROM east
    ok = east > 0.05 and east > 4 * max(west, 1e-9)
    print("      downwind point, wind FROM west: %+.4f C above ambient" % east)
    print("      same point,     wind FROM east: %+.4f C above ambient" % west)
    print("      ratio: %.1fx" % (east / max(west, 1e-9)))
    results["wind_response"] = {"downwind": east, "upwind": west, "pass": ok}
    return ok


def t4_recirculation_magnitude():
    print("\n   4. RECIRCULATION MAGNITUDE  (must be the right order, not 0.01 C or 30 C)")
    print("      published: air-cooled condensers discharge 8-14 C above ambient [Sailor 2026]")
    print("      NOTE: clean site - one hall plus its condenser bank, no downstream building,")
    print("            because sample points must not land inside an obstacle cell.")
    s = Site(2400.0, 10.0)
    s.add_building(cx=700, cy=1200, w=200, h=120)
    s.add_condensers(cx=830, cy=1200, w=60, h=120, discharge_k=11.0)
    T = solve(s, AMB, 3.0, 270.0)                       # wind FROM west -> plume goes east
    rows = []
    for d in (60, 150, 300, 600, 1000):
        rise = intake_temperature(T, s, 860 + d, 1200) - AMB
        rows.append((d, round(rise, 4)))
        print("      %4d m downwind of the bank: %+.4f C" % (d, rise))
    near = rows[0][1]
    decays = all(rows[i][1] >= rows[i + 1][1] - 1e-4 for i in range(len(rows) - 1))
    ok = 0.05 < near < 12.0 and decays
    print("      monotonic decay with distance: %s" % decays)
    print("      (published downwind measurements: 0.7-0.9 C average, 2.2 C peak, to ~500 m)")
    results["recirculation"] = {"profile": rows, "pass": ok}
    return ok


def t5_energy_scaling():
    print("\n   5. SOURCE SCALING  (double the discharge -> roughly double the rise)")
    s1, intake = demo_site(discharge_k=11.0)
    s2, _ = demo_site(discharge_k=22.0)
    r1 = intake_temperature(solve(s1, AMB, 3.0, 270.0), s1, *intake) - AMB
    r2 = intake_temperature(solve(s2, AMB, 3.0, 270.0), s2, *intake) - AMB
    ratio = r2 / r1 if abs(r1) > 1e-9 else float("nan")
    ok = 1.7 < ratio < 2.3
    print("      rise at 11 C discharge: %+.4f C" % r1)
    print("      rise at 22 C discharge: %+.4f C   ratio %.2f (linear system => ~2.0)" % (r2, ratio))
    results["scaling"] = {"r1": r1, "r2": r2, "ratio": ratio, "pass": ok}
    return ok


def t6_grid_convergence():
    print("\n   6. GRID CONVERGENCE  (halve the cell -> answer moves less than the ensemble spread)")
    vals = []
    for dx in (20.0, 10.0, 5.0):
        s, intake = demo_site(dx=dx)
        t0 = time.time()
        r = intake_temperature(solve(s, AMB, 3.0, 270.0), s, *intake) - AMB
        vals.append((dx, r, round(time.time() - t0, 2)))
        print("      dx=%4.1f m  n=%4d  rise %+.4f C   (%.2fs)" % (dx, s.n, r, vals[-1][2]))
    change = abs(vals[-1][1] - vals[-2][1])
    ok = change < 0.15
    print("      change from dx=10 to dx=5: %.4f C" % change)
    results["convergence"] = {"vals": vals, "change": change, "pass": ok}
    return ok


def main():
    banner("N-6  Solver validation - six physics checks   [FREE]")
    tests = [t1_far_field, t2_no_wind_symmetry, t3_wind_response,
             t4_recirculation_magnitude, t5_energy_scaling, t6_grid_convergence]
    passed = []
    for t in tests:
        try:
            passed.append(bool(t()))
        except Exception as e:
            print("      ERROR: %s" % str(e)[:200])
            passed.append(False)
    n_ok = sum(passed)
    print("\n   %d / %d checks passed" % (n_ok, len(passed)))
    ok = n_ok == len(passed)
    verdict(ok,
            "PASS - the solver behaves like the physics it claims to model. It is evidence, not decoration.",
            "FAIL - %d check(s) failed. Fix before the solver is used for anything." % (len(passed) - n_ok))
    save_result("n6_solver.json", {"pass": ok, "n_passed": n_ok, "detail": results})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
