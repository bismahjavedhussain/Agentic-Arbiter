/**
 * THE HERO ENTRANCE. One GSAP timeline, fired by the Enter click, sharing its clock with the audio.
 *
 * WHAT THE BRIEF ASKS FOR, AND WHERE EACH PART IS:
 *   * headline revealed behind a mask, ~80 ms stagger, ease power3.out  -> `headline` below
 *   * subhead and CTA fade and rise after, offset ~200 ms               -> PROSE_OFFSET, `powered`
 *   * one timeline, under 1.6 s on its own, extended only to match the
 *     voiceover when audio is on                                       -> BEATS, two maps
 *   * every animation wrapped via gsap.matchMedia()                     -> `mm.add(...)`
 *   * animate only transform and opacity                               -> see the note below
 *   * kill everything on unmount                                       -> the returned handle
 *
 * 🔴 A MASK REVEAL WITHOUT ANIMATING clip-path. The brief asks for a mask reveal AND for only
 * transform and opacity to be animated, which sounds contradictory: `clip-path` is not on the
 * compositor's fast path and animating it costs a paint per frame. The way both hold at once is the
 * technique the effect is actually named for -- an `overflow: hidden` wrapper around each line, with
 * the line itself moved by `yPercent`. The wrapper clips; the transform is all that animates.
 * SplitText's `mask: 'lines'` option builds those wrappers at runtime, so no markup changes on disk.
 *
 * 🔴 THE PROSE IS NOT SPLIT, AND THAT IS DELIBERATE. SplitText rewrites its target's innerHTML into
 * per-line elements, and `.aa-mast-prose` contains an `<Info>` popover -- a React component with its
 * own state and a real button. React holds references to the DOM nodes it created; having SplitText
 * move them and then re-splitting or reverting under a React re-render is a genuine way to crash a
 * subtree. The paragraphs therefore fade and rise WHOLE, with the same 80 ms stagger, which is what
 * the brief describes for them anyway ("subhead and CTA fade+rise"). The headline has no interactive
 * children, so it is the one thing split.
 *
 * 🔴 NOTHING HERE SETS AN INITIAL STATE IN CSS. Every "from" state is applied by GSAP at the moment
 * the timeline is built, and only inside the matchMedia block. If it were in a stylesheet, then with
 * reduced motion on, or the motion kill switch off, the page would render invisible -- a hidden page
 * rather than a finished one. The gate is still opaque over the hero when these values are set, so
 * there is no flash either way.
 */
import { gsap } from 'gsap'
import { SplitText } from 'gsap/SplitText'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { LOOP_PATH, NODE_ROW_Y, NODE_XS, STAGES } from './Pipeline'

gsap.registerPlugin(SplitText, MotionPathPlugin, ScrollTrigger)

/** What the timeline animates. Every one is a `data-aa-hero` attribute added to markup that already
 *  existed, because the elements otherwise carry only Tailwind utility classes and matching on those
 *  couples this file to someone else's spacing decisions. */
const SEL = {
  eyebrow: '[data-aa-hero="eyebrow"]',
  headline: '[data-aa-hero="headline"]',
  /* 🔴 `> ul > li`, NOT `> p`, AND THIS SELECTOR BROKE ONCE.
     The four headline claims became a bulleted LIST on 2026-08-29 (the user: "show some bullet points
     to show these are different points"), which changed the direct children of `[data-aa-hero="prose"]`
     from four <p> to one <ul>. This selector still said `> p`, so it matched NOTHING and the four lines
     silently dropped out of the hero reveal: they simply appeared, with no stagger, and nothing threw.
     What caught it was `verify_intro.py`'s check COUNT falling by four, not any failing assertion,
     which is why that file now also asserts the selector matched something. */
  prose: '[data-aa-hero="prose"] > ul > li',
  status: '[data-aa-hero="status"]',
  cta: '[data-aa-hero="cta"]',
  ring: '[data-aa-hero="ring"]',
  nodes: '.aa-ring-node',
  pulse: '[data-aa-pulse]',
  /** Already a stable class in App.tsx: the "Powered by" label and the FortyGuard mark. */
  brand: '.aa-banner-brand',
} as const

/**
 * THE BEAT MAP, in seconds from the Enter click.
 *
 * Two of them, because the brief is explicit that the visuals must not wait on audio: "If audio is
 * muted, the same timeline runs on its own timing." So there is no branching inside the timeline and
 * no audio event listened to anywhere. The same tweens are laid out against different positions, and
 * which map is used is decided once, up front, from a boolean.
 *
 * SILENT totals 1.52 s, inside the 1.6 s the brief allows, and the arithmetic is worth writing out
 * because the first version of these numbers came to 1.68 s and I would have reported 1.6 from the
 * intent rather than the sum:
 *
 *     eyebrow    0.00 + 0.50                      = 0.50
 *     headline   0.12 + 0.90                      = 1.02
 *     prose      0.46 + 0.20 offset + 0.62 + 0.24 = 1.52   (0.08 stagger x 3 gaps, 4 paragraphs)
 *     powered    0.80 + 0.55 + 0.16               = 1.51   (0.08 stagger x 2 gaps, 3 targets)
 *
 * It is also PUBLISHED rather than trusted: the built timeline's real duration goes onto
 * `body[data-aa-hero-ms]`, so the claim is measured from GSAP rather than from this comment.
 * AUDIO stretches to the voiceover's three sentences. `audio.play()` starts the swell at 0 and the
 * voice 700 ms later, so "Agentic Arbiter" lands at ~0.7 s, "Cooling decisions, hour by hour" at
 * ~1.9 s and "Powered by FortyGuard" at ~3.4 s. Those are the placeholder's timings; step 6 tunes
 * them against the real recording, and this is the only place they live.
 */
