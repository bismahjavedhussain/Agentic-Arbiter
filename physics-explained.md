# The Physics, Explained From Zero

**What this document is.** Every equation the agent uses, in plain words, with its source and an
honest label saying how much we actually know. Written for someone with no background in fluid
mechanics or statistics. No code — concepts, equations, and small tables only.

**Why the labels matter more than the equations.** The single biggest mistake made during this project
was treating a number from a computer simulation as if it were a measurement. That cost four days and
one falsified claim. So every quantity below carries a tag:

| Tag | Meaning |
|---|---|
| 🟩 **VERIFIED-MATH** | Checked against exact mathematics by our own test. Needs no measurement. Cannot be wrong unless the maths is wrong |
| 📘 **SOURCED** | From a published document I opened and quoted directly during this work |
| 📗 **NAMED-SOURCE** | A standard published result. I name the reference but did **not** open the primary text — treat as "well known", not "I checked it" |
| 🔧 **FITTED** | We chose the number by fitting it to real measured data |
| ✏️ **OURS** | Our own choice with no external basis. Always swept across a range, never quoted as a single value |
| 🔴 **GAP** | Physics we know is missing or wrong, stated deliberately |

If a judge points at any number, you should be able to say which tag it has. That is the whole point.

---

# Part 1 — The problem in one page

A data centre is a building full of computers. Computers make heat. That heat has to be dumped
outside, and the machine that dumps it is a **condenser** — a big array of fans blowing outdoor air
over hot metal tubes, exactly like the radiator in a car, just much larger.

Here is the trap. The condenser **breathes in** outdoor air on one side and **blows out** hot air on
the other. If some of that hot exhaust curls back around and gets sucked into the intake, the machine
is breathing its own exhaust. It now has to work harder for the same cooling. This is called
**recirculation**.

**The exact words from the field study we rely on** 📘:

> *"Recirculation is defined as the entrainment of a portion of the hot air leaving the ACC into the
> inlet air stream drawn by the fans from the surrounding atmosphere. This results in an average inlet
> air temperature to the ACC that is higher than the far field or ambient temperature."*
> — Maulbetsch & DiFilippo, California Energy Commission **CEC-500-2013-065**, page 63

So the operator faces a question they cannot answer: *what temperature is the air my condenser is
actually breathing, right now?* A weather forecast tells you the temperature of the neighbourhood. It
does not tell you the temperature two metres in front of a fan that is being fed its own exhaust.

Because they cannot answer it, they do the safe thing: **carry a permanent margin.** Assume it is
always a bit hotter than the forecast says, and run the cooling harder every hour of every year.

**Our claim is not that we can predict the temperature better.** It is that on most days the wind
carries the exhaust *away* from the intake, and on those days the margin is being paid for nothing —
and that we can tell which days are which.

---

# Part 2 — The chain, end to end

```
  FortyGuard                our physics               our statistics            the decision
 ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
 │ air temp on a│         │ how much     │         │ how wrong    │         │ turn on extra│
 │ 60 m grid,   │  ────►  │ hotter is the│  ────►  │ have we been │  ────►  │ cooling now, │
 │ 2 m above    │         │ intake than  │         │ in the past? │         │ or wait?     │
 │ ground, 12 h │         │ the grid?    │         │ → safety     │         │              │
 │ ahead        │         │              │         │   margin     │         │              │
 └──────────────┘         └──────────────┘         └──────────────┘         └──────────────┘
   Part 3                   Parts 4-7                 Part 8                   Part 9
```

Each box has its own equation and its own honesty label. Let me take them one at a time.

---

# Part 3 — What FortyGuard gives us 📘

From FortyGuard's own published material:

| Property | Value |
|---|---|
| Forecast horizon | **12 hours** |
| Time resolution | *"Forecasts are delivered hour by hour, not as averaged windows or daily summaries"* |
| Spatial resolution | Down to **20 m** in their downscaling models; **60 m** is the finest we can request via the API |
| Height | roughly **2 m above ground** |
| Method | machine learning conditioned on *"surrounding atmospheric, surface, and terrain conditions"* |
| Refresh rate | ❗ **not published anywhere** — we measured it ourselves (Part 11) |

**What we verified ourselves** 🟩: the 12-hour horizon is real and it is a hard edge. Requests at 9.25 h
and 11.25 h lead returned full data; requests at 13.25 h and 17.25 h returned nothing. A 9.41 h lead
returned **17,862 tiles** over 64 km².

**The crucial limitation, and it is the whole reason our physics exists.** A 60 m grid square is 3,600
square metres. A condenser intake is a few metres across. Whatever happens in the last few metres —
your own exhaust curling back — cannot possibly be inside a number that describes a 60 m square.
FortyGuard say this themselves: their blind spots are *"dense equipment, reflective surfaces, or
nearby structures."*

**So our job is to bridge from a 60 m average to one specific intake.** That bridge is physics.

## 3.1 🟩 But first — are we adding something that is already in there?

**The question that had to be answered before any physics was allowed.** If FortyGuard's field already
contained a wind-blown warm patch downwind of a heat source, then adding our own plume on top would be
**double-counting** — we would be charging the customer twice for the same degree.

**How we tested it, at no cost.** 25 fields already paid for — one 2 × 2 km area at 100 m, five dates ×
five two-hour windows — decomposed to ask how many independent spatial patterns are present. Wind came
from the Dulles airport weather station (FortyGuard serves none), and spanned **178°** across those 25
times, so the test had the range needed to see a wind effect if one existed.

**The result.** A single fixed spatial pattern explains **99.9971 %** of the spatial variation across all
25 fields. Removing that one pattern leaves **0.0011 °C** out of 0.212 °C. Several field pairs are
identical in shape to **six decimal places**, including pairs from *different dates*.

**In plain words:** over a 2 km area, the 397 numbers FortyGuard returns are **one fixed picture, one
brightness dial, and one offset.** Three things, not 397.

**Then we checked whether that was about the area or the resolution**, because in our earlier data the
two were tangled — every small area we had was 100 m and every large one 60 m. Six paid calls, fully
crossed, same date, same two hours:

