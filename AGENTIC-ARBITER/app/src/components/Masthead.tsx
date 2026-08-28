import { Info } from './Info'

/**
 * The headline block, ending exactly where the brief says it ends.
 *
 * 🔴 REWRITTEN 2026-08-28. The user's words: "It has this huge headline which needs to be made
 * shorter by talking direct, straight forward stuff and shows the pain of the problem, Forty Guard
 * closing the gap, the impact of the solution and the accuracy we assure."
 *
 * So four statements, one line each, in exactly that order: PAIN, GAP, IMPACT, ACCURACY. The three
 * long paragraphs that were here said the same things in about 90 words and buried the impact
 * entirely. Every clause that was cut is still reachable through the info button beside it, which is
 * what the brief asks for: "Hide all detailed explanations and deep dives behind click-triggered
 * pop-ups or modals."
 *
 * 🔴 THE IMPACT LINE READS ITS NUMBERS FROM THE ARTEFACTS. It would have been easy to type "10.7 %"
 * into this file, and it would have been an unverified claim the moment the pipeline moved. The
 * figures come in as props from the same derivation audit.py's registry uses.
 *
 * 🔴 AND THE LIVE LINE IS PLAIN TEXT NOW, NOT A POPOVER. The user: "you are supposed to write: 'LIVE
 * agent is also attached'. This is not written in a pop up but rather just below it. Remove the pop up
 * that currently exists with this line."
 */
export function Masthead({
  live,
  cutPct,
  gainHPerYear,
}: {
  live: 'checking' | 'attached' | 'replay'
  cutPct?: number
  gainHPerYear?: number
}) {
  const haveImpact = Number.isFinite(cutPct) && Number.isFinite(gainHPerYear)

  return (
    <header className="pt-8 pb-5">
      <p className="label mb-2">Free-cooling decisions, hour by hour</p>

      <h1 className="display text-[clamp(30px,5.2vw,54px)]">
        AGENTIC<span className="text-ink-2">·</span>ARBITER
      </h1>

      {/* 🔴 aa-mast-prose: THE FOUR OPENING PARAGRAPHS BELONG TO THE FIRST SCREEN ONLY.
          The user's instruction was explicit: these blocks stay on "pick a site", the first page a
          reader ever sees, and are gone from the third tab where the decision is read. By then they
          are preamble competing with the answer.

          IT IS DONE IN CSS, KEYED ON body[data-stage], AND THAT IS THE POINT. setStage() already
          writes that attribute (engine.mjs:105) and is the single owner of what belongs to which
          stage. Gating this in React would need React to know the stage, and App.tsx refuses to keep
          a copy for a documented reason: a second owner of one fact, where the last writer wins and
          which one that is depends on render timing. A CSS rule reads the fact the owner published
          and introduces no owner at all. The rule is in index.css. */}
      <div className="aa-mast-prose mt-4 max-w-[64ch] space-y-2 text-[clamp(14.5px,1.2vw,17px)] leading-[1.45]">
        {/* 🔴 ONE POPOVER FOR THE WHOLE HEADLINE, at the user's instruction. There were FOUR, one
            hanging off every sentence, which made an "i" the most repeated element on the first screen
            and put four essays behind it. The four lines below now read straight through, and the
            single note at the end answers the one question a reader actually has: why does any of
            this need a forecast. Short on purpose. The long-form reasoning has not been deleted, it
            lives in the panels the agent writes. */}
        <p>
          <b>Data centres run chiller compressors through hours when outside air would have done.</b>
        </p>

        <p>
          <b>FortyGuard forecasts heat at 2 m,</b> the height a ground-mounted condenser breathes,
          which turns "right now" into hours of notice.
        </p>

        <p>
          {haveImpact ? (
            <>
              <b>This agent turns that notice into a switching schedule:</b>{' '}
              <b className="num">{cutPct!.toFixed(1)} %</b> less mechanical cooling and{' '}
              <b className="num">+{Math.round(gainHPerYear!)}</b> chiller-hours a year.
            </>
          ) : (
            <>
              <b>This agent turns that notice into a switching schedule,</b> under a switch budget and
              a minimum dwell time.
            </>
          )}
        </p>

        <p>
          <b>Every hour carries a safety margin measured from its own past errors,</b> and it refuses
          the hours it cannot stand behind.
          <Info label="Why a forecast is needed at all, and what the margin is.">
            <b>A chiller needs hours of notice.</b> A thermometer only reports the present, so with no
            view of the coming hours the safe call is to keep the compressor running. A 2 m forecast
            turns that into a schedule.
            <br />
            <b>The margin is measured, not assumed.</b> It is a conformal interval sized from the
            agent's own past errors, and its real coverage is on the card below, including where it
            falls short.
          </Info>
        </p>
      </div>

      {/* THE MODE, AND THE LIVE LINE DIRECTLY UNDER IT. Plain text, no popover. */}
      <div className="mt-4 space-y-1 text-[13px]">
        {live === 'checking' && <p className="text-muted">Checking for a live agent…</p>}

        {/* aa-mast-prose, so this goes with the four paragraphs above: the user listed it among the
            blocks the third tab must not carry. The mode still reaches a reader on the first screen,
            and the results stage says the same thing where it is load-bearing, inside #livecard.
            ⚠ THE CLASS STOPS HERE. The "LIVE agent is also attached" line directly below is NOT in
            it and must never be: standing rule C1 keeps the live surface present on every stage. */}
        {live !== 'checking' && (
          <p className="aa-mast-prose text-ink-2">
            Running in <b className="text-ink">REPLAY</b>, on saved responses, with{' '}
            <b className="text-ink">0</b> live API calls.
          </p>
        )}

        {live === 'attached' && (
          <p
            className="inline-flex items-center gap-2 font-semibold"
            style={{ color: 'var(--good)' }}
          >
            <span
              className="h-[7px] w-[7px] rounded-full"
              style={{ background: 'var(--good)' }}
              aria-hidden="true"
            />
            LIVE agent is also attached
          </p>
        )}

        {/* 🔴 NOT PRINTED WHEN IT IS FALSE. The brief asks the headline to end on "LIVE agent is also
            attached", and it does, whenever that is true. On a static host there is no /api/health to
            answer, and printing it anyway would be a false claim on the first line a judge reads, in
            a project whose whole argument is that nothing is asserted that cannot be re-derived. So
            when no agent answers, the line says so and says how to attach one. Same place, same
            weight, no popover. */}
        {live === 'replay' && (
          <p className="text-muted">
            LIVE agent is not attached. Serve the folder with{' '}
            <code>python AGENTIC-ARBITER/src/serve_live.py</code> to attach one.
          </p>
        )}
      </div>
    </header>
  )
}
