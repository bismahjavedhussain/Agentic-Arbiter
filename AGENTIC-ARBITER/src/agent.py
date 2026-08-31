# -*- coding: utf-8 -*-
"""AGENTIC-ARBITER -- THE AGENT LOOP AS ONE RUNNABLE PROGRAM.  ZERO API CALLS.

    perceive -> solve -> bound -> decide -> act -> score -> recalibrate

Run:
    python agent.py run       # everything; writes ../demo/trace.json  (the demo's only input)
    python agent.py cycle     # just the real FortyGuard forecast/outcome cycles
    python agent.py cases     # just the scheduling cases on real KIAD hours

================================================================================
WHY THIS FILE EXISTS, AND WHAT IT REPLACES
================================================================================
`testing/run_e2e.py` demonstrated the same seven stages but is NOT the agent:
  * it runs on `solver.demo_site()`, a synthetic layout, not the committed AWS geometry;
  * it hard-codes `THRESHOLD_C = 33.0`, which is exactly the "threshold in a costume" the
    project forbids shipping;
  * it needs invented cost weights (`c_excursion = 120.0`) to make its decision come out.

This file fixes all three.

  1. It runs on the COMMITTED geometry -- OSM ways 744496750 / 744496741, AWS IAD116/IAD117,
     rasterised and V1/V2/V3-verified by `build_site.py`.

  2. NOTHING that changes a decision is a constant written by a human. Every such number is a
     SCENARIO PARAMETER, sat in a list, and swept -- see PLANT_ENVELOPE below. The output holds
     the answer for EVERY combination, so the demo exposes them as controls. Apply the project's
     "point at the constant" test to this file: the constants you can point at are ALPHA (the
     statistical confidence, 0.10, and it is a definition, not a tuning knob) and the physics
     coefficients in `physics/solver.py:CALIBRATED`, which were FITTED to ~40,000 measured points
     and validated held-out. There is no changeover temperature in this source.

  3. The decision is a CONSTRAINED MAXIMISATION, not a weighted cost:
         maximise free-cooling hours
         subject to  the 90 % upper bound on intake temperature staying under the plant limit,
                     at most `switch_budget` mode changes,
                     every completed run at least `min_dwell_h` hours long.
     A constrained form needs no invented penalty weights. The safety constraint is the only
     thing standing between the agent and "free cooling all day", and the width of that
     constraint is SET BY THE AGENT'S OWN MEASURED ACCURACY -- which is the whole point:
     score better, and the bound tightens, and MORE HOURS ARE EARNED.

================================================================================
WHERE EVERY NUMBER COMES FROM.  Read this before quoting anything this file prints.
================================================================================
MEASURED, real, no simulation:
  * FortyGuard fields -- `testing/results/fixtures/n26_{f,h}_*.json`, 17,862 tiles each, one
    paid call each, already spent. Forecast leg and its elapsed outcome leg, same window, same
    AOI, same 2 m plane.
  * Day-to-day forecast residuals d = outcome - forecast, per tile, over 4 real days.
  * Site geometry -- OpenStreetMap, ODbL, rotated min-area rectangles, true facade-to-facade
    gap 60.3 m by `ring_gap()`.
  * Weather -- 43,763 real hourly KIAD ASOS records, 2021-2025 (99.9 % of five years):
    temperature, dew point, wind bearing, wind speed.
  * Recirculation rise -- solved on the committed geometry by `physics/solver.py`, validated
    against an analytic Gaussian plume to 2.9e-10 and against 67 Project Prairie Grass 1956
    field experiments; held-out RMS 0.126 K on a 0.923 K signal.
  * Refusal -- `solver.path_blocked()`, pure geometry, no PDE solve.

DERIVED from the measured, deterministically, no random draws anywhere in this file:
  * The forecast the agent sees in the scheduling cases is
        forecast[h] = truth[h] - d_offset
    where d_offset is ONE OF THE FOUR MEASURED FortyGuard day-offsets (-0.8396, -0.8115,
    +0.1520, -3.7127 C). Each is run as its own scenario. Nothing is sampled from a fitted
    distribution -- with n = 4 days that would be inventing a shape we have not measured
    (HANDOFF section 6.3: n = 4 establishes the MECHANISM, not the FREQUENCY).
  * The conformal margin for a given offset scenario is built LEAVE-ONE-OUT, from the other
    three days only. The agent is never bounded using the day it is being tested on.

HONEST LIMITS -- state these, do not let a viewer infer otherwise:
  * The bound's measured out-of-sample coverage is 65.6 % over 3 test days, against a 90 %
    nominal. It FAILED its pre-registered conditions. This file prints that failure and the
    demo shows it. HANDOFF section 7.2: 90 % -> 75 % of that shortfall is our own sample size
    (n = 3 caps coverage at n/(n+1) = 75 % arithmetically, before FortyGuard is implicated);
    75 % -> 65.6 % is FortyGuard's day-varying level offset. ~10 days recovers it.
  * Recirculation at this site is SMALL: worst bearing 255 deg gives +0.3548 C, which is BELOW
    the 0.556 C resolution of the ASOS station one would validate against. It is real physics
    and it does change decisions, but only inside a ~0.35 C band under the limit.
  * `solver.py` models buildings as TRANSPARENT to the temperature field -- N-29 V4 measured
    0.0 % of plume heat absorbed, so heat is conserved exactly (gotcha #26; the earlier
    heat-ABSORBING description was retracted 2026-08-12 and this line asserted it for eight days
    after the code had changed). Transparency is still not deflection, so on a bearing where a
    building lies on the source-to-intake path there is no answer the solver can stand behind and
    the agent REFUSES rather than returning a number.
  * No dollars and no kWh anywhere. The C-to-kWh conversion could not be sourced from a primary
    document, so the headline unit is chiller-hours avoided.
  * The scheduling cases use KIAD ASOS as the site's ambient series for BOTH the agent and the
    incumbent, so no spatial advantage accrues to either side.

================================================================================
THE INCUMBENT -- a tuned adversary, not a strawman (methodology rule 3)
================================================================================
What operators verifiably run, per HANDOFF section 5.3: ambient now, from their OWN rooftop
weather station, no wind input, no forecast. Verified by full-text search of the 27-page LBNL
thermal-guidelines document, in which "outdoor", "outside air" and "forecast" do not appear.

The incumbent here gets the SAME statistical machinery the agent gets: a 90 % one-sided
conformal bound built from ITS OWN residuals (persistence error at the same notice period,
de-biased per hour-of-day first, because raw persistence error contains the diurnal cycle --
gotcha #25, mean +8.784 C at 12 h lead). It is not handicapped. The two differences are the
two things being claimed: the agent sees a FORECAST, and the agent knows about RECIRCULATION.
"""
import json
import math
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
ROOT = os.path.dirname(IA)
GEOM = os.path.join(IA, "data", "geometry")
WEATHER = os.path.join(IA, "data", "weather")
DEMO = os.path.join(IA, "demo")
FIXTURES = os.path.join(ROOT, "testing", "results", "fixtures")
N26_MANIFEST = os.path.join(ROOT, "testing", "results", "n26_manifest.json")

sys.path.insert(0, HERE)
from physics import solver                                          # noqa: E402
from physics.solver import CALIBRATED                               # noqa: E402
from build_site import (BANK_DEPTH_M, BANK_FACADE_FRACTION,          # noqa: E402
                        rasterise)
import conformal as C                                               # noqa: E402
import environment as E                                             # noqa: E402
import metros as M                                                  # noqa: E402

# ============================================================================
# PLANT ENVELOPE -- every entry is a SCENARIO PARAMETER, never a single value.
# These describe the customer's plant, which we do not have. They are swept, the output
# carries every combination, and the demo exposes them as controls. If a viewer asks "why
# 24 C?", the answer is that we never chose one: all four are computed and shown.
# ============================================================================
PLANT_ENVELOPE = {
    # Changeover limit: the maximum intake temperature the plant tolerates at full load.
    # Anchored to the ASHRAE recommended/allowable envelope range, spanned rather than picked.
    "limit_c": [18.0, 21.0, 24.0, 27.0],
    # Mode changes permitted per day. Chillers and dampers wear; operators cap this.
    "switch_budget": [1, 2, 4],
    # Minimum hours in a mode before another change is allowed (ramp-rate limit).
    "min_dwell_h": [1, 3],
    # Notice the plant needs before a mode change takes effect. This is the axis FortyGuard's
    # forecast sells into: a thermometer cannot see 3 h ahead.
    "notice_h": [0, 1, 3, 6],
    # Where the condenser bank sits. `longest` is the realistic 123 m facade; `facing` is the
    # 50 m sensitivity, kept because it is where refusal actually fires (63.1 % of bearings).
    "bank_mode": ["longest", "facing"],
    # WHETHER THE DAY'S LEVEL OFFSET IS REMOVED. This is the single most consequential axis in
    # the whole file and it is NOT a tuning knob -- it is a question about what hardware exists.
    #   "none"   : the agent believes FortyGuard's level as delivered. MEASURED: it loses hours,
    #              because the forecast ran warm on 3 of the 4 days and a one-sided UPPER bound
    #              protects safety, not efficiency -- it cannot un-bias a biased forecast.
    #              N-56 measured the same thing at annual scale: -645 h/yr unanchored.
    #   "sensor" : ONE local observation at decision time removes the day's level. Requires
    #              customer hardware. N-56 measured this worth +100 to +712 h/yr.
    # TWO OTHER ANCHORS ARE DELIBERATELY ABSENT, and their absence is a result:
    #   previous-day FortyGuard offset -- TESTED AND FAILED (HANDOFF 6.4): mean |error| went
    #     1.43 -> 1.71 C, because the offset jumps (-0.19 -> +3.64 between two days).
    #   same-day FortyGuard offset -- UNTESTED (HANDOFF 8.4). It would remove the sensor
    #     requirement entirely, which is exactly why it must not be shipped as if it worked.
    "anchor": ["none", "sensor"],
    # MAXIMUM DEW POINT of the outside air, in C. THIS REPLACED AN INVENTED CONSTANT, and the
    # replacement is the whole point:
    #
    #   An earlier version gated on "wet-bulb <= dry-bulb limit MINUS 3 C". The 3.0 was a number
    #   I made up. It had no source, it was derived from our other knob rather than from any
    #   published standard, and it therefore FAILED this project's own point-at-the-constant
    #   test -- correctly spotted as a threshold in a costume.
    #
    #   The sourced replacement: Green Grid White Paper #46 p.6 gives the ASHRAE RECOMMENDED
    #   MAXIMUMS as 27 C dry-bulb AND 15 C dew point, and WP46's own free-cooling hour count adds
    #   an hour only when BOTH are below those maxima. So gate 2 is a DEW-POINT limit, taken from
    #   a published envelope rather than offset from our own limit, and 15.0 is its sourced value.
    #   It is swept anyway, because a customer's plant may be tighter or looser.
    #
    #   Note the consistency this exposes: 27 C, the top of `limit_c` above, IS the same
    #   standard's recommended dry-bulb maximum. Both gates now come from one published envelope.
    "dewpoint_limit_c": [None, 15.0, 18.0],
    # THE CONTAMINATION LIMIT, as a FortyGuard PM2.5 index value. None disables the gate.
    # Swept rather than chosen because FortyGuard's `:idx` fields carry no documented units or
    # scale (our defect 9.3) -- so no primary source can fix a number. The non-None value is set
    # at runtime to the p90 of FortyGuard's OWN measured distribution.
    "aq_limit_idx": [None, None],
}

# Only meaningful when anchor == "sensor". Skill is measured RELATIVE TO PERSISTENCE: 0.00 means
# the agent forecasts no better than "same as N hours ago", 1.00 means perfect. It is SWEPT, not
# assumed -- gotcha #40 is that assuming a flat small forecast error IS an oracle leak.
# For orientation only, never as an input: DIAG-57 measured FortyGuard's own skill at 0.617
# (3.5 h) and 0.838 (9.4 h) on ONE window, which is a mechanism, not a rate.
FORECAST_SKILL = [0.00, 0.50, 0.90]

ALPHA = 0.10                       # one-sided 90 % bound. A definition of confidence, not a knob.
# MEASURED N-40, AND IT IS NOT ANY FORECASTER'S ERROR. It is the spread of wind direction over
# the LEAD TIME, from KIAD ASOS observations: 47.3 deg at a 2 h lead, 71.6 deg at 10 h. (Those
# are the min and max over leads 1-12 h, not the endpoints of the horizon -- lead 1 h is 52.0.)
# It is the allowance for not knowing the future direction, and it is deliberately conservative:
# a real forecast tracks direction better than assuming it holds, so this OVERSTATES the error
# of any actual forecaster and must not be attributed to one. Swept; both ends are reported.
SIGMA_DIR_DEG = [47.0, 72.0]
SPEED_GRID_MS = [0.5, 1.5, 2.5, 3.5, 5.0, 7.0, 9.0, 12.0]
STEP_DEG = 5
BEARINGS = np.arange(0.0, 360.0, STEP_DEG)
AMB_REF = 30.0                     # reference ambient the rise table is solved at
STEPS = 800
CALM_KT = 3.0                      # ASOS reports drct = 0 when calm; bearing is undefined there
# READ from the committed geometry, not typed. This was the literal (39.024017, -77.419691), which
# is correct for exactly one site -- and the site picker offers three, so a literal here would put
# Chicago's agent at Ashburn's coordinates. `metros.site_centre()` is the midpoint of the committed
# pair's own centre_latlon, the same fields the map marker uses, so the two cannot disagree.
SITE_CENTRE = M.site_centre()
MODE_MECH, MODE_FREE = 0, 1
MODE_NAME = {MODE_MECH: "MECHANICAL", MODE_FREE: "FREE-COOLING"}


def say(*a):
    print(*a)
    sys.stdout.flush()


def banner(t):
    say("\n" + "=" * 78)
    say(t)
    say("=" * 78)


# ============================================================================
# 1. PERCEIVE
# ============================================================================
def tile_centroids(result):
    """Per-tile (lat, lon, max_temperature). max is what N-26 scores, so we score the same thing."""
    out = []
    for t in (result.get("map_data") or {}).get("features") or []:
        c = t["geometry"]["coordinates"][0]
        la = sum(x[1] for x in c[:4]) / 4.0
        lo = sum(x[0] for x in c[:4]) / 4.0
        v = t["properties"].get("max_temperature")
        if v is not None:
            out.append((la, lo, v))
    return out


def field_by_key(result):
    """Keyed on rounded centroid so a forecast tile can be matched to its outcome tile."""
    return {(round(la, 5), round(lo, 5)): v for la, lo, v in tile_centroids(result)}


NATIONAL_FIELDS = os.path.join(IA, "data", "national_fields")


def load_fixture(tag):
    """One saved FortyGuard response, by tag, from either place a paid field can live.

    TWO LOCATIONS, ONE LOADER. The hand-bought metro fields are saved as bare vendor responses in
    `testing/results/fixtures/`. The national AOI purchases are saved by
    `testing/buy_national_fields.py` into `data/national_fields/<AOI>.json`, which WRAPS the same
    response under `raw_result` alongside the AOI's provenance (rank, state, window, activity id).
    Looking in one place only is why 40 paid AOI fields sat on disk reaching no site at all: nothing
    in the pipeline read that directory. Unwrapping here rather than duplicating 7 MB per AOI into
    the fixtures directory keeps one copy of every field that was paid for.
    """
    p = os.path.join(FIXTURES, "%s.json" % tag)
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    q = os.path.join(NATIONAL_FIELDS, "%s.json" % tag)
    if os.path.exists(q):
        return (json.load(open(q, encoding="utf-8")) or {}).get("raw_result")
    return None


def perceive_fortyguard():
    """Every complete FortyGuard forecast/outcome day-pair on disk. No call is made."""
    m = json.load(open(N26_MANIFEST, encoding="utf-8"))
    pairs = []
    for dk in sorted(m["days"]):
        day = m["days"][dk]
        ft, ot = day.get("forecast_tag"), day.get("outcome_tag")
        rf, ro = (load_fixture(ft) if ft else None), (load_fixture(ot) if ot else None)
        if not rf or not ro:
            continue
        F, H = field_by_key(rf), field_by_key(ro)
        keys = [k for k in F if k in H]
        if len(keys) < 100:
            continue
        d = np.array([H[k] - F[k] for k in keys])
        pairs.append({
            "date": dk,
            "lead_h": day.get("forecast_lead_h"),
            "n_tiles": len(keys),
            "mean_d": float(d.mean()),
            "sd_d": float(d.std(ddof=1)),
            "resid": d,
            "forecast_mean": float(statistics.fmean(F[k] for k in keys)),
            "outcome_mean": float(statistics.fmean(H[k] for k in keys)),
            "forecast_tag": ft, "outcome_tag": ot,
        })
    return pairs, m


def nearest_tile(result, lat, lon):
    """The FortyGuard tile the committed site actually sits in."""
    best, bd = None, 1e18
    for la, lo, v in tile_centroids(result):
        dd = (la - lat) ** 2 + ((lo - lon) * math.cos(math.radians(lat))) ** 2
        if dd < bd:
            best, bd = (la, lo, v), dd
    return best, math.sqrt(bd) * 111320.0


