# Casual group-chat message — participants' group (CEO present)

**No activity IDs, by design.** Short enough to read on a phone; specific enough that the past-window
detail is hard to dismiss. Detailed report with all 62 IDs stays in
`fortyguard-email-3-empty-and-stalled-windows.md` for whoever asks.

---

> Hey all — is anyone else getting `/v1/heatmap` coming back `completed` with an empty grid?
>
> We've had it since about the 18th and it's total today. Jobs submit fine — 200, activity id issued
> — then sit in polling for ~10 minutes and complete with `"features": []` and `n_cells: 0`.
>
> The part that's confusing us: it isn't only forecast windows. This afternoon we asked for a 2-hour
> window that had already **finished three hours earlier** and it still came back completed with
> nothing in it. A batch of 12 hourly windows earlier today returned 0 cells for all 12. Empty
> responses are still billed, so it adds up fast.
>
> Our project is built on the forecast + heatmap — that's the input the whole thing runs on — so we're
> pretty stuck until it clears. Is this a known incident, or is it just us? Happy to send request IDs
> to anyone on the team who wants them 🙏

---

## Why it is worded this way

- **"Is anyone else getting…"** opens it as a question to the room rather than a complaint at the
  vendor. If two or three people say yes, it stops being one team's problem and becomes a platform
  issue — which is what actually gets it escalated.
- **The already-finished window is the load-bearing detail** and it is deliberately in its own
  paragraph. It cannot be waved away as a timezone mistake or a forecast-horizon limit, which are the
  two answers already given publicly in the channel to other people.
- **Billing gets one clause, not a paragraph.** Enough for a CEO to register the cost; not enough to
  read as a refund request instead of a bug report.
- **No activity IDs**, per instruction — and the offer to send them privately is what turns attention
  into a thread.