/** ~80 ms, as briefed. */
const STAGGER = 0.08
/** The "offset ~200ms" between the prose starting and the line above it finishing. */
const PROSE_OFFSET = 0.2

/**
 * THE VOICEOVER, MEASURED.
 *
 * `durationS` is read from the shipped file's own MPEG frame headers: 179 frames of 1152 samples at
 * 44.1 kHz CBR 128 kbps, which is 4.676 s. That number is a measurement, not an estimate.
 *
 * ⚠ THE SENTENCE POSITIONS ARE ESTIMATED, AND THIS IS THE ONE PLACE IN THIS FILE THAT IS NOT
 * MEASURED. Finding them properly means decoding the MP3 to a waveform and looking for the gaps, and
 * there is no decoder available here (no ffmpeg, and the file is CBR so frame SIZES carry no envelope
 * either). So they are apportioned by syllable across the measured total:
 *
 *     "Agentic Arbiter."                 6 syllables
 *     "Cooling decisions, hour by hour." 8
 *     "Powered by FortyGuard."           6
 *     two inter-sentence pauses at ~0.22 s
 *     -> (4.676 - 0.44) / 20 = 0.212 s per syllable
 *
 * which puts the first sentence ending at 1.27 s, the second starting at 1.49 s and the third at
 * 3.41 s, all relative to the voiceover's own start.
 *
 * If a beat lands wrong to the ear, these three numbers are the only thing to change: every visual
 * position below is derived from them, so moving one moves its beat and nothing else.
 */
const VOICE = {
  durationS: 4.676,
  /** Seconds from the voiceover's start. */
  nameEndsS: 1.27,
  decisionsStartsS: 1.49,
  poweredStartsS: 3.41,
} as const

/**
 * 🔴 THE AUDIO BEAT MAP BELOW IS NOW UNREACHABLE, AND SAYING SO IS THE POINT OF THIS NOTE.
 *
 * The voiceover used to play on ARRIVAL, underneath this hero entrance, which is why there are two
 * beat maps and why one of them is laid against the narration's three sentences. On 2026-08-29 the
 * user moved the voiceover to the CLICK of "Initialize Arbiter" and made it the opening of a timed
 * cinematic sequence (`intro/launch.ts`). By the time this entrance runs, the gate has swept away and
 * the voiceover has finished, so there is nothing left to sync to and `IntroLayer` always asks for the
 * SILENT map.
 *
 * It is kept rather than deleted because the measured numbers in `VOICE` above are still the truth
 * about the recording and were expensive to establish, and because moving the narration back under
 * the hero is one boolean. ⚠ But do not read the audio map as describing what ships: it does not.
 *
 * `LEAD_S` used to come from `audio.ts:VOICE_LEAD_MS`, which no longer exists: nothing leads the voice
 * any more, because the voice and its bed start together at t = 0 of the launch timeline. The value is
 * kept locally so the arithmetic in the comments above still adds up.
 */
const LEAD_S = 0.7

/** How long the headline's mask reveal takes, so its START can be derived from where it must END. */
const HEADLINE_DUR = 0.9

/**
 * THE BEAT MAP. Two of them, because the brief is explicit that the visuals must not wait on audio:
 * "If audio is muted, the same timeline runs on its own timing." No audio event is listened to
 * anywhere; the same tweens are laid against different positions and which map is used is decided
 * once, from a boolean.
 *
 * SILENT totals 1.52 s, inside the 1.6 s the brief allows. The arithmetic is worth writing out
 * because the first version of these numbers came to 1.68 s and I would have reported 1.6 from the
 * intent rather than the sum:
 *
 *     eyebrow    0.00 + 0.50                      = 0.50
 *     headline   0.12 + 0.90                      = 1.02
 *     prose      0.46 + 0.20 offset + 0.62 + 0.24 = 1.52   (0.08 stagger x 3 gaps, 4 paragraphs)
 *     powered    0.80 + 0.55 + 0.16               = 1.51   (0.08 stagger x 2 gaps, 3 targets)
 *
 * It is also PUBLISHED rather than trusted: the built timeline's real duration goes onto
 * `body[data-aa-hero-ms]`, so the claim is measured from GSAP rather than from this comment.
 *
 * AUDIO is DERIVED from VOICE above, which is the whole point of writing it this way -- the brief's
 * sync map becomes an expression rather than a guess:
 *     "Agentic Arbiter"                 -> the headline mask reveal COMPLETES as the name ends
 *     "Cooling decisions, hour by hour" -> the loop's nodes scale in, the prose rises
 *     "Powered by FortyGuard"           -> the mark, the status lines and the CTA come up
 * It totals about 4.82 s against 5.38 s of audio, so the last visual lands just inside the last
 * words rather than after them.
 */
