# The demo — `python -m http.server 8000`, then open <http://localhost:8000>

```bash
cd AGENTIC-ARBITER/demo && python -m http.server 8000
```

**Two modes, and the page tells you which one it is in.**

- **REPLAY** (this command) — every panel computed from saved FortyGuard responses. Reproducible,
  offline, and what any static host serves. That is not a limitation: N-55 measured a re-requested
  window as **17,862 of 17,862 tiles byte-for-byte identical**, so a replayed field is the same
  values, not an approximation of them. What LIVE adds is not accuracy, it is **recency**.
- **LIVE** — `python ../src/serve_live.py --allow-paid` instead of `http.server`. Adds a card that
  asks FortyGuard what the **next hours** look like at this site's own tile and decides them. Needs a
  key in the **repository root** `.env`: `testing/common.py:load_key()` reads `<repo root>/.env`, so a
  copy inside `AGENTIC-ARBITER/` is read by nothing and the key is silently never found.

**Why LIVE needs a server at all:** the request needs an API key, and anything this page can read,
every visitor can read. `serve_live.py` holds the key in its own process and returns only numbers. It
binds to `127.0.0.1`, caps live calls per process, and refuses to spend unless started with
`--allow-paid`, because a page reload must never cost credits.

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
| `index.html` | 417 KB | the whole page. No dependencies, no build step, light **and** dark, both measured against the WCAG floors. Most of that weight is the explanatory comments: every non-obvious rule in it records the measurement or the defect that produced it |
| `trace.json` | 202 KB | the agent's inputs and results: site, plant envelope, physics provenance, the four real FortyGuard day-pairs, the seven case days hour by hour, the 72-bearing table |
| `backtest.json` | 78 KB | five years, 43,763 hours: the N-56 audit ladder, the Mondrian coverage audit, the online adaptive-conformal run |
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
| Colour palette, series separation | the data-viz validator, all checks pass all-pairs in both modes (CVD ΔE 24.7 light / 26.8 dark; normal-vision 33.6 / 31.8) |
| Colour palette, **contrast** | `testing/verify_palette.py`, which is `run_all.py` step 24, parses the tokens out of `index.html` and measures **34 pairs against their WCAG 2.1 floors in both themes**: 4.5:1 for text, 3:1 for axes and legend swatches, plus the button ink on its own fill. It found a real failure on its first run (`--series-2` at 2.83:1 on the card), and the fix is checked rather than waived: the pair is left exactly as validated above, and the boundary that carries the 3:1 instead has to be *found* on `.legend i` and referenced by the canvas code, or the check fails as though there were no remedy at all. **It found a second one on 2026-08-28**, when it was extended to the *frosted* surfaces the Apple-style chrome introduced: `--glass` is translucent, so text on the bezel, the KPI cards, the slide-over drawer and the facility dropdown is really text on a **composite**, and the drawer opens from a map click, which puts it on glass over the **basemap** rather than over the page. Both basemap values are measured off real screenshots (#323232 dark, #cfcfcf light) rather than assumed, located by a marker the page paints at its own canvas origin so the two samples cover identical pixels. Measured that way, light-theme `--muted` came in at **4.44:1** on the drawer, and at only 4.53:1 on `--surface-2`; it is now `#6c6c75`, which clears **4.64:1 on the worst surface of the five**. |
| Files serve over HTTP | 200 on `index.html`, `trace.json`, `backtest.json`, a field file |
| **Visual rendering** | ✅ **Diffed in a real browser.** `testing/verify_site_panels.py` — `run_all.py` step 25 — drives Chrome through pick → configure → results for every offerable site, renders one site **twice** and requires byte-identical output, then diffs rendered text and canvas pixels across sites. **A missing browser exits non-zero rather than skipping**, because a skipped check reports PASS for a path it never ran. ⚠️ **A difference test cannot catch a WRONG picture** — one site's overlay on another's photograph produces pixels that differ, so it passes; `audit.py` check 6d separately bans any site's own coordinates, OSM ids and station from the page for that reason. **Neither instrument judges whether a label collides: open it and look.** |
| **The national map, live** | ✅ **Read out of a running MapLibre.** `testing/verify_state_filter.py`, which is `run_all.py` step 27, drives the filter bar in headless Chrome with software WebGL and makes **62 assertions** against the registry: that all 43 state options carry their full name and the registry's own count, that the page opens fitted to California, that each state's view selects exactly that state's facilities and paints them as individual circles rather than clusters, that the name box lists its matches and opens the one you choose, and that the four filters compose. **It found a real defect on its first pass:** the map's data layers were gated on `map.isStyleLoaded()`, which stays false while the OSM basemap has tiles in flight, so on any network that blocks those tiles none of the 637 facilities were added to the map at all. ⚠️ **Exits 3, not 1, when maplibre does not load from unpkg** — the page degrades to a note by design without it, and a missing CDN is not a failing page. |

## What the page deliberately shows going wrong

A demo that only shows success is not evidence. On screen, by design:

- the conformal bound's **measured 65.6 % coverage against a 90 % promise**, and its FAILED
  pre-registered conditions;
- the hour where a single pooled quantile drops to **73 % coverage** while its average reads 90 %;
- the **refusal** screen — switch bank placement to `facing` and the agent declines to certify
  almost every hour, losing hours by construction, because a building sits on the plume path;
- what believing FortyGuard's level as delivered costs over five years — **about 562 h/year**,
  from **+405.7** h/yr anchored to **−156.0** unanchored, while measured coverage *rises* to 0.9865;
- that our own plume shape is the **outlier, in the unsafe direction**: against 67 Project Prairie
  Grass experiments our √x spread measured an exponent of **0.805**, so at these distances the
  plume is too *wide* and **under-predicts rise by 5–25 %**.
