# INTAKE — verification checks

**Companion to [intake-agent-plan.md](intake-agent-plan.md).**

**Purpose:** list *only what is still unknown* for this specific design. Thirteen data dependencies are
already verified and are **not** re-tested here — §1 says which, so nothing gets paid for twice.

**Existing protocol:** [fortyguard-day1-data-checks.md](fortyguard-day1-data-checks.md) holds 114 checks
from the earlier work. This file adds **GROUP N** (ten checks) and nothing else. No existing ID is renamed.

**Tags:** **[M]** measured · **[H]** from the account's usage history · **[L]** literature · **[S]** stub ·
**FREE** = no credits, computable on data already on disk.

---

# §1 — What we do NOT need to re-test

These are settled. Cite them; don't spend on them.

| Question | Answer | From |
|---|---|---|
| Are tiles in the same place between calls and dates? | **6,875/6,875 and 17,862/17,862 identical** | [M] |
| Does the field track real weather, or is it a climatology? | KIAD +9.6 °C → FortyGuard +11.13 °C, **ratio 1.16** | [M] |
| Is 60 m resolution real or upsampled? | Smooth monotonic decay, no jump at 500 m. **Real** | [M] |
| What is the spatial noise floor? | **≈0.09 °C at 500 m** | [M] |
| How much spatial contrast is there? | 1.3–1.5 °C across 64 km²; **sd doubles on hot days** (0.24→0.42) | [M] |
| Does the spatial pattern persist day to day? | **~73 %** | [M] |
| Can one call cover a site cluster? | **17,862 tiles, 64 km², granularity 60, 67 s** | [M] |
| Is it air or surface temperature? | Diurnal amplitude 7.8–8.3 °C → **air** | [M] |
| What is the forecast horizon? | Rolling **now + 12 h**; `env_params` serves future times too | [M] |
| Does the same request give prediction *then* outcome? | Yes. Real residual: mean +0.349, sd 0.150 | [M] |
| What does a call cost? | Heatmap **4,220** cr, flat — independent of area, granularity, hours, mode | [H] |
| Does `env_params` return wet-bulb, solar, AQI? | Yes — **15 parameters** + `elevation` + `solar_irradiance` | [M] |
| Does `filter_type=4` work? | Yes — one call = per-tile **monthly** min/max | [M] |
| Does FortyGuard's field contain a facility thermal signature? | **No.** Two independent nulls: DiD **+0.016 °C** vs a published 0.7–0.9 °C, placebo p = 0.42; and no distance decay | [M] |

**Defects already found — code around them, don't re-discover them** [M]: beyond-horizon returns
`completed` with **zero tiles and empty stats** · `persistence` mode returns byte-identical values to
`exceedance` (broken) · `heat_index_celsius` near-constant and unusable · `cloud_cover_octas` is a
**percentage** · timezone label reads `GMT-5` in July *and* August · heatmap has **no metadata block** ·
heatmap runs **~3.5 °C above `env_params`** as a near-constant offset — **never blend them** · **2019
history fails**.

---

# §2 — GROUP N: the new checks

Four need API calls (N-1…N-4). **Six are free and two of those could force a design change — run them
first.**

## N-1 (B-CODE) — ⚑ Does `env_params` vary spatially? — **2 calls**

**Why it matters.** The plan uses `env_params` for wet-bulb, solar and air quality **per site**. Every
`env_params` call we have ever made was at **one point**. If the endpoint returns the same regional values
regardless of coordinates, then per-site anchoring is an illusion.

**Do:** `env_params` at two points **~5 km apart** inside the target cluster, same timestamp, same
`analysis` list. Compare `wet_bulb_temperature_celsius`, `relative_humidity_percent`,
`solar_irradiance.clear_sky.ghi`, `air_quality_o3:idx`, `air_quality_pm2p5:idx`, `elevation`.

**Pass:** values differ by more than rounding, and in a physically sensible direction (`elevation` must
differ — it is a real terrain lookup, so it is the control that proves the coordinates were honoured).

**Fail:** identical values → these parameters are regional.
**Workaround, and the design already anticipates it:** anchor humidity/solar regionally and derive the
**local** quantity from FortyGuard's **60 m temperature field**, which we know *does* vary. The physics
solver is unaffected — it only needs ambient temperature plus wind as boundary conditions.
**Cost of the workaround:** the generator-window layer weakens (it needs local ozone); the core intake
product does not.

## N-2 (B-CLAIM) — Is the air-quality data a forecast or a nowcast? — **1 call**

**Do:** `env_params` at one point for a **future** hour, and the same point for a **past** hour. Compare
the AQI fields and check whether the future values differ from the current ones in a plausible diurnal way
(ozone should peak mid-afternoon).

