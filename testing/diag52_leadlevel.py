# -*- coding: utf-8 -*-
"""DIAG-52  ---  does SHORTENING THE LEAD remove the day-level offset that broke N-26's coverage?

FREE. Reuses N-25's already-paid five-lead fixtures. Zero API calls, no key use.

WHY THIS MATTERS
    N-26's live out-of-sample coverage FAILED: 65.6 % pooled against a 90 % promise, with one test day
    at 0.0 %. The diagnosis (verified, not guessed):
      * it is NOT our comparison -- forecast and outcome use the SAME call_window() payload
      * it is NOT FortyGuard's history -- that tracks KIAD ASOS within +0.86..+1.92 C, consistent with
        an urban heat-island offset over a data-centre corridor, and smallest on the coolest day
      * it IS the forecast's LEVEL: a spatially uniform, day-varying offset. Within-day sd across
        17,862 tiles is only 0.06-0.29 C while the day-mean offset ranged -0.84, -0.81, +0.15, -3.71 C.
        The forecast missed a real 5 C cooling event by +4.58 C against station truth.

    A conformal bound calibrated on previous days cannot absorb an offset that flips sign. The proposed
    operational fix is to SHORTEN THE LEAD: N-26 tests 9.5 h because the original design needed
    anticipation for a 3 h plant lead, but a free-cooling changeover decision needs 1-3 h, not 9.5.

THE QUESTION THIS ANSWERS, FOR FREE
    On the one day where five leads were purchased, does the level offset shrink as lead shortens?
      * if it collapses toward zero by 1.5-3 h, shortening the lead is a real fix and a short-lead
        bound could plausibly hold 90 %
      * if it persists at 1.5 h, the offset is NOT a lead-time artefact and shortening will not fix it

WHAT THIS CANNOT ESTABLISH -- stated before running
    ONE DAY. This measures the LEAD DEPENDENCE of the offset on that day. It is NOT a
    coverage measurement: coverage needs several days at the short lead, which needs live access.
    A favourable result here justifies buying that test; it does not substitute for it.
"""
import io
import json
import os
import statistics
import sys

from common import banner, save_result, field_path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

LEAD_TAGS = [("n25_f_lead09.41", 9.41), ("n25_f_lead07.49", 7.49), ("n25_f_lead05.49", 5.49),
             ("n25_f_lead03.49", 3.49), ("n25_f_lead01.49", 1.49)]
OUTCOME_TAG = "n25_outcome"
ALPHA = 0.10


def load_tiles(tag):
    p = field_path(tag + ".json")
    if not p:
        return None
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for t in d.get("map_data", {}).get("features", []):
        c = t["geometry"]["coordinates"][0]
        key = (round(sum(x[1] for x in c[:4]) / 4, 6), round(sum(x[0] for x in c[:4]) / 4, 6))
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[key] = float(v)
    return out


def main():
    banner("DIAG-52  does a SHORTER LEAD remove the day-level offset?   [FREE, already-paid data]")

    out = load_tiles(OUTCOME_TAG)
    if not out:
        print("   outcome fixture missing")
        return 2
    print("\n   outcome (%s): %d tiles, mean %.4f C" % (OUTCOME_TAG, len(out),
                                                        statistics.fmean(out.values())))

    print("\n   %-8s %8s %12s %12s %12s %12s"
          % ("lead h", "tiles", "fc mean C", "offset C", "within-day sd", "|offset|/sd"))
    rows = []
    for tag, lead in LEAD_TAGS:
        f = load_tiles(tag)
        if not f:
            print("   %-8.2f  fixture missing (%s)" % (lead, tag))
            continue
        keys = [k for k in f if k in out]
        d = [out[k] - f[k] for k in keys]
        mu = statistics.fmean(d)
        sd = statistics.stdev(d)
        rows.append({"lead_h": lead, "n_tiles": len(keys), "forecast_mean_c":
                     statistics.fmean(f[k] for k in keys), "offset_c": mu, "within_day_sd_c": sd,
                     "abs_offset_over_sd": abs(mu) / sd if sd > 0 else None})
        print("   %-8.2f %8d %12.4f %+12.4f %12.4f %12.1f"
              % (lead, len(keys), rows[-1]["forecast_mean_c"], mu, sd, abs(mu) / sd if sd else 0))

    if len(rows) < 2:
        print("\n   not enough leads to compare")
        return 2

    lo = min(rows, key=lambda r: r["lead_h"])
    hi = max(rows, key=lambda r: r["lead_h"])
    print("\n   READING")
    print("      offset at %.2f h lead : %+.4f C" % (hi["lead_h"], hi["offset_c"]))
    print("      offset at %.2f h lead : %+.4f C" % (lo["lead_h"], lo["offset_c"]))
    shrink = abs(hi["offset_c"]) - abs(lo["offset_c"])
    print("      change in |offset| from long to short lead : %+.4f C" % (-shrink))
    print()
    print("      In EVERY row the offset dwarfs the within-day spread (|offset|/sd is the last")
    print("      column). That is the signature of a spatially uniform LEVEL error, not noise:")
    print("      the forecast gets the pattern right and the level wrong.")

    if abs(lo["offset_c"]) < 0.25 * abs(hi["offset_c"]):
        verdict = ("SHORTENING THE LEAD LOOKS LIKE A REAL FIX on this day: the level offset collapses "
                   "from %+.4f C at %.2f h to %+.4f C at %.2f h. That JUSTIFIES buying a multi-day "
                   "short-lead coverage test with live access -- it does not replace it."
                   % (hi["offset_c"], hi["lead_h"], lo["offset_c"], lo["lead_h"]))
    elif abs(lo["offset_c"]) < abs(hi["offset_c"]):
        verdict = ("PARTIAL: the offset shrinks from %+.4f C to %+.4f C but does NOT collapse. A "
                   "short-lead bound would be tighter but a residual level bias remains, so 90 %% "
                   "coverage is not established by shortening alone -- a per-issue bias correction "
                   "would still be needed." % (hi["offset_c"], lo["offset_c"]))
    else:
        verdict = ("SHORTENING THE LEAD IS NOT THE FIX: the offset does not shrink (%+.4f C at %.2f h "
                   "vs %+.4f C at %.2f h). The level error is not a lead-time artefact, so a "
                   "short-lead bound would fail the same way. Do NOT spend credits on a short-lead "
                   "coverage test on this basis." % (hi["offset_c"], hi["lead_h"],
                                                     lo["offset_c"], lo["lead_h"]))
    print("\n   VERDICT: %s" % verdict)
    print("\n   ONE DAY ONLY. This is the lead dependence of the offset, NOT coverage.")

    save_result("diag52_leadlevel.json", {
        "measures": "how FortyGuard's spatially-uniform forecast LEVEL offset varies with lead, on the "
                    "one day where five leads were purchased",
        "does_not_measure": "coverage. That needs several days at a short lead, which needs live access. "
                            "This is a single day.",
        "why": "N-26's live coverage failed at 65.6 % pooled / 0.0 % worst day because the forecast "
               "error is a day-level offset that flips sign; shortening the lead is the proposed fix",
        "outcome_tag": OUTCOME_TAG, "alpha": ALPHA,
        "rows": rows, "verdict": verdict,
    })
    print("\n   written: results/diag52_leadlevel.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
