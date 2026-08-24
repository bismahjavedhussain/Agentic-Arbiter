# -*- coding: utf-8 -*-
"""N-54 -- THE REFUSAL SURFACE: sweep every wind bearing on the REAL Ashburn geometry.

WHAT THIS MEASURES, and why it is not a formality
-------------------------------------------------
`solver.py` models buildings as TRANSPARENT to the temperature field: N-29 V4 measures 0.0 % of
plume heat absorbed, so heat is conserved exactly. (This paragraph asserted the opposite -- the
RETRACTED heat-ABSORBING description, gotcha #26 -- until 2026-08-20, eight days after the pinning
was removed from the solver.) Transparency is not deflection either, though, so whenever a building
sits between the emission point and the intake the solver has no answer it can stand behind, and
`solver.path_blocked()` makes the agent REFUSE to report a number instead of returning a wrong one.

At the validated reference layout the source-to-intake path was always clear, so refusal never fired.
At a REAL site -- two long rotated halls tens of metres apart -- it must fire often. This script
measures how often, in bearings and in real wind hours, and finds the true worst-case bearing. The
facade gap is READ from the committed geometry rather than quoted here: this docstring named 47.9 m,
which belongs to a site that has since been superseded twice (the committed Ashburn pair clears the
60 m floor by 0.3 m).

THE EMISSION POINT -- the thing that makes this measurement valid or worthless
-----------------------------------------------------------------------------
`build_site.py` places the condenser bank as a strip INSIDE the source hall, so all 30 bank cells are
also obstacle cells. A ray starting at the bank CENTROID therefore begins inside a building and
`path_blocked()` returns True for 36 of 36 downwind bearings -- 100 % refusal, measured and confirmed
before this script was written. That number is an artefact of where the ray starts, not physics.

A real condenser bank discharges at the FACADE. So the emission point here is the bank's outward face:
the facade midpoint pushed OUT along the facade's outward normal (away from the hall centroid) until
it clears the obstacle mask. Obstacle crossings after that point are genuine blockage. The script
asserts the emission point is clear of obstacles and prints it, so the choice is auditable.

GEOMETRIC FACT recorded while writing this (verified, see the audit block below): BOTH ~189 m facades
of the source hall face AWAY from the receptor (outward.u = -0.896 and -0.660). The receptor lies off
the END of the hall, so the only receptor-facing facade is the 37 m end wall. A "long AND facing"
bank mode therefore CANNOT exist at this site. That is why the two modes are what they are:
  longest : 189 m facade, 3,000 m^2 -- realistic bank size, but the plume must round a corner
  facing  :  37 m end wall, 600 m^2 -- aims at the receptor, implausible facade for condensers

PRE-REGISTERED CONDITIONS -- written before the first run, per methodology rule 2
--------------------------------------------------------------------------------
P1  NON-DEGENERATE REFUSAL, mode=longest. The refused fraction of the 72 bearings must be strictly
    between 0 and 1, AND strictly between 0 and 1 as a fraction of DOWNWIND bearings.
      refused/downwind == 0    -> path_blocked never fires; gotcha #26's expectation is wrong here.
      refused/downwind == 1    -> the emission-point fix failed; the measurement is the artefact again.
    Either extreme is a FAIL and must be reported as one, not re-defined.

P2  THE NAIVE CRITICAL BEARING IS WRONG, mode=longest. PLAN/HANDOFF section 4.3 asserts that with the
    bank on a long facade the worst bearing is NO LONGER the 203.7 deg source->receptor bearing.
    Condition: the argmax-rise bearing differs from 203.7 deg by MORE than one grid step (5 deg).
    If it lands within 5 deg, section 4.3's warning was wrong and must be RETRACTED, not quietly dropped.

P3  GEOMETRIC COHERENCE. Refused bearings must form at most 3 circularly-contiguous arcs. Blockage is
    a smooth function of bearing, so scattered singletons would indicate a ray-casting bug, not physics.

P4  REPORTING (not pass/fail). The wind-weighted refusal fraction is quoted with n and a 95 % Wilson
    interval, over 5 real years of KIAD hours. Calm hours (sknt == 0, bearing undefined) are counted
    and EXCLUDED from bearing weighting, never silently folded in.

P5  SENSITIVITY (not pass/fail). mode=facing is reported alongside as a sensitivity, never as the
    headline, because a condenser bank does not go on a 37 m end wall.

AMENDMENT 2026-08-18, AFTER THE SITE WAS RE-SELECTED -- read this before quoting any verdict
--------------------------------------------------------------------------------------------
P1-P5 above were written for the ORIGINAL pair (852039781 / 793087859). **They are NOT edited, and
their verdicts there stand as recorded: P1 FAILED (100 % of downwind bearings refused), P3 PASSED,
P2 met-but-vacuous under `longest` and PASSED under `facing`.**

Because P1 failed, the site was re-selected -- see `refusal_rank.py`, whose ranking objective was
stated before its numbers were read. The new pair is **597970809 / 597970806** (Digital Realty Northern
Virginia IAD35 / IAD36), chosen because its refusal surface was MEASURED as clear.

**At the new site P1 FAILS AGAIN, and in the opposite direction: 0.0 % refused instead of 100 %.**
That is not a defect. It is the *intended consequence* of selecting for a clear plume path. P1 as
written conflated two different questions:

    (i)  does `solver.path_blocked()` actually fire?      -- a CODE-CORRECTNESS question
    (ii) is this site's plume path clear?                 -- a SITE-SUITABILITY question

P1 answers (ii) but is phrased as if a non-extreme value were always correct. At a deliberately-clear
site, 0 % is the right answer and P1's condition is simply inapplicable.

**I am deliberately NOT registering replacement pass/fail conditions here, because the numbers have
already been seen and inventing conditions now would be exactly the post-hoc threshold-moving that
methodology rule 2 forbids.** The new site's figures are therefore reported as MEASUREMENTS, not as
passes. Any future suitability test must be pre-registered before its first run.

**Independent positive control that (i) holds -- `path_blocked` is NOT silently broken:** it returns
True for 36 of 36 downwind bearings at the old site's `longest` mode, for 36 of 36 at the new site's
`facing` mode, and `refusal_rank.py` measured **56 of 145** gate-passing pairs at 100 % refusal. The
function fires. 0 % at the new site's `longest` mode is a property of that geometry, not of the code.

**`facing` mode is DEGENERATE at the new site and must not be quoted:** `facing_edge()` selects a 7 m
chamfer, giving a **1-cell, 100 m² bank** against `longest`'s 1,700 m². P5 called `facing` a
sensitivity; at this site it is not even that. Its whole purpose was to compensate for `longest` being
unusable at the OLD site, which no longer applies.

PARAMETERS AND WHERE EACH NUMBER COMES FROM  (rule 1: every human-written constant is labelled)
-----------------------------------------------------------------------------------------------
  diffusivity 7.40 m^2/s   MEASURED -- N-33 median in decision hours
  downwash_uc 8.0 m/s      CALIBRATED -- solver.CALIBRATED, field-fitted
  downwash_exponent 1.25   CALIBRATED -- N-21 falsified 2.0 against field data
  discharge_k, exchange_s  from the site JSON; calibrated, unchanged from the validated reference
  ambient 30.0 C           ARBITRARY -- we report RISE above ambient, which is what the bound uses
  bearings 5 deg steps     CHOSEN -- 72 bearings; finer than the 47-72 deg measured wind persistence
  intake disc=True         REQUIRED -- intake_temperature()'s box default is dx-dependent and reads
                           low; its docstring says any NEW absolute claim must pass disc=True.
  changeover limits        SCENARIO PARAMETERS, not agent decisions. Reported at all four of
                           18/21/24/27 C so no single value is load-bearing.

Run:  python direction_sweep.py            (both modes, ~92 s on CPU)
"""
import io
import json
import math
import os
import sys
import time

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from physics import solver                                        # noqa: E402
from physics.solver import CALIBRATED                             # noqa: E402
from build_site import rasterise                                  # noqa: E402

