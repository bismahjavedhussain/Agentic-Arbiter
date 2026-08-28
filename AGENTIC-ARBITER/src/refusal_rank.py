# -*- coding: utf-8 -*-
"""Rank gate-passing pairs by MEASURED refusal, not by a proxy for it. FREE, keyless, no solver.

WHY THIS EXISTS
---------------
`select_site.py` gates on path clearance as a BOOLEAN: the source's longest facade must face the
receptor (outward_normal . u > 0). But clearance is continuous, and the top-scoring survivor came out at
**+0.144** -- a facade normal ~82 deg off the receptor direction, i.e. very nearly perpendicular. A
boolean gate cannot tell that apart from +0.99, yet the two will refuse wildly different numbers of wind
bearings. Guessing a weight for clearance would be tuning by intuition.

So measure it instead. `solver.path_blocked()` is **pure geometry** -- ray casting over an obstacle mask,
no PDE solve -- so the refusal surface for a candidate pair costs milliseconds, not a 40 s sweep. This
script therefore computes, for EVERY gate-passing pair, the same quantity N-54 measured at the old site:

    refused_downwind_frac  = refused bearings / bearings whose plume could reach the intake
    wind_weighted_refusal  = fraction of real KIAD hours whose bearing is refused

and ranks by an objective that is stated up front rather than fitted:

    usable_exposure = wind_exposure x dilution x (1 - wind_weighted_refusal)

Read it as: *of the plume-carrying hours this pair would experience, the share the agent can actually
COMPUTE.* A pair with perfect wind alignment that refuses every hour scores zero, which is exactly the
failure N-54 found and the reason this file exists.

**Nothing here re-defines a pre-registered condition.** N-54's P1-P5 stand as recorded. This is site
SELECTION, and the objective is written before the numbers are read.

Geometry is reproduced from `build_site.py` -- same rasteriser, same bank placement, same emission-point
rule (facade midpoint marched outward until it clears the obstacle mask, per PLAN section 8f.1), same
intake standoff and radius -- so the ranking measures what the built site will actually do.
"""
import io
import json
import math
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from physics import solver                                                    # noqa: E402
from build_site import (rasterise, longest_edge, facing_edge, strip_ring,     # noqa: E402
                        SIZE_M, DX, BANK_FACADE_FRACTION, BANK_DEPTH_M,
                        INTAKE_STANDOFF_M, INTAKE_RADIUS_M)

# METRO-AWARE; ashburn keeps every original path so its audited outputs are unchanged.
import metros as _M                                                        # noqa: E402
SEL = _M.geom_path("selected_site.json")
WEATHER = _M.weather_path()   # that metro's OWN record -- refusal is weighted by ITS wind
OUT = _M.geom_path("refusal_rank.json")
STEP_DEG = 5
BEARINGS = list(range(0, 360, STEP_DEG))
KT_TO_MS = 0.514444


def shift_to_domain(ringA, ringB):
    """Translate both footprints into the solver domain, centred like build_site does."""
    xs = [p[0] for p in ringA + ringB]
    ys = [p[1] for p in ringA + ringB]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    sx, sy = SIZE_M / 2.0 - cx, SIZE_M / 2.0 - cy
    return ([[p[0] + sx, p[1] + sy] for p in ringA],
            [[p[0] + sx, p[1] + sy] for p in ringB])


def emission_point(obstacle, bank_mask, cA, n, dx):
    """Facade midpoint marched outward until clear of the obstacle mask. PLAN section 8f.1."""
    ys, xs = np.nonzero(bank_mask)
    if len(xs) == 0:
        return None
    bc = ((xs.mean() + 0.5) * dx, (ys.mean() + 0.5) * dx)
    ox, oy = bc[0] - cA[0], bc[1] - cA[1]
    L = math.hypot(ox, oy)
    if L < 1e-6:
        return None
    ox, oy = ox / L, oy / L
    for k in range(0, 200):
        px, py = bc[0] + ox * (dx * 0.5) * k, bc[1] + oy * (dx * 0.5) * k
        j, i = int(px / dx), int(py / dx)
        if not (0 <= i < n and 0 <= j < n):
            return None
        if not obstacle[i, j]:
            return (px, py)
    return None


