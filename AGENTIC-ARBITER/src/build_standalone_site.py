# -*- coding: utf-8 -*-
"""THE STANDALONE PATH -- geometry artefacts for a facility with no neighbour.  ZERO API CALLS.

    python build_standalone_site.py <FACILITY_KEY>
    python build_standalone_site.py selftest        # the zero-table invariants, offline

WHY THIS EXISTS
    `NATIONAL-BUILD-PLAN.md` section 0.2 decided, in prose, that a facility with no other tagged
    data centre inside the solver's 600 m validated range is a PASS with the plume "not modelled" --
    not a refusal. No code implemented it. 360 of 639 facilities are exactly that case, and the
    whole downstream chain (`agent` -> `backtest` -> `rolling` -> `money` -> `explain` -> `ticker`
    -> `report`) reads four geometry files that only ever existed for a hand-committed PAIR:

        <k>_selected_site.json        the committed source + receptor buildings
        <k>_solver_site_longest.json  the rasterised site, both rings, the intake
        <k>_solver_site_facing.json   the same with the bank on the end wall
        <k>_direction_table.json      the 72-bearing sweep and this site's wind statistics
        <k>_rise_table_<mode>.json    576 solved intake rises  (agent.rise_table's cache)

    This writes those five, for a single building, with the absent receptor stated as ABSENT rather
    than faked, and the rise identically zero.

--------------------------------------------------------------------------------------------
WHY A ZERO RISE TABLE IS A MEASUREMENT AND NOT A PLACEHOLDER
--------------------------------------------------------------------------------------------
The quantity `rise_table` computes is "the temperature rise at THE NEIGHBOUR'S INTAKE caused by
THIS building's condenser exhaust" -- `build_site.py` puts the bank on the source ring and the
intake outside the receptor's facing facade. With no receptor there is no intake, so the quantity is
not unknown, it is **undefined**, and the honest value of a contribution from a neighbour that does
not exist is zero.

That is a different statement from "the recirculation here is zero", which this project researched
and REJECTED as unsafe-biased (section 0.2), and it is why the reason text every artefact carries
says NOT MODELLED and publishes the measured distance to the nearest other tagged data centre.

⚠ AND THE LIMIT, STATED ONCE HERE AND CARRIED INTO EVERY FILE THIS WRITES: self-recirculation -- a
building's own exhaust re-entering its own intake -- is not modelled at ANY site in this project,
including the three shipped ones, because the operator is neighbour-to-me by construction. It is the
primary case ASHRAE Handbook Ch. 46 addresses. A standalone facility is therefore on exactly the
same footing as Ashburn on that point, which is what makes this path consistent rather than a
concession.

WHAT IS REAL IN THE FILES THIS WRITES, AND WHAT IS NULL
    REAL: this facility's own OSM ring, projected to metres; its own longest facade; a condenser
          bank placed on that facade exactly as `build_site.py` places one; its own centroid; and
          its OWN five-year wind statistics, read from its OWN assigned station's record.
    NULL: `receptor_ring_m`, `receptor_centre_m`, `intake_m`, `facade_gap_m`, and the receptor
          building's osm id and name. Null, never zero and never another building's value -- the
          distinction gotcha #98's family exists to protect.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
GEOM = os.path.join(IA, "data", "geometry")

sys.path.insert(0, HERE)
import metros as M                                                   # noqa: E402
# REUSED UNCHANGED (gotcha #12): the projection, the facade operator, the bank strip and the
# rasteriser are the same ones `build_site.py` uses on the committed pairs. A second implementation
# of "where is the longest wall" would be a second answer waiting to disagree.
from build_site import (BANK_DEPTH_M, BANK_FACADE_FRACTION, DX, INTAKE_RADIUS_M,  # noqa: E402
                        SIZE_M, longest_edge, facing_edge, rasterise, strip_ring)
from fetch_geometry import to_metres                                  # noqa: E402
from measure_national_gaps import is_building_footprint               # noqa: E402

# The same grids `agent.py` maxes the rise over. Imported so a zero table cannot be the wrong shape.
from agent import BEARINGS, SPEED_GRID_MS, STEP_DEG                   # noqa: E402

NOT_MODELLED = ("Recirculation from a neighbour is NOT MODELLED at this facility: there is no other "
                "tagged data centre inside the solver's 600 m validated range, so the quantity the "
                "rise table computes -- the rise at a NEIGHBOUR'S intake -- does not exist here "
                "rather than being unmeasured. This is a statement about the model's domain, NOT a claim that "
                "recirculation here is zero. Self-recirculation (a building's own exhaust "
                "re-entering its own intake) is not modelled at ANY site in this project, "
                "including the three shipped ones.")


def facility(key):
    p = os.path.join(GEOM, "national_registry.json")
    reg = json.load(open(p, encoding="utf-8"))["facilities"]
    if key not in reg:
        raise SystemExit("%r is not in the national registry" % key)
    f = reg[key]
    if f["kind"] != "standalone":
        raise SystemExit("%r is %r, not 'standalone'. This module is only for the no-neighbour "
                         "path; a paired facility runs the existing, unmodified funnel."
                         % (key, f["kind"]))
    return f


def rings_for(f):
    """This facility's own BUILDING footprints, in lat/lon. Parcels excluded."""
    rings = json.load(open(os.path.join(GEOM, "national_geometry.json"),
                           encoding="utf-8"))["rings"]
    out = []
    for m in f["members"]:
        r = rings.get(m)
        if r and is_building_footprint(r):
            out.append((m, r["geometry"], (r.get("tags") or {}).get("name")))
    if not out:
        raise SystemExit("no building footprint for this facility -- it is boundary_only")
    # The LARGEST building is the one the plant is modelled on: it is the one with a facade long
    # enough to host a condenser bank, and for a merged two-hall structure it is the whole thing.
    out.sort(key=lambda t: -_ring_area_m2(t[1]))
    return out


