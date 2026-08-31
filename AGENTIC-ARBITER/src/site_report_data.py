# -*- coding: utf-8 -*-
"""EVERY NUMBER THE REBUILT SITE REPORT PRINTS, PULLED FROM THE ARTEFACTS THAT PRODUCED IT.

Separated from the drawing on purpose. The old report interleaved "read a value" with "place a
string", so a figure could not be checked without reading the layout code around it. This module
returns one dict, `collect(site_key)`, and nothing in it draws. `site_report.py` renders it.

⚠ THE CONFIGURATION IS CHOSEN BY `report.pick_block`, IMPORTED RATHER THAN REIMPLEMENTED.
That function scores every configuration in `explanations.json` for informativeness and excludes
the `facing` bank, which exists only to price the refusal guard. Reusing it means the rebuilt
report describes the SAME configuration the previous one did, so a reader comparing the two is
looking at a presentation change and not a silent change of subject.

EVERY FIGURE CARRIES ITS KIND. `measured` came off an instrument or a count; `backtested` is a
simulation of two controllers over measured weather; `derived` is a measured quantity times a
sourced conversion factor; `modeled` rests on an assumption this project did not measure. The
renderer prints the label for anything that is not measured or backtested, because the brief
requires modelling to be visible in the document rather than in a footnote nobody reads.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import metros as M                                                   # noqa: E402
import report as R                                                   # noqa: E402


# --------------------------------------------------------------------------- helpers
def _load(site_key):
    art = {}
    for name in ("trace", "explanations", "backtest", "rolling", "money"):
        p = M.demo_path("%s.json" % name, site_key)
        if not os.path.exists(p):
            raise SystemExit("%s missing -- run `python build_sites.py %s` first" % (p, site_key))
        art[name] = json.load(open(p, encoding="utf-8"))
    return art


# --------------------------------------------------------------------------- the collector
def collect(site_key=None):
    k = site_key or M.metro_key()
    art = _load(k)
    t, expl, bt, rl, mn = (art["trace"], art["explanations"], art["backtest"],
                           art["rolling"], art["money"])

    case, blk = R.pick_block(expl)
    if blk is None:
        raise SystemExit("no explanation blocks in explanations.json for %s" % k)
    cfg, summ, hours = blk["config"], blk["summary"], blk["hours"]
    site = t["site"]
    rb = rl["configs"][0]

    # ---- the five-year ladder and the shipped row --------------------------------------------
    lad = [r for r in bt["n56_audit"] if str(r["step"]).startswith("C ")]
    ship = [r for r in lad if r.get("anchor") != "none"][-1]
    hours_per_day = bt["hours"] / bt["days"]
    total_h = hours_per_day * ship["test_days"]
    mech_agent = total_h - ship["agent_safe_free_h"]
    mech_inc = total_h - ship["incumbent_safe_free_h"]

    # ---- money: the site-level figure the brief wants leading, and the rate behind it ---------
    # The hours row is measured; the per-MW rate is a sweep of published factors; the megawatt
    # span comes from a watts-per-square-metre density this project did NOT measure, so the
    # site-level total is the one figure in the document labelled `modeled`.
    cells = [c for c in mn["cells"] if c["hours_label"].startswith("+ notice 3 h")]
    rate = sorted(c["usd_per_mw_it_per_year"] for c in cells)
    # 🔴 `sites.json` IS GLOBAL, AND `demo_path` WOULD KEY-PREFIX IT. `demo_path("x.json")`
    # returns the unsuffixed name only for the DEFAULT metro and `<KEY>_x.json` for every
    # other, which is right for per-site artefacts and wrong for the one manifest that lists
    # all of them. Under `METRO=AL_way_1540172608` it resolved to
    # `AL_way_1540172608_sites.json` and raised FileNotFoundError, so this would have failed
    # on all 249 sites the moment build_sites.py drove it. `audit.py` names sites.json in its
    # own GLOBAL_OK list and reads it straight from DEMO; this now does the same.
    sj = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
    scale = sj.get("scale") or {}
    foot = next((s.get("footprint_m2") for s in sj["sites"] if s["key"] == k), None)
    mw_lo = mw_hi = usd_lo = usd_hi = None
    if foot and scale.get("w_per_m2_average_load"):
        mw_lo = foot * scale["w_per_m2_average_load"] / 1e6
        mw_hi = foot * scale["w_per_m2_installed"] / 1e6
        usd_lo, usd_hi = mw_lo * rate[0], mw_hi * rate[-1]

    # ---- the bound's own record --------------------------------------------------------------
    bdl = t["cycle"].get("bound_day_level") or {}
    m3 = bt["mondrian"]["3"]
    aci = bt["aci"]["3"]

    # ---- the plume, at the bank the reported configuration actually uses ----------------------
    bank = cfg["bank_mode"]
    rt = t["cycle"]["rise_tables"][bank]

    # ---- the portfolio, from every other site's own shipped row -------------------------------
    portfolio = _portfolio()

    # 🔴 ONE FLAG, DERIVED TWO WAYS AND CHECKED AGAINST ITSELF. 168 of the 249 covered sites are a
    # SINGLE mapped building with no neighbour, so there is no facade for an exhaust plume to cross
    # and no second intake to warm: `build_standalone_site.py` writes `facade_gap_m: null`,
    # `osm_receptor: null` and `intake_m: null`, and the solver records `n_solves: 0` with the device
    # string "not solved -- no receptor intake exists to compute a rise at".
    #
    # Those are two independent signals from two different files, so they are compared rather than
    # trusted: a site that has a gap but no solves, or solves but no gap, means one of the two build
    # paths has drifted and the report must not paper over it.
    standalone = site.get("facade_gap_m") is None
    _solved = bool(rt.get("n_solves"))
    assert standalone != _solved, (
        "%s reports facade_gap_m=%r but n_solves=%r; the pair build and the standalone build "
        "disagree about what this site is" % (k, site.get("facade_gap_m"), rt.get("n_solves")))

    return {
        "site_key": k,
        "standalone": standalone,
        # 🔴 READ FROM THE MANIFEST, NOT COUNTED FROM THE PORTFOLIO. The two differ on purpose: the
        # portfolio is every site the agent was BUILT on, and `offerable` is the subset the interface
        # OFFERS, which excludes the ones whose own five-year measurement came out negative. The
        # Scale page quotes both and says why they differ, so it must read both rather than assume
        # they are the same number.
        "offered_n": sum(1 for x in json.load(
            open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))["sites"]
            if x.get("offerable")),
        "site": {
            "label": t.get("metro", {}).get("label") or site.get("label") or k,
            "station": t["weather"]["station"],
            "footprint_m2": foot,
            "osm_source": site.get("osm_source"),
            "osm_receptor": site.get("osm_receptor"),
            "facade_gap_m": site.get("facade_gap_m"),
            "operator": site.get("operator"),
            # Needed by the aerial figure, which registers the solver's own rings onto the
            # screening frame. Passed through verbatim rather than reshaped: the figure asserts the
            # gap it draws against `facade_gap_m`, and that check is only worth anything if both
            # sides come from the same trace.
            "centre": site.get("centre"),
            "geometry": site.get("geometry"),
            "weather_hours": t["weather"]["n_hours"],
        },
        "case": case,
        "config": cfg,
        "summary": summ,
        "hours": hours,

        # ---- page 1 tiles ---------------------------------------------------------------------
        "headline": {
            "runtime_cut_pct": 100.0 * (mech_inc - mech_agent) / mech_inc,
            "mech_agent_h": mech_agent,
            "mech_inc_h": mech_inc,
            "chiller_h_per_year": ship["gain_h_per_year"],
            "free_h_per_year": rb["executed_free_h_per_day"] * 365.25,
            "held_out_days": ship["test_days"],
            "weather_hours": bt["hours"],
            "weather_days": bt["days"],
            "coverage_pooled": t["cycle"]["pooled_coverage"],
            "coverage_nominal": bdl.get("nominal", 0.9),
            "usd_site_lo": usd_lo, "usd_site_hi": usd_hi,
            "mw_lo": mw_lo, "mw_hi": mw_hi,
            "usd_rate_lo": rate[0], "usd_rate_hi": rate[-1],
            "rate_cells": len(cells),
            "breach_per_1000": rb["breach_per_1000_free_h"],
            "breach_h": rb["executed_breach_h"],
            "free_h_taken": rb["executed_free_h"],
        },

        # ---- the bound, for the validation page ------------------------------------------------
        "bound": {
            "n_pairs": bdl.get("n"),
            "n_needed": bdl.get("n_needed_for_nominal"),
            "ceiling": bdl.get("attainable"),
            "margin_c": bdl.get("margin"),
            "clamped": bdl.get("clamped"),
            "pooled": t["cycle"]["pooled_coverage"],
            "pooled_worst_group": m3["pooled"]["worst_group"]["coverage"],
            "mondrian_worst_group": m3["mondrian_hod"]["worst_group"]["coverage"],
            "groups_below": m3["pooled"]["groups_below_target"],
            "aci_coverage": aci["ACI"]["realised_coverage"],
            "aci_rounds": aci["ACI"]["rounds"],
            "static_coverage": aci["static"]["realised_coverage"],
            "coverage_by_lead": rb["coverage_by_lead"],
            "mondrian_by_group": m3["mondrian_hod"].get("groups"),
        },

        # ---- the physics ----------------------------------------------------------------------
        "plume": {
            "bank": bank,
            "n_solves": rt.get("n_solves"),
            "solve_seconds": rt.get("solve_seconds"),
            "device": rt.get("device"),
            "max_rise_c": rt.get("max_rise_c"),
            "max_rise_bearing": rt.get("max_rise_bearing"),
            "refused": rt.get("refused") or [],
            "n_bearings": len(t["direction_table"]["modes"][bank]["rows"])
                          if "rows" in t["direction_table"]["modes"][bank] else 72,
            "rise_table_file": M.demo_path("rise_table_%s.json" % bank, k),
            # For the specification table on the physics page. All present in the rise table and
            # none of them previously read by the report.
            "speeds": rt.get("speeds") or [],
            "max_rise_speed_ms": rt.get("max_rise_speed_ms"),
            "mean_rise_c": rt.get("mean_rise_c"),
            "n_downwind": rt.get("n_downwind"),
            "march_m": rt.get("march_m"),
            "with_term": _n56(bt, "B with plume term"),
            "without_term": _n56(bt, "B plume term REMOVED"),
        },

        # ---- stability and the incumbent -------------------------------------------------------
        "rolling": {
            "replans": rb["replans"],
            "zero_change": rb["replans_with_zero_change"],
            "churn": rb["churn"],
            "hours_compared": rb["hours_compared"],
            "horizon_h": rl["horizon_h"],
        },

        # ---- what the forecast is worth --------------------------------------------------------
        "ablation": _skill_ablation(bt),
        "notice_sweep": _axis_sweep(bt, "notice_h"),
        "ladder": [{"step": r["step"][2:], "gain": r["gain_h_per_year"]} for r in lad],
        "portfolio": portfolio,
    }


def _n56(bt, step):
    rows = [r for r in bt["n56_audit"] if r["step"] == step]
    return rows[0] if rows else None


def _skill_ablation(bt):
    rows = {(r["axis"], str(r["value"])): r for r in bt["sensitivity"]["rows"]}
    base = [r for r in bt["sensitivity"]["rows"] if r["is_base"]][0]
    zero = rows.get(("skill", "0.0"))
    if not zero:
        return None
    return {"base_gain": base["gain_h_per_year"], "zero_skill_gain": zero["gain_h_per_year"],
            "share_pct": 100.0 * (base["gain_h_per_year"] - zero["gain_h_per_year"])
                         / base["gain_h_per_year"]}


def _axis_sweep(bt, axis):
    out = []
    for r in bt["sensitivity"]["rows"]:
        if r["axis"] == axis:
            out.append({"value": r["value"], "gain": r["gain_h_per_year"]})
    return sorted(out, key=lambda x: float(x["value"]))


_OFFERED_CACHE = []


def _offered():
    """The set of site keys the interface offers, read from the manifest once.

    ⚠ A SET, NOT A COUNT, because the chart needs to know WHICH rows are offered rather than how
    many. Cached because `_portfolio` asks per row and there are 250 of them.
    """
    if not _OFFERED_CACHE:
        sj = json.load(open(os.path.join(M.DEMO, "sites.json"), encoding="utf-8"))
        _OFFERED_CACHE.append({x["key"] for x in sj["sites"] if x.get("offerable")})
    return _OFFERED_CACHE[0]


def _portfolio():
    """Every site's own shipped five-year row, for the scale page's distribution.

    ⚠ READ FROM EACH SITE'S OWN `*_backtest.json`, not from a summary file, because no summary
    file carries it: `sites.json` has footprints and verdicts and no savings at all. 249 per-site
    backtests plus the default metro's own is the full 250.
    """
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(M.DEMO, "*_backtest.json"))) + \
             [os.path.join(M.DEMO, "backtest.json")]:
        try:
            d = json.load(open(p, encoding="utf-8"))
            lad = [r for r in d.get("n56_audit", []) if str(r["step"]).startswith("C ")]
            ship = [r for r in lad if r.get("anchor") != "none"]
            if not ship:
                continue
            key = os.path.basename(p).replace("_backtest.json", "").replace("backtest.json",
                                                                           M.DEFAULT_METRO)
            out.append({"key": key, "gain": ship[-1]["gain_h_per_year"],
                        "offered": key in _offered()})
        except Exception:                                            # noqa: BLE001
            continue
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = collect(sys.argv[1] if len(sys.argv) > 1 else None)
    h, b, p = d["headline"], d["bound"], d["plume"]
    print("SITE      %s  (%s), station %s" % (d["site"]["label"], d["site_key"], d["site"]["station"]))
    print("CASE      %s   limit %.1f C, notice %d h, budget %d, bank %s, dwell %d h"
          % (d["case"], d["config"]["limit_c"], d["config"]["notice_h"],
             d["config"]["switch_budget"], d["config"]["bank_mode"], d["config"]["min_dwell_h"]))
    print()
    print("PAGE 1 TILES")
    print("  runtime cut        %.1f %%   (%s h -> %s h)"
          % (h["runtime_cut_pct"], format(int(round(h["mech_inc_h"])), ","),
             format(int(round(h["mech_agent_h"])), ",")))
    print("  chiller h/yr       %+.0f" % h["chiller_h_per_year"])
    print("  free cooling       %s h/yr" % format(int(round(h["free_h_per_year"])), ","))
    print("  hours validated    %s over %s days, %s held out"
          % (format(h["weather_hours"], ","), format(h["weather_days"], ","),
             format(h["held_out_days"], ",")))
    print("  bound coverage     %.1f %% against a %.0f %% promise"
          % (100 * h["coverage_pooled"], 100 * h["coverage_nominal"]))
    if h["usd_site_lo"]:
        print("  money, this site   $%s to $%s per year   [MODELED]"
              % (format(int(round(h["usd_site_lo"])), ","), format(int(round(h["usd_site_hi"])), ",")))
        print("       at the rate   $%s to $%s per MW of IT load per year, %d cells   [DERIVED]"
              % (format(int(round(h["usd_rate_lo"])), ","),
                 format(int(round(h["usd_rate_hi"])), ","), h["rate_cells"]))
        print("       on a measured footprint of %s m2, %.0f to %.0f MW derived"
              % (format(int(round(d["site"]["footprint_m2"])), ","), h["mw_lo"], h["mw_hi"]))
    print()
    print("BOUND     n=%s pairs, needs %s, ceiling %.0f %%, margin %.3f C, clamped=%s"
          % (b["n_pairs"], b["n_needed"], 100 * (b["ceiling"] or 0), b["margin_c"] or 0,
             b["clamped"]))
    print("          pooled %.1f %%   mondrian worst group %.1f %%   ACI %.4f over %s rounds"
          % (100 * b["pooled"], 100 * b["mondrian_worst_group"], b["aci_coverage"],
             format(b["aci_rounds"], ",")))
    print("          %d per-lead bounds, all >= 90 %%: %s   worst %.4f"
          % (len(b["coverage_by_lead"]), all(v >= 0.9 for v in b["coverage_by_lead"].values()),
             min(b["coverage_by_lead"].values())))
    print()
    print("PLUME     bank %s, %s solves in %.1f s on %s"
          % (p["bank"], p["n_solves"], p["solve_seconds"] or 0, p["device"]))
    print("          worst rise %.3f C at %s deg, %d of %d bearings refused"
          % (p["max_rise_c"], p["max_rise_bearing"], len(p["refused"]), p["n_bearings"]))
    if p["with_term"] and p["without_term"]:
        print("          plume term: unsafe hours %d with, %d without"
              % (p["with_term"]["agent_breach_h"], p["without_term"]["agent_breach_h"]))
    print()
    print("BREACH    %d of %s free-cooling hours, %.2f per thousand"
          % (h["breach_h"], format(h["free_h_taken"], ","), h["breach_per_1000"]))
    print("ABLATION  forecast is worth %.1f %% (%.1f -> %.1f h/yr)"
          % (d["ablation"]["share_pct"], d["ablation"]["base_gain"],
             d["ablation"]["zero_skill_gain"]))
    print("HOURS     %d, binding: %s" % (len(d["hours"]),
          {x: sum(1 for y in d["hours"] if y.get("binding") == x)
           for x in sorted(set(str(y.get("binding")) for y in d["hours"]))}))
    print("PORTFOLIO %d sites, gains %.0f to %.0f h/yr, %d negative"
          % (len(d["portfolio"]), min(x["gain"] for x in d["portfolio"]),
             max(x["gain"] for x in d["portfolio"]),
             sum(1 for x in d["portfolio"] if x["gain"] < 0)))
