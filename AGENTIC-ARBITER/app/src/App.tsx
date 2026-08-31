import { useCallback, useEffect, useMemo, useState } from 'react'
import { Masthead } from './components/Masthead'
import { SearchBar, type Filters } from './components/SearchBar'
import { SelectedBar } from './components/SelectedBar'
import { KpiCards } from './components/KpiCards'
import { SiteMap } from './components/SiteMap'
import { EngineStage } from './components/EngineStage'
import { DetailModal } from './components/DetailModal'
import { IntroLayer } from './intro/IntroLayer'
import { IntroBoundary } from './components/IntroBoundary'
import { ScopeBubble } from './components/ScopeBubble'
import { useStage } from './lib/stage'
import { chooseTheme, currentTheme, installStageTheme } from './lib/theme'
import { configureSite } from './lib/engine'
import { ART, loadArtefacts, type Artefacts } from './lib/artefacts'
import { DEFAULT_METRO, loadHeadline, type Headline } from './lib/headline'

/**
 * The pick screen, in the order the brief specifies:
 *
 *   1. headline, ending on the live-agent line
 *   2. the search bar          <- sticky, so it stays usable at the map
 *   3. the data cards
 *   4. the map
 *
 * THE VIEWPORT RULE, AND THE TENSION IN IT. The brief asks for that order AND for the search bar and
 * the map to be visible together so the map can be watched while the search is used. With the data
 * cards between them those cannot both hold at any laptop height. The bar is therefore sticky: the
 * DOM order is exactly as asked, and scrolling to the map keeps the controls on screen and live.
 */