**Pass:** future AQI values differ plausibly → the generator-window layer can act ahead of time.
**Fail:** future AQI mirrors the present → nowcast only. **Workaround:** forecast the ozone-formation
*potential* from FortyGuard's temperature forecast + solar + regional ozone persistence, and state that it
is a derived index rather than a forecast concentration.

## N-3 (B-DATA) — How far back does history reach? — **3 calls**

**Why it matters.** The **predictive-maintenance output** (cumulative thermal exposure per site) needs
multiple years. **2019 fails** [M]; the real floor is unknown.

**Do:** bisect — `filter_type=1`, one hour, small polygon, at **2025-07-15**, **2023-07-15**, **2021-07-15**.
**Record:** which succeed, which return `Failed`, and how long each takes before failing (2019 hung 6–7.5
minutes) [M].
**Pass:** ≥3 years available → cumulative exposure is meaningful.
**Fail (only ~1 year):** the maintenance output becomes a single-season exposure index. **State the scope
limit; do not extrapolate.**

## N-4 (NICE) — Does `exceedance` work on a historical range? — **1 call**

**Do:** `analytic_type: exceedance`, `direction: above`, `threshold` = a site's design ambient, over a
**past** month via `filter_type=4`.
**Pass:** returns hours-above per tile → cumulative exposure costs one call per month.
**Fail:** compute client-side by counting from `tcm` fields. Same output, more calls. **Not blocking.**

---

## N-5 (B-CODE) — ⚑⚑ **FREE** — Does the learned per-site offset actually beat the regional forecast?

**This is the core commercial claim, and it can be settled today at zero cost.**

The pitch is: *each site has a persistent thermal offset we can learn, and applying it beats a regional
forecast.* We measured ~73 % persistence [M], but never the **predictive improvement in °C** — which is the
number that belongs in the pitch.

**Data already on disk:** two 17,862-tile fields over the identical 8 × 8 km polygon —
`dec_1_DC_dayA.json` (2026-06-23) and `dec_2_DC_dayB.json` (2026-07-28).

**Do:**
1. For every tile, compute its **offset** on day A: `offset_i = T_i(A) − mean(T(A))`
2. Predict day B two ways:
   - **Baseline (a regional forecast):** `pred_i = mean(T(B))` — one number for every site
   - **Ours:** `pred_i = mean(T(B)) + offset_i`
3. Compare mean absolute error against the actual `T_i(B)`

**Pass:** ours beats baseline by a margin comparable to the spatial contrast (**expect ~0.2–0.4 °C** given
73 % persistence and 1.3–1.5 °C range). **That improvement is the product's headline number.**

**Fail:** no improvement → the offset is not learnable, the "your building is different" claim collapses,
and the project must rest on the physics layer alone. **Run this before anything else.**

**Bonus, same computation, free:** repeat using the control-polygon pair (`dec_3_CT_dayA`, `dec_4_CT_dayB`)
to confirm the effect is not specific to one polygon.

## N-6 (B-CODE) — ⚑ **FREE** — Solver validation

The physics layer is the technical core. It must be shown correct **before** it is trusted, and none of this
needs the API.

