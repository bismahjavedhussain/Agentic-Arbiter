"""THE API SPEND LEDGER, RECONSTRUCTED FROM ARTEFACTS -- zero API calls, no key read.

WHY THIS EXISTS
---------------
The submission has to state how much of the FortyGuard plan was used. Writing that number into a
document by hand is how it goes stale, and it already did: HANDOFF 12.2 said "42,200 = 10 calls =
2.11 %" while the collector's own manifest recorded a meter of 1,945,140 -- three more calls than
the prose. So the figure is DERIVED here, from meter readings the test scripts saved next to their
results, and `INTAKE-ARBITER/src/audit.py` re-reads this file's output.

HOW IT KNOWS WHAT IT KNOWS
--------------------------
Every paid script in `testing/` records the usage endpoint before and after its call, because that
endpoint is free. Those readings are the ledger. Three properties make them strong evidence:

  * A credit meter only ever DECREASES inside a billing cycle, so the readings sort themselves into
    a timeline without needing trustworthy timestamps.
  * The heatmap price was measured at exactly 4,220 by differencing the meter repeatedly, so
    (issued - remaining) / 4,220 must come out a whole number. If it does not, either a
    differently-priced endpoint was called or a reading is wrong -- and the script says so instead
    of rounding.
  * Calls with a saved before/after PAIR are individually attributable. Calls visible only as a gap
    between two readings are counted but not named, and are reported separately as such. That
    distinction is the whole point: "11 of 13 calls returned zero tiles" is only worth stating if
    the 11 is arithmetic rather than recollection.

TWO CYCLES, AND WHY THE FIRST ONE IS FREE
-----------------------------------------
The pre-hackathon key's billing cycle closed 2026-07-19 and its meter FROZE: about 125 calls on
2026-08-11..17 all report the same `cycle_remaining` before and after. Those calls are real and
their data is used, but they are not chargeable and are reported separately -- counting them as
spend would overstate usage, and counting their data as unpaid-for would understate the evidence.

USAGE
-----
    python testing/api_usage_ledger.py            # prints the ledger
    python testing/api_usage_ledger.py --json     # also writes testing/results/api_usage.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The plan, from the usage endpoint's own `credit_summary` (HANDOFF 12.2). Stated here because the
# issued total is a property of the plan, not of any call we made.
PLAN_NAME = "Hackathon"
PLAN_ISSUED = 2_000_000
# MEASURED by differencing the meter, repeatedly. It used to be defined here, and on 2026-08-21 the
# collector became a second consumer (it now costs its own retries against the billing partition),
# so it moved to `common.py` and this module imports it. One measured price, one definition --
# gotcha #12, and `audit.py` check 4 is the standing scar from the last time that was not true.
sys.path.insert(0, HERE)
from common import HEATMAP_CREDITS          # noqa: E402
FROZEN_CYCLE_REMAINING = 180_980  # the pre-hackathon key, meter closed 2026-07-19

# The fields different scripts used for the same thing. Kept as an explicit list rather than a
# regex so a new spelling shows up as "unrecognised" instead of being silently missed.
BEFORE_KEYS = ("credits_before", "credits_last_before")
AFTER_KEYS = ("credits_after", "credits_last_after")
NESTED_BEFORE = ("meter_before",)
NESTED_AFTER = ("meter_after",)
NESTED_FIELD = ("cycle_remaining", "remaining", "cycle_remaining_credits")


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def observations():
    """Every (before, after, source, label) meter observation saved anywhere in testing/results."""
    out = []
    for base, _, files in os.walk(os.path.join(HERE, "results")):
        for nm in files:
            if not nm.endswith(".json"):
                continue
            path = os.path.join(base, nm)
            try:
                doc = json.load(open(path, encoding="utf-8"))
            except (ValueError, OSError):
                continue

            def visit(node, trail):
                if isinstance(node, dict):
                    b = a = None
                    for k in BEFORE_KEYS:
                        if isinstance(node.get(k), int):
                            b = node[k]
                    for k in AFTER_KEYS:
                        if isinstance(node.get(k), int):
                            a = node[k]
                    for k in NESTED_BEFORE:
                        sub = node.get(k)
                        if isinstance(sub, dict):
                            for f in NESTED_FIELD:
                                if isinstance(sub.get(f), int):
                                    b = sub[f]
                                    break
                    for k in NESTED_AFTER:
                        sub = node.get(k)
                        if isinstance(sub, dict):
                            for f in NESTED_FIELD:
                                if isinstance(sub.get(f), int):
                                    a = sub[f]
                                    break
                    if b is not None and a is not None:
                        out.append({
                            "source": rel(path),
                            "at": trail or "(root)",
                            "before": b,
                            "after": a,
                            "spent": b - a,
                            "test": node.get("test") or node.get("name") or "",
                            "activity_id": node.get("activity_id"),
                            # Four spellings for "how many tiles came back", one per script that
                            # was written before the next one existed. Listed, not guessed at.
                            "tiles": next((node[k] for k in ("tiles_returned", "features_returned",
                                                             "n_features", "forecast_n")
                                           if isinstance(node.get(k), int)), None),
                        })
                    for k, v in node.items():
                        visit(v, trail + "/" + str(k))
                elif isinstance(node, list):
                    for i, v in enumerate(node):
                        visit(v, trail + "/%d" % i)

            visit(doc, "")
    return out


def live_run_windows():
    """Per-CALL evidence from `live.py` runs: what each window actually returned.

    `live_spend.json` records one entry per paid live run, and inside it one record per live call
    with its `class` (`ok` / `completed_but_empty` / ...) and tile count. That is individual
    attribution for calls the top-level meter pair would otherwise lump into "unattributable" --
    the first 12-hour run made 11 calls of which 3 returned a field and 8 returned `completed` with
    no data, and all 8 were BILLED. Reading it turns 11 unnamed calls into 11 named ones.

    Returns (n_with_data, n_empty, n_other, detail).
    """
    path = os.path.join(HERE, "results", "live_spend.json")
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError):
        return 0, 0, 0, []
    # 🔴 ONLY SOME OUTCOMES ARE BILLED, AND THE PARTITION CHECK CAUGHT ME CONFLATING THEM.
    # Established behaviour, from the meter rather than from the docs:
    #   ok                    -> BILLED 4,220
    #   completed_but_empty   -> BILLED 4,220  (the vendor charges for a complete-but-empty field)
    #   terminal_failed       -> free
    #   stalled_in_processing -> free
    #   submit_rejected       -> free (no job was ever created)
    # Counting the free ones against a BILLED-call total over-counted by one per rejection and
    # broke `audit.py` check 9. They are reported separately as attempted-but-unbilled, which is
    # information worth having: a rejection is a vendor signal even though it costs nothing.
    BILLED = {"ok", "completed_but_empty"}
    data = empty = unbilled = 0
    detail = []
    for run in doc.get("runs", []):
        d = e = u = 0
        for w in run.get("windows", []):
            c = w.get("class")
            if c == "ok":
                d += 1
            elif c == "completed_but_empty":
                e += 1
            elif c not in BILLED:
                u += 1
        data += d
        empty += e
        unbilled += u
        detail.append("%s h+%s: %d returned a field, %d `completed` with no data%s"
                      % (run.get("metro"), run.get("horizon_h"), d, e,
                         ", %d attempted but unbilled" % u if u else ""))
    return data, empty, unbilled, detail


# Endpoints on this plan whose price is NOT the heatmap price. Measured, like everything else:
# `env_params` at 2,900 came from `activity_breakdown` and was confirmed by differencing the meter
# across DIAG-65 (1,662,400 -> 1,659,500).
OTHER_PRICES = {"env_params": 2_900}


def non_heatmap_spend():
    """Billed calls to endpoints that are not `/v1/heatmap`, read from their saved result files.

    Read rather than assumed, and named individually, because the whole point of the reconciliation
    is that the arithmetic closes without anyone having to remember what was called. A call is
    counted here only if its own result file records a meter pair that actually moved.
    """
    total, calls, detail = 0, 0, []
    here = os.path.join(HERE, "results")
    for fn in sorted(os.listdir(here)) if os.path.isdir(here) else []:
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(here, fn), encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(d, dict):
            continue
        ep = d.get("endpoint")
        if ep not in OTHER_PRICES:
            continue
        # TWO SHAPES, because two writers produce them: a one-shot diagnostic saves a single
        # `credits_spent` at the top level, while `live.py` APPENDS one entry per call to a `runs`
        # list. Reading only the first shape is how the live agent's environmental spend would have
        # gone unrecorded -- gotcha #103, which is exactly this mismatch one endpoint earlier.
        if isinstance(d.get("runs"), list):
            for run in d["runs"]:
                spent = run.get("credits")
                if isinstance(spent, int) and spent > 0:
                    total += spent
                    calls += 1
                    detail.append((fn, ep, spent))
            continue
        spent = d.get("credits_spent")
        if not isinstance(spent, int) or spent <= 0:
            continue
        total += spent
        calls += 1
        detail.append((fn, ep, spent))
    return total, calls, detail


def collector_zero_tile_days():
    """The N-26 collector's own record of which days returned `completed` with no features.

    Read rather than assumed. The manifest gained a per-day `forecast_attempts` counter on
    2026-08-19, so days before that record ONE known-failed call each and the true count may be
    higher -- which is why the caller reports these as a floor.

    2026-08-21: the collector now writes a PER-ATTEMPT log carrying each attempt's vendor class and
    whether it was billed, so from that date the count is exact rather than a floor. Three counting
    regimes therefore coexist in one manifest, and collapsing them would be the same mistake the
    ledger was written to fix:
        pre-08-19   no counter          -> 1 known-failed call, a floor
        08-19..21   an attempt integer  -> every attempt assumed billed (true on those days)
        08-21+      a per-attempt log   -> exactly the billed ones, counted
    """
    path = os.path.join(HERE, "results", "n26_manifest.json")
    try:
        m = json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError):
        return {}, 0
    out, total = {}, 0
    for dk, day in sorted(m.get("days", {}).items()):
        err = day.get("forecast_error")
        if day.get("forecast_done") or not err:
            continue
        # A lead-band skip is not a call: the collector refused to spend, so nothing was billed.
        if "comparability floor" in err or "window already started" in err:
            continue
        log = [r for r in (day.get("forecast_attempt_log") or [])
               if r.get("leg") == "forecast"]
        if log:
            # EXACT. Only the billed ones moved the meter, and the free ones are named so the
            # difference is visible rather than absorbed.
            n = sum(1 for r in log if r.get("billed"))
            free = len(log) - n
            out[dk] = ("%d billed attempt%s%s -- %s"
                       % (n, "" if n == 1 else "s",
                          ", %d free (%s)" % (free, ", ".join(sorted(
                              set(r.get("class", "?") for r in log if not r.get("billed")))))
                          if free else "", err[:52]))
        else:
            n = day.get("forecast_attempts", 1)
            out[dk] = "%d attempt%s, all zero tiles -- %s" % (n, "" if n == 1 else "s", err[:52])
        total += n
    return out, total


def main():
    obs = observations()
    frozen = [o for o in obs if o["before"] == o["after"] == FROZEN_CYCLE_REMAINING]
    billed = [o for o in obs if o["spent"] > 0]
    other = [o for o in obs if o not in frozen and o not in billed]

    # A meter only falls, so ordering by `before` descending IS chronological order within a cycle.
    billed.sort(key=lambda o: -o["before"])
    # Only a saved tile/feature count classifies a call. `n26_manifest.json` carries a meter pair
    # for the LAST call the collector made, but no tile count at that node, so it must not be read
    # as either a success or a failure here -- the collector's own per-day record classifies it.
    tile_stamped = [o for o in billed if isinstance(o["tiles"], int)]
    collector_failures, collector_zero = collector_zero_tile_days()
    live_data, live_empty, live_unbilled, live_detail = live_run_windows()

    print("=" * 90)
    print("FORTYGUARD API SPEND -- reconstructed from saved meter readings. Zero API calls.")
    print("=" * 90)
    print("plan %-12s issued %s credits    heatmap price %s (measured)"
          % (PLAN_NAME, format(PLAN_ISSUED, ","), format(HEATMAP_CREDITS, ",")))
    print()

    if not billed:
        print("NO BILLED OBSERVATIONS FOUND -- nothing to reconcile.")
        return 1

    # 🔴 THE AUTHORITY IS THE LOWEST READING EVER RECORDED IN THIS CYCLE, BILLED OR NOT.
    # This said `min(o["after"] for o in billed)` and it silently lost three calls the same day it
    # was written. `n26_manifest.json` keeps only the LAST meter pair it saw, so when a later
    # UNBILLED call (the 2026-08-20 stall, which cost 0) overwrote that slot, the manifest's
    # observation stopped satisfying `spent > 0`, dropped out of `billed`, and the reported total
    # fell from 54,860 back to 42,200 -- the exact stale figure this script exists to prevent.
    # A meter reading is evidence of cumulative spend whether or not the call that took it was
    # itself billed. Never derive a running total from a mutable single-slot field.
    cycle = [o for o in obs if o["after"] != FROZEN_CYCLE_REMAINING and o["after"] < PLAN_ISSUED]
    lowest = min(o["after"] for o in cycle) if cycle else min(o["after"] for o in billed)
    used = PLAN_ISSUED - lowest

    # 🔴 THE PLAN IS NO LONGER SINGLE-PRICED, AND THE RECONCILIATION HAD TO LEARN THAT.
    # Until 2026-08-23 every billed call on this plan was a 4,220 heatmap, so `used / 4,220` came
    # out whole and that exactness WAS the proof: a remainder would have meant a differently-priced
    # endpoint or a bad reading. The ledger's own comment said so -- "a single differently-priced
    # env_params call at 2,900 would have made the division fail."
    # DIAG-65 then made exactly that call, deliberately, and the check fired. It was right to. What
    # is wrong is only the ASSUMPTION of a single price, so the non-heatmap spend is subtracted at
    # its own measured price first and the heatmap remainder is still required to be exact. The
    # proof survives: it now says "340,500 = 80 heatmaps + 1 env_params, with nothing left over".
    other_spend, other_calls, other_detail = non_heatmap_spend()
    heatmap_used = used - other_spend
    n_calls, remainder = divmod(heatmap_used, HEATMAP_CREDITS)

    print("1. THE ATTRIBUTABLE CALLS -- a saved before/after pair names the call that made it")
    print("   %-46s %11s %11s %8s %s" % ("source", "before", "after", "spent", "result"))
    for o in billed:
        res = ("%s tiles" % format(o["tiles"], ",")) if isinstance(o["tiles"], int) else "-"
        if o["tiles"] == 0:
            res = "ZERO tiles"
        print("   %-46s %11s %11s %8s %s"
              % (o["source"][:46], format(o["before"], ","), format(o["after"], ","),
                 format(o["spent"], ","), res))
    attributed = sum(o["spent"] for o in billed)
    print("   %-46s %11s %11s %8s" % ("attributed subtotal", "", "", format(attributed, ",")))
    print()

    print("2. THE RECONCILIATION -- the meter is the authority, not the artefact count")
    print("   lowest remaining ever recorded   %s" % format(lowest, ","))
    print("   therefore spent                  %s  =  %s issued - %s remaining"
          % (format(used, ","), format(PLAN_ISSUED, ","), format(lowest, ",")))
    print("   at the measured %s per heatmap    %s calls, remainder %s"
          % (format(HEATMAP_CREDITS, ","), n_calls, remainder))
    if remainder:
        print("   *** NOT A WHOLE NUMBER OF HEATMAP CALLS. Either a differently-priced endpoint")
        print("       was billed (env_params is 2,900) or a reading is wrong. Do not quote a call")
        print("       count until this resolves.")
    unattributed = used - attributed
    n_unattr, rem_unattr = divmod(unattributed, HEATMAP_CREDITS)
    print("   attributed to a saved pair       %s  (%d call%s)"
          % (format(attributed, ","), attributed // HEATMAP_CREDITS,
             "" if attributed // HEATMAP_CREDITS == 1 else "s"))
    print("   visible only as a gap            %s  (%d call%s%s)"
          % (format(unattributed, ","), n_unattr, "" if n_unattr == 1 else "s",
             ", remainder %d" % rem_unattr if rem_unattr else ""))
    print()

    # ---- 3. WHAT THE CALLS BOUGHT, as a FLOOR AND A CEILING rather than one figure.
    # The temptation here is to assume every call not otherwise accounted for was an outage
    # attempt, which would put "83 % of spend bought nothing" on a slide. It is not established:
    # six calls are visible only as gaps between meter readings and nothing saved says what they
    # returned. So the report states what is EVIDENCED (the floor), what is POSSIBLE (the
    # ceiling), and how many calls stand between the two.
    print("3. WHAT THE CALLS BOUGHT -- evidenced, then bounded")
    got_data = [o for o in tile_stamped if o["tiles"] > 0]
    got_zero = [o for o in tile_stamped if o["tiles"] == 0]
    print("   returned a populated field, tile count saved:   %d call%s"
          % (len(got_data), "" if len(got_data) == 1 else "s"))
    for o in got_data:
        print("      %-42s %s tiles" % (os.path.basename(o["source"]), format(o["tiles"], ",")))
    print("   returned `completed` with ZERO features, METER-STAMPED:  %d call%s"
          % (len(got_zero), "" if len(got_zero) == 1 else "s"))
    for o in got_zero:
        print("      %-42s 0 tiles" % os.path.basename(o["source"]))

    # 🔴 ATTEMPTS ARE NOT BILLED CALLS, AND AS OF 2026-08-20 THEY ARE NOT EVEN CLOSE.
    # Until that day every failed request was billed 4,220, so folding the collector's recorded
    # attempt count into the billed-call partition was harmless. Then the vendor started returning
    # `status: failed` and stalling in `Processing`, and BOTH cost nothing -- so the collector now
    # records attempts that never moved the meter. Multiplying attempts by 4,220 over-counted spend
    # by exactly one call the first time this ran after the change. The two quantities are reported
    # side by side and never summed.
    # Live-run windows are attributed per CALL, not per run, so they leave the unattributable
    # bucket entirely. They are not ADDED to the total: the meter already counted them.
    # live_unbilled is deliberately NOT added: those attempts never moved the meter, so they are
    # not among the billed calls this partition covers.
    identified = len(got_data) + len(got_zero) + live_data + live_empty
    unknown = n_calls - identified
    if live_detail:
        print("   from live.py runs, attributed per call:")
        for d in live_detail:
            print("      %s" % d)
        if live_unbilled:
            print("      (%d attempt(s) were rejected or never completed -- FREE, so they are "
                  "not billed calls)" % live_unbilled)
    print("   NOT individually attributable to an artefact:            %d call%s (%s credits)"
          % (unknown, "" if unknown == 1 else "s", format(unknown * HEATMAP_CREDITS, ",")))
    print("      -- gaps between meter readings. The collector's 08-18 and 08-19 attempts predate")
    print("         its per-day attempt counter, so their individual count is not recoverable.")
    print()
    print("   THE COLLECTOR'S OWN FAILURE RECORD -- attempts, which are NOT all billed:")
    for dk, note in sorted(collector_failures.items()):
        print("      %-24s %s" % (dk, note))
    print("      %d recorded attempt(s) across %d day(s). At least one was UNBILLED: the"
          % (collector_zero, len(collector_failures)))
    print("      2026-08-20 stall cost 0 credits, so attempts x 4,220 is NOT a spend figure.")
    print()
    # The floor is what the meter can prove bought nothing; the ceiling assumes every
    # unattributable call also failed. The truth is between, and the gap is named.
    zero_floor = (len(got_zero) + live_empty) * HEATMAP_CREDITS
    zero_ceiling = zero_floor + unknown * HEATMAP_CREDITS
    print("   credits PROVEN to have bought no data:        %s of %s  (%.1f %%)"
          % (format(zero_floor, ","), format(used, ","), 100.0 * zero_floor / used))
    print("   upper bound if every unattributable call failed: %s of %s  (%.1f %%)"
          % (format(zero_ceiling, ","), format(used, ","), 100.0 * zero_ceiling / used))
    print("      The vendor record makes the ceiling far likelier than the floor: 08-18..08-20 the")
    print("      forecast leg failed every single time it was tried.")
    print()

    print("4. THE UNBILLED CYCLE -- real calls, real data, meter frozen, not chargeable")
    print("   %d saved readings all show cycle_remaining %s unchanged before and after"
          % (len(frozen), format(FROZEN_CYCLE_REMAINING, ",")))
    print("   (the pre-hackathon key; its billing cycle closed 2026-07-19)")
    if other:
        print("   %d further reading(s) fit neither pattern:" % len(other))
        for o in other[:6]:
            print("      %s  %s -> %s" % (o["source"], o["before"], o["after"]))
    print()

    print("=" * 90)
    # The headline says the TOTAL, and names the split, because "80 paid calls" while the plan has
    # been charged for 81 is the kind of quiet discrepancy this whole file exists to prevent.
    print("HEADLINE:  %d paid calls   %s credits   %.2f %% of the plan   %s remaining"
          % (n_calls + other_calls, format(used, ","), 100.0 * used / PLAN_ISSUED,
             format(lowest, ",")))
    if other_calls:
        print("           = %d heatmap x %s + %s"
              % (n_calls, format(HEATMAP_CREDITS, ","),
                 " + ".join("%d %s x %s" % (1, e, format(c, ","))
                            for _f, e, c in other_detail)))
    print("=" * 90)

    if "--json" in sys.argv:
        out = {
            "plan": PLAN_NAME,
            "issued": PLAN_ISSUED,
            "heatmap_credits": HEATMAP_CREDITS,
            "remaining": lowest,
            "spent": used,
            # `paid_calls` IS THE TOTAL ACROSS ALL ENDPOINTS, because that is what a reader means
            # by the phrase. It was briefly the heatmap-only count, which made the headline say 80
            # while the plan had actually been charged for 81 calls -- a distinction nobody outside
            # this file would infer. `heatmap_calls` carries the narrower number for the
            # reconciliation that needs it.
            "paid_calls": n_calls + other_calls,
            "heatmap_calls": n_calls,
            "other_endpoint_calls": other_calls,
            "other_endpoint_credits": other_spend,
            "other_endpoint_detail": [{"file": f, "endpoint": e, "credits": c}
                                      for f, e, c in other_detail],
            "total_calls_all_endpoints": n_calls + other_calls,
            "pct_of_plan": round(100.0 * used / PLAN_ISSUED, 4),
            "whole_call_remainder": remainder,
            "attributed_credits": attributed,
            "unattributed_credits": unattributed,
            "calls_returning_data": len(got_data) + live_data,
            "calls_returning_zero_tiles_meter_stamped": len(got_zero) + live_empty,
            "live_run_calls_with_data": live_data,
            "live_run_calls_completed_but_empty": live_empty,
            "live_run_attempts_unbilled": live_unbilled,
            "collector_recorded_failed_attempts": collector_zero,
            # Exported so bump_spend_docs.py can maintain "N attempts across M days" as a pair.
            # It was printed but not exported, so the day count in API-USAGE.md was the one figure
            # in that sentence no tool could refresh -- and it had already drifted to "three".
            "collector_failed_attempt_days": len(collector_failures),
            "collector_attempts_are_not_all_billed": True,
            "calls_not_individually_identified": unknown,
            "credits_that_bought_no_data_floor": zero_floor,
            "credits_that_bought_no_data_ceiling": zero_ceiling,
            "unbilled_frozen_cycle_readings": len(frozen),
            "attributable": [
                {k: o[k] for k in ("source", "before", "after", "spent", "tiles", "activity_id",
                                   "test")}
                for o in billed
            ],
        }
        dst = os.path.join(HERE, "results", "api_usage.json")
        json.dump(out, open(dst, "w", encoding="utf-8"), indent=1)
        print("wrote %s" % rel(dst))

    return 1 if remainder else 0


if __name__ == "__main__":
    sys.exit(main())
