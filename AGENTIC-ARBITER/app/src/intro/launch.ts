/**
 * THE LAUNCH SEQUENCE. What "Initialize Arbiter" starts.
 *
 * A timed cinematic hold: the screen does not change on the click. It stays on the globe while the
 * voiceover plays over a slow camera push-in, holds a beat after the voice, then crosses over to the
 * site picker on a whoosh.
 *
 * ────────────────────────────────────────────────────────────────────────────────────────────────
 * 🔴 ONE TIMELINE OWNS THE VISUALS. AUDIO IS FIRED AT LABELS AND DRIVES NOTHING.
 * The brief's reasoning, kept because it is the reason this file is shaped the way it is: "Do not
 * chain steps off audio.onended, if a file fails to load or is blocked, the sequence would stall
 * forever and the user would be stuck on a dead screen." So there is no audio listener anywhere in
 * this file. `playVoice()` and `playWhoosh()` are called from timeline callbacks and their return
 * values are ignored.
 *
 * 🔴 AND A WALL-CLOCK WATCHDOG OWNS COMPLETION, WHICH IS ONE STEP FURTHER THAN THE BRIEF ASKS.
 * The brief protects against audio stalling. This project has MEASURED a second stall the brief does
 * not mention: `05-TRAPS` 5b.13, GSAP's clock failing to advance under some conditions, which would
 * leave a GSAP-owned `onComplete` never firing and the reader on the very dead screen the escape
 * hatch exists for. So `finish()` is also scheduled on a plain `window.setTimeout`, and whichever
 * arrives first wins because `finish()` is idempotent.
 * The division is clean: the TIMELINE owns what the pixels do, a TIMER owns when the sequence is
 * over, and those are different facts rather than two owners of one.
 * ────────────────────────────────────────────────────────────────────────────────────────────────
 */
import { gsap } from 'gsap'
import * as audio from './audio'
import { setDolly } from './globeDolly'

/** The sequence, in seconds, all relative to the click. */
const BEATS = {
  /**
   * How long the voice segment runs. MEASURED from the shipped file's own MPEG frame headers by
   * `tools/measure_audio.py`: 179 frames of 1152 samples at 44.1 kHz, which is 4.676 s.
   *
   * ⚠ THE BRIEF SAYS "~7s" AND THE FILE IS 4.676 s. It is the same file the project measured this
   * morning (identical frame count), so the longer recording the brief describes has not arrived. The
   * sequence is built from the measurement rather than from the stated figure, because the brief's own
   * rationale forbids the alternative: "Do not play 9 seconds of silence", and 2.3 s of dead air
   * before the hold is exactly that.
   * It is also SELF-HEALING: `resolve()` below takes whichever is longer, the constant or the duration
   * the browser reports for the real element, so dropping in a 7 s take needs no code change. Reading
   * a duration cannot stall, which is why that is a read and never a wait.
   */
  voiceS: 4.676,
  /** "Hold for 1.0s. Globe push-in continues, slowing." */
  holdS: 1.0,
  /** "Landing screen fades/scales out over ~1.2s". */
  outS: 1.2,
  /**
   * Where the whoosh's low pad lands, measured by ear against a 1.959 s file: about 1.0 s in. The
   * crossfade is timed so the new screen becomes visible at that moment, which is what the brief asks
   * for, so the whoosh starts 1.0 s BEFORE the out transition finishes.
   */
  whooshPadS: 1.0,
  /** The muted and reduced-motion path. "Shorten the sequence to ~1.5s total." */
  shortS: 1.5,
  /** The escape hatch's fade. "Fade through in ~250ms." */
  escapeS: 0.25,
} as const

/** How far the camera travels. 0.16 is a 16 % reduction in distance over the whole voiceover: enough
 *  that the planet is visibly growing if you watch it, not enough to reframe the composition the user
 *  measured and signed off. */
const DOLLY_TO = 1.0

export type LaunchHandle = {
  /** Idempotent. Kills the timeline, stops audio, unbinds the hatch. Does NOT call onFinish. */
  kill: () => void
}

export type LaunchOpts = {
  /** Play the three cues. False for a muted run: the visual sequence still runs, shortened. */
  audio: boolean
  /** Skip the push-in and use a plain crossfade, per the brief's reduced-motion clause. */
  reduced: boolean
  /** The splash element to fade and scale out. */
  gate: HTMLElement | null
  /** Called once the sequence is over, whether it ran to completion or was escaped. */
  onFinish: () => void
  /**
   * 🔴 FIRED WHEN THE CROSSFADE STARTS, NOT WHEN IT ENDS, and it exists so the page behind can be
   * put into its from-state while the splash is still covering it.
   * Everything the incoming screen animates has to be invisible BEFORE the splash starts to
   * disappear, or the reader sees it at rest and then sees it blanked. `onFinish` is too late for
   * that by exactly the length of the crossfade.
   * Called at most once per sequence, whichever way the sequence ends: at the 'out' label on a full
   * run, and at the top of `escape()` on a skipped one.
   */
  onOut?: (crossfadeS: number) => void
  /** Called when the sequence actually begins, so the caller can mark the moment. */
  onStart?: (totalMs: number) => void
}

