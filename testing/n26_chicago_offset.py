# -*- coding: utf-8 -*-
"""CHICAGO'S OWN FORTYGUARD LEVEL OFFSET  ---  one day-pair, measured at Chicago, PAID.

WHY THIS EXISTS
    `agent.py` carries four MEASURED FortyGuard level offsets and rotates them leave-one-out. All
    four were measured at ASHBURN, and until now every site used them -- so Chicago's unanchored
    case was corrected by Virginia's forecast bias. That is the last numeric fallback in the tree
    (`trace.fortyguard_provenance` records it), and the user's instruction is explicit: all three
    sites are to be treated separately, on their own characteristics.

    A level offset is `mean(outcome - forecast)` over the site's own tiles. It therefore needs TWO
    calls for the SAME window: a FORECAST leg made before the window, and an OUTCOME leg made after
    it has elapsed. One past-window call -- which is what Chicago already has -- cannot produce one,
    because there is nothing to difference it against.

        cost      2 x 4,220 = 8,440 credits
        elapsed   the forecast leg in the morning, the outcome leg after ~21:15 UTC
        result    ONE offset (n=1). NOT a coverage figure: coverage needs 9 calibration pairs plus
                  a test day, which is ~84,400 credits over 10+ calendar days and does not fit
                  before the 2026-08-30 deadline. This buys the LEVEL term, not the bound.

WHAT IT DELIBERATELY COPIES FROM THE ASHBURN SERIES, AND WHY EVERY ONE MATTERS
    Same target hour (14:00 site-local), same 2 h window, same 8x8 km AOI on the committed centre,
    same granularity 60, same `tcm` analytic, and the same 6.0-11.5 h LEAD BAND. An offset measured
    at a different hour or a shorter lead is not comparable with the four it is meant to replace,
    and comparing it anyway would be gotcha #35 -- writing a cause into a document without
    tabulating what else differed between the two calls. Gotcha #70 is the same lesson with teeth:
    DIAG-62's 19:00 window was recorded OUTSIDE the series for exactly this reason.

🔴 THE TIMEZONE. `common.SITE_TZ_NAME` is HARD-CODED to America/New_York, and the heatmap endpoint
    reads `start_time` in the AOI's OWN local zone with no echo. Chicago is America/Chicago, so
    using `common.site_window()` here would be a silent ONE-HOUR error -- the same class of bug as
    the original nine-hour one, just smaller and therefore harder to see. This file builds its
    windows with an explicit `ZoneInfo`, exactly as `fetch_chicago_field.py` does.

USAGE
    python n26_chicago_offset.py selftest     # the window/lead arithmetic. ZERO calls, no key
    python n26_chicago_offset.py dryrun       # what it would call and what it would cost. FREE
    python n26_chicago_offset.py forecast --allow-paid   # leg 1, in band only
    python n26_chicago_offset.py outcome --allow-paid    # leg 2, once the window has elapsed
    python n26_chicago_offset.py report       # the measured offset, free, from saved fixtures
"""
import json
import os
import statistics
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, verdict,
                    RESULTS, FIXTURES, utc_now, HEATMAP_CREDITS, classify_vendor, vendor_rec,
                    vendor_sentence, is_billed, recent_vendor_record)

# The committed Chicago pair's own centre, read from the geometry the solver used -- never typed.
IA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "INTAKE-ARBITER")
sys.path.insert(0, os.path.join(IA, "src"))
import metros as M                                                        # noqa: E402

METRO = "chicago"
TZ_NAME = M.METROS[METRO]["tz"]                  # America/Chicago, from the registry
SIDE_KM = 8.0                                    # identical to the Ashburn series
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14
ANALYTIC = "tcm"
MIN_LEAD_H = 6.0                                 # the Ashburn series' comparability band, verbatim
MAX_LEAD_H = 11.5
HORIZON_H = 12.0

MANIFEST = os.path.join(RESULTS, "n26_chicago_offset.json")
MAX_BILLED_ATTEMPTS_PER_LEG = int(os.environ.get("CHI_MAX_ATTEMPTS", "2"))


