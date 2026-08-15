# FortyGuard API — Day-1 Data-Check Results

**Run by:** Aashan Javed
**Date:** 2026-07-30
**Method:** live calls to `https://api.fortyguard.com/v1` (+ OpenAPI spec at `/openapi.json`), auth header `api-key`. Async submit → poll `GET /v1/status/{id}`. Sites: Ashburn VA (39.0438, -77.4874), Phoenix-Goodyear AZ (33.4353, -112.3576), Hillsboro OR (45.5229, -122.9898). Raw responses captured in `results_raw.json`.

Reporting format per the checklist. Priority checks first (Z-1, A-3+S-1, S-3, S-7, B-1, B-5, E-8/F-1, B-6, B-8, C-2), then the rest.

---

## TL;DR — the four questions

| Question | Answer | Evidence |
|---|---|---|
| **Can I afford the field design at all?** | **NO, not as specified.** Heatmap = **4,220 credits/call**, ~37× the Z-4 ceiling of 115. Hourly 3-site field design needs ~20M credits vs a 1M pool. | A-3/S-1, A-7 |
| **Does σ_spatial exist?** | **YES, verified.** `stats_data.temperature_stats.standard_deviation` is the spatial stddev across tiles; matches my own tile computation to 4 dp. | S-3 ⭐ |
| **Is the future value real, and the right variable?** | Right **variable** (air temp, not LST — B-6 ✅). Future timestamps accepted (B-1 ✅). "Genuine forecast" only **partially** shown (B-5 needs collection). One landmine: the `temperature` input is **vestigial** (B-4). | B-1, B-5, B-6, B-4, E-8 |
| **When can conformal start, and against what?** | **No forecast archive** (Z-1 ❌) → must collect live from day 1. | Z-1 |

**Biggest surprises:** (1) heatmap cost is ~37× the planning ceiling — the #1 project risk is realised and severe; (2) `filter_type=4` (range up to a **month**) exists — a gift for A1, beyond the doc's assumed 1/2/3; (3) the `temperature` input to `env_params` does nothing to the outputs.

---

## PRIORITY CHECKS

---

```
CHECK ID:        Z-1  (B-CODE)
ASSUMPTION:      C5.1 — a forecast archive exists (a second, issuance-time concept)
WHAT I SENT:     Enumerated every time field in every request schema of the live OpenAPI
                 spec (api.fortyguard.com/openapi.json).
HTTP STATUS:     200 (spec fetched)
RAW RESPONSE:    DateTimeRange.properties = [start_date, end_date, start_time, end_time, filter_type]
                 Scan for issued_at / reference_time / run_time / as_of / model_run / version
                 across ALL component schemas => NONE.
VERDICT:         FAIL (expected)
WHAT I NOTICED:  Exactly one time concept. No way to ask "what did you predict for T, as of an
                 earlier issuance." The forecast archive does not exist -> the calibration set can
                 only be as long as the time since the collector starts. This is the single biggest
                 schedule constraint; the collector must start on day 1. filter_type description in
                 the spec: "1=single hour, 2=range of hours, 3=single day, 4=range of days
                 (week/month, <=1 month)".
```

```
CHECK ID:        A-1  (B-CODE)  — auth
ASSUMPTION:      A0.1 — the key authenticates
WHAT I SENT:     Header api-key on health, ready, env_params, heatmap, satellite, fetch-api-key-usage
HTTP STATUS:     200 across all data endpoints
RAW RESPONSE:    /health -> {"error":false,"status_code":200,"message":"API is healthy"}
                 /ready  -> {"error":false,"status_code":200,"message":"Service is ready"}
VERDICT:         PASS
WHAT I NOTICED:  api-key header works (not Bearer, not query param) on every functional endpoint.
```

```
CHECK ID:        A-2  (B-CODE)  — plan tier
ASSUMPTION:      A0.2 — which plan
WHAT I SENT:     POST /v1/system/fetch-api-key-usage  body {"api_key": "<key>"}
                 (GET -> 405 Method Not Allowed; the endpoint is POST with api_key at body top level)
HTTP STATUS:     200
RAW RESPONSE:    plan_details = {"plan_type":"Premium","cycle_type":"One-Time",
                   "subscription_start_date":"Jun 19, 2026","billing_period":"Jun 19 – Jul 19, 2026",
                   "active":false,"credits_reset_date":"Aug 31, 2026"}
VERDICT:         PASS (resolved)
WHAT I NOTICED:  Premium, but a ONE-TIME cycle, and active:false. Premium implies the higher caps
                 (50 mi^2 heatmaps, all env params) — good, but see A-7: the pool is one-time, not
                 monthly, so a budget mistake is not recoverable at a month boundary.
```