def _ring_area_m2(g):
    la = sum(p[0] for p in g) / len(g)
    mlat, mlon = 111132.0, 111320.0 * math.cos(math.radians(la))
    pts = [(p[1] * mlon, p[0] * mlat) for p in g]
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def local_ring(g, lat0, lon0):
    """lat/lon ring -> metres, centred so the building sits in the middle of the solver domain."""
    m = to_metres([{"lat": p[0], "lon": p[1]} for p in g], lat0, lon0)
    cx = sum(x for x, _ in m) / len(m)
    cy = sum(y for _, y in m) / len(m)
    half = SIZE_M / 2.0
    return [(x - cx + half, y - cy + half) for x, y in m]


def solver_site(ring_m, mode):
    """The `solver_site_<mode>.json` a standalone facility needs.

    The BANK IS REAL -- placed on this building's own longest facade (or end wall in `facing` mode)
    by the same operators `build_site.py` uses, and rasterised on the same grid, so `bank_cells` and
    `bank_area_m2` are measurements of this facility. What is null is everything that requires a
    SECOND building: the receptor ring, its centroid, and the intake that would sit outside it.
    """
    n = int(SIZE_M / DX)
    c = (sum(x for x, _ in ring_m) / len(ring_m), sum(y for _, y in ring_m) / len(ring_m))
    if mode == "facing":
        # No receptor to face, so `facing_edge` has no direction to be given. The honest analogue is
        # the SHORT end wall -- which is what `facing` means physically (the bank on an end wall
        # rather than the long facade) -- taken as the edge most nearly perpendicular to the longest.
        mid, along, ln, out_n = longest_edge(ring_m, c)
        perp = (-along[1], along[0])
        mid = (c[0] + perp[0] * 0.0, c[1] + perp[1] * 0.0)
        along, ln = perp, ln * 0.35            # a short wall, stated as a sensitivity placement
        out_n = perp
    else:
        mid, along, ln, out_n = longest_edge(ring_m, c)
    inward = (-out_n[0], -out_n[1])
    bank_centre = (mid[0] + inward[0] * BANK_DEPTH_M / 2.0,
                   mid[1] + inward[1] * BANK_DEPTH_M / 2.0)
    bank_ring = strip_ring(bank_centre, along, ln * BANK_FACADE_FRACTION, BANK_DEPTH_M)
    bank_cells = int(rasterise(bank_ring, n, DX).sum())
    return {
        "domain": {"size_m": SIZE_M, "dx_m": DX, "n": n},
        "source_ring_m": [list(p) for p in ring_m],
        "receptor_ring_m": None,
        "bank_ring_m": [list(p) for p in bank_ring],
        "source_centre_m": list(c),
        "receptor_centre_m": None,
        "intake_m": None,
        "intake_radius_m": INTAKE_RADIUS_M,
        "bank_cells": bank_cells,
        "bank_area_m2": bank_cells * DX * DX,
        "bank_mode": mode,
        # READ DIRECTLY by `agent.run_all` (not through the `geometry` sub-dict) and published into
        # `trace.site.facade_gap_m`, which `report.py` prints on page 1 of the PDF and
        # `audit.check_sites_actually_differ` compares across sites. NULL, because the gap this
        # names is the distance a plume crosses between TWO facades and there is only one here.
        "facade_gap_m": None,
        "standalone": True,
        "why_receptor_is_null": NOT_MODELLED,
    }


