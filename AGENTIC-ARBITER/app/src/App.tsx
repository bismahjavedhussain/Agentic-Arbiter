import { useCallback, useEffect, useMemo, useState } from 'react'
import { Masthead } from './components/Masthead'
import { SearchBar, type Filters } from './components/SearchBar'
import { SelectedBar } from './components/SelectedBar'
import { KpiCards } from './components/KpiCards'
import { SiteMap } from './components/SiteMap'
import { ART, loadArtefacts, type Artefacts } from './lib/artefacts'
import { loadHeadline, type Headline } from './lib/headline'

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
      facility: q.get('facility') || '',
    }
  })
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
    (key: string) => setFilters((f) => ({ ...f, facility: key })),
    [],
  )

  const selected = a && filters.facility ? a.byKey.get(filters.facility) ?? null : null

  const shown = useMemo(() => {
    if (!a) return 0
    return a.unified.sites.filter((s) => {
      if (filters.facility) return s.key === filters.facility
      if (filters.state && (s.state || '??') !== filters.state) return false
      if (filters.operator && !s.operators?.includes(filters.operator)) return false
      return true
    }).length
  }, [a, filters])

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
    <main className="mx-auto max-w-[1180px] px-4 pb-16 sm:px-6">
      <button
        type="button"
        onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        aria-label={theme === 'dark' ? 'Switch to the light palette' : 'Switch to the dark palette'}
        className="fixed right-4 top-4 z-50 rounded-lg border border-hair bg-surface-1 p-2
                   text-ink-2 transition-colors hover:text-ink"
      >
        {theme === 'dark' ? '☀' : '☾'}
      </button>

      <Masthead live={live} />

      {!a || !h ? (
        <p className="text-[13px] text-muted">Loading saved data…</p>
      ) : (
        <>
          <SearchBar a={a} filters={filters} onChange={setFilters} shown={shown} />
          {/* 🔴 THE PATH FORWARD, which the first version of this screen simply did not have. A
              reader could select a data centre and then had nothing to do with it. See
              SelectedBar.tsx for why the button hands off to demo/index.html rather than pretending
              the configure stage has been rebuilt here. */}
          {selected && (
            <SelectedBar
              a={a}
              facility={selected}
              onClear={() => setFilters((f) => ({ ...f, facility: '' }))}
            />
          )}
          <div className="mt-4">
            <KpiCards h={h} />
          </div>
          <div className="mt-4">
            <SiteMap a={a} filters={filters} onPick={onPick} />
          </div>
        </>
      )}
    </main>
  )
}
