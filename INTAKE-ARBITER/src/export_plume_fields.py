# -*- coding: utf-8 -*-
"""EXPORT REAL SOLVED PLUME FIELDS, one per wind bearing, for the 360-degree site view.

    METRO=dulles python export_plume_fields.py
    python export_plume_fields.py --all

ZERO API CALLS. Writes ../demo/plume_field_<metro>_<mode>.json

--------------------------------------------------------------------------------------------
WHY A SOLVED FIELD AND NOT A DRAWN PLUME
--------------------------------------------------------------------------------------------
The site view needs to show where the exhaust actually goes as the wind turns. The tempting way is
to draw a tapering cone from the condenser bank and tint it by the measured rise -- and it would be
a fiction. This project's own record is explicit that our plume SHAPE is the outlier: N-35 measured
a spread exponent of 0.805 on 67 Prairie Grass field experiments against our sqrt(x), so at 60-165 m
our plume is too WIDE and we UNDER-predict rise by 5-25 % (gotcha #45). Hand-drawing a prettier
plume would hide exactly the limitation the documentation is careful to state.

So this dumps the FIELD THE SOLVER ACTUALLY COMPUTES -- the same `solver.solve()` that produced every
published rise number, on the same rasterised OSM geometry, through the same verified rebuild
(`direction_sweep.load_site`, which refuses to continue if the bank cell count disagrees with the
JSON). What the interface renders is then a measurement, not an illustration, and its flaws are the
model's stated flaws rather than new ones invented in a canvas.

--------------------------------------------------------------------------------------------
WHY IT IS SMALL ENOUGH TO SHIP
--------------------------------------------------------------------------------------------
A 200x200 field at 36 bearings is 1.44 M numbers, which as JSON text is unusable in a browser. Two
reductions, both stated in the output:

  CROP    to the bounding box of both footprints plus MARGIN_M, because the plume between the halls
          is the entire question and the rest of the 2 km domain is ambient.
  QUANTISE the RISE (T - ambient, never the absolute temperature) to one byte over 0..q_max_c, with
          the scale written into the file so the browser reconstructs degrees rather than guessing.

Quantisation is a DISPLAY compression and is applied to nothing a decision depends on -- the decision
path reads `rise_table_*.json` at full precision (gotcha #44: never round what a comparison depends
on). The published rise for the critical bearing is carried in this file too, so a viewer can check
the rendered field against the audited number.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")
sys.path.insert(0, HERE)
import metros as M                                                            # noqa: E402
from physics import solver                                                    # noqa: E402
from direction_sweep import load_site, emission_point                         # noqa: E402

# 5 DEGREES, MATCHING direction_table.json EXACTLY -- 72 bearings.
# This was 10 deg (36 bearings) and the audited critical bearings fell in the gaps: Ashburn 255,
# Dulles 265. The panel must be able to render the field AT the bearing whose rise is published,
# or the picture and the number can never be checked against each other. Doubling the file is the
# right trade for making every dial position renderable.
STEP_DEG = 5
MARGIN_M = 160.0              # air kept around the footprints, enough to see the plume travel
AMBIENT_C = 30.0              # the reference ambient the rise tables are solved at (agent.AMB_REF)
BYTE_MAX = 250                # leave headroom below 255 so clipping is visible, not silent


def crop_window(d, n, dx):
    xs = [p[0] for p in d["source_ring_m"] + d["receptor_ring_m"]]
    ys = [p[1] for p in d["source_ring_m"] + d["receptor_ring_m"]]
    j0 = max(0, int((min(xs) - MARGIN_M) / dx))
    j1 = min(n, int(math.ceil((max(xs) + MARGIN_M) / dx)))
    i0 = max(0, int((min(ys) - MARGIN_M) / dx))
    i1 = min(n, int(math.ceil((max(ys) + MARGIN_M) / dx)))
    return i0, i1, j0, j1


def run(mkey, mode="longest"):
    site, d, bank = load_site(mode)          # verified rebuild; raises on any mismatch
    n, dx = site.n, site.dx
    # emission_point returns (point, bank_centroid, outward_normal, march_distance) -- the march
    # distance is the "ray that starts inside a building" fix from gotcha #36, so it is carried
    # through into the file rather than discarded.
    (ex, ey), bank_c, outward, march_m = emission_point(site, d, bank)
    i0, i1, j0, j1 = crop_window(d, n, dx)
    tbl = json.load(open(M.geom_path("direction_table.json"), encoding="utf-8"))
    u = float(tbl["modes"][mode]["u_median_ms"])

    # 🔴 THE SOLVER PARAMETERS COME FROM THE TABLE THIS FIELD IS CHECKED AGAINST, NOT FROM HERE.
    #    They used to be partly implicit -- `solver.solve(site, AMBIENT_C, u, b, downwash_uc=8.0)`
    #    left `diffusivity` at the function's own default of 8.0 while every published rise number
    #    is solved at the MEASURED 7.40 (N-33 median, direction_sweep.DIFFUSIVITY). A higher
    #    diffusivity spreads the plume more, so the shipped field read LOW at every site: measured
    #    across 26 exported fields the disc mean was below its own audited rise EVERY TIME, by
    #    0.06 % to 2.61 %, and CA_way_209087373 and IL_way_1446350370 crossed audit's 2 % gate.
    #    A one-signed error across 26 sites is a parameter, not noise.
    #    Reading `parameters` closes it permanently: if the sweep is ever re-run with different
    #    physics, the field follows automatically instead of silently disagreeing.
    P = tbl["parameters"]
    amb = float(P["ambient_c"])
    if int(P["step_deg"]) != STEP_DEG:
        raise SystemExit("direction_table was solved at %s deg, this exporter at %d -- the audited "
                         "critical bearing may not exist in the field"
                         % (P["step_deg"], STEP_DEG))

    bearings = list(range(0, 360, STEP_DEG))
    print("   %-11s %-8s  %d bearings at the MEDIAN measured wind %.2f m/s, crop %dx%d cells"
          % (mkey, mode, len(bearings), u, i1 - i0, j1 - j0))
    print("      solved at the TABLE's own parameters: diffusivity %.2f m2/s, ambient %.1f C, "
          "downwash uc %.1f exp %.2f"
          % (P["diffusivity_m2s"], amb, P["downwash_uc"], P["downwash_exponent"]))

    t0 = time.time()
    fields, peak = {}, 0.0
    for b in bearings:
        T = solver.solve(site, amb, u, float(b), diffusivity=float(P["diffusivity_m2s"]),
                         downwash_uc=float(P["downwash_uc"]),
                         downwash_exponent=float(P["downwash_exponent"]))
        rise = np.asarray(T)[i0:i1, j0:j1] - amb
        fields[b] = rise
        peak = max(peak, float(rise.max()))
    q = (peak / BYTE_MAX) if peak > 0 else 1.0

    out_fields = {}
    clipped = 0
    for b, rise in fields.items():
        v = np.clip(np.rint(rise / q), 0, 255).astype(np.uint8)
        clipped += int((rise / q > 255).sum())
        out_fields[str(b)] = v.flatten().tolist()

    dt = tbl["modes"][mode]
    obj = {
        "generated_by": "INTAKE-ARBITER/src/export_plume_fields.py",
        "api_calls_made": 0,
        "metro": mkey, "metro_label": M.metro(mkey)["label"], "bank_mode": mode,
        "provenance": d["provenance"],
        "solver": ("physics/solver.solve(), the same function, the same rasterised OSM geometry AND "
                   "THE SAME PARAMETERS behind every published rise number -- read from "
                   "direction_table.json's own `parameters` block rather than restated here; site "
                   "rebuilt via direction_sweep.load_site which refuses to continue if the bank "
                   "cell count disagrees with the JSON"),
        # The parameters actually used, copied from the table, so a reader can check that the field
        # and the number it is compared against were solved the same way.
        "solver_parameters": {k: P[k] for k in ("diffusivity_m2s", "ambient_c", "downwash_uc",
                                                "downwash_exponent", "intake_operator")},
        "shape_caveat": ("the plume SPREAD is our sqrt(x) model, which N-35 measured as the OUTLIER "
                         "against an exponent of 0.805 from 67 Prairie Grass experiments: at these "
                         "distances our plume is too WIDE and UNDER-predicts rise by 5-25 %. This "
                         "field shows what the model computes, flaws included -- not a nicer drawing"),
        "ambient_c": amb, "wind_speed_ms": u, "step_deg": STEP_DEG,
        "dx_m": dx, "rows": i1 - i0, "cols": j1 - j0,
        "origin_m": [j0 * dx, i0 * dx],
        "quantisation": {"units": "rise above ambient, degrees C", "scale_c_per_byte": q,
                         "byte_max": BYTE_MAX, "peak_rise_c": peak, "clipped_cells": clipped,
                         "note": ("DISPLAY compression only. Nothing a decision depends on is "
                                  "quantised -- the decision path reads rise_table_*.json at full "
                                  "precision (gotcha #44)")},
        # geometry in the SAME cropped frame, so the browser overlays without re-deriving anything
        "source_ring_m": d["source_ring_m"], "receptor_ring_m": d["receptor_ring_m"],
        "bank_ring_m": d["bank_ring_m"],
        "intake_m": d["intake_m"], "intake_radius_m": d["intake_radius_m"],
        "emission_point_m": [ex, ey],
        "bank_centroid_m": list(bank_c), "outward_normal": list(outward),
        "emission_march_m": march_m,
        "emission_note": ("the plume enters the air at the bank's OUTWARD FACE, marched %.1f m "
                          "clear of the obstacle mask. A ray starting INSIDE a building refuses "
                          "every bearing and looks like a perfect result -- gotcha #36" % march_m),
        # THE RASTERISED OBSTACLE MASK, cropped to the same window. Two reasons it is worth the
        # ~3.6 kB: the browser can draw the buildings EXACTLY as the solver sees them rather than
        # re-rasterising the rings itself (two code paths, one quantity -- gotcha #12), and the
        # intake disc average can exclude obstacle cells the way intake_temperature() does with
        # exclude_obstacles=True. Without it, re-deriving the audited rise from this file agrees
        # only to 1-3 %, and the gap could not be attributed.
        "obstacle_mask": np.asarray(site.obstacle)[i0:i1, j0:j1].astype(np.uint8)
                           .flatten().tolist(),
        "facade_gap_m": d["facade_gap_m"],
        # the audited numbers a viewer can check the picture against
        "critical_bearing_deg": dt["worst"]["bearing"],
        "critical_rise_c": dt["worst"]["rise_c"],
        "n_refused_bearings": dt["n_refused"],
        "refused_bearings": [r["bearing"] for r in dt["rows"] if r["refused"]],
        "measured_rise_by_bearing": {str(r["bearing"]): r["rise_c"] for r in dt["rows"]},
        "fields": out_fields,
    }
    p = os.path.join(DEMO, "plume_field_%s_%s.json" % (mkey, mode))
    json.dump(obj, open(p, "w", encoding="utf-8"), allow_nan=False)
    print("      peak rise %.4f C  scale %.6f C/byte  clipped %d  ->  %s (%.0f KB) in %.1f s"
          % (peak, q, clipped, os.path.basename(p), os.path.getsize(p) / 1024.0,
             time.time() - t0))
    print("      audited critical bearing %s deg at %.5f C -- the render must agree with this"
          % (dt["worst"]["bearing"], dt["worst"]["rise_c"]))
    return 0


def main(argv):
    print("=" * 78)
    print("EXPORT SOLVED PLUME FIELDS -- real solver output, not a drawn cone. Zero API calls.")
    print("=" * 78)
    keys = [k for k in sorted(M.METROS) if M.readiness(k)["offerable"]] if "--all" in argv \
        else [M.metro_key()]
    rc = 0
    for k in keys:
        os.environ["METRO"] = k
        if not os.path.exists(M.geom_path("solver_site_longest.json", k)):
            print("   %-11s no built site -- run build_site.py first" % k)
            continue
        rc |= run(k, "longest")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
