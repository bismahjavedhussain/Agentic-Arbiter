/**
 * THE ONE CHANNEL BETWEEN THE LAUNCH TIMELINE AND THE GLOBE'S CAMERA.
 *
 * The brief asks for "a slow continuous push-in, a gentle camera dolly toward the planet, running the
 * full duration of the voiceover", and gives the reason it matters: "a static screen for 7 seconds
 * reads as a hang, not as cinema."
 *
 * 🔴 WHY A REGISTRY AND NOT A PROP OR A REF.
 * The timeline is built in `launch.ts`, which is called from `IntroLayer`. The camera lives inside
 * `HeatGlobe`'s effect, which is a child of `IntroGate`, which is a sibling of the call. Threading a
 * ref down would mean IntroGate forwarding a handle it has no use for, and a React ref would still be
 * null on the first frame of the timeline. One module holding one function is smaller and it is the
 * same shape `audio.ts` already uses for the same reason.
 *
 * 🔴 AND IT IS A NUMBER, NOT A CAMERA. What crosses this boundary is `k`, from 0 (the framing the user
 * measured and signed off) to 1 (fully pushed in). `HeatGlobe` decides what that means, and it must,
 * because the framing is solved from the container's measured height and a resize re-solves it. If the
 * timeline set `camera.position.z` directly, the next ResizeObserver tick would overwrite it and the
 * push-in would snap back mid-sequence.
 *
 * ⚠ EXACTLY ONE PROVIDER AT A TIME, and the unregister returns identity-checked so a late unmount
 * cannot clear a newer globe's setter. There is only ever one globe, but "there is only ever one" is
 * how the two-writers bug this project documents gets introduced.
 */

type Apply = (k: number) => void

let apply: Apply | null = null

/** Called by HeatGlobe on mount. Returns the unregister, for its cleanup. */
export function registerDolly(fn: Apply): () => void {
  apply = fn
  return () => {
    if (apply === fn) apply = null
  }
}

/**
 * Push the camera in. `k` is clamped to 0..1 here rather than at the call site, so a tween that
 * overshoots (an easing with a back or elastic curve) cannot send the camera through the planet.
 * A no-op when no globe is mounted, which is the narrow-screen and motion-off case.
 */
export function setDolly(k: number): void {
  apply?.(Math.max(0, Math.min(1, k)))
}

/** Whether a globe is listening. Used only to report state, never to branch the timeline: the
 *  sequence must run identically whether or not there is a camera to move. */
export function dollyAttached(): boolean {
  return apply !== null
}
