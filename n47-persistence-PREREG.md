# N-47 — PRE-REGISTRATION: does FortyGuard's `persistence` analytic support a duration decision?

**Written 2026-08-16 BEFORE the calls are made. Conditions may not be edited afterwards; amendments
go in the dated log at the bottom.**

**Cost: exactly 2 paid `/v1/heatmap` calls, user-authorised 2026-08-16.** No other paid call.

---

## 1. Why this test exists

Five decision cores have died (see `intake-agent-plan.md` Part 0). Every one of them keyed on a **peak
temperature level** against a threshold, and N-45 established why that structurally cannot work here:
the economics are near-binary — on 84 % of days the optimal action is to do nothing, and acting
wrongly costs almost nothing — so *"act early, always"* is near-optimal and there is nothing to decide.

**Duration is a different quantity with different economics.** Energy = power × time, so cost scales
*linearly* with how long an excursion lasts, not as a step function. A 30-minute excursion is harmless;
a six-hour one is expensive. Cooling plant has ~3 h of thermal inertia, so *how long* is precisely what
decides between three genuinely different actions — pre-cool into thermal mass, ride it out, or stage
capacity — each with a different cost and a different latest-useful-moment.

**And it is FortyGuard-native, which is the criterion the previous cores failed.** The duration and its
spatial variation come from **their `persistence` analytic**; nothing else provides it at 60 m. In cores
1–5 the decision-relevant *variation* came from wind direction, which FortyGuard does not sell — the
project's central structural weakness. Here their data supplies the decision variable itself.

**This is the SIXTH and FINAL candidate core.** Agreed stopping rule: if it fails, no seventh is
proposed and the project ships as an instrument with six documented negatives.

---

## 2. What is already known for free, and what is genuinely unknown

Established at **zero cost** from already-paid fixtures on disk, before spending anything:

| Fixture | `value` | Distinct | Reading |
|---|---|---|---|
| `vd_d3_exceedance.json` | **6.000** flat | 1 | the D3 window was 6 h |
| `vd_d3_persistence.json` | **6.000** flat | 1 | **identical to exceedance only because no threshold was applied** |
| `n17_r2_exceedance.json` | 143.249 – 169.991 | 84 | an accumulated magnitude, not hours |
| `n17_r2_persistence.json` | **7.031 – 10.374** | **80 of 84** | **a duration in hours, varying spatially** |

**So `persistence` returns hours and it is a genuinely different quantity from `exceedance`.** Defect
D3's "they are identical" was our own bug: both calls returned *the whole window*.

**⚠ But BOTH prior tests sent the wrong field name.** `verify_api_defects.py:172` and
`test_n17_recheck.py:49` both send **`threshold_temperature`**, which probe 2 proved on 2026-08-16 the
API **silently ignores** (it validates `threshold`). N-17 nonetheless saw spatial variation because it
used `filter_type: 4` across all of July 2026, so a **server-default** threshold produced 7–10 h.

**Therefore the two things that actually matter are still unknown:**

1. **Does `threshold` — spelled correctly — change the result at all?** Never tested. If it does not,
   the decision core is dead on arrival, because a duration decision must key on a threshold the
   operator chooses.
2. **What are `persistence`'s units and semantics?** Three candidates, and they are not equivalent:
   **(a)** total hours above threshold within the requested window · **(b)** average hours per day ·
   **(c)** the longest single contiguous run. `test_n17_recheck.py`'s own docstring flags this ambiguity
   and never resolved it.

---

## 3. The two calls

Both on the **same** window and AOI so they are directly comparable; **only `threshold` differs.**

| | Call 1 | Call 2 |
|---|---|---|
| `analytic_type` | `persistence` | `persistence` |
| **`threshold`** (spec spelling) | **31.0 °C** | **32.0 °C** |
| `direction` | `above` | `above` |
| AOI | 8 × 8 km at (39.0100, −77.4460) | identical |
| `granularity` | 60 | 60 |
| Window | **2026-07-28, 10:00–20:00 site-local**, `filter_type: 2` (10 h) | identical |

**Why these choices, each justified rather than picked:**

