<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 03 - Verification

Every instrument, what it actually proves, how to run it, and what it explicitly does **not** prove.
Read this before claiming anything works.

The governing idea, which is standing rule A3: **a figure in prose is a figure nothing re-reads.**
Every published number is re-derived from the file that produced it, by something that fails loudly
when it does not match.

---

## 1. The one command

```bash
cd AGENTIC-ARBITER/src && python run_all.py
```

**28 steps, zero API calls.** If it does not finish green, do not quote a number from the page.

### Three outcomes, not two
A step reports `OK`, `FAILED`, or `COULD NOT RUN`. The third exists because exactly one step depends
on something outside this repository: `verify_state_filter.py` fetches maplibre from unpkg at runtime,
and the page is designed to degrade to a warning note without it, so an unreachable CDN says nothing
about the code.

**A could-not-run is a declaration, not a blanket rule.** The step's tuple names the exit code and
the reason; any other non-zero code from that same step still fails the rebuild. The reason is printed
at the step and again in the final banner, and the banner's completion claim narrows itself to what
actually ran. This matters because of the project's own repeated finding, **gotcha #74: a skip is not
a pass.** A check that silently skips reports success for a path it never ran.

### The last five steps
| Step | What |
|---|---|
| 24 | `verify_palette.py` |
| 25 | `verify_site_panels.py` |
| 26 | `verify_map_hover.py` |
| 27 | `verify_state_filter.py` |
| 28 | `CONTEXT/sync_context.py --check` |

Step numbers shift whenever a step is added. They have been wrong in `demo/README.md` twice. This is
why `CONTEXT/01-STATE.md` **derives** its figures instead of quoting them.

---

## 2. `AGENTIC-ARBITER/src/audit.py` - the mechanical audit

```bash
python AGENTIC-ARBITER/src/audit.py
```
**Current verdict: 2,215 passed, 0 warnings, 0 failures.** Exits 1 on any failure.

**25 numbered sections** from 24 check functions, labelled `1, 2, 2b, 2c, 2d, 2e, 2f, 3, 4, 5, 5b, 6,
6a, 6b, 6c, 6d, 6e, 6f, 6g, 7, 8, 9, 10`. They are **not** numbered 1 to 10, and the printed order is
not the execution order.

The families worth knowing by name:

- **1 dead code**, walking `ast.FunctionDef` nodes. It does **not** see unused module-level
  constants, so a dead `let`/`const` survives it.
- **2 / 2b NaN-unsafe JSON writers, and emitted JSON is strict-valid.** Python will happily write
  `NaN`, which is legal Python JSON and illegal standard JSON.
- **3 decision-critical arrays are not display-rounded on write.** A rounded array flipped decisions
  at gate boundaries once.
- **5 / 5b retracted claims.** Scans the surfaces a reader meets, including
  `CONTEXT/READING-THE-AGENT.md`, for constants and phrases that were withdrawn.
- **6d panel-per-site.** Regexes `draw[A-Za-z]\w*\(` out of `drawAll()`'s body and requires every
  function it names to read a per-site global. Its empirical half is `verify_site_panels.py`.
- **7 module self-tests.** Runs seven subprocesses: `conformal.py`, `environment.py`,
  `plume_uncertainty.py`, `explain.py`, plus `ticker.py selftest`, `money.py selftest`,
  `report.py selftest`.
- **8 cross-language.** Regenerates three fixture generators in `demo/` then runs the five node
  verifiers (section 4).
- **9 / 10 published figures.** The registry holds **exactly 77 entries**, and its own size is a
  published figure re-read by check 10 and cross-checked against the README.

**The 2,215 total is dynamic**, printed as `len(PASSES) + len(WARNS) + len(FAILS)`. Most `ck()` calls
sit inside loops over registries, so **it cannot be counted statically** and is only knowable by
running it. Do not trust a quoted audit total you have not watched print.

`audit.py` writes exactly one file and deletes it: a temporary
`demo/_audit_syntax_check.js`, extracted from the last inline `<script>` and fed to `node --check`.

---

## 3. The five verifiers in `testing/`

Four are wired into `run_all.py`. **The fifth costs money and is deliberately not.**

