# -*- coding: utf-8 -*-
"""N-5b  ---  the CORRECT baseline.  FREE.

N-5 compared each tile against the mean of the whole 64 km2 polygon. That is the wrong
competitor. The real competitor is NOAA HRRR at 3 km, which gives one number per 3 km cell.

So the question that actually matters is:
   (a) how much does a tile differ from its OWN 3 km cell?   <- this is what 60 m buys you
   (b) how much of that difference PERSISTS day to day?      <- this is what is learnable
   (c) does it persist more in built-up areas than elsewhere? <- data centres are built-up

Also decomposes total spatial variance into sub-3km and supra-3km parts, which directly
answers "what does 60 m add over 3 km".
"""
import math, statistics, sys, json, os
from common import load_field, tile_key, banner, save_result, verdict, hav, RESULTS

CELL_KM = 3.0          # HRRR resolution


def block_id(la, lo, lat0, lon0=None, cell_km=CELL_KM):
    if lon0 is None:
        raise ValueError("lon0 required")
    dla = cell_km / 110.574
    dlo = cell_km / (111.320 * math.cos(math.radians(lat0)))
    return (int((la - lat0) / dla), int((lo - lon0) / dlo))


def analyse(day_a, day_b, label):
    fa, fb = load_field(day_a), load_field(day_b)
    if fa is None or fb is None:
        print("   SKIP %s: saved field missing" % label)
        return None

    A = {tile_key(la, lo): (la, lo, p.get("average_temperature")) for la, lo, p in fa}
    B = {tile_key(la, lo): p.get("average_temperature") for la, lo, p in fb}
    keys = [k for k in A if k in B and A[k][2] is not None and B[k] is not None]
    lat0 = min(A[k][0] for k in keys)
    lon0 = min(A[k][1] for k in keys)

    # group tiles into 3 km blocks
    blocks = {}
    for k in keys:
        la, lo, _ = A[k]
        blocks.setdefault(block_id(la, lo, lat0, lon0), []).append(k)
    blocks = {b: ks for b, ks in blocks.items() if len(ks) >= 50}
    used = [k for ks in blocks.values() for k in ks]

    # ---- variance decomposition on day B ------------------------------------
    all_b = [B[k] for k in used]
    grand = statistics.fmean(all_b)
    blk_mean_b = {b: statistics.fmean(B[k] for k in ks) for b, ks in blocks.items()}
    # between-block (what HRRR could in principle see) vs within-block (what only 60 m sees)
    between = statistics.fmean((blk_mean_b[b] - grand) ** 2 for b in blocks
                               for _ in range(1)) if len(blocks) > 1 else 0.0
    within = statistics.fmean((B[k] - blk_mean_b[b]) ** 2 for b, ks in blocks.items() for k in ks)
    tot = statistics.pvariance(all_b)

    # ---- does the WITHIN-BLOCK anomaly persist? -----------------------------
    blk_mean_a = {b: statistics.fmean(A[k][2] for k in ks) for b, ks in blocks.items()}
    err_base, err_off = [], []
    for b, ks in blocks.items():
        for k in ks:
            anom_a = A[k][2] - blk_mean_a[b]          # learned on day A, within its own 3 km cell
            truth = B[k] - blk_mean_b[b]              # day B anomaly within the same cell
            err_base.append(abs(truth))               # HRRR: assume zero anomaly
            err_off.append(abs(truth - anom_a))       # ours: apply the learned anomaly
    mae_base, mae_off = statistics.fmean(err_base), statistics.fmean(err_off)
    imp = mae_base - mae_off
    better = sum(1 for a, b_ in zip(err_off, err_base) if a < b_)
    var_t = statistics.pvariance([B[k] - blk_mean_b[b] for b, ks in blocks.items() for k in ks])
    var_r = statistics.pvariance([(B[k] - blk_mean_b[b]) - (A[k][2] - blk_mean_a[b])
                                  for b, ks in blocks.items() for k in ks])
    r2 = 1 - var_r / var_t if var_t else float("nan")

    print("   %s" % label)
    print("     tiles used / 3 km blocks       : %s / %d" % (format(len(used), ","), len(blocks)))
    print("     total spatial sd (day B)       : %.4f C" % math.sqrt(tot))
    print("     WITHIN-3km sd  (60 m adds this): %.4f C" % math.sqrt(within))
    print("     share of variance below 3 km   : %.0f%%" % (100 * within / tot if tot else 0))
    print("     --- can we predict the within-cell anomaly from an earlier day? ---")
    print("     MAE, HRRR baseline (anomaly=0) : %.4f C" % mae_base)
    print("     MAE, learned anomaly           : %.4f C" % mae_off)
    print("     IMPROVEMENT                    : %+.4f C  (%.1f%%)"
          % (imp, 100 * imp / mae_base if mae_base else 0))
    print("     tiles improved                 : %s / %s  (%.0f%%)"
          % (format(better, ","), format(len(used), ","), 100 * better / len(used)))
    print("     variance explained (R2)        : %.3f" % r2)
    return {"label": label, "sd_total": math.sqrt(tot), "sd_within3km": math.sqrt(within),
            "share_below_3km": within / tot if tot else 0, "mae_base": mae_base,
            "mae_off": mae_off, "improvement": imp, "frac_improved": better / len(used), "r2": r2}


