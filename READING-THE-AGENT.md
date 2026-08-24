# Reading the agent — a complete beginner's guide to every screen, control and graph

**Who this is for:** someone who has never seen this project, does not work in data centres, and does
not know what a "bearing" or an "intake" is. By the end you will be able to open the demo, click
anything, and know exactly what you are looking at and why it is there.

**How to read it:** front to back, once. Part 1 is the vocabulary — every later part uses only words
defined there. If a word appears later that you do not recognise, it is in Part 1 or in the glossary
at the end.

---

# Part 0 — The story, before any jargon

## 0.1 What is actually happening in the world

A **data centre** is a building full of computers. Computers turn electricity into heat, and a lot of
computers make a lot of heat — enough that if you did nothing, the building would cook itself in
minutes. So every data centre has a cooling plant whose whole job is to move that heat outdoors.

There are two ways to do it.

**The expensive way — mechanical cooling.** A machine called a **chiller** works like a fridge: it
uses a big electric compressor to make cold water, and that cold water cools the air inside. It
always works, on any day, at any outdoor temperature. It also burns an enormous amount of
electricity, because you are paying a compressor to move heat uphill.

**The cheap way — free cooling.** If it happens to be cool outside, you can skip the fridge
entirely: open the dampers, pull outside air in, blow it over the computers, push the hot air out.
The heat still leaves the building, but you are paying only for fans, not for a compressor. In the
industry this is called an **economizer**, and "free" means free of the compressor, not free of all
electricity.

So the daily question for the person running the plant is simply:

> *Is it cool enough outside, right now, to switch the chillers off?*

## 0.2 Why that question is harder than it sounds

Three reasons, and the whole project exists because of the third.

**1. It is not just about temperature.** Outside air brings whatever is in it — moisture, dust,
smoke, pollen, salt. Too much moisture and you get condensation on electronics. Too much dust and you
clog filters or coat circuit boards. A US national laboratory (LBNL) put particle counters inside
eight real data centres and found that the documented reason operators avoid free cooling is *fear of
contamination and losing humidity control* — **not** temperature. So a real decision has to check
moisture and air quality too, not just the thermometer.

**2. Buildings breathe their own exhaust.** The hot air a data centre throws out has to go somewhere.
If the wind is blowing the wrong way, some of that hot exhaust drifts across and gets sucked back in
by the same building — or by the neighbouring one. So the air arriving at the intake can be *hotter
than the weather report says*. That extra warmth is called **recirculation**, and it is invisible to
any weather forecast, because it is caused by the buildings themselves.

**3. A cooling plant cannot turn on a sixpence.** This is the important one. Switching a big plant
between mechanical and free cooling is not a light switch — valves move, dampers open, water
temperatures settle. It takes hours of **notice**. So a thermometer reading *right now* is useless
for a decision you must commit to *before* you know the answer. You need to know what the air will be
like in three hours' time, and a thermometer cannot see into the future.

> **That gap is the entire product.** FortyGuard sells a *forecast* of the air — including humidity
> and air-quality measures — and that forecast is exactly the input the plant is missing.

## 0.3 What the agent does about it

It runs a loop, hour after hour:

1. **Perceive** — read the forecast, the real wind, and its own past accuracy record.
2. **Solve** — work out how much the building's own exhaust will warm its intake, given that wind.
3. **Bound** — add a safety margin, sized from how wrong it has actually been before.
4. **Decide** — produce a **schedule**: which hours to free-cool and which to run chillers.
5. **Act** — emit command rows a real building-control system could execute.
6. **Explain** — say, for every hour, exactly which condition decided it.
7. **Score, then recalibrate** — check what really happened and, if it was wrong, *widen its own
   safety margin*.

Step 7 is the one worth pausing on. The agent is not a fixed rule. It grades its own homework and
gets more cautious when reality proves it too confident. Nobody types the new margin in — it is
computed from the mistakes.

---

# Part 1 — The vocabulary

Read this once. Everything later is built from these words.

## 1.1 The building and its air

| Word | What it means, plainly |
|---|---|
| **Chiller** | The fridge. A big electric compressor that makes cold water. Reliable, expensive to run. |
| **Free cooling / economizer** | Cooling with outside air instead, so the compressor can be switched off. |
| **Mechanical** | Shorthand on screen for "chillers running". The opposite of free cooling. |
| **Condenser bank** | A row of heat-dumping equipment on the outside of the building. **This is where the hot air comes OUT.** Think of the radiator grille at the back of a fridge. |
| **Intake** | **Where the building sucks air IN.** A grille or louvre on the outside wall. This is the single most important word in the whole interface: everything the agent worries about is *the temperature of the air arriving at the intake*. |
| **Exhaust / plume** | The stream of hot air leaving the condenser bank and drifting away on the wind. A **plume** is just the shape that stream makes — like smoke from a chimney, invisible but warm. |
| **Recirculation** | When a building's own exhaust drifts back into its own (or its neighbour's) intake, so the intake air is warmer than the weather. |
| **Rise** | How many degrees Celsius warmer the intake air is because of recirculation. If the weather says 24 °C and rise is 0.35 °C, the air actually arriving is 24.35 °C. Usually a small number — and small is *good news*, it means the exhaust is escaping properly. |
| **Facade** | One outside wall of a building. |
| **Facade gap** | The distance between the two buildings' facing walls, in metres. A bigger gap means exhaust has more room to disperse before reaching the neighbour. |
| **Source / receptor** | The **source** is the building throwing heat out. The **receptor** is the building breathing it in. This project always studies a *pair*: one source, one receptor. |

## 1.2 Wind, and the word "bearing"

**Bearing** just means *direction, written as a number of degrees on a compass*.

- 0° = wind coming from the north
- 90° = from the east
- 180° = from the south
- 270° = from the west

