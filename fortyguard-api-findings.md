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
