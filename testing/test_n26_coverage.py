# -*- coding: utf-8 -*-
"""N-26  ---  DOES THE BOUND ACTUALLY COVER WHAT IT PROMISES?   PAID, one pair per day.

WHY THIS RANKS SECOND ONLY TO THE SHARPENING TEST
    The product is not a temperature prediction. It is a BOUND: "90 % of the time the intake stays
    below X." Everything downstream -- the released cooling margin, the staging decision, the whole
    commercial pitch -- is built on that number meaning what it says.

    Right now it is verified on ONE forecast/outcome pair. One pair cannot measure a 90 % rate. If
    the truth breaches the bound 30 % of the time out of sample, the core deliverable is broken no
    matter how good the physics is, and no amount of GPU or solver work fixes it.

    Like the sharpening test, this needs elapsed calendar days, so waiting until 18 Aug is the one
    choice that guarantees it cannot be fixed in time. Started 2026-08-12, it yields six independent
    day-pairs before the hackathon.

WHAT A "BOUND" MEANS HERE, PRECISELY
    Split conformal prediction, one-sided upper. Let d = outcome - forecast, per tile.

        calibrate   pool d over the CALIBRATION days; take the k-th smallest, where
                    k = ceil((n + 1) * (1 - alpha)), the finite-sample-valid index
        predict     bound = forecast + q
        score       coverage = fraction of tiles on a LATER day with outcome <= bound

    Signed rather than absolute residuals, because the decision only ever needs an upper limit --
    being cooler than predicted is never the failure. A one-sided bound is also tighter, and it
    absorbs any systematic warm or cool bias automatically instead of needing a separate correction.

THE FAILURE MODE THIS IS LOOKING FOR
    Conformal prediction guarantees coverage >= 1 - alpha only if the calibration days and the test
    day are exchangeable -- loosely, "drawn from the same weather". They are not. Days differ
    systematically: a humid day, a windy day, a frontal passage. So the honest question is not
    whether the mathematics is right (it is), but whether the day-to-day drift is small enough that
    a bound calibrated on last week still holds today. That is an empirical question about
    FortyGuard's forecast, and it is exactly what this measures.

PASS CONDITIONS, FIXED NOW, BEFORE ANY OUTCOME EXISTS
    P1  pooled out-of-sample coverage >= 0.85            (nominal is 0.90; 5 points of slack)
    P2  no single test day below 0.60                    (the agent acts daily, so one catastrophic
                                                          day is disqualifying, not averaged away)
    P3  at least 3 test days available                   (fewer cannot show a trend)

WHAT THIS DOES AND DOES NOT MEASURE -- state this before anyone asks
    DOES      whether a bound calibrated on earlier days covers, across 17,862 locations, on a day
              it has never seen. That is the right question for a multi-site deployment.
    DOES NOT  the breach rate at ONE fixed site over many days. That needs far more days than exist
              before 18 Aug. Tiles are also spatially correlated, so the effective sample is much
              smaller than the tile count and the finite-sample index is optimistic. Coverage is
              therefore also reported per spatial quadrant.

COST
    One forecast (~9.5 h lead) plus one outcome per day = 2 calls/day. Day 1 reuses the N-25
    fixtures for 2026-08-12 at zero extra cost, since N-25 already forecasts and scores the same
    14:00-16:00 window.

USAGE
    python test_n26_coverage.py collect    # safe to run any time; does only what is due today
    python test_n26_coverage.py report     # coverage, per test day and pooled
"""
import json, math, os, statistics, sys
from datetime import datetime, timedelta, timezone

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, RESULTS, FIXTURES, tile_key, site_now, site_window, lead_hours,
                    utc_now, site_tz, SITE_TZ_NAME)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14          # same window as N-25, so day 1 is free
HORIZON_H = 12.0
ALPHA = 0.10                   # nominal 90 % one-sided coverage

