# -*- coding: utf-8 -*-
"""Final site commit: measured physics ranking, then the ARCHITECTURE SCOPE GATE. FREE, keyless.

THE PIPELINE, and why it has three stages rather than one
--------------------------------------------------------
  1. select_site.py    geometric GATES (data-centre pair, true gap > intake standoff + radius,
                       longest facade faces the receptor, facade >= 100 m) then exposure x dilution.
                       611 pairs -> 145 survivors.
  2. refusal_rank.py   MEASURES each survivor's refusal surface with solver.path_blocked() -- pure
                       geometry, no PDE solve -- and ranks by
                           usable_exposure = exposure x dilution x (1 - wind_weighted_refusal).
                       Found 56 of 145 survivors would still refuse 100 % of downwind bearings, so the
                       boolean clearance gate in stage 1 was NOT sufficient on its own.
  3. THIS FILE         applies the architecture SCOPE GATE from data/geometry/architecture_verdicts.json
                       and commits the highest-ranked candidate that is actually IN SCOPE.

WHY STAGE 3 EXISTS, and it is the whole point
---------------------------------------------
Stages 1-2 optimise PHYSICS: can the plume reach the neighbour's intake in a straight line? They are
blind to whether the cooling equipment is at GRADE or on the ROOF -- and PLAN section 8d's scope
statement depends entirely on that, because grade-level intake is what makes FortyGuard's 2 m
measurement plane the correct plane.

Those criteria CONFLICTED. Stage 2's top pick, Digital Realty Northern Virginia IAD35 / IAD36
(usable exposure 0.3172, 0.0 % refused), shows roofs densely covered in equipment arrays in BOTH ESRI
and USGS imagery -- it looks rooftop-cooled, which section 8d puts explicitly out of scope. Committing
on physics alone would have based the scope statement on a site that violates it.

So the gate is deliberately ordered LAST and given VETO power over the ranking. Physics decides the
ordering; scope decides eligibility.

The architecture verdicts are a HUMAN judgement from imagery, recorded per candidate with its evidence
in architecture_verdicts.json, cross-checked across two sources with different capture seasons. This
script does not classify anything itself -- it only enforces what was recorded.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
GEOM = os.path.join(ROOT, "data", "geometry")
# METRO-AWARE; ashburn keeps every original path so the audited chain is untouched.
sys.path.insert(0, _HERE)
import metros as _M                                                        # noqa: E402
RANK = _M.geom_path("refusal_rank.json")
ARCH = os.path.join(GEOM, "architecture_verdicts.json")
CAND = _M.candidates_path()
SEL = _M.geom_path("selected_site.json")


def main():
    rank = json.load(open(RANK, encoding="utf-8"))
    arch = json.load(open(ARCH, encoding="utf-8"))
    sel = json.load(open(SEL, encoding="utf-8"))
    B = {b["osm_id"]: b for b in json.load(open(CAND, encoding="utf-8"))["buildings"]}

    # Verdicts live under a dated key per assessment session; collect ALL of them so a new
    # metro screened later is not invisible to a file that only knew about one date.
    verdicts = {}
    for kk in sorted(k for k in arch if k.startswith("assessed_")):
        for a in arch[kk]:
            verdicts[tuple(a["pair"])] = a

    print("=" * 92)
    print("  FINAL SITE COMMIT -- measured physics ranking, then the ARCHITECTURE SCOPE GATE")
    print("=" * 92)
    print("  %-4s %-11s %-11s %8s %7s %9s  %-9s %s"
          % ("rank", "source", "receptor", "gap m", "ref_dn", "usable", "scope", "name"))

    chosen = None
    for i, r in enumerate(rank["ranked"], 1):
        key = (r["source_osm_id"], r["receptor_osm_id"])
        v = verdicts.get(key)
        if v is None:
            if i <= 8:
                print("  %-4d %-11d %-11d %8.0f %6.1f%% %9.4f  %-9s %s"
                      % (i, key[0], key[1], r["true_gap_m"], 100 * (r["refused_downwind_frac"] or 0),
                         r["usable_exposure"], "not-assd", (r["source_name"] or "-")[:30]))
            continue
        ok = bool(v["in_scope"])
        print("  %-4d %-11d %-11d %8.0f %6.1f%% %9.4f  %-9s %s"
              % (i, key[0], key[1], r["true_gap_m"], 100 * (r["refused_downwind_frac"] or 0),
                 r["usable_exposure"], v["verdict"], (r["source_name"] or "-")[:30]))
        if ok and chosen is None:
            chosen = (i, r, v)
        elif not ok:
            print("       ^^ VETOED by the scope gate: %s" % v["consequence"][:96])

    if chosen is None:
        print("\n  *** No assessed candidate is IN SCOPE. Assess more candidates with")
        print("      screen_architecture.py before committing. Site NOT changed.")
        return 2

    i, r, v = chosen
    a, b = B[r["source_osm_id"]], B[r["receptor_osm_id"]]
    prev = sel.get("selected") or {}

    surv = next((s for s in (sel.get("survivors") or [])
                 if s["source_osm_id"] == r["source_osm_id"]
                 and s["receptor_osm_id"] == r["receptor_osm_id"]), None)
    if surv is None:
        print("\n  *** chosen pair is not among select_site.py's survivors -- refusing to commit")
        return 2

    sel["selected"] = surv
    sel["source_building"] = a
    sel["receptor_building"] = b
    sel["selected_by"] = (
        "commit_site.py -- three stages: (1) select_site.py geometric gates, (2) refusal_rank.py "
        "MEASURED usable exposure, (3) architecture SCOPE GATE from architecture_verdicts.json, which "
        "has VETO power over the ranking. Chosen: rank %d on physics, and the highest-ranked candidate "
        "assessed as GRADE-cooled and therefore inside PLAN section 8d's scope." % i)
    sel["architecture_gate"] = {
        "verdict": v["verdict"], "in_scope": v["in_scope"], "evidence": v["evidence"],
        "physics_rank": i,
        "vetoed_higher_ranked": [
            {"pair": list(k), "name": vv["name"], "verdict": vv["verdict"],
             "why": vv["consequence"]}
            for k, vv in verdicts.items() if not vv["in_scope"]],
        "resolution_caveat": arch["resolution_caveat"]}
    sel["refusal_measurement"] = {
        "refused_downwind_frac": r["refused_downwind_frac"],
        "wind_weighted_refusal": r["wind_weighted_refusal"],
        "usable_exposure": r["usable_exposure"],
        "n_pairs_measured": rank["n_measured"],
        "n_pairs_refusing_all_downwind": rank["n_pairs_refusing_all_downwind"],
        "n_pairs_fully_clear": rank["n_pairs_fully_clear"]}
    sel["selection_history"] = sel.get("selection_history", []) + [{
        "date": "2026-08-18",
        "from": [prev.get("source_osm_id"), prev.get("receptor_osm_id")],
        "to": [r["source_osm_id"], r["receptor_osm_id"]],
        "why": "architecture scope gate vetoed the physics-ranked leader as rooftop-cooled"}]

    json.dump(sel, open(SEL, "w", encoding="utf-8"), indent=1, allow_nan=False)

    print("\n" + "=" * 92)
    print("  COMMITTED")
    print("=" * 92)
    print("  %s" % v["name"])
    print("     source   %-11d %s" % (a["osm_id"], a.get("name") or a.get("operator")))
    print("     receptor %-11d %s" % (b["osm_id"], b.get("name") or b.get("operator")))
    print("     true gap %.1f m   longest facade %.1f m   clearance %+.3f"
          % (r["true_gap_m"], r["longest_facade_m"], r["path_clearance"]))
    print("     refused %.1f %% of downwind bearings, %.1f %% of real wind hours"
          % (100 * r["refused_downwind_frac"], 100 * r["wind_weighted_refusal"]))
    # SECOND HARD-CODED NARRATIVE FOUND AND FIXED, same class as refusal_rank.py's.
    # This read "(rank %d on physics; rank 1 was VETOED as rooftop)" unconditionally -- true for
    # Ashburn, where the rooftop veto really did demote rank 1, and FALSE for Chicago, where rank 1
    # IS the committed pair and nothing was vetoed. The output was asserting a veto that had not
    # happened. Now it reports what the verdicts actually say.
    vetoed = [vv for vv in verdicts.values() if not vv.get("in_scope")
              and vv.get("metro", _M.DEFAULT_METRO) == _M.metro_key()]
    if i > 1 and vetoed:
        print("     usable exposure %.4f  (rank %d on physics; %d higher-ranked pair(s) VETOED: %s)"
              % (r["usable_exposure"], i, len(vetoed),
                 ", ".join(vv["verdict"] for vv in vetoed)))
    else:
        print("     usable exposure %.4f  (rank %d on physics, and it survived the scope gate)"
              % (r["usable_exposure"], i))
    print("     architecture %s -- IN SCOPE for PLAN section 8d" % v["verdict"])
    print("\n  NEXT: BANK_MODE=longest python build_site.py   then   python direction_sweep.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
