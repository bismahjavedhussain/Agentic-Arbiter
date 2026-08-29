import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/**
 * The disclosure pattern the brief asks for: "Hide all detailed explanations and deep dives behind
 * click-triggered pop-ups." Now also on hover and on keyboard focus, and PORTALLED, which is the
 * whole of the bug fix below.
 *
 * 🔴 THE BUG THE USER REPORTED, AND THE CAUSE, WHICH WAS NOT THE OBVIOUS ONE.
 * Reported: the panel renders "semi-transparent, with the card's own numbers showing through", and
 * resolves into a correct opaque panel only after the pointer leaves the card entirely.
 *
 * The obvious reading is that the panel is translucent. IT IS NOT, and that was measured before
 * anything was changed. The panel's computed `background-color` is rgb(12, 26, 42) at ALPHA 1.0 and
 * its computed `backdrop-filter` is `none`, because tones.css:148-160 already overrides `.glass` for
 * `[role='note']`. Nothing about the panel is see-through.
 *
 * WHAT IS ACTUALLY HAPPENING: the KPI card carries `hover:-translate-y-0.5` (KpiCards.tsx). Tailwind
 * v4 ships that as the `translate` property, and a `translate` other than `none` MAKES THE ELEMENT A
 * STACKING CONTEXT. While the pointer is over the card, the panel's `z-index: 300` is therefore
 * scoped INSIDE that card, and every later sibling card paints over it. What looks like the tooltip
 * being see-through is the NEIGHBOURING card's own rgba(24,24,27,0.72) glass fill painted on top of
 * an opaque panel, with that card's figure stamped crisply over the prose.
 * MEASURED with a real pointer over a CDP session, sampling 80 points across the panel:
 *     tooltip is the topmost element at   28 of 80 points with the card hovered
 *     tooltip is the topmost element at   79 of 80 points with the pointer away
 *     pixel median over the overlap band  (20,24,31) hovered vs (12,26,42) away,
 *                                         against a predicted 0.72 blend of (21,25,31)
 * All five cards, at 28/31/20/44/32 of 80. Move the pointer off the card, the `translate` reverts,
 * the stacking context disappears, `z-index: 300` escapes again, and the panel is correct. That is
 * exactly the "hunt for a cursor position" the report describes.
 *
 * 🔴 THE FIX IS TO LEAVE THE CARD ALONE AND TAKE THE PANEL OUT OF IT. Deleting the hover lift would
 * also work today and would break again the first time any ancestor gains a transform, a filter, an
 * opacity or a `will-change`; the card's lift is also not something anyone asked to lose. Portalled to
 * `document.body` the panel has no card ancestor at all, so there is no stacking context to be
 * trapped in and no `overflow` to be clipped by. It is positioned from the trigger's measured rect
 * instead of from its own `position: absolute` parent.
 *
 * WHAT ELSE THE PORTAL FIXES FOR FREE: the body text was rendering in ALL CAPS because this span was
 * a child of `<div class="label">`, and index.css:283 gives `.label` `text-transform: uppercase` plus
 * a 1.155px absolute letter-spacing computed for 10.5px eyebrows. Inheritance follows the DOM, so
 * moving the node out of `.label` ends it. `normal-case tracking-normal` is set as well, so a future
 * caller inside some other uppercase container cannot reintroduce it.
 *
 * NO OPACITY FADE. The brief asks for a fully opaque background "from the first painted frame", and
 * a panel mid-way through an opacity transition is by definition translucent over whatever is behind
 * it. So the only thing that animates is a 2px rise, which never makes the surface see-through, and
 * the 120ms open delay does the work a fade would otherwise be doing. Under reduced motion even the
 * rise is dropped.
 *
 * ⚠ IT IS STILL A BUTTON WITH THE PROSE IN ITS ACCESSIBLE NAME. A hover tooltip is unreachable on a
 * touch screen and by a keyboard, so a claim parked in one is a claim some readers never see. Hover
 * is an addition here, never the only route: the same panel opens on focus, opens on click or tap,
 * closes on Escape, and the summary is on the button as `aria-label` whether or not it is ever
 * opened. That mattered on the single-file page too, and it is why the masthead's own argument lives
 * in exactly this pattern.
 */

/** How long a pointer must rest on the (i) before the panel opens. Short enough not to feel laggy,
 *  long enough that dragging the mouse across a row of five does not flash five panels. */
