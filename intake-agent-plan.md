# INTAKE — an autonomous intake-condition agent for mission-critical facilities

**FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)**
Build sprint **Aug 18–30, 2026** · submission Aug 30 · prep window Aug 10–17

> **Version 3, rewritten 2026-08-11.** Supersedes the earlier plan entirely. Four claims in the
> previous version were retracted after testing and one piece of physics was falsified by real
> measurements and refitted. Every number here carries a tag: **[M]** measured by us, **[F]** from
> published field measurements, **[L]** literature, **[S]** stub with no measurement behind it.
> The audit trail of what died and why is in [claims-and-defences.md](claims-and-defences.md) §2.
>
> ⚠ **PHYSICS NUMBERS REVISED 2026-08-12.** A defect was found and fixed: buildings were implemented
> as fixed-temperature cells, which absorbed heat instead of deflecting it, and 21 of the 49 cells in
> the intake averaging disc were *inside* the neighbour building and pinned to zero rise. **Every
> absolute intake-rise figure was biased LOW by roughly a factor of two.** All five dependent tests
> were re-run. Headline **+0.455 → +0.839 °C**, band **0.219–0.940 → 0.415–1.713 °C**, knife-edge
> ratio **13.6× → 27.0×** (stronger). **No qualitative conclusion changed.** Full account, including
> the one test that now fails its own pre-registered threshold and why that threshold was mis-specified
> rather than the physics wrong, is in
> [claims-and-defences.md §1.14](claims-and-defences.md). Sections below marked with the old figures
> are superseded by that entry.

> ## 🔶 VERSION 4 — 2026-08-16. READ PART 0 BEFORE ANYTHING ELSE.
>
> **The agentic core of Version 3 is dead.** The "online stopping rule" that Parts 3, 4 and 6 below are
> built around — *when* to stage reserve cooling — has been closed by measurement, not by opinion, and
> it is closed for **every cost model**, not just the one we guessed. **A different decision organ has
> replaced it: margin sizing**, which passed its own pre-registered test with a stated requirement
> attached.
>
> **Nothing in Version 3 has been deleted.** Every dead end, retraction and wrong turn below is kept
> deliberately. This document is the record of a two-week research sprint, not a product brochure, and
> the sprint is the more honest thing to show. Where a section is superseded it is marked
> **⚠ SUPERSEDED — see Part 0**, and the original text is left in place so a reader can see what we
> believed, when, and what changed our minds.
>
> **Version 4 additions:** Part 0 (the sprint record), Part 11 (the real FortyGuard API surface, all six
> endpoints, four new defects), and rewritten §3.1–3.3, §4, §6, §7.2 and §8.

---

# PART 0 — THE SPRINT RECORD

**This part exists because the process is the result.** Five candidate decision cores were built and
tested. Four died. The fifth survives with a measured requirement. Every verdict below came from a
test whose pass/fail condition was written into the file **before the test was run**, and every number
carries `n`, `SE` and a 95 % CI where it is an estimate.

> **The rule we held ourselves to:** *point at the constant.* For any behaviour claimed to be
> "agentic", can you find, in the source code, the number a human wrote that produces it? If yes, it
> is a threshold in a costume and must be labelled as such. That single test is what killed four of
> the five cores, and it is the reason we trust the fifth.

## 0.1 The five decision cores, and what happened to each

| # | Core | Verdict | The number that decided it |
|---|---|---|---|
| 1 | **Forecast sharpening** (N-25) | ❌ **underpowered, and the wrong statistic** | `b = −0.0608, SE 0.0803, 95 % CI [−0.316, +0.195]`. The CI contains 0, 0.129 *and* 0.187, so it establishes nothing — **but it excludes 0.500**, and 0.500 is the value Version 3's headline "+0.356, 11.2 σ" was computed with. Separately it fitted the **spatial** sd across ~17,862 tiles on one day, when the decision needs the **day-to-day** sd of the **site-level** error — quantities ~9× apart. |
| 2 | **Day-to-day sharpening** (N-42) | ❌ **unresolvable on the calendar** | Estimator built and validated against synthetic data with known answers (recovered 0.506 from 0.500, 0.179 from 0.187). Then power analysis: **80–160 days needed.** Also found an attenuation trap — a day-level offset common to all leads squashes a true `b = 0.50` to a measured **0.138**. We had 15 days. **Recommendation issued and honoured: do not buy the extra leads (~8,440 credits/day).** |
| 3 | **Wind-direction sharpening** (N-40) | ❌ **decisive fail, well powered** | σ_recirc went the **wrong way**: 0.26 °C at 1 h vs 0.16 °C at 12 h. `b = −0.1166, SE 0.0310, t = −3.77, CI [−0.186, −0.048]` — excludes zero. **It also exposed a real defect of ours:** `solver.ensemble()` perturbs direction by **±15°** while the measured error is **47–72°**, so we were understating the dominant uncertainty by ~4×. |
| 4 | **Adaptive commitment** (N-44, N-45) | ❌ **P1 passed, P2 failed, then closed on PHYSICS** | See §0.2 — this one is worth reading in full, because the reason it died is not the reason we first thought. |
| 5 | **Margin sizing** (N-46, N-46b) | ✅ **PASSES, with a requirement** | See §0.3. |

## 0.2 Core 4 in full — the most instructive failure in the project

**N-44's P1 is a real, positive finding and it still stands.** Measured **AUC** (the ability of the
ensemble p90 to discriminate breach from no-breach) against lead:

| lead | 12 h | 9 h | 6 h | **3 h** | 2 h | 1 h |
|---|---|---|---|---|---|---|
| AUC | 0.6762 | 0.7451 | 0.7671 | **0.8531** | 0.8520 | 0.8396 |

**Gain 12 h → 3 h = +0.1634, bootstrap CIs disjoint.** And recorded honestly for the first time in
Version 4: **AUC is not monotonic. It peaks at 3 h and falls back to 0.8396 at 1 h** — which is exactly
why the tuned adversary independently settled on hour 3.

**This explains N-40's inversion rather than contradicting it.** σ-in-Celsius fell while discriminating
power rose, because at long lead the ensemble sprays across the compass and collapses toward "probably
nothing" (low sd, low information); at short lead it concentrates and becomes genuinely bimodal (high
sd, high information). **σ measures dilution; AUC measures confidence.** Both measurements are correct.

**P2 then failed three times across structurally different implementations:** a hand-written heuristic
(**−6.17 σ**), binned backward induction with a fitted transition matrix (**−21.59 σ**, after finding
and fixing a real bug where the final transition row silently defaulted to uniform), and a
regression-based Longstaff–Schwartz DP using `sklearn.isotonic.IsotonicRegression` (**−19.37 σ**).
**P3 — the anti-threshold guard — actually PASSED at 66.5 % off-modal.** The policy genuinely varied
its timing. It simply lost.

**A clairvoyant bound proved the cost model was internally consistent** (13.97 vs the fixed rule's
21.11, and the fixed rule was never strictly cheaper on any single day), so the loss was not a bug.
On **3,376 of 4,000 days (84 %) the optimal action was never to commit at all**, committing when
worth it gained **112.9** against a loss of only **3.0** when not — **break-even precision 2.6 % against
a base rate of 15.6 %.** So "commit early, almost always" was near-optimal, and the DP's high commit
rate was economically *correct*.

### ⚠ Then N-45 found the specification was degenerate, and closed the question properly

Re-reading the test to rebuild its cost model from published data, **five defects surfaced, all pushing
the same way:**

1. **`AMB = 30.0` — ambient was FROZEN on all 4,000 days.** The outcome was the recirculation rise
   alone (0–0.4 °C), never the intake temperature. **The dominant driver of overheating — the weather —
   was not in the decision problem.**
2. **The breach threshold was a quantile of the model's own output:** `thr = np.percentile(allr, 75)`
   → **0.00978 °C**, with the code commenting that it was set that way *"so the decision is non-trivial
   by construction."* That is below any real sensor's resolution.
3. **`CAPACITY_RISE = 0.25 °C`, tagged `[S]` — 25.6× the threshold.** The remedy was 25× stronger than
   the problem.
4. **`C_EXCURSION = 120.0` and `C_STAGE_FIXED = 2.0` were unsourced**, inherited from a block whose own
   comment reads `# [S] plant stubs`.
5. A stale comment claimed `CAPACITY_RISE` was "swept in the sensitivity block"; **no such block
   existed.**

**Then real data settled it.** 534 real summer days at KIAD (2021–2026, site-local 16:00): ambient
**min 17.8 · median 29.4 · p90 33.3 · p99 36.7 · max 37.2 °C.**

| ASHRAE Allowable limit | Ambient alone breaches | A 1.00 °C remedy flips | A 0.25–0.40 °C remedy flips |
|---|---|---|---|
| **A2 = 35 °C** | 26 days (4.9 %) | 10 days (1.9 %) | none the data can resolve |
| **A3 = 40 °C** | 0 days | 0 days | 0 — hottest ambient in six summers is **37.22 °C**, a **2.78 °C** gap |

> **`C_EXCURSION` prices the CONSEQUENCE of an action. It cannot change the action's EFFECTIVENESS.**
> No excursion cost, at any ratio across four decades, makes a 0.25 °C lever close a 0.56–2.78 °C gap.
> **A planned 65-configuration cost sweep was therefore cancelled before running** — it would have
> burned a day re-deriving arithmetic. This is a stronger closure than N-44's −19.37 σ, because it
> holds for *every* cost model rather than one guessed set of constants.

**⚠ Resolution caveat, volunteered:** ASOS reports temperature in whole degrees Fahrenheit —
**confirmed, 100.0 % of 534 readings** — so the data sits on a **0.556 °C** grid and a 0.40 °C band is
narrower than the data's own resolution. **"Zero days" is not a measurement.** The honest form: *the
nearest resolvable ambient below 35 °C is 34.44 °C (94 °F), on 10 of 534 days, requiring ≥0.56 °C to
flip.* The A3 result is unaffected by resolution.

### 🟢 And N-45 produced the project's first favourable sharpening result

Ambient persistence-anomaly error sd: **1.572 °C at 1 h → 4.125 °C at 12 h, ratio 2.62×.**
Fitted **`b = +0.3414, SE 0.0443, 95 % CI [+0.2427, +0.4402]`, n = 12 leads** — excludes zero.

**Why this one propagates where N-40's did not:** ambient enters intake temperature **additively**, so a
sharper ambient forecast flows straight through to a sharper intake forecast. There is no dilution
mechanism. *(Two caveats: the 12 lead points come from overlapping data on the same 534 days so the OLS
CI is optimistic; and persistence is a lower bound on real forecast skill.)*

**A defect found in the raw fetch and fixed before any policy ran:** raw persistence error had a mean
of **+8.784 °C at 12 h lead** — that is the diurnal cycle, not forecast error, because lead 12 from a
16:00 target compares against 04:00. Per-lead means are subtracted, leaving the anomaly error.

## 0.3 Core 5 — margin sizing. The one that survives.

**The claim, stated falsifiably:** an operator who cannot see the recirculation at their own intake must
hold a margin sized for the **worst case over all wind directions, permanently**. An agent that models
it per hour should hold a **smaller** margin **at the same safety level**.

**Why this comparison isolates our contribution, where the earlier framings could not:** both policies
handle ambient identically, **so ambient cancels.** The only difference is whether the recirculation
increment is modelled or assumed worst-case. In core 4, ambient (±1.5–4 °C) swamped recirculation
(0.25–0.40 °C) and the physics was a 10–25 % correction. **Here the physics is the entire signal by
construction.**

