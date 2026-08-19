# N-46 — PRE-REGISTRATION: does a modelled recirculation margin beat a worst-case fixed margin?

**Written 2026-08-16, BEFORE any result is computed. Conditions below may not be edited after the
first run — amendments go in the dated log at the bottom.**

**Cost: zero API credits.** Existing GPU physics table + free NOAA ASOS. No key use.

---

## 1. The claim being tested

INTAKE's value proposition, stated as a falsifiable claim for the first time:

> An operator who cannot see the recirculation at their own air intake has only one safe option: hold
> a margin sized for the **worst case over all wind directions**, permanently. An agent that models
> the recirculation per hour can hold a **smaller** margin on most hours **at the same safety level**.

**The quantity in dispute is margin in °C.** If the saving is small, the product is weak and we learn
it now instead of in front of judges.

**Glossary:**

| Term | Plain meaning |
|---|---|
| **Margin** | Extra cooling headroom held because you are not sure how hot the incoming air will be. Insurance, paid for continuously. |
| **Recirculation** | Your neighbour's hot exhaust reaching your air intake. |
| **Worst case** | The largest recirculation the site can ever produce, over every wind direction. |
| **Coverage** | How often the promise "it will not exceed this" actually held. Target 90%. |
| **p90** | The value 90% of the ensemble's 100 answers fall below. |
| **Held-out** | Days used only for scoring, never for tuning. |
| **Paired SE** | Standard error of the per-day difference between two policies — the right test when both see the same days. |

---

## 2. Why this comparison isolates our contribution, and the earlier framings did not

**Ambient is handled identically by both policies, so it cancels.** Both know the ambient forecast;
neither has any advantage there. The only thing that differs is whether the recirculation increment is
**modelled** or **assumed worst-case**. So whatever this test measures is attributable to the solver
plus FortyGuard's wind/field inputs, and to nothing else.

This is what N-45 showed the earlier framings could not do. The commitment decision was dominated by
ambient (swings of ±1.5–4 °C against a recirculation term of 0.25–0.40 °C), so the physics was a
10–25% correction to a weather decision. **Here the physics is the entire signal by construction.**

**Explicitly NOT claimed:** that this is the operator's *total* margin. It is the recirculation
component only. The ambient component is real, larger, and not ours.

---

## 3. The two policies

Both are calibrated on TRAIN days and scored on HELD-OUT days. Neither sees held-out data while tuning.

**The adversary — a tuned fixed margin.** The **smallest constant margin** that achieves ≥90% coverage
on the training days. This is not a strawman: it is exactly what a competent engineer does with the
same data and no model. It is the incumbent, and it must be beaten on its own terms.

**The agent — a modelled per-hour margin.** From the ensemble p90 for today's forecast wind direction,
plus a conformal correction fitted on training residuals so that it, too, achieves ≥90% coverage on
training days. **The agent gets no tuned parameters beyond the one conformal correction the adversary
also gets** — one calibration constant each, so the comparison is fair.

**Truth per day:** the realised rise at the *true* wind direction, drawn from the calibrated GPU
direction table. **Observation per day:** the ensemble p90 at the *forecast* direction, where forecast
error is real KIAD persistence error at the appropriate lead.

---

## 4. PRE-REGISTERED CONDITIONS — fixed before any number is seen

- **P1 — the saving must be real.** The agent's mean margin must be **lower** than the tuned fixed
  margin by **≥ 2 paired standard errors** on held-out days.

- **P2 — no safety may be sold to buy it.** The agent's achieved held-out coverage must be **≥ the
  fixed policy's achieved held-out coverage**, and both must be **≥ 88%** (sampling slack around the
  90% target; if either falls below 88% its calibration failed and the comparison is void).

- **P3 — the anti-threshold guard.** The agent's margin must genuinely vary: **sd > 0.01 °C** across
  held-out days, **and** it must be strictly below the fixed margin on **≥ 50%** of held-out days. If
  the agent's margin is effectively constant it *is* the fixed rule wearing a costume, and **N-46 FAILS
  even if P1 and P2 pass.**

