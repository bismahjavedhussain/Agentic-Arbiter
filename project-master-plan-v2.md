# Downwind — Master Plan v2 (LOCKED)

**Measuring thermal interference between neighbouring data centres with FortyGuard's 60 m
air-temperature field — then using it to price siting and defend permits.**

**Supersedes [project-master-plan.md](project-master-plan.md) (v1), which is preserved byte-unchanged so
the v1→v2 diff is auditable and the pivot defensible.**
Commercial review: [project-viability-report.md](project-viability-report.md).
Verification protocol: [fortyguard-day1-data-checks.md](fortyguard-day1-data-checks.md).
Beginner explanations: [what-am-i-building.md](what-am-i-building.md) ·
[how-it-all-fits.md](how-it-all-fits.md).

| | |
|---|---|
| **Locked** | 2026-08-09 |
| **Hackathon** | **Aug 18 → 30, 2026.** Fresh API key at start |
| **Prep window** | **Aug 9 → 17 — 9 days, zero credits** |
| **Builder** | Solo, second-semester CS student |
| **Judges** | FortyGuard primary · NVIDIA secondary |
| **Credits spent verifying so far** | **0** — ~16 calls; metering frozen on the audited key |
| **Rubric estimate** | ≈83 / 100 |

**Evidence tags — no untagged quantitative claim appears anywhere.**
**[M]** measured, response on disk · **[H]** historical, from the account's usage breakdown ·
**[L]** literature, cited in §2 · **[U]** unverified, with the settling check named · **[S]** stub.

---

# §0 — One page

## The problem

A data centre turns electricity into heat and blows it outside. **In 2026 this became the newest
documented urban-heat hazard** — and a scientific fight, because the people with satellites were
measuring hot **roofs** while the question is about hot **air**, and the team who measured air properly
could only manage two cars at four buildings for four months [L].

## The twist that makes it commercial

Measured, not assumed [M]: **Ashburn has 226 data centre buildings; 224 of them have at least one
neighbour within 800 m, the median has eleven, and the closest pair is 62 m apart.** The plume reaches
**500 m** [L].

> **They are all standing in each other's exhaust.** A facility's cooling depends on the temperature of
> the air it draws in. Warmer intake → fewer free-cooling hours → the chillers run. **So a neighbour's
> exhaust raises your bill, and which neighbours are hurting you changes with the wind.**

Nobody can measure this. A facility's own sensor reads the damage after it arrives and cannot say why.
Every weather forecast is 3 km-blurry and reports all 226 buildings as one number.

## What Downwind is

An agent that, on each usable day, compares FortyGuard's 60 m air temperature **upwind and downwind** of
every facility in a metro, decides whether the difference exceeds what warehouses with no exhaust show,
and accumulates the result into a **thermal interference matrix** — per facility pair, per wind bearing,
the intake penalty in °C. That matrix then prices siting decisions and supports permit filings.

## Why only FortyGuard

The effect is **500 m in air temperature**. Satellite LST is the wrong variable — that confusion *is* the
dispute. HRRR at 3 km swallows facility and plume in one cell. The published state of the art is two cars.
**Remove FortyGuard and there is no measurement at all**, not a worse one. §4 traces this to named
pipeline stages.

## Feasibility, measured before any code

```
background variation at the plume scale (~500 m)   ≈ 0.09 °C   [M]
the signal being hunted                            0.7–2.2 °C  [L]
                                                   ─────────────
signal-to-background                               ≈ 8–24×
```

## What ships even in the worst case

If FortyGuard turns out blind to waste heat, that result **supports one side of a live scientific dispute**
and satisfies a published requirement for settling it, and the operational half survives on the static
cluster signature. **The project cannot come away with nothing.**

---

# §1 — How the idea got here

Four revisions, each forced by a measurement rather than a preference. Keeping this table is what makes
the pivot defensible instead of apologetic.

| Version | What it was | What killed or changed it |
|---|---|---|
| **v1** | Campus free-cooling switch, keyed on wet-bulb | — |
| **↓** | | Measured intra-campus spread **0.437 °C** [M] — smaller than the 1.5 °C margin it was meant to inform. And the heatmap serves **no spatial wet-bulb**: temperature only, no variable selector, no humidity field, and the `env_params` `temperature` input is inert [M]. **There is no path to a spatial wet-bulb field** |
| **v2a** | Grid transformer derating | The measured signal is **dry-bulb peak**, and 60 m resolves **1.346 °C at 64 km²** [M] — usable. But the rubric weights *"a real **urban-heat** problem"* at 40 %, and transformer aging is urban **infrastructure**, not urban heat |
| **v2b** | Fleet workload placement | Honest hole: only new jobs, and only some of them. Under *"a real client would adopt"* a product whose first caveat is "this applies to a subset of your workload" scores badly |
| **v2 LOCKED** | **Downwind — inter-facility thermal interference** | Data centres are the newest documented urban-heat **source** [L]; the effect is 500 m in **air** temperature, which only FortyGuard measures; the density is measured at 99 % of Ashburn facilities [M]; and it is simultaneously an operational cost nobody can currently see |

## The closure that made this the right answer

v1's threshold ladder contained the weakest number in the entire plan:

```
   22.0 °C   wet-bulb the tower actually breathes
 −  3.0 K    ⚠ STUB — "recirculation + facility waste heat"   ← A PURE GUESS
   ─────
   19.0 °C   ambient limit
```

**That guess is exactly what this project measures.** The neighbour plume *is* the recirculation term. v1's
biggest fudge factor becomes v2's central measurement, and the threshold becomes **dynamic**:

```
threshold_today = water_limit[S] − cooler_approach[S] − self_recirc[S] − interference(bearing_today)[MEASURED]
```

## Two verdicts from my own earlier audit that I retract

- **v1's 12-hour horizon was correct.** I marked it FAILING on a bad inference. It is a rolling now+12 h,
  and `env_params` serves future times too [M].
- **The Jul 30 credit figures were accurate.** I flagged them as having no receipts — they had none in
  `results_raw.json`, but every figure matched exactly when the usage call was run properly [M].

---

# §2 — Literature and policy base

**Sailor, Samareh Abolhassani & Martin, ASME *J. Eng. Sustain. Bldgs. Cities* 7(2):024501, 2026** [L] —
first field measurements of data centre waste heat on neighbourhood **air** temperature:
downwind **1.3–1.6 °F (0.7–0.9 °C)** above upwind on average, peaking **4 °F (2.2 °C)**, detectable to
**⅓ mile (~500 m)**; air-cooled condensers discharge **14–25 °F above ambient**; heat fluxes of thousands
of W/m², *"far exceeding any previously studied urban source"*. Method: multiple vehicles running
simultaneous upwind/downwind transects, **18 Jun – 25 Oct 2025**, four Phoenix facilities — **Mesa
(36 MW)** and **Chandler (169 MW campus)** named. **Their stated gap: "wider temporal and weather
conditions."**

