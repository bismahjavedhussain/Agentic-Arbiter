<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 01 - State

What is true **right now**. The figures below are generated from the shipped artefacts; the prose is
maintained by hand. Newest change first, always.

---

## 0. Resume here

**This is the first thing to read after a restart or a compaction.** Maintained by hand; it is the
only section describing work IN FLIGHT rather than work finished.

### What we are in the middle of
The React app is now **the whole product, not just the pick screen**. As of 2026-08-28 it carries
pick, configure and results, including the live agent. Remaining work is judgement, not plumbing:
the light theme is still not visually verified, and `verify_palette.py` does not yet parse
`app/src/index.css`.

### THE CORRECTION THAT RESHAPED THIS WORK, 2026-08-28
The user's words: *"I want to change the Ui but I dont want to change the buttons from the .html file
that existed before. The front page only has the configure button and then the run agent button and
run agent live button all appears afterwards with graphs and proper reports like it was doing in the
html file we made before."*

They were right and I had the scope wrong. The React rebuild was a **pick screen only**, and its
"Configure this plant" button linked out to `demo/index.html`. A new UI that hands the reader back to
the old UI at the first real action has not replaced anything. Two of the page's three stages, 18
cards, the reasoning tape and the live agent existed nowhere in it.

They then asked the exactly right follow-up question before agreeing to the approach: does lifting
the results stage weaken the LIVE agent? The answer, measured rather than asserted: no, and lifting
protects it best. A live run writes into nine elements, all inside `#livecard`, and it does produce
new charts -- `drawLive` calls `drawConformalLine` and `drawConformalSummary`, so a real conformal
bound is computed on live weather. It deliberately does **not** overwrite the replay panels, because
those are measured over 43,763 held-out hours and one live hour replacing them would make the
90 %-promise coverage test meaningless. And the live agent's REASONING is server-side in
`serve_live.py`, so no front-end move can touch it.

### The plan
| Step | State |
|---|---|
| 1. Attach the 21st.dev MCP server | **done** |
| 2. Extract `core/`, repoint the verifiers | **done and green** |
| 3. Extract the shared chart primitives | **done and green** |
| 4. React prototype of the pick screen, per the UI brief | **done and green** |
| 5. Lift the engine so the React app carries configure + results + live | **done and green** |
| 6. Verify the palette against `app/src/index.css`; check the light theme by eye | **next** |

### HOW THE TWO HALVES MEET, and why it is shaped this way
`AGENTIC-ARBITER/results/engine.mjs` is **100 functions, 208 KB, lifted byte for byte** out of
`demo/index.html`. React renders the page's own configure and results **markup** verbatim
(`app/src/generated/engine-markup.ts`, 39 KB) and its **stylesheet** verbatim
(`app/src/generated/engine.css`, 96 KB). The engine finds its targets by element id and owns
everything inside them; React owns the pick screen and the shell.

Measured, not assumed: with the pick stage fenced off, **the engine calls nothing on React's side of
the seam.** Zero crossings.

**Why the page keeps its inline copy too.** Deleting it would force `index.html` to load a module,
and browsers block module loading over `file://` -- a judge who double-clicks the page would get a
blank screen. That property is the most-tested thing about this product. So there are two copies, and
`testing/verify_results_matches_page.py` refuses to let them drift.

**Why the code is not imported from `core/`.** Those 22 functions were deliberately CHANGED when they
were extracted (`decide(k)` became `decide(k, trace)` so the node verifiers stop stubbing `$()`).
Importing them would break every call site. The duplication is intentional and asserted.

### THE THREE DEFECTS THE STATIC CHECKS COULD NOT SEE
Worth recording, because all three passed byte-identity and id-presence checks and were caught only
by driving the browser. This is why `testing/verify_app_flow.py` exists.

1. **`const BOOTED = boot();`** The generator dependency-analysed the *functions* and took the 55
   top-level *declarations* wholesale. One of them calls the page's entire bootstrap. The lifted
   module threw `ReferenceError: boot is not defined` the instant React imported it. The fix moved the
   assertion **onto the emitted output** rather than the inputs: checking the inputs is checking my own
   reasoning about them.
2. **`document.querySelector('.viz-root')`.** `cssv()` reads the design tokens through a **class**
   selector, invisible to an id-based check. Missing, it threw
   `getComputedStyle: parameter 1 is not of type 'Element'`, the configure transition rejected, and the
   screen just sat there.
3. **React re-applying its own `dangerouslySetInnerHTML`.** The transition ran, `buildControls()`
   filled `#filters`, React re-rendered on a state change, re-applied the pristine markup, and the
   controls were gone. Nothing threw; the stage said `configure` and the panel was empty. The markup is
   now injected once in a layout effect, so React has no children there to diff, ever.

Plus a fourth that was mine alone: `#c_site` is in `#pickcard`, on React's side, and the markup
verifier reported it present because the string `id="c_site"` appears **inside an HTML comment** about
a historical duplicate id. Four times in one session a name in prose was mistaken for a definition;
every scan in the verifiers now masks comments first.

### THE UNCOMMITTED RISK IS CLOSED, at commit fcf7b59
Everything is committed and `git status` is clean: **0 paths outstanding**. 7365 files changed, 15479 insertions(+), 3330 deletions(-)

Checked BEFORE committing rather than after:
- `.env` is gitignored, untracked, and **absent from the commit**. `testing/scan_secrets.py` reads the
  real key off disk and searches for it across every tracked file AND every blob in history:
  **clean, 0 hits in 5,975 tracked files and 7,393 history blobs, 1,760 MB read.**
- `node_modules` absent from the commit.
- `diff.renameLimit` raised to 8,000 FIRST, so the folder rename is recorded as **3,600 renames**
  rather than as thousands of unrelated deletes and adds. Git's default limit had silently skipped
  detection, and a history that cannot see a rename cannot follow a file through one.
