import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ART } from '../lib/artefacts'
import { Download, FileText } from 'lucide-react'

/**
 * The agent as ONE LINE: an orbiting icon, a short reasoning phrase that changes every second or so,
 * and then, on the line below, the Download PDF button.
 *
 * THE SEQUENCE, which is what the previous version got wrong. It showed "Decision ready" and the
 * button immediately, because the replay tape had already finished before anyone looked, so a reader
 * never saw the agent reason at all. Now the reasoning always plays first:
 *
 *     reasoning   orbiting icon + rotating phrases, held open for at least MIN_MS
 *     ready       one line: "Decision ready", and the Download PDF button on the row beneath
 *
 * Clicking any of the engine's run buttons restarts it, so pressing "Run the agent on live data"
 * replays the reasoning against that run rather than sitting on a stale conclusion.
 *
 * 🔴 THE PHRASES ARE FIXED AND NONE CONTAINS A DIGIT, and the stage shown beside them is READ from
 * the engine's own tape, so what advances is real. Paraphrasing the tape's numbers would be inventing
 * figures with no artefact behind them, which is the one thing this project does not ship.
 * ticker.json makes the same promise about its own templates.
 *
 * MIN_MS EXISTS BECAUSE THE TAPE CAN FINISH TOO FAST TO READ. On a warm replay the whole stream lands
 * in well under a second, and a reasoning state that flashes past reads as a glitch rather than as
 * work. So the console holds the sequence open for a few seconds even when the work is already done,
 * and it never resolves EARLIER than the real tape does.
 */

const STAGE_NAMES = ['PERCEIVE', 'SOLVE', 'BOUND', 'DECIDE', 'ACT', 'SCORE', 'RECALIBRATE'] as const

/** How long the reasoning is held open at minimum, and how long each phrase sits. */
const MIN_MS = 5200
const PHRASE_MS = 1150

/** Short phrases, in pipeline order. Each describes what a stage DOES, which is a fact about the
 *  pipeline rather than about the data, so none of them can go stale against an artefact. */
const PHRASES: string[] = [
  'Reading the vendor field...',
  'Loading real station hours...',
  'Solving the plume...',
  'Turning the wind through every bearing...',
  'Calibrating bounds...',
  'Pondering margins...',
  'Evaluating chiller data...',
  'Planning the schedule...',
  'Weighing the plant envelope...',
  'Attaching a bound to every hour...',
  'Scoring itself on held-out days...',
  'Widening its own margin...',
]

/** The engine's buttons that mean "a run has started". */
const RUN_BUTTONS = ['runagent', 'runagent2', 'livego']

function tapeDone(): boolean {
  const el = document.getElementById('tapedone')
  return !!(el?.textContent || '').trim()
}

/* A LIVE RUN NEVER WRITES #tapedone, and gating on it was a real bug the user hit: the element is
   filled by streamTape(), which is the REPLAY path. So after "Run the agent on live data" the
   console stayed in its reasoning state for as long as the tab was open, `phase` never became
   'ready', and the whole button row -- Download PDF and the live report -- never rendered at all.
   A live run's own completion signal is the summary line drawLive() writes, or the schedule table
   it fills. Either one means the run has settled, including when it settled on a refusal. */
function liveDone(): boolean {
  const msg = document.getElementById('livemsg')
  if ((msg?.textContent || '').trim()) return true
  const table = document.getElementById('livetable')
  return !!table?.querySelector('tr')
}

function tapeStage(): number {
  const tape = document.getElementById('tape')
  if (!tape) return 0
  let stage = 0
  for (const el of Array.from(tape.children) as HTMLElement[]) {
    if (el.classList.contains('n')) {
      const n = parseInt((el.textContent || '').trim(), 10)
      if (Number.isFinite(n)) stage = Math.max(stage, n)
    }
  }
  return stage
}

