# Thermal Autopilot — Master Execution Plan

**A free-cooling decision agent for AI data centers, built on FortyGuard's forecast thermal field,
with a spatially-conditioned conformal confidence bound.**

| | |
|---|---|
| **Status** | Design complete. **No code written yet.** Every number marked ⚠ is an unverified assumption with a named check. |
| **Timeline** | >30 days. Solo developer, second-semester CS level, learning the theory while building. |
| **Primary judge** | FortyGuard. NVIDIA secondary. |
| **Sites** | Ashburn VA · Phoenix–Goodyear AZ · Hillsboro OR |
| **Hard constraints** | Plain-Python agent loop (no LangChain/LangGraph/CrewAI/AutoGen) · fail-safe to chillers · non-removable human gate · working agent early · no fabricated capabilities (labelled stubs only) · replay-mode fixtures |
| **Companion docs** | [fortyguard-day1-data-checks.md](fortyguard-day1-data-checks.md) (the verification protocol) · [what-am-i-building.md](what-am-i-building.md) and [how-it-all-fits.md](how-it-all-fits.md) (beginner narratives) · [i-m-a-second-semester-computer-zazzy-hennessy.md](i-m-a-second-semester-computer-zazzy-hennessy.md) (learning plan) · [nvidia-integration-plan.md](nvidia-integration-plan.md) |

> **Reading note.** This document is written for an engineer who has never seen the project. Every
> technical term is defined the first time it appears, and §18 is a full glossary. Terms are defined
> inline rather than front-loaded so the document opens with substance.

---

# §0 — The one page

## What it is

An autonomous agent that decides, hour by hour, whether a data center should cool itself with
**free cooling** (a cooling tower evaporating water into outside air — cheap) or **mechanical
chillers** (a large refrigeration compressor — expensive but always works).

The decision hinges on **wet-bulb temperature**: the lowest temperature you can reach by evaporating
water into air. It is a hard physical floor — *a cooling tower cannot produce water colder than the
ambient wet-bulb.* Free cooling is viable only when wet-bulb sits low enough.

## The value claim, in one sentence

> Facilities today make this decision from a weather station at an airport 10–30 km away sitting in a
> grass field, while the plant's tower breathes air off a concrete campus saturated with its own waste
> heat — and they have no calibrated statement of how wrong that reading is likely to be. This agent
> replaces both halves: FortyGuard's 60-metre forecast thermal field supplies the *right place*, and a
> conformal prediction layer — **whose margin is itself set by the structure of that field** — supplies
> a bound with a measured coverage rate.

## Why this cannot be built without FortyGuard

Four load-bearing components require a **forecast thermal field**, not a point forecast:

1. **The uncertainty layer** conditions its safety margin on the *spatial heterogeneity* of the field
   (§7.6). A point API cannot supply that number. Remove FortyGuard and the confidence bound loses its
   only physical input.
2. **The perception loop** decides *where to look next* by reading the field's structure and refining
   granularity over the hot spot only (§8.3). No field → no action space → no agency.
3. **The decision primitive** is FortyGuard's own `exceedance` / `persistence` heatmap modes —
   "hours below threshold per tile" and "longest safe run per tile", computed server-side (§3.2).
4. **Both headline artifacts** — the 60 m annual free-cooling-hours map and the leave-one-station-out
   skill test — are field products. A 2.5 km gridded forecast fails the second by construction.

The full substitution test is in §2.5.

## The three headline artifacts

| # | Artifact | Depends on live collection? |
|---|---|---|
| **A1** | **The free-cooling-hours map.** Per-tile count of annual hours below threshold at 60 m over each campus, from FortyGuard history 2019→2026. Shows two spots on *one campus* differing by hundreds of hours per year. | **No** — buildable in week 1 |
| **A2** | **The leave-one-station-out skill test.** FortyGuard vs. inverse-distance interpolation vs. nearest-station-copy, scored against real airport instruments at held-out stations. | **No** — buildable in week 1 |
| **A3** | **The spatially-conditioned coverage table.** Empirical coverage and mean interval width for global conformal vs. σ-normalised conformal, with the H1 hypothesis verdict. | **Yes** — needs the collector |

A1 and A2 are schedule-independent. That is deliberate: **a complete, defensible result exists before
any waiting begins.**

---

# §1 — The problem, quantified

## 1.1 The physical setup

A data center converts electricity into heat at nearly 1:1. A 10 MW facility produces ~10 MW of heat
that must leave the building continuously. Two mechanisms:

**Mechanical chillers.** A vapour-compression refrigeration cycle. A compressor does work to move heat
from cold water to warm outside air. Works at any outdoor condition. Expensive because the compressor
is the dominant electrical load.

**Free cooling (waterside economizer).** Warm return water is sprayed down through a **cooling tower**
while fans blow outside air upward through it. Some water evaporates; evaporation absorbs latent heat;
the remaining water lands in the basin cooler. A heat exchanger transfers that coolth to the facility
loop and **the compressor is switched off entirely.** Only tower fans and pumps run.

The floor on this process is the **wet-bulb temperature** — the temperature a wet thermometer reaches
in moving air, i.e. the temperature air reaches when saturated adiabatically. You cannot evaporate your
way below it.

Two consequences that shape the whole project:

- **Wet-bulb, not dry-bulb, is the governing variable.** Phoenix at 40 °C dry-bulb and 10 % humidity
  has a *lower* wet-bulb than Virginia at 30 °C and 80 % humidity. Free cooling works better in the
  desert than the intuition suggests. This is why the site set includes Phoenix.
- **The tower never reaches the floor.** Water and air are in contact for only seconds. The gap between
  the ambient wet-bulb and the water the tower actually produces is the **approach temperature**,
  typically 2–5 K. §6 derives the threshold from it.

## 1.2 The decision, and why it is hard

Every hour someone decides: free cooling or chillers, for the hours ahead. The decision is forward-
looking because thermal mass makes a wrong switch slow to undo — you cannot un-warm a loop instantly.

**The two errors have wildly different costs.**

| Error | Consequence |
|---|---|
| Ran chillers when free cooling would have worked | Wasted electricity. Recoverable. Purely financial. |
| Ran free cooling when it could not hold setpoint | Supply-water temperature rises → rack inlet temperature rises → thermal throttling, and at the tail, hardware damage or an unplanned shutdown. |

This asymmetry means a 50/50 forecast is unacceptable, and it means the agent needs a **one-sided upper
bound** on wet-bulb, not a symmetric confidence interval. The formal framing is the meteorological
**cost-loss decision model**: protect when the probability of the bad event exceeds C/L, the ratio of
the cost of protecting to the loss from being unprotected. §6.4 makes this concrete.

## 1.3 The money, with arithmetic

Every constant below is a **⚠ stub value** — a documented placeholder a facility engineer would
replace. They live in one module (`fgcool/config.py`) with the derivation in comments, and §10.5
requires the whole evaluation be re-run across a sweep of them so no conclusion depends on a guess.

```
Facility thermal load                    10,000 kW_th          ⚠ stub
1 refrigeration ton                     = 3.517 kW_th          (exact)
Cooling load                             10,000 / 3.517  = 2,844 tons

Full chiller plant, incl. pumps + tower   0.85 kW_e/ton        ⚠ stub  (typical water-cooled range 0.6–1.0)
Free-cooling mode (fans + pumps only)     0.20 kW_e/ton        ⚠ stub  (typical range 0.15–0.25)
                                          ----
Saving while in free cooling              0.65 kW_e/ton

Electrical saving        2,844 × 0.65   = 1,849 kW_e
Industrial electricity price              $0.085 /kWh          ⚠ stub
                                          ----
Saving per free-cooling hour            ≈ $157 / h
```

Therefore:

- **One extra correctly-identified free-cooling hour per day ≈ $57,000 / year** at one 10 MW site.
- **100 extra hours per year ≈ $15,700.**
- A1 (the free-cooling-hours map) will show intra-campus spreads plausibly in the **hundreds of hours
  per year**. That spread, multiplied by the number above, is the size of the decision that current
  practice makes with a thermometer in the wrong place.

The counterweight, stated honestly: a single thermal excursion in a facility full of accelerators can
cost more than a year of the savings above. That is why the fail-safe defaults to chillers and why the
human gate is non-removable.

## 1.4 Why AI factories widen the opportunity rather than narrowing it

The intuitive read is that denser compute means less free cooling. **The opposite is true, and it is
the strongest domain point in the project.**

Dense accelerator racks (the ~120 kW class, versus 5–15 kW for conventional racks) are **liquid-cooled
at the chip**, and direct liquid cooling tolerates far warmer coolant than air cooling does — warm-water
cooling is a design goal, not a compromise. A higher acceptable supply-water temperature raises the
water-temperature ceiling at the top of the derivation ladder in §6, which raises the ambient wet-bulb
threshold, which **increases the number of hours per year that qualify for free cooling.**

So the exact facilities being built right now are the ones where an intelligent free-cooling decision
unlocks the most hours. That reframes the project from "energy efficiency" to "capacity unlock."

*Cited anchors for §1: ENERGY STAR's waterside-economizer guidance (wet-bulb below 55 °F for
3,000+ hours/year as a suitability screen) and the LBNL/DOE FEMP best-practices guide for data center
design. Both are linked in the learning plan's Tier 1 §3.*

---

# §2 — Why a point forecast cannot answer this question

This section is the project's thesis. Four claims, each with the check that verifies it.

## 2.1 The governing *variable* is wet-bulb, not temperature

Established above. Verified by **B-8** (a three-way cross-check: FortyGuard's
`wet_bulb_temperature_celsius`, psychrolib's computation from the same dry-bulb + humidity, and the
Stull closed-form approximation must agree within tolerance). B-8 simultaneously rules out the
confusable quantity **wet-bulb *globe* temperature** (WBGT), a different heat-stress index used for
sports safety.

## 2.2 The governing *location* is the tower intake, not the airport

The reference measurement in current practice is a **METAR** observation — the hourly report every
airport publishes from real instruments, free and archived for decades. Airport stations sit
deliberately in open grass, away from buildings, precisely to be *unrepresentative* of built
environments.

A data center campus is the opposite: acres of concrete and steel with waste heat pouring off it. The
difference has a name — the **urban heat island** — and it is strongest on calm nights, which is
exactly when a marginal free-cooling decision is being made.

**This is the claim A2 measures, against real thermometers** (§9.2).

## 2.3 The governing *quantity* is a field, not a point — for two independent reasons

**Reason one: the hottest spot governs safety.** The tower draws from wherever it sits. A single
representative-looking point can be the coolest corner of the property. Safety is set by the maximum
over the intake-relevant area, so the agent needs the *distribution* across the site, not one draw
from it.

**Reason two — the deeper one: the field's *structure* tells you how much to trust the forecast.**

> **Hypothesis H1.** Forecast error at a point is larger when the thermal field over the surrounding
> campus is **sharply structured** than when it is **smooth**.

Physical reasoning: a smooth field means one well-mixed air mass sitting over the site — the easy case
for any forecast. A sharply structured field means gradients are being *advected* across the site:
frontal passage, a sea-breeze boundary, heat-island edge effects, drainage flow. In those conditions a
forecast for one specific spot is far less reliable, because a small timing error in the boundary's
arrival translates into a large temperature error at a fixed location.

If H1 holds, then **the field's spatial standard deviation is a measurable, physical, real-time
difficulty signal** — and it can be fed into the confidence bound. That is §7.6, the single most
important design decision in this document.

H1 is falsifiable and pre-registered. The protocol, including what counts as failure, is §9.3.

## 2.4 The governing *horizon* is a window, not an instant

Because switching is slow to reverse, the agent commits for a window. The commitment must be safe for
*every* hour in it — the worst hour governs. This is why the guarantee needed is **joint coverage over
the window**, not per-hour coverage, and why §7.5 uses a max-over-horizon score.

FortyGuard's `persistence` mode computes exactly this quantity — longest consecutive run below a
threshold — per tile, server-side.

## 2.5 The substitution test

The honest way to check whether a data source is load-bearing: swap it for the nearest free
alternative and see what breaks. Alternative: the US National Weather Service gridded point forecast
(free, no key, ~2.5 km grid).

| Component | With FortyGuard | With an NWS point forecast |
|---|---|---|
| Threshold comparison | works | **works — identical** |
| Global conformal margin | works | **works — identical** |
| Fail-safe, logging, human gate | works | **works — identical** |
| **σ-conditioned margin (§7.6)** | works | **impossible** — no field, no σ |
| **Coarse-to-fine sampling (§8.3)** | works | **impossible** — no granularity to choose |
| **Per-tile `exceedance` / `persistence` (§3.2)** | works | **impossible** |
| **A1 — 60 m free-cooling-hours map** | works | **impossible** at ~2.5 km; a campus is one grid cell |
| **A2 — leave-one-station-out** | works | **fails by construction** — at 2.5 km it cannot resolve inter-station gradients |
| **Hot-spot location for sensor siting (§9.1)** | works | **impossible** |