def zero_rise_table(mode, ring_m):
    """A 72 x 8 table of zeros, in the exact schema `agent.rise_table`'s cache reads.

    Writing this file is what stops `rise_table()` reaching for `solver_site_*.json` and the GPU:
    it returns the cache when present. So a standalone facility costs ZERO solves, which is also
    the physically correct cost -- there is nothing to solve.
    """
    c = (sum(x for x, _ in ring_m) / len(ring_m), sum(y for _, y in ring_m) / len(ring_m))
    mid, along, ln, out_n = longest_edge(ring_m, c)
    return {
        "mode": mode,
        "device": "not solved -- no receptor intake exists to compute a rise at",
        "solve_seconds": 0.0,
        "n_solves": 0,
        "emission_point_m": [mid[0] + out_n[0] * BANK_DEPTH_M, mid[1] + out_n[1] * BANK_DEPTH_M],
        "march_m": BANK_DEPTH_M,
        # NOTHING IS REFUSED. A refusal means "a building lies on the source-to-intake path and the
        # solver will not quote a rise it cannot stand behind". With no intake there is no path, so
        # an empty refusal set is correct -- and it must not be confused with "every bearing is
        # clear", which is a claim about a plume that was never computed.
        "refused": [],
        "n_downwind": 0,
        "n_downwind_refused": 0,
        "max_rise_c": 0.0,
        # 🔴 NULL, NOT 0.0. A bearing of 0 degrees is due north -- a real direction. Publishing 0.0
        # would put "the worst bearing is north" into the trace, the dial and the PDF for 360
        # facilities, which is a fabricated fact. `argmax` of an all-zero table returns index 0 and
        # that is exactly how it would have happened.
        "max_rise_bearing": None,
        "max_rise_speed_ms": None,
        "mean_rise_c": 0.0,
        "bearings": [float(b) for b in BEARINGS],
        "speeds": list(SPEED_GRID_MS),
        "rise": [[0.0] * len(SPEED_GRID_MS) for _ in BEARINGS],
        "standalone": True,
        "why_zero": NOT_MODELLED,
    }


