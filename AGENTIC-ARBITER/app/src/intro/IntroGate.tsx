/**
 * THE SPLASH SCREEN. One-time, interactive, and the click is still what unlocks audio.
 *
 * WHAT CHANGED FROM THE ENTER GATE THIS REPLACES:
 *
 * 🔴 THE "SOUND ON" TOGGLE IS GONE, at the user's instruction ("Remove any existing Sound on toggle
 * buttons from this page"). That reverses an earlier instruction of theirs -- "a small mute toggle on
 * the gate itself, so a judge in a quiet room can opt out before anything plays" -- so the reversal is
 * honoured LITERALLY: gone from this page, and the persistent corner toggle IntroLayer renders once
 * the splash closes stays. A judge still has a way out, one click later than before.
 * `prefers-reduced-motion` still defaults audio off, because that is an accessibility rule rather
 * than a control.
 *
 * 🔴 THE CLICK IS WHERE THE AUDIO STARTS NOW, and that removed a whole mechanism rather than moving
 * it. The narration used to be attempted on mount with a first-interaction fallback, because no browser
 * permits autoplay with sound. Since 2026-08-29 the voiceover is the first act of the launch sequence
 * (`intro/launch.ts`), and a click IS the gesture browsers require, so the fallback is not merely
 * unused: it is unnecessary. What this file still owns is preloading the three files and arming the
 * button when they are in.
 *
 * 🔴 THE FIVE STAGE ROWS ARE GONE FROM HERE, moved 2026-08-29 to `components/StageRows.tsx`, below
 * the map on the landing page. The user's instruction: they were "competing with the globe in the
 * hero". Nothing was deleted; the data, the icons, the notes, the timestamps, the stagger and the
 * chime all moved together, and the stagger now starts when the section is scrolled into view rather
 * than on mount. This file therefore no longer imports lucide or `audio.chime`.
 * ⚠ The hero is now exactly five things: eyebrow, wordmark, subhead, call to action, FortyGuard mark.
 * Adding a sixth is how it grows back.
 *
 * 🔴 STILL TRUE, AND IT IS THE RULE THAT MATTERS MOST HERE: NOT ONE FIGURE FROM ANY ARTEFACT APPEARS
 * ON THIS SCREEN. A splash is the first thing a judge sees and the one thing it must never do is show
 * a value that has drifted. The globe's own comment makes the same promise about its markers.
 *
 * 🔴 IT MUST NOT BLOCK THE PRODUCT. `verify_app_flow.py` clicks "Configure this plant"; an overlay
 * that swallows that click stalls the check at step 1. `?motion=off` skips this component entirely,
 * and once dismissed it is UNMOUNTED rather than left transparent over the page.
 */
'use client'

import { useEffect, useRef, useState } from 'react'
import { ShinyButton } from '@/components/ui/shiny-button'
import { ART } from '../lib/artefacts'
import { markEntered, type IntroFlags } from './flags'
import * as audio from './audio'
import { HeatGlobe } from './HeatGlobe'

/** How long the CTA will wait for the three audio files before arming anyway. */
const ARM_CAP_MS = 1500

