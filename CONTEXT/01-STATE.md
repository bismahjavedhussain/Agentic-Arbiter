<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 01 - State

What is true **right now**. The figures below are generated from the shipped artefacts; the prose is
maintained by hand. Newest change first, always.

---

## 0. Resume here

**This is the first thing to read after a restart or a compaction.** Maintained by hand; it is the
only section describing work IN FLIGHT rather than work finished.

### THE CINEMATIC BLUE SHELL, THE ONE-ROW AGENT CONSOLE, AND WHAT IS STILL OUTSTANDING. 2026-08-29

**21st.dev MCP, used and exhausted.** `search` (free) several times, `get_usage`, and the one remaining
`get_component` retrieval spent on **#12363 `thinking-tool`** by serafimcloud, whose shimmer is the
basis of the console: an animated linear-gradient painted through the glyphs with
`background-clip: text`. Its `@tabler/icons-react` dependency was dropped for lucide, already present,
and its neutral greys repointed at the brand ramp. `mcp__21st__generate` returned
`locked: generation_limit_reached` on this free account, so the layout is hand-built from the search
results rather than generated.

**`AgentConsole.tsx`: the agent as one row.** Spinner, one shimmering line of short reasoning that
cycles, seven stage ticks, and a bright-blue **Download PDF** that springs in the moment the tape
finishes. The expanded sixteen-line tape is folded away by CSS and reopenable behind "Full trace".

🔴 **EVERY REASONING PHRASE IS FIXED AND CONTAINS NO DIGIT.** The stage is READ from the engine's tape,
so the progress is real; the wording is decoration over a real signal. Paraphrasing the tape's numbers
would be inventing figures with no artefact behind them. `ticker.json` makes the same promise about its
own templates. The **PDF is resolved from `currentSite().artefacts.report`**, never constructed, and the
button is not rendered when the manifest names none.

**The repeated heading is fixed, and it was a specificity bug of mine.** `workspace.css` already said
`.secgroup { display: none }` and it did nothing: engine.css declares `.secgroup{display:block}` and
Vite emitted that declaration AFTER ours, so equal specificity meant the later one won. Confirmed by
reading the deployed stylesheet. `.viz-root .secgroup` is (0,2,0) against (0,1,0), so order stops
mattering. The page carries the eyebrow "The decision, and what it is worth" **twice**, which is what
put it on screen twice.

🔴 **PRESELECTED IS NOT THE SAME AS FILTERED, and conflating them broke a real check.** Defaulting
`filters.facility` to `metro_ashburn` also filtered the map to that one key, so the footprint collapsed
from 637 dots to 1 and `verify_app_deterministic.py` failed, correctly: it loads `/app/?probe=1` and
asserts 637 dots and 246 halos. The default now drives the **search bar and the Configure panel**,
which is what was asked, while the **map keeps showing everything** until the reader touches something.
`pristine` is that distinction and any interaction clears it. `ashburn` is confirmed as the site whose
committed pair is Amazon Web Services IAD116 to IAD117.

**FortyGuard banner:** the wordmark ships as `demo/fortyguard-logo.png` (RGBA, 33,778 B, so opacity
alone is enough), muted at 0.34, spanning the top, `pointer-events: none`, fetched through `ART`.

⚠ **THREE PARTS OF THE BRIEF ARE NOT FULLY DELIVERED, stated rather than implied.**

1. **The charts are not blue yet.** The series ramp is `--series-1` (blue) and `--series-2` (orange),
   both among the canonical 20 that `verify_palette.py` requires the app and the page to AGREE on, and
   both read at runtime by the canvas renderers. Turning the orange into a second blue means editing
   the palette in `demo/index.html`, re-lifting `engine.css` through `tools/mkview.py`, and mirroring
   the values in the app. That is a coordinated change across the audited page, not a CSS tweak.
   The **shell** is blue via new `--fg-*` tokens that collide with nothing.
2. **True zero-scroll is not achievable while the panels are the deliverable.** One tab holds up to
   four engine panels, each with a chart and a table. What ships is an app-like frame: banner, rail,
   header and console are fixed, and the panel column is the only scroll region.
3. **The filters and metric cards are not yet consolidated into one widget grid.** They still live on
   the pick screen as the brief for that screen specified.

Verified: palette 38/0, flow 24 of 24, view-matches-page 0, shipped-current 0, deployed-root 0,
**app-deterministic 0**, `audit.py` **2,216 passed 0 failures**. Figures unchanged.

### shadcn IS INSTALLED, AND ITS INIT BROKE THREE THINGS QUIETLY. 2026-08-29

At the user's direction: `npx shadcn init -b radix -p nova`, the `@efferd` registry added to
`components.json`, then `npx shadcn add @efferd/dashboard-4`. 37 files arrived. **The generator also
made three changes nobody asked for, and every one of them was a visible regression.**

**1. It overwrote two palette values in place.** `--border` went `#27272a` to `oklch(0.922 0 0)` and
`--muted` went `#8d8d96` to `oklch(0.97 0 0)`, both near-white, so **every border and muted label in
the dark theme would have rendered near-white on `#09090b`**. `verify_palette.py` caught it and named
it: 18 of its canonical 20 tokens in common for dark against 20 for light. Restored, below shadcn's
own declarations so a re-init is overridden rather than merged.

**2. Its base layer applies `bg-background text-foreground` to `<body>`, and its `--background` is
`oklch(1 0 0)`: pure WHITE.** Installing one component would have turned the whole dark dashboard
white. Fixed by **aliasing shadcn's tokens to this app's** rather than deleting the `@apply`:
`--background: var(--page)`, `--foreground: var(--text-primary)`, `--card: var(--surface-1)` and five
more. Deleting the rule would have fixed the body and left every registry component off-palette;
aliasing fixes both, so anything added later is on-palette by construction.
⚠ `--muted` is deliberately NOT aliased: this app means muted TEXT by it, shadcn means a muted
SURFACE. One name, two meanings, and the app's wins.

**3. It changed the typeface of the whole app.** It appended `@apply font-sans` to the `html` rule
**after** the existing `font-family: "Inter", ...`, with `--font-sans: 'Geist Variable'`. Later
declaration wins, so everything silently became Geist, and five Geist woff2 files (76 KB) shipped
beside the Inter `index.html` already preloads for the render gate. Fixed by pointing `--font-sans` at
Inter, which also puts every shadcn component on the right face, and removing the font import.

**🔴 THE BLOCK'S DATA WAS DELETED, NOT ADAPTED.** `@efferd/dashboard-4` is an e-commerce dashboard and
its cards carry invented figures: `revenue-chart-data.ts` alone held **275 numeric literals and 91
e-commerce strings**, plus `stats.tsx` and three chart components. 16 files removed. A figure with no
artefact behind it is the one thing this project does not ship, and the user's instruction was explicit
that the values are the agent's and must not change.

