/**
 * Stop the page jumping to the top when nothing about the stage has changed.
 *
 * 🔴 THE BUG, MEASURED. Changing the selected facility on the pick screen threw the window to the
 * top, so the map and the filters left the viewport and the reader had to scroll back down to see
 * the site they had just chosen. It ALTERNATED: one change was fine, the next jumped.
 *
 * `scratchpad/scrollprobe.py` patched window.scrollTo, scrollIntoView and focus, drove three
 * facility changes and recorded the stacks. The answer came back unambiguous:
 *
 *     window.scrollTo arg={"top":0,"behavior":...}  at Module.ad [as setStage]   y=452 -> 0
 *
 * engine.mjs:138, the last line of setStage():
 *
 *     window.scrollTo({top:0, behavior: next==='pick' ? 'auto' : 'smooth'});
 *
 * That is RIGHT for a real transition: arriving at a new stage should start at the top of it. It is
 * wrong when setStage is re-run with the stage it is already on, which the engine does deliberately
 * in more than one place -- probeLive() ends with `if(STAGE) setStage(STAGE);` precisely so that one
 * function stays the single owner of what is visible. Those re-runs are no-ops for visibility and
 * were scrolling the page anyway.
 *
 * WHY A SHIM RATHER THAN A ONE-LINE FIX IN THE ENGINE. results/engine.mjs is asserted character for
 * character against demo/index.html by run_all.py step 30, and that identity is what makes the React
 * rebuild trustworthy. A condition added there would end it.
 *
 * WHAT IT DOES, AND WHAT IT DELIBERATELY DOES NOT.
 *   It swallows a scroll-to-top ONLY when `document.body.dataset.stage` is the same value it was at
 *   the last scroll-to-top that was allowed through. A genuine pick -> configure -> results
 *   transition still scrolls, because the attribute changed.
 *   It touches nothing else: any scroll with a target other than the very top, any scroll the READER
 *   causes, and every scrollIntoView (the "Learn more about the bound" button relies on one) pass
 *   straight through untouched.
 */

let installed = false

export function installNoScrollJump() {
  if (installed || typeof window === 'undefined') return
  installed = true

  const native = window.scrollTo.bind(window)
  /* The stage the last ALLOWED scroll-to-top belonged to. `null` until the first one, so the scroll
     at boot is never suppressed. */
  let lastStage: string | null = null

  const isTopScroll = (args: unknown[]): boolean => {
    if (args.length === 1 && typeof args[0] === 'object' && args[0] !== null) {
      const o = args[0] as ScrollToOptions
      /* `left` is allowed to be absent or 0; anything else is a real horizontal move and not ours. */
      return (o.top ?? -1) === 0 && !o.left
    }
    /* The two-argument form, scrollTo(x, y). */
    return args.length === 2 && Number(args[0]) === 0 && Number(args[1]) === 0
  }

  window.scrollTo = function patched(...args: unknown[]) {
    if (isTopScroll(args)) {
      const stage = document.body.dataset.stage || ''
      if (stage !== '' && stage === lastStage) {
        /* Same stage as the last time we jumped to the top: this is a no-op re-run of setStage, not
           a transition. Swallow it and leave the reader where they were. */
        return
      }
      lastStage = stage
    }
    // eslint-disable-next-line prefer-spread
    return native.apply(window, args as never)
  } as typeof window.scrollTo
}
