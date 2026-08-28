import { useCallback, useEffect, useMemo, useState } from 'react'
import { Masthead } from './components/Masthead'
import { SearchBar, type Filters } from './components/SearchBar'
import { SelectedBar } from './components/SelectedBar'
import { KpiCards } from './components/KpiCards'
import { SiteMap } from './components/SiteMap'
import { EngineStage } from './components/EngineStage'
import { DetailModal } from './components/DetailModal'
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
     verify_app_deterministic.py failed: it loads /app/?probe=1 and asserts 637 dots / 246 halos.
     It was right to. The 637-site footprint is the first thing the page claims.
     So the default selection drives the SEARCH BAR and the Configure panel, which is what was asked,
     while the MAP keeps showing everything until the reader actually touches something. `pristine`
     is that distinction, and any interaction clears it for good. */
  const [pristine, setPristine] = useState(
    () => !new URLSearchParams(typeof location === 'undefined' ? '' : location.search).get('facility'),
  )
  const [theme, setTheme] = useState<'dark' | 'light'>(
    () => (document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'),
  )

  useEffect(() => {
    loadArtefacts()
      .then(async (art) => {
        setA(art)
        setH(await loadHeadline(art.manifest))
      })
      .catch((e: Error) => setErr(e.message))
  }, [])

  /* THE SAME TWO-TIER PROBE THE SINGLE-FILE PAGE USES. A truthy response means a server is attached
     at all; its flags then say whether a run can actually be requested. Under a static host there is
     no /api/health to answer and the fetch simply fails, which is REPLAY and not an error. */
  useEffect(() => {
    fetch(ART + 'api/health', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => setLive(j && j.live_available ? 'attached' : j ? 'replay' : 'replay'))
      .catch(() => setLive('replay'))
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('aa-theme', theme) } catch { /* private mode; the default holds */ }
  }, [theme])

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
      <main className="mx-auto max-w-[1180px] px-4 py-16 sm:px-6">
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
    <main id="app" className="mx-auto max-w-[1180px] px-4 pb-16 sm:px-6">
      <button
        type="button"
        onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
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
        <img src={ART + 'fortyguard-logo.png'} alt="" aria-hidden="true" />
        <span className="aa-banner-sub">Free-cooling decisions, hour by hour</span>
        {/* WHERE THE STEPPER GOES. EngineStage moves the engine's own #rail node in here after the
            markup is injected, so the progress control lives in the header on every stage instead of
            in the content flow. An empty div until then, and harmless if the move ever fails. */}
        <div id="aa-railslot" />
      </div>

      {/* The masthead is on every stage: it carries the headline and the live-agent line. */}
      {/* The impact figures are passed in rather than typed into the masthead, so the headline
          cannot state a number the artefacts do not support. */}
      <Masthead live={live} cutPct={h?.cutPct} gainHPerYear={h?.gainHPerYear} />

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
