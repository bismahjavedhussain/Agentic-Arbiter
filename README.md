# INTAKE-ARBITER

**An agent that decides, hour by hour, whether a data centre can switch its mechanical chillers off
and cool with outside air — and that earns the right to say yes more often by grading its own
accuracy against reality.**

FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)

> A thermometer cannot see three hours into the future, and a cooling plant needs that much notice
> to change mode. **FortyGuard's forecast is exactly the missing input.**

---

## The problem, stated as a contract

**Data-centre cooling-plant operators** struggle to **decide, each hour, whether to switch the
mechanical chillers off and cool with outside air** because **a rooftop thermometer cannot see three
hours ahead and a plant needs that much notice to change mode** — so they either switch late or
carry a conservative buffer. The result is **406 chiller-hours per year left on the table, worth
$5,522–$7,990 per MW of IT load**, measured across **43,763 hours of real weather** against the
reactive on-site-sensor control operators verifiably run today.

Every variable in that sentence is a measured number with a file behind it, not an estimate:
`audit.py` re-reads all of them. The dollar range is 16 cells — **4 published electricity tariffs ×
4 published chiller efficiencies**, swept rather than chosen, and **compressor-only**, which makes
it an upper bound on that term rather than a projection (§ *What is honest*).

---

## Start here — two commands

```bash
# 1. Prove it. 25 steps, ~6 minutes, ZERO API calls. Exits non-zero on any failure.
cd INTAKE-ARBITER/src && python run_all.py

# 2. See it — REPLAY mode, no API key needed, works offline.
cd INTAKE-ARBITER/demo && python -m http.server 8000        # then open http://localhost:8000
```

**To see it decide the next hours from a LIVE forecast**, serve it with the live agent attached
instead. This needs a FortyGuard key in `.env`:

```bash
cd INTAKE-ARBITER/src && python serve_live.py --allow-paid   # then open http://127.0.0.1:8000
```

**Why two commands and not one:** a static page cannot make a live API call, because the request
needs a key and anything the page can read, every visitor can read. `serve_live.py` holds the key in
its own process and returns only numbers. The page detects which mode it is in and says so — it does
not offer a live button that cannot work.

**New to this? Read [`READING-THE-AGENT.md`](READING-THE-AGENT.md) first.** It explains every
screen, every control and every graph from zero — no data-centre or statistics background
assumed, every term defined before it is used.

**`file://` will not work.** Browsers block `fetch()` from it and the page will show only a red
error. Any static host serves the demo as-is — there is no build step and no server side.

**If `run_all.py` is not green, do not believe a number on the page.** It re-reads **77 published
figures** from the files the code actually wrote and runs **160 audit checks**, including five that
re-derive the browser's own arithmetic against Python and one that drives a real browser to render
every site and diff the panels a reader would look at.

---

## What it does

Seven stages, all of them in code, in `INTAKE-ARBITER/src/agent.py`:

```
perceive  FortyGuard heatmap + env_params + real wind + its own accuracy record
  solve   576-solve GPU rise table on real building geometry (NVIDIA Warp)
  bound   Mondrian group-conditional conformal + plume-ensemble normalisation
  decide  a switching SCHEDULE under a switch budget and a dwell limit, by DP
  act     BMS/SCADA-shaped command rows, each carrying its own numbers
  explain deterministic, and every claim verified by re-running the agent
  score → recalibrate — the safety margin widens itself when reality proves it wrong
```

**What that buys, measured on 43,763 hours of real weather across five years** — 913 held-out days
the agent never calibrated on, on real Ashburn geometry, against the reactive on-site-sensor
incumbent that operators verifiably run:

| | |
|---|---|
| Free cooling delivered | **5,375 h/yr** by the rolling controller, hour by hour |
| Chiller-hours avoided vs the incumbent | **+406 h/yr** |
| …without a local sensor | **−156 h/yr — the agent LOSES.** The hours need one local reading |
| A published 12-hour plan holds | **94.1 %** of 21,879 re-plans change nothing at all |
| Bound coverage, measured | **65.6 %** against a 90 % promise — **it FAILED its pre-registration** |