**Read the top three rows honestly:** the generic decision machinery survives substitution. That is
precisely the design flaw this revision corrects. Everything below the divider does not survive — and
those rows are where the project's contribution lives. If a future change moves weight back above the
divider, that is a regression.

---

# §3 — FortyGuard capability map

Every documented surface, and exactly what this project does with it. **No row may be blank** — an
unused capability must state why.

Facts confirmed from FortyGuard's documentation (carried from the checklist's reference block):
header auth `api-key` · async submit→poll→retrieve via `activity_id` · date range 2019-01-01→present,
heatmap additionally to now+12 h · `filter_type` 1 = single hour, 2 = range (max 23 h), 3 = single day ·
granularity 60/80/100 m · United States only · heatmap max area 10 mi² (Basic/Startup), 50 mi²
(Premium) · `env_params` 3 parameters per request (Basic/Startup) · credits deducted only on
`Completed`.

## 3.1 `POST /v1/heatmap` — the primary perception path

| Surface | What it gives | Where this project uses it | Breaks what if removed | Check |
|---|---|---|---|---|
| Polygon request + `granularity` 60/80/100 | A tiled field over an arbitrary GeoJSON polygon | **The core perception primitive.** Campus field every hour, all three sites | Everything below the divider in §2.5 | E-1, E-3, S-2 |
| `map_data` (per-tile values) | The field itself | Field max (safety), hot-spot location, per-tile artifacts | A1; hot-spot siting; the max-over-site aggregation | E-1, S-2 |
| `stats_data` (min/max/mean/stddev) | Summary statistics across tiles in one small payload | **σ_spatial — the conditioning variable for the conformal margin (§7.6).** Also the cheap read in the coarse pass of §8.3 | The entire uncertainty innovation; R1; A3 | E-4, S-3 |
| Forecast to now + 12 h | A *forecast* field, not just a nowcast | The 12-hour commitment window | The whole forward-looking design | B-1, B-2, **B-5** |
| History 2019-01-01 → present | ~7.6 years of fields | **A1** (free-cooling-hours map), **A2** (leave-one-station-out), the well-powered H1 pre-test (§9.3), backtest, baselines | A1, A2, the H1 pre-test, all evaluation | W-1, S-1 |
| `filter_type = 2` (range, ≤23 h) | Up to 23 hours in **one** call | **The primary credit-saving lever** — the full 12 h window in a single request instead of twelve | Budget feasibility (§11.1) | C-8, S-7 |
| `filter_type = 1` / `3` | Single hour / single day | Single-hour used for the actuals backfill; single-day used for historical sweeps | Backfill efficiency | C-2, A-4 |
| Mode `tcm` (snapshot, °C/tile) | The plain field | Hourly perception; the input to σ_spatial | Perception | F-1 |
| Mode **`exceedance`** + `threshold` + `direction: below` | Count of hours above/below a threshold, per tile | **The decision, computed server-side:** free-cooling hours available per tile over the window. Historically: **A1** | A1; the server-side decision path | **F-2**, S-4 |
| Mode **`persistence`** | Consecutive-run semantics | **The commitment window** — longest safe run per tile (§2.4) | The window recommendation's strongest form | **F-3**, S-5 |
| Mode `time_of_measure` | Hour 0–23 UTC of the peak | The daily binding hour per tile → when the risk window sits, per site | The "when is this site fragile" narrative | F-1 |
| Variable selection (does any mode carry **wet-bulb**?) | Unknown | If yes: spatial wet-bulb directly, large simplification. If no: dry-bulb field + humidity field + per-tile psychrolib | Cost and complexity of everything spatial | **E-8** |
| Area cap 10 mi² | Constraint | Campus polygons are ~0.1–0.5 mi², far inside the cap — the cap is not a limitation here, and staying small is also the credit lever | — | E-5, E-6 |
| Effective resolution | Unknown whether a point snaps to a coarser cell | Determines whether the 60 m claim is real | The hyperlocal claim's magnitude | **E-7** |

## 3.2 `POST /v1/env_params` — the point path, now secondary

| Surface | What it gives | Where used | Breaks what if removed | Check |
|---|---|---|---|---|
| Point query, `wet_bulb_temperature_celsius` | Wet-bulb at a coordinate | (a) **A2's per-station queries**; (b) point wet-bulb wherever the heatmap cannot supply it; (c) cross-check against the field at the same point | A2; the wet-bulb path if E-8 fails in both directions | B-1, B-4, B-7, I-4 |
| 3-parameter cap (Basic/Startup) | Constraint | Request exactly: wet-bulb, relative humidity, dry-bulb — the three needed to self-validate via psychrolib | B-8's cross-check | A-2, B-8 |
| The `temperature` input field | Undocumented semantics | Unknown whether it is an input to a calculator or an echo. If a calculator: feed it forecast dry-bulb from the heatmap → forecast wet-bulb, which **rescues the design if B-1 fails** | The fallback path | **B-4** |
| Future timestamps | Unknown | The original blocking risk | The point-forecast path | **B-1** |
| Standalone use | Unknown whether it requires a preceding heatmap for the same point/time | If dependent, every point sample costs a heatmap **plus** an env_params — 2× credits and latency | Z-4's arithmetic | **B-7** |

## 3.3 Supporting surfaces

| Surface | Use | Check |
|---|---|---|
| `GET /v1/status/{activity_id}` | The polling loop: bounded attempts, sleep interval, hard timeout. Also the cheapest route to replay fixtures, since results persist by id | G-2, G-3, G-4 |
| `GET /v1/system/fetch-api-key-usage` | Per-call credit accounting by differencing; the `credits_delta` column in the log schema; the live budget guard that halts the collector before exhaustion | A-3, A-6, A-7 |
| Documented status codes (400/422, 401, 403, 404, 429, 5xx) | Each mapped to an explicit branch; every unhandled case funnels to the fail-safe | H-1…H-8 |

## 3.4 Premium surfaces — deliberately not used, with reasons

| Surface | Why not |
|---|---|
| `satellite` | Satellite imagery answers a land-cover question, not an air-temperature question. Its natural output is **land-surface temperature**, which is the exact category error B-6 exists to prevent — a sunny car park can read 55 °C while the air 2 m above it is 35 °C. Wrong variable. |
| `streetview` | A perception/imagery product. Nothing in the decision path consumes images. Including it would be decoration. |
| `heat_intelligence` | Plausibly relevant, and **explicitly flagged as unexplored**. If it is available on this plan tier it should be examined for a spatial-uncertainty or confidence field — that would compete directly with §7.6's σ and would be *better* than a proxy. Added as check **S-9**. |

*Honest note: §3.4 is the section a judge will test. "Did you look at everything we sell?" The answer
must be yes, with a reason per row — including one row that says "this might be better than what I
built, and here's the check that finds out."*

---

# §4 — Architecture

## 4.1 Component diagram

```
                          ┌──────────────────────── EXTERNAL ────────────────────────┐
                          │                                                          │
                          │  FortyGuard API              NOAA / IEM METAR archive    │
                          │  /v1/heatmap                 (free, real instruments)    │
                          │  /v1/env_params                                          │
                          │  /v1/status/{id}                                         │
                          │  /v1/system/fetch-api-key-usage                          │
                          └────────┬──────────────────────────────┬──────────────────┘
                                   │                              │
                    ┌──────────────▼──────────────┐   ┌───────────▼───────────┐
                    │  api/client.py              │   │  metar/fetch.py       │
                    │  auth · submit · poll       │   │  station history      │
                    │  backoff+jitter · timeout   │   │  T + dewpoint         │
                    │  credit accounting          │   └───────────┬───────────┘
                    │  record/replay fixtures     │               │
                    └──────────────┬──────────────┘               │
                                   │                              │
                    ┌──────────────▼──────────────┐               │
                    │  field.py                   │               │
                    │  tile grid · max · hotspot  │               │
                    │  σ_spatial · sub-polygon    │               │
                    └──────────────┬──────────────┘               │
                                   │                              │
                    ┌──────────────▼──────────────┐               │
                    │  sampler.py    ◀── AGENT    │               │
                    │  coarse 100 m → read σ →    │               │
                    │  decide: refine to 60 m     │               │
                    │  over hot-spot sub-polygon? │               │
                    └──────────────┬──────────────┘               │
                                   │                              │
                    ┌──────────────▼──────────────┐               │
                    │  psychro.py                 │◀──────────────┘
                    │  wet-bulb from T + RH/Td    │   (shared derivation code:
                    │  psychrolib · Stull fallback│    one implementation serves
                    │  pressure correction        │    FortyGuard fallback, METAR,
                    └──────────────┬──────────────┘    and the Earth-2 path)
                                   │
        ══════════════════ DETERMINISTIC DECISION PATH ══════════════════
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │  conformal/                                         │
        │    scores.py    |y−ŷ| · max-over-horizon · /σ       │
        │    split.py     ⌈(n+1)(1−α)⌉-th smallest            │
        │    mondrian.py  strata: σ-tercile × horizon × site  │
        │    aci.py       online α update                     │
        │  → margin (°C)                                      │
        └──────────────────────────┬──────────────────────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │  threshold.py   per-site limit + derivation record  │
        │  decide.py      bound = field_max + margin          │
        │                 bound ≤ threshold ? free : chiller  │
        │                 fail-safe ladder (§6.5)             │
        └──────────────────────────┬──────────────────────────┘
        ══════════════════════════ │ ═══════════════════════════
                                   │  numbers are now FROZEN
        ┌──────────────────────────▼──────────────────────────┐
        │  explain.py     ◀── LLM (local Nemotron)            │
        │  prose for the operator                             │
        │  + numeric grounding assertion: every number in     │
        │    the prose must appear in the frozen decision      │
        └──────────────────────────┬──────────────────────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │  gate.py        HUMAN — approve / reject / override  │
        │                 override requires a reason string    │
        └──────────────────────────┬──────────────────────────┘
                                   │
        ┌──────────────────────────▼──────────────────────────┐
        │  logbook.py     append-only, frozen schema (§15.3)  │
        └──────────────────────────┬──────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  collector.py (hourly cron) │
                    │   job 1: fetch + log forecast│
                    │   job 2: backfill actuals   │
                    ├─────────────────────────────┤
                    │  scorer.py                  │
                    │   join → residuals → feeds  │
                    │   the conformal layer       │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │  backtest/ · experiments/   │
                    │  A1 · A2 · A3 · baselines   │
                    └─────────────────────────────┘
```

## 4.2 The one architectural rule that matters

**The LLM is on the outside of the decision, never inside it.**

Everything between the two double-lines is deterministic arithmetic. Given the same inputs it produces
the same output, and any historical recommendation can be replayed to the identical number. The LLM
sits *after* the decision is frozen (writing the explanation) and, optionally, *before* perception
(as a light orchestrator over sampling depth — see §8.5 for why even that is optional).

State this unprompted under questioning. If the LLM did the arithmetic, the coverage guarantee would be
meaningless and the system unauditable — the entire point of the conformal layer would be discarded.

## 4.3 The loop is closed

`collector` → `logbook` → `scorer` → `conformal` → `decide` → `logbook`. The agent's own output becomes
its own calibration input. That closure is what makes it an agent that learns about *itself* rather
than a stateless recommender — and, not coincidentally, the calibration set and the audit trail are the
same file.

---

# §5 — Every dataset: provenance, use, and trust

The single most important distinction in this project:

- An **observation** came from a physical instrument. Someone's thermometer read a number.
- A **hindcast** is a model's estimate *about the past*, produced after the fact. It looks exactly like
  an observation in a JSON payload and is not one.

Scoring a model against its own hindcast is the system grading its own homework. This table is where
that risk is made unmissable.

