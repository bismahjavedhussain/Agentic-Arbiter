# -*- coding: utf-8 -*-
"""N-25  ---  DOES THE FORECAST SHARPEN?  The one measurement the agency claim rests on.  PAID.

WHY THIS IS THE MOST IMPORTANT PAID TEST IN THE PROJECT
    N-24 swept the stopping rule against the best tuned fixed-hour rule across 77 points and found
    that the two risks gating the agency claim are NOT substitutes. At rho = 1.00 -- a forecast that
    never sharpens -- the rule LOSES at every peak-hour uncertainty tested, out to 4 h. So this one
    quantity decides whether the central decision is genuinely agentic or is a dressed-up threshold.

    Pre-registered in N-24, before any of this data existed:

        b >= 0.187   the stopping rule beats the tuned adversary by > 2 sigma   -> PASS
        0.129-0.187  break-even to marginal; re-run N-9 at the measured b       -> MARGINAL
        b <  0.129   waiting buys nothing; report the null and rebuild          -> FAIL

    where b is the exponent in sigma(lead) = sigma_anchor * (lead / 12) ** b, which is exactly the
    parameter N-9 and N-24 sweep. Nothing about the threshold is chosen after seeing the data.

WHAT N-13 GOT WRONG, AND WHY THIS FILE EXISTS INSTEAD OF A RERUN
    Two independent faults, both fixed here.

    1. THE 9-HOUR TIMEZONE BUG. The endpoint reads start_time in the AOI's own local zone. N-13
       built windows from datetime.now() on a UTC+5 machine and sent bare "%H:00" strings for an
       AOI at UTC-4. Its recorded leads of 2.0 h and 4.0 h were really 9.25 h and 11.25 h. See the
       block comment in common.py for the two proofs. All time handling here goes through
       common.site_window(), which refuses a naive datetime.

    2. THE TIME-OF-DAY CONFOUND. N-13 gave each lead a DIFFERENT target window, so lead time was
       confounded with diurnal predictability -- an 03:00 forecast may simply be easier than a 15:00
       one. Its own docstring flagged this and never fixed it.

       This test forecasts ONE target window repeatedly as it approaches. Same hours, same tiles,
       same geometry, only the lead changes. The confound is gone by construction, which is the
       whole reason to spend calls rather than reuse N-13's.

DESIGN
    Target window   14:00-16:00 site-local -- the diurnal peak, which is the quantity the agent
                    actually decides on. 2 h wide because start_time == end_time returns HTTP 500.
    Leads           ~9.5, 7.5, 5.5, 3.5, 1.5 h. A 6x baseline, all inside the confirmed 12 h
                    horizon, so the extrapolation to 12 h is a mild extension rather than a guess.
    AOI             8x8 km at 60 m granularity -> ~17,862 tiles per call. Pricing is FLAT in area
                    and granularity (4,220 credits either way), so the small polygon N-13 used was
                    45x less data for the same money. Same price, far tighter sigma.
    Metric          per-tile max_temperature over the window; residual = forecast - outcome.

HONESTY ABOUT THE SAMPLE
    ~17,862 tiles is not 17,862 independent samples -- neighbouring tiles see the same weather. So
    the report also fits b separately within four spatial quadrants and prints the spread. That
    spread, not the tile count, is the honest uncertainty. And this is ONE target window on ONE day:
    it measures the sharpening of this forecast system, not the day-to-day distribution of it.

USAGE
    python test_n25_sharpen.py plan     # choose the window, fire the first shot, write the manifest
    python test_n25_sharpen.py poll     # fire whatever is due now; safe to run repeatedly
    python test_n25_sharpen.py report   # fit b, compare against the pre-registered thresholds
"""
import json, math, os, statistics, sys
from datetime import timedelta

from common import (load_key, credits_remaining, submit_poll, banner, box_aoi, save_result,
                    verdict, RESULTS, FIXTURES, tile_key, site_now, site_window, lead_hours,
                    utc_now, SITE_TZ_NAME)

