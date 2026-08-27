# IMAGERY REVIEW -- what to look for, and what to send back

You are answering ONE question per site, and it is narrower than "is this a data centre":

> **Is the cooling plant at GROUND level, in a yard beside the building?**

That is the only question, because FortyGuard measures air temperature **2 m above the ground**. If
the cooling equipment sits on the roof, the 2 m field does not describe the air that equipment
breathes, and this agent has nothing true to say about the site. That is not a defect in their data
or in ours -- it is a statement about where the model applies. It is the same gate that refused
Santa Clara, and "five screened, two refused" is the most credible claim in the project.

## How to tell the three things apart

**GROUND-LEVEL CONDENSERS (in scope).** Rows of identical box-shaped units standing on the concrete
*outside* the building, in a fenced yard along a long wall. They cast shadows onto the ground beside
them, and the rows are usually 2-4 units deep. This is what Ashburn, Chicago and Dulles look like.

**ROOFTOP UNITS (out of scope).** The same kind of units, but sitting *on the roof outline* -- inside
the building's own footprint, with no ground beside them. Often in dense regular rows covering much
of the roof. Shadows fall on the roof, not on the ground.

**GENERATORS (neither -- ignore them).** Long rectangular containers in a row, usually along one end
or one side, each with a small vertical exhaust stack. They are back-up power, not cooling. Easy to
mistake for condensers; the giveaway is the stack and that they sit in a single line.

**LOADING DOCKS (not a data centre).** Trailers backed up perpendicular to the wall, with a wide
paved truck apron in front. If you see trailers, it is a warehouse.

**NOT BUILT.** Bare earth, gravel pads, a grid of small white concrete squares (foundation footings),
or a roofed shell with nothing installed around it.

## Read BOTH frames

Each site has two images at the identical map area:

* `*_ESRI.jpg`  -- ESRI World Imagery
* `*_USGS.jpg`  -- USGS The National Map

**Neither carries a date**, which is exactly why there are two: they have different capture seasons.
If one shows bare ground and the other shows a finished building, the site was built between the two
captures, and whichever shows *more* development is the later one. Where they disagree, trust the
more-developed frame as the current state.

⚠ **You are only judging the TWO BUILDINGS NAMED in the filename** -- the committed pair the solver
picked. A campus can hold an operating hall next to a construction site; the neighbours do not
matter.

## What to send back

One line per site. Copy this and fill it in -- no prose needed:

```
<KEY>  :  GROUND | ROOFTOP | MIXED | NOT_BUILT | NOT_A_DATA_CENTRE | CANNOT_TELL   -- <one clause why>
```

`CANNOT_TELL` is a real and useful answer. "I could not see it at this resolution" is worth more than
a guess, and the project has a tier for exactly that.

---

## 1. `NE_way_1253282102` — Meta Sarpy Data center, NE
| | |
|---|---|
| Files | `01_NE_way_1253282102_ESRI.jpg` · `01_NE_way_1253282102_USGS.jpg` |
| Committed pair | OSM **1253282101** (Meta Sarpy Data center) → OSM **1253282102** (Meta Sarpy Data center) |
| Operators (OSM) | none tagged |
| Verdict now | (none recorded) |
| What I read | Meta Sarpy - equipment looked ROOFTOP along the roof ridges |
| Why it matters | This site is OFFERED right now on no verdict at all. If it is rooftop it should be refused; if it is ground-level it should be cleared. Either way this is the live gap. |

## 2. `AZ_way_300959969` — CyrusOne PHX8, AZ
| | |
|---|---|
| Files | `02_AZ_way_300959969_ESRI.jpg` · `02_AZ_way_300959969_USGS.jpg` |
| Committed pair | OSM **1227682824** (CyrusOne PHX8) → OSM **977653858** (CyrusOne PHX4) |
| Operators (OSM) | none tagged |
| Verdict now | ROOFTOP (refused) |
| What I read | CyrusOne PHX8 - rooftop looked dominant |
| Why it matters | My weakest rooftop call -- I flagged it myself. If it is really ground-level we are refusing a real in-scope site and losing it for no reason. |

