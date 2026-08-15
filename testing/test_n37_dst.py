# -*- coding: utf-8 -*-
"""N-37  ---  is env_params' DAYLIGHT-SAVING error in the LABEL only, or in the DATA?   PAID, 1 call.

THE FINDING THIS RESOLVES
    fortyguard-api-findings.md section 1.8 established that env_params reports
    metadata.timezone = "GMT-5" and timezone_offset_hours = -5 on dates inside Eastern DAYLIGHT time,
    when the AOI is on EDT = -04:00. Timestamps come back as e.g. "2026-07-28T15:00:00-05:00".

    So the LABEL is definitively wrong. What we could not tell is whether the DATA is also shifted:

        LABEL ONLY   the values are for the wall-clock hour the caller asked for. Anyone who reads
                     the ISO offset correctly resolves 15:00-05:00 to 20:00 UTC = 16:00 local and is
                     an hour out; anyone who ignores the offset gets the right answer. Bad, but the
                     numbers are usable.

        DATA SHIFTED the values are for an hour later than requested. Then every timestamp we have
                     ever used is an hour out, and the sharpening and coverage tests inherit it.

    That distinction matters enough to spend one call on.

THE METHOD
    Relative humidity has a strong, reliable diurnal cycle -- it bottoms out when temperature peaks.
    So a one-hour shift is detectable by cross-correlation against an independent station.

        env_params   one call, filter_type 2, 00:00 to 23:00 -> 24 hourly relative_humidity_percent
                     (the endpoint returns the whole day in ONE call: metadata.time_range reports
                     interval 1h and count 24 -- worth knowing, it is not documented)
        KIAD ASOS    temperature and dew point, same day, hourly, from the Iowa State archive
        RH from T,Td by the Magnus formula, which is standard:
                        e_s(T) = 6.112 exp(17.67 T / (T + 243.5))   hPa
                        RH     = 100 e_s(Td) / e_s(T)

    Then correlate env_params hour h against station hour h + L for L in -3..+3.
    The lag L that maximises the correlation is the answer:

        L = 0   -> the data matches the requested wall-clock hour. LABEL ONLY.
        L = +1  -> the data is one hour LATER than its label, which is exactly what applying the
                   -05:00 offset literally would produce. DATA SHIFTED.

PRE-REGISTERED, fixed before the call
    D1  the station RH series must have a real diurnal cycle -- peak-to-trough at least 15 points --
        or the method has no signal to lock onto and the result must not be reported.
    D2  the best-lag correlation must exceed 0.6, otherwise the two series are not comparable enough
        to locate a shift at all.
    D3  the best lag must beat the runner-up by at least 0.03 in correlation, otherwise call it
        UNRESOLVED rather than pick a winner from noise.

HONEST LIMIT
    env_params RH is a modelled value at 39.0100/-77.4460; KIAD is about 8 km south. RH varies
    smoothly at that scale, but they are not the same point, so a small correlation penalty is
    expected and only the LOCATION OF THE PEAK matters, not its height.
"""
import sys, os, math, statistics, urllib.request, urllib.parse, time
import numpy as np

from common import (load_key, credits_remaining, submit_poll, banner, save_result, verdict,
                    SCRATCH, FIXTURES)
import json

LAT, LON = 39.0100, -77.4460
DAY = "2026-08-10"
LAGS = range(-3, 4)
D1_MIN_RANGE = 15.0
D2_MIN_CORR = 0.60
D3_MIN_MARGIN = 0.03


def es(t_c):
    return 6.112 * math.exp(17.67 * t_c / (t_c + 243.5))