const BEATS = {
  silent: { eyebrow: 0, headline: 0.12, prose: 0.46, ring: 0.5, powered: 0.8 },
  audio: {
    eyebrow: 0.4,
    /* Positioned by where it must FINISH, not where it starts. */
    headline: LEAD_S + VOICE.nameEndsS - HEADLINE_DUR,
    /* The prose is placed at `beats.prose + PROSE_OFFSET`, so the offset is subtracted back out
       here to make the paragraphs land exactly on the second sentence. */
    prose: LEAD_S + VOICE.decisionsStartsS - PROSE_OFFSET,
    ring: LEAD_S + VOICE.decisionsStartsS,
    powered: LEAD_S + VOICE.poweredStartsS,
  },
} as const

/**
 * THE PULSE. The brief: "slow infinite loop (~4s per cycle, ~2s pause)".
 *
 * Driven by MotionPathPlugin rather than by `stroke-dashoffset`, which the brief offers as the
 * alternative. Moving one small dot along a path is a TRANSFORM, which is the performance rule this
 * work is held to; animating dashoffset repaints the whole path every frame to show the same thing.
 */
const PULSE_CYCLE = 4
const PULSE_PAUSE = 2

/**
 * THE FLOAT. The brief: "3-5px vertical drift, 6-8s period, offset phases so they don't move in
 * unison." Three different things are offset -- distance, period AND start delay -- because two
 * nodes with the same period drift back into step even if they start apart.
 */
const FLOAT_PX = [3.5, 4.5, 3, 5, 4]
const FLOAT_PERIOD = [7.2, 6.4, 7.8, 6.8, 7.5]

/**
 * Where along the whole loop the forward row ends. The path runs left to right across the five
 * nodes, then sweeps back underneath, and the forward leg is about 47 % of the total length. Used to
 * work out when the pulse passes each node, so a label's timing is DERIVED from the geometry rather
 * than typed next to it -- moving a node in Pipeline.tsx cannot silently desynchronise its label.
 */
const FORWARD_FRACTION = 0.47

/**
 * 🔴 HOW FAR A DATA LABEL MAY BE DIMMED, and it is a measured number rather than a taste.
 *
 * The first version faded these to 0.45 as the pulse moved on. MEASURED, compositing the token over
 * the page and applying the WCAG formula: that is 2.38:1 in dark and 2.11:1 in light, against a
 * 4.5:1 floor for small text. The label would have spent most of every 6-second cycle illegible --
 * the exact fault already fixed once on the gate's footnote, arrived at from the opposite direction.
 *
 *     alpha 1.00 -> 7.76:1 dark / 7.41:1 light
 *     alpha 0.85 -> 5.82:1 / 5.05:1     <- the floor, both palettes clear
 *     alpha 0.80 -> 5.26:1 / 4.47:1     <- light already fails
 *
 * So the label moves between 0.85 and 1, which is legal but far too subtle to read as an arrival.
 * The VISIBLE signal is moved to the node's halo instead: a decorative circle carries no text and
 * therefore no contrast obligation, so it can swing from 0.5 to full and actually be seen. The
 * shapes still light up as the pulse passes; nothing a reader has to read gets dimmed to do it.
 */
const NOTE_FLOOR = 0.85


/**
 * 🔴 THE WATCHDOG, and it exists because of a measured failure rather than a hypothetical one.
 *
 * Every from-state here is written by GSAP, including `opacity: 0`. That is the right way round --
 * putting them in a stylesheet would leave the page invisible whenever the animation is disabled --
 * but it does mean the page's visibility depends on a timeline completing. If the ticker never
 * advances, the hero stays blank forever.
 *
 * That is not theoretical. MEASURED in this project's own browser harness: under Chrome's
 * `--virtual-time-budget` mode the timeline advances FAR slower than the clock it is being measured
 * against -- 5 s of virtual time moved the eyebrow's opacity to 0.9375 and left the call to action
 * 0.07px into a 14px rise. rAF fires, nothing throws, and GSAP writes its from-states correctly
 * (`transform: translate(0%, 115%)` inside an `overflow: clip` mask); it is the progression that
 * lags.
 * ⚠ An earlier version of this note said the timeline "never advances", which was wrong: it does,
 * just not at wall-clock speed. Corrected because the distinction matters -- a stalled ticker and a
 * slow one need the same insurance but describe different bugs.
 * A real browser is fine, but "a real browser is fine" is exactly the assumption worth insuring
 * against: a tab backgrounded mid-entrance, a throttled ticker, or GSAP failing to initialise all
 * land in the same place.
 *
 * So: a plain setTimeout, deliberately NOT rAF-based, jumps the timeline to its end if it has not
 * got there on its own. The page becomes the finished page. The brief's requirement that a reduced
 * page "must still look finished, not broken" is treated as a requirement on every failure path, not
 * just on the preference.
 */
