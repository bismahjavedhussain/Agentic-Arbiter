# -*- coding: utf-8 -*-
"""Choose WHICH real Ashburn pair to model, on physical grounds. FREE, keyless.

WHY NOT JUST PICK THE BIGGEST
    Ranking candidate pairs by floor area picks whatever is largest, which says nothing about whether
    recirculation actually happens there. Recirculation needs the wind to blow the source's exhaust
    TOWARD the neighbour, so the pair that matters is one whose critical wind bearing coincides with a
    bearing the wind actually comes from.

THE METEOROLOGICAL CONVENTION, stated because it is easy to get backwards
    "Wind from 270 deg" means air moving FROM the west TOWARD the east. So if the neighbour lies at
    compass bearing B from the source, the exhaust reaches it when the wind comes FROM (B + 180) mod 360.
    Getting this inverted would put the plume on exactly the wrong side of the campus.

THE SCORE
    exposure = sum over 5-degree wind-direction bins of  frequency(bin) x plume_alignment(bin)
    where plume_alignment falls off with the angle between the wind's downwind direction and the
    source->receptor bearing, over a 40 deg half-width (the measured plume sector). Separation enters as
    a 1/distance dilution factor, which is the right sign even before the solver runs.

    Frequencies come from 449 real KIAD target-hour observations (2021-2026 summers), calm excluded.

REVISED 2026-08-18 AFTER N-54 -- two gates added, and they matter more than the score
-------------------------------------------------------------------------------------
The original version scored exposure x dilution and stopped. That picked a pair whose plume cannot
reach the neighbour in a straight line, so N-54 measured **100 % of downwind bearings REFUSED** in the
realistic bank mode: the agent could never produce a recirculation number there. Exposure asks whether
the WIND points the right way; it never asked whether the GEOMETRY does.

  GATE C -- PATH CLEARANCE. A real condenser bank sits on a LONG facade. So the source's longest
      facade must actually FACE the receptor: outward_normal . unit(source->receptor) > 0. At the
      previously selected pair BOTH ~189 m facades faced away (-0.896 and -0.660) because the receptor
      lies off the END of the hall, leaving only a 37 m end wall pointing at it.

  GATE B -- MINIMUM TRUE GAP, and it is derived, not chosen. The intake disc is centred
      INTAKE_STANDOFF_M outside the receptor facade with radius INTAKE_RADIUS_M, so it reaches
      standoff + radius = 50 m toward the source. If the facade-to-facade gap is smaller than that, the
      disc sits inside the source hall and "the neighbour's intake temperature" is measuring the
      neighbour's wall. Both constants are IMPORTED from build_site so the two files cannot drift apart.

      Measured, to show the bound is real and not arithmetic on its own: at the previous site's 47.9 m
      gap the disc holds 26 cells, 3 of them (11.5 %) inside the RECEPTOR hall and 0 inside the source
      hall -- so 50 m is CONSERVATIVE at dx = 10 m, because the gap is a minimum over the whole
      footprint while the intake sits at a facade midpoint. It is kept conservative deliberately.
      **`build_site.verify()` and `solver.assert_intake_clear()` remain the real arbiters** and refuse
      to write a site regardless of what this filter allows.

  GATE D -- REALISTIC BANK SIZE. Longest facade >= MIN_FACADE_M, so the bank is a plausible condenser
      row rather than a token strip.

  Also: gap must be > 0. Touching or double-mapped footprints (e.g. 701924665 / 985207884, Vantage
  VA11, which scores +0.994 on clearance) are adjoining halls, not a source/receptor pair.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build_site import (ring_gap, longest_edge, BANK_DEPTH_M,         # noqa: E402
                        INTAKE_STANDOFF_M, INTAKE_RADIUS_M)

# METRO-AWARE. Defaults to ashburn, so both paths are byte-identical to what shipped.
import metros as _M                                                        # noqa: E402
GEOM = _M.candidates_path()
WIND = os.path.join(ROOT, "data", "weather", "kiad_wind_summers.json")
OUT = _M.geom_path("selected_site.json")

# Reproduced EXACTLY from kiad_wind_summers.json's own meta block, so a new metro's histogram means
# the same thing Ashburn's does: site-local 16:00 wind direction, June-August, >= 3 kt, calm
# excluded (ASOS reports drct = 0 when calm, which is not a direction), binned at 5 degrees.
WIND_MONTHS = (6, 7, 8)
WIND_HOUR = 16
WIND_MIN_KT = 3.0
WIND_BIN_DEG = 5


def wind_hist_5deg(mkey):
    """The 72-bin summer-afternoon wind-direction histogram for a metro.

    Ashburn reads the pre-existing derived file so its selection is bit-for-bit what it was. Any
    other metro has the same quantity COMPUTED from its own hourly record -- which the site choice
    genuinely needs, because "which facade the wind actually points at" is the whole selection
    criterion and Chicago's prevailing summer wind is not Ashburn's.
    """
    if mkey == _M.DEFAULT_METRO:
        return json.load(open(WIND, encoding="utf-8"))["dir_hist_5deg"], "kiad_wind_summers.json"
    rec = json.load(open(_M.weather_path(mkey), encoding="utf-8"))
    f = rec["meta"]["fields"]
    idr, isk = f.index("drct"), f.index("sknt")
    hist = [0] * (360 // WIND_BIN_DEG)
    n = 0
    for k, v in rec["hours"].items():
        if int(k[5:7]) not in WIND_MONTHS or int(k[11:13]) != WIND_HOUR:
            continue
        d, s = v[idr], v[isk]
        if d is None or s is None or s < WIND_MIN_KT:
            continue
        hist[int(round(d / WIND_BIN_DEG)) % len(hist)] += 1
        n += 1
    if n == 0:
        raise SystemExit("no usable summer-afternoon wind in %s -- cannot choose a site by exposure"
                         % os.path.basename(_M.weather_path(mkey)))
    return hist, "computed from %s (%d days)" % (os.path.basename(_M.weather_path(mkey)), n)

PLUME_HALF_WIDTH_DEG = 40.0     # measured plume sector; see PLAN.md section 6.6
REF_SEPARATION_M = 300.0        # dilution reference, the reference layout's separation
NON_DC = ("town center", "mall", "school", "church", "hospital", "shopping", "stadium")

# DERIVED, not chosen -- see GATE B above. Imported constants so this cannot silently drift.
# 🔴 CORRECTED 2026-08-19, +10 m, after this gate PASSED a site the builder then REFUSED.
# It read `INTAKE_STANDOFF_M + INTAKE_RADIUS_M` = 50.0 m, i.e. how far the intake averaging disc
# reaches back toward the source. That omits the CONDENSER BANK, and `strip_ring()` centres the bank
# on the facade midpoint -- so with BANK_DEPTH_M = 20 m, HALF OF IT (10 m) sits OUTSIDE the wall,
# projecting into the very gap the plume crosses. (BANK_DEPTH_M's own comment says "how far the bank
# extends into the hall", which is wrong: it is centred, so half extends out of it.)
#
# The Dulles pair Amazon IAD121 -> IAD122 has a 54.7 m gap. It passed this gate at 50 m, was selected,
# committed and built -- and `solver.assert_intake_clear()` then refused to write the site:
# "4 % of the intake averaging disc lies on condenser source cells. The disc would average the
# discharge it is supposed to measure." Two GPU builds wasted, and the guard caught it.
#
# 60 m explains every observation: Ashburn 60.3 m clears by 0.3 m, Chicago 118.4 m clears easily,
# Dulles 54.7 m is short by 5.3 m. ⚠ NOTE HOW NARROWLY THE COMMITTED ASHBURN SITE CLEARS -- 0.3 m.
# It is inside the bound, but it is not comfortably inside it, and that is worth knowing.
MIN_GAP_M = INTAKE_STANDOFF_M + INTAKE_RADIUS_M + BANK_DEPTH_M / 2.0      # = 60.0 m
MIN_FACADE_M = 100.0            # CHOSEN: a condenser row needs a long facade   [ASSUMED]


def is_datacentre(b):
    s = " ".join(str(x or "").lower() for x in
                 (b.get("name"), b.get("operator"), b.get("building_tag"), b.get("telecom_tag")))
    if any(x in s for x in NON_DC):
        return False
    if b.get("telecom_tag") == "data_center" or b.get("building_tag") == "data_center":
        return True
    return any(x in s for x in ("data", "digital", "cloud", "cyrus", "equinix", "aws", "amazon",
                                "iron mountain", "vantage", "stack", "centersquare", "quantum"))


def angdiff(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def main():
    print("=" * 78)
    print("INTAKE-ARBITER  choosing the site by WIND EXPOSURE, not by size   [FREE]")
    print("=" * 78)

    g = json.load(open(GEOM, encoding="utf-8"))
    _mk = _M.metro_key()
    hist, _hsrc = wind_hist_5deg(_mk)              # 72 bins of 5 deg, counts
    print("   metro %s (%s)   wind histogram: %s" % (_mk, _M.metro(_mk)["label"], _hsrc))
    total = sum(hist) or 1
    freq = [h / total for h in hist]
    B = {b["osm_id"]: b for b in g["buildings"]}
    print("\n   wind climatology: %d target-hour observations, calm (<%.0f kt) excluded"
          % (total, WIND_MIN_KT))
    top = sorted(range(72), key=lambda i: -freq[i])[:5]
    print("   most common bearings (wind FROM): " +
          ", ".join("%d-%d deg %.1f%%" % (i * 5, i * 5 + 5, 100 * freq[i]) for i in top))

    scored = []
    funnel = {"pairs": 0, "not_datacentre": 0, "gap_zero": 0, "gap_too_small": 0,
              "facade_faces_away": 0, "facade_too_short": 0, "survived": 0}
    rejected = []
    for p in g["pairs"]:
        funnel["pairs"] += 1
        a, b = B.get(p["source_osm_id"]), B.get(p["receptor_osm_id"])
        if not (a and b and is_datacentre(a) and is_datacentre(b)):
            funnel["not_datacentre"] += 1
            continue

        # ---- GATE B: true edge-to-edge gap, big enough for the intake disc to sit in free air
        gap = ring_gap(a["ring_m"], b["ring_m"])
        if gap <= 0.0:
            funnel["gap_zero"] += 1
            rejected.append({"pair": [a["osm_id"], b["osm_id"]], "why": "footprints touch",
                             "gap_m": round(gap, 1), "name": a.get("name")})
            continue
        if gap < MIN_GAP_M:
            funnel["gap_too_small"] += 1
            continue

        # ---- GATE C: the LONGEST facade must actually face the receptor  (the N-54 lesson)
        cA, cB = a["centre_m"], b["centre_m"]
        ux, uy = cB[0] - cA[0], cB[1] - cA[1]
        un = math.hypot(ux, uy) or 1.0
        ux, uy = ux / un, uy / un
        mid_l, along_l, len_l, nrm_l = longest_edge(a["ring_m"], cA)
        clearance = nrm_l[0] * ux + nrm_l[1] * uy
        if clearance <= 0.0:
            funnel["facade_faces_away"] += 1
            continue

        # ---- GATE D: a condenser row needs a long facade
        if len_l < MIN_FACADE_M:
            funnel["facade_too_short"] += 1
            continue

        funnel["survived"] += 1
        brg = p["bearing_a_to_b_deg"]              # receptor lies at this bearing from source
        critical_from = (brg + 180.0) % 360.0      # wind must come FROM here to carry exhaust to it
        exposure = 0.0
        for i in range(72):
            wind_from = i * 5.0 + 2.5
            downwind = (wind_from + 180.0) % 360.0
            off = angdiff(downwind, brg)
            if off <= PLUME_HALF_WIDTH_DEG:
                align = 1.0 - (off / PLUME_HALF_WIDTH_DEG)
                exposure += freq[i] * align
        dilution = REF_SEPARATION_M / max(p["separation_m"], 1.0)
        scored.append({**p, "critical_wind_from_deg": round(critical_from, 1),
                       "wind_exposure": round(exposure, 5),
                       "dilution_factor": round(dilution, 3),
                       "exposure_x_dilution": round(exposure * dilution, 5),
                       "true_gap_m": round(gap, 1),
                       "longest_facade_m": round(len_l, 1),
                       "path_clearance": round(clearance, 3)})

    print("\n   SELECTION FUNNEL  (gates B/C/D added 2026-08-18 after N-54)")
    print("      candidate pairs                              %5d" % funnel["pairs"])
    print("      - not a data-centre pair                     %5d" % funnel["not_datacentre"])
    print("      - GATE B footprints touch (gap = 0)          %5d" % funnel["gap_zero"])
    print("      - GATE B true gap < %.0f m (intake disc)       %5d"
          % (MIN_GAP_M, funnel["gap_too_small"]))
    print("      - GATE C longest facade faces AWAY           %5d" % funnel["facade_faces_away"])
    print("      - GATE D longest facade < %.0f m              %5d"
          % (MIN_FACADE_M, funnel["facade_too_short"]))
    print("      = SURVIVED all gates                         %5d" % funnel["survived"])
    if rejected:
        print("      touching-footprint rejects: " +
              ", ".join("%s/%s" % (r["pair"][0], r["pair"][1]) for r in rejected[:4]))

    scored.sort(key=lambda r: -r["exposure_x_dilution"])
    print("\n   %d pairs survived. Top by exposure x dilution:" % len(scored))
    print("      %-11s %-11s %6s %6s %7s %7s %8s %9s"
          % ("source", "receptor", "sep m", "gap m", "facade", "clear", "expos.", "score"))
    for r in scored[:10]:
        print("      %-11s %-11s %6.0f %6.1f %7.0f %+7.3f %8.3f %9.4f"
              % (r["source_osm_id"], r["receptor_osm_id"], r["separation_m"], r["true_gap_m"],
                 r["longest_facade_m"], r["path_clearance"],
                 r["wind_exposure"], r["exposure_x_dilution"]))
        print("                  %s  ->  %s" % (str(r["source_name"])[:34], str(r["receptor_name"])[:34]))

    if not scored:
        print("\n   no qualifying pair found -- widen the filters and re-run")
        return 2

    best = scored[0]
    a, b = B[best["source_osm_id"]], B[best["receptor_osm_id"]]
    print("\n   SELECTED")
    print("      source   : %s  (%s), %.0f x %.0f m, %.0f m2"
          % (a["osm_id"], a["name"] or a["operator"], a["width_m"], a["height_m"], a["area_m2"]))
    print("      receptor : %s  (%s), %.0f x %.0f m, %.0f m2"
          % (b["osm_id"], b["name"] or b["operator"], b["width_m"], b["height_m"], b["area_m2"]))
    print("      separation %.0f m, receptor at bearing %.1f deg from source"
          % (best["separation_m"], best["bearing_a_to_b_deg"]))
    print("      critical wind FROM %.1f deg, which blows %.1f %% of observed hours within the"
          % (best["critical_wind_from_deg"], 100 * best["wind_exposure"]))
    print("      40 deg plume sector -- that is the fraction of hours this pair is exposed")
    print("      site centre: %.6f, %.6f" % tuple(a["centre_latlon"]))

    json.dump({
        "selection_rule": "REVISED 2026-08-18 after N-54. Three geometric GATES first, then wind "
                          "exposure x separation dilution over 449 real KIAD observations. Gates: "
                          "(B) true edge-to-edge gap > intake standoff + radius = %.0f m, so the "
                          "intake disc sits in free air and not inside the source hall; "
                          "(C) the source LONGEST facade must FACE the receptor, so a realistic "
                          "condenser bank has a straight plume path -- the original version skipped "
                          "this and picked a pair where N-54 measured 100 %% of downwind bearings "
                          "REFUSED; (D) longest facade >= %.0f m. NOT chosen by floor area."
                          % (MIN_GAP_M, MIN_FACADE_M),
        "gates": {"min_true_gap_m": MIN_GAP_M, "min_facade_m": MIN_FACADE_M,
                  "derivation_of_min_gap": "INTAKE_STANDOFF_M + INTAKE_RADIUS_M, imported from "
                                           "build_site so the two files cannot drift"},
        "selection_funnel": funnel,
        "rejected_touching_footprints": rejected,
        "convention": "wind FROM X means air moves toward X+180. Receptor at bearing B from source is "
                      "exposed when the wind comes FROM (B+180) mod 360.",
        "plume_half_width_deg": PLUME_HALF_WIDTH_DEG,
        "selected": best,
        "source_building": a, "receptor_building": b,
        "runner_up": scored[1] if len(scored) > 1 else None,
        "survivors": scored,          # ALL gate-passing pairs, for refusal_rank.py to measure
        "assumptions_not_in_osm": [
            "Building HEIGHT is absent from OSM for these footprints, so the solver's building height "
            "remains a stated assumption rather than a measurement.",
            "Condenser bank POSITION is not mapped anywhere. It is placed on the source face pointing "
            "at the receptor, which is the physically conservative worst case.",
            "Intake POSITION is likewise assumed, on the receptor face pointing at the source.",
        ],
        "attribution": "Building footprints (c) OpenStreetMap contributors, ODbL. Weather: NOAA ASOS "
                       "via Iowa State Environmental Mesonet. No FortyGuard credential used.",
    }, open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
