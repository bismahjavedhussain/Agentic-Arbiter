import { useEffect, useRef, useState } from 'react'
// maplibre-gl v6 has NO default export -- it is 85 named exports and nothing else. `import
// maplibregl from` typechecks against older versions and fails here, so the four things this file
// uses are named explicitly. Verified by listing the module's own keys rather than assumed.
import { LngLatBounds, Map as MLMap, NavigationControl, Popup, setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
// 🔴 maplibre 6 SHIPS ITS WORKER AS A SEPARATE MODULE and will not guess where it is. Without this
// line the GeoJSON source is handed all 637 features, reports `loaded() === false` for ever, tiles
// none of them, and raises NO error -- because raster tiles are decoded on the main thread, so the
// basemap draws perfectly and the map looks fine with nothing on it.
// `?url` makes Vite emit the worker as an asset and hand back its URL, which works in dev and in a
// built dist/ dropped anywhere, since `base` is './'.
// `?worker&url`, NOT `?url`. `?url` copies the file verbatim and does not follow its imports,
// and maplibre's worker begins `import{B as e,...}` from a SHARED chunk that then is not in the
// bundle: the worker 404s on its own dependency and dies without raising anything the map can
// report. `?worker` bundles the worker together with its dependencies, and the added `&url`
// hands back the URL of that self-contained bundle, which is what setWorkerUrl wants.
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

setWorkerUrl(maplibreWorkerUrl)
import {
  CATEGORY_LABEL, facilityName, int, isReady, stateName, type Artefacts,
} from '../lib/artefacts'
import type { Filters } from './SearchBar'
// @types/geojson exports its types as a MODULE; there is no global `GeoJSON` namespace to
// reference, so the one type this file needs is imported by name.
import type { FeatureCollection, Point } from 'geojson'

const SRC = 'facilities'
const L_HALO = 'facility-halo'
const L_DOT = 'facility-dot'

/* THE BASEMAP IS OPENSTREETMAP, IN COLOUR, at the user's direction. The previous design pushed it to
   grey with maplibre `raster-*` paint so the dots would be the brightest thing in the frame; the brief
   asks for the vibrant tiles back, so no exposure paint is applied at all.
   Keyless on purpose. CARTO's tiles began requiring an API key and returned HTTP 200 with "API KEY
   REQUIRED" watermarked across every tile, which is worse than a failure because it looks like one. */
const OSM_TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const OSM_ATTRIB = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/* Radius by category, colour by runnability, and a third colour for an operator match. Small,
   because the opening view is 637 points across a continent and the geography under them has to stay
   readable between the marks. */
const R = { cluster: 6.5, pair: 5, single: 4 }

const reduced = () => {
  try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches } catch { return false }
}

function toGeoJSON(a: Artefacts): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: a.unified.sites.map((f) => ({
      type: 'Feature' as const,
      // 🔴 [lon, lat]. The artefacts store `centre` as [lat, lon]; GeoJSON is the other way round.
      // Getting this backwards puts every American data centre in the Indian Ocean.
      geometry: { type: 'Point' as const, coordinates: [f.centre[1], f.centre[0]] },
      properties: {
        key: f.key,
        state: f.state || '??',
        category: f.category,
        // Computed from the MANIFEST, not from unified_sites.json's baked `status` string. The old
        // map coloured its dots from that string: the caption said 246 runnable and 3 were green.
        runnable: isReady(a, f) ? 1 : 0,
        // A delimited string rather than an array, because maplibre's `in` works on strings and
        // `index-of` gives a substring test. Delimiters at both ends so "AWS" cannot match "AWS UK".
        operators: `|${(f.operators || []).join('|')}|`,
      },
    })),
  }
}

