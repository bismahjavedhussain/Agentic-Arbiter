# HANDOFF — FortyGuard Hackathon'26 · INTAKE-ARBITER

**Rewritten from scratch 2026-08-20; updated through the UI restructure the same day.**
**Submission deadline Aug 30 23:59 GST = 00:59 PKT Aug 31. 10 days left.**

> **THE SIX THINGS THAT MATTER MOST, in order:**
>
> 1. **START HERE:** `cd INTAKE-ARBITER/src && python run_all.py` → **15 steps, ~273 s, ZERO API
>    calls, 62 audit checks, 70 published numbers re-read from the files the code wrote.** Exits
>    non-zero on any failure. **If it is not green, quote nothing.** Then
>    `cd ../demo && python -m http.server 8000` and open `http://localhost:8000`.
>    **`file://` will NOT work** — browsers block `fetch()`.
> 2. **THE WHOLE TREE IS COMMITTED.** Branch `master`, head **`9a9b657`**. `INTAKE-ARBITER/` was
>    untracked for the entire project before 2026-08-20; it is not now. **`.gitattributes` exists and
>    is load-bearing — without it a fresh clone on Windows corrupts every PDF (§10 #82).**
> 3. **THE SITE PICKER IS NOW REAL.** It swapped ONE file for two sessions while twelve panels of
>    thirteen stayed Ashburn's. `agent.py` / `backtest.py` / `rolling.py` / `money.py` / `explain.py`
>    / `ticker.py` / `report.py` are all metro-aware; `src/build_sites.py` runs the chain per site;
>    **audit check 6c FAILS if any two sites agree. §6.13**
> 4. **THE UI IS A THREE-STAGE FLOW** — pick a site, configure a plant, watch it work — rebuilt
>    2026-08-20 to the user's spec. **§6.14, and read §9.0 first: there is one open UI item.**
> 5. **THREE REAL SITES SHIP, TWO WERE REFUSED ON EVIDENCE.** Ashburn (AWS IAD116→117), Chicago
>    (Stream→Equinix CH3), Dulles (AWS IAD81→IAD62). Santa Clara rooftop-cooled, Phoenix not built.
>    **"Five screened, two refused" is the single most credible thing in this project. §6.5**
> 6. **SESSION H IS THE ONLY SESSION LEFT AND IT CAN DISQUALIFY THE ENTRY.** Public repo,
>    `fortyguard` as collaborator, live demo link, 2–5 min video — **none exist**. §9.1
>    **TWO THINGS ONLY THE USER CAN DO:** lift rule 11 to go public, and record the video.
> 7. 🔴 **FORTYGUARD IS ACCEPTING HEATMAP JOBS AND NOT COMPLETING THEM — service-wide, not
>    forecast-specific.** DIAG-63 (2026-08-20 10:57 UTC) sent a forecast leg **and a past-window
>    control**; both returned HTTP 200 with an `activity_id`, then sat at `status: Processing` for
>    **45 polls / 425 s** and never reached a terminal state. A past window is a shape that worked
>    reliably through 08-19, so this is not the forecast path, the key, the plan, the quota, the AOI
>    or the granularity. **Neither call was billed.** Read **§4.0**, then `testing/results/
>    diag63_forecast_failed_status.json`.
> 8. **SPEND IS 13 CALLS / 54,860 / 2.74 %**, not the 10 / 42,200 / 2.11 % §12.2 carried. Re-derived
>    by `audit.py` check 9 from the meter, so it cannot drift again — **and it already caught my own
>    ledger regressing (§10 #100).** ⚠ **Attempts ≠ billed calls since 08-20**: `status: failed` and
>    a `Processing` stall are both **free**, so *attempts × 4,220* is no longer a spend figure
>    (§10 #101).
> 9. **THE PER-SITE REWORK IS UNDERWAY — Session 1 of 4 is done.** The aerial panel held three
>    Ashburn coordinates as constants and drew **Chicago's halls on Ashburn's photograph** (§10 #98).
>    **All 15 result panels now differ across all three sites**, verified by rendering each site and
>    diffing panel by panel. **Sessions 2–4 build the LIVE agent** — see §9.2.

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
| *"+67 h/yr from recirculation alone"* | **MISATTRIBUTED — §6.3.** The headline is an uncertainty asymmetry. ⚠ **But the old rider "recirculation *costs* hours" is ITSELF now retracted (§10 #97): plume awareness buys +22.8 safe h/yr AND 3.7× fewer breaches** |
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
| **The reasoning tape** | `src/ticker.py` — seven-stage events, **30 templates and not one literal digit**, 1,002 hour-tapes verified. §6.9 |
| **Conformal made visible** | The browser DERIVES the quantile: `cfQuantileIndex` / `cfSplit` mirror `conformal.py` and agree **exactly on 789 assertions**. §6.11 |
| **Full-tree audit** | `src/audit.py` — **62 checks, 0 failures**, **70 published numbers** re-read from emitted files. Checks 9 and 10 re-read the SUBMISSION documents: the API spend ledger and every figure in the root `README.md` |
| **Money, sourced** | `src/money.py` — **$/kWh and kW/ton BOTH SWEPT over published values**, 608 cells, nothing collapsed, **priced in each site's own state**. §6.12 |
| **Per-site engine** | `src/build_sites.py` — every offerable site on **its own** weather, geometry, bound and tariff. §6.13 |
| **Downloadable PDF** | `src/report.py` — a real 4-page PDF per site, **written without a PDF library** and verified by being read back. §6.15 |
| **The interface** | `demo/index.html` (~118 KB of one inline script, light+dark, no build step). **Three-stage flow**: pick → configure → results. §6.14 |
| **One command** | `src/run_all.py` — plume → agent → backtest → rolling → manifest → explain → **money** → **ticker** → fixtures → audit. **15 steps, ~273 s, zero API calls** |

| **Cross-language proofs** | browser == Python on **scheduling (500 cases)**, **decisions (20,160 configs — was 2,016, see §6.10)**, **reasons (1,336 hours)**, **stage-event sentences (2,037, character for character)** |
| **Validated physics** | vs analytic plume **0.00 %**, heat conserved **0.00 %**, **67** Prairie Grass experiments, 6 instrumented condensers **r=0.798**, GPU **81.6×** at **0.00012 °C** agreement |

## 3.2 IN PROGRESS / KNOWN INCONSISTENT

| Item | State |
|---|---|
| **N-26 coverage is 4 pairs, needs 10** | 🔴 **STALLED, not progressing.** The collector has returned zero tiles on 08-18, 08-19 and 08-20 — **§4.0**. It cannot start until the vendor's forecast path works. **Treat 65.6 % on 3 test days as final** |
| Five-year full factorial | 12-axis **one-at-a-time** sweep only. `agent.py`'s 120,960-scenario factorial covers 4 FortyGuard days, not the 5-year record |
| Dulles imagery verdict | **WEAKER than Ashburn's** — no USGS cross-check, so the two-source rule is NOT met. Chillers vs generators indistinguishable at 0.3–0.5 m. Recorded as such |
| Chicago FortyGuard field | **One past-window field.** Buys the spatial statistics + screen-zero visual, **NOT** a level offset (needs forecast + elapsed outcome = 2 calls) |
| Santa Clara / Phoenix | Refused on **screened pairs**; 5 Santa Clara frames and both other Arizona clusters remain unscreened. "Strong indication", not proof |
| `PLAN.md` | ✅ **BROUGHT CURRENT 2026-08-20.** New **§8n** (Sessions 4/0/A/C/D/F/G — the ladder, the present tense, the tape, the visible bound, money), **§8o** (B+E: three sites, two refusals), **§8p** (per-site engine, the three-stage UI, the hand-written PDF), **§12.8a** (the money citations). 🔴 **§7 and §9 were CORRECTED, not just extended** — §7 was still asserting the retracted *"+67 h/yr from recirculation alone"* and *"≈770 h/year"*, and §9 still claimed *"no dollar figure"*, *"one reference layout"* and *"no humidity gate"*. **2,047 lines** |
| Repo size | ✅ **DECIDED: publish everything with a routing README (§9.1a).** Now **~204 MB** — `metros.py --manifest` copies each site's committed aerial frame into `demo/` (6 PNGs, **14 MB**), which is duplication of `data/imagery/screen/` **and is necessary**: the demo is served with `demo/` as the document root, so `../data/...` is unreachable by `fetch()`. Only the committed pairs' frames are copied, not all 22 candidates. Under every GitHub limit |

## 3.3 NOT BUILT

| Missing | Notes |
|---|---|
| **Session F** — conformal panel | `rolling.json` already ships the per-lead margins and coverage it needs — verified, both are in `configs[0]`. **Cut this first if time compresses** |
| **Session H** — submission | **Downloadable report, README, API-usage doc, 2–5 min video, public repo, `fortyguard` collaborator.** All hard requirements. **Highest risk** |
| Local LLM narrator | Deliberate: VRAM measured at 371 MiB of 6,141 so it would fit, but no inference stack exists. `PLAN.md` §8l.1 |
| Same-day anchoring test | ~2 paid calls/day. **Unblocked** by §4 — if it worked, the customer-sensor requirement disappears |

---

# 4. ⚠ THE FORECAST BLOCKER — diagnosed as an outage, and NOT CLEARED

## 4.0a ✅ 2026-08-20 ~12:5x UTC — THE VENDOR RECOVERED, AND THE LIVE AGENT RAN

**`live.py run --paid` returned `status: ok`.** FortyGuard answered a forecast window in **39.8 s
over 4 polls with 17,785 tiles**, activity `9995dfd7`, billed the normal 4,220 (meter 1,945,140 →
1,940,920). The site's own tile sat **26.3 m** from the committed centre.

**The first genuine live decision this project has made**, every input real:

| | |
|---|---|
| Window | 2026-08-20 **09:00–10:00 site-local**, decided at 08:51 — an hour that had not happened |
| Ambient | **25.663 °C**, FortyGuard, this site's own tile |
| Wind | **100° at 1.03 m/s**, NWS live |
| Rise | **0.0001 °C** — 100° is nowhere near Ashburn's 255° critical bearing, and the solver says so |
| Bound | 25.663 + 0.0001 + **0.15203** measured margin = **25.815 °C** |
| Decision | **MECHANICAL** against a 24.0 °C limit, and separately blocked by dew point 21.1 °C > 15 °C |

⚠ **Today's N-26 pair is still lost.** Recovery came at ~12:5x UTC and the in-band firing window for
a 14:00 site-local target closed at **12:00 UTC** (lead had fallen to 5.15 h, below the 6.0 h
comparability floor). **Nothing was gained by the recovery today; tomorrow's 13:30 PKT run should
now work.** Do not raise the pair count until an outcome leg confirms it.

⚠ **Everything in §4.0 below still stands as the record of the fault**, and the four failure modes
are still what `live.py` and the collector must handle — a vendor that recovered once can fail again,
and it failed three different ways in three hours today.

## 4.0 🔴 THE OUTAGE, AS IT STOOD BEFORE THE RECOVERY — the collector failed every day 08-18..08-20

**Found 2026-08-20 by reconciling the credit meter (§10 #93). `diag62` succeeded once. The
collector has returned `completed` with ZERO features on THREE CONSECUTIVE DAYS since, including
three attempts today.**

| | |
|---|---|
| Evidence | `testing/results/n26_manifest.json` — `2026-08-18`, `2026-08-19`, `2026-08-20` all `forecast_done: false`. Today: **`forecast_attempts: 3`**, error *"completed but never populated after 59 polls over 608 s"* |
| Scheduled tasks | `FG-N26-Coverage` / `-Retry1` / `-Retry2` all report `LastTaskResult 0` at **13:30 / 13:50 / 14:15 PKT** today = **08:30 / 08:50 / 09:15 UTC**. They ran. They were billed. They returned nothing |
| Cost | **3 × 4,220 = 12,660 credits today alone**, and the same again every day the fault persists |
| **The pattern that survives** | **Every forecast FAILURE was a call made before 12:00 UTC** (08:30–11:30). **The one forecast SUCCESS was made at 13:35 UTC.** Past-window requests worked throughout, at every hour |
| **Why that cannot be tested cheaply** | Target hour and call clock time are **LOCKED TOGETHER** by the 6.0–11.5 h lead band. A 14:00 site-local window at a 9.4 h lead *forces* a call at ≈08:35 UTC. Calling at 13:35 UTC for that window gives a 4.4 h lead (below the floor); targeting tomorrow's 14:00 gives 28 h (beyond the 12 h horizon). **There is no request that varies one and holds the other** |

**What this changes:**

1. **§3.2's "~Aug 25 if nothing fails" is dead.** 6 more pairs at 1/day cannot start until the
   collector succeeds ONCE, and it has now failed on 08-18, 08-19 and 08-20. Today's budget is
   already spent.
2. **65.6 % provisional, 3 test days, is very likely FINAL.** Build the submission on it. That is
   what §4.1 already says — what was over-optimistic was the schedule, not the claim.
3. **§4's old title, "✅ THE FORECAST BLOCKER IS GONE", was wrong** — or rather, it was true of the
   entitlement question and false of the availability question, and it read as clearance of both.
   The entitlement question IS settled: forecast windows are included in the plan, proved by 17,862
   real tiles. **Availability is not settled and is currently negative.**
4. **The collector will fire again tomorrow at 13:30 PKT and spend up to 12,660 more.** Whether to
   let it is a USER decision — there is no free probe for "does the forecast work right now".

**DIAG-62, `testing/diag62_forecast_recheck.py`, one paid call authorised by the user — this part
stands and settles the ENTITLEMENT question:**

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

## 4.3 ✅ THE REWRITTEN FORTYGUARD REPORT EXISTS — `fortyguard-report-2026-08-20-jobs-not-completing.md`

**Written 2026-08-20 and ready to send.** It supersedes the draft below entirely. What it contains:
the exact request, **three distinct failure modes inside three hours** with `activity_id`s for each,
the **past-window control leg** that rules out six candidate causes before they can be asked about,
the billing change (stalls and `failed` are now free; `completed`-with-no-data was billed), the three
things a client provably cannot do today, and five prioritised asks. It credits them for the billing
change rather than only listing complaints, because that change was the right call.

**Still the user's to send.** Nothing here can mail it.

## 4.3a ⚠ SUPERSEDED — the older message must NOT be sent

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

| | safe-hour gain | raw free hours | breaches | breaches / 1,000 free h |
|---|---|---|---|---|
| agent KNOWS about the plume | **+65.6 h/yr** | **17,511** | **3** | **0.17** |
| agent IGNORES the plume | +42.8 h/yr | 17,462 | 11 | 0.63 |

🔴 **THE SIGN ON THIS WAS BACKWARDS UNTIL 2026-08-20 — see §10 #97. Plume awareness buys BOTH:
+22.8 safe h/yr AND 3.7× fewer breaches.** It is not a safety-for-hours trade, and the old line
*"it buys SAFETY, not HOURS"* understated the project's own result.

**WHY, from `score_config` in eight lines of arithmetic.** The truth is always
`truth_intake = T + rise`, and each policy's margin is the conformal quantile of **its own**
residuals:

| | the agent's residual | its bound |
|---|---|---|
| rise term IN | `(T + rise) − (fc + rise)` = **`T − fc`**, pure forecast error — **the plume cancels** | `fc + rise + q(forecast error)` |
| rise term OUT | `(T + rise) − fc` = forecast error **+ the whole plume** | `fc + q(forecast error + rise)` |

`q` is a 90th percentile per hour-of-day. **Adding the actual rise is exact; making the quantile
absorb the rise charges the hour a worst case instead.** So dropping the physics does not buy a
cheaper bound — it buys a *wider* one, and the self-calibrating margin is what makes that happen.
**This is the clearest evidence in the project that the conformal layer and the solver are load
bearing together rather than decoratively stacked.**

⚠ **The §2.3 retraction of "+67 h/yr from recirculation alone" still STANDS and is a different
claim.** The A-rows (18.4 / 65.6 / 158.4 h/yr as sensor error goes 0.1 / 0.3 / 0.5 °C) prove the
**headline** is driven by the uncertainty asymmetry. What was wrong was the further inference that
recirculation therefore *costs* hours. It contributes **+22.8 of the 65.6**, and nearly all of the
safety.

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

## 6.13 🔴 THE PER-SITE ENGINE — the picker offered three sites and only one had data

**FOUND BY THE USER, 2026-08-20:** *"the box of 'What it is worth, measured over five real years' is
the same values for all sites?"* It was, and it was worse than the headline.

`demo/index.html:loadSite()` fetched **one** file — `plume_field_<key>_longest.json`. Nothing else
changed. And `backtest.py` / `rolling.py` had **zero** mentions of `METRO`. So picking Chicago changed
**1 panel out of 13**; the headline, schedule, decision, explanation, wind dial, coverage, ladder and
money were all Ashburn's, wearing whichever label the picker was set to. **Nothing caught it** —
every number was internally consistent and every test passed. `agent.py` even carried
`SITE_CENTRE = (39.024017, -77.419691)` as a literal, so Chicago's agent stood in Virginia.

**THE FIX WAS SMALL BECAUSE OF AN EXISTING PROPERTY.** `backtest.py` and `rolling.py` take *all*
their data through `agent.load_hours()`, `agent.rise_table()` and `agent.perceive_fortyguard()`, so
**making `agent.py` metro-aware made all three.** Six path sites and one coordinate:

| what | was | now |
|---|---|---|
| weather | `kiad_hourly_2021_2025.json` literal | `M.weather_path()` — derived from the station id |
| solver site | `os.path.join(GEOM, "solver_site_%s.json")` | `M.geom_path(...)` |
| rise-table cache | `os.path.join(DEMO, "rise_table_%s.json")` | `M.demo_path(...)` |
| direction table | `os.path.join(GEOM, "direction_table.json")` | `M.geom_path(...)` |
| site centre | a hard-coded lat/lon | **`M.site_centre()`** — midpoint of the committed pair |
| outputs | `trace.json`, `scenarios.json` | `M.demo_path(...)` — **ashburn stays unsuffixed** |

**`metros.demo_path(name, k)` follows `geom_path`'s convention exactly: ashburn keeps the unsuffixed
name because `audit.py` re-reads 70 published numbers out of `trace.json` / `backtest.json` /
`rolling.json` / `money.json`, and renaming them would invalidate the audited chain for nothing.**

**MEASURED, and `audit.check_sites_actually_differ()` (check 6c) fails if any two agree:**

| site | station | hours | facade gap | worst rise | all-mech | gain h/yr | free h/day | state | $/MW-IT |
|---|---|---|---|---|---|---|---|---|---|
| **ashburn** | KIAD | 43,763 | 60.3 m | 0.3550 @255° | 43.7 % | +405.7 | 14.72 | VA | 7,990 |
| **chicago** | KORD | 43,775 | 118.4 m | 0.4108 @240° | 22.1 % | +326.8 | 16.48 | IL | 9,122 |
| **dulles** | KIAD | 43,763 | 137.7 m | 0.3593 @265° | 31.6 % | +401.7 | 14.72 | VA | 7,911 |

**Chicago being cooler shows up honestly:** only 22 % of scenarios are all-mechanical against
Ashburn's 44 %, but the *gain* is LOWER, because a reactive incumbent also does well in a cool
climate. **Dulles is the control §5 promised:** it shares KIAD, so its weather figures are identical
by construction and only its geometry differs — the audit asserts **both halves** of that.
**Chicago is priced on Illinois electricity (11.81 ¢) not Virginia's (8.72 ¢), a 35 % difference** —
`money.prices_for_metro()` selects on `METROS[k]["state"]`, a field added for exactly this.

🔴 **THE ONE LIMIT THAT SURVIVES, and it is on screen and in every trace.** Only Ashburn has
FortyGuard forecast/outcome day pairs; Chicago holds one past-window field and Dulles none. So each
site's **hours are its own** and its **coverage is Ashburn's, borrowed**.
`trace["fortyguard_provenance"]` records it, `ticker`'s `perceive.borrowed_field` event says it while
the agent runs, and `drawHeadline()` labels the coverage tile. **Quote a site's hours as its own;
quote the coverage as Ashburn's.** Running the tile lookup for Chicago against Ashburn's 8×8 km box
returned a "nearest" tile **926,064 m away** — arithmetically correct, useless — so `run_cycle()`
now guards it on `own_field`.

## 6.14 SESSION UI — the three-stage flow, rebuilt to the user's spec

**The user's complaints, verbatim in effect:** too much text; the worth box identical across sites;
the controls sitting below the results instead of in a column; and the reasoning tape far too
verbose — *"By loop, I meant to show that when we give claude something some task it shows different
words like 'perceiving, woobling'"*.

**`STAGE` + `setStage()` in `demo/index.html` are the whole mechanism.** Every card carries
`data-show="pick"` / `"configure results"` / `"results"`, and `setStage()` is the only thing that
sets `.hidden`. Three stages:

| stage | what is on screen | entry point |
|---|---|---|
| **pick** | `#pickcard` — site `<select>`, `describeSite()`, `#pickgo`; plus the screened-sites map. **Nothing else.** | `boot()` |
| **configure** | `.side` grid: `.sidebar` (actions **then** 12 controls) + `.mainpane` "What this agent decides" with that site's own tiles | `chooseSite()` |
| **results** | the streamed tape, then worth + download, then the proofs, then conformal, then money, then limits | `runAgent()` |

**The reasoning now reads like a status line.** `ticker.SHORT_TEMPLATES` — 18 entries, e.g.
`"solving {n_solves:,} plume fields on the {device}"`, `"refusing {n_refused_long:,} of
{n_bearings:,} bearings it cannot stand behind"`, `"widening its own margin by {delta_c:+.4f} C,
unprompted"` — streamed one line per stage by `streamTape()` at `STREAM_MS = 260`
(**presentation only, labelled as such; it is the reveal cadence, not a measurement**).
🔴 **THE SAME NO-LITERAL-DIGIT GUARD COVERS THE SHORT FORMS, and that matters more here:**
*"reading 17,862 tiles"* reads identically whether the number was computed or invented, so a short
phrase is exactly where a fake would hide. `check_no_literal_digits()` also fails if **any event
lacks a short form or any short form lacks an event.**

**Panel order, as specified:** worth + download → decision/schedule → aerial → plume → wind dial →
FortyGuard's own field → Why → self-scoring loop → how the bound is built → five years → money →
limits. **The long system tape is gone from the page**; its long form is in the PDF. The per-hour
7-stage tape survives inside `#whycard` as a `<details>`, because `tickerFor()` is the half that
`verify_browser_ticker.js` proves against Python and it is the only place all seven stages resolve
for one hour.

**`buildControls()` now BUILDS the control markup** from `CONTROLS` + `PE()` rather than reading a
hand-written filter row, so an axis added to `PLANT_ENVELOPE` appears without an HTML edit.
**`autofill()`** restores `AUTOFILL` — the shipped reference point the five-year backtest is scored
at — and is labelled a **navigation aid, not a recommendation**; every value it sets is one of the
swept options.

## 6.15 The downloadable PDF — written without a PDF library

`src/report.py`, `demo/report.pdf` + `chicago_report.pdf` + `dulles_report.pdf`. **4 pages each.**

**The user chose a real file over a print dialogue.** This machine has `pypdf` (which *reads* PDFs)
and **no writer** — no reportlab, no fpdf, no weasyprint. Making a judge `pip install` something
before a deliberately dependency-free demo works was the worse option, so `report.py` emits **PDF
1.4 by hand**: a catalogue, a page tree, one content stream per page, an xref table. The fourteen
standard Type1 fonts need no embedding.

**Two decisions that keep that from being reckless:**
1. **Courier throughout.** Every glyph is exactly **600/1000 em**, so `cols_at()` wrapping is
   arithmetic rather than an approximation needing an embedded metric table.
2. **`verify()` REOPENS THE FILE IT JUST WROTE** with `pypdf` and asserts every hour of the
   schedule, the headline counts and the site's own name are present — plus a **layout-bounds check
   on every placed string**, because Chrome will not render a PDF headlessly so it cannot be
   screenshotted. **That bounds check caught a line 20.1 pt off the right edge of all three reports
   on its first run**, which is why `Pdf.field()` (hanging-indent wrapping) exists.

**Which configuration the PDF reports is a DISPLAY SELECTION BY SEARCH** — `pick_block()` scores
*informativeness*: mixed modes first, then distinct binding constraints, then agent-vs-incumbent
divergence. **The first scoring rule was wrong in an instructive way:** "most free hours with a
switch" picked a day where the agent free-cooled 24 of 24 hours **and so did the incumbent** — a
report demonstrating no advantage. It is also **restricted to `bank_mode == "longest"`**, because
`facing` scores highest on distinct constraints precisely *because* refusal fires there, and
headlining the sensitivity placement would misrepresent the product.

**It is a snapshot and page 1 says so**, listing the configuration in full and telling the reader to
compare it against the live page before concluding anything.

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

## 7.4b `src/money.py` — chiller-hours priced (Session G)

`python money.py | selftest`. Writes `M.demo_path("money.json")`.

`KW_PER_TON` (12,000 Btu/h ÷ 3600 ÷ 1000 = **3.5168528 kW**, the one step with no PDF to open) ·
`CHILLER_KW_PER_TON` (4 values, PNNL-29674 Table 82) · `ELECTRICITY_CENTS_PER_KWH` (8 values, 2
states × 2 sectors × 2 vintages, EIA) · **`prices_for_metro()`** — selects on
`METROS[k]["state"]`, falls back to ALL rows and *reports* the fallback ·
`chiller_kw_per_mw_it()` · `price_row()` (**signs preserved — a negative hours row must yield a
negative saving**) · `hours_rows()` (read from `backtest.json`, never restated) · `build()` ·
`SOURCES` / `NOT_CLAIMED` (**rendered on the page FROM the JSON**, so a limit cannot be dropped from
the screen while staying in the file) · **`selftest()` — 10 cases, expectations produced with
`decimal` at 30 digits in a separate process.**

## 7.4c `src/report.py` — the downloadable PDF (Session H5)

`python report.py [site …] | selftest`. Writes `M.demo_path("report.pdf")`.

`PAGE_W/PAGE_H` (A4 pt) · `COURIER_EM = 0.600` · `char_width()` / `cols_at()` · `esc()`
(escapes `\ ( )`, transliterates non-ASCII) · `wrap()` (breaks an over-long word rather than
overflowing) · **`class Pdf`**: `line()` (**does NOT wrap**), `para()`, **`field()`** (hanging
indent — use this for any value that is not a short fixed field), `rule()`, `heading()`,
`bytes()` · `pick_block()` (informativeness search, `longest` bank only) · `build()` ·
**`verify()`** (reopens with `pypdf`; text presence + **layout bounds** + standalone-token check for
`nan`/`None`/`null`/`undefined`) · `selftest()` — 15 cases including a pypdf round trip.

## 7.4d `src/build_sites.py` — the per-site driver (§6.13)

`python build_sites.py [site …]`. `CHAIN` = agent → backtest → rolling → money → explain → ticker →
report, run per site with `METRO` set in the subprocess env. `offerable_sites()` reads
`demo/sites.json` — **the manifest is the only thing allowed to decide what may be offered**
(gotcha #69). Its docstring is the authoritative statement of what is per-site and what is borrowed.

## 7.4e `src/metros.py` — additions this session

**`demo_path(name, k)`** — same ashburn-unsuffixed convention as `geom_path` ·
**`site_centre(k)`** — (lat, lon) midpoint of the committed pair, read from `selected_site.json`'s
`centre_latlon` fields, the same ones the map marker uses · **`METROS[k]["state"]`** — added for
`money.prices_for_metro()`, explicit rather than parsed out of `label` · `export_manifest()` now
emits **`artefacts`** (every per-site filename, extension-stripped keys) and
**`has_own_fortyguard_field`**, and reports **`facade_gap_m` and `centroid_separation_m` as separate
fields** (§10 #80).

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
**`python run_all.py`** = plume → agent → backtest → rolling → manifest → **money** → explain →
**ticker** → fixtures ×3 → **report** → **build_sites (chicago, dulles)** → manifest again → audit.
**15 steps, ~273 s.** Most of that is the two extra sites: Ashburn alone is ~100 s.

### 7.7a THE 51 AUDIT CHECKS, by section — `python audit.py`

| § | function | exists because |
|---|---|---|
| 1 | `check_dead_code` | three superseded helpers survived a rewrite. **Add every new `demo/*.js` and `gen_*.py` to its file list or a function used only there reads as dead** |
| 2 | `check_nan_writers` | `json.load` accepts `NaN`; `JSON.parse` rejects it |
| 2b | (in `check_nan_writers`) | every emitted JSON must be strict-valid |
| 2c | `check_css_comments` | three `*/` against one `/*` fed English to the stylesheet, silently |
| 2d | `check_plume_fields` | re-derives the intake average from the SHIPPED field |
| **2e** | **`check_page_javascript_parses`** | **`node --check` on the extracted inline script — §10 #83** |
| 3 | `check_decision_precision` | rounding flipped decisions at exact gate boundaries |
| 4 | `check_duplicate_constants` | asserts AGREEMENT, not absence |
| 5 | `check_retired_constants` | AST-based, so prose documenting a retirement is not a false positive |
| **6a** | **`check_act_stage`** | all 37 command rows shipped `bound_c: null` — §6.10 |
| **6b** | **`check_stage_events`** | the tape's digit scan, re-run against the SHIPPED file |
| **6c** | **`check_sites_actually_differ`** | the picker changed one panel of thirteen — §6.13 |
| 6 | `check_published_numbers` | **68 figures** re-read from emitted JSON |
| 7 | `check_self_tests` | `conformal`, `environment`, `plume_uncertainty`, `explain`, `ticker`, `money`, `report` |
| 8 | `check_cross_language` | **five** browser-vs-Python tests |

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

### 7.8a NAVIGATING `demo/index.html` — one inline script, ~118,000 chars

There is **one** `<script>` block and no build step. `audit` check 2d `node --check`s it, because a
single syntax error silences the whole page (§10 #83). Grep for these:

| concern | functions |
|---|---|
| **the flow** | `STAGE`, `setStage()`, `boot()`, `describeSite()`, `chooseSite()`, `runAgent()` |
| **data** | `loadSite()` (**loads ALL of a site's artefacts**), `loadField()` |
| **controls** | `CONTROLS`, `buildControls()`, `AUTOFILL`, `autofill()`, `cfg()`, `wire()`, `syncOffday()` |
| **the decision** | `decide()` (the agent, re-run in-browser), `plan()`, `reactive()` |
| **the tape** | `SHORT_TEMPLATES` (Python side), `streamTape()`, `shortPhrase()`, `STREAM_MS` |
| **the hour tape** | `tkFormat()`, **`tkFixed()`** (mirrors Python's tie-to-even rounding), `tkRender()`, `tkEvent()`, `tickerFor()`, `tapeHTML()`, `drawTicker()` |
| **conformal** | `cfQuantileIndex()`, `cfAttainable()`, `cfMinN()`, `cfSplit()`, `drawConformal*()` |
| **money** | `drawMoney()` |
| **the PDF link** | `drawReportLink()` — **href comes from the manifest, never constructed** |
| **panels** | `drawHeadline`, `drawSched`, `drawBound`, `drawExplain`, `drawPlume`, `drawField`, `drawAerial`, `drawDial`, `drawCov`, `drawCoverageTiles`, `drawLadder`, `drawLimits`, `drawMap`, `drawAll` |

**Globals:** `T` trace · `BT` backtest · `RL` rolling · `MN` money · `TK` ticker · `EX`
explanations · `PF` plume field · `SITES` manifest · `SITE` the chosen site's manifest entry ·
`FIELD` the loaded FortyGuard field.

⚠ **`tkRender` uses `{` / `}` instead of `{` / `}` deliberately** — the cross-language tests
extract functions by counting braces, and a literal brace inside a regex cuts the function in half
(§10 #77). **Do not "clean it up".**

**Run it:** `cd INTAKE-ARBITER/demo && python -m http.server 8000` → `http://localhost:8000`.
**`file://` will NOT work** — browsers block `fetch()`, and the page says so in red.

---

# 8. HOW TO PROVE IT STILL WORKS

```bash
cd INTAKE-ARBITER/src && python run_all.py      # 15 steps, ~273 s, zero API calls, non-zero on failure
cd INTAKE-ARBITER/src && python build_sites.py # just the per-site chain (agent..report) for each site
cd INTAKE-ARBITER/src && python report.py      # just the PDFs, verified by being read back
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

## 8.1a 🔴 A PLAIN SCREENSHOT ONLY EVER SEES THE PICK STAGE — drive it

⚠ **REGENERATE `_shot_results.html` IN THE SAME COMMAND THAT SHOOTS IT (§10 #102).** It is a COPY of
`index.html`, so it goes stale the moment the page is edited — twice it reported a newly added
element as `MISSING` when the element was fine and the driver was old.

⚠ **`?site=chicago` is how you check the per-site work.** Comparing the three sites' rendered
panels is what found the aerial-imagery bug (§10 #98) and the empty dropdown (§10 #99); all 15
result panels now differ across all three sites, verified by dumping each and diffing panel by
panel.

Since the three-stage rebuild (§6.14), `boot()` lands on **pick**. The worth box, the download
button, the tape and every proof panel are `hidden` until two clicks happen, so the §8.1 command
photographs a site picker and a map and nothing else. **Both button bugs lived in the results
stage.** Drive it:

```python
# copy index.html to demo/_shot_results.html with this appended before </body>
(async () => {
  const sel = () => document.querySelector('#c_site');
  for(let i=0;i<300;i++){ if(sel() && sel().options.length>1) break;
                          await new Promise(r=>setTimeout(r,50)); }
  const want = new URLSearchParams(location.search).get('site');   // ?site=chicago
  if(want){ sel().value = want; }
  sel().dispatchEvent(new Event('change'));
  await window.chooseSite();
  await window.runAgent();
  document.title = 'DRIVER-OK stage=' + document.body.dataset.stage;   // read with --dump-dom
})();
```

**Three things that each cost a wasted run:**

1. 🔴 **`window.SITES` IS UNDEFINED.** Top-level `let`/`const` in a classic script are NOT window
   properties, so polling `window.SITES` waits forever. **Poll the DOM** (`#c_site.options.length`).
   Top-level `function` declarations *are* on window, which is why `window.chooseSite()` works.
2. **`--virtual-time-budget` must cover the stream.** `streamTape()` is ~18 events at
   `STREAM_MS = 260`; 60,000 is comfortable.
3. **`--dump-dom` and `--screenshot` are separate runs.** Put measurements in `document.title` and
   read them from the dump — there is no console to read. That is how "247 px below the heading" was
   measured instead of guessed:
   `document.querySelector('#dlreport').getBoundingClientRect().top - h2.getBoundingClientRect().top`.

**Delete `_shot*.html` and `_shot*.png` afterwards.** They are in `demo/`, which is what ships.

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

## 9.0 ✅ CLOSED 2026-08-20 — the download button is findable

**THE DOWNLOAD-PDF BUTTON IS BURIED, AND THE USER COULD NOT FIND IT.** Their exact words:
*"where is the download pdf option?"*

It **exists and works** — `#dlreport` in `demo/index.html`, href set by `drawReportLink()` from
`sites.json`'s `artefacts.report`, verified serving HTTP 200 at 26,568 bytes and correctly
per-site (`chicago_report.pdf` when Chicago is loaded). **The problem is purely placement:** it sits
inside `#headcard` ("What it is worth, measured over five real years") *below the tiles AND below
two long paragraphs* — `#headnote`'s "Read the 'no' days as a feature…" and the "Why these are two
different numbers" block — styled as a plain outline `.btn`. Confirmed by screenshot: at
1280×2600 the button lands ~560 px below the card's heading.

**This was the same class of mistake as the Run button (§10 #85), which had just been fixed.**

✅ **FIXED, and measured in the browser rather than eyeballed:** the `<p>` holding `#dlreport` now
sits immediately after `<div class="tiles" id="headline">`, before `#headnote`, styled
`class="btn btn-go"` so it reads as an action, with `#dlnote` beside it carrying the honest
"this is a snapshot" wording. **247 px below the card heading, down from ~560; 14 px below the
tiles.** Verified per-site (`report.pdf` / `chicago_report.pdf` / `dulles_report.pdf` all HTTP 200,
correct href per site) and in **both themes**.

**Do NOT restyle it into the sidebar:** the user asked for the download to sit with the five-year
worth box specifically. Both button bugs were invisible to every automated check and obvious in a
picture — **use the §8.1 screenshot workflow, including the results-stage driver, which is what
§8.1a now documents.**

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

### 9.1a DONE 2026-08-20 (second half) — and the DECISIONS the user made

| | |
|---|---|
| **H5 downloadable report** | ✅ Done earlier (§6.15), and its button is now findable (§9.0 closed) |
| **H6 API-usage document** | ✅ **`API-USAGE.md`**, and it is DERIVED: `testing/api_usage_ledger.py` reconstructs spend from saved meter readings, `audit.py` check 9 re-reads it. **This is what caught §10 #93** |
| **The front door** | ✅ **root `README.md`** — the repo had none, so a judge landed in 30 loose working notes. `audit.py` check 10 re-reads all 12 of its figures, failure rows included |
| **Pre-publication key scan** | ✅ **`testing/scan_secrets.py`** — §12.1 promised "the exact script is in §12.1" and no script existed. It scans the working tree **and every blob in history**, reports hits as `len=… sha256=…` redactions, and **never puts the key in an argv** |
| **H7 repo-size / scope** | ✅ **DECIDED BY THE USER: publish everything, with a routing README.** The imagery ships — it is the evidence behind "five screened, two refused". 194 MB is under every GitHub limit |
| **The collector** | ✅ **DECIDED BY THE USER: leave all three tasks running.** ≤12,660/day. With 1,945,140 left that is ~150 days of runway, and the binding constraint is the deadline, not credits. **A lost day is unrecoverable; a spent 4,220 is not** |

### 9.1b 🔴 H1 HAS A NEW BLOCKER, FOUND BY THE SCAN — and it is NOT the FortyGuard key

**The FortyGuard key is clean: 0 hits across 623 tracked files and 743 history blobs.** What the
scan found instead was **FortyGuard's OWN AWS access key id (`AKIA…`)** inside the presigned S3
`download_link` in `testing/results/fixtures/probe_heatintel.json`.

| | |
|---|---|
| Severity | **Low but real.** `X-Amz-Expires=600` from `20260815T212329Z`, so the signature died five days ago and grants nothing. An AWS key **id** is an identifier, not a secret |
| Why it still matters | It is **a third party's** credential material, it is the exact shape **GitHub's secret scanner** matches (which can notify AWS), and that third party is the one judging this entry |
| **Working tree** | ✅ **FIXED.** `X-Amz-Credential` and `X-Amz-Signature` redacted, matching the three redactions the file already carried. **The defect it evidences is untouched** — that defect is the caller credential in the URL *path* (`api_key%3D…`), not the standard S3 query parameters |
| **History** | 🔴 **STILL PRESENT in 2 blobs.** `git filter-branch --index-filter "git rm --cached --ignore-unmatch testing/results/fixtures/probe_heatintel.json" --prune-empty -- --all` purges it surgically without a full tree checkout. **Every commit SHA changes**, including the ones this file cites |
| **NOT DONE, deliberately** | The user was asked and answered with a question about rule 11 rather than picking an option. **A history rewrite is a local operation that does not touch rule 11** — but it is destructive and it is their repo, so it waits for an explicit instruction. **It costs nothing today and gets more expensive the moment a remote exists.** |

⚠ **`python testing/scan_secrets.py` MUST exit 0 before H1.** It exits 1 today, on those two history
blobs and nothing else.

⚠ **A judge will open the demo before reading anything.** `demo/README.md` must say
`python -m http.server` in its first line, because **`file://` blocks `fetch()` and the page will
show nothing but a red error.**

**Also outstanding, cheap, and worth doing:**
- ✅ **`PLAN.md` IS NOW CURRENT — done 2026-08-20.** §8n / §8o / §8p / §12.8a added, and **§7 and §9
  corrected where they still asserted retracted or superseded claims.** `money-sources.md` is now
  referenced from §12.8a. **What that exposed is worth remembering: the citation-bearing design
  record was the LAST document to be corrected, so it carried a retracted claim longer than
  anything else in the project.**
- The **diag62 outcome leg** (one call, ~4,220) would give a **5th measured level offset** —
  strengthening the n=4 level term `backtest.py` rotates across 1,826 days. **NOT** a 5th coverage
  pair: its window is 19:00 and the series fixes 14:00 (§10 #70).
- **Santa Clara** has 5 unscreened frames; **Phoenix** has two unscreened clusters (Chandler:
  CyrusOne/Digital Realty/H5, KPHX 20.6 km; Goodyear: Microsoft/Vantage, KPHX 33.9 km).

**Two things only the user can do:**
1. **Send the REWRITTEN FortyGuard message** — §4.3. The drafted one is superseded.
2. **Lift rule 11** so the repo can go public. **This is a hard submission requirement.**

---

## 9.2 🔴 THE PER-SITE / LIVE-AGENT REWORK — four sessions, requested by the user 2026-08-20

**The user's three faults, verbatim in effect:** (1) the aerial panel showed Ashburn for every site,
and *"when the agent is run, it generates all the results specific to that particular data centre"*;
(2) *"it says that there are 0 live API calls, how is it an agent if it doesnt make any live API
calls?"* — they want a prediction from **now**, live, with the conformal bound applied to it;
(3) *"every number, value should be for that specific site. Dont give the same output for all sites
and dont use hardcoded values."* **Credits are explicitly NOT a constraint** — *"we can get them as
much as we can"*.

### 9.2a ✅ SESSION 1 — DONE. Per-site truth at the render level

See PLAN §8q and §10 #98–#102. `metros.committed_imagery()` exports per-site imagery; the aerial
panel, the four Ashburn-named sentences, the wind-dial station and the ladder heading are all written
from `SITE`/`T`; a duplicate `id="c_site"` that made one dropdown permanently empty is gone;
`audit.check_duplicate_element_ids()` (check 2f) guards it. **All 15 result panels differ across all
three sites.**

### 9.2b ✅ SESSION 2 — DONE. `src/live.py`, the live agent

```bash
python live.py selftest                 # 22 checks, ZERO network calls. In run_all + audit check 11
python live.py dryrun --hours 12         # what it would fetch and what it would cost. Free.
python live.py run --paid --hours 12     # the real thing. Requires --paid.
python live.py run --replay <fixture>    # verify the decide path from a SAVED response
METRO=chicago python live.py run --paid  # per-site, and the metro is ASSERTED not assumed
```

**It writes no new decision logic.** `A.rise_table` / `A.lookup_rise` / `A.plan` /
`A.bms_commands` are imported from `agent.py` unchanged, so the live path is *the same agent on
different input* — which is also why the whole chain is verifiable offline. A parallel live-only
core would have drifted from the verified one within a day.

**Three sources, and only one of them is FortyGuard's:**

| Quantity | Source |
|---|---|
| Dry-bulb ambient per hour, at this site's OWN tile | **FortyGuard `/v1/heatmap`** — this IS the product |
| Wind bearing + speed per hour | **NWS `api.weather.gov` gridpoint**, free, keyless. FortyGuard has no wind field |
| Dew point per hour | **NWS**, same response. `env_params` returns no dry-bulb and `heatmap` returns no environmentals (findings §9.4) |

⚠ **The gridpoint endpoint, not `forecast/hourly`:** the hourly one gives `windDirection` as a
16-point compass string (22.5° resolution) against a rise table computed on a **5° grid**. The
gridpoint endpoint gives numeric degrees. Its fields are **run-length encoded** over ISO intervals
(`…/PT6H`), so a 12-hour horizon can arrive as three entries and must be expanded.

🔴 **THE BOUND COMES FROM `cycle.bound_day_level`, NOT FROM `rolling.py`.** rolling's per-lead
margins are calibrated on de-biased **persistence** error — a different forecaster — and using them
on a live FortyGuard forecast would be the category error §8e exists to prevent. So the live margin
is **0.15203 °C** from **n=4 measured day-pairs**, and `margin_provenance` carries: clamped to an
attainable ceiling of **0.80** against a nominal 0.90, measured coverage **65.6 %**, verdict
**FAIL**, and an **EXTRAPOLATION_WARNING** — every pair was measured at a ~9.4 h lead against a
14:00 window, and a live run bounds leads 1..12 at whatever hour it is now.

🔴 **IT NEVER INVENTS A FORECAST, AND THIS WAS PROVED AGAINST THE REAL VENDOR.** One paid call at
2026-08-20 11:0x UTC: activity `a89fef3f`, **33 polls over 307 s**, classified
`stalled_in_processing`, → `status: vendor_unavailable`, **no `hours` key and no `commands` key in
the emitted JSON**, and **0 credits** (stalls are unbilled). Four statuses, all distinct:
`ok` / `dryrun` / `vendor_unavailable` / `fixture_mismatch`.

**Cost shape.** A heatmap response is a per-tile aggregate **over the requested window**, not a time
series, so hourly resolution costs one call per hour: 12 h = 50,640 credits. Pricing is flat in hour
count, so the price is per CALL. Windows are **cached** under `data/live_cache/<metro>/` — N-55 makes
a cache hit byte-identical, not an approximation — and because the horizon SLIDES, an hourly re-run
needs only the one new far-end window, so **~1 call/hour** after the first run, inside the 30/day cap.

**Three bugs in my own code, all caught by a check rather than by reading:**
1. `A.rise_table()` takes no metro argument — it resolves through `metro_key()` from the
   environment. `live_run(metro="chicago")` would have loaded **Ashburn's** rise table. Now the env
   is set and then **asserted**.
2. `A.plan()` returns `(modes, free_h, switches)`; binding the tuple to `modes` surfaced two stages
   later as `TypeError: cannot use 'list' as a dict key`. Now unpacked, and the reported free-hour
   count is **cross-checked against a recount**.
3. A `json.dump` without `allow_nan=False` — audit check 2 caught it. NaN is legal Python JSON and
   illegal standard JSON, so it would have killed the browser silently.

🔴 **A REPLAY FIXTURE FROM ANOTHER METRO IS REFUSED.** `nearest_tile` returns the closest tile it
*has*, so replaying Ashburn's field for Chicago silently reports an Ashburn edge tile **926 km** from
the plant. **Dulles is the case that matters: 4 km.** A 926 km miss announces itself; a 4 km one does
not. Guarded at `MAX_TILE_DIST_M = 2000` and asserted in the self-test.

⚠ **Every saved FortyGuard field is an August afternoon in Virginia at 27–31 °C**, so every replay
verification correctly returns **zero** free-cooling hours — 43.7 % of all swept configurations do.
The DP's ability to grant hours is verified elsewhere, on 43,763 real hours and 20,160 cross-language
configurations.

### 9.2c ✅ SESSION 3 — DONE. `src/serve_live.py` + the LIVE/REPLAY UI

```bash
python src/serve_live.py                 # serves demo/ + /api. Dry-run only. Spends NOTHING.
python src/serve_live.py --allow-paid    # permits live calls from the browser
```

**Why a server exists at all:** a static page **cannot** make a live FortyGuard call, because the
request needs the API key and anything the page can read, every visitor can read. There is no clever
way round it. So the browser POSTs to a local server, the server reads the key in its own process,
and **only numbers come back**. That keeps both properties: GitHub Pages still serves the
REPLAY-only demo with every panel intact, and running locally gives the real live agent.

| Endpoint | |
|---|---|
| `GET /api/health` | is a live agent reachable, is it permitted to spend, what would it cost. **Does NOT report the credit balance** — reading it is a vendor call, and a health check that hits the vendor fails when the vendor does |
| `POST /api/live/<site>` | returns `{job_id}` **immediately** |
| `GET /api/live/job/<id>` | `running` / `done` / `error`, plus the progress events the page streams |

**Asynchronous by necessity:** one window can take 300 s, so a 12-hour horizon is up to an hour of
wall-clock and no browser `fetch()` survives that. The API mirrors FortyGuard's own shape.

**Three safety decisions:** binds to **127.0.0.1**, because a process that can spend money must not
be network-reachable by default (`--host` overrides, and the banner shouts when it does); refuses to
spend unless **both** `--allow-paid` **and** the request ask for it, so a page reload can never cost
50,640 credits; and a hard per-process call cap (`--max-live-calls`, default 24) whose refusal is
**explicit** rather than a silent switch to cached data.

**The UI.** The blanket *"0 live API calls"* line is gone — that sentence was true of the panels and
false of the product, and it is what prompted the user's question. `drawModeBanner()` now states
which of two modes the page is **actually** in, from a probe of `/api/health`:

- **REPLAY** — every panel from saved responses, and it says *why that is reproducibility rather
  than a limitation* (N-55: 17,862 of 17,862 tiles byte-identical), plus how to get LIVE.
- **LIVE** — plus a card that decides the next hours, with the seven stage events streaming as it
  perceives each hour.

🔴 **The live card carries its own bound's limitations ON SCREEN, next to the schedule they produced**
— the margin's source, n=4, the 80 % attainable ceiling, 65.6 % measured, the FAIL verdict, and the
extrapolation warning. **A live number with a hidden calibration story is worse than no live number.**

**A real bug this session, and it is gotcha #84's family again:** `setStage()` unhides every
`data-show="results"` card, which **overrode** `probeLive()`'s hiding — so a static host displayed a
"Run the agent on live data" button that could never work. Two pieces of code both owning `.hidden`,
last writer wins. The stage machine stays the single owner; it now evaluates `data-needs="live"` as a
second condition. Verified on both hosts: card **hidden** under `http.server`, **shown** under
`serve_live.py`.

**Also fixed:** the dead-code check flagged `do_POST` and `log_message`, which `http.server`
dispatches by name — a false positive, so an explicit `FRAMEWORK_DISPATCHED` set was added rather
than excluding the file, because excluding a file hides everything else in it.

### 9.2c-bis ✅ THE JUDGING-CRITERIA PASS — done 2026-08-20, before Session 4

**A judge (Ahmed Abdelkhalek) presented a "Builder's Trap" framework in the hackathon webinar.** The
user supplied the slides and asked for a critical self-assessment. Verdict: **the substance aligned
well; the FRAMING did not**, and three of the gaps were things we could already prove but had never
written down. Five changes, all writing rather than building, all numbers audit-registered:

| His criterion | Where we stood | What was added |
|---|---|---|
| *"API of the problem"* — a fill-in-the-blanks formula, with the guardrail *"if you cannot fill out every variable cleanly you are not ready to write a single line of code"* | We COULD fill it. We never had. | The contract sentence, README §1 and **PLAN §1a**, every variable an audited number |
| *"Engineering for the first buying customer"*, *"GTM fit"* | 🔴 **The real gap.** Value quantified, but no hero, no price, no wedge, no route to revenue | README *"Who buys this"* + PLAN §1a.1: the hero as a **role**, **$5,522–$7,990/MW-IT/yr** (16 swept cells), and the **30-day shadow trial** |
| *"Useful AI"* / *"Regex vs LLMs"* / *"Agentic scope"* | We use **zero LLMs** deliberately — his framework endorses exactly that, but **unstated, we read as a physics project that wandered into an AI hackathon** | README *"Useful AI — and where we deliberately did not use one"*: the job-by-job table, `local_model_used: false` quoted from the emitted artefact, **371 MiB of 6,141** proving it was declined on merit not capacity, and the five execution-scope constraints |
| *"MLP not MVP"*, validate before you scale | True of us, never said | The verification-surface paragraph: **62 checks and a gotcha log to #106 are headstones, not architecture**; no Kubernetes, no vector DB, no queue, no build step |
| — | 🔴 **65.6 % read to a skimmer as "their bound fails"** | Split into **method validated** (20/20 self-tests, 12 per-lead bounds ≥ 90 %) vs **calibration under-sampled** (9 pairs needed, 4 held, 80 % ceiling at n=4 — *arithmetically* unreachable, not refuted) |

🔴 **THE STRUCTURAL ARGUMENT THAT CAME OUT OF THIS, AND IT IS THE BEST ONE IN THE PROJECT:** the
30-day shadow trial is simultaneously the **sales motion** and the **missing calibration set**. The
bound needs 5 more day-pairs; a shadow trial produces them as a by-product. **The trial that earns
the first customer is the trial that finishes the science**, so the commercial path and the
scientific path do not compete for time. Lead with this.

⚠ **The one gap that writing could NOT close: no operator interview, no pilot, no LOI.** The pain is
evidenced from LBNL's instrumented study, not from a customer conversation. Stated plainly in both
README and PLAN §1a.2 rather than papered over. **If any time frees up before Aug 30, one
conversation with one facility engineer is worth more than any further engineering.**

`audit.py` check 10 now re-reads **22** README figures, including the money floor/ceiling, the cell
count, the VRAM pair, the solve count and time, and the 9-pairs/4-held/80 % trio — so none of the
new commercial or AI claims can drift.

### 9.2d ☐ SESSION 4 — autonomy, recovery, verification, docs

Collector hardened for all three failure modes (`empty` / `failed` / `stall`); a health watcher that
detects vendor recovery and banks the pair automatically; the **render-level cross-site panel diff
made a permanent check** rather than the one-off script that found #98 and #99; `run_all`/`audit`
extended; PLAN/HANDOFF/README/API-USAGE brought current.

⚠ **`N26_MAX_ATTEMPTS` now overrides the daily cap** (default still 3). The cap exists to bound a
runaway loop, not to ration credits, and on 08-20 it threw away a still-recoverable pair to save
4,220 — a lost day-pair is unrecoverable, 4,220 credits is 0.2 % of the plan.

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

## New across the per-site, money, report and UI work (2026-08-20)

80. 🔴 **A FIELD NAME THAT ASSERTS A QUANTITY IT DOES NOT HOLD.** `sites.json` reported
    `committed.facade_gap_m = 165.5` for Ashburn, whose real facade-to-facade gap is **60.3 m and
    clears the 60 m floor by 0.3 m**. The code read
    `refusal_measurement.true_gap_m or selected.separation_m`, and `refusal_measurement` has no
    `true_gap_m` — so **the fallback always fired** and the field shipped the CENTROID SEPARATION.
    Now two separate fields, and the gap is read from where it is measured. **A fallback that always
    fires is not a fallback, it is the implementation.**
81. 🔴 **A SITE PICKER THAT SWAPS ONE FILE. §6.13.** The generalisable lesson: **when an interface
    offers a choice, test that the choice CHANGES something.** `audit.check_sites_actually_differ()`
    compares values across sites and fails on agreement — existence proves nothing.
82. 🔴 **A FRESH CLONE ON WINDOWS CORRUPTS EVERY PDF WITHOUT `.gitattributes`.** Committing
    `report.pdf` warned *"LF will be replaced by CRLF the next time Git touches it"*. The blob that
    went in was byte-identical, so **nothing looked wrong** — but the warning is about the next
    CHECKOUT. A PDF's xref table is a list of byte offsets; rewriting `0x0A` → `0x0D 0x0A` invalidates
    every one. **Perfect in this working tree, broken for a judge who clones the repo.** Same exposure
    for the screening imagery. Fixed and **verified by actually cloning the repository and opening
    the PDF from the clone**: byte-identical, 4 pages, zero CRLF.
83. 🔴 **ONE BROKEN ESCAPE IN A SINGLE INLINE SCRIPT MEANS *NOTHING* RUNS.** A stray `'` inside a
    single-quoted JS string made `index.html`'s only `<script>` a SyntaxError. The page sat on
    *"Loading saved data…"* forever with **no console error, no unhandled rejection, and every JSON
    file serving HTTP 200.** Three probes found nothing because there was nothing running to probe.
    **`audit.check_page_javascript_parses()` (check 2d) now runs `node --check` on the extracted
    script.** Same shape as `check_css_comments`, and for the same reason: **the browser tests
    extract individual FUNCTIONS, so they cannot see a break between them.**
84. 🔴 **`[hidden]` LOSES TO ANY CLASS RULE THAT SETS `display`.** The UA sheet says
    `[hidden]{display:none}`, but `.side{display:grid}` and `.f{display:flex}` have higher
    specificity and win — so `el.hidden = true` did **nothing** to them. The stage machine leaked and
    the FortyGuard-level-day control stayed visible with the anchor set to a local reading. One rule,
    declared before the layout: **`[hidden]{display:none !important}`**.
85. 🔴 **A PRIMARY ACTION BELOW ELEVEN DROPDOWNS IS NOT A PRIMARY ACTION.** "Run the agent" sat at
    the BOTTOM of the sidebar, so on a 900 px screen it was off the bottom — while the copy said
    *"then Run the agent"*, pointing at a control nobody could see. **The user had to ask how to run
    it.** Actions now sit ABOVE the settings, and the main pane carries a second button wired to the
    same handler. **§9.0 is the identical mistake, still open, on the download button.**
86. **A HANDLER BOUND TO AN ELEMENT ID THAT NO LONGER EXISTS, INSIDE AN ASYNC FUNCTION, IS SILENT.**
    `syncOffday()` still targeted `#f_offday` from the retired hand-written filter row;
    `buildControls()` generates `#f_c_offday`. Setting `.hidden` on `null` threw inside an `async`
    handler, which surfaced as the page stranded on the pick screen with a clean console. **An
    unhandled rejection in an event handler is invisible unless you listen for it.**
87. **A DERIVED ARTEFACT BUILT BEFORE ITS SOURCE GAINED A FIELD IS SILENTLY EMPTY.** The per-site
    `*_ticker.json` files were generated before `SHORT_TEMPLATES` existed, so `shortPhrase()` returned
    `null` for every event and the stream rendered **zero lines with no error** — the `if(!ph) continue`
    swallowed it. **Rebuild every per-site artefact after changing anything the build emits;
    `build_sites.py` exists so that is one command.**
88. 🔴 **`.get(key)` WITH A KEY THAT STRIPS THE WRONG EXTENSION.** `export_manifest` built artefact
    keys with `nm.replace(".json","")`, so `"report.pdf"` became the key `"report.pdf"` while the page
    looked up `artefacts["report"]` and got `undefined` — a disabled button that looked like a missing
    feature. `os.path.splitext(nm)[0]`.
89. **A SUBSTRING CHECK FOR `"nan"` FIRES ON `"maintenance"`.** `report.verify()` reported three
    failures on three perfectly good PDFs. Match the **standalone token**:
    `(?<![A-Za-z0-9])nan(?![A-Za-z0-9])`.
90. 🔴 **THE DAY A REPORT CHOOSES DECIDES WHETHER IT TEACHES ANYTHING.** `pick_block()` scored "most
    free hours with at least one switch" and picked a day where the agent free-cooled **24 of 24
    hours and so did the incumbent** — a four-page report demonstrating no advantage. Score
    *informativeness*, and exclude the sensitivity bank placement, which scores highest on "distinct
    binding constraints" precisely because refusal fires there. **Same class as the ticker's
    tightest-hour default and the demo's 18 °C default: a DISPLAY SELECTION must still be searched
    for, not taken.**
91. **`%`-FORMATTING HAS NO THOUSANDS FLAG.** `"%+,.0f" % x` raises `ValueError: unsupported format
    character ','`. Use `format(round(x), ",")`.
92. 🔴 **MY VERIFICATION CODE WAS WRONG THREE MORE TIMES.** #89 above; the manifest key in #88; and
    three `money.py` self-test expectations hand-derived from a **rounded** intermediate
    (`163.782798` instead of full precision), which the test caught as three failures against
    correct code. Expectations are now produced with `decimal` at 30 digits **in a separate
    process**. **Running tally: checks wrong 13, product wrong 13.**

## New 2026-08-20, second half

93. 🔴 **A SPEND FIGURE IN A DOCUMENT NOBODY RE-READ WAS WRONG BY THREE CALLS — AND IT HID A
    LIVE VENDOR FAULT.** §12.2 said *"42,200 = 10 calls = 2.11 %, remaining 1,957,800"*. The
    collector's own manifest said `credits_last_after = 1945140`. The gap is **12,660 = exactly
    three calls**, which is `MAX_FORECAST_ATTEMPTS_PER_DAY` — today's three failed attempts.
    **The stale number was not the damage.** The damage is that the three calls it failed to
    account for were three *zero-tile* calls, so the document that would have revealed the forecast
    path is still broken was the one document nobody re-read. **§8.2 says it in one line: a number
    in a document that no test re-reads is a number that will drift — this is the FIFTH instance,
    and the first where the drift concealed a fault rather than merely being untidy.**
    Fixed three ways: `testing/api_usage_ledger.py` derives spend from saved meter readings;
    `audit.py` check 9 re-reads it and **fails on the superseded string as well as on a missing
    current one** (requiring only the new figure would pass a document quoting both); and
    `API-USAGE.md` is generated against the ledger.
94. **THE METER IS A BETTER WITNESS THAN THE ARTEFACTS, AND ITS ARITHMETIC IS A PROOF.** Only 5 of
    13 calls saved a before/after pair, so 8 were invisible to any per-call record. But a credit
    meter only decreases, the heatmap price is exactly 4,220, and `(2,000,000 − 1,945,140) / 4,220
    = 13.0000` **with no remainder** — so the call count is arithmetic, not recollection, and a
    single differently-priced `env_params` call at 2,900 would have made the division fail.
    **Ordering the readings by `before` descending recovers the timeline without trusting a single
    timestamp.** That is what made "at least 46.2 % of spend bought no data" statable.
95. **DO NOT LET A CLASSIFICATION ASSUME ITS OWN CONCLUSION.** The ledger's first version counted
    every call it could not name as a zero-tile failure and reported *"84.6 % of spend bought
    nothing"*. Nothing established that. It now reports a **floor from evidence (46.2 %) and a
    ceiling from possibility (76.9 %)**, with the four unidentified calls named as the gap between
    them. **A range you can defend beats a point estimate you cannot.**
96. **A GREEN SCHEDULED TASK MEANS THE PROCESS EXITED 0, NOT THAT THE WORK HAPPENED.** All three
    `FG-N26-*` tasks report `LastTaskResult 0` for today. All three bought zero tiles. The collector
    catches the vendor's empty response, records it and exits cleanly — which is correct behaviour
    and completely invisible from Task Scheduler. **`LastTaskResult` answers "did python run",
    never "did it get data".**

97. 🔴 **A `%+.1f` PRINTED NEXT TO THE WORD "COSTS" INVERTED A LOAD-BEARING CLAIM FOR TWO DAYS.**
    `backtest.py` computed `dh = r_with − r_without = +22.8` and printed
    *"knowing about the plume COSTS +22.8 h/yr"*. **The line contradicts itself on its face** — a
    positive difference in a gain is a benefit — and nobody read it that way because the narrative
    beneath it ("buys SAFETY, not HOURS") was confident and plausible. It propagated into HANDOFF
    §6.3 and §2.3 and stood until the meter reconciliation sent me back through the ladder.
    **The truth is better than the claim:** with the plume term the agent free-cools **17,511** hours
    with **3** breaches; without it, **17,462** with **11**. Both hours and safety, not a trade.
    **Three lessons.** (1) **A sign convention is a claim and must be tested like one** — `audit.py`
    now registers the B-rows with their ORDER asserted, so a future inversion fails a check.
    (2) **A confident sentence under a number is what stops the number being read** — the prose was
    doing the work the arithmetic should have done. (3) **Being wrong in your own favour is still
    being wrong**, and this project has now been wrong in both directions.
    **Running tally: checks wrong 13, product wrong 14.**

## New 2026-08-20, Session 1 of the per-site/live rework

98. 🔴 **THE AERIAL PANEL HELD THREE ASHBURN COORDINATES AS SOURCE-LEVEL CONSTANTS, AND THE
    OVERLAY IT DREW FOR THE OTHER TWO SITES WAS MEANINGLESS.** `SITE_BBOX`, `OSM_SRC`, `OSM_REC`.
    The footprint rings on top came from `T.site.geometry`, which IS per-site -- so selecting Chicago
    georeferenced **Chicago's halls onto Ashburn's photograph** through Ashburn's anchor. The panel
    looked entirely plausible, which is why it survived the per-site session that fixed twelve other
    panels. **The generalisable form: a panel is only per-site if EVERY input is per-site. Mixing
    one site's data with another's frame of reference produces a picture that is wrong in a way no
    reader can detect.** Fixed by `metros.committed_imagery()`, which reads the values from each
    metro's own `screen_manifest.json` -- and the frames for all three committed pairs were already
    on disk, so this was plumbing, not new data. Ashburn's manifest values are byte-identical to the
    constants they replace, so the change is provably a no-op there.
99. **A `<select id="c_site">` EXISTED TWICE, SO ONE OF THEM WAS PERMANENTLY EMPTY.**
    `querySelector` returns the FIRST match, so `buildSitePicker()` filled the stage-1 picker and
    the plume panel's copy -- a leftover from the layout before the three-stage rebuild -- rendered
    as a **"Data centre" dropdown with no options, on every site.** Nothing threw, nothing 404'd,
    every cross-language test passed. **`audit.check_duplicate_element_ids()` (check 2f) now fails
    the build on any repeated id**; the page has 96 and they are unique. Same family as #83 and #86:
    a defect that is invisible to every automated check and obvious in a screenshot.
100. 🔴 **MY OWN SPEND LEDGER LOST THREE CALLS THE SAME DAY I WROTE IT, BECAUSE IT TRUSTED A
    MUTABLE SINGLE-SLOT FIELD.** `api_usage_ledger.py` took the lowest meter reading among
    observations with `spent > 0`. `n26_manifest.json` keeps only the LAST meter pair it saw; when
    an **unbilled** call overwrote that slot (the 08-20 stall cost 0), the observation stopped
    satisfying `spent > 0`, dropped out, and the reported total fell **54,860 -> 42,200 -- the exact
    stale figure the script was written to prevent.** `audit.py` check 9 caught it within minutes.
    **A meter reading is evidence of cumulative spend whether or not the call that took it was
    billed. Never derive a running total from a field that gets overwritten.**
101. 🔴 **"ATTEMPTS" AND "BILLED CALLS" WERE INTERCHANGEABLE UNTIL 2026-08-20, AND THEN THEY
    WERE NOT.** Every failed request used to cost 4,220, so folding the collector's attempt counter
    into the billed-call partition was harmless. The vendor then started returning `status: failed`
    and stalling in `Processing` -- **both unbilled** -- so attempts x 4,220 stopped being a spend
    figure and over-counted by exactly one call. **The partition check PASSED anyway**, because the
    unattributable bucket absorbed the error: *a partition check that a miscount can satisfy is not
    checking the partition.* Now reported side by side and never summed.
102. **A `_shot_results.html` DRIVER COPY GOES STALE THE MOMENT `index.html` IS EDITED.** Two
    verification runs reported a newly added element as `MISSING` because the driver was a snapshot
    taken before the edit. **Regenerate the driver in the same command that shoots it** -- see
    section 8.1a.

103. 🔴 **MY SPEND LEDGER HAD A BLIND SPOT WORTH 46,420 CREDITS, AND `audit.py` REPORTED GREEN
    THROUGHOUT.** `api_usage_ledger.py` walks `testing/results/` for meter readings; `live.py` writes
    its output to `demo/`. So the first full 12-hour live run spent **46,420 credits — 44 % of
    everything this plan had ever spent — that no audited figure knew about**, and check 9 still
    passed, because it verifies that the DOCUMENTS match the LEDGER and never that the ledger sees
    everything. **A ledger with a blind spot is worse than no ledger, because it is trusted.** Fixed
    with `_append_spend_ledger()` writing one entry per run to `testing/results/live_spend.json`,
    **appending, never overwriting** (gotcha #100 was caused by exactly that). Second lesson, and the
    sharper one: **a check that compares two of your own artefacts proves they agree, not that either
    is complete.** Coverage of the SOURCE has to be checked separately from consistency.
104. **`completed` WITH AN EMPTY `features` ARRAY IS STILL BILLED, AND IT COST 33,760 IN ONE RUN.**
    The 12-hour run: 11 calls, 3 returned a field, **8 reported the job COMPLETE and carried no
    data, all 8 charged 4,220.** Meanwhile a `failed` job and a stalled job cost **nothing**. So the
    same vendor fault is free or expensive depending only on which way it presents — which is why
    the report to FortyGuard asks for the empty-completed case to be unbilled too, and thanks them
    for the two that already are.
106. 🔴 **A TOOL THAT WRITES DOCUMENTS WROTE `\g<1>26\g<2>` INTO ONE.**
    `bump_spend_docs.py` did `repl.replace("\\", "\\\\")` on its replacement templates, meaning
    to guard against a stray backslash in the data. What it actually escaped were the **`\g<1>`
    group references**, so `re.subn` inserted the literal text into **seven table rows of
    API-USAGE.md** -- visible garbage in a submission document, put there by the tool whose whole
    job was keeping that document correct. Fixed by making the replacement a **callable**, which
    `re` never interprets for escapes, removing the class of error rather than the instance.
    **Two smaller lessons from the same ten minutes:** the failure path printed a red-circle emoji
    and `UnicodeEncodeError`'d on the cp1252 console, so **the diagnostic crashed while reporting
    the problem it existed to report** -- a failure path is the last place to spend a character the
    terminal may not have. And the first version matched on the *current values* it was replacing,
    which made it a **one-shot**: it worked once and then silently matched nothing. It now matches
    on row LABELS and **reports every pattern that fails** instead of exiting 0. **Running tally:
    checks wrong 15, product wrong 14.**

105. **AN HOUR WITH NO FORECAST IS NOT AN HOUR "BLOCKED BY TEMPERATURE".** `bound` is NaN for a
    missing hour and `NaN <= limit` is False, so 8 no-data hours fell into the temperature bucket
    and the run reported *"blocked by temperature 11 h"* when only **3** hours were genuinely over
    the limit. **The artefact demonstrates its own bug: 3 + 8 = 11.** Missing hours are now counted
    separately, excluded from both gate counts, and a partial horizon is its own status
    (`ok_partial`). With an intermittent vendor **partial is the NORMAL case**, not an edge one.

107. 🔴 **THE WORST OUTPUT THIS PROJECT HAS PRODUCED: A SCHEDULE FOR HOURS THE AGENT NEVER
    LOOKED AT.** The user screenshotted a live run reading *"Decided at 2026-08-20 09:55 site-local
    for Ashburn ... horizon 12 h ... **0 live call(s), 3 cached, 0 credits**"* — with hours 1–3 from
    cache and **hours 4–12 marked `not_attempted` and scheduled MECHANICAL.** The agent had not
    asked about those nine hours. It had been refused the budget to ask. And the page presented the
    result as a live decision.
    **Root cause:** `not_attempted` (OUR budget/permission decision) was flowing into the same
    bucket as `completed_but_empty` (THE VENDOR'S failure). The `if not got:` guard only fired when
    **no** hour had data, so three cached hours were enough to carry nine unlooked-at hours into a
    published schedule, where the mechanical fallback read as a decision instead of an absence.
    **Fix:** `n_not_attempted` now short-circuits **even when some hours did return data**. A run
    that skipped any window reports `incomplete_not_attempted` and emits **no `hours` and no
    `commands` at all**. Every hour record carries a `no_data_reason` so the distinction cannot be
    lost downstream. **The rule, stated once: a schedule may only be published over hours the agent
    actually perceived.**
108. **A CALL CAP THAT COUNTED HOURS INSTEAD OF CALLS.** `serve_live.py` checked
    `LIVE_CALLS_MADE + hours > max`, so a 12-hour request was costed as 12 calls **even when 11
    windows were already cached** — refusing runs that needed one call, and incrementing the counter
    by 12 when it allowed them. A cached window costs nothing and must not consume a budget. Now
    `horizon_windows()` reports cache state per window, the cap is checked against **calls actually
    needed**, the remaining allowance is passed into the run and enforced where the calls happen,
    and the counter is **reconciled afterwards against the number really made**. Verified: 4 hours
    with 2 cached and an allowance of 1 refuses the **whole** run — *"needs 2 live call(s), 2 of 4
    windows already cached, only 1 remain"* — rather than fetching one hour and leaving three
    unlooked-at, which would have recreated #107.
109. 🔴 **`lead_h` WAS THE LOOP INDEX, NOT A LEAD.** The first window was
    `(now + 1h)` floored to the hour, so at **09:55** it was **10:00 — five minutes away — and
    labelled "lead +1 h"**. On a product whose entire thesis is *a thermometer cannot see three
    hours ahead*, and whose margin's calibration domain is expressed in lead hours, a lead
    mislabelled by up to an hour is a correctness bug rather than a cosmetic one. Now the first
    window is simply the next whole hour and **the lead is measured**:
    `lead_hours_for(now, window_start)`. The self-test pins it — a window 5 minutes out reports
    **0.083 h**, not 1.
110. **THE SERVER'S REFUSAL WAS OVERWRITTEN BY ITS OWN SUMMARY.** The UI wrote the refusal into
    `#livemsg`, then `drawLive()` overwrote that element with *"Decided at …"*. So a run the server
    had **explicitly refused to pay for** displayed as a completed live decision with the refusal
    nowhere on screen. Two separate elements now; `#liverefusal` is never touched by `drawLive`.
111. **A LONG-RUNNING SERVER SILENTLY SERVES STALE CODE, AND IT COST REAL DIAGNOSTIC TIME.** Python
    caches imported modules, so `serve_live.py` kept executing the `live.py` it started with. The
    screenshot above showed pre-fix wording **hours after the fix was written**, and the natural
    reading was *"the fix did not work"* — it had; the process was 48 minutes stale.
    `/api/health` now reports `code_loaded_utc`, `code_on_disk_utc` and `code_is_stale`, and the
    page shows a red banner instead of leaving anyone to compare timestamps by hand.
113. **A WARNING ABOUT A PROBLEM THE MACHINE COULD FIX ITSELF IS A WORKAROUND, NOT A FIX.** #111
    added `code_is_stale` to `/api/health` and a red banner, which was correct as far as it went --
    and it put the work on the operator: every edit meant noticing the banner and restarting by
    hand. `serve_live.py` now calls `reload_if_stale()` before answering `/api/health` and before
    starting any job, so **a run can never execute code older than the request that asked for it.**
    `importlib.reload` refreshes the module object in place, so later `LV.<name>` lookups get the new
    code while a job thread already holding the old `live_run` runs to completion rather than being
    torn out mid-flight — and `live.py` holds only constants and functions, so there is no mutable
    state to migrate. Verified by touching the file and watching `code_reloads` go 0 → 1 with no
    restart. **The banner survives as a fallback for the case a reload cannot happen** (a syntax
    error in the new file), and it now PREPENDS rather than replacing the mode line: the first
    version returned early and swallowed which mode the page was in, trading one missing piece of
    information for another.

112. **MY OWN TEST HARNESS LOST THE SAME RACE TWICE.** Chrome's `--virtual-time-budget` compresses
    `setTimeout` while the network stays real, so a poll loop of 40 × 400 ms elapses before an
    async job can answer — and the probe reported `hasresult=false`, which looks exactly like a
    broken UI. **Pre-run the job with `curl`, then point the driver at the completed job id.** Both
    times the code was correct and the harness was wrong. **Running tally: checks wrong 17,
    product wrong 18.**

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
| **Spent to date** | 🔴 **109,720 = 26 calls = 5.49 %.** Remaining **1,890,280**. **Re-derive it, never quote from memory: `python testing/api_usage_ledger.py`** |
| **⚠ Of that, 42,200 PROVABLY bought nothing** | **38.5 %** of spend. Ceiling **84,400 = 76.9 %**. §10 #93 |
| **⚠ THE LIVE AGENT IS NOW THE DOMINANT SPENDER** | One 12-hour run = **11 calls, 46,420 credits, 44 % of all spend ever**. **3 returned a field, 8 returned `completed` with no data and ALL 8 WERE BILLED** — 33,760 for nothing. §10 #103 |
| **⚠ THE PREVIOUS LINE SAID 42,200 = 10 CALLS = 2.11 %** | Stale by three calls, because the collector kept firing and no test re-read the figure. **`audit.py` check 9 now re-reads it and fails on the stale string.** §10 #93 |
| Forecast (future) windows | ⚠ **ONE success, 2026-08-19 13:35 UTC — and three failures since.** §4 is now qualified: read §4.0 |
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

**Added 2026-08-20, in order:** **`ticker.py`** (+ `demo/gen_ticker_cases.py`,
`demo/verify_browser_ticker.js`) · **`money.py`** · **`report.py`** · **`build_sites.py`** ·
`demo/gen_conformal_cases.py` · `demo/verify_browser_conformal.js` · root `money-sources.md` ·
root **`.gitattributes`**.
**Made metro-aware 2026-08-20:** `agent.py` (6 paths + `SITE_CENTRE`) · `backtest.py` ·
`rolling.py` · `money.py` · `explain.py` · `ticker.py` · `report.py`. `metros.py` gained
`demo_path()`, `site_centre()` and `METROS[k]["state"]`.
**`demo/index.html` was RESTRUCTURED** into the three-stage flow — §6.14.
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

Branch **`master`** (rename to `main` before any push). No remote configured; `gh` not installed.

| commit | what |
|---|---|
| `5289a5d` | initial — the research sprint |
| `fea3166` | endpoint probes, the credential-leak finding |
| **`d57b3b7`** | **Session D** + the whole `INTAKE-ARBITER/` tree, 186 files, 194 MB — it had been untracked |
| `fd90358` | Session F — the conformal arithmetic, derived in-browser, proved exact |
| `ee1cd1f` | Session G — money, sourced |
| `15dd952` | HANDOFF: Session H split into blocked / not-blocked |
| `403d916` | **every site genuinely its own** — §6.13 |
| `9d10a29` | **the PDF report**, written without a PDF library — §6.15 |
| `e2c832f` | **`.gitattributes`** — a fresh clone would have corrupted every PDF (§10 #82) |
| `e54a1af` | **the UI restructure** — §6.14 |
| **`872b488`** | **HEAD — surface the Run button (§10 #85)** |
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
  since fields change only when geometry does; `audit.py` check 2d `check_plume_fields` verifies the shipped ones) ·
  `run_all.py` **~273 s** (15 steps; ~100 s of it is Ashburn, the rest the two other sites) ·
  `build_sites.py` **~237 s** for three sites · `report.py` ~2 s for all three.
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
