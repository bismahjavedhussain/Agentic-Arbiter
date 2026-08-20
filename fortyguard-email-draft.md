# Email draft to FortyGuard — 2026-08-20

**Deliberately short.** The full detail is in
[`fortyguard-report-2026-08-20-jobs-not-completing.md`](fortyguard-report-2026-08-20-jobs-not-completing.md)
and in `fortyguard-api-findings.md`; this is the version that gets read.

---

**Subject:** `/v1/heatmap` accepting jobs but never completing them — activity IDs inside

Hi,

I'm building on the Hackathon'26 plan and hit something on your side that I think you'll want to see.

**`POST /v1/heatmap` returns 200 with an `activity_id`, but the job never finishes.**
`GET /v1/status/{id}` answers 200 with `status: "Processing"` on every poll and never changes — I
polled 45 times over 425 seconds. No data ever arrives.

Two activity IDs from 2026-08-20, ~11:04–11:11 UTC:

- `f010f6e2-a311-48f7-990d-c6c554bb9686` — forecast window
- `58ef42ba-10a9-46a8-8032-253b4b84cfa0` — **past** window, same AOI and settings

I sent that second one as a control. It stalls identically, so this isn't about forecast windows —
and it rules out my key, my plan, my quota, the AOI and the granularity, since the same request
shape returned 17,862 tiles the day before. Your usage endpoint answered normally throughout, so
the platform is up; it looks specific to the heatmap job pipeline.

It presented three different ways in about three hours: `completed` with an empty `features` array
(billed 4,220 each), then `status: failed`, then the indefinite `Processing` above. **The `failed`
and stalled jobs weren't billed — that's the right behaviour and I appreciate it.** The
`completed`-with-no-data ones were.

The one change that would help most: **give a job that won't finish a terminal state** — `failed`
or `timed_out` rather than `Processing` forever. Right now a client can't distinguish "stuck" from
"slow", so any timeout I pick is arbitrary.

Request was an 8 × 8 km AOI centred on 39.0100, −77.4460, `granularity: 60`,
`analytic_type: "tcm"`, `filter_type: 2`, 2-hour window. Happy to send the full status payloads or
a longer write-up if useful — I've been keeping field notes on the API throughout the build.

Thanks,
[name]
