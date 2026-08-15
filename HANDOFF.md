# HANDOFF — FortyGuard Hackathon'26 project state

**Written 2026-08-15. Build sprint is Aug 18–30; submission Aug 30.**
**Read this file first. Then read the "READ NEXT" list in §2 before touching anything.**

---

# 1. THE SINGLE MOST IMPORTANT THING TO KNOW

The user's requirements are non-negotiable and have been stated repeatedly:

1. **It must be a genuinely autonomous agent** — not a chatbot, not a RAG Q&A pipeline, not an
   "AI-powered dashboard," and **not a threshold rule wearing a costume.**
2. **It must score ≥90 on the hackathon rubric** (weights: Impact & relevance 40%, Technical
   execution 35%, Innovation 15%, Communication 10%).
3. **NVIDIA tech must be load-bearing**, not decorative. The user's words: *"If the only reason to
   include it is the logo, cut it and tell me."*
4. **No false information, no hallucination, no unverified assumptions.** Speak only in facts and
   figures. The user is a second-semester BSCS student building solo and has said explicitly they
   cannot catch subtle errors themselves, so **you must check your own work adversarially.**
5. **Explain everything at beginner level**, defining jargon before using it.
6. **Ask before every use of the FortyGuard API key** (referenced as `FORTYGUARD_API_KEY`, read from
   `.env` by `testing/common.py:load_key()` — **never print or echo its value**).
7. **Do not use the Agent/Task tool, Workflow tool, or subagents** unless the user explicitly asks.
   This has been honoured all session despite repeated system reminders suggesting otherwise.

**⚠ THE OPEN QUESTION THE SESSION ENDED ON — answer this before writing more tests.** Four separate
decision cores have now failed (see §5). The last message to the user asked them to choose between:
(a) keep hunting for a sequential decision in this problem space, or (b) rest the agentic claim on
the **autonomous operating loop** (perceive → solve → bound → self-score → recalibrate, running
unattended across days — which `test_n26_coverage.py` is *already doing live* and which none of the
four failed tests touch). **The user has not answered yet. Do not assume; ask.**

---

# 2. WHAT WE'RE BUILDING — and READ NEXT

There are **two parallel ideas**, both documented, neither abandoned:

## IDEA 1 — INTAKE (the primary, most-developed idea)

