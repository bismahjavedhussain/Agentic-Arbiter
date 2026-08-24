# -*- coding: utf-8 -*-
"""DIAG-64 -- DOES THE CATALOG HAVE A FORWARD LIMIT?   PAID, 2 calls, 8,440 credits.

THE HYPOTHESIS, WRITTEN DOWN BEFORE THE CALLS (methodology rule 2)
    H1  The empty forecast responses this project has recorded since 2026-08-18 are windows falling
        PAST the forward end of FortyGuard's catalog -- not a vendor outage.

    Origin: a FortyGuard engineer, answering a different entrant about an America/Phoenix AOI, wrote
    that their window was "about six hours past the last hour currently in the catalog (2026-08-20
    15:00 UTC). The window fell outside the data, so the grid came back empty." Our own successful
    windows over Ashburn on 2026-08-20 stop at 16:00 UTC. Two independent sources, one boundary.

THE DESIGN, AND WHY IT VARIES EXACTLY ONE THING
    Section 4.0 of HANDOFF concluded that this could not be tested:

        "Target hour and call clock time are LOCKED TOGETHER by the 6.0-11.5 h lead band. A 14:00
         site-local window at a 9.4 h lead *forces* a call at ~08:35 UTC. There is no request that
         varies one and holds the other."

    That is true of a request that must be COMPARABLE WITH THE N-26 SERIES. It is not true of a
    diagnostic, because a diagnostic may leave the band. Drop the band and the test is trivial:

        ask for THE COLLECTOR'S OWN WINDOW -- 14:00-16:00 site-local, 18:00-20:00 UTC -- but ask
        for it NOW, at a ~1.8 h lead instead of the ~9.5 h lead the schedule forces.

    Same AOI, same centre, same 8x8 km box, same granularity 60, same `tcm`, same 2-hour window,
    same `filter_type`. The ONLY difference from the four calls that failed on 08-18..08-21 is the
    clock time of the request. That is the definition of a controlled test, and it took one
    sentence from the vendor to see that the constraint we had accepted was self-imposed.

THE POSITIVE CONTROL, AND WHY THE TEST IS VOID WITHOUT IT
    Gotcha #59 in this project's log: a negative that repeats is evidence about a PERIOD, never a
    CAPABILITY -- and the lesson recorded there was to demand a positive control before retiring a
    forward plan. If FortyGuard is simply not answering today, the probe comes back empty and means
    nothing at all. So the first call asks for a window in the PAST, which all prior evidence says
    works. If THAT comes back empty, this test draws no conclusion.

PRE-REGISTERED OUTCOMES -- fixed before either call was made
    P0  CONTROL, 09:00-11:00 site-local (3.2 h in the PAST): expected to return a populated field.
        If it does not, the run is VOID and H1 is neither supported nor refuted.

    P1  PROBE, 14:00-16:00 site-local (1.8 h in the FUTURE) -- the collector's exact window:
          field returned  -> H1 SUPPORTED. The window IS in the catalog now and was NOT at 08:30
                             UTC, so the collector's four days of empty responses are a forward-limit
                             effect and the "outage" attribution is wrong. The N-26 series has been
                             asking for data that did not exist yet, every day, by construction.
          empty returned  -> H1 NOT SUPPORTED for a 1.8 h lead. The catalog does not hold a window
                             two hours ahead, so the forward extent is <= ~2 h or the catalog lags
                             real time. Either way the documented 12 h horizon is not usable, and
                             the product's notice claim needs restating rather than defending.

    Both outcomes are publishable and neither is the one we would prefer. That is the point.

COST
    2 heatmap calls = 8,440 credits. Authorised by the user 2026-08-21, explicitly, for this test.

USAGE
    python diag64_catalog_horizon.py dryrun      # the two windows and the cost. ZERO calls.
    python diag64_catalog_horizon.py run --allow-paid
"""
import json
import os
import statistics
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, site_now, site_window, lead_hours, utc_now, RESULTS,
                    HEATMAP_CREDITS, classify_vendor, vendor_rec, vendor_sentence, is_billed,
                    SITE_TZ_NAME)

IA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "INTAKE-ARBITER")
sys.path.insert(0, os.path.join(IA, "src"))
import metros as M                                                        # noqa: E402

METRO = "ashburn"          # the site with the most history to compare against
SIDE_KM = 8.0              # every constant below is the COLLECTOR'S, so the probe is comparable
GRAN = 60
ANALYTIC = "tcm"
WIN_H = 2
CONTROL_OFFSET_H = -3      # a window that has already elapsed
PROBE_TARGET_HOUR = 14     # the collector's fixed target hour, deliberately


