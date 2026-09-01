# AGENTIC-ARBITER

**An agent that decides, hour by hour, whether a data centre can switch its mechanical chillers off
and cool with outside air, and that grades its own accuracy against reality before it says yes.**

FortyGuard Hackathon '26 · Track 6 (Agentic AI) · Tracks 2 and 3 as secondaries

**Live:** [agentic-arbiter.onrender.com](https://agentic-arbiter.onrender.com) · the React app is at
[`/app/`](https://agentic-arbiter.onrender.com/app/)

---

## The problem

A chiller plant needs hours of notice to change mode. Operators have good on-site sensors, but a
sensor reports the present, and without a forecast nobody can say what the air will do next. So the
safe call is to keep the compressors running, and the plant over-cools through hours that outside
air could have handled for nothing.

**FortyGuard** closes that gap with heat intelligence **2 m above the ground**, the height a
ground-mounted condenser actually breathes. This agent turns that forecast into an hour-by-hour
switching schedule, with a safety margin measured from its own past errors rather than assumed.

At the shipped Ashburn site, over **913 held-out days** it cuts mechanical cooling runtime
**10.7 %** and recovers **+406 chiller-hours a year**. Remove FortyGuard's field and **88.3 %** of
that gain goes with it.

---

## Try it

```bash
# 1. Prove it. 45 steps, ZERO API calls, exits non-zero on any failure.
cd AGENTIC-ARBITER/src && python run_all.py

# 2. See it. Replay mode, no key needed, works offline.
cd AGENTIC-ARBITER/demo && python -m http.server 8000     # then open http://localhost:8000
```

Replay is not a weaker claim than a live call. Every panel is computed from saved FortyGuard
responses, and re-requesting a window returned **17,862 of 17,862 tiles byte for byte identical**.

To decide the *next* hours from a live forecast, put a FortyGuard key in the **repository root**
`.env` and serve with the live agent attached:

```bash
python AGENTIC-ARBITER/src/serve_live.py --allow-paid
```

`testing/common.py:load_key()` reads the `FORTYGUARD_API_KEY` environment variable first and the
repository-root `.env` second. A copy of `.env` inside `AGENTIC-ARBITER/` is read by nothing.

---

## What it does

**Five stages, hour by hour.** Perceive the 2 m field, bound it, decide under a switch budget, act,
then score itself and recalibrate.

**The bound is the product.** Every released hour carries a split conformal interval sized from the
agent's own past residuals, group-conditional by hour of day (Mondrian) and adaptive over time
(ACI). The distribution-free conditional impossibility result is stated on the page rather than
papered over. Where the solver cannot answer, the agent **refuses the hour** instead of guessing.

**It solves the exhaust plume on real geometry.** A hall can breathe its neighbour's exhaust, and a
regional forecast cannot see that. At Ashburn two Amazon halls sit **60.3 m apart**, and the agent
solves **576 fields per placement** (72 wind bearings × 8 speeds) on the building's own OpenStreetMap
footprint using **NVIDIA Warp**, in about five seconds on the GPU.

**Scale.** 238 data centre campuses across 36 US states, mapped from OpenStreetMap and scored
against **4,188,290 hours** of recorded weather from **97 ASOS airport stations**. Modelled at
**$42.4M to $84.8M a year** across the portfolio, and **+92,988 free-cooling hours**.

**FortyGuard endpoints used:** `/v1/heatmap` for the 2 m dry-bulb field, `/v1/env_params` for the
wet-bulb and a PM2.5 index that drive the humidity and contamination gates, `/v1/status` to poll the
asynchronous jobs.

---

## What is honest about this, and what is not

| | |
|---|---|
| **The 90 % bound does not hold on the live feed yet** | Measured **65.6 %**. It has 4 calibration day-pairs and needs about 10. At 4 the arithmetic ceiling is **80 %**, so part of that gap was never reachable. More days is the whole remedy, and they come from FortyGuard data alone. Over five years of held-out history the same machinery reaches **90.4 %**. |
| **The hours claim wants a level anchor** | One local reading. Unanchored, five years of data say the agent **loses**. The safety guarantee needs no customer hardware; the hours do. |
| **Twelve sites are withheld** | Measured and not offered. There the agent is the more conservative of the two, refusing hours the incumbent takes on a sensor reading with no forecast behind it, so they are not offered without site-specific engineering. |
| **The money is modelled, and labelled so** | A sweep of published tariffs and chiller efficiencies, compressor-only, which makes it an upper bound on that term rather than a projection. Every price has its document and page in [`money-sources.md`](money-sources.md). |
| **The CPU comparison is extrapolated** | The GPU time is measured. The "about six minutes on a processor" figure is scaled from a measured 100-solve CPU run, not timed at 576. |

**No unverified numbers.** Every published figure is re-read from the artefact that produced it by
`AGENTIC-ARBITER/src/audit.py`. If a number is in the interface, a check opens the file it came from.

---

## Deploying it

One container serves the artefacts, the app and the live API from the same origin, because the page
calls the agent with a relative URL.

```bash
docker build -t agentic-arbiter . && docker run -p 8000:8000 \
  -e FORTYGUARD_API_KEY=... -e MAX_LIVE_CALLS=48 agentic-arbiter
```

On Render, [`render.yaml`](render.yaml) configures everything except the key, which is entered once
in the dashboard and stored encrypted. `MAX_LIVE_CALLS` is the daily ceiling on paid runs and is the
only one: **`serve_live.py` has no authentication**, deliberately, so a judge needs no token.

---

## Where things are

| Path | What is there |
|---|---|
| [`AGENTIC-ARBITER/src/`](AGENTIC-ARBITER/src/) | The agent. 24 modules, including the Warp plume solver and `audit.py` |
| [`AGENTIC-ARBITER/demo/`](AGENTIC-ARBITER/demo/) | What ships: one HTML file with no build step, its JSON artefacts, and the built React app at `demo/app/` |
| [`AGENTIC-ARBITER/app/`](AGENTIC-ARBITER/app/) | The React source for that app |
| [`testing/`](testing/) | Every experiment, including the ones that failed |
| [`money-sources.md`](money-sources.md) | Every price and efficiency figure, with its document and page |

---

## Verify it yourself, for free

```bash
cd AGENTIC-ARBITER/src && python run_all.py       # 45 steps, the whole pipeline
cd AGENTIC-ARBITER/src && python audit.py         # every published figure, re-read from its artefact
python testing/verify_site_panels.py              # renders every site in real Chrome and diffs them
python testing/scan_secrets.py                    # the full tree and the full git history, for keys
```

All of these make **zero API calls**.
