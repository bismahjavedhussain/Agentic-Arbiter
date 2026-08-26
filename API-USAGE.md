# FortyGuard API usage — INTAKE-ARBITER

**A submission requirement, answered with the meter rather than with recollection.**
Every figure below is re-derived by one command that makes **zero API calls**:

```bash
python testing/api_usage_ledger.py
```

It reads the usage-endpoint readings that each paid script saved beside its own results, reconciles
them against the plan's issued total, and refuses to report a call count that is not a whole
multiple of the measured price. Its output is written to `testing/results/api_usage.json`, which
`INTAKE-ARBITER/src/audit.py` re-reads — so a number in this document cannot drift away from the
evidence without a test failing.

---

## 1. The headline

| | |
|---|---|
| Plan | **`Hackathon`**, issued **2,000,000** credits, active 2026-08-18 → 2026-09-22 |
| **Paid calls made** | **194** — 188 `heatmap` + 6 `env_params` |
| **Credits spent** | **810,760** |
| **Share of the plan used** | **40.54 %** |
| Credits remaining | **1,189,240** |
| Calls at demo view time | **0 in REPLAY** (the default, and what a static host serves). **LIVE mode calls one heatmap per forecast hour** — see §6 |

**The call count is bounded by the clock, not the budget**, and for two reasons that pull in
opposite directions. The good one: **the daily cap of 30 heatmaps binds long before credits do**, so
the design question was never "how many calls can we afford" but "which single call earns its
place". The bad one: **the forecast endpoint spent most of this plan's active life returning
`completed` with zero tiles**, and through 2026-08-20 a request that returned nothing was **still
billed 4,220** (§5). That changed on 08-20 itself: the vendor began returning `status: failed` and
stalling in `Processing`, and **both of those are unbilled** — so the same fault now costs credits
or not depending on which way it presents.

**Most of the research behind this project was not paid for at all.** About **125 calls** were made
on 2026-08-11…17 against a key whose billing cycle had closed on 2026-07-19 and whose meter was
**frozen** — every reading before and after those calls is identical at `cycle_remaining = 180,980`.
Those calls returned real data, and the four calibration day-pairs the conformal layer is built on
came from them. They are reported separately here because counting them as spend would be wrong and
pretending they never happened would be worse.

---

## 2. Endpoints used, and what each cost

Prices were **measured**, not read off a price list: the usage endpoint is free, so every paid
script calls it immediately before and immediately after its one paid request and saves both
readings.

| Endpoint | Credits | Measured how | Used for |
|---|---|---|---|
| **`POST /v1/heatmap`** | **4,220** | differencing the meter, repeatedly | Every paid call in this project. 8×8 km AOI, granularity 60, `analytic_type: tcm`, 2-hour window |
| `POST /v1/env_params` | **2,900** | the `activity_breakdown` field | Humidity, dew point and six air-quality indices — the gates the agent needs beyond temperature |
| `POST /v1/satellite` | 14,400 | `activity_breakdown` | Probed once for site screening; not used in the shipped pipeline |
| `POST /v1/heat_intelligence` | 8,600 | `activity_breakdown` | Probed; **returns the caller's API key inside the `download_link` path**, so its raw responses are gitignored |
| `POST /v1/streetview` | — | never completed (240 s timeout) | Probed; abandoned |
| `GET /v1/status/{activity_id}` | **free** | unchanged meter across 59 polls | Polling a submitted activity to completion |
| `POST /v1/system/fetch-api-key-usage` | **free** | unchanged meter | The meter itself — which is what makes this ledger possible |

**Two endpoints were billed, and the meter proves the split.** This section used to argue the spend
was pure `/v1/heatmap` because 4,220 divided the total exactly. That stopped being true once the
live agent started buying humidity and dew point, and the honest statement is now the arithmetic
one: **188 × 4,220 + 6 × 2,900 = 810,760**, matching the lowest meter reading ever recorded to the
credit. Both prices were measured the same way, so this is a derivation and not bookkeeping — and if
a third endpoint were ever billed, the reconciliation would **stop closing and say so** rather than
absorbing it silently.

---

## 3. The 194 calls, itemised

**99 calls** saved a before/after meter pair and so are individually attributable; the remaining
**92** are visible only as gaps between readings and are counted, not named. Five of the attributable
ones are named below as worked examples. The distinction is kept because *"11 of 13 calls returned
zero tiles"* is only worth saying if the number is arithmetic rather than memory.

⚠ The 92-call gap figure is **derived at the heatmap price** and so is approximate to ±1: the gaps
leave a 1,320-credit remainder that no whole number of either endpoint explains. The credit total is
exact; that call count is not, and it is reported rather than rounded away.

| Meter before → after | Call | Returned |
|---|---|---|
| 1,987,340 → 1,983,120 | `n55_keysize` — is a large AOI capped? | **17,862 tiles** |
| 1,978,900 → 1,974,680 | `diag61` — is the forecast blocked by horizon, entitlement or outage? | **0 features** |
| 1,966,240 → 1,962,020 | `diag62` — forecast recheck, 9.41 h lead | **17,862 tiles** |
| 1,962,020 → 1,957,800 | `chicago_field` — a second metro's own field | **17,797 tiles** |
| 1,949,360 → 1,945,140 | N-26 collector, third attempt of 2026-08-20 | **0 features** |

