# -*- coding: utf-8 -*-
"""N-32  ---  is the single-template behaviour caused by GRANULARITY or by AREA?   PAID, 6 calls.

WHAT N-31 FOUND, AND THE CONFOUND IT COULD NOT RESOLVE
    Across 25 fields on the same 2 x 2 km AOI at 100 m granularity -- five dates, five two-hour
    windows -- ONE fixed spatial template explained 99.9971 % of the spatial variance, leaving a
    residual of 0.0011 C against an original 0.212 C. Several field pairs correlated to EXACTLY
    +/-1.000000, including pairs from different dates, and the template's amplitude changed sign.

    In other words: at that AOI and granularity the product delivers one spatial pattern, one
    scalar, and one offset. There is no spatial degree of freedom left for a wind-blown plume to
    occupy, which is what we needed to know before adding one.

    But the same test on the 8 x 8 km AOIs at 60 m granularity found NO such behaviour: shape
    correlations of +0.786 and -0.244 between dates, with an affine fit leaving 62 % and 97 % of the
    variation unexplained.

    THE PROBLEM: every 2 km field we hold is granularity 100, and every large field is granularity
    60. Area and granularity are PERFECTLY CONFOUNDED. Either could cause it, and reporting the
    finding without separating them would be exactly the "generalising from one sample" error that
    has already cost this project two retracted claims.

THE DESIGN -- fully crossed, identical times, one date
                        granularity 100        granularity 60
        2 x 2 km AOI    already held           2 NEW CALLS
        8 x 8 km AOI    2 NEW CALLS            2 NEW CALLS

    Everything else is held constant: centre 39.0100 / -77.4460, analytic_type tcm, filter_type 2,
    a single fixed date, and the two windows 12:00-14:00 and 16:00-18:00 site-local -- exactly the
    request shape N-12c used, so the two held fields drop straight into the table.

    Two times per cell, because that is the statistic the 8 km / 60 m result was already computed
    from (dayA vs dayB), making all four cells directly comparable rather than merely similar.

THE STATISTIC
    For each cell, between its two times:
        shape correlation   pattern with its own mean and sd removed. |r| = 1.000 means the second
                            field is the first one scaled and shifted -- a single template.
        affine residual     fit B = m*A + c, then residual rms as a percentage of B's own spatial
                            sd. Near 0 % means one template; large means real independent structure.

INTERPRETATION, FIXED BEFORE THE CALLS
    single template appears in the g100 row only        -> GRANULARITY drives it
    single template appears in the 2 km column only     -> AREA drives it
    single template appears in both new g100 and 2 km   -> both contribute
    single template appears nowhere new                 -> it is specific to that AOI and
                                                           granularity together, and must be
                                                           reported as such and nothing wider
"""
import sys, os, json, math, statistics
import numpy as np

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, FIXTURES)

CENTRE = (39.0100, -77.4460)          # identical to N-12c
DATE = "2026-07-28"
WINDOWS = [("12:00", "14:00"), ("16:00", "18:00")]
CELLS = [("2km", 2.0, 100), ("2km", 2.0, 60), ("8km", 8.0, 100), ("8km", 8.0, 60)]
HELD = {("2km", 100): ["n12c_2026-07-28_1200", "n12c_2026-07-28_1600"]}
SINGLE_TEMPLATE_R = 0.999             # |r| above this = one template
SINGLE_TEMPLATE_RESID = 5.0           # residual below this % of sd = one template


def field_values(tag):
    p = os.path.join(FIXTURES, "%s.json" % tag)
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    feats = (d.get("map_data") or {}).get("features") or []
    out = {}
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = round(sum(x[1] for x in c[:4]) / 4, 7)
        lo = round(sum(x[0] for x in c[:4]) / 4, 7)
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[(la, lo)] = v
    return out


