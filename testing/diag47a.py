# -*- coding: utf-8 -*-
"""N-47 diagnostic  ---  HOW did P2 fail? Is `persistence` a duration with an artifact, or not a
duration at all?   FREE, reads the two fixtures N-47 already paid for.

P2 required all values in [0, 10] for a 10-hour window. The upper bound HELD (max 4.248 h). The lower
bound did not: values reach -0.581 h, and a duration cannot be negative.

Two very different explanations, with different consequences:
  (A) a small numerical artifact around zero -- interpolation or regression undershoot on tiles whose
      true duration is ~0. Then the quantity IS a duration and the artifact is a documentable defect.
  (B) the quantity is not a duration at all -- e.g. a signed anomaly, or a difference against some
      baseline. Then no decision may be keyed on it until FortyGuard says what it is.

Discriminating tests, all free:
  1. What FRACTION of tiles is negative, and how negative? (A) predicts a small fraction, tightly
     clustered just below zero. (B) allows a large fraction and/or large magnitudes.
  2. Is duration MONOTONE in threshold, tile by tile? A real duration must satisfy
     d(31.0) >= d(32.0) at every tile -- you cannot spend less time above a LOWER threshold. A
     meaningful violation rate means the field is not a coherent duration.
  3. Are negative tiles spatially clustered (edge/interpolation artifact) or scattered?
  4. Is the suspicious median of exactly 1.000 at threshold 32.0 a floor, a mode, or a coincidence?
"""
import io
import json
import os
import statistics
import sys

from common import banner, save_result, FIXTURES

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

WIN_H = 10.0
FILES = {31.0: "n47_persist_thr31.json", 32.0: "n47_persist_thr32.json"}


def load(fn):
    p = os.path.join(FIXTURES, fn)
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for f in d.get("map_data", {}).get("features", []):
        c = f["geometry"]["coordinates"][0]
        lat = sum(x[1] for x in c[:4]) / 4
        lon = sum(x[0] for x in c[:4]) / 4
        v = f["properties"].get("value")
        if isinstance(v, (int, float)):
            out[(round(lat, 6), round(lon, 6))] = float(v)
    return out


