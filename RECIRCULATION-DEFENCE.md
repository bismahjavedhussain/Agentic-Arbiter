# Defending the recirculation physics — why it is in the product, and what it buys

**Written 2026-08-23. Every number below is read from an emitted artefact, not from memory.**
Sources: `demo/backtest.json`, `demo/chicago_backtest.json`, `demo/dulles_backtest.json` (the B-rows
and the sensitivity sweep), `data/geometry/*_refusal_rank.json` and `*_selected_site.json` (the
screening funnels), `demo/trace.json` (the rise tables).

---

## 0. The one-line answer

**The rise is small. The uncertainty it removes is not.** Modelling recirculation explicitly cuts the
agent's mean safety margin roughly in half at every site, and it is the *margin* — not the rise —
that decides how many hours you win. Remove the physics and all three sites lose hours, gain
breaches, and **fall below the 90 % coverage they promise.**

---

## 1. Where the citations live

**`AGENTIC-ARBITER/PLAN.md` § 12** is the evidence register for the whole project — every load-bearing
claim with a source and a link, marked 📘 (primary document, opened and read), 🔎 (measured study) or
📗 (background).

**Recirculation specifically is § 12.6**, *"Why recirculation was considered at all — and what the
physics is built on"*:

| What it supports | Source |
|---|---|
| That exhaust-to-intake recirculation is **a recognised design concern with published dilution equations** — including the explicit note that neglecting buoyant plume rise gives *"an inherent safety factor"* | **ASHRAE Handbook — HVAC Applications, Ch. 46**, *Building Air Intake and Exhaust Design*, pp. 46.7–46.10. Held locally as `i-p_a19_ch46.pdf` |
| The **magnitude calibration** — six instrumented air-cooled condensers, ~40,000 digitised (wind, recirculation) pairs | Maulbetsch & DiFilippo, *Effect of Wind on the Performance of Air-Cooled Condensers*, California Energy Commission **CEC-500-2013-065** + Appendix B. Held locally in `validation-data/` |
| Dispersion coefficients | Pasquill-Gifford Table 3; EPA **ISC3 User's Guide**, EPA-454/B-95-003b (urban vs rural sets) |
| **Field validation** — 67 experiments, *"the most complete available for the analysis of surface layer dispersion"*, at 150–600 m, which is our range | **Project Prairie Grass (1956)**, via Harmo classic datasets + OSF mirror |
| Wind-tunnel data for a box-on-ground plume — exactly our geometry | University of Hamburg **EWTL/CEDVAL** |

Related sections you will also want in the same conversation: **§ 12.2** (LBNL's instrumented study of
why operators avoid free cooling — the commercial thesis), **§ 12.4** (why humidity and air quality
gate it), and **§ 12.9** (retracted claims, kept visible).

---

## 2. The standpoint — why a 0.36 °C effect is worth a solver

The instinct is that 0.36 °C is negligible against a 24 °C limit. That instinct is wrong, and the
reason is worth stating carefully because it is the strongest technical argument in the project.

**The agent does not act on a temperature. It acts on a bound:**

```
bound = forecast + rise + margin
```

`margin` is a conformal quantile — the 90th percentile of the agent's **own past errors**. So the
question is not "how big is the rise?" but **"what does the rise do to the error distribution?"**

Two cases, and the arithmetic is exact:

| | the agent's residual | what the margin must cover |
|---|---|---|
| **Rise modelled** | `(T + rise) − (fc + rise)` = **`T − fc`** — the plume **cancels** | forecast error only |
| **Rise ignored** | `(T + rise) − fc` = forecast error **+ the entire plume** | forecast error *and* a worst-case plume, on every single hour |

Adding the actual rise is *exact*. Making the quantile absorb it charges **every hour the worst case**,
including the 80 % of hours when the wind is blowing the exhaust away and the true rise is ~0.

**So dropping the physics does not buy a cheaper bound. It buys a wider one.** Measured:

| Site | mean margin, rise modelled | mean margin, rise ignored | inflation |
|---|---|---|---|
| Ashburn | **0.1931 °C** | 0.3363 °C | **+74 %** |
| Chicago | **0.1919 °C** | 0.3261 °C | **+70 %** |
| Dulles | **0.1931 °C** | 0.3777 °C | **+96 %** |

That is the whole defence in one table. The rise is small; the *ignorance* about it is not.

---

## 3. The before / after, per site — the proof you asked for