### `verify_palette.py` - colour, measured
**Proves:** every colour pair the page renders clears its WCAG 2.1 floor in **both themes**: 4.5:1 for
text, 3.0:1 for non-text graphics. Tokens are parsed out of `demo/index.html` rather than retyped, and
it reads `rgba()` as well as hex so the **frosted** surfaces can be measured.

**Current verdict: 34 pairs, 0 failed.** Needs neither browser nor network. Exit 1 on any failure,
0 otherwise; there is no could-not-run code.

**The frosted pairs are the subtle part.** `--glass` is translucent, so text on the bezel, the KPI
cards, the drawer and the facility dropdown is text on a *composite*. It is composited over two
backdrops and checked against the harder: the page, and the **basemap**, whose rendered value is
measured off real screenshots (**#323232** dark, **#cfcfcf** light) because it is a raster pushed
through `raster-brightness-max` and not a token. A surface this file names but cannot resolve is a
**failure**, not a skip.

**Boundary remedy.** `--series-2` sits at 2.91:1 in the light theme and is kept, because the pair is
CVD-validated. The remedy is *checked*, not waived: the edge token must clear 3:1 on every surface,
the stylesheet must draw a border on `.legend i`, and the script must reference `EDGE` at least three
times. A half-applied remedy fails as though there were none.

### `verify_site_panels.py` - the byte-identical render gate
**Proves:** the empirical half of audit check 6d. Drives the real page through pick, configure and
results for **every offerable site** in a real browser, and diffs rendered text hashes plus canvas
pixel hashes panel by panel.

**Current verdict: PASS.** 13 panels differ across sites, 1 declared shared, 0 identical-and-undeclared.

**The gate that makes it mean anything:** it renders **one site twice** and requires byte-identical
output first. Without that, a difference between two sites proves nothing. This is why the page's
animations use fixed easing curves rather than spring physics.

Exit codes: **4** = no browser found (an explicit non-skip), **1** = fewer than two offerable sites,
fewer than two rendered, any finding, or a **stale `SHARED_CARDS` excuse**. Needs a browser and a
local `python -m http.server`; makes no assertion about any CDN. It is also the shared source of
`find_browser()` and `free_port()`.

> ⚠️ **What a difference test cannot catch: a wrong picture.** One site's overlay on another's
> photograph produces pixels that differ, so it passes. Audit check 6d separately bans any site's own
> coordinates, OSM ids and station from another site's page for exactly this reason. **Neither
> instrument judges whether a label collides. Open it and look.**

### `verify_map_hover.py` - the map names the right facility
**Proves:** the hover readout and the picker's search box name the right facility from
`unified_sites.json`; the resting state is a real message rather than a blank panel; a runnable site
offers the agent; a site with no published run states its real status and is **marked** as such.

**Current verdict: PASS.** Exit codes: **4** = no browser, **3** = server never bound / probe never
reported / probe reported an error, then 1 on any failure. Needs a browser and a local server, but
**no WebGL and no external network**.

**It states two things it does not verify**, rather than implying it does: that `map.on('mousemove')`
is wired to `natReadout()`, and that a real keystroke fires the search.

### `verify_state_filter.py` - the live map, read out of maplibre
**Proves:** all 43 state options carry their full name and the registry's own count; the page opens
fitted to California; each state's view selects exactly that state's facilities and paints them as
individual circles rather than clusters; the name box lists its matches and opens the one you choose;
and the four filters compose.

**Current verdict: 62 assertions, 0 failed**, three consecutive clean runs.

The only verifier needing **both** a browser with working software WebGL **and** the external network.
Exit 0 pass, 1 fail, **3 could not run** (no browser, no `</body>`, server never bound, probe never
reported, maplibre never loaded from unpkg, or `US_STATE_NAMES` renamed).

Its harness is worth reading before writing another browser check: `05-TRAPS` section 3 is mostly
lessons from building it.

### `verify_api_defects.py` - the paid one
**Proves:** every candidate FortyGuard API defect was reproduced over **repeated fresh calls** before
being written up, bucketing seven probes into CONFIRMED / INTERMITTENT / OBSERVED_ONCE / WITHDRAWN.

> 🔴 **It spends real credits.** It needs the network, a real key, and real credits. D1 alone issues
> ten heatmap calls, and re-runs are re-billed: `common.submit_poll` always issues a live submit and
> only *writes* fixtures, never reads them back. **It is not wired into `run_all.py`, and that is
> correct.** Do not run it without explicit direction (standing rule E2).

⚠️ **It always exits 0.** A CONFIRMED defect is printed and saved to
`testing/results/api_defect_verification.json` but never fails the process.

---

## 4. The five cross-implementation verifiers

```bash
node AGENTIC-ARBITER/demo/verify_browser_{agent,conformal,decision,explanation,ticker}.js
```

**Current verdict: all five PASS.**

They exist because the page **reimplements the agent in JavaScript**, and two implementations that
drift are worse than one. Each extracts functions out of the shipped HTML by string search
(`indexOf('function ' + name + '(')`) and scores them against the Python agent:

| | Proves |
|---|---|
| `agent` | the browser agent and the Python agent decide identically, over 500 random cases |
| `conformal` | the browser derives the conformal quantile exactly as `src/conformal.py` does |
| `decision` | the browser reproduces the decisions hour for hour, bound included |
| `explanation` | both give the **same reason** for every hour |
| `ticker` | the browser renders every stage event **character for character** as Python does |

They are also run as `audit.py` check 8. **This is the single strongest reason not to introduce a
build step:** a bundler's output has no `function decide(` to find.

---

## 5. `CONTEXT/sync_context.py` - the pack itself

```bash
python CONTEXT/sync_context.py --write     # regenerate the derived parts
python CONTEXT/sync_context.py --check     # exit 0 or 1
```

**Proves:** every derived figure in `CONTEXT/` still matches the artefact it came from; the memory
mirror still matches the auto-memory directory; no file in the pack is missing, the two deep-reference
documents included; **`CLAUDE.md` still exists and still points at the pack**, which is the only reason
the pack gets read at all; `#livecard` and `#livego` are still in the page; and the map still has its
second GeoJSON source.

Each of those guards was added because its absence would fail *silently*. The `CLAUDE.md` one was
tested by moving the file away: exit 1, with the reason named.

**States plainly what it does not check: the prose.** Judgement and history cannot be re-derived from
files, and its verdict says so rather than implying otherwise.

---

## 5b. The React app: four gates, and how to see inside it

The app has **four wired-in verifiers** as of 2026-08-28, and they check four different things. The
order matters, because each one catches a class the one above it cannot see.

| Verifier | What it proves | Scale |
|---|---|---|
| `verify_results_matches_page.py` | `results/engine.mjs` is still the page's own code | 12 checks, 100 functions byte-identical, 208 KB |
| `verify_view_matches_page.py` | the lifted markup is still the page's, and every engine lookup resolves | 8 checks, 105 ids |
| `verify_app_flow.py` | the two were actually wired together: pick to results, in a browser | 21 checks |
| `verify_app_deterministic.py` | two renders of the same screen produce the same numbers | figures, labels, bar heights, map counts |

### Why the flow check earns its keep
The first two are **static**. They prove the code and the markup are the page's; they cannot prove
anything about whether the halves were connected correctly. **Three defects passed both and were
caught only by pressing the buttons:**

1. A lifted declaration, `const BOOTED = boot();`, called the page's bootstrap and threw
   `ReferenceError` at import. Byte-identity said the code was perfect, because it was.
2. `cssv()` reads tokens through `document.querySelector('.viz-root')` - a **class** selector, which an
   id-based check cannot see. Absent, `getComputedStyle(null)` threw inside an async handler and the
   configure transition silently never completed.
3. React re-applied its own `dangerouslySetInnerHTML` over the engine's output, so `buildControls()`
   filled `#filters` and a later re-render emptied it again. Nothing threw. The stage said `configure`
   and the panel was blank.

Each is a reminder of the same thing: **a check that looks at inputs is checking your reasoning about
the inputs.** The generator's fence assertion was moved onto the emitted file for exactly this reason.

### The rule the app must obey
`setStage()` remains the **single owner** of what is visible. React's pick screen carries
`data-show="pick"` and lets the engine hide it, rather than conditionally rendering it, because two
pieces of code owning `.hidden` means the last writer wins. The engine's markup is injected once in a
layout effect and React never diffs those children again.

### The probe surface, for looking inside by hand

```bash
cd AGENTIC-ARBITER/app && npm run dev        # http://127.0.0.1:5173
cd AGENTIC-ARBITER/app && npm run build
python testing/serve_app.py 8123 --hold 16   # / = the page, /app/ = the built app
```

| URL | What it does |
|---|---|
| `?probe=1` | renders a hidden `#AAPROBE` div carrying the live map's state: layers, source counts, **distinct facilities actually painted**, the filter, the paint expression, the camera, and any errors |
| `?state=CA&operator=…&facility=KEY` | seeds the filters. A shareable deep link, and the only way a headless check can drive the three filter behaviours |

⚠ **`--hold` is not optional for a screenshot, and `--virtual-time-budget` makes things worse.** A
headless capture fires at the load event, always too early for this map; and a GeoJSON source tiles in
a WORKER on the real clock while virtual time races the page's timers. Measured symptom: source and
all three layers present, `querySourceFeatures` 0, `isStyleLoaded()` false, nothing actually broken.
`--hold` keeps one subresource open so the load event stays pending and the render loop gets real
wall-clock time.

⚠ **Two instrument lessons from building `verify_app_flow.py`,** both of which produced confidently
wrong output before they were fixed:

- **The give-up must be checked FIRST in a polling probe.** It sat at the bottom of the interval
  callback, after three step blocks that each `return` when not yet ready. So the only path that
  reached the give-up was one where a step had already succeeded, and a probe that never found its
  target could never report. Three runs printed "the probe never published", which says nothing.
- **Wait for the completion signal, not the first sign of life.** The tape streams one row at a time,
  so "at least 2 rows" was satisfied 200 ms in and the check failed a 32-row tape for having 2. The
  engine fills `#tapedone` when streaming ends; that is the thing to wait for.

And one assertion that was simply wrong: the check demanded `#livego` read "Run the agent on live
data". On a static host there is no `/api/health`, so `drawLiveUnavailable()` correctly disables the
button and says **"Live agent not attached"**. Asserting the live wording unconditionally would have
been asserting that a static host pretends to have a server. The check is now mode-aware.

⚠ **Still missing for the app:** `verify_palette.py` coverage of `app/src/index.css` (its tokens are
inherited, not independently verified), and the light theme has not been checked by eye.

### `testing/shot_hero.py` - looking at the hero, and measuring it

**Not a verifier**; it exits 0 either way and nothing runs it in `run_all.py`. It renders the splash to
PNG in both palettes and prints the composition, the four texture fetches and every text element's
contrast ratio.

🔴 **`render_shots.py` CANNOT PHOTOGRAPH THE HERO, AND WILL SILENTLY PHOTOGRAPH THE WRONG THING.** It
passes `--force-prefers-reduced-motion=reduce`, and `flags.gateEnabled()` returns false under that
query, so every shot it takes is of the page BEHIND the splash. That flag is correct for the shots it
was written for and fatal for this one.

⚠ **AND IT MEASURES THE SPHERE FROM WHAT THE COMPONENT PUBLISHES, not from the canvas box.** The canvas
covers the whole viewport by design, so a crop computed from the canvas reported "0 % cropped" for a
globe that is visibly cropped. `HeatGlobe.tsx` publishes `data-aa-sphere` after its layout pass and
this reads that. A measurement of the wrong box is worse than no measurement.

### `testing/shot_cards.py` - the headline row, measured at three widths

**Not a verifier**; it exits 0 either way and nothing runs it in `run_all.py`. It drives the app with
`?motion=off` -- which `flags.ts` guarantees leaves a FINISHED page rather than a broken one, so what it
measures is what a reader sees after the gate -- and at 1920, 1024 and 600 it screenshots the page and
prints the grid template, both card boxes, the gutter, the filter panel's box and both headline figures'
computed font sizes.

The three figures it exists to produce, at a 1920 window: card width **548 px**, gutter **76 px**, and
the card right edge and filter panel right edge both at **x 1647**. It prints the gutter only when the
grid actually has two columns; below 1100 px the cards sit under the prose and
`cards[0].x - col.right` is a large negative number that measures nothing.

⚠ **IT CAUGHT THE DECORATIVE DRIFT.** The first run read the card right edge at 1651 against the
panel's 1647, because `.aa-bubble-stack` floated on an `x` axis as well as a `y` and the sample caught
it four pixels out. The layout was correct; the animation was walking the card off the edge. Nothing
that reads the CSS could have seen that, and nothing that reads a screenshot by eye would have
measured it.

## 5d. `testing/cdp.py`, and the five checks that need a real pointer

⚠ **FOUR OF THE FIVE ARE `run_all.py` STEPS**, added 2026-08-30: `verify_tooltip.py`,
`verify_results_surfaces.py`, `verify_landing_surfaces.py` and `verify_scroll_and_theme.py`. Each guards a fault that shipped, so
each belongs in the one command that is supposed to prove the product. `shot_rail.py` is not a step,
for the same reason `shot_hero.py` is not: it measures and photographs, and exits 0 either way.


Added 2026-08-30. Every other browser check in this repository runs Chrome with `--dump-dom` or
`--screenshot`, evaluates a probe, and reads what the page published about itself. That is enough for
anything the page can do to itself and it is what the other ~700 assertions rest on. It cannot produce
two states:

* **`:hover` comes from real pointer position.** No DOM API sets it. A probe can read the RULE out of
  the CSSOM, which proves the rule was written, and cannot prove the browser applies it.
* **`:focus-visible` is a heuristic, not a synonym for `:focus`.** Chrome withholds it from a
  programmatic `.focus()` on a `<button>`, so a check that calls `.focus()` and finds no ring has
  proved nothing: that is the specified behaviour.

`cdp.py` is a ~200-line DevTools Protocol client over the already-installed `websockets`. It starts
Chrome with `--remote-debugging-port`, opens the page target's WebSocket, and exposes `goto`, `eval`,
`poll`, `hover` (`Input.dispatchMouseEvent`), `click`, `key` (`Input.dispatchKeyEvent`) and `shot`
(`Page.captureScreenshot`, with an optional clip so an element can be photographed rather than a
viewport). It tears its Chrome down in a `finally` and never leaves a profile behind.
⚠ **NO `--virtual-time-budget`.** Virtual time and a live CDP session fight: the clock runs ahead of
the socket and the page can finish before the first command lands. This harness waits on the real
clock, which is what a hover check has to do anyway.

### `testing/shot_rail.py` - the workspace rail, 208 checks in both palettes

Drives pick to configure to results the way `verify_app_flow.py` does, then measures the rail at rest,
with a real pointer on a row, and with focus arrived by a real Tab. Asserts the brief of 2026-08-30
line by line: label typography and its **measured** contrast against the rail's own surface (7.45:1
dark, 5.51:1 light), row box and type, the four signals that separate active from hover, the 2px and
3px travels, the 150ms durations, and that tabbing reaches every enabled row with a >= 2px ring.
Writes `shot_rail_{rest,hover,focus}_{dark,light}.png`.

