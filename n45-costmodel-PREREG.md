# N-45 — PRE-REGISTRATION: respecify the commitment decision from physical data

**Written 2026-08-16, BEFORE any result is computed. Nothing in this file may be edited after the
first run. Amendments go in a dated appendix at the bottom, never by editing the conditions above.**

**Cost: zero API credits.** Uses the existing GPU physics table, saved fixtures, and free NOAA ASOS.

**Glossary first, because this file is unreadable without it:**

| Term | Plain meaning |
|---|---|
| **Stub `[S]`** | A number nobody measured. Put in to make the code run, meant to be replaced later. |
| **Breach / excursion** | The intake air got hotter than the limit the IT equipment is rated for. |
| **Staging** | Switching on a spare cooling unit *before* you need it, because it takes hours to come online. |
| **Threshold (`thr`)** | The temperature above which we call it a breach. |
| **Capacity** | How many °C of intake heating the spare unit can cancel out once it is running. |
| **DP (dynamic programme)** | Working backwards from the end of the day to decide the best action at each hour. |
| **Adversary** | The best simple rule we can build, tuned as hard as possible, that our agent must beat. |
| **σ (sigma)** | How many standard errors better one policy is than another. 2σ ≈ unlikely to be luck. |
| **Base rate** | What fraction of days actually have a breach. |
| **p-hacking** | Changing the setup after seeing the answer until you get the answer you wanted. Forbidden. |

---

## 1. Why this test exists — the defect found in N-44 on 2026-08-16

Four numbers jointly determine whether "when should I commit reserve cooling?" is an interesting
decision. **In N-44, all four were set by convenience rather than by evidence, and all four push in
the same direction: commit always, commit early.**