| area | resolution | tiles | is it one fixed pattern? |
|---|---|---|---|
| 2 km | 100 m | 397 | **yes** — shape identical to 6 decimals |
| 2 km | **60 m** | 1,120 | **yes** — identical statistic |
| 8 km | 100 m | 6,445 | no — genuinely structured |
| 8 km | **60 m** | 17,862 | no — genuinely structured |

**It is the AREA, not the resolution.** And asking for 60 m instead of 100 m over the same 2 km returns
**2.8× more tiles with the same information** — the statistic matches to six decimal places.

## 3.2 ✅ What this licenses, and what it does not

**LICENSED:** the field carries no independent structure *within* 2 km. A condenser plume is a few
hundred metres across. **It cannot be in there. So our plume is ADDITIVE, not double-counted.** This is
a load-bearing architectural assumption and it is now measured rather than assumed.

**NOT LICENSED:** *"FortyGuard ignores wind."* Their own description says the model is conditioned on
*"atmospheric, surface, and terrain conditions"*, and wind may well be inside that without producing
structure we can detect in a two-hour maximum. We tested what is **observable in the output**, nothing
more. That distinction is preserved in everything we report to them.

**One practical trap, if you ever rebuild this.** FortyGuard's tile grid is **rotated about 1.55° from
north** — stepping one tile east also moves you 2.7 m north, so no two tiles in a row share a latitude.
Building a raster by grouping on latitude values silently produces a mostly-empty array. It cost us one
confidently wrong result before we caught it.

---

# Part 4 — Heat moving in air: the one equation everything rests on 📗

Hot air does exactly two things:

1. **It gets carried along by the wind.** This is called **advection**. If the wind blows east at
   6 m/s, a puff of hot air moves east at 6 m/s. Nothing subtle.
2. **It spreads out and mixes with cooler air.** This is called **diffusion** (more precisely,
   turbulent mixing). The puff gets wider and weaker as it travels.

Put those together with a source of heat and you get the equation:

```
∂T/∂t  =  − u ∂T/∂x − v ∂T/∂y   +   D (∂²T/∂x² + ∂²T/∂y²)   +   S
   │              │                        │                      │
 how the      carried by              spread out by            heat added
temperature    the wind               mixing (D is            by the
changes       (u = east-west         "diffusivity")           condensers
over time      v = north-south
               wind speed)
```

**Reading it in words:** *the temperature at a point changes because wind brings different air in,
because mixing smears out sharp differences, and because something is heating the air.*

📗 **Source:** this is the standard **advection–diffusion equation** for a scalar quantity in a flow.
It is textbook continuum mechanics, in every fluid dynamics and air-pollution text. Nothing about it
is our invention. *(Named as standard; no primary text opened for this document.)*

## What we solve, and how we checked it

We cannot solve that equation with a pencil for a real site with buildings, so we solve it numerically:
chop the ground into a grid of squares, and step forward in small time steps until nothing changes any
more (**steady state**).

🟩 **VERIFIED-MATH.** For the one case where the equation *does* have an exact pencil-and-paper answer
— flat open ground, steady wind, one small source — our code reproduces that exact answer to
**0.00 % error at three different grid resolutions**, and conserves heat to **0.00 %** at every
distance downwind. Details in Part 6.

**Why that matters.** It separates two questions people constantly confuse:

| Question | Name | Our status |
|---|---|---|
| Is the code solving the equation correctly? | **verification** | ✅ **yes, exactly** |
| Is the equation the right description of a real data centre? | **validation** | 🟡 partial, and honestly limited |

A model can pass the first and fail the second. Most of the honest caveats in this document are about
the second.

---

# Part 5 — How wide does the plume spread? The one constant that used to be invented

The equation above has a constant `D`, the **diffusivity** — how fast hot air spreads sideways. Big `D`
means the plume fans out wide and dilutes quickly. Small `D` means it stays a narrow, hot ribbon.

**This was originally 8 m²/s with no justification whatsoever.** Our own test file said, in writing,
*"INVENTED — no basis at all."* That is now fixed, and here is how.

## Step 1 — what our solver does with `D` 🟩

If the wind is strong enough that we can ignore mixing *along* the wind direction (true here — the
relevant number, the **Péclet number**, is 1500, and it only needs to be much bigger than 1), then
the maths collapses to something simple.

Travelling downwind a distance `x` at speed `u` takes a time `t = x / u`. During that time the heat
spreads sideways by diffusion, and for diffusion the **variance** grows as `2 D t`. Substituting:

```
σ_y²  =  2 D x / u                    σ_y = the plume's half-width, in metres
```

**In words:** *the plume's width squared grows in proportion to distance travelled, divided by wind
speed.* Faster wind ⇒ less time to spread ⇒ narrower plume.

🟩 **We verified this exactly.** Fitting a straight line to measured σ_y² against distance in our own
solver gives a slope of **2.6667**, and `2D/u = 2 × 8 / 6 = 2.6667`. Agreement to **0.00 %** at grid
spacings of 20 m, 10 m and 5 m. This test needs no measurement — it is our code against algebra.

## Step 2 — what the published physics says the width should be 📘

Air-pollution engineering has measured plume widths since the 1950s and tabulates them by
**stability class** — a letter from A to F describing how turbulent the air is, determined by wind
speed and sunshine:

| Class | Conditions | Plain description |
|---|---|---|
| A | strong sun, light wind | very turbulent, plumes fan out fast |
| B, C | sunny, moderate wind | unstable |
| D | overcast or windy | **neutral** — the default |
| E, F | clear calm night | stable, plumes stay narrow and travel far |

For each class there is a published formula for the plume half-width, with `x` and `σ_y` in metres:

| Class | σ_y | 
|---|---|
| A | 0.493 x^0.88 |
| B | 0.337 x^0.88 |
| C | 0.195 x^0.90 |
| D | 0.128 x^0.90 |
| E | 0.091 x^0.91 |
| F | 0.067 x^0.90 |

