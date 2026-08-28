import { Info } from './Info'
import { int } from '../lib/artefacts'
import { usdShort, type Headline, type Series } from '../lib/headline'

/**
 * The data cards.
 *
 * THE BRIEF IS EXPLICIT: "Do not modify the existing reports, graphs, or numerical data cards. Leave
 * all quantitative elements exactly as they are." Every figure here is the shipped figure, derived in
 * src/lib/headline.ts exactly as audit.py's front-door registry derives it, and reproduced in Python
 * against the published strings before this file existed. What changed is the PRESENTATION.
 *
 * ---------------------------------------------------------------------------------------------
 * CREDIT, AND WHAT WAS AND WAS NOT TAKEN
 * ---------------------------------------------------------------------------------------------
 * The layout and the chart treatment are adapted from "Stats Card" by kavikatiyar on 21st.dev
 * (component 7841): the quiet label row, the dominant figure, one line of context, and beneath it a
 * flex row of bottom-aligned bars with rounded tops, heights as percentages, a highlighted final bar
 * and a small label under each. That composition is the reason the retrieval was spent.
 *
 * 🔴 ITS MOTION AND ITS NUMBER FORMATTING WERE NOT TAKEN, and could not be:
 *   1. `AnimatedValue` did `latest.toFixed(0)`. On this data that renders 10.7 % as "11 %", 65.6 % as
 *      "66 %" and $334,269 as "334269". A display layer silently rounding every audited figure to an
 *      integer is a data bug wearing an animation's clothes.
 *   2. `useSpring` for the counter and `type:"spring"` for the bars. Spring physics is TIME-DEPENDENT,
 *      so two renders of one screen differ. testing/verify_site_panels.py renders one site twice and
 *      requires byte-identical output; this is exactly why the single-file page uses fixed
 *      cubic-bezier curves and not a physics engine.
 *   3. `useInView(..., {once:true})` gates what is drawn on the reader's SCROLL POSITION, which is
 *      not a property of the data.
 * So the entrance is a CSS animation with a fixed duration and one shared easing, and it stands down
 * entirely under `prefers-reduced-motion` (which the render harness forces). No framer-motion, no
 * lucide-react, no shadcn Card: zero new dependencies.
 *
 * ⚠ AND NO TREND DELTA. The original ships a "revenue decreased by $421" line. Four of these five
 * figures are LEVELS measured once; there is no previous period. A delta would be a false claim.
 *
 * 🔴 ONLY THREE OF THE FIVE CARDS GET A CHART, because only three have a real series behind them:
 * the notice-hour ladder, the 16 money cells, and the margin trajectory. A cut percentage and an hour
 * count are single measurements. Giving them a shape would be decoration posing as evidence, which is
 * the one thing this project cannot afford to do.
 *
 * 🔴 THE FAILING NUMBER IS STILL HERE, AND STILL RED. 65.6 % against a 90 % promise, on the first
 * screen, labelled as not met.
 */
export function KpiCards({ h }: { h: Headline }) {
  return (
    <section
      aria-label="What the agent delivers, measured"
      className="grid grid-cols-2 gap-3 lg:grid-cols-5"
    >
      <Card
        i={0}
        k="Mechanical cooling cut"
        v={h.cutPct.toFixed(1)}
        unit="%"
        sub={`${int(h.mechIncumbentH)} h of chiller time becomes ${int(h.mechAgentH)} h`}
        info="A SHARE, not a total, which is why it holds at any hall size. Measured on the shipped
              five-year row: the agent's mechanical runtime against the tuned reactive on-site-sensor
              controller operators verifiably run today, over the same hours."
        infoLabel="Why a share rather than a total: it holds at any hall size."
      />

      <Card
        i={1}
        k="Chiller-hours recovered"
        v={`+${Math.round(h.gainHPerYear)}`}
        unit="h/yr"
        sub="against the reactive controller operators run today"
        series={h.series.gain}
        info="The incumbent is not a straw man: it is the on-site-sensor control plants verifiably
              run, reacting to what a thermometer reports now. The bars are the sensitivity sweep's
              notice axis, so they are the forecast's value measured by varying only the forecast."
        infoLabel="What the comparison is against, and what the bars show: chiller-hours bought by each hour of notice."
      />

      <Card
        i={2}
        k="Worth at this site"
        v={`${usdShort(h.usdLo)}–${usdShort(h.usdHi)}`}
        unit="/yr"
        sub={`${int(h.moneyCells)} swept cells · ${Math.round(h.mwLo)}–${Math.round(h.mwHi)} MW of IT load`}
        series={h.series.worth}
        info={`A RANGE BECAUSE IT IS A SWEEP, not a confidence interval: 4 published electricity
              tariffs by 4 published chiller efficiencies, ${int(h.moneyCells)} cells, cheapest to
              dearest. $${int(h.usdPerMwLo)} to $${int(h.usdPerMwHi)} per MW of IT load per year,
              times this site's own measured footprint of ${int(h.footprintM2)} m². Compressor-only,
              which makes it an upper bound on that term rather than a projection.`}
        infoLabel="Why it is a range: a 16-cell sweep of published tariffs and chiller efficiencies, not a confidence interval."
      />

      <Card
        i={3}
        k="Measured on"
        v={int(h.weatherHours)}
        unit="h"
        sub="real weather, on held-out days the agent never calibrated on"
        info="Real recorded weather from the site's own airport station, not a simulation and not the
              days the bound was calibrated on. Holding days back is the only way a measured coverage
              figure means anything."
        infoLabel="Real recorded weather on held-out days, not a simulation."
      />

      <Card
        i={4}
        k="Bound coverage, measured"
        v={h.coveragePct.toFixed(1)}
        unit="%"
        tone="critical"
        sub="against its own 90 % promise · PRE-REGISTERED TEST NOT MET"
        series={h.series.cov}
        signed
        info="THIS IS THE HONEST NUMBER AND IT IS ON THE FIRST SCREEN. The bound promised 90 % and
              delivered 65.6 %. Most of the shortfall is arithmetic rather than modelling: with n
              calibration day-pairs the best attainable coverage is n/(n+1), so 4 pairs cap it at
              80 % before anything else goes wrong. Nine are needed for 90 % and four exist. The bars
              are the margin recalibrating itself across those four pairs, and they cross zero."
        infoLabel="Why coverage fell short: with 4 calibration day-pairs the attainable ceiling is 80 percent, and 9 are needed for 90."
      />
    </section>
  )
}