function popupHTML(title: string, lines: string[], lead?: string) {
  const head = lead
    ? `<div style="font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;
         color:var(--muted);font-weight:600;margin-bottom:4px">${lead}</div>`
    : ''
  return `${head}<div style="font-weight:700;font-size:13px;letter-spacing:-.01em;
      margin-bottom:${lines.length ? '5px' : '0'}">${title}</div>${lines
    .map((l) => `<div style="font-size:11.5px;color:var(--text-secondary);line-height:1.45">${l}</div>`)
    .join('')}`
}

export function SiteMap({ a, filters, onPick }: {
  a: Artefacts
  filters: Filters
  onPick: (key: string) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const map = useRef<MLMap | null>(null)
  const popup = useRef<Popup | null>(null)
  /* 🔴 THE CLICK HANDLER LIVES IN A REF, and this is not a micro-optimisation.
     `onPick` arrives as an inline arrow from App, so it is a NEW FUNCTION IDENTITY on every render.
     With it in the create-once effect's dependency array, that effect tore the map down and built a
     new one on every render -- and under StrictMode, which double-invokes effects in development,
     twice over. The visible symptom was a basemap with none of the 637 facilities on it and no
     opening popup: the map was being destroyed before it finished adding its own data.
     A ref holds the latest callback without participating in dependencies. */
  const pick = useRef(onPick)
  useEffect(() => { pick.current = onPick }, [onPick])
  const [failed, setFailed] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  /* Kept separate on purpose: a tile that will not load is a network condition, and a style or
     source error is a defect. Conflating them is how the second hides behind the first. */
  /* Whether a filter has moved the camera away from the opening view, so clearing the filters
     returns it and ARRIVING does not touch it. */
  const moved = useRef(false)
  const [errs, setErrs] = useState<string[]>([])
  const [tiles, setTiles] = useState(0)

  /* ---- create once ------------------------------------------------------------------------- */
  useEffect(() => {
    if (!host.current || map.current) return
    let m: MLMap
    try {
      m = new MLMap({
        container: host.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: [OSM_TILES],
              tileSize: 256,
              maxzoom: 19,
              attribution: OSM_ATTRIB,
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
        },
        // THE WHOLE COUNTRY, and deliberately not zoomed in. The brief: "Display the entire US map...
        // Do not zoom in yet; keep the full US view visible."
        center: [-96, 38.5],
        zoom: 3.5,
        attributionControl: { compact: true },
      })
    } catch (e) {
      setFailed(`the map failed to start (${(e as Error).message})`)
      return
    }
    map.current = m
    m.addControl(new NavigationControl({ showCompass: false }), 'top-right')

    /* 🔴 KEEP THE ERRORS. Registering a handler REPLACES maplibre's default, which logs to the
       console, so a handler that discards makes the map quieter than having none at all. That is
       exactly what the first version of this did, and it hid the reason the facility source held
       zero features.
       Tile fetch failures are expected and separated out: the page is required to work with a dead
       tile CDN, because the 637 facilities are GeoJSON that ships with the app. Everything else is
       kept and surfaced through the ?probe=1 diagnostic. */
    m.on('error', (e) => {
      const msg = String((e as unknown as { error?: Error }).error?.message ?? e ?? '')
      const isTile = msg.includes('Failed to fetch') || msg.includes('tile')
      if (isTile) {
        setTiles((n) => n + 1)
        return
      }
      setErrs((prev) => (prev.includes(msg) ? prev : [...prev, msg].slice(0, 6)))
    })

    const addData = () => {
      // 🔴 GATED ON THE PARSED STYLE, NOT ON `isStyleLoaded()`. That returns false while ANY source
      // still has tiles in flight, and the basemap is a raster source pointing at OSM: on a network
      // that blocks or throttles those tiles it stays false forever and the facilities are never
      // added at all. This exact gate has bitten the single-file page twice.
      if (!m.getLayer('osm') || m.getSource(SRC)) return
      m.addSource(SRC, { type: 'geojson', data: toGeoJSON(a) })

      // The glow, under the runnable points only. Colour already carries that distinction, but
      // colour alone cannot survive a colourful basemap: among 637 points the clickable ones have to
      // be where the eye lands first.
      m.addLayer({
        id: L_HALO, type: 'circle', source: SRC,
        filter: ['==', ['get', 'runnable'], 1],
        paint: {
          'circle-radius': ['match', ['get', 'category'],
            'cluster', R.cluster + 6, 'pair', R.pair + 5, R.single + 5],
          'circle-color': '#34d399',
          'circle-opacity': 0.3,
          'circle-blur': 0.6,
        },
      })
      m.addLayer({
        id: L_DOT, type: 'circle', source: SRC,
        paint: {
          'circle-radius': ['match', ['get', 'category'],
            'cluster', R.cluster, 'pair', R.pair, R.single],
          'circle-color': '#8d8d96',
          // A white casing, so a dot stays a dot over a coloured map rather than dissolving into it.
          'circle-stroke-width': 1.4,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-opacity': 0.9,
          'circle-opacity': 0.95,
        },
      })

      for (const layer of [L_DOT]) {
        m.on('mouseenter', layer, () => { m.getCanvas().style.cursor = 'pointer' })
        m.on('mouseleave', layer, () => { m.getCanvas().style.cursor = '' })
        m.on('click', layer, (ev) => {
          const k = ev.features?.[0]?.properties?.key as string | undefined
          if (k) pick.current(k)
        })
      }
      setReady(true)
      /* 🔴 A TEST HOOK, and the React equivalent of something the single-file page got for free.
         There, `NATMAP` was a module-scope global and testing/verify_state_filter.py reached it by
         bare identifier to read which layers were visible and how many facilities were painted. A
         bundled module scope has no such handle, so the map is published deliberately. Without it
         there is no way to assert what the map DREW rather than what it was configured to draw, and
         that distinction has already caught two real defects in this project. */
      ;(window as unknown as { __AA_MAP?: MLMap }).__AA_MAP = m
    }
    m.on('styledata', addData)
    m.once('load', addData)

    return () => { popup.current?.remove(); m.remove(); map.current = null }
    // `a` only. The artefacts are loaded once and never replaced; see the note on `pick` above
    // for why the callback is deliberately absent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a])

  /* ---- filters: fit to a state, highlight an operator, fly to a facility ------------------- */
  useEffect(() => {
    const m = map.current
    if (!m || !ready) return
    const dur = reduced() ? 0 : 700

    /* OPERATOR HIGHLIGHT, in a third colour. Terracotta is not an arbitrary pick: it is
       `--series-2`, the frozen half of a pair validated with CIEDE2000 plus a Vienot dichromat
       simulation, so it stays distinguishable from the emerald and the grey for a colourblind
       reader as well as a trichromatic one. */
    const opMatch: unknown[] = filters.operator
      ? ['>=', ['index-of', `|${filters.operator}|`, ['get', 'operators']], 0]
      : ['==', 1, 0]
    m.setPaintProperty(L_DOT, 'circle-color', [
      'case',
      opMatch, '#eb6834',
      ['==', ['get', 'runnable'], 1], '#34d399',
      '#8d8d96',
    ] as never)
    m.setPaintProperty(L_DOT, 'circle-radius', [
      'case',
      opMatch, ['match', ['get', 'category'],
        'cluster', R.cluster + 2.5, 'pair', R.pair + 2.5, R.single + 2.5],
      ['match', ['get', 'category'], 'cluster', R.cluster, 'pair', R.pair, R.single],
    ] as never)

    /* WHICH FACILITIES SURVIVE THE FILTER. A maplibre expression, so the source keeps all 637
       features and the layers decide what to draw; filtering by rebuilding the GeoJSON would mean
       re-uploading a source on every keystroke. */
    const clauses: unknown[] = ['all']
    if (filters.state) clauses.push(['==', ['get', 'state'], filters.state])
    if (filters.facility) clauses.push(['==', ['get', 'key'], filters.facility])
    const expr = clauses.length > 1 ? clauses : null
    m.setFilter(L_DOT, expr as never)
    m.setFilter(L_HALO, (expr
      ? ['all', ['==', ['get', 'runnable'], 1], ...clauses.slice(1)]
      : ['==', ['get', 'runnable'], 1]) as never)

    /* FACILITY: fly to the point and name it. */
    if (filters.facility) {
      const f = a.byKey.get(filters.facility)
      if (f) {
        popup.current?.remove()
        popup.current = new Popup({ closeOnClick: false, offset: 12, maxWidth: '330px',
        /* 🔴 focusAfterOpen: false IS THE WHOLE FIX FOR "the page loads already scrolled".
           MEASURED with scratchpad/reloadprobe.py, which patched scrollTo, scrollIntoView and
           focus and sampled scrollY every 20 ms:

               focus on maplibregl-popup-close-button (+287ms)   y=0
                  at HTMLElement.focus ... at AA._focusFirstElement ...
               *** LEFT THE TOP *** (+307ms)                     y=501

           MapLibre opens a popup and calls its own _focusFirstElement(), which focuses the
           close button. The browser then scrolls that element into view, dragging the whole
           page down to the map. A facility is preselected, so the popup opens on load and the
           first thing a reader sees is a page already scrolled past the headline.

           It is also the other half of the ALTERNATING jump on changing site: the popup pulled
           DOWN to the map while setStage's scroll-to-top pulled UP, and which one a reader saw
           depended on ordering. Neither was scroll restoration, which is what I assumed first
           and fixed second: that guess is recorded in noscrolljump.ts because turning
           scrollRestoration to manual is correct on its own merits and changed nothing here.

           The popup stays keyboard-reachable: it is in the DOM with a real close button, and a
           reader who tabs to it still gets it. What is given up is the popup STEALING focus the
           moment it opens, which is what moves the viewport. */
        focusAfterOpen: false })
          .setLngLat([f.centre[1], f.centre[0]])
          .setHTML(popupHTML(
            `${facilityName(f)}, ${stateName(f.state)}`,
            [
              `${CATEGORY_LABEL[f.category] || f.category} · ${int(f.n_tagged)} OSM-tagged building${f.n_tagged === 1 ? '' : 's'}`,
              (f.operators || []).length ? `Operated by ${f.operators.join(', ')}` : '',
              isReady(a, f) ? 'Ready to run' : 'Real candidate, no agent run published yet',
            ].filter(Boolean),
            'The data centre you selected',
          ))
          .addTo(m)
        moved.current = true
        m.easeTo({ center: [f.centre[1], f.centre[0]], zoom: 12, duration: dur })
      }
      return
    }

    /* STATE: fit the camera to that state's own facilities. */
    popup.current?.remove()
    popup.current = null
    if (filters.state) {
      const rows = a.unified.sites.filter(
        (s) => (s.state || '??') === filters.state &&
               (!filters.operator || s.operators?.includes(filters.operator)),
      )
      if (rows.length) {
        const b = new LngLatBounds()
        for (const s of rows) b.extend([s.centre[1], s.centre[0]])
        // maxZoom caps a single-result fit, which would otherwise fly to street level and take
        // every reference the reader had with it.
        moved.current = true
        m.fitBounds(b, { padding: 56, maxZoom: 9, duration: dur })
      }
      return
    }

    /* NOTHING SELECTED: the whole country, and the shipped site named on it.
       🔴 THIS BRANCH OWNS THE OPENING POPUP, and it did not always. It used to live in its own
       effect, which ran first and was then undone by this one's `popup.current?.remove()` -- two
       effects writing one mutable ref, so the popup a reader is meant to see on arrival never
       survived mount. One owner, one place it is created, one place it is removed.

       AND THE CAMERA DOES NOT MOVE ON ARRIVAL. The brief is explicit: "Display the entire US map...
       Do not zoom in yet; keep the full US view visible." The easeTo below only runs when a filter
       has just been CLEARED, which is a return journey rather than an arrival. */
    const ash = a.unified.sites.find((x) => x.metro_key === 'ashburn')
    if (ash) {
      const c = a.manifest.sites.find((x) => x.key === 'ashburn')?.committed
      const pair =
        c?.source_name && c?.receptor_name ? `${c.source_name} → ${c.receptor_name}` : ''
      popup.current = new Popup({ closeOnClick: false, offset: 12, maxWidth: '330px',
        /* 🔴 focusAfterOpen: false IS THE WHOLE FIX FOR "the page loads already scrolled".
           MEASURED with scratchpad/reloadprobe.py, which patched scrollTo, scrollIntoView and
           focus and sampled scrollY every 20 ms:

               focus on maplibregl-popup-close-button (+287ms)   y=0
                  at HTMLElement.focus ... at AA._focusFirstElement ...
               *** LEFT THE TOP *** (+307ms)                     y=501

           MapLibre opens a popup and calls its own _focusFirstElement(), which focuses the
           close button. The browser then scrolls that element into view, dragging the whole
           page down to the map. A facility is preselected, so the popup opens on load and the
           first thing a reader sees is a page already scrolled past the headline.

           It is also the other half of the ALTERNATING jump on changing site: the popup pulled
           DOWN to the map while setStage's scroll-to-top pulled UP, and which one a reader saw
           depended on ordering. Neither was scroll restoration, which is what I assumed first
           and fixed second: that guess is recorded in noscrolljump.ts because turning
           scrollRestoration to manual is correct on its own merits and changed nothing here.

           The popup stays keyboard-reachable: it is in the DOM with a real close button, and a
           reader who tabs to it still gets it. What is given up is the popup STEALING focus the
           moment it opens, which is what moves the viewport. */
        focusAfterOpen: false })
        .setLngLat([ash.centre[1], ash.centre[0]])
        .setHTML(popupHTML(
          'Ashburn, Virginia',
          [
            pair,
            c?.facade_gap_m ? `facades ${c.facade_gap_m} m apart` : '',
            'Ready to run · click any point to open its own agent run',
          ].filter(Boolean),
          'The shipped site',
        ))
        .addTo(m)
    }
    if (moved.current) m.easeTo({ center: [-96, 38.5], zoom: 3.5, duration: dur })
    moved.current = false
  }, [ready, a, filters.state, filters.operator, filters.facility])

  /* ---- the test surface ---------------------------------------------------------------------
     🔴 A PROBE THE VERIFIERS CAN READ, gated on `?probe=1` so it never exists for a reader.
     The single-file page exposed `NATMAP` as a module-scope global and
     testing/verify_state_filter.py reached it by bare identifier, which is how 62 assertions about
     what the map DREW rather than what it was configured to draw became possible. A bundled module
     scope has no such handle, and Chrome's --evaluate-on-new-document-file did not fire in this
     environment, so the page publishes the facts itself.
     It reports what cannot be inferred from the DOM: how many features the source holds, how many
     the layer actually painted, the live filter, and the camera. */
  const probing = typeof location !== 'undefined' && location.search.includes('probe')
  // `includes`, not a regex: this line was written through a shell heredoc that ate a
  // backslash, so `/\bprobe\b/` became a regex containing two literal BACKSPACE characters.
  // It compiled and never matched, which meant `?probe=1` silently did nothing.

  if (failed) {
    return (
      <div className="glass rounded-2xl p-4 text-[12.5px] text-ink-2">
        <b className="text-ink">Map not shown, {failed}.</b> This is the only panel that needs the
        network; everything else replays saved files, so nothing else is affected.
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-hair">
      <div ref={host} className="h-[clamp(340px,52vh,620px)] w-full" />
      <Legend />
      {probing && <MapProbe map={map} ready={ready} errs={errs} tiles={tiles} />}
    </div>
  )
}

function MapProbe({ map, ready, errs, tiles }: {
  map: React.RefObject<MLMap | null>
  ready: boolean
  errs: string[]
  tiles: number
}) {
  const [text, setText] = useState('')
  useEffect(() => {
    let alive = true
    const tick = () => {
      if (!alive) return
      const m = map.current
      const out: Record<string, unknown> = {
        ready, hasMap: !!m, mapErrors: errs, tileErrors: tiles,
      }
      if (m) {
        try {
          const st = m.getStyle()
          const distinct = (layer: string) =>
            new Set(
              m.queryRenderedFeatures({ layers: [layer] })
                .map((f) => f.properties?.key)
                .filter(Boolean),
            ).size
          Object.assign(out, {
            layers: (st.layers || []).map((l) => l.id),
            sources: Object.keys(st.sources || {}),
            hasSource: !!m.getSource(SRC),
            styleLoaded: m.isStyleLoaded(),
            tilesLoaded: m.areTilesLoaded?.() ?? null,
            zoom: +m.getZoom().toFixed(2),
            // TILED vs GIVEN. querySourceFeatures reads built tiles; `_data` is what the
            // source was handed. 0 tiled with N given means the worker failed, which is a
            // completely different problem from 0 given.
            srcFeatures: m.getSource(SRC) ? m.querySourceFeatures(SRC).length : -1,
            srcGiven: (() => {
              // maplibre 6 keeps inline data at `_data.geojson`, per its own type declaration:
              // `_data: ExactlyOne<{url, geojson, updateable}>`. An earlier version of this probe
              // read `_data.features` and reported -1, which looked like "no data" and was not.
              const src = m.getSource(SRC) as unknown as {
                _data?: { geojson?: { features?: unknown[] } }
                loaded?: () => boolean
              } | undefined
              return src?._data?.geojson?.features?.length ?? -1
            })(),
            srcLoaded: (() => {
              const src = m.getSource(SRC) as unknown as { loaded?: () => boolean } | undefined
              try { return src?.loaded?.() ?? null } catch { return 'threw' }
            })(),
            paintedDots: m.getLayer(L_DOT) ? distinct(L_DOT) : -1,
            paintedHalo: m.getLayer(L_HALO) ? distinct(L_HALO) : -1,
            dotFilter: m.getLayer(L_DOT) ? JSON.stringify(m.getFilter(L_DOT)) : null,
            // The operator highlight is a PAINT expression, so the only honest way to check it
            // is to report the expression and count the features it selects.
            dotColor: m.getLayer(L_DOT)
              ? JSON.stringify(m.getPaintProperty(L_DOT, 'circle-color')).slice(0, 220)
              : null,
            popups: document.querySelectorAll('.maplibregl-popup').length,
            popupText: (document.querySelector('.maplibregl-popup-content') as HTMLElement | null)
              ?.innerText?.replace(/\s+/g, ' ')?.slice(0, 180) ?? '',
          })
        } catch (e) {
          out.probeErr = String((e as Error).message)
        }
      }
      setText(JSON.stringify(out))
      window.setTimeout(tick, 400)
    }
    tick()
    return () => { alive = false }
  }, [map, ready, errs, tiles])
  return <div id="AAPROBE" style={{ display: 'none' }}>{text}</div>
}

function Legend() {
  return (
    <div className="glass pointer-events-none absolute bottom-3 left-3 rounded-xl px-3 py-2
                    text-[11px] leading-[1.6]">
      <Row c="var(--good)" t="Ready to run" />
      <Row c="var(--axis)" t="Real candidate, not yet built" />
      <Row c="var(--series-2)" t="Matches the chosen operator" />
    </div>
  )
}
function Row({ c, t }: { c: string; t: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-[8px] w-[8px] rounded-full border border-white/70"
            style={{ background: c }} />
      <span className="text-ink-2">{t}</span>
    </div>
  )
}
