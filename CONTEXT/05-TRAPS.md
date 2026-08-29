<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 05 - Traps

Things that have already cost real time in this repository. Each one is written as *what you will
observe*, then *what is actually wrong*, because the observation is never the cause.

**This file is the TOOLING and ENVIRONMENT set only.** The project's domain gotchas are a separate,
much larger registry: `CONTEXT/HANDOFF.md` section **10, "GOTCHAS - every one of these actually
bit"**, plus section **3.6.7, "GOTCHAS A NEW SESSION WILL HIT"** (9 entries). Section 10 holds
**195** numbered entries across 125 KB, numbered 1 to 196 with #50 absent, and **81** distinct
numbers are cited from code comments, so when you see `gotcha #67` in a comment, that is where it
is defined. Do not duplicate entries here; add new ones there and cite the
number.

---

## 1. The page

### 1.1 A top-level `let`/`const` is NOT a property of `window`
**You observe:** a browser probe polls `window.NATMAP` (or `window.US`, `window.NATBYKEY`) forever
and times out against a page that is working perfectly.
**Actually:** in a classic script, top-level `function` declarations become `window` properties but
top-level `let`/`const` live in the global *lexical* environment and never appear on `window`. Use the
bare identifier with a `typeof` guard: `typeof NATMAP !== 'undefined' && NATMAP`.
**Cost so far:** three separate timeouts, in `verify_map_hover.py`, `verify_site_panels.py`, and a
screenshot driver in this repo's scratch work.

### 1.2 The bootstrap must be the LAST statement in the script
**You observe:** the page hangs on "Loading saved data…" with no error.
**Actually:** `boot()` ran before the `let`/`const` declarations below it had executed, so it hit a
temporal dead zone. `const BOOTED = boot()` therefore sits at the very end of the single inline
script, deliberately. If you add code after it, it must not be a declaration `boot()` depends on.

### 1.3 Editing `index.html` flips it to CRLF
**You observe:** a Python patch script that matched yesterday finds zero occurrences today.
**Actually:** the Edit tool normalises the file to CRLF, and patterns containing `\n` then miss.
Either read and write with `newline=""` and normalise back to LF after every edit, or write patches
that do not span line breaks. The repo's `.gitattributes` is the other half of this story: check it
before assuming what is on disk.

### 1.4 One inline script, checked with `node --check`
`audit.py` extracts the LAST inline `<script>` (by `rfind`) and runs `node --check` on it. A syntax
error anywhere in ~7,000 lines fails the audit with a line number relative to the extracted body, not
to `index.html`. Extract it the same way to find the real line.

---

## 2. The map (maplibre-gl)

### 2.1 Clustering cannot be switched off after a source is created
**You observe:** a state view shows cluster bubbles instead of individual facilities, and hiding the
cluster layers reveals nothing underneath.
**Actually:** maplibre decides at source-creation time whether a GeoJSON source clusters, and offers
no setter. Below `clusterMaxZoom` the source returns *cluster* features, so the point layer has
nothing to draw. This is why there are **two** sources over the same 637 features, one clustered and
one flat, with exactly one visible. See `02-ARCHITECTURE` section 3.

### 2.2 `isStyleLoaded()` is false while raster tiles are in flight
**You observe:** the map renders grey with no dots at all, and nothing errors.
**Actually:** `map.isStyleLoaded()` requires every source to be loaded, and the basemap is an
OpenStreetMap raster source. On a network that blocks or throttles those tiles it stays false
forever. Gate data layers on the parsed style instead: `map.getLayer('basemap')`. **This bit twice:**
first as `map.on('load')` (also tile-dependent), then again as the `isStyleLoaded()` guard.

### 2.3 A `symbol` layer needs a `glyphs` endpoint, and fails silently without one
**You observe:** you added cluster count labels; the style comes back with one fewer layer than you
added and no exception is thrown.
**Actually:** maplibre routes that failure to its own `error` event rather than throwing. This page
ships no font server by design, so cluster counts are carried by radius plus a text readout beside
the map instead.

### 2.4 CARTO basemap tiles now require an API key, and return HTTP 200 without one
**You observe:** tiles load, and every one has "API KEY REQUIRED" watermarked across it.
**Actually:** a 200 response is not a valid tile. The page uses keyless OpenStreetMap tiles pushed to
grey with maplibre `raster-*` paint properties instead.

### 2.5 `queryRenderedFeatures` is not a sound oracle for an exact count
Two independent reasons:
- it returns **one entry per source tile** a feature appears in, so a point inside a tile's buffer of
  a boundary is counted twice. Count distinct `properties.key` into a `Set`.
- it reads the **last painted frame**, and maplibre repaints the layers of one source
  independently, so a frame can hold the new filter on the glow layer and the old one on the point
  layer, stably, across successive reads.
For "which features does this layer select", use `querySourceFeatures(src, {filter:
map.getFilter(layer)})`, which is frame-independent. Keep the rendered count for its own separate
job: proving the layer is actually painting.

---

## 3. Headless Chrome and the verifiers

