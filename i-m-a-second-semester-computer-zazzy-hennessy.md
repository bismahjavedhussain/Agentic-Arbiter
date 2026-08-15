# Learning Plan — Conformal-Calibrated Free-Cooling Agent (~1 month, solo, beginner)

## Context

You are building an autonomous agent that recommends, hour by hour, whether a data center should run
free cooling (economizer) or mechanical chillers, based on hyperlocal wet-bulb forecasts from the
FortyGuard API, with conformal prediction supplying calibrated confidence. You want **conceptual
mastery**, not build instructions — enough to implement it *and* defend it under expert questioning.

This plan is deliberately sized to a beginner with ~1 month. It is **tight**. The study days below
total roughly 23–24 focused days across ~30 calendar days, and you must build simultaneously. I have
marked what to cut if you fall behind. Every resource below was verified to exist before inclusion;
where I could not verify something, it says so explicitly.

### Day-1 risk check — do this BEFORE committing to the design

From the FortyGuard docs (verified earlier in this session), three facts constrain your project, and
one is a genuine risk:

1. **Forecast horizon is 12 hours, on `POST /v1/heatmap` only.** Docs: *"Create Heatmap additionally
   supports forecasting up to 12 hours beyond the current time."*
2. **Wet-bulb lives on a different endpoint** — `POST /v1/env_params` returns
   `wet_bulb_temperature_celsius`. That endpoint takes a **point** (lat/lon) plus a `temperature`
   value, and the docs say its date/time *"should match the heatmap you generated for the same
   location and time."*
3. **RISK: the docs never state that `env_params` accepts future timestamps.** The 12-hour forecast
   sentence is scoped to Create Heatmap. Your entire design assumes forecast *wet-bulb*.

**Test this on day 1**, before building anything: submit a heatmap for `now + 6h`, then call
`env_params` for that same future timestamp and see whether it returns wet-bulb or a 400. If it
rejects future times, your fallback is to derive wet-bulb yourself from forecast dry-bulb +
humidity (see Tier 1, Concept 3 — `psychrolib` / Stull 2011). Knowing this on day 1 versus day 15
is the difference between a finished project and a rewrite.

Also note for later: history goes back to `2019-01-01`. **That historical range is your conformal
calibration set** — without it you have no residuals to calibrate on. And the docs specify *no*
numeric rate limit and *no* credit-cost formula, so instrument your own usage counter early.

---

# TIER 1 — Concepts you must understand to BUILD this

Ordered by when you will actually need them.

---

## 1. What an "agent" technically is — the perceive/reason/act loop
**~1.5 days**

**(a) What it is, and why you need it.** An agent is a program that runs a loop: it *perceives*
(pulls state from the world), *reasons* (decides what to do next, possibly choosing among available
actions), and *acts* (calls a tool that changes something or fetches something), then repeats —
carrying state across iterations. The distinction that matters for you: a **single LLM call** is
stateless text-in/text-out; a **script** has a fixed control flow you wrote in advance; an **agent**
chooses its own next action at runtime based on what it observed. Your project is genuinely agentic
in a narrow, defensible sense: it decides *how many* nearby points to sample based on how much
disagreement it finds, it decides whether it has enough confidence to recommend, and it decides
whether to escalate to a human. Be honest that much of your control flow is fixed — that is a
strength for a safety system, not a weakness, and Tier 2 gives you the language to defend it.

**(b) Days:** 1.5. This is orientation, not deep theory. Do a first pass now and return to it in
week 4 when you write your interview narrative.

**(c) Black box vs. deep.** *Deep:* the perceive–reason–act loop, what state persists across
iterations, and precisely where in YOUR system an LLM is and is not in the decision path (this is
interview-critical — see Tier 2 #4). *Black box:* agent frameworks (LangChain, LangGraph, CrewAI).
Do not learn a framework this month; write the loop yourself in plain Python. You will understand it
better and it is ~100 lines.

**Sources:**
- Anthropic, **"Building effective agents"** (Schluntz & Zhang, Dec 19 2024) —
  https://www.anthropic.com/engineering/building-effective-agents — *Start here.* Its
  workflows-vs-agents distinction is exactly the vocabulary you need, and it explicitly argues for
  the simplest thing that works.
- Russell & Norvig, *Artificial Intelligence: A Modern Approach*, **4th ed., Chapter 2 "Intelligent
  Agents"** — https://aima.cs.berkeley.edu/ — for rational agents, PEAS, environment properties.
  Read for the framing; skip the rest of the book.

---

## 2. Working with a REST API: auth, async polling, retries, timeouts, errors
**~3 days**

**(a) What it is, and why you need it.** Everything downstream depends on reliably getting numbers
out of FortyGuard. Two things make this harder than a typical beginner API exercise. First, it is
**asynchronous**: you `POST` and get back an `activity_id`, then poll `GET /v1/status/{activity_id}`
until status is `Completed` or `Failed`. That means you need a polling loop with bounded attempts, a
sleep interval, and a timeout — the docs' own example polls 120 times at 5-second intervals.
Second, it is a **networked dependency in a decision system**: if it hangs or 429s, your agent must
degrade safely rather than crash or, worse, silently recommend free cooling on stale data. You need
retries with **exponential backoff and jitter** (jitter matters because without it, retries
synchronize and hammer the server), idempotency thinking, and explicit handling for each documented
status code (400/422, 401, 403, 404, 429, 500).

**(b) Days:** 3. This is where beginners lose the most time. Budget it honestly.

**(c) Black box vs. deep.** *Deep:* the async submit→poll→retrieve lifecycle; timeout vs. retry vs.
backoff as three distinct ideas; what your agent does when data is unavailable (fail **safe** =
recommend chillers, the expensive-but-safe option). *Black box:* TLS, HTTP/2, connection pooling
internals. Use `requests`; do not hand-roll HTTP.

**Sources:**
- Microsoft Azure Architecture Center, **"Asynchronous Request-Reply pattern"** —
  https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply — the
  best free writeup of exactly the submit/poll/retrieve shape FortyGuard uses.
- Marc Brooker, AWS Architecture Blog, **"Exponential Backoff And Jitter"** (Mar 4 2015) —
  https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ — short, canonical, and
  the jitter argument is a nice thing to be able to explain out loud.
- `requests` docs — https://requests.readthedocs.io/en/latest/ ; `tenacity` (retry decorators) —
  https://tenacity.readthedocs.io/en/latest/ ; `urllib3.util.Retry` reference (has `backoff_factor`,
  `status_forcelist`, `backoff_jitter`, `respect_retry_after_header`) —
  https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html
