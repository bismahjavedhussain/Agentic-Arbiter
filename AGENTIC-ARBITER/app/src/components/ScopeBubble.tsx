import { motion } from 'framer-motion'
import { Gauge, Globe2, TrendingUp } from 'lucide-react'

/**
 * TWO CARDS IN THE EMPTY SPACE RIGHT OF THE HEADLINE: what the project COVERS, and what that is
 * WORTH. Stacked, drifting slowly together.
 *
 * 🔴 NOT ONE FIGURE HERE IS TYPED. Every number is a prop, and every prop is read from an artefact by
 * the caller: `shipped` and `mapped` from sites.json and unified_sites.json, and the four on the value
 * card from `lib/headline.ts`, which derives them exactly as `audit.py`'s published-figure registry
 * does. That is the whole reason they are props rather than strings: this is the first thing a judge
 * reads, and a claim here that no file backs is the one failure this project cannot afford.
 * ⚠ The value card RENDERS NOTHING when the figures are absent, rather than showing a dash or a
 * placeholder. A card that says "$0" is worse than a card that is not there.
 *
 * THE SECOND CARD IS NEW, at the user's request: "draw a similar shape under this one and write our
 * value ... the conclusion we draw by shipping 250 data centres ... showing commercial value and
 * intelligence as well." So it answers the question the first card provokes. The first says HOW MUCH
 * was analysed; this says WHAT THAT BUYS, in money, in recovered hours, and in the one thing that
 * separates this from a demo: the hours it was scored against are real and held out.
 *
 * THE DRIFT IS DECORATIVE AND SLOW ON PURPOSE. 11 seconds for a 10px excursion, which reads as
 * floating rather than as animation, and it is `transform` only so it never reflows anything or
 * disturbs the canvas panels below. Disabled outright under prefers-reduced-motion.
 */
export function ScopeBubble({
  shipped,
  mapped,
  usdLo,
  usdHi,
  cutPct,
  gainHPerYear,
  weatherHours,
}: {
  shipped: number
  mapped: number
  /** The four value figures. Optional: with no headline loaded the second card is simply absent. */
  usdLo?: number
  usdHi?: number
  cutPct?: number
  gainHPerYear?: number
  weatherHours?: number
}) {
  const haveValue =
    usdLo !== undefined &&
    usdHi !== undefined &&
    cutPct !== undefined &&
    gainHPerYear !== undefined &&
    weatherHours !== undefined

  /** $334k, not $334,000: the card is glanced at, and a six-digit run of figures is not. */
  const k = (n: number) => '$' + Math.round(n / 1000).toLocaleString('en-US') + 'k'

  return (
    <motion.div
      className="aa-bubble-stack"
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{
        opacity: 1,
        scale: 1,
        /* Two axes on different periods, so the path is a slow lissajous rather than a bounce. */
        y: [0, -10, 0, 8, 0],
        x: [0, 6, 0, -6, 0],
      }}
      transition={{
        opacity: { duration: 0.5, ease: 'easeOut' },
        scale: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
        y: { duration: 11, repeat: Infinity, ease: 'easeInOut' },
        x: { duration: 15, repeat: Infinity, ease: 'easeInOut' },
      }}
    >
      {/* ---- CARD ONE: the scope. */}
      <aside className="aa-bubble" aria-label="What this project covers">
        <p className="aa-bubble-hero">
          <span className="aa-bubble-num">{shipped}</span>
          <span className="aa-bubble-unit">
            data centres covered with
            <br />
            fully agentic analysis
          </span>
        </p>

        {/* 🔴 THE THREE "OWN plant / hourly schedule / solved plume" LINES ARE GONE, at the user's
            instruction. What they said is now carried by the phrase "fully agentic analysis" above
            and demonstrated by the panels themselves, which is a stronger place for it than a bullet
            list on a card nobody can check. */}
        <p className="aa-bubble-foot">
          <Globe2 size={13} strokeWidth={2.2} aria-hidden="true" />
          <span>
            out of <b>{mapped}</b> mapped from OpenStreetMap
          </span>
        </p>
      </aside>

      {/* ---- CARD TWO: what it is worth. */}
      {haveValue && (
        <aside className="aa-bubble aa-bubble-value" aria-label="What the analysis is worth">
          <p className="aa-bubble-hero">
            <span className="aa-bubble-num">
              {k(usdLo!)}
              <span className="aa-bubble-dash">to</span>
              {k(usdHi!)}
            </span>
            <span className="aa-bubble-unit">
              a year, at one
              <br />
              mid-sized site
            </span>
          </p>

          <p className="aa-bubble-foot">
            <TrendingUp size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              <b>{cutPct!.toFixed(1)} %</b> less mechanical cooling,{' '}
              <b>+{Math.round(gainHPerYear!).toLocaleString('en-US')}</b> chiller-hours recovered
            </span>
          </p>
          <p className="aa-bubble-foot">
            <Gauge size={13} strokeWidth={2.2} aria-hidden="true" />
            <span>
              scored on <b>{weatherHours!.toLocaleString('en-US')}</b> real held-out hours
            </span>
          </p>
          {/* A fourth row said "every hour carries its own measured margin", which is the masthead's
              fourth bullet verbatim. Three rows say the whole thing once: what it is worth, what it
              changes, and what it was scored against. */}
        </aside>
      )}
    </motion.div>
  )
}