📘 **Source:** read directly from *Table 3, "Equations and data for Pasquill-Gifford Dispersion
Coefficients"*, in a Pasquill-Gifford model document (linked in Part 12). Class A and class D rows
independently confirmed via a second search. **Honest limit:** this table is standard textbook material
(the usual attribution is Crowl & Louvar, *Chemical Process Safety*, reproducing Martin 1976). **I did
not open that primary text.** So the correct thing to say is *"cross-checked in two secondary
sources"*, not *"verified against the primary"*.

## Step 3 — so `D` is now derived, not invented

We have two expressions for the same plume width. Set them equal at the distance that matters and
solve for `D`:

```
    √(2 D x / u)  =  a x^b            →            D  =  u · a² · x^(2b−1) / 2
```

For our test geometry — condenser bank edge at x = 860 m, intake at x = 1090 m, so a **separation of
230 m** — at 6 m/s wind:

| Class | plume half-width at 230 m | **implied D** |
|---|---|---|
| A very unstable | 59.0 m | 45.5 |
| B unstable | 40.4 m | 21.3 |
| **C slightly unstable** | 26.0 m | **8.84** |
| D neutral | 17.1 m | 3.81 |
| E slightly stable | 12.8 m | 2.15 |
| F stable | 9.0 m | 1.04 |

**The invented value of 8.0 turns out to be Pasquill class C — slightly unstable, a perfectly ordinary
hot sunny afternoon.** It landing in the right range was luck, not derivation. **It now has a source.**

**And it caught a real error in our own sensitivity study.** We had swept `D` over 4–16, an invented
range, and concluded diffusivity was *"the least influential"* constant. Over the **full published
range** (1.04–45.5) its influence is **2.7× larger** than we reported. But the class is not a free
choice — it is *determined* by wind speed and sunshine, and for a hot afternoon at 5–6 m/s it is class
C or D, over which the influence is **smaller** than we reported. So the conclusion survives, and now
for a stated reason instead of a lucky guess. **Quote both numbers, never just the flattering one.**

## Step 4 — the gap this exposes 🔴

Look at the exponents. Published plumes widen as **x^0.88 to x^0.91** — almost exactly proportional to
distance. Our constant-`D` model widens as **x^0.5** — the square root. **These are different shapes.**

A single `D` can therefore match reality at **exactly one distance**. Matching neutral conditions at
230 m:

| distance | published table | our model | error vs table | **error vs MEASURED (N-35)** |
|---|---|---|---|---|
| 50 m | 4.3 m | 8.0 m | +84 % | **+53 %** |
| 230 m | 17.1 m | 17.1 m | 0 % | **0 %** |
| 1000 m | 64.2 m | 35.6 m | −44 % | **−34 %** at 800 m |

🟩 **These are now measured, not inferred.** N-35 fitted the plume-width exponent to **67 independent
field experiments** (Project Prairie Grass, 1956) and got **0.805**, against the table's 0.88-0.91 and
our 0.50. Because the measured exponent is a little gentler than the table's, **our error is smaller
than we had been claiming** -- we were being pessimistic. The measured 0.805 is itself a lower bound,
since the truncation filter rejects the widest plumes at long range (15 % at 800 m vs 1 % at 50 m).

🔴 This is a **known, named limitation** of constant-diffusivity ("Fickian") models at short range: real
atmospheric turbulence contains swirls of many different sizes, so a plume spreads faster than a single
fixed diffusivity allows. Our model is **locally valid near the distance it was matched at** and gets
progressively wrong away from it. Since real separations are 150–600 m, `D` should be matched **per
site**, not once globally.

**How to say this out loud:** *"Our dispersion model is a constant-diffusivity approximation matched to
the published Pasquill-Gifford curve at each site's own separation distance. It is accurate at that
distance by construction and degrades away from it — +84 % at 50 m, −44 % at 1 km. That is a stated
approximation, not a hidden one."*

---

# Part 6 — How much heat goes in: the source term ✏️🔧

The `S` in the equation is the heat the condensers add. We model it as:

```
S  =  ΔT_discharge / t_exchange          in degrees per second
```

**In words:** *a condenser blows out air some number of degrees hotter than ambient, and that heat
gets mixed into the local air over some number of seconds.*

| Quantity | Value | Tag | Basis |
|---|---|---|---|
| `ΔT_discharge` | 11 °C | ✏️ **OURS**, swept 7.8–13.9 | Chosen inside a published 14–25 °F condenser discharge range |
| `t_exchange` | 47.4 s | 🔧 **FITTED** | Fitted to ~40,000 measured points from six real power-station condensers |

**How the fit was done and what it achieved** 🔧: two constants were fitted on three power plants and
then scored on **three plants never used in the fit** — the standard way to avoid fooling yourself.
Result: **RMS error 0.126 °C against a signal of 0.923 °C**, i.e. about 14 %. That is the project's
only quantitative agreement with reality.

**The honest half of the same result:** the *shape* of the wind-speed dependence was **not** validated
— held-out correlation only **+0.082** — because the measured dependence spans just 0.20 °C, so there
is almost no shape to fit. **The magnitude transfers; the shape does not.** We claim the first and not
the second.

---

# Part 7 — The dimension we do not have 🔴

This is the **largest single gap** in the physics, and it should be said before anyone asks.

Real air moves in three dimensions. Hot air is **lighter than cold air, so it rises.** Whether a plume
sails harmlessly *over* an intake or gets dragged down into it depends on the competition between two
things:

- **buoyancy**, pushing the plume up, and
- **wind**, bending it over and pressing it down

In light wind the plume climbs and misses. In strong wind it is bent flat and can be dragged into the
intake — an effect called **downwash**.

**Our solver is two-dimensional. It has no vertical direction at all.** It cannot represent a plume
rising or being bent over, because in our model there is no "up".

**What we do instead** 🔧: we multiply the source strength by a fraction that depends on wind speed:

```
f(U)  =  U^p / (U^p + u_c^p)          p = 1.25,   u_c = 8 m/s
```

**In words:** *at low wind speed most of the heat escapes upward and only a small share stays in the
layer we model; at high wind speed most of it stays down.*