**What was kept:** the 17 `ui/` primitives, `delta.tsx`, `formater.ts`, `use-mobile.ts`, and the
block's **layout language**, which is what the request was actually about. The rail is now grouped
under eyebrow headings (Setup / The run / What it found) with lucide icons and a spring-driven active
pill, plus a **Quick actions** card of icon, title, one-line subtitle and chevron.

**🔴 THE QUICK ACTIONS ARE REMOTE CONTROLS, NOT A SECOND IMPLEMENTATION.** Each row reads a real
engine button by id and forwards the click: `#runagent`, `#livego`, `#backtopick`. It mirrors that
button's `disabled` state through a `MutationObserver`, and a row whose button does not exist yet
renders nothing. `wire()` inside the byte-identical engine is still the only thing that runs the agent.

**The panel entrance is transform and opacity ONLY, never layout.** A scaling or reflowing animation
would race the canvas redraw: `EngineStage` redraws on the frame after `data-aa-active` commits, and a
transform does not change `offsetWidth`, so the width the engine measures is the settled one. Honoured
`prefers-reduced-motion` throughout.

**Bundle cost, measured:** js 1,466,326 to 1,471,611 (**+0.4 %**, framer-motion and the icons); css
144,999 to 208,801 (**+44 %, +63.8 KB**) because `index.css` now `@import`s `shadcn/tailwind.css`
unconditionally. The 17 unused primitives are tree-shaken out of the js. Per fresh visit that moves
2.90 MB to about 2.97 MB, so roughly 1,030 journeys before the 5 GiB cap instead of 1,051.

Verified after: palette 38 checks 0 failed, flow **24 of 24**, `verify_view_matches_page` 0,
`verify_shipped_app_is_current` 0, `verify_deployed_root_is_the_app` 0, `verify_app_deterministic` 0,
`audit.py` **2,216 passed 0 failures**. Every figure unchanged: 10.7 %, +406 h/yr, 65.6 %, 43,763 h.

⚠ An `@/*` alias was added to `tsconfig.json` and `vite.config.ts` because the shadcn CLI refuses to
init without one. No hand-written import uses it; the existing relative imports are untouched.

### THE RESULTS STAGE IS NOW A SIX-TAB WORKSPACE, and the panels were not rewritten

Built 2026-08-28 at the user's direction: a hierarchical workspace with a sidebar rail, a widget grid,
glassmorphism, framer-motion transitions and a console-style component for the seven agent stages.

**THE ONE DECISION EVERYTHING ELSE FOLLOWS: the panels are rearranged, never retyped.** The thirteen
results cards keep their ids, their markup and their renderers. `results/engine.mjs` stays
byte-identical to `demo/index.html` (step 30), the markup string stays hash-identical (step 31), and
`audit.py`'s 2,216 checks still measure the page they always measured. `lib/tabs.ts` stamps
`data-aa-tab` on each panel and `workspace.css` decides which are on screen. **No node is moved.**

| tab | panels |
|---|---|
| Configuration & Setup | `[data-show="configure"]`, plus the `.sidebar` holding `#filters` |
| Live Agent Execution | `#tapecard`, `#livecard` |
| Hourly Schedule & Reasoning | `#decisioncard`, `#whycard` |
| Economic Impact | `#headcard`, `#laddercard`, `#moneycard` |
| Plume & Geometry Analysis | `#fieldcard`, `#sitecard`, `#plumecard`, `#dialcard` |
| Model Calibration | `#scorecard`, `#cfcard` |

**TWO OWNERS OF VISIBILITY, DELIBERATELY, BECAUSE THEY OWN DIFFERENT FACTS.** `setStage()` owns "is
this panel's STAGE current" through the `hidden` attribute; the tab rules own "is this panel's TAB
current" through `display`. A panel needs both. Neither reads or clears the other, so `#livecard`
remains governed by the stage machine exactly as standing rule C1 requires. That is not the
two-writers bug the page documents: that bug is two pieces of code setting the SAME property.

**🔴 THE PAGE EXPLICITLY WARNS AGAINST TABS, AND ONE HALF OF THE WARNING IS REAL.**
`demo/index.html` says `IT IS NOT A TAB BAR, AND IT MUST NOT BECOME ONE`, for two reasons.
- The `verify_site_panels.py` half does **not** apply: that check reads `demo/index.html` directly
  (its line 290) and never sees this app. The page is unchanged.
- The canvas half is entirely real: *"a canvas whose parent has no width never draws"*. The engine
  sizes each canvas from its parent's measured width, so a panel that was `display:none` when
  `drawAll()` last ran holds a zero-width canvas that painted nothing. **Every tab activation now
  redraws on the next frame**, in `EngineStage.tsx`, after the attribute is committed and the panel
  has been laid out. Without that, switching tabs reveals a permanently blank chart.

**THE FIVE DELETIONS the user asked for are all in `Masthead.tsx`**, so React-owned and safe. They are
hidden by one CSS rule on `body[data-stage]`, the attribute `setStage()` already publishes, so the
prose stays on the pick screen and is gone from configure and results with **no new owner of anything**.
⚠ The class stops short of the "LIVE agent is also attached" line, which C1 keeps on every stage.

**🔴 A BUG WORTH KEEPING, because it reads as a standing-rule violation.** The first tab map claimed
`#filters` and, since `#filters` has no frame of its own, walked up with
`closest('details, .card, [data-show]')`. That landed on a `<details>` spanning
`demo/index.html` 1754 to 6970, which **encloses all thirteen cards**. Every card then reported hidden,
`#livecard` among them, and the flow check said "the live agent card is present: FAIL". The cause was
layout, not the rule. `classifyPanels()` now **refuses to stamp any element that encloses another
tab's panel** and reports it, so this cannot recur silently.

**`verify_app_flow.py` was rewritten, not relaxed.** Asserting "all thirteen cards visible at once" is
meaningless once they are split across tabs, so the probe now **opens each tab in turn** and credits a
card only to the tab named in its own `data-aa-tab`. The union must still cover all thirteen, no
results tab may be empty, and the canvas count is the **peak across the walk**, which is what proves
the redraw fires. C1 became two assertions that each say what they mean: `#livecard` and `#livego` are
in the DOM **on every tab** (never removed), and the card is reachable in its tab.

Verified: flow check 22 of 22, `verify_view_matches_page` 0, `verify_shipped_app_is_current` 0,
`verify_deployed_root_is_the_app` 0, `verify_palette` 0, `verify_app_deterministic` 0,
`audit.py` 2,216 passed 0 failures. framer-motion 13.1.1 added.