def load_hours(with_dewpoint=False):
    """43,763 real KIAD hours. Returns keys, temp C, wind-from deg, speed kt.

    `with_dewpoint=True` also returns dew point, which is what the wet-bulb gate needs. Dew point
    is present for 100.0 % of hours (verified in environment.py's self-test). Kept in ONE loader
    so no other module re-reads the file and risks disagreeing about a field index.
    """
    # PER-METRO. This was `kiad_hourly_2021_2025.json` as a literal, which is correct for exactly
    # one site. `metros.weather_path()` derives the filename from the metro's STATION ID, so a
    # station change cannot leave a filename asserting the old one (see that function's docstring).
    d = json.load(open(M.weather_path(), encoding="utf-8"))
    f = d["meta"]["fields"]
    it, idr, isk = f.index("tmpc"), f.index("drct"), f.index("sknt")
    keys = sorted(d["hours"])
    g = lambda i: np.array([d["hours"][k][i] if d["hours"][k][i] is not None else np.nan
                            for k in keys], dtype=float)
    if with_dewpoint:
        return keys, g(it), g(f.index("dwpc")), g(idr), g(isk)
    return keys, g(it), g(idr), g(isk)


# ============================================================================
# 2. SOLVE -- physics on the committed geometry
# ============================================================================
def load_site(mode):
    """Rebuild the verified solver.Site from committed JSON, asserting the rebuild matches."""
    p = M.geom_path("solver_site_%s.json" % mode)
    d = json.load(open(p, encoding="utf-8"))
    n, dx = d["domain"]["n"], d["domain"]["dx_m"]
    s = solver.Site(d["domain"]["size_m"], dx)
    for ring in (d["source_ring_m"], d["receptor_ring_m"]):
        s.obstacle |= rasterise(ring, n, dx)
    bank = rasterise(d["bank_ring_m"], n, dx)
    if int(bank.sum()) != int(d["bank_cells"]):
        raise SystemExit("SITE REBUILD MISMATCH %s: %d bank cells, JSON says %d"
                         % (mode, bank.sum(), d["bank_cells"]))
    s.source[bank] += d["discharge_k"] / d["exchange_s"]
    return s, d, bank


def emission_point(site, d, bank):
    """The bank's OUTWARD FACE. Gotcha #36: a ray starting INSIDE the hall refuses everything,
    which looked like a dramatic 100 % refusal and was pure artefact. March out until clear."""
    ys, xs = np.nonzero(bank)
    bc = ((xs.mean() + 0.5) * site.dx, (ys.mean() + 0.5) * site.dx)
    cA = d["source_centre_m"]
    ox, oy = bc[0] - cA[0], bc[1] - cA[1]
    L = math.hypot(ox, oy)
    if L < 1e-6:
        raise SystemExit("bank centroid coincides with hall centroid; outward normal undefined")
    ox, oy = ox / L, oy / L
    for k in range(200):
        px, py = bc[0] + ox * (site.dx * 0.5) * k, bc[1] + oy * (site.dx * 0.5) * k
        j, i = int(px / site.dx), int(py / site.dx)
        if not (0 <= i < site.n and 0 <= j < site.n):
            raise SystemExit("outward march left the domain before clearing the obstacle")
        if not site.obstacle[i, j]:
            return (px, py), k * site.dx * 0.5
    raise SystemExit("could not clear the obstacle along the outward normal")


def rise_table(mode, cache=True):
    """rise[bearing, speed] on the committed geometry, plus the refused bearing set.

    576 solves. GPU via NVIDIA Warp when available, CPU otherwise; the device used is
    reported and lands in the trace, because "93x faster" is only honest if we say on what.
    Cached to demo/ so a re-run of the demo is instant.
    """
    cp = M.demo_path("rise_table_%s.json" % mode)
    if cache and os.path.exists(cp):
        c = json.load(open(cp, encoding="utf-8"))
        say("      rise table for %-8s loaded from cache (%s, %.1f s when computed)"
            % (mode, c["device"], c["solve_seconds"]))
        return np.array(c["rise"]), set(c["refused"]), c

    site, d, bank = load_site(mode)
    ix, iy = d["intake_m"]
    rad = d["intake_radius_m"]
    emit, march = emission_point(site, d, bank)

    refused = sorted(int(b) for b in BEARINGS
                     if solver.path_blocked(site, emit, ix, iy, float(b)))
    downwind = [int(b) for b in BEARINGS if _is_downwind(emit, ix, iy, float(b))]
    say("      %-8s emission point %.1f,%.1f m (marched %.0f m out of the facade)"
        % (mode, emit[0], emit[1], march))
    say("      %-8s path_blocked REFUSES %d of %d bearings (%d of %d downwind)"
        % (mode, len(refused), len(BEARINGS),
           len([b for b in refused if b in downwind]), len(downwind)))

    bb, ss = np.meshgrid(BEARINGS, np.array(SPEED_GRID_MS), indexing="ij")
    bf, sf = bb.ravel(), ss.ravel()
    dw = np.array([solver.downwash_fraction(v, CALIBRATED["downwash_uc"],
                                            CALIBRATED["downwash_exponent"]) for v in sf])
    t0, device = time.time(), "GPU (NVIDIA Warp)"
    try:
        from physics import warp_solver as ws
        T = ws.solve_batch(site, np.full(len(bf), AMB_REF), sf, bf, np.ones(len(bf)),
                           diffusivity=7.40, steps=STEPS, device="cuda", downwash=dw)
        rise = np.array([solver.intake_temperature(T[m].astype(np.float64), site, ix, iy, rad,
                                                   disc=True) - AMB_REF for m in range(len(bf))])
    except Exception as ex:
        device = "CPU fallback (%s)" % str(ex)[:60]
        rise = np.empty(len(bf))
        for m in range(len(bf)):
            Tm = solver.solve(site, AMB_REF, float(sf[m]), float(bf[m]), diffusivity=7.40,
                              downwash_uc=CALIBRATED["downwash_uc"],
                              downwash_exponent=CALIBRATED["downwash_exponent"])
            rise[m] = solver.intake_temperature(Tm, site, ix, iy, rad, disc=True) - AMB_REF
    el = time.time() - t0
    tab = rise.reshape(len(BEARINGS), len(SPEED_GRID_MS))
    bi, si = np.unravel_index(int(np.argmax(tab)), tab.shape)
    say("      %-8s %d solves in %.1f s on %s" % (mode, len(bf), el, device))
    say("      %-8s max rise %+.4f C at bearing %3.0f deg / %.1f m/s;  mean %+.4f C"
        % (mode, tab.max(), BEARINGS[bi], SPEED_GRID_MS[si], tab.mean()))

    meta = {"mode": mode, "device": device, "solve_seconds": round(el, 2),
            "n_solves": int(len(bf)), "emission_point_m": [round(emit[0], 2), round(emit[1], 2)],
            "march_m": march, "refused": refused, "n_downwind": len(downwind),
            "n_downwind_refused": len([b for b in refused if b in downwind]),
            "max_rise_c": float(tab.max()), "max_rise_bearing": float(BEARINGS[bi]),
            "max_rise_speed_ms": float(SPEED_GRID_MS[si]), "mean_rise_c": float(tab.mean()),
            "bearings": [float(b) for b in BEARINGS], "speeds": SPEED_GRID_MS,
            # FULL precision: this table feeds the bound, and a rounded number that a
            # comparison depends on is the bug that bit twice in one day (PLAN 8k.4, 8l.4).
            "rise": [[float(v) for v in row] for row in tab]}
    if cache:
        os.makedirs(DEMO, exist_ok=True)
        json.dump(json_safe(meta), open(cp, "w", encoding="utf-8"), allow_nan=False)
    return tab, set(refused), meta


def _is_downwind(emit, ix, iy, bearing):
    """True if wind FROM `bearing` carries the plume from the EMISSION POINT to the intake.

    IDENTICAL to `direction_sweep.py:255`, deliberately, and it must stay identical. An earlier
    version of this function used the centre-to-centre unit vector instead and reported "19 of
    36 downwind refused" where N-54 measured 36 of 36 -- two files computing the same quantity
    two ways, which is gotcha #12. The emission-point form is the correct one: the plume starts
    at the facade, not at the building's centre.
    """
    th = math.radians(bearing + 180.0)
    return bool(((ix - emit[0]) * math.sin(th) + (iy - emit[1]) * math.cos(th)) > 0.0)


def lookup_rise(tab, bearing, speed):
    """Nearest neighbour on the 5 deg / 8-speed grid. Vectorised."""
    bi = (np.round(np.asarray(bearing, dtype=float) / STEP_DEG).astype(int)) % len(BEARINGS)
    sg = np.asarray(SPEED_GRID_MS)
    si = np.abs(np.asarray(speed, dtype=float)[:, None] - sg[None, :]).argmin(axis=1)
    return tab[bi, si]


# ============================================================================
# 3. BOUND -- one-sided split conformal, with the small-sample truth stated
# ============================================================================
def conformal(res, alpha=ALPHA):
    """DELEGATES to conformal.split_conformal -- there is exactly one implementation now.

    This used to be a second, independent copy of the quantile logic living in this file. Two
    code paths computing one statistic is gotcha #12, and it is worse than usual here because a
    silent disagreement in a SAFETY bound would not announce itself. The library version is the
    one with the 20-check self-test (`python conformal.py`).

    The returned dict keeps this file's original key names so existing call sites are unchanged,
    and adds the library's own keys alongside.
    """
    c = C.split_conformal(res, alpha)
    return {"n": c["n"], "k": c["k"], "margin": c["q"], "clamped": c["clamped"],
            "attainable": c["ceiling"], "nominal": c["nominal"],
            "n_needed_for_nominal": C.min_n_for(alpha), "_library": c}


def debiased_persistence_residuals(temp, hour_of_day, notice_h):
    """The INCUMBENT's own error, measured, so it gets the same 90 % machinery the agent gets.

    Gotcha #25: raw persistence error contains the diurnal cycle -- mean +8.784 C at 12 h lead
    is the clock, not the weather. De-bias per hour-of-day BEFORE taking residuals, or the
    incumbent is handed a bias nobody operating a plant would tolerate.

    Returns (residuals, bias_by_hour_of_day). The bias table is also what the AGENT's anchored
    forecast is built from, so both sides are derived from one measurement, not two.
    """
    bias = np.zeros(24)
    if notice_h == 0:
        return np.zeros(1), bias               # zero notice: it reads the value it acts on
    t, hh = np.asarray(temp, float), np.asarray(hour_of_day, int)
    err = np.full(len(t), np.nan)
    # TRUTH minus FORECAST, the same orientation as N-26's d, because the bound is
    # forecast + margin >= truth. Getting this backwards would build a LOWER bound and call
    # it safety.
    err[notice_h:] = t[notice_h:] - t[:-notice_h]
    ok = ~np.isnan(err)
    for h in range(24):
        m = ok & (hh == h)
        if m.sum() > 10:
            bias[h] = np.nanmean(err[m])
            err[m] -= bias[h]
    return err[ok], bias


# ============================================================================
# 4. DECIDE -- a SCHEDULE, by dynamic programming, under the plant envelope
# ============================================================================
def plan(safe, switch_budget, min_dwell_h, start_mode=MODE_MECH,
         start_switches=0, start_dwell_owed=0, budget_reset_at=None):
    """Maximise free-cooling hours subject to safety, a switch budget and a dwell limit.

    NO COST WEIGHTS. Safety is a hard constraint, not a penalty term, so there is no invented
    exchange rate between "a degree of risk" and "an hour of chiller". That is the difference
    between this and `run_e2e.py`, which needed c_excursion = 120.0 to produce an answer.

    State: (mode, switches used, dwell hours still owed). The final run may be truncated by the
    horizon -- a plant does not owe dwell to a day that has ended.
    Objective: most FREE hours; ties broken toward FEWER switches.

    ------------------------------------------------------------------------------------------
    THE THREE ROLLING ARGUMENTS, added 2026-08-19, and why they are not a second planner
    ------------------------------------------------------------------------------------------
    This function used to assume it was planning a fresh calendar day from midnight: switches used
    = 0, no dwell owed, and a switch budget that never resets inside the horizon. That is fine for
    a day-at-a-time backtest and useless for a controller asked to "carry on from now", which is
    what a real plant needs -- it starts mid-afternoon already in FREE-COOLING, two hours into a
    three-hour dwell, having spent one of its two daily switches.

    Feeding that state in is the whole difference between a demo and a controller:
      start_switches    switches already spent in the CURRENT budget period.
      start_dwell_owed  hours still owed in `start_mode` before any switch is permitted.
      budget_reset_at   index in the horizon at which the daily switch counter resets, i.e. the
                        midnight crossing. None means the horizon does not cross one.

    Defaults reproduce the previous behaviour EXACTLY, so `plan(safe, b, d)` is unchanged and the
    browser mirror, `plan_fast` and the 500-case cross-language test all still hold. Extending the
    one planner rather than writing a rolling twin is deliberate -- gotcha #12, two code paths
    computing one quantity is how this project has been bitten most often.
    """
    H = len(safe)
    # state -> (free_hours, -switches, modes tuple)
    cur = {(start_mode, start_switches, start_dwell_owed): (0, 0, ())}
    for h in range(H):
        if budget_reset_at is not None and h == budget_reset_at:
            # A new budget period begins. Collapse the switch counter to 0; states that differed
            # only by switches spent in the period that just ended are now genuinely equivalent,
            # so keep the best of each collision rather than letting a stale count forbid a switch.
            merged = {}
            for (m, s, dl), v in cur.items():
                k = (m, 0, dl)
                if k not in merged or v[:2] > merged[k][:2]:
                    merged[k] = v
            cur = merged
        nxt = {}
        for (m, s, dl), (fh, negs, path) in cur.items():
            for nm in (m, 1 - m):
                if nm == m:
                    ns, ndl = s, max(0, dl - 1)
                else:
                    if dl > 0 or s >= switch_budget:
                        continue
                    ns, ndl = s + 1, max(0, min_dwell_h - 1)
                if nm == MODE_FREE and not safe[h]:
                    continue
                key = (nm, ns, ndl)
                val = (fh + (1 if nm == MODE_FREE else 0), -ns, path + (nm,))
                if key not in nxt or val[:2] > nxt[key][:2]:
                    nxt[key] = val
        if not nxt:                             # only reachable if MECH itself were infeasible
            return [MODE_MECH] * H, 0, 0
        cur = nxt
    best = max(cur.values(), key=lambda v: v[:2])
    return list(best[2]), best[0], -best[1]


def reactive_incumbent(safe, switch_budget, min_dwell_h):
    """Same plant constraints, same 90 % machinery, but decided greedily hour by hour with no
    plan -- because a reactive controller has no horizon. It flips as soon as its own bound
    allows, and pays for it in switches.

    ONE ASYMMETRY, AND IT FAVOURS THE INCUMBENT, so it is recorded rather than removed: when
    dwell or the switch budget would force it to hold FREE through an hour its own bound says is
    unsafe, SAFETY WINS and it switches anyway. A real plant would. The consequence is that the
    incumbent can EXCEED the switch budget the agent is held to, and `budget_exceeded` counts
    every time it does. That is not a flaw in the comparison, it is the finding: without a
    horizon you cannot respect a switch budget and stay safe at the same time.
    """
    H = len(safe)
    modes, m, s, dl, over = [], MODE_MECH, 0, 0, 0
    for h in range(H):
        want = MODE_FREE if safe[h] else MODE_MECH
        if want != m:
            if dl == 0 and s < switch_budget:
                m, s, dl = want, s + 1, max(0, min_dwell_h - 1)
            elif want == MODE_MECH:
                m, s, dl = want, s + 1, 0          # safety overrides dwell and budget
                over += 1
            else:
                dl = max(0, dl - 1)
        else:
            dl = max(0, dl - 1)
        modes.append(m)
    return modes, sum(1 for x in modes if x == MODE_FREE), s, over


# ============================================================================
# 5. ACT -- a BMS/SCADA-shaped command, with the reason attached
# ============================================================================
# The command log illustrates ONE fully-named point in the sweep. That is a DISPLAY selection, not
# a decision constant -- every axis here is swept, and this is simply the row whose numbers get
# printed in full. It is defined ONCE because it is needed in two places, and a second copy is
# exactly how the bound went missing (see `bound_series_key`).
ACT_REFERENCE_POINT = {"bank_mode": "longest", "anchor": "sensor", "forecast_skill": 0.50,
                       "notice_h": 3, "switch_budget": 2, "min_dwell_h": 3}


def bound_series_key(mode, anchor, offset_tag, skill, notice_h):
    """The name under which the scenario sweep parks its per-hour upper bound so that the ACT
    stage can quote it.

    ONE constructor, used by the writer and by the reader, because the two disagreed in silence.
    The reader asked `row.get("bound_c|longest|sensor|anchored|0.50|3") or [None] * H`; NOTHING in
    the tree ever wrote that key, because `_day_series` is not built until after the sweep has
    finished. The `or` default then turned every entry into `float("nan")`, so ALL 37 shipped
    command rows carried `bound_c: null` and the literal words "upper bound on intake nan C" in
    their reason -- 100 % of stage 5's output, for as long as the stage has existed.

    Two guards now stand where there was a default: this shared constructor, and a hard KeyError
    at the read site instead of a fallback (gotcha #54 -- a silent default reads as coverage).
    """
    return "bound_c|%s|%s|%s|%.2f|%d" % (mode, anchor, offset_tag, skill, notice_h)


