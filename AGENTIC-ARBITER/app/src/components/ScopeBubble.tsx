import { motion } from 'framer-motion'
import { Boxes, Globe2 } from 'lucide-react'

/**
 * The shipped-scope bubble: what the project actually contains, in the empty space to the right of the
 * headline, drifting slowly.
 *
 * 🔴 BOTH COUNTS ARE READ, NEVER TYPED. `shipped` is the number of sites in sites.json carrying
 * `offerable: true`, and `mapped` is the length of unified_sites.json, which is what the national map
 * draws. So this cannot claim a scope the product does not have, which is the whole reason it is a
 * prop rather than a string.
 *
 * POINTS, NOT SENTENCES, at the user's instruction: a bubble is glanced at, not read.
 *
 * THE DRIFT IS DECORATIVE AND SLOW ON PURPOSE. 11 seconds for a 10px excursion, which reads as
 * floating rather than as animation, and it is `transform` only so it never reflows anything or
 * disturbs the canvas panels below. Disabled outright under prefers-reduced-motion.
 */
export function ScopeBubble({ shipped, mapped }: { shipped: number; mapped: number }) {
  return (
    <motion.aside
      className="aa-bubble"
      aria-label="What this project ships"
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{
        opacity: 1,
        scale: 1,
        /* Two axes on different periods, so the path is a slow lissajous rather than a bounce. */
        y: [0, -10, 0, 8, 0],
        x: [0, 6, 0, -6, 0],
      }}
      transition={{
        opacity: { duration: 0.5, ease: 'easeOut' },
        scale: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
        y: { duration: 11, repeat: Infinity, ease: 'easeInOut' },
        x: { duration: 15, repeat: Infinity, ease: 'easeInOut' },
      }}
    >
      <p className="aa-bubble-hero">
        <span className="aa-bubble-num">{shipped}</span>
        <span className="aa-bubble-unit">data centres shipped</span>
      </p>

      <ul className="aa-bubble-list">
        <li>Own plant configuration</li>
        <li>Own hourly schedule</li>
        <li>Own solved plume</li>
      </ul>

      <p className="aa-bubble-foot">
        <Globe2 size={13} strokeWidth={2.2} aria-hidden="true" />
        <span>
          out of <b>{mapped}</b> mapped from OpenStreetMap
        </span>
      </p>
      <p className="aa-bubble-foot">
        <Boxes size={13} strokeWidth={2.2} aria-hidden="true" />
        <span>full agentic analysis, not a sample</span>
      </p>
    </motion.aside>
  )
}
