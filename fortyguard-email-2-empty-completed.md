# Email draft 2 to FortyGuard — 2026-08-20, evening

**Short on purpose.** Full detail in
[`fortyguard-report-2026-08-20-jobs-not-completing.md`](fortyguard-report-2026-08-20-jobs-not-completing.md).
This one leads with billed empty results, because that is the part with a number attached.

---

**Subject:** 11 of 12 heatmap jobs returned `completed` with an empty field — all billed (activity IDs inside)

Hi,

Following up on my earlier note about jobs not completing — the behaviour has changed and this
version costs money, so I wanted to flag it quickly.

**Today at 16:05 UTC I submitted 12 `/v1/heatmap` jobs, one per hour of a 12-hour forecast horizon.
Eleven returned `status: completed` with an empty `map_data.features` array. All eleven were
billed 4,220 — 46,420 credits for no data.**

The eleven:

```
ab0b0df9-0d00-42e3-bed7-7946af49aab8
33c49882-89a0-4010-b83f-788cec8388e3
b6feb9c3-7d57-4d8b-97f0-1b83bf2f51df
aa6d08c3-2e77-40c1-9e34-46fbe8155ac5
10251e21-4705-494e-b7e8-8eeedb98de3e
4c92cd7a-5ecd-4b22-8a9c-5af7fc4287cd
ce2c1a65-ffa1-4be5-ae5e-8215842817cd
84ee68ae-2835-41b0-935f-b5a009b558ce
71091754-837e-4c72-a35e-ddcff82b15f8
181ed6ae-6ec0-43a8-a999-c0b1cf70b329
a9c7e228-a8d5-458b-9912-775354fd0b9d
```

A second batch at 16:33 UTC, submitted more slowly, behaved identically —
`860b75b3-5bc1-4a5d-ad5a-eb6df4264622`, `fce295b4-7d95-40a9-88be-c85432ce7d39`,
`05de2f20-48be-4b3d-b484-78199b331516`, `e9a581ab-2b71-4e99-8855-bc511641e6dc`. Four more empty,
four more billed.

**Across the last six hours: 4 of 46 windows returned a field. 177,240 credits spent on windows
that carried no data.**

Two asks, in order:

1. **Please don't bill a `completed` job whose `features` array is empty.** You already don't bill
   `failed` jobs or jobs that never finish — I checked the meter, and I'm grateful for that. This is
   the same fault presenting a third way, and it's the only one that charges.
2. **A different status, or a `reason` field, when a job completes with no data.** Right now an
   out-of-range area, an unavailable window and a service problem are indistinguishable: all three
   are `200` + `completed` + `features: []`. Two words in the payload would remove a whole class of
   client-side guesswork.

**One smaller thing:** in the 16:05 batch, the twelfth submit was rejected outright while the other
eleven were accepted. The twelve requests differed only in `start_time`, so I assume a rate limit on
concurrent submits — I've added a small delay between them and haven't seen it again. **If there is
a documented submit rate, I'd rather code to it than guess.**

Request shape for all of the above: 8 × 8 km AOI centred on 39.0100, −77.4460, `granularity: 60`,
`analytic_type: "tcm"`, `filter_type: 2`, 1-hour windows.

Thanks,
[name]
