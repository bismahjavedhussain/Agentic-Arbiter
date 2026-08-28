import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

/**
 * The console chrome around the agent's own tape: a seven-stage rail, a status line and a caret.
 *
 * 🔴 IT WRAPS THE TAPE, IT DOES NOT REPLACE IT, and that is the whole design. The obvious build was
 * a React terminal that reads ticker.json and streams the events itself. That would put a SECOND
 * implementation of the tape beside the engine's, and the two would drift: the engine's streamTape()
 * turns ' -- ' into ': ' in the view only, picks the tightest hour by computing it rather than
 * defaulting to index 0, and refuses to render rather than show a number it cannot justify. A React
 * copy would reproduce none of that on day one and none of its later fixes ever.
 *
 * So the rows on screen stay the engine's `#tape`, restyled as console lines by index.css. This
 * component contributes only what the engine does not have: the stage rail, the status, the caret and
 * the motion. It READS `#tape` to know how far the run has got. It writes nothing into it.
 *
 * HOW IT READS. tapeHTML() (engine.mjs:1174) emits a flat run of three divs per event:
 *     <div class="n">stage number, only on the first event of a stage</div>
 *     <div class="s">stage name,   only on the first event of a stage</div>
 *     <div class="t">the text</div>
 * so the children come in triples and a new stage is the one whose `.n` is non-empty. `#tapedone` is
 * filled when streaming ends, which is the completion signal the flow check also waits on: trap 5b.4
 * records that waiting for the first row instead failed a working 32-row tape.
 */

/** The agent's seven stages, in order, from ticker.json's own `stages` map. */
const STAGES = ['PERCEIVE', 'SOLVE', 'BOUND', 'DECIDE', 'ACT', 'SCORE', 'RECALIBRATE'] as const

type Progress = { reached: number; events: number; done: boolean; lastText: string }

function readTape(): Progress {
  const tape = document.getElementById('tape')
  const done = document.getElementById('tapedone')
  if (!tape) return { reached: 0, events: 0, done: false, lastText: '' }

  let reached = 0
  let events = 0
  let lastText = ''
  const kids = Array.from(tape.children) as HTMLElement[]
  for (const el of kids) {
    if (el.classList.contains('n')) {
      const n = parseInt((el.textContent || '').trim(), 10)
      if (Number.isFinite(n)) reached = Math.max(reached, n)
    } else if (el.classList.contains('t')) {
      events += 1
      const t = (el.textContent || '').trim()
      if (t) lastText = t
    }
  }
  /* `#tapedone` filled is the honest end-of-run signal. Its text is the engine's own footer. */
  const doneTxt = (done?.textContent || '').trim()
  return { reached, events, done: !!doneTxt, lastText }
}

export function AgentTerminal() {
  const [p, setP] = useState<Progress>({ reached: 0, events: 0, done: false, lastText: '' })

  useEffect(() => {
    const tape = document.getElementById('tape')
    const done = document.getElementById('tapedone')
    if (!tape) return

    let queued = 0
    const run = () => {
      queued = 0
      setP(readTape())
    }
    /* Debounced to the next frame: streamTape() reveals rows one at a time and a 32-row tape would
       otherwise re-render this 32 times for no visible difference. */
    const mo = new MutationObserver(() => {
      if (queued) return
      queued = requestAnimationFrame(run)
    })
    mo.observe(tape, { childList: true, subtree: true, characterData: true })
    if (done) mo.observe(done, { childList: true, subtree: true, characterData: true })
    run()
    return () => {
      mo.disconnect()
      if (queued) cancelAnimationFrame(queued)
    }
  }, [])

  const running = p.events > 0 && !p.done

  return (
    <motion.div
      className="aa-term"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* THE TITLE BAR. The three dots are a window affordance and nothing more; they are
          decorative and marked aria-hidden so a screen reader is not told about fake buttons. */}
      <div className="aa-term-bar">
        <span className="aa-term-dots" aria-hidden="true">
          <i /><i /><i />
        </span>
        <span className="aa-term-title">agentic-arbiter run</span>
        <span className={`aa-term-state ${p.done ? 'is-done' : running ? 'is-run' : 'is-idle'}`}>
          {p.done ? 'complete' : running ? 'working' : 'idle'}
        </span>
      </div>

      {/* THE STAGE RAIL. Each stage lights when the tape has reached it, so this is a readout of the
          real run rather than a timed animation pretending to be one. */}
      <ol className="aa-rail" aria-label="The agent's seven stages">
        {STAGES.map((s, i) => {
          const n = i + 1
          const state = p.reached > n || p.done ? 'past' : p.reached === n ? 'now' : 'todo'
          return (
            <li key={s} className={`aa-rail-step is-${state}`}>
              <motion.span
                className="aa-rail-dot"
                initial={false}
                animate={
                  state === 'now'
                    ? { scale: [1, 1.35, 1], opacity: 1 }
                    : { scale: 1, opacity: state === 'past' ? 1 : 0.38 }
                }
                transition={
                  state === 'now'
                    ? { duration: 1.4, repeat: Infinity, ease: 'easeInOut' }
                    : { duration: 0.25 }
                }
              />
              <span className="aa-rail-n">{n}</span>
              <span className="aa-rail-label">{s}</span>
            </li>
          )
        })}
      </ol>

      {/* THE STATUS LINE, which is the engine's own last line echoed, not a message of our own. */}
      <div className="aa-term-status">
        <span className="aa-term-prompt" aria-hidden="true">
          &gt;
        </span>
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={p.lastText.slice(0, 60) || 'idle'}
            className="aa-term-line"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            {p.lastText || 'waiting for the agent to start'}
          </motion.span>
        </AnimatePresence>
        {running && (
          <motion.span
            className="aa-term-caret"
            aria-hidden="true"
            animate={{ opacity: [1, 1, 0, 0] }}
            transition={{ duration: 1, repeat: Infinity, times: [0, 0.45, 0.5, 1] }}
          />
        )}
      </div>

      {/* 🔴 NO ROW COUNT IS INVENTED HERE. `events` is counted off the tape the engine wrote, so if
          the tape is short this says so rather than claiming a full run. */}
      <p className="aa-term-foot">
        {p.events > 0
          ? `${p.events} stage event${p.events === 1 ? '' : 's'} streamed, stage ${Math.min(
              Math.max(p.reached, 1),
              STAGES.length,
            )} of ${STAGES.length}`
          : 'The tape below fills as the agent works. Run it from the panel underneath.'}
      </p>
    </motion.div>
  )
}