| Test | Pass condition |
|---|---|
| **Far-field relaxation** | With no heat sources, the interior relaxes to the ambient boundary condition |
| **No-wind symmetry** | Zero wind + one central heat source → radially symmetric field. Any asymmetry is a bug |
| **Mass/energy conservation** | Total heat out ≈ total heat in, within numerical tolerance |
| **Wind response** | Rotate the inflow 180° → the warm plume flips sides. *(The physics must do what FortyGuard's field demonstrably does not [M].)* |
| **Recirculation magnitude** | Condenser discharge modelled at **8–14 °C above ambient** [L] must produce an intake rise of the right order, not 0.01 °C and not 30 °C |
| **Grid convergence** | Halve the cell size → the answer changes by less than the ensemble spread |

**Fail any of these and the solver is not evidence, it is decoration.** Record all six in the writeup —
they are what makes the physics defensible to an NVIDIA judge.

## N-7 (B-CLAIM) — **FREE** — GPU speedup, the NVIDIA justification number

**Do:** run the identical kernel on CPU (NumPy) and on GPU (Warp) for 1, 10, and 100 ensemble members ×
1 and 20 sites. Record wall-clock for each.

**Record:** the speedup factor, and **the run count at which CPU becomes impractical**.
**Why it matters:** *"the GPU gives 40× so a 100-run ensemble across 20 sites takes 8 seconds instead of
5 minutes"* is a stated bottleneck. *"We used NVIDIA Warp"* is a logo. **This check is the difference.**
**Also record:** CPU and GPU must agree numerically to within tolerance, or the port is wrong.

## N-8 (B-CLAIM) — **FREE** — Is the bound honest?

**Do:** using ambient forecast-vs-realised residuals from history, compute **empirical coverage** of the
one-sided 90 % bound, plus **mean width**, plus a **binomial confidence interval** on the coverage figure.
Slice by hour-of-day and by site.

**Pass:** empirical coverage within the CI of nominal, and width small enough to be useful.
**Fail:** under-covering → widen; over-covering → tighten and say so.
**Report coverage and width together, always** — an infinite bound has perfect coverage and zero value.
**Report n_eff (≈ site-days), never the row count.**

## N-9 (B-CLAIM) — **FREE** — Ensemble calibration

**Do:** does the spread of the 100-run ensemble actually bracket the variation seen in reality? Compare the
ensemble's predicted spread of ambient against the observed day-to-day spread at the same sites.
**Pass:** comparable order of magnitude.
**Fail — too narrow:** the ensemble is overconfident; widen the input perturbations. **Too wide:** the bound
is useless; tighten. **Either way the conformal layer catches it** — but knowing which failure mode you
have determines the fix.

## N-10 (NICE) — **FREE** — Sensitivity sweep on every `[S]` constant

**Do:** re-run every conclusion across the plausible range of each stub — cooler approach, setpoint,
redundancy configuration, kW/ton, tariff, and the condenser-discharge assumption.
**Pass:** the conclusion's *direction* holds across the range.
**Report as a band with the constants named. Never a point estimate.**

---

# §3 — Order of work

## Now → Aug 17 (free, no key needed)

```
1.  N-5   offset skill        <- COULD KILL THE CORE CLAIM. Data is already on disk. Do this first.
2.  N-6   solver validation   <- six tests; the physics is not evidence until these pass
3.  N-7   GPU speedup         <- produces the NVIDIA justification number
4.  N-9   ensemble calibration
5.  N-8   bound honesty       (needs history; finish after Aug 18's fetch)
6.  N-10  sensitivity sweep
```

## Aug 18 morning — the call sheet, ~8 calls

```
0.  usage read                                    -> baseline
1.  heatmap, target cluster, g60, ft2  -> usage   -> PRICE. Re-budget everything off this
2.  N-1a  env_params at point A                   -> does it vary spatially?
3.  N-1b  env_params at point B, ~5 km away       -> the same, compared
4.  N-2   env_params, future hour                 -> forecast or nowcast?
5.  N-3a  history 2025-07-15                      -> depth
6.  N-3b  history 2023-07-15
7.  N-3c  history 2021-07-15
8.  N-4   exceedance over a past month (ft4)      -> cheap cumulative exposure?
```

**~8 calls ≈ 34 k credits at the historical rate.** Note: on the previously audited key the meter was
**frozen** — roughly twenty calls registered zero, because the billing cycle had closed and the
subscription showed `active: false`. **The hackathon key will have a live meter, so measure the price on
call 1 and re-budget before anything else.**

---

# §4 — What each outcome changes

| Check | If it fails | Project impact |
|---|---|---|
| **N-5** offset skill | The per-site offset is not learnable | **Severe.** The "your building is different" claim collapses; the project rests on the physics layer alone. **Free to find out — do it first** |
| **N-6** solver validation | The physics is wrong | **Severe.** Fall back to the statistical offset only; drop the GPU story honestly |
| N-7 GPU speedup | Speedup is trivial | The NVIDIA argument weakens to *"local, on-prem Nemotron"* only. State it rather than inflate it |
| N-1 spatial `env_params` | Values are regional | Generator-window layer weakens. **Core product unaffected** — the solver needs only temperature + wind |
| N-2 AQI forecast | Nowcast only | Generator windows become a derived index, clearly labelled |
| N-3 history depth | Only ~1 year | Predictive-maintenance output shrinks to a single-season index. State the scope |
| N-4 `exceedance` historical | Not supported | Count client-side. More calls, same answer. **Not blocking** |
| N-8 bound honesty | Under-coverage | Widen the bound. **This is the system working, not failing** |
| N-9 ensemble calibration | Spread wrong | Adjust input perturbations; conformal layer absorbs the rest |

---

# §5 — Reporting format

For every check, record:

```
CHECK ID:      N-5
WHAT IT TESTS: does a learned per-site offset beat a regional forecast
INPUT:         dec_1_DC_dayA.json, dec_2_DC_dayB.json  (17,862 tiles each)
RESULT:        baseline MAE = ___ C ; with offset MAE = ___ C ; improvement = ___ C
VERDICT:       pass / fail / inconclusive
NOTED:         anything surprising
```

**Keep raw responses, not summaries.** Every API response becomes a fixture, so the demo runs offline and
nothing depends on the network while judges are watching.
