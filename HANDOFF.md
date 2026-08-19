# HANDOFF — FortyGuard Hackathon'26 · INTAKE-ARBITER

**Rewritten from scratch 2026-08-20. Supersedes all earlier versions.**
**Submission deadline Aug 30 23:59 GST = 00:59 PKT Aug 31. 10 days left.**

> **THE FIVE THINGS THAT MATTER MOST, in order:**
>
> 1. **THE FORECAST BLOCKER IS GONE.** It was a ~30-hour FortyGuard outage, not a plan limit —
>    proven 2026-08-19 by one paid call returning **17,862 tiles at a 9.41 h lead** five hours after
>    the automated task had failed. **N-26 can grow again: 4 pairs now, 10 needed, ~1/day. §4**
> 2. **THREE REAL SITES SHIP, TWO WERE REFUSED ON EVIDENCE.** Ashburn (AWS IAD116→117), Chicago
>    (Stream→Equinix CH3), Dulles (AWS IAD81→IAD62). Santa Clara rooftop-cooled, Phoenix not built.
>    **"Five screened, two refused" is the single most credible thing in this project. §6.5**
> 3. **`python run_all.py` rebuilds and audits everything in ~96 s with ZERO API calls**, exits
>    non-zero on any failure. **12 steps, 39 checks, 68 published numbers re-read from the files the
>    code wrote.** If it is not green, quote nothing.
>    **⚠ `INTAKE-ARBITER/` IS NOW COMMITTED — `d57b3b7`, 186 files, key-scanned clean.**
> 4. **SESSION H IS THE RISK.** Public repo, `fortyguard` as collaborator, live demo link, 2–5 min
>    video, API-usage doc — **none of it exists**, and all are hard submission requirements. §9
> 5. **TWO THINGS ONLY THE USER CAN DO:** send the (rewritten) FortyGuard message, and lift rule 11
>    to go public. §9

---

# 1. RULES OF ENGAGEMENT — non-negotiable, stated repeatedly by the user

