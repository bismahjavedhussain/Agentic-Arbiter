<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 02 - Architecture

How the shipped thing is put together, and which of its properties are **constraints** rather than
choices. Read this before changing code.

> **Line numbers here are indicative and will drift.** Function and element names are the stable
> handle; use those to locate things.

---

## 1. The hard constraint: one file, no build step

What ships is `AGENTIC-ARBITER/demo/index.html`. **One file.** No `package.json`, no
`node_modules`, no bundler, no framework, no `.tsx`. Any static host serves it as-is.

It has exactly four top-level blocks:

| Block | Roughly | What it is |
|---|---|---|
| `<style>` | 7 - 1404 | the whole stylesheet, including both themes |
| pre-paint `<script>` in `<head>` | 1416 - 1429 | resolves the theme before the first paint |
| body markup | 1438 - 2277 | every card, in stage order |
| the main inline `<script>` | 2279 - 7386 | the entire application |

**Neither script is `type="module"`.** That single fact explains a family of behaviours:

- top-level `function` declarations **do** become `window` properties;
- top-level `let`/`const` **do not** (see `05-TRAPS` 1.1);
- there is one shared global lexical scope, so ordering matters (`05-TRAPS` 1.2).

### Why you must not "modernise" this
Four separate things depend on it, and a rewrite breaks all four at once:

1. **Five cross-implementation verifiers locate functions by string search.** They do
   `indexOf('function ' + name + '(')` into the shipped HTML, pull out `decide()`, `plan()`,
   `reactive()` and friends, and score them against the Python agent over 500 cases. A bundler's
   output has no such functions to find.
2. **`audit.py` extracts the last inline `<script>`** with `rfind` and runs `node --check` on it. Two
   script blocks, or a build artefact, and the check is measuring the wrong thing.
3. **The byte-identical render gate.** `verify_site_panels.py` renders one site twice and requires
   identical output. This is why the page's animations use fixed `cubic-bezier` curves rather than
   spring physics: spring physics is time-dependent, so two renders differ.
4. **"Host it anywhere, works offline"** is a claim the README makes. It stops being true the moment
   there is an install step.

The only runtime network dependency is the map, and it degrades to a note (section 3).

---

## 2. The three stages

One variable and one writer. `let STAGE = 'pick'`, and `setStage(next)`:

```
setStage(next)  ->  document.body.dataset.stage = next
                    every [data-show] element: el.hidden = !dataset.show.includes(next)
                    syncRail(next)
                    window.scrollTo(...)
```

| Stage | What is on screen |
|---|---|
| `pick` | 2 cards: `#natmapcard` (the national map) and `#pickcard` (search + dropdown picker) |
| `configure` | the persistent sidebar (`#secnav`, `#sitename`, `#runagent`, `#filters`, `#backtopick`) plus one card holding `#readytiles` and `#runagent2` |
| `results` | 13 cards: `#tapecard`, `#livecard`, `#decisioncard`, `#headcard`, `#laddercard`, `#moneycard`, `#fieldcard`, `#sitecard`, `#plumecard`, `#dialcard`, `#whycard`, `#scorecard`, `#cfcard` |

**The two doors between stages both return or guard:**

- `chooseSite()` is `pick -> configure`. It **returns a boolean the caller must check**: on a failed
  `loadSite()` it writes an error into `#pickinfo` and returns `false` *without* changing stage.
  Ignoring the return renders one site's numbers under another site's name.
- `runAgent()` is `configure -> results`, guarded by `let streaming` so it cannot re-enter.

**The stage rail mirrors `STAGE`, it is never a second source of truth.** `syncRail()` sets
`data-state` to done/now/todo and disables forward steps; navigation is **backwards only**, guarded
twice (a `disabled` attribute and an index check).

**`data-needs` is a second, orthogonal gate.** `data-needs="plume"` removes `#dialcard` at a facility
with no tagged neighbour, where the panel would have nothing true to draw. There **used** to be a
`data-needs="live"` branch; it was removed because its only possible effect was to hide `#livecard`,
which standing rule C1 forbids.

---

## 3. The national map: three sources, six layers

`drawUnifiedMap()`. maplibre-gl 4.7.1 loaded from unpkg at runtime, with a 6 s timeout and a
`mapFallback()` path that replaces the map with a note. **This is the only panel that needs the
network**; everything else replays saved files.

### Sources
| Source | Kind | Why |
|---|---|---|
| `basemap` | raster, OpenStreetMap tiles | keyless. Pushed to grey with `raster-*` paint per theme |
| `unisites` | geojson, `cluster:true`, `clusterRadius:46`, `clusterMaxZoom:9` | the national view |
| `unisitesflat` | geojson, no clustering | the per-state view |

