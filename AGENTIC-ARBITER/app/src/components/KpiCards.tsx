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
 * 🔴 THE FAILING NUMBER IS STILL HERE, AND STILL RED. The coverage against a 90 % promise, on the
 * first screen, labelled as not met. That is the whole reason this project is trustworthy.
 */
export function KpiCards({ h }: { h: Headline }) {
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
        info="A SHARE, not a total, which is why it holds at any hall size. Measured on the shipped
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
        info={`A RANGE BECAUSE IT IS A SWEEP, not a confidence interval: 4 published electricity
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

      <Card
        k="Bound coverage, measured"
        v={h.coveragePct.toFixed(1)}
        unit="%"
        tone="critical"
        sub="against its own 90 % promise · PRE-REGISTERED TEST NOT MET"
        info="THIS IS THE HONEST NUMBER AND IT IS ON THE FIRST SCREEN. The bound promised 90 % and did
              not reach it. Most of the shortfall is arithmetic rather than modelling: with n
              calibration day pairs the best coverage anyone can attain is n/(n+1), so a small number
              of pairs caps it well below 90 % before anything else goes wrong. The margin
              recalibrating itself across those pairs is drawn in the results stage."
        infoLabel="Why coverage fell short: with n calibration day pairs the ceiling is n/(n+1)."
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
  tone?: 'critical'
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
    </div>
  )
}
