# The Physics and Decision Logic Behind DAMPER, Explained From Zero

**What this document is.** Every concept DAMPER's decision depends on, explained assuming you know
*nothing* about HVAC, weather science, or control theory. No code. Diagrams are plain text (ASCII)
so they render in any markdown viewer. Same honesty-tagging system used throughout this project:

| Tag | Meaning |
|---|---|
| 🟩 **VERIFIED-MATH** | Checked against exact mathematics. Cannot be wrong unless the maths is wrong |
| 📘 **SOURCED** | From a document I opened and read directly this session, quoted |
| 📗 **NAMED-SOURCE** | Cross-checked via search summaries or secondary sources, not the primary document itself |
| 🔧 **FITTED** | Chosen by fitting to real measured data |
| ✏️ **OURS** | Our own choice, stated as a stub, swept across a range rather than asserted as one number |
| 🔴 **GAP** | Something known to be missing or simplified, stated deliberately |

**Is this the same physics as `physics-explained.md`?** **No — it is different physics, for a
different decision.** `physics-explained.md` is entirely about how hot exhaust air *travels through
the outdoor air* and curls back into an intake (fluid dynamics: advection, diffusion, plumes). This
document is about **the properties of the air itself** — how hot and how wet it is — and **when it
is safe and worthwhile to use it directly for cooling**. The two do connect, at one specific point
(Part 6 below), where DAMPER can optionally borrow INTAKE's already-built plume physics — but the
core mechanism explained here is new and not covered anywhere in the existing document.

---

# Part 1 — What "hot" actually means: temperature is not the whole story

## 1.1 Two kinds of air that feel completely different at the same temperature

Imagine two rooms, both exactly 20°C:

- **Room A** is bone dry (like a desert). It feels comfortable, maybe even a little cool.
- **Room B** is thick with moisture (like a rainforest, or right after a hot shower). At the *same*
  20°C, it feels sticky, heavy, harder to cool anything down in.

**Temperature alone does not tell you how good that air is at cooling something down.** You need a
second number: **how much water vapour is already in the air.**

## 1.2 Relative humidity — the number that captures "how wet"

**Relative humidity (RH)** is a percentage: how much water vapour is in the air right now, compared
to the *maximum* it could possibly hold at that exact temperature before it starts condensing into
liquid droplets.

- **0% RH** = bone dry air, no moisture at all.
- **100% RH** = the air is completely saturated — any more moisture and it starts turning into fog,
  dew, or rain.

Warm air can hold *much* more moisture than cold air before hitting 100% — which is why a foggy
morning (cold air, near 100% RH) can hold far less actual water than a humid summer afternoon (hot
air, same 100% RH) even though both are "100% humid."

## 1.3 Dew point — the temperature where condensation starts

The **dew point** is a simpler way to say almost the same thing: it's the temperature the air would
need to be cooled *to* before water starts condensing out of it — the same fog that forms on a cold
glass of a drink on a humid day. **A high dew point means genuinely a lot of moisture in the air,
regardless of the current temperature.** This matters because condensation inside a data centre —
water droplets landing on circuit boards — is a real equipment-damage risk, not a comfort issue.

## 1.4 Wet-bulb temperature — the single most useful number for this whole problem

Imagine wrapping a wet cloth around a thermometer and letting a fan blow air past it. Water
evaporates off the cloth, and evaporation *always* cools things down (this is why sweating cools
your skin) — so that thermometer reads a *lower* number than a normal, dry thermometer sitting right
next to it. **That lower reading is the wet-bulb temperature.**

- If the air is very dry, water evaporates off the cloth fast, cooling it a lot → wet-bulb is
  **much lower** than the normal (dry-bulb) temperature.
- If the air is already soaked with moisture (near 100% RH), almost no more water can evaporate off
  the cloth → wet-bulb is **almost the same** as the dry-bulb temperature.

**Why this is the single most useful number here:** it tells you, in one measurement, the coolest
temperature you could realistically get *by evaporating water into that air* — which is exactly what
some cooling systems do on purpose (evaporative/water-side cooling), and it's a strong proxy for how
much "cooling potential" the outside air holds even for plain air-side free cooling. FortyGuard's
`env_params.wet_bulb_temperature_celsius` field gives this directly, already calculated — no need to
compute it by hand. 🟩 Confirmed present in a real saved response (see `damper-agent-plan.md` Part
3.1).

## 1.5 Enthalpy — the most complete (and most complicated) number

**Enthalpy** combines temperature *and* humidity into a single number representing the *total* heat
energy stored in a parcel of air — both the "obvious" heat you can feel (temperature) and the
"hidden" heat locked up in water vapour (this hidden heat is very real: it's the same energy that
gets *released* when steam condenses back into water, which is why a steam burn is so much worse
than a boiling-water burn at the same temperature).