# Comparability guard. The target HOUR is fixed at 14:00 site-local so every day scores the same
# decision-relevant window (the diurnal peak) and diurnal predictability is held constant. That
# leaves the LEAD free to vary with whatever time of day this happens to be run, and lead matters:
# a 2 h forecast is far better than a 10 h one, so a day collected late would show artificially
# high coverage and quietly flatter the result. Only accept leads in a band around the 9.41 h that
# N-25 used, and record the actual lead so the report can warn if the spread grows.
MIN_LEAD_H = 6.0
MAX_LEAD_H = 11.5
LEAD_SPREAD_WARN_H = 3.0
MANIFEST = os.path.join(RESULTS, "n26_manifest.json")

MIN_COVERAGE = 0.85            # P1
MIN_DAY_COVERAGE = 0.60        # P2
MIN_TEST_DAYS = 3              # P3


def field_max(result):
    feats = (result.get("map_data") or {}).get("features") or []
    out = {}
    for t in feats:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4
        lo = sum(x[0] for x in c[:4]) / 4
        v = t["properties"].get("max_temperature")
        if v is not None:
            out[tile_key(la, lo)] = (v, la, lo)
    return out


def window_for(date_site):
    """The site-local target window on a given date. date_site is a date object."""
    start = datetime(date_site.year, date_site.month, date_site.day,
                     TARGET_HOUR_SITE, 0, tzinfo=site_tz())
    return site_window(start, WIN_H)


def call_window(key, aoi, dt_fields, tag):
    p = {"polygon_aoi": aoi, "granularity": GRAN, "analytic_type": "tcm",
         "date_time": {k: v for k, v in dt_fields.items() if not k.startswith("_")}}
    r = submit_poll(key, "heatmap", p, tag)
    if not r.get("ok"):
        return None, r.get("error")
    d = field_max(r["result"])
    if not d:
        return None, "ZERO TILES with completed status"
    return d, len(d)


def load_manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    # first run: seed with day 1 pointing at the N-25 fixtures, which cost nothing extra
    m = {"created_utc": utc_now().isoformat(), "site_tz": SITE_TZ_NAME,
         "centre": list(CENTRE), "side_km": SIDE_KM, "granularity": GRAN, "win_h": WIN_H,
         "target_hour_site": TARGET_HOUR_SITE, "alpha": ALPHA,
         "min_coverage": MIN_COVERAGE, "min_day_coverage": MIN_DAY_COVERAGE,
         "days": {}, "errors": {}}
    d1 = site_now().date().isoformat()
    m["days"][d1] = {"date": d1, "forecast_tag": "n25_f_lead09.41", "forecast_lead_h": 9.41,
                     "forecast_done": True, "outcome_tag": "n25_outcome",
                     "outcome_done": False, "reused_from": "N-25"}
    return m


def write_manifest(m):
    json.dump(m, open(MANIFEST, "w"), indent=1, default=str)


def fixture_exists(tag):
    return bool(tag) and os.path.exists(os.path.join(FIXTURES, "%s.json" % tag))