**The dispute** [L]. A satellite study (MODIS **land-surface temperature**, 500 m, 2004–2024) claims 2 °C
average / 9 °C peak warming affecting 343 M people within 10 km. Masley's rebuttal: that is **LST, not
air**; a 2 °C LST rise implies "a fraction of a degree at most" of air temperature; waste heat explains
**1–3 %** — the rest is buildings replacing grass. **His four requirements for settling it:** (i) control
sites vs. other large construction; (ii) **actual air-temperature measurements**; (iii) separating
construction from operation; (iv) isolating regional development. **This project delivers (i)–(iii).**

**Industry already names the mechanism** [L]: *"The position, orientation and layout of the dry coolers,
condensers and cooling towers play a decisive role in heat diffusion, and **poor siting can cause the
recirculation of hot air into the fresh-air intakes.**"* Managed **within** one site; **nobody manages it
between sites.** Also: *"in specific micro-climates, particularly those combining **data center
density** with existing heat stress, the increase reached 9.1 °C"* and *"clusters of data centers may be
becoming significant weather modifiers like cities themselves."* And a trade piece titled *"the heat island
effect operators are refusing to own."*

**The policy moment, in the metro with verified coverage** [L]. Loudoun County: 250+ data centres;
by-right permitting **eliminated** (ZOAM-2024-0001, Mar 2025) → Special Exception with public hearings;
Board moved **Jul–Aug 2026** toward pausing all applications; **Phase 2 use-specific standards being
drafted now, with no heat-impact requirement and no instrument to write one against**; Amazon's Ashburn
proposal under active opposition; Dominion seeking a 14 % residential rate rise citing data centre growth.

**Market scale** [L]: Northern Virginia 6,485 MW (133 data centres in Ashburn alone, May 2026) ·
Dallas–Fort Worth 3,704 MW · Atlanta 3,257 MW · Austin 2,558 MW · plus Phoenix, Santa Clara, Chicago,
Columbus, Salt Lake, Reno–Storey; internationally FLAP-D. **Sailor et al. measured in Phoenix, not
Ashburn** — the phenomenon is documented in a different metro.

**FortyGuard's CEO has publicly named data-centre siting as a use case** [L].

**Rejected alternative, documented:** outdoor-worker heat safety. Its adoption driver is far weaker than I
first claimed — OSHA's heat NPRM is **stalled** (comments closed Oct 2025, no finalisation date), the heat
**NEP expired 8 Apr 2026**, and its proposed triggers are **heat index**, which FortyGuard returns broken
(25.5–25.9 across dry-bulb 20→27 °C) [M].

---

# §3 — The measured baseline

## 3.1 FortyGuard API — verified capability

| Finding | Value |
|---|---|
| **Lattice stability** ⭐ | **6,875 / 6,875 tiles byte-identical** between a forecast call and a historical call over the same polygon [M] |
| **Forecast ↔ historical symmetry** | Same request shape gives prediction and, later, outcome. Real residual: mean **+0.349**, sd **0.150**, range +0.062…+0.666 [M] |
| Tile geometry | Real polygons, **59.7 × 61.4 m**, with coordinates [M] |
| One call covers a metro | **17,658 tiles at 64 km², granularity 60, in 67.1 s** [M]. Premium cap 50 mi² ≈ 129.5 km² |
| Tile yield | ~99 % of theoretical at 25 km²; drops to ~67 % on sub-km² polygons (edge handling) [M] |
| **Air, not surface** ⭐ | Diurnal amplitude **7.8–8.3 °C** [M]. Surface would swing 20–30 °C |
| Horizon | Rolling **now + 12 h**; `env_params` also serves future times [M] |
| `filter_type=4` | One call = per-tile **monthly** min/max (14.81 / 36.85) [M] |
| `filter_type=2` | Per-tile **temporal aggregate** (avg/min/max), never an hourly array [M] |
| Analytic modes | `exceedance` returns `{tile_id, value}`, `units: "hour"` (5.47 of an 8 h window below 30 °C). **`persistence` returns byte-identical values to `exceedance` — it is broken.** `time_of_measure` returns hour-of-peak, 14.0 uniform [M] |
| `env_params` | **15 parameters returned when 6 requested** (filter ignored), plus `elevation` 93.0 m and `solar_irradiance.clear_sky{ghi 702.96, dni 748.46, dhi 134.69}` [M] |
| `heat_intelligence` | Causal attribution; past/present only; **Premium allows 2 analysis types**, not the spec's 5 [M] |
| Latency | heatmap 25–70 s incl. polling; `env_params` 2–25 s [M]. Intermittent status 404s [H] |
| **Flat pricing** | heatmap **4,220** · env_params **2,900** · satellite **14,400** · heat_intelligence **8,600** cr/call, **independent of area, granularity, hours covered and mode** [H] |
| History depth | **2019 FAILS** — two attempts, two modes, 6–7.5 min hang then `Failed`, no diagnostic [M] |
| **⚠ Beyond-horizon fails silently** | `status: "completed"` with **0 tiles and empty `stats_data`** [M] |
| **⚠ Endpoint offset** | Heatmap runs **~3.5 °C above `env_params`** as a near-constant offset; amplitudes agree within 0.5 K (7.79 vs 7.25) [M]. **Never blend the two** |

**The flat-pricing dividend, and it shapes the whole design:** a bigger polygon costs the same as a small
one. **So one call over the metro contains the facilities *and* the control sites *and* the corridors
between them.** The control group is free.

## 3.2 ⭐ Effective resolution — the risk most worth closing, now closed

Mean absolute tile-to-tile difference vs. separation, computed from the 6,875-tile field on disk [M]:

```
separation        mean |ΔT|      ratio vs. previous     n pairs
   45–75   m       0.0108 °C           —                 2,369
   90–150  m       0.0252 °C         2.34×                6,970
  180–300  m       0.0481 °C         1.91×               29,192
  360–600  m       0.0926 °C         1.92×              108,490
  720–1200 m       0.1695 °C         1.83×              370,881
 1400–2400 m       0.3009 °C         1.78×            1,091,511
```

**Smooth, monotonic, near-constant ratio per doubling. No flat region, no jump near 500 m.** An upsample
from ~500 m data would show |ΔT| ≈ 0 below 500 m then a step. It does not. **The 60 m resolution carries
genuine structure**, and the background at plume scale is **≈0.09 °C** against a **0.7–2.2 °C** signal —
**8–24× headroom.**

## 3.3 Cluster density — the gate, passed

OSM Overpass, `telecom|building|industrial|man_made = data_center`, de-duplicated at 60 m [M]:

```
Metro                    facilities   pairs≤500m   pairs≤800m   %with ≥1 nbr ≤800m   median nbrs   max
Ashburn / Loudoun VA        226          583         1,276             99%                11         30
Santa Clara CA               58          180           268             90%                12         19
Dallas–Fort Worth TX         55           52            66             78%                 1          7
Phoenix E-valley AZ          44           30            46             55%                 1          9
                            383 total                                 ~90% across all four
```