CENTRE = (39.0100, -77.4460)
SIDE_KM = 8.0
GRAN = 60
WIN_H = 2
TARGET_HOUR_SITE = 14              # 14:00-16:00 site-local: the diurnal peak
PLANNED_LEADS = [7.5, 5.5, 3.5, 1.5]   # after the immediate first shot
HORIZON_H = 12.0                   # confirmed: 11.25 h works, 13.25 h returns zero tiles
MANIFEST = os.path.join(RESULTS, "n25_manifest.json")

PASS_B = 0.187                     # pre-registered in N-24: 2-sigma win
MARGINAL_B = 0.129                 # pre-registered in N-24: break-even


# ----------------------------------------------------------------- payload / io
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
    if not os.path.exists(MANIFEST):
        return None
    return json.load(open(MANIFEST))


def write_manifest(m):
    json.dump(m, open(MANIFEST, "w"), indent=1, default=str)


# ----------------------------------------------------------------- plan
def plan():
    banner("N-25 plan  one target window, five leads -- does the forecast sharpen?   [PAID]")
    if load_manifest():
        print("   a manifest already exists at %s" % MANIFEST)
        print("   run 'poll' to continue it, or delete it to start over.")
        return 2

    sn = site_now()
    target = sn.replace(hour=TARGET_HOUR_SITE, minute=0, second=0, microsecond=0)
    w = site_window(target, WIN_H)
    lead0 = lead_hours(w["_start_utc"])

    print("   site zone %s -- site local now %s" % (SITE_TZ_NAME, sn.strftime("%Y-%m-%d %H:%M %Z")))
    print("   utc now                        %s" % utc_now().strftime("%Y-%m-%d %H:%M"))
    print("   TARGET WINDOW  %s %s-%s site-local  =  %s-%s UTC"
          % (w["start_date"], w["start_time"], w["end_time"],
             w["_start_utc"].strftime("%H:%M"), w["_end_utc"].strftime("%H:%M")))
    print("   true lead to window start now  %.2f h" % lead0)

    if lead0 <= 0:
        print("\n   ABORT: the target window has already started at the site. Run earlier in the")
        print("   machine's day -- the site is %d h behind this clock."
              % round((utc_now() - sn.replace(tzinfo=utc_now().tzinfo)).total_seconds() / 3600))
        return 2
    if lead0 > HORIZON_H:
        print("\n   ABORT: %.2f h exceeds the confirmed %.0f h horizon; the call would return zero"
              % (lead0, HORIZON_H))
        print("   tiles as a successful empty response. Wait %.1f h and re-plan."
              % (lead0 - HORIZON_H))
        return 2

    shots = [{"planned_lead_h": round(lead0, 2), "due_utc": utc_now().isoformat(),
              "done": False, "immediate": True}]
    for L in PLANNED_LEADS:
        if L >= lead0:
            print("   skip lead %.1f h: not shorter than the immediate shot (%.2f h)" % (L, lead0))
            continue
        shots.append({"planned_lead_h": L,
                      "due_utc": (w["_start_utc"] - timedelta(hours=L)).isoformat(),
                      "done": False, "immediate": False})

    print("\n   SCHEDULE  (%d forecast shots + 1 outcome)" % len(shots))
    for s in shots:
        due = s["due_utc"][:16].replace("T", " ")
        print("      lead %5.2f h   fire at %s UTC" % (s["planned_lead_h"], due))
    out_due = w["_end_utc"] + timedelta(minutes=15)
    print("      OUTCOME       fire at %s UTC" % out_due.strftime("%Y-%m-%d %H:%M"))

    m = {"created_utc": utc_now().isoformat(), "site_tz": SITE_TZ_NAME,
         "centre": list(CENTRE), "side_km": SIDE_KM, "granularity": GRAN, "win_h": WIN_H,
         "target_site": "%s %s-%s" % (w["start_date"], w["start_time"], w["end_time"]),
         "date_time": {k: v for k, v in w.items() if not k.startswith("_")},
         "target_start_utc": w["_start_utc"].isoformat(),
         "target_end_utc": w["_end_utc"].isoformat(),
         "outcome_due_utc": out_due.isoformat(),
         "horizon_h": HORIZON_H, "pass_b": PASS_B, "marginal_b": MARGINAL_B,
         "shots": shots, "outcome": {"done": False},
         "credits_before": None, "errors": {}}
    write_manifest(m)
    print("\n   manifest written. Firing the first shot now ...")
    return poll()


