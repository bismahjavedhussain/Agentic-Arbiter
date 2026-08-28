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
/* LAST OF ALL. The cinematic shell re-skins the chrome the previous three laid out and fixes
   two things by specificity that equal-specificity rules could not: the repeated .secgroup
   heading, and the panel column being the only scroll region. */
import './cinematic.css'
/* And polish.css after all of them: every rule in it was written against a MEASURED computed
   style, and several deliberately override engine.css, so it has to be able to win. */
import './polish.css'
/* The tone system last of all: it is the single place that decides what colour a KIND of
   widget is, so it has to be able to override every earlier sheet including engine.css. */
import './tones.css'
/* Truly last: the backdrop wordmark, the tab-heading strip and the first-screen copy all sit on
   top of the tone system and have to be able to override it. */
import './masthead.css'
/* BEFORE App, and therefore before EngineStage's layout effect calls setStage('pick'). The shim
   only suppresses a scroll-to-top when the stage has not changed, so the boot scroll still happens;
   installing early just means no re-run can slip past it. */
import { installNoScrollJump } from './lib/noscrolljump'

installNoScrollJump()

import { App } from './App'

const el = document.getElementById('root')
if (!el) throw new Error('no #root to mount into')
createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
