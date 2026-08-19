# N-49 — PRE-REGISTRATION: can the agent DETECT a cooling-plant fault, and is the detection agentic?

**Written 2026-08-16 BEFORE any result is computed. Conditions may not be edited afterwards;
amendments go in the dated log at the bottom.**

**Cost: ZERO API credits.** Existing GPU physics + cached free NOAA ASOS. No key use.

---

## 1. Why this test exists — the root cause of six failures, and what changes here

**Six decision cores died of one thing.** Wind-direction **forecast** error is 47–72°; the plume is
~40° wide. You can never know which side of the edge tomorrow lands on, so you can never act
differently. N-25, N-40, N-43, N-44/45, N-46 and N-48 are all downstream of that single fact.

**But our own measured sweep (N-46b) says the physics works decisively when direction is *known*:**

| Direction error sd | Margin saved | σ |
|---|---|---|
| **5°** | **+0.1299 °C** | **+97.9** |
| **10°** | **+0.1045 °C** | **+70.1** |
| 25° | +0.0316 | +18.5 |
| 68° (forecast-grade) | −0.0044 | −2.9 |

**Measured wind direction is accurate to ~5–10°. The 68° figure is a *forecast* error.** So: stop
forecasting. **Diagnose on observed data instead**, where the error that killed everything does not exist.

**And this is FortyGuard's own first-named problem, which we had been ignoring.** Their Track 3 brief:

> *"Most environmental monitoring systems only track indoor conditions, overlooking the hyperlocal
> microclimate dynamics... This blind spot limits **predictive maintenance accuracy**, leading to
> overcooling, component degradation, and higher operational costs."*

**Predictive maintenance is named first.** Two weeks went into "overcooling", the second clause.

## The product being tested

The agent compares the intake temperature the customer's **own sensor measures** against what
**FortyGuard's observed ambient + our modelled recirculation** says it *should* be. A persistent
positive residual means something physical is degrading — a fouling coil, a failing fan, a blocked
filter, a new heat source next door.

**Why an operator cannot do this today, and why FortyGuard is load-bearing rather than decorative:**
they watch intake temperature climb and **cannot separate weather from equipment degradation.**
Removing the weather requires accurate hyperlocal ambient. **Here FortyGuard is not the boundary
condition — it is the confound remover, and that role has no substitute.** A distant airport reading
carries ~1 °C of error, which is larger than the fault signature being hunted.

---

## 2. Glossary — defined before use

| Term | Plain meaning |
|---|---|
| **Residual** | measured intake − modelled intake. Should hover around zero if nothing is wrong. |
| **Fault signature** | the extra intake heating caused by degrading equipment. Hotter exhaust or weaker plume rise both push more of your own heat back into your intake. |
| **False alarm rate (FAR)** | how often you cry wolf when nothing is wrong. A wasted maintenance visit. |
| **Detection delay** | days between the fault starting and the agent declaring it. Lower is better. |
| **CUSUM** | a running total of small excesses. Individually invisible days accumulate into a signal. Standard, and provably efficient for a step change. |
| **Matched FAR** | every detector tuned to the *same* false-alarm rate before comparing speed — otherwise a trigger-happy detector "wins" by alarming constantly. |
| **Hindcast** | explaining what already happened, using observed inputs. The opposite of a forecast, and the reason this test escapes the 68° problem. |

---

## 3. Design

**Days:** sampled from **449 real KIAD target-hour wind directions** (2021–2026) and **534 real ambient
temperatures**, both already cached. **Observation error on direction: 5° sd**, justified because ASOS
reports direction in 10° increments, so quantisation alone is ~±5°. **No forecast error is applied,
because a diagnostic uses observed data — that is the whole point.**

**Truth per day:** the realised intake rise at the true direction from the calibrated GPU table, plus a
**fault signature** of size *F* injected as a step beginning on a randomly chosen day.

**Modelled per day:** the ensemble **mean** at the observed direction. *(Mean, not p90 — a diagnostic
wants the expected value, not an upper bound. The bound's job is coverage; the residual's job is
detection.)*

**Fault sizes swept:** **F ∈ {0.10, 0.25, 0.50, 1.00} °C**, plus **F = 0** for false-alarm calibration.
Rationale fixed in advance: 0.10 °C is below instrument resolution and should be undetectable by
anything (a sanity floor); 1.00 °C is a gross failure any method should catch (a sanity ceiling). **The
test lives or dies in the middle, at 0.25–0.50 °C.**

