import { useEffect, useId, useRef, useState } from 'react'

/**
 * The disclosure pattern the brief asks for: "Hide all detailed explanations and deep dives behind
 * click-triggered pop-ups."
 *
 * 🔴 CLICK, NOT HOVER, AND THE TEXT IS IN THE ACCESSIBLE NAME. A hover tooltip is unreachable on a
 * touch screen and by a keyboard, so a claim parked in one is a claim some readers never see. This is
 * a button with `aria-expanded`, and the same prose is also the button's `aria-label`, so a screen
 * reader gets it whether or not the popover is opened. That mattered on the single-file page too: the
 * masthead's "why that is rational rather than careless" argument lives in exactly this pattern.
 *
 * WHY IT IS NOT JUST DECORATION. The decluttering the brief asks for only stays honest if the
 * removed prose goes SOMEWHERE. Anything genuinely load-bearing goes here or into the README; nothing
 * is simply deleted.
 */
export function Info({ children, label }: { children: React.ReactNode; label: string }) {
  const [open, setOpen] = useState(false)
  const wrap = useRef<HTMLSpanElement>(null)
  const id = useId()

  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', esc)
    }
  }, [open])

  return (
    <span ref={wrap} className="relative inline-block align-middle">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        aria-label={label}
        onClick={() => setOpen((o) => !o)}
        className="ml-1 inline-flex h-[15px] w-[15px] items-center justify-center rounded-full
                   border border-hair text-[9.5px] font-bold leading-none text-muted
                   transition-colors hover:border-[var(--axis)] hover:text-ink"
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="note"
          className="glass absolute left-0 top-[22px] z-50 block w-[min(340px,78vw)] rounded-xl
                     p-3 text-left text-[12.5px] font-normal leading-[1.5] text-ink-2 shadow-2xl"
        >
          {children}
        </span>
      )}
    </span>
  )
}