| Dataset | Source | Measurement or model? | Used for | Must **never** be used for | Known failure mode | Check |
|---|---|---|---|---|---|---|
| **FortyGuard forecast field** (now→+12 h) | `/v1/heatmap` at issuance | Model | The decision; σ_spatial; the logged prediction | Anything retroactive — it is **unrecoverable after the fact** (§5.2) | May not be a genuine forecast (persistence or climatology dressed as one) | **B-5** |
| **FortyGuard hindcast field** (past hours) | `/v1/heatmap` after the valid time | Model | The "actual" for residuals; A1; the backtest | Being called an observation, in writing or in speech | Self-referential scoring; may be silently revised days later | **K-3, K-5, W-3** |
| **FortyGuard history 2019→2026** | `/v1/heatmap`, historical dates | Model | A1; A2's FortyGuard side; the well-powered H1 pre-test; all baselines | The same | Same as above, plus possible model-version discontinuities over 7 years | W-1, K-5 |
| **METAR observations, multi-station** | NOAA / Iowa Environmental Mesonet archives | **Measurement** — the only one in the project | **(a)** trust check on FortyGuard (W-3); **(b)** the baseline current practice; **(c)** A2's ground truth; **(d)** emergency residual source if K-3 fails | The conformal truth source for the *site* — the airport is a different place (§5.1) | Station outages; sensor drift; dewpoint reported to whole degrees, coarsening derived wet-bulb | W-1, W-2 |
| **Derived wet-bulb** | `psychro.py` from T + RH or T + Td | Computed | The wet-bulb path wherever the API does not supply it; all METAR wet-bulbs | — | Stull's approximation assumes near-sea-level pressure and is valid 5–99 % RH, −20…+50 °C. Site elevations (Phoenix ~340 m, Ashburn ~100 m, Hillsboro ~60 m) are near enough, but psychrolib with real pressure is preferred | **B-8**, W-2, D-4 |
| **GPU load** | **STUB** — DCGM-schema shape | Fabricated, and labelled as such | The interface only; demonstrates where facility telemetry attaches | Any quantitative claim | — | — |
| **Cooling plant state** | **STUB** | Fabricated, labelled | The interface where a real BMS/plant controller would attach | Any claim about actual plant behaviour | — | — |
| **Tower intake conditions** | **STUB** | Fabricated, labelled | The interface for a real intake sensor. Its absence is why recirculation is absorbed into the threshold (§6.3) | Claiming intake conditions were measured | — | — |
| **Facility cost constants** | **STUB** (§1.3) | Placeholders | Cost arithmetic, always reported alongside a sensitivity sweep | A headline number quoted without the sweep | — | §10.5 |
| **The agent's own logbook** | Written by the agent | Mixed — records both model values and its own decisions | The calibration set; the audit trail; the evaluation set; the override signal | — | **A missing column on day 1 is a permanent hole in unrepeatable data** | **Z-3** |

## 5.1 METAR's four jobs, in priority order

Restated identically to the companion documents, because it is easy to get wrong:

1. **Trust check on the truth source (W-3).** The site "actual" is a hindcast from the same model that
   made the forecast. METAR is the only physical measurement anywhere in the project. W-3 confirms
   FortyGuard tracks reality in the right direction and by a physically explicable amount. The two are
   *expected* to differ — that difference is the entire premise. What is being ruled out is a gap that
   distance and physics cannot explain.
2. **The baseline.** "Current practice reads the distant airport station" — that station *is* the
   METAR. Needed regardless, for A2 and for §10's baselines.
3. **Emergency residual source.** If K-3 finds the forecast and the hindcast identical (residuals
   exactly zero), METAR becomes the only remaining source of real residuals. Contingency.
4. **An optional separate spatial bound.** A conformal bound on "how much warmer is the site than the
   station," buildable from history immediately. A good talking point, but it answers a *different*
   question and is not a shortcut for forecast-error calibration.

**METAR is not the conformal layer's truth source.** Conformal prediction must score the agent's
forecast *for the site* against what happens *at the site*. The airport is a different place.

## 5.2 The unrepeatability problem

Retrieving a *past forecast* requires the request to express two independent times — the **valid time**
(what you asked about) and the **issuance time** (when you asked). FortyGuard's documented request
surface has exactly one time concept (`date`, `start_time`/`end_time`, `filter_type`).

A single-time API can only return one series per (point, valid time), and the natural product decision
is "best estimate for that time" — a hindcast. **Therefore there is almost certainly no forecast
archive**, and the verdict follows from the request schema at zero credit cost (**Z-1**), not from an
experiment.

The consequence is the single most time-critical fact in the project:

> The forecast recorded today is **unrecoverable tomorrow.** Query that timestamp after it passes and
> you get the hindcast, not what was predicted. **The log is the only copy that will ever exist.**

This is why **Z-3 (freeze the log schema)** precedes everything, and why the collector starts on day 1
even though nothing consumes its output until week 3.

---

# §6 — The decision logic

## 6.1 The threshold, derived forwards

The threshold is **a chosen, justified modelling assumption, not a physical constant.** Being able to
say where the number came from matters more than the number.

Follow one breath of air through the plant, forwards, with all values as ⚠ stubs for Ashburn:

```
Step 1   Air at the property boundary                        wet-bulb  19.0 °C
              │
              │  + 3.0 K   RECIRCULATION + facility waste heat
              │            The tower re-breathes some of its own warm, saturated
              │            exhaust, and the air crosses a hot campus on the way in.
              ▼
Step 2   Air actually entering the tower                     wet-bulb  22.0 °C
              │
              │  + 4.0 K   APPROACH
              │            Water and air are in contact for seconds, not forever.
              │            The tower lands this far above the floor it is aiming at.
              ▼
Step 3   Water leaving the tower                                       26.0 °C
              │
              ▼
Step 4   Facility loop — can this plant hold setpoint on 26 °C water?   YES, just.
```

At 19.0 °C ambient, the plant *just* copes. At 20.0 °C ambient: 20 → 23 → 27 °C water, and 27 exceeds
what the plant can hold. **So 19.0 °C is the highest ambient wet-bulb that works.**

## 6.2 The same chain, backwards — which is how you compute it

You do not want to try every candidate day. Solve from the finish line:

```
26.0 °C   warmest water this facility can accept          ← the facility engineer supplies this
  − 4.0     approach (a property of THIS tower)
  ------
22.0 °C   warmest intake wet-bulb the tower can work with
  − 3.0     recirculation + campus waste heat (a property of THIS site)
  ------
19.0 °C   warmest AMBIENT wet-bulb we accept   ← THE THRESHOLD, and what the agent can see
```

Both directions use the same three numbers. Forwards you add, because each stage makes things warmer.
Backwards you subtract, because you are undoing them. The requirement gets *stricter* at each backward
step (26 → 19) for the same reason a 9 a.m. meeting means a 8:05 a.m. alarm.

**Why the answer must be a number about air:** the agent can only observe air. A requirement about
water has to be translated into an equivalent requirement about air, once, at design time.

**Why the approach and recirculation numbers are constants:** the approach is a property of the tower
(size, fan power, fill design). Recirculation is a property of the site layout. Neither changes with
the weather, so the arithmetic is done once and baked into a single number. The agent then does
something trivial every hour — *is the bound below 19?* — and knows nothing about towers.

## 6.3 Per-site thresholds, in code

```python
# fgcool/config.py  —  ALL THREE NUMBERS PER SITE ARE ⚠ STUBS.
# A facility engineer supplies them. The DERIVATION is the deliverable; the
# values are placeholders, and §10.5 sweeps them so no result depends on a guess.

SITES = {
    "ashburn": Site(
        # 26.0  warmest supply water this plant can hold (liquid-cooled racks,
        #       warm-water design → higher ceiling than legacy air-cooled)
        # -4.0  approach: this tower's gap above the intake wet-bulb
        # -3.0  recirculation + campus waste heat, ambient → intake
        # -----
        # 19.0
        threshold_c=19.0,
        water_limit_c=26.0, approach_k=4.0, site_loss_k=3.0,
    ),
    "phoenix": Site(
        # 27.0 − 3.5 − 2.5 = 21.0
        # Warmer-water plant design; larger tower (smaller approach); open,
        # well-ventilated site (less recirculation).
        threshold_c=21.0,
        water_limit_c=27.0, approach_k=3.5, site_loss_k=2.5,
    ),
    "hillsboro": Site(
        # 25.0 − 4.5 − 3.0 = 17.5
        # Older plant, tighter water limit; compact site.
        threshold_c=17.5,
        water_limit_c=25.0, approach_k=4.5, site_loss_k=3.0,
    ),
}
```

`threshold_c` is stored *and* recomputed from its three parts on load, with an assertion that they
agree. That prevents the number drifting away from its own justification.

**Sanity anchor:** ENERGY STAR screens waterside-economizer suitability at wet-bulb below 55 °F
(12.8 °C) for 3,000+ hours/year. That figure is for *traditional air-cooled* facilities with much
tighter water limits. Thresholds of 17.5–21 °C are higher, and §1.4 is exactly why. State the anchor
*and* the reason for departing from it — a number that contradicts published guidance without
explanation is a liability.

**Recirculation is absorbed into the threshold rather than measured**, because there is no intake
sensor (the stub in §5). This is the failure mode worth naming out loud: the forecast can be perfectly
correct and the outcome still bad, because the tower breathes worse air than the property boundary
sees. Absorbing a fixed allowance is the honest, conservative response — the same logic as a lift rated
for a 3,000 kg cable carrying a 630 kg placard.

## 6.4 From bound to action: the cost-loss rule

Two inputs: a **one-sided upper bound** on wet-bulb over the window (§7), and the threshold.

```
bound = field_max_over_window + margin
decision = FREE_COOLING  if  bound ≤ threshold
           CHILLERS      otherwise
```

The confidence level α is not chosen because 95 % looks standard. Under the cost-loss model you protect
when the probability of the bad event exceeds **C/L** — the cost of protecting divided by the loss from
being unprotected. From §1.3, C ≈ $157 per hour of unnecessary chiller operation; L is the expected cost
of a thermal excursion, orders of magnitude larger. A small C/L implies protecting at a low probability
of harm, i.e. a **high** confidence bound.

Countervailing pressure: high confidence needs many calibration points. With n_eff ≈ 42 (§7.4),
99 % is not reachable. **Target 90 %, measure the actual coverage, and report the arithmetic honestly**
— including that 90 % means being wrong one hour in ten, which is precisely why the human gate exists.

Additional guard: the bound is one-sided and *upper* only. There is no interest in how cold it might
get. A symmetric interval would waste half its width on the harmless direction.

## 6.5 The fail-safe ladder

Every branch defaults to **chillers**, with a logged reason. Ordered by check:

| # | Condition | Action |
|---|---|---|
| 1 | Any API error after retries exhausted (429, 5xx, timeout, malformed) | CHILLERS, reason `api_unavailable` |
| 2 | Forecast **staleness** — `now − issued_at > 90 min` ⚠ stub | CHILLERS, reason `stale_forecast` |
| 3 | Any required tile value null, or tile coverage below 80 % of expected ⚠ stub | CHILLERS, reason `incomplete_field` |
| 4 | `n_calib` below the conformal minimum for the target α (§7.2) | CHILLERS **or** fall back to the Phase-1 fixed margin — never to a zero margin |
| 5 | Computed margin ≤ 0, or σ_spatial exactly 0 (§12.4) | CHILLERS, reason `degenerate_margin` |
| 6 | Interval width above a usability bound (⚠ stub 5 K) | CHILLERS, reason `uninformative_bound` |
| 7 | Rolling empirical coverage below nominal by more than the CI (§7.7) | CHILLERS + raise a health alarm |
| 8 | Numbers in the LLM explanation do not match the frozen decision | CHILLERS, reason `explanation_ungrounded`, and log both |
| 9 | Credit budget guard would be breached by this run | Skip the run, CHILLERS, reason `budget_guard` |

**Staleness needs an explicit definition**, and it depends on whether an issuance timestamp is
available in the response. If not, the fetch time is a weaker proxy, and per-call — not per-run —
because a multi-minute three-site sample smears the snapshot (**G-6**, **D3.4**).

---

# §7 — The uncertainty layer

FortyGuard publishes a point value with **no uncertainty field** — no confidence, spread, or ensemble
column in any documented response schema. A bare number cannot support a risk-aware decision. This
section builds the missing piece.

## 7.1 Split conformal prediction, stated precisely

**Conformal prediction** turns any point predictor into an interval predictor with a **finite-sample,
distribution-free** coverage guarantee. The mechanism:

1. Hold out a **calibration set** of past cases where both the prediction and the outcome are known.
2. For each, compute a **nonconformity score** — a number measuring how badly it went. For regression,
   typically the absolute residual `s_i = |y_i − ŷ_i|`.
3. Sort the scores. Take the **⌈(n+1)(1−α)⌉-th smallest**.
4. That value is the margin. New prediction ± margin.

The quantile index is not `⌈n(1−α)⌉`. With n = 42 and α = 0.10, `⌈43 × 0.90⌉ = ⌈38.7⌉ = 39` — the 39th
smallest of 42, not the 38th. **The small-sample penalty is built into the formula.** Using the naive
index quietly under-covers, and saying so unprompted is a strong signal of having read the source
rather than a blog post.

The guarantee holds **without** assuming Gaussian errors, **without** assuming the underlying model is
correct, and **for finite samples** — not asymptotically. That is why it is the right tool for wrapping
a third-party black-box forecast.

## 7.2 The minimum sample size

For a one-sided 1−α bound you need `⌈(n+1)(1−α)⌉ ≤ n`, which requires roughly `n ≥ 1/α − 1`:

| Target coverage | Minimum n |
|---|---|
| 90 % | 9 |
| 95 % | 19 |
| 99 % | 99 |