⚠ **ONE FIGURE THE USER QUOTED DOES NOT MATCH.** They asked the plume tab to highlight "345 degrees
with a 0.3797 degC rise". Ashburn's real worst is **255 degrees at 0.3550 degC**
(`demo/rise_table_longest.json:max_rise_bearing`, `max_rise_c`); the facing mode is 235 degrees at
0.1584. 72 bearings and 576 solves are both confirmed. Nothing was hardcoded, so `#dialcard` shows
whichever is true for the loaded site; 345 is most likely the facility they had open.

### THE PINGER IS CREATED, on cron-job.org, 2026-08-28

`Agentic Arbiter keepalive` -> `https://agentic-arbiter.onrender.com/api/ping`, enabled, first
execution "Today at 10:25:00 PM" in its own timezone (Asia/Karachi). Response measured from here at
the moment of creation: **200, 12 bytes, 0.35 to 0.50 s**, well inside cron-job.org's 30-second
free-tier timeout.

⚠ **TWO SETTINGS NOT YET CONFIRMED**, because the job list shows neither: that the interval is
**every 5 minutes** rather than hourly (one "next execution" of 10:25 PM is consistent with both), and
that **Schedule expires is set to 21 September 2026**. Without the expiry, September runs 720 of the
750 workspace hours, which is 96 % and too tight. Both are visible under EDIT.

**The shape that was chosen, and why it changed twice.** First plan was a daily 08:00 to 22:00 window,
rejected because a judge arriving at 23:30 waits a minute for a cold start and reasonably concludes the
site is broken. Second was `Custom` with days 1-21,28-31 across August and September, which works but
picks up 28-30 September as a side effect (576 h, 76.8 %). Settled on **"Every 5 minutes" plus an
expiry date**, which is two controls instead of five multi-selects:

| | days running | instance hours | of 750 |
|---|---|---|---|
| August | 28 to 31, only 4 left | <= 96 | 12.8 % |
| September | 1 to 21 | 504 | 67 %, 246 h spare |

🔴 **A FIRST DRAFT OF THIS SCHEDULE WOULD NEVER HAVE FIRED IN AUGUST.** I told the user to set Months
= September while the question they had just asked was whether a judge could see the project on **31
August**. Their screenshot showed `5 * 1 9 *`, hourly on 1 September only. Read the crontab expression
and the "Next executions" panel; both state plainly what the multi-selects imply, and the panel is the
check: after the fix it must show **today's** date, not next month's.

⚠ **ISOLATED FAILURES IN HISTORY ARE EXPECTED, not a fault.** A cold start is about 60 s
(render.com/docs/free) against a 30 s free-tier request timeout, so **the ping that wakes a sleeping
instance can be logged as failed while still having done its job**; the next one 5 minutes later finds
it awake. It is **25 CONSECUTIVE** failures that auto-disable the job, and that many in a row would
mean the service is genuinely down.

### 🔴 RENDER HAS NO SPEND LIMIT, and the keep-alive must be WINDOWED not 24/7

Verified 2026-08-28 by a 26-agent research pass with a skeptic against every load-bearing claim.

**1. There is no workspace spend limit on Render.** No maximum spend, no spend cap, no field that caps
total workspace spend. The public feature request is open with a May 2025 comment saying it is not on
the roadmap. **"Set the spend limit to zero" is not an action that exists.** The only spend control in
the product caps ONE axis, build pipeline minutes: *Dashboard, workspace home, **Settings** in the left
pane, scroll to **Build Pipeline**, click **Set spend limit***. Not on the Billing page, not gated to
paid plans. ⚠ Whether that dialog accepts a literal `0` is unconfirmed, and a `0` there stops **all
builds including deploys** for the rest of the month, so you could not ship a fix.

**The real cap is having no payment method:** *"If you haven't added a payment method or you reach your
spend limit, Render instead disables all new builds."* Free instance hours behave the same way,
suspending rather than billing. ⚠ **A card IS on this workspace** (the $1 authorisation), so that
protection is not currently in force. The one genuinely billable axis is **bandwidth**, which has no
cap and bills per GB (5 GB included since the 2026-04-23 plan change, overage documented at $0.15/GB).

**2. 🔴 A 24/7 PINGER IS ARITHMETICALLY FINE AND PRACTICALLY RECKLESS.** 750 instance hours per month,
**workspace-wide**, shared by every free service, no rollover.

| plan | hours | headroom of 750 |
|---|---|---|
| awake 24/7, 31-day month | **744** | **6 h, 0.80 %** |
| awake 24/7, 30-day month | 720 | 30 h, 4.0 % |
| **awake 14 h/day, 31-day month** | **434** | **316 h, 42 %** |

On exhaustion Render **suspends every free service until the 1st of the next month**. Not slower: off,
for up to 30 days. And the docs never say whether deploys, restarts and previews count, so **744 is a
floor, not a ceiling**. The asymmetry decides it: a dead pinger costs one judge a one-minute cold
start; a dead hour budget costs the whole site for weeks.

**The interval does not change hours consumed.** Once it never sleeps it burns 744 h whether pinged
every 5 or every 14 minutes. The lever is the DAILY WINDOW, not the interval.

**DECIDED: every 5 minutes, hours 08 to 21 only.** 5 and not 10 minutes because spin-down is 15 idle
minutes, so a 5-minute interval gives 3 pings per window and survives two consecutive misses, while
10 gives 1.5 and one late ping lets it sleep. cron-job.org's own FAQ admits it may delay jobs
deliberately.

**3. cron-job.org is the pinger.** No card, 1-minute granularity, timezone selectable. ⚠ It
auto-disables a job after **more than 25 consecutive failures**, and the free tier has a 30-second
request timeout. Second choice is Cloudflare Workers Cron Triggers, which nothing disables for failing
or for inactivity. UptimeRobot is **fixed at 5 minutes always-on**, which cancels the window.

**4. 🔴 GITHUB ACTIONS CANNOT DO THIS ON A PRIVATE REPO, AT ANY INTERVAL.** Every job is rounded up to
1 minute against 2,000 included minutes, so the entire monthly quota spent on nothing but pings buys
64.5 runs a day, one every **22.3 minutes**, slower than the 15-minute spin-down. Going public makes
Actions minutes free, but `schedule` is documented as delayed and droppable, and **scheduled workflows
are disabled after 60 days of repository inactivity**. Still not the recommendation.

