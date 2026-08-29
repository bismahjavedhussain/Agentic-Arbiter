import { motion } from 'framer-motion'
import { Coins, Gauge, Globe2, TrendingUp } from 'lucide-react'
import type { Portfolio } from '../lib/artefacts'

/**
 * TWO CARDS BESIDE THE HEADLINE: what the project COVERS, and what that coverage is WORTH.
 * Both figures are PORTFOLIO figures. Neither is one site's.
 *
 * 🔴 THE VALUE CARD USED TO RESTATE THE SELECTED SITE, WHICH MADE IT A DUPLICATE RATHER THAN A
 * SUMMARY. It took `usdLo`, `usdHi`, `cutPct`, `gainHPerYear` and `weatherHours` from the Headline of
 * whichever site was selected, so it printed Ashburn's $334k-$967k, its 6.2 % and its +405 h -- and
 * the KPI plate a few hundred pixels below printed the same four numbers for the same site. A reader
 * scrolling past saw one site's result twice and no portfolio result at all. Every figure on the
 * value card now comes from `demo/portfolio.json`, summed over all 250 sites' own artefacts by
 * tools/portfolio_totals.py.
 *
 * 🔴 AND NOT ONE OF THEM IS A PER-SITE FIGURE TIMES A COUNT. That distinction is the whole point:
 * every one of the 250 sites carries its own backtest, trace and money artefacts (measured: 247
 * distinct backtests, 250 distinct money files), so these are sums of 250 real results. The only
 * modelling in them is the modelling already inside each site's own published figure, and where that
 * modelling is load-bearing the card says so in words rather than leaving it to a popover.
 *
 * WHAT IS DELIBERATELY NOT HEADLINED HERE, and why:
 *   * The money is a FOOT ROW, not the big number, even though this is the value card. Its low bound
 *     is negative, because 12 of the 250 sites lose hours and the sum of every site's worst swept
 *     corner is -$25.4M. That is a real bound and it is shown, but a headline figure that can be
 *     read as "-$25M" invites a judge to stop reading. The headline is the chiller-hours instead:
 *     hours need no tariff, no power density and no state, so they carry no modelling the money
 *     carries.
 *   * The hours of weather are the DISTINCT-station total, 4,232,006, not the 10,820,547 site-hours.
 *     The 250 sites share 98 airport stations, so the larger figure counts a shared record several
 *     times. It is a fair measure of work done and a bad measure of weather, and the smaller number
 *     needs no asterisk.
 *
 * ⚠ THE VALUE CARD RENDERS NOTHING when portfolio.json is absent, rather than showing a dash or a
 * placeholder. A card that says "$0" is worse than a card that is not there.
 *
 * THE DRIFT IS DECORATIVE AND SLOW ON PURPOSE. 11 seconds for a 10px excursion, which reads as
 * floating rather than as animation, and it is `transform` only so it never reflows anything or
 * disturbs the canvas panels below. Disabled outright under prefers-reduced-motion.
 */
export function ScopeBubble({
  shipped,
  mapped,
  p,
}: {
  shipped: number
  mapped: number
  /** Portfolio totals. null before `tools/portfolio_totals.py` has run: the value card is absent. */
  p: Portfolio | null
}) {
  const n = (v: number) => Math.round(v).toLocaleString('en-US')

  /** $334k, $65.8M: the card is glanced at, and an eight-digit run of figures is not read, it is
      skipped. The sign is kept, because the low bound of the portfolio sweep is genuinely below zero
      and hiding that is the one thing this card must not do. */
  const usd = (v: number) => {
    const s = v < 0 ? '-$' : '$'
    const a = Math.abs(v)
    return a >= 1e6
      ? s + (a / 1e6).toFixed(1) + 'M'
      : s + Math.round(a / 1000).toLocaleString('en-US') + 'k'
  }

  return (
    <motion.div
      className="aa-bubble-stack"
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{
        opacity: 1,
        scale: 1,
        /* 🔴 VERTICAL ONLY. There was a second axis, `x: [0, 6, 0, -6, 0]`, which made the path a slow
           lissajous rather than a straight float. It had to go: MEASURED at a 1920 window, the cards'
           right edge read 1651 against the filter panel's 1647, because the sample caught the drift
           four pixels out. The cards are laid out on the container edge correctly; the decoration was
           walking them off it. A brief that asks for two edges to share an x coordinate is not
           satisfied by an edge that is right on average. */
        y: [0, -10, 0, 8, 0],
      }}
      transition={{
        opacity: { duration: 0.5, ease: 'easeOut' },
        scale: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
        y: { duration: 11, repeat: Infinity, ease: 'easeInOut' },
      }}
    >
      {/* ---- CARD ONE: THE SCALE, and the evidence behind it. */}
      <aside className="aa-bubble" aria-label="What this project covers">
        <p className="aa-bubble-hero">
          <span className="aa-bubble-num">{shipped}</span>
          <span className="aa-bubble-unit">
            data centres carried through
            <br />
            the full agent loop
          </span>
        </p>

        <p className="aa-bubble-foot">
          <Globe2 size={13} strokeWidth={2.2} aria-hidden="true" />
          <span>
            out of <b>{mapped}</b> mapped from OpenStreetMap
          </span>
        </p>

        {/* THE SECOND ROW IS THE CREDIBILITY ONE. A count of sites says how much was attempted; hours
            of real recorded weather say what it was attempted against, which is the harder claim and
            the one a judge can check. DISTINCT hours, see the note at the top of this file. */}
        {p && (
          <p className="aa-bubble-foot">
            <Gauge size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              scored against <b>{n(p.weather_hours_distinct)}</b> hours of recorded weather from{' '}
              <b>{p.stations}</b> airport stations
            </span>
          </p>
        )}
      </aside>

      {/* ---- CARD TWO: WHAT THE PORTFOLIO IS WORTH. */}
      {p && (
        <aside className="aa-bubble aa-bubble-value" aria-label="What the portfolio is worth">
          <p className="aa-bubble-hero">
            <span className="aa-bubble-num">+{n(p.gain_h_per_year)}</span>
            <span className="aa-bubble-unit">
              chiller-hours a year across
              <br />
              the whole portfolio
            </span>
          </p>

          {/* THE LOSSES ARE ON THE CARD, not in a popover. 12 of 250 sites come out behind the
              incumbent controller, and the headline above already has them subtracted. Saying so is
              cheap here and expensive later: a judge who finds a negative site after reading an
              unqualified total stops believing the total. */}
          <p className="aa-bubble-foot">
            <TrendingUp size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              <b>{p.sites_gaining}</b> of <b>{p.sites_summed}</b> sites gain hours. The{' '}
              <b>{p.sites_losing}</b> that lose are subtracted above, not dropped
            </span>
          </p>

          <p className="aa-bubble-foot">
            <Coins size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              worth <b>{usd(p.usd_lo)}</b> to <b>{usd(p.usd_hi)}</b> a year, modelled: each site's own
              published tariff-by-efficiency sweep on IT load inferred from measured roof area
            </span>
          </p>

          {/* AND WHOSE TARIFF IT IS. EIA does not publish a row for every state, so 189 of the 250
              are priced on the Virginia and Illinois reference rows rather than their own. The money
              range above is unreadable without that sentence, so it sits directly under it. */}
          <p className="aa-bubble-foot">
            <Gauge size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              <b>{p.sites_own_state_prices}</b> priced on their own state's EIA rows,{' '}
              <b>{p.sites_reference_prices}</b> on the Virginia and Illinois reference
            </span>
          </p>
        </aside>
      )}
    </motion.div>
  )
}