Below the minimum the required quantile index exceeds the number of samples and the interval is
formally infinite. The code must assert this, not discover it (§12.4).

## 7.3 Exchangeability, and why this data violates it

The guarantee requires **exchangeability** — roughly, that the joint distribution of the data is
unchanged by reordering. **Temperature time series flatly violate this.** Today's forecast error
resembles yesterday's; there is diurnal structure and seasonal structure.

This is not a footnote. It is why §7.8 exists. The correct posture: do not cite the theorem as if it
applied cleanly — **measure the coverage empirically and report what was measured.**

## 7.4 Effective sample size — the binding constraint

Naive arithmetic: 14 days × 24 runs = 336 residual pairs per horizon per site; 1,008 across three
sites. **That number is badly misleading.**

Consecutive hourly residuals at a fixed horizon are strongly autocorrelated. One warm-biased day biases
24 consecutive rows in the same direction. Those 24 rows carry roughly **one day's** worth of
independent information.

> **n_eff ≈ site-days, not site-hours.**

14 days × 3 sites ≈ **42 effective samples**, not 1,008.

Two consequences:

1. **The fix is more climates, not more hours.** Errors in Phoenix are close to unrelated to errors in
   Oregon; 24 more hours in Virginia are all telling you approximately the same thing. This is the sole
   reason for three sites in three unrelated climates.
2. **Report n_eff, never the row count.** Quoting 1,008 would be the single most obvious overstatement
   in the project.

## 7.5 Joint coverage over the window

The agent commits for a window, so it needs the bound to hold for **all** hours in it, not each hour
separately. Per-hour marginal coverage is a much weaker promise than joint coverage.

**Bonferroni** would require roughly `1 − 0.10/12 = 99.17 %` per hour → ≥ ~120 *effective* residuals per
horizon (§7.2). With n_eff ≈ 42, **out of reach.**

**The chosen route: a max-over-horizon nonconformity score.**

```python
s_run = max(|y_h − ŷ_h| for h in 1..12)     # ONE residual per collection run
```

Calibrating on this score gives a genuine **joint** bound over the whole window from ~42 effective
samples, instead of a per-hour bound inflated twelvefold. This is the Stankevičiūtė et al. multi-horizon
conformal route.

**Both are logged.** The schema stores the per-hour residuals *and* the per-run max, so per-hour
marginal coverage is reported alongside joint coverage for comparison. Freezing only the max would
foreclose that.

## 7.6 ⭐ The spatially-conditioned score — the central contribution

Everything to this point is standard, and — critically — **provider-agnostic.** It would work
identically on any point forecast. This is where that changes.

### The idea

Replace the plain absolute residual with a **normalised** nonconformity score whose scale comes from
FortyGuard's own spatial field:

```python
sigma = field.stats_data.stddev          # °C, spatial spread across campus tiles, at issuance
s = abs(y - y_hat) / (sigma + EPS)       # EPS = 0.1 °C, guards the degenerate case (§12.4)
```

The calibration quantile is then computed on `s`, and the margin at prediction time is
`q̂ × (sigma_now + EPS)`. **The margin becomes a function of the observed field structure**: wide when
the field is sharply structured, tight when it is smooth.

An equivalent formulation, easier to explain and more robust at small n: **Mondrian (group-conditional)
conformal** — stratify the calibration set into terciles of σ_spatial and compute a separate quantile
per stratum. Both are implemented (`conformal/scores.py`, `conformal/mondrian.py`); §9.3 reports which
wins.

### Why this is the fix rather than a decoration

| | |
|---|---|
| **FortyGuard becomes irreplaceable** | A point API cannot supply spatial heterogeneity. Remove FortyGuard and the *uncertainty layer* loses its input — not merely the forecast. This is the row in §2.5 that no substitute satisfies. |
| **It attacks the project's sharpest known weakness** | Conformal's guarantee is **marginal** (right on average) not **conditional** (right in every situation), and distribution-free conditional coverage is provably impossible in finite samples. Conditioning on a *difficulty signal* is the recognised practical route to partial conditional validity. Conditioning on a **physical** difficulty signal is stronger than conditioning on a statistical proxy. |
| **It is falsifiable** | H1 has a pre-registered pass/fail (§9.3). A null result is reported as a null result. |
| **It converts the weakness into the contribution** | The project's biggest theoretical hole becomes the place where the sponsor's data does work nothing else can. |

### The honest caveats

- **H1 may be false.** §9.3 pre-registers the test *and* the reporting of failure. If σ_spatial does not
  predict residual magnitude, the global conformal layer stands, and the finding — that campus-scale
  spatial structure carries no information about point-forecast error in this field over this window —
  is itself a substantive statement about the data.
- **The live test is underpowered.** n_eff ≈ 42 cannot reliably detect a weak effect. §9.3's mitigation:
  run a **well-powered version first on thousands of historical hours** using persistence residuals,
  then the real version on live forecast residuals. Same pattern as validating the machinery before
  applying it.
- **If no heatmap mode carries wet-bulb (E-8 fails),** σ_spatial is computed on the **dry-bulb** field
  as a documented proxy. Dry-bulb structure and wet-bulb structure are correlated but not identical.
  This must be stated as a proxy, not as the intended quantity.
- **If `heat_intelligence` exposes a real spatial-uncertainty field (S-9),** it is *better than this
  proxy* and should replace it. Checking is cheap; not checking would be indefensible.

## 7.7 Reporting: coverage and width, always together, with error bars

**Coverage alone is gameable.** An infinitely wide interval has 100 % coverage and zero value. Every
result reports both.

And the coverage *estimate* is itself uncertain. At n = 42, a binomial confidence interval on an
observed 90 % coverage is roughly **±10 percentage points**. So "I measured 88 % coverage against a 90 %
target" is not evidence of under-coverage at this sample size — and saying so is more credible than
quoting 88 % as if it were precise. The CI is computed and printed next to every coverage figure.

## 7.8 Adaptive conformal (ACI) — the drift response

Two things break the assumption that old residuals describe current errors: seasonal drift, and the
possibility that FortyGuard silently updates its model. **Adaptive Conformal Inference** treats the
miscoverage level as something to control with a feedback loop — under-covering recently → widen;
over-covering → tighten. Its guarantee is **long-run, not finite-sample**, and it survives arbitrary
distribution shift. That is a different and weaker but more honest promise, and the tradeoff should be
stated as such.

Implemented by hand (≈20 lines), then cross-checked against MAPIE's
`TimeSeriesRegressor(method="aci")`. Rolling empirical coverage is a monitored health metric; a
sustained drop is the signal that something upstream changed, and it triggers fail-safe rung 7.

## 7.9 The full margin ladder, in build order

| Phase | Margin source | Available | Purpose |
|---|---|---|---|
| **0** | None — raw point comparison | Immediately | Proves the pipeline runs. Never demoed as the product |
| **1** | **Fixed conservative margin** (⚠ stub 1.5 K, justified from historical persistence-error spread) | Week 2 | **The safety net.** A complete working agent exists from here on. If everything after fails, the project is still finished |
| **2** | Split conformal, absolute residual, per horizon | Week 3 | The first calibrated bound. Measured coverage |
| **3** | Max-over-horizon score → joint window bound | Week 3 | The guarantee the design actually needs |
| **4** | **σ-normalised / Mondrian on σ_spatial** ⭐ | Week 4 | The contribution. A3 |
| **5** | ACI on top | Week 5 | Drift robustness |

Phase 1 must exist and be committed before Phase 2 begins. This is the non-negotiable "always
demoable" rule (§14).

---

# §8 — The agent loop

## 8.1 Is this really an agent?

Yes, in the perceive–reason–act sense: it runs autonomously on a loop, **chooses its own next action at
runtime based on what it observed**, carries state across iterations, and scores itself against ground
truth.

No, in the sense of open-ended LLM reasoning — and for a system touching physical infrastructure that
is correct engineering, not a limitation. The honest concession: a ReAct-style agent would handle
situations not anticipated more gracefully; this one will do something sensible-but-fixed instead.

What makes the claim defensible is the **action space** (§8.4). Before this revision the only genuine
choice was "sample more points if they disagree," which is thin. Now the agent chooses where to look,
at what resolution, over what horizon, in which mode, and whether to escalate.

## 8.2 The loop

```python
def run_hour(site: Site, now: datetime) -> Decision:      # `now` is INJECTED, never datetime.now()

    # ── 1. PERCEIVE (coarse) ────────────────────────────────────────────
    coarse = heatmap(site.polygon, granularity=100, filter_type=2,
                     start=now, end=now + 12h, mode="tcm")
    sigma  = coarse.stats_data.stddev
    field  = coarse.map_data

    # ── 2. ACT: decide whether to look harder, and WHERE ────────────────
    if sigma > site.refine_sigma_k and budget.allows(REFINE_COST):
        sub  = hotspot_subpolygon(field, pad_m=200)       # ~1/9 of the area
        fine = heatmap(sub, granularity=60, filter_type=2,
                       start=now, end=now + 12h, mode="tcm")
        field = merge(field, fine)                        # fine values win where they overlap
        sigma = max(sigma, fine.stats_data.stddev)

    # ── 3. DERIVE ───────────────────────────────────────────────────────
    wb = wet_bulb_field(field, site)     # native if E-8 passes, else psychrolib per tile

    # ── 4. BOUND ────────────────────────────────────────────────────────
    point  = wb.max_over_window()                          # hottest tile, worst hour
    margin = conformal.margin(site, horizon=12, sigma=sigma, alpha=0.10)
    bound  = point + margin

    # ── 5. DECIDE (deterministic; nothing below may change these numbers)
    decision = decide(bound, site.threshold_c, checks=FAILSAFE_LADDER)

    # ── 6. EXPLAIN (LLM, after the numbers are frozen) ──────────────────
    prose = explain(decision, wb, sigma, margin)
    assert numbers_in(prose) <= numbers_of(decision), "explanation_ungrounded"

    # ── 7. HUMAN GATE (non-removable) ──────────────────────────────────
    action, reason = gate.present(decision, prose)         # approve | reject | override+reason

    # ── 8. LOG (frozen schema; the only copy that will ever exist) ─────
    logbook.append(row_from(site, now, coarse, fine, wb, sigma,
                            margin, bound, decision, prose, action, reason))
    return decision
```

Job 2 of the collector, on the same cron tick, backfills actuals for hours that have now passed and
appends them to a **separate** table so revisions are visible (K-5).

## 8.3 Coarse-to-fine refinement — the agentic core

Why this is real rather than cosmetic:

- **It is a genuine decision** made from an observation (`sigma`) that is unavailable until after the
  first call, with a real cost attached (credits and latency).
- **It reduces spend.** A naive design requests 60 m over the whole campus every hour. This one
  requests 100 m always and 60 m over roughly a ninth of the area only when the field warrants it. On
  smooth days it costs strictly less than the naive design.
- **It is the right physical response.** Fine resolution is worth paying for where gradients exist and
  worthless where the field is flat.
- **It produces the conditioning variable for free** — `stats_data` from the coarse pass is exactly
  what §7.6 needs, so the perception step and the uncertainty step share one call.

