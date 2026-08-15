# How It All Fits — the one-page mental model

**If you only read one document, read this one.** The deep version is
[what-am-i-building.md](what-am-i-building.md). The technical version is
[project-master-plan-v2.md](project-master-plan-v2.md).

> **Note:** this file used to describe a free-cooling switch. **That's no longer the project.**
> [project-master-plan-v2.md §1](project-master-plan-v2.md) has the four pivots and the measurement that
> forced each one.

---

# Meet Sam

Sam is a **heat inspector**. Their job is to find out whether the big computer warehouses in a city are
making the air around them hotter — and by how much.

Here is Sam's whole job, done by hand:

1. Sam gets a **temperature map** of the city — the air temperature in every 60-metre square.
2. Sam checks **which way the wind is blowing** today, from the airport weather report.
3. For each warehouse-full-of-computers, Sam measures the air **on the side the wind comes from** and
   **on the side the wind goes to**, and subtracts.
4. Sam doesn't trust that number yet, so Sam does **exactly the same thing at fifty ordinary warehouses**
   — buildings just as big and dark, but with no exhaust fans.
5. If the computer buildings differ a lot and the ordinary warehouses barely differ at all, **Sam has
   found something.**
6. Sam checks their own work two ways: **redo the maths with a made-up wind direction** (the effect must
   vanish), and **look at a day when the wind blew the other way** (the warm side must swap over).
7. Sam **can't measure every building on every day** — most days the wind is too weak or too shifty — so
   Sam has to choose, each time, **which measurement is worth making.**
8. Sam **writes everything down**, shows it to a supervisor before it goes anywhere, and **later checks
   whether they were right.**

**You are building Sam.**

---

# Sam is not a weather forecaster

| A weather model | Sam |
|---|---|
| Predicts what the temperature will be | Takes the temperature as given, and works out **what a building is doing to it** |
| Trained once, then just runs | **Chooses what to measure**, learns from it, gets stricter when wrong |
| Same answer for a whole 3 km square | Works at 60 metres, where buildings actually differ |

Sam **consumes** somebody else's temperature data. Sam's contribution is **the comparison**, the **check
against buildings with no exhaust**, and **deciding what's worth measuring next.**

---

# The one idea you must be able to explain

There are **two different things** people both call "temperature," and mixing them up is why this whole
question is still unsettled.

```
        On a sunny afternoon, over a black tarmac car park:

            the air at head height   →   35 °C     ← what people feel. What we need.
            the tarmac underfoot     →   55 °C     ← what a satellite sees.

        TWENTY DEGREES APART. Same place. Same moment.
```

Walk barefoot on hot tarmac. Your feet get one number, your face gets the other.

**Satellites see roofs.** A computer warehouse has a big dark metal roof, so of course it looks hot from
space — **dark things get hot in the sun.** That says nothing about whether the machines inside are running.

**FortyGuard sells air temperature.** That's the whole reason this project exists, and we've checked it
ourselves: FortyGuard's numbers swing **7.8–8.3 °C** between 3 a.m. and 3 p.m. Air behaves like that. A roof
would swing 20–30.

---

# Sam's two comparisons

## Comparison one: upwind vs downwind — *free, and simultaneous*

```
        WIND FROM the west  ────────────────►

    ╔═══════════╗       ██████        ╔═══════════╗
    ║  UPWIND   ║       │ DC │        ║ DOWNWIND  ║
    ║ 31.6 °C   ║       ██████        ║ 32.4 °C   ║
    ╚═══════════╝                     ╚═══════════╝
      clean air                        the exhaust lands here
                    difference: +0.8 °C
```

**Why this is clever:** same day, same hour, same weather, same sunshine. The only difference is whether the
air has been through the building. You get the "what would it have been otherwise?" answer for free.

## Comparison two: the warehouses — *the one that makes it evidence*

**+0.8 °C means nothing on its own.** Air temperature varies a bit everywhere anyway.

Think about checking whether a radiator is on. You feel 22 °C beside it and 21 °C at the far wall. Is that
the radiator? **You don't know** — rooms are uneven. So you go and check **five rooms with the radiator
switched off** and find the walls differ by 0.3 °C in each. **Now** your 1 °C means something.

**A warehouse is the room with the radiator off.** Big, dark roof, tarmac all around, used to be a field —
**everything the same except the exhaust.**