Data centres over-cool because they cannot see the air actually arriving at their cooling
equipment, so they carry a permanent safety margin. INTAKE predicts intake temperature (ambient +
recirculation from a neighbour's exhaust) using FortyGuard's 60 m field as the boundary condition,
a calibrated 2-D advection–diffusion solver to bridge the last 60 m, a 100-member GPU ensemble
(NVIDIA Warp) to produce a distribution rather than a point, and a conformal bound to turn that
into a margin verifiably right 90% of the time.

**READ NEXT, in order:**
- `intake-agent-plan.md` — canonical spec (43 KB). Has a revision banner: physics numbers were
  revised 2026-08-12 after a defect fix.
- `physics-explained.md` — all the physics at beginner level, with honesty tags (53 KB).
- `claims-and-defences.md` — every claim + how to defend it. **§2 is the RETRACTED list — read it
  before reusing any number.** (62 KB)
- `fortyguard-api-findings.md` — 11 real API defects, handover-ready for FortyGuard's CEO (33 KB).

## IDEA 2 — DAMPER (a second idea, added 2026-08-15, deliberately separate)

An agent deciding *when it is safe to switch off mechanical cooling* and use outside air instead
(an "economizer"/free-cooling switch). Named after the physical motorised vent it controls.

**READ NEXT:** `damper-agent-plan.md`, `damper-physics-explained.md`,
`damper-claims-and-defences.md`, plus `damper-test-1-data-availability.md` (done),
`damper-test-2-switching-simulation.md` (done), `damper-test-3-forecast-skill-PLANNED.md`
(**designed, NOT run, needs ~8,440–16,880 credits and user approval**).

**Honest scoring of DAMPER against the rubric, given to the user 2026-08-15: ~45–50/100.** Reasons:
it sidelines FortyGuard (Test 2 used a single NOAA weather station, so a generic weather API would
work equally well), its validated mechanism is computationally trivial (no heavy load, no GPU need),
and its "adaptive" policy is a deterministic pre-tuned function — a smarter rule, not an agent.
**The user has been told this plainly.** It is kept as a supporting idea, not the flagship.

---

# 3. WHAT IS SOLID — do not re-litigate these

| Finding | Evidence | Test file |
|---|---|---|
| Solver correctness (verification) | Matches analytic Gaussian plume to **2.9 × 10⁻¹⁰** rel. error; heat conserved to **7.5 × 10⁻¹²** | `test_n29_verify.py` (V1/V2) |
| GPU port | **93.46×** on 100-member ensemble (CPU 61.82 s → GPU 0.661 s), CPU/GPU agreement **6.95 × 10⁻⁵ °C** | `test_n16_warp.py` |
| External validation (the only one) | **67** Project Prairie Grass 1956 field experiments; measured plume-width exponent **0.8047** (median R² 0.998) vs our 0.50 → our error **+52.6 % @50 m, 0.0 % @200 m, −34.5 % @800 m** | `test_n35_prairiegrass.py` |
| Dispersion coefficients | Cross-checked vs EPA ISC3 (EPA-454/B-95-003b) | `test_n36_coefficients.py` |
| Knife-edge behaviour ⭐ | Ensemble spread **27.04×** wider at the geometric edge (285°, sd 0.2556 °C) than safe sectors (0.0095 °C). **No coded rule about plumes anywhere** — the agent discovers it | `test_n23_knifeedge.py` |
| Peak-hour uncertainty | **peak_sd_h = 1.4475 h over 15 days**, leave-one-out floor **1.1579 h** (2.9× the 0.395 h break-even). The 5-day version collapsed to 0.000 when one day was dropped; this one does not | `test_n38_peaksd.py` |
| Plume is additive, not double-counted | At 2 km one spatial template leaves residual = **0.31 % of the field's own sd**; driven by **AREA not granularity** | `test_n31_windalign.py`, `test_n32_granularity.py` |
| Diffusivity derived, not invented | Pasquill class per hour from real weather; median **7.40 m²/s** in decision hours | `test_n33_stability.py` |
| Timezone/horizon | 12 h horizon **confirmed**; our own 9-hour bug found and fixed | see §7 GOTCHA #1 |
| FortyGuard `env_params` fields | 15 params incl. `wet_bulb_temperature_celsius`, `relative_humidity_percent`, and six AQI indices — **verified present in a real saved response** | `damper-test-1-data-availability.md` |

**Credits: `cycle_remaining` = 180,980, unchanged across ~200 calls all session.** That key's billing
cycle closed 2026-07-19 and **the meter is frozen**, so spend cannot be observed — budget only from
the documented rate of **4,220 credits per heatmap call**.

---

# 4. WHAT IS RUNNING RIGHT NOW (live, unattended)

**`test_n26_coverage.py` — the out-of-sample conformal-bound coverage test.** This is the one thing
genuinely running autonomously and correctly, and it is arguably the strongest *actual* agentic
artifact in the project.

- Windows Task Scheduler task **`FG-N26-Coverage`**, fires daily at **13:30 PKT (= 08:30 UTC)**.
  Last run 2026-08-15 13:44, `LastTaskResult = 0`, next run 2026-08-16 13:30, missed runs 0.
- Costs ~2 API calls/day. Collects a ~9.5 h-lead forecast + the elapsed outcome for the same
  14:00–16:00 site-local window.
- **State:** Aug 12 ✅ complete pair · Aug 13 ✅ complete pair · **Aug 14 MISSING (permanent gap —
  machine slept, and a forecast cannot be made retroactively)** · Aug 15 forecast collected, outcome
  pending (window closes 20:00 UTC, fetchable after 20:15 UTC).
- **Needs 4 complete pairs → 3 test days for its pass condition (P3).** Currently 2 pairs, 1 test day
  at **96.8 % coverage** vs a 90 % target. Verdict is correctly `NOT YET DECIDABLE`.
- **The task settings have `WakeToRun = False`**, so it cannot wake a sleeping machine. It does have
  `StartWhenAvailable = True`, so it catches up once the machine is awake. The user was told the
  laptop needs to be on sometime in the early-to-mid afternoon PKT on Aug 16 and 17. **The user was
  offered enabling `WakeToRun` and has not answered.**

---

# 5. THE FOUR FAILED DECISION CORES — the central problem, and why

Every attempt to build a genuinely *sequential* decision on top of this physics has failed. This is
the crux of the project and the reason the agentic claim is unresolved. **Do not re-run these
hoping for a different answer; read why each died first.**

### N-25 — FortyGuard temperature sharpening. FAIL, then found to be the WRONG STATISTIC.
`testing/test_n25_sharpen.py`, result `results/n25_sharpen.json`.
Measured `b` in σ(lead) ∝ lead^b: **b = −0.0608, SE 0.0803, t = −0.76, 95 % CI [−0.316, +0.195]**.
FAIL vs the 0.129 pre-registered break-even. **But the CI contains 0, 0.129 AND 0.187 — it is
underpowered, and does NOT establish that sharpening is absent.** It *does* exclude **0.500**, the
value N-24's headline "+0.356 gain, 11.2σ" was computed with (`test_n24_breakeven.py` line 211,
exponent held fixed at 0.50). **So N-24's headline agentic margin rested on an assumption the data
rules out.** Separately: N-25 fitted `b` on the **spatial sd across ~17,862 tiles on one day**, but
`staging.py:make_forecast_paths()` draws an independent error per (day, lead), so the DP needs the
**day-to-day** sd of the **site-level** error. Different quantities (~9× apart in magnitude).