# ----------------------------------------------------------------- poll
def poll():
    m = load_manifest()
    if not m:
        print("   no manifest -- run 'plan' first.")
        return 2
    key = load_key()
    if m.get("credits_before") is None:
        m["credits_before"] = credits_remaining(key)
        write_manifest(m)
    aoi = box_aoi(m["centre"][0], m["centre"][1], m["side_km"])
    now = utc_now()
    start_utc = _iso(m["target_start_utc"])
    did = 0

    for s in m["shots"]:
        if s["done"]:
            continue
        if _iso(s["due_utc"]) > now:
            continue
        actual_lead = lead_hours(start_utc, now)
        tag = "n25_f_lead%05.2f" % max(actual_lead, 0)
        print("\n   FORECAST shot  planned lead %.2f h, actual lead %.2f h  ->  %s"
              % (s["planned_lead_h"], actual_lead, tag))
        if actual_lead <= 0:
            s["done"] = True
            s["error"] = "window already started; shot skipped"
            print("      SKIPPED: the window has already started (lead %.2f h)" % actual_lead)
            write_manifest(m)
            continue
        d, n = call_window(key, aoi, m["date_time"], tag)
        s["done"] = True
        s["fired_utc"] = now.isoformat()
        s["actual_lead_h"] = round(actual_lead, 3)
        s["tag"] = tag
        if d is None:
            s["error"] = n
            m["errors"][tag] = n
            print("      FAILED: %s" % n)
        else:
            s["n_tiles"] = n
            s["mean_max"] = round(statistics.fmean(v[0] for v in d.values()), 4)
            print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","), s["mean_max"]))
        did += 1
        write_manifest(m)
        now = utc_now()

    if not m["outcome"]["done"] and utc_now() >= _iso(m["outcome_due_utc"]):
        print("\n   OUTCOME  the window has elapsed; requesting it as history ...")
        d, n = call_window(key, aoi, m["date_time"], "n25_outcome")
        m["outcome"]["done"] = True
        m["outcome"]["fired_utc"] = utc_now().isoformat()
        if d is None:
            m["outcome"]["error"] = n
            print("      FAILED: %s" % n)
        else:
            m["outcome"]["tag"] = "n25_outcome"
            m["outcome"]["n_tiles"] = n
            m["outcome"]["mean_max"] = round(statistics.fmean(v[0] for v in d.values()), 4)
            print("      %s tiles   mean per-tile max %.4f C" % (format(n, ","),
                                                                 m["outcome"]["mean_max"]))
        did += 1
        write_manifest(m)

    pending = [s for s in m["shots"] if not s["done"]]
    m["credits_after"] = credits_remaining(key)
    write_manifest(m)
    print("\n   %d call(s) made this poll. %d forecast shot(s) still pending." % (did, len(pending)))
    if pending:
        nxt = min(_iso(s["due_utc"]) for s in pending)
        print("      next due %s UTC (in %.2f h)"
              % (nxt.strftime("%Y-%m-%d %H:%M"), (nxt - utc_now()).total_seconds() / 3600))
    elif not m["outcome"]["done"]:
        od = _iso(m["outcome_due_utc"])
        print("      all shots fired; OUTCOME due %s UTC (in %.2f h)"
              % (od.strftime("%Y-%m-%d %H:%M"), (od - utc_now()).total_seconds() / 3600))
    else:
        print("      everything collected -- run 'report'.")
    print("   credits: before %s  after %s  APPARENT SPEND %s"
          % (format(m["credits_before"], ","), format(m["credits_after"], ","),
             format(m["credits_before"] - m["credits_after"], ",")))
    return 0


