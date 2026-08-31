# AGENTIC-ARBITER, demo voiceover script

**Speech 2:51, plus the measured 7.8 s intro, for 2:59. Inside the 3:00 limit.**

Read it the way you would explain it to one person across a table. Complete sentences, ordinary pace,
about 150 words a minute. Take a real breath at every `***` seam.

The judges have never seen this project. By the end they should be able to say what problem it solves,
how it decides, and why the numbers are believable. The explanations are load-bearing, so do not rush
them to buy time.

Every figure is read from a file in this repository. The sources, with exact paths, are at the end.

---

## 1. THE PROBLEM (0:29, 72 words)

> Data centres run chillers when the air outside is already cold enough.
>
> In Virginia that is almost every hour of December, and almost none of July.
>
> That is a timing problem, not carelessness. A chiller plant needs hours of warning to change how it
> cools, and its rooftop thermometer only knows about now. So they keep a buffer. Switching late
> can put a hall out of contract. Never switching only costs money.

**On screen:** landing page, still. Slow drift over the globe. No cursor movement.

***

## 2. THE SITE INTRODUCES ITSELF (its own audio, 7.8 s, you say nothing)

You click **Initialize Arbiter** (the button's own spelling). Stay silent for **eight seconds**, then
carry straight on into section 3. Do not try to hit it exactly: leave ten seconds if it is easier and
the extra silence gets trimmed in the edit, since silence can be cut invisibly.

MEASURED from the click, by hooking the page's own audio objects:

| t | what happens |
|---|---|
| 0.01 s | `voiceover.mp3` (4.68 s) and `intro-swell.mp3` (3.20 s) start together |
| 4.08 s | the swell ends |
| 5.53 s | the voiceover ends |
| 5.71 s | the splash overlay starts fading |
| 5.90 s | `transition-whoosh.mp3` (1.90 s) fires, the real transition |
| 6.85 s | the overlay is gone and the pick screen is exposed |
| **7.80 s** | the whoosh ends, and this is the gap the voiceover needs |

***

## 3. THE SCALE, AND WHAT IT IS WORTH (0:18, 46 words)

> This is Agentic Arbiter, and it runs on real buildings.
>
> Two hundred and thirty-eight data centres across America, each with its own roof outline, weather
> station and electricity price. It takes a tenth off their chiller running time, worth forty-two to
> eighty-five million dollars a year.

**On screen:** pick screen. Pointer rests on **238**, then on **$42.4M to $84.8M**, then on the
mechanical-cooling-cut card. Each number is under the pointer as you say it.

***

## 4. ONE BUILDING, AND ITS OWN SETTINGS (0:10, 26 words)

> Take one. Ashburn, Virginia, where two Amazon halls sit sixty metres apart.
>
> Every setting on this bar belongs to that building, and you can change it.

**On screen:** the selected-site card, then the pointer walks the configuration bar left to right:
plant limit, humidity limit, switch budget.

***

## 5. HOW IT DECIDES (0:21, 53 words)

> Watch what it does.
>
> It takes tomorrow's forecast and adds a margin measured from its own past mistakes. Then it
> compares that worst case, not the forecast, against the limits this plant must hold. Because it can
> see ahead, its buffer is half what a rooftop sensor needs, and that is the product.

**On screen:** click **Run the agent**. The reasoning tape scrolls; the pointer follows two lines as
they appear, then rests on the margin figure for one hour.

***

## 6. THE EVIDENCE IT WRITES ITSELF (0:08, 19 words)

> And it writes this itself.
>
> Nine pages from this building's own files, with every hour's decision and its reason.

**On screen:** click **Download the report**, the PDF opens and scrolls: page 1 tiles, page 2 satellite
frame, page 3 the bound against the limit, page 7 the money table.

***

## 7. LIVE, AND WHEN IT SAYS NO (0:15, 37 words)

> That was a saved day. It also runs live, with its own report.
>
> Everything uses the building's own local clock. When the worst case sits above the limit, it keeps
> the chillers on and tells you why.

**On screen:** pointer to **Run the agent on live data**, hover without clicking, then the live report
button, then a beat on an hour where the bound sits above the limit.

***

## 8. THE PART THAT TOOK LONGEST (0:26, 66 words)

> Now the engineering.
>
> The hot air one hall throws out drifts at its neighbour's intake, so it breathes exhaust warmer than
> the forecast. We work out where it really goes, for seventy-two wind directions. That is five
> hundred and seventy-six physics runs, done on the graphics card by NVIDIA Warp in five seconds.
>
> Over five years it made fewer unsafe calls than the controller it replaces.

**On screen:** the results tabs. Open the plume tab and rest on the polar plot, then move to the
runtime comparison, then to the agent-against-incumbent bars on the last sentence.

***

## 9. THE NUMBER WE COULD HAVE HIDDEN (0:23, 58 words)

> Now the number we could have hidden.
>
> On the live feed we scored sixty-five per cent, not ninety. That is a shortage of days, not a flaw:
> scoring it needs nine forecasts matched to what happened, and we have four. With four, eighty is the
> most the arithmetic allows.
>
> On five years of history, this method holds ninety.

**On screen:** back to the pick screen. Pointer to the **Bound coverage, measured 65.6%** card, then
click its **i** button so the explanation is open while you give the reason.

***

## 10. THE CLOSE (0:20, 50 words)

> So here is the offer.
>
> Your forecast is already good enough to turn cool air into money. What was missing is something an
> engineer can act on: a number with a limit, and a reason.
>
> The cold outside was always there. We built the thing that dares to use it.

**On screen:** slow pull back to the whole map with every dot visible, hold on the scale card, fade.

---

## Timing sheet

| # | section | runs | words |
|---|---|---|---|
| 1 | The problem | 0:29 | 72 |
| 2 | *(the site's own audio, measured)* | 0:07.8 | 0 |
| 3 | The scale, and what it is worth | 0:18 | 46 |
| 4 | One building, and its own settings | 0:10 | 26 |
| 5 | How it decides | 0:21 | 53 |
| 6 | The evidence it writes itself | 0:08 | 19 |
| 7 | Live, and when it says no | 0:15 | 37 |
| 8 | The part that took longest | 0:26 | 66 |
| 9 | The number we could have hidden | 0:23 | 58 |
| 10 | The close | 0:20 | 50 |
| | **speech** | **2:51** | **427** |
| | **total with the intro** | **2:59** | |

The intro gap is measured, not estimated: 7.80 s from the click to the transition whoosh ending, timed by hooking the page's own audio objects. Your 8 seconds was very nearly exact. And if you read faster than 150 words a minute the video simply gets shorter, because the visuals are cut to your recorded voice rather than to this table.

---

## What a judge with zero knowledge learns, and where

Each of these is said out loud, not left to the visuals.

| question | answered in |
|---|---|
| What is being wasted, and why does it persist? | 1, the December-versus-July fact and then the lead-time reason |
| How big is it, and what is it worth? | 3 |
| How does the agent actually decide? | 5, forecast plus a measured margin, worst case against the limits |
| Why is it better than what plants run today? | 5 and 8, half the safety buffer, and safer across five years |
| Does it ever say no? | 7 |
| Why should I believe any of it? | 6, 8 and 9, its own report, a five-year score, a volunteered weakness |

---

## Every figure, and the exact path it came from

Each row was read back out of the artefact on 2026-08-31.

| said | value | source, exact path |
|---|---|---|
| almost every hour of December | 23.99 h/day, 99.97% of hours | `data/weather/kiad_hourly_2021_2025.json`, dry-bulb <= 24 °C and dew point <= 15 °C, the base-case limits |
| almost none of July | 1.04 h/day, 4.34% of hours | same file, same gates |
| 238 data centres | 238 | `demo/sites.json`, count of `offerable`; 250 built less 12 withheld |
| a tenth off chiller running time | 9.7% portfolio, 10.7% at Ashburn | `demo/portfolio.json` `cut_pct`; Ashburn 9,510 h to 8,496 h |
| forty-two to eighty-five million | $42.4M to $84.8M | `demo/portfolio.json`, `usd_mid_lo` / `usd_mid_hi` |
| two Amazon halls | AWS IAD116 / IAD117 | `demo/trace.json`, `site.operator` |
| sixty metres apart | 60.3 m | `demo/trace.json`, `site.facade_gap_m` |
| buffer half what a sensor needs | 1.27 °C against 2.63 °C | `demo/backtest.json` shipped rung, `agent_margin_mean_c` / `incumbent_margin_mean_c` |
| seventy-two wind directions | 72 | `demo/trace.json`, `cycle.rise_tables.longest.bearings` length |
| 576 physics runs | 576 | same, `n_solves` |
| five seconds, NVIDIA Warp | 5.34 s, `GPU (NVIDIA Warp)` | same, `solve_seconds` and `device` |
| five years | 43,763 h over 1,826 days | `demo/backtest.json`, `hours` / `days` |
| fewer unsafe calls | 15 against 28 | `demo/backtest.json` shipped rung, `agent_breach_h` / `incumbent_breach_h` |
| sixty-five per cent | 65.6% | `demo/trace.json`, `cycle.pooled_coverage` |
| we have four | n = 4 | `demo/trace.json`, `cycle.bound_day_level.n` |
| four caps it at eighty | 80% | same, `attainable`, which is n/(n+1) |
| nine forecasts | 9 | same, `n_needed_for_nominal` |
| this method holds ninety | 90.0% over 43,260 rounds | `demo/backtest.json`, `aci.3.ACI.realised_coverage` = 0.89977 |

⚠ **Never quote the 7 unsafe hours next to the incumbent's 28.** They come from different measurements:
7 is `rolling.json` `configs[0].executed_breach_h`, and `rolling.json` contains no incumbent at all. The
comparison above uses 15 against 28, both from the same rung of the same run, which is the only
apples-to-apples pair in the artefacts. The page itself says these are "two different measurements,
reported separately rather than blended into one flattering figure".

---

## Four things I changed from the brief, and why each one mattered

**"Almost none do" is gone, because it is false and it contradicts our own source.** Nothing in this
repository measures how many real plants free-cool. Our own baseline free-cools **13.55 hours a day,
56.5% of every hour in the five-year record**, and `agent.py:91` calls it "a tuned adversary, not a
strawman", with `KpiCards.tsx:62` adding "the incumbent is not a straw man. It is the on site sensor
control that plants verifiably run." The one field study the project holds, LBNL Shehabi, calls free
cooling "this common cooling technique". Saying operators ignore free air, to a data centre audience,
would have spent the project's rarest asset in the first fifteen seconds.

**It also makes our own headline sound small.** Against "almost none do", 406 chiller-hours a year is a
rounding error. Against "your controller already takes 13.5 hours a day and still leaves 1.1 on the
table", the same figure is a real and defensible trim. The framing decides whether the number lands.

**The night framing is gone, and it was costing you about half the market.** Measured from
`data/weather/kiad_hourly_2021_2025.json` at the base-case limits: the winter-to-summer swing is
**6.9x**, the swing across the 24 hours of the clock is only **1.27x**, and **47.0% of all qualifying
hours fall in daylight**. Free cooling here is a cold-season resource available round the clock, not a
night shift. December and July say that in one breath, so section 1 uses them.

**"Ninety per cent every time once we have nine days" is not sayable.** `KpiCards.tsx` warns against
that exact sentence: nine calibration days make ninety per cent *reachable*, they do not deliver it.
Section 9 claims the ninety where it is genuinely measured, on the five-year record, and treats nine
days as what makes the live figure reachable.

Two smaller ones, for the same reason. **"Every data centre"** became "Data centres", because twelve
built-and-measured sites were withheld for having nothing to win, and `README.md:413` says "on a large
share of settings the honest answer is that there is no free cooling to win." And section 5 says
**"the limits this plant must hold"** rather than the temperature, because the real test is three gates,
temperature, humidity and contamination, and the humidity gate alone binds 2,700 hours of the record.

---

## Delivery notes

* Section 1 is explanation, not selling. Slow and level. December and July want a small pause between
  them, because that contrast is doing the work of a whole paragraph.
* The turn is "This is Agentic Arbiter". Lift there, not before.
* In section 5, pause slightly around "not the forecast". That contrast is the entire idea, and it is
  the one sentence a judge has to catch.
* Section 8 is allowed to sound like you enjoyed building it, because you did.
* Section 9 is the most important twenty-three seconds in the video. Even, unhurried, no apology. A
  team that volunteers its weakest number is a team you believe about everything else.
* The last line is slower and quieter than the one before it.