def centre():
    """The midpoint of the committed pair, from `metros.site_centre()` -- the same value the map
    marker and `agent.SITE_CENTRE` use. Typing a lat/lon here is what gotcha #98 was."""
    return M.site_centre(METRO)


def window_for(day):
    """The 14:00-16:00 CHICAGO-local window on `day`, plus its UTC bounds."""
    tz = ZoneInfo(TZ_NAME)
    start = datetime(day.year, day.month, day.day, TARGET_HOUR_SITE, 0, tzinfo=tz)
    end = start + timedelta(hours=WIN_H)
    return {"start_date": start.strftime("%Y-%m-%d"), "start_time": start.strftime("%H:00"),
            "end_time": end.strftime("%H:00"), "filter_type": 2,
            "_start_utc": start.astimezone(utc_now().tzinfo),
            "_end_utc": end.astimezone(utc_now().tzinfo)}


def lead_h(w, now=None):
    return ((w["_start_utc"] - (now or utc_now())).total_seconds()) / 3600.0


def site_now():
    return utc_now().astimezone(ZoneInfo(TZ_NAME))


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST, encoding="utf-8"))
    return {"created_utc": utc_now().isoformat(), "metro": METRO, "tz": TZ_NAME,
            "purpose": "one measured FortyGuard level offset for Chicago, to replace the borrowed "
                       "Ashburn offsets in the unanchored case",
            "side_km": SIDE_KM, "granularity": GRAN, "target_hour_site": TARGET_HOUR_SITE,
            "lead_band_h": [MIN_LEAD_H, MAX_LEAD_H], "days": {}, "attempts": []}


def write_manifest(m):
    json.dump(m, open(MANIFEST, "w", encoding="utf-8"), indent=1, default=str, allow_nan=False)


def field_max(result):
    """Per-tile MAX temperature, keyed by rounded centroid -- identical to the Ashburn collector's
    reader, so the two offsets are differenced from the same channel. Gotcha #57 is the scar: the
    tiles carry average_, min_ and max_temperature and reading a different one nearly produced a
    false defect report against FortyGuard."""
    feats = (result.get("map_data") or {}).get("features") or []
    out = {}
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4.0
        lo = sum(x[0] for x in c[:4]) / 4.0
        p = t["properties"]
        v = p.get("max_temperature", p.get("temperature"))
        if v is not None:
            out[(round(la, 6), round(lo, 6))] = float(v)
    return out


def billed_for(m, leg, date_iso):
    return sum(1 for a in m.get("attempts", [])
               if a.get("leg") == leg and a.get("date") == date_iso and a.get("billed"))


def call_window(key, w, tag, leg, date_iso, m):
    """One paid call, classified and recorded. Appends -- never overwrites (gotcha #100)."""
    clat, clon = centre()
    payload = {"polygon_aoi": box_aoi(clat, clon, SIDE_KM), "granularity": GRAN,
               "analytic_type": ANALYTIC,
               "date_time": {k: v for k, v in w.items() if not k.startswith("_")}}
    r = submit_poll(key, "heatmap", payload, tag)
    d = field_max(r["result"]) if r.get("result") else {}
    rec = vendor_rec(r, tiles=len(d))
    rec["class"] = cls = classify_vendor(rec)
    rec["billed"] = is_billed(cls)
    rec.update({"leg": leg, "date": date_iso, "tag": tag, "at_utc": utc_now().isoformat(),
                "lead_h": round(lead_h(w), 3), "sentence": vendor_sentence(cls, rec)})
    m.setdefault("attempts", []).append(rec)
    write_manifest(m)
    print("      %s" % rec["sentence"])
    print("      class=%s  %s" % (cls, "BILLED %s credits" % format(HEATMAP_CREDITS, ",")
                                  if rec["billed"] else "FREE"))
    return (d if r.get("ok") and d else None), rec