- MDN, **HTTP response status codes** —
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status
- FortyGuard's own Quickstart / Known Limitations pages (the status-code table and the
  `activity_id` lifecycle are documented there).

---

## 3. The domain: wet-bulb temperature, psychrometrics, and free cooling
**~2 days**

**(a) What it is, and why you need it.** Wet-bulb temperature is the lowest temperature air can be
cooled to by evaporating water into it. It is the hard physical floor on evaporative cooling: **a
cooling tower cannot cool water below the ambient wet-bulb**, and the gap between the two is the
"approach" temperature. That single fact is why your whole project keys on wet-bulb rather than
ordinary dry-bulb temperature — it is the variable that determines whether free cooling is
physically capable of holding the facility's supply-water setpoint. You also need the distinction
between **airside** economizers (pull in outside air directly; keyed more to dry-bulb and humidity)
and **waterside** economizers (cooling tower/heat exchanger; keyed to wet-bulb). Your project as
described is a waterside/evaporative story, so wet-bulb is the right variable — but you should be
able to say *why* explicitly, because it is the most likely domain question you will get.

Concretely: ENERGY STAR's guidance says waterside economizers suit sites where wet-bulb is below
**55 °F for 3,000+ hours/year**. That gives you a real-world sanity anchor for your threshold.

**(b) Days:** 2. You are not becoming an HVAC engineer. You need enough to defend the variable
choice, set a defensible threshold, and not say anything physically false.

**(c) Black box vs. deep.** *Deep:* why wet-bulb bounds evaporative cooling; approach temperature;
airside vs. waterside; that your threshold is a **modeling assumption you chose**, not physics
handed down — and you should be able to state the number and its source. *Black box:* the full
psychrometric chart, enthalpy calculations, ASHRAE's complete formulation. Use a library.

**Sources:**
- ENERGY STAR (US EPA), **"Consider Water-Side Economizers"** —
  https://www.energystar.gov/products/data_center_equipment/16-more-ways-cut-energy-waste-data-center/consider-water-side-economizers
  — and the companion **"Use an Air-Side Economizer"** page. Free, authoritative, short.
- **PsychroLib** — https://github.com/psychrometrics/psychrolib (MIT, Python, implements ASHRAE
  formulations). Paper: Meyer et al. (2019), *JOSS* 4(33):1137, https://doi.org/10.21105/joss.01137.
  Use this to compute wet-bulb from dry-bulb + RH if `env_params` won't serve future timestamps.
- Stull, R. (2011), **"Wet-Bulb Temperature from Relative Humidity and Air Temperature"**, *J.
  Applied Meteorology and Climatology* 50(11):2267–2269, doi:10.1175/JAMC-D-11-0143.1. Closed-form
  approximation, MAE < 0.3 °C. **Caveat worth knowing and citing:** it assumes sea-level pressure
  and is valid 5–99% RH, −20 to +50 °C — so it is wrong for a high-altitude site without correction.
  Free author copy: https://open.library.ubc.ca/soa/cIRcle/collections/facultyresearchandpublications/52383/items/1.0041967
- LBNL/DOE FEMP, **"Best Practices Guide for Energy-Efficient Data Center Design"** (rev. July 2024)
  — https://datacenters.lbl.gov/sites/default/files/2025-07/best-practice-guide-data-center-design.pdf
- SPX/Marley, **"Cooling Tower Fundamentals"** (2nd ed., Hensley) —
  https://spxcooling.com/wp-content/uploads/Cooling-Tower-Fundamentals.pdf — best free rigorous
  treatment of range/approach/wet-bulb. Note it is a **manufacturer** publication, not a standards
  body; fine for learning, cite carefully.
- ASHRAE Standards **90.1** (economizer requirements, §6.5.1) and **90.4** (data center energy) are
  available as **free read-only versions** —
  https://www.ashrae.org/technical-resources/standards-and-guidelines/read-only-versions-of-ashrae-standards
  Optional. *Thermal Guidelines for Data Processing Environments* (the A1–A4 classes) is **paid**;
  the free route to the classes is ASHRAE's reference card PDF, linked from their bookstore
  supplemental files.

---

## 4. Tool calling / function calling at runtime
**~2 days**

**(a) What it is, and why you need it.** Tool calling is the mechanism by which an LLM, instead of
emitting prose, emits a structured request to invoke a function you defined — you execute it and
feed the result back. It is what lets a language model touch the real world. In your project the
tools are things like `get_wetbulb_forecast(lat, lon, hours)`, `sample_microclimate(site)`,
`log_recommendation(...)`. The conceptual point to internalize: the model does not run your code, it
*requests* a call, and **you** remain in control of whether and how to execute it. That control
point is exactly where your human-in-the-loop gate lives.

**(b) Days:** 2.

**(c) Black box vs. deep.** *Deep:* the request/execute/return-result cycle; that tool schemas are a
contract and vague descriptions cause bad calls; that you validate arguments before executing
(an LLM can request `lat=999`). *Black box:* how the model is trained to emit tool calls; the
provider's JSON-schema internals.

**Sources:**
- Anthropic tool use docs — https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
  (note: the old `docs.anthropic.com` URLs now redirect to `platform.claude.com`), plus the
  "how tool use works" and "tool reference" subpages.
- Anthropic's open-source **`courses`** repo — https://github.com/anthropics/courses — includes a
  dedicated tool-use course. Free.
- Hugging Face **AI Agents Course** — https://huggingface.co/learn/agents-course/unit0/introduction
  — confirmed free, with free certificates. Good structured alternative if you want a syllabus.
- *(Anthropic Academy at https://anthropic.skilljar.com/ also exists and looks relevant, but I could
  not verify from Anthropic directly that it is free — check before relying on it.)*

---

## 5. Decision-making under uncertainty: thresholds, asymmetric cost, cost-loss
**~2.5 days**

