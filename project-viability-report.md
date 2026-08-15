# Downwind — Viability Report

**A critical commercial and technical review against the FortyGuard hackathon rubric.**
Written to be shown to a sceptical reader. Where the idea is weak, it says so.

| | |
|---|---|
| **Date** | 2026-08-09 |
| **Project** | *Downwind* — measuring thermal interference between neighbouring data centres using FortyGuard's 60 m air-temperature field |
| **Hackathon** | Aug 18–30, 2026 · FortyGuard primary, NVIDIA secondary |
| **Verdict** | **≈83 / 100.** A selling point, not a theoretical study — **conditional on three corrections**, one of which is a concession |

**Evidence tags:** **[M]** measured, response on disk · **[H]** historical, from the account's own usage
breakdown · **[L]** literature, cited · **[U]** unverified, with the settling test named · **[S]** stub.

---

## 1. Scorecard

| Criterion | Weight | Score | Reasoning |
|---|---|---|---|
| **Impact & relevance** | 40 % | **32** | Genuinely a real urban-heat problem: 2026 peer-reviewed field measurements, national press, an active scientific dispute, and a permitting crisis in the exact metro we have verified coverage for. **Loses marks because** the highest-value output is bought infrequently, and every dollar figure runs through unvalidated stub constants |
| **Technical execution** | 35 % | **29** | Every data dependency verified before a line of code: 100 % lattice stability, forecast↔historical symmetry, genuine 60 m resolution, real asset layer measured from OSM, unbreakable fixture-replay demo. **Loses marks because** the central risk (does FortyGuard see waste heat?) is unresolved until Aug 18, and airport wind is a proxy for facility wind |
| **Innovation** | 15 % | **13** | ~1000× scale-up of a published 2026 method; adjudicates a live dispute using the correct variable; the inter-facility interference angle is unclaimed |
| **Communication** | 10 % | **9** | Two strong assets: a visible warm plume trailing downwind, and the surface-vs-air distinction, which is memorable and is the crux of a real argument |
| | | **≈83** | |

**The single biggest threat to that score:** if a judge reads this as *a measurement study* rather than
*a product*, Impact collapses from ~32 to ~20 and the total falls to ~71. **§3, §4 and §5 exist to
prevent exactly that reading.**

---

## 2. The problem, and why it is unsolved

**Sailor et al., ASME J. Eng. Sustain. Bldgs. Cities 7(2):024501, 2026** [L] — the first field
measurements of data centre waste heat on neighbourhood air temperature:

```
Downwind air         1.3–1.6 °F (0.7–0.9 °C) above upwind, average
Peak                 4 °F (2.2 °C)
Detectable to        ⅓ mile (~500 m) from the perimeter
Condenser discharge  14–25 °F above ambient
Heat flux            thousands of W/m² — "far exceeding any previously studied urban source"
Method               multiple vehicles, simultaneous upwind/downwind transects,
                     18 Jun – 25 Oct 2025, four Phoenix facilities:
                     Mesa (36 MW) and Chandler (169 MW campus) named
Their stated gap     "wider temporal and weather conditions"
```

**And there is a live dispute.** A satellite study using MODIS **land-surface temperature** (500 m,
2004–2024) claims 2 °C average / 9 °C peak warming affecting 343 M people within 10 km [L]. Masley's
rebuttal [L]: that is **surface temperature, not air**; a 2 °C LST rise implies "a fraction of a degree
at most" of air temperature; waste heat explains only **1–3 %** of the signal — the rest is buildings
replacing grass.

**What he says would settle it** [L]:

| Requirement | Can this project do it? |
|---|---|
| (i) Control sites — data centres vs. other large construction | ✅ Yes — §5 |
| (ii) **Actual air-temperature measurements, not satellite surface readings** | ✅ **Yes — this is what FortyGuard is** |
| (iii) Separating construction timing from operational start-up | ✅ Yes — historical fields before/during/after commissioning |
| (iv) Isolating regional development | 🟡 Partially — control-site matching mitigates, does not eliminate |

**Three of his four requirements, including the hardest, are what FortyGuard uniquely enables.**

---

## 3. What is actually being sold

This section corrects an earlier framing error of mine.

