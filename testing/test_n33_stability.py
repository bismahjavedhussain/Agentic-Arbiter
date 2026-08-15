# -*- coding: utf-8 -*-
"""N-33  ---  derive the dispersion constant from REAL WEATHER, hour by hour.   FREE.

THE QUESTION
    Our solver has one diffusivity D. Until 2026-08-12 it was 8.0 m2/s with, in our own test file's
    words, "no basis at all". N-30 fixed the provenance: D can be DERIVED from the published
    Pasquill-Gifford dispersion curves once you know the atmospheric stability class, because our
    solver's plume-width law (sigma_y^2 = 2 D x / u, verified exactly in N-29) can be set equal to the
    published sigma_y = a x^b at the separation that matters:

        D  =  u * sigma_y(x)^2 / (2 x)

    But stability class is not a free choice. It is determined by WIND SPEED and SUNSHINE. So the
    honest version of the model does not have a constant D at all -- it has a D that changes every
    hour with the weather. This test asks: across real weather at the real site, what does D actually
    do? Is it a narrow band we can defend as "about 8", or does it swing so widely that a single
    value was never defensible?

WHY THIS IS RUNNABLE DESPITE FORTYGUARD SERVING NO WIND
    FortyGuard exposes no wind field (36 response fields checked; none is wind -- see
    fortyguard-api-findings.md section 6). That blocks deriving D from FortyGuard ALONE. It does not
    block deriving it at all: hourly wind and sky condition for the AOI come from the ASOS station at
    Washington Dulles (KIAD), inside the 8 km AOI, via the Iowa State University Environmental
    Mesonet archive -- free, public, no key, reported in America/New_York which is the same site-local
    convention the FortyGuard endpoint uses.

    So the architecture is: FortyGuard for the temperature field, ASOS for wind and sky. The feature
    request to FortyGuard stands, because a station is one point where their field is 60 m -- but the
    model is not blocked in the meantime.

SOURCING, AND ONE CELL I DO NOT TRUST
    Pasquill stability class from wind speed and insolation, Table 2 of the Pasquill-Gifford model
    document (page 4), transcribed with the layout preserved:

        wind m/s   Strong   Medium   Slight   Night-cloudy   Night-clear
        < 2        A        A-B      B        (blank)        (blank)
        2-3        A-B      B        C        E              E
        3-5        B        B-C      C        D              E
        5-6        C        C-D      D        D              D
        > 6        C        D        C(!)     D              D

    Two problems, both stated rather than smoothed over:
      * the "< 2" row leaves both night cells BLANK. Standard versions give F. We treat < 2 at night
        as F and flag every hour where that happens.
      * the "> 6 / Slight" cell reads C. Every standard version of this table gives D, and C (more
        unstable than the Medium column's D) is not physically sensible at high wind. We treat it as
        a probable typo in that document, use D, and flag every hour where that cell is hit.

    The table gives class from (wind, insolation category) but does NOT define how to obtain the
    insolation category from observations. The rigorous route is Turner's (1964) net-radiation index.
    We use the standard simplification -- solar elevation banded, then reduced for cloud cover -- and
    label it OURS rather than sourced, because it is.
"""
import sys, os, math, statistics
from collections import Counter
import numpy as np

from common import banner, save_result, verdict, SCRATCH

CSV = os.path.join(SCRATCH, "kiad_full_2026.csv")
LAT, LON = 39.0100, -77.4460
SEPARATION_M = 230.0          # condenser bank edge to intake in demo_site
CURRENT_D = 8.0               # the value the model has been using

# published Pasquill-Gifford continuous-plume coefficients, sigma_y = a x^b, metres
PG = {"A": (0.493, 0.88), "B": (0.337, 0.88), "C": (0.195, 0.90),
      "D": (0.128, 0.90), "E": (0.091, 0.91), "F": (0.067, 0.90)}
# cloud code -> fraction of sky covered (METAR conventions)
CLOUD = {"CLR": 0.0, "SKC": 0.0, "NCD": 0.0, "FEW": 0.1875, "SCT": 0.4375,
         "BKN": 0.6875, "OVC": 1.0, "VV": 1.0, "OVX": 1.0}


