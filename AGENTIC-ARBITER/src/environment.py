# -*- coding: utf-8 -*-
"""ENVIRONMENTAL GATES -- the other two things a real economizer checks before opening a damper.

Run `python environment.py` for the self-test, which validates the psychrometrics against an
independent ASHRAE-formulation reference implementation and audits FortyGuard's env_params fields.

--------------------------------------------------------------------------------------------
WHY: DRY-BULB TEMPERATURE ALONE IS NOT AN ECONOMIZER CONTROL
--------------------------------------------------------------------------------------------
The agent's first version gated free cooling on temperature only. Real equipment does not.

  1. HUMIDITY. Cool but damp outside air condenses on cold metal inside the hall. ENERGY STAR's
     air-side economizer guidance is explicit that products check temperature AND humidity, and
     Honeywell's JADE economizer controller states its differentials as *"A 2 deg F and a
     1 Btu/lb differential"* -- Btu/lb is an ENTHALPY unit, not a temperature.
     N-56 recorded this as a gap in its OWN limitations section: "No humidity or enthalpy gate;
     real economizers also limit on wet-bulb, which would reduce hours for BOTH policies."

  2. CONTAMINATION. This is the documented reason operators avoid free cooling at all. LBNL put
     particle counters in EIGHT real data centres and found *"economizer use caused sharp
     increases in particle concentrations when the economizer vents were open"*, dropping back
     when they closed, with annual averages still meeting ASHRAE standards. The study's stated
     motivation is that there was *"reluctance from many data center owners to use this common
     cooling technique due to fear of introducing pollutants and potential loss of humidity
     control"*.
     -- Shehabi, Tschudi & Gadgil, "Data Center Economizer Contamination and Humidity Study",
        LBNL, 6 March 2007, OSTI 971864.  https://www.osti.gov/biblio/971864

So the decision is THREE gates, not one: dry-bulb, wet-bulb/enthalpy, and contamination. All
three inputs are available from FortyGuard -- `/v1/heatmap` for the field and `/v1/env_params`
for humidity, wet-bulb and six air-quality indices.

--------------------------------------------------------------------------------------------
WHERE THE DATA COMES FROM, AND THE HONEST DIVISION OF LABOUR
--------------------------------------------------------------------------------------------
* FIVE-YEAR BACKTEST (43,763 h). Uses KIAD's own dry-bulb AND DEW POINT, both present for
  100.0 % of hours. Dew point -> relative humidity -> wet-bulb -> enthalpy, all real, hourly.
  No FortyGuard call is needed or made for this.
* FORTYGUARD `/v1/env_params`. Returns HOURLY ARRAYS -- 24 values per field per day, not a
  single reading. 29 saved responses are already on disk and already paid for, giving the
  air-quality and solar/cloud series that the KIAD record does not contain at all.
* AIR-QUALITY LIMIT. FortyGuard returns air quality as `:idx` INDICES with no documented units
  or scale, so no primary numeric limit can be sourced for them. The limit is therefore a SWEPT
  SCENARIO PARAMETER, never a constant in this file, and FortyGuard's measured distribution is
  reported as the realistic operating range. This is the same discipline as the changeover
  temperature: if we cannot source it, we sweep it and say so.

--------------------------------------------------------------------------------------------
PSYCHROMETRICS -- and a stated limit of the closed form
--------------------------------------------------------------------------------------------
Wet-bulb is computed two independent ways and they are required to agree:
  * Stull (2011), J. Applied Meteorology and Climatology 50(11):2267-2269,
    doi:10.1175/JAMC-D-11-0143.1 -- a closed form with MAE < 0.3 C. IT ASSUMES SEA-LEVEL
    PRESSURE and is valid only for RH 5-99 % and T -20 to +50 C. Hours outside that envelope
    are COUNTED AND REPORTED, never silently extrapolated.
  * PsychroLib (MIT), which implements the ASHRAE formulations by iteration and has no such
    envelope -- Meyer et al., JOSS 4(33):1137, doi:10.21105/joss.01137.
PsychroLib is the reference; Stull is kept because it is the citable closed form and because
agreement between two independent methods is evidence neither is mis-transcribed.
"""
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
ROOT = os.path.dirname(IA)
FIXTURES = os.path.join(ROOT, "testing", "results", "fixtures")

sys.path.insert(0, HERE)
from stability import insolation_category, pasquill_class, solar_elevation   # noqa: E402

SITE_ELEVATION_M = 65.0        # MEASURED: FortyGuard env_params reports elevation 65.0 m
STULL_RH_RANGE = (5.0, 99.0)   # Stull (2011) stated validity envelope
STULL_T_RANGE = (-20.0, 50.0)