**5. The ping target is `/api/ping`**, now deployed, 12 bytes. Proof it cannot spend: the only call to
the paid path is `LV.live_run(...)` at `serve_live.py:354`, reachable only from `do_POST` on
`/api/live/`; `health()` was instrumented on `socket.connect`, `getaddrinfo` and `urlopen` across two
calls, cold and warm, and made **zero** outbound calls.

⚠ Separately, and it is the owner's stated decision rather than a defect: `POST /api/live/<site>` is
unauthenticated on the deployed host, so 48 calls a day at 4,220 credits is about 202,560 credits a day
available to anyone with the URL.

**Bandwidth per visitor, measured:** first load 2.90 MB, then `loadSite` fetches 7 artefacts totalling
2.20 MB, so **5.11 MB for a full journey and 1,051 journeys before the 5 GiB cap**. `scenarios.json`
is 30.2 MB but nothing fetches it: it is named in the artefacts map and `loadSite` does not read it.

### 🔴 THE DEPLOYED APP COULD NOT LOAD A SINGLE SITE, and the harness is why it shipped

**The user reported "No built artefacts for ashburn" and a Configure button that did nothing.** Both
symptoms, one cause, and the artefacts were never missing.

`results/engine.mjs` is lifted byte for byte from `demo/index.html`, which is served FROM `demo/`. So
`loadSite()` fetches every artefact by the **bare filename** in `sites.json`'s `artefacts` map:
`trace.json`, `backtest.json`, `money.json`, the plume field. The React app is served from
`demo/app/`, **one level down**, so a browser resolves those names against `/app/` and every one 404s.
Measured against the real server:

```
/app/trace.json                          404      /trace.json                          200  207,367 B
/app/backtest.json                       404      /backtest.json                       200   80,206 B
/app/money.json                          404      /money.json                          200  241,855 B
/app/plume_field_ashburn_longest.json    404      /plume_field_ashburn_longest.json     200  684,806 B
```

`loadSite` returns false on a missing trace, so **every** site reported "No built artefacts", and
Configure did nothing because `configureSite()` starts with the same failing `loadSite`. The error
names the boot site rather than the clicked one, because `bootEngine` runs once with the initial key.

**The fix is in the server, not the engine.** Step 30 asserts the engine is character for character
the page's code, and that identity is the whole reason the React rebuild is trustworthy; prefixing its
fetches would end that. So `serve_live.py` falls back from `/app/<name>` to `demo/<name>` when the
bundle does not have it. React's own code already carries `ART = '../'` for the artefacts it reads
directly; the engine cannot, so the server closes the gap.

**🔴 WHY IT SHIPPED, and this is trap 5b.7.** `testing/serve_app.py`, the server the browser flow
check drives, **already had that fallback**, with a comment explaining it. Production did not. The
flow check passed on a server whose routing production did not share. A harness that differs from
production in any routing behaviour is certifying a server nobody runs.

Step 33 now reads `sites.json` and fetches every artefact name for two sites of different shape
(`ashburn`, unprefixed; `AL_way_1540172608`, key-prefixed) through the REAL server at `/app/`, plus
five traversal attempts proving the fallback cannot climb to the repository root where `.env` lives.
19 checks, still writes nothing.

### THE HEALTH CHECK WAS THE EXPENSIVE PART, not the keep-alive ping

Found while sizing the pinger, and it inverts the intuition. `health()` calls `offerable_sites()`,
which re-parsed the 784,300-byte `sites.json` **on every call, uncached**.

**🔴 A CORRECTION TO MY OWN WORK, AND IT WAS A STANDING-RULE BREACH.** The first version of this
section and of the code comment said *"Render polls `/api/health` every 5 seconds"* with "measured"
beside it. **The 5 seconds was never measured or sourced.** render.com/docs/health-checks says only
*"Every few seconds, Render sends health checks"* and publishes no interval. The parse cost is real;
the cadence was mine. In a repo whose rule is that any number must name the file it came from, that is
exactly the failure `audit.py` exists to prevent, and it slipped because it was in a comment rather
than in published copy.

MEASURED, 40 runs on a full core, 2026-08-28: **8.40 ms** per parse, so ~84 ms on 0.1 CPU. Cached,
**0.0356 ms, 220x faster**. The cadence-dependent cost is therefore a RANGE:

| cadence | polls/day | CPU-seconds/day | share of 0.1 CPU | `/api/health` egress/month |
|---|---|---|---|---|
| every 3 s | 28,800 | 2,419 | 2.80 % | 5.46 GB, **101.8 % of the 5 GiB allowance** |
| every 10 s | 8,640 | 726 | 0.84 % | 1.64 GB, 30.5 % |
| keep-alive ping, every 600 s | 144 | 12.1 | 0.01 % | 27 MB, 0.5 % |

With the 12-byte `/api/ping` those first two egress figures become 10.5 MB and 3.2 MB.

**🔴 AND THE FLAPPING IS NOW EXPLAINED, FROM RENDER'S OWN DOCS rather than inference.**
render.com/docs/health-checks: *"If a running service instance fails consecutive health checks for 15
seconds, Render temporarily stops routing traffic to it"*, and at 60 seconds it *"automatically
restarts the instance"*. **Traffic stopped at the edge is precisely the `x-render-routing: no-server`
404, interleaved with 200s, that was observed on 2026-08-28** and that the page surfaced as
`SyntaxError: Unexpected token 'N'`. A health check that parses 784 KB on a tenth of a CPU while a
visitor pulls a 2.9 MB page through the same tenth is a credible way to miss 15 seconds of checks. The
cache and the 12-byte endpoint address the cause; whether they fully fix it needs observation.

⚠ **NOT DOCUMENTED EITHER WAY:** whether Render's own health checks count as the "inbound traffic"
that defers spin-down. render.com/docs/free defines spin-down as 15 minutes *"without receiving any
inbound traffic ... both HTTP requests and WebSocket messages"* and says nothing about internal
checks. Inference, not fact: if they counted, no free service with a health check path would ever
spin down, which would void a documented behaviour, so they almost certainly do not. **My attempt to
settle this empirically failed** and is worth recording as a method note: a 17-minute quiet window was
broken by the user loading the page inside it and by my own deploy polling, so its "never slept"
result proves nothing. A test that needs the absence of traffic cannot be run against a host somebody
else is using.

**Now cached on the file's mtime**, not a TTL: `build_sites.py` rewriting `sites.json` moves the mtime,
so a stale answer cannot outlive the file that produced it. **7.836 ms to 0.0356 ms, 220x.** The cache
is one `(mtime, keys)` tuple rebound in a single store, because `ThreadingHTTPServer` serves on many
threads and two separate stores would let a reader see the new mtime beside the old keys.