That is all it is. When the interface says *"72 bearings solved"*, it means: the physics was
calculated separately for wind coming from 72 different compass directions — every 5 degrees all the
way round the circle (5, 10, 15 … 360 → 72 of them).

Why it matters: recirculation depends enormously on wind direction. If the wind blows the exhaust
*away* from the intake, rise is nearly zero. If it blows the exhaust *straight at* the intake, rise
is at its worst. The **critical bearing** is the single worst direction for a given site.

| Word | Plainly |
|---|---|
| **Downwind** | The intake is on the far side of the exhaust, so the wind carries exhaust towards it. The dangerous case. |
| **Upwind** | The intake is on the near side; wind carries exhaust away. Safe. |
| **Calm** | Wind speed is zero. The weather station reports no direction at all, because with no wind there *is* no direction. |
| **Refused** | The agent declines to give an answer for that wind direction. See 1.5. |

## 1.3 Time words

| Word | Plainly |
|---|---|
| **Forecast** | A prediction of the future. Here: what FortyGuard says the air will be like. |
| **Outcome** | What actually happened, measured afterwards. |
| **Lead** | How far ahead a forecast was made. A "9-hour lead" means the prediction was made 9 hours before the moment it describes. Short leads are easy; long leads are hard. |
| **Notice** | How much warning the *plant* needs before it can change mode. A plant with 3 h notice must commit to its 15:00 decision by 12:00. |
| **Horizon** | How far ahead the agent plans — here, 12 hours. |
| **Day-pair** | One forecast **plus** the matching outcome for the same window. You need *both* to know how wrong the forecast was. One alone tells you nothing. |
| **Hour-of-day group** | All the 3 p.m.s together, all the 4 a.m.s together, etc. Forecasts are not equally good at all hours, so the agent treats each hour separately. |

## 1.4 The safety margin, and the word "conformal"

This is the mathematical heart of the project, and it is simpler than it sounds.

The agent does not just predict a temperature. It produces an **upper bound**: a number it promises
the real temperature will stay below. Something like *"the intake will not exceed 25.8 °C."*

How do you choose that promise honestly? **You measure your own past mistakes.**

1. Collect a pile of past cases where you predicted something and later found out the truth.
2. For each, write down the error: `truth − prediction`.
3. Sort the errors. Find the value that 90 % of them came in under.
4. Add that value to every future prediction. That addition is the **margin**.

That is **conformal prediction**. It is not a model of the weather; it is bookkeeping on your own
track record. Its great virtue is that it needs no assumption about how the weather behaves — only
that tomorrow's mistakes look roughly like yesterday's.

| Word | Plainly |
|---|---|
| **Bound** | The promise. `bound = forecast + rise + margin`. The agent compares *this*, not the raw forecast, against the plant's limit. |
| **Margin (or quantile)** | The safety number added on, taken from the sorted list of past errors. |
| **Coverage** | The score. Out of all the times we made this promise, what fraction did reality actually respect? Aiming for 90 %. |
| **Nominal** | The coverage you were *aiming* for (90 %). |
| **Calibration set** | The past cases used to size the margin. |
| **Test / held-out** | Cases deliberately **not** used to size the margin, kept back to score it honestly. Marking your own homework with the answers you trained on proves nothing. |
| **Breach** | A time reality went above the bound. The promise broken. |
| **Mondrian** | A named refinement: instead of one margin for all hours, fit a *separate* margin for each hour of the day. Named after the painter whose canvases are divided into rectangles — the data is divided into groups the same way. |
| **α (alpha)** | The failure rate you accept. α = 0.10 means "I accept being wrong 10 % of the time", i.e. aiming for 90 % coverage. |
| **n** | How many past cases you have. **Small n is the project's biggest weakness** — see 1.6. |

## 1.5 Decision words

| Word | Plainly |
|---|---|
| **Plant limit** | The hottest intake air the operator will tolerate. Above it, chillers must run. |
| **Gate** | A condition that can block free cooling on its own. There are several (temperature, moisture, air quality…) and *any one* of them saying no means no. |
| **Binding constraint** | For a given hour, *which* gate was the one that actually decided it. Useful because it tells an operator what to fix. |
| **Schedule** | The output: a row of hours, each marked free-cooling or mechanical. Not a single yes/no — a plan across the horizon. |
| **Switch** | One change of mode. Going from mechanical to free cooling is one switch; going back is another. |
| **Switch budget** | The maximum number of switches allowed per day. Equipment wears out if you flip it constantly, so operators cap it. |
| **Dwell (minimum dwell)** | Once you change mode, the shortest time you must stay in that mode before changing again. Stops the plant "chattering" on and off. |
| **Refusal** | The agent declining to answer, rather than guessing. If a building physically blocks the line of sight between the exhaust and the intake, the physics model cannot produce a number it trusts — so it says so instead of inventing one. **A refusal is the agent working correctly, not failing.** |
| **Incumbent** | The thing the agent is compared against: what operators actually do today — a sensor on the roof, read reactively, with no forecast and no wind information. Beating a straw man proves nothing, so this baseline is tuned to be as strong as it fairly can be. |

## 1.6 Moisture and air words

| Word | Plainly |
|---|---|
| **Dew point** | The temperature at which air becomes so saturated that water starts condensing out of it. **A high dew point means humid air.** If you pull in air with a dew point of 21 °C and you have surfaces cooler than that, water forms on them — inside a building full of electronics. This is why a dew-point limit exists. |
| **Wet-bulb** | Another humidity measure: the temperature you would read on a thermometer with a wet cloth around it. Evaporation cools it, so drier air gives a lower reading. |
| **Air-quality index** | A number summarising how much unwanted material is in the air. Higher is worse. Filters cope up to a point; past it, you keep the dampers shut. |
| **ASHRAE** | The professional body that publishes the standards data-centre operators design to. When the interface says "ASHRAE max", it means the limit came from a published standard, not from someone's opinion. |

