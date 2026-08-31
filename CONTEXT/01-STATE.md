<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 01 - State

What is true **right now**. The figures below are generated from the shipped artefacts; the prose is
maintained by hand. Newest change first, always.

---

## 0. Resume here

**This is the first thing to read after a restart or a compaction.** Maintained by hand; it is the
only section describing work IN FLIGHT rather than work finished.

### THE FILL TARGET WAS MEASURED ACROSS ALL 250, AND THE REMAINING OUTLIERS ARE THE 12 WE DO NOT SELL. 2026-08-31

The user: "Only fix any report issues, leave the API usage for now." This closes the fill item, and
the closing measurement is the point of the entry.

🔴 **MY FIRST TWO ATTEMPTS AT MEASURING FILL BOTH LIED, IN OPPOSITE DIRECTIONS.** The first proxy took
the lowest ink on the page and returned **98.9 % for all 249 files, identically**: every page carries a
running footer, so "lowest ink" is the footer on every page and the metric could not see content at
all. A number that is the same to one decimal on 249 different documents is not a measurement, it is a
constant, and that is the tell. The second used `check_report.py`'s frame (header 30 pt, footer 10 pt
excluded) and reported **192 of 250 with a page under 85 %**, which is true and useless, because it
counts each document's FINAL page. No report, book or paper fills its last page; a fill floor applied
there is a wrong requirement whose only remedy is padding.

**THE HONEST NUMBER IS BODY PAGES, MEANING EVERY PAGE EXCEPT EACH DOCUMENT'S LAST: 14 THIN OF 1,835,
0.76 %.** Mean body fill 96.2 %, lowest 71.9 %, and **0 overflows past the right margin** across all
2,085 pages. Final pages average 85.1 %, which is what a closing page should look like. Before this
work the same metric found 230 of 250 with a thin page and three final pages at 3 %.

⚠ **ALL 12 OF THE THIN-PAGE SITES THAT ARE ALSO WITHHELD ARE THE SAME 12 SITES, EXACTLY.** Measured:
12 of the 14 thin-body reports are precisely the 12 sites with `pays == False`, and 0 withheld sites
are clean. That is causal, not coincidence: a site where the agent LOSES to the incumbent produces
more distinct block reasons in the appendix, each reason group takes a heading, and the headings push
the 24-row schedule table down. Nobody reaching a report from the offer path ever opens one of them.
On the 238 sites actually offered there are **2** thin body pages.

**AND THOSE 2 ARE NOT DEFECTS EITHER.** `NE_way_405034584` and `TX_way_1457383500` have NO satellite
imagery, so their page 2 carries contents plus prose and no figure, ending with 198.6 pt free. The
next section opens with the 470 pt bound chart, which cannot fit in 198.6 pt. Same shape as page 5 on
every site, which sits at 83.8 % to 85.9 % because the next thing is an h1 plus a 340 pt coverage
chart, one indivisible ~360 pt unit against 99 pt of room. A section starting a fresh page because its
opening figure does not fit is correct typesetting, and forcing it would mean shrinking the charts.

⚠ **THE 3 TEN-PAGE REPORTS ARE DIAGNOSED AND DELIBERATELY NOT FIXED.** `CA_way_58708529`,
`OH_way_1386016635`, `OR_way_697415321`. Cause, measured against Ashburn page by page: all four
documents are identical through page 7; Ashburn's appendix has 4 reason groups so 9 schedule rows fit
on page 8 and 15 land on page 9, leaving room for the ~115 pt closing pair. CA has **5** groups, so 3
rows fit on page 8 and **21** land on page 9, and the closing pair is evicted to a tenth sheet at
17.6 %. Recovering it needs ~44 pt, i.e. cutting the schedule row pitch from 20 pt to 18 pt in **all
250 documents** to buy back three final pages, two of which belong to offered sites. Not taken: that
reflows every report against a vertical-rhythm requirement it currently satisfies. The colophon is
already bound to the caveat, which is what turned a 3-line orphan at 6 % into a closing page at 17.6 %.

**THE DEMO SCRIPT IS WRITTEN AND ITS OWN LENGTH IS MEASURED, NOT ESTIMATED.** `DEMO-SCRIPT-2m50.md`:
430 spoken words, 2:52 at 150 words a minute, 2:57 with the site's own intro bed, against the user's
3:00 ceiling. 🔴 My first draft was **732 words, 4:52** and its section seams were em dashes, so the
file broke standing rule on the first pass; the length is now enforced by counting the blockquote
lines rather than by feel.

🔴 **TWO CITATIONS IN MY OWN FIGURE TABLE WERE WRONG, AND VERIFYING THE SCRIPT IS WHAT CAUGHT THEM.**
65.6 % is `trace.json` `cycle.pooled_coverage`, NOT `cycle.bound_day_level`, which holds only n = 4,
`attainable` 0.8 and `n_needed_for_nominal` 9. The 13,435 free hours and 7 unsafe are
`rolling.json` `configs[0].executed_free_h` / `executed_breach_h` / `breach_per_1000_free_h`, NOT
`backtest.json`. Every other figure re-read clean: 238 offerable, 637 mapped, 97 stations, 4,188,290
weather hours, 92,988 h/yr, $42.4M to $84.8M, 60.3 m, AWS IAD116/IAD117, 576 solves over 72 bearings
in 5.34 s on GPU (NVIDIA Warp), 913 held-out days, 43,763 h over 1,826 d, and 90.0 % over 43,260
rounds from `backtest.json` `aci.3.ACI.realised_coverage` = 0.89977.

⚠ **ONE LINE THE USER ASKED FOR IS NOT SAYABLE AND WAS REWRITTEN.** They wanted "once the 9 days are
provided the agent will report 90 % confidence every time". `KpiCards.tsx` warns against exactly that
sentence: *"before 90 % is reachable at all", NOT "and then it hits 90 %". Reaching n = 9 is necessary
and not sufficient.* Section 9 now claims the 90 % where it IS measured, on the five-year record, and
describes nine days as what makes the live figure reachable. Stronger and true.

### THE LIVE REPORT IS THE TYPESET DOCUMENT NOW, AND THE FALLBACK IS WHAT MADE IT SAFE. 2026-08-31

The user: "make sure that the format you used for automatic pdf generation in replay mode also holds
true for the live agent run ... the necessary changes would be made per site for the specific outputs
the agent derives regarding cooling mode in those live forecasting."

**`site_report_live.py` IS A DIFFERENT DOCUMENT, NOT A MODE OF THE REPLAY ONE**, and that was the
first design decision. `site_report_data.collect()` reads COMMITTED artefacts; every figure in them
describes a build-time configuration over five years. Reusing it under a live heading would put
backtest figures beside forecast hours as though this run produced them, which is the confusion the
monospaced live report was written to prevent and says so on its own first page. This module reads
the JOB and nothing else. Three pages: the run's identity and hour-by-hour strip, the bound across
the horizon plus the per-hour reasoning, then every hour, the margin disclosure and the config.

🔴 **TWO OF THE REPLAY REPORT'S BEST CHARTS ARE FORBIDDEN HERE, not unavailable.** `bound_vs_actual`'s
strongest series is "what the intake actually did", measured after the fact; a live run is a forecast
and has no actual, so substituting anything would be a caption the chart refutes.
`margin_decomposition` splits the margin two ways and `live.py` computes ONE scalar day-level margin,
identical in every hour, so a two-part bar would invent a decomposition. `live_strip` and
`live_horizon` replace them, in the same module so there is one palette and one type scale. The strip
has FIVE states because a live run can fail in ways a replay cannot: no forecast for an hour, and a
refused wind bearing. Both are visible because both changed what the agent was able to say.

⚠ **`verify_live`'s THREE TEXT CHECKS WERE KEPT, NOT LOOSENED.** It greps for "LIVE RUN REPORT" and
"the reasoning, hour by hour" and scans for bare nan/None tokens, and `serve_live.py` turns any
problem into an HTTP 500 that a download anchor writes to disk as a .json: the 2026-08-30 fault
exactly. Those are good content requirements, so the document satisfies them. Result: **0 problems**,
and `verify_live_report_button.py` passes 25/25 serving 56,470 bytes through the real route.

🔴 **THE GEOMETRY CHECK HAD TO BE REBUILT, AND MY FIRST VERSION LIED.** `report.Pdf.overflows()` is
the only library-free check `verify_live` has, and the ReportLab path has no equivalent; dropping the
key would have undone the 2026-08-30 fix from the other direction, invisibly, because the self-test's
negative control plants the key itself. So it is rebuilt on pypdf, already a deploy dependency, from
the finished bytes. ⚠ The first version read `tm[4]` as a page coordinate and reported SIX overflows
on `demo/report.pdf`, which PyMuPDF measures clean at max x 547.1: text inside a scaled Drawing
carries its x in the Drawing's space. Composing with the CTM gives 527.1 for the same string. It now
has a negative control, because the first control tested nothing: ReportLab silently refused the
over-wide table it planted, so a string is drawn at x = 700 instead and must be caught.

🔴 **THE FALLBACK HID A DEFECT, WHICH IS THE MOST IMPORTANT THING FOUND HERE.** `build_live` degrades
to the monospaced report when the typeset one raises, so a missing dependency cannot take down a
feature that is permanent by standing rule C1. It also means a bug in the typeset document shows up
as a plainer PDF and nothing else. MEASURED: `live_horizon`'s legend was 9 px too wide on any run
containing a no-forecast hour, its own assertion fired, `build_live` caught it, and the self-test
printed ALL PASS while building 9,858 bytes of monospaced PDF in place of 55,000 of typeset. The
fallback worked perfectly and concealed the failure. Both live legends now WRAP rather than assert,
and the self-test **fails** if the typeset path falls back where reportlab can be imported.

⚠ **A SHARED FUNCTION DOES NOT CHANGE TO SUIT ONE CALLER.** Adding degree signs to
`live_report.reason_for` broke the monospaced report: `report.py` wraps against base-14 Helvetica and
renders "°" as the four characters " deg", so five lines ran up to 46.2 pt past the right margin and
`verify_live` correctly refused the document, including on the no-pypdf path. Reverted;
`site_report_live._degrees` upgrades the units, trims 4 decimals to 3 and turns "240 deg" into "240°"
on the way in, for the one reader that can render them.

**THREE FACTS THE LIVE PATH CARRIES THAT NOTHING WAS READING.**
* `horizon_h` is the REQUESTED horizon and is never rewritten after truncation: `demo/live.json` says
  12 while carrying 4 hours. The document counts `len(hours)` and states the difference outright.
* `dewpoint_c` holds FortyGuard's WET-BULB where FortyGuard supplied one and NWS's dew point
  otherwise, discriminated by `humidity_source_per_hour`. Wet-bulb is the stricter test, so the
  monospaced report's "DEW PT" column understates what the gate did. The typeset column heading is
  derived per run: "wet-bulb", "dew point", or both.
* `margin_provenance` carries the bound's own limits (4 pairs, 9 needed, an 80 % arithmetic ceiling,
  65.6 % measured, clamped, and the extrapolation) and was being dumped as flat key/value rows capped
  at 26. It is now a table with a sentence per row.

⚠ **THE FREE PLAN, MEASURED AGAINST THE ACTUAL LIMITS** (0.1 CPU, 512 MB RAM, no persistent disk).
requirements.txt now asks for reportlab and svglib; matplotlib stays out, which is most of the weight.
Disk closure **33.8 MB** measured from the installed distributions, against the "roughly 60 MB" this
repo estimated for all four. RAM: the new imports cost **+10.5 MB**, a build peaks about 18 MB
transient, six builds in one process reached 78 MB, which is **15 % of 512** and shows no leak. Time:
0.13 s warm and 0.64 s cold, so roughly 1.3 s to 6.4 s on a tenth of a core. No persistent disk means
the document is built to a BytesIO and both charts are SVG strings: none of the replay report's three
file-writing figures is used. ⚠ And the logo cache falls back to the FULL-SIZE mark rather than to no
mark when the directory is unwritable: blocking the write produced a 41,864 byte PDF with no logo on
any page before the fix, and 105,041 bytes with one after.

`audit.py` 2115 passed, the same 5 pre-existing spend failures and no new ones.

### 250 OFFERED BECAME 238, AND THE CHART HAD NEVER PLOTTED THE 12 IT CLAIMED TO. 2026-08-31

The user: "we remove all those sites which show negative prices in the tiles ... let them stay on map
but include them in the category of grey dots", and for the wording, "the agent covers 238 sites; 12
more were measured and excluded because the agent's own constraints made it worse than the incumbent
there, and we don't sell those without deep dive engineering on it."

**THE GATE IS THE MEASUREMENT, NOT A LIST.** `metros.py` gains `measured_gain_h(k)`, reading the same
field the report's distribution plots: the last anchored rung of the `C ` ladder in each site's own
`*_backtest.json`. `offerable` becomes `data_ready and artefacts_built and pays`, where
`pays = gain is None or gain > 0`. MEASURED: **12 of 250** are negative, worst
`IL_way_1219083554` at **-3,649 h/yr, -183 % runtime, -$16.5 M**. At those sites the agent runs the
chillers MORE than the reactive controller it replaces. ⚠ `data_ready` deliberately stays TRUE: they
keep their artefacts, stay in the distribution and are still rebuilt by the chain. Only the OFFER
changes, which is what `offerable` has always meant. A hardcoded set of twelve keys would be correct
exactly once; a site that tips positive is now offered without anyone remembering to look.

🔴 **AND THE GATE EXPOSED A FALSE CAPTION THAT HAD BEEN SHIPPING.** The scale page said those sites
"are in the chart rather than filtered out of it: publishing them is what makes the rest of the
distribution worth reading". The chart's own code was `pos = g[g >= 0]` then `ax.hist(pos, ...)`.
**They were never in it.** The claim was the exact opposite of the code, in the paragraph carrying the
page's credibility argument, and the rewrite nearly repeated it. Plotting them is not the fix either:
an axis reaching -3,649 compresses the useful 250-to-850 range into a sixth of the frame. So the
caller now passes only the offered rows, the title counts what it plots, the excluded are described
in words with their worst value, and `portfolio_hist` **asserts** it was given no negatives, so the
silent filter cannot come back and let a caption speak for it.

⚠ **THE MARKER WOULD HAVE SQUASHED TWELVE REPORTS.** `this_site_gain` draws an `axvline`, and
matplotlib extends an axis to include one, so each withheld site's OWN report would have shown the
distribution crushed to the right to make room for its own rule. The rule is now omitted when the
value is off scale and the NOTE is not: "this site -3649 h/yr, off the scale to the left". Skipping
both, which the first attempt did, removed the single most important number on that page.

**THREE PLACES SAID THE SAME FALSE THING ABOUT THE GREY DOTS.** The map legend, the map popup and the
selected-site bar all read "no agent run published yet" for every non-offered facility. True of the
389 candidates with no artefacts, false of these 12, which have a run and a five-year measurement.
`artefacts.ts` gains `readiness()` returning `ready | measured-negative | no-run` from the `pays`
flag now published per site, and each surface says which. ⚠ Same grey dot, different sentence: a
fourth colour would imply a fourth kind of thing, and both are "not offered".

**THE AGGREGATE MOVED A LONG WAY, SO THE ARTEFACT SAYS WHAT WAS REMOVED.** Re-summing over the
offered set: `usd_lo` **-25,416,432 to +34,412,699**, `cut_pct` 6.19 to 9.73, `gain_h_per_year`
61,864 to 92,988. ⚠ And `sites_losing` became **0 by construction**, which would read as "no site
ever loses". `portfolio_totals.py` now also publishes `sites_withheld` and `sites_built`, and the
landing card's "238 of 238 sites gain" tautology became "all 238 gain and are in the total above; 12
more were measured and excluded". Still no word implying those sites FAILED, which the user ruled out
earlier and which would be wrong anyway: the measurement is of the agent at that geometry.

⚠ **THE HALO COUNT WAS A DERIVED QUANTITY PINNED AS A CONSTANT.** `verify_app_deterministic.py`
asserted 637 dots / 246 halos. Dots are a registry fact and fairly a constant; halos are the OFFERED
count, a join between `unified_sites.json` and `sites.json`. It now computes both the way the app
does. MEASURED, the drop is **10, not 12**: two of the twelve excluded keys have no unified facility
pointing at them and were never drawn. Anyone updating the constant by hand would have written 234.

**THE CROSS-CHECK, ASKED FOR AND THEREFORE DONE PROPERLY.** The user: "have you cross checked the new
aggregates all over the project attributes including the text rendered on website". Sampling three
matches and inferring would not have answered it, so the RENDERED text was read:
* `verify_app_deterministic.py` harvested `.num` only, which is the per-site KPI plate. The portfolio
  aggregates use `.aa-bubble-num` and `.aa-bubble-foot` and were **unwatched**, which is how a figure
  that moves by tens of millions gets missed. Both are now harvested, compared across renders and
  printed. As rendered: **238**, **$42.4M to $84.8M**, **+92,988**, and the footnote "all 238 sites
  gain free-cooling hours and are in the total above; 12 more were measured and excluded". Reconciled
  against `portfolio.json`: `usd_mid_lo` 42,409,817 and `usd_mid_hi` 84,813,589. They agree.
* The CANONICAL single-file page reads **no** portfolio aggregate at all: `portfolio.json`,
  `sites_summed`, `usd_lo` and `sites_offerable` occur zero times in it. Its three hits for 250, 246
  and 245 are all inside `/* */` comments. Nothing stale is rendered there.
* A bounded sweep of every .html, .ts, .tsx, .py and .md found the remaining hits to be comments and
  docstrings, and **eleven of them contradicted the code beside them** after the change: the
  ScopeBubble header still described summing 250, the artefacts.ts `Portfolio` doc still said "all 250
  shipped sites", and one block explained a sentence the same commit had replaced. Updated, because a
  comment that describes the previous behaviour is worse than none.

README's three derived figures follow (238 offerable, 233 single-source, 2120 checks) and `audit.py`
passes them. ⚠ Five audit failures remain and are NOT from this work: they are API-spend ledger drift
in `API-USAGE.md` and `CONTEXT/HANDOFF.md` from live runs in earlier sessions. Neither file has a
diff this session, and the ledger last changed in 52b1f79.

### ASHBURN ANNOUNCED THAT ASHBURN HAD NO AGENT RUN, FROM THE SECOND OF TWO CALL SITES. 2026-08-31

The user, on the first screen: "the picture shows this pop up appearing for the default site ashburn
which is selected automatically when the page opens up although ashburn does have agent run on it".

🔴 **THE TWO-KEY-SPACE BUG, FIXED ONCE AND ONLY ONCE.** `App.tsx` already carried a long comment
explaining it: the map and the search bar address facilities by the UNIFIED key `metro_ashburn`,
sites.json owns the artefacts under the METRO key `ashburn`, and `loadHeadline` handed the former
finds nothing, falls back to the shipped reference and returns `isFallback: true`. `headlineKey` was
added to do the join. But `loadHeadline` had **two** call sites, and the mount effect still passed
`filters.facility` raw. So the notice fired for the one site that ships a complete run.

⚠ Being redundant, it also RACED: both paths fetch the same three artefacts and call `setH`, so which
verdict survived depended on which fetch resolved last. The mount effect now loads artefacts and
nothing else, leaving one owner of the headline figures.

🔴 **AND THE CHECK THAT WOULD HAVE CAUGHT IT DID NOT EXIST, IN EITHER DIRECTION.** Nothing asserted
on the banner, which is why the same fault reached a screenshot twice.
`verify_app_deterministic.py` now harvests `.aa-fallback` and asserts BOTH halves:
* absent on the default load, where it is false;
* **still present** for a mapped candidate that really has no run, read from the registry rather than
  hardcoded. ⚠ THIS HALF IS THE IMPORTANT ONE. Asserting absence alone is satisfied by deleting the
  feature, and the notice is load-bearing for the 389 mapped candidates with no artefacts: it is what
  stops another site's figures being read as theirs.

⚠ **AND THE CONTROL FAILED FOR ITS OWN REASONS FIRST, WHICH IS WORSE THAN NO CONTROL.** Placed after
the comparison loop it captured `_det.html` **after the `finally` that deletes it**, harvested a 404,
and accused a correct fix of having removed the feature. It now captures alongside renders a and b,
inside the same `try`. A measuring device that reports a failure it caused itself spends the
credibility of the one signal it exists to give.

### THE REPORT NOW BUILDS FOR EVERY SITE, AND TWO THIRDS OF THEM HAVE NO PLUME. 2026-08-31

Three corrections and the rollout. The user: "NVIDIA (Warp) is exceeding the border ... The
fortyguard logo is completely embedded into the header line ... yes, go ahead and wire it into the
chain", and for the 168 single-building sites, "just say that it is a singular site, so plume physics
doesnt hold here ... then skip the plume physics related pages from the pdf and the content page."

🔴 **THE CELL THAT ESCAPED ITS COLUMN WAS A CHARACTER-COUNT HEURISTIC, AND FIXING IT BROKE A NUMBER.**
`_table` wrapped a cell in a Paragraph when `len(cell) > 24`. "GPU (NVIDIA Warp)" is 17 characters and
88 pt wide against 74.5 pt of usable column, so it stayed a raw string, and a raw string in a
ReportLab cell neither wraps nor clips: it paints straight out. Character count is not width.

Measuring every cell with `stringWidth` fixed that one and **broke the schedule table**: the "safe"
column is 32 pt, leaving 18 pt against 19.4 pt of the word "safe", so the header became a Paragraph in
a column too narrow to hold it and split mid-word as "saf" over "e". The hour column did the same to
"22", printing "2" over "2". ⚠ A Paragraph only helps where there is a space to break AT. So columns
are now widened to their **widest unbreakable token** first, taking the surplus from whichever column
has slack, and only then is anything wrapped. Two assertions: no raw cell wider than its column, and
no column narrower than its narrowest possible content. Tables also gained a light outer BOX, so the
bounds a cell must stay inside are visible on the page.

🔴 **THE LOGO WAS WELDED TO THE HEADER RULE BECAUSE THE RULE CROSSED IT.** MEASURED: the mark is
25.9 pt tall drawn 74 pt wide, its bottom edge sat at `top - 23.9`, and the rule was at `top - 16`, so
the line passed 8 pt above the mark's own baseline, through the wordmark's descender. The mark and the
running head now lift into the margin's own white, which the header was using only the bottom 16 pt
of. ⚠ Raising `HEADER_H` instead would have cost every page 12 pt of frame, and two pages are at 99 %.

🔴 **AND THE ROW SAID WIND FROM 0 m/s WHEN THE SLOWEST SPEED IS 0.5.** `_n` is "a whole number with
thousands separators", correct for hours and dollars, and `_n(0.5)` is `"0"`. The sweep does not
include dead calm and must not claim to: the plume model needs air movement to advect anything.
`_sp` keeps the decimal.

**168 OF 249 SITES HAVE ONE BUILDING, AND THE GENERATOR HAD NEVER RUN ON ONE.** `build_standalone_site.py`
writes `receptor_ring_m: null`, `intake_m: null`, `facade_gap_m: null`, and the solver records
`n_solves: 0`. Reading `geom["receptor_ring_m"]` raised on every one of them.
* `collect()` now returns `standalone`, derived from `facade_gap_m` and **cross-checked** against
  `n_solves` from a different file, so a drift between the two build paths fails the build.
* The physics section is dropped from the document AND from the contents, per the user's wording, and
  the site page says why: "the plume physics does not apply here, so the section on it is absent from
  this document rather than present and empty."
* The aerial draws one footprint, in BLUE not orange, because with no neighbour the building is purely
  the thing being protected. No gap segment, no intake ring, and the legend and caption follow.
* `_worked` loses its rise clause: a rise of exactly 0 is not "a plume rise under 0.01 °C", which is
  true arithmetic and a false description. The margin chart drops the plume legend entry rather than
  naming a series with no height.

⚠ **AND FIVE SITES HAVE NO SCREENING FRAME AT ALL.** The site section was entirely inside
`if aer is not None`, so those five got one apologetic sentence and a page 55 % empty. Whether an
imagery vendor covers a site is a fact about the vendor, not about the site, so the prose is built
either way and only the LAYOUT branches. The contents row has four variants, keyed on
(standalone, has_imagery), because promising "what the imagery can and cannot show" beside a section
with no imagery is a lie on the first page a reader reads.

🔴 **TWO FAULTS THAT WOULD HAVE HIT ALL 249 THE MOMENT THE CHAIN DROVE IT.** `build_sites.py` passes
the site in the METRO environment variable and no argument.
* `M.demo_path("sites.json")` key-prefixes, so under `METRO=AL_way_1540172608` the one global manifest
  resolved to `AL_way_1540172608_sites.json` and raised FileNotFoundError. `audit.py` lists sites.json
  in its own `GLOBAL_OK` and reads it straight from DEMO; this now does the same.
* The output path fell back to `DEFAULT_METRO` when `site_key` was None, which it is on every chain
  invocation. All 249 sites would have written over ashburn's `demo/report.pdf`, last one winning.

**WIRED IN, IN BOTH PLACES, AND THE SECOND ONE WAS THE DANGEROUS ONE.** `build_sites.py`'s chain step
"downloadable PDF report" is `site_report.py` rather than `report.py`. So is `run_all.py` step 74,
which writes `demo/report.pdf`: left pointing at the old generator it would have overwritten the
typeset report with the monospaced one on every single run_all, silently reverting the whole rebuild
for anyone who ran the pipeline after building the site. `report.py` stays in the tree because `live_report.py` imports it. ⚠ The step needs
`requirements-build.txt`, which the deploy image deliberately does not carry, and that is correct: the
PDFs are built here and committed because `serve_live.py` promises that serving `demo/` as static
files gives the whole replay demo. Generating on click would work on Render and 404 on GitHub Pages.

⚠ **THE TWO IMAGE WEIGHTS, BOTH THE SAME MISTAKE.** `/Image` was 405 KB of a 472 KB file. The logo was
embedded at 2362 px for a 74 pt placement, and the `Doc` docstring PRAISED it: "renders at 2,298 dpi
against a 300 dpi print threshold". Pre-scaled and cached, 12 KB. The aerial at 300 dpi resolved
0.303 m per pixel against source imagery of 0.2276: finer than the thing it reproduces. At 200 dpi,
149 KB. **472 KB to 268 KB.**

Verified on all three shapes: paired with imagery 9 pages mean 94.2 %, standalone with imagery 8 pages
mean 95.7 %, standalone with none 8 pages mean 91.6 %. Zero label overlaps, zero lines through text and
zero unit-spacing violations on every one.

### A DOCUMENT IN WHICH `<b>` HAD NEVER ONCE WORKED, AND FOUR PAGES THAT WERE MOSTLY PAPER. 2026-08-31

The layout brief on `REPORT-REBUILD-v3-ashburn.pdf`, ten numbered items, plus one named defect: "dont
make 'dry-bulb' go inside the graph ... write it properly before the graph margin the way 'budget' is
written." The named defect took four lines. Two of the things found on the way took the rest.

🔴 **EVERY BOLD RUN IN THE DOCUMENT WAS RENDERING AS BODY WEIGHT, AND HAD BEEN ALL ALONG.**
MEASURED: 16,379 characters of `Inter-Regular` against 945 of `Inter-SemiBold`, and all 945 came from
styles that name a face directly, such as a heading or a tile value. All **37** `<b>` runs in the prose
did nothing. `register()` called `pdfmetrics.registerFont` for three faces, which tells ReportLab the
fonts EXIST, and never called `registerFontFamily`, which is what tells it which face `<b>` means. A
`Paragraph` then resolves bold against a family that is not registered and silently falls back.

⚠ **AND THE FIX ONLY WORKS AFTER svglib, WHICH IS THE WHOLE OF IT.** Called before
`svglib.fonts.register_font`, the registration was measurably undone: `tt2ps("Inter", 1, 0)` still
returned `"Inter"`. svglib registers with ReportLab too and rewrites the family map on its way past.
Two registries, one clobbering the other, no error from either. There is now an assertion on
`tt2ps` in `register()`, so this cannot regress quietly.

🔴 **THE PAGE FILL WAS NOT A PAGINATION PROBLEM, AND THE FIRST FIX FOR IT CHANGED NOTHING.** Five of
nine pages sat under the brief's 85 % floor, one at 60 %. Making the five middle section breaks
conditional was the obvious move and it moved nothing: every section ends with 150 to 225 pt of a
705 pt page unused, and a section needs about 300 pt to start, because its first chart is 230 pt or
more. No section could ever begin in the gap left by the one before it. The gap was a chart smaller
than its page, so the charts grew into it, page by measured page. **Mean fill 83.0 % to 95.5 %, and
no page now more than 12 % empty.** Two pages needed content rather than height:

* **Page 9, 60 % empty**, got the one measured thing the report was not using.
  `explanations.json` carries `would_flip_with_more_switches` per hour and nothing read it. All
  **12** switch-budget hours come free when the day is re-planned with the budget raised, which is
  the most commercially direct sentence in the document: the hours were held by a setting, not by the
  weather. ⚠ The flag means budget **+2**, not +1 (`explain.py:212`), and `explain.py:317` re-plans to
  re-check it, which is why it can be printed.
* **Page 5, 71 % empty**, could not be fixed by growing its chart at all: a polar plot is square, so
  in a 42 % column it can never exceed 209 pt however much height the page has. The dead paper under
  the circle now holds the solve's own specification, read from `rise_table_longest.json`.

🔴 **THE OVERLAP CHECK REPORTED ZERO WHILE THREE LABELS WERE BEING PRINTED THROUGH BY LINES.** It
compared text with text. The 90 % rule crossed "87.9%" on page 6, the portfolio marker crossed its own
"this site" note on page 7, and the runtime track ran under "Reactive incumbent" on page 3. All three
were obvious on the page. `check_report.py` now tests stroked paths against the middle 62 % of every
glyph box, ⚠ and understands a knockout: an opaque plate painted after the stroke is the standard fix
for a label on a rule and is not a collision, so paint order decides. Dropping the text-vs-text
threshold from 30 % of the smaller box to any real intersection took the count from 0 to 14 before it
came back to **0**, and one word arriving as two spans ("-400" as "-4" and "00") is now excluded.

**THE AERIAL FIGURE, AND THREE THINGS THE FIRST VERSION GOT WRONG.** Item 7 is the site's own ESRI
frame with the solver's geometry on it.
* Per-building registration, which the module previously argued for at length, is **wrong**. The error
  it corrected is **0.35 m**, not the 3 to 4 m assumed, and registering the two rings independently
  changes the separation between them, so the segment drawn as the facade gap would no longer be
  60.3 m. One transform, anchored at the domain centre, keeps the gap exact.
* The line drawn was **centre to centre**, 165.5 m, and would have been labelled 60.3 m. `facade_gap_m`
  is facade to facade (`audit.py:2289`). The module now recomputes the closest approach between the
  two rings and refuses to draw unless it reproduces the artefact, which it does to 0.02 m.
* The condenser bank was the **boldest object in the frame** and `build_site.py` records its position
  as "NOT mapped in OSM. Conservative worst case". Solid now means mapped, dashed means modelled, and
  the legend says which. ⚠ The frame is also resampled to square ground pixels: it covers 318.7 by
  321.1 m in a 1400x1050 raster, a 34 % vertical squash that made a 158 m hall look 118 m long.
* ⚠ MEASURED by edge-gradient search, one edge of each ring sits 10 to 20 m off the roofline, the two
  disagreeing in OPPOSITE directions, so it is neither the projection nor parallax: OSM and ESRI are
  surveyed independently. No number in the report comes from the picture, and the caption says so.

**THE REST OF THE TEN.** The named defect: under `rotate(-90)` a label grows UPWARD from its anchor,
so `text-anchor="end"` makes every reason hang DOWNWARD from one common top edge, and the band is
measured from the longest label rather than a constant that happened to fit "budget". Cell colour now
carries the reason, three treatments for this site's three states. Every hatch fill is gone, helper
included. Tile values **auto-fit** their column, which stops the class of bug that printed "43,763"
as "43,76" over "3". Secondary grey went from **41.7 %** of characters to 12.6 % excluding the running
furniture, which is reported separately because the same strip counted nine times is not nine reads.
Bold sentences went from **13 to 1**, and the one is the NVIDIA Warp claim. Tabular figures are baked
into the cmap, because ReportLab cannot apply `tnum` and Inter's digits vary from 833 to 1323 units.
The contents page is **measured, not maintained**: a two-pass build, `Mark` flowables recording where
each heading landed, and `SECTIONS` owning both the heading and its row, because the hand-written
version advertised three titles that no longer existed and omitted a whole section.

**THE PDFs WERE ALREADY AUTOMATIC, AND MY ROLLOUT QUESTION WAS FRAMED WRONGLY.** The user: "shouldnt
these pdfs be generated automatically when a site is clicked? why are we making them manually for
all". Nothing was ever hand-made: `build_sites.py:81` runs `report.py` per site as one step of its
chain, and the 249 committed `*_report.pdf` are build output. The open question is only whether to
swap `site_report.py` into that chain.

⚠ **AND GENERATING ON CLICK WOULD BREAK A DOCUMENTED GUARANTEE.** `serve_live.py:24` states that
GitHub Pages serving `demo/` as static files must give the REPLAY-only demo "with every panel and
every proof intact", `/api/*` simply 404ing. A PDF built by a Python route exists only where Python
runs, so on a static host the download button would 404. Render does run Python, so on-demand is
possible THERE, and that is the objection: it would make the two hosts behave differently, which is
the thing the split exists to prevent.

🔴 **BUT THE QUESTION FOUND TWO REAL SIZE DEFECTS, BOTH MINE AND BOTH THE SAME MISTAKE.** MEASURED,
`/Image` was 405 KB of the report's 472 KB.
* The logo was embedded at 2362 px for a 74 pt placement, and the `Doc` docstring PRAISED it:
  "renders at 2,298 dpi against a 300 dpi print threshold". True about quality, silent about cost.
  130 KB per copy, in a document that carries it on every page. Pre-scaled once to
  `reportassets/_logo.png` at what 300 dpi needs, cached on the source's size and mtime: **12 KB**,
  and indistinguishable at 420 dpi zoom.
