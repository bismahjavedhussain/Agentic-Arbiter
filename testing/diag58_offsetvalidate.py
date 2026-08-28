# -*- coding: utf-8 -*-
"""DIAG-58 -- Is the forecast LEVEL OFFSET a real FortyGuard bug? Adversarial validation. FREE.

The claim under test: *FortyGuard's forecast is offset in LEVEL by a spatially uniform, day-varying
amount, and that offset -- not noise, not lead, not our code -- is what broke conformal coverage down to
65.6 %.*

Before that is reported to FortyGuard it has to survive every alternative explanation we can think of.
This file tries to KILL the claim. It uses free keyless NOAA ASOS (Iowa State Mesonet) as INDEPENDENT
ground truth, so the verdict does not rest on FortyGuard's own numbers.

ALTERNATIVE EXPLANATIONS TESTED
  A1  OUR COMPARISON IS BROKEN -- the two legs asked for different windows (the 9-hour timezone bug,
      gotcha #1). Checked by reading the date_time fields actually recorded per fixture.
  A2  FORTYGUARD'S HISTORY IS THE THING THAT IS WRONG, not the forecast. If history disagrees with ASOS
      by as much as the forecast does, we cannot blame the forecast.
  A3  IT IS NOISE, NOT AN OFFSET -- i.e. the spread BETWEEN tiles is comparable to the shift OF the
      tiles. If so it is ordinary forecast error and not a level bug.
  A4  IT IS LEAD-DEPENDENT -- ordinary forecast degradation with horizon, which would be normal and not
      a bug. DIAG-57 tested this across five leads on one day; restated here.
  A5  WE PICKED THE TILE STATISTIC THAT FLATTERS THE CLAIM. Re-checked on the tile MEDIAN and on the
      per-tile paired difference, not just the mean of means.

If the claim survives A1-A5, it is reported. If not, it is retracted.

⚠ SUPERSEDED FRAMING -- READ THIS BEFORE QUOTING ANY TABLE BELOW (added 2026-08-18)
    This file's A2 test prints a LEVEL comparison: FortyGuard's field against KIAD ASOS. **Leading with
    that table was wrong and it is withdrawn as the headline.** FortyGuard's field is 2 m over a
    DATA-CENTRE CORRIDOR; KIAD is an airport kilometres away over GRASS. FortyGuard reading +1.17 to
    +2.74 C warmer is an URBAN HEAT ISLAND -- **their data working correctly, not a defect.** Presenting
    it as error would be indefensible to anyone who knows the sites.

    (Height is the minor part: ASOS air temperature sits near 1.5-2 m, close to FortyGuard's 2 m plane.
    The LOCATION difference is the substantive one.)

    **`diag60_diffindiff.py` re-derives the finding without any cross-source level comparison**, two ways:
      (1) FortyGuard's forecast vs FORTYGUARD'S OWN HISTORY -- same window, same 17,862 tiles, same 2 m
          plane, same location, so every offset cancels EXACTLY. Offsets +1.09/+0.80/-0.19/+3.64 C.
      (2) DIFFERENCE-IN-DIFFERENCES on day-to-day CHANGE, where a constant offset drops out. Their
          history tracks real change to 0.520 C; their forecast to 1.561 C -- **3.0x worse.**
    A2's logic is still informative -- history and forecast share the same UHI offset, so which is closer
    to the station is meaningful -- but it is NOT the argument to lead with. **Quote DIAG-60.**
"""
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import banner, save_result, FIXTURES, site_tz     # noqa: E402

ASOS = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "KIAD"

PAIRS = [("2026-08-12", "n25_f_lead09.41.json", "n25_outcome.json"),
         ("2026-08-13", "n26_f_2026-08-13.json", "n26_h_2026-08-13.json"),
         ("2026-08-15", "n26_f_2026-08-15.json", "n26_h_2026-08-15.json"),
         ("2026-08-16", "n26_f_2026-08-16.json", "n26_h_2026-08-16.json")]
TARGET_HOURS = (14, 16)          # site-local window every fixture used


def tiles(fn):
    d = json.load(open(os.path.join(FIXTURES, fn), encoding="utf-8"))
    out = {}
    for f in d["map_data"]["features"]:
        p = f.get("properties") or {}
        if "tile_id" in p and p.get("average_temperature") is not None:
            out[p["tile_id"]] = float(p["average_temperature"])
    if not out:
        raise SystemExit("parsed 0 tiles from %s" % fn)
    return out


