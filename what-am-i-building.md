# What Am I Building?

**Read this first. It assumes you know nothing, and it defines every word before using it.**

This is the plain-English version of [project-master-plan-v2.md](project-master-plan-v2.md). If a sentence
in that document confuses you, the explanation is somewhere in here.

> **Note:** an earlier version of this file described a *free-cooling switch* — deciding hour by hour
> whether a data centre should use cheap cooling or expensive refrigeration. **That is no longer the
> project.** [project-master-plan-v2.md §1](project-master-plan-v2.md) explains what changed and why. The
> old work wasn't wasted; you'll see it come back in Part 9.

---

# Part 1 — The word "plume"

A **plume** is a trail of something drifting away from the place it came out of.

You've seen plenty:

- **Smoke from a chimney** — leaves the chimney, drifts sideways, spreads, fades
- **The white trail behind an aeroplane**
- **Milk poured into coffee** — a swirl spreading from where it landed
- **Steam from a kettle**

Every plume has the same four properties, and **all four matter to us**:

1. It has **one source**
2. It's **carried** by whatever is moving past — wind in air, current in water
3. It **spreads out** as it travels
4. It **fades** — strongest at the source, weaker with distance, until you can't detect it

## Our plume is invisible

Here's the closest everyday example. **Stand next to a clothes dryer vent** — that little duct on the side
of a house with warm air blowing out.

- Right at the vent: clearly warm
- Two metres away: a bit warm
- Ten metres away: you can't tell
- And **whichever way the wind blows, that's where the warm air goes**

**That is exactly what we're studying.** Just enormously bigger, and invisible — because warm air looks
identical to ordinary air. A thermometer would find it. Your eyes never will.

**A data centre is a clothes dryer vent the size of a shopping centre.**

---

# Part 2 — What a data centre does to the air

A **data centre** is a warehouse full of computers. Companies rent space in them to run websites, cloud
storage, AI training.

Here's the thing about computers: **they turn electricity into heat.** Nearly all of it. A computer doesn't
"use up" electricity — it converts it to heat, which comes out the back.

So a data centre drawing **169 megawatts** produces 169 megawatts of heat. To picture that: **169,000
one-kilowatt space heaters, running non-stop, forever, inside one building.**

That heat can't stay inside — the computers would cook. So giant fans blow it out into the outside air.

**Think of your fridge.** A fridge doesn't destroy heat. It moves heat from inside the fridge into your
kitchen — that's why the back of a fridge is warm. Your kitchen gets slightly hotter so your milk stays cold.

A data centre does exactly this, at enormous scale. **It keeps its computers cool by making the
neighbourhood warmer.** The neighbourhood is the kitchen.

## Two more words

**Waste heat** — heat a building has to get rid of. "Waste" because nobody wants it; it's a by-product.

