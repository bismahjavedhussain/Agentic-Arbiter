/**
 * THE AGENT LOOP, drawn. The brief's own words: "This is the explainer, not decoration. It should
 * make the agent loop legible to someone who reads nothing else."
 *
 * FIVE STAGES, AND THEY ARE THE REAL ONES. `AgentConsole.tsx:31` is the source of truth and it lists
 * seven: PERCEIVE, SOLVE, BOUND, DECIDE, ACT, SCORE, RECALIBRATE. The brief guessed at four
 * (Perceive, Reason, Act, Report), which drops the two that matter most -- BOUND, the conformal
 * safety margin that is this project's whole argument, and SCORE -> RECALIBRATE, which is what makes
 * it a loop rather than a pipeline. So five are drawn, at the user's direction: SOLVE folds into
 * BOUND (the plume is solved in order to be bounded) and RECALIBRATE is the return arc rather than a
 * sixth circle, because that is what it physically is.
 *
 * 🔴 WHY A ROW WITH A RETURN ARC AND NOT A CIRCLE. It is the same closed loop -- five nodes, one
 * cycle, RECALIBRATE closing it -- laid out for the space it has to live in. The slot is about
 * 1180 wide and 240 tall. A circle in that band is either tiny or forces the band to be as tall as
 * it is wide, pushing the site picker below the fold on a laptop. A row with the return sweeping
 * underneath reads as a loop at a glance and fits.
 *
 * 🔴 THE LABELS DESCRIBE WHAT EACH STAGE DOES, NEVER WHAT ANY NUMBER IS. That is the same rule
 * `AgentConsole.tsx` already states for its phrases: "Each describes what a stage DOES, which is a
 * fact about the pipeline rather than about the data, so none of them can go stale against an
 * artefact." Nothing here reads a value, so nothing here can be wrong about one -- which is also why
 * this component needs no data and cannot show a stale figure to a judge.
 *
 * It renders in its FINAL state. Every from-state is applied by GSAP in timeline.ts, so with motion
 * off or reduced motion on, this is a finished static diagram rather than an invisible one.
 */

/* GEOMETRY, in viewBox units. One place, so the path and the nodes cannot disagree.
 *
 * 🔴 THE HEIGHT IS A BUDGET, NOT A PREFERENCE, and it was measured before being set. At 240 units
 * this diagram rendered 230px tall and moved the "Configure this plant" button from y=585 to y=841 --
 * below the fold on a 1440x820 laptop, which has 724px of content height. The front screen's only
 * action disappearing under the fold is a worse outcome than a slightly tighter diagram, so the
 * layout is compressed to the smallest height that keeps every label legible: smaller discs, labels
 * closer under them, and the return arc brought up.
 */
const W = 1180
const H = 182
/** The forward row. */
const ROW_Y = 56
/** The return arc's horizontal run. */
const RETURN_Y = 156
const NODE_R = 21
/** Five nodes, evenly spaced, inset far enough for the return arc to curve outside them.
 *  Exported because timeline.ts needs each node's centre in USER UNITS to scale it in place --
 *  see the svgOrigin note there. Two copies of these numbers would be two things to keep in step. */
export const NODE_XS = [118, 353, 588, 823, 1058]
export const NODE_ROW_Y = ROW_Y
const XS = NODE_XS

/**
 * ONE PATH FOR THE WHOLE LOOP, and it is load-bearing twice: it is the visible connector, and it is
 * the motion path the pulse is driven along by MotionPathPlugin. Two copies of this geometry would
 * be two things to keep in step.
 * Forward along the row, out and down at the right, back along the bottom, up and in at the left.
 */
export const LOOP_PATH =
  `M ${XS[0]} ${ROW_Y} L ${XS[4]} ${ROW_Y} ` +
  `C ${XS[4] + 78} ${ROW_Y} ${XS[4] + 78} ${RETURN_Y} ${XS[4]} ${RETURN_Y} ` +
  `L ${XS[0]} ${RETURN_Y} ` +
  `C ${XS[0] - 78} ${RETURN_Y} ${XS[0] - 78} ${ROW_Y} ${XS[0]} ${ROW_Y}`

export const STAGES = [
  { key: 'perceive', label: 'PERCEIVE', note: 'The 2 m field, hour by hour' },
  { key: 'bound', label: 'BOUND', note: 'Solved, then a measured margin' },
  { key: 'decide', label: 'DECIDE', note: 'Under a switch budget' },
  { key: 'act', label: 'ACT', note: 'Setpoints for the plant' },
  { key: 'score', label: 'SCORE', note: 'Coverage against the promise' },
] as const

/**
 * WHERE THE LOOP'S OUTER EDGES ARE, in the same user units as everything else here.
 * LOOP_PATH curves out to `XS[0] - 78` on the left and `XS[4] + 78` on the right, so those two
 * numbers are the box every label has to stay inside. Derived from the path rather than typed, so
 * moving a node or widening the curve cannot leave the labels behind.
 */
