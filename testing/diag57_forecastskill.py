# -*- coding: utf-8 -*-
"""DIAG-57 -- How good IS FortyGuard's forecast, and does its error grow with lead? FREE, 0 API calls.

WHY THIS MATTERS MORE THAN ANYTHING ELSE OUTSTANDING
----------------------------------------------------
N-56 could not state a single free-cooling figure, only a range from +71 to +1,325 h/yr, because the
answer depends on a number nobody had measured: **how accurate is FortyGuard's forecast N hours ahead?**

That number is already on disk. On 2026-08-12 the project paid for forecasts of ONE target window
(14:00-16:00 site-local) issued at FIVE different leads -- 1.49, 3.49, 5.49, 7.49 and 9.41 h -- plus the
realised outcome for the same window. Same AOI, same granularity, 17,862 tiles each. Comparing them costs
nothing.

WHAT THIS CAN AND CANNOT ESTABLISH -- read before quoting
---------------------------------------------------------
CAN:  how the error behaves ACROSS LEAD on a single day, tile by tile, with 17,862 tiles per lead. If the
      error were dominated by lead-dependent noise it would grow with lead. If it is dominated by a level
      offset it will be roughly FLAT in lead. That shape is the whole question.
CANNOT: the day-to-day spread of the offset, because this is ONE day. Section 8e/2b already measured that
      separately from N-26's four pairs at ~9.4 h lead: day-mean offsets -0.84, -0.81, +0.15, -3.71 C.
      **n = 1 day here. Nothing about day-to-day variability may be claimed from this file.**

Also: the 17,862 tiles are NOT independent. Section 8e measured within-day spatial sd at only 0.06-0.29 C,
so for the LEVEL the effective sample size is close to 1, not 17,862. Spatial spread is reported, but no
confidence interval is put on the level from tile count -- that would be a fake precision.
"""
import io
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import banner, save_result, FIXTURES        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOURLY = os.path.join(ROOT, "AGENTIC-ARBITER", "data", "weather", "kiad_hourly_2021_2025.json")

LEADS = [("n25_f_lead01.49.json", 1.49), ("n25_f_lead03.49.json", 3.49),
         ("n25_f_lead05.49.json", 5.49), ("n25_f_lead07.49.json", 7.49),
         ("n25_f_lead09.41.json", 9.41)]
OUTCOME = "n25_outcome.json"


def tiles(fn):
    d = json.load(open(os.path.join(FIXTURES, fn), encoding="utf-8"))
    out = {}
    for f in d["map_data"]["features"]:
        p = f.get("properties") or {}
        if "tile_id" in p and p.get("average_temperature") is not None:
            out[p["tile_id"]] = float(p["average_temperature"])
    if not out:
        raise SystemExit("parsed 0 tiles from %s -- property names changed" % fn)
    return out


def persistence_sd(h):
    """sd of (T(t+h) - T(t)) over 5 real years -- what a reactive rule's error looks like at lead h."""
    d = json.load(open(HOURLY, encoding="utf-8"))
    it = d["meta"]["fields"].index("tmpc")
    keys = sorted(d["hours"])
    t = np.array([d["hours"][k][it] if d["hours"][k][it] is not None else np.nan for k in keys])
    t = t[~np.isnan(t)]
    n = max(1, int(round(h)))
    return float(np.std(t[n:] - t[:-n], ddof=1))