* The aerial at 300 dpi resolved 0.303 m per pixel against source imagery of 0.2276 m per pixel:
  finer than the thing it was reproducing. 200 dpi gives 0.455 m per pixel, still rendering a 57 m
  hall 125 px wide. **275 KB to 149 KB.**

**472 KB to 268 KB**, determinism intact, sha256 `bce46170...`. A 250-site rollout would be 62 MB
rather than 115 MB, against a repository already tracking 920 MB, of which 763 MB is per-site JSON
and 108 MB is the aerial JPEGs themselves. ⚠ The logo regression in between was caught by
`check_report.py`, not by eye: `io` is not imported in `site_report.py`, the header's own
`except Exception` swallowed the `NameError` into the text fallback, and the harness reported the
logo missing from 8 of 9 pages.

⚠ **BYTE-DETERMINISM SURVIVED ALL OF IT**, including the second pass and the embedded JPEG: two
consecutive builds are identical, sha256 `be674aee...`. Verified with `tools/check_report.py`:
9 pages, mean fill 95.5 %, no page under 85 %, 0 text overlaps, 0 lines through text, 0 paragraphs
over the three-accent cap, 0 unit-spacing violations, no number past three decimals, contrast passing
for every ink at its role.

### "I COULD NOT CHECK IT" WAS BEING REPORTED AS "IT IS BROKEN", AND THAT COST THE LIVE PDF. 2026-08-30

The user, on the deployed site: "pdf is not downloading after live run ... The Live run report button is
setting up a .json file for download." Both halves were one fault, and the .json WAS the diagnosis.

🔴 **MEASURED FIRST, AGAINST THE DEPLOYED ORIGIN.** `GET /api/live/report/latest` returned **HTTP 500**
with `{"error": "the report failed its own verification", "problems": ["pypdf not available, so the
file was not read back"]}`. An anchor carrying `download` saves whatever comes back, so the browser
wrote the error body to disk as a file. Nothing was corrupt and nothing was mis-routed: `/api/health`
answered 200, `/app/api/...` rewrites to `/api/...` at `serve_live.py:437`, and the PDF was being built
correctly on every single request.

**The bug was a category error in one line.** `verify_live()` opened with
`try: import pypdf / except ImportError: return ["pypdf not available..."]`, and `serve_live.py`
treats a non-empty problems list as a refusal to serve. So a missing optional library was
indistinguishable from a broken document. `requirements.txt` ships numpy and psychrolib only, and that
file was DERIVED by walking the import graph reachable from `serve_live.py`: an import inside a `try`
reads as optional to that walk, which is defensible, and wrong here because the code path runs on the
server.

**Both halves fixed, because either alone leaves a hole.**
* `verify_live()` now separates the two states. A missing library records
  `meta["read_back"] = "skipped: ..."` and returns no problems, so the report is served. A file that
  cannot be REOPENED is still a problem, because that one really is broken.
* ⚠ **THE GEOMETRY CHECK MOVED ABOVE THE IMPORT.** `Pdf.overflows()` reads the writer's own
  placements rather than the finished file, so it needs no third-party library. It used to sit after
  the early return, which meant a host with no pypdf ran NO checks at all. Now a report whose text
  runs off the paper is refused even there.
* `pypdf>=4.0` is a declared dependency, so the read-back actually happens on the host that serves it.

🔴 **AND THE 25 GREEN CHECKS COULD NOT HAVE SEEN IT.** `verify_live_report_button.py` passes 25/25 and
did so throughout, because it runs where pypdf is installed. This is **5b.42 one layer further out**:
a harness that HAS the dependency cannot test the host that does not. `live_report.py selftest` now
blocks the `pypdf` import through `builtins.__import__` and requires that a real PDF still comes back,
that `read_back` records a skip rather than a failure, and that a planted overflow is still caught.

**TWO LIVE-REPORT BUTTONS BECAME ONE.** The user: "why are there two download report buttons for live
run. I only want one report in pdf format." `lib/tabs.ts` gives the `live` tab the selectors
`['#tapecard', '#livecard']`, so the engine's `#livereport` anchor renders on the same screen as
`AgentConsole`'s own. The React one was deleted and the engine's kept, on two counts that matter:
it links `api/live/report/<LIVEJOB>` with the job's **own** id where the React one linked
`.../latest`, which on a shared host is whichever visitor ran last, so a reader could have downloaded
a stranger's schedule; and its label already says PDF. `#livecard` is permanent by standing rule C1,
so the engine's button is the one guaranteed to still be there. The per-site report button beside it
is a DIFFERENT document, generated at build time for one named configuration, and stays.

**ON `[cached]`, WHICH IS NOT A DEFECT AND IS ASKED ABOUT EVERY TIME.** A heatmap response is
aggregated over the requested window, so an hourly trajectory costs one call per hour, and windows are
keyed by exact date and hour range under `data/live_cache/<metro>/`. Because the horizon SLIDES, a
re-run within the same hour block needs only the new far-end window: the reader's run showed 11 of 12
hours `[cached]` and one line reading "submitting 1 window to FortyGuard", which is the design working.
N-55 established that re-requesting an identical window returns **17,862 of 17,862 tiles byte-for-byte
identical, max delta 0.00000000 C**, so a cache hit is the same data rather than an approximation of
it. The label exists because this project will not present cached data as a fresh call. A fully
uncached 12-hour run costs 12 x 4,220 = **50,640 credits** and needs explicit direction under rule 8.

### THE PRIME SILENCED THE SEQUENCE IT EXISTED TO ENABLE, AND THE PDFs SIT ON A GRID NOW. 2026-08-30

The user, a second time: "I hear no voice altogether although the current version is deployed on
render after the fix." Both halves of that sentence were true, and together they ruled out the
obvious answer.

🔴 **THE DEPLOYED ARTEFACT WAS NOT STALE. THE FIX HAD A BUG.** A GET of the live origin returned the
inline script carrying `removeItem('aa-intro-audio-played')`, and both referenced assets hashed
identically to the local build (`sha256 45fc4d00...36b1ee`). So cause 1 above really was fixed and
really was live, and the silence was something else: **cause 2's own fix, biting back.**

`audio.unlock()` plays each element at volume 0 and pauses it again in the play promise's `.then`.
That callback is **asynchronous**, and the sequence does not wait for it. GSAP fires `playVoice()` on
the next animation frame. MEASURED on the deployed origin with a real pointer, **7 runs out of 7**:
unlock plays the voiceover at t=5036, `playVoice` plays it for real at t=5065, the prime's callback
lands at t=5078 and **pauses it 20 ms in**. The reader heard **8 ms of a 4,676 ms narration**. The
whoosh survived, because its turn does not come until +5.9 s, so about one second of whoosh was the
entire soundtrack. "I hear no voice altogether" was literally accurate.
The prime always loses that race: resolving a play promise takes longer than one frame, and a machine
with a real audio device loses it harder, because starting a real renderer takes longer than a null
sink. So the ordering cannot be relied on and the callback has to **ask**: `if (el.volume !== 0)
return`. The three real levels are 0.400, 0.120 and 0.320 and are set immediately before their own
`play()`, so a non-zero volume means the element is no longer the prime's to stop. Correct in both
orderings, and the whoosh is still primed and stopped every time.

🔴 **A RESOLVED `play()` PROMISE IS NOT A SOUND, AND THAT IS WHY THE CHECK MISSED IT.**
`verify_audio_unlock.py` counted promises. All three resolved green while all three elements were
already paused and rewound. It now samples `paused`, `muted` and `volume` on **every animation frame**
and requires a **floor of audible milliseconds** per file: voiceover 3,000, swell 3,000, whoosh 500.
NEGATIVE CONTROL, with the guard removed and everything else identical: voiceover **0 ms** and **3 ms**
on two loads, against **6,851 ms** and **6,866 ms** with it. The check fails on the bug it missed.
⚠ **DO NOT REWRITE THAT AS A `currentTime` ASSERTION.** This machine's Chrome has no audio output
device, so the media clock never advances: a fully-buffered voiceover playing correctly sits at
currentTime = 47 ms for as long as you watch it. `paused`, `muted` and `volume` are properties of the
element and stay truthful without a sound card. The probe also wraps `pause()` and records the caller
frame, printed only on failure; that one line is what turned "the sound is gone" into a file and a
line number.

⚠ **AND `aa-audio` IS RETIRED, RENAMED TO `aa-audio-choice`.** Cause 3 above made the mute toggle
one-way for a window, and making the control visible again does nothing for a reader already carrying
`off`. A new key name expires every trapped value exactly once. `verify_audio_unlock.py` seeds the OLD
key and requires all three cues anyway.

**TWO MORE WAYS THE INTRO COULD GO QUIET, BOTH FOUND WHILE MEASURING THE FIRST.**

⚠ **AN IMPATIENT SECOND CLICK SILENCED THE READER'S OWN INTRO.** Nothing visible happens in the first
moment after Initialize Arbiter is pressed, so a reader unsure the click registered presses again, and
`launch.ts` bound the undocumented escape hatch to `pointerdown` on the window. MEASURED on the
deployed origin: a real second click at +1.5 s cut the run from **6,927 ms to 2,060 ms**, and the
transition whoosh, whose turn does not come until +5.9 s, never played. There is a **600 ms grace
window** on the pointer route now: longer than any double click, far shorter than the sequence, so a
deliberate skip still works. The KEYBOARD route is deliberately not delayed, because pressing Escape
is unambiguous in a way that clicking twice is not.

⚠ **THE MUTE TOGGLE APPEARED WHERE THERE WAS NO SOUND TO MUTE.** Under 768 px, under
prefers-reduced-motion, and on a second visit in the same tab, the intro takes the no-gate path:
`playHeroEntrance(false, 'headline')`, no unlock, no cues, nothing audible at any point. The toggle
rendered there anyway, announced "Introduction sound: on", and did nothing when pressed. It is gated
on `flags.gate` now. This is the same class of fault as the one-way mute it was added to fix, pointing
the other way: a control reporting a state the page does not have.

**THE TWO PDFs SIT ON A CHARACTER GRID NOW.** The user: "table headings like bound limit actual margin
not in alignment with their respective columns and written slightly leftwards ... lines not sitting
right below each other." Both were exactly right, and everything below is whitespace and placement:
no number, no rounding and no agentic logic was touched, and the report is still byte-deterministic
(same JSON in, same sha256 out, confirmed twice).

* **The hour table's header was a hand-typed literal and its rows were a printf format**, and the two
  disagreed by exactly **two characters** on all four numeric columns. MEASURED from the rendered
  glyphs: each heading's right edge sat **11.28 pt** left of its own column's. `HOUR_ROW` is now one
  format for both. `"%7s" % ("%.3f" % v)` is byte-identical to `"%7.3f" % v`, so no printed value moved
  a digit.
* **`para()` indented every line EXCEPT the first**, so each paragraph's opening line hung 11.28 pt
  left of its own body: 31 paragraphs and 107 lines in one report. The default is now no indent, which
  also makes `para()` agree with `field()` on the same page.
* **Two definition lists faced each other 39.48 pt apart**, values at x=132.24 and x=171.72, because
  fourteen hand-padded string literals each carried their own idea of the column. One `LABEL_COL`, and
  every row goes through `field()`, which also wraps where a literal could only overflow.
* **The reasoning body sat at `MARGIN + 14`**, which is 2.4823 characters and therefore no column at
  all; it was off-grid at the old 8.2 pt too. It is `MARGIN + 2 * char_width(BODY_PT)` now, which also
  squares the block's right edge with the six divider rules it used to overhang by 2.72 pt.
* **`field()` could butt a label straight against its value**, and in the LIVE report it did:
  `Dewpoint limit c15.0` was on the page, because that label is 16 characters and the column was 16.
  A label that fills the column now gets its own space.
* **The live report's WIND column was 14 wide and its values reach 18** ("250 deg @ 12.3 m/s"), so any
  row with a bearing overflowed and shoved RISE, BOUND, DEW PT and MODE three columns right of their
  own headings while a dashed row stayed put. `LIVE_ROW` is one format at width 18; measured after,
  every field's right edge is identical across the header and all three rows.
* **The live report's Helvetica prose was wrapped on Courier's ruler.** MEASURED: lines ending at
  x=412.93 against rules running to 549.60, a column and a half of blank paper down every paragraph.
  ⚠ And it was not even conservative in the safe direction: "AVAST" is 30.82 pt in Helvetica against
  28.20 pt in Courier, so a line of capitals could already run off the paper. `text_width()` and
  `wrap_measured()` use the published Adobe core-font advances, embedded as a table of constants rather
  than a library call, because a third-party version number has no business inside the layout of a
  deterministic artefact.
* **`live_report.py` had no geometry check at all.** `Pdf.overflows()` measures every placement in its
  own face and `verify_live` now reports it. `report.py selftest` carries a negative control for it.

**NOT CHANGED, AND DELIBERATELY:** the leading is still not an integer multiple of `LEAD`, so the
baseline grid drifts about 2.5 pt down a page. Fixing it would move page breaks, which is a different
class of risk from a whitespace change, and the drift is invisible. **AND A PRE-EXISTING BLEMISH THE
MEASUREMENT SURFACED:** six of the 250 reports end on a page holding a single line. That is true
BEFORE this change as well as after (six sites either way, a different six), so it belongs to
`_room()`'s pagination and not to this work.

⚠ **THE COMMITTED PDFs WERE STALE AGAINST THE COMMITTED JSON**, which nearly cost an hour. Rebuilding
them changed 39 page counts, and none of it was the layout: the explanation prose in
`explanations.json` had moved on since those files were last written. Built from identical JSON, old
layout against new, across all 250 reports: **245 unchanged, 5 SHORTER, none longer.** Always isolate
the variable before believing a diff.

### THE INTRO WENT SILENT, AND THERE WERE THREE CAUSES, NOT ONE. 2026-08-30

The user: "i dont hear the music and the mp3 audio that triggers when the Initialise arbiter button
is clicked." All three causes were measured with a REAL pointer click and Chrome's real autoplay rule,
against `serve_live.py`, which is what production runs.

🔴 **1. I BROKE IT MYSELF, TWO COMMITS EARLIER.** `hasSeenSplash` and `aa-intro-audio-played` are both
sessionStorage keys and they describe ONE fact between them: the reader has already been through the
intro in this document. They expired together until the "a refresh comes home to the globe" change
began clearing the first and not the second. After that, **every reload in a tab was completely
silent**: the gate came back, the reader pressed Initialize Arbiter, and `playVoice()` returned 0 on
its first line because `alreadyPlayed()` was still true.
MEASURED, three consecutive loads with HEAD's exact behaviour: load 1 played the voiceover and the
swell, loads 2 and 3 made **zero** play() calls and sat at `paused vol0 t0` through all 13 samples of
a 6.9 s hold. ⚠ And the hold still ran FULL LENGTH, because `launch.ts` picks the short 1.5 s path
from `opts.audio` rather than from whether anything actually played: 6.9 s of silence, not 1.5.
Both keys are cleared together now, in the same pre-paint script, and `verify_launch.py` asserts the
two strings match, because the key name is necessarily typed twice (a pre-paint script cannot import
from the bundle).

🔴 **2. THE TRANSITION WHOOSH WAS REFUSED IN EVERY REAL BROWSER, ON EVERY LOAD, INCLUDING THE FIRST.**
Chrome's transient user activation lasts **five seconds** and the media unlock it grants is **per
element**. The voiceover fires at +34 ms and is inside the window; the whoosh fires at **+5,876 ms**
and is not. That offset is not a choice anyone made, it is where the crossfade lands on the whoosh's
low pad.
MEASURED: 8 refusals out of 8, `NotAllowedError: play() can only be initiated by a user gesture`, with
`navigator.userActivation` reading `{isActive: false, hasBeenActive: true}`. The boundary was measured
directly with five never-played elements on one click: **+4,812 ms played, +5,110 ms and beyond
refused**. And the unlock really is per element and permanent: an element played at +1,029 ms replayed
fine at +7,740 ms with activation long expired.
So `audio.unlock()` plays and immediately stops all three elements inside the click. ⚠ At **volume 0
rather than `muted`**: every element is already built at volume 0 so the prime is inaudible, and a
muted prime might not earn the unlock at all, because Blink grants it on the play request and a muted
element is allowed to play unconditionally.
⚠ **AND IT MUST NOT RUN WITH `?cinematic=off`**, which my first version did. That switch navigates
instantly and plays nothing, and `verify_launch.py` states that as "no audio at all". Caught within
minutes.

🔴 **3. A ONE-WAY MUTE, THE SAME SHAPE AS THE THEME BUG FIXED THE SAME DAY.** One press of the corner
toggle wrote `aa-audio = 'off'`, and the toggle was rendered only when `flags.audio` was true, which
that write makes false. MEASURED: after one press and a reload, `play()` calls 0, `<audio>` elements
constructed 0, mute button present **False**, and a sweep of every button and `[role=button]` for a
label matching sound, audio, mute or volume returned **nothing**. The only ways back were `?audio=on`
or clearing storage.
It is gated on the cinematic now, which is a fact about the page rather than about the reader's last
decision. ⚠ **EXCEPT FOR `?audio=off`**, which is deliberately still hidden: a URL parameter is a
per-load instruction from whoever opened the link, it expires with the URL, and a mute button on a
page that was told to be silent is a control that lies. `flags.audioOffByParam` is the new distinction.
The gate's own button also reads the LIVE choice now rather than the mount-time flag, so unmuting and
then pressing Initialize Arbiter no longer starts a run that had already decided to be silent.

**RULED OUT BY MEASUREMENT**, so nobody has to look again: the three mp3s are tracked, are in the
Docker image, and return 200 `audio/mpeg` from both servers at both `/audio/` and `/app/audio/`;
nothing is muted by default (`AUDIO_DEFAULT` is true and a fresh profile resolves to it); nothing is
muted retroactively by the `setMuted` effect; there is only one call to action; and `CHIME_URL`'s
missing `chime.wav` is inert because its only caller is a component nothing renders.

🔴 **WHY 71 GREEN CHECKS NEVER SAW ANY OF THIS.** `verify_launch.py` launches Chrome with
`--autoplay-policy=no-user-gesture-required` AND presses the button with `el.click()`, which carries
no user activation at all. Between them those two make every permission question unanswerable. The new
`testing/verify_audio_unlock.py` inverts both: the strict policy, a real `Input.dispatchMouseEvent`,
and every probe passing `user_gesture=False`, because a CDP evaluate with the default grants an
activation of its own and would hand the page the permission the check exists to measure.
⚠ `cdp.py`'s `goto()` and `poll()` were doing exactly that, and the first run of the new check
reported `isActive = True` before any click. They are reads and they no longer grant a gesture.

**`testing/verify_audio_unlock.py`, 17 checks:** all three cues on a fresh tab and again after a
reload, the whoosh's LATE attempt specifically, the marker clearing, and a mute control that is on
screen with the sound off. `run_all.py` runs it, so it is 45 steps.

**Verified after:** `verify_audio_unlock.py` 17/0, `verify_launch.py` 71/0, `verify_intro.py` 227/0,
`verify_landing_surfaces.py` 43/0, `verify_scroll_and_theme.py` 36/0, `verify_tooltip.py` 70/0,
`verify_results_surfaces.py` 29/0, `shot_rail.py` 208/0, `verify_app_flow.py` PASS,
`verify_palette.py` 38/0, `verify_view_matches_page.py` 9/0, `verify_results_matches_page.py` 12/0,
`verify_core_matches_page.py` 64/0, `verify_shipped_app_is_current.py` PASS, `verify_site_panels.py`
PASS, `audit.py` 2211 with the 5 deferred spend-ledger failures, typecheck clean,
`sync_context --check` 0.

### THE GLOBE ARRIVES INSTEAD OF APPEARING, AND THE NEXT PAGE STOPS FLASHING ITS OWN TEXT. 2026-08-30

Two faults, both about ORDER rather than about speed, and both fixed by moving when something happens
rather than by making anything faster.

🔴 **1. THE GLOBE WAS A BLACK DISC FOR THE FIRST HALF-SECOND OF EVERY LOAD.** The user: "it shows a
black space in place of globe when the website is loaded and globe takes time to render."
It is not slow rendering. `HeatGlobe` starts its draw loop on the frame it mounts, and
`THREE.TextureLoader.load()` has by then only RETURNED a Texture object; nothing has decoded into it.
**A WebGL sampler bound to an incomplete texture reads (0, 0, 0, 1)**, and `MeshPhongMaterial`
multiplies its white base colour by that, so the sphere is black until `earth_daymap.jpg` has been
fetched (197 KB), decoded (2048x1024) and uploaded. The file's own comment already said as much
("a single render would draw a black sphere") for the reduced-motion branch and the normal branch had
no equivalent.

**A smaller texture would not have fixed it, because the problem is the round trip.** So the fix is a
texture that needs no network: `tools/make_globe_poster.py` resamples the shipped day map to **128x64,
2,681 bytes**, and writes it as a base64 data URI into `app/src/intro/globePoster.ts`. That is INSIDE
the bundle, so it is in memory before the component runs and the only cost left is a decode.
The wrapper also starts at `opacity: 0` and is lifted by `data-aa-globe="ready"`, set on the poster's
decode or after a 1.2 s wall-clock floor, whichever is first: even a data URI decodes asynchronously,
so without that there would still be a frame or two of black.
⚠ **THE FADE IS ON THE WRAPPER, NOT THE CANVAS**, and that is not arbitrary: the canvas carries three
deliberate opacities of its own (0.72 dark, 0.62 light, 0.5 under 768px) which are a legibility
decision about type over scenery. Fading the parent multiplies with whichever applies. Fading the
canvas would mean this code picking one of the three.
⚠ **AND THE POSTER ALONE WAS A HALF FIX, WHICH AN ADVERSARIAL PASS CAUGHT BEFORE IT SHIPPED.** An
empty `map` is not the only way to get a black sphere: an empty NORMAL MAP is enough on its own.
`normal_fragment_maps` does `mapN = texture(normalMap).xyz * 2 - 1`, which for an all-zero texture is
(-1, -1, -1), and the resulting normal points into the surface so every light term goes to zero.
MEASURED in an isolated scene against the repository's own three build: the real 2048x1024 day map
with an empty normal map renders **(0, 1, 10)**, still black to a reader, and with `normalMap` left
null it renders **(48, 78, 113)**, a lit ocean. Throttled to 20 Mbps the poster-only build was still
near-black for a further 420 ms, waiting on `earth_normal.png`, which at 463 KB is the largest of the
four. So the normal and specular maps are now requested at the same moment and ATTACHED only when
they carry pixels.
**MEASURED after, with a CDP screencast: 0 frames show a black disc, on a fast load and again
throttled to 20 Mbps with 40 ms of latency.** The sequence is page background, then the globe fading
in from 750 ms, fully up by 1,379 ms. The full map replaces the poster in place when it decodes, and
because both are the same photograph the change reads as focus rather than as a swap.
**For scale, from the user's own recording of the deployed site: 440 ms of empty space, then 480 ms of
a pure black disc, RGB (0, 0, 0) alpha 255.**

🔴 **2. THE NEXT PAGE SHOWED ITS TEXT, BLANKED IT, THEN ANIMATED IT IN.** The user: "The text exists
there static for a few milli second, then disappears and triggers a transition ... If it has a
transition over it, it should not be visible static in the first place."
An ordering problem, exactly as described. `IntroLayer`'s `finish` did two jobs: unmount the gate AND
build the hero entrance. But the gate does not vanish at `finish`; it has already spent `outS` = 1.2 s
crossfading, and during that second the page behind was revealed AT ITS RESTING STATE. Only afterwards
did `playHeroEntrance` write its opacity-0 from-states, blanking text the reader had been looking at.

**GSAP's `from()` renders its start values on CONSTRUCTION**, not on the first tick, which is what
makes the fix small: `playLaunch` gained an `onOut` hook that fires at its own `out` label, and
`playHeroEntrance` gained a `leadS` delay. Building the entrance at the START of the crossfade puts
every animated element at opacity 0 while the splash is still opaque; the delay holds playback until
the splash has gone. The crossfade then reveals the page's background, cards, ring and filter bar, and
the text arrives onto it.
⚠ **THE COMMENT THIS REPLACES WAS RIGHT ABOUT THE CLICK AND WRONG ABOUT THE CROSSFADE.** It said the
entrance must start at the end "because it animates the masthead behind the splash and would otherwise
play out entirely unseen". Starting at the click would indeed waste it behind six seconds of opaque
splash; starting at the crossfade wastes nothing, because the delay means nothing plays until there is
something to see it on.
**MEASURED two ways.** By DOM: at the last sample before the crossfade begins, with the gate still at
opacity 1, the eyebrow, the four list items and the status line are all already at **opacity 0**, and
they stay there for all 16 samples of the crossfade. By screencast, counting text pixels per frame:
splash copy until 1,247 ms, **everything empty at 1,696 ms**, the wordmark from 1,880 ms, the bullets
from 2,390 ms, the status from 2,591 ms. No frame has the next page's text sitting static.
`onOut` fires at most once and is also fired by the escape hatch with its own shorter crossfade, so a
skipped sequence gets the same treatment.

⚠ **AND THE SPLASH WAS NOT FADING OUT AT ALL, WHICH IS A THIRD THING THE SAME PASS FOUND.**
`intro.css` still carried `transition: opacity 600ms cubic-bezier(0.22, 1, 0.36, 1)` on the gate, left
over from when CSS owned the exit. A CSS transition does not step aside for GSAP: it FILTERS every
value GSAP writes, so a 1.2 s tween from 1 to 0 was being chased 600 ms behind itself and the element
was unmounted while its computed opacity was still about **0.26**. The splash was being cut off a
quarter of the way through its own fade, in both the old build and the new one. It is the same
two-owners-of-one-property fault the rule beside it already documents, in the other direction: that
change removed `opacity: 0` and left behind the transition that animated it. Removed. MEASURED after:
the crossfade window went from about 20 samples to 49.

🔴 **AND THE ASSERTION THAT WOULD HAVE CAUGHT ALL OF THIS IS NOW IN THE SUITE.** `verify_intro.py`
counted WHAT the entrance animates and nothing checked WHEN. `verify_landing_surfaces.py` section 4c
polls the gate's opacity and three animated targets every 20 ms through a real click, and requires
that in every sample where the gate is part-way out, NO animated element is at its resting opacity.
⚠ Its first version used the wrong window, `gate > 0.9`, and failed a working build: 283 of 310 such
samples had text at rest, every one of them during the six-second hold behind a fully opaque screen.
The rule is about the moment a page becomes VISIBLE, so the window is `0.03 < gate < 0.995`. It also
asserts the elements do arrive afterwards, so it cannot pass by animating nothing.

⚠ **`testing/cdp.py` GAINED A SCREENCAST**, and it had to. `Page.captureScreenshot` is a COMMAND
scheduled on a main thread that is busy parsing 2 MB of JavaScript during exactly the window these two
faults live in: MEASURED, a capture requested at 300 ms was delivered at **2,053 ms**. A screencast is
pushed by the compositor instead, so the timestamps are the browser's. `subscribe()`, `pump()` and
`frames()` are new, and `send()` now buffers subscribed events instead of discarding everything that
is not a reply.

⚠ **ONE HARNESS ASSERTION HAD TO LOOSEN, AND IT IS WORTH SAYING WHY THAT IS NOT MOVING A GOALPOST.**
`verify_intro.py` matched the literal string `playHeroEntrance(false, 'full')`, which a third argument
breaks. What the check exists to prove is that `false` is TYPED at the call site rather than inherited
from a default, because the silent beat map is a decision. It now matches the call and its two
required arguments and prints the line it found.

**Verified after:** `verify_intro.py` 227/0, `verify_launch.py` 68/0, `verify_landing_surfaces.py`
39/0, `verify_scroll_and_theme.py` 36/0, `verify_tooltip.py` 70/0, `verify_results_surfaces.py` 29/0,
`shot_rail.py` 208/0, `verify_app_flow.py` PASS, plus the palette, determinism, identity, panel and
audit set.

### THE PAGE SCROLLS, THE GLOBE IS THE FIRST FRAME, AND A THEME CHOICE STAYS ON ITS SCREEN. 2026-08-30

Four reports. Three of them were only visible under a condition no check in this repository
reproduced, and the fourth was a design decision that had to be reversed because it kept producing
the same complaint.

