# -*- coding: utf-8 -*-
"""N-27  ---  is the DIRECTION RATIO invariant to the unmeasured constants?   FREE, GPU.

THE PROBLEM THIS ADDRESSES, STATED AGAINST OUR OWN INTEREST
    The solver converts a FortyGuard 60 m temperature into an equipment intake temperature. It was
    calibrated against field measurements from six power-station air-cooled condensers (N-22,
    held-out RMS 0.126 K on a 0.923 K signal) because no data-centre measurement exists anywhere.
    Nothing downstream corrects for solver error either: the conformal bound is calibrated on
    FortyGuard's forecast residuals, so it covers forecast error and is blind to solver error.

    So the absolute magnitude is genuinely uncertain -- N-19 measured the headline spanning
    0.219-0.940 C, a 4.3x range, across the plausible values of every unmeasured constant.

THE QUESTION THAT MATTERS
    The product does not have to output an absolute temperature. It can output a RELEASABLE
    FRACTION: "of the fixed margin you carry today, today's wind direction lets you release 88 % of
    it." The client already knows their own design margin, so they supply the scale; we only supply
    the ratio.

    A ratio should be far more robust than a level, because a systematic error in discharge
    strength, exchange rate or downwash multiplies the numerator and the denominator alike and
    largely cancels. SHOULD BE. That is a hypothesis, and this file tests it instead of asserting it.

    If the ratio IS invariant, the defensible claim changes shape entirely:
        NOT  "the intake rise is 0.44 C"           -- rests on unvalidated constants
        BUT  "you can release ~88 % of your margin" -- rests only on the geometry of the plume

WHAT IS MEASURED
    Every stub configuration from N-19, and for each one both:
        baseline      p99 intake rise at the worst direction (the fixed margin a no-forecast
                      design must carry)                                    -- an ABSOLUTE level
        releasable(d) 1 - cond_p90(d) / baseline, per wind direction         -- a RATIO
    Then the spread of each across configurations. The absolute is expected to move a lot; the
    question is whether the ratio does.

PASS CONDITIONS, FIXED BEFORE RUNNING
    P1  the ABSOLUTE baseline really is sensitive -- max/min > 2.0 across configurations. If it is
        not, there was no problem to solve and this test is pointless.
    P2  for every direction whose mean releasable fraction exceeds 0.5 (the directions the product
        actually acts on), the spread of that fraction across ALL configurations is < 0.15, i.e.
        under 15 percentage points.
    P3  the ORDERING of directions by releasable fraction is identical in every configuration
        (Kendall-style exact check). If the ranking flips, "which directions are safe" is itself
        an artifact of the constants and the whole framing fails.

    P3 is the strictest and the one that matters most: it asks whether the SIGN of the advice is
    stable, not merely its size.
"""
import sys, time
import numpy as np

from common import banner, save_result, verdict
from solver import Site, downwash_fraction, CALIBRATED, assert_intake_clear
import warp_solver as ws

AMB = 30.0
DX = 10.0
STEPS = 800
DIRECTIONS = (0, 45, 90, 135, 180, 225, 270, 315)
N_BASE = 120
N_COND = 60
CAL_EXPO = CALIBRATED["downwash_exponent"]

BASE = dict(discharge_k=11.0, exchange_s=CALIBRATED["exchange_s"], diffusivity=8.0,
            uc=CALIBRATED["downwash_uc"], separation_m=300.0, bank_w=60.0, intake_r=30.0,
            design_wind=6.0)

SWEEPS = [
    ("discharge_k", [7.8, 13.9], "published 14-25 F discharge range"),
    ("exchange_s", [24.0, 95.0], "calibrated in N-22, swept +/-2x"),
    ("diffusivity", [4.0, 16.0], "INVENTED - no physical basis"),
    ("uc", [5.0, 12.0], "calibrated in N-22"),
    ("separation_m", [250.0, 600.0], "distance to the neighbour; 150 m is DEGENERATE, see below"),
    ("bank_w", [30.0, 120.0], "condenser bank width"),
    ("intake_r", [10.0, 60.0], "intake averaging disc"),
    ("design_wind", [3.0, 9.0], "speed the baseline is taken at"),
]

MIN_RELEASABLE = 0.5        # a direction "the product acts on"
MAX_RATIO_SPREAD = 0.15     # P2
MIN_ABS_RATIO = 2.0         # P1