/** The one place the total is worked out, so the watchdog and the report cannot disagree. */
function resolve(opts: LaunchOpts): { voiceS: number; totalS: number; short: boolean } {
  const short = !opts.audio || opts.reduced
  if (short) return { voiceS: 0, totalS: BEATS.shortS, short: true }
  /* Whichever is longer: the measured constant, or what the browser says the real file is. A file
     that has not loaded reports 0 and the constant wins, which is the point. */
  const reported = audio.voiceDurationMs() / 1000
  const voiceS = Math.max(BEATS.voiceS, Number.isFinite(reported) ? reported : 0)
  return { voiceS, totalS: voiceS + BEATS.holdS + BEATS.outS, short: false }
}

export function playLaunch(opts: LaunchOpts): LaunchHandle {
  const { voiceS, totalS, short } = resolve(opts)

  let tl: gsap.core.Timeline | null = null
  let watchdog = 0
  let escapeTimer = 0
  let done = false
  /** `onOut` is at most once. The escape hatch can fire after the label has already passed. */
  let outFired = false
  const fireOut = (crossfadeS: number) => {
    if (outFired) return
    outFired = true
    try {
      opts.onOut?.(crossfadeS)
    } catch {
      /* The caller's reveal is not allowed to take the transition down with it. The sequence still
         completes and the reader still reaches the page, just without the entrance. */
    }
  }
  /** The pick screen's own fade-in target. Read once: the engine owns nothing in here. */
  const incoming = document.querySelector<HTMLElement>('[data-show="pick"]')

  /* ---- THE ESCAPE HATCH, BOUND FIRST AND DELIBERATELY UNDOCUMENTED.
     🔴 BOUND BEFORE ANYTHING ELSE IN THIS FUNCTION, which is the brief's requirement that it "must
     work even if the audio failed to load or the GSAP timeline never started. Bind it independently
     of the sequence's own state." Everything below this point can throw and the hatch is still armed.
     ⚠ NOTHING VISIBLE IS RENDERED FOR IT, on instruction: "Do not render any visible skip hint,
     button, or text." The rationale is recorded in the brief and worth keeping: it is insurance
     against a dead screen in front of an audience, and it is what makes 9 seconds of unskippable
     motion conform to WCAG 2.2 SC 2.2.2. */
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' || e.key === ' ' || e.code === 'Space' || e.key === 'Spacebar') {
      /* Space would otherwise scroll the document behind the splash. */
      e.preventDefault()
      escape()
    }
  }
  /* `pointerdown` rather than `click`: it is the first event of the gesture, so the escape feels
     immediate. It also cannot receive the click that STARTED the sequence, because that gesture's
     pointerdown was dispatched before this listener existed.

     🔴 BUT IT COULD RECEIVE THE SECOND ONE, AND AN IMPATIENT READER SILENCED THEIR OWN INTRO WITH IT.
     Nothing visible happens for the first moment after Initialize Arbiter is pressed, so a reader who
     is not sure the click registered presses again. That second pointerdown landed on this listener
     and skipped the sequence: MEASURED on the deployed origin, a real second click at +1.5 s cut the
     run from 6,927 ms to 2,060 ms and the transition whoosh, whose turn does not come until +5.9 s,
     never played at all. The reader asked for the thing again and was given less of it.
     A GRACE WINDOW, not a redesign. A deliberate skip is a decision made after watching something;
     it does not happen a fifth of a second after your own click. 600 ms is longer than any double
     click and far shorter than the 6.9 s sequence, so the escape hatch keeps working for everyone
     who actually means it. The keyboard route is deliberately NOT delayed: pressing Escape is
     unambiguous in a way that clicking twice is not. */
  const armedAt = performance.now()
  const POINTER_GRACE_MS = 600
  const onPointer = () => {
    if (performance.now() - armedAt < POINTER_GRACE_MS) return
    escape()
  }
  window.addEventListener('keydown', onKey, true)
  window.addEventListener('pointerdown', onPointer, true)

  function unbind(): void {
    window.removeEventListener('keydown', onKey, true)
    window.removeEventListener('pointerdown', onPointer, true)
  }

  /** Idempotent by the `done` guard, which is what stops repeated presses queueing transitions. */
  function finish(): void {
    if (done) return
    done = true
    unbind()
    window.clearTimeout(watchdog)
    window.clearTimeout(escapeTimer)
    tl?.kill()
    tl = null
    audio.stopAll()
    /* Leave nothing behind on elements this file borrowed. The splash is about to unmount, but the
       pick screen is not and a stray inline opacity would outlive the sequence. */
    if (incoming) gsap.set(incoming, { clearProps: 'opacity,scale' })
    setDolly(0)
    opts.onFinish()
  }

  /**
   * The undocumented exit. Kills the sequence, silences it, and fades through in ~250 ms.
   * 🔴 THE 250 ms IS A WALL-CLOCK TIMER, NOT THE TWEEN'S onComplete. The whole purpose of this path is
   * to work when something is stuck, and a GSAP callback is the wrong thing to depend on for that: it
   * is one of the things that might be stuck. The tween is decoration over a timer.
   */
  function escape(): void {
    if (done) return
    /* The skipped path crossfades over `escapeS` rather than `outS`, so the reveal is told the
       shorter figure and lands with it rather than after it. */
    fireOut(BEATS.escapeS)
    unbind()
    window.clearTimeout(watchdog)
    tl?.kill()
    tl = null
    audio.stopAll()
    if (opts.gate) {
      gsap.to(opts.gate, { opacity: 0, duration: BEATS.escapeS, ease: 'power1.out' })
    }
    if (incoming) gsap.to(incoming, { opacity: 1, scale: 1, duration: BEATS.escapeS })
    escapeTimer = window.setTimeout(finish, BEATS.escapeS * 1000)
  }

  /* ---- THE TIMELINE. Built after the hatch is armed, so a throw in here cannot strand the reader. */
  try {
    tl = gsap.timeline({ onComplete: finish })

    /* The incoming screen starts slightly down and dim, so the reveal is a crossfade rather than the
       splash simply being taken away. Set here rather than in CSS: it must not be the page's resting
       state, only its state during these few seconds. */
    if (incoming && !opts.reduced) {
      gsap.set(incoming, { opacity: 0.35, scale: 1.015, transformOrigin: '50% 40%' })
    } else if (incoming) {
      gsap.set(incoming, { opacity: 0.35 })
    }

    if (short) {
      /* THE MUTED AND REDUCED PATH. "Shorten the sequence to ~1.5s total. Do not play 9 seconds of
         silence." No push-in, no cues, a plain crossfade. */
      tl.addLabel('out', 0)
      tl.call(() => fireOut(BEATS.shortS), undefined, 0)
      if (opts.gate) {
        tl.to(opts.gate, { opacity: 0, duration: BEATS.shortS, ease: 'power2.inOut' }, 'out')
      }
      if (incoming) {
        tl.to(incoming, { opacity: 1, scale: 1, duration: BEATS.shortS, ease: 'power2.out' }, 'out')
      }
    } else {
      /* ---- t = 0: the cues, and the push-in that makes the wait read as deliberate. */
      tl.addLabel('voice', 0)
      tl.call(
        () => {
          audio.playVoice()
        },
        undefined,
        'voice',
      )

      if (!opts.reduced) {
        /* THE DOLLY runs the full voice segment and eases OUT, so it is still moving through the hold
           and visibly slowing, which is the brief's "continues, slowing". Driven through a proxy
           object because the camera is not a DOM node and HeatGlobe owns what `k` means. */
        const k = { v: 0 }
        tl.to(
          k,
          {
            v: DOLLY_TO,
            duration: voiceS + BEATS.holdS,
            ease: 'power1.out',
            onUpdate: () => setDolly(k.v),
          },
          'voice',
        )
      }

      /* ---- the hold, which is a label rather than a tween: nothing happens in it by design. */
      tl.addLabel('hold', voiceS)

      /* ---- the transition. The whoosh starts one padS before the end, so its landing coincides with
         the new screen becoming visible. */
      const outAt = voiceS + BEATS.holdS
      tl.addLabel('out', outAt)
      /* At the label rather than one tick before it: the from-states have to be in place for the
         first frame in which the splash is anything less than opaque. */
      tl.call(() => fireOut(BEATS.outS), undefined, outAt)
      tl.call(
        () => {
          audio.playWhoosh()
        },
        undefined,
        Math.max(0, outAt + BEATS.outS - BEATS.whooshPadS),
      )
      if (opts.gate) {
        tl.to(
          opts.gate,
          { opacity: 0, scale: 1.06, duration: BEATS.outS, ease: 'power2.in' },
          'out',
        )
      }
      if (incoming) {
        tl.to(incoming, { opacity: 1, scale: 1, duration: BEATS.outS, ease: 'power2.out' }, 'out')
      }
    }
  } catch {
    /* A GSAP failure must not cost the reader the product. The watchdog below still completes the
       sequence and the hatch is already armed. */
    tl = null
  }

  /* ---- THE WATCHDOG. 400 ms of slack so it never pre-empts a healthy run. */
  watchdog = window.setTimeout(finish, totalS * 1000 + 400)
  opts.onStart?.(totalS * 1000)

  return {
    kill: () => {
      if (done) return
      done = true
      unbind()
      window.clearTimeout(watchdog)
      window.clearTimeout(escapeTimer)
      tl?.kill()
      tl = null
      audio.stopAll()
      if (incoming) gsap.set(incoming, { clearProps: 'opacity,scale' })
      setDolly(0)
    },
  }
}
