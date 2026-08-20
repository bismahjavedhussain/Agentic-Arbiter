# INTAKE-ARBITER

**An agent that decides, hour by hour, whether a data centre can switch its mechanical chillers off
and cool with outside air — and that earns the right to say yes more often by grading its own
accuracy against reality.**

FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)

> A thermometer cannot see three hours into the future, and a cooling plant needs that much notice
> to change mode. **FortyGuard's forecast is exactly the missing input.**

---

## Start here — two commands

```bash
# 1. Prove it. 15 steps, ~4.5 minutes, ZERO API calls. Exits non-zero on any failure.
cd INTAKE-ARBITER/src && python run_all.py

# 2. See it. Then open http://localhost:8000
cd INTAKE-ARBITER/demo && python -m http.server 8000
```

**`file://` will not work.** Browsers block `fetch()` from it and the page will show only a red
error. Any static host serves the demo as-is — there is no build step and no server side.

**If `run_all.py` is not green, do not believe a number on the page.** It re-reads **70 published
figures** from the files the code actually wrote and runs **61 audit checks**, including five that
re-derive the browser's own arithmetic against Python.

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

## What is honest about this, and what is not

Read [`INTAKE-ARBITER/PLAN.md`](INTAKE-ARBITER/PLAN.md) for the full design record — every claim
there carries a citation and a link, verified by opening the source. The short version:

**Established.** Seven-stage loop over **120,960 swept scenarios**. Conformal layer with **20/20
self-tests** — Mondrian, CQR, ACI/DtACI, joint coverage, worst-group. Physics validated against an
analytic plume at **0.00 %**, heat conserved at **0.00 %**, **67 Prairie Grass** field experiments,
and 6 instrumented condensers at **r = 0.798**. **1,336 explanations with 0 verification failures.**
A reasoning tape whose **30 templates contain not one literal digit**, checked at build time.
**Three sites live on their own geometry, weather, bound and tariff — and two more were refused on
aerial evidence.**

**Not established, and labelled as such everywhere it appears.**

- **The 90 % bound is not proven.** Coverage is **65.6 % on 3 test days**, which failed its
  pre-registration. A 90 % claim needs 10 measured day-pairs; **4 exist**, and the collector has
  returned zero tiles for three days running — see [`API-USAGE.md`](API-USAGE.md) §5.
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
cd INTAKE-ARBITER/src && python audit.py      # 61 checks, 70 published numbers re-read
cd INTAKE-ARBITER/src && python report.py     # the per-site PDF, verified by being reopened
```

All five make **zero API calls**.