**"Which neighbourhoods are being warmed" is dead as a product line.** It is *adversarial to the paying
customer*. No operator pays to be exposed. Keep it as an input; never as the offer.

**What sells is thermal due diligence** — an existing, budgeted, recurring category:

| Product | Bought when | Payer | Aligned with payer? |
|---|---|---|---|
| **Pre-acquisition thermal assessment of a parcel** — free-cooling hours today, and after the facilities already permitted upwind are built | Every site acquisition | Developer / site selector | ✅ They need it to underwrite the deal |
| **Permit-support impact measurement with a control group** | Every conditional-use application | Operator's permitting team | ✅ **They are currently being accused on contested satellite evidence and cannot answer** |
| **Portfolio thermal-exposure monitoring** — is my intake degrading as neighbours are built? | Subscription | Operations / asset management | ✅ |
| Neighbourhood exposure disclosure | Rarely | County | ⚠️ Small budgets; commissions one-off studies |

**The reframe that matters.** Operators are on the back foot — an industry piece is titled *"the heat
island effect operators are refusing to own"* [L]. They are being blamed on the basis of a study whose
physics is contested. **A defensible measurement with a control group is their defence, not their
exposure.** If the effect is small, measurement helps them.

**Risk to disclose on stage:** willingness to pay depends on the answer. If the measured effect turns out
large, an operator will not want it published. Say this before a judge does.

---

## 4. The economics — and where they are soft

| | Order of magnitude | Confidence |
|---|---|---|
| **Operational** — losing 1.2 °C of intake headroom removes the hours where ambient sits in that band near the threshold | **$8–24 k / yr per 10 MW**; $80–240 k / yr for 100 MW | Low — all stubs |
| **Siting** — a 200 MW facility placed where it gets ~300 fewer free-cooling hours per year, over a 30-year life | **$20–30 M per decision** | Low — all stubs |

**⚠ Both run entirely through `[S]` constants** — kW/ton, $/kWh, threshold, cooler approach. **This is a
modelled inference sitting on top of a measurement, and it is the seam a sharp judge will find.**

**Rule for every document and every slide:** lead with the **measurement** as the finding. Present money
as a **labelled sensitivity band with its stubs named**, never a point estimate. *"Depending on tariff and
plant efficiency, $X–$Y per year"* is defensible. *"$180,000"* is not.

**Untested and it gates the whole money half:** count the historical hours where ambient actually sits
**within the interference magnitude of the threshold** — the only band where a 1.2 °C penalty changes any
decision. **200 h/yr → the operational claim is real. 5 h/yr → it is worthless even with a perfect
measurement.** This is check **U-1** and it is pure computation.

---

## 5. Is it truly agentic? — a concession, and the fix

**The concession.** As originally described, the loop was:

```
fetch map → fetch wind → average two wedges → compare to threshold → report
```

with `if wind_variance < k`, `if sigma > k`, `top_k(...)`, `if d > bound`.

**That is a scheduled data pipeline with conditional branches. It is not an agent.** A judge would take it
apart, and the project's own bar requires genuine autonomy. Naming this myself is cheaper than being told.

### Where the genuine agency lives: budgeted experiment design

The **thermal interference matrix** is a grid of (facility pair × wind bearing) cells, mostly **empty**.
Four properties make filling it a real sequential decision problem:

1. **Today's weather determines which empty cells are fillable at all** — you cannot measure a west-wind
   plume on an east-wind day
2. Every measurement **costs credits from a finite pool**
3. **Earlier choices change later value** — once a bearing is well sampled, its marginal information drops
4. The agent must decide **when evidence is sufficient to declare a detection versus buy more**

So the question each cycle is not *"is the wind steady?"* but:

> **"Given what I already know, what I still do not know, and what I can afford — what is the single most
> informative measurement I can buy right now?"**

**That is an active-learning loop under a budget constraint, and it is genuinely agentic.**

### And the LLM gets a real job

`heat_intelligence` returns **unstructured causal attribution** across `urban / anthropogenic /
geographic / environmental / events` [M]. The agent must judge:

> *"Is this attribution consistent with a **waste-heat** explanation, or a **land-cover** explanation?"*