def build(discharge_k, exchange_s, separation_m, bank_w, **_):
    s = Site(2000.0, DX)
    s.add_building(cx=700, cy=1000, w=200, h=120)
    s.add_condensers(cx=700 + 100 + bank_w / 2.0, cy=1000, w=bank_w, h=120,
                     discharge_k=discharge_k, exchange_s=exchange_s)
    nb = 700 + 100 + separation_m
    s.add_building(cx=nb, cy=1000, w=200, h=120)
    return s, (nb - 110.0, 1000.0)


def rise_of(T, site, ix, iy, radius_m):
    r = max(1, int(radius_m / site.dx))
    i, j = int(iy / site.dx), int(ix / site.dx)
    return float(np.mean(T[max(0, i - r):min(site.n, i + r + 1),
                           max(0, j - r):min(site.n, j + r + 1)])) - AMB


def _batch(site, cfg, wf, spd, scl, intake):
    spd = np.asarray(spd)
    dw = np.array([downwash_fraction(v, cfg["uc"], CAL_EXPO) for v in spd])
    T = ws.solve_batch(site, np.full(len(spd), AMB), spd, np.asarray(wf), np.asarray(scl),
                       diffusivity=cfg["diffusivity"], steps=STEPS, downwash=dw)
    return np.array([rise_of(T[k].astype(np.float64), site, intake[0], intake[1],
                             cfg["intake_r"]) for k in range(len(spd))])


def evaluate(cfg, seed=5):
    """One configuration -> (baseline p99, {direction: releasable fraction}, worst direction).

    The worst direction is found PER CONFIGURATION rather than pinned at 270 deg. Pinning it was an
    error in the first version of this test: the worst direction is a function of the geometry, so
    when the sweep changes the separation or the bank width, 270 deg stops being the maximum and
    other directions come out ABOVE the baseline -- producing negative "releasable" fractions that
    look like an instability in the ratio but are really an instability in my own definition. A
    no-forecast design must cover ITS OWN site's worst direction, so that is what the baseline means.
    """
    site, intake = build(**cfg)
    assert_intake_clear(site, intake[0], intake[1], cfg["intake_r"], label=str(cfg))
    rng = np.random.default_rng(seed)

    # ---- pass 1: conditional ensemble per direction, one batch
    wf, spd, scl = [], [], []
    for d in DIRECTIONS:
        wf += list(d + rng.normal(0, 15.0, N_COND))
        spd += list(np.clip(cfg["design_wind"] + rng.normal(0, 1.0, N_COND), 0.3, 14.0))
        scl += list(rng.uniform(0.65, 1.0, N_COND))
    rises = _batch(site, cfg, wf, spd, scl, intake)

    per_dir, means = {}, {}
    for k, d in enumerate(DIRECTIONS):
        seg = rises[k * N_COND:(k + 1) * N_COND]
        per_dir[d] = float(np.percentile(seg, 90))
        means[d] = float(seg.mean())
    worst = max(means, key=lambda d: means[d])

    # ---- pass 2: the no-forecast baseline at THIS configuration's worst direction
    bwf = list(worst + rng.normal(0, 20.0, N_BASE))
    bspd = list(np.clip(cfg["design_wind"] + rng.normal(0, 2.0, N_BASE), 0.3, 14.0))
    bscl = list(rng.uniform(0.5, 1.0, N_BASE))
    baseline = float(np.percentile(_batch(site, cfg, bwf, bspd, bscl, intake), 99))

    rel = {d: 1.0 - per_dir[d] / max(baseline, 1e-9) for d in DIRECTIONS}
    return baseline, rel, worst