- **2026-07-28, not 2026-06-23.** Free reconnaissance of the saved fields shows 06-23 is a **cool day —
  max 20.52 °C across the whole AOI** — so any threshold near 30 °C would return zeros everywhere and
  waste both calls. On **07-28** the same AOI runs **min 29.98 · p10 30.52 · median 31.15 · p90 31.65 ·
  max 32.43 °C.**
- **Thresholds 31.0 and 32.0 °C** straddle that distribution: 31.0 sits just below the median (most
  tiles should exceed it for a long time) and 32.0 sits near the p99 (few tiles, briefly). If threshold
  works at all, these two must differ substantially.
- **A 10-hour window with `filter_type: 2`** bounds the answer: if `persistence` is hours-within-window,
  every value must be **≤ 10.0**. That single bound discriminates semantics (a) from (b) and (c).
- **Granularity 60** because pricing is documented flat in granularity, so the finer field is free.

---

## 4. PRE-REGISTERED CONDITIONS — fixed before the calls

- **P1 — the threshold must work.** `median(duration @ 31.0) > median(duration @ 32.0)`, strictly, and
  the two fields must not be tile-for-tile identical. **If they are identical, `threshold` is ignored
  even when spelled correctly — the decision core is DEAD, and that is a new, more serious API defect
  than any of the fifteen already documented.**

- **P2 — it must be a duration, with intelligible units.** All values in **[0, 10.0]** for a 10-hour
  window. If values exceed 10.0, the quantity is not hours-within-window and semantics (b) or (c)
  applies; the test then reports which and **no decision core is built until the units are settled**,
  because a decision keyed on a misread unit is worse than no decision.

- **P3 — there must be decision-relevant spatial variation.** At the lower threshold, the duration field
  must show **sd > 0.25 h** and **≥ 50 distinct values** across the AOI. Rationale: a decision that
  allocates action across a cluster needs the cluster to actually differ. Below that, duration is
  effectively uniform and there is nothing to decide about *where*.

- **P4 — honesty on what this does NOT establish.** Two calls on one day at one AOI cannot establish
  day-to-day behaviour, forecast skill on duration, or that any operator would act on it. **No decision
  core may be claimed from this test alone** — it is a *gate*, and passing it only earns the right to
  spend one pre-registered day building the core.

**N-47 PASSES the gate only if P1 ∧ P2 ∧ P3 hold.**

### The pre-registered negative

If P1 fails, the sixth core dies for **2 calls instead of a day of work**, and the project ships as an
instrument with six honest negatives. **That is a cheap, decisive outcome and it is worth the two
calls either way.**

### ⚠ Honest prediction, recorded before running

I expect **P1 and P2 to pass and P3 to be the risk.** The saved 07-28 field spans only **29.98–32.43 °C
— a 2.45 °C range across 17,862 tiles** — and a 31.0 °C threshold cuts through the middle of a narrow,
smooth distribution. Duration may therefore be nearly saturated (close to 10 h) over most of the AOI and
near zero elsewhere, with a thin transition band: a near-binary spatial field, which is **exactly the
zero-inflation problem that killed N-46's margin claim.** If that happens, duration varies in *time* but
not usefully in *space*, and the decision would have to be about *when*, not *where* — which returns us
to the commitment problem that N-45 closed. **I am recording this now so the result cannot be
reinterpreted favourably afterwards.**

---

## 5. Amendments log

### 2026-08-16 — RESULT: **GATE FAILED on P2.** The sixth core dies, for 2 paid calls.

`test_n47_persistence.py` → `results/n47_persistence.json`; free follow-up `diag47a.py` →
`results/n47_diag_units.json`. 17,862 tiles per call, 2026-07-28 10:00–20:00 site-local.

| Condition | Verdict | Evidence |
|---|---|---|
| **P1** threshold must work | ✅ **PASS** | median **2.960 h @ 31.0 °C** vs **1.000 h @ 32.0 °C**, difference **+1.960 h**, not tile-identical. **`threshold` spelled per the spec IS honoured** |
| **P2** must be a duration in [0, 10] | ❌ **FAIL** | values run **−0.581 → 4.248 h**. Upper bound held; **durations are NEGATIVE** |
| **P3** spatial variation | ✅ **PASS** | sd **1.015 h**, **9,971 distinct** values of 17,862 tiles, 0 % at ceiling |