## 1.7 Words about the data itself

| Word | Plainly |
|---|---|
| **Tile** | FortyGuard returns air data as a grid of little squares over an area. Each square is a **tile** with its own temperature. About 17,800 tiles cover an 8 km × 8 km area here. |
| **Field** | One complete grid of tiles for one time window — a heat map. |
| **Heatmap call** | One request to FortyGuard's API for such a field. **Each one costs 4,220 credits**, which is real money. |
| **ASOS** | The US network of airport weather stations. Free, hourly, and going back years — this is where the five-year history comes from. |
| **Station** | The specific weather station used, named by its four-letter code: **KIAD** = Washington Dulles airport, **KORD** = Chicago O'Hare. |
| **OSM (OpenStreetMap)** | A free public map of the world. The building outlines used here are real OSM data, not drawings. |
| **OSM id** | The unique number OpenStreetMap gives one building. It is how you can go and check the building yourself. |
| **Swept** | A value was **not chosen** — every plausible value was tried and all the answers are reported. This matters enormously for honesty: if someone picks one number and reports one answer, you cannot tell whether they picked the flattering one. |
| **Provenance** | A record of where a number came from. |
| **Artefact** | A file the program wrote, holding results. Every number on screen is read from one. |

---

# Part 2 — The three screens

The demo is a single web page that moves through three stages. You cannot skip ahead, and that is
deliberate: the numbers on stage 3 depend on choices made on stages 1 and 2.

```
   STAGE 1: PICK                STAGE 2: CONFIGURE            STAGE 3: RESULTS
   Which data centre?     →     What kind of plant is it?  →  What the agent decided,
   (3 to choose from)           (12 settings on the left)     and every proof behind it
```

**Starting it:**

```bash
cd INTAKE-ARBITER/demo && python -m http.server 8000
# then open http://localhost:8000
```

Opening the file directly (a `file://` address) will **not** work — browsers block pages loaded that
way from reading data files, and you would see a red error. It must be served over `http`.

There are two modes, and the page tells you which one it is in near the top:

- **REPLAY** — every number comes from saved responses. No API key, no internet, no money. Fully
  reproducible: the same request to FortyGuard returns byte-for-byte identical data, which is why
  saved answers are as good as live ones for showing the method.
- **LIVE** — additionally lets the agent go and fetch a real forecast for the next few hours and
  decide on it, right now. Needs a key and a small local server, because a web page cannot hold a
  secret key (anything the page can read, every visitor can read).

---

# Part 3 — Stage 1: choosing a data centre

You get a dropdown with three sites, a short description, and a map.

## 3.1 The three sites, and why there are three

| Site | The pair of buildings | Weather station | Why it is in the list |
|---|---|---|---|
| **Ashburn, Virginia** | Amazon IAD116 → IAD117, facades 60.3 m apart | KIAD | The main site. The only one with FortyGuard forecast-vs-outcome measurements. |
| **Elk Grove Village, Illinois** (Chicago) | Stream Chicago II → Equinix CH3, 118.4 m apart | KORD | A **different climate** — colder and much windier. Tests whether the method travels. |
| **Dulles, Virginia** | Amazon IAD81 → IAD62, 137.7 m apart | KIAD (shared with Ashburn) | A **controlled experiment**. See 3.2. |

## 3.2 Why Dulles is the clever one

Dulles deliberately uses the *same weather station as Ashburn*. That means its weather is identical
by construction — same temperatures, same wind, same five years, to the hour.

So if Ashburn and Dulles produce different answers, the difference **cannot** be the weather. It can
only be the buildings: their shapes, their spacing, their operator. That is what scientists call a
**control** — you hold one thing fixed on purpose so that you can attribute any difference to the
other thing. It also cost nothing: no new weather to download, no FortyGuard calls.

Chicago is the opposite test: genuinely different weather, and you can watch which conclusions
survive.

## 3.3 Every line of the description, decoded

Selecting a site shows something like:

> **Ashburn, Virginia** — 106 OSM-tagged data centres, 43,763 hourly records from KIAD at 99.92 %
> coverage.
> Committed pair: **Amazon Web Services IAD116** → **Amazon Web Services IAD117**, facades 60.3 m
> apart.
> *FortyGuard field purchased for this site, and its own measured forecast error: 4
> forecast-and-outcome day pairs. Nothing here is borrowed.*

| The phrase | What it is telling you |
|---|---|
| **106 OSM-tagged data centres** | How many buildings in this area are publicly mapped as data centres. Evidence the area really is a data-centre cluster, not a guess. |
| **43,763 hourly records** | The size of the weather history: one reading per hour for five years. 43,763 out of a possible 43,824 — so almost no gaps. |
| **from KIAD** | Which weather station. |
| **99.92 % coverage** | How complete that history is. A thin record is useless, because the agent needs to fit a separate margin for each of 24 hours of the day, and you cannot do that on scattered data. |
| **Committed pair** | The two specific buildings studied — named, with the real operator names from the map. |
| **facades 60.3 m apart** | The gap between their facing walls. Note how close Ashburn's is: there is a hard minimum of 60 m below which the measurement becomes meaningless (the intake region would overlap the exhaust), and this pair clears it by 30 centimetres. |

---

# Part 4 — **Your specific question: "FortyGuard field purchased" vs "No FortyGuard field purchased"**

This deserves its own part, because it is the most easily misread thing on the page.

## 4.1 The short answer

It is about **what we have actually paid for at each site**, and there are **three** different states
— not two.

