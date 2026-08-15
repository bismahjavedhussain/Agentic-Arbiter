# -*- coding: utf-8 -*-
"""N-28  ---  does the ratio-stability property survive a change of SITE LAYOUT?   FREE, GPU.

WHY THIS TEST EXISTS -- a claim of mine that was overstated

    N-27 concluded: "on the 6 of 8 directions where the geometry is unambiguous, the releasable
    fraction is stable to within 6 percentage points, tested out of sample."

    That was out of sample in the CONSTANTS -- 16 fresh values of the eight unmeasured stubs with a
    new seed. It was NOT out of sample in the GEOMETRY. All 33 configurations used one topology:

        one hall, condensers on its EAST face, one neighbour due EAST at 300 m,
        intake on the neighbour's WEST face, everything on a single axis.

    So "6 of 8" and "6 percentage points" are properties of THAT LAYOUT. Quoting them as general is
    exactly the error N-11 made with the 9 m/s peak -- taking a number produced under one set of
    conditions and speaking as though it held everywhere.

WHAT SHOULD GENERALISE, AND WHAT SHOULD NOT
    NOT the counts. A site with condensers on two faces, or a neighbour off-axis, or no neighbour at
    all, will have a different number of safe directions. That is expected and uninteresting.

    The MECHANISM should generalise, because it is a statement about plumes rather than about a site:
    where the plume clearly misses the intake the ratio is insensitive to how strong the plume is;
    where the plume half-covers the intake, the ratio depends on the magnitude and is not stable.

    That is the hypothesis under test. Six deliberately different layouts, and in each one the same
    question: is the releasable fraction on the UNAMBIGUOUS directions insensitive to the constants?

PASS CONDITIONS, FIXED BEFORE RUNNING
    P1  in EVERY layout, the worst spread of releasable fraction across the constant sweep, taken
        over that layout's unambiguous directions, is < 0.10.
    P2  in EVERY layout, the transition directions are materially worse than the unambiguous ones --
        worst transition spread > 2x worst unambiguous spread. If transitions were equally stable
        the whole "the system knows where it is uncertain" story would be decoration.
    P3  at least 4 of the 6 layouts have >= 3 unambiguous directions. A layout where almost nothing
        is unambiguous is a site where this product simply has little to say, and if that were the
        common case the commercial claim would be much weaker.

    The COUNT of unambiguous directions is reported per layout and is deliberately NOT part of any
    pass condition -- it is expected to vary, and pretending otherwise is what got us here.

RESOLUTION
    24 directions at 15 deg. N-23 measured the plume sector as narrower than the +/-15 deg forecast
    uncertainty, so 45 deg steps (N-27) can straddle a transition without resolving it. Finer steps
    are what make the unambiguous/transition split meaningful rather than an artifact of sampling.
"""
import sys, time
import numpy as np

from common import banner, save_result, verdict
from solver import Site, downwash_fraction, CALIBRATED, assert_intake_clear
import warp_solver as ws

AMB = 30.0
DX = 10.0
STEPS = 800
N_DIRS = 24
DIRECTIONS = tuple(float(d) for d in np.arange(0.0, 360.0, 360.0 / N_DIRS))
N_COND = 30
N_BASE = 120
CAL_EXPO = CALIBRATED["downwash_exponent"]
CAL_UC = CALIBRATED["downwash_uc"]
CAL_EX = CALIBRATED["exchange_s"]

UNAMBIG_HI, UNAMBIG_LO = 0.90, 0.20
MAX_UNAMBIG_SPREAD = 0.10        # P1
MIN_TRANSITION_RATIO = 2.0       # P2
MIN_UNAMBIG_DIRS = 3             # P3
MIN_LAYOUTS_WITH_ENOUGH = 4      # P3

BASE = dict(discharge_k=11.0, exchange_s=CAL_EX, diffusivity=8.0, uc=CAL_UC, intake_r=30.0,
            design_wind=6.0, bank_w=60.0)

# one value per stub, chosen at the ends of the plausible ranges used in N-19/N-27
STUBS = [("discharge_k", [7.8, 13.9]), ("exchange_s", [24.0, 95.0]),
         ("diffusivity", [4.0, 16.0]), ("uc", [5.0, 12.0]),
         ("intake_r", [15.0, 45.0]), ("design_wind", [3.0, 9.0])]