The last two rows are the point. **The failure is on the front page of the demo, not in a
footnote**, and the "no local sensor" row says plainly that the headline evaporates without one.

---

## Who buys this, and how the first one starts

**The hero is a named role, not a market.** The critical-environments or facility engineer at a
colocation operator — the person who owns the PUE target, signs off on setpoint changes, and gets
called at 03:00 when an intake runs hot. They are the buyer because they carry both halves of this
trade: the energy number they are measured on, and the risk they personally absorb if a hall
overheats.

**What the pain costs them today, per megawatt of IT load:**

| | |
|---|---|
| Chiller-hours recoverable | **406 h/yr** vs the tuned reactive incumbent |
| Value of those hours | **$5,522 – $7,990 per MW-IT per year** |
| A 30 MW hall | **$166,000 – $240,000 per year** |
| Basis | 16 cells: 4 published tariffs × 4 published chiller efficiencies, **swept, not chosen** |

⚠ **Compressor-only, and therefore an upper bound on that term.** Fans, chilled-water pumps,
condenser pumps and tower fans keep running, and an airside economizer moves *more* air — so the
unmeasured fan term has the **opposite sign**. We did not find a defensible °C→fan-kWh conversion in
any primary document, so it is excluded and labelled rather than estimated. Sources in
[`money-sources.md`](money-sources.md).

### The wedge: shadow mode, and it needs nothing from their plant

The smallest sellable unit is **not** control. It is a **30-day shadow trial**:

1. The agent publishes a 12-hour switching schedule each hour, for their site's real geometry and
   their own weather station.
2. **The operator ignores it.** No BMS integration, no setpoint written, no procurement, no risk.
3. After 30 days, compare what the agent said against what actually happened — hour by hour, with a
   reason attached to every hour.

That comparison artefact already exists and already ships: the per-site PDF this repository
generates is exactly the document a shadow trial produces. **The demo you can run right now is the
product's first deliverable**, not a mock-up of it.

**Why shadow mode is the right wedge and not a hedge:** a cooling plant will not hand control to
software it has not watched, and no procurement process starts with write access to a chiller.
Shadow mode is how this class of product is actually bought — and it is also the honest sequencing,
because the one thing this project cannot yet claim is a 90 % bound on live forecasts (§ *What is
honest*). Thirty days of shadow data is simultaneously the sales motion **and** the missing
calibration set: it produces the ~9 measured day-pairs the bound needs. **The trial that earns the
customer is the same trial that finishes the science.**

### What we do not have

No signed pilot, no letter of intent, and no operator interview. The pain is evidenced from
published sources — LBNL instrumented eight real data centres and documented *why* operators avoid
free cooling — not from a customer conversation we have had. **That is the biggest hole in the
commercial case and it is stated rather than papered over.**

---

## Useful AI — and where we deliberately did not use one

**There is no LLM anywhere in this product, and that is a decision we can defend line by line
rather than an omission.** The test we applied: *if deterministic code solves it exactly, at zero
variable cost and zero latency, an LLM is a liability rather than a feature.*

The decision is recorded in the emitted artefact, not just in prose — `demo/explanations.json`
carries `local_model_used: false` and the reason it was declined:

> *"no inference stack installed … and this stage reports numbers the agent already computed —
> **deterministic generation plus verification is safer than generation plus hope**"*

And it was declined on the merits, not on capacity: the same file records the GPU headroom measured
at the time — **371 MiB peak of 6,141 available**, so a small local model would have fitted
comfortably. We had the room and chose the verifiable path.