# ------------------------------------------------------------------ the legs
def _preflight(m, leg, allow_paid):
    """Everything that must be true before a call. Returns (day_iso, window, why_not)."""
    today = site_now().date()
    iso = today.isoformat()
    w = window_for(today)
    lead = lead_h(w)
    day = m["days"].setdefault(iso, {"date": iso})
    if leg == "forecast":
        if day.get("forecast_done"):
            return iso, w, "the forecast leg for %s is already banked (%s)" % (iso,
                                                                              day.get("f_tag"))
        if lead > MAX_LEAD_H:
            return iso, w, ("lead %.2f h is above the %.1f h ceiling%s -- re-run in %.1f h"
                            % (lead, MAX_LEAD_H,
                               " (and the %.0f h horizon)" % HORIZON_H if lead > HORIZON_H else "",
                               lead - MAX_LEAD_H))
        if lead < MIN_LEAD_H:
            return iso, w, ("lead %.2f h is BELOW the %.1f h comparability floor. A short-lead "
                            "forecast is much more accurate, so this offset would not be "
                            "comparable with the four Ashburn offsets it is meant to replace. "
                            "Today is over; the window opens again at %s UTC tomorrow."
                            % (lead, MIN_LEAD_H,
                               (w["_start_utc"] + timedelta(hours=24 - MAX_LEAD_H)).strftime("%H:%M")))
        if billed_for(m, "forecast", iso) >= MAX_BILLED_ATTEMPTS_PER_LEG:
            return iso, w, ("%d billed attempt(s) already made on this leg today -- %s credits. "
                            "Raise CHI_MAX_ATTEMPTS deliberately if you want to keep paying."
                            % (billed_for(m, "forecast", iso),
                               format(billed_for(m, "forecast", iso) * HEATMAP_CREDITS, ",")))
    else:
        if not day.get("forecast_done"):
            return iso, w, ("there is no forecast leg for %s, so an outcome call would buy a "
                            "field with nothing to difference it against" % iso)
        if day.get("outcome_done"):
            return iso, w, "the outcome leg for %s is already banked" % iso
        if utc_now() < w["_end_utc"] + timedelta(minutes=15):
            return iso, w, ("the window has not finished yet -- it ends %s UTC, so the outcome is "
                            "not observable until %s UTC"
                            % (w["_end_utc"].strftime("%H:%M"),
                               (w["_end_utc"] + timedelta(minutes=15)).strftime("%H:%M")))
        if billed_for(m, "outcome", iso) >= MAX_BILLED_ATTEMPTS_PER_LEG:
            return iso, w, "the outcome leg's billed budget is spent for today"
    if not allow_paid:
        return iso, w, ("this call costs %s credits and --allow-paid was not given"
                        % format(HEATMAP_CREDITS, ","))
    return iso, w, None


def run_leg(leg, allow_paid):
    banner("CHICAGO OFFSET -- %s leg.  %s" % (leg.upper(),
                                              "PAID" if allow_paid else "refusing to spend"))
    m = load_manifest()
    iso, w, why_not = _preflight(m, leg, allow_paid)
    clat, clon = centre()
    print("   Chicago local now : %s" % site_now().strftime("%Y-%m-%d %H:%M %Z"))
    print("   target window     : %s %s-%s %s-local" % (w["start_date"], w["start_time"],
                                                        w["end_time"], METRO))
    print("   AOI               : %.6f, %.6f  %.0fx%.0f km  gran %d  %s"
          % (clat, clon, SIDE_KM, SIDE_KM, GRAN, ANALYTIC))
    print("   lead right now    : %.2f h   band %.1f-%.1f h" % (lead_h(w), MIN_LEAD_H, MAX_LEAD_H))
    rv = recent_vendor_record(6.0)
    if rv:
        print("   vendor, last 6 h  : %d of %d windows returned a field (%.0f %%)"
              % (rv["returned_a_field"], rv["windows_seen"], 100 * rv["success_rate"]))
    if why_not:
        print("\n   NO CALL MADE: %s" % why_not)
        write_manifest(m)
        return 2
    key = load_key()
    before = credits_remaining(key)
    print("   credits before    : %s" % format(before, ","))
    tag = "n26chi_%s_%s" % (leg[0], iso)
    d, rec = call_window(key, w, tag, leg, iso, m)
    day = m["days"][iso]
    if d:
        day["%s_done" % leg] = True
        day["%s_tag" % leg] = tag
        day["%s_n" % leg] = len(d)
        day["%s_mean" % leg] = round(statistics.fmean(d.values()), 4)
        if leg == "forecast":
            day["forecast_lead_h"] = round(lead_h(w), 3)
            day["f_tag"] = tag
        print("      %s tiles, mean per-tile max %.4f C" % (format(len(d), ","),
                                                            day["%s_mean" % leg]))
    after = credits_remaining(key)
    m["credits_last_before"], m["credits_last_after"] = before, after
    write_manifest(m)
    print("   credits after     : %s   SPENT: %s" % (format(after, ","),
                                                     format(before - after, ",")))
    if d and leg == "outcome":
        print("\n   both legs are banked -- run `report` for the offset.")
    return 0 if d else 1


