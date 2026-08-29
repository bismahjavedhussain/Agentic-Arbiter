/**
 * THE TWO KILL SWITCHES, and they are independent on purpose.
 *
 * The user's requirement: "give me two independent kill-switch flags -- one to disable all audio,
 * one to disable the entire motion layer -- so I can demo without either if the room or the
 * hardware demands it."
 *
 * So there are two, they do not imply each other, and each can be thrown three ways:
 *
 *   1. EDIT THE CONSTANT BELOW.        The hard default. Survives a rebuild, needs one.
 *   2. `?motion=off` / `?audio=off`.   Per-load, nothing persisted. What to use on a strange
 *                                     machine or when handing the URL to someone.
 *   3. localStorage.                   Sticky for this browser. What the mute toggle writes.
 *
 * A URL parameter beats localStorage beats the constant, because the parameter is the most
 * deliberate act of the three: someone typed it, for this load, knowing what they wanted.
 *
 * 🔴 MOTION OFF MUST LEAVE A FINISHED PAGE, NOT A BROKEN ONE. With motion off, nothing from
 * `intro/` mounts at all -- no gate, no ring, no thermal field, no ScrollTriggers, no timeline. The
 * page renders exactly as it did before any of this existed. That is also what makes it usable as
 * the verification bypass: `testing/verify_app_flow.py` and `verify_app_deterministic.py` load with
 * `?motion=off` and see the product they were written against, rather than a gate overlay
 * intercepting the click they need to make.
 */

/** ---- 1. THE HARD DEFAULTS. Flip either to `false` to disable that layer everywhere. ---- */
export const MOTION_DEFAULT = true
export const AUDIO_DEFAULT = true
/**
 * 🔴 THE CINEMATIC KILL SWITCH, asked for by name: "One flag that disables the entire audio+cinematic
 * sequence and makes the button navigate instantly. I need this available for demo conditions where
 * sound is inappropriate."
 *
 * It is a THIRD switch rather than a reuse of the other two, because it turns off a different thing.
 * `?audio=off` silences the sequence and still plays nine seconds of it; `?motion=off` unmounts the
 * whole intro layer including the splash. This one keeps the splash exactly as it is and makes the
 * button do what it did before any of this existed: go straight to the site picker.
 *
 * Thrown the same three ways as the others, most deliberate first:
 *      ?cinematic=off   this load only
 *      localStorage     sticky for this browser  (key `aa-cinematic`)
 *      the constant     the hard default
 */
export const CINEMATIC_DEFAULT = true

/** The localStorage keys. `aa-` prefixed like `aa-theme`, which this app already stores. */
export const LS_MOTION = 'aa-motion'
export const LS_AUDIO = 'aa-audio'
export const LS_CINEMATIC = 'aa-cinematic'
/**
 * Set once the splash has been passed, so a reload or a back-button press skips it.
 * Named `hasSeenSplash` because the brief names it: "set a flag (e.g.,
 * sessionStorage.setItem('hasSeenSplash', 'true'))". sessionStorage rather than localStorage, also as
 * specified -- the splash should return for a genuinely new visit, not be suppressed forever.
 */
export const SS_ENTERED = 'hasSeenSplash'

function param(name: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    return new URLSearchParams(window.location.search).get(name)
  } catch {
    return null
  }
}

function stored(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    /* Private mode, or storage disabled. Not a reason to fail to boot. */
    return null
  }
}

/** `off`, `false`, `0` and `no` all mean off. Anything else means on. */
function isOff(v: string | null): boolean {
  return v === 'off' || v === 'false' || v === '0' || v === 'no'
}
function isOn(v: string | null): boolean {
  return v === 'on' || v === 'true' || v === '1' || v === 'yes'
}

function resolve(urlName: string, lsKey: string, hardDefault: boolean): boolean {
  const p = param(urlName)
  if (isOff(p)) return false
  if (isOn(p)) return true
  const s = stored(lsKey)
  if (isOff(s)) return false
  if (isOn(s)) return true
  return hardDefault
}

