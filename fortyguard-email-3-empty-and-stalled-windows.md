# Email 3 to FortyGuard — windows returning empty or stalling, past and future

**Status: READY TO SEND, 2026-08-21.**
Horizon question and AOI-local-time explanation deliberately excluded. No tables — prose only.

---

## THE EMAIL

**Subject:** `/v1/heatmap` returning `completed` with 0 cells on past and future windows — urgent, request IDs below

> Hi Fawad, hi team,
>
> We have a fault on `/v1/heatmap` that has been affecting us since 18 August and is now blocking us
> completely. Every request below uses the same shape — an 8×8 km polygon, `granularity: 60`,
> `analytic_type: "tcm"`, `filter_type: 2` over a 2-hour window — on two AOIs: Loudoun County,
> Virginia (39.024017, −77.419691) and Elk Grove Village, Illinois (42.000191, −87.956603). All
> times are UTC.
>
> Today we submitted two calls ten minutes apart that were identical in every field except the target
> window. At **16:13:54** we requested 13:00–15:00 the same day — a window that had already closed
> three hours earlier — and activity `14742335-957b-429a-8c12-ee898fb8f889` came back
> `status: completed` with `"features": []` and `n_cells: 0` after 59 status polls over 607 seconds.
> At **16:24:03** we requested 18:00–20:00, about 1.6 hours ahead, and activity
> `f314239b-a5c3-416c-bd74-dfa51377c914` did exactly the same after 60 polls over 606 seconds. Both
> were billed 4,220. The first one is the one we would ask you to look at first, because a window
> that has already elapsed should not depend on forecast availability.
>
> This is not new as of today, and it is not confined to forecast windows. On **20 August at
> 11:11:56** we submitted two calls in the same second on the same AOI: `f010f6e2-a311-48f7-990d-c6c554bb9686`
> for 18:00–20:00 that day, and `58ef42ba-10a9-46a8-8032-253b4b84cfa0` for 18:00–20:00 on 19 August,
> which had closed the previous day. Both sat in `processing` for 45 polls over 425 seconds and
> neither ever completed. Because they went out in the same second, nothing about timing or plan can
> differ between them — the past window failed the same way the future one did.
>
> Earlier on **20 August at about 12:52** a batch of twelve hourly windows on the Virginia AOI
> returned real data for the first three (`481e3512-3ee9-41f5-9d7b-45be68b6e5be`,
> `82746eda-d112-4669-b772-b1b153cf9d00`, `b9ca5e79-7737-4382-9724-e4de698934d6`, 17,785 cells each)
> and `completed` with 0 cells for the remaining eight. Then on **21 August at about 15:23** a batch
> of twelve hourly windows on the Illinois AOI returned 0 cells for all twelve, 10 polls over 339
> seconds each, at a cost of 50,640 credits for nothing. For contrast, on **19 August at 13:35**
> activity `f333f605-6ef6-4847-9bbf-1d22910ebcb6` returned a full 17,862-cell field for a window
> 9.4 hours ahead, so this did work recently.
>
> **Why this is urgent for us.** Our hackathon project is built directly on your forecast and heatmap
> endpoints — the forecast is the input the whole thing depends on, and without it we cannot produce
> a live result or finish the accuracy measurements the submission rests on. We have disabled all our
> scheduled jobs so we are not adding load or spend while this is open, which also means we are not
> collecting anything.
>
> Three things would help, in order: whether there is a known incident on these two AOIs; whether the
> activity IDs above tell you what those jobs actually did, since from our side a job that reports
> `completed` with an empty grid is indistinguishable from a successful one until the payload arrives;
> and one billing point — `completed` with `n_cells: 0` is currently charged in full, which across
> this plan is now roughly 227,000 credits of empty-but-billed responses including 8,440 today. You
> already made `failed` and stalled jobs unbilled, which we noticed and appreciated, and treating the
> empty-completed case the same way would stop clients like us retrying blind.
>
> I can send the remaining 40-odd activity IDs, the raw JSON of any response above, or a `curl` that
> reproduces either of today's two calls.
>
> Thanks,
> *[your name]*

---

## If they ask for the rest — the remaining activity IDs

All `completed` with 0 cells.

**08-20 ~12:52 UTC, Virginia, windows 16:00–23:00:** `530a4ea1-f635-42db-8473-d72fdd7d9440`,
`45f4a3bf-46a0-437c-9d10-e15fe50239d2`, `4a5d0f4b-9d94-4804-a49c-ad299db23af4`,
`59aef4c7-79ab-42d7-bca9-db91609fb72b`, `37d31333-e262-4583-8b41-e07cae67ab0d`,
`e121929b-0817-4f44-a24a-345bf46a79a7`, `5c9d3274-3468-431e-ba19-818e4f11525b`,
`13e9d7d2-7bbb-4d5e-82a3-1736aedaf245`

**08-20 ~13:40 and ~14:54 UTC, Virginia:** `f8b84db4-10e4-4700-82fd-c07584d255f7`,
`0c66bdc5-9d14-48cd-bd9e-f27b82c40e66`, `84daa10d-0f2c-4cdd-ba77-dc07614e9650`,
`f9226317-5c5e-4d47-8089-5880e8f61b36`