def _why_free(bound_i, rise_i, limit_c, mm):
    """The free-cooling justification, phrased for the margin THAT WAS ACTUALLY SUPPLIED.

    🔴 THIS EXISTS BECAUSE THE LIVE AGENT CRASHED THE FIRST TIME IT SAID YES, AND HAD ALWAYS BEEN
    GOING TO. `bms_commands` built one sentence and indexed `margin_meta["level_c"]`,
    `["n_level"]`, `["shape_c"]`, `["n_shape"]` and `["clamped"]` with brackets. `agent.py` supplies
    exactly those five from the five-year backtest; `live.py:1527` passes its own `mprov`, which has
    NONE of them. REPRODUCED: one MODE_FREE hour with the real provenance dict out of
    `demo/live.json` raises `KeyError: 'level_c'`; the same call with zero free hours returns a row
    and no error.

    That is why it was never seen. The row is only built on a mode CHANGE, the sentence only on a
    free-cooling row, and all three committed live artefacts (ashburn, chicago, dulles) contain zero
    free-cooling hours, while both of live.py's offline self-tests assert `"commands" not in out`.
    So the path fires on the first cold hour of the first live run that succeeds, on any of the 238
    offerable sites, which is the exact moment the product is meant to work.

    ⚠ THE FIX IS NOT A KEY MAPPING, AND THAT WAS THE TEMPTING WRONG ANSWER. The two margins are not
    the same quantity under different names. The replay margin is a LEVEL term measured over
    calibration DAYS plus a SHAPE term measured over persistence HOURS, and its sentence says so and
    then says that summing two one-sided 90 % bounds guarantees 80 %. The live margin is ONE scalar
    from N measured FortyGuard day-PAIRS with no shape term in existence. Renaming
    `clamped_to_attainable` to `clamped` and `n_calibration_pairs` to `n_level` would have produced a
    sentence describing a decomposition the live bound does not have, on a document that claims every
    number is checkable.

    So the shape of the meta selects the sentence, and each sentence states only what its own margin
    can support. The live one carries the extrapolation warning, because `live.py`'s margin is
    measured at one lead and one hour of day and applied to all of them.
    """
    if "level_c" in mm:
        return ("upper bound on intake %.3f C = forecast + level margin %+.3f C (from %s "
                "calibration DAYS%s) + shape margin %+.3f C (from %s persistence hours) "
                "+ recirculation %+.3f C, under the %.1f C plant limit. Summing two "
                "one-sided 90 %% bounds guarantees 80 %%, not 90 %% -- stated, not implied."
                % (bound_i, mm["level_c"],
                   ("%d" % mm["n_level"]) if mm.get("n_level") is not None else "no",
                   ", CLAMPED: guarantee degraded" if mm.get("clamped") else "",
                   mm["shape_c"], format(mm["n_shape"], ","), rise_i, limit_c))

    # The live margin. One scalar, measured, with its own limitations attached.
    n = mm.get("n_calibration_pairs")
    clamp = ("; CLAMPED to the %s attainable at n=%s, so the 90 %% guarantee is degraded"
             % (("%.0f %%" % (100.0 * mm["attainable_coverage_ceiling"]))
                if mm.get("attainable_coverage_ceiling") is not None else "ceiling",
                n if n is not None else "?")
             if mm.get("clamped_to_attainable") else "")
    borrowed = ("; margin BORROWED from %s, this site owns no calibration of its own"
                % mm["borrowed_from"]) if mm.get("borrowed_from") else ""
    return ("upper bound on intake %.3f C = forecast + measured margin %+.3f C (from %s FortyGuard "
            "day-PAIRS%s%s) + recirculation %+.3f C, under the %.1f C plant limit. One margin, not "
            "a level and shape split: this site's live calibration measures a single day-level "
            "residual. It was measured at one forecast lead and one hour of day and is applied to "
            "all of them, which is an EXTRAPOLATION and is recorded as one."
            % (bound_i, mm.get("margin_c") if mm.get("margin_c") is not None else float("nan"),
               n if n is not None else "no", clamp, borrowed, rise_i, limit_c))


def bms_commands(modes, hours, bound, limit_c, rise, refused_flags, margin_meta):
    """The interface an actual plant would receive. Every row carries WHY.

    Nothing here talks to real hardware -- there is no plant. The shape is what matters: a
    point in time, a mode, and an auditable reason with the numbers that produced it.

    ⚠ THE FREE-COOLING SENTENCE IS IN `_why_free`, WHICH BRANCHES ON THE MARGIN'S SHAPE. See its
    docstring: the replay and live margins are different quantities, and this function crashed on
    the live one for as long as it existed.
    """
    out, prev = [], None
    for i, m in enumerate(modes):
        if m != prev:
            # A command row whose bound is not a number is not a command, it is a bug wearing one.
            # `"%.3f" % float("nan")` renders the word "nan" into perfectly valid prose, and
            # `json_safe()` then turns the field beside it into a perfectly valid `null` -- so
            # neither the JSON validator nor a reader of the file can see anything wrong.
            #
            # 🔴 BUT A MISSING FORECAST IS NOT A BUG, AND USED TO CRASH THE RUN. MEASURED on a
            # live Ashburn run whose hour 10 came back "no field (submit_rejected)": the schedule
            # put a mode change on that hour, this guard fired, and stage 5 killed a run whose
            # first four stages had all succeeded. Every replay gives every hour a value, which
            # is why nothing before that run reached it.
            #
            # The distinction the guard exists for is kept. `safe` requires `bound_known`, so a
            # FREE row can never legitimately carry a NaN bound and one there really is a defect:
            # that still raises. A MECHANICAL row with no bound is the ordinary case of the
            # vendor not answering, which is precisely what the plant must be told, so it states
            # that instead of asserting a number it does not have.
            _no_bound = not math.isfinite(float(bound[i]))
            if _no_bound and m == MODE_FREE:
                raise ValueError(
                    "stage 5 was handed a non-finite bound on a FREE-COOLING hour, %s (index "
                    "%d). `safe` requires a known bound, so this is a defect upstream, not a "
                    "missing forecast. Refusing to certify an hour on a number it does not have."
                    % (hours[i], i))
            if _no_bound:
                why = ("NO FORECAST for this hour: the vendor returned no field, so there is no "
                       "bound to compare against the %.1f C plant limit. Staying on MECHANICAL, "
                       "which is what an unanswered hour must default to." % limit_c)
                out.append({"hour": hours[i], "index": i, "command": MODE_NAME[m], "reason": why,
                            "bound_c": None, "rise_c": round(float(rise[i]), 4),
                            "refused": bool(refused_flags[i]), "no_forecast": True})
                prev = m
                continue
            if refused_flags[i]:
                why = ("REFUSE to certify: a building lies on the source-to-intake path at this "
                       "bearing, so the solver's answer is not physical (see gotcha #26). "
                       "Falling back to MECHANICAL.")
            elif m == MODE_FREE:
                why = _why_free(bound[i], rise[i], limit_c, margin_meta or {})
            else:
                why = ("upper bound on intake %.3f C is NOT under the %.1f C plant limit "
                       "(recirculation contributes %+.3f C)." % (bound[i], limit_c, rise[i]))
            out.append({"hour": hours[i], "index": i, "command": MODE_NAME[m], "reason": why,
                        # FULL PRECISION. `round(..., 4)` here forced audit.check_act_stage to
                        # carry a tolerance it could not justify, when the quantity being compared
                        # is an identity (gotcha #44, #63). The 3 dp in the reason text above is
                        # display rounding and belongs there; the field is the number.
                        "bound_c": float(bound[i]),
                        "rise_c": round(float(rise[i]), 4),
                        "refused": bool(refused_flags[i])})
            prev = m
    return out


# ============================================================================
# 6. SCORE + RECALIBRATE -- the loop that earns hours
# ============================================================================
def day_level_ceiling(cal_days):
    """THE CEILING THAT ACTUALLY BINDS, and getting this wrong misstates the whole argument.

    Pooling 3 days of tiles gives 53,586 residuals, so n/(n+1) computed on the TILE count says
    the attainable coverage is 99.998 %. That is nonsense, and the reason is measured, not
    assumed: DIAG-57 found the map SHIFTS TOGETHER -- a ~1.2 C whole-field offset against
    ~0.1 C of between-tile scatter, a ratio of 3x to 12x. Tiles inside one day are therefore
    very nearly ONE observation, not 17,862 independent ones. Exchangeability holds across DAYS.

    So the effective sample size is the DAY count, and the arithmetic ceiling on coverage is
    n_days/(n_days+1): 75 % at 3 days, 80 % at 4, 90 % first reachable at 9. That is HANDOFF
    section 7.2, and it is why a 90 % bound was never obtainable from the days we had --
    arithmetically, before FortyGuard is implicated at all.
    """
    return cal_days / (cal_days + 1.0)


def score_sequential(pairs, alpha=ALPHA):
    """Calibrate on all earlier days, test on the next. This reproduces N-26 exactly, and it
    must: if this file disagreed with `testing/test_n26_coverage.py` one of them is wrong.

    Also returns the MARGIN TRAJECTORY -- how the agent's own bound moves as its record grows.
    That trajectory IS the recalibration step. Nobody widens it by hand.
    """
    rows, cov_n, cov_k = [], 0, 0
    for i in range(1, len(pairs)):
        cal = np.concatenate([pairs[j]["resid"] for j in range(i)])
        c = conformal(cal, alpha)
        d = pairs[i]["resid"]
        covered = int((d <= c["margin"]).sum())
        rows.append({"test_date": pairs[i]["date"], "cal_days": i, "cal_n": int(len(cal)),
                     "margin_c": round(c["margin"], 4), "clamped": c["clamped"],
                     "coverage": covered / len(d), "n_test": int(len(d)),
                     "day_level_ceiling": round(day_level_ceiling(i), 4),
                     "tile_level_ceiling_MISLEADING": round(c["attainable"], 6)})
        cov_k += covered
        cov_n += len(d)
    pooled = (cov_k / cov_n) if cov_n else float("nan")
    traj = []
    for i in range(1, len(pairs) + 1):
        c = conformal(np.concatenate([pairs[j]["resid"] for j in range(i)]), alpha)
        cd = conformal(np.array([pairs[j]["mean_d"] for j in range(i)]), alpha)
        traj.append({"after_days": i, "margin_c": round(c["margin"], 4),
                     "day_level_margin_c": round(cd["margin"], 4),
                     "day_level_ceiling": round(day_level_ceiling(i), 4),
                     "day_level_clamped": cd["clamped"]})
    return rows, pooled, traj


# ============================================================================
# THE REAL FORTYGUARD CYCLE -- one full loop per real day, scored against the real outcome
# ============================================================================
def run_cycle():
    banner("STAGE 1-6  ONE FULL LOOP PER REAL FORTYGUARD DAY   [no API call]")
    pairs, manifest = perceive_fortyguard()
    if not pairs:
        say("   no complete forecast/outcome pairs on disk.")
        return None

    say("\n   1. PERCEIVE   %d complete FortyGuard day-pairs, %s tiles each"
        % (len(pairs), format(pairs[0]["n_tiles"], ",")))
    say("      %-12s %7s %10s %10s %10s %10s"
        % ("date", "lead h", "fcst mean", "true mean", "mean d", "sd d"))
    for p in pairs:
        say("      %-12s %7.2f %10.4f %10.4f %+10.4f %10.4f"
            % (p["date"], p["lead_h"] or 0.0, p["forecast_mean"], p["outcome_mean"],
               p["mean_d"], p["sd_d"]))
    say("      (d = outcome - forecast. Positive means the forecast ran COOL.)")

    # the tile the site actually sits in -- FortyGuard's spatial dimension doing real work
    # THE TILE LOOKUP IS ONLY MEANINGFUL WHERE THE FIELD WAS BOUGHT.
    # The saved heatmaps cover an 8x8 km box over Ashburn. Running this for Chicago found the
    # nearest Ashburn tile and reported it 926,064 m away -- an arithmetically correct answer to a
    # question nobody asked, and one that reads as a bug. Non-Ashburn metros get the honest
    # sentence instead, and `site_tiles` stays empty rather than holding a 926 km "nearest" tile.
    own_field = M.metro_key() == M.DEFAULT_METRO
    site_tiles = {}
    if own_field:
        for p in pairs:
            r = load_fixture(p["forecast_tag"])
            (la, lo, v), dist = nearest_tile(r, *SITE_CENTRE)
            site_tiles[p["date"]] = {"lat": round(la, 6), "lon": round(lo, 6),
                                     "forecast_c": v, "dist_m": round(dist, 1)}
        say("      committed site %.6f, %.6f sits in tile %.6f, %.6f (%.0f m away)"
            % (SITE_CENTRE[0], SITE_CENTRE[1], site_tiles[pairs[0]["date"]]["lat"],
               site_tiles[pairs[0]["date"]]["lon"], site_tiles[pairs[0]["date"]]["dist_m"]))
    else:
        say("      *** these day-pairs are ASHBURN's. %s has no forecast/outcome pair of its own,"
            % M.metro()["label"])
        say("      so the LEVEL TERM below is borrowed and the coverage record is Ashburn's. This")
        say("      site's WEATHER and GEOMETRY are its own; its hours are its own. Its coverage is")
        say("      not. Recorded in trace.fortyguard_provenance and shown on the page.")

    say("\n   2. SOLVE      recirculation on the committed geometry, both bank placements")
    tabs = {}
    for mode in PLANT_ENVELOPE["bank_mode"]:
        tab, refused, meta = rise_table(mode)
        tabs[mode] = (tab, refused, meta)

    say("\n   3. BOUND      one-sided split conformal from the agent's own record")
    allres = np.concatenate([p["resid"] for p in pairs])
    c_all = conformal(allres)
    say("      per-TILE pooling: n=%s residuals, k=%s, margin %+.4f C, clamped=%s"
        % (format(c_all["n"], ","), format(c_all["k"], ","), c_all["margin"], c_all["clamped"]))
    say("         ^ this n is MISLEADING and we do not lean on it. DIAG-57 measured the field")
    say("           shifting TOGETHER: ~1.2 C whole-map offset vs ~0.1 C between-tile scatter,")
    say("           3x to 12x. One day's tiles are nearly ONE observation, not %s."
        % format(pairs[0]["n_tiles"], ","))
    cday = conformal(np.array([p["mean_d"] for p in pairs]))
    say("      per-DAY (the level that actually varies): n=%d, k=%d, margin %+.4f C, clamped=%s"
        % (cday["n"], cday["k"], cday["margin"], cday["clamped"]))
    say("      -> a %.0f %% bound needs n >= %d calibration DAYS. With n = %d the arithmetic"
        % (100 * (1 - ALPHA), cday["n_needed_for_nominal"], cday["n"]))
    say("         ceiling on coverage is n/(n+1) = %.1f %%. 90 %% IS NOT OBTAINABLE YET, and"
        % (100 * day_level_ceiling(cday["n"])))
    say("         that is OUR sample size, not FortyGuard's. ~10 days recovers it, free.")

    say("\n   4-5. DECIDE + ACT   per day, swept over the whole plant envelope")
    rows, pooled, traj = score_sequential(pairs)
    decisions = []
    for i in range(1, len(pairs)):
        p = pairs[i]
        cal = np.array([pairs[j]["mean_d"] for j in range(i)])
        c = conformal(cal)
        fmean = p["forecast_mean"]
        for mode in PLANT_ENVELOPE["bank_mode"]:
            tab, refused, _ = tabs[mode]
            # Refused bearings hold MEANINGLESS values, not small ones, so they are masked out
            # before the worst case is taken -- otherwise the worst case could be a number the
            # agent has already declared it cannot compute.
            ok_rows = np.array([int(b) not in refused for b in BEARINGS])
            worst_rise = float(tab[ok_rows].max()) if ok_rows.any() else float("nan")
            ub = fmean + c["margin"] + worst_rise
            for limit in PLANT_ENVELOPE["limit_c"]:
                declared = bool(ub <= limit)
                breached = bool(p["outcome_mean"] + worst_rise > limit)
                decisions.append({
                    "date": p["date"], "bank_mode": mode, "limit_c": limit,
                    "forecast_c": round(fmean, 4), "margin_c": round(c["margin"], 4),
                    "worst_rise_c": round(worst_rise, 4), "bound_c": round(ub, 4),
                    "outcome_c": round(p["outcome_mean"], 4),
                    "declared_free": declared, "would_have_breached": breached,
                    "unsafe_declaration": bool(declared and breached),
                    "cal_days": i})
    say("      %d decisions written (%d days x %d bank modes x %d limits)"
        % (len(decisions), len(pairs) - 1, len(PLANT_ENVELOPE["bank_mode"]),
           len(PLANT_ENVELOPE["limit_c"])))
    n_free = sum(1 for d in decisions if d["declared_free"])
    unsafe = [d for d in decisions if d["unsafe_declaration"]]
    say("      declared FREE-COOLING: %d of %d      unsafe declarations: %d"
        % (n_free, len(decisions), len(unsafe)))
    if n_free == 0:
        say("      *** VACUITY GUARD (gotcha #37: a condition can be MET AND MEANINGLESS) ***")
        say("      Zero unsafe declarations here is NOT evidence the agent is safe -- it declared")
        say("      free cooling ZERO times, so it had no opportunity to be wrong. The reason is")
        say("      physical, not a bug: these are August afternoons in Virginia at %.1f-%.1f C,"
            % (min(p["outcome_mean"] for p in pairs), max(p["outcome_mean"] for p in pairs)))
        say("      and the highest limit in the envelope is %.1f C. NO controller of any kind"
            % max(PLANT_ENVELOPE["limit_c"]))
        say("      free-cools on those days. What the four real days DO test is the BOUND -- and")
        say("      it failed, at 65.6 %. The hours claim is tested where days actually cross,")
        say("      which is the scheduling cases on 43,763 real hours, not here.")

    say("\n   6. SCORE + RECALIBRATE   out-of-sample, against the elapsed outcome")
    say("      %-12s %9s %10s %11s %14s"
        % ("test day", "cal days", "margin C", "coverage", "day ceiling"))
    for r in rows:
        say("      %-12s %9d %+10.4f %10.1f%% %13.1f%%"
            % (r["test_date"], r["cal_days"], r["margin_c"], 100 * r["coverage"],
               100 * r["day_level_ceiling"]))
    say("      POOLED out-of-sample coverage: %.1f %%  over %d test days   (nominal %.0f %%)"
        % (100 * pooled, len(rows), 100 * (1 - ALPHA)))
    say("      margin trajectory -- the agent widening ITSELF, unprompted, as its record grows:")
    for t in traj:
        say("         after %d day(s): tile margin %+.4f C   day margin %+.4f C   ceiling %.1f %%%s"
            % (t["after_days"], t["margin_c"], t["day_level_margin_c"],
               100 * t["day_level_ceiling"],
               "  [CLAMPED]" if t["day_level_clamped"] else ""))
    say("         ^ after the 08-15 miss the bound moved -0.7394 -> +0.1905 C on its own. No")
    say("           human widened it. That single line is the recalibrate step of the loop.")
    say("\n      VERDICT, against conditions fixed before any outcome existed:")
    say("         P1 pooled coverage >= 85 %%  : %-5s (%.1f %%)"
        % (pooled >= 0.85, 100 * pooled))
    say("         P2 no test day < 60 %%      : %-5s (worst %.1f %%)"
        % (min(r["coverage"] for r in rows) >= 0.60, 100 * min(r["coverage"] for r in rows)))
    say("         P3 at least 3 test days    : %-5s (%d)" % (len(rows) >= 3, len(rows)))
    say("      -> FAIL. Reported, not hidden. HANDOFF section 7.2 splits the shortfall:")
    say("         90 -> 75 % is OUR sample size (pure arithmetic, n = 3 days);")
    say("         75 -> 65.6 % is FortyGuard's day-varying level offset.")
    say("         ~10 calibration days recovers 90 %, on pure FortyGuard data, no customer")
    say("         hardware. We have %d. NEVER quote 90 %% until they exist." % len(pairs))

    return {"pairs": [{k: v for k, v in p.items() if k != "resid"} for p in pairs],
            "site_tiles": site_tiles,
            "bound_all_tiles": c_all, "bound_day_level": cday,
            "sequential": rows, "pooled_coverage": pooled, "margin_trajectory": traj,
            "decisions": decisions,
            "rise_tables": {m: tabs[m][2] for m in tabs},
            "manifest_errors": manifest.get("errors", {})}