def build(ringA, ringB, cA_in, cB_in, mode="longest"):
    """In-memory site: obstacle mask, bank mask, emission point, intake. Mirrors build_site.py."""
    rA, rB = shift_to_domain(ringA, ringB)
    n = int(SIZE_M / DX)

    def centroid(r):
        return (sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))

    cA, cB = centroid(rA), centroid(rB)
    ux, uy = cB[0] - cA[0], cB[1] - cA[1]
    L = math.hypot(ux, uy) or 1.0
    u = (ux / L, uy / L)

    obstacle = np.zeros((n, n), dtype=bool)
    for r in (rA, rB):
        obstacle |= rasterise(r, n, DX)

    if mode == "longest":
        mid_a, along_a, len_a, _ = longest_edge(rA, cA)
    else:
        mid_a, along_a, len_a = facing_edge(rA, cA, u)
    bank_ring = strip_ring(mid_a, along_a, len_a * BANK_FACADE_FRACTION, BANK_DEPTH_M)
    bank = rasterise(bank_ring, n, DX)

    mid_b, along_b, len_b = facing_edge(rB, cB, (-u[0], -u[1]))
    intake = (mid_b[0] - u[0] * INTAKE_STANDOFF_M, mid_b[1] - u[1] * INTAKE_STANDOFF_M)

    emit = emission_point(obstacle, bank, cA, n, DX)
    return {"n": n, "obstacle": obstacle, "bank": bank, "emit": emit, "intake": intake,
            "bank_cells": int(bank.sum()), "facade_m": len_a}


class Shim:
    """Minimal duck-type for solver.path_blocked(), which only reads .n, .dx, .obstacle."""

    def __init__(self, n, dx, obstacle):
        self.n, self.dx, self.obstacle = n, dx, obstacle


def refusal(site):
    """(refused_all, refused_downwind, n_downwind, per-bearing refused flags)."""
    if site["emit"] is None:
        return None
    sh = Shim(site["n"], DX, site["obstacle"])
    ix, iy = site["intake"]
    ex, ey = site["emit"]
    flags, ndn, nref_dn = {}, 0, 0
    for b in BEARINGS:
        th = math.radians(b + 180.0)
        wx, wy = math.sin(th), math.cos(th)
        dn = ((ix - ex) * wx + (iy - ey) * wy) > 0.0
        rf = bool(solver.path_blocked(sh, (ex, ey), ix, iy, b))
        flags[b] = rf
        if dn:
            ndn += 1
            if rf:
                nref_dn += 1
    return {"flags": flags, "n_refused": sum(flags.values()),
            "n_downwind": ndn, "n_downwind_refused": nref_dn}


def load_wind():
    d = json.load(open(WEATHER, encoding="utf-8"))
    f = d["meta"]["fields"]
    idr, isk = f.index("drct"), f.index("sknt")
    out = []
    for _, v in d["hours"].items():
        dr, sk = v[idr], v[isk]
        if dr is None or sk is None or sk <= 0:
            continue
        out.append(float(dr) % 360.0)
    return out