Closest pair **62 m** against a **500 m** plume. **Two very dense clusters, two moderately dense.**

**Refinement this forced.** The 62 m minimum shows OSM tags *individual buildings*, not campuses (226
tagged objects vs. ~133 reported "data centres" in Loudoun). For heat the **building** is the right unit —
each has its own condensers — but the pairs must be split:

- **Intra-campus** (same owner) → already managed via fan placement, stack height, spacing. Not novel.
- **Inter-campus** (different owners) → **nobody manages it, because you cannot model a neighbour whose
  equipment, load and exhaust layout you do not know. It is obtainable only by measurement from outside.**
  **This is the target.**

## 3.4 ⚠ Two Tier-0 findings that changed the plan

**(a) Only 34 % of days are usable.** Wind-steadiness census, KIAD, summer 2025, 12:00–20:00 local [M]:

```
days assessed                                            90
usable (steadiness ≥0.85 AND mean speed ≥6 kt)           31   (34 %)
  → a 13-day live window yields only ~4.5 usable days
octants populated over one summer                         7 / 8
sensitivity   ≥0.80 / ≥5 kt →  41 days (46 %), 8/8 octants
              ≥0.90 / ≥8 kt →   9 days (10 %), 5/8 octants
```

**Consequence — a real correction to the earlier plan.** The interference matrix **cannot be accumulated
during the live window.** It must be built from **history**, with days selected by METAR wind. **The live
window's job is confirmation, not construction.** An earlier draft would have produced two or three usable
days and a mostly-empty matrix.

**(b) Our first sample polygon was badly placed.** The 5 × 5 km box already paid for contains **6
facilities, none ≥550 m inside the edge**, so no wedge could be drawn. A grid search over Loudoun [M]:

```
 5×5 km   (~6,944 tiles)   centre 39.0050, −77.4580  →  137 inside, 105 usable
 8×8 km  (~17,777 tiles)   centre 39.0100, −77.4460  →  169 inside, 168 usable   ← USE THIS
11×11 km (~33,611 tiles)   centre 38.9850, −77.4700  →  188 inside, 177 usable
```

**168 facilities measurable in one call**, at a tile count already proven to complete in 67 s.

---

# §4 — Why FortyGuard, by pipeline stage

## 4.1 Substitution test

| Capability needed | Best free source | Verdict |
|---|---|---|
| Hourly metro air temperature | HRRR 3 km · NBM 2.5 km · ERA5 31 km | Available, longer horizon, archived forecasts — **better than FortyGuard above ~3 km** |
| Point ground truth | METAR | Identical. Used here anyway |
| Sub-100 m thermal detail | ECOSTRESS ~70 m · Landsat TIRS ~100 m | **Land-surface temperature, not air** — our own 7.8–8.3 °C amplitude [M] proves the difference. Revisit is days to weeks at fixed overpass |
| Wind bearing | METAR | **FortyGuard serves no wind** [M] — a named external dependency |
| **Per-tile air temperature at 60 m over a metro, on a stable lattice, hourly, with history** | **Nothing** | **The moat** |

## 4.2 Stage-by-stage dependency

```
1  facility + control registers (OSM)                          free data
2  wind bearing and steadiness (METAR)                         free data
3  metro air-temperature field, 60 m, stable lattice            ★ FORTYGUARD ONLY  [M]
4  upwind/downwind wedge differential per facility              ★ dies without stage 3
5  control-site null distribution (same call, flat pricing)      ★ dies without stage 3
6  interference matrix (pair × bearing), from history            ★ dies without stage 3 + filter_type=4
7  siting score / permit evidence pack                          ★ dies without stage 6
8  causal attribution (heat_intelligence) + LLM adjudication     ★ FortyGuard only
9  conformal detection threshold                                works on any source (honest)
10 human gate, logbook, self-scoring                            works on any source (honest)
```

**Substituting HRRR breaks stages 3–8.** Every facility in a 3 km cell receives the identical temperature,
so **the differential is identically zero for all of them** and the product's entire output vanishes.
Stages 9 and 10 survive substitution, and this document says so rather than pretending otherwise.

## 4.3 The quantified version

Two facilities 300 m apart, on opposite sides of a plume boundary:

```
FortyGuard 60 m :  31.2  vs  32.4  →  a 1.2 °C difference, and a decision exists
HRRR      3 km  :  31.7  vs  31.7  →  no difference, and no decision exists
```

**Not a worse decision — no decision.** That is the strongest available form of the argument.

---

# §5 — Architecture

## 5.1 Half A — the measurement engine

For each facility, on each **usable** day: average the 60 m field over an **upwind wedge** and a
**downwind wedge** defined by the observed bearing, and difference them. Build the null distribution of
that same statistic at **control sites** — warehouses, big-box retail, distribution depots: big,
dark-roofed, asphalt-ringed, industrially zoned, formerly fields, **but with no exhaust.** A facility is a
**detection** only when it exceeds the conformal bound derived from that null.

Default geometry, with sensitivity swept in T-1: half-angle **45°**, inner radius **100 m**, outer radius
**500 m**, minimum **8 tiles per wedge**.

Accumulated across bearings and drawn from **history**, this yields the **thermal interference matrix** —
per ordered pair (A→B) and bearing, how much A raises B's intake.

## 5.2 ⭐ Where the agency actually lives: budgeted experiment design

**A concession first.** A loop of *fetch map → fetch wind → average two wedges → compare to threshold →
report*, with `if wind_variance < k` and `if sigma > k`, is **a scheduled pipeline with conditional
branches, not an agent.** Naming that here is cheaper than being told it on stage.

The genuine agency is in **filling the matrix**, which is a sequential decision problem under a budget:

1. The matrix is a grid of (pair × bearing) cells, mostly **empty**
2. **Weather determines which empty cells are fillable at all** — no west-wind plume on an east-wind day.
   And only **34 % of days qualify** [M], so opportunity is genuinely scarce
3. Every measurement **costs credits from a finite pool**
4. **Earlier choices change later value** — a well-sampled bearing has low marginal information
5. The agent must decide **when evidence suffices to declare a detection versus buy more**

So the question each cycle is not *"is the wind steady?"* but:

> **"Given what I know, what I do not, and what I can afford — what is the single most informative
> measurement I can buy right now?"**

Implementation: score every candidate (polygon, historical date, granularity) by **expected information
gain per credit** — cells it would fill × their current emptiness × the pair's plume plausibility, divided
by cost — and buy the top one. Log the score and the runner-up so the choice is auditable.

## 5.3 Half B — the operational loop

