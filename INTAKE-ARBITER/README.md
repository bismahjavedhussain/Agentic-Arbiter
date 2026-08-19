# INTAKE-ARBITER

**An autonomous agent that decides, hour by hour, when a data centre can switch its mechanical chillers
off and cool with outside air — built on the one thing no on-site sensor can ever provide: a forecast.**

FortyGuard Hackathon'26 · Track 3 (Industrial & Enterprise) + Track 6 (Agentic AI)

---

## The case, in one paragraph

Free cooling means opening the vents instead of running the chillers. It is nearly free, and operators use
it **less than they safely could**. Not because their thermometer is bad — it sits on their own roof and it
is accurate. **It is because a thermometer cannot see three hours into the future, and a cooling plant
needs that much notice to change mode.** So the plant either switches late, or carries a conservative
buffer and leaves hours on the table. **FortyGuard's forecast is exactly the missing input**, and
INTAKE-ARBITER is the agent that turns it into switching decisions, bounds its own uncertainty, and then
**grades itself against reality every day and adjusts how aggressive it is allowed to be.**

---

## What we measured

Against the incumbent operators verifiably run — a **reactive on-site rooftop sensor** monitoring air
temperature, dew point and humidity, with **no wind data and no forecast at all.** That is not an
assumption: in the 27-page LBNL thermal-guidelines document the words *"outdoor"*, *"outside air"* and
*"forecast"* **do not appear once**.

Over **43,763 hours — 99.9 % of five full years** of real weather, on **real Ashburn geometry**, with both
sides held to the same measured safety level:

| Where the value comes from | Extra free-cooling hours/year |
|---|---|
| **Forecast, at 3 hours' notice**, using FortyGuard's skill *as measured* | **≈ 930** |
| **Forecast, at 6 hours' notice** | **≈ 1,944** |
| Recirculation physics alone, no forecast involved | ≈ 67 |
| Forecast at 1 hour's notice | ≈ 62 |

**The forecast is ~93 % of the value.** The physics is a supporting safety term. And below roughly two
hours' notice the forecast is worth almost nothing, because *"same as now"* is already a good guess over a
short gap — **we report that rather than hide it.**

*Chiller-hours only. No dollar or kWh figure is claimed anywhere: the °C→kWh conversion could not be
sourced from a primary document.*

---

## How good is FortyGuard's forecast? We measured it — and it is strong where it matters

`skill = 1 − (forecast error ÷ error of assuming nothing changes)`. 0 = no better than a naive guess.

| Hours ahead | Skill |
|---|---|
| 1.5 h | 0.15 — barely better than guessing |
| **3.5 h** | **0.62** |
| 9.4 h | **0.84** |

**That is exactly the right shape for this problem.** Over a short gap persistence is already fine; over a
long gap it is hopeless — and long notice is what a plant needs. **This is the capability an on-site sensor
cannot buy at any price.**

⚠ Measured on **one day** across five lead times. The shape is well determined; the day-to-day spread is
not. See [`n56-freecooling-PREREG.md`](../n56-freecooling-PREREG.md) §6.

---

## What we found in FortyGuard's data — and are handing back

The self-scoring loop caught a real defect. **Stated carefully, because the obvious way to state it
would be wrong:**

**We are NOT comparing FortyGuard against a distant weather station.** Their field is 2 m above a
data-centre corridor; the nearest airport station is kilometres away over grass. FortyGuard reads **~+2 °C
warmer** there — **that is urban heat island, i.e. their data working correctly, and it is not a defect.**

**The finding is that FortyGuard's forecast disagrees with FORTYGUARD'S OWN HISTORY** — same API, same
17,862 tiles, same 2 m plane, same location, same two-hour window. Any height or location offset cancels
exactly. **Their two products differ by up to +3.64 °C about the same window.**

**And it shows up where it matters most — in tracking real change:**

| Consecutive days | Real change | FG **history** | FG **forecast** |
|---|---|---|---|
| Aug 12 → 13 | +1.67 °C | +2.11 | +1.82 |
| Aug 13 → 15 | −1.11 °C | −0.40 | −1.40 |
| **Aug 15 → 16** | **−6.11 °C** | **−5.70** | **−1.87** |

**A real 6.1 °C cool-down arrived. Their history saw 5.7 °C of it. Their forecast saw 1.9 °C.** Across
day-to-day changes their history tracks reality to **0.52 °C** and their forecast to **1.56 °C** — **3.0×
worse.** Because these are *changes*, the comparison is immune to the height and location objection above.

**The tell that it is fixable: the error is the same 1.5 hours ahead as 9.4 hours ahead** — slope
**−0.006 °C per hour of lead.** A forecast genuinely struggling gets worse with horizon. This one does not,
which points at **calibration, not forecast difficulty.** Usually a small fix.

**Cost to a client: a measured 645 free-cooling hours per year**, because the safety buffer must inflate
from 0.19 °C to 2.30 °C to survive it.

Five alternative explanations were tested and excluded: our request windows, their history being the
culprit, ordinary noise, normal decay with horizon, and choice of statistic. `testing/diag58_*.py`,
`diag60_*.py`.

Full write-up with reproduction payloads in
[`fortyguard-api-findings.md`](../fortyguard-api-findings.md), alongside 16 other characterised defects —
including a **severe credential leak**: `/v1/heat_intelligence` returns the caller's own API key inside a
URL.