try:
    import psychrolib as _psy
    _psy.SetUnitSystem(_psy.SI)
    HAVE_PSYCHROLIB = True
except Exception:
    HAVE_PSYCHROLIB = False


# ============================================================================
# Psychrometrics
# ============================================================================
def station_pressure_pa(elevation_m=SITE_ELEVATION_M):
    """ISA barometric formula. Our KIAD record carries no pressure field, so pressure is derived
    from elevation and treated as constant -- an ASSUMPTION, and the reason Stull's sea-level
    caveat is reported rather than ignored."""
    return 101325.0 * (1.0 - 2.25577e-5 * elevation_m) ** 5.25588


def sat_vapour_pressure_hpa(t_c):
    """Magnus-Tetens saturation vapour pressure over water, hPa. Standard meteorological form."""
    t = np.asarray(t_c, dtype=float)
    return 6.112 * np.exp((17.67 * t) / (t + 243.5))


def rh_from_dewpoint(t_c, td_c):
    """Relative humidity (%) from dry-bulb and dew point. Clipped to (0, 100]."""
    rh = 100.0 * sat_vapour_pressure_hpa(td_c) / sat_vapour_pressure_hpa(t_c)
    return np.clip(rh, 0.0, 100.0)


def wet_bulb_stull(t_c, rh_pct):
    """Stull (2011) closed form. Returns (wet_bulb_C, in_validity_envelope_mask)."""
    t = np.asarray(t_c, dtype=float)
    rh = np.asarray(rh_pct, dtype=float)
    tw = (t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
          + np.arctan(t + rh)
          - np.arctan(rh - 1.676331)
          + 0.00391838 * np.power(np.maximum(rh, 0.0), 1.5) * np.arctan(0.023101 * rh)
          - 4.686035)
    ok = ((rh >= STULL_RH_RANGE[0]) & (rh <= STULL_RH_RANGE[1])
          & (t >= STULL_T_RANGE[0]) & (t <= STULL_T_RANGE[1]))
    return tw, ok


def wet_bulb_reference(t_c, rh_pct, pressure_pa=None):
    """PsychroLib's ASHRAE-formulation wet-bulb. NaN where unavailable."""
    if not HAVE_PSYCHROLIB:
        return np.full(np.shape(t_c), np.nan)
    p = pressure_pa if pressure_pa is not None else station_pressure_pa()
    t = np.atleast_1d(np.asarray(t_c, dtype=float))
    rh = np.atleast_1d(np.asarray(rh_pct, dtype=float))
    out = np.full(len(t), np.nan)
    for i in range(len(t)):
        try:
            out[i] = _psy.GetTWetBulbFromRelHum(float(t[i]),
                                                float(np.clip(rh[i], 0.001, 100.0) / 100.0), p)
        except Exception:
            pass
    return out


def enthalpy_kj_kg(t_c, rh_pct, pressure_pa=None):
    """Moist-air specific enthalpy, kJ per kg of dry air -- the quantity JADE's 1 Btu/lb
    differential is stated in. Uses PsychroLib when present, else the standard textbook form."""
    p = pressure_pa if pressure_pa is not None else station_pressure_pa()
    t = np.atleast_1d(np.asarray(t_c, dtype=float))
    rh = np.atleast_1d(np.asarray(rh_pct, dtype=float))
    if HAVE_PSYCHROLIB:
        out = np.full(len(t), np.nan)
        for i in range(len(t)):
            try:
                w = _psy.GetHumRatioFromRelHum(float(t[i]),
                                               float(np.clip(rh[i], 0.001, 100.0) / 100.0), p)
                out[i] = _psy.GetMoistAirEnthalpy(float(t[i]), w) / 1000.0
            except Exception:
                pass
        return out
    e = sat_vapour_pressure_hpa(t) * np.clip(rh, 0.0, 100.0) / 100.0
    w = 0.62198 * e / ((p / 100.0) - e)
    return 1.006 * t + w * (2501.0 + 1.86 * t)


# ============================================================================
# FortyGuard /v1/env_params -- hourly arrays, 15 fields
# ============================================================================
AQ_FIELDS = ["air_quality:idx", "air_quality_pm2p5:idx", "air_quality_pm10:idx",
             "air_quality_no2:idx", "air_quality_o3:idx", "air_quality_so2:idx"]
DEFECTIVE_FIELDS = {
    "heat_index_celsius": "computed from the CALLER'S temperature input, not conditions "
                          "at the location (our defect 1.1). Never use.",
    "temperature": "echoes the caller's own input with no indication it is an echo "
                   "(our defect 1.7). env_params returns no dry-bulb at all.",
}