`backtest.py` runs the identical five-year configuration twice, changing exactly one flag —
`include_rise: true` vs `false` — over **913 held-out days** at each site. Everything else is held:
notice 0, skill 1.0, limit 24 °C, switch budget 24, dwell 1 h, dew-point gate off, sensor error
0.3 °C. That isolates the plume term and nothing else.

### Ashburn (KIAD, 60.3 m facade gap)

| | **rise modelled** | **rise ignored** | difference |
|---|---|---|---|
| Chiller-hours gained vs incumbent | **+65.6 h/yr** | +42.8 h/yr | **−22.8 h/yr** |
| Raw free-cooling hours | 17,511 | 17,462 | −49 |
| **Breaches** (bound exceeded) | **3** | **11** | **3.7× worse** |
| Breaches per 1,000 free hours | 0.171 | 0.630 | 3.7× worse |
| Mean safety margin | 0.1931 °C | 0.3363 °C | +74 % |
| **Measured coverage** | **0.9025** ✅ | **0.8998** ❌ | falls below the 90 % promise |

### Chicago (KORD, 118.4 m gap)

| | **rise modelled** | **rise ignored** | difference |
|---|---|---|---|
| Chiller-hours gained | **+57.2 h/yr** | +43.2 h/yr | **−14.0 h/yr** |
| **Breaches** | **2** | **8** | **4.0× worse** |
| Mean safety margin | 0.1919 °C | 0.3261 °C | +70 % |
| **Measured coverage** | **0.9005** ✅ | **0.8925** ❌ | below nominal |

### Dulles (KIAD, 137.7 m gap) — **the most affected by the plume term**

| | **rise modelled** | **rise ignored** | difference |
|---|---|---|---|
| Chiller-hours gained | **+71.2 h/yr** | +46.0 h/yr | **−25.2 h/yr** |
| **Breaches** | **5** | **9** | **1.8× worse** |
| Mean safety margin | 0.1931 °C | 0.3777 °C | **+96 %** |
| **Measured coverage** | **0.9025** ✅ | **0.8974** ❌ | below nominal |

### The three sentences to say out loud

1. **Removing the physics costs 14–25 chiller-hours a year at every site.** Not a rounding error —
   that is 20–35 % of the unconstrained headline.
2. **It makes the agent less safe at the same time**, 1.8× to 4× more breaches. This is *not* a
   safety-for-hours trade; the physics buys both.
3. 🔴 **It breaks the product's central promise.** With the plume term the bound covers ≥ 90 % at all
   three sites. Without it, **all three fall below 90 %** — the bound stops meaning what it says.

⚠ **Sign-error warning, stated because we made it.** Until 2026-08-20 this project reported the
opposite conclusion — *"knowing about the plume COSTS +22.8 h/yr"* — from a `%+.1f` printed next to
the word "costs". The line contradicted itself on its face and a confident narrative underneath it
stopped anyone reading the number. Recorded as gotcha #97; `audit.py` now asserts the ORDER of these
rows so an inversion fails a check.

---

## 4. Why our sites look clean — and why that is the physics working, not evidence against it

This is the part a judge will probe, so lead with it rather than waiting to be asked.

**The shipped sites have small recirculation because we screened for it.** The funnels, from
`*_selected_site.json`:

| | Ashburn | Chicago | Dulles | **Total** |
|---|---|---|---|---|
| Building pairs considered | 611 | 2,148 | 53 | **2,812** |
| ❌ Rejected: **closer than the 60 m measurement floor** | 45 | 2 | 12 | **59** |
| ✅ Survived to physics measurement | 141 | 9 | 16 | **166** |
| 🔴 **Of those, pairs refusing EVERY downwind bearing** | 53 | 2 | 3 | **58 (35 %)** |

**Read the last row.** Of 166 real data-centre pairs we solved on real OSM geometry, **58 have a
building sitting on the exhaust-to-intake path** — the agent cannot produce a rise it can stand
behind and says so instead of guessing. **A third of real pairs are not clean.** We ship three that
are, because the screening told us which ones they were.

**And where the geometry is bad, the price is enormous.** The `bank_mode = facing` axis puts the
condenser bank on the short end wall instead of the long facade — the same buildings, equipment moved:

| Site | gain at `facing` | hours refused | of which **genuinely safe** |
|---|---|---|---|
| **Ashburn** | **−3,124.4 h/yr** | 10,779 of 21,912 | **7,142** |
| Chicago | +324.8 h/yr | 0 | 0 |
| Dulles | +401.7 h/yr | 0 | 0 |

