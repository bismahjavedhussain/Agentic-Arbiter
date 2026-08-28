import { useEffect, useId, useMemo, useRef, useState } from 'react'

export type ComboItem = {
  /** What goes into state when this row is chosen. '' means "no filter". */
  value: string
  /** What the reader sees. */
  label: string
  /** The right-hand count or qualifier, e.g. "46". */
  meta?: string
  /** Draws the small status dot when true. */
  ready?: boolean
}

type Props = {
  label: string
  placeholder: string
  items: ComboItem[]
  value: string
  onChange: (value: string) => void
  /** Rows to show before scrolling. */
  max?: number
  /** Widen the popover past the input, for rows that are sentences rather than words. */
  wide?: boolean
}

/**
 * A combobox that accepts TYPING and offers a DROPDOWN, which is what the brief asked for on all
 * three filter fields.
 *
 * 🔴 `aria-expanded` IS MAINTAINED, and that is not boilerplate. The single-file page's facility
 * search shipped with `aria-expanded="false"` hard-coded in the markup and never updated, so a screen
 * reader announced a closed list while eight facilities were on screen. That is worse than having no
 * combobox role at all: the role promises an expandable listbox and then lies about its state. Here
 * it is derived from `open`, so it cannot fall out of step.
 *
 * WHY THIS IS HAND-BUILT rather than pulled from 21st.dev. Two reasons, and the second is the real
 * one. First, the free tier allows two component retrievals a day. Second, every 21st combobox ships
 * as a shadcn registry component requiring `npx shadcn add`, which brings components.json, a utils
 * module, Radix and cmdk -- and would then have to be rewired for the interconnected filter semantics
 * below, where choosing a state narrows the operator list. The integration plus the rewiring costs
 * more than the 90 lines it replaces, and leaves the behaviour owned by neither side.
 */
export function Combo({ label, placeholder, items, value, onChange, max = 9, wide }: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const wrap = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const listId = useId()

  const selected = items.find((i) => i.value === value)

  /* WHAT THE INPUT SHOWS when it is not being typed in: the chosen row's label. While typing, the
     reader's own text, because overwriting what someone is typing is the fastest way to make a
     control feel broken. */
  const shown = open ? query : selected?.label ?? ''

  const hits = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!open) return items
    if (!q) return items
    // Prefix hits first, then substring: someone typing "cal" wants California above "Cal Poly".
    const pre: ComboItem[] = []
    const sub: ComboItem[] = []
    for (const it of items) {
      const l = it.label.toLowerCase()
      if (l.startsWith(q)) pre.push(it)
      else if (l.includes(q)) sub.push(it)
    }
    return [...pre, ...sub]
  }, [items, query, open])

  useEffect(() => {
    if (active >= hits.length) setActive(0)
  }, [hits.length, active])

  /* Clicking away closes it. `mousedown` rather than `click`, so it closes before a click elsewhere
     is processed, and containment is checked so choosing a row is not itself a dismissal. */
  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', away)
    return () => document.removeEventListener('mousedown', away)
  }, [open])

  const commit = (it: ComboItem) => {
    onChange(it.value)
    setOpen(false)
    setQuery('')
    input.current?.blur()
  }

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (!open) { setOpen(true); return }
      setActive((a) => {
        const n = hits.length
        if (!n) return 0
        return e.key === 'ArrowDown' ? (a + 1) % n : (a - 1 + n) % n
      })
      return
    }
    if (e.key === 'Enter') {
      if (open && hits[active]) { e.preventDefault(); commit(hits[active]) }
      return
    }
    if (e.key === 'Escape') { setOpen(false); setQuery(''); return }
    if (e.key === 'Home' && open) { e.preventDefault(); setActive(0) }
    if (e.key === 'End' && open) { e.preventDefault(); setActive(Math.max(0, hits.length - 1)) }
  }

  return (
    <div ref={wrap} className="relative min-w-0 flex-1">
      <label className="label mb-1.5 block" htmlFor={`${listId}-input`}>
        {label}
      </label>
      <div className="relative">
        <input
          id={`${listId}-input`}
          ref={input}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && hits[active] ? `${listId}-${active}` : undefined}
          autoComplete="off"
          spellCheck={false}
          value={shown}
          placeholder={placeholder}
          onFocus={() => { setOpen(true); setQuery('') }}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); setActive(0) }}
          onKeyDown={onKey}
          className="w-full rounded-lg border border-hair bg-surface-1 px-3 py-2 pr-8
                     text-[13.5px] text-ink placeholder:text-muted
                     transition-colors duration-150 hover:border-[var(--axis)]"
        />
        {/* A chevron that is a real button, so the dropdown is reachable without typing. */}
        <button
          type="button"
          tabIndex={-1}
          aria-label={open ? `Close the ${label} list` : `Open the ${label} list`}
          onMouseDown={(e) => { e.preventDefault(); setOpen((o) => !o); input.current?.focus() }}
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted
                     hover:text-ink"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"
               style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .18s' }}>
            <path d="M5 8l7 7 7-7" />
          </svg>
        </button>
      </div>

      {open && (
        <div
          id={listId}
          role="listbox"
          aria-label={label}
          className="glass absolute left-0 z-50 mt-1.5 overflow-y-auto rounded-xl shadow-2xl"
          style={{
            top: '100%',
            minWidth: '100%',
            width: wide ? 'max-content' : undefined,
            maxWidth: wide ? 'min(460px, 82vw)' : undefined,
            maxHeight: `${max * 34 + 8}px`,
          }}
        >
          {hits.length === 0 && (
            <div className="px-3 py-2.5 text-[12.5px] text-ink-2">
              Nothing matches “{query}”.
            </div>
          )}
          {hits.map((it, i) => (
            <div
              key={it.value || '__all__'}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={it.value === value}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => { e.preventDefault(); commit(it) }}
              className={`flex cursor-pointer items-center gap-2 border-b border-hair px-3 py-2
                          text-[12.5px] last:border-b-0 ${
                            i === active ? 'bg-surface-2' : ''
                          }`}
            >
              {it.ready !== undefined && (
                <span
                  className="h-[7px] w-[7px] shrink-0 rounded-full"
                  style={{ background: it.ready ? 'var(--good)' : 'var(--axis)' }}
                />
              )}
              <span className="min-w-0 flex-1 truncate font-semibold text-ink">{it.label}</span>
              {it.meta && <span className="num shrink-0 text-[11.5px] text-muted">{it.meta}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