# ============================================================================
# THE SCHEDULING CASES -- real KIAD days, real wind, the four MEASURED offsets
# ============================================================================
def case_criterion(c, worst_bearing):
    """Render one case's criterion for THIS site's own measured worst bearing.

    MODULE LEVEL so the console log and the emitted trace call the SAME function. The first version
    was a closure defined just before the `return`, while the log loop printing the criteria runs
    earlier in the same function -- so the console showed readers the raw
    "{worst_bearing:.0f} deg" template while the artefact was correct. One renderer, two callers.

    With no worst bearing there is nothing to quote: `.format(None)` renders "None deg" and skipping
    the substitution leaves template syntax on the page. Both are worse than stating the true thing.
    """
    if "{worst_bearing" not in c:
        return c
    if worst_bearing is None:
        return ("day whose wind sits closest to the worst bearing -- NOT APPLICABLE: no plume was "
                "solved at this facility, so no bearing is worst")
    return c.format(worst_bearing=worst_bearing)


CASE_SPECS = [
    ("clear_cool",   "max hourly temp at least 4 C below the lowest limit in the envelope"),
    ("clear_hot",    "highest MINIMUM hourly temperature in five years -- mechanical all day"),
    ("crossing",     "crosses one limit exactly twice -- one changeover each way"),
    ("chatter",      "most limit crossings of any day in five years at some limit"),
    ("recirc_edge",  "most hours sitting within the worst recirculation rise below a limit"),
    # 🔴 GENERATED FROM THIS SITE'S OWN MEASUREMENT, and it used to be the literal "255 deg".
    # 255 is ASHBURN's worst bearing. The string shipped verbatim on every site: measured
    # 2026-08-24, `chicago_trace.json` and `dulles_trace.json` both published "closest to the worst
    # bearing, 255 deg" while their own `rise_tables.longest.max_rise_bearing` read 240 and 265.
    # The DAY the code picked was correct -- `knife_edge` minimises distance to the real
    # `worst_bearing` variable -- so the selection was right and only the sentence describing it was
    # false, which is the hardest version to notice. Fifth instance of gotcha #67 ("hard-coded
    # narratives have asserted things that were false") and exactly what methodology rule 11 says:
    # generate the prose from the data rather than writing it twice.
    ("knife_edge",   "day whose wind sits closest to the worst bearing, {worst_bearing:.0f} deg"),
    ("safe_sector",  "day whose wind sits in the zero-rise sector"),
]


def _building_label(b):
    """WHO THIS BUILDING IS, and never the same answer for two different buildings.

    The mirror of `buildingOf()` in demo/index.html. A name if OSM carries one; otherwise the way
    id, which is unique by construction and which a reader can look up. The bare word "unnamed" is
    not an identifier -- it collides with every other unnamed building, and audit.py's identity
    check correctly reads that collision as a fallback masquerading as a measurement.
    """
    nm = b.get("name")
    if nm:
        return nm
    osm = b.get("osm_id")
    return ("OSM way %s" % osm) if osm is not None else "unnamed building"


def select_cases(keys, temp, dewp, drct, sknt, tab):
    """Pick real days from the 43,763-hour record by PRINTED criteria, then report what was
    picked. These are not invented days -- every one is a date that happened at KIAD.
    """
    days = {}
    for i, k in enumerate(keys):
        days.setdefault(k[:10], []).append(i)
    # 🔴 "COMPLETE DAY" HAS TO MEAN EVERY CHANNEL A GATE READS, NOT JUST TEMPERATURE.
    # This filter checked `temp` alone. The agent gates on three things -- dry bulb, humidity and
    # contamination -- so a day with a full temperature record and a hole in the dew point is not a
    # complete day for this purpose, and it is a poor worked example: `nan <= limit` is False in
    # numpy, so the humidity gate fails CLOSED and the hour runs mechanical for want of a reading
    # rather than for a reason about the weather. Correct as a decision, useless as an illustration.
    # It also broke the build. Two national facilities -- KCBF missing 2 hours of dew point, the
    # Lockbourne station 6 -- had one of those hours land inside a selected case day, and every
    # downstream consumer that formats a per-hour number hit the resulting null in turn:
    # explain.py's json.dump refused it and left a truncated 4,300-byte artefact behind, then
    # ticker.py raised on float(None). Both of those are now honest about an absent value in their
    # own right, but the real defect was upstream and is here: the case set should never have
    # offered a day whose humidity gate cannot be evaluated.
    # The five-year backtest is untouched by this and still scores ALL hours, gaps included -- this
    # narrows only the five named days chosen as worked examples, which is exactly what it should do.
    full = {d: ix for d, ix in days.items()
            if len(ix) >= 20 and not np.isnan(temp[ix]).any() and not np.isnan(dewp[ix]).any()}
    worst_rise = float(tab.max())
    # 🔴 argmax OF AN ALL-ZERO TABLE RETURNS INDEX 0, AND INDEX 0 IS DUE NORTH.
    # A standalone facility's rise table is identically zero -- there is no neighbour intake for a
    # plume to be worst at -- so this line published `worst_bearing_deg: 0.0`, and the knife_edge
    # criterion rendered "the worst bearing, 0 deg". That is a fabricated compass direction, and it
    # would have appeared in the trace, the wind dial and the PDF for 360 facilities.
    # The rise table already publishes `max_rise_bearing: null` for exactly this reason; this is the
    # same quantity computed a second time here, and it has to agree. Found by `audit.py` crashing
    # while comparing the two -- the check disagreeing with the artefact is what exposed it.
    worst_bearing = (None if not np.any(tab > 0.0) else
                     float(BEARINGS[int(np.unravel_index(int(np.argmax(tab)), tab.shape)[0])]))
    lo, hi = min(PLANT_ENVELOPE["limit_c"]), max(PLANT_ENVELOPE["limit_c"])
    picks = {}

    def crossings(t, lim):
        s = (np.asarray(t) > lim).astype(int)
        return int(np.abs(np.diff(s)).sum())

    cand = {d: temp[ix] for d, ix in full.items()}
    c1 = [(d, t.max()) for d, t in cand.items() if t.max() <= lo - 4.0]
    picks["clear_cool"] = max(c1, key=lambda x: x[1])[0] if c1 else None
    # NOT "min temp above the highest limit": no day at KIAD in five years has a night warmer
    # than 27 C, so that criterion finds nothing. Verified, then relaxed to the honest question
    # -- which real day is hottest overnight -- rather than left as a hole in the case set.
    c2 = [(d, float(t.min())) for d, t in cand.items()]
    picks["clear_hot"] = max(c2, key=lambda x: x[1])[0] if c2 else None
    c3 = [(d, abs(t.max() - t.min())) for d, t in cand.items()
          if any(crossings(t, L) == 2 for L in PLANT_ENVELOPE["limit_c"])]
    picks["crossing"] = max(c3, key=lambda x: x[1])[0] if c3 else None
    c4 = [(d, max(crossings(t, L) for L in PLANT_ENVELOPE["limit_c"])) for d, t in cand.items()]
    picks["chatter"] = max(c4, key=lambda x: x[1])[0] if c4 else None
    c5 = [(d, max(int(((t > L - worst_rise) & (t <= L)).sum()) for L in PLANT_ENVELOPE["limit_c"]))
          for d, t in cand.items()]
    picks["recirc_edge"] = max(c5, key=lambda x: x[1])[0] if c5 else None
    c6, c7 = [], []
    for d, ix in full.items():
        b, s = drct[ix], sknt[ix]
        ok = (~np.isnan(b)) & (s >= CALM_KT)
        if ok.sum() < 12:
            continue
        if worst_bearing is not None:
            db = np.abs(((b[ok] - worst_bearing + 180.0) % 360.0) - 180.0)
            c6.append((d, float(db.mean())))
        r = lookup_rise(tab, b[ok], np.maximum(s[ok] * 0.514444, 0.3))
        c7.append((d, float(np.abs(r).mean())))
    # NO WORST BEARING, NO knife_edge DAY. The case is "the day whose wind sat closest to the worst
    # bearing" -- with no worst bearing there is no such day, and `min()` over an all-equal list
    # would return whichever day happened to sort first while the label claimed it was chosen for a
    # reason. `None` here renders as "NONE FOUND", which is what the other cases already do when
    # five years of weather contain no example.
    picks["knife_edge"] = (min(c6, key=lambda x: x[1])[0] if c6 else None)
    # `safe_sector` is degenerate the same way when every rise is zero -- every day is equally
    # "in the zero-rise sector", so picking one implies a discrimination that did not happen.
    picks["safe_sector"] = (min(c7, key=lambda x: x[1])[0]
                            if (c7 and worst_bearing is not None) else None)
    return picks, worst_rise, worst_bearing


def hod_of(ix, keys):
    """Hour-of-day index array for a list of record positions."""
    return np.array([int(keys[i][-2:]) for i in ix])


def _pm25_hour_profile():
    """Hour-of-day PM2.5 index profile MEASURED from FortyGuard's saved env_params responses.

    What this is: the average diurnal shape of PM2.5 at this site, across every saved response
    carrying a full 24-hour series. That shape is a real measurement.

    What this is NOT: a claim about air quality on any particular 2021-2025 day. FortyGuard's
    series are 2026 and the KIAD case days are 2021-2025, so there is no per-day overlap. Using
    the measured diurnal shape as an overlay is the honest maximum available; inventing per-day
    air quality is the alternative and we will not do it. The gate LIMIT is swept, never chosen,
    because the `:idx` values carry no documented units (our defect 9.3).
    """
    try:
        envs = E.load_env_params()
    except Exception:
        return None, 0
    rows = []
    for e in envs:
        v = e["parameters"].get("air_quality_pm2p5:idx")
        if isinstance(v, list) and len(v) >= 24:
            a = np.array([np.nan if x is None else float(x) for x in v[:24]], dtype=float)
            if np.isfinite(a).all():
                rows.append(a)
    if not rows:
        return [], 0
    # REAL measured 24-hour series, NOT their average. Averaging 9 days flattened the profile to
    # 45.9-48.1 and destroyed the diurnal variation that makes the gate mean anything. Each case
    # day is instead paired with one real measured FortyGuard air-quality day, in rotation. The
    # pairing is arbitrary -- the years do not overlap -- and it is labelled as arbitrary.
    return rows, len(rows)


def plume_uncertainty_terms(mode):
    """(spread table, multiplier, sigma_dir) for the plume term of the bound.

    Imported lazily because `plume_uncertainty` imports THIS module -- a top-level import would
    be circular. Reads the calibration written by `python plume_uncertainty.py`; if it is absent
    the plume term is DISABLED rather than silently guessed, and that is reported.
    """
    try:
        from plume_uncertainty import lookup_spread, spread_table   # noqa: F401
        # PER-SITE. This was `os.path.join(DEMO, ...)` -- unsuffixed -- so every site after the
        # first read the first site's calibration. See spread_table()'s docstring for the full
        # measurement of what that shipped.
        pj = M.demo_path("plume_uncertainty.json")
        if not os.path.exists(pj):
            return None, 0.0, None, ("%s missing -- run plume_uncertainty.py for this metro"
                                     % os.path.basename(pj))
        cal = json.load(open(pj, encoding="utf-8"))["calibration"]
        sd = cal["shipped"]["sigma_dir_deg"]
        mult = cal["shipped"]["multiplier"]
        tab, meta = spread_table(mode, sd)
        return tab, float(mult), float(sd), None
    except Exception as ex:
        return None, 0.0, None, "plume term disabled: %s" % str(ex)[:70]


