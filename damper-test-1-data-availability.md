# DAMPER Test 1 — Is the data DAMPER needs actually there?

**Status: ✅ Done. Cost: $0 — no new API call, checked against data already on disk.**

## What this test settles

Before designing any decision logic, the most basic question: does FortyGuard's API actually
return the fields DAMPER needs (wet-bulb temperature, relative humidity, air-quality indices), or
was that assumed from an earlier, less careful pass of research?

## Why this needed checking rather than assuming

An earlier stage of this project's research (a different, since-abandoned idea) had claimed
FortyGuard's `env_params` endpoint returns air-quality fields. When first asked about this for
DAMPER, an initial check searched only for `fortyguard-api-findings.md` mentioning these fields by
name — found nothing — and nearly reported "not found." **That check had a bug**: it searched a
document for a *discussion* of the fields, when the real test should be whether a *real API
response* contains them. The correct check is done here.

## Method

Loaded a real, already-paid-for, saved response from this project's own test fixtures —
`n37_ep_2026-07-22.json`, an `env_params` call made on 2026-08-13 for the date 2026-07-22 — and
printed every field actually present under `locations[0].parameters`.

## Result

**All of the following fields are present, with real, non-null numeric values, one per hour, 24
hours in the response:**

```
heat_index_celsius           [25.4, 25.4, 25.4, ...]
apparent_temperature_celsius [25.1, 23.4, 23.7, ...]
relative_humidity_percent    [96.9, 97.2, 96.3, ...]
precipitation_mm             [0.5, 0.1, 0.4, ...]
cloud_cover_octas            [31.0, 70.0, 62.0, ...]
wet_bulb_temperature_celsius [21.9, 20.9, 20.7, ...]
air_quality:idx               [34.0, 32.9, 31.8, ...]
air_quality_pm2p5:idx         [34.0, 32.9, 31.8, ...]
air_quality_pm10:idx          [5.7, 5.5, 5.4, ...]
air_quality_no2:idx           [2.0, 1.7, 1.6, ...]
aqi_us_co                     [1.3, 1.3, 1.3, ...]
air_quality_o3:idx            [30.9, 29.3, 27.8, ...]
air_quality_so2:idx           [0.2, 0.2, 0.2, ...]
methane_ppb                   [2011.7, 2011.7, 2007.3, ...]
co2_ppm                       [450.0, 452.0, 453.0, ...]
```

The values are physically plausible for a humid Virginia summer day (96–97% RH, 21°C wet-bulb) —
not placeholder/default-looking numbers.

## What this does and does not establish

**DOES establish:** the raw data fields DAMPER's decision logic needs are real, already being
returned, and were already paid for as part of routine testing on a completely different question.

**DOES NOT establish:** whether the *forecast* (as opposed to this historical example) version of
these fields has genuine predictive skill 12 hours ahead. That is a separate, not-yet-run test —
see `damper-test-3-forecast-skill-PLANNED.md`.

## Honest note on the correction

This test file exists partly to document a mistake caught and fixed in the same session: the first
attempt to answer "does this data exist" used the wrong check (searching a findings document
instead of a real response) and would have reported a false negative. Recorded here in the open,
matching this project's own standing rule that a correction made visibly is more credible than a
mistake never mentioned.
