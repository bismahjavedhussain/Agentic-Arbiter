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