🔴 **1. THE PAGE COULD NOT SCROLL, AND THE USER CALLED IT THE BIGGEST ISSUE.** `cinematic.css` gave
`#app` `height: 100vh; overflow: hidden` on every stage but the landing, with `.aa-workspace-main` as
the only scroller. A dashboard shell, and a reasonable one until the viewport is short.
**MEASURED at 1366x768:** `main#app` clientHeight **672** against scrollHeight **755**, so 83 px were
clipped with nothing in the chain able to reach them; `document.scrollingElement` read 672/672 and
`window.scrollTo(0, 4000)` left scrollY at **0**. Both Quick Action rows sat entirely below the fold.
⚠ **AND THE RAIL'S OWN SCROLLBAR WAS NOT A WAY IN**, which is what makes this containment rather than
discoverability: at 1600x1000 and 1400x820 the rail had NOTHING to scroll (scrollHeight 561 ==
clientHeight 561), and at 1366x768 it had 19 px, exhausted by one real wheel tick, after which both
rows were still completely below the fold.
The rule that permitted it was `max-height: calc(100vh - 128px)`: 128 is a guess at the rail's top
offset and the rail's top **measures 210.6 px**, so the rule allowed a box ending 82.6 px past the
bottom of the screen. That is `05-TRAPS` 5b.12 word for word, and its own advice ("the fix is not a
smaller constant, which would just be a guess at the masthead's height") had been followed for the
engine's sidebar and never applied here.
**The shell is gone.** `min-height: 100vh` and no overflow clamp, `.aa-workspace-main` is an ordinary
flex child, and both sticky columns are bounded by `calc(100vh - 32px)`, which needs no measurement of
anything. `--aa-scrollport` and the effect that published it are removed with their only consumer.
⚠ **AND THE TAB RESET HAD TO BE TOLD IT MEANT IT.** `lib/noscrolljump.ts` patches `window.scrollTo` to
swallow any scroll-to-top taken while `body[data-stage]` is unchanged, because the engine re-runs
`setStage()` on the stage it is already on. A tab change does not change the stage, so "every tab
opens at its own top" looked exactly like one of those re-runs and was swallowed: MEASURED at window
scroll 400, money stayed at 400, plume went to 521 and calib clamped to 279. `scrollToTopNow()` is
that file's new and only sanctioned way to mean it.
**MEASURED after:** at 1366x768 on results, scrollHeight 837 against clientHeight 672, `scrollY`
reaches 165, and "Choose a different site" sits fully on screen at 552..593. Same at 1400x820 and on
the configure stage.
⚠ **WHY NOTHING CAUGHT IT:** every browser check here uses a tall window, 1500x1400, 1500x1000,
1600x1000 or 1440x1000. `verify_scroll_and_theme.py` runs 1366x768 and 1400x820 on purpose.

🔴 **2. THE FIRST FRAME WAS THE WRONG PAGE.** `<IntroLayer/>` was rendered at the END of the
`!a || !h` data-loading ternary, so the gate could not exist until the artefact bundle AND the three
headline JSONs had landed. Until then React painted the OTHER arm of the same ternary, and that is
what the user recorded: the banner, the wordmark, the four bullets, both value cards, the REPLAY line
and "Loading saved data...".
**MEASURED on four warm loads: 451, 470, 591 and 717 ms of the wrong page.** Confirmed causal by
holding `backtest.json`, `trace.json` and `money.json` for 3 s over CDP: the gate's DOM insert moved
from 1,253 ms to 3,876 ms, +2.62 s for a +2.9 s hold. Their own recording of the deployed site shows
it at t = 1.323 s.
The gate now renders BEFORE the guard, so it is in React's first commit. **MEASURED after: the first
frame with `#root` children and the first frame with the gate are the same frame, at 346 ms.**
⚠ **AND A SECOND, SEPARATE FLASH UNDERNEATH IT, WHICH THE FIRST FIX WOULD NOT HAVE TOUCHED.**
`body[data-aa-intro]` was set in a `useEffect`, which runs AFTER paint. `intro.css` paints the gate
`background: var(--page) !important`, and `--page` is **#fafafa in the light palette**; the rule that
pins the splash to the dark floor is the one hanging off that attribute. So a light-theme reader got a
full-viewport WHITE splash in the wrong layout until it landed, which is exactly what their recording
shows between t = 1.600 s and t = 2.425 s. `useLayoutEffect` instead. **MEASURED after: 0 samples with
the gate present and the attribute unset, and the gate's background is rgb(7,16,24) at first sight.**

🔴 **3. THE LANDING PAGE KEPT COMING BACK LIGHT, AND THE PREVIOUS DESIGN IS REVERSED.** A theme choice
was recorded GLOBALLY, so one press of the toggle anywhere pinned every screen for good. MEASURED:
pressing it TWICE on the configure screen leaves configure looking identical, light to dark to light,
and permanently pins the LANDING page to light, in the same document and after a reload. One press on
the landing does it just as directly.
⚠ **THAT WAS THE SPECIFIED BEHAVIOUR** (`02-ARCHITECTURE` section 5, `05-TRAPS` 5b.26) and the user has
now reported its consequence twice, so the specification changes rather than the code being defended.
A choice is recorded **per stage group**: `pick` is the landing, `work` is configure plus results.
Pressing the toggle on the landing pins the landing and nothing else. New key names, `-pick` and
`-work`, which is the half of the fix that unsticks a reader already carrying the old pair.
Four harness seeders had to move with it, and one of them silently: `shot_rail.py` drives to RESULTS
and never asserts the palette, so seeding `-pick` there would have left the run labelled "dark"
rendering light with nothing to say so. It seeds `-work`.

**4. THE VALUE CARD**, at the user's instruction: the money is a second headline figure at the same
44 px / 800 as the hours, and the sites line is one phrase, "238 of 250 sites gain free-cooling hours,
and all 250 are in the total above", down from three clauses. The split and the netting both survive
the cut, which was the constraint.

**`testing/verify_scroll_and_theme.py` is new**, 36 checks: the document scrolls at three
short-viewport/stage combinations, the last Quick Action is reachable, and the toggle is driven with
real pointer clicks through the exact two-press-on-configure sequence that reproduced the report.
`run_all.py` runs it, so it is 44 steps.

**Verified after:** `verify_scroll_and_theme.py` **36/0**, `verify_landing_surfaces.py` 39/0,
`verify_tooltip.py` 70/0, `verify_results_surfaces.py` 29/0, `shot_rail.py` 208/0,
`verify_intro.py` 227/0, `verify_launch.py` 68/0, `verify_app_flow.py` PASS,
`verify_core_matches_page.py` 64/0, `verify_view_matches_page.py` 9/0,
`verify_results_matches_page.py` PASS, `verify_palette.py` 38/0, `verify_state_filter.py` 62/0,
`verify_stop_control.py` 31/0, `verify_live_report_button.py` 25/0,
`verify_app_deterministic.py` PASS, `verify_site_panels.py` PASS,
`verify_shipped_app_is_current.py` PASS, `verify_deployed_root_is_the_app.py` PASS, `audit.py` 2211
passed with the 5 spend-ledger failures the user deferred, typecheck clean, `sync_context --check` 0.

### THE HERO COPY, THE VALUE CARD, THE LOOP, THE PULSE AND THE REFRESH. 2026-08-30

Six items, and two of them required saying no to the wording as given, with the measurement that
justified it. Both are recorded here because the numbers are the argument.

**1. TWO HERO BULLETS REWRITTEN**, verbatim as supplied. "Data centres run mechanical chillers even
when outside air could provide the necessary cooling." and "...turns 'right now' into hours of prior
notice."

**2. THE VALUE CARD IS PRICE, THEN THE FIGURE, THEN SITES**, at the user's instruction, with only
numerals bold. The headline figure now sits in the MIDDLE of the card rather than at the top, which
is unusual and is what was asked for: the price line introduces it, the sites line qualifies it. The
tariff-provenance row is gone, because the instruction enumerated the card's contents as three
phrases and that was not one of them.

🔴 **THE NEGATIVE SIGN WAS NOT DELETED. THE FIGURE WAS REPLACED.** The instruction was "worth $25.4M
to $65.8M a year ... (Note: The negative sign has been intentionally removed)." Printing that would
assert a floor of plus twenty-five million against an artefact that says the floor is MINUS twenty-
five million, which is a worse fault than the one it fixes, and it is the exact thing the same reader
ruled out two days earlier: "presenting one as fact is unacceptable."
The sign can go honestly, by using a pair that is genuinely positive at both ends. `usd_lo`/`usd_hi`
are the sum of every site's CHEAPEST and DEAREST swept corner; summing 250 worst corners describes a
world in which all 250 land on their worst at once, and its mirror for the best. Neither is a
scenario, and the pair spanning zero was an artefact of adding up extremes.
**`usd_mid_lo`/`usd_mid_hi` are new**: the MEDIAN cell of each site's own sweep, at the two published
IT-load densities, summed. **$3,071,953 to $6,143,468.** Positive at both ends, reproducible from the
same cells, and it needs no minus. Both pairs are published in `portfolio.json`; only which one the
card states changed.
⚠ **AND THE OTHER SUPPLIED SENTENCE WAS FACTUALLY WRONG, MEASURED.** It read: "The remaining 12 sites,
where site-specific gates accurately predict zero free-cooling hours, remain factored into the total
calculations." Measured across all twelve: the agent certifies between **4,364 and 7,529** free-cooling
hours at each of them, and **not one certifies zero**. What is true is that at those twelve the
INCUMBENT certifies more, because the agent's bound refuses hours a thermometer would take. The card
says the agent is the more conservative of the two there, which is the fact in the neutral register
that was asked for.
"Chiller-hours" is "free-cooling hours" on this card. It is unchanged on the per-site KPI tile
(`Chiller-hours recovered`) and in the masthead's third bullet, because those are a different figure
about a different thing and renaming them would move `audit.py`'s published-figure registry.

**3. THE LOOP'S OUTER LABELS CLEAR THE CURVE, AND THE PREVIOUS FIX USED THE WRONG NUMBER.** It
anchored them to `XS[0] - 78`, the x of both control points on the left turn. **A cubic never reaches
its control points.** For a curve whose two controls share an offset, the extreme is at t = 0.5 and is
`endpoint + 0.75 * offset`, so the loop bulges 58.5 units, not 78. Measured at the note's baseline the
turn is at x 60.5 while the note began at x 56: the sentence started four and a half units outside the
loop. `CURVE_BULGE = 0.75 * TURN` now, derived rather than typed. Measured after: the left note runs
74.7 to 201.9 against a loop edge at 59.5, the right note ends at 1100.9 against 1116.5.

**4. THE REVOLVING DOT SURVIVES A ROUND TRIP.** Three separate reasons it could not before:
`IntroLayer` renders `null` off the landing stage so `Pipeline` UNMOUNTS and its SVG goes with it;
leaving calls the entrance's `stopLoops()`, which kills the tweens and deletes `body[data-aa-ring]`,
the attribute intro.css gates the dot's `visibility` on; and the only thing that ever started the
loops was `playHeroEntrance` in a `useLayoutEffect` with an EMPTY dependency array, on a component
that never unmounts because it returns null.
The loop builder is lifted out of that closure into `buildRingLoops()`, and `startRingLoops()` starts
it standalone. `IntroLayer` calls it on a return only, gated on a `hasLeft` ref, and
`startRingLoops` refuses outright when `body[data-aa-ring]` says a live set already exists, so the
first load is untouched and no path runs two sets at once.

**5. A REFRESH COMES HOME TO THE GLOBE, AND THERE WAS NOTHING TO REDIRECT.** This app has no router:
pick, configure and results are three states of ONE document, and a fresh document already starts on
'pick'. What survived a refresh was `hasSeenSplash` in sessionStorage, which `gateEnabled()` reads to
skip the gate, so a reload landed on the first screen with the globe, the wordmark and the audio all
suppressed. A script in `app/index.html` now removes that key on every DOCUMENT LOAD, before the
bundle runs and therefore before the flag is read.
⚠ **THIS REVERSES HALF OF THE BRIEF THAT INTRODUCED THE FLAG**, which asked for exactly the opposite:
"a reload or a back-button press skips it". The other half is untouched and is what "normal
client-side navigation" means here: within one document, passing the gate and then walking pick ->
configure -> results -> pick never brings it back, because nothing clears the key between state
changes. Verified both ways.

**6. THE THREE-GATES SENTENCE NAMES NOBODY.** Two attempts at naming a source got it wrong in two
different ways, so at the user's instruction it names none: "Three gates: temperature, humidity,
contamination. Not temperature alone, because a real economizer also limits on moisture and on what
the outside air carries in." The check asserts the ABSENCE of eight source names rather than the
presence of one, so the next attempt cannot slip a different one in.

**`testing/verify_landing_surfaces.py` is new**, 38 checks over the DevTools Protocol: the two bullets
verbatim, the card's three blocks in order with its money read back out of `portfolio.json` and every
bold run required to be a figure, the ring labels measured against the PATH by `getPointAtLength`
rather than against its control points, the dot sampled twice a beat apart on arrival and again after
a real navigation and back, and a real reload.
`run_all.py` now runs it and the two other pointer-driven verifiers, so it is 43 steps.

**Verified after:** `verify_landing_surfaces.py` **38/0**, `verify_tooltip.py` 70/0,
`verify_results_surfaces.py` 29/0, `shot_rail.py` 208/0, `verify_intro.py` 227/0, `verify_launch.py`
68/0, `verify_core_matches_page.py` 64/0, `verify_view_matches_page.py` 9/0,
`verify_results_matches_page.py` PASS, `verify_palette.py` 38/0, `verify_state_filter.py` 62/0,
`verify_stop_control.py` 31/0, `verify_live_report_button.py` 25/0, `verify_app_flow.py` PASS,
`verify_app_deterministic.py` PASS, `verify_site_panels.py` PASS,
`verify_shipped_app_is_current.py` PASS, `verify_deployed_root_is_the_app.py` PASS, `audit.py` 2211
passed with the 5 spend-ledger failures the user deferred, typecheck clean, `sync_context --check` 0.

### THE RAIL, THE TOOLTIP, THE HOUR DROPDOWN, THE COVERAGE TILE AND ONE ACRONYM. 2026-08-30

Five reports in one message, and three of them turned out to be the same class of fault: a CSS or DOM
mechanism doing something invisible that no amount of reading the component would have shown. So the
first thing built was a way to measure them.

🔴 **`testing/cdp.py` IS NEW, AND IT IS THE REASON ANY OF THIS IS VERIFIED RATHER THAN ASSERTED.** Every
other browser check here runs Chrome with `--dump-dom` and reads what a probe published. That cannot
produce the two states this brief is entirely about: `:hover` comes from real pointer position and no
DOM API sets it, and `:focus-visible` is a heuristic Chrome withholds from a programmatic `.focus()`
on a button. A ninety-line DevTools Protocol client over the already-installed `websockets` gives
`Input.dispatchMouseEvent`, `Input.dispatchKeyEvent` and `Page.captureScreenshot`, so a check can
hover, press Tab, and photograph the result. Three new verifiers use it.

---

**1. THE SIDEBAR RAIL. The hierarchy was inverted, and the user led with that.** MEASURED before: nav
rows 12.9px at default weight in `--text-secondary` with icons at `opacity: 0.62`; Quick Action titles
12.6px at weight 600 in `--text-primary` with icons at full `--series-1`. The group a reader navigates
with was the quieter of the two. Now 13.2px/500 against 12.6px/500, and the nav group owns the only
saturated state in the rail.
Section labels are 700 / 11px / 0.09em, and the `opacity: 0.72` is gone: a token chosen for its
measured contrast and then multiplied by 0.72 is a token whose measurement no longer applies.
**MEASURED in the browser against `--w-1`, the surface tones.css actually paints the rail with:
7.45:1 dark, 5.51:1 light**, both over the 4.5:1 floor.
Rows are 40px, radius 8, icons at `currentColor`. Active: a 28-to-38 % fill (up from 17 %), weight
600, brand-blue icon, and a **3px accent bar on the row rather than on the marker**, because the
marker is the element framer-motion slides by `layoutId` and a 3px child inside it would be stretched
for the length of the slide. Hover: a 7 % neutral fill, a step of ink, `translateX(2px)`, 150ms
ease-out. Active-on-hover deepens its own tint and never takes the neutral fill. `:focus-visible` 2px
at 2px offset, `:active` `scale(0.99)` at 80ms, and every transform and transition is undone under
`prefers-reduced-motion` by PROPERTY rather than by state, so a state added later cannot forget.
⚠ **THE OWNERSHIP WAS THE OTHER HALF OF THE FIX.** `.aa-rail-eyebrow` was declared in BOTH
workspace.css and dashboard.css, and dashboard.css loads later, so editing the copy in workspace.css
changed nothing at all. workspace.css now keeps the box and dashboard.css owns every state; and
because cinematic.css loads after BOTH, it restates each of those states in `--fg-*`, or the rail
would be zinc-grey type on a blue-slate panel.
⚠ **"Run the agent" IS GONE FROM QUICK ACTIONS**, at the user's instruction, and it really was inert:
it forwarded to `#runagent`, whose handler is `runAgent()` (demo/index.html:2770), which is
`if (streaming) return; setStage('results'); drawAll(); await streamTape()`. By the time the rail
exists the stage is already `results`, so the only visible effect left is re-streaming `#tape`, a
panel workspace.css shows on the `live` tab alone. Nothing was removed from the engine.
`testing/shot_rail.py`: **208 checks, 0 failed**, both palettes, with rest/hover/focus screenshots.

**2. THE (i) TOOLTIP, AND THE OBVIOUS DIAGNOSIS WAS WRONG.** Reported as "semi-transparent, with the
card's numbers showing through, correct only once the pointer leaves the card". MEASURED before
touching anything: the panel's background was **rgb(12,26,42) at alpha 1.0** and its backdrop-filter
was **`none`** (tones.css:148-160 already handles `[role='note']`). It was never translucent.
🔴 **THE CAUSE WAS `hover:-translate-y-0.5` ON THE CARD.** Tailwind v4 ships it as the `translate`
property, a non-none `translate` makes a stacking context, so while the card was hovered the panel's
`z-index: 300` was scoped inside it and every later sibling card painted over it. The wash was the
NEIGHBOUR's own `rgba(24,24,27,0.72)` glass fill on top of an opaque panel. Sampled at 80 points with
a real pointer: **topmost at 24 of 80 hovered, 80 of 80 with the pointer away**; pixel median over the
overlap band (20,24,31) hovered against (12,26,42) away, matching a predicted 0.72 blend of (21,25,31).
The fix leaves the card alone and portals the panel to `<body>`, where there is no card ancestor to be
trapped in and no `overflow` to be clipped by. It now opens on hover after 120ms, on click, and on
keyboard focus, closes in 60ms or on Escape or on a click outside, auto-flips and shifts to stay in
the viewport, and carries `pointer-events: none`. **No opacity fade**: an element mid-fade IS
translucent, which is the one thing the brief forbids, so only a 2px rise animates.
The ALL CAPS was real inheritance of `text-transform` from `.label`; portalling ends it, and the five
authored capital openers ("A SHARE", "A RANGE BECAUSE IT IS A SWEEP" and three more) are lowered.
Wording unchanged, casing only.
`testing/verify_tooltip.py`: **70 checks, 0 failed**, including a pixel assertion that reads the
rendered PNG back and requires every pixel inside the panel to be its own fill or its own ink.

**3. THE HOUR DROPDOWN DID NOTHING, AND IT WAS A CLONE.** `<select id="c_hour">` lives in a `<details>`
inside `#whycard`; the engine binds a real handler to it (`results/engine.mjs:309`) that redraws the
seven stage lines in `#tkhour`. `lib/declutter.ts` folded that whole block away and serialised its
`innerHTML` into the fold modal. **Serialising HTML drops event listeners**, so the select a reader
could see was inert, and because ids are copied too there were two `#c_hour` and `$('#c_hour')` still
found the hidden original. MEASURED: a real `change` event on the visible clone left the stage text
byte-identical; the same event on the hidden original redrew it from 12:00 to 00:00.
One line: the fold exemption list now includes `select, input, textarea`. The block stays a closed
`<details>` on the card, so nothing is un-decluttered.
**AND THE ANSWER TO "what is this hour dropdown for then":** it drives the seven stages and nothing
else. The table below it, `#extable`, is built from ALL 24 hours by `drawExplain()` and never reads
the selection. Verified: 25 rows, one per hour plus a header.

**4. THE BOUND COVERAGE TILE IS GREEN AND NO LONGER SAYS "FAILED".** The caption is now
**"5 more day-pairs before 90 % is reachable at all: the ceiling at 4 is 80.0 %"**, and every number
in it is read from `trace.json`: `cycle.pairs.length` is 4 and `cycle.bound_day_level
.n_needed_for_nominal` is 9, so the shortfall recomputes to 3 the day the two deferred pairs are
adopted.
⚠ **IT SAYS "REACHABLE AT ALL", NOT "NEEDED FOR 90 %", AND THAT IS DELIBERATE.** The user asked for
"6 more days of forecasting needed for 90 %"; the number is 5 and the claim is not supportable.
Reaching n = 9 is NECESSARY and not SUFFICIENT: measured coverage is 14.4 points below even the
current 80 % ceiling, and the project's own simulation (`testing/results/diag59_daysneeded.json`,
`days_for_90pct_all_three = 10`) attributes only part of the gap to sample size. `#n26fail` already
states the 10.
The tone is still DERIVED, and it is the question that changed: from "is this under 90 %", which is
red for as long as the arithmetic forbids 90 %, to "is 90 % reachable at this n AND still missed",
which is the only reading under which the figure is a defect. It turns red on its own with no edit.
⚠ `tone='good'` alone painted nothing: there was a `.tile[data-tone="good"]` border rule and no ink
rule. Added, and it has a blast radius of one, because this is the only tile in the engine that ever
passes `'good'`.
⚠ The plate cell publishing the same figure passed a hard-coded `'miss'` class, red plus a diagonal
hatch, unconditional. Now `null`, or the two surfaces would contradict each other.
⚠ **THE SELF-SCORING TAB IS DELIBERATELY UNTOUCHED.** `drawCoverageTiles()` keeps the strict
`< 0.90 ? 'crit' : 'good'`, because that panel exists to score the promise and a scorecard should show
the miss. One line to change if that is wanted too.

**5. "LBNL" NOW SAYS WHO IT IS, AND THE SENTENCE AROUND IT IS TRUE.**
⚠ **SUPERSEDED THE SAME DAY, see the entry above:** the user asked for the line to name no source at
all. The correction below stands as a record of what was wrong with the original; the wording it
introduced lasted one revision.
** The card read "the three things
LBNL measured operators actually worry about". The acronym was expanded in exactly one place in the
repository, `src/money.py:160`, attached to a DIFFERENT publication. And it credited LBNL with all
three gates, which `src/environment.py:12-27` does not: humidity is ENERGY STAR plus Honeywell's JADE
controller, and only contamination is LBNL. That study measured PARTICLE CONCENTRATIONS in eight data
centres; operator reluctance is its stated motivation, not something it measured.
Now: "Three gates: temperature, humidity, contamination. Humidity comes from ENERGY STAR and
Honeywell's JADE controller; contamination comes from Lawrence Berkeley National Laboratory (LBNL),
which put particle counters in eight real data centres." Every clause has a line to point at.
`testing/verify_results_surfaces.py`: **23 checks, 0 failed**, covering 3, 4 and 5.

**Verified after:** `shot_rail.py` 208/0, `verify_tooltip.py` 70/0, `verify_results_surfaces.py` 23/0,
`verify_intro.py` 227/0, `verify_launch.py` 68/0, `verify_core_matches_page.py` 64/0,
`verify_view_matches_page.py` 9/0, `verify_results_matches_page.py` PASS, `verify_palette.py` 38/0,
`verify_state_filter.py` 62/0, `verify_stop_control.py` 31/0, `verify_live_report_button.py` 25/0,
`verify_app_flow.py` PASS, `verify_app_deterministic.py` PASS, `verify_site_panels.py` PASS,
`verify_shipped_app_is_current.py` PASS, `verify_deployed_root_is_the_app.py` PASS, `audit.py` 2211
passed with the 5 spend-ledger failures the user deferred, typecheck clean, `sync_context --check` 0.

### THE TWO SUMMARY CARDS BECAME A GRID COLUMN, AND STOPPED QUOTING ONE SITE. 2026-08-29

**THE LAYOUT WAS THE SMALLER HALF.** The pair used to be `position: absolute; top: 148px; right: 8px`
against `#app`, which meant they were positioned against their nearest positioned ancestor rather than
against the container everything else shares, so their right edge had no reason to agree with anything
and did not. They are now the second column of a real grid,
`minmax(0, 1.4fr) minmax(360px, 1fr)` with `column-gap: clamp(48px, 4.5vw, 76px)`, inside a container
widened from 1,180 px to 1,440 px.
**MEASURED at a 1920 window** by `testing/shot_cards.py`: cards **548 px** wide each, gutter **76 px**,
and the card right edge and the filter panel right edge both at **x 1647**. Before: 347 px of card
beside a 360 px gap, with the right edges 22 px apart. A gap wider than the thing it separates is why
the cards read as cramped and stranded at once.
🔴 **THE DECORATIVE DRIFT HAD TO LOSE AN AXIS FOR THAT LAST FIGURE TO BE TRUE.** The stack floats on a
slow framer-motion loop; it used to float on two axes, `x: [0, 6, 0, -6, 0]` as well as `y`. Measured,
the right edge read 1651 against the panel's 1647, because the sample caught the drift four pixels out.
The layout was already correct; the decoration was walking the card off the edge it was laid out on.
A brief that asks two edges to share an x coordinate is not satisfied by an edge that is right on
average. Vertical only now.
Responsive, both verified with screenshots: **below 1100 px** one column, cards beneath the prose and
side by side as a 2-up row (467 px each at a 1024 window); **below 700 px** stacked full width (550 px
at a 600 window). One numeric scale for both headline figures, `clamp(30px, 3.1vw, 44px)`, where the
count was 62 px and the money 31 px and the smaller of the two read as a caption.
⚠ Hiding a grid item does not give its track back: `body[data-stage]` now collapses `.aa-mast-grid` to
one column on configure and results as well as hiding the stack, or the prose would sit in 1.4/2.4 of
the page beside 548 px of nothing.

**THE CONTENT WAS THE LARGER HALF, AND THE OLD CARD WAS A DUPLICATE.** It read `usdLo`, `usdHi`,
`cutPct`, `gainHPerYear` and `weatherHours` from the Headline of whichever site was SELECTED, so it
printed Ashburn's $334k-$967k, its 10.7 % and its +406 h, and the KPI plate a few hundred pixels below
printed the same four numbers for the same site. Every figure now comes from **`demo/portfolio.json`**,
written by **`tools/portfolio_totals.py`** and regenerated by `run_all.py` (a new step, placed after
`metros.py --manifest` because it opens the artefact filenames that step writes).

🔴 **IT IS A SUM OF 250 REAL RESULTS, NOT A PER-SITE FIGURE MULTIPLIED BY A COUNT**, and the tool proves
that rather than asserting it: it hashes every artefact it opens and reports **247 distinct backtests
and 250 distinct money files**. The user's instruction was explicit -- "a per-site figure multiplied by
the site count is a modeled projection, not a measurement" -- and this is the check that the objection
does not apply.

**WHAT THE CARDS NOW SAY, and where each number comes from:**

| figure | value | computation |
|---|---|---|
| sites run | **250** | `sites.json`, count of `offerable` |
| sites mapped | **637** | `unified_sites.json`, `sites.length` |
| hours of weather | **4,232,006** | sum of `backtest.hours` over the **98 DISTINCT stations**, each counted once |
| chiller-hours a year | **+61,864** | sum of `gain_h_per_year` from each site's own anchored `C ` ladder row |
| sites gaining | **238 of 250** | count of sites with `gain_h_per_year > 0` |
| money | **-$25.4M to $65.8M** | sum of each site's `min(cells) x mw_lo` and `max(cells) x mw_hi` at the shipped 3 h notice |
| tariff provenance | **61 own state, 189 reference** | count of `electricity_prices_are_this_states_own` |

⚠ **THE HOURS FIGURE IS TWO FIGURES AND THE LARGER ONE IS A TRAP.** Summing `weather_hours` over 250
sites gives **10,820,547**, and that is site-hours scored, not hours of weather: the 250 sites draw on
only **98** airport stations, so a station shared by three sites is counted three times. Both are
published in `portfolio.json`; the card states the smaller one, which needs no asterisk.

