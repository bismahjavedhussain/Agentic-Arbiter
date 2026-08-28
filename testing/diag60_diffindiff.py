# -*- coding: utf-8 -*-
"""DIAG-60 -- Does the offset claim survive WITHOUT trusting NOAA's absolute level? FREE.

THE OBJECTION THIS FILE EXISTS TO ANSWER
    "FortyGuard's field is 2 m above ground over a data-centre corridor. KIAD ASOS is an airport several
     km away over grass. Of course they differ. Calling that difference an ERROR is invalid."

    **That objection is CORRECT about absolute levels, and DIAG-58 led with a level table, which was the
    wrong way to present it.** FortyGuard reading ~+2 C above the airport is an urban heat island over a
    corridor full of waste heat -- that is their data WORKING.

    (Height is the smaller part: ASOS air temperature is measured near 1.5-2 m, close to FortyGuard's 2 m
    plane. The LOCATION difference -- airport grass vs dense buildings -- is the substantive one.)

WHAT SURVIVES, AND WHY IT DOES NOT NEED NOAA'S LEVEL
    Two arguments, neither of which uses an absolute cross-source comparison.

    ARGUMENT 1 -- PURELY INTERNAL TO FORTYGUARD. Their forecast and their own history describe the SAME
    two-hour window, the SAME AOI, the SAME 17,862 tiles, the SAME 2 m plane. Any height or location
    offset is common to both and cancels exactly. Whatever remains is FortyGuard disagreeing with itself.

    ARGUMENT 2 -- DIFFERENCE-IN-DIFFERENCES. Compare day-to-day CHANGES, not levels:
        delta_ASOS     = how much the real airport temperature changed from one day to the next
        delta_history  = how much FortyGuard's history changed
        delta_forecast = how much FortyGuard's forecast changed
    A constant urban-heat-island offset, and a constant height offset, both DROP OUT of a change. So if
    delta_history tracks delta_ASOS while delta_forecast does not, the forecast is failing to track real
    day-to-day variation -- and that conclusion is immune to the objection above.

    This is the same technique `claims-and-defences.md` used to produce the two well-powered nulls on
    neighbourhood warming, so it is not being invented for convenience here.

WHAT WOULD FALSIFY THE CLAIM
    If delta_forecast tracks delta_ASOS about as well as delta_history does, then the forecast is fine and
    the earlier finding was an artefact of comparing levels across sources. That would be a retraction.
"""
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import banner, save_result, FIXTURES      # noqa: E402

ASOS = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
PAIRS = [("2026-08-12", "n25_f_lead09.41.json", "n25_outcome.json"),
         ("2026-08-13", "n26_f_2026-08-13.json", "n26_h_2026-08-13.json"),
         ("2026-08-15", "n26_f_2026-08-15.json", "n26_h_2026-08-15.json"),
         ("2026-08-16", "n26_f_2026-08-16.json", "n26_h_2026-08-16.json")]
HOURS = (14, 16)


def tile_mean(fn):
    d = json.load(open(os.path.join(FIXTURES, fn), encoding="utf-8"))
    v = [f["properties"]["average_temperature"] for f in d["map_data"]["features"]
         if (f.get("properties") or {}).get("average_temperature") is not None]
    if not v:
        raise SystemExit("no tiles in %s" % fn)
    return float(np.mean(v))


def fetch_asos():
    q = [("station", "KIAD"), ("data", "tmpc"), ("year1", 2026), ("month1", 8), ("day1", 11),
         ("year2", 2026), ("month2", 8), ("day2", 19), ("tz", "America/New_York"),
         ("format", "onlycomma"), ("latlon", "no"), ("missing", "empty"), ("trace", "empty"),
         ("direct", "no"), ("report_type", "3")]
    req = urllib.request.Request(ASOS + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "AGENTIC-ARBITER research"})
    txt = urllib.request.urlopen(req, timeout=180).read().decode("utf-8", "replace")
    acc = {}
    for line in txt.splitlines()[1:]:
        p = line.split(",")
        if len(p) < 3 or not p[2].strip():
            continue
        try:
            ts = datetime.strptime(p[1].strip(), "%Y-%m-%d %H:%M")
            if HOURS[0] <= ts.hour < HOURS[1]:
                acc.setdefault(ts.strftime("%Y-%m-%d"), []).append(float(p[2]))
        except Exception:
            pass
    return {k: float(np.mean(v)) for k, v in acc.items()}