def fetch_kiad_rh(day):
    """Hourly RH at KIAD for one day, computed from temperature and dew point."""
    base = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    y, mo, d = (int(v) for v in day.split("-"))
    parts = [("station", "IAD"), ("data", "tmpf"), ("data", "dwpf"),
             ("year1", y), ("month1", mo), ("day1", d),
             ("year2", y), ("month2", mo), ("day2", d + 1),
             ("tz", "America/New_York"), ("format", "onlycomma"), ("latlon", "no"),
             ("missing", "M"), ("trace", "T"), ("direct", "no"), ("report_type", 3)]
    url = base + "?" + urllib.parse.urlencode(parts)
    hdr = {"User-Agent": "Mozilla/5.0 (research)"}
    raw = None
    for a in range(4):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=hdr),
                                         timeout=180).read().decode("utf-8", "replace")
            break
        except Exception:
            time.sleep(4)
    if raw is None:
        return None
    byhour = {}
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 4:
            continue
        try:
            date, tm = p[1].split(" ")
            if date != day:
                continue
            hh = int(tm.split(":")[0])
            tf, df = float(p[2]), float(p[3])
        except Exception:
            continue
        tc, dc = (tf - 32) * 5.0 / 9.0, (df - 32) * 5.0 / 9.0
        rh = 100.0 * es(dc) / es(tc)
        byhour.setdefault(hh, []).append(min(rh, 100.0))
    return {h: statistics.fmean(v) for h, v in byhour.items()}