### `testing/verify_tooltip.py` - the (i) panel, 70 checks

Hovers each of the five KPI `(i)` triggers with a real pointer and requires: an opaque background, no
backdrop-filter, no ancestor that makes a stacking context, no ancestor that can clip, a `<body>`
parent, and the panel topmost at **every** sampled point. Then the same again in pixels: the panel is
photographed and every pixel inside it must be its own fill or its own ink. Also slides between
adjacent triggers and requires at most one panel at any instant, checks the two edge cards stay inside
the viewport, checks it paints over the map, and drives focus, Escape and click.
🔴 **THE PIXEL ASSERTION IS THE ONE THAT WOULD HAVE CAUGHT THE ORIGINAL BUG.** Every computed style was
already correct; what was wrong was which element painted on top.

### `testing/verify_landing_surfaces.py` - the landing page end to end, 38 checks

The two rewritten hero bullets compared verbatim. The value card read block by block in DOM order,
with its money pair compared against `demo/portfolio.json`'s `usd_mid_*` rather than against a string,
every bold run required to match `[+-]?\$?[\d,.]+[kM%]?` so that only figures are emphasised, and the
word "chiller" required to be absent from it.

🔴 **THE RING LABELS ARE MEASURED AGAINST THE PATH, NOT AGAINST ITS SOURCE.** `getPointAtLength` walks
`#aa-ring-track` at 2,000 samples and reports the curve's real x extent over each label's own y band,
which is then compared with the label's `getBBox()`. That is what caught the previous fix: it had
computed the loop's edge from the control points, which a cubic never reaches. See `05-TRAPS` 5b.33.

