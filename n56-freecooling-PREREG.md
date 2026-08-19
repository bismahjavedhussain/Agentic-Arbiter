# N-56 — FREE-COOLING HOURS vs A REACTIVE ON-SITE ROOFTOP SENSOR

**Pre-registration + amendment log. Code: `testing/test_n56_freecooling.py`. Results:
`testing/results/n56_freecooling.json`. Zero API calls, GPU, 43,763 real hours.**

**Supersedes N-51, whose ≈150 h/yr figure is WITHDRAWN.**

---

## 1. Why N-51 had to be redone

N-51 modelled the incumbent as reading **a weather station some kilometres away**, carrying a 0.40 °C
station-to-site divergence (N-49b). `claims-and-defences.md` §1.15 then established by full-text search
that this is **verified false**: data centres use **on-site rooftop weather stations** (Vantage and GoDaddy
named; Orion units wired to BMS/HVAC). With an on-site sensor that divergence largely vanishes — and it
was a large part of N-51's margin.

**What is verified about the incumbent, and it is the whole basis of this test:** it monitors outside air
temperature, dew point and humidity. **Wind speed, wind direction and solar radiation are entirely
absent.** In the 27-page authoritative LBNL thermal-guidelines document, *"outdoor"*, *"outside air"* and
*"forecast"* **do not appear at all**.

So the incumbent is a **reactive on-site rooftop sensor**: ambient now, at its own location, nothing else.
Three candidate advantages remain, and each is measured rather than asserted — **anticipation**,
**recirculation awareness**, **wind**.

---

## 2. Pre-registered conditions (written before the first run)

| | Condition |
|---|---|
**Q1** | **Equal safety or the comparison is VOID.** Both policies calibrate a one-sided conformal buffer to 90 % on the TRAIN half, scored on HELD-OUT. Each policy's exceedance rate among its own declared-safe hours must fall in **10 % ± 2 pp**. |
**Q2** | **The N = 0 floor.** At zero notice the agent's only edge is recirculation awareness. Report the gain with n, SE, 95 % CI. **This is the floor of any claim.** |
**Q3** | **The notice curve.** Report gain for every N ∈ {0,1,2,3,4,6} h. The "3 h notice" figure is **unsourced**, so no single N may be quoted alone. |
**Q4** | **The bias test.** With FortyGuard's measured day-varying level bias applied, does the agent still satisfy Q1? **If not, the gain is conditional on level anchoring and the unanchored result must be reported as a FAILURE, not omitted.** |
**Q5** | **The incumbent is a range, not a strawman.** Sensor error swept {0.1, 0.3, 0.5} °C; its buffer TUNED by the same conformal procedure. Print the fitted buffer. |
**Q6** | **Anti-degeneracy.** Print both fitted buffers. If the advantage equals the incumbent's buffer minus a constant, the gain is a threshold artefact. |

**Design choices made to avoid known traps:** the agent gets **forecast** wind, not observed —
direction error N(0, σ) with σ swept over the **measured 47–72°** (N-40) — because handing it the realised
bearing would be the oracle leak that inverted N-50. Geometry is the **committed** AWS IAD116/IAD117 pair
(60.3 m gap, 2,600 m² bank), not `demo_site()`. KIAD stands in for site ambient **for both policies
equally**, so no spatial term advantages either side — that is the correction this test exists to make.

---

## 3. ⚠ AMENDMENT 2026-08-18 — two errors in my own test, both found after the first run

### ERROR 1 — an oracle leak, the same family as gotcha #17

The agent's forecast was `amb_fut + N(0, 0.15)` **at every notice period**. But 0.15 °C is FortyGuard's
residual sd on *observed* peak temperature, not an N-hour-ahead forecast error. **Measured persistence
error sd at KIAD is 1.41 / 2.38 / 3.27 / 4.07 / 5.42 °C at 1 / 2 / 3 / 4 / 6 h.** So the agent was handed a
6-hour forecast **36× better than persistence, free.** Its fitted buffer stayed flat at ~0.21 °C while the
incumbent's grew to 7.76 °C, and it "gained" **+2,439 h/yr at N = 6**.

**That figure is withdrawn. It measured the leak, not the agent.**