def load_env_params(pattern="*.json"):
    """Every saved env_params response, as hourly arrays. No API call is made."""
    out = []
    for f in sorted(glob.glob(os.path.join(FIXTURES, pattern))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if not (isinstance(d, dict) and d.get("locations")):
            continue
        loc = d["locations"][0]
        P = loc.get("parameters") or {}
        if not P:
            continue
        out.append({"file": os.path.basename(f), "lat": loc.get("lat"), "lon": loc.get("lon"),
                    "elevation_m": loc.get("elevation"),
                    "solar_clear_sky": (loc.get("solar_irradiance") or {}).get("clear_sky"),
                    "n_hours": max((len(v) for v in P.values() if isinstance(v, list)),
                                   default=0),
                    "parameters": P})
    return out


def cloud_fraction(raw_cloud_cover):
    """FortyGuard's `cloud_cover_octas` -> a 0-1 fraction, WITH THE UNITS BUG CORRECTED.

    OUR DEFECT 1.3, NOW REFINED AND THIS MATTERS. The field is named `octas` (a 0-8 scale) but
    every one of 236 saved values is an integer in 0-100, with 73 distinct values above 8. It is
    a PERCENTAGE mislabelled as octas -- a naming/units defect, not corrupt data. That upgrades
    the field from unusable to usable, which is why it is worth reporting to FortyGuard
    precisely rather than as "out of range".

    Treating a percentage as octas would divide cloud cover by 12.5 and classify a fully
    overcast sky as almost clear, which pushes the stability class the wrong way.
    """
    v = np.asarray(raw_cloud_cover, dtype=float)
    return np.clip(v / 100.0, 0.0, 1.0)


def stability_from_fortyguard(lat, lon, day_of_year, hour_utc, wind_ms, raw_cloud_cover):
    """Pasquill stability class using FortyGuard cloud cover instead of assuming clear sky.

    THE ASSUMPTION THIS REMOVES. Our five-year ASOS fixture carries no cloud field, so all
    43,708 classified hours were treated as CLEAR. Clear skies mean stronger daytime insolation
    and more stable nights, so the assumption biased the classification at both ends.
    `pasquill_class` and `insolation_category` are IMPORTED from stability.py rather than
    reimplemented, so the two modules cannot drift apart (gotcha #12).
    """
    cf = cloud_fraction(raw_cloud_cover)
    elev = solar_elevation(lat, lon, hour_utc, day_of_year)
    insol = insolation_category(elev, float(np.mean(cf)) if np.ndim(cf) else float(cf))
    return pasquill_class(wind_ms, insol, float(np.mean(cf)) if np.ndim(cf) else float(cf))


def air_quality_series(env):
    """The six air-quality index series from one env_params response, plus an integrity audit."""
    P = env["parameters"]
    s = {k: np.array([np.nan if x is None else float(x) for x in P[k]], dtype=float)
         for k in AQ_FIELDS if isinstance(P.get(k), list)}
    audit = {}
    if "air_quality:idx" in s and "air_quality_pm2p5:idx" in s:
        a, b = s["air_quality:idx"], s["air_quality_pm2p5:idx"]
        n = min(len(a), len(b))
        if n:
            audit["overall_equals_pm25"] = bool(np.allclose(a[:n], b[:n], equal_nan=True))
            audit["max_abs_diff"] = float(np.nanmax(np.abs(a[:n] - b[:n]))) if n else None
    return s, audit


def contamination_gate(aq_series, limit_idx, field="air_quality_pm2p5:idx"):
    """True where outside air is clean enough to admit, at a SWEPT index limit.

    `limit_idx` is a scenario parameter, never a constant here: FortyGuard's `:idx` values carry
    no documented units or scale, so no primary source can fix a numeric limit. The physical
    justification for gating at all is LBNL's measurement that opening economizer vents raises
    indoor particle concentrations sharply.
    """
    v = aq_series.get(field)
    if v is None:
        return None
    return v <= limit_idx


# ============================================================================
# SELF-TEST
# ============================================================================
def _selftest():
    ok_all = True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        print("   [%s] %-56s %s" % ("PASS" if cond else "FAIL", name, detail))

    print("=" * 78)
    print("ENVIRONMENT SELF-TEST")
    print("=" * 78)
    print("   psychrolib reference available: %s" % HAVE_PSYCHROLIB)
    print("   station pressure at %.0f m: %.0f Pa" % (SITE_ELEVATION_M, station_pressure_pa()))

    # ---- 1. psychrometrics on the REAL five-year record
    print("\n1. Wet-bulb on all 43,763 real KIAD hours, two independent methods")
    hp = os.path.join(IA, "data", "weather", "kiad_hourly_2021_2025.json")
    d = json.load(open(hp, encoding="utf-8"))
    f = d["meta"]["fields"]
    it, idw = f.index("tmpc"), f.index("dwpc")
    keys = sorted(d["hours"])
    T = np.array([d["hours"][k][it] for k in keys], dtype=float)
    Td = np.array([d["hours"][k][idw] for k in keys], dtype=float)
    check("dry-bulb and dew point present for every hour",
          np.isfinite(T).all() and np.isfinite(Td).all(), "n=%s" % format(len(T), ","))

    RH = rh_from_dewpoint(T, Td)
    check("relative humidity lands in (0, 100]", (RH > 0).all() and (RH <= 100.0).all(),
          "min %.1f max %.1f mean %.1f %%" % (RH.min(), RH.max(), RH.mean()))

    Tw, in_env = wet_bulb_stull(T, RH)
    print("      Stull validity envelope: %s of %s hours inside (%.2f %%)"
          % (format(int(in_env.sum()), ","), format(len(T), ","), 100.0 * in_env.mean()))
    print("      outside because RH<5%%: %d   RH>99%%: %d   T<-20C: %d   T>50C: %d"
          % (int((RH < 5).sum()), int((RH > 99).sum()),
             int((T < -20).sum()), int((T > 50).sum())))

    # physical bounds must hold: dew point <= wet bulb <= dry bulb
    tol = 0.35                                   # Stull's own stated MAE is < 0.3 C
    bound_ok = (Tw <= T + tol) & (Tw >= Td - tol)
    check("dew point <= wet bulb <= dry bulb (within Stull's stated MAE)",
          bound_ok.mean() > 0.999, "%.4f of hours" % bound_ok.mean())

    if HAVE_PSYCHROLIB:
        idx = np.linspace(0, len(T) - 1, 4000).astype(int)
        Tw_ref = wet_bulb_reference(T[idx], RH[idx])
        m = np.isfinite(Tw_ref) & in_env[idx]
        diff = Tw[idx][m] - Tw_ref[m]
        print("      Stull vs PsychroLib on %d sampled in-envelope hours:" % int(m.sum()))
        print("         mean %+.4f C   MAE %.4f C   max|diff| %.4f C"
              % (diff.mean(), np.abs(diff).mean(), np.abs(diff).max()))
        check("agrees with the ASHRAE reference within Stull's published MAE",
              np.abs(diff).mean() < 0.30, "MAE %.4f C" % np.abs(diff).mean())
        Tw_all = wet_bulb_reference(T[idx], RH[idx])
        check("reference method returns a value for every sampled hour",
              np.isfinite(Tw_all).all(), "n=%d" % len(idx))

    E = enthalpy_kj_kg(T[:3000], RH[:3000])
    check("enthalpy is finite and monotone-ish in temperature",
          np.isfinite(E).all() and np.corrcoef(E, T[:3000])[0, 1] > 0.9,
          "range %.1f to %.1f kJ/kg, corr with T %.3f"
          % (E.min(), E.max(), np.corrcoef(E, T[:3000])[0, 1]))

    # THE OPERATIONAL POINT: how often does a wet-bulb gate bind when dry-bulb says yes?
    print("\n2. Does the humidity gate actually change decisions? (the reason to add it)")
    for limit in (18.0, 21.0, 24.0, 27.0):
        dry_ok = T <= limit
        # a wet-bulb limit cannot simply equal the dry-bulb limit; report the CO-INCIDENCE
        wb_ok = Tw <= limit - 3.0        # illustrative offset, swept in the agent, not fixed here
        blocked = dry_ok & ~wb_ok
        print("      limit %.0f C: dry-bulb allows %5.1f %% of hours; of those %5.2f %% are "
              "blocked by a wet-bulb gate 3 C tighter"
              % (limit, 100.0 * dry_ok.mean(),
                 100.0 * (blocked.sum() / max(dry_ok.sum(), 1))))
    check("the humidity gate is not vacuous -- it blocks some dry-bulb-allowed hours",
          ((T <= 24.0) & ~(Tw <= 21.0)).sum() > 0,
          "%s hours at the 24/21 pair" % format(int(((T <= 24.0) & ~(Tw <= 21.0)).sum()), ","))

    # ---- 3. FortyGuard env_params audit
    print("\n3. FortyGuard /v1/env_params -- what is on disk, already paid for")
    envs = load_env_params()
    hourly = [e for e in envs if e["n_hours"] >= 24]
    total_values = sum(sum(len(v) for v in e["parameters"].values() if isinstance(v, list))
                       for e in envs)
    print("      %d saved responses, %d of them full 24-hour series" % (len(envs), len(hourly)))
    print("      %s individual hourly environmental values on disk" % format(total_values, ","))
    check("env_params returns HOURLY ARRAYS, not single readings", len(hourly) > 0,
          "%d responses x 24 h" % len(hourly))

    fields = sorted({k for e in envs for k in e["parameters"]})
    print("      fields returned (%d): %s" % (len(fields), ", ".join(fields)))
    check("all six air-quality indices are present", all(k in fields for k in AQ_FIELDS),
          "%d of 6" % sum(1 for k in AQ_FIELDS if k in fields))
    check("wet-bulb and relative humidity are both present",
          "wet_bulb_temperature_celsius" in fields and "relative_humidity_percent" in fields)

    # the cloud-cover units defect, measured
    cc = np.concatenate([np.array([x for x in e["parameters"]["cloud_cover_octas"]
                                   if x is not None], dtype=float)
                         for e in envs if isinstance(e["parameters"].get("cloud_cover_octas"),
                                                     list)])
    print("\n      cloud_cover_octas: n=%d  min %.1f  max %.1f  all integers: %s"
          % (len(cc), cc.min(), cc.max(), bool((cc == np.round(cc)).all())))
    print("         fraction <= 8 (valid octas): %.3f    fraction <= 100 (valid %%): %.3f"
          % (np.mean(cc <= 8), np.mean(cc <= 100)))
    check("field is PERCENT mislabelled as octas -- usable once relabelled",
          (cc <= 100).all() and np.mean(cc <= 8) < 0.5,
          "%d distinct values above 8" % len(set(cc[cc > 8])))

    # the overall-AQI duplication finding
    dup = []
    for e in envs:
        s, audit = air_quality_series(e)
        if "overall_equals_pm25" in audit:
            dup.append(audit["overall_equals_pm25"])
    if dup:
        print("\n      NEW FINDING: `air_quality:idx` equals `air_quality_pm2p5:idx` in %d of %d "
              "responses" % (sum(dup), len(dup)))
        print("         The overall index carries no information beyond the PM2.5 sub-index.")
        check("overall AQI duplicates the PM2.5 sub-index (report to FortyGuard)",
              sum(dup) >= 1, "%d of %d responses" % (sum(dup), len(dup)))

    # air-quality operating range, for sweeping the gate
    pm = np.concatenate([air_quality_series(e)[0]["air_quality_pm2p5:idx"]
                         for e in envs
                         if "air_quality_pm2p5:idx" in air_quality_series(e)[0]])
    pm = pm[np.isfinite(pm)]
    print("\n      PM2.5 index measured range: min %.1f  p50 %.1f  p90 %.1f  max %.1f  (n=%d)"
          % (pm.min(), np.percentile(pm, 50), np.percentile(pm, 90), pm.max(), len(pm)))
    print("      -> the contamination limit is SWEPT across this measured range in the agent,")
    print("         because FortyGuard's `:idx` values carry no documented units or scale.")
    g = contamination_gate({"air_quality_pm2p5:idx": pm}, float(np.percentile(pm, 50)))
    check("contamination gate binds on roughly half the hours at the median limit",
          g is not None and 0.35 < g.mean() < 0.65, "%.3f pass" % g.mean())

    # ---- 4. stability with real cloud instead of assumed clear
    print("\n4. Pasquill class: FortyGuard cloud cover vs the assumed-clear-sky default")
    e0 = [e for e in envs if isinstance(e["parameters"].get("cloud_cover_octas"), list)
          and len(e["parameters"]["cloud_cover_octas"]) >= 24][0]
    raw = np.array([x for x in e0["parameters"]["cloud_cover_octas"][:24]], dtype=float)
    lat, lon = e0["lat"] or 39.0100, e0["lon"] or -77.4460
    changed = 0
    for h in range(24):
        a = stability_from_fortyguard(lat, lon, 220, float(h), 3.6, raw[h])
        elev = solar_elevation(lat, lon, float(h), 220)
        b = pasquill_class(3.6, insolation_category(elev, 0.0), 0.0)     # the old CLEAR default
        changed += (a != b)
    print("      %s: real cloud changes the class in %d of 24 hours" % (e0["file"], changed))
    check("using real cloud cover changes the stability classification",
          changed > 0, "%d of 24 hours" % changed)

    print("\n" + "=" * 78)
    print("SELF-TEST %s" % ("PASSED" if ok_all else "FAILED -- do not use these results"))
    print("=" * 78)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(_selftest())