🔴 **AND THE PULSE IS PROVED TO BE MOVING, NOT MERELY PRESENT.** Two samples of its computed transform
a beat apart; equal means the tween was constructed and is not running. Taken on arrival, then again
after a real click through to the configure stage and back, which is the exact trip that used to
leave the dot gone for good.
The reload check is a real second `Page.navigate`, and it asserts BOTH directions: the gate returns
after a document load, and it does NOT return after an in-document round trip.

### `testing/verify_scroll_and_theme.py` - short viewports, and a theme that stays put, 36 checks

🔴 **IT RUNS 1366x768 AND 1400x820 ON PURPOSE, AND THAT IS THE WHOLE REASON IT EXISTS.** Every other
browser check in this repository uses a tall window (1500x1400, 1500x1000, 1600x1000, 1440x1000), and
the scroll fault it guards only occurred when the viewport was short enough for a fixed-height shell
to clip its own content. Roughly 700 green assertions never saw it. See `05-TRAPS` 5b.36.

Three viewport/stage combinations, each asserting that the DOCUMENT has something to scroll, that
`window.scrollTo` actually moves `scrollY`, that `#app` no longer clips, and that the LAST Quick
Action row is fully on screen after scrolling to the bottom. It names the row in the output, because
"Choose a different site" is the control the reader said they could not reach.