| What you see | Which site | What it means |
|---|---|---|
| *"FortyGuard field purchased for this site, and its own measured forecast error: 4 forecast-and-outcome day pairs. Nothing here is borrowed."* | **Ashburn** | We bought FortyGuard data here **and** we measured how wrong it was. Everything on this site's page is this site's own. |
| *"FortyGuard field purchased for this site."* **+** *"But no forecast/outcome day pair yet, so the measured level offset is still Ashburn's."* | **Chicago** | We bought **one** snapshot of FortyGuard data here — real, 17,797 tiles, this site's own. But one snapshot cannot tell you how *wrong* a forecast is, so the accuracy figure is still borrowed from Ashburn. |
| *"No FortyGuard field purchased here — its weather, geometry and hours are its own, but the measured level offset is Ashburn's."* | **Dulles** | We never bought FortyGuard data here at all. Everything else about this site is real and its own. |

## 4.2 The longer answer — why buying a field and measuring accuracy are different purchases

Think of it as two different questions you can pay to answer.

**Question 1: "What does FortyGuard say the air is like here?"**
Cost: **one** API call, 4,220 credits. You get a heat map — about 17,800 tiles across 8 km × 8 km.
This is a **field**.

**Question 2: "How wrong is FortyGuard here?"**
Cost: **two** API calls, 8,440 credits, *and* you have to wait.
Here is why two:

```
   Morning        Ask: "what will 2 p.m. be like?"        →  a FORECAST   (call 1)
   Afternoon      2 p.m. happens
   Evening        Ask: "what WAS 2 p.m. actually like?"   →  an OUTCOME   (call 2)

   Subtract one from the other  →  the ERROR.
```

You cannot get the error from one call, because a single measurement has nothing to be compared
against. And you cannot do it retroactively — you had to have asked *before* the moment arrived. That
pair of calls is a **day-pair**.

**Chicago's situation is exactly the middle case.** On 19 August we bought one field for Chicago — but
it was a *past* window, i.e. "what was 2 p.m. like yesterday?". That is an outcome with no forecast
beside it. Real data, genuinely Chicago's, and it shows you what FortyGuard resolves in Illinois — but
it cannot produce an error figure.

## 4.3 So what exactly is "borrowed", and what is not?

This is the crucial distinction, and the page is careful about it because it would be easy to imply
more than is true.

| For Chicago and Dulles | Whose is it? |
|---|---|
| Building outlines, spacing, orientation | **Their own** (OpenStreetMap) |
| Five-year weather history | **Their own** station (Chicago: KORD; Dulles: KIAD, deliberately shared) |
| Wind — direction and speed distribution | **Their own** |
| The physics — 576 exhaust-plume simulations on their real geometry | **Their own** |
| Chiller-hours saved per year | **Their own** |
| Electricity price used | **Their own state** (Illinois 11.81 ¢/kWh vs Virginia 8.72) |
| **The measured level offset** — how much FortyGuard runs warm or cool | ⚠ **Ashburn's, borrowed** |
| **The coverage figure** — 65.6 %, how often the promise held | ⚠ **Ashburn's, borrowed** |

**So: quote a site's hours as its own. Quote its accuracy as Ashburn's.** That sentence appears in
the data files, in the agent's own running commentary, and on the limits panel — deliberately, in
several places, so it cannot be missed.

## 4.4 Is this being fixed?

Yes, and it is running now. A scheduled task fires daily and asks FortyGuard for a Chicago forecast
in the morning, then reads the outcome the next day — giving Chicago its own measured offset. Two
calls, 8,440 credits per pair.

⚠ **But an offset is not a coverage figure.** One pair gives you "how much FortyGuard runs warm here".
A *coverage* figure — "how often does the promise hold" — needs about **ten** pairs, because you
cannot measure a 90 % success rate from a handful of tries. That is roughly 84,000 credits and at
least ten calendar days.

---

# Part 5 — **Your second question: Stage 2, every control in the left column**

After choosing a site you land on the configure screen. The left column holds twelve dropdowns. The
main panel on the right shows what this agent decides for this site.

## 5.1 First: the little coloured word next to each label

Every control has a small tag. **This tag is the honesty label** and it is the most important thing
in the sidebar:

| Tag | Meaning |
|---|---|
| **measured** | This came from a real observation. Nobody chose it. |
| **swept** | Every plausible value was tried and all results are available. The dropdown lets you see any of them. **Nothing was cherry-picked.** |
| **ASHRAE** | The value comes from a published professional standard, with a page reference. |
| **saved** | Selects which stored FortyGuard response to display. |

Why "swept" matters: suppose someone reports "we save 400 hours a year" having quietly picked the one
plant limit that flatters them. You could not tell. Here, the limit is a dropdown — **you** pick it,
and you can watch the answer get better or worse. The claim is not one number; it is the whole
surface, and you are invited to poke it.

## 5.2 The twelve controls, one at a time

### 1. Day — *measured*
Which real day to examine hour by hour. These are actual dates from the five-year weather record,
chosen to show different behaviours: a day where the decision flips mid-afternoon, a day that is
clearly cool, a day that is hot throughout, a day that would make the plant chatter.

*Changes:* the schedule, the hourly reasoning, the graphs. Not the annual totals.
**Why it exists:** so you can see the agent's logic on a concrete day rather than only in averages.

### 2. Plant limit °C — *swept* — choices 18 / 21 / 24 / 27
The hottest intake air this plant tolerates. Above it, chillers must run.

*Changes:* nearly everything. A 27 °C plant can free-cool for far more hours than an 18 °C plant.
**Why swept:** real plants differ, and there is no single right answer. Note that 27 °C is the top of
the published ASHRAE recommended range, so the sweep spans the real design space rather than a
convenient part of it.
**Try this:** set 18 °C and watch the agent declare almost everything mechanical. That is not a bug —
on a hot day, an 18 °C plant genuinely cannot free-cool, and the page explains that when it happens.

### 3. Notice needed, h — *swept* — choices 0 / 1 / 3 / 6
How many hours of warning the plant needs before changing mode.