def _iso(s):
    from datetime import datetime
    return datetime.fromisoformat(s) if isinstance(s, str) else s


# ----------------------------------------------------------------- report
# Two-sided 95 % critical values of Student's t by degrees of freedom. Hard-coded to avoid a scipy
# dependency; verified against the t CDF to 5 decimal places for dof 2-10, and dof 1
# against the exact Cauchy form 0.5 + atan(x)/pi.
TCRIT_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
            8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 15: 2.131, 20: 2.086}


def _fit_stats(leads, vals):
    """OLS of ln(vals) on ln(lead), WITH the standard error and a 95 % CI on the slope.

    b IS the exponent N-9 and N-24 sweep. The SE and the interval were added for a
    specific reason worth keeping in the file: earlier that day a 4-point slope was fitted from a
    PROXY (the shortest-lead forecast standing in for the outcome), came out at -0.61, and was
    reported as a finding. It had to be withdrawn. The SE was 0.674, t was -0.90, and the 95 % CI
    ran [-3.51, +2.29] -- an interval that excludes nothing at all, not zero, not the 0.129
    break-even, not the 0.187 threshold, not even the 0.50 that N-24's headline sweep held fixed.

    A slope without an interval is not a measurement. This is now the ONLY place a slope is
    computed in this file, so the headline fits and the quadrant fits cannot drift apart.
    """
    n = len(leads)
    xs = [math.log(l) for l in leads]
    ys = [math.log(max(v, 1e-9)) for v in vals]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0 or n < 3:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    ss_t = sum((y - my) ** 2 for y in ys)
    r2 = 1.0 - sum(r * r for r in resid) / ss_t if ss_t > 0 else None
    dof = n - 2
    se = math.sqrt(sum(r * r for r in resid) / dof / sxx)
    tc = TCRIT_95.get(dof, 1.96 if dof > 30 else 4.303)
    return {"n": n, "dof": dof, "b": b, "se": se, "r2": r2, "tcrit": tc,
            "t": (b / se if se > 0 else float("inf")),
            "ci_lo": b - tc * se, "ci_hi": b + tc * se}


def _fit(leads, sds):
    """Thin wrapper preserving the original (b, r2) contract, including (None, None) on a
    degenerate design matrix. The verdict path uses only these two values, so routing it through
    _fit_stats leaves every existing number and the exit code unchanged."""
    f = _fit_stats(leads, sds)
    return (None, None) if f is None else (f["b"], f["r2"])


