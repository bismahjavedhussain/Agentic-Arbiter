# Claims and defences — what I can say, and how to defend it

**FortyGuard Hackathon'26 · compiled 2026-08-11 · one row per claim**

Every claim below has been tested. For each: the exact number, where it came from, the likely attack,
and the answer. **§2 lists claims that were RETRACTED** — those must never be said aloud, and knowing
why they died is itself a defence, because it shows the testing was real.

**The single most useful habit:** state the limitation before the judge finds it. A claim volunteered
with its own caveat reads as competence. The same claim extracted under questioning reads as
overreach.

---

## 1. Claims I can defend

### 1.1 ✅ Hot exhaust re-enters the air intake, making it warmer than the general outside air

**Say:** *"Cooling equipment breathes air that is measurably warmer than the surrounding
neighbourhood, because its own exhaust and its neighbours' exhaust drift back onto the intake."*

| | |
|---|---|
| **Evidence** | ASHRAE Handbook, Systems & Equipment Ch. 39: *"Recirculation raises the entering wet-bulb temperature"*; *"The possibility of air recirculation should be considered, particularly on multiple-tower installations."* A measured case reached **23 °F (12.8 °C) above ambient** at chiller inlets. CFD studies find **5–50 %** of discharge recirculated. **And measured directly in this project:** six instrumented power-plant condensers show a deck gradient of **0.84–1.04 K** pooled. |
| **Attack** | *"How big is it really?"* |
| **Answer** | *"On the metric the field reports use — the spread across a condenser deck — about 1 K, measured across six instrumented plants. Individual cases reach far higher: one published case measured 23 °F above ambient."* |
| **Never say** | A specific number for a *data centre* intake. All the measured data is from power stations. |

---

### 1.2 🟡 Wind DIRECTION carries more of the signal than wind SPEED — state this CAREFULLY

**This is the claim the product rests on, and the evidence is genuinely mixed. The careful version is
still strong. The loose version will be dismantled.**

**❌ Do NOT say:** *"Measurements show wind direction matters more than wind speed."* Too broad.

**✅ Say:** *"At the one site where the report plots recirculation directly against wind direction,
the swing between compass sectors is 1.60× — larger than the entire wind-speed effect across all six
plants. The report's own text says direction had more influence than speed during one episode. Other
periods show direction shifts with no effect at all — which is exactly what you would expect from a
geometry effect that only bites when the exhaust plume lines up with the intake."*

#### Evidence FOR

| | |
|---|---|
| **Direct measurement** | **Figure 6-90, Wygen plant, 12,290 digitised points.** Mean recirculation by 45° sector: 0.490 K (180–225°) up to 0.786 K (45–90°) — **swing 0.296 K, ratio 1.60×**. The wind-*speed* swing pooled over all six plants is only **0.204 K.** |
| **The report's own words** | *"These figures suggest a stronger influence of wind direction on recirculation than of wind speed."* (Appendix B p. 143) |
| **A dramatic documented case** | *"following a 180° shift in the wind direction from easterly to westerly, the situation completely changes to one of significant recirculation."* |
| **Independent corroboration** | Wind direction is **input #19 of 19** in Google's published production cooling model. |
| **Physics predicts it** | Direction decides *whether* the plume reaches the intake at all — near on/off. Speed only decides *how diluted* it is — gradual. A switch beats a dimmer. |

#### ⚠ Evidence AGAINST — volunteer these before you are asked

| | |
|---|---|
| **Same plant, same day, no effect** | The supporting quote covers a 7–10 p.m. window on 18 July 2005 at Apex. **Earlier that same day**, *"five major shifts from southeast to westerly and back again. The recirculation was not noticeably affected by these shifts."* |
| **Another plant, no effect** | *"Figure 6-41 shows essentially no effect of wind direction"* — though the report explains it: *"since the variation in wind direction is very small, no obvious correlation would be expected."* |
| **And another** | *"Figure 6-44... exhibits no evident correlation of average recirculation with particular wind directions."* |
| **Only ONE direct scatter exists** | Of 50 direction-related figures in Appendix B, **Figure 6-90 is the only recirculation-vs-direction scatter plot.** All the others are time series. So this claim rests on one site, while the speed claim pools six. |

#### The reconciliation — and it makes the product case stronger, not weaker

Direction only matters **when the geometry lines up.** If the wind rotates but the plume never points at
the intake, nothing happens. If it swings through the bad sector, you get a jump. An effect that is
**invisible most of the time and occasionally large** is exactly what near-binary geometry predicts —
and it is exactly the kind of thing worth forecasting.

> **A gradual effect you could simply budget for once. An effect that is nothing on most days and
> significant on a few is precisely what needs a per-day warning.** The mixed evidence is not a
> weakness in the claim; it is the shape of the claim.

**If pressed on the single-site limitation, answer:** *"Correct — one site for the direct scatter,
because it is the only one the report published. Six sites for the speed comparison. We say so, and
the physics gives an independent reason to expect it."*

### 1.2b ✅ The margin widens BY ITSELF when the forecast is geometrically ambiguous — and this is demonstrable live

**Say:** *"The system works out on its own when wind direction matters. We never coded a rule for it."*

| | |
|---|---|
| **Evidence** | Sweeping forecast direction in 5° steps with a 60-member ensemble: spread at the boundary of the plume sector is **27.0× the spread in the safe sectors** (sd 0.2556 vs 0.0095 °C), widest at 285°, most split at 250°. **This got stronger, not weaker, after the 2026-08-12 defect fix (§1.14) — it was 13.6× before.** |
| **Why it matters** | The agent is **never told where the plume points.** It discovers it by pushing today's forecast through the physics 60 times and reading the spread. Same code relaxes on safe days and refuses at the edge. |
| **The bonus finding** | The share of ensemble members in the hot zone **never exceeds 72 %**, even pointing squarely at the plume. The bad sector is ~40° wide; the direction forecast is ±15°. **So there is never a clean "definitely hot" day** — near the bad sector you are always partly on the edge. **A point forecast at this geometry is always ambiguous.** That is the strongest argument in the project for a bound rather than a single number. |
| **Attack** | *"Isn't the uncertainty just padding?"* |
| **Answer** | *"No — it is 27× larger at the geometric edge than in the interior, and it is the thing that stops us relaxing on the one day in ten when a point forecast would have told us we were safe."* |
| **Demo value** | This is the single best thing to show live: put wind direction on a dial, and as it turns the margin flattens to nothing across ~60 % of the compass, then swells through a ~55° band, then collapses again. No slides needed. |

---

### 1.3 ✅ FortyGuard's 60 m field is real, live, and is air temperature

| Property | Measured |
|---|---|
| Tile lattice stability | **17,862/17,862** tiles byte-identical across calls and dates |
| Tracks real weather | Airport station (KIAD) rose 9.6 °C between two dates; field rose 11.13 °C — **ratio 1.16** |
| Genuine 60 m resolution | Mean \|ΔT\| decays smoothly 0.011 → 0.301 °C over 60 → 2000 m, **no jump** indicating upsampling |
| Air, not land surface | Diurnal amplitude **7.8–8.3 °C** (surface temperature would be far larger) |
| Diurnal cycle correct | 21.1 °C at 04:00–06:00 rising to **33.8 °C at 16:00–18:00** for Ashburn in August |