```
CHECK ID:        A-3 + S-1  (B-DATA)  — credit cost per call  ***THE MAKE-OR-BREAK NUMBER***
ASSUMPTION:      A0.3 — a 3-site heatmap collector fits in the credit pool
WHAT I SENT:     usage read -> one heatmap (g100, filter_type 1, ~0.9km polygon) -> usage read
                 -> one env_params (filter_type 1) -> usage read. Cross-checked against
                 activity_breakdown (credits/count).
HTTP STATUS:     200
RAW RESPONSE:    total_credits_used: 2,686,520 -> 2,690,740 (heatmap) -> 2,693,640 (env_params)
                 activity_breakdown:
                   Environment Parameter Analysis : 287,100 cr / 99  = 2,900 cr/call
                   Heatmap Generation             : 278,520 cr / 66  = 4,220 cr/call
                   Tile Satellite Segmentation    : 244,800 cr / 17  = 14,400 cr/call
                   Heat Intelligence Report       :   8,600 cr / 1   = 8,600 cr/call
VERDICT:         FAIL — apply the bottom of Z-4's degradation ladder
WHAT I NOTICED:  MEASURED (both live-delta and breakdown agree):
                   heatmap  = 4,220 credits/call   (Z-4 ceiling was 115  ->  ~37x over)
                   env_params = 2,900 credits/call
                 The field-first hourly design (~5,200 calls/month) => ~20,000,000 credits vs a
                 1,000,000 pool => ~20x over budget. Even ONE heatmap/site/hour (2,160/month) is
                 ~9.1M credits. **The hourly campus-field design is not affordable on this plan.**
                 Consequences for the plan: field perception must drop to a few times per day (Z-4
                 bottom rung); A1's historical sweep must be sparse (weekly/monthly, logged as a
                 cap); sites cannot each carry an hourly field. R1 (sigma) survives; R4 (hourly
                 coarse-to-fine) does not, as specified.
```

```
CHECK ID:        A-7  (B-DATA)  — monthly vs one-time pool
ASSUMPTION:      A0.4
HTTP STATUS:     200
RAW RESPONSE:    total_available_credits: 1,000,000 ; cycle_credits_used: 819,020 ;
                 cycle_remaining_credits: 180,980 ; total_credits_used: 2,693,640 ;
                 total_remaining_credits: -1,693,640 ; cycle_type: One-Time ; reset: Aug 31, 2026
VERDICT:         FAIL-risk (one-time pool)
WHAT I NOTICED:  One-time, not monthly. This specific key is already ~1.69M OVER its 1M allocation
                 (total_remaining_credits negative) and active:false, yet calls still complete and
                 still deduct. The cycle shows 180,980 credits left; at 4,220/heatmap that is only
                 ~43 more heatmaps this cycle. Z-4's 30% reserve is mandatory, and for the hackathon
                 a fresh/active key with a real 1M cycle is needed before the collector starts.
```

```
CHECK ID:        S-3  (B-CODE)  — spatial standard deviation  ***THE CENTRAL BET'S DEPENDENCY***
ASSUMPTION:      sigma_spatial (the conditioning variable of the conformal margin) exists
WHAT I SENT:     heatmap Ashburn, granularity 60, filter_type 1, 2026-07-28 15:00. Read
                 stats_data.temperature_stats.standard_deviation AND computed population stddev
                 from the raw per-tile average_temperature values myself.
HTTP STATUS:     200
RAW RESPONSE:    stats keys = [minimum, maximum, mean, standard_deviation]
                 API standard_deviation = 0.11473813598381839  (over 172 tiles)
                 my population stddev of tile values = 0.1144
VERDICT:         PASS ⭐
WHAT I NOTICED:  The API's standard_deviation IS the SPATIAL spread across tiles (matches my own
                 computation to 4 dp), not a temporal stddev. sigma_spatial is real, cheap (comes in
                 the small stats_data payload without parsing every tile), and trustworthy. Per-site
                 single-hour values already differ meaningfully: Ashburn 0.115, Hillsboro 0.159,
                 Phoenix 0.004 (a very smooth desert field) — exactly the structure H1 needs.
```

