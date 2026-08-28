<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 06 - Glossary

Every term this project uses that is not ordinary English, defined in plain language before it is
used elsewhere in the pack. This file exists because of standing rule **B1**: the user is learning
conformal prediction, decision theory and psychrometrics *while* building this, so a term appearing
in the project's own documents does not mean it is shared vocabulary.

**No figures live here.** Numbers belong in `01-STATE.md`, where they are generated from the
artefacts. If you want to know how many sites there are, look there, not here.

---

## 1. The physical problem

**Data centre cooling, in one paragraph.** Computers turn electricity into heat. A data hall has to
dump that heat outside. There are two ways. If the outside air is cool enough you can simply blow it
through, which costs only the electricity to run a **fan**. If it is not, you have to run a
refrigeration cycle, which costs the electricity to run a **compressor**. A compressor costs far more
than a fan. So every hour the outside air is cool enough and you run the compressor anyway is money
burned for nothing.

**Free cooling.** Cooling the hall with outside air rather than with refrigeration. Also called
*air-side economising*. The "free" is relative: you still pay for fans, just not for a compressor.

**Economiser.** The equipment that lets a plant switch between outside air and refrigeration.

**Chiller.** The refrigeration machine. Contains the compressor. Slow to start and slow to stop,
which is the whole reason this project exists: a chiller needs **hours of notice** to switch, and a
thermometer only tells you about *now*.

**Condenser.** The outdoor part that rejects heat to the air. Ground-mounted condensers breathe air
at roughly **2 m above the ground**, which is why a forecast at 2 m is the relevant one and a
forecast at 10 m or a satellite skin temperature is not.

**Switchover / notice hours / forecast lead.** How far ahead the plant learns what the air will do.
More notice means more of the cheap hours are actually usable, because the plant has time to act
before they arrive.

**Dry-bulb temperature.** Air temperature as an ordinary thermometer reads it.

**Wet-bulb temperature.** What a thermometer reads with a wet wick over the bulb, so evaporation
cools it. Always at or below dry-bulb. It tells you how much cooling you could get by evaporating
water, so it is the limit for evaporative equipment.

**Dew point.** The temperature at which the air's moisture would start condensing. It caps how far
some equipment can go without making water where you do not want it.

**Psychrometrics.** The physics of moist air: how temperature, humidity, dew point and energy content
relate. The reason a decision cannot be made on dry-bulb alone.

**ASHRAE allowable range.** The industry body's published envelope of temperature and humidity a data
hall may operate in. Widening what counts as "cool enough" widens the free-cooling hours, which is
why the standard's version matters to the arithmetic.

**IT load, in MW.** How much electrical power the computers draw, which is very nearly how much heat
must be removed. Savings scale with it, so a saving is quoted *per MW* to stay comparable between a
small hall and a large one.

**Tariff.** The price of electricity. Savings depend on it, so a money figure without a tariff is not
a figure.

---

## 2. Where the heat goes: plumes

**Plume.** The hot air a condenser throws out. It does not vanish; it drifts, rises and spreads.

**Recirculation.** When one unit's hot exhaust reaches another unit's (or its own) air intake. The
intake then breathes air hotter than the weather, so the plant performs worse than the forecast says
it should. This is the failure mode the geometry work is about.

**Source and receptor.** The **source** is the unit emitting the plume. The **receptor** is the intake
that might breathe it. A **source-receptor pair** is one specific exhaust and one specific intake,
with a real distance and a real bearing between them.

**Gaussian plume model.** The standard way to estimate how a plume spreads: concentration falls off
from the centreline in a bell-curve shape, wider the further downwind you go.

**Plume rise.** Hot exhaust is buoyant, so it climbs before it levels off. How high it gets decides
whether it passes over an intake or into it. **Briggs** is the standard set of plume-rise formulas.

**Atmospheric stability class (Pasquill-Gifford).** A letter, A through F, describing how turbulent
the air is. Turbulent air (A) mixes a plume away quickly; stable air (F) lets it stay concentrated.
The same geometry recirculates differently under different classes.

**Prairie Grass.** A classic 1956 field experiment whose measurements are still used to check that a
dispersion model is calibrated. Used here as an external reference rather than a self-check.

**Geometry refusal.** When the physical arrangement of a site means the agent *cannot* honestly
promise the hour, it **refuses the hour** rather than guessing. Refusing is a first-class output of
this agent, not an error.

---

## 3. The data

**FortyGuard.** The vendor whose API supplies the forecast this project is built on. Its distinguishing
property here is that it forecasts air temperature **2 m above the ground**, which is the height the
equipment actually breathes.

**Field.** A purchased grid of forecast values covering an area, as opposed to a single point reading.

**Day-pair (forecast/outcome pair).** One forecast plus the *elapsed* outcome it can be scored
against. You cannot measure a forecast's error until the day it forecast has happened, so a field on
its own is not a calibration. **This is the scarcest resource in the project.**

**Hindcast.** Running a forecasting method over a past period whose answers are already known, to see
how it would have done. Cheap, because it needs no waiting.

**Backtest.** The same idea applied to a decision rather than a forecast: replay history and ask what
this agent would have decided, and what that would have cost.