⚠ **THE MONEY IS A FOOT ROW, NOT THE HEADLINE, AND ITS LOW BOUND IS NEGATIVE.** 12 of the 250 sites come
out BEHIND the incumbent controller, so the sum of every site's worst swept corner is -$25.4M. The
headline is the chiller-hours instead, because hours need no tariff, no power density and no state, and
therefore carry none of that modelling. The 12 losing sites are named on the card ("238 of 250 sites
gain hours. The 12 that lose are subtracted above, not dropped") rather than left in a popover, and so
is the tariff provenance: EIA publishes no row for most states, so 189 of the 250 are priced on the
Virginia and Illinois reference rows. Presenting the positive corner alone would have been exactly the
unlabelled cherry-pick the brief forbade.

**AND THE DARK DEFAULT WAS BROKEN ON THE DEPLOYED SITE, for a reason worth keeping.** The marker meaning
"the reader chose a theme" was `aa-theme` -- true of the code as written, false of the world, because
this app has written `aa-theme` for weeks. Every returning visitor already had one, so every returning
visitor counted as having chosen, and the stage default never applied to any of them. A dedicated key,
**`aa-theme-choice`**, cannot have that history: it is written only by `chooseTheme()`. `aa-theme`
remains, demoted to a CACHE of the resolved palette so the pre-paint script still prevents a flash.
⚠ `verify_intro.py` had to be told: seeding only `aa-theme` now tests nothing, because the app is free
to overwrite the cache. Its light-theme fixture writes both keys.

⚠ **TWO PRE-EXISTING FAILURES FOUND WHILE VERIFYING, both fixed here.**
* `verify_core_matches_page.py` was failing at HEAD: `core/explain.mjs` still carried the wrong vendor
  attribution that commit `e72e06d` corrected in the page ("the wind-direction error FortyGuard
  actually has"). The page was right and core was stale, so core was corrected to match and
  `tools/mkcore.py` re-run to refresh the provenance hashes. 64 checks, 0 failed.
* `verify_intro.py`'s overlay hit-test used `by <= innerHeight`. The last y a viewport of height H owns
  is H-1, so `elementFromPoint(x, H)` returns null. Once the prose column narrowed from 1334 px to
  742 px the bullets took an extra line each and the Configure button's centre landed at exactly
  y=844 in an 844 px viewport: the bounds test said "on screen", the hit test said "nothing there",
  and the check reported that the gate does not cover the page. Strict `<`, plus a null fallback to
  the viewport centre. `05-TRAPS` 5b.25.

**Verified after:** `verify_intro.py` **227/0**, `verify_launch.py` 68/0, `verify_core_matches_page.py`
**64/0**, `verify_palette.py` 38/0, `verify_state_filter.py` 62/0, `verify_stop_control.py` 31/0,
`verify_live_report_button.py` 25/0, `verify_app_flow.py` PASS, `verify_app_deterministic.py` PASS,
`verify_shipped_app_is_current.py` PASS, `verify_deployed_root_is_the_app.py` PASS, `audit.py` 2211
passed with the 5 known spend-ledger failures the user deferred, typecheck clean.

### THE PAGE WENT BLANK WITH NO WEBGL, AND NOTHING IN THE SUITE COULD SEE IT. 2026-08-29

**The user: "it's not rendering."** They were right, and every check was green.

🔴 **`new THREE.WebGLRenderer()` THROWS WHEN IT CANNOT GET A CONTEXT.** It does not return null. Thrown
from inside `HeatGlobe`'s effect, with no error boundary above it, React unmounted the entire tree.
MEASURED with `--disable-webgl`: `#root` went from **1 child to 0**, plus a second cascading error. Not
a missing globe, not a degraded splash: an empty page, on a machine whose only fault is that 3D
acceleration is off, which is ordinary on locked-down laptops, in VMs and behind some GPU drivers.

⚠ **AND EVERY BROWSER CHECK IN THIS REPOSITORY MISSED IT FOR THE SAME REASON:** they all launch Chrome
with `--enable-unsafe-swiftshader --use-gl=angle`, because MapLibre needs a rasteriser. A harness that
always supplies the thing under test cannot see its absence. That is `05-TRAPS` 5b.7 wearing another
costume, and it is the second time this project has shipped a fault its own suite was structurally
unable to catch.

**HOW IT WAS FOUND, and it is the method rather than the luck:** the report was three words with no
stack. Rather than guess, the app was loaded four ways and instrumented for uncaught errors: the built
bundle through `serve_app.py`, the deployed `demo/app/` layout through the real `serve_live.py`, the
Vite dev server, and finally the same page with WebGL taken away. The first three were clean. The
fourth was the answer in one run.

**TWO FIXES, and the second is the one that matters:**
* the renderer is attempted inside a `try`, and a failure returns from the effect before anything else
  is built. No globe, working page, no message: a reader with WebGL off does not need to be told what
  they are not seeing.
* **`components/IntroBoundary.tsx`** wraps `IntroLayer`. Everything under `intro/` is scenery, and
  scenery failing must cost the reader the scenery and nothing else. A class, because error boundaries
  are the one thing React still has no hook for. ⚠ It catches render and lifecycle errors only, not
  asynchronous ones, which is why `launch.ts` wraps its own timeline and `audio.ts` wraps every
  `play()`; this is the last line, not the only one.

**AND A PERMANENT CHECK, `verify_intro.py` section 13b**, which runs the whole page with
`--disable-webgl --disable-3d-apis` and asserts the splash, its wordmark and its call to action all
render, that the canvas is present but has no GL context (so the scenario is testing what it claims),
that the product is reachable with the intro off as well, and that App.tsx really does wrap IntroLayer
rather than merely importing the boundary. **227 checks, 0 failed**, up from 218.

⚠ **A PROCESS SLIP IN THE DIAGNOSIS, worth recording.** While hunting this I ran
`npx vite build --mode development`, which overwrote `app/dist` with a development build. Caught
immediately because `build_app.py` prints the source hash and the asset names, and restored by
rebuilding properly; `verify_shipped_app_is_current.py` confirms the bundle matches the source. Do not
run vite directly: `tools/build_app.py` from the repository root is the only build.

**Verified after:** `verify_intro.py` **227 checks, 0 failed**, `verify_launch.py` 68/0,
`verify_app_flow.py` PASS, `verify_app_deterministic.py` PASS, `verify_palette.py` 38/0,
`verify_shipped_app_is_current.py` PASS, typecheck clean, `sync_context.py --check` 0.

### EIGHT UI CORRECTIONS, AND ONE THEY DID NOT ASK FOR THAT THE CHECK COUNT FOUND. 2026-08-29

**THE DEFAULT THEME NOW DEPENDS ON THE STAGE.** Dark on the landing page, light on configure and
results, both at the user's instruction and both only a DEFAULT.
🔴 The distinction that makes it work is between an AUTOMATIC theme and a CHOSEN one.
⚠ **SUPERSEDED THE SAME DAY, see the entry above:** the key holding that distinction is
`aa-theme-choice`, not `aa-theme`. As written below this was correct about the code and wrong about the
world, because `aa-theme` already existed in every returning reader's storage. The rest stands: with no
such key the stage decides and keeps deciding. ⚠ **That key used to be written on every
change**, which would have made the first automatic switch indistinguishable from a choice and frozen
the theme from then on. It is the one line that had to move for any of this to be true. `App.tsx`
reads the stage through the same read-only `useStage()` observer IntroLayer uses, so no second owner.

**THE HEADLINE IS FOUR BULLETED POINTS**, a real `<ul>` so the count and position are announced, with
a small brand-blue square marker rather than a disc.

**THE RING'S NOTES ARE INSIDE THE LOOP AND CAPITALISED.** The outer two are now anchored to the LOOP's
own edges (`start` at `XS[0] - 78 + 16`, `end` at `XS[4] + 78 - 16`) rather than centred on their node.
Clamping the width would truncate a sentence and nudging x by a measured amount is a guess the next
wording breaks; anchoring makes containment a property of the geometry.

**THE SCOPE CARD IS REWRITTEN AND HAS A SECOND CARD UNDER IT.** "250 data centres covered with fully
agentic analysis / out of 637 mapped from OpenStreetMap", with the three "Own plant configuration"
lines gone. The new value card carries **$334k to $967k a year**, **10.7 % less mechanical cooling and
+406 chiller-hours**, and **43,763 real held-out hours**.
⚠ **SUPERSEDED THE SAME DAY, see the entry above:** those four are ONE SITE's figures, and the KPI plate
below prints the same four for the same site. Both cards now read portfolio totals from
`demo/portfolio.json`.
🔴 Every one of those five figures is a PROP read from an artefact, never typed: the caller passes them
from the same `Headline` the KPI plate reads, so the card and the plate cannot disagree. The card
renders NOTHING rather than a placeholder when they are absent.
⚠ Positioning moved from the card to a STACK, because two absolutely positioned cards would need two
sets of coordinates kept in step by hand.

**THE AGENT'S REASONING PLAYS ONCE PER VISIT.** A module-level flag, not React state: `EngineStage`
mounts the console with `{tab === 'live' && ...}`, so leaving the tab UNMOUNTS it and returning mounts
a new one, which state cannot survive. The run buttons no longer restart it either; they only record
whether the run was live, because the two paths have different completion signals. ⚠ That reverses a
considered decision recorded in the file, and the user named the case explicitly.

**THE CONSOLE'S BUTTON ROW.** "Download PDF" became **"Download this site's report"** (two buttons
reading "PDF" beside each other is a coin toss), and a new **"See what the agent found"** sits beside
it, switching to `schedule`, the first of the findings tabs. Outlined rather than filled: two
full-weight primaries side by side means neither is primary.

**THE RAIL HIGHLIGHTS EVERY ROW ON HOVER.** `.aa-tab:hover` only lifted the text colour while
`.aa-qa:hover` painted a background, so half the rail read as inert. Same fill for both now.

🔴 **AND A REGRESSION I INTRODUCED, CAUGHT BY THE CHECK COUNT RATHER THAN BY ANY FAILURE.**
`verify_intro` went from 208 checks to 204 with nothing red. Turning the four headline paragraphs into
list items changed the direct children of `[data-aa-hero="prose"]` from four `<p>` to one `<ul>`, and
`timeline.ts:SEL.prose` still said `> p`. It matched nothing, so **the four headline lines silently
dropped out of the hero reveal** and the probe wrote no entry for that target, so its assertions
removed themselves.
That is gotcha #74 in a new costume: a check that does not run reports success. Two fixes, and the
second matters more than the first:
* the selector is `> ul > li`, with a note saying what broke it;
* **the probe now reports every hero target whether or not it was found, and the Python side iterates
  over a NAMED list rather than over whatever the probe happened to return.** A missing target fails
  by name. 218 checks now, up from 208, because five "was found at all" assertions exist per run that
  did not before.
⚠ THE GENERAL RULE, worth carrying: never loop over what a probe found. Loop over what you require.

**THE LIVE AGENT WAS NEVER BROKEN.** The screenshots showing "Live agent not attached" are
`testing/serve_app.py` on port 8123, a static server with no `/api/` at all, which is the case
`drawLiveUnavailable()` exists for. Verified against the real server:
`serve_live.py --port 8131` answers `/api/health` with `key_present: true` and route parity at
`/app/api/health`; adding `--allow-paid` flips `live_available` to **true** with 250 offerable sites.
⚠ No POST was made, so no credits were spent: arming the SERVER is only the first of the two
independent keys.

**Verified:** `verify_intro.py` **218 checks, 0 failed**, `verify_launch.py` 68/0,
`verify_app_flow.py` PASS, `verify_app_deterministic.py` PASS, `verify_palette.py` 38/0, typecheck
clean, `sync_context.py --check` 0.
**Measured by eye and by probe:** the pick stage renders dark with no stored preference, configure
renders light, both cards sit right of the headline, and both ring end-labels are inside the loop.
Contrast measured on the new surfaces in both palettes: worst is `.aa-bubble-foot span` at 5.51:1 in
light. The count at 62px measures 4.25:1 in light, which PASSES its actual floor (3:1 for large text)
and was moved to `--fg-deep` anyway, the fifth time that remedy has been applied here.

### THE LAUNCH SEQUENCE: WHAT "INITIALIZE ARBITER" NOW STARTS. 2026-08-29

A timed cinematic. The screen deliberately does NOT change on the click: it holds on the globe through
the voiceover over a slow camera push-in, holds a beat, then crosses over to the site picker on a
whoosh. `intro/launch.ts` is new and owns all of it.

**MEASURED FIRST, AND THE FIRST MEASUREMENT CONTRADICTED THE BRIEF.** `tools/measure_audio.py` is new
and counts MPEG frames, because the sequence's beats are derived from the voiceover's length and an
approximation there compounds through the hold, the whoosh cue and the crossfade:

| file | frames | measured | the brief said |
|---|---:|---:|---|
| voiceover.mp3 | 179 | **4.676 s** | ~7 s |
| intro-swell.mp3 | 125 | 3.265 s | 3.2 s |
| transition-whoosh.mp3 | 75 | 1.959 s | 1.9 s |

🔴 **THE VOICEOVER IS 4.676 s, NOT 7 s, AND IT IS THE SAME FILE AS THIS MORNING** (identical frame
count), so the longer take the brief describes has not arrived. The sequence is built from the
measurement rather than the stated figure, because the brief's own rationale forbids the alternative:
"Do not play 9 seconds of silence", and 2.3 s of dead air before the hold is exactly that.
It is also SELF-HEALING: `resolve()` takes whichever is longer, the constant or the duration the
browser reports for the real element, so dropping in a 7 s take needs no code change. Reading a
duration cannot stall; waiting for one can, which is why that is a read and never a wait.
**Total today: 4.676 + 1.0 hold + 1.2 out = 6.876 s.** With a 7 s take it becomes the brief's 9.2 s.

**ONE TIMELINE OWNS THE VISUALS, AND NOTHING LISTENS TO AUDIO.** The brief's reasoning is kept in the
file: a cue that fails to load must not be able to stall the sequence, so there is no `ended` listener
anywhere and `playVoice()` / `playWhoosh()` are fired from timeline labels with their returns ignored.

🔴 **AND A WALL-CLOCK WATCHDOG OWNS COMPLETION, WHICH IS ONE STEP FURTHER THAN ASKED.** The brief
protects against audio stalling. This project has measured a second stall it does not mention: trap
5b.13, GSAP's clock failing to advance, which would leave a GSAP `onComplete` never firing and the
reader on the very dead screen the escape hatch exists for. So `finish()` is also scheduled on a plain
`setTimeout` at total + 400 ms and is idempotent. The division is clean: the TIMELINE owns what the
pixels do, a TIMER owns when the sequence is over.
⚠ That is not theoretical here. Under the virtual clock every other browser check uses, GSAP is frozen
and the watchdog is what completes the sequence, which is why `verify_intro.py` can still measure it at
all.

**THE ESCAPE HATCH IS UNDOCUMENTED AND BOUND FIRST.** Esc, Space or a click anywhere. Registered before
the timeline is built, so a throw in the timeline cannot strand the reader; idempotent, so five presses
queue one transition; and its 250 ms fade completes on a wall-clock timer rather than a tween's
callback, because the whole point of the path is to work when something is stuck.
**Nothing visible is rendered for it**, on instruction. `verify_launch.py` walks every displayed text
node AND every `aria-label` on the splash across three scenarios looking for the vocabulary a hint would
have to use, and finds none.

**THE PUSH-IN GOES THROUGH A REGISTRY, `intro/globeDolly.ts`, and it is a NUMBER not a camera.** 0 to 1,
where `HeatGlobe` decides what that means. It has to: the framing is solved from the container's
measured height and a resize re-solves it, so a timeline writing `camera.position.z` directly would be
overwritten by the next ResizeObserver tick and the push-in would snap back mid-sequence. `applyCamera()`
is now the only writer of that property. 16 % of the solved distance, measured 0.084 to 1.0 across the
sequence.

**FOUR REVERSALS OF EARLIER INSTRUCTIONS, all recorded where a future session will meet them:**

| was | now | where |
|---|---|---|
| narration plays on ARRIVAL, with an autoplay fallback | plays on the CLICK, and the fallback is unnecessary rather than unused | IntroGate.tsx header |
| the splash SWEEPS up, `translateY(-100%)` over 700 ms | fades and scales out over 1.2 s, timed against the whoosh | intro.css section 7 |
| SWELL_URL pointed at transition-whoosh.mp3 | `intro-swell.mp3` is the bed, the whoosh is its own cue | audio.ts |
| the hero entrance had an audio-synced beat map | always the SILENT map: the narration finishes before it starts | timeline.ts |

⚠ `ramp()`, `RAMP_MS`, `VOICE_LEAD_MS`, `DUCK` and `FADE_MS` are all DELETED rather than left unused.
The bed and the voice start together now, so there is nothing to fade up from and nothing to duck from,
and the gate's exit timing has one owner. Each deletion left a note saying what went and why.

**VERIFIED, and the six scenarios the brief named are each a section of the new
`testing/verify_launch.py`: 68 checks, 0 failed.** It is `run_all.py` step 37, and it runs on a REAL
clock (no virtual-time budget, `serve_app.py --hold 15`), which is the only way to reach a GSAP label.

| scenario | measured |
|---|---|
| normal run | gate still up at 200 ms with the button reading "Initializing"; voice at **+34 ms** after the click at 0.4, bed at 0.12; whoosh at **+5,841 ms** against 5,876 predicted; gone by the end, on the picker |
| push-in | dolly **0.084 at 200 ms to 0.99 at 5.2 s**, still 1.0 at 6.4 s, clamped |
| escape: Esc at 60 ms, before audio can have loaded | gate gone, picker showing, audio stopped |
| escape: Space at 2.2 s, click at 3.4 s, five presses at once | all four the same, nothing queued |
| no visible hint | **0 matches** across three scenarios and every sampled moment |
| muted | **+3,007 ms** to gone, against ~7 s for the audio path |
| every audio file 404ing | sequence completed, 0 thrown, 0 uncaught rejections |
| double click | voiceover played **exactly once** |
| navigate away mid-sequence | every element paused, pause actually issued |
| `?cinematic=off` | gate gone within the first sample, no audio at all |

**Also verified:** `verify_intro.py` **208 checks, 0 failed** (twice, for stability),
`verify_app_flow.py` PASS, `verify_palette.py` 38/0, typecheck clean, `sync_context.py --check` 0.

🔴 **FOUR PROCESS FAULTS OF MINE, EACH COSTING A ROUND, AND EACH ONE ALREADY IN THIS PACK.**
1. **Backticks in a GLSL comment closed the template literal** (trap 5b.21, written yesterday). Hit
   again in `launch.ts`'s neighbour while editing shaders.
2. **A heredoc ate `\\n` out of a regex** (trap 5.4, hit nine times before this). The patch file wrote
   `re.sub(r"//[^` and a real newline. Written with `chr()` and `re.escape()` now.
3. **A source scan matched the word in a COMMENT** (trap 5b.1). `launch.ts` explains at length why it
   does not chain off `audio.onended`, and the check searching for that name found the explanation and
   reported the opposite of the truth. Comments are masked before the scan now.
4. **A probe that could not report** (trap 5b.3). It published only from inside each scenario branch,
   so a throw meant no steps, no error, and "the probe ran: FAILED" with nothing to diagnose. There is
   an unconditional late publish now.
⚠ AND ONE THAT IS NEW: **`serve_app.py --hold` DELAYS DOMContentLoaded past the hold**, so a probe that
waits for that event publishes after the DOM has already been dumped. Poll for the element instead.
Recorded as trap 5b.22.

⚠ **AND I SHIPPED A FLAKY CHECK BEFORE CATCHING IT.** `verify_intro`'s settled sample sat 1.5 s past the
hero watchdog and failed one run in two on "the pulse is on screen". A check that passes half the time
is worse than no check. The margin is 4 s now and it was run twice to confirm.

⚠ **ONE THING A READER MIGHT MEET: the CTA is disabled until the three files report enough data**,
capped at 1,500 ms (`ARM_CAP_MS`). The brief asks for both "before the button becomes interactive" and
"if they haven't loaded when clicked, run without audio", and those pull against each other; the cap is
how both are honoured. With local files it resolves in a few milliseconds. It is also what made the
first version of `verify_launch.py` click into the void, because a disabled button silently ignores
`.click()`.

### THE HERO, FOURTH PASS: RATIOS NOT PIXELS, AND THE STAGE ROWS ARE GONE. 2026-08-29

**THE FRAMING WAS INVERTED, AND THE USER NAMED IT EXACTLY:** "The globe's top is clipped and the bottom
sits just inside the frame. The reference is the opposite." It was, and the cause was the previous
round's own spec: an ABSOLUTE pixel diameter of 980 to 1050 px, which assumed a 1080 px viewport. The
real container is **924 px** after browser chrome, so a 1,000 px sphere was 1.08 of H and the bottom gap
that had been solved for pushed the top out of frame.

🔴 **SO THE FRAMING IS NOW THREE RATIOS OF THE MEASURED CONTAINER, AND THE CAMERA IS DERIVED FROM THEM.**
That reverses the previous round's request for a single `CAMERA_Z` constant, at the user's instruction
("derive camera distance from the container's measured height so the ratio holds at any viewport size"),
and the reason is the flaw in the constant: a fixed distance ties apparent size to the CANVAS, and the
canvas follows the window's aspect ratio rather than its height.

    pxPerWorld = (diameterOfH * H) / 2      halfH = (side/2) / pxPerWorld      cameraZ = halfH / tan(FOV/2)

`FRAME` holds `diameterOfH: 0.90`, `centreOfW: 0.72`, `centreOfH: 0.66`, and `applyLayout()` solves the
rest from `host.clientWidth/Height` on mount and from the ResizeObserver. **Still the camera and never
`mesh.scale`**, for the reason the brief has now given twice: the atmosphere is a separate shell at a
fixed radius, so scaling the earth detaches the glow.

**MEASURED at a 1920 x 1020 window:**

| target | measured |
|---|---|
| container H, never assumed | **924 px** (W 1902), derived camera z **9.91** |
| diameter 0.90 x H | **832 px = 0.900 x H** |
| centre Y 0.66 x H, below the midpoint | **610 px = 0.660 x H** |
| centre X 0.72 x W | **1370 px = 0.720 x W** |
| clearance above about 0.20 x H | **194 px = 0.210 x H** |
| bottom limb cropped | **cropped by 102 px = 0.11 x H** |
| left limb fully visible | **x = 954**, 50.2 % across |
| lattice locked to the globe | apex at x = 780, 174 px left of the sphere's own limb, reframed with it |

⚠ **"CROPPED BY THE VIEWPORT RIGHT EDGE" DOES NOT HAPPEN AT THIS WINDOW, AND IT IS ARITHMETIC.** The
right edge sits at `0.72 W + 0.45 H`, so it is cropped only when `0.45 H > 0.28 W`, i.e. **W < 1.61 H**,
which at H = 924 is W < 1486. Measured, it stops **116 px short** of a 1902 px container. It IS cropped
on any window narrower than that. Flagged rather than quietly fixed because the two ratios it follows
from are both the user's; cropping it at 1902 wide needs centre X near 0.80 instead of 0.72. This is the
second round the same conflict has been reported.

**THE FIVE STAGE ROWS ARE REMOVED FROM THE PAGE**, at the user's instruction ("remove this", with a
screenshot). ⚠ **`components/StageRows.tsx` and `stagerows.css` ARE STILL ON DISK, deliberately**: the
instruction that moved them out of the hero was explicit that the component and its data wiring must not
be deleted, and the only reading that honours both is gone from the page, kept on disk. `App.tsx` no
longer imports it either, so it is tree-shaken out rather than shipped dead. Deleting the two files is a
decision the user can make in one line.
**verify_intro section 14 asserts BOTH halves** and is smaller than the two sections it replaces, which
is stated in the file: there is less product to check, and padding the count with checks of an absent
feature is the opposite of what these files are for. 228 checks became 206.

🔴 **THE USER REPLACED THE GENERATED AUDIO MID-SESSION, AND THE VERIFIER IS THE ONLY REASON IT WAS
NOTICED.** `demo/audio/swell.wav` and `chime.wav` disappeared and `transition-whoosh.mp3` appeared at
19:02. `verify_intro.py` failed on "demo/audio/swell.wav exists", which would otherwise have shipped as
a silent 404 behind `attempt()`'s catch.
`SWELL_URL` now points at the sourced file. **This supersedes standing rule C4**: that rule records
choosing a synthesised WAV because the brief wanted royalty-free stock and there is no MP3 encoder on
this machine, and a real sourced file is what was wanted all along. The constant keeps its NAME, because
"the swell" is the concept in a dozen places (the duck, the ramp, the lead) and renaming them to follow a
filename changes no behaviour. `tools/make_swell.py` is not deleted, so the generated version is
reproducible.
⚠ `CHIME_URL` still names an absent file, on purpose: the only caller of `chime()` is the unrendered
StageRows, which must keep compiling, and nothing requests the file while nothing renders it.

**THE CLOUD LAYER is at opacity 0.45**, up from 0.40, as asked. ⚠ Part of why it read as faint is not the
opacity: the light moved to the right during the lattice pass, so the left half of the planet is dimmer
and its clouds with it. That move is what lets a sparse pale grid read against the limb at all, so the
two pull against each other; the opacity is the free lever and it is at the requested value.

**Verified:** `verify_intro.py` **206 checks, 0 failed**, `verify_app_flow.py` PASS,
`verify_app_deterministic.py` PASS, `verify_palette.py` 38/0, `verify_shipped_app_is_current.py` PASS,
typecheck clean, `sync_context.py --check` 0.

### THE HERO, THIRD PASS: ONE SIZE KNOB, AND THE LATTICE IS A GRID NOW. 2026-08-29

Four corrections from the user, all four measured rather than eyeballed.

**1. THE PLANET IS SIZED BY ONE NAMED CONSTANT, `CAMERA_Z`, AND NOTHING ELSE TOUCHES ITS SIZE.**
Asked for by name. The camera moves; `mesh.scale` is never touched, and the brief is right about why
that matters: the atmosphere is a separate shell at a fixed radius, so scaling the earth would shrink
the planet and leave the glow floating at its old size.

    drawn diameter in px  =  canvas side / (CAMERA_Z * tan(FOV/2))

At `CAMERA_Z = 8.32` and a 1920 px canvas that is 999.6 px. **MEASURED at a true 1920x1080 viewport:**

| the brief's target | measured |
|---|---|
| diameter 980 to 1050 px | **1000 px** (0.926 x viewport height) |
| bottom limb visible, 40 to 80 px beneath | **60 px** |
| centre at about x = 72 % | **72.0 %** |
| left limb visible, curving through frame | **x = 883**, and the top limb is at y = 20, so the whole left arc is inside the frame |

⚠ **"CROPPED ON THE RIGHT EDGE ONLY" CANNOT HOLD AT THOSE NUMBERS, and it is arithmetic rather than a
miss.** A centre at 72 % of 1920 is x = 1382, so a sphere is cropped on the right only if
1382 + D/2 > 1920, i.e. **D > 1076**, which is above the stated 1050 ceiling. Measured, the sphere's
right edge lands at 1883, 37 px short of the viewport. What IS cropped is the atmosphere, which reaches
1928. Both numbers are the user's own and both were honoured; moving one of them is their call. To crop
the sphere itself the centre needs about 76 %, or the diameter needs to exceed 1076.

⚠ **AND THE WINDOW IS NOT THE VIEWPORT.** Measured in this headless build: `--window-size=1920,1080`
gives an INNER viewport of **1902x984**, because the browser keeps 18 px of width and 96 px of height.
The first run reported a 990 px diameter and a top limb at y = -61 (cropped) purely because of that,
and the numbers only made sense once the window was set to 1938x1176. `testing/shot_hero.py` now prints
the inner size every measurement is against.

**2. THE PARTICLE FIELD IS A LATTICE, AND RANDOMNESS WAS THE MISTAKE RATHER THAN THE DENSITY.**
The user: "a random, dense spray, it reads as confetti or static", against a reference that is "an
ordered lattice: regular rows and columns". A random field cannot have rows, so thinning it would never
have produced one. Every dot now sits at an exact `(u, v)` address on a 38 x 20 grid: **760 dots, down
from 1,900, which is the requested 60 % cut exactly.** Uniform size, low opacity, additive, and the
whole grid drifts as one rigid object so the rows stay legible while moving. No noise term anywhere in
the shape.

🔴 **THE SHEET'S GEOMETRY TOOK TWO ATTEMPTS AND A THIRD FIX.**
* **A cone slice about the funnel's axis** was the first. Geometrically a converging lattice, and it
  drew CONCENTRIC RINGS around the planet, because a cone seen end-on does. The rows were there and
  they arched over the top instead of arriving from the left.
* **A fan in the screen plane** replaced it: rows radiate from the apex, columns are arcs across them,
  plus a quadratic bow toward the camera for the "curved surface".
* **And that fan was invisible**, because its mouth landed at radius 0.70 from the planet's centre,
  i.e. INSIDE a unit sphere, so the depth test correctly hid most of it. The fix is a **radial clamp**:
  any point inside `HUG = 1.045` is pushed straight out along its own direction. So the sheet flows in
  flat and then HUGS the planet where it arrives, which is the brief's "wrapping toward the globe"
  written as three lines of arithmetic, and because the clamp is a radial scaling the lattice survives
  it: neighbours stay neighbours and rows stay rows.

⚠ The light moved right again (0.55 to 1.15 in x) and only because the lattice needed it: at
near-head-on the planet's left limb is its BRIGHTEST region and a sparse pale grid over it competed
with the ocean. The reference lights its globe from the right for the same reason.

**3. THE LEFT 38 % IS FREE OF PARTICLES, BY TWO MECHANISMS AND ONE MEASUREMENT.** The lattice is placed
to the right of the boundary, and the vertex shader independently fades any dot whose projected
position falls left of it, because a placement can be walked out of position by a resize and a
guarantee cannot. **Measured on the rendered PNG: 0 lattice pixels left of x = 736, 18,917 right of
it.**

🔴 **THE MEASUREMENT ITSELF WAS WRONG TWICE, AND BOTH FALSE ALARMS ARE WORTH KEEPING.** This is the only
one of the four requirements that cannot be measured from the DOM, since a shader leaves no trace in the
document, so it counts cyan pixels in the image. First version: 1,335 hits in a zone the lattice was
nowhere near, because the EYEBROW and the FortyGuard mark are painted `--fg-bright` #14a1e0 and are
cyan. Second version: 66 hits, all of them the antialiasing of "POWERED BY" at colours like
(130,130,159), where r EQUALS g. So the test is now three conditions, and the third is the one that
matters: a cyan dot has g well above r, and neither the type nor a grey does.

**4. THE ATMOSPHERE IS A THIN HALO. The user diagnosed the cause correctly** and it was this shader's
own low-rim tail: the shell is additive so it cannot darken anything, but at exponent 3.2 a point a
third of the way in still added about 0.5 % of full brightness over a very large area, which over
near-black reads as a dark navy band. Exponent **3.2 to 6.4** (that same point now contributes 4e-6)
and shell radius **1.15 to 1.09**, which caps how far out the band can reach at all, with intensity
raised 1.15 to 1.9 because a sharper falloff dims the arc that was already right.
**MEASURED on the render, scanning the centre row outward from the limb: the glow band is 22 px, 2.2 %
of the 1,000 px diameter.** The ambient went 0.6 to 0.78 as well, because part of what read as a dark
band is the PLANET's own unlit limb and no change to the shell can reach that.

🔴 **A NEW TRAP, HIT TWICE IN ONE SESSION: A BACKTICK IN A SHADER COMMENT CLOSES THE TEMPLATE LITERAL.**
The shaders are template literals, and a comment that quotes an identifier in backticks (`` `uHug` ``,
`` `HeatGlobe.tsx` ``) terminates the string mid-shader. The errors point at TypeScript syntax dozens of
lines away and say nothing about backticks. Recorded as `05-TRAPS` 5b.21 with the check: the file's
backtick count must be even.

⚠ **AND `tools/build_app.py` SAVED A ROUND BY SAYING SO.** The second backtick broke the build, the
tool printed "vite build failed, exit 1. Nothing was copied", and the screenshot that followed was of
the OLD bundle with figures that looked plausible. Without that line it would have read as a successful
run. The identical-PNG-size tell in the pack is the same lesson from the other side.

⚠ **ONE CHECK WAS FLAKY AND IS NOW SIGNAL-DRIVEN.** Section 14 sampled the stage rows 3,600 ms after
scrolling them into view, which is longer than the 2,320 ms the stagger needs and still failed once with
four of five rows settled: under a compressed clock the gap between the scroll and the
IntersectionObserver firing is not fixed, so any constant is a race. It now waits for every row to carry
`data-settled`. Trap 5b.4, paid for once already on the reasoning tape.

**Verified:** `verify_intro.py` **228 checks, 0 failed**, `verify_app_flow.py` PASS,
`verify_app_deterministic.py` PASS, `verify_palette.py` 38/0,
`verify_shipped_app_is_current.py` PASS, typecheck clean, `sync_context.py --check` 0.

### THE HERO IS FINISHED: FUNNEL, ROWS MOVED, BUTTON FIXED. 2026-08-29

All six steps of the brief are in. The globe entry below this one covers steps 1 and 2 and the three
measurements that got them right; this covers the rest.

**THE PARTICLE FUNNEL, `intro/funnel.ts`.** 1,900 particles under the brief's ~2,000 cap, one
`THREE.Points`, additive, converging to a point near the left edge and wrapping onto the planet's
limb.

🔴 **EVERY PARTICLE IS POSITIONED IN THE VERTEX SHADER, and that is the performance decision that
matters.** The obvious version walks a Float32Array on the CPU and re-uploads 22.8 KB every frame, on
the same main thread as React, GSAP and a MapLibre map. Here the buffer is written once and the only
per-frame data crossing the boundary is one float uniform. Each particle carries its own seed, and the
seeds come from a **hash of the index rather than `Math.random()`**, because this project renders the
same screen twice and requires the same result.

**THE FUNNEL FORCED THE GLOBE'S CANVAS AND ITS LIGHT TO CHANGE, and both are worth reading.**

1. **The canvas now covers the viewport, and the composition moved out of CSS entirely.** The strands
   converge near the LEFT EDGE while the planet sits to the right, so a square box positioned inside
   the viewport cannot hold both. CSS now decides one thing, `max(100vw, 100vh)` left-aligned and
   vertically centred; `HeatGlobe.tsx:applyLayout()` solves everything else from three fractions
   (diameter 1.35 of the height, left limb 35 % across, top limb 19 % down) and publishes what it
   solved on the canvas as `data-aa-sphere`. That removed a real coupling: the two files each used to
   hold half a guess about the other, with a comment in each telling the reader to keep them in step.
2. **The light moved from the left to slightly right of head-on.** Lit from the left, the planet's
   left limb is its BRIGHTEST region, and 1,900 small cyan dots over a bright ocean read as scattered
   noise. The supplied reference does not have that problem because its globe is lit from the right.
   ⚠ Two attempts at the fan were wrong first: ending it at -0.55 spread it across the whole visible
   disc, which is dots ON the globe rather than the brief's "wrapping toward" it. -0.88 terminates it
   just inside the left surface, so the near half crosses the limb and the far half is occluded.

**THE FIVE STAGE ROWS MOVED BELOW THE MAP**, `components/StageRows.tsx` and `stagerows.css`. Nothing
was deleted: the data, icons, notes, timestamps, stagger and chime all went across.
🔴 **THEY LIVE OUTSIDE `intro/` ON PURPOSE.** `?motion=off` unmounts everything in that folder, and
these rows are the only plain-language account of the loop on the landing page, so they are CONTENT
and must survive every kill switch. Rendered by `App.tsx` inside `[data-show="pick"]`, which
`setStage()` hides exactly like the rest of the pick screen. The stagger starts on an
IntersectionObserver rather than on mount, because below the fold a mount-time stagger plays out while
the reader is still looking at the hero and every timestamp would read page-load time.
⚠ **THE CHIME CAME WITH THEM, and that is a judgement call.** `CHIME_ON_ARRIVAL` in StageRows.tsx
turns it off on its own.

🔴 **AND A REAL PRODUCT DEFECT THE VERIFIER FOUND: AN ANIMATION CLOCK CAN LEAVE A SECTION INVISIBLE
FOR EVER.** `verify_intro.py` measured all five rows at opacity 0. This is trap 5b.13, which the pack
recorded for GSAP, and it applies to **CSS animations** too: while an animation is in its active phase
it overrides the element's declared style, so a frozen clock holds the `from` keyframe, which here is
`opacity: 0`.
⚠ **MY FIRST FIX WAS WRONG AND CHANGED NOTHING.** I removed `animation-fill-mode: both`, reasoning
that the fill was what held the from-state. Fill mode is irrelevant: the animation is ACTIVE, not
before or after its range. The fix is a wall-clock `setTimeout` watchdog that marks each row
`data-settled`, and CSS cancels the animation for a settled row, so the element falls back to its own
declared style, which IS the finished state. Same shape as `intro/timeline.ts`'s watchdog. The check
now asserts the END STATE, which is the only honest thing to assert about an animation.

**THE SHINY BUTTON WAS NEVER WRONG. `tones.css` WAS.** The user: "The current button is a generic
purple/blue gradient pill with a heavy outline. That is not the component I picked." Measured on the
rendered button: the component's own CSS was intact and `[role='dialog'] button` was overriding it.
That rule sets `background` as the **shorthand** with `!important`, so it did not tint the component,
it REPLACED its entire background: `background-image: none` and a flat `oklab(... / 0.12)` wash where
a black `padding-box` fill and a rotating conic `border-box` gradient belong. Its own comment says it
was written for "Its Close button, which was a hairline box on glass", so the fix is
`[role='dialog'] button:not(.shiny-cta)` at that rule rather than a louder rule elsewhere. Measured
after: 18.37:1 on its declared `--shiny-cta-bg`.
⚠ Nothing in the pasted component changed. The two adaptations remain the two already recorded:
`<style jsx>` is Next-only so the CSS is a co-located stylesheet, and the Google Fonts `@import` is
gone because Inter is self-hosted and offline operation is required.

🔴 **THE MOBILE AND REDUCED-MOTION GLOBE CODE IS DEFENSIVE, NOT OBSERVABLE, AND THAT IS WORTH
KNOWING.** Measured at 504 px and with `prefers-reduced-motion=reduce`: **the splash does not render
at all** in either case, so the globe never mounts and its narrow and reduced branches are unreachable
on a fresh load. That is `flags.ts:gateEnabled()` doing what an earlier instruction of the user's asked
("Mobile (<768px): skip the enter gate entirely"), not something this work changed. The branches exist
for a wide session dragged narrow. What a phone and a reduced-motion reader DO get, measured: the five
stage rows present and static (`animationName: none`, `opacity: 1`), the note column dropped at narrow
width, Configure reachable, zero JS errors.

**THE COST, MEASURED against the committed bundle:**

| | before | after | delta |
|---|---:|---:|---|
| `index-*.js` gzipped | 428,213 B | 625,437 B | **+197,224 B, +46.1 %** |
| `index-*.css` gzipped | 36,921 B | 39,985 B | +3,064 B, +8.3 % |
| textures, landing stage only | 0 | 1,247,161 B | +1.19 MB |

**Verified after:** `verify_intro.py` **228 checks, 0 failed** (was 207; sections 14 and 15 are new),
`verify_app_flow.py` PASS, `verify_app_deterministic.py` PASS, `verify_palette.py` 38/0, typecheck
clean, `sync_context.py --check` 0.

⚠ **I HIT TWO OF THIS PACK'S OWN TRAPS WHILE DOING THIS**, both recorded because they cost a round
each: `tools/build_app.py` run from inside `app/` does nothing and the grep for "copied" matches
nothing (05-TRAPS 5.3, and the build-from-root note), and the shell's working directory persists
between calls so a bare filename resolves against the wrong folder.

### THE HERO IS A THREE.JS EARTH NOW, AND cobe IS UNINSTALLED. 2026-08-29

**THIS WAS THE CHECKPOINT AT STEP 2 OF 6**, taken at the user's instruction: *"Stop after step 2 and
show me a screenshot before continuing. The globe is the piece most likely to come out wrong."* They
then said go, and the entry ABOVE this one covers steps 3 to 6. Kept as its own entry because the
three measurements it records are about the globe alone.

**WHAT "THE HERO" IS, because the word does not appear anywhere in this codebase.** It is the SPLASH,
`intro/IntroGate.tsx`, matched by its contents: eyebrow, wordmark, subhead, CTA, FortyGuard mark. Not
the masthead, and not `demo/index.html`.

**THE GLOBE IS A COMPLETE REPLACEMENT, NOT A RETUNE**, which is what the brief asked for and is also
the only thing that could have worked: cobe takes no texture input at all (it rasterises a dot matrix
from a landmass mask), has no light and therefore no terminator, and its glow is a flat halo rather
than a fresnel. `HeatGlobe.tsx` is now Three.js: a 64x64 sphere with the day, normal and specular
maps, a cloud shell at 1.01 read as an alphaMap, and an atmosphere at 1.15 rendered `BackSide` with a
custom fresnel shader, additively blended.

🔴 **THE HERO IS PINNED TO THE DARK PALETTE IN BOTH THEMES, AND THAT IS ARITHMETIC RATHER THAN
TASTE.** The rim glow is ADDITIVE, so on the light theme's `#fafafa` every channel is already at 250
of 255 and adding cyan moves nothing. That is also the explanation for the flat look reported on the
cobe version. Done by re-declaring the dark values as LOCALS on `.aa-splash` so every existing rule
keeps reading `var(--text-primary)` and resolves correctly, rather than naming elements one by one,
which is the popover-text lesson. ⚠ The two light-theme contrast remedies had to be UNDONE: `--fg-deep`
is 2.48:1 on the new floor and the dark `--fg-bright` is 6.58:1, so the remedy became the failure.

**THREE THINGS WERE MEASURED, AND ALL THREE FIRST ATTEMPTS WERE WRONG.**

| what | first attempt | what the measurement said |
|---|---|---|
| the framing | sphere overflowing its own canvas by 8 % | it clipped the ATMOSPHERE at the canvas edge, leaving a straight vertical line where a curved rim belongs. The crop belongs to the VIEWPORT: camera pulled to d=5.41 so sphere plus atmosphere fit the square at 80 %, and the square is simply bigger than the window |
| the start longitude | derived from three's SphereGeometry: `L = -90 - a*180/PI` | wrong. At a=0.53 the rendered centre is +5 E, not -120. Measured at two points instead: 0.53 -> +5 E, 1.53 -> -52 E, so `L = 35.4 - a*180/PI` and facing -85 E needs **2.101** |
| the canvas box | width and height both set to one custom property | `max-width: 100%` survives from section 7 and squashed it to **1382x1426**, an Earth drawn as an oval. `verify_intro.py` caught it, not a look |

**THE NORMAL MAP IS THE ONE ASSET THAT CANNOT BE JPEG.** Measured on the source TIFF: stddev
**1.36 of 255** with the blue channel a constant 255, because Earth's relief is 9 km on a 6,371 km
radius and a correctly scaled normal map is nearly flat. It therefore has to be amplified
(`normalScale` 2.8), and q88 JPEG had already destroyed a quarter of the signal (stddev 1.36 to 1.00).
It ships as lossless PNG. `tools/make_earth_textures.py` prints the stddev of every file it writes for
exactly this reason: a texture that encoded to a plausible number of bytes and lost its detail looks
like a success otherwise.

**THE COST, STATED RATHER THAN BURIED.** Three.js is the largest dependency in this app and the
previous cobe argument was right on its own terms:

| | before | after | delta |
|---|---:|---:|---|
| `index-*.js` gzipped | 428,213 B | 622,680 B | **+194,467 B, +45.4 %** |
| `index-*.css` gzipped | 36,921 B | 39,986 B | +3,065 B, +8.3 % |
| textures, landing stage only | 0 | 1,247,161 B | +1.19 MB |

So a first visit carries about **1.39 MB more**, which takes the full journey from the 5.11 MB
measured on 2026-08-28 to about 6.5 MB, and Render's 5 GiB monthly allowance from about 1,051
journeys to about **825**. Bandwidth is the one genuinely billable axis on that plan, so this is worth
watching rather than filing.

**Verified after:** `verify_intro.py` **207 checks, 0 failed**, `verify_app_flow.py` PASS,
`verify_app_deterministic.py` PASS, `verify_palette.py` 38/0, typecheck clean. The palette check is
unaffected because it reads `app/src/index.css` and the pinned values are locals in `intro.css`.

⚠ **THE MEASURING HARNESS IS NOT `render_shots.py`, AND CANNOT BE.** That tool passes
`--force-prefers-reduced-motion=reduce`, and `flags.gateEnabled()` returns false under it, so every
shot it takes is of the page BEHIND the splash. `scratchpad/shot_hero.py` is the one that sees the
hero: same `--hold` plus virtual-time-budget mechanism, without that flag.

### THE LIVE RUN HAD NO DOWNLOAD, AND THE CONFIG COLUMN COULD NOT SCROLL ITSELF. 2026-08-29

**THE REPORT BUTTON WAS GATED ON THE WRONG SIGNAL, and it was my gate.** The user ran the agent live
on Ashburn twice and had nothing to download. `AgentConsole.tsx` resolved its ready state on
`tapeDone()`, which reads `#tapedone` -- and that element is written by `streamTape()`, the REPLAY
path. A live run never touches it, so `phase` stayed `reasoning` for as long as the tab was open and
the entire button row, Download PDF included, never rendered at all.

Fixed in two places, because one of them was the wrong home for it:

* the offer now lives at the END OF THE LIVE OUTPUT, in `#livereport`, written by `drawLive()` --
  the function that actually knows a live run finished. That is also where the user asked for it.
