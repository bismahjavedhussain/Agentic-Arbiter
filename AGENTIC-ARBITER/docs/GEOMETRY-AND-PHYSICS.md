# What the agent actually models — every part, and how sure we are of it

**Every element is tagged.** 📏 **MEASURED** (from data we hold) · 📘 **PUBLISHED** (a citable source) ·
✏️ **ASSUMED** (our choice, defensible, stated) · ❓ **UNKNOWN** (we do not know and cannot currently
find out).

The site is a real pair of adjacent hyperscale halls in Ashburn, Virginia — OpenStreetMap ways
`852039781` (source) and `793087859` (receptor).

---

## 1. Plan view — looking straight down

```
                                    N
                                    ^
                                    |
        wind FROM 203.7 deg  \
        (the critical bearing) \
                                \
                                 \
                                  v   air moves toward 23.7 deg
                                   \
                                    \
                      +-------------------------+
                      |                         |   RECEPTOR  (OSM 793087859)
                      |      HALL  B            |   169 x 125 m   📏
                      |                         |   9,804 m2      📏
                      |    [ I ] <-- INTAKE     |
                      +-------------------------+   [ I ] position  ✏️ ASSUMED
                                 ^                  (on the face pointing at the source:
                                 |                   the conservative worst case)
                                 |
                       141 m separation  📏
                                 |
                                 |     ~~~ PLUME ~~~  warm exhaust drifting downwind
                                 |    ~~~~~~~~~~~~~~
                      +-------------------------+
                      |    [ C ] <-- CONDENSER  |   SOURCE  (OSM 852039781)
                      |          BANK           |   163 x 189 m   📏
                      |      HALL  A            |   11,796 m2     📏
                      |                         |   [ C ] position  ✏️ ASSUMED
                      +-------------------------+   (not mapped anywhere in OSM)

    receptor lies at bearing  23.7 deg  from the source          📏
    so the plume reaches it when wind comes FROM 203.7 deg       📏 (derived)
    that happens on  20.3 %  of observed hours                  📏 (449 real KIAD obs)
```

**The meteorological convention, because it is easy to invert:** *"wind from 203.7°"* means air moving
**from** the south-south-west **toward** 23.7°. Get this backwards and the plume lands on the wrong side
of the campus.

---

## 2. Section view — and ⚠ THE HEIGHT PROBLEM

**This is the diagram that matters, and it exposes an unresolved gap.**

```
   height
   above
   grade
     |
 20m-+                                    ❓ Is the cooling equipment UP HERE?
     |        ~~~~~~~~~~~~~~~~~~~~~~~~~      Rooftop chillers / condensers are common.
     |      ~~~   PLUME CENTRELINE   ~~~     If so, the intake breathes air at ROOF height,
     |    ~~~   rises, then bends down  ~~   NOT at 2 m.
 15m-+  ~~~      (DOWNWASH)            ~~
     | ~~                                ~
     |~            +---------------+      ~~~
 10m-+  +--------+ |               |         ~~~~
     |  |        | |   HALL  B     |  <-- [ I ] intake, IF roof-mounted   ❓
     |  | HALL A | |               |
  5m-+  |        | +---------------+
     |  | [ C ]  |        ❓ or IF the equipment sits in a ground-level
     |  |        |           yard, the intake is down HERE, ~2-4 m,
  2m-+--+--------+--------------------------  <=== FORTYGUARD MEASURES HERE  📏
     |     ^                                       "2 metres above the ground"
     |     |  [ C ] condenser bank, IF yard-mounted ✏️
  0m-+=====+==========================================  grade
        HALL A                    141 m                     HALL B
```

### ⚠ The 2 m mismatch — stated plainly because it is not solved

**FortyGuard measures air temperature at 2 m above ground.** That is confirmed from their own material:
*"2-meter, street-level ambient air temperature"*, *"measured 2 meters above the ground"*. 📏

**We do not know the height of the cooling equipment at this site.** OSM has no building heights for
these footprints and does not map mechanical equipment at all. ❓

**Why it matters — air temperature is not constant with height near the ground:**

| Condition | What happens between 2 m and ~15 m | Sign |
|---|---|---|
| **Purely adiabatic** | dry adiabatic lapse rate **9.8 °C/km = 0.0098 °C/m** → ~**0.13 °C** over 13 m | 📘 negligible |
| **Sunny afternoon, unstable** | the near-surface layer is *superadiabatic*; 2 m is **warmer** than roof height | ❓ order of a degree |
| **Clear night, stable inversion** | temperature *increases* with height; 2 m is **colder** than roof height | ❓ order of a degree |

**The adiabatic term (0.13 °C) is genuinely negligible. The stability-driven departures are not, and
we have not measured them.** They are plausibly of the same order as — or larger than — the entire
recirculation term this project computes (**0–0.855 °C**), and larger than the ~0.4 °C buffer difference
that drives the free-cooling result.

