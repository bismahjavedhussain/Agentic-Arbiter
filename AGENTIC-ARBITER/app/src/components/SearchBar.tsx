import { useMemo } from 'react'
import { Combo, type ComboItem } from './Combo'
import { facilityName, int, isReady, stateName, type Artefacts } from '../lib/artefacts'

export type Filters = { state: string; operator: string; facility: string }

type Props = {
  a: Artefacts
  filters: Filters
  onChange: (f: Filters) => void
  shown: number
}

/**
 * The three combo boxes, INTERCONNECTED, sticky under the masthead.
 *
 * INTERCONNECTED means each field's options are computed from what the others already exclude. Pick
 * California and the operator list drops from 163 to the ones that actually operate there, with their
 * California counts, not their national ones. A filter bar whose options ignore the other filters
 * offers combinations that return nothing, and the reader has to discover that by trying them.
 *
 * 🔴 STICKY, AND THAT IS THE ANSWER TO A CONTRADICTION IN THE BRIEF. It asks for the order
 * headline -> search -> data cards -> map, AND for the search bar and the map to be visible at the
 * same time so the map can be watched while the search is used. With the data cards between them,
 * those cannot both hold at any laptop height. Pinning the bar satisfies the intent rather than the
 * letter: scroll to the map and the controls are still there, still usable, and the map still moves.
 */
export function SearchBar({ a, filters, onChange, shown }: Props) {
  const sites = a.unified.sites

  /* Each list is built from the rows the OTHER filters leave alive. */
  const afterOperator = useMemo(
    () => (filters.operator ? sites.filter((s) => s.operators?.includes(filters.operator)) : sites),
    [sites, filters.operator],
  )
  const afterState = useMemo(
    () => (filters.state ? sites.filter((s) => (s.state || '??') === filters.state) : sites),
    [sites, filters.state],
  )

  const stateItems: ComboItem[] = useMemo(() => {
    const n: Record<string, number> = {}
    for (const s of afterOperator) n[s.state || '??'] = (n[s.state || '??'] || 0) + 1
    const codes = Object.keys(n).sort((x, y) => stateName(x).localeCompare(stateName(y)))
    return [
      { value: '', label: 'All states', meta: int(afterOperator.length) },
      ...codes.map((c) => ({ value: c, label: stateName(c), meta: int(n[c]) })),
    ]
  }, [afterOperator])

  const operatorItems: ComboItem[] = useMemo(() => {
    const n: Record<string, number> = {}
    for (const s of afterState) for (const o of s.operators || []) n[o] = (n[o] || 0) + 1
    // By COUNT, then alphabetically: someone looking for AWS should not scroll past forty
    // single-site operators to reach it, and ties must order stably between builds.
    const keys = Object.keys(n).sort((x, y) => n[y] - n[x] || x.localeCompare(y))
    return [
      { value: '', label: 'All operators', meta: int(keys.length) },
      ...keys.map((k) => ({ value: k, label: k, meta: int(n[k]) })),
    ]
  }, [afterState])

  const facilityItems: ComboItem[] = useMemo(() => {
    const rows = sites.filter((s) => {
      if (filters.state && (s.state || '??') !== filters.state) return false
      if (filters.operator && !s.operators?.includes(filters.operator)) return false
      return true
    })
    // Runnable first within the list, then by name, so the ones a reader can actually open lead.
    rows.sort((x, y) => {
      const r = Number(isReady(a, y)) - Number(isReady(a, x))
      return r || facilityName(x).localeCompare(facilityName(y))
    })
    return [
      { value: '', label: 'Any facility', meta: int(rows.length) },
      ...rows.map((s) => ({
        value: s.key,
        label: facilityName(s),
        meta: stateName(s.state),
        ready: isReady(a, s),
      })),
    ]
  }, [sites, filters.state, filters.operator, a])

  const set = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch }
    /* Choosing a state or an operator drops a facility that is no longer in scope, rather than
       leaving a selection the other two filters exclude. */
    if (next.facility) {
      const f = a.byKey.get(next.facility)
      const stillIn =
        f &&
        (!next.state || (f.state || '??') === next.state) &&
        (!next.operator || f.operators?.includes(next.operator))
      if (!stillIn) next.facility = ''
    }
    onChange(next)
  }

  const any = filters.state || filters.operator || filters.facility

  return (
    <div className="sticky top-0 z-40 -mx-4 px-4 py-3 sm:-mx-6 sm:px-6">
      <div className="glass flex flex-wrap items-end gap-3 rounded-2xl px-3.5 py-3 shadow-xl">
        <Combo
          label="State"
          placeholder="type or choose…"
          items={stateItems}
          value={filters.state}
          onChange={(v) => set({ state: v })}
        />
        <Combo
          label="Operator"
          placeholder="type or choose…"
          items={operatorItems}
          value={filters.operator}
          onChange={(v) => set({ operator: v })}
        />
        <Combo
          label="Facility"
          placeholder="name a data centre…"
          items={facilityItems}
          value={filters.facility}
          onChange={(v) => set({ facility: v })}
          wide
        />

        <div className="flex shrink-0 items-center gap-3 pb-1">
          <span className="num text-[12.5px] text-ink-2" role="status" aria-atomic="true">
            <b className="text-ink">{int(shown)}</b> of {int(a.unified.n_sites)} shown
          </span>
          {any && (
            <button
              type="button"
              onClick={() => onChange({ state: '', operator: '', facility: '' })}
              className="rounded-lg border border-hair px-2.5 py-1.5 text-[11.5px] font-semibold
                         text-ink-2 transition-colors hover:text-ink"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