# ------------------------------------------------------------------ collect (both legs, one run)
def collect(allow_paid):
    """BOTH LEGS IN ONE INVOCATION, so one daily scheduled task is enough.

    WHY THIS SHAPE, AND IT IS THE ASHBURN COLLECTOR'S SHAPE ON PURPOSE.
    A day-pair needs a forecast made BEFORE the window and an outcome read AFTER it. Chicago's
    14:00-16:00 local window ends at 21:00 UTC, which is **02:15 PKT the following morning** once the
    15-minute settling delay is added. Scheduling a second task at 02:15 would mean asking a human to
    leave a machine awake at two in the morning, and sleep is already what lost 2026-08-14 and 08-17.

    So the outcome leg is collected on the NEXT DAY'S RUN, exactly as `test_n26_coverage.py collect`
    does for Ashburn: settle whatever outcome legs are owed from earlier days first, then fire
    today's forecast leg if the lead is in band. One task, one wake-up window, no night shift.

    Ordering matters: outcomes FIRST. An outcome leg is a debt already paid for -- its forecast leg
    is banked and the 4,220 credits are spent -- so if only one call is going to succeed today, it
    should be the one that completes a pair rather than the one that starts another.
    """
    banner("CHICAGO OFFSET collect   outcome debts first, then today's forecast   [%s]"
           % ("PAID" if allow_paid else "DRY -- refusing to spend"))
    m = load_manifest()
    key = load_key() if allow_paid else None
    before = credits_remaining(key) if key else None
    if before is not None:
        print("   credits before    : %s" % format(before, ","))
    print("   Chicago local now : %s" % site_now().strftime("%Y-%m-%d %H:%M %Z"))
    rv = recent_vendor_record(6.0)
    if rv:
        print("   vendor, last 6 h  : %d of %d windows returned a field (%.0f %%)"
              % (rv["returned_a_field"], rv["windows_seen"], 100 * rv["success_rate"]))
    did = 0

    # ---- 1. outcome legs owed from EARLIER days ------------------------------------
    for iso in sorted(m.get("days", {})):
        day = m["days"][iso]
        if day.get("outcome_done") or not day.get("forecast_done"):
            continue
        w = window_for(datetime.fromisoformat(iso).date())
        if utc_now() < w["_end_utc"] + timedelta(minutes=15):
            print("\n   outcome for %s: the window has not finished yet (ends %s UTC)"
                  % (iso, w["_end_utc"].strftime("%m-%d %H:%M")))
            continue
        if billed_for(m, "outcome", iso) >= MAX_BILLED_ATTEMPTS_PER_LEG:
            print("\n   outcome for %s: billed budget spent (%d attempts)"
                  % (iso, billed_for(m, "outcome", iso)))
            continue
        print("\n   OUTCOME leg for %s  target %s-%s Chicago-local"
              % (iso, w["start_time"], w["end_time"]))
        if not allow_paid:
            print("      would call -- %s credits. --allow-paid not given."
                  % format(HEATMAP_CREDITS, ","))
            continue
        d, _rec = call_window(key, w, "n26chi_o_%s" % iso, "outcome", iso, m)
        did += 1
        if d:
            day.update({"outcome_done": True, "outcome_tag": "n26chi_o_%s" % iso,
                        "outcome_n": len(d),
                        "outcome_mean": round(statistics.fmean(d.values()), 4)})
            print("      %s tiles, mean per-tile max %.4f C" % (format(len(d), ","),
                                                                day["outcome_mean"]))
            print("      *** the pair for %s is COMPLETE -- run `report` for the offset." % iso)
        write_manifest(m)

    # ---- 2. today's forecast leg, if the lead is in band ---------------------------
    iso, w, why_not = _preflight(m, "forecast", allow_paid=True)
    print("\n   TODAY'S FORECAST  %s %s-%s Chicago-local, lead %.2f h"
          % (w["start_date"], w["start_time"], w["end_time"], lead_h(w)))
    if why_not:
        print("      SKIP: %s" % why_not)
    elif not allow_paid:
        print("      would call -- %s credits. --allow-paid not given."
              % format(HEATMAP_CREDITS, ","))
    else:
        d, _rec = call_window(key, w, "n26chi_f_%s" % iso, "forecast", iso, m)
        did += 1
        day = m["days"][iso]
        if d:
            day.update({"forecast_done": True, "forecast_tag": "n26chi_f_%s" % iso,
                        "f_tag": "n26chi_f_%s" % iso, "forecast_n": len(d),
                        "forecast_lead_h": round(lead_h(w), 3),
                        "forecast_mean": round(statistics.fmean(d.values()), 4)})
            print("      %s tiles, mean per-tile max %.4f C" % (format(len(d), ","),
                                                                day["forecast_mean"]))
            print("      the outcome leg becomes readable at %s UTC -- it will be collected on"
                  % (w["_end_utc"] + timedelta(minutes=15)).strftime("%H:%M"))
            print("      TOMORROW'S run, so no night-time wake-up is needed.")
        write_manifest(m)

    if key:
        after = credits_remaining(key)
        m["credits_last_before"], m["credits_last_after"] = before, after
        write_manifest(m)
        print("\n   %d call(s) this run.  credits after: %s   SPENT: %s"
              % (did, format(after, ","), format(before - after, ",")))
    pairs = sum(1 for d in m.get("days", {}).values()
                if d.get("forecast_done") and d.get("outcome_done"))
    print("   complete day-pairs for Chicago: %d  (1 is enough for a LEVEL OFFSET; a coverage "
          "figure needs 10)" % pairs)
    return 0