- Git normalised line endings on three new `testing/` files on the way in. All three re-parsed and the
  suite re-ran afterwards: audit 2,215/0, drift gate 64/0, palette 34/0, context pack clean.

⚠ **It is ONE commit for a very large amount of work, and that is a fault rather than a style.** It
should have been several. From here on, commit incrementally.

⚠ **There is no remote.** `git remote -v` is empty, so this snapshot exists only on this machine. A
disk failure still loses everything. Pushing somewhere is a separate decision and has not been made.

### 🔴 THE NEXT ACTION
The pick screen prototype EXISTS and every behaviour in the brief is verified (below). What is left,
in order:

1. **Spend the 21st.dev retrievals deliberately.** Free tier: **2 component-code retrievals per day**,
   search and browsing unmetered. Nothing retrieved yet, 2 of 2 remaining.
   **Recommended first spend: a stat/KPI card design** (candidates found by search: `Stats Card`
   id 7841, `Progress Metric Card` id 15024). Reasons: the five cards are the largest flat area and
   the first thing after the headline; it is purely presentational, so the audited figures in
   `headline.ts` are untouched; and it **restores something this React rebuild lost** -- the
   single-file page had micro-sparklines built from three REAL series (the notice-hour ladder in
   `BT.sensitivity.rows`, the 16 money cells, and the margin trajectory) and the React KPI cards
   have none. `charts/primitives.mjs` already exports `sparkSVG`, so what is wanted from 21st is the
   card's visual craft, not a charting library.
   ⚠ **Drop any "+12% vs last month" affordance such a card ships with.** Four of the five figures
   are LEVELS, not trends; there is no previous period. Rendering one would be a false visual claim.
   **Second spend: hold it.** Retrievals reset daily, and choosing before seeing the first one
   integrated is guessing. If it must be pre-committed, the next weakest thing is the page FRAME:
   it still reads as a document rather than an application.
2. **Extend `verify_palette.py` to the app's tokens.** `app/src/index.css` inherits every colour value
   from `demo/index.html` verbatim, because each one is measured; but the validator parses the page,
   not the app, so right now they are inherited rather than independently verified.
3. **Rebuild the remaining panels as components**, one at a time, only when the pick screen is signed
   off. The other 30 stay in the HTML page until then.
4. **Decide when the app supersedes the page.** At that point: the page's inline agent copy goes, the
   drift gate (step 29) becomes unnecessary, and `dist/` gets committed once, deliberately.

### 🔴 THE GAP THE USER CAUGHT, and it was a real one
**The React pick screen let a reader select a data centre and then offered nothing.** No configure
button, no run, no statement that those stages exist. The user asked "where's the button of
configuring the plant selected by the user?" and was right to read that as a missing feature.

**What was NOT true:** nothing had been removed from the shipped page. Verified: `demo/index.html`
still has 3 stage-rail steps, `#pickgo`, `#runagent`, `#runagent2`, `#backtopick`, `#livecard`,
`#livego`, `#filters`, `#readytiles`, 15 results-stage cards and 3 configure blocks. The React app is
a one-screen prototype, which is what step 4 scoped.

**Why that is still not a defence.** A screen that ends in a dead end is not a smaller product, it is
a broken one. "The brief only specified the pick screen" does not license shipping a cul-de-sac.

**The fix: `app/src/components/SelectedBar.tsx`.** Selecting a facility now reveals a bar with its
name, category, operators, weather station, a Deselect, and the primary action:
- ready to run → **"Configure this plant →"**, linking to `../index.html?site=<metro_key>`
- a candidate → the honest reason instead of a button that would quietly land elsewhere

It is a HANDOFF, not a reimplementation. Configure, results, the reasoning tape, all 13 panels and the
live-agent card exist and work in `demo/index.html` today; none of it has been rebuilt in React. A
button that pretended otherwise would be worse than the dead end.
`?site=` takes a METRO key, which the page validates against its own picker options, so the CTA is
only offered where the metro is offerable.

### 🔴 THE URL LAYOUT, which that one link forced into the open
The app fetched artefacts relatively, which is correct only when the app's directory IS the artefacts'
directory. That is true in vite dev and nowhere else, and mounting the app at `/app/` exposed it:
`/app/sites.json` was a 404, and the production layout `demo/app/` would have failed the same way.

**One constant fixes all three: `ART = '../'` in `app/src/lib/artefacts.ts`.** Browsers CLAMP `../` at
the root rather than erroring, so:

| Layout | app at | `../sites.json` resolves to |
|---|---|---|
| `vite dev` | `/` | `/sites.json`, served by the config's plugin |
| `testing/serve_app.py` | `/app/` | `/sites.json`, i.e. `demo/` |
| production | `demo/app/index.html` | `demo/sites.json` |

And `../index.html` reaches the single-file page in all three, which is what makes the CTA correct
everywhere. **When the app eventually replaces `demo/index.html`, `ART` becomes `''` and nothing else
changes.** The fonts in `index.css` and the preloads in `index.html` use the same `../` for the same
reason, and `testing/serve_app.py` now mounts the app at `/app/` to mirror production.

### Step 4, as built
`AGENTIC-ARBITER/app/` -- Vite 7, React 19, TypeScript, Tailwind 4, maplibre-gl 6. Nine source files.
`npm install` clean, 0 vulnerabilities. Typecheck clean. Build clean.

**It consumes rather than re-derives.** The same `demo/*.json` at the same relative paths, so
`vite.config.ts` SERVES `../demo` in development rather than copying it: demo/ is 695 MB across 3,304
files, and `publicDir` would duplicate all of it into `dist/`. A built bundle is meant to be dropped
INTO demo/, where the same fetches resolve, which is what keeps "no install step" true for the
artefact even though the source now has a build.