**Attack:** *"Could it be an interpolated climate map?"* → **Answer:** *"No — it moved 11.13 °C when the
nearby airport moved 9.6 °C, and the resolution decay curve has no discontinuity."*

---

### 1.4 ✅ The uncertainty statements are calibrated — verified, not asserted

**Say:** *"When the system says it is 90 % confident, it is right 90 % of the time. We measured that."*

| | |
|---|---|
| **Evidence** | Empirical coverage **90.0 % ± 0.4 pp** against a 90 % nominal target. Forecast error on peak temperature measured on **6,875 matched tiles**: bias +0.349 °C, sd 0.150 °C, \|residual\| q90 **0.495 °C**. |
| **Why it is strong** | Conformal prediction's guarantee is **distribution-free** — it does not assume the physics is right, only that tomorrow's errors resemble the ones it was calibrated on. **A wrong model with an honestly measured error distribution is safe; a right model with an unmeasured one is not.** |
| ⚠ **Volunteer this** | The bound is calibrated on **ambient forecast** errors. It does **not** yet cover the solver's own error, because there is no ground truth for that. The fix is a deployment property: the customer's own intake sensor closes the loop within a fortnight, and the same machinery recalibrates end-to-end. |

---

### 1.5 ✅ The staging decision is genuinely sequential — this is what makes it an agent

**Say:** *"The system decides WHEN to bring reserve cooling online, not just whether. That decision
cannot be written as a threshold."*

| | |
|---|---|
| **Evidence** | Beats the **best tuned fixed-hour rule** — both the hour and the sensitivity margin optimised by exhaustive search — by **+0.356 ± 0.032 cost units/day, 11.2 σ**, on **held-out** days, with **zero tuned parameters** of its own. Fires off its modal hour on **41.3 %** of staging days. **18 of 21** stub variations are significant wins. |
| **The killer illustration** | On the test day the policy says **wait at hours 0–1, act at hours 2–6, then wait again** — because past hour 6 the cooling can no longer arrive before the peak. **No threshold can produce an action set that switches on and then off in time.** |
| **Attack** | *"Isn't this just 'act when it looks bad'?"* |
| **Answer** | *"We built that rule, tuned it exhaustively over every hour and margin, and it loses by 11 standard errors out of sample."* |
| ⚠ **Volunteer this** | It rests on two parameters, and **N-24 has now measured exactly how much room each has** — see §1.11. Peak-hour uncertainty needs **> 0.70 h**; it is 1.49 h, clearing by **+11.2σ**, but on five days. The sharpening rate needs **ρ ≤ 0.772** and is **still unmeasured**. Say both before you are asked, and say that the second one is the load-bearing one. |

---

### 1.6 ✅ NVIDIA is load-bearing, and the honest version is more convincing

**Say:** *"For the very first calculation the GPU is four times slower, because it has to compile the
kernel. For the hundred we actually need, it is 72 times faster."*

| Workload | CPU | GPU | |
|---|---|---|---|
| single solve, **first in the process** | **0.593 s** | 2.594 s | 🔴 GPU **loses** — 2.37 s of it is kernel compile |
| single solve, kernel already compiled | 0.712 s | **0.144 s** | GPU wins 4.9× |
| 100-member ensemble | 63.6 s / 61.8 s | 0.9 s / 0.7 s | ✅ **72.7× and 93.5×**, two runs |
| 20 sites × 100 members | 1,272 s (**21.2 min**) | **13–17 s** | — |

⚠ **Two precision points, because both are the kind of thing a sharp judge catches.**

1. **Quote 72.7×, the lower of two runs.** Same code, same GPU, a week apart: the difference is
   CPU-side timing variance on a laptop. If asked, say *"72.7 and 93.5 on two runs — I quote the lower
   one."* Quoting 93.5 and failing to reproduce it live is far worse.
2. **The single-solve loss is a one-off, not a property of the GPU.** It is the kernel compile, paid
   once per process. Lead with it, because it shows the number was measured — but if you say "the GPU
   is slower at single solves" and someone re-runs it warm, you are wrong by 4.9×.

Correctness proven **before** timing: max \|CPU − GPU\| = **0.000251 °C** over the whole field
(float32 vs float64 rounding over 800 steps). Hardware: RTX 4050 Laptop, sm_89, Warp 1.16.0.

**A bug this re-verification caught, worth telling if asked "what did testing find?".** N-22
recalibrated the downwash exponent to 1.25 in `downwash_fraction()` but left `solve()` defaulting to
the falsified 2.0. N-16 fed the CPU through one and the GPU through the other, so **the very test
asserting CPU/GPU equivalence was comparing two different physics** — source terms differing by up to
**1.84×** at 3 m/s. It passed anyway, because the recorded figure predated the split. Both paths now
read one `CALIBRATED` dictionary and N-16 passes the exponent explicitly to each side. *The lesson:
never let two code paths agree by sharing a default.*

**The argument:** *"A single solve is not the workload. To say '90 % of the time it stays below X' the
physics must run across a spread of conditions — the distribution IS the product. The bound needs
the ensemble; the ensemble needs the GPU."* Remove the GPU and a named stage stops working.

**Bonus line:** *"It also makes the honesty affordable — 1,500 solves for our sensitivity sweep took
9 seconds. At 16 minutes we would not run it routinely, and an unswept assumption is how a wrong
number reaches you."*

---

### 1.7 ✅ The solver's MAGNITUDE is validated against real measurements

**Say:** *"We calibrated the physics against 40,000 measured points from six instrumented plants, and
held three of them back to test it."*

| | |
|---|---|
| **Evidence** | Fitted on three plants, scored on **three never used in the fit**: **RMS 0.126 K on a 0.923 K mean signal = 14 %**. Constants adopted: exponent 1.25, uc 8.0 m/s, exchange_s 47.4 s. |
| **Independent check** | Direction swing, never part of the fit: solver **2.17×** vs measured **1.60×**. |
| ⚠ **Volunteer this** | **The SHAPE is not validated.** Held-out correlation is **+0.082** — essentially zero. The measured wind-speed dependence spans only 0.20 K around a 0.92 K mean, so there is almost no shape to fit. **The magnitude is validated; the wind-speed shape is not resolvable from this data.** The solver also over-predicts direction sensitivity by ~35 %, in the expected direction, because our modelled deck is a bare rectangle while real sites have surroundings that smear the response. |
| **Attack** | *"Power stations aren't data centres."* |
| **Answer** | *"Correct, and we say so. Deck sizes and cell counts differ. What transfers is the physical mechanism and the order of magnitude, not a site-specific number."* |

---

### 1.8 ✅ The benefit: a band, never a point

**Say:** *"Of order one degree — between 0.42 and 1.71 °C across the plausible range of every
unmeasured constant. And the conclusion holds throughout the band."*