**Only Ashburn's geometry is tight enough for the refusal guard to fire** — its 60.3 m gap clears the
floor by 30 cm, the tightest pair in all 166. When it fires it costs **3,124 hours a year**, and
7,142 of the refused hours were genuinely safe. That is the cost of not knowing, priced, on our own
site, and it is on screen in the demo.

---

## 5. Is there a US site "deeply affected" that we should run instead?

**Short answer: no, and the reason is a hard limit of our own instrument, which is worth saying
plainly rather than shopping for a better site.**

**59 pairs across the three metros sit closer than 60 m** — exactly where recirculation would be
largest. We cannot measure any of them, and the reason is geometric, not a choice:

```
MIN_GAP_M = INTAKE_STANDOFF_M + INTAKE_RADIUS_M + BANK_DEPTH_M/2 = 60.0 m
```

The intake is modelled as a **30 m-radius disc**. Below ~60 m of separation that disc physically
overlaps the condenser bank, so **the instrument would be averaging the exhaust it is supposed to be
measuring**. The gate does not reject those pairs because they are uninteresting — it rejects them
because *any* number we produced for them would be an artefact. (This constant was itself wrong once:
it omitted the bank depth and passed a 54.7 m pair, which two GPU builds later `assert_intake_clear()`
refused. Gotcha #65.)

**So the honest position is: the tighter the pair, the larger the recirculation, and the less able we
are to measure it.** Going and finding a tighter US site does not escape that — it walks straight
into it. What it would take is a different measurement operator (a smaller intake disc, or a proper
CFD intake surface), which is a redesign, not a site search.

**There is also a second reason not to go site-shopping**, and it is the more important one for
credibility: **choosing a site because it makes our number look bigger is exactly the
cherry-picking this project's whole method is built to avoid.** Every decision-shaping value in the
agent is swept rather than chosen, for precisely this reason. Selecting a site for a flattering
result would undo that in one move, and a judge who noticed would be right to discount everything
else.

**What we have instead is better:** three sites where the plume term is measured to be worth 14–25
h/yr and 2–4× the breach rate, a 35 % refusal rate across 166 real pairs showing that clean geometry
is the exception rather than the rule, and one site — Ashburn at `facing` — where the cost of not
knowing is priced at −3,124 h/yr.

---

## 6. If you are asked the blunt version

> **"Your recirculation model changes the answer by a third of a degree. Why did you build a GPU
> solver for it?"**

> Because the agent does not act on the temperature, it acts on a bound, and the bound is sized by
> the agent's own past errors. If we do not model the rise, the safety margin has to absorb it as
> if it were random noise — which nearly doubles the margin, from 0.19 °C to 0.33–0.38 °C, and the
> margin is what costs hours. Measured over 913 held-out days at each of three sites: removing the
> physics loses 14 to 25 chiller-hours a year, makes breaches 1.8 to 4 times more frequent, and drops
> measured coverage below the 90 % the bound promises at all three sites.
>
> And the small number is itself a result. We screened 2,812 building pairs, measured 166, and 58 of
> them have a building sitting on the exhaust path — a third of real pairs. Our three ship *because*
> the physics told us they were clean. On the one site tight enough for the geometry to bite, moving
> the condenser bank to the short wall costs 3,124 hours a year. The solver is what tells you which
> site you are standing on.

---

## 7. What is NOT claimed

- **Recirculation is not the headline, and never was.** The headline is the forecast: +405.7 h/yr in
  the shipped configuration comes from having 3 hours of notice, not from the plume. Recirculation
  contributes **+22.8 of the 65.6 h/yr** in the unconstrained comparison, and nearly all of the
  safety. The retracted claim *"+67 h/yr from recirculation alone"* is recorded in `PLAN.md` § 12.9
  and must never be reused.
- **Our plume shape is the outlier, in the unsafe direction.** Against 67 Prairie Grass experiments
  our √x spread measured an exponent of **0.805**, meaning at these distances our plume is too *wide*
  and **under-predicts rise by 5–25 %**. Stated on the demo page.
- **The effect is below the validation floor of the weather record.** KIAD's five-year ASOS series
  resolves 0.5556 °C (whole °F); the worst rise is 0.3550 °C = **0.64 of one grid step**. No claim
  resting on an effect this size can be validated against that record — which is an independent
  reason the project leads with the forecast rather than the physics.
- **21.9 % of hours are calm or have no bearing** and use an all-bearing mean rise. Recirculation is
  physically *worse* in calm air, so this likely **understates** the effect on a fifth of all hours.