* the console additionally gets `liveDone()` (the summary line, or a row in the schedule table) and
  chooses `wasLive ? liveDone() : tapeDone()`, so its own row appears for a live run too.

`testing/verify_live_report_button.py` (run_all step 35) checks BOTH halves, because either alone
would be a false pass: a button pointing at a broken route, and a working route with no button, look
identical from one side. 25 checks, 0 failed, and it runs on a REPLAY fixture so it costs nothing.
The PDF comes back at 14,970 bytes with a complete `%%EOF` trailer, by job id and as `latest`, at
`/api/...` and at `/app/api/...`.

⚠ Choosing that fixture took three attempts, and the failures were mine not the product's. Any
populated fixture drew one from another metro, the run returned `fixture_mismatch`, and the report
route REFUSED to build a PDF with no schedule, which is exactly right. Filtering on "ashburn" in the
filename matched nothing, because the usable fixtures are named for the experiment that bought them.
The picker now asks the question the code asks: nearest tile within `MAX_TILE_DIST_M`. 31.5 m.

**THE CONFIGURATION COLUMN, MEASURED BEFORE TOUCHED.** The user: *"even if I scroll up all the way in
the bar itself, it doesn't show till the top of the bar unless I scroll the page itself up too."*
`scratchpad/probe_railscroll.py` walked the scroll chain at 1502x904:

    *** aside.sidebar          876/832   rect 268..1102   max-height 834px
    *** div.aa-workspace-main  834/636   rect 268..904

Two nested scrollers. The sidebar's own scrollbar covered 44px of overflow while its box ran 198px
past the bottom of the viewport, so the remaining 198px belonged to the container behind it.

**THE PAGE'S VALUE IS CORRECT FOR THE PAGE.** `index.html:896` is
`max-height: calc(100vh - var(--bezel-h) - var(--sp-5))`, and on the single-file page the WINDOW is
the scrollport and the sidebar sticks under a fixed bezel, so 100vh is the right basis. In the app
the scrollport is `.aa-workspace-main`, which begins below the masthead AND the tab header, so 100vh
overstates it by the height of both. A fixed correction would be a guess at the masthead; instead
`EngineStage.tsx` publishes `--aa-scrollport` from that container's measured `clientHeight` on a
ResizeObserver, and `lastmile.css` rule 6 reads it. `top: 0` too, since the bezel offset does not
exist in this layout.

Re-measured after: sidebar `876/616`, `rect 268..886` inside a 904 viewport, and
`.aa-workspace-main` at `636/636` **no longer scrolls at all**. One scroller, 260px of it, all of it
on the bar's own scrollbar.

### THE CINEMATIC INTRO LAYER, AND IT IS A NEW SUBSYSTEM. 2026-08-29

Six commissioned steps plus a rework, all in `AGENTIC-ARBITER/app/src/intro/`, which did not exist
this morning. It is the landing stage's opening: a splash screen with a rotating globe, a narrated
voiceover, a staggered widget load, an animated agent-loop diagram, a heat-field background and a
scroll handoff into the static technical content.

⚠ THIS PACK WENT SIX STEPS WITHOUT A SINGLE MENTION OF IT, and the user had to ask. The ritual in
`00-START-HERE.md` section 4 is part of the change, not a thing done afterwards, and it was not
followed. Recorded here because the failure is more useful than a silent correction.

**WHAT IS THERE**, and `02-ARCHITECTURE.md` section 8 describes each file:
`flags.ts` (two kill switches), `audio.ts` (voiceover, swell, chime, duck, teardown),
`IntroGate.tsx` (the splash), `IntroLayer.tsx` (the one mount point and all cleanup),
`timeline.ts` (the GSAP entrance, the ambient loops, the scroll handoff), `Pipeline.tsx` (the
five-stage loop), `HeatGlobe.tsx` (cobe), `ThermalField.tsx` (the CSS background), `intro.css`.
Plus `components/ui/shiny-button.tsx` and its stylesheet.

**THE TWO KILL SWITCHES ARE THE MOST IMPORTANT THING TO KNOW.** `?motion=off` mounts nothing from
`intro/` at all, and `?audio=off` silences it. `verify_app_flow.py` and `verify_app_deterministic.py`
both run with `&motion=off`, because the splash is a full-viewport overlay and would otherwise
swallow the Configure click those checks depend on. They are also how to demo without either.

**AUDIO.** The user supplied `demo/audio/voiceover.mp3`, measured from its own MPEG frame headers at
**4.676 s** (179 frames of 1152 samples, 44.1 kHz CBR 128 kbps). `swell.wav` and `chime.wav` are
SYNTHESISED by `tools/make_swell.py` -- there is no MP3 encoder on this machine and a generated tone
has no licence to be wrong about. 226 KB combined, inside the 300 KB budget. Every audio beat in
`timeline.ts` is DERIVED from the measured duration; the sentence positions are the one estimated
number and are apportioned by syllable, which the file says out loud.

**THE SPLASH REWORK, 2026-08-29 (later).** The enter gate became a splash: cobe globe, the supplied
ShinyButton as the CTA, five widgets staggering in with lucide icons and live `HH:MM:SS.mmm`
timestamps and a chime as each SETTLES, a 700 ms `translateY(-100%)` sweep, and `hasSeenSplash` in
sessionStorage. Two instructions were reversed by the user and both are recorded in
`04-STANDING-RULES.md` section C3 so nobody "restores" them.

**GLOBE MARKERS ARE REAL PLACES.** Eleven facilities read out of `demo/sites.json` bounding boxes,
with arcs all leaving Ashburn because that is the site whose calibration the others borrow. Nothing on
the splash states a figure from an artefact, deliberately: it is the first thing a judge sees and the
one thing it must not do is show a value that has drifted.

**BUNDLE.** 473 KB gzipped before any of this, **500 KB** after. cobe is 18.8 KB with zero
dependencies; `react-globe.gl` would have been 250-400 KB gzipped because it pulls Three.js.

### A FIVE-DIMENSION REVIEW OF THE INTRO LAYER: 21 OF 36 FINDINGS CONFIRMED. 2026-08-29

Run as a workflow, every finding adversarially verified before it reached me. 15 were dismissed.

**FIXED (all three high, plus two mediums):**
* the hero text reveal never ran on mobile -- the entrance was gated on `flags.gate`, and
  `gateEnabled()` is false under 768px, so a phone got NO intro motion at all. It is the one thing the
  brief's mobile clause says to KEEP. Now a `'headline'` variant from a `useLayoutEffect`, which runs
  before paint so there is no from-state flash without a gate to cover it;
* the corner mute toggle's `aria-label` was an ACTION while `aria-pressed` was a STATE, so a screen
  reader announced "Turn the introduction sound on, toggle button, pressed";
* the splash declared `aria-modal` with no focus containment, so Tab walked onto controls hidden
  behind an opaque overlay;
* `opacity: 0.72` on the gate toggle's pressed state (~2.4:1 dark, 2.1:1 light);
* `?audio=off` was written to localStorage, turning a per-load demo switch into a permanent
  preference.

**STILL OPEN, 16, and one cluster matters more than the rest:** returning to the landing stage (via
"Choose a different site" or `#backtopick`) never re-arms the intro, so the pulse and the scroll
handoff are dead for the rest of the session. Then: ScrollTrigger's global machinery installed at
import time and never disabled; 31 of 55 `intro.css` rules not anchored to `body[data-aa-intro]`
despite the file claiming they all are; reduced-motion overrides that lose on specificity; `kill()`
clearing props on selectors React has already removed.

### THE SPEND DRIFTED AND THE AUDIT IS FAILING. IT IS NOT THE INTRO. 2026-08-29

The user's live runs moved the meter. Current, and it reconciles to the credit:
**267 heatmap x 4,220 + 14 env_params x 2,900 = 1,167,340**, remaining **832,660**, **58.37 %** used,
281 calls.

Two things follow, and only one of them is cosmetic:
1. `README.md:603` -- the file index a judge reads -- says **"13 calls, 54,860 credits, 2.74 %"**. It
   was right when 13 calls had been made and has never been updated, because `audit.py` registers the
   spend figures in API-USAGE.md and HANDOFF.md ONLY. See trap 5b.19.
2. `testing/bump_spend_docs.py` REFUSES to write, correctly: API-USAGE.md section 3 closes with "those
   three rows sum to ...", and they now come to 1,166,820 against a headline of 1,167,340 -- **520
   short**. `api_usage_ledger.py:350-354` divides gap credits by the heatmap price with integer
   division, so any `env_params` call (2,900) inside an unattributed gap loses its remainder.

⚠ NOTHING WAS HAND-EDITED TO MAKE THE AUDIT PASS. That would be exactly the unverified claim the rule
exists to prevent. The fix is to correct the ledger's classification and to add README.md to the
spend check, and it is waiting on the user's go.

### THE STOP CONTROL: what "Stop agent now" can and cannot save. 2026-08-29

The user asked for a red force-stop beside the live run. The honest version of that button is an
arithmetic one, because FortyGuard bills at SUBMIT and not at poll. `API-USAGE.md`'s measured table:
`POST /v1/heatmap` **4,220 credits**, `GET /v1/status/{id}` **free**, "unchanged meter across 59
polls". `perceive_ambient()` is submit-then-poll. So:

* stopping **before** a submit saves 4,220 credits every time. That is where the button earns its
  keep, and that is where the checks are placed.
* stopping **during** the poll saves nothing, and abandoning the loop would forfeit windows already
  billed. So a stop takes **one more free reading** instead, and each window that lands is written to
  the cache: credits already spent still buy data a later run gets for nothing.

`POST /api/live/stop/<job_id>` sets a flag that the worker reads between windows. A flag, not a
thread kill: the run is mid-spend, and a killed thread could lose the record of a call that was
already billed. An unrecorded 4,220 credits is the one outcome worse than a slow stop.

`testing/verify_stop_control.py` (run_all step 34) proves it at **zero credits**, stubbing the two
functions that reach the vendor, and the assertion is a CALL COUNT rather than a flag: stopped after
2 of 12 submits, `submit_window` is called exactly **2** times and 10 windows come back
`stopped_by_operator`, which is **42,200 credits not spent**. 29 checks, 0 failed.

`#livego` and `#livecard` are untouched (standing rule C1). `#livestop` is additive and hidden until a
run is in flight. Outlined red rather than filled: the palette comment above `--critical` says it
"never appears as a bare mark, only as ink on a figure that also carries the word FAILED", and red ink
on a control labelled Stop keeps that promise where a red slab would not.

⚠ A stop pressed during the opening POST used to be droppable, since there was no job id yet to name
in the request. `STOPWANTED` holds it and the request goes out the moment an id exists.

### THE WIND ATTRIBUTION WAS WRONG TWICE, AND THE SECOND TIME WAS MINE. 2026-08-29

Every free-cooling explanation ended *"...given the wind-direction error **FortyGuard** actually
has."* The user caught it, and I changed it to name **NWS**. That was wrong too, and the user caught
that as well, with the question that settles it: *what error? why is there error? how did we
categorize an open source's data as "error"?*

**IT IS NOBODY'S FORECAST ERROR.** `SIGMA_DIR_DEG = [47.0, 72.0]` (`agent.py:196`) is the
**persistence** error of wind direction: the spread between the direction at the decision hour and the
direction L hours earlier, from **KIAD ASOS observations**, 1,619 hours over 72 days, cached in
`testing/results/fixtures/n40_kiad_dir_errors.json`. Both terms are OBSERVATIONS from one station, so
no forecaster appears in the measurement at all. The fixture states the intent itself:
`"why_lower_bound": "any real forecast beats persistence; this understates skill"`.

So naming NWS was the same category error as naming FortyGuard, aimed at a different party:
persistence UNDERSTATES forecast skill, therefore OVERSTATES the error of any real forecaster.
`live.py:51` already states the correct principle for the temperature margin, "calibrated on de-biased
*persistence* errors: those describe a different forecaster", and the direction margin was doing the
exact borrowing that warns against.

**THE STATIC PATH'S WIND IS NOT NWS EITHER.** NWS supplies wind only in the LIVE path;
`agent.py:307` `load_hours()` reads 43,763 real **KIAD ASOS** hours. The sentence named the wrong
source even about which source it was describing.

47 and 72 are **lead 2 h (47.33 deg) and lead 10 h (71.58 deg)**, the min and max over leads 1-12 h.
They are NOT the horizon endpoints: lead 1 h is 52.0 and lead 12 h is 71.0. Reading "47-72" as "1 h to
12 h" is reading it wrong.

Now, naming no one: *"how far the plume could move if the wind direction differs from the one planned
for, at the **measured spread of wind direction over this lead time**."*

**THE BLAST RADIUS WAS 500 FILES, AND THE PDF WAS THE ONE THAT MATTERED.** Three adversarial skeptics
(0 of 3 refuted) plus five parallel sweeps found 19 inaccurate sites, 11 of them reader-facing. The
earlier HTML fix had touched ONE. `explain.py:139` still said *"the amount FortyGuard's forecast is
actually off by"*, and `report.py:446` renders that string verbatim into the PDF a judge downloads.
The same sentence was baked into **500 shipped `*_explanations.json` artefacts**, and
`plume_uncertainty.py:307` wrote `"source_of_sigma_dir": "N-40 measured FortyGuard wind-direction
forecast error"` into **82** more. All patched, generator and data together, so a regeneration
reproduces the corrected text.

⚠ **FIXING THE PAGE IS NOT FIXING THE CLAIM.** The page is one renderer. `explain.py` is the source
the PDF shares, and the explanation artefacts are precomputed and shipped. Grepping the SENTENCE would
have found all 500 the first time. I greped the page.

**VRAM is gone entirely**, including from the comment that explained it, so a grep finds nothing in
the page, the lifted markup or the shipped bundle.

### POPUP TEXT: THE BUG WAS LISTING TAGS, AND THE FIX IS MEASURED

The popups are dark in BOTH themes. My earlier rule named `p`, `li`, `strong`, `b`, `h3`, `h4`, so
everything else inherited the PAGE's colour: near-black on near-black in light, fine in dark. The
heading "One hour, all seven stages of the loop" is a **`<summary>`** and was invisible.

🔴 **NAMING TAGS WAS THE MISTAKE.** The colour is now set on the container and inherited, with the
deliberate accents re-stated after it. A tag nobody remembers can no longer go invisible.

**AND CONTRAST IS NOW ASSERTED.** The user's instruction was "see the actual rendered screen's shot
yourself before approving color choices". Better than looking: `verify_app_flow.py` opens a dialog and
computes the WCAG contrast ratio of every leaf text node against the dialog's own painted background,
failing under 3:1. **Worst is 7.31:1 over 8 nodes.**
⚠ Writing that check, I declared `var txt` inside a loop, which hoists to the whole enclosing function
and shadowed the probe's own `txt(selector)` helper; step 1 died with "txt is not a function".

### THE CONTROL STRIP FLOATED OVER ITS OWN CARD

`engine.css:266` is `.filters { position: sticky; top: 0; z-index: 20 }`. Right on the single-file
page, where one long scroll means the controls stay reachable. Inside a tab the panels have their own
scroll container, so a sticky strip rides up over its own card: the alpha and n selects of the
conformal panel sat on top of the cards below them. Un-stuck for strips inside engine cards ONLY; the
pick screen's filter bar keeps the sticky behaviour App.tsx documents as deliberate.

Also this round: the FortyGuard mark gets a saturation and contrast lift in the LIGHT theme, where it
had none and washed out; the banner reserves 52px so the stepper stops running under the fixed theme
toggle; and the measured-coverage figure in the Self-Scoring panel is green, scoped to `#covtiles` so
every other `crit` tone keeps its warning colour. `engine.mjs:2531` derives that tone from
`coverage < 0.90` and its comment is right to; what the red IMPLIED was fault, and the cause is 4
calibration day-pairs capping attainable coverage at 80.0 %.

### 🔴 THE REAL CAUSE OF THE SCROLL FAULTS WAS MAPLIBRE, AND I FIXED TWO WRONG THINGS FIRST

The user's report after my first fix: "the website loads with an already scrolled page. What have you
fixed? Fix this issue accurately for once please." Fair. Two guesses preceded the measurement.

**What it actually is.** `scratchpad/reloadprobe.py`, now `testing/probe_reload_scroll.py`, patched
`scrollTo`, `scrollIntoView` and `focus` and sampled `scrollY` every 20 ms:

```
focus on maplibregl-popup-close-button (+287ms)   y=0
   at HTMLElement.focus ... at AA._focusFirstElement ...
*** LEFT THE TOP *** (+307ms)                     y=501
```

**MapLibre opens a popup and calls its own `_focusFirstElement()`, focusing the close button; the
browser scrolls that element into view and drags the page to 501.** A facility is preselected, so the
popup opens on load and the first screen arrives scrolled past the headline. `focusAfterOpen: false`
on both `new Popup(...)` in SiteMap.tsx. **Measured after: scrollY 0 at every sample to +4500 ms.**

It is also the other half of the ALTERNATING jump on changing site: the popup pulled DOWN to the map
while `setStage`'s scroll-to-top pulled UP, and which one won depended on ordering. One cause, two
symptoms, and my first fix addressed only the second.

⚠ **THE TWO WRONG GUESSES, KEPT BECAUSE BOTH CHANGES ARE STILL CORRECT ON THEIR OWN MERITS.**
1. `setStage` scrolling to top on a no-op re-run is real, and `noscrolljump.ts` should suppress it.
   That fix was right; it just was not the whole cause.
2. `history.scrollRestoration = 'manual'` is right too, and it changed NOTHING here: the probe showed
   `restoration: manual` and `finalY: 501` on the same run. Recorded because a fix that makes no
   difference is worth knowing about rather than quietly crediting.

**Three assertions now, where there were none.** `verify_app_flow.py`: the first screen loads at
`scrollY` 0; every tab is entered at `scrollTop` 0 having deliberately left its predecessor at 400.
Nothing in the suite looked at a scroll position before this.

### TWO SCROLL FAULTS, BOTH FOUND BY INSTRUMENTING RATHER THAN GUESSING. 2026-08-29

**1. Changing the selected facility threw the window to the top**, so the map and the filters left
the viewport. It ALTERNATED, which is what made it look mysterious.

`scratchpad/scrollprobe.py` patched `window.scrollTo`, `scrollBy`, `scrollIntoView` and `focus`,
drove three facility changes and recorded the stacks. One line answered it:

```
window.scrollTo arg={"top":0,"behavior":...}   at Module.ad [as setStage]   y=452 -> 0
```

**engine.mjs:138**, the last line of `setStage()`:
`window.scrollTo({top:0, behavior: next==='pick' ? 'auto' : 'smooth'});`

That is RIGHT for a real transition and wrong for a no-op re-run, and the engine re-runs setStage with
the stage it is already on deliberately, in more than one place: `probeLive()` ends with
`if(STAGE) setStage(STAGE);` precisely so that one function stays the single owner of visibility.

**`app/src/lib/noscrolljump.ts`** swallows a scroll-to-top ONLY when `body.dataset.stage` is unchanged
since the last one that was allowed through. A genuine pick to configure to results transition still
scrolls. Any scroll to a target other than the very top, any scroll the reader causes, and every
`scrollIntoView` pass through untouched, which matters because `#boundmore` relies on one.
A shim rather than a one-line edit to the engine, because step 30 asserts engine.mjs character for
character against the page.
**Measured before: y=520 became 0 and stayed. After: y=452 held across all three changes.**

**2. A tab opened part-scrolled if the previous tab had been scrolled.** `.aa-workspace-main` is ONE
scroll container shared by all six tabs, so its `scrollTop` survived the change. Reset in EngineStage
on every `tab` change, with `behavior: instant` because a smooth scroll would animate through the
panels of the tab being left.
**Now asserted permanently:** the flow check's tab walk leaves each container at 400 before moving on,
so every tab is entered from a scrolled predecessor, and reports "6 tab(s) entered at scrollTop 0".

### THE LIVE RUN'S OWN REPORT, and the popup and bubble work. 2026-08-29

⚠ **THESE ENTRIES ARE LATE, AND THAT IS THE POINT OF RECORDING IT.** Three rounds of work went in with
their narrative in the COMMIT MESSAGE only. `sync_context.py --write` ran each time, which regenerates
the derived figures and says nothing about prose, so `--check` passed while 01-STATE.md said nothing
about any of it. CLAUDE.md is explicit that the change-log entry is "yours to write". Running the tool
is not the same as updating the pack.

**`src/live_report.py`** writes a PDF about ONE live run from the job that produced it: the config it
used, what it spent, the schedule hour by hour, THE REASONING hour by hour, the seven stages as they
streamed, and what it does not cover. Served at `/api/live/report/<job_id>`, with `latest` resolving to
the most recent finished job so the browser can ask without the engine exposing its job id.
⚠ On a shared host `latest` is whoever ran last; the content is a weather schedule, and the explicit
`/<job_id>` form exists for a caller that has one.

**Helvetica for prose, Courier for the table.** The writer wraps by arithmetic because every Courier
glyph is 600/1000 em, and Helvetica's metrics are not in this repository. Wrapping Helvetica on
Courier's metric is CONSERVATIVE: Helvetica averages about 0.5 em, so a line that measures as fitting
is narrower once set and cannot run past the margin. The table stays Courier because a column of
figures wants a fixed advance.
⚠ **INTER IS DEFERRED, NOT FORGOTTEN.** It needs TrueType embedding by hand: descriptor, embedded font
stream, a `/Widths` array and the real advance table parsed out of the woff2, replacing the
exact-arithmetic wrapping the writer depends on.

**A report that fails its own read-back is not served.** Two bugs in that verifier, both found by
running it: it looked for mixed-case section text when `Pdf.heading()` UPPERCASES, and its
forbidden-token test fired on the word **"provenance"**, which contains "nan". Word boundaries now.

**All FOUR floating-surface kinds now share one dark treatment**, and each was found separately, which
is why the rule grew three times: `.info-bub` (the engine's), `[role='note']` (React's Info.tsx, which
is what the masthead actually uses), `[role='listbox']` (the Combo dropdown) and `[role='dialog']` (the
DetailModal). All four carried `.glass`.

**The scope is a drifting bubble**, points not sentences, 250 at `clamp(40px,5.4vw,62px)`, both counts
read from the artefacts. **The FortyGuard mark is at full ink and labelled "Powered by"**: a bare
wordmark above a product called AGENTIC-ARBITER reads as though FortyGuard built it, which is not true.

🔴 **AND A GIT LESSON THAT COST TWO REPORTED-AS-DONE COMMITS.** A long multi-line `git commit -m` was
misparsed as a pathspec: `Co-Authored-By: ...' did not match any file(s) known to git`. The commit
never happened; the background task then ran `git push`, which succeeded with nothing new, and exit 0
came back from the PUSH. **Check the commit step's own output, not the push's.** Use `-F <file>` for
any message longer than a line.

### EIGHT ITEMS, EACH CHECKED AGAINST A RENDERED PNG. 2026-08-29

| ask | what it needed |
|---|---|
| headings merge with content on scroll | the heading LEFT the scroll container. `position: sticky` was the wrong tool twice: sticky means "scrolls with, then pins", and the panels share its scroll box either way, so they slid under it. Now `.aa-workspace-col` is a flex stack of a fixed heading and a separate scrolling body. |
| NVIDIA Warp is invisible | it appeared ONCE in the whole product, mid-popover at index.html:2121. `PlumeBadge.tsx` names it on the Plume tab. **The numbers are scraped from `#dialcard`'s rendered text**, so 72 bearings and 576 GPU solves follow the site instead of being typed. |
| is "Model Calibration" the right name | **No, and it is now "Self-Scoring".** There is no learned model to calibrate: it is a conformal bound plus a feedback loop. "Model" invites a judge to ask which model, trained on what, and the answer is none. |
| move "Learn more about the bound" | node-moved into `#cfcard`, the last panel on that tab. |
| the logo is diffused at the top | it was **19px in a 46px band**, a favicon in a corner. Now `clamp(48px, 6.8vw, 88px)` at 0.15 opacity as a backdrop. WARNING: the first attempt used `z-index: -1` and the logo **disappeared entirely**, because `.aa-banner` paints no background so a negative-index child falls behind body's gradient. `z-index: 0` with siblings at 1. |
| say what is shipped | "**250** data centres ship with a full agentic analysis ... out of **637** mapped". Both counts READ from `manifest.sites` and `unified.sites`, so the line cannot drift from what the product contains. |
| KPI cards do not follow the selected site | see below, the one real functional bug in the batch. |
| 65.6 % in bold red | green, and the sub now reads "the ceiling at 4 day-pairs is 80.0 %". |

### 🔴 THE KPI CARDS IGNORED THE SELECTION, AND THERE WERE TWO SEPARATE CAUSES

A regression against the single-file page, which was site-specific here.

**Cause one:** `loadHeadline(manifest)` took no site at all. It fetched the unprefixed `backtest.json`,
`trace.json` and `money.json`, which are Ashburn's, and `headlineFigures` read
`sites.find(s => s.key === DEFAULT_METRO).footprint_m2` unconditionally. So every figure was Ashburn's
whatever was selected. It now takes a key, resolves that site's OWN `artefacts` map from sites.json
(never a constructed filename), and reports `usedKey` / `isFallback` so the caller can label a fallback
rather than passing another site's numbers off as this one's.

**Cause two, found by looking at the render:** **there are TWO KEY SPACES.** The map and the search bar
address facilities by the UNIFIED key (`metro_ashburn`); sites.json owns the artefacts and uses the
metro key (`ashburn`). The unified entry carries `metro_key` for exactly this join. Passing the unified
key straight through meant it was never found, so the shipped-reference fallback fired for the DEFAULT
site and the first screen announced that **Ashburn had no agent run**. Caught in a PNG, not by a test.

### THE COVERAGE CARD IS GREEN, AND THE ARGUMENT IS ARITHMETIC RATHER THAN PRESENTATION

`tone="critical"` painted 65.6 % in the failure red and read as an apology. The shortfall stays on
screen; the cause is a COUNTING limit. A conformal bound on n day-pairs cannot exceed **n/(n+1)**
coverage however well it is built, so at 4 pairs the ceiling is 80.0 % and 90 % was unreachable before
the method was even considered. **90 % needs n >= 9**, because n/(n+1) >= 0.90 solves to n >= 9: a fact
about the arithmetic, not a claim about the data. The popover adds why there are not 9 yet (a pair is a
vendor forecast plus its elapsed outcome, so each takes a real calendar day and cannot be back-filled)
and what more days change (only n).
**The pair count is READ, not typed:** `series.cov` carries one margin value per day-pair.

WARNING, A DEFECT THE SCREENSHOT FOUND THAT NOBODY REPORTED: the blue `.btn-go` treatment was painting
**disabled** buttons as full-width primary CTAs, so "Live agent not attached" looked like the main
action on the page. The label was honest and the styling was not. `:disabled` is now muted.

**testing/render_shots.py** gained a `plume` shot. Its first version clicked the tab in the same tick
the stage became `results`, and `EngineStage`'s auto-tab effect immediately overrode it, so the PNG
photographed the wrong tab. The click is deferred now. Looking at the image caught that too.

### THE CALIBRATION PAIRS COLLECTOR IS RUNNING AGAIN, 2026-08-29

Enabled: `FG-N26-Coverage` (daily **13:30 +05:00**), `FG-N26-Coverage-Retry1` (13:50),
`FG-N26-Coverage-Retry2` (14:15). All three run `testing/test_n26_coverage.py collect`, which is
self-guarding: "safe to run any time; does only what is due today", `fixture_exists()` short-circuits
before any call, and the retries only spend after a failure.

🔴 **LEFT DISABLED ON PURPOSE, and this is the important half.**
`INTAKE-ARBITER n26 calibration` runs the SAME collector at 13:30 **and** 15:30. It duplicates the
primary and adds an unwanted second window: **it is the task that fired at 15:40 and cost 4,220
credits** when I had reported all FG tasks disabled after filtering names for `FG-`.
`FG-N26-Chicago-Offset` also stays disabled: a different script, `--allow-paid`, three daily triggers.

Verified: flow 26 of 26, palette 38/0, view-matches-page 0, shipped-current 0, deployed-root 0,
app-deterministic 0, `audit.py` 2,216 passed 0 failures.

### 🔴 THE LIVE AGENT WAS DEAD ON THE DEPLOYED SITE FOR ONE MISSING PREFIX. 2026-08-29

Asked to "make the live agent option active". It was not a settings problem: the server had been armed
the whole time (`live_available True, paid_enabled True, key_present True, max_live_calls 48`). The page
could not reach it.

`probeLive()` at `results/engine.mjs:2077`:

```js
const r = await fetch('api/health', {cache:'no-store'});
```

**A bare relative path, with no `ART`.** On `demo/index.html`, served out of `demo/`, it resolves to
`/api/health` and works. The React app is served from `demo/app/`, so the browser resolves the same
string against `/app/` and asks for **`/app/api/health`**, which `do_GET` did not recognise as an API
route at all because it does not start with `/api/`. Measured against the live host:

```
/api/health       200      <- React's path, ART + 'api/health'
/app/api/health   404      <- the engine's path. probeLive() asks for THIS
```

So `HEALTH` became null, `drawLiveUnavailable()` ran, and `#livego` was disabled and relabelled "Live
agent not attached". **Three routes were affected, not one:** `api/health`, `api/live/<site>` (the POST
that starts a run, engine.mjs:2229) and `api/live/job/<id>` (the poll, engine.mjs:2239).

**This is the SAME BUG SHAPE as the artefact 404s** fixed earlier the same day: a bare relative path in
lifted code resolving one level too deep at `/app/`. `_app_artefact_fallback` did not catch it because
that only rewrites paths resolving to a real FILE, and these are routes.

**Fixed in the server, not the engine.** `_unprefix_api()` strips a leading `/app` from any
`/app/api/...` path, called first in `do_GET`, `do_HEAD` and `do_POST`. Step 30 asserts engine.mjs is
character for character the page's code, so adding a prefix there would end that identity.
**No new capability:** it strips a known prefix and hands the request to the same handlers, which keep
their own checks. `do_POST` still refuses a non-offerable site, `--allow-paid` is still required, and
the per-process cap still applies.

Step 33 now asserts **route parity**: `/api/X` and `/app/api/X` must return the same status for
`api/health`, `api/ping` and `api/live/job/<id>`, and an unknown `/app/api/` path must still 404 so the
prefix strip cannot be too broad. ⚠ **Only the GET routes are exercised. The POST is the one that spends
4,220 credits and a verifier must never be the thing that spends them.**

⚠ **WHAT IS NOW LIVE, STATED PLAINLY.** `#livego` on the deployed site is enabled and a click really
calls FortyGuard. **4,220 credits per hourly window**, capped at `MAX_LIVE_CALLS=48` per process, so
about 202,560 credits a day is reachable by anyone with the URL. That is the owner's standing decision
from 2026-08-28 ("let the user make live calls, whoever it may be"), recorded here because the button
was inert until now and the exposure only becomes real with this commit.

### 🔴 A GREP IS NOT A LOOK. testing/render_shots.py NOW EXISTS FOR THAT REASON. 2026-08-29

The user's words: **"WHY ARE YOU SO BLIND? DONT YOU SEE THE SCREENSHOTS OF THE RENDERED RESULT BEFORE
TELLING ME ITS DONE."** They were right, twice over.

Two fixes had been reported as done after grepping the BUILT CSS for the selector. That proves a rule
shipped and says nothing about what a reader sees. Both were wrong:

| reported fixed | why it was not |
|---|---|
| the masthead popover | the rule targeted the engine's `.info-bub`; the masthead uses **React's `Info.tsx`**, `role="note"` with `.glass`. A different element. |
| the dropdown | the background went dark and the LABEL did not. `Combo.tsx` puts `text-ink` on the label span, and a utility on the span beat a colour set on the container. Dark text on navy. |

Then my own second attempt made the dropdown WORSE: `polish.css` and `tones.css` both put `!important`
on `[role='listbox']`, one winning the background and the other the colour, so the state names went
from hard to read to **invisible**. One selector needs one owner in one file.

**`testing/render_shots.py` renders the app to PNG** in both themes, for the dropdown open, a popover
open, the configure stage, and the configure stage scrolled. Every fix below was checked by looking at
the image. Run it before claiming a visual fix is done.

### WHAT THE SCREENSHOTS THEN FIXED

- **The dropdown** is dark in BOTH themes with light text and blue counts, and does not vary with the
  theme at all: a menu floating over a map and a row of cards has to be legible against what is behind
  it, not match the paper.
- **The masthead had FOUR popovers, one per sentence.** Now one, at the end, short. The four lines read
  straight through. The long-form reasoning was not deleted; it lives in the panels the agent writes.
- **Every call to action is brand blue.** `.btn-go`, `#pickgo`, `#runagent2` and React's Configure CTA
  all took `var(--action)`, which is zinc-inverted by design: black in light, white in dark. ⚠ `--action`
  is canonical, so its VALUE is untouched and the components are re-skinned. Repointing it inside `#app`
  would pass `verify_palette.py` while defeating its intent.
- **The tab heading survives a scroll.** It vanished because `.aa-workspace-main` is the scroll
  container and the heading was inside it. Now `position: sticky` with the floor colour behind it.
- **THE TONE SYSTEM, which is what was actually asked for:** not a gradient on every block, but one
  tone per KIND of widget, held across every page. `--w-0` floor, `--w-1` panel, `--w-2` nested block,
  `--w-3` input, plus `--w-hair`, `--w-ink`, `--w-dim`. The grey boxes were `.tile` and `.filters`
  taking `--surface-2`, which is zinc.
- **The light theme is blue PAPER, not white paper.** The first tone set used `#ffffff` for panels,
  which is exactly why the cards still photographed as white boxes: a card the same colour as nothing
  else in the palette reads as grey whatever surrounds it.
- **The black band under the frame is gone.** `#app` is `height: 100vh; overflow: hidden` and only
  `body` carried the gradient, so anything body did not cover fell through to the UA default. `html`
  carries the floor now.
- **The duplicate eyebrow** is gone: the banner already says "free-cooling decisions, hour by hour".

