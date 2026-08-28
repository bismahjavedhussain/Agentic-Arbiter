# -*- coding: utf-8 -*-
"""Atmospheric stability, and the 2 m -> intake-height offset as a LEARNED quantity.

FREE, keyless. Zero API calls. Reuses the sourced Pasquill classifier from earlier work.

=============================================================================================
THE PROBLEM THIS SOLVES
=============================================================================================
FortyGuard measures air temperature at 2 m above ground. If a site's cooling equipment sits on the
roof, the air it breathes is 10-20 m up, and near-surface air temperature is NOT constant with height:
superadiabatic in strong sun (2 m warmer than roof), inversion on clear calm nights (2 m COLDER).

The purely adiabatic part is negligible -- the dry adiabatic lapse rate is 9.8 C/km, so 2 m -> 15 m is
about 0.13 C. The stability-driven part is not negligible, and it flips sign between day and night.

=============================================================================================
WHY THERE IS NO LOOKUP TABLE HERE, AND WHY THAT IS THE RIGHT CHOICE
=============================================================================================
The obvious approach is a published vertical-temperature-gradient table indexed by stability class.
We do not use one, for a reason:

  * ASHRAE Handbook ch. 46 -- the one primary source on disk that covers intake/exhaust design -- was
    searched in full: ZERO hits for "lapse rate", "temperature gradient", "stability class",
    "potential temperature", "stable", "unstable" or "neutral". It is about stack height and dilution,
    not atmospheric profiles.
  * Quoting a gradient table from memory would be exactly the kind of unsourced constant this project
    retracts claims over.

SO THE OFFSET IS NOT ESTIMATED. IT IS LEARNED, INDEXED BY STABILITY CLASS.

    offset[class]  starts at 0.0 C with an explicit "unknown" flag
    each time the customer's intake sensor reports, the residual (measured - predicted) is attributed
    to that hour's stability class and the class's offset and spread are updated
    the conformal bound is computed PER CLASS, so its width reflects how well that class is known

This is strictly better than a table:

  1. No unverifiable constant enters the physics.
  2. It discovers the site's ARCHITECTURE by itself. Ground-level equipment yard -> the learned offsets
     converge toward zero. Rooftop equipment -> they converge to whatever the real profile gives. The
     agent does not need to be told which, and it can REPORT which it found.
  3. It is a genuine learning element with structure, not a scalar being nudged.
  4. Stratifying the bound by class is the textbook fix for exactly the failure mode a single constant
     calibration has: an offset that varies diurnally cannot be absorbed by one number, and
     free-cooling hours are concentrated at night.

=============================================================================================
WHY THIS MAKES FORTYGUARD LOAD-BEARING RATHER THAN INCIDENTAL
=============================================================================================
The index is the stability class, and stability comes from SOLAR RADIATION, cloud cover and wind.

  * /v1/env_params returns solar_irradiance (clear-sky GHI/DNI/DHI) and cloud_cover_octas -- both
    confirmed present in a real saved response.
  * The verified finding about what data centres actually monitor on site is that they measure outside
    air temperature, dew point and humidity -- and that "wind speed and wind direction are entirely
    absent. So is solar radiation."

So the customer's own rooftop station CANNOT supply the index. FortyGuard can. The correction for
FortyGuard's measurement height is computed from FortyGuard's own data.

=============================================================================================
HONEST STATUS BEFORE ANY SENSOR DATA EXISTS
=============================================================================================
With no intake sensor connected, every offset is 0.0 and flagged UNKNOWN, and the per-class bound is
wide because the class's residual spread is unmeasured. The agent's correct behaviour then is to SAY
it does not know the offset, not to pretend to. That is demo case 8.
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

HOURLY = os.path.join(ROOT, "data", "weather", "kiad_hourly_2021_2025.json")
OUT = os.path.join(ROOT, "data", "weather", "stability_profile.json")

SITE_LAT, SITE_LON = 39.0172, -77.4391      # the selected Ashburn pair
DRY_ADIABATIC_K_PER_M = 0.0098              # 9.8 C/km -- a physical constant, not a fitted value
KT_TO_MS = 0.514444

# Free-cooling changeover candidates, for the class breakdown. ASHRAE recommended upper is 27 C.
CHANGEOVER_C = [18.0, 21.0, 24.0, 27.0]

CLASSES = ["A", "A-B", "B", "B-C", "C", "C-D", "D", "E", "F"]


# ----------------------------------------------------------------- solar geometry
def solar_elevation(lat, lon, when_utc_hours, day_of_year):
    """Solar elevation in degrees. Standard NOAA-style approximation."""
    dec = math.radians(23.44) * math.sin(math.radians(360.0 / 365.0 * (day_of_year - 81)))
    ha = math.radians(15.0 * (when_utc_hours + lon / 15.0 - 12.0))
    la = math.radians(lat)
    sin_el = math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))


# ----------------------------------------------------------------- Pasquill, reused as sourced
def insolation_category(elev_deg, cloud_frac):
    """[OURS] elevation banded, then reduced for cloud -- the common simplification. The rigorous
    route is Turner (1964)'s net-radiation index. Carried over unchanged from N-33 so the two agree."""
    if elev_deg <= 0.0:
        return "night"
    if elev_deg > 60.0:
        cat = 3
    elif elev_deg > 35.0:
        cat = 2
    else:
        cat = 1
    if cloud_frac >= 0.875:
        cat -= 2
    elif cloud_frac >= 0.5:
        cat -= 1
    return {3: "strong", 2: "medium", 1: "slight"}.get(max(cat, 1), "slight")


