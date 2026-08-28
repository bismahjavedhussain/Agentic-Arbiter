import { CATEGORY_LABEL, facilityName, int, isReady, stateName, type Artefacts, type Facility }
  from '../lib/artefacts'

/**
 * WHAT TO DO NEXT, once a facility is chosen.
 *
 * 🔴 THIS WAS MISSING AND THE USER CAUGHT IT. The pick screen let a reader select a data centre and
 * then offered nothing: no way to configure the plant, no way to run the agent, no statement that
 * those stages exist. A screen that ends in a dead end is not a smaller version of the product, it is
 * a broken one, and "the brief only specified the pick screen" is not a defence for shipping a
 * cul-de-sac.
 *
 * WHERE THE BUTTON GOES, and it is a handoff rather than a reimplementation. The configure and results
 * stages exist and work TODAY in `demo/index.html`: the plant envelope, the 20,160 swept
 * configurations, the reasoning tape, all thirteen result panels, and the live-agent card. None of that
 * has been rebuilt in React yet, and pretending otherwise with a button that goes nowhere would be
 * worse than this. So the button links to the page that does the work, at the site the reader picked,
 * using the `?site=` parameter it already understands.
 *
 * ⚠ `?site=` TAKES A METRO KEY, NOT A FACILITY KEY. The page validates it against the picker's own
 * options, which are the offerable metros, and falls through to the default silently on anything it
 * does not recognise. So the CTA is only offered for a facility whose metro is offerable, and a
 * candidate gets the honest reason instead of a button that would quietly land somewhere else.
 */
export function SelectedBar({ a, facility, onClear }: {
  a: Artefacts
  facility: Facility
  onClear: () => void
}) {
  const ready = isReady(a, facility)
  const man = a.manifest.sites.find((s) => s.key === facility.metro_key)
  const ops = (facility.operators || []).filter(Boolean)

  return (
    <div className="glass mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl px-3.5 py-3">
      <span
        className="h-[9px] w-[9px] shrink-0 rounded-full"
        style={{ background: ready ? 'var(--good)' : 'var(--axis)' }}
        aria-hidden="true"
      />

      <div className="min-w-0 flex-1">
        <div className="truncate text-[14px] font-bold tracking-[-0.01em]">
          {facilityName(facility)}
          <span className="font-normal text-ink-2">, {stateName(facility.state)}</span>
        </div>
        <div className="mt-0.5 truncate text-[11.5px] text-ink-2">
          {CATEGORY_LABEL[facility.category] || facility.category}
          {' · '}
          {int(facility.n_tagged)} OSM-tagged building{facility.n_tagged === 1 ? '' : 's'}
          {ops.length ? ` · ${ops.slice(0, 3).join(', ')}${ops.length > 3 ? ` +${ops.length - 3}` : ''}` : ''}
          {man?.station ? ` · weather from ${man.station}` : ''}
        </div>
      </div>

      <button
        type="button"
        onClick={onClear}
        className="shrink-0 rounded-lg border border-hair px-2.5 py-1.5 text-[11.5px]
                   font-semibold text-ink-2 transition-colors hover:text-ink"
      >
        Deselect
      </button>

      {ready ? (
        <a
          // Relative, so it works from the dev server, from a built dist/ dropped into demo/, and
          // from any static host. `../index.html` in dev; the server maps it onto demo/.
          href={`../index.html?site=${encodeURIComponent(facility.metro_key)}`}
          className="shrink-0 rounded-lg px-3.5 py-2 text-[12.5px] font-bold transition-transform
                     duration-150 hover:-translate-y-0.5"
          style={{ background: 'var(--action)', color: 'var(--action-ink)' }}
        >
          Configure this plant →
        </a>
      ) : (
        <span
          className="shrink-0 rounded-lg border border-hair px-3 py-2 text-[11.5px] text-muted"
          title="Only sites with a published agent run can be configured. This one is a real,
                 OSM-tagged candidate that has not been built yet."
        >
          No agent run published yet
        </span>
      )}
    </div>
  )
}
