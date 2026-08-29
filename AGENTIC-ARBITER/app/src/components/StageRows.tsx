/**
 * THE FIVE AGENT STAGES, AS A SECTION BELOW THE FOLD.
 *
 * 🔴 THIS IS A RELOCATION, NOT A REWRITE. These rows used to be in the splash, between the subhead
 * and the call to action. The user's instruction: "Delete the five horizontal rows from the hero ...
 * Do not delete the underlying component or data wiring, move it below the fold as a section further
 * down the landing page. It explains what the agent does and I still want it, just not competing
 * with the globe in the hero."
 * So the data, the icons, the notes, the timestamps, the stagger and the chime all came across
 * intact. What changed is where they are and what starts them.
 *
 * 🔴 IT LIVES OUTSIDE `intro/`, AND THAT IS THE POINT OF THE MOVE.
 * Everything in `intro/` is motion, and `?motion=off` unmounts all of it. These rows are now CONTENT:
 * they are the only place on the landing page that says what the seven-stage loop actually does in
 * words. A reader who turned motion off, or who is on a phone, must still get them. So this
 * component is rendered by `App.tsx` inside the pick stage's own `[data-show="pick"]` block, which
 * the engine's `setStage()` hides on the way to configure, exactly like the rest of the pick screen.
 * The FLAGS still decide the animation, and nothing else.
 *
 * 🔴 IT STARTS WHEN IT IS SEEN, NOT WHEN IT MOUNTS. Below the fold, a mount-time stagger runs while
 * the reader is still looking at the hero and is finished before they arrive: the animation would
 * exist and never be seen, and the timestamps would all read the moment the page loaded rather than
 * the moment anything happened. An IntersectionObserver starts it on first entry and then
 * disconnects, so it plays once.
 *
 * ⚠ THE CHIME CAME WITH THE ROWS, AND THAT IS A JUDGEMENT CALL. The original brief asked for a cue
 * "precisely when each widget completes its entry animation", which is still literally what happens,
 * just further down the page. If a chime on scroll is unwanted, `CHIME_ON_ARRIVAL` below turns it off
 * on its own without touching anything else.
 */
import { useEffect, useRef, useState } from 'react'
import { Activity, Gauge, GitBranch, Radar, ShieldCheck } from 'lucide-react'
import { readFlags } from '../intro/flags'
import * as audio from '../intro/audio'
import './stagerows.css'

/** Set false to keep the entry animation and drop the sound. See the note above. */
const CHIME_ON_ARRIVAL = true

/**
 * The five stages, in pipeline order, from AgentConsole.tsx's own list. SOLVE folds into BOUND and
 * RECALIBRATE is the loop closing, exactly as `intro/Pipeline.tsx` draws it.
 *
 * 🔴 NOT ONE FIGURE HERE COMES FROM AN ARTEFACT, and that is deliberate rather than lazy. Stage names
 * and what a stage is FOR are facts about the pipeline; a number would be a claim about a particular
 * site and this section is not attached to one. `AgentConsole.tsx` and `ticker.json` make the same
 * promise about their own copy.
 */
export const STAGES = [
  { key: 'perceive', Icon: Radar, label: 'PERCEIVE', note: 'the 2 m field, hour by hour' },
  { key: 'bound', Icon: ShieldCheck, label: 'BOUND', note: 'a margin measured from past error' },
  { key: 'decide', Icon: GitBranch, label: 'DECIDE', note: 'under a switch budget' },
  { key: 'act', Icon: Gauge, label: 'ACT', note: 'setpoints for the plant' },
  { key: 'score', Icon: Activity, label: 'SCORE', note: 'coverage against the promise' },
] as const

/** How far apart the rows arrive. 420 ms reads as a sequence; much less reads as one event. */
const STAGGER_MS = 420
/** Matches the entry animation in stagerows.css, so the chime lands as a row SETTLES rather than as
 *  it starts moving. One number, two files, and the CSS says so too. */
const ENTER_MS = 520

