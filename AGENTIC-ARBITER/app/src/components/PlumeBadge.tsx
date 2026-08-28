import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Cpu } from 'lucide-react'

/**
 * What solves the plume, said out loud on the Plume tab.
 *
 * 🔴 WHY THIS EXISTS. "NVIDIA Warp" appeared exactly once in the whole product, buried in the middle
 * of a popover on #dialcard (demo/index.html:2121), which is the least likely place a reader looks.
 * The solver is a real part of the engineering and the tab it belongs to said nothing about it.
 *
 * 🔴 THE NUMBERS ARE READ FROM THE PANEL, NOT TYPED. The solve count and the bearing count are
 * written by the engine into #dialcard from the site's own rise table, so they change per site and
 * per placement. This scrapes them out of that rendered text with a regex and shows NOTHING numeric
 * when the match fails. Hardcoding "576 solves" would have been a figure with no artefact behind it
 * that silently went stale the moment another site was selected.
 *
 * It is a READER of engine DOM and writes nothing into it.
 */
export function PlumeBadge() {
  const [facts, setFacts] = useState<{ solves?: string; bearings?: string }>({})

  useEffect(() => {
    const card = document.getElementById('dialcard')
    if (!card) return
    let queued = 0
    const read = () => {
      queued = 0
      const txt = card.textContent || ''
      /* Both patterns are the engine's own wording. If it ever changes, this shows the framework and
         the purpose and drops the numbers, rather than showing a number that is no longer true. */
      const s = txt.match(/([\d,]+)\s+GPU solves/i)
      const b = txt.match(/(\d+)\s+bearings/i)
      setFacts({ solves: s?.[1], bearings: b?.[1] })
    }
    const mo = new MutationObserver(() => {
      if (queued) return
      queued = requestAnimationFrame(read)
    })
    mo.observe(card, { childList: true, subtree: true, characterData: true })
    read()
    return () => { mo.disconnect(); if (queued) cancelAnimationFrame(queued) }
  }, [])

  return (
    <motion.div
      className="aa-gpu"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      <span className="aa-gpu-icon" aria-hidden="true">
        <Cpu size={16} strokeWidth={2.2} />
      </span>
      <div className="aa-gpu-body">
        <p className="aa-gpu-head">
          Solved on the GPU with <strong>NVIDIA Warp</strong>
        </p>
        <p className="aa-gpu-sub">
          {facts.bearings ? <><strong>{facts.bearings} wind bearings</strong>, every one</> : 'Every wind bearing'}{' '}
          solved on the committed building footprints
          {facts.solves ? <> at <strong>{facts.solves} GPU solves</strong> per placement</> : null}.
          Not sampled and not interpolated: a bearing the solver cannot stand behind is refused rather
          than answered, which is only affordable because each solve is cheap enough to run all of them.
        </p>
      </div>
    </motion.div>
  )
}