| | |
|---|---|
| **Evidence** | Sweeping all eight solver constants on calibrated physics: headline **+0.839 °C**, full range **0.415–1.713 °C**, ratio **4.1×**. |
| **Two reassuring details** | `diffusivity` — the one constant that used to have no basis at all, now derived from the published Pasquill-Gifford curves (§1.14) — remains among the **least** influential. The **most** influential, `bank_w` (span 1.298 °C), is condenser bank width — **a geometry fact you would simply measure for a real client**, so it is not really an unknown in deployment. |
| **What survives** | *"On 7 of 8 wind directions almost all of that margin is dead weight."* This depends on the **direction contrast**, not the absolute level, so it holds across the whole band. |
| **Never say** | Any single figure without the band. |
| ⚠ **If you have seen our earlier figures** | These numbers **roughly doubled on 2026-08-12** after a defect fix, from +0.455 (band 0.219–0.940). The reason is in §1.14 — the old numbers were biased **low** because building interiors were being averaged into the intake temperature. The old band did contain the corrected value, but only near its top edge. **Quote the new band.** |

---

### 1.9 ✅ The commercial gap is real and verified

**Say:** *"Autonomous cooling control is a mature product category with paying customers. Not one of
the twelve products we surveyed looks at the weather."*

| | |
|---|---|
| **The market exists** | **Vigilent** — closed-loop autonomous control, resold as **Schneider EcoStruxure IT Advisor: Cooling Optimize since 2014** and as **Siemens White Space Cooling Optimisation**. **Phaidra** at **Merck West Point** — 7M sq ft, 4 chiller plants, ~60,000 refrigerant tons, autonomous ~84 % of the time, confirmed by TechCrunch. **etalytics** at **Equinix FR6 Frankfurt** — 900 MWh/yr, 240 tCO₂e/yr. **Meta** — RL agent controlling supply-airflow setpoint since 2021, 20 % fan energy. |
| **The gap** | Surveying twelve products for "weather", "forecast", "outdoor", "ambient", "wet bulb": **zero explicit claims.** Every disclosed input is internal — rack sensors, CRAC/CRAH telemetry, chiller loop data, IT load, power draw. Phaidra's leading indicator is explicitly **rack power draw, not weather**. |
| **The best quote you have** | DeepMind's own BCOOLER field trial alternated control policies **daily** so they would *"get to see reasonably consistent weather between the two policies"* — **they treated weather as a confounder to cancel out, not a signal to exploit.** |
| **The reframe** | *"We are not competing with Phaidra or Vigilent. We are the input they do not have."* That makes FortyGuard's CEO a supplier to a market that already pays, rather than a competitor in it. |
| **Prior art — cite it, don't be caught by it** | **EPFL DAD-DPC at Polydome** (arXiv 2412.09238) is the closest work: real building, ~2-month closed loop, split conformal prediction, Tomorrow.io forecasts, 20.5 % savings. It is a **lecture hall, not a data centre**, its conformal bound lumps model error and weather error together rather than bounding the forecast, and it is a university trial, not a product. |

---

### 1.10 ✅ Pricing is known exactly

**4,220 credits per heatmap call** — arithmetic, not inference: the usage endpoint reports Heatmap
Generation at **278,520 credits over 66 calls**. Pricing is **flat** in area, granularity, hour count
and analytic type, so large polygons are effectively free. One call returned **17,862 tiles over
64 km² in 67 s**.

---

### 1.11 ✅ The two open risks are pre-registered experiments, not hand-waving — N-24

**Say:** *"Two quantities decide whether that decision is genuinely agentic, and neither is measured
yet. So before I had the live key, I measured exactly what each one has to clear — and I wrote the
kill condition down first."*

| Quantity | Plain meaning | Must clear | Where it stands |
|---|---|---|---|
| **ρ = σ(3 h lead) ⁄ σ(12 h lead)**, equivalently the exponent **b** | How much sharper is the forecast 3 hours out than 12 hours out? | **b ≥ 0.187** for a 2σ win; break-even **0.129** (ρ ≤ 0.772 / 0.837) | 🔄 **Being measured 2026-08-12 — N-25.** See §1.12 |
| **`peak_sd_h`** | How uncertain is *which hour* the daily peak lands on? | **> 0.70 h** for a 2σ win; break-even **0.395 h** | ✅ **1.49 h → +11.2σ**, but from five days |

**Why this framing is worth more than the numbers.** A risk described as *"unmeasured, might be fatal"*
tells a judge you have not finished. The same risk with a threshold attached tells them you designed an
experiment that can fail. The thresholds were fixed before 18 Aug, so the day-one result cannot be
reinterpreted afterwards.

**The strongest thing in this section — volunteer it.** N-24 asked whether the two risks can cover for
each other: if the peak hour were wildly uncertain, could the rule earn its keep with *no* forecast
sharpening at all? **No.** At ρ = 1.00 the rule loses at every peak-hour uncertainty tested, out to 4 h.

> *"They are not substitutes. If FortyGuard's forecasts turn out not to sharpen as the hour approaches,
> my stopping rule earns nothing over a tuned fixed-hour rule, and I would report that as a null
> result. One measurement on day one decides it, and I know which measurement it is."*

**If pressed on how ρ gets measured:** one target hour, a forecast requested at ~12 h lead, another at
~3 h lead, then the realised value after the hour elapses; ρ is the ratio of the two error spreads.
3 h is chosen because it is the plant's lead time — the moment the decision stops mattering.

**Two honest caveats to have ready.** The benefit **saturates** past ρ ≈ 0.47, so beating the target by
a lot buys nothing extra. And **too much** peak-hour uncertainty hurts — the gain peaks near 2.1 h and
falls beyond it, because a peak that could land anywhere in the horizon leaves no structure to exploit.
Both are the shape you would expect, which is mild evidence the harness is behaving.

| | |
|---|---|
| **Method** | The N-9 adversary, **imported rather than reimplemented** — best fixed-hour rule with hour *and* margin tuned exhaustively on 20,000 training days, scored on 20,000 held-out days, paired per day. 77 sweep points. The stopping rule has **zero** tunable parameters. |
| **Pass conditions, fixed first** | Both gain curves monotone (Spearman > 0.8 — got +0.843 and +0.849); a finite breakeven exists in each; the measured `peak_sd_h` wins by > 2σ. **All three met.** |
| **Never say** | That the sharpening risk is *"probably fine because weather forecasts usually sharpen"*. It is unmeasured for **this** API. |

---

### 1.12 ⭐ The timezone bug — the best answer you have to *"what did your testing actually find?"*

**Tell this story.** It is short, it is technical, it ends with you correcting yourself against your own
interest, and it demonstrates the one thing a judge cannot verify from a demo: that the testing was
real.

> *"We told FortyGuard their forecast path was intermittent — 48 retries recovered nothing. Then I
> checked our own code. The endpoint reads request times in the AOI's local zone. We were running a
> UTC+5 machine against a UTC−4 site. Every forecast request we had ever made was nine hours off. The
> four leads we thought were 4 to 10 hours out were really 13 to 19 — all outside the 12-hour horizon.
> Retrying could never have worked. So I withdrew the complaint, and the horizon turned out to be
> exactly as documented."*

**How it was proved, without spending a credit** — two independent arguments from data already saved:

1. Across five days, the diurnal maximum falls in the **16:00–18:00** requested window and is already
   declining by 18:00. That is a local afternoon curve. Under a UTC reading, 18:00 UTC = 14:00 local —
   essentially the peak — where temperature cannot be falling.
