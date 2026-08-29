/**
 * THE ONE MOUNT POINT FOR EVERYTHING IN `intro/`, and the only thing App.tsx knows about.
 *
 * It owns three responsibilities and deliberately no others:
 *   1. read the flags ONCE, so every child agrees about what this load is allowed to do;
 *   2. exist only on the landing stage;
 *   3. tear down audio and (from step 3 on) every timeline when that stops being true.
 *
 * 🔴 "LANDING PAGE ONLY" IS A STAGE, NOT A ROUTE, and that shaped this file. This product is one
 * document: `body[data-stage]` moves through pick -> configure -> results and the engine's
 * `setStage()` is its single owner. There is no navigation event to hang cleanup off, so the stage
 * attribute IS the navigation, read through the existing `useStage()` (a read-only
 * MutationObserver). When it leaves 'pick', this component unmounts its children and calls
 * `audio.teardown()`. That is the brief's "stop and unload all audio on navigation away", expressed
 * in the only terms this app has.
 *
 * WHY NOT A SECOND COPY OF THE STAGE IN REACT STATE: App.tsx already refuses to keep one, for a
 * documented reason -- two owners of one fact, last writer wins, and which one that is depends on
 * render timing. This reads the owner's published value and introduces no owner.
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useStage } from '../lib/stage'
import { readFlags, storeAudioChoice, type IntroFlags } from './flags'
import * as audio from './audio'
import { IntroGate } from './IntroGate'
import { Pipeline } from './Pipeline'
import { ThermalField } from './ThermalField'
import { playHeroEntrance, type HeroHandle, startRingLoops } from './timeline'
import { playLaunch, type LaunchHandle } from './launch'

/** Marks the document while the intro is running, so CSS can scope to it without React knowing. */
const BODY_ATTR = 'data-aa-intro'

/* 🔴 `FADE_MS` WAS DELETED HERE. It was 640 ms, "slightly longer than intro.css's 600 ms opacity
   transition, so the fade completes before the element is removed", and it was the gate's whole exit
   timing. The launch sequence owns that now and its duration is derived from the measured voiceover,
   so a constant here would be a second answer to a question that has one. `launch.ts:BEATS` is where
   the timing lives. */

