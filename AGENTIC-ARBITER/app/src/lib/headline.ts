/* The five headline figures, derived exactly as audit.py derives them.
   ================================================================================================
   THE BRIEF SAYS: "Do not modify the existing reports, graphs, or numerical data cards. Leave all
   quantitative elements exactly as they are." So these cards must show the SAME numbers as the
   shipped page, to the last digit.

   WHY NOT PORT drawPlate(). It is 12,377 characters and it also writes innerHTML, tiles and prose.
   What is needed here is five numbers, and there is already an authoritative statement of how each
   one is derived: audit.py's front-door registry, check 10, which re-reads every figure published in
   README.md from the emitted JSON and fails if the formatted string a reader sees has drifted.

   EVERY DERIVATION BELOW WAS REPRODUCED IN PYTHON FIRST and checked against the published strings
   before a line of this file was written. All twelve matched, including the intermediate values:

       mechanical cooling cut        10.7 %              incumbent chiller hours   9,510 h
       chiller-hours avoided        +406 h/yr            agent chiller hours       8,496 h
       $/MW-IT/yr floor          $5,522                  site footprint           86,280 m2
       $/MW-IT/yr ceiling        $7,990                  site MW range            61-121 MW
       worth at this site        $334,269 - $967,245     hours of real weather    43,763 h
       bound coverage, measured     65.6 %               money cells swept        16 cells

   ⚠ THIS IS A SECOND PLACE THE DERIVATIONS LIVE, and that is a drift surface. It is accepted only
   because audit.py check 10 independently re-derives all of them from the same artefacts and fails
   on a mismatch, so a change to the science breaks the audit rather than silently changing this card.
   When the page is retired, these five should be emitted once by Python and read from a file instead.
   Recorded in CONTEXT/01-STATE.md.
   ================================================================================================ */

import { ART, type Manifest } from './artefacts'

/* Only the fields these five figures touch. Deliberately narrow: a wide type here would invite
   reading things this module has no business knowing. */
type Backtest = {
  hours: number
  days: number
  sensitivity?: { rows: Array<{ axis: string; value: number; gain_h_per_year: number }> }
  n56_audit: Array<{
    step: string
    anchor: string
    test_days: number
    agent_safe_free_h: number
    incumbent_safe_free_h: number
    gain_h_per_year: number
  }>
}
type Trace = {
  cycle: {
    pooled_coverage: number
    margin_trajectory?: Array<{ margin_c: number }>
  }
}
type Money = {
  cells: Array<{ hours_label: string; usd_per_mw_it_per_year: number }>
  hours_rows: Array<{ label: string; is_base?: boolean }>
}

/** A sparkline's values plus the caption that says what they ARE. Never a caption without values. */
export type Series = { vals: number[]; cap: string; labels?: string[] }

export type Headline = {
  /** Which site these figures are actually for. Not always the one asked for: see loadHeadline. */
  usedKey?: string
  /** True when the requested site had no agent run and the shipped reference was substituted. */
  isFallback?: boolean
  cutPct: number
  mechIncumbentH: number
  mechAgentH: number
  gainHPerYear: number
  usdLo: number
  usdHi: number
  mwLo: number
  mwHi: number
  footprintM2: number
  usdPerMwLo: number
  usdPerMwHi: number
  moneyCells: number
  weatherHours: number
  coveragePct: number
  /* THREE REAL SERIES, and only three. The single-file page's plateSparks() draws exactly these, and
     the other two cards get NO chart because there is no series behind them: a cut percentage and an
     hour count are single measurements, and inventing a shape for them would be decoration posing as
     evidence. */
  series: { gain?: Series; worth?: Series; cov?: Series }
}

/** The shipped site. `metros.py` calls it DEFAULT_METRO and its value is "ashburn". */
export const DEFAULT_METRO = 'ashburn'