**METAR / ASOS.** Standard aviation weather observations from airport stations, hourly, free and long.
Used here as the independent ground truth. **KIAD** is Washington Dulles, the station behind the
Ashburn site.

**OpenStreetMap (OSM), way, relation.** The open map database the facility registry is built from. A
**way** is a line or building outline; a **relation** groups ways together. A facility key like
`CA_way_209087373` is a state code plus the OSM object it came from, so every site in the registry
traces to a real mapped building rather than to a guess.

**Metro versus facility.** A **facility** is one mapped site in `unified_sites.json`. A **metro** is
an entry in `sites.json`, which is what the agent actually runs on and what the picker offers. They
are related by `metro_key`, and the counts are **not** the same number. See `01-STATE.md`.

**Offerable / ready to run.** A site the picker will let you open because a full agent run has been
published for it. Decided by `sites.json`'s `offerable` flag and nothing else, deliberately: the map
once coloured its dots from a stale baked `status` string and disagreed with its own caption.

**Site category.** `cluster` (a multi-building campus), `pair` (an exact source-to-receptor pair) or
`single` (standalone, no tagged neighbour). Carried on the map as marker size.

---

## 4. The statistics

**Prediction interval.** Not a single predicted number but a range, with a stated probability that
the truth lands inside it. "Interval" and "bound" are used interchangeably here.

**Conformal prediction.** A way of turning any forecaster into one that emits *ranges with a
guarantee*, without assuming the errors follow any particular distribution. The recipe: take a set of
past cases where you know the answer, measure how wrong the forecaster was on each, and use the
distribution of those past errors to size the range for a new case. The guarantee is
**distribution-free**, which is why this project uses it rather than a normal-distribution error bar.

**Calibration set.** The past cases whose errors size the interval. Its size is the hard limit on what
coverage you can promise: with *n* cases the best achievable is *n/(n+1)*, so **3 day-pairs cannot
promise 90 %** no matter how the maths is arranged. This is arithmetic, not a modelling choice.

**Nonconformity score / residual.** How wrong the forecaster was on one past case. Usually the
absolute error.

**Quantile.** The value below which a given fraction of a set falls. The 90th percentile of past
errors is the number that sizes a 90 % interval.

**Coverage.** The fraction of cases where the truth actually landed inside the interval. **Promised**
coverage is what the method claims; **measured** coverage is what happened. This project publishes
both, including where measured falls short of promised, on screen.

**Marginal versus conditional coverage.** *Marginal* means the promise holds on average over
everything. *Conditional* means it holds for each subgroup separately: every site, every hour of the
day, every weather regime. Marginal coverage can be perfect while some subgroup is badly served.
There is a **distribution-free impossibility result**: exact conditional coverage cannot be had for
free. Standing rule A1 requires that this be stated rather than papered over.

**Mondrian / group-conditional conformal.** The practical middle ground: split the cases into a few
declared groups and calibrate within each. Recovers a real guarantee per group without claiming the
impossible.

**Adaptive conformal (ACI / DtACI).** Adjusts the interval's width over time as errors come in, so it
recovers when conditions shift. **Dt** is "dynamically tuned": the adjustment rate itself adapts.

**Effective sample size.** How many *independent* cases you really have. Adjacent hours are highly
correlated, so 24 hourly readings are worth far fewer than 24 independent observations, and a naive
count overstates confidence.

**Pre-registered test.** A test whose pass/fail criterion is written down *before* the result is
known, so it cannot be reinterpreted afterwards. This project's demo shows a pre-registered test that
was **NOT MET** on screen, deliberately. A demo that only shows success is not evidence.

**Holdout.** Cases deliberately withheld from calibration so they can score it honestly.

**Knife-edge hour.** An hour where the decision is nearly a tie, so the bound's width, not the
forecast's centre, decides the outcome. Where a bound earns its keep.

---

## 5. Verification vocabulary used in this repo

**Artefact.** A file a build step wrote (`trace.json`, `backtest.json`, a field file). The
authoritative source for any published figure. Prose is never the source.

**Cross-implementation verifier.** A check that runs the *browser's* copy of the agent against the
*Python* copy on the same inputs and requires identical output. There are five, covering the decision,
the conformal bound, the explanations and the event stream. They exist because the page reimplements
the agent in JavaScript, and two implementations that drift are worse than one.

**Byte-identical render gate.** `verify_site_panels.py` renders one site **twice** and requires the
output to be byte-identical before it will believe that a difference between two *different* sites
means anything. This is why animations in this page use deterministic easing curves rather than
spring physics.

**Difference test, and what it cannot catch.** Diffing rendered panels across sites proves each site
draws its own data. It **cannot** catch a *wrong* picture: one site's overlay on another's photograph
still differs, so it passes. A separate audit check bans any site's own coordinates, OSM ids and
station from appearing on another site's page for exactly this reason.

**Boundary remedy.** When a colour pair is kept for a validated reason but sits under a contrast
floor, the fix is a *checked* structural remedy (a border, a cased canvas mark) rather than a waiver.
`verify_palette.py` asserts all parts of the remedy exist, or fails as though there were none.