- **P4 — the honesty condition on units.** The result is reported in **°C of margin, with n, SE and a
  95% CI**. The conversion from °C to kilowatt-hours to dollars is **NOT sourced** — the chiller
  efficiency figure it needs could not be found in any primary document on disk (see
  `n45-costmodel-PREREG.md` §2). **No energy or money figure derived from this test may be quoted
  until that conversion is sourced and cited.** Reporting a °C saving as a dollar saving would be
  exactly the kind of unsourced claim this project retracts.

**N-46 PASSES only if P1 ∧ P2 ∧ P3 hold, and P4 is honoured in how it is reported.**

### The pre-registered negative

If the agent cannot beat a worst-case constant at equal safety, then **modelling the recirculation buys
no margin**, and INTAKE's value proposition is not margin reduction. That would be a decisive result
about the product — and it must be reported as plainly as a pass.

### ⚠ Honest prediction, recorded before running

From N-23's measured direction sweep the p90 rise is **0.0000 °C at 180°, 0.047 at 225°, 0.369 at 250°,
0.396 at 265°, 0.376 at 285°, 0.049 at 315°** — near zero across most of the compass and sharply peaked
over a narrow arc. A worst-case constant must cover the peak (~0.40 °C) on every hour of the year.
**I therefore expect the agent to win P1 comfortably, because the honest answer is near zero most of
the time.** The real risks are P2 and P3, not P1:

- **P2 risk:** the peak is narrow, so a forecast direction error of 50–70° can put the true direction
  inside the plume when the forecast said it was outside. That is a coverage failure, and it is the
  reason the conformal correction exists. **If the correction has to be large, it eats the saving** —
  and that, not the mean, is the real test of whether this works.
- **P3 risk:** if the conformal correction dominates, the agent's margin becomes nearly constant and
  it collapses into the fixed rule.

**So the number that decides this test is not the mean saving — it is how big the conformal correction
has to be to survive a 50–70° direction error.** Recording that here so the result cannot be
reinterpreted afterwards.

### What N-46 cannot establish — stated before running

- **One site layout** (`solver.demo_site`). N-28 showed layout sensitivity; generalising needs the
  layout sweep repeated.
- **Persistence wind error, KIAD, one station.** Persistence is the honest *lower* bound on forecast
  skill, so the agent's real-world performance should be **better** than measured here — but the
  absolute numbers are not calibrated to FortyGuard's product.
- **Simulated days, real physics.** The rise distribution is the calibrated solver on the GPU; the days
  are sampled from real wind and real ambient. This tests the MARGIN MECHANISM, not FortyGuard's
  forecast skill.
- **The recirculation margin only.** Not the operator's total margin (see §2).
- **Nothing about money.** See P4.

---

## 5. Amendments log

### 2026-08-16 — Design note, decided before the run: wind speed held at 3.0 m/s

`build_direction_table()` perturbs speed per member around `WIND_SPEED_MS = 3.0`. The measured KIAD
median at the target hour is **8.0 kt = 4.12 m/s**. The primary run keeps **3.0 m/s** for
comparability with N-23/N-44, and because plume concentration falls with wind speed, so 3.0 is the
**conservative (higher-rise)** choice. Sensitivity at 4.12 m/s not yet run.

### 2026-08-16 — RESULT: **FAIL.** P1 = −2.19σ. Recorded as measured.

| Condition | Verdict | Value |
|---|---|---|
| **P1** margin lower by ≥2 paired SE | **FAIL** | **−0.0076 ± 0.0035 °C = −2.19σ** (agent margin is *larger*) |
| P2 no safety sold | PASS | agent **90.0%** vs fixed **89.9%** coverage, held-out |
| P3 margin genuinely varies | PASS | sd **0.2200 °C**, below fixed on **55.3%** of days |

Full output in `results/n46_margin.json`. Headline lead 9 h, 4,000 train / 4,000 held-out days,
directions sampled from **449 real KIAD target-hour days**.

**Mechanism, and it is not what §4's prediction guessed.** The prediction was that a large conformal
correction would eat the saving. **The correction was negligible: q = +0.0007 °C.** The actual cause:

- The plume is **narrow and the rise field is severely zero-inflated** — `median p90 across all 72
  direction bins = 0.0000 °C`, with the peak at **270° = 0.7887 °C**. More than half the compass
  produces literally no recirculation.