```python
def cycle(cluster, now):                    # `now` INJECTED; datetime.now() lives only in clock.py

    # ── PERCEIVE ────────────────────────────────────────────────────────────
    wind = metar.bearing_speed_steadiness(now)          # free; FortyGuard has no wind [M]
    state = matrix.coverage()                           # what do I already know?

    # ── DECIDE (the agentic core): what is worth buying today? ─────────────
    plan = experiment_planner.best_purchase(state, wind, budget)
    if plan is None:
        return skip("no_informative_measurement_affordable")   # a real outcome, logged

    field = heatmap(plan.polygon, granularity=plan.gran, analytic_type="tcm",
                    filter_type=2, start=plan.start, end=plan.end)
    assert field.features and field.stats_data, "empty_field"  # [M] beyond-horizon returns empty silently

    # ── MEASURE ────────────────────────────────────────────────────────────
    for f in plan.facilities:                            # 168 in one call at the §3.4 polygon [M]
        d = wedge_differential(field, f, wind.bearing)
        f.detected = d > conformal.detection_bound(alpha=0.10)   # null from control sites, same call
        matrix.update(f, wind.bearing, d)

    # ── ATTRIBUTE: the agent chooses who earns a paid explanation (max 2 types [M]) ──
    for f in agent_selects(plan.facilities, k=budget.attribution_slots):
        f.cause = heat_intelligence(f.lat, f.lon, analysis=["urban", "anthropogenic"])
        f.verdict = nemotron.adjudicate(f.cause)         # waste heat, or land cover? real reasoning

    # ── OPERATIONAL OUTPUT (deterministic, replayable) ─────────────────────
    for f in cluster.facilities:
        f.interference = matrix.penalty(f, wind.bearing)
        f.threshold    = f.water_limit - f.approach - f.self_recirc - f.interference   # [S] + [MEASURED]
        f.intake_ub    = field.max_at(f) + conformal.margin(sigma=field.sigma, alpha=0.10)
        f.free_window  = window_where(f.intake_ub <= f.threshold)
        f.penalty_band = cost_band(naive_window(f) - f.free_window)   # a BAND, never a point [§10.4]
        f.action       = decide(f, FAILSAFE_LADDER)

    # ── EXPLAIN → GATE → LOG → SELF-SCORE ─────────────────────────────────
    brief = nemotron.write(cluster)
    assert numbers_in(brief) <= frozen_numbers(cluster), "explanation_ungrounded"
    gate.present(brief)                       # a human approves; nothing writes to a PLC, ever
    logbook.append(...)
    scorer.score(now - 1day)                  # re-query yesterday historically → residual → margin
```

**Cost:** 1–2 calls per cluster per cycle. 13 days × 2 clusters × 2 ≈ **52 calls ≈ 219 k credits** —
comfortable in a fresh 1 M pool.

## 5.4 Autonomy checklist

| Requirement | Where |
|---|---|
| Perceives state | Field · wind · facility and control registers · its own logbook · **its own matrix of what it already knows** |
| **Runtime action choice** | **Which matrix cell to target** · whether any measurement is worth buying at all today · granularity · **detection vs. non-detection against its own calibrated bound** · which facilities earn a paid attribution call · escalate or not |
| Independent tool calls | **Number, target and type** decided at runtime from a budget it manages |
| Decisions nobody triggered | Runs on a schedule; emits detections, penalties, a watchlist and a siting score unprompted |
| Closes the loop | Re-queries history to score its own prediction; updates **both** its margin and its matrix |
| Bounded | Fail-safe ladder · non-removable human gate · credit guard · numeric grounding assertion |
| **The LLM's real job** | Adjudicating unstructured causal attribution: **waste heat or land cover?** No threshold answers it. Decorative summarisation is cut |

**Concede unprompted:** the numeric path is deterministic and replayable to an identical number. For a
system producing evidence in a regulatory process, that is correct engineering.

---

# §6 — Endpoint map

| Surface | Verified behaviour | Used for | Breaks what |
|---|---|---|---|
| `heatmap` `tcm` + `filter_type=2` | Per-tile avg/min/max; 17,658 tiles at 64 km² in 67 s [M] | **Stage 3 — the core measurement** | Stages 3–8 |
| `map_data.features[].geometry` | Real ~60 m polygons, **byte-stable across calls and dates** (6875/6875) [M] | Wedge assignment; per-tile time series | Everything per-facility |
| `stats_data.temperature_stats.standard_deviation` | Genuine spatial σ; API 0.11474 vs independent recompute 0.1144 [M] | Refinement decision; margin scaling | The runtime resolution choice |
| `filter_type=4` | One call = per-tile **monthly** extremes [M] | **Stage 6** — historical matrix, before/after commissioning | The matrix; the commissioning test |
| `filter_type=1` / `3` | Single hour / single day [M] | Targeted historical dates for specific bearings | Matrix precision |
| `analytic_type: exceedance` | `{tile_id, value}`, `units: "hour"` [M] | Server-side "hours above threshold per tile" | An optimisation; computable from `tcm` |
| `analytic_type: persistence` | **Byte-identical to `exceedance` — broken** [M] | **Not used.** Run-lengths computed client-side | Nothing |
| `analytic_type: time_of_measure` | Hour-of-peak, `units: "hour"` [M] | When each facility's risk window sits | Nothing critical |
| `env_params` | 15 params + `elevation` + `solar_irradiance.clear_sky`; **serves future times** [M] | Anchor humidity/solar at a few points; elevation for pressure corrections. **Never blended with heatmap temperature** (§3.1 offset) | The solar refinement |
| `heat_intelligence` | Causal attribution, past/present only, **2 types on Premium** [M] | **Stage 8** — the LLM's adjudication input | The attribution half; cut-able |
| `status/{activity_id}` | Async lifecycle, intermittent 404s [H]; results persist by id | Bounded polling with grace window; fixture source | Reliability, replay |
| `system/fetch-api-key-usage` | Plan, cycle state, per-activity breakdown [M] | Day-1 price measurement; the live budget guard the planner spends against | Budget safety |
| `system/fetch-api-key-custom-usage` | Usage over an arbitrary date range [M] | Per-phase accounting | An optimisation |
| `hackathon-registration` · `free-key` · `startup-key` | Self-service key issuance [M] | Escape hatch if credits run out | Recovery |
| `satellite` | 14,400 cr/call [H] — 3.4× a heatmap | **Not used.** Land cover is free from OSM/Sentinel-2. Worst credit-per-decision in the catalogue. Stated, not skipped | — |
| `streetview` | Segmentation [M schema] | **Not used.** Nothing in the decision path consumes imagery | — |

---

# §7 — The measurement method, and its honesty checks

## 7.1 Wedge differential

```
                    WIND FROM the west  ──────────────►

        ╔═══════════╗                        ╔═══════════╗
        ║  UPWIND   ║        ██████          ║ DOWNWIND  ║
        ║  wedge    ║        │ DC │          ║  wedge    ║
        ║  45° half ║        ██████          ║  45° half ║
        ║ 100–500 m ║                        ║ 100–500 m ║
        ╚═══════════╝                        ╚═══════════╝
          mean 31.6 °C                         mean 32.4 °C
                        differential = +0.8 °C
```