Verified by **S-8** (does refinement over a sub-polygon return a grid consistent with the parent — see
§12.2's tile-alignment edge case).

## 8.4 The action space

| Action | Chosen from | Bounded by |
|---|---|---|
| Granularity: 100 m or refine to 60 m | σ_spatial from the coarse pass | Credit budget guard |
| Sub-polygon to refine | Hot-spot location in the field | Minimum polygon size (E-5) |
| Horizon depth: full 12 h or short | Whether the near hours already breach | Committed window is 12 h |
| Mode: `tcm` vs `exceedance` vs `persistence` | Whether the question is "how hot" or "how long" | Mode availability (F-1) |
| Escalate to human vs auto-recommend | Bound margin against threshold; fail-safe rungs | Gate is never skippable |
| Sample count for the point cross-check | Field disagreement | 3-parameter cap |

## 8.5 Where the LLM sits, and why no framework

**The LLM does three things:** writes the operator explanation; summarises field disagreement into
prose; optionally nudges sampling depth. **It never touches the arithmetic.**

**No LangChain / LangGraph / CrewAI / AutoGen.** The reason is not aesthetic. Those frameworks exist to
orchestrate an LLM that *chooses its own actions from a large space*. Here the action space is small,
known, and enumerated in §8.4, and the consequential choice (`sigma > threshold`) is a numeric
comparison. A framework would add abstraction layers, nondeterminism, and dependency surface to a
control-path system that must be auditable and replayable. The loop above is the loop; it is a few
hundred lines of plain Python with `requests` and `tenacity`.

"No framework" ≠ "from scratch." `requests`, `tenacity`, `psychrolib`, `mapie` (for cross-checking) are
all in use. If a middle ground were ever wanted, the Anthropic SDK's `client.beta.messages.tool_runner()`
supplies a tool loop without a framework — noted for completeness, not planned.

---

# §9 — The three headline artifacts

## 9.1 A1 — The free-cooling-hours map

**The claim.** Two points on a *single campus* differ by hundreds of free-cooling hours per year, and no
station network can see it.

**Method.**
1. For each site polygon, run historical `exceedance` heatmaps with `direction: below` and
   `threshold` = the site's wet-bulb limit, sweeping 2019-01-01 → present.
2. If `exceedance` cannot operate on wet-bulb (E-8/F-2), fall back to per-tile counting from `tcm`
   fields plus derived wet-bulb — more calls, same output, and §11.1's budget governs the sweep density.
3. Produce, per tile: annual hours below threshold, averaged over years and per-year for trend.

**Report.**
- A choropleth per campus at 60 m.
- The **intra-campus spread**: `max_tile_hours − min_tile_hours`, in hours/year and in dollars via §1.3.
- The **airport comparison**: hours/year at the nearest METAR station location vs. hours/year at the
  campus's own tiles. The gap is current practice's blind spot, quantified.
- Per-year values, so a reader can see whether the field is stable or the model changed.

**Why it lands.** It is a single image that makes the thesis obvious, it needs no waiting, and it is
literally unproducible from a station network.

**Honest caveat.** These are hindcast hours, not measured hours. A1 says "FortyGuard's field implies
this spread." A2 is what establishes that the field deserves that trust.

## 9.2 A2 — Leave-one-station-out skill test

**The claim.** FortyGuard's field predicts conditions at a location better than the standard practice
of interpolating nearby stations — **measured against real instruments.**

**Why this matters more than any other test in the project.** Every other accuracy statement scores
FortyGuard against FortyGuard's own hindcast. This one scores it against physical thermometers, and it
is the only test that escapes the self-grading problem entirely.

**Stations** (⚠ to be confirmed for history coverage in W-1):

| Metro | Stations |
|---|---|
| Ashburn VA | KIAD, KJYO, KHEF, KDCA |
| Phoenix AZ | KPHX, KGYR, KDVT, KSDL |
| Hillsboro OR | KHIO, KPDX, KTTD |

**Protocol**, for each held-out station X, each hour, over a multi-year window:

1. Derive X's true wet-bulb from its reported dry-bulb + dewpoint via `psychro.py` (validated in B-8/W-2).
2. **Competitor 1 — nearest-station copy.** The value at the nearest *remaining* station. This is what
   current practice literally does.
3. **Competitor 2 — inverse-distance weighting** (power 2) over all remaining stations.
4. **Competitor 3 — IDW with an elevation lapse adjustment.** The strongest cheap baseline.
5. **FortyGuard** at X's exact coordinates.
6. Score all four against X's measurement: MAE, bias, and the 95th percentile of absolute error (the
   tail is what matters for a safety decision).

**Stratify** by hour-of-day (the heat island peaks at night), by season, and by wind speed (heat-island
signal is strongest on calm nights). An aggregate number would hide the effect.

**Pre-registered pass condition.** FortyGuard must beat nearest-station-copy by **≥ 0.5 °C MAE**.
Beating IDW is the stronger claim and the headline if achieved.

**The caveat that must be stated, because it is the honest reading.** Airport stations sit in open grass
fields *by design*. So A2 measures FortyGuard's skill at **airport-like locations**, not at urban
campuses. If FortyGuard's advantage comes from resolving built environments, this test **understates**
it — the hardest cases for the interpolation baselines (dense urban tiles) contain no stations to score
against. A2 is therefore a **lower bound** on the hyperlocal advantage. Saying this before being asked
is worth more than the number.

**This also settles V6.2** — "is FortyGuard just interpolating those same stations?" If it were, it
would tie the interpolation rather than beat it.

## 9.3 A3 — The H1 experiment and the coverage table

**The hypothesis.** Forecast error is larger when the campus thermal field is sharply structured than
when it is smooth.

**Feature.** `sigma = stats_data.stddev` over the campus field at issuance, per run. If E-8 fails,
computed on the dry-bulb field and reported as a proxy.

### Stage 1 — the well-powered pre-test (historical, thousands of hours)

n_eff ≈ 42 cannot detect a weak effect. So test the *mechanism* first where data is abundant:

1. Over the historical record, build a **persistence forecast** — "conditions at hour T equal
   conditions now" — for each horizon. This is a genuine predictor with genuine, computable residuals,
   available for every hour since 2019.
2. Compute σ_spatial for the same hours from historical fields.
3. Test the association across thousands of hours.

If the effect is present here, it is strong prior evidence and Stage 2 becomes confirmation rather than
discovery. If absent here with thousands of samples, H1 is very likely false and §7.6 should be reported
as an attempted-and-rejected idea — which is a legitimate result, not a failure of the project.

### Stage 2 — the live test (forecast residuals, n_eff ≈ 42)

Same analysis on the collector's real forecast residuals, using the max-over-horizon score.

### Pre-registered statistics — written down before looking

| | |
|---|---|
| **Primary test** | Spearman rank correlation between σ_spatial and \|residual\| across runs |
| **Significance** | ρ > 0.20 with p < 0.05 |
| **Practical significance** | The top σ-tercile's 90th-percentile residual exceeds the bottom tercile's by **≥ 0.3 °C**. Statistical significance alone is not enough — the effect must be large enough to change a margin |
| **Failure reporting** | If either fails: the global conformal layer stands, §7.6 is reported as tested-and-not-supported, and the observed ρ and tercile gap are printed with their CIs. **No quiet removal.** |

### The deliverable table

| Configuration | Nominal | Empirical coverage (±CI) | Mean width (°C) | Coverage in top σ-tercile | Coverage in bottom σ-tercile |
|---|---|---|---|---|---|
| Phase 1 — fixed 1.5 K margin | — | | | | |
| Phase 2 — split conformal, per horizon | 90 % | | | | |
| Phase 3 — max-over-horizon (joint) | 90 % | | | | |
| **Phase 4 — σ-normalised** ⭐ | 90 % | | | | |
| **Phase 4b — Mondrian on σ-tercile** ⭐ | 90 % | | | | |
| Phase 5 — ACI | 90 % (long-run) | | | | |

**Win condition for §7.6:** coverage at or above nominal **and** mean width smaller than Phase 3; *or*
equal width with **more uniform coverage across the σ-terciles**. That second criterion is the one that
matters — it is literally partial conditional coverage, which is the theoretical prize.

The last two columns are the entire point. If global conformal over-covers on smooth days and
under-covers on structured ones, and the σ-conditioned version evens that out, the contribution is
demonstrated numerically.

---

# §10 — Evaluation protocol

## 10.1 The three baselines

Named and non-negotiable. "It seems to work" fails here.

| # | Baseline | What beating it proves |
|---|---|---|
| **B0** | **Always chillers.** Safe, expensive, the status quo. | That the system saves money at all |
| **B1** | **Reactive threshold.** Free-cool whenever *current* wet-bulb is below threshold, no forecast. | That **forecasting** adds value over reacting |
| **B2** | **Persistence forecast.** Assume conditions hold. The standard, surprisingly strong meteorological baseline. | That **FortyGuard's forecast** adds value over "nothing changes" |
| **B3** | **Airport-station-driven decision.** B1/B2 but reading the nearest METAR instead of the site. | That **hyperlocal** adds value. This is the project's actual claim, and it is a distinct baseline from B1/B2 |

B3 is the one most projects omit. It is the baseline that corresponds to what the industry actually
does, and it must be beaten for the thesis to hold.

## 10.2 Walk-forward validation

Random train/test splits are **invalid** for time series — they leak future information into past
predictions. Evaluation is forward-chaining: calibrate on data strictly before time T, evaluate at T,
advance. Implemented in `backtest/harness.py`; cross-checked against
`sklearn.model_selection.TimeSeriesSplit` semantics.

An expert will probe this. The reason matters more than the mechanism: a conformal margin fitted on
residuals that include the hour being predicted is not a margin, it is a fit.

## 10.3 Metrics

| Metric | Why |
|---|---|
| Empirical vs. nominal coverage, **with CI** | Does the 90 % bound actually hold 90 % of the time |
| Mean and 90th-percentile interval width | Coverage alone is gameable |
| Coverage sliced by σ-tercile, hour-of-day, season, site | Marginal coverage can hide bad conditional coverage exactly where the decision matters |
| Simulated cost vs. each baseline | The decision-level metric, in dollars, via §1.3 |
| **Threshold violations counted separately** | The asymmetric failure. Never averaged into a cost figure |
| Free-cooling hours recommended and accepted | The operational quantity |
| **Operator override rate, and override direction** | A second, independent evaluation signal (§10.4) |
| n_eff, printed everywhere a coverage number is printed | Prevents the row-count overstatement |

## 10.4 The operator gate as an evaluation instrument

The human gate is a safety requirement first. But every override is a labelled disagreement between the
agent and a human, with a reason string. Aggregated, that gives:

- an override rate — a usability metric no purely numeric evaluation captures;
- override *direction* — are humans overriding toward caution (the agent is too aggressive) or toward
  free cooling (the agent is too conservative, i.e. the margin is too wide)?
- the reason strings themselves, which are the closest thing available to domain feedback.

For the hackathon the "operator" is the developer, and that must be stated plainly — it demonstrates the
mechanism, not real operator behaviour.

## 10.5 The sensitivity sweep — required, not optional

Every ⚠ stub in §1.3 and §6.3 is a guess. Any headline conclusion that depends on a guess is fragile.
So the entire evaluation runs across a sweep:

- **Threshold:** 15.0 → 23.0 °C in 0.5 K steps, per site.
- **Cost constants:** chiller kW/ton 0.6–1.0; free-cooling kW/ton 0.15–0.25; $/kWh 0.05–0.15.
- **Target coverage:** α ∈ {0.05, 0.10, 0.20}.

Report the conclusion *as a function of* the threshold, not at one value. This converts the weakest
assumption in the project into a demonstration of rigour: *"my conclusion holds across the entire
plausible range, and here is where it stops holding."*

## 10.6 The limitation to state first

There is no real facility. This evaluates a **recommender in simulation against historical data**.
Actual thermal outcomes, real operator behaviour, and plant dynamics are not measured. That is the gap
between this and a deployed system, and naming it unprompted is worth more than any feature.

---

# §11 — Bottlenecks, ranked

Each with: symptom · detection · mitigation · **numeric decision trigger**.

## 11.1 Heatmap credit cost — the #1 risk to the whole revision

**Symptom.** The spatial design is affordable at point-query prices and possibly not at field prices.
Every one of R1/R3/R4 depends on this.

**Detection.** **A-3** and **S-1**: read credits → one call → poll to `Completed` → read credits again.
Repeat per configuration (granularity × filter_type × area × mode). Credits are deducted only on
`Completed`, and rejected requests are not charged, so measurement is cheap.

**Budget arithmetic.** Available: 1,000,000 credits ⚠ (confirm the pool is monthly-reset and not a
one-time allocation — **A-7**).

```
Daily collector calls, per site:
   1  coarse heatmap, granularity 100, filter_type 2, 12 h in ONE call
 0.4  fine refinement (only when σ warrants it — empirically ~40 % of hours ⚠ estimate)
   1  actuals backfill (single hour, filter_type 1)
 ----
 2.4  calls / site / hour   ×  3 sites  ×  24 h  =  ~173 calls / day
                                        ×  30 days  =  ~5,200 calls

Maximum affordable per-call cost, reserving 40 % of the pool for
experiments (A1's historical sweep is the large consumer):
        600,000 / 5,200  ≈  115 credits / call
```

**Mitigation levers, in order of power:**

| Lever | Saving |
|---|---|
| `filter_type = 2` — 12 hours in one call, not twelve | **~12×** |
| Campus polygons ~0.1–0.5 mi², not the 10 mi² cap | Large, if cost scales with area |
| Coarse-first: 100 m always, 60 m over ~1/9 of the area only when σ warrants | ~3–5× vs. naive 60 m everywhere |
| `stats_data` for σ without parsing full `map_data` | Bandwidth and parse cost, not credits |
| Cache and re-read by `activity_id` | Free re-reads; also the fixture source |
| Coarsen A1's historical sweep (sample days, not all days) | Tunable; **must be logged as a stated cap, not silently applied** |

**Decision triggers.**

| If measured cost | Then |
|---|---|
| ≤ 115 credits/call | Proceed as designed |
| 115–300 | Drop the fine-refinement pass to σ > 90th percentile only; sample A1's history weekly rather than daily |
| 300–1,000 | Granularity 100 m only; A1 sampled monthly; **σ_spatial still available** — R1 survives |
| > 1,000 | Field perception becomes **twice daily** rather than hourly; the point path (`env_params`) carries the hourly decision and the field carries σ. **R1 survives; R4 does not.** Document the degradation |