```
CHECK ID:        S-7 / C-2  (B-DATA / B-CODE)  — does filter_type=2 cover the window in one call, and what is the time step
ASSUMPTION:      the ~12x credit lever, and the hourly step
WHAT I SENT:     heatmap Ashburn, filter_type 2, start_time 06:00, end_time 18:00, granularity 100
HTTP STATUS:     200 (completed)
RAW RESPONSE:    top-level keys unchanged: [map_data, stats_data]. A tile's properties:
                 {"tile_id":0,"average_temperature":27.4874,"min_temperature":22.883,"max_temperature":32.0886}
VERDICT:         PASS with an important nuance
WHAT I NOTICED:  filter_type=2 accepts the whole range in ONE call — but it returns a TEMPORAL
                 AGGREGATE per tile (average / min / max over the window), NOT 12 separate hourly
                 fields. That is actually ideal for the safety decision: the per-tile MAX over the
                 window (max_temperature) is exactly "hottest tile, worst hour." BUT there is no
                 hour-by-hour array per tile in range mode, so C-2's "hourly step" does not apply to
                 a range heatmap; to get the hourly sequence you either loop filter_type=1 per hour
                 (12x the calls => at 4,220 cr/call, prohibitive) or use the persistence / exceedance
                 analytic modes. Net: the credit lever holds for the decision value; the hourly curve
                 does not come free.
```

```
CHECK ID:        B-1  (B-CODE)  — does the heatmap accept a FUTURE timestamp
ASSUMPTION:      P1.1 — forecast field is obtainable
WHAT I SENT:     heatmap Ashburn: (a) control past 2026-07-28 15:00 ; (b) future 2026-07-30 23:00
HTTP STATUS:     200 (both completed)
RAW RESPONSE:    control_past : mean 31.13 C, 64 tiles
                 future_today: mean 22.73 C, 64 tiles
VERDICT:         PASS
WHAT I NOTICED:  Future times within the current local day return a valid field. The future value
                 (22.7 C at 23:00) is far from the current-day afternoon value (31.1 C at 15:00) and
                 sits at a plausible night level -> not obviously persistence-of-now. Horizon is the
                 end of the current local day (~ up to +12 h), consistent with the docs. Days beyond
                 today were not accepted in prior testing.
```

```
CHECK ID:        B-5  (B-CODE + B-CLAIM)  — is the future value a GENUINE forecast
ASSUMPTION:      P1.4 — not persistence or climatology
WHAT I SENT:     Single-day diurnal shape only (a full two-issuance / two-weather-day test needs the
                 collector running).
HTTP STATUS:     200
RAW RESPONSE:    Ashburn 2026-07-28 diurnal (mean C): 03->23.34, 09->24.39, 15->31.13, 21->22.79
VERDICT:         INCONCLUSIVE (leaning genuine)
WHAT I NOTICED:  The curve has a real diurnal shape (cool pre-dawn, afternoon peak, evening fall),
                 which rules out flat persistence-of-now. It does NOT yet rule out climatology. The
                 definitive test — query the same future valid-time from two different issuance times
                 hours apart, and compare two days with different weather — REQUIRES the collector
                 (Z-1: values are unrecoverable after the fact). Schedule B-5/K-2 for +6 h once
                 collecting. Do NOT build the exceedance forward-count (F-2) on this until B-5 passes.
```

```
CHECK ID:        F-1  (B-CODE)  — the heatmap mode parameter
ASSUMPTION:      the decision primitives exist server-side
WHAT I SENT:     Read HeatmapSubmitRequest schema
HTTP STATUS:     200
RAW RESPONSE:    analytic_type enum = ["tcm","time_of_measure","exceedance","persistence"] (default tcm)
                 plus optional: threshold (number), direction ("above"|"below")
VERDICT:         PASS
WHAT I NOTICED:  exceedance (+ direction:"below" + threshold) and persistence exist as documented —
                 these ARE the free-cooling-hours and commitment-window primitives, computed
                 server-side. NOTE: exceedance was measured live at ~similar heatmap cost, and its
                 forward use is gated on B-5.
```

```
CHECK ID:        E-8  (B-CODE)  — can a heatmap carry WET-BULB
ASSUMPTION:      M2.2 — spatial wet-bulb in one call
WHAT I SENT:     Inspected heatmap tile properties + checked for any variable-selector field
HTTP STATUS:     200
RAW RESPONSE:    tile properties = [tile_id, average_temperature, min_temperature, max_temperature].
                 HeatmapSubmitRequest has NO variable-selection field; analytic_type does not select
                 a variable.
VERDICT:         FAIL (expected) — dry-bulb only
WHAT I NOTICED:  The heatmap maps TEMPERATURE only. There is no spatial wet-bulb and (see below) no
                 spatial humidity. So the spatial-wet-bulb field must be DERIVED per tile from the
                 dry-bulb field + a humidity source, or sigma is computed on the DRY-BULB field as a
                 documented proxy (plan Section 11.3). Given the cost finding, the dry-bulb-sigma
                 proxy is the realistic path.
```

