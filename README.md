# AGENTIC-ARBITER

**An agent that decides, hour by hour, whether a data centre can switch its mechanical chillers off
and cool with outside air, and that earns the right to say yes more often by grading its own
accuracy against reality.**

FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)

> **Data centres over-cool, continuously, because nobody can promise them the hours ahead.** A
> chiller plant needs hours of notice to change mode, and a thermometer only ever reports *now*: so
> the mechanical chillers keep running through hours that outside air could have cooled for free.
> **FortyGuard** closes that gap with heat intelligence **2 m above the ground**, the height a
> ground-mounted condenser actually breathes. This agent turns that forecast into an hour-by-hour
> schedule with a **calibrated safety bound**: over **913 held-out days** it cuts mechanical cooling
> runtime **10.7 %**: 9,510 h to 8,496 h. Remove the forecast and **88.3 %** of the gain goes with
> it.
>
> *No specific notice period is claimed. `notice_h` is a swept axis `[0, 1, 3, 6]` and the shipped
> row uses 3: a chosen configuration, not a sourced property of cooling plants. The whole sweep is
> in `backtest.json` and on the page.*

---

## The problem, stated as a contract

**Data-centre cooling-plant operators** struggle to **decide, each hour, whether to switch the
mechanical chillers off and cool with outside air** because **a rooftop thermometer cannot see three
hours ahead and a plant needs that much notice to change mode**, so they either switch late or
carry a conservative buffer. The result is **406 chiller-hours per year left on the table, worth
$5,522–$7,990 per MW of IT load**, measured across **43,763 hours of real weather** against the
reactive on-site-sensor control operators verifiably run today.

Every variable in that sentence is a measured number with a file behind it, not an estimate:
`audit.py` re-reads all of them. The dollar range is 16 cells: **4 published electricity tariffs ×
4 published chiller efficiencies**, swept rather than chosen, and **compressor-only**, which makes
it an upper bound on that term rather than a projection (§ *What is honest*).

---

## Start here: two commands

```bash
# 1. Prove it. 35 steps, ZERO API calls. Exits non-zero on any failure.
cd AGENTIC-ARBITER/src && python run_all.py

# 2. See it: REPLAY mode, no API key needed, works offline.
cd AGENTIC-ARBITER/demo && python -m http.server 8000        # then open http://localhost:8000
```

**How long step 1 takes scales with how many sites are offerable**, so it is quoted as a rate rather
than a duration: step 13 rebuilds every offerable site from its own data at **~63 s each** (measured),
and the rest of the ladder is a few minutes. That is ~5 minutes at the three shipped metros and a few
hours across the national tier. It used to say "~6 minutes" full stop, which was true when three
sites shipped and quietly stopped being true as the national build grew.

**To see it decide the next hours from a LIVE forecast**, serve it with the live agent attached
instead. This needs a FortyGuard key in the **repository root** `.env`: `testing/common.py:load_key()`
reads `<repo root>/.env`, and a copy inside `AGENTIC-ARBITER/` is read by nothing, which fails
silently: the server starts, `/api/health` answers, and the key is simply never found.

```bash
cp AGENTIC-ARBITER/.env.example .env          # then put your key in ./.env
python AGENTIC-ARBITER/src/serve_live.py --allow-paid   # then open http://127.0.0.1:8000
```

**Why two commands and not one:** a static page cannot make a live API call, because the request
needs a key and anything the page can read, every visitor can read. `serve_live.py` holds the key in
its own process and returns only numbers. The page detects which mode it is in and says so: it does not offer a live button that cannot work.

**New to this? Read [`READING-THE-AGENT.md`](CONTEXT/READING-THE-AGENT.md) first.** It explains every
screen, every control and every graph from zero: no data-centre or statistics background
assumed, every term defined before it is used.

**`file://` will not work.** Browsers block `fetch()` from it and the page will show only a red
error. Any static host serves the demo as-is: there is no build step and no server side.

**There are two front ends, and the single-file page is the canonical one.**
`AGENTIC-ARBITER/demo/index.html` is what a judge opens: one file, no build step, nothing to install,
and it is what every verifier measures. `AGENTIC-ARBITER/app/` is a Vite + React rebuild of the same
product, started 2026-08-28. It is not a separate demo: it renders the page's own configure and
results markup and drives the page's own drawing code, lifted byte for byte into
`AGENTIC-ARBITER/results/engine.mjs`. Three of the 35 steps below exist to prove that, one of them by
driving pick to results in a real browser. Build it with `cd AGENTIC-ARBITER/app && npm ci && npm run
build`; the output is designed to drop into `demo/`, where the same relative fetches resolve, so the
shipped artefact still has no install step.