2. Site-local is the **only** convention that explains which windows returned data: 9.25 h and 11.25 h
   succeeded, 13.25 h and 17.25 h returned zero tiles. A UTC reading predicts the 9.25 h case should
   have succeeded. It did not.

**What survives as a genuine FortyGuard defect, and it is now sharper than before:** a request outside
the horizon returns `status: completed` with zero tiles — indistinguishable from an empty area *and*
from a transient failure. Two additions would have prevented the whole episode: **echo the interpreted
window back**, and **name the horizon in an error**. That is the highest-value item in the handover
document, and it is framed as an interface improvement rather than a bug.

**If asked "isn't that embarrassing?"** — *"The opposite. It is the third defect I withdrew after
retesting, along with `persistence` and `heat_index`. I would rather hand their CEO five findings that
all hold than ten where half collapse under scrutiny."*

**Never say** the forecast path is unreliable. You have no evidence of that and one direct
counter-example: a 9.41 h lead returning a full 17,862-tile field.

---

### 1.13 🟡 "You can't validate your solver — so why should I believe it?"

**The hardest question you will get, and the answer has three parts in this order.**

**Part 1 — concede it immediately and precisely.**

> *"You're right that I can't validate it at a data centre. No such measurement exists publicly — all
> the field data on condenser recirculation is from power stations, six instrumented air-cooled
> condensers. I calibrated against those: held-out RMS 0.126 °C on a 0.923 °C signal, fitted on three
> plants and scored on three it never saw. What transfers is the mechanism and the order of magnitude.
> No site-specific number transfers, and I don't claim one."*

**Part 2 — the claim is built not to need the magnitude, and that was tested across geometries.**

| | |
|---|---|
| **Absolute intake rise** | moves **26.6×** (0.179–4.753 °C) across every plausible constant **and** six different site layouts |
| **Releasable fraction** | moves by at most **14 percentage points** over that same range |

> *"So I don't report a temperature. I report the fraction of your existing margin you can release,
> with a 15-point band. You supply the scale, I supply the ratio — and a systematic error in my
> physics largely cancels between numerator and denominator."*

**Part 3 — one sensor closes it, and say so before you're asked.** The conformal bound is calibrated
on FortyGuard's **forecast** residuals, so it covers forecast error and is **blind to solver error**.
One temperature logger at a real condenser intake makes the residual cover the whole chain.

> *"The first thing I'd do at a real site is put one sensor on a condenser intake. Then the bound
> calibrates the whole chain, including my solver, within a week. Until then it's a band and I say so."*

⚠ **Two things I tested and had to withdraw — volunteer them if pressed on rigour.**

1. *"The releasable fraction is robust"* — **false.** Pre-registered spread threshold 0.15; measured
   0.626 on one layout. The blanket version is dead.
2. *"The instability lives at the transition directions"* — **false.** Across six layouts the
   transition/unambiguous ratio was **0.7–1.3**, not the >2 the hypothesis needed; in one layout
   transitions were *more* stable. Withdrawn.

**A distinction to keep straight, because conflating them is a real vulnerability.** N-23's knife-edge
finding is about the **ensemble spread** — uncertainty about *today's outcome* — widening 27.0× at the
sector edge. That **stands**. N-27/N-28 were about sensitivity to **unmeasured constants**. Different
quantities. I linked them once and that was wrong.

**Never say:** *"6 of 8 directions are stable to 6 percentage points."* Those numbers belong to a
single site layout. Across six layouts the unambiguous-direction count ran 18–22 of 24 and the worst
spread was 0.124.

---

### 1.14 ⭐ The heat-sink defect — found, fixed, and every number re-run

**Tell this one if asked "did you find any bugs in your own physics?"** It is the strongest kind of
answer: a defect found by our own verification, quantified, fixed, with every dependent number re-run
and republished *higher* than before.

#### What was wrong

Buildings were implemented by **forcing those grid cells to stay at ambient temperature**. That is a
fixed-temperature boundary, and a cell held at a fixed temperature **absorbs heat without limit**. Real
air flows *around* a building; it is not annihilated by one.

Two separate consequences, and the second is the one that mattered:

| | |
|---|---|
| **Blocked directions** | A 120 × 200 m building placed across an otherwise exactly-conserving plume removed **99.7 %** of the heat, against **100.0 %** conserved in the open domain |
| **The headline itself** | **21 of the 49 cells** in the intake averaging disc lie *inside* the neighbour building. They were pinned to a rise of exactly zero, dragging the reported intake temperature **down by 43 %** |

That second point is worth being blunt about: **we were averaging the inside of a building into an
air-intake temperature.** That is not a modelling choice, it is a bug.

#### What was changed

1. **Intake averaging now uses air cells only.** Building interiors are excluded, and the code raises
   if the whole averaging region is inside a structure.
2. **Obstacles are transparent to the temperature field.** The pinning is gone from **both** the CPU
   and the GPU kernel — checked deliberately, because the last defect we found was exactly a CPU/GPU
   divergence. Conservation re-verified at **100.00 % at every station**, including straight through
   the neighbour building.
3. **A line-of-sight check that refuses to answer.** For any wind direction where a building sits
   between source and intake *and* the intake is downwind, the system reports **"not modelled"**
   instead of a number.

#### Why "transparent" and not something cleverer — this is the part to have ready

> *"The obvious fix is a reflecting wall. But our velocity field is uniform — it doesn't know the
> buildings are there. So heat would advect into the wall and pile up with nowhere to go, and our
> intake sits ten metres upwind of the neighbour's face, so that fake hotspot would land right on it.
> I'd be swapping a number that was too low for one that was too high, and I couldn't tell you which
> was closer. Transparent is wrong in one stated direction instead of catastrophically, and it
> conserves heat exactly."*

**And ASHRAE justifies it for this geometry.** Chapter 46 distinguishes a **visible** intake (direct
line of sight to the source) from a **hidden** one (behind an obstruction), and applies a dilution
correction only to hidden intakes — a conservative factor of **2.0**. Our intake has direct line of
sight, so *no building correction* is the sourced treatment for our case. The line-of-sight check is
what keeps us honest about the cases where it is not.

#### What the re-run did to every number

| | before | after |
|---|---|---|
| N-8 worst-direction baseline | +0.4369 °C | **+0.8045 °C** |
| N-19 headline · band | +0.455 · 0.219–0.940 | **+0.839 · 0.415–1.713** |
| N-23 knife-edge spread ratio | 13.6× | **27.0× — stronger** |
| N-27 held-out unambiguous spread | 0.061 | **0.069 — still passes** |
| N-28 absolute range, 6 layouts | 18× | **26.6×** |
| N-28 releasable-fraction spread | ≤ 0.15 | **≤ 0.142** |

**Every qualitative conclusion is unchanged.** Only the levels moved, and they moved *up*.

#### ⚠ One test now fails its own pre-registered condition — say this plainly

N-8's pass condition required the worst direction to release **≤ 0.05 °C absolute**. It now releases
**0.083 °C**, so the test **FAILS**.

**That is a threshold-specification flaw, not a physics change.** The condition was written in absolute
degrees while the baseline doubled. In *relative* terms the worst direction releases **10.3 %** of the
margin, against **11.2 %** before — essentially identical.