def run_cases(fg_offsets, extra_note=""):
    banner("SCHEDULING CASES   real KIAD days x the four MEASURED FortyGuard offsets   [no API call]")
    keys, temp, dewp, drct, sknt = load_hours(with_dewpoint=True)
    say("   1. PERCEIVE   %s real KIAD hourly records, %s to %s"
        % (format(len(keys), ","), keys[0], keys[-1]))
    hour_of_day = np.array([int(k[-2:]) for k in keys])

    # ---- WET BULB, for the humidity gate. Computed from the real dew point (100 % coverage),
    # by the same validated code the backtest uses -- agreement with PsychroLib's ASHRAE
    # formulation is 0.2681 C MAE, inside Stull's published < 0.3 C. See environment.py.
    rh = E.rh_from_dewpoint(temp, dewp)
    twb, stull_ok = E.wet_bulb_stull(temp, rh)
    say("      wet-bulb computed for all hours; %.2f %% inside Stull's validity envelope"
        % (100.0 * stull_ok.mean()))

    # ---- AIR QUALITY, for the contamination gate. THE HONEST CONSTRUCTION, and its limit:
    # FortyGuard's air-quality series exist for 2026, the KIAD case days for 2021-2025, so there
    # is NO per-day overlap. What IS real and usable is the DIURNAL SHAPE: 29 saved env_params
    # responses give a measured hour-of-day PM2.5 profile at this site. That profile is applied
    # as a climatological overlay and LABELLED as one -- it is not a claim about air quality on
    # any specific 2021-2025 day, and the gate limit is swept, not chosen, because FortyGuard's
    # `:idx` values carry no documented units (our defect 9.3).
    aq_days, aq_n = _pm25_hour_profile()
    if aq_days:
        allv = np.concatenate(aq_days)
        PLANT_ENVELOPE["aq_limit_idx"] = [None, float(np.percentile(allv, 90))]
        say("      %d REAL measured FortyGuard 24-h PM2.5 series on disk; index range %.1f-%.1f"
            % (aq_n, allv.min(), allv.max()))
        say("      each case day is paired with one real measured series, in rotation "
            "(arbitrary pairing -- the years do not overlap, and it is labelled as arbitrary)")
        say("      contamination limit swept at [off, %.1f] = the p90 of FortyGuard's own "
            "measured values" % PLANT_ENVELOPE["aq_limit_idx"][1])
    else:
        PLANT_ENVELOPE["aq_limit_idx"] = [None]
        say("      no FortyGuard air-quality series on disk -- contamination gate DISABLED")

    tabs = {}
    for mode in PLANT_ENVELOPE["bank_mode"]:
        tabs[mode] = rise_table(mode)
    tab_primary = tabs["longest"][0]

    picks, worst_rise, worst_bearing = select_cases(keys, temp, dewp, drct, sknt, tab_primary)
    say("\n   case selection, by the criteria printed here, over %d complete days:"
        % len({k[:10] for k in keys}))
    for name, crit in CASE_SPECS:
        say("      %-12s %-12s  %s" % (name, picks.get(name) or "NONE FOUND",
                                       case_criterion(crit, worst_bearing)))
    if worst_bearing is None:
        say("      no recirculation was solved: this facility has no tagged neighbour inside the")
        say("      solver's validated range, so there is no intake for a rise to be worst at.")
    else:
        say("      worst recirculation rise on the committed geometry: %+.4f C at %.0f deg"
            % (worst_rise, worst_bearing))
        say("      NOTE %.4f C is BELOW the 0.556 C resolution of the ASOS station one would"
            % worst_rise)
        say("           validate against. Real physics, small here, and said so rather than hidden.")

    # ---- THE BOUND IS NOW GROUP-CONDITIONAL (MONDRIAN), not one pooled quantile.
    # Measured on this exact data (backtest.py's Mondrian audit): a pooled quantile reads 0.9017
    # coverage overall at 3 h notice while hour 9 sits at 0.7314, and 6 of 24 hour-groups fall
    # below 90 %. Calibrating within hour-of-day lifts the worst group to 0.8794 and makes the
    # margin vary 2.9x across the day instead of being one number that is simultaneously too
    # tight in some hours and too loose in others. Vovk (2012); see PLAN section 12.7.
    inc_margin, pers_bias, mond, mond_wet, mond_dp = {}, {}, {}, {}, {}
    for N in PLANT_ENVELOPE["notice_h"]:
        r, pers_bias[N] = debiased_persistence_residuals(temp, hour_of_day, N)
        inc_margin[N] = conformal(r)                      # pooled, kept for comparison only
        if N:
            sh = np.empty_like(temp); sh[N:] = temp[:-N]; sh[:N] = temp[0]
            rr = (temp - sh) - pers_bias[N][hour_of_day]
            ok = ~np.isnan(rr); ok[:N] = False
            mond[N] = C.Mondrian(ALPHA).fit(hour_of_day[ok], rr[ok])
            shw = np.empty_like(twb); shw[N:] = twb[:-N]; shw[:N] = twb[0]
            _, bw = debiased_persistence_residuals(twb, hour_of_day, N)
            rw = (twb - shw) - bw[hour_of_day]
            okw = ~np.isnan(rw); okw[:N] = False
            mond_wet[N] = C.Mondrian(ALPHA).fit(hour_of_day[okw], rw[okw])
            shd = np.empty_like(dewp); shd[N:] = dewp[:-N]; shd[:N] = dewp[0]
            _, bd = debiased_persistence_residuals(dewp, hour_of_day, N)
            rd = (dewp - shd) - bd[hour_of_day]
            okd = ~np.isnan(rd); okd[:N] = False
            mond_dp[N] = C.Mondrian(ALPHA).fit(hour_of_day[okd], rd[okd])
            sm = mond[N].summary()
            say("      %d h notice: pooled margin %+.4f C   MONDRIAN %d groups, "
                "%.4f..%.4f C, smallest group n=%s"
                % (N, inc_margin[N]["margin"], sm["n_groups_fitted"],
                   sm["group_q_min"], sm["group_q_max"], format(sm["smallest_group_n"], ",")))
        else:
            mond[N] = mond_wet[N] = mond_dp[N] = None
            say("      0 h notice: no forecast error to bound (the policy reads what it acts on)")
    say("      TWO CHOICES ABOVE BOTH FAVOUR THE INCUMBENT, and are made anyway:")
    say("      (a) its error is de-biased per hour-of-day first (gotcha #25), which hands it the")
    say("          average shape of a day -- a small climatological forecast. It makes the")
    say("          adversary STRONGER, which is the direction an adversary should be wrong in.")
    say("      (b) at 0 h notice its sensor is treated as PERFECT (margin 0.0000 C). A real")
    say("          rooftop sensor reads 0.1-0.5 C off. THAT ASSUMPTION IS THE WHOLE ZERO-NOTICE")
    say("          STORY: backtest.py showed N-56's +67 h/yr tracks the INCUMBENT's buffer, not")
    say("          recirculation -- sensor error 0.1/0.3/0.5 C gives +10.4/+66.8/+162.0 h/yr with")
    say("          the agent's buffer fixed at 0.1945 C. Giving it a perfect sensor here is the")
    say("          conservative choice, and it is why our zero-notice rows are negative.")

    # One flat product over the three per-decision limits, so the scenario loop gains two real
    # axes without another level of nesting. Every combination is computed and shipped; none of
    # these three is a chosen constant.
    gate_limit_grid = [(w, a, l)
                       for w in PLANT_ENVELOPE["dewpoint_limit_c"]
                       for a in PLANT_ENVELOPE["aq_limit_idx"]
                       for l in PLANT_ENVELOPE["limit_c"]]
    say("      swept per-decision limits: %d dew-point limits x %d air-quality limits x "
        "%d changeover limits = %d combinations"
        % (len(PLANT_ENVELOPE["dewpoint_limit_c"]), len(PLANT_ENVELOPE["aq_limit_idx"]),
           len(PLANT_ENVELOPE["limit_c"]), len(gate_limit_grid)))

    day_index = {}
    for i, k in enumerate(keys):
        day_index.setdefault(k[:10], []).append(i)

    results, n_scen = [], 0
    # ---- THE UNANCHORED LEVEL TERM, computed ONCE and SHIPPED ---------------------------------
    # An unanchored agent believes FortyGuard's absolute level, so it inherits that day's measured
    # offset AND needs a conformal margin for how wrong the level can be. The margin is fitted
    # LEAVE-ONE-OUT -- from the other measured days only -- so the agent is never bounded using the
    # day it is being tested on.
    #
    # WHY THIS MOVED OUT OF THE SWEEP AND INTO THE TRACE. It used to be computed inline, four times
    # per case, and shipped nowhere. The browser therefore could not have it, so `decide()` invented
    # its own unanchored construction: ONE fixed worst-magnitude offset for every scenario and no
    # level margin at all. That disagreed with this agent on 2,588 of 8,064 unanchored
    # configurations -- 32.1 % -- and it was invisible because verify_browser_decision.js filtered
    # to `anchor === 'sensor'`. Worse, one constant offset is the exact oracle gotcha #48 records:
    # a single offset across 1,826 days gave +450.9 h/yr where the four rotated gave -156.0.
    # One computation, exported, used by both languages.
    loo_levels = []
    for off_i, o in enumerate(fg_offsets):
        loo = np.array([x["mean_d"] for j, x in enumerate(fg_offsets) if j != off_i], dtype=float)
        cl = conformal(loo)
        loo_levels.append({"date": o["date"], "mean_d": float(o["mean_d"]),
                           "level_margin_c": float(cl["margin"]), "level_n": int(cl["n"]),
                           "level_clamped": bool(cl["clamped"])})
    loo_by_date = {r["date"]: r for r in loo_levels}
    if loo_levels:
        say("\n   THE UNANCHORED LEVEL TERM, leave-one-out, shipped so the browser can reproduce it:")
        for r in loo_levels:
            say("      %s  measured offset %+.4f C   margin from the other %d days %+.4f C%s"
                % (r["date"], r["mean_d"], r["level_n"], r["level_margin_c"],
                   "   [CLAMPED]" if r["level_clamped"] else ""))

    # case -> {bound key -> per-hour upper bound}. Filled by the sweep below, which is the only
    # code that computes the bound, and merged into `series` once `_day_series` has built it.
    bound_series = {}
    for case_i, (name, crit) in enumerate(CASE_SPECS):
        day = picks.get(name)
        if not day:
            continue
        ix = day_index[day]
        t_true = temp[ix]
        b = np.where(np.isnan(drct[ix]), 0.0, drct[ix])
        s_ms = np.maximum(np.where(np.isnan(sknt[ix]), 0.0, sknt[ix]) * 0.514444, 0.3)
        calm = (np.isnan(drct[ix])) | (np.where(np.isnan(sknt[ix]), 0.0, sknt[ix]) < CALM_KT)
        hours = [keys[i][-2:] + ":00" for i in ix]
        ones_h = np.ones(len(t_true), dtype=bool)
        twb_day = twb[ix]                                 # real wet-bulb (kept for reporting)
        dp_day = dewp[ix]                                 # real DEW POINT -- what gate 2 tests
        aq_day = (aq_days[case_i % len(aq_days)][hod_of(ix, keys)] if aq_days else None)

        for mode in PLANT_ENVELOPE["bank_mode"]:
            tab, refused, _ = tabs[mode]
            # THE AGENT DOES NOT KNOW TOMORROW'S WIND DIRECTION. N-40 measured the spread of
            # direction over the lead time at 47-72 deg -- nobody's forecast error, see
            # SIGMA_DIR_DEG -- so the agent's plume estimate is the rise at
            # the FORECAST bearing while the truth is the rise at the bearing that actually
            # occurred. Before this, both used the same bearing -- which handed the agent a
            # perfect plume forecast for free and left the plume term with no uncertainty at all
            # while the temperature term carried a carefully calibrated margin.
            sp_tab, sp_mult, sp_sd, sp_err = plume_uncertainty_terms(mode)
            if sp_sd:
                rng_dir = np.random.default_rng(40)      # named for N-40; deterministic
                b_fcst = (b + rng_dir.normal(0.0, sp_sd, len(b))) % 360.0
            else:
                b_fcst = b
            rise_true = lookup_rise(tab, b, s_ms)        # what actually happens
            rise = lookup_rise(tab, b_fcst, s_ms)        # what the agent can compute
            # A REFUSED bearing's table entry is NOT a small number, it is a MEANINGLESS one --
            # the plume passed straight THROUGH a building that would really have deflected it,
            # so the number is unphysical in an unbounded direction. Refused rows are masked out
            # before any max is taken over bearings, or the calm-hour worst case below would
            # quietly quote a number the agent has already declared it cannot compute.
            ok_rows = np.array([int(bb) not in refused for bb in BEARINGS])
            worst_by_speed = (tab[ok_rows].max(axis=0) if ok_rows.any()
                              else np.full(len(SPEED_GRID_MS), np.nan))
            si = np.abs(np.asarray(SPEED_GRID_MS)[None, :] - s_ms[:, None]).argmin(axis=1)
            # Calm hours have NO DEFINED BEARING (ASOS reports drct = 0 when calm), so the agent
            # does not get to pick one: it takes the worst rise over every bearing it is still
            # allowed to compute. Counted and reported, never silently folded in (N-54 P4).
            rise = np.where(calm, worst_by_speed[si], rise)
            rise_true = np.where(calm, worst_by_speed[si], rise_true)
            # refusal is judged on the bearing the agent BELIEVES, because that is what it has
            ref_flag = np.array([((int(round(x / STEP_DEG) * STEP_DEG) % 360) in refused and not c)
                                 or (c and not ok_rows.any())
                                 for x, c in zip(b_fcst, calm)])
            # the plume term of the bound: multiplier x per-hour ensemble spread (CQR-style).
            # Narrow where the geometry is forgiving, wide where a small direction error swings
            # the plume across the intake -- measured 34.6x variation on this geometry.
            if sp_tab is not None:
                from plume_uncertainty import lookup_spread as _lus
                plume_margin = sp_mult * np.where(calm, np.nanmax(sp_tab), _lus(sp_tab, b_fcst, s_ms))
            else:
                plume_margin = np.zeros(len(t_true))

            truth_intake = t_true + rise_true
            for N in PLANT_ENVELOPE["notice_h"]:
                # THE INCUMBENT sees only what its own rooftop sensor read N hours ago --
                # persistence -- and knows nothing about the plume. Same 90 % machinery.
                hod = np.array([int(h[:2]) for h in hours])
                inc_src = t_true.copy()
                if N:
                    inc_src[N:] = t_true[:-N]
                    inc_src[:N] = t_true[0]          # before the day starts, the last it saw
                    inc_src = inc_src + pers_bias[N][hod]    # its diurnal de-bias, applied
                # Per-hour GROUP-CONDITIONAL margin, not one pooled number. At 3 h notice the
                # pooled quantile leaves hour 9 at 0.7314 coverage while reading 0.9017 overall.
                if N and mond[N] is not None:
                    marg_h = mond[N].q_array(hod)
                else:
                    marg_h = np.zeros(len(t_true))
                ub_inc = inc_src + marg_h

                # the incumbent must clear the humidity gate too -- it has a hygrometer, it just
                # has no forecast and no plume model
                inc_wet = twb_day.copy()
                rw_prime = np.zeros(len(t_true))
                if N:
                    shw = twb_day.copy(); shw[N:] = twb_day[:-N]; shw[:N] = twb_day[0]
                    _, bw_full = debiased_persistence_residuals(twb, hour_of_day, N)
                    inc_wet = shw + bw_full[hod]
                    rw_prime = (twb_day - inc_wet)
                margw_h = (mond_wet[N].q_array(hod) if (N and mond_wet[N] is not None)
                           else np.zeros(len(t_true)))
                ub_wet_inc = inc_wet + margw_h
                # DEW POINT, for gate 2. Bounded with its own group-conditional quantile from the
                # same five-year record, so the humidity gate is calibrated rather than assumed.
                inc_dp = dp_day.copy()
                rdp_prime = np.zeros(len(t_true))
                if N:
                    shd = dp_day.copy(); shd[N:] = dp_day[:-N]; shd[:N] = dp_day[0]
                    _, bd_full = debiased_persistence_residuals(dewp, hour_of_day, N)
                    inc_dp = shd + bd_full[hod]
                    rdp_prime = dp_day - inc_dp
                margdp_h = (mond_dp[N].q_array(hod) if (N and mond_dp[N] is not None)
                            else np.zeros(len(t_true)))
                ub_dp_inc = inc_dp + margdp_h

                # r_prime: the incumbent's DE-BIASED persistence error on THIS day, hour by
                # hour. The anchored agent's error is defined as a fraction (1 - skill) of it,
                # which is what "skill relative to persistence" MEANS. No random draws, no
                # fitted distribution -- these are real KIAD numbers.
                r_prime = np.zeros(len(t_true))
                if N:
                    shifted = t_true.copy()
                    shifted[N:] = t_true[:-N]
                    shifted[:N] = t_true[0]
                    r_prime = (t_true - shifted) - pers_bias[N][hod]

                # A FORECAST GETS TWO THINGS WRONG, AND BOTH ARE SWEPT SEPARATELY.
                #   LEVEL -- the whole-day offset. MEASURED: 4 real FortyGuard values. Removable
                #            by one local reading, which is what `anchor` decides.
                #   SHAPE -- the hour-to-hour profile. UNMEASURED for FortyGuard (we hold one
                #            window per day, not an hourly series), so it is expressed as skill
                #            relative to persistence and SWEPT.
                # An earlier version of this loop gave the unanchored agent a PERFECT SHAPE and
                # only a level error. That is the mirror image of gotcha #40 -- free information
                # dressed as a measurement -- and it flattered the agent. Both errors now apply
                # in both anchor branches.
                for anchor in PLANT_ENVELOPE["anchor"]:
                    offs = (fg_offsets if anchor == "none"
                            else [{"date": "anchored", "mean_d": 0.0}])
                    for off_i, off in enumerate(offs):
                        if anchor == "none":
                            # LEAVE-ONE-OUT, from the table computed once above and SHIPPED, so
                            # this loop and the browser cannot disagree about it.
                            _l = loo_by_date[off["date"]]
                            level_margin = _l["level_margin_c"]
                            level_n, level_clamped = _l["level_n"], _l["level_clamped"]
                        else:
                            level_margin, level_n, level_clamped = 0.0, None, False

                        for skill in FORECAST_SKILL:
                            forecast = t_true - off["mean_d"] - (1.0 - skill) * r_prime
                            # Sum of two one-sided 90 % bounds. By Bonferroni this guarantees
                            # only 1 - 2*alpha = 80 %, not 90 %, and it is WIDER than a bound
                            # fitted jointly -- so it costs the agent hours rather than safety.
                            # Stated because a reader is entitled to know which way it errs.
                            # GROUP-CONDITIONAL, per hour -- `marg_h` is mond[N].q_array(hod).
                            #
                            # BUG FIXED 2026-08-19. This line read
                            #     shape_margin = (1.0 - skill) * inc_margin[N]["margin"]
                            # i.e. the POOLED quantile, while `_day_series` shipped the MONDRIAN
                            # per-hour margin to the browser. The two disagreed by 2.4567 vs
                            # 1.9065 C at hour 23 of the crossing day, so the agent's own
                            # decisions were still being made with a pooled bound even though
                            # every document said group-conditional. Caught by
                            # demo/verify_browser_decision.js, which compares the browser's
                            # hour-by-hour modes against the rows this loop writes -- exactly the
                            # class of error that agreeing unit tests cannot see.
                            shape_margin = (1.0 - skill) * marg_h
                            margin = level_margin + shape_margin
                            m_clamped = bool(level_clamped
                                             or (mond[N].summary()["any_group_clamped"]
                                                 if (N and mond[N] is not None) else False))
                            off_tag, off_c = off["date"], off["mean_d"]

                            ub_agent = forecast + margin + rise + plume_margin
                            # PARK THE BOUND FOR STAGE 5. This loop is the ONLY place the per-hour
                            # bound exists: `_day_series` deliberately ships the browser the INPUTS
                            # and lets it form the bound itself, so re-deriving it for the command
                            # log would be a second code path for one quantity (gotcha #12). It is
                            # stored only at the reference point the log prints, and `series` is
                            # merged with it after `_day_series` has built the dict.
                            if all(ACT_REFERENCE_POINT[k] == v for k, v in
                                   (("bank_mode", mode), ("anchor", anchor),
                                    ("forecast_skill", skill), ("notice_h", N))):
                                bound_series.setdefault(name, {})[
                                    bound_series_key(mode, anchor, off_tag, skill, N)] = [
                                        float(v) for v in ub_agent]
                            # the agent forecasts wet-bulb the same way it forecasts dry-bulb,
                            # and bounds it with its OWN group-conditional quantile
                            ub_wet = (twb_day - (1.0 - skill) * rw_prime
                                      + (1.0 - skill) * margw_h + level_margin)
                            ub_dp = (dp_day - (1.0 - skill) * rdp_prime
                                     + (1.0 - skill) * margdp_h + level_margin)

                            for dp_limit, aq_limit, limit in gate_limit_grid:
                                # GATE 1 of 3 -- DRY BULB, the temperature bound
                                g_dry = ub_agent <= limit
                                # GATE 2 of 3 -- DEW POINT against a PUBLISHED maximum.
                                # Green Grid WP#46 p.6: the ASHRAE recommended maxima are 27 C
                                # dry-bulb and 15 C dew point, and WP46 counts a free-cooling
                                # hour only when BOTH hold. Dew point is read straight from the
                                # station record (100 % coverage), so no psychrometric formula
                                # sits between the measurement and the decision.
                                g_wet = ones_h if dp_limit is None else (ub_dp <= dp_limit)
                                g_wet_i = ones_h if dp_limit is None else (ub_dp_inc <= dp_limit)
                                # GATE 3 of 3 -- CONTAMINATION. Opening a damper raises indoor
                                # particle counts: LBNL measured it at eight real data centres,
                                # and named owner fear of pollutants as the reason free cooling
                                # goes unused. Both policies face it -- outside air is outside
                                # air regardless of who opened the damper.
                                g_aq = (ones_h if (aq_day is None or aq_limit is None)
                                        else (aq_day <= aq_limit))
                                sa = g_dry & g_wet & g_aq & (~ref_flag)
                                si = (ub_inc <= limit) & g_wet_i & g_aq
                                for budget in PLANT_ENVELOPE["switch_budget"]:
                                    for dwell in PLANT_ENVELOPE["min_dwell_h"]:
                                        ma, fa, swa = plan(sa, budget, dwell)
                                        mi, fi, swi, over = reactive_incumbent(si, budget, dwell)
                                        ba = int(sum(1 for h in range(len(ma))
                                                     if ma[h] == MODE_FREE
                                                     and truth_intake[h] > limit))
                                        bi = int(sum(1 for h in range(len(mi))
                                                     if mi[h] == MODE_FREE
                                                     and truth_intake[h] > limit))
                                        n_scen += 1
                                        results.append({
                                            "case": name, "day": day, "bank_mode": mode,
                                            "anchor": anchor, "forecast_skill": skill,
                                            "offset_day": off_tag, "offset_c": round(off_c, 4),
                                            "notice_h": N, "limit_c": limit,
                                            "dewpoint_limit_c": dp_limit,
                                            "aq_limit_idx": aq_limit,
                                            "switch_budget": budget, "min_dwell_h": dwell,
                                            "agent_free_h": fa, "agent_switches": swa,
                                            "agent_breaches": ba,
                                            "incumbent_free_h": fi, "incumbent_switches": swi,
                                            "incumbent_breaches": bi,
                                            "incumbent_budget_exceeded": over,
                                            "delta_free_h": fa - fi,
                                            "agent_modes": "".join(str(x) for x in ma),
                                            "incumbent_modes": "".join(str(x) for x in mi),
                                            "n_refused_h": int(ref_flag.sum()),
                                            "n_calm_h": int(calm.sum()),
                                            # `margin` is now a PER-HOUR array (group-conditional),
                                            # so a single number can only be a summary of it
                                            "margin_mean_c": round(float(np.mean(margin)), 4),
                                            "margin_min_c": round(float(np.min(margin)), 4),
                                            "margin_max_c": round(float(np.max(margin)), 4),
                                            "margin_level_c": round(float(level_margin), 4),
                                            "margin_shape_mean_c": round(float(np.mean(shape_margin)), 4),
                                            "margin_n_level_days": level_n,
                                            "margin_n_shape_hours": inc_margin[N]["n"],
                                            "margin_clamped": m_clamped,
                                            "incumbent_margin_c": round(
                                                inc_margin[N]["margin"], 4),
                                        })

    say("\n   4-5. DECIDE + ACT   %s scenarios planned (case x bank x offset x notice x limit x "
        "budget x dwell)" % format(n_scen, ","))
    if not results:
        say("      no scenarios produced -- check case selection.")
        return None

    # THE POOLED MEAN OVER THIS SWEEP IS NOT A RESULT. It averages across notice periods, and
    # notice is the axis the whole claim lives on: at 0 h notice the incumbent is reading the
    # present, which no forecast can beat. Broken out per axis, and the breakdown comes FIRST.
    dfree = np.array([r["delta_free_h"] for r in results], dtype=float)
    def block(title, keyf, fmt, order=None):
        say("\n      " + title)
        say("      %-22s %8s %10s %12s %11s %11s %11s"
            % ("", "n", "agent h", "incumbent h", "delta h", "agent brch", "inc brch"))
        ks = order if order is not None else sorted({keyf(r) for r in results},
                                                   key=lambda x: (isinstance(x, str), x))
        for k in ks:
            g = [r for r in results if keyf(r) == k]
            if not g:
                continue
            d = [r["delta_free_h"] for r in g]
            se = (statistics.stdev(d) / math.sqrt(len(d))) if len(d) > 1 else 0.0
            say("      %-22s %8s %10.3f %12.3f %+8.3f%s %10d %11d"
                % (fmt % k, format(len(g), ","),
                   statistics.fmean(r["agent_free_h"] for r in g),
                   statistics.fmean(r["incumbent_free_h"] for r in g),
                   statistics.fmean(d), (" +/-%.3f" % (1.96 * se)) if se else "       ",
                   sum(r["agent_breaches"] for r in g),
                   sum(r["incumbent_breaches"] for r in g)))

    block("BY BANK PLACEMENT -- read this FIRST; it dominates every other axis:",
          lambda r: r["bank_mode"], "%s", order=PLANT_ENVELOPE["bank_mode"])
    say("      ^ N-54 P5 SAYS `facing` IS A SENSITIVITY AND NEVER THE HEADLINE, and this table")
    say("        is why. In `facing` mode `path_blocked()` refuses 36 of 36 DOWNWIND bearings --")
    say("        every bearing on which the plume could reach the intake -- so the agent")
    say("        declines to certify almost every hour and falls back to MECHANICAL. It loses")
    say("        hours BY CONSTRUCTION, and that is the refusal guard working exactly as")
    say("        designed (gotcha #26, methodology rule 8: when a guard refuses, do not route")
    say("        around it). A condenser bank does not go on a 50 m end wall. The realistic")
    say("        placement is `longest`, the 123 m facade, and there the agent WINS.")
    say("      ANY POOLED NUMBER ACROSS THESE TWO MODES IS MEANINGLESS. Quote `longest`.")

    say("\n      THE PRIMARY CONFIGURATION -- bank on the realistic 123 m facade:")
    say("      %-22s %8s %10s %12s %11s %11s %11s"
        % ("anchor x notice", "n", "agent h", "incumbent h", "delta h", "agent brch", "inc brch"))
    for anch in PLANT_ENVELOPE["anchor"]:
        for N in PLANT_ENVELOPE["notice_h"]:
            g = [r for r in results
                 if r["bank_mode"] == "longest" and r["anchor"] == anch and r["notice_h"] == N]
            if not g:
                continue
            d = [r["delta_free_h"] for r in g]
            se = (statistics.stdev(d) / math.sqrt(len(d))) if len(d) > 1 else 0.0
            say("      %-22s %8s %10.3f %12.3f %+8.3f +/-%.3f %8d %11d"
                % ("%-8s %d h" % (anch, N), format(len(g), ","),
                   statistics.fmean(r["agent_free_h"] for r in g),
                   statistics.fmean(r["incumbent_free_h"] for r in g),
                   statistics.fmean(d), 1.96 * se,
                   sum(r["agent_breaches"] for r in g),
                   sum(r["incumbent_breaches"] for r in g)))
    say("      ^ Read DOWN each anchor block: the agent's advantage grows monotonically with")
    say("        NOTICE, which is the axis FortyGuard's forecast sells into and the reason the")
    say("        pitch leads with the forecast rather than the physics.")

    block("BY ANCHORING -- what it costs to believe FortyGuard's level as delivered:",
          lambda r: r["anchor"] if r["bank_mode"] == "longest" else None, "%s",
          order=PLANT_ENVELOPE["anchor"])
    say("      ^ `longest` only, since pooling the modes would hide the effect. Unanchored, the")
    say("        agent carries FortyGuard's day-level offset into every decision -- and because a")
    say("        one-sided UPPER bound protects safety rather than efficiency, it cannot un-bias")
    # GOTCHA #67, and it stood in this string for weeks. It used to print "costs about 595 h/yr
    # (+489.7 -> -104.8 h/yr at 3 h notice) while coverage RISES to 0.9865" -- long after the
    # ladder had moved to +405.7 -> -156.0, i.e. a ~562 h/yr step. Those are backtest.py's
    # numbers: agent.py never opens backtest.json AND runs BEFORE it in run_all, so a figure
    # typed here is one no check re-reads and one this module cannot recompute. Teaching it to
    # read the artefact would be worse -- on a rebuild it would read the PREVIOUS run's file and
    # present a stale number as current (gotcha #73's family). So state the DIRECTION, which the
    # table above actually demonstrates, and send the reader to the artefact for the magnitude.
    say("        a warm forecast. The table above carries the DIRECTION; for the five-year")
    say("        MAGNITUDE read the anchored and unanchored rows of `n56_audit` in")
    say("        demo/backtest.json, where audit.py check 6 registers all five with coverage.")
    say("        Dropping the anchor COSTS HOURS while coverage RISES -- the bound stays safe")
    say("        and pays for it in hours.")
    say("        SO THE HOURS CLAIM IS CONDITIONAL and the condition is stated: it wants a level")
    say("        anchor. The 90 % SAFETY guarantee is NOT conditional on hardware -- it needs")
    say("        ~10 calibration days of pure FortyGuard data (HANDOFF 7.3).")

    block("BY NOTICE PERIOD -- the axis FortyGuard's forecast actually sells into:",
          lambda r: r["notice_h"], "%d h", order=PLANT_ENVELOPE["notice_h"])
    say("      ^ 0 h notice is the incumbent reading the PRESENT with a sensor we gave it for")
    say("        free and error-free. Nothing that forecasts can beat that, and nothing here")
    # RETRACTED CLAIM, HANDOFF 2.3 and 6.3. This printed "N-56 puts the zero-notice gain at
    # +67 h/yr, recirculation alone." The registered retraction in audit.py:RETRACTED_CLAIMS is
    # "+67 h/yr from recirculation alone" -- this string said "+67 h/yr, recirculation alone", so
    # it evaded the exact-substring registry BY ONE WORD while asserting the misattribution
    # verbatim. The gain is an uncertainty asymmetry (FortyGuard's forecast error against a
    # customer sensor's), not recirculation. Figure not restated: it is backtest.py's.
    say("        claims to. And the zero-notice gain is NOT recirculation: it is an UNCERTAINTY")
    say("        ASYMMETRY between FortyGuard's forecast error and a customer sensor's, which is")
    say("        why `n56_audit`'s A-rows sweep the sensor error. The plume term contributes part")
    say("        of it -- the B-rows isolate it -- and buys most of the SAFETY, not most of the")
    say("        hours. It buys BOTH; it does not trade one for the other.")

    block("ANCHORED ONLY, by forecast skill vs persistence (swept, never assumed):",
          lambda r: r["forecast_skill"] if r["anchor"] == "sensor" else None,
          "skill %.2f", order=FORECAST_SKILL)
    say("      ^ skill 0.00 is an agent forecasting NO BETTER than 'same as N hours ago'. That")
    say("        it still gains anything at skill 0 is the recirculation term, not the forecast.")

    block("UNANCHORED ONLY, by which MEASURED FortyGuard offset applies that day:",
          lambda r: r["offset_day"] if r["anchor"] == "none" else None, "%s",
          order=[o["date"] for o in fg_offsets])
    say("      ^ THIS IS THE FORECAST BUG, PRICED IN HOURS. 08-16's offset is -3.7127 C, so the")
    say("        forecast ran 3.7 C WARM and an agent that believes it declines hours it could")
    say("        have taken. 08-15's is +0.1520 C -- the ONLY day the forecast ran cool -- so")
    say("        its leave-one-out margin comes from three warm days, is NEGATIVE, and the bound")
    say("        sits UNDER the truth. That is where every agent breach comes from, and it is")
    say("        the same mechanism as N-26's 0.0 %% coverage day. ~10 days is the fix.")

    block("BY CASE, `longest` only -- seven real days, each exercising one behaviour:",
          lambda r: r["case"] if r["bank_mode"] == "longest" else None, "%s",
          order=[c[0] for c in CASE_SPECS])

    say("\n      pooled over the whole sweep (NOT interpretable on its own; printed for audit):")
    say("         mean %+.4f h/day   SE %.4f   n = %s"
        % (dfree.mean(), dfree.std(ddof=1) / math.sqrt(len(dfree)), format(len(dfree), ",")))
    ab = sum(r["agent_breaches"] for r in results)
    ib = sum(r["incumbent_breaches"] for r in results)
    say("      breaches (declared FREE while true intake was over the limit): agent %d, "
        "incumbent %d" % (ab, ib))
    say("      agent switches, mean %.2f/day;  incumbent %.2f/day"
        % (statistics.fmean(r["agent_switches"] for r in results),
           statistics.fmean(r["incumbent_switches"] for r in results)))
    ov = [r for r in results if r["incumbent_budget_exceeded"] > 0]
    say("      scenarios where the INCUMBENT had to break its own switch budget to stay safe:")
    say("         %d of %s (%.1f %%) -- a reactive controller has no horizon, so it cannot"
        % (len(ov), format(len(results), ","), 100.0 * len(ov) / len(results)))
    say("         respect a switch budget and stay safe at once. The agent never did (%d)."
        % sum(1 for r in results if r["agent_switches"] > r["switch_budget"]))
    say("      scenarios where the agent REFUSED at least one hour: %d (%s bank mode is where"
        % (sum(1 for r in results if r["n_refused_h"] > 0), "facing"))
    say("         refusal fires -- 63.1 % of bearings there, 0.0 % on the realistic facade)")
    say("\n      READ THIS BEFORE QUOTING THE MEAN ABOVE. These seven days were SELECTED to")
    say("      exercise seven different behaviours, so they are not a random sample of the year")
    say("      and the mean is NOT an annual rate. The annual rate is N-56's, on all 43,763")
    say("      hours: +67 h/yr at zero notice, +0.1827 h/day, SE 0.0196, 95 % CI")
    say("      [+0.1443, +0.2211], n = 914 days. %s" % extra_note)
    # ---- 5. ACT -------------------------------------------------------------------------
    # The stage that makes this a controller rather than an analysis: a command log a plant
    # could receive, every row carrying the numbers that produced it.
    series = _day_series(picks, day_index, keys, temp, drct, sknt, tabs)
    # The sweep above is the only place the per-hour bound exists, and it ran before this dict did.
    # Attaching it here is what makes stage 5 able to quote a number at all.
    for _name, _extra in bound_series.items():
        if _name in series:
            series[_name].update(_extra)

    # ---- THE DEMO'S INPUTS, not its conclusions -------------------------------------------
    # The page re-runs the agent's decision itself: same DP, same three gates, same margins.
    # So what is shipped is the per-hour INPUTS -- forecast error, group-conditional margins,
    # plume rise, wet-bulb, air quality, refusal -- and the browser forms the bound and plans the
    # schedule. That means moving a control genuinely re-decides rather than replaying a lookup,
    # and every number on screen is reconstructible from these arrays.
    for name, day in picks.items():
        if not day:
            continue
        ix = day_index[day]
        row = series[name]
        t_true = temp[ix]
        hod = np.array([int(h) for h in row["hours"]])
        row["twb_c"] = [float(v) for v in twb[ix]]
        row["dewpoint_c"] = [float(v) for v in dewp[ix]]
        row["rh_pct"] = [round(float(v), 1) for v in rh[ix]]
        ci = list(picks).index(name)
        row["aq_idx"] = ([round(float(v), 1) for v in aq_days[ci % len(aq_days)][hod]]
                         if aq_days else None)
        b = np.where(np.isnan(drct[ix]), 0.0, drct[ix])
        s_ms = np.maximum(np.where(np.isnan(sknt[ix]), 0.0, sknt[ix]) * 0.514444, 0.3)
        calm = (np.isnan(drct[ix])) | (np.where(np.isnan(sknt[ix]), 0.0, sknt[ix]) < CALM_KT)
            # FULL PRECISION, deliberately, on every array the browser uses to REBUILD a
            # decision. Rounding these to 4 dp flipped decisions at exact gate boundaries: on
            # 2023-06-21 the dew-point bound lands on exactly 15.000 against a 15.0 limit, and a
            # 1e-4 rounding difference put the browser on the other side of the tie. Caught by
            # demo/verify_browser_decision.js. Display rounding belongs in the view, never in the
            # numbers a decision is recomputed from.
        for mode in PLANT_ENVELOPE["bank_mode"]:
            tab, refused, _ = tabs[mode]
            ok_rows = np.array([int(bb) not in refused for bb in BEARINGS])
            worst_by_speed = (tab[ok_rows].max(axis=0) if ok_rows.any()
                              else np.full(len(SPEED_GRID_MS), np.nan))
            sidx = np.abs(np.asarray(SPEED_GRID_MS)[None, :] - s_ms[:, None]).argmin(axis=1)
            # The browser must reconstruct EXACTLY what the Python agent decided, so it needs the
            # same split the scenario loop uses: the agent sees the rise at the FORECAST bearing
            # and carries a per-hour plume margin; the truth is the rise at the ACTUAL bearing.
            # Shipping one `rise` array would silently make the demo show decisions never made.
            sp_tab, sp_mult, sp_sd, _e = plume_uncertainty_terms(mode)
            if sp_sd:
                b_f = (b + np.random.default_rng(40).normal(0.0, sp_sd, len(b))) % 360.0
            else:
                b_f = b
            rr_f = np.where(calm, worst_by_speed[sidx], lookup_rise(tab, b_f, s_ms))
            rr_t = np.where(calm, worst_by_speed[sidx], lookup_rise(tab, b, s_ms))
            if sp_tab is not None:
                from plume_uncertainty import lookup_spread as _lus2
                pm = sp_mult * np.where(calm, np.nanmax(sp_tab), _lus2(sp_tab, b_f, s_ms))
            else:
                pm = np.zeros(len(t_true))
            row["rise_c_" + mode] = [float(v) for v in rr_f]                  # agent's estimate
            row["rise_true_c_" + mode] = [float(v) for v in rr_t]             # what happens
            row["plume_margin_c_" + mode] = [float(v) for v in pm]
            row["bearing_forecast_deg_" + mode] = [round(float(v), 1) for v in b_f]
            row["refused_" + mode] = [
                bool(((int(round(x / STEP_DEG) * STEP_DEG) % 360) in refused and not c)
                     or (c and not ok_rows.any())) for x, c in zip(b_f, calm)]
        for N in PLANT_ENVELOPE["notice_h"]:
            if N:
                sh = t_true.copy(); sh[N:] = t_true[:-N]; sh[:N] = t_true[0]
                rp = (t_true - sh) - pers_bias[N][hod]
                shw = twb[ix].copy(); shw[N:] = twb[ix][:-N]; shw[:N] = twb[ix][0]
                _, bw = debiased_persistence_residuals(twb, hour_of_day, N)
                rwp = (twb[ix] - shw) - bw[hod]
                md = mond[N].q_array(hod)
                mw = mond_wet[N].q_array(hod)
            else:
                rp = rwp = md = mw = np.zeros(len(t_true))
            row["r_prime|%d" % N] = [float(v) for v in rp]
            row["rw_prime|%d" % N] = [float(v) for v in rwp]
            row["margin_dry|%d" % N] = [float(v) for v in md]
            row["margin_wet|%d" % N] = [float(v) for v in mw]
            if N:
                shd2 = dewp[ix].copy(); shd2[N:] = dewp[ix][:-N]; shd2[:N] = dewp[ix][0]
                _, bd2 = debiased_persistence_residuals(dewp, hour_of_day, N)
                rdp = (dewp[ix] - shd2) - bd2[hod]
                mdp = mond_dp[N].q_array(hod)
                idp = shd2 + bd2[hod]
            else:
                rdp = mdp = np.zeros(len(t_true)); idp = dewp[ix]
            row["rdp_prime|%d" % N] = [float(v) for v in rdp]
            row["margin_dp|%d" % N] = [float(v) for v in mdp]
            row["incumbent_dp_src|%d" % N] = [float(v) for v in idp]
            row["incumbent_src|%d" % N] = [float(v) for v in
                                           ((sh + pers_bias[N][hod]) if N else t_true)]
            row["incumbent_wet_src|%d" % N] = [float(v) for v in
                                               ((shw + bw[hod]) if N else twb[ix])]

    act_log, example = {}, None
    for name, day in picks.items():
        if not day:
            continue
        row = series[name]
        for r in results:
            if r["case"] != name or r["bank_mode"] != "longest":
                continue
            # one fully-labelled point per case for the command log; the demo can move every
            # axis, and the label below says exactly which point this is. The point is named in
            # ACT_REFERENCE_POINT so that this filter and the sweep's bound capture cannot drift.
            if any(r[k] != v for k, v in ACT_REFERENCE_POINT.items()):
                continue
            key = "%s@limit%.0f" % (name, r["limit_c"])
            modes = [int(x) for x in r["agent_modes"]]
            rise = row["rise_c_longest"]
            bkey = bound_series_key(r["bank_mode"], r["anchor"], r["offset_day"],
                                    r["forecast_skill"], r["notice_h"])
            # NO DEFAULT. A missing bound must fail the build: the previous
            # `row.get(bkey) or [None] * len(modes)` is precisely how stage 5 shipped `nan` in
            # every one of its 37 command rows without a single test noticing.
            if bkey not in row:
                raise RuntimeError(
                    "stage 5 has no per-hour bound under %r -- the scenario sweep must park it "
                    "(see bound_series_key). Refusing to emit a command log with no numbers."
                    % bkey)
            bound = row[bkey]
            act_log[key] = {
                "configuration": {k: r[k] for k in ("bank_mode", "anchor", "forecast_skill",
                                                    "notice_h", "limit_c", "switch_budget",
                                                    "min_dwell_h")},
                "day": day,
                "commands": bms_commands(modes, row["hours"], bound,
                                         r["limit_c"], rise,
                                         row.get("refused_longest", [False] * len(modes)),
                                         {"margin": r["margin_mean_c"],
                                          "level_c": r["margin_level_c"],
                                          "shape_c": r["margin_shape_mean_c"],
                                          "n_level": r["margin_n_level_days"],
                                          "n_shape": r["margin_n_shape_hours"],
                                          "clamped": r["margin_clamped"]})}
            if example is None:
                example = key
    if example:
        say("\n   5. ACT   example command log -- ONE point in the sweep, named in full:")
        cfg = act_log[example]["configuration"]
        say("      case %s, %s   %s" % (example, act_log[example]["day"],
                                        "  ".join("%s=%s" % (k, v) for k, v in cfg.items())))
        for c in act_log[example]["commands"]:
            say("      %s  ->  %-12s  %s" % (c["hour"], c["command"], c["reason"][:96]))
        say("      (%d command rows across %d case/limit combinations are in the trace)"
            % (sum(len(v["commands"]) for v in act_log.values()), len(act_log)))

    # HOW OFTEN THE HONEST ANSWER IS "NO", counted over every scenario rather than asserted.
    # 43.7 % of the sweep declares ZERO free-cooling hours -- on a 35 C July day at an 18 C
    # changeover limit that is simply correct, but a viewer who lands on one of those
    # configurations sees a schedule of solid MECHANICAL and reads it as a broken agent. The demo
    # needs the number in order to say "this is one of the 43.7 %, and here is why", so it is
    # computed here from the same rows the sweep produced.
    n_all = len(results)
    n_zero = sum(1 for r in results if r["agent_free_h"] == 0)
    by_limit = {}
    for r in results:
        b = by_limit.setdefault(str(r["limit_c"]), [0, 0])
        b[1] += 1
        b[0] += int(r["agent_free_h"] == 0)
    say("\n   HOW OFTEN THE AGENT CORRECTLY REFUSES ALL DAY: %s of %s scenarios (%.1f %%)"
        % (format(n_zero, ","), format(n_all, ","), 100.0 * n_zero / max(1, n_all)))
    say("      by changeover limit: " + "  ".join(
        "%s C %.0f%%" % (k, 100.0 * v[0] / v[1]) for k, v in sorted(by_limit.items(),
                                                                    key=lambda kv: float(kv[0]))))
    say("      That is physics, not inertia -- but the interface has to SAY so, or an all-mechanical")
    say("      day reads as an agent doing nothing. See demo/index.html drawZeroNote().")

    # `.format` on EVERY criterion, not just the one with a placeholder: a criterion that gains a
    # site-specific number later then cannot be added without it being filled, and the ones without
    # placeholders are unaffected (none contains a brace -- asserted below).
    return {"cases": [{"name": n, "criterion": case_criterion(c, worst_bearing),
                       "day": picks.get(n)} for n, c in CASE_SPECS],
            "worst_rise_c": worst_rise, "worst_bearing_deg": worst_bearing,
            "incumbent_margin": {str(k): v for k, v in inc_margin.items()},
            "scenarios": results,
            "all_mechanical": {"n_zero": n_zero, "n_total": n_all,
                               "fraction": n_zero / max(1, n_all),
                               "by_limit_c": {k: v[0] / v[1] for k, v in by_limit.items()}},
            "act_log": act_log,
            # The unanchored level term, so the browser mirrors this agent instead of improvising.
            "fg_offsets": loo_levels,
            "day_series": series}