```
CHECK ID:        B-6  (B-CLAIM)  — 2 m air temperature vs land-surface temperature
ASSUMPTION:      P1.8 — it is AIR temperature
WHAT I SENT:     heatmap Ashburn 2026-07-28 at 03/09/15/21:00; computed diurnal amplitude
HTTP STATUS:     200
RAW RESPONSE:    mean C: 03->23.34, 09->24.39, 15->31.13, 21->22.79 ; amplitude = 8.34 C
VERDICT:         PASS ⭐
WHAT I NOTICED:  8.3 C diurnal amplitude is squarely AIR-like (8–15 C). Land-surface temperature
                 would swing 20–30 C. Cross-site sanity also fits air, not LST: Phoenix 39.8 C
                 (~104 F air, not 55 C+ desert ground), Ashburn 31 C, Hillsboro 26.5 C. The ~20 C
                 category error is ruled out.
```

```
CHECK ID:        B-4  (B-CODE)  — what does the env_params `temperature` input DO
ASSUMPTION:      P1.5 — it may drive a wet-bulb calculator (the fallback path if B-1 failed)
WHAT I SENT:     env_params Ashburn 2026-07-28 15:00, identical except temperature = 15.0 then 35.0
HTTP STATUS:     200 (both)
RAW RESPONSE:    input 15.0 -> own_temperature 15.0, wet_bulb 22.6, humidity 72, apparent 30.4
                 input 35.0 -> own_temperature 35.0, wet_bulb 22.6, humidity 72, apparent 30.4
VERDICT:         VESTIGIAL — input is echoed but does NOT affect outputs
WHAT I NOTICED:  The `temperature` you pass is echoed back as locations[].temperature but the
                 computed wet_bulb / humidity / apparent are IDENTICAL regardless of it. So
                 env_params derives everything from its own internal model. **Consequence: the plan's
                 fallback "feed forecast dry-bulb from the heatmap into env_params to get forecast
                 wet-bulb" DOES NOT WORK.** Wet-bulb must instead be derived with psychrolib from a
                 dry-bulb source + a humidity source (B-8), or read directly from env_params' own
                 point value (which is not spatial).
```

```
CHECK ID:        B-8  (B-CLAIM)  — psychrolib triple cross-check
ASSUMPTION:      P1.7 — units are C, fields co-located, psychrometric wet-bulb (not WBGT)
WHAT I SENT:     env_params wet_bulb + humidity at Ashburn 15:00, plus psychrolib from (dry-bulb,
                 RH, pressure). NOTE: env_params does not expose the dry-bulb it actually used
                 (it echoes the input, which is vestigial — B-4), so a CLEAN three-way is blocked.
HTTP STATUS:     200
RAW RESPONSE:    API wet_bulb 22.6 C, humidity 72% ; psychrolib(25 C,72%,101325) = 21.25 C ;
                 wet_bulb <= dry_bulb : TRUE
                 Back-solving: wet_bulb 22.6 at 72% RH implies an internal dry-bulb ~26.5 C, whereas
                 the heatmap dry-bulb at the same point/time was ~31 C.
VERDICT:         PARTIAL — physics floor holds; clean cross-check blocked; an I-4 discrepancy surfaced
WHAT I NOTICED:  (1) wet-bulb <= dry-bulb always held (physics OK), and near-saturation behaviour
                 should be re-tested. (2) The API's wet_bulb is self-consistent with ~72% RH but
                 implies a dry-bulb (~26.5 C) that DISAGREES with the heatmap's dry-bulb (~31 C) at
                 the same location/time by ~4.6 C (an I-4 red flag: heatmap and env_params may be
                 different products/models — cross-check B-6/I-4). Recommendation: treat the heatmap
                 as the dry-bulb source of truth, and derive wet-bulb via psychrolib from the heatmap
                 dry-bulb + a humidity source; do not mix env_params' wet-bulb with heatmap dry-bulb
                 blindly. This is a genuine, must-resolve data-semantics finding.
```

```
CHECK ID:        C-2  (B-CODE)  — time step
(Answered under S-7.) Single-hour (filter_type 1) returns one field; range (filter_type 2)
returns a per-tile temporal aggregate (avg/min/max), not an hourly array. There is no exposed
sub-hourly or hourly-array step inside a range heatmap.
```

---

## COVERAGE (H-3 / site feasibility) — all three sites work

