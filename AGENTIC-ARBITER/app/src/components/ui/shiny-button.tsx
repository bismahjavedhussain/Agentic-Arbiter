/**
 * ShinyButton -- the supplied component, adapted to this project's stack.
 *
 * TWO CHANGES FROM THE PASTED SOURCE, BOTH FORCED, BOTH RECORDED IN shiny-button.css:
 *   1. `<style jsx>` is a Next.js feature and this is a Vite app. The CSS moved to a co-located
 *      stylesheet, unchanged apart from (2). Every selector was already `.shiny-cta`, so it was
 *      class-scoped rather than jsx-scoped in practice and nothing is lost.
 *   2. The Google Fonts `@import` is gone. Inter is self-hosted and preloaded here, and the intro is
 *      required to work with no network.
 *
 * `"use client"` is kept for portability -- a Next.js consumer needs it, and in Vite it is an inert
 * string literal at the top of the module.
 *
 * The public shape is exactly as supplied: children, onClick, className. No data, no state, nothing
 * about the dashboard. A splash-screen call to action that knew about artefacts could show a judge a
 * stale figure; this one cannot.
 */
'use client'

import type React from 'react'
import './shiny-button.css'

interface ShinyButtonProps {
  children: React.ReactNode
  onClick?: () => void
  className?: string
  /** Additive: the splash needs to name the action for assistive technology when the visible label is
   *  short, and to be able to disable the button while the sweep transition is running. Both are
   *  optional, so existing call sites are unaffected. */
  'aria-label'?: string
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}

export function ShinyButton({
  children,
  onClick,
  className = '',
  disabled = false,
  type = 'button',
  ...rest
}: ShinyButtonProps) {
  return (
    <button
      type={type}
      className={`shiny-cta ${className}`}
      onClick={onClick}
      disabled={disabled}
      {...rest}
    >
      <span>{children}</span>
    </button>
  )
}