export function AgentConsole({ pdfHref }: { pdfHref: string | null }) {
  const [phase, setPhase] = useState<'reasoning' | 'ready'>('reasoning')
  const [idx, setIdx] = useState(0)
  const [stage, setStage] = useState(0)
  const startedAt = useRef<number>(0)
  /* Whether the run being watched is a LIVE one. The engine holds the job id privately, so
     this is inferred from WHICH button started the run, which is the same signal `begin`
     already listens for. Only #livego means a vendor call happened. */
  const [wasLive, setWasLive] = useState(false)

  /* One restartable run of the sequence. `startedAt` is a ref, not state: the interval below reads it
     and must not be re-created every time it changes. */
  const begin = useCallback(() => {
    startedAt.current = performance.now()
    setIdx(0)
    setPhase('reasoning')
  }, [])

  /* Start on mount. Opening this tab at the results stage is itself the moment to show the work. */
  useEffect(() => { begin() }, [begin])

  /* AND RESTART ON ANY RUN BUTTON. Capture phase, so this sees the click even though the engine's own
     handler is bound to the same element. It only OBSERVES: the engine's handler is what actually
     runs the agent, and nothing here interferes with it or duplicates it. */
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null
      const btn = t && t.closest ? (t.closest('button, a') as HTMLElement | null) : null
      if (btn && RUN_BUTTONS.includes(btn.id)) {
        setWasLive(btn.id === 'livego')
        begin()
      }
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [begin])

  /* One interval drives both the phrase and the stage read, so they cannot drift apart, and it stops
     the moment the sequence resolves. */
  useEffect(() => {
    if (phase !== 'reasoning') return
    const id = setInterval(() => {
      setIdx((i) => i + 1)
      setStage(tapeStage())
      /* Resolves only when BOTH the minimum has elapsed AND the real tape has finished, so the console
         can never claim a decision the engine has not actually reached. */
      const settled = wasLive ? liveDone() : tapeDone()
      if (performance.now() - startedAt.current >= MIN_MS && settled) setPhase('ready')
    }, PHRASE_MS)
    return () => clearInterval(id)
  }, [phase, wasLive])

  const phrase = PHRASES[idx % PHRASES.length]
  const stageLabel = stage >= 1 && stage <= 7 ? STAGE_NAMES[stage - 1] : ''

  return (
    <div className="aa-console-wrap">
      {/* LINE ONE: the agent thinking, or the conclusion. */}
      <motion.div
        className={`aa-console ${phase === 'ready' ? 'is-done' : 'is-run'}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* THE ORBITING ICON. Two counter-rotating arcs around a core, so it reads as thinking rather
            than as a progress spinner, which would imply a percentage nobody is measuring. */}
        <span className="aa-orbit" aria-hidden="true" data-state={phase}>
          <i className="aa-orbit-a" />
          <i className="aa-orbit-b" />
          <i className="aa-orbit-core" />
        </span>

        <div className="aa-console-line" aria-live="polite">
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={phase === 'ready' ? 'done' : idx % PHRASES.length}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className={phase === 'reasoning' ? 'aa-shimmer' : undefined}
            >
              {phase === 'ready' ? 'Decision ready. Every hour carries its own bound.' : phrase}
            </motion.span>
          </AnimatePresence>
        </div>

        {phase === 'reasoning' && stageLabel && (
          <span className="aa-console-stage">{stageLabel}</span>
        )}
      </motion.div>

      {/* LINE TWO: the payoff, on its own row as asked. It points at a REAL file, the per-site
          report.pdf named in sites.json's artefacts map, and is not rendered when the manifest names
          none, rather than offering a dead link. */}
      <AnimatePresence initial={false}>
        {phase === 'ready' && pdfHref && (
          <motion.div
            key="dlrow"
            className="aa-console-dlrow"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
          >
            <motion.a
              href={pdfHref}
              download
              className="aa-console-dl"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.985 }}
            >
              <Download size={15} strokeWidth={2.4} aria-hidden="true" />
              Download PDF
            </motion.a>
            {/* 🔴 THE LIVE RUN'S OWN REPORT, and it is a DIFFERENT DOCUMENT from the one beside it.
                The button on the left downloads the per-site report, generated at build time from
                saved responses for one named configuration. This one is built at request time from
                the job that just ran: its hours, its bounds, its gates and its reasoning hour by
                hour, plus the seven stages as they streamed. serve_live.py reads the PDF back before
                returning a byte of it and refuses to serve one that fails its own check.
                Shown only after a LIVE run, because after a replay there is no live moment to report
                on and offering it would imply one. */}
            {wasLive && (
              <motion.a
                href={ART + 'api/live/report/latest'}
                download
                className="aa-console-dl is-live"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: 'spring', stiffness: 420, damping: 30, delay: 0.08 }}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.985 }}
              >
                <FileText size={15} strokeWidth={2.4} aria-hidden="true" />
                Live run report
              </motion.a>
            )}
            <span className="aa-console-dlnote">
              {wasLive
                ? 'Two documents: the site report, and this run’s own hours and reasoning.'
                : 'A snapshot of this configuration. The panels recompute for whatever you select.'}
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
