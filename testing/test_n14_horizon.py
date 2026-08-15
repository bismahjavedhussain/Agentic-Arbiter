# -*- coding: utf-8 -*-
"""N-14  ---  where does usable data ACTUALLY start and stop?   PAID.

*** OFFSETS INVALIDATED 2026-08-12 BY THE 9-HOUR TIMEZONE BUG. DO NOT QUOTE ITS BOUNDARIES. ***

    This file builds windows from datetime.now() -- machine local, UTC+5 -- while the endpoint reads
    them in the AOI's local zone, UTC-4. Every entry in OFFSETS is therefore shifted by nine hours:
    the "+2 h" probe was really +11 h, and "+4 h" onward were all outside the 12 h horizon.

    Note that the docstring below ALREADY listed a timezone as a candidate explanation. It was the
    right hypothesis and it was never tested. It has now been settled by two independent arguments
    from data already on disk -- see the time section of common.py.

    The horizon is CONFIRMED at 12 h: 9.25 h and 11.25 h return data, 13.25 h and 17.25 h return
    zero tiles, and a 9.41 h lead returned 17,862 tiles on 2026-08-12.

    If re-run, convert OFFSETS through common.site_window() first.

WHY THIS SUDDENLY MATTERS MORE THAN ANYTHING ELSE

The whole INTAKE design assumes a rolling 12-hour forecast: the stopping rule in N-9 reasons over
a 12-hour horizon, and the agent's daily cycle is "one heatmap call gives me the next 12 h".
N-13 leg1 contradicted that. Issued at 16:45 local:

    +1 h window  ->  397 tiles
    +3 h window  ->  397 tiles
    +5 h window  ->  ZERO TILES with status completed
    +9 h window  ->  ZERO TILES with status completed

Three explanations with very different consequences, and they must not be guessed between:

  A TIMEZONE. The endpoint may interpret start_time in the site's local zone while this machine
    reports a different one. The timezone label is already a documented defect: it reads GMT-5
    in July AND August, so it cannot be trusted to disambiguate.
  B INGEST LAG AT THE BOUNDARY. Windows that have only just ended may have neither a forecast
    nor a finalised history, leaving a hole around "now".
  C THE HORIZON IS SHORTER THAN 12 h, at least at this time of day.

If C is true the staging horizon must shrink, which changes N-9's problem shape. If A or B, the
12 h horizon survives but the request builder needs fixing.

METHOD
    Probe a ladder of 2-hour windows from well in the past to well in the future and record, for
    each, whether tiles came back. The boundaries of the non-empty region give the real usable
    span. Windows never cross midnight (the endpoint takes one start_date) and are always >= 2 h
    (start_time == end_time returns HTTP 500, found in N-12b).

    A deliberately coarse probe on purpose: the aim is to locate the edges, not to be pretty.
"""
import sys, statistics
from datetime import datetime, timedelta

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 1.0          # small: this test is about availability, not spatial detail
GRAN = 100
WIN_H = 2
# hours relative to now; negative = past. Chosen to bracket both edges.
OFFSETS = [-30, -24, -12, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 18, 24]


def probe(key, aoi, st, en):
    if st.date() != en.date():
        return "skipped: crosses midnight", None
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {"start_date": st.strftime("%Y-%m-%d"),
                       "start_time": st.strftime("%H:00"),
                       "end_time": en.strftime("%H:00"), "filter_type": 2}}
    r = submit_poll(key, "heatmap", p, "n14_%s_%s" % (st.strftime("%Y%m%d"), st.strftime("%H")))
    if not r.get("ok"):
        return "error: %s" % str(r.get("error"))[:60], None
    f = (r["result"].get("map_data") or {}).get("features") or []
    if not f:
        return "EMPTY", None
    v = [t["properties"].get("max_temperature") for t in f]
    v = [x for x in v if x is not None]
    return "ok (%d tiles)" % len(f), (statistics.fmean(v) if v else None)