export function headlineFigures(bt: Backtest, t: Trace, mn: Money, manifest: Manifest,
  forKey: string,
): Headline {
  /* THE SHIPPED ROW of the five-year ladder. Addressed by its `anchor` FIELD rather than by index:
     audit.py's comment records that this used to be `C[-2]`, which silently encoded "the unanchored
     row is last", so adding a rung to the ladder would have re-pointed it at the wrong configuration
     with nothing noticing. */
  const C = bt.n56_audit.filter((r) => r.step.startsWith('C '))
  const ship = C.filter((r) => r.anchor !== 'none').at(-1)
  if (!ship) throw new Error('backtest.json has no anchored row in the five-year ladder')

  /* MECHANICAL RUNTIME for both controllers, on that row. `hours / days` rather than a hard-coded 24,
     because the backtest's day length is a property of the data, not an assumption. */
  const hoursPerDay = bt.hours / bt.days
  const H = hoursPerDay * ship.test_days
  const mechAgentH = H - ship.agent_safe_free_h
  const mechIncumbentH = H - ship.incumbent_safe_free_h

  /* THE MONEY CELLS at the shipped notice period: 4 published tariffs x 4 published chiller
     efficiencies, swept rather than chosen. The range is the sweep, not a confidence interval. */
  const moneyRow = mn.cells
    .filter((c) => c.hours_label.startsWith('+ notice 3 h'))
    .map((c) => c.usd_per_mw_it_per_year)
  const usdPerMwLo = Math.min(...moneyRow)
  const usdPerMwHi = Math.max(...moneyRow)

  /* THE SITE'S OWN MEASURED SIZE, turned into an IT load range by two published densities: average
     load for the floor, installed capacity for the ceiling. */
  const scale = manifest.scale || {}
  /* 🔴 THE SELECTED SITE'S FOOTPRINT, NOT THE DEFAULT'S. This read `DEFAULT_METRO` unconditionally,
     which is why picking a different data centre left every figure on the first screen unchanged: the
     three artefacts were Ashburn's and so was the footprint the money range is scaled by. The user
     photographed an Alabama facility selected above Ashburn's numbers. */
  const footprintM2 =
    manifest.sites.find((s) => s.key === forKey)?.footprint_m2 ?? NaN
  const mwLo = (footprintM2 * (scale.w_per_m2_average_load ?? NaN)) / 1e6
  const mwHi = (footprintM2 * (scale.w_per_m2_installed ?? NaN)) / 1e6

  /* ---- THE THREE SERIES, lifted from the page's plateSparks() so the two cannot disagree -------
     1. GAIN BY FORECAST LEAD. The notice_h axis of the sensitivity sweep: 0, 1, 3 and 6 hours of
        notice against the chiller-hours each buys. This is the single most persuasive series in the
        project, because it is the forecast's value measured by varying only the forecast.
     2. THE MONEY CELLS, cheapest to dearest. Addressed through the base row's own label rather than
        by matching a string, which is how money.json says which row is the shipped one.
     3. THE MARGIN, RECALIBRATING. One value per day-pair, and it crosses zero, which is why the bars
        below are drawn from a zero baseline rather than from the bottom of the box. */
  const series: Headline['series'] = {}

  const notice = bt.sensitivity?.rows
    ?.filter((r) => r.axis === 'notice_h')
    ?.slice()
    ?.sort((x, y) => x.value - y.value)
  if (notice && notice.length >= 2) {
    series.gain = {
      vals: notice.map((r) => r.gain_h_per_year),
      labels: notice.map((r) => `${r.value}h`),
      cap: 'chiller-hours bought by each hour of notice',
    }
  }

  const baseRow = mn.hours_rows?.find((r) => r.is_base)
  const usd = mn.cells
    .filter((c) => c.hours_label === baseRow?.label)
    .map((c) => c.usd_per_mw_it_per_year)
    .sort((x, y) => x - y)
  if (usd.length >= 2) {
    series.worth = { vals: usd, cap: `${usd.length} swept cells, cheapest to dearest` }
  }

  const traj = t.cycle.margin_trajectory || []
  if (traj.length >= 2) {
    series.cov = {
      vals: traj.map((x) => x.margin_c),
      labels: traj.map((_, i) => `${i + 1}`),
      cap: `the margin recalibrating itself over ${traj.length} day-pairs`,
    }
  }

  return {
    series,
    cutPct: (100 * (mechIncumbentH - mechAgentH)) / mechIncumbentH,
    mechIncumbentH,
    mechAgentH,
    gainHPerYear: ship.gain_h_per_year,
    usdLo: usdPerMwLo * mwLo,
    usdHi: usdPerMwHi * mwHi,
    mwLo,
    mwHi,
    footprintM2,
    usdPerMwLo,
    usdPerMwHi,
    moneyCells: moneyRow.length,
    weatherHours: bt.hours,
    coveragePct: 100 * t.cycle.pooled_coverage,
  }
}