- So the *unconditional* 90th percentile of realised rise is only **0.2144 °C**, and that is all the
  fixed margin has to cover. It is a much stronger adversary than expected.
- Meanwhile **direction forecast error of 47.7° (1 h) to 72.7° (12 h) smears the narrow plume across
  most of the compass.** Whenever the forecast direction lands within ~70° of the plume arc, the
  ensemble picks up hot members and p90 jumps. The 150–360° sectors hold ~70% of observed days, so the
  agent's p90 is elevated on most days: **mean agent margin 0.2220 °C against a real-frequency-weighted
  mean p90 of only 0.0662 °C.**
- The agent is below the constant on 55.3% of days but *far* above it on the rest, so it loses on the
  mean. **This is the same dilution mechanism N-40 and N-44 identified, acting on an upper quantile:
  a mixture with a hot tail has a high p90 even when most members are zero.**

**A second, separate fragility worth recording:** the tuned fixed margin swings from **0.1642 to
0.2209 °C** across leads purely from resampling, because zero-inflation puts the 90th percentile in a
sparse tail. Any single estimate of it is unstable, and the by-lead σ values (+3.94 at lead 2, −15.85
at lead 4) are dominated by that noise rather than by lead.

**⚠ The caveat that stops this being final, and it was pre-registered in §4:** the direction error used
here is **KIAD persistence, the honest LOWER bound on forecast skill.** A real forecast is
substantially better. The result is therefore decisive **for persistence-quality direction forecasts**
and does **not** settle the case for NWP-quality ones. The follow-up that resolves it is a sensitivity
sweep over direction-error magnitude, which converts a failure into a stated engineering requirement.

**What this result does NOT damage:** both policies hit **89.9%/90.0% held-out coverage against a 90%
target**. The conformal machinery — the product's actual promise — is working correctly out of sample.
What failed is the claim that modelling beats a constant, not the claim that the bound is honest.

### 2026-08-16 — N-46b: the direction-error requirement. **Margin thesis VIABLE, conditionally.**

`test_n46b_dirsweep.py`, result `results/n46b_dirsweep.json`. Bands were fixed before the run
(≥25° viable / 10–25° demanding / <10° or no crossover = dead). 20,000 train + 20,000 held-out days.

**Crossover = 40° direction-error sd → "VIABLE on a modest requirement."**

| Direction error sd | Fixed margin | Agent margin | Saved | σ | Saved as % of fixed |
|---|---|---|---|---|---|
| 0° (perfect) | 0.2116 | 0.0656 | **+0.1460** | +124.2 | **69.0%** |
| 10° | 0.2116 | 0.1072 | +0.1045 | +70.1 | 49.4% |
| 20° | 0.2116 | 0.1587 | +0.0529 | +31.3 | 25.0% |
| 25° | 0.2116 | 0.1777 | +0.0339 | +19.8 | 16.0% |
| 30° | 0.2116 | 0.1925 | +0.0191 | +11.2 | 9.0% |
| **40°** | 0.2116 | 0.2074 | **+0.0043** | **+2.55** | 2.0% |
| 50° | 0.2116 | 0.2106 | +0.0010 | +0.63 | 0.5% |
| 68.37° (as measured) | 0.2116 | 0.2128 | −0.0012 | −0.75 | — |

**Why this sweep is trustworthy:**

- **Port verified.** The vectorised implementation reproduces N-46's loop implementation: margins
  0.2071/0.2152 vs 0.2144/0.2220, and the *saving* agrees to 0.0005 °C (−0.0081 vs −0.0076). σ differs
  (−5.28 vs −2.19) only because n went from 4k to 20k, and −2.19 × √5 = −4.9, as expected.
- **Paired design.** The same seed is used for every row, so true directions and realised truths are
  *identical* across rows and only the error magnitude changes — which is why the tuned fixed margin is
  exactly 0.2116 on every line. This isolates the effect of forecast quality and removes the
  resampling instability that made N-46's by-lead table unreadable.
- **The saving is understated, not flattered.** Coverage *rises* as error shrinks (90.1% → 93.6%),
  meaning the agent over-delivers safety at low error. It dominates the constant on **both** axes and
  could shrink its margin further by targeting exactly 90%.