**P1 conclusively confirms the field-name defect (12.8).** With `threshold` spelled correctly the
analytic responds correctly in aggregate. **Both prior tests — `verify_api_defects.py:172` (D3) and
`test_n17_recheck.py:49` (N-17) — sent the ignored `threshold_temperature` and are therefore invalid.**

**And my pre-registered worry was wrong in the right direction:** I predicted P3 would fail because the
07-28 field spans only 2.45 °C and duration would saturate into a near-binary spatial field. It did
not — 9,971 distinct values, nothing at the ceiling. The spatial signal is genuinely rich.

### Why P2's failure is fatal rather than cosmetic — the free diagnostic settled it

Two explanations were possible: **(A)** a real duration with a small numerical artifact near zero, or
**(B)** not a duration at all. Three tests, all free, and they point at **(B)**:

1. **Monotonicity is violated on 9.06 % of tiles** (1,619 of 17,862; 7.44 % worse than −0.05 h; worst
   **−0.625 h**). **A duration cannot decrease when the threshold is lowered** — you cannot spend *less*
   time above 31 °C than above 32 °C. This is physically impossible and it is not a rounding artifact.
2. **The negatives are not an edge/interpolation artifact.** The outermost 5 % of the AOI holds 18.9 %
   of tiles but only 10.5 % of the negative tiles — an enrichment of **0.56×**, i.e. negatives are
   *depleted* at the boundary and **scattered through the interior**.
3. **A massive spike at exactly 1.00 h.** At threshold 32.0, **47.87 % of tiles read 1.00 h** (2 dp) and
   **55.25 % lie within 0.01 h of 1.000**. That is a floor, default or quantisation, not a measurement.

> **Conclusion: whatever `persistence` returns, it is not a coherent duration, and the spec offers no
> definition (its response schema is `{}`).** Per §4's P2, *"no decision core may be built until the
> units are settled, because a decision keyed on a misread unit is worse than no decision."*

### Consequences, recorded plainly

- **The sixth and final decision core is dead.** Per the agreed stopping rule, **no seventh is
  proposed.** The project ships as an **instrument** with six documented negative results.
- **Cost of learning this: 2 paid calls** — exactly what the gate was designed to cost, instead of a
  day of building on a misread quantity.
- **New API defect #16, and it is substantive** — see below. Reproducible, quantified over 17,862 tiles
  × 2 thresholds, and directly useful to FortyGuard.

### 🔴 DEFECT 16 for the handover document

**`analytic_type: persistence` returns a quantity that cannot be a duration, and is undefined in the spec.**

| Symptom | Measured |
|---|---|
| Negative values | down to **−0.581 h** (2.40 % of tiles at thr 31.0; **6.92 %** at thr 32.0) |
| Non-monotone in `threshold` | **9.06 %** of tiles have `d(31.0) < d(32.0)`, worst **−0.625 h** |
| Degenerate mode | **47.87 %** of tiles read exactly **1.00 h** at thr 32.0 |
| Documentation | response schema in the OpenAPI spec is literally `{}`; no units, no definition |

**Aggregate behaviour is sane** (medians 2.960 vs 1.000 h; mean tile-wise difference **+1.492 h**), which
is why this survives a summary-statistics check and only fails a tile-level one. **A caller who trusts
it per-tile — which is what any spatial decision does — is reading noise as hours.**

### ⚠ One free channel that could overturn this reading, and the plan must NOT depend on it

**Fawad Shah's session, Aug 18, 7:15 PM PKT**, explicitly covers *"Choosing the right analysis layer:
snapshot vs. exceedance vs. persistence"* and *"Where the data will mislead you if you read it
naively."* If `persistence` is not intended as hours at all, this reading changes. **Attend with this
data in hand and ask directly.** But the sprint plan proceeds as if the gate failed, because it did.
