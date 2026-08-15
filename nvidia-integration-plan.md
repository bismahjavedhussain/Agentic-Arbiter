# AI Factory Thermal Autopilot — NVIDIA Integration Plan

**Timeline:** 2–3 weeks · **Compute:** local NVIDIA GPU · **Rules:** open (NVIDIA judges, no mandated stack)
**Status:** plan only, no code yet.

---

## 0. The test I applied before adding anything

NVIDIA engineers judge a lot of hackathons. They can spot a project that bolted their logo on for
points, and it reads as *worse* than not using their stack at all — because it signals you didn't
understand your own problem well enough to know what it needed.

So every integration below had to pass one question:

> **If I removed this, would the project get measurably worse at its actual job?**

Things that passed are in Tier A and B. Things that failed are in §7, listed with the reason —
because "I considered cuOpt and rejected it because I have one site, not a routing problem" is a
*better* answer under questioning than having shoehorned it in.

**Your original hard constraints are unchanged:** plain-Python agent loop, no LangChain/LangGraph/
CrewAI/AutoGen, fail-safe to chillers, human-in-the-loop gate, phased build with a working agent
early, no fabricated capabilities, replay-mode fixtures.

---

## 1. The reframe: from "a data center" to "an AI factory"

Same system, sharper target. Three facts make this land with NVIDIA judges specifically:

**(a) They are the stakeholder.** NVIDIA's own rack designs run at extraordinary power density —
a GB200 NVL72 rack is in the ~120 kW class, versus roughly 5–15 kW for a conventional rack. Cooling
is not a side concern for these facilities; it is a primary design constraint. You are not
explaining why your problem matters. They already know.

**(b) The free-cooling opportunity is *bigger* for AI factories, not smaller — and this is the
insight to lead with.** Dense AI racks are liquid-cooled, and liquid cooling tolerates much warmer
coolant than air cooling does. A higher acceptable supply-water temperature means the wet-bulb
threshold below which free cooling is safe sits *higher* — which means more hours of the year
qualify. So the exact facilities NVIDIA is building are the ones where an intelligent free-cooling
decision unlocks the most. Most people assume dense compute means *less* free cooling. The opposite
is true, and being able to explain why demonstrates you understand the domain rather than just the
code.

**(c) Ambient conditions are only half the equation.** Whether free cooling is safe depends on
outside wet-bulb *and* on how much heat the facility is about to produce. A rack at idle and the
same rack mid-training-run are different thermal problems. A cooling decision that ignores upcoming
compute load is incomplete — and this is where an NVIDIA-native data source genuinely belongs (§3.3).

**Suggested framing line:** *"Free cooling for AI factories, decided on hyperlocal microclimate and
projected GPU load, with a calibrated confidence bound instead of a guess."*

---

## 2. The architectural upgrade — three signals instead of one

Your original design has one real weakness, and you already identified it: **FortyGuard gives a
point forecast with no uncertainty field.** Conformal prediction fixes that from your own logged
history. That works — but it means your uncertainty estimate is purely retrospective. It knows how
wrong you've *been*; it has no signal about whether *today's atmosphere* is unusually volatile.

That gap is where NVIDIA technology does genuine work.

| Signal | Source | Answers |
|---|---|---|
| **Where** | FortyGuard, 60–100 m | What is wet-bulb *at this exact site*? |
| **How uncertain** | NVIDIA Earth-2 ensemble | How volatile is the atmosphere *right now*? |
| **How much heat** | DCGM-schema GPU telemetry | What load is the facility about to carry? |

**Concept — ensemble forecasting** (new term, briefly): a single weather forecast is one guess. An
*ensemble* runs the forecast many times from slightly different starting conditions and looks at how
far apart the results drift. Tight cluster → confident atmosphere. Wide scatter → volatile, treat
predictions with suspicion. This is the classical, physics-grounded way to measure forecast
uncertainty, and it's completely independent of your residual history.