**Monitoring window:** 120 days per run, 400 runs per configuration.

### The three detectors, and what each isolates

| Detector | Uses | Isolates |
|---|---|---|
| **A. Raw threshold** — alarm when measured intake exceeds a tuned constant | no FortyGuard, no solver | **the true incumbent.** What an operator has today |
| **B. Tuned single-day residual** — alarm when one day's residual exceeds a tuned constant | FortyGuard + solver, no memory | whether **removing the weather** helps |
| **C. Sequential (CUSUM) on the residual** — accumulate evidence, declare when the running total crosses a bound | FortyGuard + solver + state | whether **being sequential** helps |

**All three are calibrated on fault-free days to the SAME false-alarm rate before any comparison.**
A and B each get one tuned constant; C gets its two CUSUM parameters fitted on training days only.
Every detector is tuned on TRAIN and scored on HELD-OUT runs.

---

## 4. PRE-REGISTERED CONDITIONS — fixed before any number is seen

- **P1 — is FortyGuard load-bearing for detection?** At matched FAR, detector **B must beat A** by
  **≥ 2 paired SE** in mean detection delay, at **F = 0.50 °C**. **If P1 fails, removing the weather
  confound does not help, FortyGuard is not load-bearing for diagnosis either, and this pivot is dead —
  report it and stop.**

- **P2 — is the sequential decision worth anything?** At matched FAR, detector **C must beat B** by
  **≥ 2 paired SE** in mean detection delay, at **F = 0.25 °C**. **If P2 fails, a threshold on the
  residual is sufficient, there is no agentic core here either, and that must be reported as plainly as
  a pass.** *(F = 0.25 °C is chosen deliberately: at F = 1.00 everything detects immediately and the
  comparison is uninformative.)*

- **P3 — the anti-threshold guard.** Detector C's declaration day must genuinely vary: it must fire off
  its own modal delay on **≥ 25 %** of runs. A detector that always declares on day *k* is a constant
  wearing a costume — the exact failure mode N-9 v1 had.

- **P4 — the FAR must actually be matched, and verified out of sample.** On held-out fault-free runs,
  all three detectors' false-alarm rates must lie within **±2 percentage points** of the target. **If
  they do not, the speed comparison is void** — a faster detector at a higher FAR has won nothing.

**N-49 PASSES only if P1 ∧ P2 ∧ P3 ∧ P4 hold.**

### The pre-registered negative

If P1 fails, the diagnostic pivot dies for zero credits and half a day, and the project ships as the
instrument-plus-audit. If P1 passes and P2 fails, then **FortyGuard is load-bearing but the agent is
not** — a genuinely useful product with an honest "this is a detector, not an agent" label. **Both
outcomes are worth having and both must be reported without spin.**

### ⚠ Honest predictions, recorded before running

- **P1 I expect to PASS comfortably**, and the reason is arithmetic rather than optimism: day-to-day
  ambient spans **17.8–37.2 °C** while the fault signature is 0.25–0.50 °C. Detector A hunts a 0.5 °C
  step inside several degrees of weather noise; B removes almost all of that variance. If B does *not*
  win, something is wrong with the test rather than with the idea, and I should look for a bug first.
- **P2 is the real test, and I expect it to pass at F = 0.25 but narrow at F = 0.50** — CUSUM's advantage
  over a single-day threshold is largest exactly when the per-day signal is subtle. **If that pattern
  appears, it is also the honest statement of the agent's value: it earns its keep on the faults a
  threshold cannot see, and adds nothing on the obvious ones.**
- **My two most recent predictions were both wrong** (N-46: I predicted P2/P3 risk, P1 failed; N-48: I
  predicted scaling would help, it inverted). **Weight these accordingly.**

### What N-49 CANNOT establish — stated before running

- **There is no real intake sensor and no real fault.** Faults are injected into simulated days built on
  real physics, real wind and real ambient. **This tests the DETECTION MECHANISM, not field
  performance**, and must never be described as having caught a real fault.
- **The fault model is a step.** Real fouling is gradual; a ramp would be harder to detect. A pass here
  is therefore an **upper bound** on performance.
- **One site layout** (`solver.demo_site`). N-28 showed layout sensitivity.
- **Nothing in energy or money.** The °C → kWh conversion remains unsourced. A detection product's value
  is avoided equipment damage and avoided truck rolls, neither of which we have a sourced figure for.