**(a) What it is, and why you need it.** This is the concept that turns a forecast into an action,
and it is the part beginners skip. You are not asking "will wet-bulb stay below threshold?" — you
are asking "given my uncertainty, is switching to free cooling *worth it*?" Those are different
questions because **the two errors cost wildly different amounts**. Wrongly running chillers wastes
money. Wrongly running free cooling risks a thermal excursion in a facility full of expensive
hardware — potentially catastrophic. That asymmetry means your decision threshold should **not** be
"50% chance it's fine." The classical framework here is the **cost-loss decision model** from
meteorology: you act protectively when the probability of the bad event exceeds the ratio of the
cost of protecting to the loss from being unprotected (C/L). This gives you a principled, defensible
way to pick your confidence level instead of grabbing 95% because it looks standard. It also directly
motivates **one-sided** bounds: you care about the upper bound on wet-bulb, not a symmetric interval.

**(b) Days:** 2.5.

**(c) Black box vs. deep.** *Deep:* expected value under asymmetric loss; the C/L ratio and how it
maps to your confidence threshold; why you want a one-sided upper bound; why a point forecast alone
is insufficient for this decision. *Black box:* full utility theory, MDPs, reinforcement learning
(explicitly out of scope — see Skip list).

**Sources:**
- Russell & Norvig, AIMA 4th ed., chapters on **decision theory / making simple decisions** — for
  expected utility and decision-theoretic framing.
- The **cost-loss ratio** model is standard in forecast-value literature. The canonical modern
  reference is Richardson (2000), *"Skill and relative economic value of the ECMWF ensemble
  prediction system"*, Quarterly Journal of the Royal Meteorological Society. **I did not verify
  this citation in this session** — confirm it before citing it in an interview. The *concept* is
  well established and easy to find under "cost-loss ratio forecast value"; search that term rather
  than trusting my citation.
- Gneiting & Raftery (2007), **"Strictly Proper Scoring Rules, Prediction, and Estimation"**, *JASA*
  102(477):359–378 — for why you score probabilistic forecasts the way you do. **Not verified this
  session**, though I am reasonably confident it exists; check before citing. Overlaps with Concept 7.

---

## 6. Agent state and memory
**~1.5 days**