def pearson(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a = a - a.mean(); b = b - b.mean()
    d = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else 0.0


def main():
    banner("N-37  env_params DST: is the DATA shifted, or only the LABEL?   [PAID, 1 call]")
    key = load_key()
    before = credits_remaining(key)
    print("   cycle_remaining BEFORE: %s" % format(before, ","))
    print("   day under test: %s (inside Eastern DAYLIGHT time; AOI is on EDT = -04:00)" % DAY)

    tag = "n37_ep_%s" % DAY
    fx = os.path.join(FIXTURES, "%s.json" % tag)
    if os.path.exists(fx):
        res = json.load(open(fx)); print("   using cached env_params fixture")
    else:
        p = {"latitude": LAT, "longitude": LON, "temperature": 25.0,
             "date_time": {"start_date": DAY, "start_time": "00:00", "end_time": "23:00",
                           "filter_type": 2}}
        r = submit_poll(key, "env_params", p, tag)
        if not r.get("ok"):
            print("   env_params FAILED: %s" % r.get("error")); return 2
        res = r["result"]

    m = res.get("metadata", {})
    ts = m.get("timestamps") or []
    loc = (res.get("locations") or [{}])[0]
    ep_rh = loc.get("parameters", {}).get("relative_humidity_percent")
    if not isinstance(ep_rh, list) or len(ep_rh) != len(ts):
        print("   unexpected response shape"); return 2
    print("\n   env_params returned %d hourly values in ONE call" % len(ts))
    print("      metadata.timezone = %r, offset_hours = %r"
          % (m.get("timezone"), m.get("timezone_offset_hours")))
    print("      first timestamp %s   last %s" % (ts[0], ts[-1]))

    ep = {}
    for t, v in zip(ts, ep_rh):
        try:
            hh = int(t[11:13])
        except Exception:
            continue
        if v is not None:
            ep[hh] = float(v)

    st = fetch_kiad_rh(DAY)
    if not st:
        print("   station fetch failed"); return 2
    print("   KIAD gave %d hourly RH values (from temperature and dew point)" % len(st))

    st_vals = np.array([st[h] for h in sorted(st)])
    st_range = float(st_vals.max() - st_vals.min())
    d1 = st_range >= D1_MIN_RANGE
    print("\n   D1 station diurnal range %.1f points (need >= %.0f) : %s"
          % (st_range, D1_MIN_RANGE, d1))
    print("      station RH min at hour %d, max at hour %d"
          % (min(st, key=lambda h: st[h]), max(st, key=lambda h: st[h])))
    print("      env_params RH min at hour %d, max at hour %d"
          % (min(ep, key=lambda h: ep[h]), max(ep, key=lambda h: ep[h])))
    if not d1:
        print("\n   *** no usable diurnal signal on this day. Do NOT report a result. Pick another day.")
        return 2

    print("\n   CROSS-CORRELATION   env_params hour h  vs  station hour h + L")
    print("      %6s %8s %10s" % ("lag L", "n", "corr"))
    corrs = {}
    for L in LAGS:
        pairs = [(ep[h], st[h + L]) for h in sorted(ep) if (h + L) in st]
        if len(pairs) < 12:
            continue
        c = pearson([x[0] for x in pairs], [x[1] for x in pairs])
        corrs[L] = {"n": len(pairs), "corr": c}
        print("      %6d %8d %10.4f %s" % (L, len(pairs), c, "  <-- best" if False else ""))
    best = max(corrs, key=lambda L: corrs[L]["corr"])
    ranked = sorted(corrs, key=lambda L: -corrs[L]["corr"])
    margin = corrs[ranked[0]]["corr"] - (corrs[ranked[1]]["corr"] if len(ranked) > 1 else -1)
    print("\n      best lag L = %+d (corr %.4f), runner-up L = %+d (corr %.4f), margin %.4f"
          % (best, corrs[best]["corr"], ranked[1], corrs[ranked[1]]["corr"], margin))

    d2 = corrs[best]["corr"] >= D2_MIN_CORR
    d3 = margin >= D3_MIN_MARGIN
    print("      D2 best corr >= %.2f : %s" % (D2_MIN_CORR, d2))
    print("      D3 margin >= %.2f    : %s" % (D3_MIN_MARGIN, d3))

    if not (d2 and d3):
        concl = "UNRESOLVED"
    elif best == 0:
        concl = "LABEL ONLY"
    else:
        concl = "DATA SHIFTED by %+d h" % best

    print("\n   CONCLUSION: %s" % concl)
    if concl == "LABEL ONLY":
        print("      The values correspond to the wall-clock hour requested. The -05:00 offset in the")
        print("      response is wrong but the numbers are the ones you asked for. A client that")
        print("      parses the offset CORRECTLY lands an hour out; one that ignores it is right.")
        print("      Our own timestamps are safe, because we index by the requested hour.")
    elif concl.startswith("DATA SHIFTED"):
        print("      *** The DATA is shifted, not just the label. Every env_params timestamp we have")
        print("          used is out by that much, and the sharpening and coverage tests inherit it.")
        print("          Re-examine before quoting anything that depends on env_params timing.")
    else:
        print("      The two series are not comparable enough on this day to locate a shift.")
        print("      Try another day with a sharper diurnal cycle. Claim nothing from this.")

    after = credits_remaining(key)
    print("\n   cycle_remaining AFTER: %s   APPARENT SPEND: %s"
          % (format(after, ","), format(before - after, ",")))

    ok = concl == "LABEL ONLY"
    print()
    verdict(ok,
            "PASS - the daylight-saving error is in the LABEL ONLY. env_params returns the values for "
            "the wall-clock hour requested, so our own use of it is unaffected, and the defect stays "
            "a (serious) interface problem rather than a data problem. Best lag %+d, correlation %.4f."
            % (best, corrs[best]["corr"]),
            "NOT the benign case - conclusion was %s (best lag %+d, corr %.4f, margin %.4f). If the "
            "data is shifted, every env_params timestamp we have used is out by that amount. If "
            "unresolved, repeat on a day with a sharper diurnal cycle."
            % (concl, best, corrs[best]["corr"], margin))

    save_result("n37_dst.json", {
        "day": DAY, "method": "cross-correlate env_params RH against KIAD station RH from T and Td "
                              "(Magnus), lags -3..+3 h",
        "env_params_one_call_returns_full_day": True, "n_hours": len(ep),
        "metadata_timezone": m.get("timezone"),
        "metadata_offset_hours": m.get("timezone_offset_hours"),
        "station_diurnal_range": st_range, "d1_signal": d1,
        "correlations": {str(k): v for k, v in corrs.items()},
        "best_lag": best, "best_corr": corrs[best]["corr"], "margin": margin,
        "d2_corr_ok": d2, "d3_margin_ok": d3, "conclusion": concl,
        "credits_before": before, "credits_after": after, "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