```
warehouses vary by  −0.3 to +0.3 °C    →   our +0.8 °C is REAL      ✓
warehouses vary by  −0.9 to +1.1 °C    →   we measured NOTHING      ✗
```

**Same number. Opposite conclusions.** The warehouses decide which one you're in.

---

# The mind map

```
                         ┌─────────────────────────────┐
                         │   THE OPEN QUESTION          │
                         │  Do computer warehouses      │
                         │  heat the air around them?   │
                         │  Nobody knows. Scientists    │
                         │  are still arguing.          │
                         └──────────────┬──────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼────────┐    ┌───────────▼──────────┐   ┌─────────▼─────────┐
    │  SATELLITES      │    │  CARS WITH           │   │  FORTYGUARD       │
    │  measured ROOFS  │    │  THERMOMETERS        │   │  measures AIR     │
    │  → wrong thing   │    │  measured AIR — but  │   │  at 60 m, hourly, │
    │                  │    │  2 cars, 4 buildings │   │  years of history │
    │                  │    │  → doesn't scale     │   │  → THE INSTRUMENT │
    └──────────────────┘    └──────────────────────┘   └─────────┬─────────┘
                                                                  │
                                        ┌─────────────────────────┴─────┐
                                        │        SAM (the agent)         │
                                        └─────────────┬─────────────────┘
                                                      │
            ┌────────────────┬──────────────┬─────────┴────────┬──────────────────┐
            │                │              │                  │                  │
     ┌──────▼─────┐   ┌──────▼─────┐  ┌─────▼──────┐   ┌───────▼──────┐  ┌────────▼───────┐
     │ TEMPERATURE│   │  WIND      │  │ WAREHOUSES │   │  WHAT TO     │  │  OWN TRACK     │
     │ MAP        │   │  (airport, │  │ (the null) │   │  MEASURE     │  │  RECORD        │
     │ FortyGuard │   │   free)    │  │            │   │  TODAY?      │  │                │
     │ 60 m       │   │            │  │ 50 sites,  │   │  ⭐ the real  │  │ grades itself, │
     │            │   │ FortyGuard │  │ 1 km clean │   │  decision    │  │ gets stricter  │
     │            │   │ has none   │  │ screen     │   │              │  │                │
     └────────────┘   └────────────┘  └────────────┘   └──────────────┘  └────────────────┘
                                                      │
                              ┌───────────────────────┴──────────────────┐
                              │                                          │
                    ┌─────────▼──────────┐                   ┌───────────▼──────────┐
                    │  WHAT IT PRODUCES  │                   │  WHO PAYS            │
                    │  · interference    │                   │  · land buyers       │
                    │    matrix          │                   │    (siting)          │
                    │  · permit evidence │                   │  · permit applicants │
                    │  · siting score    │                   │  · counties          │
                    └────────────────────┘                   └──────────────────────┘
```

---

# Sam's hardest decision — and it's what makes Sam an agent

Sam has a big grid to fill in:

```
                    wind FROM:  N    NE    E    SE    S    SW    W    NW
   building A → B              ✓     ?     ?     ✓    ?     ?    ✓    ?
   building A → C              ?     ?     ✓     ?    ?     ✓    ?    ?
   building B → D              ✓     ?     ?     ?    ?     ?    ?    ?
   ...  (thousands of rows)
```

Every ✓ is a measurement Sam has made. Every ? is something Sam doesn't know yet.

**Four things make filling this a genuine puzzle:**

1. **Today's wind decides which ?s you can even reach.** You cannot measure a west-wind plume on an
   east-wind day.
2. **Only about a third of days are usable at all** — we checked a whole summer of airport records: 31 of
   90 days had wind steady and strong enough to mean anything. Chances are scarce.
3. **Every measurement costs credits** from a fixed budget.
4. **Filling one ? changes what the others are worth.** Once a wind direction is well covered, measuring it
   again teaches almost nothing.

So Sam's question each time is **not** *"is the wind steady?"* It is:

> **"Given what I already know, what I still don't, and what I can afford — what is the single most
> informative measurement I can buy right now?"**

**That's a real decision, and the answer changes every day.** Sam scores every option by how much it would
teach per credit, buys the best one, **and writes down both the choice and the runner-up** so you can check
Sam's judgement afterwards.

**Be honest about the rest.** The measuring itself is a pipeline — fetch, average, subtract, compare. If
that were all of it, this would be a scheduled script with a few if-statements, and calling it an agent
would be fair game for a judge. **The agency is in choosing what to measure, not in doing the measurement.**

