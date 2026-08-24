# NATIONAL BUILD — every US data centre in the picker, each on its own data

**Opened 2026-08-23. Requested by the user: three sites (one without a FortyGuard field) does not
show impact or commercial value; the agent has to run across the United States.**

> **READ THIS BEFORE ANY SESSION.** Stage status is the table in §6. The user's three standing
> decisions are §2 and they are not to be re-litigated. **Rule 8 still binds: ask before every paid
> call.** §3 is the arithmetic that bounds the whole thing.

---

## 0. 🔴 2026-08-23, LATER THE SAME DAY — THE REFUSAL RATE CONCERN, AND WHAT THE FUNNEL ACTUALLY SAYS

**The user, having seen "35% of pairs refuse every bearing" read as alarming, said: eliminate the
possibility of refusal, don't stand on logic so firmly that we refuse lots of sites, and don't
over-complicate wind/plume to the point of mass refusal.**

**Measured from the three committed sites' own `selected_site.json` funnels — not from memory:**

| | Ashburn | Chicago | Dulles | Total |
|---|---|---|---|---|
| candidate pairs considered | 611 | 2,148 | 53 | 2,812 |
| rejected: not actually a data centre | 220 | 2,133 | 11 | **2,364 (84 %)** |
| rejected: too close / bad facade | 254 | 6 | 26 | 286 (10 %) |
| survived to physics | 141 | 9 | 16 | 166 |
| refuse every wind bearing | 53 | 2 | 3 | 58 |
| **clean pairs available** | **88** | **7** | **13** | — |

🔴 **THE 35 % FIGURE IS PER-CANDIDATE-PAIR, NOT PER-SITE, AND IT WAS BEING READ AS THE LATTER.**
Every metro tried so far found a clean pair on its FIRST attempt (88, 7, 13 available — we only
ever need one). **The plume/wind logic is not the thing that has refused anything.** The two real
refusals (Santa Clara, Phoenix) are facts about the physical world — rooftop cooling equipment
outside a ground-plane model's view, and a cluster that is bare desert with nothing built — not the
recirculation gate being too strict. **84 % of "rejections" are the pairing search trying every
combination of two tagged buildings and correctly discarding the ones where one isn't a data
centre.** That is bookkeeping, not refusal.

### 0.1 Where refusals COULD actually spike at national scale, and the honest fix

The real risk is different: the pipeline is **pair-based only**. A standalone data centre with no
other data centre nearby currently has nothing to be paired against, so it would fall out of the
funnel entirely rather than being evaluated. Most of the ~1,500+ national candidates are likely
exactly this — isolated, not part of a tight campus.

**Proposed fix, not yet built:** a data centre with no other data centre within the plume's
negligible-effect radius has **zero recirculation by geometry** — a real, favourable, honest
result, not a refusal, and it needs no 576-solve GPU run to establish, only a distance check. This
directly serves "eliminate refusal" without loosening any existing gate:
- **Isolated sites** (the expected majority): recirculation = 0 by measured geometry, ship with a
  plain statement of why (no data centre within the negligible-radius), decision made on the FG
  temperature/humidity/AQ gates alone.
- **Campus/paired sites**: run the existing, unmodified, already-strict pairwise funnel exactly as
  built. It already works — see the table above.
- **Genuine site-level refusals stay rare**: rooftop-cooled retrofit markets and untagged/unbuilt
  clusters, which are real physical facts, and this project's own most credible line is that it
  refuses those *on evidence*, not that it never refuses.

**Gate on this only with a SOURCED distance**, not an invented one — gotcha #49 is the exact scar
(`wetbulb_margin_c = 3.0`, swept and still invented).

### 0.2 ✅ DECIDED 2026-08-23 — no distance threshold. A validated-domain boundary instead.

**A workflow researched a "negligible beyond X metres" cutoff and its own adversarial verify step
rejected it: NOT_DEFENSIBLE.** The derivation compared the three committed sites' rises against the
0.5556 °C ASOS floor without applying this project's OWN already-measured correction — the solver
under-predicts rise by 5–25 % at these distances (N-35, 67 Prairie Grass experiments,
`RECIRCULATION-DEFENCE.md:231-233`). Applied correctly, Chicago's margin against the floor shrinks
to ~7 % — too thin to support ANY blanket "assume zero past here" rule, and inventing one would be
biased in the unsafe direction, which is worse than the last invented-constant scar (#49), not
milder.

**What ships instead — a claim about the TOOL's validated domain, not about physics beyond it:**
Project Prairie Grass (1956), already cited by this project, is *"the most complete [field
validation] available for the analysis of surface layer dispersion, at 150–600 m, which is our
range"* (`RECIRCULATION-DEFENCE.md:33`). This solver has never been checked against reality past
600 m, and a near-field building-wake model has no business being extrapolated to kilometre-scale
transport — that is a different atmospheric regime (mesoscale), not a distance this tool was built
for.