**Why this matters technically, and why it's the strongest part of this plan:** the ensemble spread
becomes a *conditioning variable* for your conformal layer. Instead of one interval width applied
uniformly, intervals widen automatically when the atmosphere is unsettled and tighten when it's
stable. That directly attacks the sharpest known weakness of conformal prediction — that its
guarantee is **marginal** (correct on average) rather than **conditional** (correct in every
situation). Conditioning on a difficulty signal is a recognised, principled way to claw back some
conditional validity.

So the honest one-line defense is:

> *"FortyGuard tells me where. Earth-2 tells me how much to trust it. Conformal prediction turns
> both into a calibrated bound I can attach a number to."*

Nothing here is decoration. Each piece closes a gap the others leave open.

---

## 3. The NVIDIA stack, by tier

### TIER A — Load-bearing, low risk. Build these.

#### 3.1 Nemotron running locally on your GPU (explanation + orchestration)

**What it is.** Nemotron is NVIDIA's family of open-weight language models. Open weights = you can
download and run them on your own hardware, no API, no per-token cost.

**Why it genuinely belongs — and this is a real architectural argument, not a flex:** your agent
advises a facility control decision. A production operator would not accept a cooling controller
whose reasoning depends on an external cloud API — that's an availability dependency and a data-
governance problem on a control path. Running the language layer **entirely on-premises on a single
NVIDIA GPU** is the architecturally correct choice for this use case. You should say exactly that.

**What it does in your system:**
- Generates the plain-language explanation for the non-technical operator
- Summarises microclimate disagreement across sampled points into readable prose
- Optionally: light orchestration decisions (how many points to sample given observed disagreement)

**What it must NOT do:** touch the numeric decision. The bound, the threshold comparison, and the
cost-asymmetry rule stay deterministic. Keep the model out of the math and say so unprompted — it's
one of the strongest things you can assert in judging.

**Setup note.** Check your VRAM first (`nvidia-smi` in a terminal — look at the total memory figure).
Pick the largest Nemotron variant that fits comfortably; smaller quantised variants run in modest
VRAM. Run it locally via a standard local-inference runtime. *I have not verified current Nemotron
variant names and VRAM requirements — check NVIDIA's model listings on Hugging Face or
build.nvidia.com before committing to a specific size.*

**Fallback.** NVIDIA hosts these models behind free-tier API endpoints at build.nvidia.com. If local
inference eats too much time, switch to hosted and note the on-prem path as designed-for. Keep the
call behind one function so switching is a one-line change.

**Risk: LOW.** **Effort: ~1 day.**

---

#### 3.2 NVIDIA Earth-2 ensemble spread — the differentiator

**What it is.** Earth-2 is NVIDIA's AI-weather initiative. The relevant open-source piece is
**`earth2studio`**, a Python package that runs pretrained AI weather models (FourCastNet, SFNO, and
others). The core advantage: because these are neural networks rather than traditional physics
solvers, you can generate a large ensemble in a fraction of the time and compute — which is
precisely what makes ensemble uncertainty practical on one GPU instead of a supercomputer.

**Its role here.** Earth-2 models are *global and coarse* (tens of kilometres). They will **not**
give you hyperlocal wet-bulb — that's FortyGuard's job, and you should be explicit about the
division of labour. What Earth-2 gives you is **synoptic-scale volatility**: is the broader weather
pattern over this region settled or unsettled in the next 12 hours? That is a real, physically
meaningful signal and it is exactly what your conformal layer is missing.

**The defensible framing:** *"Atmospheric volatility is largely a synoptic-scale property. The local
offset from regional conditions is what FortyGuard captures. So I use each source for the thing it's
actually good at, rather than pretending one can do both."* Also state the honest limit: ensemble
spread captures regional uncertainty, **not** microclimate-specific uncertainty. Naming that
yourself is worth more than hoping nobody asks.

**Scoped for 2–3 weeks — read this carefully.** Do **not** put live Earth-2 inference inside your
hourly agent loop. That's how you lose a week. Instead:

1. Design the agent to read volatility from a **pluggable provider interface** — one function,
   `get_volatility_signal(site, time)`, returning a single number.