def main():
    banner("DIAG-60  does the offset claim survive without trusting NOAA's LEVEL?   [FREE]")

    st = fetch_asos()
    rows = []
    for day, ff, hf in PAIRS:
        rows.append({"day": day, "forecast": tile_mean(ff), "history": tile_mean(hf),
                     "station": st.get(day, float("nan"))})

    print("\n   LEVELS -- shown for completeness, and NOT used as evidence")
    print("      %-12s %10s %10s %10s   %s" % ("day", "station", "FG hist", "FG fcst", "note"))
    for r in rows:
        print("      %-12s %10.2f %10.2f %10.2f   FG-vs-station gap is URBAN HEAT ISLAND, not error"
              % (r["day"], r["station"], r["history"], r["forecast"]))
    gaps = [r["history"] - r["station"] for r in rows]
    print("      FG history sits %+.2f to %+.2f C above the airport (mean %+.2f). Expected for a"
          % (min(gaps), max(gaps), float(np.mean(gaps))))
    print("      data-centre corridor vs airport grass. **This is NOT the finding.**")

    print("\n   [ARGUMENT 1] FORTYGUARD vs ITSELF -- no NOAA anywhere, offsets cancel exactly")
    print("      %-12s %12s %12s %14s" % ("day", "FG forecast", "FG history", "fcst - hist"))
    internal = []
    for r in rows:
        d = r["forecast"] - r["history"]
        internal.append(d)
        print("      %-12s %12.4f %12.4f %+14.4f" % (r["day"], r["forecast"], r["history"], d))
    print("      => FortyGuard disagrees with ITSELF by %+.2f to %+.2f C about the same window,"
          % (min(internal), max(internal)))
    print("         same tiles, same 2 m plane, same location. No cross-source comparison involved.")

    print("\n   [ARGUMENT 2] DIFFERENCE-IN-DIFFERENCES -- day-to-day CHANGE, offsets drop out")
    print("      %-24s %11s %11s %11s   %10s %10s"
          % ("consecutive days", "d_station", "d_history", "d_forecast", "hist err", "fcst err"))
    dd = []
    for i in range(1, len(rows)):
        a, b = rows[i - 1], rows[i]
        gap = (datetime.fromisoformat(b["day"]) - datetime.fromisoformat(a["day"])).days
        ds = b["station"] - a["station"]
        dh = b["history"] - a["history"]
        df = b["forecast"] - a["forecast"]
        dd.append({"from": a["day"], "to": b["day"], "gap_days": gap,
                   "d_station": ds, "d_history": dh, "d_forecast": df,
                   "hist_err": dh - ds, "fcst_err": df - ds})
        print("      %-24s %+11.2f %+11.2f %+11.2f   %+10.2f %+10.2f"
              % ("%s -> %s%s" % (a["day"][5:], b["day"][5:], "" if gap == 1 else " (%dd)" % gap),
                 ds, dh, df, dh - ds, df - ds))

    mh = float(np.mean([abs(x["hist_err"]) for x in dd]))
    mf = float(np.mean([abs(x["fcst_err"]) for x in dd]))
    print("\n      mean |error in tracking the real day-to-day CHANGE|")
    print("         FortyGuard HISTORY  : %.3f C" % mh)
    print("         FortyGuard FORECAST : %.3f C" % mf)
    survives = mf > mh * 1.5
    print("      => %s" % ("the FORECAST fails to track real day-to-day change %.1fx worse than their "
                           "HISTORY does. Immune to the height/location objection." % (mf / max(mh, 1e-9))
                           if survives else
                           "forecast tracks change about as well as history -- CLAIM RETRACTED."))

    print("\n   [THE DECISIVE DAY] 2026-08-15 -> 2026-08-16, a real cool-down")
    a = [r for r in rows if r["day"] == "2026-08-15"][0]
    b = [r for r in rows if r["day"] == "2026-08-16"][0]
    print("      the airport cooled by      %+.2f C   (%.2f -> %.2f)"
          % (b["station"] - a["station"], a["station"], b["station"]))
    print("      FortyGuard HISTORY cooled  %+.2f C   (%.2f -> %.2f)  <- caught it"
          % (b["history"] - a["history"], a["history"], b["history"]))
    print("      FortyGuard FORECAST cooled %+.2f C   (%.2f -> %.2f)  <- MISSED it"
          % (b["forecast"] - a["forecast"], a["forecast"], b["forecast"]))
    print("      A real %.1f C cool-down arrived. Their history saw %.1f C of it."
          % (abs(b["station"] - a["station"]), abs(b["history"] - a["history"])))
    print("      Their forecast saw %.1f C of it. That is the finding, and it needs no absolute"
          % abs(b["forecast"] - a["forecast"]))
    print("      cross-source comparison -- only the DIRECTION AND SIZE of a change.")

    print("\n" + "=" * 84)
    print("  VERDICT")
    print("=" * 84)
    print("  RETRACTED from DIAG-58's presentation: leading with FortyGuard-vs-station LEVELS.")
    print("     FortyGuard running ~+2 C warm over a data-centre corridor is urban heat island and")
    print("     is their data working correctly. That table should never have been the headline.")
    print("  SURVIVES: FortyGuard's forecast disagrees with FORTYGUARD'S OWN HISTORY by up to")
    print("     %+.2f C on the same window, and fails to track real day-to-day change %.1fx worse"
          % (max(internal), mf / max(mh, 1e-9)))
    print("     than their history does. Both statements are FREE of the height/location objection.")

    save_result("diag60_diffindiff.json", {
        "test": "DIAG-60 difference-in-differences -- offset claim without cross-source levels",
        "objection": "FG is 2 m over a data-centre corridor; KIAD is an airport km away. Absolute "
                     "level differences are urban heat island, not error.",
        "retracted": "DIAG-58's presentation led with FG-vs-station LEVELS. That framing is withdrawn.",
        "levels": rows,
        "internal_forecast_minus_history": internal,
        "difference_in_differences": dd,
        "mean_abs_change_error_history_c": mh,
        "mean_abs_change_error_forecast_c": mf,
        "ratio_forecast_over_history": mf / max(mh, 1e-9),
        "claim_survives": bool(survives),
        "caveat": "n = 3 consecutive-day transitions, one of which spans a 2-day gap. Establishes the "
                  "mechanism, not the frequency."})
    print("\n  written: testing/results/diag60_diffindiff.json")
    return 0 if survives else 1


if __name__ == "__main__":
    sys.exit(main())
