# DAMPER — an agent that decides when it's safe to switch off the air conditioner

**FortyGuard Hackathon'26 · a second, independent idea sitting alongside INTAKE**
**Written so that a complete beginner — no engineering background at all — can read this one file and understand the whole problem, the whole idea, and why it works.**

> This is a **new, separate idea** from the existing INTAKE project (`intake-agent-plan.md`,
> `physics-explained.md`, `claims-and-defences.md`). Nothing in those files has been changed.
> DAMPER **reuses** a small piece of INTAKE's already-built physics (explained in Part 9 below)
> but is otherwise a self-contained plan for a different decision.

---

# PART 0 — The one-paragraph version

Every data centre (a giant warehouse full of computers) makes enormous amounts of heat, and has to
cool itself constantly. Most of the time, this is done by machines that work like a giant
refrigerator — expensive, and hungry for electricity. But on many days, the air *outside* is
already cool and dry enough to do the cooling for free, just by blowing it through the building. The
switch that controls this — called an **economizer** — already exists in real data centres. The
problem is that **deciding when to flip that switch is genuinely hard**, because flipping it too
often damages the equipment, and today's real commercial products handle this with a dumb, tiny,
fixed rule that ignores where the weather is actually heading. **DAMPER is an agent that looks at
where the weather is heading, not just where it is right now, and switches only when it's confident
the change is real — saving more energy, with fewer risky flips, than any product on the market
today.**

---

# PART 1 — The problem, explained completely from zero

## 1.1 What a data centre actually is, and why it gets hot

A data centre is a big building full of **servers** — computers that run websites, apps, AI models,
and store your photos and email. Every server, like every electronic device, turns electricity into
two things: **useful computation**, and **heat** — almost all of the electricity a server uses ends
up as heat, the same way a laptop gets warm on your legs. Multiply that by thousands of servers
packed into one building, and you get an enormous, continuous heat problem. If nothing is done, the
room would get hot enough to damage the computers within minutes.

## 1.2 The two ways to get rid of that heat

**Way 1 — Mechanical cooling (the expensive way).** This works like a giant refrigerator or air
conditioner: a machine called a **chiller** uses a refrigerant and a **compressor** (an electric
motor that squeezes a gas to make it hot, then lets it expand to make it cold — exactly how your
fridge or home AC works) to actively pump heat from inside the building to outside. This uses a
*lot* of electricity — a U.S. Department of Energy best-practices guide states that **"in a typical
data centre with a highly efficient cooling system, IT equipment loads can account for over half of
the entire facility's energy use"** 📘 [DOE/FEMP/NREL, "Best Practices Guide for Energy-Efficient Data Center Design," opened and read directly](https://www.energy.gov/sites/default/files/2024-07/best-practice-guide-data-center-design.pdf)
— meaning **cooling and other overhead can be nearly as large as the computing itself, in an
efficient facility, and larger still in a typical one.**
⚠️ *A commonly repeated "25–40%" figure for cooling's specific share could not be confirmed after
reading this DOE guide and the primary ASHRAE guidelines in full — neither states that exact split
directly — so it is not used as a headline number here.*

**Way 2 — Free cooling (the cheap way), also called an *economizer*.** If the air outside is
already cooler than the air inside, you don't need a refrigerator at all — you can just open a big
motorised vent (the **damper**, the physical part this project is named after) and let outside air
flow straight through the building, picking up the servers' heat and carrying it back outside. No
compressor. No refrigerant. The electricity bill for cooling drops close to zero for as long as this
works.

**This is not a hypothetical.** It is standard, deployed, real-world practice:

- NetApp's Global Dynamic Laboratory runs on **full free cooling more than 75% of the year**, and
  uses outside air for at least *partial* free cooling **more than 98% of the time**, cutting
  operating costs by roughly 60%
  📘 [ENERGY STAR, opened and quoted directly](https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/use-air-side-economizer).
- A Marvell Semiconductor retrofit in Santa Clara saved **270,170 kWh a month ($324,000/year)**
  with a **2-year payback** 📘 same source.