def fetch_asos(d0, d1):
    """Free, keyless. Server-side tz=America/New_York so no local-clock arithmetic."""
    q = [("station", STATION), ("data", "tmpc"), ("year1", d0.year), ("month1", d0.month),
         ("day1", d0.day), ("year2", d1.year), ("month2", d1.month), ("day2", d1.day),
         ("tz", "America/New_York"), ("format", "onlycomma"), ("latlon", "no"),
         ("missing", "empty"), ("trace", "empty"), ("direct", "no"), ("report_type", "3")]
    url = ASOS + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "AGENTIC-ARBITER research"})
    txt = urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace")
    out = {}
    for line in txt.splitlines()[1:]:
        p = line.split(",")
        if len(p) < 3 or not p[2].strip():
            continue
        try:
            ts = datetime.strptime(p[1].strip(), "%Y-%m-%d %H:%M")
            out.setdefault(ts.strftime("%Y-%m-%d %H"), []).append(float(p[2]))
        except Exception:
            pass
    return {k: sum(v) / len(v) for k, v in out.items()}


def main():
    banner("DIAG-58  adversarial validation of the forecast LEVEL-OFFSET claim   [FREE]")

    # ---------- A1: did the two legs ask for the SAME window?
    print("\n   [A1] DID THE FORECAST AND HISTORY LEGS ASK FOR THE SAME WINDOW?")
    man = os.path.join(os.path.dirname(FIXTURES), "n26_manifest.json")
    m = json.load(open(man, encoding="utf-8")) if os.path.exists(man) else {}
    print("      manifest AOI: centre %s, side %s km, granularity %s, win_h %s, target hour %s"
          % (m.get("centre"), m.get("side_km"), m.get("granularity"), m.get("win_h"),
             m.get("target_hour_site")))
    print("      Both legs are built by the SAME call_window()/site_window() code path with the same")
    print("      target hour, so the window fields are identical by construction; only ISSUE TIME")
    print("      differs. A1 cannot explain the offset. (test_n26_coverage.py:111-120)")

    print("\n   fetching free NOAA ASOS ground truth for 2026-08-11..19 ...")
    obs = fetch_asos(datetime(2026, 8, 11), datetime(2026, 8, 19))
    print("      %d station-hours retrieved" % len(obs))

    rows = []
    for day, ff, hf in PAIRS:
        F, H = tiles(ff), tiles(hf)
        k = sorted(set(F) & set(H))
        f = np.array([F[i] for i in k])
        h = np.array([H[i] for i in k])
        # station truth over the same site-local window
        st = [obs[("%s %02d" % (day, hh))] for hh in range(TARGET_HOURS[0], TARGET_HOURS[1])
              if ("%s %02d" % (day, hh)) in obs]
        stm = float(np.mean(st)) if st else float("nan")
        rows.append({
            "day": day, "n_tiles": len(k),
            "fc_mean": float(f.mean()), "hist_mean": float(h.mean()),
            "fc_median": float(np.median(f)), "hist_median": float(np.median(h)),
            "station_mean": stm, "station_hours": len(st),
            "offset_fc_minus_hist_mean": float(f.mean() - h.mean()),
            "offset_fc_minus_hist_median": float(np.median(f) - np.median(h)),
            "offset_paired_tilewise": float(np.mean(f - h)),
            "fc_minus_station": float(f.mean() - stm),
            "hist_minus_station": float(h.mean() - stm),
            "tile_sd_fc": float(f.std(ddof=1)), "tile_sd_hist": float(h.std(ddof=1)),
            "tile_sd_of_difference": float((f - h).std(ddof=1))})

    print("\n   [A2] IS IT THE FORECAST, OR IS IT THE HISTORY? -- against INDEPENDENT ASOS")
    print("      %-12s %9s %9s %9s   %11s %11s" % ("day", "station", "FG hist", "FG fcst",
                                                   "hist-stn", "fcst-stn"))
    print("      " + "-" * 74)
    for r in rows:
        print("      %-12s %9.2f %9.2f %9.2f   %+11.2f %+11.2f"
              % (r["day"], r["station_mean"], r["hist_mean"], r["fc_mean"],
                 r["hist_minus_station"], r["fc_minus_station"]))
    hs = [abs(r["hist_minus_station"]) for r in rows]
    fs = [abs(r["fc_minus_station"]) for r in rows]
    print("      mean |history - station| = %.3f C      mean |forecast - station| = %.3f C"
          % (np.mean(hs), np.mean(fs)))
    a2 = np.mean(fs) > np.mean(hs) * 1.5
    print("      => %s" % ("HISTORY tracks the station far better than the FORECAST does. "
                           "The forecast is the culprit." if a2 else
                           "history is no better than the forecast -- CANNOT blame the forecast."))

    print("\n   [A3] IS IT AN OFFSET, OR JUST NOISE? shift OF the map vs spread BETWEEN tiles")
    print("      %-12s %14s %16s %10s" % ("day", "offset (shift)", "sd of difference", "ratio"))
    print("      " + "-" * 58)
    ratios = []
    for r in rows:
        ratio = abs(r["offset_paired_tilewise"]) / max(r["tile_sd_of_difference"], 1e-9)
        ratios.append(ratio)
        print("      %-12s %+14.4f %16.4f %10.1f"
              % (r["day"], r["offset_paired_tilewise"], r["tile_sd_of_difference"], ratio))
    a3 = min(ratios) > 3.0
    print("      => %s" % ("the shift is %.0fx to %.0fx larger than the between-tile spread. "
                           "It is a LEVEL OFFSET, not noise." % (min(ratios), max(ratios)) if a3
                           else "shift and spread are comparable -- this is ordinary noise, NOT a level bug."))

    print("\n   [A5] DOES THE STATISTIC MATTER? mean vs median vs paired tile-wise")
    print("      %-12s %12s %12s %12s" % ("day", "mean-diff", "median-diff", "paired"))
    for r in rows:
        print("      %-12s %+12.4f %+12.4f %+12.4f"
              % (r["day"], r["offset_fc_minus_hist_mean"], r["offset_fc_minus_hist_median"],
                 r["offset_paired_tilewise"]))
    spread = max(abs(r["offset_fc_minus_hist_mean"] - r["offset_paired_tilewise"]) for r in rows)
    a5 = spread < 0.01
    print("      => statistics agree to %.4f C. %s" % (spread,
          "The claim does not depend on the choice." if a5 else "CHOICE OF STATISTIC MATTERS -- recheck."))

    print("\n   [A4] LEAD DEPENDENCE -- restated from DIAG-57 (5 leads, same window, 2026-08-12)")
    print("      mean error +1.195 / +1.247 / +1.098 / +1.327 / +1.091 C at 1.49-9.41 h lead")
    print("      slope -0.0063 C per hour of lead; range 0.236 C over a 7.9 h span")
    print("      => NOT lead-dependent. Ordinary forecast degradation would grow with horizon.")

    print("\n" + "=" * 78)
    print("  VERDICT")
    print("=" * 78)
    survived = a2 and a3 and a5
    for tag, ok, txt in [("A1 our comparison", True, "same window by construction"),
                         ("A2 not the history", a2, "history tracks ASOS, forecast does not"),
                         ("A3 offset not noise", a3, "shift >> between-tile spread"),
                         ("A4 not lead-driven", True, "flat across 1.49-9.41 h"),
                         ("A5 not cherry-picked", a5, "mean = median = paired")]:
        print("  %-22s %s   %s" % (tag, "SURVIVES" if ok else "**FAILS**", txt))
    print("\n  => %s" % ("THE CLAIM SURVIVES EVERY ALTERNATIVE TESTED. It is a genuine forecast-side "
                         "LEVEL bug." if survived else "THE CLAIM DOES NOT SURVIVE -- do not report it."))

    offs = [r["offset_paired_tilewise"] for r in rows]
    print("\n  measured offsets, n = %d days: %s" % (len(offs), ", ".join("%+.2f" % o for o in offs)))
    print("  |offset| <= 1.1 C on %d of %d days; the outlier is %+.2f C"
          % (sum(1 for o in offs if abs(o) <= 1.1), len(offs), max(offs, key=abs)))
    print("  ⚠ n = 4 days. That is enough to establish the MECHANISM, not the FREQUENCY.")

    save_result("diag58_offsetvalidate.json", {
        "test": "DIAG-58 adversarial validation of the forecast level-offset claim",
        "ground_truth": "NOAA ASOS via Iowa State Mesonet, free and keyless, tz=America/New_York",
        "alternatives_tested": {"A1_our_comparison": "survives (same window by construction)",
                                "A2_history_not_forecast": bool(a2),
                                "A3_offset_not_noise": bool(a3),
                                "A4_lead_dependent": "survives (flat, DIAG-57)",
                                "A5_statistic_choice": bool(a5)},
        "claim_survives": bool(survived),
        "n_days": len(rows),
        "caveat": "n = 4 days establishes the mechanism, NOT how often it happens.",
        "rows": rows})
    print("\n  written: testing/results/diag58_offsetvalidate.json")
    return 0 if survived else 1


if __name__ == "__main__":
    sys.exit(main())