def _day_series(picks, day_index, keys, temp, drct, sknt, tabs):
    """The hourly series behind each case, so the demo can draw exactly what was decided."""
    out = {}
    for name, day in picks.items():
        if not day:
            continue
        ix = day_index[day]
        row = {"day": day,
               "hours": [keys[i][-2:] for i in ix],
               "temp_c": [None if np.isnan(temp[i]) else float(temp[i]) for i in ix],
               "wind_from_deg": [None if np.isnan(drct[i]) else round(float(drct[i]), 1) for i in ix],
               "wind_kt": [None if np.isnan(sknt[i]) else round(float(sknt[i]), 1) for i in ix]}
        for mode in tabs:
            tab = tabs[mode][0]
            b = np.where(np.isnan(drct[ix]), 0.0, drct[ix])
            s_ms = np.maximum(np.where(np.isnan(sknt[ix]), 0.0, sknt[ix]) * 0.514444, 0.3)
            # full precision: this array is one the browser rebuilds decisions from
            row["rise_c_" + mode] = [float(v) for v in lookup_rise(tab, b, s_ms)]
        out[name] = row
    return out


# ============================================================================
# TRACE -- the demo's only input
# ============================================================================
def export_field(tag, out_name):
    """One FortyGuard field, compacted for a browser.

    All 17,862 tiles share ONE quad shape to within 1e-8 degrees (verified), so the file
    carries that shape once plus a centroid and a temperature per tile: ~0.5 MB instead of
    the 7.4 MB raw response, with no loss of what is drawn.
    """
    r = load_fixture(tag)
    if not r:
        return None
    feats = r["map_data"]["features"]
    c0 = feats[0]["geometry"]["coordinates"][0][:4]
    la0 = sum(x[1] for x in c0) / 4.0
    lo0 = sum(x[0] for x in c0) / 4.0
    quad = [[round(x[0] - lo0, 8), round(x[1] - la0, 8)] for x in c0]
    tiles, tmin, tmax = [], 1e9, -1e9
    for la, lo, v in tile_centroids(r):
        tiles.append([round(la, 6), round(lo, 6), round(v, 3)])
        tmin, tmax = min(tmin, v), max(tmax, v)
    obj = {"tag": tag, "n_tiles": len(tiles), "quad_offsets_deg": quad,
           "t_min": round(tmin, 3), "t_max": round(tmax, 3),
           "stats_from_fortyguard": r.get("stats_data", {}).get("temperature_stats"),
           "tiles": tiles}
    os.makedirs(DEMO, exist_ok=True)
    p = os.path.join(DEMO, out_name)
    json.dump(obj, open(p, "w", encoding="utf-8"), allow_nan=False)
    say("      %-28s %s tiles -> %s (%.1f KB)"
        % (tag, format(len(tiles), ","), out_name, os.path.getsize(p) / 1024.0))
    return {"file": out_name, "n_tiles": len(tiles), "t_min": obj["t_min"], "t_max": obj["t_max"]}