🔴 **Be completely clear about what this is.** It is **not** a published formula. The *shape* is loosely
motivated by plume-rise physics, but the two numbers were **fitted to the power-station data**, and it
is standing in for an entire missing dimension. Closing this gap properly means writing a
three-dimensional solver, which is beyond a hackathon.

**How to say it:** *"The solver is 2-D. The vertical dimension — whether the plume lifts over the
intake or is pressed into it — is represented by a single fitted wind-speed function rather than
modelled. That is the biggest approximation in the physics and it is why I quote a band."*

## 7.1 📘 What the industry standard says — ASHRAE Chapter 46, now actually read

This chapter is **the** professional treatment of our exact problem: exhaust from a building reaching an
air intake. Reading it changed the picture materially, and mostly in our favour.

**Their dilution equation, Equation (18):**

```
                4 U_H σ_y σ_z         ⎛  Δ²  ⎞
    D_r(x)  =  ───────────────  · exp ⎜ ──── ⎟          Δ = vertical separation, plume to intake
                   V_e d_e²           ⎝ 2σ_z²⎠
```

For a flush vent with no stack, Δ = 0 and this reduces to their **Equation (22)**:
`D_s(x) = 4 U_H σ_y σ_z / (V_e d_e²)`.

`D` is the **dilution factor** — how many times weaker the contaminant is at the intake than at the
exhaust. Higher is better. Since the exhaust volume flow is `Q_e = A_e V_e = (π d_e²/4) V_e`, this
rearranges to a form directly comparable with ours:

```
    D = π U σ_y σ_z / Q_e          so      ΔT_intake = ΔT_exhaust · Q_e / (π U σ_y σ_z)
```

### 🟩 The single most useful thing in the chapter: our missing dimension has a *known sign*

| | dependence |
|---|---|
| **ASHRAE, 3-D** | ΔT ∝ 1 / (U · **σ_y · σ_z**) |
| **Ours, 2-D** (verified exactly in Part 4) | ΔT ∝ 1 / (U · **σ_y**) |

**The difference is exactly one factor of σ_z.** We have no vertical dilution at all. And because σ_z
*grows* with distance in reality, the real plume keeps diluting vertically as it travels while ours
does not.

**So our 2-D simplification makes us over-predict the intake temperature, increasingly so at larger
separations.** For a *safety margin*, over-predicting is the safe direction to be wrong.

That reframes Gap #1 completely. It is no longer *"we are missing a dimension and who knows what that
does"* — it is *"we are missing a known term, its absence biases us conservative, and here is the
industry-standard equation that says so."*

### 📘 And ASHRAE makes the same kind of deliberate simplification, in print

> *"For all exhausts except very hot flue gases from combustion appliances, it is recommended that
> plume rise from buoyancy be neglected in dilution calculations and stack design on buildings. **By
> neglecting buoyant plume rise, the predicted dilution has an inherent safety factor**, particularly
> at low wind speed, where buoyancy rise is significant."*
> — ASHRAE Handbook — HVAC Applications 2019, Chapter 46, page 46.8

The industry standard **deliberately drops the buoyant rise term to stay conservative and says so.**
"We simplified in the conservative direction and stated it" is not a hackathon excuse — it is the
professional practice.

### 📘 A ratio we can now use instead of guess

From their Equation (21): `i_y = 0.75 i_x` and `i_z = 0.50 i_x`, so in the near-field
mechanical-mixing regime

```
    σ_z / σ_y  =  0.50 / 0.75  =  0.667
```

A sourced number where we previously had nothing.

### 🟩 ASHRAE independently corroborates the field data that killed our own worst mistake

ASHRAE states plainly that wind speed has **two competing effects** — at low speed the jet rises and
misses the intake, at high speed the plume is stretched and diluted — so there is a **critical wind
speed in between at which dilution is worst.** For capped stacks and flush vents they recommend:

```
    U_H,crit = 400 fpm = 2.03 m/s = 4.5 mph
```

Now line that up with everything else we have:

| source | worst-case wind speed | |
|---|---|---|
| **CEC field data**, six instrumented condensers | peak in the **0–5 mph** bin | 📘 measurement |
| **ASHRAE recommendation** for flush vents | **4.5 mph** (2.03 m/s) | 📘 industry standard |
| **our N-22 fitted curve** | peaks at **7.5 mph** (3.35 m/s) | 🔧 our fit |
| ~~N-11's retracted claim~~ | ~~20.1 mph (9 m/s)~~ | ❌ **retracted, from a CFD figure** |

**Three independent lines now put the worst case in the low-wind regime**, and ASHRAE's 4.5 mph lands
*inside* the CEC field data's peak bin. The claim we retracted was wrong by a factor of four, and it is
now contradicted by the industry standard as well as by the measurements. **ASHRAE also confirms the
*shape* N-11 was reaching for was real** — there genuinely is a critical worst-case speed. It just is
not at 9 m/s.

## 7.2 🔴 But their magnitude formula does not apply to our geometry — and that matters

We tried to use Equation (22) as an independent magnitude check. **It does not work here, and the
reason is worth stating because it is a point in our favour.**

ASHRAE's equations are written for rooftop **stacks and vents** — sources small compared with the
distance travelled. Our condenser deck is 60 × 120 m:

| quantity | value |
|---|---|
| deck area `A_e` | 7,200 m² |
| effective diameter `d_e = √(4A_e/π)` | **95.7 m** |
| ASHRAE initial source size `σ_o = 0.35 d_e` | **33.5 m** |
| Pasquill class C `σ_y` at the 230 m intake | **26.0 m** |

**The source is wider than the plume it creates**, and 42 % as wide as the whole separation distance.
Pushed through anyway, Equation (22) returns a dilution **below 1** at a realistic fan velocity — which
is physically impossible, since dilution starts at 1 and only increases. The formula is simply outside
its regime.

**Two honest consequences:**

1. **We cannot use ASHRAE for a magnitude cross-check.** We can use it for the structure, the σ_z/σ_y
   ratio, the σ-versus-distance shape, and the critical wind speed — all of which we now do.