⚠ **AND A PROCESS SLIP WORTH RECORDING:** twice I ran `python tools/build_app.py` from inside
`AGENTIC-ARBITER/app`, where that path does not exist. The grep for "copied" matched nothing, no build
happened, and the screenshots were of the OLD bundle. Identical PNG byte sizes across a run that
changed CSS is the tell. Build from the repository root, and check for the "copied N file(s)" line.

**21st.dev quota:** free tier, **2 component retrievals per day, 0 remaining**. The API does not
publish a reset timestamp, so the exact hour is unknown; available again within 24 hours of use.
`search` is free and unmetered (`freeSearchesPerDay: null`).

Verified: flow 26 of 26, palette 38/0, view-matches-page 0, shipped-current 0, deployed-root 0,
app-deterministic 0, `audit.py` 2,216 passed 0 failures.

### FIVE DEFECTS FIXED BY MEASURING FIRST, and the first page turned blue. 2026-08-29

After being confidently wrong twice on the heading, every fix in this round was written against a
COMPUTED STYLE read out of Chrome. `polish.css` quotes the measurement beside each rule.

| defect | what the probe reported | fix |
|---|---|---|
| heading touched the card ceiling | `card padding-top 24px`, **`h2 margin-top -24px`**, text flush | `.viz-root .card > h2 { padding-top: var(--sp-4) }` |
| stepper sat in the content flow | **`#rail` parent was `viz-root`**, and `#bezel` is not in the lifted markup at all | node moved into a banner slot |
| two Run the agent buttons | rail quick action plus the plant panel's own | `.viz-root #runagent { display: none }` |
| popover text overlapped the page | `--surface-1` IS opaque, so it was a stacking loss at `z-index: 80` | `z-index: 300`, `isolation: isolate`, dark `--fg-pop`, `:focus-within` |
| dropdown showed the map through it | the listbox carries **`className="glass"`** | opaque `--fg-pop`, `backdrop-filter: none` |

**The heading one is worth reading twice.** The negative margin is DELIBERATE and correct:
`engine.css:1134` pulls `.card > h2` out to the card's edges so it becomes a full-width header strip
with a bottom rule, which is the line the user saw the text sitting on. What it omits is a TOP padding,
so the strip had 24 px below the text and 0 above. The margin was never the bug and still carries
`!important`; only the padding needed adding. Verified after: `paddingTop: 14px`.

**The popover was NOT translucent.** `--surface-1` is `#18181b` dark and `#ffffff` light, both opaque.
The bleed-through was the masthead's own later paragraphs winning a stacking contest against a
`z-index: 80` element inside an earlier paragraph. `:focus-within` was added because **a click gives
`:focus`, not `:focus-visible`**, which is why clicking behaved differently from hovering.

⚠ **`#rail` MOVED AS A NODE, not re-rendered.** `appendChild` relocates the engine's own element with
its id, its handlers (`wireRail()` bound them earlier) and its lit pill intact. Nothing is retyped, so
nothing can drift from the page. Safe because no engine.css rule selects `.rail` through an ancestor.

**The first page is blue** (`bodyBg` measured as `rgb(7, 16, 24)` at `stage: pick`), and so are its
search bar, selects, tiles and the theme toggle. ⚠ It RE-SKINS rather than repalettes: not one
canonical token value changed, because `verify_palette.py` requires the app to declare the same values
as `demo/index.html`. That is also why **the charts are still blue-and-orange**: `--series-2` is
canonical and read at runtime by the canvas renderers.

Verified: flow **26 of 26**, palette 38/0, view-matches-page 0, shipped-current 0, deployed-root 0,
app-deterministic 0, `audit.py` **2,216 passed 0 failures**.

### 🔴 THE REPEATED HEADING TOOK THREE ATTEMPTS, AND THE FIRST TWO WERE WRONG FOR THE SAME REASON

The user reported it three times. Worth recording in full, because the mistake is a general one.

`demo/index.html` carries four `.secgroup` eyebrows and **two of them say the same thing**, "The
decision, and what it is worth". Every tab showed them. My fixes, in order:

| attempt | rule | specificity | outcome |
|---|---|---|---|
| 1 | `.secgroup { display: none }` | (0,1,0) | lost |
| 2 | `.viz-root .secgroup { display: none }` | (0,2,0) | lost |
| 3 | `.secgroup { display: none !important }` | n/a | **wins** |

What engine.css actually says, at line 565, is `body[data-stage="results"] .secgroup { display: block }`
which is **(0,2,1)**. Both my fixes lost to it.

🔴 **THE ROOT CAUSE OF BEING WRONG TWICE: I grepped the MINIFIED BUNDLE.** It printed
`secgroup{display:block;...}` and I read that as the whole selector. The `body[data-stage="results"]`
prefix was there in the source the entire time. **Read the source stylesheet, not the built one, when
reasoning about specificity**: minified output shows a rule's declarations, not reliably its selector
context, and a grep that starts mid-selector silently drops the parts that decide the cascade.

`!important` is the right answer here rather than a fourth guess: engine.css is lifted verbatim from
the audited page and cannot be edited in the app, which is exactly the case the keyword exists for.

**AND IT IS NOW ASSERTED, NOT ARGUED.** `verify_app_flow.py` counts `.secgroup` elements that a real
browser renders, on **every tab**: "4 .secgroup element(s) in the page, 0 displayed on any tab". Two
fixes were argued from specificity and both were wrong, so the third is measured.

### THE CONSOLE, REBUILT: REASONING FIRST, THEN THE BUTTON. 2026-08-29

The first version showed "Decision ready" and the PDF button immediately, because the replay tape had
already finished before anyone looked, so **a reader never saw the agent reason at all**. Rebuilt to
the sequence the user asked for:

- **Line one:** an orbiting icon (two counter-rotating CSS arcs around a pulsing core, so it reads as
  thinking rather than as a progress bar implying a percentage nobody measures) plus one short phrase
  that changes every 1.15 s, with the real stage name beside it.
- **Line two:** the blue **Download PDF** button, springing in on its own row.

`MIN_MS = 5200` holds the sequence open even when the work is already done, because a warm replay lands
in under a second and a reasoning state that flashes past reads as a glitch. It **never resolves
earlier than the real tape**: the gate is minimum-elapsed AND `#tapedone` filled.

Clicking `#runagent`, `#runagent2` or `#livego` restarts it, via a **capture-phase** listener that only
observes, so the engine's own handler still does all the work.

**Removed from the screen entirely, at the user's instruction:** `AgentTerminal.tsx` deleted (the stage
rail whose status badge said COMPLETE while its line said "waiting for the agent to start"), and
`#tapecard` hidden, taking "The agent, working", its prose, its own PDF button and its disclosure with
it. ⚠ `#tapecard` is **hidden, not removed**: `#tape` is what proves the reasoning streamed and
`#tapedone` is the signal the console reads. The flow check now asserts exactly that contract, present
and deliberately not displayed, so neither half can regress silently. The live-run block below it is
`#livecard` with `#livego`, still present and still governed by standing rule C1.

Verified: flow **26 of 26**, palette 38/0, view-matches-page 0, shipped-current 0, deployed-root 0,
app-deterministic 0, `audit.py` **2,216 passed 0 failures**.

### THE CINEMATIC BLUE SHELL, THE ONE-ROW AGENT CONSOLE, AND WHAT IS STILL OUTSTANDING. 2026-08-29

**21st.dev MCP, used and exhausted.** `search` (free) several times, `get_usage`, and the one remaining
`get_component` retrieval spent on **#12363 `thinking-tool`** by serafimcloud, whose shimmer is the
basis of the console: an animated linear-gradient painted through the glyphs with
`background-clip: text`. Its `@tabler/icons-react` dependency was dropped for lucide, already present,
and its neutral greys repointed at the brand ramp. `mcp__21st__generate` returned
`locked: generation_limit_reached` on this free account, so the layout is hand-built from the search
results rather than generated.

**`AgentConsole.tsx`: the agent as one row.** Spinner, one shimmering line of short reasoning that
cycles, seven stage ticks, and a bright-blue **Download PDF** that springs in the moment the tape
finishes. The expanded sixteen-line tape is folded away by CSS and reopenable behind "Full trace".

🔴 **EVERY REASONING PHRASE IS FIXED AND CONTAINS NO DIGIT.** The stage is READ from the engine's tape,
so the progress is real; the wording is decoration over a real signal. Paraphrasing the tape's numbers
would be inventing figures with no artefact behind them. `ticker.json` makes the same promise about its
own templates. The **PDF is resolved from `currentSite().artefacts.report`**, never constructed, and the
button is not rendered when the manifest names none.

**The repeated heading is fixed, and it was a specificity bug of mine.** `workspace.css` already said
`.secgroup { display: none }` and it did nothing: engine.css declares `.secgroup{display:block}` and
Vite emitted that declaration AFTER ours, so equal specificity meant the later one won. Confirmed by
reading the deployed stylesheet. `.viz-root .secgroup` is (0,2,0) against (0,1,0), so order stops
mattering. The page carries the eyebrow "The decision, and what it is worth" **twice**, which is what
put it on screen twice.

🔴 **PRESELECTED IS NOT THE SAME AS FILTERED, and conflating them broke a real check.** Defaulting
`filters.facility` to `metro_ashburn` also filtered the map to that one key, so the footprint collapsed
from 637 dots to 1 and `verify_app_deterministic.py` failed, correctly: it loads `/app/?probe=1` and
asserts 637 dots and 246 halos. The default now drives the **search bar and the Configure panel**,
which is what was asked, while the **map keeps showing everything** until the reader touches something.
`pristine` is that distinction and any interaction clears it. `ashburn` is confirmed as the site whose
committed pair is Amazon Web Services IAD116 to IAD117.

**FortyGuard banner:** the wordmark ships as `demo/fortyguard-logo.png` (RGBA, 33,778 B, so opacity
alone is enough), muted at 0.34, spanning the top, `pointer-events: none`, fetched through `ART`.

⚠ **THREE PARTS OF THE BRIEF ARE NOT FULLY DELIVERED, stated rather than implied.**

1. **The charts are not blue yet.** The series ramp is `--series-1` (blue) and `--series-2` (orange),
   both among the canonical 20 that `verify_palette.py` requires the app and the page to AGREE on, and
   both read at runtime by the canvas renderers. Turning the orange into a second blue means editing
   the palette in `demo/index.html`, re-lifting `engine.css` through `tools/mkview.py`, and mirroring
   the values in the app. That is a coordinated change across the audited page, not a CSS tweak.
   The **shell** is blue via new `--fg-*` tokens that collide with nothing.
2. **True zero-scroll is not achievable while the panels are the deliverable.** One tab holds up to
   four engine panels, each with a chart and a table. What ships is an app-like frame: banner, rail,
   header and console are fixed, and the panel column is the only scroll region.
3. **The filters and metric cards are not yet consolidated into one widget grid.** They still live on
   the pick screen as the brief for that screen specified.

Verified: palette 38/0, flow 24 of 24, view-matches-page 0, shipped-current 0, deployed-root 0,
**app-deterministic 0**, `audit.py` **2,216 passed 0 failures**. Figures unchanged.

### shadcn IS INSTALLED, AND ITS INIT BROKE THREE THINGS QUIETLY. 2026-08-29

At the user's direction: `npx shadcn init -b radix -p nova`, the `@efferd` registry added to
`components.json`, then `npx shadcn add @efferd/dashboard-4`. 37 files arrived. **The generator also
made three changes nobody asked for, and every one of them was a visible regression.**

**1. It overwrote two palette values in place.** `--border` went `#27272a` to `oklch(0.922 0 0)` and
`--muted` went `#8d8d96` to `oklch(0.97 0 0)`, both near-white, so **every border and muted label in
the dark theme would have rendered near-white on `#09090b`**. `verify_palette.py` caught it and named
it: 18 of its canonical 20 tokens in common for dark against 20 for light. Restored, below shadcn's
own declarations so a re-init is overridden rather than merged.

**2. Its base layer applies `bg-background text-foreground` to `<body>`, and its `--background` is
`oklch(1 0 0)`: pure WHITE.** Installing one component would have turned the whole dark dashboard
white. Fixed by **aliasing shadcn's tokens to this app's** rather than deleting the `@apply`:
`--background: var(--page)`, `--foreground: var(--text-primary)`, `--card: var(--surface-1)` and five
more. Deleting the rule would have fixed the body and left every registry component off-palette;
aliasing fixes both, so anything added later is on-palette by construction.
⚠ `--muted` is deliberately NOT aliased: this app means muted TEXT by it, shadcn means a muted
SURFACE. One name, two meanings, and the app's wins.

**3. It changed the typeface of the whole app.** It appended `@apply font-sans` to the `html` rule
**after** the existing `font-family: "Inter", ...`, with `--font-sans: 'Geist Variable'`. Later
declaration wins, so everything silently became Geist, and five Geist woff2 files (76 KB) shipped
beside the Inter `index.html` already preloads for the render gate. Fixed by pointing `--font-sans` at
Inter, which also puts every shadcn component on the right face, and removing the font import.

**🔴 THE BLOCK'S DATA WAS DELETED, NOT ADAPTED.** `@efferd/dashboard-4` is an e-commerce dashboard and
its cards carry invented figures: `revenue-chart-data.ts` alone held **275 numeric literals and 91
e-commerce strings**, plus `stats.tsx` and three chart components. 16 files removed. A figure with no
artefact behind it is the one thing this project does not ship, and the user's instruction was explicit
that the values are the agent's and must not change.

**What was kept:** the 17 `ui/` primitives, `delta.tsx`, `formater.ts`, `use-mobile.ts`, and the
block's **layout language**, which is what the request was actually about. The rail is now grouped
under eyebrow headings (Setup / The run / What it found) with lucide icons and a spring-driven active
pill, plus a **Quick actions** card of icon, title, one-line subtitle and chevron.

**🔴 THE QUICK ACTIONS ARE REMOTE CONTROLS, NOT A SECOND IMPLEMENTATION.** Each row reads a real
engine button by id and forwards the click: `#runagent`, `#livego`, `#backtopick`. It mirrors that
button's `disabled` state through a `MutationObserver`, and a row whose button does not exist yet
renders nothing. `wire()` inside the byte-identical engine is still the only thing that runs the agent.

**The panel entrance is transform and opacity ONLY, never layout.** A scaling or reflowing animation
would race the canvas redraw: `EngineStage` redraws on the frame after `data-aa-active` commits, and a
transform does not change `offsetWidth`, so the width the engine measures is the settled one. Honoured
`prefers-reduced-motion` throughout.

**Bundle cost, measured:** js 1,466,326 to 1,471,611 (**+0.4 %**, framer-motion and the icons); css
144,999 to 208,801 (**+44 %, +63.8 KB**) because `index.css` now `@import`s `shadcn/tailwind.css`
unconditionally. The 17 unused primitives are tree-shaken out of the js. Per fresh visit that moves
2.90 MB to about 2.97 MB, so roughly 1,030 journeys before the 5 GiB cap instead of 1,051.

Verified after: palette 38 checks 0 failed, flow **24 of 24**, `verify_view_matches_page` 0,
`verify_shipped_app_is_current` 0, `verify_deployed_root_is_the_app` 0, `verify_app_deterministic` 0,
`audit.py` **2,216 passed 0 failures**. Every figure unchanged: 10.7 %, +406 h/yr, 65.6 %, 43,763 h.

⚠ An `@/*` alias was added to `tsconfig.json` and `vite.config.ts` because the shadcn CLI refuses to
init without one. No hand-written import uses it; the existing relative imports are untouched.

### THE RESULTS STAGE IS NOW A SIX-TAB WORKSPACE, and the panels were not rewritten

Built 2026-08-28 at the user's direction: a hierarchical workspace with a sidebar rail, a widget grid,
glassmorphism, framer-motion transitions and a console-style component for the seven agent stages.

**THE ONE DECISION EVERYTHING ELSE FOLLOWS: the panels are rearranged, never retyped.** The thirteen
results cards keep their ids, their markup and their renderers. `results/engine.mjs` stays
byte-identical to `demo/index.html` (step 30), the markup string stays hash-identical (step 31), and
`audit.py`'s 2,216 checks still measure the page they always measured. `lib/tabs.ts` stamps
`data-aa-tab` on each panel and `workspace.css` decides which are on screen. **No node is moved.**

| tab | panels |
|---|---|
| Configuration & Setup | `[data-show="configure"]`, plus the `.sidebar` holding `#filters` |
| Live Agent Execution | `#tapecard`, `#livecard` |
| Hourly Schedule & Reasoning | `#decisioncard`, `#whycard` |
| Economic Impact | `#headcard`, `#laddercard`, `#moneycard` |
| Plume & Geometry Analysis | `#fieldcard`, `#sitecard`, `#plumecard`, `#dialcard` |
| Model Calibration | `#scorecard`, `#cfcard` |

**TWO OWNERS OF VISIBILITY, DELIBERATELY, BECAUSE THEY OWN DIFFERENT FACTS.** `setStage()` owns "is
this panel's STAGE current" through the `hidden` attribute; the tab rules own "is this panel's TAB
current" through `display`. A panel needs both. Neither reads or clears the other, so `#livecard`
remains governed by the stage machine exactly as standing rule C1 requires. That is not the
two-writers bug the page documents: that bug is two pieces of code setting the SAME property.

**🔴 THE PAGE EXPLICITLY WARNS AGAINST TABS, AND ONE HALF OF THE WARNING IS REAL.**
`demo/index.html` says `IT IS NOT A TAB BAR, AND IT MUST NOT BECOME ONE`, for two reasons.
- The `verify_site_panels.py` half does **not** apply: that check reads `demo/index.html` directly
  (its line 290) and never sees this app. The page is unchanged.
- The canvas half is entirely real: *"a canvas whose parent has no width never draws"*. The engine
  sizes each canvas from its parent's measured width, so a panel that was `display:none` when
  `drawAll()` last ran holds a zero-width canvas that painted nothing. **Every tab activation now
  redraws on the next frame**, in `EngineStage.tsx`, after the attribute is committed and the panel
  has been laid out. Without that, switching tabs reveals a permanently blank chart.

**THE FIVE DELETIONS the user asked for are all in `Masthead.tsx`**, so React-owned and safe. They are
hidden by one CSS rule on `body[data-stage]`, the attribute `setStage()` already publishes, so the
prose stays on the pick screen and is gone from configure and results with **no new owner of anything**.
⚠ The class stops short of the "LIVE agent is also attached" line, which C1 keeps on every stage.

**🔴 A BUG WORTH KEEPING, because it reads as a standing-rule violation.** The first tab map claimed
`#filters` and, since `#filters` has no frame of its own, walked up with
`closest('details, .card, [data-show]')`. That landed on a `<details>` spanning
`demo/index.html` 1754 to 6970, which **encloses all thirteen cards**. Every card then reported hidden,
`#livecard` among them, and the flow check said "the live agent card is present: FAIL". The cause was
layout, not the rule. `classifyPanels()` now **refuses to stamp any element that encloses another
tab's panel** and reports it, so this cannot recur silently.

**`verify_app_flow.py` was rewritten, not relaxed.** Asserting "all thirteen cards visible at once" is
meaningless once they are split across tabs, so the probe now **opens each tab in turn** and credits a
card only to the tab named in its own `data-aa-tab`. The union must still cover all thirteen, no
results tab may be empty, and the canvas count is the **peak across the walk**, which is what proves
the redraw fires. C1 became two assertions that each say what they mean: `#livecard` and `#livego` are
in the DOM **on every tab** (never removed), and the card is reachable in its tab.

Verified: flow check 22 of 22, `verify_view_matches_page` 0, `verify_shipped_app_is_current` 0,
`verify_deployed_root_is_the_app` 0, `verify_palette` 0, `verify_app_deterministic` 0,
`audit.py` 2,216 passed 0 failures. framer-motion 13.1.1 added.

⚠ **ONE FIGURE THE USER QUOTED DOES NOT MATCH.** They asked the plume tab to highlight "345 degrees
with a 0.3797 degC rise". Ashburn's real worst is **255 degrees at 0.3550 degC**
(`demo/rise_table_longest.json:max_rise_bearing`, `max_rise_c`); the facing mode is 235 degrees at
0.1584. 72 bearings and 576 solves are both confirmed. Nothing was hardcoded, so `#dialcard` shows
whichever is true for the loaded site; 345 is most likely the facility they had open.

### THE PINGER IS CREATED, on cron-job.org, 2026-08-28

`Agentic Arbiter keepalive` -> `https://agentic-arbiter.onrender.com/api/ping`, enabled, first
execution "Today at 10:25:00 PM" in its own timezone (Asia/Karachi). Response measured from here at
the moment of creation: **200, 12 bytes, 0.35 to 0.50 s**, well inside cron-job.org's 30-second
free-tier timeout.

⚠ **TWO SETTINGS NOT YET CONFIRMED**, because the job list shows neither: that the interval is
**every 5 minutes** rather than hourly (one "next execution" of 10:25 PM is consistent with both), and
that **Schedule expires is set to 21 September 2026**. Without the expiry, September runs 720 of the
750 workspace hours, which is 96 % and too tight. Both are visible under EDIT.

**The shape that was chosen, and why it changed twice.** First plan was a daily 08:00 to 22:00 window,
rejected because a judge arriving at 23:30 waits a minute for a cold start and reasonably concludes the
site is broken. Second was `Custom` with days 1-21,28-31 across August and September, which works but
picks up 28-30 September as a side effect (576 h, 76.8 %). Settled on **"Every 5 minutes" plus an
expiry date**, which is two controls instead of five multi-selects:

| | days running | instance hours | of 750 |
|---|---|---|---|
| August | 28 to 31, only 4 left | <= 96 | 12.8 % |
| September | 1 to 21 | 504 | 67 %, 246 h spare |

🔴 **A FIRST DRAFT OF THIS SCHEDULE WOULD NEVER HAVE FIRED IN AUGUST.** I told the user to set Months
= September while the question they had just asked was whether a judge could see the project on **31
August**. Their screenshot showed `5 * 1 9 *`, hourly on 1 September only. Read the crontab expression
and the "Next executions" panel; both state plainly what the multi-selects imply, and the panel is the
check: after the fix it must show **today's** date, not next month's.

⚠ **ISOLATED FAILURES IN HISTORY ARE EXPECTED, not a fault.** A cold start is about 60 s
(render.com/docs/free) against a 30 s free-tier request timeout, so **the ping that wakes a sleeping
instance can be logged as failed while still having done its job**; the next one 5 minutes later finds
it awake. It is **25 CONSECUTIVE** failures that auto-disable the job, and that many in a row would
mean the service is genuinely down.

### 🔴 RENDER HAS NO SPEND LIMIT, and the keep-alive must be WINDOWED not 24/7

Verified 2026-08-28 by a 26-agent research pass with a skeptic against every load-bearing claim.

**1. There is no workspace spend limit on Render.** No maximum spend, no spend cap, no field that caps
total workspace spend. The public feature request is open with a May 2025 comment saying it is not on
the roadmap. **"Set the spend limit to zero" is not an action that exists.** The only spend control in
the product caps ONE axis, build pipeline minutes: *Dashboard, workspace home, **Settings** in the left
pane, scroll to **Build Pipeline**, click **Set spend limit***. Not on the Billing page, not gated to
paid plans. ⚠ Whether that dialog accepts a literal `0` is unconfirmed, and a `0` there stops **all
builds including deploys** for the rest of the month, so you could not ship a fix.

**The real cap is having no payment method:** *"If you haven't added a payment method or you reach your
spend limit, Render instead disables all new builds."* Free instance hours behave the same way,
suspending rather than billing. ⚠ **A card IS on this workspace** (the $1 authorisation), so that
protection is not currently in force. The one genuinely billable axis is **bandwidth**, which has no
cap and bills per GB (5 GB included since the 2026-04-23 plan change, overage documented at $0.15/GB).

**2. 🔴 A 24/7 PINGER IS ARITHMETICALLY FINE AND PRACTICALLY RECKLESS.** 750 instance hours per month,
**workspace-wide**, shared by every free service, no rollover.

| plan | hours | headroom of 750 |
|---|---|---|
| awake 24/7, 31-day month | **744** | **6 h, 0.80 %** |
| awake 24/7, 30-day month | 720 | 30 h, 4.0 % |
| **awake 14 h/day, 31-day month** | **434** | **316 h, 42 %** |

On exhaustion Render **suspends every free service until the 1st of the next month**. Not slower: off,
for up to 30 days. And the docs never say whether deploys, restarts and previews count, so **744 is a
floor, not a ceiling**. The asymmetry decides it: a dead pinger costs one judge a one-minute cold
start; a dead hour budget costs the whole site for weeks.

**The interval does not change hours consumed.** Once it never sleeps it burns 744 h whether pinged
every 5 or every 14 minutes. The lever is the DAILY WINDOW, not the interval.

**DECIDED: every 5 minutes, hours 08 to 21 only.** 5 and not 10 minutes because spin-down is 15 idle
minutes, so a 5-minute interval gives 3 pings per window and survives two consecutive misses, while
10 gives 1.5 and one late ping lets it sleep. cron-job.org's own FAQ admits it may delay jobs
deliberately.

**3. cron-job.org is the pinger.** No card, 1-minute granularity, timezone selectable. ⚠ It
auto-disables a job after **more than 25 consecutive failures**, and the free tier has a 30-second
request timeout. Second choice is Cloudflare Workers Cron Triggers, which nothing disables for failing
or for inactivity. UptimeRobot is **fixed at 5 minutes always-on**, which cancels the window.

**4. 🔴 GITHUB ACTIONS CANNOT DO THIS ON A PRIVATE REPO, AT ANY INTERVAL.** Every job is rounded up to
1 minute against 2,000 included minutes, so the entire monthly quota spent on nothing but pings buys
64.5 runs a day, one every **22.3 minutes**, slower than the 15-minute spin-down. Going public makes
Actions minutes free, but `schedule` is documented as delayed and droppable, and **scheduled workflows
are disabled after 60 days of repository inactivity**. Still not the recommendation.

**5. The ping target is `/api/ping`**, now deployed, 12 bytes. Proof it cannot spend: the only call to
the paid path is `LV.live_run(...)` at `serve_live.py:354`, reachable only from `do_POST` on
`/api/live/`; `health()` was instrumented on `socket.connect`, `getaddrinfo` and `urlopen` across two
calls, cold and warm, and made **zero** outbound calls.

⚠ Separately, and it is the owner's stated decision rather than a defect: `POST /api/live/<site>` is
unauthenticated on the deployed host, so 48 calls a day at 4,220 credits is about 202,560 credits a day
available to anyone with the URL.

**Bandwidth per visitor, measured:** first load 2.90 MB, then `loadSite` fetches 7 artefacts totalling
2.20 MB, so **5.11 MB for a full journey and 1,051 journeys before the 5 GiB cap**. `scenarios.json`
is 30.2 MB but nothing fetches it: it is named in the artefacts map and `loadSite` does not read it.

### 🔴 THE DEPLOYED APP COULD NOT LOAD A SINGLE SITE, and the harness is why it shipped

**The user reported "No built artefacts for ashburn" and a Configure button that did nothing.** Both
symptoms, one cause, and the artefacts were never missing.

`results/engine.mjs` is lifted byte for byte from `demo/index.html`, which is served FROM `demo/`. So
`loadSite()` fetches every artefact by the **bare filename** in `sites.json`'s `artefacts` map:
`trace.json`, `backtest.json`, `money.json`, the plume field. The React app is served from
`demo/app/`, **one level down**, so a browser resolves those names against `/app/` and every one 404s.
Measured against the real server:

```
/app/trace.json                          404      /trace.json                          200  207,367 B
/app/backtest.json                       404      /backtest.json                       200   80,206 B
/app/money.json                          404      /money.json                          200  241,855 B
/app/plume_field_ashburn_longest.json    404      /plume_field_ashburn_longest.json     200  684,806 B
```

`loadSite` returns false on a missing trace, so **every** site reported "No built artefacts", and
Configure did nothing because `configureSite()` starts with the same failing `loadSite`. The error
names the boot site rather than the clicked one, because `bootEngine` runs once with the initial key.

**The fix is in the server, not the engine.** Step 30 asserts the engine is character for character
the page's code, and that identity is the whole reason the React rebuild is trustworthy; prefixing its
fetches would end that. So `serve_live.py` falls back from `/app/<name>` to `demo/<name>` when the
bundle does not have it. React's own code already carries `ART = '../'` for the artefacts it reads
directly; the engine cannot, so the server closes the gap.

**🔴 WHY IT SHIPPED, and this is trap 5b.7.** `testing/serve_app.py`, the server the browser flow
check drives, **already had that fallback**, with a comment explaining it. Production did not. The
flow check passed on a server whose routing production did not share. A harness that differs from
production in any routing behaviour is certifying a server nobody runs.

Step 33 now reads `sites.json` and fetches every artefact name for two sites of different shape
(`ashburn`, unprefixed; `AL_way_1540172608`, key-prefixed) through the REAL server at `/app/`, plus
five traversal attempts proving the fallback cannot climb to the repository root where `.env` lives.
19 checks, still writes nothing.

### THE HEALTH CHECK WAS THE EXPENSIVE PART, not the keep-alive ping

Found while sizing the pinger, and it inverts the intuition. `health()` calls `offerable_sites()`,
which re-parsed the 784,300-byte `sites.json` **on every call, uncached**.

**🔴 A CORRECTION TO MY OWN WORK, AND IT WAS A STANDING-RULE BREACH.** The first version of this
section and of the code comment said *"Render polls `/api/health` every 5 seconds"* with "measured"
beside it. **The 5 seconds was never measured or sourced.** render.com/docs/health-checks says only
*"Every few seconds, Render sends health checks"* and publishes no interval. The parse cost is real;
the cadence was mine. In a repo whose rule is that any number must name the file it came from, that is
exactly the failure `audit.py` exists to prevent, and it slipped because it was in a comment rather
than in published copy.

MEASURED, 40 runs on a full core, 2026-08-28: **8.40 ms** per parse, so ~84 ms on 0.1 CPU. Cached,
**0.0356 ms, 220x faster**. The cadence-dependent cost is therefore a RANGE:

| cadence | polls/day | CPU-seconds/day | share of 0.1 CPU | `/api/health` egress/month |
|---|---|---|---|---|
| every 3 s | 28,800 | 2,419 | 2.80 % | 5.46 GB, **101.8 % of the 5 GiB allowance** |
| every 10 s | 8,640 | 726 | 0.84 % | 1.64 GB, 30.5 % |
| keep-alive ping, every 600 s | 144 | 12.1 | 0.01 % | 27 MB, 0.5 % |

With the 12-byte `/api/ping` those first two egress figures become 10.5 MB and 3.2 MB.

**🔴 AND THE FLAPPING IS NOW EXPLAINED, FROM RENDER'S OWN DOCS rather than inference.**
render.com/docs/health-checks: *"If a running service instance fails consecutive health checks for 15
seconds, Render temporarily stops routing traffic to it"*, and at 60 seconds it *"automatically
restarts the instance"*. **Traffic stopped at the edge is precisely the `x-render-routing: no-server`
404, interleaved with 200s, that was observed on 2026-08-28** and that the page surfaced as
`SyntaxError: Unexpected token 'N'`. A health check that parses 784 KB on a tenth of a CPU while a
visitor pulls a 2.9 MB page through the same tenth is a credible way to miss 15 seconds of checks. The
cache and the 12-byte endpoint address the cause; whether they fully fix it needs observation.

⚠ **NOT DOCUMENTED EITHER WAY:** whether Render's own health checks count as the "inbound traffic"
that defers spin-down. render.com/docs/free defines spin-down as 15 minutes *"without receiving any
inbound traffic ... both HTTP requests and WebSocket messages"* and says nothing about internal
checks. Inference, not fact: if they counted, no free service with a health check path would ever
spin down, which would void a documented behaviour, so they almost certainly do not. **My attempt to
settle this empirically failed** and is worth recording as a method note: a 17-minute quiet window was
broken by the user loading the page inside it and by my own deploy polling, so its "never slept"
result proves nothing. A test that needs the absence of traffic cannot be run against a host somebody
else is using.

**Now cached on the file's mtime**, not a TTL: `build_sites.py` rewriting `sites.json` moves the mtime,
so a stale answer cannot outlive the file that produced it. **7.836 ms to 0.0356 ms, 220x.** The cache
is one `(mtime, keys)` tuple rebound in a single store, because `ThreadingHTTPServer` serves on many
threads and two separate stores would let a reader see the new mtime beside the old keys.

Verified five ways: identical output on 250 keys, a caller mutating the returned list cannot poison the
cache, 220x faster, it does invalidate when the file changes (tested against a temp copy so the real
artefact is never touched), and a missing file returns `[]` rather than a stale answer.

### `/api/ping`, and the HEAD trap that would have made a pinger report an outage

Two changes so the keep-alive ping is cheap and actually works.

**`/api/ping` returns 12 bytes, `{"ok": true}`, and does no work at all.** No `reload_if_stale`, no
`offerable_sites`, no key read. Point Render's Health Check Path and the external pinger here, not at
`/api/health`. The bandwidth arithmetic, if Render really polls every 5 seconds:

| polled endpoint | bytes | per month at one poll / 5 s | share of the 5 GiB free allowance |
|---|---|---|---|
| `/api/health` | 6,233 | 3.28 GB | **61 %** |
| `/api/ping` | 12 | 7.9 MB | 0.15 % |

A 10-minute pinger on `/api/ping` costs 0.07 MB a month. ⚠ Whether Render's own health checks count
against billed bandwidth is NOT confirmed, and neither is the 5-second cadence: both are inferred.
The endpoint is worth having either way, and it removes the question.

**🔴 HEAD ANSWERED 404 ON EVERY `/api/*` PATH.** `SimpleHTTPRequestHandler` implements `do_HEAD` for
FILES only, so `HEAD /api/health` returned 404 while `GET /api/health` returned 200. Measured
2026-08-28. Uptime monitors commonly send HEAD, and **a pinger that gets a 404 is worse than no
pinger**: the instance still falls asleep, and the monitoring service also starts emailing that the
site is down. `do_HEAD` now answers `/api/ping` and `/api/health` with 200 and no body, keeps a clean
404 for unknown `/api/*` so a mistyped ping URL cannot look healthy, and shares `_root_redirect()`
with `do_GET` so both verbs route identically.

Guard extended: `run_all.py` step 33 now checks all of that, 16 checks, and still writes nothing.