2. Ship a **fallback provider first** (§3.4). The agent works completely without Earth-2.
3. Run Earth-2 **offline, once**, over your demo window and backtest period. Save the resulting
   spread values to a file. The provider reads from that file.
4. Live inference becomes a stretch goal, not a dependency.

This gets you the full technical story and the demo, with a hard floor under the risk.

**To verify before relying on it:** confirm which output variables the model you choose actually
provides — you need near-surface temperature and a humidity variable to derive wet-bulb. If humidity
at the surface isn't available, you can still use temperature spread alone as the volatility proxy,
which is weaker but perfectly defensible. Also note: deriving wet-bulb from Earth-2 output needs the
*same* psychrolib/Stull skill as your FortyGuard fallback — so that work serves both paths. Build it
once.

**Risk: MEDIUM (de-risked by the offline scoping).** **Effort: 2–3 days offline.**

---

#### 3.3 DCGM-schema GPU load telemetry (the stub, done right)

**What it is.** DCGM (Data Center GPU Manager) is NVIDIA's open-source tool for monitoring GPUs at
fleet scale. `dcgm-exporter` publishes metrics like GPU power draw and temperature with standardised
field names — `DCGM_FI_DEV_POWER_USAGE`, `DCGM_FI_DEV_GPU_TEMP`, and similar.

**Why this is the highest value-per-hour item in the whole plan.** Your constraints require that
operator telemetry be a *clearly-labeled stub with a documented interface*. So build that stub
**against the real DCGM field names**. You are not faking telemetry — you are building a real
integration surface with a labeled simulator behind it, so it could drop into an actual cluster by
swapping the data source.

The difference in how this reads: "I made up a load number" versus "I built against the DCGM metric
schema and stubbed the source" is enormous, and the second one costs you a couple of hours.

**What it feeds.** Projected facility heat load modifies the effective safety threshold — higher
projected load means less thermal headroom means a stricter wet-bulb bar. That makes your decision
genuinely two-variable and materially more sophisticated than a pure weather threshold.

**Be scrupulous about labeling.** The stub must be obviously a stub in the code, in the logs, and in
your demo narration. Never let a judge think you had real cluster telemetry. Overclaiming is the one
unrecoverable error in front of these judges.

**Risk: LOW.** **Effort: ~half a day.**

---

#### 3.4 Fallback volatility signal — build this BEFORE Earth-2

Not NVIDIA tech, but it's what makes the Earth-2 piece safe to attempt.

From check **I-2** in your day-1 document: query a fixed future time, then query it again later, and
watch how much the prediction gets revised. **The size of those revisions is itself a volatility
signal**, free, from data you're already collecting. Big revisions → unsettled. Stable → confident.

Build this first. It makes the volatility interface real and the agent complete. Earth-2 then
*upgrades* the signal rather than enabling it. If Earth-2 falls through entirely, you still have a
working three-signal architecture and an honest story about why the better source didn't make the
cut in the time available.

**Risk: LOW.** **Effort: ~half a day** (the collector is already running).

---

### TIER B — Real value, only if Tier A lands early

#### 3.5 RAPIDS / cuDF for the backtest sweep

**What it is.** RAPIDS is NVIDIA's GPU-accelerated data science stack; `cuDF` is a GPU dataframe
library that mirrors the pandas API closely.

**Honest assessment:** at your data scale — a few sites, a few weeks of hourly records — this is a
speed win, not a capability win, and your calibration would run fine on CPU. It becomes genuinely
justified for the **backtest parameter sweep**: multiple years of historical hours × several
thresholds × 12 horizons × multiple conformal variants is a real combinatorial pile, and that's
where GPU dataframes earn their place.

**Windows friction — factor this in.** RAPIDS on Windows requires WSL2 (a Linux environment inside
Windows). That's a genuine setup cost, plausibly most of a day for someone who hasn't used it. With
2–3 weeks, **only do this if you're ahead of schedule.** Do not let it block the conformal work.

**Risk: MEDIUM (setup).** **Effort: 1 day including WSL2.** **Verdict: stretch goal.**

---

## 4. Revised build order — 2.5 weeks (~18 days)