### N-42 — the corrected day-to-day statistic. UNRESOLVABLE on the calendar.
`testing/test_n42_daytoday_sharpen.py` (modes: `validate` / `status` / `report` / `collect`).
Estimator built and **validated against synthetic data with known answers** (recovers 0.506 from
0.500, 0.179 from 0.187, and matches an analytic attenuation prediction to 3 dp). Two blockers found
**before** spending any credits:
- **Attenuation:** if a share of the error is a day-level offset common to every lead (N-25's five
  leads all sat at ~+1.06 °C), the measurable `b` is squashed. At an offset-to-resolvable ratio of
  1.0, a *true* b of 0.50 measures as **0.138** — below the 0.187 bar.
- **Power:** Monte-Carlo of the estimator needs **~80–160 days** for a decisive verdict. The
  hackathon calendar cannot supply that.
Current real data: **1 usable lead leg (~9.5 h) with n=2 days, sd 0.0566 °C.** Needs ≥3 legs.
**Recommendation given: do NOT buy the extra leads (~8,440 credits/day) — it cannot pay off in time.**

### N-40 — wind-direction sharpening through the solver. DECISIVE FAIL, well-powered.
`testing/test_n40_windsharpen.py`, result `results/n40_windsharpen.json`.
σ_recirc went the **wrong way**: **0.26 °C at 1 h lead vs 0.16 °C at 12 h**, fit **b = −0.1166,
SE 0.0310, t = −3.77, CI [−0.186, −0.048]** — excludes zero. Also fixed a real defect of ours:
`solver.ensemble()` perturbs direction by **±15°** while the measured error is **47–72°**, i.e. we
were understating the dominant uncertainty by ~4×.
**⚠ N-44 later explained this inversion** — see below. N-40's number is correct *for what it
measured*; it measured **dilution, not confidence**.

### N-43 — multi-site fleet triage of a scarce PHYSICAL resource. DECISIVE FAIL.
`testing/test_n43_triage.py`, result `results/n43_triage.json`.
**−3.63σ** against a tuned point-forecast ranking baseline. A **sign-inversion bug was found and
fixed first** (the ensemble inverted `true = forecast + error` when generation used
`forecast = true + error`; correct is `forecast − error`) — the verdict survived the fix
(−5.51σ → −3.63σ). Deliberately *not* a repeat of N-20 (which allocated cheap GPU compute and lost
to equal-split at −2.67σ); this allocated a genuinely scarce physical resource instead. Still lost.

### N-44 — adaptive commitment. P1 PASSED (a real, new finding). P2 FAILED. **Cost model mis-specified.**
`testing/test_n44_adaptive_commit.py`, result `results/n44_adaptive_commit.json`.

**⭐ P1 is the one genuinely positive decision-relevant result in the whole project, and it stands.**
Measured **AUC** (discriminating power of the ensemble p90 for predicting a breach) as a function of
lead: **rises from 0.676 at 12 h to 0.853 at 3 h, gain +0.1634, bootstrap CIs disjoint.**
**This explains N-40 precisely:** σ-in-Celsius *inverted* while discriminating power *rose*, because
at long lead the ensemble sprays across the compass and collapses toward "probably nothing" (low sd,
low information); at short lead it concentrates and becomes genuinely bimodal (high sd, high
information). **σ-in-°C measures dilution; AUC measures confidence.** Both measurements are correct.

**P2 failed three times, across three structurally different implementations:**
1. Hand-written heuristic (not a real DP): **−6.17σ**. Degenerated to "commit at hour 0" — the most
   expensive action.