Verified five ways: identical output on 250 keys, a caller mutating the returned list cannot poison the
cache, 220x faster, it does invalidate when the file changes (tested against a temp copy so the real
artefact is never touched), and a missing file returns `[]` rather than a stale answer.

### `/api/ping`, and the HEAD trap that would have made a pinger report an outage

Two changes so the keep-alive ping is cheap and actually works.

**`/api/ping` returns 12 bytes, `{"ok": true}`, and does no work at all.** No `reload_if_stale`, no
`offerable_sites`, no key read. Point Render's Health Check Path and the external pinger here, not at
`/api/health`. The bandwidth arithmetic, if Render really polls every 5 seconds:

| polled endpoint | bytes | per month at one poll / 5 s | share of the 5 GiB free allowance |
|---|---|---|---|
| `/api/health` | 6,233 | 3.28 GB | **61 %** |
| `/api/ping` | 12 | 7.9 MB | 0.15 % |

A 10-minute pinger on `/api/ping` costs 0.07 MB a month. ⚠ Whether Render's own health checks count
against billed bandwidth is NOT confirmed, and neither is the 5-second cadence: both are inferred.
The endpoint is worth having either way, and it removes the question.

**🔴 HEAD ANSWERED 404 ON EVERY `/api/*` PATH.** `SimpleHTTPRequestHandler` implements `do_HEAD` for
FILES only, so `HEAD /api/health` returned 404 while `GET /api/health` returned 200. Measured
2026-08-28. Uptime monitors commonly send HEAD, and **a pinger that gets a 404 is worse than no
pinger**: the instance still falls asleep, and the monitoring service also starts emailing that the
site is down. `do_HEAD` now answers `/api/ping` and `/api/health` with 200 and no body, keeps a clean
404 for unknown `/api/*` so a mistyped ping URL cannot look healthy, and shares `_root_redirect()`
with `do_GET` so both verbs route identically.

Guard extended: `run_all.py` step 33 now checks all of that, 16 checks, and still writes nothing.

### 🔴 THE DEPLOYED SITE WAS SERVING THE OLD SINGLE-FILE PAGE, and the user caught it

**The user opened `agentic-arbiter.onrender.com` and saw the PREVIOUS interface.** They were right,
and I was diagnosing the wrong thing at the time: I had spent the preceding effort on intermittent
`x-render-routing: no-server` 404s and had not checked WHICH PAGE the working requests returned.

The cause, one line. `serve_live.py` sets the static root to `demo/`:

```python
super().__init__(*a, directory=DEMO, **kw)      # line 344
```

So `/` served `demo/index.html`, the single-file page. The React bundle is `demo/app/index.html` and
was only ever reachable at `/app/`. Build fine, bundle current, key present, deploy green, wrong page.

**The fix is a 302 from `/` to `/app/`**, added in `do_GET` after the `/api/` branches. A redirect and
NOT serving `demo/app/index.html` at `/`, because the bundle's references are relative:
`./assets/index-*.js` and `../fonts/inter-latin.woff2`. At `/` those resolve to `/assets/` and to a
parent of the root, neither of which exists. At `/app/` they resolve correctly and the app's own
`ART = '../'` fetches land on `demo/*.json`. **The `/app/` depth is load-bearing.**

`demo/index.html` is NOT hidden. It stays at `/index.html`, which is what the verification layer
measures and what `CLAUDE.md` calls canonical.

Verified locally on port 8099, no artefact written:

| path | result |
|---|---|
| `/` | 302 to `/app/`, one `Cache-Control` header |
| `/app/` | React bundle, 3 markers (`id="root"`, js, css) |
| `/app/assets/index-CU1B4VOs.js` | 200, 1,332,270 B |
| `/app/assets/index-DXWxYH6S.css` | 200, 139,341 B |
| `/fonts/inter-latin.woff2` | 200, 48,256 B |
| `/sites.json` | 200, 784,300 B |
| `/index.html` | 200, 491,456 B, `#livego` and `#livecard` both present |

`verify_shipped_app_is_current.py` exits 0, hash `b3378b7b3319f500`, so the bundle the redirect points
at is built from the committed source.

**THE LESSON, and it generalises.** `verify_shipped_app_is_current.py` answers "is the bundle
current?" Nothing answered "is the bundle the thing a visitor reaches?" A currency check one layer in
cannot see a routing mistake one layer out. When a check passes and the user still sees the old thing,
suspect the layer the check does not cover.

### PUSHED, and the Render free-tier limits that actually matter, verified

**The repository is on GitHub: `github.com/bismahjavedhussain/Agentic-Arbiter`, branch `master`.**
4,930 files, 943 MB, 85 commits. Local and remote HEAD agree at `3ac39b6`. The GitHub API returns 404
without credentials, which is what a PRIVATE repo does, so it needs making public for judges to read it.

`scan_secrets.py` ran before the push as the gate: **CLEAN, 0 hits in 4,930 tracked files and 10,746
history blobs, 2,437 MB read.**

⚠ `http.postBuffer` was raised to 500 MB locally first. The 1 MB default makes large HTTPS pushes fail
with `RPC failed; curl 55`, and 943 MB would very likely have hit it.

🔴 A MISTAKE OF MINE WORTH KEEPING. I reported `git ls-remote origin | head -10; echo "EXIT: $?"` as
proving the repo existed and was empty. That `$?` is **head's** exit code, not git's; the probe was in
fact sitting on a credential prompt. The conclusion happened to be right and the evidence was
worthless. `${PIPESTATUS[0]}` is what reads the real exit code through a pipe, and the push used it.

### WHAT 0.1 CPU ACTUALLY COSTS, measured rather than guessed

The Render free instance is **0.1 CPU and 512 MB**. RAM was never the risk; CPU is. Measured on this
machine, then divided by 0.1:

| Work | Here | On 0.1 CPU | Verdict |
|---|---|---|---|
| One full page load, 3.2 MB | 0.09 s, 33 MB/s | about 1 s of CPU | fine, unnoticeable |
| Server memory, peak | 65.5 MB | same | 446 MB spare |
| **One LIVE run** | **12.1 s of CPU time** | **about 121 s, 2 minutes** | slow but not broken |

The live figure is the one that matters and it needed a specific measurement: **total CPU time**, not
wall clock, because 0.1 CPU rations CPU seconds. A run consumed 12.1 CPU seconds at an effective
**0.80 cores**, so it is essentially single-threaded and there is no hidden multi-core multiplier
inflating the estimate.

**IT CANNOT TIME OUT, which is the saving grace.** `POST /api/live/<site>` returns a `job_id`
immediately, the agent runs in a background `threading.Thread`, and the browser polls
`GET /api/live/job/<id>` while progress streams. So two minutes shows as a progressing card, not a dead
request. Had this been one synchronous request it would have been unusable on this tier.

