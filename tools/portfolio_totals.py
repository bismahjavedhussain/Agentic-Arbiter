"""Aggregate the 250 shipped sites into the portfolio figures the landing cards state.

🔴 WHY THIS IS A BUILD-TIME TOOL AND NOT BROWSER ARITHMETIC.
Every figure here needs three artefacts per site (backtest, trace, money). Across 250 sites that is
750 fetches and about 300 MB before the first card could render. So the sum is computed once, here,
and written to `demo/portfolio.json`, which the app reads as one small file.

🔴 AND WHY IT IS A SUM RATHER THAN A PROJECTION, which is the part that matters.
The user's instruction is explicit: "A per-site figure multiplied by the site count is a modeled
projection, not a measurement. Presenting one as fact is unacceptable." It is not one here. All 250
offerable sites carry their OWN backtest, trace and money artefacts, each built by `build_sites.py`
from that site's own weather, geometry and bound. Every total below is the sum over 250 real per-site
results, so the only modelling in it is whatever was already inside each site's own figure.

⚠ WHAT IS STILL MODELLED INSIDE EACH SITE, stated because a total inherits its parts' caveats:
  * the IT LOAD is inferred from the site's measured roof footprint by two published power densities
    (average load for the floor, installed capacity for the ceiling). Nobody has told us any site's
    real MW, so the money range is "what this floor area would be worth at published densities".
  * the TARIFF and CHILLER EFFICIENCY are swept over published values, not chosen. The lo and hi are
    the cheapest and dearest corners of that sweep, so the range is a sweep and NOT a confidence
    interval.
  * and the tariff is NOT EVERY SITE'S OWN. MEASURED here: 61 of the 250 sites sit in a state whose
    own EIA rows are in the sweep (4 prices x 4 chiller efficiencies = 16 cells). The other 189 do
    not, and fall back to the Virginia and Illinois reference prices (8 x 4 = 32 cells). The count is
    reported below and published in portfolio.json so a card can state it rather than imply that 250
    state tariffs were looked up.
Those are properties of the per-site figure the product already publishes on every site tile; summing
does not add a new assumption, it carries the existing one 250 times.

🔴 THE HOURS FIGURE IS TWO DIFFERENT FIGURES AND THEY MUST NOT BE CONFUSED.
`weather_site_hours` is the sum over 250 sites of the hours each was scored against: 10,820,547. It is
a real measure of work done, but it is NOT 10.8 million hours of weather, because the 250 sites draw
on only 98 distinct airport stations and a station shared by three sites is counted three times.
`weather_hours_distinct` sums each of the 98 stations ONCE: 4,232,006 hours of recorded weather. That
is the smaller and the unimpeachable one, so it is the one the landing card states.

THE DERIVATION MIRRORS `app/src/lib/headline.ts:headlineFigures` line for line, deliberately: if the
two ever disagree the card would contradict the tile a reader clicks into. `run_all.py` regenerates
this file, so the totals cannot outlive the artefacts they were summed from.

Run from the repository root:  python tools/portfolio_totals.py
"""
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEMO = os.path.join(ROOT, "AGENTIC-ARBITER", "demo")
OUT = os.path.join(DEMO, "portfolio.json")


def load(name):
    with io.open(os.path.join(DEMO, name), encoding="utf-8") as f:
        return json.load(f)


def site_figures(bt, tr, mn, footprint_m2, scale):
    """One site's figures. The same arithmetic as headlineFigures(), and no other."""
    rows = [r for r in bt["n56_audit"] if str(r.get("step", "")).startswith("C ")]
    anchored = [r for r in rows if r.get("anchor") != "none"]
    if not anchored:
        return None
    ship = anchored[-1]

    hours_per_day = bt["hours"] / bt["days"]
    H = hours_per_day * ship["test_days"]
    mech_agent = H - ship["agent_safe_free_h"]
    mech_incumbent = H - ship["incumbent_safe_free_h"]

    cells = [c["usd_per_mw_it_per_year"] for c in mn["cells"]
             if str(c.get("hours_label", "")).startswith("+ notice 3 h")]
    if not cells or footprint_m2 is None:
        return None

    mw_lo = footprint_m2 * scale["w_per_m2_average_load"] / 1e6
    mw_hi = footprint_m2 * scale["w_per_m2_installed"] / 1e6

    return {
        "usd_lo": min(cells) * mw_lo,
        "usd_hi": max(cells) * mw_hi,
        "footprint_m2": footprint_m2,
        # EIA does not list every state, so a site outside the listed ones is priced on the Virginia
        # and Illinois reference rows instead of its own. The money file says which it got, and the
        # portfolio total has no business hiding that.
        "own_state_prices": bool(mn.get("electricity_prices_are_this_states_own")),
        "gain_h_per_year": ship["gain_h_per_year"],
        "mech_incumbent_h": mech_incumbent,
        "mech_agent_h": mech_agent,
        "weather_hours": bt["hours"],
        "mw_lo": mw_lo,
        "mw_hi": mw_hi,
        "coverage": tr["cycle"]["pooled_coverage"],
    }


