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

🔴 **IN THE REACT APP THERE ARE TWO KEYS, AND ONLY ONE OF THEM IS A DECISION.** `aa-theme-choice` is
written only by `chooseTheme()` and means the reader pressed the toggle; with it absent the STAGE picks
the default (dark on the landing page, light on configure and results). `aa-theme` is a CACHE of the
resolved palette, which the pre-paint script reads so a reader who has chosen never sees a flash of the
other one. Collapsing the two -- treating the presence of `aa-theme` as a choice -- is `05-TRAPS` 5b.26,
and it silently disabled the stage default for every returning reader.

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
| `portfolio.json` | the **250-site totals** the landing cards state. Written by `tools/portfolio_totals.py`, a `run_all.py` step |
| the field files | purchased FortyGuard data |

**`offerable` is the only source of truth for "ready to run".** The map once coloured its dots from a
stale baked `status` string and disagreed with its own caption: it said 246 runnable and painted 3
green. See `01-STATE` for why 250 and 246 are both correct.

### `portfolio.json`, and why a total is a build-time file

Added 2026-08-29 for the two summary cards beside the headline, which state PORTFOLIO figures rather
than the selected site's. Every field needs three artefacts per site; across 250 sites that is 750
fetches and hundreds of megabytes before the first card could paint, so the sum is computed once at
build time and read as one small file.

🔴 **THE ARITHMETIC MIRRORS `app/src/lib/headline.ts:headlineFigures` LINE FOR LINE, DELIBERATELY.** A
portfolio total and the site tile a reader clicks into must not be able to disagree about how a figure
is derived.

🔴 **AND IT IS A SUM, NOT A PROJECTION**, which the tool proves rather than asserts: it hashes every
artefact it opens and reports **247 distinct backtests and 250 distinct money files**, so no figure is
one site's result multiplied by a count.

⚠ **TWO FIELDS THAT LOOK INTERCHANGEABLE AND ARE NOT.** `weather_site_hours` (**10,820,547**) is the sum
over 250 sites of the hours each was scored against; `weather_hours_distinct` (**4,232,006**) counts
each of the **98** airport stations once. The 250 sites share those 98 stations, so only the second is
a count of hours of weather. The card states the second.

⚠ **AND THREE FIELDS THAT EXIST SO THE CARD CAN QUALIFY ITSELF:** `sites_gaining` / `sites_losing`
(**238** / **12** -- the money floor is negative because of those 12) and `sites_own_state_prices` /
`sites_reference_prices` (**61** / **189** -- EIA publishes no row for most states, so most sites are
priced on the Virginia and Illinois reference rows). A total that hides its own composition is the
thing `04-STANDING-RULES` calls an unverified claim.

## 8. The cinematic intro layer: `AGENTIC-ARBITER/app/src/intro/`

Added 2026-08-29. The landing stage's opening sequence. **App-side only** -- nothing here is lifted
from `demo/index.html` and nothing here is byte-asserted, so it is the one part of the product that
can be changed without re-lifting.

### The single most important architectural fact

**"Landing page only" is a STAGE, not a route.** This product is one document: `body[data-stage]`
moves through `pick` -> `configure` -> `results` and the engine's `setStage()` is its single owner.
There is no navigation event to hang cleanup off, so **the stage attribute IS the navigation**, read
through `lib/stage.ts`'s `useStage()`, a read-only MutationObserver. When it leaves `pick`,
`IntroLayer` unmounts its children, tears down audio, kills every timeline and every ScrollTrigger.

### What each file owns

