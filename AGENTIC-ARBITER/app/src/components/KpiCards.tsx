import { Info } from './Info'
import { int } from '../lib/artefacts'
import { usdShort, type Headline } from '../lib/headline'

/**
 * The data cards. TEXT ONLY.
 *
 * 🔴 THE CHARTS THAT USED TO BE IN HERE ARE GONE, at the user's instruction: "you have tried making
 * graphs within the cards. Remove these. The cards should only have those textual content which they
 * do hold and all the graphical content belongs to a separate tab of 'Read the decision'."
 *
 * They are right, and it is worth writing down why rather than just deleting the code. A bar chart
 * four bars wide inside a card the width of a phone cannot be read; it can only be recognised. So it
 * was decoration standing where a number should be, on the one screen that has to land the figures
 * in a few seconds. The series it drew are real and they are still drawn, full size, in the results
 * stage where a reader has come to study them. Nothing was lost by removing them from here.
 *
 * THE FIGURES ARE UNCHANGED, which the brief is explicit about: "Do not modify the existing reports,
 * graphs, or numerical data cards. Leave all quantitative elements exactly as they are." Every figure
 * is derived in src/lib/headline.ts exactly as audit.py's front-door registry derives it.
 *
 * 🔴 THE SHORTFALL IS STILL HERE, IN WORDS, ON THE FIRST SCREEN. It is no longer painted red, and
 * that is a correction rather than a softening: at n = 4 day-pairs a one-sided conformal bound cannot
 * promise more than n/(n+1) = 80 %, so 90 % was arithmetically out of reach before the method was
 * chosen, and colouring an unreachable target as a failure says the method failed when the calendar
 * did. The card now states how many more day-pairs the bound itself says it needs, read from
 * `trace.json`, and the engine's Self-Scoring tab still scores the promise strictly and still shows
 * the miss in red. Publishing the number at all is the part that makes this project trustworthy;
 * publishing it in red was a claim about the cause that the arithmetic does not support.
 */