The theme half drives the toggle with REAL pointer clicks through the exact sequence that reproduced
the report: two presses on the configure screen, which leave configure looking identical and used to
pin the landing page to light for good. It then asserts the landing group's keys are still empty, goes
back to the landing and requires it to be dark, and finally presses the toggle THERE and requires the
choice to survive a real reload. Both halves of the rule, in one run.

### `testing/verify_results_surfaces.py` - three reported surfaces, 23 checks

The hour dropdown (one `#c_hour`, handler bound, block not folded, and changing it really does redraw
`#tkhour` while leaving `#extable`'s 25 rows alone), the bound-coverage tile (green, no "FAILED", and
a caption whose every figure it re-derives from `demo/trace.json` before comparing), and the LBNL
sentence (acronym expanded, no unsupported claim, no em dashes).

## 6. The two experiment families in `testing/`

Not verifiers, and `run_all.py` runs neither as a family.

- **`test_n*`** - 50 files, the numbered experiment log N-1 to N-56, one file per **pre-registered**
  question, each docstring stating FREE or PAID and the call cost. 16 mention PAID. Numbering has
  gaps. **Some declare themselves dead in their own docstring:** `test_n13` is superseded by
  `test_n25_sharpen.py`; `test_n14` and `test_n18` have results invalidated by the 9-hour timezone
  bug. Read the docstring before trusting a result.