/** HH:MM:SS.mmm, local. The real arrival time; there is nothing to gain from faking a clock. */
function stamp(): string {
  const d = new Date()
  const p = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}.${p(d.getMilliseconds(), 3)}`
}

export function StageRows() {
  /* Read once. `readFlags()` resolves the URL parameter, then localStorage, then the constant, and
     reading it twice is how two components end up disagreeing about whether audio is allowed. */
  const flagsRef = useRef<ReturnType<typeof readFlags> | null>(null)
  if (flagsRef.current === null) flagsRef.current = readFlags()
  const flags = flagsRef.current

  /* 🔴 WITH MOTION OFF, REDUCED MOTION, OR A NARROW SCREEN, EVERY ROW IS PRESENT FROM THE FIRST
     RENDER. Not hidden and revealed instantly: present, with its timestamp already taken. A section
     whose content depends on an animation having run is a section that disappears when the animation
     does not, which is the failure `flags.ts` exists to prevent. */
  const instant = !flags.motion || flags.reduced || flags.narrow

  const [arrived, setArrived] = useState<{ key: string; at: string }[]>(() =>
    instant ? STAGES.map((s) => ({ key: s.key, at: stamp() })) : [],
  )

  /**
   * 🔴 THE WATCHDOG, AND IT IS A PRODUCT FIX RATHER THAN A TEST FIX.
   *
   * MEASURED: `verify_intro.py` found all five rows sitting at opacity 0 after their entrance should
   * have finished. The cause is the trap this project already recorded for GSAP (05-TRAPS 5b.13) and
   * it applies to CSS animations too: THE ANIMATION CLOCK DOES NOT ALWAYS ADVANCE. While an animation
   * is in its active phase it overrides the element's own declared style, so a clock frozen at
   * progress 0 holds the `from` keyframe, which here is `opacity: 0`. FILL MODE CANNOT SAVE THAT --
   * that was my first attempt and it changed nothing, because the animation is active rather than
   * before or after its range.
   * These rows are the only plain-language account of the loop on this page, so "invisible until an
   * animation completes" is not an acceptable failure mode for them.
   *
   * So each row is marked settled by a `window.setTimeout`, which is a WALL-CLOCK timer and cannot
   * be frozen with the animation clock, and `stagerows.css` cancels the animation for a settled row.
   * If the clock was working, the animation had already finished and cancelling it changes nothing
   * visible. If it was not, the row snaps to its finished state. Either way the page ends up
   * FINISHED rather than empty, which is the standard `intro/timeline.ts` already holds itself to
   * with its own watchdog.
   */
  const [settled, setSettled] = useState<string[]>(() => (instant ? STAGES.map((s) => s.key) : []))
  const section = useRef<HTMLElement | null>(null)
  const timers = useRef<number[]>([])
  const started = useRef(instant)

  useEffect(() => {
    const el = section.current
    if (!el || started.current) return

    const begin = () => {
      if (started.current) return
      started.current = true
      STAGES.forEach((s, i) => {
        timers.current.push(
          window.setTimeout(() => {
            setArrived((m) => (m.some((x) => x.key === s.key) ? m : [...m, { key: s.key, at: stamp() }]))
            /* The watchdog and the chime are the same moment: the row has finished arriving. A little
               slack past ENTER_MS so a healthy animation is allowed to end on its own rather than
               being cut off one frame early. */
            timers.current.push(
              window.setTimeout(() => {
                setSettled((k) => (k.includes(s.key) ? k : [...k, s.key]))
              }, ENTER_MS + 120),
            )
            if (CHIME_ON_ARRIVAL && flags.audio) {
              timers.current.push(window.setTimeout(() => audio.chime(), ENTER_MS))
            }
          }, i * STAGGER_MS),
        )
      })
    }

    /* No IntersectionObserver (an old browser, a test harness that stubs it): start immediately
       rather than leave the section empty for ever. A missing capability must degrade to the content
       being there, never to the content being absent. */
    if (typeof IntersectionObserver === 'undefined') {
      begin()
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            begin()
            io.disconnect()
          }
        }
      },
      /* A third of the section has to be on screen. A 0 threshold fires while it is still one pixel
         below the fold, which is the same "played before anyone saw it" failure one step smaller. */
      { threshold: 0.34 },
    )
    io.observe(el)
    return () => io.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    return () => {
      for (const t of timers.current) window.clearTimeout(t)
      timers.current = []
    }
  }, [])

  return (
    <section ref={section} className="aa-stagerows" aria-labelledby="aa-stagerows-h">
      <h2 id="aa-stagerows-h" className="aa-stagerows-h">
        What the agent does, every hour
      </h2>
      <p className="aa-stagerows-sub">
        Five stages run for each hour of the horizon. The loop closes on the last one: what it scores
        is what sizes the next margin.
      </p>

      <ul className="aa-stagerows-list">
        {STAGES.map((s) => {
          const a = arrived.find((x) => x.key === s.key)
          if (!a) return null
          const { Icon } = s
          return (
            <li
              className="aa-stagerow"
              key={s.key}
              /* Set by the wall-clock watchdog above. stagerows.css cancels the entry animation for a
                 settled row, which is what guarantees the finished state whether or not the animation
                 clock ever ran. It is also the signal verify_intro.py asserts, because the END STATE
                 is the one thing that can honestly be measured about an animation. */
              data-settled={settled.includes(s.key) ? '1' : undefined}
            >
              <Icon className="aa-stagerow-icon" size={16} strokeWidth={2.2} aria-hidden="true" />
              <span className="aa-stagerow-label">{s.label}</span>
              <span className="aa-stagerow-note">{s.note}</span>
              {/* The arrival time, taken when this row appeared. */}
              <time className="aa-stagerow-time">{a.at}</time>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
