/**
 * THE TAB MAP: which engine-owned panel belongs in which workspace tab.
 *
 * WHY THIS IS A MAP AND NOT A REBUILD. The thirteen results panels are drawn by
 * results/engine.mjs, which run_all.py step 30 asserts is character for character the code inside
 * demo/index.html. It finds all 113 of its targets by element id and writes into them with innerHTML
 * and canvas contexts. So the tabs REARRANGE what is on screen; they never retype a panel. A panel
 * keeps its id, its markup and its renderer, and gains one attribute saying which tab it lives in.
 *
 * 🔴 VISIBILITY HAS TWO OWNERS HERE AND THAT IS DELIBERATE, because they own different facts.
 *   setStage() owns  "is this panel's STAGE the current one"  -> the `hidden` attribute
 *   the tabs own     "is this panel's TAB the current one"    -> a CSS rule on [data-aa-tab]
 * A panel shows only when both are true. That is not the two-writers bug the page warns about: that
 * bug is two pieces of code setting THE SAME property from different beliefs. Here the properties are
 * different, the mechanisms are different, and neither reads or clears the other. setStage keeps
 * working untouched, which is what standing rule C1 needs for #livecard.
 *
 * 🔴 AND THE CANVASES MUST BE REDRAWN WHEN A TAB OPENS. demo/index.html carries an explicit warning
 * that "a canvas whose parent has no width never draws". It is right: the engine sizes each canvas
 * from its parent's measured width, so a panel that is display:none when drawAll() runs produces a
 * blank chart that stays blank. Every tab activation therefore calls the engine's own drawAll() on
 * the next frame, once the panel has a width. See Workspace.tsx.
 *
 * That warning is about THE PAGE, and the page is not changing. testing/verify_site_panels.py reads
 * demo/index.html directly (its line 290), so it never sees this app.
 */

export type TabId = 'config' | 'live' | 'schedule' | 'money' | 'plume' | 'calib'

export type Tab = {
  id: TabId
  label: string
  /** One short line under the heading. Kept to a line: the deep prose lives in the panels. */
  blurb: string
  /**
   * CSS selectors, resolved inside the engine host once after the markup is injected.
   *
   * SELECTORS AND NOT BARE IDS, because the configure stage's two blocks carry NO id. They are
   * `<div data-show="configure">` at index.html:1795 and the `<details>` holding #filters at
   * index.html:1758. Targeting them by id is impossible, and giving them one would edit the hashed
   * markup that verify_view_matches_page.py compares against the page.
   */
  selectors: string[]
  /** Which engine stage must be reached before this tab can be opened at all. */
  needs: 'configure' | 'results'
}

/**
 * The six tabs, in the order the brief specifies. Every one of the thirteen named results panels
 * appears exactly once, so no panel becomes unreachable: Workspace.tsx asserts that in development.
 */
