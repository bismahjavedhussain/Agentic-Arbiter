# Email 4 to the FortyGuard hackathon team — short, no request IDs

**Status: READY TO SEND, 2026-08-21.** Deliberately short. No request IDs, no tables. The full
report with all 62 activity IDs is `fortyguard-email-3-empty-and-stalled-windows.md` if they ask.

---

**Subject:** `/v1/heatmap` returning `completed` with an empty grid — blocking our submission

> Hi team,
>
> We are hitting a problem with `/v1/heatmap` that has been building since 18 August and is total as
> of today, and it is now blocking our hackathon project.
>
> Requests submit normally — HTTP 200, "Heatmap Submitted Successfully", an activity ID issued. The
> job then stays in `processing` for around ten minutes and finishes with `status: completed` carrying
> `"features": []` and `n_cells: 0`. No error at any point, so from our side a failed job is
> indistinguishable from a successful one until the empty payload arrives.
>
> It is not limited to forecast windows, which is the part we cannot explain. This afternoon we
> requested a two-hour window that had already closed three hours earlier, and it came back completed
> and empty in exactly the same way. Earlier today a batch of twelve consecutive hourly windows
> returned zero cells for all twelve. We are seeing it on two different AOIs, one in Virginia and one
> in Illinois, with the same request shape that was returning full 17,000-cell fields last week.
>
> Our project is built directly on the forecast and heatmap endpoints — the forecast is the input the
> entire system depends on, and without it we cannot produce a live result or complete the accuracy
> measurements our submission rests on. We have paused our scheduled jobs so we are not adding load
> while this is open.
>
> Could you let us know whether there is a known incident affecting this? We have the activity IDs,
> timestamps and raw responses for every one of these calls and can send them over immediately if
> that helps someone trace it.
>
> Thanks,
> *[your name]*