export function App() {
  const [a, setA] = useState<Artefacts | null>(null)
  const [h, setH] = useState<Headline | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [live, setLive] = useState<'checking' | 'attached' | 'replay'>('checking')
  const [configuring, setConfiguring] = useState(false)
  /* THE FILTERS CAN ARRIVE IN THE URL, which buys two things at once.
     A reader gets a shareable link to a state, an operator or one facility. And the browser checks
     get a way to DRIVE the three behaviours the brief specifies -- fit to a state, highlight an
     operator, fly to a facility -- without simulating typing into a combobox. Without it, those
     three could only be verified by hand, which for this project means not verified. */
  const [filters, setFilters] = useState<Filters>(() => {
    const q = new URLSearchParams(typeof location === 'undefined' ? '' : location.search)
    return {
      state: q.get('state') || '',
      operator: q.get('operator') || '',
      /* 🔴 ASHBURN IS PRESELECTED, at the user's instruction: the first screen should open on the
         facility the project actually ships a full agent run for, rather than on an empty search box
         over 637 candidates. `metro_ashburn` is the map key whose label is "Ashburn, Virginia" and
         whose committed pair is Amazon Web Services IAD116 to IAD117 (sites.json `committed`).
         It is the DEFAULT, not a lock: `?facility=` still overrides it, which is what the browser
         checks drive, and clearing the selection still works. */
      facility: q.get('facility') || 'metro_ashburn',
    }
  })
  /* 🔴 PRESELECTED IS NOT THE SAME AS FILTERED, and conflating them broke a real check.
     Defaulting `filters.facility` to metro_ashburn also filtered the map to that ONE key
     (SiteMap.tsx:254 clauses on it), so the national footprint collapsed from 637 dots to 1 and
     verify_app_deterministic.py failed: it loads /app/?probe=1 and asserts the dot and halo counts,
     which it now JOINS from unified_sites.json and sites.json rather than naming as constants,
     because the halo count is the offered count and that moved from 246 to 236 when the 12 sites the
     agent loses on stopped being offered.
     It was right to. The 637-site footprint is the first thing the page claims.
     So the default selection drives the SEARCH BAR and the Configure panel, which is what was asked,
     while the MAP keeps showing everything until the reader actually touches something. `pristine`
     is that distinction, and any interaction clears it for good. */
  const [pristine, setPristine] = useState(
    () => !new URLSearchParams(typeof location === 'undefined' ? '' : location.search).get('facility'),
  )
  /* 🔴 READ, NEVER OWNED. `setStage()` in the lifted engine is the single owner of which stage is
     showing; this is the same read-only MutationObserver IntroLayer uses. A second copy of the stage
     in React state is the two-writers bug this file already refuses elsewhere. */
  const stage = useStage()
  /* Seeded from what the pre-paint script in index.html already wrote, so the first render agrees
     with the first paint. `installStageTheme` takes over immediately afterwards. */
  const [theme, setTheme] = useState<'dark' | 'light'>(currentTheme)

  /* 🔴 THIS EFFECT LOADS THE ARTEFACTS AND NOTHING ELSE, AND THAT IS THE FIX.
     It used to also call `loadHeadline(art.manifest, filters.facility)`, which is the very
     two-key-space bug the block below documents and repairs: `filters.facility` defaults to the
     UNIFIED map key `metro_ashburn`, while sites.json owns the artefacts under the METRO key
     `ashburn`. So `loadHeadline` looked for a site called `metro_ashburn`, did not find it, fell
     back to the shipped reference, and returned `isFallback: true` for the default site. The first
     screen then announced "This facility has no agent run published yet ... the shipped reference
     for ashburn" ON ASHBURN ITSELF, which is both false and the exact thing the notice exists to
     prevent. Photographed by the user, twice now.

     The `headlineKey` memo below already does the join correctly, and the effect after it already
     reloads on every selection change, including the first one. This call was therefore redundant
     as well as wrong, and being redundant it also RACED: both paths fetch the same three files and
     call `setH`, so which verdict survived depended on which fetch resolved last. Removing it
     leaves exactly one owner of the headline figures. */
  useEffect(() => {
    loadArtefacts()
      .then(setA)
      .catch((e: Error) => setErr(e.message))
  }, [])

  /* 🔴 THE FIGURES FOLLOW THE SELECTION. They did not, and that was a regression against the
     single-file page: loadHeadline ignored the chosen site and always read Ashburn's three artefacts,
     so picking an Alabama facility left Ashburn's numbers on every card. The user photographed it.
     Guarded on `a` so this does not race the first load, and loadHeadline falls back to the shipped
     reference for a facility with no run, reporting that through `isFallback`. */
  /* 🔴 TWO KEY SPACES, AND CONFLATING THEM PRODUCED A FALSE "no agent run" NOTICE.
     The map and the search bar address facilities by the UNIFIED key (`metro_ashburn`); sites.json,
     which owns the artefacts, addresses them by the metro key (`ashburn`). The unified entry carries
     `metro_key` for exactly this join. Passing the unified key straight to loadHeadline meant it was
     never found, so the shipped-reference fallback fired for the DEFAULT site and the first screen
     announced that Ashburn had no agent run. Measured in a screenshot. */
  const headlineKey = useMemo(() => {
    if (!a || !filters.facility) return DEFAULT_METRO
    const u = a.byKey.get(filters.facility) as
      { metro_key?: string; key?: string } | undefined
    return u?.metro_key || u?.key || filters.facility
  }, [a, filters.facility])

  useEffect(() => {
    if (!a) return
    let cancelled = false
    loadHeadline(a.manifest, headlineKey)
      .then((next) => { if (!cancelled) setH(next) })
      .catch(() => { /* a site with no artefacts keeps the figures already on screen */ })
    return () => { cancelled = true }
  }, [a, filters.facility])

  /* THE SAME TWO-TIER PROBE THE SINGLE-FILE PAGE USES. A truthy response means a server is attached
     at all; its flags then say whether a run can actually be requested. Under a static host there is
     no /api/health to answer and the fetch simply fails, which is REPLAY and not an error. */
  useEffect(() => {
    fetch(ART + 'api/health', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => setLive(j && j.live_available ? 'attached' : j ? 'replay' : 'replay'))
      .catch(() => setLive('replay'))
  }, [])

  /**
   * 🔴 THE DEFAULT THEME DEPENDS ON THE STAGE, AND ONLY THE DEFAULT.
   *
   * The user asked for two different things on two screens: "This page should be in dark mode by
   * default" of the landing page, and "the default mode when the user lands on this page should be
   * light mode" of the configure screen. Both add "the user can change it when they want to", so this
   * is a default and never a lock. A choice is recorded per STAGE GROUP, so pressing the toggle on
   * one screen cannot pin the other.
   *
   * 🔴 THE DECISION AND THE WRITE BOTH MOVED OUT OF REACT, AND THAT IS A FIX RATHER THAN TIDYING.
   * They used to be two effects here: one that watched `stage` and called `setTheme`, and one that
   * watched `theme` and assigned `documentElement.dataset.theme`. A `useEffect` runs AFTER paint, and
   * a `setState` arriving from `useStage`'s MutationObserver is not a discrete event, so React was
   * free to paint the new stage before the palette caught up. MEASURED with a per-frame recorder on
   * the way back from results to the landing page: TWO PAINTED FRAMES, 21 ms, of the dark landing
   * page rendered in the light palette. The user reported exactly that.
   * `lib/theme.ts` observes `body[data-stage]` itself and writes the attribute in the observer's own
   * callback, which is a microtask and therefore lands before the paint. This component now MIRRORS
   * that value for the one thing it needs it for: `EngineStage` repaints its canvases from the
   * `theme` prop. It no longer decides it and no longer writes it.
   */
  useEffect(() => installStageTheme(setTheme), [])

  /** The toggle. It records a preference for the group the reader is actually looking at, and
   *  `chooseTheme` applies it to the document at once so there is no frame of the old palette here
   *  either. */
  const onChooseTheme = useCallback(
    (next: 'dark' | 'light') => {
      chooseTheme(stage, next)
      setTheme(next)
    },
    [stage],
  )

  /* Stable identity, so SiteMap's create-once effect stays create-once even if its dependency
     array is ever widened again. Belt as well as braces: the ref inside SiteMap is the braces. */
  const onPick = useCallback(
    (key: string) => { setPristine(false); setFilters((f) => ({ ...f, facility: key })) },
    [],
  )

  /* Every route by which a reader changes a filter goes through here, so `pristine` cannot survive an
     interaction by being forgotten at one call site. */
  const onFilters = useCallback((next: Filters | ((f: Filters) => Filters)) => {
    setPristine(false)
    setFilters(next as Filters)
  }, [])

  /* "Configure the plant". The whole transition lives in lib/engine.ts because its ORDER carries a
     reason -- it is chooseSite()'s order from the page, and wire() inside it is what binds #runagent,
     #runagent2 and #backtopick. So the two run buttons on the next screens need no code here. */
  const onConfigure = useCallback(async (metroKey: string) => {
    setConfiguring(true)
    try {
      /* No React state to set. The engine's setStage() inside configureSite() is the single owner
         of what is visible, and it also writes <body data-stage>, which the CSS keys off. React
         mirroring it would be a second owner of one fact -- the exact bug the page documents. */
      await configureSite(metroKey)
    } finally {
      setConfiguring(false)
    }
  }, [])

  /* What the MAP and the count see: the same filters, minus a facility nobody chose. */
  const mapFilters = useMemo(
    () => (pristine ? { ...filters, facility: '' } : filters),
    [pristine, filters],
  )

  const selected = a && filters.facility ? a.byKey.get(filters.facility) ?? null : null

  const shown = useMemo(() => {
    if (!a) return 0
    return a.unified.sites.filter((s) => {
      if (mapFilters.facility) return s.key === mapFilters.facility
      if (mapFilters.state && (s.state || '??') !== mapFilters.state) return false
      if (mapFilters.operator && !s.operators?.includes(mapFilters.operator)) return false
      return true
    }).length
  }, [a, mapFilters])

  if (err) {
    return (
      <main className="mx-auto max-w-[1440px] px-4 py-16 sm:px-6">
        <p className="text-[14px]" style={{ color: 'var(--critical)' }}>
          <b>Could not load the artefacts:</b> {err}
        </p>
        <p className="mt-3 text-[12.5px] text-ink-2">
          The app reads the same <code>demo/*.json</code> files the single-file page reads. In
          development <code>vite.config.ts</code> serves them from <code>../demo</code>; a built
          bundle expects to sit beside them.
        </p>
      </main>
    )
  }

  return (
    /* id="app" because the engine does `$('#app').hidden = false` once it has booted; nothing in the
       engine ever sets it back to true, so hosting the attribute here is safe and keeps that lookup
       from returning null.
       ⚠ THE WIDTH IS THE PAGE'S WIDTH, and a stage-dependent one was removed rather than kept. It
       widened the container on the results stage on the theory that the panels needed more room --
       a theory I had not measured, and the engine's own .viz-root carries a 1180px measure anyway,
       so the widening did nothing except justify a duplicate copy of the stage in React state. */
    <main id="app" className="mx-auto max-w-[1440px] px-4 pb-16 sm:px-6">
      <button
        type="button"
        onClick={() => onChooseTheme(theme === 'dark' ? 'light' : 'dark')}
        aria-label={theme === 'dark' ? 'Switch to the light palette' : 'Switch to the dark palette'}
        className="fixed right-4 top-4 z-50 rounded-lg border border-hair bg-surface-1 p-2
                   text-ink-2 transition-colors hover:text-ink"
      >
        {/* 🔴 SVG, NOT A GLYPH. This was `theme === 'dark' ? '☀' : '☾'`, and in the light theme the
            crescent (U+263E) is not in Inter, so it fell back to a font that drew something closer to
            a capital C. Visible in the light-theme capture of the configure stage. An icon that
            depends on which fonts a reader happens to have is not an icon; these two paths depend on
            nothing. Both are 16px, currentColor, and inherit the button's hover transition. */}
        {theme === 'dark' ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4.2" />
            <path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2
                     M5.4 5.4l1.6 1.6M17 17l1.6 1.6M18.6 5.4L17 7M7 17l-1.6 1.6" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M20.2 14.6A8.4 8.4 0 1 1 9.4 3.8a6.6 6.6 0 0 0 10.8 10.8z" />
          </svg>
        )}
      </button>

      {/* 🔴 THE FORTYGUARD BANNER, muted and spanning the top. The wordmark ships as
          demo/fortyguard-logo.png, a real RGBA png, so low opacity is enough and no blend trick is
          needed. Fetched through ART like every other artefact, so it resolves at /app/ and at the
          demo root alike. alt is empty and it is aria-hidden: the product name is already the <h1>
          directly below, so announcing the logo would just repeat it. */}
      <div className="aa-banner">
        {/* 🔴 "POWERED BY" IS NOT DECORATION, IT IS DISAMBIGUATION. A bare FortyGuard wordmark at the
            top of a product called AGENTIC-ARBITER reads as though FortyGuard built this, which is
            not true and is not a claim to leave ambiguous in front of a judge. The relationship is
            real and specific: FortyGuard supplies the 2 m forecast field that the whole decision
            depends on, which the masthead states directly. So the mark is labelled.
            The alt text carries the same words, because with the label present the image is now
            informative rather than scenery. */}
        <span className="aa-banner-brand">
          <span className="aa-banner-by">Powered by</span>
          <img src={ART + 'fortyguard-logo.png'} alt="FortyGuard" />
        </span>
        <span className="aa-banner-sub">Free-cooling decisions, hour by hour</span>
        {/* WHERE THE STEPPER GOES. EngineStage moves the engine's own #rail node in here after the
            markup is injected, so the progress control lives in the header on every stage instead of
            in the content flow. An empty div until then, and harmless if the move ever fails. */}
        <div id="aa-railslot" />
      </div>

      {/* The masthead is on every stage: it carries the headline and the live-agent line. */}
      {/* The impact figures are passed in rather than typed into the masthead, so the headline
          cannot state a number the artefacts do not support. */}
      {/* 🔴 ONE GRID, NOT A FLOATING CARD, AND THAT IS WHAT FIXES THE ALIGNMENT.
          The cards used to be `position: absolute; right: 8px`, which meant they were laid out against
          whatever the nearest positioned ancestor happened to be rather than against the container
          everything else sits in. MEASURED by the user at 1920: the cards' right edge landed at 1672
          and the filter panel's at 1650, a visible 22 px overhang, with a 360 px gutter beside 347 px
          cards -- a gap wider than the thing it was separating.
          As a real two-column grid the alignment is not something to get right, it is something that
          cannot go wrong: both columns end where the container ends, so the cards and the filter panel
          share an edge by construction. The cards also take the width the gutter was wasting. */}
      <div className="aa-mast-grid">
        <div className="aa-mast-col">
          <Masthead live={live} cutPct={h?.cutPct} gainHPerYear={h?.gainHPerYear} />
        </div>

        {/* WHAT IS ACTUALLY SHIPPED, and what it is worth. Rendered here rather than further down so
            it is a COLUMN of this grid; it was previously inside the loading guard below, which is why
            it had to position itself absolutely to appear beside the text at all.

            🔴 THE VALUE CARD READS THE PORTFOLIO, NOT THE SELECTED SITE, AND THAT WAS THE BUG.
            It used to be handed `h`, the Headline for whichever site is selected, so it restated
            Ashburn's $334k-$967k, its 6.2 % and its 405 chiller-hours -- the same four numbers the KPI
            tiles print a few hundred pixels below, for the same one site. Two cards saying one site's
            figures is not a portfolio summary, it is a duplicate. `a.portfolio` is the sum over all
            the OWN artefacts of the 238 sites the agent is offered on, written by
            tools/portfolio_totals.py. 12 further built sites are excluded; see ScopeBubble.

            EVERY NUMBER IS READ, NEVER TYPED: `offerable` is the flag sites.json sets on a site with a
            full run, unified_sites.json is the mapped universe, and the portfolio fields come from
            demo/portfolio.json. */}
        {a && (
          <ScopeBubble
            shipped={a.manifest.sites.filter((x) => (x as { offerable?: boolean }).offerable).length}
            mapped={a.unified.sites.length}
            p={a.portfolio}
          />
        )}
      </div>

      {/* WHERE THE AGENT-LOOP DIAGRAM GOES, on the landing stage only. An empty div until the intro
          layer portals into it, and harmless if that never happens -- the same arrangement as
          #aa-railslot above, which EngineStage fills with the engine's own stepper.
          It is here rather than inside IntroLayer's own output because IntroLayer renders at the END
          of this component, next to the modal, and the diagram belongs in the document flow directly
          under the masthead it explains. */}
      <div id="aa-ringslot" />

      {/* 🔴 THE GATE IS RENDERED BEFORE THE DATA GUARD, AND THAT ORDER IS THE BUG FIX.
          The user, with a screen recording of the deployed site: "The site load with different page
          than it is supposed to. It should land directly on the page with the globe without showing
          the other page before."
          It was rendered at the END of the `!a || !h` ternary's else-arm, so the gate could not exist
          until BOTH the artefact bundle and the three headline JSONs had been fetched. Until then
          React painted the OTHER arm of that same ternary, and that is the page they saw: the
          FortyGuard banner, the wordmark, the four bullets, both value cards, the REPLAY line and
          "Loading saved data...".
          MEASURED on three warm loads: the wrong page held the glass for 451, 470 and 591 ms, and 717
          ms on a fourth. Confirmed causal by holding backtest.json, trace.json and money.json for 3 s
          with CDP: the gate's DOM insert moved from 1,253 ms to 3,876 ms, +2.62 s for a +2.9 s hold.
          Their own recording shows the same thing on the deployed site at t = 1.323 s.
          Rendered here, the gate is in React's FIRST commit, so the first contentful frame of the
          document is the splash and everything else is painted UNDERNEATH an opaque
          `position: fixed; inset: 0; z-index: 200` overlay. Measured on a patched build: the gate
          enters the DOM in the same tick as `#root`'s first child, and no frame contains the masthead.

          ⚠ "PLACED LAST SO THE GATE IS OVER THE PAGE IN PAINT ORDER" WAS THE OLD REASON FOR THE OLD
          POSITION, AND IT WAS NOT LOAD-BEARING. `#app` becomes a stacking context under
          `body[data-aa-intro] #app { position: relative; z-index: 1 }`, and the gate's
          `z-index: 200 !important` wins inside it regardless of DOM order: measured across 243
          samples spanning 417 ms to 5,002 ms on the patched build, the gate was the topmost element
          at 9 of 9 hit-test points every time, including after the map and the cards had rendered.

          ⚠ ONE NARROW CONSEQUENCE, NAMED RATHER THAN DISCOVERED LATER. `launch.ts` looks up
          `[data-show="pick"]` and `timeline.ts` looks up `[data-aa-hero="cta"]`, and both live inside
          the guard below, so between first paint and the artefacts landing they are null. Every use
          of both is null-guarded, so the sequence degrades to a plain fade instead of a crossfade.
          Two things keep it out of reach anyway: the call to action is disabled until the audio has
          preloaded (capped at 1,500 ms) and the sequence runs 6.876 s before it hands over, against
          headline JSONs that resolved at 487 ms warm.

          🔴 WRAPPED, because a decorative layer must not be able to blank the product. A throw inside
          IntroLayer's subtree used to unmount the entire tree: measured with WebGL disabled, `#root`
          went to zero children. See IntroBoundary. */}
      <IntroBoundary>
        <IntroLayer />
      </IntroBoundary>

      {!a || !h ? (
        <p className="text-[13px] text-muted">Loading saved data…</p>
      ) : (
        <>
          {/* 🔴 data-show="pick", NOT a conditional render. The engine's setStage() walks
              [data-show] and sets .hidden, and it stays the single owner of what is on screen. If
              React also unmounted this subtree there would be two owners of one decision, which is
              precisely the bug demo/index.html documents at length: the last writer wins, and which
              one that is depends on render timing. So React labels its screen and lets setStage()
              decide. The map instance survives inside a hidden container, so returning to the pick
              screen does not rebuild it. */}
          {/* WHEN THE SELECTED FACILITY HAS NO RUN, say whose figures are on the cards. Showing the
              shipped reference silently is the bug this replaces: an Alabama site was selected above
              Ashburn's numbers with nothing saying so. */}
          {h.isFallback && (
            <p className="aa-fallback">
              This facility has no agent run published yet, so the figures below are the shipped
              reference for <b>{h.usedKey}</b>. Pick a site marked ready to run to see its own.
            </p>
          )}

          <div data-show="pick">
            <SearchBar a={a} filters={filters} onChange={onFilters} shown={shown} />
            {/* 🔴 THE PATH FORWARD. The first version of this screen let a reader select a data
                centre and then offered nothing; the second offered a link back to the old page.
                This one calls the engine. */}
            {selected && (
              <SelectedBar
                a={a}
                facility={selected}
                busy={configuring}
                onConfigure={onConfigure}
                onClear={() => setFilters((f) => ({ ...f, facility: '' }))}
              />
            )}
            <div className="mt-4">
              <KpiCards h={h} />
            </div>
            <div className="mt-4">
              <SiteMap a={a} filters={mapFilters} onPick={onPick} />
            </div>
            {/* 🔴 THE FIVE AGENT STAGES USED TO RENDER HERE, AND ARE NOW REMOVED FROM THE PAGE.
                Moved out of the splash on 2026-08-29 at the user's instruction, then removed
                outright later the same day: "remove this", with a screenshot of this section.
                ⚠ `components/StageRows.tsx` and `stagerows.css` ARE STILL IN THE REPOSITORY and are
                deliberately not deleted, because the instruction that moved them here was explicit
                that the component and its data wiring must not be deleted. Those two instructions
                are only compatible one way: gone from the page, kept on disk. Deleting the files is
                a one-line decision the user can make; putting the section back is this one JSX tag.
                The five stage names still appear in the product, in `intro/Pipeline.tsx`'s diagram
                and in `AgentConsole.tsx`'s stage ticks, so nothing about the loop is now unstated. */}
          </div>

          {/* THE OTHER TWO STAGES: the page's own markup, drawn by the page's own engine. Rendered
              always and hidden by setStage(), never conditionally mounted -- see EngineStage.tsx for
              why React must not re-render this subtree. */}
          <EngineStage
            sites={a.manifest as unknown as { sites: Array<Record<string, unknown>> }}
            theme={theme}
            siteKey={DEFAULT_METRO}
          />

          {/* Where the folded prose opens. Listens for an event, so the buttons injected into engine
              DOM can reach it without React managing those nodes. */}
          <DetailModal />

        </>
      )}
    </main>
  )
}
