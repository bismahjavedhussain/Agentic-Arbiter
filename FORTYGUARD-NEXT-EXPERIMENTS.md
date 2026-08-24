# Experiments to run the moment FortyGuard's data path returns — pre-registered

**Written 2026-08-23.** Every experiment below is specified *before* it is run: the payload, the
cost, the pass/fail condition, and what it would **not** establish. That ordering is the project's
methodology rule 2 and it is what stops a result being reinterpreted after the fact.

**Background:** `FORTYGUARD-VALUE-AUDIT.md` — what their API offers versus what we consume.
**Blocker:** every `/v1/heatmap` window, past and future, has returned `completed` with `n_cells: 0`
since 2026-08-18. Five days. Collectors are disabled.

---

## E1 — Is `env_params` alive while `heatmap` is down? 🔴 RUN THIS FIRST

**The hypothesis (the user's, 2026-08-23):** the fault is specific to `/v1/heatmap`, and
`/v1/env_params` is serving normally.

**Why it is the first thing to run and not the third.** It is the cheapest call we can make
(**2,900** vs 4,220), it is diagnostic regardless of outcome, and if it passes it **unblocks E2
immediately** — meaning we could demonstrate new FortyGuard-powered agent behaviour *during* the
heatmap outage rather than waiting it out. It also sharpens the vendor report from *"your API returns
empty"* to *"your heatmap returns empty while your env_params serves the same AOI and hour normally"*,
which is a far more actionable thing to hand an engineer.

**Payload** — the same AOI centre and the same hour we would ask `heatmap` for, so the two are
comparable:

```json
POST /v1/env_params
{ "polygon_aoi": { "...8x8 km box centred 39.024017, -77.419691..." },
  "date_time": { "start_date": "<site-local today>",
                 "start_time": "00:00", "end_time": "23:00", "filter_type": 2 } }
```

`filter_type: 2` with 00:00–23:00 returns **24 hourly values per field** — one call covers the whole
day including the forecast hours, which is why this is cheap per hour of coverage.

**Pre-registered outcomes:**

| Result | Conclusion |
|---|---|
| Returns populated hourly arrays | ✅ **H1 SUPPORTED.** The fault is heatmap-specific. E2 becomes buildable today, and the vendor report gains a clean contrast case |
| Returns empty / errors the same way as heatmap | ❌ The fault spans endpoints. Not a wasted call — it removes the "just heatmap" hypothesis and tells FortyGuard the blast radius is wider than they may think |

**Cost:** 2,900 credits, one call.
**What it does NOT establish:** nothing about whether the *values* are correct — only that the path
serves data. Field correctness is E2's problem.

---

## E2 — Put all three gates on FortyGuard's own forecast

**The gap.** The live agent perceives **one** FortyGuard variable. Its humidity gate runs on NWS and
its air-quality gate does not run at all:

| Gate | Live agent today | After E2 |
|---|---|---|
| Dry-bulb | FortyGuard `heatmap` | FortyGuard `heatmap` |
| Humidity / dew point | **NWS** | **FortyGuard `env_params`** (`wet_bulb_temperature_celsius`, `relative_humidity_percent`) |
| Air quality / contamination | **not evaluated** | **FortyGuard `env_params`** (six indices) |
| Wind | NWS | NWS — they have no wind field (our filed feature request) |

**The decisive fact, already paid for.** `env_params` **serves the forecast horizon**:
`testing/test_n15_forecast_state.py` asked for `now + 6 h` and got a full set back —
`testing/results/fixtures/n15_ep_future.json`: RH **87.2 %**, wet-bulb **22.6 °C**, cloud **100 %**,
precipitation **0.3 mm**, all six air-quality indices. So this is an integration job, not a research
question.

**Why it matters beyond tidiness.** LBNL's instrumented study of eight data centres is this project's
*commercial thesis* — contamination and humidity, not temperature, are the documented reasons
operators refuse free cooling. FortyGuard sells six air-quality indices. **The live agent currently
ignores them**, so the argument is asserted and never exercised.

**Implementation** — small, because the pieces exist:
- `environment.py` already parses every one of these fields and audits two as defective.
- `live.py` already batches, polls, classifies and caches vendor calls.
- One extra call in `perceive_ambient()`; one gate evaluation that already exists in the backtest.

**Pre-registered pass condition:** a live run emits a schedule in which at least one hour is blocked
by the humidity or air-quality gate **using FortyGuard values**, with provenance recorded per hour,
and `live.py selftest` still passes offline.

**Cost:** 2,900 per run, on top of the heatmap calls. Windows cache like heatmap windows do.
**What it does NOT establish:** that FortyGuard's humidity is *better* than NWS's. We have no
measured comparison and must not imply one. The claim is coverage — every gate on one vendor's
forecast — not accuracy.

⚠ **Keep the honest note that `env_params` reports a fixed `GMT-5` offset and does not apply daylight
saving** (findings §1.8). Our windows are built in the AOI's zone, so the hourly array must be aligned
deliberately rather than assumed.

---

## E3 — Can their field replace the customer's thermometer? 🔴 THE BIG ONE, AND UNVALIDATED

**The weakness it attacks.** The agent's headline needs a **level anchor** — one local temperature
reading — because its weather station is **9.38 km** from the plant. Measured over five years,
without it the agent **loses 156 h/yr** instead of gaining 406: a **562 h/yr** swing, and the biggest
caveat on the demo's front page (*"the safety guarantee needs no customer hardware; the hours do"*).

**The idea.** That station→site offset is exactly what a 2 m urban-heat product is for. One `heatmap`
call over a box containing **both the site and its ASOS station** measures it directly — no customer
hardware, no installation, no procurement. If it works, the product's largest limitation becomes a
second reason to buy FortyGuard data.

**Measured feasibility, not guessed:**

| | |
|---|---|
| Site → KIAD station | **9.38 km** |
| Box needed to contain both | **~21 × 21 km** |
| Tiles at granularity 60 m | ~120,000 — far beyond the 17,862 we have ever seen returned |
| Tiles at granularity 100 m | **~43,000** — the value to try |
| Precedent | findings §3.2: spatial information content is set by **AOI size**, not granularity |

**Pre-registered outcomes:**

| Result | Conclusion |
|---|---|
| A populated field covering both points | Proceed to validation — score the field's predicted station→site offset against the **43,763 hours** of KIAD observations we already hold. **Free**, no further calls |
| Empty, truncated, or capped below the box | The idea is dead at this AOI size. Record the cap as a finding and report it — an undocumented AOI ceiling is worth telling them about |

**Cost:** 4,220, one call, plus zero for validation.
**What it does NOT establish, and this is the important one:** a returned field proves *coverage*, not
*skill*. Whether their 2 m field genuinely resolves a 9 km microclimate gradient is the actual
question, and only the validation against KIAD answers it.

🔴 **If E3 appears in the submission at all, it must be framed as the experiment we would run next —
never as a capability.** The whole credibility of this project rests on not doing that.

---

## Priority, cost and sequencing

| # | Experiment | Cost | Blocked by | Buys |
|---|---|---|---|---|
| **E1** | Is `env_params` alive? | 2,900 | nothing — **runnable the moment you authorise it** | Diagnosis either way; unblocks E2 |
| **E2** | All three gates on their forecast | 2,900/run | E1 passing | Turns "we use their temperature" into "every gate runs on their forecast" |
| **E3** | Wide-AOI anchor replacement | 4,220 | the heatmap path recovering | Would remove the −156 h/yr caveat |

**Total to answer all three: 10,020 credits** — about 0.6 % of the plan, against 1,662,400 remaining.

**E1 does not depend on the heatmap fault clearing.** E3 does.

---

## Ready to run

`testing/diag65_env_params_alive.py` implements E1 with the same discipline as DIAG-62/63/64:
pre-registered conditions in the docstring, a free `dryrun` mode, `--allow-paid` required, meter
readings before and after, the shared vendor classifier, and the result saved to
`testing/results/`.

```bash
python testing/diag65_env_params_alive.py dryrun          # free: the payload and the cost
python testing/diag65_env_params_alive.py run --allow-paid # 2,900 credits
```