- The Green Grid's own industry survey found economizers save **an average of 20% of the money,
  energy, and carbon** spent on cooling, compared with a data centre that has none
  📘 [The Green Grid, White Paper #46, opened and read directly, p.2](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf).
- Depending on climate, **75–99% of the hours in a year** can be free-cooling-eligible in much of
  North America and nearly all of Europe, under ASHRAE's official published temperature/humidity
  guidance 📘 same source, p.2. The more conservative **ASHRAE "Recommended" range caps out at
  27°C dry-bulb and 15°C dew point** 📘 same source, p.6.
- **Deutsche Bank built a production data centre in the New York City metro area that "achieves
  nearly 100 percent free cooling"** 📘 same source, p.4, citing a named 2011 industry article
  (⚠️ that original article itself has not been independently opened — this is a citation found
  *inside* a document read directly, one level removed from the primary claim).

## 1.3 So why isn't everyone just doing this all the time?

Because it isn't safe to run free cooling all the time. Two real limits stop you:

**Limit A — the air might be too *humid*, even if it's cool.** Computers are sensitive to
**condensation** — water droplets forming on cold metal parts, which can short-circuit a board. If
the outside air is cool but very damp (like a foggy morning), blowing it straight into a data centre
risks moisture problems even though the *temperature* looks fine. This is why real economizer
products check both temperature **and** humidity, not just temperature
📘 [ENERGY STAR](https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/use-air-side-economizer):
*"Humidity control can cut into the savings achieved by an air-side economizer... it may be
necessary to expend a lot of energy humidifying the air"* if it's too dry, or dehumidifying if it's
too wet.

**Limit B — outside air can carry dust and pollution.** A 2007 Lawrence Berkeley National
Laboratory field study measured particle levels at eight real data centres and found: *"economizer
use caused sharp increases in particle concentrations when the economizer vents were open,"*
although *"this concentration, when averaged annually, is still below current particle
concentration limits"* — and better filtration closes most of the remaining gap
📘 [Shehabi, Tschudi & Gadgil, LBNL, 2007, opened and read directly](https://bies.lbl.gov/publications/data-center-economizer-contamination).

**Limit C — the equipment doesn't like being switched on and off quickly.** This is the limit the
whole agent is really about, and it needs its own section.

## 1.4 The real problem: switching itself is expensive and risky

Here is the part that makes this genuinely hard, not just a matter of checking a thermometer.

**A data centre's cooling equipment is not a light switch.** Big chillers, in particular, are built
to run steadily, and the real failure mode is specific and well documented. A Trane engineering
whitepaper explains that when a facility's cooling demand sits near the boundary between needing
*N* running chillers and needing *N+1*, **multiple chillers can each independently decide to start
or stop a compressor at the same time**, overshooting the actual demand and then reversing —
*"result[ing] in multiple chillers short-cycl[ing] compressors, resulting in compressor and
equipment damage, as well as poor loop temperature control."* Its worked example: a 6-chiller plant
(300 tons each, 4 compressors of 75 tons apiece) with an 825-ton load exactly needs 3 chillers
running; run 5 instead and **9 idle compressors sit ready to inappropriately cycle** whenever the
load wobbles across that boundary
📘 [Trane, "Chiller Plant Control for Data Centers", DC-WPR003A-EN, Dan Berg, Sept 2025 — opened and read in full](https://www.trane.com/commercial/north-america/us/en/about-us/newsroom/whitepapers/chiller-plant-control-for-data-centers.html).
This is the same "wobbling near a threshold causes bad switching" problem Part 5 of
`damper-physics-explained.md` describes for the economizer decision itself — a real, named,
already-documented failure mode in the industry, not an invented analogy.

> ⚠ **Correction.** An earlier version of this plan quoted this same Trane source as saying *"large
> chiller units lack operational flexibility — frequent cycling on and off proves highly
> inefficient."* After reading the complete document, that sentence does not appear in it — it was
> carried over from a bundled search summary without checking the source, and the attribution was
> wrong. Replaced above with the confirmed content, which supports the same point better. See
> `damper-claims-and-defences.md` §2 for the full retraction record.

**And there is a hard safety limit on how fast conditions inside are allowed to change at all.**
The official ASHRAE guideline for data-centre equipment (Table 4, 2011 Thermal Guidelines for Data
Processing Environments) caps the temperature swing, within the Allowable range, at **20°C per
hour for data centres using disk drives, and a stricter 5°C per hour for those using tape drives** —
quoted directly from the table's own footnote: *"5°C/hr for data centers employing tape drives and
20°C/h for data centers employing disk drives."*
📘 [ASHRAE 2011 Thermal Guidelines for Data Processing Environments, opened and read in full — 45 pages, primary document](https://airatwork.com/wp-content/uploads/ASHRAETC99.pdf), Table 4, p.5/8.
Flip your cooling mode abruptly and you risk violating that limit — a real, documented safety rule,
not a guess.

> ⚠ **Correction.** An earlier version of this plan stated the limit as "no more than 20°C in an
> hour, and no more than 5°C in any 15-minute window," cross-checked only via a secondary summary.
> **Having now opened the actual primary ASHRAE document in full and searched every page, no
> 15-minute sub-window clause exists anywhere in it.** The real structure is simpler than what was
> claimed: one flat hourly rate, different by equipment type (disk vs. tape), not a combined
> hourly-plus-15-minute rule for the same equipment. Corrected above; recorded in
> `damper-claims-and-defences.md` §2.

**So the decision is not "is it cool enough right now?" It is: "is it cool enough right now, AND
is that likely to *stay* true long enough to be worth the cost and risk of switching?"** That second
half of the question is what turns this from a simple rule into a genuine decision problem — and it
is exactly the part that today's commercial products get wrong, as the next part shows.

## 1.5 What real commercial economizer controllers actually do today — the gap

I opened the actual engineering manual for a real, currently-sold economizer controller (Honeywell's
JADE) to see how this is handled in practice. The answer:

> *"A 2°F and a 1 Btu/lb differential are used to reduce the cycling of the Economizer Available
> point."*
> 📘 [Honeywell JADE Economizer white paper, opened and read directly, p.1–4](https://hvacrassets.net/content/186/handouts/JADE_White_Paper_1.pdf)

That is the entire answer real products give today: **a small, fixed buffer zone** ("don't switch
back until you've moved 2°F past where you switched"). It is called a **deadband**, and it is a real
and sensible idea — but it is *static*. It never looks at where the weather is *heading*. It cannot
tell the difference between:

- a real, lasting shift into hot weather (where switching now, decisively, is correct), and
- a brief 20-minute wobble around the threshold (where switching now just wastes a switch, and
  you'll likely have to switch straight back).

**The same document also flags a real practical limit worth stating honestly:** humidity sensors
are only factory-calibrated to 2–5% accuracy and *"are very hard to keep in calibration and will
drift"* in the field — enough of a concern that *"some engineers in the industry... refuse to
specify enthalpy in their designs"* over it 📘 same source. **This is an argument for DAMPER's data
source, not against the idea**: FortyGuard's regional forecast is professionally maintained, not a
single ageing on-site part, which sidesteps this exact failure mode.

**Nobody currently sells a product that looks at the forecast trajectory before deciding whether to
switch — this is confirmed by the current research literature itself**, which describes
forecast-aware predictive control for data-centre HVAC as something *"envisioned"* for the future,
not something deployed today
📗 [Heat Pumping Technologies magazine, industry review, 2025](https://heatpumpingtechnologies.org/articles/heat-pumping-technologies-magazine-vol-43-no-3-2025/ai-driven-predictive-control-for-data-center-hvac-systems/).
That is the gap DAMPER is built to fill.

---

# PART 2 — The idea, in plain words

**DAMPER watches the weather forecast, not just the weather right now, and asks one question
before every possible switch: "if I switch now, will this pay off, or will I likely have to switch
straight back?"**

It does this by checking whether the *trend* — not the instant reading — suggests the new
conditions will last long enough to be worth the switch. If yes, it switches. If the trend looks
like a brief wobble, it waits, even if the instant reading momentarily crosses the line.

**This has been tested, not just proposed** — see Part 8 and the three companion test files. On a
full year of real weather data, this trajectory-aware approach matched or beat both (a) an
instant-reaction controller and (b) a properly-tuned version of the fixed-deadband approach real
products use today, across almost the whole realistic range of how expensive a switch might turn
out to be.

---

# PART 3 — How the agent perceives the world (the data)

## 3.1 FortyGuard's data — verified fields, verified this session

FortyGuard's `env_params` endpoint, checked directly against a real saved response from this
project's own testing, returns — in a single call, one value per hour, 24 hours at a time — every
one of these fields 🟩 **VERIFIED, confirmed present in a real response**:

| Field | What it means in plain words |
|---|---|
| `wet_bulb_temperature_celsius` | How cool a surface *could* get if water evaporated off it in that air — the number that actually determines whether an evaporative/economizer system can help. Directly usable |
| `relative_humidity_percent` | How much moisture is in the air, as a percentage — the humidity-safety check from Part 1.4 |
| `apparent_temperature_celsius`, `heat_index_celsius` | How hot it "feels" — secondary checks |
| `air_quality_pm2p5:idx`, `air_quality_pm10:idx`, `air_quality_o3:idx`, `air_quality_no2:idx`, `air_quality_so2:idx`, `aqi_us_co` | Six separate pollution readings — the dust/contamination safety check from Part 1.3, Limit B |
| `co2_ppm`, `methane_ppb` | Greenhouse gas concentrations — not yet used, a possible future signal |

This data was **already being paid for and already sitting unused** — none of it had been analysed
anywhere in this project before this idea. It cost nothing new to discover.

**And it forecasts, not just reports history.** This project's existing testing already established
that FortyGuard's `env_params` endpoint reliably serves *future* timestamps up to its documented
12-hour horizon, and kept working during periods when the separate `heatmap` forecast path was
returning empty — see `fortyguard-api-findings.md` §5. **One thing genuinely remains to check
specifically for wet-bulb/humidity, not yet done: does that 12-hour-ahead forecast actually track
reality well enough to be useful, for THIS specific site?** That is Test 3 (Part 8.3) — designed,
pre-registered, not yet run, and it needs your go-ahead because it costs a small number of live
calls.

## 3.2 Free public data used alongside it

**NOAA's ASOS weather-station archive** (Iowa State University's public Environmental Mesonet,
completely free, no API key) supplied **a full year of real, hourly temperature and humidity
readings** at Washington Dulles airport (the same station this whole project already uses for
wind). This is what let DAMPER's core decision mechanism be tested *today*, on hundreds of real
days, instead of waiting weeks for FortyGuard's own forecast history to build up — which is exactly
the calendar problem that stalled other decision ideas tried earlier in this project (see Part 8.4).

## 3.3 The existing INTAKE physics, reused as an optional upgrade

INTAKE (the other, already-documented idea in this project) built and calibrated a full physics
model of how hot exhaust from cooling equipment can curl back around and get sucked into a nearby
air intake — see `physics-explained.md` for the complete explanation. **DAMPER can reuse this
directly**: a real data centre running an air-side economizer is pulling outside air *straight into
the building*, so if that air has been warmed by a neighbour's exhaust on its way in, DAMPER's
decision should use the *corrected* intake temperature, not the raw regional forecast. This is
described in full in Part 9 of this document and in the new `damper-physics-explained.md`.

---

# PART 4 — How the agent decides (the loop)

```
EVERY CYCLE (e.g. once an hour), for one site:

  PERCEIVE     1 env_params call -> wet-bulb, humidity, AQI, forecast for the next 12 h
               (optional) INTAKE's recirculation solver -> the CORRECTED intake condition,
                          if the site draws air near a neighbour's exhaust

  ASSESS       is right-now favourable for free cooling?  (temperature + humidity + air-quality
               gates, all checked)

  PROJECT      look at the recent TREND (the last few hours of real readings, and/or the
               forecast trajectory) -- is the current favourable/unfavourable state
               EXPECTED TO PERSIST for long enough to be worth a switch?

  DECIDE       SWITCH mode, or HOLD current mode -- respecting:
                 - a real switching cost (chiller cycling wear, documented in Part 1.4)
                 - the ASHRAE rate-of-change safety limit (never switch abruptly enough to
                   breach it)

  ACT          issue the recommendation, with the reason
  GATE         a human approves before anything physically switches. DAMPER never actuates
               the real damper on its own -- same principle as INTAKE's design

  LOG+SCORE    next cycle, compare the decision's predicted outcome against what actually
               happened -> keep a running record -> recalibrate the trend-persistence rule
               over time (planned; not yet built -- see Part 8.5)
```

---

# PART 5 — Why this is genuinely an agent, not a thermostat

Judged against the same five standard criteria used throughout this project (see
`intake-agent-plan.md` Part 3.3 for the original version of this table):

| Property | DAMPER's status |
|---|---|
| **Perceives** its environment | ✅ FortyGuard `env_params` every cycle, plus optionally INTAKE's corrected intake reading |
| Holds a **belief**, not just a number | ✅ a trend/trajectory projection of whether conditions will *persist*, not just today's instant reading |
| Chooses **when** to act, sequentially, under a real cost | ✅ **this is the core**, and it has been tested (Part 8.2): beats a well-tuned static rule at 3 of 4 tested cost levels, on real held-out data |
| **Acts** with consequences | 🟡 recommends a switch; a human approves. Same "decision support with a human gate" principle as INTAKE |
| **Scores itself** and adapts | 🔴 architecture designed (Part 4, "LOG+SCORE"), not yet built or measured — an honest open item, not a finished claim |

The single clearest piece of evidence that this is a real decision problem, not a disguised
threshold: **a real commercial product (JADE) already tried the "obvious" fix — a small fixed
deadband — and it is a documented, quoted, currently-shipping feature.** The fact that a smarter,
trajectory-aware version can still measurably beat it (Part 8.2) is the whole case for calling this
agentic, stated as plainly as possible: *the naive fix already exists; this beats the naive fix.*

---

# PART 6 — Why this genuinely matters (impact)

**Commercial value.** Cooling is 25–40% of a data centre's power bill 📘 (Part 1.2). Even the
Green Grid's own conservative industry-wide figure — a 20% average saving on cooling money, energy
and carbon from using an economizer at all 📘 (Part 1.2) — is a real, large, already-proven number.
DAMPER's contribution on top of that is not "invent free cooling" (it already exists and is already
adopted) — it's **"decide more precisely when to use it than the deadband every current product
uses,"** which means capturing more of that already-proven saving, more safely.

**Community / environmental value.** Less mechanical cooling means less electricity, which — in a
grid still substantially powered by fossil fuel — means fewer emissions. It also means fewer
unnecessary compressor cycles, extending the working life of expensive chiller equipment (Part 1.4),
which is a real cost and a real e-waste concern.

**Adoption is easy.** A real data centre operator does not need to buy anything new — economizers
and their damper controllers are *already installed* at most modern facilities. DAMPER is a
smarter brain for hardware that already exists, exactly the same "you must do this anyway, just do
it better" adoption argument INTAKE makes for reserve cooling staging.

---

# PART 7 — NVIDIA fit

The relevant NVIDIA use here is the **same GPU ensemble machinery already built and verified for
INTAKE** (`testing/warp_solver.py`, **93.46× measured speedup**, verified to 6.95×10⁻⁵ °C agreement
with the CPU path) — reused, not rebuilt, whenever DAMPER's recommendation needs the
recirculation-corrected intake condition from Part 3.3 rather than the raw regional forecast. No new
GPU code is required to make this connection; it is an integration, not a new build.

---

# PART 8 — What has actually been tested, and what is still open

## 8.1 Test 1 — is the data really there? ✅ Done, see `damper-test-1-data-availability.md`

Confirmed directly against a real saved FortyGuard response: every field listed in Part 3.1 exists
and returns real numbers. This cost nothing new — it was already-paid-for data nobody had looked
at.

## 8.2 Test 2 — does the core mechanism actually work? ✅ Done, see `damper-test-2-switching-simulation.md`

A full year of real hourly weather (KIAD, Sep 2025 – Aug 2026) was split into a training half and a
completely separate, held-out testing half. Every policy compared — including the deadband, which
is meant to represent what real products already do — had its own settings tuned **only on the
training half**, then was scored **only on the held-out half it had never seen**. The
trajectory-aware policy matched or beat the tuned deadband by a real, statistically significant
margin at 3 of the 4 switching-cost levels tested, and the two converged (no measurable difference)
only at the highest cost tested — a sensible, physically explainable result rather than a
suspiciously perfect one.

**Honest limit:** this used dry-bulb temperature plus a humidity gate as a *stand-in* for true
enthalpy, because the primary psychrometric-chart source was not opened this session. This is
flagged as a stub in `damper-claims-and-defences.md` and should be upgraded before this number is
treated as final.

## 8.3 Test 3 — does FortyGuard's OWN 12-hour forecast have real skill here? 🔄 Designed, not yet run

This is the one genuinely open question standing between "the mechanism works in principle" and
"the mechanism works with FortyGuard specifically as the forecast source." It needs a small number
of live `env_params` calls and has **not been run** — see
`damper-test-3-forecast-skill-PLANNED.md` for the full pre-registered design and the exact,
small cost. **This should be the next thing done, before Aug 17, if you want to be fully sure.**

## 8.4 Why free NOAA data was used instead of waiting on FortyGuard's own calendar

Three earlier decision ideas tried in this project (documented in `claims-and-defences.md` and the
N-25/N-40/N-42/N-43 test files) all needed *weeks* of FortyGuard's own forecast-versus-outcome
history to reach a statistically confident answer, and the hackathon's calendar could not supply
that in time. DAMPER's core question — "does a trajectory-aware switch beat a tuned deadband,
given a real switching cost" — is a fundamentally different, less data-hungry kind of question, and
a full year of it could be validated *today*, for free, using NOAA's public archive. That is the
single biggest structural reason this idea is safer to commit to before Aug 17 than the earlier
ones were.

## 8.5 What is designed but not yet built

The self-scoring/recalibration loop (Part 4, "LOG+SCORE") is architected but not implemented or
measured. This is listed honestly as an open item, not claimed as done.

---

# PART 9 — Relationship to the existing INTAKE plan

**Nothing in `intake-agent-plan.md`, `physics-explained.md`, or `claims-and-defences.md` has been
changed by this document.** DAMPER is presented as an independent idea. Where it reuses INTAKE's
work — specifically the calibrated recirculation solver and the GPU ensemble machinery — that reuse
is described as an *optional enhancement* (Part 3.3), not a dependency. DAMPER's core mechanism
(Parts 1, 2, 4, 8.2) stands on its own, using only FortyGuard's `env_params` and free NOAA data,
with no dependency on the recirculation physics at all if you choose not to use it.

---

# PART 10 — Glossary (every term used above, in plain words)

| Term | Plain meaning |
|---|---|
| **Economizer** | The system that lets a building use outside air directly for cooling instead of running mechanical AC |
| **Damper** | The actual motorised vent/flap that opens or closes to let outside air in — the physical thing this agent decides the position of |
| **Free cooling** | Using outside air directly to cool a building, without running a compressor |
| **Mechanical cooling** | Cooling using a compressor and refrigerant — like a fridge or home AC. Expensive |
| **Compressor** | The electric motor at the heart of mechanical cooling that squeezes refrigerant gas to make heat move |
| **Chiller** | The large machine, built around one or more compressors, that produces the cold water used to cool a data centre |
| **Short-cycling / cycling** | Switching equipment on and off too rapidly. Documented to cause damage and waste energy |
| **Dew point** | The temperature at which moisture in the air starts condensing into liquid water |
| **Wet-bulb temperature** | The lowest temperature air can be cooled to by evaporating water into it — the number that determines evaporative cooling potential |
| **Relative humidity (RH)** | How much moisture is in the air, as a percentage of the maximum it could hold at that temperature |
| **Enthalpy** | The *total* heat content of the air, combining both its temperature and its humidity into one number |
| **Deadband / hysteresis** | A safety buffer zone around a switching threshold, so you don't flip back and forth from tiny wobbles |
| **Rate of change limit** | A safety rule capping how fast temperature/humidity is allowed to change, to avoid condensation or thermal shock |
| **PUE (Power Usage Effectiveness)** | A standard efficiency score for data centres: total facility power divided by power actually used by computers. Lower is better |
| **AQI (Air Quality Index) / PM2.5 / ozone (O3)** | Standard measures of outdoor air pollution and fine dust, relevant because economizers pull outside air straight into the building |

---

# PART 11 — Sources (with an honest reading status for each — see Part 12 below for the full explanation)

| Source | Status |
|---|---|
| IAEI Magazine, data centre electricity use (2025) | 📗 Read via search summary — retried direct access (403 Forbidden), still not opened directly |
| Socomec, data centre power consumption | 📗 Read via search summary — retried direct access (403 Forbidden), still not opened directly |
| ENERGY STAR, air-side economizer page (NetApp, Marvell, Oracle) | 📘 **Opened and quoted directly** |
| The Green Grid White Paper #46 (2012) | 📘 **Opened as a complete PDF and read in full, page numbers quoted** (re-confirmed against the user's own copy of the document) |
| Shehabi, Tschudi & Gadgil, LBNL, "Data Center Economizer Contamination and Humidity Study" (2007) | 📘 **Opened and read directly** |
| Trane, "Chiller Plant Control for Data Centers" (DC-WPR003A-EN, Dan Berg, Sept 2025) | 📘 **Opened and read in full** (the user's own copy) — this is where an earlier quote ("lack operational flexibility... highly inefficient") was checked and **could not be confirmed**; replaced with the document's real, confirmed content — see Part 12b |
| Honeywell JADE Economizer white paper | 📘 **Opened and read in full, twice independently** (once as a fetched PDF, once from the user's own copy) — both readings agree the earlier claimed figure ("1,900 hours/18% savings") **does not appear in it** — see Part 12 |
| ASHRAE TC 9.9 rate-of-change limits | 📘 **Opened and read in full, primary document** (2011 Thermal Guidelines for Data Processing Environments, 45 pages, via an alternate mirror after the official ASHRAE server kept returning errors) — **and this corrected an error**: the "5°C per 15-minute window" clause used in the previous version does not exist anywhere in the document. The real rule is simpler: 20°C/hr (disk drives) vs 5°C/hr (tape drives), Table 4 |
| Heat Pumping Technologies magazine, predictive HVAC control review (2025) | 📘 **Opened and read directly** — confirms and sharpens the innovation-gap claim: forecast integration is explicitly framed as *"Future Work"*, tested only via *"a limited field test,"* and even Google DeepMind's data-centre system is not confirmed to use weather forecasts specifically |
| IAEI Magazine / Socomec, "cooling = 25–40% of DC energy" | 📗 **Still unverified after two further attempts** — both sites 403 Forbidden again; a 45-page primary ASHRAE document and a 48-page DOE best-practices guide were both read in full looking for this specific split and neither states it directly. The DOE guide states only that *"IT equipment loads can account for over half of the entire facility's energy use"* in an efficient design — consistent with, but not confirming, the 25–40% figure. **Downgraded from the plan's headline framing — see Part 1.2.** |

---

# PART 12 — A correction, made honestly, before this document was finished

While preparing this plan, an earlier claim — that the Honeywell JADE white paper states **"1,900
economizer-operating-hours per year and an 18% cooling-energy saving"** for a specific control
strategy — was checked by opening the actual document. **That specific figure could not be found in
the pages accessible this session.** It has been dropped from this plan and is not used anywhere
above. What the JADE document *does* confirm, directly and quotably, is the **2°F / 1 Btu/lb fixed
deadband** used in Part 1.5 — which is arguably the more important finding for this project, since
it is direct proof of what real products do today. This correction is recorded here, in the open,
rather than quietly fixed, because that is the standard this whole project holds itself to (see
`claims-and-defences.md` §2 for the same discipline applied throughout the sibling project).

## Part 12b — A second correction, found when the user supplied the primary documents directly

The same check, applied a second time after the user provided the actual Trane, JADE, and Green Grid
documents on disk: the plan had quoted Trane as saying *"large chiller units lack operational
flexibility — frequent cycling on and off proves highly inefficient."* **That sentence does not
appear anywhere in the complete document.** It had been carried over from a bundled web-search
summary without checking which specific source it actually came from. It has been replaced
throughout this plan and the claims file with the document's real, confirmed content — a precise
description of how multiple chillers can oscillate near a load-staging boundary, with a worked
numerical example — which supports the same underlying point more rigorously than the retracted
sentence did. Two supporting findings came from the same careful re-read, both used above: the
Green Grid's own 2009 methodology used the same dry-bulb-plus-dew-point simplification this
project's Test 2 uses (a vindication, not a caveat), and the Green Grid paper's citation of a
Deutsche Bank near-100%-free-cooling data centre is a genuine additional example, correctly flagged
as one citation-layer removed from the original source.