**If `run_all.py` is not green, do not believe a number on the page.** It re-reads **77 published
figures** from the files the code actually wrote and runs **2216 audit checks**, including five that
re-derive the browser's own arithmetic against Python and one that drives a real browser to render
every site and diff the panels a reader would look at.

---

## What it does

Seven stages, all of them in code, in `AGENTIC-ARBITER/src/agent.py`:

```
perceive  FortyGuard heatmap + env_params + real wind + its own accuracy record
  solve   576-solve GPU rise table on real building geometry (NVIDIA Warp)
  bound   Mondrian group-conditional conformal + plume-ensemble normalisation
  decide  a switching SCHEDULE under a switch budget and a dwell limit, by DP
  act     BMS/SCADA-shaped command rows, each carrying its own numbers
  explain deterministic, and every claim verified by re-running the agent
  score → recalibrate: the safety margin widens itself when reality proves it wrong
```

**What that buys, measured on 43,763 hours of real weather across five years**: 913 held-out days
the agent never calibrated on, on real Ashburn geometry, against the reactive on-site-sensor
incumbent that operators verifiably run:

| | |
|---|---|
| Free cooling delivered | **5,375 h/yr** by the rolling controller, hour by hour |
| Chiller-hours avoided vs the incumbent | **+406 h/yr** |
| **FortyGuard**'s share of that gain | **88.3 %**: at zero forecast skill the same agent gains only **+47.6 h/yr** |
| A published 12-hour plan holds | **94.1 %** of 21,879 re-plans change nothing at all |
| Bound coverage, measured | **65.6 %** against a 90 % promise: **it FAILED its pre-registration** |

**The forecast is the product.** Row three is measured by taking it away: hold every other setting
at the shipped configuration, drop the forecast to zero skill: nothing beyond "tomorrow resembles
today", and 405.7 h/yr becomes 47.6. The physics, the plant limits and the dew-point gate are all
still in place; only **FortyGuard** is gone. The same axis run the other way says it scales with
lead time: **0 h → +118.8 · 1 h → +230.8 · 3 h → +405.7 · 6 h → +645.3 h/yr.** A thermometer gives
zero notice by construction, which is why a forecast is the missing input rather than a refinement.

And the last row is the other point. **The failure is on the front page of the demo, not in a
footnote.**

---

## Who buys this, and how the first one starts

**The hero is a named role, not a market.** The critical-environments or facility engineer at a
colocation operator: the person who owns the PUE target, signs off on setpoint changes, and gets
called at 03:00 when an intake runs hot. They are the buyer because they carry both halves of this
trade: the energy number they are measured on, and the risk they personally absorb if a hall
overheats.

**What the pain costs them today:**

| | |
|---|---|
| **Mechanical cooling runtime cut** | **10.7 %**: 9,510 h of chiller time becomes 8,496 h. A share, so it holds at any hall size |
| Chiller-hours recoverable | **406 h/yr** vs the tuned reactive incumbent |
| Value of those hours | **$5,522 – $7,990 per MW-IT per year** |
| At the shipped site's own measured size: 86,280 m², **61–121 MW** of IT load | **$334,000 – $967,000 per year** |
| At the largest facility in the registry: 1,116,335 m², **783–1,566 MW** | **$4.3M – $12.5M per year** |
| Basis | 16 cells: 4 published tariffs × 4 published chiller efficiencies, **swept, not chosen** |

**Lead with the first row.** It is a percentage, so it needs no assumption about how big the
building is: over 913 held-out days the reactive incumbent runs its chillers **9,510 hours** and the
agent runs them **8,496**. That figure reads the same on a 1 MW room and a 1,500 MW campus, which is
why it is the honest headline and the dollar rows are the illustration.

⚠ **The megawatt figures are DERIVED, and the footprint half of them is measured.** The footprint is
ours: **20,441,476 m²** of tagged data-centre buildings across 639 US facilities, computed from the
same OpenStreetMap rings the solver runs on. The density is derived from LBNL 2024: **176 TWh** of
US data-centre electricity in 2023 (p.6, p.52) at **PUE 1.4** (p.47) is 125.7 TWh of IT-only energy,
**14,341 MW** averaged over the year, spread over that footprint: **702 W/m²** of average load, or
**1,403 W/m²** installed at LBNL's ~50 % capacity utilisation (p.7). Hence a range, not a point.