**Diagram — the psychrometric idea, simplified:**

```
                    HUMIDITY (how much moisture the air holds)
                    ^
             100% RH|.........................
                     |    TOO WET ZONE          |
                     |   (skip free cooling --   |
              80% RH |    condensation risk)  ___|
                     |                     __/
                     |     THE SAFE       /
                     |   FREE-COOLING    /
                     |      WINDOW      /
                     |   (cool AND     /
                     |    dry enough) /
                     |_______________/________________________>
                          cold                        hot        TEMPERATURE
                    (always fine,             (too hot no matter
                     if dry enough)            how dry -- use
                                                mechanical cooling)
```

**A real, published, industry-standard version of this exact chart exists** — the "psychrometric
chart" used throughout HVAC engineering, and real economizer products (like the Honeywell JADE
system described in Part 4) draw curved boundary lines directly on this chart to decide when free
cooling is allowed 📘 [Honeywell JADE white paper, opened and read directly](https://hvacrassets.net/content/186/handouts/JADE_White_Paper_1.pdf).

**Simplification used in this project's own feasibility test** 🟡: rather than computing true
enthalpy (which needs a full psychrometric formula), the first feasibility test approximated the
"safe window" using **dry-bulb temperature plus a relative-humidity gate** — a two-part rule instead
of one smooth enthalpy curve. **This turns out to match the industry's own standard methodology,
not just a convenient shortcut**: the Green Grid's own official 2009 free-cooling maps — still the
reference maps cited by ASHRAE-adjacent guidance today — were built the same way: *"for each hour
where average dry bulb and dew point temperatures are below the ASHRAE recommended maximums, an
hour is added to the possible free cooling hours"*
📘 [The Green Grid White Paper #46, opened and read in full, p.6](https://datacenters.lbl.gov/sites/default/files/WP46UpdatedAirsideFreeCoolingMapsTheImpactofASHRAE2011AllowableRanges.pdf).
The same source gives the actual ASHRAE **Recommended** range this simplification approximates:
**max dry-bulb 27°C, max dew point 15°C** (p.6) — and the feasibility test's own threshold, tuned
purely by minimising simulated cost on a year of real weather with no knowledge of this number,
came out at **26.0°C**, within 1°C of the independently published figure. **Still true enthalpy is
the more complete, and eventually preferable, calculation** — this remains a real simplification,
just a well-precedented one rather than an unusual shortcut. See `damper-claims-and-defences.md`
§1.5.

---

# Part 2 — Why cool, dry outside air can cool a building "for free"

This part needs no advanced physics — just one basic rule everyone already knows:

> **Heat always flows from hot to cold, on its own, with no machine needed.**

A data centre full of servers is hot. If the air *outside* is cooler than the air *inside*, you can
just let outside air flow through the building: it picks up heat from the hot equipment (getting a
little warmer itself) and carries that heat back outside when it leaves. **No compressor, no
refrigerant, no motor doing the hard work of pumping heat uphill (from cold to hot) — the heat is
moving downhill (from hot to cold) on its own,** the same way a cup of tea sitting in a cool room
loses its heat to the air around it without any machine helping.

**Mechanical cooling (Way 1 in `damper-agent-plan.md` Part 1.2) has to do the opposite: pump heat
from somewhere cold (inside the servers) to somewhere hot (outside on a summer day) — pushing heat
"uphill", against its natural direction.** That is inherently harder and needs real energy input (the
compressor). This is why free cooling, whenever it's available, is so much cheaper: it's just letting
physics do something it already wants to do.

---

# Part 3 — The economizer: the mechanism that switches between the two

**Diagram — what an air-side economizer physically does:**

```
  MODE 1 — FREE COOLING (damper OPEN)
  ------------------------------------
  outside air ---> [DAMPER: OPEN] ---> flows through the room full
  (cool, dry                            of hot servers, picks up
   enough)                              their heat, flows back
                                        outside carrying that heat away.

                    compressor: OFF.  Electricity for cooling: near zero.


  MODE 2 — MECHANICAL COOLING (damper CLOSED, or nearly so)
  -----------------------------------------------------------
  outside air ---> [DAMPER: CLOSED] --X   room air is cooled by
  (too hot or                              a chiller (compressor +
   too humid)                              refrigerant), then
                                            recirculated inside.

                    compressor: ON.  Electricity for cooling: full price.
```

The **damper** is a real, physical, motorised flap or louvre. This project's agent is named after
it because deciding its position — open, closed, or somewhere in between — every cycle, is
literally the decision DAMPER makes.

---

# Part 4 — How real commercial economizer controllers decide today

Reading the actual engineering manual for a real, currently-sold controller
(Honeywell's JADE, 📘 opened and read directly this session) shows there are several real control
strategies in active industrial use, not just one:

| Strategy | What it compares | In plain words |
|---|---|---|
| **Dry-bulb** | Outside temperature vs. one fixed setpoint | "Is it below X degrees outside? If yes, open the damper." Simplest, ignores humidity entirely |
| **Differential dry-bulb** | Outside temperature vs. the building's own *return* air temperature | "Is outside actually cooler than what's already inside?" A smarter, self-adjusting version of the above |
| **Single enthalpy** | Outside air's total heat content vs. a fixed setpoint curve | Accounts for humidity, not just temperature |
| **Differential enthalpy** | Outside air's total heat content vs. the building's own return air | The most complete of the standard strategies |

**And crucially, real commercial products already know that switching too often is a problem, and
already build in a fix — but a very simple one:**

> *"A 2°F and a 1 Btu/lb differential are used to reduce the cycling of the Economizer Available
> point."*
> 📘 Honeywell JADE white paper, p.1–4 (opened directly)

This fixed buffer zone is called a **deadband** (or **hysteresis**), and it is explained properly in
Part 5. **The gap DAMPER fills is not "no one has thought about switching costs" — they clearly
have. The gap is that the fix used today is a small, fixed, one-size-fits-all number, and it never
looks at where the weather is actually heading.**

---

# Part 5 — The deadband problem, and why "looking ahead" beats it

## 5.1 Why switching a naive on/off rule too fast is a real cost

Imagine a rule: *"switch to free cooling the instant outside temperature drops below 21°C."*

Real weather doesn't move in a smooth, single direction — it wobbles. If the temperature spends an
hour drifting back and forth across 21°C (completely normal, especially at sunrise or during a
passing cloud), a naive instant-reaction rule will flip the damper open and closed **many times in
that single hour.** Each flip:

- Risks breaching the ASHRAE rate-of-change safety limit (`damper-agent-plan.md` Part 1.4).
- Adds wear to chiller/compressor equipment that engineering guidance explicitly says should not be
  cycled frequently 📘 (Trane whitepaper, Part 1.4).

## 5.2 The deadband fix, and its own weakness

**Diagram — three approaches to the same wobbly day:**

```
   Outside temperature through one representative day:

    Temp
     |                     ___
     |                    /   \
     |‥‥‥‥‥‥‥‥‥‥‥‥‥‥‥‥‥/‥‥‥‥‥\‥‥‥‥‥‥‥‥‥‥‥‥‥‥‥‥  <- the threshold line
     |               /            \
     |             /                \
     |___________/____________________\_____________  time ->
        morning     midday not-quite-hot      evening


   NAIVE (switches the INSTANT the line crosses the threshold):
     reacts to every wobble near the crossing -- can flip back and
     forth several times in a single hour if the line hovers near
     the threshold. Fast to react to REAL changes, but jumpy on
     small ones.

   DEADBAND / HYSTERESIS (only switches once safely PAST the line
   by a fixed buffer, e.g. Honeywell's 2 F):
     ignores small wobbles near the threshold -- fewer switches.
     BUT it also reacts slower to REAL, lasting changes, because
     it insists on waiting for the buffer to clear even when the
     change is obviously real and here to stay. Can sit in the
     "wrong" mode for a while, wasting free-cooling opportunity.

   DAMPER'S APPROACH (checks whether the RECENT TREND says the
   new conditions will actually persist for the next few hours,
   before committing to a switch):
     ignores brief wobbles (like the deadband does), BUT switches
     promptly once the trend confirms a real, lasting change
     (unlike the deadband, which always waits for the same fixed
     buffer regardless of how obvious the trend already is).
```

## 5.3 Why this is provably not just a fancier threshold

A critic might ask: *"isn't checking the trend just another kind of instant rule?"* No — and here is
the precise reason. A threshold rule, however clever, only ever looks at **where the reading is
right now** (possibly compared to a fixed buffer). DAMPER's rule looks at **where the reading is
heading** — a genuinely different kind of information, only available by using several recent
readings (or a forecast) together, not a single instant snapshot. **This has been tested against a
properly, fairly-tuned deadband — not a strawman — on a full year of real, held-out weather data,
and it wins by a real statistical margin at most of the switching-cost levels tested.** Full details,
numbers, and the honest limits of that test are in `damper-test-2-switching-simulation.md`.

---

# Part 6 — Where this connects to INTAKE's existing physics (optional, not required)

`physics-explained.md` (INTAKE's physics document) explains, in full, how hot exhaust air from
cooling equipment can spread through the outdoor air and curl back into a nearby air intake —
governed by the standard **advection-diffusion equation** and calibrated against ~40,000 real
measurements from six instrumented power-station condensers.

**Why DAMPER can use this:** a data centre running an air-side economizer is, by definition, pulling
outside air *straight into the building*. If that outside air has already been warmed by a
neighbouring facility's exhaust on its way in — exactly the effect INTAKE's whole physics stack was
built to calculate — then the *true* temperature and humidity arriving at the intake is not quite
the same as the regional forecast. **DAMPER's decision can optionally use INTAKE's
already-calibrated, already-GPU-accelerated corrected value instead of the raw forecast, with zero
new physics code required.** This is a genuine, free upgrade path, not a requirement — DAMPER's core
mechanism (Parts 4–5 above) works completely on its own using only the raw forecast.

**Nothing about this changes or duplicates anything in `physics-explained.md`.** For the full
mathematics of the recirculation physics itself, that document remains the single source of truth.

---

# Part 7 — The safety rule that limits how fast DAMPER is allowed to switch

Real data-centre equipment has a documented limit on how fast its environment is allowed to change,
independent of any cost argument — this is a **safety** rule, not an efficiency one:

> **No more than 20°C of temperature change in any one hour, for data centres using disk drives —
> and a stricter 5°C per hour for those using tape drives.**
> 📘 Opened and read in full, ASHRAE 2011 Thermal Guidelines for Data Processing Environments
> (45 pages), Table 4, quoted directly: *"5°C/hr for data centers employing tape drives and 20°C/h
> for data centers employing disk drives."*

> ⚠ **Correction.** An earlier version of this document (and the plan file) stated this as "20°C in
> an hour AND 5°C in any 15-minute window" — a combined two-window rule, sourced only from a
> secondary summary. **Having now read the complete primary document, no such 15-minute clause
> exists anywhere in it.** The real rule is one flat hourly rate that differs by equipment type
> (disk vs. tape), not a stacked hourly-plus-15-minute rule for the same equipment. This is now the
> single most solidly sourced number in this entire document — the only one confirmed directly
> against ASHRAE's own primary publication rather than a secondary summary.

**Why this matters for the decision, not just as a footnote:** any switch DAMPER recommends must be
checked against this limit. In practice, at typical outdoor weather-change speeds this rarely binds
(measured on the real year of data used in Part 5's test: outdoor temperature changed by more than
5°C between consecutive hours only **0.56% of the time**, comfortably under even the stricter
5°C/hour tape-drive limit) — but it is a real, hard constraint that must be respected whenever it
does, and DAMPER's design checks it explicitly rather than assuming it away.

---

# Part 8 — The decision maths, in plain words (no equations required to understand it)

Every cycle, DAMPER is really doing simple bookkeeping, not advanced mathematics:

1. **What would running mechanical cooling cost right now?** — call this the "full price."
2. **What would running free cooling cost right now, IF conditions are favourable?** — much
   cheaper, sourced at roughly a quarter of full price based on the real 70–90% savings figures in
   Part 1.2 of the plan (a swept range, not one invented number ✏️).
3. **What would running free cooling cost if conditions turn out NOT to be favourable after all
   (a mistake)?** — more expensive than either of the above, because you'd need extra mechanical
   help anyway plus whatever unnecessary humidity/dust exposure happened ✏️.
4. **What does a SWITCH itself cost, separately from all of the above?** — this is the number from
   Part 5, and it is *not* precisely known (real sources confirm switching is costly and should be
   minimised, but do not give an exact dollar figure) — so this project sweeps it across a
   reasonable range and checks the conclusion holds up across that whole range, rather than betting
   everything on one guessed number ✏️.

**DAMPER's whole decision is: pick the sequence of open/closed choices, over the next several
hours, that keeps the running total of (1)+(2)+(3)+(4) as low as possible — while never breaching
the Part 7 safety limit.** That is the entire idea. There is no hidden complexity beyond "add up
the real costs honestly, including the cost of changing your mind, and don't switch unless the
trend justifies it."

---

# Part 9 — Glossary

See `damper-agent-plan.md` Part 10 for the complete glossary shared between both documents.

---

# Part 10 — Sources, with an honest reading status

See `damper-agent-plan.md` Part 11 for the full list with tags, and Part 12 for a correction made
honestly during this session (a figure originally attributed to the JADE white paper could not be
confirmed after opening the actual document, and has been removed from every claim in this project).