### 🔴 THE DEPLOYED SITE WAS SERVING THE OLD SINGLE-FILE PAGE, and the user caught it

**The user opened `agentic-arbiter.onrender.com` and saw the PREVIOUS interface.** They were right,
and I was diagnosing the wrong thing at the time: I had spent the preceding effort on intermittent
`x-render-routing: no-server` 404s and had not checked WHICH PAGE the working requests returned.

The cause, one line. `serve_live.py` sets the static root to `demo/`:

```python
super().__init__(*a, directory=DEMO, **kw)      # line 344
```

So `/` served `demo/index.html`, the single-file page. The React bundle is `demo/app/index.html` and
was only ever reachable at `/app/`. Build fine, bundle current, key present, deploy green, wrong page.

**The fix is a 302 from `/` to `/app/`**, added in `do_GET` after the `/api/` branches. A redirect and
NOT serving `demo/app/index.html` at `/`, because the bundle's references are relative:
`./assets/index-*.js` and `../fonts/inter-latin.woff2`. At `/` those resolve to `/assets/` and to a
parent of the root, neither of which exists. At `/app/` they resolve correctly and the app's own
`ART = '../'` fetches land on `demo/*.json`. **The `/app/` depth is load-bearing.**

`demo/index.html` is NOT hidden. It stays at `/index.html`, which is what the verification layer
measures and what `CLAUDE.md` calls canonical.

Verified locally on port 8099, no artefact written:

| path | result |
|---|---|
| `/` | 302 to `/app/`, one `Cache-Control` header |
| `/app/` | React bundle, 3 markers (`id="root"`, js, css) |
| `/app/assets/index-CU1B4VOs.js` | 200, 1,332,270 B |
| `/app/assets/index-DXWxYH6S.css` | 200, 139,341 B |
| `/fonts/inter-latin.woff2` | 200, 48,256 B |
| `/sites.json` | 200, 784,300 B |
| `/index.html` | 200, 491,456 B, `#livego` and `#livecard` both present |

`verify_shipped_app_is_current.py` exits 0, hash `b3378b7b3319f500`, so the bundle the redirect points
at is built from the committed source.

**THE LESSON, and it generalises.** `verify_shipped_app_is_current.py` answers "is the bundle
current?" Nothing answered "is the bundle the thing a visitor reaches?" A currency check one layer in
cannot see a routing mistake one layer out. When a check passes and the user still sees the old thing,
suspect the layer the check does not cover.

### PUSHED, and the Render free-tier limits that actually matter, verified

**The repository is on GitHub: `github.com/bismahjavedhussain/Agentic-Arbiter`, branch `master`.**
4,930 files, 943 MB, 85 commits. Local and remote HEAD agree at `3ac39b6`. The GitHub API returns 404
without credentials, which is what a PRIVATE repo does, so it needs making public for judges to read it.

`scan_secrets.py` ran before the push as the gate: **CLEAN, 0 hits in 4,930 tracked files and 10,746
history blobs, 2,437 MB read.**

⚠ `http.postBuffer` was raised to 500 MB locally first. The 1 MB default makes large HTTPS pushes fail
with `RPC failed; curl 55`, and 943 MB would very likely have hit it.

🔴 A MISTAKE OF MINE WORTH KEEPING. I reported `git ls-remote origin | head -10; echo "EXIT: $?"` as
proving the repo existed and was empty. That `$?` is **head's** exit code, not git's; the probe was in
fact sitting on a credential prompt. The conclusion happened to be right and the evidence was
worthless. `${PIPESTATUS[0]}` is what reads the real exit code through a pipe, and the push used it.

### WHAT 0.1 CPU ACTUALLY COSTS, measured rather than guessed

The Render free instance is **0.1 CPU and 512 MB**. RAM was never the risk; CPU is. Measured on this
machine, then divided by 0.1:

| Work | Here | On 0.1 CPU | Verdict |
|---|---|---|---|
| One full page load, 3.2 MB | 0.09 s, 33 MB/s | about 1 s of CPU | fine, unnoticeable |
| Server memory, peak | 65.5 MB | same | 446 MB spare |
| **One LIVE run** | **12.1 s of CPU time** | **about 121 s, 2 minutes** | slow but not broken |

The live figure is the one that matters and it needed a specific measurement: **total CPU time**, not
wall clock, because 0.1 CPU rations CPU seconds. A run consumed 12.1 CPU seconds at an effective
**0.80 cores**, so it is essentially single-threaded and there is no hidden multi-core multiplier
inflating the estimate.

**IT CANNOT TIME OUT, which is the saving grace.** `POST /api/live/<site>` returns a `job_id`
immediately, the agent runs in a background `threading.Thread`, and the browser polls
`GET /api/live/job/<id>` while progress streams. So two minutes shows as a progressing card, not a dead
request. Had this been one synchronous request it would have been unusable on this tier.

Measured with `live.py run --replay <cached window>`, which does the same computation from a saved
FortyGuard response for **zero credits**.

⚠ **NO PERSISTENT DISK on the free tier**, per Render's own notice on the plan picker. `data/live_cache/`
is where a bought window is cached so it is not bought twice, and it is ephemeral here: a redeploy or a
restart loses it, so the same window can cost 4,220 credits again. Not a fault, but it is why the cache
cannot be relied on to prevent double spending in this deployment.

⚠ Also stated on that notice, and all harmless here: no SSH, no scaling, no one-off jobs.

### THE FREE-TIER NUMBERS, all workspace-wide and per month

Researched by a 9-agent workflow and then checked adversarially, which found 35 problems in the first
pass. Every number below carries a source in the workflow output.

| Limit | Value | What happens when exceeded, with no card on file |
|---|---|---|
| RAM per instance | **512 MB** | process killed, "Ran out of memory", deploy cancelled |
| Outbound bandwidth | **5 GB** | every free service suspended until the 1st |
| Build pipeline minutes | **500** | no new builds for the rest of the month, so no redeploying a fix |
| Instance hours | **750** | every free web service suspended until the 1st |

**THE RAM RISK IS CLEARED BY MEASUREMENT, not by argument.** The workflow called 512 MB "the one number
most likely to stop this outright". Measured locally, serving every path a judge's browser requests:

```
peak working set   65.5 MB
Render free limit 512.0 MB
headroom          446.5 MB
```

The server streams artefacts from disk rather than loading them, so numpy's import is most of the 63 MB.
⚠ NOT measured: a real live run, which allocates numpy arrays for a 17,862-tile field. Measuring it
costs 4,220 credits, so it was not done.

⚠ **750 HOURS LEAVES SIX HOURS OF SLACK.** Keeping one service awake through a 31-day month spends 744.
So: **only one free service in this workspace**, or the allowance is split and both get suspended.

### 🔴 GITHUB ACTIONS CANNOT BE THE KEEP-ALIVE PINGER ON A PRIVATE REPO

This is the finding that most changed the plan, and it would have failed silently. A 10-minute schedule
is 6 runs an hour, 4,320 a month, and **GitHub rounds every job up to a whole minute**, so it needs
4,320 billable minutes against the **2,000** included on GitHub Free. The pings stop dead about
**13.9 days** into each month with no alert. Only viable if the repo is public.

**So the pinger is `cron-job.org`:** no card, no repo change, no Render change, any interval from one
minute upward.

### DECIDED, SCHEDULED FOR AFTER THE PUSH: Render with a card and a zero spend limit

The user's decision on 2026-08-28, recorded because it is the next action and it involves money:
*"we will go with the first option i.e Render, card plus a zero spend limit. But for now push the
project on github first."*

**Target repo: `https://github.com/bismahjavedhussain/Agentic-Arbiter`** (branch here is `master`).

**Why a card at all, since Render's own docs say free access does not need one.** The signup asked for
it anyway, most likely because the **Blueprint** flow can create several services at once. The
documented free-tier behaviour is that payment info only matters for OVERAGES: *"If you haven't added a
payment method, Render instead suspends all of your Free services"* for bandwidth, and *"disables all
new builds"* for build minutes.

**The plan, in order, once the push is done:**
1. Render, **New > Web Service** (not Blueprint), connect the repo, pick the **Free** instance type.
2. Add the card, then set the workspace **spend limit to zero**, so overages suspend rather than bill.
3. Paste `FORTYGUARD_API_KEY` as a secret env var. The user pastes it; it never passes through me.
4. Start command is in the Dockerfile. Public URL will be `<service>.onrender.com/app/`.
5. Point a free uptime pinger at `/api/health` every 10 minutes: Render spins a free service down
   after 15 minutes idle and takes about a minute to wake, and 750 free instance hours a month covers
   one always-awake service with about six hours to spare.

⚠ COULD NOT VERIFY: the exact dashboard path for the spend limit. Render's `/docs/spend-limits` and
`/docs/billing` both return 404, and the pricing table is rendered client-side. The limit is referenced
by the free-tier doc (*"unless you've reached your spend limit"*), so it exists; the click path is not
established.

⚠ HUGGING FACE SPACES IS NOT AN ALTERNATIVE, correcting something I said earlier from memory. Their
docs: *"Gradio and **Docker Spaces** run on compute and **require a paid plan** to create"*. Koyeb's
free web tier also appears to be gone. TryCloudflare quick tunnels are genuinely card-free and
account-free, but the URL is *"randomly generated each time"* and Cloudflare calls them *"intended for
testing and development only"*, so they suit a live demo you attend, not a submission link.

### What we are in the middle of
The React app is now **the whole product, not just the pick screen**. As of 2026-08-28 it carries
pick, configure and results, including the live agent. Remaining work is judgement, not plumbing:
the light theme is still not visually verified, and `verify_palette.py` does not yet parse
`app/src/index.css`.

### THE CORRECTION THAT RESHAPED THIS WORK, 2026-08-28
The user's words: *"I want to change the Ui but I dont want to change the buttons from the .html file
that existed before. The front page only has the configure button and then the run agent button and
run agent live button all appears afterwards with graphs and proper reports like it was doing in the
html file we made before."*

They were right and I had the scope wrong. The React rebuild was a **pick screen only**, and its
"Configure this plant" button linked out to `demo/index.html`. A new UI that hands the reader back to
the old UI at the first real action has not replaced anything. Two of the page's three stages, 18
cards, the reasoning tape and the live agent existed nowhere in it.

They then asked the exactly right follow-up question before agreeing to the approach: does lifting
the results stage weaken the LIVE agent? The answer, measured rather than asserted: no, and lifting
protects it best. A live run writes into nine elements, all inside `#livecard`, and it does produce
new charts -- `drawLive` calls `drawConformalLine` and `drawConformalSummary`, so a real conformal
bound is computed on live weather. It deliberately does **not** overwrite the replay panels, because
those are measured over 43,763 held-out hours and one live hour replacing them would make the
90 %-promise coverage test meaningless. And the live agent's REASONING is server-side in
`serve_live.py`, so no front-end move can touch it.

### The plan
| Step | State |
|---|---|
| 1. Attach the 21st.dev MCP server | **done** |
| 2. Extract `core/`, repoint the verifiers | **done and green** |
| 3. Extract the shared chart primitives | **done and green** |
| 4. React prototype of the pick screen, per the UI brief | **done and green** |
| 5. Lift the engine so the React app carries configure + results + live | **done and green** |
| 6. Verify the palette against `app/src/index.css`; check the light theme by eye | **next** |

### HOW THE TWO HALVES MEET, and why it is shaped this way
`AGENTIC-ARBITER/results/engine.mjs` is **100 functions, 208 KB, lifted byte for byte** out of
`demo/index.html`. React renders the page's own configure and results **markup** verbatim
(`app/src/generated/engine-markup.ts`, 39 KB) and its **stylesheet** verbatim
(`app/src/generated/engine.css`, 96 KB). The engine finds its targets by element id and owns
everything inside them; React owns the pick screen and the shell.

Measured, not assumed: with the pick stage fenced off, **the engine calls nothing on React's side of
the seam.** Zero crossings.

**Why the page keeps its inline copy too.** Deleting it would force `index.html` to load a module,
and browsers block module loading over `file://` -- a judge who double-clicks the page would get a
blank screen. That property is the most-tested thing about this product. So there are two copies, and
`testing/verify_results_matches_page.py` refuses to let them drift.

**Why the code is not imported from `core/`.** Those 22 functions were deliberately CHANGED when they
were extracted (`decide(k)` became `decide(k, trace)` so the node verifiers stop stubbing `$()`).
Importing them would break every call site. The duplication is intentional and asserted.

### THE THREE DEFECTS THE STATIC CHECKS COULD NOT SEE
Worth recording, because all three passed byte-identity and id-presence checks and were caught only
by driving the browser. This is why `testing/verify_app_flow.py` exists.

1. **`const BOOTED = boot();`** The generator dependency-analysed the *functions* and took the 55
   top-level *declarations* wholesale. One of them calls the page's entire bootstrap. The lifted
   module threw `ReferenceError: boot is not defined` the instant React imported it. The fix moved the
   assertion **onto the emitted output** rather than the inputs: checking the inputs is checking my own
   reasoning about them.
2. **`document.querySelector('.viz-root')`.** `cssv()` reads the design tokens through a **class**
   selector, invisible to an id-based check. Missing, it threw
   `getComputedStyle: parameter 1 is not of type 'Element'`, the configure transition rejected, and the
   screen just sat there.
3. **React re-applying its own `dangerouslySetInnerHTML`.** The transition ran, `buildControls()`
   filled `#filters`, React re-rendered on a state change, re-applied the pristine markup, and the
   controls were gone. Nothing threw; the stage said `configure` and the panel was empty. The markup is
   now injected once in a layout effect, so React has no children there to diff, ever.

Plus a fourth that was mine alone: `#c_site` is in `#pickcard`, on React's side, and the markup
verifier reported it present because the string `id="c_site"` appears **inside an HTML comment** about
a historical duplicate id. Four times in one session a name in prose was mistaken for a definition;
every scan in the verifiers now masks comments first.

### THE UNCOMMITTED RISK IS CLOSED, at commit fcf7b59
Everything is committed and `git status` is clean: **0 paths outstanding**. 7365 files changed, 15479 insertions(+), 3330 deletions(-)

Checked BEFORE committing rather than after:
- `.env` is gitignored, untracked, and **absent from the commit**. `testing/scan_secrets.py` reads the
  real key off disk and searches for it across every tracked file AND every blob in history:
  **clean, 0 hits in 5,975 tracked files and 7,393 history blobs, 1,760 MB read.**
- `node_modules` absent from the commit.
- `diff.renameLimit` raised to 8,000 FIRST, so the folder rename is recorded as **3,600 renames**
  rather than as thousands of unrelated deletes and adds. Git's default limit had silently skipped
  detection, and a history that cannot see a rename cannot follow a file through one.
- Git normalised line endings on three new `testing/` files on the way in. All three re-parsed and the
  suite re-ran afterwards: audit 2,215/0, drift gate 64/0, palette 34/0, context pack clean.

⚠ **It is ONE commit for a very large amount of work, and that is a fault rather than a style.** It
should have been several. From here on, commit incrementally.

⚠ **There is no remote.** `git remote -v` is empty, so this snapshot exists only on this machine. A
disk failure still loses everything. Pushing somewhere is a separate decision and has not been made.

### 🔴 THE NEXT ACTION
The pick screen prototype EXISTS and every behaviour in the brief is verified (below). What is left,
in order:

1. **Spend the 21st.dev retrievals deliberately.** Free tier: **2 component-code retrievals per day**,
   search and browsing unmetered. Nothing retrieved yet, 2 of 2 remaining.
   **Recommended first spend: a stat/KPI card design** (candidates found by search: `Stats Card`
   id 7841, `Progress Metric Card` id 15024). Reasons: the five cards are the largest flat area and
   the first thing after the headline; it is purely presentational, so the audited figures in
   `headline.ts` are untouched; and it **restores something this React rebuild lost** -- the
   single-file page had micro-sparklines built from three REAL series (the notice-hour ladder in
   `BT.sensitivity.rows`, the 16 money cells, and the margin trajectory) and the React KPI cards
   have none. `charts/primitives.mjs` already exports `sparkSVG`, so what is wanted from 21st is the
   card's visual craft, not a charting library.
   ⚠ **Drop any "+12% vs last month" affordance such a card ships with.** Four of the five figures
   are LEVELS, not trends; there is no previous period. Rendering one would be a false visual claim.
   **Second spend: hold it.** Retrievals reset daily, and choosing before seeing the first one
   integrated is guessing. If it must be pre-committed, the next weakest thing is the page FRAME:
   it still reads as a document rather than an application.
2. **Extend `verify_palette.py` to the app's tokens.** `app/src/index.css` inherits every colour value
   from `demo/index.html` verbatim, because each one is measured; but the validator parses the page,
   not the app, so right now they are inherited rather than independently verified.
3. **Rebuild the remaining panels as components**, one at a time, only when the pick screen is signed
   off. The other 30 stay in the HTML page until then.
4. **Decide when the app supersedes the page.** At that point: the page's inline agent copy goes, the
   drift gate (step 29) becomes unnecessary, and `dist/` gets committed once, deliberately.

### 🔴 THE GAP THE USER CAUGHT, and it was a real one
**The React pick screen let a reader select a data centre and then offered nothing.** No configure
button, no run, no statement that those stages exist. The user asked "where's the button of
configuring the plant selected by the user?" and was right to read that as a missing feature.

**What was NOT true:** nothing had been removed from the shipped page. Verified: `demo/index.html`
still has 3 stage-rail steps, `#pickgo`, `#runagent`, `#runagent2`, `#backtopick`, `#livecard`,
`#livego`, `#filters`, `#readytiles`, 15 results-stage cards and 3 configure blocks. The React app is
a one-screen prototype, which is what step 4 scoped.

**Why that is still not a defence.** A screen that ends in a dead end is not a smaller product, it is
a broken one. "The brief only specified the pick screen" does not license shipping a cul-de-sac.

**The fix: `app/src/components/SelectedBar.tsx`.** Selecting a facility now reveals a bar with its
name, category, operators, weather station, a Deselect, and the primary action:
- ready to run → **"Configure this plant →"**, linking to `../index.html?site=<metro_key>`
- a candidate → the honest reason instead of a button that would quietly land elsewhere

It is a HANDOFF, not a reimplementation. Configure, results, the reasoning tape, all 13 panels and the
live-agent card exist and work in `demo/index.html` today; none of it has been rebuilt in React. A
button that pretended otherwise would be worse than the dead end.
`?site=` takes a METRO key, which the page validates against its own picker options, so the CTA is
only offered where the metro is offerable.

### 🔴 THE URL LAYOUT, which that one link forced into the open
The app fetched artefacts relatively, which is correct only when the app's directory IS the artefacts'
directory. That is true in vite dev and nowhere else, and mounting the app at `/app/` exposed it:
`/app/sites.json` was a 404, and the production layout `demo/app/` would have failed the same way.

**One constant fixes all three: `ART = '../'` in `app/src/lib/artefacts.ts`.** Browsers CLAMP `../` at
the root rather than erroring, so:

| Layout | app at | `../sites.json` resolves to |
|---|---|---|
| `vite dev` | `/` | `/sites.json`, served by the config's plugin |
| `testing/serve_app.py` | `/app/` | `/sites.json`, i.e. `demo/` |
| production | `demo/app/index.html` | `demo/sites.json` |

And `../index.html` reaches the single-file page in all three, which is what makes the CTA correct
everywhere. **When the app eventually replaces `demo/index.html`, `ART` becomes `''` and nothing else
changes.** The fonts in `index.css` and the preloads in `index.html` use the same `../` for the same
reason, and `testing/serve_app.py` now mounts the app at `/app/` to mirror production.

### Step 4, as built
`AGENTIC-ARBITER/app/` -- Vite 7, React 19, TypeScript, Tailwind 4, maplibre-gl 6. Nine source files.
`npm install` clean, 0 vulnerabilities. Typecheck clean. Build clean.

**It consumes rather than re-derives.** The same `demo/*.json` at the same relative paths, so
`vite.config.ts` SERVES `../demo` in development rather than copying it: demo/ is 695 MB across 3,304
files, and `publicDir` would duplicate all of it into `dist/`. A built bundle is meant to be dropped
INTO demo/, where the same fetches resolve, which is what keeps "no install step" true for the
artefact even though the source now has a build.

**The five KPI figures are the shipped figures.** Derived in `app/src/lib/headline.ts` exactly as
audit.py's front-door registry derives them, and **reproduced in Python first** and checked against
the published strings before a line of TypeScript was written. All twelve matched, intermediates
included. ⚠ That is a second place the derivations live; it is accepted only because audit check 10
re-derives all of them independently and fails on a mismatch.

**Every behaviour the brief specifies, verified through the app's own `?probe=1` surface:**

| Brief | Measured |
|---|---|
| Inter, self-hosted, real hierarchy | ~1.32 type scale, hero figure ~4x body; one family by weight, not two by family |
| Order: headline, search, cards, map | exactly that, in the DOM |
| Search bar and map visible together | the bar is **sticky**; see the note below on the contradiction |
| Three interconnected combo boxes | choosing California drops the operator list to those operating there, with California counts |
| Vibrant coloured OSM | no `raster-*` exposure paint at all |
| 246 ready-to-run in green | `paintedHalo: 246` |
| Full US on arrival, no zoom | `zoom: 3.5`, camera untouched on mount |
| Ashburn popup on arrival | "Ashburn, Virginia / Amazon Web Services IAD116 → Amazon Web Services IAD117 / facades 60.3 m apart" |
| State selection fits that state | `state=CA` → 46 dots, 10 halos, zoom 5.48 |
| Operator highlight, contrasting | paint expression targets the 57 AWS facilities in `--series-2` terracotta; all 637 stay visible |
| Facility selection zooms and names it | 1 dot, zoom 12, "The data centre you selected: QTS San Antonio II, Texas" |
| **All 637 facilities on the map** | `paintedDots: 637`, `srcGiven: 637`, registry holds 637. **A filtered view showing 1 dot is correct**, and the bar says "1 of 637 shown" |
| A way to proceed from a chosen site | `SelectedBar` → `../index.html?site=<metro>`, verified to land on the page carrying `#pickgo` and `#runagent` |

**THE ONE CONTRADICTION IN THE BRIEF, and how it was resolved.** It asks for the order
headline → search → cards → map AND for the search bar and map to be visible at once. With the cards
between them, both cannot hold at any laptop height. The bar is sticky: the DOM order is exactly as
asked, and scrolling to the map leaves the controls on screen and live.

**"LIVE agent is also attached" is rendered only when it is true.** Hard-coding it would be a false
claim on the first line a judge reads. When no agent is attached the line states REPLAY and says how
to attach one.

### 🔴 FIVE DEFECTS IN STEP 4, and the order matters more than the list
The map showed a perfect, interactive, colourful basemap with **none of the 637 facilities on it**,
and raised no error. Five things were wrong, found in this order:

1. **`onPick` was an inline arrow in the map effect's dependency array**, so the map was destroyed and
   rebuilt on every render, twice over under StrictMode. Real bug, fixed with a ref. **Not the cause.**
2. **My `on('error')` handler discarded everything.** Registering a handler REPLACES maplibre's
   default, which logs, so adding it made the map quieter than having none. An error handler that
   discards is worse than no error handler.
3. **My probe read `_data.features`.** maplibre 6 keeps inline data at `_data.geojson`, per its own
   type declaration. It reported `-1`, which looked like "the source has no data" and meant "my
   instrument looked in the wrong place". Corrected, it read **637**.
4. **THE ACTUAL CAUSE: maplibre 6 ships its worker as a separate module** and requires
   `setWorkerUrl`. Raster tiles decode on the main thread, so the basemap drew perfectly; only
   GeoJSON needs the worker, so the facilities never tiled and `loaded()` stayed false for ever, with
   no error. A correct, colourful, interactive map with nothing on it is exactly what a missing
   worker looks like.
5. **And `?url` was the wrong import for it.** It copies the file verbatim without following its
   imports, and maplibre's worker begins `import{B as e,...}` from a shared chunk that is then absent
   from the bundle. `?worker&url` bundles it: 18 KB became 476 KB, and the dots appeared.

Plus two smaller ones: two effects both owned the popup, so the second removed what the first had just
created (`popups: 0` every time); and `committed.source` / `.receptor` were guesses -- the real names
are `source_name` / `receptor_name`, and an optional chain on a misspelt key renders nothing at all
rather than failing.

⚠ **A heredoc mangled a patch into a regex containing literal BACKSPACE characters**, so `?probe=1`
compiled, ran, and never matched. Sixth occurrence of `05-TRAPS.md` 5.4 this session. Use the Write
tool for anything containing a backslash.

### How to run and verify the app
```
cd AGENTIC-ARBITER/app && npm install && npm run dev     # http://127.0.0.1:5173
cd AGENTIC-ARBITER/app && npm run build
python testing/serve_app.py 8123 --hold 16               # serves app/dist + demo together
```
`?probe=1` renders a hidden `#AAPROBE` div carrying the live map's state: layers, source counts,
distinct facilities actually PAINTED, the filter, the paint expression, the camera, and any errors.
`?state=CA&operator=...&facility=KEY` seeds the filters, which is both a shareable deep link and the
only way a headless check can drive the three filter behaviours.

⚠ **`--hold` is not optional for a screenshot.** A headless capture fires at the load event, which is
always too early for this map, and `--virtual-time-budget` makes it worse: a GeoJSON source tiles in a
worker on the real clock while virtual time races the page's timers. Measured: source and layers
present, `querySourceFeatures` 0, `isStyleLoaded()` false, nothing broken.

⚠ **Not yet verified:** the light theme visually (the palette is inherited and measured, but the app's
own tokens are not parsed by `verify_palette.py`), and the app has no equivalent of the byte-identical
render gate.

### Step 2, as built
`AGENTIC-ARBITER/core/` is six ES modules: `format`, `config`, `conformal`, `agent`, `explain`,
`ticker`. Generated by `scratchpad/mkcore.py`, which lifts each function out of `demo/index.html` with
the same brace-matcher the verifiers use and prints every substitution it makes.

**All five cross-implementation verifiers now `import` from `core/` instead of string-scraping the
page, and none of them fakes a browser any more.** Corpora unchanged: 500 DP cases, 789 conformal
assertions, 20,160 configurations, 1,336 explanations, 2,037 event sentences, zero mismatches.

The design decision that made it possible: **`cfg()` stays in the page.** It was the only thing
reaching into the DOM, and it is a 10-line adapter over eleven `#c_*` controls. Its coercions moved to
`core/config.mjs` as `cfgFromStrings(get)`, where `get` is an injected callback. The page passes
`id => $(id).value`; a test passes `id => String(row[...])`. Identical coercions, one definition. That
matters because a `<select>` always yields a string, so `offday` is `"0"` and not `0`.

### Step 3, and why it was reframed
The plan said "extract the canvas draws to `charts/` the same way". **That was the wrong shape of
job.** There are 31 `draw*` functions, 152,107 characters, about 3,621 lines, and every one writes
`innerHTML`. They are not chart functions; they are panel renderers that emit tables, tiles and prose
AND paint canvas. Extracting them as pure draw functions means splitting all 31 into
data → view-model → DOM, and the React migration rewrites the DOM half of each one anyway. That work
would be discarded on arrival.

What moved instead is the **primitive layer** all 31 share and every React chart component needs:
`charts/primitives.mjs`, 105 lines, seven functions byte-identical to the page plus `DPR_CAP` and
`EDGE`. The 31 panels get **rebuilt as components**, one at a time, starting with the ones the pick
screen needs (the KPI plate and the map). The brief says not to modify the reports, graphs or data
cards, so the other panels stay in the HTML page for now.

**And it closed a drift risk the page documents but could not guard.** `index.html` builds its canvas
font strings from `CFACE`/`CMONO`/`CBODY` literals duplicating the CSS tokens, and its own comment
concedes: *"Keep the two in step by hand; there is no mechanical guard available."* There is one; it
just was not reachable there, because `getCssVar` is defined 3,700 lines below `CF`. In a module the
order is ours, so `CF` is now an object of **getters** that resolve from the tokens at first use, with
no change at any of the 40 `fillText` call sites.

### The gate that holds it together
`testing/verify_core_matches_page.py`, `run_all.py` **step 29**. The agent now lives twice: in
`core/` (which the five verifiers test against Python) and inline in `demo/index.html` (which a reader
runs). The verifiers prove `core/` matches Python; nothing else would notice if the PAGE drifted from
`core/`, and then five passing checks would be testing code nobody sees.

It reads `core/_transform.json`, a provenance manifest the generator writes: per function, the SHA-256
of the page source extracted and of the module source produced, plus the substitutions in words.
**64 checks, 0 failed**, over 22 functions across both directories, 18 of them byte-identical.
Tamper-tested: a one-character change to `cfAttainable` fails both this gate and the conformal
verifier. **It becomes unnecessary the moment the page imports `core/` instead of carrying its own
copy.**

### Four defects the instruments found in themselves, worth knowing before writing more of them
1. **`\bUS\b` matched inside `toLocaleString('en-US')`** and silently rewrote the locale tag, because
   a hyphen and a quote are both non-word characters. `tkFormat` never referenced the global at all.
   Locale matching is case-insensitive, so no behavioural test would ever have caught it.
   `thread()` in the generator now refuses to substitute inside a string literal.
2. **The first drift gate asserted against difflib's chunking**, not against the code: `cfg` →
   `cfgFromStrings` arrives as an insertion of `"FromStrings"`, and `tkEvent(` → `_ev(` fragments
   because the strings share a `v` and a `(`. Replaced with hashes, which have no opinions.
3. **The diff tool re-found each run with `old.find(a)`** instead of using difflib's offsets, so four
   separate one-character substitutions all printed the same wrong context. A verification tool that
   prints confident, wrong context is how a real defect gets waved through.
4. **`verify_browser_explanation.js` had its own `fmt` stub returning an ASCII hyphen** where the page
   returns an en dash, so it had always compared explanations built with one formatter against a page
   shipping another. Now imports the real one, and passes, so the divergence was latent.

Also: the cross-module imports in `core/` are **derived**, not hand-written. A hand-written list
already cost the 1,336-explanation corpus once, because `explainHour` calls `plan` and the list said
only `fmt`.

---

## 1. Figures

<!-- FIGURES:BEGIN -- generated by sync_context.py, do not hand-edit -->

| Figure | Value | Derived from |
|---|---:|---|
| Real facilities in the registry | **637** | demo/unified_sites.json -> len(sites) |
| Of those, ready to run | **236** | sites.json offerable metros, joined on metro_key |
| Offerable metros | **238** | demo/sites.json -> sites[].offerable |
| States represented | **43** | distinct unified_sites.json sites[].state |
| run_all.py steps | **45** | count of STEPS entries in src/run_all.py |
| demo/index.html size | **490 KB** | byte length of the shipped page |
| Map GeoJSON sources | **2** | one clustered, one flat -- see 02-ARCHITECTURE |
| Map unisites-* layers | **5** | cluster, halo, points, flat-halo, flat |
| `#livecard` present | **yes** | standing rule: the live agent is never removed |
| `#livego` present | **yes** | standing rule: the live agent is never removed |

*Every row above is re-read from the artefact named beside it by `CONTEXT/sync_context.py`. None of it is typed by hand, so none of it can go stale without the check failing.*

<!-- FIGURES:END -->

### A distinction that is easy to get wrong
**250 offerable metros, but 246 ready-to-run facilities, and both numbers are correct.**
`sites.json` marks 250 metros `offerable`. Four of them have no matching row in
`unified_sites.json` (`CA_way_358455179`, `IL_way_863162820`, `VA_way_714622339`,
`VA_way_744496750`), so only 246 *facilities* join to an offerable metro. The mapping for those 246 is
strictly 1:1. **The number published on screen and in the README is 246**, which is the facility
count, and that is the right one for a reader looking at a map of facilities. Do not "fix" one of
these figures to match the other.

---

## 2. Where verification stands

Every verdict below was produced by running the check, not by reading a note about it. Detail,
commands and exit-code contracts are in `03-VERIFICATION.md`.

| Check | Verdict | Scale |
|---|---|---|
| `AGENTIC-ARBITER/src/audit.py` | **PASS** | 2,216 passed, 0 warnings, 0 failures |
| `testing/verify_palette.py` | **PASS** | 34 pairs, 0 failed, both themes |
| `testing/verify_state_filter.py` | **PASS** | 62 assertions, 3 consecutive clean runs |
| `testing/verify_map_hover.py` | **PASS** | |
| `testing/verify_site_panels.py` | **PASS** | 13 panels differ across sites, 1 declared shared, 0 identical-and-undeclared |
| The five cross-implementation verifiers | **PASS** | agent, conformal, decision, explanation, ticker |
| Live agent surface | **present** | `#livecard`, `#livego`, `/api/health` reports `live_available: true` |
| `testing/verify_core_matches_page.py` | **PASS** | 64 checks, 0 failed, 22 functions across `core/` and `charts/` |
| `testing/audit_nothing_lost.py` | **NO LOSSES** | 5,975 baseline paths walked, every function, id, artefact and verdict string present |
| `testing/verify_results_matches_page.py` | **PASS** | 12 checks, 100 engine functions byte-identical, 208 KB |
| `testing/verify_view_matches_page.py` | **PASS** | 8 checks, 105 engine lookups all accounted for |
| `testing/verify_app_flow.py` | **PASS** | 21 checks, pick to results in a real browser, 32-row tape, 11 canvases |
| `testing/verify_app_deterministic.py` | **PASS** | two renders identical: figures, labels, bar heights, map counts |
| Paid API calls spent this session | **0** | |

---

## 3. Change log

### 2026-08-28 - Where it deploys, decided against fetched facts rather than memory

**The user's requirement: "Deploy on a good platform where no dynamic working or live calls get
interrupted."** That single line rules out most free tiers, so the platform docs were fetched rather
than recalled.

| Platform | Verified fact | Verdict |
|---|---|---|
| Render free | "spins down a Free web service that goes 15 minutes without receiving any inbound traffic", wake "takes about one minute", 750 free instance hours per workspace per month | usable **with a keep-alive ping** |
| Hugging Face Spaces | "Gradio and **Docker Spaces** run on compute and **require a paid plan** to create" | **not an option** on a free account |
| HF free hardware | "your Space will go to sleep and stop executing after a period of time if unused" | would interrupt anyway |