def wind_block(key):
    """This facility's OWN five-year wind statistics, from its OWN assigned station.

    Imported from `direction_sweep.load_wind`, which reads `metros.weather_path()` -- so it resolves
    through the station THIS facility was assigned by measurement. The three counts must partition
    the record exactly; `audit.check_wind_is_this_sites_own` asserts that identity, and it exists
    because a literal `kiad_hourly_2021_2025.json` once gave every site Virginia's wind.
    """
    import direction_sweep as DS
    wind, calm, missing = DS.load_wind()
    wpath = M.weather_path(key)
    n_hours = len(json.load(open(wpath, encoding="utf-8"))["hours"])
    speeds = sorted(s for _, s, _ in wind)
    return {
        "station": "K" + M.metro(key)["station"],
        "metro": key,
        "weather_file": os.path.basename(wpath),
        "usable_hours": len(wind),
        "calm_excluded": calm,
        "missing": missing,
        "n_hours_in_record": n_hours,
    }, (speeds[len(speeds) // 2] if speeds else 0.0)


def direction_table(key, ring_m, u_median):
    wb, _ = wind_block(key)
    rows = [{"bearing": int(b), "downwind": False, "refused": False, "rise_c": 0.0}
            for b in BEARINGS]
    c = (sum(x for x, _ in ring_m) / len(ring_m), sum(y for _, y in ring_m) / len(ring_m))
    mid, along, ln, out_n = longest_edge(ring_m, c)
    per_mode = {
        "mode": None, "rows": rows,
        "emission_point": [mid[0] + out_n[0] * BANK_DEPTH_M, mid[1] + out_n[1] * BANK_DEPTH_M],
        "bank_centroid": list(mid), "outward_normal": list(out_n),
        "march_m": BANK_DEPTH_M, "u_median_ms": u_median,
        "n_refused": 0, "n_downwind": 0, "n_downwind_refused": 0, "arcs": 0,
        "worst": None,
        "solve_seconds": 0.0,
        "wind_weighted": {"all_hours": {"n_hours": wb["usable_hours"], "n_refused": 0,
                                        "frac_refused": 0.0}},
        "standalone": True, "why_zero": NOT_MODELLED,
    }
    return {
        "test": "N-54 refusal surface -- NOT RUN, no receptor intake exists",
        "generated_by": "AGENTIC-ARBITER/src/build_standalone_site.py",
        "parameters": {"step_deg": STEP_DEG, "intake_operator": "none -- no receptor",
                       "standalone": True},
        "wind": wb,
        # The pre-registered conditions P1-P3 are about a REFUSAL SURFACE. There is no surface here,
        # so they are recorded as not-applicable rather than as passes. A skipped gate reported as a
        # pass is gotcha #74, and `all_pass: true` on a sweep that never ran would be exactly that.
        "verdicts": {"P1_non_degenerate_refusal": "not_applicable_no_intake",
                     "P2_naive_bearing_wrong": "not_applicable_no_intake",
                     "P3_geometric_coherence": "not_applicable_no_intake"},
        "all_pass": None,
        "modes": {m: dict(per_mode, mode=m) for m in ("longest", "facing")},
    }


def selected_site(key, f, blds, ring_m):
    osm, geom, name = blds[0]
    lat0 = sum(p[0] for p in geom) / len(geom)
    lon0 = sum(p[1] for p in geom) / len(geom)
    return {
        "generated_by": "AGENTIC-ARBITER/src/build_standalone_site.py",
        "api_calls_made": 0,
        "selected": {
            "source_osm_id": int(osm.split("/")[1]),
            "receptor_osm_id": None,
            "source_name": name,
            "receptor_name": None,
            "facade_gap_m": None,
            "centroid_separation_m": None,
        },
        "source_building": {
            "osm_id": int(osm.split("/")[1]), "name": name,
            "centre_latlon": [lat0, lon0], "ring_latlon": geom,
        },
        # PRESENT AND EXPLICITLY NULL. Absent keys would make every consumer raise; another
        # building's values would be gotcha #98. A null-object that says WHY is the third option and
        # the only honest one.
        "receptor_building": {
            "osm_id": None, "name": None, "centre_latlon": None, "ring_latlon": None,
            "why_absent": NOT_MODELLED,
        },
        "survivors": [],
        "standalone": True,
        "kind": f["kind"],
        "nearest_other_tagged_dc_m": f["plume"]["nearest_other_tagged_dc_m"],
        "why_no_pair": f["plume"]["reason"],
    }


def selftest():
    ok = True

    def t(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("   [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))

    sq = [(400.0, 400.0), (600.0, 400.0), (600.0, 500.0), (400.0, 500.0)]
    zt = zero_rise_table("longest", sq)
    t("rise table is the shape agent.rise_table expects",
      len(zt["rise"]) == len(BEARINGS) and len(zt["rise"][0]) == len(SPEED_GRID_MS),
      "%dx%d" % (len(zt["rise"]), len(zt["rise"][0])))
    t("every rise is exactly zero", all(v == 0.0 for row in zt["rise"] for v in row))
    t("nothing is refused (no intake means no blocked path)", zt["refused"] == [])
    t("worst bearing is NULL, not 0 degrees -- 0 is due north, a real claim",
      zt["max_rise_bearing"] is None, repr(zt["max_rise_bearing"]))
    t("the table says it was not solved", "not solved" in zt["device"])
    t("the reason says NOT MODELLED and refuses the zero claim",
      "NOT MODELLED" in zt["why_zero"] and "NOT a claim that" in zt["why_zero"])
    t("the reason states the self-recirculation limit",
      "own exhaust re-entering its own intake" in zt["why_zero"])
    ss = solver_site(sq, "longest")
    t("solver site keeps the receptor NULL, never zero",
      ss["receptor_ring_m"] is None and ss["receptor_centre_m"] is None
      and ss["intake_m"] is None)
    t("the condenser bank is REAL and rasterised on this building",
      ss["bank_cells"] > 0 and ss["bank_area_m2"] > 0, "%d cells" % ss["bank_cells"])
    t("every key agent.py reads is present",
      all(k in ss for k in ("domain", "source_ring_m", "receptor_ring_m", "bank_ring_m",
                            "source_centre_m", "receptor_centre_m", "intake_m",
                            "intake_radius_m", "bank_cells", "bank_area_m2", "bank_mode")))
    # The direction table needs a real weather record, so its invariants are asserted on a BUILT
    # site by `main()` (the wind-partition assert) and by audit check 6e -- not faked here.
    print("\n   SELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    if argv and argv[0] == "selftest":
        return selftest()
    if not argv:
        raise SystemExit("name a standalone facility key, or 'selftest'")
    key = argv[0]
    f = facility(key)
    blds = rings_for(f)
    osm, geom, name = blds[0]
    lat0 = sum(p[0] for p in geom) / len(geom)
    lon0 = sum(p[1] for p in geom) / len(geom)
    ring_m = local_ring(geom, lat0, lon0)

    print("=" * 78)
    print("STANDALONE SITE -- %s.  ZERO API CALLS, ZERO SOLVES." % key)
    print("=" * 78)
    print("   %s | %s | %s" % (", ".join(f["names"] or ["(unnamed)"]), f["state"], f["kind"]))
    print("   building        : %s (%s), %d vertices, %.0f m2"
          % (osm, name or "unnamed", len(geom), _ring_area_m2(geom)))
    print("   longest facade  : %.1f m" % f["longest_facade_m"])
    print("   nearest other DC: %.0f m = %.2fx the 600 m validated range"
          % (f["plume"]["nearest_other_tagged_dc_m"],
             f["plume"]["nearest_over_validated_range"]))
    print("   station         : K%s" % (M.metro(key)["station"] or "?"))

    wb, u_med = wind_block(key)
    print("   its own wind    : %s usable + %s calm + %s missing = %s hours at %s"
          % (format(wb["usable_hours"], ","), format(wb["calm_excluded"], ","),
             format(wb["missing"], ","), format(wb["n_hours_in_record"], ","), wb["station"]))
    assert wb["usable_hours"] + wb["calm_excluded"] + wb["missing"] == wb["n_hours_in_record"], \
        "the wind counts must partition this site's own record exactly (audit check 6e)"
    print("   median wind     : %.4f m/s  (this site's own, not a borrowed constant)" % u_med)

    wrote = []
    p = M.geom_path("selected_site.json", key)
    json.dump(selected_site(key, f, blds, ring_m), open(p, "w", encoding="utf-8"),
              allow_nan=False)
    wrote.append(p)
    for mode in ("longest", "facing"):
        p = M.geom_path("solver_site_%s.json" % mode, key)
        json.dump(solver_site(ring_m, mode), open(p, "w", encoding="utf-8"), allow_nan=False)
        wrote.append(p)
        p = M.demo_path("rise_table_%s.json" % mode, key)
        json.dump(zero_rise_table(mode, ring_m), open(p, "w", encoding="utf-8"), allow_nan=False)
        wrote.append(p)
    p = M.geom_path("direction_table.json", key)
    json.dump(direction_table(key, ring_m, u_med), open(p, "w", encoding="utf-8"), allow_nan=False)
    wrote.append(p)

    print("\n   wrote %d artefact(s):" % len(wrote))
    for p in wrote:
        print("      %s" % os.path.basename(p))
    print("\n   The rise tables are ZERO and the receptor fields are NULL. `agent.rise_table` will")
    print("   read the cache and never reach the solver -- zero GPU solves, which is also the")
    print("   physically correct cost: there is no neighbour intake to compute a rise at.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