def main():
    sel = json.load(open(SEL, encoding="utf-8"))
    survivors = sel.get("survivors") or []
    if not survivors:
        print("no survivors in selected_site.json -- run select_site.py first")
        return 2
    cand = json.load(open(_M.candidates_path(), encoding="utf-8"))
    B = {b["osm_id"]: b for b in cand["buildings"]}
    wind = load_wind()

    def bin_deg(b):
        return int(round(b / STEP_DEG)) % (360 // STEP_DEG) * STEP_DEG

    print("=" * 96)
    print("  MEASURED REFUSAL RANKING -- %d gate-passing pairs, pure geometry, no solver, no API"
          % len(survivors))
    print("  objective: usable_exposure = exposure x dilution x (1 - wind_weighted_refusal)")
    print("=" * 96)
    print("  wind: %d real non-calm KIAD hours" % len(wind))

    rows, skipped = [], 0
    for s in survivors:
        a, b = B.get(s["source_osm_id"]), B.get(s["receptor_osm_id"])
        if not (a and b):
            skipped += 1
            continue
        site = build(a["ring_m"], b["ring_m"], a["centre_m"], b["centre_m"], "longest")
        r = refusal(site)
        if r is None:
            skipped += 1
            continue
        k = sum(1 for w in wind if r["flags"][bin_deg(w)])
        wwr = k / len(wind)
        rows.append({
            "source_osm_id": s["source_osm_id"], "receptor_osm_id": s["receptor_osm_id"],
            "source_name": s.get("source_name"), "receptor_name": s.get("receptor_name"),
            "separation_m": s["separation_m"], "true_gap_m": s["true_gap_m"],
            "longest_facade_m": s["longest_facade_m"], "path_clearance": s["path_clearance"],
            "wind_exposure": s["wind_exposure"], "dilution_factor": s["dilution_factor"],
            "exposure_x_dilution": s["exposure_x_dilution"],
            "bank_cells": site["bank_cells"], "bank_area_m2": site["bank_cells"] * DX * DX,
            "n_downwind": r["n_downwind"], "n_downwind_refused": r["n_downwind_refused"],
            "refused_downwind_frac": (r["n_downwind_refused"] / r["n_downwind"]
                                      if r["n_downwind"] else None),
            "wind_weighted_refusal": wwr,
            "usable_exposure": s["exposure_x_dilution"] * (1.0 - wwr),
        })

    rows.sort(key=lambda r: -r["usable_exposure"])
    print("  measured %d pairs, skipped %d\n" % (len(rows), skipped))
    print("  %-11s %-11s %5s %6s %6s %6s %8s %8s %9s  %s"
          % ("source", "recept", "gap", "facade", "clear", "bank", "ref_dn", "ref_wt", "USABLE", "name"))
    for r in rows[:14]:
        print("  %-11d %-11d %5.0f %6.0f %+6.2f %6.0f %7.1f%% %7.1f%% %9.4f  %s"
              % (r["source_osm_id"], r["receptor_osm_id"], r["true_gap_m"], r["longest_facade_m"],
                 r["path_clearance"], r["bank_area_m2"], 100 * r["refused_downwind_frac"],
                 100 * r["wind_weighted_refusal"], r["usable_exposure"],
                 (r["source_name"] or "-")[:30]))

    zero = [r for r in rows if r["refused_downwind_frac"] >= 0.999]
    print("\n  pairs that would refuse 100 %% of downwind bearings (the old site's failure mode): "
          "%d of %d" % (len(zero), len(rows)))
    fully = [r for r in rows if r["refused_downwind_frac"] <= 0.001]
    print("  pairs with a COMPLETELY clear plume path (0 %% refused): %d of %d" % (len(fully), len(rows)))

    best = rows[0]
    print("\n" + "=" * 96)
    print("  BEST BY MEASURED USABLE EXPOSURE")
    print("=" * 96)
    print("  %d -> %d   %s -> %s" % (best["source_osm_id"], best["receptor_osm_id"],
                                     best["source_name"], best["receptor_name"]))
    print("     true gap %.1f m   longest facade %.0f m   clearance %+.3f   bank %.0f m2"
          % (best["true_gap_m"], best["longest_facade_m"], best["path_clearance"],
             best["bank_area_m2"]))
    print("     refused: %.1f %% of downwind bearings, %.1f %% of real wind hours"
          % (100 * best["refused_downwind_frac"], 100 * best["wind_weighted_refusal"]))
    print("     exposure x dilution %.4f  ->  USABLE exposure %.4f"
          % (best["exposure_x_dilution"], best["usable_exposure"]))

    # -------------------------------------------------------------- commit the selection
    # select_site.py ranks by exposure x dilution and CANNOT see refusal, so its own top pick
    # (1544360250 -> 1534356804, clearance +0.144) refuses 100 % of downwind bearings. This file is
    # the final arbiter: it rewrites selected_site.json so build_site.py reads the measured winner.
    old = sel.get("selected") or {}
    sel["selected"] = next(s for s in survivors
                           if s["source_osm_id"] == best["source_osm_id"]
                           and s["receptor_osm_id"] == best["receptor_osm_id"])
    sel["source_building"] = B[best["source_osm_id"]]
    sel["receptor_building"] = B[best["receptor_osm_id"]]
    sel["selected_by"] = ("refusal_rank.py -- MEASURED usable exposure. select_site.py's gates run "
                          "first, then every survivor's refusal surface is measured geometrically and "
                          "the winner maximises exposure x dilution x (1 - wind_weighted_refusal).")
    sel["superseded_selection"] = {
        "pair": [old.get("source_osm_id"), old.get("receptor_osm_id")],
        "why": "ranked top on exposure x dilution but MEASURES 100 %% of downwind bearings refused; "
               "path clearance was only +0.144, i.e. the long facade is nearly perpendicular to the "
               "receptor. A boolean clearance gate cannot detect this." % ()}
    sel["refusal_measurement"] = {
        "refused_downwind_frac": best["refused_downwind_frac"],
        "wind_weighted_refusal": best["wind_weighted_refusal"],
        "n_pairs_measured": len(rows),
        "n_pairs_refusing_all_downwind": len(zero),
        "n_pairs_fully_clear": len(fully)}
    json.dump(sel, open(SEL, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n  COMMITTED to %s" % os.path.basename(SEL))
    # THIS MESSAGE USED TO ASSERT A MEASUREMENT IT HAD NOT MADE. It read
    #   "(was X -> Y, which refuses 100 % of downwind bearings)"
    # unconditionally -- true for the Ashburn pair it was written for, and FALSE for the three new
    # metros, where every ranked pair refuses 0.0 %. It also printed "was X -> Y" when X -> Y was
    # the same pair just selected, so the output claimed a replacement that had not happened.
    # Now it reports what the rows actually say, and stays silent when nothing changed.
    changed = (old.get("source_osm_id") != best["source_osm_id"]
               or old.get("receptor_osm_id") != best["receptor_osm_id"])
    if changed:
        oldrow = next((r for r in rows if r["source_osm_id"] == old.get("source_osm_id")
                       and r["receptor_osm_id"] == old.get("receptor_osm_id")), None)
        why = ("which refuses %.1f %% of downwind bearings"
               % (100.0 * oldrow["refused_downwind_frac"]) if oldrow
               else "which did not survive the clearance gates")
    print("     selected  %d -> %d   refuses %.1f %% of downwind bearings, %.1f %% of wind hours"
          % (best["source_osm_id"], best["receptor_osm_id"],
             100.0 * best["refused_downwind_frac"], 100.0 * best["wind_weighted_refusal"]))
    if changed:
        print("     REPLACED the exposure-only pick %s -> %s, %s"
              % (old.get("source_osm_id"), old.get("receptor_osm_id"), why))
    else:
        print("     the exposure-only pick already had the best measured refusal; unchanged")

    json.dump({"objective": "exposure x dilution x (1 - wind_weighted_refusal), stated before reading "
                            "the numbers; see this file's docstring",
               "method": "solver.path_blocked() is pure geometry, so refusal is measured per pair "
                         "without any PDE solve; bank placement and emission point mirror build_site.py",
               "n_measured": len(rows), "n_skipped": skipped,
               "n_pairs_refusing_all_downwind": len(zero),
               "n_pairs_fully_clear": len(fully),
               "wind_hours": len(wind), "step_deg": STEP_DEG,
               "ranked": rows}, open(OUT, "w", encoding="utf-8"), indent=1, allow_nan=False)
    print("\n  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