### 3.1 maplibre DOES render headless, with the right two flags
`--enable-unsafe-swiftshader --use-gl=angle` gives the headless session a software WebGL rasteriser.
Before those flags, "headless Chrome cannot reach a loaded MapLibre state here" was recorded as
gotcha **#155** and believed; `testing/verify_state_filter.py` now reads the live map. If you find a
comment claiming the map cannot be rendered headless, it predates 2026-08-28.

### 3.2 `--virtual-time-budget` compresses timers but not the network or workers
This is the single richest source of false failures in this repo.
- A `setTimeout` fallback resolves in **no wall-clock time**, so it fires before the thing it was
  guarding. Wait on **events** (`moveend`, `idle`, `render`), not on timers.
- Every timer fallback is spent from **one shared budget**. Seventeen settles at a 12 s fallback each
  overran a 120 s budget, and Chrome dumped the DOM mid-probe, so the marker element came back empty
  and the probe looked like it had crashed. Sum your fallbacks against the budget.
- A GeoJSON source builds tiles in a **worker**, on the real clock. Retrying on a compressed timer
  runs every attempt before the worker delivers anything. The lever is that Chrome **pauses the
  virtual clock while a network fetch is outstanding**, so `await fetch(...)` buys real time. A 404
  against a local server buys about a millisecond, which is not enough; `verify_state_filter.py`
  serves its own `/__warm*` path that sleeps **120 ms** for exactly this purpose.

### 3.3 `requestAnimationFrame` does not tick in the mode the verifiers use
A probe that pumps frames with `rAF` never returns. Use maplibre's `render` event after
`triggerRepaint()`, which is guaranteed to be scheduled.

### 3.4 An animated camera move is unreadable under virtual time
Because `rAF` does not tick, an ease never progresses and every state reports the view it started
from. `--force-prefers-reduced-motion=reduce` makes the page **jump** instead, which is both the
correct behaviour for a reader who asked for it and the only state the check can measure.

### 3.5 A converging read must converge on LIVENESS, not on the assertion
A retry loop that waits until the claim is true proves nothing. Wait until *the layer the page says
it is showing* has painted something, and until two successive reads agree; then assert. The
distinction is what keeps `verify_state_filter.py` honest, and it is written into its comments.

### 3.6 `--screenshot` fires at the load event, so a WebGL map is always empty
Hold a subresource open to keep the load event pending and buy the render loop real wall-clock time.
That is what `slowserve.py` is for (`/__hold.js`).

### 3.7 A screenshot driver must be SAME-ORIGIN to drive the page
An `iframe` from `file://` to `http://127.0.0.1` cannot touch `contentWindow.document`. Write the
driver into the served directory instead, as a copy of `index.html` with a probe appended before
`</body>`, and **delete it afterwards**: it sits in the directory that gets deployed.

### 3.8 Never blanket-kill Chrome
`Get-Process chrome | Stop-Process -Force` closes the user's own browser. It has happened. Kill by
the specific PID you spawned, or let the harness clean up.

### 3.9 Killing a verifier's parent leaves its servers running
`verify_site_panels.py` spawns `python -m http.server`. Killing the parent orphans them, they hold
port and directory locks, and the next `git mv` fails with "Permission denied" for reasons that look
nothing like the cause.

---

## 4. Keys, spend and servers

### 4.1 The API key is read from the REPOSITORY ROOT `.env`, nowhere else
`testing/common.py:load_key()` opens `<repo root>/.env`. Running
`cp .env.example .env` from inside `AGENTIC-ARBITER/` creates a file that **nothing reads**, and the
symptom is an authentication failure that looks like a bad key. The correct sequence is
`cd <repo root>` then `cp AGENTIC-ARBITER/.env.example .env`.

### 4.2 Never print, echo, log or transmit the key
It is gitignored and untracked, and it is a real credential. Read it only through `load_key()`.

### 4.2b FOUR WINDOWS SCHEDULED TASKS COULD SPEND MONEY ON THEIR OWN, and three were armed
Disabled 2026-08-28 at the user's direction, minutes before the next would have fired. They are the
user's own collector, set up deliberately with `--allow-paid`, and they are **not** part of
`run_all.py`; nothing in the pipeline spends.

```
FG-N26-Chicago-Offset    daily 13:35   python testing/n26_chicago_offset.py collect --allow-paid
FG-N26-Coverage-Retry1   daily 13:50
FG-N26-Coverage-Retry2   daily 14:15
FG-N26-Coverage          already disabled
```

**Why they were stopped: the collector had stopped returning data and was still being billed.**

| Date | Attempts | Tiles returned |
|---|---|---|
| 2026-08-25 | 2 | 17,862 and 17,862, captured |
| 2026-08-26 | 2 | 17,862 and 17,862, captured |
| 2026-08-27 | 3 | 0, 0, 0 |
| 2026-08-28 | 1 | 0 |

Four consecutive empty results at 4,220 credits each. The 08-25 and 08-26 successes are where the two
unadopted day-pairs in section 5 of `01-STATE.md` came from.

**Re-enable with:**
```
schtasks /change /tn FG-N26-Chicago-Offset  /enable
schtasks /change /tn FG-N26-Coverage-Retry1 /enable
schtasks /change /tn FG-N26-Coverage-Retry2 /enable
```

