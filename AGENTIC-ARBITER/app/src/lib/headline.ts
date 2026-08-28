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
  n56_audit: Array<{
    step: string
    anchor: string
    test_days: number
    agent_safe_free_h: number
    incumbent_safe_free_h: number
    gain_h_per_year: number
  }>
}
type Trace = { cycle: { pooled_coverage: number } }
type Money = { cells: Array<{ hours_label: string; usd_per_mw_it_per_year: number }> }

export type Headline = {
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
}

/** The shipped site. `metros.py` calls it DEFAULT_METRO and its value is "ashburn". */
export const DEFAULT_METRO = 'ashburn'

export function headlineFigures(bt: Backtest, t: Trace, mn: Money, manifest: Manifest): Headline {
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
  const footprintM2 =
    manifest.sites.find((s) => s.key === DEFAULT_METRO)?.footprint_m2 ?? NaN
  const mwLo = (footprintM2 * (scale.w_per_m2_average_load ?? NaN)) / 1e6
  const mwHi = (footprintM2 * (scale.w_per_m2_installed ?? NaN)) / 1e6

  return {
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

export async function loadHeadline(manifest: Manifest): Promise<Headline> {
  const grab = async <T,>(n: string): Promise<T> => {
    const r = await fetch(ART + n, { cache: 'no-cache' })
    if (!r.ok) throw new Error(`${n}: HTTP ${r.status}`)
    return (await r.json()) as T
  }
  const [bt, t, mn] = await Promise.all([
    grab<Backtest>('backtest.json'),
    grab<Trace>('trace.json'),
    grab<Money>('money.json'),
  ])
  return headlineFigures(bt, t, mn, manifest)
}
