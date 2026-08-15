# INTAKE — test results

**Run 2026-08-09/10 · total credits spent: 0** (`cycle_remaining_credits` read 180,980 before and
after every call — the audited key's billing cycle closed 19 July and shows `active: false`, so the
meter is frozen. **The hackathon key will have a live meter: measure the price on call #1.**)

| Test | Cost | Verdict |
|---|---|---|
| **N-5** learned per-site offset vs. area mean | free | 🔴 **FAIL as framed** — wrong baseline (my error) |
| **N-5b** same, against the correct 3 km HRRR baseline | free | 🟡 **PASS but small** |
| **N-6** solver validation, six physics checks | free | ✅ **6/6 PASS** (after two fixes) |
| **N-7** is there a real compute bottleneck? | free | ✅ **PASS — measured** |
| **N-1** does `env_params` vary spatially? | 2 calls | ✅ **PASS decisively** |
| **N-2** forecast or nowcast? | 2 calls (1 failed = free) | ✅ **PASS** |
| **E2E** full agent cycle on fixtures | free | ✅ **PASS — coverage 90.0 % ± 0.4 pp** |
| **N-9** is the decision sequential, or a threshold? | free | 🟡 **FAIL then PASS** — v1 lost to a simple rule; see below |
| **N-11** wind-speed response of intake rise | free | 🟡 **defect found and fixed** — trend was inverted |
| **N-8 v3** the saving, on the calibrated solver | free | 🔴 **FAIL** — half the claim survives; see N-8 RERUN |
| **N-12** peak hour via `time_of_measure` | 5 calls | 🔴 **VOID** — endpoint falsified |
| **N-12b** falsify `time_of_measure` against tcm | 4 calls | ✅ **endpoint proven broken** |
| **N-12c** peak_sd_h by window bisection | 25 calls | 🟡 **1.49 h** — but one day of five drives it |
| **N-13** σ(lead) leg 1 | 4 calls | 🔴 **blocked** — heatmap serves no future windows |
| **N-14** real usable data span | 15 calls | 🔴 **forward horizon +2 h, not 12 h** |
| **N-15** forecast gone, or key degraded? | 5 calls | ✅ **diagnosed** — product alive, heatmap path dead |
| **N-16** Warp GPU port — correctness then speed | free | ✅ **PASS — 72.7x, verified to 0.00007 C** |
| **N-17** recheck two untrusted defects | 5 calls | ✅ **1 escalated, 1 withdrawn** |
| **N-19** error bands on the headline (GPU sweep) | free | ✅ **PASS — band 0.47–1.94 C** |
| **N-20** fleet allocation as a 2nd agentic decision | free | 🔴 **FAIL as predicted** — equal-split wins |
| **N-18** forecast retry probe (48 attempts) | 48 calls | 🔴 **0 of 4 leads recovered** |
| **N-21** VALIDATION vs ACC field measurements | free | 🔴 **N-11 falsified; direction claim SURVIVES** |
| **N-22** calibrate the wind response to field data | free | ✅ **PASS — held-out RMS 14 % of signal** |
| **N-23** does the bound widen at a geometric edge? | free | ✅ **PASS — 13.6x wider, emergent** |

---

## The headline, and it is not what I expected

> **The value is not in the spatial resolution. And it is not a saving — it is that a single fixed
> margin is wrong in BOTH directions.**

> 🔴 **THE +1.132 C AND +2.048 C FIGURES BELOW ARE VOID.** They were computed before N-11,
> with the solver's wind-speed response inverted. N-8 has been rerun on the calibrated solver;
> read the N-8 RERUN section at the bottom of this file instead. The +0.036 C from N-5b is
> unaffected (it is a spatial measurement and does not use the wind response).

```
value of the learned per-site spatial offset      +0.036 C   (N-5b, still valid)
value of knowing today's conditions               +1.132 C   (N-8, VOID -- pre-N-11)
                                                  ---------
                                                  ~31x apart  (ratio also void)
```

I had been pitching spatial resolution. It is worth about four hundredths of a degree. What is actually
worth something is knowing **today's** conditions rather than designing for **all** conditions.

**⚠ Retraction.** The E2E run reported "1.238 °C recovered by using a bound instead of a guess." **That
number was circular** — it compared the ensemble's p90 against the same ensemble's maximum, so it measured
the width of my own Monte Carlo tail rather than anything an operator does. **N-8 replaces it.**

### And the finding that matters more than the saving

On the one wind direction that points the exhaust at the intake, the conditional bound is
~~**+2.048 °C**~~ while the no-forecast design point is ~~**+1.132 °C**~~. **Both struck through: void
pre-N-11 numbers.** The *structural* claim below — that one fixed margin errs in both directions — does
not depend on those particular values, but the values themselves must not be quoted.

> **A fixed design margin is simultaneously too generous on 7 days out of 8, and not generous enough on
> the 8th.** It over-cools most of the time *and* under-protects exactly when it matters.

That is the product. Not "we save you a degree" — *"your single margin is wrong in both directions, and
we can tell you which day is which."* It is the same argument as marginal-versus-conditional coverage,
made physical.

---

## N-5 / N-5b — how much does 60 m actually buy?

**N-5, as originally written, used the wrong baseline** — each tile against the mean of the whole 64 km²
polygon. The real competitor is HRRR at 3 km.

| | Data-centre cluster | Control polygon |
|---|---|---|
| tiles / 3 km blocks | 17,862 / 9 | 17,892 / 9 |
| total spatial sd (hot day) | 0.4183 °C | 0.3367 °C |
| **within-3 km sd — what 60 m adds** | **0.2895 °C** | 0.2223 °C |
| share of variance below 3 km | 48 % | 44 % |
| MAE, HRRR baseline | 0.1892 °C | 0.1649 °C |
| MAE, with learned anomaly | 0.1531 °C | 0.1831 °C |
| **improvement** | **+0.0361 °C (19.1 %)** | **−0.0183 °C (worse)** |
| tiles improved | 11,439 / 17,862 (64 %) | 7,902 / 17,892 (44 %) |
| variance explained R² | **+0.444** | **−0.286** |

**Two things must be said honestly:**

1. **The improvement is real but small.** 0.036 °C does not change a cooling setpoint. Sub-3 km structure
   exists (48 % of variance, sd 0.29 °C), and 44 % of it is predictable — but the absolute magnitude is a
   few tenths of a degree.
2. **Persistence is not universal.** The same method *hurts* in the control polygon 26 km away (R² −0.29).
   A built-vs-open split inside the data-centre polygon did **not** explain it (R² +0.52 near facilities,
   +0.58 far from them), so the cause is a property of the area, not of the data centres. **Do not claim
   persistence generalises.**

---

## N-6 — solver validation: 6/6

| # | Check | Result |
|---|---|---|
| 1 | Far-field relaxation (no sources → ambient) | max deviation **0.000000 °C** |
| 2 | No-wind symmetry (calm + central source) | L-R **0.000000**, U-D **0.000000** |
| 3 | Wind response (rotate inflow 180°) | downwind **+1.79 °C**, upwind **+0.00 °C** — the plume flips |
| 4 | Recirculation magnitude & decay | 60 m **+3.31** → 150 m +3.10 → 300 m +2.78 → 600 m +2.34 → 1000 m **+1.98 °C**, monotonic |
| 5 | Source scaling (double discharge) | ratio **2.00** — correct for a linear system |
| 6 | Grid convergence (dx 20 → 10 → 5 m) | change **0.139 °C**, inside tolerance (marginal) |

**Two bugs found and fixed, and one of them was mine:**
- **My test bug:** sample points in check 4 walked *inside* a neighbouring building, where obstacle cells
  are pinned to ambient — hence an impossible exact 0.0000 at 300 m. Fixed by using a clean site.
- **A real solver bug:** at near-zero wind the upwind stencil is still fully one-sided, which broke radial
  symmetry (0.49 °C). Fixed by switching to central differencing below 1 cm/s.

Check 4's profile is consistent with the literature — published downwind measurements are 0.7–0.9 °C mean
and 2.2 °C peak out to ~500 m; ours gives 2.3–3.3 °C at 60–600 m from an 11 °C discharge. Same order,
slightly high, which is expected for a 2-D model with no vertical mixing. **State that.**

---

## N-7 — the GPU bottleneck is real, and measured

```
single solve on CPU (NumPy)
  dx=20 m   100x100     0.052 s
  dx=10 m   200x200     0.583 s
  dx= 5 m   400x400    15.723 s

one daily cycle = 20 sites x 100 ensemble members
  dx=20 m      104 s    CPU is fine
  dx=10 m      871 s    CPU too slow for a 5-minute cycle
  dx= 5 m      8.7 h    CPU IMPOSSIBLE
```

**Measured, not extrapolated:** 20 ensemble runs at dx=10 took 8.71 s (0.436 s/run).

> **The bottleneck is real at the working resolution.** A GPU claim is therefore justified by a number.

⚠ **Warp is not installed, so no speedup was measured. Do not quote a speedup figure we have not
observed.** The port is the same kernel; measure it before claiming it.

---

## N-1 — `env_params` genuinely varies with location ✅

Points chosen as the **coolest and hottest tiles** from the saved 17,862-tile field, 7,166 m apart
(heatmap difference 2.4448 °C):

| parameter | cool point | hot point | difference |
|---|---|---|---|
| **elevation** *(control — proves coordinates were honoured)* | 74.0 | 93.0 | **+19.0 m** |
| solar GHI | 702.56 | 702.69 | +0.13 |
| wet-bulb °C | 22.2 | 21.8 | **−0.4** |
| relative humidity % | 69.6 | 62.2 | **−7.4** |
| ozone index | 42.2 | 44.7 | **+2.5** |
| PM2.5 index | 94.0 | 88.7 | **−5.3** |
| apparent temp °C | 29.5 | 30.1 | +0.6 |

**Per-site anchoring is real**, and the ozone gradient (+2.5 over 7 km) supports the generator-window
layer. Note the heatmap and `env_params` disagree on the *pattern* as well as the level — the heatmap says
the hot point is +2.44 °C, while `env_params` gives it a *lower* wet-bulb and much lower RH. Physically
coherent (warmer, drier air) but **confirms they are different products. Never blend them.**

---

## N-2 — genuine future values, air quality included ✅

| parameter | 2026-07-28 15:00 | now + 3 h (18:00) |
|---|---|---|
| wet-bulb °C | 22.2 | 22.1 |
| relative humidity % | 69.6 | **37.6** |
| ozone index | 42.2 | **59.4** |
| PM2.5 index | 94.0 | 52.4 |
| apparent temp °C | 29.5 | **34.2** |
| **solar GHI** | **702.56** | **119.85** |

**Solar GHI dropping from 703 to 120 between 15:00 and 18:00 is the sun genuinely being lower** — strong
independent proof the endpoint is time-resolved rather than returning a single cached value.

**Also learned:** a request for 20:00 when only ~4 h of horizon remained returned `status: failed`. Unlike
the heatmap (which returns `completed` with zero tiles), `env_params` **fails loudly** when out of horizon.
**Failed tasks cost nothing.**

---

## End-to-end — the full cycle runs, and the bound is calibrated

```
1 PERCEIVE     17,862 tiles from fixture, area ambient 31.140 C
               env_params fixture: wet-bulb 22.2, RH 69.6, O3 42.2, solar 702.56
2 ALLOCATE     60 s budget @ 0.45 s/run  ->  100 ensemble members   [runtime decision]
3 SOLVE        100 runs in 45.0 s
               intake rise  mean +1.239  sd 0.633  p50 +1.237  p90 +1.986  max +3.224 C
4 BOUND        point 32.377 C   ambient margin +0.467 C from 17,862 residuals
               ensemble p90 33.126 C  ->  90% UPPER BOUND 33.126 C
5 DECIDE       threshold 33.0 C [S]  headroom -0.126 C  ->  ELEVATED, escalate
               worst-case guess would leave -1.364 C;  calibrated bound leaves -0.126 C
               ** 1.238 C of headroom recovered by using a bound instead of a guess **
6 LOG          bound, margin, n_resid, posture, ensemble size, fixture ids, allocation decision
7 SELF-SCORE   empirical coverage 90.0% (+/- 0.4 pp) against nominal 90%  ->  well calibrated
```

**Coverage came out at 90.0 % against a nominal 90 %.** The conformal layer is doing exactly what it
claims, and the self-verification step proves it rather than asserting it.

---

## N-8 — the honest saving (replaces the circular E2E number)

**Unconditional** = what you must design for with no per-day forecast: wind direction unknown (uniform
0–360°), speed calm to brisk, load 50–100 %. **Conditional** = what you can design for given today's
forecast: only forecast error perturbed (±15°, ±1 m/s, ±20 % load). Different uncertainty sources, so the
comparison is **not** self-referential — sd 0.263 °C unconditional vs 0.592 °C conditional at 270°.

```
UNCONDITIONAL intake rise above ambient, 200 runs
  p50 +0.000   p90 +0.309   p95 +0.686   p99 +1.132   max +1.697 C
  -> design point with no forecast: +1.132 C

CONDITIONAL p90 by wind direction (intake faces west)
  wind FROM    bound      saving
      0 deg   +0.000    +1.132     exhaust blown away
     45 deg   +0.000    +1.132     exhaust blown away
     90 deg   +0.000    +1.132     exhaust blown away
    135 deg   +0.000    +1.132     exhaust blown away
    180 deg   +0.002    +1.131     exhaust blown away
    225 deg   +0.097    +1.035     exhaust blown away
    270 deg   +2.048    -0.915  <- EXHAUST ONTO THE INTAKE: the fixed margin UNDER-protects
    315 deg   +0.336    +0.797     partial

  median saving +1.132 C · 7 of 8 directions allow >0.5 C relaxation
```

**A numerical bug was found and fixed doing this.** The first run produced `max +2.05e43 °C` — a divergent
solve. Cause: the timestep used `min(dx/max(|u|,|v|), dx²/4D)`, treating advection and diffusion as
separate limits when they share the timestep and therefore add. Replaced with the correct combined
condition `dt = 0.4 / ((|u|+|v|)/dx + 4D/dx²)`, plus a divergence guard that raises rather than silently
averaging a bad run into the statistics. **Stress test after the fix: 0/40 diverged.** N-6 still 6/6.

*Side effect: the correct timestep is smaller, so a solve at dx=10 went from 0.34 s to 0.77 s — which
strengthens N-7's bottleneck rather than weakening it.*

**Caveats:** the geometry is invented (bank on the east face, neighbour 300 m east, intake on the west
face) — real numbers need real site layouts. The 11 °C discharge is a stub. The model is 2-D with no
vertical mixing. **Sweep all three and report a band.**

## What this means for the project

**Executable: yes.** Every stage runs, the physics validates, the bound calibrates, and the demo needs no
network.

**But the pitch must change**, and the measurements say how:

| Claim | Status |
|---|---|
| ~~"Your building is different, and 60 m resolution tells you by how much"~~ | 🔴 **Worth 0.036 °C. Drop it as the headline** |
| **"We replace a worst-case guess about your intake with a calibrated bound"** | ✅ **Worth 1.238 °C, measured, with 90.0 % coverage** |
| "There is a real compute bottleneck justifying GPU" | ✅ 871 s vs a 300 s budget, measured |
| "Per-site wet-bulb, solar and air quality are real" | ✅ N-1, decisively |
| "It forecasts, air quality included" | ✅ N-2 |

**Open risks:**
- **Warp uninstalled** → the speedup is unmeasured. Install and measure before claiming.
- **The 1.238 °C depends entirely on solver stubs** — discharge_k, exchange_s, diffusivity. **Sweep them
  and report a band, never a point.**
- **2-D, no vertical mixing** → recirculation runs slightly high vs. published values. State it.
- **Persistence is not universal** (control polygon R² −0.29). Do not generalise.
- The intake bound is **modelled, not measured** — we have no facility. METAR and FortyGuard history are
  the only anchors.

## Files

```
testing/
  common.py                 shared helpers, API client, fixture writer
  solver.py                 2-D advection-diffusion solver (+ Warp hook)
  test_n5_offset.py         N-5   core claim, wrong baseline (kept for the record)
  test_n5b_scale.py         N-5b  correct 3 km baseline
  test_n6_solver.py         N-6   six physics checks
  test_n7_speedup.py        N-7   compute bottleneck
  test_n1n2_envparams.py    N-1/N-2  the only paid tests
  run_e2e.py                full agent cycle on fixtures
  results/                  json outputs + fixtures/ (replay data)
```


---

# N-9 — is the staging decision genuinely sequential, or secretly a threshold?

`run_e2e.py` used to end in three if-statements on headroom. A threshold is not an agent, so this check
replaced it with an online stopping rule and then tried hard to prove the replacement was pointless.

**Calibration is real** [M]: forecast-vs-outcome residuals on **peak** temperature from
`fb_1_FCST_12H.json` vs `fb_2_HIST_SAMEWIN.json`, **6,875 matched tiles** — signed mean **+0.3489 °C**,
sd **0.1504 °C**, one-sided 90 % conformal half-width **0.4950 °C**.

## ⚠ v1 FAILED, and the failure was mine, not the method's

The first formulation assumed a **known peak hour**. Deferring was then strictly better on *both* axes —
tighter bound *and* fewer paid hours — with a hard wall where staging stopped working. "Wait until the
wall" is near-optimal by construction there, so a tuned simple rule **beat** the stopping rule
(9.358 vs 9.456) and it lost in **11 of 16** sweeps.

Two distinct errors:

1. **No tension in the problem.** Nothing punished waiting until the last legal moment.
2. **The adversary was tuned in-sample.** 301 margins fitted and scored on the same 20,000 days. Measured
   optimism from this alone: **+0.426 cost units/day** — about the size of the original gap.

## The fix was physical, not cosmetic

**You do not know which hour the peak will land on.** If it arrives early, the lead time you were saving
no longer exists and the capacity shows up after the event. So `protect_prob(t)` = P(peak ≥ t + lead)
decays as you wait — 1.00 at t=0, 0.95 at t=3, 0.63 at t=5, 0.15 at t=7 — while staging simultaneously
gets *cheaper*. How much of that risk to accept depends on how hot the forecast says it will be, and
**no fixed hour resolves that for every day.**

Also added: a **fixed** commitment cost (without it, staging in the last hours costs nothing, so the
solver "stages" as a free no-op that cannot help — 10,909 of 18,145 stagings were this artifact), plus
**held-out evaluation** and **paired standard errors**.

> **`peak_sd_h` is a stub, but a cheaply settled one.** FortyGuard's `time_of_measure` analytic returns
> the hour each tile's maximum occurred, so forecast-vs-outcome error on peak hour is directly
> measurable. **One call on Aug 18 replaces the stub with a measurement.**

## Result — the adversary is the best possible tuned fixed-hour rule

Not the rule we shipped: the best member of *"check the forecast at hour H and stage if the bound
breaches"*, with **both H and the margin** tuned by exhaustive search (12 hours × 121 margins) on
training days and scored on held-out days. That family contains the day-0 threshold *and*
defer-to-deadline as special cases. **The stopping rule has zero tuned parameters.**

| Policy (held-out, 20,000 days) | Cost/day | Regret vs oracle |
|---|---|---|
| oracle (knows temperature **and** hour) | 9.910 | — |
| **stopping rule** | **11.773** | **+1.863** |
| best tuned fixed-hour rule | 12.129 | +2.219 |
| myopic hourly threshold | 13.394 | +3.484 |
| day-0 threshold (the old code) | 13.444 | +3.533 |
| always stage | 19.334 | +9.424 |
| never stage | 39.624 | +29.714 |

```
gain over the BEST tuned rule, out of sample   +0.356 +/- 0.032   =  11.2 sigma
                                               (16.1% of the regret that rule leaves)
stagings firing off the modal hour                        41.3%
```

**Grid resolution is measured, not guessed:** 0.05 → 0.01 → 0.0025 moved the gain +0.291 → +0.356 →
+0.365, so 0.01 is the locked default.

## Where it stops winning — reported, not buried

**18 of 21 stub variations are significant wins; 2 are significant losses; 1 is indistinguishable.**

| Variation | Gain | Reading |
|---|---|---|
| tightening exponent **0.00** | **−0.204 (−5.1σ)** | If the bound never sharpens with lead time, waiting buys no information. The pessimistic corner |
| capacity gain **3.0 °C** | **−0.077 (−4.1σ)** | If staging fixes everything, the decision barely matters |
| peak-hour sd **0.5 h** | +0.005 (0.2σ) | Near-certain peak hour returns to the v1 hard-wall regime — a tie, as expected |

> **The pattern is coherent: the stopping rule earns its keep exactly where there is genuine uncertainty
> to reason about, and not otherwise.** That is a more honest shape than a clean sweep would have been.

## What this changes in the pitch

The decision is now **a time, not a yes/no.** On the fixture day the policy says *wait* at t=0–1,
*stage* at t=2–6, then *wait* again once capacity can no longer arrive before the peak. **No threshold
can produce a non-monotonic action set in time.** That is the concrete answer to "is this actually
agentic, or a dashboard with an if-statement?"


---

# N-11 — the solver's wind-speed response was inverted

## The defect, measured

The 2-D solver injected **100 % of the condenser discharge at ground level at every wind
speed.** Measured consequence, wind from 270° (straight onto the neighbour's intake):

| wind | 0.5 | 1 | 2 | 3 | 5 | 7 | 9 | 13 m/s |
|---|---|---|---|---|---|---|---|---|
| rise °C | **3.209** | 2.826 | 2.049 | 1.578 | 1.071 | 0.807 | 0.647 | **0.461** |
| implied recirculation | 29.2 % | 25.7 % | 18.6 % | 14.3 % | 9.7 % | 7.3 % | 5.9 % | 4.2 % |

**Peak at 0.5 m/s.** The ACC literature has hot recirculation rate *rising* with wind speed and
**peaking near 9 m/s**.

> **The magnitude was plausible — the published CFD range is 5–50 % recirculation and these sit
> inside it. It was the TREND that was inverted.** That is a sign error, and sign errors are what
> a judge finds in thirty seconds.

## What was missing: plume rise

Condenser discharge is hot, therefore buoyant, therefore it **rises**. Bent-over buoyant plume
theory (Briggs) gives plume rise ∝ **1/U**: in calm air the plume climbs clear of the intake
layer, and wind **bends it over and pins it down**. So the fraction re-ingested at intake level
*grows* with wind speed.

Injecting all of it at ground level is the **high-wind limit applied at every wind speed.**

The fix is a closure — `downwash_fraction(U) = U² / (U² + uc²)` — the share of discharge that
stays in the layer this 2-D model represents.

## After the fix

| wind | 0.5 | 2 | 3 | 5 | 7 | **9** | 11 | 13 m/s |
|---|---|---|---|---|---|---|---|---|
| rise °C | 0.037 | 0.362 | 0.584 | 0.903 | 1.050 | **1.083** | 1.057 | 1.004 |
| implied recirculation | 0.3 % | 3.3 % | 5.3 % | 8.2 % | 9.5 % | **9.8 %** | 9.6 % | 9.1 % |

| Check | Result |
|---|---|
| **Trend** rises over 1–7 m/s | ✅ |
| **Peak** at **9.0 m/s** vs literature ~9 m/s | ✅ |
| **Magnitude** 75 % of speeds inside the published 5–50 % band | ✅ |
| **Direction** dependence (N-6's property) survives — spread **0.903 °C** at 5 m/s | ✅ |

**Converged, not capped:** 533–863 iterations against a 4000 cap. **And free:** per-solve
1.01 s with the closure vs 1.05 s without, so N-7's compute argument is unaffected.

## ⚠ Two calibrated parameters, and I am not going to dress this up

| Parameter | Value | Fitted to |
|---|---|---|
| `uc` | 8 m/s | puts the peak at the literature's ~9 m/s |
| `exchange_s` | 20 s | puts implied recirculation inside the 5–50 % CFD band |

**The model REPRODUCES the published peak location and magnitude band. It does not derive
them.** `exchange_s` = 20 s is at least independently defensible — a 10 m cell with air moving at
a few m/s turns over in single-digit seconds, so the original 60 s was slow — but it was still
chosen to hit a target.

Sweeps: `uc` 5→12 m/s moves the peak 6→13 m/s; the exponent 1→3 moves it 3→11 m/s;
`exchange_s` 10→60 s gives peak recirculation 20 %→3 %. **Every single sweep still rises with
wind speed**, so the *direction* of the fix is robust even though the *magnitude* is not pinned.

## Still not captured — say it before a judge asks

- **Fan-flow degradation.** Cross wind cuts the volume flow upwind fans deliver, raising discharge
  temperature. Needs fan curves. Not modelled.
- **3-D wake vortices.** The reversed-flow zone behind a building is a vertical structure a 2-D
  layer model cannot resolve. The closure stands in for it.
- **No real-facility measurement anywhere in this.** Trend and peak now match published
  behaviour; the absolute level still rests on invented geometry.

## 🔴 Consequence for N-8 — must be recomputed

`demo_site`'s default is deliberately left at `exchange_s=60, downwash_uc=None` so every
previously recorded number stays reproducible. **That means N-8's figures — the +2.048 °C
worst-direction bound and the +1.132 °C median saving — were computed with the defective
wind-speed response.** Adopting the calibrated pair invalidates them and they need rerunning.
**Do not quote N-8's numbers until that is done.**


---

# N-8 RERUN (v3) — half the claim survives, and the other half was untestable

Run on the calibrated solver from N-11 (`uc = 8 m/s`, `exchange_s = 20 s`).
**Supersedes v1 (circular) and v2 (+0.502 °C, direction-averaged mush). Both void.**

## Measured

Worst direction is **270°** (mean +0.589 °C at 6 m/s); every other direction is ≤ +0.019 °C.

| Baseline at 270° | p50 | p90 | p95 | **p99** | max |
|---|---|---|---|---|---|
| intake rise °C | +0.349 | +0.745 | +0.795 | **+0.874** | +1.010 |

| wind from | conditional p90 | margin released |
|---|---|---|
| 0 / 45 / 90 / 135 / 180° | +0.000 | **+0.874** (all of it) |
| 225° | +0.103 | +0.770 |
| 315° | +0.120 | +0.754 |
| **270°** | **+0.708** | **+0.166** |

**7 of 8 directions: most of the margin is dead weight. 0 of 8: margin must be held.**
Stable under the design-wind sweep — baseline 0.817–0.971 °C across 3–12 m/s.

## 🔴 Why it failed — a logical error in the test, not a marginal result

The pre-committed pass condition required **both** failure modes in one site: best-case saving
> 50 % of baseline (✅ 0.874 vs 0.437) **and** worst-case saving ≤ 0.05 °C (❌ +0.166).

**That condition was unsatisfiable by construction.** The baseline was *defined* as the p99 at the
worst direction, so it covers the worst direction by definition. For the worst-direction saving to
reach zero, the conditional p90 would have to exceed the baseline p99 — impossible, because the
baseline is built from strictly wider uncertainty (±20° vs ±15°, ±2 vs ±1 m/s, 50–100 % vs
65–100 % load).

Three constructions of this check, three distinct flaws: **v1 circular · v2 direction-averaged
mush · v3 unsatisfiable.** Each was caught by the test rather than by a reviewer, which is the
system working — but the threshold was not lowered and the claim fails.

## ✅ What survives — and it is what the client challenge actually asks for

> **A fixed margin sized for the worst wind direction carries +0.874 °C, and on 7 of 8
> directions essentially all of it is dead weight.**

FortyGuard's Track 3 text names **"overcooling"** explicitly. That one-sided claim is measured,
robust to the design-wind sweep, and sufficient for the rubric's "measurable benefit".

## ❌ Drop from the pitch

**"A fixed margin is wrong in BOTH directions."** Not demonstrated, and not demonstrable against a
baseline defined to be sufficient. Testing the under-protection half needs a baseline set the way
operators really set it — ASHRAE design conditions at the **nearest weather station** plus a
generic recirculation allowance, which knows nothing about this site's geometry. **No defensible
number for that exists in this project**, and inventing one is not acceptable.

Also: the **−0.156 at 12 m/s** in the sweep is almost certainly an artifact of the baseline and
conditional distributions having different spreads at n=20. **Do not quote it.**


---

# Aug 11 live-API session — 58 calls, 0 credits, five findings

**Every before/after read returned `cycle_remaining 180,980 -> 180,980`.** The meter is frozen, so
this key can be tested on freely. What it cannot reveal is per-call price on a *live* meter.

## ✅ Pricing CONFIRMED from the account's own breakdown

The usage endpoint returns a per-service breakdown, not just a total:

| Service | Credits | Count | **Per call** |
|---|---|---|---|
| Heatmap Generation | 278,520 | 66 | **4,220** |
| Tile Satellite Segmentation | 244,800 | 17 | 14,400 |
| Heat Intelligence Report | 8,600 | 1 | 8,600 |
| Unused | 180,980 | — | — |

**4,220 cr/heatmap is now confirmed arithmetic, not inference.** Also: `billing_cycle` ran
2026-06-19 to 2026-07-19, but **`credits_reset_date` is 2026-08-31** — one day *after* submission.
And the count of 66 has not moved despite ~58 calls today, confirming the freeze.

## 🔴 `time_of_measure` is broken — do not use it

N-12 asked it for the daily peak hour across five summer days and got modal hours of
**0, 1, 13, 2, 22**. A temperature maximum at midnight in Virginia in July is not credible. Worse,
the **same request shape on the same date** returned `14.0` uniformly in one call and
`modal 22, range 14-22` in another; spatial sd was exactly 0.000 on three days and 2.4/3.9 on two.

N-12b falsified it directly with tcm on 2026-07-28:

```
12:00-16:00   mean per-tile max 31.122 C
20:00-23:00   mean per-tile max 24.676 C     difference +6.446 C
```

The peak is in the afternoon. The analytic nominated hour 22 — **wrong by ~8 hours.**
**N-12's "PASS" and its 8.593 h figure are void.** New defect. Also new: `start_time == end_time`
returns **HTTP 500**.

## 🟡 peak_sd_h = 1.49 h, measured — but on thin evidence

Re-measured in N-12c by window bisection on **tcm only** (5 days x 5 two-hour windows):

| day | peak window | centre |
|---|---|---|
| 2026-06-15 | 16:00-18:00 | 17.0 |
| 2026-06-30 | 16:00-18:00 | 17.0 |
| **2026-07-10** | **12:00-14:00** | **13.0** |
| 2026-07-20 | 16:00-18:00 | 17.0 |
| 2026-07-28 | 16:00-18:00 | 17.0 |

Raw sd 1.600 h; quantisation-corrected **1.492 h** — almost exactly the 1.5 h N-9 assumed.

> ⚠ **One day of five drives the entire result.** Drop 2026-07-10 and the sd is 0.000, which
> collapses N-9. The number is consistent with the assumption but n=5 with a single outlier is not
> a settled parameter. **More days are free on this key and should be run.**

## 🔴 The heatmap serves NO future windows right now

N-14 probed a ladder of 2-hour windows (small AOI, granularity 100):

```
-30h -24h -12h -6h -4h -2h  +0h  +2h  |  +4h  +8h  +10h  +12h  +18h  +24h
 ok   ok   ok   ok  ok  ok   ok   ok  | EMPTY EMPTY EMPTY EMPTY EMPTY EMPTY
```

**The timezone question is settled by the data, not assumed.** Keyed on requested `start_time` the
diurnal curve is textbook Ashburn -- 21.1 C at 04:00-06:00 rising to **33.8 C at 16:00-18:00** --
so `start_time` is read as **site-local**, and the request builder is not at fault.

## ✅ But the forecast PRODUCT is alive — N-15 discriminates the causes

| Probe | Result |
|---|---|
| `env_params`, future hour | ✅ **ok** — wet_bulb 22.6, RH 87.2, apparent 27.6 |
| `heatmap` future, `filter_type=1` | 🔴 ZERO TILES |
| `heatmap` future, `filter_type=2` | 🔴 **HTTP 500** |
| `heatmap` future, different metro (Dallas) | 🔴 ZERO TILES — not AOI-specific |
| `heatmap` past (control) | ✅ ok, 84 tiles |

So: **the forecast exists and is served at points; the heatmap path to it is dead on this key
right now.** And a 6,875-tile 12-hour heatmap forecast provably worked on this same key on
2026-08-08, with residuals measured from it (bias +0.349 C, sd 0.150). **Cause unknown and not
guessable — record as intermittent, make it day-one call #1 on Aug 18.**

## The architectural consequence, which is actually an improvement

The design assumed one heatmap call delivers the spatial field *and* the 12 h forecast. That
coupling is fragile. The robust decomposition, and every piece of it is already measured:

```
SPATIAL pattern   heatmap, HISTORICAL   -- persists 73 % day to day [M]
TEMPORAL forecast env_params at anchor points -- confirmed serving future values TODAY [M]
```

Spatial pattern from history x temporal evolution from a point forecast. **This is how it should
have been built anyway** — it degrades gracefully when the heatmap forecast path fails, and it
uses the 73 % persistence finding that was otherwise decorative.

## 🔴 N-13 σ(lead) is BLOCKED

Measuring how forecast error shrinks with lead time needs heatmap forecasts at several leads.
That path returns empty. **The tightening exponent stays unmeasured, and N-9 loses -0.204 at
exponent 0.** Options: re-attempt on Aug 18 with a live key, or rebuild σ(lead) from
`env_params` point forecasts, which do work. **The second is available now and should be tried.**


---

# N-16 — the NVIDIA number, measured on this machine

**Hardware:** NVIDIA GeForce RTX 4050 Laptop GPU, 6 GiB, **sm_89**, CUDA Toolkit 12.9, driver 13.1.
Warp 1.16.0. Grid 200 x 200, dx 10 m, **fixed 800 steps** so CPU and GPU do identical work.

## Correctness first — a speedup on wrong numbers is worthless

| | |
|---|---|
| max &#124;CPU − GPU&#124; over the whole field | **0.000247 °C** |
| mean &#124;CPU − GPU&#124; | 0.000014 °C |
| intake rise | CPU **+0.9947 °C** vs GPU **+0.9947 °C** (differ by 0.00004 °C) |

That residual is float32-versus-float64 rounding accumulated over 800 steps and nothing else. The
test **aborts before reporting any timing** if this check fails.

## Then speed — and the honest shape of it

| Workload | CPU | GPU | |
|---|---|---|---|
| **single** solve | **0.593 s** | 2.594 s | 🔴 **GPU LOSES** — 2.37 s of that is kernel compile |
| **100-member ensemble** | **63.6 s** | **0.9 s** | ✅ **72.7×** |
| per member | 0.636 s | 0.0087 s | 73× |
| 20 facilities x 100 members | 1,272 s (**21.2 min**) | **17 s** | — |

Ensemble agreement on intake rise: max &#124;CPU − GPU&#124; = **0.00007 °C**.
CPU p90 +0.8803 °C vs GPU p90 +0.8802 °C.

## Why this makes NVIDIA load-bearing rather than decorative

**State the loss, not just the win.** For one solve the GPU is *four times slower* — the compile
dominates. The GPU only matters because **a single solve is not the workload.**

> To say "90 % of the time the intake stays below X" the physics must run across a spread of
> ambient conditions, wind directions and load assumptions, and the **distribution** is the
> product. **The bound requires the ensemble, and the ensemble requires the GPU.**

A daily cycle over a 20-site campus is **21 minutes of CPU** — not viable inside an hourly decision
loop — and **17 seconds on this GPU**. That is the substitution test passing: remove the GPU and a
named stage of the pipeline stops working, because the uncertainty quantification is what creates
the compute demand.

Batching is per-ensemble-member on the third array axis, with **one kernel launch per timestep for
all members and no host transfer inside the loop**.


---

# N-19 — error bands on the headline, by sweeping every stub

The headline from N-8 v3 is *"+0.874 °C must be carried for the worst wind direction, and on 7 of 8
directions almost all of it is dead weight."* Every physical constant behind that number is either
invented or calibrated to a literature target, so quoting it bare is not defensible. This sweeps all
eight and reports the range.

**Baseline at the coded stub values: +0.956 °C** (N-8 v3 reported +0.874 °C; the small difference is
a slightly different site-builder and sampling seed).

| stub | basis | low | base | high | **span** |
|---|---|---|---|---|---|
| `bank_w` | condenser bank width | 0.468 | 0.956 | 1.943 | **1.475** |
| `exchange_s` | calibrated in N-11 | 1.913 | 0.956 | 0.478 | **1.435** |
| `uc` | calibrated in N-11 to the ~9 m/s peak | 1.524 | 0.956 | 0.587 | 0.937 |
| `discharge_k` | published 14–25 °F discharge range | 0.678 | 0.956 | 1.208 | 0.530 |
| `separation_m` | distance to the neighbour | 0.603 | 0.956 | 0.866 | 0.353 |
| `intake_r` | intake averaging disc | 1.107 | 0.956 | 0.811 | 0.296 |
| `design_wind` | speed the baseline is taken at | 0.849 | 0.956 | 1.000 | 0.151 |
| `diffusivity` | **invented outright** | 0.995 | 0.956 | 0.873 | **0.122** |

```
FULL RANGE across all sweeps    +0.468 to +1.943 C      ratio 4.2 x
1,500 solves in 9.0 s on the GPU (~16 min on CPU)
```

## Two things in that table are worth saying out loud

**1. The parameter with no physical basis at all matters least.** `diffusivity` swept across a 4×
range (4 → 16 m²/s) moves the headline by **0.122 °C** — the smallest span of any stub. The most
arbitrary choice in the solver is not driving the answer.

**2. The largest contributor is not really a stub.** `bank_w` is the **condenser bank width** — a
geometry fact that would simply be measured for any real facility. It only floats here because the
site is invented. Discount it and the dominant remaining uncertainty is `exchange_s`, the single
calibration constant, which is exactly where N-11 already says the weakness is.

## How to quote the headline

> ❌ *"The saving is 0.874 °C."*
>
> ✅ *"The margin carried for the worst wind direction is **of order 1 °C**, spanning 0.5–1.9 °C
> across the plausible range of every unmeasured constant. **The conclusion — that it is dead weight
> on 7 of 8 directions — holds throughout**, because it depends on the direction contrast, not the
> absolute level."*

The contrast is the product. The level is a stub. Lead with the contrast.

## And the sweep is itself the GPU argument

1,500 ensemble solves in **9.0 seconds**. On CPU that is ~16 minutes, which means this sensitivity
analysis would not be run routinely — and an unswept stub is how a wrong number reaches a judge.
**The GPU does not just make the agent faster; it makes the honesty affordable.**


---

# N-20 — fleet allocation is NOT a second agentic decision

**The prediction was recorded in the file before the run:** *"I predicted this would FAIL against
equal-split."* It did.

## Setup — real solver distributions, not convenient assumptions

20 facilities with different geometry (separation 150–700 m, bank width 30–120 m, own wind
exposure). Each site's true rise distribution came from a **120-member reference ensemble on the
GPU** (14 s total), so the spreads the policies exploit are the solver's real spreads.

```
true p90 rise across sites   0.077 to 1.117 C   (threshold at the median, 0.419)
per-site sd                  0.055 to 0.428 C   -> spread varies 7.7 x across sites
budget                       200 members over 20 sites (10 each if equal); scout 3 each
```

So there **was** exploitable signal: site uncertainty varies 7.7×, independently of the mean.

## Result — every concentration strategy lost

| policy | margin | train | **held-out** |
|---|---|---|---|
| **equal_split** | +0.10 | 1.1163 | **1.1555** |
| random | +0.30 | 1.1900 | 1.1746 |
| two_stage (the proposed policy) | +0.30 | 1.2373 | 1.2292 |
| top_m_by_mean | +0.40 | 1.2107 | 1.2363 |
| top_m_marginal | +0.40 | 1.2047 | 1.2559 |

```
gain of two_stage over the best baseline:  -0.0737 +/- 0.0369  =  -2.0 sigma  (WORSE)
```

**Random beat the proposed policy.** All four concentration strategies lost to equal-split. This is
a consistent null, not a marginal miss.

## Why — and it is obvious in hindsight

Concentrating budget on marginal sites **starves the rest down to ~1 member each**. With one sample
a site's p90 estimate is worthless, so genuinely-safe sites get misclassified and the excursion cost
(1.0 vs 0.08 for over-staging) punishes that hard. Equal split gives every site enough samples to be
correctly identified as safe.

**With 20 sites and this cost asymmetry, spreading is optimal.** That is a one-line rule, not a
decision requiring an agent.

## Consequence — the agency claim rests on N-9 alone

This was the proposed answer to the honest criticism that INTAKE has only ONE genuine sequential
decision. **The proposed fix failed.** So the accurate position is:

> INTAKE has **one** genuine sequential decision — the staging stopping rule (N-9) — which is
> validated at 11.2 sigma out-of-sample against the best tuned fixed-hour rule. Compute allocation
> is **not** a second one: equal split is optimal and should simply be implemented as such.

Claiming otherwise would not survive fifteen minutes of scrutiny from anyone who tried equal-split.
**Dropped.**


---

# N-21 — first real-world validation, and it falsifies N-11

**Source.** Maulbetsch, J.S. & DiFilippo, M.N., *Effect of Wind on the Performance of Air-Cooled
Condensers*, California Energy Commission **CEC-500-2013-065** (2010) and Appendix B
**CEC-500-2013-065-APB** (2008). Field campaigns at **six operating power-plant ACCs**, 1-minute
resolution, cell inlet air temperature with wind speed and direction. Public domain.
**~40,000 digitised (wind, recirculation) pairs**, plus 12,290 direction points.

**Metric matched to the report:** they substitute minimum cell inlet temperature for far-field
ambient, so recirculation = `mean(cell inlet) − min(cell inlet)`. The solver was rebuilt as an
8×4-cell ACC deck and the identical quantity computed, because a rise-above-ambient comparison
would have been invalid.

## Measured, per plant (°F by wind-speed bin, mph)

| plant | n | 0–5 | 5–10 | 10–15 | 15–20 | 20–25 | 25–30 |
|---|---|---|---|---|---|---|---|
| El Dorado 2007 | 4,279 | 1.59 | 1.75 | **1.84** | 1.47 | 1.57 | 1.49 |
| Bighorn | 5,992 | **2.08** | 1.85 | 1.61 | 1.50 | 1.50 | 1.50 |
| El Dorado 2005 | 7,592 | 2.00 | **2.37** | 1.79 | 1.56 | 1.55 | 1.51 |
| Wygen | 11,273 | **1.29** | 1.08 | 1.01 | 1.18 | 1.27 | 1.22 |
| Front Range | 6,387 | **3.16** | 2.78 | 2.38 | 2.18 | 2.21 | 2.21 |
| Apex | 4,178 | 1.14 | 1.30 | 1.27 | 1.17 | **1.34** | — |

**Pooled (K): 1.043 · 1.032 · 0.917 · 0.838 · 0.874 · 0.882.** Peak in the **0–5 mph** bin.
Trend **−0.160 K** — recirculation **falls slightly** with wind, and is close to **flat**.

## 🔴 N-11 is falsified

| configuration | corr r vs measured | peak bin | values (K) |
|---|---|---|---|
| **measured** | — | **0–5 mph** | 1.04 → 0.88 |
| N-11 fix **ON** (uc=8) | **−0.869** | 15–20 mph | 0.567 → 2.187 → 2.010 |
| N-11 fix **OFF** (original) | **+0.798** | 0–5 mph | **29.630** → 2.862 |

The published claim that hot recirculation *rises* with wind speed to a ~9 m/s peak **is not what
six instrumented ACCs measured on this metric.** N-11 was made on the strength of that claim and it
produced an **anti-correlated** response. **Revert or recalibrate.**

## ⚠ But OFF is not validated either — overriding this test's own PASS

The test passed on `r > 0.5`. **That threshold was too lenient and I am overriding it.** Correlation
scores shape, not magnitude, and the magnitudes are indefensible:

```
at 1.12 m/s     measured 1.04 K      solver OFF 29.63 K      28x too high
measured decline across the range   -15%
solver OFF decline                  -90%
```

**The honest verdict: neither configuration is validated.** The measured wind-speed dependence is
weak and nearly flat; the solver has it either backwards (ON) or far too steep and far too large
(OFF). Every number computed on the calibrated solver — N-8 v3, N-19, N-20 — rests on this and
needs recomputing once the wind response is fixed.

## ✅ The direction claim SURVIVES, and it is the one the product is built on

Wygen, 12,290 points, mean recirculation by 45° sector:

| sector | n | K |
|---|---|---|
| 45–90° | 364 | **0.786** ← worst |
| 270–315° | 3,006 | 0.716 |
| 225–270° | 1,464 | 0.695 |
| 90–135° | 856 | 0.681 |
| 315–360° | 2,761 | 0.652 |
| 0–45° | 182 | 0.602 |
| 135–180° | 1,660 | 0.497 |
| 180–225° | 1,997 | **0.490** ← best |

```
DIRECTION swing  0.296 K  (ratio 1.60 x)
SPEED     swing  0.204 K
-> in real measurements, direction matters 1.4 x MORE than speed
```

> **This is the finding that matters.** The product's core claim is that knowing *which way* the
> wind will blow changes the decision. Six instrumented power plants say direction outweighs speed
> by 1.4×. **The thing that survived validation is exactly the thing the agent is built on** — and
> the thing that failed (the speed response) is a detail we introduced two days ago.

## Constructive path — the data can now CALIBRATE, not just test

40,000 measured points make it possible to fit the wind response instead of arguing from a
literature sentence: choose the downwash form and constants so the curve is nearly flat with a
slight decline and magnitudes near 1 K. **That would be the project's first empirically calibrated
physics**, replacing two constants currently fitted to prose.

## Honest limits, stated regardless of which way it went

- These are **power-plant ACCs, not data centres**; deck sizes and cell counts differ.
- The field metric uses min-cell as an ambient surrogate, so it measures the **spatial gradient
  across a deck**, not rise above true far-field ambient. A model can be right about one and wrong
  about the other.
- The y values are **digitised from vector figures**, not tabulated data.
- The solver deck is generic, not any of the six real sites.

---

# N-18 — forecast retry probe: 0 of 4 leads recovered in 48 attempts

| lead | attempts | first success |
|---|---|---|
| +4 h | 12 | never |
| +6 h | 12 | never |
| +8 h | 12 | never |
| +10 h | 12 | never |

**A measurement, not a conclusion about the product.** FortyGuard confirms the 12 h forecast exists
and that transient failures are retryable; on 2026-08-11 with this key, 12 retries per lead at 4 s
spacing recovered nothing. Reported as a reliability statistic in
[fortyguard-api-findings.md](../fortyguard-api-findings.md) §1.4, not as a capability claim.
**σ(lead) therefore remains unmeasured.**


---

# N-22 — the first empirically calibrated physics in this project

N-11's closure was fitted to a sentence in the literature and N-21 showed it anti-correlated
(r = −0.869) with six instrumented ACCs. This refits it to the **~40,000 measured points**.

**Method.** Amplitude is separable — `exchange_s` only scales the curve — so for each
(exponent, uc) the shape is computed once on the GPU and the optimal amplitude solved in closed form
by least squares. Fit on **three plants**, scored on the **three held out**, then checked against the
**direction** data which was never part of the fit.

## Result

```
BEST FIT     exponent p = 1.25   (N-11 used 2.0)
             uc         = 8.0 m/s
             exchange_s = 47.4 s (N-11 used 20 s)

fit set   (El Dorado 2007, Bighorn, El Dorado 2005)   RMS 0.0602 K   corr +0.850
HELD OUT  (Wygen, Front Range, Apex)                  RMS 0.1263 K   corr +0.082
                                                      = 14 % of the 0.923 K mean signal
```

| | 1.12 | 3.35 | 5.59 | 7.82 | 10.06 | 12.29 m/s |
|---|---|---|---|---|---|---|
| **fitted** | 0.984 | 1.096 | 1.026 | 0.931 | 0.841 | 0.762 |
| measured (fit set) | 1.050 | 1.107 | 0.970 | 0.838 | 0.855 | 0.836 |
| measured (held out) | 1.035 | 0.957 | 0.864 | 0.838 | 0.892 | 0.953 |

## ⚠ What is and is not validated — the correlation is near zero and that matters

**Magnitude: validated.** Held-out RMS of 0.126 K on a 0.923 K signal, on plants never used in the
fit. That is the project's first quantitative agreement with reality.

**Shape: NOT validated, and not resolvable from this data.** Held-out correlation is **+0.082**.
The reason is in the numbers: the measured wind-speed dependence spans just **0.20 K around a
0.92 K mean**. There is almost no shape to fit. The sweep confirms the fit is not sharply peaked —
`p=1.25/uc=6` gives better correlation but worse RMS; `p=2/uc=2` gives corr +0.970 but 3.6× the RMS.

> **The honest conclusion is itself the finding: wind SPEED varies deck recirculation by about
> ±10 %, wind DIRECTION by ±23 %. Speed is nearly irrelevant; direction carries the signal.**

**Direction, checked independently (never fitted):** solver ratio **2.17×** against a measured
**1.60×**. The solver **over-predicts direction sensitivity by ~35 %**, which is the expected sign of
error — the modelled deck is a bare symmetric rectangle, while real sites have asymmetric
surroundings that smear the directional dependence.

## Adopted

`solver.py` now carries a `CALIBRATED` dict, and `downwash_fraction`'s default exponent moved
**2.0 → 1.25**. The docstring records that these are fitted to field data, not to a literature claim,
and names N-21 as the falsification of the previous values.

## 🔴 Downstream consequence — the headline benefit roughly HALVED

N-19 recomputed on the calibrated solver:

| | before (N-11 values) | **after (N-22 calibrated)** |
|---|---|---|
| headline worst-direction p99 | +0.956 °C | **+0.455 °C** |
| full band across all stubs | 0.468 – 1.943 °C | **0.219 – 0.940 °C** |
| ratio | 4.2× | 4.3× |
| most influential stub | `bank_w` (0.721) | `bank_w` (0.721) |
| least influential | `diffusivity` (0.088) | `diffusivity` (0.088) |

**Calibrating against reality cut the estimated benefit by about half.** That is what calibration is
for. `diffusivity` — the one constant with no physical basis at all — remains the *least* influential
parameter, which is reassuring; and `bank_w`, the most influential, is a geometry fact that would
simply be measured for a real client.

**Still to recompute on calibrated physics: N-8 v3 and N-20.** Their numbers currently rest on the
falsified N-11 values and must not be quoted.


---

# N-23 — the bound widens by itself at a geometric knife edge

Wind direction behaves almost like a **switch**: the exhaust plume either points at the intake or it
does not. N-21 showed the field data has exactly this character — direction mattering enormously in
some periods and not at all in others. This asks whether the agent **notices by itself**, and whether
it reaches the margin.

Swept the forecast direction in 5° steps, 60-member ensemble at each with the operational
uncertainties (direction ±15°, speed ±1 m/s, load 65–100 %), on the **N-22 calibrated** solver.
**The agent is never told where the plume sector is.**

| wind from | mean | sd | **p90** | members "hot" |
|---|---|---|---|---|
| 180° | 0.0000 | 0.0002 | 0.0000 | 0 % |
| 225° | 0.0194 | 0.0437 | 0.0470 | 2 % |
| 250° | 0.1662 | 0.1327 | 0.3686 | 37 % |
| **265°** | **0.2643** | 0.1149 | **0.3962** | **72 %** ← peak level |
| 270° | 0.2511 | 0.1334 | 0.3940 | 65 % |
| **285°** | 0.1627 | **0.1379** | 0.3759 | 37 % ← **widest spread** |
| 315° | 0.0231 | 0.0557 | 0.0492 | 5 % |
| 360° | 0.0000 | 0.0000 | 0.0000 | 0 % |

```
widest spread at 285 deg, sd 0.1379 C
mean sd in the clearly-cold sectors  0.0102 C
-> spread at the edge is 13.6 x the interior spread
```

## What reaches the decision

The agent acts on the **p90**, not the mean:

```
at the edge (280 deg)        mean 0.2056 C   p90 0.3740 C    bound is 1.8 x the mean
deep in the safe sector      mean 0.0037 C   p90 0.0089 C    essentially nothing to carry
```

> **The same code relaxes on safe days and refuses to relax at the edge, purely because the ensemble
> straddles the geometry. There is no rule anywhere that says "check whether the plume points at
> me."** The behaviour is emergent from propagating direction uncertainty through the physics.

## 💡 An unexpected finding: the plume is narrower than the forecast's own uncertainty

`frac hot` **never exceeds 72 %.** Even pointing squarely at 270°, only 65 % of ensemble members land
in the hot zone. The bad sector is roughly 40° wide; the direction forecast is ±15°, so ~30° wide.

**There is therefore never a clean "definitely hot" day.** Whenever the forecast is anywhere near the
bad sector, it is partly on the edge by construction.

> **This is the strongest argument for a bound instead of a point estimate that the project has
> produced.** A point forecast of "wind from 270°" is *always* ambiguous at this geometry. The
> uncertainty is not a refinement bolted on afterwards — it is the dominant feature of the problem.

**Practical shape:** ~60 % of directions give p90 ≈ 0.00 °C (clean, defensible relaxation) · a ~55°
transition band where the bound inflates automatically · peak exposure at ~265°, p90 0.396 °C.

**Known cosmetic bug in the output:** the line `clearly-cold directions: 180-360 deg` prints
first-to-last index, and cold directions exist at *both* ends of the sweep. The sd value (0.0102 C) is
correct; the range label is not.

---

# N-8 v4 — the honest saving, recomputed on the calibrated solver   ✅ PASS

**Why rerun.** v3 ran at `exchange_s = 20 s` and downwash exponent `2.0`. N-21 falsified that pair
against real field measurements and N-22 refitted it, so v3's **+0.874 °C is void** — not because the
method was wrong, but because the physics under it was. v3's JSON is preserved at
`results/n8_saving_v3_ARCHIVED.json`.

**Three changes.** Calibrated constants (exponent 1.25, uc 8.0 m/s, exchange_s 47.4 s); moved to the
Warp GPU batch solver; and **many more members** — v3 estimated a p99 from 120 samples, where the top
1 % is about one draw. v4 uses 600. Whole test: **16.8 s on the GPU.**

| | v3 (falsified physics) | **v4 (calibrated)** |
|---|---|---|
| worst-direction p99 baseline | +0.874 °C | **+0.4369 °C** |
| best conditional saving | — | **+0.4369 °C = 100 % of baseline** |
| directions releasing most of the margin | 7 / 8 | **7 / 8** |
| directions that must hold | 1 / 8 | **1 / 8** |

**Cross-check that matters:** N-19 swept the stubs independently, on a different site build, and got
**+0.455 °C**. Two independent paths to ~0.44 °C. Quote the **band 0.219–0.940 °C** from N-19, never
either point value.

**Direction scan (40 members each, 6 m/s):** 0/45/90/135/180° all **+0.0000 °C**, 225° +0.0159,
270° **+0.3068**, 315° +0.0042. **6 of 8 directions return under 0.005 °C** — direction is a switch,
not a dial, and that one line is the product.

**A claim removed rather than rescued.** v3 printed *"a fixed margin is wrong in BOTH directions — too
generous on most, NOT ENOUGH on the aligned one."* The second half is **unreachable by construction**:
the baseline *is* the p99 at the worst direction, so the saving there approaches zero and cannot go
negative. v4 prints only what it can support — the margin is dead weight on the directions that carry
exhaust away. It is not unsafe on the aligned day.

**Design-wind sweep [S]:** baseline 0.4363 / 0.4416 / 0.4471 / 0.3571 °C at 3 / 6 / 9 / 12 m/s — nearly
flat, consistent with the calibrated exponent 1.25 producing a weak speed dependence.

---

# N-20 rerun — fleet allocation on calibrated physics   ❌ FAIL, as predicted, harder

Same code, same pre-committed pass condition (beat the best of four tuned baselines by > 2σ out of
sample), now with `exchange_s = 47.4 s` and exponent 1.25. Pre-calibration JSON archived at
`results/n20_fleet_PRECAL_ARCHIVED.json`.

| policy | held-out cost | |
|---|---|---|
| **equal_split** | **1.1758** | best baseline |
| random | 1.2044 | |
| top_m_by_mean | 1.2404 | |
| top_m_marginal | 1.2481 | |
| **two_stage (ours)** | **1.2273** | |

**Gain −0.0515 ± 0.0193 = −2.7σ** (was −2.0σ pre-calibration). Site spreads still vary **7.1×**, so
the information the policy tries to exploit is genuinely there — it just is not worth acting on.
**The conclusion is unchanged and now rests on validated physics, which makes it a quotable finding
rather than a stale one.** Agency rests on N-9 alone.

---

# 🐛 BUG FOUND AND FIXED — the two code paths disagreed on the downwash exponent

Found while doing the N-8 rerun, and it is the most instructive defect in this codebase.

N-22 recalibrated the downwash exponent to **1.25** and updated `downwash_fraction()`'s default —
but `solve()` kept its own default at the **falsified 2.0**. Any caller passing `downwash_uc` without
an explicit exponent therefore got **1.25 from one function and 2.0 from the other**:

| wind speed | retained fraction at 2.0 | at 1.25 | ratio |
|---|---|---|---|
| 3 m/s | 0.1233 | 0.2269 | **1.84×** |
| 6 m/s | 0.3600 | 0.4111 | 1.14× |
| 9 m/s | 0.5586 | 0.5367 | 0.96× |
| 12 m/s | 0.6923 | 0.6241 | 0.90× |

**`test_n16_warp.py` did exactly that** — CPU through `solve()`, GPU through `downwash_fraction()`. So
**the test asserting CPU/GPU equivalence was comparing two different physics**, differing by up to
1.84× in source strength. It kept passing only because the recorded figure predated the split.

**Fix.** `solve()` now defaults to `CALIBRATED["downwash_exponent"]`, and N-16 passes the exponent
**explicitly to both sides** so a future default change cannot silently desync them.
`test_n11_windspeed.py` is unaffected — it always passed the exponent explicitly, because comparing
exponents is its job.

**Re-verified N-16** (`n16_warp_PREFIX_ARCHIVED.json` holds the prior run):

| | prior record | re-verified |
|---|---|---|
| max abs(CPU−GPU) whole field | 0.000247 °C | **0.000251 °C** |
| ensemble agreement on intake rise | — | **0.00007 °C** |
| 100-member speedup | 72.7× | **93.5×** |
| single solve, first in process | 0.593 CPU / 2.594 GPU | — |
| single solve, kernel cached | — | **0.712 CPU / 0.144 GPU** |

Two corrections follow, both now in the plan and the claims brief:

1. **Quote 72.7×, the lower of the two runs.** The spread is CPU-side timing variance on a laptop.
2. **"The GPU loses a single solve" is true only on the first call in a process** — it is the ~2.4 s
   kernel compile, paid once. With a warm cache the GPU *wins* the single solve 4.9×. Lead with the
   loss, because it shows the number was measured, but do not state it as a property of the GPU.

**Lesson worth carrying:** never let two code paths agree by sharing a default. One `CALIBRATED`
dictionary, read explicitly at every call site.

---

# N-24 — where are the lines? Breakevens for the two unmeasured quantities   ✅ PASS

**Purpose.** Two open risks gated the agency claim and both were stated as adjectives. An open risk
described as *"unmeasured, might be fatal"* is nearly useless; the same risk with a threshold attached
is a pre-registered experiment. Both thresholds were fixed **before** the live key exists, so day one
cannot be reinterpreted afterwards.

**Method.** The N-9 adversary **imported, not reimplemented** — best fixed-hour rule with hour *and*
margin tuned exhaustively on 20,000 training days, scored on 20,000 held-out days, paired per day.
The stopping rule has zero tunable parameters. 77 sweep points, **168 s**. Bias runs against us at
every point.

**ρ, the quantity that is actually measurable.** The model is σ(lead) = σ₁₂ · (lead/12)^e; the exponent
`e` is not observable. The ratio **ρ = σ(3 h lead) / σ(12 h lead)** is: one target hour, a forecast at
~12 h lead, another at ~3 h lead, the realised value after the hour elapses. 3 h is the plant's lead
time — the moment the decision stops mattering. ρ = 1.00 means the forecast never improves; 0.50 is the
random-walk value.

### Risk 1 — forecast sharpening (peak_sd_h held at the measured 1.49 h)

| exponent | ρ | best tuned | stopping | gain | σ |
|---|---|---|---|---|---|
| 0.00 | 1.000 | 12.278 | 12.481 | **−0.203** | **−5.3 LOSES** |
| 0.05 | 0.933 | 12.258 | 12.385 | −0.127 | −2.7 LOSES |
| 0.10 | 0.871 | 12.234 | 12.282 | −0.048 | −1.2 ns |
| 0.15 | 0.812 | 12.244 | 12.209 | +0.036 | +1.1 ns |
| **0.20** | **0.758** | 12.209 | 12.131 | +0.078 | **+2.3** |
| 0.50 | 0.500 | 12.117 | 11.753 | +0.364 | +11.9 |
| 0.55 | 0.467 | 12.096 | 11.712 | +0.384 | +12.4 |
| 1.00 | 0.333† | 11.937 | 11.559 | +0.379 | +11.0 |

† **σ has a 0.05 °C floor in the schedule.** With the measured σ₁₂ = 0.1504 °C the floor binds above
exponent **0.794**, so ρ saturates at 0.333 and the analytic (3/12)^e would print an unmeasurable
0.250. `rho_of()` now computes ρ from the schedule itself. **Both breakevens sit at exponents ≈0.13–0.19,
far below the binding point, so the reported thresholds are unaffected** — but the top of the table
would have been wrong.

- **Break-even: exponent 0.129 → ρ = 0.837**
- **2σ win: exponent 0.187 → ρ = 0.772** ← the pre-registered target
- Spearman +0.843 (monotone as required)
- **Benefit saturates past ρ ≈ 0.47** — beating the target by a lot buys nothing extra

### Risk 2 — peak-hour uncertainty (sharpening held at the random-walk exponent 0.50)

| peak_sd_h | best tuned | stopping | gain | σ |
|---|---|---|---|---|
| 0.00 | 10.552 | 10.686 | **−0.134** | **−5.0 LOSES** |
| 0.30 | 10.690 | 10.803 | −0.113 | −3.8 LOSES |
| 0.40 | 10.940 | 10.933 | +0.007 | +0.3 ns |
| **0.80** | 11.351 | 11.198 | +0.153 | **+6.7** |
| **1.50 [M]** | 12.129 | 11.773 | **+0.356** | **+11.2** |
| 2.10 | 12.767 | 12.206 | **+0.560** | +9.9 ← peak |
| 3.00 | 13.751 | 13.366 | +0.385 | +8.5 |

- **Break-even: 0.395 h · 2σ win: 0.703 h**
- **Measured 1.49 h clears at +11.2σ** — and the collapse case the plan warned about is confirmed:
  at **0.00 h the rule LOSES by −5.0σ**, exactly the N-9 v1 failure mode (a race to a known wall)
- Spearman +0.849
- **Gain peaks near 2.1 h and falls beyond it** — a peak hour that could land anywhere in the horizon
  leaves no structure to exploit

### The finding that matters more than either threshold — the joint grid

Can the two risks substitute for each other? If the peak hour were wildly uncertain, could the rule
earn its keep with *no* sharpening at all?

| ρ ↓ / peak_sd_h → | 0.25 h | 0.75 h | **1.49 h** | 2.50 h | 4.00 h |
|---|---|---|---|---|---|
| **1.00** no sharpening | −20.6 | −10.8 | **−5.3** | −1.9 | −7.0 |
| 0.81 | −12.0 | −4.7 | **+1.1** | +2.7 | −1.9 |
| 0.66 | −7.9 | −0.8 | **+4.9** | +6.8 | +2.0 |
| **0.50** random walk | −4.7 | +4.5 | **+11.9** | +10.9 | +6.0 |
| 0.35 | −3.9 | +6.1 | **+12.2** | +12.6 | +8.8 |

**No — they are not substitutes.** At ρ = 1.00 the rule loses at *every* peak-hour uncertainty tested,
out to 4 h. **So the sharpening measurement on 18 Aug decides whether this decision is agentic at all.**
That is now the single load-bearing unknown in the project, and it goes first on the day-one sheet.

### Pass conditions, all fixed before the sweeps ran

| | condition | result |
|---|---|---|
| **P1** | both gain curves monotone, Spearman > 0.8 | ✅ +0.843 and +0.849 |
| **P2** | a finite breakeven exists in each | ✅ |
| **P3** | measured peak_sd_h wins by > 2σ | ✅ **+11.2σ** |

P3 deliberately has no counterpart for the sharpening rate — nothing has been measured there yet,
which is the point.

---

# 🐛 THE 9-HOUR TIMEZONE BUG — found 2026-08-12, at zero cost, and it withdraws a complaint

**The single most consequential defect found in this project, and it was ours.**

## What it is

`heatmap`'s `date_time.start_time` / `end_time` carry no offset and no zone. They are interpreted in
**the AOI's own local time**. Every paid test in this suite built its windows from `datetime.now()` —
this machine, **UTC+5** — and sent bare `"%H:00"` strings. The AOI is Loudoun County, Virginia,
**UTC−4** in August. **A silent nine-hour error on every forecast request ever issued.**

The response contains no metadata block, so nothing ever contradicted the assumption.

## How it was proved — two independent arguments, no API calls

**1. The diurnal curve.** Across five saved days (N-12c fixtures), mean per-tile max by requested
window:

| date | 10:00 | 12:00 | 14:00 | 16:00 | 18:00 | peak |
|---|---|---|---|---|---|---|
| 2026-06-15 | 24.063 | 24.888 | 25.348 | **25.755** | 24.781 | 16:00 |
| 2026-06-30 | 29.674 | 32.118 | 32.368 | **32.772** | 32.346 | 16:00 |
| 2026-07-10 | 29.887 | **31.738** | 31.127 | 30.623 | 28.749 | 12:00 |
| 2026-07-20 | 25.687 | 28.030 | 29.540 | **30.182** | 29.665 | 16:00 |
| 2026-07-28 | 27.318 | 30.084 | 31.122 | **32.498** | 25.898 | 16:00 |

Peak in the **16:00–18:00** labelled window on 4 of 5 days, already declining by 18:00–20:00. That is
a normal *local* afternoon curve. Under a UTC reading, 18:00 UTC = 14:00 EDT — essentially the true
peak — where temperature cannot be falling.

**2. Which windows returned data.** N-13 leg 1 was issued 2026-08-11 11:45 UTC and requested four
windows. Testing all three candidate conventions against a 12 h horizon:

| labels mean | 17:00 | 19:00 | 21:00 | 01:00 | explains all four? |
|---|---|---|---|---|---|
| **site-local EDT** | 9.25 h ✓ok | 11.25 h ✓ok | 13.25 h ✓ok | 17.25 h ✓ok | **YES** |
| UTC | 5.25 h ok | 7.25 h ok | 9.25 h **CONTRADICTION** | 13.25 h ok | no |
| machine-local | 0.25 h ok | 2.25 h ok | 4.25 h **CONTRADICTION** | 8.25 h **CONTRADICTION** | no |

Only site-local puts the horizon cut between **11.25 h (returns 397 tiles)** and **13.25 h (returns
zero)**. Both alternatives predict the 21:00 window should have succeeded; it did not.

## Consequences — one withdrawal, one confirmation, several invalidations

### ❌ WITHDRAWN: the claim of forecast intermittency against FortyGuard

N-18 believed it was probing leads of 4, 6, 8 and 10 h. True leads:

| believed | true | inside 12 h horizon? |
|---|---|---|
| +4 h | **13.00 h** | no — guaranteed empty |
| +6 h | **15.00 h** | no |
| +8 h | **17.00 h** | no |
| +10 h | **19.00 h** | no |

**All 48 attempts requested windows outside the horizon.** No amount of retrying could ever have
succeeded. "0 of 4 leads recovered in 48 attempts" measures our own bug, not FortyGuard's service.
`fortyguard-api-findings.md` §1.4b now carries the withdrawal explicitly. **Third defect withdrawn
after retesting**, after `persistence` and `heat_index`.

### ✅ CONFIRMED: the 12-hour horizon is real and clean

9.25 h and 11.25 h return data; 13.25 h and 17.25 h return zero tiles. Independently, on 2026-08-12 a
**9.41 h lead returned a full 17,862-tile field** over 64 km² at 60 m. `horizon_h = 12` in the Spec is
now measured rather than assumed.

### ⚠️ INVALIDATED

| Artifact | Status |
|---|---|
| **N-13** all lead labels | Recorded 2.0 / 4.0 h; really **9.25 / 11.25 h**. Superseded by N-25 — it also had an unfixed time-of-day confound |
| **N-18** entire result | Our bug. Banner added to the file. Do not quote |
| **N-14** all offsets | Shifted 9 h. Its docstring already listed a timezone as a candidate explanation and never tested it |
| **`fb_1_FCST_12H` lead label** | Labelled "12 h"; true lead recoverable only to **9.1–21.1 h** across a 12-hour-wide window. The forecast↔history **pairing is valid**, so bias **+0.3489 °C** and sd **0.1504 °C** are real residuals — only the lead is unknown. N-25 replaces it with five known leads |

### ✅ FIXED IN SHARED CODE

`common.py` gains `site_tz()`, `utc_now()`, `site_now()`, `site_window()` and `lead_hours()`.
**`site_window()` raises on a naive datetime** rather than guessing, because guessing is what caused
this. The full derivation is a block comment above them so the next person cannot repeat it.

## The lesson, and it generalises

Two code paths agreed by sharing an *implicit* convention — one used the machine clock, the other the
site clock, and nothing in between ever compared them. That is the **same class of error** as the
downwash-exponent split found the same day, where `solve()` and `downwash_fraction()` disagreed on a
default. **Make conventions explicit at every call site, or they will silently diverge.**

## What this does for the handover document

The withdrawal actually *strengthens* it. §3.1 is now the highest-value entry: a nine-hour client-side
error was able to masquerade as a service reliability problem for four days, purely because the
response echoes no timestamp and out-of-horizon requests return `completed` with zero tiles. Two small
additions — **echo the interpreted window**, and **name the horizon in an error** — would have turned a
four-day misdiagnosis into a five-minute fix. That is framed as an interface improvement, not a bug,
and it is the kind of finding a CEO can act on.

---

# 🐛 BUG — a degenerate geometry was inside the published sensitivity band

Found while building N-27, and it had been sitting in N-19 since that test was written.

`build()` places the neighbour's intake at `x = 690 + separation_m`, and the condenser bank spans
`800` to `800 + bank_w`. The intake temperature is the mean over a disc of radius `intake_r`. So the
geometry is only physically meaningful when

```
separation_m  >  110 + bank_w + intake_r
```

With the defaults (`bank_w = 60`, `intake_r = 30`) that means **separation must exceed 200 m**. N-19
swept it to **150 m**:

| separation | disc spans x | bank source spans | overlap |
|---|---|---|---|
| **150 m** | 810–870 | 800–860 | **71 % of the disc is condenser SOURCE** |
| **170 m** | 830–890 | 800–860 | **43 %** |
| 200 m | 860–920 | 800–860 | none |
| 300 m (base) | 960–1020 | 800–860 | none |

At 150 m we were averaging the discharge cells themselves and calling the result "the neighbour's
intake temperature". It is not a conservative case or a sensitivity case — **it is measuring the heat
source and reporting it as what someone breathes.** The failure is silent: you get a large,
plausible-looking number and no warning.

**Note it is not an obstacle collision.** `add_condensers()` writes to `site.source`, not
`site.obstacle`, so an obstacle-mask check passes cleanly. That is why it was never caught.

**Fix.** `solver.py` gains `intake_source_overlap()` and `assert_intake_clear()`, and both N-19 and
N-27 now call the assertion for every configuration. Separation sweeps moved to valid values.

**Effect on the published band: none.** Recomputed without the degenerate point, N-19 still gives
**+0.455 °C** with a full range of **0.219–0.940 °C, 4.3×** — because the band was driven by `bank_w`
(span 0.721) and `exchange_s` (0.672), not by separation, whose span merely tightened from ~0.14 to
0.096. The old JSON is archived at `results/n19_stubs_DEGENERATE_ARCHIVED.json`. **The number was
right for the wrong reason, and it is now right for the right reason.**

---

# N-27 — is the direction RATIO invariant to the unmeasured constants?   ❌ FAIL as pre-registered, with a confirmed conditional claim

## Why the test exists

The solver converts a FortyGuard 60 m temperature into an intake temperature. It is calibrated
against **power-station** field data because no data-centre measurement exists, and the conformal
bound is calibrated on **forecast** residuals so it is blind to solver error. The absolute magnitude
is therefore genuinely uncertain — N-19 puts it at 4.3× across the plausible constants.

**Hypothesis:** output a *releasable fraction* instead of a temperature. The client knows their own
design margin, so they supply the scale and we supply only the ratio — and a ratio should be robust,
because a systematic error multiplies numerator and denominator alike and cancels.

## An error in v1 of this test, worth recording

v1 pinned the worst direction at 270° "for comparability" and produced **negative** releasable
fractions at several directions, which looked like a violent instability in the ratio. It was an
instability in **my own definition**: the worst direction is a function of the geometry, so when the
sweep changes separation or bank width, 270° stops being the maximum and other directions come out
above the baseline. A no-forecast design must cover *its own* site's worst direction. Fixed by
finding the worst direction per configuration.

## Result on 17 configurations, absolute level spanning 4.2×

| direction | mean releasable | spread across all configs |
|---|---|---|
| 0°, 45°, 90°, 135°, 180° | ~1.00 | **≤ 0.029** |
| 270° (aligned) | 0.071 | **0.077** |
| **225°** (transition) | 0.510 | **0.626** |
| **315°** (transition) | 0.651 | **0.529** |

**Pre-registered conditions:** P1 absolute level fragile (>2×) **PASS, 4.2×** · P2 ratio spread
< 0.15 wherever the product acts **FAIL, worst 0.626** · P3 direction ordering identical everywhere
**FAIL, 3 orderings**.

**So the blanket claim is dead:** "the releasable fraction is robust" is **not true**.

Two observations on the failure, both post-hoc:
- The instability is confined to the **transition directions** 225° and 315°, where the plume is half
  on the intake. This is independently consistent with **N-23**, which found ensemble spread
  exploding **13.6×** in exactly those sectors, reached from a completely different direction.
- The three "distinct orderings" differ **only** by permuting directions that are all tied at 1.000.
  The decision-relevant tail is identical in every configuration: `… > 180 > 315 > 225 > 270`.

## Phase 2 — the refined claim, pre-registered before the held-out run

**Condition fixed after seeing the failure but BEFORE the held-out configurations were generated:**
on directions classified unambiguous (mean releasable > 0.90 or < 0.20), the spread must be < 0.10
across a **fresh** set of stub values with a **different seed**.

Held-out set: **16 configurations**, baseline spanning 0.321–0.742 °C (2.3×).

| direction | class | held-out spread |
|---|---|---|
| 0°, 45°, 90°, 135°, 180° | unambiguous | 0.009, 0.000, 0.000, 0.000, 0.008 |
| 270° | unambiguous | **0.061** ← worst |
| 225°, 315° | TRANSITION | 0.340, 0.331 |

- **refined condition: TRUE** (worst unambiguous spread **0.061** vs 0.10 threshold)
- **classification replicates out of sample: TRUE** — every direction called unambiguous stayed
  unambiguous

## What this licences, and what it does not

**NOT defensible:** *"the intake rise is 0.44 °C"* — moves 4.3× across constants never measured at a
data centre. **NOT defensible:** *"the releasable fraction is robust"* — false at the transition
directions.

**Defensible, and confirmed out of sample:**

> *"On the 6 of 8 directions where the geometry is unambiguous, the fraction of margin you can
> release is stable to within 6 percentage points — even though the absolute temperature is
> uncertain by 4.2×. On the 2 transition directions it is not stable, and the system widens its
> bound there instead of pretending to know."*

The second sentence is the valuable half. It is the **same behaviour N-23 measured independently**,
and it converts the solver's biggest weakness from an unquantified worry into a stated, tested
boundary: the advice is robust exactly where it is unambiguous, and the system knows where it is not.

---

# N-28 — does ratio stability survive a change of SITE LAYOUT?   ❌ FAIL

**Why this test exists.** N-27 concluded *"on the 6 of 8 directions where the geometry is
unambiguous, the releasable fraction is stable to within 6 percentage points, tested out of sample."*
That was out of sample in the **constants** — 16 fresh stub values, new seed — but **not** in the
**geometry**. All 33 configurations shared one topology: one hall, condensers on its east face, one
neighbour due east, everything on a single axis.

So "6 of 8" and "6 percentage points" were properties of **one layout**. Quoting them as general is
the same error N-11 made with the 9 m/s peak: taking a number produced under one set of conditions
and speaking as though it held everywhere.

**Design.** Six deliberately different topologies — not variations of one — × 13 constant
configurations × 24 directions at 15° (N-27's 45° steps can straddle a transition without resolving
it; N-23 showed the plume sector is narrower than 45°). **65,520 solves, 406 s on the GPU.**

## Result

| layout | worst dir | baseline °C | unambiguous | u-spread | t-spread | t/u |
|---|---|---|---|---|---|---|
| L1 east neighbour | 270° | 0.24–0.94 | 19/24 | 0.105 | 0.125 | 1.2 |
| L2 north neighbour | 180° | 0.24–0.94 | 18/24 | 0.091 | 0.121 | 1.3 |
| L3 diagonal NE | 225° | 0.16–0.63 | 21/24 | **0.124** | **0.146** | 1.2 |
| L4 two neighbours | 270° | 0.24–0.94 | 19/24 | 0.105 | 0.125 | 1.2 |
| L5 self-recirculation | 180° | 0.49–1.92 | 19/24 | 0.084 | 0.063 | **0.7** |
| L6 wide bank, far nbr | 270° | 0.72–2.85 | 22/24 | 0.097 | 0.091 | 0.9 |

**Pre-registered conditions:**

| | condition | result |
|---|---|---|
| **P1** | unambiguous spread < 0.10 in **every** layout | ❌ **FAIL** — worst 0.124 (L3) |
| **P2** | transitions > 2× worse than unambiguous, every layout | ❌ **FAIL** — ratios 0.7–1.3, min 0.7 |
| **P3** | ≥ 4 layouts with ≥ 3 unambiguous directions | ✅ PASS (6 of 6) |

## 🔴 Two retractions

**1. N-27's numbers do not generalise.** The unambiguous-direction count runs 18–22 of 24 across
layouts, and the worst spread is 0.124, not 0.061. **Never quote "6 of 8" or "6 percentage points."**

**2. The transition mechanism claim is WRONG and is withdrawn.** N-27 phase 2 asserted that the
instability lives at the transition directions, and linked that to N-23. Across six layouts the
transition/unambiguous spread ratio is **0.7 to 1.3** — nowhere near the 2× the hypothesis required,
and in L5 the transitions were *more* stable than the unambiguous directions. **The instability is
not concentrated at transitions.**

**And a conflation to correct, because it would be damaging if a judge found it.** N-27 phase 2
treated its result as the same phenomenon N-23 measured. They are different quantities:

| | quantity | status |
|---|---|---|
| **N-23** | within one configuration, the **ensemble spread** — uncertainty about *today's outcome* — widens 13.6× at the knife edge | ✅ **stands, untouched** |
| **N-27/28** | how much the **releasable fraction moves across unmeasured constants** | ❌ not concentrated at transitions |

N-23's finding is unaffected by this failure. Linking them was my error, not a measurement.

## ✅ What actually survives, stated at its true strength

Across **six layouts × 13 constant configurations × 24 directions**:

```
ABSOLUTE baseline          0.159  to  2.852 C     =  18.0 x
RELEASABLE FRACTION        worst spread anywhere  =  0.146  (14.6 percentage points)
```

So an **18× swing** in the quantity we cannot measure produces at most **~15 points** of swing in the
quantity we would report. That is a real robustness result and it *is* tested across geometries — but
it is much weaker than N-27 suggested. Fifteen points is not small: a releasable fraction of 85 %
becomes 70–100 %. Still actionable (release 70 %), but it must be quoted with that width.

**The defensible sentence, at last:**

> *"The absolute intake rise moves 18× across every plausible value of the unmeasured constants and
> across six different site layouts. The fraction of margin you can release moves by at most 15
> percentage points over that same range. So I quote a fraction with a 15-point band, not a
> temperature — and I tell you the provenance is power-station field data, because no data-centre
> measurement exists."*

## Process note

Two hypotheses failed in a row on this question — blanket ratio stability, then the transition
mechanism. The reframing is therefore a **partial mitigation, not a rescue**. The largest remaining
gap is unchanged and is free to close: **solver VERIFICATION** — the analytic Gaussian-plume limit,
grid convergence, and energy conservation — which asks whether the code solves its equations
correctly and needs no measurements at all. None of it has been done.

---

# N-29 — VERIFICATION: does the code solve its own equations correctly?

**Verification is not validation, and we had done none of it.** Validation asks whether the equations
match reality and needs measurements — ours are power-station data and that limit stays open until a
site sensor exists. **Verification asks whether the code solves the equations it claims to, and needs
no measurements at all.** It is checkable against exact mathematics. Until this test there was none,
which meant calibration could have been absorbing a numerical error into a physical constant — the
same mistake as N-11, one level down.

## ✅ V1 — the diffusion term is EXACT

With no obstacles, uniform wind along +x, and high Péclet number (u·L/D = **1500**), the steady
equation reduces to the heat equation with x/u as time, so the cross-stream variance must grow as

```
sigma_y^2(x) = sigma_0^2 + 2 D (x - x0) / u        slope EXACTLY 2D/u = 2.6667 m
```

This is normalisation-free — it needs no knowledge of the source strength, and the intercept absorbs
the finite source size.

| dx | steps | fitted slope | expected | error |
|---|---|---|---|---|
| 20 m | 425 | 2.6667 | 2.6667 | **0.00 %** |
| 10 m | 914 | 2.6667 | 2.6667 | **0.00 %** |
| 5 m | 2,274 | 2.6667 | 2.6667 | **0.00 %** |

Station by station at dx = 5 m, σ_y grows 24.32 → 33.54 → 40.72 → 46.82 → 52.20 → 57.08 m over
200–1200 m downstream, matching the analytic prediction at every station.

## ✅ V2 — heat conservation is EXACT

No sink term, so everything injected must be advected downstream: `u · ∫θ dy = ∫∫ S dA` exactly, at
every station. Measured **92.8270 vs 92.8270** at all six stations, **0.00 % error**, at all three
grid resolutions.

**V1 and V2 together verify the two operators that matter.** The diffusion term and the conservation
property are not approximately right — they are exact to printed precision.

## ❌ V3 — failed as pre-registered, and the cause was the MEASUREMENT, not the solver

Grid refinement on the real geometry gave **0.562, 0.479, 0.521 °C** at dx = 20, 10, 5 — a sign flip,
so no Richardson order exists (`nan`).

**Diagnosis.** `intake_temperature` computes `r = max(1, int(radius_m/dx))` then slices
`[i-r : i+r+1]`, giving `(2r+1)·dx` metres across:

| dx | cells | physical size | vs nominal 60 m |
|---|---|---|---|
| 20 m | 3 | 60 m | +0 % |
| 10 m | 7 | **70 m** | **+17 %** |
| 5 m | 13 | 65 m | +8 % |
| 2.5 m | 25 | 62.5 m | +4 % |

**The three convergence points were measuring three different quantities.** The solver was never at
fault — V1 and V2 had already proven the numerics exact.

**Confirmed by re-running with a dx-consistent operator** (average cells whose centres fall inside the
radius, a fixed physical region):

| dx | box (default) | true disc |
|---|---|---|
| 20 m | 0.56235 | 0.62573 |
| 10 m | 0.47922 | 0.58609 |
| 5 m | 0.52116 | 0.60834 |
| 2.5 m | 0.54443 | **0.60636** |

Successive changes with the consistent operator shrink **0.040 → 0.022 → 0.002 °C**. It converges to
**≈0.606 °C**. Convergence is **oscillatory**, not monotone, so a clean order of convergence cannot be
extracted and **none is claimed**.

**A second finding inside this one.** The box operator at dx = 10 averages 4,900 m² where a 30 m disc
is 2,827 m², pulling in cooler surrounding air. On the identical field it reads **0.479 vs 0.586 °C** —
a **0.107 °C** difference **from the operator alone**, larger than the 0.020 °C attributable to
resolution. Every headline number uses the box, so they are internally consistent, and 0.107 °C sits
inside the already-published band (N-19: 0.219–0.940 °C). But it is one more reason the absolute value
must never be quoted tightly. `intake_temperature` now takes `disc=True`; **the default is deliberately
unchanged** so every recorded result stays reproducible (regression checked: still 0.47922).

## 🔴 V4 — a real defect: buildings are heat SINKS, not no-flow walls

`solver.py`'s docstring said *"Buildings are no-flow obstacle cells."* **That was false.** The code
does `newT = np.where(free, newT, ambient)` — a fixed-temperature Dirichlet condition, which absorbs
heat. A no-flow wall is zero-gradient: it reflects, deflects the plume around itself, and conserves.

Measured directly by placing a 120 × 200 m building across the otherwise-verified plume:

| | downstream flux | |
|---|---|---|
| open domain | 92.8270 | **100.0 % conserved** |
| wall in the plume | 0.2911 | **99.7 % of the heat DISAPPEARED** |

Physically, air flows **around** a building; it is not annihilated by one. **So this is wrong, not a
modelling choice.** Intake rise is biased **LOW** — potentially drastically — for any wind direction
where a structure sits between source and intake, and such directions will look *"safe"* when they may
not be.

**Not yet changed**, because fixing it alters every number computed so far and that must be a
deliberate decision rather than a side effect. The docstring is corrected.

**What is and is not affected:**
- **Unaffected:** `demo_site`'s condenser bank spans x 800–860 and its intake sits at x 1090 with no
  building between, so **N-8, N-19, N-23 and N-27 do not depend on this.**
- **Possibly affected:** **N-28**'s six-layout classification. Directions blocked by a building would
  register near-zero rise and be classified "unambiguous safe". That may inflate the
  unambiguous-direction counts (18–22 of 24) and it is flagged there.

## Verdict

**FAIL as pre-registered** (V3), with the failure diagnosed to the measurement operator rather than the
solver, and a genuine modelling defect surfaced in V4.

**What can now be said, and it is new:**

> *"The diffusion operator reproduces the exact analytic Gaussian-plume solution to 0.00 % at three
> grid resolutions, and heat is conserved to 0.00 % at every downstream station. Grid refinement
> converges to within 0.002 °C once the intake averaging operator is made resolution-independent.
> Separately, verification found that buildings are implemented as heat sinks rather than no-flow
> walls, which biases any blocked direction low — that is unfixed and stated."*

That is a verification claim, independent of any measurement, and it is the question an NVIDIA judge is
most likely to ask. It also found two real defects that calibration would never have revealed.

---

# N-30 — grounding the solver in published physics instead of invented constants

**Why.** N-19's own docstring described the diffusivity as *"INVENTED — no basis at all"*, and every
other constant was then tuned around it. That is backwards. This entry replaces the invention with a
published parameterisation, states what the published source does and does not cover, and quantifies
the mismatch rather than hiding it.

## The published physics

Standard Gaussian-plume dispersion uses empirical horizontal dispersion coefficients as a function of
downwind distance, tabulated by Pasquill stability class (A very unstable → F stable). For continuous
plumes, with x and σ_y in metres:

| class | σ_y | stability |
|---|---|---|
| A | 0.493 x^0.88 | very unstable |
| B | 0.337 x^0.88 | unstable |
| C | 0.195 x^0.90 | slightly unstable |
| D | 0.128 x^0.90 | neutral |
| E | 0.091 x^0.91 | slightly stable |
| F | 0.067 x^0.90 | stable |

**Sourcing, stated at its true strength.** These values were read from a Pasquill-Gifford model
document (Table 3, "Equations and data for Pasquill-Gifford Dispersion Coefficients") and the class A
and class D rows were independently confirmed by a separate search result. The table is standard
textbook material (Crowl & Louvar, *Chemical Process Safety*, reproducing Martin 1976). **The primary
text was not opened**, so the confidence is "cross-checked in two secondary sources", not "verified
against the primary". Say it that way.

## The link that makes D derivable rather than invented

N-29 verified — exactly, 0.00 % error at three grid resolutions — that our solver obeys

```
sigma_y^2 = 2 D x / u        i.e.   sigma_y  proportional to  x^0.5
```

Setting that equal to the published curve at a chosen distance gives **D = u · σ_y(x)² / (2x)**. For our
geometry (condenser bank edge x = 860 m, intake x = 1090 m → **separation 230 m**, u = 6 m/s):

| class | σ_y(230 m) | **implied D** | worst-dir p99 |
|---|---|---|---|
| A | 59.04 m | 45.47 | 0.2702 °C |
| B | 40.36 m | 21.25 | 0.3681 °C |
| **C** | 26.04 m | **8.84** | 0.4490 °C |
| D | 17.09 m | 3.81 | 0.4879 °C |
| E | 12.83 m | 2.15 | 0.5013 °C |
| F | 8.95 m | 1.04 | 0.5097 °C |

**The value we have been using, D = 8.0 m²/s, corresponds to Pasquill class C (slightly unstable)** — a
defensible hot-afternoon condition. It landing in the plausible range was **luck, not derivation**. It
now has a source.

## A real problem with N-19's sweep, and its resolution

N-19 swept D over **4–16 m²/s**, an invented range, reported a span of **0.088 °C**, and called
diffusivity *"the LEAST influential stub"*.

- Over the full published range **A–F (1.04–45.47)** the span is **0.2395 °C — 2.7× larger**. So the
  sweep understated this constant's influence.
- **But stability class is not a free parameter.** It is determined by wind speed and solar radiation
  via the standard Pasquill classification. For a hot afternoon at 5–6 m/s that gives **class C or D**,
  and the span over C–D is **0.0389 °C** — *smaller* than N-19 reported.

**So the "least influential" conclusion survives and is now better supported**, because the range is
sourced and conditioned on the actual weather rather than guessed. Both numbers should be quoted: the
unconditional range (0.24 °C) and the weather-conditioned one (0.039 °C).

## The functional-form gap, quantified rather than hidden

Constant eddy diffusivity gives σ_y ∝ x^0.5. The published curves give σ_y ∝ x^0.88–0.91, i.e. nearly
linear. **These are different shapes, so one constant D can match at exactly one distance.** Matching
class D at 230 m:

| x | published σ_y | our model | error |
|---|---|---|---|
| 50 m | 4.33 | 7.97 | **+84 %** |
| 100 m | 8.08 | 11.27 | +40 % |
| **230 m** | 17.09 | 17.09 | **0 %** |
| 500 m | 34.38 | 25.20 | −27 % |
| 1000 m | 64.15 | 35.64 | −44 % |
| 2000 m | 119.71 | 50.40 | −58 % |

**This is a known limitation of Fickian (constant-diffusivity) models at short range** — real
atmospheric turbulence contains eddies of many sizes, so relative dispersion grows faster than the
constant-diffusivity assumption allows. Our model is therefore **locally valid around the matched
separation** and progressively wrong away from it. Since real separations are 150–600 m, the model
should be matched per site rather than once globally.

## What this changes in the design

**D stops being a constant and becomes a derived quantity.** Per hour: wind speed and solar radiation
→ Pasquill class → published σ_y(x) at that site's separation → D. Wind speed comes from METAR (we
established FortyGuard serves no wind); solar irradiance comes from `env_params`, which is already
verified working. Nothing invented, one citable table.

⚠ **The classification table itself was extracted with some ambiguity** (one row of the wind-speed ×
insolation grid did not parse cleanly). **Read the exact cell values from the source before coding
them** — do not use my extraction.

## The gaps that remain, and cannot be closed with what we have

| gap | why it cannot be closed now |
|---|---|
| **The solver is 2-D** — horizontal only, no vertical dimension | Real dispersion has a vertical spread σ_z that determines whether the plume passes *above* an intake. Our `downwash_fraction` closure is a crude stand-in for that entire dimension, fitted to power-station data. Fixing it means a 3-D solver |
| **Urban vs rural coefficients** | The table above is the standard (rural) set. Urban coefficients differ, and Data Center Alley is suburban/industrial. Using the rural set is a stated choice, not a verified one |
| **Buildings are heat sinks, not walls** (N-29 V4) | Absorbs 99.7 % of a plume that crosses a building. Real, unfixed, biases blocked directions low |
| **No data-centre measurement anywhere** | All field data is power-station ACCs. Closed only by a site sensor |
| **Primary sources not opened** | Coefficients cross-checked in two secondary sources only |

**This is the honest position: the equation is verified exactly, the dispersion constant now comes from
a published table rather than from nothing, the functional-form mismatch is quantified, and the five
gaps above are named rather than papered over.**

---

# N-31 / N-32 — does FortyGuard's field already contain a wind-blown plume?

**Why this mattered.** Our physics *adds* a plume. If FortyGuard's field already contained one, we would
be **double-counting** and would have to subtract theirs. This is a correctness check on the whole
chain, not a tuning exercise, and it had never been run.

## Method — N-31, zero new API calls

25 fields already paid for: one 2 × 2 km AOI at 100 m, five dates × five two-hour windows, exact times
known. Wind from **KIAD (Dulles) hourly ASOS** via the Iowa State Environmental Mesonet — free, public,
reported in `America/New_York`, vector-averaged over each window.

**Power check first:** wind spanned **178° across 5 distinct 45° sectors**. Had it not, a null would
have been meaningless and must not have been reported.

## 🐛 Two bugs in my own test, both caught before reporting

**1. The directional test measured integer rounding.** Converting a 200 m lag to whole cells makes the
*actual* separation vary from **141 m** (45°, offsets 1,1) to **224 m** (15°, offsets 2,1). Shorter
separation ⇒ smaller temperature difference ⇒ that angle wins regardless of physics. It returned
**exactly 30° for all 25 fields** — the signature of an artifact, not a measurement.

**2. Worse — `to_grid` was broken, and this one is a finding about FortyGuard.** The tile lattice is
**rotated ~1.55° from north**: stepping one tile east also moves **+2.7 m north**, so no two tiles in a
row share a latitude. Inferring the lattice from distinct lat/lon values produced a **397 × 397 array
holding 397 values with 2.8 m "cells"**.

**What survived:** the SVD and the pairwise shape correlations are **value-matched** — they compare like
position with like position and never use neighbours — so they were unaffected. Only the directional
test needed real geometry, and it is now **skipped with an explicit message** rather than printing a
number. `to_grid` raises if its reconstruction gives non-square cells.

## The finding

**One fixed spatial template explains 99.9971 % of the spatial variance** across all 25 fields — five
dates, five hours. Residual **0.0011 °C** against an original **0.212 °C**. Several pairs correlate to
**exactly ±1.000000**, including pairs from *different dates*, and the amplitude changes sign (−8.23 to
+0.93), so the pattern inverts exactly between some consecutive windows.

So 397 tiles carry **one pattern, one amplitude, one offset** — two degrees of freedom, not 397.

**But it did not hold at 8 km / 60 m:** shape correlations **+0.786** and **−0.244** on two independent
AOIs, affine fits leaving **62 %** and **97 %** unexplained.

**And every 2 km field we held was g100 while every large one was g60 — area and granularity perfectly
confounded.** Reporting without separating them would have repeated the "generalise from one sample"
error that already cost two retracted claims.

## N-32 — the confound resolved, 6 paid calls, fully crossed at identical times

Same date (2026-07-28), same two windows (12:00–14:00, 16:00–18:00), same centre, `tcm`,
`filter_type 2`. Two cells were already held from N-12c.

| AOI | granularity | tiles | shape r between windows | affine residual, % of sd | |
|---|---|---|---|---|---|
| 2 km | 100 | 397 | **+0.999995** | **0.31 %** | SINGLE TEMPLATE |
| 2 km | **60** | 1,120 | **+0.999995** | **0.31 %** | SINGLE TEMPLATE |
| 8 km | 100 | 6,445 | +0.599696 | 80.0 % | structured |
| 8 km | **60** | 17,862 | +0.601686 | 79.9 % | structured |

**Two clean conclusions:**

1. **It follows AREA, not granularity.** One template at 2 km at *both* granularities; structured at
   8 km at *both*.
2. **Granularity does not change information content.** At 2 km, g60 returns **2.8× more tiles** than
   g100 and the statistic is **identical to six decimal places**. At 8 km, 17,862 vs 6,445 tiles moves
   the correlation by **0.002**.

*Not* a claim that 60 m is fake — the separation-decay check found no upsampling discontinuity. This is
about independent structure, not smoothness.

## What this licenses

✅ **Our plume is ADDITIVE, not double-counted.** The field carries no independent structure within
2 km, and a condenser plume is a few hundred metres. It cannot be in there. **This was the question,
and it is answered.**

❌ **Not licensed:** *"FortyGuard ignores wind."* Their material describes the model as conditioned on
*"atmospheric, surface, and terrain conditions"*. We tested only what is **observable in the output**.

## Bonus — an open question resolved into a HIGH finding

Chasing the wind claim, I dumped every `env_params` field: **36 fields, not one matching
wind/gust/direction/speed.** The feature request is airtight.

And `metadata.timezone` **exists** — open question §2.1 said it was absent because we had looked at
`locations[].timezone`. It reports **`GMT-5` / `offset_hours: -5` on 2026-07-28 and 2026-08-08**, both
inside Eastern daylight saving, when the location is on **EDT = −04:00**. Timestamps are emitted as
`2026-07-28T15:00:00-05:00`. **So a client that parses the offset correctly lands an hour late, while
one that ignores it gets the right answer** — the worst arrangement for a careful client. Promoted to
findings §1.8 (HIGH), with the honest caveat that we cannot yet tell whether the *data* is shifted or
only the *label*, plus the RH cross-correlation test that would settle it.

## Written to the handover document

- **§1.8** DST not applied in `env_params` — HIGH, promoted from open question §2.1
- **§3.2** Spatial information content set by area not granularity — characterisation, may be intended
- **§3.3** Tile lattice rotated 1.55° — LOW
- **§6** Feature request: expose wind speed and direction — built on four checkable facts, with an
  explicit statement of what we are *not* claiming