| File | Owns |
|---|---|
| `flags.ts` | The two kill switches, resolved once. URL parameter beats localStorage beats a constant. Also `isNarrow()` (768px, matching `hooks/use-mobile.ts`) and `hasSeenSplash` |
| `audio.ts` | Two `<audio>` elements plus a three-element chime pool, preload, the duck, mute, and `teardown()` which clears `src` and reloads so the decoder is actually released |
| `IntroGate.tsx` | The splash: globe, title, staggered widgets, ShinyButton, FortyGuard mark. Focus trap, focus restore, scroll lock |
| `IntroLayer.tsx` | **The only thing `App.tsx` knows about.** Reads the flags once, exists only on the landing stage, and is where every teardown lives |
| `timeline.ts` | One GSAP entrance timeline, the ambient pulse and float, and the scroll handoff. Two beat maps: silent (1,520 ms) and audio-synced (4,110 ms, derived from the measured voiceover) |
| `Pipeline.tsx` | The five-stage agent loop as SVG, and the geometry the timeline needs (`NODE_XS`, `NODE_ROW_Y`, `LOOP_PATH`) |
| `HeatGlobe.tsx` | **Three.js** since 2026-08-29, replacing cobe entirely. ⚠ **The framing is three ratios of the MEASURED container and the camera distance is derived from them** (`FRAME`: diameter 0.90 of H, centre at 0.72 of W and 0.66 of H), recomputed from the ResizeObserver so it holds at any window size. It moves the CAMERA and never `mesh.scale`, because the atmosphere is a separate shell at a fixed radius and scaling the earth detaches the glow. `applyLayout()` publishes what it solved as `data-aa-sphere`, so a probe measures the applied values rather than re-deriving them, and the particle lattice is offset in the adjacent statement so it cannot reframe separately (see `04-STANDING-RULES` C5). Three spheres: the Earth at radius 1 with day, normal and specular maps; a cloud shell at 1.01 read as an `alphaMap`; an atmosphere at 1.15 rendered `BackSide` through a custom fresnel shader, additively blended. One directional light plus a low blue ambient. Own rAF loop with a real clock, drag to rotate, and a teardown that disposes every geometry, material and texture and calls `forceContextLoss()` |
| `funnel.ts` | the converging measurement LATTICE, rebuilt 2026-08-29 from a random scatter that read as confetti. One `THREE.Points`, **760 dots on an exact 38 x 20 (u, v) grid**, additive, uniform size. A fan in the SCREEN PLANE with a quadratic bow, plus a radial clamp at 1.045 so the sheet hugs the planet instead of sinking inside it. **Every position is computed in the vertex shader**: the grid is written once and only a `uTime` uniform crosses per frame. No noise term in the shape at all, and the one hash is a flicker phase that displaces nothing |
| `demo/textures/` | the four Earth maps the globe fetches through `ART`, 1.19 MB, CC BY 4.0. Written by `tools/make_earth_textures.py`, attribution in `CREDITS.txt` beside them. ⚠ `earth_normal.png` is lossless on purpose: its signal is 1.36 of 255 wide and is amplified in the shader |
| `ThermalField.tsx` | The background. Pure CSS keyframes, no JS in the motion at all |
| `launch.ts` | **The timed cinematic behind "Initialize Arbiter"**, added 2026-08-29. One GSAP timeline owns the visuals; audio is fired at labels and listened to nowhere; a wall-clock watchdog owns completion so a frozen GSAP clock cannot strand the reader. Carries the undocumented Esc / Space / click escape hatch, bound before the timeline is built |
| `globeDolly.ts` | The one channel between that timeline and the camera. A number from 0 to 1, never a camera: the framing is re-solved on resize, so a timeline writing `camera.position.z` would be overwritten mid-sequence |
| `intro.css` | Loaded last, after `lastmile.css`. Section 8 pins the hero to the DARK palette in both themes, for the reason in `04-STANDING-RULES` C5 |

**AND ONE FILE THAT DELIBERATELY LEFT THIS FOLDER.** `components/StageRows.tsx` and its
`stagerows.css` hold the five agent stages that used to sit in the splash between the subhead and the
call to action. They were moved below the map on 2026-08-29 and moved OUT of `intro/` in the same
change, because everything in `intro/` is motion and `?motion=off` unmounts all of it: those rows are
the only plain-language account of the loop on the landing page, so they are content and must survive
every kill switch. `App.tsx` renders them inside `[data-show="pick"]`, so `setStage()` still owns
whether they are visible. Their stylesheet is therefore **not** scoped to `body[data-aa-intro]`, and it
follows the reader's theme rather than being pinned dark, because nothing in it is emissive.

### Three stacking decisions that are not obvious

* **The heat field is portalled to `<body>`, not rendered inside `#app`.** `z-index: -1` is useless
  because `body` has an opaque background (`index.css:270`) and a negative-index child paints behind
  it. A `z-index: 0` positioned element paints ABOVE static block content, so inside `#app` it would
  cover the prose. As a direct child of body at `z-index: 0` with `#app` raised to `1`, the order is
  right. That one declaration on `#app` is the only thing the feature changes about an existing
  element, and it is scoped to `body[data-aa-intro]`.
* **The agent-loop diagram is portalled into `<div id="aa-ringslot" />`**, which `App.tsx` renders
  under the masthead. Same pattern as the existing `#aa-railslot` that `EngineStage` fills. The slot
  is read in a `useEffect`, not during render, because on the first pass React has not put App's own
  output in the document yet.
* **The splash locks `documentElement.overflow`, not `body`.** Only the ROOT element's overflow
  propagates to the viewport; on `<body>` alone it changed nothing and the page still scrolled behind
  the overlay.

### Five `data-aa-hero` attributes, and why they exist

`Masthead.tsx` carries four and `SelectedBar.tsx` one. They are attributes only -- no class, element
or nesting level changed. Those elements otherwise carry only Tailwind utilities, and matching on
those would couple `timeline.ts` to someone else's spacing decisions.