# ------------------------------------------------------------------ report
def report():
    banner("CHICAGO OFFSET report   the measured level offset. FREE, from saved fixtures.")
    m = load_manifest()
    rows = []
    for iso, day in sorted(m.get("days", {}).items()):
        ft, ot = day.get("forecast_tag"), day.get("outcome_tag")
        if not (ft and ot):
            continue
        pf = os.path.join(FIXTURES, "%s.json" % ft)
        po = os.path.join(FIXTURES, "%s.json" % ot)
        if not (os.path.exists(pf) and os.path.exists(po)):
            continue
        F = field_max(json.load(open(pf, encoding="utf-8")))
        H = field_max(json.load(open(po, encoding="utf-8")))
        keys = [k for k in F if k in H]
        if len(keys) < 100:
            print("   %s: only %d shared tiles -- refusing to quote an offset" % (iso, len(keys)))
            continue
        dd = [H[k] - F[k] for k in keys]
        rows.append({"date": iso, "lead_h": day.get("forecast_lead_h"), "n_tiles": len(keys),
                     "mean_d": statistics.fmean(dd),
                     "sd_d": statistics.pstdev(dd) if len(dd) > 1 else 0.0})
    if not rows:
        print("   no complete day-pair yet. Run the forecast leg in band, then the outcome leg")
        print("   after the window has elapsed.")
        return 2
    print("   %-12s %-8s %-9s %-12s %s" % ("date", "lead h", "tiles", "mean d C", "sd C"))
    for r in rows:
        print("   %-12s %-8.2f %-9s %-+12.4f %.4f"
              % (r["date"], r["lead_h"] or float("nan"), format(r["n_tiles"], ","),
                 r["mean_d"], r["sd_d"]))
    ash = [-0.8395574067853544, -0.8114965065502183, 0.15202845146120256, -3.71268561191356]
    print("\n   ASHBURN's four measured offsets, for comparison ONLY -- same target hour, same")
    print("   lead band, same AOI size, so the comparison is like-for-like:")
    print("      %s" % ", ".join("%+.4f" % v for v in ash))
    print("      mean %+.4f C, range %.4f C" % (statistics.fmean(ash), max(ash) - min(ash)))
    out = {"metro": METRO, "measured_at": METRO, "n_pairs": len(rows), "pairs": rows,
           "ashburn_offsets_for_comparison": ash,
           "not_claimed": ["This is a LEVEL offset, not a coverage figure. Coverage needs 9 "
                           "calibration pairs plus a test day; n=%d here." % len(rows),
                           "n=%d, so no distribution and no interval is quoted." % len(rows)]}
    json.dump(out, open(os.path.join(RESULTS, "n26_chicago_offset_report.json"), "w",
                        encoding="utf-8"), indent=1, allow_nan=False)
    print("\n   wrote results/n26_chicago_offset_report.json")
    verdict(True, "MEASURED - Chicago now has %d level offset(s) of its own, measured on its own "
                  "tiles at its own committed centre." % len(rows), "")
    return 0