| # | Quantity | Value used | Where it came from | Verdict |
|---|---|---|---|---|
| 1 | `thr` — breach threshold | **0.00978 °C** | `np.percentile(allr, 75)`, [test_n44_adaptive_commit.py:438](testing/test_n44_adaptive_commit.py#L438). The comment on line 441 says it is set this way *"so the decision is non-trivial by construction."* | **Self-referential.** The breach threshold is a quantile of the model's own output. It is not a physical limit, and 0.00978 °C is far below any real instrument's resolution. |
| 2 | `CAPACITY_RISE` | **0.25 °C**, tagged `[S]` | [line 139](testing/test_n44_adaptive_commit.py#L139) | **25.6× the threshold.** The remedy is 25× stronger than the problem it fixes, so staging almost never fails to work. |
| 3 | `C_EXCURSION` | **120.0** | Inherited from [test_n9_staging.py:48-51](testing/test_n9_staging.py#L48-L51), whose own comment reads `# [S] plant stubs` | **Unsourced.** This single number is what makes a wrong commitment nearly free (loss 3.0 against a gain of 112.9). |
| 4 | `C_STAGE_FIXED` | **2.0** | Same stub block | **Unsourced.** |

**And a fifth problem, which is the most serious of all:**

> **`AMB = 30.0` — ambient temperature is FROZEN at 30 °C on every one of the 4,000 simulated days**
> ([line 141](testing/test_n44_adaptive_commit.py#L141), used at [line 182](testing/test_n44_adaptive_commit.py#L182)).
> The realised outcome `truth` is the **recirculation rise alone** (0 to ≈0.4 °C), never the intake
> temperature. **So the single largest driver of whether an intake actually overheats — the weather —
> was removed from the decision problem.** What remained was: *"will a 0.01 °C rise occur?"*, with a
> remedy worth 0.25 °C and a penalty of 120 units.

**Two further housekeeping defects found while reading:**

- Line 139's comment claims `CAPACITY_RISE` is *"swept in the sensitivity block."* **There is no
  sensitivity block in N-44.** `main()` runs exactly one configuration end to end. The comment was
  inherited from an earlier test and is stale.
- N-9 posed the same decision in **absolute** temperature (`thr_c = 33.0 °C`, `capacity_c = 1.5 °C`);
  N-44 posed it in **rise above ambient** (`thr = 0.0098 °C`, `capacity = 0.25 °C`). These are
  different problems with a **6× different capacity**, and the change was never reconciled anywhere.

### What this does and does not overturn

**It does NOT overturn:** N-44's P1 result. The AUC gate — discriminating power rising from
**0.6762 at 12 h to 0.8531 at 3 h**, bootstrap CIs disjoint — is a property of the *forecast* and the
*physics*, not of the cost model. It stands. *(Recorded honestly for the first time here: AUC is
**not monotonic**. It peaks at 3 h and then falls back to 0.8396 at 1 h. That is consistent with, and
explains, the adversary tuning itself to exactly hour 3.)*

**It does NOT overturn:** N-44's P3 result, which **passed** — the adaptive policy fired off its modal
hour on **66.5%** of committing days. It was never a threshold in costume. It simply lost.

**It DOES overturn the conclusion drawn from N-44's P2 failure.** HANDOFF §5 records: *"this problem's
physics is near-binary and its cost asymmetry is extreme, which together make the optimal policy
simple."* That statement is **true of the configuration that was run, and the configuration was chosen
rather than measured.** It has not been tested on a physically specified version of the problem.
It may still turn out to be true. That is what this test is for.

---

## 2. Honest audit: what published data can and cannot fix

I searched every primary document on disk. **Results, stated plainly, including the failures:**

| Quantity | Can published data set it? | Source |
|---|---|---|
| **Breach threshold** | ✅ **Yes** | ASHRAE 2011 class **Allowable** upper limits: **A2 = 35 °C**, **A3 = 40 °C**, both *"for short periods of time"* — [WP46 Green Grid, Executive Summary](idea2files(md)/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.md), lines 44-53, on disk and read. **⚠ One citation layer removed** — Green Grid quoting ASHRAE. The ASHRAE 2011 primary PDF has been read in full before in this project (mirror recorded in `damper-agent-plan.md:138`); the A-class limits must be confirmed against it directly before the number is quoted in the submission. |
| **Staged unit size** | ✅ **Yes** | Trane DC-WPR003A-EN, read in full, [line 24](idea2files(md)/DC-WPR003A-EN.md): a colocation plant of 6 chillers × 300 tons (1055 kW), **each chiller having 4 compressors of 75 tons (263.7 kW)**, against a base loop load of **825 tons (2901.4 kW)**. So one staging action = **one compressor = 75/825 = 9.09% of loop capacity.** Note this is **cooling** capacity (kW-thermal), *not* electrical draw. |
| **Cost of a start** (`C_STAGE_FIXED`) | ❌ **No number exists** | Trane supports it **qualitatively only** — short cycling causes *"compressor and equipment damage"* — but the document contains **no** cost, kW, or wear figure. **Must be swept, not asserted.** |
| **Cost of an excursion** (`C_EXCURSION`) | ❌ **Not to a single number, and it never will be** | It is facility-specific: a colocation SLA penalty, lost GPU-hours on a training cluster, and a bank's outage cost are three different numbers spanning orders of magnitude. Searched and **not found**: ASHRAE Handbook ch. 46 (extracted 14 pages: **0 hits** for x-factor, failure rate, reliability, downtime, `$`, kW — it is *Building Air Intake and Exhaust Design*, a physics chapter, not an economics one); Green Grid WP46 (**0** reliability-cost figures); Trane (**0**). **Must be swept, not asserted.** |

**Therefore the honest design is not to pick the two missing numbers. It is to sweep them and report
the region of cost-space in which a sequential policy wins.** That is a strictly stronger result than
a point verdict, and it cannot be p-hacked, because the pass condition below is stated in terms of the
*shape* of the winning region before any of it is computed.

*(Side note, logged for `fortyguard-api-findings.md`: ASHRAE Handbook ch. 46 is **"Building Air Intake
and Exhaust Design"**, containing **"Exhaust-To-Intake Dilution or Concentration Calculations"** and a
**"Geometric Method for Estimating Stack Height"**. That is an ASHRAE-standard method for precisely the
exhaust→intake problem the solver models. It is a **physics cross-validation opportunity** and is not
used anywhere in the project yet. Out of scope for N-45; do not let it be forgotten.)*

---

## 3. The respecified problem

Everything below changes an input **toward** a measured or published source and **away** from a
convenience value. Each direction of change was decided before any result was computed.

| Input | N-44 | **N-45** | Basis |
|---|---|---|---|
| Ambient | frozen at 30 °C | **varies per day, from real observations** (KIAD ASOS hourly history, the same free source N-40 used, plus the FortyGuard forecast/outcome pairs N-26 is accumulating) | The weather is the dominant term and must not be constant |
| Outcome | recirculation rise alone | **intake temperature = ambient + recirculation rise** | This is the physical quantity the product predicts |
| Threshold | p75 of own output (0.0098 °C) | **ASHRAE class Allowable limit** (A2 = 35 °C, A3 = 40 °C; both reported) | Published equipment spec |
| Capacity | 0.25 °C `[S]` | **derived from a 9.09% loop-capacity step** via an air-side energy balance, using the solver's own air properties | Trane, on disk |
| `C_STAGE_HR` | 1.0 | **1.0 — definitional**, the unit of account ("one hour of running the spare compressor") | Definition, not a claim |
| `C_STAGE_FIXED` | 2.0 `[S]` | **swept** | Unsourceable |
| `C_EXCURSION` | 120.0 `[S]` | **swept over decades** | Unsourceable |

**Everything else is held exactly as N-44 had it** — the GPU physics table, `PEAK_SD_H = 1.4475` from
N-38, the KIAD wind-direction error pool from N-40, `LEAD_H = 3`, the same tuned adversary family, and
the same paired scoring imported from `test_n9_staging.paired`. **The physics is not touched.**

### ⚠ The honest prediction, recorded before running

With ambient varying and an ASHRAE threshold, **breaches will be rare and driven by the weather**, with
the 0–0.4 °C recirculation rise acting as a *last straw* only on days when ambient is already within
≈0.4 °C of the limit. Against an A2 limit of 35 °C, a 30 °C ambient leaves **5 °C** of headroom, and
the largest rise the physics produces is ≈**0.4 °C — about 8% of that headroom.** So:

**I expect a low base rate, and I expect the decision to be live on only a small minority of days.**
That is not a reason to avoid the test. It is the reason to run it: it is the first version of this
problem where breaches are caused by the thing that actually causes breaches.

---

## 4. PRE-REGISTERED CONDITIONS — fixed before any number is seen

Let **R = C_EXCURSION / C_STAGE_HR** (how many hours of spare-unit runtime one breach is worth) and
**F = C_STAGE_FIXED / C_STAGE_HR** (how many hours of runtime one start is worth).

Swept grid, fixed now: **R ∈ {1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000}** (13 values,
log-spaced, spanning four decades and containing N-44's 120). **F ∈ {0, 1, 2, 5, 10}** (5 values,
containing N-44's 2). **65 configurations.** For each: tune the fixed-hour adversary on TRAIN days,
score both policies on HELD-OUT days, and record paired σ, off-modal fraction, base rate, and the
clairvoyant lower bound.

- **P0 — cost-model consistency (a guard, run first, on every configuration).** The clairvoyant policy
  (knows the outcome, picks the cheapest legal action) must be **≤** every other policy's cost on every
  configuration. If it is not, there is a bug in the cost model or the action space, and **no verdict
  may be read from that configuration.** This is the check that caught N-44's transition-matrix defect.

- **P1 — the AUC gate.** Already passed in N-44 (**+0.1634**, CIs disjoint) and **not re-litigated
  here**, because it does not depend on the cost model. Re-reported for completeness only.

- **P2′ — the sequential-decision condition.** There must exist a **contiguous band of R, at least half
  a decade wide** (i.e. R_high / R_low ≥ √10 ≈ 3.16, meaning at least three adjacent grid values), at
  **some** value of F, in which the DP beats the tuned fixed-hour adversary by **σ ≥ +2.0** on held-out
  days. *A single isolated winning grid point does NOT count* — that is noise or knife-edge tuning, and
  ruling it out is the whole reason this condition is written in terms of a band.

- **P3′ — the anti-threshold guard.** Inside that band, the DP must fire off its own modal commitment
  hour on **≥ 25%** of committing days. If it collapses to a constant it is a threshold in costume and
  **N-45 FAILS even if P2′ passes.**

- **P4 — the reality condition, and it can fail the test on its own.** The winning band must be
  reported alongside the best available evidence for where real facilities actually sit in R. **If a
  winning band exists but no plausible real facility lives inside it, the verdict for the product is
  still FAIL**, and it must be recorded that way. *A policy that only wins for cost ratios nobody has
  is not a product.* Evidence for real R will be gathered **after** the sweep is computed, so that
  knowing the winning band cannot influence the search — and the search method will be written down
  before it starts.

**N-45 PASSES only if P0 ∧ P2′ ∧ P3′ ∧ P4 all hold.**

### The pre-registered negative, which is a genuine result

**If the winning band is empty across all 65 configurations, then the sequential commitment decision is
dead for every cost model in four decades of the ratio that matters — not merely for one guessed
value.** That closes a question this project has re-opened five times, permanently, and it is a much
stronger and more honest finding than N-44's point failure. **It also frees the whole remaining sprint
for the perception-scheduling core.** Either outcome is worth the run.

### What N-45 still cannot establish — stated before running

- **One site layout.** N-28 already showed conclusions can be layout-specific. A pass would need the
  layout sweep repeated before being generalised.
- **Persistence wind error, one station, 72 days.** Persistence is the honest *lower* bound on forecast
  skill, so absolute numbers stay pessimistic and are not calibrated to FortyGuard's product.
- **Simulated days, real physics.** The rise distribution is the calibrated solver on the GPU; the days
  are sampled. This tests the DECISION STRUCTURE, not FortyGuard's forecast skill.
- **The A-class limit is one citation layer removed** until confirmed against the ASHRAE primary PDF.
- **Ambient forecast error will come from KIAD persistence, not from FortyGuard**, because only two
  usable FortyGuard forecast/outcome pairs exist so far (N-26 is still accumulating). Persistence again
  understates real skill.

---

## 5. Amendments log

### 2026-08-16 — Amendment 1: raw persistence de-biased per lead. Decided BEFORE any policy ran.

`fetch_n45_ambient.py` returned raw persistence errors whose **mean at lead 12 h is +8.784 °C**. That
is not forecast error — it is the diurnal cycle, because lead 12 from a 16:00 target compares against
04:00. Using it raw would hand the agent a +8.8 °C bias. **Per-lead mean subtracted, leaving the
anomaly error.** This is the standard persistence-of-anomaly baseline. No policy had been written or
run when this was decided; the artifact is visible in the raw fetch output alone.

*Minor in-sample note: the per-lead offset is estimated on the same 534 days later sampled from. With
n = 533 per lead the offset's standard error is ≈0.18 °C, so this is not a meaningful leak.*

### 2026-08-16 — Amendment 2: **the 65-configuration sweep in §4 was NOT run, and must not be.**

The two diagnostics (`diag45a.py`, `diag45b.py`, results in `results/n45_diag_live.json` and
`results/n45_diag_quantisation.json`) established, on 534 real summer days at KIAD:

- Against the ASHRAE A2 Allowable limit of 35.0 °C, a remedy of **1.00 °C** flips at most **10 of 534
  days (1.9%)**, and a remedy of **0.25–0.40 °C** — the size `CAPACITY_RISE` actually models — flips
  **none that the data can resolve** (see the resolution caveat below).
- Against the A3 limit of 40.0 °C, **zero** days, and this one is not a resolution question: the
  hottest observed ambient in six summers is **37.22 °C**, a **2.78 °C** gap.
- On the hottest days the headroom runs out entirely: p95 ambient 34.44 °C leaves **+0.56 °C**; p99
  ambient 36.67 °C leaves **−1.67 °C**. On the 26 days (4.9%) where ambient alone exceeds 35 °C, a
  sub-degree remedy cannot prevent the breach at any price.

**Therefore the sweep is moot. `C_EXCURSION` prices the CONSEQUENCE of an action; it cannot change the
action's EFFECTIVENESS.** No excursion cost, at any of the 13 ratios across four decades, can make a
0.25 °C lever close a 0.56–2.78 °C gap. Running all 65 configurations would consume a day of sprint
time to re-derive arithmetic already settled above.

**This is recorded as a decisive NEGATIVE for the commitment decision as N-44 posed it — and it is a
stronger closure than N-44's −19.37σ, because it is a physical result that holds for every cost model
rather than for one guessed set of constants.** P2′/P3′/P4 are therefore not evaluated: the action
space failed before the cost space was reached.

### 2026-08-16 — Amendment 3: resolution caveat on the "zero days" figure, stated because it limits the claim

**ASOS reports temperature in whole degrees Fahrenheit — confirmed, 100.0% of the 534 readings** — so
`tmpc` lies on a grid **0.556 °C** apart. A 0.40 °C band is *narrower than the data's own resolution*
and can be spuriously empty. **So "0 days" must not be quoted as a measurement.** The honest form:

> The nearest resolvable ambient value below 35.0 °C is **34.44 °C (94 °F), on 10 of 534 days**, which
> requires **≥0.56 °C** to flip. At this data's resolution, a remedy of ≤0.40 °C cannot be shown to
> flip any day.

The A3 result (zero days, 2.78 °C gap) is unaffected by resolution and stands as measured.