def pasquill_class(u_ms, insol, cloud_frac):
    """Pasquill-Gifford Table 2 (p.4), with the two problem cells handled explicitly.
    Transcribed in N-33; reused verbatim so both modules classify identically."""
    if insol == "night":
        night_cloudy = cloud_frac >= 0.5
        if u_ms < 2.0:
            return "F"
        if u_ms < 3.0:
            return "E"
        if u_ms < 5.0:
            return "D" if night_cloudy else "E"
        return "D"
    if u_ms < 2.0:
        return {"strong": "A", "medium": "A-B", "slight": "B"}[insol]
    if u_ms < 3.0:
        return {"strong": "A-B", "medium": "B", "slight": "C"}[insol]
    if u_ms < 5.0:
        return {"strong": "B", "medium": "B-C", "slight": "C"}[insol]
    if u_ms < 6.0:
        return {"strong": "C", "medium": "C-D", "slight": "D"}[insol]
    if insol == "slight":
        return "D"
    return {"strong": "C", "medium": "D"}[insol]


# ----------------------------------------------------------------- the learned offset store
class HeightOffsetModel:
    """offset[class] -> the 2 m to intake-height correction, LEARNED from sensor residuals.

    Nothing is assumed. Every class starts UNKNOWN with a zero offset, and the agent is expected to
    report that rather than pretend. `adiabatic_floor` is the one part we DO know: the dry adiabatic
    lapse rate is a physical constant, so a correction can never be smaller in magnitude than that.
    """

    def __init__(self, intake_height_m=None):
        self.intake_height_m = intake_height_m          # None = unknown, which is the honest default
        self.obs = {c: [] for c in CLASSES}

    def adiabatic_floor(self):
        """The part of the offset that is known from physics alone. Returns None if height is unknown."""
        if self.intake_height_m is None:
            return None
        return -DRY_ADIABATIC_K_PER_M * (self.intake_height_m - 2.0)

    def observe(self, cls, measured_intake_c, predicted_intake_c):
        if cls in self.obs:
            self.obs[cls].append(measured_intake_c - predicted_intake_c)

    def offset(self, cls):
        """(value_c, spread_c, n, known). known is False until the class has real observations."""
        v = self.obs.get(cls, [])
        if len(v) < 2:
            return 0.0, None, len(v), False
        return statistics.fmean(v), statistics.stdev(v), len(v), True

    def report(self):
        rows = {}
        for c in CLASSES:
            val, sd, n, known = self.offset(c)
            rows[c] = {"offset_c": round(val, 4) if known else 0.0,
                       "spread_c": round(sd, 4) if sd is not None else None,
                       "n_observations": n, "known": known}
        return {"intake_height_m": self.intake_height_m,
                "adiabatic_floor_c": self.adiabatic_floor(),
                "per_class": rows,
                "status": "NO SENSOR DATA YET -- every offset is UNKNOWN and the agent must say so"
                          if all(not r["known"] for r in rows.values()) else "partially learned"}


