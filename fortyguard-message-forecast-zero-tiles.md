# Message to FortyGuard — ⚠ DO NOT SEND AS DRAFTED, REWRITE FIRST

> **🔴 SUPERSEDED 2026-08-19 13:35 UTC. The forecast path RECOVERED.** One paid call at identical
> parameters returned **17,862 tiles at a 9.41 h lead**, and the automated collector had failed five
> hours earlier the same day — so this was a **vendor-side outage, not a plan entitlement limit**.
>
> **This draft's central question — "does the Hackathon plan include forecast windows?" — is now
> answered: YES. Sending it as written would report a defect that has resolved and would read as
> though we had not checked.**
>
> **The report still worth sending is a different one, and it is genuinely useful to them:** for
> roughly 30 hours (2026-08-18 → 2026-08-19 08:30 UTC) forecast requests returned `HTTP 200` +
> `status: completed` + zero `features` **and were billed 4,220 credits each** — seven of them,
> ≈29,540 credits — with nothing on the status endpoint to distinguish an incident from an empty
> area, an out-of-horizon window, or a permission failure. Recovery at 13:35 UTC, `activity_id`
> `f333f605-6ef6-4847-9bbf-1d22910ebcb6`. Ask for: an incident signal, a non-`completed` status on
> failure, and no billing for an empty result. See `fortyguard-api-findings.md` §10.7.

# (original draft below — kept for the activity IDs and the request table)

Drafted 2026-08-19. **Rewritten to report ONLY evidence from the current Hackathon key**, at the
user's instruction. No other key and no earlier usage is referenced anywhere.

**The comparison is stronger this way:** same key, same request shape, **past window vs future
window**. Nothing depends on comparing across two credentials.

Activity IDs are request identifiers, not credentials — safe to share.
**Do not paste the API key. Do not mention the subscription start date** (it invites questions about
what came before).

---

## SHORT VERSION — Discord / live Q&A

> Hi — one question about the Hackathon plan, plus a bug report.
>
> **Does the Hackathon plan include forecast (future-window) `/v1/heatmap` requests?**
>
> On my key, a **past** window works perfectly: 8×8 km, `granularity: 60`, `analytic_type: tcm` →
> **17,862 features**.
>
> The **identical** request shape for a **future** window returns HTTP 200, `status: "completed"`,
> `n_cells: 0`, an empty `features` array — and is billed 4,220 credits each time. Five attempts,
> five empty responses, at leads from 2.3 h to 9.4 h:
>
> - `8a18e777-d247-4dc3-8fc2-e9139db5f483` — 8.6 h ahead
> - `b3e4a367-14ad-4680-9409-0c8633f327a7` — 9.4 h ahead
> - `8989544f-d961-4bed-9ef4-a56473bd98a8` — **2.3 h ahead**
> - `fdff9e40-49e7-4fd2-bd30-67c4f851090d` — 8.9 h ahead
> - `d5f6c9d1-3f48-49d9-86da-3869cc81ffd6` — 8.2 h ahead, **58 polls over 607 s**
>
> The **2.3 h** one is why I don't think this is the 12-hour horizon.
>
> **And thank you for Qusay's point 3 — that was a real bug in mine.** I was returning on the first
> `Completed` without checking `map_data.features`. I've fixed the loop to keep polling until the
> data fields populate, and the last entry above is that fixed version: 58 polls over 607 seconds,
> `features` never populated. So this one isn't a premature read either. For comparison, the
> past-window request populates in about 45 seconds.
>
> If forecasts simply aren't in the plan, that's completely fine — I just need to know, because my
> project measures forecast accuracy and I'd rather document the limitation honestly than keep
> retrying. If they *are* included, something looks wrong on the forecast path.

---

## FULLER VERSION — email or support ticket

**Subject:** Hackathon plan — future-window `/v1/heatmap` returns `completed` with zero tiles (and is billed)

Hello,

I'm building a hackathon project on the temperature API and I've hit something I can't resolve from
the documentation. One question first, then the evidence.

### The question

**Does the Hackathon plan include forecast (future-window) `/v1/heatmap` requests?**

If it doesn't, that's genuinely fine — I'll state the limitation in my submission and stop
retrying. I can't tell from `plan_details`, which returns no entitlement information:

```json
"plan_details": {"plan_type": "Hackathon", "cycle_type": "Hackathon",
                 "active": true, ...}
```

There's no field indicating which endpoints, which `analytic_type` values, or whether future
windows are permitted.

### What I observe on this key

