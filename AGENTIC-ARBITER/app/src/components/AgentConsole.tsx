import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ART } from '../lib/artefacts'
import { ArrowRight, Download, FileText } from 'lucide-react'

/**
 * The agent as ONE LINE: an orbiting icon, a short reasoning phrase that changes every second or so,
 * and then, on the line below, the report download and the way into the findings tabs.
 *
 * THE SEQUENCE, which is what the previous version got wrong. It showed "Decision ready" and the
 * button immediately, because the replay tape had already finished before anyone looked, so a reader
 * never saw the agent reason at all. Now the reasoning always plays first:
 *
 *     reasoning   orbiting icon + rotating phrases, held open for at least MIN_MS
 *     ready       one line: "Decision ready", and the button row beneath it
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

/**
 * 🔴 THE REASONING PLAYS ONCE PER VISIT, AND THIS MODULE-LEVEL FLAG IS WHY.
 *
 * The user: "the first time the user runs the agent and lands on this page the circle swirls and this
 * reasoning is seen, but then later on, when it stops and user goes to different other tabs or runs
 * the agent live, this reasoning doesnt start again. It remains stopped."
 *
 * Two things were making it replay, and only one of them was obvious:
 *   1. EngineStage mounts this component with `{tab === 'live' && ...}`, so leaving the tab UNMOUNTS
 *      it and coming back MOUNTS A NEW ONE. React state cannot survive that, which is why this lives
 *      outside the component rather than in a `useRef`.
 *   2. a capture-phase listener deliberately restarted the sequence on every run button, including
 *      "Run the agent on live data". That was a considered decision at the time and the user has now
 *      reversed it explicitly, naming that case.
 *
 * Module scope rather than sessionStorage: the intent is "once while this page is open". A reload is a
 * new visit and the agent really is starting again, so the swirl belongs there. The flag dies with the
 * page, which is exactly that rule.
 */
let reasoningPlayed = false

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

export function AgentConsole({
  pdfHref,
  onSeeFindings,
}: {
  pdfHref: string | null
  /** Switch to the first of the findings tabs. Supplied by EngineStage, which owns the tab state. */
  onSeeFindings?: () => void
}) {
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

  /* Start on mount, but ONLY the first time in this visit. Every later mount -- coming back to the
     tab, or a live run -- opens straight on the conclusion. See `reasoningPlayed` above. */
  useEffect(() => {
    if (reasoningPlayed) {
      setPhase('ready')
      return
    }
    begin()
  }, [begin])

  /* Remember it the moment it resolves, rather than when it starts: a sequence the reader never got
     to see (they left the tab after two seconds) should still be shown in full next time. */
  useEffect(() => {
    if (phase === 'ready') reasoningPlayed = true
  }, [phase])

  /* 🔴 THE RUN BUTTONS NO LONGER RESTART THE SWIRL, only record WHICH run it was.
     This used to call `begin()`, so pressing "Run the agent on live data" replayed the reasoning. The
     user reversed that: it must remain stopped. What the listener still has to do is note whether the
     run was LIVE, because the two paths have different completion signals -- a replay fills #tapedone
     and a live run does not -- and the first sequence of the visit may still be waiting on one.
     Capture phase, and it only OBSERVES: the engine's own handler is what runs the agent. */
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null
      const btn = t && t.closest ? (t.closest('button, a') as HTMLElement | null) : null
      if (btn && RUN_BUTTONS.includes(btn.id)) setWasLive(btn.id === 'livego')
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [])

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
              {/* 🔴 "Download PDF" SAID NOTHING ABOUT WHAT THE PDF IS. The user: "change the name of
                  this button from download pdf to something meaningful, like what pdf the user doesnt
                  know what the pdf means here." They are right: on a screen with a live-run report
                  beside it, two buttons both reading "PDF" is a coin toss. This one is the SITE's
                  report for the configuration on screen, so it says so, and the note underneath still
                  explains what a snapshot means. */}
              Download this site&rsquo;s report
            </motion.a>
            {/* 🔴 THE WAY INTO WHAT THE AGENT FOUND, and it did not exist before.
                The user: "there is no pop up, or option which takes the users to these tabs ... So
                before the card of live agent, add a button with some phrase written on it that takes
                users to these tabs starting from the first one."
                The rail has always been there, but nothing on this screen POINTED at it, so a reader
                who ran the agent was left on the live tab with the run finished and no next step. It
                sits immediately right of the download, which is where the eye already is once the
                sequence resolves.
                It calls the same `setTab` the rail calls; there is no second navigation mechanism.
                'schedule' is the first tab of the WHAT THE AGENT FOUND group, which is the "starting
                from the first one" the instruction asks for. Rendered only when the caller supplies a
                handler, so the console still works anywhere that does not have tabs. */}
            {onSeeFindings && (
              <motion.button
                type="button"
                onClick={onSeeFindings}
                className="aa-console-dl is-next"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: 'spring', stiffness: 420, damping: 30, delay: 0.04 }}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.985 }}
              >
                See what the agent found
                <ArrowRight size={15} strokeWidth={2.4} aria-hidden="true" />
              </motion.button>
            )}

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