- **It does not establish that operators would act on it**, or that they lack a better existing method.

---

## 5. Amendments log

*(Empty.)*

### 2026-08-16 — Run 1: **GATE FAILED on P4.** Substantive conditions passed; validity condition did not.

`test_n49_detection.py` run 1 → `results/n49_detection.json`.

| Condition | Verdict | Value |
|---|---|---|
| **P1** FortyGuard load-bearing | ✅ PASS | **+34.00 σ** — mean delay **80.89 → 0.03 days** at F = 0.50 °C |
| **P2** sequential worth it | ✅ PASS | **+21.02 σ** — mean delay **49.09 → 2.56 days** at F = 0.25 °C |
| **P3** anti-threshold guard | ✅ PASS | **48 %** off modal (modal delay 3 days) |
| **P4** FAR matched, held out | ❌ **FAIL** | target 5 % ± 2 pp → **A 6.5 %, B 7.2 %, C 7.2 %**. B and C exceed the 7.0 pp ceiling by **0.2 pp** |

**Recorded as a FAIL, not a near-pass.** Methodology rule 2 forbids moving a threshold after seeing
data, and three earlier tests in this project (N-8, N-33, N-34) stand as FAILED for exactly that
reason. The conditions above are unchanged.

**Diagnosis — an estimator defect, not a goalpost problem.** The FAR was calibrated as the 95th
percentile of the per-run maximum over only **400** fault-free training runs. That quantile estimate is
too noisy to land a 5 % target out of sample, and the held-out FAR is itself measured on 400 runs
(binomial SE ≈ **1.09 pp**), so ±2 pp is only ~1.8 SE. **The fix is to reduce estimator and measurement
noise — 4,000 calibration runs and 2,000 held-out runs — against the SAME ±2 pp condition.**

### Two observations from run 1 that must be carried forward regardless of the re-run

1. **`k = 0.0000`.** The CUSUM slack was set to the 75th percentile of clean residuals and landed
   exactly at zero, because the rise field is **zero-inflated** (median p90 across bins is 0.0000, so on
   most days both truth and model are zero and the residual is exactly zero). With k = 0 the CUSUM is a
   pure running sum of positive residuals — a valid variant, but **its sensitivity is a consequence of
   zero-inflation and must be stated when the result is quoted.**
2. **The predicted pattern appeared, and this time the prediction was right.** C beats B decisively on
   subtle faults (at F = 0.10: B misses **83 %** of faults, C misses **0 %** and detects in 7.35 days)
   and is marginally *slower* on obvious ones (F = 0.50: B 0.03 d vs C 0.92 d; F = 1.00: B 0.00 vs C
   0.03). **The honest claim is therefore narrow and specific: the sequential agent earns its keep on
   the faults a threshold cannot see, and adds nothing on the ones it can.**
3. **Detector A is genuinely hopeless, and that is the quantified case for FortyGuard.** Hunting a
   0.10–1.00 °C step inside a **17.8–37.2 °C** ambient spread, it misses **38–91 %** of faults with mean
   delays of **62–111 days**.

---

### 2026-08-16 — Run 2: **GATE PASSED**, same conditions, calibration sample increased.

`test_n49_detection.py` run 2 → `results/n49_detection.json`. N_TRAIN_RUNS 400 → **4,000**;
N_TEST_RUNS 400 → **2,000**. **P4's ±2 pp condition unchanged.**

| Condition | Verdict | Value |
|---|---|---|
| **P4** FAR matched, held out | ✅ PASS | **A 4.2 %, B 4.9 %, C 5.3 %** — all inside 5 % ± 2 pp |
| **P1** FortyGuard load-bearing | ✅ PASS | **+75.63 σ** — delay **79.69 → 0.03 days** at F = 0.50 °C |
| **P2** sequential worth it | ✅ PASS | **+52.64 σ** — delay **57.48 → 2.67 days** at F = 0.25 °C |
| **P3** anti-threshold guard | ✅ PASS | **48 %** off modal (modal delay 3 days) |

**Detection delay in days, miss rate in brackets — the full picture:**