function Card({
  i, k, v, unit, sub, info, infoLabel, tone, series, signed,
}: {
  i: number
  k: string
  v: string | number
  unit?: string
  sub: string
  info: string
  infoLabel: string
  tone?: 'critical'
  series?: Series
  /** Draw from a zero baseline, for a series that crosses it. */
  signed?: boolean
}) {
  return (
    <div
      className="glass group relative flex flex-col rounded-2xl p-4 transition-transform
                 duration-200 ease-out hover:-translate-y-0.5"
    >
      <div className="label flex items-start leading-[1.3]">
        <span>{k}</span>
        <Info label={infoLabel}>{info}</Info>
      </div>

      <div
        className="num display mt-3 flex items-baseline gap-1"
        style={{ color: tone === 'critical' ? 'var(--critical)' : 'var(--text-primary)' }}
      >
        <span className="text-[clamp(26px,3.2vw,42px)]">{v}</span>
        {unit && (
          <span className="text-[clamp(11px,1vw,15px)] font-semibold tracking-normal text-ink-2">
            {unit}
          </span>
        )}
      </div>

      <p className="mt-2 text-[11.5px] leading-[1.45] text-ink-2">{sub}</p>

      {series && <Bars series={series} signed={signed} delay={i * 60} critical={tone === 'critical'} />}
    </div>
  )
}

/**
 * The bar chart, adapted from the 21st.dev card's treatment and driven by a real series.
 *
 * DETERMINISTIC BY CONSTRUCTION. Heights are computed from the data and written as inline styles, so
 * the final frame is a pure function of the values. The only motion is one CSS animation with a fixed
 * duration and a fixed easing, and `@media (prefers-reduced-motion: reduce)` in index.css collapses it
 * to nothing. Nothing here reads the clock, the scroll position, or a random number.
 */
function Bars({ series, signed, delay, critical }: {
  series: Series
  signed?: boolean
  delay: number
  critical?: boolean
}) {
  const vals = series.vals
  const n = vals.length
  const max = Math.max(...vals.map((x) => Math.abs(x)), 1e-9)

  // A signed series is drawn from the middle, because a margin that crosses zero has to be SEEN to
  // cross zero. An all-positive series is drawn from the bottom, where a reader expects it.
  const pct = (x: number) => (signed ? (Math.abs(x) / max) * 50 : (Math.abs(x) / max) * 100)

  const accent = critical ? 'var(--critical)' : 'var(--series-1-edge)'
  const quiet = 'var(--axis)'

  return (
    <div className="mt-3">
      <div
        className="relative flex h-[42px] w-full items-end"
        style={{ gap: n > 8 ? '2px' : '4px' }}
        role="img"
        aria-label={`${series.cap}: ${vals.map((x) => x.toFixed(2)).join(', ')}`}
      >
        {signed && (
          // The zero line, drawn so the sign of each bar is readable rather than implied.
          <div
            className="pointer-events-none absolute left-0 right-0 top-1/2 h-px"
            style={{ background: 'var(--grid)' }}
          />
        )}
        {vals.map((x, j) => {
          const last = j === n - 1
          return (
            <div key={j} className="relative flex h-full flex-1 items-end">
              <span
                className="aa-bar w-full rounded-t-[3px]"
                style={{
                  height: `${pct(x)}%`,
                  background: last ? accent : quiet,
                  opacity: last ? 1 : 0.55,
                  // A signed series sits on the midline; a negative bar hangs below it.
                  ...(signed
                    ? x >= 0
                      ? { position: 'absolute', bottom: '50%' }
                      : { position: 'absolute', top: '50%', borderRadius: '0 0 3px 3px' }
                    : {}),
                  animationDelay: `${delay + j * 45}ms`,
                }}
              />
            </div>
          )
        })}
      </div>

      {series.labels && n <= 8 && (
        <div className="mt-1 flex w-full" style={{ gap: '4px' }}>
          {series.labels.map((l, j) => (
            <span
              key={j}
              className="num flex-1 text-center text-[9.5px] text-muted"
              style={{ opacity: j === n - 1 ? 1 : 0.7 }}
            >
              {l}
            </span>
          ))}
        </div>
      )}

      <p className="mt-1.5 text-[10px] leading-[1.35] text-muted">{series.cap}</p>
    </div>
  )
}