**The adversary is not a strawman:** the **smallest constant margin achieving ≥90 % coverage on training
days** — exactly what a competent engineer builds with the same data and no model. Both policies get
**one** calibration constant from the identical one-sided split-conformal construction.

**N-46, at measured persistence-quality wind forecasts: FAILED.**

| Condition | Verdict | |
|---|---|---|
| **P1** margin lower by ≥2 paired SE | **FAIL** | **−0.0076 ± 0.0035 °C = −2.19 σ** — agent's margin was *larger* |
| P2 no safety sold to buy it | PASS | agent **90.0 %** vs fixed **89.9 %** held-out coverage |
| P3 margin genuinely varies | PASS | sd **0.2200 °C**, below fixed on **55.3 %** of days |

**The mechanism, measured — and it was not what the pre-registration predicted.** The prediction was
that a large conformal correction would eat the saving. **The correction was negligible: q = +0.0007 °C.**
The real cause: the rise field is **severely zero-inflated** — `median p90 across all 72 direction bins
= 0.0000 °C`, peak **0.7887 °C at 270°** — so the unconditional 90th percentile of realised rise is only
**0.2144 °C**, and that is all a constant must cover. Meanwhile **direction forecast error of 47.7°
(1 h) to 72.7° (12 h) smears the narrow plume across most of the compass**, so the agent's p90 is
inflated on most days: mean agent margin **0.2220 °C** against a real-frequency-weighted mean p90 of only
**0.0662 °C**. Same dilution mechanism as N-40/N-44, now acting on an upper quantile.

**N-46b — the decisive question was not "does it work" but "how good must the wind forecast be".**
Bands were fixed before the run (≥25° viable / 10–25° demanding / <10° or none = dead). 20,000 train +
20,000 held-out days, **paired design** (identical truths across rows, only error magnitude changes —
which is why the tuned constant is exactly 0.2116 on every line):

| Direction error sd | Fixed | Agent | Saved | σ | % of margin |
|---|---|---|---|---|---|
| 0° (perfect) | 0.2116 | 0.0656 | **+0.1460** | +124.2 | **69.0 %** |
| 10° | 0.2116 | 0.1072 | +0.1045 | +70.1 | 49.4 % |
| 20° | 0.2116 | 0.1587 | +0.0529 | +31.3 | 25.0 % |
| 25° | 0.2116 | 0.1777 | +0.0339 | +19.8 | 16.0 % |
| **40° ← crossover** | 0.2116 | 0.2074 | **+0.0043** | **+2.55** | 2.0 % |
| 50° | 0.2116 | 0.2106 | +0.0010 | +0.63 | 0.5 % |
| 68.37° (measured persistence) | 0.2116 | 0.2128 | −0.0012 | −0.75 | — |

> ### ✅ VERDICT: **the margin thesis is viable if the wind-direction forecast beats ≈40° sd at 9 h lead.**
> Measured persistence is 68.37°, so **a real forecast must be ~1.7× better than persistence.**

**Three things that make this trustworthy:**
- **Port verified.** The vectorised implementation reproduces N-46's loop version — the *saving* agrees
  to 0.0005 °C (−0.0081 vs −0.0076); σ differs only by sample size (−2.19 × √5 = −4.9 ≈ −5.28).
- **The saving is understated, not flattered.** Coverage *rises* as error shrinks (90.1 % → 93.6 %), so
  at good forecast quality the agent delivers **more** safety *and* a smaller margin. It dominates on
  both axes and could tighten further by targeting exactly 90 %.
- **It explains the earlier failure** instead of contradicting it: persistence sits just past the
  crossover.

**⚠ Two things NOT established, and no claim may be made until they are:**
1. **That any real forecast meets 40°.** Not measured. And note the requirement lands on the **wind**
   forecast — free public NWS/HRRR data — **not on FortyGuard**, whose API contains no wind field at all
   (confirmed from their OpenAPI spec, Part 11).
2. **That the absolute magnitude is worth money.** The saving is **0.05–0.15 °C** at plausible forecast
   quality. **No energy or dollar figure may be quoted**, because the °C → kWh conversion requires a
   chiller-efficiency number that **could not be found in any primary document on disk** (Trane, Green
   Grid WP46 and ASHRAE Handbook ch. 46 were all searched; the Trane whitepaper is qualitative and
   contains no kW or cost figure). The obvious lever on absolute size is **site layout** — this is one
   deliberately modest geometry, and N-28 already showed layout sensitivity.

## 0.4 Ideas we dropped, and the honest reason for each

Kept because a judge should see the reasoning, not just the survivor.

| Dropped | Why |
|---|---|
| **Fleet compute allocation** (N-20) | Equal split wins. All four concentration strategies lost; random beat ours. **−2.7 σ** on the calibrated solver. Implemented as a one-line rule, which is the correct answer. |
| **Multi-site triage of a scarce physical resource** (N-43) | **−3.63 σ** against a tuned point-forecast ranking baseline. A sign-inversion bug was found and fixed *first* and the verdict survived it (−5.51 σ → −3.63 σ). A point forecast captures nearly all the signal in ranking sites by predicted temperature. |
| **Buying extra forecast leads to measure sharpening** | ~8,440 credits/day, and the power analysis says it cannot resolve inside the hackathon calendar. Declined. |
| **The 65-configuration cost sweep** (planned N-45) | Cancelled *before running* once the action was shown to be ineffective at its size. Cost ratios cannot fix an ineffective action. |
| **⚠ Credit-budget perception scheduling** | Proposed as a decision core, then **withdrawn on the user's objection, which was correct on two counts.** FortyGuard *sells* API credits, so an agent whose talent is minimising API calls optimises **against the sponsor's revenue model**. And it fails on economics: the entire data budget is **1,000,000 credits for $79/month**, a rounding error against the cooling bill it exists to reduce. Optimising a rounding error is not a product. |
| **Earth-2 / CorrDiff** | NIM requires ≥40 GB VRAM; the dev machine has **6 GB**. Its 3 km resolution is also far coarser than the ~200 m separations that matter here. Cut on measurement, not preference. |
| **RAPIDS** | No bottleneck it addresses. Including it would have been logo-driven. |
| **DAMPER as flagship** | A separate free-cooling-switch agent, honestly self-scored at **~45–50/100**: it sidelines FortyGuard (its validated test used a single NOAA station, so a generic weather API would do), needs no GPU, and its "adaptive" policy is a pre-tuned deterministic function. Kept as documented supporting work, not the entry. |
| **Deriving site geometry from FortyGuard** | Tested with two paid calls on 2026-08-16 and **ruled out** — see Part 11. `solver.demo_site()` stays hand-specified, and that is stated as a limitation rather than hidden. |

## 0.5 What actually survived — the agent, organ by organ

Graded against the standard agent ladder (Russell & Norvig, *AIMA* ch. 2), whose top rung — a
**learning agent** — has four organs: a performance element that acts, a **critic** that scores it, a
**learning element** that improves it, and a **problem generator** that seeks informative experience.

| Organ | Status | Evidence, and the point-at-the-constant test |
|---|---|---|
| **Perception** | ✅ real | FortyGuard `heatmap` + `env_params` + public wind, every cycle. *Earns little on its own — any script can fetch data.* |
| **World model** | ✅ **real and validated** | 2-D advection–diffusion solver computing intake air 60 m downwind — **a quantity in no dataset on Earth.** Analytic agreement **2.9 × 10⁻¹⁰**, heat conserved **7.5 × 10⁻¹²**, **67** Project Prairie Grass 1956 field experiments, coefficients cross-checked against EPA ISC3. **Not in the source: it is the solution of a PDE.** |
| **Belief under uncertainty** | ✅ real | 100-member GPU ensemble → a distribution, not a point. **93.46×** speed-up (quote the lower repeat, **72.7×**), CPU/GPU agreement **6.95 × 10⁻⁵ °C**. |
| **Emergent caution** ⭐ | ✅ **strongest single result** | Ensemble spread **27.04×** wider at the geometric edge than in safe sectors. **There is no rule about plumes anywhere in the code**, and `285` does not appear in the source — you could not put it there, because knowing that bearing is dangerous requires running the physics first. |
| **Decision (performance element)** | ✅ **margin sizing**, with the §0.3 requirement | Hold the smallest margin the physics and the measured track record can defend; widen when the geometry is ambiguous. **0.0656 °C at good forecast quality vs 0.2128 °C at poor** — not a constant in the source. |
| **Critic** | ✅ **live and unattended** | `test_n26_coverage.py` on a daily scheduled task, **96.8 % measured coverage against a 90 % promise**. Honest status: **1 of 3 required test days, verdict `NOT YET DECIDABLE`.** Aug 14 is a permanent gap (machine asleep; a forecast cannot be made retroactively). |
| **Learning element** | ✅ real but narrow | The conformal bound updates from measured residuals. The 90 % target is a **goal**, which an agent is entitled to; the **margin in °C** is computed and moves daily. |
| **Problem generator** | ❌ **not built** | The credit-budget version was withdrawn (§0.4). No replacement has been justified by evidence yet, and one will not be invented to fill the row. |

**Honest summary:** a validated world model, calibrated belief, emergent caution nobody programmed, a
live self-scoring critic, and a decision organ with a measured basis and a stated dependency. **What is
missing is the problem generator, and — as of 2026-08-16 — an assembled loop, a public repository, a
hosted demo and a video**, all of which are hard submission requirements. That gap is the sprint's real
remaining risk, and it is larger than any physics question left open.

---

# PART 1 — The idea, in plain words

## 1.1 The problem, which is FortyGuard's own

Their Track 3 challenge, quoted:

> *"Operators of mission-critical facilities like data centers and nuclear plants face escalating
> cooling loads and reliability risks as external heat intensifies. Even minor temperature
> fluctuations around air intakes, cooling towers, and external walls can impact uptime, energy use,
> and equipment lifespan. Yet, most environmental monitoring systems only track indoor conditions,
> overlooking the hyperlocal microclimate dynamics that develop around **dense equipment, reflective
> surfaces, or nearby structures**. This blind spot limits predictive maintenance accuracy, leading
> to **overcooling**, component degradation, and higher operational costs."*

In plain words: a data centre is a building full of computers making heat. Outside, machines dump
that heat into the air. **How hard they must work depends on the temperature of the air they suck
in** — the *intake*. Cool air is cheap; warm air is expensive.

Operators cannot see that air well, so **they run the cooling harder than necessary, all the time,
as insurance.** That is **overcooling**, and it is the word FortyGuard's own brief uses.

## 1.2 Why a better measurement does not fix it

**The airport story.** You must be at the airport by 9:00. The drive takes 30 minutes. You leave at
8:00, not 8:30, because traffic might be bad. That buffer is not stupidity — it is insurance against
not knowing.

Now someone gives you a *better estimate*: *"today the drive is 32 minutes."* **Do you leave at
8:28?** No. You still do not know how wrong they might be.

What would let you leave later:

> *"I have timed this exact drive 200 times. **Nine times out of ten it took under 38 minutes.**
> Here is the record."*

> **Overcooling is a margin problem, not a measurement problem. Margins shrink on evidence, not on
> precision. A better number does not shrink a buffer — a track record with a success rate does.**