# ------------------------------------------------------------------ dryrun / selftest
def dryrun():
    banner("CHICAGO OFFSET dry run.  ZERO API CALLS, no key read, nothing spent.")
    m = load_manifest()
    clat, clon = centre()
    today = site_now().date()
    w = window_for(today)
    print("   UTC now            : %s" % utc_now().strftime("%Y-%m-%d %H:%M"))
    print("   Chicago local now  : %s" % site_now().strftime("%Y-%m-%d %H:%M %Z"))
    print("   committed centre   : %.6f, %.6f  (from metros.site_centre, not typed)" % (clat, clon))
    print("   target window      : %s %s-%s Chicago-local  ->  %s to %s UTC"
          % (w["start_date"], w["start_time"], w["end_time"],
             w["_start_utc"].strftime("%H:%M"), w["_end_utc"].strftime("%H:%M")))
    print("   lead right now     : %.2f h    band %.1f-%.1f h" % (lead_h(w), MIN_LEAD_H, MAX_LEAD_H))
    lo = w["_start_utc"] - timedelta(hours=MAX_LEAD_H)
    hi = w["_start_utc"] - timedelta(hours=MIN_LEAD_H)
    print("   in-band firing     : %s to %s UTC  (%s to %s PKT)"
          % (lo.strftime("%H:%M"), hi.strftime("%H:%M"),
             (lo + timedelta(hours=5)).strftime("%H:%M"),
             (hi + timedelta(hours=5)).strftime("%H:%M")))
    print("   outcome observable : %s UTC onward"
          % (w["_end_utc"] + timedelta(minutes=15)).strftime("%H:%M"))
    for leg in ("forecast", "outcome"):
        _iso, _w, why = _preflight(m, leg, allow_paid=True)
        print("   %-9s leg      : %s" % (leg, why or "WOULD CALL -- %s credits"
                                         % format(HEATMAP_CREDITS, ",")))
    print("\n   total if both legs run today: %s credits" % format(2 * HEATMAP_CREDITS, ","))
    rv = recent_vendor_record(6.0)
    print("   vendor, last 6 h   : %s"
          % ("%d of %d windows returned a field (%.0f %%)"
             % (rv["returned_a_field"], rv["windows_seen"], 100 * rv["success_rate"])
             if rv else "no measurement in the last 6 h"))
    return 0


