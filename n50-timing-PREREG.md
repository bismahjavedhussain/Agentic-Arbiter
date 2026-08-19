# N-50 — PRE-REGISTRATION: when should the agent commit its setpoint?

**Written 2026-08-16 BEFORE any result is computed. Conditions may not be edited afterwards;
amendments go in the dated log at the bottom.**

**Cost: ZERO API credits.** Existing GPU physics table + cached free NOAA ASOS. No key use.

> **⚠ This is the SEVENTH decision core, and I had stated I would stop at six.** The user overrode
> that, and the override is defensible for one specific reason: **this is not a new idea — it is the
> original when-to-act decision with a code-level defect repaired.** N-44 held `AMB = 30.0` frozen on
> all 4,000 days and scored only the recirculation rise, which **deleted the one term that sharpens**
> from the problem it was testing. That is a line of code, not a reinterpretation. **But the honest
> record is that six previous cores failed, and this one is more likely to fail than not.**

---

## 1. Why this differs from the six that failed

**Every previous core died of one thing:** wind-direction **forecast** error (47–72°) against a ~40°
plume. You can never tell which side of the edge tomorrow lands on, so you can never act differently.

**This decision is driven by the ambient bound, which is direction-independent.** It does not need the
plume edge resolved.

**And the sharpening it depends on has now been measured, positive, for the first time:**

| Measurement | Exponent | Verdict |
|---|---|---|
| N-25, FortyGuard spatial sd | −0.0608, CI [−0.316, +0.195] | unmeasurable — CI contains everything |
| N-40, recirculation σ through the solver | −0.1166, CI [−0.186, −0.048] | decisive negative |
| **N-45, ambient anomaly** | **+0.3414, CI [+0.2427, +0.4402]** | **excludes zero** |

Ambient enters intake temperature **additively**, so there is no dilution mechanism to invert it the way
there was for the recirculation term. **That structural difference is why this is worth one run.**

**The magnitude, measured (ambient persistence-anomaly sd × 1.2816 for a one-sided 90 % bound):**

| Lead | ambient sd | required margin |
|---|---|---|
| 12 h | 4.125 °C | **5.29 °C** |
| 9 h | 3.108 °C | 3.98 °C |
| 6 h | 2.614 °C | 3.35 °C |
| **3 h (deadline)** | 2.459 °C | **3.15 °C** |

**Waiting from 12 h to 3 h cuts the required margin by 2.14 °C** — roughly twenty times the quantities
the previous cores operated on, which sat inside our own noise.

**The tension is measured on both sides:** waiting tightens the bound (above), and waiting risks the
peak arriving before capacity does — the plant needs **LEAD_H = 3 h**, and the peak hour is uncertain at
**peak_sd_h = 1.4475 h** (N-38, 15 days, leave-one-out floor 1.1579 h — the most robustly measured
decision-relevant quantity in the project).

---

## 2. The problem, specified so no cost constant is invented

**Time axis.** Decision hours *t* = 0…9. Peak hour ~ Normal(**12**, **1.4475**), clipped to [1, 16].
Forecast lead at decision hour *t* is **12 − t**, so leads run 12 h down to 3 h and map directly onto the
measured ambient error pool. Capacity comes online at *t* + 3 and helps only if **online ≤ peak_h**.

**What the agent observes at each hour *t*:** the ambient forecast at lead 12−*t* (error drawn from the
measured KIAD anomaly pool for that lead), and the ensemble **p90 of recirculation** at the forecast wind
direction (direction error drawn from the measured KIAD pool for that lead). Their sum plus a conformal
correction is the **bound** it could commit to.

**The action.** COMMIT the setpoint now, locking in the bound observed at this hour, or WAIT.

### The cost model, and why it needs no unsourced constant

**Cost is expressed in °C·hours of held margin — "margin-hours" — a physical unit.**

> **Cost = committed margin × W**, where **W is the fixed duration of the peak risk window.**

**W is deliberately independent of commitment time.** This is a correction to N-44, whose
`hours_run = max(0, HORIZON_H - online_t + 1)` made late commitment cheap *twice over* — once through a
tighter bound and again through fewer paid hours — which is part of why its DP drifted late and useless.
**Here the only benefits of waiting are a tighter bound and the risk of missing the deadline.**

