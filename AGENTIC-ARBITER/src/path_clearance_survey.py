# -*- coding: utf-8 -*-
"""Does a BETTER site exist? Survey all 611 candidate pairs for plume-path clearance.

N-54 found that at the selected pair, BOTH ~189 m facades of the source hall face AWAY from the
receptor, so under the realistic bank mode every downwind bearing is refused. This asks whether that
is peculiar to the selected pair or true of the whole candidate set.

Criterion, per pair: take the source's LONGEST facade (where a real condenser bank goes), compute its
outward normal, and dot with the unit vector toward the receptor. dot > 0 means the realistic bank
faces the neighbour, so a straight plume path exists and the agent can actually compute a number.
"""
import io
import json
import math
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.chdir(r"d:\FGHackathon\AGENTIC-ARBITER")
sys.path.insert(0, "src")
from build_site import longest_edge, ring_gap                    # noqa: E402

d = json.load(open("data/geometry/ashburn_candidates.json", encoding="utf-8"))
B = {b["osm_id"]: b for b in d["buildings"]}

SEL_SRC, SEL_RCP = 852039781, 793087859


def outward_dot(src, rcp):
    """(dot of longest-facade outward normal with unit-toward-receptor, facade length)."""
    ring, cA = src["ring_m"], src["centre_m"]
    cB = rcp["centre_m"]
    ux, uy = cB[0] - cA[0], cB[1] - cA[1]
    L = math.hypot(ux, uy)
    if L < 1e-6:
        return None, None
    ux, uy = ux / L, uy / L
    r = longest_edge(ring, cA)
    mid, ln = r[0], r[2]
    ox, oy = mid[0] - cA[0], mid[1] - cA[1]
    on = math.hypot(ox, oy)
    if on < 1e-6:
        return None, None
    return (ox / on) * ux + (oy / on) * uy, ln


rows = []
for p in d["pairs"]:
    s, r = B.get(p["source_osm_id"]), B.get(p["receptor_osm_id"])
    if not s or not r:
        continue
    dot, ln = outward_dot(s, r)
    if dot is None:
        continue
    rows.append({"src": p["source_osm_id"], "rcp": p["receptor_osm_id"],
                 "dot": dot, "facade_m": ln, "sep_m": p["separation_m"],
                 "src_area": p["source_area_m2"], "rcp_area": p["receptor_area_m2"],
                 "src_name": p.get("source_name"), "rcp_name": p.get("receptor_name")})

n = len(rows)
faces = [r for r in rows if r["dot"] > 0]
print("=" * 76)
print("  DOES A BETTER SITE EXIST?  611 candidate pairs, longest-facade orientation")
print("=" * 76)
print("  pairs evaluated                            : %d" % n)
print("  longest facade FACES the receptor (dot > 0) : %d  (%.1f %%)" % (len(faces), 100 * len(faces) / n))
print("  longest facade faces AWAY   (dot <= 0)     : %d  (%.1f %%)"
      % (n - len(faces), 100 * (n - len(faces)) / n))

sel = [r for r in rows if r["src"] == SEL_SRC and r["rcp"] == SEL_RCP]
if sel:
    r = sel[0]
    print("\n  THE CURRENTLY SELECTED PAIR")
    print("     %d -> %d   dot %+.3f   longest facade %.0f m   separation %.0f m"
          % (r["src"], r["rcp"], r["dot"], r["facade_m"], r["sep_m"]))
    worse = sum(1 for x in rows if x["dot"] < r["dot"])
    print("     only %d of %d pairs (%.1f %%) point their long facade further away"
          % (worse, n, 100 * worse / n))

print("\n  BEST 12 PAIRS BY FACADE-FACES-RECEPTOR, with a long facade and a close gap")
cand = [r for r in faces if r["facade_m"] >= 100.0]
print("  (%d of %d facing pairs also have a >=100 m longest facade)" % (len(cand), len(faces)))
cand.sort(key=lambda r: (-r["dot"], r["sep_m"]))
print("  %-11s %-11s %6s %8s %8s  %s" % ("source", "receptor", "dot", "facade", "sep m", "name"))
for r in cand[:12]:
    print("  %-11d %-11d %+.3f %8.0f %8.0f  %s"
          % (r["src"], r["rcp"], r["dot"], r["facade_m"], r["sep_m"], (r["src_name"] or "-")[:26]))

# how many are BOTH facing and close (the geometry that makes recirculation a real hazard)?
close = [r for r in cand if r["sep_m"] <= 120.0]
print("\n  pairs with long facade facing the receptor AND separation <= 120 m : %d" % len(close))
for r in sorted(close, key=lambda z: -z["dot"])[:8]:
    print("     %d -> %d  dot %+.3f  facade %.0f m  sep %.0f m  %s"
          % (r["src"], r["rcp"], r["dot"], r["facade_m"], r["sep_m"], (r["src_name"] or "-")[:24]))

json.dump({"n_pairs": n, "n_facing": len(faces),
           "n_facing_long": len(cand), "n_facing_long_close": len(close),
           "selected": (sel[0] if sel else None),
           "top": cand[:40]},
          open("data/geometry/path_clearance_survey.json", "w", encoding="utf-8"), indent=1, allow_nan=False)
print("\n  written: data/geometry/path_clearance_survey.json")