That is reasoning over text with no threshold answer, and it feeds back into detection confidence. **A
legitimate LLM role** — unlike "write a nice summary," which is decoration and is cut.

### Autonomy checklist

| Requirement | Where satisfied |
|---|---|
| Perceives state | The field, the wind, the facility register, its own logbook, its own matrix of what it already knows |
| **Chooses actions at runtime** | Which cell of the matrix to target · whether today's conditions permit any measurement · whether to buy resolution · **detection vs. non-detection against its own calibrated bound** · which facilities earn a paid attribution call · when to escalate |
| Independent tool calls | The **number, target and type** of call is decided at runtime from a budget it manages |
| Decisions nobody triggered | Runs on a schedule; produces detections, penalties and a watchlist unprompted |
| Closes the loop | Re-queries history to score its own prediction; updates its margin **and** its matrix |
| Bounded | Fail-safe ladder · human gate · credit guard · numeric grounding assertion on all generated prose |

**Concede unprompted:** the numeric decision path is deterministic and replayable to an identical number.
For a system producing evidence in a regulatory process, that is correct engineering, not a limitation.

---

## 6. Does it make a tedious system autonomous?

**Yes, and the system it replaces is explicit and documented:**

> **The ASU team bolted thermometers to cars and drove around four buildings for four months** [L].

Vehicle transect campaigns are the standard method for this measurement. Thermal impact assessment today
is a consultancy engagement with field crews, or a CFD study that takes weeks and models **only the campus
you own.**

**We replace a field campaign with one API call and a statistical test.**

---

## 7. Does it interest FortyGuard's partners? Can the CEO sell it?

**Do they cluster?** Yes — measured, not asserted [M]:

```
Metro                    facilities   pairs≤500m   pairs≤800m   %with ≥1 nbr ≤800m   median nbrs   max
Ashburn / Loudoun VA        226          583         1,276             99%                11         30
Santa Clara CA               58          180           268             90%                12         19
Dallas–Fort Worth TX         55           52            66             78%                 1          7
Phoenix E-valley AZ          44           30            46             55%                 1          9
                            383 total                                 ~90% across all four
```

Closest pair **62 m** against a **500 m** plume. **Not an Ashburn problem** — and note Sailor et al.
measured the effect in **Phoenix**, a different metro entirely.

**Would a hyperscaler buy this from a student? Probably not — they would build it in-house.** They have
site-selection teams, CFD consultants and weather-data contracts. **Do not claim otherwise on stage.**
Four things survive that concession:

1. **CFD models the campus you own. It cannot model your neighbour's plume** — you do not know their
   equipment, load or exhaust layout. Only external measurement gets it. A structural gap, not a gap in
   their competence.
2. **They model; this measures.** CFD predicts from assumed inputs. A permit hearing needs a measurement
   with a control group.
3. **Colocation is the bigger and far less equipped market** — Digital Realty, Equinix, CyrusOne, Vantage,
   QTS, Aligned. Packed against competitors they do not control, a fraction of the in-house science, much
   more exposure to who builds next door. **Santa Clara's density is largely colo.**
4. **Counties have nothing at all**, and Loudoun is drafting standards right now.

### The decisive reframe

**The audience is FortyGuard, not AWS.** The question is not *"will a hyperscaler buy this from you"* but
*"does this prove a valuable use case for FortyGuard's API."*

**If AWS builds it in-house, they still need FortyGuard's data to do it.** That is the sale.

FortyGuard sells an **API**, not reports. What they need is use cases that force **recurring, high-volume
consumption by customers with money**: hourly fields across a portfolio, historical sweeps for every siting
decision, per-facility monitoring. Their named partners — **Microsoft, Google, AWS, NVIDIA** — all build
and operate data centres, so this is an **unmonetised use case inside customers they already have**. And
their CEO has publicly named data-centre siting as a use case [L].

**The pitch:** *"Every data centre cluster in America has a thermal interference problem — modest at the
operating level, very large at the siting level. Satellites measure the wrong variable. Weather models are
3 km blurry. The published state of the art is two cars at four buildings. Your API is the only instrument
that can measure it, and here is a working reference implementation."*

