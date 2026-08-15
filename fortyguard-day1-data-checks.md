# FortyGuard API — Pre-Build Assumption Audit & Day-1 Verification

**Purpose:** find out whether the design is actually executable against this API, before writing code.
Every check below names the **design assumption it validates**, so a failure tells you what to change,
not just that something broke.

**How to use:** follow the **run sheet** below, not the group order. The groups are organised by topic
so you can find things; the run sheet is organised so that nothing expensive happens before a check
that could invalidate it. Record raw responses, not summaries.

**Time needed:** Day 0 (zero credits, no API key required) is ~half a day. Day 1's blocking checks are
another half day. The rest can be discovered while building.

---

## Scope note — what this document does and doesn't change

This is a verification document. The **master plan** is
[project-master-plan.md](project-master-plan.md) — read that for the architecture, the bottleneck
ladder, and the edge-case register. This file is the protocol that de-risks it.

**One thing changed in [nvidia-integration-plan.md](nvidia-integration-plan.md), and it matters.** That
plan assigned Earth-2's ensemble spread the role of *the* conditioning variable for the conformal layer
(NVIDIA §2). The hackathon is judged by **FortyGuard**, so that role now belongs to **FortyGuard's own
spatial field** — `stats_data.stddev`, tested by **K-9** — and Earth-2 becomes an **optional second
feature** in the same conditioning scheme. The two signals are genuinely orthogonal (*when* is the
atmosphere volatile, versus *where* is the field structured), so having both is stronger than either
alone; only the priority changed.

Everything else in the NVIDIA plan stands: local Nemotron for the explanation layer, the DCGM-schema
load stub, the fallback volatility signal, RAPIDS as a stretch goal. Two checks feed it: **I-2** is
where the fallback volatility signal comes from (NVIDIA §3.4), and the psychrolib work in **B-8** serves
the FortyGuard wet-bulb fallback, the per-tile derivation path (E-8), and the Earth-2 path — write it
once.

It also changes nothing in [the learning plan](i-m-a-second-semester-computer-zazzy-hennessy.md). It
does, however, correct one thing: the learning plan's Tier 2 #14 says you can "bootstrap the
calibration set by pulling historical forecasts." **See Z-1 and Group K — that is almost certainly not
available, and the correction matters.**

---

## Glossary

The rest of this document uses these words. They're defined here because the learning plan introduces
them later than you need them.

| Term | Plain meaning |
|---|---|
| **Collector** | A small Python script that runs once an hour, calls the API, and appends numbers to a file. Runs on your laptop. Nothing physical, no travel. |
| **Issuance time** | *When you asked.* At 09:00 you ask about 15:00 → issuance time is 09:00. |
| **Valid time** | *What you asked about.* In that example, 15:00. |
| **Horizon** | The gap between them — 6 hours. A 1-hour-ahead guess is much better than a 12-hour-ahead guess, so residuals must always be grouped by horizon. |
| **Residual** | How wrong a guess was. Predicted 18.0 °C, turned out 19.4 °C → residual 1.4 °C. |
| **Calibration set** | A big pile of past residuals. Your track record of being wrong. Conformal prediction is built entirely from this. |
| **Observation** | A number that came from a real physical instrument. |
| **Hindcast** | A number a computer model produced *about the past*, after the fact. Looks like an observation but isn't one — nobody stood there with a thermometer. |
| **Autocorrelation** | Nearby things resemble each other. Today's forecast error resembles yesterday's, so 24 hourly errors from one day carry roughly one day's worth of information, not 24. |
| **Effective sample size (n_eff)** | How many *genuinely independent* data points you have, after accounting for autocorrelation. Always smaller than your row count. This is the number that matters. |
| **Land-surface temperature (LST)** | The temperature of the *ground itself*, measured by satellite. A sunny car park can be 55 °C while the air 2 m above it is 35 °C. Your project needs the **air** number. |
| **Wet-bulb globe temperature (WBGT)** | A different, confusingly-named quantity used for sports heat-safety warnings. Not what you want. B-8 rules it out. |
| **psychrolib** | A free Python library that does the physics of moist air. Give it temperature and humidity → it gives you wet-bulb. |
| **METAR** | The hourly weather report published by every airport, from real instruments on the ground. Free, archived for decades. |
| **Fixture / replay mode** | Saved copies of real API responses, so you can run the agent (and demo it) off files instead of the live internet. |
| **Marginal vs joint coverage** | "Each hour's bound is right 90% of the time" (marginal) is a much weaker promise than "the bound holds for *all 12* hours 90% of the time" (joint). Your agent needs joint. See K-7. |
| **Field** | Values across a whole area, not at one point. A heatmap returns a field. This is FortyGuard's actual product, and the design is now built around it rather than around point lookups. |
| **Tile** | One cell of a heatmap. At granularity 60, one tile is roughly 60 m across. |
| **σ_spatial** (`stats_data.stddev`) | How much the values *disagree across the tiles* of one heatmap. Small = a smooth, well-mixed air mass. Large = sharp gradients moving over the site. **This project's central bet (K-9) is that a large σ means the forecast is less trustworthy** — so the safety margin is scaled by it. |
| **Coarse-to-fine** | Ask for the cheap 100 m field first, look at σ, and only pay for 60 m over the hot corner if the field looks structured. The agent's main real decision, and it *saves* credits rather than spending them. |
| **Exceedance** | A count of hours above or below a threshold. Also a FortyGuard heatmap mode — "how many of the next 12 hours are below X, per tile" is very nearly this project's question, computed by the API (F-2). |
| **Persistence (heatmap mode)** | Consecutive-run semantics — "how long a stretch stays below the threshold." Not to be confused with a *persistence forecast* (below). See F-3. |
| **Persistence forecast** | The baseline "conditions will stay exactly as they are now." Deceptively hard to beat, and the reason K-9's Stage 1 can be run on thousands of historical hours without waiting for collected data. |
| **Heat island** | Built-up areas running warmer than their surroundings. Strongest on calm nights — which is exactly when a marginal free-cooling call is being made. |
| **Leave-one-station-out** | Hide one airport's readings, predict that spot, and score against what that airport actually measured. The only test in this project judged by a real thermometer rather than by a model's own hindcast. See W-6. |

---

## Locked design decisions

These are settled. The checks below assume them.

**1. Three sites, three unrelated climates.**

| Site | Why | Climate character |
|---|---|---|
| Ashburn, Virginia | World's largest data center market — instantly recognisable | Hot, humid summers → free cooling is genuinely hard in July |
| Phoenix area, Arizona | Counterintuitive result: very dry air means wet-bulb sits far below dry-bulb, so free cooling works better than the temperature suggests | Hot, arid |
| Hillsboro, Oregon | Established market, cool marine air | Free cooling viable nearly year-round |

Reason for three rather than one: errors in Phoenix are unrelated to errors in Oregon, whereas 24
consecutive hours in Virginia are all telling you roughly the same thing. Three unrelated climates is
the only available way to raise n_eff on this timeline (see K-6).

**2. METAR airport data is a core dependency — but it is NOT the conformal layer's truth source.**

Conformal prediction scores *your forecast for the site* against *what happens at the site*. The
airport is a different place and cannot substitute for that. METAR's four jobs, in priority order:

- **(a) Trust check on the truth source.** Your site "actual" is a hindcast from the same model that
  made the forecast — the system grading its own homework. METAR is the only real physical measurement
  anywhere in this project. Check W-3 uses it to confirm FortyGuard tracks reality at all. The two are
  *expected* to differ; that difference is your entire project. What you're ruling out is a gap that
  physics and distance can't explain.
- **(b) Your baseline.** "Current systems use the distant airport station" — that station **is** the
  METAR. You need it regardless, for the headline number.
- **(c) Emergency backup.** If K-3 finds zero residuals, METAR is the only remaining source of real
  ones. Contingency, not the main path.
- **(d) Optional bonus.** A *separate* conformal bound on "how much warmer is my site than the
  station," buildable on day 1 from years of history. Nice, and a good talking point — but it answers a
  different question, so it is a supplement, not a shortcut.

**3. Full 12-hour safety window, calibrated with a max-over-horizon score.** One residual per
collection run — the worst hour across the whole window — rather than twelve separate per-hour
residuals. This is what makes a genuine joint guarantee reachable from the data you'll actually have.
See K-7. Per-hour marginal coverage is still reported alongside, for comparison.

**4. ⭐ The design is field-first, not point-first — and the field sets the margin.**

The unit of perception is a **heatmap over a campus polygon**, not an `env_params` point. Two things
follow, and they are why Groups S, F and K-9 were re-prioritised:

- **`stats_data.stddev` — the spatial spread across the campus tiles — is the conditioning variable for
  the conformal margin.** Hypothesis H1 (K-9): forecast error is larger when the field is sharply
  structured than when it is smooth. If it holds, the margin widens on structured days and tightens on
  smooth ones, automatically, from a physical signal.

  This is the decision that makes the project **FortyGuard-specific.** Split conformal on a point
  forecast is provider-agnostic by construction — its whole selling point is treating the predictor as an
  interchangeable black box — so it would work identically on a free point-forecast API. Conditioning the
  margin on spatial structure does not. **A point API cannot supply σ_spatial.**
- **`exceedance` (`direction: below`) and `persistence` are decision primitives, not extras.**
  "Hours below threshold per tile" and "longest consecutive safe run per tile" are near-exact matches for
  the question the agent exists to answer. F-2 and F-3 moved from NICE/P2/P3 to **B-CODE**.

Consequence: **Z-4 was rewritten around heatmap costs**, and heatmap cost (A-3 + **S-1**) is now the
single largest risk in the project. Z-4's degradation ladder is deliberately ordered so σ_spatial is the
last thing to be cut.

Full reasoning, the substitution test, and the bottleneck ladder:
[project-master-plan.md](project-master-plan.md) §2.5, §7.6, §11.1.

---

## Priority key

The old single P0–P3 scale conflated three different kinds of "blocking." Use both columns.

| Tag | Meaning |
|---|---|
| **B-CODE** | If this fails, the **architecture** changes. Resolve before writing the agent. |
| **B-DATA** | If this fails, **data you collect from day 1 is unusable or unrepeatable.** Resolve before the collector starts. This is the category people discover too late. |
| **B-CLAIM** | Code still works, but something you'd say about the project would be untrue. Resolve before the writeup. |
| **NICE** | Implementation detail. Discoverable while building. |

Legacy P-tags are kept in the check titles so any notes you've already made still read.

---

# ⚑ THE RUN SHEET

Do these in this order. Do not skip ahead.

### ⚑ TIER 0 — free, no API key, DO THESE FIRST (Aug 9–17)

| # | Check | Status | Why here |
|---|---|---|---|
| 0 | Read the glossary above | — | Everything else assumes it |
| 1 | **Z-5** facility + control registers; **the density gate** | ✅ **DONE** — passed across 4 metros | If facilities aren't within ~800 m of each other there is nothing to measure. **99 % of Ashburn facilities are** |
| 2 | **Z-7** effective-resolution decay | ✅ **DONE — PASSES** | **The highest unexamined technical risk.** If the field were smoothed at 500 m, a 500 m plume would vanish. It isn't: signal-to-background is **8–24×** |
| 3 | **T-3** usable-day census | ✅ **DONE** | **Only 34 % of days are usable** → the interference matrix must be built from **history**, not live accumulation. This changed the plan |
| 4 | **Z-6** optimal polygon placement | ✅ **DONE** | **8 × 8 km at 39.0100, −77.4460 → 168 usable facilities in one call.** The already-paid-for polygon had 6, none usable |
| 5 | **⚠ R-2** can free data predict the field? | **TODO — before Aug 18** | **The substitution test, quantified. R² > 0.9 and the premise collapses.** Costs nothing |
| 6 | **⚠ U-1** does the interference change any decision? | **TODO** | Gates the entire money half. **~200 h/yr → real; ~5 h/yr → worthless.** Costs nothing |
| 7 | **P-4** rotation placebo · **T-1** geometry sweep · **T-2** spatial n_eff | TODO | All computable on saved data |
| 8 | **Q-3** contamination screen · **Q-4** control matching | TODO | **A warehouse inside a plume is not a control.** Getting this wrong hides a real effect |
| 9 | **Z-1** request-schema audit · **Z-3** freeze the log schema · **Z-4** credit budget | ✅ / TODO | Z-1 settled; Z-3 is **irreversible** so do it before any collection |
| 10 | **W-1, W-2, V-2 (=W-6)** METAR history and the multi-station leave-one-out | TODO | Free, and **the only check judged by a physical instrument** |

### ⚑ Aug 18 morning — the ~14-call sheet. **Every decisive call is HISTORICAL, so nothing waits on weather.**

| # | Call | Decides |
|---|---|---|
| 0 | usage read | Price baseline |
| 1 | heatmap over the **Z-6 polygon** (8 × 8 km, 39.0100 −77.4460, g60, ft2) → usage read | **PRICE.** Everything re-budgets off this. Also delivers the field for calls 6 and 7 |
| **2** | **⚑⚑ P-2 wind-following** — same facility, two historical days ≥120° apart | **Does the warm side MOVE? World A vs World B. The single most important call in the project** |
| **3** | **⚑ P-1 answer key** — Chandler (169 MW) | Do we reproduce Sailor's published 0.7–0.9 °C? |
| 4 | **P-1b** — Mesa (36 MW) | Second independent check against the answer key |
| 5 | **P-3** calm-day negative control | No wind ⇒ no directional lobe. If a lobe appears, it's land cover |
| 6 | **Q-1 / Q-2** control sites | **Free — inside call 1's polygon.** The null distribution, and the instrument-blindness test |
| 7 | **R-1** paved vs vegetated tile amplitude | **Free — inside call 1.** Air or surface, within one scene |
| 8 | **R-3** hot day vs cool day | **Does the field respond to weather at all**, or is it a climatology? |
| 9–11 | History bisection 2025 / 2023 / 2021 | How far back V-1 can reach (2019 fails) |
| 12 | **V-1** before/after commissioning, if depth allows | **Separates construction from operation — immune to every land-cover confound** |
| 13 | `heat_intelligence`, one facility, **2** analysis types (Premium cap) | The LLM's adjudication input |
| — | **then re-budget everything against the measured price** | |

### Day 1 also, if credits allow — the original API checks