⚠ **And the density's errors do not cancel.** LBNL's 176 TWh covers every data centre, including
server closets carrying no OSM tag, so dividing it by tagged-only footprint **overstates** density;
incomplete OSM coverage overstates it again; multi-storey halls understate it. Net: probably high.
The one independent check available says it lands in the right place: applied to Virginia's measured
4.71 km² it gives **~3,300 MW** of average IT load, against published Northern Virginia data-centre
load in the low thousands of MW. That is a sanity test, not a calibration, and the range is quoted
because of it. **The old row here read "a 30 MW hall": a round number with no source behind it,
which this replaces.**

⚠ **Compressor-only, and therefore an upper bound on that term.** Fans, chilled-water pumps,
condenser pumps and tower fans keep running, and an airside economizer moves *more* air, so the
unmeasured fan term has the **opposite sign**. We did not find a defensible °C→fan-kWh conversion in
any primary document, so it is excluded and labelled rather than estimated. Sources in
[`money-sources.md`](money-sources.md).

### The wedge: shadow mode, and it needs nothing from their plant

The smallest sellable unit is **not** control. It is a **30-day shadow trial**:

1. The agent publishes a 12-hour switching schedule each hour, for their site's real geometry and
   their own weather station.
2. **The operator ignores it.** No BMS integration, no setpoint written, no procurement, no risk.
3. After 30 days, compare what the agent said against what actually happened: hour by hour, with a
   reason attached to every hour.

That comparison artefact already exists and already ships: the per-site PDF this repository
generates is exactly the document a shadow trial produces. **The demo you can run right now is the
product's first deliverable**, not a mock-up of it.

**Why shadow mode is the right wedge and not a hedge:** a cooling plant will not hand control to
software it has not watched, and no procurement process starts with write access to a chiller.
Shadow mode is how this class of product is actually bought, and it is also the honest sequencing,
because the one thing this project cannot yet claim is a 90 % bound on live forecasts (§ *What is
honest*). Thirty days of shadow data is simultaneously the sales motion **and** the missing
calibration set: it produces the ~9 measured day-pairs the bound needs. **The trial that earns the
customer is the same trial that finishes the science.**

### What we do not have

No signed pilot, no letter of intent, and no operator interview. The pain is evidenced from
published sources: LBNL instrumented eight real data centres and documented *why* operators avoid
free cooling: not from a customer conversation we have had. **That is the biggest hole in the
commercial case and it is stated rather than papered over.**

---

## Useful AI, and where we deliberately did not use one

**There is no LLM anywhere in this product, and that is a decision we can defend line by line
rather than an omission.** The test we applied: *if deterministic code solves it exactly, at zero
variable cost and zero latency, an LLM is a liability rather than a feature.*

The decision is recorded in the emitted artefact, not just in prose: `demo/explanations.json`
carries `local_model_used: false` and the reason it was declined:

> *"no inference stack installed … and this stage reports numbers the agent already computed: > **deterministic generation plus verification is safer than generation plus hope**"*

And it was declined on the merits, not on capacity: the same file records the GPU headroom measured
at the time: **371 MiB peak of 6,141 available**, so a small local model would have fitted
comfortably. We had the room and chose the verifiable path.

| Job | What does it | Why not a model |
|---|---|---|
| Deciding the switching schedule | **Dynamic programming** over `(mode, switches used, dwell owed)` | The optimum under a switch budget and a dwell limit is *exactly* computable. A model would approximate a solved problem, and could not carry a hard constraint |
| The safety margin | **Split conformal prediction**: Mondrian, group-conditional, 20/20 self-tests | A distribution-free finite-sample guarantee. No learned uncertainty head offers that, and this one is falsifiable: ours failed its pre-registration and we published the failure |
| Explaining every decision | Deterministic templates, and **30 stage-event templates in which no template may contain a literal digit**: enforced at build time | A generated explanation cannot be verified against the decision it explains. Ours is re-derived and checked: **1,336 explanations, 0 verification failures** |
| Reading the vendor's field | Nearest-tile lookup on real coordinates | It is a spatial index, not a judgement |

**Where machine compute *is* load-bearing, because rules genuinely break down there:** the plume
field. **576 coupled advection–diffusion solves** across 72 wind bearings × 8 wind speeds on the
rasterised OpenStreetMap footprints, run on the GPU through **NVIDIA Warp in 5.34 s**. There is no
closed form for exhaust recirculation between two irregular buildings: that is precisely the
"rules-based logic naturally breaks down" case, and it is where the compute budget goes.

**The agent's execution scope is constrained on purpose, and narrowly:**