| Nearest other tagged data centre | What happens |
|---|---|
| within the solver's validated range | run the EXISTING, unmodified pairwise funnel (gap, facade, wind) on the real geometry — nothing about the current logic changes |
| beyond it | **recirculation is NOT MODELLED**, stated on screen as a limitation with its reason and source — **not a refusal**. The free-cooling decision runs on FortyGuard's own temperature/humidity/AQ perception alone, same gates the paired sites also use |

🔴 **This does not reduce what any site is shown.** Requirement 2 (a FortyGuard field for every
site) is unaffected — recirculation and the FortyGuard perception gates are separate systems, and a
standalone site still gets its own field, its own map point, its own decision. What changes is only
whether a *plume* term is added to that decision, and the honest answer for a genuinely isolated
site is that there is nothing nearby for it to add.

### 0.3 ✅ FOUND 2026-08-23 — the discovery script itself was silently deleting the sites this need

`discover_dc_clusters.py` clustered by an ~11 km grid and kept only cells with **`>= MIN_CLUSTER`
(3)** tagged buildings — one threshold conflating two different real cases that were both being
thrown away before ever reaching a human or a later stage:
- **Exactly 2 tagged buildings in a cell** is not "not a cluster" — it is precisely what
  `select_site.py`'s existing pairwise funnel needs (one source, one receptor). It was being
  dropped for no architectural reason.
- **Exactly 1** is the real standalone case §0.2 now has an honest path for, and it was being
  dropped entirely — a national build that deletes every isolated site before counting them cannot
  claim "majority of US data centres."

**Fixed in `discover_dc_clusters.py`:** every cell with ≥1 tagged building is now emitted, tagged
`category: "cluster" | "pair" | "single"`, state resolved once per cell (not per building, to keep
the free Nominatim lookup count sane), with `osm_ids` carried through for traceability.

✅ **First national run completed 2026-08-23 20:43** (old schema, clusters-only): **1,645 distinct
tagged data-centre ways nationally, 130 clusters of ≥3.** MO's Overpass query failed outright (needs
a retry — `states_failed`, not evidence of zero). Confirmed the state-resolution fix holds at
national scale.

### 0.4 ✅ FOUND AND FIXED 2026-08-23 — two "unresolved" clusters were actually CANADIAN

The first run's two `state: null` entries were not a geocoding hiccup — reading them showed real
data centres: **Cologix TOR4, Equinix Markham TR5, EdgeConneX Toronto** and others, 13 tagged
buildings between two clusters, both in **Toronto/Markham, Ontario.** The `NY` state box's northern
edge sits at 45.1°N, well past the border, and `resolve_state()` collapsed two different situations
into the same `null`: *"Nominatim could not be reached"* and *"this coordinate genuinely is not in
the United States."* A national build scoped to the US cannot ship a real Canadian data centre
un-flagged — that is the sharper form of "never claim a data centre that does not exist": never
claim a real one is a US one when it is not.

**Fixed: `resolve_geo()` replaces `resolve_state()`**, reading Nominatim's `country_code` and
returning a `reason` — `outside_united_states` (confirmed foreign, excluded with its evidence kept
in `excluded_non_us`) vs `geocode_failed` (a real retry candidate, kept in `unresolved`). Verified
against both Canadian coordinates (now `country: "ca", reason: "outside_united_states"`) **and**
Ashburn plus a WA cluster sitting right next to the same border (both still resolve cleanly to
`us`/their real state) — the control holding is what proves the fix is a fix (#132's method).
Any border-adjacent box (WA/ND/MT/ME here; TX/AZ/CA near Mexico are the same exposure) is covered
by the same general fix, not a two-entry patch.

✅ **Second national run completed 2026-08-23 21:25** (corrected schema + border fix): **1,646
distinct tagged ways, 433 cells with ≥1 tagged building — 127 clusters (≥3) / 58 pairs (==2) / 236
singles (==1), 12 cells (25 buildings) confirmed outside the US** (Canada AND Mexico both showed up
— the general border fix caught more than the two originally-observed Canadian cases, which is what
"general, not a two-entry patch" was supposed to buy). **58 exactly-2 pairs and 236 standalone
singles exist nationally that the old script would have deleted before anyone counted them.**

### 0.5 ✅ FOUND AND FIXED 2026-08-23 — the output dict silently lost one real site to a key collision

**The arithmetic didn't close: 127+58+236 = 421 counted, but only 420 survived in the written
file.** The old output key was `"%s_%.2f_%.2f" % (state, min(lats), min(lons))` — for a
single-member cell that is just the one building's own coordinate, rounded to 2 decimals (~1.1 km).
Two DIFFERENT standalone data centres, each correctly in its own separate grid cell but close
enough to a shared boundary that their raw coordinates rounded to the same two decimals, collided
on that key — and one silently overwrote the other. **Real, distinct sites, silently reduced to
one**, exactly the failure class this project's own rules exist to catch (§10's repeated "two things
must not be flattened into one" scars — #98, #132, #133, #142, all one site standing in for
another; this is the same shape one layer earlier, before either site had even been screened).

**Fixed:** the key now uses the cell's own `(row, col)` grid index — the literal dict key `cells`
was already built from, unique by construction — instead of re-deriving a rounded coordinate.
**A mechanical tripwire was added** (`len(allc) != n_cluster + n_pair + n_single` raises and refuses
to write the file) so a future collision, from any cause, cannot silently ship again — it is a
guard against the NEXT key-format change, not a fix that trusts itself.

