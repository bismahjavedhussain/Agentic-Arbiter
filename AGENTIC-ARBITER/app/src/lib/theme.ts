/**
 * WHICH PALETTE THIS SCREEN IS IN, AND THE ONE PLACE THAT WRITES IT TO THE DOCUMENT.
 *
 * 🔴 THIS EXISTS BECAUSE REACT WAS A FRAME TOO LATE, AND A FRAME IS VISIBLE.
 * The user: "when i click 'choose a different site', it takes me to the data centre choosing page,
 * but that page shows the light mode for a few milliseconds before turning into the default dark
 * mode." MEASURED with a per-frame recorder: **2 painted frames, 21 ms**, on the pick stage in the
 * light palette before it flipped to dark.
 * The chain was long and every link cost time: the engine's `setStage()` writes
 * `body[data-stage]`, `lib/stage.ts`'s MutationObserver sees it and calls `setState`, React schedules
 * a render, the render runs, and only then did a `useEffect` write `documentElement.dataset.theme`.
 * A `useEffect` runs after paint by definition, and a `setState` from a MutationObserver microtask is
 * not a discrete event, so React is free to paint before the render lands. Both of those had to go.
 *
 * A MutationObserver callback runs as a MICROTASK, before the next paint. So the observer here writes
 * the attribute itself, synchronously, in the same tick the stage changed. React finds out afterwards
 * and uses the value for the props that need it; it no longer decides it.
 *
 * ⚠ ONE WRITER, WHICH IS THE POINT AND NOT A SIDE EFFECT. This module is the only thing in the app
 * that assigns `documentElement.dataset.theme`, and `App.tsx` now mirrors rather than owns. The
 * alternative, leaving React as the owner and hoping a layout effect lands in time, is the
 * two-owners-of-one-property shape this codebase documents more often than any other.
 * The pre-paint script in `index.html` writes the attribute once before any of this exists, so the
 * FIRST paint of a document is already correct; this module takes over from there.
 */

export type Theme = 'dark' | 'light'
export type Stage = 'pick' | 'configure' | 'results' | null

/**
 * TWO GROUPS, AND ONLY TWO. 'pick' is the landing page, 'work' is configure plus results.
 *
 * A choice is recorded per group because a global one defeated the whole rule: MEASURED, pressing the
 * toggle twice on the configure screen leaves configure looking identical and permanently pins the
 * LANDING page to light, in the same document and after a reload. The reader had changed a screen
 * they were not looking at. See `05-TRAPS` 5b.26 and the entry for 2026-08-30 in `01-STATE`.
 */
export function themeGroup(stage: Stage): 'pick' | 'work' {
  return stage === 'configure' || stage === 'results' ? 'work' : 'pick'
}

/** The group's default when the reader has expressed no preference for it. */
function defaultFor(group: 'pick' | 'work'): Theme {
  return group === 'work' ? 'light' : 'dark'
}

/**
 * What the palette SHOULD be, given the stage and what the reader has chosen for that stage's group.
 *
 * ⚠ THE KEY NAMES CARRY A `-pick` OR `-work` SUFFIX AND THAT IS HALF OF AN EARLIER FIX. Every reader
 * who had ever pressed the toggle was carrying a global `aa-theme-choice`, so keeping the old names
 * would have left them pinned no matter how correct the new logic was. The old pair is deliberately
 * never read again and simply expires.
 */
export function resolveTheme(stage: Stage): Theme {
  const g = themeGroup(stage)
  try {
    if (window.localStorage.getItem('aa-theme-choice-' + g) === '1') {
      const t = window.localStorage.getItem('aa-theme-' + g)
      if (t === 'light' || t === 'dark') return t
    }
  } catch {
    /* private mode: no choice can be read, so the group default holds, which is the safe way round */
  }
  return defaultFor(g)
}

/** The one assignment. Nothing else in the app writes this attribute. */
export function applyTheme(t: Theme): void {
  document.documentElement.dataset.theme = t
}

/** Read what is on the document right now, for a caller that needs to seed state from it. */
export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

/** Record a deliberate choice for the group the reader is looking at, and apply it at once. */
export function chooseTheme(stage: Stage, next: Theme): void {
  const g = themeGroup(stage)
  try {
    window.localStorage.setItem('aa-theme-choice-' + g, '1')
    window.localStorage.setItem('aa-theme-' + g, next)
  } catch {
    /* private mode: the choice holds for this visit and is forgotten on the next, which is the right
       way round. A theme that cannot be remembered should not pretend it was. */
  }
  applyTheme(next)
}

/**
 * KEEP THE DOCUMENT'S PALETTE IN STEP WITH THE STAGE, SYNCHRONOUSLY.
 *
 * Observes `body[data-stage]`, which `setStage()` in the engine is the single owner of, and resolves
 * and applies the palette in the observer's own callback. That callback is a microtask, so it lands
 * before the browser paints the frame in which the stage changed: there is no window in which the new
 * screen is on screen in the old palette.
 *
 * `onChange` lets React mirror the value for the props that need it (`EngineStage` repaints its
 * canvases from it). It is told AFTER the attribute is already correct, so a late render cannot
 * un-paint anything.
 *
 * Returns a disposer. Safe to call twice: the second call replaces the first.
 */
export function installStageTheme(onChange: (t: Theme) => void): () => void {
  if (typeof window === 'undefined' || typeof MutationObserver === 'undefined') return () => {}

  let last: Theme | null = null
  const sync = () => {
    const stage = (document.body.dataset.stage as Stage) || null
    const t = resolveTheme(stage)
    if (t === last) return
    last = t
    applyTheme(t)
    onChange(t)
  }

  /* Once immediately: EngineStage's `setStage('pick')` runs in a LAYOUT effect and can land before
     this one, and a MutationObserver reports nothing about the past. Same reasoning as `useStage`. */
  sync()
  const mo = new MutationObserver(sync)
  mo.observe(document.body, { attributes: true, attributeFilter: ['data-stage'] })
  return () => mo.disconnect()
}