Measured with `live.py run --replay <cached window>`, which does the same computation from a saved
FortyGuard response for **zero credits**.

⚠ **NO PERSISTENT DISK on the free tier**, per Render's own notice on the plan picker. `data/live_cache/`
is where a bought window is cached so it is not bought twice, and it is ephemeral here: a redeploy or a
restart loses it, so the same window can cost 4,220 credits again. Not a fault, but it is why the cache
cannot be relied on to prevent double spending in this deployment.

⚠ Also stated on that notice, and all harmless here: no SSH, no scaling, no one-off jobs.

### THE FREE-TIER NUMBERS, all workspace-wide and per month

Researched by a 9-agent workflow and then checked adversarially, which found 35 problems in the first
pass. Every number below carries a source in the workflow output.

| Limit | Value | What happens when exceeded, with no card on file |
|---|---|---|
| RAM per instance | **512 MB** | process killed, "Ran out of memory", deploy cancelled |
| Outbound bandwidth | **5 GB** | every free service suspended until the 1st |
| Build pipeline minutes | **500** | no new builds for the rest of the month, so no redeploying a fix |
| Instance hours | **750** | every free web service suspended until the 1st |

**THE RAM RISK IS CLEARED BY MEASUREMENT, not by argument.** The workflow called 512 MB "the one number
most likely to stop this outright". Measured locally, serving every path a judge's browser requests:

```
peak working set   65.5 MB
Render free limit 512.0 MB
headroom          446.5 MB
```

The server streams artefacts from disk rather than loading them, so numpy's import is most of the 63 MB.
⚠ NOT measured: a real live run, which allocates numpy arrays for a 17,862-tile field. Measuring it
costs 4,220 credits, so it was not done.

⚠ **750 HOURS LEAVES SIX HOURS OF SLACK.** Keeping one service awake through a 31-day month spends 744.
So: **only one free service in this workspace**, or the allowance is split and both get suspended.

### 🔴 GITHUB ACTIONS CANNOT BE THE KEEP-ALIVE PINGER ON A PRIVATE REPO

This is the finding that most changed the plan, and it would have failed silently. A 10-minute schedule
is 6 runs an hour, 4,320 a month, and **GitHub rounds every job up to a whole minute**, so it needs
4,320 billable minutes against the **2,000** included on GitHub Free. The pings stop dead about
**13.9 days** into each month with no alert. Only viable if the repo is public.

**So the pinger is `cron-job.org`:** no card, no repo change, no Render change, any interval from one
minute upward.

### DECIDED, SCHEDULED FOR AFTER THE PUSH: Render with a card and a zero spend limit

The user's decision on 2026-08-28, recorded because it is the next action and it involves money:
*"we will go with the first option i.e Render, card plus a zero spend limit. But for now push the
project on github first."*

**Target repo: `https://github.com/bismahjavedhussain/Agentic-Arbiter`** (branch here is `master`).

**Why a card at all, since Render's own docs say free access does not need one.** The signup asked for
it anyway, most likely because the **Blueprint** flow can create several services at once. The
documented free-tier behaviour is that payment info only matters for OVERAGES: *"If you haven't added a
payment method, Render instead suspends all of your Free services"* for bandwidth, and *"disables all
new builds"* for build minutes.

**The plan, in order, once the push is done:**
1. Render, **New > Web Service** (not Blueprint), connect the repo, pick the **Free** instance type.
2. Add the card, then set the workspace **spend limit to zero**, so overages suspend rather than bill.
3. Paste `FORTYGUARD_API_KEY` as a secret env var. The user pastes it; it never passes through me.
4. Start command is in the Dockerfile. Public URL will be `<service>.onrender.com/app/`.
5. Point a free uptime pinger at `/api/health` every 10 minutes: Render spins a free service down
   after 15 minutes idle and takes about a minute to wake, and 750 free instance hours a month covers
   one always-awake service with about six hours to spare.

⚠ COULD NOT VERIFY: the exact dashboard path for the spend limit. Render's `/docs/spend-limits` and
`/docs/billing` both return 404, and the pricing table is rendered client-side. The limit is referenced
by the free-tier doc (*"unless you've reached your spend limit"*), so it exists; the click path is not
established.

⚠ HUGGING FACE SPACES IS NOT AN ALTERNATIVE, correcting something I said earlier from memory. Their
docs: *"Gradio and **Docker Spaces** run on compute and **require a paid plan** to create"*. Koyeb's
free web tier also appears to be gone. TryCloudflare quick tunnels are genuinely card-free and
account-free, but the URL is *"randomly generated each time"* and Cloudflare calls them *"intended for
testing and development only"*, so they suit a live demo you attend, not a submission link.

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
| run_all.py steps | **35** | count of STEPS entries in src/run_all.py |
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

### 2026-08-28 - Where it deploys, decided against fetched facts rather than memory

**The user's requirement: "Deploy on a good platform where no dynamic working or live calls get
interrupted."** That single line rules out most free tiers, so the platform docs were fetched rather
than recalled.

| Platform | Verified fact | Verdict |
|---|---|---|
| Render free | "spins down a Free web service that goes 15 minutes without receiving any inbound traffic", wake "takes about one minute", 750 free instance hours per workspace per month | usable **with a keep-alive ping** |
| Hugging Face Spaces | "Gradio and **Docker Spaces** run on compute and **require a paid plan** to create" | **not an option** on a free account |
| HF free hardware | "your Space will go to sleep and stop executing after a period of time if unused" | would interrupt anyway |

**The chosen answer: Render free plus an external pinger on `/api/health` every 10 minutes.** The
arithmetic closes: a service kept awake through a 31-day month uses about 744 hours against a 750-hour
allowance. `/api/health` makes no vendor call and costs no credits, so the pinger is free in both senses.

⚠ THE MARGIN IS SIX HOURS. If they exhaust the 750, Render suspends free services until the next month.
Fine for a hackathon window; the cheapest paid instance removes the question. Render's price could not
be verified from here, the pricing table is rendered client-side, so no figure is quoted.

**Also added `.dockerignore`.** Without it the build context is about 1.6 GB: `.git` alone is 479 MB and
`node_modules` 138 MB. It also excludes `.env` explicitly, because a LOCAL `docker build` runs against
the working tree where that file does exist, unlike a git clone.

**THE KEY NEVER PASSES THROUGH ME.** `render.yaml` declares `FORTYGUARD_API_KEY` with `sync: false`, so
Render prompts for it and stores it encrypted. The user pastes it. A key that passes through a chat
transcript is a leaked key, and there is no version of this task that requires me to see it.