| # | Check | Why here |
|---|---|---|
| 8 | **A-1** auth → **A-2** plan → **A-3** + **S-1** cost per call, per configuration → **A-7** credit window | You cannot interpret anything else without these. **S-1 is the gate on the whole field design** |
| 9 | **B-1** does `env_params` take a future time | The original blocking question |
| 10 | **B-5** is that future value *actually a forecast* | **Passing B-1 is not enough.** B-5 is the check that catches a fake forecast — and a server-side `exceedance` count from a fake forecast is a fake count |
| 11 | **F-1** the mode parameter → **E-8**/**S-6** does any mode carry wet-bulb | The biggest fork in the spatial design. Everything in Group S downstream needs F-1's parameter name |
| 12 | **S-7** does `filter_type=2` cover 12 h in one call | The ~12× credit lever. Z-4's arithmetic collapses without it |
| 13 | **B-4** what the `temperature` input does, + forecast humidity | The fallback path if B-1 fails, **and** the per-tile derivation path if E-8 fails |
| 14 | **B-7** does `env_params` work standalone | If not, every point sample costs double. Less painful now that the heatmap is primary |
| 15 | **B-8** psychrolib triple cross-check | Validates units, field alignment, wet-bulb definition, and your own formula — in one test |
| 16 | **B-6** 2 m air temperature or land-surface temperature | A 20 °C category error |
| 17 | **S-2** campus field shape and size → **S-3** ⚠ does `stats_data` give a **spatial** stddev | **S-3 is the check the entire uncertainty contribution rests on.** If σ_spatial doesn't exist, find out now |
| 18 | **G-1** heatmap latency | Now B-CODE: a granularity-60 campus heatmap × 3 sites must fit inside the hour |
| 19 | **C-2** time step → **C-1** timezone → **B-2** horizon ladder → **B-3** metadata fields | Fixes the shape of every request you'll ever make |
| 20 | **K-4** how soon after hour T is the "actual" available | Sets the collector's second job's cadence |

### Day 1, afternoon — ⚠ GATE, then start the collector

> **Do not start the collector until Z-3 (log schema) and Z-4 (budget) are done, and B-1/B-5/S-3 have
> answers.** Everything the collector writes is unrepeatable. Starting it with the wrong schema is
> worse than starting it a few hours later — and **S-3 determines whether σ_spatial is a column at all,**
> which is exactly the kind of omission that cannot be fixed retroactively.

| # | Check | Why here |
|---|---|---|
| 21 | **Start the collector** | Most time-critical action in the project. Every hour not collected is gone forever |
| 22 | **W-3** truth-source trust check | Uses W-1's data; no FortyGuard credits |
| 23 | **G-2**, **G-3** polling behaviour | You need these to make the collector reliable |
| 24 | **F-2**, **F-3** / **S-4**, **S-5** — `exceedance` and `persistence` | The decision primitives. Also what **A1** (the free-cooling-hours map) is built from, and A1 needs no waiting |

### Day 1 evening → Day 3 — everything else

Run in group order: A-4, A-5, A-6 · C-3…C-11 · D-1…D-6 · E-1…E-8 · S-8, S-9 · G-4…G-6 · H-1…H-8 ·
I-1…I-4 · W-4, W-5, **W-6 part B**.

**S-8** (grid stability) deserves attention rather than a skim: if the tile grid re-anchors per request,
per-tile time series are invalid and **A1 must be rebuilt on a self-defined lattice.** Better to know in
week 1 than in week 4.

### Requires waiting — schedule these, don't forget them

| When | Check |
|---|---|
| +6 h | **K-2** frozen-forecast test, **I-2** forecast revision |
| +1 day | **K-3** zero-residual guard ← **the most dangerous silent failure. Do not skip.** |
| +1 day, +7 days | **I-1** / **K-5** are past values silently revised |
| +3 days | **K-6** effective-n arithmetic, **K-7** joint-coverage feasibility |
| +1 week | **K-8** cross-site pooling and per-site coverage |
| **Week 1, no waiting needed** | **K-9 Stage 1** — the well-powered historical H1 pre-test. Runs on FortyGuard history plus persistence residuals, so it needs no collected data. **Do it early:** if H1 fails here with thousands of samples, you learn in week 1 rather than week 4 |
| **+3 weeks** | **K-9 Stage 2** — the live H1 test on real forecast residuals |

---

## Before you start — two reassurances

1. **Testing is nearly free.** The docs state that requests rejected for bad input return an error and
   are *not charged*, and that tasks failing during processing don't consume credits either. You will
   not meaningfully dent 1,000,000 credits doing this.
2. **A failed check is a successful test.** An error message is data. Don't quietly fix things and move
   on — record what broke, and the exact text.

---

## Reference: what the docs already told us

Confirmed from documentation, so you needn't re-verify — but watch for contradictions:

- **Auth:** header `api-key: YOUR_API_KEY`
- **Endpoints:** `POST /v1/heatmap`, `POST /v1/env_params`, `GET /v1/status/{activity_id}`,
  `GET /v1/system/fetch-api-key-usage`, plus satellite / streetview / heat_intelligence (premium)
- **Async:** POST returns an `activity_id`; poll status until `Completed` / `Failed`
- **Date range:** 2019-01-01 → present. Create Heatmap additionally: up to **now + 12 hours**
- **filter_type:** `1` = Single Hour, `2` = Range of Hours (max 23 hrs), `3` = Single Day
- **granularity:** 60m / 80m / 100m
- **Coverage:** United States only, current release
- **Heatmap max area:** 10 mi² (Basic/Startup), 50 mi² (Premium)
- **Env params limit:** 3 parameters per request (Basic/Startup), all (Premium)
- **Wet-bulb field name:** `wet_bulb_temperature_celsius`, inside `locations[].parameters`
- **Credits:** deducted only on `Completed`

**What the docs did NOT say** — the numeric rate limit, the credit cost per call, the forecast time
step, whether `env_params` accepts future times, what the `temperature` input field does, whether any
forecast archive exists, and whether the values are air or surface temperature.

---

# GROUP Z — Day 0: zero credits, no API key required

The four highest-leverage checks in this document are here, and none of them cost anything.

### Z-1 (B-CODE) — Is there a forecast *archive*, or only observations?

**Assumption validated:** C5.1 — that you can retrieve *what the API predicted for a past time*,
alongside what actually happened, and therefore build a calibration set retrospectively on day 1.

**Why this is a documentation check and not an experiment.** To ask "on 15 July at 08:00, what did you
predict for 14:00?" a request must express **two independent times** — the valid time (14:00) and the
issuance time (08:00). Read the full request schema for `/v1/env_params` and `/v1/heatmap` and list
every time-related field.

**Do:** enumerate the request fields. Look specifically for a *second* time concept — anything like
`issued_at`, `reference_time`, `run_time`, `model_run`, `forecast_reference_time`, `as_of`, `version`.

**Pass:** a second time field exists → you can build the calibration set from history immediately.
Test it, then celebrate, because your timeline just got much easier.

**Fail (expected):** exactly one time concept (`date`, `start_time`/`end_time`, `filter_type`). A
single-time API can only return one series per (point, valid time), and the natural product choice is
"best estimate for that time" — an observation or hindcast. **The archive does not exist.**

**Workaround:** collect forecast/actual pairs live, starting day 1. See the whole of Group K.
**Cost:** your calibration set can only be as long as the time since you started collecting. This is
the single largest schedule constraint in the project, and it is why the collector comes before the
agent.

**Optional confirmation (costs a few credits, do it on day 1):** send `env_params` with a speculative
extra field such as `"issued_at": "2024-07-15T08:00:00Z"`, twice with different values. If the response
is byte-identical both times, the field has no effect and the verdict is confirmed behaviourally.

---

### Z-2 (B-CLAIM) — Pick the exact coordinates, and find each site's nearest station

**Assumption validated:** V6.1 — that each site has a usable METAR station with history covering your
backtest period, at a distance where a real site-vs-station gap exists.

**Do, for each of the three sites:**
1. Pick a candidate point. Rough anchors to start from — **these are city-level and must be refined,
   not copied**: Ashburn VA ≈ 39.04 N, −77.49 W · Phoenix metro (the data center clusters are in Mesa,
   Chandler and Goodyear, not downtown) ≈ 33.3–33.5 N, −111.8 to −112.4 W · Hillsboro OR ≈ 45.52 N,
   −122.99 W.
2. Find the nearest METAR station and compute the distance. Candidates worth checking: **KIAD**
   (Dulles) and **KJYO** (Leesburg) for Ashburn; **KPHX** (Sky Harbor), **KCHD** (Chandler) and
   **KGYR** (Goodyear) for the Phoenix area; **KHIO** (Hillsboro) and **KPDX** (Portland) for Oregon.
   Do not trust my distances — measure them.
3. Confirm the station has hourly history covering your intended backtest period.

**Pass:** each site has a station **5–30 km away** with continuous hourly history. Far enough that the
microclimate gap is real, close enough that the comparison is meaningful.

**Fail:** station is <2 km away → there is no gap to demonstrate; move the site or pick a different
station. Station history has large holes → pick another station.

**Workaround:** if no suitable station exists near a site, swap the site. There are many US data center
markets. **Cost:** none if you do this on day 0. Significant if you discover it in week 2, because
your collected data will be about a site you can't make a claim for.

**Also record:** the elevation of each site. Phoenix-area sites sit around 300–400 m, which matters for
D-6 and for the Stull sea-level caveat.

---

### Z-3 (B-DATA) — ⚠ Freeze the log schema. This is the irreversible decision.

**Assumption validated:** C5.3 — that your log captures everything the conformal layer will need.

**Why it's irreversible:** per Z-1, the forecast you record now is the *only copy that will ever
exist*. Query that timestamp after it passes and you get the hindcast, not what was predicted. If you
forget a column, you cannot add it retroactively — those hours are gone.

**Do:** write out the schema, in a file, before the collector runs. Minimum required columns:

**Forecast rows** (one per site × sample point × horizon × run):

| Column | Why it's needed |
|---|---|
| `site_id` | Group by site for per-site coverage (K-8) |
| `point_id`, `lat`, `lon` | Which microclimate sample this is |
| `issued_at_utc` | **Per-call, not per-run** — see G-6 |
| `valid_at_utc` | Always UTC. Local time only at display (C-1, C-10) |
| `horizon_hours` | Residuals *must* be grouped by this |
| `wet_bulb_c` | The forecast value |
| `dry_bulb_c`, `relative_humidity_pct` | Needed for B-8's cross-check and for the derivation fallback |
| `value_source` | `api_direct` or `derived_psychrolib` — you may end up with both |
| `wind_dir_deg`, `wind_speed` | If D-6 finds them. Nullable |
| `granularity` | 60/80/100 |
| `activity_id` | Lets you re-fetch the raw response for free (G-4) |
| `credits_delta` | Instrumented usage tracking |
| `api_status`, `error_text` | Nullable. A missing value must be distinguishable from a failed call |
| `raw_response_path` | Path to the saved fixture |

**Actual rows** (one per site × point × valid hour):

| Column | Why |
|---|---|
| `site_id`, `point_id`, `valid_at_utc` | The join key |
| `wet_bulb_c_actual` | FortyGuard's later value — your primary truth |
| `fetched_at_utc` | So K-5 can detect silent revisions |
| `revision_n` | Increment if you re-fetch and the value changed |
| `metar_station`, `metar_wet_bulb_c`, `metar_obs_time_utc` | The independent measurement (W-3) |

**Derived per-run row** (one per site × run) — needed for decision 3:

| Column | Why |
|---|---|
| `max_wet_bulb_forecast_c` | The worst hour across the 12-hour window |
| `max_wet_bulb_actual_c` | Its realised counterpart |
| `volatility_signal` | Conditioning feature (NVIDIA §3.4). Nullable now, unrecoverable later |
| `microclimate_spread_c` | Max − min across sampled points. Also a conditioning feature |
| `n_points_sampled` | The agent's own sampling decision, for the audit trail |

**Pass:** the schema is written down and includes every column above.
**Fail:** you started the collector first. **Workaround:** none. That's the point.

Append-only JSONL or SQLite are both fine. Don't over-engineer it — just don't forget a column.

---

### Z-4 (B-DATA) — Credit budget arithmetic, **for the field design**

**Assumption validated:** A0.3/A0.4 — that a three-site **heatmap** collector fits in 1,000,000 credits.

> **Rewritten.** The design is now field-first, not point-first
> ([project-master-plan.md](project-master-plan.md) §3, §8.3). The unit of perception is a heatmap over
> a campus polygon, not an `env_params` point. Heatmaps may cost far more per call than points, so this
> is the **single largest risk in the project** (master plan §11.1) — do the arithmetic before A-3/S-1
> measures the real number, so the measurement is immediately interpretable.

**Do:** compute the maximum per-call cost you can afford.

```
Per site, per hour:
   1     coarse heatmap   granularity 100, filter_type 2, whole 12 h in ONE call   ← confirm via S-7
 ~0.4    fine refinement  granularity 60 over the hot-spot sub-polygon, only when
                          the field is structured enough to warrant it (§8.3)
   1     actuals backfill single past hour, filter_type 1
 -----
 2.4     calls / site / hour

 2.4 × 3 sites × 24 h            = ~173 calls / day
     × 30 days                   = ~5,200 calls

max affordable = 1,000,000 × 0.6  ÷  5,200  ≈  115 credits / call
                              ^^^ 40% reserved: A1's historical sweep (master plan §9.1)
                                  is the large consumer, not the collector
```

**If S-7 fails and a 12-hour range is *not* one call**, multiply the collector's calls by 12 and divide
the affordable ceiling by 12 → ~10 credits/call. That is a very different project; find out on day 0.

**Pass:** A-3/S-1's measured cost is at or below your ceiling. Proceed as designed.

**Fail — the degradation ladder.** Apply in this order. It is deliberately ordered so that
**σ_spatial — the conditioning variable the whole uncertainty contribution rests on — is the last thing
to go.**

| Measured cost | Action |
|---|---|
| ≤ 115 | Proceed as designed |
| 115–300 | Refine only when σ is above its 90th percentile; sample A1's history **weekly** not daily |
| 300–1,000 | Granularity 100 m only, no refinement (drops R4); A1 sampled **monthly** |
| > 1,000 | Field perception drops to **twice daily**; the hourly decision reverts to `env_params` at the hot spot, and the field supplies σ only. **R1 survives, R4 does not.** Document the degradation in the writeup |

**Do not cut sites before cutting resolution or cadence** — sites are what buy you n_eff (K-6), and
they are also what make cross-climate pooling (K-8) possible.

**Also decide now, because both appear in Z-3's frozen schema and cannot change mid-collection:**
the campus polygon for each site (store its hash), and the σ threshold at which refinement triggers.

**Log any cap you apply.** If A1's historical sweep samples weekly rather than daily, that is a stated
limitation, not a silent truncation. A reader must not be able to mistake a sampled result for an
exhaustive one.

---

## ⚑ TIER 0 — Z-5 to Z-8: free, computable on data already held, do these FIRST

> Four checks that cost **nothing** — no credits, no API key — and that between them can kill or de-risk the
> project before Aug 18. Three of the four have already been run; their results are recorded here.

### Z-5 (B-CODE) — ✅ Facility and control registers, and the density gate — **DONE 2026-08-09**
**Assumption validated:** that facilities are close enough together for interference to exist at all.
**Measured**, OSM Overpass, `telecom|building|industrial|man_made = data_center`, de-duplicated at 60 m:

```
Metro                    facilities   pairs≤500m   pairs≤800m   %with ≥1 nbr ≤800m   median nbrs   max
Ashburn / Loudoun VA        226          583         1,276             99%                11         30
Santa Clara CA               58          180           268             90%                12         19
Dallas–Fort Worth TX         55           52            66             78%                 1          7
Phoenix E-valley AZ          44           30            46             55%                 1          9
```

Closest pair **62 m** against a **500 m** plume. **GATE PASSED across four metros.**

**Remaining work:** the 62 m minimum shows OSM tags *individual buildings*, not campuses (226 objects vs.
~133 reported "data centres"). **Group the buildings into owner campuses** so **intra-campus** pairs (which
the operator already manages via fan placement and spacing) are separated from **inter-campus** pairs —
which nobody can manage, because you cannot model a neighbour whose equipment you do not know. **The
inter-campus pairs are the target.** Then build the control register with **Q-3's 1 km screen.**

### Z-6 (B-DATA) — ✅ Optimal polygon placement — **DONE 2026-08-09**
**Assumption validated:** that one call can cover enough facilities, with each far enough from the polygon
edge that a 500 m wedge is not truncated.
**Do:** grid-search polygon centres; count facilities inside, and those ≥550 m from the edge.
**Measured** over Loudoun:

```
 5×5 km   (~6,944 tiles)   centre 39.0050, −77.4580  →  137 inside, 105 usable
 8×8 km  (~17,777 tiles)   centre 39.0100, −77.4460  →  169 inside, 168 usable   ← USE THIS
11×11 km (~33,611 tiles)   centre 38.9850, −77.4700  →  188 inside, 177 usable
```

**168 facilities measurable in a single call**, at a tile count already proven to complete in 67 s (S-2).

**⚠ Lesson worth recording:** the 5 × 5 km polygon **already paid for** contains only **6 facilities, none
≥550 m inside the edge** — so no wedge could be drawn on it at all. **Polygons must be positioned around
facilities deliberately, not around a metro's nominal centre.** That error cost a call.

### Z-7 (B-CODE) — ✅ Effective resolution decay — **DONE 2026-08-09, PASSES**
**Assumption validated:** P1.10 / E-7 — that 60 m granularity carries real information rather than being
upsampled from a coarser field. **If the field were smoothed at ~500 m, a 500 m plume would be smeared to
nothing** — this was the highest unexamined technical risk in the project.
**Do:** mean absolute tile-to-tile temperature difference as a function of separation, from a saved field.
**Measured** on the 6,875-tile response:

```
separation        mean |ΔT|      ratio vs. previous     n pairs
   45–75   m       0.0108 °C           —                 2,369
   90–150  m       0.0252 °C         2.34×                6,970
  180–300  m       0.0481 °C         1.91×               29,192
  360–600  m       0.0926 °C         1.92×              108,490
  720–1200 m       0.1695 °C         1.83×              370,881
 1400–2400 m       0.3009 °C         1.78×            1,091,511
```

**PASS.** Smooth, monotonic, near-constant ratio per doubling. **No flat region and no jump near 500 m** — an
upsample from coarse data would show |ΔT| ≈ 0 below 500 m then a step. **The 60 m resolution is genuine.**

**And the derived number that makes the project feasible:**

```
background variation at the plume scale (~500 m)   ≈ 0.09 °C
the signal being hunted (Sailor et al.)            0.7–2.2 °C
                                                   ─────────────
signal-to-background                               ≈ 8–24×
```

**If the plume is present in FortyGuard's field, it should be unmistakable.**

### Z-8 (B-CLAIM) — Preliminary plume probe on saved data *(free; blocked, and why)*
**Do:** overlay the Z-5 facility register on a saved field, take that period's METAR bearing, compute wedge
differentials, and run the P-4 rotation placebo.
**Status: could not run.** The saved polygon contains only 6 facilities and **none ≥550 m from the edge**
(Z-6), and the wind over that window was **4.5 kt with steadiness 0.52** — a textbook *unusable* day by
T-3's criterion.
**What that tells you anyway, for free:** (a) polygon placement must be deliberate; (b) **T-3's
wind-steadiness filter is not bureaucratic — it would have rejected this window, correctly**; (c) re-run Z-8
as **call 1 + P-2** on Aug 18 with the Z-6 polygon and a wind-selected historical date.

---

---

# GROUP A — Access, plan, and accounting

You cannot interpret any later result without knowing which plan you're on.

### A-1 (B-CODE, P0) — Does the key authenticate?
**Assumption:** A0.1.
**Do:** any simple request — easiest is `GET /v1/system/fetch-api-key-usage`.
**Record:** HTTP status. Does `api-key` in the header work, or does it want something else
(`Authorization: Bearer`, a query parameter)?
**Pass:** 200. **Fail:** 401/403 → try the alternatives above before concluding the key is bad.
**Why it matters:** everything stops here. Also confirms whether the usage endpoint takes the key in a
header or as a parameter — the docs show a form field in the UI, hinting it might be a query param.

### A-2 (B-CODE, P0) — Which plan are you on?
**Assumption:** A0.2.
**Do:** read the usage endpoint response.
**Record:** plan name (Basic / Premium / **Startup**), `total_available_credits`,
`cycle_remaining_credits`, `credits_reset_date`, `subscription_start_date`, `billing_period`.
**Why it matters:** determines whether you're capped at 3 environmental parameters per request and
10 mi² heatmaps — which constrains D-3 and E-6.

### A-3 (B-DATA, P0) — What does one call actually cost?
**Assumption:** A0.3.
**Do:** read credits → make **one** heatmap call → wait for `Completed` → read credits again. Repeat
separately for one `env_params` call.
**Record:** exact credit delta for each endpoint type.
**Pass:** delta ≤ your Z-4 ceiling. **Fail:** above it → apply Z-4's workaround ladder.
**Why it matters:** **completely undocumented**, and the single most important number for planning. If
one call costs 1 credit you have effectively unlimited budget. If it costs 500, the three-site
collector needs redesigning before it starts.

### A-4 (NICE, P1) — Does cost scale with request size?
**Assumption:** A0.3.
**Do:** compare credit delta for (a) `filter_type=1` vs `filter_type=2` over six hours; (b) granularity
100 vs 60 on the same polygon; (c) small vs large polygon; (d) `env_params` with 1 vs 3 parameters.
**Record:** delta for each variant.
**Why it matters:** tells you whether to batch. If cost is flat per request, always ask for all 12
hours at once. If it scales per data point, batching saves nothing.

### A-5 (B-DATA, P2) — Where is the rate limit?
**Assumption:** A0.6.
**Do:** send requests in quick succession — ~10 back to back, then ~30 — watching for HTTP `429`.
**Record:** how many requests before 429, over what window. Is there a `Retry-After` header?
**Pass:** the limit is comfortably above your per-run call count from Z-4.
**Fail:** the limit is below it → the collector must serialise with sleeps, which lengthens each run and
smears the issuance time (see G-6).
**Why it matters:** your collector fires 3 sites × M points at once. Stop as soon as you see one 429 —
you've found the answer.

### A-6 (NICE) — Does the usage endpoint update promptly?
**Assumption:** A0.5.
**Do:** read usage → one call → read usage immediately → read again after 5 minutes.
**Pass:** the delta appears immediately → you can instrument per-call credit cost by differencing, and
`credits_delta` in Z-3's schema is meaningful.
**Fail:** usage lags → per-call attribution is impossible. **Workaround:** count calls yourself and
reconcile against total usage daily. **Cost:** you lose per-call cost visibility; your credit
instrumentation becomes a counter plus a daily reconciliation rather than a live figure.

### A-7 (B-DATA) — Is the credit pool monthly or one-time?
**Assumption:** A0.4.
**Do:** from A-2's `billing_period`, `credits_reset_date` and `subscription_start_date`, determine
whether 1,000,000 credits reset monthly or are a one-time allocation over a fixed window (the Startup
plan is documented as a **6-month one-time** window).
**Pass:** monthly reset → Z-4's arithmetic is generous, and a heavy month is recoverable.
**Fail:** one-time pool → **Z-4's 30% reserve is not optional.** If you burn the pool in week 1 there
is no month-boundary refill, and the project ends.
**Why it matters:** this changes the consequence of a budget mistake from "wait until next month" to
"the project is over."

---

# GROUP B — The blocking risks

**These decide whether the project works as designed.** Ordered by run sequence, not by number.

### B-1 (B-CODE, P0) — ⚠ Does `env_params` accept a FUTURE timestamp?
**Assumption:** P1.1 — that you can fetch forecast wet-bulb at a point at all.

**Do:** three requests to `/v1/env_params`, identical except the date/time, same US location:
1. **Control:** a past date (e.g. `2024-07-15`, `14:00`) — should work
2. **Now:** today's date, current hour
3. **Future:** today's date, current hour **+ 6**

**Record for each:** HTTP status, exact error text if rejected, and whether
`wet_bulb_temperature_celsius` comes back with a real number.

**Pass:** future works → your original design is intact. **Now go straight to B-5** — passing B-1 is
necessary but not sufficient.

**Fail:** future rejected → you cannot fetch forecast wet-bulb directly. **Workaround:** get forecast
dry-bulb from `/v1/heatmap` (documented to support now+12h), obtain forecast humidity, and compute
wet-bulb yourself with `psychrolib` (or the Stull 2011 closed-form, MAE < 0.3 °C — but it assumes
near-sea-level pressure and is valid 5–99% RH, −20 to +50 °C, so use station pressure from elevation
for the Phoenix sites). **Cost:** ~0.3 °C of added error, a dependency on forecast humidity being
available at all (see B-4), and a weaker claim — you're deriving a variable rather than reading it.
Your B-8 code already does this, so the implementation cost is near zero.

**Control also fails:** the request *format* is wrong, not the date. Fix the shape before concluding
anything.

### B-5 (B-CODE + B-CLAIM) — ⚠⚠ Is that future value *actually a forecast*?
**Assumption:** P1.4 — that a future value is a genuine prediction, not persistence-of-now or a
climatological average.

**Why this exists.** If B-1 passes, the API returns a number for `now+6h`. That number could be:
(a) a real forecast, (b) the current observation copied forward, or (c) a climatological average for
that hour-of-year. **All three look identical in the response.** If it's (b) or (c), your entire value
claim and every residual you ever collect are measuring the wrong thing — and nothing else in this
document would catch it.

**Do:**
1. Request `filter_type=2` from the current hour to +12h at one site. Record all 13 values.
2. Compare the future values to the current-hour value.
3. Repeat tomorrow, at the same clock time, and compare the two days' curves.

**Pass:** the values diverge from the current hour, trace a plausible diurnal shape (warming into
afternoon, cooling overnight), and **the curve differs between two days with different weather**.

**Fail — case (b), persistence:** all future values equal (or nearly equal) the current-hour value.
**Fail — case (c), climatology:** the curve is smooth and near-identical on two days whose actual
weather differed.

**Workaround if it fails:** the point-forecast path is dead. Fall back to `/v1/heatmap`, which is the
endpoint the docs actually document a 12-hour forecast for, and derive wet-bulb per B-1's fallback. Then
run this same B-5 test **on the heatmap endpoint** — do not assume the heatmap is a real forecast
either. **Cost:** if *both* endpoints fail B-5, FortyGuard cannot supply forecasts and the project must
be restated as a *hyperlocal-vs-airport spatial* system using an external forecast source. That is a
significant redesign, which is exactly why this check runs on day 1.

### B-4 (B-CODE, P0) — ⚠ What does the `temperature` input field actually DO?
**Assumption:** P1.5 — and this check may rescue the project if B-1 fails.

`env_params` requires you to *supply* a `temperature` value. Nobody has explained why.

**Do, part one:** same location, same date/time, three requests differing **only** in `temperature`:
`15.0`, `25.0`, `35.0`. Record the `wet_bulb_temperature_celsius` returned by each.

- **Wet-bulb changes with your input** → `env_params` is a **calculator**. It derives wet-bulb from the
  temperature *you* give it, plus humidity it looks up. **Very good news:** even if B-1 fails, you may
  be able to feed it a *forecast* temperature from the heatmap and get forecast wet-bulb out. Proceed to
  part two.
- **Wet-bulb identical regardless of input** → it ignores your number and uses its own data. The field
  is vestigial, and B-1's answer is final. Skip part two.

**Do, part two — the forecast-humidity test (this is the part that decides it).** If it's a calculator,
its output is only a forecast if the *humidity it looks up* is a forecast. Hold `temperature` fixed at
one value and vary only the timestamp across `now+1h … now+12h`. Record
`relative_humidity_percent` for each.

**Pass:** humidity varies hour by hour in a plausible way → there is genuine forecast humidity, and the
heatmap-temperature + env_params-humidity path works.
**Fail:** humidity is flat across all future hours, or equals the current hour's value → there is no
forecast humidity. Any wet-bulb you compute from it is **fake precision**: it will vary with
temperature but carry no information about how humid it will actually be. **Workaround:** source
forecast humidity externally (a public forecast API), or fall back to the most conservative humidity
you've observed at that site and hour — which widens your bound substantially. **Cost:** either a new
external dependency, or a much more conservative agent that recommends free cooling far less often.

### B-7 (B-CODE) — Does `env_params` work standalone?
**Assumption:** P1.6.

**Why:** the docs say the `env_params` date/time *"should match the heatmap you generated for the same
location and time."* It is unclear whether that is advice or a requirement. If `env_params` is really
stage 2 of a two-call workflow, every microclimate sample costs a heatmap **plus** an env_params —
doubling both credits and latency, and invalidating Z-4's arithmetic.

**Do:** with a fresh key and no prior heatmap for that location or time, call `env_params` cold at a
valid US point for a past hour. Then call it at a point you have *never* included in any heatmap.
**Pass:** returns real values → standalone. Z-4's arithmetic holds.
**Fail:** errors, or returns nulls, or returns something that only becomes real after a heatmap exists
→ **Workaround:** treat heatmap-then-env_params as one logical operation, halve your sample points, and
redo Z-4. **Cost:** roughly 2× credits and 2× latency per sample, which may push you to 1–2 sample
points per site.

### B-8 (B-CLAIM) — ⚠ The psychrolib triple cross-check
**Assumption:** P1.7 — units are °C, the fields refer to the same instant and place, and it is
*psychrometric* wet-bulb rather than wet-bulb **globe** temperature.

**This is the single best correctness test in the document, and it validates four things at once.**

**Do:** request `wet_bulb_temperature_celsius`, air temperature, and `relative_humidity_percent` for the
same point and hour (three parameters — exactly the Basic/Startup cap, see D-3). Then compute wet-bulb
yourself from that temperature and humidity using `psychrolib`, at the station pressure implied by the
site's elevation from Z-2.

**Pass:** your computed value agrees with the API's within ~0.3 °C. You have simultaneously proven:
units are °C; the three fields describe the same instant and place; the field is psychrometric wet-bulb
and not WBGT; and **your own derivation code is correct** — which is the code B-1's fallback depends on.
One test, four answers.

**Fail:** a large disagreement. Diagnose by pattern:
- Off by a factor that looks like °F↔°C → units.
- Your value much *lower* than theirs, especially in sun → theirs may be WBGT, or the "temperature" may
  be a surface temperature (see B-6).
- Disagreement varies with time of day → the fields may describe different instants; check C-1/C-9.
- Disagreement scales with humidity → check whether their humidity is a fraction (0–1) rather than a
  percentage.

**Workaround:** once you know which field is trustworthy, use it and derive the rest. **Cost:** if the
API's wet-bulb can't be reconciled, you compute wet-bulb yourself from temperature and humidity for
*everything*, which is fine — but say so, and inherit Stull's/psychrolib's error.

**Extra credit:** repeat when humidity is near 100%. Wet-bulb should then be very close to dry-bulb.
If it is, you're reading the data correctly.

### B-6 (B-CLAIM) — ⚠ Is it 2 m air temperature, or land-surface temperature?
**Assumption:** P1.8.

**Why:** your value proposition says "hyperlocal 2-metre site data." FortyGuard also sells satellite
and streetview products, which hints its heritage may be satellite **land-surface temperature** — the
temperature of the ground, not of the air above it. On a sunny afternoon those differ by 10–20 °C. If
you're getting LST, your threshold comparison is physically wrong and your wet-bulb derivation is
meaningless. This would *not* show up as an obvious error — it would look like a strong urban heat
island effect.

**Do:**
1. Pull a full 24 hours of air temperature at one site and compute the **diurnal amplitude**
   (max − min).
2. Compare to the METAR station's amplitude for the same day (you have this from W-1).
3. Search the response and its `metadata` for any height, level, or product field (`height`, `level`,
   `2m`, `agl`, `lst`, `surface`, `product`).

**Pass:** amplitude is air-like, roughly 8–15 °C, and within a few °C of the station's. No field
suggests a surface product.
**Fail:** amplitude is 20–30 °C+, or afternoon values run 15 °C above the station with no plausible
explanation → it's a surface product.

**Workaround:** if it is LST, you need an air-temperature variable instead. Check whether the response
offers a separate air-temperature parameter (D-3 lists what's available). If only surface temperature
exists, wet-bulb from it is not physically meaningful and the project must key on a different data
source or a documented LST→air-temperature relationship. **Cost:** potentially severe. Which is why it
runs on day 1, not week 3.

### B-3 (B-CODE, P0) — What's in `metadata`? Is there any "when was this produced" concept?
**Assumption:** C5.1 (behavioural confirmation of Z-1) and D3.4 (staleness detectability).

**Do:**
1. Query a past date/time. Record the wet-bulb value.
2. Read the **full** response, every field including `metadata`. Look for `issued_at`, `forecast_time`,
   `run_time`, `model_run`, `reference_time`, `generated_at`, or similar.
3. Query the exact same past date/time again. Identical?

**Record:** the full raw `metadata` block verbatim.

**Pass (for staleness):** an issuance timestamp exists → your fail-safe can define "stale" properly, as
"the data was produced more than N hours ago."
**Fail:** no issuance concept anywhere → "stale" can only mean "I fetched this a while ago."
**Workaround:** define staleness as fetch age, using your own clock, and log `fetched_at_utc` (already
in Z-3's schema). **Cost:** you cannot detect the case where the API serves you a fresh-looking
response built from an old model run. State that limitation.

**Pass (for the archive):** an issuance field that you can *set* → Z-1 was wrong in your favour.
**Fail:** an issuance field you can only *read* → still no archive, but useful for staleness.

### B-2 (B-CODE, P0) — What is the real forecast horizon, and where does it cut off?
**Assumption:** P1.2.
**Do:** heatmap requests at now **+1h, +6h, +11h, +12h, +13h, +24h**. Then the same ladder on
`env_params` if B-1 succeeded.
**Record:** the last offset that succeeds and the first that fails, for each endpoint, with exact error
text.
**Pass:** both endpoints reach at least +12h → your committed window is achievable.
**Fail:** `env_params` has a shorter horizon than the heatmap → your window is capped at the shorter of
the two. **Workaround:** shorten the committed window to the real horizon, and note that this *reduces*
the joint-coverage burden (K-7), so it isn't purely bad news. **Cost:** less advance notice for the
operator; restate decision 3's window.

---

# GROUP K — Conformal-prediction data feasibility

**This group did not exist before and is the reason for this audit.** The rest of the design fails
loudly; this part fails silently.

### K-1 (B-CODE) — Record the archive verdict
**Assumption:** C5.1. Carry Z-1's finding here, plus B-3's confirmation. One line: *archive exists /
does not exist*, and the evidence.

**If it does not exist (expected):** the following is now true and must be written where you'll see it
every day —

> **The forecast I record now is the only copy that will ever exist.** Querying that timestamp after it
> passes returns the hindcast, not what was predicted. There is no way to recover a missed hour.

### K-2 (B-DATA) — The frozen-forecast test
**Assumption:** C5.1/C5.2 — that a forecast and a later "actual" for the same hour are *different
numbers*, i.e. that residuals exist.

**Do:**
1. Now, query `now+6h` at one site. Record the value as **F**, along with the current time.
2. Wait until that hour has passed.
3. Query that **same timestamp** again. Record the value as **A**.

**Pass:** F ≠ A, by a plausible amount (roughly 0.3–2 °C at a 6-hour horizon). The API's answer for a
given hour changes depending on whether that hour is future or past → real forecasts and real
observations, therefore real residuals. Proceed.

**Fail:** F = A exactly. This is the dangerous case → go to K-3 immediately.

### K-3 (B-CODE) — ⚠⚠ The zero-residual guard
**Assumption:** C5.2 — the most dangerous silent failure in the entire project.

**Why:** if the API serves one consistent model field regardless of when you ask, then forecast =
later actual for every hour, every residual is **exactly zero**, your conformal interval collapses to
**zero width**, and your agent becomes 100% confident all the time — including when it is wrong. It
presents as *"my forecasts are perfect."* Nothing else in this document would catch it.

**Do:** after one full day of collecting, compute residuals for every (site, point, horizon) pair.
Then:
- Count how many are exactly 0.0.
- Compute the median absolute residual per horizon.
- Check that median residual **grows with horizon** — h=12 should be visibly worse than h=1.

**Pass:** residuals are non-zero, median magnitude is physically plausible (~0.2–1 °C at h=1, ~1–3 °C at
h=12), and they grow with horizon. Conformal prediction is buildable as designed.

**Fail:** all residuals zero, or median residual at h=12 no larger than at h=1 (which means the
"forecast" carries no horizon-dependent uncertainty and is probably not a forecast — cross-check B-5).

**Workaround:** promote METAR from cross-check to residual source. Residual = your forecast for the
site at T minus the station's measured wet-bulb at T. This is **not clean** — it blends forecast error
with the site-vs-station spatial gap — but it is real, non-zero, and derived from a physical
measurement. **Cost:** your bound then covers "forecast error plus spatial offset" rather than forecast
error alone. You must say that plainly; a bound on the wrong quantity stated confidently is worse than
a wider bound stated honestly.

**Build this as an assertion in the collector, not a manual check.** If residuals go to zero at any
point, the agent should refuse to use the conformal bound and fall back to the Phase-1 fixed safety
margin.

### K-4 (B-DATA) — How soon after hour T is the "actual" for T available?
**Assumption:** S4.4.

**Do:** at 10 minutes past the hour, query the hour that just ended. Then again at +1h, +3h, +6h,
+24h. Record whether a value comes back each time, and whether it *changes*.

**Pass:** a value is available within an hour and doesn't change afterwards → your collector's
"fetch actuals" job can run hourly, one hour behind.
**Fail, delayed:** no value until T+3h or later → the actuals job must lag by that much, and your
self-scoring is correspondingly delayed. **Fail, unstable:** the value keeps changing → see K-5.
**Workaround:** set the actuals job's lag to the observed settling time, and record `fetched_at_utc`
and `revision_n` (already in Z-3's schema). **Cost:** slower self-scoring feedback; if the lag is
24 hours, your agent can't score yesterday's calls until tomorrow, which weakens the live demo.

### K-5 (B-DATA) — Are past values silently revised days later?
**Assumption:** S4.3.

**Why:** check I-1 as originally written re-queries a past hour a *few minutes* later. That won't catch
a nightly or weekly reanalysis. If the "actual" for last Tuesday changes next Tuesday, then residuals
computed at different times are inconsistent, and your calibration set is quietly built on shifting
ground.

**Do:** pick five specific past hours. Record their values on day 1. Re-query the **same** hours on
day 2 and day 8.
**Pass:** byte-identical all three times.
**Fail:** values change → **Workaround:** define a settling period from the observed behaviour, and
only admit an hour into the calibration set once it's older than that. Keep `revision_n` so you can
quantify the churn. **Cost:** your calibration set trails real time by the settling period, shrinking
n_eff by that many days.

### K-6 (B-CODE) — Effective sample size arithmetic
**Assumption:** C5.4.

**Why:** raw row count badly overstates what you have. Consecutive hourly residuals at a fixed horizon
are strongly autocorrelated — one warm-biased day biases 24 consecutive rows the same way — so they
carry roughly one day's worth of information, not 24.

**Do:** after three days of collection, for each horizon:
1. Count raw residuals.
2. Compute the lag-1 autocorrelation of the residual series.
3. Estimate n_eff. A serviceable rule for an AR(1)-like series is `n_eff ≈ n × (1 − ρ) / (1 + ρ)`.
4. Compare against the honest floor: a one-sided 1−α bound needs at least `1/α − 1` calibration points
   (so ≥ 9 for 90%), and realistically a few hundred *effective* points for a stable quantile.

**Expected arithmetic:** 14 days × 24 runs = 336 raw residuals per horizon per site. With high
autocorrelation, n_eff lands closer to the number of **site-days** — around 14 per site, ~42 across
three sites. Workable for a one-sided **90%** bound; **not** enough for 95% or 99%.

**Pass:** n_eff ≥ ~30 for your target α. **Fail:** below that.
**Workaround, in order of preference:** (1) target 90%, not 95% — and justify it with the cost-loss
ratio rather than convention; (2) use the max-over-horizon score, which spends your samples far more
efficiently (K-7); (3) add a fourth site if Z-4's budget allows. **Cost of getting this wrong:** an
under-powered quantile estimate is *unstable*, meaning your bound might be too narrow — the dangerous
direction. **Report n_eff, not the raw count, in your writeup.** Doing that unprompted is a strong
signal.

### K-7 (B-CODE) — Is joint coverage over the 12-hour window achievable?
**Assumption:** C5.5.

**Why:** the agent commits to a mode for a *window*, so per-hour coverage isn't the guarantee it needs.
If each of 12 hourly bounds holds 90% of the time individually, the chance all 12 hold together is much
lower. A Bonferroni correction for 90% joint over 12 hours requires ~99.2% per hour, which needs
≥ ~120 *effective* residuals per horizon — out of reach per K-6.

**The chosen design (locked decision 3):** a **max-over-horizon nonconformity score**. Per run, compute
one residual: `max(actual over the window) − max(forecast over the window)`. Calibrate the quantile on
those. That gives a genuine bound on the window maximum — exactly the quantity the safety decision
needs — from one residual per run rather than twelve.

**Do:** after three days, build the calibration set both ways and compare:
1. **Per-hour + Bonferroni:** per-horizon residuals, target 1 − 0.10/12 per hour.
2. **Max-over-horizon:** one residual per run, target 90%.
Report empirical joint coverage and mean interval width for both.

**Pass:** the max-over-horizon bound achieves ~90% empirical joint coverage at a usable width, and is
narrower than the Bonferroni version.
**Fail:** it under-covers → **Workaround:** shorten the committed window (a 4-hour window needs a
Bonferroni factor of 4 rather than 12, and fewer hours to be simultaneously right about), or widen α.
**Cost:** less advance notice for the operator.

**Note:** report per-hour marginal coverage *as well*, so you can say precisely how the two differ.
Volunteering the joint-vs-marginal distinction unprompted is one of the highest-signal things you can
do in judging (learning plan, Tier 2 #7).

### K-8 (B-CLAIM) — Can you pool residuals across three climates?
**Assumption:** C5.6.

**Why:** the three-site decision exists to raise n_eff. But pooling assumes the sites are exchangeable
— that a Phoenix residual and an Oregon residual are drawn from the same distribution. They almost
certainly aren't: dry-climate wet-bulb forecasts have different error characteristics from marine ones.
Pooling non-exchangeable data breaks the per-site guarantee, which is the guarantee an operator at a
specific facility cares about.

**Do:** after a week, compare per-site residual distributions — median, spread, and the 90th percentile
of absolute residual. Then compute empirical coverage three ways: pooled, per-site, and
Mondrian/group-conditional (calibrating separately per site).

**Pass:** the three distributions are similar → pooling is defensible, and you keep the full n_eff.
**Fail:** they differ materially → **Workaround:** Mondrian conformal, calibrating per site, which
gives back per-site validity at the cost of the n_eff you gained. A middle path: pool to estimate the
*shape* of the residual distribution while allowing a per-site scale factor.
**Cost:** either a weaker per-site guarantee, or fewer effective samples. **Report per-site coverage
regardless** — an aggregate number that hides a badly-covered site is exactly the marginal-vs-conditional
failure the learning plan's Tier 2 #6 warns about.

### K-9 (B-CLAIM) — ⭐ Does spatial spread actually predict forecast error? (**hypothesis H1**)
**Assumption:** the central architectural bet
([project-master-plan.md](project-master-plan.md) §7.6, artifact **A3**).

> **Hypothesis H1.** Forecast error at a point is larger when the thermal field over the surrounding
> campus is **sharply structured** than when it is **smooth.**
>
> Physical reasoning: a smooth field means one well-mixed air mass — the easy case for any forecast. A
> structured field means gradients are being advected across the site (frontal passage, sea-breeze
> boundary, heat-island edge, drainage flow), and a small timing error in the boundary's arrival becomes
> a large temperature error at a fixed location.

If H1 holds, `stats_data.stddev` is a real-time, physical, **FortyGuard-only** difficulty signal, and it
becomes the scale of the conformal margin. That is what makes the uncertainty layer stop being
provider-agnostic. **This is the single most important experiment in the project.**

**⚠ Write the pass condition down BEFORE you look at any results.** Pre-registration is what separates a
finding from a post-hoc story.

| | |
|---|---|
| **Primary test** | Spearman rank correlation between σ_spatial at issuance and \|residual\| |
| **Statistical bar** | ρ > 0.20 with p < 0.05 |
| **Practical bar** | The top σ-tercile's 90th-percentile residual exceeds the bottom tercile's by **≥ 0.3 °C**. Statistical significance alone is not enough — the effect must be big enough to move a margin |

**Do — Stage 1, the well-powered pre-test (historical, thousands of hours, no waiting).**
n_eff ≈ 42 (K-6) cannot reliably detect a weak effect, so test the *mechanism* first where data is
abundant:
1. Over FortyGuard's history, build a **persistence forecast** for each horizon ("conditions at T equal
   conditions now"). A real predictor with real, computable residuals, available for every hour since
   2019.
2. Compute σ_spatial for the same hours from historical fields (S-3).
3. Run the primary test across thousands of hours.

**Do — Stage 2, the live test.** The same analysis on the collector's real forecast residuals, using the
max-over-horizon score (K-7).

**Pass:** both bars cleared → implement the σ-normalised score `|y−ŷ| / (σ + 0.1)` **and** the Mondrian
variant (separate quantile per σ-tercile), and report the coverage table with per-tercile columns. The
win condition is coverage at or above nominal with **narrower** width, or equal width with **more uniform
coverage across terciles** — that second one is literally partial conditional coverage, the theoretical
prize.

**Fail:** → **report the null.** The global conformal layer stands; A1, A2, F-2/F-3 and the coarse-to-fine
sampler are all unaffected. Print the observed ρ and tercile gap with confidence intervals, and state
that campus-scale spatial structure carried no usable information about point-forecast error in this
field over this window. **Do not quietly delete the experiment** — a measured negative result on a
physically motivated hypothesis is a legitimate contribution, and hiding it is the one thing that would
actually damage the project.

**Fail in Stage 1 but pass in Stage 2, or vice versa:** report both. A disagreement between thousands of
persistence residuals and 42 forecast residuals is itself informative — most likely underpowered noise in
Stage 2, and it should be described that way rather than as a discovery.

**If S-9 found a real vendor uncertainty field**, run this same test on that field as a competing feature
and report which predicts residuals better. A vendor's own estimate should be expected to win.

---

# GROUP W — Airport station cross-check

> **Read this first:** METAR is **not** the conformal layer's truth source. Your forecast is about the
> site; the station is somewhere else. This group's primary job is to establish whether the site
> "actual" you *do* score against can be trusted at all.

### W-1 (B-CLAIM) — Pull station history
**Assumption:** V6.1. Day 0, no FortyGuard credits.
**Do:** for each of Z-2's three stations, download hourly history covering your intended backtest
period, from a free archive (NOAA, or Iowa State University's Mesonet archive). You need dry-bulb
temperature and dewpoint, plus station pressure if available.
**Pass:** continuous hourly coverage with few gaps.
**Fail:** large holes → pick a different station from Z-2's candidate list.

### W-2 (B-CLAIM) — Derive wet-bulb from the station data, and validate the code
**Assumption:** V6.3.
**Do:** convert dry-bulb + dewpoint → relative humidity → wet-bulb, using `psychrolib` with the
station's actual pressure. Sanity-check: wet-bulb must always be ≤ dry-bulb, and must approach it as
humidity approaches 100%.
**Pass:** no violations, and the near-saturation behaviour is right.
**Fail:** violations → your conversion has a bug. Fix it now; **B-8 depends on this same code**, and so
does B-1's fallback and (per NVIDIA §3.2) the Earth-2 path. Write it once, correctly, on day 0.
**Note the Stull caveat:** if you use the Stull 2011 closed form instead of psychrolib, it assumes
near-sea-level pressure. The Phoenix-area sites sit around 300–400 m, so use psychrolib with real
pressure there rather than Stull.

### W-3 (B-CODE) — ⚠ Truth-source trust check
**Assumption:** C5.9 — that FortyGuard's site "actual," which is a hindcast rather than a measurement,
is trustworthy enough to score your forecasts against.

**Do:** for each site, take a month of FortyGuard historical wet-bulb and the same month of
station-derived wet-bulb from W-2. Then:
1. Plot both series. Do they move together?
2. Compute the mean difference (bias) and its spread.
3. Check the bias's **daily pattern** — an urban site should read warmest relative to a rural station
   overnight, when the heat island is strongest.
4. Check its **seasonal** direction if you have the range.

**Pass:** the two track each other closely in shape; the mean difference is a few °C with a sign and
diurnal pattern that urban-heat-island physics explains (site warmer, most at night). This is the
expected and *desirable* result — that difference is your project's entire premise.

**Fail — case A, no relationship:** the series don't move together. FortyGuard isn't tracking reality
at this location, and it cannot serve as a truth source. **Workaround:** try another site; if it
persists, the data product is unusable for this project.
**Fail — case B, implausible magnitude:** a 12–20 °C offset that distance can't explain → cross-check
B-6, because this is what a land-surface-temperature product looks like.
**Fail — case C, suspiciously perfect agreement:** see W-5.

**Cost of skipping this:** you'd calibrate a beautiful conformal bound against a number that has no
connection to physical reality, and never know.

**Whatever the result, write this sentence in your writeup:** *"Coverage is measured against
FortyGuard's own later estimate for the site, which is a model hindcast rather than an in-situ
measurement; I validated that estimate against the nearest airport station's physical observations
(W-3) and found [result]."* Stating that limitation yourself is worth more than hoping nobody asks.

### W-4 (B-CLAIM) — The site-vs-station gap, which is also your headline number
**Assumption:** V6.1.
**Do:** from W-3's data, count for each site: how many hours per year is the *station's* wet-bulb below
your free-cooling threshold, versus the *site's*?
**Record:** both counts, and their difference.
**Why it matters:** this is the number that wins it (NVIDIA §6). Note the sign carefully — an urban
site is typically *warmer* than a rural airport, so hyperlocal data may reveal **fewer** safe hours,
not more. **That is still a valuable result**, and arguably a more honest one: it means the current
airport-based approach is *unsafe* at this site, and your system catches a risk that existing practice
misses. Do not assume the difference goes the direction that flatters you; report which way it goes.

### W-5 (B-CLAIM) — Is FortyGuard just interpolating the station?
**Assumption:** V6.2.
**Do:** compare a site very close to its station against one far from any station. Look at whether the
far site's values are implausibly smooth, or track the station's minute-to-minute wiggles too
faithfully.
**Pass:** the site shows structure the station doesn't — that's genuine downscaling.
**Fail:** the site's series looks like the station's with a constant offset → the "hyperlocal" value may
be substantially interpolated station data, which sharply weakens the "closing the gap" claim.
**Workaround:** none technically; report it honestly. **Cost:** your central claim becomes "I add a
calibrated spatial offset to station data" rather than "I use independent hyperlocal measurement."
Weaker, but still a real system — and being the person who found this themselves is worth more than
being caught by a judge.

### W-6 (B-CLAIM) — ⚑ Leave-one-station-out: prove the hyperlocal claim against **real instruments**
**Assumption:** V6.1, V6.2, and the whole value claim
([project-master-plan.md](project-master-plan.md) §9.2 — artifact **A2**).

**Why this exists.** Every other accuracy statement in the project scores FortyGuard against
FortyGuard's own hindcast — the system grading its own homework (S4.2). This is the **only** check that
scores it against physical thermometers, and it is the only one that escapes that problem entirely.
**Part of it is runnable on day 0, before you have a key**, which makes it the cheapest high-value work
available.

**Stations** (confirm history coverage via W-1):

| Metro | Candidates |
|---|---|
| Ashburn VA | KIAD, KJYO, KHEF, KDCA |
| Phoenix AZ | KPHX, KGYR, KDVT, KSDL |
| Hillsboro OR | KHIO, KPDX, KTTD |

**Do — part A (day 0, zero credits).** For each held-out station X, over a multi-year window, build the
three baselines that need no FortyGuard at all and score them against X's own measurement:
1. **Nearest-station copy** — the value at the nearest *remaining* station. This is literally what
   current practice does.
2. **IDW** — inverse-distance weighting (power 2) over all remaining stations.
3. **IDW + elevation lapse adjustment** — the strongest cheap baseline.

This establishes **the bar FortyGuard must clear**, before a single credit is spent.

**Do — part B (day 1+).** Query FortyGuard's wet-bulb at X's exact coordinates for the same hours and
score it the same way.

**Record**, for all four methods: MAE, bias, and the **95th percentile of absolute error** (the tail is
what matters for a safety decision). **Stratify by** hour-of-day (heat island peaks overnight), season,
and wind speed (heat-island signal is strongest on calm nights). An aggregate number will hide the
effect.

**Pass (pre-registered):** FortyGuard beats nearest-station-copy by **≥ 0.5 °C MAE**. Beating IDW is the
stronger claim and the headline if achieved.

**Fail:** FortyGuard does not beat the interpolation baselines → **this is a significant finding, and it
must be reported.** It would mean FortyGuard's value at airport-like locations is comparable to
interpolation, and the "closing the gap" claim must be restated as being about *built* environments
specifically, supported by W-5 rather than by W-6. **Workaround:** none — report it.

**⚠ The caveat that must be written down, because it is the honest reading.** Airport stations sit in
open grass fields **by design**. So W-6 measures FortyGuard's skill at *airport-like* locations, not at
urban campuses. If FortyGuard's advantage comes from resolving built environments, this test
**understates** it — the hardest tiles for the interpolation baselines contain no stations to score
against. **W-6 is therefore a lower bound on the hyperlocal advantage.** Saying this before a judge asks
is worth more than the number itself.

**This also settles W-5 / V6.2 quantitatively:** if FortyGuard were substantially interpolating these
same stations, it would *tie* the interpolation, not beat it.

---

# GROUP C — Time semantics

Silent time bugs are the most common way a forecasting project produces confident nonsense. You now
have **three timezones**, and one of them doesn't observe DST — so C-10 is not theoretical.

### C-1 (B-DATA, P1) — What timezone are inputs interpreted in?
**Assumption:** O7.6.
**Do:** request a specific hour and compare against the returned `timestamps`. Note that result
`metadata` contains `timezone` and `timezone_offset_hours`.
**Record:** did asking for `14:00` return 14:00 local, 14:00 UTC, or something else? What do those two
metadata fields say? **Do this at all three sites** — the answer may be per-site.
**Pass:** the behaviour is consistent and documented by the metadata.
**Fail:** ambiguous → **Workaround:** send UTC explicitly if the API accepts it; otherwise send local
and verify the echoed timestamp on every call, treating a mismatch as an error.
**Why it matters:** if you request "now + 6h" local but the API reads UTC, you silently forecast the
wrong time of day — potentially the coolest hour instead of the hottest.

### C-2 (B-CODE, P1) — What is the time STEP?
**Assumption:** P1.3.
**Do:** `env_params` with `filter_type=2`, `start_time` = current hour, `end_time` = +6 hours.
**Record:** how many values in each parameter array; `metadata.time_range.interval`;
`metadata.time_range.count`; the actual `timestamps` list.
**Pass:** ~7 values → hourly, as the design assumes.
**Fail:** 25 values → 15-minute steps; 2 values → 3-hourly. **Workaround:** if sub-hourly, aggregate to
hourly and note whether you take the max (safer) or the mean (see C-9). If coarser than hourly,
interpolate and state that you did. **Cost:** coarser than hourly weakens the "hour by hour" claim.
**Why it matters:** the docs never specify this — `interval` appears only as an unfilled placeholder
`"TIME_INTERVAL_STRING"`. Also determines whether a 12-hour window is one call, which Z-4's arithmetic
depends on.

### C-3 (NICE, P1) — Does `filter_type=1` return one value or an array?
**Do:** single-hour request; inspect the shape of `parameters.wet_bulb_temperature_celsius`.
**Record:** bare number, or one-element array?
**Why it matters:** the documented schema shows arrays (`["NUMBER_OR_NULL"]`) even for single values.
Affects how you parse everything.

### C-4 (NICE, P1) — What does `filter_type=3` (Single Day) return?
**Do:** single-day request for a past date.
**Record:** how many values? Do they span 00:00–23:00 local?
**Why it matters:** may be the cheapest way to bulk-pull historical data for W-3's comparison — one call
instead of 24. Check the credit delta against A-4.

### C-5 (NICE, P2) — What happens with a non-round time?
**Do:** request `14:37`.
**Record:** rejected? Rounded down? Rounded to nearest?
**Why it matters:** your collector fires at arbitrary wall-clock moments. Determines whether to round
before sending.

### C-6 (NICE, P2) — Can a range cross midnight?
**Do:** `filter_type=2`, `start_time` `22:00`, `end_time` `04:00`.
**Record:** accepted? Rolls into the next day, or errors?
**Why it matters:** your 12-hour window crosses midnight most evenings. If ranges can't, you must split
into two calls and stitch — which doubles the per-run call count and changes Z-4's arithmetic.

### C-7 (NICE, P2) — Does the 23-hour cap behave as documented?
**Do:** `filter_type=2` with a 23-hour range, then a 25-hour range.
**Record:** where it breaks, and the exact error text.

### C-8 (NICE, P2) — Can one range span past *and* future?
**Do:** `filter_type=2`, `start_time` = now − 3h, `end_time` = now + 6h.
**Record:** accepted? Do you get historical and forecast values in one response?
**Why it matters:** if yes, one call gets you context plus forecast — simpler and cheaper. **Also a
sneaky B-5 check:** if the past and future halves join smoothly with no discontinuity at "now," that's
consistent with a single model field rather than a genuine forecast/observation distinction. Compare
against K-2.

### C-9 (B-CLAIM) — Are hourly values instantaneous, or hourly means?
**Assumption:** D3.5.
**Why:** an hourly *mean* of 17.8 °C can hide a 20-minute spike at 19.5 °C. If your threshold is 19 °C,
a mean-based decision would call that hour safe when it wasn't. Thermal safety cares about the peak.
**Do:** check `metadata` for any interval or aggregation semantics. Then compare one site's hourly
series against sub-hourly station observations for the same hours (many stations report every 20
minutes) — does the API value track the hourly mean, or the value on the hour?
**Pass:** instantaneous, or explicitly a maximum → use as-is.
**Fail:** hourly mean → **Workaround:** add an explicit safety margin for sub-hourly variability,
estimated from the station's within-hour spread, and document it as a separate term in your threshold.
**Cost:** a slightly more conservative agent, plus one more assumption to defend. Cheap to fix, ugly to
discover late.

### C-10 (B-DATA) — DST and nonexistent local hours
**Assumption:** O7.6. **Now a real risk:** Virginia is Eastern (observes DST), Oregon is Pacific
(observes DST), **Arizona does not observe DST at all.**
**Do:** request a local time that doesn't exist (2:30 AM on a US spring-forward date) and a local time
that occurs twice (1:30 AM on a fall-back date), in a DST-observing zone.
**Record:** rejected, silently shifted, or ambiguous?
**Pass:** the API takes UTC, or errors clearly.
**Fail:** silent shifting → **Workaround, and do this regardless of the result: store every timestamp
in UTC internally and convert only for display.** A "local to UTC" helper that assumes DST will be
silently one hour wrong for Phoenix for half the year — and a one-hour error in a residual join
produces a confident, wrong system. **Cost:** none. Just discipline.

### C-11 (NICE) — Clock skew
**Do:** compare your machine's UTC clock against any timestamp the API echoes as "current."
**Record:** the offset.
**Why it matters:** if your clock runs 10 minutes fast, your "now+12h" requests may fall just past the
horizon boundary and fail intermittently — which looks like a flaky API rather than a clock problem.
Sync your clock and note the offset.

---

# GROUP D — Wet-bulb data quality

### D-1 (B-DATA, P1) — Are the values real, and are they ever null?
**Assumption:** P1.9.
**Do:** pull wet-bulb across a full past day, and across a forecast window if available.
**Record:** any `null` values? Where do they cluster — future hours, night hours, specific parameters,
specific sites?
**Pass:** nulls are rare and predictable.
**Fail:** nulls scattered unpredictably → **Workaround:** treat a null as missing data, which by your
fail-safe rule means "recommend chillers." Log it distinctly from an API error (`api_status` and
`error_text` in Z-3's schema exist for this). **Cost:** more chiller hours. Never let a null become a
zero — a wet-bulb of 0.0 °C would look like ideal free-cooling conditions.

### D-2 (B-CLAIM, P1) — Physics sanity: wet-bulb ≤ dry-bulb
**Superseded by B-8**, which is strictly stronger — but keep this as the cheap continuous assertion in
your collector. Wet-bulb can never exceed dry-bulb; that's physics, not convention. Assert it on every
row you write, and log any violation loudly.

### D-3 (B-CODE, P1) — Which parameters can you request together?
**Assumption:** A0.2, and it constrains B-8.
**Do:** on Basic/Startup, request exactly 3 parameters, then try 4. Confirm the `analysis` array
parameter names.
**Record:** exact rejection behaviour at 4. Confirm the full list of available parameter names — you
need to know whether a separate **air temperature** parameter exists (critical for B-6) and whether
**wind direction** exists (D-6).
**Why it matters:** with a 3-parameter cap, B-8's triple (wet-bulb + air temperature + humidity) uses
your entire budget for that call. Also confirm: does omitting `analysis` return *all* parameters, and
does that cost more credits?

### D-4 (NICE, P2) — What's in the response besides parameters?
**Assumption:** D3.6.
**Do:** inspect `locations[]` fully.
**Record:** confirm `lat`, `lon`, `elevation`, `temperature`. Is `elevation` real, or 0/null?
**Why it matters:** elevation gives you air pressure, which you need for accurate wet-bulb derivation.
Compare against Z-2's independently-sourced elevations. If it's null, use Z-2's values from a public
elevation source. This matters most for the Phoenix sites.

### D-5 (B-CLAIM, P2) — Are values plausible for the location and season?
**Do:** compare a handful of values against the station data from W-1.
**Record:** rough agreement, or systematically offset?
**Why it matters:** catches unit errors and timezone errors at a glance. Largely subsumed by W-3, which
does this properly — treat D-5 as the quick smoke test and W-3 as the real one.

### D-6 (B-CODE) — Is wind direction available?
**Assumption:** M2.3.
**Why:** your design says the agent samples "upwind / over-site / downwind" points. Without wind data,
labelling a point "upwind" would be inventing a capability — which violates your own no-fabrication
rule, and is exactly the kind of thing a judge will probe.
**Do:** from D-3's parameter list, check for wind direction and speed. If present, request them.
**Pass:** wind direction available → the upwind/downwind sampling geometry is real. Log it
(`wind_dir_deg` in Z-3's schema) and rotate your sample points with the wind.
**Fail:** not available → **Workaround:** replace the wind-relative geometry with a **fixed compass
rosette** (e.g. centre point plus four points at 200 m N/E/S/W) and **rename it in the code, the logs,
and your narration.** Say "I sample a fixed spatial pattern around the site" — never "upwind."
**Cost:** you lose a small amount of physical motivation for the sampling pattern, and gain the ability
to describe your system accurately. Worth it.

---

# GROUP E — Spatial sampling and microclimate

### E-1 (B-CODE, P1) — What does `map_data` actually contain?
**Do:** run a heatmap on a small polygon; inspect `map_data` closely.
**Record:** is it a GeoJSON FeatureCollection? How many features? What `properties` does each feature
carry — a value? Coordinates per tile?
**Why it matters:** determines whether the heatmap **is** your microclimate sampler. If each tile
carries a value and a location, one call gives you dozens of sample points and you don't need a
hand-rolled grid — which would dramatically improve Z-4's arithmetic.

### E-2 (NICE, P1) — Does granularity want `100` or `"100m"`?
**Do:** try both.
**Record:** which is accepted.
**Why it matters:** the docs contradict themselves — the constraints page says `60m`/`80m`/`100m`, the
code example passes the number `100`.

### E-3 (NICE, P1) — How many tiles for a realistic site?
**Do:** the same campus-scale polygon at granularity 100, 80, and 60.
**Record:** tile count each time, plus response size and job duration.
**Why it matters:** tells you the real spatial resolution you're reasoning over, and whether finer
granularity is worth the cost and latency.

### E-4 (B-CODE, P1) — Confirm the `stats_data` structure
**Do:** inspect field by field.
**Record:** exact key names for min / max / mean / standard deviation. Documented as `Temperature_stats`
with `Minimum`, `Maximum`, `Mean`, `Standard_deviation`, plus `Overall_temperature_distribution`,
`Normal_temperature_distribution`, `Temperature_frequency`. Confirm the capitalisation — it's unusual.
**Why it matters:** `Maximum` is your conservative worst-case value and `Standard_deviation` is a
ready-made microclimate-heterogeneity measure — that's `microclimate_spread_c` in Z-3's schema. Both
drop straight into the design. **But check whether these describe temperature or wet-bulb** (see E-8).

### E-5 (NICE, P2) — How small can a polygon be?
**Do:** try a very small polygon — roughly one building.
**Record:** accepted? How many tiles? Any minimum-size error?

### E-6 (NICE, P2) — What happens over the area limit?
**Do:** a polygon clearly larger than 10 mi².
**Record:** exact error and status code.

### E-7 (B-CLAIM) — What is the *effective* spatial resolution?
**Assumption:** P1.10.
**Why:** if a point query snaps to a grid cell, two nearby points may return identical values not
because the microclimate is uniform but because they land in the same cell. Without this check you'd
misread that as "there is no microclimate variation here" and wrongly conclude your project's premise
is wrong.
**Do:** query `env_params` at points **20 m, 70 m, 150 m, 500 m, and 2 km** apart, same timestamp, same
granularity. Record where values *start* to differ.
**Pass:** values begin differing at a separation near your requested granularity (60–100 m) → true
resolution matches the claim, and your sample points should be spaced at least that far apart.
**Fail:** values are identical until ~2 km → the effective resolution is far coarser than advertised.
**Workaround:** space sample points at the *observed* decorrelation distance, not the advertised one,
and restate your resolution claim to match what you measured. **Cost:** a weaker hyperlocal claim — but
a measured number you can defend beats a marketing number you can't. Also re-run E-7 at each of the
three sites; resolution may vary with data availability.

### E-8 (B-CODE) — Can a heatmap map **wet-bulb**, or only dry-bulb?
**Assumption:** M2.2.
**Why:** if heatmap tiles carry only temperature, then spatial *wet-bulb* costs one `env_params` call
per point, and Z-4's arithmetic stands. If a heatmap can map wet-bulb directly, you get a whole spatial
wet-bulb field — plus `Maximum` and `Standard_deviation` from E-4 — in **one call**. That would be a
major simplification and a large credit saving.
**Do:** look for a parameter on `/v1/heatmap` that selects the mapped variable (see F-1). Try
`wet_bulb_temperature_celsius`.
**Pass:** it works → make this the primary microclimate sampler. `Maximum` becomes your conservative
per-site value directly, and `Standard_deviation` your heterogeneity measure. Redo Z-4 — you can afford
many more sites or a finer window.
**Fail:** temperature only → **Workaround:** per-point `env_params` calls as planned, or a heatmap of
dry-bulb plus a heatmap of humidity and a per-tile psychrolib derivation (your W-2 code). **Cost:** the
per-point path is what Z-4 already assumes, so no surprise — but confirm it explicitly rather than
inferring it.

---

# GROUP F — Heatmap modes

> **⚑ This group was re-prioritised.** It used to be P2/P3 "nice to know." It is now **B-CODE**, because
> two of these modes are the project's decision primitives rather than optional extras
> ([project-master-plan.md](project-master-plan.md) §3.1, §9.1). `exceedance` with `direction: below`
> *is* "how many of the next N hours are safe, per tile." `persistence` *is* the commitment window.
> Both are near-exact matches for the question the agent exists to answer, computed server-side. Run
> them on day 1.

The docs hint at multiple heatmap types beyond a temperature snapshot: **tcm** (snapshot, °C per tile),
**time_of_measure** (hour 0–23 UTC of peak), **exceedance** (hours above/below a threshold), and
**persistence**. There are also optional `threshold` (default 30 °C) and `direction`
(`above` / `below`) parameters.

### F-1 (B-CODE, P0) — What is the mode parameter, and what's the default?
**Do:** find the field that selects the mode on the Create Heatmap docs page. Run a default request and
see which mode you get.
**Record:** parameter name, accepted values, default.
**Why it matters:** E-8 depends on knowing whether a variable-selection parameter exists here, and F-2/
F-3 cannot be run without the mode parameter's name.

### F-2 (B-CODE) — Does `exceedance` work on a forecast window?
**Assumption:** the server-side decision path exists.
**Do:** an exceedance heatmap with `threshold` set and `direction: "below"`, over a **future** range
(now → now+12 h). Then the same over a **historical** range.
**Record:** does it return the number of hours below the threshold, per tile? Which variable does it
threshold on — dry-bulb or wet-bulb (cross-check **E-8**)? Does the historical form accept a multi-month
range, or must you loop?
**Why it matters:** this is the decision, computed by the API. The historical form is also how
**A1 — the annual free-cooling-hours map** (master plan §9.1) is built, and A1 is a headline artifact
that needs no collection window.
**Pass:** both forms work → use them.
**Fail on the future range:** → **Workaround:** compute exceedance client-side by counting tiles from
`tcm` fields. Same output, more calls, and Z-4's arithmetic must be redone. **A1 is unaffected** — it is
historical.
**Fail on wet-bulb (thresholds dry-bulb only):** → threshold on the dry-bulb equivalent and state the
substitution, or count client-side from a derived wet-bulb field. Do not quietly report a dry-bulb count
as a wet-bulb count.
**⚠ Do not build on this before B-5.** A server-side count derived from a fake forecast is a fake count.

### F-3 (B-CODE) — What does `persistence` mean here?
**Assumption:** the commitment-window primitive exists.
**Do:** read the docs page; run one over a future range with a threshold set.
**Record:** the exact definition. Consecutive hours below threshold? Longest run? Total run count? Where
does the run start counting?
**Why it matters:** "longest consecutive run below threshold" is *precisely* what the agent must
recommend, because it commits to a mode for a window rather than an instant (master plan §2.4). If the
semantics match, this replaces client-side run-length logic and is a strong talking point.
**Pass:** semantics are consecutive-run-below-threshold → wire it into the recommendation as the
"longest safe prefix" (master plan §12.4).
**Fail:** semantics are something else, or unavailable → **Workaround:** compute run lengths client-side
from the `tcm` field. **Cost:** a few lines of Python; no loss of capability, only of the "computed
server-side" talking point.

---

# GROUP S — The spatial field (the primary perception path)

> **New group, and the most important one after Z and B.** The design is now field-first: the unit of
> perception is a heatmap over a campus polygon, and the field's *spatial spread* is the conditioning
> variable for the conformal margin ([project-master-plan.md](project-master-plan.md) §7.6). That makes
> these checks dependencies, not curiosities. If Group S fails badly, the project's contribution changes
> shape — so run it on day 1, immediately after Group B.

### S-1 (B-DATA) — ⚠ What does a heatmap actually cost, per configuration?
**Assumption:** A0.3, and Z-4's entire ladder.
**Do:** read credits → one heatmap → poll to `Completed` → read credits again. Repeat, varying **one**
thing at a time:

| Vary | Values |
|---|---|
| `granularity` | 100, 80, 60 |
| `filter_type` | 1 (single hour), 2 (12-hour range), 3 (single day) |
| Polygon area | ~0.1 mi², ~0.5 mi², ~2 mi² |
| Mode | `tcm`, `exceedance`, `persistence`, `time_of_measure` |

**Record:** a cost table. Note which dimension dominates — area, tile count, hours, or mode.
**Pass:** cost/call ≤ Z-4's ceiling (~115 credits) → proceed as designed.
**Fail:** apply **Z-4's degradation ladder**, which is ordered so σ_spatial survives longest.
**Why this is first in the group:** every other spatial decision is an economic one, and you cannot make
economic decisions without prices. Rejected requests aren't charged and failures don't consume credits,
so this is cheap to measure.

### S-2 (B-CODE) — What does a campus-scale field actually look like?
**Assumption:** M2.5, and the payload-size bottleneck (master plan §11.9).
**Do:** run `tcm` over each site's real campus polygon at granularity 100 and 60.
**Record:** number of tiles; response size in KB; wall-clock time; whether tile geometry is returned as
centroids, corners, or a raster; the actual min/max/mean/stddev of the field.
**Pass:** tile count is manageable (order hundreds, not tens of thousands) and the payload parses.
**Fail — too many tiles:** → **Workaround:** store `stats_data` + the hot-spot tile + a downsampled
field in the hot log, and archive full `map_data` separately keyed by `activity_id` (G-4 makes re-reads
cheap). **Cost:** an extra storage tier.

### S-3 (B-CODE) — ⚠ Confirm `stats_data` gives you a spatial standard deviation
**Assumption:** the conditioning variable of master plan §7.6 exists.
**Do:** inspect `stats_data` on the S-2 responses. Confirm a **standard deviation across tiles** is
present, and confirm by hand that it matches the stddev you compute yourself from `map_data`.
**Record:** exact field names; whether stddev is across tiles (spatial) or across hours (temporal); the
units.
**Pass:** a spatial stddev is present and matches your own computation → **this is σ_spatial, and R1 is
buildable.**
**Fail — it's a temporal stddev:** → that is a *different* signal (also interesting, but not spatial).
Compute σ_spatial yourself from `map_data`. **Cost:** you must parse the full field every hour instead of
reading a small summary, which raises S-2's payload cost and removes the cheap-coarse-read saving in the
sampler (master plan §8.3).
**Fail — no stddev at all:** → same workaround. R1 still works; it just costs more bandwidth.
**Cost of skipping:** you'd build the entire uncertainty contribution on a field you never verified
exists.

### S-4 (B-CODE) — Does `exceedance` accept a future range with `direction: below`?
Carried out as part of **F-2**. Recorded here because Z-4's arithmetic and A1's method both depend on it.

### S-5 (B-CODE) — `persistence` semantics
Carried out as part of **F-3**.

### S-6 (B-CODE) — Does any mode carry **wet-bulb**?
Carried out as part of **E-8**. Recorded here because it is the single biggest fork in the spatial design:
native spatial wet-bulb, versus a dry-bulb field + humidity field + per-tile `psychrolib` derivation, with
σ_spatial computed on dry-bulb as a **documented proxy** (master plan §11.3).

### S-7 (B-DATA) — ⚠ Does `filter_type=2` cover the whole 12-hour window in ONE call?
**Assumption:** the largest single credit lever in the project (~12×).
**Do:** one heatmap with `filter_type=2`, `start_time` = now, `end_time` = now + 12 h. Count the hours
returned. Then read the credit delta and compare against twelve `filter_type=1` calls covering the same
hours.
**Record:** hours returned; credit delta for the range call vs. 12 single calls; whether the 23-hour cap
is inclusive; what happens at exactly 12 and exactly 23 hours.
**Pass:** twelve hours in one call, at a cost well below twelve single calls → Z-4's arithmetic stands.
**Fail:** → multiply the collector's call count by 12 and divide Z-4's ceiling by 12 (~10 credits/call).
**Workaround:** drop the perception cadence to every 2–3 hours and note the reduced n_eff, or shorten the
committed window from 12 h — but shortening the window weakens the design's central operational claim, so
prefer cutting cadence first.

### S-8 (B-CODE) — Is the tile grid **stable** across calls, and does refinement nest?
**Assumption:** master plan §8.3 (coarse-to-fine) and §12.2 (grid stability).
**Do:** three tests.
1. Submit the **identical** request twice. Compare tile centroids.
2. Submit the same polygon at granularity 100 and at 60. Do the 60 m tiles nest inside the 100 m ones, or
   is the grid re-anchored per request?
3. Submit a **sub-polygon** of the campus at granularity 60. Do its tile centroids coincide with the
   corresponding tiles from the full-campus 60 m request?

**Record:** centroid coordinates for each; any offset.
**Pass:** grids are anchored to a global lattice and are reproducible → per-tile time series are valid,
A1 works, and refinement merges cleanly.
**Fail — grid re-anchors per request:** → **this is serious.** The same physical location falls in
different tiles across hours, which corrupts any per-tile time series **including A1**. **Workaround:**
define your own fixed lattice and aggregate returned tiles into it (area-weighted), accepting a coarser
effective resolution. **Cost:** A1 becomes coarser; the "60 m" claim must be restated as "aggregated to a
fixed N-metre lattice."
**Fail — refinement doesn't nest:** → **Workaround:** don't merge. Use the fine field for the decision
value and the coarse field for σ, and log both separately.

### S-9 (B-CLAIM) — Does `heat_intelligence` expose a spatial-uncertainty or confidence field?
**Assumption:** that §7.6's σ_spatial proxy is the best available uncertainty signal.
**Do:** check whether `heat_intelligence` (listed as premium) is available on your plan tier (A-2). If it
is, read its response schema and look for anything resembling confidence, spread, ensemble range, or a
per-tile uncertainty.
**Record:** availability on your tier; any uncertainty-like field.
**Pass (nothing there):** σ_spatial from `stats_data` remains the best signal. Proceed with §7.6 and say
in the writeup that you checked.
**Pass (something there):** **it is better than your proxy and should replace or augment it.** A vendor's
own uncertainty estimate beats a heterogeneity proxy. Fold it into the conditioning scheme as a second
feature and report which predicts residuals better (the same experiment as K-9).
**Why run it:** checking is nearly free, and *not* checking whether the sponsor already sells the thing
you spent a week approximating would be indefensible under questioning.

---

# GROUPS P · Q · R · T · U · V — the Downwind measurement protocol

> **These six groups were added when the project became *Downwind* — measuring thermal interference
> between neighbouring data centres ([project-master-plan-v2.md](project-master-plan-v2.md)).** Groups Z–S
> above verify the **API**. These verify the **measurement**.
>
> They were designed by walking the inference chain and asking, at each link, *"what could be true about the
> data that would make our conclusion wrong?"*
>
> ```
> numbers → is it AIR? → does it resolve at 60 m? → does it respond to weather?
>         → wedge averaging → is the difference EXHAUST or LAND COVER?
>         → are the CONTROLS valid? → is the statistic sound? → does the MONEY follow?
> ```
>
> Eight places to break. Six groups to catch them. **No existing check ID was renamed or removed.**

---

## GROUP P — Is the signal present at all?

### P-2 (B-CODE) — ⚑⚑ The wind-following test — **the single most important check in this document**
**Assumption validated:** that FortyGuard's field responds to *air movement*, not merely to what a building
looks like. This is the **World A vs. World B** discriminator.

**Do:** pick one facility. Choose two **historical** days whose METAR bearings differ by **≥120°**, matched
for hour-of-day and regional temperature (within ~2 °C). Request the same polygon for both. Compute the
upwind/downwind wedge differential on each.

**Pass:** the warm lobe **flips to the other side** when the wind flips. → **World A. The field carries
advected heat and the project is alive.**

**Fail:** the warm patch stays in the same place. → **World B.** The warmth is a static land-cover artifact.

**Why this outranks the answer-key check (P-1):** if a facility happens to have a car park on its east side
and a golf course on its west, you would measure a "plume" that is really land cover — **and it could match
the published numbers by pure coincidence.** Land cover does not move when the wind moves. **P-1 cannot
detect that confound; P-2 can.**

**Workaround if it fails:** report the null — it supports the Masley critique and satisfies his requirement
(iii). The operational half survives on the *static* cluster signature used as a spatial correction to the
regional forecast. **Cost:** the interference matrix cannot be built; A1/A2/A3 become a single-facility
static footprint product.

### P-1 (B-CODE) — The answer-key test against Sailor et al.
**Assumption validated:** that FortyGuard reproduces a peer-reviewed field measurement.
**Do:** polygons over **Mesa (36 MW)** and **Chandler (169 MW campus)** — the facilities Sailor et al. named
— for historical hours inside their 18 Jun – 25 Oct 2025 campaign window with known METAR bearings.
**Record:** differential magnitude and the distance at which it decays to the noise floor.
**Pass:** 0.5–1.2 °C mean with extent 300–700 m — consistent with published 0.7–0.9 °C mean, 2.2 °C peak,
~500 m.
**Fail:** |differential| < 0.2 °C → consistent with World B; confirm against P-2.
**Why it matters:** this is the only check in the entire project with a **peer-reviewed answer key.** It is
the credibility anchor of the writeup.

### P-3 (B-CLAIM) — Calm-day negative control
**Assumption validated:** that a detected lobe requires wind.
**Do:** same facility, a historical day with mean wind **< 2 kt** and variable direction.
**Pass:** no coherent directional lobe.
**Fail:** a lobe appears anyway → it is land cover, not a plume. Cross-check P-2.

### P-4 (B-CLAIM) — Rotation placebo *(free — no API call)*
**Do:** on a real day's field, recompute the differential using **200 randomly assigned bearings**.
**Pass:** the true bearing's differential sits in the **top ~10 %** of the placebo distribution.
**Fail:** the true bearing is unremarkable → there is no *directional* signal, only spatial variation.
**Why it matters:** this is what separates "the field is lumpy" from "the field is lumpy in the direction the
wind is blowing." Cheap, and it belongs in every result you publish.

---

## GROUP Q — Is the control group actually a control?

> **The sharpest attack surface in the whole method. Expect a judge here.**

### Q-1 (B-CODE) — The control-site null distribution
**Assumption validated:** that "ordinary spatial variation" can be quantified.
**Do:** ≥50 warehouses / big-box / distribution depots in the **same polygon and the same days**. Identical
wedge geometry. Record the full distribution of differentials.
**Pass:** a tight distribution (e.g. ±0.3 °C) well separated from facility values.
**Fail:** as wide as the facilities → no discriminating power.
**Note:** this distribution **is** the conformal calibration set (§8.1 of the master plan). It is not a
side-check; it is the statistic.
**Cost:** zero extra credits — **flat pricing means the controls are inside the same call as the
facilities.**

### Q-2 (B-CLAIM) — ⚠ The instrument-blindness test
**Assumption validated:** that FortyGuard can distinguish a data centre from a warehouse at all.
**Why this exists:** **if the model infers temperature from land cover, a warehouse and a data centre look
identical to it.** Controls would then show the *same* apparent plume, and we would get a null **by
construction** — not because there is no effect, but because the instrument cannot tell them apart.
**Do:** compare the Q-1 control distribution against the facility distribution, **and read it together with
P-2.**
**Pass:** controls tight, facilities wide, and P-2 shows wind-following → genuine discrimination.
**Fail:** controls as wide as facilities **and** P-2 fails → **the question is unanswerable with this
instrument. Report that.** It is a legitimate finding and it belongs on the limitations slide **before a
judge finds it.**

### Q-3 (B-DATA) — ⚠ Contamination screen
**Assumption validated:** that controls are outside every plume.
**Do:** exclude any candidate control within **1 km** of any data centre.
**Why it matters:** **a warehouse 400 m downwind of a facility is inside the plume — it is not a control.**
Including it inflates the null and **hides a real effect.** This is the error a careless implementation makes.
**Pass:** ≥50 controls survive the screen.
**Fail:** too few → widen the metro polygon, or relax to 800 m and state the relaxation.

### Q-4 (B-CLAIM) — Matching quality
**Do:** compare facilities and controls on building footprint area, roof type (OSM tags / imagery),
surrounding impervious fraction, distance to nearest major road, and elevation.
**Pass:** distributions overlap substantially on all five.
**Fail:** a systematic difference → re-select controls, or report the imbalance as a limitation.

---

## GROUP R — Is the field what it claims to be?

### R-2 (B-CLAIM) — ⚠⚠ Can **free data** predict FortyGuard's field? *(free — the substitution test, quantified)*
**Assumption validated:** the entire "only FortyGuard" premise.
**Do:** fit a simple model from **free inputs only** — OSM land use, building footprint density, Sentinel-2
NDVI, elevation, distance to water — to FortyGuard's saved field. Report R².
**Pass:** R² moderate (say < 0.8) → there is information in the field beyond land cover, which is where a
plume could live.
**Fail:** **R² > 0.9 → FortyGuard is essentially a land-cover function and adds nothing beyond free data.
The premise collapses.**
**Why it matters:** this converts *"why do you need FortyGuard?"* from an argument into **a number.** It
costs nothing and **must be run before Aug 18.**

### R-1 (B-CLAIM) — Air vs. surface, stronger than B-6
**Do:** within one scene, compare the diurnal amplitude of a **paved** tile against a **vegetated** tile.
**Pass:** both swing ~8 °C, offset by 1–2 °C → air.
**Fail:** paved swings 20–30 °C while vegetation swings ~10 °C → surface temperature. Contradicts B-6;
investigate before anything else.

### R-3 (B-CODE) — Does the field respond to weather **at all**?
**Assumption validated:** that the field is live rather than climatological.
**Do:** two historical days with very different regional conditions per METAR (≥8 °C apart). Compare
FortyGuard's mean against METAR's change.
**Pass:** FortyGuard tracks METAR's swing within a reasonable factor.
**Fail:** **FortyGuard barely moves while METAR swings 10 °C → the field is a climatology, not a
measurement.** Nothing about plume detection would be meaningful. **Never run before; fundamental.**

### R-4 (B-DATA) — Lattice stability, extended
**Already partly verified:** 6875/6875 identical geometry across a forecast/historical pair, and 43/43 across
`filter_type` 3 vs 4 [measured].
**Do:** extend across a long time gap (2024 vs 2026) and across `filter_type` 1 vs 2.
**Fail:** the grid re-anchors → per-tile time series invalid; snap to a self-defined lattice and state the
coarsening.

---

## GROUP T — Is the statistic sound?

### T-1 (B-CLAIM) — Wedge-geometry sensitivity
**Do:** sweep half-angle **30/45/60/90°**, inner radius **0/100/200 m**, outer radius **300/500/800 m**.
**Pass:** the differential's sign and rough magnitude survive across most of the grid.
**Fail:** the result appears at only one geometry → **it is a fishing expedition.** Report the sweep, not
the best cell.

### T-2 (B-CLAIM) — Spatial effective sample size
**Do:** from the §Z-P3 decay curve, estimate the decorrelation distance; divide wedge area by it.
**Why it matters:** 500 tiles in a wedge are **not** 500 independent samples. The confidence interval on the
wedge mean depends on n_eff, not tile count.

### T-3 (B-DATA) — ✅ Usable-day census — **MEASURED 2026-08-09**
**Assumption validated:** that enough days have wind steady enough for "downwind" to mean anything.
**Measured** at KIAD, summer 2025, 12:00–20:00 local:

```
days assessed                                            90
usable (steadiness ≥0.85 AND mean speed ≥6 kt)           31   (34 %)
  → a 13-day live window yields only ~4.5 usable days
octants populated over one summer                         7 / 8
sensitivity   ≥0.80 / ≥5 kt →  41 days (46 %), 8/8 octants
              ≥0.90 / ≥8 kt →   9 days (10 %), 5/8 octants
```

**⚠ CONSEQUENCE — this changed the plan.** The interference matrix **cannot be accumulated during the live
window.** It must be built from **history**, with days selected by METAR bearing. **The live window's job is
confirmation, not construction.** Relax to ≥0.80 / ≥5 kt when a bearing octant is thin, and mark any cell
built on fewer than 5 days as unreliable — **never interpolate across an empty cell.**

---

## GROUP U — Does the operational claim actually follow?

### U-1 (B-CLAIM) — ⚠⚠ Does the interference change **any** decision? *(free — and it gates the whole money half)*
**Assumption validated:** that a measured intake penalty has operational consequence.
**Do:** over the historical record, count the hours where ambient sits **within the interference magnitude
of the threshold** — the only band where a 1.2 °C penalty flips the free-cooling decision.
**Pass:** ~200 h/yr → the operational claim is real.
**Fail:** ~5 h/yr → **the operational half is worthless even with a perfect measurement.** Ship the
measurement half only (A2/A4/A5) and say so.
**Why it matters:** nothing else in the project tests this, and it decides whether Half B exists. Pure
computation.

### U-2 (NICE) — Intake-location sensitivity
**Do:** shift the sample point 60 m and 120 m in each direction; recompute.
**Pass:** the differential is stable → the 60 m tile is an adequate proxy for a real intake location.
**Fail:** highly sensitive → widen the wedge inner radius and state the uncertainty.

### U-3 (B-CLAIM) — Does the differential **repeat**?
**Already known for the field generally:** ~73 % of the between-tile pattern persists day to day [measured].
**Do:** the same for the *differential* at a given bearing, across many day-pairs.
**Pass:** the penalty at a bearing is stable → the interference matrix is a real asset.
**Fail:** it does not repeat → the matrix is noise; report per-day detections only, no matrix.

---

## GROUP V — Independent cross-validation

### V-1 (B-CLAIM) — ⚑ Before / after commissioning — **possibly the most persuasive check available**
**Assumption validated:** that the warm signature is caused by *operation*, not by *construction*.
**Do:** pick a facility with a known opening date. Request the **same polygon** at three epochs: before
construction, during construction, after operation began.

```
signature appears at CONSTRUCTION   →  it is land cover        (supports Masley)
signature appears at COMMISSIONING  →  it is waste heat        (supports Sailor)
```

**Why it outranks everything except P-2:** it **separates the two hypotheses in time rather than in space**,
so it is immune to *every* land-cover confound. It is Masley's own requirement (iii).
**Constraint:** bounded by history depth — **2019 fails** [measured]. Bisect 2025 / 2023 / 2021 first.
**Fail (insufficient depth):** drop V-1 and rely on P-2 + Q-2. **Cost:** the most persuasive argument in the
writeup is lost.

### V-2 (B-CLAIM) — Multi-station METAR leave-one-out
Carried from **W-6**. **The only check in the project judged by a physical instrument.** Still never run;
still free.

### V-3 (B-CLAIM) — Satellite LST at the same sites
**Do:** pull MODIS or ECOSTRESS land-surface temperature for the same facilities and dates. Compute the same
wedge differential on LST.
**Record:** how much larger the LST differential is than the air differential.
**Why it matters:** this is **an artifact as much as a check** — it puts the scientific dispute on screen and
quantifies the error the satellite studies made. Expect LST to show a much larger apparent effect.

---

# GROUP G — Async behaviour and latency

Your collector runs on a schedule across three sites, and the unit of perception is now a heatmap rather
than a point — so **G-1 is B-CODE, not P1**. A heatmap at granularity 60 over a campus is materially
slower than a point query, and the hourly cycle is a hard constraint.

### G-1 (B-CODE, P1) — How long do jobs take?
**Assumption:** O7.1, M2.4.
**Do:** time submission → `Completed` for: a single-hour env_params; a 12-hour env_params; a small
heatmap; a large heatmap at granularity 60.
**Record:** seconds for each.
**Pass:** a full collector run (3 sites × M points) completes well inside an hour.
**Fail:** too slow sequentially → **Workaround:** parallel submission (G-5). If that's unavailable, cut
sample points. **Cost:** if a run takes 20+ minutes, the "hourly snapshot" isn't a snapshot — see G-6.

### G-2 (B-CODE, P1) — Does the documented 404-right-after-submit happen?
**Do:** poll the status endpoint **immediately** after submitting, with no delay.
**Record:** do you get a 404? For how long?
**Why it matters:** the docs warn *"Activity not found or temporarily unavailable immediately after
submission."* A naive poller treats 404 as fatal and discards a job that was about to succeed. You need
an initial delay or a 404 grace period. **Workaround:** treat 404 as retryable for the first N seconds,
then fatal.

### G-3 (NICE, P1) — What's a sensible poll interval?
**Do:** derive from G-1's timings.
**Record:** a recommended interval and a max attempt count.
**Why it matters:** the docs' example polls every 5 s up to 120 times. Confirm that's sane, and make
the bound explicit so a hung job can't stall the collector past its hour.

### G-4 (NICE, P2) — How long do results persist?
**Do:** fetch a completed `activity_id`, re-fetch an hour later, and again the next day.
**Record:** still available? Any expiry?
**Why it matters:** if results persist, you can re-read a response for free instead of re-spending
credits — which is why `activity_id` is in Z-3's schema. Also the cheapest route to replay fixtures.

### G-5 (B-CODE, P2) — Can you run jobs in parallel?
**Do:** submit 5 jobs before polling any of them.
**Record:** all accepted? Any concurrency error?
**Why it matters:** parallel submission is the fix for G-1's latency and is what keeps the collector
inside its hour. Cross-check against A-5's rate limit — parallel submission is the fastest way to hit a
429.

### G-6 (B-DATA) — Per-call issuance time, not per-run
**Assumption:** O7.5.
**Why:** if a full run takes 15 minutes, the last site's forecast was issued 15 minutes after the
first's. Recording one `issued_at` for the whole run introduces a systematic timing error into every
residual — small, but exactly the kind of thing that quietly biases a calibration set.
**Do:** from G-1's timings, measure the wall-clock spread of one complete run.
**Pass:** the spread is under ~2 minutes → a per-run timestamp is fine, but log per-call anyway; it's
free.
**Fail:** the spread is 10+ minutes → **you must log `issued_at_utc` per call**, as Z-3's schema
already requires. **Cost:** none, if you do it from row one. Unrecoverable if you don't.

---

# GROUP H — Errors and edge cases

You need these to build the fail-safe path. **Every one must end with "recommend chillers," never a
crash, and never a silently-substituted default.**

For each: **record the exact HTTP status and the exact error message text.**

### H-1 (NICE, P2) — Date before 2019-01-01
### H-2 (NICE, P2) — Date beyond the forecast horizon
Covered by B-2 — just record the message text here.
### H-3 (B-DATA, P2) — Coordinates outside the US
**Assumption:** O7.4.
**Why it matters:** docs say US-only. Does it 400, or silently return garbage? **Silent garbage is far
more dangerous** — a plausible-looking number for a place with no data would poison your calibration
set. **Pass:** clear error. **Fail:** 200 with values → **Workaround:** validate coordinates against a
US bounding box before every call, client-side.
### H-4 (NICE, P2) — Coordinates in the ocean, or a wildly invalid value like `lat: 999`
### H-5 (NICE, P2) — Malformed polygon (first and last coordinates not identical)
### H-6 (NICE, P2) — A deliberately wrong API key
**Record:** 401 or 403?
### H-7 (NICE, P2) — A missing required field
### H-8 (B-CODE, P3) — Can a job return `Failed` rather than being rejected up front?
**Why it matters:** two different failure paths needing two different handlers, and only one is visible
at submission time. Your fail-safe must cover both.

---

# GROUP I — Consistency and forecast behaviour

This group tells you how *reliable* the forecast is — directly relevant to the conformal layer.

### I-1 (B-DATA, P1) — Is the same request reproducible?
**Assumption:** S4.1, S4.3.
**Do:** an identical request twice, a few minutes apart, for a **past** date. **Then repeat the same
request on day 2 and day 8** — see K-5, because a minutes-apart check won't catch a nightly reanalysis.
**Record:** byte-identical values, at each interval?
**Why it matters:** historical data should be stable. If it drifts, caching, reproducibility, and your
residuals all become problems.

### I-2 (B-CLAIM, P1) — ⚠ Does a forecast for a fixed future time change as that time approaches?
**Do:** pick a target ~10 hours out. Query it now. Query the **same target** again in 2 hours, and again
2 hours later.
**Record:** the predicted value at each query, with the time you queried.
**Why it matters:** **one of the most informative checks here.** It tells you whether forecasts get
*revised*, and by how much. The size of those revisions is a direct early read on forecast uncertainty
per horizon, before you've built any conformal machinery. Large swings at 10 hours out and small ones
at 2 is exactly the horizon-dependent pattern your intervals need to widen for.

**Two extra uses:** (1) this is the **fallback volatility signal** from NVIDIA §3.4 — big revisions mean
an unsettled atmosphere. Record it into `volatility_signal` in Z-3's schema from day 1, because it
cannot be reconstructed later. (2) **If forecasts are never revised at all, that's a B-5 red flag** — a
genuine forecast should change as new information arrives.

### I-3 (B-CLAIM, P2) — Do neighbouring points agree?
**Assumption:** M2.1.
**Do:** query `env_params` at 3–4 points a few hundred metres apart, at all three sites.
**Record:** spread in wet-bulb across them.
**Pass:** a measurable spread → the microclimate variation your project is premised on is real.
**Fail:** identical values → **check E-7 before concluding anything**, because grid snapping produces
exactly this symptom and means something completely different. If E-7 shows the resolution is genuinely
coarse, then be honest in your writeup: the hyperlocal resolution isn't doing what the marketing
suggests, and your value comes from the site-vs-airport gap (W-4) rather than from within-site
variation. **Cost:** you lose the microclimate-sampling story but keep the spatial-gap story, which is
the stronger of the two anyway.

### I-4 (NICE, P2) — Do heatmap and env_params agree at the same point?
**Do:** get temperature at point P from the heatmap; compare to the `temperature` echoed by
`env_params` for the same point and time.
**Record:** match, or systematic offset?
**Why it matters:** confirms whether the intended workflow really is heatmap-then-env_params (see B-7),
and whether the two share an underlying model. A large disagreement means one of them is a different
product — cross-check B-6.

---

# Design rules that fall out of this audit

These aren't checks; they're decisions to build in from the first line of code.

**1. The agent must never call `datetime.now()` internally (O7.3).** Pass "now" in as a parameter. A
forecast fixture is only meaningful relative to its issuance time, so replay mode is impossible if the
agent reads the real clock — it will compute horizons off today's date and mismatch every fixture. This
is the single most common way beginners make their code untestable. One parameter, threaded through.

**2. Store every timestamp in UTC. Convert to local only for display.** Three timezones, one without
DST (C-10). No exceptions, no "just this once."

**3. Define staleness explicitly, and log it.** Per B-3, you may have no issuance timestamp, so
staleness may only mean fetch age. Whichever it is, write the rule down as a number ("data older than
90 minutes is stale → recommend chillers") rather than leaving it implicit.

**4. A null is not a zero.** Per D-1, a missing wet-bulb must propagate as *missing* all the way to the
decision, where it means chillers. A wet-bulb of 0.0 °C looks like perfect free-cooling weather. Never
let a parse failure produce one.

**5. Rename "upwind/downwind" unless D-6 finds wind data.** Call it what it is — a fixed spatial
pattern. In the code, in the logs, and in your narration.

**6. Assert physics on every row you write.** Wet-bulb ≤ dry-bulb (D-2). Residuals non-zero (K-3).
Values within a plausible range for the site and season. These are three cheap `assert`s that catch
whole categories of silent corruption.

**7. If the conformal bound can't be computed — too few samples, zero residuals, stale calibration —
fall back to the Phase-1 fixed safety margin, log the reason, and keep running.** The conformal layer
must never be able to stop the agent, and must never produce a zero-width interval.

**8. Log σ_spatial on every row from row one, even before you use it.** Per S-3 and K-9, the spatial
spread of the field at issuance is the conditioning variable for the margin — and like the forecast
itself, it is **unrecoverable after the fact**, because re-querying that hour returns the hindcast field,
not the field you saw when you decided. If K-9 turns out to fail, an unused column costs nothing. If you
omit it, weeks of data cannot answer the project's central question. Same reasoning for
`db_stddev_c` — log it too, in case E-8 forces the dry-bulb proxy path.

**9. Guard the degenerate σ.** The normalised score divides by σ. Floor it (`σ + 0.1 °C`), **and** branch
separately on σ being exactly zero over a multi-tile field — that is suspicious data, not a smooth day,
so use the global margin and log it. A single-tile polygon has *undefined* σ, not zero (see the master
plan's §12.4).

**10. Never truncate silently. Log every cap you apply.** If A1's historical sweep samples weekly rather
than daily, if refinement is limited to the top σ decile, if a site was skipped — say so in the output.
A reader must not be able to mistake a sampled result for an exhaustive one. This is the difference
between a stated limitation and a misleading claim.

---

# How to report back

For each check you complete, give me:

```
CHECK ID:        B-5
ASSUMPTION:      P1.4 — future values are genuine forecasts
WHAT I SENT:     (the request body, or what you varied from the previous test)
HTTP STATUS:     200 / 400 / 422 / ...
RAW RESPONSE:    (paste it — truncate very long map_data, but keep metadata in full)
VERDICT:         pass / fail / inconclusive
WHAT I NOTICED:  (optional — anything surprising)
```

**Please don't tidy the output.** Exact error strings, exact field names, exact capitalisation. A
message like `"date_time must not exceed 12 hours"` tells me far more than "it rejected the date."

**Priority for reporting.** Under the *Downwind* design the order changed. Send these first:

| Question | Checks | Status |
|---|---|---|
| **Is there anything to measure?** (facilities close enough together) | **Z-5** | ✅ passed, 4 metros |
| **Can the instrument see 500 m detail?** | **Z-7** | ✅ passed, 8–24× margin |
| **Are there enough usable days?** | **T-3** | ✅ 34 % — matrix must come from history |
| **⚠ Could free data do this instead?** | **R-2** | **TODO before Aug 18. R² > 0.9 ⇒ premise collapses** |
| **⚠ Does the measurement change any decision?** | **U-1** | **TODO. Gates the money half** |
| **⚠⚠ Does the warm side move with the wind?** | **P-2** | **Aug 18, call 2. World A vs World B** |
| **Do we reproduce a peer-reviewed result?** | **P-1** | Aug 18, calls 3–4 |
| **Are the controls valid, or too good?** | **Q-1, Q-2, Q-3** | Q-3 free now; Q-1/Q-2 Aug 18 call 6 |
| **What does it cost?** | **A-3 + S-1** | Aug 18, call 1 |
| **Is it air, and does it respond to weather?** | **B-6, R-1, R-3** | B-6 ✅; R-1/R-3 Aug 18 |
| **How far back does history go?** | **history bisection** | 2019 fails; Aug 18 calls 9–11 |

Everything else can be worked around.

**If something crashes or behaves in a way this document doesn't anticipate — tell me that too.** An
unexpected result is more valuable than a clean one; it means we found something the docs hid.

---

## What I'll do with your results

| Check | What it decides |
|---|---|
| **Z-1 / K-1** | Whether conformal prediction can start on day 1 or must wait for collected data |
| **Z-3** | Locked before anything else — the log schema you'll live with |
| **Z-4 / A-3 / S-1 / A-7** | Granularity, refinement policy, collector cadence, A1's sweep density — and which rung of Z-4's degradation ladder you're on |
| **S-3** | ⭐ **Whether σ_spatial exists.** If it doesn't, the entire uncertainty contribution is rebuilt from `map_data` at higher bandwidth cost |
| **S-7** | Whether the 12-hour window is one call or twelve. A ~12× swing in every budget number |
| **S-8** | Whether per-tile time series are valid — i.e. whether **A1** can be built at native resolution or on a self-defined lattice |
| **S-9** | Whether FortyGuard already sells a better uncertainty signal than your proxy. If yes, use theirs |
| **B-1 / B-4 / B-5** | The forecast data path — direct, derived, or redesigned. **B-5 also gates F-2's forward use** |
| **B-6 / B-8** | Whether the numbers mean what the design assumes. If these fail, everything downstream is wrong |
| **B-7 / E-8 / S-6** | Native spatial wet-bulb, versus dry-bulb field + humidity field + per-tile psychrolib — and whether σ becomes a documented dry-bulb proxy |
| **F-1 / F-2 / F-3** | Whether the decision is computed server-side or client-side, and whether **A1** uses `exceedance` or hand-counted tiles |
| **B-2 / C-2 / C-9** | The agent's planning window, time step, and threshold margin |
| **K-2 / K-3** | Whether residuals exist at all. **K-3 is the make-or-break for the conformal layer** |
| **K-4 / K-5** | The collector's actuals cadence and the calibration set's settling lag |
| **K-6 / K-7 / K-8** | The confidence level, the score function, and whether to pool across sites |
| **K-9** | ⭐ **Whether the σ-conditioned margin is real.** Stage 1 answers this in week 1 with thousands of samples; Stage 2 confirms it live |
| **W-3** | Whether your truth source is trustworthy — and the honest sentence you'll write about it |
| **W-4** | The site-vs-station gap, and which direction it goes |
| **W-6** | ⭐ **The headline number, measured against real thermometers** — the one result that doesn't depend on a hindcast |
| **D-6** | Whether "upwind" is real or needs renaming |
| **E-7 / I-3** | Your real spatial resolution, and whether the microclimate story survives |
| **G-1 / G-2 / G-5 / G-6** | The polling, concurrency, and timestamping design — G-1 now gates whether hourly field perception is possible at all |
| **I-2** | Initial expectations for interval width per horizon, plus the fallback volatility signal |