🔴 AND THE DIAGNOSTIC LESSON, because I got this wrong out loud first. A changed
`testing/results/api_usage.json` after a pipeline run does **not** mean the pipeline spent. `audit.py`
WRITES that file: it re-derives the ledger from the manifest, so a scheduled task's spend surfaces the
next time the audit runs and looks like the audit's fault. Check `schtasks /query` and the fixture
mtimes before concluding anything about who spent. `agent.py` has no network code at all.

### 4.3 A live paid run costs 4,220 credits per hourly window
50,640 for a 12-hour horizon. `serve_live.py` requires **two** keys to spend: the `--allow-paid`
flag on the server *and* a flag on the request. Do not spend without explicit direction.

### 4.4 "Live agent not attached" usually means the wrong server is running
A plain `python -m http.server` serves the page but has no `/api/health`, so the page correctly
reports no live agent. Run `serve_live.py`. Check with
`curl http://127.0.0.1:<port>/api/health`.

---

## 5. Windows and git in this working copy

### 5.1 `git mv` on a directory fails while anything holds it
Orphaned servers (3.9 above) and the editor's file watcher both do. The old `INTAKE-ARBITER/`
directory is still present for exactly this reason and could not be removed. Move children
individually if you must, and expect a husk.

### 5.2 An MCP server registered under the wrong-cased project key never loads
**You observe:** an MCP server you configured is simply absent. No error, no warning, and asking for
its tools returns nothing.
**Actually:** `~/.claude.json` keys `mcpServers` **per project path, and the key is case-sensitive**.
`D:/FGHackathon` and `d:/FGHackathon` are two separate entries. The 21st.dev server was registered on
the capital-D key while sessions ran as lowercase, so it had never loaded in any session, including
the one where it was first asked for.
**Fix:** register the server under both spellings. Check with
`python -c "import io,json; d=json.load(io.open(r'C:/Users/<you>/.claude.json',encoding='utf-8')); print({k:list((v.get('mcpServers') or {}).keys()) for k,v in d['projects'].items() if 'fghackathon' in k.lower()})"`.
**And:** MCP servers connect when the CLI **process** starts. Editing the config mid-session does
nothing until a restart, so a config fix and a "the tools still are not there" observation are not in
conflict.

### 5.3 The shell's working directory persists between calls, and drifts
A `cd` in one command changes the directory the next command starts in. A `grep HANDOFF.md` that
reports "No such file or directory" is usually this. **Use absolute paths.**

### 5.4 Heredocs mangle non-ASCII AND backslash escapes
Emoji, arrows and dashes passed through a bash heredoc arrive corrupted. Write script files with the
Write tool instead when the content is not plain ASCII.

**It also eats backslash escapes, which is worse, because the result usually still runs.** Hit nine
times as of 2026-08-28. Observed corruptions:

| Written | Arrived as | Symptom |
|---|---|---|
| `\b` | a literal BACKSPACE byte | the regex silently matches nothing: "0 classes" in a 96 KB stylesheet |
| `\n` inside an emitted template | a real line break | invalid TypeScript, or an unterminated string |
| `" \\t\\r\\n"` | a literal tab and newline | `SyntaxError: unterminated string literal` |
| `/\bprobe\b/` | a regex holding BACKSPACE bytes | matched nothing; replaced with `.includes('probe')` |

**The habits that avoid it:** use Write and Edit for anything containing a backslash; build escapes
with `chr(92)`, `chr(10)`, `re.escape()` and `json.dumps()` instead of writing them literally; and
prefer `str.isspace()` to a whitespace-escape literal.

---

## 5b. Checks that look right and prove nothing

Four instances in one session, 2026-08-28. Each check passed, each was wrong, and the shape repeats.

### 5b.1 A name in prose is not a definition: MASK COMMENTS FIRST
This codebase documents its own bug history in comments, and those comments QUOTE code. A scan for a
definition therefore finds the story about it.

| The scan | What it actually found | Consequence |
|---|---|---|
| ids in the lifted markup | `id="c_site"` inside an HTML comment about a historical duplicate id | reported present; the real element was on React's side, and the app stalled at the configure stage |
| `$('#limits')` call sites | the war story that quotes the lookup | reported as an unguarded lookup, when the code beneath it is guarded |
| the results closure | `//` inside the string `'<code>file://</code>'` swallowed the rest of the line | `buildSitePicker` reported OUTSIDE a closure that plainly calls it |
| CSS comment balance | `*/` written inside backticks in prose | the delimiters BALANCED, so the check passed while nine words of English were parsed as CSS |

Mask comments and string bodies before any analysis, **length-preservingly**, so line numbers stay
usable. And strip strings BEFORE line comments, never after.

### 5b.2 Assert on the OUTPUT, not on the inputs
The engine generator asserted its fence over every function it lifted, and passed. It took the 55
top-level declarations wholesale, and one was `const BOOTED = boot();`, the page's entire bootstrap.
The emitted module threw `ReferenceError` the instant React imported it.

Checking the inputs is checking your own reasoning about what the inputs contain. The assertion now
runs over the emitted file and refuses to write it.

