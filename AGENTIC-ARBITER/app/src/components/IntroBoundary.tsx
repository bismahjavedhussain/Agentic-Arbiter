import { Component, type ErrorInfo, type ReactNode } from 'react'

/**
 * 🔴 A DECORATIVE LAYER MUST NEVER BE ABLE TO BLANK THE PRODUCT.
 *
 * This exists because it happened. `HeatGlobe` constructs a `THREE.WebGLRenderer`, which THROWS rather
 * than returning null when the browser has no WebGL context. Thrown from a `useEffect` with nothing
 * catching it, React unmounts the whole tree: measured with `--disable-webgl`, `#root` went from one
 * child to zero and the page was empty. The agent, the map, the panels and the report all disappeared
 * because a background animation could not start.
 *
 * The renderer is now guarded at its own call site, which fixes that particular throw. This is the
 * general answer to the class: everything under `intro/` is scenery, and scenery failing must cost the
 * reader the scenery and nothing else.
 *
 * WHY A CLASS. Error boundaries are the one thing React still has no hook for; `componentDidCatch` and
 * `getDerivedStateFromError` are only available on a class. That is the whole reason this file is not
 * written like everything else in this directory.
 *
 * ⚠ IT CATCHES RENDER AND LIFECYCLE ERRORS, NOT ASYNCHRONOUS ONES. A throw inside a `setTimeout`, a
 * rejected promise or an event handler never reaches a boundary, which is why `launch.ts` wraps its own
 * timeline construction and `audio.ts` wraps every `play()`. This is the last line, not the only one.
 */
type Props = { children: ReactNode }
type State = { failed: boolean }

export class IntroBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    /* Logged, not surfaced. A reader whose graphics card is disabled should see the product, not a
       stack trace; a developer with the console open should see exactly what went wrong. */
    console.error('[intro] the motion layer failed and was dropped:', error, info.componentStack)
  }

  render(): ReactNode {
    /* NOTHING is rendered in its place. The intro is additive by construction -- the page underneath is
       complete without it -- so the honest fallback is its absence rather than a placeholder
       apologising for a thing the reader never knew was coming. */
    if (this.state.failed) return null
    return this.props.children
  }
}
