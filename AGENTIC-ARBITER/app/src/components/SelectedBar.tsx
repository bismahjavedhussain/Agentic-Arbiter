import { CATEGORY_LABEL, facilityName, int, isReady, measuredGain,
  readiness, stateName, type Artefacts, type Facility }
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
 * WHERE THE BUTTON GOES, AS OF 2026-08-28: INTO THIS APP. It used to be a link out to
 * `demo/index.html?site=...`, which was honest at the time -- the configure and results stages had not
 * been brought across -- but the user's reply was the right one: a new UI that hands you back to the
 * old UI at the first real action has not replaced anything. So the stages came across. The engine
 * that draws them is results/engine.mjs, lifted byte for byte out of the page, and this button now
 * calls it. Same plant envelope, same 20,160 swept configurations, same reasoning tape, same thirteen
 * panels, same live-agent card, and the same numbers -- because it is the same code.
 *
 * ⚠ THE ENGINE IS KEYED BY METRO, NOT BY FACILITY. `loadSite()` looks the key up in sites.json and
 * refuses one it does not know, so the CTA is only offered where the facility's metro is offerable. A
 * real OSM-tagged candidate with no published run gets the honest sentence instead of a button that
 * would quietly load somewhere else.
 */
export function SelectedBar({ a, facility, onClear, onConfigure, busy }: {
  a: Artefacts
  facility: Facility
  onClear: () => void
  /** Hands the metro key to the engine. See lib/engine.ts:configureSite. */
  onConfigure: (metroKey: string) => void
  /** True while the engine is loading that site's artefacts, so the button can say so. */
  busy?: boolean
}) {
  const ready = isReady(a, facility)
  const state = readiness(a, facility)
  const gain = measuredGain(a, facility)
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
        // 🔴 THE ONLY BUTTON ON THE FIRST SCREEN, which is what the brief asks for: "The front page
        // only has the configure button and then the run agent button and run agent live button all
        // appears afterwards." Run the agent and Run the agent on live data are bound by the engine's
        // own wire(), on the next screen, exactly as they are in the page.
        <button
          type="button"
          disabled={busy}
          onClick={() => onConfigure(facility.metro_key)}
          /* The landing intro's call-to-action beat lands on this button, because it is the only
             action the first screen has. One attribute; nothing about the button changes. */
          data-aa-hero="cta"
          className="shrink-0 rounded-lg px-3.5 py-2 text-[12.5px] font-bold transition-transform
                     duration-150 hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-60"
          /* BRAND BLUE, not var(--action). --action is one of the 20 canonical palette tokens
             verify_palette.py requires the app and the page to agree on, so its VALUE is left alone
             and this component is re-skinned instead. It rendered black in the light theme, which is
             what the user photographed. */
          style={{
            background: 'linear-gradient(180deg, var(--fg-bright), var(--fg-deep))',
            color: '#fff',
            boxShadow: '0 6px 18px color-mix(in oklab, var(--fg-deep) 34%, transparent)',
          }}
        >
          {busy ? `Loading ${facility.metro_key}…` : 'Configure this plant →'}
        </button>
      ) : (
        /* 🔴 THE SAME FALSE SENTENCE AS THE MAP LEGEND, IN THE PLACE A READER IS MOST LIKELY TO
           READ IT. "No agent run published yet" is right for the 389 candidates with no artefacts
           and wrong for the 12 that were built, measured across five years and then withheld
           because the agent came out worse than the controller it replaces. Those have a run; what
           they do not have is a result worth selling. Saying so is both more honest and a better
           argument: a portfolio that reports where it does not work is one a reader can believe
           about where it does. */
        <span
          className="shrink-0 rounded-lg border border-hair px-3 py-2 text-[11.5px] text-muted"
          title={
            state === 'measured-negative'
              ? `Built and measured over five years. The agent recovered ${int(gain)} chiller-hours `
                + 'a year here, which is worse than the reactive controller it would replace: its '
                + 'own safety constraints hand back more free-cooling hours than they win at this '
                + 'geometry. It is not offered without site-specific engineering.'
              : 'Only sites with a published agent run can be configured. This one is a real, '
                + 'OSM-tagged candidate that has not been built yet.'
          }
        >
          {state === 'measured-negative'
            ? `Measured, not offered · ${int(gain)} h/yr`
            : 'No agent run published yet'}
        </span>
      )}
    </div>
  )
}
