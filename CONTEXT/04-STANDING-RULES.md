<!-- Part of CONTEXT/. Read 00-START-HERE.md first. -->

# 04 - Standing rules

**Read this file in full, every session.** These are not preferences to weigh against convenience.
They were each stated directly by the user, most of them after I had already got them wrong once.

The machine-readable copies live in the auto-memory at
`~/.claude/projects/d--FGHackathon/memory/`, mirrored verbatim into `CONTEXT/MEMORY-MIRROR.md`. That
mirror is **generated**, so it cannot drift. This file is the expansion: what the rule means in
practice, and what breaking it looked like.

---

## A. Rules about the work itself

### A1. Ship production, not an MVP
Stated 2026-08-18 as non-negotiable for the entire rest of the build.

1. A fully functioning end-to-end solution. *"It demonstrates the idea"* is not a stopping point.
2. A genuine urban-heat problem with real impact and commercial value, not a toy framing chosen
   because it was tractable.
3. **Conformal prediction done as it is supposed to be done.** Marginal-only coverage applied outside
   its calibration domain is not acceptable. Group-conditional (Mondrian) plus adaptive (ACI/DtACI)
   is the standard, and the distribution-free *conditional* impossibility result must be stated
   rather than papered over.
4. Every claim in `AGENTIC-ARBITER/PLAN.md` carries a real citation with a link, verified by opening
   the source, never from a search snippet.
5. FortyGuard's data wired in deeply, not as a crumb: the environmental parameters that genuinely
   change the physics or the decision, with a cited reason for each.

**How to apply.** When a shortcut would leave a stage stubbed, simulated or statistically
unjustified, build the real thing. If something genuinely cannot be built in the time, say so
explicitly and in full rather than shipping a hollow version.

### A2. A complete agent. No thresholds in costume
Stated 2026-08-15, emphatically, with *"Please never forget this"*:

> "i dont get what makes the system agentic and autonomous. I dont care much of what track 06 thinks
> makes a system agentic. I want a complete agent. No thresholds, if conditions or a simple
> dashboard."

**The trap this closes.** I once argued that the hackathon track's wording set a lower bar than the
one the project was failing, and offered that as a reason to relax the requirement. That reasoning
was rejected outright. **Citing the track text, the judges' backgrounds or the rubric as a reason to
accept weaker agency is not a valid argument here, and offering one costs trust.**

**The falsifiable test**, which the user can run themselves: *can you point at the constant in the
source code that produces this behaviour?* If yes, it is a threshold in costume. Label it as such;
do not defend it. Say plainly which components are genuinely agentic and which are only computation.
Never use the word "just" to wave away a gap.

### A3. No unverified claims
A figure in prose is a figure nothing re-reads. Every published number is re-read from the artefact
that produced it by `audit.py` checks 9 and 10. If you state a number, be ready to name the file.
This is the reason `CONTEXT/01-STATE.md`'s figures are generated rather than typed.

---

## B. Rules about how to communicate

### B1. Explain at beginner level
The user is a second-semester CS student building this solo, studying conformal prediction, decision
theory and psychrometrics **while** building. A term appearing in their own project documents does
not mean they know it yet.

- Define jargon on first use, in plain language, before building on it.
- Put a short glossary near the front of any document written for them. `CONTEXT/06-GLOSSARY.md` is
  that glossary for this folder.
- Prefer a concrete analogy over a formal definition.
- They ask sharp follow-up questions and will catch an overstated claim. **When they push back,
  check whether they are right before defending, and say plainly if they are.**

Unexplained jargon (METAR, hindcast, residual, calibration set, effective sample size) once made a
document they had to act on unusable and stalled an approval.

### B2. No em dashes
Stated 2026-08-28: *"Never use ehmm dashes"*. Applies to page copy, README prose, commit messages,
and anything else a reader sees. En dashes and the horizontal bar are out for the same reason;
ordinary hyphens in compound words (hour-by-hour, ground-mounted) are fine.

**Why it is worth obeying rather than treating as taste.** An em dash is the easiest way to bolt a
second thought onto a finished sentence, and it was doing exactly that in three of the four masthead
paragraphs. Removing them forced one thought per line, which is most of what made that block shorter.

**Stated in the same breath:** the masthead is a header plus **2 to 3 lines**, not four paragraphs.
When prose has to go somewhere, use the `.info` popover pattern already in the page: the claim stays
on the same element one interaction away, and it sits in the trigger's `aria-label` so it is not lost
to a reader who cannot hover.