def main():
    banner("N-27  Is the direction RATIO invariant to the unmeasured constants?   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable."); return 2
    t0 = time.time()

    configs = [("BASE (calibrated)", dict(BASE))]
    for name, vals, basis in SWEEPS:
        for v in vals:
            c = dict(BASE); c[name] = v
            configs.append(("%s=%g" % (name, v), c))

    print("   %d configurations x (%d baseline + %d directions x %d) members = %s solves"
          % (len(configs), N_BASE, len(DIRECTIONS), N_COND,
             format(len(configs) * (N_BASE + len(DIRECTIONS) * N_COND), ",")))
    print("   the worst direction is found PER CONFIGURATION. Pinning it at 270 deg was an error")
    print("   in v1: it produced negative releasable fractions that looked like an unstable ratio")
    print("   but were an unstable DEFINITION. See evaluate().")

    print("\n   %-22s %10s %6s   %s" % ("configuration", "baseline C", "worst",
                                        "releasable fraction by wind direction"))
    print("   %-22s %10s %6s   %s" % ("", "", "dir", " ".join("%5d" % d for d in DIRECTIONS)))
    rows = []
    for label, cfg in configs:
        try:
            base, rel, worst = evaluate(cfg)
        except ValueError as e:
            print("   %-22s SKIPPED - %s" % (label, str(e)[:66]))
            continue
        rows.append({"config": label, "baseline": base, "worst_dir": worst,
                     "releasable": {str(d): rel[d] for d in DIRECTIONS}})
        print("   %-22s %10.4f %6.0f   %s"
              % (label, base, worst, " ".join("%5.2f" % rel[d] for d in DIRECTIONS)))

    bases = np.array([r["baseline"] for r in rows])
    abs_ratio = float(bases.max() / max(bases.min(), 1e-9))

    print("\n   1. THE ABSOLUTE LEVEL  (this is what N-19 already showed is fragile)")
    print("      baseline spans %.4f to %.4f C  ->  ratio %.1f x"
          % (bases.min(), bases.max(), abs_ratio))

    print("\n   2. THE RATIO  (the quantity the product could output instead)")
    print("      %10s %9s %9s %9s %9s %s" % ("wind from", "mean", "min", "max", "spread", ""))
    per_dir = {}
    for d in DIRECTIONS:
        v = np.array([r["releasable"][str(d)] for r in rows])
        per_dir[d] = {"mean": float(v.mean()), "min": float(v.min()), "max": float(v.max()),
                      "spread": float(v.max() - v.min())}
        acted = per_dir[d]["mean"] > MIN_RELEASABLE
        print("      %10d %9.3f %9.3f %9.3f %9.3f %s"
              % (d, per_dir[d]["mean"], per_dir[d]["min"], per_dir[d]["max"],
                 per_dir[d]["spread"],
                 ("<- product acts here" if acted else "") +
                 ("   SPREAD TOO WIDE" if acted and per_dir[d]["spread"] > MAX_RATIO_SPREAD else "")))

    acted_dirs = [d for d in DIRECTIONS if per_dir[d]["mean"] > MIN_RELEASABLE]
    worst_spread = max((per_dir[d]["spread"] for d in acted_dirs), default=float("nan"))

    # ---- P3: does the ORDERING of directions ever change?
    orderings = set()
    for r in rows:
        order = tuple(sorted(DIRECTIONS, key=lambda d: -r["releasable"][str(d)]))
        orderings.add(order)
    order_stable = len(orderings) == 1

    print("\n   3. IS THE ADVICE'S ORDERING STABLE?  (the strictest question)")
    print("      distinct direction orderings across %d configurations: %d"
          % (len(rows), len(orderings)))
    if order_stable:
        print("      every configuration ranks the directions identically:")
        print("         %s" % " > ".join("%d" % d for d in list(orderings)[0]))
        print("      So WHICH directions are safe is a property of the geometry, not of the")
        print("      constants. That is the claim worth making in front of a judge.")
    else:
        print("      *** the ranking CHANGES between configurations. 'Which directions are safe'")
        print("          is partly an artifact of unmeasured constants. Do not present the")
        print("          direction advice as robust. Orderings seen:")
        for o in sorted(orderings)[:6]:
            print("            %s" % " > ".join("%d" % d for d in o))

    # ------------------------------------------------------------------ phase 2
    # The pre-registered P2/P3 above FAILED. Inspecting why: the instability is confined to the
    # TRANSITION directions (225, 315), where the plume is half on the intake. The directions where
    # the geometry is unambiguous -- clearly missing or clearly hitting -- barely move at all. That
    # is physically coherent rather than convenient: N-23 independently found the ensemble spread
    # exploding by 13.6x in exactly those transition sectors.
    #
    # But that is a POST-HOC observation on the data that just failed, which is worth very little on
    # its own. So it gets a refined criterion, fixed here, and tested on a FRESH set of stub values
    # and a different random seed. Confirmation out of sample, or it is not claimed.
    UNAMBIG_HI, UNAMBIG_LO = 0.90, 0.20
    REFINED_MAX_SPREAD = 0.10
    HOLDOUT = [
        ("discharge_k", [9.5, 12.5]), ("exchange_s", [35.0, 70.0]),
        ("diffusivity", [6.0, 12.0]), ("uc", [6.5, 10.0]),
        ("separation_m", [350.0, 500.0]), ("bank_w", [45.0, 90.0]),
        ("intake_r", [20.0, 45.0]), ("design_wind", [4.5, 7.5]),
    ]
    unambig = [d for d in DIRECTIONS
               if per_dir[d]["mean"] > UNAMBIG_HI or per_dir[d]["mean"] < UNAMBIG_LO]
    transition = [d for d in DIRECTIONS if d not in unambig]

    print("\n   5. PHASE 2 - a refined claim, pre-registered HERE and tested OUT OF SAMPLE")
    print("      Observation (post-hoc, worth little alone): the instability sits only in the")
    print("      TRANSITION directions %s, where the plume is half on the intake."
          % ", ".join("%d" % d for d in transition))
    print("      Unambiguous directions %s move by at most %.3f."
          % (", ".join("%d" % d for d in unambig),
             max(per_dir[d]["spread"] for d in unambig) if unambig else float("nan")))
    print("      REFINED CONDITION, fixed now: on the unambiguous directions the releasable")
    print("      fraction spreads < %.2f across a FRESH set of stub values and a new seed."
          % REFINED_MAX_SPREAD)

    hrows = []
    for name, vals in HOLDOUT:
        for v in vals:
            c = dict(BASE); c[name] = v
            try:
                base, rel, worst = evaluate(c, seed=808)
            except ValueError as e:
                print("      %-22s SKIPPED - %s" % ("%s=%g" % (name, v), str(e)[:60]))
                continue
            hrows.append({"config": "%s=%g" % (name, v), "baseline": base, "worst_dir": worst,
                          "releasable": {str(d): rel[d] for d in DIRECTIONS}})
    hbases = np.array([r["baseline"] for r in hrows])
    print("\n      HELD-OUT SET: %d configurations, baseline spans %.4f to %.4f C (%.1f x)"
          % (len(hrows), hbases.min(), hbases.max(), hbases.max() / max(hbases.min(), 1e-9)))
    print("      %10s %9s %9s %9s %9s %s" % ("wind from", "mean", "min", "max", "spread", "class"))
    hper = {}
    for d in DIRECTIONS:
        v = np.array([r["releasable"][str(d)] for r in hrows])
        hper[d] = {"mean": float(v.mean()), "min": float(v.min()), "max": float(v.max()),
                   "spread": float(v.max() - v.min())}
        cls = "unambiguous" if d in unambig else "TRANSITION"
        flag = ""
        if d in unambig and hper[d]["spread"] >= REFINED_MAX_SPREAD:
            flag = "  <- BREACHES the refined condition"
        print("      %10d %9.3f %9.3f %9.3f %9.3f %s%s"
              % (d, hper[d]["mean"], hper[d]["min"], hper[d]["max"], hper[d]["spread"], cls, flag))

    hold_worst = max((hper[d]["spread"] for d in unambig), default=float("nan"))
    refined_ok = bool(unambig) and hold_worst < REFINED_MAX_SPREAD
    # the classification must also replicate: a direction called unambiguous must stay unambiguous
    class_ok = all((hper[d]["mean"] > UNAMBIG_HI or hper[d]["mean"] < UNAMBIG_LO) for d in unambig)
    print("\n      refined condition on held-out configs : %s  (worst unambiguous spread %.3f)"
          % (refined_ok, hold_worst))
    print("      classification replicates out of sample: %s" % class_ok)

    p1 = abs_ratio > MIN_ABS_RATIO
    p2 = bool(acted_dirs) and worst_spread < MAX_RATIO_SPREAD
    p3 = order_stable
    ok = p1 and p2 and p3

    print("\n   4. RESULT")
    print("      P1 absolute level IS fragile (>%.1fx)        : %s  (%.1f x)"
          % (MIN_ABS_RATIO, p1, abs_ratio))
    print("      P2 ratio spread < %.2f where product acts    : %s  (worst %.3f over %d dirs)"
          % (MAX_RATIO_SPREAD, p2, worst_spread, len(acted_dirs)))
    print("      P3 direction ordering identical everywhere   : %s" % p3)
    print("      elapsed %.0f s on the GPU" % (time.time() - t0))

    print("\n   WHAT THIS ACTUALLY LICENCES YOU TO SAY")
    if refined_ok and class_ok:
        print("      The BLANKET claim fails: 'the releasable fraction is robust' is not true,")
        print("      because on the transition directions %s it moves by up to %.2f."
              % (", ".join("%d" % d for d in transition),
                 max(per_dir[d]["spread"] for d in transition)))
        print("      The CONDITIONAL claim survives, and it survived out of sample:")
        print("        \"On the %d of 8 directions where the geometry is unambiguous, the fraction"
              % len(unambig))
        print("         of margin you can release is stable to within %.0f percentage points -- even"
              % (100 * hold_worst))
        print("         though the absolute temperature is uncertain by %.1fx. On the %d transition"
              % (abs_ratio, len(transition)))
        print("         directions it is NOT stable, and the system widens its bound there instead")
        print("         of pretending to know.\"")
        print("      That second sentence is worth more than the first: it is the same behaviour")
        print("      N-23 found independently, arrived at from a completely different direction.")
    else:
        print("      Neither the blanket nor the conditional claim is supported. Quote the N-19")
        print("      band, state the solver limitation plainly, and do not reframe the output as a")
        print("      percentage -- the reframing does not rescue it.")

    if ok:
        print("\n   WHAT TO SAY INSTEAD")
        print("      NOT  \"the intake rise is %.2f C\"  -- that moves %.1fx across constants we"
              % (bases[0], abs_ratio))
        print("           have never measured at a data centre.")
        print("      BUT  \"today's wind direction lets you release %.0f %% of the margin you"
              % (100 * per_dir[max(acted_dirs, key=lambda d: per_dir[d]['mean'])]["mean"]))
        print("           already carry\" -- stable to within %.0f points across every one of"
              % (100 * worst_spread))
        print("           those same constants, because the error cancels between numerator and")
        print("           denominator. The CLIENT supplies the scale; we supply the ratio.")

    print()
    verdict(ok,
            "PASS - the absolute level moves %.1fx across the unmeasured constants, but the "
            "RELEASABLE FRACTION moves by at most %.0f percentage points and the ranking of "
            "directions is identical in all %d configurations. So express the output as a fraction "
            "of the client's existing margin, not as a temperature: that claim survives the solver "
            "being wrong about magnitude, which is exactly the weakness we cannot close before a "
            "site measurement exists." % (abs_ratio, 100 * worst_spread, len(rows)),
            "FAIL - P1 %s, P2 %s, P3 %s. The ratio is NOT meaningfully more robust than the level, "
            "so reframing the output as a percentage buys no defensibility. Keep quoting the band "
            "from N-19 and state the solver limitation plainly instead of engineering around it."
            % (p1, p2, p3))

    save_result("n27_ratio.json", {
        "n_configs": len(rows), "base_config": BASE, "worst_dir_per_config": True,
        "n_base": N_BASE, "n_cond": N_COND, "steps": STEPS,
        "rows": rows, "absolute_range": [float(bases.min()), float(bases.max())],
        "absolute_ratio": abs_ratio,
        "per_direction": {str(k): v for k, v in per_dir.items()},
        "acted_directions": acted_dirs, "worst_ratio_spread": worst_spread,
        "n_distinct_orderings": len(orderings), "order_stable": order_stable,
        "orderings": [list(o) for o in orderings],
        "p1_absolute_fragile": p1, "p2_ratio_stable": p2, "p3_order_stable": p3, "pass": ok,
        "phase2": {
            "note": "P2/P3 failed as pre-registered. The refined conditional claim below was fixed "
                    "AFTER seeing that failure but BEFORE the held-out configurations were run.",
            "unambiguous_dirs": unambig, "transition_dirs": transition,
            "unambig_thresholds": [UNAMBIG_LO, UNAMBIG_HI],
            "refined_max_spread": REFINED_MAX_SPREAD,
            "holdout_rows": hrows,
            "holdout_per_direction": {str(k): v for k, v in hper.items()},
            "holdout_worst_unambiguous_spread": hold_worst,
            "refined_ok": refined_ok, "classification_replicates": class_ok}})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