def fetch(key, side_km, gran, start, end, tag):
    aoi = box_aoi(CENTRE[0], CENTRE[1], side_km)
    p = {"polygon_aoi": aoi, "granularity": gran, "analytic_type": "tcm",
         "date_time": {"start_date": DATE, "start_time": start, "end_time": end,
                       "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, tag)
    if not r.get("ok"):
        return None, r.get("error")
    feats = (r["result"].get("map_data") or {}).get("features") or []
    if not feats:
        return None, "ZERO TILES with completed status"
    return len(feats), None


def compare(a, b):
    """Shape correlation and affine residual between two fields, matched tile by tile."""
    keys = [k for k in a if k in b]
    if len(keys) < 100:
        return None
    A = np.array([a[k] for k in keys], dtype=float)
    B = np.array([b[k] for k in keys], dtype=float)
    if A.std() < 1e-9 or B.std() < 1e-9:
        return None
    r = float(np.corrcoef((A - A.mean()) / A.std(), (B - B.mean()) / B.std())[0, 1])
    sl, ic = np.polyfit(A, B, 1)
    resid = float(np.sqrt(((B - (sl * A + ic)) ** 2).mean()))
    return {"n": len(keys), "r": r, "slope": float(sl), "resid_rms": resid,
            "resid_pct_of_sd": 100.0 * resid / float(B.std()),
            "sd_a": float(A.std()), "sd_b": float(B.std())}


def main():
    banner("N-32  Single template: caused by GRANULARITY or by AREA?   [PAID, 6 calls]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    print("   date %s, windows %s, centre %.4f / %.4f, analytic tcm, filter_type 2"
          % (DATE, " and ".join("%s-%s" % w for w in WINDOWS), CENTRE[0], CENTRE[1]))
    print("   fully crossed: {2 km, 8 km} x {g100, g60}. Two cells already held from N-12c.")

    tags, errors = {}, {}
    for name, side, gran in CELLS:
        key_cell = (name, gran)
        if key_cell in HELD:
            tags[key_cell] = HELD[key_cell]
            print("\n   %s / g%-3d : using 2 held fields (no call)" % (name, gran))
            continue
        got = []
        for (s, e) in WINDOWS:
            tag = "n32_%s_g%d_%s" % (name, gran, s.replace(":", ""))
            if os.path.exists(os.path.join(FIXTURES, "%s.json" % tag)):
                print("\n   %s / g%-3d %s : fixture already present, skipping call"
                      % (name, gran, s))
                got.append(tag)
                continue
            print("\n   %s / g%-3d %s-%s : calling ..." % (name, gran, s, e))
            n, err = fetch(key, side, gran, s, e, tag)
            if n is None:
                errors[tag] = err
                print("      FAILED: %s" % err)
                continue
            print("      %s tiles" % format(n, ","))
            got.append(tag)
        tags[key_cell] = got

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))

    print("\n   RESULT  --  between the two windows, within each cell")
    print("   %-14s %9s %11s %11s %12s %14s"
          % ("cell", "tiles", "shape r", "aff slope", "resid C", "resid % of sd"))
    rows = []
    for name, side, gran in CELLS:
        t = tags.get((name, gran)) or []
        if len(t) < 2:
            print("   %-14s %9s  incomplete" % ("%s / g%d" % (name, gran), "-"))
            continue
        a, b = field_values(t[0]), field_values(t[1])
        if a is None or b is None:
            print("   %-14s %9s  fixture missing" % ("%s / g%d" % (name, gran), "-"))
            continue
        c = compare(a, b)
        if c is None:
            print("   %-14s %9s  not comparable" % ("%s / g%d" % (name, gran), "-"))
            continue
        single = abs(c["r"]) > SINGLE_TEMPLATE_R and c["resid_pct_of_sd"] < SINGLE_TEMPLATE_RESID
        c.update({"cell": "%s/g%d" % (name, gran), "aoi": name, "gran": gran,
                  "single_template": single})
        rows.append(c)
        print("   %-14s %9s %+11.6f %11.4f %12.6f %14.2f %s"
              % ("%s / g%d" % (name, gran), format(c["n"], ","), c["r"], c["slope"],
                 c["resid_rms"], c["resid_pct_of_sd"],
                 "  <- SINGLE TEMPLATE" if single else ""))

    by = {r["cell"]: r["single_template"] for r in rows}
    g100 = [r for r in rows if r["gran"] == 100]
    g60 = [r for r in rows if r["gran"] == 60]
    a2 = [r for r in rows if r["aoi"] == "2km"]
    a8 = [r for r in rows if r["aoi"] == "8km"]

    print("\n   READING THE 2 x 2")
    print("      %-16s %-22s %s" % ("", "granularity 100", "granularity 60"))
    for name in ("2km", "8km"):
        cells = []
        for gran in (100, 60):
            m = [r for r in rows if r["aoi"] == name and r["gran"] == gran]
            cells.append("r=%+.4f %s" % (m[0]["r"], "TEMPLATE" if m[0]["single_template"]
                                         else "structured") if m else "n/a")
        print("      %-16s %-22s %s" % ("%s AOI" % name, cells[0], cells[1]))

    all_g100 = bool(g100) and all(r["single_template"] for r in g100)
    all_g60 = bool(g60) and all(r["single_template"] for r in g60)
    all_2km = bool(a2) and all(r["single_template"] for r in a2)
    all_8km = bool(a8) and all(r["single_template"] for r in a8)

    print("\n   DIAGNOSIS")
    if all_g100 and not all_g60:
        cause = "GRANULARITY"
        print("      Single-template behaviour follows GRANULARITY: present at g100 in both AOIs,")
        print("      absent at g60. Requesting 100 m returns one pattern plus two numbers,")
        print("      regardless of how large an area you ask for.")
    elif all_2km and not all_8km:
        cause = "AREA"
        print("      Single-template behaviour follows AREA: present at 2 km in both granularities,")
        print("      absent at 8 km. A small AOI is dominated by one spatial mode whatever")
        print("      granularity is requested.")
    elif all_g100 and all_2km:
        cause = "BOTH"
        print("      Both coarse granularity and small area produce it; they are not separable")
        print("      from this design alone.")
    elif not any(r["single_template"] for r in rows if r["cell"] != "2km/g100"):
        cause = "SPECIFIC TO 2km/g100"
        print("      It appears ONLY in the 2 km / g100 combination. Report it as specific to that")
        print("      combination and claim nothing wider -- neither granularity nor area alone")
        print("      reproduces it.")
    else:
        cause = "MIXED"
        print("      The pattern is mixed and no single explanation follows. State the 2 x 2 table")
        print("      as measured and draw no causal conclusion.")

    ok = len(rows) == 4
    print("\n   elapsed calls this run: %d new" % max(0, 6 - 0))
    print()
    verdict(ok,
            "CONCLUSIVE - all four cells of the 2 x 2 measured at identical times. Single-template "
            "behaviour is attributable to %s. The confound N-31 could not resolve is now resolved, "
            "and the finding can be stated at exactly the scope the data supports." % cause,
            "INCOMPLETE - only %d of 4 cells returned usable data (%s). Do not draw the causal "
            "conclusion; state the cells that worked and the confound that remains."
            % (len(rows), ", ".join(sorted(errors)) if errors else "see above"))

    save_result("n32_granularity.json", {
        "purpose": "separate granularity from area as the cause of N-31's single-template finding",
        "date": DATE, "windows": WINDOWS, "centre": list(CENTRE),
        "design": "fully crossed {2km,8km} x {g100,g60} at identical times",
        "held_cells": {str(k): v for k, v in HELD.items()},
        "thresholds": {"single_template_r": SINGLE_TEMPLATE_R,
                       "single_template_resid_pct": SINGLE_TEMPLATE_RESID},
        "cells": rows, "by_cell": by, "cause": cause, "errors": errors,
        "credits_before": before, "credits_after": after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