2. Binned backward induction over (hour, p90-quantile-bin) with a fitted transition matrix:
   **−21.59σ**. **Found and fixed a real bug** — `trans[t]` was only populated for
   `t < last_commit_h`, so the final row silently defaulted to a uniform 1/N transition and
   corrupted the entire backward chain. Still lost after the fix. Ruled out estimation noise:
   20× more training data and 60 % fewer bins changed nothing (32.4–32.8 either way).
3. Regression-based Longstaff-Schwartz backward induction using `sklearn.isotonic.IsotonicRegression`
   (no bins, no transition matrix): **−19.37σ**.

**Then a clairvoyant-bound diagnostic found the actual cause, and it is NOT a policy bug:**
- Clairvoyant (knows the outcome, picks the cheapest action) = **13.97** vs fixed rule **21.11**, and
  the fixed rule is **never** strictly cheaper on any single day → **the cost model and action space
  are internally consistent.**
- **On 3,376 of 4,000 days (84 %) the optimal action is to never commit at all.**
- Payoff asymmetry: committing when worth it **gains 112.9**; committing when not **loses only 3.0**
  → **break-even precision is 2.6 %** while the base rate of worth-it days is **15.6 %**.
- **Therefore committing almost always is close to optimal, and the DP's 88 % commit rate was
  economically CORRECT, not over-committing.** The earlier read of it as a bug was wrong.
- The real loss came from **timing**: `day_cost()` charges staging by hours run, but capacity only
  helps if `online_t ≤ peak_h`. Late commits are cheap and useless; the fixed hour-3 rule sits near
  the sweet spot by construction. The DP spread commits across hours 2–9 including useless late ones.
- **And the AUC for the decision that actually matters** ("is committing worth it at all") rises only
  **0.68 → 0.77 and plateaus after t=4**, so waiting past mid-horizon buys almost nothing.

**⚠ HONEST CONCLUSION recorded for the user:** the optimal policy here is close to *"commit early,
almost always"* — barely a sequential decision. **The pattern across all four failures is consistent
and is a property of the problem, not four unlucky implementations: this problem's physics is
near-binary and its cost asymmetry is extreme, which together make the optimal policy simple.**

---

# 6. FILES CREATED / MODIFIED THIS SESSION (2026-08-15)

## Created — DAMPER documentation (root)
- `damper-agent-plan.md` — full beginner-level plan, 450 lines
- `damper-physics-explained.md` — physics of humidity/wet-bulb/enthalpy + ASCII diagrams, 359 lines.
  **This is DIFFERENT physics from `physics-explained.md`** (that one is plume advection–diffusion;
  this one is air-property psychrometrics + switching-cost control). Connects at one optional point.
- `damper-claims-and-defences.md` — 135 lines, includes a §2 RETRACTED table
- `damper-test-1-data-availability.md` — ✅ done, $0
- `damper-test-2-switching-simulation.md` — ✅ done, $0
- `damper-test-3-forecast-skill-PLANNED.md` — 🔄 **not run**, needs approval

## Created — test code (`testing/`)
- `test_n42_daytoday_sharpen.py` — corrected sharpening estimator + power/attenuation analysis
- `test_n43_triage.py` — fleet triage (failed, −3.63σ)
- `test_n44_adaptive_commit.py` — AUC gate (P1 ✅) + adaptive commitment (P2 ✗)
- `diag44b.py` … `diag44f.py` — **diagnostic scratch files for N-44.** `diag44e.py` (clairvoyant
  consistency check) and `diag44f.py` (payoff-asymmetry analysis) contain the reasoning that
  produced §5's conclusion. **These are throwaway — delete or fold into the test file.**

## Modified — test code
- `test_n25_sharpen.py` — folded SE/t/95 % CI reporting into `report()`. Made `_fit()` a thin wrapper
  over a new `_fit_stats()` so there is **exactly one slope implementation** in the file. Exit code
  and verdict logic deliberately unchanged. Added `TCRIT_95` table (verified to 5 dp).
- Deleted `testing/n25_stats.py` — was a temporary standalone; folded into `report()` as above.

## Downloaded reference material
- `idea2files(md)/` — **the user supplied these**: `DC-WPR003A-EN.md` (Trane chiller whitepaper),
  `JADE_White_Paper_1.md` (Honeywell economizer manual),
  `WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.md` (Green Grid).
  **All three were read in full.**