def main():
    banner("DIAG-57  FortyGuard forecast error vs LEAD, from already-paid fixtures   [FREE]")

    obs = tiles(OUTCOME)
    print("\n   outcome window: %d tiles" % len(obs))

    rows = []
    print("\n   %-8s %10s %10s %10s %10s %10s" % ("lead h", "mean_err", "sd_err", "spatial_sd",
                                                  "after_anch", "n_tiles"))
    print("   " + "-" * 66)
    for fn, lead in LEADS:
        fc = tiles(fn)
        common = sorted(set(fc) & set(obs))
        e = np.array([fc[k] - obs[k] for k in common])
        # "after anchoring" = remove the single per-day level offset, i.e. what a local sensor fixes
        resid = e - e.mean()
        rows.append({"lead_h": lead, "n_tiles": len(common),
                     "mean_error_c": float(e.mean()),
                     "sd_error_c": float(e.std(ddof=1)),
                     "spatial_sd_forecast_c": float(np.std([fc[k] for k in common], ddof=1)),
                     "sd_after_anchoring_c": float(resid.std(ddof=1)),
                     "rmse_c": float(np.sqrt((e ** 2).mean())),
                     "rmse_after_anchoring_c": float(np.sqrt((resid ** 2).mean()))})
        print("   %-8.2f %+10.4f %10.4f %10.4f %10.4f %10d"
              % (lead, e.mean(), e.std(ddof=1),
                 np.std([fc[k] for k in common], ddof=1), resid.std(ddof=1), len(common)))

    errs = [r["mean_error_c"] for r in rows]
    print("\n   [1] DOES THE ERROR GROW WITH LEAD?")
    print("      mean error runs %+.4f C at 1.49 h  ->  %+.4f C at 9.41 h" % (errs[0], errs[-1]))
    print("      range across a 7.9 h span of lead : %.4f C" % (max(errs) - min(errs)))
    ld = np.array([r["lead_h"] for r in rows])
    sl, ic = np.polyfit(ld, np.array(errs), 1)
    print("      least-squares slope              : %+.5f C per hour of lead" % sl)
    flat = abs(sl) * 8.0 < 0.5
    print("      => %s" % ("ESSENTIALLY FLAT. The error is a LEVEL OFFSET, not lead-dependent noise."
                           if flat else "the error DOES vary with lead."))

    print("\n   [2] WHAT DOES ANCHORING REMOVE?")
    print("      RMSE before anchoring : %.4f .. %.4f C" % (min(r["rmse_c"] for r in rows),
                                                           max(r["rmse_c"] for r in rows)))
    print("      RMSE after  anchoring : %.4f .. %.4f C" % (min(r["rmse_after_anchoring_c"] for r in rows),
                                                            max(r["rmse_after_anchoring_c"] for r in rows)))
    frac = 1.0 - (np.mean([r["rmse_after_anchoring_c"] for r in rows])
                  / np.mean([r["rmse_c"] for r in rows]))
    print("      => anchoring to a local sensor removes %.1f %% of the error magnitude" % (100 * frac))

    print("\n   [3] IS IT BETTER THAN A REACTIVE SENSOR'S PERSISTENCE GUESS?")
    print("      %-8s %14s %14s %10s" % ("lead h", "FG rmse", "persistence sd", "skill"))
    print("      " + "-" * 50)
    for r in rows:
        ps = persistence_sd(r["lead_h"])
        sk = 1.0 - (r["rmse_c"] / ps)
        ska = 1.0 - (r["rmse_after_anchoring_c"] / ps)
        r["persistence_sd_c"] = ps
        r["skill_vs_persistence"] = sk
        r["skill_after_anchoring"] = ska
        print("      %-8.2f %14.4f %14.4f %10.3f   (anchored %.3f)" % (r["lead_h"], r["rmse_c"], ps, sk, ska))

    print("\n      skill = 1 - (forecast error / persistence error).")
    print("      0 means no better than assuming nothing changes; 1 means perfect.")

    save_result("diag57_forecastskill.json", {
        "test": "DIAG-57 FortyGuard forecast error vs lead",
        "source": "already-paid N-25 fixtures, one target window, five leads + outcome",
        "n_days": 1,
        "caveats": [
            "ONE day. Nothing about day-to-day variability may be claimed here; see section 8e for "
            "the four-day spread of day-mean offsets (-0.84, -0.81, +0.15, -3.71 C).",
            "17,862 tiles are NOT independent -- within-day spatial sd is 0.06-0.29 C, so effective n "
            "for the LEVEL is near 1. No CI is placed on the level from tile count.",
        ],
        "slope_c_per_hour_of_lead": float(sl),
        "error_is_flat_in_lead": bool(flat),
        "anchoring_removes_fraction_of_error": float(frac),
        "rows": rows})
    print("\n   written: testing/results/diag57_forecastskill.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