/** Dollars sized to fit a card: k above ten thousand, M above a million. The single-file page has the
 *  same helper and the same reason -- "$334,269" and "$967,245" side by side do not fit at 390 px. */
export function usdShort(v: number): string {
  if (!Number.isFinite(v)) return '–'
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2).replace(/\.?0+$/, '')}M`
  if (Math.abs(v) >= 1e4) return `$${Math.round(v / 1e3)}k`
  return `$${Math.round(v).toLocaleString('en-US')}`
}

/**
 * Load the three artefacts the first screen's figures come from, FOR ONE SITE.
 *
 * 🔴 IT USED TO IGNORE THE SELECTION ENTIRELY. It fetched the unprefixed `backtest.json`,
 * `trace.json` and `money.json`, which are Ashburn's, so every card on the pick screen showed
 * Ashburn no matter which of the 637 facilities was chosen. The single-file page was site-specific
 * here and the React rebuild had quietly lost it.
 *
 * FILENAMES COME FROM THE MANIFEST, never constructed. sites.json carries an `artefacts` map per
 * site: unprefixed for the metro, key-prefixed for a national site. A guessed name is a 404 that
 * looks like a missing feature (the engine's own loadSite() says the same thing).
 *
 * A FACILITY WITH NO AGENT RUN falls back to the shipped reference and SAYS SO through `usedKey`, so
 * the caller can label the figures rather than passing another site's numbers off as this one's.
 * Showing the default silently is exactly the bug being fixed.
 */
export async function loadHeadline(
  manifest: Manifest,
  siteKey: string = DEFAULT_METRO,
): Promise<Headline> {
  const grab = async <T,>(n: string): Promise<T> => {
    const r = await fetch(ART + n, { cache: 'no-cache' })
    if (!r.ok) throw new Error(`${n}: HTTP ${r.status}`)
    return (await r.json()) as T
  }
  /* Resolve the site, and fall back to the shipped reference when the one asked for has no run. A
     facility can be real, mapped and selectable while carrying no artefacts: sites.json marks those
     `offerable: false`, and the pick screen already says "No agent run published yet" for them. */
  const wanted = manifest.sites.find((s) => s.key === siteKey)
  const site =
    wanted && (wanted as { offerable?: boolean }).offerable
      ? wanted
      : manifest.sites.find((s) => s.key === DEFAULT_METRO)
  const usedKey = String((site as { key?: string })?.key ?? DEFAULT_METRO)
  const art = ((site as { artefacts?: Record<string, string> })?.artefacts) || {}

  const [bt, t, mn] = await Promise.all([
    grab<Backtest>(art.backtest || 'backtest.json'),
    grab<Trace>(art.trace || 'trace.json'),
    grab<Money>(art.money || 'money.json'),
  ])
  const figs = headlineFigures(bt, t, mn, manifest, usedKey)
  /* WHICH SITE THESE FIGURES ARE ACTUALLY FOR, so the caller can label them instead of implying they
     belong to whatever is selected. Reporting the substitution is the whole point of the fallback. */
  return { ...figs, usedKey, isFallback: usedKey !== siteKey }
}