## Installed
- `pypdf` (to extract text from PDFs that WebFetch could not read)
- `scikit-learn` (for `IsotonicRegression` in N-44's third implementation)

---

# 7. GOTCHAS — every one of these actually bit during this project

1. **⚠ THE 9-HOUR TIMEZONE BUG (the worst one).** The `heatmap` endpoint reads `start_time` in the
   **AOI's own local zone**, echoes no timestamp, and carries no metadata. Scripts built windows from
   a UTC+5 machine clock for a UTC−4 site → **silent 9-hour error on every forecast request for four
   days**, which we misdiagnosed as FortyGuard's service being intermittent (that complaint was
   **withdrawn**). **ALWAYS use `common.site_window()` / `common.lead_hours()`; they raise on a naive
   datetime.** Never format a window time from `datetime.now()`.
2. **Out-of-horizon requests return HTTP 200 + `status: completed` + ZERO tiles** — indistinguishable
   from a legitimately empty area. **Always assert non-empty** (`common.assert_non_empty()`). Firing
   a call >12 h ahead burns 4,220 credits for nothing.
3. **`/tmp` is unreliable in this environment.** It maps to a huge shared Windows temp dir; files
   written by one Bash call were repeatedly not found by the next. **Use the session scratchpad**
   (`C:\Users\bisma\AppData\Local\Temp\claude\d--FGHackathon\<session>\scratchpad`) or write real
   files into `testing/`. This wasted several cycles this session.
4. **Bash heredocs (`<<'PY'`) mangle `\n` inside Python strings** — 4+ occurrences across the project.
   **Use the Write tool for multi-line Python, not heredocs.**
5. **Windows console is cp1252** — any non-ASCII char in `print()` raises `UnicodeEncodeError` and
   kills the process. It once fired **after all 40 paid API calls but before `save_result()`**.
   `common.py` now forces UTF-8 on stdout/stderr at import, so every test that imports it is covered.
   Still prefer plain ASCII in `print()`.
6. **Background command output capture is unreliable** — several `run_in_background` calls returned an
   empty output file even on exit code 0, especially when combined with a `/tmp` redirect. Prefer
   foreground with a generous `timeout`, or write to a real file under `testing/`.
7. **WebFetch cannot read most PDFs** (returns binary/garbage) and several sites 403 it
   (IAEI, Socomec, hvacrassets). **Workaround that worked:** `curl -sL -A "Mozilla/5.0 ..."` to
   download, then extract locally with `pypdf`. This is how three primary sources got verified.
8. **`statistics.pstdev` vs `stdev`** — for a *sample* of days you want `stdev` (÷ n−1). Using
   `pstdev` biased every early estimate low. Fixed in `test_n42_daytoday_sharpen.py`.
9. **Naive rounding splits a single lead leg into two buckets** — 9.41 h and 9.50 h are the *same*
   daily leg but `round(x, 1)` separated them, making a real 2-day pool look unpoolable. Fixed with
   `nominal_lead()` in `test_n42_daytoday_sharpen.py`.
10. **`setdefault` before parsing creates empty entries.** `obs.setdefault(k, []).append(float(p[2]))`
    leaves an empty list behind whenever ASOS reports `M` for missing, then `fmean` explodes.
    **Parse every field before touching the dict.** Fixed in `test_n40_windsharpen.py`.
11. **Sign conventions in inverse problems.** If days are generated as `forecast = true + error`, the
    ensemble must invert with `true = forecast − error`. Getting it backwards cost N-43 a re-run.
12. **`solve()` vs `downwash_fraction()` once used different exponents** (2.0 vs the recalibrated
    1.25), so a CPU/GPU equivalence test was comparing **different physics** and passed anyway.
    Both now read one `CALIBRATED` dict in `solver.py`. Lesson recorded: *never let two code paths
    agree by sharing a default.*
13. **NOAA ASOS via Iowa State (free, no key) rate-limits and 503s** on large requests. Fetch in
    ~3-week chunks with retries and save each chunk incrementally.

---

# 8. METHODOLOGY RULES ADOPTED — keep following these

1. **No exponent, ratio, or margin is EVER quoted without n, SE, and a 95 % CI.** This rule exists
   because a 4-point proxy slope (b = −0.61) was reported as a finding and had to be publicly
   withdrawn when its CI turned out to be [−3.51, +2.29] — excluding nothing at all.
2. **Pre-register pass/fail conditions in the test file's docstring BEFORE running.** Never move a
   threshold after seeing data. **Three tests (N-8, N-33, N-34) are recorded as FAILED because their
   thresholds were mis-specified** — that is the correct handling, not re-definition.
