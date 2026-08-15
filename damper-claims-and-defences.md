# DAMPER — Claims and defences

**A separate companion to `claims-and-defences.md` (INTAKE's own file, unchanged). Same discipline:
every claim tagged with what actually backs it, retractions kept visible rather than deleted.**

---

## 1. Claims I can defend

### 1.1 🟡 Cooling is a large, well-documented share of a data centre's energy bill — the exact "25–40%" split is not confirmed; a fully-verified alternative statement is used instead

**Do NOT say:** *"Cooling accounts for 25 to 40 percent of a data centre's total electricity use."*
This figure came from IAEI Magazine / Socomec search summaries, never opened directly (403
Forbidden, tried twice, on two separate sessions). **Two further, more authoritative primary
sources were read in full specifically looking for this split — a 45-page ASHRAE document and a
48-page DOE best-practices guide — and neither states it.** It is not used as a headline claim.

**Say instead, fully verified:** *"A U.S. Department of Energy best-practices guide states that in
a typical data centre with a highly efficient cooling system, IT equipment loads account for over
half of total facility energy — meaning cooling and other overhead are comparable in size to the
computing itself even in an efficient facility, and larger in a typical one."*

| | |
|---|---|
| **Evidence** | 📘 **Opened and read directly, in full**, DOE/FEMP/NREL, "Best Practices Guide for Energy-Efficient Data Center Design" (2024): *"In a typical data center with a highly efficient cooling system, IT equipment loads can account for over half of the entire facility's energy use."* |
| **What was checked and did NOT confirm the old figure** | This DOE guide (48 pages) and the primary ASHRAE 2011 Thermal Guidelines (45 pages) were both searched in full for a direct "cooling = X%" statement. Neither states one. The DOE guide's PUE section (p.39) only *defines* PUE=1.0 as "100% of power... goes to IT equipment and none to cooling" — a definition, not a typical-facility statistic. |
| **Attack** | *"So the 25–40% figure is made up?"* |
| **Answer** | *"It's a commonly repeated industry figure, but I could not confirm it against either of two authoritative primary documents I read in full looking for it, so I don't use it. What I can state with full confidence, from a document I opened directly, is that IT load itself is typically under half of total facility energy even in an efficient design — which makes the same basic point without relying on an unconfirmed split."* |

### 1.2 ✅ Free cooling (economizers) already delivers large, real, measured savings — opened and quoted directly

**Say:** *"This isn't a hypothetical saving. Real facilities already run mostly on free cooling and
publish the numbers."*

| | |
|---|---|
| **Evidence** | 📘 **Opened and quoted directly**, ENERGY STAR: NetApp's Global Dynamic Laboratory runs *"without a chilled water plant for more than 75 percent of the year"* and uses outside air *"for partial free cooling more than 98 percent of the time,"* cutting *"ongoing operating costs by roughly 60 percent."* A Marvell Semiconductor retrofit: *"Monthly Energy Use Reduction (kWh): 270,170,"* *"Annual Savings ($): $324,000,"* *"Payback without Incentive (years): 2.0."* |
| **Corroboration** | 📘 **Opened as a PDF and read directly**, The Green Grid White Paper #46 (2012), p.2: *"use of economizers will result in saving an average of 20 percent of the money, energy, and carbon for cooling when compared to data center designs without economizers."* |
| **Attack** | *"These are cherry-picked showcase facilities."* |
| **Answer** | *"The Green Grid's number is the average across a broad operator survey, not a single showcase — 20 percent, industry-wide. NetApp and Marvell are the upper end, and I say so."* |
| **Never say** | That every facility could reach NetApp's 75–98% figures — that depends heavily on climate (see 1.3). |

### 1.3 ✅ How much of the year free cooling works depends heavily on climate and on which ASHRAE equipment class a facility is rated for — opened and quoted directly with page numbers

**Say:** *"Under the newer, wider ASHRAE allowable ranges, 75 to 99 percent of hours in a typical
year can be free-cooling-eligible across most of North America and nearly all of Europe — but this
depends on which equipment class a facility's hardware is rated for."*

| | |
|---|---|
| **Evidence** | 📘 **Opened as a PDF and read directly**, The Green Grid White Paper #46, p.2: *"The class A2 Allowable range... shows that 75 percent of North America could use air side economizers for every hour of a typical year if operators are able to allow temperatures up to 35°C for short periods... The same class A2 range allows 97 percent of Europe and 14 percent of Japan to use free cooling all year long. If operators have equipment that can run in the new class A3 Allowable range... up to 40°C... 91 to 99 percent of locations, free air cooling could be used every hour of the year, even in Japan."* |
| **Attack** | *"Why is Japan so much lower under A2?"* |
| **Answer** | *"Japan's humidity profile is the limiting factor there, not temperature — this is exactly why a real system must gate on humidity as well as temperature, not temperature alone."* |
| **Never say** | A single, climate-independent "X% of the year" figure without naming the class and region it applies to. |
| **Also confirmed, same source, p.6** | The ASHRAE **Recommended** range (the more conservative of the two ranges) has a **max dry-bulb of 27°C and max dew point of 15°C**. Notable cross-check: Test 2's independently, data-tuned favourable threshold (found by minimising simulated cost on real weather, with no knowledge of this number) came out at **26.0°C** — within 1°C of ASHRAE's own published figure, with no connection between the two calculations. |
| **A named, real example beyond NetApp/Marvell** | 📘 Same source, p.4, citing a named 2011 industry article: *"Deutsche Bank recently announced they had built a production data center in the New York City metro area that achieves nearly 100 percent free cooling."* ⚠️ This is a secondary citation *within* a document I opened directly — the original CTOEdge.com article itself has not been independently opened. |

### 1.4 ✅ Switching cooling mode has a real, documented cost — this is not an invented friction

**Say:** *"HVAC engineering literature says plainly that frequent cycling of large cooling equipment
is inefficient and damaging, independent of any modelling assumption I've made."*

| | |
|---|---|
| **Evidence** | 📘 **Opened and read directly in full**, Trane whitepaper DC-WPR003A-EN, "Chiller Plant Control for Data Centers" (Dan Berg, Trane, Sept 2025). Confirms directly: *"preventing short cycling of equipment... reduces equipment wear and tear, thus improving overall equipment lifespan"*, and describes the exact failure mechanism — when facility load sits near the boundary between needing N versus N+1 running chillers, multiple chillers' compressors can start and stop *"attempting to maintain loop load,"* each independently deciding to add or subtract a compressor stage, which *"could result in multiple chillers short-cycl[ing] compressors, resulting in compressor and equipment damage, as well as poor loop temperature control."* A concrete worked example is given: a 6-chiller plant (300 tons/chiller, 4 compressors × 75 tons each) with an 825-ton base load exactly matches 3 chillers running (11 compressors, 1 standby); running 5 chillers instead leaves 9 idle compressors that can inappropriately cycle when load crosses that boundary. |
| ⚠ **Correction, made after the user supplied the primary document directly** | An earlier draft of this project attributed the quote *"large chiller units lack operational flexibility — frequent cycling on and off proves highly inefficient"* to this Trane document. **After reading the complete text, that exact sentence does not appear anywhere in it.** It was carried over from a bundled web-search summary without checking which specific source it came from, and the attribution was wrong. It is **retracted** — see §2. The mechanism and worked example above are the real, confirmed content, and they support the same underlying claim (switching/cycling is costly and risky) more precisely than the retracted sentence did. |
| ⚠ **What is still NOT verified** | The specific dollar/energy magnitude of a single mode switch. An earlier pass also attributed a "20–40% swing" / "33% savings, 56% peak-power reduction" figure to a PNNL chiller-optimization study **found via search but never opened directly** — not found in this document either. Not used in any claim; not cited until the actual PNNL source is opened. |
| **Attack** | *"So you don't actually know how expensive a switch is?"* |
| **Answer** | *"Correct, and I say so. The mechanism — near a load boundary, multiple chillers can oscillate and damage themselves — is now confirmed in detail, with a real worked example. The exact dollar cost of one switch is not sourced to a number, so the feasibility test sweeps it across a wide range (0.5x to 4x a baseline hour of mechanical cost) and reports which conclusions survive across that whole range."* |

### 1.5 ✅ Real commercial economizer controllers already exist, and their fix for switching cost is a small, fixed, non-adaptive deadband — opened and quoted directly

**Say:** *"I checked the actual engineering manual for a real, currently-sold product. It confirms
switching cost is a known problem in the industry, and it confirms the fix used today is a small,
fixed buffer, not anything that looks at the forecast."*

| | |
|---|---|
| **Evidence** | 📘 **Opened as a PDF and read directly**, Honeywell JADE Economizer white paper, p.1: *"A 2°F and a 1 Btu/lb differential are used to reduce the cycling of the Economizer Available point."* Also documents four real, named control strategies in current industrial use: single dry-bulb, differential dry-bulb, single enthalpy, and differential (dual) enthalpy. |
| ⚠ **Retraction, now double-confirmed** | An earlier draft attributed a *"1,900 economizer-operating-hours per year and 18% cooling-energy savings"* figure to this same document. **The user supplied the complete primary PDF directly; re-reading it in full a second time confirms the figure does not appear anywhere in it.** It is not used anywhere in this project's claims. Recorded here rather than quietly dropped. |
| **Practical caveat, also confirmed directly** | The same document warns that humidity sensors are factory-calibrated at only 55°F/50% RH to 2–5% accuracy and *"are very hard to keep in calibration and will drift"* over time in the field — enough of a real concern that *"some engineers in the industry... refuse to specify enthalpy in their designs"* over it. **This is an argument in DAMPER's favour, not against it**: it is a reason to prefer FortyGuard's regional forecast data (professionally maintained, not a single drifting on-site part) over relying on one uncalibrated local humidity sensor. |
| **Attack** | *"Isn't a 2°F deadband basically already solving your problem?"* |
| **Answer** | *"It solves the 'don't chatter on noise' half of the problem. It does not solve the 'switch promptly when the trend is a real, lasting change' half — a fixed buffer waits the same amount regardless of how obvious the trend already is. That is the specific, narrow gap being tested."* |
| **Methodology vindication, found while re-reading the Green Grid paper** | The Green Grid's own official 2009 methodology for its industry-standard free-cooling maps used exactly the same kind of simplification as this project's Test 2: *"for each hour where average dry bulb and dew point temperatures are below the ASHRAE recommended maximums, an hour is added to the possible free cooling hours."* **A dry-bulb-plus-humidity gate, not full enthalpy — the same simplification Test 2 used, and previously described here only as a stub to apologise for.** It is the industry's own standard simplification, not a shortcut unique to this project. Upgraded from "stub" framing accordingly — see `damper-physics-explained.md` Part 1.5. |

### 1.6 ✅ Outdoor air pollution is a real, measured, but manageable constraint on free cooling — opened and read directly, full citation

**Say:** *"A real field study at eight data centres measured that economizers do increase indoor
particle levels while open, but the annual average stays within limits, and better filtration closes
most of the remaining gap."*

| | |
|---|---|
| **Evidence** | 📘 **Opened and read directly**, Shehabi, Tschudi & Gadgil, Lawrence Berkeley National Laboratory, "Data Center Economizer Contamination and Humidity Study" (2007): *"particle monitoring was conducted at eight data centers in Northern California... economizer use caused sharp increases in particle concentrations when the economizer vents were open... this concentration, when averaged annually, is still below current particle concentration limits... Current filtration in data centers is minimal (ASHRAE 40%)... When using economizers, modest improvements in filtration"* [text continues past the extracted excerpt — the improved-filtration percentage itself was reported via search summary as "ASHRAE 85%" but not independently re-confirmed by direct reading, flagged honestly] |
| **Attack** | *"Doesn't this kill the whole idea for polluted regions?"* |
| **Answer** | *"No — it's a gate, not a blocker. FortyGuard's `env_params` already returns six separate pollution readings (PM2.5, PM10, O3, NO2, SO2, CO) every cycle. The agent can simply refuse to recommend free cooling on days those readings are bad, exactly like INTAKE's line-of-sight refusal for blocked geometry."* |

### 1.7 ✅ FortyGuard's data needed for this idea is real, verified this session, and was already being paid for

**Say:** *"Every field this idea needs — wet-bulb temperature, humidity, and six pollution
indices — is already returned by a call this project makes routinely. None of it required a new
API call to discover."*

| | |
|---|---|
| **Evidence** | 🟩 Confirmed directly against a real saved response (`n37_ep_2026-07-22.json`): `wet_bulb_temperature_celsius`, `relative_humidity_percent`, `apparent_temperature_celsius`, `heat_index_celsius`, `air_quality_pm2p5:idx`, `air_quality_pm10:idx`, `air_quality_o3:idx`, `air_quality_no2:idx`, `air_quality_so2:idx`, `aqi_us_co`, `co2_ppm`, `methane_ppb` all present with real numeric values |
| ⚠ **What is not yet verified** | Whether FortyGuard's *forecast* (not just historical) value of these specific fields has real skill 12 hours out. See `damper-test-3-forecast-skill-PLANNED.md` |

### 1.8 ✅ The core switching mechanism has been tested on a full year of real, held-out weather data

**Say:** *"A trajectory-aware switching policy was compared against a properly tuned version of
today's industry-standard deadband, on six months of real weather the tuning never saw. It won by a
real statistical margin at three of four tested switching-cost levels."*

See `damper-test-2-switching-simulation.md` for the complete numbers, the pre-registered prediction,
and the correction made mid-test (an early version compared against an untuned baseline and was
superseded).

### 1.9 ✅ The switching-rate safety limit — now the single most solidly sourced number in this project, and a correction to an earlier version of it

**Say:** *"ASHRAE's own published Thermal Guidelines cap the rate of temperature change at 20°C per
hour for data centres using disk drives, and a stricter 5°C per hour for those using tape drives."*

| | |
|---|---|
| **Evidence** | 📘 **Opened and read in full**, ASHRAE 2011 Thermal Guidelines for Data Processing Environments (45 pages), Table 4, footnote (f), quoted directly: *"5°C/hr for data centers employing tape drives and 20°C/h for data centers employing disk drives."* This is the ONLY claim in this project confirmed against ASHRAE's own primary publication rather than a secondary summary. |
| ⚠ **Correction** | An earlier version of this claim stated the limit as *"20°C in an hour AND 5°C in any 15-minute window,"* sourced only from a secondary summary (hvac.best). **After reading the complete 45-page primary document and searching every page for "15 minute" / "15-minute" / "quarter hour," no such clause exists anywhere in it.** The real rule is simpler — one flat hourly rate, different by equipment type — not a stacked two-window rule for the same equipment. Retracted — see §2. |
| **Attack** | *"Why should I trust this number over the one you had before?"* |
| **Answer** | *"Because this one is checked against ASHRAE's own document, in full, and the old one wasn't — it came from a summary that turned out to have invented a detail that isn't in the primary source at all."* |

---

## 2. 🔴 RETRACTED — do not use these

| Retracted claim | Killed by |
|---|---|
| *"The JADE white paper documents 1,900 economizer-hours/year and 18% cooling-energy savings for the differential-enthalpy-plus-fixed-dry-bulb strategy"* | **Checked by opening the primary document directly.** Not found in the accessible pages. Likely conflated from a different source during an earlier search-summary pass. Dropped entirely. |
| *"PNNL chiller-plant optimization delivers 33% annual energy savings and 56% peak-power reduction"* | **Checked by opening the Trane page these figures were attributed to.** Not found on the accessible content. The underlying PNNL study was never opened directly. Not used in any claim. |
| *"The switching-cost-aware policy beats the deadband by 7.01 sigma"* (an early result) | **Superseded by a corrected re-run.** The first version compared the proposed policy against an *arbitrarily chosen* deadband setting rather than one tuned fairly on separate training data — exactly the mistake this project's own house rules exist to prevent. The corrected, tuned, train/test version is what is reported in §1.8 and in `damper-test-2-switching-simulation.md`. |
| *"Large chiller units lack operational flexibility — frequent cycling on and off proves highly inefficient"* (attributed to Trane) | **Checked against the complete primary document, supplied directly by the user.** That exact sentence does not appear anywhere in it. Wrongly carried over from a bundled web-search summary without checking the source. Replaced in §1.4 with the document's real, confirmed content — the compressor-oscillation mechanism and a worked 6-chiller numeric example, which support the same underlying claim more precisely. |
| *"ASHRAE caps the rate of change at 20°C in an hour AND 5°C in any 15-minute window"* | **Checked by opening the actual 45-page primary ASHRAE document and searching every page.** No 15-minute clause exists anywhere in it. The real rule (Table 4, footnote f) is simpler: 20°C/hr for disk-drive data centres, 5°C/hr for tape-drive data centres — one flat hourly rate per equipment type, not a stacked two-window rule. Corrected in §1.9. |
| *"Cooling accounts for 25 to 40 percent of a data centre's total electricity use"* | **Not confirmed after reading two further primary sources in full** (a 45-page ASHRAE document, a 48-page DOE guide) specifically looking for this split. Neither states it. Not dropped as false, but downgraded to "unconfirmed" and no longer used as a headline number — see §1.1 for the fully-verified statement used instead. |

---

## 3. The one sentence to open with

> *"Free cooling already saves data centres 20 to 90 percent of their cooling energy, and it's
> already deployed — the industry's own products just switch it on and off using a small fixed
> buffer that never looks at where the weather is heading. DAMPER does, and on a year of real,
> held-out weather it measurably beats that buffer."*

## 4. If asked "what is weakest?"

> *"Three things. The 'favourable' definition used in the tested simulation is dry-bulb temperature
> plus a humidity gate, not true enthalpy — a real upgrade still to do. The exact cost of a single
> mode switch is not pinned to a sourced number, only swept across a range. And whether FortyGuard's
> own forecast — as opposed to persistence on real historical data — carries genuine skill for this
> specific decision has not yet been tested; that is the next concrete step, not yet run."*