Classified by what the artefacts record:

| | Calls | Credits |
|---|---|---|
| Returned a populated field, tile count saved | **37** — 31 heatmap + 6 `env_params` | 148,220 |
| Returned `completed` with **zero** features, individually attributed | **54** | 227,880 |
| Not individually attributable — a gap between two readings | **103** | 434,660 |

Those three rows sum to 194 and to 810,760, which is the check that keeps this table honest.

So **28.1 %** of spend is *proven* to have bought nothing, and the ceiling — if every unattributable
call also failed — is **81.7 %**. The vendor record makes the ceiling far likelier than the floor:
across 08-18…08-20 the forecast leg failed **every single time it was tried.** The collector's
08-18 and 08-19 attempts predate the per-day attempt counter it gained on 08-19, which is why their
individual count is not recoverable and is not claimed.

⚠ **Attempts are not billed calls, and since 2026-08-20 they are not even close.** The collector
records **10** failed attempts across **4** days; at least one of those cost **0** credits, because
the vendor began returning `status: failed` and stalling in `Processing` — both unbilled. Any figure
computed as *attempts × 4,220* is therefore not a spend figure, and the ledger reports the two
quantities side by side rather than summing them.

---

### 3a. The live agent is now the dominant spender, and one run shows why

`src/live.py` fetches **one heatmap window per forecast hour**, because a heatmap response is a
per-tile aggregate **over the window** rather than a time series. The first full 12-hour run
(2026-08-20) is the clearest single record of what this endpoint costs when it half-works:

| | |
|---|---|
| Calls | **11** live (one window was already cached, so it cost nothing) |
| Spent | **46,420 credits** — **5.7 %** of this plan's spend today, in one run. It was **44 %** on the day it was made, which is the better measure of how sharp this endpoint's cost is |
| Returned a field | **3** — a real rising morning trajectory, 25.66 → 28.84 → 30.71 → 32.23 °C |
| Returned `completed` with **no data** | **8**, and **all 8 were billed** — **33,760 credits for nothing** |

That is the billing asymmetry in §5 stated in money: a `failed` job and a stalled job cost nothing,
but a job that reports itself **complete** while carrying an empty `features` array is charged in
full. In this run that distinction was worth 33,760 credits.

**Live spend is recorded in `testing/results/live_spend.json`, one entry per run with one record per
call.** That file exists because it had to: `live.py` writes its output to `demo/` and the ledger
walks `testing/results/`, so the first 12-hour run spent 46,420 credits that **no audited figure
knew about** — while `audit.py` check 9 still reported green, because it verifies that the documents
match the ledger and not that the ledger sees everything. **A ledger with a blind spot is worse than
no ledger, because it is trusted.**

## 4. Spending discipline

The rules were fixed before the plan was issued and are visible in the code, not just asserted here:

- **Every diagnostic call was individually authorised by a human before it was made**, and the
  authorisation is recorded inside the result file it produced (`"authorised_by_user":
  "2026-08-19"`, `"api_calls_made": 1`). The N-26 collector is the one exception and is not claimed
  otherwise: it fires from a scheduled task, so it runs under a **standing** authorisation bounded
  by the daily cap below rather than a per-call one. That is the whole reason the cap exists.
- **Two separate daily caps in `testing/test_n26_coverage.py`, because there are two different
  risks.** `MAX_BILLED_FORECAST_ATTEMPTS_PER_DAY = 3` is the **credit** budget and counts only
  attempts FortyGuard actually charged for; `MAX_TOTAL_FORECAST_ATTEMPTS_PER_DAY = 8` is the
  **runaway** guard and counts every attempt, billed or not. The attempt is written to the manifest
  **before** the call, so a crash mid-call still counts. The credit budget is overridable with
  `N26_MAX_ATTEMPTS` for a deliberate, attended retry — because **a lost day-pair is unrecoverable
  while 4,220 credits is 0.2 % of the plan.**

  **Why it was split on 2026-08-21.** Until 2026-08-20 every failed request cost 4,220, so
  "attempts" and "billed calls" were the same number and one counter could serve both purposes.
  Then the vendor began failing two ways that are **free** — `status: failed`, and an indefinite
  stall in `Processing` — while `completed`-with-no-data stayed **billed**. A budget written to
  ration credits was from that day being consumed by failures that cost none. The classifier that
  decides which is which is `common.classify_vendor`, **the same function the live agent uses**, and
  the split is exercised offline by `python testing/test_n26_coverage.py selftest` — 24 assertions,
  zero API calls, no key read, and it is step 16 of `run_all.py`.

  **What the split does not buy.** On a day whose failures are all `completed`-with-no-data
  (2026-08-21: four of four) every attempt is billed and the split changes nothing. On a day that
  stalls (2026-08-20) it permits the whole in-band window to be probed for zero credits.

