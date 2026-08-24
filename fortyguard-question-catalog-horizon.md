# To FortyGuard — two activity IDs, and one question

**Status: READY TO SEND.**
**Rewritten 2026-08-21 after DIAG-64.** The first draft asked only about the catalog's forward
extent. DIAG-64 then measured something sharper and unambiguous, so the report leads with that and
the horizon question follows it.

---

## What DIAG-64 measured

Two `/v1/heatmap` calls, ten minutes apart, **identical in every field except the target window**:
same AOI (8×8 km on 39.024017, −77.419691), same `granularity: 60`, same `analytic_type: "tcm"`,
same 2-hour window, same `filter_type: 2`.

| | window (site-local, `America/New_York`) | = UTC | lead | result |
|---|---|---|---|---|
| **CONTROL** | 2026-08-21 09:00–11:00 | 13:00–15:00 | **−3.23 h (already elapsed)** | `completed`, **0 cells** |
| **PROBE** | 2026-08-21 14:00–16:00 | 18:00–20:00 | **+1.60 h** | `completed`, **0 cells** |

Both took ~607 s and ~59 status polls before we stopped waiting. Both were **billed 4,220**.

**The control is the important one.** A window three hours in the past cannot be beyond the forward
end of a catalog, so its emptiness is not explained by the timezone/horizon issue at all. Until
2026-08-20, past-window requests over this AOI worked reliably at every hour of the day — that is the
one thing that had been constant through a week of forecast trouble.

---

## Suggested message

> Hi Fawad,
>
> Thank you for the `America/Phoenix` answer in the channel — it prompted us to test something, and
> the test found a separate problem we think is on your side. Two activity IDs, both over an 8×8 km
> AOI centred on **39.024017, −77.419691** (Loudoun County, VA):
>
> | | window (site-local `America/New_York`) | = UTC | result |
> |---|---|---|---|
> | `14742335-957b-429a-8c12-ee898fb8f889` | 2026-08-21 **09:00–11:00** — already elapsed | 13:00–15:00 | `completed`, `n_cells: 0` |
> | `f314239b-…` | 2026-08-21 **14:00–16:00** — 1.6 h ahead | 18:00–20:00 | `completed`, `n_cells: 0` |
>
> Both were submitted at about **16:15 UTC on 2026-08-21**, ten minutes apart, and are identical in
> every field except the window: `granularity: 60`, `analytic_type: "tcm"`, `filter_type: 2`, same
> polygon. Both returned `status: completed` with `"features": []` after ~600 s and ~59 status polls,
> and both were billed 4,220.
>
> **The first one is why we are writing.** It is a window that had already finished three hours
> earlier, so it cannot be past the end of the catalog — and history requests over this same AOI
> worked reliably at every hour of the day until 2026-08-20. Something changed.
>
> To save you asking: **we are already sending AOI-local times.** We found that behaviour on
> 12 August and build every window in the AOI's own zone (`America/New_York` here,
> `America/Chicago` for our Illinois site). `"09:00"` above means 09:00 Eastern = 13:00 UTC, which is
> what we intended.
>
> **Two questions:**
>
> **(a) Is there a current incident affecting this AOI?** If so we will simply stop calling until it
> clears — we have disabled our scheduled collectors in the meantime.
>
> **(b) How far ahead of "now" does the catalog extend, and is there a *free* way to ask what the
> last available hour is before submitting?** This is the one from your Phoenix answer. Our
> calibration series targets 14:00 site-local at a 6–11.5 h lead, which forces a morning call for an
> 18:00 UTC window, and if that is structurally past the catalog's end then the series has been
> asking for data that does not exist yet and we will redesign it. A field on the usage or status
> endpoint giving the last available hour would turn a 4,220-credit guess into a free check — it is
> the single most useful thing you could give us.
>
> **One data point that does not fit either explanation, in case it helps you:** on **2026-08-19 at
> 13:35 UTC** we requested 19:00–21:00 site-local (**23:00–01:00 UTC**) — a 9.41 h lead — and it
> returned **17,862 tiles** of genuinely new values, activity
> `f333f605-6ef6-4847-9bbf-1d22910ebcb6`. If there were a hard forward limit of a few hours, that
> call should have come back empty.
>
> **And one suggestion, offered constructively:** a job that reports itself `completed` while
> carrying an empty `features` array is currently billed in full — the two calls above cost 8,440
> for nothing, and we are at roughly 227,000 credits of empty-but-billed responses overall. You
> already made `status: failed` and stalled jobs unbilled, which we noticed and appreciated. Treating
> `completed`-with-`n_cells: 0` the same way would be consistent with that, and it would also remove
> the incentive for clients to keep retrying blind.
>
> Happy to share the full request log or a `curl` that reproduces either call.

---

## Our own position, for the record

**DIAG-64's verdict is VOID for its own hypothesis, and that was pre-registered.** The test was
designed to ask whether our empty forecast responses were windows past the catalog's forward end, by
requesting the collector's exact window at a 1.6 h lead instead of the 9.5 h lead the schedule
forces. That comparison only means something if the vendor is answering *at all*, which is why a past
window was included as a positive control. The control came back empty, so the probe cannot
distinguish a forward limit from a general fault, and **no conclusion about the horizon may be drawn
from this run.** Gotcha #59: a negative that repeats is evidence about a PERIOD, never a CAPABILITY.

**What DIAG-64 does establish:** as of 2026-08-21 16:15 UTC, this AOI returns `completed` with zero
cells for **both** a past and a near-future window. That is a vendor-side fault and it is not the
timezone issue.

**So `fortyguard-report-2026-08-20-jobs-not-completing.md` is UNBLOCKED** — the concern that it
blamed the vendor for our own request pattern is not supported: a past window failing is squarely
theirs. ⚠ But its framing should be **widened from "forecast windows" to "windows in general"**
before sending, because it currently describes a forecast-path fault and we have now measured the
same signature on history.

**The horizon question stays open and still needs answering**, because it may well explain
2026-08-18..20 — where past windows worked and future ones did not — even though it cannot explain
today. Those are two different faults and we cannot separate them until history works again.