# ----------------------------------------------------------------- measurement over real weather
def main():
    print("=" * 78)
    print("AGENTIC-ARBITER  stability classes over 5 real years, and where free cooling lives")
    print("=" * 78)

    d = json.load(open(HOURLY, encoding="utf-8"))
    hours = d["hours"]
    print("\n   %d hourly records, KIAD 2021-2025" % len(hours))
    print("   classifying each hour by Pasquill class from solar elevation, cloud and wind speed")
    print("   NOTE: cloud fraction is not in this fixture, so sky cover is unavailable and every")
    print("   hour is treated as CLEAR. That biases daytime classes UNSTABLE and night-time STABLE,")
    print("   i.e. toward the extremes. Recorded, not hidden -- FortyGuard's cloud_cover_octas and")
    print("   solar_irradiance replace this guess once the key is live on 2026-08-18.")

    counts = {c: 0 for c in CLASSES}
    by_class_temp = {c: [] for c in CLASSES}
    night_hours = 0
    usable = 0
    for k, v in hours.items():
        t, dwp, drct, sknt = v
        if t is None or sknt is None:
            continue
        date, hh = k.split(" ")
        y, m, dd = (int(x) for x in date.split("-"))
        doy = (int(__import__("datetime").date(y, m, dd).strftime("%j")))
        # the fixture is site-local (America/New_York); convert to UTC hours for solar geometry
        utc_h = int(hh) + 5.0
        elev = solar_elevation(SITE_LAT, SITE_LON, utc_h, doy)
        cloud = 0.0                                    # unavailable in this fixture -- see note above
        insol = insolation_category(elev, cloud)
        cls = pasquill_class(float(sknt) * KT_TO_MS, insol, cloud)
        counts[cls] += 1
        by_class_temp[cls].append(t)
        if insol == "night":
            night_hours += 1
        usable += 1

    print("\n   %d hours classified (%.1f %% of the record); %d are night hours (%.1f %%)"
          % (usable, 100.0 * usable / len(hours), night_hours, 100.0 * night_hours / usable))
    print("\n   %-6s %9s %8s   %s" % ("class", "hours", "share", "median dry-bulb C"))
    for c in CLASSES:
        if counts[c] == 0:
            continue
        print("   %-6s %9d %7.1f %%   %.1f"
              % (c, counts[c], 100.0 * counts[c] / usable, statistics.median(by_class_temp[c])))

    print("\n   WHERE FREE-COOLING HOURS ACTUALLY LIVE, by stability class")
    print("   (this decides how much the height offset matters, because the offset is class-dependent)")
    fc = {}
    for L in CHANGEOVER_C:
        row = {}
        tot = 0
        for c in CLASSES:
            k = sum(1 for t in by_class_temp[c] if t < L)
            row[c] = k
            tot += k
        fc["limit_%.0f" % L] = {"total_hours": tot, "per_class": row,
                                "per_class_share": {c: (row[c] / tot if tot else 0.0) for c in CLASSES}}
        stable = row.get("E", 0) + row.get("F", 0)
        print("      limit %2.0f C : %6d free-cooling hours, of which %6d (%4.1f %%) are in STABLE "
              "classes E/F" % (L, tot, stable, 100.0 * stable / tot if tot else 0.0))

    model = HeightOffsetModel(intake_height_m=None)
    rep = model.report()
    print("\n   THE HEIGHT-OFFSET MODEL, as it stands today")
    print("      intake height        : UNKNOWN (not in OSM, not surveyed)")
    print("      adiabatic floor      : cannot be computed without a height")
    print("      learned offsets      : all UNKNOWN, n=0 -- no intake sensor is connected")
    print("      the agent's correct behaviour is to REPORT this, not to assume zero silently")

    json.dump({
        "measures": "distribution of Pasquill stability classes over 5 real years at the site, and how "
                    "free-cooling hours distribute across those classes",
        "why": "the 2 m -> intake-height offset is class-dependent, so which classes carry the "
               "free-cooling hours determines how much the offset matters",
        "does_not_measure": "the offset itself. That is LEARNED from intake-sensor residuals; no "
                            "published gradient table is used, because none could be sourced from any "
                            "primary document available (ASHRAE ch.46 searched: zero hits)",
        "caveat_cloud": "cloud fraction is absent from this fixture so every hour is treated as CLEAR, "
                        "biasing day classes unstable and night classes stable. FortyGuard's "
                        "cloud_cover_octas and solar_irradiance replace this once the key is live.",
        "n_hours_classified": usable, "night_hours": night_hours,
        "class_counts": counts,
        "class_median_drybulb_c": {c: (round(statistics.median(by_class_temp[c]), 2)
                                       if by_class_temp[c] else None) for c in CLASSES},
        "free_cooling_by_class": fc,
        "height_offset_model": rep,
        "adiabatic_lapse_k_per_m": DRY_ADIABATIC_K_PER_M,
    }, open(OUT, "w"), indent=1, allow_nan=False)
    print("\n   written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