### 5b.3 A polling probe must check its give-up FIRST
With the give-up after the step blocks, and each step doing `if (not ready yet) return`, the only path
that reaches the give-up is one where a step already succeeded. A probe that never finds its target can
then never report, and prints "the probe never published", which says nothing.

### 5b.5 A MEASUREMENT THAT WRITES IS NOT A MEASUREMENT, and `git add -A` will ship it
Timing the live path with `live.py run --replay <window>` produced the CPU number that decided the
Render instance question. It also **wrote `AGENTIC-ARBITER/demo/live.json`**, a shipped artefact, which
its own output announced (`wrote: live.json`) and which I did not read. The next `git add -A` committed
it, so a measurement's output became part of what deploys.

`audit_nothing_lost.py` caught it: *"no JSON value changed beyond the rename: live.json, 77 values"*.
`audit.py` did not, because the file's shape and status were unchanged and only the numbers moved.

**The habits:** read what a tool says it wrote; prefer `git add <path>` over `git add -A` right after
running anything that produces output; and if a measurement must write, copy the artefact aside first
and restore it. Both `--replay` here and `build_sites.py` earlier in this project mutate `demo/`.

### 5b.4 Wait for the completion signal, not the first sign of life
"At least 2 tape rows" was satisfied 200 ms into a stream that ends at 32, and the check failed a
working tape. Find the thing that means *finished* (`#tapedone` here) and wait for that.

### 5b.8 A LONG `git commit -m` IS PARSED AS A PATHSPEC, and the push then reports success
Two rounds of work were reported as committed and pushed. Neither commit existed. The message was a
long multi-line string after `-m`, and git took part of it as a filename:

```
Co-Authored-By: ...' did not match any file(s) known to git
```

The commit failed, the background task went on to `git push`, the push succeeded with nothing new in
it, and the task's exit code came from the PUSH. Everything was still staged, so nothing was lost, but
"done" was reported twice for work that was not in the repository.

**Two rules.** Use `git commit -F <file>` for any message longer than one line. And when a task chains
`commit && push`, read the COMMIT step's output: a zero exit from the push says nothing about whether
the commit happened.

### 5b.12 THE PAGE ASSUMES THE WINDOW IS THE SCROLLPORT; IN THE APP IT IS NOT
`index.html` sizes its sticky panels against `100vh` minus a fixed bezel, which is exact there: the
window scrolls and the bezel is the only thing above. The React app puts the same markup inside
`.aa-workspace-main`, a nested scroller starting below the masthead and the tab header, so every
`100vh`-based height is too tall by however much sits above it. Measured overshoot for
`aside.sidebar`: 198px, which left 44px of its 260px of overflow on its own scrollbar and the rest on
the container behind it.
The tell is TWO scrollers in the chain where the reader expects one. `scratchpad/probe_railscroll.py`
walks from an element to `html` and prints every ancestor whose `scrollHeight > clientHeight`.
The fix is not a smaller constant, which would just be a guess at the masthead's height. Measure the
scrollport and publish it: `--aa-scrollport` from a ResizeObserver on the real container.

### 5b.13 GSAP DOES NOT ADVANCE UNDER CHROME'S VIRTUAL TIME, and neither does ScrollTrigger
Every browser check in `testing/` runs Chrome with `--virtual-time-budget`, which is what lets a
scenario describing 12 seconds finish in two. GSAP's clock does not keep up with it. MEASURED:

* the hero entrance wrote its from-states correctly (`transform: translate(0%, 115%)` inside an
  `overflow: clip` mask), rAF fired 150 times over 2.5 s, nothing threw, and 5 s of virtual time moved
  the eyebrow's opacity to **0.9375** and the call to action **0.07px** into a 14px rise;
* the scroll handoff reported `--aa-th-fade` of exactly **1** at every scroll position from 0 to 750,
  i.e. it never fired at all;
* `gsap.delayedCall` scheduled for 2.5 s had still not run at 6.2 s.

THREE CONSEQUENCES, and they are different from each other:
1. **Do not assert an animated VALUE under virtual time.** Assert the declaration (`transitionProperty`,
   `animationDuration`), the mounted window, and the END STATE.
2. **Anything that DECIDES when to start must not be on the animation clock.** `gsap.delayedCall` was
   replaced with `window.setTimeout` for exactly this: when to begin is a wall-clock question.
3. **For the few things that must be seen moving, remove the budget.** `testing/serve_app.py --hold N`
   holds one subresource open, which delays the load event, which is what `--dump-dom` and
   `--screenshot` wait for. The page then runs on a REAL clock for N seconds.
   `verify_intro.py`'s `load(..., realtime=True)` is that mode.