- **Two actions.** Free cooling, or mechanical. That is the entire action space.
- **Safety is a hard constraint, not a penalty term.** There is no invented exchange rate between a
  degree of risk and an hour of chiller. An earlier prototype needed `c_excursion = 120.0` to
  produce an answer at all; that number had no source, so the whole approach was discarded.
- **It refuses.** When the intake disc would average the exhaust it is meant to measure, the solver
  declines to answer and the agent **falls back to mechanical**: a refused bearing is not
  permission.
- **Bounded actuation.** A switch budget and a minimum dwell, both cited to operator practice rather
  than chosen by us.
- **It cannot act on a perception it does not have.** When the vendor returns no field, the live
  agent emits **no schedule at all**: not an interpolation, not a carried-forward value, not a
  saved field relabelled as live.

**What this buys in cost terms:** the decision path has **zero variable inference cost and zero
model latency**. Every FortyGuard credit is spent on *perception*: the one thing we cannot compute
ourselves, and none on reasoning we can do exactly.

---

## What is honest about this, and what is not

**The first four of these used to be a card on the demo page.** They were removed from it on
2026-08-26 and moved here, because a results screen is for results: not because any of them stopped
being true. `drawLimits()` in the demo still derives all four from the artefacts, so this copy stays
checkable against something rather than becoming prose nobody re-reads.

**The fifth arrived here the same way, on 2026-08-27.** It was two sentences on the site *picker*,
*"No forecast/outcome day pair yet, so the measured level offset is still Ashburn's…"*, shown to
anyone choosing one of the many sites that hold a field without a calibration. A caveat that applies
to almost every site is a property of the project rather than news about the site just chosen, and
the picker is where a reader is choosing, not reading method. It is off that screen and stated here,
and it remains on each site's own results panel where the coverage figure it qualifies actually
appears.

| | |
|---|---|
| **Reproducible rather than live, and it says which** | Every panel is computed from saved **FortyGuard** responses. N-55 re-requested a window and got **17,862 of 17,862 tiles byte-for-byte identical**, so replay is not a weaker claim than a live call, it is the same numbers, on demand. The live path exists and is labelled separately. |
| **The 90 % bound does not hold yet** | Measured **65.6 %**. It has 4 calibration day-pairs and needs about 10. At 4, the arithmetic ceiling is 80 %, so part of that gap was never reachable. More days is the whole remedy, and they come from **FortyGuard** data alone. |
| **The hours claim wants a level anchor** | One local reading. Unanchored, five years of data say the agent **loses**. The *safety* guarantee needs no customer hardware; the *hours* do. |
| **Recirculation here is small, and that is the physics working** | The worst case is a fraction of one weather-station grid step. A model that reported a large rise at this geometry would be wrong, not impressive. |
| **Only Ashburn has a calibration of its own** | A **field** is one call; a **calibration** needs a forecast leg *and* its elapsed outcome. Many sites hold a purchased **FortyGuard** field, and **Ashburn is the only one with forecast/outcome day-pairs**, so at every other site the *hours, weather and geometry are that site's own* and the **measured level offset and the coverage record are Ashburn's**. The artefact records it per site (`trace.fortyguard_provenance.own_measured_day_pairs`), the coverage figure on each site's results panel says *"measured at Ashburn and applied here"*, and `audit.py` check 6d asserts that **every** borrowing site declares it, so a borrowed number cannot pass as a measured one. |
| **The imagery is one source at nearly every site, and it cannot certify equipment** | The screening gate reads aerial frames. **3 of 250 offerable sites** have two independent sources (ESRI World Imagery *and* USGS The National Map); **245 carry exactly one**, so the **two-source cross-check is NOT met** there, one vendor and one capture season. And **2 have no screening frame at all**. Separately, at *every* site including those three, imagery at **0.3–0.5 m shows objects, not nameplates**: it cannot certify a unit type or measure a height, so it is evidence about *where* equipment is, never about *what* it is. Both facts are recorded per site in `sites.json` (`imagery.two_source_cross_check`, `imagery.resolution_note`), those three counts are re-read from it by `audit.py` rather than typed here, and the site panel's "Imagery source" control lists exactly the sources that exist, so a single-source site cannot present itself as cross-checked. |

**What "no plume is modelled" does and does not mean.** At a facility with no other tagged data
centre inside the solver's validated 600 m range, the quantity the rise table computes: the
temperature rise at a *neighbour's* air intake: **does not exist** rather than being unmeasured.
That is a statement about the model's domain, **not a claim that recirculation there is zero.** And
one limitation applies everywhere, not just to those sites: **self-recirculation: a building's own
exhaust re-entering its own intake: is not modelled at ANY site in this project, including the
three shipped metros.** The solver places the condenser bank on the source building's ring and the
intake outside the *receptor's* facing facade, so the only quantity it ever computes is the
neighbour's exhaust arriving at my intake. That is worth stating plainly because the primary case in
this project's own cited source, **ASHRAE Handbook Ch. 46**, is the self-recirculation one: and
because it is what makes running the isolated facilities *consistent* with the paired ones rather
than a concession.

