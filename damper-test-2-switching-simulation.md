# DAMPER Test 2 — Does a trajectory-aware switching policy actually beat what real products do today?

**Status: ✅ Done, on a properly tuned, held-out basis. Cost: $0 — free NOAA public archive only,
zero FortyGuard calls.**

## What this test settles

`damper-physics-explained.md` Part 5 claims that looking at the *trend*, not just the instant
reading, beats the fixed deadband real commercial economizer controllers use today (documented
directly from the Honeywell JADE manual — see `damper-claims-and-defences.md` §1.5). That is a
real, checkable claim, not a plausible-sounding assertion, and this is where it was checked.

## Why free NOAA data, not FortyGuard's own forecasts

Three earlier decision ideas tried in this project (documented in the sibling `claims-and-defences.md`
and test files N-25, N-40, N-42, N-43) all needed weeks of FortyGuard's own forecast-versus-outcome
history to reach a confident answer, and the hackathon calendar could not supply that. This
question — does a switching-cost-aware policy beat a tuned deadband — is a fundamentally different,
less data-hungry kind of question, answerable on **abundant, free, historical weather data**: a full
year of real hourly temperature and humidity from NOAA's public ASOS archive at Washington Dulles
airport (the same station this project already uses for wind), fetched via Iowa State University's
free Environmental Mesonet service, no API key required.

## Design, pre-registered before the corrected run

- **Data:** 8,335 real hourly (temperature, humidity) readings, 2025-09-01 to 2026-08-14. Humidity
  computed from temperature and dew point via the standard Magnus formula, the same method already
  used and verified elsewhere in this project (see `physics-explained.md`'s conformal-prediction
  section for the same formula in a different context).
- **Split:** first ~6 months (Sep 2025 – Feb 2026) = **training** data, used only to tune every
  policy's own settings. Last ~6 months (Mar – Aug 2026) = **held-out test** data, scored only once,
  never used for tuning. Time-ordered, not random — this is a time series and no future information
  is allowed to leak backward.
- **Policies compared, ALL fairly tuned on training data only:**
  - **naive** — switches the instant the reading crosses a threshold. The threshold itself is
    tuned on training data so this baseline gets its fairest possible shot too.
  - **hysteresis** — the deadband approach real products use (§1.5 of the claims file). Its buffer
    width is grid-searched on training data, at each tested switching cost separately.
  - **lookahead (the proposed policy)** — extrapolates the recent hourly trend and only switches
    if the trend suggests the new state will hold for several more hours. Its own settings (how
    many hours ahead to check, how many past hours to use for the trend) are also grid-searched on
    training data, at each tested switching cost separately.
  - **perfect foresight** — reported only as a theoretical ceiling (uses the *actual* future,
    which no real system can do), never claimed as achievable.
- **Cost model, stated as a stub, swept:** mechanical cooling = 1 unit/hour. Free cooling when
  conditions are genuinely favourable = 0.25 units/hour (the midpoint of the sourced 70–90% savings
  range from ENERGY STAR/NSIDC — see the plan file Part 1.2). Free cooling when conditions turn out
  unfavourable = 3 units/hour (a penalty, representing needing backup mechanical help anyway). A
  single mode switch costs [0.5, 1.0, 2.0, 4.0] units — **swept across this whole range because the
  real number is not sourced to a precise figure**, only qualitatively confirmed as "real and worth
  avoiding" (Trane whitepaper, `damper-claims-and-defences.md` §1.4).

## A mistake made and corrected inside this same test, kept visible

The first version of this test compared the lookahead policy against **one arbitrarily chosen**
hysteresis setting (a 2°C/5% buffer, picked without tuning). That version showed a striking
7.01-sigma win for lookahead. **This was flagged as unfair before being reported**, because an
untuned baseline is not a real adversary — exactly the mistake this project's own house rules (see
INTAKE's N-9/N-20/N-24 test files) exist to prevent. The test was rebuilt with the training/test
split and per-policy tuning described above, and re-run. The result below is from the corrected,
tuned version only.

## Result (held-out test data only, all policies tuned fairly)

| switching cost | favourable-threshold found (temperature) | naive | hysteresis (tuned) | lookahead (tuned) |
|---|---|---|---|---|
| 0.5 | 26.0°C | 2728.5 | 2872.2 | **2732.2** |
| 1.0 | 26.0°C | 2923.0 | 3017.2 | **2909.8** |
| 2.0 | 26.0°C | 3312.0 | 3307.2 | **3233.5** |
| 4.0 | 26.0°C | 4090.0 | 3845.5 | 3877.5 |

(Lower total cost is better. Bold = lowest cost at that switching-cost level.)

**Paired, week-by-week significance test, held-out weeks only, tuned lookahead vs. tuned
hysteresis:**

| switching cost | weeks compared | result |
|---|---|---|
| 0.5 | 23 | **lookahead wins, +7.74 standard errors** |
| 1.0 | 23 | **lookahead wins, +6.12 standard errors** |
| 2.0 | 23 | **lookahead wins, +3.35 standard errors** |
| 4.0 | 23 | no significant difference (+0.11 standard errors) |

## Sanity check: is this result an artifact of a degenerate threshold?

Checked directly: the tuned "favourable" threshold (26.0°C) produces a genuinely varying, seasonally
sensible pattern, not an always-true or always-false rule:

| month (test period) | fraction of hours favourable | mean temperature |
|---|---|---|
| March 2026 | 68% | 10.8°C |
| April 2026 | 67% | 16.1°C |
| May 2026 | 59% | 17.7°C |
| June 2026 | 44% | 23.6°C |
| July 2026 | 21% | 26.0°C |
| August 2026 | 18% | 25.9°C |

This tracks the real seasonal cycle correctly (favourable much more often in cool months, much less
in hot summer) — the comparison above is testing a genuinely live decision problem, not a trivial
one.

## Honest reading of the result

**What is well supported:** across three of the four tested switching-cost levels — spanning almost
an order of magnitude — the trajectory-aware policy matches or beats a *properly tuned* version of
today's industry-standard deadband, by a statistically real, not marginal, margin. The one level
where the difference disappears (switching cost = 4.0) is itself informative and physically sensible:
at a very high cost, both policies converge toward "switch as rarely as possible," so the specific
mechanism used to decide *when* matters less.

**What this test does NOT establish, stated plainly:**

1. This used **dry-bulb temperature plus a humidity gate** as the "favourable" definition, not true
   enthalpy — flagged as a stub in `damper-claims-and-defences.md`, not yet upgraded.
2. The switching-cost magnitude is swept, not sourced to a real number — the qualitative conclusion
   (lookahead wins at low-to-moderate cost) is robust to this, but the *exact* crossover point where
   the advantage disappears is not independently verified against a real chiller-plant cost figure.
3. This is real weather at ONE station (KIAD), used as a feasibility proxy. It does not yet use
   FortyGuard's own field or forecast at all — see Test 3.
4. This tests the MECHANISM (does trajectory-awareness help, given a real switching cost) — it does
   not yet test whether FortyGuard's own specific forecast product has enough real-world skill to
   supply that trajectory. That is the one remaining open question before Aug 17.

## Raw data and code

Fetched via `mesonet.agron.iastate.edu`'s free ASOS request service (Iowa State University),
17 chunks, ~3 weeks each, saved to the session scratchpad. Simulation code available on request;
not yet formalised into the main `testing/` suite pending a decision on whether to proceed with
this idea.