**Fix**, and the only defensible framing since FortyGuard's H-hour skill at this site is **unmeasured**:
`forecast_sd(N) = (1 − skill) × persistence_sd(N)` with `persistence_sd` **measured** from the same
43,763 hours and **skill swept over {0.00, 0.25, 0.50, 0.75, 0.90}**. `skill = 0` means no better than
persistence, i.e. **no anticipation advantage at all.** The headline becomes the **break-even skill**.

### ERROR 2 — Q1 was mis-specified and unsatisfiable

Q1 asked for the exceedance rate **among declared-safe hours** to sit at 10 % ± 2 pp. But a one-sided
conformal bound guarantees `P(intake ≤ pred + buffer) ≥ 90 %` **marginally over all hours**, not
conditionally on the declared subset. Among declared hours the true intake is typically far below the
limit, so the observed rate was **0.000–0.034 for BOTH policies** and all 132 first-run configurations
came out VOID. **That is a defect in the condition, not a finding.**

**Q1 is recorded FAILED AS WRITTEN.** The correct check, stated in the amendment:

> **Q1b — MARGINAL HELD-OUT COVERAGE.** For both policies the fraction of held-out hours with
> `intake ≤ pred + buffer` must lie within **90 % ± 2 pp** — the same quantity and tolerance N-26 uses.

**This repair affects both policies identically and favours neither**, which is why it is a repair and not
a moved goalpost. Q2–Q6 are unchanged and their verdicts stand.

---

## 4. Results

**Q1b — the real equal-safety check: PASSED, 612 of 612 configurations.**
Coverage: incumbent **0.898–0.909**, agent **0.893–0.907**. Both bounds hold at nominal, so the
declared-hour comparison is at equal safety.

**Q6 — anti-degeneracy: PASSED.** The incumbent's buffer is dominated by **persistence error**
(1.77 → 7.76 °C as notice grows), not by anything we chose; the agent's is 0.19–0.72 °C when anchored.
The gain is not a constant offset — it varies with notice, skill and limit.

**Q5 — the incumbent is not a strawman.** At N = 3, skill 0.50: gain **+753 / +769 / +792 h/yr** for
sensor error 0.1 / 0.3 / 0.5 °C, with the incumbent's fitted buffer barely moving (4.41 / 4.37 / 4.41 °C).
**The result is insensitive to how good we assume their sensor is**, because persistence error dominates.

### Q2 — THE FLOOR, and the most defensible number in this test

**At N = 0 (no forecast involved at all), anchored: +67 free-cooling hours per year.**
Paired per-day **+0.1827 h, SE 0.0196, 95 % CI [+0.1443, +0.2211], n = 914 days — SIGNIFICANT.**

**This is recirculation awareness alone.** It needs no forecast skill, so it survives regardless of what
FortyGuard's H-hour skill turns out to be.

### Q3 — the notice curve (limit 24 °C, sensor 0.3 °C, anchored, σ_dir 72°)

| Notice | persistence sd | skill 0.00 | 0.25 | 0.50 | 0.75 | 0.90 | break-even |
|---|---|---|---|---|---|---|---|
0 h | 0.00 | **+67** | +67 | +67 | +67 | +67 | none needed |
1 h | 1.41 | **−28** | +126 | +300 | +436 | +514 | **skill ≥ 0.25** |
2 h | 2.38 | +52 | +270 | +537 | +809 | +954 | ≥ 0.00 |
3 h | 3.27 | +71 | +407 | **+769** | +1,114 | +1,325 | ≥ 0.00 |
4 h | 4.07 | +243 | +557 | +1,008 | +1,415 | +1,707 | ≥ 0.00 |
6 h | 5.42 | +348 | +801 | +1,320 | +1,895 | +2,261 | ≥ 0.00 |

All cells pass Q1b. Every cell in the table has a paired per-day CI in the results JSON.

**At 1 h notice with no forecast skill the agent LOSES 28 h/yr** (CI [−0.153, −0.0003] h/day). Recorded,
not hidden — it is the honest lower corner of the surface.

**Limit sensitivity**, N = 3, skill 0.50: **+624 / +699 / +769 / +740 h/yr** at 18 / 21 / 24 / 27 °C.