def solar_elevation(lat, lon, y, mo, d, hh, mm, utc_offset_h):
    """Solar elevation in degrees. Standard NOAA-style algorithm.

    Sanity-checked below: at 39.01 N on 21 June at solar noon it must give about
    90 - 39.01 + 23.44 = 74.4 deg.
    """
    # fractional day -> UTC
    ut = hh + mm / 60.0 - utc_offset_h
    a = math.floor((14 - mo) / 12)
    yy = y + 4800 - a
    mm2 = mo + 12 * a - 3
    jdn = d + math.floor((153 * mm2 + 2) / 5) + 365 * yy + math.floor(yy / 4) \
        - math.floor(yy / 100) + math.floor(yy / 400) - 32045
    jd = jdn + (ut - 12.0) / 24.0
    n = jd - 2451545.0
    L = (280.460 + 0.9856474 * n) % 360.0                     # mean longitude
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)       # mean anomaly
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    # equation of time, minutes
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    eot = (math.radians(L) - ra)
    eot = (eot + math.pi) % (2 * math.pi) - math.pi
    eot_min = 4.0 * math.degrees(eot)
    tst = ut * 60.0 + eot_min + 4.0 * lon                     # true solar time, minutes
    ha = math.radians(tst / 4.0 - 180.0)
    la = math.radians(lat)
    sin_el = math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))


def insolation_category(elev_deg, cloud_frac):
    """[OURS] elevation banded, then reduced for cloud. Not from the source table -- stated as ours.

    The rigorous route is Turner (1964)'s net-radiation index. This is the common simplification.
    """
    if elev_deg <= 0.0:
        return "night"
    if elev_deg > 60.0:
        cat = 3          # strong
    elif elev_deg > 35.0:
        cat = 2          # medium
    else:
        cat = 1          # slight
    if cloud_frac >= 0.875:
        cat -= 2
    elif cloud_frac >= 0.5:
        cat -= 1
    return {3: "strong", 2: "medium", 1: "slight"}.get(max(cat, 1), "slight")


def pasquill_class(u_ms, insol, cloud_frac):
    """Table 2, with the two problem cells handled explicitly. Returns (class, flag)."""
    if insol == "night":
        night_cloudy = cloud_frac >= 0.5
        if u_ms < 2.0:
            return ("F", "row<2 night is BLANK in the source; standard versions give F")
        if u_ms < 3.0:
            return ("E", None)
        if u_ms < 5.0:
            return ("D" if night_cloudy else "E", None)
        return ("D", None)
    if u_ms < 2.0:
        return ({"strong": "A", "medium": "A-B", "slight": "B"}[insol], None)
    if u_ms < 3.0:
        return ({"strong": "A-B", "medium": "B", "slight": "C"}[insol], None)
    if u_ms < 5.0:
        return ({"strong": "B", "medium": "B-C", "slight": "C"}[insol], None)
    if u_ms < 6.0:
        return ({"strong": "C", "medium": "C-D", "slight": "D"}[insol], None)
    if insol == "slight":
        return ("D", "source cell '>6 / Slight' reads C, which is not physical; using D")
    return ({"strong": "C", "medium": "D"}[insol], None)


def sigma_y(cls, x):
    """sigma_y for a class label, averaging the two members of a hyphenated class."""
    parts = cls.split("-")
    vals = []
    for p in parts:
        a, b = PG[p]
        vals.append(a * x ** b)
    return statistics.fmean(vals)