*These two sentences were on the demo page until 2026-08-26, where they filled a card that had
nothing else to show. They remain verbatim in the `why_zero` field of every standalone facility's
rise table, so the page trims the view without touching the record.*

**What the safety bound does NOT claim, and cannot.** Full *conditional* coverage: being right 90 %
of the time in **every** situation separately rather than 90 % on average: is **provably
impossible** for any distribution-free method with finite data (Barber, Candès, Ramdas &
Tibshirani, *The limits of distribution-free conditional predictive inference*, Information and
Inference **10**(2), 2021). That matters because an average hides its own worst case: pooled across
the day this bound reads a healthy **90.17 %** overall while one hour of the day sits at
**73.14 %**, and **6 of 24** hours fall under nominal. So the agent ships the strongest thing that
*is* achievable: **Mondrian conformal stratified by hour of day**, which calibrates each hour
separately and lifts that worst hour to **87.94 %**, leaving **5 of 24** under nominal. Stratifying
by hour **and** season on top was measured and **rejected**: it over-stratifies, dropping the worst
group to **84.93 %** and putting **27 of 96** groups under nominal. The claim is group-conditional
by hour of day, and nothing more.

*This paragraph was a panel on the demo page until 2026-08-26. Its five figures are registered in
`audit.py` check 10 and re-read from `backtest.json` on every build, so moving it off the screen did
not turn it into prose nobody checks.*

**Why the money figure is a ceiling and not a projection.** It counts the chiller **compressor
only**. Fans, chilled-water pumps, condenser pumps and cooling-tower fans keep running, and an
airside economizer moves *more* air, so the unmeasured term has the **opposite sign**. On top of
that, the chiller is assumed at ASHRAE 90.1 code minimum, which is a legal *floor* that real
hyperscale plants beat, and full-load kW/ton overstates the draw at exactly the cool conditions free
cooling needs. The tariff is an EIA state-sector average, not the site's own contract. Four
independent reasons the real number is **smaller**, none that it is larger.

All **608 cells** are swept: every ladder and sensitivity row × 4 published chiller efficiencies ×
4 published prices, and **no row is collapsed**, including the ones that come out negative. The
worst cell anywhere in the sweep is **−$61,538 per MW-IT per year**, where the refusal guard fires.
Every one of those limits, and all four parsed sources, are in
[`money-sources.md`](money-sources.md), generated from `money.json` by
`src/write_money_doc.py` and asserted present by `audit.py` check 12.

Read `AGENTIC-ARBITER/PLAN.md` for the full design record: every claim
there carries a citation and a link, verified by opening the source. The short version:

**Established.** Seven-stage loop over **120,960 swept scenarios**. Conformal layer with **20/20
self-tests**: Mondrian, CQR, ACI/DtACI, joint coverage, worst-group. Physics validated against an
analytic plume at **0.00 %**, heat conserved at **0.00 %**, **67 Prairie Grass** field experiments,
and 6 instrumented condensers at **r = 0.798**. **1,336 explanations with 0 verification failures.**
A reasoning tape whose **32 templates contain not one literal digit**, checked at build time.
**Three sites live on their own geometry, weather, bound and tariff, and two more were refused on
aerial evidence.**

**On the size of the verification surface**, because it is fair to ask: **2216 audit checks and a
gotcha log of 195 entries exist because every one of them actually bit**: a NaN that
was legal Python JSON and illegal standard JSON, a rounded array that flipped decisions at gate
boundaries, an invented constant that outlived its own retraction by a day, a site picker that
swapped one file out of thirteen. Every check is a headstone. That is **validation** infrastructure,
and it is the only infrastructure here: there is **no Kubernetes, no vector database, no message
queue, no microservice and no build step**: the interface is one HTML file with one inline script,
and the whole thing rebuilds and re-verifies in about five minutes on one laptop. **Scale is a
problem we have deliberately not solved yet.**

**Not established, and labelled as such everywhere it appears.**

