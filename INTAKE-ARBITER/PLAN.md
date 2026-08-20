# INTAKE-ARBITER — the plan, and the road that got here

**FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)**
Build sprint **Aug 18–30, 2026**. Written 2026-08-16.

> **This document deliberately records what we rejected as well as what we are building.** Seven
> candidate decision cores were designed, pre-registered and tested before this one. Six failed and one
> was withdrawn on its own merits. **Every failure is in §6 with the number that killed it**, because a
> project that only shows what worked is not a research record — and because two of those failures were
> caused by bugs in our own test code, which is worth knowing about a system before you trust it.

---

## 1. What this is, in one paragraph

A data centre can switch its mechanical chillers off and cool with outside air whenever the air entering
its cooling equipment is cool enough. **Operators do this less often than they safely could — and the
reason is TIME, not accuracy.** Their thermometer is on their own roof and it is fine. But **a thermometer
cannot see three hours ahead, and a cooling plant needs that much notice to change mode**, so the plant
either switches late or carries a conservative buffer and leaves hours unclaimed.
**FortyGuard's forecast is precisely the missing input.** INTAKE-ARBITER turns it into an hour-by-hour
switching schedule, adds a validated physics solver for the site's own exhaust recirculation, wraps the
result in a bound whose success rate is *measured rather than asserted*, and then **grades its own accuracy
every day and adjusts how aggressive it is allowed to be.**

### ⚠ Where the value actually is — measured, and it reordered the pitch

| Source of value | Extra free-cooling hours/year |
|---|---|
| **The FORECAST at 3 h notice**, at FortyGuard's *measured* skill (0.617 at 3.5 h) | **≈ 930** |
| The forecast at 6 h notice (skill 0.770) | **≈ 1,944** |
| Recirculation physics alone, no forecast | ≈ 67 |
| The forecast at 1 h notice | ≈ 62 |

**The forecast is ~93 % of the value; the physics is a supporting safety term.** That is the opposite of
how this document originally read, and the reordering is the result of measurement (N-56 + DIAG-57), not
preference. Below ~2 h notice the forecast is worth almost nothing, because persistence is already good
over a short gap.

**Two consequences worth stating plainly:**

1. **The most technically impressive component — the GPU ensemble over a validated dispersion solver —
   delivers about 7 % of the measured hours.** Its real job turns out to be **knowing when to refuse**: at
   the first candidate site it correctly declined on **100 % of the wind directions that mattered**, which
   is why the site was changed rather than a number published that the geometry could not support.
2. **Recirculation is real physics but SMALL here** — mean rise 0.058 °C, worst case 0.350 °C, below the
   0.556 °C resolution of the station we would validate against. It is honest, sourced (ASHRAE Ch. 46
   treats exhaust-to-intake as a design concern) and named in FortyGuard's own track brief — but it is not
   what makes or breaks a cooling decision, and it is no longer presented as if it were.

**⚠ WITHDRAWN: the ≈150 h/yr figure.** Its incumbent read a station kilometres away;
`claims-and-defences.md` §1.15 verified that data centres use **on-site rooftop weather stations**, so the
0.40 °C spatial divergence driving that result largely vanishes. N-56 re-ran the comparison against what
operators verifiably run. **Also withdrawn: "spatial resolution is the value proposition"** — measured
worth **+0.036 °C**, negligible. **FortyGuard's value is the TIME dimension, not the space dimension.**

**⚠ The safety claim is 65.6 %, not 90 %, and we say so** — with the diagnosis that **most of the shortfall
is our own sample size** (a 90 % one-sided conformal bound needs ≥ 9 calibration days; we had 3, ceiling
75 %). **≈10 days recovers it on pure FortyGuard data with no customer hardware.** See HANDOFF §2c and
§8e below.

**And the bound's live coverage is 65.6 %, not the nominal 90 % (§8e).** Both free-cooling figures
therefore **require the customer's sensor to anchor the forecast level**: unanchored, the zero-notice case
**loses 645 h/yr** to the same level bias that produced that coverage failure.

---

## 2. The problem — in FortyGuard's own words

From their Track 3 brief:

> *"Operators of mission-critical facilities like data centers and nuclear plants face escalating cooling
> loads and reliability risks as external heat intensifies. Even minor temperature fluctuations around
> **air intakes**, cooling towers, and external walls can impact uptime, energy use, and equipment
> lifespan. Yet, most environmental monitoring systems only track indoor conditions, overlooking the
> hyperlocal microclimate dynamics that develop around **dense equipment, reflective surfaces, or nearby
> structures**. This blind spot limits **predictive maintenance accuracy**, leading to **overcooling**,
> component degradation, and higher operational costs."*

Every phrase in bold is something this agent addresses. The problem statement is not ours; it is theirs.

---

## 3. What the agent does — the loop

```
ONCE PER CYCLE, unattended:

  PERCEIVE     FortyGuard heatmap      -> hyperlocal ambient field over the campus
               FortyGuard env_params   -> wet-bulb, humidity, solar, cloud cover
               public wind (ASOS/NWS)  -> bearing and speed. FortyGuard serves NO wind.
               own state               -> its measured accuracy record to date

  SOLVE        100-member ensemble on the NVIDIA GPU. Each member is a full 2-D
               advection-diffusion solve of THIS campus's real geometry, with wind
               bearing, speed and load perturbed by their MEASURED uncertainties.
               -> a DISTRIBUTION of intake temperature, not a single number

  BOUND        one-sided split-conformal upper bound from measured residuals
               -> "the intake will not exceed X, and here is the MEASURED rate at
                  which that has held" -- see 8e: live out-of-sample coverage is
                  65.6 % as shipped, 80.1 % level-anchored, NOT the nominal 90 %

  DECIDE       plan a SWITCHING SCHEDULE over the horizon: which hours on free
               cooling, which on mechanical, subject to
                 - a switch budget (short-cycling damages compressors: Trane)
                 - a ramp-rate limit (20 C/hr, ASHRAE Table 4 footnote f)
               The boundary it compares against is a SURFACE computed at runtime from
               f(hours remaining, switches remaining, ensemble spread, coverage record)
               -- not a constant anywhere in the source.

  ACT          write the schedule to a BMS/SCADA-shaped interface, with the reason

  EXPLAIN      local NVIDIA Nemotron renders the reasoning trace in prose.
               The LLM NEVER sets the bound or the schedule. It narrates them.

  SCORE        compare against what actually happened -> residual
  RECALIBRATE  coverage above target -> the bound is too fat -> TIGHTEN -> more
                                        free-cooling hours earned
               coverage below target -> it is breaching   -> WIDEN -> fewer, safer
```

**The last step is the point.** The agent converts *"I have been right more often than I promised"* into
*"therefore I may run free cooling more aggressively."* Nothing tells it to. It derives the permission
from its own track record.

---

## 4. Why we claim this is agentic — and the honest limit of that claim

Graded against the standard ladder (Russell & Norvig, *AIMA* ch. 2), whose top rung — a **learning
agent** — has four organs: a performance element that acts, a **critic** that scores it, a **learning
element** that improves it, and a **problem generator** that seeks informative experience.

| Organ | Status |
|---|---|
| **Perceives** its environment | ✅ FortyGuard + env_params + wind, every cycle |
| **World model** — answers *"what would happen if…?"* about the unobservable | ✅ the solver computes intake air that exists in no dataset |
| **Belief under uncertainty**, not a point estimate | ✅ 100-member GPU ensemble → a distribution |
| **Emergent caution nobody programmed** | ✅ ensemble spread is **27.04× wider** at the geometric edge than in safe sectors. **There is no rule about plumes anywhere in the code** |
| **Performance element** — acts with consequences | ✅ commits a switching schedule under hard constraints |
| **Critic** — scores itself against reality | ✅ running unattended, and it **caught a real failure**: live out-of-sample coverage **65.6 %** against a 90 % promise, worst day **0.0 %** (§8e). The critic working is what makes the rest honest |
| **Learning element** | ✅ two things: the conformal width, and a per-bearing correction learned from its own residuals |
| **Problem generator** | ❌ **not built.** Stated plainly rather than dressed up |

### The test we hold ourselves to, and where it bites

> **Point at the constant.** For any behaviour claimed to be agentic: *can you find, in the source, the
> number a human wrote that produces it?* If yes, it is a threshold in a costume.

| | The boundary is… |
|---|---|
| A thermostat / hysteresis rule | **two constants a human typed.** Readable without running anything |
| **INTAKE-ARBITER** | **a surface** computed at runtime from the ensemble, the switch budget and the coverage record. **Not stored anywhere; nobody can state it in advance** |

**⚠ Two honest limits on this claim, and we say them before a judge finds them:**

1. **It is not a *stopping rule*.** Seven tests established that a "when to act" decision is
   *structurally* impossible in this problem — see §6.7. Because a conformal bound is calibrated per
   lead, **waiting does not change your risk, only your cost**, and two monotone curves cross at one
   hour, which a fixed rule expresses exactly. This is an **adaptive controller with a self-calibrating
   boundary**, which is a real and different thing.
2. **On an easy day it behaves like a thermostat, because that is correct.** The behaviour that
   distinguishes it appears on crossing days, knife-edge days and low-switch-budget days. That is why
   the demo is built around those cases (§8) rather than a typical afternoon.

---

## 5. The physics and the maths, plainly

**Intake temperature = ambient + recirculation.**

- **Ambient** is a neighbourhood-scale quantity — the air arriving has been mixing over hundreds of
  metres — so FortyGuard's ~60 m field is the *appropriate* resolution for it. This is the dominant
  term: **17.8 – 37.8 °C** in five years of local data.
- **Recirculation** is a few-metres quantity: the site's own exhaust curling back into its own intake.
  **0 – 0.855 °C** at the reference layout. This is what no outdoor product can resolve and what the
  solver computes.

**The solver** integrates 2-D advection–diffusion — *advection* is wind carrying warm air, *diffusion*
is turbulence mixing and diluting it — with a *downwash* term for wind bending the rising plume back
down to intake level.

**Why FortyGuard is load-bearing, quantitatively.** The field's own spatial variation is **0.011 / 0.025
/ 0.048 / 0.093 / 0.170 / 0.301 °C** at 60 m → 2 km, with **1.3–1.5 °C** of contrast across the 64 km²
campus area. **That correction is larger than the entire quantity our solver computes.** Substitute a
station reading and you compute a 0.1 °C correction on top of a 1 °C error. And their
forecast↔history symmetry — the same request shape returns a prediction and later the outcome, residual
bias **+0.349 °C**, sd **0.150**, **n = 6,875** — is what makes a calibrated bound possible at all.

**The bound** is one-sided split conformal: take the *k*-th smallest calibration residual where
*k* = ⌈(n+1)(1−α)⌉. That guarantees ≥90 % coverage on exchangeable data with no distributional
assumption — and it is *checkable*, which is the whole point.

---

## 6. What we rejected, and why — the road that got here

**Seven decision cores, each pre-registered with pass/fail conditions written before it ran.**

### 6.1 Forecast sharpening of the FortyGuard field — ❌ underpowered, and the wrong statistic
`b = −0.0608, SE 0.0803, 95 % CI [−0.316, +0.195]`. The CI contains 0, 0.129 *and* 0.187 — it
establishes nothing. **But it excludes 0.500, and 0.500 was the value an earlier headline
("+0.356 cost units/day, 11.2 σ") had been computed with. That headline was retracted.** It also fitted
the *spatial* sd across ~17,862 tiles on one day when the decision needed the *day-to-day* sd of the
*site-level* error — quantities ~9× apart.

### 6.2 The corrected day-to-day statistic — ❌ unresolvable on the calendar
Estimator built and validated against synthetic data with known answers (recovered 0.506 from 0.500).
Then the power analysis: **80–160 days needed.** We had 15. Also found an attenuation trap — a day-level
offset common to all leads squashes a true 0.50 to a measured **0.138**. **Declined to buy extra
forecast legs (~8,440 credits/day) because the power analysis said it could not resolve in time.**

### 6.3 Wind-direction sharpening through the solver — ❌ decisive fail, well powered
σ went the **wrong way**: 0.26 °C at 1 h lead vs 0.16 °C at 12 h. `b = −0.1166, SE 0.0310, t = −3.77`,
CI excludes zero. **It also exposed a real defect of ours:** the ensemble perturbed bearing by **±15°**
while the measured error is **47–72°** — we were understating the dominant uncertainty by ~4×.

### 6.4 Multi-site fleet triage — ❌ −3.63 σ
Lost to a tuned point-forecast ranking baseline. A sign-inversion bug was found and fixed *first*, and
the verdict survived it (−5.51 σ → −3.63 σ). Ranking sites by predicted temperature is something a point
forecast already does well.

### 6.5 Adaptive commitment of reserve cooling — ❌ failed, then closed on physics
Three structurally different implementations lost by **−6.17 σ**, **−21.59 σ** and **−19.37 σ**. A
clairvoyant bound proved the cost model was *consistent*, so it was not a bug: on **84 % of days the
optimal action was to do nothing**, and committing wrongly cost **3.0** against a gain of **112.9** —
break-even precision **2.6 %** against a base rate of **15.6 %**, so "act early, always" is near-optimal.
**Then a defect surfaced that invalidated the whole framing: ambient had been FROZEN at 30.0 °C**, so the
test scored recirculation alone and had deleted the weather from a weather problem. And with a
*physically sourced* threshold (ASHRAE A2 = 35 °C) instead of a quantile of our own model output, a
0.25 °C remedy cannot close a **0.56–2.78 °C** gap. **No cost model can fix an ineffective action, so a
planned 65-configuration cost sweep was cancelled before it ran.**

### 6.6 Margin reduction — ❌ **loses to a constant, and gets WORSE at bigger facilities**
The claim was that modelling recirculation lets you hold a smaller margin than a worst-case constant.
**Measured: −2.19 σ. The agent's margin was *larger*.** Cause, measured not guessed: the rise field is
severely zero-inflated (median p90 across all 72 bearings is **0.0000 °C**), so the unconditional 90th
percentile a constant must cover is only **0.2144 °C** — a much stronger adversary than expected — while
**47.7–72.7° of direction *forecast* error smears the narrow plume across most of the compass**, inflating
the agent's own p90. A requirement sweep found the crossover at **~30–40° of direction error**, against a
measured 68°. And at a facility with a **4.4× larger** condenser bank the saving **inverts** to
**−0.1276 °C**, because a stronger plume amplifies the penalty for getting the bearing wrong. **Closed at
all facility sizes.**

### 6.7 Commitment timing, with ambient unfrozen — ❌ and this one closed the whole class
Rebuilt with ambient varying from 534 real days and the first *positive* sharpening measurement in the
project (**ambient anomaly b = +0.3414, CI [+0.2427, +0.4402]**, which propagates additively so it cannot
invert the way §6.3 did). Waiting from 12 h to 3 h genuinely cuts the required margin by **2.14 °C** —
twenty times the quantities the earlier cores fought over.

**It still failed, and four specification errors in our own test had to be found first, each of which had
inflated an apparent win:** an inherited cost double-count; a threshold grid running to 3.0 while the
variable reached 5.5 (43 % of values off the top of the grid); a scan inequality pointing the wrong way
for a decreasing signal; and finally **an oracle leak — the policy was comparing the *realised* cost,
which contains the actual breach outcome, so it knew whether committing today would breach.** With the
leak removed the DP **loses by 15–22 σ** at every penalty across four decades.

> **And the diagnostic explains all seven failures in one sentence. Because the conformal bound is
> calibrated per lead, the breach rate is 10 % at every hour by construction — waiting changes your
> COST, which falls monotonically, against deadline risk, which rises monotonically. Two monotone
> curves cross at ONE hour. Calibration removes the very state-dependence a stopping rule needs.**

### 6.8 Other things considered and dropped

| Dropped | Why |
|---|---|
| **Fleet GPU-compute allocation** | Equal split wins; all four concentration strategies lost, **−2.7 σ**. Implemented as a one-line rule, which is the correct answer |
| **Credit-budget perception scheduling** | An agent whose talent is minimising API calls **optimises against FortyGuard's own revenue model** — they sell credits. And economically it is a rounding error: the entire data budget is 1,000,000 credits for **$79/month** against a cooling bill |
| **Within-site bank differentiation** | Ambient cancels between banks at one site — which means **FortyGuard cancels**. Maximising our physics' share by minimising theirs is backwards for this entry |
| **Deriving site geometry from FortyGuard** | Tested with two paid calls. `/v1/satellite` returns a **225 × 225** raster with a two-class vocabulary (`earth, ground` 99.78 %, `others` 0.22 %), alpha-blended over the photo, **with no georeferencing**. No building footprints. Ruled out — hence OpenStreetMap instead |
| **`/v1/heat_intelligence` as an agent input** | Returns a **748 KB human-readable PDF** report, not machine-readable data. Took 217 s |
| **`persistence` analytic as a duration signal** | Returns values that **cannot be a duration**: negative (to −0.581 h), **non-monotone in threshold on 9.06 % of tiles**, and **47.9 % of tiles pile up at exactly 1.00 h**. Undefined in the spec |
| **Earth-2 / CorrDiff** | NIM needs ≥40 GB VRAM; the dev machine has **6 GB**. Its 3 km resolution is also far coarser than the ~200 m separations that matter |
| **RAPIDS** | No bottleneck it addresses. Including it would have been logo-driven |
| **Controlling the chiller plant directly** | Requires an *invented* plant response model — the exact `[S] plant stubs` mistake that collapsed §6.5. The agent commits setpoints and schedules; a human gate stays on physical actuation |
| **Fan-speed / exhaust-momentum control** | The one actuator the outdoor physics genuinely owns, and ASHRAE Handbook ch. 46 is the standards source — **but our `downwash_fraction()` depends on wind speed only, not discharge velocity, so it needs new calibrated physics.** Out of scope at day 11 of 13 |

---

## 7. What is verified — every number traceable