**The breach penalty is NOT chosen. It is swept.** Let **R = breach penalty / (1 °C·hour)**, swept
log-spaced over **R ∈ {1, 3, 10, 30, 100, 300, 1000, 3000, 10000}** — four decades. A breach occurs when
the realised intake temperature exceeds the committed setpoint, or when nothing was committed in time.

---

## 3. The adversary — tuned, not a strawman

**The best fixed-hour rule:** commit at a fixed hour *h*\*, if the observed bound exceeds a margin
threshold *m*\*, with **both** tuned by exhaustive search on TRAIN days and scored on HELD-OUT days.
That family contains "commit at hour 0", "commit at the deadline", and "never commit" as special cases.
The same paired scoring is imported from `test_n9_staging.paired`, not reimplemented.

**The agent** is a backward-induction DP using **isotonic-regression Longstaff–Schwartz** on the
continuous observed bound — the third and cleanest of N-44's three implementations, chosen because the
binned transition-matrix approach is where **two** real defects lived. **The DP has zero tuned parameters
of its own; it sees only the cost constants the adversary also sees.**

---

## 4. PRE-REGISTERED CONDITIONS — fixed before any number is seen

- **P0 — instrument check, run first.** The simulated days must reproduce the measured ambient sd by
  lead to within 5 %, and the measured direction sd by lead likewise. **If the generator does not
  reproduce its own inputs, nothing downstream may be read.**

- **P1 — clairvoyant consistency, every R.** A clairvoyant policy (knows the outcome, picks the cheapest
  legal action) must cost **≤** every other policy at every R. If not, the cost model or action space has
  a bug and **no verdict may be read from that R.** This is the check that exposed N-44's
  transition-matrix defect.

- **P2 — the DP must win over a BAND, not a point.** There must exist a **contiguous range of R at least
  one decade wide** (≥ 3 adjacent grid values) in which the DP beats the tuned fixed-hour rule by
  **≥ 2 paired SE** on held-out days. A single isolated winning R is noise or knife-edge tuning.

- **P3 — THE ANTI-DEGENERACY GUARD, and it is the one most likely to fail.** Inside that band the DP must
  fire off its own modal commitment hour on **≥ 25 %** of committing days. **If the bound tightens
  monotonically toward a fixed deadline, "wait until the deadline" is trivially optimal and is a constant
  in a costume. N-50 FAILS if P3 fails, even if P2 passes.**

- **P4 — is the PHYSICS load-bearing in the DECISION?** The DP's commitment hour must correlate with the
  day's recirculation ensemble **spread** (the 27× knife-edge state), at **|Spearman ρ| ≥ 0.15** with a
  CI excluding zero. **Failing P4 does not kill the decision, but it kills the claim that the GPU
  ensemble drives the timing** — and in that case the honest statement is that the ensemble computes the
  belief while ambient drives the timing. **This must be reported either way.**

- **P5 — honesty on units.** Results reported in **°C·hours of margin and breach counts**. **No energy or
  dollar figure may be quoted** — the °C → kWh conversion is still unsourced (see
  `n45-costmodel-PREREG.md` §2).

**N-50 PASSES only if P0 ∧ P1 ∧ P2 ∧ P3 hold. P4 is reported separately as the physics-relevance verdict.**

### The pre-registered negative

If P2 fails across all four decades, **the when-to-act decision is dead for every breach penalty, not
just one guessed value** — a permanent closure, and the seventh and final attempt. If P2 passes but P3
fails, the honest finding is *"the optimal policy is 'wait until the deadline', which a fixed rule
expresses perfectly, so no agent is warranted."* **Both must be reported as plainly as a pass.**

### ⚠ Honest predictions, recorded before running

1. **P3 is the likely failure mode, and I said so before writing the code.** The required margin falls
   monotonically as lead shortens across the actionable range (5.29 → 3.15 °C), and the deadline is
   fixed at *t* + 3 ≤ peak_h. The only thing preventing "wait until the last moment" from being trivially
   optimal is that **peak_h is uncertain (sd 1.4475 h)**. Whether 1.4475 h is enough to make timing
   genuinely state-dependent is exactly what P3 tests, and I do not know the answer.
2. **P4 is a coin flip.** The mechanism that could carry it: on a knife-edge day the recirculation spread
   is 27× wider, widening the total bound and plausibly shifting the optimal hour. But recirculation is
   0–0.85 °C against an ambient bound of 3.15–5.29 °C, so it is a **6–27 % perturbation** on the state
   variable. It may simply be too small to move the decision.
