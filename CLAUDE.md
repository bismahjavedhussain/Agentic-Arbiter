# FGHackathon - AGENTIC-ARBITER

## Read the context pack first

**Before doing anything substantive in this repository, read `CONTEXT/00-START-HERE.md`.** It is the
index for `CONTEXT/`, which holds the durable state of this project: what is built, what is verified,
what the standing rules are, and which traps have already cost time here.

This applies at the start of a session **and again after every context compaction**. A compaction
drops the detail of what was just done and why; `CONTEXT/` is where that detail is kept so it can be
recovered rather than guessed.

Always read, in this order, and they are short on purpose:

1. `CONTEXT/00-START-HERE.md` - the index, the read order, the update ritual
2. `CONTEXT/01-STATE.md` - what is true right now, and the change log newest-first
3. `CONTEXT/04-STANDING-RULES.md` - the user's standing instructions and the security constraints

Read on demand, by section: `02-ARCHITECTURE.md`, `03-VERIFICATION.md`, `05-TRAPS.md`,
`06-GLOSSARY.md`.

**Never read `CONTEXT/HANDOFF.md` (406 KB) or `CONTEXT/READING-THE-AGENT.md` (56 KB) whole.** They are
deep reference, section-numbered. `grep -n "^#" CONTEXT/HANDOFF.md` gives the map; read the section
you need. HANDOFF.md §10 is the gotcha registry, and code comments cite it by number
(`gotcha #67` means entry 67 there).

## Keep the context pack current

`CONTEXT/` is updated as **part of** every change, not afterwards. The ritual is in
`00-START-HERE.md` section 4. Before reporting any work as done:

```
python CONTEXT/sync_context.py --write
python CONTEXT/sync_context.py --check     # must exit 0
```

That tool regenerates what can be derived and fails on drift. It does **not** check the prose, so the
change log entry and any narrative updates are still yours to write.

## The constraints most easily broken by accident

Stated here as well as in the pack, because getting these wrong has already cost real trust. The
authoritative versions and their history are in `CONTEXT/04-STANDING-RULES.md`.

- **The live agent is permanent.** `#livecard` and `#livego` in `AGENTIC-ARBITER/demo/index.html` are
  never removed, never relocated, never replaced with another surface. A UI brief that mentions both
  static and live modes is a *constraint on the UI work*, not a request for new live features.
- **No em dashes** in anything a reader sees: page copy, README prose, commit messages. Ordinary
  hyphens in compound words are fine. Do not sweep the user's own existing prose without asking.
- **No unverified claims.** If you state a number, be ready to name the file it was read from.
  `audit.py` enforces this on published figures.
- **The API key** lives in the repository-root `.env`, is read only via `testing/common.py:load_key()`,
  and is never printed, echoed, logged or transmitted.
- **Paid FortyGuard calls cost 4,220 credits per hourly window.** Never spend without explicit
  direction.
- **Explain at beginner level.** The user is a second-semester CS student learning the theory while
  building. Define every term before using it; `CONTEXT/06-GLOSSARY.md` is the shared glossary.

## Shape of the work

- **There are two front ends right now, and that is deliberate and temporary.**
  - `AGENTIC-ARBITER/demo/index.html` is the CANONICAL one: one self-contained page, no build step,
    nothing to install. It is what the verification layer measures and what a judge opens today.
  - `AGENTIC-ARBITER/app/` is a **Vite + React + TypeScript + Tailwind** rebuild, started 2026-08-28
    at the user's direction so the 21st.dev MCP server and the `frontend-design` skill can act on
    real components. It has a `package.json` and a bundler **on purpose**. Do not "restore" the
    single-file constraint over it; read `CONTEXT/01-STATE.md` section 0 first.
  - The five cross-implementation verifiers no longer extract functions out of the page by string
    search. They `import` from `AGENTIC-ARBITER/core/`, and `run_all.py` step 29 asserts that core
    and the page are still the same code. That is what made the React work safe.
  - The built app is designed to be dropped into `demo/`, where the same relative fetches resolve, so
    **the shipped artefact still has no install step** even though the source now has a build.
- `AGENTIC-ARBITER/src/run_all.py` proves the whole pipeline with **zero API calls**.
- Verifiers live in `testing/`. `AGENTIC-ARBITER/src/audit.py` is the mechanical audit.