The upwind wedge is a **free simultaneous control** — same day, hour, weather and insolation; the only
difference is whether the air has passed the building.

## 7.2 The four honesty checks

| Check | What it does | Why it matters |
|---|---|---|
| **Control sites** | 50+ warehouses, identical method, same days → **the null distribution, which *is* the conformal calibration set** | Masley requirement (i). Turns a number into evidence |
| **Rotation placebo** | Recompute using 200 randomly assigned bearings. The true bearing must sit in the top ~10 % | Proves the signal is *directional*, not just spatial |
| **Wind-following** | Two days, bearings ≥120° apart. **The warm lobe must flip sides** | **Land cover does not move when the wind moves.** This is the discriminator |
| **Before/after commissioning** | Same polygon before construction, during construction, after operation | Masley requirement (iii). **Separates the hypotheses in time, immune to every land-cover confound** |

## 7.3 ⚠ Two limitations that must be volunteered, not discovered

**(a) The control group may be too good.** If FortyGuard infers temperature from land cover, **a warehouse
and a data centre look identical to the model.** Controls would then show the *same* apparent plume and we
would get a null **by construction** — not because there is no effect, but because the instrument cannot
distinguish them. The **wind-following** check separates it: if neither facilities nor controls show
wind-dependent structure, we have learned the instrument cannot answer the question, **and we report
that.** This is the sharpest available objection to the whole method.