- **The 90 % bound is not proven on live forecasts, and the reason is sample size rather than
  method.** Two separate things, kept separate because collapsing them misdescribes both:
  - **The method is validated.** The conformal layer passes **20/20 self-tests**, and on the
    five-year record **all 12 per-lead bounds cover ≥ 90 %**.
  - **The live calibration is under-sampled.** A 90 % one-sided bound needs **9 calibration
    day-pairs; 4 exist.** At n=4 the attainable coverage ceiling is n/(n+1) = **80 %**, so 90 % is
    *arithmetically* unreachable: not methodologically refuted. Measured coverage on held-out days
    is **65.6 %**, which **failed its pre-registration**, and that is the only figure we quote.
  
  So this is a data-collection gap with a known fix: 5 more day-pairs: currently blocked by the
  vendor outage in [`API-USAGE.md`](API-USAGE.md) §5. **A 30-day shadow trial produces exactly that
  calibration set**, which is why the commercial wedge and the remaining science are the same
  activity.
- **The agent is an adaptive controller with a self-calibrating boundary, not a stopping rule.**
  Seven pre-registered "when to act" decision cores were tried and **all seven failed**; they are
  documented rather than deleted (`PLAN.md` §6).
- **Money covers the chiller compressor term only**, from two documents parsed in this repository
  ([`money-sources.md`](money-sources.md)). The fan, pump and tower term is **not sourced and not
  claimed**, and it has the opposite sign.
- **Claims that were retracted are listed as retracted**, with what killed each one
  (`HANDOFF.md` §2.3).

---

## Reading the results stage, panel by panel

The interface deliberately shows very little prose. Each panel carries a one line lead, its numbers and
its graph, and a single button that opens the detail. This section is the long form of that detail, so
nothing on the screen is reachable only by clicking.

Panels appear in this order once you press **Run the agent**. Every figure named below is recomputed
from the artefacts whenever you change a control; the words here explain what a panel is for, not what
its numbers happen to be today.

### The agent, working
Seven named stages, streamed as they run: perceive, solve, bound, decide, act, score, recalibrate.
Every number anywhere else on the page is produced in these steps, and each line is a claim you can
check. **No language model is involved**, and that is a design decision rather than a limitation: this
stage reports numbers the agent already computed, which is the one place a model would be most likely
to be wrong and least excusable. The **Download the decision report** button writes a PDF snapshot of
one named configuration.

### The decision: a schedule, not a thermostat
One day, hour by hour, in two rows: what the agent chose, and what the reactive controller operators
actually run chose. Hours are maximised **subject to** three constraints at once, which is what makes
it a schedule rather than a setpoint:

- a hard safety bound on intake temperature,
- a **switch budget**, a limit on how many times a day the plant may change mode,
- a **minimum dwell**, the least time it must stay in a mode once it is there.

The line chart beneath shows, for each hour, the agent's upper bound on intake against the plant limit
and against what actually happened. Where the bound crosses the limit, the agent does not switch.

### What it is worth here, over five real years
The site's own recorded weather, priced. Delivered is what the rolling controller actually ran, hour by
hour on a twelve hour horizon, each hour bounded at its own forecast lead. Avoided is the difference
against the incumbent.

**On a large share of settings the honest answer is that there is no free cooling to win, and that is
reported rather than hidden.** A tool that claims a saving everywhere is not measuring anything.

### Five years of real hours
A ladder: take one input away at a time, leave everything else in reality, and measure what the loss
costs. That is how you find out what each part of the agent is actually worth rather than asserting it.

- Blind it to the neighbour's exhaust and it loses hours **and** its unsafe declarations rise.
- Remove the single on site temperature reading and forecast skill falls, because that reading is what
  removes the day level offset.

### What it is worth in money, and why it is a ceiling
Four published electricity tariffs by four published chiller efficiencies, sixteen cells, cheapest to
dearest. **A sweep, not a projection, and not a confidence interval.** The result is quoted per MW of
IT load per year and multiplied by this site's own measured footprint.

It is a **ceiling** because it prices compressor energy only. Real plants also spend on fans, pumps and
maintenance, and those are not counted, so the true saving on the cooling bill is smaller than the
compressor term alone.

### Screen zero: FortyGuard's field, doing the work first
The vendor's own forecast field for the tile this site sits in, at roughly two metres above ground. The
reason that height matters is the whole premise: a satellite skin temperature and a ten metre weather
mast both measure air the equipment never touches, while a ground mounted condenser breathes at about
two metres.

### The site, on real imagery
The building footprints the solver actually used, taken from OpenStreetMap, drawn over aerial imagery so
you can see they are the real buildings and not a sketch. Drag to pan, scroll to zoom.

### The plume, solved
The neighbour's hot exhaust, solved on this site's real geometry rather than drawn as a cone. Turn the
wind and watch the intake heat up.