### Q4 — the bias test: the level bias does NOT break safety, it costs HOURS

Unanchored agent coverage **0.898–0.908** — inside the band in **612 of 612**. So Q1b holds either way.
But the bias inflates the agent's buffer from **0.19 → 2.30 °C**, and that is expensive:

| Notice | skill | anchored | unanchored | **anchoring is worth** |
|---|---|---|---|---|
0 h | — | **+67** | **−645** | **712 h/yr** |
1 h | 0.50 | +300 | −238 | 538 |
3 h | 0.50 | +769 | +407 | 362 |
6 h | 0.90 | +2,261 | +1,705 | 556 |

**At zero notice the unanchored agent LOSES 645 h/yr** — the bias alone destroys the entire recirculation
advantage. **So the customer's sensor is a REQUIRED input, not an optional examiner**, exactly as §8e/§2b
concluded from the live coverage failure. Anchoring is worth **100–712 h/yr**.

---

## 5. ⚠ What this test does NOT establish

1. **🔴 Q4's pass does not transfer to reality.** The bias here is drawn i.i.d. per day across ~1,825 days
   with train and test **exchangeable by construction**, so a conformal buffer can absorb it. §2b's real
   failure (65.6 % coverage) was on **4 days** with calibration that was **not** exchangeable. **This
   simulation cannot reproduce that failure and must not be cited as evidence against it.** It shows only
   that a *stationary, calibratable* level bias costs hours rather than safety.
2. **FortyGuard's actual H-hour forecast skill at this site is unmeasured.** Every cell except N = 0 is
   conditional on it. **This is the single measurement that would settle the headline**, and it costs
   2 paid calls per site per day.
3. **At skill 0 and N = 1–2 the gain is small** (−28 to +52 h/yr) — essentially the recirculation floor
   plus noise. Do not quote those cells as a benefit.
4. **No humidity or enthalpy gate.** Real economizers also limit on wet-bulb, which reduces hours for
   **both** policies.
5. **KIAD stands in for the site's ambient time series.** Applied identically to both policies, so it
   advantages neither, but it is not the site's own record.
6. **No dollars, no kWh.** The °C → kWh conversion could not be sourced. Chiller-hours only.
7. **Rise magnitudes remain below the station quantum.** Mean rise 0.0584 °C, p90 0.1522 °C, max
   0.3503 °C, against ASOS's **0.556 °C** grid (gotcha #24).

---

## 6. ✅ THE MISSING NUMBER IS NOW MEASURED — DIAG-57, 2026-08-18, zero API calls

§5 item 2 said FortyGuard's H-hour forecast skill was unmeasured and that it was *"the single measurement
that would settle the headline"*. **It did not need new calls.** On 2026-08-12 the project had already paid
for forecasts of ONE target window issued at **five different leads** (1.49 / 3.49 / 5.49 / 7.49 / 9.41 h)
plus the realised outcome — 17,862 tiles each, all on disk. `testing/diag57_forecastskill.py` compares
them. **Free.**

### The error is a LEVEL OFFSET, and it is FLAT in lead

| Lead h | mean error | per-tile sd | after removing the offset |
|---|---|---|---|
1.49 | **+1.1950** | 0.1080 | 0.1080 |
3.49 | **+1.2468** | 0.1254 | 0.1254 |
5.49 | **+1.0979** | 0.0947 | 0.0947 |
7.49 | **+1.3271** | 0.1069 | 0.1069 |
9.41 | **+1.0907** | 0.1166 | 0.1166 |

**The whole map is uniformly ~1.2 °C too warm, and that barely changes over a 7.9 h span of lead** —
least-squares slope **−0.0063 °C per hour of lead**, total range **0.2364 °C**. Per-tile scatter is only
**0.09–0.13 °C**, i.e. two orders of magnitude smaller than the offset.

**This is the same defect §8e diagnosed on the coverage failure, now confirmed across lead as well as
across space.** It also explains why §8e found lead-shortening useless: **shortening the lead cannot help,
because the error does not come from the lead.**

**Anchoring to a local sensor removes 90.8 % of the error magnitude** — RMSE 1.10–1.33 °C → 0.09–0.13 °C.