*Changes:* the difficulty of the whole problem. At 0 h notice you may decide using the current
reading. At 6 h you must commit six hours early, using a forecast — and a 6-hour-ahead forecast is
much less certain, so the safety margin grows and you lose some hours.
**Why it exists:** this is the *entire reason FortyGuard is needed*. At 0 h notice a thermometer is
enough. At 3 h it is useless, and only a forecast will do.

### 4. Level anchor — *swept* — "one local reading" / "none — believe FortyGuard"
Does the plant have one thermometer of its own on site?

- **one local reading** — yes. The agent uses it to correct any consistent warm/cool bias in the
  forecast.
- **none — believe FortyGuard** — no. The agent must trust the forecast's absolute level.

*Changes:* this is the single most consequential switch on the page. With an anchor, the agent gains
about **+406 hours a year**. Without one, it **loses about 156 hours a year** — the agent is *worse*
than the incumbent.
**Why it exists, and why that losing number is on screen:** it is the honest boundary of the product.
The *safety* guarantee needs no customer hardware; the *hours* do. Switch to "none" and watch the
headline collapse — that row is deliberately not hidden.

### 5. Forecast skill — *swept* — e.g. 0.00 / 0.50 / 0.90 "vs persistence"
How good the forecast is assumed to be, compared to the laziest possible forecast.

"Persistence" is that lazy baseline: *"it will be the same as it is now."* Surprisingly hard to beat
at short range. A skill of 0 means no better than lazy; 0.9 means far better.

*Changes:* better skill → tighter margin → more free-cooling hours.
**Why it exists:** so nobody has to take a vendor's accuracy on trust. You can ask "what if the
forecast were mediocre?" and see the answer. The shipped headline uses **0.50** — the middle, not the
flattering end.

### 6. FortyGuard level day — *measured* — four dates with a °C value
Which of the four **measured** offsets to apply. Each entry is a real day where we compared a
FortyGuard forecast against the outcome and found how far off the *level* was.

The four are: −0.8396, −0.8115, **+0.1520**, −3.7127 °C.

*Changes:* the correction applied to the forecast's absolute level.
**Why it exists, and this is worth understanding:** notice how different those four are. Three say
FortyGuard was reading about 0.8 °C too warm; one says it was 3.7 °C off. A bias that *varies* like
that cannot be learned away — if you assumed one fixed correction you would be pretending to
knowledge you do not have. So the agent rotates through them, always leaving one out to test against
the others. Picking a single one and reporting the good result is exactly the mistake this control
exists to prevent.

### 7. Max dew point °C — *ASHRAE* — off / 15 / 18
The humidity gate. Above this dew point, outside air is too damp to bring in, whatever its
temperature.

*Changes:* blocks free cooling on muggy days that pass the temperature test. On the five-year record
this gate is the deciding factor about **11 %** of the time.
**Why "ASHRAE":** 15 °C is not somebody's guess — it is the maximum dew point in a published Green
Grid / ASHRAE guideline, with a page reference. An earlier version of this project used an invented
humidity rule and it was removed for exactly that reason: a number a human typed, producing a
behaviour, with no source behind it.

### 8. Air-quality limit — *swept* — off / index ≤ 73.5
The contamination gate. Above the limit, keep the dampers shut regardless of temperature.

*Changes:* very little here — it binds about **0.1 %** of hours.
**Why it exists anyway, and why the small number is admitted:** LBNL's study says contamination is a
*top* reason operators refuse free cooling, so the gate must exist for the product to be credible.
But FortyGuard's index has no documented units, so the threshold is swept rather than claimed, and
the measured effect is reported as tiny rather than talked up.

### 9. Condenser bank — *swept* — "longest facade (real)" / "end wall (sensitivity)"
Where on the building the hot-air equipment sits.

- **longest facade (real)** — along the long wall. What the site actually looks like.
- **end wall (sensitivity)** — bunched on the short end wall. A deliberately awkward alternative.

*Changes:* dramatically. On the end wall, the building's own shape blocks the line of sight between
exhaust and intake, so the agent **refuses** to answer for many wind directions — and refusing means
falling back to chillers. The cost of that is about **−3,124 hours a year**.
**Why it exists:** it is the project's own worst case, priced and displayed. The headline is *only*
valid for the real placement, and this control is how you check that claim rather than trusting it.

### 10. Switch budget — *swept* — 1 / 2 / 4 per day
How many mode changes per day the operator permits.

*Changes:* a tight budget forces the agent to be choosier about which hours are worth switching for.
**The interesting part:** tightening this *helps* the agent's relative position, because the reactive
incumbent — which just responds to whatever the sensor says — blows through the budget constantly (on
212 days out of 913 at a budget of 1), while the agent plans within it. Being able to plan ahead is
worth more when the constraint is tighter.

### 11. Min dwell, h — *swept* — 1 / 3
Minimum time in a mode before changing again. Stops the plant chattering.

*Changes:* very little — it is the deciding factor in **1 hour out of 1,336**.
**Why it is on screen anyway:** it is one of only two constraints a simple thermostat could not
handle at all, and the honest thing is to say it is *nearly vacuous* rather than present it as a
selling point.

### 12. FortyGuard field — *saved*
Which stored FortyGuard heat map to display in the "Screen zero" panel.

**This is the control that differs most between sites**, and it is the visible consequence of Part 4:

- **Ashburn** — eight entries, four forecast/outcome pairs, labelled by date.
- **Chicago** — one entry, `observed past window`: its own purchased snapshot.
- **Dulles** — **empty and greyed out.** Nothing was purchased, so nothing is offered. The panel says
  so in words rather than showing Ashburn's map with a caveat.

---

# Part 6 — Stage 3: the results, panel by panel

Press **Run the agent** and the page works through the loop, then shows fourteen panels. Here is each
one, in the order you meet it.