def check_physics_not_drifted():
    """The shipped tree carries its own copy of the physics. Copies drift silently, so compare."""
    import hashlib
    out = {}
    for f in ("solver.py", "warp_solver.py"):
        a = os.path.join(HERE, "physics", f)
        b = os.path.join(ROOT, "testing", f)
        ha = hashlib.md5(open(a, "rb").read()).hexdigest()
        hb = hashlib.md5(open(b, "rb").read()).hexdigest() if os.path.exists(b) else None
        out[f] = {"shipped_md5": ha, "research_md5": hb, "identical": ha == hb}
        if hb and ha != hb:
            say("   *** WARNING: %s has DRIFTED from testing/%s. Numbers may not reproduce. ***"
                % (f, f))
    return out


def run_all():
    t0 = time.time()
    banner("AGENTIC-ARBITER   the agent loop, end to end, on saved data.  ZERO API CALLS.")
    # COMPUTED, not typed. These four literals described Ashburn and were printed for whatever
    # metro was running -- the same defect as the "595 h/year" literal in the view (gotcha #67).
    _sel = json.load(open(M.geom_path("selected_site.json"), encoding="utf-8"))["selected"]
    say("   metro          : %s  (station K%s)" % (M.metro()["label"], M.metro()["station"]))
    say("   committed site : OSM %s -> %s, %s / %s, %.6f %.6f"
        % (_sel["source_osm_id"], _sel["receptor_osm_id"],
           _sel.get("source_name") or "?", _sel.get("receptor_name") or "?",
           SITE_CENTRE[0], SITE_CENTRE[1]))
    say("   plant envelope : every decision-changing number is swept, none is chosen --")
    for k, v in PLANT_ENVELOPE.items():
        say("                    %-14s %s" % (k, v))
    say("   alpha          : %.2f  (the confidence level; a definition, not a tuning knob)" % ALPHA)
    drift = check_physics_not_drifted()
    say("   physics copies : %s"
        % ("identical to the research tree" if all(d["identical"] for d in drift.values())
           else "DRIFTED -- see warning above"))

    cyc = run_cycle()
    offsets = [{"date": p["date"], "mean_d": p["mean_d"]} for p in cyc["pairs"]] if cyc else []
    cas = run_cases(offsets)

    banner("EXPORT   the demo's only input")
    os.makedirs(DEMO, exist_ok=True)
    # ---- WHICH FORTYGUARD FIELD THIS SITE SHIPS, and it is no longer Ashburn's by default -------
    # 🔴 THIS EXPORTED ASHBURN'S EIGHT PAIR FIELDS INTO EVERY SITE'S TRACE UNTIL 2026-08-21. The
    # demo's "Screen zero -- FortyGuard's field" panel reads `T.fields`, so selecting Chicago
    # displayed a heatmap of LOUDOUN COUNTY, VIRGINIA. It was labelled -- the note said the site had
    # no field of its own -- and for Chicago that label was itself WRONG: one past-window heatmap
    # was purchased for Chicago on 2026-08-19, 17,797 tiles, 4,220 credits, and it sat unused in
    # `testing/results/fixtures/` while the page showed Ashburn's and claimed Chicago had none.
    # `metros.py`'s own docstring already required this: *"the interface must say plainly that no
    # FortyGuard field was purchased for it rather than borrowing another site's."* The intent was
    # right and the implementation had drifted from it.
    # Three cases, from the registry, never from a fallback:
    fields = {}
    m_fg = M.metro()
    if cyc and m_fg.get("fortyguard_day_pairs"):
        # (1) MEASURED DAY-PAIRS of its own -- a forecast leg and its elapsed outcome. Ashburn only.
        for p in cyc["pairs"]:
            fields[p["date"] + "_forecast"] = export_field(p["forecast_tag"],
                                                           "field_%s_forecast.json" % p["date"])
            fields[p["date"] + "_outcome"] = export_field(p["outcome_tag"],
                                                          "field_%s_outcome.json" % p["date"])
    elif m_fg.get("fortyguard_field_fixture"):
        # (2) ONE PURCHASED PAST WINDOW. Real, this site's own, and NOT a pair: it carries no
        # forecast leg, so it buys the spatial statistics and the screen-zero visual and cannot buy
        # a level offset or a coverage record. The key is named for what it is, so no reader can
        # mistake it for a pair.
        got = export_field(m_fg["fortyguard_field_fixture"],
                           "field_%s_observed.json" % M.metro_key())
        if got:
            fields["observed_past_window"] = got
            say("      this site's OWN purchased field: %s tiles (one past window, not a pair)"
                % format(got["n_tiles"], ","))
    else:
        # (3) NOTHING PURCHASED. Ship nothing. An empty block is a true statement; another site's
        # field is not, however carefully it is labelled.
        say("      no FortyGuard field was purchased for %s, so NONE is shipped -- the panel says"
            % m_fg["label"])
        say("      so. Borrowing Ashburn's here is what this used to do and it is what the registry"
            " docstring already forbade.")
    dtab = json.load(open(M.geom_path("direction_table.json"), encoding="utf-8"))
    site_geom = {m: json.load(open(M.geom_path("solver_site_%s.json" % m), encoding="utf-8"))
                 for m in PLANT_ENVELOPE["bank_mode"]}
    # WHO THIS PLANT IS, read from the file `commit_site.py` wrote. The trace used to name Ashburn's
    # two AWS halls regardless of the metro -- see the `site` block below.
    _committed = json.load(open(M.geom_path("selected_site.json"), encoding="utf-8"))

    trace = {
        "generated_by": "AGENTIC-ARBITER/src/agent.py",
        "api_calls_made": 0,
        # WHICH SITE THIS IS, and what is genuinely its own versus borrowed. Without this block a
        # reader cannot tell a Chicago trace from an Ashburn one, and the site picker would imply
        # more independence than the data has.
        "metro": {
            "key": M.metro_key(), "label": M.metro()["label"],
            "station": "K" + M.metro()["station"], "tz": M.metro()["tz"],
            "climate_note": M.metro().get("climate_note"),
        },
        "weather": {"file": os.path.basename(M.weather_path()),
                    "station": "K" + M.metro()["station"],
                    "n_hours": len(load_hours()[0])},
        # 🔴 THE HONEST LIMIT OF A NON-ASHBURN RUN. Weather and geometry are this site's own. The
        # four MEASURED FortyGuard level offsets are not: only Ashburn has forecast/outcome day
        # pairs (Chicago holds one past-window field, Dulles none), so the level term and the N-26
        # coverage record are Ashburn's, applied here. That is an approximation, it is stated, and
        # it is the reason `run_cycle`'s coverage numbers must not be quoted as this site's.
        "fortyguard_provenance": {
            "own_measured_day_pairs": M.metro_key() == M.DEFAULT_METRO,
            "level_offsets_measured_at": M.DEFAULT_METRO,
            "note": ("weather and geometry are this site's own; the four measured FortyGuard level "
                     "offsets and the N-26 coverage record are Ashburn's, because only Ashburn has "
                     "forecast/outcome day pairs. Quote the hours for this site; quote the "
                     "coverage for Ashburn."
                     if M.metro_key() != M.DEFAULT_METRO else
                     "this site's own measured FortyGuard forecast/outcome day pairs"),
        },
        # 🔴 THESE THREE WERE ASHBURN LITERALS, IN EVERY SITE'S TRACE, UNTIL 2026-08-21.
        # `osm_source: 744496750`, `osm_receptor: 744496741` and the operator string "Amazon Web
        # Services IAD116 / IAD117" were typed here, so Chicago's trace identified its plant as a
        # pair of AWS halls in Virginia -- and `report.py` prints the OSM pair straight onto page 1
        # of the downloadable PDF. Found by walking every leaf of the three traces and reporting the
        # ones that agreed: two OSM ids that are identical across three different metros cannot be
        # right, and no test compared them because none had been asked to.
        # They are read from the same `*_selected_site.json` that `commit_site.py` wrote and that
        # `metros.export_manifest()` reads, so there is one source of truth for who this plant is.
        "site": {"centre": list(SITE_CENTRE),
                 "osm_source": _committed["source_building"]["osm_id"],
                 "osm_receptor": _committed["receptor_building"]["osm_id"],
                 # ONE BUILDING GETS ONE NAME. The pair form ("A / B") rendered as
                 # "Apple / unnamed" for a standalone facility, and this string is printed on page 1
                 # of the downloadable PDF as the reader's check that they are looking at the right
                 # plant -- so a phantom second hall in it is worse than cosmetic.
                 # 🔴 "unnamed" IS NOT AN IDENTIFIER, AND FOUR FACILITIES WERE SHARING IT.
                 # The fallback for a building with no OSM `name` tag was the bare word "unnamed",
                 # so AL_way_1540172608, IA_way_191655977, NC_way_844372538 and WI_way_1510420026
                 # all published `operator: "unnamed"` -- and audit.py's identity check reads
                 # equality here as proof of an Ashburn-style fallback, which is exactly what it
                 # was. Its own premise names the remedy: "two different buildings cannot share an
                 # OSM id". So an unnamed building is identified by its way id, which is real,
                 # unique, and something a reader can actually look up -- and it is printed on page
                 # 1 of the PDF, where "unnamed" told them nothing at all.
                 # This is `buildingOf()` from demo/index.html, in Python: one convention for
                 # "who is this building", in both languages, rather than two that drift.
                 "operator": ("%s / %s" % (_building_label(_committed["source_building"]),
                                           _building_label(_committed["receptor_building"]))
                              if _committed["receptor_building"].get("osm_id") is not None
                              else _building_label(_committed["source_building"])),
                 "facade_gap_m": site_geom["longest"]["facade_gap_m"],
                 # 🔴 `bank_length_m` AND `facade_length_m` ARE PUBLISHED BECAUSE THE PAGE WAS
                 # ASSERTING THEM AS LITERALS. `demo/index.html`'s wind-dial note read "The
                 # realistic placement -- a 123 m facade" and "a 50 m end wall" on EVERY site, and
                 # measured 2026-08-24 the real facades are 162.5 m (Ashburn), 200.0 (Chicago),
                 # 293.8 (Dulles) and 337.5 (the first national facility) -- so 123 m was wrong for
                 # all four, including the site it was presumably typed from. "50 m end wall" was
                 # Ashburn's BANK length described as a wall, which is a different quantity again.
                 # Sixth instance of gotcha #67, and rendered. Derived here, in Python, from the
                 # rasterised bank area and the two ASSUMED constants that produced it, so the page
                 # prints a number instead of owning one.
                 "geometry": {m: dict(
                     {k: site_geom[m][k] for k in
                      ("domain", "source_ring_m", "receptor_ring_m", "bank_ring_m",
                       "source_centre_m", "receptor_centre_m", "intake_m",
                       "intake_radius_m", "bank_cells", "bank_area_m2", "bank_mode")},
                     bank_length_m=round(site_geom[m]["bank_area_m2"] / BANK_DEPTH_M, 1),
                     facade_length_m=round(site_geom[m]["bank_area_m2"]
                                           / BANK_DEPTH_M / BANK_FACADE_FRACTION, 1))
                     for m in site_geom}},
        "plant_envelope": PLANT_ENVELOPE,
        "alpha": ALPHA,
        "physics_provenance": {
            "validation": {"vs_analytic_gaussian_plume": 2.9e-10, "heat_conservation": 7.5e-12,
                           "prairie_grass_1956_experiments": 67,
                           "held_out_rms_k": 0.126, "held_out_signal_k": 0.923},
            "calibrated_constants": CALIBRATED,
            "known_defect": ("buildings are TRANSPARENT to the temperature field -- N-29 V4 "
                             "measures 0.0 % of plume heat absorbed, so heat is conserved exactly, "
                             "but a transparent building cannot deflect a plume that really would "
                             "be deflected. The agent therefore REFUSES on any bearing where a "
                             "building lies on the source-to-intake path rather than quote a rise "
                             "it cannot stand behind (gotcha #26). This field asserted the "
                             "RETRACTED heat-absorption claim until 2026-08-20; nothing rendered "
                             "it, but it shipped in trace.json for eight days"),
            "retracted_claims_in_this_field": [
                "buildings absorb heat rather than deflect it -- FALSE since 2026-08-12, measured "
                "0.0 % absorbed by N-29 V4"],
            "source_copies": drift},
        "cycle": cyc,
        "cases": cas,
        "fields": fields,
        # `u_median_ms` IS COPIED THROUGH from 2026-08-21, and it is not decoration: it is the wind
        # speed every row in `rows` and every one of the 72 RENDERED plume fields was solved at. It
        # was Ashburn's on all three sites until that day, and the trace could not have shown it,
        # because the trace did not carry it. `audit.check_wind_is_this_sites_own()` joins it to the
        # shipped field's own `wind_speed_ms` -- a number you cannot check without publishing it.
        "direction_table": {"parameters": dtab["parameters"], "wind": dtab["wind"],
                            "modes": {m: {"rows": dtab["modes"][m]["rows"],
                                          "worst": dtab["modes"][m]["worst"],
                                          "u_median_ms": dtab["modes"][m].get("u_median_ms"),
                                          "n_refused": dtab["modes"][m]["n_refused"],
                                          "n_downwind": dtab["modes"][m]["n_downwind"],
                                          "n_downwind_refused": dtab["modes"][m]["n_downwind_refused"],
                                          "wind_weighted": dtab["modes"][m]["wind_weighted"]}
                                      for m in dtab["modes"]}},
        "standing_results_quoted_elsewhere": {
            # WHERE THESE WERE MEASURED, stated in the block rather than implied by the file it
            # sits in. Every figure below is a cross-reference to an earlier experiment, and all of
            # the SITE-dependent ones were run at Ashburn -- so carrying them unlabelled inside a
            # Chicago trace invites exactly the reading this project has spent two days removing.
            # The Warp figures are the exception and are marked as such: a GPU speed-up is a
            # property of this machine, not of a data centre.
            "measured_at": M.DEFAULT_METRO,
            "measured_at_note": ("these are standing results from earlier experiments, all run on "
                                 "the Ashburn site. They are quoted here for reference and are NOT "
                                 "this site's measurements unless this site IS Ashburn. The "
                                 "warp_speedup figures are hardware, not site, and apply anywhere."),
            "is_this_sites_own": M.metro_key() == M.DEFAULT_METRO,
            "n56_free_cooling_floor_h_per_year": 67,
            "n56_paired_per_day_h": {"mean": 0.1827, "se": 0.0196,
                                     "ci95": [0.1443, 0.2211], "n_days": 914},
            "n26_pooled_coverage": 0.655898928824693,
            "n26_verdict": "FAIL against pre-registered P1/P2",
            "warp_speedup_x": {"headline_repeat": 72.7, "best_repeat": 93.46,
                               "cpu_gpu_agreement_c": 6.95e-5},
            "forecast_skill_vs_persistence": {"1.49h": 0.146, "3.49h": 0.617, "5.49h": 0.770,
                                              "7.49h": 0.777, "9.41h": 0.838},
            # THE SAME MEASUREMENT WITH THE LEVEL OFFSET REMOVED, which is what one on-site reading
            # does. DIAG-57 subtracts the day's mean error and re-scores against persistence:
            # at the 3.49 h lead the agent runs on, RMSE falls 1.253 -> 0.125 C and skill goes
            # 0.617 -> 0.962. It was measured in testing/results/diag57_forecastskill.json and the
            # demo never loaded that file, so the strongest FortyGuard figure in the project was
            # invisible on the page. Carried here because this block is exactly what it is for:
            # standing results measured elsewhere and quoted with their provenance.
            # ⚠ ONE DAY, like every DIAG-57 row. The caveat travels with it.
            "forecast_skill_after_anchoring": {"1.49h": 0.923, "3.49h": 0.962, "5.49h": 0.980,
                                               "7.49h": 0.982, "9.41h": 0.983},
            "forecast_skill_source": ("DIAG-57, one day, 17,862 tiles per lead. `after_anchoring` "
                                      "removes the day's single level offset -- what one on-site "
                                      "reading does -- and rescores against persistence."),
            "no_dollars_or_kwh": ("the C-to-kWh conversion could not be sourced from a primary "
                                  "document, so the unit is chiller-hours avoided"),
        },
        "runtime_seconds": None,
    }
    # The full sweep is thousands of rows. It goes in its own file so the page paints before it
    # arrives -- but it is SHIPPED IN FULL, because "we swept it" is only checkable if you can
    # read every row.
    if cas and cas.get("scenarios"):
        # 🔴 THE SWEEP RUNS FOR EVERY SITE; THE 31 MB DUMP DOES NOT, AND THAT IS A SCALE DECISION.
        # scenarios.json has exactly ONE consumer in the tree: demo/verify_browser_decision.js,
        # which opens `__dirname + '/scenarios.json'` -- the UNSUFFIXED reference file, on every
        # run. index.html never names it, audit.py never opens it, and nothing reads
        # artefacts["scenarios"] out of the manifest. So chicago_scenarios.json and
        # dulles_scenarios.json were 61.9 MB shipped on no code path at all.
        # At three sites that is untidy. At national scale it is decisive: ~31 MB per site against
        # a repo that must stay publishable on GitHub, where the whole rest of a site's artefacts
        # come to ~5 MB. Writing it for every site would put a 100-site build past 3 GB.
        # WHAT IS NOT REDUCED: the sweep itself still runs in full for every site, so
        # trace["cases"]["summary"] and every audited number are computed from all 120,960 rows.
        # Only the row dump is skipped, and only where nothing reads it.
        # Force it anywhere with WRITE_SCENARIOS=1 -- the cross-language test needs exactly one.
        is_reference = M.metro_key() == M.DEFAULT_METRO
        want_dump = is_reference or os.environ.get("WRITE_SCENARIOS") == "1"
        trace["cases"] = dict(cas)
        trace["cases"]["summary"] = _summarise(cas["scenarios"])
        if want_dump:
            sp = M.demo_path("scenarios.json")
            # COLUMNAR, not a list of objects. Repeating 24 key names 40,320 times costs ~18 MB of
            # nothing. Same rows, same fidelity, ~4x smaller: `columns` names the fields and `rows`
            # holds one array per scenario in that order.
            cols = list(cas["scenarios"][0].keys())
            json.dump({"n": len(cas["scenarios"]),
                       "swept_axes": list(PLANT_ENVELOPE.keys()) + ["forecast_skill", "case",
                                                                    "fortyguard_offset_day"],
                       "forecast_skill_grid": FORECAST_SKILL,
                       "columns": cols,
                       "rows": [[r[c] for c in cols] for r in cas["scenarios"]]},
                      open(sp, "w", encoding="utf-8"), default=_jsonable, allow_nan=False)
            say("      %-28s %s rows x %d cols -> %s (%.1f KB)"
                % ("the full plant-envelope sweep", format(len(cas["scenarios"]), ","), len(cols),
                   os.path.basename(sp), os.path.getsize(sp) / 1024.0))
            # NAME THE FILE THAT WAS ACTUALLY WRITTEN. This said "scenarios.json" unconditionally,
            # so every non-reference site's trace pointed a reader at ASHBURN's file -- gotcha
            # #133's family, one field over.
            trace["cases"]["scenarios"] = {"in_file": os.path.basename(sp),
                                           "n": len(cas["scenarios"])}
        else:
            say("      %-28s %s rows swept, dump skipped (read by nothing for this site)"
                % ("the full plant-envelope sweep", format(len(cas["scenarios"]), ",")))
            trace["cases"]["scenarios"] = {
                "in_file": None,
                "n": len(cas["scenarios"]),
                "not_shipped_because": (
                    "the row dump has one consumer, verify_browser_decision.js, and it reads the "
                    "reference site's file only. The sweep RAN in full and this trace's summary is "
                    "computed from all of it; re-emit with WRITE_SCENARIOS=1."),
            }

    trace["runtime_seconds"] = round(time.time() - t0, 2)

    p = M.demo_path("trace.json")
    json.dump(json_safe(trace), open(p, "w", encoding="utf-8"), default=_jsonable, allow_nan=False)
    say("      %-28s -> %s (%.1f KB)"
        % ("the whole loop", os.path.basename(p), os.path.getsize(p) / 1024.0))
    say("\n   DONE in %.1f s. Zero API calls. Every number above traces to a saved response,"
        % trace["runtime_seconds"])
    say("   a committed geometry file, or %s real weather records from K%s."
        % (format(trace["weather"]["n_hours"], ","), M.metro()["station"]))
    return 0