## 3. `OR_way_734323663` — Digital Realty PDX11 Data Center, OR
| | |
|---|---|
| Files | `03_OR_way_734323663_ESRI.jpg` · `03_OR_way_734323663_USGS.jpg` |
| Committed pair | OSM **1153935548** (Digital Realty PDX11 Data Center) → OSM **734323663** (Digital Realty PDX11 Data Center) |
| Operators (OSM) | none tagged |
| Verdict now | ROOFTOP (refused) |
| What I read | Digital Realty PDX11 - arrays across nearly the whole roof |
| Why it matters | Confirms or overturns a refusal. I am fairly confident here, but confidence is not a verdict. |

## 4. `TX_way_577628941` — LightEdge Austin II, TX
| | |
|---|---|
| Files | `04_TX_way_577628941_ESRI.jpg` · `04_TX_way_577628941_USGS.jpg` |
| Committed pair | OSM **379204643** (LightEdge Austin II) → OSM **383888101** (Lumen Austin 1) |
| Operators (OSM) | none tagged |
| Verdict now | NO_GROUND_PLANT_VISIBLE (refused) |
| What I read | LightEdge Austin II - generic industrial park, no plant visible |
| Why it matters | LightEdge Austin II is a REAL operating colo at this address. The question is only whether an outdoor condenser bank exists on the committed buildings. |

## 5. `VA_way_460175664` — Digital Realty IAD42 (Building R), VA
| | |
|---|---|
| Files | `05_VA_way_460175664_ESRI.jpg` · `05_VA_way_460175664_USGS.jpg` |
| Committed pair | OSM **1544360250** (unnamed) → OSM **1534356804** (unnamed) |
| Operators (OSM) | none tagged |
| Verdict now | PAIR_NOT_BUILT (refused, kept on map) |
| What I read | office park in USGS, cleared pads in ESRI |
| Why it matters | The Digital Realty campus is real; the question is whether the two committed footprints are built. |

## 6. `NV_way_984796364` — Switch Edge 1, NV
| | |
|---|---|
| Files | `06_NV_way_984796364_ESRI.jpg` · `06_NV_way_984796364_USGS.jpg` |
| Committed pair | OSM **585998678** (Switch Las Vegas 9) → OSM **617194689** (Switch Las Vegas 11) |
| Operators (OSM) | none tagged |
| Verdict now | NOT_A_DATA_CENTRE (REMOVED from map) |
| What I read | semi-trailers at loading docks - distribution warehouses |
| Why it matters | REMOVED from the map entirely. Highest consequence if I am wrong. |

## 7. `VA_way_1510517639` — Amazon Web Services, VA
| | |
|---|---|
| Files | `07_VA_way_1510517639_ESRI.jpg` · `07_VA_way_1510517639_USGS.jpg` |
| Committed pair | OSM **1510517638** (Amazon Web Services) → OSM **1510517639** (Amazon Web Services) |
| Operators (OSM) | none tagged |
| Verdict now | NOT_BUILT (REMOVED from map) |
| What I read | raw land in USGS, shell + foundation footings in ESRI |
| Why it matters | REMOVED from the map entirely. Highest consequence if I am wrong. |

## 8. `AZ_way_1456975949` — AZ facility AZ_way_1456975949
| | |
|---|---|
| Files | `08_AZ_way_1456975949_ESRI.jpg` · `08_AZ_way_1456975949_USGS.jpg` |
| Committed pair | OSM **1456975948** (unnamed) → OSM **1456975949** (unnamed) |
| Operators (OSM) | none tagged |
| Verdict now | NOT_BUILT (REMOVED from map) |
| What I read | bare graded desert, no structures |
| Why it matters | This is the same facility as the hand-refused PHOENIX metro, so a NOT_BUILT here agrees with a call this project already made independently. |