**(b) Airport wind ≠ facility wind.** METAR is kilometres away. Mitigation: use only strong, steady
regional flow (§3.4's criteria), and report sensitivity to the bearing tolerance.

**(c) Industrial-area confounding.** Facilities cluster where it is already hot. Control matching on
footprint area, roof type, impervious fraction, road proximity and elevation mitigates but does not
eliminate this. **Contamination screen: exclude any control within 1 km of a facility** — a warehouse
inside a plume is not a control, and including it inflates the null and hides a real effect.

---

# §8 — Uncertainty: two distinct jobs

FortyGuard publishes no uncertainty field in any documented response schema [M].

## 8.1 Job one — detection

*Is the differential real, or ordinary spatial variation?* Take the control-site nulls, sort them, take the
**⌈(n+1)(1−α)⌉-th** largest. At n = 42, α = 0.10 that is the **39th of 42**, not the 38th — the
small-sample penalty is in the formula. Minimum n for a one-sided bound ≈ 1/α − 1: **9 / 19 / 99** for
90 / 95 / 99 %.

Asymmetric cost, exactly as v1 §6.4: **falsely accusing an operator** vs. **missing a real impact** → a
one-sided bound, not a symmetric interval.

## 8.2 Job two — the operational bound

Upper bound on tomorrow's intake temperature, calibrated on forecast-vs-actual residuals. **Already proven
to work**: identical lattice (6875/6875) and a real measured residual pair (mean +0.349, sd 0.150) [M].

## 8.3 Effective sample size

Two separate autocorrelations bite:

- **Spatially:** 500 tiles in a wedge are far fewer independent samples. Estimate the decorrelation
  distance from §3.2's decay curve and report n_eff.
- **Temporally:** consecutive days are correlated. **n_eff ≈ facility-days**, never tile-count. And with
  only 34 % of days usable [M], the usable-day census (T-3) *is* the sample-size budget.

Report n_eff wherever a coverage number appears. Never the row count.

## 8.4 Reporting

Coverage and width **always together** — an infinite interval has perfect coverage and zero value. Plus a
binomial CI on the coverage estimate (roughly ±10 pp at small n), and coverage sliced by bearing octant,
season and metro.

---

# §9 — Artifacts, ordered by commercial worth

| | Output | Buyer and value |
|---|---|---|
| **A1 — Siting score per parcel** ⭐ | *"This parcel gets N free-cooling hours/yr today, and M after the facilities already permitted upwind are built. It deposits +X °C on K homes downwind."* | **Developers, site selectors, brokers, counties.** A capital-allocation decision. Industry literature explicitly asks for it [L]; FortyGuard's CEO has named it [L] |
| **A2 — Permit evidence pack** ⭐ | *"Facility X: +0.8 °C mean downwind, 2.1 °C peak, extent 430 m, K homes. Control sites ±0.3 °C. Placebo p = 0.02."* | **Operators needing a defensible number for a Special Exception; counties needing to verify one.** Both need it; neither has it |
| **A3 — The interference matrix** | Per ordered pair × bearing, intake penalty in °C, built from history | The asset A1 and A2 are computed from. **Nothing like it exists** |
| **A4 — Validation vs. Sailor et al.** | Our differentials at Mesa (36 MW) and Chandler (169 MW) vs. published 0.7–0.9 °C / 2.2 °C / ~500 m | **The credibility anchor** — a peer-reviewed answer key |
| **A5 — Control null + placebo + wind-following** | The statistical spine | What makes it evidence rather than a chart |
| **A6 — Daily operating advisory** | *"Interference +1.2 °C today. Free-cooling window closes 2 h early."* | Operations. **Modest money per facility — say so.** Its real job is proving the measurement is live and calibrated, and driving recurring API consumption |

---

# §10 — Evaluation

## 10.1 Baselines

| | What beating it proves |
|---|---|
| **HRRR 3 km** assigned to every facility | **That FortyGuard's resolution matters** — the load-bearing baseline. It reports a differential of exactly zero |
| Satellite LST at the same sites | **Wrong variable** — reproduces the dispute on screen |
| Control sites | The null |
| Nearest METAR | That hyperlocal beats current practice |
| Persistence | That the forecast adds value |

## 10.2 Metrics

Detection rate vs. Sailor's ground truth · **false-positive rate on control sites** · placebo p-value ·
coverage and width with binomial CIs · **n_eff as facility-days** · sensitivity to wedge geometry and
wind-steadiness thresholds · penalty hours vs. each baseline · operator override rate. Walk-forward only —
random splits leak the future and are invalid for time series.

## 10.3 Required sensitivity sweep

Every **[S]** constant is a guess, so results are reported *as a function of* the derating threshold, the
approach constant, the tariff, and the wedge geometry — never at one value.

## 10.4 ⚠ The economics rule

**No point-estimate dollar figure anywhere.** Order of magnitude only, as a labelled band with its stubs
named: operational **$8–24 k/yr per 10 MW** [S]; siting **$20–30 M per 200 MW decision over 30 yr** [S].
**Lead with the measurement; money is a sensitivity band.**

**And U-1 gates the whole money half:** count the historical hours where ambient sits **within the
interference magnitude of the threshold** — the only band where a 1.2 °C penalty changes a decision.
**200 h/yr → real. 5 h/yr → Half B is worthless even with a perfect measurement.**

## 10.5 State first

No real facility, no measured intake temperature, no operator. Residuals are FortyGuard-vs-FortyGuard;
METAR is the only physical anchor.

---

# §11 — How this scores against the rubric

**Impact & relevance — 40 %.** *"A real urban-heat problem with measurable benefit; commercially viable
solutions a real client would adopt."* Data centre waste heat is the newest documented urban-heat hazard,
with 2026 peer-reviewed field measurements, national press coverage and an unresolved scientific dispute
[L]. The benefit is measurable in °C, in affected homes, and in free-cooling hours. The client is real and
the need is current: Loudoun eliminated by-right permitting, is drafting standards now, and has no
instrument [L]. The product is **thermal due diligence** — an existing budget line, bought at every
acquisition and every permit application, and **aligned with the payer**, who is currently being accused
on contested evidence and cannot answer. **Marks lost:** the highest-value output is bought infrequently,
and every dollar figure runs through stubs. **Estimate 32/40.**

**Technical execution — 35 %.** *"It works, the build is sound, data handled well; deployable,
client-grade quality."* Seven data dependencies were verified before a line of code: 100 % lattice
stability, forecast↔historical symmetry with a real measured residual, genuine 60 m resolution with an
8–24× signal-to-background margin, real tile geometry, one-call metro coverage at 17,658 tiles, air-not-LST
confirmed independently, and a real asset layer measured from OSM rather than stubbed. The demo runs
entirely from `activity_id`-keyed fixtures, so **no live call is needed during judging.** **Marks lost:**
the central risk (does FortyGuard see waste heat?) is unresolved until Aug 18, and airport wind is a proxy.
**Estimate 29/35.**

**Innovation — 15 %.** *"Original approach or a fresh combination of ideas."* It scales a published 2026
method from four buildings measured by two cars to every facility in a metro, computationally and
retrospectively; it adjudicates a live scientific dispute using the variable both sides agree is the
correct one; and the inter-facility interference framing is unclaimed. **Estimate 13/15.**

**Communication — 10 %.** *"Clear, compelling demo and write-up."* Two strong assets: a visible warm plume
trailing downwind of a building, and the surface-vs-air distinction, which is memorable and is the crux of
a real argument. Beginner-level explanations exist in two companion documents. **Estimate 9/10.**

**≈83/100 — and the gap between 83 and 71 is entirely whether it reads as a product or a study.**

---

# §12 — Bottlenecks and risks

| # | Risk | Detect | Mitigation | Trigger |
|---|---|---|---|---|
| **1** | **Model blind to waste heat** (World B) | **P-2 wind-following**, day 1 | Static cluster signature as a spatial correction to the regional forecast; report the null as a finding | Warm side does not move → publish the negative result |
| **2** | ⚠ **Control group too good** (§7.3a) | Q-2 with P-2 | State that the instrument cannot answer the question | Controls show the same plume **and** P-2 fails |
| **3** | **Free data predicts the field** | **R-2**, free, before Aug 18 | None — the premise would collapse | R² > 0.9 from OSM + NDVI + elevation |
| **4** | **The money does not follow** | **U-1**, free | Ship the measurement half only | < ~20 h/yr in the decision band |
| **5** | **Only 34 % of days usable** [M] | Already measured | **Build the matrix from history, not live accumulation.** Relax to ≥0.80/5 kt for 46 % and 8/8 octants | A bearing octant with < 5 days → mark that cell unreliable, do not interpolate |
| **6** | Price unverified on the new key | Usage read either side of call #1 | Flat pricing rewards one big call | ≫4,220 → fewer, larger polygons |
| **7** | **History does not reach 2019** [M] | Bisect 2025 / 2023 / 2021 | Commissioning analysis limited to whatever is real | Only ~1 yr → drop A4's before/after |
| **8** | Silent empty beyond horizon [M] | Non-empty assertion on every response | Fail-safe rung 3 | — |
| **9** | `persistence` broken [M] | Found | Client-side run lengths | Already mitigated |
| **10** | ~3.5 °C endpoint offset [M] | Repeat at 3 points × 3 hours | Heatmap alone for temperature; **differencing cancels a constant offset** | Non-constant → drop `env_params` from the decision path |
| **11** | Payload at 17,658+ tiles | Measured | `stats_data` + joined rows hot; archive `map_data` by `activity_id` | 129 km² call times out → tile the metro |
| **12** | Solo-developer time | Weekly check | §13 gates | Cut per §13 |

## Fail-safe ladder

| # | Condition | Action |
|---|---|---|
| 1 | API error after retries exhausted | Conservative output, `api_unavailable` |
| 2 | Fetch age > 6 h **[S]** — the heatmap has **no metadata block at all** [M], so staleness can only be fetch age | `stale_field` |
| 3 | **`completed` but zero tiles or empty `stats_data`** [M] | `empty_field` — **never treated as data** |
| 4 | Wind steadiness below criterion | `unusable_day`, logged, no measurement recorded |
| 5 | Fewer than 8 tiles in either wedge | Skip that facility, log it |
| 6 | `n_calib` below the conformal minimum (§8.1) | Fixed conservative threshold — **never zero** |
| 7 | Rolling coverage below nominal by more than its CI | Conservative + health alarm |
| 8 | Numbers in generated prose ≠ frozen decision | `explanation_ungrounded`, log both |
| 9 | Credit guard would be breached | Skip the cycle |
| 10 | Heatmap vs `env_params` disagreement beyond tolerance [M] | Use the heatmap. Flag. **Never blend** |

---

# §13 — Tiers and cut lines

**Ambitious.** A1–A6 · the interference matrix across ≥6 bearing octants from history · live confirmation
Aug 18–30 · conformal detection threshold with control-site null · `heat_intelligence` attribution with
Nemotron adjudication · full sensitivity sweep · CLI review queue with override capture.

**Fallback — what ships if everything goes wrong.** **A4 + A5 + a working agent on a fixed threshold.**
The Sailor validation, the control-site null with placebo and wind-following, and an agent running end to
end on fixtures with a fail-safe ladder, human gate and logbook. **A complete, defensible project** — it
answers a live scientific question and needs almost no live credits.

**Cut order, from the bottom.** Earth-2 → A6 daily advisory → A1 siting score → `heat_intelligence`
attribution (LLM falls back to land-cover heuristics) → second metro → local Nemotron (hosted model, **and
say so**).

**Never cut:** the control-site null · the placebo test · the wind-following test · the fail-safe ladder ·
the human gate · n_eff honesty · the banded economics rule.

**Demo safety.** Everything replays from `activity_id`-keyed fixtures with an injected `now`. **No live
call is required during judging.** The ~16 responses already captured are the seed set.

---

# §14 — NVIDIA

| Component | Verdict |
|---|---|
| **Nemotron, open-weight, local, batched (vLLM / TensorRT-LLM)** | **LOAD-BEARING**, on two specific grounds. *A real reasoning job:* adjudicating `heat_intelligence`'s unstructured attribution — waste heat or land cover? — per facility, every cycle, feeding back into detection confidence. No threshold answers that. *Architecture:* a tool producing evidence for a regulatory process must not put a cloud API on its path — availability and data governance |
| **Earth-2 / FourCastNet (PhysicsNeMo)** | **GATED STRETCH.** Plume transport depends on boundary-layer state; ensembles give a spread of transport scenarios, and FortyGuard publishes **no wind and no uncertainty** [M]. **Not started unless the agent is demoable by Aug 27.** Honest caveat: free ensembles exist (GEFS, HREF), so the argument is GPU-native ensembling and stack fit, not exclusivity |
| **RAPIDS / cuDF / cuSpatial** | **CUT.** 17,658 tiles per call [M]; the full historical sweep is under a million rows. Pandas and shapely handle it in seconds on a laptop. No bottleneck → no argument → logo. NVIDIA judges would spot it first, and it would undercut the Nemotron argument that *is* real |

---

# §15 — Schedule

**Invariant: a working end-to-end agent exists on fixtures before anything clever. Ugly is fine.**

## Phase 0 — Aug 9 to 17, zero credits

| Day | Work |
|---|---|
| **9** | Register the hackathon key. Read Sailor et al. and the Masley post. ✅ *Tier-0 tests already done: resolution decay, usable-day census, optimal polygon* |
| **10** | Facility register (OSM + Loudoun list) → **group buildings into owner campuses** so intra-campus pairs are separated from inter-campus. Control-site register with the **1 km contamination screen** |
| **11** | METAR ingest; **select the specific historical dates** for each bearing octant from the usable-day census |
| **12** | **R-2 — can free data predict the field?** Fit OSM land use + building density + NDVI + elevation → FortyGuard's saved field. **If R² > 0.9 the premise collapses — this must run before Aug 18** |
| **13** | Wedge geometry + differential engine, validated against the 6,875-tile response on disk. API client: bounded poll, 404 grace, backoff+jitter, **non-empty assertion**, credit guard, record/replay. Injectable clock, UTC-internal, frozen log schema |
| **14** | Control-site null on synthetic data; **placebo harness**; conformal detection bound |
| **15** | **U-1 — does the interference change any decisions?** Historical hours in the decision band. Cost model as a **band** |
| **16** | Experiment planner: expected-information-gain-per-credit scoring over matrix cells |
| **17** | **Working agent end-to-end on fixtures. Commit and tag — the safety net.** Write the Aug 18 call sheet |

## Phase 1 — Aug 18 to 30, live key

| Day | Work |
|---|---|
| **18 am** | **Call sheet, in order. ~14 calls. Every decisive call is HISTORICAL, so viability is settled on day one.**<br>0 · usage read → baseline<br>1 · heatmap over the **8×8 km polygon centred 39.0100, −77.4460** (168 usable facilities [M]) → usage read → **PRICE**<br>**2 · ⚑ P-2 WIND-FOLLOWING** — same facility, two historical days ≥120° apart. *Does the warm side move?*<br>**3 · ⚑ P-1 ANSWER KEY** — Chandler (169 MW) vs. published 0.7–0.9 °C<br>**4 · P-1b** — Mesa (36 MW), same<br>5 · **P-3** calm-day negative control<br>6 · **Q-2** control sites — **free, inside call 1's polygon**<br>7 · **R-1** paved vs vegetated tile amplitude<br>8 · **R-3** hot day vs cool day — does the field track METAR at all?<br>9–11 · history bisection 2025 / 2023 / 2021<br>12 · **V-1** before/after commissioning, if depth allows<br>13 · `heat_intelligence`, 2 analysis types<br>→ **re-budget against the measured price** |
| **18 pm** | Start the cycle; record every response as a fixture from call one |
| **19–20** | **A4** Sailor validation · **A5** control null + placebo + wind-following |
| **21–24** | **A3** interference matrix **from history**, planner-driven, one octant at a time |
| **25–26** | **A2** permit evidence pack · **A1** siting score |
| **27** | `heat_intelligence` + Nemotron adjudication. **Earth-2 gate** |
| **28** | Sensitivity sweep · **A6** daily advisory · review queue |
| **29** | **Freeze.** Full offline fixture rehearsal. Limitations slide — including §7.3's three self-disclosures |
| **30** | Submit. Rehearse: the four-pivot evolution, World A vs B, the 8–24× feasibility margin, the nine API defects |

**Hard gates.** No fixture-driven agent by **Aug 17** → ship the §13 fallback. Nemotron not running by
**Aug 28** → hosted model, and say so.

---

# §16 — Code layout and the frozen log schema

```
downwind/
  clock.py            now() — INJECTED; datetime.now() appears nowhere else
  config.py           clusters, polygons, thresholds + derivations, cost bands (⚠ all [S])
  api/
    client.py         auth · submit · bounded poll · 404 grace · backoff+jitter
                      · NON-EMPTY ASSERTION · credit guard · record/replay
    heatmap.py        request builders per mode / granularity / filter_type
    envparams.py      point queries (never blended with heatmap temperature)
    usage.py          credit reads; the budget the planner spends against
  metar/
    fetch.py          hourly bearing + speed; steadiness computation
    usable_days.py    the census; date selection per bearing octant
  registry/
    facilities.py     OSM + Loudoun list; campus grouping (intra vs inter)
    controls.py       warehouses/big-box + 1 km contamination screen + matching
  field.py            tile lattice, geometry, spatial index, σ
  wedge.py            sector geometry, differential, tile-count guard
  planner.py          ⭐ expected information gain per credit over matrix cells
  matrix.py           the interference matrix; coverage; penalty lookup
  conformal/
    detection.py      ⌈(n+1)(1−α)⌉ bound from the control null
    operational.py    intake upper bound from forecast/actual residuals
    diagnostics.py    coverage, width, binomial CI, per-octant slices, n_eff
  placebo.py          rotation test; wind-following test
  decide.py           dynamic threshold, free-cooling window, fail-safe ladder
  explain.py          Nemotron: attribution adjudication + grounded prose
  gate.py             CLI review queue: approve / reject / override + reason
  logbook.py          append-only, frozen schema
  scorer.py           re-query history → residual → margin + matrix update
  experiments/        A1…A6
  stubs/              plant_thermal.py · scada_load.py · cost_constants.py
fixtures/             recorded responses by activity_id
```

**Frozen log columns** (a missing column is a permanent hole): `schema_version`, `code_version`, `run_id`,
`cluster_id`, `facility_id`, `campus_id`, `is_control`, `issued_at_utc`, `valid_from_utc`, `valid_to_utc`,
`fetched_at_utc`, `activity_id`, `request_hash`, `polygon_hash`, `granularity`, `filter_type`,
`analytic_type`, `n_tiles`, `tile_lattice_hash`, `wind_bearing`, `wind_speed_kt`, `wind_steadiness`,
`wedge_half_angle`, `wedge_r_in`, `wedge_r_out`, `n_tiles_up`, `n_tiles_down`, `mean_up_c`, `mean_down_c`,
**`differential_c`**, `field_sigma_c`, `detection_bound_c`, `detected`, `placebo_p`, `alpha`, `n_calib`,
`n_eff`, `interference_c`, `threshold_c`, `intake_ub_c`, `free_window_start`, `free_window_end`,
`penalty_hours`, `penalty_band_low`, `penalty_band_high`, `attribution_json`, `attribution_verdict`,
`planner_score`, `planner_runner_up`, `explanation_text`, `explanation_numbers_ok`, `operator_action`,
`operator_reason`, `credits_delta`, `latency_ms`, `api_status`, `retry_count`, `failsafe_reason`.

`planner_score` and `planner_runner_up` exist so **the agent's own choices are auditable** — which is what
makes the agency claim checkable rather than asserted.

---

# §17 — Stubs and limitations

## Stubs
| Stub | Real system supplies | Consequence |
|---|---|---|
| `stubs/plant_thermal.py` | Real cooler approach, water limit, self-recirculation allowance | Every threshold is parameterised and swept |
| `stubs/scada_load.py` | Actual facility load | Interference is measured; the *response* to it is modelled |
| `stubs/cost_constants.py` | Real kW/ton and tariff | **Every dollar figure is a band, never a point** |
| Facility attributes beyond OSM geometry | MW rating, cooling type, commissioning date | Locations are **real and measured**; attributes are **[S]** |

## What this cannot claim
- **No real facility, no measured intake temperature, no operator.** The gate is exercised by the developer.
- **Residuals are FortyGuard-vs-FortyGuard.** METAR is the only physical anchor.
- **⚠ The control group may be too good** (§7.3a) — the sharpest objection, self-disclosed.
- **⚠ Airport wind is a proxy** for facility wind.
- **⚠ Every economic figure rests on stubs.** Bands only.
- **Only 34 % of days are usable** [M] — the matrix is history-built, and thin octants are marked unreliable.
- **History does not reach 2019** [M]; commissioning analysis is bounded by what bisection finds.
- Heatmap absolute values run **~3.5 °C above `env_params`** [M] and are not standard shelter-height air
  temperature. The method uses **differences**, which cancel a constant offset — but never blend the two.
- `solar_irradiance` is **clear-sky only**; `cloud_cover_octas` is mislabelled; `heat_index_celsius` is
  unusable [M].
- **n_eff ≈ facility-days**, not tiles. 17,658 tiles from one call are one weather sample.
- **US only** [M]. Four metros is not a national sample.

---

# §18 — Defects to report to FortyGuard

Nine findings, all measured. A team that returns usable findings on the sponsor's own API is more
interesting than one that only consumes it.

| # | Defect | Evidence | Cost to users |
|---|---|---|---|
| 1 | **Beyond-horizon returns `completed` + empty instead of 4xx** | 0 tiles, `stats_data: {}` [M] | **Silent data loss.** Highest severity |
| 2 | **`persistence` returns `exceedance`** | Byte-identical 5.0946 / 5.8891 / 5.46597 [M] | A documented mode is unusable |
| 3 | **`heat_index_celsius` near-constant** | 25.9 at dry-bulb ≈27 °C, 25.5 at ≈20 °C [M] | Silently wrong; use `apparent_temperature_celsius` |
| 4 | **`cloud_cover_octas` is a percentage** | 49, 68, 92 on a 0–8 scale [M] | ~11× error for anyone trusting the unit name |
| 5 | **DST ignored** | `"timezone": "GMT-5"` in July **and** August [M] | Every summer timestamp off by an hour |
| 6 | **Documented 2019 history unavailable** | Two modes, 6–7.5 min hang then `Failed`, no diagnostic [M] | Requests fail slowly and opaquely |
| 7 | **Heatmap and `env_params` disagree ~3.5 °C** | Constant offset; amplitudes agree within 0.5 K [M] | Blending them produces wrong derived variables |
| 8 | **Heatmap response has no metadata block** | Only `map_data` + `stats_data` [M] | No timezone, no issuance time → staleness can only be fetch age |
| 9 | **Spec/reality mismatches** | `heat_intelligence` rejects >2 analysis types (spec allows 5); `env_params` `analysis` filter ignored — 6 requested, 15 returned [M] | Clients written to the spec get 400s |

**Two feature requests, in value order.** (1) **An issuance-time parameter** — without it past forecasts
are unrecoverable and every serious customer must collect from scratch. (2) **No wind field** — this project
takes wind from METAR because FortyGuard has none, and wind is what makes a thermal field actionable.

---

# §19 — Glossary

| Term | Meaning |
|---|---|
| **Plume** | A trail of something drifting from its source — smoke from a chimney, warm air from a vent. Ours is invisible warm air |
| **Waste heat** | Heat a building must dispose of. A by-product nobody wants |
| **Upwind / downwind** | The side the wind comes from (clean, untouched) / goes to (where the plume lands) |
| **Surface temperature (LST)** | How hot the ground and roofs are. What satellites see. Can be 20 °C above the air |
| **Air temperature** | How hot the air you stand in is. What FortyGuard serves, and what the dispute is about |
| **Wedge / sector** | The pie-slice of tiles used for the upwind or downwind average |
| **Differential** | Downwind mean minus upwind mean. The measurement |
| **Control site** | A warehouse: big, dark-roofed, asphalt-ringed, formerly a field — but **no exhaust**. Measured identically to show what "nothing happening" looks like |
| **Rotation placebo** | Redo the maths with random bearings. The effect must vanish |
| **Wind-following test** | Does the warm lobe move when the wind moves? **Land cover does not move.** The discriminator |
| **Conformal prediction** | Using a pile of past measurements to set how large a difference must be before you may call it real, with a stated success rate |
| **Interference matrix** | Per facility pair × wind bearing, how much one raises the other's intake |
| **Intra- vs inter-campus** | Same owner (already managed) vs different owners (**unmanageable without external measurement — the target**) |
| **Experiment planner** | The agentic core: picks the measurement with the highest expected information gain per credit |
| **n_eff** | Genuinely independent samples after autocorrelation. Here ≈ facility-days. **The number that matters** |
| **Usable day** | Wind steady and strong enough that a plume direction is meaningful. **Only ~34 % of days** [M] |
| **METAR** | The free hourly weather report every airport publishes. Our only wind source and only physical anchor |
| **HRRR** | NOAA's 3 km hourly model, free. The load-bearing baseline — it reports a differential of exactly zero |
| **Flat pricing** | FortyGuard charges per call, not per area. So one call holds the facilities **and** the controls |
| **Fixture / replay** | Recorded responses so the agent runs offline. The demo path |
| **Stub** | A labelled interface with nothing behind it. More honest than a simulation |