2. **There is no standard closed-form answer for our case.** A 7,200 m² condenser deck at 230 m
   separation falls between the rooftop-vent formulas and full CFD. **ASHRAE's own recommendation for
   complex building environments is wind tunnel modelling** — it says the analytical equations are not
   adequate there. So a numerical solver is the *appropriate* tool for this geometry, not a shortcut.

**A third source against our √x.** ASHRAE's near-field spreads grow roughly **linearly** with distance
(`σ ≈ i·x` plus the initial size in quadrature). Pasquill-Gifford says **x^0.88–0.91**. Ours says
**x^0.5**. **Two independent standards now agree that our shape is the outlier** — which is exactly why
`D` is matched per site at the separation that matters, and why the +84 % / −44 % errors in Part 5 are
stated rather than buried.

---

# Part 8 — 🔴 The most important honesty in this document: plume versus vortex

This is the caveat most likely to be found by a sharp judge, so volunteer it.

**What we model:** a plume that leaves the condensers, travels *downwind*, spreads out, and some of it
arrives at an intake some distance away.

**What the field data we calibrated against actually measured** 📘:

> *"The physical cause of recirculation is known to be the establishment of vortices which form
> starting at the upstream edge of the ACC and expand in the downwind direction... As the size of the
> vortex grows, it becomes large enough to direct flow under the bottom of the wind walls and into the
> ACC air inlet region."*
> — **CEC-500-2013-065**, page 63

**Those are not the same mechanism.** A **vortex** is a swirl — like the curl of air behind a moving
lorry — that forms at the *upstream* edge of the equipment and pulls hot air **backwards and downwards**
into the machine's own inlet. It is inherently three-dimensional and it goes *against* the wind
direction near the ground.

**Our 2-D downwind plume model cannot represent that at all.**

**What this means, precisely:**
- The **magnitudes** are comparable — both mechanisms deliver roughly 1 °C of intake warming, and our
  fit reproduces the measured magnitude to 14 % on held-out plants.
- The **mechanisms differ.** So the calibration matched *how much*, not *how*.
- Our model is a better description of **one facility's exhaust reaching a neighbour's intake** (a
  downwind plume) than of **one machine breathing its own exhaust** (a vortex).

**How to say it:** *"The field data I calibrated against measured vortex-driven self-recirculation at a
power station's own inlet. I model a downwind plume reaching a neighbouring intake. The magnitudes
agree to 14 % on held-out plants, but they are different mechanisms, and I would not claim my model
captures self-recirculation."*

Also 📘 note from the same report: their own comparison between field measurements and CFD simulation
disagreed, and the report recommends further testing to resolve it. **A CFD result is a simulation, not
a measurement.** Confusing those two is the exact error that cost this project four days.

---

# Part 9 — ✅ A defect we found, measured, and FIXED

In our code, a building is represented by **forcing those grid cells to stay at ambient temperature**.
That sounds harmless. It is not: a cell pinned to a fixed temperature **absorbs** heat without limit.

We measured it. Placing a 120 × 200 m building across an otherwise perfectly-conserving plume:

| | heat arriving downstream |
|---|---|
| open ground | **100.0 % conserved** |
| building in the way | **0.3 % — 99.7 % of the heat vanished** |

In reality, air flows **around** a building. It is deflected, not destroyed.

**And it was corrupting the headline number, not just blocked directions.** **21 of the 49 cells** in
the intake averaging disc lie *inside* the neighbour building. They were pinned to a rise of exactly
zero, dragging the reported intake temperature **down 43 %**. We were averaging the inside of a
building into an air-intake temperature — not a modelling choice, a bug.

## ✅ What was changed, 2026-08-12

1. **Intake averaging uses air cells only.** Building interiors excluded; the code raises if the whole
   averaging region falls inside a structure.
2. **Obstacles are transparent to the temperature field** — pinning removed from **both** the CPU and
   the GPU kernel, checked deliberately because the previous defect was exactly a CPU/GPU divergence.
   **Conservation re-verified at 100.00 % at every station**, straight through the building.
3. **A line-of-sight check that refuses to answer.** Where a building sits between source and intake
   *and* the intake is downwind, the system reports **"not modelled"** rather than a number.

## Why transparent, and not a reflecting wall

A mirrored (adiabatic) wall restores conservation but creates a **worse** artifact here, because the
velocity field is uniform and does not know the buildings exist. Heat would advect into the wall and
pile up with nowhere to go, and our intake sits **10 m upwind** of the neighbour's face — so that fake
stagnation hotspot would land directly on it. That trades a number that is too low for one that is too
high, with no way to say which is closer.

📘 **ASHRAE justifies transparent for this geometry.** Chapter 46 distinguishes a **visible** intake
(direct line of sight to the source) from a **hidden** one (behind an obstruction) and applies a
correction — a conservative factor of 2.0 — only to hidden intakes. Our intake has direct line of
sight, so *no building correction* is the sourced treatment. Across demo_site's compass the
line-of-sight check finds **no blocked direction**, confirming it is the visible case.

## What the re-run did

| | before | after |
|---|---|---|
| N-8 worst-direction baseline | +0.4369 °C | **+0.8045 °C** |
| N-19 headline · band | +0.455 · 0.219–0.940 | **+0.839 · 0.415–1.713** |
| N-23 knife-edge ratio | 13.6× | **27.0× — stronger** |

**No qualitative conclusion changed. Only the levels, and they moved up.** One test (N-8) now fails its
own pre-registered threshold, because that threshold was written in *absolute* degrees while the
baseline doubled — relatively the worst direction still releases ~10 % of the margin, against ~11 %
before. **The threshold was mis-specified; the physics was not.** Recorded as a fail rather than moved.

## 🔭 What remains, and what would close it

Transparent is a **stated approximation, not the right answer.** The right answer is a
**mass-consistent (divergence-free) wind field**: zero the velocity inside obstacles, then solve one
Poisson equation for a correction potential so the flow travels *around* them. Standard
diagnostic-wind-model practice (MATHEW/CALMET family, after Sherman 1978) — one extra Poisson solve.