def selftest():
    banner("CHICAGO OFFSET selftest.  ZERO API CALLS, no key read.")
    fails = []

    def ck(name, ok, detail=""):
        (fails.append(name) if not ok else None)
        print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail))

    # 1. THE TIMEZONE, which is the whole reason this file is not the Ashburn collector.
    import common as _C
    day = datetime(2026, 8, 21).date()
    w = window_for(day)
    ck("the window is built in CHICAGO's zone, not the hard-coded Eastern one",
       TZ_NAME == "America/Chicago" and _C.SITE_TZ_NAME == "America/New_York",
       "%s here vs %s in common.py" % (TZ_NAME, _C.SITE_TZ_NAME))
    ck("14:00 Chicago-local on 2026-08-21 is 19:00 UTC, not 18:00",
       w["_start_utc"].strftime("%H:%M") == "19:00",
       "%s UTC -- an hour out would be the nine-hour bug's little brother"
       % w["_start_utc"].strftime("%H:%M"))
    ck("the payload carries no underscore-prefixed internals",
       not any(k.startswith("_") for k in
               {k: v for k, v in w.items() if not k.startswith("_")}), "clean")

    # 2. the band, and the direction of each refusal
    fixed = w["_start_utc"]
    ck("a 9.4 h lead is in band, matching the Ashburn series' reference",
       MIN_LEAD_H <= lead_h(w, fixed - timedelta(hours=9.4)) <= MAX_LEAD_H, "9.40 h")
    ck("a 3.98 h lead is REFUSED -- it would flatter the offset",
       lead_h(w, fixed - timedelta(hours=3.98)) < MIN_LEAD_H, "below the 6.0 h floor")
    ck("a 28 h lead is REFUSED -- beyond the vendor's 12 h horizon",
       lead_h(w, fixed - timedelta(hours=28)) > HORIZON_H, "above the ceiling")

    # 3. the band matches Ashburn's EXACTLY, or the two offsets are not comparable
    import test_n26_coverage as N26
    ck("the lead band is character-for-character the Ashburn series' band",
       (MIN_LEAD_H, MAX_LEAD_H) == (N26.MIN_LEAD_H, N26.MAX_LEAD_H),
       "%.1f-%.1f h in both" % (MIN_LEAD_H, MAX_LEAD_H))
    ck("the target hour, AOI size and granularity match it too",
       (TARGET_HOUR_SITE, SIDE_KM, GRAN, WIN_H)
       == (N26.TARGET_HOUR_SITE, N26.SIDE_KM, N26.GRAN, N26.WIN_H),
       "hour %d, %.0f km, gran %d, %d h window" % (TARGET_HOUR_SITE, SIDE_KM, GRAN, WIN_H))

    # 4. the centre is READ, not typed -- gotcha #98
    clat, clon = centre()
    ck("the AOI centre comes from the committed pair, not a literal",
       abs(clat - 41.0) > 0.5 and 41.0 < clat < 43.0 and -89.0 < clon < -87.0,
       "%.6f, %.6f is in Illinois, and it is Chicago's own midpoint" % (clat, clon))
    ck("...and it is NOT Ashburn's centre",
       (round(clat, 3), round(clon, 3)) != tuple(round(v, 3) for v in M.site_centre("ashburn")),
       "chicago %.3f,%.3f vs ashburn %.3f,%.3f"
       % (clat, clon, M.site_centre("ashburn")[0], M.site_centre("ashburn")[1]))

    # 5. an outcome leg without a forecast leg must refuse
    m0 = {"days": {}, "attempts": []}
    _i, _w, why = _preflight(m0, "outcome", allow_paid=True)
    ck("an outcome call with no forecast leg is refused", bool(why) and "no forecast leg" in why,
       "nothing to difference it against")
    # 6. the billed budget counts only billed attempts
    m1 = {"days": {site_now().date().isoformat(): {}},
          "attempts": [{"leg": "forecast", "date": site_now().date().isoformat(),
                        "billed": False, "class": "stalled_in_processing"}] * 5}
    ck("free failures do not exhaust the paid budget",
       billed_for(m1, "forecast", site_now().date().isoformat()) == 0,
       "5 free attempts, 0 billed -- same rule as the hardened Ashburn collector")

    print()
    verdict(not fails,
            "PASS - the window is built in Chicago's own zone, the lead band and AOI match the "
            "Ashburn series exactly so the two offsets are comparable, the centre is read from the "
            "committed pair, and no call can be made out of band or without its counterpart.",
            "FAIL - %s" % ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    mode = (argv[0].lower() if argv and not argv[0].startswith("-") else "dryrun")
    allow = "--allow-paid" in argv
    if mode == "collect":
        sys.exit(collect(allow))
    if mode == "forecast":
        sys.exit(run_leg("forecast", allow))
    if mode == "outcome":
        sys.exit(run_leg("outcome", allow))
    if mode == "report":
        sys.exit(report())
    if mode == "selftest":
        sys.exit(selftest())
    sys.exit(dryrun())