**A past window succeeds.** This exact request returned **17,862 features** and was billed 4,220
credits (my `total_credits_used` moved 12,660 → 16,880, so it's visible in your logs):

```json
{"polygon_aoi": <8x8 km box centred 39.0100, -77.4460>,
 "granularity": 60,
 "analytic_type": "tcm",
 "date_time": {"start_date": "2026-08-16", "start_time": "14:00",
               "end_time": "16:00", "filter_type": 2}}
```

**The same request shape for a future window returns nothing.** HTTP 200, `status: "completed"`,
`n_cells: 0`, `features: []` — and is billed 4,220 credits each time:

| lead to window | features | activity_id |
|---|---|---|
| ~8.6 h | 0 | `8a18e777-d247-4dc3-8fc2-e9139db5f483` |
| 9.38 h | 0 | `b3e4a367-14ad-4680-9409-0c8633f327a7` |
| **2.29 h** | 0 | `8989544f-d961-4bed-9ef4-a56473bd98a8` |
| 8.86 h | 0 | `fdff9e40-49e7-4fd2-bd30-67c4f851090d` |
| 8.22 h | 0 — **after 58 polls over 607 s** | `d5f6c9d1-3f48-49d9-86da-3869cc81ffd6` |

The AOI, `granularity` (60) and `analytic_type` (`tcm`) are **identical** in all six requests
above — the one successful past window and the five empty future ones. I changed one thing at a
time.

### What I've ruled out

- **The 12-hour horizon.** A window only **2.29 h** ahead also returned zero. A horizon limit can't
  explain that when the same request shape returns 17,862 features for a past window.
- **Request size and granularity.** 8×8 km at `granularity: 60` works on this key — that's the
  successful call above.
- **Time of day.** Four of the five attempts fell within about an hour of one another, and one of
  them at the same time of day as a request that had succeeded for a past window.
- **A premature read.** Qusay's third point — that `map_data` can be empty on the first `Completed`
  poll — described a genuine bug in my code, which I've fixed: I was returning on the first
  `Completed` without checking `map_data.features`. But it doesn't explain this. After the fix, one
  future-window request was polled **58 times over 607 seconds** and `features` never populated
  (`d5f6c9d1-3f48-49d9-86da-3869cc81ffd6`). For comparison, the past-window request above returns a
  populated field in about 45 seconds.
- **A momentary outage.** Possible, but five consecutive empty responses across a 20-hour span,
  four of them within an hour, makes it less likely. I can't rule it out from my side, which is part
  of why I'm asking.

### Four suggestions, if they're useful

1. **Return an error rather than `completed` with zero tiles** when a request falls outside the
   plan's entitlement — an HTTP 403 with a reason, or any `status` other than `completed`. As it
   stands, an empty success is indistinguishable from an empty area, an out-of-horizon window, a
   transient failure, and a permission problem. **Four different causes, one identical response.**
2. **Don't bill a response that carries no data.** I've been charged **21,100 credits for five
   responses with zero tiles**. Total spend is only ~1.7 % of my allowance, so this isn't about the
   cost — it's that the billing record says "Heatmap Generation, success" for every one of them.
3. **Add an entitlement block to `plan_details`** — permitted endpoints, permitted `analytic_type`
   values, and whether future windows are allowed. That would let a consumer check *before* spending.
4. If forecasts **are** included and this is an incident, **a signal on the status endpoint** would
   have saved me five paid calls and two days of a time-boxed build.

### Why I'm asking rather than working around it

My project's headline safety number is the measured accuracy of a statistical bound placed on your
**forecast** temperatures — so forecast windows are the one thing I can't substitute. Historical
data works beautifully and I'm using a lot of it, but it can't tell me how far ahead the agent can
safely commit a cooling plant.

A plain yes or no genuinely unblocks me either way. Happy to share full request payloads or my
reproduction script if that helps.

Thanks for running the hackathon.

---

## Notes for whoever sends this

- **Never paste the API key.** The activity IDs are enough for them to locate every request.
- **Do not mention any other key, or the subscription start date.** Per instruction, and because it
  invites a tangent that doesn't help.
- If they answer **"forecasts are not in the Hackathon plan"** → update `HANDOFF.md` §4 and
  `fortyguard-api-findings.md` §10.3, and treat **65.6 %** as the final coverage figure.
- If they answer **"forecasts are included"** → it's an incident. The daily 13:30 PKT task is
  already the detector; a successful run resumes collection immediately.
- Either answer is worth having **in writing before submission**, because §10 of the API findings
  document is itself part of the deliverable.
