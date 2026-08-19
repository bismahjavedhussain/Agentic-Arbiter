# FortyGuard API — field findings from hackathon development

**Compiled during FortyGuard Hackathon'26 build preparation · 2026-08-11 · living document**

Behaviour observed while building against the FortyGuard v1 API, written to be useful to the
engineering team. The discipline applied throughout:

- **Nothing is reported from a single observation.** Every entry lists its independent lines of
  evidence and trial count.
- **Exact request payloads are included** so each finding can be reproduced.
- **Items that failed retest are listed in [§4](#4-withdrawn--suspected-but-disproved-on-retest),
  not deleted.** Two of eight initial suspicions were withdrawn this way. One was our own
  measurement error. They are documented so the team can see what was checked and cleared.
- Where behaviour may be intended, that is said. Several entries are **documentation gaps**, not
  bugs.

**Environment.** API key redacted. ~125 calls issued 2026-08-11. The key's billing cycle closed
2026-07-19 and the usage endpoint reports the meter frozen (`cycle_remaining_credits` unchanged
throughout), so some behaviour may be specific to a key in that state — flagged per entry.

| Severity | Meaning |
|---|---|
| **HIGH** | Returns wrong or unusable data that a client cannot detect |
| **MEDIUM** | Detectable, but needs a workaround |
| **LOW** | Naming, units or documentation; no wrong values |

---

## 1. Confirmed findings

### 1.1 `heat_index_celsius` is computed from the caller's `temperature` input, not from conditions at the location — **HIGH**

**Expected.** Heat index is a function of air temperature and humidity *at the requested location
and time*. The `temperature` field in the request body is an input parameter; the response should
describe measured or modelled conditions.

**Observed.** `heat_index_celsius` is a direct function of whatever the caller passes in
`temperature`. Same coordinate, same date, same hour, only the input varied:

| request `temperature` | `heat_index_celsius` | `apparent_temperature_celsius` | `wet_bulb_temperature_celsius` |
|---|---|---|---|
| 10.0 | **10.0** | 30.8 | 24.6 |
| 25.0 | **25.8** | 30.8 | 24.6 |
| 40.0 | **86.7** | 30.8 | 24.6 |

Two things stand out. The heat index moves across a **76.7 °C range** purely from an input the
caller chose, while `apparent_temperature_celsius` and `wet_bulb_temperature_celsius` correctly
stay fixed — they describe the location and are unaffected. And an input of 40 °C produces a heat
index of **86.7 °C**, which is not a physically achievable value; no range validation appears to
reject it.

**Reproduction.**

```json
POST /v1/env_params
{ "latitude": 39.01, "longitude": -77.446,
  "temperature": 40.0,
  "date_time": { "start_date": "2026-08-10", "start_time": "15:00", "filter_type": 1 } }
```

**Impact.** A client that leaves `temperature` at a default, or passes a placeholder, receives a
heat index that describes nothing. We initially recorded this as *"heat_index is near-constant and
unusable"* — because we happened always to pass 25.0. The real behaviour is more serious: the field
is not near-constant, it is **arbitrary**, and the constancy was an artifact of our own fixed
input. **Suggested fix:** compute it from the same conditions that drive
`apparent_temperature_celsius`, or document it as a client-side convenience calculation over the
supplied temperature.

---

### 1.2 `analytic_type: time_of_measure` returns physically implausible hours and contradicts `tcm` — **HIGH**

**Expected.** For a request spanning a day, the hour at which each tile's maximum occurred. In
Ashburn, Virginia in July that is mid-afternoon.

**Observed.** Three independent lines of evidence.

**A — implausible hours.** Five summer days, same 2 × 2 km AOI, window 01:00–23:00,
`filter_type: 2`:

| date | modal hour | tiles | spatial sd |
|---|---|---|---|
| 2026-06-15 | **0** | 397 | 2.439 |
| 2026-06-30 | **1** | 397 | 0.000 |
| 2026-07-10 | 13 | 397 | 0.000 |
| 2026-07-20 | **2** | 397 | 0.000 |
| 2026-07-28 | **22** | 397 | 3.903 |

A daily maximum at 00:00, 01:00 or 02:00 is not possible at that latitude in summer. Note also the
spatial standard deviation: exactly 0.000 on three days, 2.4 and 3.9 on the other two.

**B — contradicted by `tcm` on the same date.** Same AOI, 2026-07-28, mean of per-tile
`max_temperature`:

```
12:00-16:00     31.122 C
20:00-23:00     24.676 C        difference +6.446 C
```

The maximum is unambiguously in the afternoon. `time_of_measure` nominated hour **22** — wrong by
roughly eight hours.

**C — the same request returned different results on different occasions.** For 2026-07-28,
01:00–23:00, one call returned **14.0 for every tile** (spatial sd 0.000, `stats_data` reporting
`min 14.0, max 14.0, mean 14.0, units "hour"`); later calls returned **modal 22, range 14–22**.
*Qualification:* three consecutive calls within a single session were identical to each other, so
this is a difference **between** sessions, not within one. We cannot say what changed in between.

**Reproduction.**

```json
POST /v1/heatmap
{ "polygon_aoi": { "...2x2 km box centred 39.0100, -77.4460..." },
  "granularity": 100, "analytic_type": "time_of_measure",
  "date_time": { "start_date": "2026-07-28", "start_time": "01:00",
                 "end_time": "23:00", "filter_type": 2 } }
```

**Impact.** A client using this to locate the daily peak is silently wrong. We had to abandon it
and recover peak timing indirectly, by requesting a series of narrow `tcm` windows and comparing
their maxima — 5 calls per day instead of 1.

---

### 1.3 `cloud_cover_octas` returns values far outside the octas range — **LOW**

**Expected.** Octas are eighths of sky cover: integers 0–8.

**Observed.** Four points across three US time zones, four different hours:

| point | hour | `cloud_cover_octas` |
|---|---|---|
| Ashburn VA | 06:00 | **81.0** |
| Ashburn VA +0.05° | 12:00 | **89.0** |
| Dallas TX | 18:00 | **44.0** |
| Phoenix AZ | 15:00 | **38.0** |

Also observed at 92.0 and 68.0 in earlier calls. Every value exceeds 8; all are consistent with
**percentages**.

**Impact.** Low — no wrong values, and easy to work around once noticed. But a client trusting the
name will be wrong by a factor of 12.5. **Suggested fix:** rename to `cloud_cover_percent`, or
divide by 12.5 and round.

---

### 1.4 Out-of-horizon windows return `status: completed` with zero tiles — **HIGH**

> **Revised 2026-08-12, and narrowed in FortyGuard's favour.** This entry previously also implied the
> forecast path was *intermittently* failing inside the supported horizon. **That part is withdrawn:
> it was our bug, not yours.** The correction is documented in §1.4b below, and the remaining defect
> is now stated more precisely than before because we can name the exact boundary that triggers it.

**Expected.** A request for a window outside the available horizon returns a non-success status, or
an explicit error a client can branch on — ideally one naming the horizon.

**Observed.** HTTP 200, `status: completed`, `map_data.features: []`, with a `stats_data` block
present. **Indistinguishable from a legitimately empty area, and indistinguishable from a transient
failure.**

**The boundary, now measured precisely.** With request times interpreted in the AOI's local zone
(see §3), four windows issued at a known instant behaved as follows:

| true lead to window start | result |
|---|---|
| 9.25 h | 397 tiles |
| 11.25 h | 397 tiles |
| **13.25 h** | **zero tiles, `status: completed`** |
| **17.25 h** | **zero tiles, `status: completed`** |

Independently confirmed the same day at **9.41 h lead → 17,862 tiles** over 64 km² at 60 m. So the
horizon behaves as a clean **12-hour** cut, exactly as documented — and crossing it is silent.

**Reproduction.** Issue two otherwise identical requests, one inside and one outside the horizon, with
times expressed in the AOI's local zone:

```json
POST /v1/heatmap
{ "polygon_aoi": { "...8x8 km box centred 39.0100, -77.4460..." },
  "granularity": 60, "analytic_type": "tcm",
  "date_time": { "start_date": "<site-local today>",
                 "start_time":  "<site-local hour ~9 h ahead>",
                 "end_time":    "<+2 h>", "filter_type": 2 } }
```
Repeat with a start ~13 h ahead. The first returns a full field; the second returns `completed` with
`features: []`.

**Why it matters.** A client cannot distinguish *"outside the horizon"* from *"empty area"* from
*"retry me"*. In our case it produced 48 futile retries against windows that were never going to
return data. A distinct status, or an error such as `OUTSIDE_FORECAST_HORIZON` with the horizon in the
body, would remove the ambiguity entirely. As it stands every client must assert non-empty on every
response or empty results propagate silently into downstream calculations.

---

### 1.4b ⚠️ CORRECTION — a previous claim of forecast intermittency is withdrawn

**We reported** that the forecast path was returning empty responses inside the supported horizon,
citing 48 retries across four lead times that recovered nothing on 2026-08-11.

**That was our defect.** Our test harness built request windows from the local clock of the machine
running it (UTC+5) while the endpoint interprets them in the AOI's local zone (UTC−4 in August) — a
silent **nine-hour** error. The four windows we believed were at leads of 4, 6, 8 and 10 h were
really at **13, 15, 17 and 19 h**. Every one was outside the 12-hour horizon, so no number of retries
could ever have succeeded.

**What this means for FortyGuard:** the 12-hour forecast worked correctly in every case we can now
verify, including a 9.41 h lead returning a full 17,862-tile field. **We have no evidence of forecast
intermittency and we retract the suggestion of it.**

**What still stands, and is arguably the more useful finding:** the fact that a nine-hour client-side
timezone error was able to masquerade as a service reliability problem *for four days* is itself the
consequence of §1.4 and §3.1 — silent empty successes plus no echoed timestamp in the response. Had
the response carried the interpreted window back, or named the horizon in an error, we would have
found our own bug within minutes. **Two small additions to the response would have prevented a
customer from misdiagnosing your service.**

---

### 1.5 `start_time` equal to `end_time` returns HTTP 500 — **MEDIUM**

**Expected.** A 400-class validation error naming the problem, or graceful handling of a
zero-length window.

**Observed.** `HTTP 500 Internal Server Error` at submit. **3 of 3 attempts**, plus two earlier
independent occurrences the same day.

**Reproduction.**

```json
POST /v1/heatmap
{ "polygon_aoi": { "...1x1 km box..." }, "granularity": 100, "analytic_type": "tcm",
  "date_time": { "start_date": "2026-08-10", "start_time": "14:00",
                 "end_time": "14:00", "filter_type": 2 } }
```

**Impact.** A 500 gives no way to distinguish a bad request from a server fault, so retry logic
will retry a request that can never succeed.

---

### 1.6 Historical coverage floor is undocumented, and older dates fail inconsistently — **MEDIUM**

**Expected.** Either data, or an error stating the earliest supported date.

**Observed.** Same AOI, 15 July at 15:00, `filter_type: 1`, four years:

| year | result |
|---|---|
| 2019 | **request timed out** |
| 2021 | **empty success** (`completed`, zero tiles) |
| 2023 | ok, 84 tiles |
| 2025 | ok, 84 tiles |

So the floor lies between 2021 and 2023, is not documented, and the two unsupported years fail in
**two different ways** — one hanging until timeout, one returning a successful empty response.

**Impact.** Clients cannot discover the supported range except by bisection, which is what we did.
A documented floor, or a consistent error, would remove that.

---

### 1.7 `locations[].temperature` echoes the caller's input with no indication it is an echo — **MEDIUM**

**Observed.** The value at `locations[].temperature` is always exactly the `temperature` sent in
the request (verified at inputs of 10.0, 25.0 and 40.0). There is no separate field marking it as
an echo.

**Impact.** This cost us real time and produced a false finding we nearly reported. We compared
`heatmap` temperatures against `locations[].temperature` and measured differences of +1.56 °C and
+9.18 °C, and briefly believed the two endpoints disagreed. They do not — **we were comparing the
heatmap against our own input constant.** See §4.2.

Related and worth documenting: **`env_params` returns no dry-bulb air temperature.** Of the 15
parameters, the temperature-like ones are `apparent_temperature_celsius`,
`wet_bulb_temperature_celsius` and `heat_index_celsius`. There is no plain air temperature, so
`heatmap` and `env_params` cannot be cross-checked on temperature at all. If that is intended, a
line in the docs would help; if not, exposing dry-bulb would be valuable.

---

### 1.8 `env_params` reports the standard-time offset in summer — daylight saving is not applied — **HIGH**

> **Upgraded 2026-08-12 from open question §2.1.** That entry said we could not locate a timezone field
> on retest. **We were looking in the wrong place** — it is at `metadata.timezone`, not
> `locations[].timezone`. Having found it, the original suspicion is confirmed.

**Expected.** For an AOI in Loudoun County, Virginia, on a date in July or August, the UTC offset is
**−04:00 (EDT)**. Eastern US daylight saving runs from March to November.

**Observed.** Three saved responses, two different dates, both inside the DST window:

| response | `metadata.timezone` | `timezone_offset_hours` | first timestamp |
|---|---|---|---|
| 2026-07-28 15:00 request | `"GMT-5"` | **−5** | `2026-07-28T15:00:00-05:00` |
| 2026-07-28 03:00 request | `"GMT-5"` | **−5** | `2026-07-28T03:00:00-05:00` |
| 2026-08-08 21:00 request | `"GMT-5"` | **−5** | `2026-08-08T21:00:00-05:00` |

**−05:00 is EST, the winter offset.** It is being applied on dates when the location is on EDT, so the
offset is wrong by one hour on roughly two-thirds of the year.

**Impact, and it is the ambiguity that hurts rather than the hour itself.** The timestamp is emitted as
a fully-formed ISO-8601 string with an offset attached, so a client that parses it *correctly* — which
is the whole point of including an offset — resolves `2026-07-28T15:00:00-05:00` to **20:00 UTC**,
which is **16:00 local**, an hour later than the 15:00 the caller asked for. A client that ignores the
offset and reads the wall-clock time gets what it expected. **So correct parsing gives the wrong
answer and naive parsing gives the right one**, which is the worst arrangement for a client trying to
be careful.

**RESOLVED 2026-08-12 — the DATA is shifted, not just the label.**

We first tried cross-correlating `relative_humidity_percent` against station-derived RH at KIAD. That
was **inconclusive even pooled over 8 days and 192 hourly pairs**: lag 0 scored 0.9181 against lag +1 at
0.9012, a margin of 0.017 — too small to call. RH is a modelled field whose diurnal phase does not track
a station 8 km away closely enough, and the correlation curve is too flat near its peak to locate a
one-hour shift **at any sample size**.

**What settled it was your own `solar_irradiance` block, because clear-sky irradiance is pure astronomy
with no weather noise.** Its peak must fall at true solar noon, and true solar noon at 39.0100/−77.4460
is **13:10 EDT** or, equivalently, **12:10 EST**. Six single-hour requests on 2026-08-10:

| requested hour | clear-sky GHI |
|---|---|
| 10:00 | 738.27 |
| 11:00 | 836.59 |
| **12:00** | **880.09** ← peak |
| 13:00 | 865.54 |
| 14:00 | 793.99 |
| 15:00 | 670.76 |

**The peak falls at requested hour 12, which is solar noon only under EST.** Under EDT it would have to
fall at 13. (Our solar-position algorithm was verified to 0.0° against a known reference before being
used for this.)

**So `env_params` computes on standard time year-round.** A caller requesting 12:00 on a summer day
receives the conditions for **12:00 EST = 13:00 EDT** — one hour later in true local time than asked
for. This is more serious than a labelling error: the values themselves are for the wrong hour.

**Suggested fix, unchanged but now more urgent:** resolve the offset with a DST-aware timezone database
for the AOI's date. Emitting the IANA zone name (`America/New_York`) beside the numeric offset would let
clients verify it independently.

### 1.8b `solar_irradiance` returns a scalar where `parameters` returns arrays — **LOW**

Requesting a multi-hour window (`filter_type: 2`, 00:00–23:00) returns `metadata.timestamps` with 24
entries and every field under `parameters` as a **24-element array** — but `solar_irradiance.clear_sky`
comes back as a **single scalar**. So irradiance cannot be obtained as a time series in one call; it
needs one call per hour. This is what forced the six single-hour calls above. Either shape is fine, but
they should agree with each other.

**Suggested fix.** Resolve the offset with a DST-aware timezone database for the AOI's date, not a
fixed standard-time offset. Emitting the IANA zone name (`America/New_York`) alongside the numeric
offset would let clients verify it independently. Note this compounds §3.1: `heatmap` accepts times
with no zone at all and interprets them as AOI-local, while `env_params` returns times labelled with an
offset that is wrong in summer — so **the two endpoints do not agree with each other about what time it
is.**

---

## 2. Open questions — observed but not established

Reported as questions, not defects.

**2.1 Timezone label — RESOLVED, promoted to §1.8.** The field exists at `metadata.timezone`; we had
been looking at `locations[].timezone`. It reports `GMT-5` in July and August, where the location is on
EDT (GMT-4). Daylight saving is not applied. See §1.8.

**2.2 `heat_intelligence` analysis types.** Earlier work found 2 of the 5 documented analysis
types accepted on a Premium key. Not re-verified in this round.

---

## 3. Documentation observations

### 3.1 ⭐ The timezone of `start_time` / `end_time` is undocumented — **and this one cost us four days**

`date_time.start_time` and `end_time` carry no offset and no zone. Empirically they are interpreted in
**the AOI's own local time**, not UTC and not the caller's zone. Nothing in the response reveals which
convention was applied.

We ran a UTC+5 machine against a UTC−4 AOI and were silently nine hours off on **every forecast
request for four days**, which we misread as a fault in your forecast service (now withdrawn, §1.4b).

Established by two independent arguments, both from responses already in hand:

1. Across five days of saved fields, the diurnal maximum falls in the **16:00–18:00** requested window
   and is already declining by 18:00–20:00 — a normal *local* afternoon curve. Under a UTC reading,
   18:00 UTC is 14:00 local, essentially the peak, where temperature cannot be falling.
2. Site-local is the only convention consistent with which windows returned data: 9.25 h and 11.25 h
   leads succeeded, 13.25 h and 17.25 h returned zero tiles — a clean 12 h cut. A UTC reading predicts
   the 9.25 h case should have succeeded, and it did not.

**Two changes, either of which would have prevented this entirely:**
- **State the convention in the documentation**, and ideally accept an ISO-8601 offset (`"2026-08-12T14:00:00-04:00"`) so the caller cannot be ambiguous.
- **Echo the interpreted window back in the response.** One field would have turned a four-day
  misdiagnosis into a five-minute fix.

This is the single highest-value change in this document. It is not a bug in your service — it is an
interface that makes a specific client error both easy to commit and impossible to detect.

### 3.2 ⭐ Spatial information content is set by AOI SIZE, not by granularity — **characterisation, may be intended**

**Not filed as a bug.** It may be correct physics, or an intended property of the downscaling. But it
changed our architecture once we measured it, so it is worth documenting for other clients.

**What we measured.** Across **25 fields** on one 2 × 2 km AOI at 100 m — five dates × five two-hour
windows — a single fixed spatial pattern explains **99.9971 %** of the spatial variance. Removing that
one component leaves a residual of **0.0011 °C** against an original 0.212 °C. Several field pairs
correlate to **exactly ±1.000000**, including pairs from *different dates*, and the pattern's
amplitude changes sign (so it inverts exactly between some consecutive windows).

In other words, at that AOI a response of 397 tiles carries **one fixed pattern, one amplitude and one
offset** — two degrees of freedom, not 397.

**We then separated area from granularity**, because in our earlier data every small AOI happened to be
g100 and every large one g60. Fully crossed, identical times (2026-07-28, 12:00–14:00 vs 16:00–18:00,
`tcm`, `filter_type 2`, same centre):

| AOI | granularity | tiles | shape correlation between the two windows | affine residual, % of sd |
|---|---|---|---|---|
| 2 km | 100 | 397 | **+0.999995** | **0.31 %** |
| 2 km | **60** | 1,120 | **+0.999995** | **0.31 %** |
| 8 km | 100 | 6,445 | +0.599696 | 80.0 % |
| 8 km | **60** | 17,862 | +0.601686 | 79.9 % |

**Two clean conclusions:**

1. **It follows AREA, not granularity.** At 2 km the field is one template at *both* granularities; at
   8 km it is genuinely structured at *both*.
2. **Granularity does not change the information content.** At 2 km, g60 returns **2.8× more tiles**
   than g100 (1,120 vs 397) and the statistic is **identical to six decimal places**. At 8 km, 17,862
   tiles versus 6,445 changes the correlation by **0.002**.

**To be explicit about what this does NOT say:** it does not say 60 m is fake. Our own separation-decay
check (§5) found the tile-to-tile |ΔT| decays smoothly from 60 m to 2 km with no upsampling
discontinuity. The finding is about **independent temporal-spatial structure**, not about smoothness.

**Why it mattered to us.** We are trying to resolve a condenser exhaust plume, which is a few hundred
metres across. The measurement above says the field carries no independent structure at that scale, so
a plume cannot be inside it. That was genuinely useful — it told us our physics layer is *additive*
rather than double-counting something you already model. But we only learned it by running 31 fields
through a decomposition. **One line in the documentation** — "spatial structure is resolved at scales
above roughly X km; finer granularity increases tile count without adding independent structure" —
would save every client that work, and would stop anyone assuming that requesting 60 m over a small
box buys them detail it does not contain.

### 3.3 Tile lattice is rotated ~1.55° from north — **LOW**

Tile centres do not lie on constant-latitude rows. Stepping one tile "east" also moves **+2.7 m
north**; stepping one row "north" moves **−2.7 m east**. The lattice is a regular ~101 m grid rotated
**+1.55°**, consistent with a projected grid rendered back into WGS-84.

Harmless once known, and the lattice is perfectly stable (§5). But a client that builds a raster by
grouping on distinct latitude values gets one row per tile — in our case a 397 × 397 array holding 397
values, which silently produced a confidently wrong result in one of our own analyses before we caught
it. **Suggested fix:** state the projection and rotation, or expose row/column indices per tile.

### 3.4 Other observations

- **`heatmap` responses contain no metadata block** — no echo of requested parameters, no
  generation timestamp. A stale or cached response cannot be distinguished from a fresh one except
  by the client's own fetch time. **Combined with 3.1, this is why the timezone error was invisible.**
- **Per-call pricing is recoverable but not stated.** `POST /v1/system/fetch-api-key-usage` returns
  a per-service breakdown; for this account, Heatmap Generation is 278,520 credits over 66 calls,
  i.e. **4,220 credits per heatmap call**. Useful, but the client must divide it out.
- **`env_params` has no line item in that breakdown**, alongside Heatmap Generation, Tile Satellite
  Segmentation and Heat Intelligence Report. Unclear whether it is unmetered or bundled. This
  materially affects how a client designs its call pattern — we would lean on `env_params` much
  more heavily if we knew it were free.
- **`filter_type` semantics are undocumented.** Values 1–4 were established empirically: 1 a single
  hour, 2 a window with `end_time`, 3 a day, 4 a month range using `end_date`.
- **`billing_cycle.credits_reset_date` (2026-08-31) differs from `billing_cycle.end_date`
  (2026-07-19)** with no explanation of the relationship.

---

## 4. Withdrawn — suspected but disproved on retest

Kept visible so the team can see what was checked and cleared, and because both withdrawals were
instructive.

### 4.1 `analytic_type: persistence` is NOT broken — withdrawn

**We initially believed** `persistence` returned values identical to `exceedance`, based on a batch
where both were byte-identical.

**Retest disproved it.** Over a single afternoon window (10:00–18:00, threshold 30 °C) both
analytics returned exactly 6.0 on all 84 tiles — but that is **correct behaviour**: if temperature
crosses the threshold once and stays above for six contiguous hours, then *hours above* and
*longest run above* are both 6. The window could not discriminate.

Repeated over a **month** (2026-07-01 to 2026-07-31, `filter_type: 4`), where the two quantities
must diverge:

| analytic | mean | range |
|---|---|---|
| `exceedance` | 162.360 | 143.249 – 169.991 |
| `persistence` | **9.420** | 7.031 – 10.374 |

**Identical on 0 of 84 tiles.** The two analytics compute genuinely different quantities.
**`persistence` works. Our original test window was the problem.**

### 4.2 `heatmap` and `env_params` do NOT disagree on temperature — withdrawn

**We initially measured** differences of +1.560 °C and +9.180 °C between `heatmap` average
temperature and `env_params` temperature at the same point and hour, and were preparing to report
a substantial endpoint disagreement.

**It was our error.** We read `locations[].temperature`, which is the **echo of our own request
input** (25.0 in both calls — hence the difference growing with the heatmap value). `env_params`
returns no dry-bulb air temperature at all, so the comparison is not possible. See §1.7.

*(An earlier ~3.5 °C offset between the two endpoints was recorded in prior work by a different
method. It is not re-asserted here, because we no longer have a valid way to measure it.)*

---

## 5. What worked well

A defect list alone gives a misleading picture. These were verified and were solid throughout.

- **The tile lattice is perfectly stable.** 6,875/6,875 and 17,862/17,862 tiles byte-identical
  between separate calls and across dates. Per-tile time series can be built with confidence, and
  this is the property everything else we did depends on.
- **The field tracks real weather.** Between two dates a nearby airport station (KIAD) rose 9.6 °C;
  the FortyGuard field over the same span rose 11.13 °C — ratio 1.16. Live data, not a climatology.
- **60 m granularity is genuine.** Mean |ΔT| between tile pairs decays smoothly with separation —
  0.011, 0.025, 0.048, 0.093, 0.170, 0.301 °C at 60 m through 2000 m — with no discontinuity
  indicating upsampling from a coarser product.
- **It is air temperature, not land surface temperature.** Diurnal amplitude of 7.8–8.3 °C is
  consistent with air; LST would be far larger.
- **The diurnal cycle is correct and internally consistent.** Keyed on requested `start_time`,
   04:00–06:00 gave 21.1 °C rising to a peak of 33.8 °C at 16:00–18:00 for Ashburn in August —
  which also confirmed for us that `start_time` is interpreted as site-local.
- **Capacity is excellent.** 17,862 tiles over 64 km² at 60 m granularity in a single 67 s call.
- **Pricing is flat** with respect to area, granularity, hour count and analytic type, which makes
  budgeting simple and rewards large polygons.
- **`env_params` is rich** — 15 parameters plus `elevation` and a `solar_irradiance` block with
  clear-sky GHI/DNI/DHI — and it served future timestamps reliably, including at times when the
  `heatmap` forecast path was returning empty.
- **Forecast and history are request-symmetric.** The same request shape returns a prediction before
  the fact and the outcome after it, which makes measuring forecast error straightforward. On 6,875
  matched tiles: bias +0.349 °C, sd 0.150 °C on peak temperature. **This property is what let us
  calibrate a statistical bound at all**, and it is genuinely uncommon in weather APIs.

---

## 6. Feature request: expose wind speed and direction

**One request, and it is the only one in this document that asks for new data rather than a fix.** We
have tried to keep it to verifiable facts, because a feature request built on a guess wastes your time.

### The blocker, stated plainly

`env_params` returns 15 parameters plus `elevation` and a `solar_irradiance` block. **None of them is
wind.** `heatmap` returns temperature analytics only. So a client cannot obtain wind speed or direction
from FortyGuard at all, at any resolution.

We needed it, could not get it, and had to source hourly wind from a **third-party station archive**
(NOAA ASOS at KIAD, via Iowa State University's Environmental Mesonet). That means a product built on
FortyGuard's 60 m field depends on a separate provider for a variable at *station* resolution — one
point for the whole metro — which throws away the spatial advantage that made us choose FortyGuard.

### Why wind, specifically, and not a wish-list

Four facts, each independently checkable:

1. **Direction carries more signal than speed for our physics.** From six instrumented air-cooled
   condensers in California Energy Commission report **CEC-500-2013-065** (~40,000 digitised points):
   recirculation varies **1.60×** across wind-direction sectors, against **1.22×** across the entire
   measured wind-speed range. Speed is nearly flat; direction is the variable that decides the answer.
2. **Published work in this exact application uses it.** Google/DeepMind's data-centre cooling
   controller takes **wind speed and wind direction** among its model inputs. This is not an exotic
   requirement — it is standard for the industry you are selling into.
3. **It is required to interpret your own product correctly.** Atmospheric dispersion depends on the
   Pasquill stability class, which is determined from **wind speed plus solar radiation**. You already
   serve solar irradiance. Wind speed is the missing half, and without it a client cannot select the
   dispersion regime that governs how heat moves through the field you are selling them.
4. **We could not test a question about your own data without it.** To ask whether your 60 m field
   contains wind-aligned structure, we had to bring in outside wind. A client should not need a
   competitor's data to characterise yours.

### What would help, in order of value

| | Request | Why |
|---|---|---|
| **1** | **`wind_speed` and `wind_direction` in `env_params`**, at a requested point and hour, forecast and historical, matching the existing 12 h horizon | Smallest change, unblocks stability classification and any dispersion calculation. Point resolution alone would already be enough for us |
| **2** | A wind analytic in `heatmap`, on the same tile lattice | The spatial version. Genuinely differentiating, since station data cannot provide it — but only worth it if the downscaling supports wind, which we cannot judge |
| **3** | Dry-bulb air temperature in `env_params` (see §1.7) | Would also let the two endpoints be cross-checked, which is currently impossible |

### What we are explicitly NOT claiming

We are **not** saying your model ignores wind. Your own material describes it as conditioned on
*"atmospheric, surface, and terrain conditions"*, and wind may well be inside that. We tested only
whether wind-dependent structure is **detectable in the output**, and at a 2 km AOI in a two-hour
maximum across 178° of wind direction we could not detect it — which given §3.2 is unsurprising, since
that AOI has only two spatial degrees of freedom to begin with. **That is a statement about what is
observable in the response, not about your internals.** Our request is simply that the variable be
**exposed**, whatever role it plays inside.

---

## 7. Forecast-vs-history level disagreement, and the uncertainty gap it creates

**Added 2026-08-18.** This section is the most operationally significant finding in the document, because
it is the one that stops a client making a calibrated promise on top of your forecast.

### 7.1 The measurement

We ran a pre-registered, unattended daily test (`testing/test_n26_coverage.py`) that issues **one
`/v1/heatmap` forecast** for a fixed target window and, after that window has elapsed, retrieves **the
history for the identical window**. Both legs go through the **same function with the same payload** —
`analytic_type: "tcm"`, `granularity: 60`, an 8 × 8 km polygon at 39.0100, −77.4460, window
**14:00–16:00 site-local (America/New_York)**, `filter_type: 2`. **The only difference is when the call
was issued.** 17,862 tiles per call. Forecast lead ≈ 9.3–9.5 h, inside your documented 12 h horizon.

**Per-tile `outcome − forecast`, over four complete pairs:**

| Date | day-mean offset | **within-day sd across 17,862 tiles** | \|offset\| / sd |
|---|---|---|---|
| 2026-08-12 | **−0.8396 °C** | 0.1056 | 7.9 |
| 2026-08-13 | **−0.8115 °C** | 0.0699 | 11.6 |
| 2026-08-15 | **+0.1520 °C** | 0.0644 | 2.4 |
| 2026-08-16 | **−3.7127 °C** | **0.2903** | 12.8 |

> **Within any one day, all 17,862 tiles are wrong by very nearly the same amount. Between days, that
> amount swings by 3.9 °C and changes sign.** The error is a **spatially uniform, day-varying level
> offset** — your spatial downscaling is excellent and the level carries essentially all of the error.

### 7.2 It is not a lead-time effect

We hold five forecasts of one target window purchased at leads **9.41, 7.49, 5.49, 3.49 and 1.49 h**
(`testing/diag52_leadlevel.py`, from N-25's fixtures). The offset does **not** shrink:

| Lead | 9.41 h | 7.49 h | 5.49 h | 3.49 h | **1.49 h** |
|---|---|---|---|---|---|
| offset | −0.8396 | −1.0850 | −0.8846 | −1.1787 | **−1.0177 °C** |
| \|offset\|/sd | 7.9 | 10.0 | 9.2 | 9.1 | **9.1** |

**At 1.5 h lead the offset is still ~1 °C.** At that horizon persistence alone would be near-perfect, so
this is not forecast skill. **It reads as a systematic level difference between the forecast pipeline and
the history pipeline for the same request.**

### 7.3 Your history looks right; we are not questioning it

Against **independent** ground truth — NOAA ASOS at KIAD, same site-local window — your **history** sits
at **+1.92, +1.92 and +0.86 °C** above the airport on 13/15/16 August. That is physically expected: the
AOI is 8 km of data-centre corridor with asphalt and waste heat, KIAD is airport grass. **And the offset
is smallest on the coolest day, which is exactly how an urban heat-island signal should behave.** We read
that as your history working. On 16 August the real day was **5 °C cooler** than the two before it
(26.11 °C at the station); **your history caught it at 26.97 °C, your forecast said 30.69 °C.**

### 7.4 Why this blocks a calibrated promise — with the number

We wrap your forecast in a one-sided **split-conformal** bound, calibrated on earlier days' residuals, to
promise a client *"the intake will not exceed X, and that holds 90 % of the time."* Conformal coverage
requires the calibration days and the test day to be **exchangeable**. A level offset that flips sign
breaks that assumption directly. Measured, sequential, out-of-sample:

| | pooled coverage | worst test day |
|---|---|---|
| **As shipped** | **65.6 %** | **0.0 %** |
| Level anchored to one in-AOI observation | 80.1 % | 52.8 % |
| *nominal target* | *90 %* | |

The **0.0 %** day is not a marginal miss: calibrating on two days where the forecast ran warm produced a
negative half-width, the next day ran cool, and **every one of 17,862 tiles breached.**

Anchoring the level to a single local observation (`testing/diag53_anchored.py`) recovers most of it —
the 0.0 % day becomes **89.9 %** — but not all, **because on 16 August your forecast's spatial residual
spread also widened 4.5× (0.0644 → 0.2903 °C).** So the bad day is bad in **both** level and pattern, and
a client calibrated on normal days cannot see it coming.

### 7.5 The two requests, in priority order

| | Request | Why it matters, concretely |
|---|---|---|
| **1** | **A per-request forecast uncertainty indicator** — a spread estimate, a confidence band, or a recent-verification bias term returned alongside the forecast | Today the API returns a **point forecast with no uncertainty**, so a client cannot distinguish a good forecast from a poor one until after the window has passed. **On 16 August your forecast was 3.7 °C off in level and 4.5× wider in spatial spread than normal. Had either been exposed, our agent would have widened its bound and kept its 90 % promise. Because neither was, it published 80 %.** This single field is the difference between a client offering a calibrated guarantee and offering a caveat |
| **2** | **Forecast verification access** — a forecast archive, or a verification endpoint pairing past forecasts with realised history | Measuring your forecast skill currently costs a client **two paid calls per site per day** (forecast + history of the same window) sustained over weeks. At **4,220 credits per heatmap call** that is a real barrier to anyone trying to build a calibrated product on top of you — and the resulting skill statistics would be useful to you as well |

### 7.6 What we are explicitly NOT claiming

- **Not** that your forecast is inaccurate in general. **Four pairs, three test days, one bad day.** A
  missed frontal passage or unexpected cloud at 9.5 h lead is ordinary forecast error, and we would not
  report it as a defect. **What we are reporting is the STRUCTURE of the error** — spatially uniform,
  day-varying, present even at 1.5 h lead — **and the absence of any way for a client to see it coming.**
- **Not** that your history is wrong. §7.3 argues the opposite.
- **Not** a claim about your internals. We measured only what the responses contain.
- Our comparison to ASOS is a **spatial mean of per-tile maxima versus a single-point maximum**, which are
  not the same statistic. The AOI's own spatial sd is ~0.2–0.4 °C, so that cannot explain differences of
  degrees, but it does mean the ASOS numbers are an indication rather than a calibration reference.
- **Everything here is reproducible from the payloads above**, and the fixtures are retained.

---

## 8. `completed` with zero tiles has (at least) four different causes — and all of them are billed

**Added 2026-08-18. Substantially CORRECTED later the same day: our first diagnosis was wrong, and the
correction makes the finding worse, not better. The retraction is left visible in §8.6.**

### 8.1 What happened

Our daily unattended collector (`testing/test_n26_coverage.py collect`) had worked for days. On
2026-08-18 its forecast leg failed with our own guard message:

```
forecast_error: "ZERO TILES with completed status"
```

The request was well formed and inside the documented horizon — **the same payload shape that had
succeeded on 12, 13, 15 and 16 August**, at a lead of 6.5 h against a 12 h horizon. **The response was
HTTP 200, `status: completed`, and an empty tile set.**

### 8.2 First hypothesis: quota exhaustion. ❌ WRONG — see §8.6

`POST /v1/system/fetch-api-key-usage` returned, for that key, **two meters that disagree:**

| Field | Value |
|---|---|
| `cycle_remaining_credits` | **180,980** |
| `cycle_usage_percentage` | 81.9 |
| `total_available_credits` | 1,000,000 |
| `total_credits_used` | **3,864,820** |
| `total_remaining_credits` | **−2,864,820** |

**That meter disagreement is a genuine, separate defect and we still report it** (§8.4 request 2). It is
simply **not** the cause of the empty responses. A key with **2,000,000 credits available and
0 used** produces **exactly the same completed-with-zero-tiles response** for the same request.

### 8.3 The cause is still UNKNOWN — but it is demonstrably not size, key, plan or quota

**Corrected 2026-08-18 (second correction). An earlier version of this section blamed an undocumented
plan-tier request-size cap. That was also wrong.** See §8.6.

The decisive evidence is a fully controlled pair of calls made by our own unattended collector **inside a
single run, roughly 70 seconds apart, on one key**:

| Clock (PKT) | Path | Target window | AOI | `granularity` | Result |
|---|---|---|---|---|---|
| **14:23:17** | forecast | 2026-08-18 14:00-16:00 site-local | 8 x 8 km | 60 m | **`features: []`, `n_cells: 0`** |
| **14:24:34** | history | 2026-08-16 14:00-16:00 site-local | 8 x 8 km | 60 m | **17,862 features, 7.4 MB** |

**Identical key, identical AOI, identical granularity, identical analytic type, same process, same minute.
One returned a full field; the other returned an empty success.** Therefore:

- **Not request size / tile count / granularity** — the successful call was the same 8 x 8 km @ 60 m
  request, returning 17,862 tiles.
- **Not the plan tier or the key** — same key for both.
- **Not credit exhaustion** — and note this key's `total_remaining_credits` read **−2,864,820** at the
  time, yet it returned 7.4 MB of data. **An overdrawn total meter does not stop service**, which retracts
  the first version of this section too (§8.6).

**The only variables that differ are the target window and whether it lay in the future.** The empty
request was for a window still **~8.6 h ahead** at the moment of asking; the successful one was for a
window **~2 days past**. A second probe for an *elapsed* 2026-08-18 02:00-04:00 window, only ~3.5 h past at
the time, was **also empty** — consistent with a processing lag rather than permanently absent data.

**Our current best explanation, offered as a hypothesis and not a claim: data for the requested date was
not yet available in FortyGuard's pipeline when we asked** — the forecast for that window not yet issued,
and the recent past not yet processed. **We cannot confirm this from the API's responses, which is itself
the defect** (§8.5).

**A further controlled test strengthens this.** We re-issued the *full-size* request — 8 x 8 km @
granularity 60, identical AOI and analytic type — for the **2026-08-16** window, i.e.
changing only the key relative to the successful call:

| Key / plan | Window | AOI, granularity | Result | Charged |
|---|---|---|---|---|
| past window | 2026-08-16 (past) | 8 x 8 km, 60 m | 17,862 features | 4,220 |
| **new, `Hackathon`** | 2026-08-16 (past) | 8 x 8 km, 60 m | **17,862 features** | **4,220** |
| new, `Hackathon` | 2026-08-18 (~8.6 h future) | 8 x 8 km, 60 m | **0 cells** | 4,220 |

**So neither the plan tier nor the request size is implicated. The distinguishing variable is the
requested window.** This is why request 3 in §8.7 asks for data-availability semantics to be published.

**A positive finding, worth stating plainly: your historical fields are perfectly reproducible.** The two
rows above were compared tile by tile — **17,862 of 17,862 identical on `average_temperature`,
`min_temperature` and `max_temperature`, identical tile geometry, and identical summary statistics
(mean 26.625009 °C, sd 0.230840 °C); maximum absolute difference 0.00000000 °C.** A settled past window
returns the same field regardless of which key or plan tier asks. For anyone building a validation
pipeline on your API, that is exactly the guarantee they need, and it deserves to be documented as such.

**What we can state without inference:** a well-formed, in-horizon, fully-paid request returned
`status: completed` with zero cells, **while a structurally identical request 70 seconds later returned
17,862 cells**, and nothing in either response explains the difference.

### 8.4 🔴 Empty responses are billed at full price, contradicting the FAQ

**The hackathon FAQ states that credits are consumed only when a task succeeds.** Observed instead:

- **Zero-tile responses are each charged the full 4,220 credits.**
- `POST /v1/system/plan-details` → `activity_breakdown` recorded, at the point we checked,
  **"Heatmap Generation", 8,440 credits, count 2** — i.e. **two empty responses, both counted as
  successful generations and both billed.** 8,440 credits for zero data.

**Combined with §8.3 this is the sharp edge: exceeding a limit you were never told about costs you money
and returns no information about why.** A client discovering their plan's ceiling by trial pays full
price for every probe.

For completeness, and to FortyGuard's credit: **`/v1/system/*` endpoints appear to be free**, and on this
key the meter is live and self-consistent, which is what made the 4,220-per-call figure measurable at all.

### 8.5 Why the empty-success signature is the root problem

**`completed` + zero tiles now means at least four different things:**

| # | Cause | Documented? |
|---|---|---|
| 1 | Request outside the forecast horizon | §1 — inferred by us, not documented |
| 2 | Genuinely empty / no-data area | reasonable |
| 3 | **Requested window not yet available in the pipeline** (our leading hypothesis, §8.3) | **no** |
| 4 | Account credit state — **not our case**: an overdrawn key still served 7.4 MB | no |

1. **A client cannot tell these apart.** We diagnosed #3 only by buying a controlled experiment.
2. **The meter a client would naturally watch is the wrong one.** `cycle_remaining_credits` read
   **180,980 — comfortably positive** — and had been **frozen at that value since the billing cycle closed
   2026-07-19**, so it was stale *and* reassuring simultaneously.
3. **It silently corrupts unattended pipelines.** Ours is idempotent and guarded, so it logged an error
   and moved on. **A client without an explicit non-empty assertion would write empty arrays into their
   database and compute statistics on them.** We only had that guard because defect §1 forced us to add it.

### 8.6 ⚠ RETRACTION — our own error, kept visible

**This section originally asserted quota exhaustion as the cause.** That was **wrong**, and we retract it.
It was inference from a negative `total_remaining_credits` coinciding with the onset of empty responses,
and it did not survive the obvious control: **a fresh key with full credits behaves identically.** We then
briefly hypothesised a forecast-path-specific bug; that was **also wrong** — the elapsed/history path
returns empty for the same AOI.

**Then we asserted an undocumented plan-tier request-size cap. That was ALSO wrong, and we retract it
too.** It rested on comparing a failing 8 x 8 km @ 60 m request against a succeeding 2 x 2 km @ 100 m one —
**but those two calls also differed in target date, in past-versus-future, and in which key issued them.**
Three variables changed at once and we credited the size. The controlled pair in §8.3 — same key, same
size, 70 seconds apart, opposite outcomes — excludes size entirely.

Our original §8.5 did hedge that exhaustion might not be the sole cause and invited correction. **That
hedge was doing real work and we would rather state the correction plainly than rely on it.** The lesson we
have now learned twice: **vary one variable per paid call, and write the hypothesis down before spending.**

**What survives unchanged, and is strengthened:** an empty success is an undiagnosable signal, and it is
billed.

### 8.7 Requests

| | Request | Why |
|---|---|---|
| **1** | **Never return `status: completed` with an empty result for a refusal.** Use a distinct status or an HTTP error, and name the reason: out of horizon / over plan limit / out of credits / genuinely empty | **The single highest-value fix in this document.** It converts silent, undiagnosable data loss into a one-line client check |
| **2** | **Do not bill refused or empty requests** — or if a partial charge is intentional, say so in the docs and return the amount charged in the response | The FAQ says credits are used only on success. We were charged **8,440 for two zero-cell responses**, and `activity_breakdown` logged both as successful *"Heatmap Generation"* |
| **3** | **Publish data-availability semantics**: how far ahead a forecast window becomes retrievable, and how long after an hour elapses its observed field is queryable | This is our leading explanation for the empty responses (§8.3) and we cannot verify it from the API. A client scheduling unattended collection has no way to know when a window is safe to request |
| **4** | **Document any per-plan request-size limits** — AOI extent, tile count, granularity floor, and which binds | We do **not** claim to have hit one; §8.6 retracts that. But we could not rule it out without buying an experiment, which is itself the gap |
| **5** | **State which meter is authoritative, and keep it live** | `cycle_remaining_credits` being **frozen** and **positive** while requests fail is actively misleading |
| **6** | **Surface remaining quota and daily-call count in response headers** | `X-RateLimit-Remaining`-style. Lets a client see a documented daily cap (we understand it to be 30 heatmaps/day) without a second call |

### 8.8 What we are NOT claiming

- **Not** that we know why the empty responses occurred. §8.3 gives a hypothesis, clearly labelled.
  **We have twice been wrong about the cause and say so in §8.6.**
- **Not** that any plan-tier size cap exists. **We retract that claim.** A single key served the same
  8 x 8 km @ 60 m request both successfully and emptily within 70 seconds.
- **Not** claiming the meter disagreement in §8.2 causes anything. It is a separate reporting defect.
- **A definitive account requires FortyGuard's server-side logs**, and we would welcome correction.

---

## 9. `env_params` field defects found while wiring the fields into the agent (2026-08-18)

Found by `INTAKE-ARBITER/src/environment.py`, whose self-test reproduces every number below.
Reproduce with `python environment.py`. **No new API calls were made** — all findings come from
29 `env_params` responses already on disk.

### 9.1 ⭐ `cloud_cover_octas` returns PERCENT, not octas — **it is a units/naming bug, not bad data**

This **supersedes and refines §1.3**, which reported only that the values were "far outside the
octas range". They are not arbitrary: they are a clean percentage.

| Measurement | Value |
|---|---|
| Values examined | **236** across 29 responses |
| Range | **0.0 to 100.0** |
| All integer-valued | **yes** |
| Fraction ≤ 8 (i.e. a valid octas value) | **0.229** |
| Fraction ≤ 100 (i.e. a valid percentage) | **1.000** |
| Distinct values in (8, 100] | **73** |

An octas scale runs 0–8. A field returning 73 distinct integers up to exactly 100 is reporting
**percent cloud cover** under an octas name.

**Why this matters to a consumer, and why it is worth fixing rather than documenting.** Anyone
who trusts the field name divides by nothing and feeds 80 into an 0–8 scale, or divides by 12.5
and turns a **fully overcast sky into an almost clear one**. We use cloud cover to select a
Pasquill-Gifford atmospheric stability class, which sets how quickly a plume disperses. Getting
it backwards pushes the class the wrong way at both ends of the day.

**Requests, in priority order:** (1) rename to `cloud_cover_percent`, or divide by 12.5 and keep
the name; (2) state the units in the schema — the response schema for this endpoint is currently
`{}`; (3) if the intent really is octas, the values are wrong by a factor of 12.5.

**Good news for FortyGuard:** once relabelled the field is immediately usable, and it removes a
real assumption from our model. Our five-year ASOS fixture carries **no cloud field at all**, so
every one of 43,708 classified hours had been treated as CLEAR. Substituting FortyGuard's
measured cloud cover **changes the stability class in 4 of 24 hours** on the first day tested.

### 9.2 ⭐ NEW — `air_quality:idx` is identical to `air_quality_pm2p5:idx`

| Measurement | Value |
|---|---|
| Responses where the two series are equal at every hour | **21 of 29** |
| Comparison | element-wise, `numpy.allclose`, NaN-aware |

The documented-as-overall air-quality index appears to be **the PM2.5 sub-index itself**, not a
composite of the six pollutants also returned (`pm2p5`, `pm10`, `no2`, `o3`, `so2`, plus
`aqi_us_co`). In the 8 responses where they differ, the difference is not obviously a composite
either.

**Why this matters.** A caller reasonably reads `air_quality:idx` as "the headline number" and
the others as its components. If it is just PM2.5 under another name, then **any hour dominated
by ozone or NO₂ is invisible in the headline index** — and ozone is exactly the pollutant that
peaks on hot sunny afternoons, which are the hours a free-cooling controller cares about most.

**Request:** either document `air_quality:idx` as an alias of the PM2.5 sub-index, or make it a
genuine composite.

### 9.3 `:idx` fields carry no documented units or scale

All six air-quality fields are suffixed `:idx`. Neither the OpenAPI schema (the response schema
is literally `{}`) nor the site documents the scale, the pollutant concentration it maps to, or
the standard it follows (US EPA AQI? EU CAQI? a FortyGuard-internal scale?). `aqi_us_co` names a
standard in the field name; the six `:idx` fields do not.

**Consequence for us, stated as a design decision rather than a complaint:** because we cannot
source a numeric limit for an undocumented index, the agent's contamination limit is a **swept
scenario parameter** across the measured range rather than a constant. Measured range over 236
values: **min 15.9, median 50.8, p90 75.2, max 94.0.**

**Request:** publish the scale and the concentration mapping. With it, the gate could be set to a
real ASHRAE/ISO cleanliness limit instead of swept.

### 9.4 What we now use, and the two fields we deliberately refuse

`env_params` returns **hourly arrays — 24 values per field per day**, not the single readings the
absent schema might suggest. Across 29 saved responses that is **3,540 individual hourly
environmental values**, of which 9 responses are full 24-hour series.

| Field | Our use |
|---|---|
| `wet_bulb_temperature_celsius`, `relative_humidity_percent` | the humidity/enthalpy gate — real economizers limit on wet-bulb, not dry-bulb alone |
| `air_quality_pm2p5:idx`, `pm10`, `no2`, `o3`, `so2` | the contamination gate — LBNL measured particle spikes in 8 real data centres when economizer vents opened |
| `cloud_cover_octas` (as percent), `solar_irradiance` | Pasquill stability class, replacing an assumed clear sky over 43,708 hours |
| `precipitation_mm` | damper operation realism |
| ❌ `heat_index_celsius` | **refused — §1.1**: computed from the caller's own `temperature` input |
| ❌ `locations[].temperature` | **refused — §1.7**: echoes the caller's input; the endpoint returns no dry-bulb at all |

**A feature request that would change what we can build:** `env_params` returns humidity and
wet-bulb but **no dry-bulb temperature**, while `heatmap` returns temperature but none of the
environmental fields. Returning dry-bulb in `env_params` — or the environmental fields per tile
in `heatmap` — would let a consumer compute enthalpy from one call at one place and time. Today
it requires two endpoints and an assumption that they refer to the same air.

---

## 10. ✅ RESOLVED — a ~30-HOUR FORECAST OUTAGE, first read as a plan limit

> **⚠ READ §10.7 FIRST. This section was written while forecast windows were failing and its
> conclusions were overtaken on 2026-08-19 13:35 UTC**, when one paid call at identical parameters
> returned **17,862 tiles at a 9.41 h lead**. Forecast windows **are** included on the Hackathon
> plan. The investigation below is kept intact — the exclusions it performed (horizon, request size,
> granularity, time of day, first-poll-empty) were all sound, and the reproducible defect it
> documents is real and still worth reporting: **`HTTP 200` + `completed` + zero features, billed
> 4,220 credits, for ~30 hours, with no incident signal.** What it got wrong was the *cause*.

**Filed 2026-08-19. This is the most consequential finding of the sprint for us, because it stops a
measurement we cannot take any other way.** Reproduced by `testing/diag61_forecast_entitlement.py`.

### 10.1 What happens

A `/v1/heatmap` request whose window lies in the **future** returns `status: completed`, HTTP 200,
`n_cells: 0` and an empty `features` array. The same request shape with a **past** window returns
**17,862 features** on the same key (established by N-55). Every future window tried has failed:

| date | lead to window | result | billed |
|---|---|---|---|
| **past window** 2026-08-16 14:00–16:00 | — | **17,862 tiles** | 4,220 |
| 2026-08-18 | ~8.6 h | **0 tiles** | 4,220 |
| 2026-08-19 | 9.38 h | **0 tiles** | 4,220 |
| 2026-08-19 | **2.29 h** | **0 tiles** | 4,220 |

### 10.2 The variable table, built before any cause was written

Only one variable separates the last success from every failure.

| variable | past-window OK | FAIL | FAIL | FAIL | FAIL |
|---|---|---|---|---|---|
| lead | — (elapsed) | ~8.6 h | 9.38 h | **2.29 h** | 8.86 h |
| AOI | 8×8 km | 8×8 km | 8×8 km | 8×8 km | 8×8 km |
| granularity | 60 | 60 | 60 | 60 | 60 |
| `analytic_type` | tcm | tcm | tcm | tcm | tcm |
| **window direction** | **PAST** | **future** | **future** | **future** | **future** |
| result | **17,862** | 0 | 0 | 0 | 0 |

### 10.3 What is excluded, and what is not

**EXCLUDED — the 12-hour horizon.** This was the leading hypothesis and it is dead. A window only
**2.29 h ahead** returned zero tiles, on the same AOI, granularity and analytic type. A horizon
cannot explain a failure at 2.29 h when 9.498 h succeeded two days earlier.

**EXCLUDED — request size, granularity, plan request caps.** N-55 already settled these: the
Hackathon key returns 17,862 features for 8×8 km at granularity 60 on a **past** window.

**EXCLUDED — time of day.** The 08-19 failure landed at 13:37, three minutes from the 13:30 that
succeeded on 08-16.

**NOT YET EXCLUDED, and we will not claim between them today:**

- **A1 — the Hackathon plan carries no forecast entitlement.** Every future window fails while the
  identical request for a past window succeeds, which is what an entitlement boundary drawn between
  history and forecast would look like. `plan_details` carries no field that would confirm or deny
  it (§10.4).
- **A3 — FortyGuard's forecast path is transiently degraded.** Cannot be separated from A1 by any
  single call. It is separated **for free** by tomorrow's scheduled run: if a forecast succeeds
  tomorrow on the same key, it was transient.

Per this project's own rule — vary one variable per paid call, and tabulate every difference before
writing a cause — **no further paid call is being made today.**

### 10.4 `plan_details` carries no entitlement information

The full payload from `/v1/system/fetch-api-key-usage`:

```json
"plan_details": {"plan_type": "Hackathon", "cycle_type": "Hackathon",
                 "subscription_start_date": "Aug 18, 2026",
                 "billing_period": "Aug 18, 2026 – Sep 22, 2026",
                 "active": true, "credits_reset_date": "Sep 22, 2026"}
```

There is **no field listing which endpoints, analytic types, or window directions the plan permits.**
So a consumer cannot tell in advance whether forecasts are included — the only way to find out is to
spend 4,220 credits and read an empty array.

### 10.5 🔴 The cost, measured by differencing the meter

**Every zero-tile response was billed in full.** Confirmed again, and this is the third independent
confirmation of §8.4:

- `activity_breakdown`: `{"name": "Heatmap Generation", "credits": 21100, "count": 5}`
- **8,440 credits spent on the two zero-tile collector runs.**
- **4,220 credits for the diagnostic above**, which bought a genuine answer.
- Total spend **21,100 of 2,000,000 (1.06 %)**. Budget is not the constraint; capability is.

An empty result is not a free result, and a consumer with a daily collector will burn credits
indefinitely on a capability they do not have, with no error telling them so.

### 10.6 Requests, in priority order

1. **State plainly whether the Hackathon plan includes forecast (future-window) heatmaps.** One
   sentence resolves this. If it does not, we will say so in our submission and stop trying.
2. **Return an ERROR, not `completed` with zero tiles, when a request is outside the plan's
   entitlement.** HTTP 403 with a reason, or a `status` other than `completed`. An empty success is
   indistinguishable from an empty area, an out-of-horizon window, and a permission failure — four
   different causes, one response.
3. **Do not bill an entitlement failure.** 8,440 credits were charged for two responses that could
   never have contained data.
4. **Add an entitlement block to `plan_details`** — which endpoints, which `analytic_type` values,
   and whether future windows are permitted.
5. If forecasts *are* included and this is an outage, **an incident signal on the status endpoint**
   would have saved four paid calls and two days of a time-boxed collection.

### 10.7 ✅ RESOLVED 2026-08-19 13:35 UTC — it was an OUTAGE, not an entitlement

**This section previously concluded that 65.6 % coverage had become permanent and that the
"~10 calibration days" plan was blocked by capability. That was wrong, and the correction is
recorded here rather than deleted.**

One paid call (`DIAG-62`, authorised by the user) at **exactly** the collector's parameters — 8×8 km
on the committed centre, `granularity: 60`, `analytic_type: tcm`, a 2 h window, and a **9.41 h lead**
reproducing the N-25 reference lead — returned **17,862 tiles in 35.7 s with zero
completed-but-empty polls**. `activity_id` `f333f605-6ef6-4847-9bbf-1d22910ebcb6`.

**Verified as a genuine forecast before this was written:** the lattice is identical to the
past-window fixtures (17,862 of 17,862 tile keys shared), **0 of 17,862 values match** the
2026-08-16 field, the difference is spatially varying (mean +0.56 °C, range −0.36 to +1.10 °C), and
30.32–32.30 °C is plausible for 19:00–21:00 on an August evening in Virginia.

**What pins it to an outage rather than a plan limit:** the automated collector failed at
**08:30 UTC the same day** ("completed but never populated after 58 polls over 607 s") and this call
succeeded at **13:35 UTC**. A five-hour recovery. **An entitlement cannot appear during a day.**

| | |
|---|---|
| Outage window observed | **2026-08-18 → 2026-08-19 08:30 UTC**, at least ~30 h |
| Zero-tile forecast responses | **seven**, two through the corrected polling loop |
| **Credits billed for nothing** | **≈29,540** |
| Recovery confirmed | 2026-08-19 **13:35 UTC**, 17,862 tiles |

**Consequences for us:** the 4-pair ceiling lifts, ~10 pairs makes a 90 % bound attainable again, and
**65.6 % returns to provisional — though it stays the only figure we quote until the pairs exist.**

**§10.6's requests still stand, and the outage strengthens rather than weakens them.** Request 1 is
now answered (forecast windows *are* included). Requests 2, 3 and 5 are the important ones: for ~30
hours this API returned `HTTP 200` + `status: completed` + zero features **and billed 4,220 credits
per call**, with nothing on the status endpoint to distinguish a vendor incident from an empty area,
an out-of-horizon window, or a permission failure. **A client cannot tell an outage from a
capability limit, and pays either way** — we spent two days and ~29,540 credits concluding the wrong
one. An incident signal, a non-`completed` status, or simply not billing an empty result would each
have prevented it.