> **Do not sweep the user's own prose.** The copy deeper in the page still contains many em dashes
> they wrote themselves. Ask before rewriting those. This rule governs what *I* write.

---

## C. Rules about the product's surfaces

### C1. The live agent is permanent
The `#livecard` panel at the results stage and its `#livego` button are fixed. Never remove them,
never move them to another screen, never replace them with a different surface (a dialog, a masthead
panel, a bezel control).

Stated 2026-08-27: *"dont ever remove the live agent working and its button from there"*. Earlier the
same day I had relocated the mode statement into a bezel lamp and added an agent-link dialog with its
own live controls; the response was that this *"completely changed the dynamic"*.

**A UI brief that mentions both static and live modes is a CONSTRAINT on the UI work, not a request
for new live features.** That misreading is what caused the incident.

Treat as fixed: `#livecard`, `#livego`, `probeLive()`, `drawModeBanner()`, `drawLiveUnavailable()`,
`drawLiveCost()`, `runLive()`. UI work may restyle them (colour, type, the disabled state's
appearance) but must not change where they are, what they are, or what they say. If a live-path
change seems necessary, **ask first**.

`sync_context.py` asserts `#livecard` and `#livego` are still present on every check, so this rule
has a mechanical tripwire rather than only a note.

### C2. The project is AGENTIC-ARBITER
Renamed from INTAKE-ARBITER on 2026-08-27. The folder is `AGENTIC-ARBITER/`. The rename covered
2,737 string occurrences across 2,649 files, the split bezel wordmark (`Agentic·Arbiter`, two spans,
so invisible to a literal search), and all 266 generated report PDFs, which were **regenerated** with
`report.py` rather than byte-patched, because a PDF's xref table is byte-offset addressed and the new
name is one byte longer.

**Two things deliberately keep the old name**, and both are records rather than code: the build
`*.log` / `*.err` files at the repo root (a log is a transcript of a past moment; rewriting one makes
it a transcript of something that never happened) and `report (7).pdf` at the root, a stray browser
download.

An empty `INTAKE-ARBITER/` husk still exists. The editor's file watcher holds the directory, so it
cannot be removed. It is safe to delete once the editor releases it.

---

## D. Rules about delegation

### D1. Subagents and workflows are permitted, since 2026-08-23
*"eliminate rule 9 and use subagents/workflows or Task tools when needed."* Documented as lifted in
`HANDOFF.md` §1 rule 9 and §9.-1 item 5.

**But:** delegate SEARCH and independent VERIFICATION, never the judgement. Every other rule binds a
subagent exactly as it binds the main session, especially A3 (no unverified claims) and E2 (ask
before every paid call). **Confirm every subagent finding against the actual artefact before it
reaches a document or a fix.** A fan-out that returns plausible prose is the project's own gotcha #47
("my verification code was buggier than the product") at N times the volume.

---

## E. Security and spend

These are not preferences. Treat them as hard constraints.

### E1. The API key
The real FortyGuard credential lives in the **repository-root `.env`**, which is gitignored and
untracked (as is `AGENTIC-ARBITER/.env`). It is read only through `testing/common.py:load_key()`.
**Never print, echo, log or transmit its value.** See `05-TRAPS` section 4.1 for the trap where the
`.env` is created in the wrong directory.

### E2. Paid calls
A live paid run costs **4,220 credits per hourly window**, so **50,640** for a 12-hour horizon.
`serve_live.py` requires two independent keys to spend: the `--allow-paid` flag on the server *and* a
flag on the request. **Do not spend without explicit direction.**

### E3. Do not blanket-kill processes
`Get-Process chrome | Stop-Process -Force` closed the user's own browser. Kill by the specific PID
you spawned.

---

## F. How this folder stays true

`CONTEXT/` is updated as part of every change, not after it. The mechanics are in
`00-START-HERE.md` section 4. The short version:

1. Make the change and verify it.
2. Add a dated entry at the top of `01-STATE.md`'s change log.
3. Update any other doc in the pack the change touched.
4. Run `python CONTEXT/sync_context.py --write`, then `--check`.
5. Only then report the work as done.

If a rule in this file is ever contradicted by something the user says, **the user wins and this file
is wrong**. Update it in the same turn, and update the auto-memory source too, or the mirror will put
the old rule back.