### 5b.13b IT IS NOT ONLY GSAP: A CSS ANIMATION HOLDS ITS `from` KEYFRAME FOR EVER TOO
**You observe:** five rows that should have faded in are all sitting at `opacity: 0`, long after their
520 ms animation should have ended. Nothing threw.
**Actually:** the same frozen animation clock as 5b.13, applied to a plain CSS `animation`. While an
animation is in its ACTIVE phase it overrides the element's own declared style, so a clock stuck at
progress 0 paints the `from` keyframe indefinitely.
⚠ **`animation-fill-mode` IS NOT THE FIX, AND TRYING IT COSTS A ROUND.** The first attempt removed
`both`, on the reasoning that the fill was what held the from-state. It changed nothing, because fill
mode only governs the BEFORE and AFTER phases and the animation is neither.
**The fix is a wall-clock watchdog**, the same shape `intro/timeline.ts` already uses: a
`window.setTimeout` marks the element `data-settled`, and a CSS rule cancels the animation for a
settled element, so it falls back to its own declared style. Make that declared style the FINISHED
state and a dead clock leaves a finished page.
**And the check has to assert the watchdog's result, not the animated value**, which is 5b.13's own
first consequence.

### 5b.26 A LOCALSTORAGE KEY THAT ALREADY EXISTS CANNOT BE REPURPOSED AS A "HAS CHOSEN" MARKER
**You observe:** a stage-dependent default theme works perfectly on every fresh profile the harness
launches, and does not work at all on the deployed site, for you or for anyone who has used it before.
**Actually:** the marker was `aa-theme`, on the reasoning that the key exists only if the toggle wrote
it. That is true of the code as written and false of the world: this app has written `aa-theme` on
every theme change for weeks, so every returning reader already had one and every returning reader
counted as having chosen. The default was never reached by anybody who could report on it.
**The fix is a key with no history:** `aa-theme-choice`, written only by `chooseTheme()`. The old key
stays, demoted to a CACHE of the resolved palette that the pre-paint script reads so there is no flash.
🔴 **AND THE HARNESS HAD TO BE TOLD.** `verify_intro.py` seeded `aa-theme` to choose a palette. Once the
app treats that key as a cache it is free to overwrite it, so seeding it tests nothing; the fixture now
writes both keys. A fresh profile is exactly the population a "returning reader" bug is invisible to.
**The habit:** before making a key's PRESENCE mean something, ask what is already in it in the field. A
fresh browser profile is not a sample of your readers.

### 5b.25 `elementFromPoint(x, innerHeight)` IS OUTSIDE THE VIEWPORT AND RETURNS null
**You observe:** an overlay-coverage check reports that a full-screen gate does not cover the page. The
gate is `inset: 0` and a screenshot shows it covering everything.
**Actually:** the probe took the centre of a button, checked `by >= 0 && by <= innerHeight`, and hit
tested there. The last y a viewport of height H owns is H-1, so at exactly H the call returns null, and
null was reported as "hits none" rather than as "asked about a pixel that does not exist".
**What made it fire:** a layout change, not a logic change. The masthead prose column narrowed from
1334 px to 742 px when the summary cards became a real grid column, each bullet took an extra line, and
the button's centre landed on exactly y=844 in an 844 px viewport. An off-by-one that had been latent
for as long as the check existed.
**Two fixes:** strict `<` on both bounds, and -- the general one -- if `elementFromPoint` returns null,
re-ask at the viewport centre and record which point was used. A probe should never report a null as
though it were a measurement.

### 5b.24 `new THREE.WebGLRenderer()` THROWS, AND A THROW IN AN EFFECT BLANKS THE WHOLE APP
**You observe:** the user says "it's not rendering". Every check is green and the page renders on your
machine.
**Actually:** three.js does not return null when it cannot get a WebGL context, it throws. From inside
a `useEffect` with no error boundary above it, React unmounts the entire tree. MEASURED with
`--disable-webgl`: `#root` went from 1 child to 0. A background animation took the agent, the map, the
panels and the report with it.
**Two fixes and the second is the general one:** guard the construction, and put an ERROR BOUNDARY
around anything decorative. `components/IntroBoundary.tsx` is that boundary; a class, because error
boundaries are still the one thing React has no hook for. ⚠ Boundaries catch render and lifecycle
errors only, never a throw inside a timer, a promise or an event handler.
🔴 **AND THE REASON NO CHECK SAW IT: every browser check here passes
`--enable-unsafe-swiftshader --use-gl=angle`, because MapLibre needs a rasteriser.** A harness that
always supplies the thing under test cannot see its absence. `verify_intro.py` section 13b now takes it
away on purpose.
**The habit:** when a report is "it does not render" and your own load is clean, the difference is in
the ENVIRONMENT, not the code path. Load it four ways with an error trap attached (built bundle, the
deployed layout through the real server, the dev server, and then with a capability removed) rather
than reasoning about which line is wrong.

### 5b.23 A PROBE THAT REPORTS ONLY WHAT IT FOUND LETS ITS OWN CHECKS DISAPPEAR
**You observe:** a verifier exits 0 with nothing red, and its total has quietly fallen. 208 checks
became 204.
**Actually:** the probe built its result with `if (el) { o[k] = ... }` and the Python side looped over
`result.items()`. A selector that stopped matching therefore wrote no entry, and the assertions for
that target REMOVED THEMSELVES rather than failing. In this instance the headline's four paragraphs
became list items, `timeline.ts:SEL.prose` still said `> p`, and the four lines silently dropped out
of the hero reveal with no symptom other than four fewer checks.
**This is gotcha #74 in a new costume: a check that does not run reports success.** The 2,215-style
dynamic totals this project prints are what makes it survivable at all; a fixed count would have said
nothing.
**The rule: never loop over what a probe FOUND, loop over what you REQUIRE.** Name the targets on the
asserting side, have the probe report `{found: false}` for a miss, and fail on it by name.
⚠ And a corollary for the probe: writing a key only on success is the same mistake one level down.
Always write the key.