**The five KPI figures are the shipped figures.** Derived in `app/src/lib/headline.ts` exactly as
audit.py's front-door registry derives them, and **reproduced in Python first** and checked against
the published strings before a line of TypeScript was written. All twelve matched, intermediates
included. ⚠ That is a second place the derivations live; it is accepted only because audit check 10
re-derives all of them independently and fails on a mismatch.

**Every behaviour the brief specifies, verified through the app's own `?probe=1` surface:**

| Brief | Measured |
|---|---|
| Inter, self-hosted, real hierarchy | ~1.32 type scale, hero figure ~4x body; one family by weight, not two by family |
| Order: headline, search, cards, map | exactly that, in the DOM |
| Search bar and map visible together | the bar is **sticky**; see the note below on the contradiction |
| Three interconnected combo boxes | choosing California drops the operator list to those operating there, with California counts |
| Vibrant coloured OSM | no `raster-*` exposure paint at all |
| 246 ready-to-run in green | `paintedHalo: 246` |
| Full US on arrival, no zoom | `zoom: 3.5`, camera untouched on mount |
| Ashburn popup on arrival | "Ashburn, Virginia / Amazon Web Services IAD116 → Amazon Web Services IAD117 / facades 60.3 m apart" |
| State selection fits that state | `state=CA` → 46 dots, 10 halos, zoom 5.48 |
| Operator highlight, contrasting | paint expression targets the 57 AWS facilities in `--series-2` terracotta; all 637 stay visible |
| Facility selection zooms and names it | 1 dot, zoom 12, "The data centre you selected: QTS San Antonio II, Texas" |
| **All 637 facilities on the map** | `paintedDots: 637`, `srcGiven: 637`, registry holds 637. **A filtered view showing 1 dot is correct**, and the bar says "1 of 637 shown" |
| A way to proceed from a chosen site | `SelectedBar` → `../index.html?site=<metro>`, verified to land on the page carrying `#pickgo` and `#runagent` |

**THE ONE CONTRADICTION IN THE BRIEF, and how it was resolved.** It asks for the order
headline → search → cards → map AND for the search bar and map to be visible at once. With the cards
between them, both cannot hold at any laptop height. The bar is sticky: the DOM order is exactly as
asked, and scrolling to the map leaves the controls on screen and live.

**"LIVE agent is also attached" is rendered only when it is true.** Hard-coding it would be a false
claim on the first line a judge reads. When no agent is attached the line states REPLAY and says how
to attach one.

### 🔴 FIVE DEFECTS IN STEP 4, and the order matters more than the list
The map showed a perfect, interactive, colourful basemap with **none of the 637 facilities on it**,
and raised no error. Five things were wrong, found in this order:

1. **`onPick` was an inline arrow in the map effect's dependency array**, so the map was destroyed and
   rebuilt on every render, twice over under StrictMode. Real bug, fixed with a ref. **Not the cause.**
2. **My `on('error')` handler discarded everything.** Registering a handler REPLACES maplibre's
   default, which logs, so adding it made the map quieter than having none. An error handler that
   discards is worse than no error handler.
3. **My probe read `_data.features`.** maplibre 6 keeps inline data at `_data.geojson`, per its own
   type declaration. It reported `-1`, which looked like "the source has no data" and meant "my
   instrument looked in the wrong place". Corrected, it read **637**.
4. **THE ACTUAL CAUSE: maplibre 6 ships its worker as a separate module** and requires
   `setWorkerUrl`. Raster tiles decode on the main thread, so the basemap drew perfectly; only
   GeoJSON needs the worker, so the facilities never tiled and `loaded()` stayed false for ever, with
   no error. A correct, colourful, interactive map with nothing on it is exactly what a missing
   worker looks like.
5. **And `?url` was the wrong import for it.** It copies the file verbatim without following its
   imports, and maplibre's worker begins `import{B as e,...}` from a shared chunk that is then absent
   from the bundle. `?worker&url` bundles it: 18 KB became 476 KB, and the dots appeared.

Plus two smaller ones: two effects both owned the popup, so the second removed what the first had just
created (`popups: 0` every time); and `committed.source` / `.receptor` were guesses -- the real names
are `source_name` / `receptor_name`, and an optional chain on a misspelt key renders nothing at all
rather than failing.

⚠ **A heredoc mangled a patch into a regex containing literal BACKSPACE characters**, so `?probe=1`
compiled, ran, and never matched. Sixth occurrence of `05-TRAPS.md` 5.4 this session. Use the Write
tool for anything containing a backslash.

### How to run and verify the app
```
cd AGENTIC-ARBITER/app && npm install && npm run dev     # http://127.0.0.1:5173
cd AGENTIC-ARBITER/app && npm run build
python testing/serve_app.py 8123 --hold 16               # serves app/dist + demo together
```
`?probe=1` renders a hidden `#AAPROBE` div carrying the live map's state: layers, source counts,
distinct facilities actually PAINTED, the filter, the paint expression, the camera, and any errors.
`?state=CA&operator=...&facility=KEY` seeds the filters, which is both a shareable deep link and the
only way a headless check can drive the three filter behaviours.

⚠ **`--hold` is not optional for a screenshot.** A headless capture fires at the load event, which is
always too early for this map, and `--virtual-time-budget` makes it worse: a GeoJSON source tiles in a
worker on the real clock while virtual time races the page's timers. Measured: source and layers
present, `querySourceFeatures` 0, `isStyleLoaded()` false, nothing broken.

⚠ **Not yet verified:** the light theme visually (the palette is inherited and measured, but the app's
own tokens are not parsed by `verify_palette.py`), and the app has no equivalent of the byte-identical
render gate.