const WATCHDOG_MARGIN = 0.7

export type HeroHandle = {
  /** Reverts every tween and every split, and clears what GSAP wrote. Safe to call twice. */
  kill: () => void
  /** For the verifier: what this run decided to do. */
  info: () => Record<string, unknown>
}

const NOOP: HeroHandle = { kill: () => {}, info: () => ({ ran: false }) }

/**
 * THE RING'S AMBIENT MOTION, BUILT IN ONE PLACE AND OWNED BY WHOEVER ASKED FOR IT.
 *
 * 🔴 THIS WAS A CLOSURE INSIDE `playHeroEntrance`, AND THAT IS WHY THE DOT ONLY EVER APPEARED ONCE.
 * The user: "the small circle that revolves around the loop only appears on the first page load. If
 * a user navigates away and then returns, the circle disappears entirely."
 * The chain: `IntroLayer` returns null off the landing stage, so `Pipeline` unmounts and its SVG goes
 * with it; leaving also calls `hero.kill()`, which calls `stopLoops()`, which kills the tweens and
 * deletes `body[data-aa-ring]` -- the attribute intro.css gates the dot's `visibility` on. Coming
 * back remounts a FRESH `Pipeline` whose pulse is parked at the path origin and hidden, and the only
 * thing that ever started the loops was a `useLayoutEffect` with an empty dependency array, which by
 * definition does not run twice. So the dot was gone and nothing could bring it back.
 * Lifting the builder out means `IntroLayer` can start the loops again on a return without replaying
 * the whole headline entrance, and there is still exactly one implementation of what they are.
 *
 * Returns the animations rather than storing them: `playHeroEntrance` has to put them in its own
 * `loops` array, which its scroll handoff pauses and its `kill()` empties, and a second owner of
 * that array is the bug the array's own comment already records.
 */
function buildRingLoops(): gsap.core.Animation[] {
  const out: gsap.core.Animation[] = []
  const pulse = document.querySelector(SEL.pulse)
  const nodes = gsap.utils.toArray(SEL.nodes) as SVGGElement[]
  if (!pulse || !nodes.length) return out

  /* THE PULSE. `repeatDelay` is the brief's "~2s pause": the dot completes the loop, waits, goes
     again. `ease: 'none'` because a light travelling a wire does not accelerate. */
  out.push(
    gsap.to(pulse, {
      /* No `align`: the dot is positioned BY the path rather than aligned to another element,
         and MotionPathPlugin's type for that option is a selector or an Element, never a boolean.
         `autoRotate: false` because a circle has no orientation to rotate. */
      motionPath: { path: LOOP_PATH, autoRotate: false },
      duration: PULSE_CYCLE,
      repeat: -1,
      repeatDelay: PULSE_PAUSE,
      ease: 'none',
      /* PLACED ON THE PATH IMMEDIATELY. A `to()` tween does not render its start state by default,
         so without this the dot keeps its authored position -- SVG (0, 0), the top-left corner --
         until the first tick. The same moment makes it visible, so a reader can catch a stray dot
         in the corner of the diagram. With it, the dot is at the path's start before it is shown. */
      immediateRender: true,
    }),
  )

  /* THE DATA LABELS, lifted as the pulse reaches each node and let back down behind it, so the
     shapes read as carrying something. Timing derived from FORWARD_FRACTION, not typed. */
  STAGES.forEach((stage, i) => {
    const note = document.querySelector('[data-aa-note="' + stage.key + '"]')
    if (!note) return
    const at = (i / (STAGES.length - 1)) * FORWARD_FRACTION * PULSE_CYCLE
    const halo = document.querySelector('[data-aa-node="' + stage.key + '"] .aa-ring-halo')
    out.push(
      gsap
        .timeline({ repeat: -1, repeatDelay: PULSE_PAUSE, delay: at })
        .to(note, { opacity: 1, duration: 0.35, ease: 'power2.out' }, 0)
        .to(note, { opacity: NOTE_FLOOR, duration: 0.9, ease: 'power2.in' }, 0.8)
        /* The node's own response, and the part that is actually visible. Opacity and scale on a
           decorative circle: no text, no contrast floor, so it can swing far enough to register. */
        /* OPACITY ONLY, NO SCALE, and dropping the scale is the fix rather than a compromise.
           A scaled halo has to be told where its centre is, and getting that wrong put it visibly
           off its own disc -- 8.62px at worst, measured. Opacity has no origin to get wrong. The
           swing is 0.5 to 1 on a 16 %-alpha fill, which is a clear change in presence and is what
           a reader actually notices; the extra 16 % of radius was never the signal. */
        .to(halo, { opacity: 1, duration: 0.35, ease: 'power2.out' }, 0)
        .to(halo, { opacity: 0.5, duration: 0.9, ease: 'power2.in' }, 0.8),
    )
  })

  /* THE FLOAT, `y` only. */
  nodes.forEach((node, i) => {
    out.push(
      gsap.to(node, {
        y: FLOAT_PX[i % FLOAT_PX.length],
        duration: FLOAT_PERIOD[i % FLOAT_PERIOD.length] / 2,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: i * 0.55,
      }),
    )
  })

  return out
}