### 5b.22 `serve_app.py --hold` DELAYS DOMContentLoaded, SO A PROBE HUNG OFF IT NEVER REPORTS
**You observe:** a browser probe publishes nothing at all. No steps, no error, no partial log, and the
harness can only say "the probe never ran".
**Actually:** `--hold N` keeps one subresource pending for N seconds, which is exactly how a real-clock
check buys wall-clock time. It also holds DOMContentLoaded back past the hold, so a listener on that
event fires AFTER `--dump-dom` has already captured the page. The probe was fine; it was scheduled
after the only moment anyone would look.
**The fix:** poll for the element the scenario actually needs rather than waiting for a lifecycle
event. `verify_launch.py` polls every 100 ms for an ENABLED `.shiny-cta`, which is both earlier and
more precise, because what the scenario needs is a clickable button rather than a parsed document.
⚠ **AND POLL FOR THE ENABLED STATE, NOT THE PRESENCE.** A disabled button silently ignores `.click()`.
The first version clicked into the void while the CTA was still waiting for its audio to preload, and
every downstream assertion failed in a way that looked like a broken product.

### 5b.21 A BACKTICK IN A GLSL COMMENT CLOSES THE TEMPLATE LITERAL THE SHADER LIVES IN
**You observe:** TypeScript reports `TS1005: ',' expected` at half a dozen lines scattered through a
file, none of them where you were working, and the last one is the closing brace of a function that is
plainly balanced.
**Actually:** the shader is a template literal, and a comment inside the GLSL that quotes an identifier
in backticks ends the string there. Everything after it is parsed as TypeScript, which is why the errors
land in code that was never touched and why not one of them mentions a backtick.
**Hit twice in one session**, on `` `HeatGlobe.tsx` `` and `` `uHug` ``, both in explanatory comments
written in this codebase's usual style, which quotes identifiers that way everywhere else.
**The habit:** inside a shader body, never quote an identifier. **The check:** a file's backtick count
must be EVEN; an odd count means a literal is unterminated.
⚠ And the second one broke the build, which matters because `tools/build_app.py` prints
"vite build failed, exit 1. Nothing was copied" and the screenshot taken afterwards was of the OLD
bundle, with figures that looked entirely plausible. Read that line. It is the same lesson as the
identical-PNG-byte-size tell, from the other side.

### 5b.20 A `[role=...]` SKIN THAT SETS `background` AS A SHORTHAND DELETES A COMPONENT'S ENTIRE FILL
**You observe:** a self-contained component renders as a flat translucent wash with an outline. Its own
stylesheet is present, correct, and demonstrably loaded.
**Actually:** `tones.css` carried `[role='dialog'] button { background: color-mix(...) !important; }`,
written for one Close button. `background` is a SHORTHAND, so with `!important` it does not tint what is
underneath, it resets every `background-*` longhand. A component painting
`linear-gradient(...) padding-box, conic-gradient(...) border-box` therefore came back with
`background-image: none`.
**The tell:** read the computed `backgroundImage`, not the computed `backgroundColor`. `none` on an
element whose stylesheet clearly sets a gradient means something replaced the shorthand.
**Fix it at the rule that is wrong**, with `:not(.the-component)`, rather than answering it with a
louder rule elsewhere: one selector needs one owner in one file (5b.1's cousin, and the same lesson the
`!important` war in the dropdown taught).
⚠ This is the THIRD instance of the project-wide `[role=...]` skin capturing a later element. The gate
itself hit it, `lastmile.css` hit it for prose, and now a button. **Any element that takes a role this
project skins inherits that skin, whatever it was written for.**

🔴 AND IT IS ALSO A PRODUCT RISK, NOT ONLY A HARNESS ONE. Every from-state is written by GSAP,
`opacity: 0` included -- correct, because a stylesheet would leave the page blank whenever the
animation is off. But it means visibility depends on a timeline completing. `intro/timeline.ts` carries
a plain `setTimeout` watchdog that jumps the timeline to its end if it has not got there, so a stalled
or throttled ticker leaves a FINISHED page rather than an invisible one.

### 5b.14 AN SVG SCALE NEEDS `svgOrigin`. CSS `transform-origin` is inert and `transformOrigin` is not enough
Three attempts, and only the third was right:
1. `transform-origin: center` in CSS -- **inert**. GSAP bakes an SVG element's origin into the matrix it
   writes and sets `transform-origin: 0px 0px` inline while doing it. MEASURED: the CSS rule computed
   to `0px 0px`.
2. `transformOrigin: 'center'` in the tween -- **did not fix it**. The worst halo-to-disc offset stayed
   at **8.62px** across 995 samples, and it was worst at the node NEAREST the origin, so the
   displacement was not the `cx * (scale - 1)` I had assumed.