✅ **Third national run (collision fix) launched 2026-08-23, in progress.** This is the registry S3
will actually use — do not use v1 or v2's `dc_clusters.json` for anything; both are superseded.

---

## 1. THE USER'S REQUIREMENT, in their own terms

1. **All US data centres in the dropdown, or the majority of them**, with their locations on the
   front-page map.
2. **A FortyGuard field for every one.** *"The core claim of our project is FortyGuard data, so that
   can't be dismissed or neglected at any cost."*
3. **No site may use another site's data.** *"Every site has its own specific geometry and own data
   and own picture from the map."*
4. **Never claim a data centre that does not exist.** Real, researched, individually approved.
5. Where a limitation cannot be engineered away, **state it against that specific site** rather than
   dropping the site or hiding the gap.

**The point of the exercise is commercial: large-scale impact.** A national result is the argument;
three sites is an anecdote.

---

## 2. DECISIONS THE USER MADE 2026-08-23 — settled, do not reopen

| | Decision | Consequence |
|---|---|---|
| **FortyGuard fields** | **Bought PER CLUSTER, not per site** | One 8×8 km call covers a campus; each site reads **its own tile at its own coordinates**. ~150 calls covers the country instead of ~2,000 |
| **Spend ceiling** | **150 heatmap calls = 633,000 credits**, 40 % of the 1,600,160 remaining | Leaves 967,160 and the N-26 collector's budget intact. **Not a licence to spend without asking** — rule 8 is per batch |
| **Deadline** | **HARD STOP on new build work 2026-08-28.** Aug 29–30 is freeze, verify, document, ship | Submission (public repo, collaborator, live link, video) is still the whole remaining risk and is the user's |

### 2.1 What "per cluster" does and does not mean

**It is a shared PURCHASE, never a shared VALUE.** A heatmap response is 17,862 tiles at 60 m
spacing across 8×8 km; two sites in one cluster read two different tiles with two different
temperatures. That is what a spatial field product *is*.

🔴 **This is NOT the defect family that has bitten four times** — #98 (Chicago's footprints on
Ashburn's photograph), #132 (Chicago's plume solved on Virginia's wind), #133 (Ashburn's field shown
on Chicago's page), #142 (Chicago's replay taking Ashburn's humidity). In every one of those, a site
was handed **another site's value**. Here each site reads its own coordinate out of a field that
covers both.

**The rule that keeps it honest, and it must be enforced mechanically:** every site records the AOI
it was served by, its **own tile's distance from its own centroid**, and the purchase timestamp.
`MAX_TILE_DIST_M = 2000` already refuses a tile too far away — that guard exists because replaying
Ashburn's field for Chicago silently returned a tile **926 km** away (§9.2b). At national scale the
dangerous case is not 926 km, it is 4 km, so the distance must be **published per site**, not merely
checked.

---

## 3. THE ARITHMETIC THAT BOUNDS EVERYTHING — measured 2026-08-23

| Constraint | Measured value | Where it binds |
|---|---|---|
| Heatmap price | **4,220 credits** | 150 calls = 633,000 |
| Credits remaining | **1,600,160** | allows 379 calls — **not** the binding constraint |
| **Vendor daily cap** | **30 heatmaps/day** | 🔴 **THIS is the binding constraint.** 150 calls = **5 days minimum** |
| Days to hard stop | **Aug 23 → Aug 28** | 5 build days. Zero slack if the vendor fails a day |
| AOI covered per call | **8×8 km, 17,862 tiles @ 60 m** | one call serves a whole campus |
| Clusters in 4 states | **37, holding 530 tagged DCs, coverable by 41 calls** | measured from `dc_clusters.json` |
| **Projected nationally** | **~120–150 clusters, ~1,500–2,000 tagged DCs, ~150 calls** | the 150-call ceiling was chosen to match this |

### 3.1 Repo size — solved, and it was the thing that made this impossible

**Marginal cost per site was ~36 MB. It is now ~5 MB, and can go to ~3 MB.**

`scenarios.json` is **31 MB per site** and has exactly one consumer in the tree:
`demo/verify_browser_decision.js`, which opens `__dirname + '/scenarios.json'` — the unsuffixed
reference file, always. `index.html` never names it, `audit.py` never opens it, nothing reads
`artefacts["scenarios"]`. So `chicago_scenarios.json` and `dulles_scenarios.json` were **61.9 MB
shipped on no code path at all.**

✅ **Done 2026-08-23.** `agent.py` writes the dump only for the reference site (or under
`WRITE_SCENARIOS=1`). **The sweep still runs in full for every site** — all 120,960 rows — so
`trace["cases"]["summary"]` and every audited number are unchanged; only the row dump is skipped,
and only where nothing reads it. A site that does not ship it records `in_file: null` **and the
reason**, rather than pointing at Ashburn's file the way the old code did.