def built_vs_open(day_a, day_b):
    """Does persistence differ between tiles near buildings and tiles far from them?"""
    reg = os.path.join(RESULTS, "..", "..", "registers.json")
    cand = [reg, os.path.join(RESULTS, "registers.json")]
    from common import SCRATCH
    cand.append(os.path.join(SCRATCH, "registers.json"))
    pts = None
    for c in cand:
        if os.path.exists(c):
            try:
                pts = [tuple(p) for p in json.load(open(c))["facilities"]]
                break
            except Exception:
                pass
    if not pts:
        print("   (facility register not found - skipping built-vs-open split)")
        return None
    fa, fb = load_field(day_a), load_field(day_b)
    if fa is None or fb is None:
        return None
    A = {tile_key(la, lo): (la, lo, p.get("average_temperature")) for la, lo, p in fa}
    B = {tile_key(la, lo): p.get("average_temperature") for la, lo, p in fb}
    keys = [k for k in A if k in B and A[k][2] is not None and B[k] is not None]
    near, far = [], []
    for k in keys:
        la, lo, _ = A[k]
        dla = 400 / 110.574; dlo = 400 / (111.320 * math.cos(math.radians(la)))
        close = any(abs(p[0]-la) <= dla and abs(p[1]-lo) <= dlo and hav(p, (la, lo)) <= 400 for p in pts)
        (near if close else far).append(k)
    out = {}
    for name, ks in (("within 400 m of a data centre", near), ("further than 400 m", far)):
        if len(ks) < 200:
            continue
        ma = statistics.fmean(A[k][2] for k in ks); mb = statistics.fmean(B[k] for k in ks)
        vt = statistics.pvariance([B[k] - mb for k in ks])
        vr = statistics.pvariance([(B[k] - mb) - (A[k][2] - ma) for k in ks])
        r2 = 1 - vr / vt if vt else float("nan")
        print("     %-32s n=%-7s R2=%+.3f" % (name, format(len(ks), ","), r2))
        out[name] = {"n": len(ks), "r2": r2}
    return out


def main():
    banner("N-5b  What does 60 m add over HRRR's 3 km, and does it persist?   [FREE]")
    out = []
    r1 = analyse("DC_2026-06-23", "DC_2026-07-28", "Data-centre cluster")
    if r1: out.append(r1)
    print()
    r2 = analyse("CT_2026-06-23", "CT_2026-07-28", "Control polygon")
    if r2: out.append(r2)

    print()
    print("   --- persistence split: built-up vs open (data-centre polygon) ---")
    split = built_vs_open("DC_2026-06-23", "DC_2026-07-28")

    if not out:
        print("\n   NO DATA")
        return 2
    p = out[0]
    ok = p["improvement"] > 0.02 and p["frac_improved"] > 0.55
    print()
    verdict(ok,
            "PASS - within a 3 km cell the field varies by %.3f C sd, and %.0f%% of that is "
            "predictable from an earlier day. That is what FortyGuard adds over HRRR."
            % (p["sd_within3km"], 100 * max(0.0, p["r2"])),
            "FAIL - the sub-3km anomaly does not persist, so a learned per-site offset adds nothing "
            "over a regional forecast.")
    save_result("n5b_scale.json", {"pass": ok, "runs": out, "built_vs_open": split})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