### Skill against a reactive sensor's persistence guess

`skill = 1 − forecast_error / persistence_error`. 0 = no better than assuming nothing changes; 1 = perfect.

| Lead h | FG RMSE | persistence sd | **skill** | skill if anchored |
|---|---|---|---|---|
1.49 | 1.1999 | 1.4052 | **0.146** | 0.923 |
3.49 | 1.2531 | 3.2714 | **0.617** | 0.962 |
5.49 | 1.1020 | 4.7882 | **0.770** | 0.980 |
7.49 | 1.3314 | 5.9593 | **0.777** | 0.982 |
9.41 | 1.0969 | 6.7706 | **0.838** | 0.983 |

**The forecast is nearly useless at 1.5 h and strong from 3 h out.** That is the right shape for this
problem: persistence is good over short gaps and hopeless over long ones, and a plant needs *long* notice.

### What that means for §4's table — read the cells at the MEASURED skill

The measured RMSE matches N-56's error model to within 0.01 °C at every lead, so the measured skill is
directly the column to read:

| Notice | measured skill | **gain, forecast as measured** | anchored (lower bound) |
|---|---|---|---|
1 h | 0.146 | **+62 h/yr** | +514 |
3 h | 0.617 | **+930 h/yr** | +1,325 |
6 h | 0.770 | **+1,944 h/yr** | +2,261 |

*Anchored figures are LOWER bounds: measured anchored skill is 0.92–0.98, above the 0.90 top of the swept
grid, so the true anchored gain is higher than shown.*

**So the forecast is the LARGER half of the benefit, not a dropped feature: ≈67 h/yr from recirculation
physics alone, ≈930 h/yr once the forecast is used at 3 hours' notice.**

### ⚠ What DIAG-57 does NOT establish

1. **n = 1 DAY.** Five leads, one target window. The *shape* across lead is well measured (17,862 tiles per
   lead, and the offset dwarfs the scatter), but **the day-to-day spread of the offset cannot be estimated
   from one day.** §8e measured that separately from N-26's four pairs: day-mean offsets **−0.84, −0.81,
   +0.15, −3.71 °C**. That spread is the live risk, and it is why coverage came in at 65.6 %.
2. **The 17,862 tiles are not independent** — within-day spatial sd is 0.06–0.29 °C, so effective n for the
   LEVEL is close to 1. No confidence interval is placed on the level from tile count; that would be fake
   precision.
3. **🔴 The "anchored" column assumes the offset is KNOWN at decision time.** Flatness in lead is
   encouraging — it means an offset measured against a concurrent forecast should still apply N hours
   out — **but real-time anchoring has not itself been tested, and it is not the same experiment.** Until
   it is, treat the anchored column as an upper bound on what anchoring could deliver, and quote the
   **measured-skill column** as the defensible case.
4. Skill is computed against **persistence at KIAD**, the same baseline N-56 uses, so the two are
   consistent — but persistence is a floor, not the best possible reactive rule.

---

## 7. What may be quoted

> **≈67 additional free-cooling hours per year from recirculation physics alone, no forecast required** —
> equal measured safety (90 % ± 2 pp coverage, both policies), 95 % CI [+0.144, +0.221] h/day, n = 914 days.
> **This is the FLOOR: it holds whatever the forecast turns out to be worth.**
>
> **≈930 h/yr at 3 hours' notice using FortyGuard's forecast AS MEASURED** (skill 0.617 at 3.5 h lead,
> DIAG-57 §6). **≈1,944 h/yr at 6 hours' notice** (skill 0.770). ⚠ The skill measurement is **one day**.
>
> **The forecast is the larger half of the benefit** — but it is **nearly useless below ~2 h notice**
> (skill 0.146 at 1.5 h), because persistence is already good over short gaps.
>
> **Anchoring the forecast level to the customer's sensor removes 90.8 % of its error.** Unanchored, the
> zero-notice case **loses 645 h/yr**. Real-time anchoring is **not yet tested** as its own experiment.

**Do not quote:** N-51's ≈150 h/yr · the first-run +2,439 h/yr · any single notice period alone · any
cell at skill 0 with N ≤ 2 as a benefit.