**That is also the answer to whether FortyGuard could take it forward.** You are not handing them a product
to sell. You are handing them **a reason for Microsoft to buy more data.**

---

## 8. Technical feasibility — what is now measured

### Verified before writing any code

| Finding | Value | Why it matters |
|---|---|---|
| **Lattice stability** | **6,875 / 6,875 tiles byte-identical** between a forecast call and a historical call over the same polygon [M] | Per-tile time series are valid. Without this, nothing downstream works |
| **Forecast ↔ historical symmetry** | Same request shape yields prediction and, later, outcome. Real residual measured: mean **+0.349**, sd **0.150** [M] | A working residual generator, proven not assumed |
| **Tile geometry** | Real polygons, **59.7 × 61.4 m** [M] | Genuine spatial join to asset points |
| **One call covers a metro** | **17,658 tiles at 64 km², granularity 60, in 67 s** [M] | The whole measurement is one call |
| **Air, not surface** | Diurnal amplitude **7.8–8.3 °C** [M]. Surface would swing 20–30 °C | **Independent proof we hold the instrument the dispute requires** |
| **`filter_type=4`** | One call = per-tile **monthly** min/max (14.81 / 36.85) [M] | Historical sweeps are cheap |
| **Flat pricing** | heatmap **4,220** cr/call, independent of area, granularity, hours, mode [H] | Bigger polygons are free. **The control sites live inside the same call as the facilities** |

### ⚑ Effective resolution — the risk I most wanted closed, now closed

Mean absolute tile-to-tile temperature difference as a function of separation, from the 6,875-tile field
already on disk [M]:

```
separation        mean |ΔT|      ratio vs. previous
   45–75   m       0.0108 °C           —
   90–150  m       0.0252 °C         2.34×
  180–300  m       0.0481 °C         1.91×
  360–600  m       0.0926 °C         1.92×
  720–1200 m       0.1695 °C         1.83×
 1400–2400 m       0.3009 °C         1.78×
```

**Smooth, monotonic, near-constant ratio per doubling. No flat region. No jump near 500 m.** Had the field
been upsampled from ~500 m data, |ΔT| would be near-zero below 500 m and then step up. It is not.
**The 60 m resolution carries genuine structure.**

**And the derived number that makes the project feasible:**

```
background variation at the plume scale (~500 m)   ≈ 0.09 °C   [M]
the signal we are hunting                          0.7–2.2 °C  [L]
                                                   ─────────────
signal-to-background                               ≈ 8–24×
```

**The effect is an order of magnitude larger than the natural variation at the same scale.** If the plume
is present in FortyGuard's field, it should be unmistakable.

### ⚠ Two findings that changed the plan

**(a) Only 34 % of days are usable.** Wind-steadiness census at KIAD, summer 2025, afternoon window
12:00–20:00 local [M]:

```
days assessed                                             90
usable (steadiness ≥0.85 AND mean speed ≥6 kt)            31   (34 %)
  → a 13-day live window yields only ~4.5 usable days
octants populated over one summer                          7 / 8
sensitivity:  ≥0.80 / ≥5 kt →  41 days (46 %), 8/8 octants
              ≥0.90 / ≥8 kt →   9 days (10 %), 5/8 octants
```

**Consequence, and it is a real correction:** the interference matrix **cannot be built from the live
window.** It must be built from **history**, with days selected by METAR wind. The live window's job is
**confirmation, not construction.** A plan that accumulated the matrix live would have produced two or
three usable days and a mostly-empty matrix.

**(b) Our first sample polygon was badly placed.** The 5 × 5 km box we already paid for contains **6
facilities, and none of them sits ≥550 m inside the edge**, so no wedge could be drawn. A grid search over
Loudoun found much better placements [M]:

```
 5×5 km   (~6,944 tiles)   centre 39.0050, −77.4580  →  137 inside, 105 usable
 8×8 km  (~17,777 tiles)   centre 39.0100, −77.4460  →  169 inside, 168 usable   ← use this
11×11 km (~33,611 tiles)   centre 38.9850, −77.4700  →  188 inside, 177 usable
```

**168 facilities measurable in a single call**, at a tile count already proven to complete in 67 s.

---