### Step 2, as built
`AGENTIC-ARBITER/core/` is six ES modules: `format`, `config`, `conformal`, `agent`, `explain`,
`ticker`. Generated by `scratchpad/mkcore.py`, which lifts each function out of `demo/index.html` with
the same brace-matcher the verifiers use and prints every substitution it makes.

**All five cross-implementation verifiers now `import` from `core/` instead of string-scraping the
page, and none of them fakes a browser any more.** Corpora unchanged: 500 DP cases, 789 conformal
assertions, 20,160 configurations, 1,336 explanations, 2,037 event sentences, zero mismatches.

The design decision that made it possible: **`cfg()` stays in the page.** It was the only thing
reaching into the DOM, and it is a 10-line adapter over eleven `#c_*` controls. Its coercions moved to
`core/config.mjs` as `cfgFromStrings(get)`, where `get` is an injected callback. The page passes
`id => $(id).value`; a test passes `id => String(row[...])`. Identical coercions, one definition. That
matters because a `<select>` always yields a string, so `offday` is `"0"` and not `0`.

### Step 3, and why it was reframed
The plan said "extract the canvas draws to `charts/` the same way". **That was the wrong shape of
job.** There are 31 `draw*` functions, 152,107 characters, about 3,621 lines, and every one writes
`innerHTML`. They are not chart functions; they are panel renderers that emit tables, tiles and prose
AND paint canvas. Extracting them as pure draw functions means splitting all 31 into
data → view-model → DOM, and the React migration rewrites the DOM half of each one anyway. That work
would be discarded on arrival.

What moved instead is the **primitive layer** all 31 share and every React chart component needs:
`charts/primitives.mjs`, 105 lines, seven functions byte-identical to the page plus `DPR_CAP` and
`EDGE`. The 31 panels get **rebuilt as components**, one at a time, starting with the ones the pick
screen needs (the KPI plate and the map). The brief says not to modify the reports, graphs or data
cards, so the other panels stay in the HTML page for now.

**And it closed a drift risk the page documents but could not guard.** `index.html` builds its canvas
font strings from `CFACE`/`CMONO`/`CBODY` literals duplicating the CSS tokens, and its own comment
concedes: *"Keep the two in step by hand; there is no mechanical guard available."* There is one; it
just was not reachable there, because `getCssVar` is defined 3,700 lines below `CF`. In a module the
order is ours, so `CF` is now an object of **getters** that resolve from the tokens at first use, with
no change at any of the 40 `fillText` call sites.

### The gate that holds it together
`testing/verify_core_matches_page.py`, `run_all.py` **step 29**. The agent now lives twice: in
`core/` (which the five verifiers test against Python) and inline in `demo/index.html` (which a reader
runs). The verifiers prove `core/` matches Python; nothing else would notice if the PAGE drifted from
`core/`, and then five passing checks would be testing code nobody sees.

It reads `core/_transform.json`, a provenance manifest the generator writes: per function, the SHA-256
of the page source extracted and of the module source produced, plus the substitutions in words.
**64 checks, 0 failed**, over 22 functions across both directories, 18 of them byte-identical.
Tamper-tested: a one-character change to `cfAttainable` fails both this gate and the conformal
verifier. **It becomes unnecessary the moment the page imports `core/` instead of carrying its own
copy.**

### Four defects the instruments found in themselves, worth knowing before writing more of them
1. **`\bUS\b` matched inside `toLocaleString('en-US')`** and silently rewrote the locale tag, because
   a hyphen and a quote are both non-word characters. `tkFormat` never referenced the global at all.
   Locale matching is case-insensitive, so no behavioural test would ever have caught it.
   `thread()` in the generator now refuses to substitute inside a string literal.
2. **The first drift gate asserted against difflib's chunking**, not against the code: `cfg` →
   `cfgFromStrings` arrives as an insertion of `"FromStrings"`, and `tkEvent(` → `_ev(` fragments
   because the strings share a `v` and a `(`. Replaced with hashes, which have no opinions.
3. **The diff tool re-found each run with `old.find(a)`** instead of using difflib's offsets, so four
   separate one-character substitutions all printed the same wrong context. A verification tool that
   prints confident, wrong context is how a real defect gets waved through.
4. **`verify_browser_explanation.js` had its own `fmt` stub returning an ASCII hyphen** where the page
   returns an en dash, so it had always compared explanations built with one formatter against a page
   shipping another. Now imports the real one, and passes, so the divergence was latent.

Also: the cross-module imports in `core/` are **derived**, not hand-written. A hand-written list
already cost the 1,336-explanation corpus once, because `explainHour` calls `plan` and the list said
only `fmt`.

---

## 1. Figures

<!-- FIGURES:BEGIN -- generated by sync_context.py, do not hand-edit -->

| Figure | Value | Derived from |
|---|---:|---|
| Real facilities in the registry | **637** | demo/unified_sites.json -> len(sites) |
| Of those, ready to run | **246** | sites.json offerable metros, joined on metro_key |
| Offerable metros | **250** | demo/sites.json -> sites[].offerable |
| States represented | **43** | distinct unified_sites.json sites[].state |
| run_all.py steps | **33** | count of STEPS entries in src/run_all.py |
| demo/index.html size | **480 KB** | byte length of the shipped page |
| Map GeoJSON sources | **2** | one clustered, one flat -- see 02-ARCHITECTURE |
| Map unisites-* layers | **5** | cluster, halo, points, flat-halo, flat |
| `#livecard` present | **yes** | standing rule: the live agent is never removed |
| `#livego` present | **yes** | standing rule: the live agent is never removed |

*Every row above is re-read from the artefact named beside it by `CONTEXT/sync_context.py`. None of it is typed by hand, so none of it can go stale without the check failing.*

<!-- FIGURES:END -->

