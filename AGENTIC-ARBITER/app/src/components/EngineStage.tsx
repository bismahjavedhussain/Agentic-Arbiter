import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ENGINE_MARKUP } from '../generated/engine-markup'
import { bootEngine, engine } from '../lib/engine'
import { applyDeclutter } from '../lib/declutter'
import { classifyPanels, unlockedTabs, type TabId } from '../lib/tabs'
import { useStage } from '../lib/stage'
import { TabHeader, TabRail } from './Workspace'
import { AgentConsole } from './AgentConsole'
import { PlumeBadge } from './PlumeBadge'
import { ART } from '../lib/artefacts'

/**
 * The configure and results stages: the page's own markup, driven by the page's own engine.
 *
 * WHY THIS COMPONENT IS ONE `innerHTML` AND NOTHING ELSE.
 *
 * The user's complaint was that the new UI had lost the Configure button and everything behind it.
 * It had: the React rebuild was a pick screen that linked out to demo/index.html. Bringing the rest
 * across had two possible shapes, and only one of them is safe.
 *
 * Rewriting 31 renderers and 116 element ids as components would put every audited figure on this
 * page at the mercy of a transcription. audit.py's 2,215 checks read the SINGLE-FILE PAGE; they
 * cannot see a mistake made in a rebuild. So a typo in one id yields a panel that silently draws
 * nothing and no test anywhere goes red.
 *
 * So the markup travels verbatim (scratchpad/mkview.py), the code travels verbatim
 * (scratchpad/mkresults.py), and two verifiers refuse to let either drift. React's contribution is
 * the pick screen the brief asked to redesign, and the shell around all of it.
 *
 * 🔴 THE ONE RULE: REACT DOES NOT RE-RENDER THIS SUBTREE. The engine writes into these nodes with
 * innerHTML and canvas contexts, and a React re-render would wipe every panel it has drawn. Hence
 * `dangerouslySetInnerHTML` with a constant and an empty dependency list: after mount, this subtree
 * belongs entirely to the engine. That is the ordinary pattern for hosting a non-React widget, and
 * here it is also what keeps the verification meaningful.
 *
 * VISIBILITY IS STILL THE ENGINE'S. setStage() walks `[data-show]` and sets `.hidden`, and it stays
 * the single owner -- the page's own comment is emphatic that two pieces of code owning `.hidden`
 * means the last writer wins. React's pick screen therefore carries `data-show="pick"` and lets
 * setStage() hide it, rather than conditionally rendering it.
 */