### 🔴 Why there are two copies of the same 637 features
**maplibre fixes clustering at source creation and provides no setter.** Below `clusterMaxZoom` a
clustered source returns *cluster* features, so a point layer filtered to `!has point_count` has
nothing to draw, and hiding the cluster layers reveals nothing. A single state fits at a zoom that
depends on the state (California about 5.4, Connecticut about 9), so tuning `clusterMaxZoom` to
straddle both views is a guess the next small state breaks.

`setMapView()` is the switch: `flat = !!(MAPFILTER.state || q.length >= 2)`, toggling layout
visibility so exactly one of the clustered trio and the flat pair is live. Cost: one extra copy of a
637-point FeatureCollection in memory. **`sync_context.py` asserts both sources still exist**, because
this is the design decision most likely to be undone by someone tidying up.

### Layers
`unisites-clusters`, `unisites-halo`, `unisites-circles` (clustered source) and
`unisites-flat-halo`, `unisites-flat` (flat source), plus `basemap`.

**There is no `symbol` layer, and that is not an omission.** See `05-TRAPS` 2.3.

### What gates the data layers
```js
if(!map.getLayer('basemap') || map.getSource('unisites')) return;
```
"Is the style **spec** parsed", plus idempotency. Deliberately **not** `map.isStyleLoaded()` and
**not** `map.on('load')`: both wait on raster tiles, and both have already caused the 637 facilities
to be silently absent. `05-TRAPS` 2.2.

### Filtering never rebuilds the GeoJSON
`mapFilterExpr()` returns a maplibre `['all', ...]` expression; `applyMapFilter(fit, dur)` pushes it
through four `setFilter` calls. The clustered point layers must keep their `['!',['has','point_count']]`
clause or they would draw the bubbles as points too. `filteredSites()` computes the same predicate in
plain JS for the count and the bounds, because both must be over **everything**, not over what is
rendered.

### The filter bar
`#mf_state` (full state names, sorted by name, defaulting to `CA`), `#mf_op` (operators by count then
alphabetically), `#mf_q` (a combobox), and a segmented `#mf_all` / `#mf_ready` radio pair, with the
count in `#mf_count`.

`#mf_q` renders `#mf_drop`, up to eight `.mfrow` rows. Choosing one clears the list, eases the map to
that facility, then opens the inspector.

### Two search surfaces, separate by design
`#pickcard` has the older one (`#sitesearch` -> `#searchresults`, rows `.srchrow[data-i]`). The filter
bar has the newer one (`#mf_q` -> `#mf_drop`, rows `.mfrow[data-key]`). **They are not duplication:**
`verify_map_hover.py` drives `#sitesearch`, reads `#searchresults` and `#searchnote`, selects
`.srchrow` and asserts exact strings. Reusing those ids would put two writers on one element.

---

## 4. The live-agent path

**Permanent. See `04-STANDING-RULES` C1 before touching anything here.**

Three relative endpoints, all without a leading slash so the page works under any path:

| Call | When |
|---|---|
| `GET api/health` | `probeLive()`, at boot, `{cache:'no-store'}` |
| `POST api/live/<SITE.key>` | `runLive()`, body `{hours, limit_c, paid}` |
| `GET api/live/job/<job_id>` | the poll loop |

**Availability is a two-tier decision.** Tier 1: `HEALTH = r.ok ? await r.json() : null`. A truthy
`HEALTH` means *a server is attached at all*. Tier 2 reads the flags inside it (`live_available`,
`paid_enabled`, `key_present`) to decide whether a run can actually be requested. The card is always
shown; what changes is what it says.

`#livego` is wired **once**, inside `buildControls()`, which only runs from `chooseSite()`. On the
pick stage the button exists but is not yet bound. Output ids: `#liverefusal` (kept separate from
`#livemsg` on purpose), `#livestream`, and the rest written by `drawLive()`.

### The server: `AGENTIC-ARBITER/src/serve_live.py`
Static files plus four API endpoints. **Three independent safety layers, not two:**

1. **Two keys to spend.** `paid = bool(want_paid and CONF["allow_paid"])`. The request must ask *and*
   the server must have been started with `--allow-paid`. Asking without the flag does not error, it
   downgrades to a dry run.
2. **A rolling daily budget.** `--max-live-calls` (default 24), counted from UTC midnight, so it
   clears itself the way the vendor's own daily quota does.
3. **Input clamped and paths sanitised.** `hours` clamped to 1..24; any `replay` fixture name is
   forced through `os.path.basename()`, with the comment that a browser must not be able to choose a
   path.

Flags: `--port`, `--host` (loopback by default, "this process can spend money; do not expose it"),
`--allow-paid`, `--max-live-calls`.