export function IntroLayer() {
  const stage = useStage()
  /** The ambient ring motion when it is NOT owned by an entrance: see the return-visit effect below. */
  const ring = useRef<{ kill: () => void } | null>(null)
  /** Has this reader been off the landing stage at least once in this session? */
  const hasLeft = useRef(false)

  /* READ ONCE. A ref, not state: these cannot change during a visit, and re-resolving them on every
     render is how two components end up disagreeing about whether audio is allowed. */
  const flagsRef = useRef<IntroFlags | null>(null)
  if (flagsRef.current === null) flagsRef.current = readFlags()
  const flags = flagsRef.current

  const [gateOpen, setGateOpen] = useState(flags.gate)
  /* Whether the intro has been released to run. With no gate (narrow screen, reduced motion, a
     second visit in this tab) it is released immediately, because there is no click to wait for. */
  const [released, setReleased] = useState(!flags.gate)
  const [muted, setMuted] = useState(!flags.audio)
  /** The launch sequence, so it can be killed on the way out. */
  const launch = useRef<LaunchHandle | null>(null)
  /** The hero timeline, so it can be killed on the way out. */
  const hero = useRef<HeroHandle | null>(null)
  /** The slot App.tsx renders for the diagram. Read after commit, not during render: on the first
   *  pass React has not put App's own output in the document yet, so getElementById returns null. */
  const [slot, setSlot] = useState<HTMLElement | null>(null)

  /* THE LANDING STAGE, AND NOTHING ELSE.
     `null` means the engine has not written the attribute yet, which happens on first paint before
     `setStage('pick')` runs. Treated as the landing stage so the gate is not skipped for one frame
     and then flashed in. */
  const onLanding = stage === 'pick' || stage === null

  /** Released by the gate, or immediately when there is no gate. */
  const release = useCallback(
    (withAudio: boolean) => {
      setReleased(true)
      setMuted(!withAudio)

      /**
       * 🔴 THE LAUNCH SEQUENCE OWNS THE NEXT FEW SECONDS, AND IT REPLACED A 640 ms TIMER.
       *
       * This used to be: start the audio, start the hero entrance, and unmount the gate after
       * FADE_MS. The user's brief made it a timed cinematic instead: "Clicking Initialize Arbiter
       * starts a timed cinematic sequence. The screen does not change immediately, it holds on the
       * globe while a voiceover plays, then transitions."
       *
       * So the gate is unmounted by the sequence's own completion rather than by a constant here, and
       * `launch.ts` is the only thing that knows how long that is. Three things follow:
       *   - the HERO ENTRANCE starts when the sequence FINISHES, not on the click, because it animates
       *     the masthead behind the splash and would otherwise play out entirely unseen;
       *   - the sequence is told `audio` and `reduced` and decides its own shape from them;
       *   - `onFinish` is the ONE path out, whether the sequence ran to completion, was escaped with a
       *     key or a click, or was cut short by its own watchdog.
       */
      const finish = () => {
        setGateOpen(false)
        /* 🔴 `withAudio` IS PASSED AS FALSE DELIBERATELY -- see the note in timeline.ts. The narration
           has already finished by the time this runs, so there are no beats left to sync against and
           the silent map is the truthful one. */
        if (flags.gate) hero.current = playHeroEntrance(false, 'full')
      }

      /* 🔴 THE KILL SWITCH. "One flag that disables the entire audio+cinematic sequence and makes the
         button navigate instantly." No timeline, no audio, no wait. */
      if (!flags.cinematic) {
        finish()
        return
      }

      launch.current = playLaunch({
        audio: withAudio,
        reduced: flags.reduced,
        gate: document.querySelector<HTMLElement>('.aa-gate.aa-splash'),
        onFinish: finish,
      })
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  /* Find the diagram's slot once the tree is in the document. One extra render, and it means the
     diagram is mounted and measurable BEFORE Enter is pressed -- which the entrance timeline needs,
     because it scales the nodes in as part of itself. */
  useEffect(() => {
    setSlot(document.getElementById('aa-ringslot'))
  }, [])

  /**
   * NO GATE: RELEASE BEFORE THE FIRST PAINT, AND RUN THE HEADLINE REVEAL.
   *
   * 🔴 useLayoutEffect, NOT useEffect, and the difference is the whole point. A `useEffect` runs
   * AFTER the browser has painted, so setting `opacity: 0` there means the reader sees the finished
   * page for a frame and then watches it rebuild -- a glitch, not an entrance. A layout effect runs
   * synchronously after the DOM is in place and before paint, so the from-state is never visible.
   *
   * This is the path a phone takes (the gate is skipped under 768px) and the path a return visit in
   * the same tab takes. It plays the 'headline' variant: the brief's "Keep only the hero text
   * reveal", and the only part that can be set up before paint without waiting for the portalled
   * diagram to mount.
   */
  useLayoutEffect(() => {
    if (flags.gate || !flags.motion) return
    /* NO GATE MEANS NO SEQUENCE: there is nothing to hold on and nothing to transition out of. This is
       the phone, the reduced-motion reader and the second visit in a tab. The headline reveal runs and
       that is the whole intro. */
    hero.current = playHeroEntrance(false, 'headline')
    setReleased(true)
    setMuted(!flags.audio)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* MARK THE DOCUMENT while the intro owns the landing stage, and unmark it on the way out. Every
     rule in intro.css hangs off this attribute, so a page that never mounts this component, or has
     left the landing stage, cannot pick up a single intro style.

     🔴 useLayoutEffect, NOT useEffect, AND ON THE LIGHT THEME THE DIFFERENCE IS A WHITE FLASH.
     A plain effect runs AFTER the browser has painted, so the first painted frame of the gate had no
     `data-aa-intro` on the body. `intro.css` paints the gate `background: var(--page) !important`,
     and `--page` is #fafafa in the light palette against #09090b in the dark one; the rule that pins
     the splash to the dark floor is the one hanging off this attribute. So a light-theme reader got a
     full-viewport WHITE splash, in the wrong layout, until the attribute landed.
     MEASURED on the user's own recording of the deployed site: white and centred from t = 1.600 s to
     t = 2.200 s, flipping to the dark floor and the left-aligned layout by t = 2.425 s. Measured
     again in the harness: 589 ms of gate in the wrong palette even after the gate itself was moved
     into the first commit.
     A layout effect runs synchronously after the DOM is in place and BEFORE paint, so there is no
     frame in which the gate exists unmarked. Same reasoning as the entrance's own layout effect
     directly above; this one was simply written the other way. */
  useLayoutEffect(() => {
    if (!flags.motion) return
    const b = document.body
    if (onLanding) b.setAttribute(BODY_ATTR, released ? 'running' : 'gate')
    else b.removeAttribute(BODY_ATTR)
    return () => b.removeAttribute(BODY_ATTR)
  }, [flags.motion, onLanding, released])

  /* LEAVING THE LANDING STAGE STOPS THE SOUND. Configure is a technical screen and the brief is
     explicit that it stays silent. */
  useEffect(() => {
    if (onLanding) return
    /* 🔴 THE SEQUENCE DIES WITH THE STAGE. "Stop and unload all audio on navigation away. Kill the
       timeline and any RAF loops." `kill()` does not call onFinish, so leaving mid-sequence does not
       also try to run the hero entrance on a masthead that is no longer on screen. */
    launch.current?.kill()
    launch.current = null
    audio.teardown()
    /* The entrance belongs to the landing stage. Configure can be reached before the timeline has
       finished -- the CTA is live throughout -- and a tween still running against a masthead that
       has scrolled out of the tab's panel is work nobody sees, holding a SplitText's wrappers in the
       document while it does it. */
    hero.current?.kill()
    hero.current = null
  }, [onLanding])

  /**
   * 🔴 THE REVOLVING DOT COMES BACK. The user: "the small circle that revolves around the loop only
   * appears on the first page load. If a user navigates away (e.g., clicking Configure this plant)
   * and then returns, the circle disappears entirely."
   *
   * They were right, and there were three separate reasons it could never return:
   *   1. this component renders `null` off the landing stage, so `Pipeline` UNMOUNTS and its SVG
   *      goes with it. Coming back mounts a brand new one whose pulse is parked at the path's origin
   *      with no tween attached to it;
   *   2. leaving calls `hero.current.kill()`, which calls the entrance's `stopLoops()`, which kills
   *      the tweens AND deletes `body[data-aa-ring]` -- the attribute intro.css gates the dot's
   *      `visibility` on, so even a surviving tween would have been invisible;
   *   3. the only thing that ever started the loops was `playHeroEntrance` in a `useLayoutEffect`
   *      with an EMPTY dependency array. That runs once per mount of this component, and this
   *      component never unmounts: it returns null. So it never ran again.
   *
   * So the return is handled explicitly. `startRingLoops()` is the entrance's own loop builder with
   * the entrance taken off it, and it refuses when `body[data-aa-ring]` says a live set already
   * exists, so the first load is untouched and there is no path on which two sets run at once.
   * `hasLeft` is what keeps this out of the first load: at mount the reader has not been anywhere,
   * and the entrance is the thing that should start the motion then.
   */
  useEffect(() => {
    if (!flags.motion) return
    if (!onLanding) {
      hasLeft.current = true
      ring.current?.kill()
      ring.current = null
      return
    }
    if (!hasLeft.current || !slot) return
    /* No delay needed: an effect runs after React has committed the portal, so the new `Pipeline`'s
       `[data-aa-pulse]` is already in the document by the time this line executes. */
    ring.current = startRingLoops()
    return () => {
      ring.current?.kill()
      ring.current = null
    }
  }, [flags.motion, onLanding, slot])

  /* AND SO DOES LEAVING THE PAGE. Unmount covers the React side; pagehide covers a real navigation
     or a tab close, which unmount does not reliably reach. `pagehide` rather than `unload` because
     `unload` is ignored in some browsers and blocks the back/forward cache in the rest. */
  useEffect(() => {
    const stop = () => {
      launch.current?.kill()
      launch.current = null
      audio.teardown()
    }
    window.addEventListener('pagehide', stop)
    return () => {
      window.removeEventListener('pagehide', stop)
      launch.current?.kill()
      launch.current = null
      hero.current?.kill()
      hero.current = null
      ring.current?.kill()
      ring.current = null
      audio.teardown()
    }
  }, [])

  /* Reflect the live mute state onto whatever is playing, and remember the choice. */
  useEffect(() => {
    audio.setMuted(muted)
  }, [muted])

  /* MOTION OFF MEANS NOTHING FROM THIS FOLDER EXISTS. Not hidden, not transparent: absent. That is
     what makes the flag safe as a demo switch and as the verification bypass. */
  if (!flags.motion) return null
  if (!onLanding) return null

  return (
    <>
      {/* THE HEAT FIELD, portalled to <body> rather than rendered here.
          It has to paint BELOW #app's content and above body's own background, and neither is
          possible from inside #app: a positioned z-index:0 element paints above static siblings, and
          z-index:-1 would go behind body's opaque background. As a direct child of body at z-index 0
          with #app raised to 1 (intro.css section 6), the order is exactly right.
          Rendered as soon as this layer mounts, so it is already breathing behind the gate -- which
          is what the brief asks for: "Background already breathing faintly". */}
      {createPortal(<ThermalField />, document.body)}

      {/* THE DIAGRAM, portalled into the slot under the masthead. Rendered as soon as this layer
          mounts, not on Enter: the gate is opaque over it, and the entrance timeline has to be able
          to find the nodes when it is built. Its own CSS hides it under 768px. */}
      {slot && createPortal(<Pipeline />, slot)}

      {gateOpen && <IntroGate flags={flags} onEnter={release} />}

      {/* THE PERSISTENT TOGGLE, in a corner, only once the gate is gone.
          Bottom LEFT deliberately: App.tsx pins the theme toggle to `right-4 top-4`, and the
          engine's own controls sit along the top, so the opposite corner is the one piece of chrome
          nothing else claims.
          It is not rendered at all when audio was never possible for this load -- a mute button on a
          page that has no sound to mute is a control that lies about what the page does. */}
      {!gateOpen && released && flags.audio && (
        <button
          type="button"
          className="aa-mutebtn"
          /* 🔴 THE NAME STATES THE STATE, BECAUSE aria-pressed ALREADY STATES THE STATE.
             This carried `aria-pressed={muted}` alongside an ACTION label ("Turn the introduction
             sound on"), which encodes the same fact with the opposite polarity: at muted === true a
             screen reader announced "Turn the introduction sound on, toggle button, pressed", i.e. a
             pressed control whose name claims sound is on. Both icons are aria-hidden and there is no
             visible text, so nothing arbitrated. One convention, not two. */
          aria-pressed={muted}
          aria-label={muted ? 'Introduction sound: off' : 'Introduction sound: on'}
          onClick={() => {
            const next = !muted
            setMuted(next)
            storeAudioChoice(!next)
          }}
        >
          {muted ? (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M11 5 6 9H3v6h3l5 4z" />
              <path d="m16 9 5 6M21 9l-5 6" />
            </svg>
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M11 5 6 9H3v6h3l5 4z" />
              <path d="M15.5 8.5a5 5 0 0 1 0 7" />
            </svg>
          )}
        </button>
      )}
    </>
  )
}
