/**
 * Turn the results stage from a report you scroll through into a screen you read.
 *
 * THE PROBLEM, MEASURED. The rendered results stage carries **1,680 words of prose in 52 blocks**
 * across 13 cards, most of it written at runtime by the renderers rather than sitting in the markup.
 * The user's words: "seems like a report generated through which you keep scrolling through with dump
 * of too much technical information and not an interactive app which is not boring to look at. I
 * wanted you to be intelligent here and only display one or two liners for every aspect and only
 * explain in a pop up option."
 *
 * WHAT THIS DOES, AND THE LINE IT WILL NOT CROSS.
 *
 *   IT REWRITES PROSE.      Each card gets one authored lead of one or two lines, in plain language,
 *                           chosen to say what the panel is FOR and why it matters. Every long prose
 *                           block the engine wrote is folded behind a button that opens it in a modal.
 *
 *   IT TOUCHES NO NUMBERS.  Tiles, tables and canvases are excluded by selector, not by hope. The
 *                           brief is explicit: "Do not modify the existing reports, graphs, or
 *                           numerical data cards. Leave all quantitative elements exactly as they
 *                           are." So no figure, axis, row or chart is read, moved or rewritten here.
 *                           Nothing in this file can change a number, because it never looks at one.
 *
 * WHY IT IS A DOM PASS RATHER THAN AN EDIT TO THE ENGINE. The engine is lifted byte for byte out of
 * demo/index.html and a verifier fails the build if a character moves. Rewriting its prose would mean
 * rewriting the page, which would restate the user's own writing and break the one thing that makes
 * two copies of 208 KB safe. So the engine draws what it always drew, and this reorganises the result.
 * The page itself is untouched and stays available as the dense version, preserved in
 * AGENTIC-ARBITER/preserved/.
 *
 * IT MUST BE IDEMPOTENT AND RE-RUNNABLE. drawAll() runs again on every control change and on every
 * theme flip, replacing whole cards' innerHTML and discarding this pass with it. So each processed
 * node is marked, and EngineStage re-runs the pass when the subtree changes.
 */

/** A word count above which a paragraph is a deep dive rather than a caption. */
const FOLD_ABOVE_WORDS = 14

/** The authored lead for each card: one or two lines, plain words, no dashes as punctuation. */
type Lead = { lead: string; more: string }

const LEADS: Record<string, Lead> = {
  tapecard: {
    lead: 'Seven stages, streamed as they ran. Every number on this page was computed in these steps.',
    more: 'How it worked',
  },
  decisioncard: {
    lead: 'One day, hour by hour: when to cool with outside air, and when to run the chiller.',
    more: 'How the schedule is chosen',
  },
  headcard: {
    lead: 'Five years of this site’s real weather, priced. On many settings the honest answer is that there is no free cooling to win.',
    more: 'What these figures mean',
  },
  laddercard: {
    lead: 'Take one input away at a time and measure what it costs. That is what each part of the agent is worth.',
    more: 'What each row removes',
  },
  moneycard: {
    lead: 'A sweep of published electricity tariffs and chiller efficiencies, cheapest to dearest. Not a projection.',
    more: 'Where the prices come from',
  },
  fieldcard: {
    lead: 'FortyGuard’s own forecast field, at the height a ground-mounted condenser breathes.',
    more: 'How the field is read',
  },
  sitecard: {
    lead: 'The real buildings the solver used, drawn from OpenStreetMap over aerial imagery.',
    more: 'How the site was measured',
  },
  plumecard: {
    lead: 'The neighbour’s hot exhaust, solved on this site’s real geometry. Turn the wind and watch the intake heat up.',
    more: 'How the plume is solved',
  },
  dialcard: {
    lead: 'Every wind direction, solved. Where the geometry beats the physics, the agent refuses the hour instead of guessing.',
    more: 'What refusal means',
  },
  whycard: {
    lead: 'The agent’s reasoning for one hour, in its own words, then checked by running it again.',
    more: 'Read the reasoning',
  },
  scorecard: {
    lead: 'The agent grades its own promise against what actually happened, and widens its margin when it was wrong.',
    more: 'How it scores itself',
  },
  cfcard: {
    lead: 'The safety margin is built from the agent’s own past errors. This is the arithmetic, step by step.',
    more: 'Follow the arithmetic',
  },
  livecard: {
    lead: 'The next hours, decided on a forecast bought right now rather than on saved data.',
    more: 'What a live run costs',
  },
}

/** Elements whose contents are quantitative and therefore off limits. */
const PROTECTED = '.tile, table, canvas, #tape, .ev, .plate-cell, .rail-step, svg'

const MARK = 'data-aa-declutter'

function words(t: string): number {
  return t.trim().split(/\s+/).filter(Boolean).length
}

/** Fire the modal. A custom event, so engine DOM can talk to React without importing it. */
export const DETAIL_EVENT = 'aa:detail'

export type DetailPayload = { title: string; html: string }

function foldButton(label: string, title: string, html: string): HTMLButtonElement {
  const b = document.createElement('button')
  b.type = 'button'
  b.className = 'aa-fold'
  b.setAttribute(MARK, 'trigger')
  b.textContent = label
  b.addEventListener('click', () => {
    window.dispatchEvent(
      new CustomEvent<DetailPayload>(DETAIL_EVENT, { detail: { title, html } }),
    )
  })
  return b
}

