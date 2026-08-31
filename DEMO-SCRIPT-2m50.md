# AGENTIC-ARBITER, demo voiceover script

**Speech time 2:52.** Plus the site's own intro audio, about 5 seconds, for 2:57 total.
Read at a steady pitch pace, about 150 words a minute. Leave a clear breath, about 0.7 seconds, at
every `***` seam. Those are the section boundaries.

Every figure is read from a file in this repository; the sources are listed at the end. The **on
screen** line under each section is what the recording shows while you say it, so the picture never
contradicts the voice.

Measured, not estimated: 430 spoken words, 2:52 at 150 words a minute.

---

## 1. THE PROBLEM (0:25, 62 words)

> Every data centre throws away cold air.
>
> On a cool night the outside air is already colder than a server hall needs. The plant could switch
> the chillers off and let the outside do the work, free. Almost none do. The engineer who owns
> that call cannot prove the hall stays in contract. So they pay for cooling nobody needs, all year.

**On screen:** landing page, still. Slow drift over the globe. No cursor movement.

***

## 2. THE SITE INTRODUCES ITSELF (site's own audio, you say nothing)

Cursor moves to **Initialise Arbiter** and clicks. The page plays its own voiceover and runs its
launch sequence. Leave this gap silent in your recording.

*(Exact length measured during capture and inserted here. The audio bed is about 5 seconds.)*

***

## 3. SCALE, AND WHAT IT IS WORTH (0:21, 53 words)

> This is Agentic Arbiter. Not a slide.
>
> Two hundred and thirty-eight real data centres, from six hundred and thirty-seven we mapped.
> Each with its own roof, weather station and tariff. Ninety-seven stations. Four million hours of
> recorded weather.
>
> The cold we can hand back is worth forty-two to eighty-five million dollars a year.

**On screen:** pick screen. Pointer rests on **238**, then **$42.4M to $84.8M**, then **+92,988**.
Each number under the pointer as you say it.

***

## 4. ONE SITE, ITS OWN SETTINGS (0:09, 22 words)

> Take one. Ashburn, Virginia. Two Amazon halls, sixty metres apart.
>
> Every control on this bar belongs to this building. Nothing is borrowed.

**On screen:** selected-site card, then the pointer walks the configuration bar: plant limit, humidity
limit, switch budget.

***

## 5. THE AGENT DECIDES (0:19, 47 words)

> Watch it work.
>
> It takes the forecast, adds a margin measured from its own past mistakes, and tests the worst case
> against the plant's limit. Not the forecast. The worst case. That is why an operator can sign it off.
>
> Twenty-four hours, every decision with its reason.

**On screen:** click **Run the agent**. Reasoning tape scrolls. Pointer follows two lines, then rests
on one hour's stated reason.

***

## 6. THE EVIDENCE, ON PAPER (0:15, 37 words)

> And it writes its own report.
>
> Nine pages, built from this site's files, typed by nobody. The real buildings from the air. The
> bound against the limit, hour by hour. Every number traceable to its own file.

**On screen:** click **Download the report**. PDF opens and scrolls: page 1 tiles, page 2 satellite
frame, page 3 bound chart, page 7 money table.

***

## 7. LIVE, AND WHEN IT PAYS (0:18, 46 words)

> That was a saved day. It also runs live, on a fresh forecast, with its own report.
>
> Timing matters. Everything runs on the site's own local clock, so a night run in Virginia finds cold
> air. At midday it keeps the chillers on, and says why.

**On screen:** pointer to **Run the agent on live data**, hover. Then the live report button. Then a
beat on an hour where the bound sits above the limit.

***

## 8. THE ENGINEERING UNDER IT (0:22, 56 words)

> Behind those buttons, the part nobody sees.
>
> Hot air from one hall drifts at the other. We solve it on the real rooftops. Five hundred and
> seventy-six solves, seventy-two wind directions, on a GPU, five seconds.
>
> Then five years of weather. Nine hundred and thirteen days it never saw. Thirteen thousand free hours
> taken. Seven unsafe.

**On screen:** results tabs. Open the plume tab, rest on the polar plot, then the runtime bars, then
the breach figure.

***

## 9. WHAT WE WILL NOT HIDE (0:22, 56 words)

> Now the number we could have buried.
>
> Against the live feed we scored sixty-five per cent, not ninety. That is days, not method.
>
> The score needs nine forecasts matched to what happened. The feed came in pieces, so we have four,
> and four caps you at eighty.
>
> On five years of history, the method holds ninety.

**On screen:** back to the pick screen. Pointer to the **Bound coverage, measured 65.6%** card, click
its **i** button, explanation open as you give the reason.

***

## 10. THE CLOSE (0:20, 51 words)

> So, the offer.
>
> Your forecast is already good enough to turn cold nights into money. Missing was the piece that lets
> a person act: a bound, a reason in plain words, a report that survives checking.
>
> The cold outside was always free. We built the thing that dares to use it.