### A distinction that is easy to get wrong
**250 offerable metros, but 246 ready-to-run facilities, and both numbers are correct.**
`sites.json` marks 250 metros `offerable`. Four of them have no matching row in
`unified_sites.json` (`CA_way_358455179`, `IL_way_863162820`, `VA_way_714622339`,
`VA_way_744496750`), so only 246 *facilities* join to an offerable metro. The mapping for those 246 is
strictly 1:1. **The number published on screen and in the README is 246**, which is the facility
count, and that is the right one for a reader looking at a map of facilities. Do not "fix" one of
these figures to match the other.

---

## 2. Where verification stands

Every verdict below was produced by running the check, not by reading a note about it. Detail,
commands and exit-code contracts are in `03-VERIFICATION.md`.

| Check | Verdict | Scale |
|---|---|---|
| `AGENTIC-ARBITER/src/audit.py` | **PASS** | 2,216 passed, 0 warnings, 0 failures |
| `testing/verify_palette.py` | **PASS** | 34 pairs, 0 failed, both themes |
| `testing/verify_state_filter.py` | **PASS** | 62 assertions, 3 consecutive clean runs |
| `testing/verify_map_hover.py` | **PASS** | |
| `testing/verify_site_panels.py` | **PASS** | 13 panels differ across sites, 1 declared shared, 0 identical-and-undeclared |
| The five cross-implementation verifiers | **PASS** | agent, conformal, decision, explanation, ticker |
| Live agent surface | **present** | `#livecard`, `#livego`, `/api/health` reports `live_available: true` |
| `testing/verify_core_matches_page.py` | **PASS** | 64 checks, 0 failed, 22 functions across `core/` and `charts/` |
| `testing/audit_nothing_lost.py` | **NO LOSSES** | 5,975 baseline paths walked, every function, id, artefact and verdict string present |
| `testing/verify_results_matches_page.py` | **PASS** | 12 checks, 100 engine functions byte-identical, 208 KB |
| `testing/verify_view_matches_page.py` | **PASS** | 8 checks, 105 engine lookups all accounted for |
| `testing/verify_app_flow.py` | **PASS** | 21 checks, pick to results in a real browser, 32-row tape, 11 canvases |
| `testing/verify_app_deterministic.py` | **PASS** | two renders identical: figures, labels, bar heights, map counts |
| Paid API calls spent this session | **0** | |

---

## 3. Change log

### 2026-08-28 - The new UI now carries the whole product, engine and all

**The user's correction:** the React app was a pick screen whose Configure button led back to
`demo/index.html`. Two of three stages, 18 cards, the reasoning tape and the live agent were not in
the new UI at all. Full account in section 0.

**What was measured before anything was built.** The page has 124 top-level functions. Rooted at the
real entry points, the configure + results + live closure is **100 functions, 208 KB**; the 24 outside
it are exactly the pick-stage map and search code the React app had already replaced. So the seam
falls at a natural boundary rather than through the middle of something, and with the pick stage
fenced off the engine calls **nothing** on React's side. Zero crossings, measured.

A finding that made the lift far safer than the raw grep counts suggested: **`R` is not a global.**
146 apparent references are almost all local `const R = decide();` plus right-margin variables
(`const L=46, R=14`). The genuinely shared state is 55 top-level declarations, all of which keep their
literal names in one module, so every reference stays byte-identical.

**Built:**
- `AGENTIC-ARBITER/results/engine.mjs` - 100 functions lifted byte for byte, plus a **three-function
  adapter** (`attachSites`, `currentSite`, `currentStage`) that is the only written code in the file
  and is pinned by hash so logic cannot accumulate there.
- `app/src/generated/engine-markup.ts` - the configure and results markup, 39 KB, six blocks, verbatim.
- `app/src/generated/engine.css` - the page's stylesheet, 96 KB, verbatim. It lifts cleanly because the
  page's CSS has **zero `url()` references** by deliberate design, recorded in its own comment: no
  `@font-face`, no `@import`, because the page must work offline and `verify_site_panels.py` demands
  byte-identical canvases, which a font arriving over the network cannot promise.
- `app/src/lib/engine.ts`, `app/src/components/EngineStage.tsx` - the seam.
- `testing/verify_results_matches_page.py`, `testing/verify_view_matches_page.py`,
  `testing/verify_app_flow.py` - three new gates, wired into `run_all.py`. **31 steps became 33.**