**Not shipped, for one reason: it adds an approximation we cannot yet check.** The dataset that would
check it is **CEDVAL** wind-tunnel flow *and concentration* measurements around an isolated rectangular
building — literally our geometry. The access request is sent. **With it, blocked directions stop being
refusals and become numbers.**

---

# Part 10 — The safety margin: conformal prediction 📗

We now have a predicted intake temperature. It will be wrong. The question is: **by how much, at worst?**

The naive approach is to guess a margin. The honest approach is to **measure your own past mistakes**:

```
Every day:  write down what you predicted, and later what actually happened.
            The gap between them is a "residual".

To make a 90 % upper bound:  sort all past residuals, and take the one such that
                             90 % of them are smaller. Add that to today's prediction.
```

Formally, with `n` past residuals `d = (actual − predicted)`, sorted, the bound is

```
q  =  the k-th smallest residual,  where  k = ⌈(n + 1)(1 − α)⌉        α = 0.10 for 90 %
bound  =  today's prediction  +  q
```

**Why `(n+1)` and not `n`?** That small correction is what makes the guarantee valid with a *finite*
number of past days rather than only in the limit of infinitely many. The penalty for having little
data lives in that formula rather than in a fudge factor.

📗 **Source:** this is **split conformal prediction**, a standard method. Standard references are
Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World* (2005), and the tutorial by
Angelopoulos & Bates (2021). **Named, not opened for this document.**

**The guarantee, and its one condition.** Conformal prediction promises at least 90 % coverage
**provided** past days and today are interchangeable — loosely, "similar weather". **They are not.**
Weather drifts. So the guarantee is conditional, and whether the drift is small enough is an empirical
question — which is exactly why we are measuring it (Part 11).

🔴 **A limit worth stating plainly.** Our residuals compare **FortyGuard's forecast** to **what
happened**. So the margin covers *forecast* error. It is **blind to solver error** — because we have
never once observed a real condenser intake temperature to compare against. **One temperature logger at
one real intake would close this**, and that is the single highest-value physical measurement anyone
could make for this project.

---

# Part 11 — The decision: why waiting is a real choice 📗

Extra cooling capacity needs notice — a chiller takes time to come online — and it costs energy every
hour it runs. Once an hour the agent chooses: **start it now, or wait?**

**Waiting is attractive** because the forecast gets sharper as the hour approaches, and because
starting later means paying for fewer hours.

**Waiting is dangerous** because capacity needs lead time. Wait too long and the hot hour arrives
before the cooling does.

**Why this is not a threshold.** A threshold rule says *"if the forecast exceeds X, act."* That cannot
express *"how much better will I know this in three hours, and will I still be able to act on it?"*
The right action depends on the value of information you have not received yet.

The standard tool is **backward induction** (dynamic programming): work backwards from the last hour
at which acting is still useful.

```
value of being at hour t  =  minimum of:
        cost of acting now
        expected cost of waiting, using the value of being at hour t+1
```

📗 **Source:** standard **optimal stopping / dynamic programming**, from Bellman onward. Textbook
material. **Named, not opened.**

**What we tested, and what it depends on** 🟩: we built the best possible threshold rule as an
adversary — every hour of the day × every margin, tuned exhaustively on 20,000 training days — and
scored both on 20,000 **held-out** days. The stopping rule wins, **but only if forecasts genuinely
sharpen**. If they never sharpen, it **loses**. That is why measuring the sharpening rate is the single
most important live measurement in the project.

**As of writing, that measurement is running**, and the first two data points confirm that FortyGuard
issues genuinely new forecasts between requests — **100 % of 17,862 tiles changed** between a 9.41-hour
and a 7.49-hour lead, with an RMS change of 0.255 °C. So new information really is arriving; the
question is whether it is *better* information.

---

# Part 12 — Master table: what is verified, fitted, and assumed

| Quantity | Value | Tag | Basis |
|---|---|---|---|
| Advection–diffusion equation | — | 📗 | Standard continuum mechanics |
| Our solver reproduces its exact solution | 0.00 % error | 🟩 | Own test, 3 grid resolutions |
| Heat conservation | 0.00 % error | 🟩 | Own test, every station |
| Plume width law σ_y² = 2Dx/u | slope 2.6667 | 🟩 | Own test vs algebra, exact |
| Published plume widths σ_y = a x^b | b = 0.88–0.91 | 📘 | Pasquill-Gifford table, cross-checked twice |
| Diffusivity `D` | 8.84 (class C) | 📘 | **Derived** from the above, was invented |
| Discharge temperature rise | 11 °C | ✏️ | Inside a published range; swept 7.8–13.9 |
| Exchange time | 47.4 s | 🔧 | Fitted to 6 power stations, held-out RMS 0.126 °C |
| Downwash function | p=1.25, u_c=8 | 🔧🔴 | Fitted; stands in for a missing dimension |
| Vertical dispersion | **absent** | 🔴 | Solver is 2-D |
| Buildings | **transparent** | 🔧✅ | Were heat sinks absorbing 99.7 % of a crossing plume. **Fixed 2026-08-12**; conservation re-verified at 100.00 %. Blocked directions now refuse to answer |
| Conformal bound | ⌈(n+1)(1−α)⌉ | 📗 | Split conformal prediction |
| Bound covers solver error | **no** | 🔴 | Calibrated on forecast residuals only |
| Stopping rule | backward induction | 📗 | Standard optimal stopping |
| Forecast sharpening rate | **being measured** | 🔄 | The claim depends on it |

---

# Part 13 — The gaps, ranked by how much they matter