**`demo/` went 120.5 MB → 57 MB.** At ~5 MB/site a 100-site build is ~500 MB; with JPEG aerials in
place of 2.5 MB PNGs it is ~300 MB. **A 3.6 GB repo cannot be published, and a public repo is a hard
submission requirement — this is why the size work came first.**

---

## 4. THE GATES EVERY SITE MUST PASS — none of them may be skipped to make a number bigger

A tagged building is **not** a shippable site — but as of §0.2/§0.3, "no nearby data centre" is a
**pass into the standalone path, not a refusal**. **Refusal is now reserved for the two things that
are actually facts about the physical world**, both rare: rooftop-cooled retrofit equipment (G5)
and a tagged cluster that was never built (G5). Measured against the three committed sites, that is
2 metros refused out of 5 — not 35 %, which was a per-pair statistic mislabelled as per-site
(§0, corrected 2026-08-23).

| # | Gate | Cost | What it decides |
|---|---|---|---|
| G1 | **Exists in OSM as a tagged data centre** | free | untagged halls are invisible — a LOWER BOUND, never a market-size claim |
| G2 | **Does another tagged data centre exist within the solver's validated range (≤600 m, §0.2)?** | free | **YES → paired path** (existing funnel, unchanged). **NO → standalone path** (§0.2): its own field, its own map point, recirculation stated as not-modelled. **Neither answer is a refusal** |
| G3 | *(paired path only)* **Facade gap ≥ 60 m** (`MIN_GAP_M`, derived, and #65 proves it was wrong at 50) | free | Ashburn's own committed site clears by **0.3 m**. Every metro tried so far (3 of 3) found a clean pair on its first attempt — see §0's funnel table |
| G4 | **Weather station ≥ 95 % coverage over 5 years** | free | #68: nearest is not best, complete is best (KIWA at 2.7 km rejected at 81.7 %) |
| G5 | **Imagery verdict: ground-level plant, actually built** | free | 🔴 the ONLY gate that has actually refused a whole site — Santa Clara (rooftop) and Phoenix (bare desert). Real facts, not tunable |
| G6 | *(paired path only)* **The solver does not refuse the geometry** | GPU | refused Dulles rank 1 — 4 % of the intake disc on condenser cells |
| G7 | **Its own FortyGuard field** | **4,220 / cluster** | the user's requirement 2 — standalone sites get one too, §0.2 |

🔴 **A site that fails G5 is REFUSED AND PUBLISHED AS REFUSED**, with the frame and the reason. That
is evidence, not a gap — and it should stay the RARE case, per the user's explicit instruction not
to stand so firmly on logic that many sites are refused. **Do not pad the dropdown with sites that
failed G5**, but do not manufacture a refusal out of G2/G3/G6 either: G2 has its own honest
non-refusal outcome now, and G3/G6 have so far cleared every metro tried.

⚠ **G5 has a known resolution limit and it must be stated per site, not globally:** chillers and
generators are **indistinguishable at 0.3–0.5 m**, which is why Dulles's verdict is recorded as
weaker than Ashburn's (no USGS cross-check, so the two-source rule is not met). At national scale
most sites will have one imagery source. **Record the confidence per site.**

---

## 4a. 🔴 S3 RESULT, 2026-08-23 — FULL NATIONAL COVERAGE NEEDS 399 CALLS, NOT ~150

`src/pack_national_aois.py` packs the 422-entry registry by REAL measured extent (each entry's own
`lat_range`/`lon_range`), not the discovery grid — an entry bigger than 8×8 km gets its own split,
never shared; everything else is greedily packed into real, shareable 8×8 km boxes. This is a
stated heuristic (exact geometric bin-packing is NP-hard), not a proven optimum, but it is real
distance-based packing, not the grid's arbitrary edges.

| | |
|---|---|
| Registry | 422 entries (127 cluster / 58 pair / 237 single), 1,647 tagged buildings |
| Oversized (own extent > 8 km) | 8 entries, needing 16 dedicated purchases — never shared |
| Packable | 414 entries → **383 purchases, only 29 of which share ≥2 registry entries** |
| **TOTAL for full national coverage** | **399 real purchases, covering 1,622 of 1,647 tagged buildings** |

🔴 **The 150-call ceiling was set from a projection built on Ashburn's dense-campus pattern
(41 calls covering 530 tagged DCs in 4 states). Most of the country does not look like Ashburn** —
only 29 of 383 packable purchases share more than one registry entry; the rest are genuinely
isolated locations too far apart to share an 8 km box. **399 vs the 150-call ceiling is the real
gap, not an estimate.**

🔴 **CORRECTED 2026-08-23, same day: the "30/day" figure was NEVER a confirmed vendor limit, and
calling it "physical" here was an overclaim the user was right to challenge.** Its only source is
`fortyguard-api-findings.md` §8.7 request #6, phrased *"we understand it to be 30 heatmaps/day"* —
inside a request ASKING FortyGuard to document a cap this project has never been able to confirm
from the API itself (no response header, no plan-tier spec, no observed rejection at call #31).
**What IS real and measured: the credit balance.** 1,600,160 remaining ÷ 4,220/call = **379 calls**,
independent of any daily-cap question — 20 short of the 399 needed for full coverage. The
allocation question below is otherwise unaffected: it was always about which purchases to prioritise
under a real ceiling, and 379 is that ceiling, not 150.

**The open question is therefore ALLOCATION, not budget: which purchases to prioritise under the
real ~379-call ceiling.** Ranking purely by impact (tagged buildings served per purchase —
`pack_national_aois.py`'s current sort) covers 82–83 % of tagged buildings with the top ~150-200,
but skews heavily toward the already-dense VA/CA/TX corridor, because that is where sharing is
possible. **The user's decision 2026-08-23: start with real tagged data centres, ordered by highest
impact, continuing until all are covered** — i.e., use the existing impact ranking and push as far
down it as the real ceiling allows, rather than reserving calls for geographic breadth first.

---

## 4b. 🔴 FIRST LIVE PURCHASE ATTEMPT, 2026-08-23 — 0 % SUCCESS, MANUALLY STOPPED, TWO SCRIPT DEFECTS FOUND

**Authorised: "authorize the full 379 now."** `testing/buy_national_fields.py` built to buy one
past, elapsed 8×8 km field per ranked AOI — same shape as the proven `fetch_chicago_field.py`
(granularity 60, `tcm`, 2 h window, ≥30 min safety margin), timezone MEASURED per AOI via
`timezonefinder` (verified against 5 known coordinates spanning Eastern/Central/Mountain/Pacific/
Arizona's no-DST zone before being trusted) rather than a state-level guess.

**A packer bug was caught by the dry run before any money moved:** the 8 oversized clusters
(own extent > 8 km) were each ONE list entry carrying `n_calls: 2`, not two actual differently-
centred purchases — a buyer iterating the list would have bought a single box on the campus
centroid and silently missed the buildings outside it. Fixed in `pack_national_aois.py` to emit one
real, distinctly-tiled entry per actual sub-box; re-verified the corrected registry (399 entries,
matching `dryrun`'s count exactly) before spending anything.

**The live run: first chunk of 20, 100 % failure.** All 20 came back `completed_but_empty` —
0 tiles, fully billed, the exact historical outage signature HANDOFF.md §4.0 documents at length.
**Killed manually rather than let the script's own `STOP_AFTER_BAD_CHUNKS=2` wait for a second bad
chunk to confirm what a unanimous first chunk had already shown.** That decision itself exposed a
second, worse defect:

| | |
|---|---|
| Confirmed (in the ledger) | 20 calls, all `completed_but_empty` |
| **Unaccounted for at the moment of the kill** | **14 more calls, billed (84,400 → later found to be part of a 143,480-credit total = exactly 34 calls, zero remainder) with NO ledger record** |
| Why | `run_chunk()` batched classification + ledger-append until the WHOLE chunk (all 20 jobs) resolved. Billing happens server-side the instant FortyGuard's OWN job completes — independent of whether this process is still alive to poll for it. A mid-chunk kill left real, billed spend with no record: gotcha #103's exact lesson, in a new shape (a batching WINDOW instead of a missing source) |

**Fixed:** `finalize_job()` now classifies, saves the field (if real) and appends to the ledger THE
INSTANT this process itself learns a job is terminal — inside the poll loop, not after the slowest
sibling in its chunk also finishes. A rejected submit is finalized immediately too. **Also fixed:**
stdout was fully block-buffered when redirected to the run's log file, so nothing printed for the
first several minutes of real, billed activity — the only way to see the run was actually working
was to check the live credit meter directly. `sys.stdout.reconfigure(line_buffering=True)` added.
**Also fixed:** a unanimous 0-of-≥10 first chunk now stops immediately rather than waiting for a
second bad chunk to "confirm" it.

**Diagnosis before any further spend, all free:**
- ✅ **Not a timezone bug** — every requested window was verified 18–21 hours genuinely elapsed in
  its own zone at run time, well past the 30-minute margin.
- ✅ **Not a payload-shape bug** — `polygon_aoi`/`granularity`/`analytic_type`/`date_time` fields
  are structurally identical to the proven `fetch_chicago_field.py`.
- ⚠ **Rank #1 of the failed batch (VA, centre 39.0244,-77.4496) sits in the SAME broad area as the
  already-successful Ashburn geometry** — arguing against "the vendor simply doesn't cover these new
  locations" and toward either a renewed general outage (the forecast path had recovered hours
  earlier the same day, §4.0-RECOVERY; a relapse is plausible given the vendor's whole recent
  history) or something specific to past/observed requests at AOIs never previously requested.
- ✅ **DISTINGUISHED 2026-08-23 — DIAG-66, one authorised control call.** Same date/hour as the
  failed batch's rank #1 (2026-08-22 14:00–16:00), at ASHBURN'S OWN long-proven committed centroid
  (39.024017, -77.419691) instead of the new national cluster ~2.5 km away. **Result: also
  `completed_but_empty` — 0 tiles, 44 empty polls over 481.5 s, billed 4,220 in full.**
  **VERDICT: GENERAL, RENEWED OUTAGE — not AOI-specific.** Even the geometry that returned 12/12
  populated forecast windows THIS SAME MORNING (§4.0-RECOVERY) failed identically a few hours
  later. **The vendor relapsed within the same day it recovered.** Resuming the national batch
  right now would spend into the same fault regardless of which AOIs are prioritised.
- 🔴 **RETRACTED, the same discovery:** `fetch_chicago_field.py`'s docstring claimed *"a past
  window has NEVER failed on this key across nine calls"* — true as of 2026-08-19, false as of
  today. Marked retracted in both `fetch_chicago_field.py` and `buy_national_fields.py` rather than
  silently rewritten, per this project's own rule that retractions stay visible. **A past window
  reduces risk; it is not, and was never provably, a guarantee.**

**Spend so far this session:** 1,600,160 → 1,456,680 at first check (**143,480 credits, 34 calls**,
exact division confirms no mixed pricing). **20 of 34 confirmed `completed_but_empty`; the other 14
are unconfirmed (no saved activity_id — lost to the same batching bug the ledger fix now closes) but,
under identical conditions in the same short window, almost certainly the same outcome. Stated as
inferred, not measured, because it is.**

⚠ **LESSON: killing the client process does NOT cancel already-submitted vendor jobs.** A second
check a few minutes later found the balance had dropped AGAIN, unattended, with no process running
— 1,456,680 → **1,439,800 (160,360 total, exactly 38 calls, still zero remainder)**, then stable
across two immediate re-checks. This is not a new incident: chunk 2's ~20 jobs were already
submitted (staggered, ~8 s) before the kill, and FortyGuard's servers continued processing and
billing them asynchronously regardless of whether the polling client that submitted them was still
alive. **"Stop the process" stops future submissions and this script's own bookkeeping; it does not
recall a job the vendor has already accepted.**

**Plus DIAG-66's own 4,220: total this session 1,600,160 → 1,435,580 = 164,580 credits, exactly 39
calls, zero remainder.** 39 of 39 known outcomes are `completed_but_empty` or its inferred
equivalent — **0 % success across every call made today after the morning's recovery.**

🔴 **DO NOT RESUME THE NATIONAL BATCH.** The outage is general and current, confirmed by a clean
control at the best-proven geometry this project has. Spending further right now — at any
allocation strategy, any AOI — would spend into the same fault. **Wait for independent evidence of
recovery** (matching how §4.0-RECOVERY was itself detected: a paid probe, since there is still no
free way to ask "does the heatmap path work right now") before authorising another batch.

Anyone stopping a live batch mid-flight should
expect the credit meter to keep moving for a short while after, and should re-check it before
treating a kill as a hard stop on spend.

---

## 5. WHAT IS ALREADY FIXED, 2026-08-23 session 1

| | |
|---|---|
| ✅ **Dead per-site `scenarios.json`** | 61.9 MB removed; writer made reference-only; absence recorded with its reason. §3.1 |
| ✅ **State was inherited from the query bbox** | 🔴 `CA_36.06_-115.22` is **Switch Las Vegas, NEVADA**, and `CA_39.57_-119.55` is **Reno** — both labelled CA because California's box is searched first and reaches −114.1. **`money.prices_for_metro()` picks the electricity tariff off that field**, so Nevada campuses were priced on California power. Now reverse-geocoded from each cluster's own centroid, cached, 1 req/s, and `null` when unresolved rather than guessed. **Verified: Las Vegas → NV, Reno → NV, and Ashburn/Chicago/Santa Clara unchanged — the control holding is what proves the fix (#132)** |
| ✅ **`STATE_BBOX` 10 → 49 states** | `--all` now means the United States, not "the ten someone thought of". AK/HI omitted deliberately |
| ✅ **Overlapping boxes double-counted campuses** | 49 overlapping boxes return the same campus from several state queries. Now deduped on **OSM element id**, clustered once nationally, and the query states kept as `state_queries_that_returned_it` — evidence, not truth |
| ✅ **The "35 % refusal" number was per-pair, read as per-site** | §0. All 3 metros tried have found a clean pair on the first attempt (88/7/13 available); the 2 real refusals are physical facts (rooftop, unbuilt), not the plume logic being strict |
| ✅ **No sourced negligible-distance threshold exists, and none was invented** | §0.2. Ships as a validated-domain boundary (≤600 m, Prairie Grass, already cited) instead — beyond it, "not modelled" and stated, never "assumed zero" |
| ✅ **The discovery script was silently deleting exactly the sites this build needs** | §0.3. `MIN_CLUSTER=3` dropped every 2-building pair and every standalone site before they were ever counted. Now every cell with ≥1 tagged building is emitted, categorised `cluster`/`pair`/`single` |

---

## 6. STAGES — status table, update it every session

| # | Stage | Paid? | Status |
|---|---|---|---|
| **S1** | Foundation: size, state resolution, national bboxes, dedup | free | ✅ **DONE 2026-08-23** |
| **S2** | National discovery — Overpass across 49 states, cluster/pair/single registry | free | ✅ **DONE 2026-08-23 (v3)** — 422 entries verified, key-collision-proof. §0.3–0.5 |
| **S3** | AOI packing — real distance-based grouping into 8×8 km purchases | free | ✅ **DONE 2026-08-23** — 399 real purchases needed for full coverage, oversized-tiling bug found and fixed. §4a |
| **S7** | **FortyGuard fields, per cluster** | 🔴 **PAID** | ⚠ **STARTED, STOPPED — general vendor outage.** 39 calls made (135 total this plan), 0 successes today. DIAG-66 confirms it is not AOI-specific. §4b. **Blocked on vendor recovery — `national_recovery_watch.py` ready, attended-only, not scheduled** |
| **UI** | National footprint map on the front page — every registry entry, real coordinates, honest status (has field / attempted-empty / not yet reached) | free | ✅ **DONE 2026-08-23** — screenshotted light + dark, both correct. §9 below |
| **S4** | Geometry + pairing at scale (G2, G3), per cluster | free | ✅ **DONE 2026-08-24** — building-level union-find at the real 600 m range, real ring geometry, real G3 verdicts. §10 below |
| **S5** | Weather station assignment (G4) — ASOS, rate-limited, slow | free | ☐ next — a national ASOS station list is fetchable the same way (Iowa State Mesonet, per-state `<ST>_ASOS` networks, free/keyless), confirmed feasible but not started |
| **S6** | Imagery screening (G5) — own frame per site, annotated, verdict + confidence | free | ☐ |
| **S8** | Solve + build per site (G6), manifest | free (GPU) | ☐ |
| **S9** | Verify: `run_all` green, per-site differ checks extended to N sites | free | ✅ **holding green** — `audit.py` 95/95, real-Chrome panel diff clean, re-verified after every change this session |
| **S10** | **HARD STOP Aug 28** → freeze, docs, submission-ready | free | ☐ |

## 10. S4 — REAL GEOMETRY AND PAIRING AT NATIONAL SCALE, done 2026-08-24

**The naive approach would have been wrong twice over, and both times the audit was "does this
number look plausible," not "did I check."** Building this properly took three corrective passes:

1. **`classify_isolation.py` (now SUPERSEDED, kept as the record).** Treated each discovery-grid
   ENTRY as one aggregate point. Found a real bug this way — two Georgia entries 280 m apart,
   mislabelled "single" by both landing in adjacent ~11 km grid cells — but only found **28** real
   pairing candidates nationally, because it could not see that a "cluster" entry's OWN buildings
   might not be mutually within the solver's 600 m validated range. The discovery grid's cell size
   has nothing to do with the physics gate.
2. **Fixed properly: per-building coordinates, then real union-find at 600 m.**
   `fetch_national_building_centres.py` pulled every one of the 1,622 tagged buildings' own
   coordinate by OSM id (no bbox rescan — Overpass answers directly from its element-id index).
   `build_national_pairs.py` then unions any two buildings within 600 m and takes CONNECTED
   COMPONENTS as the real groups. Result: **396 buildings genuinely isolated, 243 real groups of
   ≥2** — **161 of those groups disagreed with the discovery grid's original category**, which is
   the measured size of the flaw step 1 could not see.
3. **G3, on real footprint rings, not centroids.** `fetch_national_geometry.py` pulled full way
   geometry (`out geom`) for the 1,226 buildings inside a real group. `measure_national_gaps.py`
   reused `to_metres()` / `ring_gap()` / `longest_edge()` **directly, unchanged** (gotcha #12) —
   no second implementation of a measurement this project already trusts. **Verdict: 100 groups
   clear the 60 m floor on real edge-to-edge geometry; 143 are too close and refused on evidence**,
   with real building names (e.g. Centersquare Ashburn IAD4's two halls, 1.9 m apart).

**A real overclaim caught and corrected in my own code before it could mislead anyone:** a
docstring asserted centroid distance "overstates" the true edge gap as a general rule. Measured
counter-example while spot-checking the CLEAR verdicts (not just the refusals): `TX_way_1533350872`
(Microsoft Texas Research Park) has a real ring-to-ring gap of 130.7 m against a crude
vertex-average centroid distance of only 50.7 m — the opposite of the claim. Corrected to state a
tendency, not a guarantee, once found. **It did not affect any verdict** — every G3 decision came
from real `ring_gap()`, never from the centroid heuristic, which was only ever used to pick which
pair to measure inside a larger group.

**Stated simplification, not hidden:** a group larger than 2 buildings (measured up to 81) is
represented by its CLOSEST pair, not a full combinatorial score across every internal pair — the
closest pair is also the one most likely to bind the 60 m floor, which is the conservative choice
for a refusal decision, but it is a chosen simplification and is documented as one, not a claim of
completeness.

**What S4 has NOT yet done:** picked which SPECIFIC 2 buildings within a cluster act as
source/receptor for the physics funnel when a group has 3+ real candidates (today: closest pair
only), and has not yet run orientation/facing checks (`longest_edge()` is imported and available,
not yet applied at national scale). Both are natural next refinements, not blockers for S5/S6.

## 9. THE NATIONAL FOOTPRINT UI — done 2026-08-23

A new card, "The national footprint," on the pick stage (the front page), below the existing 3-5
site map — all 422 registry entries as real map points, never mixed into the existing site picker
(which stays focused on the sites with a full agent run).

**Encoding, per the project's own dataviz method:** colour = STATUS (`has_field` good-green /
`attempted_empty` warning-amber / `not_yet_attempted` muted-grey) — using this project's already-
defined, colourblind-validated status palette, never re-themed. Category (cluster/pair/single)
rides on marker RADIUS instead, so the two dimensions never compete for one colour channel.
Rendered as a GeoJSON circle layer, not 422 DOM markers, for the same reason a spreadsheet doesn't
render as 422 separate `<div>`s.

**Fed by `src/export_national_sites.py`** (new, free), which joins three files — the registry, the
ranked purchase plan, and the live purchase ledger — because none of the three alone can answer
"does this real location have a real field." Wired into `run_all.py` as step 17 of 22, so it
regenerates on every rebuild and never goes stale relative to the ledger.

**Two real defects caught before shipping, neither by eye:**
- A join defect: oversized clusters split into multiple tile purchases were silently losing all
  but the last tile's status (a dict overwrite, same failure *shape* as the packer's earlier
  key-collision bug — measured 26 references, 25 surviving, before the fix).
- An invented `format()` helper call that doesn't exist in this codebase (the real one is `int()`).

**Verified:** `node --check` on the extracted script (0 errors), `audit.py` 95/95 including the
duplicate-element-id guard, a full `run_all.py` pass (REBUILD COMPLETE), and an actual screenshot
in both themes — light mode showed the map, markers, legend and computed stat line all rendering
correctly; a rapid dark-mode re-test hit OpenStreetMap's public tile server's rate limiting (proven
by re-testing light mode immediately after and getting the same blank tiles) — a shared, disclosed
limitation of the ORIGINAL map too, not a defect in the new one. Legend and text colours were
confirmed correct in dark mode regardless.

### 6.1 Ordering constraint that matters

**S7 is the only paid stage and the only one with a daily cap, so it is the critical path.** It also
cannot start until S3 says which AOIs to buy. Every free stage should therefore run *ahead* of it,
so that when a day's 30 calls land there is somewhere for them to go.

⚠ **Do not buy a field for a cluster that has not passed G2/G3.** A call spent on a cluster with no
valid pair is 4,220 credits bought for a site that can never ship — and at 30/day, a wasted call is
a wasted *slot*, which is the scarce thing.

---

## 7. WHAT MUST NOT HAPPEN — the failure modes this project has already committed

1. **One site's value shown for another.** Four instances (#98, #132, #133, #142). At 3 sites these
   were found by eye. **At 150 sites nobody will see them** — so `check_sites_actually_differ` and
   `check_panels_are_per_site` must scale to N sites, and the per-site sweep method from §10's
   per-site sweep ("flatten every leaf to a JSON pointer and list every pointer that AGREES across
   sites") is the tool that found four defects in twenty minutes. **Run it at N.**
2. **A number in prose that no check re-reads.** §8.2, five instances. At national scale the
   temptation is a headline like "N sites, X h/yr saved". **Register it or do not write it.**
3. **Claiming a data centre that is not there.** OSM tagging is crowd-sourced. A cluster is evidence
   that *tagged* halls exist; the imagery verdict is what confirms one is real and built.
4. **A skipped gate reported as a pass.** #74. If imagery is unavailable for a site, that site is
   **not screened**, not "screened, assumed fine".
5. **Padding the count OR manufacturing refusals to look rigorous.** Neither is what the user asked
   for. §0 corrected the reading that the pipeline refuses heavily — it does not; every metro tried
   has found a clean pair, and §0.2 turned "no nearby neighbour" from an exclusion into a real,
   shippable, favourable finding. **The two genuine refusals (rooftop, unbuilt) stay rare, on real
   evidence, and that rarity is now measured, not assumed.** A national build that includes the
   large majority of real, tagged data centres — standalone and paired alike — while refusing only
   the handful that are physically not what they claim to be, is the stronger and the honest result.

---

## 8. OPEN QUESTIONS — carry these forward

- **Weather at national scale.** Every site needs an ASOS station ≥95 % complete. Iowa State
  rate-limits and 503s (#13), and each station is 60 month-chunks. Sites genuinely near the same
  station legitimately share it — Ashburn and Dulles already do, and it is a deliberate control.
  **Sharing a station is physically correct; sharing geometry, imagery, a tile or a plume is not.**
- **Aerial imagery format.** 2.5 MB PNG × 150 sites = 375 MB. JPEG at ~300 KB keeps the evidence and
  fits. Screening frames are photographs, so JPEG loss is acceptable — **but the annotated overlay
  must stay legible**, and that should be checked on a real frame before converting all of them.
- **GPU time.** 576 solves per site. Rise table is 5–9 s, but `export_plume_fields` is ~2.3 min/site
  — 150 sites is ~6 h. It is already outside `run_all` for this reason.
- **Does every site need 72 solved plume fields shipped?** 1.1 MB each. Likely reduce to the
  critical bearing plus a coarse set for non-reference sites, with the reference sites keeping all
  72. **Not yet decided.**
