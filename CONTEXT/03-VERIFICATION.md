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

## 5b. The React app, and how to see inside it

The app has no automated verifier yet. What it has is a **probe surface**, which is how every claim
about it in `01-STATE.md` was measured rather than eyeballed.

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

⚠ **Still missing for the app:** a wired-in verifier (the probe is driven by hand today),
`verify_palette.py` coverage of `app/src/index.css`, and any equivalent of the byte-identical render
gate.

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