def main():
    banner("N-47 diag  is `persistence` a duration with an artifact, or not a duration?   [FREE]")

    fields = {}
    for thr, fn in FILES.items():
        try:
            fields[thr] = load(fn)
            print("   loaded %s: %d tiles" % (fn, len(fields[thr])))
        except Exception as e:
            print("   could not load %s: %s" % (fn, str(e)[:120]))
    if len(fields) != 2:
        print("   need both fixtures")
        return 2

    out = {}

    # ---- 1. how negative, and how many? ----
    print("\n   [1] NEGATIVE VALUES -- fraction and magnitude")
    for thr in sorted(fields, reverse=True):
        v = list(fields[thr].values())
        neg = [x for x in v if x < 0]
        n = len(v)
        rec = {"n": n, "n_negative": len(neg), "frac_negative": len(neg) / n,
               "most_negative": min(v),
               "neg_median": statistics.median(neg) if neg else None,
               "frac_below_minus_0p1": sum(1 for x in v if x < -0.1) / n,
               "frac_below_minus_0p5": sum(1 for x in v if x < -0.5) / n}
        out["neg_thr%.0f" % thr] = rec
        print("      thr %.1f C : %5d of %d negative (%.2f %%), most negative %.3f h, "
              "median of negatives %s"
              % (thr, len(neg), n, 100 * rec["frac_negative"], rec["most_negative"],
                 "%.3f" % rec["neg_median"] if neg else "n/a"))
        print("                  below -0.1 h: %.3f %%    below -0.5 h: %.4f %%"
              % (100 * rec["frac_below_minus_0p1"], 100 * rec["frac_below_minus_0p5"]))

    # ---- 2. monotonicity in threshold, tile by tile ----
    print("\n   [2] MONOTONICITY -- a real duration must have d(31.0) >= d(32.0) at EVERY tile")
    keys = [k for k in fields[31.0] if k in fields[32.0]]
    diffs = [fields[31.0][k] - fields[32.0][k] for k in keys]
    viol = [d for d in diffs if d < 0]
    bad = [d for d in diffs if d < -0.05]
    print("      %d tiles compared" % len(keys))
    print("      violations (d31 < d32)          : %d (%.3f %%)" % (len(viol), 100 * len(viol) / len(keys)))
    print("      violations worse than -0.05 h   : %d (%.3f %%)" % (len(bad), 100 * len(bad) / len(keys)))
    print("      worst violation                 : %.3f h" % (min(diffs) if diffs else 0))
    print("      mean difference d31 - d32       : %+.3f h" % statistics.fmean(diffs))
    out["monotonicity"] = {"n": len(keys), "n_violations": len(viol),
                           "frac_violations": len(viol) / len(keys),
                           "n_violations_beyond_0p05": len(bad),
                           "worst_violation_h": min(diffs) if diffs else None,
                           "mean_diff_h": statistics.fmean(diffs)}

    # ---- 3. are negatives spatially clustered? edge test ----
    print("\n   [3] SPATIAL PATTERN of negatives -- clustered at the AOI edge, or scattered?")
    lats = sorted({k[0] for k in fields[31.0]})
    lons = sorted({k[1] for k in fields[31.0]})
    lat_lo, lat_hi = lats[0], lats[-1]
    lon_lo, lon_hi = lons[0], lons[-1]
    band = 0.05          # outermost 5 % of the box counts as "edge"
    dlat, dlon = (lat_hi - lat_lo), (lon_hi - lon_lo)

    def is_edge(k):
        return (k[0] < lat_lo + band * dlat or k[0] > lat_hi - band * dlat
                or k[1] < lon_lo + band * dlon or k[1] > lon_hi - band * dlon)

    edge_all = sum(1 for k in fields[31.0] if is_edge(k))
    negs = [k for k, v in fields[31.0].items() if v < 0]
    edge_neg = sum(1 for k in negs if is_edge(k))
    base = edge_all / len(fields[31.0])
    obs = (edge_neg / len(negs)) if negs else 0.0
    print("      outermost 5 %% of the AOI holds %.1f %% of all tiles" % (100 * base))
    print("      but holds %.1f %% of the NEGATIVE tiles (%d of %d)"
          % (100 * obs, edge_neg, len(negs)))
    print("      enrichment factor: %.2fx  %s"
          % ((obs / base) if base else 0,
             "-> consistent with an EDGE/interpolation artifact" if base and obs / base > 2
             else "-> NOT edge-concentrated; scattered through the interior"))
    out["edge_test"] = {"frac_tiles_at_edge": base, "frac_negatives_at_edge": obs,
                        "enrichment": (obs / base) if base else None,
                        "n_negative": len(negs)}

    # ---- 4. the suspicious median of exactly 1.000 at threshold 32 ----
    print("\n   [4] THE EXACT 1.000 MEDIAN at threshold 32.0 -- floor, mode, or coincidence?")
    v32 = list(fields[32.0].values())
    n32 = len(v32)
    for target in (1.0,):
        exact = sum(1 for x in v32 if abs(x - target) < 1e-9)
        near = sum(1 for x in v32 if abs(x - target) < 0.01)
        print("      exactly %.3f : %d tiles (%.2f %%)" % (target, exact, 100 * exact / n32))
        print("      within 0.01  : %d tiles (%.2f %%)" % (near, 100 * near / n32))
    # most common rounded values
    from collections import Counter
    c = Counter(round(x, 2) for x in v32)
    print("      most common values (2 dp) at thr 32.0:")
    for val, cnt in c.most_common(6):
        print("         %6.2f h  %5d tiles (%.2f %%)" % (val, cnt, 100 * cnt / n32))
    out["thr32_mode"] = {"most_common": [[v, c2] for v, c2 in c.most_common(6)],
                         "n": n32}

    # ---- conclusion ----
    print("\n   READING")
    fn = out["neg_thr31"]["frac_negative"]
    mono_bad = out["monotonicity"]["frac_violations"]
    enrich = out["edge_test"]["enrichment"] or 0
    if fn < 0.05 and mono_bad < 0.02:
        concl = ("Explanation (A): the values behave as a DURATION -- monotone in threshold at "
                 "%.2f %% violation, upper bound respected -- with a small negative artifact on "
                 "%.2f %% of tiles near zero. Usable if the negatives are clamped, and the artifact "
                 "is a documentable API defect." % (100 * mono_bad, 100 * fn))
    elif mono_bad >= 0.02:
        concl = ("Explanation (B): %.2f %% of tiles violate monotonicity in threshold, which a real "
                 "duration cannot do. The quantity is NOT a coherent duration and nothing may be "
                 "keyed on it until FortyGuard defines it." % (100 * mono_bad))
    else:
        concl = ("Mixed: monotonicity holds (%.2f %% violations) but negatives affect %.2f %% of "
                 "tiles, too many for a pure edge artifact (enrichment %.2fx). Units unresolved."
                 % (100 * mono_bad, 100 * fn, enrich))
    print("      %s" % concl)
    out["conclusion"] = concl

    save_result("n47_diag_units.json", out)
    print("\n   written: results/n47_diag_units.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