## 6.1 "The agent, working" — the live commentary

Short lines appear one at a time as the agent goes through its stages: *reading 4 FortyGuard
day-pairs… solving 576 plume fields on the GPU… refusing 36 of 72 bearings it cannot stand behind…
widening its own margin by +0.0043 °C, unprompted…*

**What to notice:** the numbers in those sentences are not decoration. There is a rule enforced by
the build: **no sentence template in the program may contain a digit.** Every number you see arrived
from a computation and was inserted at display time. That is checked mechanically, and it means "the
agent computed this" is something you can verify rather than believe.

**Honest note:** the *pace* at which lines appear is just presentation — a reveal cadence, labelled
as such. The content is real; the drama is not a measurement.

## 6.2 "Right now — the next hours, decided live"

Only appears in LIVE mode. The agent asks FortyGuard about hours that have not happened yet, applies
the same physics and the same margin, and emits a schedule.

**The most important behaviour here is a refusal.** If FortyGuard does not answer for some hours, the
agent publishes **no schedule at all** rather than filling the gaps with "run the chillers". Once, it
did exactly that — presented a 12-hour plan where 9 of the hours had never been asked about — and that
is now recorded as the worst output the project has produced. The rule that came out of it: *a
schedule may only be published over hours the agent actually perceived.*

The card also carries its own limitations right next to the numbers: the margin came from only 4
day-pairs, 90 % coverage is not even arithmetically reachable at that sample size, the measured
coverage was 65.6 %, the pre-registered test **failed**, and the margin is being used at leads it was
never measured at. A live number with a hidden calibration story is worse than no live number.

## 6.3 "What it is worth, measured over five real years"

Headline tiles, plus the **Download PDF** button.

| Tile | Reading it |
|---|---|
| Free cooling delivered | Hours per year the agent actually free-cools. |
| Chiller-hours avoided | The gain **versus the incumbent** — the number that matters. Not total hours; the *extra* hours. |
| Coverage | How often the promise held. Shown at **65.6 %** against a 90 % target — a failure, on the front page. |
| Plan stability | How often a re-plan changes nothing. |

**Why "chiller-hours avoided" and not money or kWh:** converting degrees to kilowatt-hours honestly
requires the plant's own equipment curves. The money panel later does price *part* of it, with the
sources, and says loudly which part.

## 6.4 "The decision — a schedule, not a thermostat"

A two-row chart across the hours of the chosen day.

- **Top row — Agent.** What the agent decided for each hour.
- **Bottom row — Incumbent.** What today's reactive sensor-based approach would have done.

Colour tells you the mode: free cooling versus mechanical. **Click any hour** to make every other
panel explain that hour.

**What to look for:** hours where the two rows disagree. That is the product. Typically the agent
switches *earlier* — because it can see the change coming — and avoids a late scramble.

## 6.5 "The site — real imagery, real footprints"

A real aerial photograph of the actual site, with the two building outlines drawn on top: the source
in one colour, the receptor in another, plus the plume direction. Drag to pan, scroll to zoom.

**Why it is here:** so you can check that these are real buildings in a real place rather than a
diagram. The outlines are the same shapes the physics simulation used.

⚠ **A caveat the panel states itself:** at 0.3–0.5 m per pixel you can see *objects* but not
*nameplates*. You cannot tell a chiller from a generator. So the imagery supports "these are big
industrial buildings with rooftop and yard equipment" — it does not certify what any specific unit is.

## 6.6 "The plume, solved — turn the wind and watch the exhaust move"

The one to play with. A heat-map of the air around the buildings showing how much warmer it is,
computed by an actual fluid simulation on the real geometry. Turn the wind dial and watch the warm
region swing round.

**What the colours mean:** brightness = degrees of warming above the ambient air. The scale is on the
panel.

**Why a simulation and not a drawn cone:** a drawn cone would hide its own errors. This one was
checked against **67 real field experiments** from a classic 1956 dispersion study, and that check
found our plume is somewhat *too wide* at these distances, which means it **under-predicts** warming
by 5–25 %. Under-predicting is the *unsafe* direction — and the panel says so on screen. That is the
opposite of hiding a limitation.

## 6.7 "Turn the wind — 72 bearings solved on the real geometry"

A compass dial. For each of the 72 wind directions it shows whether the intake is downwind, and what
the resulting rise is. Drag it.

**Reading it:**
- The **critical bearing** is the worst direction. Ashburn's is 255°; Chicago's is 240°; Dulles's is
  265°. Different buildings, different worst directions — as you would expect.
- Directions marked **REFUSED** are ones where a building blocks the path, so the model declines to
  produce a number.

**Perspective:** the worst rise is about 0.36 °C at Ashburn. That is small — and small is *good*. It
means this site's exhaust escapes properly. Which is also why the project leads with the forecast,
not the plume: the plume's value here is *refusal and safety*, not extra hours.

## 6.8 "Screen zero — FortyGuard's field, doing the work first"

FortyGuard's own data, drawn as the grid of tiles it arrives as. This is the vendor's product, shown
before any of our processing.

**This panel differs by site — see Part 4:**
- **Ashburn** — forecast and outcome for four dates, 17,862 tiles each. You can flip between the
  forecast and what actually happened.
- **Chicago** — its own single purchased window, 17,797 tiles, labelled as one past window and not a
  day-pair.
- **Dulles** — **empty, with an explanation.** Nothing was purchased here, so nothing is drawn.

## 6.9 "Why — the agent's own reasoning, checkable"

For the selected hour, in plain sentences: what the forecast said, what the plume added, what margin
was applied, what the bound came to, which gate decided it, and **how close the call was**.

**"Binding constraint"** is the key phrase: which single condition decided this hour. Counted across
all 1,336 explanations in the shipped file:

| What decided the hour | Share |
|---|---|
| Dry-bulb temperature (plain heat) | 46.9 % |
| Nothing — free cooling was simply fine | 32.7 % |
| Dew point (too humid) | 10.8 % |
| Refusal (geometry blocked the path) | 6.6 % |
| Switch budget (already switched enough today) | 3.0 % |
| Air quality | **0 hours** — nothing at all, in this configuration |
| Minimum dwell | 0.1 % — **one hour out of 1,336** |

**Read the bottom two rows honestly.** Air quality and minimum dwell are the two constraints a simple
thermostat could not possibly handle — so they are the most impressive-sounding — and they are also
very nearly irrelevant in practice. Saying so is the point.

**Why it is trustworthy:** every one of those 1,336 explanations was checked by *re-running the agent*
and confirming the claim, with zero failures. The explanation is not a story written next to the
result; it is a claim that gets tested.

## 6.10 "The self-scoring loop — including where it failed"

Step 7 of the loop, made visible: the agent scoring itself and adjusting.

You see each test day, whether reality respected the bound, and the margin **widening** when it did
not. Nobody types the new margin. It comes out of the errors.

**And the failure is here, not hidden:** measured coverage **65.6 %** against a 90 % promise, worst
day **0.0 %**, and the pre-registered pass conditions **FAILED**. Pre-registered means the pass mark
was written down *before* any result existed, so it could not be moved afterwards.

## 6.11 "How the bound is built — the arithmetic, run in front of you"

The most unusual panel: it does the conformal arithmetic *live in your browser*, and prints its own
answer beside the one the Python program computed, with the difference — **0.0 °C**.

Two sliders: **α** (the failure rate you accept) and **n** (how many past cases you have). Move them
and watch which order statistic gets picked.

**The one thing to take away from this panel** — it is the clearest statement of the project's central
weakness:

| Situation | n | Best coverage arithmetically possible | Is the shortfall arithmetic? |
|---|---|---|---|
| The four real FortyGuard days | **4** | **80 %** | **Yes, entirely.** With 4 cases the highest promise you can make is 4/5 = 80 %. **90 % is not reachable, and no amount of programming reaches it.** Only more data does. |
| The twelve per-lead bounds on five years of weather | **≥ 21,838** | **99.995 %** | **No, not at all.** These run 91.4–92.0 % — all *above* the 90 % target. |

**Same mathematics, opposite outcomes.** The method is fine — proved by the second row. The
FortyGuard calibration is starved of data — the first row. Those are very different criticisms and
the panel refuses to let them blur.

## 6.12 "Five years of real hours"

The five-year backtest as a ladder: start from a bare comparison and add one realistic constraint at a
time, showing what each does.

| Step | Gain, hours/year |
|---|---|
| Bare comparison, no constraints | +65.6 |
| + switch budget 2, min dwell 3 h | +85.6 |
| + dew-point gate 15 °C | +118.8 |
| + 3 h notice, mid-range forecast skill | **+405.7** ← the shipped configuration |
| + no local sensor | **−156.0** ← **the agent LOSES** |

**Read the last row.** It is on screen on purpose. Without one local thermometer, five years of real
weather say this agent is worse than what operators already do.

**And the counter-intuitive bit:** adding *constraints* (switch budget, humidity gate) makes the agent
look **better**, not worse — because those constraints hurt the reactive incumbent more than they hurt
something that can plan.

## 6.13 "What it is worth in money — and the three reasons it is an upper bound"

Dollars, with every input swept rather than chosen: 4 published electricity tariffs × 4 published
chiller efficiencies = 16 combinations, none collapsed.

**The unit is per megawatt of IT load.** This project has never measured a data centre's *size*, and
inventing one would multiply the headline by a number nobody measured. A reader who knows their own
load multiplies once themselves. So: never "saves $X million" — there is nothing here to multiply by.

**Three qualifications, and all three make the real number smaller:**

1. **Compressor only.** Fans, pumps and cooling-tower fans keep running — and an air-side economizer
   moves *more* air, so fan power can **rise**. The unmeasured term has the *opposite sign*.
2. **Code-minimum efficiency is the optimistic end.** Real hyperscale plants beat the standard, and a
   better chiller saves less per hour switched off.
3. **State-average tariffs, not the site's own contract.**