3. `svgOrigin: '<x> <y>'` in USER UNITS -- correct. 8.62px became **0px** across 915 samples.

Why 'center' was wrong: a `<g>`'s bounding box includes the label text BELOW the disc, so its centre is
not the disc's centre. The geometry is exported from `Pipeline.tsx` and named explicitly.
The symptom was a ghost circle a hundred pixels from its node, and it was found **in a screenshot, not
by a check**. `verify_intro.py` now samples halo-versus-disc alignment continuously.

### 5b.15 AN ANIMATION PUSHED INTO THE ARRAY ITS OWN CALLBACK PAUSES CAN NEVER REVERSE
The scroll handoff's `onUpdate` pauses the ambient loops once the fade passes 90 %, so nothing keeps
tweening behind an invisible diagram. Both handoff tweens were in that same array. Past 90 % they
**paused themselves**, froze, and could never reverse. MEASURED on a real clock: correct to 0 at
scrollY 360, back UP to 0.060 at 480, and stuck at 0 after returning to the top -- a reader who
scrolled down and up was left on a landing page with no background at all.
Two arrays now: `loops` is ambient motion nobody is looking at, and is pausable. `handoff` is driven by
the reader's own scroll and never is.
🔴 THE CHECK IS THE LESSON. Sampling only downwards passed. Any reversible animation has to be swept
BOTH WAYS, and the same scroll position must give the same value in each direction.

### 5b.16 PASTED COMPONENTS CARRY THEIR FRAMEWORK'S ASSUMPTIONS
A supplied component used `<style jsx>`, which is styled-jsx, which is Next.js. This project is Vite +
React 19 and has neither. Left as pasted, React 19 renders a `<style>` element with an invalid `jsx`
attribute: it warns, and then injects every rule **globally unscoped**, including four `@property`
registrations and keyframes named `shimmer` and `breathe`. That is worse than not working, because it
half-works and the failure is a name collision months later.
The same paste also carried `@import url("https://fonts.googleapis.com/...Inter...")`. Inter is
self-hosted here and preloaded, and offline operation is a standing requirement.
CHECK BEFORE PASTING: `next` and `styled-jsx` in package.json, `"use client"` (inert in Vite, keep it
for portability), any `@import` over the network, and `next/image` or `next/font`.

### 5b.17 `--fg-bright` FAILS AA ON NEAR-WHITE. CHECKING ONE PALETTE IS CHECKING HALF THE PRODUCT
`--fg-bright` is `#14a1e0` in dark, which is 6.83:1 on the near-black page, and `#0d7fb4` in light,
which is **4.27:1** on `#fafafa` -- under the 4.5:1 floor for small text. It has now been hit three
times: the gate's eyebrow, the agent loop's data labels, and the splash's timestamps.
The answer each time is `--fg-deep`, the wordmark's darker half, `#12558f` in light, **7.39:1**. An
existing token, same hue family, no literal, no palette value touched.
TWO GENERAL RULES FROM IT:
* any small text painted `--fg-bright` needs a light-theme override;
* **opacity on text is the other repeat offender.** `opacity: 0.72` on `--text-secondary` measures
  ~2.4:1 dark and ~2.1:1 light. It looks like "slightly quieter" and is arithmetically "less
  legible". If a line must recede, use a quieter COLOUR that has been measured.

### 5b.18 A GRADIENT FILL IS INVISIBLE TO `background-color`, so a contrast probe will lie
The contrast helper walks up for the first opaque `background-color`. A button whose fill is
`linear-gradient(var(--x), var(--x)) padding-box` has a TRANSPARENT background-color, so the walk went
past it to the page and measured white text on a near-white page: **1.10:1** reported for a control
that actually renders 15.56:1. The fix is to measure against the colour the gradient is made of, which
the component declares as a custom property.
Related: a `color-mix()` computes to `oklab(...)`, which the same regex cannot parse -- and the row
silently VANISHED from the results while every check still said PASS. An unreadable colour must be
reported as a failure, never dropped.

### 5b.19 A PUBLISHED FIGURE CAN HAVE A THIRD COPY THAT NOTHING CHECKS
`audit.py`'s spend section registers **API-USAGE.md and CONTEXT/HANDOFF.md**, and
`testing/bump_spend_docs.py` writes those same two. `README.md:603` carries a THIRD copy, and it says
**"13 calls, 54,860 credits, 2.74 %"** against a true 281 calls / 1,167,340 / 58.37 %. It is internally
consistent (13 x 4,220 = 54,860) because it was right when 13 calls had been made, and it has never
been updated because nothing looks at it.
The sentence even claims provenance -- "derived from the credit meter rather than asserted" -- for a
number that has drifted from the meter by a factor of 21, in the one document a judge reads.
WHEN A FIGURE IS PUBLISHED IN TWO PLACES, GREP FOR A THIRD.

### 5b.10 `exit=$?` AFTER A PIPELINE READS THE PIPE'S LAST COMMAND, not the test
Three verifiers were reported as passing on the strength of this loop:

    python testing/$t.py 2>&1 | tail -6
    echo "exit=$?"