/**
 * Apply the pass to one card. Returns how many blocks were folded.
 *
 * The card's own <h2> stays exactly as the engine wrote it, because it is the panel's name and the
 * section rail links to it.
 */
function declutterCard(card: HTMLElement, id: string): number {
  const spec = LEADS[id]
  const title = (card.querySelector('h2')?.textContent || '').replace(/\s+/g, ' ').trim()

  // 1. the authored lead, inserted once, directly after the heading
  if (spec && !card.querySelector(`[${MARK}="lead"]`)) {
    const h2 = card.querySelector('h2')
    const p = document.createElement('p')
    p.className = 'aa-lead'
    p.setAttribute(MARK, 'lead')
    p.textContent = spec.lead
    if (h2 && h2.parentNode) h2.parentNode.insertBefore(p, h2.nextSibling)
    else card.insertBefore(p, card.firstChild)
  }

  // 2. fold any deep dive the engine has written that is not folded yet
  const blocks = Array.from(card.querySelectorAll<HTMLElement>('p, li, details'))
  for (const el of blocks) {
    if (el.getAttribute(MARK)) continue
    if (el.closest(PROTECTED)) continue
    const text = (el.textContent || '').replace(/\s+/g, ' ').trim()
    if (words(text) <= FOLD_ABOVE_WORDS) continue
    /* Never fold something that carries a chart, a table, a figure, or A CONTROL THE ENGINE HAS
       WIRED.
       🔴 THE LAST CLAUSE IS A BUG FIX, AND IT IS THE ONE THE USER REPORTED: "why does changing the
       hour do nothing to the output table below? what is this hour dropdown for then?"
       The `<details>` headed "One hour, all seven stages of the loop" (demo/index.html:2186) holds
       `<select id="c_hour">`, and the engine binds a real change handler to it
       (results/engine.mjs:309, `bind('#c_hour', () => { if(TK) drawTicker(); })`) which rewrites the
       seven stage lines in `#tkhour`. Folding that block hid the live node and serialised its
       `innerHTML` into the string this file hands to the fold row, and step 3 below re-parses that
       string with dangerouslySetInnerHTML.
       SERIALISING HTML DROPS EVENT LISTENERS. So the select a reader could actually see was a dead
       copy with no handler, and because ids are copied along with everything else there were then
       TWO `#c_hour` in the document, with `$('#c_hour')` inside the engine still resolving to the
       hidden original. MEASURED headlessly against this exact bundle: a real bubbling `change` event
       on the visible clone left the seven stage lines byte-identical, while the same event on the
       hidden original redrew them from 12:00 to 00:00.
       Exempting the block keeps the LIVE node on the page. It stays a `<details>`, so it is still
       closed until a reader opens it and the decluttering brief is still honoured: a disclosure and
       a modal are the same "behind one click" affordance. Removing the duplicate id also restores
       `$('#c_hour')` for engine.mjs:808, 1197, 1201 and 1203.
       ⚠ BLAST RADIUS IS ONE BLOCK, checked rather than assumed: the other engine selects on this
       stage (#c_alpha, #c_n, #c_chiller, #c_price, #c_field, #c_img) are not inside a `p`, `li` or
       `details`, so they were never fold candidates in the first place. */
    if (el.querySelector('canvas, table, .tile, select, input, textarea')) continue
    el.setAttribute(MARK, 'folded')
    el.style.display = 'none'
  }

  /* 3. REBUILD THE SINGLE FOLD ROW FROM SCRATCH, rather than appending another one.
     🔴 The first version appended a new row on every pass, and the engine redraws PARTS of a card
     (`$('#dbar').innerHTML = ...`) without replacing the card, so my row survived and a second and
     third were added beside it. The screen showed "What a live run costs (3)" next to "(1)", and
     "How the schedule is chosen" three times.
     Collecting from the folded nodes themselves, which are still in the DOM and still marked, makes
     this self-healing: whatever state the card is in, one pass produces exactly one correct row. */
  const foldedEls = Array.from(
    card.querySelectorAll<HTMLElement>(`[${MARK}="folded"]`),
  )
  for (const old of Array.from(card.querySelectorAll(`[${MARK}="row"]`))) old.remove()

  if (foldedEls.length && spec) {
    const holder = document.createElement('div')
    holder.className = 'aa-foldrow'
    holder.setAttribute(MARK, 'row')
    holder.appendChild(
      foldButton(
        `${spec.more} (${foldedEls.length})`,
        title,
        foldedEls.map((e) => `<p>${e.innerHTML}</p>`).join(''),
      ),
    )
    card.appendChild(holder)
  }
  return foldedEls.length
}

/** Run over the whole results subtree. Safe to call repeatedly. */
export function applyDeclutter(root: ParentNode = document): { cards: number; folded: number } {
  let cards = 0
  let folded = 0
  for (const id of Object.keys(LEADS)) {
    const card = root.querySelector<HTMLElement>('#' + id)
    if (!card) continue
    cards++
    folded += declutterCard(card, id)
  }
  return { cards, folded }
}