def windows():
    """The two windows, built through the SAME helpers the paid collector uses."""
    now_site = site_now()
    ctl_start = (now_site + timedelta(hours=CONTROL_OFFSET_H)).replace(minute=0, second=0,
                                                                      microsecond=0)
    probe_start = now_site.replace(hour=PROBE_TARGET_HOUR, minute=0, second=0, microsecond=0)
    return [("CONTROL", ctl_start, "a window that has already elapsed -- all prior evidence says "
                                   "history works"),
            ("PROBE", probe_start, "the collector's OWN window, asked for now instead of at 08:30 "
                                   "UTC")]


def one_call(key, label, start_site, note, results):
    w = site_window(start_site, WIN_H)
    lead = lead_hours(w["_start_utc"])
    clat, clon = M.site_centre(METRO)
    print("\n   %s  %s %s-%s site-local (%s)" % (label, w["start_date"], w["start_time"],
                                                 w["end_time"], SITE_TZ_NAME))
    print("      = %s-%s UTC   lead %+.2f h" % (w["_start_utc"].strftime("%H:%M"),
                                                w["_end_utc"].strftime("%H:%M"), lead))
    print("      %s" % note)
    before = credits_remaining(key)
    payload = {"polygon_aoi": box_aoi(clat, clon, SIDE_KM), "granularity": GRAN,
               "analytic_type": ANALYTIC,
               "date_time": {k: v for k, v in w.items() if not k.startswith("_")}}
    tag = "diag64_%s" % label.lower()
    r = submit_poll(key, "heatmap", payload, tag)
    feats = ((r.get("result") or {}).get("map_data") or {}).get("features") or []
    rec = vendor_rec(r, tiles=len(feats))
    rec["class"] = cls = classify_vendor(rec)
    rec["billed"] = is_billed(cls)
    after = credits_remaining(key)
    vals = []
    for t in feats:
        p = t.get("properties") or {}
        v = p.get("max_temperature", p.get("temperature"))
        if v is not None:
            vals.append(float(v))
    print("      -> %s" % vendor_sentence(cls, rec))
    print("      tiles %s   meter %s -> %s   spent %s"
          % (format(len(feats), ","), format(before, ","), format(after, ","),
             format(before - after, ",")))
    if vals:
        print("      values %.3f .. %.3f C, mean %.3f" % (min(vals), max(vals),
                                                          statistics.fmean(vals)))
    results.append({
        "label": label, "window_site_local": "%s %s-%s" % (w["start_date"], w["start_time"],
                                                           w["end_time"]),
        "window_utc": "%s-%s" % (w["_start_utc"].strftime("%Y-%m-%d %H:%M"),
                                 w["_end_utc"].strftime("%H:%M")),
        "lead_h": round(lead, 3), "class": cls, "billed": rec["billed"],
        "tiles": len(feats), "activity_id": rec.get("activity_id"),
        "polls": rec.get("polls"), "elapsed_s": rec.get("elapsed_s"),
        "credits_before": before, "credits_after": after, "spent": before - after,
        "t_min": round(min(vals), 3) if vals else None,
        "t_max": round(max(vals), 3) if vals else None,
        "t_mean": round(statistics.fmean(vals), 3) if vals else None,
        "sentence": vendor_sentence(cls, rec)})
    return len(feats) > 0


def dryrun():
    banner("DIAG-64 dry run   the two windows and the cost.  ZERO API CALLS, no key read.")
    clat, clon = M.site_centre(METRO)
    print("   AOI            : %.6f, %.6f  %.0fx%.0f km  gran %d  %s  filter_type 2 (%d h window)"
          % (clat, clon, SIDE_KM, SIDE_KM, GRAN, ANALYTIC, WIN_H))
    print("   every constant above is the COLLECTOR'S, unchanged, so only the LEAD differs")
    for label, start, note in windows():
        w = site_window(start, WIN_H)
        print("\n   %-8s %s %s-%s site-local = %s-%s UTC   lead %+.2f h"
              % (label, w["start_date"], w["start_time"], w["end_time"],
                 w["_start_utc"].strftime("%H:%M"), w["_end_utc"].strftime("%H:%M"),
                 lead_hours(w["_start_utc"])))
        print("            %s" % note)
    print("\n   cost if run: 2 x %s = %s credits" % (format(HEATMAP_CREDITS, ","),
                                                     format(2 * HEATMAP_CREDITS, ",")))
    return 0