> *"The condition should have been relative from the start. I'm not moving it after the fact, so the
> test is recorded as a fail, and the number that actually matters — the worst direction still releases
> only about a tenth of the margin — is unchanged."*

#### 🔭 What CEDVAL would buy us — the honest forward path

**Transparent obstacles are a stated approximation, not the right answer.** The right answer is a
**mass-consistent (divergence-free) wind field**: zero the velocity inside obstacles, then solve one
Poisson equation for a correction potential so the flow travels *around* buildings instead of through
them. That is the standard diagnostic-wind-model approach (MATHEW/CALMET family, after Sherman 1978).
It is one extra Poisson solve — cheap, and we already have the iterative machinery.

**We have not done it, for one specific reason: we could not validate it.** Adding flow deflection
means adding a new approximation, and swapping a *known* gap for an *unvalidated* one days before
judging is a bad trade.

**CEDVAL is the dataset that closes this.** The University of Hamburg Environmental Wind Tunnel
Laboratory publishes flow *and concentration* measurements around **an isolated rectangular building**
and around **arrays of buildings** — literally our geometry, a box on the ground with a plume near it.
It is free; the files are password-protected and the request has been sent.

> *"Buildings are currently transparent to my temperature field, which is a stated approximation
> justified by ASHRAE's visible-intake case, and I refuse to give a number where a structure blocks
> the path. The proper fix is a mass-consistent wind field so the plume goes around obstacles — one
> Poisson solve. I haven't shipped it because I'd be adding an approximation I can't check, and the
> dataset that would check it is CEDVAL wind-tunnel measurements around an isolated building. That
> request is in. With it, the blocked directions stop being refusals and become numbers."*

**That is the strongest possible shape for a gap:** named, quantified, with the fix identified, the
reason for not shipping it stated, and the exact dataset that would unlock it already requested.

---

### 1.15 ✅ What data centres actually measure today — VERIFIED, and it corrects one of our own framings

**This was checked online rather than assumed, and it forced a retraction.**

#### ❌ What we can no longer say

> ~~*"Remove FortyGuard and you are back to a station reading from miles away."*~~