Note the shape of that ladder: **it is ordered so that R1 — the contribution — is the last thing to be
cut.**

## 11.2 Heatmap latency vs. the hourly cycle

**Symptom.** Three sites × (coarse + maybe fine + backfill) must complete well inside an hour, or the
"hourly snapshot" is not a snapshot.

**Detection.** **G-1** (now B-CODE): time submit→`Completed` for a small heatmap, a large heatmap at
granularity 60, a single-hour `env_params`, and a 12-hour `env_params`.

**Mitigation.** Parallel submission across sites (**G-5**); submit all three coarse passes before
polling any; skip refinement when the clock is short; **log issuance time per call, not per run**
(**G-6**) so a smeared snapshot is visible in the data rather than hidden.

**Trigger.** If a full run exceeds 20 minutes, drop to sequential-coarse-only and record that the run is
not simultaneous across sites — because pooling residuals across sites (K-8) assumes comparable
issuance conditions.

## 11.3 Does any heatmap mode carry wet-bulb?

**Symptom.** If tiles carry only dry-bulb, spatial wet-bulb requires one `env_params` per tile —
completely infeasible at hundreds of tiles.

**Detection.** **E-8** and **F-1**.

**Mitigation.** Dry-bulb field + humidity field + **per-tile psychrolib** (two heatmaps, then local
computation — cheap and fully under our control). σ_spatial then computed on the dry-bulb field as a
**documented proxy**, with the caveat stated wherever it appears.

**Trigger.** If neither a wet-bulb mode nor a humidity field exists: the per-tile wet-bulb field is
impossible. Fall back to (a) `env_params` at the hot spot for the decision value, (b) dry-bulb σ as the
conditioning proxy. R1 survives in proxy form; the "spatial wet-bulb field" claim must be dropped from
all writing.

## 11.4 Is the +12 h value a genuine forecast? (B-5)

**Symptom.** The API might return persistence-of-now or climatology for future times. Passing **B-1**
(it accepts a future timestamp) does **not** establish this.

**Detection.** **B-5.** Query the same valid time from two issuance times hours apart and check the
values differ in a way persistence cannot explain; compare a +12 h value against the current value and
against a climatological mean for that hour.

**Consequence if it fails.** Not fatal but reframing: the project becomes "a calibrated decision system
over a *nowcast* field," the 12-hour window claim must be withdrawn or restated, and — importantly —
**a server-side `exceedance` count derived from a fake forecast is a fake count**, so R3's forward-
looking use collapses while its historical use (A1) survives untouched.

## 11.5 Zero-residual collapse (K-3) — the most dangerous silent failure

**Symptom.** If the API serves one consistent model field regardless of when it is asked, the forecast
for T equals the later hindcast for T. Residuals are **exactly zero**. The conformal interval collapses
to zero width. The agent becomes maximally overconfident precisely where it must be most conservative —
and it presents as *"my forecasts are perfect."*

**Detection.** An explicit assertion in the collector from day 1, not a check run once: if the
distribution of residuals has near-zero spread, halt and alarm.

**Mitigation.** METAR becomes the residual source (§5.1 job 3) — imperfect, because it blends forecast
error with the site-vs-station gap, but real. The Phase-1 fixed margin remains the floor.

**Trigger.** Median absolute residual < 0.05 °C over ≥ 24 runs → treat the temporal calibration set as
empty and switch to the METAR-based path, with the substitution stated in the writeup.

## 11.6 Effective sample size

**Symptom.** 42 effective samples is enough for a one-sided 90 % bound and not much more.

**Mitigation.** Three unrelated climates (already locked); the max-over-horizon score (§7.5) so joint
coverage is reachable; the historical pre-test (§9.3 Stage 1) to validate the machinery on abundant
data before applying it to scarce data; CIs on every coverage figure.

**Trigger.** If K-8 finds per-site residual distributions too dissimilar to pool, report per-site
coverage separately and accept n_eff ≈ 14 per site — which means 90 % is the ceiling and 95 % must not
be claimed.

## 11.7 The hindcast truth source

**Symptom.** Coverage is measured against the API's own later estimate. Self-referential.

**Mitigation.** **W-3** verifies the truth source against real station measurements. **A2** (§9.2) gives
the value claim an instrument-grounded footing that does not depend on the hindcast at all. And the
writeup states plainly: *"coverage is measured against the API's own later estimate, validated against
station observations."*

**Trigger.** If W-3 finds a gap that distance and physics cannot explain, the hindcast is unusable as
truth and the project pivots to METAR-based residuals entirely.

## 11.8 `env_params` standalone or heatmap-dependent (B-7)

The docs say `env_params`' date/time *"should match the heatmap you generated for the same location and
time."* If it is genuinely stage 2 of a two-call workflow, every point sample costs a heatmap **plus**
an `env_params` — 2× credits and latency, and §11.1's arithmetic changes. Since the revision makes the
heatmap primary anyway, this hurts far less than it would have before: A2's per-station queries are the
main exposure.

## 11.9 Tile payload size at campus scale

A 0.5 mi² polygon at 60 m granularity is roughly 360 tiles ⚠ (estimate; **S-2** measures it). Times 12
hours, times 3 sites, times 24 runs/day — that is a meaningful volume of JSON to parse, store, and
back up. Mitigation: store `stats_data` plus the hot-spot tile and a downsampled field in the hot log;
archive full `map_data` separately, keyed by `activity_id`, and re-fetch on demand.

## 11.10 Solo-developer time

The largest risk not on any API's side. Mitigations: the Phase-1 safety net (§7.9) so a complete project
exists in week 2; A1 and A2 needing no waiting so results exist in week 1; the explicit cut order in
§14.4.

---

# §12 — Edge cases

## 12.1 Time

| Case | Behaviour required | Check |
|---|---|---|
| Three timezones: ET, MST, PT | **Store UTC internally, convert only for display.** No local time in the log except as a derived display column | C-1, O7.6 |
| **Arizona does not observe DST** | Phoenix's UTC offset is constant while the other two shift. Hardcoding a single offset breaks two sites for half the year | C-10 |
| The nonexistent local hour at the spring transition | Never construct a local timestamp and convert; go UTC → local only for display | C-10 |
| The repeated local hour at the autumn transition | Same. A naive local-time key produces **two rows with the same key** and silently corrupts the join | C-10 |
| Window crosses midnight | The 12 h window routinely spans two dates; `filter_type=2` and `filter_type=3` behave differently here | C-6, C-8 |
| Window spans past and future | Does one call accept `now − 2h` → `now + 10h`? | C-8 |
| Clock skew between laptop and API's "now" | If the local clock is ahead, a "future" request may be a past one. Read the API's notion of now and log the delta | C-11 |
| **Hourly mean vs. instantaneous value** | An hourly *mean* hides a sub-hourly spike. A safety decision needs the peak. If values are means, the threshold must absorb an extra allowance | C-9, D3.5 |
| Laptop sleeps and misses hours | Detect gaps at startup and backfill what is recoverable — noting the *forecast* is not recoverable (§5.2), only the actual | §15.4 |
| Collector double-runs (cron overlap) | Idempotency: one row per (site, issued_at, valid_at) enforced by a unique key; a second run updates nothing | §15.3 |
| Leap second / 25-hour day | Treat as a data gap rather than special-casing | — |

## 12.2 Space

| Case | Behaviour required | Check |
|---|---|---|
| Polygon extends over water | Tiles may be null or physically meaningless. Clip the polygon to land, or filter tiles by validity | D-1 |
| Polygon crosses a state or coverage boundary | Partial results. Must fail loudly, not silently return a partial field labelled complete | H-3 |
| Point outside US coverage | Loud failure required, never silent garbage | H-3, O7.4 |
| Polygon exceeds the area cap | Documented failure vs. silent truncation | E-6 |
| Degenerate tiny polygon (below the minimum) | Find the minimum; the refinement sub-polygon in §8.3 must stay above it | E-5 |
| **Tile grid shifts between calls** | If the grid is anchored to the request rather than a global lattice, the same physical location falls in different tiles across hours — **which would corrupt any per-tile time series, including A1.** Detect by comparing tile centroids across two identical requests | **S-8, E-1** |
| Refinement grid does not nest inside the parent grid | Merging fine into coarse needs a defined rule. Fine wins on overlap; conflicts logged | S-8 |
| **A point query snaps to a coarser cell** | If a 60 m request resolves to a 500 m cell, the hyperlocal claim is smaller than advertised. Test by walking separation 20/70/150/500 m/2 km and finding where values start to differ | **E-7** |
| Hot spot on the polygon edge | The refinement sub-polygon must be padded and clipped to the parent, not allowed to extend outside the site | §8.2 |

## 12.3 Data semantics

| Case | Behaviour required | Check |
|---|---|---|
| **Land-surface temperature instead of 2 m air temperature** | A ~20 °C category error. A sunny car park reads 55 °C while the air above it is 35 °C. Detect by comparing a paved tile to a vegetated tile at solar noon vs. pre-dawn — LST diverges enormously, air temperature far less | **B-6** |
| **WBGT instead of psychrometric wet-bulb** | A different quantity entirely. B-8's three-way agreement rules it out | **B-8** |
| Nulls indistinguishable from failures | Must be separable, or a null is silently treated as a value | D-1 |
| **Past values silently revised days later** | A nightly reanalysis would change the "actual" after residuals were computed. Re-query the same past hour at T+1 h, T+1 day, T+7 days | **I-1, K-5** |
| Actual for hour T not available promptly after T | An assimilation lag sets the backfill cadence. If the actual for 14:00 is not available until 20:00, the collector's job 2 must lag accordingly | **K-4** |
| Relative humidity reported ≥ 100 % | Physically possible in reports; psychrolib may raise. Clamp to 100 %, log the clamp | B-8 |
| Derived wet-bulb exceeds dry-bulb | Physically impossible. Assert; on violation, discard the sample and alarm | B-8 |
| Dewpoint reported to whole degrees | METAR often is. Coarsens derived wet-bulb by up to ~0.3 °C — a real floor on A2's resolution, and it must be stated | W-2 |
| Elevation wrong or missing | Pressure correction fails. Stull assumes near-sea-level; site elevations are 60–340 m so the error is small, but confirm | D-4 |
| **Wind direction unavailable** | Then "upwind sampling" is a **fabricated capability** and the language must change to a fixed compass rosette | **D-6** |
| Model-version discontinuity across 7 years of history | A1's per-year values would show a step. Report per-year, don't only average | K-5 |

## 12.4 Numeric and statistical

| Case | Behaviour required |
|---|---|
| **σ_spatial exactly 0** (perfectly uniform field, or a single-tile polygon) | The normalised score divides by zero. `EPS = 0.1 °C` floor, **and** a separate branch: if σ = 0 on a multi-tile field, that is suspicious — log it and use the global margin, not the normalised one |
| Single-tile polygon | σ is undefined, not zero. Refuse and fall back to the global margin |
| **n_calib below the conformal minimum** (§7.2) | `⌈(n+1)(1−α)⌉ > n` → the interval is formally infinite. **Assert at startup**, do not discover at runtime. Fall back to the Phase-1 fixed margin, never to zero |
| All residuals identical | The quantile is that value. Valid but suspicious — cross-check against the K-3 zero-residual alarm |
| **Computed margin ≤ 0** | Impossible for an absolute-residual score; if it happens, there is a sign bug. Assert and fail safe |
| Bound exactly equals the threshold | Define the comparison as `bound ≤ threshold` → free cooling, and **write the tie-break down**. Undefined ties become irreproducible decisions |
| Margin larger than the whole plausible range of wet-bulb | Fail-safe rung 6: uninformative bound |
| Residual distribution heavily skewed | Absolute-residual scores assume symmetry; a **one-sided** score `(y − ŷ)` is more appropriate for an upper bound and should be reported alongside |
| Bound below threshold at hour 1, above at hour 12 | The max-over-horizon score already handles this — the window fails as a whole. But **also** report the longest safe *prefix*, since `persistence` mode gives exactly that and it is more useful to an operator than a flat no |
| Coverage computed on fewer than the minimum samples | Refuse to print a coverage number; print n_eff and "insufficient" |

## 12.5 Operational

| Case | Behaviour required | Check |
|---|---|---|
| 429 rate limited | Exponential backoff **with jitter** — without jitter, retries synchronise across three parallel site jobs and hammer the server | H-6 |
| 5xx | Retry with backoff; after budget exhausted, fail safe | H-7 |
| `activity_id` 404 immediately after submit | Documented behaviour. The poller must tolerate an initial 404 window rather than treating it as failure | **G-2** |
| Job stuck in `Processing` forever | Bounded polling: max attempts × interval, then hard timeout → fail safe | G-3 |
| Credits exhausted mid-run | The budget guard checks before submitting, not after. Partial runs are logged as partial | A-6, §11.1 |
| Partial run — 2 of 3 sites succeeded | Log per-site status. **Never** impute a missing site. Pooling (K-8) must exclude incomplete runs |
| Malformed / unexpected JSON shape | Schema-validate every response; an unrecognised shape is a failure, not something to `.get()` around | H-1 |
| An undocumented daily or concurrency quota | Would break a 24/7 three-site collector days in. Watch for it explicitly | **A-6** |
| Replay mode with a mismatched `now` | **A forecast fixture is only valid for its issuance time.** Replaying it against a different `now` produces a nonsense horizon. `now` is injected and asserted against the fixture's issuance time | **O7.3** |
| Log schema change mid-collection | `schema_version` column from row 1; migrations are additive only, never in place | Z-3 |

