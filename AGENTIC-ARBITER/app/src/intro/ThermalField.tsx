/**
 * THE HEAT FIELD. One background, landing stage only, slow enough that you have to stare to catch it.
 *
 * THE BRIEF, AND ITS NON-NEGOTIABLES:
 *   * cycle 45-60 s, and "if motion is perceptible at a glance, it's too fast"  -> 50 s and 58 s
 *   * low saturation, opacity 0.12-0.18, behind all content                     -> 0.15, z-index 0
 *   * CSS or lightweight canvas, no WebGL, no Three.js                          -> pure CSS
 *   * landing page only, never on a data or detail page                         -> body[data-aa-intro]
 *   * no particles, no floating blobs, no starfields                            -> see below
 *
 * 🔴 "ONE ONLY" IS SATISFIED BY CONSTRUCTION, NOT BY PROMISE. `cinematic.css:49` already paints an
 * ambient pair of radial gradients, and its selector is `body:not([data-stage='pick'])` -- the
 * configure and results screens. The landing stage has no ambient background at all today. So this
 * field goes exactly where there is nothing, and the two can never appear together: one selector
 * excludes the landing stage, the other requires it.
 *
 * 🔴 WHY THIS IS A FIELD AND NOT BLOBS, which the brief forbids by name. Two full-bleed layers, each
 * a pair of very large soft radial gradients, oversized past the viewport and moved as WHOLES by a
 * single slow transform each. Nothing is a discrete object with an edge you could point at, nothing
 * travels across the screen, and the two layers drift against each other so the overlap region
 * changes shape -- which is what makes it read as a temperature field shifting rather than as shapes
 * moving over a background. The distance moved is a few percent of the viewport over most of a
 * minute.
 *
 * TRANSFORM ONLY. Two elements, one transform each, promoted with `will-change`. No gradient stop is
 * animated (that repaints), no filter is animated (that is worse), and there is no rAF loop, no
 * canvas and no JavaScript involved in the motion at all -- so this costs nothing when GSAP is idle
 * and keeps working if the motion layer's ticker stalls.
 */
export function ThermalField() {
  return (
    /* aria-hidden and no text: it carries no information, so announcing it would be noise. It is
       also `pointer-events: none` in CSS, because scenery must never intercept a click. */
    <div className="aa-thermal" aria-hidden="true">
      <div className="aa-thermal-a" />
      <div className="aa-thermal-b" />
    </div>
  )
}
