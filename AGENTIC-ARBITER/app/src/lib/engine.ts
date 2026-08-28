/**
 * The typed door onto AGENTIC-ARBITER/results/engine.mjs.
 *
 * WHAT THE ENGINE IS. The 100 functions that draw the configure and results stages, lifted byte for
 * byte out of demo/index.html by scratchpad/mkresults.py. Every panel, the decision tape, the plume
 * field, the conformal bound, the money sweep and the live agent. run_all.py asserts on every run
 * that it is still character-for-character the page's own code.
 *
 * WHY A WRAPPER RATHER THAN IMPORTING IT DIRECTLY EVERYWHERE. Two reasons, and the second is the
 * important one:
 *   1. It is a generated .mjs with no type declarations, so the surface is declared once, here.
 *   2. IT NAMES THE SEQUENCE. The page's boot() ran these calls in a specific order and its own
 *      comment says why -- "buildSitePicker() runs FIRST and picks the default selection while PF is
 *      still null; loading a site before it would change which option the picker opens on, which is a
 *      behaviour change disguised as a performance tweak". Order that carries a reason like that
 *      belongs in one function with the reason attached, not scattered across three components.
 *
 * WHAT REACT MUST NOT DO. Re-render the engine's DOM. The engine owns everything inside the markup it
 * was given; React renders that markup once and then keeps its hands off. See EngineStage.tsx.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
/* No @ts-expect-error here: TypeScript resolves the generated .mjs on its own and infers `any`, so
   the directive was reported as unused. The Engine type below is what actually constrains the calls,
   and it is the honest place for that -- a suppression comment would only have hidden the fact that
   nothing was checking them. */
import * as ENGINE from '../../../results/engine.mjs'

type Sites = { sites: Array<Record<string, any>>; scale?: unknown }

/** The subset of the engine's 103 exports this app actually calls. */
type Engine = {
  /* the adapter, the only written code in the generated file */
  attachSites: (s: Sites) => boolean
  currentSite: () => any
  currentStage: () => 'pick' | 'configure' | 'results'
  /* the stage machine, still the single owner of what is visible */
  setStage: (s: 'pick' | 'configure' | 'results') => void
  /* loading */
  loadSite: (key: string) => Promise<boolean>
  loadField: () => Promise<unknown>
  /* the configure stage */
  buildControls: () => void
  describeSite: () => void
  siteIsRunnable: (key: string) => boolean
  /* wiring: this is what binds #runagent, #runagent2 and #backtopick */
  wire: () => void
  wireAerial: () => void
  wireRail: () => void
  /* drawing */
  drawAll: () => void
  drawPlate: () => void
  drawReadyTiles: () => void
  /* theme: applyTheme repoints the BLUE and ORANGE ramps every renderer draws with */
  applyTheme: (next: 'dark' | 'light', persist: boolean) => void
  /* the live agent */
  probeLive: () => Promise<unknown> | void
  runLive: () => Promise<unknown> | void
}

const E = ENGINE as unknown as Engine

export const engine = E

/**
 * Bring the engine up, in the page's own order.
 *
 * Mirrors boot() minus the three things it did that React now does itself: building the national map,
 * building the site picker's options, and wiring the theme button. Everything else is the same
 * sequence for the same reasons.
 *
 * Returns the key that was actually loaded, or null if the site had no built artefacts.
 */
export async function bootEngine(
  sites: Sites,
  theme: 'dark' | 'light',
  siteKey: string,
): Promise<string | null> {
  E.attachSites(sites)
  /* FIRST, because it repoints the BLUE and ORANGE sequential ramps at the correct end for the
     theme, and every panel draws with those ramps. `false` means do not repaint: nothing is drawn
     yet, and the page's own applyTheme would call drawAll() on a stage that has no data. */
  E.applyTheme(theme, false)
  E.wireRail()

  /* #c_site is the engine's own <select> and it arrives with the lifted markup, but its options are
     built by buildSitePicker() -- which stays in the page because React's search bar replaces it.
     So the value is set directly. loadSite() looks the key up in SITES and refuses an unknown one,
     which is the same validation the page's ?site= handling relies on. */
  const sel = document.getElementById('c_site') as HTMLSelectElement | null
  if (sel) {
    if (!Array.prototype.some.call(sel.options, (o: HTMLOptionElement) => o.value === siteKey)) {
      const o = document.createElement('option')
      o.value = siteKey
      o.textContent = siteKey
      sel.appendChild(o)
    }
    sel.value = siteKey
  }

  const ok = await E.loadSite(siteKey)
  if (!ok) return null
  E.drawPlate()
  E.setStage('pick')
  /* The live probe is fire-and-forget on purpose: on a static host there is no /api/health to
     answer, the fetch fails, and that is REPLAY rather than an error. The card explains itself
     either way, which is why standing rule C1 keeps it present instead of hiding it. */
  try { void E.probeLive() } catch { /* a missing live server is a mode, not a fault */ }
  return siteKey
}

/**
 * The "Configure the plant" transition, which is the page's chooseSite() with its own button work
 * removed. React owns #pickgo now, so the caller reports progress and failure.
 *
 * The order here is chooseSite()'s order: load, build the controls, fetch the field, wire, name the
 * site, then move the stage. wire() is what binds #runagent, #runagent2 and #backtopick, so the three
 * buttons on the next two screens need no React code at all.
 */
export async function configureSite(key: string): Promise<boolean> {
  const sel = document.getElementById('c_site') as HTMLSelectElement | null
  if (sel) sel.value = key

  const ok = await E.loadSite(key)
  if (!ok) return false

  E.buildControls()
  await E.loadField()
  E.wire()
  E.wireAerial()

  const site = E.currentSite()
  const nameEl = document.getElementById('sitename')
  if (nameEl && site) nameEl.textContent = site.label
  E.setStage('configure')
  return true
}
