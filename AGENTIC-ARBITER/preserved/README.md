# preserved/

A frozen copy of the single-file page, kept at the user's request on 2026-08-28:

> "If you have these same layouts that were previously in the html file even now, then good, dont
> lose these layouts. That is exactly how my html file was and I would want that we do keep a copy of
> that anywhere else on disk maybe so that we can always go back if we dont like react."

## What is here

`index-2026-08-28-dense-report.html` is `demo/index.html` exactly as it stood on 2026-08-28, before
any decluttering of the results stage. Open it over HTTP and it works on its own: one file, no build
step, nothing to install. It is the dense scrolling report layout, which is the thing being changed.

## Two things worth knowing

**This is a belt-and-braces copy, not the only one.** `demo/index.html` is still the canonical page
and is still unchanged; the React app renders the page's *lifted* markup rather than editing it, so
redesigning the app cannot damage the page. Every commit in git also holds the page at that point in
time. This copy exists so that going back does not require knowing any git commands.

**Nothing verifies this file, on purpose.** `audit.py` and the verifiers read `demo/`, not here, so
this copy is allowed to go stale as the page moves on. That is the point of a snapshot. If you want
today's page instead, copy `demo/index.html` again.
