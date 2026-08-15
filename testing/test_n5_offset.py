# -*- coding: utf-8 -*-
"""N-5  ---  THE CORE CLAIM.  FREE: uses fields already on disk.

The pitch is: every site carries a persistent thermal offset from the area average,
we can learn it, and applying it beats what a regional forecast would give you.

Test: learn each tile's offset on day A, use it to predict day B, and compare
against the baseline of just using day B's area mean for every tile (which is
exactly what a 3 km regional forecast delivers).

If this fails, the "your building is different" claim collapses and the project
must rest on the physics layer alone. It costs nothing to find out.
"""
import statistics, sys
from common import load_field, tile_key, banner, save_result, verdict


def evaluate(day_a, day_b, label):
    fa, fb = load_field(day_a), load_field(day_b)
    if fa is None or fb is None:
        print("   SKIP %s: saved field missing (%s / %s)" % (label, day_a, day_b))
        return None

    A = {tile_key(la, lo): p.get("average_temperature") for la, lo, p in fa}
    B = {tile_key(la, lo): p.get("average_temperature") for la, lo, p in fb}
    common = [k for k in A if k in B and A[k] is not None and B[k] is not None]
    if len(common) < 100:
        print("   SKIP %s: only %d matched tiles" % (label, len(common)))
        return None

    mean_a = statistics.fmean(A[k] for k in common)
    mean_b = statistics.fmean(B[k] for k in common)

    err_base, err_off = [], []
    for k in common:
        offset = A[k] - mean_a                    # learned on day A
        err_base.append(abs(mean_b - B[k]))       # regional forecast: one number for everyone
        err_off.append(abs((mean_b + offset) - B[k]))

    mae_base = statistics.fmean(err_base)
    mae_off = statistics.fmean(err_off)
    improvement = mae_base - mae_off
    pct = 100 * improvement / mae_base if mae_base else 0
    better = sum(1 for a, b in zip(err_off, err_base) if a < b)

    # how much of day B's spatial variance does day A's pattern explain?
    var_b = statistics.pvariance([B[k] for k in common])
    resid_var = statistics.pvariance([(mean_b + (A[k] - mean_a)) - B[k] for k in common])
    r2 = 1 - resid_var / var_b if var_b else float("nan")

    print("   %s" % label)
    print("     matched tiles                  : %s" % format(len(common), ","))
    print("     day A area mean                : %.4f C" % mean_a)
    print("     day B area mean                : %.4f C" % mean_b)
    print("     day B spatial sd               : %.4f C" % statistics.pstdev([B[k] for k in common]))
    print("     MAE, regional-forecast baseline: %.4f C" % mae_base)
    print("     MAE, with learned offset       : %.4f C" % mae_off)
    print("     IMPROVEMENT                    : %.4f C   (%.1f%%)" % (improvement, pct))
    print("     tiles improved                 : %s / %s  (%.0f%%)"
          % (format(better, ","), format(len(common), ","), 100 * better / len(common)))
    print("     variance explained (R2)        : %.3f" % r2)
    return {"label": label, "n": len(common), "mae_base": mae_base, "mae_off": mae_off,
            "improvement": improvement, "pct": pct, "frac_improved": better / len(common), "r2": r2}


def main():
    banner("N-5  Does a learned per-site offset beat a regional forecast?   [FREE]")
    print("   Baseline = one temperature for the whole area (what HRRR at 3 km gives you).")
    print("   Ours     = that area mean plus each tile's own offset, learned on an earlier day.")
    print()

    out = []
    r1 = evaluate("DC_2026-06-23", "DC_2026-07-28", "Data-centre cluster  (8x8 km @ 39.0100,-77.4460)")
    if r1: out.append(r1)
    print()
    r2 = evaluate("CT_2026-06-23", "CT_2026-07-28", "Control polygon      (8x8 km @ 39.1500,-77.2000)")
    if r2: out.append(r2)

    if not out:
        print("\n   NO DATA — cannot run. Saved fields not found.")
        return 2

    print()
    primary = out[0]
    ok = primary["improvement"] > 0.05 and primary["frac_improved"] > 0.6
    verdict(ok,
            "PASS - the learned offset beats a regional forecast by %.3f C (%.0f%% of tiles improved). "
            "This number is the product headline." % (primary["improvement"], 100 * primary["frac_improved"]),
            "FAIL - the offset does not generalise. The 'your building is different' claim collapses; "
            "the project must rest on the physics layer alone.")
    save_result("n5_offset.json", {"pass": ok, "runs": out})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