/**
 * START THE AMBIENT MOTION ON ITS OWN, for a reader who has come BACK to the landing stage.
 *
 * The entrance is a one-off: it splits the headline, plays the reveal and hands over. A return visit
 * needs none of that and would be worse for having it, so this is the loops and nothing else.
 *
 * ⚠ IT REFUSES IF THE ENTRANCE ALREADY OWNS THEM. `body[data-aa-ring]` is the entrance's own
 * published marker, so its presence means a live set exists and a second set would double every
 * tween on the same elements. Same three refusals as the entrance otherwise: no window, under 768px
 * the brief disables the pulse outright, and reduced motion means no ambient motion at all.
 */
export function startRingLoops(): { kill: () => void } {
  const NONE = { kill: () => {} }
  if (typeof window === 'undefined') return NONE
  if (window.innerWidth < 768) return NONE
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return NONE
  } catch {
    /* no matchMedia: treat it as no preference, which is what the rest of this file does */
  }
  if (document.body.dataset.aaRing === 'running') return NONE
  const anims = buildRingLoops()
  if (!anims.length) return NONE
  document.body.dataset.aaRing = 'running'
  return {
    kill: () => {
      for (const a of anims) a.kill()
      anims.length = 0
      if (document.body.dataset.aaRing === 'running') delete document.body.dataset.aaRing
    },
  }
}

/**
 * Build and play the entrance. Returns a handle even when nothing runs, so callers never branch.
 *
 * `withAudio` selects the beat map and nothing else. It is NOT used to wait for anything.
 */