**⚠ Two things this does NOT establish, and both must be closed before any claim is made:**

1. **Whether any real forecast meets the 40° requirement.** Measured persistence is 68.37° at 9 h, so a
   real forecast must be ≈**1.7× better than persistence**. Plausible for NWP, **not sourced here**.
   Note also that the requirement lands on the **wind** forecast, which comes from public NWS/HRRR data
   in our loop, *not* from FortyGuard — FortyGuard supplies the ambient boundary condition. Be precise
   about that division when pitching.
2. **Whether the absolute magnitude is worth money.** The saving is **0.05–0.15 °C** at plausible
   forecast quality. In *relative* terms that is 25–49% of the margin; in absolute terms it is tenths
   of a degree. **Per P4, no energy or money figure may be quoted** — the conversion is still unsourced.
   The obvious lever on absolute size is **site layout**: this is one deliberately modest geometry, and
   N-28 already showed layout sensitivity. A tighter site would have a larger recirculation term.

---

### 2026-08-16 — N-48: does the saving scale with facility size? **NO — IT INVERTS.** Thesis closed.

`test_n48_geometry_scale.py` → `results/n48_geometry_scale.json`. Conditions fixed before running. Only
the site geometry changed — conformal construction, tuned adversary, real KIAD wind (449 days) and leads
held identical — so any difference is attributable to facility size.

**Geometry:** `demo_site` 60 × 120 m condenser bank vs **L6 `layout_wide_far` 160 × 200 m — 4.4× the
source area.** Measured max rise **0.8549 → 3.2493 °C (3.80×)**; p90 peak 0.7887 → 2.9295 °C, both at 270°.

| Direction error sd | demo_site saved | **L6 saved** | demo_site σ | **L6 σ** |
|---|---|---|---|---|
| 0° | +0.1437 | **+0.2555** | +120.2 | +62.8 |
| 10° | +0.1017 | **+0.1046** | +67.6 | +19.4 |
| 15° | +0.0746 | **+0.0117** | +46.0 | +2.00 |
| 25° | +0.0316 | **−0.1276** | +18.5 | **−20.7** |
| 68.37° (measured) | −0.0044 | **−0.1976** | −2.9 | **−35.5** |

| Condition | Verdict |
|---|---|
| **P1** saving at 25° ≥ 0.1017 °C | ❌ **FAIL — −0.1276 °C, the wrong sign** |
| P3 no safety sold | ✅ PASS (agent 93.4 % vs fixed 89.9 %) |
| **P4** crossover ≥ 40° | ❌ **FAIL — L6 15°, demo_site 30°** |
| P2 materiality ≥ 0.50 °C | ❌ not reached |

**The mechanism, and it is coherent rather than a bug.** A stronger plume amplifies the *penalty* for
direction error: when the forecast bearing is wrong the ensemble sprays across the compass and picks up
plume members, and at L6 those members are ~3.8× hotter, so the agent's p90 inflates faster than the
constant it must beat. Measured — **the fixed margin scales only 2.1× (0.2108 → 0.4426) for a 3.80× rise**,
because the realised distribution is still zero on most bearings, while **the agent's margin at 25° scales
~3.2× (0.1791 → 0.5702).** The gap flips sign.

> ## 🔴 CONCLUSION: the margin thesis is closed at ALL facility sizes.
> It is not merely small — **it inverts at exactly the facilities where the physics matters most**, and
> the wind-forecast requirement *tightens* from ~30° to ~15° against a measured 68.37°. **A bigger
> facility needs a better forecast.** P4 was written in advance to detect precisely this, and it did.

*Two corrections this forces on earlier text:* **(a)** demo_site's crossover reads **30°** here against
40° in N-46b — different seed and sample size. **Quote it as ~30–40°, seed-sensitive, never as a sharp
40°.** **(b)** The note above suggesting *"a tighter site would have a larger recirculation term"* was
right about the magnitude and **wrong about the consequence** — a larger term makes the agent worse, not
better.

L6's magnitude is ~3.5× outside the range the physics was validated on (a 0.923 K signal, RMS 0.126 K),
so the scaling is a **model extrapolation**, labelled as one.