**08-20 ~15:03 UTC, Illinois** (first window `fb57bebc-3bc9-43a5-95e4-a66fff191b9e` returned 17,797
cells; the rest empty): `22e8179b-4464-48c1-bd9d-996a4add3024`, `dedd15df-d976-45ed-9bb4-13f6a83961cd`,
`714d04e7-63dc-4221-bebe-96bbf0f157e7`, `d8b9aaf2-ed9e-4ffa-a46b-ebc486835a6a`,
`6aa19062-cdfe-4488-96b4-bebe2af787a0`, `86f8e559-5699-4d11-a9e5-4609be5a0a3d`,
`ae44d8b6-c8c8-47d1-acad-9fc477e7847c`, `2299d240-a3ac-4f25-9de7-efa25e9d5314`,
`729cc7a8-ac67-49e7-869c-103d9f80fbac`, `9bd451b9-3a5a-4bf7-a610-7296285070fb`,
`c6e8b7ec-e047-408a-8c2c-e60c4b880dfa`

**08-20 ~15:33 and ~16:05 UTC, Virginia:** `6c09799f-57c7-47ff-9c68-fcd3a0c691d5`,
`ed474def-2e51-469a-8a2a-eb882fedfe50`, `da759479-84b5-4681-aca6-7336d3545997`,
`ab0b0df9-0d00-42e3-bed7-7946af49aab8`, `33c49882-89a0-4010-b83f-788cec8388e3`,
`b6feb9c3-7d57-4d8b-97f0-1b83bf2f51df`, `aa6d08c3-2e77-40c1-9e34-46fbe8155ac5`,
`10251e21-4705-494e-b7e8-8eeedb98de3e`, `4c92cd7a-5ecd-4b22-8a9c-5af7fc4287cd`,
`ce2c1a65-ffa1-4be5-ae5e-8215842817cd`, `84ee68ae-2835-41b0-935f-b5a009b558ce`,
`71091754-837e-4c72-a35e-ddcff82b15f8`, `181ed6ae-6ec0-43a8-a999-c0b1cf70b329`,
`a9c7e228-a8d5-458b-9912-775354fd0b9d`

**08-20 ~16:33 UTC, Virginia, 20 polls / 312 s each:** `860b75b3-5bc1-4a5d-ad5a-eb6df4264622`,
`fce295b4-7d95-40a9-88be-c85432ce7d39`, `05de2f20-48be-4b3d-b484-78199b331516`,
`e9a581ab-2b71-4e99-8855-bc511641e6dc`

**08-21 ~15:23 UTC, Illinois, 10 polls / 339 s each:** `b0f0d1e3-34f4-4fac-ada1-af798a587b8c`,
`752e676c-0871-403a-90ce-3bef48a2d95a`, `689cebc5-ecce-4f47-9423-dece4c926959`,
`fa936d38-e92e-4c7d-a1ee-f12b35b2c677`, `2ad4a387-0e93-4397-9b0f-d9a9a47a7b30`,
`37222d41-c7e7-4f7a-b93d-958569716ab2`, `7ff4c7c9-f463-4290-93aa-65fd976febfb`,
`589e392a-f148-418d-bee9-09a9eab9accc`, `58a2f259-535b-46dc-b36f-8e9d757f973e`,
`d8e88ad5-668d-4afa-a6dd-d7ea46542eed`, `78ddc384-b73e-4ef9-99da-8b7aadf1c7ea`,
`255841c5-15d9-4da9-af6a-4346933393b2`

⚠ One submit in the 08-20 16:05 batch was **rejected outright** with no activity ID while the other
eleven were accepted. Twelve near-identical submits with one rejection reads as rate limiting; we now
stagger submits by 0.4 s and retry a rejection once. Not worth raising unless they ask.

---

## Notes for us, not for them

**Every ID and timestamp is read from a saved artefact, not from memory:**
`testing/results/diag64_catalog_horizon.json` (today's two calls, with meter readings),
`testing/results/live_spend.json` (every live run, one record per call),
`testing/results/diag63_forecast_failed_status.json` (the 08-20 stalled pair),
`testing/results/diag62_forecast_recheck.json` (the 08-19 success). All 55 IDs were checked back
against those files before this was written. Today's submit times are derived as *response-saved time
minus measured elapsed*, which is why they carry seconds while the older ones carry "about".

⚠ **A correction to our own record, found while writing this.** HANDOFF §4.0 said *"past-window
requests worked throughout, at every hour."* **False after 2026-08-20 11:11 UTC** —
`58ef42ba-10a9-46a8-8032-253b4b84cfa0` asked for a window that had closed the previous day and
stalled for 425 s. It was in our artefact the whole time and the summary described it as a pass. That
clause is retracted in HANDOFF §4.0, and the 08-20 pair is now the strongest evidence in the email
because both legs were submitted in the same second.

**Deliberately excluded, per the user's instruction:** the catalog-horizon question (12-hour forecast
offering confirmed) and any explanation of our AOI-local time handling (we already do it correctly,
and raising it invites a reply about a non-issue).