GEOM = os.path.join(ROOT, "data", "geometry")
# METRO-AWARE; ashburn keeps its original filenames so the audited chain is untouched.
import metros as _M                                                        # noqa: E402
WEATHER = os.path.join(ROOT, "data", "weather")

DIFFUSIVITY = 7.40          # MEASURED, N-33 median in decision hours
AMBIENT = 30.0              # ARBITRARY -- we report rise, not level
STEP_DEG = 5                # CHOSEN
BEARINGS = list(range(0, 360, STEP_DEG))
CHANGEOVER_C = [18.0, 21.0, 24.0, 27.0]     # SCENARIO parameters, all four reported
KT_TO_MS = 0.514444


# ----------------------------------------------------------------------------- helpers
def wilson(k, n, z=1.96):
    """95 % Wilson score interval for a proportion. Correct at extremes, unlike normal approx."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def contiguous_arcs(flags):
    """Number of circularly-contiguous runs of True in a list indexed by bearing."""
    n = len(flags)
    if all(flags):
        return 1
    if not any(flags):
        return 0
    # rotate so index 0 is False, then count rising edges
    z = flags.index(False)
    r = flags[z:] + flags[:z]
    return sum(1 for i in range(n) if r[i] and not r[i - 1])


def load_site(mode):
    """Rebuild a solver.Site from the saved geometry. Verifies the rebuild against the JSON."""
    p = _M.geom_path("solver_site_%s.json" % mode)
    d = json.load(open(p, encoding="utf-8"))
    n, dx = d["domain"]["n"], d["domain"]["dx_m"]
    s = solver.Site(d["domain"]["size_m"], dx)
    for ring in (d["source_ring_m"], d["receptor_ring_m"]):
        s.obstacle |= rasterise(ring, n, dx)
    bank = rasterise(d["bank_ring_m"], n, dx)
    if int(bank.sum()) != int(d["bank_cells"]):
        raise SystemExit("REBUILD MISMATCH %s: %d bank cells, JSON says %d"
                         % (mode, bank.sum(), d["bank_cells"]))
    s.source[bank] += d["discharge_k"] / d["exchange_s"]
    return s, d, bank


def emission_point(site, d, bank):
    """The bank's OUTWARD FACE: where the plume actually enters the air.

    Marches from the bank centroid along the outward normal (away from the source-hall centroid)
    until the cell is not an obstacle. Raises if it cannot clear -- silence here would restore the
    artefact this whole script exists to avoid.
    """
    dx, n = site.dx, site.n
    ys, xs = np.nonzero(bank)
    bc = ((xs.mean() + 0.5) * dx, (ys.mean() + 0.5) * dx)
    cA = d["source_centre_m"]
    ox, oy = bc[0] - cA[0], bc[1] - cA[1]
    L = math.hypot(ox, oy)
    if L < 1e-6:
        raise SystemExit("bank centroid coincides with hall centroid; outward normal undefined")
    ox, oy = ox / L, oy / L
    for k in range(0, 200):
        px, py = bc[0] + ox * (dx * 0.5) * k, bc[1] + oy * (dx * 0.5) * k
        j, i = int(px / dx), int(py / dx)
        if not (0 <= i < n and 0 <= j < n):
            raise SystemExit("outward march left the domain before clearing the obstacle")
        if not site.obstacle[i, j]:
            return (px, py), bc, (ox, oy), k * dx * 0.5
    raise SystemExit("could not clear the obstacle along the outward normal")


def load_wind():
    """THIS SITE'S OWN hourly record. Returns (bearing_deg, speed_ms, tmpc) triples + a calm count.

    🔴 THIS READ `kiad_hourly_2021_2025.json` AS A LITERAL UNTIL 2026-08-21, ON EVERY SITE.
    Section 6.13 of HANDOFF lists six paths that were changed from literals to `metros` lookups when
    the engine was made per-site. This one was not among them, and nothing noticed for two days,
    because the numbers it produces are internally consistent and plausible for anywhere:

      * every site's per-bearing rise curve was solved at **KIAD's median wind speed**, so Chicago's
        published plume curve was computed at Virginia's wind;
      * `export_plume_fields.py` reads that same median speed to solve the **72 rendered fields**, so
        the plume a reader drags around for Chicago was solved at Virginia's wind too;
      * the wind statistics shipped in every trace were KIAD's, and the block even hard-coded
        `"station": "KIAD"` beside them -- a field asserting a station the site does not use.

    The tell was arithmetic and it was sitting in the artefact: Chicago's usable + calm + missing
    came to **43,763**, which is KIAD's hour count, while Chicago's own record is KORD's **43,775**.
    `audit.check_wind_is_this_sites_own()` now asserts that identity for every site, because it is
    exactly the kind of claim a reader cannot check and a computer can.

    THE AGENT'S DECISIONS WERE NOT AFFECTED, and that is worth stating precisely rather than
    hopefully: `agent.rise_table()` maxes over a fixed 72 x 8 bearing/speed grid (`SPEED_GRID_MS`),
    which never consults a station record, so the bound and the schedule are untouched. What was
    wrong is everything DISPLAYED about the wind and the plume shape.
    """
    d = json.load(open(_M.weather_path(), encoding="utf-8"))
    fields = d["meta"]["fields"]
    it, idr, isk = fields.index("tmpc"), fields.index("drct"), fields.index("sknt")
    out, calm, missing = [], 0, 0
    for _, v in d["hours"].items():
        t, dr, sk = v[it], v[idr], v[isk]
        if dr is None or sk is None or t is None:
            missing += 1
            continue
        if sk <= 0.0:                      # ASOS calm: bearing is undefined, never guess it
            calm += 1
            continue
        out.append((float(dr) % 360.0, float(sk) * KT_TO_MS, float(t)))
    return out, calm, missing


# ----------------------------------------------------------------------------- the sweep
def sweep(mode, wind, verbose=True):
    site, d, bank = load_site(mode)
    emit, bc, outward, march = emission_point(site, d, bank)
    ix, iy = d["intake_m"]
    rad = d["intake_radius_m"]

    # median wind speed over hours whose bearing could matter at all -- MEASURED, not chosen
    speeds = sorted(w[1] for w in wind)
    u_med = speeds[len(speeds) // 2]

    if verbose:
        print("\n" + "=" * 78)
        print("  BANK_MODE = %s" % mode.upper())
        print("=" * 78)
        print("  GEOMETRY AUDIT")
        print("     bank cells %d  (%.0f m2)   obstacle cells %d"
              % (bank.sum(), d["bank_area_m2"], site.obstacle.sum()))
        print("     bank centroid        (%7.1f, %7.1f)   inside a building: %s"
              % (bc[0], bc[1], bool(site.obstacle[int(bc[1] / site.dx), int(bc[0] / site.dx)])))
        print("     outward normal       (%+.3f, %+.3f)" % outward)
        print("     EMISSION POINT       (%7.1f, %7.1f)   marched %.0f m to clear the facade"
              % (emit[0], emit[1], march))
        print("     intake               (%7.1f, %7.1f)   disc radius %.0f m" % (ix, iy, rad))
        print("     facade-to-facade gap %.1f m" % d["facade_gap_m"])
        print("     median KIAD wind     %.2f m/s  (n=%d non-calm hours)  MEASURED" % (u_med, len(wind)))

    rows = []
    t0 = time.time()
    for b in BEARINGS:
        # is the intake downwind of the emission point at all?
        th = math.radians(b + 180.0)
        wx, wy = math.sin(th), math.cos(th)
        downwind = bool(((ix - emit[0]) * wx + (iy - emit[1]) * wy) > 0.0)
        blocked = bool(solver.path_blocked(site, emit, ix, iy, b))
        if blocked:
            rows.append({"bearing": b, "downwind": downwind, "refused": True, "rise_c": None})
            continue
        T = solver.solve(site, AMBIENT, u_med, b, diffusivity=DIFFUSIVITY,
                         downwash_uc=CALIBRATED["downwash_uc"],
                         downwash_exponent=CALIBRATED["downwash_exponent"])
        rise = solver.intake_temperature(T, site, ix, iy, rad, disc=True) - AMBIENT
        rows.append({"bearing": b, "downwind": downwind, "refused": False,
                     "rise_c": round(float(rise), 5)})
    el = time.time() - t0

    ref = [r["refused"] for r in rows]
    dn = [r for r in rows if r["downwind"]]
    dn_ref = [r for r in dn if r["refused"]]
    solved = [r for r in rows if not r["refused"]]
    worst = max(solved, key=lambda r: r["rise_c"]) if solved else None

    if verbose:
        print("\n  SWEEP  (%d bearings, %.1f s, %d solved / %d refused)"
              % (len(rows), el, len(solved), sum(ref)))
        print("     downwind bearings                : %d of %d" % (len(dn), len(rows)))
        print("     REFUSED (building in the path)   : %d of %d  = %.1f %% of all bearings"
              % (sum(ref), len(rows), 100.0 * sum(ref) / len(rows)))
        print("     refused / downwind               : %d of %d  = %.1f %%"
              % (len(dn_ref), len(dn), 100.0 * len(dn_ref) / max(1, len(dn))))
        print("     contiguous refused arcs          : %d" % contiguous_arcs(ref))
        if worst:
            print("     WORST bearing (max intake rise)  : %d deg, rise %.4f C"
                  % (worst["bearing"], worst["rise_c"]))
            print("     naive source->receptor bearing   : 203.7 deg  (|delta| = %.1f deg)"
                  % abs(((worst["bearing"] - 203.7 + 180) % 360) - 180))
            # If every DOWNWIND bearing was refused, the argmax runs over upwind bearings only,
            # where the rise is ~0 by construction. Say so loudly instead of quoting a noise argmax.
            solved_dn = [r for r in solved if r["downwind"]]
            print("     solved bearings that are downwind: %d of %d" % (len(solved_dn), len(solved)))
            print("     rise range over solved bearings  : %.6f .. %.6f C"
                  % (min(r["rise_c"] for r in solved), max(r["rise_c"] for r in solved)))
            if not solved_dn:
                print("     *** every DOWNWIND bearing was refused. The argmax above is taken over")
                print("         UPWIND bearings only, where rise is ~0, so it is NOISE, not a")
                print("         critical bearing. P2 is VACUOUS for this mode -- see the verdicts.")

        # a compact picture of the refusal surface
        print("\n  REFUSAL SURFACE  ( .  computed    X  REFUSED    o computed & upwind )")
        line, lab = [], []
        for r in rows:
            line.append("X" if r["refused"] else ("." if r["downwind"] else "o"))
        for i in range(0, len(rows), 6):
            lab.append("%-6d" % rows[i]["bearing"])
        print("     " + "".join(line))
        print("     " + "".join(lab))

    return {"mode": mode, "rows": rows, "emission_point": list(emit), "bank_centroid": list(bc),
            "outward_normal": list(outward), "march_m": march, "u_median_ms": u_med,
            "n_refused": int(sum(ref)), "n_downwind": len(dn), "n_downwind_refused": len(dn_ref),
            "arcs": contiguous_arcs(ref), "worst": worst, "solve_seconds": round(el, 1)}


def weight_by_wind(res, wind):
    """Wind-weight the refusal surface over 5 real years, plus free-cooling subsets."""
    refused = {r["bearing"]: r["refused"] for r in res["rows"]}
    rise = {r["bearing"]: r["rise_c"] for r in res["rows"]}

    def bin_deg(b):
        return int(round(b / STEP_DEG)) % (360 // STEP_DEG) * STEP_DEG

    out = {}
    for label, sub in [("all_hours", wind)] + \
                      [("below_%.0fC" % c, [w for w in wind if w[2] < c]) for c in CHANGEOVER_C]:
        n = len(sub)
        k = sum(1 for w in sub if refused[bin_deg(w[0])])
        lo, hi = wilson(k, n)
        rs = [rise[bin_deg(w[0])] for w in sub if not refused[bin_deg(w[0])]]
        out[label] = {"n_hours": n, "n_refused": k,
                      "frac_refused": (k / n if n else None),
                      "ci95": [lo, hi],
                      "mean_rise_c_when_computed": (sum(rs) / len(rs) if rs else None),
                      "max_rise_c_when_computed": (max(rs) if rs else None)}
    return out


def main():
    print("=" * 78)
    print("  N-54  THE REFUSAL SURFACE -- real Ashburn geometry, 72 bearings")
    print("=" * 78)
    wind, calm, missing = load_wind()
    print("  KIAD 2021-2025: %d usable hours, %d calm (excluded, bearing undefined), %d missing"
          % (len(wind), calm, missing))
    print("  Pre-registered P1-P5 are in this file's docstring. Conditions are NOT re-defined below.")

    results = {}
    for mode in ("longest", "facing"):
        res = sweep(mode, wind)
        res["wind_weighted"] = weight_by_wind(res, wind)
        results[mode] = res
        w = res["wind_weighted"]
        print("\n  WIND-WEIGHTED REFUSAL  (5 real years, calm excluded)")
        print("     %-14s %8s %9s %9s   %s" % ("subset", "hours", "refused", "frac", "95 % CI"))
        for k, v in w.items():
            print("     %-14s %8d %9d %8.1f %%   [%.3f, %.3f]"
                  % (k, v["n_hours"], v["n_refused"], 100 * v["frac_refused"],
                     v["ci95"][0], v["ci95"][1]))

    # ------------------------------------------------------------------ verdicts
    print("\n" + "=" * 78)
    print("  PRE-REGISTERED VERDICTS")
    print("=" * 78)
    L = results["longest"]
    verdicts = {}

    f_all = L["n_refused"] / len(BEARINGS)
    f_dn = L["n_downwind_refused"] / max(1, L["n_downwind"])
    p1 = (0.0 < f_all < 1.0) and (0.0 < f_dn < 1.0)
    verdicts["P1_non_degenerate_refusal"] = {
        "pass": bool(p1), "frac_all_bearings": f_all, "frac_downwind": f_dn}
    print("  P1 non-degenerate refusal      : %s   refused %.1f %% of bearings, %.1f %% of downwind"
          % ("PASS" if p1 else "**FAIL**", 100 * f_all, 100 * f_dn))

    if L["worst"] is None:
        p2, delta = False, None
        print("  P2 naive bearing is wrong      : **FAIL** -- every bearing refused, no argmax exists")
    else:
        delta = abs(((L["worst"]["bearing"] - 203.7 + 180) % 360) - 180)
        p2 = delta > STEP_DEG
        # VACUITY GUARD. P2's condition is met by arithmetic, but it is only MEANINGFUL if the
        # argmax ran over bearings that can actually carry the plume to the intake. The condition
        # is NOT re-defined here (methodology rule 2) -- it is reported as met AND vacuous.
        vac = not any(r["downwind"] for r in L["rows"] if not r["refused"])
        print("  P2 naive bearing is wrong      : %s   worst %d deg vs naive 203.7 deg, |delta| %.1f deg"
              % ("PASS" if p2 else "**FAIL -- retract section 4.3**", L["worst"]["bearing"], delta))
        if vac:
            print("     ^^ VACUOUS for mode=longest: no solved bearing is downwind, so this argmax")
            print("        is noise over upwind bearings. Condition met arithmetically, worthless")
            print("        physically. Do NOT cite it. The meaningful test is mode=facing.")
    verdicts["P2_naive_bearing_wrong"] = {"pass": bool(p2), "delta_deg": delta,
                                          "vacuous": bool(vac) if L["worst"] else None,
                                          "worst_bearing": (L["worst"] or {}).get("bearing"),
                                          "worst_rise_c": (L["worst"] or {}).get("rise_c")}
    # the same condition, evaluated where it IS meaningful
    Fm = results["facing"]
    if Fm["worst"] is not None and any(r["downwind"] for r in Fm["rows"] if not r["refused"]):
        d2 = abs(((Fm["worst"]["bearing"] - 203.7 + 180) % 360) - 180)
        verdicts["P2_on_facing_mode_where_meaningful"] = {
            "pass": bool(d2 > STEP_DEG), "delta_deg": d2,
            "worst_bearing": Fm["worst"]["bearing"], "worst_rise_c": Fm["worst"]["rise_c"]}
        print("  P2 re-evaluated on mode=facing : %s   worst %d deg vs naive 203.7 deg, |delta| %.1f deg"
              % ("PASS" if d2 > STEP_DEG else "**FAIL -- retract section 4.3**",
                 Fm["worst"]["bearing"], d2))

    p3 = L["arcs"] <= 3
    verdicts["P3_geometric_coherence"] = {"pass": bool(p3), "arcs": L["arcs"]}
    print("  P3 geometric coherence         : %s   %d contiguous refused arc(s)"
          % ("PASS" if p3 else "**FAIL -- suspect ray-casting bug**", L["arcs"]))

    print("  P4 reporting with n and CI     : done -- see the wind-weighted table above")
    print("  P5 facing mode as sensitivity  : done -- reported, never the headline")

    allpass = p1 and p2 and p3
    print("\n  OVERALL: %s" % ("ALL PRE-REGISTERED CONDITIONS MET"
                               if allpass else "AT LEAST ONE CONDITION FAILED -- reported as FAILED"))

    # ---------------------------------------------------------------- amendment note
    if f_dn <= 0.001:
        print("\n  " + "-" * 74)
        print("  AMENDMENT NOTE -- see this file's docstring, section 'AMENDMENT 2026-08-18'")
        print("  " + "-" * 74)
        print("  P1 fails here at 0.0 % refused, the OPPOSITE extreme from the original site's 100 %.")
        print("  That is the INTENDED consequence of re-selecting for a clear plume path, not a defect.")
        print("  P1 conflated 'does path_blocked fire?' with 'is this site clear?'. It answers the")
        print("  second. At a deliberately-clear site, 0 % is the correct answer.")
        print("  NO replacement conditions are registered, because the numbers have now been seen and")
        print("  inventing them would be post-hoc threshold-moving (methodology rule 2). The figures")
        print("  below are MEASUREMENTS, not passes:")
        if L["worst"]:
            print("     usable rise surface : %d of %d downwind bearings solved"
                  % (sum(1 for r in L["rows"] if r["downwind"] and not r["refused"]), L["n_downwind"]))
            print("     critical bearing    : %d deg, rise %.4f C  (naive 203.7 deg, |delta| %.1f deg)"
                  % (L["worst"]["bearing"], L["worst"]["rise_c"],
                     abs(((L["worst"]["bearing"] - 203.7 + 180) % 360) - 180)))
        print("  POSITIVE CONTROL that path_blocked still fires: 36/36 at the old site's longest mode,")
        print("     36/36 at this site's facing mode, and 56 of 145 pairs in refusal_rank.py.")
        F2 = results.get("facing") or {}
        if F2.get("n_downwind") and F2["n_downwind_refused"] == F2["n_downwind"]:
            print("  facing mode here is DEGENERATE (1-cell, 100 m2 bank from a 7 m chamfer) -- do NOT")
            print("     quote it; its purpose was to compensate for longest being unusable at the OLD site.")

    out = _M.geom_path("direction_table.json")
    json.dump({
        "test": "N-54 refusal surface",
        "generated_by": "INTAKE-ARBITER/src/direction_sweep.py",
        "parameters": {"diffusivity_m2s": DIFFUSIVITY, "ambient_c": AMBIENT,
                       "step_deg": STEP_DEG, "downwash_uc": CALIBRATED["downwash_uc"],
                       "downwash_exponent": CALIBRATED["downwash_exponent"],
                       "intake_operator": "disc=True (fixed physical region)",
                       "changeover_limits_c": CHANGEOVER_C},
        # THE STATION IS READ, NOT TYPED. It said "KIAD" unconditionally, on every site's file --
        # a field naming a station the site does not use, which is gotcha #62's lesson ("if a
        # document field describes a code path, compute it from that path") applied to a station id.
        # `n_hours_in_record` is emitted so the partition below can be checked by a reader as well
        # as by audit: usable + calm + missing must equal it exactly.
        # `"K" + station` because `metros` holds the 3-letter code ("IAD") and every other artefact
        # in the tree publishes the 4-letter ICAO id ("KIAD") -- `agent.py` does exactly this. Two
        # spellings of one station across two files is how a reader ends up unable to join them.
        "wind": {"station": "K" + _M.metro()["station"], "metro": _M.metro_key(),
                 "weather_file": os.path.basename(_M.weather_path()),
                 "usable_hours": len(wind), "calm_excluded": calm, "missing": missing,
                 "n_hours_in_record": len(wind) + calm + missing},
        "verdicts": verdicts, "all_pass": bool(allpass),
        "modes": {m: {k: v for k, v in r.items()} for m, r in results.items()},
    }, open(out, "w", encoding="utf-8"), indent=1,
        default=lambda o: (bool(o) if isinstance(o, np.bool_)
                           else float(o) if isinstance(o, np.floating)
                           else int(o) if isinstance(o, np.integer)
                           else str(o)), allow_nan=False)
    print("\n  written: %s" % out)
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