| # | Gap | Why it cannot be closed now | What would close it |
|---|---|---|---|
| **1** | **No vertical dimension** | 2-D solver; plume rise is the dominant real mechanism for whether exhaust reaches an intake | A 3-D solver |
| **2** | **Plume ≠ vortex** | Field data measured vortex self-recirculation; we model a downwind plume | Data-centre measurements, or a 3-D model |
| ~~**3**~~ | ~~**Buildings absorb heat**~~ | ✅ **CLOSED 2026-08-12.** Obstacles made transparent, intake averaging restricted to air cells, line-of-sight refusal added. All five dependent tests re-run; absolute levels roughly doubled, no conclusion changed | *Remaining:* a mass-consistent wind field so plumes go **around** buildings — one Poisson solve, but it needs CEDVAL to validate |
| **4** | **Bound is blind to solver error** | Never observed a real intake temperature | **One temperature logger at one intake** |
| **5** | **σ_y ∝ x^0.5 not x^0.9** | Fickian limitation | Match per site; or a proper dispersion parameterisation |
| **6** | **Rural coefficients used** — worth a **factor of 2** | 🟢 **MEASURED, N-36.** The urban (McElroy-Pooler) set halves the headline: +0.839 → +0.422–0.489 °C. Ashburn is between grassland and a city core, so the truth is between. **We report rural because it is the conservative pick, and state that urban would halve it.** Not a gap any more — a stated choice with a measured size |
| **7** | **No data-centre measurement anywhere** | None published | A site partnership |

**None of these are hidden.** All of them are quotable in the form *"here is the gap, here is why it
is open, here is what would close it."* That is a stronger position than pretending they do not exist.

---

# Part 14 — How to check this yourself: real datasets

Two independent public datasets can test our physics against reality. Neither is a data centre — but
between them they cover the two mechanisms we model.

## 14.1 Project Prairie Grass (1956) — for the dispersion part 📘

The canonical field experiment for exactly this question: how wide does a plume get?

