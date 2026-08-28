# CONTEXT - start here

This folder is the durable memory of the **AGENTIC-ARBITER** project. It exists so that a session
which has lost its history can recover the state of the work without re-deriving it, and without
guessing.

**If you are an assistant picking this repository up, or you have just been through a context
compaction: read this file, then `01-STATE.md`, then `04-STANDING-RULES.md`, before you do anything
substantive.** Those three are short by design. Everything else here is addressed on demand.

---

## 1. If you have sixty seconds

- **What this is.** An agent that decides, hour by hour, whether a data centre can cool itself with
  outside air instead of running its chillers. It uses FortyGuard's forecast of air temperature **2 m
  above the ground**, the height a ground-mounted condenser actually breathes, so the plant gets
  hours of notice instead of a thermometer reading of *now*.
- **What makes it defensible.** Every hour it releases carries a safety margin **measured from its own
  past errors** (conformal prediction), and where the site geometry defeats the physics it **refuses
  the hour rather than guess**.
- **What it ships as.** One self-contained HTML page, `AGENTIC-ARBITER/demo/index.html`. **No build
  step, no package.json, no node_modules.** That is a constraint, not an accident: see
  `02-ARCHITECTURE` section 1.
- **How it is proved.** `AGENTIC-ARBITER/src/run_all.py` runs the whole pipeline with **zero API
  calls** and exits non-zero on any failure. `audit.py` re-reads every published figure from the JSON
  that produced it. See `03-VERIFICATION`.
- **The three rules most easily broken by accident.** The live-agent card and button are permanent
  (`04-STANDING-RULES` C1). No em dashes in anything a reader sees (B2). Never claim a number you
  cannot point at a file for (A3).

---

## 2. What is in this folder

| File | What it is | Read it |
|---|---|---|
| `00-START-HERE.md` | this file: the index, the read order, and the update ritual | **always** |
| `01-STATE.md` | what is true **right now**: generated figures, the change log newest-first, what is green, what is pending | **always** |
| `04-STANDING-RULES.md` | the user's standing instructions and the security constraints | **always** |
| `02-ARCHITECTURE.md` | the shipped system: files, the single-page constraint, the map's two sources, the live path, the data artefacts | when you are about to change code |
| `03-VERIFICATION.md` | every check, what it proves, how to run it, its current verdict | when you are about to claim something works |
| `05-TRAPS.md` | tooling and environment traps that have already cost time here | when something behaves impossibly |
| `06-GLOSSARY.md` | every term this project uses that is not ordinary English | when you meet a word, or before writing for the user |
| `MEMORY-MIRROR.md` | the auto-memory files, mirrored verbatim. **Generated** | when you need a rule's exact wording |
| `sync_context.py` | the tool that keeps the derived parts of this pack true | see section 4 |
| `HANDOFF.md` | **deep reference, 406 KB.** 20 numbered top-level sections. The full project history, and the gotcha registry (§10, 195 entries) | **never whole.** Read the section you need |
| `READING-THE-AGENT.md` | **deep reference, 56 KB.** The agent explained for a beginner | by section |

### The reading budget, which matters
`HANDOFF.md` alone is about 100,000 tokens. Reading it whole would consume most of a context window
to learn things `01-STATE.md` states in a paragraph, and would leave no room to do the work. **Both
deep-reference documents are section-numbered so you can address a section without opening the
file.** Use `grep -n "^#" CONTEXT/HANDOFF.md` to see the map.

---

## 3. What is deliberately NOT in this folder

Kept where they are, because code reads them by path or because they are the project's public face:

- `README.md` (repo root) - the front door: how to run it, the headline figures, and the "what is
  honest" limitations.
- `AGENTIC-ARBITER/demo/README.md` - the verification table for the shipped page.
- `AGENTIC-ARBITER/PLAN.md` (173 KB) - the design record, with every claim cited.
- `API-USAGE.md` - the API spend ledger. Rewritten from the ledger by
  `testing/bump_spend_docs.py`, so never hand-edit its figures.
- The auto-memory at `~/.claude/projects/d--FGHackathon/memory/` - the **source of truth** for the
  standing rules. `MEMORY-MIRROR.md` here is a generated copy; editing the mirror changes nothing.
- The `*.log` / `*.err` files at the repo root - build transcripts. They still say INTAKE-ARBITER on
  purpose (`04-STANDING-RULES` C2).

---

## 4. How this folder stays true

A context pack that has drifted is worse than none: it does not merely fail to help, it misinforms
with the authority of a document that says "read this first". So the parts that **can** be derived
are derived, and the parts that cannot are marked as prose.

### The ritual, on every change
1. Make the change and verify it.
2. Add a dated entry at the **top** of the change log in `01-STATE.md`. Newest first, so the most
   relevant thing is the first thing read.
3. Update any other file in this pack the change touched. A new verifier goes in
   `03-VERIFICATION`. A new trap goes in `05-TRAPS`, or into `HANDOFF.md` §10 with a number if it is
   a domain gotcha. A new term goes in `06-GLOSSARY`.
4. Run it:
   ```
   python CONTEXT/sync_context.py --write     # regenerate the derived parts
   python CONTEXT/sync_context.py --check     # must exit 0
   ```
5. Only then report the work as done.

### What the tool checks, and what it cannot
It **regenerates** two things: `MEMORY-MIRROR.md` from the auto-memory directory, and the `FIGURES`
block in `01-STATE.md` from the shipped artefacts.

It **asserts** five more, and fails on any of them:
- every file this pack is supposed to contain, the two deep-reference documents included, because
  `audit.py` now opens both through a `CONTEXT/` path;
- that `CLAUDE.md` still exists at the repo root and still points at this file. **That is the whole
  mechanism.** Delete `CLAUDE.md` and the pack silently stops being read, with nothing anywhere
  reporting that anything is wrong;
- that `#livecard` and `#livego` are still in the page (`04-STANDING-RULES` C1);
- that the map still has its second, flat GeoJSON source (`02-ARCHITECTURE` section 3);
- that the mirror and the figures have not drifted.

**It does not check the prose.** Judgement, history and reasoning cannot be re-derived from files, and
the tool says so in its own verdict rather than implying otherwise. Keeping the narrative true is a
human act, done in step 3.

### If a rule here conflicts with what the user just said
The user wins, and this pack is wrong. Fix it in the same turn, and fix the auto-memory source too,
or the next `--write` will put the old rule back.

---

## 5. Orientation: where the work lives

```
d:\FGHackathon\
  CONTEXT\                  <- this folder
  AGENTIC-ARBITER\
    demo\                   <- what ships: index.html + its JSON artefacts
    src\                    <- the agent, the audit, run_all.py
    PLAN.md
  testing\                  <- the verifiers, the pre-registered tests, the API probes
  README.md
  .env                      <- the real credential. gitignored. NEVER print it
  INTAKE-ARBITER\           <- empty husk of the old name. Safe to delete when unlocked
```

Full detail in `02-ARCHITECTURE`.
