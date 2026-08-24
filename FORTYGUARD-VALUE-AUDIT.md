# How much of FortyGuard's data are we actually using? — an honest audit

**Written 2026-08-23, after the question: "is the only value we portray the forecast?"**
Short answer: **no, but very nearly yes in the place that matters most — the live agent.** There are
two concrete, testable gaps, and one of them would remove the single biggest limitation in the whole
product.

Sources: `fortyguard-api-findings.md` §9.4 (what `env_params` returns), the 30 saved `env_params`
fixtures, `src/environment.py`, `src/agent.py`, `src/live.py`, and the paid probe
`testing/results/fixtures/n15_ep_future.json`.

---

## 1. What their API offers, and what we do with each part

| Endpoint | What it returns | Cost | Our use today |
|---|---|---|---|
| **`/v1/heatmap`** | a 17,862-tile temperature field over 8×8 km at 2 m, past **and forecast to 12 h** | 4,220 | ✅ **The core input.** The site's own tile is the agent's dry-bulb perception, live and in the calibration record |
| **`/v1/env_params`** | **hourly arrays, 24 values per field**: `relative_humidity_percent`, `wet_bulb_temperature_celsius`, six air-quality indices, `cloud_cover_octas`, `solar_irradiance`, `precipitation_mm`, `methane_ppb` | 2,900 | ⚠️ **Used in the five-year model, NOT in the live agent** — see §2 |
| `/v1/satellite` | imagery | 14,400 | ❌ Probed and dropped: returns no building footprints, and OSM gives us those free |
| `/v1/heat_intelligence` | a 748 KB PDF report | 8,600 | ❌ Probed and dropped: **leaks the caller's API key in the `download_link` path** (reported to them) |
| `/v1/streetview` | — | — | ❌ Never completed inside a 240 s timeout |
| `/v1/status/{id}`, usage/plan endpoints | job state, credit meter | **free** | ✅ Used throughout; the meter is what makes the spend ledger possible |

**So two endpoints carry real value for this problem, and we use both — but not equally, and not
everywhere.**

---

## 2. ✅ CLOSED 2026-08-23 (E2 implemented) — the gap that mattered

> **STATUS UPDATE.** Everything in this section describes the state **before** E2. The integration is
> now in `src/live.py`: one `env_params` call per run supplies the humidity gate from FortyGuard's
> own `wet_bulb_temperature_celsius` and adds a contamination gate on their PM2.5 index, with the
> source recorded per hour and NWS retained as the fallback. Verified offline — `live.py selftest`
> now covers the hour-alignment detector against a known shift, the fallback, and the refused fields.
> ⚠ **Not yet exercised end-to-end**, because a full live run also needs `heatmap`, which has
> returned nothing for five days. The section below is kept as the record of why it was built.

### The gap, as it stood: the LIVE agent ran on ONE FortyGuard variable

The agent gates on the three things a real economizer gates on. Here is where each gate's data
actually comes from:

| Gate | Five-year backtest | **Live agent** |
|---|---|---|
| **1. Dry-bulb temperature** | ASOS station record | ✅ **FortyGuard heatmap** |
| **2. Humidity / dew point** | ASOS `dwpc` | ❌ **NWS** (free, keyless) |
| **3. Air quality / contamination** | FortyGuard `env_params` — diurnal shape from 30 saved days | ❌ **not evaluated at all** |
| Atmospheric stability (cloud → Pasquill) | FortyGuard `env_params` | ❌ not used |
| Wind bearing and speed | ASOS | ❌ **NWS** — FortyGuard has no wind field (our filed feature request, findings §6) |

**The live card — the thing that demonstrates agency, and the first thing a judge clicks — perceives
exactly one FortyGuard number per hour.** Everything else in that decision comes from a free US
government API.

That is defensible on cost and it is *documented* (`live.py` explains that `env_params` returns no
dry-bulb while `heatmap` returns no environmentals, so one place and time already needs two calls,
and NWS gives dew point and wind together for nothing). But it badly under-sells the vendor whose
data the project is built on, and it makes the LBNL argument — *contamination and humidity are the
documented reasons operators refuse free cooling* — an argument the live agent never actually acts
on.

### The decisive fact, from our own paid probe

**`env_params` serves the forecast horizon.** `testing/test_n15_forecast_state.py` requested
`now + 6 h` and got a complete parameter set back —
`testing/results/fixtures/n15_ep_future.json`: RH **87.2 %**, wet-bulb **22.6 °C**, cloud **100 %**,
precipitation **0.3 mm**, and all six air-quality indices. The test's own comment records that it
had also served future values on 2026-08-08.

**So all three gates could run on FortyGuard's own 12-hour forecast, for one extra call of 2,900
credits per run.**

### What that changes about the story

| Today | With one `env_params` call added to `live.py` |
|---|---|
| "We use FortyGuard's temperature forecast." | "**Every gate a real economizer needs — temperature, humidity and contamination — runs on FortyGuard's 12-hour forecast.** The only input we go elsewhere for is wind, which they do not offer and which we have filed as a prioritised feature request." |