def run(allow_paid):
    banner("DIAG-64   does the catalog have a forward limit?   [%s]"
           % ("PAID -- 2 calls" if allow_paid else "REFUSING to spend"))
    if not allow_paid:
        print("   --allow-paid was not given. `dryrun` shows the plan for free.")
        return 5
    key = load_key()
    t0 = credits_remaining(key)
    print("   meter at start : %s" % format(t0, ","))
    print("   PRE-REGISTERED: control must return a field or the run is VOID; the probe is the")
    print("   collector's own window at a ~1.8 h lead instead of ~9.5 h.")
    results = []
    ctl_ok = None
    for label, start, note in windows():
        got = one_call(key, label, start, note, results)
        if label == "CONTROL":
            ctl_ok = got
            if not got:
                print("\n   *** CONTROL RETURNED NO FIELD. The vendor is not answering for a past")
                print("       window either, so the probe cannot distinguish a forward limit from a")
                print("       general fault. Continuing anyway -- the probe's result is still worth")
                print("       recording -- but the pre-registration says this run is VOID for H1.")
    probe_ok = results[-1]["tiles"] > 0
    t1 = credits_remaining(key)

    print("\n" + "=" * 78)
    print("   RESULT")
    for r in results:
        print("      %-8s lead %+6.2f h   %-22s %6s tiles   %s credits"
              % (r["label"], r["lead_h"], r["class"], format(r["tiles"], ","),
                 format(r["spent"], ",")))
    print("   total spent: %s credits (meter %s -> %s)"
          % (format(t0 - t1, ","), format(t0, ","), format(t1, ",")))

    if not ctl_ok:
        conclusion = ("VOID -- the positive control returned no field, so the vendor is not "
                      "answering for past windows either. H1 is neither supported nor refuted, and "
                      "a repeat is needed on a day when history works. Gotcha #59: a negative that "
                      "repeats is evidence about a PERIOD, never a CAPABILITY.")
        supported = None
    elif probe_ok:
        conclusion = ("H1 SUPPORTED. The collector's exact window returned a populated field at a "
                      "%.2f h lead, having returned EMPTY at a ~9.5 h lead on four consecutive "
                      "days. Nothing about the request changed except when it was made, so the "
                      "empty responses are a FORWARD-LIMIT effect and the 'vendor outage' "
                      "attribution in HANDOFF section 4.0 is wrong. The N-26 series has been asking "
                      "for data that did not exist yet, by construction, since 2026-08-18."
                      % results[-1]["lead_h"])
        supported = True
    else:
        conclusion = ("H1 NOT SUPPORTED AT THIS LEAD. History works (the control returned a field) "
                      "but a window %.2f h ahead does not. So the catalog does not extend even two "
                      "hours into the future right now: the forward extent is <= ~2 h, or the "
                      "catalog lags real time. Either way the documented 12 h horizon is not usable "
                      "today, and the product's notice claim must be restated rather than defended."
                      % results[-1]["lead_h"])
        supported = False

    print()
    print("   " + "\n   ".join(conclusion[i:i + 92] for i in range(0, len(conclusion), 92)))
    save_result("diag64_catalog_horizon.json", {
        "test": "DIAG-64 catalog forward limit",
        "hypothesis": "the empty forecast responses are windows past the catalog's forward end, "
                      "not a vendor outage",
        "authorised_by_user": "2026-08-21",
        "design": "the collector's OWN window (14:00-16:00 site-local) requested at a ~1.8 h lead "
                  "instead of the ~9.5 h lead the schedule forces. Same AOI, centre, granularity, "
                  "analytic, window length and filter_type -- only the request clock time differs.",
        "positive_control": "a window 3 h in the past, which all prior evidence says works",
        "metro": METRO, "aoi_centre": list(M.site_centre(METRO)), "side_km": SIDE_KM,
        "granularity": GRAN, "analytic_type": ANALYTIC, "window_hours": WIN_H,
        "api_calls_made": len(results),
        "credits_before": t0, "credits_after": t1, "credits_spent": t0 - t1,
        "control_returned_field": ctl_ok, "probe_returned_field": probe_ok,
        "h1_supported": supported, "conclusion": conclusion, "calls": results})
    print("=" * 78)
    verdict(supported is not None, conclusion[:200], "VOID -- see the conclusion above")
    return 0


if __name__ == "__main__":
    mode = (sys.argv[1].lower() if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
            else "dryrun")
    sys.exit(run("--allow-paid" in sys.argv) if mode == "run" else dryrun())
