import { Info } from './Info'

/**
 * The headline block, ending exactly where the brief says it ends.
 *
 * THE BRIEF: 1-to-2 line punchy statements only, everything deeper behind a click, and the section
 * closing on the line about the live agent. Three sentences, and each one does a distinct job: the
 * cost, what closes the gap, and why the answer can be trusted.
 *
 * 🔴 THE LAST LINE TELLS THE TRUTH ABOUT THE MODE, and that is why it is not hard-coded.
 * The brief asks the headline to end with "LIVE agent is also attached". It says that when a live
 * agent IS attached. When the page is served statically there is no /api/health to answer, and
 * printing it anyway would be a false claim on the first line a judge reads -- against the project's
 * own standing rule that nothing is asserted that cannot be re-derived. So the line states which of
 * the two is true, and says how to get the other.
 */
export function Masthead({ live }: { live: 'checking' | 'attached' | 'replay' }) {
  return (
    <header className="pt-8 pb-6">
      <p className="label mb-2">Free-cooling decisions, hour by hour</p>

      <h1 className="display text-[clamp(30px,5.2vw,54px)]">
        AGENTIC<span className="text-ink-2">·</span>ARBITER
      </h1>

      <div className="mt-4 max-w-[68ch] space-y-2.5 text-[clamp(14px,1.15vw,17px)] leading-[1.5]">
        <p>
          <b>Cooling with outside air costs a fan. Cooling with a chiller costs a compressor.</b>{' '}
          Plants burn the compressor through cheap hours anyway, because a chiller needs hours of
          notice and a thermometer only reports <i>now</i>.
          <Info label="Why running the compressors anyway is rational rather than careless: switching late risks a hall running hot, while not switching only costs electricity. One of those is recoverable and the other is not.">
            <b>Why that is rational, not careless.</b> Switching late risks a hall running hot;
            not switching only costs electricity. One of those is recoverable and the other is not,
            so with no view of the next hours, running the compressors is the correct choice.
          </Info>
        </p>

        <p>
          <b>FortyGuard closes that gap</b> by forecasting heat <b>2 m above the ground</b>, the
          height a ground-mounted condenser actually breathes.
          <Info label="Why 2 m matters: it is the height a ground-mounted condenser draws air from, so a forecast at that height is the one that predicts what the equipment will experience.">
            <b>Why the height is the point.</b> A satellite skin temperature and a 10 m weather-mast
            reading are both measuring air the equipment never touches. A condenser sitting on the
            ground breathes at roughly 2 m, so that is the forecast that predicts what it will
            actually experience.
          </Info>
        </p>

        <p>
          Every hour this agent releases carries a <b>safety margin measured from its own past
          errors</b>, and where the geometry defeats the physics it <b>refuses the hour rather than
          guess</b>.
          <Info label="What the safety margin is: a conformal prediction interval sized from the agent's own measured past errors, which is distribution-free rather than assuming a shape for the error.">
            <b>Measured, not assumed.</b> The margin is a conformal prediction interval: take the
            forecaster's errors on past cases where the answer is now known, and let their
            distribution size the bound. It assumes no shape for the error, which is why the
            guarantee is called distribution-free. Its measured coverage is on the card below,
            including where it falls short.
          </Info>
        </p>
      </div>

      <p className="mt-5 text-[13px]">
        {live === 'checking' && <span className="text-muted">Checking for a live agent…</span>}
        {live === 'attached' && (
          <span className="inline-flex items-center gap-2 font-semibold" style={{ color: 'var(--good)' }}>
            <span className="h-[7px] w-[7px] rounded-full" style={{ background: 'var(--good)' }} />
            LIVE agent is also attached
          </span>
        )}
        {live === 'replay' && (
          <span className="text-ink-2">
            Running in <b className="text-ink">REPLAY</b>, on saved responses, with{' '}
            <b className="text-ink">0</b> live API calls.
            <Info label="How to attach the live agent: serve the page with serve_live.py, which holds the API key in its own process, because anything a web page can read every visitor can read.">
              <b>The live agent can be attached.</b> Serve the page with{' '}
              <code>python AGENTIC-ARBITER/src/serve_live.py</code> and it will fetch a real
              forecast for the next hours and decide on it. It runs as a separate process because
              FortyGuard authenticates with a secret key, and anything a web page can read, every
              visitor of that page can read.
            </Info>
          </span>
        )}
      </p>
    </header>
  )
}