def main():
    banner("N-33  What diffusivity does REAL WEATHER imply, hour by hour?   [FREE]")
    if not os.path.exists(CSV):
        print("   ASOS file missing: %s" % CSV); return 2

    # ---- sanity-check the solar algorithm before trusting it
    e = solar_elevation(LAT, LON, 2026, 6, 21, 13, 7, -4)      # ~solar noon EDT on the solstice
    expect = 90.0 - LAT + 23.44
    print("   solar algorithm check: elevation at 21 Jun solar noon = %.1f deg, expected ~%.1f"
          % (e, expect))
    if abs(e - expect) > 3.0:
        print("   *** solar elevation is off by more than 3 deg -- ABORT, fix it before using it")
        return 2
    print("   agrees within %.1f deg -- proceeding" % abs(e - expect))

    rows, flags = [], Counter()
    for line in open(CSV, encoding="utf-8").read().splitlines()[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 7:
            continue
        try:
            date, tm = p[1].split(" ")
            y, mo, d = (int(v) for v in date.split("-"))
            hh, mm = (int(v) for v in tm.split(":")[:2])
            drct = float(p[2]); sknt = float(p[3])
        except Exception:
            continue
        u = sknt * 0.514444
        c1 = CLOUD.get(p[4].upper(), None)
        c2 = CLOUD.get(p[5].upper(), None)
        cloud = max([v for v in (c1, c2) if v is not None], default=None)
        if cloud is None:
            flags["no usable sky condition"] += 1
            continue
        elev = solar_elevation(LAT, LON, y, mo, d, hh, mm, -4)
        insol = insolation_category(elev, cloud)
        cls, flag = pasquill_class(u, insol, cloud)
        if flag:
            flags[flag] += 1
        sy = sigma_y(cls, SEPARATION_M)
        D = u * sy * sy / (2.0 * SEPARATION_M) if u > 0.05 else float("nan")
        rows.append({"when": p[1], "u_ms": u, "dir": drct, "cloud": cloud, "elev": elev,
                     "insol": insol, "cls": cls, "sigma_y": sy, "D": D})

    good = [r for r in rows if math.isfinite(r["D"])]
    print("\n   %d hourly observations classified (%d usable D)" % (len(rows), len(good)))
    if flags:
        print("\n   FLAGGED CELLS -- stated, not hidden:")
        for k, v in flags.items():
            print("      %5d hours : %s" % (v, k))

    cc = Counter(r["cls"] for r in good)
    print("\n   STABILITY CLASS DISTRIBUTION across real weather")
    print("      %-8s %8s %8s %14s %12s" % ("class", "hours", "share", "sigma_y(230m)", "implied D"))
    for cls in sorted(cc, key=lambda k: -cc[k]):
        sel = [r for r in good if r["cls"] == cls]
        print("      %-8s %8d %7.1f%% %14.2f %12.2f"
              % (cls, cc[cls], 100 * cc[cls] / len(good), sel[0]["sigma_y"],
                 statistics.fmean(r["D"] for r in sel)))

    Ds = np.array([r["D"] for r in good])
    qs = {q: float(np.percentile(Ds, q)) for q in (5, 25, 50, 75, 95)}
    print("\n   IMPLIED DIFFUSIVITY, distribution over %d real hours" % len(good))
    print("      min %.2f   p5 %.2f   p25 %.2f   MEDIAN %.2f   p75 %.2f   p95 %.2f   max %.2f m2/s"
          % (Ds.min(), qs[5], qs[25], qs[50], qs[75], qs[95], Ds.max()))
    print("      the model has been using a fixed D = %.1f m2/s" % CURRENT_D)
    within = float(np.mean((Ds > CURRENT_D / 2) & (Ds < CURRENT_D * 2)))
    print("      fraction of hours within a factor of 2 of that: %.1f %%" % (100 * within))
    print("      p95/p5 spread: %.1f x" % (qs[95] / max(qs[5], 1e-9)))

    # what matters operationally is the HOT hours, when the agent actually decides
    hot = [r for r in good if r["elev"] > 20.0 and 11 <= int(r["when"][11:13]) <= 18]
    if hot:
        Dh = np.array([r["D"] for r in hot])
        print("\n   RESTRICTED TO DECISION HOURS (11:00-18:00 local, sun above 20 deg): %d hours"
              % len(hot))
        print("      min %.2f   p25 %.2f   MEDIAN %.2f   p75 %.2f   max %.2f m2/s"
              % (Dh.min(), np.percentile(Dh, 25), np.percentile(Dh, 50),
                 np.percentile(Dh, 75), Dh.max()))
        ch = Counter(r["cls"] for r in hot)
        print("      classes: %s" % ", ".join("%s %.0f%%" % (k, 100 * v / len(hot))
                                              for k, v in ch.most_common()))

    med = qs[50]
    ratio = max(med, CURRENT_D) / min(med, CURRENT_D)
    ok = ratio < 2.0
    print("\n   RESULT")
    print("      median implied D over real weather : %.2f m2/s" % med)
    print("      the fixed value in the model       : %.2f m2/s" % CURRENT_D)
    print("      ratio                              : %.2f x" % ratio)
    print()
    verdict(ok,
            "PASS - the fixed D = %.1f sits within a factor of %.2f of what real weather implies "
            "(median %.2f m2/s over %d hours). So the constant was defensible as a central value, and "
            "the honest version is to compute it per hour: wind speed and sky condition give the "
            "Pasquill class, the published curve gives sigma_y, and sigma_y gives D. Nothing invented."
            % (CURRENT_D, ratio, med, len(good)),
            "FAIL - real weather implies a median D of %.2f m2/s against the %.1f the model uses, a "
            "factor of %.2f. A single fixed diffusivity is not defensible; compute it per hour from "
            "wind speed and sky condition." % (med, CURRENT_D, ratio))

    save_result("n33_stability.json", {
        "question": "what diffusivity does real weather imply, hour by hour?",
        "wind_source": "KIAD ASOS via Iowa State Environmental Mesonet, America/New_York",
        "separation_m": SEPARATION_M, "current_fixed_D": CURRENT_D,
        "n_hours": len(good), "class_distribution": dict(cc),
        "D_quantiles": qs, "D_min": float(Ds.min()), "D_max": float(Ds.max()),
        "D_median": med, "ratio_to_fixed": ratio,
        "frac_within_factor_2": within,
        "flagged_source_cells": dict(flags),
        "insolation_method": "OURS - solar elevation banded then reduced for cloud; the rigorous "
                             "route is Turner (1964) net-radiation index",
        "decision_hours": ({"n": len(hot),
                            "D_median": float(np.median([r["D"] for r in hot])),
                            "classes": dict(Counter(r["cls"] for r in hot))} if hot else None),
        "pass": ok})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