/**
 * REDUCED MOTION DEFAULTS AUDIO OFF TOO, at the user's instruction: "users who set it usually want
 * less of everything." It is a DEFAULT and not a lock -- an explicit `?audio=on` still wins, which
 * is why this is checked after the parameter in `audioEnabled()` rather than before.
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

/**
 * MOBILE IS UNDER 768px, matching `hooks/use-mobile.ts` rather than inventing a second breakpoint.
 * The brief: "Mobile (<768px): skip the enter gate entirely, disable pipeline pulse and background
 * animation, no audio. Keep only the hero text reveal."
 *
 * Read once at mount rather than tracked live. A phone does not cross 768px mid-visit, and a desktop
 * window dragged narrow mid-animation is not worth tearing a timeline down for.
 */
export function isNarrow(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < 768
}

/**
 * Is the timed cinematic sequence allowed to run at all?
 * Independent of `audioEnabled()`: a muted cinematic is still a cinematic, and the brief wants one
 * switch that removes the WAIT, not just the sound.
 */
export function cinematicEnabled(): boolean {
  if (!motionEnabled()) return false
  return resolve('cinematic', LS_CINEMATIC, CINEMATIC_DEFAULT)
}

/** Is the motion layer allowed to mount at all? */
export function motionEnabled(): boolean {
  return resolve('motion', LS_MOTION, MOTION_DEFAULT)
}

/**
 * Is audio allowed? Four ways to end up silent, and they are checked in order of how deliberate
 * each one is:
 *   an explicit ?audio=on   -> sound, whatever else is true
 *   ?audio=off              -> silence
 *   motion off              -> silence, because there is no timeline left to score
 *   reduced motion, narrow  -> silence
 *   the stored mute choice  -> silence
 */
export function audioEnabled(): boolean {
  if (isOn(param('audio'))) return true
  if (isOff(param('audio'))) return false
  if (!motionEnabled()) return false
  if (prefersReducedMotion() || isNarrow()) return false
  return resolve('audio', LS_AUDIO, AUDIO_DEFAULT)
}

/**
 * Should the enter gate be shown? Only when there is something for the click to unlock and the
 * reader has not already passed it in this tab.
 *
 * NARROW SCREENS SKIP THE GATE ENTIRELY, per the brief. On a phone there is no audio to unlock, so
 * a gate would be a door in front of an open room.
 */
export function gateEnabled(): boolean {
  if (!motionEnabled()) return false
  if (isNarrow()) return false
  if (prefersReducedMotion()) return false
  try {
    if (window.sessionStorage.getItem(SS_ENTERED) === 'true') return false
  } catch {
    /* no sessionStorage: show the gate. Showing it twice is a smaller fault than never. */
  }
  return true
}

/** Remember that the gate has been passed, for this tab only. */
export function markEntered(): void {
  try {
    window.sessionStorage.setItem(SS_ENTERED, 'true')
  } catch {
    /* nothing to do: the gate simply shows again on return */
  }
}

/** Persist the reader's mute choice. `true` means they want sound. */
export function storeAudioChoice(on: boolean): void {
  try {
    window.localStorage.setItem(LS_AUDIO, on ? 'on' : 'off')
  } catch {
    /* the choice still applies to this page's live state; it just will not survive a reload */
  }
}

/**
 * A single object describing what this load is allowed to do, resolved once so every component
 * agrees. Reading the flags twice and getting two answers is the kind of bug that only appears on
 * the machine you cannot debug.
 */
export type IntroFlags = {
  motion: boolean
  audio: boolean
  /** The timed launch sequence. False means the CTA navigates instantly. */
  cinematic: boolean
  gate: boolean
  reduced: boolean
  narrow: boolean
}

export function readFlags(): IntroFlags {
  return {
    motion: motionEnabled(),
    audio: audioEnabled(),
    cinematic: cinematicEnabled(),
    gate: gateEnabled(),
    reduced: prefersReducedMotion(),
    narrow: isNarrow(),
  }
}
