# Session G — the money figure, and every source behind it

**Written 2026-08-20. Every document below was DOWNLOADED AND PARSED IN THIS REPOSITORY, not read
from a search snippet.** The commands that fetched and read them are reproduced under each entry so
that anyone can repeat the extraction and get the same characters.

Until this document existed, the project's standing position was: *"No dollar or kWh figure is
claimed anywhere; the °C→kWh conversion could not be sourced from a primary document."* That
position is now retired for the **chiller-compressor** term only, and the limits below say exactly
what is still not claimed.

---

## 1. THE UNIT OF THE ANSWER, AND WHY IT IS NOT "DOLLARS PER YEAR"

**Everything is expressed PER MEGAWATT OF IT LOAD.** The agent has never measured a data centre's
size, and inventing one would be a hard-coded constant of the worst kind — a number that multiplies
the headline. Per-MW-of-IT is the natural unit: a reader who knows their own IT load multiplies once.

**The quantity monetised is CHILLER-HOURS AVOIDED**, which the agent measures directly. It is
converted with two factors, and **both are swept, never chosen**:

```
$ saved per MW of IT load per year
    = (chiller-hours avoided per year)
    x (chiller electrical power per MW of IT load, kW)      <- section 3, SWEPT over 4 sourced values
    x (electricity price, $/kWh)                            <- section 2, SWEPT over 4 sourced values
```

---

## 2. ELECTRICITY PRICE — U.S. Energy Information Administration

### 2a. Annual, latest complete year

> **"2024 Total Electric Industry- Average Retail Price (cents/kWh)"**
> *(Data from forms EIA-861- schedules 4A-D, EIA-861S and EIA-861U)*
> `State Residential Commercial Industrial Transportation Total`
> `Illinois 15.87 11.81 8.83 7.76 12.21`
> `Virginia 14.41 8.72 8.99 9.25 10.62`

- **Source:** <https://www.eia.gov/electricity/sales_revenue_price/pdf/table_4.pdf>
- **How it was read:** downloaded with `urllib.request`, text extracted with `pypdf`, and the two
  state rows printed verbatim. The block above is that output, unedited.

### 2b. Monthly, most recent

> **"Table 5.6.A. Average Price of Electricity to Ultimate Customers by End-Use Sector, by State,
> May 2026 and 2025 (Cents per Kilowatthour)"**
>
> | | Commercial May 2026 | Industrial May 2026 |
> |---|---|---|
> | **Virginia** | **10.84** | **10.53** |
> | **Illinois** | **15.36** | **10.20** |

- **Source:** <https://www.eia.gov/electricity/monthly/xls/table_5_06_a.xlsx>
  (rendered at <https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=epmt_5_6_a>)
- **How it was read:** the `.xlsx` was downloaded and **parsed as a zip of XML with `zipfile` and
  `xml.etree`** — no spreadsheet library, no summarising model. Row `A == "Virginia"` gave
  `D = 10.84` (Commercial, May 2026) and `F = 10.53` (Industrial). The header rows confirming the
  column meanings were printed alongside.
- ⚠ **A WebFetch summary of the rendered page was ALSO obtained first, and it agreed.** It is not
  cited as the source, because a small model reading a page is exactly the snippet-trust the
  project's rule 7 forbids. The XLSX parse is the source; the agreement is only reassurance.

### 2c. What is SWEPT, and what is NOT claimed

**Swept:** Virginia commercial 8.72, Virginia industrial 8.99, Virginia commercial 10.84, Illinois
commercial 11.81 ¢/kWh — spanning **sector** and **vintage** for the two metros that ship.

🔴 **NOT CLAIMED: that any of these is the price the site actually pays.** These are EIA
*state-sector averages*. A hyperscale campus in Loudoun County buys on a large-general-service
tariff, and Dominion Energy has pursued a separate rate class for data centres. **The real number is
contractual and not public.** The sweep is a range of published averages, and it is labelled as one.

---

## 3. CHILLER ELECTRICAL POWER PER MW OF IT LOAD

### 3a. Tons of refrigeration to reject, per MW of IT load

One ton of refrigeration is **12,000 Btu/h exactly**, which is **3.516852842 kW**. So rejecting
1 MW of heat is `1000 / 3.516852842 = ` **284.345 tons**.

This is a **definition**, not a measurement, and it is the only unsourced-to-a-PDF step here —
deliberately, because a unit conversion has no primary document to open. It is written out in full in
`src/money.py` so it can be checked by hand.

### 3b. Chiller efficiency — PNNL / ASHRAE Standard 90.1-2019

> **PNNL-29674, *ANSI/ASHRAE/IES Standard 90.1-2019 Performance Rating Method Reference Manual*,
> page 221 (PDF page 236), "Chiller Rated Efficiency" and
> Table 82, "Minimum Efficiency Requirements for Water Chilling Packages"**
> *(Table 82 reproduces Standard 90.1-2019 Table G3.5.3.)*
>
> Test conditions for the full-load (FL) rating, quoted verbatim:
> - 44 °F leaving chilled-fluid temperature
> - 2.4 gpm/ton evaporator fluid flow
> - 85 °F entering condenser-fluid temperature
> - 3.0 gpm/ton condenser-fluid flow
>
> | Water cooled, electrically operated | Size | Minimum efficiency |
> |---|---|---|
> | Positive displacement (rotary screw and scroll) | < 150 tons | 0.790 kW/ton FL · 0.676 IPLV.IP |
> | | 150–300 tons | 0.718 FL · 0.629 IPLV |
> | | **> 300 tons** | **0.639 FL · 0.572 IPLV** |
> | Centrifugal | < 150 tons | 0.703 FL · 0.670 IPLV |
> | | 150–300 tons | 0.634 FL · 0.596 IPLV |
> | | **> 300 tons** | **0.576 FL · 0.549 IPLV** |
>
> `FL = Full Load; IPLV = Integrated Part Load Value`. Test procedure **ARI 550/590**.

