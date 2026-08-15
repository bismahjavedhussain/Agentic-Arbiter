# DAMPER Test 3 — Does FortyGuard's OWN forecast have real skill for this decision?

**Status: 🔄 Designed and pre-registered. NOT YET RUN. Needs your go-ahead — it spends a small
number of live API calls on the sensitive key.**

## What this test would settle, and why it's the one gap left

Test 2 proved the *mechanism* (trajectory-awareness beats a tuned deadband) works, using real NOAA
historical weather as the trajectory source. It did **not** test whether FortyGuard's own 12-hour
`env_params` forecast — the actual data source DAMPER would use in production — is itself good
enough to supply that trajectory. This is a much lower, easier-to-clear bar than the "does the
forecast sharpen over time" question that sank three earlier ideas in this project (N-25, N-40,
N-42): here, the forecast only needs to have **some** real skill, better than pure guessing, not a
specific improving-with-lead-time shape.

## Why this is a low-risk, cheap, and fast test — unlike the ones that failed before

- **No calendar wait required for the core check.** Skill can be assessed with historical
  forecast-vs-outcome PAIRS already collectable in one or two calls, reusing the exact
  `submit_poll`/`site_window` machinery already built and hardened in `testing/common.py` (including
  the hard-won timezone-safety fix documented there).
- **A much weaker claim needed.** "Has some skill" is a far lower bar than "sharpens over time,"
  and persistence-based skill (yesterday's reading predicts today reasonably well) is already a
  well-established property of humidity and wet-bulb temperature in general meteorology — this test
  only needs to confirm FortyGuard's *specific* product clears that ordinary bar, not prove
  something exotic.

## Design, pre-registered now, before any call is made

1. **Target quantity:** `wet_bulb_temperature_celsius` and `relative_humidity_percent`, at the same
   site centre used throughout this project (39.0100, -77.4460).
2. **Method:** request an `env_params` forecast ~9–10 hours ahead for a specific future hour (inside
   the confirmed 12-hour horizon), then request the same hour again after it has passed (the
   historical/outcome value). Compute the forecast error. Repeat for a small number of days.
3. **Comparison — the actual test:** compare FortyGuard's forecast error against **pure
   persistence** (assuming the value simply stays the same as it was ~10 hours earlier, computed
   for free from the NOAA archive already on disk as an approximation, or from FortyGuard's own
   historical data on a second, cheap call).
4. **Pre-registered pass condition, fixed now:** FortyGuard's forecast error (mean absolute error)
   must be smaller than the persistence baseline's error, on the available sample, for **at least
   one of** wet-bulb temperature or relative humidity. This is a deliberately low, honest bar — the
   point is confirming basic usable skill exists, not measuring its precise size (that would need
   far more days, exactly like the sharpening tests that failed for lack of calendar time).
5. **What a FAIL would mean, decided now rather than after seeing the result:** if FortyGuard's
   forecast cannot even beat simple persistence, DAMPER should fall back to using persistence
   itself (extrapolating recent real readings, exactly as Test 2's "lookahead" policy already does)
   rather than FortyGuard's forecast for the trajectory signal — the switching-cost-aware mechanism
   proven in Test 2 does not actually require FortyGuard's forecast specifically to work, only
   *some* forward-looking signal, so a fail here narrows the data source, not the core idea.

## Cost, stated honestly before asking

At the documented rate of 4,220 credits per call (`fortyguard-api-findings.md` §5), this needs
roughly **2–4 calls total** (one or two forecast requests, one or two outcome requests) —
approximately **8,440–16,880 credits**, a small fraction of the 180,980 currently on the key. This
has **not been run**. Say the word and it can be scheduled the same way N-26's daily collection was
— or run as a single one-off check if you'd rather not wait on the calendar at all.

## Why this is listed as the single most important remaining step before Aug 17

Everything else in this idea (Tests 1 and 2, the physics explanation, the claims file) is either
already confirmed or deliberately independent of FortyGuard's forecast specifically. This is the
one place where "does FortyGuard's actual product work for this" has not yet been checked at all.
It is cheap, fast, and low-risk relative to the three earlier tests that consumed real calendar time
for a much harder question — but it is still open, and this file exists so that fact is not lost.