The rule is unchanged: **a working agent exists from day 5 and never stops working.** Everything
after is layered on top of something demoable.

**Days 1–2 — Verify, and start the clock on data**
- Run the day-1 checks (P0 and P1 groups) from `fortyguard-day1-data-checks.md`.
- **Start the hourly collector immediately.** This is the single most time-critical action in the
  project. See §5.
- Resolve the wet-bulb forecast question (B-1/B-4) and pick the data path.

**Days 3–5 — Working agent, unsophisticated**
- Plain-Python perceive → sample → naive safety-margin decision → log → explain → human gate.
- Fail-safe path wired from the start: any error, timeout, or stale data → recommend chillers.
- Retries with exponential backoff + jitter, bounded polling, structured logs, credit instrumentation.
- Record real API responses as replay fixtures.
- **Milestone: demoable end-to-end. This is your safety net — protect it.**

**Days 6–7 — NVIDIA layer one**
- Local Nemotron for the explanation layer (§3.1).
- DCGM-schema load stub (§3.3), feeding the threshold adjustment.
- Fallback volatility provider from forecast revisions (§3.4).
- **Milestone: three-signal architecture complete, all local, all working.**

**Days 8–11 — Conformal, Phase 1**
- Backtest harness + the three baselines (always-chillers / reactive-no-forecast / persistence).
- Split conformal on collected residuals; replace the naive margin with a one-sided upper bound.
- Report coverage **and** interval width, sliced by forecast horizon.
- **Milestone: calibrated confidence, measured not claimed.**

**Days 12–14 — Earth-2, offline**
- Run `earth2studio` offline over the demo/backtest window; export ensemble spread to file.
- Swap the volatility provider to read it.
- Condition conformal interval width on the spread; measure whether coverage improves in the
  volatile slices specifically. **Report the result honestly either way** — "I tested whether
  conditioning helped and it moved coverage by X" is a real finding regardless of sign.

**Days 15–17 — The number that wins it (§6), and polish**
- Compute the hyperlocal-vs-airport headline metric.
- Energy / cost / water impact figures.
- Demo rehearsal in replay mode so nothing depends on the network.

**Day 18 — Buffer.** Something will overrun. Protect this.

**If you fall behind, cut in this order:** RAPIDS → live Earth-2 → adaptive/time-series conformal
(ship split conformal, explain ACI verbally) → Earth-2 entirely (keep the revision-spread signal and
explain the design). **Never cut:** the working agent, the fail-safe path, the human gate, or the
headline metric.

---

## 5. ⚠️ The scheduling constraint that decides your conformal layer

Conformal prediction calibrates on pairs of *(what was forecast for time T, what actually happened
at T)*. Per check B-3, FortyGuard's historical data is very likely **observations** — what the
weather *was* — not an archive of past *forecasts*. If so, you cannot build forecast-error residuals
retrospectively at all.

**Which means: with 2–3 weeks, your calibration set can only be as long as the time since you
started collecting.**

- Start the collector on **day 1** → ~14 days of data by day 15 → roughly 300+ forecast/actual pairs
  per horizon. Enough for split conformal at 90%.
- Start it on **day 8** → roughly half that, thin but survivable.
- Start it in **week 3** → you have nothing, and the centerpiece of your project cannot be built.

Set up the hourly collector before you write a single line of agent code. It logs forecasts for
now+1h … now+12h, and separately logs what actually occurred. Nothing else in the project is this
time-sensitive.

**Two datasets, two purposes — keep them distinct:**
- **Historical observations** (2019→now, available immediately) → backtest the *decision logic*: how
  often would free cooling have been safe?
- **Live-collected pairs** (from day 1) → calibrate the *forecast uncertainty*.

**And be honest about the short window:** two weeks of data is enough to calibrate split conformal,
but it is *not* enough for adaptive conformal to demonstrate its advantage, because you won't
observe meaningful seasonal drift. Say so. Optionally demonstrate the adaptive variant's response by
injecting synthetic drift into a held-out series and showing intervals widen correctly. That's a
legitimate, clearly-labeled way to show the mechanism works without pretending you observed real
drift.