def report():
    banner("N-25 report  fitting the sharpening exponent against a pre-registered threshold")
    m = load_manifest()
    if not m:
        print("   no manifest -- run 'plan' first.")
        return 2
    op = os.path.join(FIXTURES, "n25_outcome.json")
    if not m["outcome"].get("done") or not os.path.exists(op):
        print("   the outcome has not been collected yet. Run 'poll' after %s UTC."
              % str(m["outcome_due_utc"])[:16])
        return 2

    H = field_max(json.load(open(op)))
    print("   target window %s site-local (%s)" % (m["target_site"], m["site_tz"]))
    print("   outcome: %s tiles, mean per-tile max %.4f C"
          % (format(len(H), ","), statistics.fmean(v[0] for v in H.values())))

    lats = [v[1] for v in H.values()]
    lons = [v[2] for v in H.values()]
    mid_la, mid_lo = statistics.median(lats), statistics.median(lons)

    rows, fields = [], {}
    print("\n   %8s %9s %9s %8s %8s %9s  %s"
          % ("lead h", "n tiles", "bias C", "sd C", "rms C", "q90|res|", "quadrant sd (NE NW SE SW)"))
    for s in m["shots"]:
        if not s.get("tag"):
            continue
        fp = os.path.join(FIXTURES, "%s.json" % s["tag"])
        if not os.path.exists(fp):
            continue
        F = field_max(json.load(open(fp)))
        keys = [k for k in F if k in H]
        if len(keys) < 100:
            print("      lead %.2f h: only %d matched tiles -- skipped" % (s["actual_lead_h"],
                                                                           len(keys)))
            continue
        res = [F[k][0] - H[k][0] for k in keys]
        a = sorted(abs(x) for x in res)
        q90 = a[min(len(a) - 1, math.ceil((len(a) + 1) * 0.9) - 1)]
        bias = statistics.fmean(res)
        sd = statistics.pstdev(res)
        rms = math.sqrt(bias ** 2 + sd ** 2)      # total error: bias and spread together
        quads = {"NE": [], "NW": [], "SE": [], "SW": []}
        for k in keys:
            la, lo = F[k][1], F[k][2]
            quads[("N" if la >= mid_la else "S") + ("E" if lo >= mid_lo else "W")].append(
                F[k][0] - H[k][0])
        qsd = {q: (statistics.pstdev(v) if len(v) > 1 else None) for q, v in quads.items()}
        rows.append({"lead_h": s["actual_lead_h"], "n": len(keys), "tag": s["tag"],
                     "bias": bias, "sd": sd, "rms": rms,
                     "q90_abs": q90, "quad_sd": qsd})
        fields[s["actual_lead_h"]] = F
        print("   %8.2f %9s %+9.4f %8.4f %8.4f %9.4f  %s"
              % (s["actual_lead_h"], format(len(keys), ","), bias, sd, rms, q90,
                 " ".join("%.4f" % qsd[q] if qsd[q] else "  -  " for q in ("NE", "NW", "SE", "SW"))))

    if len(rows) < 3:
        print("\n   fewer than 3 leads recovered -- a slope cannot be fitted, and a 2-point slope")
        print("   has no residual left to test the power-law assumption with. Reporting no verdict.")
        save_result("n25_sharpen.json", {"manifest": m, "rows": rows, "pass": None})
        return 2

    rows.sort(key=lambda r: r["lead_h"])
    leads = [r["lead_h"] for r in rows]

    # ---------------------------------------------------------------- refresh diagnostic
    # THE MECHANISM CHECK, and it decides how a null result must be read.
    #
    # FortyGuard publishes a 12 h horizon and hourly resolution but states its REFRESH CADENCE
    # nowhere -- not in the API docs, not on the technology page, not in the 12-hour-forecast
    # announcement. So if the model runs every N hours and several of our shots land inside one
    # run, those shots return the SAME numbers and b is forced to 0 for a reason that has nothing
    # to do with forecast skill. Two very different worlds:
    #
    #   b ~ 0 and forecasts IDENTICAL  -> we never received a new forecast. Says nothing about
    #                                     skill. Find the cadence and re-measure across it.
    #   b ~ 0 and forecasts DIFFERENT  -> new forecasts arrive and are no better. THAT is the
    #                                     result that kills the agency claim.
    #
    # Without this check a null would be ambiguous and could kill the project for the wrong reason.
    order = sorted(fields.keys(), reverse=True)       # issue order: longest lead first
    refresh, n_distinct = [], 1
    print("\n   DID A NEW FORECAST ACTUALLY ARRIVE BETWEEN SHOTS?")
    print("      %-22s %10s %10s %10s %s" % ("issued pair", "tiles", "frac chg", "rms chg", ""))
    for i in range(1, len(order)):
        prev, cur = fields[order[i - 1]], fields[order[i]]
        common = [k for k in cur if k in prev]
        if not common:
            continue
        d = [cur[k][0] - prev[k][0] for k in common]
        frac = sum(1 for x in d if abs(x) > 1e-6) / len(d)
        rms_chg = math.sqrt(statistics.fmean(x * x for x in d))
        changed = frac > 0.01
        n_distinct += 1 if changed else 0
        refresh.append({"from_lead": order[i - 1], "to_lead": order[i], "n": len(common),
                        "frac_changed": frac, "rms_change": rms_chg,
                        "max_change": max(abs(x) for x in d), "changed": changed})
        print("      %-22s %10s %9.1f%% %10.4f %s"
              % ("%.2f h -> %.2f h" % (order[i - 1], order[i]), format(len(common), ","),
                 100 * frac, rms_chg,
                 "new forecast" if changed else "*** IDENTICAL - same model run ***"))
    print("      -> %d distinct forecast(s) across %d shots" % (n_distinct, len(order)))
    if n_distinct < 3:
        print("      *** WARNING: fewer than 3 distinct forecasts. Any slope below is fitted")
        print("          largely across REPEATS of the same forecast, so a small b would measure")
        print("          FortyGuard's refresh cadence, NOT its forecast skill. Read the verdict")
        print("          as inconclusive and re-measure with shots spread across the cadence.")

    b, r2 = _fit(leads, [r["sd"] for r in rows])
    bq, _ = _fit(leads, [r["q90_abs"] for r in rows])
    br, _ = _fit(leads, [r["rms"] for r in rows])

    print("\n   FIT  sigma(lead) = A * lead ** b   over leads %.2f-%.2f h (%.1fx baseline)"
          % (min(leads), max(leads), max(leads) / min(leads)))
    print("      b from per-tile sd        : %+.3f   (R^2 %.3f)  <- the headline" % (b, r2 if r2 else float("nan")))
    print("      b from |residual| q90     : %+.3f   (the quantity the conformal bound uses)" % bq)
    print("      b from rms (bias + sd)    : %+.3f   (total error, if no bias correction)" % br)

    # ---------------------------------------------------------------- the interval on b
    # Added later. See _fit_stats' docstring for the withdrawn claim that motivated it.
    # This is REPORTING ONLY -- it does not touch the verdict or the exit code, because the
    # pre-registered condition is a POINT-ESTIMATE rule (b >= 0.187) and tightening it to "the CI
    # lower bound clears 0.187" after seeing the data would be moving a threshold after the fact.
    # N-8, N-33 and N-34 are all recorded as failures rather than re-specified; same rule here.
    stats = {}
    for label, keyname in (("sd", "sd"), ("q90", "q90_abs"), ("rms", "rms")):
        f = _fit_stats(leads, [r[keyname] for r in rows])
        if f:
            stats[label] = f
    if stats:
        any_f = next(iter(stats.values()))
        print("\n   THE SAME FITS WITH AN INTERVAL   (%d points, %d dof, t_crit %.3f)"
              % (any_f["n"], any_f["dof"], any_f["tcrit"]))
        print("      %-5s %9s %8s %8s %8s   %s"
              % ("metric", "b", "SE", "t", "R^2", "95 % CI"))
        for label in ("sd", "q90", "rms"):
            f = stats.get(label)
            if not f:
                continue
            print("      %-5s %+9.4f %8.4f %8.2f %8.3f   [%+.3f, %+.3f]"
                  % (label, f["b"], f["se"], f["t"],
                     f["r2"] if f["r2"] is not None else float("nan"), f["ci_lo"], f["ci_hi"]))

        h = stats.get("sd")
        print("\n      WHAT THE INTERVAL EXCLUDES -- the only claims this data supports")
        for nm, v in (("0.000 no sharpening", 0.0), ("0.129 break-even", MARGINAL_B),
                      ("0.187 two-sigma", PASS_B), ("0.500 assumed by N-24", 0.500)):
            ex = v < h["ci_lo"] or v > h["ci_hi"]
            print("         %-24s %s" % (nm, "EXCLUDED" if ex else "inside the interval"))
        if h["ci_lo"] <= 0.0 <= h["ci_hi"]:
            print("\n      *** THE INTERVAL CONTAINS ZERO. On one day and %d leads this cannot"
                  % len(leads))
            print("          distinguish sharpening from none. The pre-registered rule below is a")
            print("          POINT-ESTIMATE rule and returns whatever it returns -- but do NOT report")
            print("          a low b as 'we measured that the forecast does not sharpen'. It is an")
            print("          UNDERPOWERED result. More DAYS is the fix, not more tiles: 17,862 tiles")
            print("          are one weather realisation, and the sd column is flat across leads.")
        if 0.500 < h["ci_lo"] or 0.500 > h["ci_hi"]:
            print("\n      *** b = 0.500 IS EXCLUDED, and that is the load-bearing finding here.")
            print("          N-24's headline '+0.356 gain, 11.2 sigma' was computed with the")
            print("          exponent HELD FIXED AT 0.50 (test_n24_breakeven.py line 211). That")
            print("          assumption is now ruled out by measurement, whatever the true b is.")

    quad_bs = {}
    for q in ("NE", "NW", "SE", "SW"):
        sds = [r["quad_sd"][q] for r in rows]
        if all(s for s in sds):
            qb, _ = _fit(leads, sds)
            quad_bs[q] = qb
    if quad_bs:
        vals = list(quad_bs.values())
        print("      b per spatial quadrant    : %s"
              % "  ".join("%s %+.3f" % (k, v) for k, v in quad_bs.items()))
        print("      -> spread %+.3f to %+.3f. Tiles are spatially correlated, so THIS spread is"
              % (min(vals), max(vals)))
        print("         the honest uncertainty on b, not the %s tile count." % format(rows[0]["n"], ","))

    in_range = rows[0]["sd"] / rows[-1]["sd"] if rows[-1]["sd"] > 0 else float("nan")
    print("\n   MEASURED IN-RANGE RATIO  sigma(%.2f h) / sigma(%.2f h) = %.3f"
          % (min(leads), max(leads), in_range))
    rho_fit = (3.0 / 12.0) ** b
    print("   rho EXTRAPOLATED to the N-24 definition sigma(3h)/sigma(12h) = %.3f" % rho_fit)
    print("      [S] this last number extrapolates the fitted power law beyond the measured range.")
    print("          Quote b against the threshold; quote rho only with this caveat attached.")

    print("\n   VERDICT AGAINST THE N-24 PRE-REGISTERED THRESHOLDS")
    print("      b >= %.3f  -> stopping rule beats the tuned adversary by > 2 sigma" % PASS_B)
    print("      %.3f-%.3f  -> break-even to marginal; re-run N-9 at the measured b"
          % (MARGINAL_B, PASS_B))
    print("      b <  %.3f  -> waiting buys nothing; report the null" % MARGINAL_B)
    print("      measured b = %+.3f" % b)
    band = ("PASS" if b >= PASS_B else "MARGINAL" if b >= MARGINAL_B else "FAIL")
    print("      -> %s" % band)

    # A slope is only IDENTIFIED if at least three DISTINCT forecasts went into it. With two, the
    # "slope" is an artifact of where the single step between model runs happens to fall -- and a
    # synthetic test with two runs and a true b of 0.5 produced a spurious +0.331, which the earlier
    # version of this code reported as a PASS. A false pass is worse than a false fail here: it would
    # let us claim agency we have not demonstrated. So distinctness gates the verdict, both ways.
    quad_ok = bool(quad_bs) and min(quad_bs.values()) >= MARGINAL_B
    identified = n_distinct >= 3
    inconclusive = not identified
    ok = (b >= PASS_B) and identified

    if inconclusive:
        print("\n   *** INCONCLUSIVE -- neither a pass nor a fail ***")
        print("      Only %d distinct forecast(s) arrived across %d shots, so b is NOT identified:"
              % (n_distinct, len(order)))
        print("      the fit runs mostly across repeats of the same model run. Whatever b came out,")
        print("      it measures FortyGuard's refresh cadence, not its forecast skill. This applies")
        print("      to a HIGH b as much as a low one -- two runs at different error levels produce")
        print("      a slope that looks real and is not.")
        print("      ACTION: re-run with shots spaced wider than the cadence implied above.")
    print()
    verdict(ok,
            "PASS - forecast error shrinks with lead time at exponent %+.3f, clearing the %.3f "
            "pre-registered in N-24, and %d distinct forecasts went into the fit so the slope is "
            "identified. Waiting genuinely buys information, so the stopping rule rests on measured "
            "behaviour rather than an assumed shape. Every spatial quadrant %s the break-even. "
            "Re-run N-9 and N-24 at b = %.3f and quote that number."
            % (b, PASS_B, n_distinct, "clears" if quad_ok else "does NOT clear", b),
            ("INCONCLUSIVE - b = %+.3f was fitted across only %d distinct forecast(s), so it is not "
             "identified and MUST NOT be reported either way. Determine FortyGuard's refresh cadence "
             "from the table above and re-measure with shots spaced wider than it. Nothing is known "
             "about forecast sharpening yet." % (b, n_distinct)) if inconclusive else
            ("MARGINAL - measured b = %+.3f clears the %.3f break-even but NOT the %.3f "
             "pre-registered for a 2-sigma win. The threshold does not move after the fact. Re-run "
             "N-9 and N-24 at b = %.3f and quote whatever gain that yields -- it may still be "
             "positive, just not by two standard errors. Say 'marginal', never 'passes'."
             % (b, MARGINAL_B, PASS_B, b)) if band == "MARGINAL" else
            ("FAIL - measured b = %+.3f is below the %.3f break-even pre-registered in N-24, across "
             "%d distinct forecasts so the result IS identified. At this sharpening rate waiting buys "
             "no information and the stopping rule earns nothing over a tuned fixed-hour rule. Report "
             "the null honestly and rebuild the agency claim on the peak-hour risk alone -- N-24's "
             "joint grid says that will not be enough on its own, so this outcome means the central "
             "decision is not agentic and the project needs rethinking."
             % (b, MARGINAL_B, n_distinct)))

    save_result("n25_sharpen.json", {
        "design": "ONE target window, %d leads -- no time-of-day confound" % len(rows),
        "target_site": m["target_site"], "site_tz": m["site_tz"],
        "aoi_side_km": SIDE_KM, "granularity": GRAN,
        "supersedes": "N-13, which had a 9-hour timezone error AND a time-of-day confound",
        "rows": rows, "leads_h": leads,
        "refresh_diagnostic": refresh, "n_distinct_forecasts": n_distinct,
        "inconclusive_due_to_refresh": inconclusive,
        "b_sd": b, "b_r2": r2, "b_q90": bq, "b_rms": br, "b_by_quadrant": quad_bs,
        # The interval. Quote b from this project ONLY with n, SE and CI beside it.
        "b_stats": stats,
        "b_ci_contains_zero": bool(stats and stats["sd"]["ci_lo"] <= 0.0 <= stats["sd"]["ci_hi"]),
        "b_ci_excludes_assumed_0.50": bool(
            stats and not (stats["sd"]["ci_lo"] <= 0.500 <= stats["sd"]["ci_hi"])),
        "underpowered": bool(stats and stats["sd"]["ci_lo"] <= MARGINAL_B <= stats["sd"]["ci_hi"]),
        "verdict_rule": "point-estimate rule pre-registered in N-24; NOT tightened to a CI rule "
                        "after seeing the data",
        "in_range_ratio": in_range, "rho_extrapolated": rho_fit,
        "pass_b": PASS_B, "marginal_b": MARGINAL_B,
        "band": "INCONCLUSIVE" if inconclusive else band, "slope_identified": identified,
        "all_quadrants_clear_breakeven": quad_ok,
        "credits_before": m.get("credits_before"), "credits_after": m.get("credits_after"),
        "errors": m.get("errors"), "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    mode = (sys.argv[1] if len(sys.argv) > 1 else "poll").lower()
    sys.exit({"plan": plan, "poll": poll, "report": report}.get(mode, poll)())