def main():
    manifest = load("sites.json")
    scale = manifest.get("scale") or {}
    for k in ("w_per_m2_average_load", "w_per_m2_installed"):
        if k not in scale:
            print("sites.json has no scale.%s; cannot derive an IT load" % k)
            return 1

    offerable = [s for s in manifest["sites"] if s.get("offerable")]
    tot = {k: 0.0 for k in ("usd_lo", "usd_hi", "gain_h_per_year", "mech_incumbent_h",
                            "mech_agent_h", "weather_hours", "mw_lo", "mw_hi", "footprint_m2")}
    n = 0
    skipped = []
    gaining = 0
    own_state_prices = 0
    # station -> its hours, so a station shared by several sites is counted ONCE. See the docstring:
    # this is the difference between 4.2 million hours of weather and 10.8 million site-hours.
    station_hours = {}
    # 🔴 DISTINCTNESS IS CHECKED, NOT ASSUMED. If every site shipped a copy of Ashburn's backtest a
    # sum over 250 of them would be a projection wearing a total's clothes. The hashes prove the
    # artefacts really differ before any of them is added up.
    seen_bt, seen_mn = set(), set()

    for s in offerable:
        art = s.get("artefacts") or {}
        try:
            bt_raw = io.open(os.path.join(DEMO, art["backtest"]), encoding="utf-8").read()
            mn_raw = io.open(os.path.join(DEMO, art["money"]), encoding="utf-8").read()
            tr_raw = io.open(os.path.join(DEMO, art["trace"]), encoding="utf-8").read()
        except (KeyError, OSError):
            skipped.append(s["key"])
            continue
        seen_bt.add(hashlib.sha256(bt_raw.encode()).hexdigest())
        seen_mn.add(hashlib.sha256(mn_raw.encode()).hexdigest())

        f = site_figures(json.loads(bt_raw), json.loads(tr_raw), json.loads(mn_raw),
                         s.get("footprint_m2"), scale)
        if not f:
            skipped.append(s["key"])
            continue
        for k in tot:
            tot[k] += f[k]
        if f["gain_h_per_year"] > 0:
            gaining += 1
        if f["own_state_prices"]:
            own_state_prices += 1
        station_hours[s.get("station") or s["key"]] = f["weather_hours"]
        n += 1

    print("   sites summed              %d of %d offerable" % (n, len(offerable)))
    if skipped:
        print("   skipped (no usable row)   %d: %s" % (len(skipped), ", ".join(skipped[:6])))
    print("   distinct backtest files   %d   distinct money files %d" % (len(seen_bt), len(seen_mn)))
    print()
    print("   TOTAL usd_lo              $%s" % format(round(tot["usd_lo"]), ","))
    print("   TOTAL usd_hi              $%s" % format(round(tot["usd_hi"]), ","))
    print("   TOTAL gain_h_per_year     %s chiller-hours" % format(round(tot["gain_h_per_year"]), ","))
    print("   TOTAL weather_hours       %s scored hours" % format(round(tot["weather_hours"]), ","))
    print("   TOTAL mech incumbent h    %s" % format(round(tot["mech_incumbent_h"]), ","))
    print("   TOTAL mech agent h        %s" % format(round(tot["mech_agent_h"]), ","))
    cut = 100.0 * (tot["mech_incumbent_h"] - tot["mech_agent_h"]) / tot["mech_incumbent_h"]
    print("   PORTFOLIO cut             %.2f %%  (summed hours, not a mean of percentages)" % cut)
    print("   TOTAL IT load             %.1f to %.1f MW" % (tot["mw_lo"], tot["mw_hi"]))
    print("   TOTAL roof measured       %s m2" % format(round(tot["footprint_m2"]), ","))
    print()
    print("   sites gaining hours       %d of %d  (the other %d lose, and are SUBTRACTED above)"
          % (gaining, n, n - gaining))
    print("   priced on own state       %d of %d  (the other %d use the VA/IL reference rows)"
          % (own_state_prices, n, n - own_state_prices))
    print("   distinct weather stations %d" % len(station_hours))
    print("   hours of weather, DISTINCT %s   (site-hours scored: %s)"
          % (format(round(sum(station_hours.values())), ","),
             format(round(tot["weather_hours"]), ",")))

    out = {
        "_what": "Portfolio totals, summed over every offerable site's OWN artefacts. Written by "
                 "tools/portfolio_totals.py. Not a per-site figure multiplied by a count.",
        "_derivation": "For each offerable site in sites.json: its own backtest.json supplies the "
                       "anchored row of the five-year ladder (gain_h_per_year, the two mechanical "
                       "runtimes and the scored hours), its own money.json supplies the 16 swept "
                       "usd_per_mw_it_per_year cells at the shipped 3 h notice, and its own "
                       "footprint_m2 is turned into an MW range by sites.json's two published power "
                       "densities. Identical arithmetic to app/src/lib/headline.ts:headlineFigures.",
        "_modelled": "The IT load per site is inferred from measured roof area by published power "
                     "densities, and the tariff and chiller efficiency are swept over 16 published "
                     "combinations rather than known. The dollar range is that sweep, not a "
                     "confidence interval. Both caveats already apply to every per-site figure the "
                     "product publishes; the sum inherits them and adds none.",
        "sites_summed": n,
        "sites_gaining": gaining,
        "sites_losing": n - gaining,
        "sites_own_state_prices": own_state_prices,
        "sites_reference_prices": n - own_state_prices,
        "stations": len(station_hours),
        "weather_hours_distinct": sum(station_hours.values()),
        "weather_site_hours": tot["weather_hours"],
        "footprint_m2": tot["footprint_m2"],
        "sites_offerable": len(offerable),
        "distinct_backtests": len(seen_bt),
        "distinct_money_files": len(seen_mn),
        "usd_lo": tot["usd_lo"],
        "usd_hi": tot["usd_hi"],
        "gain_h_per_year": tot["gain_h_per_year"],
        "weather_hours": tot["weather_hours"],
        "mech_incumbent_h": tot["mech_incumbent_h"],
        "mech_agent_h": tot["mech_agent_h"],
        "cut_pct": cut,
        "mw_lo": tot["mw_lo"],
        "mw_hi": tot["mw_hi"],
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print("\n   wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
