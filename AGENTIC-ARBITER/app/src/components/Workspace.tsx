import { motion } from 'framer-motion'
import { TABS, type TabId } from '../lib/tabs'

/**
 * The tab rail: the workspace's navigation, and the only new owner of anything on this page.
 *
 * It owns ONE fact, "which tab is active", published as `data-aa-active` on the workspace element.
 * index.css turns that into a display rule keyed on each panel's `data-aa-tab`. setStage() goes on
 * owning `hidden`, untouched, so #livecard is still governed by the stage machine exactly as standing
 * rule C1 requires.
 *
 * A LOCKED TAB IS DISABLED, NOT HIDDEN. Before the agent has run, the results panels hold no data,
 * so five of the six tabs would show empty frames. They stay listed and greyed with the reason
 * attached, because a reader who can see where the work is going understands the flow; a nav that
 * grows items as you go teaches nothing and looks broken.
 */
export function TabRail({
  active,
  unlocked,
  onSelect,
}: {
  active: TabId
  unlocked: TabId[]
  onSelect: (id: TabId) => void
}) {
  return (
    <nav className="aa-rail-nav" aria-label="Workspace sections">
      <p className="aa-rail-eyebrow">Workspace</p>
      <ul>
        {TABS.map((t) => {
          const isOpen = unlocked.includes(t.id)
          const isActive = active === t.id && isOpen
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => isOpen && onSelect(t.id)}
                /* 🔴 THE ONE AFFORDANCE FOR THE BROWSER CHECK, and it is here rather than in the
                   check because the alternative is worse. verify_app_flow.py has to open each tab and
                   confirm that tab's panels are visible, which is how "all thirteen cards render"
                   survives being split across tabs. Without this it would have to assume the Nth
                   button is the Nth entry of TABS, which is true today and silently wrong the first
                   time the order changes. An id on the control it clicks costs nothing and cannot
                   drift from the id in `data-aa-tab`, because both come from `t.id`. */
                data-aa-tabid={t.id}
                disabled={!isOpen}
                aria-current={isActive ? 'page' : undefined}
                aria-disabled={!isOpen}
                title={
                  isOpen
                    ? t.blurb
                    : t.needs === 'results'
                      ? 'Available once the agent has run'
                      : 'Available once a site is configured'
                }
                className={`aa-tab ${isActive ? 'is-active' : ''} ${isOpen ? '' : 'is-locked'}`}
              >
                {/* 🔴 ONE SHARED layoutId, WHICH IS WHY THE HIGHLIGHT SLIDES RATHER THAN BLINKS.
                    framer-motion matches the element across renders by layoutId and animates the
                    difference, so the indicator travels between tabs without either tab animating
                    its own box. Rendered only for the active tab, which is what makes it single. */}
                {isActive && (
                  <motion.span
                    layoutId="aa-tab-marker"
                    className="aa-tab-marker"
                    transition={{ type: 'spring', stiffness: 520, damping: 38, mass: 0.7 }}
                  />
                )}
                <span className="aa-tab-label">{t.label}</span>
                {!isOpen && (
                  <svg
                    className="aa-tab-lock"
                    width="11"
                    height="11"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.4"
                    strokeLinecap="round"
                    aria-hidden="true"
                  >
                    <rect x="4.5" y="10.5" width="15" height="10" rx="2.2" />
                    <path d="M8.4 10.5V7.8a3.6 3.6 0 0 1 7.2 0v2.7" />
                  </svg>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/**
 * The heading strip above the active tab's panels. Two lines, never more: the brief asks for punchy
 * statements with the depth behind a click, and the depth is already inside the panels.
 */
export function TabHeader({ active }: { active: TabId }) {
  const tab = TABS.find((t) => t.id === active)
  if (!tab) return null
  return (
    <motion.header
      /* Keyed on the tab, so switching tabs replaces this element and the transition runs. Without
         the key React would reuse it and only the text would swap, with no motion at all. */
      key={tab.id}
      className="aa-tabhead"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      <h2>{tab.label}</h2>
      <p>{tab.blurb}</p>
    </motion.header>
  )
}