The worst cell anywhere in Ashburn's sweep is **−$61,538 per MW-IT per year** — the refusal guard
firing on the awkward equipment placement. It is on screen, not filtered out. (Each site has its own
worst cell, because each is priced on its own state's electricity.)

## 6.14 "Honest limits — stated before anyone asks"

The last panel. Every known weakness, in one place, and — importantly — **generated from the data
files rather than typed**, so a limitation cannot quietly disappear from the screen while remaining
true in the files.

It covers: the 90 % bound not holding yet; the hours claim depending on a local sensor;
recirculation being small here; heat passing straight through buildings (so refusal is about geometry,
not absorption); air quality not being backtestable over five years; the dollar figure being a
ceiling; and "designed for the edge, not verified on it" — because the GPU kernel is small enough for
edge hardware, but nobody has run it on any.

---

# Part 7 — A ten-minute guided tour

Do these in order, and you will have seen the whole argument.

1. **Pick Ashburn.** Read the description. Note "4 forecast-and-outcome day pairs. Nothing here is
   borrowed."
2. **Press Configure, then Run the agent.** Watch the commentary. Remember: no sentence template
   contains a digit.
3. **Go to the schedule.** Find an hour where the Agent and Incumbent rows disagree. Click it.
4. **Read "Why".** See which gate decided that hour and by how much.
5. **Set Level anchor to "none — believe FortyGuard".** Watch the headline fall from +406 h/yr to
   −156. **This is the honest limit of the product**, on screen, in one click.
6. **Set it back. Now set Plant limit to 18 °C.** Watch almost everything go mechanical, and read the
   note explaining that 43.7 % of all swept configurations do exactly that.
7. **Set Condenser bank to "end wall (sensitivity)".** Watch refusals appear and the annual figure go
   sharply negative. That is the agent declining to guess, priced.
8. **Open "How the bound is built."** Drag *n* down to 4. Watch 90 % become unreachable. This is the
   project's main weakness, shown as arithmetic rather than described.
9. **Now switch to Chicago.** Note: its own weather, its own wind, its own buildings, its own
   electricity price — but the coverage tile is still labelled as Ashburn's.
10. **Switch to Dulles.** Note the FortyGuard panel is empty and says why. Then note its weather
    figures are *identical* to Ashburn's — that is the deliberate control, not a bug.

---

# Part 8 — Quick reference

## 8.1 If you only remember five things

1. The agent decides using a **bound** (`forecast + rise + margin`), never a raw forecast.
2. The **margin is measured from its own past errors**, and it widens itself when it is wrong.
3. **Everything decision-shaping is swept, not chosen** — you can move every dial yourself.
4. **Refusing to answer is correct behaviour**, and it is priced rather than hidden.
5. The headline **depends on one local thermometer**. Without it, the agent loses. That is on screen.

## 8.2 Numbers you will see, and what they are

| Number | What it is |
|---|---|
| **43,763** | Hours of real weather (KIAD, five years). Chicago's is 43,775. |
| **120,960** | Configurations swept by the agent. |
| **17,862** | Tiles in one FortyGuard field at Ashburn. Chicago's own field has 17,797. |
| **576** | Plume simulations per site (72 wind directions × 8 wind speeds). |
| **65.6 %** | Measured coverage against a 90 % promise. **A failure, reported as one.** |
| **4** | FortyGuard day-pairs held. **Nine are needed** for a 90 % bound, plus one to score it. |
| **80 %** | The best coverage arithmetically possible with 4 pairs. |
| **+405.7 h/yr** | The headline gain, in the shipped configuration. |
| **−156 h/yr** | The same agent with no local sensor: it **loses**. |
| **0.3550 °C** | Ashburn's worst recirculation warming. Chicago's is 0.4108; Dulles's 0.3593. |
| **4,220** | Credits for one FortyGuard heatmap call. Real money. |

## 8.3 Glossary, alphabetical

**α (alpha)** — the failure rate you accept; 0.10 → aiming for 90 % coverage.
**ASHRAE** — the professional body whose published standards the limits come from.
**ASOS** — the free US airport weather-station network; source of the five-year history.
**Bearing** — wind direction in compass degrees (0 = from north, 90 = from east).
**Bound** — the promise: forecast + rise + margin. What the decision is actually made on.
**Breach** — a time reality went above the bound.
**Calibration set** — past cases used to size the margin.
**Chiller** — the electric fridge that cools by compressor. Expensive to run.
**Condenser bank** — the outdoor equipment where hot air leaves the building.
**Conformal prediction** — sizing a safety margin from your own measured past errors.
**Coverage** — the fraction of times the bound actually held.
**Day-pair** — a forecast plus its matching outcome. Needed to measure error at all.
**Dew point** — the temperature at which water starts condensing out of air; high = humid.
**Downwind** — the intake is on the far side, so wind carries exhaust towards it. The risky case.
**Dwell** — the minimum time you must stay in a mode before switching again.
**Economizer / free cooling** — cooling with outside air, compressor off.
**Facade** — one outside wall. **Facade gap** — the distance between two facing walls.
**Field** — one complete grid of FortyGuard tiles for one time window.
**Gate** — a condition that can block free cooling on its own.
**Held-out** — data deliberately kept back from calibration, used only for honest scoring.
**Horizon** — how far ahead the agent plans (12 hours here).
**Incumbent** — the reactive, sensor-only approach operators use today; the comparison baseline.
**Intake** — where the building sucks air in. The place every number is ultimately about.
**Lead** — how far ahead a forecast was made.
**Level offset** — a measured consistent warm/cool bias in the forecast.
**Margin** — the safety number added to the forecast, taken from past errors.
**Mechanical** — chillers running; the opposite of free cooling.
**Mondrian** — fitting a separate margin per hour-of-day instead of one for all hours.
**n** — how many past cases you have. Small n caps how strong a promise you can make.
**Nominal** — the coverage you were aiming for (90 %).
**Notice** — how much warning the plant needs before changing mode.
**OSM** — OpenStreetMap; source of the real building outlines. **OSM id** — one building's unique number.
**Plume** — the drifting stream of hot exhaust air.
**Provenance** — the record of where a number came from.
**Recirculation** — a building breathing its own exhaust.
**Refusal** — the agent declining to answer rather than guessing.
**Rise** — degrees of extra warmth at the intake caused by recirculation.
**Source / receptor** — the building emitting heat / the building breathing it in.
**Station** — the weather station used (KIAD = Dulles airport, KORD = Chicago O'Hare).
**Swept** — every plausible value was tried and all results reported; nothing cherry-picked.
**Switch / switch budget** — one mode change / the daily cap on them.
**Tile** — one small square of a FortyGuard grid, with its own temperature.
**Wet-bulb** — a humidity measure; the reading from a thermometer wrapped in a wet cloth.

---

## One last thing — why so much of this page is about failure

Most demos show only what works. This one puts a failed pre-registration, a losing configuration, a
priced refusal, two rejected sites, an under-predicting plume model and a borrowed calibration
directly on screen.

That is a deliberate choice, and the reason is simple: **the only claims worth anything are the ones
that could have come out the other way.** A number you cannot check, from a system that never reports
a bad result, tells you nothing about the next number it produces. Everything here is arranged so that
you can go and check — the dials move, the arithmetic runs in front of you, and the limitations are
generated from the same files as the headlines.