### 2026-08-28 - The README lost its em dashes, and the ranges kept theirs

66 em dashes removed from README, the one document judges read. The rule: a dash followed by a
conjunction or pronoun is joining clauses, so a comma; anything else introduces an expansion, so a
colon. Two comma splices the rule could not see were fixed by hand, and one case where a blockquote
marker sat between the dash and the word after it, so the rule read ">" instead of "so".

🔴 EIGHT EN DASHES STAY, AND audit.py IS THE REASON. Replacing them with "to" broke check 10
immediately: `audit.py` FORMATS published figures as `"**%d–%d MW**"` and `"$%s – $%s per year"`, so the
range separator is part of a published figure, not prose. Changing it means changing the formatter in
audit.py, the page, and the React app together, and regenerating everything, to gain a typographic
nicety on a numeric range. Reverted rather than pushed through, and the seven ranges plus one
`advection–diffusion` are what remain. **Left as an open question for the user rather than decided
quietly.**

### 2026-08-28 - The deployment, and a correction: the SERVER does need part of data/

**One service, decided by the user: "I only want one deployment which supports the new UI and a live
agent working on the deployed project."** `serve_live.py` already serves the artefact folder statically
AND answers `/api/*`, so one process is the whole deployment and no code was needed to support it. Both
front ends call the agent with a relative url, `fetch('api/live/<site>')`, so a split origin would have
meant inventing a configurable API base plus CORS, which is two new ways for live to break.

```
python AGENTIC-ARBITER/src/serve_live.py --allow-paid --host 0.0.0.0 --port $PORT --max-live-calls 48
    /app/              the React interface
    /                  the single-file page
    /api/live/<site>   a live run
```

New at the repo root: `Dockerfile`, `render.yaml`, `requirements.txt`, and a *Deploying it* section in
README. `requirements.txt` is **derived**: the import graph from `serve_live.py` was walked, 12 modules,
and only `numpy` and `psychrolib` are third party. `physics` looks like a third and is not, it is a
local package at `src/physics/`, which a first pass missed by looking for `physics.py` rather than
`physics/`. **No GPU:** nvidia-warp solved the plume fields at build time and they ship as data.

⚠ **NOT VERIFIED: the Docker image itself.** Docker is unavailable in this environment, so the
Dockerfile is reasoned rather than built. The start command inside it IS verified, which is the part
that usually goes wrong.

**THE KEY, and the blocker that had to be fixed first.** `testing/common.py:load_key()` read
`<root>/.env` and nothing else. That file is gitignored and must stay so, therefore it does not exist
on a host: the live agent could only ever have started on this one machine. It now reads
`FORTYGUARD_API_KEY` from the environment first, with the file as fallback. `render.yaml` declares the
variable with `sync: false`, so Render prompts and stores it encrypted and it is never in the
repository, not even in the Docker build context.

**⚠ THE LIVE ENDPOINT IS OPEN, BY THE OWNER'S EXPLICIT DECISION.** Their words: "let the user make live
calls, whoever it may be. there should be enough live calls limit available for multiple judges to run
the agent and they will refresh the credits themselves." `serve_live.py` has no authentication of any
kind, checked for tokens, bearer headers, origin and referer. `MAX_LIVE_CALLS` is the only ceiling,
counted per day. Each run is one heatmap window at 4,220 credits, about 246 runs remain, so 48 a day is
roughly five days of headroom and 24 a day roughly ten.

### 🔴 CORRECTION: "data/ is never needed at runtime" was half wrong

Recorded prominently because I told the user the wrong thing and then acted on it.

**What I claimed:** `AGENTIC-ARBITER/data/` is never fetched at runtime, proved by reading every fetch
in the page. **That part is true and remains true: the BROWSER never touches it.**

**What I missed:** the SERVER does. `serve_live.py` imports `live.py` which imports `agent.py`, and
`agent.py` reads `data/geometry/` at import time. Tested by hiding the folder:

```
live.py selftest   FileNotFoundError: data\geometry\selected_site.json
serve_live.py      will not start at all
```

**The minimal set, measured by hiding each subfolder in turn and re-running the selftest:**

| subfolder | size | needed by the server |
|---|---|---|
| `geometry` | **13.0 MB**, 1,185 files | **YES**, tracked in the repo now |
| `weather` | 229.2 MB | no |
| `national_fields` | 279.5 MB | no |
| `imagery` | 299.9 MB | no |
| `live_cache` | 217.6 MB | no, and the server recreates it if absent |

So the structure changed: the whole-folder junction is gone, `data/geometry/` is a **real directory
inside the repo**, and the other four are **per-folder junctions** to `D:/FGHackathon-data`.
`.gitignore` carries `AGENTIC-ARBITER/data/*` with `!AGENTIC-ARBITER/data/geometry/`.

Confirmed by hiding all four at once, which is what a fresh clone has: selftest ALL PASS, `/api/health`
200, `/app/` 200, `/sites.json` 200.

⚠ A TRAP THIS EXPOSED TWICE: running the server or the selftest RECREATES `data/live_cache/` as a real
empty directory, which then collides with restoring the junction under the same name. It has no files,
only an empty `ashburn/` subdirectory, so `Directory.Delete(path, recursive=true)` then rename the
junction back.

### 2026-08-28 - The repository is now what a judge sees, and nothing more

**The user: "Only 1 read me md file is to be there for the judges which will be professional."**
61 tracked `.md` files became 18; the 43 moved to `D:/FGHackathon-notes` with their original relative
paths. `IMAGERY-REVIEW/` followed them: 17 files, 5.1 MB of ESRI-versus-USGS comparison JPGs, and
nothing in any `.py`, `.js`, `.mjs` or `.html` reads it.