The spread follows the textbook square root law, and it was **checked rather than assumed**: it was
tested against 67 Prairie Grass field experiments. Orange is rise above ambient. The dashed circle is
the thirty metre intake averaging disc; the orange strip is the condenser bank.

### Turn the wind: 72 bearings on the real geometry
Every wind direction, solved, not sampled: 72 bearings at five degree steps, 576 GPU solves per
placement, on the committed footprints.

**Bearings the solver refuses are marked, and refusal is a feature.** Where a building sits on the line
from the source to the intake, the validated model does not apply, so the agent declines the hour
instead of guessing. An agent that always has an answer is not being careful.

### Why: the agent's own reasoning, checkable
The agent's reasoning for a single hour, in its own words, and then checked by running the agent again
and comparing. It is deterministic prose generated from the numbers, which is why it can be verified at
all.

### The self-scoring loop
The agent grades its own promise against what happened, and widens its own margin when it was wrong,
unprompted. Coverage is also broken out by hour of day, because **one pooled number is not enough**: a
bound can look fine on average and fail badly in the hard hours.

### How the bound is built
The safety margin is **not chosen**. It is an order statistic over the agent's own past errors, and
there is no changeover temperature anywhere in the source. This panel runs that arithmetic in front of
you, with the two parameters exposed:

- **alpha**, the miscoverage you are willing to allow,
- **n**, how many calibration points there are.

The ceiling matters and it is arithmetic, not modelling: with **n** calibration day pairs the best
coverage anyone can attain is **n/(n+1)**. A small **n** caps coverage well below 90 % before any
modelling error enters. The same machinery is then shown at five year sample sizes across twelve
separate bounds, one per forecast lead, because **a bound calibrated at one lead is not valid at
another**.

### Run the agent live for the next hours
The next hours decided on a forecast bought at that moment rather than on saved responses, bounded by
the agent's own measured track record and scheduled under the same switch budget and dwell limit.

Served statically there is no live agent, the card says so, and the button is disabled. That is the
honest state and not a failure. To attach one:

```bash
python AGENTIC-ARBITER/src/serve_live.py --allow-paid
```

It runs as a separate process because FortyGuard authenticates with a secret key, and anything a web
page can read, every visitor of that page can read. **A live run costs 4,220 credits per hourly
window**, so it needs both that flag on the server and the request itself to ask for it.

---

## Deploying it

One service serves the whole product, including the live agent. That is possible because both front
ends call the agent with a **relative** url, `fetch('api/live/<site>')`, and
`AGENTIC-ARBITER/src/serve_live.py` answers both the static files and `/api/*` from the same origin.

```bash
# what a host runs
python AGENTIC-ARBITER/src/serve_live.py --allow-paid --host 0.0.0.0 --port $PORT --max-live-calls 48
```

| URL | What is there |
|---|---|
| `/app/` | the React interface |
| `/` | the single-file page, no build step, works offline |
| `/api/health` | what mode the server is in, and how much budget is left |
| `/api/live/<site>` | a live run, on a forecast bought at that moment |

### The five steps

1. Create an empty repository on GitHub, then:
   ```bash
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin master
   ```
2. In Render: **New > Blueprint**, point it at the repository. It reads [`render.yaml`](render.yaml).
3. Render prompts for `FORTYGUARD_API_KEY`. **Paste the key there yourself.** It is stored encrypted,
   and it is never in this repository, never in the Docker image, and never in a chat log.
4. Deploy. The interface is at `https://<your-service>.onrender.com/app/`.
5. Add a keep-alive ping, which is what stops a judge meeting a cold start. See below.

### Changing the project after it is deployed

Render **auto-deploys on push** to `master`, and if a build fails the running version keeps serving
uninterrupted. Deploys have zero downtime, so a judge will not catch a gap.

⚠ **ONE STEP IS EASY TO FORGET AND FAILS SILENTLY.** The site serves `AGENTIC-ARBITER/demo/app/`, the
built React bundle, which is committed. The image installs Python dependencies only, so it cannot build
the app. Edit the source, push, and Render will rebuild, succeed, and serve the **previous** interface.

So a front-end change is:

```bash
python tools/build_app.py          # builds, copies into demo/app/, records a source hash
git add -A && git commit -m "..."  # commit demo/app/ along with your source change
git push
```

`run_all.py` step 32 fails if the shipped bundle is stale, and **step 33 starts the server and
checks that `/` actually returns the React app**, because those are different failures: the bundle can
be current and still not be the page anyone reaches. That second one is not hypothetical, it is why the
step exists. A change to the Python side needs no build step at all: commit and push.

