import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Download, Loader2 } from 'lucide-react'

/**
 * The agent, as ONE ROW. A live shimmer while it reasons, a blue Download button the moment it stops.
 *
 * Replaces the expanded sixteen-line tape as the thing a reader looks at. The tape itself stays in the
 * DOM, hidden by CSS: it is what verify_app_flow.py counts (`#tape > *`) and what #tapedone reports
 * completion through, and it remains openable under "Full reasoning trace".
 *
 * 🔴 EVERY WORD OF THE REASONING IS A FIXED PHRASE, AND NOT ONE OF THEM CONTAINS A DIGIT. That is
 * deliberate and it is the whole reason this component is safe. The stage it shows is READ from the
 * engine's own tape, so the progress is real; the wording is decoration over a real signal. A version
 * that paraphrased the tape's numbers would be inventing figures with no artefact behind them, which
 * is the one thing this project does not ship. ticker.json makes the same promise about its own
 * templates: "no template in src/ticker.py contains a literal digit".
 *
 * THE SHIMMER is adapted from 21st.dev's `thinking-tool` (serafimcloud): an animated linear-gradient
 * painted through `background-clip: text`. Its icon dependency (@tabler/icons-react) was dropped for
 * lucide, which is already here, and the greys were repointed at this project's blue ramp.
 */

/** The seven real stages, in order, from ticker.json's own `stages` map. */
const STAGE_NAMES = ['PERCEIVE', 'SOLVE', 'BOUND', 'DECIDE', 'ACT', 'SCORE', 'RECALIBRATE'] as const

/**
 * Short reasoning phrases, keyed by the stage the tape has actually reached. Two or three per stage so
 * a long stage does not sit on one line, cycled on a timer.
 *
 * Each phrase describes what that stage DOES, which is a fact about the pipeline rather than about the
 * data, so none of them can go stale against an artefact.
 */
const PHRASES: Record<number, string[]> = {
  1: ['Reading the vendor field...', 'Loading real station hours...', 'Locating the committed site...'],
  2: ['Solving the plume...', 'Turning the wind through every bearing...', 'Marching the exhaust downwind...'],
  3: ['Calibrating bounds...', 'Pondering margins...', 'Fitting residuals to held-out days...'],
  4: ['Planning the schedule...', 'Weighing the plant envelope...', 'Evaluating chiller data...'],
  5: ['Emitting the command rows...', 'Attaching a bound to every hour...'],
  6: ['Scoring itself on held-out days...', 'Checking its own coverage...'],
  7: ['Widening its own margin...', 'Recalibrating online...'],
}

type Tape = { stage: number; events: number; done: boolean }

function readTape(): Tape {
  const tape = document.getElementById('tape')
  const done = document.getElementById('tapedone')
  if (!tape) return { stage: 0, events: 0, done: false }
  let stage = 0
  let events = 0
  for (const el of Array.from(tape.children) as HTMLElement[]) {
    if (el.classList.contains('n')) {
      const n = parseInt((el.textContent || '').trim(), 10)
      if (Number.isFinite(n)) stage = Math.max(stage, n)
    } else if (el.classList.contains('t')) events += 1
  }
  return { stage, events, done: !!(done?.textContent || '').trim() }
}

export function AgentConsole({ pdfHref }: { pdfHref: string | null }) {
  const [t, setT] = useState<Tape>({ stage: 0, events: 0, done: false })
  const [phraseIdx, setPhraseIdx] = useState(0)

  /* Mirror the tape. Debounced to a frame: streamTape() reveals rows one at a time and a 32-row tape
     would otherwise re-render this 32 times for no visible difference. */
  useEffect(() => {
    const tape = document.getElementById('tape')
    const done = document.getElementById('tapedone')
    if (!tape) return
    let queued = 0
    const run = () => { queued = 0; setT(readTape()) }
    const mo = new MutationObserver(() => {
      if (queued) return
      queued = requestAnimationFrame(run)
    })
    mo.observe(tape, { childList: true, subtree: true, characterData: true })
    if (done) mo.observe(done, { childList: true, subtree: true, characterData: true })
    run()
    return () => { mo.disconnect(); if (queued) cancelAnimationFrame(queued) }
  }, [])

  const running = t.events > 0 && !t.done
  const phrases = PHRASES[Math.min(Math.max(t.stage, 1), 7)] ?? PHRASES[1]

  /* Cycle the phrase while running. Cleared when it stops, so the last line does not keep animating
     under the Download button. */
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setPhraseIdx((i) => i + 1), 2100)
    return () => clearInterval(id)
  }, [running])

  const phrase = phrases[phraseIdx % phrases.length]
  const stageLabel = useMemo(
    () => (t.stage >= 1 && t.stage <= 7 ? STAGE_NAMES[t.stage - 1] : ''),
    [t.stage],
  )

  return (
    <motion.div
      className={`aa-console ${t.done ? 'is-done' : running ? 'is-run' : 'is-idle'}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* LEFT: the state light. A spinner while working, a filled dot when finished. */}
      <span className="aa-console-orb" aria-hidden="true">
        {running ? <Loader2 className="aa-spin" size={15} strokeWidth={2.4} /> : <i />}
      </span>

      {/* MIDDLE: one line, swapped with a crossfade. aria-live so a screen reader hears the state
          change without the text being re-announced on every cosmetic swap. */}
      <div className="aa-console-line" aria-live="polite">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={t.done ? 'done' : `${t.stage}-${phraseIdx % phrases.length}`}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className={running ? 'aa-shimmer' : undefined}
          >
            {t.done
              ? 'Decision ready. Every hour carries its own bound.'
              : running
                ? phrase
                : 'Idle. Run the agent to see it reason.'}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* The seven stages as ticks, so the row still shows WHERE it is without a second panel. */}
      <ol className="aa-console-ticks" aria-label={`Stage ${t.stage} of 7`}>
        {STAGE_NAMES.map((s, i) => (
          <li
            key={s}
            className={t.done || t.stage > i + 1 ? 'is-past' : t.stage === i + 1 ? 'is-now' : ''}
            title={s}
          />
        ))}
      </ol>
      {stageLabel && !t.done && <span className="aa-console-stage">{stageLabel}</span>}

      {/* 🔴 THE FULL TRACE STAYS REACHABLE. Folding the sixteen-line tape away is a display decision;
          hiding an agent's actual reasoning behind a decoration would not be. This toggles a class on
          #tapecard that cinematic.css keys off, so the rows are one click away and the DOM is
          untouched either way, which is what keeps verify_app_flow.py's row count meaningful. */}
      {t.events > 0 && (
        <button
          type="button"
          className="aa-trace-toggle"
          onClick={() => document.getElementById('tapecard')?.classList.toggle('aa-trace-open')}
        >
          Full trace
        </button>
      )}

      {/* RIGHT: the payoff. The button appears only when the tape is finished, and it points at a REAL
          file: the per-site report.pdf listed in sites.json's artefacts map. If the manifest names no
          report for this site the button is not rendered at all, rather than offering a dead link. */}
      <AnimatePresence initial={false}>
        {t.done && pdfHref && (
          <motion.a
            key="dl"
            href={pdfHref}
            download
            className="aa-console-dl"
            initial={{ opacity: 0, scale: 0.94, x: 6 }}
            animate={{ opacity: 1, scale: 1, x: 0 }}
            exit={{ opacity: 0, scale: 0.94 }}
            transition={{ type: 'spring', stiffness: 460, damping: 30 }}
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.98 }}
          >
            <Download size={15} strokeWidth={2.4} aria-hidden="true" />
            Download PDF
          </motion.a>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