---

# The levels of Sam

**Level 0 — a thermometer on a wall.** Reads one number. Not an agent.

**Level 1 — a script.** Fetches the map, averages two wedges, prints a number. Runs on a schedule. No
memory, no judgement. **Still not an agent.**

**Level 2 — Sam, and this is a genuine agent:**
- **Decides what to measure**, from what's still unknown and what today's wind allows
- **Spends a real budget** on that judgement
- **Refuses to call something real** unless it beats the warehouses
- **Checks its own work** — the placebo test and the wind-following test
- **Grades yesterday's answer** and gets stricter if it was wrong
- **Shows a human** before anything goes out

**Level 3 — Sam with an opinion about *why*.** FortyGuard can also say *why* a place is hot — urban form,
human activity, geography — in plain language. Sam reads that and judges: *does this sound like **waste
heat**, or like **land cover**?* No threshold answers that. It needs reading comprehension, which is a real
job for a language model.

**Level 2 is a complete project. Level 3 is what makes it stand out. Build 2 first and protect it.**

---

# The story of your month

## Aug 9–17 — nine days, costs nothing

Register the hackathon key. Read the two papers. Build the list of computer warehouses **and** the list of
ordinary warehouses (throwing out any warehouse within 1 km of a data centre — one sitting in somebody's
plume is not a control). Pull a season of airport wind and **pick the exact dates** you'll measure. Write
the wedge maths and test it on data you already have. **By Aug 17, Sam runs end to end on saved data with a
fixed threshold — and you commit and tag it. That's your safety net.**

## Aug 18 morning — about fourteen calls, and they settle everything

Measure the price first. Then, in order:

- **Does the warm side move when the wind moves?** ← *the single most important question*
- **Do we get the numbers the Arizona team published**, at the buildings they named?
- **Does a calm day show nothing**, as it should?
- **Do the warehouses show a plume too?** (If they do, and the warm side doesn't move, the instrument
  can't tell a warehouse from a data centre — and we say so.)

**Every one of those uses historical data**, so **nothing waits for the weather.** You know by lunchtime on
day one whether this works.

## Aug 18–30 — build outward

Fill the grid from history, one wind direction at a time. Produce the permit evidence pack, then the siting
score. Add the *why* layer. **Freeze the code on Aug 29** and rehearse the whole thing offline from saved
replies, so **no live API call is needed while judges are watching.**

---

# Every jargon word → what Sam does

| They say | Sam does |
|---|---|
| "Plume" | The invisible trail of warm air drifting downwind |
| "Upwind / downwind wedge" | The two pie slices Sam averages |
| "Differential" | Downwind average minus upwind average |
| "Control site" | The fifty ordinary warehouses |
| "Null distribution" | What the warehouses came back with |
| "Conformal prediction" | How Sam decides how big a difference must be before it counts — with a stated success rate |
| "Placebo test" | Redo the maths with a made-up wind direction; the effect must vanish |
| "Wind-following test" | Same building, opposite wind: the warm side must swap over |
| "Interference matrix" | Sam's big grid of ✓s and ?s |
| "Expected information gain per credit" | How Sam picks today's measurement |
| "n_eff" | How many measurements are *genuinely* independent — always fewer than you'd hope |
| "Fail-safe" | If anything's wrong, say nothing rather than say something false |
| "Fixture / replay" | Saved replies, so the demo can't break |
| "Stub" | A clearly labelled fake, where we don't have the real thing |

---

# Five things to remember

**1. Two temperatures.** Roofs and air are different numbers, twenty degrees apart. Satellites measure
roofs. FortyGuard measures air. **That confusion is the entire scientific argument.**

**2. Upwind is a free control.** Same day, same weather, same sun — only the exhaust differs.

**3. The warehouses are what make it evidence.** Without them you have a colourful map and no argument.
And a warehouse inside somebody's plume isn't a control.

**4. The agency is in choosing what to measure**, not in doing the measurement. Only a third of days are
usable, credits are finite, and the grid is mostly empty. Deciding what to buy today is a real decision.

**5. Either answer wins.** If the warm side moves with the wind, you've scaled a 2026 scientific paper from
four buildings to a whole country. If it doesn't, you've supported the other side of a live dispute and
shown the instrument's limit. **You cannot come away with nothing** — and for a nine-day build against a
hard deadline, that is worth more than any feature.