**A real defect found in the page and fixed there.** A CSS comment contained the text
`had THREE `*/` closers and one `/*` opener` - prose ABOUT the original bug. CSS comments have no
escaping, so that `*/` closed the comment, nine words of English were parsed as CSS, and the following
`/*` opened a new one. **The delimiters therefore balanced**, so `audit.py`'s `check_css_comments`
passed: it counts delimiters, and the count was right. Browsers error-recover to the next resync
point, so nothing ever looked wrong. It surfaced only when esbuild's stricter minifier warned during a
Vite build. `audit.py` gained a second check that asks the question the other way round - is any text
OUTSIDE the comments not plausibly CSS - and the count went 2,215 to 2,216.

**`audit_nothing_lost.py` was silently going vacuous.** It compared against `HEAD`, which was the
pre-work commit when it was written. Once the work was committed, `HEAD` contained the changes and
every comparison trivially agreed; the first run after committing reported 8 losses that were nothing
of the kind, because the rename had landed and `git show HEAD:INTAKE-ARBITER/...` simply failed. The
baseline is now a pinned commit id, and the section that read `git status` for deletions - zero, once
the rename was committed - now walks **all 5,975 paths that existed at the baseline** instead.

### 2026-08-28 - The pick screen had no way forward, and the URL layout that fixed it
The user caught that the React screen offered no "configure the plant" action. Added
`SelectedBar.tsx`, which hands off to `demo/index.html?site=<metro>` rather than pretending the
configure stage has been rebuilt. That one link exposed a real layout bug: the app's relative artefact
fetches only worked in vite dev, and both `testing/serve_app.py` and the intended production layout
would have 404'd. Fixed with a single `ART = '../'` base. Nothing was ever removed from the shipped
page; verified element by element. Detail in section 0.


### 2026-08-28 - Step 4: the React pick screen exists and is verified
`AGENTIC-ARBITER/app/`, nine source files, consuming `core/`, `charts/` and the same artefacts. Every
behaviour in the user's UI brief measured through the app's own probe surface. Five defects found and
fixed on the way, the real one being that maplibre 6 needs `setWorkerUrl` pointed at a properly
bundled worker. Detail in section 0. `CLAUDE.md` corrected: it forbade the bundler and the
`package.json` this work requires, which would have led a future session to undo it.


### 2026-08-28 - Steps 1 to 3 of the React migration, all green
`core/` (6 modules) and `charts/primitives.mjs` extracted from `demo/index.html`; all five
cross-implementation verifiers repointed to import them; `run_all.py` step 29 added as the drift gate
between the two copies. Detail in section 0. Nothing about the shipped page changed: audit 2,215/0,
palette 34/0, state filter 62/0, map hover PASS, all five verifiers PASS with corpora unchanged.


### 2026-08-28 - UI direction set, and the core extracted
The user said the UI is monotonous, has no visual hierarchy, and that the font reads as machine-like.
They asked whether the HTML could be replaced with a front end the `frontend-design` skill and the
21st.dev MCP server can act on, **without losing the deterministic output**, and chose the staged
plan. Details and the current position are in section 0.

**Two findings that shaped the answer:**
- 🔴 **The 21st.dev MCP server was configured but never loading.** It sat under the project key
  `D:/FGHackathon` while the session ran as `d:/FGHackathon`. Those are separate entries in
  `~/.claude.json`, so the tools had never appeared in any session, including the one where they were
  first asked for. Now registered on both keys. A backup is at `~/.claude.json.bak-ctx`.
- **The `frontend-design` skill is stack-agnostic.** It is design direction: palette, type scale,
  taking one justified risk. It does not emit React and does not care about the stack. **Only
  21st.dev is a reason to change stack**, because it emits React plus Tailwind.

**What determinism actually depends on**, established by reading the checks rather than assuming:
nothing in the verification layer needs vanilla JavaScript. It needs the agent to be **findable as
source text in one file**, which is a fragile coupling and the reason the extraction makes
verification *stronger* rather than weaker. Only four audit checks read the page at all
(`check_duplicate_element_ids`, `check_page_javascript_parses`, `check_panels_are_per_site`,
`check_retracted_claims`) and **none of them requires prose to be present**, so the brief's aggressive
decluttering is safe. The stated limits and the four sources live in `money-sources.md`, checked by
audit check 12, not in the page.


### 2026-08-28 - The context pack itself
Created `CONTEXT/` at the user's request: a folder that holds the project's durable state, is updated
as part of every change, and is re-read after every context compaction so quality is not lost to a
summary.

- `CLAUDE.md` at the repo root is the mechanism. It is loaded automatically every session and after
  every compaction, and it points here. Without it, "read the context folder" would be an intention
  rather than a behaviour.
- `sync_context.py` makes freshness mechanical rather than promised: it regenerates the memory mirror
  and the figures block, and fails on drift. It also asserts two standing rules that happen to be
  checkable (the live-agent elements exist; the map still has its second GeoJSON source).
- `HANDOFF.md` and `READING-THE-AGENT.md` moved in from the repo root. **This required code edits**,
  because `audit.py` and `testing/bump_spend_docs.py` open both by constructed path; prose citations
  of the form "HANDOFF section 6.3" were unaffected. See section 4 below for what was touched.
- Two stale paths fixed at the source in the auto-memory: `ship-production-not-mvp.md` still said
  `INTAKE-ARBITER/PLAN.md`, and `subagents-permitted.md` still described HANDOFF as 250 KB.
- `run_all.py` gained step 28, the pack's own freshness check. That moved the step count, which is
  itself a published figure in `README.md`, so it was updated in the same breath. The check caught the
  change immediately, which is the behaviour it exists for.

**Building the pack meant reading the repository properly, and that surfaced seven real defects.**
Six are fixed; the seventh is recorded in section 5 as a decision.

1. 🔴 **`run_all.py` contradicted its own comment.** `verify_state_filter.py` exits **3** when
   maplibre cannot be fetched from unpkg, because the page degrades to a note without it by design.
   The runner treated *any* non-zero code as a failed step, so on a machine with no route to unpkg the
   whole 28-step proof went red for a reason unrelated to anything it proves. A step can now
   **declare** which exit codes mean "could not run", with the reason; those are printed at the step
   and again in the banner, and the banner narrows its completion claim to what actually ran. Exit 1
   from that same step still fails the rebuild. **Not** fixed by treating 3 as success, which would be
   gotcha #74 all over again.
2. **`#mf_q` was a combobox that never said whether it was open.** `aria-expanded` was written once,
   hard-coded to `"false"` in the markup, and never updated, so a screen reader announced a closed
   list with eight facilities on screen. Worse than no ARIA role at all: the role promises an
   expandable listbox and then lies about its state. Now set at every open and every close.
   **Mine, from the same day the dropdown was built.**
3. **`#secnav` linked to a card that no longer exists.** `href="#limitscard"` survived the removal of
   the "Honest limits" card on 2026-08-26. A dead index entry is worse than a missing one: it tells a
   reader the page makes a disclosure it no longer makes here. Removed. `drawLimits()` is untouched
   and still derives all four limits from the artefacts, guarded by `if(!el) return;`.
4. **`setStage()` still carried a branch that would hide `#livecard`.** `data-needs="live"` was taken
   off the card on 2026-08-25, so the branch was dead, but its only possible effect was to hide the
   live card, which standing rule C1 forbids outright. Removing it makes the rule a property of the
   code rather than a note beside it. `data-needs="plume"` is live and different, and stays.
5. **`verify_state_filter.py` died with a traceback** instead of its documented exit 3 if the page's
   `US_STATE_NAMES` table were renamed: `load_state_names()` used `str.index`, which raises, and it
   runs before the browser work. Now `find`, and it reports the could-not-run properly. Verified by
   renaming the table in a copy of the page: exit 3 with a diagnosis. **Mine.**
6. **`demo/README.md` quoted three wrong `run_all.py` step numbers** (`verify_palette` as step 26, it
   is 24; `verify_site_panels` as step 20, it is 25) and said `verify_state_filter` makes 60
   assertions when it makes 62. Corrected. Step numbers shift every time a step is added, which is
   exactly why this pack derives its figures instead of quoting them.
7. **`README.md` published two stale figures about the gotcha registry**: "96 gotchas" and "running to
   #185". Measured against the file: section 10 holds **195** numbered entries, 1 to 196 with #50
   absent. Both corrected. Neither was re-derivable, which is the defect standing rule A3 exists to
   catch.

### 2026-08-28 - The map filter bar: four changes, three real defects
The user asked for four things. Each is now covered by assertions in
`testing/verify_state_filter.py`, which is new and is `run_all.py` step 27.

1. **The facility search box has its dropdown back.** `#mf_q` now renders `#mf_drop`, up to eight
   `.mfrow` rows carrying the facility name, its state in full, and a READY or CANDIDATE pill.
   Choosing a row flies the map to that facility and opens its inspector. It is a **separate element
   from `#searchresults`** on purpose: `verify_map_hover.py` drives `#sitesearch` and selects
   `.srchrow`, so reusing those ids would put two writers on one element.
2. **States are named, not coded.** `US_STATE_NAMES` covers all fifty plus DC; the select shows
   "California · 46", sorted by name, each count read from the registry. The expansion also reached
   the hover readout, the inspector's *Where* row, and both search lists, and it expands a trailing
   ", CA" **inside** a label, because `unified_sites.json` is inconsistent: 424 of its 637 labels
   already read "Ashburn, Virginia" while 213 read "Reston, VA". The artefact was not rewritten;
   this is a display-time expansion only.
3. **A selected state shows individual small circles**, fitted to that state's own extent.
   **This needed a second GeoJSON source.** maplibre fixes clustering at source creation and offers
   no setter, so a clustered source returns *cluster* features at low zoom whatever the layer filters
   say, and hiding the cluster layers reveals nothing. There are now two sources over the same 637
   features, one clustered and one flat, with exactly one visible. Radii step down to 7 / 5.5 / 4.5
   from the national 9 / 7 / 5.
4. **The page opens on California**, fitted, with no animation on load.

**Defects found and fixed on the way:**
- 🔴 `addData` was gated on `map.isStyleLoaded()`, which stays false while the OpenStreetMap basemap
  has tiles in flight. **On any network that blocks or throttles those tiles, none of the 637
  facilities were added to the map at all.** Now gated on `map.getLayer('basemap')`, which reads the
  parsed style and is independent of tiles. This is the second time this gate has bitten; it was
  `map.on('load')` before, tile-dependent for the same reason.
- The camera fit animated unconditionally, ignoring `prefers-reduced-motion`. Now
  `motionOK() ? 620 : 0`, which is both correct behaviour and the only state a headless check can
  measure.
- Search rows for a facility with no published run carried `aria-disabled="true"` while
  `searchOpen()` routes them to the inspector. A row that performs an action must not announce itself
  as disabled. Now `data-ready="0"`. **This one was mine, from earlier the same day.**

**A fourth defect, from extending the palette check** to the frosted surfaces nothing had measured:
`--glass` is translucent, so text on the bezel, the KPI cards, the drawer and the new dropdown is
text on a *composite*, and the drawer opens from a map click, which puts it on glass over the
**basemap**. Measured that way, light-theme `--muted` was **4.44:1**, under the 4.5:1 text floor, and
only 4.53:1 on `--surface-2`. It is now `#6c6c75`, clearing **4.64:1 on the worst of five surfaces**.
Both basemap values are measured off real screenshots (**#323232** dark, **#cfcfcf** light), located
by a marker the page paints at its own canvas origin so the two samples cover identical pixels. The
first draft of that constant *guessed* #dcdcdc and the measurement came back half a stop darker,
which is why it is measured.

**Also:** `verify_palette.py` now reads `rgba()` tokens, not only hex, and treats a surface it names
but cannot resolve as a **failure** rather than a skip. The old loop silently `continue`d past an
unknown surface, which would have reported PASS for a pair it never measured.

### 2026-08-28 (earlier) - Masthead cut, em dashes removed
Four paragraphs to three (162 words). The "rational hedge" argument moved into an `.info` popover
whose text is duplicated in the trigger's `aria-label`. Em dashes stripped from the six page strings
and twelve README rows I had written; the user's own prose left untouched.

### 2026-08-27 - Renamed INTAKE-ARBITER to AGENTIC-ARBITER
2,737 string occurrences across 2,649 files, the split bezel wordmark, and all 266 report PDFs
regenerated rather than byte-patched. Details and the deliberate exceptions in
`04-STANDING-RULES` C2.

*Earlier history is in `CONTEXT/HANDOFF.md`, which is the full record. Do not read it whole.*

---

## 4. Files touched by the CONTEXT move

Recorded here because a future session will otherwise wonder why these paths look unusual.

| File | What changed |
|---|---|
| `AGENTIC-ARBITER/src/audit.py` | the constructed paths to `HANDOFF.md` and `READING-THE-AGENT.md` now point into `CONTEXT/` |
| `testing/bump_spend_docs.py` | same, for `HANDOFF.md` |
| `README.md` | any markdown link to either document |

`audit.py` is the proof that this was done correctly: it re-reads both documents and would fail if a
path were wrong. It reports **2,215 passed, 0 failures** after the move.

---

## 5. Open items

Not blockers, and each is stated rather than quietly dropped.

### 🔴 BLOCKER, DEFERRED BY THE USER 2026-08-28: two measured day-pairs are not in the figures

**The user's decision: "dont do it right now, we'll do it later. just save the pairs somewhere for
now."** So nothing has been rebuilt and no published figure has been touched. This entry is the save.

**THE FIXTURES ARE SAFE.** All four files are tracked and committed, 7.2 MB each, 28.9 MB of paid
measured data:

```
testing/results/fixtures/n26_f_2026-08-25.json   n26_h_2026-08-25.json
testing/results/fixtures/n26_f_2026-08-26.json   n26_h_2026-08-26.json
```

`testing/results/n26_manifest.json` lists **6 complete forecast/outcome day-pairs**. The shipped
artefacts were built from **4**. `backtest.py` calls `perceive_fortyguard()`, which reads *every*
complete pair on disk, so a pipeline run today picks up all six.

**IT IS NOT NONDETERMINISM AND NOT A CODE CHANGE.** Proved by regenerating `backtest.json` from the
committed `trace.json` with the current `backtest.py`: the diff ADDS `/fortyguard_offsets/4` and
`/5`, dated 2026-08-25 and 2026-08-26. New input data, never adopted. The manifest was last committed
2026-08-27 in `01cc7aa`.

**WHAT MOVES WHEN IT IS ADOPTED.** Measured once, recorded here so nobody has to spend another full
pipeline run deriving it:

| Figure | Shipped, 4 pairs | Regenerated, 6 pairs |
|---|---|---|
| Pooled bound coverage | **65.6 %** (0.6559) | **78.6 %** (0.7857) |
| Attainable ceiling, n/(n+1) | 80.0 % (4/5) | 85.7 % (6/7) |
| Ladder 5 unanchored coverage | 0.9865 | 0.9165 |
| Unanchored cost | 561.7 h/yr | 312.8 h/yr |
| Ladder 5 + unanchored, offsets rotated | -156.0 | +92.8 |
| Significant reversal axes | 3 | 2 |
| `backtest.json` | | 51 values changed, +10 keys, -5 |

The 90 % promise is unchanged and the pre-registered test is **still NOT MET** either way, so the
honesty story survives; it gets stronger, because the bound would be measured on six real day-pairs
instead of four. Adopting it means restating `README.md` lines 119, 278 and 363, the CONTEXT figures,
and regenerating 243 artefacts and 266 PDFs.

**⚠ CONSEQUENCE WHILE THIS IS DEFERRED: `run_all.py` DOES NOT EXIT 0.** It regenerates and then
audits, so it rebuilds with six pairs and then fails `audit.py` against docs that quote four. Two
steps fail: `every other offerable site, on its own data`, and `AUDIT: everything, mechanically`.
`audit.py` run on its own against the committed artefacts is still **2,216 passed, 0 failures**,
because the docs and the shipped artefacts agree with each other. Both describe the four-pair state.

This matters because `README.md` says "If `run_all.py` is not green, do not believe a number on the
page." Today the honest statement is narrower: **the shipped numbers are internally consistent and
audited, and they are not reproducible from a full pipeline run until this is resolved.**

⚠ AND A TRAP FOR THE NEXT SESSION: `run_all.py` and `build_sites.py` REWRITE the artefacts in place.
A run leaves 243 modified files whose numbers no longer match the published figures. `git checkout --
AGENTIC-ARBITER/demo/` restores them. Do not read figures off the tree during or after a partial run;
one set of screenshots in this session caught a half-rewritten state and showed an 85.7 % ceiling on a
page whose documents say 80 %.

- **The empty `INTAKE-ARBITER/` husk cannot be deleted.** The editor's file watcher holds the
  directory. Safe to delete once released; nothing reads it.
- **The user's own prose still contains em dashes** deeper in the page and in the older documents.
  The rule governs what I write; sweeping theirs needs their say-so
  (`04-STANDING-RULES` B2).
- **`verify_palette.py` does not measure decorative borders on glass.** A pill's border on the
  light-theme frosted panel is about 1.06:1, which is below the 3:1 non-text floor but is not
  *required to identify a component or its state*, so it is out of scope for WCAG 1.4.11. Recorded so
  the omission is a decision rather than an oversight.
- **Write-only state in the page.** `INSPECT_KEY`, `LIVEJOB` and `ENV` are assigned or merely
  declared and never read anywhere. Harmless, and `audit.py`'s dead-code check cannot see them because
  it walks function nodes only. **Not removed:** `LIVEJOB` sits inside `runLive()`, and standing rule
  C1 says to ask before changing the live path. Editing working live code to tidy a dead variable is
  not obviously worth it.
- **`verify_api_defects.py` is the only paid verifier, always exits 0, and is deliberately not wired
  into `run_all.py`** -- but nothing in `run_all.py` says so, so its absence reads as an oversight
  rather than a decision. Recorded in `03-VERIFICATION` section 3 instead.
- **Whether `verify_site_panels.py` passes with the network fully blocked is unverified.** It asserts
  nothing about any CDN, but the page it renders fetches maplibre from one.

*(The scratch drivers that used to sit in `AGENTIC-ARBITER/demo/` -- `_agentlink_driver.html`,
`_phone.html`, `_shot.html` -- and `testing/verify_agent_link.py` are all gone as of 2026-08-28.)*