**Exhaust** — the actual warm air being blown out. (Same word as a car's exhaust.)

---

# Part 3 — Upwind and downwind

Imagine wind blowing left to right:

```
        WIND  ────────────────────────►

    ┌──────────┐      ██████      ┌──────────┐
    │  UPWIND  │      │ BLDG │    │ DOWNWIND │
    └──────────┘      ██████      └──────────┘
    the air comes                  the air goes
    FROM here                      TO here
    clean, untouched                the plume lands here
```

**Upwind** = the side the wind comes from. That air hasn't touched the building yet.
**Downwind** = the side the wind goes to. That's where the exhaust ends up.

**This is the whole trick of the project**, and here's why it's clever:

> **The upwind side is a free comparison.** Same day, same hour, same weather, same sunshine. The *only*
> difference is that one side's air has been through the building's exhaust and the other hasn't.

Any other way of measuring this would need you to somehow know what the temperature "would have been"
without the building. Upwind gives you that for nothing.

---

# Part 4 — The mystery

## The question, in one sentence

> **When you put a building full of computers in a neighbourhood, does the air outside actually get hotter
> — and if so, by how much, and how far away?**

That sounds like it should have an obvious answer. **It doesn't.** As of right now, in 2026, **nobody knows,
and scientists are arguing about it.**

Here's how it became a mystery. Four acts.

## Act 1 — Somebody looked from space

Researchers used **satellites** to study data centres worldwide over twenty years.

Their finding: data centres are about **2 °C hotter** than their surroundings, up to **9 °C** in the worst
spots, affecting **343 million people** within 10 km.

Huge claim. CNN, Forbes and others ran it.

## Act 2 — Somebody said: you measured the wrong thing

This is the heart of everything. Slowly, then.

**There are two completely different things that people both call "temperature."**

**Thing one: how hot the ground and rooftops are.** What a satellite measures, because a satellite looks
*down* at surfaces.

**Thing two: how hot the air is.** What you feel, and what a thermometer at head height reads.

**These are not the same number. Not even close.**

Picture a black tarmac car park on a sunny afternoon:

```
        the air at head height        →   35 °C
        the tarmac under your feet    →   55 °C
```

**Twenty degrees apart. Same place. Same moment.**

You know this from experience. Walk barefoot across hot tarmac in summer — your feet get the *surface*
temperature, your face gets the *air* temperature. Two completely different experiences at the same instant.

**Now the objection.** A satellite looking at a data centre sees a big dark metal roof. Of course it's
hotter than the grass field that was there before. **Dark things get hot in the sun. That has nothing to do
with whether the computers inside are running.**

He did the physics: the actual exhaust could explain only about **1–3 %** of what the satellite saw. The
other 97–99 % is simply *"a dark roof instead of grass."*

So the headline might be badly wrong. Or might not. **Nobody could say.**

## Act 3 — Somebody measured the air properly

A team at Arizona State University did it the honest way. They bolted good thermometers onto cars and
**drove around four data centres in Phoenix**, upwind and downwind at the same moment, from June to October
2025.

```
Air downwind was      0.7–0.9 °C warmer than upwind, on average
Worst case            2.2 °C warmer
Detectable out to     about 500 metres from the fence
The exhaust itself    8–14 °C hotter than the surrounding air
```

**So the effect is real** — but much smaller than the satellite headline, and only fairly close in.

## Act 4 — But four buildings isn't an answer

There are **thousands** of data centres. You cannot drive cars around all of them, every hour, forever. The
scientists said so themselves: they need measurements across far more time, weather and locations.

**So the mystery sits there, half-answered.** We know it's real. Nobody knows how big, where, or how much it
matters — **because nobody has an instrument that can measure it at scale.**

---

# Part 5 — The twist: they're heating each other

Here's the part that turns a science question into a business.

**I measured this.** Using free OpenStreetMap data:

```
Data centre buildings in Ashburn, Virginia                        226
Buildings with at least one other within 800 metres              224   (99%)
The typical building has this many neighbours within 800 m         11
The most crowded one has                                          30
Closest pair                                                      62 metres
And the plume reaches                                            ~500 metres
```

**They are all standing in each other's exhaust.**

And this isn't just Ashburn. Santa Clara: 58 buildings, 90 % with a neighbour within 800 m. Dallas: 78 %.
Phoenix: 55 %. Across those four metros, **about 90 % of facilities have a neighbour inside plume range.**

## Why that costs money

A data centre cools itself by **taking in outside air**:

- **Cool air coming in** → just run fans → **cheap**
- **Warm air coming in** → switch on refrigeration → **expensive**

So **your neighbour's exhaust raises your electricity bill.** And when the wind changes direction, *which*
neighbours are hurting you changes too.

**Nobody can measure this.** The building's own thermometer tells it the incoming air is warm — it can't say
*why*, or that it's about to get worse in four hours, or which three buildings upwind are responsible.

---

# Part 6 — What we're building

**A program that runs by itself and answers, for every data centre in a city:**

> *"How much warmer is the air on your downwind side than your upwind side? Is that difference real? And
> what is it costing you?"*

Three steps, plus a crucial fourth.

**Step 1 — Get a temperature map.**
One request to FortyGuard covers the whole area, split into squares 60 metres across, each with its own air
temperature. Already tested and working: **17,658 squares in 67 seconds.**

**Step 2 — Find out which way the wind is blowing.**
FortyGuard doesn't provide wind, so we take it free from the nearest airport's hourly weather report.

**Step 3 — Compare the two sides.**

```
                    WIND FROM the west  ──────────────►

        ╔═══════════╗                        ╔═══════════╗
        ║  UPWIND   ║        ██████          ║ DOWNWIND  ║
        ║   wedge   ║        │ DC │          ║   wedge   ║
        ╚═══════════╝        ██████          ╚═══════════╝
          mean 31.6 °C                         mean 32.4 °C

                    difference = +0.8 °C
```

We use a **wedge** (a pie slice) rather than a single point, so we're averaging lots of squares instead of
trusting one.

**Step 4 — and this is the one that makes it real science: check it against warehouses.**

---

# Part 7 — Why warehouses matter

That +0.8 °C means **nothing on its own.** Temperature varies a bit everywhere — a road here, trees there,
a slight slope, one side caught more morning sun. Maybe 0.8 °C is just... normal.

## The radiator test

Suppose you want to know whether a radiator in a room is actually switched on.

You feel the air next to it: **22 °C.** Is that warm? You don't know.
You feel the air by the far wall: **21 °C.** A 1 °C difference. Is that the radiator?

**Still don't know** — rooms are uneven anyway. **So you go and check five rooms where the radiator is
definitely off.** You find the two walls differ by about 0.3 °C in each.

**Now** your 1 °C means something. It's well outside what an ordinary room does.

**The warehouse is the room with the radiator off.**

## Why a warehouse specifically

You want the comparison building to be as similar to a data centre as possible **in every way except the
exhaust.** A warehouse is:

- Big
- Dark flat roof
- Ringed by tarmac
- In an industrial estate
- Replaced a field when it was built

**The only thing it doesn't have is 169 MW of fans.**

So measure 50 warehouses with the identical method:

```
If warehouses come back at  −0.3 to +0.3 °C   →  our +0.8 °C is REAL
If warehouses come back at  −0.9 to +1.1 °C   →  we've measured NOTHING
```

Same 0.8 °C, opposite conclusions. **The warehouses decide which world we're in.** Without them, you have a
colourful map and no argument.

**A lovely bonus:** FortyGuard charges **per request, not per area** — measured, not assumed. So one request
over the city already contains the data centres *and* the warehouses. **The comparison group is free.**

**One trap to avoid:** a warehouse 400 metres downwind of a data centre is **inside the plume** — it's not a
control. We exclude any warehouse within 1 km of a facility. Forgetting this would hide a real effect.

## Two more honesty checks

**The rotation placebo.** Take a real day's data and redo all the maths using a **randomly chosen** wind
direction, 200 times over. **The effect must disappear.** If you still "find" plumes with a made-up wind
direction, you were never measuring exhaust.

**The wind-following test — the most important one.** Take the same building on two days with **opposite**
wind directions. **Does the warm side swap over?**

This matters more than anything else, and here's why. Suppose the east side of a facility happens to be a
car park and the west side a golf course. You'd measure a "plume" on the east side that is really just land
cover — and it might match the published numbers by pure coincidence.

> **Land cover does not move when the wind moves.** A plume does.

That single test separates a real measurement from a coincidence.

---

# Part 8 — Why FortyGuard and nothing else

We need four things at once:

1. **Air** temperature — not roof temperature
2. **Small squares** — the plume is only ~500 m long, so big squares would smear it away
3. **Every hour** — because the wind changes
4. **Years of history** — so we can look before and after a building opened

Now every alternative:

| | Fails because |
|---|---|
| **Satellites** | Measure the **roof**, not the air. That's the exact mistake the whole argument is about. And they only pass over every few days |
| **Free weather forecasts** (NOAA's HRRR) | Right thing (air), but squares are **3 km** across. **The building and its entire 500 m plume fit inside one square** and get reported as a single number. Like hunting for a bruise wearing a boxing glove |
| **Airport thermometer** | One point, kilometres away, in a grass field |
| **Cars with thermometers** | Actually works — but two cars, four buildings, four months |

**FortyGuard is the only thing that does all four.**

And here is the sharpest way to say it:

```
Two facilities 300 metres apart, on opposite sides of a plume edge:

FortyGuard 60 m :  31.2  vs  32.4  →  a difference exists, so a decision exists
HRRR      3 km  :  31.7  vs  31.7  →  no difference, so NO DECISION EXISTS
```

**Not a worse decision. No decision at all.** That's the strongest form of "why do you need FortyGuard?"

---

# Part 9 — What we already know, before writing any code

Every one of these came from a real API call, and they're all on disk.

**The instrument holds up:**

| What we checked | Result |
|---|---|
| Do the map squares stay in the same place between calls? | **6,875 out of 6,875 identical.** Perfect. Without this nothing works |
| Is it air temperature or roof temperature? | Day/night swing of **7.8–8.3 °C**. Air behaves like that; a roof would swing 20–30 °C. **We hold the right instrument** |
| Are the 60 m squares real, or blurred from something coarser? | Nearby squares differ smoothly with distance, no sudden jump. **The 60 m detail is genuine** |
| Can one request cover a whole cluster? | **17,658 squares in 67 seconds** |
| Does the same request give us a prediction *and*, later, the outcome? | Yes — real measured error: average +0.35 °C |

**And the number that says this project can work:**

```
Ordinary variation between squares 500 m apart   ≈ 0.09 °C
The plume we're hunting                          0.7–2.2 °C
                                                 ─────────
The signal is                                    8–24× bigger than the noise
```

**If the plume is in FortyGuard's data, it should be unmistakable.**

**Two things we learned that changed the plan:**

**(1) Only about a third of days are usable.** We checked a whole summer of airport wind records: only
**31 of 90 days** had wind steady and strong enough to say which way a plume was going. So a 13-day
hackathon window would give us only about **4–5 usable days.** Not enough. **So we build the measurement
from historical days instead**, picking dates from the wind records. The live window just confirms it.

**(2) Our first test polygon was in the wrong place.** It contained only 6 data centres, all too close to
the edge to measure. A search found a much better 8 × 8 km box containing **168 measurable facilities** —
in one request.

**And here's where your old free-cooling work comes back.** The v1 plan had this in it:

```
   22.0 °C
 −  3.0 K    ⚠ "recirculation + facility waste heat"   ← A PURE GUESS
   ─────
   19.0 °C
```

That −3.0 was the weakest number in the entire plan. I flagged it as something a facility engineer would
have to supply. **The neighbour plume *is* that number.** The thing we couldn't know, we now measure.

---

# Part 10 — What could go wrong

Being honest about this is worth more than hiding it.

## The big one: FortyGuard might not know about waste heat

FortyGuard doesn't have a thermometer in every 60 m square — that would be millions of thermometers. So
they must be **computing** the temperature from other information: weather stations, satellite imagery of
what the ground looks like, building density, sun angle, time of day.

**Does anything in that list know that one particular building has 169 MW of fans blowing hot air out?**
Almost certainly not.

So two possible worlds:

```
WORLD A — the model picked it up somehow
  wind from west  →  warm patch on the EAST side
  wind from east  →  warm patch on the WEST side
  The warm side MOVES.

WORLD B — the model is blind to it
  warm patch glued to the building, same place regardless of wind
  Because it's caused by what the building LOOKS like, not what it's doing.
```

**How we find out:** the Arizona scientists **named their buildings** — Mesa (36 MW) and Chandler (169 MW).
Point FortyGuard at those exact sites and see whether we get their published numbers. Phoenix coverage is
already confirmed working. **Two calls.**

**And either answer is a result:**

- **World A** → we've taken a 2026 scientific paper from four buildings to every data centre in America
- **World B** → that **supports the critic**, separates *"the building is dark"* from *"the building is
  running"*, and is a real finding

**You cannot walk away with nothing.**

## The sharpest criticism anyone could make

**What if the warehouses look the same to the model?**

If FortyGuard works out temperature from land cover, then a warehouse and a data centre — both big, both
dark-roofed, both on tarmac — **look identical to it.** In that case our warehouses would show the *same*
plume, and we'd get a "no effect" answer **not because there's no effect, but because the instrument can't
tell them apart.**

This is the objection I'd expect a sharp judge to find. **So say it first.** The wind-following test
separates it: if neither the data centres nor the warehouses show a moving warm side, we've learned the
instrument can't answer the question — and we report that.

## Two smaller ones, also worth saying out loud

**The wind reading comes from an airport kilometres away.** It might not be the wind at the building. We
only use days with strong, steady wind, and we report how sensitive the result is to that.

**The money figures rest on guesses.** The temperature difference is measured. Turning it into dollars needs
constants — cost per kWh, plant efficiency — that we don't have. **So we always give money as a range with
the guesses named, never as a single confident number.**

---

# Part 11 — Who would pay for this

**Right now, in Ashburn, Virginia** — the exact place we have working data for:

- **250+ data centres** in one county
- The county **removed automatic approval** in 2025; every new one needs a public hearing
- In **July–August 2026** the board began moving toward **pausing all new applications**
- They are **writing new rules this year** — with **no heat requirement**, because **nobody has an
  instrument to write one against**
- The electricity company has asked for a 14 % household rate rise, blaming data centre growth

**Two customers need the same thing, and neither has it:**

| Who | Why they'd pay |
|---|---|
| **A company buying land for a new facility** | *"How many cheap-cooling hours does this parcel get — today, and after the three facilities already approved upwind get built?"* That's a decision worth hundreds of millions, locked in for 30 years |
| **A company applying for permission** | Somebody at the hearing will ask *"how much will this heat my neighbourhood?"* **They cannot answer.** And they're being blamed on the basis of a satellite study whose physics is disputed — **a real measurement is their defence, not their exposure** |

**One thing to be careful about.** "Here's which neighbourhoods are being warmed" is *not* the product —
nobody pays to be exposed. The product is **thermal due diligence**: the measurement that lets a buyer
underwrite a deal or answer a hearing. Same data, completely different framing.

## And why FortyGuard themselves would care

FortyGuard sells **an API**, not reports. So what they need is *reasons for big customers to buy lots of
data.*

Their named partners are **Microsoft, Google, AWS and NVIDIA** — every one of them builds data centres.
Would they buy an analysis tool from a student? **Probably not — they'd build it in-house.** And that's
fine, because **to build it they'd need FortyGuard's data.**

**That's the pitch:** not *"here's a product to sell"* but *"here's a reason for Microsoft to buy more of
your data, in a use case your own CEO has already talked about publicly, that nothing else on the market
can serve — and here's a working demonstration."*

---

# Part 12 — What makes this an *agent* and not a chart

This matters, because "truly agentic" is one of the things being judged, and it's easy to fake.

**A fair criticism first.** If the program just did: *fetch map → fetch wind → average two wedges → compare
to a threshold → print*, then it would be **a scheduled script with a few if-statements.** That is not an
agent, and calling it one would get taken apart.

**Here's where the real decision-making lives.**

The **interference matrix** is a big grid: one row per pair of facilities, one column per wind direction.
Almost all of it is empty. Filling it is a genuine puzzle:

- **Today's weather decides which empty cells you can fill at all** — you can't measure a west-wind plume on
  an east-wind day. And **only ~34 % of days are usable**, so chances are scarce
- **Every measurement costs credits** from a limited budget
- **Earlier choices change what's worth doing later** — once a wind direction is well covered, measuring it
  again teaches you little
- And the agent has to decide **when it has enough evidence to call something real, versus buy more**

So the question the agent asks each time isn't *"is the wind steady?"* It's:

> **"Given what I already know, what I still don't, and what I can afford — what is the single most
> informative measurement I can buy right now?"**

**That's a real decision**, and the answer is different every day. The agent scores every possible
measurement by *how much it would teach us per credit spent*, picks the best one, and **writes down both
its choice and its runner-up** so you can check its judgement afterwards.

**And the AI model gets a real job too.** FortyGuard's `heat_intelligence` endpoint returns *reasons* a
place is hot, in plain language — urban form, human activity, geography. The agent has to judge:

> *"Does this reason sound like **waste heat**, or like **land cover**?"*

There's no threshold that answers that. It needs actual reading comprehension. That's a legitimate job for a
language model — unlike "write a nice summary," which is decoration and is cut from the plan.

**What it does:** produces detections, a ranked watchlist and a siting score **that nobody asked it for**,
on a schedule, and then **grades its own past work** and gets stricter if it's been wrong. Delete the screen
entirely and it still runs.

---

# Part 13 — The code, file by file

```
downwind/
  clock.py       the current time — passed IN, never read directly.
                 (So we can replay any past day exactly.)
  config.py      the clusters, the polygons, the guessed constants (all clearly marked)

  api/client.py  talks to FortyGuard: send, wait, retry, and CHECK THE REPLY ISN'T EMPTY
                 (FortyGuard returns "success" with zero data if you ask beyond its range —
                  the most dangerous thing we found)
  metar/         the airport wind: direction, speed, and how steady it was
  registry/      the list of data centres and the list of warehouses,
                 with the 1 km "don't use a contaminated control" filter

  field.py       the temperature map: squares, positions, statistics
  wedge.py       draws the two pie slices and computes the difference
  planner.py     ⭐ THE AGENT'S BRAIN — which measurement is worth buying today?
  matrix.py      the interference matrix: what we know so far

  conformal/     how big must a difference be before we may call it real
  placebo.py     the rotation test and the wind-following test
  decide.py      the recommendation, and the fail-safe rules
  explain.py     the local AI model: judges the attribution, writes the summary
  gate.py        a human approves before anything leaves
  logbook.py     writes every row down, forever, in a frozen format
  scorer.py      looks up what actually happened and grades yesterday's answer

  stubs/         clearly labelled fakes: plant details, facility load, cost constants
fixtures/        saved real replies, so the whole thing runs with no internet
```

**Two rules that never bend:**

**The clock is passed in.** `datetime.now()` appears in exactly one file. Everything else receives the time
as a parameter. Without this you can't replay a past day, and replay is how the demo works.

**A "stub" is a clearly labelled fake.** We don't have a real data centre's plant details, so we put a
labelled placeholder there. **A stub is more honest than a simulation** — a simulation invites you to
believe a number was measured.

---

# Part 14 — Every word, in one place

| Word | Plain meaning |
|---|---|
| **Plume** | A trail drifting from a source — smoke from a chimney, warm air from a dryer vent. Ours is invisible |
| **Waste heat** | Heat a building must get rid of. A by-product nobody wants |
| **Exhaust** | The actual warm air being blown out |
| **Upwind** | The side the wind comes from. Clean air; hasn't touched the building |
| **Downwind** | The side the wind goes to. Where the plume lands |
| **Surface temperature** | How hot the ground and roofs are. What satellites see. Can be 20 °C hotter than the air |
| **Air temperature** | How hot the air you stand in is. What we need, and what FortyGuard sells |
| **Tile / square** | One 60-metre patch of FortyGuard's map |
| **Wedge** | The pie slice of squares we average, upwind or downwind |
| **Differential** | Downwind average minus upwind average. **The measurement** |
| **Control site** | A warehouse — same in every way except the exhaust. Shows what "nothing happening" looks like |
| **Contamination** | When a "control" warehouse is actually inside somebody's plume. Excluded by the 1 km rule |
| **Rotation placebo** | Redo the maths with random wind directions. The effect must vanish |
| **Wind-following test** | Does the warm side move when the wind moves? **Land cover doesn't move.** The key test |
| **Interference matrix** | The grid: for each pair of buildings and each wind direction, how much one heats the other |
| **Conformal prediction** | Using a pile of past measurements to decide how big a difference must be before you may call it real — with a stated success rate |
| **Usable day** | Wind steady and strong enough that "downwind" means something. **Only about a third of days** |
| **METAR** | The free hourly weather report every airport publishes. Our wind source |
| **HRRR** | NOAA's free 3 km weather model. Our main comparison — it reports zero difference between neighbours |
| **Fixture / replay** | Saved real replies, so the agent runs with no internet. The safe demo |
| **Stub** | A labelled fake. More honest than a simulation |
| **n_eff** | How many *genuinely independent* measurements you have. Always fewer than you'd like |

---

# Part 15 — The three questions you'll definitely be asked

**"Couldn't you do this with free data?"**
> *"For the air temperature across a metro, yes — NOAA's HRRR is free and better above 3 km. But the effect
> I'm measuring is 500 metres wide, and one HRRR cell is 3 kilometres, so it reports every facility in the
> cluster as the same number. Satellites do get to 70 metres, but they measure the ground, not the air —
> and that confusion is literally what the current scientific argument is about. I checked our own data:
> the day–night swing is 7.8–8.3 °C, which is how air behaves. A surface would swing 20–30. Take FortyGuard
> away and there is no measurement at all — not a worse one."*

**"Isn't this already automated? Data centres have thousands of sensors."**
> *"Their cooling is automated, and very well. But a sensor tells a building what its intake air is **right
> now**. It cannot tell it that it is downwind of three neighbours today, or that its intake will degrade in
> four hours. And no weather service can tell it either, because the effect is 500 metres wide and depends
> on which neighbours happen to be upwind today. We never touch their control system — we tell them
> something their sensors structurally cannot know."*

**"Is this really an agent?"**
> *"The measuring part is a pipeline, and I'd say so. The agent is the part that decides **what to measure**.
> There's a big grid of facility pairs and wind directions to fill, only a third of days are usable, and
> every measurement costs credits from a fixed budget — so each cycle it has to work out which single
> measurement teaches it the most per credit. It logs its choice and its runner-up so you can audit its
> judgement. And it grades its own past answers and gets stricter when it's been wrong. The arithmetic
> stays deterministic and replayable on purpose — for something producing evidence in a planning process,
> that's the right engineering."*
