import { useEffect, useState } from 'react'

/**
 * READ the engine's current stage. Do not set it.
 *
 * 🔴 WHY AN OBSERVER RATHER THAN REACT STATE, and the distinction matters more here than it looks.
 * App.tsx already refuses to keep a copy of the stage, and its comment says why: "React mirroring it
 * would be a second owner of one fact, which is precisely the bug demo/index.html documents at
 * length: the last writer wins, and which one that is depends on render timing."
 *
 * That objection is to a second WRITER. This is a reader. setStage() publishes the stage as
 * `document.body.dataset.stage` (engine.mjs:105) on every transition, and this watches that
 * attribute. Nothing here can set it, so there is still exactly one owner; the workspace just gets
 * told which tabs may be unlocked.
 *
 * The alternative was threading a callback out of configureSite() and out of the engine's own
 * #runagent handler, which wire() binds. That handler is inside the byte-identical engine and cannot
 * be given a callback without editing it, so an observer is not merely tidier, it is the only route
 * that leaves engine.mjs untouched.
 */
export function useStage(): 'pick' | 'configure' | 'results' | null {
  const [stage, setStage] = useState<'pick' | 'configure' | 'results' | null>(
    () => (document.body.dataset.stage as 'pick' | 'configure' | 'results') || null,
  )

  useEffect(() => {
    const read = () => {
      const s = document.body.dataset.stage
      setStage(s === 'pick' || s === 'configure' || s === 'results' ? s : null)
    }
    /* attributeFilter, so this wakes on the one attribute it cares about rather than on every class
       toggle anything else makes to <body>. */
    const mo = new MutationObserver(read)
    mo.observe(document.body, { attributes: true, attributeFilter: ['data-stage'] })
    /* And read once on mount: EngineStage calls setStage('pick') in a LAYOUT effect, which can land
       before this effect runs, and a MutationObserver reports nothing about the past. */
    read()
    return () => mo.disconnect()
  }, [])

  return stage
}