**The chosen answer: Render free plus an external pinger on `/api/health` every 10 minutes.** The
arithmetic closes: a service kept awake through a 31-day month uses about 744 hours against a 750-hour
allowance. `/api/health` makes no vendor call and costs no credits, so the pinger is free in both senses.

⚠ THE MARGIN IS SIX HOURS. If they exhaust the 750, Render suspends free services until the next month.
Fine for a hackathon window; the cheapest paid instance removes the question. Render's price could not
be verified from here, the pricing table is rendered client-side, so no figure is quoted.

**Also added `.dockerignore`.** Without it the build context is about 1.6 GB: `.git` alone is 479 MB and
`node_modules` 138 MB. It also excludes `.env` explicitly, because a LOCAL `docker build` runs against
the working tree where that file does exist, unlike a git clone.

**THE KEY NEVER PASSES THROUGH ME.** `render.yaml` declares `FORTYGUARD_API_KEY` with `sync: false`, so
Render prompts for it and stores it encrypted. The user pastes it. A key that passes through a chat
transcript is a leaked key, and there is no version of this task that requires me to see it.

### 2026-08-28 - The README lost its em dashes, and the ranges kept theirs

66 em dashes removed from README, the one document judges read. The rule: a dash followed by a
conjunction or pronoun is joining clauses, so a comma; anything else introduces an expansion, so a
colon. Two comma splices the rule could not see were fixed by hand, and one case where a blockquote
marker sat between the dash and the word after it, so the rule read ">" instead of "so".

🔴 EIGHT EN DASHES STAY, AND audit.py IS THE REASON. Replacing them with "to" broke check 10
immediately: `audit.py` FORMATS published figures as `"**%d–%d MW**"` and `"$%s – $%s per year"`, so the
range separator is part of a published figure, not prose. Changing it means changing the formatter in
audit.py, the page, and the React app together, and regenerating everything, to gain a typographic
nicety on a numeric range. Reverted rather than pushed through, and the seven ranges plus one
`advection–diffusion` are what remain. **Left as an open question for the user rather than decided
quietly.**

### 2026-08-28 - The deployment, and a correction: the SERVER does need part of data/

**One service, decided by the user: "I only want one deployment which supports the new UI and a live
agent working on the deployed project."** `serve_live.py` already serves the artefact folder statically
AND answers `/api/*`, so one process is the whole deployment and no code was needed to support it. Both
front ends call the agent with a relative url, `fetch('api/live/<site>')`, so a split origin would have
meant inventing a configurable API base plus CORS, which is two new ways for live to break.

```
python AGENTIC-ARBITER/src/serve_live.py --allow-paid --host 0.0.0.0 --port $PORT --max-live-calls 48
    /app/              the React interface
    /                  the single-file page
    /api/live/<site>   a live run
```

New at the repo root: `Dockerfile`, `render.yaml`, `requirements.txt`, and a *Deploying it* section in
README. `requirements.txt` is **derived**: the import graph from `serve_live.py` was walked, 12 modules,
and only `numpy` and `psychrolib` are third party. `physics` looks like a third and is not, it is a
local package at `src/physics/`, which a first pass missed by looking for `physics.py` rather than
`physics/`. **No GPU:** nvidia-warp solved the plume fields at build time and they ship as data.

⚠ **NOT VERIFIED: the Docker image itself.** Docker is unavailable in this environment, so the
Dockerfile is reasoned rather than built. The start command inside it IS verified, which is the part
that usually goes wrong.

**THE KEY, and the blocker that had to be fixed first.** `testing/common.py:load_key()` read
`<root>/.env` and nothing else. That file is gitignored and must stay so, therefore it does not exist
on a host: the live agent could only ever have started on this one machine. It now reads
`FORTYGUARD_API_KEY` from the environment first, with the file as fallback. `render.yaml` declares the
variable with `sync: false`, so Render prompts and stores it encrypted and it is never in the
repository, not even in the Docker build context.

**⚠ THE LIVE ENDPOINT IS OPEN, BY THE OWNER'S EXPLICIT DECISION.** Their words: "let the user make live
calls, whoever it may be. there should be enough live calls limit available for multiple judges to run
the agent and they will refresh the credits themselves." `serve_live.py` has no authentication of any
kind, checked for tokens, bearer headers, origin and referer. `MAX_LIVE_CALLS` is the only ceiling,
counted per day. Each run is one heatmap window at 4,220 credits, about 246 runs remain, so 48 a day is
roughly five days of headroom and 24 a day roughly ten.

### 🔴 CORRECTION: "data/ is never needed at runtime" was half wrong

Recorded prominently because I told the user the wrong thing and then acted on it.

**What I claimed:** `AGENTIC-ARBITER/data/` is never fetched at runtime, proved by reading every fetch
in the page. **That part is true and remains true: the BROWSER never touches it.**

**What I missed:** the SERVER does. `serve_live.py` imports `live.py` which imports `agent.py`, and
`agent.py` reads `data/geometry/` at import time. Tested by hiding the folder:

```
live.py selftest   FileNotFoundError: data\geometry\selected_site.json
serve_live.py      will not start at all
```

**The minimal set, measured by hiding each subfolder in turn and re-running the selftest:**

| subfolder | size | needed by the server |
|---|---|---|
| `geometry` | **13.0 MB**, 1,185 files | **YES**, tracked in the repo now |
| `weather` | 229.2 MB | no |
| `national_fields` | 279.5 MB | no |
| `imagery` | 299.9 MB | no |
| `live_cache` | 217.6 MB | no, and the server recreates it if absent |

So the structure changed: the whole-folder junction is gone, `data/geometry/` is a **real directory
inside the repo**, and the other four are **per-folder junctions** to `D:/FGHackathon-data`.
`.gitignore` carries `AGENTIC-ARBITER/data/*` with `!AGENTIC-ARBITER/data/geometry/`.

Confirmed by hiding all four at once, which is what a fresh clone has: selftest ALL PASS, `/api/health`
200, `/app/` 200, `/sites.json` 200.

⚠ A TRAP THIS EXPOSED TWICE: running the server or the selftest RECREATES `data/live_cache/` as a real
empty directory, which then collides with restoring the junction under the same name. It has no files,
only an empty `ashburn/` subdirectory, so `Directory.Delete(path, recursive=true)` then rename the
junction back.

### 2026-08-28 - The repository is now what a judge sees, and nothing more

**The user: "Only 1 read me md file is to be there for the judges which will be professional."**
61 tracked `.md` files became 18; the 43 moved to `D:/FGHackathon-notes` with their original relative
paths. `IMAGERY-REVIEW/` followed them: 17 files, 5.1 MB of ESRI-versus-USGS comparison JPGs, and
nothing in any `.py`, `.js`, `.mjs` or `.html` reads it.

🔴 THE KEEP LIST WAS MEASURED. Every `.py` was stripped of comments and docstrings and the `.md`
filenames surviving inside string literals are the ones code actually opens. Moving one would have
broken `audit.py`'s 2,216 checks or `run_all`'s context step:

    README.md, API-USAGE.md, CLAUDE.md, RECIRCULATION-DEFENCE.md, money-sources.md,
    demo/README.md, demo/money-sources.md, CONTEXT/*.md

### 🔴 validation-data/ WAS QUIETLY HOLDING UP TWO PUBLISHED CLAIMS WITH NO GATE WATCHING IT

Asked whether it was needed, I first said yes because "the two recirculation tests read it". **They did
not.** They read `os.path.join(SCRATCH, fn)`, and `SCRATCH` in `testing/common.py` names ONE Claude
session's temp directory by id, `48b2e995-a9e0-4f0c-8ab4-8cbe4f628a17`, which no longer exists. So
`test_n21_validate.py` and `test_n22_calibrate.py` had been exiting 2 with *"no field data found in the
scratchpad"*, which reads like an absent dataset rather than a stale path.

The data was never absent. All SEVEN CSVs those tests ask for are in `validation-data/`, digitised from
California Energy Commission report **CEC-500-2013-065**, whose three source PDFs sit beside them, and
they are the evidence behind README's recirculation and 67-Prairie-Grass claims. **`run_all.py` does not
run those two tests, so nothing anywhere went red.** That is precisely how a folder like this gets
deleted by accident.

Fixed rather than noted: `common.py` gained `VALIDATION` and `field_path()` now searches
`(SCRATCH, VALIDATION, FIXTURES, HERE)`. Both tests run again:

- `test_n21_validate` **PASS**, the solver reproduces the measured shape at **r=0.798** in its better
  configuration (N-11 OFF), against 1-minute field data from six air-cooled condensers.
- `test_n22_calibrate` **PASS**, the closure fits the field data on held-out RMS.

### 2026-08-28 - Deployment prep, and the prose the UI stopped showing

**Deployment shape chosen by the user:** both the static demo and the live API on ONE Python host, so
`fetch('api/live/...')` stays same-origin and needs no code change, plus a static replay-only mirror on
GitHub Pages as the always-up fallback. `serve_live.py` already serves `demo/` statically and answers
`/api/*`, so the single-host option needs nothing written.

**Tracked bytes: 1,823 MB to 962 MB**, inside GitHub's recommended 1 GB. Nothing exceeded the 100 MB
per-file hard limit (largest is `scenarios.json` at 30 MB), so size was a repository problem rather than
a file problem.

| Removed | Size | Why it was safe |
|---|---|---|
| `AGENTIC-ARBITER/data/` | 1,039 MB, 2,120 files | never fetched at runtime; moved to `D:/FGHackathon-data` with a DIRECTORY JUNCTION at the old path so all twelve scripts keep working |
| unoffered artefacts | 28.3 MB, 153 files | the 14 sites `sites.json` marks not offerable; `#c_site` only ever holds an offerable key |

⚠ THE COST, STATED: a fresh clone cannot regenerate the pipeline without fetching the data folder
separately. That was the accepted trade.

**README migration, the brief's last unfinished item.** "Strip all other verbose, explanatory paragraphs
from the UI entirely and compile them into a well-structured README.md file." A new section, *Reading the
results stage, panel by panel*, 1,192 words, one subsection per panel, so nothing on screen is reachable
only by clicking.

🔴 IT DELIBERATELY QUOTES NO SITE-SPECIFIC FIGURE. The folded prose contains runtime numbers that change
with the selected site and the controls. Copying them into a static document would manufacture exactly
the class of claim `audit.py` exists to prevent: a figure no test re-reads. So the section explains what
each panel is FOR and what its arithmetic means, and leaves every number to the artefacts.

### 2026-08-28 - The results stage stopped being a report you scroll through

**The user, on the screen they cared most about:** "by the time user reaches the 'read the decision'
tab, it's the same layout as the html file that I told you I didnt like the UI of... seems like a
report generated through which you keep scrolling through with dump of too much technical information
and not an interactive app... I wanted you to be intelligent here and only display one or two liners
for every aspect and only explain in a pop up option."

**MEASURED FIRST, because "too much text" needs a number.** A probe drove the app to the results stage
and counted the prose actually on screen, per card: **1,680 words in 52 blocks across 13 cards**, most
of it written at runtime by the renderers rather than sitting in the markup. After the change:
**260 words in 19 blocks.** An 85 % cut.

**AND NOTHING QUANTITATIVE MOVED.** Tile, table and canvas counts per card are identical before and
after, checked card by card: decisioncard 5 tiles 1 table 2 canvases, headcard 5/0/0, cfcard 0/1/3, and
so on. `app/src/lib/declutter.ts` selects `p, li, details` and excludes
`.tile, table, canvas, #tape, .ev, .plate-cell, .rail-step, svg`, so it never looks at a figure. The
brief's line holds: "Do not modify the existing reports, graphs, or numerical data cards."

**HOW IT WORKS.** Each card gets one authored lead of one or two lines in plain language, and every
prose block over 14 words is hidden and folded into one button per card that opens it in a modal
(`DetailModal.tsx`). The engine keeps drawing exactly what it drew; this reorganises the result. Done
as a DOM pass rather than an edit to the engine because the engine is lifted byte for byte and a
verifier fails the build if a character moves.

Two bugs of mine on the way, both worth keeping:
- The pass appended a new fold row on every run, because the engine redraws PARTS of a card without
  replacing it. The screen showed "What a live run costs (3)" beside "(1)". It now rebuilds the single
  row from the folded nodes themselves, which are still in the DOM and still marked, so one pass
  produces exactly one correct row from any starting state.
- The audit that measured the improvement counted `textContent`, which includes hidden nodes, so it
  reported prose going UP after 52 blocks were folded away.

### 2026-08-28 - No dashes anywhere a reader looks

**The user:** "Throughout this project's text that you display and render, dont use '-' dashes."

**139 em dashes removed from displayed text, in two passes with different tools, because they needed
different care.**

| Where | Count | How |
|---|---|---|
| the page's body markup | 28 | 23 became a colon, 4 a comma, 1 a full stop |
| the page script's STRING LITERALS | 111 | same rule, applied by a classifier |
| the page script's COMMENTS | 10 | **left alone**, deliberately |

The markup pass was straightforward. The script needed a real scanner: a regex cannot tell
`'<code>fetch()</code> from '` from a comment that quotes code, and 10 of the 121 occurrences are the
page's own documentation, which there is no reader benefit in rewriting. So a single pass classifies
every character as code, comment, string or regex, asserts the classification round-trips to the
original, and rewrites inside strings only. It printed every change and refused to write if any dash
remained in a string.

That count is why the scanner mattered: I had assumed most of the script's dashes were in comments. It
was the other way round, 111 to 10, and they included the DAY dropdown ("crossing: 2025-03-11"), the
level anchor ("none: believe FortyGuard"), the decision legend and six of fourteen card headings.

`decide` and `explainHour` therefore changed in the page, which `audit_nothing_lost.py` correctly
flagged. Both are now declared exceptions with the reason and the date, so a THIRD function changing
still fails. Its HANDOFF.md line check gained the same treatment, anchored on the four shapes
`bump_spend_docs.py` owns rather than on whichever line failed last.

⚠ STILL WITH DASHES, and not swept: the page's own comments, `CONTEXT/`, and `README.md` prose the
user wrote. Standing rule B2 governs those.

### 2026-08-28 - The new UI now carries the whole product, engine and all

**The user's correction:** the React app was a pick screen whose Configure button led back to
`demo/index.html`. Two of three stages, 18 cards, the reasoning tape and the live agent were not in
the new UI at all. Full account in section 0.

**What was measured before anything was built.** The page has 124 top-level functions. Rooted at the
real entry points, the configure + results + live closure is **100 functions, 208 KB**; the 24 outside
it are exactly the pick-stage map and search code the React app had already replaced. So the seam
falls at a natural boundary rather than through the middle of something, and with the pick stage
fenced off the engine calls **nothing** on React's side. Zero crossings, measured.

A finding that made the lift far safer than the raw grep counts suggested: **`R` is not a global.**
146 apparent references are almost all local `const R = decide();` plus right-margin variables
(`const L=46, R=14`). The genuinely shared state is 55 top-level declarations, all of which keep their
literal names in one module, so every reference stays byte-identical.

**Built:**
- `AGENTIC-ARBITER/results/engine.mjs` - 100 functions lifted byte for byte, plus a **three-function
  adapter** (`attachSites`, `currentSite`, `currentStage`) that is the only written code in the file
  and is pinned by hash so logic cannot accumulate there.
- `app/src/generated/engine-markup.ts` - the configure and results markup, 39 KB, six blocks, verbatim.
- `app/src/generated/engine.css` - the page's stylesheet, 96 KB, verbatim. It lifts cleanly because the
  page's CSS has **zero `url()` references** by deliberate design, recorded in its own comment: no
  `@font-face`, no `@import`, because the page must work offline and `verify_site_panels.py` demands
  byte-identical canvases, which a font arriving over the network cannot promise.
- `app/src/lib/engine.ts`, `app/src/components/EngineStage.tsx` - the seam.
- `testing/verify_results_matches_page.py`, `testing/verify_view_matches_page.py`,
  `testing/verify_app_flow.py` - three new gates, wired into `run_all.py`. **31 steps became 33.**

**A real defect found in the page and fixed there.** A CSS comment contained the text
`had THREE `*/` closers and one `/*` opener` - prose ABOUT the original bug. CSS comments have no
escaping, so that `*/` closed the comment, nine words of English were parsed as CSS, and the following
`/*` opened a new one. **The delimiters therefore balanced**, so `audit.py`'s `check_css_comments`
passed: it counts delimiters, and the count was right. Browsers error-recover to the next resync
point, so nothing ever looked wrong. It surfaced only when esbuild's stricter minifier warned during a
Vite build. `audit.py` gained a second check that asks the question the other way round - is any text
OUTSIDE the comments not plausibly CSS - and the count went 2,215 to 2,216.

**`audit_nothing_lost.py` was silently going vacuous.** It compared against `HEAD`, which was the
pre-work commit when it was written. Once the work was committed, `HEAD` contained the changes and
every comparison trivially agreed; the first run after committing reported 8 losses that were nothing
of the kind, because the rename had landed and `git show HEAD:INTAKE-ARBITER/...` simply failed. The
baseline is now a pinned commit id, and the section that read `git status` for deletions - zero, once
the rename was committed - now walks **all 5,975 paths that existed at the baseline** instead.

### 2026-08-28 - The pick screen had no way forward, and the URL layout that fixed it
The user caught that the React screen offered no "configure the plant" action. Added
`SelectedBar.tsx`, which hands off to `demo/index.html?site=<metro>` rather than pretending the
configure stage has been rebuilt. That one link exposed a real layout bug: the app's relative artefact
fetches only worked in vite dev, and both `testing/serve_app.py` and the intended production layout
would have 404'd. Fixed with a single `ART = '../'` base. Nothing was ever removed from the shipped
page; verified element by element. Detail in section 0.


### 2026-08-28 - Step 4: the React pick screen exists and is verified
`AGENTIC-ARBITER/app/`, nine source files, consuming `core/`, `charts/` and the same artefacts. Every
behaviour in the user's UI brief measured through the app's own probe surface. Five defects found and
fixed on the way, the real one being that maplibre 6 needs `setWorkerUrl` pointed at a properly
bundled worker. Detail in section 0. `CLAUDE.md` corrected: it forbade the bundler and the
`package.json` this work requires, which would have led a future session to undo it.


### 2026-08-28 - Steps 1 to 3 of the React migration, all green
`core/` (6 modules) and `charts/primitives.mjs` extracted from `demo/index.html`; all five
cross-implementation verifiers repointed to import them; `run_all.py` step 29 added as the drift gate
between the two copies. Detail in section 0. Nothing about the shipped page changed: audit 2,215/0,
palette 34/0, state filter 62/0, map hover PASS, all five verifiers PASS with corpora unchanged.


### 2026-08-28 - UI direction set, and the core extracted
The user said the UI is monotonous, has no visual hierarchy, and that the font reads as machine-like.
They asked whether the HTML could be replaced with a front end the `frontend-design` skill and the
21st.dev MCP server can act on, **without losing the deterministic output**, and chose the staged
plan. Details and the current position are in section 0.

**Two findings that shaped the answer:**
- 🔴 **The 21st.dev MCP server was configured but never loading.** It sat under the project key
  `D:/FGHackathon` while the session ran as `d:/FGHackathon`. Those are separate entries in
  `~/.claude.json`, so the tools had never appeared in any session, including the one where they were
  first asked for. Now registered on both keys. A backup is at `~/.claude.json.bak-ctx`.
- **The `frontend-design` skill is stack-agnostic.** It is design direction: palette, type scale,
  taking one justified risk. It does not emit React and does not care about the stack. **Only
  21st.dev is a reason to change stack**, because it emits React plus Tailwind.

**What determinism actually depends on**, established by reading the checks rather than assuming:
nothing in the verification layer needs vanilla JavaScript. It needs the agent to be **findable as
source text in one file**, which is a fragile coupling and the reason the extraction makes
verification *stronger* rather than weaker. Only four audit checks read the page at all
(`check_duplicate_element_ids`, `check_page_javascript_parses`, `check_panels_are_per_site`,
`check_retracted_claims`) and **none of them requires prose to be present**, so the brief's aggressive
decluttering is safe. The stated limits and the four sources live in `money-sources.md`, checked by
audit check 12, not in the page.


### 2026-08-28 - The context pack itself
Created `CONTEXT/` at the user's request: a folder that holds the project's durable state, is updated
as part of every change, and is re-read after every context compaction so quality is not lost to a
summary.

- `CLAUDE.md` at the repo root is the mechanism. It is loaded automatically every session and after
  every compaction, and it points here. Without it, "read the context folder" would be an intention
  rather than a behaviour.
- `sync_context.py` makes freshness mechanical rather than promised: it regenerates the memory mirror
  and the figures block, and fails on drift. It also asserts two standing rules that happen to be
  checkable (the live-agent elements exist; the map still has its second GeoJSON source).
- `HANDOFF.md` and `READING-THE-AGENT.md` moved in from the repo root. **This required code edits**,
  because `audit.py` and `testing/bump_spend_docs.py` open both by constructed path; prose citations
  of the form "HANDOFF section 6.3" were unaffected. See section 4 below for what was touched.
- Two stale paths fixed at the source in the auto-memory: `ship-production-not-mvp.md` still said
  `INTAKE-ARBITER/PLAN.md`, and `subagents-permitted.md` still described HANDOFF as 250 KB.
- `run_all.py` gained step 28, the pack's own freshness check. That moved the step count, which is
  itself a published figure in `README.md`, so it was updated in the same breath. The check caught the
  change immediately, which is the behaviour it exists for.

**Building the pack meant reading the repository properly, and that surfaced seven real defects.**
Six are fixed; the seventh is recorded in section 5 as a decision.

1. 🔴 **`run_all.py` contradicted its own comment.** `verify_state_filter.py` exits **3** when
   maplibre cannot be fetched from unpkg, because the page degrades to a note without it by design.
   The runner treated *any* non-zero code as a failed step, so on a machine with no route to unpkg the
   whole 28-step proof went red for a reason unrelated to anything it proves. A step can now
   **declare** which exit codes mean "could not run", with the reason; those are printed at the step
   and again in the banner, and the banner narrows its completion claim to what actually ran. Exit 1
   from that same step still fails the rebuild. **Not** fixed by treating 3 as success, which would be
   gotcha #74 all over again.
2. **`#mf_q` was a combobox that never said whether it was open.** `aria-expanded` was written once,
   hard-coded to `"false"` in the markup, and never updated, so a screen reader announced a closed
   list with eight facilities on screen. Worse than no ARIA role at all: the role promises an
   expandable listbox and then lies about its state. Now set at every open and every close.
   **Mine, from the same day the dropdown was built.**
3. **`#secnav` linked to a card that no longer exists.** `href="#limitscard"` survived the removal of
   the "Honest limits" card on 2026-08-26. A dead index entry is worse than a missing one: it tells a
   reader the page makes a disclosure it no longer makes here. Removed. `drawLimits()` is untouched
   and still derives all four limits from the artefacts, guarded by `if(!el) return;`.
4. **`setStage()` still carried a branch that would hide `#livecard`.** `data-needs="live"` was taken
   off the card on 2026-08-25, so the branch was dead, but its only possible effect was to hide the
   live card, which standing rule C1 forbids outright. Removing it makes the rule a property of the
   code rather than a note beside it. `data-needs="plume"` is live and different, and stays.
5. **`verify_state_filter.py` died with a traceback** instead of its documented exit 3 if the page's
   `US_STATE_NAMES` table were renamed: `load_state_names()` used `str.index`, which raises, and it
   runs before the browser work. Now `find`, and it reports the could-not-run properly. Verified by
   renaming the table in a copy of the page: exit 3 with a diagnosis. **Mine.**
6. **`demo/README.md` quoted three wrong `run_all.py` step numbers** (`verify_palette` as step 26, it
   is 24; `verify_site_panels` as step 20, it is 25) and said `verify_state_filter` makes 60
   assertions when it makes 62. Corrected. Step numbers shift every time a step is added, which is
   exactly why this pack derives its figures instead of quoting them.
7. **`README.md` published two stale figures about the gotcha registry**: "96 gotchas" and "running to
   #185". Measured against the file: section 10 holds **195** numbered entries, 1 to 196 with #50
   absent. Both corrected. Neither was re-derivable, which is the defect standing rule A3 exists to
   catch.

### 2026-08-28 - The map filter bar: four changes, three real defects
The user asked for four things. Each is now covered by assertions in
`testing/verify_state_filter.py`, which is new and is `run_all.py` step 27.

1. **The facility search box has its dropdown back.** `#mf_q` now renders `#mf_drop`, up to eight
   `.mfrow` rows carrying the facility name, its state in full, and a READY or CANDIDATE pill.
   Choosing a row flies the map to that facility and opens its inspector. It is a **separate element
   from `#searchresults`** on purpose: `verify_map_hover.py` drives `#sitesearch` and selects
   `.srchrow`, so reusing those ids would put two writers on one element.
2. **States are named, not coded.** `US_STATE_NAMES` covers all fifty plus DC; the select shows
   "California · 46", sorted by name, each count read from the registry. The expansion also reached
   the hover readout, the inspector's *Where* row, and both search lists, and it expands a trailing
   ", CA" **inside** a label, because `unified_sites.json` is inconsistent: 424 of its 637 labels
   already read "Ashburn, Virginia" while 213 read "Reston, VA". The artefact was not rewritten;
   this is a display-time expansion only.
3. **A selected state shows individual small circles**, fitted to that state's own extent.
   **This needed a second GeoJSON source.** maplibre fixes clustering at source creation and offers
   no setter, so a clustered source returns *cluster* features at low zoom whatever the layer filters
   say, and hiding the cluster layers reveals nothing. There are now two sources over the same 637
   features, one clustered and one flat, with exactly one visible. Radii step down to 7 / 5.5 / 4.5
   from the national 9 / 7 / 5.
4. **The page opens on California**, fitted, with no animation on load.

**Defects found and fixed on the way:**
- 🔴 `addData` was gated on `map.isStyleLoaded()`, which stays false while the OpenStreetMap basemap
  has tiles in flight. **On any network that blocks or throttles those tiles, none of the 637
  facilities were added to the map at all.** Now gated on `map.getLayer('basemap')`, which reads the
  parsed style and is independent of tiles. This is the second time this gate has bitten; it was
  `map.on('load')` before, tile-dependent for the same reason.
- The camera fit animated unconditionally, ignoring `prefers-reduced-motion`. Now
  `motionOK() ? 620 : 0`, which is both correct behaviour and the only state a headless check can
  measure.
- Search rows for a facility with no published run carried `aria-disabled="true"` while
  `searchOpen()` routes them to the inspector. A row that performs an action must not announce itself
  as disabled. Now `data-ready="0"`. **This one was mine, from earlier the same day.**

**A fourth defect, from extending the palette check** to the frosted surfaces nothing had measured:
`--glass` is translucent, so text on the bezel, the KPI cards, the drawer and the new dropdown is
text on a *composite*, and the drawer opens from a map click, which puts it on glass over the
**basemap**. Measured that way, light-theme `--muted` was **4.44:1**, under the 4.5:1 text floor, and
only 4.53:1 on `--surface-2`. It is now `#6c6c75`, clearing **4.64:1 on the worst of five surfaces**.
Both basemap values are measured off real screenshots (**#323232** dark, **#cfcfcf** light), located
by a marker the page paints at its own canvas origin so the two samples cover identical pixels. The
first draft of that constant *guessed* #dcdcdc and the measurement came back half a stop darker,
which is why it is measured.

**Also:** `verify_palette.py` now reads `rgba()` tokens, not only hex, and treats a surface it names
but cannot resolve as a **failure** rather than a skip. The old loop silently `continue`d past an
unknown surface, which would have reported PASS for a pair it never measured.

### 2026-08-28 (earlier) - Masthead cut, em dashes removed
Four paragraphs to three (162 words). The "rational hedge" argument moved into an `.info` popover
whose text is duplicated in the trigger's `aria-label`. Em dashes stripped from the six page strings
and twelve README rows I had written; the user's own prose left untouched.

### 2026-08-27 - Renamed INTAKE-ARBITER to AGENTIC-ARBITER
2,737 string occurrences across 2,649 files, the split bezel wordmark, and all 266 report PDFs
regenerated rather than byte-patched. Details and the deliberate exceptions in
`04-STANDING-RULES` C2.

*Earlier history is in `CONTEXT/HANDOFF.md`, which is the full record. Do not read it whole.*

---

## 4. Files touched by the CONTEXT move

Recorded here because a future session will otherwise wonder why these paths look unusual.

| File | What changed |
|---|---|
| `AGENTIC-ARBITER/src/audit.py` | the constructed paths to `HANDOFF.md` and `READING-THE-AGENT.md` now point into `CONTEXT/` |
| `testing/bump_spend_docs.py` | same, for `HANDOFF.md` |
| `README.md` | any markdown link to either document |

`audit.py` is the proof that this was done correctly: it re-reads both documents and would fail if a
path were wrong. It reports **2,215 passed, 0 failures** after the move.

---

## 5. Open items

Not blockers, and each is stated rather than quietly dropped.

### 🔴 BLOCKER, DEFERRED BY THE USER 2026-08-28: two measured day-pairs are not in the figures

**The user's decision: "dont do it right now, we'll do it later. just save the pairs somewhere for
now."** So nothing has been rebuilt and no published figure has been touched. This entry is the save.

**THE FIXTURES ARE SAFE.** All four files are tracked and committed, 7.2 MB each, 28.9 MB of paid
measured data:

```
testing/results/fixtures/n26_f_2026-08-25.json   n26_h_2026-08-25.json
testing/results/fixtures/n26_f_2026-08-26.json   n26_h_2026-08-26.json
```

`testing/results/n26_manifest.json` lists **6 complete forecast/outcome day-pairs**. The shipped
artefacts were built from **4**. `backtest.py` calls `perceive_fortyguard()`, which reads *every*
complete pair on disk, so a pipeline run today picks up all six.

**IT IS NOT NONDETERMINISM AND NOT A CODE CHANGE.** Proved by regenerating `backtest.json` from the
committed `trace.json` with the current `backtest.py`: the diff ADDS `/fortyguard_offsets/4` and
`/5`, dated 2026-08-25 and 2026-08-26. New input data, never adopted. The manifest was last committed
2026-08-27 in `01cc7aa`.

**WHAT MOVES WHEN IT IS ADOPTED.** Measured once, recorded here so nobody has to spend another full
pipeline run deriving it:

| Figure | Shipped, 4 pairs | Regenerated, 6 pairs |
|---|---|---|
| Pooled bound coverage | **65.6 %** (0.6559) | **78.6 %** (0.7857) |
| Attainable ceiling, n/(n+1) | 80.0 % (4/5) | 85.7 % (6/7) |
| Ladder 5 unanchored coverage | 0.9865 | 0.9165 |
| Unanchored cost | 561.7 h/yr | 312.8 h/yr |
| Ladder 5 + unanchored, offsets rotated | -156.0 | +92.8 |
| Significant reversal axes | 3 | 2 |
| `backtest.json` | | 51 values changed, +10 keys, -5 |

The 90 % promise is unchanged and the pre-registered test is **still NOT MET** either way, so the
honesty story survives; it gets stronger, because the bound would be measured on six real day-pairs
instead of four. Adopting it means restating `README.md` lines 119, 278 and 363, the CONTEXT figures,
and regenerating 243 artefacts and 266 PDFs.

**⚠ CONSEQUENCE WHILE THIS IS DEFERRED: `run_all.py` DOES NOT EXIT 0.** It regenerates and then
audits, so it rebuilds with six pairs and then fails `audit.py` against docs that quote four. Two
steps fail: `every other offerable site, on its own data`, and `AUDIT: everything, mechanically`.
`audit.py` run on its own against the committed artefacts is still **2,216 passed, 0 failures**,
because the docs and the shipped artefacts agree with each other. Both describe the four-pair state.

This matters because `README.md` says "If `run_all.py` is not green, do not believe a number on the
page." Today the honest statement is narrower: **the shipped numbers are internally consistent and
audited, and they are not reproducible from a full pipeline run until this is resolved.**

⚠ AND A TRAP FOR THE NEXT SESSION: `run_all.py` and `build_sites.py` REWRITE the artefacts in place.
A run leaves 243 modified files whose numbers no longer match the published figures. `git checkout --
AGENTIC-ARBITER/demo/` restores them. Do not read figures off the tree during or after a partial run;
one set of screenshots in this session caught a half-rewritten state and showed an 85.7 % ceiling on a
page whose documents say 80 %.

- **The empty `INTAKE-ARBITER/` husk cannot be deleted.** The editor's file watcher holds the
  directory. Safe to delete once released; nothing reads it.
- **The user's own prose still contains em dashes** deeper in the page and in the older documents.
  The rule governs what I write; sweeping theirs needs their say-so
  (`04-STANDING-RULES` B2).
- **`verify_palette.py` does not measure decorative borders on glass.** A pill's border on the
  light-theme frosted panel is about 1.06:1, which is below the 3:1 non-text floor but is not
  *required to identify a component or its state*, so it is out of scope for WCAG 1.4.11. Recorded so
  the omission is a decision rather than an oversight.
- **Write-only state in the page.** `INSPECT_KEY`, `LIVEJOB` and `ENV` are assigned or merely
  declared and never read anywhere. Harmless, and `audit.py`'s dead-code check cannot see them because
  it walks function nodes only. **Not removed:** `LIVEJOB` sits inside `runLive()`, and standing rule
  C1 says to ask before changing the live path. Editing working live code to tidy a dead variable is
  not obviously worth it.
- **`verify_api_defects.py` is the only paid verifier, always exits 0, and is deliberately not wired
  into `run_all.py`** -- but nothing in `run_all.py` says so, so its absence reads as an oversight
  rather than a decision. Recorded in `03-VERIFICATION` section 3 instead.
- **Whether `verify_site_panels.py` passes with the network fully blocked is unverified.** It asserts
  nothing about any CDN, but the page it renders fetches maplibre from one.

*(The scratch drivers that used to sit in `AGENTIC-ARBITER/demo/` -- `_agentlink_driver.html`,
`_phone.html`, `_shot.html` -- and `testing/verify_agent_link.py` are all gone as of 2026-08-28.)*