| | |
|---|---|
| What | ~70 releases of sulphur dioxide tracer near O'Neill, Nebraska, July–August 1956 |
| Measured | concentration on arcs at **50, 100, 200, 400 and 800 m** downwind, sampled at 1.5 m height |
| Why it fits us | those distances **span our range of interest** (150–600 m separations) |
| Terrain | flat, open, no buildings — so it isolates the dispersion physics from the building physics |
| Status | *"the data from the experiment still represent the most complete available for the analysis of surface layer dispersion"* |
| Where | listed at [harmo.org/classic.php](https://www.harmo.org/classic.php); data posted under [harmo.org/jsirwin](https://www.harmo.org/jsirwin/PrairieGrassDiscussion.html); also on [OSF](https://osf.io/u78ac/) and in the ASTM D6589 package |

✅ **DONE -- N-35.** Files downloaded (`PGARCS.txt`, `PGrassTTUU.txt`), 340 arc records across 68
experiments parsed, stability taken from the measured vertical temperature gradient at 7 heights.

**Result: median plume-width exponent 0.805 over 67 experiments, median R2 0.998.** That confirms the
published 0.88-0.91 against real field data and confirms our x^0.50 is the outlier. Our error, matched
at 200 m: **+53 % at 50 m, -34 % at 800 m** -- smaller than the +84 %/-44 % we had inferred from the
table alone.

**What it does NOT validate:** our absolute magnitude. This is a test of the *shape* of plume growth.
Magnitude still rests on the power-station calibration.

**Two bugs it caught in our own code first:** sampler azimuths wrap through 360/0 deg (a naive mean gave
sigma_y = 60 m at a 50 m arc -- impossible), and arcs where the plume exceeds the sampled span must be
rejected or they silently understate sigma_y and flatter our x^0.5.

⚠ **A second, subtler caveat:** the Pasquill-Gifford curves were themselves derived partly from
experiments of this era, so agreement is partly expected. It still tests our *implementation*, which is
the point.

## 14.2 CEDVAL, University of Hamburg — for the building part 📘

Wind tunnel measurements built specifically to validate models like ours around obstacles.

| | |
|---|---|
| What | flow and concentration measurements around **an isolated rectangular building** and **arrays of buildings** |
| Scale | 1:200 and 1:225 models in the BLASIUS and WOTAN wind tunnels |
| Why it fits us | it is *exactly* our geometry — a box on the ground with a plume near it |
| Access | free, but the files are password-protected: **email ewtl.mi@uni-hamburg.de for the password.** Some sets require signing a data-policy agreement |
| Where | [University of Hamburg, EWTL data sets](https://www.mi.uni-hamburg.de/en/arbeitsgruppen/windkanallabor/data-sets.html) |

**The test:** this is the right dataset to settle the **building-as-heat-sink defect** in Part 9. It
measures what a plume actually does when it meets a building. **Send that email today** — the wait for
a reply is the long pole, and it costs nothing.

## 14.3 Also available, less directly relevant 📘

From [ADMLC's dataset list](https://admlc.com/datasets/): **Michelstadt** (wind tunnel, simplified
urban), **MUST** (field, mock urban), **Joint Urban 2003** (field, Oklahoma City), **CODASC** (street
canyons). All involve buildings; all are more complex than we need. The **Model Validation Kit** is the
standard packaging for several.

---

# Part 15 — What still needs testing on FortyGuard's own data

| # | Test | What it settles | Status |
|---|---|---|---|
| **1** | **Forecast sharpening** — same target hour forecast at five leads, then the outcome | Whether waiting buys information. **The agentic claim depends entirely on this** | 🔄 running |
| **2** | **Bound coverage** — does a 90 % bound calibrated on earlier days actually cover on a new day? | Whether the central product claim is true out of sample | 🔄 running, first signal Aug 14 |
| **3** | **Double-counting check** — does the field already contain a wind-blown warm patch? | **✅ DONE — see Part 3.1.** One fixed pattern explains 99.9971 % of the spatial variation over 2 km, and the cause is area rather than resolution (6 crossed calls). **Our plume is additive, not double-counted** | ✅ **answered** |
| **4** | **Stability-class inputs** — can we compute the Pasquill class per hour from what the API returns? | Whether `D` can be derived live rather than fixed. Solar irradiance is verified working; wind speed is **not exposed anywhere in the API** (36 response fields checked, none is wind), so it needs an external station feed | 🟡 **half-blocked** |
| **5** | Peak-hour uncertainty over ~20 days | One of the two numbers the stopping rule depends on; currently rests on 5 days | ❗ partial |

**Test 3 was the one that mattered most and it is now done.** It was the only test checking whether our
physics **double-counts** something FortyGuard already models — a correctness question about the chain
rather than about a constant. The answer clears the architecture.

**Test 4 is now the blocked one, and it is why we filed a feature request.** Deriving `D` live needs
wind speed, and wind appears in **none of the 36 fields** any FortyGuard response returns. We had to
source it from a third-party station archive, which throws away the spatial advantage that made
FortyGuard the right choice in the first place. That request is
[fortyguard-api-findings.md](fortyguard-api-findings.md) §6.

---

# Part 16 — Glossary

| Term | Plain meaning |
|---|---|
| **Advection** | Being carried along by the wind |
| **Diffusion** | Spreading out and mixing with surrounding air |
| **Diffusivity (`D`)** | How fast that spreading happens. Bigger = wider, weaker plume |
| **Plume** | The stream of hot air leaving the condensers |
| **Recirculation** | A machine breathing its own exhaust |
| **Condenser / ACC** | The fan-and-coil array that dumps heat outdoors. A car radiator, much bigger |
| **σ_y (sigma-y)** | How wide the plume has spread sideways, in metres |
| **Stability class (A–F)** | A letter describing how turbulent the air is, set by wind and sunshine |
| **Downwash** | Wind bending a rising plume back down toward the ground |
| **Vortex** | A swirl of air, like the curl behind a moving lorry |
| **Steady state** | When nothing changes any more, however long you wait |
| **Péclet number** | How much wind dominates over mixing. Ours is 1500, i.e. wind dominates |
| **Verification** | Is the code solving its equations right? (no measurements needed) |
| **Validation** | Are those equations right for reality? (measurements needed) |
| **Conformal prediction** | A safety margin sized from your own past mistakes |
| **Residual** | Predicted minus actual. One past mistake |
| **Held-out** | Data deliberately not used for fitting, kept to score honestly |
| **Optimal stopping** | Deciding *when* to act when waiting brings better information but less time |
| **Backward induction** | Solving a decision problem by working from the end backwards |
| **CFD** | Computational Fluid Dynamics — a computer simulation. **A simulation, not a measurement** |

---

# Part 17 — Sources

**Opened and quoted directly during this work** 📘

1. **ASHRAE Handbook — HVAC Applications 2019, Chapter 46, "Building Air Intake and Exhaust Design."**
   Held locally as `i-p_a19_ch46.pdf`, 14 pages. **The industry-standard treatment of our exact
   problem.** Quoted from pages 46.7–46.10. Source of: the dilution equations (18) and (22), the
   turbulence-intensity ratios of Equation (21) giving σ_z/σ_y = 0.667, the recommended critical wind
   speed U_H,crit = 400 fpm = 2.03 m/s, the explicit statement that neglecting buoyant plume rise gives
   *"an inherent safety factor"*, and the recommendation of wind tunnel modelling for complex building
   environments. See Parts 7.1 and 7.2. Builds on flow-recirculation work by **Wilson (1979)** and
   dispersion parameters from **Cimorelli et al. (2005)** (AERMOD), both cited there but not opened
   by us.
2. **Maulbetsch, J.S. & DiFilippo, M.N.**, *Effect of Wind on the Performance of Air-Cooled
   Condensers*, California Energy Commission **CEC-500-2013-065** (2010), and Appendix B
   **CEC-500-2013-065-APB** (2008). Held locally in `validation-data/`. Quoted from pages 63 and 69.
   Six instrumented power-station condensers; ~40,000 digitised (wind, recirculation) pairs.
   Recirculation defined there as *"the difference between the average inlet temperature of all cells
   minus the minimum cell inlet temperature"* (p. 69).
2. **Pasquill-Gifford dispersion coefficients**, Table 3 —
   [hazopmalaysia PDF](https://hazopmalaysia.wordpress.com/wp-content/uploads/2009/07/3-3_dispersion2pasquill-gifford.pdf).
   Class A and D cross-checked independently.
3. **FortyGuard**, [Our Technology](https://www.fortyguard.com/our-technology) and
   [Introducing 12-Hour Forecasting](https://www.fortyguard.com/post/introducing-12-hour-forecasting-local-temperature-intelligence-for-real-world-operations).
   Source of the 12-hour horizon, hourly resolution, and the ML-downscaling description. **Refresh
   cadence is absent from both.**
4. **University of Hamburg EWTL / CEDVAL** —
   [data sets](https://www.mi.uni-hamburg.de/en/arbeitsgruppen/windkanallabor/data-sets.html).
5. **ADMLC** — [validation dataset list](https://admlc.com/datasets/).
6. **Harmo** — [classic tracer datasets](https://www.harmo.org/classic.php), including Prairie Grass.

**Named as standard references, primary text NOT opened** 📗


8. **Briggs** dispersion parameterisation, functional form σ_y = a x (1 + b x)^(−1/2). Form confirmed
   via search; **coefficient values not obtained.**
9. **Vovk, Gammerman & Shafer**, *Algorithmic Learning in a Random World* (2005);
   **Angelopoulos & Bates**, *A Gentle Introduction to Conformal Prediction* (2021).
10. **Bellman** and the standard optimal-stopping / dynamic-programming literature.
11. **Crowl & Louvar**, *Chemical Process Safety* — usual attribution for the Pasquill-Gifford table in
    source 2. **Inferred, not confirmed.**
12. **EPA ISC3 model user's guide**, EPA-454/B-95-003b —
    [PDF](https://gaftp.epa.gov/aqmg/SCRAM/models/other/isc3/isc3v2.pdf). Authoritative source for the
    urban/rural coefficient sets we have **not** yet used.

---

**Last honest word.** The equation is standard and our implementation of it is exact. The dispersion
constant now comes from a published table. One constant is fitted to real measurements on held-out
plants. And there are seven named gaps, of which the missing vertical dimension and the plume-versus-vortex
mismatch are the two that a specialist would go for first. Saying all of that plainly is a stronger
position than any amount of polish.