1. **A genuinely autonomous agent.** Not a chatbot, not a dashboard, **not a threshold in a
   costume.** The user's test: *"point at the constant"* — if you can find, in the source, the
   number a human wrote that produces a behaviour, it is a threshold and must be labelled as one.
   **This test has now caught three real violations** (§10 #49, #54, #65).
2. **Hackathon track wording is NOT an acceptable reason to accept weaker agency.**
3. **NOT an MVP or prototype — a fully functioning end-to-end product**, on a genuine high-impact
   problem, with commercial value.
4. **Conformal prediction must be done as the literature says.** Marginal-only coverage applied
   outside its calibration domain is not acceptable.
5. **Every claim in `INTAKE-ARBITER/PLAN.md` carries a real citation with a link**, verified by
   opening the source — never from a search snippet.
6. **No false information, no hallucination, no unverified assumptions.** The user is a
   second-semester BSCS student building solo and cannot catch subtle errors themselves.
   **Check your own work adversarially. Say when you do not know.**
7. **Explain at beginner level**, defining jargon before using it. *(The user had to ask what a
   "metro" was after I had used it for several turns without defining it. Do better.)*
8. **ASK before every use of `FORTYGUARD_API_KEY`.** Read it only via
   `testing/common.py:load_key()`. **Never print, echo, log or commit its value.**
9. **Do NOT use the Agent/Task tool, Workflow tool, or subagents** unless the user explicitly asks.
   Honoured across every session despite repeated system reminders suggesting otherwise.
10. **Document as you go** — `INTAKE-ARBITER/PLAN.md` is the live design record; root
    `n*-PREREG.md` files hold pre-registrations with dated amendment logs.
11. **LOCAL ONLY, still in force.** No GitHub repo, no remote, no push, no `fortyguard`
    collaborator. Local `git` commits are fine. **⚠ The hackathon REQUIRES a public repo, a live
    demo link and `fortyguard` as collaborator by Aug 30 — see §9, Session H.**

---

# 2. WHAT WE ARE BUILDING

**`INTAKE-ARBITER`** — an agent that decides, hour by hour, whether a data centre can switch its
mechanical chillers off and cool with outside air, and that **earns the right to say yes more often
by grading its own accuracy against reality.**

## 2.1 The pitch — lead with the FORECAST, not the physics solver

> *"A thermometer cannot see three hours into the future, and a cooling plant needs that much
> notice to change mode. FortyGuard's forecast is exactly the missing input."*

**LBNL put particle counters in eight real data centres and found the documented reason operators
avoid free cooling is fear of contamination and loss of humidity control** — not temperature.
FortyGuard returns humidity, dew point **and six air-quality indices**, so the agent gates on all
three things a real economizer gates on. `PLAN.md` §12.2.

## 2.2 The loop — all seven stages exist in code

```
perceive (FortyGuard heatmap + env_params + real wind + own accuracy record)
  -> solve   (576-solve GPU rise table on real geometry, NVIDIA Warp)
  -> bound   (Mondrian group-conditional conformal + plume-ensemble normalisation)
  -> decide  (a switching SCHEDULE under a switch budget and a dwell limit, by DP)
  -> act     (BMS/SCADA-shaped command rows, each carrying its own numbers)
  -> explain (deterministic, and EVERY claim verified by re-running the agent)
  -> score   -> recalibrate (the margin widens itself when reality proves it wrong)
```

**The agentic claim and its honest limit:** an **adaptive controller with a self-calibrating
boundary**, **not** a stopping rule. Seven pre-registered "when to act" cores all failed — §6.1.
**Since Session A it also runs in the PRESENT TENSE** — any start hour, any plant state — §6.4b.

**Headline metric: chiller-hours avoided.** Session G now also prices it — **but only the chiller
COMPRESSOR term**, from two documents downloaded and parsed in this repository. §6.12 and
`money-sources.md`. **The °C→kWh conversion for fans, pumps and towers is still NOT sourced and
still NOT claimed**, and the unmeasured fan term has the *opposite* sign.

## 2.3 ⚠ CLAIMS THAT ARE RETRACTED — never reuse them

| Retracted | Killed by |
|---|---|
| *"Operators read a weather station kilometres away"* | **FALSE.** On-site rooftop stations. `PLAN.md` §12.3 |
| *"Spatial resolution is the value proposition"* | Worth **+0.036 °C**. FortyGuard's value is the TIME dimension |
| *"+67 h/yr from recirculation alone"* | **MISATTRIBUTED — §6.3.** An uncertainty asymmetry; recirculation *costs* hours |
| *"Nobody sells forecast-aware switching"* | **Overstated.** Corrected in `PLAN.md` §12.9 |
| *"Buildings absorb 99.7 % of plume heat"* | **STALE — fixed 2026-08-12.** Obstacles are TRANSPARENT. §10 #26 |
| *"The solver absorbs heat into buildings"* (in the demo's own limits panel) | **Was live in the UI for a week after retraction.** §10 #56 |
| *"Forecast windows are unavailable on this plan"* | **WRONG — a ~30 h outage.** §4, §10 #59 |
| *"The solver absorbs heat into buildings"* (again — in `agent.py` ×3, `direction_sweep.py`, `solver.py`'s docstring, and **`trace.json`'s `known_defect`**) | **STALE for eight days. Fixed 2026-08-20.** Nothing rendered it, unlike #56. §6.10 #3 |
| *"The unanchored agent carries the worst measured offset"* (the browser's own label) | **That construction is the ORACLE #48 retracted.** The agent rotates four offsets leave-one-out. §6.10 #2 |

---

# 3. STATUS — blunt

## 3.1 Built, verified, reproducible in one command

| | |
|---|---|
| **The agent loop, 7 stages** | `INTAKE-ARBITER/src/agent.py`. **120,960 scenarios** across 8 swept axes. Zero API calls, ~37 s |
| **Rigorous conformal layer** | `src/conformal.py` — Mondrian, convolution, CQR, ACI/DtACI, joint coverage, worst-group. **20/20 self-tests** |
| **Present-tense controller** | `src/rolling.py` — starts from ANY hour in ANY state; **12 per-lead conformal bounds, all covering ≥ 90 %**; churn **1.128 %**, **94.08 % of re-plans change nothing**. §6.4b |
| **Five-year backtest** | `src/backtest.py` — 43,763 h, N-56 ladder, **12-axis sensitivity**, Mondrian audit, 43,260-round ACI |
| **Multi-site engine** | `src/metros.py` + `discover_dc_clusters.py` + `fetch_weather.py` + `annotate_screen.py`; 7 pipeline scripts made metro-aware. **3 sites live, 2 refused.** §6.5 |
| **Solved plume fields** | `src/export_plume_fields.py` — 72 real solved fields per site, audit-verified against the published rise to ≤1.1 % |
| **Environmental gates** | `src/environment.py` — dew point / wet-bulb vs PsychroLib **0.2681 °C MAE**; air quality; cloud→Pasquill |
| **Plume uncertainty** | `src/plume_uncertainty.py` — ensemble spread IS the bound's width. **34.6× variation** across bearings |
| **Stage 7 explain** | `src/explain.py` — **1,336 explanations, 0 verification failures** |
| **The reasoning tape** | `src/ticker.py` — seven-stage events, **29 templates and not one literal digit**, 1,002 hour-tapes verified. §6.9 |
| **Conformal made visible** | The browser DERIVES the quantile: `cfQuantileIndex` / `cfSplit` mirror `conformal.py` and agree **exactly on 789 assertions**. §6.11 |
| **Full-tree audit** | `src/audit.py` — **39 checks, 0 failures**, **68 published numbers** re-read from emitted files |
| **Money, sourced** | `src/money.py` — **$/kWh and kW/ton BOTH SWEPT over published values**, 608 cells, nothing collapsed. §6.12 |
| **One command** | `src/run_all.py` — plume → agent → backtest → rolling → manifest → explain → **money** → **ticker** → fixtures → audit. **12 steps, ~97 s, zero API calls** |
| **The interface** | `demo/index.html` (~100 KB, light+dark). Headline strip, MapLibre site map, **site picker**, solved-plume panel, screen-zero field, aerial, schedule, bound chart, wind dial, live explanations, coverage, ladder, honest limits |
| **Cross-language proofs** | browser == Python on **scheduling (500 cases)**, **decisions (20,160 configs — was 2,016, see §6.10)**, **reasons (1,336 hours)**, **stage-event sentences (2,037, character for character)** |
| **Validated physics** | vs analytic plume **0.00 %**, heat conserved **0.00 %**, **67** Prairie Grass experiments, 6 instrumented condensers **r=0.798**, GPU **81.6×** at **0.00012 °C** agreement |

## 3.2 IN PROGRESS / KNOWN INCONSISTENT

| Item | State |
|---|---|
| **N-26 coverage is 4 pairs, needs 10** | Collector hardened (§4.2). **~1 pair/day if the machine is awake 11:30–17:00 PKT.** ~Aug 25 if nothing fails |
| Five-year full factorial | 12-axis **one-at-a-time** sweep only. `agent.py`'s 120,960-scenario factorial covers 4 FortyGuard days, not the 5-year record |
| Dulles imagery verdict | **WEAKER than Ashburn's** — no USGS cross-check, so the two-source rule is NOT met. Chillers vs generators indistinguishable at 0.3–0.5 m. Recorded as such |
| Chicago FortyGuard field | **One past-window field.** Buys the spatial statistics + screen-zero visual, **NOT** a level offset (needs forecast + elapsed outcome = 2 calls) |
| Santa Clara / Phoenix | Refused on **screened pairs**; 5 Santa Clara frames and both other Arizona clusters remain unscreened. "Strong indication", not proof |
| `PLAN.md` | Updated for the gate fix and the 12-axis sweep. **NOT yet updated for Sessions A, B, E, D** |
| Repo size | The committed tree is **194 MB**, mostly screening imagery (`data/imagery/` is 22 PNGs at 2–4 MB) plus `scenarios.json` at 28.8 MB. Under every GitHub limit, but **Session H must decide what a public repo publishes** |

## 3.3 NOT BUILT

| Missing | Notes |
|---|---|
| **Session F** — conformal panel | `rolling.json` already ships the per-lead margins and coverage it needs — verified, both are in `configs[0]`. **Cut this first if time compresses** |
| **Session H** — submission | **Downloadable report, README, API-usage doc, 2–5 min video, public repo, `fortyguard` collaborator.** All hard requirements. **Highest risk** |
| Local LLM narrator | Deliberate: VRAM measured at 371 MiB of 6,141 so it would fit, but no inference stack exists. `PLAN.md` §8l.1 |
| Same-day anchoring test | ~2 paid calls/day. **Unblocked** by §4 — if it worked, the customer-sensor requirement disappears |

---

# 4. ✅ THE FORECAST BLOCKER IS GONE — it was an outage

**DIAG-62, `testing/diag62_forecast_recheck.py`, one paid call authorised by the user:**

| | |
|---|---|
| Window | 2026-08-19 **19:00–21:00 site-local**, i.e. the FUTURE |
| **Lead** | **9.41 h** — reproduces the N-25 reference lead exactly, inside the 6.0–11.5 h band |
| AOI / gran / analytic | 8×8 km on the committed centre / 60 / `tcm` — **identical to the collector** |
| **Result** | 🟢 **17,862 tiles in 35.7 s, `empty_completed_polls` = 0** |
| `activity_id` | `f333f605-6ef6-4847-9bbf-1d22910ebcb6` |

**Verified a genuine forecast before the claim was written:** identical lattice to the past-window
fixtures (17,862 of 17,862 keys), **zero of 17,862 values match** the 2026-08-16 field, delta mean
**+0.56 °C** spatially varying, 30.32–32.30 °C plausible for an August evening in Virginia.

**What pins it to an outage:** the automated task FAILED at **08:30 UTC the same day** (58 polls
over 607 s) and this call SUCCEEDED at **13:35 UTC**. **A five-hour recovery. An entitlement cannot
appear during a day.** The outage ran at least 2026-08-18 → 2026-08-19 08:30 UTC: seven zero-tile
responses, **≈29,540 credits bought nothing.**

## 4.1 The 4-pair ceiling lifts

A 90 % bound needs **9 calibration days**, and scoring it needs a test day that is not one of them,
so **10 PAIRS — not 9.** We have 4. **6 more.** *(The dry-run's first version said 9 and would have
stopped us one short at 8/9 = 88.9 %.)*

**65.6 % is PROVISIONAL again, and remains the ONLY figure to quote today** — 3 test days, worst day
0.0 %, FAILED its pre-registration. **Never quote 90 % until the pairs exist.**

## 4.2 The collector, hardened in Session 0

| | |
|---|---|
| Triggers | **13:30 + 13:50 + 14:15 PKT** — leads **9.50 / 9.17 / 8.75 h** |
| Why clustered | The in-band firing window is 11:30–17:00 PKT, but spreading retries across it would push the lead spread past the 3.0 h comparability warning. Kept within **0.75 h** |
| Retry cost | **Zero when the first succeeds** — `forecast_done` / `outcome_done` short-circuit before any call |
| Spend cap | **`MAX_FORECAST_ATTEMPTS_PER_DAY = 3`**, written to the manifest *before* the call so a crash still counts |
| Sleep | **`WakeToRun` + `StartWhenAvailable` + run-on-battery** on all three tasks (`FG-N26-Coverage`, `-Retry1`, `-Retry2`). **Sleep is what lost 2026-08-14 and 08-17** — absent from the manifest, no error, machine asleep |
| Free verifier | **`python test_n26_coverage.py dryrun`** — window, true lead, in-band firing window, outcome debt, pair arithmetic. **Zero API calls, no key read** |

## 4.3 ⚠ The FortyGuard message must be REWRITTEN before sending

`fortyguard-message-forecast-zero-tiles.md` is flagged **DO NOT SEND AS DRAFTED**. Its central
question — *"does the Hackathon plan include forecast windows?"* — **is now answered: yes.**

**The report still worth sending**, and useful to them: for ~30 hours, forecast requests returned
`HTTP 200` + `status: completed` + zero `features` **and were billed 4,220 each** — seven of them,
≈29,540 credits — with nothing on the status endpoint distinguishing an incident from an empty area,
an out-of-horizon window or a permission failure. Ask for: an incident signal, a non-`completed`
status on failure, and no billing for an empty result. `fortyguard-api-findings.md` §10.7.

---

# 5. THE THREE COMMITTED SITES

**Re-run order after ANY geometry change** — `PLAN.md` §8.7, and **§10 #66: never run a middle
stage alone**:

```
fetch_geometry.py → select_site.py → refusal_rank.py → screen_architecture.py
  → annotate_screen.py → HUMAN/MODEL IMAGERY VERDICT → commit_site.py
  → BANK_MODE=longest build_site.py → BANK_MODE=facing build_site.py
  → direction_sweep.py → export_plume_fields.py → metros.py --manifest
```

All are **metro-aware via the `METRO` environment variable**; unset resolves to `ashburn` with
byte-identical paths, so every audited number is untouched.

| | **ashburn** (default) | **chicago** | **dulles** |
|---|---|---|---|
| Pair | AWS **IAD116 → IAD117** | **Stream Chicago II → Equinix CH3** | AWS **IAD81 → IAD62** |
| OSM ways | 744496750 → 744496741 | 863162820 → 377032061 | 693381107 → 545396372 |
| Facade gap | 60.3 m *(clears the 60 m floor by 0.3 m!)* | 118.4 m | 137.7 m |
| Clearance | +0.737 | +0.665 | +0.984 |
| Critical rise | **0.3550 °C @ 255°** | **0.4116 °C @ 240°** | **0.3593 °C @ 265°** |
| Station | KIAD 8.9 km, 43,763 h, 99.92 % | KORD 4.4 km, 43,775 h, 99.94 % | KIAD 6.7 km (shared) |
| FortyGuard field | ✅ 9 calls, 8 saved fields | ✅ 1 call, 17,797 tiles | ❌ not purchased |
| Bank, `longest` | 123×20 m, 26 cells | 162×20 m, 32 cells | 232×20 m, 47 cells |

**Dulles cost ZERO credits and ZERO weather work** — it shares KIAD, so it isolates **geometry and
operator** from climate. Its cluster holds 24 tagged data centres of 31 buildings (77 %), operated by
AWS (9), Google (3), Microsoft (2), Digital Realty (2), CyrusOne — including a 198,921 m² **Google
Data Center** and a 136,947 m² **Microsoft Data Center**.

**⚠ `data/imagery/imagery_manifest.json` describes the SUPERSEDED site** (Digital Realty IAD35/36).
Use `data/imagery/screen/…` and `screen_manifest.json`.

---

# 6. RESULTS — every number traceable, `audit.py` re-checks 61 of them

## 6.1 The seven dead decision cores — do not re-run these

`PLAN.md` §6. Forecast sharpening (N-25) ❌ · day-to-day sharpening (N-42) ❌ · wind-direction
sharpening (N-40) ❌ · fleet triage (N-43) −3.63 σ ❌ · adaptive commitment (N-44/45) ❌ · margin
reduction (N-46/48) ❌ · commitment timing (N-50) **−15 to −22 σ once an oracle leak was removed
from our own DP** ❌.

> **THE STRUCTURAL REASON: because a conformal bound is calibrated per lead, the breach rate is
> 10 % at every hour BY CONSTRUCTION. Waiting trades cost (falling) against deadline risk
> (rising). Two monotone curves cross at ONE hour, which a fixed rule expresses exactly.**

**Also dropped:** fleet GPU allocation (−2.7 σ) · credit-budget scheduling (*optimises against
FortyGuard revenue*) · within-site bank differentiation · geometry from `/v1/satellite` (no
footprints) · `/v1/heat_intelligence` (748 KB PDF, **leaks the key**) · Earth-2/CorrDiff (≥40 GB
VRAM, machine has 6) · RAPIDS · direct plant control.

## 6.2 The conformal layer — measured on real weather

Held-out chronological split, 913/913 days:

| notice | pooled: overall / **worst hour** / groups <90 % | Mondrian: overall / **worst** / <90 % | Mondrian q range |
|---|---|---|---|
| 1 h | 0.9011 / **0.7864** (h19) / 8 of 24 | 0.9133 / **0.8838** / 4 | 0.81–2.17 °C |
| 3 h | 0.9017 / **0.7314** (h9) / 6 of 24 | 0.9144 / **0.8794** / 5 | 1.49–4.37 °C |
| 6 h | 0.9113 / **0.7884** (h11) / 8 of 24 | 0.9177 / **0.8936** / 2 | 2.21–6.66 °C |

**A pooled average of 0.9017 hides an hour at 0.7314.** Adding season **over-stratifies** — worst
group falls to 0.8484 — so **hour-of-day alone is the right stratification**.

**Online ACI, 43,260 real rounds:** static 0.8943 → **ACI 0.8998**, DtACI 0.8996. Honest note: the
de-biased persistence stream is nearly stationary, so the gain is only **+0.55 pp**.

**Full conditional coverage is PROVABLY IMPOSSIBLE** distribution-free (Barber, Candès, Ramdas &
Tibshirani 2021, `PLAN.md` §12.7). Group-conditional is the ceiling, and we say which one we shipped.

**N-26 live coverage: 65.6 % pooled, worst day 0.0 %, 3 test days.** FAILED its P1/P2. Split:
**90 → 75 % is our own sample size**, **75 → 65.6 % is FortyGuard's day-varying level offset.**

## 6.3 🔴 The +67 h/yr correction — read before quoting any hours figure

N-56's own rows at notice 0 / anchored / 24 °C: sensor error 0.1 → +10.4, **0.3 → +66.8**, 0.5 →
+162.0 h/yr, **with the agent's buffer fixed at 0.1945 °C in all three.** It is an **uncertainty
asymmetry** (FortyGuard 0.15 °C vs customer sensor 0.3 °C), **not recirculation.** Isolated by
rerunning with the plume term removed from the agent's bound but left in the truth:

| | gain | breaches / 1,000 free-cooling hours |
|---|---|---|
| agent KNOWS about the plume | **+65.6 h/yr** | **0.17** |
| agent IGNORES the plume | +42.8 h/yr | 0.63 |

**Plume awareness COSTS 22.8 h/yr and cuts the breach rate 3.7×. It buys SAFETY, not HOURS.**

## 6.4 The five-year ladder — 913 held-out days, sensor 0.3 °C

**Regenerated on the SOURCED dew-point gate. All five rows are now in `audit.py`'s registry — they
were not before, which is exactly how the invented constant survived.**

| step | gain h/day | ±95 % | h/yr | coverage |
|---|---|---|---|---|
| N-56-like: notice 0, skill 1.00, no constraints | +0.1796 | 0.0357 | **+65.6** | 0.9025 |
| + switch budget 2, min dwell 3 h | +0.2344 | 0.0877 | **+85.6** | 0.9025 |
| + dew-point gate **15 °C, Green Grid WP#46 p.6** | +0.3253 | 0.1111 | **+118.8** | 0.9025 |
| + notice 3 h, skill 0.50 | +1.1106 | 0.2092 | **+405.7** | 0.9035 |
| + **unanchored**, four measured FG offsets rotated | −0.4272 | 0.2154 | **−156.0** | 0.9865 |

**N-56 reference +66.8 h/yr; ours +65.6 — within 1.8 %**, two independent implementations.
The switch budget and humidity gate **INCREASE** the agent's advantage (both hurt the reactive
incumbent more). **Unanchored costs ~562 h/yr** while coverage rises to 0.9865 — the bound stays
safe and pays in hours. **The old rows read +112.4 / +489.7 / −104.8; see §10 #49 and #53.**

## 6.4a The 12-axis sensitivity — three axes reverse the answer

`backtest.py` declared **eight** sweep lists and iterated **one**. `run_sensitivity()` now varies
**all 12 axes BASE declares**, 33 configs, and **`main()` exits 3 and writes NOTHING if any axis has
no sweep list** — verified by injecting a knob.

| axis | range h/yr | negative at | the measured mechanism |
|---|---|---|---|
| `bank_mode` | −3124.4 … +405.7 | `facing` | agent **refused 10,779 of 21,912** held-out hours; **7,142 were genuinely safe** |
| `anchor` | −156.0 … +405.7 | `none` | coverage **rose 0.9035 → 0.9865** vs a 0.90 nominal |
| `switch_budget` | −78.0 … +405.7 | `1` | incumbent **exceeded the budget on 212 of 913 days** (base: 28) and kept its hours |

🔴 **THE REFUSAL GUARD IS PRICED: −3,124 h/yr** where it fires. **The headline is conditional on the
bank sitting on the long facade.** `switch_budget=1` is **not a fair fight and it favours the
incumbent** — deliberate (methodology rule 3), now reported rather than discarded.

## 6.4b Session A — the present tense, and plan churn

`src/rolling.py`, `demo/rolling.json`. 913 held-out days, **CHRONOLOGICAL** split, 12 h horizon.

**`agent.plan()` was EXTENDED, not duplicated** (gotcha #12) with `start_switches`,
`start_dwell_owed`, `budget_reset_at`. Defaults reproduce the old behaviour exactly, so the browser
mirror, `plan_fast` and the 500-case test all still hold. **Each horizon hour is forecast at its OWN
lead with its own Mondrian margin** — 12 separate calibrations, mean margin **1.20 °C at 1 h to
5.38 °C at 12 h**.

| Over 21,879 re-plans and 240,252 horizon-hours | |
|---|---|
| **Re-plans that change NOTHING** | **94.08 %** |
| **Next-hour flip rate** (the hour the plant acts on) | **0.873 %** |
| Churn across the published horizon | 1.128 % |
| Executed free cooling | 14.72 h/day |
| Coverage, all 12 leads | **0.9141 – 0.9201, none below the 90 % nominal** |

🔴 **THE ATTRIBUTION IS NOT WHAT WE'D GUESS.** Removing the switch budget and dwell limit changes
churn by a factor of **1.001 — nothing.** **The stability comes from the FORECAST**, not the
constraints. **No commitment mechanism exists or is claimed** (N-44/45, N-50 both failed). This is a
*measurement* of stability, not a guarantee.

## 6.5 Session B — the multi-site engine, and four rejections that matter

**Five sites screened, three shipped.** Neither failure was detectable from OSM tags, wind data,
weather quality or the physics ranking:

| Rejected | Why | Detectable from data alone? |
|---|---|---|
| **santaclara** (Vantage CA2, then Digital Realty SJC34) | **ROOFTOP**, 2 of 2 pairs | ❌ best numbers of any metro: 53 tagged, 53.1 % exposure, 99.88 % coverage |
| **phoenix** (Mesa) | **NOT BUILT** — bare graded desert | ❌ tagged `data_center`, no name/operator |
| **dulles rank 1** (AWS IAD121 → IAD122) | **SOLVER REFUSED IT** — 4 % of the intake disc on condenser cells | ❌ the *cleanest* GRADE pair screened anywhere, clearance +1.000 |
| **dulles rank 2** (Digital Realty IAD44) | receptor **under construction**, source roof arrays | ❌ |

**Santa Clara's failure has a structural cause worth quoting:** it is a dense, expensive **retrofit**
market — multi-storey buildings on small parcels — so plant goes on the roof. **Our scope premise,
that FortyGuard's 2 m plane is the plane the equipment breathes, fits GREENFIELD campuses and not
dense retrofit markets.** A real, quotable limit on where this agent applies.

**Free vs paid, measured.** Geometry (Overpass), imagery (ESRI/USGS), weather (Iowa State ASOS) and
physics (576 GPU solves) are **all free**. Only the FortyGuard field costs 4,220. **`env_params` was
considered as a cheap coverage probe and DROPPED**: the earlier key's `activity_breakdown` prices it
at **2,900** — only 31 % below a heatmap, so paying to predict a heatmap is bad economics. **The
flagship call IS the coverage test.**

## 6.6 Session E — the solved plume, rendered

`src/export_plume_fields.py` → `demo/plume_field_<metro>_longest.json`. **72 real solved fields per
site** (5° step, matching `direction_table.json` exactly), cropped to the footprints + 160 m and
quantised to one byte per cell — **display compression only**, applied to nothing a decision touches.

**`audit.py` check 2d re-derives the intake average FROM THE SHIPPED FIELD** using the solver's own
obstacle-exclusion rule and requires it to match the audited rise:

| Site | Field-derived | Audited | Apart |
|---|---|---|---|
| ashburn 255° | 0.35315 | 0.35477 | **0.46 %** |
| chicago 240° | 0.40695 | 0.41156 | **1.12 %** |
| dulles 265° | 0.35674 | 0.35929 | **0.71 %** |

**Why a solved field and not a drawn cone:** N-35 measured our √x spread as the **outlier** against
an exponent of 0.805 on 67 Prairie Grass experiments — at these distances our plume is too **wide**
and **under-predicts rise by 5–25 %**, the unsafe direction. A hand-drawn plume would hide exactly
that. The panel says so on screen.

## 6.7 🔴 The ASOS resolution floor — a hard limit on what can be claimed

KIAD's five-year record holds **112 distinct temperature values**; **98 % are whole degrees
Fahrenheit**, so effective resolution is **0.5556 °C**. Recirculation worst bearing 0.3550 °C =
**0.64 grid steps**; the agent-vs-incumbent margin at zero notice 0.1948 °C = **0.35 steps**; the
conformal margin at 3 h notice 2.4636 °C = **4.43 steps**. **No claim resting on an effect below
~0.55 °C is validatable against this record.** Independent support for leading with the forecast.

## 6.9 Session D — the reasoning tape, and how it is proved not to be a script

`src/ticker.py`, `demo/ticker.json`, the panel *"The loop, thinking out loud"*.

**The whole argument in one sentence: NO TEMPLATE IN `ticker.py` MAY CONTAIN A LITERAL DIGIT.**
`literal_digits()` strips every `{…}` field out of a template and fails on any digit left over —
at import time, so a hand-written number cannot survive to a test run, let alone a screen. **29
templates, 0 with a digit.** Run the project's own point-at-the-constant test on it and it comes
back empty.

`verify()` then adds four more, each for a defect this project has committed:

| | |
|---|---|
| **V1** no literal digits | #67 — four hard-coded narratives asserted false measurements |
| **V2** exact payload match | every placeholder has a value **and** every value is shown; an unused number is one computed and quietly hidden |
| **V3** every digit traced | remove each rendered value from the **shipped** text; no digit may survive |
| **V4** real execution order | stage numbers ascend and **all seven appear** |
| **V5** independent re-derivation | **23 of 71** system-tape numbers recomputed from a *different field written by different code*. **The other 48 are only read back, and the panel says so** |

**The templates are SHIPPED in `ticker.json`, so the browser owns no phrases at all** — it renders
the same strings against a payload it computes live. `verify_browser_ticker.js` therefore compares
**2,037 rendered sentences across 291 tapes and all 12 hour branches, character for character, 0
mismatches.** `gen_ticker_cases.py` **searches all 1,670 (case × config × hour) tapes for a covering
set and exits non-zero if any branch is unreachable.**

**1,002 hour-tapes verified in Python, 0 failures.** The per-hour tape is **recomputed in the
browser for whatever hour and configuration is selected** — its default hour is *computed* as the
tightest one (bound closest to the limit), because defaulting to index 0 showed a March midnight
where every gate passes by 14 °C.

🔴 **READING THE PRINTED TAPE CAUGHT FOUR ERRORS THAT NO CHECK WOULD HAVE** — see §10 #73–#76.
That is why `ticker.py main()` prints the whole tape.

## 6.10 🔴 Session D's three defects — the tape was built on broken stages

**1. STAGE 5 HAD NO NUMBERS AT ALL, and had not since it was written.** `run_cases` read the
per-hour bound as `row.get("bound_c|longest|sensor|anchored|0.50|3") or [None] * H`. **Nothing in
the tree ever wrote that key** — `_day_series` is not built until *after* the sweep that computes
the bound. So the `or` fired every time, `bms_commands` formatted `"%.3f" % nan`, and **all 37
shipped command rows carried `bound_c: null` and the words "upper bound on intake nan C"** —
**100 % of the ACT stage's output**, while §2.2 said each row "carries its own numbers".
Nothing caught it: `check_nan_writers` looks for `allow_nan`, and the file was valid JSON because
`json_safe()` had dutifully turned the NaN into `null`.
**Fixed** with `bound_series_key()` used by writer and reader, a hard `RuntimeError` where the
default was, a non-finite guard inside `bms_commands`, and **`audit.check_act_stage`**, which
rebuilds all 37 bounds from the shipped day-series inputs — **max |Δ| 0.00e+00 °C**, bounds
3.683–29.510 °C.

**2. THE BROWSER'S UNANCHORED DECISIONS DISAGREED WITH THE AGENT ON 2,588 OF 8,064 CONFIGURATIONS
(32.1 %).** Two causes: `decide()` used **one fixed worst-magnitude offset** (−3.7127 °C) for every
scenario where `agent.py` **rotates the four measured offsets with a leave-one-out conformal fit**,
and it **added no level margin at all**. It also **subtracted the dry-bulb offset from the
dew-point channel**, where no measured FortyGuard dew-point offset exists — closing the humidity
gate on **1,541** configurations on its own.
**One constant offset is the exact oracle #48 records: one offset across 1,826 days gave
+450.9 h/yr where the four rotated gave −156.0.** The retracted construction was live in the UI.
**Fixed:** the offsets and their leave-one-out margins are computed **once** in `agent.py` and
shipped as `trace.cases.fg_offsets`; `decide()`, `state_from_trace()` and `ticker.py` all read
them; a **FortyGuard level day** control selects which measured day applies.

| the four measured offsets, leave-one-out | offset °C | margin from the other 3 days |
|---|---|---|
| 2026-08-12 | −0.8396 | +0.1520 (clamped) |
| 2026-08-13 | −0.8115 | +0.1520 (clamped) |
| **2026-08-15** | **+0.1520** | **−0.8115 — NEGATIVE, so the bound sits UNDER the truth** |
| 2026-08-16 | −3.7127 | +0.1520 (clamped) |

**3. THE RETRACTED HEAT-ABSORPTION CLAIM WAS STILL IN SIX SOURCE LOCATIONS**, eight days after the
solver stopped absorbing heat — including **`trace.json`'s `physics_provenance.known_defect`**,
which ships to the demo folder. **Nothing rendered it**, so this is not a repeat of #56's UI
regression, but it shipped. Corrected in **both solver copies** (kept byte-identical so
`check_physics_not_drifted` still passes), `agent.py` ×3 and `direction_sweep.py`, with the
retraction left visible. `warp_solver.py` and `solver.py`'s inline comment were already correct.

**And a tolerance that was doing a registry's job:** `audit.py` checked the worst plume rise against
`direction_table` with a **5e-4** tolerance — wide enough to hide that **`direction_sweep.py` solves
one median wind speed (0.35477 °C) while `agent.rise_table()` maxes over a 72 × 8 grid
(0.35497 °C)**, and that the published **0.3550** is the second. **Now two registry lines at 1e-5
each, plus an identity that both pipelines must find the worst bearing at 255°.**

## 6.11 Session F — the conformal machinery, derived in the browser

Panel *"How the bound is built — the arithmetic, run in front of you"*, plus
`cfQuantileIndex` / `cfAttainable` / `cfMinN` / `cfSplit` in `index.html` and
`verify_browser_conformal.js`.

**Nothing in this panel is a displayed number — it is all derived, live.** α and *n* are controls, and
the browser recomputes **k = ⌈(n+1)(1−α)⌉**, the clamp flag, the ceiling **n/(n+1)** and
`min_n_for(α)` on every change.

**Why this earns exact equality rather than a tolerance:** both languages run identical IEEE-754
operations in identical order, so any difference would be a real divergence. **The fixture grid walks
*n* across every 1/α boundary** — the only place `ceil` could plausibly land on the other side.
**789 assertions, 0 mismatches**, including **60 residual arrays containing NaN** (which must be
dropped, not sorted) and **all 13 bounds the artefacts actually ship**.

**The panel's argument, which is the clearest statement of the project's headline failure:**

| regime | n | ceiling n/(n+1) | is the shortfall arithmetic? |
|---|---|---|---|
| the four real FortyGuard days | **4** | **80.0 %** | **YES, entirely** — ⌈(n+1)(1−α)⌉ = 5 exceeds n, so there is no such order statistic and the largest is used. **90 % is not reachable, and no code change reaches it** |
| the twelve per-lead bounds | **≥ 21,838** | **99.995 %** | **NO, not at all** — coverage runs 91.41–92.01 %, none below nominal |

**Same machinery, opposite regimes**, and the panel says which is which. It also **checks itself on
screen**: the browser prints its own k and margin beside the ones `conformal.py` wrote, with the
difference — **0.0e+0 °C**.

**The 12 per-lead bounds are rendered for the first time** — `rolling.json` shipped them since
Session A and nothing displayed them. Margin **0.81 °C at 1 h → 7.06 °C at 12 h**.

**And what is NOT claimed:** full conditional coverage is **provably impossible** distribution-free
(Barber, Candès, Ramdas & Tibshirani, *The limits of distribution-free conditional predictive
inference*, Information and Inference **10**(2), 2021). The panel states that, names
**Mondrian by hour of day** as what shipped, and quotes the lift it buys — worst hour
**73.14 % → 87.94 %**, hours under nominal **6 → 5 of 24**.

## 6.12 Session G — money, and the three qualifications that all point the same way

`src/money.py`, `demo/money.json`, the panel *"What it is worth in money"*, and
**`money-sources.md`** in the root, which holds the verbatim quotes and the fetch method for every
document. **Read that file before quoting any dollar figure.**

**THE UNIT IS PER MEGAWATT OF IT LOAD.** This project has never measured a data centre's size, and
inventing one would be a hard-coded constant that multiplies the headline. A reader who knows their
own IT load multiplies once. **Never say "saves $X million" — there is nothing here to multiply by.**

**Both conversion factors are SWEPT over published values, neither is chosen.** 4 prices × 4 chiller
efficiencies × 38 hours rows = **608 cells, nothing collapsed.**

| the sources, each DOWNLOADED AND PARSED HERE | what it gave |
|---|---|
| EIA, *2024 Total Electric Industry — Average Retail Price*, forms EIA-861 (PDF, read with `pypdf`) | **VA commercial 8.72**, VA industrial 8.99, **IL commercial 11.81** ¢/kWh |
| EIA **Table 5.6.A**, May 2026 (`.xlsx` **parsed as a zip of XML** — no spreadsheet library, no summarising model) | **VA commercial 10.84**, VA industrial 10.53, IL commercial 15.36 ¢/kWh |
| **PNNL-29674** p. 221, Table 82 = ASHRAE 90.1-2019 Table G3.5.3 (**PDF page 236 printed in full and read in place**) | water-cooled **> 300 tons: centrifugal 0.576 kW/ton FL, 0.549 IPLV**; screw/scroll 0.639 FL, 0.572 IPLV, at ARI 550/590 |
| **LBNL 2024 US Data Center Energy Usage Report** (all 79 pages extracted and grepped) | **PUE 1.4 in 2023, 1.15–1.35 by 2028 — CONTEXT ONLY.** It states PUE and **never states a chiller kW/ton, COP or IPLV**, verified by grepping every page |

**Why PNNL and not ASHRAE directly:** 90.1 is paywalled; PNNL-29674 is a **free DOE
national-laboratory publication reproducing the requirement tables**. The standard's values at one
remove, **and the remove is stated**.

**The arithmetic, per MW of IT load:** 1 ton = 12,000 Btu/h = **3.5168528 kW** (a definition, the one
step with no PDF to open), so 1 MW = **284.345 tons**, and the chiller draws **156.1–181.7 kW**.

| five-year ladder step | h/yr | kWh/MW-IT | $ /MW-IT/yr at VA 8.72 ¢ + 0.576 kW/ton |
|---|---|---|---|
| N-56-like: notice 0, no constraints | +65.6 | 10,746 | **$937** |
| + switch budget 2, min dwell 3 h | +85.6 | 14,022 | **$1,223** |
| + dew-point gate 15 °C | +118.8 | 19,460 | **$1,697** |
| **+ notice 3 h, skill 0.50 — the shipped configuration** | **+405.7** | **66,439** | **$5,794** |
| + unanchored, 4 measured offsets rotated | **−156.0** | −25,554 | **−$2,228** |

**The worst cell anywhere in the sweep is −$67,045/MW-IT/yr** at `bank_mode = facing` — the refusal
guard firing. **It is on screen.** `money.py:selftest` has a case asserting a negative hours row
produces a negative saving, because a dropped sign there would turn the agent's worst result into a
win.

🔴 **THREE QUALIFICATIONS, AND ALL THREE MAKE THE REAL NUMBER SMALLER:**
1. **COMPRESSOR ENERGY ONLY.** Fans, chilled-water pumps, condenser pumps and tower fans keep
   running, and an airside economizer moves **more** air — **fan power can RISE.** The unmeasured
   term has the **opposite sign**, so this is an upper bound.
2. **CODE MINIMUM IS THE OPTIMISTIC END.** 90.1 is a *floor*; hyperscale plants beat it, and a better
   chiller saves less per hour switched off.
3. **STATE-AVERAGE TARIFFS, not the site's.** A Loudoun County campus buys on a large-general-service
   contract that is not public.

**All seven limits are rendered on the page FROM `money.json`'s `not_claimed` list**, not written in
the HTML — so a limit cannot be dropped from the screen while staying in the file (#56).

**A self-test caught my own arithmetic, not the code's:** three hand-computed expectations were wrong
because they were derived from a *rounded* intermediate. The expectations are now produced with
`decimal` at 30 digits in a separate process. **#78's tally: checks wrong 11, product wrong 13.**

## 6.8 Other standing results

**N-49 fault detection PASSED** — removing weather: 79.7 → 0.03 d (+75.6 σ); sequential vs threshold
57.5 → 2.67 d (+52.6 σ). · **Emergent caution**: ensemble spread 27× wider at the geometric edge with
**no coded plume rule anywhere in the source**. · **N-49b FAILED P5** as pre-registered. · **Stability
over 5 real years**: 43,708 h classified — E 24.7 % / F 19.1 % / C 17.9 % / D 16.2 % / B 11.3 %. ·
**N-55 reproducibility**: same window re-requested returned **17,862 / 17,862 tiles byte-for-byte
identical**, max |Δ| **0.00000000 °C** — which is what lets the demo run offline. · **N-35 Prairie
Grass**: exponent **0.805** on 67 experiments (§10 #45). · **Solver verification**: V1 diffusion
0.00 % ✅, V2 conservation 0.00 % ✅, **V3 grid convergence FAILED AS WRITTEN** (order unestimable —
the intake disc holds 6/22/80 cells at dx=20/10/5, so the operator is grid-dependent), V4 obstacle
absorption 0.0 % ✅.

---

# 7. THE ARCHITECTURE — file paths and function names

## 7.1 `src/agent.py` — the loop

`python agent.py run | cycle | cases`. Writes `demo/trace.json`, `scenarios.json`, `field_*.json`,
`rise_table_*.json`.

- `PLANT_ENVELOPE` — **every decision-shaping number, swept, never chosen**: `limit_c` [18,21,24,27]
  · `switch_budget` [1,2,4] · `min_dwell_h` [1,3] · `notice_h` [0,1,3,6] · `bank_mode`
  [longest,facing] · `anchor` [none,sensor] · `dewpoint_limit_c` [None,15,18] · `aq_limit_idx`
  [None,73.5]. Plus `FORECAST_SKILL` [0,0.5,0.9]. **120,960 scenarios.**
- `load_hours(with_dewpoint=False)` — the ONE loader for the 43,763-hour record.
- `rise_table(mode)` — 576 GPU solves, cached full-precision; `emission_point()` marches out of the
  facade (§10 #36); `_is_downwind()` — **identical to `direction_sweep.py:255`**, must stay so.
- `conformal(res, alpha)` — **delegates to `conformal.split_conformal`**; one implementation only.
- `plan(safe, switch_budget, min_dwell_h, start_mode, start_switches, start_dwell_owed,
  budget_reset_at)` — the DP. **Maximise free hours subject to a hard safety constraint**, so no
  cost weights exist. **The last three args are Session A's rolling extension; defaults reproduce
  the original exactly.**
- `reactive_incumbent(...)` → `(modes, free, switches, over)`; `over` counts budget violations.
- `plume_uncertainty_terms(mode)` — lazy import (circular otherwise). **Disables the plume term
  rather than guessing if calibration is missing.**
- `_day_series(...)` — **ships the browser its inputs at FULL PRECISION** (§10 #44).
- `json_safe(o)` and `allow_nan=False` on every dump — §10 #43.
- `check_physics_not_drifted()` — MD5s `physics/solver.py` against `testing/solver.py`.
- **NEW:** an `all_mechanical` block in the trace — **43.7 % of 120,960 scenarios declare ZERO
  free-cooling hours** (52 % at 18 °C, 37 % at 27 °C). The UI needs this to explain itself (§8.3).

## 7.2 `src/conformal.py` — the statistics (20/20 self-tests)

`quantile_index` · `attainable_coverage` · `min_n_for` · `split_conformal` · `class Mondrian`
(**flags every pooled fallback**) · `convolved_upper` (**states its independence assumption**) ·
`class NormalizedConformal` (CQR) · `class ACI` / `class DtACI` · `joint_upper` ·
`coverage_by_group` (**always returns the worst group**). `python conformal.py` runs the suite.

## 7.3 `src/environment.py` — the gates

`station_pressure_pa` · `sat_vapour_pressure_hpa` · `rh_from_dewpoint` · `wet_bulb_stull` (returns a
**validity mask**) · `wet_bulb_reference` (PsychroLib) · `enthalpy_kj_kg` · `load_env_params` ·
`cloud_fraction` (**corrects the percent-vs-octas defect**) · `stability_from_fortyguard` ·
`air_quality_series` · `contamination_gate`. `DEFECTIVE_FIELDS` names the two fields we refuse.

## 7.4 `src/plume_uncertainty.py`

`spread_table(mode, sigma_dir)` — resampled from the rise table, **no new PDE solves** ·
`lookup_spread` · `build_calibration` · `calibrate`. Ships **σ_dir = 72°**, the pessimistic end of a
measured 47–72° range; both ends in `demo/plume_uncertainty.json`.

## 7.4a `src/ticker.py` — the stage-event tape (Session D)

`python ticker.py | selftest`. Writes `demo/ticker.json`.

`fmt_value` / `render` / `placeholders` / **`literal_digits`** — the anti-fake guard, three lines
long on purpose · **`check_no_literal_digits()` runs at IMPORT time** · `SYSTEM_TEMPLATES` (17) +
`HOUR_TEMPLATES` (12), **and the tuple's order IS the loop's order** · `event()` · `system_stream()`
reads artefacts only, so there is no second code path · `hour_stream()` — mirrored by `tickerFor()`
in `index.html` · `_rederive_table()` — **says which numbers have an independent path and which do
not** · `verify()` → `(failures, {rederived, read_back_only})` · **`selftest()` — 15 cases, and it
must pass before the module is allowed to judge anything.**

**The formatter supports exactly four specs** — `""`, `","`, `".Nf"`, `"+.Nf"` — because a
JavaScript mirror big enough to have its own bugs defeats the purpose. **A number passed with no
spec is an error, not a default.**

## 7.5 `src/explain.py` — stage 7

`gates_for_hour` · `flip_distance` · `explain_hour` · `explain_schedule` · **`verify()` — re-runs the
agent to check every claim** · `state_from_trace`. Seven binding constraints; measured distribution
across 1,336 hours: dry-bulb 46.7 %, none 32.6 %, **dew point 11.1 %**, **refusal 6.6 %**, **switch
budget 2.8 %**, air quality 0.1 %, **minimum dwell 0.1 % (1 hour in 1,336)**. **The last two are the
ones a thermostat cannot produce, and they are nearly vacuous — say so.**

## 7.6 `src/backtest.py` — five years

`plan_fast` (+ `_verify_dp_agreement` against `agent.plan`) · `build_state` · `split_days` ·
`persistence_shift` · `fit_bounds` · `score_config` · `run_aci` · `run_mondrian_audit` ·
`run_n56_audit` · **`sensitivity_axes` / `run_sensitivity`**. Gates on the **sourced**
`dewpoint_limit_c`. `python backtest.py all | n56 | sensitivity | mondrian | aci`.

## 7.6a `src/rolling.py` — the present-tense controller

`hour_numbers(keys)` — **absolute hour index, so leads are measured in HOURS not array steps**
(§10 #63) · `build_lead_bounds` — **12 separate Mondrian calibrations**, drops rows whose real gap
isn't N (exactly 46×N per lead) · `rolling_safety` · `simulate` — acts only on the first slot,
carries state across boundaries, **raises if handed a non-contiguous span** (§10 #60) · `churn` ·
`summarise`. `SPLIT_MODE = "chronological"` is **required**, and the written label derives from it.

## 7.6b `src/metros.py` — the site registry

`METROS` (5 entries) · `metro_key()` reads `METRO`, defaults `ashburn` · `metro()` ·
`candidates_path()` · `weather_file()` **derived from the station id** · `weather_path()` ·
`geom_path(name)` — **ashburn keeps unsuffixed names**, others get a prefix · `readiness(k)` —
gates on geometry **AND** a data-centre-to-data-centre pair **AND** `MIN_WEATHER_COVERAGE = 0.95` ·
`export_manifest()` → `demo/sites.json`, which additionally requires an **in-scope architecture
verdict for the committed pair** (§10 #69).
`python metros.py` lists readiness; `python metros.py --manifest` writes the manifest.

## 7.6c The multi-site helpers

- **`discover_dc_clusters.py`** — Overpass query for `telecom=data_center` / `building=data_center`
  by state; grid-clusters and emits `suggested_bbox`. **Use its output verbatim** (§10 #64).
- **`fetch_weather.py`** — 60 month-chunks per station, parsing carried over verbatim from
  `testing/fetch_n51_fullyear.py`; reports per-year counts and a lone-high-outlier check.
- **`annotate_screen.py`** — draws the source (red) and receptor (blue) footprints and the plume
  direction onto each screening frame. **Without it nobody can tell which two of ~10 buildings are
  the pair.**
- **`export_plume_fields.py`** — 72 solved fields per site + the obstacle mask.

## 7.7 `src/audit.py` + `src/run_all.py`

`check_dead_code` · `check_nan_writers` (+ **2b** strict-JSON, **2c** `check_css_comments`,
**2d** `check_plume_fields`) · `check_decision_precision` (source-level) ·
`check_duplicate_constants` (asserts **agreement**) · **`check_retired_constants`** (AST-based, so
prose documenting a retirement is not a false positive; **the detector passes its own 6-case test**)
· **`check_act_stage`** (stage 5's 37 command bounds, rebuilt from the shipped inputs) ·
**`check_stage_events`** (the reasoning tape's digit scan, re-run against the SHIPPED file)
· **`check_published_numbers`** — **62 figures re-read from emitted JSON**, including all five ladder
rows and **two cross-path invariants** (the ladder's rows 4 and 5 must equal the sensitivity sweep's
base and `anchor=none` rows **to full precision**) · `check_self_tests` · `check_cross_language`.
**`python run_all.py`** = plume → agent → backtest → rolling → manifest → explain → fixtures →
audit, **~97 s**.

## 7.8 `demo/` — the interface

`index.html` (~100 KB, light + dark, no build step). Renderers: `drawHeadline`, **`drawMap`** (the
only networked panel), **`buildSitePicker`** / **`loadSite`**, **`drawPlume`**, `drawField`,
`drawAerial`, `drawSched`, `drawExplain` (+ **`drawZeroNote`**), `drawBound`, `drawDial`, `drawCov`,
`drawCoverageTiles`, `drawLadder`, `drawLimits` (+ **`refusalLimits`**). `decide()` re-runs the agent
in the browser; `explainHour()` mirrors `explain.py`.

**Five cross-language tests, each EXTRACTING functions from `index.html` rather than copying:**
`verify_browser_agent.js` (500 scheduling cases) · `verify_browser_decision.js` (**20,160 configs,
both anchors, both banks, bound included — and it fails if either anchor goes uncompared**) ·
`verify_browser_explanation.js` (**1,336 hours**) · **`verify_browser_ticker.js` (35 formatter
values + 2,037 stage-event sentences, character for character, all 12 hour branches)**.
**`verify_browser_conformal.js`** (**476 (n, α) grid points + 300 residual arrays + all 13 real
shipped bounds = 789 assertions, EXACT equality, 0 mismatches**).
`gen_dp_cases.py`, `gen_ticker_cases.py` and `gen_conformal_cases.py` write the Python-scored
fixtures.

**Session D's renderers:** `drawTicker` · `tapeHTML` · `tickerFor` (mirrors `ticker.hour_stream`) ·
`tkEvent` / `tkRender` / `tkFormat` / **`tkFixed`** (mirrors Python's tie-to-even rounding).
Clicking `#sched` drives the tape's hour.

**Run it:** `cd INTAKE-ARBITER/demo && python -m http.server 8000` → `http://localhost:8000`.
**`file://` will NOT work** — browsers block `fetch()`, and the page says so in red.

---

# 8. HOW TO PROVE IT STILL WORKS

```bash
cd INTAKE-ARBITER/src && python run_all.py      # 12 steps, ~97 s, zero API calls, non-zero on failure
cd INTAKE-ARBITER/src && python ticker.py       # prints the whole tape -- READ IT, see #76
cd ../demo && python -m http.server 8000       # then open http://localhost:8000
cd ../../testing && python test_n26_coverage.py dryrun   # free: what the collector would do now
```

## 8.1 Screenshot and actually LOOK at the page

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu \
  --hide-scrollbars --virtual-time-budget=30000 --window-size=1280,17000 \
  --screenshot="$(pwd -W)/_shot.png" "http://localhost:8000/index.html"
```

Then read `_shot.png` with the Read tool. **PIL 11.3.0 is installed** — crop the tall page into
slices rather than letting Read downscale a 7,400 px page into mush. **Delete the PNGs afterwards.**

**Dark theme:** copy `index.html` to a temp file with `data-theme="dark"` injected into `<html>`.

**⚠ Narrow viewport: `--window-size=390` IS A TRAP (§10 #58).** Chrome clamps the window to ~504 px
and just crops the image. Serve a wrapper holding `<iframe src="index.html" width="390">`. Compare
the iframe document's `scrollWidth` against its `clientWidth` and **ignore elements inside a scroll
container**. Last verified: **zero overflow at 390, 768 and 1280 px, both themes.**

## 8.2 Where the numbers live

Every published figure is in `audit.py:check_published_numbers`. **A number in a document that no
test re-reads is a number that will drift** — four instances so far (§10 #67).

## 8.3 The demo must never look inert

**43.7 % of the 120,960 swept configurations declare zero free-cooling hours** — correct physics on a
35 °C day. `drawZeroNote()` states the peak intake, how many hours were over the limit, how much
higher the limit would need to be, that it is one of the 43.7 %, and the annual total anyway.
**If you change the defaults, re-check that an all-mechanical view still explains itself.**

---

# 9. NEXT STEPS — ONE SESSION REMAINS, and it is the one that can disqualify the entry

**DONE:** Sessions 1–3 (plume uncertainty, explain, audit) · **4** (UI pass + the invented-constant
fix) · **0** (collector hardening) · **A** (present tense + churn) · **C** (annual headline + the
"no" days) · **B** (multi-site) · **E** (plume simulation, site picker, map) · **D** (the reasoning
tape + three defects, §6.9/§6.10) · **F** (conformal made visible, §6.11) · **G** (money,
sourced, §6.12).

**Order confirmed by the user 2026-08-20: D → F → G → H as written.**

## 9.1 SESSION H — the whole remaining risk, broken into what is blocked and what is not

**Deadline Aug 30 23:59 GST. As of 2026-08-20 the code is done and NONE of the submission
requirements exist.** Three of five requirements are met (working demo, documentation, API usage
partly recorded); **the public repo, the collaborator, the live link and the video are not.**

| # | Item | Blocked on | Notes |
|---|---|---|---|
| H1 | **Public GitHub repo** | 🔴 **USER — rule 11** | `gh` is NOT installed and no remote is configured. Branch must be renamed `master` → `main`. **Re-run the full-tree key scan first** — the exact script is in §12.1 and it currently reports 0 hits outside the two gitignored `.env` files |
| H2 | **`fortyguard` as collaborator** | 🔴 **USER** — needs H1 | A hard submission requirement |
| H3 | **Live demo link** | 🔴 **USER** — needs H1 | GitHub Pages serves `demo/` as static files with no build step, which is exactly what this demo is. **The only networked panel is the map, and it already fails soft** |
| H4 | **2–5 minute video** | 🔴 **USER** | Nothing here can record one |
| H5 | **Downloadable report (CSV/PDF)** | ✅ **not blocked** | Every number already exists in `demo/*.json`. A `src/report.py` writing a per-site CSV + a printable HTML is a self-contained job |
| H6 | **API-usage document** | ✅ **not blocked** | `fortyguard-api-findings.md` is 64 KB of it already; needs a short front section stating: **10 paid calls, 42,200 credits, 2.11 %**, which endpoints, and the outage report |
| H7 | **Repo-size decision** | ✅ **not blocked** | **194 MB**, of which `data/imagery/` is ~50 MB of screening PNGs and `scenarios.json` is 28.8 MB. Under every GitHub limit. **Decide deliberately whether the imagery ships** — it is the evidence behind "five screened, two refused", which is the single most credible thing in the project |

**H5, H6 and H7 can be done without lifting rule 11, so do those first.** H1–H4 are the user's.

⚠ **A judge will open the demo before reading anything.** `demo/README.md` must say
`python -m http.server` in its first line, because **`file://` blocks `fetch()` and the page will
show nothing but a red error.**

**Also outstanding, cheap, and worth doing:**
- 🔴 **`PLAN.md` is not updated for Sessions A, B, E, D, F or G.** It is the **citation-bearing
  design record** and rule 5 attaches to it, so this is the largest documentation debt in the
  project. Session G's citations are in **`money-sources.md`** instead, which is complete and
  standalone — but PLAN.md does not yet reference it.
- The **diag62 outcome leg** (one call, ~4,220) would give a **5th measured level offset** —
  strengthening the n=4 level term `backtest.py` rotates across 1,826 days. **NOT** a 5th coverage
  pair: its window is 19:00 and the series fixes 14:00 (§10 #70).
- **Santa Clara** has 5 unscreened frames; **Phoenix** has two unscreened clusters (Chandler:
  CyrusOne/Digital Realty/H5, KPHX 20.6 km; Goodyear: Microsoft/Vantage, KPHX 33.9 km).

**Two things only the user can do:**
1. **Send the REWRITTEN FortyGuard message** — §4.3. The drafted one is superseded.
2. **Lift rule 11** so the repo can go public. **This is a hard submission requirement.**

---

# 10. GOTCHAS — every one of these actually bit

## Carried forward

1. **⚠ THE 9-HOUR TIMEZONE BUG.** `heatmap` reads `start_time` in the **AOI's own local zone** and
   echoes no timestamp. **Always use `common.site_window()` / `common.lead_hours()`**; they raise on
   a naive datetime. **⚠ `common.SITE_TZ_NAME` is HARD-CODED to `America/New_York`** — for a
   non-Virginia AOI you must pass the zone explicitly, as `testing/fetch_chicago_field.py` does.
2. **Out-of-horizon requests return HTTP 200 + `completed` + ZERO tiles.** Always
   `common.assert_non_empty()`. This signature has **at least five distinct causes**, one of which
   was a 30-hour outage (§4).
3. **`/tmp` is unreliable here.** Use the session scratchpad or real files under `testing/`.
4. 🔴 **Bash heredocs mangle `\n` and backticks inside Python strings.** Hit repeatedly. Also
   **`b'''…'''` is a BYTES LITERAL, not an assignment** — that cost three failed patches. **Use the
   Write tool for multi-line code and the Edit tool for repairs.**
5. **Windows console is cp1252** — use plain ASCII in `print()`. A `⚠` crashed `fetch_weather.py`.
6. **Background command output capture is unreliable.** Prefer foreground with a generous timeout;
   write progress to a file if the job must be backgrounded.
7. **WebFetch cannot read most PDFs**, and several sites 403 it.
8. **`statistics.pstdev` vs `stdev`** — for a *sample* use `stdev` (÷ n−1).
9. **Naive rounding splits one lead leg into two buckets.** 9.41 h and 9.50 h are the same leg.
10. **`setdefault` before parsing creates empty entries.** Parse every field BEFORE touching the dict.
11. **Sign conventions in inverse problems.** If days are `forecast = true + error`, invert
    `true = forecast − error`.
12. 🔴 **Never let two code paths compute one quantity two ways.** Bit repeatedly — #26, #44, #46.
13. **NOAA ASOS via Iowa State rate-limits and 503s.** Fetch in month chunks, save incrementally.
14. **An axis-aligned bbox badly misdescribes a rotated building.** Save `ring_m` and a rotated
    `min_area_rect()`. **`width_m`/`height_m` in the candidates file are BBOX EXTENTS, not vertical
    height** — OSM has no heights, and the file's own caveat says so.
15. **Place equipment on facade EDGES, not vertices.**
16. **Vertex-to-vertex distance overstates a gap.** Use `ring_gap()`.
17. 🔴 **THE ORACLE LEAK.** N-50's DP action rule compared the **realised** cost, which contains the
    outcome. **A policy's action rule must use PREDICTED cost only.**
18. **A tuning grid must span the variable's range.** Print what fraction exceeds the maximum.
19. **Check the inequality direction against the signal's slope.**
20. **FortyGuard validates `threshold`, NOT `threshold_temperature`**, and **silently drops unknown
    body fields.** Proven for zero credits by forcing a 422 with `granularity: 7`.
21. **`/v1/heat_intelligence` leaks the API key in `download_link`.**
22. **Spec says `analysis` `maxItems: 5`; the server enforces 2.**
23. **`analytic_type: persistence` returns values that cannot be a duration.**
24. 🔴 **ASOS temperatures are whole degrees Fahrenheit** — a **0.5556 °C grid. Never claim a result
    on a band narrower than that.** §6.7.
25. **Raw persistence error contains the diurnal cycle.** De-bias per lead AND per hour-of-day.
26. **⚠ STALE, CORRECTED.** Obstacles are **TRANSPARENT** — heat passes through a building, measured
    **0.0 % absorbed**. That conserves heat exactly and is *sourced* (ASHRAE Ch. 46 corrects only a
    **hidden** intake). **That — not absorption — is why `path_blocked()` refuses.**
27. **`env_params` reports a fixed `timezone: "GMT-5"`**, wrong in summer for a UTC−4 site.
28. **`build_site.py:verify()` runs V1/V2/V3 and refuses to write a site if any fails.** Keep that.
29. 🔴 **`.env.example` IS COMMITTABLE** — `.gitignore` deliberately re-includes it. **Verify with
    `git check-ignore -v`.**
30. 🔴 **A zero-tile `completed` response IS BILLED 4,220.** Confirmed repeatedly.
31. **A key's observed behaviour is not necessarily its documented behaviour.** **Verify, do not
    infer.**
32. **Difference `total_credits_used` around every paid call.**
33. **System / usage / plan-details endpoints are FREE.** Poll them before and after paid work.
    **`env_params` is NOT free — 2,900 credits**, derived from `activity_breakdown`.
34. **A negative diagnosis is worth paying for, but only once.** **Vary ONE variable per paid call
    and write the hypothesis down first.**
35. 🔴 **Before writing a cause into a document, tabulate every variable that differed between the
    compared calls.** Violated again in Session A — by the code written to prevent it (#55a).
36. 🔴 **A RAY THAT STARTS INSIDE A BUILDING REFUSES EVERYTHING.** March the emission point outward
    and print the distance. **A dramatic number from a guard is the first thing to distrust.**
37. **A pre-registered condition can be MET AND MEANINGLESS.** Report it met **and vacuous**.
38. 🔴 **A measurement operator can impose a hard geometric bound.** The intake disc reaches 50 m.
    **`MIN_GAP_M` is DERIVED and imported — and it was still WRONG, see #65.**
39. 🔴 **A boolean gate on a continuous quantity hides the failure it was added to prevent.**
    **`path_blocked()` needs no PDE solve, so MEASURE refusal instead of gating on a proxy.**
40. 🔴 **A FORECAST ERROR THAT DOES NOT GROW WITH LEAD IS AN ORACLE LEAK.** Anchor forecast error to
    a MEASURED baseline and **sweep skill**.
41. 🔴 **A pre-registered condition can be UNSATISFIABLE BY CONSTRUCTION.** Record it FAILED AS
    WRITTEN and state the repair.
42. 🔴 **NEVER BUILD A DEFECT CLAIM ON A CROSS-SOURCE ABSOLUTE LEVEL.** **Difference the thing
    first:** the product against ITSELF, or difference-in-differences.
43. 🔴 **PYTHON WRITES `NaN`; `JSON.parse` REJECTS IT — AND `json.load` ACCEPTS IT.** Every writer
    uses `json_safe()` and `allow_nan=False`. **A validator written in the producing language cannot
    see the consumer's rules.**
44. 🔴 **NEVER ROUND A NUMBER THAT A COMPARISON DEPENDS ON.** Bit twice in one day. Display rounding
    belongs in the view only; `audit.py:check_decision_precision` enforces it at the source.
45. 🔴 **A PASS CAN CONFIRM A LIMITATION.** N-35 passed — and what it confirms is that our √x plume
    shape is the **outlier** (measured exponent 0.805). We **UNDER-predict rise by 5–25 %** — the
    *unsafe* direction. **Read what a test validates, not just its verdict.**
46. 🔴 **A GROUP-CONDITIONAL BOUND CAN BE DOCUMENTED WITHOUT BEING USED.** Caught only by an
    end-to-end test comparing two implementations' *outputs*.
47. 🔴 **MY VERIFICATION CODE WAS BUGGIER THAN THE PRODUCT.** A tool that cries wolf trains you to
    ignore it. **Running tally: checks wrong 8, product wrong 10.**
48. 🔴 **A CONSTANT OFFSET IS LEARNABLE; A VARYING ONE IS NOT.** One offset across 1,826 days gave
    **+450.9 h/yr**; the four **measured** offsets rotated gave **−156.0**. **A bias that is constant
    in your simulation is an oracle.**
49. 🔴 **"IT'S SWEPT" IS NOT A DEFENCE IF THE VALUE IS INVENTED.** `wetbulb_margin_c = 3.0` was swept
    and still failed the point-at-the-constant test. Replaced by a **sourced** dew-point maximum —
    **15 °C, Green Grid WP#46 p.6** — which also revealed that our 27 °C top-of-envelope **is the
    same standard's dry-bulb maximum.**
51. 🔴 **A `completed` STATUS DOES NOT MEAN THE DATA IS THERE.** FortyGuard's own team documented it;
    `common.py:submit_poll()` now treats completed-but-empty as a reason to keep polling and reports
    `empty_completed_polls`. **It did NOT explain the blocker — a plausible vendor explanation still
    has to be TESTED.**
52. **CHROME IS INSTALLED, SO THE PAGE CAN BE SEEN.** §8.1.

## New across Sessions 4, 0, A, C, B, E

53. 🔴 **A FREE PERFECT SENSOR CAN HIDE INSIDE A CHANNEL NOTHING GATES ON.** The agent's humidity
    reading was exact while the incumbent's was dithered — a **0.0000 °C** margin. Harmless until the
    dew-point gate made it load-bearing, then it inflated the gate row **+118.8 → +206.4 h/yr**.
    **`margin == 0.0000` is the tell.**
54. 🔴 **A COMMENT CLAIMING A SWEEP IS NOT A SWEEP.** Eight lists declared, one iterated, behind a
    comment asserting the opposite. **A declared-but-unused sweep list reads as coverage.** Fixed
    with a guard that exits non-zero and writes nothing.
55. 🔴 **THE CODE I WROTE TO PREVENT A GOTCHA COMMITTED IT.** (a) The reversal explainer blamed a
    quantity **identical at the base case** — gotcha #35 verbatim. (b) The retired-constant scanner
    failed on prose *documenting* a retirement; it is **AST-based** now, with its own 6-case test.
56. 🔴 **A RETRACTION MUST PROPAGATE TO EVERY SURFACE.** The buildings-absorb-heat claim was live in
    the demo's **"Honest limits"** panel a week after retraction. `audit.py` re-reads 62 *numbers*, so
    a stale **sentence** is invisible to it. **Grep the whole tree, and prefer generating prose from
    data.**
57. 🔴 **I CAME ONE STEP FROM FILING A FALSE DEFECT REPORT AGAINST FORTYGUARD.** Their `stats_data`
    sat 0.08–0.56 °C below the `map_data` extremes in **8 of 8** responses — a textbook level offset.
    It was **our own field choice**: tiles carry `average_`, `min_` and `max_temperature`;
    `tile_centroids()` reads **max**, `stats_data` describes **average**, and their mean reproduces
    the average channel **exactly**. **Enumerate every channel their payload offers and prove you
    compared the same one.**
58. 🔴 **`--window-size=390` DOES NOT GIVE YOU A 390 px VIEWPORT.** §8.1. Also: comparing an element's
    right edge against `documentElement.clientWidth` can **never** detect horizontal overflow,
    because clientWidth grows with it. **Two wrong answers before the right one — measure the
    measurement.**
59. 🔴 **"EXHAUSTIVELY EXCLUDED" IS NOT "PERMANENT".** Seven zero-tile responses across two days, every
    competing explanation individually excluded — and it was a **vendor outage**. **I recommended
    against the 4,220-credit test; the user overrode it and was right.** (a) **A negative that repeats
    is evidence about a PERIOD, never a CAPABILITY.** (b) **Retiring a forward plan has a cost —
    demand a positive control.** (c) **When a cheap test can overturn your most load-bearing
    conclusion, run the test.**
60. 🔴 **A ROLLING SIMULATOR NEEDS CONTIGUOUS HOURS; AN ALTERNATING SPLIT LEAKS.** A 43,739-hour span
    containing **21,857 CALIBRATION hours**. **The tell was 28.5 free hours per day, impossible in a
    24-hour day** — a number outside its own physical range is the cheapest bug detector there is.
61. 🔴 **SCALING A CONFORMAL MARGIN WITHOUT SCALING THE FORECAST DESTROYS THE BOUND.** Coverage came
    out **0.73–0.79 on ALL TWELVE leads. 12 of 12 below nominal is a broken construction, not noise**
    — which is why coverage is measured per lead, not pooled. **Validity must be invariant to a swept
    axis, so sweeping the axis is itself the test.**
62. **A HARD-CODED LABEL OUTLIVED THE THING IT DESCRIBED.** `rolling.json` said
    `"split": "alternating"` after the code moved to chronological. **If a document field describes a
    code path, compute it from that path.**
63. 🔴 **A GUARD WITH A TOLERANCE BAND WAS HIDING A REAL BUG — the user spotted it by asking why the
    guard was needed at all.** The answer: the KIAD record has **61 missing hours** and **46 index
    pairs 2/3/5 real hours apart**, and leads were computed as **array-position distance**, so a slot
    labelled "3 h ahead" was really 5 h ahead and got the 3-hour margin — **silent under-bounding, in
    the unsafe direction.** Fixed with `rolling.hour_numbers()`; the guard is now an **exact
    identity**. **If you cannot say why a tolerance is not zero, you do not understand the quantity.**
64. 🔴 **I SUBSTITUTED MY OWN ARITHMETIC FOR A MEASUREMENT TWICE, ON THE SAME NUMBER.** A Phoenix bbox
    from memory returned a **shopping mall, a Dillards depot and a Walmart** — zero data centres. Then,
    having built `discover_dc_clusters.py`, I **re-derived** the bbox as centre ± 0.012° instead of
    using its `suggested_bbox`: still zero. **Having built the measurement, use its output.** Also:
    "did the fetch return buildings" passes for a mall — `readiness()` gates on **data-centre-to-
    data-centre pairs**. Positive control: the top cluster found anywhere was **VA with 106 tagged**,
    and its bbox contains our own committed site.
65. 🔴 **A DERIVED CONSTANT CAN STILL BE WRONG IF THE DERIVATION IS INCOMPLETE.** `MIN_GAP_M` was
    `standoff + radius` = 50 m and **omitted the condenser bank** — `strip_ring()` CENTRES the bank on
    the facade, so **10 m projects into the gap**. The gate passed a 54.7 m pair; two GPU builds later
    `assert_intake_clear()` refused: *"the disc would average the discharge it is supposed to
    measure."* Corrected to **60 m**, which explains every site — **and Ashburn's committed site clears
    by 0.3 m.** **The downstream guard was right where the upstream gate was wrong: that is the
    argument for having both.**
66. 🔴 **`select_site.py` AND `refusal_rank.py` ARE DESTRUCTIVE.** Both write their own top pick into
    `selected_site.json`; only `commit_site.py` applies the architecture veto. Running either "just to
    check" **replaced the committed AWS pair with the ROOFTOP-vetoed Digital Realty IAD35/36 pair —
    twice in one session.** **The §5 pipeline order is a requirement, not advice.**
67. **A HARD-CODED NARRATIVE ASSERTED MEASUREMENTS THAT WERE FALSE — four instances.** The "595 h/year"
    literal in the view; the ladder row labels; `rolling.json`'s split; and both
    *"which refuses 100 % of downwind bearings"* and *"rank 1 was VETOED as rooftop"*, printed
    unconditionally and false for Chicago. **If a sentence states a number, compute the sentence.**
68. **STATION PROXIMITY LOST TO RECORD COMPLETENESS, AND THAT WAS RIGHT.** KIWA was **2.7 km** from the
    Mesa cluster and rejected: **81.70 % complete, only 50.8 % of 2021**, plus a lone 54.0 °C reading
    against a next-highest of 46.0. A one-year probe: **KIWA 50.8 %, KCHD 61.5 %, KFFZ 99.1 %,
    KPHX 99.8 %, KSDL 99.7 %.** **24 hour-of-day groups cannot be fitted on a record that thin.**
    Nearest is not best; complete is best.
69. 🔴 **DATA READINESS IS NOT SCOPE.** The first `sites.json` marked **all five** sites offerable,
    because `readiness()` only asks whether the data exists — and Phoenix and Santa Clara pass all
    three data gates. **The picker would have offered exactly the two sites just refused by the imagery
    gate.** `offerable` now also requires an **in-scope architecture verdict for the committed pair**.
70. **A PAIR IS NOT A PAIR IF IT BREAKS THE SERIES' CONTROL.** DIAG-62's window is **19:00**; the N-26
    series fixes **14:00** so diurnal predictability is held constant, and hour-of-day dominates
    forecast error here (worst group 0.7314 vs 0.8794). Folding it in would contaminate the headline.
    Recorded under `off_series_observations`, deliberately outside `m["days"]`.
71. **AN ASYNC LOAD-ORDER BUG LOOKS EXACTLY LIKE A MISSING FILE.** `drawMap()` fired in
    `setTimeout(…,0)` after `boot()` — but `boot()` is async, so the map reported *"sites.json did not
    load"* while the picker beside it worked from that very file. **The failure path was right; the
    ordering was wrong.** Chained off `boot()`'s promise, still never awaited.
## New across Session D

73. 🔴 **`.get(key) or DEFAULT` IS HOW A WHOLE STAGE SHIPS NOTHING.** The key had never been
    written, the default was `[None] * H`, and the result was `nan` formatted into 37 command rows'
    prose plus `null` in the field beside it — **valid JSON, valid Python, 100 % of stage 5, and
    invisible to every existing check.** §6.10 #1. **A lookup with a default cannot fail, which
    means it cannot tell you it failed.** Where a value is *required*, raise.
74. 🔴 **A TEST THAT EXCLUDES A CODE PATH REPORTS PASS FOR IT.** One clause —
    `r[col.anchor] === 'sensor'` — kept `verify_browser_decision.js` at 2,016 configurations and
    hid a **32.1 %** disagreement on the other 8,064. It also pinned `bank_mode` to `longest`, so
    the refusal path was never compared either. **Now 20,160 configurations, and the test FAILS if
    either anchor setting ends up with zero rows compared.** Ask of every filter: *what does this
    stop me from seeing?*
75. 🔴 **`toFixed` IS NOT `format()`, AND THE DIFFERENCE IS ONE DIGIT WIDE.** Python rounds ties to
    **even**, JavaScript's `toFixed` rounds them **away from zero**: `0.125` at 2 dp is `0.12`
    against `0.13`, `2.5` at 0 dp is `2` against `3`, `-0.5` is `-0` against `-1`. Four of 35 probe
    values failed. Fixed by doing decimal string arithmetic on `toFixed(20)` — correctly rounded far
    beyond any rendered precision, and an exact tie terminates well inside it. **Enumerate the
    awkward values as fixtures; do not reason about them.**
76. 🔴 **READING THE OUTPUT CAUGHT FOUR ERRORS NO CHECK COULD.** The first tape printed
    (a) *"a widening of −0.0086 C"* — a hand-written word contradicting its own sign, in the module
    built to prevent exactly that; (b) `bound.mondrian` tagged **stage 4**, which V4 accepted because
    ascending order does not notice a mislabel; (c) *"23 hour-of-day groups"*, the day's hour count
    on a day missing an hour, where the sentence is about the **calibration's 24**; (d) *"0.0 % of
    the distance to the limit"* on an hour whose ambient was **already over** it — a guarded division
    reading as a measurement of nothing. **`main()` prints the whole tape for this reason.**
77. **THE BRACE COUNTER THAT EXTRACTS FUNCTIONS FROM `index.html` BREAKS ON A REGEX.** `/\{…[^}]*…\}/`
    contains one `{` and two `}`, so `extract()` stopped mid-function and the extracted source would
    not parse. `\x7B` and `\x7D` instead — **with a comment saying not to tidy it up.**
78. 🔴 **MY VERIFICATION CHECK WAS VACUOUS TWICE IN ONE SESSION.** (a) V3 scanned the
    **freshly-rendered** text rather than the **shipped** text, so it could only ever confirm the
    template — a digit hand-edited into the artefact would have been rendered out of existence before
    the scan. Caught by the module's own self-test. (b) The dark-theme screenshot check asserted
    `'data-theme="dark"' in html` **after** injection — and that string is already in the CSS, so it
    passed while the injection had silently missed the real `<html>` tag. The page rendered light and
    I nearly read it as dark. **Running tally: checks wrong 10, product wrong 13.**
79. **A DEFAULT SELECTION IS A CHOICE, SO COMPUTE IT.** The hour tape defaulted to index 0 and
    showed a March midnight where every gate passes by 14 °C — the loop looking trivial. It now
    picks the hour whose bound sits **closest to the limit**, found by search. Same class as the
    18 °C default two panels up.

## Carried forward, continued

72. **A CSS COMMENT CAN BE UNBALANCED AND SILENT.** Successive edits left **three `*/` against one
    `/*`**, feeding two paragraphs of English to the stylesheet. Browsers error-recover, so every
    screenshot and cross-language test passed. `check_css_comments` counts delimiters now.

---

# 11. METHODOLOGY RULES — keep following these

1. **No exponent, ratio or margin is EVER quoted without n, SE and a 95 % CI.**
2. **Pre-register pass/fail conditions in the test file docstring BEFORE running.** N-8, N-33, N-34,
   N-49b, N-50, N-54 P1, N-56 Q1 and **N-29 V3** all stand as FAILED. That is correct handling.
3. **Name a real, TUNED adversary.** Tune on training days, score on held-out, compare paired
   per-day.
4. **Include an anti-threshold guard.** N-9 v1 "won" by discovering a constant.
5. **A correctly-specified DP cannot lose to a policy inside its own search space** — but see #17.
6. **Retractions stay visible.** §2.3, `PLAN.md` §12.9, the PREREG amendment logs — **and every UI
   surface** (#56).
7. **Verify sources by opening them, not by trusting snippets.**
8. **When a guard refuses, that is the guard working. Do not route around it.** (#65 is the proof.)
9. **When a comparison spans two measurement systems, DIFFERENCE the thing first.**
10. **A claim must be checkable by re-running the code.** `explain.py:verify()`,
    `audit.py:check_published_numbers` and `check_plume_fields` are the pattern.
11. **NEW: prefer generating prose from data over writing it twice.** Four hard-coded narratives have
    now asserted things that were false (#67).

---

# 12. CREDENTIALS, API AND BUDGET

## 12.1 Where the key lives

- **`FORTYGUARD_API_KEY`** in `d:\FGHackathon\.env` **and** `d:\FGHackathon\INTAKE-ARBITER\.env`,
  read via **`testing/common.py:load_key()`**. **Never print, echo, log or commit its value.**
- **ASK the user before every paid call.** Standing rule, never waived.
- **Exactly one key is on disk**, the `Hackathon` plan key — both files hold the same value, verified
  by comparing SHA-256 fingerprints, never by printing them.
- **Re-run a full-tree key scan before any commit.** Session-B artefacts were scanned clean
  (the raw `diag62` and `chicago_field` fixtures included).

## 12.2 The plan — measured, not guessed

| Fact | Value |
|---|---|
| Plan | **`Hackathon`**, active, started Aug 18 2026, valid to Sep 22 |
| Credits issued | **2,000,000** |
| **Cost per heatmap call** | **exactly 4,220** — verified by differencing the meter, repeatedly |
| **Cost per `env_params` call** | **2,900** — from `activity_breakdown`, NOT free |
| `satellite` / `heat_intelligence` | 14,400 / 8,600 |
| **Daily limit** | **30 heatmaps/day** — the cap binds long before credits do |
| System / usage / plan endpoints | **FREE** |
| **Spent to date** | **42,200 = 10 calls = 2.11 %.** Remaining **1,957,800** |
| **⚠ Of that, ≈29,540 bought nothing** | seven zero-tile forecast responses during the vendor outage — §4. Not our error |
| Forecast (future) windows | ✅ **WORK** — 17,862 tiles at 9.41 h lead, verified 2026-08-19 13:35 UTC |
| History (past) windows | ✅ work: 17,862 tiles at 8×8 km / granularity 60 |

## 12.3 Credential incidents — three, all contained, none ever committed

1. The key was **hard-coded** in `hackathon/hackathon/run_checks.py` and captured into
   `testing/results/n15_forecast_state.json`. **Both redacted before the first commit.**
2. **`/v1/heat_intelligence` returns the caller key inside the `download_link` URL path.**
   `data/raw_api/` is gitignored for this reason.
3. **2026-08-18: the key was pasted into `INTAKE-ARBITER/.env.example`** — the one dotfile
   `.gitignore` deliberately re-includes. Moved into `.env`, template restored. **Never committed.**

---

# 13. FILES — created and modified

## 13.1 `INTAKE-ARBITER/src/` — 24 modules, **UNTRACKED in git**

**Session D added:** **`ticker.py`** (+ `demo/gen_ticker_cases.py`, `demo/verify_browser_ticker.js`).
**Sessions A/B/E added:** `rolling.py` · `metros.py` · `discover_dc_clusters.py` ·
`fetch_weather.py` · `annotate_screen.py` · `export_plume_fields.py`.
**Made metro-aware:** `fetch_geometry.py` · `select_site.py` · `refusal_rank.py` ·
`screen_architecture.py` · `commit_site.py` · `build_site.py` · `direction_sweep.py`.
**Earlier:** `agent.py` · `conformal.py` · `environment.py` · `plume_uncertainty.py` · `explain.py` ·
`backtest.py` · `audit.py` · `run_all.py` · `fetch_imagery.py` · `path_clearance_survey.py` ·
`stability.py`.
`physics/solver.py` and `physics/warp_solver.py` are copies of the `testing/` originals — **I did not
write the solver**; it predates this sprint and was calibrated in N-22 against ~40,000 measured
points.

## 13.2 `INTAKE-ARBITER/demo/` — the interface, ~41 MB

`index.html` · `README.md` · **`sites.json`** (the manifest that decides what may be offered) ·
**`plume_field_{ashburn,chicago,dulles}_longest.json`** (~2.8 MB total) · **`rolling.json`** ·
`trace.json` · `scenarios.json` (30 MB, 120,960 rows, columnar) · `backtest.json` ·
`explanations.json` · `plume_uncertainty.json` · `field_<date>_{forecast,outcome}.json` × 8 ·
`rise_table_{longest,facing}.json` · `spread_table_<mode>_sd{47,72}.json` × 4 ·
`site_aerial.png`, `site_aerial_usgs.png` · `dp_cases.json` · `gen_dp_cases.py` ·
`verify_browser_{agent,decision,explanation}.js`.

## 13.3 `INTAKE-ARBITER/data/`

`geometry/` — `dc_clusters.json` (37 discovered clusters) · `{ashburn,chicago,dulles,phoenix,
santaclara}_candidates.json` · per-metro `*_selected_site.json`, `*_refusal_rank.json`,
`*_solver_site_{longest,facing}.json`, `*_direction_table.json` (**ashburn's are unsuffixed**) ·
`architecture_verdicts.json` (**the imagery scope gate — every verdict, its evidence and its
confidence, including the two refusals and the two Dulles rejections**).
`weather/` — `kiad_hourly_2021_2025.json` (43,763) · **`kord_`** (43,775) · **`ksjc_`** (43,747) ·
**`kffz_`** (41,919) · `kiad_wind_summers.json`.
`imagery/` — `screen/` plus per-metro subfolders with `annotated_*.png` frames.

## 13.4 Root

**`HANDOFF.md`** (this file) · **`fortyguard-api-findings.md`** (§10.7 records the outage resolution) ·
**`fortyguard-message-forecast-zero-tiles.md`** (**flagged DO NOT SEND AS DRAFTED**) ·
`INTAKE-ARBITER/PLAN.md` (**not yet updated for Sessions A, B, E**) · `n56-freecooling-PREREG.md` ·
`n50-timing-PREREG.md`.

## 13.5 `testing/` — this sprint

**`diag62_forecast_recheck.py`** (the call that overturned the blocker) ·
**`fetch_chicago_field.py`** (explicit-timezone paid call) · `diag61_forecast_entitlement.py` ·
`test_n26_coverage.py` (**+`dryrun` mode, retry budget, per-year reporting**) ·
`fetch_n51_fullyear.py` · `diag57_forecastskill.py` … plus `results/` and ~200 fixtures.
**`testing/run_e2e.py` is SUPERSEDED** — it hard-codes `THRESHOLD_C = 33.0` and uses a synthetic
`demo_site()`. **Do not ship it.**

## 13.6 Git

Branch **`master`** (rename to `main` before any push). `5289a5d` initial · `fea3166` endpoint
probes · **`d57b3b7` Session D + the whole `INTAKE-ARBITER/` tree, 186 files, 194 MB.**
**The tree is COMMITTED as of 2026-08-20** — every file scanned against the live key before
committing (**0 hits**; only the two gitignored `.env` files hold it, and the committed
`.env.example` has an empty value). No remote configured; `gh` not installed.

---

# 14. ENVIRONMENT

- Windows 11, working dir `d:\FGHackathon`, a git repo. PowerShell primary; Bash also available.
- Python **3.14** at `C:\Users\bisma\AppData\Local\Programs\Python\Python314\python.exe`.
- **NVIDIA RTX 4050 Laptop, 6 GB, sm_89, CUDA 12.9, Warp 1.16.0.** The Warp ensemble peaks at
  **371 MiB**, leaving 5,770 MiB free. 6 GB is why Earth-2/CorrDiff was cut (NIM needs ≥40 GB).
- Installed: `numpy`, `scikit-learn`, `pypdf`, `psychrolib`, **`PIL` 11.3.0** (used to crop tall
  screenshots). **No torch, no transformers, no Ollama, no llama.cpp.**
- **Chrome AND Edge installed** — headless screenshots work, §8.1. **Node available** — the three
  `verify_browser_*.js` tests need it.
- **⚠ The machine's clock is Pakistan Standard Time (UTC+5).** `date` in Git Bash has reported a
  bogus `PST` label — **trust `common.site_now()` / Python's timezone-aware values, never the shell.**
- Timings: rise table **5–9 s GPU** · `agent.py run` ~37 s · `backtest.py all` ~27 s ·
  `rolling.py` ~10 s · `export_plume_fields.py --all` **~2.3 min** (deliberately NOT in `run_all`,
  since fields change only when geometry does; `audit.py` check 2d verifies the shipped ones) ·
  `run_all.py` **~97 s**.
- **⚠ `d:\FGHackathon\CLAUDE.md` DOES NOT EXIST** and never has. The rules it would carry are §1.

---

# 15. RUBRIC POSITION — honest

**Impact & Relevance 40 %, Technical Execution 35 %, Innovation 15 %, Communication 10 %**, plus an
unweighted **Business Viability** — treat it as real. **Submission requires a public GitHub repo, a
live demo link, `fortyguard` as collaborator, a 2–5 minute video, and documentation of API usage.**
Judging Sept 1–15, winners Sept 16. Prizes $3,000 / $2,000 / $1,000 plus an **NVIDIA Jetson AI
Developer Kit** — which supports an honest *"designed for and sized to fit the edge"*, since the Warp
kernel peaks at 371 MiB. **Say "designed for", not "verified on" — there is no Jetson.**

**We have three of five submission requirements.** The demo exists and runs; **the video and the
public repo do not.**

**Business Viability is worth arguing explicitly:** the value rests on FortyGuard's **forecast**, a
recurring paid API product, rather than on a physics term worth 0.8 % of hours; the agent gates on
**contamination and humidity**, which LBNL documents as the actual reasons operators avoid free
cooling; **three real sites across two climates** show it generalises; and the deliverable includes
**a reproduced vendor outage report** worth money to them.

**The strongest story is the honesty:**
- a self-calibrating bound whose measured coverage is **65.6 % against a 90 % nominal, reported as a
  failure**;
- **five sites screened and two refused** — one rooftop-cooled, one not built — plus a third refused
  **by the solver itself** because the intake disc would have averaged the exhaust it is meant to
  measure;
- a refusal guard **priced at −3,124 h/yr** where it fires;
- a plume model that **costs hours and buys safety**, said plainly, whose shape is documented as the
  **outlier** that under-predicts in the unsafe direction;
- a 12-hour schedule whose stability is **measured (94.08 % of re-plans change nothing)** and whose
  cause is **correctly attributed to the forecast, not to our constraints**;
- and an audit that re-reads **62 published numbers** out of the files the code itself wrote,
  plus a reasoning tape whose **29 templates contain not one literal digit** — so "nothing here is
  hand-written" is a command you can run rather than a claim you have to take on trust.