## 12.6 Decision-level

| Case | Behaviour required |
|---|---|
| Operator overrides toward free cooling against the recommendation | Record it, act on the human's decision (they are accountable), and count it in §10.4's override statistics |
| Operator overrides toward chillers | Same. Direction is the informative part |
| Operator never responds | Timeout → the fail-safe default (chillers) stands. Silence must not become implicit approval |
| The recommendation flips every hour | Add hysteresis, and be explicit that this is a **stub for real plant dynamics**, not a modelled switching cost |
| The bound is below threshold but σ is enormous | Fail-safe rung 6 catches it via width. This is exactly the case §7.6 exists to handle correctly |
| Threshold changes mid-experiment | Re-derive, re-run, and version the threshold in the log. Never compare results across threshold versions |

---

# §13 — Risk register

| Risk | Detection | Kill criterion | Fallback |
|---|---|---|---|
| No forecast archive | **Z-1**, zero cost | Assumed true unless disproven | Collect live from day 1. **Already the plan** |
| Heatmap cost prohibitive | **A-3, S-1** | > 1,000 credits/call | §11.1's ladder; field perception drops to twice daily; **R1 survives** |
| No mode carries wet-bulb | **E-8, F-1** | Neither wet-bulb nor a humidity field | Dry-bulb σ as documented proxy; `env_params` at the hot spot for the decision value |
| `exceedance` cannot use a future range | **F-2, S-4** | Rejects `direction: below` on future dates | Compute exceedance client-side from `tcm` fields. Same output, more calls. **A1 unaffected** (it is historical) |
| `+12 h` is not a real forecast | **B-5** | Values match persistence within noise | Reframe as a calibrated nowcast system; withdraw the 12 h claim; R3's forward use collapses, A1 survives |
| Zero residuals | **K-3**, day 1 assertion | Median \|residual\| < 0.05 °C over 24 runs | METAR-based residuals (§5.1 job 3) |
| **H1 false** | **§9.3 Stage 1**, historical, well-powered | ρ ≤ 0.20 or tercile gap < 0.3 °C | Report the null; global conformal stands; the project keeps A1, A2, R3, R4 |
| Truth source untrustworthy | **W-3** | Gap unexplainable by distance and physics | METAR-based residuals entirely |
| Latency too high | **G-1** | Full run > 20 min | Parallel submit; coarse only; log non-simultaneity |
| Tile grid unstable across calls | **S-8, E-1** | Centroids differ between identical requests | Snap tiles to a locally-defined lattice and aggregate; A1 becomes coarser but survives |
| Cross-site pooling invalid | **K-8** | Per-site residual distributions materially different | Per-site coverage; n_eff ≈ 14 each; **90 % is then the ceiling** |
| Time runs out | Weekly self-check | Phase 4 not started by day 24 | §14.4's cut order |

**The shape of this table is the point:** every row's fallback preserves at least one headline artifact,
and the ladder in §11.1 is ordered so R1 is cut last.

---

# §14 — Schedule

Invariant, above everything: **a working end-to-end agent must exist before anything sophisticated is
attempted.** Ugly is fine. This is the safety net — if every subsequent week fails, the project is
still finished.

## 14.1 Day 0 — zero credits, no API key needed

| # | Action |
|---|---|
| 1 | **Z-1** request-schema audit → the forecast-archive verdict, free |
| 2 | **Z-2** exact coordinates for three sites + the full station list per metro, with distances and history coverage. *A site 2 km from its station has no gap to demonstrate* |
| 3 | **Z-3 ⚠ FREEZE THE LOG SCHEMA** (§15.3). The one irreversible decision |
| 4 | **Z-4** credit-budget arithmetic, rewritten around heatmaps (§11.1) |
| 5 | **W-1, W-2** pull METAR history; write and validate `psychro.py` — the same code B-8 needs |
| 6 | **W-6** run A2's leave-one-station-out on the *interpolation baselines only* — no FortyGuard needed yet. Establishes the bar FortyGuard must clear, before spending a credit |

## 14.2 Day 1

**Morning — the make-or-break checks.** A-1 auth → A-2 plan tier → **A-3 + S-1 cost per call per
configuration** → A-7 credit window → **B-1** future timestamps → **B-5 is it really a forecast** →
B-4 the `temperature` input → B-7 standalone → **B-8** psychrolib three-way → **B-6** air vs.
land-surface → **E-8 / F-1** does any mode carry wet-bulb → **S-7** does `filter_type=2` cover 12 h in
one call → C-2 time step → C-1 timezone → B-2 horizon ladder → **K-4** actuals lag → **G-1** latency.

> **⚠ GATE — do not start the collector until Z-3 and Z-4 are done and B-1/B-5 have answers.**
> Everything the collector writes is unrepeatable. Starting with the wrong schema is worse than
> starting six hours later.

**Afternoon.** Start the collector. **This is the most time-critical action in the project — every hour
not collected is gone forever.** Then W-3 (truth check, free), G-2/G-3 (polling behaviour).

## 14.3 Weeks

| Week | Deliverable | Why here |
|---|---|---|
| **1** | **A1 and A2 complete.** The historical free-cooling-hours map and the leave-one-station-out result. Plus: the API client with retries/backoff/timeouts/credit accounting, and the collector running reliably | **A result exists in week 1.** Nothing downstream can take that away. Also: S-2…S-9, E-1…E-7, F-1…F-3 land here since A1 exercises them |
| **2** | **A complete, unsophisticated agent, end to end.** Perceive → coarse field → derive wet-bulb → **Phase-1 fixed margin** → threshold → explain → human gate → log. Committed and tagged | **The safety net.** From here the project is finished; everything after is improvement |
| **3** | Backtest harness + all four baselines (§10.1) **before** conformal, so the effect of conformal is measurable. Then Phase 2 (split conformal) and Phase 3 (max-over-horizon). Coverage and width reported | Baselines before the thing they evaluate. Otherwise "it works" is unfalsifiable |
| **4** | ⭐ **A3.** §9.3 Stage 1 (well-powered historical H1) then Stage 2 (live). Phase 4 σ-normalised and Mondrian. The coverage table with σ-tercile columns. R4's coarse-to-fine sampler | The contribution. Needs three weeks of residuals and the backtest harness to exist |
| **5** | Phase 5 ACI. §10.5's sensitivity sweep. The operator gate CLI polished. Fixtures recorded for a fully offline demo | Robustness and demo safety |
| **6 / spare** | NVIDIA secondary: local Nemotron for the explanation layer; Earth-2 ensemble spread as a **second** conditioning feature alongside σ_spatial, with an experiment on which predicts residuals better. Writeup, limitations slide, Tier-2 answers rehearsed aloud | Explicitly last, because it is secondary |

## 14.4 Cut order, if behind

Cut from the bottom:

1. Earth-2 second conditioning feature
2. ACI (Phase 5) — a crisp *"here is why exchangeability fails, here is what ACI does, I ran out of
   time"* beats a broken implementation
3. Mondrian variant (keep the σ-normalised score)
4. The `persistence` / `time_of_measure` mode work (keep `exceedance`, which A1 needs)
5. Local Nemotron (fall back to a hosted model for prose, and say so)

**Never cut:** the Phase-1 safety net · the fail-safe ladder · the human gate · A1 · A2 · the
baselines · the sensitivity sweep · honest reporting of n_eff.

---

# §15 — Code layout

## 15.1 Tree

```
fgcool/
  clock.py              now() — INJECTED everywhere; datetime.now() appears nowhere else
  config.py             sites, polygons, thresholds + derivations, cost constants (⚠ all stubs)
  api/
    client.py           auth · submit · bounded poll · backoff+jitter · timeout · credit accounting
    heatmap.py          request builders per mode/granularity/filter_type
    envparams.py        point queries, 3-parameter budget
    usage.py            credit reads; the pre-submit budget guard
    fixtures.py         record and replay; asserts fixture issuance == injected now
  metar/
    stations.py         station registry per metro, with distances
    fetch.py            archive retrieval, caching
  psychro.py            wet-bulb from T+RH or T+Td; psychrolib primary, Stull fallback, pressure correction
  field.py              tile grid, lattice snapping, max, hot-spot, σ_spatial, sub-polygon construction
  sampler.py            R4: coarse → read σ → decide whether/where to refine
  threshold.py          per-site threshold; recomputes from parts and asserts agreement
  conformal/
    scores.py           |y−ŷ| · one-sided · max-over-horizon · σ-normalised
    split.py            the ⌈(n+1)(1−α)⌉ quantile, with the minimum-n assertion
    mondrian.py         strata: σ-tercile × horizon × site
    aci.py              online α update (~20 lines)
    diagnostics.py      coverage, width, binomial CI on coverage, per-stratum slices, n_eff
  decide.py             bound vs threshold; the fail-safe ladder; the documented tie-break
  explain.py            LLM prompt + the numeric grounding assertion
  gate.py               CLI review queue: approve / reject / override+reason
  logbook.py            append-only writer; frozen schema; unique-key idempotency
  collector.py          hourly: job 1 forecast, job 2 actuals backfill
  scorer.py             join predictions to actuals → residuals
  backtest/
    harness.py          walk-forward, no random splits
    baselines.py        B0 always-chiller · B1 reactive · B2 persistence · B3 airport-driven
    costmodel.py        kW/ton → kWh → $, with the sensitivity sweep
  experiments/
    hours_map.py        A1
    loo_stations.py     A2
    h1_spatial.py       A3 — Stage 1 historical, Stage 2 live
  stubs/
    cooling_plant.py    labelled interface, no simulation
    gpu_load.py         DCGM-schema shape, labelled
    intake_sensor.py    labelled — the reason recirculation is absorbed into the threshold
cli.py                  run-hour · collect · backfill · review · backtest · experiment
tests/
fixtures/               recorded real responses, by activity_id
```

## 15.2 Two non-negotiable rules

**Injectable `now`.** `datetime.now()` appears in exactly one place: `clock.py`. Everything else takes
`now` as a parameter. Without this, replay mode is impossible — and a forecast fixture is only
meaningful relative to its issuance time (**O7.3**).

**UTC internally, local only for display.** Three timezones, one of which does not observe DST (§12.1).
Any local timestamp in the log is a derived display column, never a key.

## 15.3 The frozen log schema

**This is the irreversible decision (Z-3).** A missing column on day 1 is a permanent hole in weeks of
unrepeatable data. Columns exist because a *specific* downstream consumer needs them; the consumer is
named.

**Table `predictions`** — one row per (site, issuance, valid time):

| Column | Consumer |
|---|---|
| `schema_version`, `code_version` | Migrations; reproducibility |
| `run_id`, `site_id` | Grouping; per-site coverage (K-8) |
| **`issued_at_utc`** | **Per call, not per run** (G-6). Horizon arithmetic; staleness |
| `valid_at_utc`, `horizon_h` | Residual grouping by horizon (§7.4) |
| `fetched_at_utc` | Staleness proxy if no issuance timestamp exists (D3.4) |
| `activity_id`, `endpoint`, `mode`, `granularity`, `filter_type`, `polygon_hash`, `request_hash` | Free re-reads; fixtures; reproducing any historical call exactly |
| `n_tiles`, `tile_grid_hash` | The grid-stability edge case (§12.2) |
| `wb_max_c`, `wb_mean_c`, `wb_min_c`, **`wb_stddev_c`** | The decision value; **σ_spatial — R1's conditioning variable** |
| `db_max_c`, `db_mean_c`, **`db_stddev_c`** | The proxy path if E-8 fails (§11.3) |
| `hotspot_lat`, `hotspot_lon` | Sensor-siting narrative; refinement targeting |
| `refined` (bool), `refine_sigma_k` | R4's action, so the agent's choices are auditable |
| `source` (`fortyguard` \| `derived` \| `metar`), `derivation` (`none` \| `psychrolib` \| `stull`) | Provenance (§5) |
| `threshold_c`, `threshold_version` | Never compare across threshold versions (§12.6) |
| `alpha`, `margin_c`, `margin_source` (`phase1` \| `split` \| `maxhorizon` \| `normalised` \| `mondrian` \| `aci`) | Which phase produced this row; the §9.3 table |
| `n_calib`, `n_eff` | Printed with every coverage figure (§7.4) |
| `bound_c`, `decision`, `failsafe_reason` | The decision and why |
| **`run_max_residual_c`** (filled later by `scorer`) | The max-over-horizon score (§7.5) — must be storable alongside per-hour values |
| `explanation_text`, `explanation_numbers_ok` | Grounding audit (§4.2) |
| `operator_action`, `operator_reason`, `operator_at_utc` | §10.4's second evaluation signal |
| `credits_delta`, `latency_ms`, `api_status`, `retry_count` | Budget guard; §11 bottleneck monitoring |