const OPEN_MS = 120
/** And the close, which is deliberately faster than the open: a panel that lingers is in the way. */
const CLOSE_MS = 60
const GAP = 8      // between the trigger and the panel
const EDGE = 10    // the closest the panel may come to a viewport edge
const WIDTH = 340  // matches the brief, and .aa-tip's max-width

/**
 * 🔴 ONE OPEN PANEL, ENFORCED AT MODULE SCOPE RATHER THAN BY A CONTEXT PROVIDER.
 * "Exactly one tooltip visible at any time. Opening a new one closes any other immediately." Each
 * instance is an island; there is no common ancestor to hang a provider on that would not also have
 * to be threaded through the masthead, the KPI plate and anything added later. One module variable
 * holding "the closer of whoever is currently open" costs nothing and cannot be forgotten by a new
 * caller, because opening goes through this function or it does not happen.
 */
let closeCurrent: (() => void) | null = null

type Pos = { left: number; top: number; ready: boolean }

export function Info({ children, label }: { children: React.ReactNode; label: string }) {
  const [open, setOpen] = useState(false)
  /** `ready` is false for exactly one frame: the panel has to be in the document to be measured, and
   *  its height decides whether it opens downward or flips above. It is `visibility: hidden` for that
   *  frame, so nothing translucent is ever painted. */
  const [pos, setPos] = useState<Pos>({ left: 0, top: 0, ready: false })
  /** Opened by a pointer resting on the (i), as opposed to by a click, a tap or a keyboard. A hover
   *  panel goes away when the pointer does; a deliberate one stays until it is dismissed. */
  const [sticky, setSticky] = useState(false)

  const btn = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const openTimer = useRef<number | undefined>(undefined)
  const closeTimer = useRef<number | undefined>(undefined)
  /** `open`, readable from a timer callback. A `setTimeout` closes over the state of the render that
      scheduled it, which for a 120ms delay is a render that may already be two states stale. */
  const openRef = useRef(false)
  openRef.current = open
  const id = useId()

  const clearTimers = () => {
    window.clearTimeout(openTimer.current)
    window.clearTimeout(closeTimer.current)
  }

  const hide = useCallback(() => {
    clearTimers()
    setOpen(false)
    setSticky(false)
    setPos((p) => ({ ...p, ready: false }))
    if (closeCurrent) closeCurrent = null
  }, [])

  const show = useCallback((asSticky: boolean) => {
    clearTimers()
    /* Close whoever else is open FIRST, and synchronously, so two panels never coexist even for a
       frame. `closeCurrent` is nulled by the other instance's own `hide`. */
    if (closeCurrent) closeCurrent()
    closeCurrent = () => {
      setOpen(false)
      setSticky(false)
      setPos((p) => ({ ...p, ready: false }))
    }
    /* 🔴 `s || asSticky`, NOT `asSticky`, AND THE PLAIN ASSIGNMENT WAS A RACE.
       A mouse CLICK on the (i) is preceded by a `pointerenter`, so `enter()` schedules a hover-open
       for 120ms later and then the click's own `show(true)` runs about a millisecond after it and
       pins the panel. `show` cancels the pending timer, and MEASURED, that cancellation does not
       always win: the panel came up `sticky` and was `hover` again 180ms later, because the late
       timer's `show(false)` had unpinned it. The next click then read `open && sticky` as false and
       re-opened instead of closing, which is a click that visibly does nothing.
       Stickiness is now a latch: it is set by any deliberate open and cleared only by `hide`, so a
       hover-open arriving after a click cannot demote what the click pinned. The timer is still
       cancelled as well; this is the half that does not depend on winning a race. */
    setSticky((was) => was || asSticky)
    setOpen(true)
  }, [])

  /* ---- POSITION. Measured from the trigger, in viewport coordinates, because the panel is
     `position: fixed` and therefore has no offset parent to be relative to. Recomputed on scroll and
     on resize; `capture: true` on the scroll listener so a scrolling CONTAINER moving the trigger is
     caught as well as the window. */
  const place = useCallback(() => {
    const b = btn.current
    const p = panel.current
    if (!b || !p) return
    const r = b.getBoundingClientRect()
    const h = p.offsetHeight
    const w = Math.min(WIDTH, p.offsetWidth || WIDTH)
    const vw = document.documentElement.clientWidth
    const vh = document.documentElement.clientHeight

    // Horizontal: aligned to the trigger, then SHIFTED rather than allowed to overflow. The fifth
    // KPI card sits hard against the right edge at every width, so this branch is not hypothetical.
    let left = r.left
    if (left + w > vw - EDGE) left = vw - EDGE - w
    if (left < EDGE) left = EDGE

    // Vertical: below by preference, FLIPPED above when below would not fit and above would.
    let top = r.bottom + GAP
    const fitsBelow = top + h <= vh - EDGE
    const fitsAbove = r.top - GAP - h >= EDGE
    if (!fitsBelow && fitsAbove) top = r.top - GAP - h
    else if (!fitsBelow) top = Math.max(EDGE, vh - EDGE - h)   // taller than the viewport: clamp

    setPos({ left: Math.round(left), top: Math.round(top), ready: true })
  }, [])

  useLayoutEffect(() => {
    if (!open) return
    place()
  }, [open, place])

  useEffect(() => {
    if (!open) return
    const onScroll = () => place()
    const away = (e: MouseEvent) => {
      const t = e.target as Node
      if (btn.current && btn.current.contains(t)) return
      if (panel.current && panel.current.contains(t)) return
      hide()
    }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') hide() }
    window.addEventListener('scroll', onScroll, { passive: true, capture: true })
    window.addEventListener('resize', onScroll)
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', esc)
    return () => {
      window.removeEventListener('scroll', onScroll, { capture: true } as EventListenerOptions)
      window.removeEventListener('resize', onScroll)
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', esc)
    }
  }, [open, place, hide])

  /* An unmount while open would leave `closeCurrent` pointing at a dead component, and the next
     opener would call setState on it. Cleared here rather than hoped about. */
  useEffect(() => () => { clearTimers(); if (closeCurrent) closeCurrent = null }, [])

  /* ---- HOVER, MOUSE ONLY. `pointerenter` fires for touch immediately before `click`, so binding
     hover for every pointer type makes a tap open the panel and then the click toggle close it again.
     Touch goes through the click path alone, which is the only reliable route there anyway. */
  const enter = (e: React.PointerEvent) => {
    if (e.pointerType !== 'mouse') return
    window.clearTimeout(closeTimer.current)
    if (open) return
    /* Checked again when the timer FIRES, not only when it is scheduled: 120ms is long enough for a
       click to have opened the panel in between, and re-running `show` then is at best redundant. */
    openTimer.current = window.setTimeout(() => { if (!openRef.current) show(false) }, OPEN_MS)
  }
  const leave = (e: React.PointerEvent) => {
    if (e.pointerType !== 'mouse') return
    window.clearTimeout(openTimer.current)
    if (sticky) return              // opened deliberately: only a dismissal closes it
    closeTimer.current = window.setTimeout(hide, CLOSE_MS)
  }

  return (
    <>
      <button
        ref={btn}
        type="button"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        aria-describedby={open ? id : undefined}
        aria-label={label}
        /* THE STATE, PUBLISHED, because "open" and "open and pinned" behave differently and a check
           that can only see `aria-expanded` cannot tell them apart. testing/verify_tooltip.py reads
           this; the same pattern as `data-aa-intro` and `data-aa-sphere` elsewhere in the app. */
        data-aa-tip={open ? (sticky ? 'sticky' : 'hover') : 'closed'}
        onPointerEnter={enter}
        onPointerLeave={leave}
        /* 🔴 `:focus-visible`, NOT `:focus`, AND THE DIFFERENCE IS A BROKEN TOGGLE.
           A mouse press focuses the button before it clicks it. With a bare `onFocus` handler the
           first press therefore OPENED the panel and the click that followed immediately toggled it
           shut, so a single click did nothing and it took two to open. MEASURED by
           testing/verify_tooltip.py section 7, which is why that check exists.
           Chrome grants `:focus-visible` to a button when the focus arrived from the keyboard and
           withholds it when it arrived from a pointer, which is exactly the distinction needed here:
           a keyboard reader gets the panel on arrival, a mouse reader gets it from the click they
           were going to make anyway. */
        onFocus={(e) => { if (e.currentTarget.matches(':focus-visible')) show(true) }}
        onBlur={hide}
        onClick={() => (open && sticky ? hide() : show(true))}
        className="ml-1 inline-flex h-[15px] w-[15px] items-center justify-center rounded-full
                   border border-hair text-[9.5px] font-bold leading-none text-muted
                   transition-colors hover:border-[var(--axis)] hover:text-ink"
      >
        i
      </button>

      {open && createPortal(
        <div
          ref={panel}
          id={id}
          role="note"
          className={`aa-tip${pos.ready ? ' is-ready' : ''}`}
          style={{ left: pos.left, top: pos.top }}
        >
          {children}
        </div>,
        document.body,
      )}
    </>
  )
}