- **Every attempt is now recorded individually**, not counted. The manifest carries a
  `forecast_attempt_log` per day holding each attempt's vendor class, whether it was billed, its
  activity id, poll count, elapsed time and the HTTP body of any rejection. The previous record was
  a single integer plus the *last* error string, and both lost information that had already cost
  real money to recover: a mutable single-slot meter field lost three calls from the ledger, and a
  rejection's status and body — the only fields that explain *why* — were gone by the time anyone
  asked.

- **A recovery watcher exists, and it is attended by design**: `testing/n26_recovery_watch.py`.
  `plan` reports what it would do for zero credits and no key read; `watch --allow-paid` spreads the
  remaining **billed** attempts across the rest of the in-band window and retries a **free** failure
  almost immediately. It makes no API call of its own — every attempt goes through the collector and
  its two caps, so the watcher cannot spend anything the collector would have refused.
- **The collector refuses to spend when the data would not be comparable.** If the lead to the
  target window falls outside 6.0–11.5 h, it skips the day rather than buying a forecast whose
  accuracy is not exchangeable with the ones already collected. A short-lead forecast is much more
  accurate, so recording one would have *flattered* the coverage figure.
- **A free dry-run verifier exists**: `python testing/test_n26_coverage.py dryrun` reports what the
  collector would do — window, true lead, in-band firing window, outcome debt, pair arithmetic —
  with **zero API calls and without reading the key at all.**
- **The key is never printed, logged or committed.** It is read only through
  `testing/common.py:load_key()`. `python testing/scan_secrets.py` scans every tracked file **and
  every blob in git history** for it, reporting matches as `len=… sha256=…` redactions so the scan
  report can never become the leak.

---

## 5. What we reported back to FortyGuard

Two findings were written up for the engineering team. Both are in
**[`fortyguard-api-findings.md`](fortyguard-api-findings.md)** (1,105 lines, 10 sections, with exact
reproduction payloads).

**A. `completed` with zero tiles has at least four different causes, and all of them are billed.**
An out-of-range area, an unavailable window, a permission problem and a service incident are
**indistinguishable** on the status endpoint: all four return `HTTP 200`, `status: completed`, and an
empty `features` array. A client cannot tell "you asked for the impossible" from "we are broken",
and is charged 4,220 either way. Requested: an incident signal, a non-`completed` status on
failure, and no billing for an empty result.

**B. A ~30-hour forecast outage, which we first misread as a plan limitation.**
Between 2026-08-18 and 2026-08-19 08:30 UTC, forecast-window requests returned zero tiles
repeatedly. We initially concluded the Hackathon plan did not include forecast windows — and that
conclusion was **wrong**, retracted after `diag62` returned 17,862 tiles at a 9.41 h lead on
2026-08-19 13:35 UTC. The evidence that pins it to an outage rather than an entitlement: the same
automated request **failed at 08:30 UTC and succeeded at 13:35 UTC the same day.** An entitlement
does not appear during a day.

**⚠ Still open as of 2026-08-20.** The N-26 collector's forecast request has now returned
`completed` with zero features on **three consecutive days** — 08-18, 08-19 and 08-20, the last with
three attempts at 08:30, 08:50 and 09:15 UTC. Every forecast failure was a call made **before
12:00 UTC**; the one forecast success was made at **13:35 UTC**. Past-window requests worked
throughout. We are not claiming a cause — the target hour and the call clock time are locked
together by the lead constraint and cannot be varied independently — but **the forecast path is not
reliably available**, and no figure in this project depends on assuming otherwise.

---

## 6. Zero API calls at demo time

The interface (`INTAKE-ARBITER/demo/index.html`) makes **no FortyGuard calls at all**. It replays
saved responses from `demo/field_*.json`, and it says so on screen: *"Everything below runs from
saved FortyGuard responses: 0 live API calls."*

That is a correctness requirement, not a convenience. **N-55 established that re-requesting the same
window returns 17,862 of 17,862 tiles byte-for-byte identical, max |Δ| = 0.00000000 °C** — so a
replayed field is not an approximation of the live API, it is the same values. It also means a judge
can run the whole demo offline, and that the numbers on screen cannot silently change under a
reader's feet.

---

## 7. Where to look next

| Document | What is in it |
|---|---|
| [`fortyguard-api-findings.md`](fortyguard-api-findings.md) | 1,105 lines of field findings written for the FortyGuard team: confirmed defects with reproduction payloads, documentation gaps, **and a §4 listing the suspicions that failed retest and were withdrawn rather than deleted** |
| [`testing/api_usage_ledger.py`](testing/api_usage_ledger.py) | The ledger that produces every number above, from saved meter readings. Zero API calls |
| [`testing/scan_secrets.py`](testing/scan_secrets.py) | Full-tree **and full-history** secret scan, run before publication |
| [`testing/test_n26_coverage.py`](testing/test_n26_coverage.py) | The collector: retry budget, comparability guard, and a free `dryrun` mode |
| [`INTAKE-ARBITER/PLAN.md`](INTAKE-ARBITER/PLAN.md) | The design record, with a citation and a link for every claim |