| Finding | Value |
|---|---|
| Solver vs analytic Gaussian plume | **2.9 × 10⁻¹⁰** relative error; heat conserved to **7.5 × 10⁻¹²** |
| External field validation | **67** Project Prairie Grass 1956 experiments; coefficients cross-checked vs EPA ISC3 |
| Magnitude, held out | fitted on 3 plants, scored on 3 unseen: **RMS 0.126 K on a 0.923 K signal (14 %)** |
| NVIDIA Warp GPU port | **93.46×** on a 100-member ensemble; CPU/GPU agreement **6.95 × 10⁻⁵ °C**. *Quote the lower repeat, 72.7×* |
| Emergent caution | ensemble spread **27.04×** wider at the geometric edge; **no coded plume rule** |
| Conformal bound, **simulated** days | 89.9–90.0 % at demo_site, 93.4 % at a second geometry — **⚠ SIMULATED, not live. Superseded for the forecast path by §8e** |
| **Conformal bound, LIVE FortyGuard forecasts** | 🔴 **65.6 % pooled, worst day 0.0 %** over 3 test days; **80.1 %** with the level anchored to one local observation. **Quote these, not 90 %** (§8e) |
| Live unattended self-scoring | Daily scheduled task, **4 complete pairs, 3 test days, verdict FAIL** — see §8e. Aug 14 and Aug 17 are permanent gaps (machine off) |
| Fault detection (supporting result) | removing weather cuts detection delay **79.7 → 0.03 days** (+75.6 σ); sequential evidence beats a threshold **57.5 → 2.67 days** (+52.6 σ) at matched false-alarm rate |
| **Free-cooling hours gained** | 🔴 **SUPERSEDED — read §8n.1 for the five-year ladder, which is what `audit.py` re-reads.** The current rows on **43,763 h / 1,826 days / 913 held out**: base **+65.6 h/yr** → **+85.6** with a switch budget and dwell limit → **+118.8** with the sourced dew-point gate → **+405.7** at 3 h notice and skill 0.50 → **−156.0 unanchored, where the agent LOSES.** The two claims retracted from the old wording: *"≈67 h/yr from RECIRCULATION AWARENESS ALONE"* (it is an **uncertainty asymmetry** — the same row reads 18.4 / 65.6 / 158.4 as sensor error goes 0.1 / 0.3 / 0.5 °C) and *"≈770 h/year"* (the ladder's own figure is **+405.7**, and **skill 0.50 remains an ASSUMPTION, not a measurement**). See `n56-freecooling-PREREG.md` |
| **What the plume model is worth** | **+22.8 safe h/yr AND 3.7× fewer breaches** — with the rise term: 17,511 free hours, 3 breaches, 0.17 per 1,000; without it: 17,462 and 11, 0.63 per 1,000. **Not a safety-for-hours trade.** The truth is always `T + rise`, so with the term the plume **cancels out of the conformal residual** (`(T+rise) − (fc+rise) = T − fc`); without it the 90th-percentile quantile must absorb the plume's whole spread, which charges every hour a worst case instead of its actual value. **Dropping the physics buys a WIDER bound, not a cheaper one.** ⚠ **The sign on this was inverted in the source until 2026-08-20 — HANDOFF §10 #97** |
| FortyGuard API characterisation | **16 defects**, including a **severe credential leak**: the caller's API key is embedded in a `download_link` URL path |

---

## 8. The demo — eight cases, each proving a different behaviour

| Case | What it proves |
|---|---|
| 1. Clear cool day | free cooling all day — baseline sanity |
| 2. Clear hot day | mechanical all day |
| 3. Crossing day | the schedule decision — where planning shows |
| 4. **Chatter day** | temperature hovers at changeover. A threshold rule switches repeatedly; the agent rides through within its switch budget |
| 5. **Recirculation-critical day** ⭐ | ambient sits *below* changeover but the plume is on the intake, so the *intake* is above. Run **with** and **without** recirculation side by side — opposite answers, and the outcome vindicates the recirculation-aware one |
| 6. **Knife-edge day** | bearing 285°: the ensemble disagrees with itself **27×** more than in safe sectors. The agent stays conservative **and says why** |
| 7. Safe-sector day | bearing 180°: recirculation is exactly **0.0000 °C** — the agent relaxes and *gains* hours |
| 8. Drift day | coverage degrades; the agent widens itself unprompted |

Plus the **wind dial**: sweep the bearing and watch the schedule flip as the plume swings onto the intake.
**Screen Zero is FortyGuard's own field** — 17,862 tiles from one call — so the sponsor's data is seen
doing work before any of ours is.

---

## 8b. Build log — real geometry, 2026-08-16

**Kept as a running record of what changed, what was assumed, and what went wrong.**

### 8b.1 The site, chosen on physics rather than size

> **⚠ SUPERSEDED 2026-08-18 — this subsection is the historical build log of the FIRST site.** The pair
> below (`852039781` / `793087859`, 47.9 m gap) was **replaced** after N-54 measured 100 % of downwind
> bearings refused there. **The committed site is AWS IAD116 / IAD117 — see §8f.9.** Kept unedited because
> the errors found and fixed here (§8b.2–8b.4) are what made the later work possible.

Ranking candidate pairs by floor area picks whatever is biggest, which says nothing about whether the
plume ever reaches the neighbour. So pairs were scored by **wind exposure × dilution** over **449 real
KIAD observations**: 391 data-centre pairs qualified after filtering out non-data-centres (a shopping
mall passed the size filter and had to be excluded by name).

| | |
|---|---|
| Source | OSM way `852039781` — rotated rect **190 × 62 m at 52.9°**, 11,796 m² |
| Receptor | OSM way `793087859` — rotated rect **158 × 62 m at 154.0°**, 9,804 m² |
| Centre-to-centre | 141 m |
| **True facade-to-facade gap** | **47.9 m** |
| Receptor bearing from source | 23.7° |
| Critical wind | **FROM 203.7°** — which is the *prevailing* bearing at KIAD (210–215° is 6.7 %, 220–225 % 6.2 %) |
| **Hours exposed** | **20.3 %** of observed hours fall inside the 40° plume sector |

**⚠ Naming decision, deliberately left open.** This original pair was two adjacent halls tagged in OSM as
Amazon **IAD119 / IAD118**; the **committed** pair (§8f.9) is Amazon Web Services **IAD116 / IAD117**
(`744496750` / `744496741`). Either way the concern is identical. Everything claimed is a *physical*
statement about geometry and wind — recirculation is normal and universal — but in a public demo it could
read as an accusation. **Recommendation: name it generically in the demo and video ("a real hyperscale
campus in Ashburn — OSM ways 744496750 and 744496741") and keep the real names in the data files for
reproducibility.** The same courtesy applies to the **vetoed** Digital Realty pair: the ROOFTOP verdict in
`architecture_verdicts.json` is an observation about imagery, **not** a criticism of anyone's engineering.

### 8b.2 Three errors found and fixed in our own new code

| # | What was wrong | How it surfaced | Fix |
|---|---|---|---|
| 1 | Footprints described by their **axis-aligned bounding box** | The bboxes **overlapped by 28 m** at the real 141 m separation, which would have placed two **interpenetrating** buildings. Measured **fill ratios of 0.38 and 0.46** exposed it: the halls are *rotated*, so a bbox is a bad descriptor | Save the raw polygon **rings** plus a **rotated minimum-area rectangle** (fill ratio **0.99** for both). `fetch_geometry.py` re-run |
| 2 | Bank placed on the **furthest vertex** of the ring | A vertex of a rotated hall is a **corner**, so a 152 m strip centred there extended outside the building toward the receptor. **`solver.assert_intake_clear` refused to write the site** — 4 % of the intake disc landed on source cells | Place on the facing **edge** (facade), not the vertex |
| 3 | "Facade gap" computed **vertex-to-vertex** (58.6 m) | Overstated the real clearance | True **edge-to-edge** segment distance: **47.9 m** |

**The refusal in #2 is worth noting on its own: an existing guard caught a new bug before it could
produce a number.** That is what the guard was for.

### 8b.3 A polygon rasteriser, and why it is verified rather than trusted

`solver.Site.add_building()` only places axis-aligned rectangles, so the real rings are rasterised by
even-odd ray casting on cell centres. **This is new code touching the physics, so `build_site.py`
refuses to write a site unless three checks pass:**

| Check | Result |
|---|---|
| **V1** rasterised axis-aligned rectangle vs `add_building` | **PASS — 0 cells differ** (tolerance was one perimeter layer, 68 cells) |
| **V2** rasterised area vs analytic polygon area | PASS — source 11,700 vs 11,800 m²; receptor 9,800 vs 9,806 m² |
| **V3** the two buildings share no cell | PASS — 0 overlapping cells |

### 8b.4 ⚠ The condenser-bank placement problem, and why BOTH are built

The rule *"put the bank on the facade facing the receptor"* is self-consistent but **physically wrong at
this pair.** The source's long axis is 52.9° and the receptor sits at 23.7° — only ~29° apart — so **the
receptor lies off the END of a 190 m hall.** The receptor-facing facade is therefore only **37 m** long,
and a bank on it is **600 m², twelve times smaller than the validated reference's 7,200 m².** Condenser
rows do not go on a 37 m end wall; they go along a long facade or on the roof.

**Neither placement is chosen for us. Both are built and both will be swept, and the RANGE is reported.**

| `BANK_MODE` | Facade | Bank | Rationale |
|---|---|---|---|
| **`longest`** (primary) | **189 m** | **151 × 20 m, 3,000 m²** | Physically realistic: condenser rows sit along a long facade |
| `facing` (sensitivity) | 37 m | 30 × 20 m, 600 m² | Aims the plume straight at the receptor, but on an implausibly small facade |

**Consequence that must not be glossed over: with the bank on a long facade, the worst wind bearing is no
longer the source→receptor bearing.** It becomes a joint function of bank position *and* receptor
position, so **the critical bearing has to be found by the direction sweep rather than assumed.** The
"critical wind FROM 203.7°" figure in §8b.1 is the *centre-to-centre* bearing and is only the worst case
under `BANK_MODE=facing`.

### 8b.5 ⚠ Two known defects carried into this work, both flagged not fixed

1. **`solver.py` implements buildings as fixed-temperature cells that ABSORB heat rather than deflect
   it.** N-29 measured this directly: a building across an otherwise verified Gaussian plume removed
   **99.7 %** of the heat against 100.0 % conserved in the open domain. The reference layout was
   unaffected because its source-to-intake path is clear. **At a 47.9 m gap between two long rotated
   halls, far more bearings will have a building in the path.** `solver.path_blocked()` exists precisely
   for this and makes the agent **refuse** to report a number on those bearings — citing ASHRAE Ch. 46's
   hidden-intake case. **Those refusals are load-bearing here, not a formality, and the fraction of the
   compass they cover must be reported as part of the result.**
2. **The 2 m measurement height versus the true intake height is unmodelled** — see
   `docs/GEOMETRY-AND-PHYSICS.md` §2. Uncovered by any test in the project until 2026-08-16.

### 8b.6 Every assumption introduced by this step

| Assumption | Value | Why |
|---|---|---|
| Bank position | on a source facade | **not mapped in OSM anywhere** |
| Bank facade fraction | 0.80 | ✏️ our choice |
| Bank depth | 20 m | ✏️ our choice |
| Intake position | receptor facade facing the source, **20 m** standoff | not mapped; standoff raised from 15 m because `assert_intake_clear` rejected 15 m |
| Intake averaging radius | 30 m | unchanged from all prior work |
| `discharge_k`, `exchange_s` | 11 K, calibrated 47.4 s | **strength per unit area unchanged from the validated reference**, so total heat follows the real footprint — correct, since a differently sized facility releases different heat |
| Building height | ❓ absent from OSM | irrelevant to a 2-D solver, central to the 2 m gap |
| Domain, grid | 2000 m, dx = 10 m | unchanged, so results stay comparable to every prior validated number |

---

## 8d. SCOPE — which sites this applies to, settled by imagery (2026-08-18)

> **⚠ RE-VERIFIED 2026-08-18 ON A DIFFERENT SITE.** This section was originally written from imagery of
> the AWS **IAD119 / IAD118** pair. That pair was **replaced** after N-54 measured 100 % of downwind
> bearings refused there (§8f). The committed site is now **AWS IAD116 / IAD117
> (`744496750` / `744496741`)**, site centre **39.024017, −77.419691**.
>
> **The scope statement below still holds, on FRESH evidence, not inherited evidence:** new USGS and ESRI
> imagery of IAD116 / IAD117 shows the same architecture — mostly-bare roofs with two rows of small
> regularly-spaced units, and **a long row of large units at GRADE in the gap between the halls.**
> Recorded per candidate in `data/geometry/architecture_verdicts.json`.
>
> **This was not automatic.** The site that ranked FIRST on measured physics (Digital Realty IAD35 /
> IAD36) is **rooftop-cooled and was vetoed** precisely to keep this section true — see §8f.8.

**The 2 m question is resolved for this site, and it resolved favourably.** Rather than exclude
architectures we cannot validate, the scope is now a positive, evidence-backed statement.

### 8d.1 How it was settled — free, keyless, reproducible

1. **Full OSM tag query** (Overpass) for both ways. Result: `building=data_center`,
   `telecom=data_center`, `operator=Amazon Web Services`, addresses **21645 and 21641 Charles View
   Drive, Sterling VA** — and **no `height` or `building:levels` tag on either**, confirming OSM cannot
   supply height.
2. **Public aerial imagery** via the ArcGIS REST `export` endpoint, from **two independent sources with
   different capture seasons**: [USGS The National Map `USGSImageryOnly`](https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer)
   (US federal, **public domain**) and ESRI World Imagery as a cross-check. Fetcher:
   `src/fetch_imagery.py`. Images: `data/imagery/{usgs,esri}_{wide,tight}.png`.

### 8d.2 What the imagery shows — both sources agree

**High confidence** (clear shadows, outside the roof outline, regular spacing, visible in both sources):

> **A row of large modular units at GRADE along the long facade of each hall** — roughly 8–12 per
> building, sitting on the apron immediately alongside the wall, **not on the roof.**

Also visible in both: **a line of small, regularly-spaced units ON the roof** running the hall's length —
small relative to the roof, consistent with **exhaust fans or relief vents**, not chillers. Plus **a row
of circular tanks** at the building ends (~6–9 each), consistent with water storage for
evaporative/adiabatic assist; a large electrical substation to the west; stormwater retention ponds.

**This matches the published description of this operator's architecture** — *"exhaust fans on the roof,
and louvers to let the exterior air in"* ([SemiAnalysis, Datacenter Anatomy Part 2](https://newsletter.semianalysis.com/p/datacenter-anatomy-part-2-cooling-systems))
— with the intake side realised as ground-level air-handling modules along the facade.

### 8d.3 Why this is the ideal outcome

| Observation | Consequence |
|---|---|
| **Air intake is at GRADE** | **FortyGuard's 2 m plane is the plane the equipment actually breathes.** No vertical correction. No unvalidated term. The height problem dissolves for this site |
| **Exhaust is on the ROOF** | The plume is released *high* and reaches a *low* intake only by being bent down — **precisely our field-calibrated downwash term** (exponent **1.25**, u_c **8.0 m/s**, fitted to ~40,000 measured points across six instrumented condensers) |
| **Recirculation path** | neighbour's **roof exhaust → downwash → our ground-level intake.** The downwash physics becomes the centrepiece, grounded in observed architecture rather than assumed |

### 8d.4 The scope statement

> **INTAKE-ARBITER applies to facilities whose cooling equipment draws air within a few metres of grade
> — ground-level air-handling modules, air-cooled chiller and condenser yards, cooling towers.** For
> those, **FortyGuard's 2 m field is the correct measurement plane and no vertical correction is
> applied.** For intakes higher up a facade or on a roof, the agent **requires the customer's own intake
> sensor** to calibrate the offset, and **reports that it is outside its validated envelope** until that
> data exists.

**Deployment guard:** once a customer sensor exists, if residuals show a persistent offset inconsistent
with ground-level equipment, the agent **says so** rather than silently correcting.

### 8d.5 What is NOT claimed

**At ~0.3–0.5 m imagery resolution we can see objects, not nameplates.** We cannot certify these are air
handlers rather than air-cooled condensers or chillers, and we cannot measure heights. The honest
statement is *"the visible cooling plant is at grade along the long facades, with small roof-mounted
units consistent with exhaust"* — corroborated by two independent imagery sources and a published
description of this operator's architecture, **not a site survey.** A street-level view along Charles
View Drive, or Loudoun County's public site plans, would upgrade it.

**On prevalence, we could not establish a majority either way.** The [Uptime Institute Cooling Systems
Survey 2025](https://intelligence.uptimeinstitute.com/sites/default/files/2025-07/UI%20Field%20181_Data%20center%20cooling.pdf)
(April–June 2025, 1,033 respondents) reports heat-rejection **type** — *air-cooled chillers 35 %,
evaporative cooling towers 22 %, other 19 %, DX/air conditioners 11 %, fluid/dry coolers 6 %, fresh air
4 %, adiabatic 3 %* (n=400) — **but nobody surveys equipment PLACEMENT**, and rooftop chillers occur even
at 48 MW scale. So the scope is stated as a *requirement on the site*, not as a claim about the market.

---

## 8e. 🔴 THE CONFORMAL BOUND DOES NOT HOLD 90 % ON LIVE FORECASTS (2026-08-18)

**This supersedes every "90 %" claim in this document. It is the most important measured result in the
project and it is negative.**

`test_n26_coverage.py` reached its pre-registered 3-test-day condition and **FAILED**:

| Condition | Verdict | |
|---|---|---|
| P1 pooled coverage ≥ 85 % | ❌ | **65.6 %** |
| P2 no test day < 60 % | ❌ | **worst day 0.0 %** |
| P3 ≥ 3 test days | ✅ | 3 |

### 8e.1 The diagnosis — three candidates, two eliminated

| Candidate | Verdict |
|---|---|
| **Our comparison** | ❌ **Ruled out.** Both legs use the *same* `call_window()` payload — identical `tcm`, granularity, AOI, window. Only the issue time differs |
| **FortyGuard's history** | ❌ **Not the problem, and it looks good.** Against KIAD ASOS it sits **+0.86…+1.92 °C** — consistent with urban heat island over a data-centre corridor, and **smallest on the coolest day.** On 16 Aug the real day was 5 °C cooler; **their history caught it (26.97 vs 26.11 station), their forecast did not (30.69)** |
| **FortyGuard's forecast LEVEL** | ✅ **This is it.** A **spatially uniform, day-varying** offset: day-means **−0.84, −0.81, +0.15, −3.71 °C** while the within-day sd across 17,862 tiles is only **0.06–0.29 °C** |

### 8e.2 Shortening the lead is NOT the fix — my proposal, and it was wrong

Five leads of the same window, already paid for (`diag52_leadlevel.py`):

| Lead | 9.41 h | 7.49 h | 5.49 h | 3.49 h | **1.49 h** |
|---|---|---|---|---|---|
| offset | −0.8396 | −1.0850 | −0.8846 | −1.1787 | **−1.0177 °C** |

**At 1.5 h lead the offset is still ~1 °C**, where persistence alone would be near-perfect. So it is not
forecast skill — it reads as a systematic level difference between the forecast and history pipelines.

### 8e.3 Anchoring the level helps substantially but does not reach 90 %

`diag53_anchored.py` — remove each day's mean offset, i.e. let **one in-AOI observation set the level and
FortyGuard set the shape**, then re-run the identical sequential protocol:

| Test day | unanchored | **anchored** | that day's within-day sd |
|---|---|---|---|
| 2026-08-13 | 96.8 % | **97.4 %** | 0.0699 |
| 2026-08-15 | **0.0 %** | **89.9 %** | 0.0644 |
| 2026-08-16 | 100.0 % | **52.8 %** | **0.2903** |
| **pooled** | **65.6 %** | **80.1 %** | |

*(Control check passed: unanchored reproduces N-26's failure, so the script is sound.)*

**Two error terms, not one:** the **level offset** is dominant and anchoring removes it — the
catastrophic 0.0 % day becomes 89.9 %. But **the spatial spread itself varies 4.5×** (0.0644 → 0.2903),
which anchoring cannot touch, and that is why 16 August still fails. **Both blew up on the same day: the
one where the forecast missed a real 5 °C cooling event. The bound holds on ordinary days and fails on
the day the forecast breaks down.**

### 8e.4 What we may and may not say

- ❌ **Do NOT say "90 %", "89.9–90.0 %", or "verifiably right 9 times out of 10" about the forecast path.**
  Those figures came from **simulated** days (N-46, N-49), not live FortyGuard forecasts.
- ✅ **Say the measured rate:** *"out-of-sample coverage measured **65.6 %** as shipped and **80.1 %** with
  the level anchored to one local observation, over 3 test days — and here is the mechanism."*
- ✅ **This does NOT touch the detection result (N-49)**, which is a hindcast on *observed* data, so
  forecast drift does not enter.
- ⚠️ **n = 3 test days.** This establishes the *mechanism* decisively; it does not establish a *rate*.
- ✅ **Anchoring makes the customer's sensor a REQUIRED input, not an optional examiner.** That is a real
  change to the dependency list and belongs in the pitch.

### 8e.5 The finding is written up for FortyGuard

`fortyguard-api-findings.md` §7 now carries the full reproducible account plus two prioritised requests:
**(1) a per-request forecast uncertainty indicator** — *"on 16 August your forecast was 3.7 °C off in
level and 4.5× wider in spatial spread than normal; had either been exposed, our agent would have widened
and kept its 90 % promise"* — and **(2) forecast verification access**, since measuring skill currently
costs a client two paid calls per site per day.

---

## 8f. 🔴 N-54 THE REFUSAL SURFACE — the selected site cannot demonstrate recirculation (2026-08-18)

**`src/direction_sweep.py`, 72 bearings x 2 bank modes, CPU, no API call. Pre-registered P1–P5 in that
file's docstring, written before the first run. Results in `data/geometry/direction_table.json`.**

**Verdict: P1 FAILED, P3 PASSED, P2 passed but is VACUOUS in the primary mode and PASSES where it is
meaningful. Reported as a failure, not re-defined.**

### 8f.1 An artefact caught before it became a headline

`build_site.py` places the condenser bank as a strip **inside** the source hall, so **all 30 bank cells
are also obstacle cells.** A ray starting at the bank *centroid* therefore begins inside a building, and
`solver.path_blocked()` returns True for **36 of 36 downwind bearings — 100 % refusal.** Measured and
confirmed before the sweep was written.

**That number is an artefact of where the ray starts, not physics.** A real condenser bank discharges at
the **facade**, so the emission point is the facade midpoint marched outward along the outward normal
until it clears the obstacle mask — 30 m for `longest`, 15 m for `facing`. The script prints the emission
point so the choice is auditable, and raises rather than continuing if it cannot clear.

### 8f.2 The geometric fact that decided everything

**Both ~189 m facades of the source hall face AWAY from the receptor:** outward·û = **−0.896** and
**−0.660**. The receptor lies off the **end** of the hall, so its only receptor-facing facade is the
**37 m end wall.** A *"long AND facing"* bank mode **cannot exist at this site.**

### 8f.3 The measured refusal surface

| | `longest` (189 m facade, 3,000 m², primary) | `facing` (37 m end wall, 600 m², sensitivity) |
|---|---|---|
| Emission point | (906.8, 899.5), marched 30 m | (1000.3, 989.9), marched 15 m |
| Refused, all bearings | **36 of 72 = 50.0 %** | 0 of 72 = 0.0 % |
| **Refused / downwind** | **36 of 36 = 100.0 %** | 0 of 36 = 0.0 % |
| Contiguous refused arcs | **1** | 0 |
| Worst bearing | *none exists* | **165°**, rise **0.1621 °C** |
| Rise range on solved bearings | 0.00004–0.00897 °C (all upwind) | 0.00018–0.16207 °C |

**Wind-weighted over 34,200 real non-calm KIAD hours** (5 years; **7,728 calm hours excluded** because
bearing is undefined at `sknt = 0`, and 1,835 missing), 95 % Wilson intervals:

| Subset | Hours | Refused | Fraction | 95 % CI |
|---|---|---|---|---|
| all hours | 34,200 | 17,171 | **50.2 %** | [0.497, 0.507] |
| below 18 °C | 20,028 | 8,761 | 43.7 % | [0.431, 0.444] |
| below 21 °C | 23,301 | 10,399 | 44.6 % | [0.440, 0.453] |
| below 24 °C | 27,723 | 12,938 | 46.7 % | [0.461, 0.473] |
| below 27 °C | 30,630 | 14,743 | 48.1 % | [0.476, 0.487] |

*Changeover limits are SCENARIO parameters, not agent decisions; all four are reported so no single value
is load-bearing.*

### 8f.4 The verdicts, stated as they fell

- **P1 non-degenerate refusal — ❌ FAILED.** Refusal is 100.0 % of downwind bearings under `longest`.
  Pre-registration named that extreme a failure in advance, and it is recorded as one.
- **P2 naive bearing is wrong — ⚠️ met arithmetically, VACUOUS under `longest`.** With every downwind
  bearing refused, the argmax runs over **upwind** bearings whose rise is ~0.009 °C, i.e. **noise**.
  The condition was **not re-defined**; it is reported as met *and* worthless, and then re-evaluated
  where it is meaningful. **Under `facing` it PASSES: worst 165° vs the naive 203.7°, |Δ| = 38.7°.**
  **So §8b.4's warning is vindicated** — even in the mode where the naive answer is most expected, the
  worst bearing is 38.7° away from the source→receptor line.
- **P3 geometric coherence — ✅ PASSED.** Exactly **1** contiguous refused arc. Blockage varies smoothly
  with bearing, so the ray-casting is behaving; scattered singletons would have indicated a bug.

### 8f.5 What this means, honestly

**The refusal mechanism works, and is doing real work.** Half of all wind hours are correctly declared
not-computable rather than answered wrongly. That is the guard from gotcha #26 behaving exactly as
designed, and it is a genuine agentic behaviour: **the agent declines rather than guessing.**

**But at this site the realistic configuration yields NO usable recirculation signal at all.** 100 % of
plume-carrying bearings refused means the recirculation term contributes nothing, so the agent's decisions
collapse back to ambient forecasting alone — **removing the physics differentiator that is this project's
core technical claim.**

**And the one mode that does produce a number produces a small one: peak 0.1621 °C.** For context,
**ASOS temperatures sit on a 0.556 °C grid** (gotcha #24), so this peak is *below the resolution of the
station data* — validation would have to come from elsewhere.

**Why refusal is the right behaviour even so:** obstacles are transparent to the temperature field, so a
blocked path silently returns the *unobstructed* answer, which is too HIGH. Concretely, the naive 203.7°
bearing under `longest` returns **0.5386 °C** from the bank centroid — a number the geometry cannot
support. Refusing is what stops that from being published. ASHRAE Ch. 46 calls this the HIDDEN-intake case
and applies a conservative dilution factor of 2.0; a mass-consistent wind field validated against CEDVAL
could replace the refusal with a number, and that is future work, not a claim.

### 8f.6 A better site exists — surveyed, not assumed

Before recommending anything, all **611 candidate pairs** were surveyed for plume-path clearance
(`data/geometry/path_clearance_survey.json`; free, keyless, from data already on disk). Criterion: take
the source's **longest** facade — where a real bank goes — and dot its outward normal with the unit vector
toward the receptor.

- **292 of 611 pairs (47.8 %) point their long facade AT the receptor.** Better sites are abundant.
- **The selected pair scores −0.660. Only 28.6 % of pairs point further away** — we picked one of the
  worse ones for plume path, because selection optimised **wind exposure × dilution** and never asked
  whether the plume could travel in a straight line.
- **258 of the 292 also have a ≥100 m longest facade**, so a realistic bank size and a clear path coexist.
- **0 pairs have both a facing long facade and centre-to-centre ≤ 120 m** — a real trade-off, worth stating.

**Top candidates, with TRUE edge-to-edge gaps computed via `ring_gap()`:**

| Source → receptor | outward·û | Longest facade | Centre-to-centre | **True gap** | Name |
|---|---|---|---|---|---|
| **300162674 → 300162675** | **+1.000** | 123 m | 135 m | **25.5 m** | Digital Realty ACC5 |
| 794147655 → 1443187163 | +1.000 | 149 m | 211 m | 29.4 m | CloudHQ LC2 |
| 1088241982 → 300967252 | +0.984 | 135 m | 128 m | 30.4 m | — |
| 794147654 → 794147655 | +0.984 | **339 m** | 225 m | 33.1 m | CloudHQ LC1 |
| *current site* | *−0.660* | *189 m* | *141 m* | *47.9 m* | *(two Amazon halls)* |

**⚠ Exclude gap = 0.0 m pairs.** `701924665 → 985207884` (Vantage VA11) scores +0.994 with a 146 m facade
but its footprints **touch** — adjoining or double-mapped halls, not a source/receptor pair. A minimum-gap
filter is needed in `select_site.py`; there is none today.

**Digital Realty ACC5 beats the current site on all three axes that matter here:** plume path clear
(+1.000 vs −0.660), **tighter** gap (25.5 m vs 47.9 m, so a *stronger* recirculation signal), and a
realistic 123 m facade.

### 8f.7 ✅ RESOLVED — the site WAS re-selected, 2026-08-18. Three stages, and the third vetoed the first

The user approved the switch. What was built is **not** the ACC5 pair recommended in §8f.6 — two checks
made after that recommendation ruled it out, and both are worth recording.

**Check 1: the intake measurement operator sets a hard minimum gap, and ACC5 fails it.** The intake disc
is centred `INTAKE_STANDOFF_M` (20 m) outside the receptor facade with radius `INTAKE_RADIUS_M` (30 m), so
it reaches **50 m** toward the source. **ACC5's gap is 25.5 m**, so the disc would have spanned the whole
gap and sat inside the source hall — measuring the neighbour's *wall*, not the air anyone breathes. The
recommendation in §8f.6 ranked on clearance, facade and gap and **never checked the operator**. Gap is now
a derived gate: `MIN_GAP_M = INTAKE_STANDOFF_M + INTAKE_RADIUS_M`, imported from `build_site.py` so the
two files cannot drift.

*Measured, so the bound is not arithmetic alone:* at the old site's 47.9 m gap the disc holds 26 cells,
3 (11.5 %) inside the receptor hall and **0** inside the source hall — so 50 m is **conservative** at
dx = 10 m, because the gap is a minimum over the whole footprint while the intake sits at a facade
midpoint. Kept conservative deliberately; `build_site.verify()` and `solver.assert_intake_clear()` remain
the real arbiters.

**Check 2: a boolean clearance gate is not enough — 56 of 145 survivors still refuse everything.**

| Stage | What it does | Result |
|---|---|---|
| 1. `select_site.py` | gates: data-centre pair · gap > 50 m · **longest facade faces receptor** · facade ≥ 100 m; then exposure × dilution | **611 → 145** |
| 2. `refusal_rank.py` | **MEASURES** each survivor's refusal surface (`path_blocked()` is pure geometry, no PDE solve) and ranks by `exposure × dilution × (1 − wind_weighted_refusal)` | **56 of 145 still refuse 100 % of downwind bearings**; 89 fully clear |
| 3. `commit_site.py` | **architecture SCOPE GATE**, with **veto power** over the ranking | **vetoed rank 1** |

**Stage 1's funnel:** 220 not a data-centre pair · 2 touching footprints (gap = 0) · 38 gap < 50 m ·
**199 longest facade faces away** · 7 facade < 100 m → **145 survived**.

Stage 1's own top pick, `1544360250 → 1534356804`, has clearance **+0.144** — a facade normal ~82° off the
receptor — and **measures 100 % of downwind bearings refused.** A boolean gate cannot tell +0.144 from
+0.99. Worse, `597970811 → 597970813` has clearance **+0.988** and *also* refuses 100 %, so **clearance is
not even a reliable proxy.** Measuring was not optional.

### 8f.8 🔴 The scope gate CONFLICTED with the physics ranking, and scope won

Stage 2's winner was **`597970809 → 597970806`, Digital Realty Northern Virginia IAD35 / IAD36** — usable
exposure **0.3172**, **0.0 % refused**, gap 69.1 m. It built and verified cleanly and swept cleanly.

**Then the imagery was actually looked at, and it is ROOFTOP-cooled.** Both ESRI (winter) and USGS
(summer) show the roofs of both halls **densely covered in large regular arrays of rectangular units
across essentially the whole roof area.** §8d puts rooftop intakes **explicitly out of scope**, because the
2 m-to-roof offset cannot be validated.

**So optimising for plume-path physics had broken the scope premise that §8d rests on.** Committing on
stages 1–2 alone would have based the scope statement on a site that violates it. The architecture gate
was therefore added **last and given veto power**: physics decides the *ordering*, scope decides
*eligibility*. Verdicts live in `data/geometry/architecture_verdicts.json`, per candidate, with evidence,
cross-checked across two sources with different capture seasons, and are a **human judgement** — at
0.3–0.5 m we see objects, not nameplates.

### 8f.9 The committed site — AWS IAD116 / IAD117

**`744496750 → 744496741`, Amazon Web Services IAD116 → IAD117.** Rank **2** on measured physics; rank 1
vetoed.

| | |
|---|---|
Source | OSM `744496750` — rotated rect **153 × 62 m at 84.6°**, 9,526 m² |
Receptor | OSM `744496741` — rotated rect **155 × 62 m at 84.4°**, 9,509 m² |
Centre-to-centre | 165.5 m |
**True facade-to-facade gap** | **60.3 m** (edge-to-edge; clears the 50 m operator bound) |
Longest facade / clearance | **153.2 m**, outward·û **+0.737** |
Critical wind (naive) | FROM 317.9°; receptor at bearing 137.9° |
Site centre | **39.024017, −77.419691** |
Bank, `longest` | **123 × 20 m, 26 cells, 2,600 m²** — realistic condenser row |
Bank, `facing` | 50 × 20 m, 10 cells, 1,000 m² — a **genuine** sensitivity here, not degenerate |
Verification | V1 **0 cells differ** · V2 9,400 vs 9,534 m² and 9,400 vs 9,513 m² · V3 **0 overlap** · intake clear **PASS** |

**Architecture, both sources agreeing:** roofs **largely bare** but for two rows of small regularly-spaced
units per hall (consistent with **exhaust fans**); **a long row of large rectangular units at GRADE running
most of the gap between the halls**, distinct shadows, clearly outside the roof outlines; large cylindrical
tanks (consistent with water storage) at the hall ends. This matches the published description of this
operator's architecture — *"exhaust fans on the roof, and louvers to let the exterior air in."*
**§8d holds here, on fresh evidence rather than inherited evidence.**

**And the grade-level equipment sits IN THE GAP — exactly where the modelled plume path runs.**

**N-54 re-run on the committed site:**

| | `longest` (2,600 m², primary) | `facing` (1,000 m², sensitivity) |
|---|---|---|
Refused / downwind | **0 of 36 = 0.0 %** | 36 of 36 = 100.0 % |
Wind-weighted refusal | **0.0 %** | **63.1 %** [0.626, 0.636] |
Downwind bearings solved | **36 of 36** | 0 of 36 |
**Critical bearing** | **255°, rise 0.3548 °C** | *none exists* |
vs naive 203.7° | **\|Δ\| = 51.3°** | — |

**The agent can now answer on 100 % of plume-carrying hours in the realistic configuration**, against
0 % at the original site. And **§8b.4's warning is confirmed a third time**: the critical bearing is
**51.3° away** from the naive source→receptor line.

**The `facing` sensitivity is informative rather than degenerate:** a bank on the 62 m end wall refuses
**63.1 %** of real wind hours, which is the honest statement that *where you put the condensers decides
whether the neighbour is reachable at all.*

⚠ **Still below the station quantum.** 0.3548 °C sits under the **0.556 °C** ASOS grid (gotcha #24), so
ASOS cannot validate this magnitude. Larger than the old site's 0.1621 °C, but the caveat stands.

### 8f.10 What P1's second failure means, and what was NOT done about it

At the committed site N-54's **P1 FAILS AGAIN — 0.0 % refused, the opposite extreme from the original
100 %.** That is the *intended consequence* of selecting for a clear path. P1 conflated two questions:
*does `path_blocked` fire?* (code correctness) and *is this site clear?* (site suitability).

**No replacement pass/fail conditions were registered, because the numbers had already been seen** and
inventing them then would be exactly the post-hoc threshold-moving methodology rule 2 forbids. The
committed site's figures are reported as **measurements, not passes**. The amendment is written into
`direction_sweep.py`'s docstring; P1–P5 themselves are **unedited**.

**Positive control that `path_blocked` is not silently broken:** 36/36 refused at the original site's
`longest` mode, **36/36 at the committed site's `facing` mode**, and **56 of 145** pairs in
`refusal_rank.py`. The function fires. 0 % is a property of the committed geometry, not of the code.

### 8f.11 ⚠ Superseded, kept visible

- **§8f.6's ACC5 recommendation is withdrawn** — it fails the 50 m intake-disc bound at 25.5 m.
- **Digital Realty IAD35 / IAD36 was built, verified and swept, then vetoed** as rooftop-cooled. Its
  artefacts were overwritten; the verdict and evidence are in `architecture_verdicts.json`.
- **Six of the eight screened candidates remain NOT ASSESSED** for architecture, recorded as such rather
  than assumed. **No claim is made that all AWS halls are grade-cooled or all Digital Realty halls are
  rooftop-cooled** — two pairs were assessed.

### 8f.12 ⚠ Decision that was the user's, and was taken

**Re-selecting the site was not a parameter tweak, which is why it was put to the user rather than done
quietly.** It invalidated the site-specific imagery evidence in **§8d** (then 21645 / 21641 Charles View
Drive) on which the **scope statement rests**, so the new site needed its own free imagery check before
§8d could be re-asserted.

**The user approved it, and that check was done** — fresh USGS and ESRI frames of the committed pair, plus
the eight-candidate screen that produced the veto in §8f.8. **§8d now rests on evidence for the site
actually modelled**, and carries a banner saying so. **The original N-54 result stands as measured
(§8f.3–8f.4); it is what forced the switch.**

### 8f.13 A modelling tension this exposed, recorded for honesty

`README.md` frames the hazard as *"their own hot exhaust blowing back onto their own air intake"* —
**self**-recirculation — while the built site models **source hall → the NEIGHBOUR's intake.** These are
different problems. §8d established intake at grade with **exhaust on the roof** — and the committed AWS
IAD116 / IAD117 pair shows exactly that again (§8f.9) — so self-recirculation is roof-exhaust → downwash →
own ground intake **on the same building**, which a 2-D solver cannot represent as an over-the-roof path.
**Not resolved. Flagged so it is not discovered later as a surprise.**

**The site switch sharpened this rather than fixing it.** At the committed pair the grade-level equipment
row sits **in the gap between the two halls**, so the *neighbour* path we model is well posed and now fully
computable (0 % refused). The *self* path still is not, and any claim about a facility's own exhaust
returning to its own intake remains outside what this solver can support.

---

## 8g. ✅ THE AGENT LOOP EXISTS AS ONE PROGRAM — `src/agent.py`, 2026-08-18

`src/agent.py`, ~1,200 lines, **zero API calls, 13 s end to end.** It supersedes
`testing/run_e2e.py` and is what the demo reads. Three commands: `run` (everything, writes
`demo/trace.json`), `cycle` (the real FortyGuard loops only), `cases` (the scheduling sweep only).

### 8g.1 What it replaces, and why `run_e2e.py` could not be shipped

| `run_e2e.py` | `agent.py` |
|---|---|
| `solver.demo_site()`, a synthetic layout | the **committed AWS IAD116/IAD117 geometry**, V1/V2/V3-verified |
| **`THRESHOLD_C = 33.0`** hard-coded | **no changeover temperature in the source at all** — swept 18/21/24/27 °C |
| needed invented cost weights (`c_excursion = 120.0`) | **constrained maximisation, no cost weights exist** |
| single frozen clock | 4 real FortyGuard day-pairs + 7 real KIAD days |

**The decision is posed as: maximise free-cooling hours subject to (a) the upper bound on intake
staying under the plant limit, (b) at most `switch_budget` mode changes, (c) every completed run at
least `min_dwell_h` long.** A constrained form needs no exchange rate between risk and chiller-hours,
so there is no invented penalty constant to point at. Solved by DP over
`(mode, switches_used, dwell_owed)`.

**Point-at-the-constant audit.** The only constants left that change a decision are `ALPHA = 0.10`
(the confidence level — a definition) and `physics/solver.py:CALIBRATED`, which was **fitted to
~40,000 measured points** and validated held-out at 0.126 K RMS. Everything else sits in
`PLANT_ENVELOPE` and is swept: **40,320 scenarios**, all shipped in `demo/scenarios.json`.

### 8g.2 It reproduces N-26 exactly — the cross-check that matters

Per-day coverage **96.8 % / 0.0 % / 100.0 %**, pooled **65.6 %**, `pooled_coverage`
0.655898928824693 — identical to `testing/test_n26_coverage.py`. Two independently written
implementations agreeing is the only reason to believe either.

**It also shows the recalibrate step as a measured trajectory:** after the 08-15 miss the bound moved
**−0.7394 → +0.1905 °C on its own.** No human widened it. That line *is* the self-calibration.

### 8g.3 🔴 FOUR ERRORS OF MY OWN, FOUND AND FIXED WHILE BUILDING IT

1. **The arithmetic ceiling was computed on TILES, not DAYS.** Pooling 3 days gives 53,586
   residuals, so `n/(n+1)` read **99.998 %** — nonsense, and it would have destroyed the HANDOFF §7.2
   argument. DIAG-57 measured the field *shifting together* (~1.2 °C whole-map offset vs ~0.1 °C
   between-tile scatter, 3–12×), so one day's tiles are nearly **one** observation. The ceiling is
   `n_days/(n_days+1)`: **75 % at 3 days, 80 % at 4, 90 % first reachable at 9.** Now computed by
   `day_level_ceiling()` with the reasoning in its docstring.
2. **A SHAPE ORACLE, the mirror image of gotcha #40.** The unanchored agent's forecast was
   `truth − constant_offset`, so it got the hour-to-hour profile **exactly right** for free. Removing
   it — by making forecast skill a real swept axis on *both* anchor branches — cost the agent
   **~0.8 h/day**, turning `anchor=none` from +0.272 to **−0.551 ± 0.069 h/day.** Free information
   dressed as a measurement, and it flattered us.
3. **I misattributed the cause before tabulating the axes — gotcha #35, again.** I wrote "unanchored,
   the agent LOSES" into the output before checking `bank_mode`. The loss is driven by **`facing`**
   (−8.338 h/day), where `path_blocked()` refuses **36 of 36 downwind bearings**. Corrected: bank
   placement dominates every other axis, `longest` is the headline per N-54 P5, and **any number
   pooled across the two modes is meaningless.**
4. **`_is_downwind()` disagreed with `direction_sweep.py`** — centre-to-centre vs
   emission-point-to-intake, so it printed "19 of 36 downwind refused" where N-54 measured **36 of
   36**. Gotcha #12: two code paths computing one quantity two ways. Now byte-identical logic.

### 8g.4 The result — headline is `bank_mode=longest`, the realistic 123 m facade

Seven **real** KIAD days, selected by printed criteria, × the four **measured** FortyGuard offsets.
Δ = agent − incumbent free-cooling hours per day, paired, ±1.96 SE.

| anchor | 0 h notice | 1 h | 3 h | 6 h |
|---|---|---|---|---|
| **none** (believe FortyGuard's level) | −1.685 ±0.131 | −0.744 ±0.133 | −0.192 ±0.131 | **+0.418 ±0.145** |
| **sensor** (one local reading removes the level) | −0.235 ±0.101 | **+0.453 ±0.184** | **+0.865 ±0.222** | **+1.205 ±0.276** |

**Monotone in notice in both rows.** Break-even ≈3–6 h unanchored, ≈0–1 h anchored — which lands on
**N-56's independently derived break-even table** (1 h needs skill ≥ 0.25; 3 h needs ≥ 0.00).

- **Safety: agent 2,003 breaches vs incumbent 3,960** across the whole sweep. The agent is safer.
- **The incumbent broke its own switch budget in 10.0 % of scenarios** to stay safe; **the agent never
  did (0).** A reactive controller has no horizon, so it cannot respect a switch budget and stay safe
  at once. That is the clearest thing in the sweep that a threshold provably cannot do.
- **⚠ These seven days were SELECTED to exercise seven behaviours. The mean is NOT an annual rate.**
  The annual rate remains N-56's, on all 43,763 hours.

**The claim is therefore CONDITIONAL, and the condition is stated: the HOURS want a level anchor. The
90 % SAFETY guarantee does not — that needs ~10 calibration days of pure FortyGuard data and no
customer hardware (HANDOFF §7.3).** Previous-day FortyGuard anchoring is **absent because it was
tested and FAILED** (1.43 → 1.71 °C); same-day anchoring is **absent because it is untested.**

### 8g.5 The vacuity guard that fired on the real days

On all four real FortyGuard days the agent declared free cooling **0 of 24 times**, so "0 unsafe
declarations" is **met and meaningless** — gotcha #37. The reason is physical: August afternoons in
Virginia at 27.0–33.0 °C against a 27.0 °C top-of-envelope limit. **No controller of any kind
free-cools on those days.** What the four days *do* test is the bound, and it failed at 65.6 %.
`agent.py` prints this rather than letting a reader infer safety from a vacuous zero.

### 8g.6 What `demo/` now contains — the demo's only input

| File | What |
|---|---|
| `trace.json` (260 KB) | the whole loop: site, envelope, physics provenance, cycle, cases, summaries, **`act_log`** |
| `scenarios.json` (7.9 MB) | **all 40,320 rows**, columnar (`columns` + `rows`) so nothing is summarised away |
| `field_<date>_{forecast,outcome}.json` (8 × 570 KB) | 17,862 real FortyGuard tiles each. All tiles share **one quad shape to 1e-8**, so the file is one shared template + centroids: 570 KB instead of 7.4 MB |
| `rise_table_{longest,facing}.json` | 576 GPU solves each, cached so a re-run is instant |

**ACT is real, not narrated.** `act_log` holds BMS/SCADA-shaped command rows, each carrying the
numbers that produced it, e.g. for the crossing day at an 18 °C limit:

> `00 -> FREE-COOLING` — upper bound on intake 4.466 °C = forecast + level margin +0.000 °C (level
> anchored) + shape margin +1.228 °C (from 43,760 persistence hours) + recirculation +0.018 °C, under
> the 18.0 °C limit. *Summing two one-sided 90 % bounds guarantees 80 %, not 90 % — stated, not implied.*
>
> `12 -> MECHANICAL` — upper bound 18.119 °C is NOT under the 18.0 °C limit (recirculation +0.008 °C).

### 8g.7 Still to build

**The demo page itself.** `trace.json` + `scenarios.json` + the field files are the complete input; no
API call, no server, no key. Screen Zero (17,862-tile field), the wind dial over
`direction_table.json`, the seven cases, the refusal screen (`bank_mode=facing`), and the 65.6 %
failure shown rather than hidden.

---

## 8h. ✅ RIGOROUS CONFORMAL LAYER + FIVE-YEAR BACKTEST — 2026-08-18

Three new modules, each with a self-test that IS the evidence it works:
`src/conformal.py` (20/20 checks), `src/environment.py` (all checks), `src/backtest.py`.
**Zero API calls.** Full run 16 s.

### 8h.1 The defect this repairs

The bound was calibrated on **4 residuals, all from one hour-of-day (14:00) at one lead (~9.4 h)**,
then applied to **every hour at leads 0–6 h.** Conformal validity requires **exchangeability** —
calibration and test cases must be interchangeable. A 14:00 residual at 9.4 h lead is not
interchangeable with an 04:00 residual at 3 h lead. **The bound was used outside the domain it was
calibrated on.** That is a stronger criticism than "marginal instead of conditional."

**Three levels of guarantee, and which is reachable:**

| Level | Meaning | Status |
|---|---|---|
| Marginal | right 90 % averaged over all hours | what we had |
| **Group-conditional (Mondrian)** | right 90 % **within every group** | **ACHIEVABLE — built** |
| Full conditional | right 90 % for every individual case | **PROVABLY IMPOSSIBLE** distribution-free — Barber, Candès, Ramdas & Tibshirani (2021), [arXiv:1903.04684](https://arxiv.org/abs/1903.04684) |

So "right for every hour" in the strict sense is forbidden by a theorem. We build the strongest
thing that is not forbidden and say which one we shipped. Citations: PLAN §12.7.

### 8h.2 `conformal.py` — what the self-test proves, on synthetic data with a known answer

| Component | Demonstrated result |
|---|---|
| Mondrian (Vovk 2012) | pooled reads **0.900 overall while one group sits at 0.729**; Mondrian holds **0.894–0.899 in every group** and is **tighter on easy groups (0.381 vs 1.900)** |
| Convolution vs Bonferroni | adding two 90 % bounds over-covers at 0.9650; convolving lands at nominal 0.8955 — **recovers 0.774 °C of margin** |
| Normalized score (CQR, Romano 2019) | fixed width **under-covers hard cases (0.8739)**; normalized holds 0.8990 and is smaller on easy ones |
| ACI / DtACI (Gibbs & Candès) | static bound under drift **collapses to 0.5208**; ACI recovers to **0.8960** and **0.8930 after the shift** |
| Joint coverage (Stankevičiūtė 2021) | per-hour bound gives only **0.8196** across a 6 h commitment; max-over-horizon gives 0.8984 and beats Bonferroni-in-time on width |
| Worst-group diagnostics | every report now carries the worst group, never only the mean |

### 8h.3 Does group-conditional calibration matter on REAL weather? Yes — measured

Held-out chronological split, 913/913 days.

| notice | pooled: overall / **worst group** / groups < 90 % | Mondrian: overall / **worst** / < 90 % | Mondrian q range |
|---|---|---|---|
| 1 h | 0.9011 / **0.7864** (hour 19) / 8 of 24 | 0.9133 / **0.8838** / 4 | 0.81–2.17 °C |
| 3 h | 0.9017 / **0.7314** (hour 9) / 6 of 24 | 0.9144 / **0.8794** / 5 | 1.49–4.37 °C |
| 6 h | 0.9113 / **0.7884** (hour 11) / 8 of 24 | 0.9177 / **0.8936** / 2 | 2.21–6.66 °C |

**The pooled average hides hours where a controller would be unsafe** — 0.9017 overall, 0.7314 at
hour 9. The Mondrian quantile varies **2.9×** across hours of day, so one pooled number was
simultaneously too tight in some hours and too loose in others.

**⚠ Over-stratification HURTS, and we measured it rather than assuming more groups is better.**
Adding season → 96 groups, smallest n = 181, and the worst group gets **worse** (0.8484–0.8498)
with 27–40 groups failing. **Hour-of-day alone is the right stratification here.**

### 8h.4 Online adaptive conformal — 43,260 real rounds

| | realised coverage | first half | second half |
|---|---|---|---|
| static | 0.8943 | 0.8937 | 0.8949 |
| **ACI** | **0.8998** | 0.8999 | 0.8997 |
| DtACI | 0.8996 | 0.9006 | 0.8986 |

**Honest reading: ACI's benefit here is real but small (+0.55 pp), because the de-biased
persistence residual stream is nearly stationary.** ACI's dramatic value appears where a genuine
level shift occurs — which is exactly what FortyGuard's day offset does (−0.19 → +3.64 between
consecutive days). **That is the component ACI is for, and it is the one we cannot yet validate,
because it has n = 4.** Shipped, validated on the stream where thousands of rounds exist, and its
intended target named.

### 8h.5 🔴 THE ASOS QUANTISATION LIMIT — found while chasing an exact zero

The first N-56 comparison returned **exactly +0.0000 h/day**. Exactly zero is a tell, not a
measurement. Cause, verified:

- KIAD's five-year record holds only **112 distinct temperature values** across 43,763 hours.
  **98 % are whole degrees Fahrenheit** (gotcha #24 confirmed on the full record), giving an
  effective resolution of **0.5556 °C**.
- Around 24 °C the representable values are **23.33, 23.89, 24.44**. Both policy thresholds
  (incumbent 23.610; agent 23.805 − rise ∈ [23.45, 23.805]) fall inside **one empty gap**, so they
  select the identical set of hours.

**Effect sizes against that resolution:**

| quantity | °C | grid steps |
|---|---|---|
| recirculation, worst bearing | 0.3550 | **0.64** |
| agent-vs-incumbent margin at zero notice | 0.1948 | **0.35** |
| conformal margin at 3 h notice | 2.4636 | **4.43** |

**Any claim resting on an effect below ~0.55 °C cannot be validated against this record.** The
zero-notice recirculation story is sub-resolution; the forecast story at 3 h is 4.4 grid steps and
resolves cleanly. **This is independent support for the pitch already leading with the forecast.**
A real sensor reads noisily each hour, which dithers across the grid; that is now modelled
(`sensor_dither`, fixed seed) and it is what makes N-56's mechanism reproducible at all.

### 8h.6 🔴 CORRECTION TO HANDOFF §5.3 — "+67 h/yr from recirculation alone" IS WRONG

N-56's own rows, at notice 0, anchored, limit 24 °C:

| sensor error | incumbent buffer | agent buffer | gain |
|---|---|---|---|
| 0.1 °C | 0.2177 | **0.1945** | +10.4 h/yr |
| 0.3 °C | 0.4588 | **0.1945** | **+66.8 h/yr** ← the quoted headline |
| 0.5 °C | 0.7113 | **0.1945** | +162.0 h/yr |

**The agent's buffer never moves. The gain tracks the INCUMBENT's buffer.** The number is produced
by an **uncertainty asymmetry** — FortyGuard's field assumed more precise (0.15 °C) than the
customer's rooftop sensor (0.3 °C) — **not by recirculation awareness.**

**Direct isolation, by rerunning with the plume term removed from the agent's bound while leaving
it in the ground truth (sensor 0.3 °C, notice 0):**

| | gain | breaches per 1,000 free-cooling hours |
|---|---|---|
| agent KNOWS about the plume | **+65.6 h/yr** | **0.17** |
| agent IGNORES the plume | +42.8 h/yr | 0.63 |

**Knowing about the plume COSTS 22.8 h/yr and cuts the breach rate by 3.7×.**
**Recirculation awareness buys SAFETY, not HOURS**, against an incumbent that carries no plume
allowance of its own. State it that way from now on.

### 8h.7 The reproduction, and the five-year numbers

Both policies now bound **the same target — true intake temperature** — each from a Mondrian
conformal quantile of **its own residuals on calibration days only**. An earlier version bounded
the incumbent against **ambient**, which was unfair to it: a real operator's fitted buffer absorbs
the plume statistically even though the operator has never heard of it, because the plume is inside
the residuals they fit on. Removing that made the adversary weaker than reality and inflated our
gain.

**Reproduction of N-56 (notice 0, skill 1.00, no scheduling constraints):**

| sensor error | **ours** | N-56 | agreement |
|---|---|---|---|
| 0.1 °C | +18.4 h/yr | +10.4 | same sign and order |
| **0.3 °C** | **+65.6 h/yr** | **+66.8** | **within 1.8 %** |
| 0.5 °C | +158.4 h/yr | +162.0 | within 2.2 % |

Two independently written implementations agreeing to 1.8 % on the headline row is the reason to
believe either.

**Cumulative realism ladder** — 913 held-out days, sensor 0.3 °C, coverage measured on held-out
hours:

| step | gain h/day | ±95 % | h/yr | coverage |
|---|---|---|---|---|
| N-56-like: notice 0, skill 1.00, no constraints | +0.1796 | 0.0357 | **+65.6** | 0.9025 |
| + switch budget 2, min dwell 3 h | +0.2344 | 0.0877 | **+85.6** | 0.9025 |
| + dew-point gate **15 °C, Green Grid WP#46 p.6** | +0.3253 | 0.1111 | **+118.8** | 0.9025 |
| + notice 3 h, skill 0.50 (no perfect forecast) | +1.1106 | 0.2092 | **+405.7** | 0.9035 |
| + **unanchored**, four measured FG offsets rotated | −0.4272 | 0.2154 | **−156.0** | 0.9865 |

Two results worth reading carefully:

1. **The switch budget and the humidity gate INCREASE the agent's advantage** (+65.6 → +85.6 →
   +118.8). Both constraints hurt the reactive incumbent more than the planning agent — it has no
   horizon, so it cannot respect a switch budget and stay safe at once, and its noisy sensor must
   clear the humidity gate too. The gate is **not vacuous**: it binds on **3,093 held-out hours,
   17.7 % of the hours dry-bulb alone would have allowed**.
2. **Unanchored costs ~562 h/yr** (+405.7 → −156.0) and coverage rises to **0.9865** — the bound
   stays safe and pays for it in hours. **That is the forecast-calibration bug priced over five
   real years**, and it is the strongest argument for both the level anchor and the ~10-day
   calibration set.

**⚠ TWO CORRECTIONS MADE TO THIS TABLE ON 2026-08-19, both in the same direction — a number we
could point at.**

**(a) The humidity gate was INVENTED, and this row used to carry it.** The row read
*"+ wet-bulb gate 3 °C tighter → +112.4 h/yr"*. That 3.0 °C had no source and was derived from our
*own* changeover limit, so it failed the project's point-at-the-constant test. `agent.py` had
already migrated to a **sourced dew-point maximum — 15 °C, [Green Grid White Paper #46
p.6](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf),
the ASHRAE recommended dew-point maximum, which WP#46's own free-cooling hour count uses jointly
with a 27 °C dry-bulb maximum** — but `backtest.py` had not, so **the five-year ladder was still
being produced by the condemned constant while this document described the sourced one.** Nothing
in the tree could see
that, because **no test re-read the ladder** (methodology rule 10). All five rows are now in
`audit.py`'s registry, and a new `check_retired_constants()` fails the build if a constant removed
for cause reappears as *code* anywhere in `src/` or `demo/`.

**(b) The agent had a free perfect hygrometer.** Migrating the gate exposed it: the incumbent's
humidity reading was dithered by its sensor error while the agent's was left **exact**, so the
agent's fitted humidity margin came out at **0.0000 °C**. It had gone unnoticed while the wet-bulb
gate rarely bound; the dew-point gate binds on 17.7 % of candidate hours, which made it
load-bearing. FortyGuard's measured field noise (0.15 °C sd) is now applied to **both** channels it
supplies, and the agent's humidity margin reads **0.1929 °C against the incumbent's 0.5064** — the
documented 0.15-vs-0.3 asymmetry rather than 0-vs-0.3. **Without this fix the gate row read
+206.4 h/yr; with it, +118.8.**

**What the corrections mean for the story: they do not change it.** The sourced gate costs
approximately what the invented one did (+118.8 against +112.4, and `audit.py` now asserts the two
agree within 10 h/yr), so **no headline ever depended on the invented number** — which is the only
reason this is a correction rather than a retraction.

**⚠ An oracle of ours, caught and removed here.** A first version applied ONE constant offset to
all 1,826 days; a margin fitted on those days absorbed it completely and the unanchored case came
out at **+450.9 h/yr**. A constant bias is learnable from history — FortyGuard's is not. The four
measured offsets are now **rotated across days**, so calibration and test days carry different
offsets and the margin must cover the spread. That single change moved the number from +450.9 to
**−156.0 h/yr.**

### 8h.7a The 12-axis sensitivity — and the three axes that reverse the answer

**⚠ This section exists because of a defect in our own honesty, not in the physics.**
`backtest.py`'s base case carried a comment claiming *"every axis below is varied around it and
reported, and the full factorial over the value axes is run separately."* **That was false in that
file.** Eight sweep lists were declared at module level and **exactly one of them was ever
iterated.** The five-year headline therefore rested on a hand-picked `notice_h = 3`,
`skill = 0.50`, `limit_c = 24 °C`, `switch_budget = 2`, `min_dwell_h = 3` with nothing in the
five-year code varying any of them — the point-at-the-constant test failing five times over, behind
a comment asserting the opposite. (The 120,960-scenario factorial in `agent.py` is real, but it runs
over **four** FortyGuard days, not over the five-year record. A sweep on other data is not a sweep
on this data.)

`run_sensitivity()` now varies **every one of the 12 axes `BASE` declares**, 33 configurations on
the same 913 held-out days, and **`main()` returns a non-zero exit code and refuses to write output
if any axis in `BASE` has no sweep list** — verified end-to-end by injecting a knob and confirming
`backtest.json` was left untouched. Eleven of the twelve axis lists are **imported from
`agent.py`'s `PLANT_ENVELOPE`** rather than restated (they had already drifted: `switch_budget` read
`[1,2,3,4]` here against `[1,2,4]` there). The twelfth, FortyGuard's field noise, is **read off
disk** — min / mean / max of the per-tile sd of the four measured N-26 pairs, so the swept range
cannot drift from the measurement it claims to come from.

**The gain keeps its sign on 9 of 12 axes. On three it does not, and each reversal is explained by
a quantity the run itself counted:**

| axis | range h/yr | negative at | the measured mechanism |
|---|---|---|---|
| `bank_mode` | −3124.4 … +405.7 | `facing` | the agent **refused 10,779 of 21,912 held-out hours**, and **7,142 of those were genuinely safe** |
| `anchor` | −156.0 … +405.7 | `none` | realised coverage **rose 0.9035 → 0.9865** against a 0.90 nominal |
| `switch_budget` | −78.0 … +405.7 | `1` | the incumbent **exceeded the budget on 212 of 913 days** (base case: 28) and kept its hours |

**1. `bank_mode = facing` costs −3,124 h/yr, and that is the refusal guard working.** In this
geometry the intake has no line of sight to the source on **49.3 % of all hours**, so
`path_blocked()` declines to answer rather than returning a rise the solver cannot compute.
7,142 ÷ 913 = **7.8 h/day of genuinely safe cooling handed to the incumbent for free**, against a
measured 9.7 h/day gap. **This is the first time the refusal guard has been priced.** It is a real
limitation, stated as one: the headline is **conditional on the condenser bank sitting on the long
facade**, and where it does not, the agent's honesty costs more than its forecast earns.

**2. `switch_budget = 1` is not a fair fight, and it favours the INCUMBENT.** The agent honours the
budget as a hard DP constraint; the reactive incumbent **breaks it to stay safe and still has its
hours counted**. That count was being discarded by `score_config` and is now reported. It is left
that way deliberately — a real reactive controller does break its switch budget, and giving it a
constraint it would not honour is the untuned-adversary mistake (methodology rule 3).

**3. The reversal explainer had to be fixed before it could be trusted.** Its first version
reported *"the incumbent exceeded the switch budget on 28 days"* under `anchor = none` **and**
`bank_mode = facing` — but the base case also sits at 28, so **that quantity did not differ between
the compared runs and could not be the cause.** That is gotcha #35, committed by the code written
to prevent it. A diagnostic is now printed only if it **moved** relative to the base row.

### 8h.8 `environment.py` — the two gates a real economizer has and we did not

| Gate | Basis | Verified |
|---|---|---|
| **Dew point** ⟵ *the SHIPPED gate* | Green Grid **WP#46 p.6**: the ASHRAE **recommended maximum dew point is 15 °C**, and WP#46 counts a free-cooling hour only when dry-bulb **and** dew point both clear their maxima. ENERGY STAR: products check temperature **and** humidity; Honeywell JADE states differentials in **Btu/lb**, an enthalpy unit. N-56 listed this as a gap in its own limitations | Dew point is read **straight from the station record at 100 % coverage**, so no psychrometric formula sits between the measurement and the decision. Swept at `[None, 15, 18]`; **not vacuous** — binds on 3,093 held-out hours, 17.7 % of those dry-bulb alone would allow |
| **Wet-bulb / enthalpy** — *derived and validated, but **NOT** gated on* | Kept because it is the independent check on our psychrometrics, and because an enthalpy economizer is what a JADE controller actually implements | wet-bulb computed on all 43,763 hours from real dew point, validated against **PsychroLib** (independent ASHRAE reference): **MAE 0.2681 °C**, inside Stull's published < 0.3 °C. Physical bounds Td ≤ Twb ≤ T hold on **1.0000** of hours. 99.59 % inside Stull's validity envelope; the 180 exceptions are all RH > 99 % and are counted, not extrapolated. **It gates nothing**: a wet-bulb limit has no published maximum to test against, which is exactly how an invented 3 °C offset got in (§8h.7) |
| **Contamination** | LBNL measured particle spikes at **8 real data centres** when economizer vents opened, and named owner **reluctance over pollutants** as the barrier to using free cooling at all — [OSTI 971864](https://www.osti.gov/biblio/971864) | limit **swept** across FortyGuard's measured range (median 50.8, p90 75.2), because their `:idx` fields carry no documented units |

**The humidity gate is not cosmetic:** at a 24 °C limit it blocks **1,389 hours** that dry-bulb
alone would have allowed, and it *increases* the agent's advantage by 26.8 h/yr.

**⚠ The air-quality gate cannot be backtested over five years** — no five-year air-quality record
exists in this project. It is measured on the 29 FortyGuard days and reported with its own n, never
folded into the annual number. A free EPA AQS fetch would close this.

### 8h.9 Two new FortyGuard defects found while wiring the fields in

Filed as `fortyguard-api-findings.md` §9.

1. **`cloud_cover_octas` returns PERCENT, not octas** — 236 values, **all integers, 100 % ≤ 100, 73
   distinct values above 8.** A units/naming bug, not corrupt data, which **upgrades the field from
   unusable to usable.** Supersedes our §1.3. Using it changes the Pasquill stability class in
   **4 of 24 hours**, retiring the "all 43,708 hours are CLEAR" assumption.
2. **`air_quality:idx` is identical to `air_quality_pm2p5:idx` in 21 of 29 responses** — the
   headline index carries no ozone or NO₂ information, and ozone peaks on exactly the hot sunny
   afternoons a free-cooling controller cares about.

### 8h.10 Still to do

- **Wire `agent.py` onto `conformal.py` and `environment.py`.** The three modules are built and
  self-validated; `agent.py` still runs its own single-quantile bound and one dry-bulb gate.
- The full config sweep over the five years (only the N-56 ladder and sensitivity runs so far).
- The demo page.

---

## 8i. ✅ THE DEMO EXISTS — `demo/index.html`, 2026-08-18

`demo/` was an empty folder this morning. It now holds a **single-file static page, 46 KB, no
dependencies, no build step, light + dark**, that runs from saved FortyGuard responses with
**zero API calls at view time**. Any static host serves it as-is.

### 8i.1 It re-runs the agent, it does not replay a lookup

`trace.json` ships the per-hour **inputs** — forecast error, group-conditional margins, plume
rise, wet-bulb, air quality, refusal flags — and the browser forms the bound and solves the
schedule with the same dynamic program and the same three gates as `src/agent.py`. Moving any
control genuinely re-decides. The 18 MB sweep is shipped for audit but never loaded by the page.

**That puts the scheduler in two languages, which is gotcha #12 with a safety decision attached.
So it is tested:** `verify_browser_agent.js` **extracts the functions out of `index.html`** (rather
than copying them, so it tests what ships) and compares against the Python agent on 500 random
patterns — **0 plan mismatches, 0 reactive mismatches.**

### 8i.2 What is on screen, including what goes wrong

Screen zero is FortyGuard's own 17,862-tile field. Then: a draggable **wind dial** over the 72
real bearings; the **schedule** for agent vs incumbent hour by hour; the **bound against the limit
and against what actually happened**; **coverage by hour of day**, pooled vs group-conditional;
the **five-year ladder**; and an honest-limits panel.

Shown deliberately, because a demo that only shows success is not evidence:

- the bound's **measured 65.6 %** against a 90 % promise, and its FAILED pre-registered conditions;
- the hour where **one pooled quantile drops to 73 %** while its average reads 90 %;
- **refusal** — switch bank placement to `facing` and the agent declines nearly every hour, which
  the 12-axis sweep now prices at **−3,124 h/year**, 7,142 genuinely safe hours forgone (§8h.7a);
- what believing FortyGuard's level as delivered costs (**~562 h/year** — the demo computes this by
  differencing the two ladder rows rather than carrying a literal, which is why it moved when the
  ladder was regenerated on the sourced gate);
- that recirculation awareness **costs hours and buys safety**.

Every control is labelled `swept`, and there is still **no changeover temperature in the source**.

### 8i.3 Verification, and the one thing NOT verified

| Checked | How |
|---|---|
| all 74 data paths the page reads | asserted against `trace.json` / `backtest.json` / field files |
| JavaScript parses | `node --check` on the extracted script |
| browser agent == Python agent | 500 random cases, 0 mismatches |
| colour palette | the data-viz validator: all checks pass **all-pairs in both modes** (CVD ΔE 24.7 light / 26.8 dark, normal-vision 33.6 / 31.8). Two categorical slots only; sequential blue = temperature, sequential orange = plume rise; status colours always carry a text label |
| serves over HTTP | 200 on the page and every data file |
| **visual rendering** | ⚠️ **NOT verified — no browser was available.** Label collisions, canvas geometry and overflow have not been eyeballed. **Open it and look before recording the video.** |

---

## 8j. 🔬 SOLVER VERIFICATION — re-run from scratch, 2026-08-19

Asked for directly: *"re-check if the solver is correct and how we need it for the final locked
idea."* Every number below is from re-running the tests today, not from the record.

### 8j.1 Results

| Test | Verdict | Measured today |
|---|---|---|
| **N-29 V1** diffusion term | ✅ **PASS** | σ_y² slope error **0.00 %** vs the analytic 2D/u, at dx=5 |
| **N-29 V2** heat conservation | ✅ **PASS** | shortfall **0.00 %** |
| **N-29 V3** grid convergence | ❌ **FAIL AS WRITTEN** | magnitude \|dx10−dx5\| = **0.00889 °C**, inside its own 0.05 °C bound; **order p = nan** → fails |
| **N-29 V4** obstacle absorption | ✅ **0.0 %** | the 2026-08-12 fix works; gotcha #26 was stale |
| **N-16** CPU vs GPU | ✅ **PASS** | **81.6×** on 100 members; agreement **0.00012 °C** |
| **N-35** Prairie Grass, 67 field experiments | ✅ **PASS** | exponent **0.805** measured — confirms **our √x shape is the outlier** |
| **N-21** six instrumented ACCs | ✅ **PASS** | **r = 0.798**; direction matters **1.4×** more than speed |

### 8j.2 V3 diagnosed, NOT redefined

V3's own docstring demands the two causes be separated before anything is claimed. Done:

- **The field converges.** At a *fixed physical probe point*, dx = 20/10/5 gives 0.121698 /
  0.132168 / 0.132291 °C — successive difference **1.2 × 10⁻⁴ °C**. The PDE solution is converged.
- **The measurement operator does not, and cannot.** V3 measures `intake_temperature(disc=True)`,
  a 30 m-radius disc average that *excludes obstacle cells*. Usable cells in that disc:
  **6 at dx=20, 22 at dx=10, 80 at dx=5.** The quantity being compared is *defined differently on
  each grid*, so an order of convergence cannot be estimated for it — and the successive
  differences flip sign (+0.00486, −0.00889) exactly as expected at the noise floor.
- I also tested and **rejected** my first hypothesis (that the 20 m source, 1 cell at dx=20 and
  4×4 at dx=5, was the confounder): making the source exact on all three grids did not stabilise
  the order either.

**Recorded as FAILED AS WRITTEN with a diagnosis** — same handling as N-54 P1 and N-56 Q1
(methodology rule 2). The honest statement: *the solver's field is grid-converged to ~1 × 10⁻⁴ °C;
V3's order criterion is unestimable because its own operator is grid-dependent.*

### 8j.3 🔴 THE LIMITATION THAT MATTERS FOR THE LOCKED IDEA

N-35's PASS confirms a **limitation**, not a strength. Measured on 67 independent 1956 field
experiments, plume width grows as **x^0.805**; ours grows as **x^0.5**. Matched at 200 m:

| distance | measured | ours | our error |
|---|---|---|---|
| 50 m | 0.328 | 0.500 | **+53 %** |
| 100 m | 0.572 | 0.707 | **+24 %** |
| 200 m | 1.000 | 1.000 | 0 % |
| 800 m | 3.051 | 2.000 | −34 % |

**Our committed site's source-to-intake distance is 60–165 m — squarely in the band where our
plume is TOO WIDE.** A wider plume is a more diluted plume, so **our model UNDER-predicts the
intake rise there, by roughly 5–25 %.** That is the *unsafe* direction for a safety bound and it
must be said plainly.

Two partial offsets, both sourced: ASHRAE Ch. 46 notes that neglecting buoyant plume rise gives
*"an inherent safety factor"*, and the conformal bound is fitted to residuals against **real
outcomes**, so a systematic under-prediction of the plume term is absorbed into the measured
margin rather than escaping unnoticed. **Scale check:** worst measured rise 0.3550 °C; inflating
25 % gives ~0.44 °C, still **under one ASHRAE-station grid step (0.5556 °C)**. So the conclusion
does not flip — but its margin is thinner than the raw number suggests.

### 8j.4 Do we need the solver at all? Four claims, honestly graded

| Justification | Status |
|---|---|
| **Refusal** — `path_blocked()` declines to answer where a hall blocks the path | ✅ **Real and load-bearing.** Pure geometry, untouched by V3/V4/N-35. 56 of 145 candidate pairs refuse every downwind bearing; it forced the site change |
| **Site screening at scale** — refusal measured for 145 pairs in seconds, no PDE solve | ✅ **Real.** It is what selected the committed site |
| **Magnitude of the recirculation term** | ⚠️ **Real but small, and it costs hours.** Worst 0.3550 °C = 0.64 station grid steps; the five-year backtest measured plume awareness **costing 22.8 h/yr** while cutting breaches **3.7×** (0.63 → 0.17 per 1,000 free-cooling hours). A **safety** instrument, not an hours instrument |
| **Uncertainty shaping** — ensemble spread as the conformal normalizer | ❌ **NOT BUILT. Claim withdrawn.** `NormalizedConformal` exists in `conformal.py` and passes its self-test, but `grep` shows it is used **nowhere** in the agent, and `agent.ensemble_spread()` is **dead code, never called**. A previous session stated this was "implemented and tested" — the *class* is; the *wiring* is not. Session 2 builds it |

**Verdict: the solver is correct where it has been verified, honestly limited where it has not, and
justified today by refusal and site screening rather than by magnitude.** The strongest
justification — feeding the ensemble spread into the bound — is the next thing to build, and until
it exists it must not be claimed.

---

## 8k. ✅ SESSION 1 — THE ENSEMBLE SPREAD IS NOW THE WIDTH OF THE BOUND (2026-08-19)

New module `src/plume_uncertainty.py` (self-test passes) plus two real bug fixes found on the way.

### 8k.1 What was wrong

The bound added a **point estimate** of the plume rise with **no uncertainty attached**, while
carrying a carefully calibrated margin for the temperature forecast. Inconsistent: the agent does
not know tomorrow's wind **direction** either, and the plume term depends on direction more sharply
than on anything else. Worse, the case loop used the **same bearing** for the agent and for the
truth — handing the agent a perfect plume forecast for free.

A previous session claimed this was already built. It was not: `NormalizedConformal` passed its own
self-test but `grep` found it used nowhere, and `agent.ensemble_spread()` was dead code. That claim
was withdrawn in §8j.4 and is now actually delivered.

### 8k.2 How it works — no new PDE solves

N-40 **measured** FortyGuard's wind-direction forecast error at **47–72°**. So the agent's estimate
is the rise at the **forecast** bearing; the truth is the rise at the **actual** bearing. The spread
of the rise over that measured direction distribution is the per-hour **difficulty** signal, and it
is obtained by resampling the existing rise table — a lookup, not a solve.

Measured on the committed geometry: spread **0.00397–0.13740 °C**, a **34.6× variation** across
bearings at σ_dir = 47° (calmest due east, where the plume blows away; sharpest at 210–230°, where
a small direction error swings it across the intake).

### 8k.3 What it buys, measured on 43,763 real hours, held-out days

| | FIXED width | NORMALIZED (CQR-style) |
|---|---|---|
| margin | 0.08658 °C everywhere | **0.00482–0.13359 °C** |
| coverage overall | 0.9049 | **0.9019** |
| coverage, EASY quartile | 0.9523 *(over-covering — wasted margin)* | 0.8888 |
| coverage, HARD quartile | **0.9212** *(under-covering where it matters)* | **0.9412** |
| mean margin, easy hours | 0.08658 | **0.02980 — 2.9× tighter** |

**Margin moved from where it was not needed to where it was.** In the shipped bound the margin
varies **2.24×** (p95/p5) across 34,197 non-calm hours; it is tighter than a fixed margin on 31 %
of hours and wider on 69 % — i.e. a fixed margin was under-protecting the majority.

**σ_dir is a measured range, so the shipped bound takes the pessimistic end (72°).** Stated trade:
that costs discrimination (2.24× rather than 34.6×). Both ends are calibrated and shipped in
`demo/plume_uncertainty.json`.

**Cost in hours, and it is real:** the agent now carries a plume margin it previously ignored, so
`sensor / 3 h` fell from **+0.907 to +0.589 h/day**. That is the price of an honest bound.

### 8k.4 🔴 TWO BUGS FOUND BY A NEW END-TO-END TEST

`demo/verify_browser_decision.js` drives the **shipped** `decide()` (extracted from `index.html`,
not copied) and compares its hour-by-hour modes against the rows `agent.py` itself wrote. The
existing DP test could never catch either of these, because the DP agreed perfectly while the
**bound fed into it** differed.

1. **🔴 The Mondrian bound was never actually in the agent's decisions.** The scenario loop still
   read `inc_margin[N]["margin"]` — the **pooled** quantile — while `_day_series` shipped the
   group-conditional one. They disagreed by **2.4567 vs 1.9065 °C** at hour 23 of the crossing day.
   Every document said group-conditional; the decisions were pooled. **47 configurations mismatched.**
2. **Rounding the shipped arrays to 4 dp changed decisions at exact gate boundaries.** On
   2023-06-21 the dew-point bound lands on **exactly 15.000** against a 15.0 limit, so a 1e-4
   rounding difference put the browser on the other side of a tie. **24 configurations mismatched.**
   Every array a decision is recomputed from now ships at **full precision**; display rounding
   belongs in the view.

**After both fixes: 2,016 configurations compared, 0 mismatches.**

### 8k.5 Verification state

`conformal.py` ✅ · `environment.py` ✅ · `plume_uncertainty.py` ✅ · `verify_browser_agent.js` ✅
(500 cases) · `verify_browser_decision.js` ✅ (2,016 configurations) · all 19 demo JSON files
strict-JSON valid · decision panel re-rendered and inspected.

---

## 8l. ✅ SESSION 2 — STAGE 7 (EXPLAIN) IS BUILT, AND ITS CLAIMS ARE VERIFIED (2026-08-19)

`src/explain.py` + a live explainer in the interface. The loop now ships **all seven stages**.

### 8l.1 The design decision, and the measurement that settled it

The plan was a local Nemotron narrator. Measured first:

- **Warp ensemble peak VRAM: 371 MiB of 6,141 — 5,770 MiB free.** A small quantised model would
  fit comfortably. **VRAM was never the constraint**, and that question is now closed.
- **There is no inference stack on this machine** — no Ollama, no torch, no transformers, no
  llama.cpp. Adding one is a multi-gigabyte install on the user's machine.

But the deciding argument is neither. **This stage's whole job is to report numbers the agent
already computed** — precisely where a language model is most likely to be wrong and least
excusable, against a standing no-hallucination rule. So:

> **EVERY CLAIM AN EXPLANATION MAKES IS VERIFIED BY RE-RUNNING THE AGENT.**

If an explanation says *"this hour would flip if the limit were 0.42 °C higher"*, `verify()` moves
the limit by 0.42 °C, re-plans, and checks that it flips — **and that 0.42 °C minus a hair does
NOT**, so the distance is tight rather than merely sufficient. Modes are checked against a fresh
plan; scheduling counterfactuals against a fresh re-plan; every "safe" claim against an independent
recomputation of the gates.

**Result: 1,336 hour-explanations across 7 case days × 8 configurations, 0 verification failures.**

An LLM can still be layered on later to rephrase this brief into friendlier prose, with a checker
that rejects any number absent from the brief. The factual content stays here, where it is testable.

### 8l.2 Seven kinds of reason, and two of them prove the agency claim

Exercised counts from `verify_browser_explanation.js`: dry-bulb 624 · free 435 · dew point 148 ·
refusal 88 · **switch budget 38** · air quality 2 · **minimum dwell 1**.

| Binding constraint | What the agent says |
|---|---|
| **refusal** | *"a building sits between the condensers and the intake… the model has no representation of a building standing in the flow, so any number would be meaningless"* |
| 🔴 **switch budget** | *"Mechanical EVEN THOUGH THIS HOUR IS SAFE — the budget of 2 changes is already committed to better hours"* |
| 🔴 **minimum dwell** | *"…the plant must hold its mode for 3 h before changing again"* |
| **dew point** | *"TEMPERATURE IS NOT THE REASON — the dry-bulb bound of 21.530 °C would have passed. The air is too HUMID: 20.27 vs 15.0 °C"* |
| **air quality** | *"neither temperature nor humidity — the air is too DIRTY: PM2.5 index 75.7 against 73.5"* |
| **dry-bulb** | *"fails by 11.510 °C; a limit that much higher would change it"* |

**The two marked in red are the ones a thermostat cannot produce.** "This hour is safe and I
declined anyway" requires a plan to be constrained by. Which of the two constraints bound is
determined by **re-planning with each relaxed in turn**, never by guessing. That is the agency
claim made auditable rather than asserted.

### 8l.3 Generated live, and cross-checked against Python

The interface generates explanations from the same state it decided with, so they cover **every**
swept configuration rather than a precomputed handful. That puts the explainer in two languages, so
it is tested the same way the scheduler is: `verify_browser_explanation.js` extracts `explainHour`
**out of `index.html`** and compares the binding constraint and mode for every hour against
`explain.py`. **1,336 compared, 0 mismatches.**

### 8l.4 Two of my own bugs, caught in this session

1. **The identical rounding mistake as §8k.4, hours later.** `flip_needs` was rounded to 4 dp, so
   `limit + flip_needs` landed a hair *below* the bound and `verify()` reported **328 false
   failures**. A number a comparison depends on is not a display number. Now full precision.
2. **The interface printed "−0.000 °C of group-conditional forecast error."** The shape margin was
   being re-derived by subtracting the other terms out of the bound, accumulating float error into a
   negative zero — in a sentence whose entire point is that the margin is measured. The margin the
   agent actually applied is now passed through instead of reconstructed.

### 8l.5 Verification state after Session 2

`conformal.py` ✅ · `environment.py` ✅ · `plume_uncertainty.py` ✅ · `explain.py` ✅ (0 of 1,336) ·
`verify_browser_agent.js` ✅ (500) · `verify_browser_decision.js` ✅ (2,016) ·
`verify_browser_explanation.js` ✅ (1,336) · all demo JSON strict-valid · explain panel rendered
and inspected.

---

## 8m. ✅ SESSION 3 — FULL-TREE AUDIT, MECHANICAL AND REPEATABLE (2026-08-19)

Two new modules: `src/audit.py` (16 checks) and `src/run_all.py` (one command, full rebuild + audit,
**65 s, zero API calls**). The audit is deliberately mechanical rather than a read-through, so it
can be re-run after any change and before any claim.

### 8m.1 What the audit checks, and which real bug each check exists for

| Check | The bug it exists for |
|---|---|
| **dead code** | three superseded helpers were still in the tree after `score_config` was rewritten |
| **NaN-unsafe writers** | `NaN` is legal Python JSON and **illegal** standard JSON — the demo died on it while every Python-side check passed, because `json.load` accepts what `JSON.parse` rejects |
| **rounded decision arrays** | rounding to 4 dp flipped decisions at exact gate boundaries, **twice in one day** |
| **constant drift** | the same physical constant in two modules |
| 🔴 **stale published numbers** | **every headline figure is re-read from the JSON the code actually wrote.** A drifted figure is a hallucination with a paper trail, and this is the check that catches it |
| **self-tests** | all four module suites |
| **cross-language** | the browser agrees with Python on decisions *and* on reasons |

**Result: 16 passed, 0 warnings, 0 failures — including all 23 published headline numbers.**

### 8m.2 What it found and fixed in the source

1. **Four dead functions** — `bound_series`, `margin_series`, `ensemble_spread`, `noise_quantiles`
   (plus its three `erfinv` helpers), all orphaned by earlier rewrites. Removed.
2. **`realised_coverage()` on `ACI`/`DtACI` was never exercised.** An untested public method is a
   liability, so the conformal self-test now asserts it against an independently counted rate
   rather than deleting a sensible API.
3. **Two more rounded decision arrays** — a second `rise_c_` write in `_day_series`, and the
   **cached rise table itself**, which feeds the bound. Both now full precision.
4. **Fourteen `json.dump` calls** across the site pipeline gained `allow_nan=False`, so a future
   NaN raises at write time instead of shipping a file no browser can read.

### 8m.3 🔴 THE UNCOMFORTABLE FINDING: my checks were buggier than the code

Three of this session's "failures" were **defects in the verification, not the product**:

- the dead-code scanner subtracted the definition count from the reference count, but a
  `FunctionDef` never registers as a `Name` — so it reported **43 of 133 functions dead**, including
  `run_all` and `explain_hour`, which are obviously called;
- the precision check counted decimal places, which cannot distinguish "rounded on write" from
  "the ASOS source only ever had two decimals" — false failures on `temp_c` and `dewpoint_c`;
- the NaN-writer check matched parentheses inside a **500-character window**, and
  `select_site.py`'s dump spans **2,415 characters**, so `allow_nan=False` sat outside the window
  and ten guarded calls were reported unguarded.

All three are fixed, and each fix is commented with the false failure it produced. **A verification
tool that cries wolf is worse than none**, because it trains you to ignore it. Recorded here rather
than quietly corrected, because the pattern matters more than the three bugs: this session's
scoreboard is *checks wrong: 3, product wrong: 4*.

### 8m.4 The precision check, reframed honestly

Counting decimals was the wrong instrument. The check is now made **at the source** — no `round(`
may be applied to a decision-critical array as it is written — and the real guarantee is stated
where it lives: `verify_browser_decision.js` rebuilds **every** decision from those arrays and
matches the Python agent across **2,016 configurations**. That is end-to-end equality, which no
precision heuristic can approach.

### 8m.5 Constant duplication: agreement, not centralisation

`STEP_DEG` is defined in `agent.py`, `direction_sweep.py` and `refusal_rank.py`. Centralising it
would mean editing the committed site pipeline, whose output is the geometry every published number
rests on — a real risk this late for no behavioural gain. So the audit asserts the values **agree**
(all 5) and will catch drift the moment it appears. Same for `ALPHA` across four modules (all 0.10).

### 8m.6 One command

```bash
cd INTAKE-ARBITER/src && python run_all.py     # 65 s, zero API calls, exits non-zero on any failure
```
Order matters and is enforced: plume calibration → agent → backtest → explain → browser fixtures
→ audit. **If it exits 0, every figure in PLAN.md and HANDOFF.md is backed by a file that run
wrote.** Interface re-rendered and inspected afterwards.

---

## 8n. ✅ SESSIONS 4, 0, A, C, D, F, G — the ladder, the present tense, the tape, the visible bound, and money (2026-08-19 → 2026-08-20)

Seven sessions, written up together because they share one theme: **each one took a claim that was
being asserted and made a program re-derive it.**

### 8n.1 The five-year ladder — what each layer of realism COSTS

`src/backtest.py`, **43,763 hours / 1,826 days, 913 held out.** The point of a ladder rather than a
single figure is that a reader can see which assumption is carrying the headline:

| Step | Gain vs the tuned incumbent |
|---|---|
| N-56-like: notice 0, skill 1.00, no constraints | **+65.6 h/yr** |
| + switch budget 2, minimum dwell 3 h | **+85.6** |
| + the sourced 15 °C dew-point gate *(Green Grid WP#46 p.6)* | **+118.8** |
| + notice 3 h, forecast skill 0.50 *(no perfect forecast)* | **+405.7** |
| 🔴 **+ unanchored — four measured FortyGuard offsets rotated** | **−156.0 — THE AGENT LOSES** |

**The last row is the honest headline.** Without one local reading to anchor the level, the agent is
worse than the incumbent, and every published figure says so beside it. **`skill = 0.50` is an
ASSUMPTION** — FortyGuard's H-hour skill at this site is still unmeasured (§8e), and it is swept as
an axis rather than asserted.

**The sensitivity sweep is 12 axes, one at a time, and three of them reverse the sign.** An axis
whose interval crosses zero is an axis the headline is conditional on, and `backtest.py` prints
those explicitly rather than leaving them in a table for a reader to find.

### 8n.2 Session A — the agent runs in the PRESENT TENSE

`src/rolling.py`. Until this session the agent scored whole days from midnight, which is not how a
plant is operated. It now starts from **any hour in any plant state**, re-plans on a 12-hour rolling
horizon, and **only ever acts on the first slot of each plan** — so what is measured is what a
controller would actually have executed.

| | |
|---|---|
| Re-plans compared | **21,879** |
| **Re-plans that change nothing at all** | **94.08 %** |
| Churn | **1.128 %** of slot-decisions revised |
| Free cooling actually EXECUTED | **14.715 h/day = 5,375 h/yr** over 913 held-out days |
| Per-lead conformal bounds | **12, one per lead hour, every one covering ≥ 90 %** |

**Why churn matters commercially:** an operator will not accept a published 12-hour schedule that
rewrites itself hourly. **94 % of re-plans changing nothing is the answer to the first question a
plant engineer asks**, and it is measured rather than promised.

### 8n.3 Session D — the reasoning tape, and why it cannot be a script

`src/ticker.py` emits a seven-stage event tape. The obvious objection to any "watch it think" display
is that the words are hand-written, so the guard is mechanical — and it is the strongest single
anti-theatre check in the project:

- **30 templates, and not one of them may contain a literal digit** — `check_no_literal_digits()`
  fails the build otherwise. Every number a reader sees is interpolated from a payload value.
- **18 short forms** for the streamed status line, under the **same** guard. This matters *more* for
  the short forms: *"reading 17,862 tiles"* reads identically whether the number was computed or
  invented, so a terse phrase is exactly where a fake would hide. The check also fails if **any
  event lacks a short form or any short form lacks an event.**
- **1,002 per-hour tapes verified, 0 failures.** Of the numbers in them, **23 are re-derived from
  first principles** and **48 are read back** from the emitting file — reported separately, because
  "re-read the file that wrote it" is a weaker check than "compute it again", and conflating the two
  would overstate the verification.
- The browser renders the same sentences **character for character**, checked by
  `demo/verify_browser_ticker.js`.

### 8n.4 Session F — the conformal quantile, DERIVED IN THE BROWSER

The bound is the part a reader is least able to check, so the demo does not display a number from a
file — **`cfQuantileIndex` / `cfSplit` mirror `src/conformal.py` and are verified to agree exactly**
against `demo/conformal_cases.json`: **476 (n, α) grid points, 300 residual arrays, and 13 cases
taken from the real run.** The ⌈(n+1)(1−α)⌉ index rule is the whole game in split conformal, and an
off-by-one there is invisible in the output and fatal to the guarantee.

### 8n.5 Sessions 4 and 0 — an invented constant, and a collector that slept through two days

**Session 4 removed an invented constant.** The humidity gate was *"wet-bulb ≤ dry-bulb limit − 3 °C"*
and the **3.0 had no source** — it was derived from our own other knob, which is exactly what the
point-at-the-constant test exists to catch. It is now a **published 15 °C dew-point maximum** with a
citation, and `audit.py` has a **retired-constants check** so the invented one cannot return. It had
already survived a full day in `backtest.py` after being removed from `agent.py`, which meant the
five-year headline was briefly produced by a number every document had already condemned.

**Session 0 hardened the collector.** Two day-pairs were lost to the machine being **asleep** — no
error, no manifest entry, nothing to notice. Fixed with `WakeToRun` + `StartWhenAvailable` +
run-on-battery on all three tasks, a **retry budget that costs nothing when the first attempt
succeeds**, the attempt written to the manifest *before* the call so a crash still counts, and a
**free `dryrun` mode** that reports what the collector would do without reading the key at all.

### 8n.6 Session G — money, with the qualification attached to the number

`src/money.py`. The old limit in §9 — *"no dollar or energy figure"* — is lifted, but narrowly:

- **Both conversion factors are SWEPT, not chosen.** 4 published electricity prices × 4 published
  chiller efficiencies × the hours rows = **608 cells**, and **nothing is collapsed to a single
  number**. A single dollar figure would have hidden which published value produced it.
- **Priced in each site's own state** — Virginia prices for Ashburn, Illinois for Chicago — because
  a national average would have been a fifth unsourced assumption.
- **The chiller COMPRESSOR only.** Fans, chilled-water pumps, condenser pumps and tower fans keep
  running, and **an airside economizer moves MORE air, so fan power RISES.** The unmeasured term has
  the **opposite sign**, which makes the compressor-only figure an **upper bound on the saving, not
  an estimate of it.**
- Every source in **`money-sources.md`**.

---

## 8o. ✅ SESSIONS B + E — three sites on their own data, and two refused on evidence (2026-08-19 → 20)

**Five metros screened from real aerial imagery. Three ship. Two were REFUSED.**

| | **ashburn** (default) | **chicago** | **dulles** |
|---|---|---|---|
| Committed pair | AWS **IAD116 → IAD117** | **Stream Chicago II → Equinix CH3** | AWS **IAD81 → IAD62** |
| OSM ways | 744496750 → 744496741 | 863162820 → 377032061 | 693381107 → 545396372 |
| Facade gap | **60.3 m** *(clears the 60 m floor by 0.3 m)* | 118.4 m | 137.7 m |
| Critical rise | **0.3550 °C @ 255°** | **0.4116 °C @ 240°** | **0.3593 °C @ 265°** |
| Station | KIAD 8.9 km, 43,763 h, 99.92 % | KORD 4.4 km, 43,775 h, 99.94 % | KIAD 6.7 km *(shared)* |
| FortyGuard field | 9 calls, 8 saved fields | 1 call, 17,797 tiles | **none purchased** |

**The refusals are the most credible thing here, so they ship rather than being quietly dropped:**
**Santa Clara is rooftop-cooled** — there is no facade-to-facade intake path to reason about — and
**Phoenix is not built yet.** Both are exported and drawn on the map in red with the reason attached.
⚠ Neither refusal is proof: 5 Santa Clara frames and two Arizona clusters remain unscreened, so they
are recorded as a **"strong indication"** rather than a finding.

**Dulles cost ZERO credits and ZERO weather work**, because it shares KIAD with Ashburn — which is
the point. It **isolates geometry and operator from climate**, so a difference between Ashburn and
Dulles cannot be a weather difference.

⚠ **Dulles's imagery verdict is WEAKER than Ashburn's** and is recorded as such: no USGS
cross-check, so the two-source rule is **not met**, and chillers cannot be distinguished from
generators at 0.3–0.5 m resolution. ⚠ **Chicago's single past-window field buys the spatial
statistics and the screen-zero visual, NOT a level offset** — that needs a forecast leg *and* its
elapsed outcome, i.e. two calls.

**Session E rendered the solved plume.** `src/export_plume_fields.py` writes **72 real solved fields
per site**, audit-verified against the published critical rise to **≤ 1.1 %**. The demo draws the
field the solver actually produced, flaws included: at these distances the √x spread model is **too
wide, so it under-predicts rise by 5–25 %** — the unsafe direction — and the panel says so on screen.

---

## 8p. ✅ THE PER-SITE ENGINE, THE INTERFACE, AND A REAL PDF (2026-08-20)

### 8p.1 A site picker that swapped ONE file

**The picker offered three sites and only one of them had data.** Twelve of thirteen panels stayed
Ashburn's while the dropdown said Chicago, because only the plume field was per-site.
`agent.py` / `backtest.py` / `rolling.py` / `money.py` / `explain.py` / `ticker.py` / `report.py` are
now all metro-aware via a `METRO` environment variable — **unset resolves to `ashburn` with
byte-identical paths, so every previously audited number is untouched** — and `src/build_sites.py`
runs the whole chain per site.

🔴 **The generalisable lesson, and it is now a check:** when an interface offers a choice, **test
that the choice CHANGES something.** `audit.check_sites_actually_differ()` compares values across
sites and **fails on agreement.** Existence proves nothing.

### 8p.2 The interface is a three-stage flow

`STAGE` + `setStage()` in `demo/index.html`. **pick** a site → **configure** a plant → **watch it
work**. Every card carries `data-show` and `setStage()` is the only thing that sets `.hidden`. The
reasoning streams one line per stage at 260 ms — **presentation only, and labelled as such: it is the
reveal cadence, not a measurement.**

`buildControls()` **builds** the control markup from `CONTROLS` + `PLANT_ENVELOPE`, so an axis added
to the envelope appears without an HTML edit. **`autofill()` is labelled a navigation aid, not a
recommendation**, and every value it sets is one of the swept options.

### 8p.3 A real PDF, written without a PDF library

`src/report.py` emits **PDF 1.4 by hand** — catalogue, page tree, one content stream per page, xref
table — because this machine has a PDF *reader* and no writer, and making a judge `pip install`
something before a deliberately dependency-free demo was the worse option. **Courier throughout**,
so every glyph is exactly 600/1000 em and wrapping is arithmetic rather than an approximation
needing an embedded metric table.

**`verify()` REOPENS THE FILE IT JUST WROTE** and asserts every scheduled hour, the headline counts
and the site's own name are present, **plus a layout-bounds check on every placed string** — because
Chrome will not render a PDF headlessly, so it cannot be screenshotted. **That bounds check caught a
line 20.1 pt off the right edge of all three reports on its first run.**

**Which configuration the report shows is a DISPLAY SELECTION BY SEARCH**, not a default:
`pick_block()` scores *informativeness* — mixed modes first, then distinct binding constraints, then
agent-vs-incumbent divergence. The first scoring rule picked a day where the agent free-cooled 24 of
24 hours **and so did the incumbent** — a four-page report demonstrating no advantage. **Page 1 says
it is a snapshot** and tells the reader to compare it against the live page before concluding
anything.

---

## 9. Honest limits — stated before anyone asks

- **The dollar figure covers the CHILLER COMPRESSOR ONLY** *(was: "no dollar or energy figure" — that
  limit was lifted on 2026-08-20, see §8n.6)*. `src/money.py` prices the hours using **kW/ton and
  ¢/kWh both SWEPT over published values** — 608 cells, nothing collapsed to a single number, priced
  in each site's own state. **The fan, pump and cooling-tower term is still NOT sourced and NOT
  claimed, and it has the OPPOSITE SIGN** (free cooling moves more air), so the compressor-only
  figure is an upper bound on the saving, not an estimate of it. Every source in
  `money-sources.md`.
- **No real intake sensor.** The bound is calibrated against FortyGuard's own forecast-vs-outcome pairs;
  end-to-end validation needs a customer's sensor, which closes the loop within a fortnight of deployment.
- **Three real layouts now, and conclusions remain layout-sensitive** *(was: "one reference layout so
  far")*. Ashburn (AWS IAD116→117, 60.3 m facade gap), Chicago (Stream→Equinix CH3, 118.4 m) and
  Dulles (AWS IAD81→IAD62, 137.7 m) each run on **their own** OSM geometry, station record, bound
  and tariff — `audit.py` **fails if any two sites agree on a value**. Two further metros were
  **REFUSED on aerial evidence** (Santa Clara rooftop-cooled, Phoenix not built), and the refusals
  ship. **Dulles shares KIAD with Ashburn deliberately**, which isolates geometry and operator from
  climate. See §8o.
- **21.9 % of hours are calm or lack a bearing** and use an all-bearing mean rise. Recirculation is
  physically *worse* in calm air, so this likely **understates** the effect on a fifth of all hours.
- **The incumbent baseline is given the same conformal calibration machinery**, which is generous to it.
  It is also specified as what operators verifiably run — a **reactive on-site rooftop sensor** with no
  wind and no forecast — and its buffer is TUNED, not assumed. Its fitted buffer is dominated by
  **persistence error** (1.77 → 7.76 °C as notice grows), not by anything we chose, and the result barely
  moves when its instrument error is swept 0.1 → 0.5 °C (+753 / +769 / +792 h/year). **⚠ The earlier
  ≈150 h/year figure is WITHDRAWN** — that incumbent read a station kilometres away, which
  `claims-and-defences.md` §1.15 established is false. See N-56.
- **🔴 FortyGuard's H-hour forecast skill at this site is UNMEASURED**, so every free-cooling figure except
  the ≈67 h floor is conditional on it. **That one measurement would settle the headline.** At 1 h notice
  with no forecast skill at all, the agent **loses 28 h/year** — recorded, not hidden.
- **The humidity gate exists and it COSTS hours, as it should** *(was: "no humidity/enthalpy gate
  yet")*. `src/environment.py` computes dew point and wet-bulb against PsychroLib at **0.2681 °C
  MAE**, and the gate is a **sourced 15 °C dew-point maximum (The Green Grid WP#46 p.6, which gives
  the ASHRAE recommended maxima as 27 °C dry-bulb AND 15 °C dew point)** — replacing an invented
  *"wet-bulb ≤ dry-bulb limit − 3 °C"* whose 3.0 was derived from our own other knob and so failed
  the point-at-the-constant test. **BOTH policies face the gate**, each testing it with a bound from
  its own residuals, and the ladder step is **+85.6 → +118.8 h/yr**. That a gate *raises* the gain
  is not a paradox: the incumbent's humidity bound is fitted on **persistence** residuals and is
  therefore wider, so gating costs it more hours than it costs the agent. **An enthalpy changeover
  proper is still not implemented, and the air-quality gate cannot be backtested at all — no
  five-year air-quality record exists.**
- **Physics validated to ~0.9 K.** Large-recirculation layouts are extrapolation and are labelled so.
- **Wind is not FortyGuard's.** Their API contains no wind field — confirmed from their OpenAPI spec.
  Bearing and speed come from free public data. FortyGuard supplies ambient, which is the dominant term
  and the confound remover.

---

## 10. Build order

1. ✅ Project skeleton, no credential anywhere, `.env.example` only
2. 🔄 **Real Ashburn campus geometry from OpenStreetMap** (free, keyless) → re-run the hour count on real
   footprints and quote the real-site number
3. ☐ The loop, end to end, as one program
4. ☐ Hosted demo: Screen Zero + wind dial + the eight cases
5. ☐ Local Nemotron reasoning traces (measure ensemble VRAM headroom first — 6 GB total)
6. ☐ Public repo with `fortyguard` as collaborator, and the 2–5 minute video

**The API key arrives 2026-08-18.** Until then every module that needs it must fail with a clear message
rather than silently returning nothing. Weather and geometry need no key at all, which is why steps 2–4
can proceed now.

---

## 11. Glossary

| Term | Plain meaning |
|---|---|
| **Intake** | Where a cooling machine draws air in. Everything hinges on its temperature |
| **Recirculation** | A machine breathing back its own hot exhaust |
| **Free cooling / economizer** | Switching off mechanical chillers and cooling with outside air |
| **Changeover limit** | The temperature above which free cooling is no longer safe |
| **Deadband / hysteresis** | Using two thresholds instead of one so a controller does not flip back and forth |
| **Ensemble** | Running the physics many times with slightly different assumptions to get a spread instead of one answer |
| **Conformal bound** | A margin whose success rate is *measured*, not assumed. **The measurement is the point, including when it fails** — ours measured 65.6 % against a 90 % target on live forecasts (§8e), which is exactly the information a nominal claim would have hidden |
| **p90** | The value only 1 run in 10 exceeds. Averages hide danger |
| **Knife edge** | A bearing where the plume boundary sits inside the forecast's own uncertainty, so the answer is genuinely unresolvable — and the agent widens itself |
| **Coverage** | How often the bound's promise actually held |
| **Chiller-hours** | Hours of mechanical cooling avoided. The headline unit, chosen because it needs no unsourced cost constant |
| **Pre-registration** | Writing pass/fail conditions into the test *before* running it, so a threshold can never be moved after seeing data |
| **Point-at-the-constant test** | Our own honesty check: if you can find the deciding number in the source, it is a threshold in a costume |

---

## 12. EVIDENCE AND CITATIONS — every load-bearing claim, with its source

**How to read the verification marks.** This project has already retracted a Trane figure and an
ASHRAE clause that did not exist in the documents they were attributed to (methodology rule 7), so
provenance is tracked per claim, not per document:

- 📘 **primary document opened and read directly** — status carried forward from the project file
  where it was recorded (`damper-agent-plan.md`, `physics-explained.md`, `claims-and-defences.md`).
- 🔎 **re-verified 2026-08-18 in this session** by fetching the source.
- 📗 **named as a standard reference; primary text NOT opened by us.** Cite as a pointer, never as
  evidence.
- ⚠️ **retracted** — listed in §12.9 so it cannot be reused by accident.

---

### 12.1 The problem is real, large, and commercially significant

| Claim we make | Source | Mark |
|---|---|---|
| In a typical data centre with a highly efficient cooling system, *"IT equipment loads can account for over half of the entire facility's energy use"* — i.e. cooling is the other large share | DOE/FEMP/NREL, **Best Practices Guide for Energy-Efficient Data Center Design** (rev. 2024) — [PDF](https://www.energy.gov/sites/default/files/2024-07/best-practice-guide-data-center-design.pdf) | 📘 |
| NetApp's Global Dynamic Laboratory runs **full free cooling >75 % of the year**, partial free cooling **>98 % of the time**, cutting operating costs ~60 % | US EPA **ENERGY STAR**, *Use an Air-Side Economizer* — [page](https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/use-air-side-economizer) | 📘 |
| A Marvell Semiconductor retrofit in Santa Clara saved **270,170 kWh/month (~$324,000/yr)**, ~2-year payback | ENERGY STAR, same page | 📘 |
| Economizers save **~20 % on average** of cooling money/energy/carbon vs a facility with none | The Green Grid, **White Paper #46**, p.2 — [PDF](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf) | 📘 |
| The ASHRAE **recommended maxima are 27 °C dry-bulb AND 15 °C dew point**, and WP#46's own free-cooling hour count adds an hour only when **both** hold. **This is the source of BOTH shipped gates** — `dewpoint_limit_c = 15.0` and the top of the swept `limit_c` — and it replaced an invented 3 °C wet-bulb offset (§8h.7) | The Green Grid, **White Paper #46**, p.6 — same [PDF](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf) | 📘 |
| Water-side economizers are the companion strategy | ENERGY STAR, *Consider Water-Side Economizers* — [page](https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/consider-water-side-economizers) | 📘 |

**⚠️ We do NOT claim a percentage for "cooling is X % of data-centre energy."** Both the DOE guide
(48 pp) and the primary ASHRAE 2011 Thermal Guidelines (45 pp) were searched in full and **neither
states one**; the DOE PUE section only *defines* PUE = 1.0. Recorded in `damper-claims-and-defences.md`.

---

### 12.2 🔴 THE DOCUMENTED REASON OPERATORS DON'T USE FREE COOLING — this is the commercial thesis

| Claim | Source | Mark |
|---|---|---|
| *"Economizer use caused sharp increases in particle concentrations when the economizer vents were open"*, dropping back when vents closed; **annual averages still met ASHRAE standards.** Measured with particle counters at **eight real data centres** in Northern California | Shehabi, Tschudi & Gadgil, **Data Center Economizer Contamination and Humidity Study**, LBNL, 6 Mar 2007, OSTI 971864 — [record](https://www.osti.gov/biblio/971864) · [PDF](https://www.osti.gov/servlets/purl/971864) | 🔎 |
| **There was reluctance from many data-centre owners to use this common cooling technique due to fear of introducing pollutants and potential loss of humidity control**, with concerns about equipment failure from airborne pollutants | same study, stated motivation | 🔎 |
| Companion analysis of filtration vs economizer energy | LBNL-2939E — [PDF](https://seta.lbl.gov/sites/default/files/2939e.pdf) | 📗 |
| Regional energy implications of economizer use | **Energy Implications of Economizer Use in California Data Centers**, OSTI 937579 — [PDF](https://www.osti.gov/servlets/purl/937579) | 📗 |
| Peer-reviewed version of the particle work | *Particle concentrations in data centers*, **Atmospheric Environment** (2008) — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1352231008003166) · [preprint PDF](https://datacenters.lbl.gov/sites/default/files/Partical%20concentations%20data%20centers_2007.pdf) | 📗 |

**Why this reshapes the product.** The barrier to free cooling is not only *"is it cool enough?"* It
is **"is the outside air clean enough and dry enough to let into my hall?"** FortyGuard returns
humidity, wet-bulb **and six air-quality indices** from `/v1/env_params`. So the agent's free-cooling
gate is properly **three gates, not one** — dry-bulb, wet-bulb/enthalpy, and contamination — and all
three inputs come from the sponsor's own product. See §12.4.

---

### 12.3 What operators actually run today — the incumbent, and why it is not a strawman

| Claim | Source | Mark |
|---|---|---|
| Data centres use **on-site rooftop weather stations** wired into BMS/HVAC control (Vantage, GoDaddy named; Orion units) — **not** a distant airport station | Columbia Weather Systems, data-centre applications — [page](https://columbiaweather.com/applications/data-centers/) | 📘 |
| ASHRAE TC 9.9 monitoring guidance concerns **IT-equipment intake air inside the hall** — three sensors per rack, top/middle/bottom, ±0.5 °C | LBNL, **Thermal Guidelines and Temperature Measurements** (2020) — [PDF](https://datacenters.lbl.gov/sites/default/files/FINAL%20Thermal%20Guidelines%20and%20Temp%20Measurements%209-15-2020.pdf) | 📘 |
| In that 27-page document the words **"outdoor", "outside air" and "forecast" do not appear at all** — verified by full-text search. This is the evidence that the incumbent is reactive, not forecast-aware | same document, our own full-text search | 📘 |
| Real economizer controllers use a **deadband/differential to stop cycling**: *"A 2°F and a 1 Btu/lb differential are used to reduce the cycling of the Economizer Available point"* | Honeywell **JADE Economizer** white paper, pp.1–4 — [PDF](https://hvacrassets.net/content/186/handouts/JADE_White_Paper_1.pdf) | 📘 |

**Consequence for our comparison:** the incumbent in `agent.py` is given the same 90 % conformal
machinery, a **de-biased** persistence forecast, and a **perfect sensor at zero notice**. All three
choices favour it. It differs from the agent in exactly two ways — no forecast, no plume awareness —
which are the two things being claimed.

---

### 12.4 Why humidity and air quality gate free cooling — and why dry-bulb alone is not enough

| Claim | Source | Mark |
|---|---|---|
| Real economizer products check **both temperature and humidity**, not temperature alone, because cool-but-damp air risks condensation on cold metal | ENERGY STAR, *Use an Air-Side Economizer* — [page](https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/use-air-side-economizer) | 📘 |
| Enthalpy (not just dry-bulb) is the controlled quantity in practice — the JADE differential is quoted in **Btu/lb**, an enthalpy unit | Honeywell JADE, as above | 📘 |
| Wet-bulb / psychrometric conversions implemented to ASHRAE formulations | **PsychroLib** (MIT) — [repo](https://github.com/psychrometrics/psychrolib); Meyer et al., *JOSS* 4(33):1137 — [doi:10.21105/joss.01137](https://doi.org/10.21105/joss.01137) | 📘 |
| Closed-form wet-bulb approximation, MAE < 0.3 °C, **valid 5–99 % RH, −20 to +50 °C, assumes sea-level pressure** | Stull (2011), *J. Applied Meteorology and Climatology* 50(11):2267–2269, doi:10.1175/JAMC-D-11-0143.1 — [free author copy](https://open.library.ubc.ca/soa/cIRcle/collections/facultyresearchandpublications/52383/items/1.0041967) | 📘 |
| ASHRAE **90.1 §6.5.1** (economizer requirements) and **90.4** (data-centre energy) exist as free read-only versions | ASHRAE — [read-only standards](https://www.ashrae.org/technical-resources/standards-and-guidelines/read-only-versions-of-ashrae-standards) | 📗 |

**N-56 explicitly recorded this as a gap in its own limitations:** *"No humidity or enthalpy gate;
real economizers also limit on wet-bulb, which would reduce hours for BOTH policies."* Closing it is
therefore a correction we owe, not a feature we invented.

---

### 12.5 Why mode switching is constrained — the switch budget and the ramp limit are cited, not chosen

| Claim | Source | Mark |
|---|---|---|
| Excess staged capacity causes *"equipment damage, as well as poor loop temperature control"*; worked example — a 6-chiller plant where running 5 instead of 3 leaves **9 idle compressors ready to inappropriately cycle** | Trane, **Chiller Plant Control for Data Centers**, DC-WPR003A-EN, Dan Berg, Sept 2025 — [page](https://www.trane.com/commercial/north-america/us/en/about-us/newsroom/whitepapers/chiller-plant-control-for-data-centers.html) | 📘 |
| ASHRAE caps the temperature **rate of change** at **20 °C/hr for disk-drive data centres and 5 °C/hr for tape** — quoted from the table footnote: *"5°C/hr for data centers employing tape drives and 20°C/h for data centers employing disk drives"* | ASHRAE **2011 Thermal Guidelines for Data Processing Environments**, Table 4, p.5/8 — [PDF mirror](https://airatwork.com/wp-content/uploads/ASHRAETC99.pdf) ⚠️ *third-party mirror; the official ASHRAE server returned errors when this was fetched* | 📘 |

**This corrected an earlier error of ours:** a *"5 °C per 15-minute window"* clause used in a previous
version **does not exist anywhere in the document.** The real rule is the 20 °C/hr vs 5 °C/hr pair.
Recorded in `damper-agent-plan.md`.

---

### 12.6 Why recirculation was considered at all — and what the physics is built on

| Claim | Source | Mark |
|---|---|---|
| Exhaust-to-intake recirculation is a **design concern with published dilution equations** — Eqs. (18) and (22), turbulence-intensity ratios giving σ_z/σ_y = 0.667, critical wind speed U_H,crit = 400 fpm = 2.03 m/s, the explicit note that neglecting buoyant plume rise gives *"an inherent safety factor"*, and a recommendation of wind-tunnel modelling for complex building environments | **ASHRAE Handbook — HVAC Applications, Chapter 46** (*Building Air Intake and Exhaust Design*), pp. 46.7–46.10. Held locally as `i-p_a19_ch46.pdf` | 📘 |
| Recirculation magnitude calibrated against **six instrumented air-cooled condensers, ~40,000 digitised (wind, recirculation) pairs**; recirculation defined there as *"the difference between the average inlet temperature of all cells minus the minimum cell inlet temperature"* (p.69) | Maulbetsch & DiFilippo, **Effect of Wind on the Performance of Air-Cooled Condensers**, California Energy Commission **CEC-500-2013-065** + Appendix B **-APB**. Held locally in `validation-data/` | 📘 |
| Dispersion coefficients (Pasquill-Gifford), Classes A and D cross-checked independently | Pasquill-Gifford Table 3 — [PDF](https://hazopmalaysia.wordpress.com/wp-content/uploads/2009/07/3-3_dispersion2pasquill-gifford.pdf) | 📘 |
| Urban vs rural coefficient sets (McElroy-Pooler), and the authoritative source for them | EPA **ISC3 User's Guide**, EPA-454/B-95-003b — [PDF](https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf) | 📘 |
| Field validation: **67 Project Prairie Grass (1956) experiments**, *"the most complete available for the analysis of surface layer dispersion"*, spanning 150–600 m — our range of interest | Harmo classic datasets — [index](https://www.harmo.org/classic.php) · [discussion + data](https://www.harmo.org/jsirwin/PrairieGrassDiscussion.html) · [OSF mirror](https://osf.io/u78ac/) | 📘 |
| Wind-tunnel datasets for a box-on-ground plume — *exactly* our geometry (password by request) | University of Hamburg **EWTL/CEDVAL** — [data sets](https://www.mi.uni-hamburg.de/en/arbeitsgruppen/windkanallabor/data-sets.html); [ADMLC list](https://admlc.com/datasets/) | 📘 |
| Briggs dispersion parameterisation, functional form σ_y = a·x·(1+b·x)^(−1/2) — **form confirmed, coefficient values not obtained** | Briggs, via search | 📗 |
| Cooling-tower / condenser fundamentals background | SPX/Marley, **Cooling Tower Fundamentals** (Hensley, 2nd ed.) — [PDF](https://spxcooling.com/wp-content/uploads/Cooling-Tower-Fundamentals.pdf) | 📗 |
| Data-centre cooling-system anatomy, for orientation | SemiAnalysis, *Datacenter Anatomy Part 2: Cooling Systems* — [article](https://newsletter.semianalysis.com/p/datacenter-anatomy-part-2-cooling-systems); Uptime Institute field report — [PDF](https://intelligence.uptimeinstitute.com/sites/default/files/2025-07/UI%20Field%20181_Data%20center%20cooling.pdf) | 📗 |

---

### 12.7 Conformal prediction — the methods we use, and the limit we must state out loud

| Concept | Source | Mark |
|---|---|---|
| **Primary text.** Split conformal, coverage/width evaluation | Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 — [paper](https://arxiv.org/abs/2107.07511) · [code](https://github.com/aangelopoulos/conformal-prediction) · video [1](https://www.youtube.com/watch?v=nql000Lu_iE) [2](https://www.youtube.com/watch?v=TRx4a2u-j7M) [3](https://www.youtube.com/watch?v=37HKrmA5gJE) | 📘 |
| Original tutorial by the founders | Shafer & Vovk, **JMLR** 9:371–421 (2008) — [paper](https://jmlr.org/papers/v9/shafer08a.html) | 📗 |
| Foundational book | Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World*, 2nd ed. 2022, doi:10.1007/978-3-031-06649-8 — [companion site](https://www.alrw.net/) | 📗 |
| 🔴 **Exact distribution-free CONDITIONAL coverage is IMPOSSIBLE in finite samples.** This is the theorem that answers "why not just make it right for every hour?" | Barber, Candès, Ramdas & Tibshirani, **The limits of distribution-free conditional predictive inference**, *Information and Inference* 10(2):455–482 (2021) — [paper](https://arxiv.org/abs/1903.04684) | 📘 |
| ✅ **Group-conditional (Mondrian) validity IS achievable** — calibrate separately within strata. This is what we build | Vovk, **Conditional validity of inductive conformal predictors**, ACML 2012, PMLR 25:475–490 — [paper](https://proceedings.mlr.press/v25/vovk12.html) | 📘 |
| ✅ **Adaptive-width intervals** — wider where the model is less certain | Romano, Patterson & Candès, **Conformalized Quantile Regression**, NeurIPS 2019, arXiv:1905.03222 — [paper](https://arxiv.org/abs/1905.03222) | 📘 |
| ✅ **Coverage under distribution shift, WITHOUT exchangeability** — the correct answer to "weather drifts" | Gibbs & Candès, **Adaptive Conformal Inference Under Distribution Shift**, NeurIPS 2021 — [paper](https://arxiv.org/abs/2106.00170) | 📘 |
| DtACI — cite the JMLR version, not the preprint | Gibbs & Candès, **Conformal Inference for Online Prediction with Arbitrary Distribution Shifts**, **JMLR 25 (2024), paper 22-1218** — [paper](https://jmlr.org/papers/v25/22-1218.html) | 📘 |
| AgACI, on an **electricity-price forecasting** application — framing close to ours | Zaffran, Féron, Goude, Josse & Dieuleveut, **Adaptive Conformal Predictions for Time Series**, ICML 2022, PMLR 162:25834–25866 — [paper](https://proceedings.mlr.press/v162/zaffran22a.html) · [project](https://mzaffran.github.io/acp-ts/) | 📘 |
| EnbPI — conformal intervals for dynamic time series | Xu & Xie, ICML 2021, PMLR 139:11559–11569 — [paper](https://proceedings.mlr.press/v139/xu21h.html) · [code](https://github.com/hamrel-cxu/EnbPI) | 📘 |
| Theory of what happens when exchangeability fails | Barber, Candès, Ramdas & Tibshirani, **Conformal prediction beyond exchangeability**, *Annals of Statistics* 51(2):816–845 (2023) — [paper](https://arxiv.org/abs/2202.13415) | 📘 |
| 🔴 **Multi-horizon / JOINT coverage** — per-hour 90 % does NOT give 90 % across a multi-hour committed run | Stankevičiūtė, Alaa & van der Schaar, **Conformal Time-Series Forecasting**, NeurIPS 2021 — [paper](https://proceedings.neurips.cc/paper/2021/hash/312f1ba2a72318edaaa995a67835fad5-Abstract.html) · [code](https://github.com/kamilest/conformal-rnn) | 📘 |
| Reference implementation to cross-check ours against | **MAPIE** (scikit-learn-contrib) — [docs](https://mapie.readthedocs.io/en/stable/) | 📘 |
| Lecture notes | R. Tibshirani — [conformal](https://www.stat.berkeley.edu/~ryantibs/statlearn-s23/lectures/conformal.pdf) · [distribution shift](https://www.stat.berkeley.edu/~ryantibs/statlearn-s24/lectures/conformal_ds.pdf) | 📗 |
| Curated index | [awesome-conformal-prediction](https://github.com/valeman/awesome-conformal-prediction) | 📗 |

---

### 12.8 FortyGuard's own published claims — the basis of what we assume about their product

| Claim | Source | Mark |
|---|---|---|
| 12-hour horizon, hourly resolution, ML-downscaling description. **Refresh cadence is absent from both pages** and we do not assume one | FortyGuard — [Our Technology](https://www.fortyguard.com/our-technology) · [Introducing 12-Hour Forecasting](https://www.fortyguard.com/post/introducing-12-hour-forecasting-local-temperature-intelligence-for-real-world-operations) | 📘 |
| The 12-hour horizon is **confirmed by our own measurement**: 9.25 h and 11.25 h return data; 13.25 h and 17.25 h return zero tiles; a 9.41 h lead returned 17,862 tiles | our own probes, `fortyguard-api-findings.md` | 📘 |

---

### 12.8a The money conversion — every factor sourced, and both of them swept

Rule 5 attaches to this section, and Session G's citations are held in full in **`money-sources.md`**
(standalone, complete) rather than being restated here. What matters at this level:

| Factor | Value(s) SWEPT | Source, opened and read |
|---|---|---|
| Chiller efficiency, water-cooled packages | centrifugal **0.576** full load / **0.549** IPLV.IP; screw-scroll **0.639** / **0.572** kW/ton | ASHRAE 90.1-2019 minimum path, via **PNNL-29674 p. 221, Table 82** *(reproducing Standard 90.1-2019 Table G3.5.3)* — **PDF page 236, printed in full and read in place** |
| Electricity price — **each site in its OWN state, 4 prices per site** | Ashburn/Dulles (VA): **8.72** commercial and **8.99** industrial 2024 annual, **10.84** / **10.53** May 2026. Chicago (IL): **11.81** / **8.83** / **15.36** / **10.20** | **EIA `table_4.pdf`** (2024 Total Electric Industry, text-extracted with `pypdf`) and **EIA Table 5.6.A** (`.xlsx` parsed as a zip of XML with `zipfile` + `xml.etree` — **no spreadsheet library and no summarising model**) |
| 1 ton of refrigeration | **3.5168528420666667 kW** | definition, not an estimate |

**Both axes are swept rather than chosen — 4 prices × 4 efficiencies × 38 hours rows = 608 cells per
site, and nothing is collapsed to a single number.** Note the sweep is **within** a state: a site is
never priced at another state's tariff, and Illinois commercial (11.81 ¢) is **35 % above** Virginia's
(8.72 ¢), which is exactly why a national average would have been a fifth unsourced assumption.
`audit.py` registers the published factors and one worked cell, so a drifted kW/ton cannot silently
change every dollar figure in the project.

🔴 **What is NOT claimed, and it has the opposite sign.** The figure covers the **chiller compressor
only**. Fans, chilled-water pumps, condenser pumps and cooling-tower fans keep running, and **an
airside economizer moves MORE air, so fan power RISES.** No primary document available to us gave a
defensible °C → fan-kWh conversion for this plant, so the term is left out and labelled — which makes
the published figure an **upper bound on the saving, not an estimate of it.** LBNL PUE material is
carried as context only and is not used in any arithmetic.

---

### 12.9 ⚠️ RETRACTED CITATIONS AND CLAIMS — never reuse these

Kept visible per methodology rule 6. Each died to a check, and knowing why is itself a defence.

| Retracted | Why |
|---|---|
| *"The JADE white paper documents 1,900 economizer-hours/year and 18 % cooling-energy savings"* | **Not found** on opening the primary document. Likely conflated from a search summary. The JADE **2 °F / 1 Btu/lb differential** quote (§12.3) is separate and **does stand.** |
| *"PNNL chiller-plant optimization delivers 33 % annual energy savings and 56 % peak-power reduction"* | **Not found** on opening the Trane page it was attributed to; the PNNL study was never opened. The Trane **chiller-cycling** quote (§12.5) is separate and **does stand.** |
| *"5 °C per 15-minute window"* ASHRAE rate limit | **Does not exist** in the 45-page primary document. Real rule: 20 °C/hr disk, 5 °C/hr tape. |
| *"Engineers pick one number and use it every day of the year"* | **False.** Google DeepMind re-optimises cooling every 5 minutes in production, ~40 % cooling-energy reduction. An NVIDIA judge would know instantly. |
| *"Nobody currently sells a product that looks at the forecast trajectory before deciding whether to switch"* | 🔴 **OVERSTATED — corrected 2026-08-18 by re-fetching the source.** The 2025 review *proposes* its own framework, validates it with *"a combination of simulation (digital twin) and a limited field test"*, and reports *"a pilot deployment … on an actual data center CRAH unit for a short duration (with operator oversight)"* — and it cites DeepMind as deployed at scale. **What is defensible: AI-driven predictive control for data-centre HVAC sits at the simulation-and-limited-pilot stage in the 2025 review literature, and DeepMind's deployed system optimises setpoints from current conditions rather than from an external temperature forecast.** Source: [Heat Pumping Technologies Magazine 43(3) 2025](https://heatpumpingtechnologies.org/articles/heat-pumping-technologies-magazine-vol-43-no-3-2025/ai-driven-predictive-control-for-data-center-hvac-systems/) 🔎 |
| *"Operators read a weather station kilometres away"* | **Verified false.** On-site rooftop stations — §12.3. |
| *"Spatial resolution is the value proposition"* | Measured worth **+0.036 °C.** FortyGuard's value here is the **time** dimension. |
| *"Data centres warm their neighbourhood measurably"* | **Two well-powered nulls**: difference-in-differences +0.016 °C against a published 0.7–0.9 °C; rotation placebo p = 0.42. |
| *"≈150 extra free-cooling hours/year"* | Its incumbent was the false distant station. Superseded by N-56. |
| *"Recirculation rises with wind speed, peaking near 9 m/s"* | **Falsified by field data** — peak in the 0–5 mph bin; the solver built on it was anti-correlated r = −0.869. |
| *"Urban vs rural dispersion coefficients are second-order"* | **Wrong, and measured.** The urban set roughly **halves** the headline (+0.839 → +0.422–0.489 °C). |
| *"FortyGuard's `persistence` analytic is broken"* / *"`heatmap` and `env_params` disagree by ~9 °C"* / *"forecast path is intermittent"* | All three **withdrawn — our own bugs**, incl. the 9-hour timezone error. |
| 🔴 *"a bound that is right 90 % of the time — verified at 90.0 % ± 0.4 pp"* — still present in `claims-and-defences.md` §3 | **STALE. That figure is the SIMULATED bound.** On live FortyGuard forecasts the measured value is **65.6 %**, and it FAILED its pre-registered conditions. Quote 65.6 % until ~10 calibration days exist. |

---