### Keeping it awake, which matters more than it sounds

Render's free instance **spins down after 15 minutes without traffic**, and waking it takes about a
minute. A judge arriving at a sleeping service waits, and a live run requested during that minute can
time out. So point any free uptime pinger at the health endpoint every 10 minutes:

```
https://<your-service>.onrender.com/api/health     every 10 minutes
```

`/api/health` is cheap, makes no vendor call and costs no credits: it reports the mode, the key's
presence and the remaining budget. The arithmetic works out: Render allows **750 free instance hours
per workspace per month**, and a service kept awake for a 31-day month uses about 744, so one
always-awake service fits inside the free allowance with a little room.

If you would rather not depend on that margin, Render's cheapest paid instance is always on and removes
the question. Check their pricing page for the current figure.

The same [`Dockerfile`](Dockerfile) runs on Fly.io, Railway, Google Cloud Run or any container host.
⚠ Hugging Face Spaces is **not** an option on a free account any more: Docker Spaces now require a paid
plan.

### Two things worth knowing before you deploy

**The key is never in the repository.** `.env` is gitignored, and
`testing/common.py:load_key()` reads the `FORTYGUARD_API_KEY` environment variable first and falls back
to that file only for local work. A host supplies the variable; the repository never carries the secret.

**The live endpoint is open, and that is a deliberate choice.** `serve_live.py` has no authentication,
so any visitor can request a live run and no token is needed for a judge to try it. The only ceiling is
`MAX_LIVE_CALLS`, counted per day, changeable in the host's dashboard without a redeploy. Each live run
is one FortyGuard heatmap window at **4,220 credits**:

```
MAX_LIVE_CALLS=48    up to 202,560 credits a day
MAX_LIVE_CALLS=24    up to 101,280 credits a day
```

**No GPU is required.** The plume fields were solved with NVIDIA Warp at build time and ship as data.
The server replays them and never solves, so the smallest CPU instance is enough. Its only dependencies
are `numpy` and `psychrolib`, listed in [`requirements.txt`](requirements.txt).

---

## Where things are

| Path | What is there |
|---|---|
| [`AGENTIC-ARBITER/`](AGENTIC-ARBITER/) | The product. `src/` is 24 modules, `demo/` is the interface, `PLAN.md` is the citation-bearing design record |
| [`AGENTIC-ARBITER/demo/`](AGENTIC-ARBITER/demo/) | One HTML file, one inline script, no build step, no dependencies. **Zero API calls at view time** |
| [`API-USAGE.md`](API-USAGE.md) | How much of the FortyGuard plan was used, derived from the credit meter rather than asserted: **13 calls, 54,860 credits, 2.74 %** |
| `fortyguard-api-findings.md` | 1,105 lines of field findings written for the FortyGuard team, with a section listing the suspicions that **failed retest and were withdrawn** rather than deleted |
| [`money-sources.md`](money-sources.md) | Every price and efficiency figure, with the document and page it came from |
| [`CONTEXT/HANDOFF.md`](CONTEXT/HANDOFF.md) | The working log. Long, blunt, and includes **195 gotchas that each actually bit**, plus a running tally of how often this project's own verification code was wrong |
| [`testing/`](testing/) | Every experiment, including the failures. `scan_secrets.py` and `api_usage_ledger.py` are the two you can run for free |
| [`*-PREREG.md`](.) | Pre-registrations with dated amendment logs, written **before** each test ran |
| `damper-*.md`, `project-master-plan*.md` | An earlier project direction, abandoned. Kept because the reasoning that killed it is part of the record |

---

## Reproducing the parts that cost nothing

```bash
python testing/api_usage_ledger.py           # the API spend ledger, from saved meter readings
python testing/scan_secrets.py               # full tree AND full git history, for leaked keys
python testing/test_n26_coverage.py dryrun    # what the collector would do now; no key is read
python testing/test_n26_coverage.py selftest  # its retry budget, against all 5 measured vendor faults
python testing/n26_recovery_watch.py plan     # what the recovery watcher would spend today; spends 0
python testing/n26_chicago_offset.py dryrun    # Chicago's own level offset: window, lead, cost. Spends 0
python testing/verify_site_panels.py          # renders every site in real Chrome and diffs the panels
cd AGENTIC-ARBITER/src && python audit.py      # 2057 checks, 77 published numbers re-read
cd AGENTIC-ARBITER/src && python report.py     # the per-site PDF, verified by being reopened
```

All five make **zero API calls**.