# ----------------------------------------------------------------- collect
def collect():
    banner("N-26 collect  one forecast + one outcome, for the daily coverage record   [PAID]")
    m = load_manifest()
    key = load_key()
    before = credits_remaining(key)
    aoi = box_aoi(m["centre"][0], m["centre"][1], m["side_km"])
    today = site_now().date()
    print("   site local now %s   (site zone %s)"
          % (site_now().strftime("%Y-%m-%d %H:%M %Z"), SITE_TZ_NAME))
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    did = 0

    # ---- 1. today's forecast, if the window is still far enough ahead ----
    key_today = today.isoformat()
    day = m["days"].setdefault(key_today, {"date": key_today, "forecast_done": False,
                                           "outcome_done": False})
    if day.get("forecast_done"):
        print("\n   today's forecast: already recorded (%s)%s"
              % (day.get("forecast_tag"), " [reused from N-25]" if day.get("reused_from") else ""))
    else:
        w = window_for(today)
        lead = lead_hours(w["_start_utc"])
        print("\n   TODAY'S FORECAST  target %s %s-%s site-local, lead %.2f h"
              % (w["start_date"], w["start_time"], w["end_time"], lead))
        if lead <= 0:
            print("      SKIP: the window has already started at the site. Nothing to forecast.")
            day["forecast_error"] = "run too late; window already started"
        elif lead > MAX_LEAD_H:
            print("      SKIP: lead %.2f h is above the %.1f h comparability ceiling%s."
                  % (lead, MAX_LEAD_H, " (and the %.0f h horizon)" % HORIZON_H
                     if lead > HORIZON_H else ""))
            print("      Re-run in %.1f h. Nothing is lost by waiting." % (lead - MAX_LEAD_H))
        elif lead < MIN_LEAD_H:
            print("      SKIP: lead %.2f h is below the %.1f h comparability floor. A short-lead"
                  % (lead, MIN_LEAD_H))
            print("      forecast is much more accurate, so recording it would inflate coverage and")
            print("      flatter the result. Today is skipped deliberately -- run earlier tomorrow.")
            day["forecast_error"] = "lead %.2f h below comparability floor %.1f h" % (lead,
                                                                                      MIN_LEAD_H)
        else:
            tag = "n26_f_%s" % key_today
            d, n = call_window(key, aoi, w, tag)
            if d is None:
                day["forecast_error"] = n
                m["errors"][tag] = n
                print("      FAILED: %s" % n)
            else:
                day.update({"forecast_tag": tag, "forecast_lead_h": round(lead, 3),
                            "forecast_done": True, "forecast_n": n,
                            "forecast_mean": round(statistics.fmean(v[0] for v in d.values()), 4),
                            "forecast_issued_utc": utc_now().isoformat()})
                print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","),
                                                                     day["forecast_mean"]))
            did += 1
            write_manifest(m)

    # ---- 2. outcomes for any earlier day whose window has elapsed ----------
    for dk in sorted(m["days"]):
        day = m["days"][dk]
        if day.get("outcome_done") or not day.get("forecast_done"):
            continue
        dt = datetime.fromisoformat(dk).date()
        w = window_for(dt)
        if utc_now() < w["_end_utc"] + timedelta(minutes=15):
            print("\n   outcome for %s: window has not finished yet (ends %s UTC)"
                  % (dk, w["_end_utc"].strftime("%m-%d %H:%M")))
            continue
        tag = day.get("outcome_tag") or ("n26_h_%s" % dk)
        if fixture_exists(tag):
            day["outcome_done"] = True
            print("\n   outcome for %s: fixture already present (%s)" % (dk, tag))
            write_manifest(m)
            continue
        print("\n   OUTCOME for %s  target %s-%s site-local" % (dk, w["start_time"], w["end_time"]))
        d, n = call_window(key, aoi, w, tag)
        if d is None:
            day["outcome_error"] = n
            m["errors"][tag] = n
            print("      FAILED: %s" % n)
        else:
            day.update({"outcome_tag": tag, "outcome_done": True, "outcome_n": n,
                        "outcome_mean": round(statistics.fmean(v[0] for v in d.values()), 4),
                        "outcome_fetched_utc": utc_now().isoformat()})
            print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","),
                                                                 day["outcome_mean"]))
        did += 1
        write_manifest(m)

    after = credits_remaining(key)
    m["credits_last_before"], m["credits_last_after"] = before, after
    write_manifest(m)
    pairs = sum(1 for d in m["days"].values()
                if d.get("forecast_done") and d.get("outcome_done"))
    print("\n   %d call(s) this run.  complete day-pairs: %d  (need %d test days, so %d pairs)"
          % (did, pairs, MIN_TEST_DAYS, MIN_TEST_DAYS + 1))
    print("   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))
    print("   run this again tomorrow at about the same time (site window must be < %.0f h ahead)"
          % HORIZON_H)
    return 0


# ----------------------------------------------------------------- report
def _q_index(n, alpha):
    """Finite-sample-valid split-conformal index: ceil((n+1)(1-alpha)), clipped."""
    return min(n - 1, math.ceil((n + 1) * (1.0 - alpha)) - 1)


def report():
    banner("N-26 report  out-of-sample coverage of the one-sided conformal bound")
    if not os.path.exists(MANIFEST):
        print("   no manifest -- run 'collect' first.")
        return 2
    m = json.load(open(MANIFEST))

    pairs = []
    for dk in sorted(m["days"]):
        day = m["days"][dk]
        ft, ot = day.get("forecast_tag"), day.get("outcome_tag")
        if not (fixture_exists(ft) and fixture_exists(ot)):
            continue
        F = field_max(json.load(open(os.path.join(FIXTURES, "%s.json" % ft))))
        H = field_max(json.load(open(os.path.join(FIXTURES, "%s.json" % ot))))
        keys = [k for k in F if k in H]
        if len(keys) < 100:
            continue
        d = {k: H[k][0] - F[k][0] for k in keys}          # outcome - forecast
        pairs.append({"date": dk, "lead_h": day.get("forecast_lead_h"), "n": len(keys),
                      "d": d, "F": F, "H": H,
                      "mean_d": statistics.fmean(d.values()),
                      "sd_d": statistics.pstdev(d.values())})

    print("   complete day-pairs found: %d" % len(pairs))
    if not pairs:
        print("   nothing to score yet. Each pair needs a forecast and its elapsed outcome.")
        return 2

    print("\n   %-12s %8s %10s %10s %10s" % ("date", "lead h", "n tiles", "mean d", "sd d"))
    for p in pairs:
        print("   %-12s %8s %10s %+10.4f %10.4f"
              % (p["date"], "%.2f" % p["lead_h"] if p["lead_h"] else "-",
                 format(p["n"], ","), p["mean_d"], p["sd_d"]))
    print("   (d = outcome - forecast, per tile. A positive mean means the forecast runs COOL.)")

    leads = [p["lead_h"] for p in pairs if p["lead_h"]]
    lead_spread = (max(leads) - min(leads)) if leads else 0.0
    if lead_spread > LEAD_SPREAD_WARN_H:
        print("\n   *** LEAD SPREAD WARNING: %.1f h across days (%.2f to %.2f) ***"
              % (lead_spread, min(leads), max(leads)))
        print("      Coverage is only comparable across days at a similar lead -- a short-lead")
        print("      forecast is more accurate and inflates coverage. Treat the pooled number as")
        print("      indicative and quote the per-day column instead.")
    elif leads:
        print("   lead spread across days: %.1f h (%.2f to %.2f) -- comparable"
              % (lead_spread, min(leads), max(leads)))

    if len(pairs) < 2:
        print("\n   only one pair: a bound can be calibrated OR tested, not both. Need >= 2.")
        save_result("n26_coverage.json", {"n_pairs": len(pairs), "pass": None,
                                          "days": [{k: p[k] for k in
                                                    ("date", "lead_h", "n", "mean_d", "sd_d")}
                                                   for p in pairs]})
        return 2

    # ---- sequential out-of-sample coverage: calibrate on days < k, test on day k ----
    print("\n   SEQUENTIAL OUT-OF-SAMPLE COVERAGE  (calibrate on all earlier days, test on the next)")
    print("   %-12s %9s %10s %10s %11s %s"
          % ("test day", "cal days", "cal n", "halfwidth", "coverage", "quadrants NE NW SE SW"))
    tests = []
    for i in range(1, len(pairs)):
        cal = [x for p in pairs[:i] for x in p["d"].values()]
        cal.sort()
        q = cal[_q_index(len(cal), ALPHA)]
        tp = pairs[i]
        breaches = [k for k, v in tp["d"].items() if v > q]
        cov = 1.0 - len(breaches) / tp["n"]
        lats = [tp["F"][k][1] for k in tp["d"]]
        lons = [tp["F"][k][2] for k in tp["d"]]
        mla, mlo = statistics.median(lats), statistics.median(lons)
        quad = {"NE": [0, 0], "NW": [0, 0], "SE": [0, 0], "SW": [0, 0]}
        for k, v in tp["d"].items():
            qq = ("N" if tp["F"][k][1] >= mla else "S") + ("E" if tp["F"][k][2] >= mlo else "W")
            quad[qq][1] += 1
            if v <= q:
                quad[qq][0] += 1
        qcov = {kk: (vv[0] / vv[1] if vv[1] else None) for kk, vv in quad.items()}
        tests.append({"test_date": tp["date"], "n_cal_days": i, "n_cal": len(cal),
                      "halfwidth": q, "coverage": cov, "n_breach": len(breaches),
                      "quad_coverage": qcov})
        print("   %-12s %9d %10s %10.4f %10.1f%%  %s"
              % (tp["date"], i, format(len(cal), ","), q, 100 * cov,
                 " ".join("%.0f%%" % (100 * qcov[x]) if qcov[x] is not None else " - "
                          for x in ("NE", "NW", "SE", "SW"))))

    covs = [t["coverage"] for t in tests]
    pooled = statistics.fmean(covs)
    worst = min(covs)
    print("\n   RESULT")
    print("      nominal coverage (1 - alpha)      : %.0f %%" % (100 * (1 - ALPHA)))
    print("      pooled out-of-sample coverage     : %.1f %%  over %d test day(s)"
          % (100 * pooled, len(tests)))
    print("      worst single test day             : %.1f %%" % (100 * worst))
    print("      shortfall vs nominal              : %+.1f points" % (100 * (pooled - (1 - ALPHA))))

    print("\n   HOW TO READ A SHORTFALL")
    print("      Conformal coverage is guaranteed only if the calibration days and the test day are")
    print("      exchangeable. They are not -- weather drifts. So a shortfall is not a bug in the")
    print("      mathematics, it measures how far FortyGuard's forecast error drifts day to day.")
    print("      The operational fix is a shorter calibration window or a per-day inflation factor,")
    print("      and this number is what tells you whether either is needed.")

    p1 = pooled >= MIN_COVERAGE
    p2 = worst >= MIN_DAY_COVERAGE
    p3 = len(tests) >= MIN_TEST_DAYS
    ok = p1 and p2 and p3
    print("\n   VERDICT AGAINST CONDITIONS FIXED BEFORE ANY OUTCOME EXISTED")
    print("      P1 pooled coverage >= %.0f %%   : %s  (%.1f %%)"
          % (100 * MIN_COVERAGE, p1, 100 * pooled))
    print("      P2 no test day < %.0f %%        : %s  (%.1f %%)"
          % (100 * MIN_DAY_COVERAGE, p2, 100 * worst))
    print("      P3 at least %d test days       : %s  (%d)" % (MIN_TEST_DAYS, p3, len(tests)))
    print()
    verdict(ok,
            "PASS - a bound calibrated on earlier days covers %.1f %% of 17k locations on days it "
            "has never seen, against a %.0f %% promise, worst day %.1f %%. The central product claim "
            "is measured out of sample rather than asserted."
            % (100 * pooled, 100 * (1 - ALPHA), 100 * worst),
            ("NOT YET DECIDABLE - only %d test day(s) available, %d required. Keep collecting; this "
             "is a calendar limit, not a result." % (len(tests), MIN_TEST_DAYS)) if not p3 else
            ("FAIL - out-of-sample coverage is %.1f %% against a %.0f %% promise (worst day %.1f %%). "
             "The bound does not mean what it says across days. Do NOT quote a 90 %% bound. Either "
             "shorten the calibration window, inflate per day, or state the measured rate instead of "
             "the nominal one -- and say which you did."
             % (100 * pooled, 100 * (1 - ALPHA), 100 * worst)))

    save_result("n26_coverage.json", {
        "alpha": ALPHA, "nominal_coverage": 1 - ALPHA,
        "days": [{k: p[k] for k in ("date", "lead_h", "n", "mean_d", "sd_d")} for p in pairs],
        "tests": tests, "pooled_coverage": pooled, "worst_day_coverage": worst,
        "n_test_days": len(tests),
        "lead_spread_h": lead_spread, "lead_range_h": [min(leads), max(leads)] if leads else None,
        "leads_comparable": lead_spread <= LEAD_SPREAD_WARN_H,
        "measures": "coverage across ~17.9k locations on an unseen day, bound calibrated on "
                    "earlier days",
        "does_not_measure": "breach rate at one fixed site over many days; tiles are spatially "
                            "correlated so the effective sample is far below the tile count",
        "p1_pooled": p1, "p2_worst_day": p2, "p3_enough_days": p3, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "collect").lower()
    sys.exit({"collect": collect, "report": report}.get(mode, collect)())
