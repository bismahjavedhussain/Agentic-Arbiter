import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
/* 🔴 ORDER MATTERS AND IT IS DELIBERATE.
   engine.css is the page's own 96 KB stylesheet, lifted verbatim, because the configure and results
   markup in generated/engine-markup.ts is written against its classes and tokens. It comes FIRST so
   that where the two stylesheets define the same thing, the app's own design wins. They are not in
   conflict by accident: testing/verify_palette.py asserts 34 page/app colour pairs agree. */
import './generated/engine.css'
import './index.css'
/* LAST, because the workspace re-measures and re-hides what the other two lay out: it overrides
   .viz-root's 1180px measure, collapses .side's two columns and decides which panels are on screen.
   A separate file rather than more of index.css so that "what the tabs do" is one thing to read, and
   so removing the workspace is removing one import. */
import './workspace.css'
/* And the dashboard arrangement last: it styles the rail groups, the quick actions and the
   panel entrance, all of which sit on top of what workspace.css lays out. */
import './dashboard.css'
import { App } from './App'

const el = document.getElementById('root')
if (!el) throw new Error('no #root to mount into')
createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
