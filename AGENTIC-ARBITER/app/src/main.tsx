import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
/* 🔴 ORDER MATTERS AND IT IS DELIBERATE.
   engine.css is the page's own 96 KB stylesheet, lifted verbatim, because the configure and results
   markup in generated/engine-markup.ts is written against its classes and tokens. It comes FIRST so
   that where the two stylesheets define the same thing, the app's own design wins. They are not in
   conflict by accident: testing/verify_palette.py asserts 34 page/app colour pairs agree. */
import './generated/engine.css'
import './index.css'
import { App } from './App'

const el = document.getElementById('root')
if (!el) throw new Error('no #root to mount into')
createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