**This is not just an analogy.** [MPC under weather-forecast uncertainty](https://www.sciencedirect.com/science/article/pii/S037877882101077X)
measured it [L]: predictive control **with** a calibrated forecast-error model returned **3.4 %**
weekly saving and **73 % fewer** temperature violations; **without** one, **0.7 %** saving and
violations **20 % worse than doing nothing.** The calibrated margin is not a refinement wrapped
around the physics — it is the difference between helping and harming.

## 1.3 ⚠ "Can't you just put a sensor there?" — the honest answer

**Yes. A thermometer at the intake costs about fifty dollars, and most facilities already have one.**

**What we concede:** for *"what is my intake temperature right now?"*, a sensor wins outright. It is
cheaper, more accurate, and it is the ground truth. We are not competing with it.

**But a sensor answers one question at one spot.** It cannot answer: what will it be in six hours ·
what would it be at a site that does not exist yet · what if we add 20 MW of load · what if the
neighbour builds next door · what about the hottest day of the next decade (which by definition is
not in its history) · which of six condenser banks is worst *today*.

> **The sensor is not our competitor. It is our examiner.**
>
> We forecast; it tells us afterwards whether we were right. That measured track record is what turns
> a guess into a bound, which is the only thing that lets the margin shrink. **Without the sensor
> there is no honest bound.**

**One-line pitch:** *A sensor tells you that you are already too hot. We tell you six hours
beforehand — and we let the sensor prove we were right.*

## 1.4 What we discovered that changes the shape of the product

Two things came out of testing that were not in the original idea.

**(a) Wind direction behaves like a switch, not a dial.** The exhaust plume either points at the
intake or it does not. Turn the wind 20° and you go from nothing to the full effect. Wind *speed*, by
contrast, only dilutes — gradual and forgiving.

**Measured [M]:** across eight compass sectors, five of eight give an intake rise of **0.000 °C**;
one gives **+0.708 °C**. Near-binary.

**(b) The plume is narrower than the wind forecast's own uncertainty.** The bad sector is ~40° wide;
a direction forecast carries about ±15°. So whenever the wind is anywhere near the bad sector, **you
are partly on the edge by construction** — the share of ensemble members in the hot zone **never
exceeds 72 %**, even pointing squarely at the plume [M].

> **There is never a clean "definitely hot" day. A point forecast of "wind from 270°" is
> *permanently* ambiguous at this geometry. The uncertainty is not a refinement bolted on at the end
> — it is the dominant feature of the problem.**

That single finding is the strongest justification in the project for producing a **bound** rather
than a number, and it is what the live demo shows (Part 9).

## 1.5 Why FortyGuard is required

A sensor gives one point, in the present, at a building that already exists. FortyGuard gives:

- **Air temperature across a whole area in 60 m squares** [M] — so every intake, not just the
  instrumented one, and every candidate parcel with no building on it yet
- **A rolling forecast** — which is what anticipation requires
- **Years of history** — how a bound gets calibrated
- **And it tracks reality** [M]: when the airport thermometer rose 9.6 °C between two days,
  FortyGuard's field rose **11.13 °C** — ratio 1.16. It is live data, not a climate map

**Where it enters technically:** FortyGuard sets the **boundary condition** of the physics solve —
the temperature of the air flowing into the site. Remove it and you are back to a station reading
from miles away, which a [published review](https://link.springer.com/article/10.1007/s12273-020-0759-2)
says deviates from a real site by amounts *"large enough to influence design and operation
decisions"* [L].

### 1.5b ⭐ "But 60 m can't resolve an intake — so why use FortyGuard at all?" (added 2026-08-16)

**This is the sharpest question anyone can ask about the project, and the answer is quantitative.**
The objection assumes there is one quantity at one scale. There are **two**, at two different scales:

| Term | Physical scale | Who supplies it |
|---|---|---|
| **The ambient air arriving at the site** | **neighbourhood.** This air has been mixing over hundreds of metres upwind — it is not a few-metres property, and 60 m is the *appropriate* resolution for it | **FortyGuard** |
| **The recirculation increment** — your own exhaust curling back onto your own intake | **a few metres** | **our solver** |

**So the division is physics, not a workaround.** Now the numbers that make it decisive:

| Quantity | Measured |
|---|---|
| FortyGuard field variation, 60 m → 2 km | median \|ΔT\| **0.011 / 0.025 / 0.048 / 0.093 / 0.170 / 0.301 °C** [M] |
| Spatial contrast across the 64 km² AOI | **1.3–1.5 °C**, and the sd **doubles on hot days** (0.24 → 0.42) [M] |
| **The entire recirculation term our physics computes** | **0 – 0.855 °C** [M] |
| **The margin saving we claim** | **0.05 – 0.15 °C** [M] |

> **The spatial correction FortyGuard supplies is LARGER than the whole quantity our solver computes.**
> Substitute a station reading from miles away and you inject roughly a degree of error into a
> sub-degree answer — the solver would be computing 0.1 °C on top of a 1 °C mistake. **FortyGuard is
> not a convenience here; it is what makes a sub-degree question askable at all.**

**And for the forecast leg there is no substitute.** The nearest alternative is NWS/HRRR at **3 km** —
a cell **50× coarser**, averaging over ~0.3–0.5 °C of real variation, which *by itself* exceeds the
0.05–0.15 °C the agent is trying to save. **FortyGuard's resolution is a precondition for the margin
claim being meaningful, not a nice-to-have.**

**Third, and unique to them:** the **forecast↔history symmetry** — the *same request shape* returns a
prediction, and later the outcome. Residual bias **+0.349 °C**, sd **0.150**, **n = 6,875** [M]. **That
pairing is what makes a calibrated conformal bound possible, and the bound is the product.** No other
source offers it at 60 m.

**The one-line answer for a judge:**

> *"Our computed signal is a few tenths of a degree. A station reading is wrong by about a degree.
> FortyGuard is what makes a sub-degree question askable."*

## 1.6 Why NVIDIA is required

**⚠ REFRAMED 2026-08-16.** This section used to open by leading with FortyGuard's *limitation*
(*"60 m cannot resolve it"*), which invites exactly the objection answered in §1.5b and undersells the
data the whole product rests on. **Lead with what 60 m enables — see §1.5b — and only then explain what
the GPU adds on top of it.**

FortyGuard resolves the incoming air mass at the scale that quantity genuinely varies on. What no
outdoor field product can resolve is a facility's own perturbation of it: the building's geometry, its
exhaust curling back, and the structure next door — **exactly the blind spot FortyGuard names** in its
own brief (*"dense equipment, reflective surfaces, or nearby structures"*). **Bridging that last step
is a physics problem, and the physics is where the GPU earns its place.**

**And here is why the GPU is load-bearing rather than decorative. Lead with the loss:**

| Workload | CPU | GPU | |
|---|---|---|---|
| **single** solve, **first in the process** | **0.593 s** | 2.594 s | 🔴 **GPU LOSES** — 2.37 s of it is kernel compile |
| single solve, kernel already compiled | 0.712 s | **0.144 s** | GPU wins 4.9× — the compile is a one-off |
| **100-member ensemble** | 63.6 s / 61.8 s | **0.9 s / 0.7 s** | ✅ **72.7× and 93.5×** on two runs [M] |
| 20 sites × 100 members | 1,272 s (**21.2 min**) | **13–17 s** | — |

> **Say 72.7×, the lower of the two.** Same code, same GPU, two runs a week apart: the spread is
> CPU-side timing variance on a laptop, not anything about the port. Quoting the higher number and
> being unable to reproduce it is worse than quoting the lower one and beating it.
>
> **And be precise about the loss.** The GPU loses the *first* solve in a process because compiling
> the kernel costs ~2.4 s. That cost is paid once, not per solve. It is still worth leading with —
> it shows the number was measured rather than assumed — but do not let it become "the GPU is slower
> at single solves", which is false once the cache is warm.

> **A single solve is not the workload.** To say *"90 % of the time it stays below X"* the physics
> must run across a spread of conditions, and the **distribution is the product**. The bound needs
> the ensemble; the ensemble needs the GPU. Remove the GPU and a named stage stops working: a
> 21-minute cycle cannot sit inside an hourly decision loop.

**Second argument, and it is the one that lands:** the GPU **makes the honesty affordable.** Our
sensitivity sweep is 1,500 solves — **9.0 seconds** on the GPU, ~16 minutes on CPU. At 16 minutes you
do not sweep your assumptions routinely, and an unswept assumption is how a wrong number reaches a
judge.

## 1.7 The whole thing in one paragraph

> Data centres waste electricity cooling harder than needed, because they cannot see the air arriving
> at their equipment and so keep a permanent safety buffer. A better thermometer does not shrink that
> buffer, any more than a better traffic estimate makes you leave for the airport later. What shrinks
> a buffer is a track record: *"nine times out of ten it stays below this."* So: FortyGuard's 60 m
> field gives the neighbourhood air. A physics solver — **calibrated against 40,000 real
> measurements from six instrumented plants** — carries it the last 60 metres to the actual intake,
> run a hundred times on an NVIDIA GPU to produce a spread rather than a guess. A conformal bound
> turns that spread into a margin that is **verifiably right 90 % of the time**. An agent then decides
> **when** to bring reserve cooling online — a *time*, not a yes/no, provably beyond what any fixed
> rule can express. And every day it grades itself against what actually happened, using the
> customer's own sensor as the examiner.

---

# PART 2 — What is verified, and what it cost

**Total credits spent: 0.** ~125 calls issued 2026-08-11; the audited key's billing cycle closed
19 July and the meter is frozen (`cycle_remaining_credits` unchanged throughout).

## 2.1 FortyGuard capabilities [M]

| Finding | Value | Why it matters here |
|---|---|---|
| **Lattice stability** | **6,875/6,875** and **17,862/17,862** tiles byte-identical across calls and dates | Per-site time series are valid → self-scoring works |
| **Tracks real weather** | KIAD +9.6 °C → field +11.13 °C, **ratio 1.16** | Live, not climatological. The fatal risk, closed |
| **Genuine 60 m resolution** | smooth monotonic \|ΔT\| decay 0.011 / 0.025 / 0.048 / 0.093 / 0.170 / 0.301 °C at 60 → 2000 m, **no jump** | Not upsampled from a coarser product |
| **Noise floor** | ≈**0.09 °C** at 500 m | The scale any real effect must beat |
| **Spatial contrast** | ~1.3–1.5 °C across 64 km²; sd **doubles** on hot days (0.24 → 0.42) | The signal grows when it matters |
| **Persistence** | ~**73 %** of the spatial pattern repeats day to day | Learnable per-site structure |
| **Capacity** | 17,862 tiles over 64 km² at 60 m in **67 s**, one call | Cheap perception |
| **Forecast ↔ history symmetry** | same request shape gives prediction then outcome. Residual on peak temperature: bias **+0.349 °C**, sd **0.150**, \|res\| q90 **0.495 °C**, n = 6,875 | **This is what makes a calibrated bound possible at all** |
| **Air, not surface** | diurnal amplitude **7.8–8.3 °C** | Correct variable |
| **Diurnal cycle correct** | 21.1 °C at 04:00–06:00 → **33.8 °C at 16:00–18:00**, Ashburn August | Also proves `start_time` is site-local |
| **Pricing** | **4,220 credits/heatmap**, flat in area, granularity, hours and analytic type. From 278,520 cr ÷ 66 calls | Big polygons are free. Budget with confidence |
| **`env_params`** | 15 parameters + `elevation` + `solar_irradiance` (clear-sky GHI/DNI/DHI), **and it serves future timestamps** | Kept working when the heatmap forecast path did not |

## 2.2 Physics, validated against real measurements [F]

**Source:** Maulbetsch & DiFilippo, *Effect of Wind on the Performance of Air-Cooled Condensers*,
California Energy Commission **CEC-500-2013-065** (2010) + Appendix B (2008). Six instrumented
power-plant condensers, 1-minute data. Public domain. PDFs preserved in
[validation-data/](validation-data/). **~40,000 points, digitised from published vector figures —
never describe this as a "downloaded dataset."**

| Check | Result |
|---|---|
| Solver physics checks | **6/6 pass** [M] |
| Convergence | 533–863 iterations against a 4000 cap [M] |
| **Magnitude, held-out** | fitted on 3 plants, scored on **3 never used**: **RMS 0.126 K on a 0.923 K signal = 14 %** [F] |
| **Calibrated constants** | downwash exponent **1.25**, uc **8.0 m/s**, exchange_s **47.4 s** — fitted to field data, not to literature |
| Direction ratio | solver **2.17×** vs measured **1.60×** — over-predicts by ~35 %, expected sign (our deck is a bare rectangle; real sites have surroundings that smear it) |
| ⚠ **Shape, held-out** | correlation **+0.082 — essentially zero.** The measured wind-speed dependence spans only 0.20 K around a 0.92 K mean, so **there is almost no shape to fit** |

> **State it exactly like this: the magnitude is validated; the wind-speed shape is not resolvable
> from the available data. Wind speed moves the answer ~±10 %, direction ~±23 %.**

## 2.3 Eleven API defects to code around [M]

Full evidence, reproduction payloads and severity in
[fortyguard-api-findings.md](fortyguard-api-findings.md). Engineering consequences:

- **Assert non-empty on every response.** Unavailable windows return `status: completed` with zero
  tiles — 10 of 10 attempts. Indistinguishable from a legitimately empty area
- **Never use `analytic_type: time_of_measure`.** It returns physically impossible peak hours
  (midnight in Virginia in July) and is contradicted by `tcm` by **+6.446 °C**
- **Never use `heat_index_celsius`.** It is computed from the caller's own `temperature` input —
  input 40 °C yields a heat index of **86.7 °C**
- **`cloud_cover_octas` is a percentage** (values 38–92 observed; octas are 0–8)
- **Never send `start_time == end_time`** → HTTP 500, 3 of 3
- **`locations[].temperature` echoes your own input.** `env_params` returns no dry-bulb temperature
- **Historical floor is between 2021 and 2023**, undocumented; 2021 returns empty-success, 2019 times
  out
- Heatmap responses carry **no metadata block** — staleness can only be judged by fetch age

**Two candidate defects were WITHDRAWN after retest** (`persistence` works correctly; the
heatmap/`env_params` discrepancy was our own measurement error). Both are documented, because a
defect list with visible withdrawals is more credible than one without.

---

# PART 3 — Architecture

## 3.1 The stack

**⚠ UPDATED 2026-08-16.** The **Decide** row changed completely; see Part 0 §0.2–0.3.

| Layer | Component | Status |
|---|---|---|
| **Perceive** | FortyGuard `heatmap` — 60 m field + forecast over the cluster | ✅ [M] |
| | FortyGuard `env_params` — 15 params + `elevation` + clear-sky GHI/DNI/DHI at anchor points | ✅ [M] |
| | FortyGuard `satellite` — land-cover fractions (surface roughness / heat-flux input) | 🟡 probed 2026-08-16, blocked by a georeferencing gap — Part 11 |
| | Public wind (ASOS/METAR now, NWS/HRRR for forecast) — **FortyGuard serves no wind**, confirmed from their OpenAPI spec | free |
| **Physics** | 2-D advection–diffusion solver, calibrated to field data, batched on NVIDIA Warp | ✅ [M][F] |
| **Quantify** | 100-member ensemble → distribution, not a point | ✅ [M] |
| **Bound** | One-sided conformal bound, calibrated on measured residuals | ✅ **89.9–90.0 % held-out** [M] |
| **Decide** | ~~Online stopping rule — *when* to stage~~ **DEAD (Part 0 §0.2).** Now: **margin sizing** — hold the smallest defensible margin, widen it when the geometry is ambiguous | ✅ **+2.55 σ at the 40° crossover**, requirement attached [M] |
| **Explain** | Nemotron, local — turn the decision into a justification an operator or auditor can read | planned |
| **Gate** | Human approves before anything **physically actuates**. The decision loop itself runs unattended | by design |
| **Self-score** | Re-query the realised conditions → residual → update the bound | ✅ live, **96.8 %**, `NOT YET DECIDABLE` (1 of 3 test days) [M] |

## 3.2 The loop

```
ONCE PER CYCLE, per facility:

  PERCEIVE   1 heatmap call   -> 60 m temperature field + forecast over the cluster
             k env_params      -> wet-bulb / solar / AQI at anchor points
             METAR             -> wind speed and direction
             state             -> which sites are still un-staged, and how much horizon is left

  SOLVE      100-member ensemble on the GPU. Perturb wind direction (+/-15 deg), speed (+/-1 m/s)
             and load (65-100 %). Each member is a full physics solve of the site.
             -> a DISTRIBUTION of intake temperature, not a number

  BOUND      one-sided conformal upper bound from measured forecast-vs-outcome residuals
             -> "it will not exceed X, and that holds 90 % of the time"

  DECIDE     [SUPERSEDED 2026-08-16 -- kept as the record of what we built and why it died]
             an online stopping rule: STAGE reserve cooling now, or WAIT for a sharper
             forecast. Solved by backward induction over the horizon.
             -> CLOSED BY MEASUREMENT. See Part 0 section 0.2. Four implementations, best
                -19.37 sigma, then closed on PHYSICS for every cost model: the remedy is
                0.25 C against a 0.56-2.78 C gap to the ASHRAE limit.

  ACT        issues the posture and the HOUR, with the reason
  GATE       a human approves anything consequential. The agent never actuates
  LOG+SCORE  next cycle, compare against what happened -> residual -> update the bound
```

### 3.2b The loop as it now stands (Version 4)

```
ONCE PER CYCLE, per facility:

  PERCEIVE   1 heatmap call    -> 60 m temperature field + forecast over the cluster
             k env_params      -> wet-bulb / humidity / solar / AQI at anchor points
             public wind       -> direction + speed, and the FORECAST direction error
             state             -> calibration history: what coverage has actually been

  SOLVE      100-member ensemble on the GPU. Perturb wind direction by the MEASURED error
             (47-72 deg, not the old +/-15 deg -- that defect was found by N-40), speed,
             and load. Each member is a full physics solve.
             -> a DISTRIBUTION of intake temperature

  BOUND      one-sided split-conformal upper bound from measured forecast-vs-outcome
             residuals -> "it will not exceed X, and that holds 90 % of the time"

  DECIDE     the agentic core: MARGIN SIZING.
             Hold the smallest margin this ensemble and this measured track record can
             defend. On an ambiguous bearing the ensemble disagrees with itself and the
             margin widens by itself; on a safe bearing it collapses toward zero.
             -> 0.0656 C at good forecast quality vs 0.2128 C at poor. Nobody wrote
                either number: they come out of 4,320 GPU solves plus measured residuals.
             -> GUARD: if the wind-direction forecast error exceeds ~40 deg sd, the agent
                must report that a constant margin is as good, and say so. It does not
                get to claim a saving it cannot earn. (Part 0 section 0.3)

  ACT        issues the margin and the reason, into a BMS/SCADA-shaped interface
  GATE       a human approves anything that PHYSICALLY actuates. The decision loop
             itself runs with no human in it -- which is the autonomy claim
  LOG+SCORE  compare against what happened -> residual -> recalibrate the bound.
             If measured coverage falls below the 90 % promise, the agent WIDENS itself.
```

## 3.3 Why this is genuinely an agent — and the honest limits

> ### 🔴 RETRACTED 2026-08-16 — the "+0.356, 11.2 σ" headline below, and the row claiming a sequential core.
>
> The 11.2 σ figure was computed with the sharpening exponent **held fixed at 0.500**
> (`test_n24_breakeven.py` line 211). **N-25 later measured that exponent and its 95 % CI
> [−0.316, +0.195] EXCLUDES 0.500.** So the headline rested on an assumption the data rules out. It
> is left visible below because citing a retracted number is worse than not knowing it, and because
> the retraction is part of the record.
>
> **The replacement claim, and the current agency audit, is Part 0 §0.5.** The table immediately below
> is superseded by it. Grade against a real ladder (Russell & Norvig, *AIMA* ch. 2) rather than a
> home-made five-point list, and apply the *point-at-the-constant* test to every row.

**⚠ SUPERSEDED — Version 3's self-assessment, kept for the record:**

| Property | Status |
|---|---|
| **Perceives** its environment | ✅ FortyGuard + `env_params` + METAR, every cycle |
| Holds a **belief**, not a number | ✅ ensemble distribution; conformal bound is a *calibrated* belief |
| Chooses **when** to act, sequentially | 🔴 **RETRACTED — closed by measurement, Part 0 §0.2** |
| **Acts** with consequences | 🟡 recommends; a human approves. *"Decision support with a human gate"* |
| **Scores itself** and adapts | ✅ measures its own coverage and adjusts — now **96.8 % live, 1 of 3 test days** |

**The decision, and why no threshold can express it.** Reserve cooling needs ~3 h of notice, costs
money every hour it runs, and you do not know which hour will be hottest. So waiting is *cheaper and
better-informed* but *progressively less likely to work at all*.

Measured [M]: the rule beats the **best tuned fixed-hour rule** — both the hour and the sensitivity
margin optimised by exhaustive search, tuned on training days and scored on **held-out** days — by
**+0.356 ± 0.032 cost units/day, 11.2 σ**, with **zero tuned parameters** of its own. It fires off its
modal hour on **41.3 %** of staging days. 18 of 21 stub variations are significant wins.
**🔴 All three sentences above are retracted — see the banner.**

**The illustration that settles it:** on the test day the policy says **wait at hours 0–1, act at
hours 2–6, then wait again** — because past hour 6 the capacity can no longer arrive before the peak.
**No threshold, however tuned, can produce an action set that switches on and then off in time.**

### ⚠ Three honest limits — say these before they are found

1. **It is ONE decision.** We tested fleet compute allocation as a second one and it **failed**:
   equal split wins, all four concentration strategies lost, random beat ours (−2.0 σ). **Dropped.**
   Equal split is optimal and is implemented as a one-line rule.
2. **Two parameters carry it.** `peak_sd_h` is measured at **1.49 h** — but **one day of five drives
   that**, and the rule ties if it were 0.5 h. **The forecast-sharpening rate is UNMEASURED**, and the
   rule *loses* (−0.204) if forecasts never sharpen. 48 retry attempts across 4 lead times recovered
   nothing on 2026-08-11.
3. **No LLM in the decision path.** Track 6 says "Agentic AI" and some judges expect a language model
   calling tools. Ours reasons by solving equations — legitimately agentic by the textbook definition,
   and *more* trustworthy for a safety decision. **Say this out loud rather than letting it be
   inferred.** The language model's place here is **explaining** the decision, not making it.

   **⚠ UPDATED 2026-08-16, from the hackathon page's actual text.** Track 06 reads, verbatim:
   *"Create autonomous AI agents that use FortyGuard APIs to **analyze, decide, and automate**
   heat-related workflows **without human intervention**. Push the frontier of AI-native
   applications."* Its listed technologies are *"Temperature API, AI Agents, **LLMs**, Workflow
   Automation"* and its own build examples are modest — *"Heat Response Agent, API Orchestration Bot,
   Alert Automation Engine."*

   **Two consequences.** First, **Track 06 never asked for a sequential decision** — that bar was ours,
   not theirs, and Part 4's line *"Track 6 is off the table"* without a stopping rule was an assumption
   the track text contradicts. Second, **LLMs are explicitly expected**, so the honest position is not
   to avoid one but to place it precisely: **Nemotron, running locally, holds the six FortyGuard
   endpoints as tools, composes the multi-step workflow, and writes the operator justification and
   audit log — and never sets the margin.** State on the slide that the LLM never touches the safety
   bound. One judge, **Ahmed Abdelkhalek**, leads Digital Natives/Startups for **Google Cloud** and works
   on *"Agentic AI workflows"*, with a stated view that machine intelligence should be applied *"only
   where it genuinely solves the problem, balanced against cost"* — that framing is exactly what he will
   test. The other named judge, **Prof. Jonathan Reichental**, is a former CIO of O'Reilly Media **and of
   the City of Palo Alto**, speaking on *"Physical AI"*; he will ask what happens when the agent is
   wrong and who is accountable, which is what the conformal bound and the live critic answer.

   **Also resolve the tension in "without human intervention" out loud:** the decision loop —
   perceive, solve, bound, size the margin, self-score, recalibrate — runs with **no human in it**. The
   gate sits *only* on physical actuation, which is what every real SCADA deployment does. FortyGuard's
   own data-centre page supplies the vocabulary: their API *"integrates with building management and
   SCADA systems."*

## 3.4 The behaviour that is worth more than any of the numbers

**The margin widens by itself when the forecast is geometrically ambiguous.** Sweeping forecast
direction in 5° steps with a 60-member ensemble [M]:

| wind from | mean | sd | **p90 (the acting bound)** | members hot |
|---|---|---|---|---|
| 180° | 0.0000 | 0.0002 | **0.0000** | 0 % |
| 225° | 0.0194 | 0.0437 | 0.0470 | 2 % |
| 250° | 0.1662 | 0.1327 | 0.3686 | 37 % |
| **265°** | 0.2643 | 0.1149 | **0.3962** | 72 % ← peak level |
| **285°** | 0.1627 | **0.1379** | 0.3759 | 37 % ← **widest spread** |
| 315° | 0.0231 | 0.0557 | 0.0492 | 5 % |

```
spread at the geometric edge   0.2556 C   (widest at 285 deg)
spread in the safe sectors     0.0095 C        ->  27.0 x wider at the edge
                                                  (was 13.6 x before the 2026-08-12 heat-sink fix
                                                   -- this finding got STRONGER, see 7.3)
```

> **The agent is never told where the plume points.** It discovers the edge by pushing today's
> forecast through the physics 60 times and noticing that its own answers disagree with each other.
> **The same code relaxes on safe days and refuses at the edge. There is no rule anywhere about
> plumes.**

---

# PART 4 — What each component earns

| Component | What breaks without it |
|---|---|
| **FortyGuard heatmap** | No boundary condition. You are back to an airport reading miles away, which published work says deviates enough to change design and operation decisions |
| **FortyGuard forecast** | No anticipation. You can only react, and cooling plant has 3 h of inertia |
| **FortyGuard history** | No calibrated bound. The residuals that make the 90 % promise honest come from forecast-vs-outcome pairs |
| **The physics solver** | You have neighbourhood air, not intake air. Two well-powered null results [M] proved FortyGuard's field carries **no** facility-scale thermal signature (difference-in-differences **+0.016 °C** against a published 0.7–0.9 °C; rotation placebo **p = 0.42**). The facility physics **must** come from us |
| **NVIDIA GPU** | 21 minutes per cycle over 20 sites — outside an hourly loop. And sensitivity sweeps become unaffordable, so assumptions go unswept |
| **Conformal bound** | You have a number, not a promise. The margin cannot shrink, so the customer gets nothing |
| ~~**Stopping rule**~~ | ~~You have a dashboard with an if-statement. Track 6 is off the table~~ **🔴 BOTH HALVES WRONG, 2026-08-16.** The stopping rule is dead (Part 0 §0.2), and Track 06's actual text never required one (§3.3 limit 3). **Replaced by margin sizing**, whose absence *would* leave you with a constant margin — measured as no worse than the agent's whenever wind-direction error exceeds ~40° sd, and **0.05–0.15 °C worse below it** |
| **Self-scoring** | No track record. See the airport story — the whole product collapses |
| **Public wind forecast** | The margin cannot beat a constant. This is the one load-bearing input **FortyGuard does not supply** — say so plainly rather than letting a judge find it (Part 11) |

---

# PART 5 — NVIDIA components

| Component | Role | Status |
|---|---|---|
| **Warp** | The advection–diffusion timestep as a GPU kernel, batched over the ensemble on a third array axis. One launch per timestep for all members, **no host transfer inside the loop** | ✅ **72.7×** (93.5× on a repeat run — quote the lower), verified to **0.000251 °C** max field difference vs CPU [M] |
| **Nemotron**, local | Turn a staging decision plus its bound into a justification an operator or an auditor would accept. Runs locally because evidence for a compliance file must not depend on a cloud API | planned |
| **RAPIDS** | **CUT** — no bottleneck it addresses. Including it would be logo-driven |

**Graceful degradation:** if Warp is unavailable the identical NumPy kernel runs on CPU with a
reduced ensemble. The demo path never requires the GPU to be present, but the *timing claim* does.

---

# PART 6 — Rubric fit

> ## ⚠ UPDATED 2026-08-16 — the rubric is now CONFIRMED from the hackathon page, and the old score below is stale.
>
> **The weights are real.** FAQ 5 on fortyguard.com/hackathon26, verbatim: *"How are projects judged? |
> **Impact & Relevance (40 %), Technical Execution (35 %), Innovation (15 %), Communication (10 %)**."*
> Version 3 guessed these correctly.
>
> **But there is a SECOND, differently worded criteria list on the same page** (in the submission panel),
> unweighted: **Innovation** · **Technical Quality** — *"implementation and use of FortyGuard API"* ·
> **Business Viability** — *"real-world applicability and market potential"* · **Presentation** —
> *"clarity of pitch and documentation quality"*. **"Business Viability" appears nowhere in the weighted
> list.** Treat it as real: two of the three named judges are commercial people, not researchers.
>
> **Hard submission requirements, verbatim:** *"Submit three things: a public GitHub repo, a live
> website/demo link, and add `fortyguard` as a collaborator on your repo."* Plus a **2–5 minute video**
> and *"Documentation of FortyGuard API usage."* Deadline **30 Aug 23:59 GST = 00:59 PKT on 31 Aug**.
> Judging Sept 1–15, winners Sept 16.
>
> **Prizes:** $6,000 ($3,000 / $2,000 / $1,000; 1st adds an internship pathway + partner promotion),
> **plus an NVIDIA Jetson AI Developer Kit to each winning team** — spec'd on the page at **67 TOPS,
> 1,024 CUDA cores + 32 Tensor cores, 6-core ARM Cortex-A78AE, 8 GB LPDDR5.** That matters for the
> NVIDIA story: **the Warp kernel achieves 93.46× on a 6 GB RTX 4050, and 8 GB ≥ 6 GB**, so "designed to
> run at the facility, on the edge" is credible — and it is precisely Reichental's *"Physical AI"* frame.
> **Say "designed for and sized to fit", not "verified on" — we have no Jetson.**
>
> ### Honest re-score, 2026-08-16
>
> | Criterion | Weight | V3 claimed | Now | Why it moved |
> |---|---|---|---|---|
> | Impact & Relevance | 40 % | 33–35 | **30–34** | The problem statement is still FortyGuard's own words, and their data-centre page independently uses *"air intakes"* and *"overcooling"* and lists *"Reduces overcooling inefficiencies"* as the value. **But the quantified benefit shrank**: the releasable margin is now **0.05–0.15 °C**, conditional on a wind forecast beating 40° sd, and **no dollar figure may be quoted** because the °C→kWh conversion is unsourced. |
> | Technical Execution | 35 % | 30–32 | **28–33** | Stronger on rigour than V3: five decision cores pre-registered and tested, four negative results published with receipts, a port verified against its predecessor, an ASOS quantisation artifact caught before it became a claim, and **four new API defects found**. **Weaker on delivery: nothing is assembled, hosted, or demonstrable as of 2026-08-16.** The upper end is only reachable if the loop, repo and demo ship. |
> | Innovation | 15 % | 12–13 | **12–13** | Unchanged. The combination is still verifiably empty in the surveyed market, and the *"σ measures dilution, AUC measures confidence"* result is a genuinely novel piece of analysis. |
> | Communication | 10 % | 9 | **4–9** | V3's 9 assumed the wind-dial demo existed. **It does not, and neither does the video or the hosted link.** 4 if nothing ships; 9 if they do. |
> | | | **≈84–89** | **≈74–89** | **The entire spread is delivery, not research.** |
>
> **The single highest-value remaining item is unchanged from V3 and still unbuilt: the wind-dial demo
> (Part 9).** It is now *more* valuable, because margin sizing is exactly what it visualises.

**⚠ SUPERSEDED — Version 3's scoring, kept for the record:**

| Criterion | Weight | Score | Reasoning |
|---|---|---|---|
| **Impact & relevance**<br>*"real urban-heat problem, measurable benefit, a real client would adopt"* | 40 % | **33–35** | The problem is FortyGuard's own words. Benefit is measured and banded: **0.22–0.94 °C** releasable, on 7 of 8 wind directions. The market **already pays** — Vigilent since 2014, Phaidra at Merck, etalytics at Equinix — which proves adoption without us arguing for it |
| **Technical execution**<br>*"works, sound, data handled well; deployable, client-grade"* | 35 % | **30–32** | 11 API defects found and coded around, 2 withdrawn after retest. Physics **calibrated to 40,000 field measurements with held-out validation**. GPU port verified before timed. Every stub swept and banded. Four claims retracted with receipts |
| **Innovation**<br>*"original approach **or a fresh combination of ideas**"* | 15 % | **12–13** | 60 m urban field + site-scale physics + calibrated bound + sequential decision. **A survey of twelve commercial products found none that ingests a weather forecast** — the combination is verifiably empty |
| **Communication**<br>*"clear, compelling demo and write-up"* | 10 % | **9** | The airport analogy, *"the sensor is our examiner"*, and the **wind-dial demo** (Part 9). Fixture replay means the demo cannot fail live |
| | | **≈84–89** | |

**Commercial reframe — the sentence for FortyGuard's CEO:**

> **"We are not competing with Phaidra or Vigilent. We are the input they do not have."**

Twelve products surveyed for "weather", "forecast", "outdoor", "ambient", "wet bulb": **zero explicit
claims.** Every disclosed input is internal — rack sensors, CRAC/CRAH telemetry, chiller loop data, IT
load. Phaidra's leading indicator is explicitly **rack power draw**. And DeepMind's own BCOOLER trial
alternated policies daily to *"get to see reasonably consistent weather"* — **they treated weather as
a confounder to cancel out, not a signal to exploit.**

That makes FortyGuard a **supplier to a market that already pays**, not a competitor in it — which is
exactly FortyGuard's business model.

**Prior art to cite before being caught by it:** EPFL's DAD-DPC at Polydome (arXiv 2412.09238) is the
closest work — real occupied building, ~2-month closed loop, split conformal prediction, hyperlocal
forecasts, 20.5 % savings. It is a **lecture hall, not a data centre**, its conformal bound lumps
model and weather error together rather than bounding the forecast, and it is a university trial.

---

# PART 7 — Honest stubs, limits and open risks

## 7.1 Stubs [S] — and the sensitivity of the headline to each

Sweeping all eight on the calibrated solver: headline **+0.839 °C**, full band **0.415–1.713 °C**
(ratio 4.1×). ⚠ **These roughly doubled on 2026-08-12** after the heat-sink fix (§7.3) — the earlier
+0.455 / 0.219–0.940 was biased LOW because building interiors were averaged into the intake.

| Stub | span | Note |
|---|---|---|
| `bank_w` condenser bank width | **0.721 °C** | Largest — but a **geometry fact you would measure for any real client**. Not really unknown in deployment |
| `exchange_s` | 0.672 °C | Calibrated to field data. The genuine remaining weakness |
| `uc` | 0.314 °C | Calibrated to field data |
| `discharge_k` | 0.253 °C | Within the published 14–25 °F range |
| `separation_m`, `intake_r` | ~0.14 °C | Site geometry |
| `design_wind` | 0.037 °C | Weak |
| `diffusivity` | **0.088 °C** | **The one constant with no physical basis at all is the LEAST influential.** Reassuring |

**Quote the headline as a band, never a point:** *"of order half a degree, 0.22–0.94 °C across the
plausible range of every unmeasured constant — and the conclusion, that it is dead weight on 7 of 8
directions, holds throughout, because it depends on the direction contrast rather than the level."*

## 7.2 Open risks — sorted by whether a test can close them

**The distinction matters more than the list.** Three of these are *unmeasured quantities*, which a
test closes. Three are *permanent limits of the available evidence*, which no test closes — they get
stated, with the reason they are survivable. Presenting a permanent limit as an unfinished to-do makes
it look like you ran out of time. Presenting it as a known boundary of your evidence makes it look
like you understand what you built.

### 🟢 Closed since the last revision

| Was | Now |
|---|---|
| **N-8 v3 and N-20 rest on falsified physics** | **Both rerun on the calibrated solver.** N-8 v4: baseline **+0.4369 °C**, 7 of 8 directions release ~100 % of it — and it lands beside N-19's independent **+0.455 °C**. N-20 fails **again**, harder: **−2.7σ** (was −2.0σ). The null result now rests on validated physics, so it is quotable as a finding rather than an unfinished job |
| **`solve()` and `downwash_fraction()` disagreed on the downwash exponent** | Found while doing the rerun. N-22 recalibrated the free function to 1.25 and left `solve()` at the falsified 2.0, so the CPU and GPU paths of **N-16 itself** were using source terms differing by up to **1.84×** (at 3 m/s). Both now read `CALIBRATED`, and N-16 passes the exponent explicitly to each side. Re-verified: **0.000251 °C** [M] |
| **Two risks stated as adjectives** | **N-24** turns both into pre-registered thresholds — see below |
| **"Heatmap forecast intermittency"** | **Dissolved 2026-08-12 — it was our bug.** The endpoint reads `start_time` in the **AOI's local zone**; our scripts built windows from a UTC+5 machine clock for a UTC−4 site, a silent **9-hour** error on every forecast request. N-18's four "leads" of 4/6/8/10 h were really **13/15/17/19 h — all outside the horizon**, so 48 retries could never have succeeded. Fixed in `common.site_window()`, which raises on a naive datetime |
| **12-hour horizon unverified** | **Now CONFIRMED positively.** 9.25 h and 11.25 h leads return data; 13.25 h and 17.25 h return zero tiles — a clean 12 h cut. Independently, a **9.41 h lead returned a full 17,862-tile field** on 2026-08-12. `horizon_h = 12` is measured, not assumed |

### 🔴 CLOSED — N-25, the sharpening measurement. It FAILED, and it took the 11.2 σ headline with it.

> **Result: `b = −0.0608, SE 0.0803, t = −0.76, 95 % CI [−0.316, +0.195]`.** FAIL against the 0.129
> pre-registered break-even. **But read the CI honestly in both directions:** it contains 0, 0.129
> *and* 0.187, so it is underpowered and does **not** prove sharpening is absent — while it **does**
> exclude **0.500**, the value the 11.2 σ headline was computed with. That is why §3.3 is retracted.
>
> **And it measured the wrong quantity anyway.** It fitted `b` on the **spatial** sd across ~17,862
> tiles on one day; the decision needs the **day-to-day** sd of the **site-level** error — different
> quantities, roughly 9× apart. The corrected estimator (N-42) was built and validated against
> synthetic data, then a power analysis showed **80–160 days** are required. Unresolvable on this
> calendar. **See Part 0 §0.1–0.2.**
>
> **The premise did eventually get support — from a different variable.** Ambient sharpens at
> **`b = +0.3414, SE 0.0443, CI [+0.2427, +0.4402]`** (Part 0 §0.2), and it propagates additively where
> the recirculation term did not. The design below is left in place because the instrument-validation
> discipline in it is the part worth repeating.

**⚠ SUPERSEDED — the plan as written on 2026-08-12:**

**It was never necessary to wait for Aug 18.** The timezone fix made the forecast path usable, and
because the AOI is nine hours behind this machine, the site's whole day is forecastable from here in
the morning. N-25 is running now:

| | |
|---|---|
| **Design** | ONE target window — **14:00–16:00 site-local**, the diurnal peak the agent actually decides on — forecast at five leads (**9.4 → 1.5 h**), then the outcome. Same window every time, so **the time-of-day confound N-13 had is gone by construction** |
| **Sample** | 8×8 km at 60 m = **17,862 tiles per call.** Pricing is flat in area, so N-13's 2 km polygon was 45× less data for the same 4,220 credits |
| **Fitted quantity** | `b` in σ(lead) ∝ lead^b — *exactly* the parameter N-9 and N-24 sweep |
| **Pre-registered** | **b ≥ 0.187** → 2σ win · 0.129–0.187 → marginal, re-run N-9 at the measured b · **< 0.129** → waiting buys nothing, report the null |
| **Instrument validated first** | Fed synthetic data built at known exponents, it recovered **0.498 from 0.500**, **0.185 from 0.187**, **−0.002 from 0.000**, and independently reproduced ρ = 0.774 at b = 0.187 against N-24's 0.772 |
| **Honesty** | 17,862 tiles are spatially correlated, so `b` is also fitted per spatial quadrant and **that spread is the reported uncertainty, not the tile count**. And this is one window on one day |
| **Status** | Shot 1 done: **17,862 tiles at 9.41 h lead.** Verdict tonight |

### 🟡 The other gated quantity — N-24 thresholds

| Quantity | Must clear | Measured | Status |
|---|---|---|---|
| **Peak-hour uncertainty** `peak_sd_h` | **> 0.70 h** for a 2σ win (breaks even at 0.395 h) | **1.49 h** → **+11.2σ** | ✅ clears comfortably, but on 5 days |
| **The σ anchor's lead label** | — | — | ⚠️ **`fb_1_FCST_12H` is labelled "12 h" and that label is NOT verifiable.** Built on the same UTC+5 clock, its true lead is somewhere in **9.1–21.1 h** across a 12-hour-wide window. The forecast↔history *pairing* is valid, so bias +0.3489 °C and sd 0.1504 °C are real residuals — only the lead is unknown. **N-25 replaces it with five known leads** |

**ρ in one sentence:** *how much sharper is the forecast three hours before the hour that matters than
it was twelve hours before it?* One number, measurable in two calls plus a wait. ρ = 1.00 means the
forecast never improves; ρ = 0.50 is the random-walk value that most real weather forecasts beat.

**The finding that matters more than either threshold.** N-24's joint grid asked whether the two risks
can substitute for each other — if the peak hour were wildly uncertain, could the rule earn its keep
*without* any sharpening? **No.** At ρ = 1.00 the rule loses at every peak-hour uncertainty tested,
including 4 h:

| ρ ↓ / `peak_sd_h` → | 0.25 h | 0.75 h | **1.49 h** | 2.50 h | 4.00 h |
|---|---|---|---|---|---|
| **1.00** no sharpening | −20.6σ | −10.8σ | **−5.3σ** | −1.9σ | −7.0σ |
| 0.81 | −12.0σ | −4.7σ | **+1.1σ** | +2.7σ | −1.9σ |
| 0.66 | −7.9σ | −0.8σ | **+4.9σ** | +6.8σ | +2.0σ |
| **0.50** random walk | −4.7σ | +4.5σ | **+11.9σ** | +10.9σ | +6.0σ |
| 0.35 | −3.9σ | +6.1σ | **+12.2σ** | +12.6σ | +8.8σ |

So **the sharpening measurement on Aug 18 decides whether this decision is agentic at all.** Say that
out loud before a judge finds it. Two further honest readings of the same grid: the benefit **saturates**
past ρ ≈ 0.47 — more sharpening stops helping — and **too much** peak-hour uncertainty hurts (the gain
peaks near 2.1 h and the 4 h column is worse than the 2.5 h column), because a peak hour that could be
anywhere in the horizon leaves no structure to exploit.

### 🔴 Permanent limits — no test closes these, so say them first

| Limit | Why no test fixes it | What you say |
|---|---|---|
| **No data-centre measurements exist anywhere** | All published recirculation field data is from power stations. There is no data-centre dataset to find | *"The mechanism and the order of magnitude transfer. No site-specific number does, and I am not claiming one."* |
| **Direction claim rests on one site** | Figure 6-90 is the **only** recirculation-vs-direction scatter in the report; the other 50 direction figures are time series. More testing cannot create a second dataset | Cite the report's own text, the physics reason, and Google's input #19. Keep the claim **🟡, never ✅** |
| **Wind-speed shape not validated** | The field data's speed dependence spans only **0.20 K** — below the resolution needed to fit a shape. Held-out correlation **+0.082** | Claim **magnitude only**. Never claim a peak location. This is precisely the error N-11 made |
| **Out-of-horizon requests fail silently** | `status: completed` with zero tiles is indistinguishable from an empty area. That much is genuinely FortyGuard's, and you decided not to build a fallback | Assert non-empty; **compute the lead through `common.site_window()` before every call** so you never ask outside the horizon by accident. Reported in the handover document |

---

# PART 8 — Schedule

## Prep, Aug 10–17 — zero credits

- ✅ Warp port, correctness then speed (**72.7×**)
- ✅ Field-data validation and recalibration (**N-21, N-22**)
- ✅ Knife-edge behaviour (**N-23**)
- ✅ API defect report, handover-ready
- ✅ Claims-and-defences brief
- ✅ **Recomputed N-8 (v4) and N-20 on the calibrated solver** — N-20 fails
  again at −2.7σ. Both quotable now
- ✅ **Fixed the downwash-exponent split between `solve()` and `downwash_fraction()`** and re-verified
  N-16 (0.000251 °C)
- ✅ **N-24 breakevens** — both open risks now have pre-registered thresholds
- ☐ Build the **wind-dial demo** (Part 9) — highest-value remaining item
- ☐ Multi-day self-scoring (coverage is currently measured on one day-pair)
- ☐ Nemotron justification layer

### Prep actually completed Aug 12–17 (added 2026-08-16)

- ✅ **N-25 → N-46b: five decision cores pre-registered, built and tested.** Four negative, one positive
  with a requirement. Full record in Part 0.
- ✅ **Multi-day self-scoring is RUNNING**, not pending: `test_n26_coverage.py` on a daily Windows
  scheduled task (`FG-N26-Coverage`, 13:30 PKT). **2 complete day-pairs, 1 test day, 96.8 % coverage,
  verdict `NOT YET DECIDABLE`** (needs 3 test days = 4 pairs). Aug 14 is a permanent gap — the machine
  slept and a forecast cannot be made retroactively. `WakeToRun` was enabled, then **reverted to
  `False` at the user's request** on 2026-08-16; the machine must be awake roughly 11:30–17:00 PKT for
  the forecast leg to land inside the 6.0–11.5 h comparability band.
- ✅ **Real weather history fetched, free, no key:** 534 summer days of KIAD ambient and 449 days of
  wind direction (2021–2026), cached as fixtures.
- ✅ **The full FortyGuard API surface mapped from their OpenAPI spec**, and two unused endpoints probed
  with two paid calls. **Four new defects found.** Part 11.
- ✅ **The hackathon rubric, submission requirements, judges and prizes read off the live page** and
  reconciled against Part 6.
- ☐ **Still not done, and these are the submission blockers:** the assembled loop, a public GitHub repo
  with `fortyguard` as collaborator, a hosted demo link, the 2–5 minute video.

## Build, Aug 18–30 — live key

> **⚠ REWRITTEN 2026-08-16.** The original day-one order below is obsolete: item 2 (measure ρ, the
> forecast-sharpening rate) was the *"single load-bearing unknown"* under Version 3's stopping rule, and
> **that rule is dead**, so ρ no longer gates anything. Item 4 (extend `peak_sd_h`) served the same dead
> rule — it was extended to 15 days anyway (**1.4475 h, leave-one-out floor 1.1579 h**) and is now
> simply a spare measurement.
>
> **The revised order, and the reasoning is delivery risk rather than research risk:**
> 1. **Public GitHub repo + `fortyguard` as collaborator.** A hard requirement sitting at zero. Minutes
>    of work. **`.env` must never be committed.**
> 2. **Assemble the loop end to end** — the organs exist as ~30 separate test files and nothing runs as
>    one program. This is the largest single gap and it is what "agent" means to a judge.
> 3. **The hosted demo link** — the wind-dial (Part 9), which now visualises margin sizing directly.
> 4. **Measure whether a real wind-direction forecast beats 40° sd** (NWS/HRRR, free). This is the one
>    remaining measurement that the surviving claim depends on. If it fails, the honest pitch becomes
>    the instrument and the verifiable bound, without the saving.
> 5. **Nemotron orchestrator/explainer**, local. **Measure the Warp ensemble's peak VRAM first** — 6 GB
>    total, and the 100-member ensemble already lives there. Sequence solve → free → generate rather
>    than quietly shrinking the ensemble.
> 6. **The 2–5 minute video**, after Karol Wiszowaty's pitch clinic on Aug 26.
>
> **Do NOT spend credits on:** N-42's extra forecast leads (~8,440/day, cannot resolve in time), or the
> cancelled 65-configuration cost sweep.

**⚠ SUPERSEDED — the original day-one order:**

**Day one, in this order:**
1. **Measure the price on call #1** — the audited key's meter is frozen, so the live price is unknown
2. **Forecast-sharpening leg 1 — measure ρ.** The only test with an unavoidable waiting period, and
   N-24 proved it is the *single* load-bearing unknown, so it goes first among the physics tests.
   **Pre-registered target: ρ ≤ 0.772.** Procedure: for a fixed target hour, request a forecast at
   ~12 h lead and again at ~3 h lead; after the hour elapses, request the realised value; ρ is the
   ratio of the two error spreads. `env_params` point forecasts are the fallback route and were
   working when the heatmap forecast path was not. **If ρ > 0.837 the stopping rule earns nothing and
   we report the null** — that decision is made now, not on the day
3. `env_params` line-item check — it has **no entry in the billing breakdown**, so it may be unmetered.
   If free, lean on it heavily
4. Extend `peak_sd_h` to ~20 days. **Must stay above 0.70 h**; currently 1.49 h from 5 days
5. `env_params` spatial variation at 60–500 m

Then: cluster-scale run, self-scoring over consecutive days, demo polish, write-up.

---

# PART 9 — The demo

## 9.1 The centrepiece: sweep the wind dial, watch the margin breathe

**On screen:** a compass dial for wind direction. Beside it, one bar showing the reserve cooling the
plant must carry, with a band around it showing how *sure* the system is.

**Turn the dial slowly and narrate:**

```
  0 deg -> 220 deg    bar flat on the floor, band tight
                      "Sixty percent of the compass. Nothing to carry. Relax."

     240 deg          bar rising, band fattening
                      "Approaching the edge."

     265 deg          bar tallest        p90 = 0.714 C
                      "Worst case. Hold everything."

     285 deg          band FATTEST       sd = 0.2556 C, 27.0 x the safe sector
                      "Here the system is telling you it cannot resolve which side
                       of the building's geometry we will be on today."

  320 deg -> 360 deg  bar collapses, band tightens
                      "Clear again."
```

**Why "breathe":** the uncertainty band visibly swells and shrinks as the dial turns. In and out.

**Why this beats any slide:**

1. **It is live** — the actual system responding, not a chart someone drew
2. **It shows judgement, not output.** Anyone can print a number. This shows the system **knowing
   when it does not know** — the hard part, and the trustworthy part
3. **Both halves of the pitch in one gesture.** *"Relax when safe"* is the flat stretch; *"hold when
   it matters"* is the tall fuzzy bump. The judge watches both instead of being argued at
4. **No jargon.** Nobody has to hear "conformal prediction" or "ensemble." You turn a dial
5. **It is honest.** The fat band is the system admitting uncertainty, on screen, unprompted — which
   reads as confidence in a way a smooth line never does

**The line to say while turning it:**

> *"Notice it is not the peak that widens — it is the edges. That is the system telling you the wind
> forecast cannot resolve which side of the building's geometry you will be on today. On those days we
> do not relax the margin, and we can tell you exactly why."*

**Fifteen seconds, and it contains the entire product.**

## 9.1b ⭐ Screen ZERO: FortyGuard's field, before the dial (added 2026-08-16)

**The wind dial cannot be the first thing a judge sees.** *"Technical Quality — implementation and use
of FortyGuard API"* is an explicitly scored criterion, and the dial shows **our** physics. If the field
only appears later as a supporting screen, a judge can watch the whole demo without ever seeing the
sponsor's data do work. **Fix the order: FortyGuard's data opens the demo.**

**On screen, in this order, before the dial is touched:**

```
  1. THE FIELD          17,862 tiles at 60 m over 8 x 8 km, from ONE call, in 67 s.
                        Show it as a heat surface with the facility cluster marked.
                        Say: "this is FortyGuard, not a model of ours."

  2. THE SCALE ARGUMENT Drop a pin at the site and a second pin where the nearest
                        airport station is. Show the temperature at both.
                        Say: "the difference between these two pins is about a degree.
                              Everything my agent computes is a few TENTHS of a degree.
                              Without this field I would be computing a correction on
                              top of an error ten times its size."

  3. THE SAME CALL,     Flip the analytic layer live: tcm (snapshot) -> exceedance ->
     FOUR WAYS          persistence, and name time_of_measure as the one we PROVED
                        broken and code around. Four layers of one endpoint.
                        Say: "we did not just call the API. We characterised it."

  4. FORECAST -> OUTCOME  The same request shape, run once as a prediction and once as
                        the realised outcome. Residual bias +0.349 C, sd 0.150, n=6,875.
                        Say: "this pairing is what lets me make a 90 % promise at all.
                              Nothing else I can buy does this at 60 metres."

  ---> ONLY NOW turn the wind dial (9.1). The dial is the agent's JUDGEMENT.
       Screen zero is the EVIDENCE the judgement is built on.
```

**Why this ordering wins rather than just being polite to the sponsor:** it converts the strongest
objection — *"60 m can't resolve an intake, so why FortyGuard?"* (§1.5b) — from a question a judge asks
you into a point **you make first, with their own data on screen.** And screen 4 is where the eleven
documented API defects stop looking like criticism and start looking like engagement: **we found what
their data can and cannot do, and built to it.**

## 9.2 The rest of the demo

| Screen | Content |
|---|---|
| ~~**Perceive**~~ | **Promoted to Screen Zero (§9.1b) — it now opens the demo rather than following the dial** |
| **Ensemble** | 100 members resolving on the GPU in **0.9 s**, with the CPU comparison alongside |
| **The bound** | Point estimate, then the calibrated margin, then the 90 % bound |
| **The decision** | The hour-by-hour table: **wait, wait, ACT, ACT… wait** — and the sentence *"no threshold can switch on and then off in time"* |
| **Self-score** | Coverage measured over consecutive days against the 90 % target |
| **Validation** | The field-data comparison: measured vs modelled, held-out plants |
| **Honesty slide** | The retraction log. Four claims withdrawn with receipts |

**Fixture replay:** every screen runs from saved responses with an injected clock. **No live API call
is required while judges are watching.**

## 9.3 What ships if things break

| If | Then |
|---|---|
| Live API unavailable | Fixture replay. Already the primary demo path |
| No GPU on the demo machine | Identical NumPy kernel, reduced ensemble. The timing claim becomes a recorded measurement rather than live |
| Forecast path empty | Assert non-empty, retry, and show the retry statistics — it is a documented API finding, not a project failure |
| Nemotron layer incomplete | The decision table stands alone. The language model explains; it does not decide |

---

# PART 11 — The real FortyGuard API surface (added 2026-08-16)

Read off their own OpenAPI spec (`hackathon/hackathon/openapi.json`), then two endpoints probed with
two paid calls. **This section exists because *"Technical Quality — implementation and use of
FortyGuard API"* is a judged criterion, and because we had been using two endpoints out of six without
knowing what the others did.**

## 11.1 All six data endpoints, and what each actually gives us

| Endpoint | What it returns | Us |
|---|---|---|
| `POST /v1/heatmap` | Temperature field over a polygon AOI. `granularity` **60/80/100**; `analytic_type` **`tcm` (snapshot), `time_of_measure`, `exceedance`, `persistence`**; `threshold` + `direction` (`above`/`below`) | ✅ **the boundary condition.** 17,862 tiles over 8×8 km at 60 m, one call, ~67 s |
| `POST /v1/env_params` | 15 parameters at a point + `elevation` + a separate `solar_irradiance` block (**clear-sky GHI/DNI/DHI**). Confirmed present: `heat_index_celsius`, `apparent_temperature_celsius`, `relative_humidity_percent`, `precipitation_mm`, `cloud_cover_octas`, `wet_bulb_temperature_celsius`, seven AQI indices, `methane_ppb`, `co2_ppm` | ✅ used. `cloud_cover_octas` + solar feed the stability class |
| `POST /v1/heat_intelligence` | lat/lon/`temperature`/`date` + an **`analysis`** list (`geographic` \| `environmental` \| `urban` \| `events` \| `anthropogenic`). **Returns a `download_link` to a 748 KB human-readable PDF** — *"Heat Intelligence Report"*, rendered by `wkhtmltopdf 0.12.6.1` with embedded JPEG charts | 🔴 **probed 2026-08-16 — NOT USABLE as an agent input.** An agent cannot consume a rendered report as a data feed. Took **217 s** to produce |
| `POST /v1/satellite` | Satellite **segmentation** at a point — see 11.2 | 🟡 probed, ruled out for geometry |
| `POST /v1/streetview` | Streetview **segmentation** at a point with view angles | 🟡 probed, did not complete |
| `GET /v1/status/{activity_id}` | Async poll for all of the above | ✅ used |

> ### 🔴 **FortyGuard supplies NO WIND.** Confirmed: the only `direction` field in the entire spec is
> `enum: ["above","below"]` on `/v1/heatmap`, the direction of a *threshold comparison*. There is no
> wind direction, speed or gust field anywhere. **Wind comes from public data (ASOS now, NWS/HRRR for
> forecast), and Part 0 §0.3 shows the surviving claim depends on it. Say this before a judge finds it.**

**But be equally precise that FortyGuard is still the primary data.** Intake temperature = ambient +
recirculation increment. Ambient is **17.8–37.2 °C** with forecast uncertainty **1.57–4.13 °C**; the
recirculation increment is **0–0.855 °C** with ensemble spread **0.0095–0.2556 °C**. **FortyGuard supplies
~97–99 % of the predicted value and dominates the uncertainty by 16–60×**, and the conformal bound —
the product's actual promise — is calibrated **entirely** on FortyGuard residuals. Wind sets the
*shape* of a small correction; FortyGuard sets the level and the error budget.

## 11.2 The satellite/streetview probe — 2 paid calls, 2026-08-16, user-authorised

**The question:** `solver.demo_site()` is a **hand-written** layout (building positions, exhaust and
intake locations). Could FortyGuard supply that geometry, so the agent derives its own site layout and
one more hand-specified input disappears?

**Answer: no.** `/v1/satellite` returned, at 39.0100/−77.4460, `granularity: 60`, `image_year: 2026`:

```
image_dimensions : 225 x 225 pixels
segments         : {"earth, ground": 99.78, "others": 0.22}
image_legend     : class -> RGB, e.g. [120,120,70]
```

Both images were decoded and inspected. **The photo is bare scrubland with dirt tracks and no buildings
at all**, so the classifier's 99.78 % is *correct*, not a failure. And `image_content` is the original
photo with the class colour **alpha-blended over it** — a visualisation, not a parseable label raster.

**It fails on four independent counts:** a *point* query rather than a polygon · a 225×225 raster with
no vector polygons · a two-class vocabulary with no building or roof class · a picture rather than data.
**`solver.demo_site()` stays hand-specified, and that is stated as a limitation rather than hidden.**

**The one honest, non-decorative use:** the `segments` percentages are real land-cover fractions, and
surface cover controls roughness and sensible heat flux, which feed the atmospheric stability class —
something N-33 currently derives from weather alone. **Blocked by defect 12.2 below.**

**`/v1/streetview` accepted the request** (`"Street View Segmentation Submitted Successfully"`, activity
`1cf837aa-a857-452a-a349-dd83a0b92186`) and was **still `Processing` 25 minutes later**, against 15
seconds for satellite. The `activity_id` is saved, so it can be polled later at no cost.

**Credits: `cycle_remaining` 180,980 before and after.** The meter has been frozen since the billing
cycle closed 2026-07-19, so **a zero difference does not prove the calls were free.** Both raw responses
are saved under `results/fixtures/` so this is never paid for twice.

## 11.3 Four NEW defects for the handover document (12–15)

Additions to the eleven in [fortyguard-api-findings.md](fortyguard-api-findings.md).

| # | Defect | Evidence |
|---|---|---|
| **12.1** | **`orignal_image` — misspelled duplicate key** in the satellite response, **byte-identical** to `original_image` (verified `True`), 50,272 chars each. Doubles the payload for zero benefit | `results/fixtures/probe_satellite.json` |
| **12.2** | **No georeferencing.** The response gives the query point and pixel dimensions but **no bounding box, ground extent, or metres-per-pixel**, so the mask cannot be placed on the ground. **This is the one that matters** — it is what blocks the legitimate land-cover use above | same |
| **12.3** | **Type inconsistency.** The request schema requires `latitude`/`longitude` as `number`; the response returns them as **strings** (`"39.01"`, `"-77.446"`) | same |
| **12.4** | **A task can sit in `Processing` indefinitely** with no error, timeout or ETA — streetview exceeded **25 minutes** while satellite completed in **15 seconds**. Operationally there is no way to distinguish slow from stuck | `probe_streetview_submit.json` |

**A further observation, not a defect but a documentation gap:** the FAQ states *"credits are only used
when a task succeeds"*, which sits awkwardly beside existing defect #2 — an out-of-horizon request
returns `status: completed` with **zero tiles**. Whether that "success" is charged **cannot be
determined while the meter is frozen.** Do not assert either way.

## 11.5 🔴 Four MORE defects from the second probe — and one is severe (2026-08-16)

| # | Defect | Severity | Evidence |
|---|---|---|---|
| **12.5** | **🔴 THE CALLER'S API KEY IS EMBEDDED IN THE `download_link` URL PATH.** `/v1/heat_intelligence` returns an S3 link of the form `.../<tier>_api/accountid%3Dacc%23<ACCOUNT>/api_key%3D<32-CHAR-KEY>/type%3D.../activity_id%3D...` — the live credential, in a URL, together with the account id | **SEVERE** | `results/fixtures/probe_heatintel.json` (**now redacted**) |
| **12.6** | **`heat_intelligence` returns a rendered PDF, not data.** The spec's response schema is literally `{}`, giving no warning. A programmatic caller gets a 748 KB `wkhtmltopdf` report | **HIGH** — makes the endpoint unusable for any agent | same |
| **12.7** | **Spec/server mismatch on `analysis`.** The published schema says `maxItems: 5`; the server returns HTTP 400 *"Heat Intelligence analysis types exceed current model limit of 2 types for premium plan"*. An undocumented plan-tier limit contradicting the published contract | MEDIUM | `probe_heatintel_submit.json` |
| **12.8** | **Unknown body fields are silently dropped, with no warning.** `threshold_temperature` is accepted and ignored while the real field is `threshold`. **This silently broke one of our own tests for eight days** (see below) | MEDIUM — and it is the kind of defect that costs *callers* real money in wasted calls | `probe_threshold_fieldname.json` |

**Why 12.5 matters far beyond us, and why it should lead the handover to FortyGuard.** A credential in a
URL *path* leaks into places nobody audits: web-server access logs, browser history, proxy and CDN
caches, and HTTP `Referer` headers. It is also written into any file that stores the response — **which
is exactly how it landed in our own fixture, in a repository we are required to make PUBLIC as a
submission condition.** We caught it with a pre-commit secret scan; a team without one would publish
their key and not know. **The fix is standard and cheap: put the credential in a header or use an
opaque signed token, never in the object path.**

> **Also fixed on our side, same day:** the key was found hard-coded in
> `hackathon/hackathon/run_checks.py` (a plaintext literal, present since 2026-08-08) and captured into
> `testing/results/n15_forecast_state.json`. Both redacted **before the repository's first commit**, so
> no credential has ever entered git history. `.env` is gitignored, and a scan of all 354 tracked files
> confirms zero occurrences.

## 11.6 ⚠ A defect in OUR OWN code, found by defect 12.8 — and it affects a published finding

[verify_api_defects.py:172](testing/verify_api_defects.py#L172) sends **`"threshold_temperature": 30.0`**.
The API validates **`threshold`** and, per 12.8, **silently ignored ours.** Proven for **zero credits**
by sending both field names with deliberately invalid values alongside an out-of-enum `granularity: 7`,
so the request could only ever 422 and never become a billable task. The response named
**`body.threshold`** (`float_parsing`) and **did not mention `threshold_temperature` at all.**

**Consequence, stated plainly:** the exceedance-vs-persistence comparison behind **defect D3 never
applied the 30.0 °C threshold it intended** — it ran against whatever the server default is. D3 was
already *withdrawn* for a different reason (the test window), and this gives a second, independent
reason the original comparison was invalid. **We also never sent the companion `direction`
(`above`/`below`) parameter at all.**

**Required before either analytic layer is quoted again:** re-run with `threshold` and `direction`
spelled as the spec defines them. **Cost: 2 paid calls. Not yet done — flagged, not hidden.**

## 11.4 A physics source found on disk, unused, and worth not losing

`i-p_a19_ch46.pdf` in the project root is **ASHRAE Handbook chapter 46, "Building Air Intake and Exhaust
Design"** — 14 pages containing *"Exhaust-To-Intake Dilution or Concentration Calculations"* and a
*"Geometric Method for Estimating Stack Height."* **That is an ASHRAE-standard method for precisely the
exhaust→intake problem this solver models, and it is used nowhere in the project.** It is a physics
cross-validation opportunity independent of Project Prairie Grass. Out of scope for the sprint; recorded
so it is not forgotten.

---

# PART 10 — Glossary

| Term | Plain meaning |
|---|---|
| **Intake** | Where a cooling machine sucks air in. The whole story hinges on its temperature |
| **Overcooling** | Running cooling harder than needed because you cannot see what is coming. FortyGuard's word |
| **Recirculation** | A machine breathing back its own hot exhaust. In the field reports, measured as *(average cell inlet − minimum cell inlet)* |
| **Plume** | The stream of hot air leaving the equipment, carried by the wind |
| **Ensemble** | Running the physics many times with slightly different assumptions, to get a spread instead of a single answer |
| **Conformal bound** | A margin whose success rate is measured, not assumed. *"Right 9 times out of 10"* — and verified at 90.0 % ± 0.4 pp |
| **p90** | The value only 1 run in 10 exceeds. The number the agent acts on, because averages hide danger |
| **Staging** | Bringing reserve cooling online. Takes ~3 h to take effect and costs money every hour |
| **Stopping rule** | Deciding *when* to act, given that waiting is cheaper and better-informed but progressively less likely to work |
| **Backward induction** | Solving the last moment first, then stepping back — like tic-tac-toe with one square left |
| **Advection / diffusion** | Wind *carrying* warm air / turbulence *mixing and diluting* it |
| **Downwash** | Wind bending a rising hot plume back down to intake level. The constant we fitted to field data |
| **CFD** | Computational fluid dynamics — a computer simulation of air flow. **Not a measurement**, which is the confusion that cost us N-11 |
| **Knife edge** | A forecast direction where the plume boundary sits inside the forecast's own uncertainty, so the answer is genuinely unresolvable |

**Added in Version 4:**

| Term | Plain meaning |
|---|---|
| **Margin** | The extra cooling headroom an operator holds because they are not sure how hot the incoming air will be. Insurance, paid for continuously whether or not it was needed. **Sizing it is now the agent's decision.** |
| **Point-at-the-constant test** | Our own honesty test for any "agentic" claim: *can you find, in the source code, the number a human wrote that produces this behaviour?* If yes, it is a threshold in a costume. |
| **Pre-registration** | Writing the pass/fail condition into the test file **before running it**, so a threshold can never be moved after seeing data. Three tests in this project are recorded as FAILED because their thresholds were mis-specified — that is the correct handling. |
| **AUC** | *Area under the ROC curve.* How well a score separates two outcomes — 0.5 is a coin flip, 1.0 is perfect. Scale-free, so unlike a standard deviation it **cannot be fooled by an ensemble that washes out toward zero**. |
| **Dilution vs confidence** | The distinction that resolved a contradiction between two of our own tests. A washed-out ensemble looks *certain* by standard deviation (everything is near zero) while actually knowing *less*. σ measures dilution; AUC measures confidence. |
| **Zero-inflated** | A distribution with a big pile of exact zeros plus a thin tail. Ours is: **more than half the compass produces no recirculation at all.** It makes an upper percentile unstable and makes a constant margin surprisingly hard to beat. |
| **Split conformal** | The specific recipe used for the bound: take the *k*-th smallest calibration residual where *k* = ⌈(n+1)(1−α)⌉. Guarantees ≥90 % coverage on exchangeable data with no distributional assumption. |
| **Paired SE** | The standard error of the *per-day difference* between two policies — the right test when both see the same days, and stronger than comparing two averages. |
| **Persistence baseline** | "Tomorrow will be like today." The honest **lower bound** on forecast skill — any real forecast beats it. Every wind and ambient error figure here is persistence-based, so real performance should be better. |
| **Anomaly (of an error)** | The error with its predictable part removed. Raw persistence error at 12 h lead had a mean of **+8.784 °C** — that is the sun, not forecast error. Subtracting the per-lead mean leaves the real uncertainty. |
| **Problem generator** | In the standard agent ladder, the organ that deliberately seeks out informative experience — the part that makes an agent *curious*. **We do not have one**; the credit-budget version was withdrawn because it optimised against FortyGuard's own revenue model. |
| **Allowable vs Recommended** | ASHRAE's two envelopes for data-centre air. **Allowable** is the wider one you may enter *"for short periods"* — **A2 = 35 °C, A3 = 40 °C**. Our breach threshold comes from here instead of from a quantile of our own model output. |
| **Clairvoyant bound** | A diagnostic policy that already knows the outcome and picks the cheapest action. If a real policy beats it, your cost model has a bug. Used to prove N-44's cost model was consistent *before* blaming the policy. |