**(a) What it is, and why you need it.** Memory is what makes your system an agent that *learns
about itself* rather than a stateless recommender. You need three distinct kinds and should not
conflate them: **working state** (this hour's forecasts, samples, current decision), **episodic
memory** (a durable log of every past recommendation: what it predicted, what confidence, what it
recommended, what the operator did), and **outcome memory** (what actually happened — the realized
wet-bulb, joined back to the prediction after the fact). That third one is what enables
self-scoring, and it is also, not coincidentally, exactly the data your conformal calibration needs.
Design the log schema early and deliberately: if you don't record predicted-vs-realized with
timestamps, you cannot calibrate, cannot evaluate, and cannot demo the self-scoring feature.

**(b) Days:** 1.5. The concepts are simple; the discipline of designing the schema up front is the
real content.

**(c) Black box vs. deep.** *Deep:* the three memory types; the join between prediction and realized
outcome; that your log is simultaneously your audit trail, your eval set, and your calibration set.
*Black box:* vector databases and embedding-based memory — **you do not need these** (see Tier 2 #3).
SQLite or even append-only JSONL is correct and defensible here.

**Sources:** No single canonical source; this is mostly good engineering judgment. Python `sqlite3`
docs are sufficient. The Anthropic "Building effective agents" post touches on state in workflows.
*I am not aware of a single authoritative free tutorial specifically on agent memory design that I
can confidently recommend — treat this as design work rather than something to study.*

---

## 7. Evaluation: scoring rules, calibration, backtesting
**~2 days**

**(a) What it is, and why you need it.** You need to answer "does it work?" with numbers, and for a
probabilistic system that means more than accuracy. Three ideas: **proper scoring rules** (e.g.
Brier score for binary events, pinball/quantile loss for intervals) reward honest probabilities and
cannot be gamed by overconfidence; **calibration** asks whether your stated 90% confidence actually
happens 90% of the time, visualized with a reliability diagram; and **backtesting / walk-forward
validation** is how you evaluate a time-series system without leaking future information into past
predictions. That last one is a real trap: ordinary random train/test splits are **invalid** for
time series, and an interviewer may well probe whether you understand why. Study this *before*
conformal prediction, because coverage — the thing conformal guarantees — is an evaluation concept,
and CP will make much more sense if you already think in these terms.

**(b) Days:** 2.

**(c) Black box vs. deep.** *Deep:* empirical coverage vs. nominal coverage; interval width as the
cost of coverage (trivially, an infinitely wide interval has 100% coverage and zero value — so you
always report coverage *and* width together); why random splits leak in time series; your baselines
(see Tier 2 #6). *Black box:* the full theory of proper scoring rules; exotic metrics like CRPS
decompositions.

**Sources:**
- Angelopoulos & Bates' gentle intro (Concept 8) covers coverage/width evaluation well — you can
  fold this in.
- The MAPIE docs' examples show coverage-and-width reporting concretely —
  https://mapie.readthedocs.io/en/stable/
- Gneiting & Raftery (2007) as above (**unverified citation** — check first).
- For backtesting/walk-forward specifically: `sklearn.model_selection.TimeSeriesSplit` docs are a
  concrete, correct starting point and explain the forward-chaining idea.

---

## 8. Conformal prediction — the core
**~4 days**

**(a) What it is, and why you need it.** Conformal prediction turns any point predictor into an
interval predictor with a **finite-sample, distribution-free coverage guarantee**. The mechanism is
remarkably simple, which is part of why it is defensible: take a held-out **calibration set**, run
your model on it, compute a **nonconformity score** for each point (for regression, typically the
absolute residual), take the appropriate empirical quantile of those scores, and add/subtract it
from new predictions. That's split (inductive) conformal prediction. The guarantee: your intervals
cover the truth at least 1−α of the time, **without assuming** the data is Gaussian, without
assuming your model is correct, and **for finite samples** — not asymptotically. For your project
this is precisely the missing piece: FortyGuard hands you a point forecast with **no uncertainty
estimate whatsoever** (I checked the docs — there is no confidence or spread field). You cannot make
a risk-aware decision from a bare number. Conformal lets you wrap that number in a calibrated bound
using nothing but your own logged history of forecast-vs-realized residuals.

The assumption you must understand cold: the guarantee requires **exchangeability** — roughly, that
the joint distribution of your data is invariant to reordering. Standard CP's validity rests on it,
and **temperature time series flatly violate it** (today's error correlates with yesterday's;
there's diurnal and seasonal structure). That violation is not a footnote — it is the entire reason
Concept 9 exists, and it is the single most likely place a sharp interviewer will press you.

**(b) Days:** 4.

**(c) Black box vs. deep.** *Deep:* split conformal end to end, by hand, on paper; what a
nonconformity score is and that you *choose* it; the exact role of the calibration set; the precise
statement of the guarantee **and what it does not promise** (marginal, not conditional — Tier 2 #5);
exchangeability and why your data breaks it. *Black box:* full-transductive CP (computationally
impractical, not needed); the measure-theoretic proofs. You need to *state* the guarantee correctly
and explain the intuition, not reproduce the proof.

**Sources (authoritative, as requested — these are the real foundational texts):**
- **Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free
  Uncertainty Quantification"**, arXiv:2107.07511 — https://arxiv.org/abs/2107.07511 — **this is
  your primary text.** Published as a monograph under the different title *"Conformal Prediction: A
  Gentle Introduction"*, Foundations and Trends in ML 16(4):494–591, 2023. Companion code:
  https://github.com/aangelopoulos/conformal-prediction (Jupyter notebooks on real data).
- **Angelopoulos' 3-part video tutorial** (linked from that repo) — Part 1
  https://www.youtube.com/watch?v=nql000Lu_iE , Part 2 (conditional coverage & diagnostics)
  https://www.youtube.com/watch?v=TRx4a2u-j7M , Part 3
  https://www.youtube.com/watch?v=37HKrmA5gJE . Also an IMSI tutorial with downloadable slides:
  https://www.imsi.institute/videos/tutorial-on-conformal-prediction-and-distribution-free-uncertainty-quantification/
- **Shafer & Vovk, "A Tutorial on Conformal Prediction"**, JMLR 9:371–421 (2008) —
  https://jmlr.org/papers/v9/shafer08a.html — the original tutorial by the field's founders.
- **Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World*** — Springer; **2nd ed.
  2022** (doi:10.1007/978-3-031-06649-8). The foundational book. Reference, not a read-through.
  Companion site with free related PDFs: https://www.alrw.net/
- **Romano, Patterson & Candès, "Conformalized Quantile Regression"**, NeurIPS 2019,
  arXiv:1905.03222 — how to get *adaptive-width* intervals. Directly relevant: your uncertainty is
  almost certainly larger at hour 12 than hour 1, and constant-width intervals would be wasteful.
- **MAPIE** (scikit-learn-contrib) — https://mapie.readthedocs.io/en/stable/ — implement by hand
  first, then cross-check against MAPIE.
- Curated index if you want to go further: https://github.com/valeman/awesome-conformal-prediction

---

## 9. Time-series / adaptive conformal prediction — your centerpiece
**~5 days**

**(a) What it is, and why you need it.** Since exchangeability fails for temperature series, standard
split CP's guarantee does not hold as stated — empirically you tend to get under-coverage exactly
when you least want it (during unusual weather, which is precisely when the free-cooling decision is
risky). Adaptive conformal methods fix this by **updating the quantile online**: **ACI (Adaptive
Conformal Inference)** treats the miscoverage level α as something to control with a feedback loop —
if you have been under-covering recently, widen; if over-covering, tighten — and it provides
long-run coverage guarantees *without any exchangeability assumption at all*. That last property is
the thing to be able to say out loud: ACI's guarantee is a long-run/asymptotic one that survives
arbitrary distribution shift, which is a genuinely different (and weaker, but more honest) promise
than split CP's finite-sample marginal guarantee. Related approaches: **EnbPI** (ensemble batch
prediction intervals, bootstrap-based, no data splitting), **AgACI** (aggregates multiple ACI
learning rates so you don't have to tune one), **DtACI** (dynamically tuned). There is also a
principled framework for **why** CP degrades gracefully under non-exchangeability — Barber et al.'s
"beyond exchangeability" paper, which gives a coverage bound in terms of total-variation distance
from exchangeability. Knowing that paper exists and roughly what it says is a strong signal.

Practical note that will save you days: **MAPIE implements exactly this.**
`mapie.regression.TimeSeriesRegressor` supports `method="aci"` and `method="enbpi"`, with
`partial_fit` for online residual updates. Implement ACI by hand first — it's about 20 lines and the
understanding is the whole point — then validate against MAPIE.

**(b) Days:** 5. This is the deepest item; it is also your differentiator. Do not compress it.

**(c) Black box vs. deep.** *Deep:* precisely why exchangeability fails for your data (autocorrelated
residuals, diurnal cycle, seasonality); the ACI update rule and the intuition for the feedback loop;
that ACI's guarantee is **long-run, not finite-sample** — a real and stateable tradeoff; how you
choose the learning rate γ and what it trades off (responsiveness vs. stability). *Black box:* the
convergence proofs; the full theory of DtACI's expert-aggregation machinery; EnbPI's bootstrap
internals if you go with ACI.

**Sources (all verified):**
- **Gibbs & Candès, "Adaptive Conformal Inference Under Distribution Shift"**, NeurIPS 2021 —
  https://arxiv.org/abs/2106.00170 — **the core ACI paper. Read this one properly, more than once.**
- **Gibbs & Candès, "Conformal Inference for Online Prediction with Arbitrary Distribution Shifts"**,
  **JMLR 25 (2024), paper 22-1218** — https://jmlr.org/papers/v25/22-1218.html (arXiv:2208.08401).
  DtACI. Cite the JMLR version, not the arXiv preprint — the preprint-only citation is now outdated.
- **Zaffran, Féron, Goude, Josse & Dieuleveut, "Adaptive Conformal Predictions for Time Series"**,
  ICML 2022, PMLR 162:25834–25866 — https://proceedings.mlr.press/v162/zaffran22a.html — AgACI, and
  notably it is an **electricity-price forecasting** application, so the framing is close to yours.
  Project page: https://mzaffran.github.io/acp-ts/ . MAPIE has a worked example reproducing it.
- **Xu & Xie, "Conformal prediction interval for dynamic time-series"**, ICML 2021, PMLR
  139:11559–11569 — https://proceedings.mlr.press/v139/xu21h.html — EnbPI. Code:
  https://github.com/hamrel-cxu/EnbPI
- **Barber, Candès, Ramdas & Tibshirani, "Conformal prediction beyond exchangeability"**, *Annals of
  Statistics* 51(2):816–845, 2023 — https://arxiv.org/abs/2202.13415 — the theory of what happens
  when exchangeability fails. Read the abstract and intro at minimum; it is the best single citation
  for the assumption question.
- **Stankevičiūtė, Alaa & van der Schaar, "Conformal Time-Series Forecasting"**, NeurIPS 2021 —
  https://proceedings.neurips.cc/paper/2021/hash/312f1ba2a72318edaaa995a67835fad5-Abstract.html —
  relevant for **multi-horizon** coverage (your 12-hour window), see Tier 2 #10. Code:
  https://github.com/kamilest/conformal-rnn
- Ryan Tibshirani's free lecture slides: https://www.stat.berkeley.edu/~ryantibs/statlearn-s23/lectures/conformal.pdf
  and on distribution shift: https://www.stat.berkeley.edu/~ryantibs/statlearn-s24/lectures/conformal_ds.pdf

---

# TIER 2 — Cross-examination concepts

For each: definition → your stance → the defensible answer.

---

### 1. ReAct and other agent reasoning patterns
**Definition.** ReAct (Yao et al., ICLR 2023, arXiv:2210.03629) interleaves free-form reasoning
traces with actions, letting an LLM think, act, observe, and re-think in an open loop. Planning-based
agents instead generate a multi-step plan up front and then execute it.

**Your stance.** Partially used / deliberately constrained.

**The defense.** *"My loop is closer to a structured workflow than to open-ended ReAct, and that's a
deliberate safety choice. ReAct shines when the action space is large and the path is unknown — web
research, multi-hop QA. My action space is small and known: fetch forecasts, sample points, compute
an interval, compare to a threshold, recommend. The variable part isn't which tool to call, it's the
numeric judgment, and that's handled by conformal prediction, not by LLM reasoning. Open-ended
reasoning would add nondeterminism to a decision that needs to be auditable and reproducible for an
operator. I do use LLM reasoning for the parts that suit it — summarizing microclimate disagreement
and explaining the recommendation in plain language."* Honest tradeoff to concede: a ReAct-style
agent would handle novel situations you didn't anticipate more gracefully; yours will do something
sensible-but-fixed instead.

**Learn from:** the ReAct paper's abstract/intro; Anthropic's "Building effective agents" for the
workflow-vs-agent distinction; optionally Reflexion (Shinn et al., NeurIPS 2023, arXiv:2303.11366),
whose self-critique loop is the closest analogue to your self-scoring feature — though yours scores
against ground truth, which is stronger than verbal self-critique.

---

### 2. Single-agent vs. multi-agent
**Definition.** Decomposing a system into multiple specialized agents that communicate, versus one
agent with multiple tools.

**Your stance.** Rejected, deliberately.

**The defense.** *"I considered splitting into a forecasting agent, a decision agent, and an
explanation agent. I rejected it because there's no genuine parallelism or specialization to
exploit — the stages are strictly sequential and share one small state object. Multi-agent adds
coordination overhead, more failure modes, and more places for information to get garbled in
translation between agents, in exchange for modularity I can get from plain functions. The
multi-agent case gets strong when subtasks need genuinely different tools or can run concurrently;
mine don't."* Concede: if you extended to hundreds of sites with per-site specialization, or added a
genuinely adversarial "red team" agent to challenge recommendations, the calculus would change.

**Learn from:** Anthropic's "Building effective agents" (orchestrator-workers and its cost
discussion) — https://www.anthropic.com/engineering/building-effective-agents

---

### 3. RAG (Retrieval-Augmented Generation)
**Definition.** Retrieving relevant documents from a corpus and injecting them into an LLM's context
so it can answer grounded in external text.

**Your stance.** Out of scope — and this is the easy one to answer well.

**The defense.** *"RAG solves the problem of getting relevant **unstructured text** into a model's
context. I don't have a text corpus. My inputs are numeric time series from a structured API, and my
decision is a numerical comparison against a threshold with a calibrated bound. There's nothing to
retrieve and nothing to semantically search. Using a vector database here would be architecture
cosplay."* Then show range: *"The one place RAG would become relevant is if I wanted the agent to
reason over facility-specific documentation — equipment manuals, ASHRAE guidance, site runbooks — to
justify thresholds per facility. That's a plausible v2, and it would be genuine RAG. It just isn't
this project."* That last move — knowing exactly when it *would* apply — is what separates a good
answer from a defensive one.

**Learn from:** you need only a working definition. Do **not** spend days on RAG.

---

### 4. Where is the LLM, actually? / Is this even an agent?
**Definition.** The question of whether the LLM is making the consequential decision, or orchestrating
around a deterministic one.

**Your stance.** Used, but deliberately kept out of the numeric decision path. **This is the most
important architectural claim you will make.**

**The defense.** *"The LLM never decides the cooling mode. The decision is: compute a conformal upper
bound on wet-bulb across the horizon, compare to the safety threshold, apply the cost-asymmetric
confidence rule. That's deterministic and reproducible — I can replay any historical recommendation
and get the identical answer. The LLM does three things it's actually good at: orchestrating which
tools to call and how many microclimate samples to take, summarizing conflicting local readings, and
translating a numeric decision into plain language for a non-technical operator. If I let the LLM do
the arithmetic I'd get an unauditable system with no coverage guarantee — I'd have thrown away the
entire point of the conformal layer."* If pressed on "so is it really an agent?", don't get
defensive: *"It's an agent in the perceive–reason–act sense — it runs autonomously on a loop,
chooses actions like how deeply to sample, maintains memory, and scores itself. It's not an agent in
the sense of open-ended LLM reasoning, and for a system touching physical infrastructure I'd argue
that's correct engineering, not a limitation."*

**Learn from:** Anthropic's "Building effective agents"; your own Tier 1 #1 study.

---

### 5. Conformal vs. simpler uncertainty methods — BOTH directions
**Definition.** Alternatives: naive residual quantiles (just take the 90th percentile of past
errors); parametric Gaussian intervals (±1.645σ); quantile regression; bootstrap/ensembles; Bayesian
methods (GPs, Bayesian NNs); or simply consuming a provider's own ensemble spread.

**Your stance.** Chose conformal — must defend against *both* "why not simpler?" and "why not
something more sophisticated?"

**Direction A — "Why not just use historical error percentiles? Isn't conformal overkill?"**
*"Split conformal with absolute-residual scores is **almost exactly** that — and I'd say so plainly.
The difference is that conformal gives it a precise finite-sample guarantee and a principled
framework for extending it: adaptive scores when uncertainty varies by horizon, and adaptive
conformal when the distribution shifts. Naive percentiles have no guarantee and quietly break under
drift. The added complexity is small and buys me a defensible statement about coverage — which
matters when I'm telling an operator it's safe to turn off the chillers."*

**Direction B — "Why not Bayesian / a full probabilistic model?"**
*"A Bayesian approach would give richer, conditional uncertainty — but its calibration is only as
good as its likelihood and prior. I'd be asserting a model of forecast error I can't validate, on
top of a third-party forecast whose internals I don't have. Conformal is model-agnostic and
distribution-free: it treats FortyGuard as a black box and calibrates on observed residuals, which
is exactly the right posture when you don't own the model. It's also far less to get wrong in a
month."* Concede honestly: *"The real cost is that I get **marginal** coverage, not conditional —
see below."*

**Direction C — "Why not use the provider's own uncertainty?"**
*"FortyGuard doesn't publish one. I checked the documented response schemas — there's no confidence,
spread, or ensemble field. So calibrating externally isn't a preference, it's the only option."*

**Learn from:** Angelopoulos & Bates §1–2 (arXiv:2107.07511); Romano et al. CQR (arXiv:1905.03222)
for the quantile-regression comparison.

---

### 6. Marginal vs. conditional coverage
**Definition.** Marginal coverage means your intervals cover the truth 90% of the time *averaged over
all conditions*. Conditional coverage means 90% *for every subgroup* — e.g. specifically on hot
summer afternoons. Conformal gives you the former, not the latter.

**Your stance.** Used, with a known and stateable limitation. **This is the sharpest question a CP-
literate interviewer can ask you, and most candidates fail it.**

**The defense.** *"My guarantee is marginal. That's a real limitation for my use case, because the
decision matters most in exactly the conditions where coverage could be worst — hot, humid,
marginal-wet-bulb days. Achieving distribution-free **conditional** coverage is provably impossible
in finite samples without further assumptions — that's Barber, Candès, Ramdas & Tibshirani, 'The
limits of distribution-free conditional predictive inference' (2021). So my mitigations are the
practical ones: adaptive-width scores (CQR-style) so intervals widen where the model is less certain;
Mondrian/group-conditional conformal, calibrating separately by strata like season or hour-of-day;
and explicitly evaluating coverage sliced by condition rather than only reporting the aggregate
number."*

**Learn from:** **Barber, Candès, Ramdas & Tibshirani, "The limits of distribution-free conditional
predictive inference"**, *Information and Inference* 10(2):455–482, 2021 —
https://arxiv.org/abs/1903.04684 (the canonical impossibility result). Also **Vovk, "Conditional
validity of inductive conformal predictors"**, ACML 2012, PMLR 25:475–490 —
https://proceedings.mlr.press/v25/vovk12.html — for the Mondrian/group-conditional taxonomy (note:
this is about *achieving* relaxed conditional validity, not the impossibility theorem — don't mix
them up). And Angelopoulos' video Part 2, which is specifically on conditional coverage and
diagnostics.

---

### 7. Multi-horizon / simultaneous coverage over your 12-hour window
**Definition.** If each hourly interval has 90% coverage individually, the probability that **all 12**
hold simultaneously is much lower — potentially far below 90%. Your agent commits to a cooling mode
for a *window*, so per-hour coverage is not the guarantee you actually need.

**Your stance.** Must address it — this is a genuine technical subtlety in your specific design, and
a sharp interviewer who notices your commitment window will go straight here.

**The defense.** *"Right — per-hour marginal coverage doesn't give me joint coverage over the window,
and since I commit to a mode for several hours, joint is what I actually care about. The simplest
correction is a Bonferroni-style adjustment: to get 90% joint coverage over 12 hours, target roughly
1 − 0.10/12 per hour. That's conservative — it ignores the strong positive correlation between
consecutive hours, so it'll be wider than necessary. The more principled route is a max-over-horizon
nonconformity score, which is essentially what Stankevičiūtė et al. do for multi-horizon conformal
forecasting. Given a month, I'd implement Bonferroni, state clearly that it's conservative, and
measure the actual joint coverage empirically."* Saying that unprompted is a strong signal.

**Learn from:** Stankevičiūtė, Alaa & van der Schaar, "Conformal Time-Series Forecasting", NeurIPS
2021 — https://proceedings.neurips.cc/paper/2021/hash/312f1ba2a72318edaaa995a67835fad5-Abstract.html

---

### 8. Did you train or fine-tune a model?
**Definition.** Training your own forecaster, or fine-tuning an LLM on domain data.

**Your stance.** No, on both — deliberately.

**The defense.** *"I didn't train a weather model, and I shouldn't have — FortyGuard's hyperlocal
forecast is the product of far more data and domain expertise than I could replicate, and rebuilding
it badly would be the least defensible thing in the project. Conformal prediction is specifically
designed to be model-agnostic: it wraps someone else's black-box predictor and calibrates it on
observed residuals. That's the whole appeal. I also didn't fine-tune an LLM — my LLM usage is
orchestration and explanation, where a general model with good prompting and tool definitions is
sufficient, and I have neither the training data nor a task-specific objective that would justify
it."* If pressed on whether you fit *anything*: be precise — *"I fit the conformal calibration
layer, which is one quantile computed from residuals, plus the ACI update. That's the only thing
learned from data, and that's by design."*

---

### 9. How do you evaluate this? What are your baselines?
**Definition.** Whether your evaluation is rigorous, and what you compare against.

**Your stance.** Used — and you must have concrete baselines ready, because "it seems to work" fails
here.

**The defense.** Have these named and ready: (1) **always chillers** — safe, expensive, the status
quo; your system must show cost savings against it. (2) **always free cooling when current wet-bulb
< threshold** — the naive reactive controller with no forecast; this is the baseline that proves
forecasting adds value. (3) **persistence forecast** — assume conditions stay as they are now; the
standard, surprisingly strong meteorological baseline that proves the API adds value over "nothing
changes." Then: *"I backtest on historical data with walk-forward validation — no random splits,
since that would leak future information. I report three things: empirical coverage vs. nominal
(does the 90% bound actually hold 90% of the time?), mean interval width (coverage alone is gameable
— an infinite interval has perfect coverage), and a decision-level metric: simulated cost versus each
baseline, counting threshold violations separately since they're the asymmetric failure."* Concede
the honest limitation: *"I'm evaluating a recommender in simulation against historical data. I have
no real facility, so I can't measure actual thermal outcomes or operator behavior — that's the main
gap between this and a deployed system."*

**Learn from:** Tier 1 #7 sources; `sklearn.model_selection.TimeSeriesSplit` docs for walk-forward;
MAPIE's coverage/width reporting examples.

---

### 10. Hallucination and grounding — does it apply here?
**Definition.** LLMs generating fluent but false content; grounding is tying output to verified
sources.

**Your stance.** Applies narrowly, and the honest answer is more interesting than "not applicable."

**The defense.** *"The numeric path can't hallucinate — those values come from an API and
deterministic arithmetic. But the **explanation layer** absolutely can. If the LLM writes 'wet-bulb
will stay near 14 °C all afternoon' and the actual forecast said 18 °C, that's a hallucination with
operational consequences, because the operator is making a decision from the prose, not from my JSON.
So I ground the explanation: the LLM receives the computed values and is constrained to report them,
and I can validate that numbers appearing in the output match the numbers I passed in. The failure
mode I care about isn't invented facts, it's **misrepresented confidence** — prose that sounds more
certain than the interval justifies."* That last sentence is the sophisticated version of this
answer and worth having ready.

---

### 11. Human-in-the-loop, and what full autonomy would cost
**Definition.** Requiring human approval before consequential actions.

**Your stance.** Used, deliberately.

**The defense.** *"Switching cooling modes in a live data center is high-consequence and hard to
reverse quickly — thermal mass means a wrong call takes time to recover from, and the downside is
hardware damage. My agent recommends and explains; a human approves. That's appropriate given that
my confidence guarantee is statistical, not absolute: at 90% coverage I'm explicitly wrong 10% of
the time, and someone should be accountable for those cases. Full autonomy would need substantially
more: much higher confidence thresholds, a validated fail-safe path (on any API failure or stale
data, default to chillers), automatic rollback on threshold breach, and a track record of
demonstrated calibration in production. The tradeoff is response latency and operator workload
versus catastrophic-error risk — and for v1 with no deployment history, that trade is obvious."*

**Learn from:** the human-in-the-loop / guardrails sections of Anthropic's "Building effective
agents".

---

### 12. Spatial sampling — are your microclimate points independent?
**Definition.** You sample multiple nearby points to characterize a site's microclimate. An
interviewer will ask what you do with them and whether the statistics are valid.

**Your stance.** Used — know the assumption you're making.

**The defense.** *"Nearby points are strongly spatially autocorrelated — that's Tobler's first law,
and it's the entire reason hyperlocal data has value. So I do **not** treat them as independent
samples and shrink my uncertainty by √n; that would be wrong and would make me overconfident. I use
them for two things: detecting spatial heterogeneity across the site, and taking a conservative
aggregate — the worst-case (highest) wet-bulb across sampled points rather than the mean, since the
hottest spot governs thermal safety."* Useful implementation note: FortyGuard's `POST /v1/heatmap`
takes a **GeoJSON polygon** and returns tiled values at 60/80/100 m granularity — so the heatmap
endpoint *is* your multi-point sampler, and its `stats_data` (min/max/mean/stddev across tiles) is
directly the heterogeneity measure you want. You don't need to hand-roll a sampling grid.

---

### 13. Fail-safe behavior and degradation
**Definition.** What the system does when its inputs fail.

**Your stance.** Used — and volunteering this makes you look like an engineer rather than a student.

**The defense.** *"Every failure mode defaults to the expensive-but-safe action: run chillers. API
timeout, 429, malformed response, forecast older than a staleness bound, or conformal interval wider
than a usability threshold — all of them produce 'insufficient confidence, stay on mechanical
cooling' plus a logged reason. The asymmetry of costs makes this the only sensible default: an
unnecessary chiller hour costs money, an unsafe free-cooling hour costs hardware."*

---

### 14. Calibration data and cold start
**Definition.** Conformal needs a calibration set of forecast-vs-realized residuals. Where does a
brand-new system get one?

**Your stance.** Must have an answer; this is a practical gotcha.

**The defense.** *"Cold start is real — on day one I have no residuals. FortyGuard exposes history
back to 2019-01-01, so I bootstrap the calibration set by pulling historical forecasts and realized
values for the site and computing residuals retrospectively. After that, the agent's own outcome log
extends the calibration set continuously, which is also what makes the adaptive conformal update
meaningful. If historical forecast data weren't available, I'd have to run in shadow mode —
recommending but not acting — until I'd accumulated enough residuals."* Know roughly how many
calibration points you need: for a 1−α bound you need at least ~1/α, so ≥ ~20 for 95%, and
realistically a few hundred for stability.

---

### 15. Distribution shift and drift
**Definition.** The relationship between forecast and reality changing over time — seasonally,
or because the provider updates its model.

**Your stance.** Directly addressed by your ACI choice — this is where your Tier 1 #9 work pays off.

**The defense.** *"This is precisely why I used adaptive conformal rather than vanilla split
conformal. Seasonal drift, and the possibility that FortyGuard silently updates its model, both
break the assumption that my old residuals describe my current errors. ACI's online update tracks
that automatically — if recent coverage degrades, intervals widen without me intervening. I monitor
rolling empirical coverage as a health metric, and a sustained drop is my signal that something
upstream changed."*

**Learn from:** Gibbs & Candès (arXiv:2106.00170); Barber et al. "beyond exchangeability"
(arXiv:2202.13415); Tibshirani's distribution-shift lecture slides.

---

# Suggested month-long order (learn interleaved with build)

**Before you write anything (days 1–3)**
- **Day 1: run the API risk check** described at the top. Everything downstream depends on it.
- Tier 1 #1 (agent loop, first pass) — Anthropic's "Building effective agents" + AIMA ch. 2.
- Start Tier 1 #2 (REST/async/polling).
- *Do not touch conformal prediction yet.* You need residuals before CP means anything.

**Week 1 (days 4–7) — get data flowing**
- Finish Tier 1 #2. Build the API client: auth, submit, poll, retry with backoff, structured errors.
- Tier 1 #3 (wet-bulb / free cooling domain, 2 days). Pick and **write down** your threshold and its
  justification now.
- **Build milestone:** a script that prints a 12-hour wet-bulb forecast for one site. Not an agent yet.

**Week 2 (days 8–14) — a working simple version**
- Tier 1 #4 (tool calling, 2 days).
- Tier 1 #5 (decision under uncertainty, 2.5 days) — the cost-asymmetry framing.
- Tier 1 #6 (memory/state, 1.5 days) — **design the log schema now**; CP depends on it.
- **Build milestone (end of week 2): a complete, unsophisticated agent that works end to end** —
  perceives, samples a few points, applies a naive threshold rule with a fixed safety margin, logs
  its recommendation, explains itself, and asks a human. Ugly is fine. This is your safety net: if
  everything after this fails, you still have a finished project.

**Week 3 (days 15–21) — make it honest, then make it calibrated**
- Tier 1 #7 (evaluation, 2 days) — build the backtest harness and the three baselines **before** CP,
  so you can measure whether CP actually helps.
- Tier 1 #8 (conformal core, 4 days) — Angelopoulos & Bates + videos. Implement split conformal **by
  hand** on your logged residuals. Replace the fixed safety margin with a conformal upper bound.
- **Build milestone:** measured empirical coverage vs. nominal, plus interval width.

**Week 4 (days 22–28) — the centerpiece**
- Tier 1 #9 (time-series/adaptive CP, 5 days) — Gibbs & Candès first, then Zaffran et al. Implement
  ACI by hand, then cross-check against MAPIE's `TimeSeriesRegressor(method="aci")`.
- Add the Bonferroni-style multi-horizon adjustment (Tier 2 #7) — cheap, and a strong talking point.
- Re-run the backtest: split CP vs. ACI, coverage and width, sliced by season/hour.

**Days 29–30 — consolidate for the interview**
- Write out Tier 2 answers **in your own words**, out loud. Do not memorize mine.
- Prepare one honest slide of limitations. Being the person who names their own weaknesses first is
  worth more than any feature.

**If you fall behind:** cut Tier 1 #9 down to ACI only (skip EnbPI/AgACI/DtACI entirely), and cut the
multi-horizon adjustment. Ship split conformal working and well-understood rather than adaptive
conformal half-understood. A crisp *"here's why exchangeability fails, here's what ACI does about it,
and I ran out of time to implement it"* beats a broken implementation you can't explain.

---

# Concepts to SKIP (honestly out of scope)

- **Agent frameworks** (LangChain, LangGraph, AutoGen, CrewAI). You'll spend days on abstractions and
  learn less than writing the loop yourself. Your loop is ~100 lines.
- **RAG, vector databases, embeddings.** Not your problem. Know the definition for the interview
  (Tier 2 #3) and move on.
- **Fine-tuning, LoRA, PEFT, RLHF.** You are not training a model. Zero payoff here.
- **Reinforcement learning / MDPs / bandits.** Tempting because "sequential decisions under
  uncertainty," but you'd need an environment model and far more data. Your decision is a calibrated
  threshold comparison. Be ready to *say* that if asked; don't study RL.
- **Deep learning forecasting** (LSTMs, Transformers, N-BEATS, TFT). You are consuming a forecast, not
  producing one. Skip entirely.
- **Full-transductive conformal prediction.** Computationally impractical and unnecessary; split CP
  is what everyone actually uses.
- **Conformal for classification** (APS, RAPS). Real and interesting, but your target is continuous.
- **Bayesian deep learning / GPs / MC dropout.** Know the one-line comparison for Tier 2 #5; don't
  implement.
- **MLOps: Docker, Kubernetes, CI/CD, cloud deployment.** Not what this project is judged on.
- **Advanced psychrometrics** beyond wet-bulb and approach temperature. Use `psychrolib`.
- **Multi-agent orchestration protocols.** See Tier 2 #2.

---

# The three Tier-2 concepts to be bulletproof on

Chosen by **likelihood × how much you lose by fumbling it**:

**1. Conformal vs. simpler methods, exchangeability, and marginal-vs-conditional coverage**
(Tier 2 #5 + #6). You are advertising CP as your centerpiece, so this *will* be probed, and it's the
one place a genuine expert can take you apart. You must be able to state the guarantee precisely,
say why exchangeability fails for temperature, explain what ACI does about it, and — without being
prompted — volunteer that your coverage is marginal rather than conditional and cite that
distribution-free conditional coverage is provably impossible. Nailing that unprompted is the single
highest-signal thing you can do in the whole interview.

**2. Where the LLM actually sits / is this really an agent?** (Tier 2 #4 + #1). This is the standard
skeptical opener for *any* agent project, and many candidates fold because they've never articulated
the boundary. Your answer is strong — the LLM orchestrates and explains, deterministic math decides —
but only if you can say it crisply and defend the choice as engineering judgment rather than
limitation.

**3. Evaluation and baselines** (Tier 2 #9). "How do you know it works?" gets asked in essentially
every technical interview, and beginners consistently have no real answer. Having three named
baselines, walk-forward validation, coverage-*and*-width reporting, and an honest statement of the
simulation gap will separate you from most candidates at your level.

**Also near-certain but cheap: RAG (Tier 2 #3).** Someone will ask. It takes ten minutes to prepare
and you should not spend more — but do prepare the "here's when it *would* apply" second half, which
is what makes the answer land.

---

## Verification note on sources

Every URL and citation above was checked in this session except three, which are flagged inline:
Richardson (2000) on cost-loss forecast value, and Gneiting & Raftery (2007) on proper scoring rules
— both concepts are well established, but confirm the exact citations before quoting them — and the
absence of a canonical agent-memory-design tutorial, where I found nothing I could confidently
recommend. Two corrections worth noting since you may search for them: Angelopoulos & Bates' arXiv
paper and its published monograph have **different titles**, and Gibbs & Candès' DtACI paper now has
a **JMLR 2024** citation that supersedes the arXiv-only reference you'll see in older bibliographies.