---

## 6. The number that wins it

Judges remember one figure. Build the project so it produces this one:

> **"Using the nearest airport weather station, this site can safely free-cool N hours per year.
> Using hyperlocal 2-metre data with a calibrated confidence bound, it safely free-cools N + X hours
> — with the same or fewer thermal-margin violations."**

This is precisely your stated value proposition — closing the gap between official regional weather
and the true microclimate — expressed as a measured result rather than a claim.

**How to compute it:** airport observations (METAR) are freely available from public archives such
as NOAA and the Iowa State Mesonet. Pull the nearest station's history, run your decision logic on
both data sources over the same historical period, and count qualifying hours plus violations under
each.

Then convert: extra free-cooling hours × facility cooling load × electricity price → dollars and kWh.
For a rack density in NVIDIA's range the numbers get large fast. Add water as a second axis if time
permits — evaporative cooling trades electricity for water, and an agent that surfaces both is
noticeably more credible than one optimising a single variable.

**Two integrity rules:**
- Report violations alongside savings. A system that free-cools more by being reckless is worse, not
  better. Showing you measured the safety side is the whole point of the calibrated bound.
- State the simulation gap plainly: this is a recommender backtested on historical data, with no
  live facility and no real thermal telemetry.

---

## 7. Deliberately excluded — and why (bring these up yourself)

Having considered and rejected things is a strength. Volunteer these before you're asked.

| Technology | Why not |
|---|---|
| **Omniverse / digital twin** | Genuinely on-theme for NVIDIA, and the natural v2 — a 3D thermal twin of the facility. But it's a visualisation layer over a decision system that must exist first, and it's weeks of work. Roadmap, not scope. |
| **cuOpt** (GPU optimisation) | Real fit for scheduling cooling across *many* sites under shared constraints. I have one site and a binary decision. There's no optimisation problem here yet. |
| **PhysicsNeMo** (physics-informed ML) | Would let me model facility thermal response rather than treating the threshold as fixed. Needs real facility telemetry I don't have. Fabricating it would violate my own no-fake-capabilities rule. |
| **NeMo Agent Toolkit** | Profiling/observability for agents, framework-agnostic. But I committed to plain Python so I could understand and defend my own control flow, and structured logging covers my needs at this scale. |
| **TensorRT / Triton / Dynamo** | Inference-serving optimisation. I have one model and one request per hour. Nothing to optimise. |
| **Fine-tuning any model** | No training data, no task-specific objective, and my language layer only explains — it doesn't decide. |

---

## 8. Honest risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Earth-2 won't run in time or in your VRAM | Medium | Fallback volatility provider (§3.4) built first; agent never depends on Earth-2 |
| `env_params` refuses future timestamps (B-1) | Unknown | psychrolib/Stull derivation from forecast dry-bulb + humidity; same code path serves Earth-2 |
| Too little calibration data | Medium-high | Start collector day 1; split conformal needs less than adaptive; be explicit about the window |
| RAPIDS/WSL2 eats a day | Medium | Explicitly a stretch goal; cut without hesitation |
| Scope creep from three NVIDIA integrations | **High** | Tier A only until it works. The phased order exists to protect you from yourself. |

**The largest risk is not technical.** It's building four impressive half-finished things instead of
one complete one. A working agent with a calibrated bound and one well-integrated NVIDIA component
beats a broken system touching five. If you're behind on day 12, cut Earth-2 and polish what works.

---

## 9. Immediate next actions

1. **Start the hourly collector.** Before anything else. §5 explains why this is irreversible.
2. Run day-1 checks B-1, B-4, B-3, B-2, A-3, C-2 and report back.
3. Run `nvidia-smi` and tell me your GPU model and total VRAM — it determines the Nemotron variant
   and whether Earth-2 local inference is realistic.
4. Confirm the framing: are you targeting the AI-factory angle (§1)? It changes the threshold values,
   the impact numbers, and the pitch.

Once I have (2) and (3), I'll turn this into the concrete implementation plan with module structure,
interfaces, and the log schema.