```
CHECK ID:        Coverage of the three hackathon sites (heatmap, 2026-07-28 15:00, g100)
HTTP STATUS:     200 (all completed)
RAW RESPONSE:    ashburn_va          : 64 tiles, mean 31.13 C, spatial stddev 0.115
                 phoenix_goodyear_az : 63 tiles, mean 39.81 C, spatial stddev 0.004
                 hillsboro_or        : 63 tiles, mean 26.50 C, spatial stddev 0.159
VERDICT:         PASS
WHAT I NOTICED:  All three chosen coordinates have heatmap coverage and return physically plausible
                 July-afternoon air temperatures. (Earlier ad-hoc tests saw some 404s at other
                 coordinates, so confirm the EXACT campus polygon per site before committing — see
                 the intermittency note below.)
```

---

## BONUS / BEYOND THE DOC

```
FINDING:  filter_type = 4 (range of days, up to one month) EXISTS.
WHY IT MATTERS:  The checklist and reference block assume filter_type is 1/2/3 only. The live spec
                 exposes 4 = "range of days (week/month, <=1 month)". This is a direct, cheaper path
                 for A1's historical free-cooling-hours sweep and for monthly aggregates, IF its
                 credit cost per call is acceptable (measure it — at 4,220/call for a single hour, a
                 monthly aggregate may be the single biggest cost saver or the single biggest call).
```

```
FINDING:  Heatmap unit is CELSIUS (stats_data + per-tile average_temperature are C).
WHY IT MATTERS:  Confirmed via cross-site sanity (Ashburn 31 C ~ 88 F, Phoenix 39.8 C ~ 104 F). No
                 F->C conversion should be applied to heatmap values. (This was a real trap in other
                 work; flagged here so the collector stores C directly.)
```

```
FINDING:  Heatmap endpoint is INTERMITTENT (G-2 / operational).
WHY IT MATTERS:  Repeated status polls sometimes 404 ("No activity found for the provided activity")
                 even after a valid activity_id, and some coordinates/hours return no field on one
                 attempt then succeed on retry. The collector MUST implement submit-with-retry +
                 a 404 grace window on the status poll (matches the documented "activity not found
                 immediately after submission" warning, G-2). All results here used up to 3–4 retries.
```

---

## STILL OUTSTANDING (need waiting / not yet run)

| Check | Why not now | When |
|---|---|---|
| **B-5 / K-2** full forecast-vs-later-actual | Values are unrecoverable (Z-1); needs the collector running | +6 h after collector starts |
| **K-3** zero-residual guard | Needs a day of forecast/actual pairs | +1 day |
| **K-4** actuals availability lag | Needs a valid hour to pass and be re-queried | +1–6 h |
| **K-5 / I-1** silent revision of past values | Needs re-query on day 2 and day 8 | +1 day, +7 days |
| **S-8** tile-grid stability across calls | Not yet compared centroid-by-centroid | Day 1 evening |
| **W-1/W-2/W-3/W-6** METAR baseline + truth check | Independent (NOAA/IEM) work, no FortyGuard credits | Day 0/1 |
| **S-9** heat_intelligence uncertainty field | heat_intelligence returned a non-PDF/dict in ~120 s in prior testing; needs its own dig | Day 1 |
| **G-1** full latency budget across 3 sites | Individual calls timed (~15–60 s heatmap incl. polling); a full 3-site run not yet timed end-to-end | Day 1 |

---

## What these results change in the plan

1. **Economics dominate everything.** At 4,220 credits/heatmap, the hourly 3-site campus-field design is ~20× over a 1M pool. Move directly to the **bottom rungs of Z-4**: field perception a few times per day (not hourly), A1 sampled weekly/monthly (logged as a cap), the hourly decision reverting to a single point where possible — except env_params is *also* 2,900 credits/call and its wet-bulb is not driveable (B-4), so the cheap hourly point path the plan assumed is not actually cheap. **Re-do Z-4 with these numbers before writing any collector.** Consider whether the whole design must shift from "hourly live field" to "historical A1 + a sparse live σ signal."
2. **σ_spatial is real and verified (S-3).** The central contribution's data dependency holds. Good.
3. **Wet-bulb is the hardest data problem, not temperature.** Heatmap = dry-bulb only (E-8); env_params wet-bulb is point-only and derived from its own model with an internal dry-bulb that disagrees with the heatmap (B-8 / I-4); the temperature input is vestigial (B-4). The realistic path: heatmap dry-bulb field for the decision and for σ (dry-bulb proxy), with wet-bulb derived via psychrolib from a documented humidity source, and this stated as a limitation.
4. **No forecast archive (Z-1)** — collector from day 1, as already planned.
5. **All three sites are usable**, and **filter_type=4** gives A1 a cheaper-per-day (if not per-call) route.