## 9. Risks, ranked, with what each would cost

| # | Risk | Test | If it fails |
|---|---|---|---|
| **1** | **FortyGuard is blind to waste heat.** If the model infers temperature from land cover, a facility reads warm merely because it is a big dark building | **P-2 wind-following** — does the warm side move when the wind moves? Land cover does not move | **Not fatal.** Supports Masley, satisfies his requirement (iii), and the operational half survives on the *static* cluster signature as a spatial correction to the regional forecast |
| **2** | ⚠ **The control group may be too good.** If the model is land-cover-driven, a **warehouse and a data centre look identical to it** — so controls would show the same apparent plume and we would get a null **by construction** | Q-2, in conjunction with P-2 | We would have learned the instrument cannot answer the question. **Report it.** This is the sharpest available objection and it belongs on the limitations slide |
| **3** | **Free data may predict the field.** If OSM land use + building density + NDVI + elevation reproduce FortyGuard's field with R² > 0.9, the premise collapses | **R-2** — free, computable now | Fatal to the "only FortyGuard" claim. **Must be run before Aug 18** |
| **4** | **The money may not follow.** If ambient rarely sits within the interference magnitude of the threshold | **U-1** — free | The operational half is worthless; the measurement half still ships |
| **5** | Airport wind ≠ facility wind | Restrict to strong, steady regional flow; report bearing-tolerance sensitivity | A stated limitation, not a blocker |
| **6** | Industrial-area confounding | Control-site matching on footprint, roof type, impervious fraction, road proximity, elevation | Mitigated, not eliminated. Disclose |
| **7** | Price unverified on the hackathon key — metering was frozen on the audited key, so ~16 verification calls registered **0** [M] | First call on Aug 18 | Re-budget |
| **8** | History does not reach 2019 — two attempts, two modes, ~6–7.5 min hang then `Failed` [M] | Bisect 2025 / 2023 / 2021 | Bounds how far back commissioning analysis can go |

---

## 10. Conclusion

**It is a selling point.** The problem is real, current, contested, and unmeasurable by anything else. The
market is measured rather than asserted. The instrument has been verified against seven separate technical
requirements before a line of code was written. And it cannot fail to produce a finding — if the plume is
absent from FortyGuard's field, that outcome supports one side of a live scientific dispute and satisfies
a published requirement for settling it.

**It becomes a theoretical study if three things are not done:**

1. **Frame it as thermal due diligence**, not neighbourhood exposure reporting
2. **Frame the agency as budgeted experiment design**, not conditional branches
3. **Never quote a point-estimate dollar figure** — the measurement is the finding; money is a band

**And three limitations must be volunteered before a judge finds them:** the control group may be too good
(§9 #2), airport wind is a proxy, and every economic figure rests on stubs.

**Score: ≈83 / 100. The gap between 83 and 71 is entirely whether it reads as a product or a study.**

---

## Sources

- Sailor, Samareh Abolhassani & Martin, *"Data Center Waste Heat as an Emerging Urban Thermal Hazard: First
  Field Measurements of Neighborhood-Scale Air Temperature Impacts"*, ASME **J. Eng. Sustain. Bldgs. Cities**
  7(2):024501, 2026
- Masley, *"Data centers' heat exhaust is not raising the land temperature around where they're built"* —
  the LST-vs-air critique and the four requirements for settling it
- Loudoun County: ZOAM-2024-0001 (Mar 2025, by-right permitting eliminated); Phase 2 Data Center Standards;
  Board motion toward an application pause (Jul–Aug 2026)
- US data centre market scale: Avison Young Q2 2026 market overview; Ashburn facility count (May 2026)
- Data-centre engineering practice on heat rejection and **recirculation into fresh-air intakes**
- Industry commentary: *"the heat island effect operators are refusing to own"*
- OSHA Heat Injury and Illness Prevention rulemaking status and NEP expiry (8 Apr 2026) — cited only to
  document why an alternative direction was rejected
- FortyGuard CEO interview naming data-centre siting as a use case
- All **[M]** figures: `hackathon/hackathon/results_raw.json`, `openapi.json`, and the validation responses
  captured 2026-08-08/09 in the session scratchpad