**False.** Data centres use **on-site weather stations**, not airport data. [Columbia Weather
Systems](https://columbiaweather.com/applications/data-centers/) names **Vantage Data Centers** and
**GoDaddy** using fixed-base Orion stations wired into local HVAC control systems, BMS controllers and
HMI historians. Their own reading is *on the roof*, not miles away. **Never use the distant-station
framing.**

#### ✅ What is verified, and it is much stronger

| Verified fact | Source |
|---|---|
| Outdoor monitoring exists, on site, for **economiser changeover** — *"Direct measurement of local weather conditions allows the data center facility to take advantage of outside air economization"* | Columbia Weather Systems case studies |
| The parameters monitored are **outside air temperature, dew point, relative/absolute humidity** | same |
| **Wind speed and wind direction are entirely absent.** So is solar radiation | same |
| ASHRAE TC 9.9 monitoring guidance is about **IT equipment intake air inside the hall** — three sensors per rack, top/middle/bottom, ±0.5 °C | [LBNL Thermal Guidelines](https://datacenters.lbl.gov/sites/default/files/FINAL%20Thermal%20Guidelines%20and%20Temp%20Measurements%209-15-2020.pdf) |
| In that 27-page authoritative guide, the words **"outdoor", "outside air" and "forecast" do not appear at all** | verified by full-text search |
| Design conditions come from **station-derived climate data** — ASHRAE Weather Data Center, climatic design conditions per Handbook Fundamentals | [ASHRAE Weather Data Center](https://www.ashrae.org/technical-resources/bookstore/weather-data-center) |

#### The three-part answer to *"they already measure this — what do you add?"*

**1. They measure. They do not forecast.** In a 27-page authoritative guide to data-centre temperature
measurement, **"forecast" appears zero times.** A sensor tells you that you are already too hot.

**2. They measure one point. Not what each condenser breathes.** One on-site station, versus the
specific air arriving at a specific condenser intake — which differs from the station reading by
exactly the recirculation our physics computes.

**3. They do not measure wind at all** — and wind direction is the variable our field data says decides
whether recirculation happens (1.60× direction swing vs 1.22× across the whole speed range). **Their
own monitoring omits the governing variable.** So does FortyGuard's API, which is why §6 of the
handover document asks for it.

#### ⚠ And say this plainly, because it is the honest boundary

> *"I am not claiming my prediction of the intake temperature is more accurate than a thermometer at
> the intake. It is not, and it never will be. A sensor is the ground truth — it is my examiner, not my
> competitor. What I add is six hours of warning, coverage of every condenser rather than the one that
> happens to be instrumented, and a bound with a measured success rate. And ASHRAE's own logic supports
> the framing: their guidance says IT equipment 'depends exclusively on the intake air'. I am applying
> that same principle one level further out — to the cooling equipment's intake air."*

**Never say** that data centres do not monitor outdoor conditions. They do, on site, for economiser
control. **Say** that they monitor without wind and without a forecast.

---

### 1.16 🟡 The largest gap now has a SIZE — but it is QUANTIFIED, not FIXED — N-34

**Say:** *"Our solver is 2-D. ASHRAE's dilution equation shows the missing term is the vertical plume
spread, so I know we over-predict. I've now worked out by how much."*

#### ⚠ Be ruthless about this distinction — it is the easiest place to be heard as overclaiming

| | |
|---|---|
| ✅ **The size of the error is known** | factor **0.96–1.80×** at our 230 m geometry, for plausible calibration distances |
| ✅ **The sign is known** | we **over-predict** → conservative → the safe direction for a safety margin |
| ❌ **The model is unchanged** | still 2-D, still over-predicts. **No correction has been applied** |
| ❌ **The gap is not closed** | closing it needs a 3-D solver, which is out of scope |

**Why we deliberately did NOT apply the correction:** it depends on the calibration distance, which we
know only to within a factor of two. Applying an uncertain correction to remove a *conservative* bias
trades a known safe error for an unknown one. **Leaving it is the more defensible choice, and saying so
is part of the claim.**

⚠ **The main weakness in the quantification itself, and volunteer it.** The derivation assumes σ_z grows
with the **same exponent** as σ_y. That comes from ASHRAE's near-field form where both spread linearly.
But in the Pasquill-Gifford tables **σ_z has different exponents from σ_y, and they vary strongly with
stability class** — much steeper for unstable air, flatter for stable. So the estimate holds near-field
and degrades with distance. Doing it properly needs the published σ_z coefficients, **which we have not
obtained.**

> *"The gap is measured, not closed. And the measurement itself leans on σ_z growing like σ_y, which is
> an ASHRAE near-field approximation rather than the full Pasquill treatment. I'd want the published σ_z
> coefficients to tighten it."*

#### The derivation, in one line each

ASHRAE Eq. (22) gives 3-D concentration ∝ `Q/(U σ_y σ_z)`; ours gives 2-D temperature ∝ `Q/(U σ_y)`.
Comparing peak Gaussian values, `θ_2D / θ_3D = √(2π) σ_z / H`, where `H` is the layer depth our 2-D
world implicitly assumes. **The calibration is what set `H`** — fitting `exchange_s` to measured deck
recirculation forced the ratio to 1 at the calibration distance. Therefore:

```
    over-prediction factor  =  σ_z(x_app) / σ_z(x_cal)  =  (x_app / x_cal)^b
```

**Notice what drops out:** ASHRAE's σ_z/σ_y ratio **cancels entirely**. Only the exponent `b`
(0.88–0.91, published) and the two distances matter. So the one borrowed ratio isn't even load-bearing.

#### The numbers

| calibration distance | factor at 230 m | factor at 600 m | corrected headline at 230 m |
|---|---|---|---|
| 60 m *(deliberately pessimistic)* | 3.35 | 7.94 | +0.250 °C |
| 120 m | 1.80 | 4.26 | +0.467 °C |
| **180 m** | **1.25** | 2.96 | **+0.673 °C** |
| 240 m | 0.96 | 2.28 | +0.872 °C |

**The plausible range is 120–240 m**, because the ACC deck we modelled in N-21 is 240 × 120 m and the
hot air travels a good fraction of it. At 60 m the factor is included only as a pessimistic bound.

**Conservative in 81 % of cases**, and bounded — the worst factor anywhere is 7.94, not unbounded.

#### ⚠ It FAILS one pre-registered condition, and the failure is the useful part

I required the corrected headline to stay inside N-19's published band (0.415–1.713 °C). At the
pessimistic 60 m calibration distance it drops to **0.250 °C — below the band.** So the test **fails**.

**What that actually tells us, and it is worth volunteering:**

> *"My published band comes from sweeping the solver's constants. It does not include the uncertainty
> from the 2-D approximation, because that is structural rather than parametric. So my true uncertainty
> is wider than my band. At the physically plausible calibration distances the correction is 0.96–1.80×
> and the corrected value stays inside the band; only at a deliberately pessimistic 60 m does it fall
> out. I state the two separately rather than pretending one contains the other."*

**Third time a pre-registered condition has failed on how I specified it rather than on the substance**
— after N-8's absolute-versus-relative threshold and N-33's all-hours-versus-decision-hours median.
That is a genuine lesson about my own test design, and I would rather report the pattern than hide it.

---

### 1.17 ✅ The dispersion constant is now computed from real weather, hour by hour — N-33

**Say:** *"The diffusivity isn't a constant any more. Wind speed and sky condition give the atmospheric
stability class, the published curve gives the plume width, and that gives the diffusivity. Every hour."*

**And the wind comes from a real, free, public source** — the NOAA ASOS station at Washington Dulles
(KIAD), *inside* our 8 km area, via Iowa State University's Environmental Mesonet archive. FortyGuard
exposes no wind (36 response fields checked), so the architecture is FortyGuard for the temperature
field, ASOS for wind and sky. **The feature request still stands, because a station is one point where
their field is 60 m — but we are not blocked.**

| | |
|---|---|
| **Method** | Solar elevation (NOAA algorithm, **verified against a known value: 74.4° at solar noon on the June solstice at 39.01 °N, expected 74.4°**) → insolation band → reduced for cloud cover → Pasquill class from the published table → published σ_y → `D = u σ_y²/(2x)` |
| **Result over 970 real hours** | class **C 31 %**, E 21 %, D 17 %, B 9 %, F 9 %, B–C 9 % — a sensible mid-Atlantic summer distribution |
| **Implied D** | median **3.79** m²/s, p5–p95 **0.27–11.09**, a **41× spread** |
| **Restricted to decision hours** (11:00–18:00, sun above 20°) | median **7.40** m²/s, p25–p75 **4.55–9.86** |

#### The finding, and why the fixed value survives

**Our fixed D = 8.0 is a poor all-hours average (median 3.79) but almost exactly right for the hours
the agent actually acts in (median 7.40).** Nights are stable — classes E and F, D ≈ 0.3–0.9 — and drag
the all-hours median down. The agent decides about afternoon peak load, which is classes B/C.

⚠ **The test FAILS its pre-registered condition**, which compared against the *all-hours* median and
required within a factor of 2 (got 2.11×). **The condition was specified on the wrong population.** I
am not moving it.

> *"A single diffusivity was never the right design. It's now derived per hour from wind speed and sky
> condition using a published table. The old fixed 8.0 turns out to be within a few per cent of the
> median for the hours that matter — which was luck, and it now has a provenance instead."*

#### ⚠ Two source cells I had to fill in — volunteer these

The published stability table has two defects in the copy we have. **Say them before you are asked:**

1. The **"wind < 2 m/s at night"** cells are **blank**. Standard versions give F. We use F, and it
   affects **206 of 1,169 hours (17.6 %)** — all night hours, none of them decision hours.
2. The **"> 6 m/s / slight insolation"** cell reads **C**, which is *less* stable than the adjacent
   Medium column's D — not physically sensible at high wind. Every standard version gives D. We use D,
   affecting **27 hours**.

**Neither cell touches the decision hours**, which is the population that matters.

---

### 1.18 ✅ Why the decision is an AFTERNOON decision — measured, and it contains a surprise

**This was asserted before it was checked. Checking it changed the reasoning and found something
counter-intuitive worth volunteering.**

#### The measurement

The intake temperature is **ambient + recirculation**, and those two behave completely differently
through the day. Solver run at representative conditions from the N-33 classification, using our own
measured diurnal cycle (21.1 °C at 04:00–06:00, 33.8 °C at 16:00–18:00):

| condition | ambient | recirculation rise | **total intake** |
|---|---|---|---|
| Afternoon, unstable (class B/C) | 30.0 °C | 0.886 °C | **30.89 °C** |
| Afternoon, neutral (class D) | 30.0 °C | 0.933 °C | **30.93 °C** |
| Night, stable (class E) | 21.0 °C | **1.047 °C** | 22.05 °C |
| Night, very stable (class F) | 21.0 °C | 1.018 °C | 22.02 °C |

**Ambient swings 8.8 °C. Recirculation swings 0.16 °C. Ambient dominates by ~55×.**

#### ❌ The wrong reason, and ✅ the right one

**Do NOT say** *"afternoon matters because recirculation is worst then."* **It isn't.**

**Say:** *"The total intake temperature peaks in the afternoon because ambient dominates the diurnal
swing by about fifty-five to one. That is when the plant is stressed, so that is when the staging
decision matters."*

#### 🔬 The surprise — volunteer it, it demonstrates the physics is understood

**Recirculation is about 18 % WORSE at night** (1.05 vs 0.89 °C). Stable night air has a small
diffusivity, so the plume stays narrow and undiluted → *more* returns to the intake. The theory says
rise ∝ 1/√(D·u), and that quantity swings **11×** from afternoon to a very stable night.

**But the measured rise only moves 18 %, not 11×** — because lower wind also reduces the downwash
fraction, so less exhaust stays in the modelled layer. The two effects largely cancel.

⚠ **And do not oversell that cancellation as physics.** It is partly a property of our *fitted* downwash
closure, which is itself the stand-in for the missing vertical dimension (§1.16). *"Recirculation is
robust to stability"* is **not** a claim we have earned.

#### Why this matters for the product

It sharpens what the agent is for. **Peak-load staging is an afternoon problem, decided in the morning.**
If a facility were constrained at night for some other reason, our model says night recirculation is
slightly worse — and that would be a different product with a different decision.

---

### 1.19 ⭐⭐ THE FIRST EXTERNAL VALIDATION — Prairie Grass 1956, 67 field experiments — N-35

**This is the strongest single item in the document, and it is the answer to the question you were
previously unable to answer: "has any of this been checked against real measurements that are not your
own calibration?"**

**Say:** *"I validated the plume physics against Project Prairie Grass — 67 independent field
experiments from 1956, sulphur dioxide released and measured on arcs at 50 to 800 metres. It confirmed
the published dispersion law, and it confirmed that my own model's shape is the outlier."*

#### Why this test cannot be circular — the part that makes it worth something

Our diffusivity `D` is **derived** from the Pasquill-Gifford table (§1.17). So testing whether our `D`
matches that table proves nothing — it agrees by construction.

**What can be tested is the FUNCTIONAL FORM**, and that is not circular:

| | plume width grows as |
|---|---|
| **Ours** (verified exactly in N-29) | **x^0.50** |
| **Published** Pasquill-Gifford | x^0.88 to x^0.91 |
| **MEASURED**, 67 experiments | **x^0.805** |

#### The numbers

| | |
|---|---|
| Source | `PGARCS.txt` + `PGrassTTUU.txt` from harmo.org — **free, no registration** |
| Data | 340 arc records · 68 experiments · arcs at 50/100/200/400/800 m |
| **Median measured exponent** | **0.805** (mean 0.795, sd 0.133, 67 experiments) |
| **Quality of the power-law fit** | **median R² = 0.998** — the power law describes the measurements almost exactly |
| Stability from measured temperature gradient | unstable **0.847** (n=32) · near-neutral **0.724** (n=14) · stable **0.662** (n=21) |

**All three pre-registered conditions passed:** exponent above our 0.5 ✅ · within [0.70, 1.10] of the
published value ✅ · at least 20 experiments ✅.

#### What our square-root shape actually costs — now measured, not inferred

Matched to the measurement at 200 m:

| distance | measured | ours | **our error** |
|---|---|---|---|
| 50 m | 0.328 | 0.500 | **+53 %** |
| 200 m | 1.000 | 1.000 | 0 % |
| 800 m | 3.051 | 2.000 | **−34 %** |

**This is slightly BETTER than we previously claimed.** Working from the published table we had stated
+84 % and −44 %; against real data it is **+53 % and −34 %**, because the measured exponent (0.805) is a
little gentler than the table's 0.90. **We were being pessimistic. Update the figures in
physics-explained.md Part 5 to the measured ones.**

#### ⚠ Two caveats, both volunteered

**1. Our measured 0.805 is a LOWER BOUND.** The quality filter rejects arcs where the plume is wider
than the sampled span, and rejections concentrate at long range — **15 % at 800 m against 1 % at 50 m**.
That removes the widest plumes at the largest distance, which biases the fitted exponent **downward**.
So the true exponent is likely closer to the published 0.88–0.91, and our stated error is if anything
slightly understated at long range.

**2. The exponent depends on stability** — 0.85 unstable, 0.66 stable. So a *single* exponent is not
right either. The published table already knows this; it gives a different `a` and `b` per class.

#### The two bugs this test found in our own code, before any result was trusted

1. **Sampler azimuths wrap through 360°/0°.** A naive mean and variance gave σ_y = **60 m at a 50 m
   arc** — physically impossible. Fixed with a concentration-weighted *circular* mean → 20.04 m.
2. **No truncation filter.** Without it, arcs where the plume exceeds the sampled span silently
   understate σ_y and would have flattered our x^0.5. Now rejected and counted.

#### The one-sentence version

> *"Sixty-seven field experiments say plume width grows as distance to the power 0.805. The published
> table says 0.88 to 0.91 — confirmed. My solver says 0.5 — so my shape is wrong, by +53 % at 50 metres
> and −34 % at 800, which is why the diffusivity is matched per site at the separation that matters.
> That limitation was declared before I measured it; now it has a number from real data."*

**Never say** this validates our absolute magnitude. **It validates the shape of the plume growth law
and quantifies our departure from it.** Magnitude still rests on the power-station calibration.

---

### 1.20 ✅ The coefficients are now authoritative — and one of my own claims was wrong — N-36

**Source** 📘: **EPA-454/B-95-003b**, *User's Guide for the Industrial Source Complex (ISC3) Dispersion
Models, Volume II*, downloaded from the EPA SCRAM archive. 128 pages. Tables 1-1 to 1-4 read directly.
**This is the regulatory source** — it supersedes the course handout we had been using, and it supplies
two things we did not have at all: σ_z, and the urban coefficient set.

#### ✅ Result 1 — our σ_y source was fine

The handout's simple power law versus the EPA regulatory formula
`σ_y = 465.11628 · x · tan(0.017453293[c − d ln x])`:

| | worst disagreement over 100–600 m, classes B/C/D |
|---|---|
| simple power law vs EPA | **5.2 %** |

**Confirmed.** The one source we could not verify against a primary is now verified against the
regulatory standard.

#### ✅ Result 2 — N-34's stated weakness is CLOSED

N-34 had to **assume** σ_z grows with the same exponent as σ_y (~0.90), because we lacked the σ_z
coefficients. I flagged that as the main weakness of the whole vertical quantification. The real values:

| class | σ_z exponent, rural | σ_z exponent, urban |
|---|---|---|
| B | 0.983 | 1.093 |
| C | 0.915 | 1.000 |
| D | 0.870 | 0.968 |

**0.870–0.983 against an assumed 0.90.** The assumption was sound, so **N-34's estimate stands and its
declared weakness is now closed.** (ASHRAE's borrowed σ_z/σ_y = 0.667 also sits inside the measured
spread of 0.542–0.593 rural / 0.869–0.950 urban — reasonable, and no longer needed.)

#### 🔴 Result 3 — I was WRONG, and this one needs saying out loud

**I twice described the urban-versus-rural coefficient choice as "second-order" without measuring it.**
Measured:

| class | σ_y rural | σ_y **urban** | ratio | D rural | D **urban** | ratio |
|---|---|---|---|---|---|---|
| B | 41.05 m | 70.43 m | 1.72× | 21.98 | 64.70 | 2.94× |
| C | 26.86 m | 48.42 m | 1.80× | 9.41 | 30.58 | 3.25× |
| D | 17.70 m | 35.22 m | 1.99× | 4.09 | 16.18 | 3.96× |

Because intake rise ∝ 1/√(D·u), switching to the urban set **reduces the predicted rise by 1.72–1.99×**:

> **headline +0.839 °C (rural) becomes +0.422 to +0.489 °C (urban)**

**That is not second-order. It is a factor of two — comparable to the entire rest of the N-19 band.**
Calling it minor without measuring it was exactly the error this project keeps having to correct.

#### What to say about which set applies

> *"Data Center Alley is neither open grassland nor a dense city core. The rural coefficients give
> 0.84 °C and the urban ones give 0.42–0.49 °C, so the coefficient choice alone is worth a factor of
> two. The urban set was measured in the St. Louis city core, which is denser than Ashburn, so the truth
> sits between. I report the rural figure because it is the more conservative of the two, and I state
> that the urban set would halve it."*

**Both endpoints stay inside the published band (0.415–1.713 °C)** — the urban value at 0.422 sits just
above its floor. So the band survives, but it is now doing more work than it was designed for: it was
built to cover *parameter* uncertainty and is being asked to cover a *coefficient-set* choice too.

**Never say** the urban/rural choice is minor. **Say** it is a factor of two, that rural is the
conservative pick, and that the site is genuinely between the two.

---

## 2. 🔴 RETRACTED — never say these

Each died to a measurement. **Knowing why is a defence:** it demonstrates the testing was real.

| Retracted claim | Killed by |
|---|---|
| *"Engineers pick one number and use it every day of the year"* | **False.** Google DeepMind re-optimises cooling **every 5 minutes** with neural networks controlling chillers and fan speeds — **40 % cooling energy reduction**, in production. An NVIDIA judge would know this instantly. |
| *"Recirculation rises with wind speed, peaking near 9 m/s"* | **Falsified by field data.** Six instrumented ACCs: peak in the **0–5 mph** bin, recirculation nearly flat and slightly *falling*. Our solver built on that claim was **anti-correlated, r = −0.869**. |
| *"+2.048 °C worst direction / +1.132 °C median saving"* | Computed with the falsified wind response. **Void.** |
| *"+1.238 °C recovered by using a bound instead of a guess"* | **Circular** — compared an ensemble's p90 against its own maximum. |
| *"A fixed margin is wrong in BOTH directions"* | Only the over-cooling half survives. The under-protection half was **untestable as built** — the baseline was defined to be sufficient. |
| *"+0.874 / +0.956 °C headline"* | Superseded twice. Calibration halved it to ~0.45; then the 2026-08-12 heat-sink fix (§1.14) roughly doubled it again because building interiors had been averaged into the intake. **Current: N-19 +0.839 °C, N-8 v4 +0.8045 °C. Quote the band 0.415–1.713 °C.** |
| *"+0.455 °C headline / band 0.219–0.940 °C"* | **Superseded 2026-08-12.** Biased **low** — 21 of 49 cells in the intake averaging disc were inside the neighbour building, pinned to zero rise (§1.14). The old band contained the corrected value but only near its top edge. |
| *"The knife-edge spread ratio is 13.6×"* | Superseded — it is **27.0×** after the heat-sink fix. This one got **stronger**. |
| *"Fleet compute allocation is a second agentic decision"* | **Equal split wins.** All four concentration strategies lost; random beat ours. **Rerun on calibrated physics — fails harder, −2.7σ (was −2.0σ).** The null is now a validated finding, not a stale one. |
| *"6 of 8 directions are stable to 6 percentage points"* | **Layout-specific.** Tested out of sample in the *constants* but on **one topology**. Across six layouts the count ran **18–22 of 24** and the worst spread was **0.135**, not 0.061. What survives: absolute moves **26.6×**, releasable fraction moves **≤ 14 points**. |
| *"The instability lives at the transition directions"* | **False.** Across six layouts the transition/unambiguous spread ratio was **0.7–1.3** against a required >2; in one layout transitions were *more* stable. Also conflated with N-23, which measures a different quantity (ensemble spread, not constant-sensitivity) and **still stands**. |
| *"Remove FortyGuard and you are back to a station reading from miles away"* | **WITHDRAWN 2026-08-12 — verified false.** Data centres use **on-site** weather stations (Vantage, GoDaddy named; Orion units wired to BMS/HVAC control). Their reading is on the roof, not miles away. What IS verified and stronger: they monitor outside air temperature, dew point and humidity — **and no wind at all**, and they do not forecast. See §1.15. |
| *"A single fixed diffusivity D = 8.0 m²/s"* | Superseded — **now derived per hour** from wind speed and sky condition via the published Pasquill table (§1.17). Real weather implies a median of 3.79 m²/s over all hours but **7.40 m²/s in decision hours**, so the old fixed value was right for the hours that matter and wrong as an average. |
| *"Afternoon matters because recirculation is worst then"* | **False — measured.** Recirculation is ~18 % **worse at night** (1.05 vs 0.89 °C), because stable air keeps the plume narrow. Afternoon matters because **ambient** dominates the diurnal swing by ~55× (8.8 °C vs 0.16 °C). Right conclusion, wrong reason. See §1.18. |
| *"The 2-D gap is fixed"* | **Never say this.** It is **quantified** (factor 0.96–1.80× at 230 m) and **conservative**, but the model is unchanged and no correction has been applied. See §1.16. |
| *"Urban vs rural dispersion coefficients are second-order"* | **WRONG — measured and retracted.** Switching to the urban (McElroy-Pooler) set **halves the headline**: +0.839 → +0.422–0.489 °C, a factor of **1.72–1.99×**. Comparable to the entire rest of the N-19 band. I said this twice without measuring it. See §1.20. |
| *"Spatial resolution is the value proposition"* | The learned per-site offset is worth **+0.036 °C** — negligible. |
| *"Data centres warm their neighbourhood measurably"* | **Two well-powered nulls:** difference-in-differences **+0.016 °C** against a published 0.7–0.9 °C, rotation placebo **p = 0.42**. |
| *"FortyGuard's `persistence` analytic is broken"* | **Withdrawn.** Over a month it gives 162.36 vs `exceedance` 9.42 — identical on **0 of 84** tiles. Our original test window (one contiguous afternoon) could not discriminate. |
| *"`heatmap` and `env_params` disagree by ~9 °C"* | **Withdrawn — our error.** We read `locations[].temperature`, which echoes the caller's own input. `env_params` returns no dry-bulb temperature at all. |
| *"peak_sd_h = 8.59 h"* | Void — derived from `time_of_measure`, which we then proved broken. |
| *"FortyGuard's forecast path is intermittent — 48 retries recovered nothing"* | **WITHDRAWN 2026-08-12 — it was OUR bug, and this is the one to tell if asked what testing found.** The endpoint reads `start_time` in the **AOI's local zone**; our harness built windows from a UTC+5 machine clock for a UTC−4 site. A silent **9-hour** error meant N-18's four "leads" of 4/6/8/10 h were really **13/15/17/19 h — every one outside the horizon**, so retrying could never have worked. The 12 h horizon is now **CONFIRMED**: 9.25 h and 11.25 h return data, 13.25 h and 17.25 h return zero tiles, and a **9.41 h lead returned 17,862 tiles**. |

---

## 3. The three sentences to open with

> **1.** *"Data centres over-cool because they cannot see the air arriving at their equipment, so they
> keep a permanent safety margin. A better thermometer does not shrink a margin — a measured track
> record does."*
>
> **2.** *"We predict what each cooling unit will breathe, attach a bound that is right 90 % of the
> time — verified at 90.0 % ± 0.4 pp — and decide **when** to bring reserve cooling online."*
>
> **3.** *"The part we validated against 40,000 real measurements is the part the product rests on:
> **which way the wind blows matters 1.4× more than how hard it blows.**"*

## 4. If asked "what is weakest?"

Answer it straight — this question is a test of candour, not of the project:

> *"Three things. The forecast-sharpening rate is unmeasured and our stopping rule depends on it.
> Our peak-hour spread rests on one unusual day out of five. And we have no measurements from an
> actual data centre — all our validation data is from power stations, so the mechanism and the
> order of magnitude transfer, but no site-specific number does."*