**On screen:** slow pull back to the full map, all dots visible, hold on the scale card, fade.

---

## Timing sheet

| # | section | runs | words |
|---|---|---|---|
| 1 | The problem | 0:25 | 62 |
| 2 | *(site's own audio)* | ~0:05 | 0 |
| 3 | Scale and worth | 0:21 | 53 |
| 4 | One site, own settings | 0:09 | 22 |
| 5 | The agent decides | 0:19 | 47 |
| 6 | Evidence on paper | 0:15 | 37 |
| 7 | Live, and when it pays | 0:18 | 46 |
| 8 | The engineering | 0:22 | 56 |
| 9 | What we will not hide | 0:22 | 56 |
| 10 | The close | 0:20 | 51 |
| | **speech** | **2:52** | **430** |
| | **with the site's audio** | **2:57** | |

Absolute start times are deliberately absent past section 2: they depend on the measured length of the
site's own audio, and the alignment reads your real word timings anyway. If you read faster than 150
words a minute the video simply gets shorter, because the visuals are cut to your voice, not to this
table.

---

## Every figure, and the file it came from

Every row below was read back out of the artefact on 2026-08-31, not carried over from memory. Two of
my first citations were wrong and are corrected here: 65.6% is not in `bound_day_level`, and the
free-hour counts are in `rolling.json`, not `backtest.json`.

| said | value | source, exact path |
|---|---|---|
| sites covered | 238 | `demo/sites.json`, count of `offerable`; `portfolio.json` 250 built less 12 withheld |
| mapped candidates | 637 | `demo/unified_sites.json`, entry count |
| worth per year | $42.4M to $84.8M | `demo/portfolio.json`, `usd_mid_lo` / `usd_mid_hi` |
| chiller-hours | 92,988 | `demo/portfolio.json`, `gain_h_per_year` |
| weather stations | 97 | `demo/portfolio.json`, `stations` |
| hours of weather | 4,188,290 | `demo/portfolio.json`, `weather_hours_distinct` |
| two Amazon halls | AWS IAD116 / IAD117 | `demo/trace.json`, `site.operator` |
| sixty metres apart | 60.3 m | `demo/trace.json`, `site.facade_gap_m` |
| plume solves | 576 | `demo/trace.json`, `cycle.rise_tables.longest.n_solves` |
| wind directions | 72 | same, `bearings` length; 8 speeds, 0 refused |
| on a GPU, five seconds | 5.34 s, GPU (NVIDIA Warp) | same, `solve_seconds` and `device` |
| five years of weather | 43,763 h over 1,826 d | `demo/backtest.json`, `hours` / `days` |
| days it never saw | 913 | `demo/backtest.json`, `sensitivity.held_out_days` |
| thirteen thousand free hours | 13,435 | `demo/rolling.json`, `configs[0].executed_free_h` |
| seven unsafe | 7, or 0.52 per 1,000 | same, `executed_breach_h`, `breach_per_1000_free_h` |
| sixty-five per cent | 65.6% | `demo/trace.json`, `cycle.pooled_coverage` |
| four forecasts | n = 4 | `demo/trace.json`, `cycle.bound_day_level.n` |
| four caps you at eighty | 80% | same, `attainable`, which is n/(n+1) |
| nine forecasts needed | 9 | same, `n_needed_for_nominal` |
| the method holds ninety | 90.0% over 43,260 rounds | `demo/backtest.json`, `aci.3.ACI.realised_coverage` = 0.89977 |

## Two wordings I changed, and why

**"Ninety per cent every time once we have nine days" is not sayable.** The coverage card's own code
says: *"before 90 % is reachable at all", NOT "and then it hits 90 %". Reaching n = 9 is necessary and
not sufficient.* Nine forecasts make ninety arithmetically possible; they do not deliver it. Section 9
claims the ninety where it is actually measured, on the five-year record, and treats nine days as what
makes the live figure reachable. That is the stronger claim as well as the true one, and it survives a
question from an engineer in the room.

**"Night" means night at the building.** Confirmed in `live.py`: the hour labels and the forecast
window are both the site's own local time, `America/New_York` for Ashburn, hours stamped `-04:00`. Not
UTC, and not a vendor zone. Section 7 says "the site's own local clock" for that reason.

## Delivery notes

* Section 1 is slow and flat. No selling. You are describing something wasteful and ordinary.
* The first four words of section 3 are the turn. Lift there, not before.
* In section 5, "Not the forecast. The worst case." wants a real pause between the two. That contrast
  is the product.
* Section 9 is the most important twenty seconds in the video. Say it evenly and without apology. A
  team that volunteers its weakest number is a team you believe about the rest.
* The last line lands better a little slower and a little quieter than the line before it.
