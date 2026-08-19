# -*- coding: utf-8 -*-
"""EXPLAIN -- the seventh stage of the loop: say WHY, in a way that can be checked.

    python explain.py        # builds explanations for every case day and VERIFIES each one

ZERO API CALLS.

--------------------------------------------------------------------------------------------
WHY IT IS BUILT THIS WAY, AND NOT WITH A LOCAL LLM (yet)
--------------------------------------------------------------------------------------------
The plan was a local Nemotron narrator. Two measurements changed the design:

  1. VRAM IS NOT THE CONSTRAINT. The Warp ensemble peaks at **371 MiB** of 6,141 MiB, leaving
     5,770 MiB free -- comfortably enough for a small quantised model. That question is settled.
  2. THERE IS NO INFERENCE STACK ON THIS MACHINE. No Ollama, no torch, no transformers, no
     llama.cpp. Adding one is a multi-gigabyte install, and it is the user's machine.

But the deciding argument is neither of those. **This stage's entire job is to report numbers the
agent already computed.** That is exactly where a language model is most likely to be wrong and
least excusable, and this project's standing rule is no hallucination. So the explanation is
generated deterministically from the decision itself, and -- the part that matters --

    EVERY CLAIM AN EXPLANATION MAKES IS VERIFIED BY RE-RUNNING THE AGENT.

If the explanation says "this hour would flip to free cooling if the limit were 0.42 C higher",
`verify()` moves the limit by 0.42 C, re-plans, and checks that it actually flips. An explanation
that cannot be reproduced is a bug, not prose. A language model can be layered on top later to
rephrase this brief into friendlier English, with a checker that rejects any number not present in
the brief -- the factual content stays here, where it is testable.

--------------------------------------------------------------------------------------------
WHAT MAKES THIS MORE THAN A TEMPLATE
--------------------------------------------------------------------------------------------
The interesting explanations are the ones only a PLANNER can give:

  * "SAFE, BUT MECHANICAL ANYWAY." An hour can pass all three gates and still run chillers,
    because the switch budget is spent or the minimum dwell has not elapsed. A thermostat cannot
    produce that sentence -- it has no plan to be constrained by. Which of the two bound is
    determined by re-planning with each relaxed in turn, not by guessing.
  * "REFUSED." The solver declines to answer because a building sits on the source-to-intake path.
    That is a different sentence from "too hot", and conflating them would hide the guard.
  * "WHICH GATE, AND BY HOW MUCH." Dry-bulb, dew point and contamination are separate limits; the
    explanation names the binding one and the exact distance to it.
  * "WHAT THE MARGIN IS MADE OF." Level term, group-conditional shape term, plume term -- each
    with its provenance, so a reader can see the bound is measured rather than chosen.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IA = os.path.dirname(HERE)
DEMO = os.path.join(IA, "demo")

sys.path.insert(0, HERE)
from agent import MODE_FREE, MODE_MECH, banner, plan, reactive_incumbent, say   # noqa: E402

GATE_DRY, GATE_DEW, GATE_AQ, GATE_REFUSED = "dry-bulb", "dew point", "air quality", "refusal"
SCHED_BUDGET, SCHED_DWELL = "switch budget", "minimum dwell"


def gates_for_hour(st, h, cfg):
    """(passes, distance to each limit) for the three gates plus refusal, at one hour."""
    out = {}
    out[GATE_DRY] = (st["ub_dry"][h] <= cfg["limit_c"], cfg["limit_c"] - st["ub_dry"][h])
    if cfg["dewpoint_limit_c"] is None:
        out[GATE_DEW] = (True, float("inf"))
    else:
        out[GATE_DEW] = (st["ub_dp"][h] <= cfg["dewpoint_limit_c"],
                         cfg["dewpoint_limit_c"] - st["ub_dp"][h])
    if cfg["aq_limit_idx"] is None or st["aq"] is None:
        out[GATE_AQ] = (True, float("inf"))
    else:
        out[GATE_AQ] = (st["aq"][h] <= cfg["aq_limit_idx"],
                        cfg["aq_limit_idx"] - st["aq"][h])
    out[GATE_REFUSED] = (not st["refused"][h], float("nan"))
    return out


def flip_distance(st, h, cfg, gate):
    """How far the binding limit would have to move for this hour to pass that gate."""
    if gate == GATE_DRY:
        return st["ub_dry"][h] - cfg["limit_c"]
    if gate == GATE_DEW:
        return st["ub_dp"][h] - cfg["dewpoint_limit_c"]
    if gate == GATE_AQ:
        return st["aq"][h] - cfg["aq_limit_idx"]
    return float("nan")


def explain_hour(st, h, cfg, modes, safe):
    """One hour, one reason, with the binding constraint named and a checkable counterfactual."""
    g = gates_for_hour(st, h, cfg)
    free = modes[h] == MODE_FREE
    e = {"hour": st["hours"][h], "index": h, "mode": "FREE-COOLING" if free else "MECHANICAL",
         "safe": bool(safe[h]),
         "ambient_c": round(float(st["temp"][h]), 3),
         "dewpoint_c": round(float(st["dew"][h]), 3),
         "plume_rise_c": round(float(st["rise"][h]), 4),
         "bound_c": round(float(st["ub_dry"][h]), 4),
         "limit_c": cfg["limit_c"],
         "margin_total_c": round(float(st["marg_total"][h]), 4),
         "margin_parts": {
             "level": round(float(st["marg_level"]), 4),
             "shape_group_conditional": round(float(st["marg_shape"][h]), 4),
             "plume_from_ensemble_spread": round(float(st["marg_plume"][h]), 5)},
         "actual_intake_c": round(float(st["truth"][h]), 4)}

    if free:
        e["binding"] = None
        e["why"] = ("Free cooling. The 90 %%-nominal upper bound on intake air is %.3f C, which is "
                    "%.3f C under the %.1f C plant limit. That bound is the forecast plus a margin "
                    "of %.3f C, and the margin is measured, not chosen: %.3f C of group-conditional "
                    "forecast error for this hour of day, plus %.4f C for how much the plume could "
                    "move if the wind direction is off by the amount FortyGuard's forecast is "
                    "actually off by."
                    % (st["ub_dry"][h], cfg["limit_c"] - st["ub_dry"][h], cfg["limit_c"],
                       st["marg_total"][h], st["marg_shape"][h], st["marg_plume"][h]))
        if st["truth"][h] > cfg["limit_c"]:
            e["why"] += (" *** THIS WAS WRONG: the intake actually reached %.3f C, above the limit. "
                         "The bound failed here, and it is counted as a breach rather than "
                         "explained away. ***" % st["truth"][h])
        return e

    # ---- not free. Was it UNSAFE, or was it safe and the SCHEDULE could not afford it?
    if not safe[h]:
        if st["refused"][h]:
            e["binding"] = GATE_REFUSED
            e["why"] = ("Mechanical, and the reason is a REFUSAL rather than a temperature. At this "
                        "wind bearing a building sits between the condensers and the air intake. "
                        "The dispersion model has no representation of a building standing in the "
                        "flow, so any number it produced here would be meaningless. The agent "
                        "declines to certify the hour instead of returning a figure it cannot "
                        "stand behind.")
            return e
        failed = [k for k in (GATE_DRY, GATE_DEW, GATE_AQ) if not g[k][0]]
        # the binding gate is the one that is furthest past its limit in its own units
        binding = max(failed, key=lambda k: flip_distance(st, h, cfg, k)) if failed else GATE_DRY
        e["binding"] = binding
        d = flip_distance(st, h, cfg, binding)
        # FULL PRECISION. Rounding this to 4 dp made `limit + flip_needs` land a hair BELOW the
        # bound, so verify() reported 328 false failures -- the identical mistake that broke the
        # browser's decisions the same day (PLAN 8k.4). A number a comparison depends on is not a
        # display number. Rounding happens in the sentence below, never in the field.
        e["flip_needs"] = float(d)
        if binding == GATE_DRY:
            e["why"] = ("Mechanical. The upper bound on intake air is %.3f C against a %.1f C "
                        "limit, so it fails by %.3f C. It would take a limit %.3f C higher, or a "
                        "bound %.3f C tighter, to change this hour."
                        % (st["ub_dry"][h], cfg["limit_c"], d, d, d))
        elif binding == GATE_DEW:
            e["why"] = ("Mechanical, and TEMPERATURE IS NOT THE REASON -- the dry-bulb bound of "
                        "%.3f C would have passed. The outside air is too HUMID: the dew-point "
                        "bound is %.2f C against a %.1f C maximum, failing by %.2f C. Cool but damp "
                        "air condenses on cold surfaces inside the hall, which is why real "
                        "economizers gate on humidity and not on temperature alone."
                        % (st["ub_dry"][h], st["ub_dp"][h], cfg["dewpoint_limit_c"], d))
        else:
            e["why"] = ("Mechanical, and neither temperature nor humidity is the reason. The "
                        "outside air is too DIRTY: PM2.5 index %.1f against a %.1f limit. Opening "
                        "a damper pulls that air into the hall, which is the documented reason "
                        "operators avoid free cooling at all."
                        % (st["aq"][h], cfg["aq_limit_idx"]))
        if len(failed) > 1:
            e["also_failing"] = [k for k in failed if k != binding]
        return e

    # ---- SAFE BUT MECHANICAL: the planner declined. Which constraint?  Determined by re-planning.
    relaxed_budget, _, _ = plan(safe, cfg["switch_budget"] + 2, cfg["min_dwell_h"])
    relaxed_dwell, _, _ = plan(safe, cfg["switch_budget"], 1)
    by_budget = relaxed_budget[h] == MODE_FREE
    by_dwell = relaxed_dwell[h] == MODE_FREE
    e["binding"] = (SCHED_BUDGET if by_budget and not by_dwell else
                    SCHED_DWELL if by_dwell and not by_budget else
                    SCHED_BUDGET if by_budget else None)
    e["would_flip_with_more_switches"] = bool(by_budget)
    e["would_flip_with_shorter_dwell"] = bool(by_dwell)
    e["why"] = ("Mechanical EVEN THOUGH THIS HOUR IS SAFE. Every gate passes -- the bound is "
                "%.3f C against a %.1f C limit. The schedule is what forbids it: %s. This is the "
                "one explanation a thermostat cannot give, because a thermostat has no plan to be "
                "constrained by. It is also why the decision is a schedule and not a comparison: "
                "spending a mode change here would cost a better one later."
                % (st["ub_dry"][h], cfg["limit_c"],
                   "the switch budget of %d changes per day is already committed elsewhere"
                   % cfg["switch_budget"] if by_budget else
                   ("the plant must hold its current mode for %d h before changing again"
                    % cfg["min_dwell_h"]) if by_dwell else
                   "no relaxation of either the switch budget or the dwell would free it, so the "
                   "surrounding hours are worth more"))
    return e


def explain_schedule(st, cfg):
    """Per-hour explanations plus a day-level summary that names what drove the day."""
    safe = st["safe"]
    modes, free_h, sw = plan(safe, cfg["switch_budget"], cfg["min_dwell_h"])
    imodes, ifree, isw, iover = reactive_incumbent(st["safe_inc"], cfg["switch_budget"],
                                                  cfg["min_dwell_h"])
    rows = [explain_hour(st, h, cfg, modes, safe) for h in range(len(safe))]
    breaches = [r for r in rows if r["mode"] == "FREE-COOLING"
                and r["actual_intake_c"] > cfg["limit_c"]]
    safe_but_mech = [r for r in rows if r["mode"] == "MECHANICAL" and r["safe"]]
    by_binding = {}
    for r in rows:
        if r["binding"]:
            by_binding[r["binding"]] = by_binding.get(r["binding"], 0) + 1
    ibreach = int(sum(1 for h in range(len(safe))
                      if imodes[h] == MODE_FREE and st["truth"][h] > cfg["limit_c"]))
    summary = {
        "day": st["day"], "case": st["case"],
        "agent_free_h": free_h, "agent_switches": sw,
        "incumbent_free_h": ifree, "incumbent_switches": isw,
        "incumbent_broke_its_own_switch_budget": iover,
        "agent_breach_h": len(breaches), "incumbent_breach_h": ibreach,
        "safe_but_mechanical_h": len(safe_but_mech),
        "hours_by_binding_constraint": by_binding,
        "refused_h": int(sum(1 for r in rows if r["binding"] == GATE_REFUSED)),
    }
    lead = ("The agent ran free cooling for %d of %d hours with %d mode change%s."
            % (free_h, len(safe), sw, "" if sw == 1 else "s"))
    if ifree > free_h:
        lead += (" The reactive incumbent took %d hours -- %d more -- but declared %d unsafe hour%s "
                 "against the agent's %d."
                 % (ifree, ifree - free_h, ibreach, "" if ibreach == 1 else "s", len(breaches)))
    elif free_h > ifree:
        lead += (" That is %d more than the reactive incumbent, at %d unsafe hour%s against its %d."
                 % (free_h - ifree, len(breaches), "" if len(breaches) == 1 else "s", ibreach))
    if iover:
        lead += (" The incumbent had to break its own switch budget %d time%s to stay safe; the "
                 "agent never did." % (iover, "" if iover == 1 else "s"))
    if safe_but_mech:
        lead += (" %d hour%s safe but still ran chillers, because the schedule could not "
                 "afford them." % (len(safe_but_mech),
                                   " was" if len(safe_but_mech) == 1 else "s were"))
    summary["narrative"] = lead
    return {"summary": summary, "hours": rows, "modes": "".join(str(m) for m in modes),
            "incumbent_modes": "".join(str(m) for m in imodes)}


def verify(st, cfg, expl):
    """RE-RUN THE AGENT TO CHECK EVERY CLAIM. An explanation that cannot be reproduced is a bug.

    Three families of claim are checkable, and all three are checked:
      * a dry-bulb / dew-point / air-quality flip distance -> move that limit by it and re-decide
      * "would flip with more switches" / "with a shorter dwell" -> re-plan and look
      * "safe" -> recompute the gates independently of the explanation text
    """
    fails = []
    safe = st["safe"]
    modes, _, _ = plan(safe, cfg["switch_budget"], cfg["min_dwell_h"])

    for r in expl["hours"]:
        h = r["index"]
        # 1. the reported mode must match a fresh plan
        if (modes[h] == MODE_FREE) != (r["mode"] == "FREE-COOLING"):
            fails.append("h%02d mode disagrees with a fresh plan" % h)
        # 2. a claimed flip distance must actually flip the gate when applied
        if r.get("flip_needs") is not None and r["binding"] in (GATE_DRY, GATE_DEW, GATE_AQ):
            d = r["flip_needs"]
            c2 = dict(cfg)
            key = {GATE_DRY: "limit_c", GATE_DEW: "dewpoint_limit_c",
                   GATE_AQ: "aq_limit_idx"}[r["binding"]]
            c2[key] = cfg[key] + d + 1e-6
            g2 = gates_for_hour(st, h, c2)
            if not g2[r["binding"]][0]:
                fails.append("h%02d claimed flip of %+.4f on %s did NOT open that gate"
                             % (h, d, r["binding"]))
            # and a hair LESS must NOT open it -- otherwise the distance is not tight
            c3 = dict(cfg); c3[key] = cfg[key] + d - 1e-3
            if gates_for_hour(st, h, c3)[r["binding"]][0]:
                fails.append("h%02d claimed flip distance on %s is not tight"
                             % (h, r["binding"]))
        # 3. scheduling counterfactuals must reproduce
        if r.get("would_flip_with_more_switches"):
            m2, _, _ = plan(safe, cfg["switch_budget"] + 2, cfg["min_dwell_h"])
            if m2[h] != MODE_FREE:
                fails.append("h%02d claimed more switches would free it; re-plan says no" % h)
        if r.get("would_flip_with_shorter_dwell"):
            m3, _, _ = plan(safe, cfg["switch_budget"], 1)
            if m3[h] != MODE_FREE:
                fails.append("h%02d claimed a shorter dwell would free it; re-plan says no" % h)
        # 4. a "safe" claim must survive an independent recomputation of the gates
        g = gates_for_hour(st, h, cfg)
        indep = all(g[k][0] for k in (GATE_DRY, GATE_DEW, GATE_AQ, GATE_REFUSED))
        if indep != r["safe"]:
            fails.append("h%02d 'safe' claim disagrees with a recomputation of the gates" % h)
    return fails


# ============================================================================
def state_from_trace(trace, case, cfg):
    """Rebuild the per-hour decision state from the shipped trace -- the same arrays the browser
    uses, so an explanation describes the decision the demo displays."""
    ds = trace["cases"]["day_series"][case]
    N, skill = cfg["notice_h"], cfg["skill"]
    s = 1.0 - skill
    H = len(ds["hours"])
    bank = cfg["bank_mode"]
    rise = np.array(ds["rise_c_" + bank], dtype=float)
    rise_t = np.array(ds.get("rise_true_c_" + bank, ds["rise_c_" + bank]), dtype=float)
    pm = np.array(ds.get("plume_margin_c_" + bank, [0.0] * H), dtype=float)
    rp = np.array(ds["r_prime|%d" % N], dtype=float)
    md = np.array(ds["margin_dry|%d" % N], dtype=float)
    rdp = np.array(ds["rdp_prime|%d" % N], dtype=float)
    mdp = np.array(ds["margin_dp|%d" % N], dtype=float)
    isrc = np.array(ds["incumbent_src|%d" % N], dtype=float)
    idp = np.array(ds["incumbent_dp_src|%d" % N], dtype=float)
    temp = np.array(ds["temp_c"], dtype=float)
    dew = np.array(ds["dewpoint_c"], dtype=float)
    # THE UNANCHORED LEVEL TERM. `off` is the day's MEASURED FortyGuard offset -- an input error the
    # agent inherits -- and `lvl` is the leave-one-out conformal margin that bounds it. Both are read
    # from the table agent.py ships, and `cfg["offset_day"]` names which measured day applies.
    #
    # This block used to take max(|mean_d|) over every pair and add NO level margin, which is the
    # same improvisation demo/index.html was making, and neither matched the agent: one constant
    # offset is gotcha #48's oracle, and the missing margin left the bound short in the unsafe
    # direction. The two now read the same shipped numbers.
    off, lvl = 0.0, 0.0
    if cfg["anchor"] == "none":
        offs = trace["cases"].get("fg_offsets") or []
        if not offs:
            raise KeyError("trace has no cases.fg_offsets -- re-run `python agent.py run`. "
                           "An unanchored bound cannot be formed without the measured level table.")
        want = cfg.get("offset_day")
        row = next((r for r in offs if r["date"] == want), None) if want else offs[0]
        if row is None:
            raise KeyError("no measured FortyGuard offset for %r; have %s"
                           % (want, [r["date"] for r in offs]))
        off, lvl = float(row["mean_d"]), float(row["level_margin_c"])
    ub_dry = (temp - off - s * rp) + lvl + s * md + rise + pm
    # `off` is a DRY-BULB offset (mean_d is measured on FortyGuard's heatmap) and is deliberately
    # NOT applied here: no measured FortyGuard dew-point offset exists. agent.py's sweep does the
    # same, and the browser was corrected to match -- it had been subtracting it, which closed the
    # dew-point gate on 1,541 of 20,160 configurations.
    ub_dp = (dew - s * rdp) + lvl + s * mdp
    ub_inc = isrc + md
    ub_inc_dp = idp + mdp
    refused = [bool(x) for x in ds["refused_" + bank]]
    aq = np.array(ds["aq_idx"], dtype=float) if ds.get("aq_idx") else None

    st = {"case": case, "day": ds["day"], "hours": ds["hours"], "temp": temp, "dew": dew,
          "rise": rise, "truth": temp + rise_t, "refused": refused, "aq": aq,
          "ub_dry": ub_dry, "ub_dp": ub_dp,
          # `marg_level` is the conformal LEVEL MARGIN, not the offset. It used to hold `off`, which
          # made the explanation call an input error a margin -- they point in opposite directions.
          "marg_total": lvl + s * md + pm, "marg_shape": s * md, "marg_plume": pm,
          "marg_level": lvl, "level_offset": off,
          "ub_inc": ub_inc}
    g_dry = ub_dry <= cfg["limit_c"]
    g_dew = (np.ones(H, bool) if cfg["dewpoint_limit_c"] is None
             else ub_dp <= cfg["dewpoint_limit_c"])
    g_aq = (np.ones(H, bool) if (cfg["aq_limit_idx"] is None or aq is None)
            else aq <= cfg["aq_limit_idx"])
    st["safe"] = g_dry & g_dew & g_aq & (~np.array(refused))
    si = ub_inc <= cfg["limit_c"]
    if cfg["dewpoint_limit_c"] is not None:
        si = si & (ub_inc_dp <= cfg["dewpoint_limit_c"])
    if cfg["aq_limit_idx"] is not None and aq is not None:
        si = si & g_aq
    st["safe_inc"] = si
    return st


BASE_CFG = {"limit_c": 18.0, "notice_h": 3, "anchor": "sensor", "skill": 0.5,
            "bank_mode": "longest", "switch_budget": 2, "min_dwell_h": 3,
            "dewpoint_limit_c": 15.0, "aq_limit_idx": None,
            # Which MEASURED FortyGuard day supplies the level offset when anchor is "none".
            # `None` means the first shipped one; agent.py sweeps all four as separate scenarios,
            # so this names a point in that sweep rather than choosing a value.
            "offset_day": None}


def main():
    banner("EXPLAIN   stage 7 of the loop: say WHY, and CHECK it.  [no API calls]")
    tp = os.path.join(DEMO, "trace.json")
    if not os.path.exists(tp):
        say("   trace.json missing -- run `python agent.py run` first.")
        return 2
    trace = json.load(open(tp, encoding="utf-8"))

    say("\n   Warp ensemble peak VRAM measured at 371 MiB of 6,141 -- 5,770 MiB free, so a local")
    say("   model would FIT. It is not used, and the reason is not memory: this stage reports")
    say("   numbers the agent already computed, which is where a language model is most likely to")
    say("   be wrong and least excusable. Every claim below is instead VERIFIED by re-running the")
    say("   agent, so an explanation that cannot be reproduced fails the build.")

    out, total_fails, total_claims = {}, [], 0
    cases = [c["name"] for c in trace["cases"]["cases"] if c["day"]]
    # explain every case under several configurations, not one flattering pick
    configs = [dict(BASE_CFG),
               dict(BASE_CFG, limit_c=21.0),
               dict(BASE_CFG, notice_h=6, skill=0.0),
               dict(BASE_CFG, anchor="none"),
               dict(BASE_CFG, bank_mode="facing"),
               dict(BASE_CFG, switch_budget=1, min_dwell_h=3),
               dict(BASE_CFG, dewpoint_limit_c=None),
               dict(BASE_CFG, aq_limit_idx=73.5)]
    for case in cases:
        out[case] = []
        for ci, cfg in enumerate(configs):
            st = state_from_trace(trace, case, cfg)
            ex = explain_schedule(st, cfg)
            fails = verify(st, cfg, ex)
            total_claims += len(ex["hours"])
            total_fails += ["%s/cfg%d: %s" % (case, ci, f) for f in fails]
            out[case].append({"config": cfg, **ex})

    say("\n   %d case days x %d configurations = %d schedules, %d hour-explanations, all verified"
        % (len(cases), len(configs), len(cases) * len(configs), total_claims))
    if total_fails:
        say("\n   *** %d VERIFICATION FAILURES ***" % len(total_fails))
        for f in total_fails[:12]:
            say("      %s" % f)
    else:
        say("   VERIFICATION: 0 failures -- every mode, every flip distance, every scheduling")
        say("   counterfactual and every safety claim reproduced on a fresh run of the agent.")

    # show the interesting ones rather than the first ones
    say("\n   ---- WORKED EXAMPLES, chosen because each is a different KIND of reason ----")
    shown = set()
    for case in out:
        for blk in out[case]:
            for r in blk["hours"]:
                b = r["binding"]
                if b in shown or b is None:
                    continue
                shown.add(b)
                say("\n   [%s]  %s %s:00  (%s, limit %.1f C)"
                    % (b, case, r["hour"], blk["config"]["bank_mode"], blk["config"]["limit_c"]))
                say("      %s" % r["why"])
    for case in out:
        blk = out[case][0]
        if blk["summary"]["safe_but_mechanical_h"]:
            say("\n   DAY-LEVEL NARRATIVE (%s):" % case)
            say("      %s" % blk["summary"]["narrative"])
            break

    p = os.path.join(DEMO, "explanations.json")
    json.dump({"generated_by": "INTAKE-ARBITER/src/explain.py", "api_calls_made": 0,
               "warp_peak_vram_mib": 371, "gpu_total_mib": 6141,
               "local_model_used": False,
               "why_no_local_model": "no inference stack installed (no Ollama/torch/transformers/"
                                     "llama.cpp), and this stage reports numbers the agent already "
                                     "computed -- deterministic generation plus verification is "
                                     "safer than generation plus hope",
               "verification": {"hour_explanations": total_claims,
                                "failures": len(total_fails), "failure_detail": total_fails[:50]},
               "cases": out},
              open(p, "w", encoding="utf-8"), allow_nan=False, default=float)
    say("\n   wrote %s (%.1f KB)" % (p, os.path.getsize(p) / 1024.0))
    say("\n" + "=" * 78)
    say("EXPLAIN %s" % ("PASSED" if not total_fails else "FAILED -- explanations are not trustworthy"))
    say("=" * 78)
    return 0 if not total_fails else 1


if __name__ == "__main__":
    sys.exit(main())