- **Source:** <https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-29674.pdf>
- **How it was read:** downloaded, `pypdf` text extraction, **PDF page 236 printed in full** and read
  in place. The table above is transcribed from that printout, including the size-band boundaries.
- **Why a PNNL report and not the standard itself:** ASHRAE 90.1 is a paywalled document. PNNL-29674
  is a **free U.S. Department of Energy national-laboratory publication that reproduces the
  requirement tables**, which is openable and therefore citable under the project's rule 7. It is the
  standard's values at one remove, and that remove is stated.

### 3c. The four swept values

A data-centre plant at 1 MW of IT load needs 284 tons, so the **> 300 tons** band applies once the
site is above ~1.06 MW of IT — and both chiller types are in scope, because both are deployed.
(LBNL 2024, section 4, models nine cooling systems including both air- and water-cooled chillers.)

| swept value | kW/ton | kW per MW of IT load |
|---|---|---|
| centrifugal, IPLV | 0.549 | **156.1** |
| centrifugal, full load | 0.576 | **163.8** |
| screw/scroll, IPLV | 0.572 | **162.6** |
| screw/scroll, full load | 0.639 | **181.7** |

**Which way each end errs, stated rather than hidden:**
- **Full load OVERSTATES** the draw at the moment free cooling is available, because free cooling is
  available when it is *cool outside*, and a chiller at cool condenser temperatures runs well below
  its rated full-load kW/ton.
- **IPLV is not the right number either.** It is an *annual-weighted* part-load metric under
  AHRI 550/590's assumed load profile, not the part-load point that coincides with free-cooling
  weather. It is used as the lower end of the sweep because it is the lower published figure, not
  because it is the correct one.
- 🔴 **CODE MINIMUM IS THE OPTIMISTIC END FOR SAVINGS.** Standard 90.1 is a *floor*. Hyperscale
  operators specify chillers well above it, and a more efficient chiller draws less, so **a real site
  saves LESS money per chiller-hour than this table implies.** Whatever the sweep says, treat it as
  an upper end.

---

## 4. 🔴 WHAT THIS FIGURE IS NOT — read before quoting it

1. **IT IS THE CHILLER COMPRESSOR ONLY.** Switching to outside air switches off the *compressor*. It
   does **not** switch off the CRAH/AHU fans, the chilled-water pumps, the condenser-water pumps or
   the cooling-tower fans, and an airside economizer typically moves **more** air, so **fan power can
   go UP**. None of that is netted off here, because none of it is measured by this agent. **The
   figure is therefore an upper bound on the saving, and the unmeasured fan penalty has the opposite
   sign.**
2. **THE HEAT REJECTED IS APPROXIMATED BY THE IT LOAD.** UPS, PDU and lighting losses inside the
   cooled envelope also become heat, so the true load is somewhat above 1 MW per MW of IT; some
   overhead sits outside the cooled space, so scaling by the full PUE would overshoot. LBNL 2024
   measures **average PUE 1.4 in 2023**, projected to **1.15–1.35 by 2028**
   (<https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf>,
   page 47, read directly). That range is quoted **as context only** — it is not used as a multiplier,
   because attributing the right share of it to the chiller would require a breakdown the report
   does not give. **It states PUE; it never states chiller kW/ton or COP** — that was checked by
   grepping all 79 pages for `kW/ton`, `COP`, `IPLV` and `chiller efficien`, and the only hits were
   bibliographic.
3. **NO CARBON, NO WATER, NO MAINTENANCE, NO DEMAND CHARGES.** Cooling-tower water use moves in the
   opposite direction to chiller energy; demand charges depend on coincident peak, which the agent
   does not model.
4. **THE HOURS THEMSELVES CARRY THEIR OWN CAVEATS.** Every hours figure is conditional on the bank
   sitting on the long facade (the refusal guard is priced at **−3,124 h/yr** where it fires) and the
   unanchored case is **negative**. The money table inherits all of it, row for row.

---

## 5. THE HEADLINE, AND THE HONEST WAY TO SAY IT

`src/money.py` writes `demo/money.json`: **every ladder and sensitivity row × 4 prices × 4 chiller
efficiencies**, with no row collapsed. Nothing is averaged, because averaging over incomparable
plant settings is what §7.1's `_summarise` exists to avoid.

**Say it like this:** *"At the shipped configuration the agent avoids 405.7 chiller-hours per
megawatt of IT load per year. Priced with ASHRAE 90.1-2019's minimum chiller efficiency and EIA's
2024 Virginia commercial tariff, that is about $5,800 per MW of IT load per year — compressor energy
only, at a code-minimum chiller, on a state-average tariff, and every one of those three
qualifications makes the real number smaller."*

**Never say:** *"saves $X million"* — there is no site size in this project to multiply by.