- **`diag*`** - 21 follow-up diagnostics, each attached to one test. Several re-analyse
  already-paid fixtures for free.

`run_all.py` runs exactly one of them, and only its offline subcommand:
`test_n26_coverage.py selftest`, as step 19. It runs zero `diag*` files.

**35 files in `testing/` import `load_key()`.** That function reads **one** path: the
repository-root `.env`, opened with `utf-8-sig` so a BOM is tolerated. Not `testing/.env`, not
`AGENTIC-ARBITER/.env`. See `05-TRAPS` 4.1.

---

## 7. What nothing here checks

Stated so the gaps are decisions rather than oversights.

- **Whether a label collides, or a chart is readable.** Only a human looking at it.
- **Whether a picture is the *right* picture.** Section 3, `verify_site_panels`.
- **The prose in `CONTEXT/` and in the README.** `audit.py` checks published *figures*; nothing checks
  narrative accuracy.
- **Decorative borders on the frosted surfaces.** A pill's border on the light-theme glass is about
  1.06:1, below the 3:1 non-text floor, but it is not required to identify a component or its state,
  so it is out of WCAG 1.4.11's scope. Recorded as a decision.
- **Whether `verify_site_panels.py` passes with the network fully blocked.** It asserts nothing about
  the CDN, but the page it renders loads maplibre from one. Unverified.
- **Write-only state in the page.** `INSPECT_KEY`, `LIVEJOB` and `ENV` are assigned or declared and
  never read. Harmless; `LIVEJOB` sits inside `runLive()`, which standing rule C1 says to leave alone
  without asking.

## 5c. The three verifiers added 2026-08-29

All three cost nothing to run: no API calls, and the two that need a browser skip cleanly without one.

### `verify_intro.py` - the cinematic intro, 227 checks

