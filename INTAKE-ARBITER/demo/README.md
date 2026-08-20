# The demo — `python -m http.server 8000`, then open <http://localhost:8000>

```bash
cd INTAKE-ARBITER/demo && python -m http.server 8000
```

**Two modes, and the page tells you which one it is in.**

- **REPLAY** (this command) — every panel computed from saved FortyGuard responses. Reproducible,
  offline, and what any static host serves. That is not a limitation: N-55 measured a re-requested
  window as **17,862 of 17,862 tiles byte-for-byte identical**, so a replayed field is the same
  values, not an approximation of them.
- **LIVE** — `python ../src/serve_live.py --allow-paid` instead of `http.server`. Adds a card that
  asks FortyGuard what the **next hours** look like at this site's own tile and decides them. Needs a
  key in `.env`.

**Why LIVE needs a server:** the request needs an API key, and anything this page can read, every
visitor can read. `serve_live.py` holds the key in its own process and returns only numbers. It binds
to `127.0.0.1` and refuses to spend unless started with `--allow-paid`, because a page reload must
never cost credits.

🔴 **DO NOT open `index.html` by double-clicking it.** Browsers block `fetch()` from `file://`, so
the page loads and then shows nothing but a red error — it looks like a broken submission and it is
not. **It needs any HTTP server, and that is the only requirement.** No build step, no npm, no
dependencies, no server-side code: GitHub Pages or Netlify serve this folder exactly as it is.

**Zero API calls at view time.** Everything on screen replays saved FortyGuard responses, and the
page says so in its own header. That is a correctness property, not a convenience — N-55 established
that re-requesting the same window returns **17,862 of 17,862 tiles byte-for-byte identical, max |Δ|
= 0.00000000 °C**, so a replayed field is not an approximation of the live API, it is the same
values.

**What you are looking at:** pick one of three data centres → configure a plant from swept options
→ watch the agent work through its seven stages → read the proof panels underneath, including the
five-year worth, the downloadable PDF, and the panel where the bound **fails** its 90 % promise.

## Regenerate the data

```bash
cd ../src
python agent.py run        # -> trace.json, scenarios.json, field_*.json, rise_table_*.json
python backtest.py all     # -> backtest.json
```

## What each file is

| File | Size | What |
|---|---|---|
| `index.html` | 46 KB | the whole page. No dependencies, no build step, light + dark |
| `trace.json` | 112 KB | the agent's inputs and results: site, plant envelope, physics provenance, the four real FortyGuard day-pairs, the seven case days hour by hour, the 72-bearing table |
| `backtest.json` | 30 KB | five years, 43,763 hours: the N-56 audit ladder, the Mondrian coverage audit, the online adaptive-conformal run |
| `field_<date>_{forecast,outcome}.json` | 570 KB each | 17,862 real FortyGuard tiles. All tiles share one quad shape to 1e-8, so the file is one shared template plus a centroid and a temperature per tile — 570 KB instead of 7.4 MB |
| `scenarios.json` | 18 MB | the full 80,640-row plant-envelope sweep, columnar. **The page does not load this** — it is shipped so the sweep is auditable row by row |
| `rise_table_*.json` | 5 KB each | 576 GPU solves per bank placement, cached |

## The page re-runs the agent, it does not replay a lookup

`trace.json` ships the per-hour **inputs** — forecast error, group-conditional margins, plume rise,
wet-bulb, air quality, refusal flags — and the browser forms the bound and solves the schedule
itself, with the same dynamic program and the same three gates as `src/agent.py`. Moving any
control genuinely re-decides.

That means the scheduler exists twice, in Python and in JavaScript, which is exactly the
duplicate-code-path risk this project has been bitten by before. So it is tested:

```bash
python gen_dp_cases.py      # 500 random cases scored by the PYTHON agent
node verify_browser_agent.js
# -> plan mismatches: 0 / reactive mismatches: 0
```

`verify_browser_agent.js` **extracts the functions out of `index.html`** rather than copying them,
so it tests the code that actually ships.

## Verification status, stated honestly

| Checked | How |
|---|---|
| Every data path the page reads exists | 74 assertions against `trace.json` / `backtest.json` / the field files |
| JavaScript parses | `node --check` on the extracted script |
| Browser agent == Python agent | 500 random cases, 0 mismatches |
| Colour palette | the data-viz validator, all checks pass all-pairs in both modes (CVD ΔE 24.7 light / 26.8 dark; normal-vision 33.6 / 31.8) |
| Files serve over HTTP | 200 on `index.html`, `trace.json`, `backtest.json`, a field file |
| **Visual rendering** | ⚠️ **NOT verified.** No browser was available in the build environment, so label collisions, canvas geometry and overflow have not been eyeballed. **Open it and look before recording anything.** |

## What the page deliberately shows going wrong

A demo that only shows success is not evidence. On screen, by design:

- the conformal bound's **measured 65.6 % coverage against a 90 % promise**, and its FAILED
  pre-registered conditions;
- the hour where a single pooled quantile drops to **73 % coverage** while its average reads 90 %;
- the **refusal** screen — switch bank placement to `facing` and the agent declines to certify
  almost every hour, losing hours by construction, because a building sits on the plume path;
- what believing FortyGuard's level as delivered costs over five years (**about 595 h/year**);
- that recirculation awareness **costs hours and buys safety**, rather than the reverse.