`$?` there is `tail`'s status, and `tail` always succeeds. One of the three had actually FAILED with
a JavaScript ReferenceError that stalled the whole flow at step 1, and the word PASS never appeared
in its output -- only the absence of a failure line, which reads the same as success when skimming.
Run the test, capture the code, THEN look at the output:

    python testing/$t.py > log 2>&1; echo "exit=$?"

The same shape hides in `grep`-filtered summaries: a pattern that matches nothing prints nothing, and
nothing looks like a clean run.

### 5b.11 A LIFTED STRING IS NOT A LIFTED FUNCTION
`tools/mkresults.py` walks reachability from `ENTRY` by matching CALLS, `name(`. An event handler is
never called; it is ASSIGNED (`lsb.onclick = stopLive`). So `stopLive` was skipped while the string
`"api/live/stop/"` was lifted anyway, inside `runLive` -- and the bundle threw "stopLive is not
defined" from `buildControls`. `runLive` is in `ENTRY` for exactly this reason; every new handler
needs adding there too.
A check for the ROUTE passed while the FUNCTION was missing. When a verifier asserts a lifted string,
assert the definition as well: `"function stopLive" in engine.mjs`.

### 5b.9 INSTRUMENT THE BROWSER, do not reason about who scrolled
"Changing the site jumps to the top, and it alternates" was three plausible theories deep (layout
shift from a toggling note, a focus change, the map camera) before anything was measured. Patching
`window.scrollTo`, `scrollBy`, `scrollIntoView` and `focus` to record a stack trace answered it in one
run: `at Module.ad [as setStage]`, from `engine.mjs:138`.
`scratchpad/scrollprobe.py` is the pattern. A scroll, a focus or a re-render has a caller, and the
caller can be asked directly instead of inferred from the symptom.

### 5b.7 THE HARNESS MUST REPRODUCE PRODUCTION, or it certifies a server nobody runs
`testing/serve_app.py` serves the app at `/app/` and, for any path under it, tries the bundle **and
then falls back to `demo/`**. Its own comment explains why: "the app's own assets and the artefacts
live in different places". Production's `serve_live.py` had no such fallback.

`results/engine.mjs` is lifted byte for byte from `demo/index.html`, which is served FROM `demo/`, so
`loadSite()` fetches every artefact by the BARE name in `sites.json`'s `artefacts` map. At `/app/` a
browser resolves those one level too low. Every fetch 404d, `loadSite` returned false, and the deployed
app reported **"No built artefacts for ashburn"** for every site while the Configure button did nothing,
because the transition it starts rejected. The browser flow check passed throughout, on a server whose
routing production did not share.

**The rule: a harness that differs from production in ANY routing behaviour is testing a server nobody
runs.** Either drive the real server, or assert the behaviour the harness adds is also in production.
Step 33 now fetches every artefact name from `sites.json` through `serve_live.py` at `/app/`.

**And when you add a fallback, test what it opens.** The fix rewrites `/app/<name>` to `/<name>`, so
the obvious question is whether `..` climbs to the repository root where `.env` lives. It cannot,
because both candidates go through `translate_path`, but that is now five asserted traversal attempts
rather than a claim in a comment.

Related: 5b.6 was the same shape one layer out. Both are "the check passed and the user saw it fail".

### 5b.6 A CURRENCY check cannot see a ROUTING mistake: verify WHICH PAGE, not just which bytes
`verify_shipped_app_is_current.py` proved the React bundle was built from the committed source, and it
was right. The deployed site still showed the old interface, because `serve_live.py`'s static root is
`demo/` and `/` therefore served `demo/index.html` while the bundle sat at `/app/`. Every check green,
wrong page, and the user found it rather than the suite.

Two habits follow.

**Assert on the URL a visitor actually opens.** "The bundle is current" and "the bundle is what `/`
returns" are different claims, and only the second is what the user is looking at. A probe of the root
that greps for a React marker (`id="root"`) would have caught this in one request.

**When a check passes and the user still sees the old thing, suspect the layer the check does not
cover.** I spent the preceding effort on intermittent `no-server` 404s, which were real but were not
the complaint. I never checked what the SUCCEEDING requests returned.

Related to 5b.2: assert on the output. Here the output was not the file, it was the response.

---

## 6. Documentation traps

### 6.1 A figure in prose is a figure nothing re-reads
This is the defect the whole verification layer exists to prevent. `audit.py` re-reads every headline
figure quoted in `README.md`, `PLAN.md`, `HANDOFF.md` and `API-USAGE.md` from the JSON that produced
it. If you publish a number, expect to be asked which file it came from.

### 6.2 Changing a count means changing every place that states it
`run_all.py`'s step count is stated in `README.md`. The palette pair count is stated in
`demo/README.md`. `CONTEXT/01-STATE.md`'s figures are generated by `sync_context.py` precisely so
that this class of drift cannot happen there.

### 6.3 No em dashes in copy
A standing instruction from the user. See `04-STANDING-RULES`. Pre-existing prose written by the user
is left alone; anything written for them must not contain one.