**The key never leaves the process.** `health()` calls `load_key()` for *existence only* and returns
just the boolean `key_present`. `/api/*` responses set `Cache-Control: no-store`.

---

## 5. Theme

**Dark is the base, not the override.** `:root{ color-scheme:dark; ... }` is the default palette;
`:root[data-theme="light"]{ color-scheme:light; ... }` overrides it. Getting this backwards once made
`verify_palette.py` measure the dark values against the light surfaces and report a clean pass for a
palette nothing had checked.

The **pre-paint IIFE in `<head>`** resolves the theme and stamps `data-theme` before the first paint.
It is there rather than in the main script because the main script runs after parse, which would paint
light first and repaint dark: a white flash on every load.

`let THEME` re-reads what the pre-paint script wrote. `applyTheme()` also has to repaint the canvases
and the map, which CSS cannot do for it.

Both blocks declare `color-scheme`, so native `<select>` popups and search-field clear buttons follow
the theme.

---

## 6. Per-site data loading

`loadSite(key)` carries a **generation guard**: `const gen = ++LOAD_GEN` before a single
`Promise.all` of seven artefacts, checked after. Without it, a reader who picks two sites quickly gets
one site's numbers under the other's name, because `loadSite()` leaves the previous site's globals
intact on a failed or slow fetch.

`drawAll()` is the results-stage repaint and a **registered set**: `audit.py` check 6d regexes
`draw[A-Za-z]\w*\(` out of `drawAll()`'s body and requires every function it names to read one of the
per-site globals. Adding a `draw*` call to `drawAll()` therefore obliges you to either read per-site
data or declare an exception.

`drawAll()` has **no try/catch**, so one throw kills every call after it. That has happened: a
`drawLimits()` that assigned `.innerHTML` on a null element threw as the last call, and
`runAgent()` never reached `await streamTape()`. The page looked perfect and the reasoning tape simply
never streamed.

---

## 7. `AGENTIC-ARBITER/src/` and the wider tree

| Path | What it is |
|---|---|
| `src/agent.py` | the agent: perceive, solve, bound, decide, act, explain, score |
| `src/audit.py` | the mechanical whole-tree audit. **25 numbered sections** from 24 check functions, labelled `1, 2, 2b..2f, 3, 4, 5, 5b, 6, 6a..6g, 7, 8, 9, 10`. Exits 1 on any FAIL. Writes only a temporary `demo/_audit_syntax_check.js` |
| `src/run_all.py` | the one-command proof. **28 steps, zero API calls** |
| `src/serve_live.py` | the live server (section 4) |
| `src/report.py`, `money.py`, `ticker.py`, `conformal.py`, `environment.py`, `plume_uncertainty.py`, `explain.py` | each carries a `selftest`, run as audit check 7 |
| `src/backtest.py`, `metros.py`, `live.py` | the backtest, the metro registry, the live path's own logic |
| `testing/` | the verifiers, the pre-registered `test_n*` tests, the `diag*` probes, `common.py` |
| `demo/*.json` | the shipped artefacts the page fetches |

**Four `src` modules read files outside `AGENTIC-ARBITER/` by path**, which is deliberate: `agent.py`
reads `testing/results/fixtures` and `testing/results/n26_manifest.json`, and **md5-compares its
shipped physics against `testing/solver.py` and `testing/warp_solver.py`** so the two cannot drift.
`audit.py` opens six documents above the project directory, two of which now live in `CONTEXT/`.

### `audit.py`'s published-number registry
Exactly **77 entries**. Its own size is a published figure: `PUBLISHED_COUNT[0] = len(reg)` is re-read
by check 10 and cross-checked against the README. The audit total (**2,215**) is **dynamic**, printed
as `len(PASSES) + len(WARNS) + len(FAILS)`, so it cannot be counted statically and is only knowable by
running it.

---

## 8. The data artefacts

The page fetches these at runtime from `AGENTIC-ARBITER/demo/`:

| File | Holds |
|---|---|
| `sites.json` | the manifest: **264 rows**, **250 with `offerable` true**. The only thing allowed to decide what the picker offers |
| `unified_sites.json` | the facility registry: **637 rows**, 43 states, **163 operators**, 46 in California |
| `trace.json` | one site's full agent run |
| `backtest.json` | the swept configurations and the money cells |
| `rolling.json`, `money.json`, `ticker.json`, `explanation.json` | the per-site panels' inputs |
| the field files | purchased FortyGuard data |

**`offerable` is the only source of truth for "ready to run".** The map once coloured its dots from a
stale baked `status` string and disagreed with its own caption: it said 246 runnable and painted 3
green. See `01-STATE` for why 250 and 246 are both correct.