3. **N-24's existing map is the prior:** at peak_sd_h = 1.49 h the rule won by **+11.9 σ** when the
   sharpening exponent was at the random-walk value 0.50, and **lost at every peak-hour uncertainty when
   there was no sharpening at all.** We now measure **+0.3414**, which sits between those cases — closer
   to the losing end than the winning one. **That is a reason for caution, not optimism.**
4. **My last three predictions:** N-46 wrong (predicted P2/P3 risk, P1 failed), N-48 wrong (predicted
   scaling would help, it inverted), N-49 right (predicted the subtle-fault pattern). **Weight accordingly.**

### What N-50 cannot establish — stated before running

- **Simulated days on real inputs.** Real KIAD ambient (534 days) and real wind (449 days) and real
  solver physics, but the days are sampled. This tests the DECISION STRUCTURE, not FortyGuard's forecast
  skill.
- **Persistence error is a LOWER bound on forecast skill**, for both ambient and direction. A real
  forecast sharpens *more*, which would favour the agent — so a failure here is not necessarily final,
  but a pass would be optimistic.
- **One site layout** (`solver.demo_site`); N-28 showed layout sensitivity.
- **Nothing in energy or money.** See P5.
- **W, the risk-window duration, is a modelling choice**, not a measurement. Because cost is linear in
  W it cancels from every policy comparison — but it means absolute margin-hour figures are not
  physically calibrated and must not be quoted as savings.

---

## 5. Amendments log

*(Empty.)*

### 2026-08-16 — RESULT: **FAILED on P3.** And the P2 "win" is CONFOUNDED — see below.

`test_n50_timing.py` → `results/n50_timing.json`. 4,000 train / 4,000 held-out days.

| Condition | Verdict | Value |
|---|---|---|
| **P0** generator reproduces its inputs | ✅ PASS | every lead within **1.9 %** on both ambient and direction sd |
| **P1** clairvoyant ≤ all policies, every R | ✅ PASS | cost model consistent across all four decades |
| **P2** contiguous winning band ≥ 3 values | ✅ PASS | **7 adjacent values, R ∈ [10 … 10 000]**, σ **+13.60 → +20.61** |
| **P3** off-modal ≥ 25 % throughout the band | ❌ **FAIL** | **9 %, 10 %, 10 %** at R = 100, 1 000, 10 000 |
| **P4** timing tracks the knife-edge spread | ❌ FAIL | **ρ = +0.068**, CI includes zero |

**Sweep:**

| R | clairvoyant | tuned fixed | DP | σ | off-modal |
|---|---|---|---|---|---|
| 1 | 0.6887 | 0.6887 | 0.6887 | — | 0 % |
| 3 | 1.4078 | 2.0663 | 2.1389 | −4.36 | 44 % |
| 10 | 1.4081 | 3.4150 | 2.7128 | **+13.60** | 51 % |
| 30 | 1.4081 | 5.5150 | 3.2244 | +15.84 | 32 % |
| 100 | 1.4081 | 12.7328 | 4.2405 | +16.37 | **9 %** |
| 300 | 1.4081 | 31.7466 | 5.1293 | +18.16 | 47 % |
| 1 000 | 1.4081 | 99.1216 | 5.1023 | +19.88 | **10 %** |
| 3 000 | 1.4081 | 291.6216 | 5.6969 | +20.35 | 45 % |
| 10 000 | 1.4081 | 965.3716 | 5.3487 | +20.61 | **10 %** |

**P3 failed, and it was the pre-registered likely failure mode (§4 prediction 1).** No contiguous
≥3-value sub-band satisfies both P2 and P3: [10, 30] gives 51 %/32 % but is only two values wide.
**There is no way to rescue this inside the conditions, and the conditions stand.**

**P4 also failed, as §4 prediction 2 flagged was a coin flip.** ρ = +0.068 with a CI spanning zero:
**the commitment hour does not track the recirculation ensemble spread.** The honest statement is
therefore *"the GPU ensemble computes the belief; ambient drives the timing"* — the physics is not
load-bearing in this decision.

### 🔴 AND THE P2 WIN IS CONFOUNDED — found while checking, and it invalidates the headline