def main():
    banner("N-14  Real usable data span: probing a ladder of windows around now   [PAID]")
    key = load_key()
    before = credits_remaining(key)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    print("   machine local now: %s   (timezone label from the API is a known defect: GMT-5 in"
          % now.strftime("%Y-%m-%d %H:%M"))
    print("   both July and August, so it cannot be used to disambiguate)")
    aoi = box_aoi(CENTRE[0], CENTRE[1], SIDE_KM)

    rows = []
    for off in OFFSETS:
        st = now + timedelta(hours=off)
        en = st + timedelta(hours=WIN_H)
        status, mean_max = probe(key, aoi, st, en)
        rows.append({"offset_h": off, "date": st.strftime("%Y-%m-%d"),
                     "start": st.strftime("%H:00"), "end": en.strftime("%H:00"),
                     "status": status, "mean_max_c": mean_max})
        print("      %+4dh  %s %s-%s  ->  %-18s %s"
              % (off, st.strftime("%m-%d"), st.strftime("%H:00"), en.strftime("%H:00"),
                 status, ("mean max %.3f C" % mean_max) if mean_max is not None else ""))

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))

    ok_rows = [r for r in rows if r["status"].startswith("ok")]
    empty = [r for r in rows if r["status"] == "EMPTY"]
    errs = [r for r in rows if r["status"].startswith("error")]
    skipped = [r for r in rows if r["status"].startswith("skipped")]

    print("\n   RESULT")
    print("      windows returning data : %d  at offsets %s"
          % (len(ok_rows), [r["offset_h"] for r in ok_rows]))
    print("      windows EMPTY          : %d  at offsets %s"
          % (len(empty), [r["offset_h"] for r in empty]))
    print("      hard errors            : %d  %s"
          % (len(errs), [(r["offset_h"], r["status"]) for r in errs]))
    print("      skipped (midnight)     : %d  at offsets %s"
          % (len(skipped), [r["offset_h"] for r in skipped]))

    fwd = [r["offset_h"] for r in ok_rows if r["offset_h"] >= 0]
    back = [r["offset_h"] for r in ok_rows if r["offset_h"] < 0]
    max_fwd = max(fwd) if fwd else None
    min_back = min(back) if back else None
    print("\n      furthest FUTURE offset with data : %s"
          % ("+%dh" % max_fwd if max_fwd is not None else "none"))
    print("      furthest PAST offset with data   : %s"
          % ("%dh" % min_back if min_back is not None else "none"))

    print("\n   WHAT THIS MEANS FOR THE DESIGN")
    if max_fwd is None:
        print("      No future window returned data at all. Either the forecast is unavailable")
        print("      right now, or start_time is being interpreted in another timezone. The 12 h")
        print("      horizon claim cannot be supported and N-9's horizon must be re-derived.")
    elif max_fwd >= 10:
        print("      A ~12 h forward horizon is intact; N-13's failures were a boundary or")
        print("      timezone artifact in the request builder, not a data limit.")
    else:
        print("      Usable forward horizon is only about +%d h at this time of day, NOT 12 h."
              % max_fwd)
        print("      N-9's stopping problem was solved over 12 epochs; it must be re-solved over")
        print("      the real horizon, and the staging lead time (3 h [S]) becomes a much larger")
        print("      fraction of it, which will shrink the room the agent has to reason in.")
    if empty and ok_rows:
        gap = [r["offset_h"] for r in empty
               if min_back is not None and max_fwd is not None
               and min_back < r["offset_h"] < max_fwd]
        if gap:
            print("      A HOLE exists inside the available span at offsets %s -- consistent with"
                  % gap)
            print("      ingest lag around 'now'. Any agent must assert non-empty per window and")
            print("      degrade gracefully rather than trusting a contiguous series.")

    ok = max_fwd is not None and max_fwd >= 10
    print()
    verdict(ok,
            "PASS - forward data reaches +%dh, so the 12 h horizon the design assumes is real "
            "and N-13's empties were a request-builder artifact." % (max_fwd or 0),
            "FAIL - forward data reaches only +%s. The 12 h horizon is NOT available as "
            "requested; fix the request convention or re-derive the agent's horizon before "
            "quoting N-9." % ("%dh" % max_fwd if max_fwd is not None else "nothing"))

    save_result("n14_horizon.json", {
        "machine_now": now.isoformat(), "centre": CENTRE, "side_km": SIDE_KM,
        "granularity": GRAN, "win_h": WIN_H, "offsets": OFFSETS, "rows": rows,
        "n_ok": len(ok_rows), "n_empty": len(empty), "n_error": len(errs),
        "max_future_offset_h": max_fwd, "min_past_offset_h": min_back,
        "before": before, "after": after, "meter_moved": before != after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