**We think this is the most useful thing we can hand FortyGuard: a precise, reproducible, independently
validated diagnosis of the one bug standing between their forecast and mission-critical use.**

---

## Honest status of the safety claim

The agent promises an upper bound on intake temperature, then **measures how often that bound actually
holds.** Current measured result: **65.6 % over 3 test days against a 90 % target.** We publish it, because
a bound whose success rate is asserted rather than measured is worth nothing.

**We diagnosed it — and most of the shortfall is ours, not FortyGuard's:**

| From → to | Cause |
|---|---|
| **90 % → 75 %** | **Our sample size.** A one-sided conformal bound needs **≥ 9 calibration days** to promise 90 %. We had **3**. It was arithmetically impossible from the start. |
| 75 % → 65.6 % | FortyGuard's day-varying offset, above |

**Simulation says ≈10 calibration days recovers 90 % — on pure FortyGuard data, with no customer
hardware.** Collection runs daily. **A local sensor is an optional efficiency upgrade worth ~645 h/yr, not
a requirement for the safety claim.**

**Until those days exist we quote 65.6 %, never 90 %.**

---

## Why this is an agent and not a dashboard

The test we hold ourselves to: **point at the constant.** For any behaviour claimed autonomous, can you
find the number a human typed that produces it? If yes, it is a threshold in a costume.

| | The decision boundary is… |
|---|---|
| A thermostat or hysteresis rule | **two constants a human typed** |
| **INTAKE-ARBITER** | **a surface** computed at runtime from ensemble spread, switch budget and its own coverage record. **Not stored anywhere. Nobody can state it in advance.** |

Three things it does that a dashboard cannot:

- **It grades itself and changes its own behaviour.** Coverage above target → the bound is too fat →
  tighten → more free-cooling hours *earned*. Below → widen. **Nothing tells it to; it derives the
  permission from its own track record** — and that loop is what caught the 65.6 %.
- **It refuses.** The solver models buildings as heat sinks, so when a building sits between exhaust and
  intake its answer is meaningless. Rather than return a wrong number, the agent **declines.** At our first
  candidate site that was **100 % of the wind directions that mattered** — so we changed site rather than
  publish a number the geometry could not support.
- **It shows caution nobody programmed.** Ensemble spread is **27× wider** at the geometric edge than in
  safe sectors. **There is no rule about plumes anywhere in the code.**

**Honest limit:** this is an adaptive controller with a self-calibrating boundary, **not** a stopping rule.
Seven candidate "when to act" decision cores were designed, pre-registered and tested. **All seven
failed** — [PLAN.md](PLAN.md) §6 records each with the number that killed it. **Two failed because of bugs
in our own test code.**

---

## Read this first

**[PLAN.md](PLAN.md)** — the design, the physics, and **§6: the seven decision cores we rejected.** That
section exists because a project showing only what worked is not a research record.

Pre-registrations with amendment logs, **including our own errors found and corrected**:
[`n56-freecooling-PREREG.md`](../n56-freecooling-PREREG.md) (an oracle leak, and a pre-registered
condition that turned out to be unsatisfiable), plus `n45`/`n46`/`n47`/`n49`/`n50`.

---

## Setup

```bash
cp .env.example .env      # then paste the key into .env
```

`.env` is gitignored. **Never paste a key into `.env.example`** — `.gitignore` deliberately re-includes
that template so collaborators can see it, which makes it the one dotfile that *would* be committed.

**Worth knowing before spending anything:** a heatmap call costs **4,220 credits**, the hackathon plan
allows **30 per day**, and **a request can return HTTP 200 with `status: completed` and zero tiles — and is
still billed.** Always assert the response is non-empty.

**Three of the four data layers need no credential at all**, which is why most of this repo runs with no key:

| Layer | Source | Key needed |
|---|---|---|
| Ambient field + **forecast** | FortyGuard Temperature API | yes |
| Wind bearing and speed | NOAA ASOS via Iowa State Mesonet | **no** |
| Real building footprints | OpenStreetMap Overpass API | **no** |
| Aerial imagery | USGS National Map · ESRI World Imagery | **no** |

### ⚠ Credential hygiene — this project has already been bitten

- A key was found hard-coded in two files, caught by a scan **before** the first commit. Scan before you push.
- **FortyGuard's `/v1/heat_intelligence` returns the caller's API key inside the `download_link` URL.** Any
  file caching a raw response can contain a live credential. `data/raw_api/` is gitignored for this reason.

---

## Layout

```
src/  fetch_geometry.py       real Ashburn footprints from OpenStreetMap    (free, keyless)
      select_site.py          geometric gates: true gap, facade orientation, size
      refusal_rank.py         MEASURES where the physics can and cannot answer
      screen_architecture.py  aerial imagery of candidate sites             (free, keyless)
      commit_site.py          final site choice; the scope gate has VETO power
      build_site.py           rasterises real polygons; refuses to write if verification fails
      direction_sweep.py      the refusal surface across 72 wind bearings
      stability.py            Pasquill stability classes over five years
      physics/                the validated solver and its NVIDIA Warp GPU kernel
data/ geometry/  weather/  imagery/
```

## Attribution

Building footprints © OpenStreetMap contributors, ODbL. Weather from NOAA ASOS via the Iowa State
Environmental Mesonet. Imagery from USGS The National Map (public domain) and ESRI World Imagery. Physics
validated against Project Prairie Grass (1956) and CEC-500-2013-065 (public domain). Temperature
intelligence and forecasting from the FortyGuard API.