export const TABS: Tab[] = [
  {
    id: 'config',
    label: 'Configuration & Setup',
    blurb: 'The plant, and what the agent is allowed to do with it.',
    /* 🔴 #filters IS NOT LISTED, AND LISTING IT COST A ROUND TRIP. buildControls() writes the plant
       limit, notice, skill and switch budget into #filters, so it looked like the panel to claim.
       But #filters has no frame of its own, so the first version walked up with
       closest('details, .card, [data-show]') to find one, and landed on a <details> that spans
       demo/index.html lines 1754 to 6970 and ENCLOSES ALL THIRTEEN RESULTS CARDS. Stamping that
       'config' hid every card whenever another tab was active, and the flow check reported all
       twelve hidden including #livecard, which reads as a standing-rule violation rather than as
       the layout mistake it was.
       It needs no entry: #filters lives inside <aside class="sidebar">, and workspace.css shows that
       aside on this tab and hides it on the others. One rule, no walking up. */
    selectors: ['[data-show="configure"]'],
    needs: 'configure',
  },
  {
    id: 'live',
    label: 'Live Agent Execution',
    blurb: 'Seven stages, streaming, on saved responses or on live vendor data.',
    // 🔴 #livecard IS PERMANENT by standing rule C1. It is never removed and never relocated out of
    // the DOM; it lives here, on screen, with #livego inside it.
    selectors: ['#tapecard', '#livecard'],
    needs: 'results',
  },
  {
    id: 'schedule',
    label: 'Hourly Schedule & Reasoning',
    blurb: 'Every hour: ambient, wet-bulb, the bound, and the mode it earns.',
    selectors: ['#decisioncard', '#whycard'],
    needs: 'results',
  },
  {
    id: 'money',
    label: 'Economic Impact',
    blurb: 'Five real years of avoided chiller-hours, priced with its own ceiling.',
    selectors: ['#headcard', '#laddercard', '#moneycard'],
    needs: 'results',
  },
  {
    id: 'plume',
    label: 'Plume & Geometry Analysis',
    blurb: 'The vendor field, the real imagery, and 72 bearings solved on the geometry.',
    selectors: ['#fieldcard', '#sitecard', '#plumecard', '#dialcard'],
    needs: 'results',
  },
  {
    id: 'calib',
    label: 'Model Calibration',
    blurb: 'What the agent promised, what it measured, and the arithmetic between them.',
    selectors: ['#scorecard', '#cfcard'],
    needs: 'results',
  },
]

/** Every named panel the map claims, for the development-time completeness assertion. */
export const MAPPED_PANEL_IDS = TABS.flatMap((t) =>
  t.selectors.filter((s) => s.startsWith('#')).map((s) => s.slice(1)),
)

/**
 * Stamp `data-aa-tab` onto each panel, once, after the engine markup is in the DOM.
 *
 * CLASSIFICATION, NOT VISIBILITY. This writes which tab a panel belongs to and nothing else; a CSS
 * rule keyed on the host's `data-aa-active` does the hiding. Keeping the two apart is what lets
 * setStage() go on owning `hidden` without either of them clearing the other.
 *
 * Returns the ids it could not find, so a rename shows up as a reported gap rather than a panel that
 * silently belongs to no tab and is therefore never displayed again.
 */
/** Every selector the map claims, so the containment guard below can ask "does this element enclose
 *  a panel that belongs to some other tab?" */
const SELF_SELECTORS = TABS.flatMap((t) => t.selectors)

export function classifyPanels(host: HTMLElement): { stamped: number; missing: string[] } {
  const missing: string[] = []
  let stamped = 0

  for (const tab of TABS) {
    for (const sel of tab.selectors) {
      const found = host.querySelectorAll<HTMLElement>(sel)
      if (!found.length) {
        missing.push(sel)
        continue
      }
      found.forEach((el) => {
        /* 🔴 A PANEL MAY NEVER CONTAIN ANOTHER PANEL, and this guard is here because violating it is
           invisible until the whole results stage goes blank. Hiding an ancestor hides everything
           inside it, and `vis()` in verify_app_flow.py tests `offsetParent !== null`, which an
           element inside a display:none parent fails no matter what its own rules say. The first
           version of this map claimed a <details> spanning demo/index.html 1754 to 6970, and every
           card reported hidden.
           So: refuse the stamp and report it, rather than applying it and hiding the stage. */
        if (SELF_SELECTORS.some((s) => s !== sel && el.querySelector(s))) {
          missing.push(`${sel} (rejected: it encloses another tab's panel)`)
          return
        }
        /* A panel could match two tabs if the map ever overlapped. Space-separated plus `~=` in the
           CSS means the panel would then show in both rather than silently in neither. */
        const prev = el.dataset.aaTab
        el.dataset.aaTab = prev && prev !== tab.id ? `${prev} ${tab.id}` : tab.id
        stamped += 1
      })
    }
  }
  return { stamped, missing }
}

/** The tabs reachable at a given engine stage. Anything else is locked, because its panels hold no
 *  data yet: the agent has not run. */
export function unlockedTabs(stage: string | null): TabId[] {
  if (stage === 'results') return TABS.map((t) => t.id)
  if (stage === 'configure') return TABS.filter((t) => t.needs === 'configure').map((t) => t.id)
  return []
}