**Why it exists:** the splash is a full-viewport overlay at `z-index: 200` over a working product, and
`verify_app_flow.py` runs with `?motion=off` precisely so it never meets it. Without this file nothing
in the suite would notice if the splash started eating the Configure click forever.

Thirteen sections. The ones worth knowing about:
* **the overlay probe uses `elementFromPoint`**, not the absence of a node. It probes the Configure
  button when it is on screen and the viewport centre when it is not, and records WHICH, so a pass can
  never be mistaken for the other measurement;
* **`motion=off` must leave no trace** -- no gate, no diagram, no field, no body attribute;
* **the audio contract is observed by patching `HTMLMediaElement.prototype`** before the bundle runs
  (possible because Vite emits a deferred module while a classic inline script in `<head>` executes
  during parse). `audio.ts` builds its elements with `new Audio()`, so they are never in the DOM;
* **contrast is measured in both palettes**, compositing the text colour's alpha and every inherited
  opacity over the nearest opaque background. Eight elements, 4.5:1 floor. It has caught four real
  failures;
* **`load(..., realtime=True)`** removes the virtual-time budget for the scroll handoff. See trap
  5b.13;
* **the handoff is swept DOWN AND BACK UP**, because the bug it guards against was one-way;
* **sections 14 and 15, added 2026-08-29 with the hero rebuild.** 14 asserts BOTH HALVES of the
  instruction that moved the five stage rows out of the hero: zero of them on the splash, and five of
  them below the map with their labels, notes, icons and timestamps. Either alone is a false pass,
  because "deleted outright" satisfies the absence and "still in the hero" satisfies the presence.
  15 measures the rows' own contrast, separately from the splash's, because the hero is pinned dark in
  both palettes and the rows sit on a surface that follows the theme, so the same token passes in one
  and fails in the other.

🔴 **SECTION 14 FOUND A REAL PRODUCT DEFECT, which is the whole argument for writing it.** It measured
all five rows at `opacity: 0`. The cause is `05-TRAPS` 5b.13 in a new guise: a CSS animation in its
active phase overrides the element's declared style, so a frozen animation clock holds the `from`
keyframe for ever. `animation-fill-mode` is irrelevant and removing it changed nothing. The product now
carries a wall-clock watchdog that marks each row `data-settled` and cancels the animation, and the
check asserts THAT rather than an animated value, per 5b.13's own first consequence.

### `verify_launch.py` - the Initialize Arbiter cinematic, 68 checks

**Why it is a separate file from `verify_intro.py`:** it runs on a REAL clock. Every other browser check
uses `--virtual-time-budget`, and GSAP does not advance under it (`05-TRAPS` 5b.13), so a GSAP-driven
seven-second sequence cannot be measured there at all: what completes it is the wall-clock watchdog, and
every cue attached to a timeline label is never reached. This file removes the budget and lets
`serve_app.py --hold 15` give the page real seconds. It is slow, about three minutes, and it costs
nothing.

Eight sections, one per scenario the brief named: the normal run (including the push-in, measured from a
`data-aa-dolly` the globe publishes), the escape hatch from Esc, Space, a click and five presses at once,
the absence of any visible skip hint across three scenarios, the muted short path, every audio file
404ing, a double click, navigating away mid-sequence, and the `?cinematic=off` kill switch. Section 8
reads the source and asserts the contract: no audio listener, a wall-clock watchdog, and the hatch bound
literally earlier in the function than the timeline.

⚠ **Its own comment scan masks comments first** (`05-TRAPS` 5b.1): `launch.ts` explains at length why it
does not chain off `audio.onended`, and a substring search for that name finds the explanation.

### `verify_stop_control.py` - does "Stop agent now" stop the spending, 31 checks
The assertion is a CALL COUNT, not a flag: stopped after 2 of 12 submits, `submit_window` is called
exactly 2 times and 10 windows come back `stopped_by_operator`, which is 42,200 credits not spent. The
two functions that reach FortyGuard are stubbed and one assertion is that the stub was never reached.

### `verify_live_report_button.py` - the live run's PDF, 25 checks
Checks BOTH halves, because either alone is a false pass: a button pointing at a broken route and a
working route with no button look identical from one side. Driven with a replay fixture selected by
TILE DISTANCE rather than by filename, which is the criterion the product itself applies.