It also closes a real hole in the argument: LBNL's instrumented study of eight data centres is the
**commercial thesis** of this project, and it says contamination is the reason operators refuse free
cooling. FortyGuard sells six air-quality indices. Right now the live agent ignores them.

**Effort:** small. `live.py` already batches, polls and classifies vendor calls; `environment.py`
already parses every one of these fields and audits two of them as defective. It is one more call in
`perceive_ambient()` and a gate evaluation that already exists.

---

## 3. 🔴 The bigger idea: their field could replace the customer's thermometer

This is the one worth thinking hardest about, because it attacks the **single biggest weakness in the
product**.

**The weakness:** the agent's headline needs a *level anchor* — one local temperature reading at the
site — to correct FortyGuard's absolute level. Measured over five years, without it the agent
**loses 156 h/yr** instead of gaining 406. That is a swing of about **562 h/yr**, and it is the
honest limit stated on the demo's front page: *"the safety guarantee needs no customer hardware; the
hours do."*

**Why the anchor is needed:** the weather station is **9.38 km** from the committed Ashburn site.
Nobody knows the temperature difference between the station and the plant's own air, so the agent
either measures it with customer hardware or carries a wider bound.

**That difference is exactly what a 2 m urban heat product is for.** A single `heatmap` call over a
box containing **both the site and its ASOS station** would give the station→site offset directly,
from FortyGuard's own field — no customer sensor, no installation, no procurement.

If that works, it converts the product's biggest caveat into a second reason to buy FortyGuard data.

**What it would take, measured rather than guessed:**

- The box must contain both points: 9.38 km apart, so roughly **21 × 21 km**.
- At granularity 60 m that is ~120,000 tiles, well beyond the 17,862 we have seen returned. At
  granularity 100 m it is ~43,000. **Whether the API returns a field that large is unknown and must
  be tested** — findings §3.2 records that spatial information content is set by AOI size rather
  than granularity, which is encouraging but not the same question.
- Validation is free once the field exists: we hold **43,763 hours** of KIAD observations, so the
  field's predicted station→site offset can be scored against the station's own record on the days
  we already have.

⚠ **This is a hypothesis, not a result.** It rests on FortyGuard's 2 m field genuinely resolving a
9 km microclimate gradient, which we have never tested. The honest framing for a judge is *"here is
the biggest limitation, here is the specific FortyGuard capability that would remove it, and here is
the experiment"* — not a claim that it works.

⚠ It is also **blocked today**: the vendor has returned `completed` with zero cells for every window,
past and future, for five days.

---

## 4. What we are already doing well, and should say louder

Not everything is a gap. Two things are genuinely load-bearing and under-stated:

**The air-quality data is already in the five-year model.** `agent.py` measures the **hour-of-day
PM2.5 profile** from 30 saved `env_params` responses and uses it in the contamination gate across
43,708 hours. It is honestly labelled — the FortyGuard series are 2026 and the weather days are
2021-25, so they are paired by diurnal shape rather than by date, and the gate binds only **0.1 %**
of hours. But it is real FortyGuard data doing real work.

**Their cloud-cover data replaced an assumption.** Atmospheric stability (the Pasquill class that
drives plume dispersion) used to assume clear sky across every one of 43,708 hours. It is now derived
from FortyGuard's `cloud_cover_octas` and `solar_irradiance`. That is FortyGuard data feeding the
*physics*, not just the gates — and finding §9.1 records that we also caught their field returning
**percent while named octas**, which we reported.

**We also refuse two of their fields, on evidence** — `heat_index_celsius` (computed from the
caller's own input, findings §1.1) and `locations[].temperature` (echoes the caller's input, §1.7).
Refusing bad fields while using the good ones is a stronger signal of engagement than using
everything uncritically.

---

## 5. Recommendation, in priority order

| # | Action | Cost | Why |
|---|---|---|---|
| **1** | **Add one `env_params` call to the live agent** so the humidity and air-quality gates run on FortyGuard's forecast instead of NWS/nothing | 2,900 credits per run | Turns "we use their temperature" into "every gate runs on their forecast". Small code change, large story change. Directly exercises the LBNL contamination thesis |
| **2** | **Test the wide-AOI station→site offset** — one heatmap call over a box containing both, granularity 100 m | 4,220, one call | If it works it removes the −156 h/yr anchor caveat, the product's biggest limitation, and makes FortyGuard's *spatial* data load-bearing rather than worth +0.036 °C |
| 3 | Say §4 out loud in the submission | free | The AQ profile and the cloud-derived stability are already FortyGuard data doing real work and are currently buried |

**Both 1 and 2 need the vendor's data path to work**, and it has returned empty for every window —
past and future — since 18 August. Neither is worth attempting until that clears.

**And a caution on #2:** it is the more exciting one and it is also unvalidated. If it is put in the
submission at all it must be framed as *the experiment we would run next*, with the reason it is
blocked, and not as a capability. This project's credibility rests on not doing that.