| Job | What does it | Why not a model |
|---|---|---|
| Deciding the switching schedule | **Dynamic programming** over `(mode, switches used, dwell owed)` | The optimum under a switch budget and a dwell limit is *exactly* computable. A model would approximate a solved problem, and could not carry a hard constraint |
| The safety margin | **Split conformal prediction** — Mondrian, group-conditional, 20/20 self-tests | A distribution-free finite-sample guarantee. No learned uncertainty head offers that, and this one is falsifiable — ours failed its pre-registration and we published the failure |
| Explaining every decision | Deterministic templates, and **30 stage-event templates in which no template may contain a literal digit** — enforced at build time | A generated explanation cannot be verified against the decision it explains. Ours is re-derived and checked: **1,336 explanations, 0 verification failures** |
| Reading the vendor's field | Nearest-tile lookup on real coordinates | It is a spatial index, not a judgement |

**Where machine compute *is* load-bearing, because rules genuinely break down there:** the plume
field. **576 coupled advection–diffusion solves** across 72 wind bearings × 8 wind speeds on the
rasterised OpenStreetMap footprints, run on the GPU through **NVIDIA Warp in 5.34 s**. There is no
closed form for exhaust recirculation between two irregular buildings — that is precisely the
"rules-based logic naturally breaks down" case, and it is where the compute budget goes.

**The agent's execution scope is constrained on purpose, and narrowly:**

- **Two actions.** Free cooling, or mechanical. That is the entire action space.
- **Safety is a hard constraint, not a penalty term.** There is no invented exchange rate between a
  degree of risk and an hour of chiller. An earlier prototype needed `c_excursion = 120.0` to
  produce an answer at all; that number had no source, so the whole approach was discarded.
- **It refuses.** When the intake disc would average the exhaust it is meant to measure, the solver
  declines to answer and the agent **falls back to mechanical** — a refused bearing is not
  permission.
- **Bounded actuation.** A switch budget and a minimum dwell, both cited to operator practice rather
  than chosen by us.
- **It cannot act on a perception it does not have.** When the vendor returns no field, the live
  agent emits **no schedule at all** — not an interpolation, not a carried-forward value, not a
  saved field relabelled as live.

**What this buys in cost terms:** the decision path has **zero variable inference cost and zero
model latency**. Every FortyGuard credit is spent on *perception* — the one thing we cannot compute
ourselves — and none on reasoning we can do exactly.

---

## What is honest about this, and what is not

Read [`INTAKE-ARBITER/PLAN.md`](INTAKE-ARBITER/PLAN.md) for the full design record — every claim
there carries a citation and a link, verified by opening the source. The short version:

**Established.** Seven-stage loop over **120,960 swept scenarios**. Conformal layer with **20/20
self-tests** — Mondrian, CQR, ACI/DtACI, joint coverage, worst-group. Physics validated against an
analytic plume at **0.00 %**, heat conserved at **0.00 %**, **67 Prairie Grass** field experiments,
and 6 instrumented condensers at **r = 0.798**. **1,336 explanations with 0 verification failures.**
A reasoning tape whose **32 templates contain not one literal digit**, checked at build time.
**Three sites live on their own geometry, weather, bound and tariff — and two more were refused on
aerial evidence.**

**On the size of the verification surface**, because it is fair to ask: **160 audit checks and a
gotcha log running to #161 exist because every entry in it actually bit** — a NaN that
was legal Python JSON and illegal standard JSON, a rounded array that flipped decisions at gate
boundaries, an invented constant that outlived its own retraction by a day, a site picker that
swapped one file out of thirteen. Every check is a headstone. That is **validation** infrastructure,
and it is the only infrastructure here: there is **no Kubernetes, no vector database, no message
queue, no microservice and no build step** — the interface is one HTML file with one inline script,
and the whole thing rebuilds and re-verifies in about five minutes on one laptop. **Scale is a
problem we have deliberately not solved yet.**

**Not established, and labelled as such everywhere it appears.**