🔴 THE KEEP LIST WAS MEASURED. Every `.py` was stripped of comments and docstrings and the `.md`
filenames surviving inside string literals are the ones code actually opens. Moving one would have
broken `audit.py`'s 2,216 checks or `run_all`'s context step:

    README.md, API-USAGE.md, CLAUDE.md, RECIRCULATION-DEFENCE.md, money-sources.md,
    demo/README.md, demo/money-sources.md, CONTEXT/*.md

### 🔴 validation-data/ WAS QUIETLY HOLDING UP TWO PUBLISHED CLAIMS WITH NO GATE WATCHING IT

Asked whether it was needed, I first said yes because "the two recirculation tests read it". **They did
not.** They read `os.path.join(SCRATCH, fn)`, and `SCRATCH` in `testing/common.py` names ONE Claude
session's temp directory by id, `48b2e995-a9e0-4f0c-8ab4-8cbe4f628a17`, which no longer exists. So
`test_n21_validate.py` and `test_n22_calibrate.py` had been exiting 2 with *"no field data found in the
scratchpad"*, which reads like an absent dataset rather than a stale path.

The data was never absent. All SEVEN CSVs those tests ask for are in `validation-data/`, digitised from
California Energy Commission report **CEC-500-2013-065**, whose three source PDFs sit beside them, and
they are the evidence behind README's recirculation and 67-Prairie-Grass claims. **`run_all.py` does not
run those two tests, so nothing anywhere went red.** That is precisely how a folder like this gets
deleted by accident.

Fixed rather than noted: `common.py` gained `VALIDATION` and `field_path()` now searches
`(SCRATCH, VALIDATION, FIXTURES, HERE)`. Both tests run again:

- `test_n21_validate` **PASS**, the solver reproduces the measured shape at **r=0.798** in its better
  configuration (N-11 OFF), against 1-minute field data from six air-cooled condensers.
- `test_n22_calibrate` **PASS**, the closure fits the field data on held-out RMS.

### 2026-08-28 - Deployment prep, and the prose the UI stopped showing

**Deployment shape chosen by the user:** both the static demo and the live API on ONE Python host, so
`fetch('api/live/...')` stays same-origin and needs no code change, plus a static replay-only mirror on
GitHub Pages as the always-up fallback. `serve_live.py` already serves `demo/` statically and answers
`/api/*`, so the single-host option needs nothing written.

**Tracked bytes: 1,823 MB to 962 MB**, inside GitHub's recommended 1 GB. Nothing exceeded the 100 MB
per-file hard limit (largest is `scenarios.json` at 30 MB), so size was a repository problem rather than
a file problem.

| Removed | Size | Why it was safe |
|---|---|---|
| `AGENTIC-ARBITER/data/` | 1,039 MB, 2,120 files | never fetched at runtime; moved to `D:/FGHackathon-data` with a DIRECTORY JUNCTION at the old path so all twelve scripts keep working |
| unoffered artefacts | 28.3 MB, 153 files | the 14 sites `sites.json` marks not offerable; `#c_site` only ever holds an offerable key |

⚠ THE COST, STATED: a fresh clone cannot regenerate the pipeline without fetching the data folder
separately. That was the accepted trade.

**README migration, the brief's last unfinished item.** "Strip all other verbose, explanatory paragraphs
from the UI entirely and compile them into a well-structured README.md file." A new section, *Reading the
results stage, panel by panel*, 1,192 words, one subsection per panel, so nothing on screen is reachable
only by clicking.

🔴 IT DELIBERATELY QUOTES NO SITE-SPECIFIC FIGURE. The folded prose contains runtime numbers that change
with the selected site and the controls. Copying them into a static document would manufacture exactly
the class of claim `audit.py` exists to prevent: a figure no test re-reads. So the section explains what
each panel is FOR and what its arithmetic means, and leaves every number to the artefacts.

### 2026-08-28 - The results stage stopped being a report you scroll through

**The user, on the screen they cared most about:** "by the time user reaches the 'read the decision'
tab, it's the same layout as the html file that I told you I didnt like the UI of... seems like a
report generated through which you keep scrolling through with dump of too much technical information
and not an interactive app... I wanted you to be intelligent here and only display one or two liners
for every aspect and only explain in a pop up option."

**MEASURED FIRST, because "too much text" needs a number.** A probe drove the app to the results stage
and counted the prose actually on screen, per card: **1,680 words in 52 blocks across 13 cards**, most
of it written at runtime by the renderers rather than sitting in the markup. After the change:
**260 words in 19 blocks.** An 85 % cut.

**AND NOTHING QUANTITATIVE MOVED.** Tile, table and canvas counts per card are identical before and
after, checked card by card: decisioncard 5 tiles 1 table 2 canvases, headcard 5/0/0, cfcard 0/1/3, and
so on. `app/src/lib/declutter.ts` selects `p, li, details` and excludes
`.tile, table, canvas, #tape, .ev, .plate-cell, .rail-step, svg`, so it never looks at a figure. The
brief's line holds: "Do not modify the existing reports, graphs, or numerical data cards."

**HOW IT WORKS.** Each card gets one authored lead of one or two lines in plain language, and every
prose block over 14 words is hidden and folded into one button per card that opens it in a modal
(`DetailModal.tsx`). The engine keeps drawing exactly what it drew; this reorganises the result. Done
as a DOM pass rather than an edit to the engine because the engine is lifted byte for byte and a
verifier fails the build if a character moves.

Two bugs of mine on the way, both worth keeping:
- The pass appended a new fold row on every run, because the engine redraws PARTS of a card without
  replacing it. The screen showed "What a live run costs (3)" beside "(1)". It now rebuilds the single
  row from the folded nodes themselves, which are still in the DOM and still marked, so one pass
  produces exactly one correct row from any starting state.
- The audit that measured the improvement counted `textContent`, which includes hidden nodes, so it
  reported prose going UP after 52 blocks were folded away.

### 2026-08-28 - No dashes anywhere a reader looks

**The user:** "Throughout this project's text that you display and render, dont use '-' dashes."

**139 em dashes removed from displayed text, in two passes with different tools, because they needed
different care.**

| Where | Count | How |
|---|---|---|
| the page's body markup | 28 | 23 became a colon, 4 a comma, 1 a full stop |
| the page script's STRING LITERALS | 111 | same rule, applied by a classifier |
| the page script's COMMENTS | 10 | **left alone**, deliberately |

The markup pass was straightforward. The script needed a real scanner: a regex cannot tell
`'<code>fetch()</code> from '` from a comment that quotes code, and 10 of the 121 occurrences are the
page's own documentation, which there is no reader benefit in rewriting. So a single pass classifies
every character as code, comment, string or regex, asserts the classification round-trips to the
original, and rewrites inside strings only. It printed every change and refused to write if any dash
remained in a string.

That count is why the scanner mattered: I had assumed most of the script's dashes were in comments. It
was the other way round, 111 to 10, and they included the DAY dropdown ("crossing: 2025-03-11"), the
level anchor ("none: believe FortyGuard"), the decision legend and six of fourteen card headings.

`decide` and `explainHour` therefore changed in the page, which `audit_nothing_lost.py` correctly
flagged. Both are now declared exceptions with the reason and the date, so a THIRD function changing
still fails. Its HANDOFF.md line check gained the same treatment, anchored on the four shapes
`bump_spend_docs.py` owns rather than on whichever line failed last.

⚠ STILL WITH DASHES, and not swept: the page's own comments, `CONTEXT/`, and `README.md` prose the
user wrote. Standing rule B2 governs those.

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