def _summarise(rows):
    """Marginal summaries along each swept axis. A single mean over the whole sweep would be
    meaningless -- it averages across incomparable plant settings -- so nothing is collapsed
    below the axis level, and n is carried on every line.
    """
    out = {}
    for axis in ("case", "bank_mode", "anchor", "forecast_skill", "limit_c", "notice_h",
                 "switch_budget", "min_dwell_h", "offset_day"):
        g = {}
        for r in rows:
            g.setdefault(r[axis], []).append(r)
        out[axis] = []
        for k in sorted(g, key=lambda x: (isinstance(x, str), x)):
            v = g[k]
            d = [x["delta_free_h"] for x in v]
            out[axis].append({
                "value": k, "n": len(v),
                "agent_free_h": round(statistics.fmean(x["agent_free_h"] for x in v), 3),
                "incumbent_free_h": round(statistics.fmean(x["incumbent_free_h"] for x in v), 3),
                "delta_free_h_mean": round(statistics.fmean(d), 4),
                "delta_free_h_se": (round(statistics.stdev(d) / math.sqrt(len(d)), 4)
                                    if len(d) > 1 else None),
                "agent_breaches": sum(x["agent_breaches"] for x in v),
                "incumbent_breaches": sum(x["incumbent_breaches"] for x in v),
                "refused_hours": sum(x["n_refused_h"] for x in v),
                "incumbent_budget_exceeded": sum(x["incumbent_budget_exceeded"] for x in v),
            })
    return out


def json_safe(o):
    """Recursively replace NaN / +-Infinity with None so the output is VALID STANDARD JSON.

    THE BUG THIS FIXES, because it is a good one. `json.dump` happily writes bare `NaN` and
    `Infinity`. Python's own `json.load` reads them back, so a Python-side validator sees nothing
    wrong -- but they are NOT legal JSON, and a browser's `JSON.parse` rejects the whole file with
    `Unexpected token 'N'`. The demo failed to load with every data path individually verified,
    and only rendering the page in a real browser surfaced it.

    Everything written from here passes `allow_nan=False` as well, so a future NaN raises at write
    time instead of silently shipping a file no browser can read.
    """
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [json_safe(v) for v in o]
    if isinstance(o, np.floating):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return json_safe(o.tolist())
    return o


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError("not JSON serialisable: %r" % type(o))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "cycle":
        run_cycle()
    elif cmd == "cases":
        c = run_cycle()
        run_cases([{"date": p["date"], "mean_d": p["mean_d"]} for p in c["pairs"]] if c else [])
    else:
        sys.exit(run_all())