Unique key: `(site_id, issued_at_utc, valid_at_utc)` — the cron-overlap idempotency guard (§12.5).

**Table `actuals`** — separate, so revisions are visible:

| Column | Consumer |
|---|---|
| `site_id`, `valid_at_utc` | The join key |
| `actual_wb_c`, `actual_source`, `actual_derivation` | The residual |
| `actual_fetched_at_utc`, `revision_n`, `previous_value_c` | **K-5** — silent revision detection. A revision appends, it never overwrites |
| `actual_field_stddev_c` | Was the field structured at the valid time, as well as at issuance? |

**Table `metar`** — station observations, cached: `station`, `obs_at_utc`, `db_c`, `dewpoint_c`,
`wind_kt`, `derived_wb_c`, `raw`.

## 15.4 Replay mode

Every response is recorded to `fixtures/` keyed by `activity_id` and `request_hash`. In replay mode the
client serves from fixtures, `now` is injected from the fixture's issuance time, and the whole agent
runs with no network. This is the demo path — a live API call during judging is an avoidable risk — and
it is also how the test suite runs.

---

# §16 — Stubs and limitations

## 16.1 The four stubs

A **stub** is a clearly-labelled interface with no implementation behind it. It is more honest than a
simulation, because a simulation invites the reader to believe a number was measured.

| Stub | What a real system would put here | Why it is a stub | Consequence |
|---|---|---|---|
| `cooling_plant.py` | A BMS / plant controller interface — actual setpoints, chiller state, tower fan speed | No facility | The agent recommends; it never actuates. This is also why the human gate is architecturally natural |
| `gpu_load.py` | Real DCGM telemetry — projected compute load, since a rack at idle and mid-training-run are different thermal problems | No cluster | The load-aware half of the decision is an interface, not a claim. **§1.4's argument survives, but "we account for load" must not be said** |
| `intake_sensor.py` | A wet-bulb sensor at the tower intake | No facility | **Recirculation is absorbed into the threshold** (§6.3) rather than measured. This is the honest response, and the failure mode is nameable: the forecast can be right and the outcome still bad |
| Facility cost constants (`config.py`) | Real kW/ton and tariff from the operator | No operator | Every dollar figure is quoted **with** §10.5's sensitivity sweep |

## 16.2 What this system cannot claim

Written out so it can be said first, before being asked:

- **No measured thermal outcome.** This is a recommender evaluated in simulation. Actual rack
  temperatures, plant dynamics, and switching costs are not modelled.
- **No real operator.** The gate is exercised by the developer. It demonstrates the mechanism.
- **Coverage is measured against the API's own later estimate**, validated against station
  observations (W-3) — not against a thermometer at the site, because none exists.
- **Wet-bulb is sampled at 2 m, not at the tower intake.** The defence is physical: heating air raises
  dry-bulb but lowers relative humidity and the two effects largely offset, so **wet-bulb varies far
  less with height and location than dry-bulb does.** And the headline comparison in A2 is 2 m-to-2 m,
  so it is unaffected. But the intake itself is a stub.
- **The microclimate sampling is horizontal, not vertical.** Sampling "the roof" is not possible from
  2 m data. What varies across the property is the arriving air, and that is what is sampled.
- **n_eff ≈ 42, not 1,008.** Every coverage figure carries a confidence interval roughly ±10 pp.
- **90 % coverage means being wrong one hour in ten.** That is not a bug; it is the number, and it is
  why a human approves.
- **United States only**, per FortyGuard's current coverage.
- **Three sites is three climates, not a representative sample of the US.**

---

# §17 — What FortyGuard gets from this

The reverse-value section. A team that produces usable feedback on the sponsor's own API is more
interesting than one that merely consumes it.

## 17.1 Capabilities this exercises hardest

| Capability | How this project stresses it |
|---|---|
| `stats_data` | Promoted from a summary convenience to **a load-bearing physical signal**. If H1 holds, `stats_data.stddev` is a forecast-difficulty indicator — arguably a *product feature FortyGuard does not currently market* |
| `exceedance` + `direction: below` | Used as a decision primitive, not a visualisation. Server-side threshold counting over a forecast window is close to a purpose-built answer for industrial cooling |
| `persistence` | Used for the commitment-window question. If its semantics are "longest consecutive run," it maps directly onto an operational decision |
| Granularity ladder | Exercised as an **economic** choice via coarse-to-fine refinement, which is probably how cost-sensitive customers will actually use it |
| 2019→present history at 60 m | Used to produce a per-tile climatology artifact (A1). A strong demonstration of the archive's value beyond ad-hoc lookups |

## 17.2 Gaps this exposes — the honest feedback

| Gap | Why it costs users | What would fix it |
|---|---|---|
| **No uncertainty field** in any response schema | Any risk-aware decision needs one. This project spends its hardest week building an external substitute | A spread, ensemble, or confidence column — even a coarse one |
| **No forecast archive** (§5.2) | A single time concept in the request means past forecasts are unrecoverable. Every customer wanting to validate forecast skill must start collecting from scratch and wait weeks | A second optional time parameter (issuance time) — arguably the single highest-value addition for serious users |
| Air vs. surface temperature not stated unambiguously in the docs | The difference is ~20 °C in a car park. It is the most consequential possible documentation ambiguity | One explicit sentence, and the variable's reference height |
| Whether a future value is a genuine forecast is undocumented | Users cannot tell a forecast from persistence without designing an experiment (B-5) | State the method and the underlying model |
| Credit cost per call not published | Makes budgeting a measurement exercise. A three-site hourly collector cannot be planned in advance | A cost table by endpoint × granularity × area × filter_type |
| Whether `env_params` requires a preceding heatmap is ambiguous (B-7) | The docs' "should match the heatmap you generated" reads as a dependency but may be advice. Doubles cost if misread | One clarifying sentence |
| Wind direction availability unclear (D-6) | Advection-aware use cases — early warning from upwind conditions — depend on it | State it |
| Time-step and mean-vs-instantaneous semantics undocumented (C-9) | An hourly mean hides sub-hourly peaks, which matters for safety decisions | State it |

## 17.3 What a v2 would ask for

1. **Issuance time as a request parameter.** Unlocks forecast-skill validation without a collection
   window. Highest value by a distance.
2. **A spatial uncertainty layer** — if `heat_intelligence` already provides something like this
   (**S-9**), it is under-marketed for this use case.
3. **Wet-bulb as a mappable heatmap variable.** For any evaporative-cooling customer, wet-bulb is *the*
   variable, and per-tile `env_params` calls are not a viable substitute.
4. **A threshold-exceedance subscription** — "notify me when the forecast field over my polygon crosses
   X" — which is this project's decision, as a product.

---

# §18 — Glossary

| Term | Plain meaning |
|---|---|
| **ACI** | Adaptive Conformal Inference. Updates the margin online: recently under-covering → widen; over-covering → tighten. Guarantee is long-run, not finite-sample |
| **Advection** | Air being carried horizontally, bringing different conditions with it |
| **Agent** | A program that loops: perceives, chooses its next action at runtime from what it saw, acts, remembers |
| **Approach temperature** | How far above the ambient wet-bulb a cooling tower's output water actually lands. Caused by finite contact time. Typically 2–5 K |
| **Autocorrelation** | Nearby things resemble each other. Today's error resembles yesterday's, so 24 hourly errors carry roughly one day of information |
| **Backfill** | Fetching what actually happened for hours that have now passed |
| **Baseline** | A simpler method you must beat for your result to mean anything |
| **Calibration set** | A pile of past residuals. Your track record of being wrong. Conformal prediction is built entirely from this |
| **Chiller** | Compressor-driven refrigeration. Works always; costs a lot |
| **Climatology** | The long-run average for this place and time of year. A forecast that is really climatology is not a forecast |
| **Collector** | A small script that runs hourly, calls the API, and appends rows to a file. Runs on a laptop |
| **Conformal prediction** | Turning a point prediction into an interval with a measured coverage rate, using nothing but past residuals |
| **Cost-loss model** | Protect when the probability of harm exceeds (cost of protecting) ÷ (loss if unprotected) |
| **Coverage** | How often the interval actually contains the truth. Nominal = what you claimed; empirical = what happened |
| **DCGM** | NVIDIA's GPU telemetry schema. Used here only as a stub's shape |
| **Dewpoint** | The temperature at which air becomes saturated. METAR reports it; wet-bulb is derived from it |
| **Dry-bulb** | Ordinary air temperature |
| **Economizer** | HVAC term for free cooling. *Airside* pulls in outside air; *waterside* uses a tower. This project is waterside |
| **Effective sample size (n_eff)** | How many genuinely independent data points you have after autocorrelation. Always less than the row count. **The number that matters** |
| **Exceedance** | A count of hours above or below a threshold. Also a FortyGuard heatmap mode |
| **Exchangeability** | The assumption that reordering the data changes nothing. Temperature series violate it |
| **Fail-safe** | On any doubt, choose the expensive-but-safe action. Here: chillers |
| **Field** | Values across an area, not at a point. FortyGuard's product |
| **Fixture / replay mode** | Saved real API responses, so the agent runs offline |
| **Free cooling** | Cooling by evaporating water into outside air, compressor off. Cheap; only works when wet-bulb is low enough |
| **Granularity** | Tile size in the heatmap: 60, 80, or 100 m |
| **Heat island** | Built-up areas being warmer than their surroundings. Strongest on calm nights |
| **Hindcast** | A model's estimate *about the past*, made after the fact. Looks like an observation; is not one |
| **Horizon** | The gap between when you asked and what you asked about. A 1-hour-ahead guess is much better than a 12-hour one, so residuals are always grouped by horizon |
| **IDW** | Inverse-distance weighting. Estimate at a point by weighting nearby stations by 1/distance². The standard interpolation baseline |
| **Issuance time** | *When you asked.* At 09:00 asking about 15:00 → issuance 09:00 |
| **Joint vs marginal coverage** | "Each hour's bound is right 90 % of the time" (marginal) is much weaker than "the bound holds for *all 12* hours 90 % of the time" (joint). This agent needs joint |
| **Land-surface temperature (LST)** | The temperature of the ground itself. A sunny car park at 55 °C with 35 °C air above it. This project needs the **air** number |
| **METAR** | The hourly weather report every airport publishes from real instruments. Free, archived for decades |
| **Mondrian conformal** | Split the calibration set into groups and compute a separate margin per group |
| **Nonconformity score** | The number measuring how badly a prediction went. You *choose* it — this project's choice is §7.6's contribution |
| **Observation** | A number from a physical instrument |
| **Persistence forecast** | "Conditions will stay as they are now." Deceptively strong; a required baseline |
| **PUE** | Power Usage Effectiveness — total facility power ÷ IT power. Cooling is the main non-IT term |
| **psychrolib** | A free library implementing the physics of moist air. Temperature + humidity → wet-bulb |
| **Psychrometrics** | The physics of air–water-vapour mixtures |
| **Recirculation** | A cooling tower breathing back its own warm, saturated exhaust, raising the floor it is working against |
| **Residual** | How wrong a prediction was. Predicted 18.0, got 19.4 → residual 1.4 |
| **σ_spatial** | The standard deviation of values across the campus tiles. This project's difficulty signal |
| **Setpoint** | The temperature the plant is trying to hold |
| **Split conformal** | The standard, practical form: calibrate on a held-out set, take a quantile of the scores |
| **Stall / staleness** | A forecast older than a defined bound. Triggers the fail-safe |
| **Stub** | A labelled interface with nothing behind it. Honest, unlike a simulation |
| **Stull approximation** | A closed-form wet-bulb formula from temperature and relative humidity. MAE < 0.3 °C, assumes near-sea-level pressure, valid 5–99 % RH and −20…+50 °C |
| **Threshold** | The ambient wet-bulb above which free cooling is refused. A **chosen, justified** assumption, derived in §6 |
| **Valid time** | *What you asked about.* In the issuance example, 15:00 |
| **Walk-forward validation** | Evaluating a time-series system without leaking the future. Random splits are invalid |
| **WBGT** | Wet-bulb *globe* temperature — a different heat-stress index. Not what this project needs; B-8 rules it out |
| **Wet-bulb** | The lowest temperature reachable by evaporating water into air. The hard floor on evaporative cooling, and the governing variable of this entire project |
