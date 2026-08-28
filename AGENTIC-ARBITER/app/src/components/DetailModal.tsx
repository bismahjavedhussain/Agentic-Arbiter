import { useEffect, useRef, useState } from 'react'
import { DETAIL_EVENT, type DetailPayload } from '../lib/declutter'

/**
 * The pop-up the folded prose opens into.
 *
 * THE BRIEF: "Hide all detailed explanations and deep dives behind click-triggered pop-ups or
 * modals." So the engine's long paragraphs are folded away by lib/declutter.ts and land here, in
 * full, when a reader asks for them. Nothing is deleted; it is moved off the first read.
 *
 * WHY IT LISTENS FOR AN EVENT INSTEAD OF TAKING A PROP. The buttons that open it live inside DOM the
 * ENGINE owns, injected by a pass that runs after every draw. React does not manage those nodes and
 * must not start to: EngineStage exists precisely so React never diffs that subtree. A custom event
 * on `window` is the seam. Engine DOM dispatches, React listens, and neither one holds a reference to
 * the other.
 *
 * The content is inserted with dangerouslySetInnerHTML because it IS the engine's own markup, lifted
 * out of the card unchanged: its <strong>, its <code>, its links. It is first-party content from the
 * same document, not anything a visitor supplied.
 */
export function DetailModal() {
  const [payload, setPayload] = useState<DetailPayload | null>(null)
  const closeRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    const onOpen = (e: Event) => {
      const d = (e as CustomEvent<DetailPayload>).detail
      if (d) setPayload(d)
    }
    window.addEventListener(DETAIL_EVENT, onOpen)
    return () => window.removeEventListener(DETAIL_EVENT, onOpen)
  }, [])

  /* Escape closes, and focus moves to the close button when it opens. A modal that traps a keyboard
     reader with no way out is worse than no modal. */
  useEffect(() => {
    if (!payload) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setPayload(null)
    }
    window.addEventListener('keydown', onKey)
    closeRef.current?.focus()
    return () => window.removeEventListener('keydown', onKey)
  }, [payload])

  if (!payload) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto p-4 sm:p-8"
      style={{ background: 'rgba(0,0,0,0.55)' }}
      onClick={() => setPayload(null)}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={payload.title || 'Detail'}
        className="glass relative my-8 w-full max-w-[68ch] rounded-2xl p-5 sm:p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start gap-4">
          <h3 className="display text-[clamp(15px,1.5vw,19px)] leading-tight">
            {payload.title || 'Detail'}
          </h3>
          <button
            ref={closeRef}
            type="button"
            onClick={() => setPayload(null)}
            aria-label="Close"
            className="ml-auto shrink-0 rounded-lg border border-hair px-2.5 py-1 text-[12px]
                       font-semibold text-ink-2 transition-colors hover:text-ink"
          >
            Close
          </button>
        </div>

        {/* `aa-detail` is styled in index.css to inherit the page's own prose treatment, so the
            engine's markup looks the same here as it did in the card. */}
        <div
          className="aa-detail text-[13.5px] leading-[1.55] text-ink-2"
          dangerouslySetInnerHTML={{ __html: payload.html }}
        />
      </div>
    </div>
  )
}