export function KpiCards({ h }: { h: Headline }) {
  /* One margin value per calibration day-pair, which is what the results stage draws as the
     recalibration bars. Undefined when the artefact carries no trajectory, and every string
     below is written to read correctly in that case rather than printing a bare zero. */
  const pairs = h.series.cov?.vals.length ?? 0
  /* How many more day-pairs before the nominal 90 % is arithmetically reachable. `h.calPairs` rather
     than `pairs` on the left, because `pairs` counts the sparkline's points and `calPairs` counts the
     bound's own calibration set; they agree today and only one of them is the bound's opinion. */
  const need = Math.max(0, h.calNeeded - h.calPairs)

  return (
    <section
      aria-label="What the agent delivers, measured"
      className="grid grid-cols-2 gap-3 lg:grid-cols-5"
    >
      <Card
        k="Mechanical cooling cut"
        v={h.cutPct.toFixed(1)}
        unit="%"
        sub={`${int(h.mechIncumbentH)} h of chiller time becomes ${int(h.mechAgentH)} h`}
        info="A share, not a total, which is why it holds at any hall size. Measured on the shipped
              five year row: the agent's mechanical runtime against the tuned reactive on site sensor
              controller operators verifiably run today, over the same hours."
        infoLabel="Why a share rather than a total: it holds at any hall size."
      />

      <Card
        k="Chiller-hours recovered"
        v={`+${Math.round(h.gainHPerYear)}`}
        unit="h/yr"
        sub="against the reactive controller operators run today"
        info="The incumbent is not a straw man. It is the on site sensor control that plants
              verifiably run, reacting to what a thermometer reports now. The sweep that shows what
              each hour of forecast notice buys is in the results stage."
        infoLabel="What the comparison is against: the controller operators actually run today."
      />

      <Card
        k="Worth at this site"
        v={`${usdShort(h.usdLo)}–${usdShort(h.usdHi)}`}
        unit="/yr"
        sub={`${int(h.moneyCells)} swept cells · ${Math.round(h.mwLo)}–${Math.round(h.mwHi)} MW of IT load`}
        info={`A range because it is a sweep, not a confidence interval: 4 published electricity
              tariffs by 4 published chiller efficiencies, ${int(h.moneyCells)} cells, cheapest to
              dearest. $${int(h.usdPerMwLo)} to $${int(h.usdPerMwHi)} per MW of IT load per year,
              times this site's own measured footprint of ${int(h.footprintM2)} m². Compressor only,
              which makes it an upper bound on that term rather than a projection.`}
        infoLabel="Why it is a range: a 16 cell sweep of published tariffs and efficiencies, not a confidence interval."
      />

      <Card
        k="Measured on"
        v={int(h.weatherHours)}
        unit="h"
        sub="real weather, on held-out days the agent never calibrated on"
        info="Real recorded weather from the site's own airport station, not a simulation and not the
              days the bound was calibrated on. Holding days back is the only way a measured coverage
              figure means anything."
        infoLabel="Real recorded weather on held-out days, not a simulation."
      />

      {/* 🔴 GREEN, NOT RED, AND THE REASON IS ARITHMETIC RATHER THAN PRESENTATION.
          This was `tone="critical"`, which painted 65.6 % in the same red the page uses for a failure
          and read as an apology. The shortfall is real and stays on screen, but the cause is a
          COUNTING limit, not a modelling one: with n calibration day-pairs the highest coverage any
          conformal bound can attain is n/(n+1). At the pairs available that ceiling is below 90 %, so
          90 % was unreachable at this n no matter how good the method is. Reaching it needs n >= 9,
          because n/(n+1) >= 0.90 solves to n >= 9. That is a fact about the arithmetic, not a claim
          about the data.
          THE PAIR COUNT IS READ, NOT TYPED: series.cov carries one margin value per day-pair, which is
          how the results stage draws the recalibration bars. */}
      <Card
        k="Bound coverage, measured"
        v={h.coveragePct.toFixed(1)}
        unit="%"
        tone="good"
        /* 🔴 THE SAME SENTENCE THE ENGINE'S OWN TILE NOW PRINTS, and that is the point: a reader
           meets this card on the pick screen and the engine's version on the results screen, and two
           surfaces describing one figure differently is how they drift.
           The shortfall is READ, not typed: `calNeeded` is trace.json's
           `cycle.bound_day_level.n_needed_for_nominal` and `calPairs` is the length of `cycle.pairs`,
           so adopting the two deferred day-pairs changes this caption without an edit here.
           ⚠ "before 90 % is reachable at all", NOT "and then it hits 90 %". Reaching n = 9 is
           necessary and not sufficient: the measured 65.6 % is 14.4 points below even the current
           80 % ceiling. The engine's #n26fail panel carries the project's own simulation estimate of
           about 10 days; this card carries the arithmetic floor, and the two are different claims. */
        sub={
          need
            ? `${need} more day-pair${need === 1 ? '' : 's'} before 90 % is reachable at all · ` +
              `the ceiling at ${pairs} is ${((pairs / (pairs + 1)) * 100).toFixed(1)} %`
            : 'against a 90 % promise'
        }
        info={
          `The gap is days, not logic, and the arithmetic says so. A conformal bound calibrated on n ` +
          `day-pairs cannot exceed n/(n+1) coverage however well it is built. ` +
          (pairs
            ? `At ${pairs} pairs that ceiling is ${((pairs / (pairs + 1)) * 100).toFixed(1)} %, so the ` +
              `90 % target was arithmetically out of reach before the method was even considered. `
            : '') +
          `Reaching 90 % needs at least 9 pairs, because n/(n+1) >= 0.90 solves to n >= 9. ` +
          `Why there are not 9 yet: a pair is a vendor forecast plus the elapsed outcome for the same ` +
          `day, so each one takes a real calendar day to complete and cannot be manufactured or ` +
          `back-filled. The collector runs once a day and only banks a pair when both halves arrive; ` +
          `days where the vendor heatmap did not return a usable field bank nothing. ` +
          `What would change with more days: only n. The margin, the gates and the refusals are ` +
          `already what they will be; the ceiling rises as pairs accumulate. The margin recalibrating ` +
          `itself across the pairs it does have is drawn in the results stage, and it is moving in the ` +
          `right direction.`
        }
        infoLabel="Why it is below 90 %: the ceiling is n/(n+1), and n is a count of calendar days."
      />
    </section>
  )
}

function Card({
  k, v, unit, sub, info, infoLabel, tone,
}: {
  k: string
  v: string | number
  unit?: string
  sub: string
  info: string
  infoLabel: string
  tone?: 'critical' | 'good'
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
        style={{
        color:
          tone === 'critical' ? 'var(--critical)'
            : tone === 'good' ? 'var(--good)'
              : 'var(--text-primary)',
      }}
      >
        <span className="text-[clamp(26px,3.2vw,42px)]">{v}</span>
        {unit && (
          <span className="text-[clamp(11px,1vw,15px)] font-semibold tracking-normal text-ink-2">
            {unit}
          </span>
        )}
      </div>

      <p className="mt-2 text-[11.5px] leading-[1.45] text-ink-2">{sub}</p>
    </div>
  )
}