- **The 90 % bound is not proven on live forecasts, and the reason is sample size rather than
  method.** Two separate things, kept separate because collapsing them misdescribes both:
  - **The method is validated.** The conformal layer passes **20/20 self-tests**, and on the
    five-year record **all 12 per-lead bounds cover ≥ 90 %**.
  - **The live calibration is under-sampled.** A 90 % one-sided bound needs **9 calibration
    day-pairs; 4 exist.** At n=4 the attainable coverage ceiling is n/(n+1) = **80 %**, so 90 % is
    *arithmetically* unreachable — not methodologically refuted. Measured coverage on held-out days
    is **65.6 %**, which **failed its pre-registration**, and that is the only figure we quote.
  
  So this is a data-collection gap with a known fix — 5 more day-pairs — currently blocked by the
  vendor outage in [`API-USAGE.md`](API-USAGE.md) §5. **A 30-day shadow trial produces exactly that
  calibration set**, which is why the commercial wedge and the remaining science are the same
  activity.
- **The agent is an adaptive controller with a self-calibrating boundary, not a stopping rule.**
  Seven pre-registered "when to act" decision cores were tried and **all seven failed**; they are
  documented rather than deleted (`PLAN.md` §6).
- **Money covers the chiller compressor term only**, from two documents parsed in this repository
  ([`money-sources.md`](money-sources.md)). The fan, pump and tower term is **not sourced and not
  claimed** — and it has the opposite sign.
- **Claims that were retracted are listed as retracted**, with what killed each one
  (`HANDOFF.md` §2.3).

---

## Where things are

| Path | What is there |
|---|---|
| [`INTAKE-ARBITER/`](INTAKE-ARBITER/) | The product. `src/` is 24 modules, `demo/` is the interface, `PLAN.md` is the citation-bearing design record |
| [`INTAKE-ARBITER/demo/`](INTAKE-ARBITER/demo/) | One HTML file, one inline script, no build step, no dependencies. **Zero API calls at view time** |
| [`API-USAGE.md`](API-USAGE.md) | How much of the FortyGuard plan was used, derived from the credit meter rather than asserted: **13 calls, 54,860 credits, 2.74 %** |
| [`fortyguard-api-findings.md`](fortyguard-api-findings.md) | 1,105 lines of field findings written for the FortyGuard team — with a section listing the suspicions that **failed retest and were withdrawn** rather than deleted |
| [`money-sources.md`](money-sources.md) | Every price and efficiency figure, with the document and page it came from |
| [`HANDOFF.md`](HANDOFF.md) | The working log. Long, blunt, and includes **96 gotchas that each actually bit**, plus a running tally of how often this project's own verification code was wrong |
| [`testing/`](testing/) | Every experiment, including the failures. `scan_secrets.py` and `api_usage_ledger.py` are the two you can run for free |
| [`*-PREREG.md`](.) | Pre-registrations with dated amendment logs, written **before** each test ran |
| `damper-*.md`, `project-master-plan*.md` | An earlier project direction, abandoned. Kept because the reasoning that killed it is part of the record |

---

## Reproducing the parts that cost nothing

```bash
python testing/api_usage_ledger.py           # the API spend ledger, from saved meter readings
python testing/scan_secrets.py               # full tree AND full git history, for leaked keys
python testing/test_n26_coverage.py dryrun    # what the collector would do now; no key is read
python testing/test_n26_coverage.py selftest  # its retry budget, against all 5 measured vendor faults
python testing/n26_recovery_watch.py plan     # what the recovery watcher would spend today; spends 0
python testing/n26_chicago_offset.py dryrun    # Chicago's own level offset: window, lead, cost. Spends 0
python testing/verify_site_panels.py          # renders every site in real Chrome and diffs the panels
cd INTAKE-ARBITER/src && python audit.py      # 160 checks, 77 published numbers re-read
cd INTAKE-ARBITER/src && python report.py     # the per-site PDF, verified by being reopened
```

All five make **zero API calls**.