const LOOP_LEFT = XS[0] - 78
const LOOP_RIGHT = XS[4] + 78
/** A little air between a label and the curve it must not touch. */
const EDGE_PAD = 16

/**
 * 🔴 THE OUTER TWO NOTES ARE ANCHORED TO THE LOOP, NOT CENTRED ON THEIR NODE.
 * The user: "sentences like 'the 2 m field, hour by hour' and 'coverage against the promise' are
 * exceeding out of the loop." They were: centred on nodes at x = 118 and x = 1058, they are wider
 * than the 78 units of clearance the return arc leaves outside those nodes, so both ends spilled
 * past the curve.
 * Clamping the text width would truncate a sentence; nudging the x by a measured amount would be a
 * guess that the next wording breaks. Anchoring the first note's START to the left edge and the last
 * note's END to the right edge makes containment a property of the geometry: whatever the sentence
 * says, it cannot begin before the loop or finish after it. The middle three stay centred, because
 * they have room and centred is what reads as belonging to the node above.
 */
function noteAnchor(i: number): { x: number; anchor: 'start' | 'middle' | 'end' } {
  if (i === 0) return { x: LOOP_LEFT + EDGE_PAD, anchor: 'start' }
  if (i === STAGES.length - 1) return { x: LOOP_RIGHT - EDGE_PAD, anchor: 'end' }
  return { x: XS[i], anchor: 'middle' }
}

export function Pipeline() {
  return (
    <div className="aa-ring" data-aa-hero="ring">
      {/* aria-hidden with a real text alternative beside it: an SVG of five circles announces
          nothing useful node by node, but the loop it describes is worth stating once. The sentence
          is visually hidden, not display:none, so it reaches a screen reader. */}
      <p className="aa-ring-sr">
        The agent runs a loop of five stages: perceive the forecast, bound it with a measured safety
        margin, decide a schedule, act on the plant, then score its own coverage and recalibrate.
      </p>

      <svg
        className="aa-ring-svg"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
        focusable="false"
      >
        {/* THE CONNECTOR. Drawn first so the node discs sit on top of it and mask it where they
            overlap, which is what makes the line read as running BETWEEN the stages. */}
        <path id="aa-ring-track" className="aa-ring-track" d={LOOP_PATH} fill="none" />

        {/* THE RETURN LEG'S NAME. RECALIBRATE is a stage, not an ornament, so it is labelled where
            it happens: on the leg that carries SCORE's result back to PERCEIVE. */}
        <text className="aa-ring-return" x={W / 2} y={RETURN_Y - 12} textAnchor="middle">
          RECALIBRATE
        </text>
        {/* Direction, stated once. Without it a return line is ambiguous about which way it runs. */}
        <path
          className="aa-ring-arrow"
          d={`M ${W / 2 - 8} ${RETURN_Y - 6} L ${W / 2 - 20} ${RETURN_Y} L ${W / 2 - 8} ${RETURN_Y + 6}`}
          fill="none"
        />

        {STAGES.map((s, i) => (
          /* One group per stage, so timeline.ts can scale, float and label them as units. The
             transform-box/transform-origin pair in intro.css is what makes a scale tween grow the
             node from its own centre rather than from the SVG's origin. */
          <g key={s.key} className="aa-ring-node" data-aa-node={s.key} data-aa-index={i}>
            <circle className="aa-ring-halo" cx={XS[i]} cy={ROW_Y} r={NODE_R + 8} />
            <circle className="aa-ring-disc" cx={XS[i]} cy={ROW_Y} r={NODE_R} />
            <text className="aa-ring-n" x={XS[i]} y={ROW_Y + 5} textAnchor="middle">
              {i + 1}
            </text>
            <text className="aa-ring-label" x={XS[i]} y={ROW_Y + NODE_R + 22} textAnchor="middle">
              {s.label}
            </text>
            {/* THE DATA LABEL. Faded in and out as the pulse passes, so the shapes read as carrying
                something. It is a description of the stage, never a value. */}
            <text
              className="aa-ring-note"
              data-aa-note={s.key}
              x={noteAnchor(i).x}
              y={ROW_Y + NODE_R + 39}
              textAnchor={noteAnchor(i).anchor}
            >
              {s.note}
            </text>
          </g>
        ))}

        {/* THE PULSE. Parked at the path's start and moved along it by MotionPathPlugin, which means
            the only property animating is a transform -- the performance rule the brief sets, and
            cheaper than animating stroke-dashoffset, which repaints the whole path every frame.
            Hidden until the loop starts, so a motion-off page has no stray dot in the corner. */}
        <circle className="aa-ring-pulse" data-aa-pulse="" r={6} cx={0} cy={0} />
      </svg>
    </div>
  )
}
