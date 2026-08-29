/* The artefacts, loaded once, with the shapes this app actually reads.
   ================================================================================================
   These are the SAME files demo/index.html fetches, at the same relative paths, which is why
   vite.config.ts serves ../demo rather than copying anything. One set of numbers, one registry, two
   front ends. If this app ever computed a figure the page does not, that would be the drift the whole
   verification layer exists to prevent.
   ================================================================================================ */

export type Facility = {
  key: string
  label: string
  state: string
  metro_key: string
  category: 'cluster' | 'pair' | 'single'
  /** [latitude, longitude] -- note the order; maplibre wants them the other way round. */
  centre: [number, number]
  operators: string[]
  sample_names: string[]
  n_tagged: number
  status: string
  detail?: string
}

export type UnifiedSites = { n_sites: number; sites: Facility[] }

export type ManifestSite = {
  key: string
  offerable?: boolean
  footprint_m2?: number
  weather_hours?: number
  station?: string
  /* The names as sites.json actually spells them. Guessed `source`/`receptor` first and the
     popup silently rendered an empty line, which is the failure mode of an optional chain on a
     misspelt key: no error, just nothing. */
  committed?: {
    source_name?: string
    receptor_name?: string
    facade_gap_m?: number
    centroid_separation_m?: number
  }
  [k: string]: unknown
}

export type Manifest = {
  sites: ManifestSite[]
  scale?: Record<string, number>
  [k: string]: unknown
}

/**
 * WHERE THE ARTEFACTS ARE, relative to this app's own page. ONE constant, because the answer differs
 * by deployment and getting it wrong is a silent 404 per file:
 *
 *   vite dev              app at /             ../sites.json -> /sites.json      (the config's plugin)
 *   testing/serve_app.py  app at /app/         ../sites.json -> /sites.json      (demo/)
 *   production            demo/app/index.html  ../sites.json -> demo/sites.json
 *
 * `../` holds in all three because browsers CLAMP it at the root rather than erroring. When the app
 * eventually REPLACES demo/index.html this becomes '' and nothing else changes.
 */
export const ART = '../'

async function grab<T>(name: string): Promise<T> {
  // `no-cache` rather than `no-store`: revalidate, but let the browser keep a copy. The single-file
  // page does the same for these two, and for the same reason -- a rebuild must not be served stale.
  const r = await fetch(ART + name, { cache: 'no-cache' })
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`)
  return (await r.json()) as T
}

/** THE PORTFOLIO TOTALS, summed over all 250 shipped sites by `tools/portfolio_totals.py`.
 *
 * 🔴 A FILE RATHER THAN ARITHMETIC IN THE BROWSER, and that is a deliberate trade. Every field here
 * needs three artefacts per site; across 250 sites that is 750 fetches and hundreds of megabytes
 * before the first card could paint. The tool computes it once at build time with the SAME arithmetic
 * as `headline.ts:headlineFigures`, so a portfolio total and the site tile a reader clicks into
 * cannot disagree.
 *
 * ⚠ IT IS A SUM, NOT A PROJECTION. Each of the 250 sites carries its own backtest, trace and money
 * artefacts (measured: 247 distinct backtests, 250 distinct money files), so none of these is one
 * site's figure multiplied by a count. */
export type Portfolio = {
  sites_summed: number
  sites_gaining: number
  sites_losing: number
  sites_own_state_prices: number
  sites_reference_prices: number
  stations: number
  /** Each of the 98 stations counted ONCE. The honest "hours of weather" figure. */
  weather_hours_distinct: number
  /** 250 sites x their own station's record. Real work done, but stations are shared, so this is
      site-hours and must never be called hours of weather. */
  weather_site_hours: number
  footprint_m2: number
  usd_lo: number
  usd_hi: number
  gain_h_per_year: number
  cut_pct: number
  mw_lo: number
  mw_hi: number
}

export type Artefacts = {
  manifest: Manifest
  unified: UnifiedSites
  /** null when demo/portfolio.json has not been generated. The cards that read it simply omit their
      portfolio rows in that case, rather than printing a zero that no file supports. */
  portfolio: Portfolio | null
  /** metro keys the manifest marks offerable. THE ONLY source of truth for "ready to run". */
  offerable: Set<string>
  /** facility key -> row, so a map click or a dropdown row reads the FULL row, not a truncated copy. */
  byKey: Map<string, Facility>
}

export async function loadArtefacts(): Promise<Artefacts> {
  const [manifest, unified, portfolio] = await Promise.all([
    grab<Manifest>('sites.json'),
    grab<UnifiedSites>('unified_sites.json'),
    /* TOLERANT ON PURPOSE, unlike the two above. sites.json and unified_sites.json are the product;
       without them there is no page and throwing is correct. portfolio.json is a summary written by a
       build tool, and a deployment that predates the tool should still render the product rather than
       show a loading state forever. */
    grab<Portfolio>('portfolio.json').catch(() => null),
  ])
  /* 🔴 READY-TO-RUN COMES FROM sites.json AND NOWHERE ELSE.
     unified_sites.json carries a baked `status` string, and the old map coloured its dots from it:
     the caption said 246 runnable while the map painted 3 green. The manifest's `offerable` flag is
     the only thing allowed to decide what the agent can open. */
  const offerable = new Set(
    manifest.sites.filter((s) => s.offerable).map((s) => s.key),
  )
  const byKey = new Map(unified.sites.map((s) => [s.key, s]))
  return { manifest, unified, portfolio, offerable, byKey }
}

export const isReady = (a: Artefacts, f: Facility) => a.offerable.has(f.metro_key)

/** en-US grouping, matching the page's `int()` so the two never disagree on a thousands separator. */
export const int = (v: number | null | undefined) =>
  v === null || v === undefined || Number.isNaN(v) ? '–' : Math.trunc(v).toLocaleString('en-US')

export const US_STATE_NAMES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California', CO: 'Colorado',
  CT: 'Connecticut', DE: 'Delaware', DC: 'District of Columbia', FL: 'Florida', GA: 'Georgia',
  HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas',
  KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts',
  MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri', MT: 'Montana',
  NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico',
  NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma',
  OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia',
  WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
}

/** A state code expanded for display. The artefacts store the code, because that is what OSM's
 *  address tags give and a display name has no business in a measurement file. */
export const stateName = (code: string | undefined) =>
  (code && US_STATE_NAMES[code]) || code || 'Unknown'

/** `unified_sites.json` is inconsistent: 424 of its 637 labels already read "Ashburn, Virginia" and
 *  213 read "Reston, VA", because they were built from different OSM address tags. Expanded for
 *  DISPLAY only, and only when the last two characters after a comma really are a state code. */
export const expandStateSuffix = (t: string | undefined) =>
  String(t ?? '').replace(/, ([A-Z]{2})$/, (m, c: string) =>
    US_STATE_NAMES[c] ? `, ${US_STATE_NAMES[c]}` : m,
  )

/** The best human name for a facility: its own sample name if OSM had one, else its label. */
export const facilityName = (f: Facility) =>
  expandStateSuffix((f.sample_names || []).filter(Boolean)[0] || f.label) ||
  `${stateName(f.state)} site`

export const CATEGORY_LABEL: Record<string, string> = {
  cluster: 'multi-building campus',
  pair: 'exact source to receptor pair',
  single: 'standalone, no tagged neighbour',
}