export function IntroGate({
  flags,
  wantsAudio,
  onEnter,
}: {
  flags: IntroFlags
  /**
   * Whether the reader wants sound RIGHT NOW, as opposed to whether audio was allowed when the layer
   * mounted. `flags` is resolved once; the corner mute toggle lives outside this component and can
   * change the answer after that, so the live value is passed in rather than read from the snapshot.
   */
  wantsAudio: boolean
  /** Called once, with whether sound is wanted. The caller starts the timeline. */
  onEnter: (withAudio: boolean) => void
}) {
  const [leaving, setLeaving] = useState(false)
  /**
   * 🔴 IMMEDIATE FEEDBACK, WHICH THE BRIEF FLAGS AS MATTERING: "Button enters an active/committed
   * state: disable further clicks, dim or collapse the label. It must be visually obvious the click
   * registered." On a sequence whose whole point is that the screen does NOT change for several
   * seconds, the button is the only thing that can say the click landed.
   */
  const [committed, setCommitted] = useState(false)
  /**
   * WHETHER THE CTA IS ARMED. The brief: "Preload all three files during page load, before the button
   * becomes interactive. If they haven't loaded when clicked, run the visual sequence without audio
   * rather than waiting."
   * Those two clauses pull against each other, so both are honoured: the button waits for the files,
   * but never for longer than ARM_CAP_MS. In practice the three files are local and total 175 KB, so
   * this resolves in a few milliseconds and is never seen; the cap exists so a slow or missing asset
   * cannot leave a dead control on screen, which would be a worse failure than a silent sequence.
   */
  const [armed, setArmed] = useState(false)
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const returnFocusTo = useRef<HTMLElement | null>(null)
  const done = useRef(false)

  /* ---- PRELOAD ALL THREE, and arm the button when they are in or when the cap expires. */
  useEffect(() => {
    if (!flags.audio || !flags.cinematic) {
      /* Nothing to wait for: a muted or non-cinematic run has no cues to load. */
      setArmed(true)
      return
    }
    audio.preload()
    if (audio.ready()) {
      setArmed(true)
      return
    }
    /* Polled rather than listened for, deliberately: `canplaythrough` on three elements is three
       listeners, three removals and a race about which fires last, and this is a 120 ms poll against a
       local file. It stops at the cap either way. */
    const t0 = performance.now()
    const iv = window.setInterval(() => {
      if (audio.ready() || performance.now() - t0 > ARM_CAP_MS) {
        window.clearInterval(iv)
        setArmed(true)
      }
    }, 120)
    return () => window.clearInterval(iv)
  }, [flags.audio, flags.cinematic])

  /* 🔴 THE NARRATION USED TO BE ATTEMPTED HERE, ON MOUNT, WITH A FIRST-INTERACTION FALLBACK.
     It is gone, and that reverses an earlier instruction of the user's ("The MP3 voice narration must
     play automatically, triggering on the first user interaction if blocked by browser autoplay
     policies"). The current brief moves it: "On click of Initialize Arbiter: ... voiceover.mp3
     starts." That is strictly better as well as newer, because a click IS the user gesture browsers
     require, so the whole autoplay-refusal fallback becomes unnecessary rather than merely unused.
     `intro/launch.ts` owns it now. */

  /* ---- LOCK THE PAGE. Measured bug: the splash is `position: fixed; inset: 0`, which covers the
     viewport but does not stop the document behind it scrolling, and a reader who scrolled arrived
     mid-page (scrollY 501 of a 1,345px document). On documentElement, because only the ROOT element's
     overflow propagates to the viewport -- on <body> alone it changed nothing. The scrollbar's width
     is reserved so the page does not shift sideways as the lock comes off during the sweep. */
  useEffect(() => {
    const html = document.documentElement
    const b = document.body
    const prevHtml = html.style.overflow
    const prevBody = b.style.overflow
    const prevPad = b.style.paddingRight
    const sbw = window.innerWidth - html.clientWidth
    html.style.overflow = 'hidden'
    b.style.overflow = 'hidden'
    if (sbw > 0) b.style.paddingRight = sbw + 'px'
    return () => {
      html.style.overflow = prevHtml
      b.style.overflow = prevBody
      b.style.paddingRight = prevPad
    }
  }, [])

  /* ---- FOCUS: taken on mount, restored on the way out.
     Queried rather than held in a ref, because ShinyButton is used exactly as supplied and does not
     forward one. Changing its public shape to add forwardRef would be changing a component the brief
     said to use as given. */
  useEffect(() => {
    returnFocusTo.current = document.activeElement as HTMLElement | null
    dialogRef.current?.querySelector<HTMLElement>('.shiny-cta')?.focus()
    return () => {
      const back = returnFocusTo.current
      if (back && typeof back.focus === 'function' && document.contains(back)) back.focus()
    }
  }, [])

  /* ---- FOCUS IS CONTAINED, because aria-modal is a promise. The splash is an opaque full-viewport
     overlay; without this, Tab walked out onto the theme toggle and the site picker behind it. */
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const f = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), [href]') ?? [],
      )
      if (!f.length) return
      const first = f[0]
      const last = f[f.length - 1]
      const active = document.activeElement
      const inside = dialogRef.current?.contains(active)
      if (e.shiftKey && (active === first || !inside)) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || !inside)) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [])

  const go = (withAudio: boolean) => {
    /* 🔴 THE DOUBLE-CLICK GUARD, and it is a ref rather than state on purpose: two clicks in the same
       tick would both read a stale `false` from state and both start a sequence. A ref is written
       synchronously. The brief asks for this by name. */
    if (done.current) return
    done.current = true
    setCommitted(true)
    /* THE ONE-TIME FLAG, set here rather than after the sweep: a reader who reloads mid-transition
       must not be shown the splash again. */
    markEntered()
    setLeaving(true)
    onEnter(withAudio)
  }

  /* Escape enters silently, for a reader who wants the thing gone rather than the show. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') go(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div
      ref={dialogRef}
      className={'aa-gate aa-splash' + (leaving ? ' is-leaving' : '')}
      role="dialog"
      aria-modal="true"
      aria-labelledby="aa-gate-title"
    >
      {/* 🔴 THE GLOBE IS RENDERED ON NARROW SCREENS TOO NOW, and that is a change of position worth
          stating. The old cobe globe was withheld under 768px and the CSS hid it as well. The brief
          for the Three.js one asks instead for a REDUCED version there: no cloud layer, no rotation,
          the sphere and its rim glow still present. So the flags are passed through rather than used
          as a gate, and `HeatGlobe` renders one static frame and stops in either reduced case.
          IntroLayer still refuses to render this whole component under 768px, so in practice this
          path is reached by a wide session dragged narrow. Both switches are honoured at the point
          they mean something rather than by not mounting. */}
      <HeatGlobe reduced={flags.reduced} narrow={flags.narrow} />

      <div className="aa-gate-inner aa-splash-inner">
        <p className="aa-gate-eyebrow">Free-cooling decisions, hour by hour</p>

        <h1 id="aa-gate-title" className="aa-gate-title">
          AGENTIC<span className="aa-gate-dot">·</span>ARBITER
        </h1>

        <p className="aa-gate-sub">
          An agent that decides, hour by hour, when outside air can cool a data centre, and refuses
          the hours it cannot stand behind.
        </p>

        <div className="aa-gate-actions">
          <ShinyButton
            /* 🔴 `wantsAudio`, NOT `flags.audio`, BECAUSE THE READER MAY HAVE CHANGED IT SINCE MOUNT.
               `flags` is resolved once when IntroLayer mounts. The corner mute toggle writes a new
               choice and lives outside this component, so a reader who turns the sound back on and
               then presses Initialize Arbiter would otherwise start a run that had already decided to
               be silent. The live value is passed in. */
            onClick={() => go(wantsAudio)}
            className={'aa-splash-cta' + (committed ? ' is-committed' : '')}
            /* Disabled once committed, so further clicks cannot reach the handler at all rather than
               being turned away by the ref guard alone. Belt and braces, and the disabled state is
               also what makes the commitment visible to a screen reader. */
            disabled={committed || leaving || !armed}
            aria-label="Initialize Arbiter and open the site map"
          >
            {/* The label collapses to a working state on commit, which is the brief's "dim or collapse
                the label". `aria-live` so the change is announced rather than only seen. */}
            <span aria-live="polite">{committed ? 'Initializing' : 'Initialize Arbiter'}</span>
          </ShinyButton>
        </div>

        {/* POWERED BY, with the mark. Labelled, for the reason App.tsx's banner records: a bare
            FortyGuard wordmark on a product called AGENTIC-ARBITER reads as though FortyGuard built
            it, which is not true. */}
        <div className="aa-gate-brand">
          <span className="aa-gate-by">Powered by</span>
          <img src={ART + 'fortyguard-logo.png'} alt="FortyGuard" />
        </div>
      </div>
    </div>
  )
}