export function EngineStage({
  sites,
  theme,
  siteKey,
  onReady,
}: {
  sites: { sites: Array<Record<string, unknown>>; scale?: unknown }
  theme: 'dark' | 'light'
  siteKey: string
  onReady?: (ok: boolean) => void
}) {
  const host = useRef<HTMLDivElement | null>(null)
  const booted = useRef(false)
  const injected = useRef(false)
  const [failed, setFailed] = useState<string | null>(null)
  /* Read-only: useStage observes body[data-stage], which setStage() publishes. See lib/stage.ts for
     why an observer rather than React state, given App.tsx's rule against mirroring the stage. */
  const stage = useStage()
  const [tab, setTab] = useState<TabId>('config')
  const unlocked = unlockedTabs(stage)
  /* THE PDF THE CONSOLE OFFERS. Read from the engine's own currentSite() and its `artefacts`
     map, never constructed: sites.json names report.pdf for the metro and a key-prefixed one
     per national site, and a guessed filename is a 404 that looks like a missing feature.
     Null when the manifest names none, and the button is then not rendered at all. */
  const [pdfHref, setPdfHref] = useState<string | null>(null)


  /* The markup goes in FIRST, in a layout effect, so it is in the DOM before bootEngine() runs and
     before the browser paints. Guarded by a ref: injecting twice would discard whatever the engine had
     already drawn, which is the very bug this replaced. */
  useLayoutEffect(() => {
    if (!host.current || injected.current) return
    injected.current = true
    host.current.innerHTML = ENGINE_MARKUP
    /* 🔴 AND HIDE THE NON-PICK STAGES IN THE SAME FRAME. The markup arrives with every card
       unhidden, and setStage() is what hides them -- but bootEngine() below cannot call it until
       loadSite() has awaited two fetches. In between, the results cards and the live card were on
       screen at the pick stage: measured, not theorised, by the flow check, which found #runagent
       visible and <body data-stage> unset on the first screen.
       setStage() needs the DOM and nothing else, so it can run here, synchronously, before the
       browser paints. This is also why it is a LAYOUT effect. */
    try { engine.setStage('pick') } catch { /* the engine is imported at module load; this cannot
                                               fail, but a broken import should not blank the app */ }
    /* AND CLASSIFY THE PANELS INTO TABS, in the same frame and before the first paint. This only
       stamps `data-aa-tab`; the hiding is a CSS rule keyed on the workspace's `data-aa-active`, so
       setStage() remains the sole owner of `hidden`. Doing it here rather than in an effect means no
       frame exists in which every panel is unassigned and therefore displayed at once. */
    /* 🔴 MOVE THE STEPPER INTO THE HEADER. MEASURED: #rail's parent was `viz-root` and `#bezel`,
       the header it sits in on the single-file page, is NOT in the lifted markup, so the progress
       control had nowhere to sit but the content flow, below the tab heading.
       A NODE MOVE and not a re-render: appendChild relocates the engine's own element with its own
       id, its own handlers (wireRail() bound them before this runs) and its own lit pill intact.
       Nothing is retyped, so nothing can drift from the page. Safe because no CSS rule in engine.css
       selects .rail through an ancestor: it is a standalone flex container. */
    const railSlot = document.getElementById('aa-railslot')
    const rail = host.current.querySelector('#rail')
    if (railSlot && rail) railSlot.appendChild(rail)

    /* 🔴 #boundmore IS NOT MOVED, AND MOVING IT IS WHAT BROKE IT.
       I appended it into #cfcard, the last card on the Self-Scoring tab, because that is where a
       "learn more" was asked for. It disappeared.

       #cfcard ships with the class `cfshut` and is COLLAPSED, and engine.mjs:1668 refuses to draw
       anything inside it while that class is present, because every canvas in there sizes itself from
       its parent's clientWidth and a collapsed parent reports zero. #boundmore's own handler
       (engine.mjs:318) is the ONLY thing that opens it: it removes `cfshut`, calls drawConformal(),
       relabels itself "The arithmetic is open below" and scrolls the card into view.

       So the button is the card's opener, and I put the opener inside the thing it opens. It stays
       where the engine put it: the end of #scorecard, directly above the card it reveals, which is
       also exactly where a reader meets it after reading the coverage figures. */

    const { missing } = classifyPanels(host.current)
    if (missing.length && import.meta.env.DEV) {
      /* A panel that matches nothing belongs to no tab and would never be shown again, which is
         invisible in production. Loud in development, silent in the bundle. */
      console.warn('[tabs] these selectors matched no panel, so their content is unreachable:', missing)
    }
  }, [])

  useEffect(() => {
    /* StrictMode runs effects twice in development. Booting twice would re-run loadSite and rebind
       every handler, so the guard is a ref rather than state: it must survive the second call
       without waiting for a render. */
    if (booted.current) return
    booted.current = true

    let cancelled = false
    bootEngine(sites, theme, siteKey)
      .then((key) => {
        if (cancelled) return
        if (!key) setFailed(siteKey)
        onReady?.(!!key)
      })
      .catch((e: Error) => {
        if (!cancelled) setFailed(e.message)
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* 🔴 RE-APPLY THE DECLUTTER AFTER EVERY DRAW, because drawAll() replaces whole cards' innerHTML.
     The engine redraws on any control change and on every theme flip, and each redraw discards the
     folded prose along with everything else it wrote. So this watches the subtree and re-runs.
     Three things keep an observer that mutates what it observes from looping:
       1. every node the pass touches is marked, so a second run finds nothing to do;
       2. `busy` drops mutations raised by the pass itself;
       3. the work is debounced to the next frame, so a redraw that fires fifty mutations runs it once.
     Measured before this existed: 1,680 words in 52 blocks across 13 cards. */
  useEffect(() => {
    const el = host.current
    if (!el) return
    let busy = false
    let queued = 0

    const run = () => {
      queued = 0
      busy = true
      try { applyDeclutter(el) } finally {
        /* released on the next frame, so mutations this pass caused are seen while busy is true */
        requestAnimationFrame(() => { busy = false })
      }
    }

    const mo = new MutationObserver(() => {
      if (busy || queued) return
      queued = requestAnimationFrame(run)
    })
    mo.observe(el, { childList: true, subtree: true })
    run()
    return () => { mo.disconnect(); if (queued) cancelAnimationFrame(queued) }
  }, [])

  /* Theme changes AFTER boot go through the engine, because applyTheme() repoints the two sequential
     ramps and then repaints whatever is on screen. React's toggle owns the attribute; the engine owns
     the redraw. One owner each. */
  useEffect(() => {
    if (!booted.current) return
    try { engine.applyTheme(theme, false) } catch { /* pre-boot; bootEngine sets it */ }
    try {
      if (engine.currentStage() === 'results') engine.drawAll()
      else engine.drawReadyTiles()
    } catch { /* nothing loaded yet */ }
  }, [theme])

  useEffect(() => {
    if (stage !== 'results') return
    try {
      const site = engine.currentSite() as { artefacts?: Record<string, string> } | null
      const rel = site?.artefacts?.report
      setPdfHref(rel ? ART + rel : null)
    } catch { setPdfHref(null) }
  }, [stage])

  /* MOVE TO THE TAB THE NEW STAGE IS ABOUT. Reaching `configure` means the plant is what matters;
     reaching `results` means the run is, so the workspace opens on the agent working rather than
     leaving the reader on a tab whose panels just changed underneath them. */
  useEffect(() => {
    if (stage === 'configure') setTab('config')
    else if (stage === 'results') setTab('live')
  }, [stage])

  /* 🔴 REDRAW WHEN A TAB OPENS, AND THIS IS THE ONE THING A TABBED VERSION OF THIS PAGE CANNOT SKIP.
     demo/index.html carries the warning in full: "a canvas whose parent has no width never draws".
     It is correct. The engine sizes every canvas from its parent's MEASURED width (cssv/yr in
     engine.mjs read layout), so a panel that was display:none when drawAll() last ran holds a canvas
     of zero width that painted nothing, and switching to its tab would reveal a blank chart that
     stays blank forever.

     So every tab activation redraws, on the NEXT FRAME rather than inline: the `data-aa-active`
     attribute below has to be committed and the browser has to lay the panel out before its width is
     anything but zero. requestAnimationFrame is exactly that boundary.

     Cheap enough to do unconditionally: drawAll() is the same call the theme toggle already makes on
     every flip, and only the active tab's canvases have a width to draw into. */
  useEffect(() => {
    if (!booted.current || stage !== 'results') return
    const id = requestAnimationFrame(() => {
      try { engine.drawAll() } catch { /* a panel with no artefact draws nothing, which is its job */ }
    })
    return () => cancelAnimationFrame(id)
  }, [tab, stage])

  /* 🔴 EVERY TAB OPENS AT ITS OWN TOP, whatever the last one was scrolled to.
     `.aa-workspace-main` is the scroll container and it is SHARED by all six tabs, so its scrollTop
     survives a tab change: after reading to the bottom of Economic Impact, clicking Plume showed the
     new panels already scrolled halfway down. The user's report is exact, that it "will show me
     somewhere middle of the page", and that it only happens after scrolling the previous tab.

     Reset here rather than inside the click handler, so it applies however the tab changed, including
     the automatic move to 'live' when the stage becomes 'results'.
     `behavior: 'instant'` on purpose: a smooth scroll would animate through the panels of a tab the
     reader is leaving, which looks like a glitch rather than navigation. */
  useEffect(() => {
    const main = document.querySelector('.aa-workspace-main')
    if (main) main.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
  }, [tab])

  return (
    <>
      {/* 🔴 className="viz-root" IS LOAD-BEARING, NOT COSMETIC. The engine reads its design tokens
          with `const cssv = n => getComputedStyle(document.querySelector('.viz-root'))...`, so
          without an element carrying that class the selector returns null and getComputedStyle
          throws "parameter 1 is not of type 'Element'" -- which is exactly what happened: the
          configure transition rejected, the stage never advanced, and the screen simply sat there.
          It is a CLASS selector, so the id-based check in verify_view_matches_page.py could not see
          it; that check now covers class and attribute selectors too.
          In the page this class is on the main content wrapper and carries its 1180px measure, so
          hosting it here reproduces the page's own layout as well as satisfying the lookup. */}
      {/* 🔴 #c_site IS REACT'S DEBT, and forgetting it stalled the whole flow.
          The engine reads the chosen site from `$('#c_site').value` in cfg() and describeSite(), and
          in the page that <select> lives inside #pickcard -- which React replaced. So React owns the
          picker and therefore owes the element. Without it those lookups return null and throw.
          It is HIDDEN rather than styled, because the visible way to choose a site in this UI is the
          search bar and the map; this is the engine's own handle on that choice, kept in sync by
          lib/engine.ts. Populated from sites.json, which is what buildSitePicker() used to do.
          It sits BEFORE the markup and inside this component so that it is in the DOM before
          bootEngine() runs in the effect below. */}
      <select id="c_site" hidden aria-hidden="true" tabIndex={-1}>
        {(sites.sites || [])
          .filter((s) => (s as { offerable?: boolean }).offerable)
          .map((s) => String((s as { key?: string }).key))
          .map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
      </select>

      {/* 🔴 THE MARKUP IS INJECTED IN AN EFFECT, NOT VIA dangerouslySetInnerHTML, and the difference
          is not stylistic. With dangerouslySetInnerHTML React OWNS these children: it holds the
          previous __html and re-applies it whenever it decides to. That is what happened here -- the
          configure transition ran, buildControls() filled #filters, React re-rendered on the
          `configuring` state change, re-applied the pristine markup, and #filters was empty again.
          Nothing threw. The stage said "configure" and the controls were simply gone, which is the
          least debuggable failure available.
          An empty div plus a one-time innerHTML in a layout effect means React has no children here to
          diff, ever. The engine owns this subtree outright. That is what the comment at the top of
          this file was already asserting; this is the version of it that is actually true. */}
      {/* THE WORKSPACE SHELL. `data-aa-active` is the one fact the tabs own, and index.css turns it
          into a display rule against each panel's `data-aa-tab`. It sits on an ANCESTOR of the host
          because that is what the CSS needs; it is never set on a panel, so it cannot collide with
          the `hidden` attribute setStage() owns.
          At the pick stage the rail is hidden by CSS on body[data-stage], not unmounted, so the
          engine host inside it is never torn down and rebuilt. */}
      <div className="aa-workspace" data-aa-active={tab}>
        <TabRail active={tab} unlocked={unlocked} onSelect={setTab} />
        {/* 🔴 THE HEADING IS OUTSIDE THE SCROLL CONTAINER, which is the only way it stops merging
            with the content. As a sticky child of the scrolling column it stayed on screen but the
            panels slid UNDER it, so it overlapped the first card: the user's words were that the
            headings "completely get merged with the content".
            Now the column is a flex stack of a fixed heading and a scrolling body, so the heading is
            never painted over and the panels never reach it. That is how a tab is supposed to sit. */}
        <div className="aa-workspace-col">
          <TabHeader active={tab} />
          <div className="aa-workspace-main">
          {/* The console chrome, only where it means anything. It reads #tape and writes nothing,
              so mounting and unmounting it cannot disturb the engine's own stream. */}
          {/* THE AGENT, AS ONE ROW, and the ONLY thing standing in for the tape now.
              The stage rail and the expanded 16-line trace are both gone from the screen at the
              user's instruction. #tapecard stays in the DOM, hidden by cinematic.css, because
              #tape is what verify_app_flow.py counts and #tapedone is the completion signal this
              console reads. It reads them and writes nothing, so the engine's stream is untouched. */}
          {tab === 'live' && stage === 'results' && <AgentConsole pdfHref={pdfHref} />}
          {/* The solver, named on the tab it belongs to. Reads #dialcard and writes nothing. */}
          {tab === 'plume' && stage === 'results' && <PlumeBadge />}
            <div ref={host} className="viz-root" />
          </div>
        </div>
      </div>
      {failed && (
        <p className="mt-4 text-[13px]" style={{ color: 'var(--critical)' }}>
          <b>No built artefacts for {failed}.</b> Run{' '}
          <code>python src/build_sites.py {failed}</code> and reload. The pick screen and the map are
          unaffected.
        </p>
      )}
    </>
  )
}