**⚠ Do not quote a number for this. We cannot measure it from what we hold:** KIAD's ASOS reports
temperature at one height only, so no vertical profile is available. Two instrumented heights, or a
tower, would settle it.

### Why the headline result survives this anyway — and it is a real argument, not a dodge

**The free-cooling claim is DIFFERENTIAL, and a height bias is common-mode.**

- The **incumbent** reads a weather station, which also measures at ~1.5–2 m (ASOS standard).
- The **agent** reads FortyGuard, also at 2 m.
- **Both** have their buffers calibrated against the same realised outcomes, so **both absorb the same
  height offset in calibration.** It largely cancels from *hours gained*.

**What it does NOT survive:** any claim about the **absolute** intake temperature. *"Your intake will be
27.3 °C"* is not defensible for roof-mounted equipment until the height offset is known. *"You can free
cool for ~150 more hours a year than your current rule allows"* is, because it is a comparison.

**And the deployment path closes it properly:** the customer's own intake sensor sits at the true height.
Once it feeds back, the residuals include the height offset and the conformal bound absorbs it
end-to-end — within a fortnight of data. **That is the same mechanism that already handles every other
unmodelled term, and it is why the self-scoring loop is the product rather than a nicety.**

**Second-order caveat, volunteered:** the offset varies with time of day and stability, and free-cooling
hours are concentrated at night and in shoulder seasons. So a single constant calibration will not absorb
it perfectly across the hours that matter. A time-of-day-stratified calibration is the honest fix.

---

## 3. Every part, with its status

| Part | What it is | Status |
|---|---|---|
| **Ambient air field** | FortyGuard, 2 m above grade, 60/80/100 m granularity | 📏 17.8–37.8 °C over 5 years |
| **Source hall** | OSM way `852039781`, 163 × 189 m | 📏 footprint · ❓ height |
| **Receptor hall** | OSM way `793087859`, 169 × 125 m | 📏 footprint · ❓ height |
| **Separation** | centre-to-centre | 📏 **141 m** — less than half the 300 m reference layout |
| **Condenser bank** | the heat source: hot air leaving the cooling equipment | ✏️ placed on the face toward the receptor; **not in OSM** · ❓ height |
| **Exhaust / discharge** | temperature rise of air leaving the bank | 📘 within the published 14–25 °F range |
| **Plume** | the warm stream carried downwind | 📏 solver, validated to **2.9 × 10⁻¹⁰** vs analytic and against **67** field experiments |
| **Downwash** | wind bending the rising plume back to intake level | 📏 calibrated to field data: exponent **1.25**, u_c **8.0 m/s** |
| **Intake** | where the receptor draws air in | ✏️ on the face toward the source · ❓ height |
| **Recirculation rise** | plume contribution at the intake | 📏 **0–0.855 °C** at the 300 m reference; **expected larger here at 141 m — not yet measured** |
| **Vertical dispersion (σ_z)** | the dilution our 2-D solver omits | 📘 ASHRAE Ch. 46 Eq. 22. **We over-predict**, by a factor growing with distance/calibration-distance |
| **Wind bearing + speed** | drives everything | 📏 449 obs (bearings) + 43,763 hourly records. **FortyGuard supplies no wind** |
| **The 2 m → intake height offset** | ⚠ **unmodelled** | ❓ **the largest open gap. See §2** |

---

## 4. The two known biases, and their directions

Being explicit about sign matters more than magnitude, because a bias of known sign is usable.

1. **Missing σ_z → we OVER-predict recirculation.** We omit a dilution term, so our numbers are too hot.
   That is the **safe** direction for a free-cooling decision: over-predicting the intake makes the agent
   *more* conservative about switching, not less. 📘
2. **The 2 m height offset → sign FLIPS diurnally.** Warm-biased in unstable afternoons, cold-biased in
   stable nights. **A cold bias at night is the dangerous direction**, because free cooling is most used
   at night — the agent could think the air is cooler than the roof actually is. ❓ **This is the risk to
   state out loud, and the intake-sensor feedback loop is the answer to it.**

---

## 5. What would close the gaps, in order of value

| Gap | What closes it | Cost |
|---|---|---|
| Intake/condenser **height** | one photograph, one site drawing, or a customer conversation | free, needs access |
| The **2 m → roof offset** | two instrumented heights for a fortnight, or the customer's own intake sensor | needs the customer |
| **σ_z** over-prediction | a 3-D solver, or ASHRAE Ch. 46 Eq. 22 applied as a correction factor | days of work; the chapter is on disk and unused |
| Condenser **position** | site imagery or drawings | free, needs access |
| Building **height** | OSM `height` tags where present, or lidar | partly free |

---

*Footprints © OpenStreetMap contributors (ODbL). Weather: NOAA ASOS via Iowa State Environmental
Mesonet. Physics validated against Project Prairie Grass (1956) and CEC-500-2013-065 (public domain).*