| Fault | **A** no ambient model | **B** FortyGuard, no memory | **C** sequential agent |
|---|---|---|---|
| 0.10 °C | 113.1 (**93 % missed**) | 107.8 (**86 % missed**) | **7.79 (0 % missed)** |
| 0.25 °C | 110.1 (**89 % missed**) | 57.5 (**32 % missed**) | **2.67 (0 % missed)** |
| 0.50 °C | 79.7 (**55 % missed**) | 0.03 (0 %) | 1.00 (0 %) |
| 1.00 °C | 63.7 (**39 % missed**) | 0.00 (0 %) | 0.05 (0 %) |

**The claim this licenses is narrow and specific, and must be stated that way:** the sequential agent
earns its keep on the subtle faults a threshold cannot see — at 0.10–0.25 °C a single-day threshold
misses **32–86 %** while the agent misses **none** — and adds nothing on the obvious ones (at 0.50 °C
the threshold is marginally *faster*). **This is the first gate any decision core in this project has
passed**, and the prediction recorded in §4 before running was correct this time.

---

### 2026-08-16 — N-49b: **FAILED P5.** The FortyGuard-SPECIFIC claim is not yet established.

`test_n49b_station.py` → `results/n49b_station.json`. Adds **detector D** — intake minus a nearby
airport reading — because N-49's detector A had *no* outdoor reference at all and is therefore the
weakest possible incumbent. C and D use **identical CUSUM machinery**, so the only difference is
ambient accuracy.

**Station-vs-site divergence, measured from a saved 17,862-tile FortyGuard field:**

| Separation | n | median \|ΔT\| (07-28 / 06-23) |
|---|---|---|
| 1–2 km | 2,613 | 0.075 / 0.105 |
| 2–3 km | 4,372 | 0.101 / 0.174 |
| 3–4 km | 6,119 | 0.212 / 0.361 |
| **4–5 km** | **3,375** | **0.420 / 0.399** |
| 5–6 km | **508** | 0.191 / 0.208 ← **breaks the monotone trend** |

**Detection delay at F = 0.25 °C, matched FAR:**

| Station error sd | C (FortyGuard) | D (station) | σ |
|---|---|---|---|
| 0.10 | 2.83 d | 2.53 d | **−9.4** |
| **0.20** | 2.83 d | 7.30 d | **+42.1** |
| 0.30 | 2.83 d | 18.34 d | +39.4 |
| 0.50 | 2.83 d | 62.48 d | +58.0 |
| 1.00 | 2.83 d | 101.37 d | +117.4 |

| Condition | Verdict |
|---|---|
| **P5** C beats D at the measured station error | ❌ **FAIL** (−9.39 σ, judged at 0.10 °C) |
| P6 FARs matched | ✅ PASS (C 4.7 %, D 5.5 %) |

**Why it failed, and it is a defect in MY measurement rule, not in the finding.** The rule was *"take
the largest resolvable separation bin"*, which selected the **5–6 km bin at n = 508** — a bin sampling
only the **corners** of a square AOI, which breaks the clean monotone trend established by four
better-populated bins. That yielded 0.199 °C, so P5 was judged at a swept 0.10 °C where C and D are
equivalent.

**What IS established, and it does not depend on that choice:** **the crossover is 0.20 °C.** FortyGuard
wins decisively above it. And the best-populated far measurement — **4–5 km, n = 3,375, 0.40–0.42 °C** —
is **twice the crossover**, with KIAD ~8 km away and the trend still increasing.

> **Recorded as a FAIL, not a near-pass.** The outcome has now been seen, so re-picking the estimator
> would be exactly the p-hacking that rules N-8/N-33/N-34 stand as FAILED for. **A clean claim requires
> re-registering with the bin rule fixed on objective grounds first — restrict to bins with n ≥ 1,000,
> which excludes the corner-sampled bin for a reason visible in the data rather than in the result — and
> re-running. That proposal is being made AFTER seeing the direction, and must be weighted accordingly.**

**Artifact worth carrying forward:** at station sd = 0.10, D is *slightly faster* (−9.4 σ). Adding
symmetric noise to a zero-inflated residual lifts the CUSUM slack `k` off zero and changes its
character. **At very small station error the two detectors are effectively equivalent and differences
there are calibration artifacts, not findings.**

**Consequence for the pitch, until a clean re-run exists:** say *"an accurate ambient reference"* is
load-bearing — which N-49 P1 establishes at +75.6 σ — and describe FortyGuard's 60 m advantage over a
station as **supported but not yet established**, with the 0.20 °C crossover as the honest statement.