3. **Name a real, TUNED adversary.** Tune it on training days, score on held-out days, compare paired
   per-day. An untuned baseline is not an adversary — this mistake was caught mid-test in DAMPER's
   Test 2 (an early 7.01σ "win" against an arbitrary deadband was discarded and re-run properly).
4. **Include an anti-threshold guard.** N-44's P3 requires the policy to fire off its own modal hour
   on ≥25 % of days. N-9 v1 "won" by discovering a constant — a threshold in costume.
5. **A correctly-specified DP cannot lose to a policy inside its own search space.** If it does, you
   have a bug — this is what exposed N-44's transition-matrix defect. Use a **clairvoyant upper
   bound** to check cost-model consistency before blaming a policy.
6. **Retractions stay visible.** `claims-and-defences.md` §2 and `damper-claims-and-defences.md` §2
   list every dead claim with what killed it. Citing a retracted number is worse than not knowing it.
7. **Verify sources by opening them, not by trusting search snippets.** Two claims were retracted this
   session after the primary documents were actually read: a Trane quote that **does not exist in the
   document**, and an ASHRAE "5 °C per 15-minute window" clause that **does not appear anywhere** in
   the 45-page primary text (the real rule is 20 °C/hr for disk-drive sites, 5 °C/hr for tape-drive
   sites, Table 4, footnote f).

---

# 9. STILL-UNVERIFIED CLAIMS (flagged, not fixed)

- **"Cooling is 25–40 % of a data centre's energy."** IAEI and Socomec both 403 on repeated attempts.
  A 45-page ASHRAE doc and a 48-page DOE guide were read in full looking for this split; **neither
  states it.** Replaced in the DAMPER docs with a verified DOE statement instead. Not load-bearing.
- **ASHRAE TC 9.9 primary book** — the 2011 Thermal Guidelines were obtained via an alternate mirror
  and read in full; the *current* (2021) edition has not been opened.
- **Deutsche Bank "nearly 100 % free cooling"** — cited *inside* a document read directly, one
  citation-layer removed from the original. Flagged as such in `damper-claims-and-defences.md`.

---

# 10. IMMEDIATE NEXT STEPS

1. **ASK THE USER the §1 open question** (keep hunting for a sequential decision vs. rest the agentic
   claim on the autonomous operating loop). Do not proceed without an answer.
2. **Keep `FG-N26-Coverage` alive.** It needs Aug 16 and Aug 17 afternoon runs (PKT) to reach 4 pairs
   / 3 test days. Offer `WakeToRun = True` again if the machine may sleep.
3. **Collect Aug 15's outcome** — fetchable after 20:15 UTC via
   `python test_n26_coverage.py collect` (1 paid call; **ask first**).
4. **Do not spend credits on N-42's extra leads** — the power analysis says it cannot resolve in time.
5. **If DAMPER continues:** run `damper-test-3-forecast-skill-PLANNED.md` (~8,440–16,880 credits,
   **needs approval**) — it is the only thing standing between "the mechanism works in principle" and
   "it works with FortyGuard specifically."
6. **Clean up** `testing/diag44*.py` (5 scratch files) once N-44's conclusions are folded into
   `results/n44_adaptive_commit.json` or the test docstring.
7. **Rubric reality check:** the user was told INTAKE's own earlier self-assessment was 84–89 *before*
   its stopping-rule pillar collapsed, and DAMPER scores ~45–50. **Neither currently clears 90.** The
   gap is concentrated in Technical execution (nothing is *built* yet — no agent loop, no UI, no
   demo) and Communication (no demo exists at all). `intake-agent-plan.md` Part 9 has a designed but
   **unbuilt** wind-dial demo concept that is the highest-value remaining buildable item.

---

# 11. HARDWARE / ENVIRONMENT

- Windows 11, primary working dir `d:\FGHackathon`, **not a git repo** (no version control — be
  careful with overwrites).
- Python 3.14 at `C:\Users\bisma\AppData\Local\Programs\Python\Python314\`.
- **NVIDIA RTX 4050 Laptop GPU, 6 GB, sm_89, CUDA 12.9, Warp 1.16.0.** GPU path verified working.
  **6 GB is a real constraint** — it is why Earth-2/CorrDiff was evaluated and **cut** (NIM requires
  ≥40 GB VRAM, and its 3 km resolution is far coarser than the ~200 m separations that matter here).
- Shells: PowerShell (primary) and Bash both available, each with its own syntax.