**The adversary only gets ONE look.** `run_fixed()` evaluates `margin[:, i]` at a single tuned hour and
commits there or never. **The DP scans all ten decision hours.** So the DP has strictly more information
— **ten observations against one** — and its +13.6 → +20.6 σ advantage may be an *information*
advantage rather than a *timing* advantage.

The mechanism is visible in the numbers: the fixed rule's cost explodes with R (965 at R = 10 000)
because on any day whose margin at its one chosen hour sits below threshold it **never commits at all**
and eats the full breach penalty. The DP simply catches those days at some other hour. **That is
better day SELECTION, not better TIMING.**

**The adversary family was inherited from N-9/N-44, where the question was "is there a special hour".
It is too weak for the question asked here, and that is my specification error, not a property of the
data.** The correct adversary is a **first-crossing scan rule** — *"commit at the first hour where the
margin exceeds a tuned threshold"* — which also sees all ten hours but has no state-dependent timing.
**Until that comparison exists, the +20 σ figure must not be quoted.**

**Status: N-50 FAILED, and its one passing substantive condition is not trustworthy as stated.**

---

### 2026-08-16 — N-50d: **DEFINITIVE FAIL.** The apparent win was an ORACLE LEAK in my own DP.

`results/n50d_honest.json`. **Four specification errors were found in this test, in sequence, and every
one of them had inflated the DP's apparent advantage:**

| # | Error | Effect |
|---|---|---|
| 1 | (inherited from N-44) cost double-counted late commitment | fixed in N-50's spec before running |
| 2 | Threshold grid ran to **3.0** while the margin reaches **5.5 °C** — **43 %** of (day, hour) margins exceeded it | no threshold could suppress firing; both adversaries degenerated to "always commit" |
| 3 | Scan inequality **backwards**. Margin *decreases* with t (4.68 → 1.81), so "fire when margin > m" can only fire **early or never** | the scan family was structurally incapable of waiting |
| 4 | 🔴 **ORACLE LEAK.** `run_dp` compared the **realised** `c_commit` — which contains `R × breach` from the **actual outcome** — against the continuation value | **the DP knew whether committing today would breach** |

**Error 4 is why the DP appeared to win by +13.6 → +22.6 σ.** A conformal bound covers 90 %, so *any*
committing policy must eat ≈10 % × R; at R = 10 000 every honest policy costs > 1 000, yet the "DP"
reported **5.35**. It was not beating them, it was cheating. **P1 did not catch it because the DP was
only *partially* clairvoyant (5.35 vs the true clairvoyant's 1.41), so the consistency check passed.**

**With the leak removed — the DP's action rule using an isotonic-fitted breach probability, the way
N-44 did it — the result reverses completely:**

| R | clairvoyant | fixed-1h | SCAN-LE | **DP (honest)** | **σ vs best adversary** |
|---|---|---|---|---|---|
| 10 | 1.4081 | 3.4150 | 3.5975 | 3.5189 | **−15.79** |
| 30 | 1.4081 | 5.5150 | 5.7418 | 5.7013 | **−21.87** |
| 100 | 1.4081 | 12.7328 | 12.4443 | 12.5926 | **−19.29** |
| 1 000 | 1.4081 | 99.1216 | 110.2536 | 102.3997 | **−18.52** |
| 10 000 | 1.4081 | 965.3716 | 1066.5036 | 993.4005 | **−18.43** |

**P2 FAILS at every penalty from 10 to 10 000. The DP loses by 15–22 σ.** Not a marginal miss.

### 🔴 VERDICT: the timing decision is CLOSED. Seventh and final core.

**And the diagnostic explains all seven failures in one structural sentence.** The realised breach rate
when committing, by hour: **10 % · 10 % · 10 % · 10 % · 10 % · 10 % · 11 % · 14 % · 24 % · 38 %.**

> **Because the conformal bound is calibrated per lead, waiting does not change your RISK — it is 10 %
> at every hour by construction. It changes only your COST, which falls monotonically, against deadline
> risk, which rises monotonically after t6. Two monotone curves cross at ONE hour. A fixed-hour rule
> expresses that exactly, and there is nothing sequential left to decide.**

**Calibration removes the state-dependence a stopping rule needs.** That is a real finding about this
problem class, and it is the honest answer to seven attempts.

**On my own reliability in this test: four errors, and the headline was wrong after each of the first
three fixes. That record should weigh against any further proposal from me on this decision.**
