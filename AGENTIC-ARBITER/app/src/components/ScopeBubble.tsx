import { motion } from 'framer-motion'
import { Gauge, Globe2, TrendingUp } from 'lucide-react'
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
 * value card now comes from `demo/portfolio.json`, summed by tools/portfolio_totals.py over the
 * sites the agent is OFFERED on: 238 of the 250 it was built on, since 2026-08-31. The other 12 were
 * built and measured across the same five years and are excluded from the sum because their own
 * result is negative, and `sites_withheld` carries that count so the card can say so.
 *
 * 🔴 AND NOT ONE OF THEM IS A PER-SITE FIGURE TIMES A COUNT. That distinction is the whole point:
 * every one of the 250 built sites carries its own backtest, trace and money artefacts, so these
 * are sums of real results and the 238 summed here are a subset chosen by measurement, not a sample. The only
 * modelling in them is the modelling already inside each site's own published figure, and where that
 * modelling is load-bearing the card says so in words rather than leaving it to a popover.
 *
 * WHAT IS DELIBERATELY NOT HEADLINED HERE, and why:
 *   * The money is a FOOT ROW, not the big number, even though this is the value card. Hours need no
 *     tariff, no power density and no state, so they carry none of the modelling the money carries,
 *     and they are the figure this project can defend without qualification.
 *   * 🔴 AND THE MONEY PAIR CHANGED ON 2026-08-30, FROM THE EXTREMES TO THE MEDIAN. It used to be
 *     `usd_lo`/`usd_hi`, the sum of every site's cheapest and dearest swept corner. Summing every
 *     worst corner describes a world in which they all land on their worst at once, and summing every
 *     best corner describes its mirror; neither is a scenario, and the pair spanning zero was an
 *     artefact of adding up extremes rather than a finding.
 *     ⚠ IT NO LONGER SPANS ZERO ANYWAY, and not because the arithmetic changed: excluding the 12
 *     sites the agent loses on moved `usd_lo` from -$25.4M to +$34.4M. The median pair is still the
 *     one on the card, because its honesty argument never depended on the sign.
 *     The user asked for the leading minus to go. It cannot go by deletion: "$25.4M to $65.8M" would
 *     assert a floor of plus twenty-five million that the same computation contradicts, which is a
 *     worse fault than the one being fixed. It goes by using a pair that is genuinely positive at
 *     both ends: `usd_mid_lo`/`usd_mid_hi`, the MEDIAN cell of each site's own sweep at the two
 *     published IT-load densities. Smaller than the extremes, reproducible from the same cells, and
 *     true at both ends. Currently +$42.4M to +$84.8M over the 238 offered sites; it was +$3.1M to
 *     +$6.1M when the sum still included the 12 that lose. The extremes stay in portfolio.json.
 *   * The hours of weather are the DISTINCT-station total, not the site-hours sum. The summed sites
 *     share 97 airport stations, so the larger figure counts a shared record several
 *     times. It is a fair measure of work done and a bad measure of weather, and the smaller number
 *     needs no asterisk.
 *
 * ⚠ WHAT THE 12 NON-GAINING SITES ACTUALLY DO, because the obvious description of them is wrong.
 * They are NOT sites where the gates predict zero free-cooling hours. MEASURED across all twelve:
 * the agent certifies between 4,364 and 7,529 free-cooling hours at each of them over the test
 * period, and not one of them certifies zero. What is true is that at those twelve the INCUMBENT
 * controller certifies more, because the agent's bound refuses hours the incumbent takes on a
 * thermometer reading alone. So the card says the agent is the more conservative of the two there,
 * which is the fact, in the neutral register the user asked for.
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

      {/* ---- CARD TWO: WHAT THE PORTFOLIO IS WORTH.
          🔴 PRICE, THEN HOURS, THEN SITES, at the user's instruction: "arrange the following three
          phrases in this specific top-to-bottom order (Price, Free-cooling hours, Sites), applying
          bold formatting only to the numerical figures." So the headline figure sits in the MIDDLE
          rather than at the top, which is unusual for a card and is what was asked for: the price
          line introduces it and the sites line qualifies it. */}
      {p && (
        <aside className="aa-bubble aa-bubble-value" aria-label="What the portfolio is worth">
          {/* ---- PRICE, top, AT THE SAME WEIGHT AND SIZE AS THE HOURS.
              The user: "write the money price in million in big size font (just like the size of the
              number of free cooling hours font)." So it is a second `.aa-bubble-hero` rather than a
              caption, and the two figures share one type scale by construction: neither block sets a
              size of its own, so a change to `.aa-bubble-num` moves both. */}
          <p className="aa-bubble-hero">
            <span className="aa-bubble-num">
              {usd(p.usd_mid_lo)}
              <span className="aa-bubble-dash">to</span>
              {usd(p.usd_mid_hi)}
            </span>
            <span className="aa-bubble-unit">
              a year, modelled: each site's median
              <br />
              published tariff sweep on inferred IT load
            </span>
          </p>

          {/* ---- FREE-COOLING HOURS, middle. */}
          <p className="aa-bubble-hero">
            <span className="aa-bubble-num">+{n(p.gain_h_per_year)}</span>
            <span className="aa-bubble-unit">
              free-cooling hours a year
              <br />
              gained across the portfolio
            </span>
          </p>

          {/* ---- SITES, bottom, and now a phrase rather than a paragraph.
              ⚠ THE SPLIT AND THE NETTING BOTH SURVIVE THE CUT, and that was the constraint. It read
              "At the other 12 the agent's gates are the more conservative of the two controllers, and
              every one of them stays in the total above", which is three clauses where the card has
              room for one. Why those twelve behave that way is in this file's own header and in
              portfolio.json, which is where a reader who asks the next question goes. What is NOT
              here is any word implying they failed, which the user ruled out.
              ⚠ SUPERSEDED 2026-08-31: the 12 are no longer inside the figure above. They are
              excluded from the sum and from what the interface offers, so the sentence below states
              the exclusion rather than the netting. Kept because the constraint it records, name the
              twelve without implying failure, still binds. */}
          {/* 🔴 "238 OF 238" IS A TAUTOLOGY, AND IT ARRIVED BY ACCIDENT. This read "{gaining} of
              {summed} sites gain free-cooling hours, and all {summed} are in the total above",
              which was informative while the sum covered every built site and 12 of them lost.
              `metros.py` now withholds a site whose own five-year result is negative, so both
              numbers are 238 and the sentence says nothing while appearing to reassure.
              `sites_withheld` is the count that still carries the fact.

              ⚠ AND STILL NO WORD IMPLYING THOSE SITES FAILED, which the user ruled out and which
              would be wrong anyway: the measurement is of the AGENT at that geometry, not of the
              facility. "the agent's own constraints make it worse than the incumbent there" is the
              same phrasing the report's scale page uses, so the two cannot drift. */}
          <p className="aa-bubble-foot">
            <TrendingUp size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              all <b>{p.sites_summed}</b> sites gain free-cooling hours and are in the total above
              {p.sites_withheld
                ? <>
                    {'; '}<b>{p.sites_withheld}</b> more were measured and excluded, because the
                    agent&apos;s own constraints make it worse than the incumbent there
                  </>
                : null}
            </span>
          </p>
        </aside>
      )}
    </motion.div>
  )
}