export function playHeroEntrance(
  withAudio: boolean,
  /**
   * 🔴 'headline' EXISTS BECAUSE THE MOBILE CLAUSE WAS UNIMPLEMENTED.
   *
   * The brief: "Mobile (<768px): skip the enter gate entirely, disable pipeline pulse and background
   * animation, no audio. Keep only the hero text reveal." A review traced that the entrance was
   * gated on `flags.gate`, and `gateEnabled()` returns false for any viewport under 768px -- so a
   * phone got NO gate and therefore NO entrance either. The one thing the clause says to keep was
   * the one thing missing, and the narrow-screen check in verify_intro.py only asserted the
   * negatives, so nothing caught it.
   *
   * Why a variant rather than just calling the full entrance: without a gate there is nothing opaque
   * covering the page while GSAP writes its from-states, so the reader would see the finished page
   * for a frame and then watch it rebuild itself. The headline alone can be split and set inside a
   * LAYOUT effect, which runs before paint, and it is one element that does not depend on the
   * portalled diagram having mounted yet. The prose, the status lines and the call to action stay
   * where they are.
   */
  variant: 'full' | 'headline' = 'full',
  /**
   * 🔴 SECONDS TO WAIT BEFORE THE REVEAL PLAYS, WHILE ITS FROM-STATES ARE ALREADY APPLIED. This is
   * what stops the next page showing its own text and then blanking it.
   *
   * The user: "The text exists there static for a few milli second, then disappears and triggers a
   * transition ... If it has a transition over it, it should not be visible static in the first
   * place." They were describing an ordering problem, not an animation problem. The entrance used to
   * be built at `onFinish`, AFTER the splash had finished crossfading away, so the crossfade revealed
   * a page at its resting state and the from-states then blanked what the reader had just seen.
   * GSAP's `from()` defaults to `immediateRender: true`, which means the start values are written the
   * moment the tween is CONSTRUCTED, not when it first ticks. So constructing the entrance at the
   * START of the crossfade puts every animated element at opacity 0 while the splash still covers
   * them, and `delay` holds the playback until the splash has gone. The crossfade then reveals an
   * empty page and the text arrives onto it, which is the order that was asked for.
   *
   * 0 for a caller with nothing in front of it: the no-gate path, and the kill switch.
   */
  leadS = 0,
): HeroHandle {
  if (typeof window === 'undefined') return NOOP
  if (!document.querySelector(SEL.headline)) return NOOP

  const beats = withAudio ? BEATS.audio : BEATS.silent
  let split: SplitText | null = null
  let built = false
  let total = 0
  let watchdog: number | null = null
  let watchdogFired = false
  /** The ambient loops. They outlive the entrance timeline and are killed with the handle. */
  const loops: gsap.core.Animation[] = []
  /** The wall-clock timer that starts them. */
  let loopStart: number | null = null
  /** The scroll handoff. Tracked separately: a ScrollTrigger is not an animation and needs its own
   *  kill(), and leaving one behind on a page whose elements have gone is a listener on every
   *  scroll event for the rest of the session. */
  const triggers: ScrollTrigger[] = []
  /**
   * 🔴 THE HANDOFF TWEENS LIVE IN THEIR OWN ARRAY, AND THIS WAS A REAL BUG.
   *
   * They were pushed into `loops` alongside the pulse and the float. `loops` is exactly the set the
   * handoff's own onUpdate PAUSES once the diagram is faded out -- so past 90 % of the fade the two
   * scroll tweens paused THEMSELVES, froze at whatever value they held, and could never reverse
   * because a paused tween gets no further updates.
   *
   * MEASURED, on a real clock: fading correctly to 0 at scrollY 360, then back UP to 0.060 at 480,
   * and stuck at 0 after scrolling all the way back to the top -- a reader who scrolled down and up
   * again was left on a landing page with no background at all.
   *
   * Two arrays, one rule: `loops` is ambient motion nobody is looking at once the hero has gone, and
   * is pausable. `handoff` is driven by the reader's own scroll and must never be paused.
   */
  const handoff: gsap.core.Animation[] = []
  let handoffProgress = 0

  /* gsap.matchMedia is the brief's requirement and it is doing real work here, not decoration:
     everything inside is added ONLY when the query matches, and `mm.revert()` undoes all of it in
     one call, including restoring the values the `from()` tweens started from. With reduced motion
     the block never runs, so the page is simply itself. */
  const mm = gsap.matchMedia()

  mm.add('(prefers-reduced-motion: no-preference)', () => {
    const headline = document.querySelector<HTMLElement>(SEL.headline)
    if (!headline) return

    /* THE MASK WRAPPERS, built at runtime and removed on revert. `lines` rather than chars: the
       wordmark is one line and it should arrive as one object, not assemble itself letter by letter,
       which reads as a gimmick on a two-word title. */
    split = new SplitText(headline, { type: 'lines', mask: 'lines', linesClass: 'aa-hero-line' })

    const tl = gsap.timeline({
      /* The lead-in. The tweens below are `from()`, so their start values are written NOW and the
         delay only postpones playback. See the parameter's own note. */
      delay: leadS,
      defaults: { ease: 'power3.out' },
      /* Put the headline's DOM back the moment the reveal is over, rather than leaving SplitText's
         wrappers in the document for the rest of the visit. Anything reading the page afterwards --
         a verifier, a screen reader, a copy-paste -- sees the original markup. */
      onComplete: () => {
        if (split) {
          split.revert()
          split = null
        }
      },
    })

    /* 1. The eyebrow. A short fade and rise; it is a label, not an event. */
    if (variant === 'full') {
      tl.from(SEL.eyebrow, { opacity: 0, y: 10, duration: 0.5 }, beats.eyebrow)
    }

    /* 2. THE HEADLINE, rising out from behind its mask. `yPercent` so the distance is the line's own
       height and cannot be wrong at a different clamp() size. */
    tl.from(
      split.lines,
      { yPercent: 115, duration: 0.9, stagger: STAGGER },
      beats.headline,
    )

    /* 3. The prose, whole paragraphs, offset after the headline. Everything from here on is the
       'full' variant only: see the note on the `variant` parameter. */
    if (variant !== 'full') {
      built = true
      total = tl.duration()
      document.body.dataset.aaHeroMs = String(Math.round(total * 1000))
      return () => {
        if (split) {
          split.revert()
          split = null
        }
        tl.kill()
        delete document.body.dataset.aaHeroMs
      }
    }

    tl.from(
      SEL.prose,
      { opacity: 0, y: 16, duration: 0.62, stagger: STAGGER },
      beats.prose + PROSE_OFFSET,
    )

    /* 4. "Powered by FortyGuard": the status lines, the mark and the call to action, together.
       This is the beat the third sentence of the voiceover lands on. Targets are filtered for
       existence because the CTA only appears once a site is selected and the brand group only once
       the banner has rendered; a missing selector would otherwise make GSAP warn about an empty
       tween. */
    const rise = [SEL.status, SEL.brand].filter((sel) => document.querySelector(sel))
    if (rise.length) {
      tl.from(rise, { opacity: 0, y: 14, duration: 0.55, stagger: STAGGER }, beats.powered)
    }

    /* 🔴 THE CALL TO ACTION FADES BUT DOES NOT RISE, and that is a fix rather than a shortcut.
       SelectedBar's button already owns its own transform: it carries Tailwind's
       `transition-transform duration-150` and `hover:-translate-y-0.5` for its hover lift. Tweening
       `y` on it means every frame GSAP writes is then CSS-transitioned AGAIN, and the two never
       quite agree -- MEASURED as `matrix(1, 0, 0, 1, 0, 0.0684301)` still settling seconds after the
       timeline had ended, on an element that should have been at rest.
       Suppressing the button's transition for the duration would work and would also mean this file
       reaching in to disable another component's interaction styling. Fading is enough: it arrives on
       the same beat, and the hover lift stays entirely the button's business. */
    if (document.querySelector(SEL.cta)) {
      tl.from(SEL.cta, { opacity: 0, duration: 0.55 }, beats.powered + STAGGER * 2)
    }

    /* 5. THE LOOP'S FIVE STAGES, scaled in sequentially AS PART OF THIS TIMELINE, which is what the
       brief asks for: they arrive on the beat that carries "Cooling decisions, hour by hour".
       `scale` and `opacity` only. intro.css gives each node `transform-box: fill-box` and
       `transform-origin: center`; without those an SVG scale is measured from the viewBox origin and
       the nodes fly in from the corner instead of appearing where they belong. */
    const nodes = gsap.utils.toArray(SEL.nodes) as SVGGElement[]
    if (nodes.length) {
      tl.from(
        ['#aa-ring-track', '.aa-ring-return', '.aa-ring-arrow'],
        { opacity: 0, duration: 0.6 },
        beats.ring - 0.1,
      )
      /* 🔴 svgOrigin, NAMED IN USER UNITS, ONE TWEEN PER NODE.
         Scaling an SVG element needs its origin stated, and two weaker attempts came first:
           * CSS `transform-origin: center` -- inert. GSAP bakes the origin into the matrix it
             writes and sets `transform-origin: 0px 0px` inline while doing it. MEASURED: the CSS
             rule computed to `0px 0px`.
           * `transformOrigin: 'center'` in the tween -- did not fix it either. MEASURED: the worst
             halo-to-disc offset stayed at 8.62px across 995 samples, and it was worst at the node
             NEAREST the origin, so the displacement was not the simple cx*(scale-1) I had assumed.
         `svgOrigin` takes an absolute point in the SVG's own user coordinates and leaves no room for
         interpretation. Each node's centre is already known from the geometry Pipeline.tsx exports,
         so it is stated rather than derived from a bounding box that includes the label text --
         which is why 'center' was wrong in the first place: the group's box spans the note beneath
         it, so its centre is not the disc's centre.
         The cost is a loop instead of one staggered tween, which is worth paying to be exact. */
      nodes.forEach((node, i) => {
        tl.from(
          node,
          {
            opacity: 0,
            scale: 0.72,
            svgOrigin: NODE_XS[i] + ' ' + NODE_ROW_Y,
            duration: 0.5,
            ease: 'back.out(1.7)',
          },
          beats.ring + i * STAGGER,
        )
      })
    }

    built = true
    total = tl.duration()

    /* PUBLISH THE DURATION GSAP ACTUALLY BUILT, so "under 1.6 s on its own" is a measurement rather
       than an intention. This is the same kind of self-description as `data-aa-intro`: the intro
       states what it is doing, on the document, where anything can read it. */
    document.body.dataset.aaHeroMs = String(Math.round(total * 1000))

    /* See WATCHDOG_MARGIN. `progress(1)` completes the timeline synchronously and fires its
       onComplete, so the split is reverted by the same path a normal finish uses -- one way for the
       page to reach its final state, not two. */
    watchdog = window.setTimeout(() => {
      if (tl.progress() < 1) {
        watchdogFired = true
        tl.progress(1, false)
      }
      if (split) {
        split.revert()
        split = null
      }
    }, (total + WATCHDOG_MARGIN) * 1000)

    /* 🔴 A setTimeout, NOT gsap.delayedCall, AND THE DIFFERENCE IS NOT COSMETIC.
       `gsap.delayedCall` is scheduled on GSAP's own ticker, so the DECISION to start the ambient
       motion inherited whatever was happening to the animation clock. MEASURED: under the browser
       harness the loops had still not started 6.2 s in, because GSAP's clock had not reached 2.5 s.
       The same would be true of a reader whose tab was backgrounded during the entrance -- they
       would return to a diagram that had simply never come alive.
       When to start is a wall-clock question. setTimeout answers it. What the loops then DO is
       GSAP's business, and lagging there only makes the motion slow rather than absent.
       It is also why the entrance's onComplete is not used: a watchdog-completed entrance must still
       get its loops. */
    loopStart = window.setTimeout(startLoops, (beats.ring + 0.6) * 1000)

    /* matchMedia's own cleanup, which `mm.revert()` also triggers. Reverting the split here as well
       as in onComplete is deliberate: a kill mid-flight must not leave the wrappers behind. */
    return () => {
      if (watchdog !== null) {
        window.clearTimeout(watchdog)
        watchdog = null
      }
      stopLoops()
      if (split) {
        split.revert()
        split = null
      }
      tl.kill()
      delete document.body.dataset.aaHeroMs
    }
  })

  /**
   * THE TWO INFINITE LOOPS: the pulse travelling the path, and the nodes' float.
   *
   * Deliberately NOT on the entrance timeline. That one finishes and is reverted; these run for as
   * long as the reader is on the landing stage.
   *
   * Skipped entirely under 768px, which the brief requires: "Mobile (<768px): ... disable pipeline
   * pulse and background animation". The diagram itself is still there and still legible; what stops
   * is the motion.
   */
  function startLoops(): void {
    if (window.innerWidth < 768) return
    const built = buildRingLoops()
    if (!built.length) return

    /* Published so the pulse's `visibility` can be CSS-gated: a dot parked at the path's origin must
       not show on a page where the loop never starts. */
    document.body.dataset.aaRing = 'running'
    loops.push(...built)

    /* The handoff is set up with the loops, not with the entrance: it needs the diagram at its final
       size to anchor to, and while the entrance is still scaling nodes the element's box is moving. */
    startHandoff()
  }


  /**
   * THE SCROLL HANDOFF. The brief: "As the user scrolls past the hero, background and pipeline fade
   * out and the page settles into fully static technical content. Deliberate signal: pitch is over,
   * substance begins."
   *
   * So it is scrubbed rather than triggered: the fade tracks the reader's own scroll position, which
   * makes it feel like a consequence of what they did rather than an animation that fired at them.
   * By the time the filter bar and the metric cards are in view, the field and the diagram are gone
   * and nothing on screen is moving.
   *
   * 🔴 THE WINDOW IS THE SCROLLER, which is what ScrollTrigger defaults to and is why nothing here
   * has to configure one.
   * ⚠ THAT USED TO BE TRUE ONLY ON THIS STAGE. `cinematic.css` gave #app `height: 100vh;
   * overflow: hidden` for `body:not([data-stage='pick'])` and made `.aa-workspace-main` the scroll
   * container, so the handoff's scroller genuinely did not exist two clicks later. The shell was
   * removed on 2026-08-30 because it clipped the rail on a short viewport, and the document scrolls
   * on every stage now. The handoff is still killed when the stage changes, for the reason below
   * rather than for that one: a scroll listener on a landing page nobody is on is work nobody sees.
   *
   * IT ALSO STOPS PAYING FOR WHAT IT CANNOT SEE. Once the diagram is faded out, its pulse and its
   * five float tweens are work nobody is looking at, so they are paused, and resumed if the reader
   * scrolls back up. That is the difference between "settles into static content" as an appearance
   * and as a fact.
   */
  function startHandoff(): void {
    const ring = document.querySelector(SEL.ring)
    const field = document.querySelector('.aa-thermal')
    if (!ring && !field) return

    const targets: object[] = []
    if (field) targets.push({ el: field, vars: { '--aa-th-fade': 0 } })
    if (ring) targets.push({ el: ring, vars: { opacity: 0, y: -18 } })

    for (const t of targets) {
      const { el, vars } = t as { el: Element; vars: gsap.TweenVars }
      const tween = gsap.to(el, {
        ...vars,
        ease: 'none',
        scrollTrigger: {
          /* Anchored to the diagram rather than to a pixel count, so the handoff happens where the
             pitch actually ends however tall the masthead prose renders at a given width. */
          trigger: ring || field,
          start: 'bottom 82%',
          end: 'bottom 18%',
          scrub: true,
          onUpdate: (self) => {
            handoffProgress = self.progress
            /* Pause the ambient motion once the diagram is essentially invisible. Not at exactly 1,
               because a reader parked mid-fade should not leave tweens running against something at
               2 % opacity either. */
            const hidden = self.progress > 0.9
            /* `loops` only -- see the note on `handoff` above. Pausing the scroll tweens here is
               what made the fade one-way. */
            for (const a of loops) {
              if (hidden && !a.paused()) a.pause()
              else if (!hidden && a.paused()) a.resume()
            }
          },
        },
      })
      handoff.push(tween)
      const st = tween.scrollTrigger
      if (st) triggers.push(st)
    }
  }

  /** Stop the ambient motion and leave the diagram in its resting state. */
  function stopLoops(): void {
    if (loopStart !== null) {
      window.clearTimeout(loopStart)
      loopStart = null
    }
    /* THE TRIGGERS GO FIRST. Killing a tween that a ScrollTrigger still owns leaves the trigger
       alive: a scroll listener, a cached start/end measurement and a refresh handler, all pointing at
       elements that are about to be unmounted. */
    for (const st of triggers) st.kill()
    triggers.length = 0
    for (const a of handoff) a.kill()
    handoff.length = 0
    for (const a of loops) a.kill()
    loops.length = 0
    handoffProgress = 0
    delete document.body.dataset.aaRing
    /* Put the field back to full, or a reader who scrolled and then reached Configure would return
       to a landing stage whose background had been left faded. */
    const field = document.querySelector('.aa-thermal')
    if (field) gsap.set(field, { clearProps: '--aa-th-fade' })
  }

  return {
    kill: () => {
      if (watchdog !== null) {
        window.clearTimeout(watchdog)
        watchdog = null
      }
      mm.revert()
      stopLoops()
      if (split) {
        split.revert()
        split = null
      }
      /* Clear anything GSAP left inline. `mm.revert()` already restores the tweened values, so this
         is belt rather than braces -- but an inline `opacity: 1` left on the hero would silently
         win over a future stylesheet rule, and that is a bug nobody would look for here. */
      gsap.set(Object.values(SEL).join(', '), { clearProps: 'opacity,transform,y,yPercent' })
      /* The nodes and their labels are inside an SVG and are not in SEL's top-level list. */
      gsap.set('.aa-ring-node, .aa-ring-note, #aa-ring-track, .aa-ring-return, .aa-ring-arrow', {
        clearProps: 'opacity,transform,y,scale',
      })
    },
    info: () => ({
      ran: built,
      variant,
      withAudio,
      total: Math.round(total * 1000) / 1000,
      watchdogFired,
      handoffProgress,
      triggers: triggers.length,
      beats,
    }),
  }
}
