# FortyGuard `/v1/heatmap` — jobs accepted, never completed (2026-08-20)

**Hackathon'26 participant report. Written to be actionable rather than to complain: every claim
below has an `activity_id` you can look up, and the control experiment is included so you can rule
out the obvious client-side causes without asking.**

---

## 1. Summary in three sentences

`POST /v1/heatmap` accepts our request and returns `200` with an `activity_id`. `GET
/v1/status/{activity_id}` then answers `200` with `{"message": "Processing", "data": {"status":
"Processing"}}` on **every** poll and never changes — we polled **45 times over 425 seconds** and
the job never reached a terminal state. **The same request shape worked reliably until 2026-08-19**,
and an identical request for a **past** window fails in exactly the same way, so this is not about
forecast windows.

---

## 2. The exact request

Identical for both legs below except `start_date`. AOI is an 8 × 8 km box centred on
**39.0100, −77.4460** (Loudoun County, Virginia).

```json
POST https://api.fortyguard.com/v1/heatmap
{
  "polygon_aoi":   { "...8x8 km box centred on 39.0100, -77.4460..." },
  "granularity":   60,
  "analytic_type": "tcm",
  "date_time": {
    "start_date": "2026-08-20",
    "start_time": "14:00",
    "end_time":   "16:00",
    "filter_type": 2
  }
}
```

Then `GET /v1/status/{activity_id}` every 8 s.

---

## 3. What happened — three different failure modes in one day

All times UTC, 2026-08-20.

| Time | What we sent | Response | Billed |
|---|---|---|---|
| ~08:30, 08:50, 09:15 | forecast window, today 14:00–16:00 local | `status: completed`, **`map_data.features` empty** — after 59 polls / 608 s | **4,220 each** |
| ~10:48 | same | **`status: failed`** | 0 |
| 11:04 → 11:11 | same | **`status: Processing` for 45 polls / 425 s, never terminal** — `activity_id` **`f010f6e2-a311-48f7-990d-c6c554bb9686`** | 0 |
| 11:04 → 11:11 | **PAST** window, 2026-08-19 14:00–16:00 local | **identical: `Processing` for 45 polls / 424.8 s** — `activity_id` **`58ef42ba-10a9-46a8-8032-253b4b84cfa0`** | 0 |
| ~11:2x | forecast window, 1 h | `Processing`, 33 polls / 307 s — `activity_id` **`a89fef3f-c8a2-4a7e-95c1-f2d39fd35c3b`** | 0 |

**Three distinct presentations of what is probably one fault, inside about three hours.** We are not
claiming they share a root cause — that is your side of the wall — but a client sees three different
things and cannot tell whether it is one incident or three.

---

## 4. The control experiment, so you can skip the obvious questions

We ran a second leg **identical in every field except the date**, asking for a window that had
already elapsed. It stalled the same way. That rules out, from our side:

| Candidate cause | Ruled out because |
|---|---|
| Forecast/future windows specifically | a **past** window stalls identically |
| API key revoked or invalid | submits return `200` and issue `activity_id`s; the free usage endpoint answers normally throughout |
| Plan or quota exhausted | 1,945,140 of 2,000,000 credits remain (2.74 % used); a quota rejection would surface at submit |
| Daily heatmap cap (30/day) | well under it; and the cap rejects, it does not stall |
| The AOI, the granularity or `analytic_type` | byte-identical request shape returned 17,862 tiles on 2026-08-19 |
| Our polling logic | the status endpoint returns `200` and a well-formed body every time; it just never changes |

**Service is up.** `POST /v1/system/fetch-api-key-usage` answered correctly throughout. It appears
to be specifically the **heatmap job pipeline** that accepts work and does not finish it.

---

## 5. Billing behaviour changed today, and the change is in the right direction

- The **`completed` + empty `features`** responses on 08-18…08-20 were **billed 4,220 each**.
- The **`failed`** response and the **stalled `Processing`** jobs were **not billed**.

**That second behaviour is what we would ask for**, so if it was a deliberate change, thank you — it
is the correct call. We mention it only because the two coexist: the same underlying fault costs a
client credits or not depending on which way it happens to present.

---

## 6. What a client cannot do today

This is the part that costs integrators the most time:

1. **`status: completed` with zero `features` is indistinguishable from a legitimate empty result.**
   An out-of-range area, an unavailable window, a permissions problem and a service incident all
   look identical: `200`, `completed`, `features: []`. A client cannot tell "you asked for something
   impossible" from "we are broken", and historically was charged either way.
2. **There is no terminal state for a stalled job.** `Processing` forever is indistinguishable from
   `Processing` slowly. We chose 425 s as a give-up threshold with no documented basis, because none
   exists. A documented maximum job duration, or a `timed_out` status, would make this deterministic
   instead of a guess.
3. **There is no way to ask whether the service is healthy.** We cannot distinguish "our request is
   bad" from "the platform is degraded" without spending credits to find out.

---

## 7. What would help, in priority order

1. **A terminal state for jobs that will not finish** — `failed` or `timed_out` rather than
   `Processing` indefinitely. This is the single highest-value change: it turns an unbounded wait
   into an error a client can handle.
2. **Do not bill a result that carries no data.** Already true for `failed` and for stalls; please
   extend it to `completed` with an empty `features` array.
3. **Distinguish "empty because your request asks for nothing" from "empty because we could not
   produce it"** — different `status`, or a `reason` field. Two words in the payload would remove an
   entire class of client-side guesswork.
4. **A free health or status endpoint**, so a client can tell a platform incident from its own bug
   without spending credits.
5. **Document the maximum job duration**, so a client's polling timeout has a basis.

---

## 8. Context on why we care about this particular endpoint

We are building a data-centre free-cooling agent: it decides, hour by hour, whether outside air is
cool enough to switch the mechanical chillers off, using your forecast as the input a rooftop
thermometer cannot provide. `/v1/heatmap` is the **only** endpoint our decision depends on, and the
resolution genuinely matters to us — we measured 60 m granularity as real signal, not interpolation
(mean |ΔT| between tile pairs decays smoothly with separation), and a single call returns 17,862
tiles over 64 km² in about 67 s when it works.

We also had a **daily unattended collector** running against this endpoint to build a calibration
record — one forecast per day plus its elapsed outcome the next day. It has now returned no usable
data on **08-18, 08-19 and 08-20**, which is why we noticed the pattern rather than a single failure.

**Full field notes, including the items we withdrew after retesting, are in
`fortyguard-api-findings.md`** in our submission — 10 sections with reproduction payloads.

---

## 9. Reproduction, if useful

```bash
python testing/diag63_forecast_failed_status.py
```

Two legs, one forecast and one past-window control, full status payload for every distinct state
transition saved to `testing/results/diag63_forecast_failed_status.json`. It classifies the outcome
as one of `ok` / `completed_but_empty` / `terminal_<status>` / `stalled_in_processing` — the four
behaviours we have actually observed.