# ---------------------------------------------------------------- layouts
# Each returns (site, intake). Deliberately different topologies, not variations of one.
def layout_east(cfg):
    """L1  the N-27 layout: condensers on the east face, neighbour due east."""
    bw = cfg["bank_w"]
    s = Site(2000.0, DX)
    s.add_building(cx=700, cy=1000, w=200, h=120)
    s.add_condensers(cx=800 + bw / 2.0, cy=1000, w=bw, h=120,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    s.add_building(cx=1100, cy=1000, w=200, h=120)
    return s, (990.0, 1000.0)


def layout_north(cfg):
    """L2  rotated 90 deg: condensers on the NORTH face, neighbour due north."""
    bw = cfg["bank_w"]
    s = Site(2000.0, DX)
    s.add_building(cx=1000, cy=700, w=120, h=200)
    s.add_condensers(cx=1000, cy=800 + bw / 2.0, w=120, h=bw,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    s.add_building(cx=1000, cy=1100, w=120, h=200)
    return s, (1000.0, 990.0)


def layout_diagonal(cfg):
    """L3  neighbour off-axis to the north-east, so no wind direction is exactly aligned."""
    bw = cfg["bank_w"]
    s = Site(2000.0, DX)
    s.add_building(cx=750, cy=750, w=200, h=200)
    s.add_condensers(cx=850 + bw / 2.0, cy=850, w=bw, h=bw,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    s.add_building(cx=1200, cy=1200, w=200, h=200)
    return s, (1080.0, 1080.0)


def layout_two_neighbours(cfg):
    """L4  two receptors, east and north. The intake scored is the EAST one, but the north
    building changes the flow field, so the plume no longer sees an open domain."""
    bw = cfg["bank_w"]
    s = Site(2000.0, DX)
    s.add_building(cx=700, cy=1000, w=200, h=120)
    s.add_condensers(cx=800 + bw / 2.0, cy=1000, w=bw, h=120,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    s.add_building(cx=1100, cy=1000, w=200, h=120)
    s.add_building(cx=800, cy=1350, w=200, h=120)
    return s, (990.0, 1000.0)


def layout_self(cfg):
    """L5  no neighbour at all. The condenser array sits on our own roof and the intake is on the
    far side of the SAME building -- self-recirculation, which is the common real case."""
    bw = cfg["bank_w"]
    s = Site(2000.0, DX)
    s.add_building(cx=1000, cy=1000, w=300, h=200)
    s.add_condensers(cx=1000, cy=1130 + bw / 2.0, w=200, h=bw,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    return s, (1000.0, 1320.0)


def layout_wide_far(cfg):
    """L6  a wide bank and a distant neighbour: a broad, weak plume rather than a narrow strong one."""
    s = Site(2000.0, DX)
    s.add_building(cx=600, cy=1000, w=300, h=200)
    s.add_condensers(cx=810, cy=1000, w=160, h=200,
                     discharge_k=cfg["discharge_k"], exchange_s=cfg["exchange_s"])
    s.add_building(cx=1450, cy=1000, w=300, h=200)
    return s, (1280.0, 1000.0)


LAYOUTS = [("L1 east neighbour", layout_east),
           ("L2 north neighbour", layout_north),
           ("L3 diagonal NE", layout_diagonal),
           ("L4 two neighbours", layout_two_neighbours),
           ("L5 self-recirculation", layout_self),
           ("L6 wide bank, far nbr", layout_wide_far)]


# ---------------------------------------------------------------- machinery
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


def evaluate(layout_fn, cfg, seed):
    site, intake = layout_fn(cfg)
    assert_intake_clear(site, intake[0], intake[1], cfg["intake_r"])
    rng = np.random.default_rng(seed)

    wf, spd, scl = [], [], []
    for d in DIRECTIONS:
        wf += list(d + rng.normal(0, 15.0, N_COND))
        spd += list(np.clip(cfg["design_wind"] + rng.normal(0, 1.0, N_COND), 0.3, 14.0))
        scl += list(rng.uniform(0.65, 1.0, N_COND))
    rises = _batch(site, cfg, wf, spd, scl, intake)

    p90, means = {}, {}
    for k, d in enumerate(DIRECTIONS):
        seg = rises[k * N_COND:(k + 1) * N_COND]
        p90[d] = float(np.percentile(seg, 90))
        means[d] = float(seg.mean())
    worst = max(means, key=lambda d: means[d])

    bwf = list(worst + rng.normal(0, 20.0, N_BASE))
    bspd = list(np.clip(cfg["design_wind"] + rng.normal(0, 2.0, N_BASE), 0.3, 14.0))
    bscl = list(rng.uniform(0.5, 1.0, N_BASE))
    baseline = float(np.percentile(_batch(site, cfg, bwf, bspd, bscl, intake), 99))
    if baseline <= 1e-4:
        return None
    return baseline, {d: 1.0 - p90[d] / baseline for d in DIRECTIONS}, worst


def main():
    banner("N-28  Does ratio stability survive a change of SITE LAYOUT?   [FREE, GPU]")
    if not ws.HAVE_WARP:
        print("   warp-lang unavailable."); return 2
    t0 = time.time()

    configs = [("BASE", dict(BASE))]
    for name, vals in STUBS:
        for v in vals:
            c = dict(BASE); c[name] = v
            configs.append(("%s=%g" % (name, v), c))

    print("   %d layouts x %d constant-configs x (%d dirs x %d + %d) = %s solves"
          % (len(LAYOUTS), len(configs), N_DIRS, N_COND, N_BASE,
             format(len(LAYOUTS) * len(configs) * (N_DIRS * N_COND + N_BASE), ",")))
    print("   %d directions at %.0f deg. N-27 used 8 at 45 deg, which can straddle a transition"
          % (N_DIRS, 360.0 / N_DIRS))
    print("   without resolving it -- N-23 showed the plume sector is narrower than 45 deg.")
    print("   The COUNT of unambiguous directions is expected to differ per layout. The question")
    print("   is whether the STABILITY PROPERTY holds in every one.\n")

    print("   %-22s %7s %9s %9s %11s %11s %7s"
          % ("layout", "worst", "baseline", "unambig", "unambig", "transition", "ratio"))
    print("   %-22s %7s %9s %9s %11s %11s %7s"
          % ("", "dir", "range C", "dirs", "max spread", "max spread", "t/u"))

    results, skipped = [], []
    for lname, fn in LAYOUTS:
        rows = []
        for cname, cfg in configs:
            try:
                got = evaluate(fn, cfg, seed=4242)
            except ValueError as e:
                skipped.append((lname, cname, str(e)[:60])); continue
            if got is None:
                skipped.append((lname, cname, "baseline ~0: no plume reaches the intake")); continue
            base, rel, worst = got
            rows.append({"config": cname, "baseline": base, "worst_dir": worst, "rel": rel})
        if len(rows) < 5:
            print("   %-22s insufficient valid configs (%d)" % (lname, len(rows)))
            continue

        bases = np.array([r["baseline"] for r in rows])
        per = {}
        for d in DIRECTIONS:
            v = np.array([r["rel"][d] for r in rows])
            per[d] = {"mean": float(v.mean()), "spread": float(v.max() - v.min())}
        unamb = [d for d in DIRECTIONS if per[d]["mean"] > UNAMBIG_HI or per[d]["mean"] < UNAMBIG_LO]
        trans = [d for d in DIRECTIONS if d not in unamb]
        wu = max((per[d]["spread"] for d in unamb), default=float("nan"))
        wt = max((per[d]["spread"] for d in trans), default=0.0)
        ratio = wt / wu if wu > 1e-9 else float("inf")
        results.append({"layout": lname, "n_configs": len(rows),
                        "baseline_range": [float(bases.min()), float(bases.max())],
                        "worst_dir_modal": float(np.median([r["worst_dir"] for r in rows])),
                        "n_unambiguous": len(unamb), "n_transition": len(trans),
                        "unambiguous_dirs": [float(d) for d in unamb],
                        "worst_unambiguous_spread": wu, "worst_transition_spread": wt,
                        "transition_over_unambiguous": ratio,
                        "per_direction": {str(d): per[d] for d in DIRECTIONS}})
        print("   %-22s %7.0f %9s %9s %11.3f %11.3f %7s"
              % (lname, results[-1]["worst_dir_modal"],
                 "%.2f-%.2f" % (bases.min(), bases.max()),
                 "%d/%d" % (len(unamb), N_DIRS), wu, wt,
                 "%.1f" % ratio if np.isfinite(ratio) else "inf"))

    if skipped:
        print("\n   skipped %d layout/config combinations:" % len(skipped))
        for ln, cn, why in skipped[:6]:
            print("      %-22s %-16s %s" % (ln, cn, why))

    if not results:
        print("\n   no layout produced enough valid configurations. Cannot conclude.")
        return 2

    wus = [r["worst_unambiguous_spread"] for r in results]
    ratios = [r["transition_over_unambiguous"] for r in results]
    enough = [r for r in results if r["n_unambiguous"] >= MIN_UNAMBIG_DIRS]

    print("\n   RESULT across %d layouts" % len(results))
    print("      worst unambiguous spread, over ALL layouts : %.3f  (threshold %.2f)"
          % (max(wus), MAX_UNAMBIG_SPREAD))
    print("      smallest transition/unambiguous ratio       : %.1f x (threshold %.1f)"
          % (min(ratios), MIN_TRANSITION_RATIO))
    print("      unambiguous direction COUNT by layout       : %s"
          % ", ".join("%d" % r["n_unambiguous"] for r in results))
    print("      -> the count varies, as expected. That is a property of each site, not a claim.")

    p1 = max(wus) < MAX_UNAMBIG_SPREAD
    p2 = min(ratios) > MIN_TRANSITION_RATIO
    p3 = len(enough) >= MIN_LAYOUTS_WITH_ENOUGH
    ok = p1 and p2 and p3

    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE RUNNING")
    print("      P1 unambiguous spread < %.2f in EVERY layout : %s  (worst %.3f)"
          % (MAX_UNAMBIG_SPREAD, p1, max(wus)))
    print("      P2 transitions > %.1fx worse in EVERY layout : %s  (min %.1f x)"
          % (MIN_TRANSITION_RATIO, p2, min(ratios)))
    print("      P3 >= %d layouts with >= %d unambiguous dirs : %s  (%d)"
          % (MIN_LAYOUTS_WITH_ENOUGH, MIN_UNAMBIG_DIRS, p3, len(enough)))
    print("      elapsed %.0f s on the GPU" % (time.time() - t0))

    print("\n   HOW THE CLAIM MUST NOW BE WORDED")
    if ok:
        print("      NOT  \"6 of 8 directions are stable to 6 points\"  -- those numbers belong to")
        print("           ONE layout and vary from %d to %d unambiguous directions across six."
              % (min(r["n_unambiguous"] for r in results),
                 max(r["n_unambiguous"] for r in results)))
        print("      BUT  \"on whichever directions a given site's geometry makes unambiguous, the")
        print("           releasable fraction is insensitive to the unmeasured constants -- under")
        print("           %.0f points across six deliberately different layouts -- while on the"
              % (100 * max(wus)))
        print("           transition directions it is %.0fx worse and the system widens its bound"
              % min(ratios))
        print("           instead of pretending to know. The COUNT is site-specific; the BEHAVIOUR")
        print("           is not.\"")
    else:
        print("      The property does NOT hold across layouts (P1 %s, P2 %s, P3 %s)." % (p1, p2, p3))
        print("      Do not generalise beyond the single layout N-27 tested, and say so explicitly.")

    print()
    verdict(ok,
            "PASS - the stability property is a property of plume geometry, not of one site. Across "
            "six deliberately different layouts the unambiguous directions never spread more than "
            "%.3f, while transition directions spread at least %.1fx more. The COUNT of safe "
            "directions varies (%s) and is reported per site rather than claimed."
            % (max(wus), min(ratios),
               "/".join("%d" % r["n_unambiguous"] for r in results)),
            "FAIL - P1 %s, P2 %s, P3 %s. The stability seen in N-27 does not survive changing the "
            "site layout, so it is a property of that one topology. Restrict every claim to the "
            "tested geometry and state that limitation before anyone asks." % (p1, p2, p3))

    save_result("n28_layouts.json", {
        "motivation": "N-27 varied the CONSTANTS out of sample but held the LAYOUT fixed; its "
                      "'6 of 8 / 6 points' figures were properties of one topology",
        "n_dirs": N_DIRS, "dir_step_deg": 360.0 / N_DIRS, "n_cond": N_COND, "n_base": N_BASE,
        "n_layouts": len(results), "n_configs_per_layout": len(configs),
        "unambig_thresholds": [UNAMBIG_LO, UNAMBIG_HI],
        "thresholds": {"max_unambiguous_spread": MAX_UNAMBIG_SPREAD,
                       "min_transition_ratio": MIN_TRANSITION_RATIO,
                       "min_unambiguous_dirs": MIN_UNAMBIG_DIRS},
        "layouts": results, "skipped": skipped,
        "worst_unambiguous_spread_all": max(wus), "min_transition_ratio_all": min(ratios),
        "p1": p1, "p2": p2, "p3": p3, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
